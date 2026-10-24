"""Hộp thư gọn: fixture metadata riêng, không thao tác hộp thư sản xuất."""
import json
import io
import hashlib
import os
import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from contextlib import redirect_stdout
from unittest import mock
import pytest

with mock.patch.object(os, "environ", {}):
    from tools import hop_thu as ht
    try:
        from tools import hop_thu_store as store
    except ImportError:
        store = None

VN = timezone(timedelta(hours=7))
NOW = datetime(2026, 10, 24, 12, tzinfo=VN)


@pytest.fixture(autouse=True)
def fake_runtime(tmp_path):
    with mock.patch.object(os, "environ", {"HOME": str(tmp_path / "home"), "USERPROFILE": str(tmp_path / "home"), "PYTHONUTF8": "1"}), \
            mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network disabled")), \
            mock.patch.object(subprocess, "Popen", side_effect=AssertionError("native disabled")):
        yield


def event(root, name, kind="tin", lane="phien-chinh", to="codex", ts=None, **extra):
    path = root / "hop_thu/su_kien" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"ts": (ts or NOW - timedelta(days=10)).isoformat(), "lane": lane, "kind": kind, "to": to, **extra}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path, data


def test_snapshot_exact_ids_does_not_ack_late_backdated_mail(tmp_path):
    assert store is not None
    event(tmp_path, "a.json")
    assert [r["id"] for r in store.unread_snapshot(tmp_path, "codex", "codex1")] == ["a.json"]
    event(tmp_path, "late.json", ts=NOW - timedelta(days=30))
    store.acknowledge_snapshot(tmp_path, "codex", "codex1", now=NOW - timedelta(days=5))
    assert [r["id"] for r in store.unread_snapshot(tmp_path, "codex", "codex1")] == ["late.json"]
    assert {r["id"] for r in store.unread_snapshot(tmp_path, "codex", "codex2")} == {"a.json", "late.json"}


def test_codex_reader_required_and_snapshot_hash_verified(tmp_path):
    assert store is not None
    with pytest.raises(ValueError):
        store.acknowledge_snapshot(tmp_path, "codex")
    path, data = event(tmp_path, "a.json")
    store.unread_snapshot(tmp_path, "codex", "codex1")
    path.write_text(json.dumps({**data, "text": "changed"}), encoding="utf-8")
    with pytest.raises(ValueError):
        store.acknowledge_snapshot(tmp_path, "codex", "codex1")


def test_archive_copies_before_unlink_and_preserves_board_history(tmp_path):
    assert store is not None
    event(tmp_path, "a.json", to="cloud-B")
    store.unread_snapshot(tmp_path, "cloud-B")
    store.acknowledge_snapshot(tmp_path, "cloud-B", now=NOW - timedelta(days=5))
    before = ht.render_board(ht.compute_state(ht.load_events(tmp_path)[0]), [])
    plan = store.archive(tmp_path, ht.compute_state(ht.load_events(tmp_path)[0]), now=NOW)
    assert plan["eligible"] == ["a.json"] and (tmp_path / "hop_thu/su_kien/a.json").exists()
    store.archive(tmp_path, ht.compute_state(ht.load_events(tmp_path)[0]), now=NOW, apply=True)
    assert not (tmp_path / "hop_thu/su_kien/a.json").exists()
    assert ht.render_board(ht.compute_state(ht.load_events(tmp_path)[0]), []) == before
    assert store.unread_snapshot(tmp_path, "cloud-B") == []


def test_unanswered_question_and_any_unacked_codex_reader_stay_raw(tmp_path):
    assert store is not None
    event(tmp_path, "q.json", kind="hoi", to="cloud-B")
    event(tmp_path, "a.json")
    for lane, reader in (("cloud-B", None), ("codex", "codex1"), ("codex", "codex2")):
        store.unread_snapshot(tmp_path, lane, reader)
        store.acknowledge_snapshot(tmp_path, lane, reader, now=NOW - timedelta(days=5))
    plan = store.archive(tmp_path, ht.compute_state(ht.load_events(tmp_path)[0]), now=NOW, apply=True)
    assert not plan["eligible"]
    assert (tmp_path / "hop_thu/su_kien/q.json").exists()
    assert (tmp_path / "hop_thu/su_kien/a.json").exists()


def test_archive_id_collision_and_broken_jsonl_are_reported(tmp_path):
    assert store is not None
    _, data = event(tmp_path, "a.json")
    folder = tmp_path / "hop_thu/luu_tru"
    folder.mkdir(parents=True)
    path = folder / "2026-10.jsonl"
    path.write_text(json.dumps({"id": "a.json", "event": data}) + "\n", encoding="utf-8")
    assert len(store.load_records(tmp_path)[0]) == 1
    path.write_text(json.dumps({"id": "a.json", "event": {**data, "text": "collision"}}) + "\n{broken\n", encoding="utf-8")
    assert len(store.load_records(tmp_path)[1]) == 2


def test_archive_fsync_failure_never_unlinks_source(tmp_path):
    assert store is not None
    event(tmp_path, "a.json", to="cloud-B")
    store.unread_snapshot(tmp_path, "cloud-B")
    store.acknowledge_snapshot(tmp_path, "cloud-B", now=NOW - timedelta(days=5))
    with mock.patch.object(store.os, "fsync", side_effect=OSError("fixture failure")), pytest.raises(OSError):
        store.archive(tmp_path, ht.compute_state(ht.load_events(tmp_path)[0]), now=NOW, apply=True)
    assert (tmp_path / "hop_thu/su_kien/a.json").exists()


@pytest.mark.parametrize("folder", ["hop_thu/luu_tru", "hop_thu/da_doc/cloud-B"])
def test_metadata_symlink_never_writes_outside(tmp_path, folder):
    event(tmp_path, "a.json", to="cloud-B")
    store.unread_snapshot(tmp_path, "cloud-B")
    if "luu_tru" in folder:
        store.acknowledge_snapshot(tmp_path, "cloud-B", now=NOW - timedelta(days=5))
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "sentinel").write_text("unchanged", encoding="utf-8")
    link = tmp_path / folder
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Windows không cấp quyền symlink")
    with pytest.raises(ValueError):
        if "luu_tru" in folder:
            store.archive(tmp_path, ht.compute_state(ht.load_events(tmp_path)[0]), now=NOW, apply=True)
        else:
            store.acknowledge_snapshot(tmp_path, "cloud-B")
    assert [p.name for p in outside.iterdir()] == ["sentinel"]
    assert (outside / "sentinel").read_text() == "unchanged"


def test_malformed_timestamp_never_echoes_its_content(tmp_path, capsys):
    event(tmp_path, "bad.json", ts=NOW)
    path = tmp_path / "hop_thu/su_kien/bad.json"
    row = json.loads(path.read_text())
    row["ts"] = "FIXTURE_PRIVATE_SENTINEL"
    path.write_text(json.dumps(row), encoding="utf-8")
    ht.main(["--goc", str(tmp_path), "bang"])
    output = capsys.readouterr()
    assert "FIXTURE_PRIVATE_SENTINEL" not in output.out + output.err
    assert "bad.json" in output.out + output.err


def test_legacy_all_unknown_is_visible_and_never_archived(tmp_path):
    event(tmp_path, "legacy.json", to="all")
    for lane, reader in (("codex", "codex1"), ("cloud-Z", None)):
        assert [row["id"] for row in store.unread_snapshot(tmp_path, lane, reader)] == ["legacy.json"]
        store.acknowledge_snapshot(tmp_path, lane, reader, now=NOW - timedelta(days=5))
    plan = store.archive(tmp_path, ht.compute_state(ht.load_events(tmp_path)[0]), now=NOW, apply=True)
    assert "legacy.json" in plan["held"] and not plan["eligible"]


def test_den_only_acknowledges_snapshot_prefix_and_receipt_is_immutable(tmp_path):
    event(tmp_path, "a.json", to="cloud-B")
    event(tmp_path, "b.json", to="cloud-B")
    store.unread_snapshot(tmp_path, "cloud-B")
    first = store.acknowledge_snapshot(tmp_path, "cloud-B", upto="a.json", now=NOW - timedelta(days=5))
    before = first[0].read_bytes()
    store.acknowledge_snapshot(tmp_path, "cloud-B", upto="a.json", now=NOW)
    assert first[0].read_bytes() == before
    assert [row["id"] for row in store.unread_snapshot(tmp_path, "cloud-B")] == ["b.json"]


def test_git_auth_paths_preserved_but_fake_api_keys_never_passed(tmp_path):
    fake = {"HOME": "fixture-home", "USERPROFILE": "fixture-user", "APPDATA": "fixture-appdata", "LOCALAPPDATA": "fixture-local",
            "PATH": "fixture-path", "CLIPAI_API_KEY": "fake-secret", "ANTHROPIC_API_KEY": "fake-secret", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_ALLOW_PROTOCOL": "file"}
    with mock.patch.object(os, "environ", fake):
        env = store.git_environment(tmp_path)
        assert env["HOME"] == "fixture-home" and env["APPDATA"] == "fixture-appdata"
        assert "CLIPAI_API_KEY" not in env and "ANTHROPIC_API_KEY" not in env
        assert env["GIT_ALLOW_PROTOCOL"] == "file"
        private = store._git_index_env(tmp_path, tmp_path / "index")
        assert private["HOME"] != env["HOME"] and private["GIT_CONFIG_GLOBAL"] == os.devnull


def test_fetch_pins_its_own_ref_even_if_fetch_head_changes(tmp_path):
    calls, refs = [], {}
    def git(root, *args, **kwargs):
        calls.append(args)
        if args[0] == "fetch":
            refs[args[-1].split(":", 1)[1]] = "a" * 40
        if args[0] == "rev-parse":
            assert args[1] != "FETCH_HEAD"
            return SimpleNamespace(stdout=refs[args[1]], returncode=0)
        return SimpleNamespace(stdout="", returncode=0)
    assert store._remote_files(tmp_path, git) == ("a" * 40, {})
    assert calls[-1][:2] == ("update-ref", "-d")


@pytest.mark.parametrize("failure", ["push", "verify"])
def test_failed_push_or_remote_verification_keeps_manifest(tmp_path, failure):
    path = ht.write_event(tmp_path, "phien-chinh", "tin", to="cloud-B", text="fixture")
    original = path.read_bytes()
    def git(root, *args, **kwargs):
        if args[0] == "push" and failure == "push" or args[0] == "merge-base" and failure == "verify":
            return SimpleNamespace(stdout="", returncode=1)
        return SimpleNamespace(stdout="b" * 40, returncode=0)
    with mock.patch.object(store, "_remote_files", return_value=("a" * 40, {})), pytest.raises(ValueError):
        store.flush_pending(tmp_path, git, tries=2)
    assert path.read_bytes() == original
    assert len(list((store.local_dir(tmp_path) / "pending").glob("*.json"))) == 1


def test_archive_retry_after_copy_before_unlink_is_lossless(tmp_path):
    path, _ = event(tmp_path, "a.json", to="cloud-B")
    store.unread_snapshot(tmp_path, "cloud-B")
    store.acknowledge_snapshot(tmp_path, "cloud-B", now=NOW - timedelta(days=5))
    state = ht.compute_state(ht.load_events(tmp_path)[0])
    original = Path.unlink
    def fail_source(target, *a, **kw):
        if target == path:
            raise OSError("fixture interrupted before unlink")
        return original(target, *a, **kw)
    with mock.patch.object(Path, "unlink", fail_source), pytest.raises(OSError):
        store.archive(tmp_path, state, now=NOW, apply=True)
    assert path.exists() and len(store.load_records(tmp_path)[0]) == 1
    store.archive(tmp_path, state, now=NOW, apply=True)
    assert not path.exists() and len(store.load_records(tmp_path)[0]) == 1


@pytest.mark.parametrize("folder", ["hop_thu/luu_tru", "hop_thu/da_doc/cloud-B"])
def test_metadata_ancestor_guard_runs_before_any_write(tmp_path, folder):
    event(tmp_path, "a.json", to="cloud-B")
    store.unread_snapshot(tmp_path, "cloud-B")
    if "luu_tru" in folder:
        store.acknowledge_snapshot(tmp_path, "cloud-B", now=NOW - timedelta(days=5))
    blocked = tmp_path / folder
    old = Path.is_symlink
    with mock.patch.object(Path, "is_symlink", lambda path: path == blocked or old(path)):
        with mock.patch.object(store, "atomic_bytes") as write, pytest.raises(ValueError):
            if "luu_tru" in folder:
                store.archive(tmp_path, ht.compute_state(ht.load_events(tmp_path)[0]), now=NOW, apply=True)
            else:
                store.acknowledge_snapshot(tmp_path, "cloud-B")
        write.assert_not_called()


def test_broken_display_does_not_save_an_unseen_snapshot(tmp_path):
    event(tmp_path, "a.json", to="cloud-B")
    class Broken(io.StringIO):
        def write(self, value):
            raise OSError("fixture display interrupted")
    with redirect_stdout(Broken()):
        assert ht.main(["--goc", str(tmp_path), "chua-doc", "--lane", "cloud-B"]) == 1
    assert not (store.local_dir(tmp_path) / "snapshots/cloud-B.json").exists()


def test_same_remote_blob_is_not_cat_filed_again_and_corrupt_cache_fails(tmp_path):
    content = b'{"ts":"2026-10-01T00:00:00+07:00","kind":"tin","lane":"phien-chinh","to":"cloud-B"}\n'
    oid = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    calls = []
    def git(root, *args, **kw):
        calls.append(args)
        if args[0] == "rev-parse":
            value = "a" * 40
        elif args[0] == "ls-tree":
            value = f"100644 blob {oid}\thop_thu/su_kien/a.json\0"
        elif args[0] == "cat-file":
            value = content
        else:
            value = ""
        return SimpleNamespace(stdout=value, returncode=0)
    assert store._remote_files(tmp_path, git) == store._remote_files(tmp_path, git)
    assert sum(args[0] == "cat-file" for args in calls) == 1
    (store.local_dir(tmp_path) / "blobs" / oid).write_bytes(b"fixture corrupt cache")
    with pytest.raises(ValueError):
        store._remote_files(tmp_path, git)


def test_board_all_closed_one_row_and_latest_news_with_explicit_holder(tmp_path):
    event(tmp_path, "a.json", kind="giao", task="A", to="codex")
    event(tmp_path, "b.json", kind="nhan", task="A", lane="codex", to="phien-chinh", reader="codex2", branch="codex/a")
    event(tmp_path, "c.json", task="A", lane="codex", to="phien-chinh", text="latest fixture")
    event(tmp_path, "d.json", kind="xong", task="A", lane="codex", to="phien-chinh", commit="abcdef1")
    event(tmp_path, "e.json", kind="gop", task="A", to="phien-chinh", commit="abcdef2")
    state = ht.compute_state(ht.load_events(tmp_path)[0])
    assert "| A |" not in ht.render_board(state, [])
    all_rows = ht.render_board(state, [], include_closed=True)
    assert all_rows.count("| A |") == 1 and "codex/codex2" in all_rows and "latest fixture" in all_rows


def test_flush_rechecks_ancestor_before_source_read_or_git(tmp_path):
    path, _ = event(tmp_path, "a.json", to="cloud-B")
    store.queue_path(tmp_path, path)
    blocked = tmp_path / "hop_thu/su_kien"
    old = Path.is_symlink
    original_read = Path.read_bytes
    with mock.patch.object(Path, "is_symlink", lambda p: p == blocked or old(p)), \
            mock.patch.object(store, "_remote_files") as remote, \
            mock.patch.object(Path, "read_bytes", autospec=True, side_effect=original_read) as read:
        with pytest.raises(ValueError):
            store.flush_pending(tmp_path, mock.Mock())
        assert all(call.args[0] != path for call in read.call_args_list)
        remote.assert_not_called()


@pytest.mark.parametrize("kind", ["hoi", "xong", "gop", "giao", "tin", "nhan", "bo", "tra_loi", "het_viec"])
@pytest.mark.parametrize("offline", [False, True])
def test_finish_dispatch_critical_only_and_explicit_offline(tmp_path, kind, offline):
    args = SimpleNamespace(push=False, khong_day=offline, lane="codex")
    path = tmp_path / "hop_thu/su_kien/a.json"
    with mock.patch.object(ht, "is_git_repo", return_value=True), mock.patch.object(ht, "git_push_event") as push:
        ht._finish(args, tmp_path, path, kind, "A")
    assert push.call_count == int(not offline and kind in {"hoi", "xong", "gop", "giao"})


def test_push_offline_mutually_exclusive_and_nongit_local(tmp_path, capsys):
    with pytest.raises(SystemExit):
        ht.build_parser().parse_args(["tin", "--lane", "codex", "--to", "all", "--text", "fixture", "--push", "--khong-day"])
    with mock.patch.object(ht, "is_git_repo", return_value=False), mock.patch.object(ht, "git_push_event") as push:
        ht._finish(SimpleNamespace(push=False, khong_day=False, lane="codex"), tmp_path,
                   tmp_path / "hop_thu/su_kien/a.json", "hoi", None)
    push.assert_not_called()
    assert "local" in capsys.readouterr().out


def test_explicit_push_ordinary_and_failed_auto_keeps_queue(tmp_path, capsys):
    with mock.patch.object(ht, "is_git_repo", return_value=True), mock.patch.object(ht, "git_push_event") as push:
        ht._finish(SimpleNamespace(push=True, khong_day=False, lane="codex"), tmp_path,
                   tmp_path / "hop_thu/su_kien/a.json", "tin", None)
        push.assert_called_once()
    capsys.readouterr()
    with mock.patch.object(ht, "is_git_repo", return_value=True), \
            mock.patch.object(ht, "git_push_event", side_effect=ht.HopThuError("fixture push failed")):
        assert ht.main(["--goc", str(tmp_path), "giao", "A", "--lane", "phien-chinh", "--to", "codex", "--title", "fixture"]) == 1
    assert list((store.local_dir(tmp_path) / "pending").glob("*.json"))
    assert "Đã gửi" not in capsys.readouterr().out
