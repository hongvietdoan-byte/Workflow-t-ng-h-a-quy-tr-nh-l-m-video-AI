# -*- coding: utf-8 -*-
"""Kiểm tra công cụ dọn trên thư mục và repo Git tạm, không dùng dữ liệu thật."""
from __future__ import annotations

import json
import os
import sqlite3
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


def _age_worktree_git_metadata(path: Path, timestamp: float) -> None:
    marker = path / ".git"
    assert marker.is_file()
    value = next(line[8:] for line in marker.read_text(encoding="utf-8").splitlines()
                 if line.startswith("gitdir: "))
    git_dir = Path(value)
    if not git_dir.is_absolute():
        git_dir = (path / git_dir).resolve()
    for relative in ("index", "HEAD", "logs/HEAD"):
        metadata = git_dir / relative
        if metadata.exists():
            os.utime(metadata, (timestamp, timestamp))


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
    # Mtime intentionally contradicts the timestamp embedded in each filename.
    base = datetime.now(timezone.utc).timestamp()
    for index, path in enumerate(backups):
        os.utime(path, (base + len(backups) - index, base + len(backups) - index))

    result = don_rac.rotate_backups(data, archive, journal, keep=3, dry_run=False)

    assert result["moved"] == 2
    assert set(map(Path, result["kept"])) == set(backups[-3:])
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


@pytest.mark.parametrize("name", ["manifest.sqlite.backup_20261023.sqlite", "dashboard.env",
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


def test_manifest_backup_uses_sqlite_online_backup_while_source_is_open(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    source = data / "manifest.sqlite"
    live_db = sqlite3.connect(source)
    live_db.execute("PRAGMA journal_mode=WAL")
    live_db.execute("CREATE TABLE fixture_items (id INTEGER PRIMARY KEY, value TEXT)")
    live_db.execute("INSERT INTO fixture_items(value) VALUES ('synthetic')")
    live_db.commit()

    result = don_rac.create_backup(source, dry_run=False, repo_root=tmp_path)

    assert result["created"] is True
    backup = sqlite3.connect(result["destination"])
    try:
        source_tables = live_db.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        backup_tables = backup.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        assert backup_tables == source_tables
        assert backup.execute("SELECT value FROM fixture_items").fetchall() == [("synthetic",)]
    finally:
        backup.close()
        live_db.close()


def test_manifest_backup_is_limited_to_canonical_repo_data_path(tmp_path):
    repo = tmp_path / "repo"
    source = repo / "config" / "manifest.sqlite"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic database placeholder")

    with pytest.raises(don_rac.SafetyError):
        don_rac.create_backup(source, dry_run=False, repo_root=repo)

    assert source.read_bytes() == b"synthetic database placeholder"
    assert list(source.parent.glob("manifest.backup_*.sqlite")) == []


def test_cli_allows_manifest_backup_through_the_scoped_guard(tmp_path, capsys):
    root, _remote = _repo(tmp_path)
    source = root / "data" / "manifest.sqlite"
    source.parent.mkdir()
    live_db = sqlite3.connect(source)
    live_db.execute("CREATE TABLE fixture_items (id INTEGER PRIMARY KEY)")
    live_db.commit()

    rc = don_rac.main([
        "--goc", str(root), "--output", str(tmp_path / "output"),
        "sao-luu", str(source),
    ])

    assert rc == 0
    assert "Sao lưu đã tạo" in capsys.readouterr().out
    backups = list(source.parent.glob("manifest.backup_*.sqlite"))
    assert len(backups) == 1
    copy_db = sqlite3.connect(backups[0])
    try:
        assert copy_db.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0] == 1
    finally:
        copy_db.close()
        live_db.close()


def test_manifest_is_still_rejected_by_move_guard(tmp_path):
    repo = tmp_path / "repo"
    source = repo / "data" / "manifest.sqlite"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic db placeholder")
    with pytest.raises(don_rac.SafetyError):
        don_rac._guard_path(source, repo)


def test_manifest_cannot_be_restored_from_move_archive(tmp_path):
    repo = tmp_path / "repo"
    source = repo / "data" / "manifest.sqlite"
    stored = tmp_path / "archive" / "manifest.sqlite"
    source.parent.mkdir(parents=True)
    stored.parent.mkdir(parents=True)
    source.write_bytes(b"source database placeholder")
    stored.write_bytes(b"archived placeholder")
    journal = tmp_path / "journal.jsonl"
    journal.write_text(json.dumps({
        "id": "manifest-move", "action": "move", "status": "moved",
        "source": str(source), "stored": str(stored), "sha256": don_rac._sha256(stored),
    }) + "\n", encoding="utf-8")

    with pytest.raises(don_rac.SafetyError):
        don_rac.restore_item("manifest-move", journal, repo_root=repo)
    assert source.read_bytes() == b"source database placeholder"
    assert stored.read_bytes() == b"archived placeholder"


def test_worktree_cleanup_removes_only_merged_old_codex_handoff(tmp_path):
    root, remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "old-handoff"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/old-handoff", str(wt), "origin/main")
    (wt / "HANDOFF.md").write_text("handoff", encoding="utf-8")
    old = datetime.now(timezone.utc).timestamp() - 5 * 86400
    _age_worktree_git_metadata(wt, old)
    os.utime(wt / "HANDOFF.md", (old, old))  # HANDOFF cũng phải cũ (> 3 ngày) mới được dọn
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


def test_gop_keeps_merged_worktree_with_ignored_data_file(tmp_path, monkeypatch):
    root, _remote = _repo(tmp_path)
    (root / ".gitignore").write_text("data/*.sqlite\n", encoding="utf-8")
    _git(root, "add", ".gitignore")
    _git(root, "commit", "-q", "-m", "ignore local sqlite fixtures")
    _git(root, "push", "-q", "origin", "HEAD:main")
    _git(root, "fetch", "-q", "origin")

    wt = root / ".codex-wt" / "merged-with-ignored-data"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/merged-with-ignored-data", str(wt), "origin/main")
    _git(wt, "config", "user.name", "test")
    _git(wt, "config", "user.email", "test@example.invalid")
    (wt / "change.py").write_text("merged\n", encoding="utf-8")
    _git(wt, "add", "change.py")
    _git(wt, "commit", "-q", "-m", "feature")
    tip = _git(wt, "rev-parse", "HEAD")
    ignored_db = wt / "data" / "x.sqlite"
    ignored_db.parent.mkdir()
    ignored_db.write_bytes(b"synthetic ignored data")
    _git(root, "merge", "-q", "--no-ff", "codex/merged-with-ignored-data", "-m", "merge feature")
    _git(root, "push", "-q", "origin", "HEAD:main")
    _write_xong_events(root, "codex/merged-with-ignored-data", tip)

    rc, _out, err = _run_hop_thu(root, "gop", "CX22-T", "--lane", "phien-chinh", "--commit", "merge-sha")

    assert rc == 0, err
    assert wt.exists()
    assert ignored_db.read_bytes() == b"synthetic ignored data"


def test_worktree_status_ignores_only_harmless_python_caches(tmp_path):
    root, _remote = _repo(tmp_path)
    (root / ".gitignore").write_text(
        ".pytest_cache/\n__pycache__/\n*.pyc\ndata/*.sqlite\n", encoding="utf-8"
    )
    _git(root, "add", ".gitignore")
    _git(root, "commit", "-q", "-m", "ignore local fixtures")
    _git(root, "push", "-q", "origin", "HEAD:main")
    _git(root, "fetch", "-q", "origin")
    wt = root / ".codex-wt" / "status-check"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/status-check", str(wt), "origin/main")
    (wt / ".pytest_cache").mkdir()
    (wt / ".pytest_cache" / "nodeids").write_text("fixture", encoding="utf-8")
    (wt / "src" / "__pycache__").mkdir(parents=True)
    (wt / "src" / "__pycache__" / "module.pyc").write_bytes(b"fixture")
    (wt / "src" / "__pycache__" / "payload.sqlite").write_bytes(b"synthetic ignored payload")
    (wt / "data").mkdir()
    (wt / "data" / "x.sqlite").write_bytes(b"synthetic ignored db")

    assert don_rac._worktree_status(wt) == [
        "!! data/x.sqlite", "!! src/__pycache__/payload.sqlite",
    ]


def test_worktree_cleanup_keeps_dirty_new_and_unmerged(tmp_path):
    root, _remote = _repo(tmp_path)
    old = datetime.now(timezone.utc).timestamp() - 5 * 86400

    dirty = root / ".codex-wt" / "dirty"
    dirty.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/dirty", str(dirty), "origin/main")
    (dirty / "code.py").write_text("uncommitted", encoding="utf-8")
    _age_worktree_git_metadata(dirty, old)

    fresh = root / ".codex-wt" / "fresh"
    _git(root, "worktree", "add", "-b", "codex/fresh", str(fresh), "origin/main")

    locked = root / ".codex-wt" / "locked"
    _git(root, "worktree", "add", "-b", "codex/locked", str(locked), "origin/main")
    _git(root, "worktree", "lock", str(locked), "--reason", "fixture")
    _age_worktree_git_metadata(locked, old)

    unmerged = root / ".codex-wt" / "unmerged"
    _git(root, "worktree", "add", "-b", "codex/unmerged", str(unmerged), "origin/main")
    (unmerged / "new.py").write_text("unmerged", encoding="utf-8")
    _git(unmerged, "add", "new.py")
    _git(unmerged, "commit", "-q", "-m", "unmerged")
    _age_worktree_git_metadata(unmerged, old)

    result = don_rac.cleanup_worktrees(root, dry_run=False)
    assert result["removed"] == 0
    assert dirty.exists() and fresh.exists() and unmerged.exists() and locked.exists()


def test_worktree_age_uses_latest_git_admin_metadata_mtime(tmp_path):
    root, _remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "age-check"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/age-check", str(wt), "origin/main")
    old = datetime.now(timezone.utc).timestamp() - 5 * 86400
    _age_worktree_git_metadata(wt, old)
    git_dir = Path(next(line[8:] for line in (wt / ".git").read_text(encoding="utf-8").splitlines()
                        if line.startswith("gitdir: ")))
    recent = datetime.now(timezone.utc).timestamp() - 3600
    os.utime(git_dir / "logs" / "HEAD", (recent, recent))
    os.utime(wt, (old, old))

    assert not don_rac._worktree_is_old(wt, 3, datetime.now(timezone.utc))

    _age_worktree_git_metadata(wt, old)
    assert don_rac._worktree_is_old(wt, 3, datetime.now(timezone.utc))


def test_find_repo_root_from_linked_worktree_returns_common_repo(tmp_path):
    root, _remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "root-check"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/root-check", str(wt), "origin/main")
    nested = wt / "nested"
    nested.mkdir()

    assert don_rac.find_repo_root(nested) == root.resolve()


def test_git_helper_sets_default_timeout_and_handles_timeout(tmp_path, monkeypatch):
    calls = []
    def complete(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "ok", "")
    monkeypatch.setattr(don_rac.subprocess, "run", complete)

    result = don_rac._git(tmp_path, "status")

    assert result.stdout == "ok"
    assert calls[0][1]["timeout"] == 60

    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])
    monkeypatch.setattr(don_rac.subprocess, "run", timeout)
    timed_out = don_rac._git(tmp_path, "fetch", check=False)
    assert timed_out.returncode == 124


def test_worktree_cleanup_fetches_pruned_remote_once(tmp_path, monkeypatch):
    root, _remote = _repo(tmp_path)
    original = don_rac._git
    fetch_calls = []
    def record_fetch(path, *args, **kwargs):
        if args == ("fetch", "--prune", "origin"):
            fetch_calls.append(args)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(don_rac, "_git", record_fetch)

    don_rac.cleanup_worktrees(root, dry_run=True)

    assert len(fetch_calls) == 1


def test_merged_worktree_cleanup_fetches_pruned_remote_once(tmp_path, monkeypatch):
    root, _remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "merged-fetch-check"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/merged-fetch-check", str(wt), "origin/main")
    _git(wt, "config", "user.name", "test")
    _git(wt, "config", "user.email", "test@example.invalid")
    (wt / "change.py").write_text("merged\n", encoding="utf-8")
    _git(wt, "add", "change.py")
    _git(wt, "commit", "-q", "-m", "feature")
    tip = _git(wt, "rev-parse", "HEAD")
    _git(root, "merge", "-q", "--no-ff", "codex/merged-fetch-check", "-m", "merge feature")
    _git(root, "push", "-q", "origin", "HEAD:main")
    original = don_rac._git
    fetch_calls = []
    def record_fetch(path, *args, **kwargs):
        if args == ("fetch", "--prune", "origin"):
            fetch_calls.append(args)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(don_rac, "_git", record_fetch)

    result = don_rac.cleanup_merged_branch_worktree(
        root, "codex/merged-fetch-check", tip, journal=tmp_path / "journal.jsonl"
    )

    assert len(fetch_calls) == 1
    assert "đã gỡ" in result


def test_stop_redundant_servers_respects_age_and_protected_ports(tmp_path, monkeypatch):
    from types import SimpleNamespace

    now = datetime.now(timezone.utc).timestamp()
    class FakeError(Exception):
        pass
    class FakeTimeout(FakeError):
        pass
    class FakeProcess:
        def __init__(self, pid, created):
            self.pid = pid
            self.created = created
            self.terminated = False
        def cmdline(self):
            return ["python", "-m", "streamlit", "run", "app.py", f"--server.port={ports[self.pid]}"]
        def create_time(self):
            return self.created
        def terminate(self):
            self.terminated = True
        def wait(self, timeout=None):
            return None

    ports = {1: 8501, 2: 8502, 3: 8503, 4: 8504, 5: 8505}
    processes = {
        1: FakeProcess(1, now - 2000), 2: FakeProcess(2, now - 2000),
        3: FakeProcess(3, now - 901), 4: FakeProcess(4, now - 899),
        5: FakeProcess(5, now - 2000),
    }
    connections = [SimpleNamespace(laddr=SimpleNamespace(port=port), pid=pid, status="LISTEN")
                   for pid, port in ports.items()]
    connections.append(SimpleNamespace(laddr=SimpleNamespace(port=8505), pid=5, status="ESTABLISHED"))
    class FakePsutil:
        Error = FakeError
        TimeoutExpired = FakeTimeout
        CONN_ESTABLISHED = "ESTABLISHED"
        CONN_LISTEN = "LISTEN"
        @staticmethod
        def net_connections(kind="tcp"):
            return connections
        @staticmethod
        def Process(pid):
            return processes[pid]

    monkeypatch.setattr(don_rac, "_processes", lambda: FakePsutil)

    stopped = don_rac.stop_redundant_servers(tmp_path)

    assert stopped == 1
    assert processes[3].terminated is True
    assert processes[1].terminated is False and processes[2].terminated is False
    assert processes[4].terminated is False and processes[5].terminated is False


def test_stop_orphan_pytest_requires_old_process_inside_repo(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc).timestamp()
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    class FakeError(Exception):
        pass
    class FakeNoSuchProcess(FakeError):
        pass
    class FakeTimeout(FakeError):
        pass
    class FakeProcess:
        def __init__(self, pid, created, cwd, ppid=404):
            self.info = {"pid": pid, "name": "python.exe", "cmdline": ["python", "-m", "pytest"], "ppid": ppid}
            self.created = created
            self.path = cwd
            self.terminated = False
        def create_time(self):
            return self.created
        def cwd(self):
            return str(self.path)
        def terminate(self):
            self.terminated = True
        def wait(self, timeout=None):
            return None

    old_inside = FakeProcess(1, now - 901, repo)
    recent_inside = FakeProcess(2, now - 899, repo)
    old_outside = FakeProcess(3, now - 901, outside)
    parent_alive = FakeProcess(4, now - 901, repo, ppid=42)
    processes = [old_inside, recent_inside, old_outside, parent_alive]
    class FakePsutil:
        Error = FakeError
        NoSuchProcess = FakeNoSuchProcess
        TimeoutExpired = FakeTimeout
        @staticmethod
        def process_iter(_attrs):
            return processes
        @staticmethod
        def Process(pid):
            if pid == 42:
                return object()
            raise FakeNoSuchProcess()

    monkeypatch.setattr(don_rac, "_processes", lambda: FakePsutil)

    stopped = don_rac.stop_orphan_pytest(repo)

    assert stopped == 1
    assert old_inside.terminated is True
    assert recent_inside.terminated is False
    assert old_outside.terminated is False
    assert parent_alive.terminated is False


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


# ---- Rà phiên chính 23/10 (CX22/CX23): hồi quy an toàn ----

def _merged_codex_worktree(root: Path, name: str) -> tuple[Path, str]:
    wt = root / ".codex-wt" / name
    wt.parent.mkdir(exist_ok=True)
    _git(root, "worktree", "add", "-b", f"codex/{name}", str(wt), "origin/main")
    _git(wt, "config", "user.name", "test")
    _git(wt, "config", "user.email", "test@example.invalid")
    (wt / f"{name}.py").write_text("merged\n", encoding="utf-8")
    _git(wt, "add", f"{name}.py")
    _git(wt, "commit", "-q", "-m", "feature")
    tip = _git(wt, "rev-parse", "HEAD")
    _git(root, "merge", "-q", "--no-ff", f"codex/{name}", "-m", "merge feature")
    _git(root, "push", "-q", "origin", "HEAD:main")
    return wt, tip


def test_merged_cleanup_accepts_short_commit_from_xong_event(tmp_path):
    # Sự kiện XONG thật hay ghi sha rút gọn (vd "2c4444b0"); so chuỗi thô làm việc dọn không bao giờ chạy.
    root, _remote = _repo(tmp_path)
    wt, tip = _merged_codex_worktree(root, "short-sha")
    journal = tmp_path / "_luu_tru" / "nhat_ky_don_rac.jsonl"

    result = don_rac.cleanup_merged_branch_worktree(root, "codex/short-sha", tip[:8], journal=journal)

    assert "đã gỡ worktree" in result
    assert not wt.exists()


def test_worktree_cleanup_never_removes_worktree_holding_cwd(tmp_path, monkeypatch):
    root, _remote = _repo(tmp_path)
    wt = root / ".claude" / "worktrees" / "agent-cwd"
    wt.parent.mkdir(parents=True)
    _git(root, "worktree", "add", "-b", "worktree-agent-cwd", str(wt), "origin/main")
    (wt / "sub").mkdir()
    _age_worktree_git_metadata(wt, datetime.now(timezone.utc).timestamp() - 5 * 86400)
    monkeypatch.chdir(wt / "sub")

    result = don_rac.cleanup_worktrees(root, dry_run=True)

    assert result["candidates"] == 0
    assert any(item["reason"] == "worktree đang chạy lệnh" for item in result["skipped"])


def test_merged_cleanup_never_removes_worktree_holding_cwd(tmp_path, monkeypatch):
    root, _remote = _repo(tmp_path)
    wt, tip = _merged_codex_worktree(root, "cwd-merged")
    monkeypatch.chdir(wt)

    result = don_rac.cleanup_merged_branch_worktree(
        root, "codex/cwd-merged", tip, journal=tmp_path / "j.jsonl")

    assert result.startswith("bỏ qua")
    assert wt.exists()


def test_codex_handoff_edited_recently_keeps_worktree(tmp_path):
    root, _remote = _repo(tmp_path)
    wt = root / ".codex-wt" / "active-handoff"
    wt.parent.mkdir()
    _git(root, "worktree", "add", "-b", "codex/active-handoff", str(wt), "origin/main")
    (wt / "HANDOFF.md").write_text("đang ghi", encoding="utf-8")
    _age_worktree_git_metadata(wt, datetime.now(timezone.utc).timestamp() - 5 * 86400)

    result = don_rac.cleanup_worktrees(root, dry_run=True)

    assert result["candidates"] == 0


def test_gop_keeps_worktree_while_sibling_task_on_same_branch_unmerged(tmp_path, monkeypatch):
    # CX22-DON-RAC-TOOL và CX23-DON-RAC-FIX dùng chung nhánh: gộp việc đầu không được gỡ chỗ việc sau đang làm.
    monkeypatch.setattr(don_rac, "JOURNAL_PATH", tmp_path / "_luu_tru" / "j.jsonl")
    root, _remote = _repo(tmp_path)
    wt, tip = _merged_codex_worktree(root, "shared")
    _write_xong_events(root, "codex/shared", tip)
    event_dir = root / "hop_thu" / "su_kien"
    for i, row in enumerate([
        {"ts": "2026-10-23T09:10:00+07:00", "lane": "codex", "kind": "giao",
         "task": "CX23-T", "to": "codex", "title": "fix"},
        {"ts": "2026-10-23T09:10:01+07:00", "lane": "codex", "kind": "nhan", "task": "CX23-T"},
        {"ts": "2026-10-23T09:10:02+07:00", "lane": "codex", "kind": "xong", "task": "CX23-T",
         "branch": "codex/shared", "commit": tip},
    ]):
        (event_dir / f"20261023-09100{i}-codex-b{i:03x}.json").write_text(json.dumps(row), encoding="utf-8")

    rc, out, err = _run_hop_thu(root, "gop", "CX22-T", "--lane", "phien-chinh", "--commit", "merge-sha")

    assert rc == 0, err
    assert wt.exists()
    assert "CX23-T" in out


@pytest.mark.skipif(os.name != "nt", reason="junction chỉ có trên Windows")
def test_directory_sizes_does_not_follow_junctions(tmp_path):
    import _winapi
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "f.bin").write_bytes(b"12345")
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"x" * 999)
    _winapi.CreateJunction(str(outside), str(tmp_path / "link"))

    sizes = {Path(path).name: size for size, path in don_rac._directory_sizes(tmp_path)}

    assert sizes == {"a": 5}


def test_rotation_continues_when_one_backup_is_locked(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    for kind in ("alpha", "beta"):
        for i in range(4):
            (data / f"{kind}.backup_202610{i + 1:02d}-120000.json").write_text(kind, encoding="utf-8")
    real_move = don_rac.shutil.move

    def locked_move(src, dst):
        if Path(src).name.startswith("alpha"):
            raise PermissionError("file đang bị giữ")
        return real_move(src, dst)

    monkeypatch.setattr(don_rac.shutil, "move", locked_move)
    result = don_rac.rotate_backups(data, tmp_path / "arch", tmp_path / "j.jsonl", keep=3, dry_run=False)

    assert result["moved"] == 1
    assert (data / "alpha.backup_20261001-120000.json").exists()
    assert not (data / "beta.backup_20261001-120000.json").exists()
    assert result["failed"] and "alpha" in result["failed"][0][0]
