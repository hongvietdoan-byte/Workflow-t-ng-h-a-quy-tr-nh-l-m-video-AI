# -*- coding: utf-8 -*-
"""Công cụ dọn an toàn cho worktree và bản sao lưu của AI-Video-Pipeline.

Mọi thao tác chuyển/xóa đều dry-run mặc định. Không hỗ trợ sửa hoặc sao lưu dữ liệu
nhạy cảm của pipeline (manifest.sqlite, dashboard.env, projects, models3d, plates3d).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SafetyError(ValueError):
    """Từ chối thao tác vượt vùng an toàn."""


JOURNAL_PATH = Path(r"D:\AI-Video-Output\_luu_tru\nhat_ky_don_rac.jsonl")


def find_repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    try:
        common_dir = Path(_git(here, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        root = common_dir.resolve().parent
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise SafetyError(f"Không tìm thấy gốc Git từ {here}.") from exc
    if not (root / ".git").exists():
        raise SafetyError(f"Không tìm thấy gốc Git từ {here}.")
    return root


def _git(
    root: Path, *args: str, check: bool = True, timeout: float = 60,
) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    try:
        result = subprocess.run(
            command, cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        detail = f"vượt quá {timeout:g} giây"
        if check:
            raise RuntimeError(f"git {args[0] if args else ''} {detail}.") from exc
        return subprocess.CompletedProcess(command, 124, "", detail)
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"git {args[0] if args else ''} lỗi: {detail}")
    return result


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _guard_path(
    path: Path, repo_root: Path | None = None, *, allow_manifest_backup: bool = False,
) -> Path:
    target = path.expanduser().resolve()
    lowered = [part.casefold() for part in target.parts]
    if target.name.casefold() == "dashboard.env" or "dashboard.env" in target.name.casefold():
        raise SafetyError("Từ chối: dashboard.env luôn nằm ngoài phạm vi công cụ.")
    canonical_manifest = False
    if allow_manifest_backup and repo_root is not None:
        expected = (Path(repo_root).resolve() / "data" / "manifest.sqlite").resolve()
        canonical_manifest = os.path.normcase(str(target)) == os.path.normcase(str(expected))
    if target.name.casefold().startswith("manifest.sqlite") and not canonical_manifest:
        raise SafetyError("Từ chối: manifest.sqlite luôn nằm ngoài phạm vi công cụ.")
    protected_dirs = {"projects", "models3d", "_plates3d", ".codex-runtime"}
    if any(part in protected_dirs for part in lowered):
        raise SafetyError("Từ chối: đường dẫn thuộc vùng dữ liệu được bảo vệ.")
    if repo_root is not None:
        root = repo_root.resolve()
        # Không cho công cụ thao tác vào repo khác hoặc thư mục tùy ý.
        if not _inside(target, root):
            raise SafetyError("Từ chối: đường dẫn phải nằm trong repo được chỉ định.")
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _append_journal(journal: Path, record: dict[str, Any]) -> None:
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def create_backup(
    source: Path,
    kind: str | None = None,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
    journal: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Tạo bản sao cạnh file nguồn; không bao giờ ghi đè bản sao đã có."""
    source = Path(source).expanduser().resolve()
    is_manifest = (
        repo_root is not None
        and os.path.normcase(str(source)) == os.path.normcase(
            str((Path(repo_root).resolve() / "data" / "manifest.sqlite").resolve())
        )
    )
    source = _guard_path(source, repo_root, allow_manifest_backup=is_manifest)
    if not source.is_file():
        raise SafetyError("Tệp nguồn không tồn tại hoặc không phải tệp thường.")
    stamp = (now or datetime.now(timezone.utc)).astimezone().strftime("%Y%m%d-%H%M%S")
    label = (kind or source.stem).strip()
    if not label or any(c in label for c in "\\/:*?\"<>|\r\n") or label in (".", ".."):
        raise SafetyError("Tên loại bản sao lưu không hợp lệ.")
    suffix = source.suffix
    destination = source.with_name(f"{label}.backup_{stamp}{suffix}")
    if destination.exists():
        raise SafetyError("Bản sao lưu cùng tên đã tồn tại; không ghi đè.")
    record = {
        "id": uuid.uuid4().hex[:12], "action": "backup", "kind": label,
        "source": str(source), "stored": str(destination),
        "bytes": source.stat().st_size, "ts": datetime.now(timezone.utc).isoformat(),
    }
    if dry_run:
        record["sha256"] = _sha256(source)
        return {"created": False, "source": str(source), "destination": str(destination), "record": record}
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        if is_manifest:
            source_db = sqlite3.connect(str(source))
            try:
                destination_db = sqlite3.connect(str(temporary))
                try:
                    source_db.backup(destination_db)
                finally:
                    destination_db.close()
            finally:
                source_db.close()
        else:
            source_digest = _sha256(source)
            shutil.copy2(source, temporary)
            if _sha256(temporary) != source_digest:
                raise OSError("SHA-256 bản sao không khớp nguồn; đã hủy.")
        record["sha256"] = _sha256(temporary)
        record["bytes"] = temporary.stat().st_size
        os.replace(temporary, destination)
        if journal:
            _append_journal(journal, record)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"created": True, "source": str(source), "destination": str(destination), "record": record}


def _backup_kind(path: Path) -> str | None:
    name = path.name.casefold()
    if "dashboard.env" in name:
        return None
    if ".backup_" in name:
        return name.split(".backup_", 1)[0]
    if name.startswith("backup_") and ".before_" in name:
        return name.split(".before_", 1)[0]
    return None


_BACKUP_TIMESTAMP = re.compile(r"(?<!\d)(20\d{6})(?:[-_]?([0-2]\d[0-5]\d[0-5]\d))?(?!\d)")


def _backup_sort_key(path: Path) -> tuple[float, str]:
    match = _BACKUP_TIMESTAMP.search(path.name)
    if match:
        date, clock = match.groups()
        try:
            embedded = datetime.strptime(date + (clock or "000000"), "%Y%m%d%H%M%S")
            return embedded.timestamp(), path.name.casefold()
        except ValueError:
            pass
    return path.stat().st_ctime, path.name.casefold()


def rotate_backups(
    data_root: Path,
    archive_root: Path,
    journal: Path,
    *,
    keep: int = 3,
    dry_run: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Giữ N bản mới nhất mỗi loại; chuyển bản cũ vào kho, không xóa."""
    data_root = Path(data_root).resolve()
    archive_root = Path(archive_root).resolve()
    journal = Path(journal).resolve()
    if keep < 1:
        raise SafetyError("--giu phải ít nhất là 1.")
    if not data_root.is_dir():
        raise SafetyError("Thư mục nguồn không tồn tại.")
    groups: dict[str, list[Path]] = {}
    for candidate in data_root.iterdir():
        kind = _backup_kind(candidate)
        if kind and candidate.is_file():
            try:
                _guard_path(candidate, data_root.parent)
            except SafetyError:
                continue
            groups.setdefault(kind, []).append(candidate)
    stamp_day = (now or datetime.now(timezone.utc)).astimezone().strftime("%Y-%m-%d")
    move_plan: list[tuple[Path, Path]] = []
    kept: list[str] = []
    for kind, paths in sorted(groups.items()):
        ordered = sorted(paths, key=_backup_sort_key, reverse=True)
        kept.extend(str(p) for p in ordered[:keep])
        for source in ordered[keep:]:
            destination = archive_root / stamp_day / source.name
            if destination.exists():
                destination = destination.with_name(f"{destination.stem}-{uuid.uuid4().hex[:6]}{destination.suffix}")
            move_plan.append((source, destination))
    moved: list[str] = []
    failed: list[tuple[str, str]] = []
    for source, destination in move_plan:
        if dry_run:
            continue
        _guard_path(source, data_root.parent)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            digest = _sha256(source)
            size = source.stat().st_size
        except OSError as exc:
            failed.append((str(source), str(exc)))
            continue
        record = {
            "id": uuid.uuid4().hex[:12], "action": "move", "status": "planned", "kind": _backup_kind(source),
            "source": str(source), "stored": str(destination), "sha256": digest,
            "bytes": size, "ts": datetime.now(timezone.utc).isoformat(),
        }
        _append_journal(journal, record)
        try:
            shutil.move(str(source), str(destination))
        except OSError as exc:
            # File đang bị giữ (Windows) → bỏ qua file này, các file khác vẫn xoay; ghi nhật ký thất bại.
            record["status"] = "failed"
            record["error"] = str(exc)
            _append_journal(journal, record)
            failed.append((str(source), str(exc)))
            continue
        if _sha256(destination) != digest:
            # Preserve evidence; do not delete destination on mismatch.
            raise OSError(f"SHA-256 sau khi chuyển không khớp: {destination.name}")
        record["status"] = "moved"
        _append_journal(journal, record)
        moved.append(record["id"])
    return {
        "moved": len(move_plan) if dry_run else len(moved), "ids": moved,
        "kept": kept, "plan": [(str(a), str(b)) for a, b in move_plan], "dry_run": dry_run,
        "failed": failed,
    }


def restore_item(item_id: str, journal: Path, *, repo_root: Path | None = None) -> str:
    """Khôi phục một mục đã chuyển; không ghi đè file đích và kiểm SHA trước."""
    journal = Path(journal).resolve()
    if not journal.is_file():
        raise SafetyError("Không tìm thấy nhật ký khôi phục.")
    selected = None
    for line in journal.read_text(encoding="utf-8-sig").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("id") == item_id:
            selected = row
    if not selected:
        raise SafetyError("Không tìm thấy mã trong nhật ký.")
    if selected.get("action") == "branch_removed":
        branch = str(selected.get("branch") or "")
        head = str(selected.get("head") or "")
        if not branch or not head:
            raise SafetyError("Bản ghi nhánh thiếu tên hoặc commit.")
        if selected.get("status") != "branch_deleted":
            return f"Nhánh local {branch} chưa bị xóa; không cần tạo lại. Trạng thái: {selected.get('status', 'không rõ')}"
        return f"Nhánh local đã bị gỡ. Khôi phục bằng: git branch {branch} {head}"
    source = Path(selected["source"]).resolve()
    stored = Path(selected["stored"]).resolve()
    if selected.get("action") != "move":
        raise SafetyError("Chỉ khôi phục mục đã chuyển; bản sao lưu vẫn còn cạnh nguồn.")
    _guard_path(source, repo_root)
    if not _inside(stored, journal.parent):
        raise SafetyError("Từ chối: tệp lưu trữ nằm ngoài thư mục nhật ký.")
    if not stored.is_file():
        raise SafetyError("Không tìm thấy tệp đã chuyển.")
    if source.exists():
        raise SafetyError("Đường dẫn gốc đã có tệp; từ chối ghi đè.")
    if _sha256(stored) != selected.get("sha256"):
        raise SafetyError("SHA-256 không khớp nhật ký; không khôi phục.")
    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stored), str(source))
    return str(source)


def _porcelain_worktrees(root: Path) -> list[dict[str, Any]]:
    raw = _git(root, "worktree", "list", "--porcelain").stdout
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in raw.splitlines() + [""]:
        if not line:
            if current:
                rows.append(current)
                current = {}
        elif line.startswith("worktree "):
            current["path"] = Path(line[9:]).resolve()
        elif line.startswith("HEAD "):
            current["head"] = line[5:].strip()
        elif line.startswith("branch "):
            value = line[7:].strip()
            current["branch"] = value[len("refs/heads/"):] if value.startswith("refs/heads/") else value
        elif line == "locked" or line.startswith("locked "):
            current["locked"] = True
        elif line == "prunable" or line.startswith("prunable "):
            current["prunable"] = True
    return rows


def _worktree_status(path: Path) -> list[str]:
    result = _git(path, "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--ignored", check=False)
    if result.returncode:
        return ["<không đọc được git status>"]
    status: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        code, _, raw_path = line.partition(" ")
        path_text = raw_path.strip().strip('"').replace("\\", "/").rstrip("/")
        parts = {part.casefold() for part in path_text.split("/") if part}
        harmless = ".pytest_cache" in parts or (
            "__pycache__" in parts
            and path_text.casefold().endswith(".pyc")
        )
        if code == "!!" and not harmless and "__pycache__" in parts:
            cache_path = (path / Path(path_text)).resolve()
            if _inside(cache_path, path) and cache_path.is_dir():
                contents = list(cache_path.rglob("*"))
                harmless = all(
                    item.is_dir() or (item.is_file() and item.suffix.casefold() == ".pyc")
                    for item in contents
                )
        if code == "!!" and harmless:
            continue
        status.append(line)
    return status


def _worktree_is_old(path: Path, days: int, now: datetime) -> bool:
    try:
        marker = path / ".git"
        if marker.is_file():
            git_dir_text = next(
                (line[8:] for line in marker.read_text(encoding="utf-8").splitlines()
                 if line.startswith("gitdir: ")),
                None,
            )
            if not git_dir_text:
                return False
            git_dir = Path(git_dir_text)
            if not git_dir.is_absolute():
                git_dir = (path / git_dir).resolve()
        elif marker.is_dir():
            git_dir = marker
        else:
            return False
        metadata = [git_dir / name for name in ("index", "HEAD", "logs/HEAD")]
        timestamps = [item.stat().st_mtime for item in metadata if item.is_file()]
        if not timestamps:
            return False
        age = now.timestamp() - max(timestamps)
    except (OSError, StopIteration):
        return False
    return age > days * 86400


def _holds_cwd(path: Path) -> bool:
    """True nếu tiến trình đang đứng trong worktree này (kể cả thư mục con)."""
    try:
        return _inside(Path.cwd(), path)
    except OSError:
        return True


def _worktree_candidate(root: Path, row: dict[str, Any], now: datetime, current: Path) -> tuple[bool, str]:
    path = row.get("path")
    branch = row.get("branch")
    if not path or not branch:
        return False, "detached hoặc thiếu đường dẫn"
    allowed = (root / ".claude" / "worktrees", root / ".codex-wt")
    if not any(_inside(path, base) and path != base.resolve() for base in allowed):
        return False, "ngoài thư mục worktree được phép"
    if row.get("locked") or row.get("prunable"):
        return False, "worktree bị khóa hoặc prunable"
    if path == current or _holds_cwd(path):
        return False, "worktree đang chạy lệnh"
    is_codex = path.parent.name.casefold() == ".codex-wt" or branch.startswith("codex/")
    days = 3 if is_codex else 1
    if not _worktree_is_old(path, days, now):
        return False, f"chưa quá {days} ngày"
    status = _worktree_status(path)
    if status:
        if not (is_codex and len(status) == 1 and status[0].replace("\\", "/") == "?? HANDOFF.md"):
            return False, "có thay đổi chưa commit"
        # HANDOFF.md chưa theo dõi không làm đổi index: tuổi worktree phải tính cả lần sửa HANDOFF.
        try:
            handoff_age = now.timestamp() - (path / "HANDOFF.md").stat().st_mtime
        except OSError:
            return False, "không đọc được HANDOFF.md"
        if handoff_age <= days * 86400:
            return False, f"HANDOFF.md sửa chưa quá {days} ngày"
    head = row.get("head") or _git(path, "rev-parse", "HEAD").stdout.strip()
    main_ancestor = _git(root, "merge-base", "--is-ancestor", head, "origin/main", check=False).returncode == 0
    remote_contains = bool(_git(root, "branch", "-r", "--contains", head, check=False).stdout.strip())
    if not (main_ancestor or remote_contains):
        return False, "HEAD chưa có trên origin/main hoặc nhánh remote"
    return True, "đủ điều kiện"


def cleanup_worktrees(
    root: Path,
    *,
    dry_run: bool = True,
    now: datetime | None = None,
    archive_root: Path | None = None,
    journal: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    fetched = _git(root, "fetch", "--prune", "origin", check=False)
    if fetched.returncode:
        return {
            "candidates": 0, "removed": 0, "plan": [],
            "skipped": [{"path": str(root), "branch": "", "reason": "không fetch được origin; bỏ qua rà dọn"}],
            "dry_run": dry_run,
        }
    current = Path(_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    candidates: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    removed = 0
    for row in _porcelain_worktrees(root):
        eligible, reason = _worktree_candidate(root, row, now, current)
        item = {"path": str(row.get("path", "")), "branch": str(row.get("branch", "")), "reason": reason}
        if not eligible:
            skipped.append(item)
            continue
        candidates.append(item)
        if dry_run:
            continue
        path = Path(item["path"]).resolve()
        branch = item["branch"]
        # Check path containment again immediately before the destructive operation.
        if not any(_inside(path, (root / suffix)) for suffix in (".claude/worktrees", ".codex-wt")):
            skipped.append({**item, "reason": "đường dẫn đổi ngoài vùng cho phép"})
            continue
        status = _worktree_status(path)
        force = bool(status)  # Chỉ trạng thái duy nhất được phép là ?? HANDOFF.md của Codex.
        if force:
            handoff = path / "HANDOFF.md"
            if status != ["?? HANDOFF.md"] or not handoff.is_file():
                skipped.append({**item, "reason": "trạng thái thay đổi sau khi rà; không đụng worktree"})
                continue
            archive = Path(archive_root).resolve() if archive_root else root / "_luu_tru" / "handoff_codex"
            archive.mkdir(parents=True, exist_ok=True)
            head = _git(path, "rev-parse", "HEAD").stdout.strip()[:8]
            safe_branch = "".join(c if c.isalnum() or c in "-_." else "_" for c in branch)
            stored = archive / f"{safe_branch}-{head}-HANDOFF.md"
            if stored.exists():
                skipped.append({**item, "reason": "bản lưu HANDOFF cùng tên đã tồn tại"})
                continue
            digest = _sha256(handoff)
            try:
                shutil.copy2(handoff, stored)
                if _sha256(stored) != digest:
                    skipped.append({**item, "reason": "SHA-256 HANDOFF sau sao lưu không khớp"})
                    continue
                _append_journal(archive / "nhat_ky_handoff.jsonl", {
                    "id": uuid.uuid4().hex[:12], "source": str(handoff), "stored": str(stored),
                    "sha256": digest, "branch": branch, "head": head,
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
            except OSError as exc:
                skipped.append({**item, "reason": f"không lưu được HANDOFF: {exc}"})
                continue
        head = _git(path, "rev-parse", "HEAD").stdout.strip()
        branch_record = {
            "id": uuid.uuid4().hex[:12], "action": "branch_removed", "status": "planned",
            "branch": branch, "head": head, "worktree": str(path),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if journal:
            _append_journal(Path(journal), branch_record)
        result = _git(root, "worktree", "remove", *( ["--force"] if force else []), str(path), check=False)
        if result.returncode:
            if journal:
                branch_record["status"] = "worktree_kept"
                _append_journal(Path(journal), branch_record)
            skipped.append({**item, "reason": (result.stderr or result.stdout).strip() or "gỡ worktree thất bại"})
            continue
        branch_record["status"] = "worktree_removed"
        if journal:
            _append_journal(Path(journal), branch_record)
        branch_result = _git(root, "branch", "-d", branch, check=False)
        if branch_result.returncode:
            if journal:
                branch_record["status"] = "branch_kept"
                _append_journal(Path(journal), branch_record)
            skipped.append({**item, "reason": (branch_result.stderr or branch_result.stdout).strip() or "không xóa được nhánh local"})
            continue
        branch_record["status"] = "branch_deleted"
        if journal:
            _append_journal(Path(journal), branch_record)
        removed += 1
    return {"candidates": len(candidates), "removed": removed, "plan": candidates, "skipped": skipped, "dry_run": dry_run}


def cleanup_merged_branch_worktree(
    root: Path,
    branch: str,
    merged_commit: str,
    *,
    journal: Path | None = None,
) -> str:
    """Gỡ worktree local sạch sau khi commit của nhánh đã vào origin/main."""
    root = Path(root).resolve()
    if not branch or branch.startswith("-") or not merged_commit or merged_commit.startswith("-"):
        return "bỏ qua: thiếu nhánh hoặc commit"
    fetched = _git(root, "fetch", "--prune", "origin", check=False)
    if fetched.returncode:
        return "bỏ qua: không cập nhật được origin/main để kiểm tra an toàn"
    # Sự kiện XONG có thể ghi sha rút gọn: chuẩn hóa thành sha đầy đủ trước khi so với HEAD worktree.
    resolved = _git(root, "rev-parse", "--verify", "--quiet", f"{merged_commit}^{{commit}}", check=False)
    if resolved.returncode or not resolved.stdout.strip():
        return "bỏ qua: không xác định được commit báo XONG"
    merged_commit = resolved.stdout.strip()
    contained = _git(root, "merge-base", "--is-ancestor", merged_commit, "origin/main", check=False)
    if contained.returncode:
        return "bỏ qua: commit nhánh chưa nằm trong origin/main"
    row = next((r for r in _porcelain_worktrees(root) if r.get("branch") == branch), None)
    if row is None:
        return "không có worktree local cho nhánh"
    path = row.get("path")
    if not path or row.get("locked") or row.get("prunable"):
        return "bỏ qua: worktree thiếu đường dẫn, bị khóa hoặc prunable"
    allowed = (root / ".claude" / "worktrees", root / ".codex-wt")
    if not any(_inside(path, base) and path != base.resolve() for base in allowed):
        return "bỏ qua: worktree nằm ngoài vùng được phép"
    current = Path(_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if path == current or _holds_cwd(path):
        return "bỏ qua: đang đứng trong worktree mục tiêu"
    head = _git(path, "rev-parse", "HEAD", check=False).stdout.strip()
    if head != merged_commit:
        return "bỏ qua: HEAD worktree đã khác commit báo XONG"
    if _worktree_status(path):
        return "bỏ qua: worktree có thay đổi chưa commit"
    journal = Path(journal or JOURNAL_PATH)
    record = {
        "id": uuid.uuid4().hex[:12], "action": "branch_removed", "status": "planned",
        "branch": branch, "head": head, "worktree": str(path),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _append_journal(journal, record)
    remove = _git(root, "worktree", "remove", str(path), check=False)
    if remove.returncode:
        record["status"] = "worktree_kept"
        _append_journal(journal, record)
        return f"cảnh báo: không gỡ được worktree ({(remove.stderr or remove.stdout).strip()})"
    record["status"] = "worktree_removed"
    _append_journal(journal, record)
    delete = _git(root, "branch", "-d", branch, check=False)
    if delete.returncode:
        record["status"] = "branch_kept"
        _append_journal(journal, record)
        return f"cảnh báo: worktree đã gỡ nhưng giữ nhánh local ({(delete.stderr or delete.stdout).strip()})"
    record["status"] = "branch_deleted"
    _append_journal(journal, record)
    return "đã gỡ worktree và nhánh local; không xóa nhánh remote"


def _processes() -> Any:
    try:
        import psutil  # type: ignore[import-not-found]
    except ImportError:
        return None
    return psutil


def stop_redundant_servers(_root: Path) -> int:
    """Dừng Streamlit listener thừa trên 8503–8510 khi không có ESTABLISHED client."""
    psutil = _processes()
    if psutil is None:
        return 0
    stopped = 0
    try:
        connections = psutil.net_connections(kind="tcp")
    except (OSError, psutil.Error):
        return 0
    established_ports = {c.laddr.port for c in connections if c.status == psutil.CONN_ESTABLISHED and c.laddr}
    listening = {c.laddr.port: c.pid for c in connections if c.status == psutil.CONN_LISTEN and c.laddr and c.pid}
    for port in range(8503, 8511):
        pid = listening.get(port)
        if not pid or port in established_ports:
            continue
        try:
            process = psutil.Process(pid)
            if time.time() - process.create_time() <= 15 * 60:
                continue
            command_args = [str(arg).casefold() for arg in process.cmdline()]
            command = " ".join(command_args)
            if "streamlit" not in command or not any(
                arg == str(port) or arg.endswith(f"={port}") for arg in command_args
            ):
                continue
            if any(c.status == psutil.CONN_ESTABLISHED and c.laddr and c.laddr.port == port for c in psutil.net_connections(kind="tcp")):
                continue
            process.terminate()
            try:
                process.wait(timeout=2)
            except psutil.TimeoutExpired:
                continue
            stopped += 1
        except (OSError, psutil.Error):
            continue
    return stopped


def stop_orphan_pytest(_root: Path) -> int:
    """Dừng pytest mồ côi đã cũ trong repo; giữ tiến trình mới hoặc ngoài repo."""
    psutil = _processes()
    if psutil is None:
        return 0
    root = Path(_root).resolve()
    stopped = 0
    for process in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
        try:
            cmd = " ".join(process.info.get("cmdline") or []).casefold()
            name = str(process.info.get("name") or "").casefold()
            if "pytest" not in cmd or not (name.startswith("python") or "pytest" in name):
                continue
            if time.time() - process.create_time() <= 15 * 60:
                continue
            if not _inside(Path(process.cwd()), root):
                continue
            parent_pid = process.info.get("ppid")
            if not parent_pid:
                continue
            try:
                psutil.Process(parent_pid)
                continue
            except psutil.NoSuchProcess:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except psutil.TimeoutExpired:
                    continue
                stopped += 1
        except (OSError, RuntimeError, ValueError, psutil.Error):
            continue
    return stopped


def _directory_sizes(path: Path, limit: int = 15) -> list[tuple[int, str]]:
    if not path.is_dir():
        return []
    base_root = path.resolve()
    local_bytes: dict[Path, int] = {}
    children: dict[Path, list[Path]] = {}
    pending = [base_root]
    while pending:
        current = pending.pop()
        current_children: list[Path] = []
        size = 0
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if current == base_root and entry.name.casefold() in {"data", ".codex-runtime"}:
                                continue
                            child = Path(entry.path)
                            current_children.append(child)
                            pending.append(child)
                        else:
                            size += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            pass
        local_bytes[current] = size
        children[current] = current_children

    totals: dict[Path, int] = {}
    # Accumulate bottom-up once per directory. Avoid re-walking every ancestor for
    # every file: main may contain hundreds of worktrees and millions of entries.
    for current in reversed(list(local_bytes)):
        totals[current] = local_bytes[current] + sum(totals.get(child, 0) for child in children[current])
    totals.pop(base_root, None)
    return sorted(((size, str(folder)) for folder, size in totals.items()), reverse=True)[:limit]


def _count_branches(root: Path) -> tuple[int, int]:
    worktrees = len(_porcelain_worktrees(root))
    branches = len([line for line in _git(root, "branch", "--format=%(refname:short)").stdout.splitlines() if line.strip()])
    return worktrees, branches


def report(root: Path, output_root: Path, *, save: bool = True) -> str:
    root = Path(root).resolve()
    output_root = Path(output_root).resolve()
    worktrees, branches = _count_branches(root)
    sections = [(root, "Repo")]
    if output_root.is_dir():
        sections.append((output_root, "D:\\AI-Video-Output"))
    lines = [f"BÁO CÁO DỌN RÁC — {datetime.now().astimezone().isoformat(timespec='minutes')}",
             f"Repo: {root}", f"Worktree: {worktrees}; nhánh local: {branches}", ""]
    snapshot: dict[str, Any] = {"ts": datetime.now(timezone.utc).isoformat(), "worktrees": worktrees, "branches": branches}
    for base, title in sections:
        lines.append(f"{title} — 15 thư mục lớn nhất (byte)")
        items = _directory_sizes(base)
        snapshot[title] = [{"path": name, "bytes": size} for size, name in items]
        lines.extend(f"{size:>14}  {name}" for size, name in items)
        if not items:
            lines.append("(không có thư mục con)")
        lines.append("")
    log = output_root / "_luu_tru" / "don_rac_bao_cao.jsonl"
    previous = None
    if log.is_file():
        for line in reversed(log.read_text(encoding="utf-8-sig").splitlines()):
            try:
                previous = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if previous:
        lines.append(f"So với báo cáo trước: worktree {worktrees - int(previous.get('worktrees', worktrees)):+d}; "
                     f"nhánh {branches - int(previous.get('branches', branches)):+d}.")
        for _base, title in sections:
            old = {row.get("path"): int(row.get("bytes", 0)) for row in previous.get(title, [])}
            current = {row["path"]: int(row["bytes"]) for row in snapshot.get(title, [])}
            deltas = [(name, size - old[name]) for name, size in current.items() if name in old and size != old[name]]
            if deltas:
                lines.append(f"Thay đổi dung lượng {title}: " + "; ".join(f"{name} {delta:+d} byte" for name, delta in deltas[:5]))
    else:
        lines.append("So với báo cáo trước: chưa có nhật ký.")
    lines.append("Ghi chú: bỏ qua data/ và các đường dẫn dữ liệu nhạy cảm khi tính dung lượng.")
    if save:
        _append_journal(log, snapshot)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dọn rác repo, mặc định dry-run với thao tác chuyển/xóa.")
    parser.add_argument("--goc", type=Path, help="gốc repo (mặc định tìm từ thư mục hiện tại)")
    parser.add_argument("--output", type=Path, default=Path(r"D:\AI-Video-Output"), help="thư mục lưu trữ/báo cáo")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("nhanh", help="tóm tắt ngắn một dòng; dừng server/test an toàn")
    p = sub.add_parser("worktree", help="dọn worktree cũ; mặc định dry-run")
    p.add_argument("--lam-that", action="store_true")
    p = sub.add_parser("sao-luu", help="tạo bản sao cạnh tệp không nhạy cảm; chuyển bản cũ chỉ với --lam-that")
    p.add_argument("file", type=Path)
    p.add_argument("--loai")
    p.add_argument("--dry-run", action="store_true", help="chỉ xem trước, không tạo bản sao")
    p.add_argument("--lam-that", action="store_true")
    p = sub.add_parser("xoay", help="xoay vòng backup, chuyển bản cũ vào kho")
    p.add_argument("--giu", type=int, default=3)
    p.add_argument("--lam-that", action="store_true")
    sub.add_parser("bao-cao", help="in thống kê thư mục, worktree/branch và chênh lệch")
    p = sub.add_parser("khoi-phuc", help="khôi phục mục đã chuyển theo ID nhật ký")
    p.add_argument("id")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = find_repo_root(args.goc)
        output = Path(args.output).resolve()
        journal = output / "_luu_tru" / "nhat_ky_don_rac.jsonl"
        if args.command == "nhanh":
            stopped_servers = stop_redundant_servers(root)
            stopped_pytest = stop_orphan_pytest(root)
            worktrees = cleanup_worktrees(root, dry_run=True, archive_root=output / "_luu_tru" / "handoff_codex",
                                          journal=journal)
            available = _processes() is not None
            process_note = "" if available else "; psutil chưa có nên bỏ kiểm tra tiến trình"
            print(f"Streamlit thừa đã tắt: {stopped_servers}; pytest mồ côi đã tắt: {stopped_pytest}; "
                  f"worktree/nhánh đã dọn: {worktrees['removed']} (đủ điều kiện: {worktrees['candidates']}){process_note}.")
        elif args.command == "worktree":
            result = cleanup_worktrees(root, dry_run=not args.lam_that,
                                       archive_root=output / "_luu_tru" / "handoff_codex", journal=journal)
            mode = "dry-run" if not args.lam_that else "đã chạy"
            print(f"Worktree: {mode}; đủ điều kiện {result['candidates']}; đã gỡ {result['removed']}; bỏ qua {len(result['skipped'])}.")
            for item in result.get("plan", []):
                print(f"Kế hoạch: {item['path']} | nhánh {item['branch']}")
            for item in result["skipped"]:
                print(f"Bỏ qua {item['path']}: {item['reason']}")
        elif args.command == "sao-luu":
            source = Path(args.file).resolve()
            if args.goc:
                _guard_path(
                    source, root,
                    allow_manifest_backup=source.name.casefold() == "manifest.sqlite",
                )
            result = create_backup(source, args.loai, dry_run=args.dry_run, journal=journal, repo_root=root)
            print(f"Sao lưu {'dry-run' if args.dry_run else 'đã tạo'}: {result['destination']}")
            if not args.dry_run:
                rotation = rotate_backups(source.parent, output / "_luu_tru" / "backup_cu", journal,
                                          keep=3, dry_run=not args.lam_that)
                print(f"Xoay sau sao lưu: {'kế hoạch chuyển' if not args.lam_that else 'đã chuyển'} "
                      f"{rotation['moved']} bản cũ; không xóa file.")
                for old_source, reason in rotation.get("failed", []):
                    print(f"CẢNH BÁO: giữ nguyên {old_source} (không chuyển được: {reason})")
                if not args.lam_that:
                    for old_source, destination in rotation["plan"]:
                        print(f"Kế hoạch: {old_source} -> {destination}")
        elif args.command == "xoay":
            data = root / "data"
            result = rotate_backups(data, output / "_luu_tru" / "backup_cu", journal,
                                    keep=args.giu, dry_run=not args.lam_that)
            print(f"Xoay {'dry-run' if not args.lam_that else 'đã chạy'}: giữ {len(result['kept'])}, "
                  f"chuyển {result['moved']}; không xóa file.")
            for source, reason in result.get("failed", []):
                print(f"CẢNH BÁO: giữ nguyên {source} (không chuyển được: {reason})")
            if not args.lam_that:
                for source, destination in result["plan"]:
                    print(f"Kế hoạch: {source} -> {destination}")
        elif args.command == "bao-cao":
            print(report(root, output))
        elif args.command == "khoi-phuc":
            print(f"Đã khôi phục: {restore_item(args.id, journal, repo_root=root)}")
        return 0
    except (OSError, RuntimeError, SafetyError, ValueError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
