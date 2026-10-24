"""Git native chỉ repo bare tạm: hai process, retry union, không lộ code/index."""
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from unittest import mock
import pytest

with mock.patch.object(os, "environ", {}):
    from tools import hop_thu as ht

GIT = "C:/Program Files/Git/cmd/git.exe" if os.name == "nt" else "/usr/bin/git"
CODE = str(Path(__file__).resolve().parents[1])


@pytest.fixture(autouse=True)
def fake_environment(tmp_path):
    with mock.patch.object(os, "environ", environment(tmp_path)), \
            mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network disabled")):
        yield


def environment(home):
    return {"HOME": str(home), "USERPROFILE": str(home), "SYSTEMROOT": "C:/Windows", "PYTHONUTF8": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "file",
            "PATH": "C:/Program Files/Git/cmd;C:/Windows/System32" if os.name == "nt" else "/usr/bin:/bin"}


def git(root, *args):
    result = subprocess.run([GIT, *args], cwd=root, env=environment(root), capture_output=True, encoding="utf-8")
    assert result.returncode == 0, "fixture git command failed"
    return result.stdout.strip()


def repos(tmp_path, with_event=False):
    remote, seed = tmp_path / "remote.git", tmp_path / "seed"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(seed))
    (seed / "README.md").write_text("fixture\n", encoding="utf-8")
    if with_event:
        ht.write_event(seed, "phien-chinh", "tin", to="cloud-B", text="seed", now=ht.datetime(2026, 10, 1, tzinfo=ht.VN_TZ))
    git(seed, "add", ".")
    git(seed, "-c", "user.name=Fixture", "-c", "user.email=fixture@localhost", "commit", "-qm", "seed")
    git(seed, "push", "-q", "origin", "HEAD:main")
    clones = []
    for name in ("a", "b"):
        target = tmp_path / name
        git(tmp_path, "clone", "-q", str(remote), str(target))
        clones.append(target)
    return remote, clones


WORKER = r'''
import os, sys
from unittest.mock import patch
home, root, code, barrier, who, mode = sys.argv[1:]
fake = {"HOME": home, "USERPROFILE": home, "SYSTEMROOT": "C:/Windows", "PYTHONUTF8": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "file", "PATH": "C:/Program Files/Git/cmd;C:/Windows/System32" if os.name == "nt" else "/usr/bin:/bin"}
patch.object(os, "environ", fake).start()
import json, socket, time
from pathlib import Path
patch.object(socket.socket, "connect", side_effect=AssertionError("network disabled")).start()
sys.path.insert(0, code)
from tools import hop_thu as ht
from tools import hop_thu_store as store
root, barrier = Path(root), Path(barrier)
original = store._remote_files
calls = 0
def remote(*args):
    global calls
    value = original(*args)
    calls += 1
    if calls == 1:
        (barrier / (who + ".ready")).write_text("ready")
        end = time.monotonic() + 30
        while len(list(barrier.glob("*.ready"))) != 2:
            if time.monotonic() > end:
                raise RuntimeError("fixture barrier timeout")
            time.sleep(.02)
    return value
store._remote_files = remote
metrics = {}
flush = store.flush_pending
def measured(*args, **kw):
    result = flush(*args, **kw)
    metrics.update(result)
    return result
store.flush_pending = measured
if mode == "batch":
    for i in range(2):
        assert ht.main(["--goc", str(root), "tin", "--lane", "phien-chinh", "--to", "cloud-B", "--text", who + str(i)]) == 0
    assert ht.main(["--goc", str(root), "giao", who, "--to", "cloud-B", "--title", who, "--lane", "phien-chinh", "--push"]) == 0
else:
    now = ht.datetime(2026, 10, 24, tzinfo=ht.VN_TZ)
    ht.write_event(root, "phien-chinh", "tin", to="cloud-B", text=who, now=now - ht.timedelta(days=20))
    store.unread_snapshot(root, "cloud-B")
    store.acknowledge_snapshot(root, "cloud-B", now=now - ht.timedelta(days=10))
    store.archive(root, ht.compute_state(ht.load_events(root)[0]), now=now, apply=True)
    store.flush_pending(root, ht._git)
print(json.dumps(metrics))
'''


def test_urgent_without_push_flushes_queued_batch(tmp_path):
    remote, clones = repos(tmp_path)
    root = clones[0]
    before = git(root, "rev-parse", "HEAD")
    assert ht.main(["--goc", str(root), "tin", "--lane", "phien-chinh", "--to", "cloud-B", "--text", "queued fixture"]) == 0
    assert git(root, "ls-remote", "origin", "refs/heads/main").split()[0] == before
    assert ht.main(["--goc", str(root), "giao", "AUTO", "--lane", "phien-chinh", "--to", "cloud-B", "--title", "auto fixture"]) == 0
    after = git(root, "ls-remote", "origin", "refs/heads/main").split()[0]
    assert before != after
    assert git(remote, "rev-list", "--count", f"{before}..{after}") == "1"
    assert len(git(remote, "ls-tree", "-r", "--name-only", after, "hop_thu/su_kien").splitlines()) == 2
    assert git(root, "rev-parse", "HEAD") == before
    assert not list((ht.store.local_dir(root) / "pending").glob("*.json"))


def concurrent(tmp_path, clones, mode):
    script, barrier = tmp_path / "worker.py", tmp_path / "barrier"
    script.write_text(WORKER, encoding="utf-8")
    barrier.mkdir()
    workers = [subprocess.Popen([sys.executable, "-X", "utf8", str(script), str(tmp_path / "home"), str(root), CODE,
                                str(barrier), str(i), mode], env=environment(tmp_path / "home"),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
               for i, root in enumerate(clones)]
    results = []
    try:
        for worker in workers:
            out, _ = worker.communicate(timeout=75)
            assert worker.returncode == 0, "fixture worker failed"
            results.append(json.loads(out.splitlines()[-1]))
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.wait()
    assert sorted(row["attempts"] for row in results) == [1, 2]
    return results


def test_two_real_process_batches_retry_without_code_or_index_changes(tmp_path):
    remote, clones = repos(tmp_path)
    git(clones[0], "checkout", "-qb", "private-code")
    (clones[0] / "private.py").write_text("fixture_private_code\n")
    git(clones[0], "add", "private.py")
    git(clones[0], "-c", "user.name=Fixture", "-c", "user.email=fixture@localhost", "commit", "-qm", "private")
    for root in clones:
        (root / "staged.py").write_text("fixture_staged_code\n")
        git(root, "add", "staged.py")
    before = [(git(root, "rev-parse", "HEAD"), (root / ".git/index").read_bytes()) for root in clones]
    results = concurrent(tmp_path, clones, "batch")
    names = git(remote, "ls-tree", "-r", "--name-only", "main").splitlines()
    assert len([p for p in names if p.startswith("hop_thu/su_kien/")]) == 6
    assert "private.py" not in names and "staged.py" not in names
    assert git(remote, "rev-list", "--count", "main") == "3"  # seed + 2 lô, thay vì 6 commits sự kiện
    assert [row["paths"] for row in results] == [3, 3]
    for root, (head, index) in zip(clones, before):
        assert git(root, "rev-parse", "HEAD") == head
        assert (root / ".git/index").read_bytes() == index
        assert not list((ht.store.local_dir(root) / "pending").glob("*.json"))


def test_two_real_process_archive_receipt_union_keeps_ids(tmp_path):
    remote, clones = repos(tmp_path, with_event=True)
    concurrent(tmp_path, clones, "archive")
    latest = tmp_path / "latest"
    git(tmp_path, "clone", "-q", str(remote), str(latest))
    records, errors = ht.store.load_records(latest)
    assert not errors and len(records) == 3
    assert not list((latest / "hop_thu/su_kien").glob("*.json"))
    assert len(ht.store._archive_rows((latest / "hop_thu/luu_tru/2026-10.jsonl").read_bytes())) == 3
    assert ht.store.unread_snapshot(latest, "cloud-B") == []


def test_second_sync_same_sha_uses_verified_blob_cache(tmp_path):
    remote, clones = repos(tmp_path, with_event=True)
    calls = []
    def measured(root, *args, **kwargs):
        calls.append(args)
        return ht._git(root, *args, **kwargs)
    first = ht.store.sync_remote(clones[0], measured)
    assert sum(args[0] == "cat-file" for args in calls) == 1
    second = ht.store.sync_remote(clones[0], measured)
    assert first == second
    assert sum(args[0] == "cat-file" for args in calls) == 1
