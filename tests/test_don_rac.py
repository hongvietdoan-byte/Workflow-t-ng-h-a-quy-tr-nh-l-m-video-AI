# -*- coding: utf-8 -*-
"""Kiểm tra công cụ dọn trên thư mục và repo Git tạm, không dùng dữ liệu thật."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import don_rac  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(tmp_path, "clone", "-q", str(remote), str(seed))
    _git(seed, "config", "user.name", "test")
    _git(seed, "config", "user.email", "test@example.invalid")
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", "origin", "HEAD:main")
    _git(seed, "fetch", "-q", "origin")
    return seed, remote


def test_backup_rotation_moves_old_files_and_restores_by_journal_id(tmp_path):
    data = tmp_path / "data"
    archive = tmp_path / "_luu_tru" / "backup_cu"
    journal = tmp_path / "_luu_tru" / "nhat_ky_don_rac.jsonl"
    data.mkdir()
    backups = []
    for i in range(5):
        path = data / f"feature_settings.backup_202610{i + 1:02d}-120000.json"
        path.write_text(f"backup-{i}\n", encoding="utf-8")
        backups.append(path)

    result = don_rac.rotate_backups(data, archive, journal, keep=3, dry_run=False)

    assert result["moved"] == 2
    assert backups[-3] in [Path(item) for item in result["kept"]]
    records = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line]
    completed = [row for row in records if row.get("status") == "moved"]
    assert len(completed) == 2
    restore_id = completed[0]["id"]
    restored = don_rac.restore_item(restore_id, journal)
    assert Path(restored).is_file()
    assert Path(restored).read_text(encoding="utf-8").startswith("backup-")


def test_restore_refuses_to_overwrite_existing_original(tmp_path):
    source = tmp_path / "data" / "asset.bin"
    stored = tmp_path / "_luu_tru" / "asset.bin"
    source.parent.mkdir()
    stored.parent.mkdir()
    source.write_bytes(b"new")
    stored.write_bytes(b"old")
    journal = tmp_path / "_luu_tru" / "nhat_ky_don_rac.jsonl"
    journal.write_text(json.dumps({"id": "safe1", "action": "move", "status": "moved",
                                   "source": str(source), "stored": str(stored),
                                   "sha256": don_rac._sha256(stored)}) + "\n", encoding="utf-8")
    with pytest.raises(don_rac.SafetyError):
        don_rac.restore_item("safe1", journal, repo_root=tmp_path)
    assert source.read_bytes() == b"new"
    assert stored.read_bytes() == b"old"


def test_rotation_dry_run_does_not_move_files_or_write_journal(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for i in range(4):
        (data / f"manifest.backup_202610{i + 1:02d}-120000.sqlite").write_bytes(bytes([i]))
    journal = tmp_path / "journal.jsonl"
    result = don_rac.rotate_backups(data, tmp_path / "archive", journal, keep=3, dry_run=True)
    assert result["moved"] == 1
    assert len(list(data.glob("manifest.backup_*"))) == 4
    assert not journal.exists()


def test_rotation_never_touches_dashboard_env_backups(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    protected = data / "backup_dashboard.env.before_20261001"
    protected.write_text("fake-secret-marker", encoding="utf-8")
    for i in range(4):
        (data / f"feature_settings.backup_202610{i + 1:02d}-120000.json").write_text(str(i), encoding="utf-8")
    result = don_rac.rotate_backups(data, tmp_path / "archive", tmp_path / "journal.jsonl", keep=3, dry_run=False)
    assert result["moved"] == 1
    assert protected.read_text(encoding="utf-8") == "fake-secret-marker"
    assert list((tmp_path / "archive").rglob("backup_dashboard.env.before_20261001")) == []


def test_restore_branch_record_prints_recreate_command(tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text(json.dumps({"id": "br1", "action": "branch_removed", "status": "branch_deleted",
                                   "branch": "codex/old", "head": "0123456789abcdef"}) + "\n", encoding="utf-8")
    assert don_rac.restore_item("br1", journal).endswith("git branch codex/old 0123456789abcdef")


def test_directory_sizes_aggregates_nested_folders_and_skips_data(tmp_path):
    (tmp_path / "a" / "sub").mkdir(parents=True)
    (tmp_path / "b").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "a" / "one.bin").write_bytes(b"123")
    (tmp_path / "a" / "sub" / "two.bin").write_bytes(b"1234")
    (tmp_path / "b" / "three.bin").write_bytes(b"12")
    (tmp_path / "data" / "sensitive.bin").write_bytes(b"x" * 1000)

    sizes = {Path(path).relative_to(tmp_path).as_posix(): size
             for size, path in don_rac._directory_sizes(tmp_path)}

    assert sizes["a"] == 7
    assert sizes["a/sub"] == 4
    assert sizes["b"] == 2
    assert all(not path.startswith("data") for path in sizes)


@pytest.mark.parametrize("name", ["manifest.sqlite", "manifest.sqlite.backup_20261023.sqlite", "dashboard.env",
                                   "nested/dashboard.env", "backup_dashboard.env.before_20261023"])
def test_sensitive_files_are_never_accepted_for_backup(tmp_path, name):
    repo = tmp_path / "repo"
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("dummy only", encoding="utf-8")
    before = set(target.parent.iterdir())
    with pytest.raises(don_rac.SafetyError):
        don_rac.create_backup(target, kind="fixture", dry_run=False)
    assert set(target.parent.iterdir()) == before


def test_worktree_cleanup_removes_only_merged_old_codex_handoff(tmp_path):
    root, remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "old-handoff"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/old-handoff", str(wt), "origin/main")
    (wt / "HANDOFF.md").write_text("handoff", encoding="utf-8")
    old = datetime.now(timezone.utc).timestamp() - 5 * 86400
    os.utime(wt, (old, old))
    now = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp(), timezone.utc)

    dry = don_rac.cleanup_worktrees(root, dry_run=True, now=now)
    assert dry["candidates"] == 1
    assert wt.exists()

    archive = tmp_path / "archive" / "handoffs"
    journal = tmp_path / "_luu_tru" / "nhat_ky_don_rac.jsonl"
    done = don_rac.cleanup_worktrees(root, dry_run=False, now=now, archive_root=archive, journal=journal)
    assert done["removed"] == 1
    assert not wt.exists()
    assert "codex/old-handoff" not in _git(root, "branch", "--list")
    saved = list(archive.glob("*-HANDOFF.md"))
    assert len(saved) == 1 and saved[0].read_text(encoding="utf-8") == "handoff"
    assert len(list(archive.glob("nhat_ky_handoff.jsonl"))) == 1
    result_line = json.loads(journal.read_text(encoding="utf-8").splitlines()[-1])
    assert result_line["status"] == "branch_deleted"
    assert don_rac.restore_item(result_line["id"], journal).endswith(
        f"git branch codex/old-handoff {result_line['head']}"
    )


def test_worktree_cleanup_keeps_dirty_new_and_unmerged(tmp_path):
    root, _remote = _repo(tmp_path)
    old = datetime.now(timezone.utc).timestamp() - 5 * 86400

    dirty = root / ".codex-wt" / "dirty"
    dirty.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/dirty", str(dirty), "origin/main")
    (dirty / "code.py").write_text("uncommitted", encoding="utf-8")
    os.utime(dirty, (old, old))

    fresh = root / ".codex-wt" / "fresh"
    _git(root, "worktree", "add", "-b", "codex/fresh", str(fresh), "origin/main")

    locked = root / ".codex-wt" / "locked"
    _git(root, "worktree", "add", "-b", "codex/locked", str(locked), "origin/main")
    _git(root, "worktree", "lock", str(locked), "--reason", "fixture")
    os.utime(locked, (old, old))

    unmerged = root / ".codex-wt" / "unmerged"
    _git(root, "worktree", "add", "-b", "codex/unmerged", str(unmerged), "origin/main")
    (unmerged / "new.py").write_text("unmerged", encoding="utf-8")
    _git(unmerged, "add", "new.py")
    _git(unmerged, "commit", "-q", "-m", "unmerged")
    os.utime(unmerged, (old, old))

    result = don_rac.cleanup_worktrees(root, dry_run=False)
    assert result["removed"] == 0
    assert dirty.exists() and fresh.exists() and unmerged.exists() and locked.exists()


def test_quick_report_is_one_line_and_does_not_stop_processes_by_default(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(don_rac, "find_repo_root", lambda _path=None: tmp_path)
    monkeypatch.setattr(don_rac, "stop_redundant_servers", lambda *_a, **_k: 0)
    monkeypatch.setattr(don_rac, "stop_orphan_pytest", lambda *_a, **_k: 0)
    monkeypatch.setattr(don_rac, "cleanup_worktrees", lambda *_a, **_k: {
        "removed": 0, "candidates": 1, "plan": [{"path": str(tmp_path / "old"), "branch": "codex/old"}],
        "skipped": [],
    })
    rc = don_rac.main(["nhanh"])
    out = capsys.readouterr().out
    assert rc == 0
    assert len(out.splitlines()) == 1

    rc = don_rac.main(["--goc", str(tmp_path), "worktree"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Worktree: dry-run; đủ điều kiện 1; đã gỡ 0" in out
    assert f"Kế hoạch: {tmp_path / 'old'} | nhánh codex/old" in out


def test_gop_cleanup_failure_does_not_break_event_completion(tmp_path, monkeypatch):
    root, _remote = _repo(tmp_path)
    (root / "hop_thu" / "su_kien").mkdir(parents=True)
    # Thiết lập trạng thái XONG từ event, rồi kiểm lệnh gop vẫn ghi được event dù dọn lỗi.
    import json
    event_dir = root / "hop_thu" / "su_kien"
    (event_dir / "20261023-090000-codex-abcd.json").write_text(
        json.dumps({"ts": "2026-10-23T09:00:00+07:00", "lane": "codex", "kind": "giao",
                    "task": "CX22-T", "to": "codex", "title": "test"}), encoding="utf-8")
    (event_dir / "20261023-090001-codex-abce.json").write_text(
        json.dumps({"ts": "2026-10-23T09:00:01+07:00", "lane": "codex", "kind": "nhan",
                    "task": "CX22-T"}), encoding="utf-8")
    (event_dir / "20261023-090002-codex-abcf.json").write_text(
        json.dumps({"ts": "2026-10-23T09:00:02+07:00", "lane": "codex", "kind": "xong",
                    "task": "CX22-T", "branch": "codex/nonexistent", "commit": "abc123"}),
        encoding="utf-8")
    def fail_cleanup(*_args, **_kwargs):
        raise OSError("fixture")
    monkeypatch.setattr(don_rac, "cleanup_merged_branch_worktree", fail_cleanup, raising=False)
    rc, out, err = _run_hop_thu(root, "gop", "CX22-T", "--lane", "phien-chinh", "--commit", "def456")
    assert rc == 0, err
    assert "GỘP" in out or "Đã ghi" in out
    assert len(list(event_dir.glob("*.json"))) == 4


def test_gop_removes_clean_merged_worktree_and_local_branch(tmp_path, monkeypatch):
    journal = tmp_path / "_luu_tru" / "nhat_ky_don_rac.jsonl"
    monkeypatch.setattr(don_rac, "JOURNAL_PATH", journal)
    root, _remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "merged"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/merged", str(wt), "origin/main")
    _git(wt, "config", "user.name", "test")
    _git(wt, "config", "user.email", "test@example.invalid")
    (wt / "change.py").write_text("merged\n", encoding="utf-8")
    _git(wt, "add", "change.py")
    _git(wt, "commit", "-q", "-m", "feature")
    tip = _git(wt, "rev-parse", "HEAD")
    _git(root, "merge", "-q", "--no-ff", "codex/merged", "-m", "merge feature")
    _git(root, "push", "-q", "origin", "HEAD:main")
    _write_xong_events(root, "codex/merged", tip)

    rc, out, err = _run_hop_thu(root, "gop", "CX22-T", "--lane", "phien-chinh", "--commit", "merge-sha")
    assert rc == 0, err
    assert "đã gỡ worktree và nhánh local" in out
    assert not wt.exists()
    assert not _git(root, "branch", "--list", "codex/merged")
    record = json.loads(journal.read_text(encoding="utf-8").splitlines()[-1])
    assert record["action"] == "branch_removed"
    assert record["status"] == "branch_deleted"
    assert record["branch"] == "codex/merged"
    assert record["head"] == tip


def test_gop_giu_worktree_disables_automatic_cleanup(tmp_path):
    root, _remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "merged"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/merged", str(wt), "origin/main")
    _git(wt, "config", "user.name", "test")
    _git(wt, "config", "user.email", "test@example.invalid")
    (wt / "change.py").write_text("merged\n", encoding="utf-8")
    _git(wt, "add", "change.py")
    _git(wt, "commit", "-q", "-m", "feature")
    tip = _git(wt, "rev-parse", "HEAD")
    _git(root, "merge", "-q", "--no-ff", "codex/merged", "-m", "merge feature")
    _git(root, "push", "-q", "origin", "HEAD:main")
    _write_xong_events(root, "codex/merged", tip)

    rc, _out, err = _run_hop_thu(root, "gop", "CX22-T", "--lane", "phien-chinh",
                                 "--commit", "merge-sha", "--giu-worktree")
    assert rc == 0, err
    assert wt.exists()
    assert _git(root, "branch", "--list", "codex/merged")


def _write_xong_events(root: Path, branch: str, commit: str) -> None:
    event_dir = root / "hop_thu" / "su_kien"
    event_dir.mkdir(parents=True, exist_ok=True)
    base = "20261023-09000"
    events = [
        {"ts": "2026-10-23T09:00:00+07:00", "lane": "codex", "kind": "giao",
         "task": "CX22-T", "to": "codex", "title": "test"},
        {"ts": "2026-10-23T09:00:01+07:00", "lane": "codex", "kind": "nhan", "task": "CX22-T"},
        {"ts": "2026-10-23T09:00:02+07:00", "lane": "codex", "kind": "xong", "task": "CX22-T",
         "branch": branch, "commit": commit},
    ]
    for i, row in enumerate(events):
        (event_dir / f"{base}{i}-codex-{i:04x}.json").write_text(
            json.dumps(row), encoding="utf-8")


def _run_hop_thu(root: Path, *args: str) -> tuple[int, str, str]:
    import io
    from contextlib import redirect_stderr, redirect_stdout
    from tools import hop_thu
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = hop_thu.main(["--goc", str(root), *args])
    return rc, out.getvalue(), err.getvalue()
