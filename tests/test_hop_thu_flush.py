"""Hồi quy flush: môi trường giả, không Git mạng hay dữ liệu sản xuất."""
import os
import json
import time
from pathlib import Path
from unittest import mock
from types import SimpleNamespace
import pytest
with mock.patch.object(os, 'environ', {}):
    from tools import hop_thu_store as store
    from tools import hop_thu as ht

@pytest.fixture(autouse=True)
def isolated(tmp_path):
    with mock.patch.object(os, 'environ', {'HOME': str(tmp_path / 'home'), 'USERPROFILE': str(tmp_path / 'home')}):
        yield

def ev(i):
    return store.canonical({'ts':'2026-10-01T00:00:00+07:00','lane':'phien-chinh','kind':'tin','text':str(i)})

def test_flush_only_materializes_three_new_files(tmp_path):
    remote = {f'hop_thu/su_kien/{i}.json': ev(i) for i in range(1000)}
    new = {f'hop_thu/su_kien/{i}.json': ev(i) for i in range(1000,1003)}
    for rel, content in new.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        store.queue_path(tmp_path, path)
    written = []
    original = Path.write_bytes
    def write(path, content, **kw):
        if 'union-' in str(path) and str(path).endswith('.json'):
            written.append(str(path))
        return original(path, content, **kw)
    git = mock.Mock(return_value=SimpleNamespace(stdout='b'*40,returncode=0))
    with mock.patch.object(store, '_remote_files', side_effect=[('a'*40,remote),('b'*40,{**remote,**new})]), mock.patch.object(Path,'write_bytes',write):
        assert store.flush_pending(tmp_path,git)['paths'] == 3
    assert len(written) == 3

def test_dead_owner_is_archived_and_successor_not_removed(tmp_path):
    path = store.local_dir(tmp_path)/'flush.lock'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'pid':99999999,'token':'old','renewed':time.time(),'started':time.time(),'identity':'old'}))
    with mock.patch.object(store,'_process_identity', return_value=None):
        with store.locked(tmp_path,'flush'):
            row=json.loads(path.read_text())
            assert row['token'] != 'old'
            row['token']='successor'
            path.write_text(json.dumps(row))
    assert json.loads(path.read_text())['token']=='successor'
    assert len(list((path.parent/'_luu_tru').glob('flush-*'))) == 1

def test_fresh_owner_queues_without_hiding_other_errors(tmp_path,capsys):
    with mock.patch.object(store,'locked',side_effect=store.LockTimeout('fixture')):
        assert store.flush_pending(tmp_path,mock.Mock())['queued']
    with mock.patch.object(store,'locked',side_effect=ValueError('fixture')):
        with pytest.raises(ValueError): store.flush_pending(tmp_path,mock.Mock())

def test_remote_cache_bundle_uses_no_per_event_copy(tmp_path):
    files={f'hop_thu/su_kien/{i}.json':ev(i) for i in range(1000)}
    with mock.patch.object(store,'atomic_bytes',wraps=store.atomic_bytes) as write:
        store._cache_remote(tmp_path,'a'*40,files)
    assert write.call_count == 1
    assert len(store.require_records(tmp_path))==1000


@pytest.mark.parametrize("owner,identity,age,reclaimed", [
    ("alive", "birth", 0, False),
    ("hung", "birth", 601, True),
    ("reused", "new-birth", 0, True),
])
def test_lock_lease_pid_reuse_and_fresh_owner(tmp_path, owner, identity, age, reclaimed):
    path=store.local_dir(tmp_path)/"flush.lock"
    path.parent.mkdir(parents=True)
    row={"pid":99999999,"token":"old","started":time.time()-age,"renewed":time.time()-age,"identity":"birth"}
    path.write_text(json.dumps(row))
    def process(pid):
        return identity if pid==99999999 else "self"
    with mock.patch.object(store,"_process_identity",side_effect=process), mock.patch.object(store,"LOCK_WAIT",0):
        if reclaimed:
            with store.locked(tmp_path,"flush") as lease:
                lease.check(renew=True)
                assert json.loads(path.read_text())["token"]!="old"
            assert not path.exists()
        else:
            with pytest.raises(store.LockTimeout):
                with store.locked(tmp_path,"flush"): pass
            assert json.loads(path.read_text())["token"]=="old"


def test_lease_lost_cannot_push_or_clean_queue(tmp_path):
    with store.locked(tmp_path,"flush") as lease:
        path=store.local_dir(tmp_path)/"flush.lock"
        row=json.loads(path.read_text())
        row["token"]="replacement"
        path.write_text(json.dumps(row))
        with pytest.raises(ValueError): lease.check(renew=True)
    assert path.exists()


def test_lock_containment_blocks_symlink_parent(tmp_path):
    blocked=store.local_dir(tmp_path)
    original=Path.is_symlink
    with mock.patch.object(Path,"is_symlink",lambda p:p==blocked or original(p)):
        with pytest.raises(ValueError):
            with store.locked(tmp_path,"flush"): pass
    assert not blocked.exists()


def test_canonical_duplicate_keeps_remote_bytes():
    raw=ev(1)
    incoming=json.dumps(json.loads(raw),indent=2).encode()
    remote={"hop_thu/su_kien/a.json":raw}
    assert store._union_files(remote,{"hop_thu/su_kien/a.json":incoming})==remote


def test_queue_message_only_for_lock_timeout(tmp_path,capsys):
    result={"paths":0,"commit":None,"queued":True}
    with mock.patch.object(store,"flush_pending",return_value=result):
        ht.cmd_day_lo(None,tmp_path)
    assert "đã xếp hàng, lô sau sẽ đẩy" in capsys.readouterr().out


def test_legacy_empty_lock_requires_expired_lease(tmp_path):
    path=store.local_dir(tmp_path)/"flush.lock"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"")
    with mock.patch.object(store,"LOCK_WAIT",0):
        with pytest.raises(store.LockTimeout):
            with store.locked(tmp_path,"flush"): pass
    old=time.time()-601
    os.utime(path,(old,old))
    with store.locked(tmp_path,"flush"): pass
    assert len(list((path.parent/"_luu_tru").glob("flush-*")))==1


@pytest.mark.parametrize("kind,explicit", [("tin",True),("hoi",False),("xong",False),("gop",False),("giao",False)])
def test_finish_queued_never_claims_sent(tmp_path,capsys,kind,explicit):
    path=tmp_path/"hop_thu/su_kien/a.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(ev(1))
    args=SimpleNamespace(push=explicit,khong_day=False,lane="phien-chinh")
    with mock.patch.object(ht,"is_git_repo",return_value=True), mock.patch.object(store,"flush_pending",return_value={"paths":0,"commit":None,"queued":True}):
        ht._finish(args,tmp_path,path,kind,"A")
    output=capsys.readouterr().out
    assert "đã xếp hàng, lô sau sẽ đẩy" in output
    assert "Đã gửi" not in output and "Đã push" not in output


def test_busy_guard_at_push_boundary_keeps_queue(tmp_path):
    from contextlib import contextmanager
    path=tmp_path/"hop_thu/su_kien/a.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(ev(1))
    store.queue_path(tmp_path,path)
    original=store._lock_guard
    busy=[False]
    @contextmanager
    def guard(root,name):
        if busy[0]:
            yield False
        else:
            with original(root,name) as held: yield held
    calls=[]
    def git(root,*args,**kw):
        calls.append(args[0])
        if "commit-tree" in args: busy[0]=True
        return SimpleNamespace(stdout="b"*40,returncode=0)
    with mock.patch.object(store,"_lock_guard",guard), mock.patch.object(store,"_remote_files",return_value=("a"*40,{})):
        with pytest.raises(ValueError): store.flush_pending(tmp_path,git)
    assert "push" not in calls
    assert path.exists() and list((store.local_dir(tmp_path)/"pending").glob("*.json"))


def test_unknown_valid_pid_cannot_steal_even_expired(tmp_path):
    path=store.local_dir(tmp_path)/"flush.lock"
    path.parent.mkdir(parents=True)
    old=time.time()-601
    row={"pid":99999999,"identity":"birth","token":"old","started":old,"renewed":old}
    path.write_text(json.dumps(row))
    with mock.patch.object(store,"_process_identity",return_value="unknown"),mock.patch.object(store,"LOCK_WAIT",0):
        with pytest.raises(store.LockTimeout):
            with store.locked(tmp_path,"flush"): pass
    assert json.loads(path.read_text())["token"]=="old"
    assert not (path.parent/"_luu_tru").exists()


@pytest.mark.parametrize("queued", [True,False])
def test_windows_guard_only_contention_can_queue(tmp_path,queued):
    import errno
    # Proxy riêng cho module store: không đổi os.name toàn tiến trình/Path.
    class WindowsOS:
        name="nt"
        def __getattr__(self,name): return getattr(os,name)
    code=errno.EACCES if queued else errno.EIO
    fake=SimpleNamespace(LK_NBLCK=1,LK_UNLCK=0,locking=mock.Mock(side_effect=OSError(code,"fixture guard")))
    import builtins
    original_import=builtins.__import__
    def load(name,*args,**kwargs):
        return fake if name=="msvcrt" else original_import(name,*args,**kwargs)
    with mock.patch.object(store,"os",WindowsOS()),mock.patch.object(builtins,"__import__",side_effect=load),mock.patch.object(store,"_process_identity",return_value="fixture-birth"),mock.patch.object(store,"LOCK_WAIT",0):
        if queued:
            assert store.flush_pending(tmp_path,mock.Mock())["queued"]
        else:
            with pytest.raises(OSError): store.flush_pending(tmp_path,mock.Mock())


def test_git_timeout_is_bounded_generic_and_keeps_queue(tmp_path,capsys):
    import subprocess
    path=ht.write_event(tmp_path,"phien-chinh","tin",text="fixture",to="codex")
    args=SimpleNamespace(push=True,khong_day=False,lane="phien-chinh")
    def timeout(*a,**kw):
        assert 0 < kw.get("timeout",0) <= 30
        raise subprocess.TimeoutExpired(["fixture-private-command"],kw["timeout"],output="fixture-private-output")
    with mock.patch.object(ht,"is_git_repo",return_value=True), mock.patch.object(subprocess,"run",side_effect=timeout):
        with pytest.raises(ht.HopThuError) as error:
            ht._finish(args,tmp_path,path,"tin",None)
    assert "fixture-private" not in str(error.value)
    assert "hết thời gian" in str(error.value)
    assert "Đã gửi" not in capsys.readouterr().out
    assert path.exists() and list((store.local_dir(tmp_path)/"pending").glob("*.json"))
