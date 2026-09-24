"""Trash for generated images and videos: deleted files are moved here (never destroyed at once) and
purged automatically after TRASH_DAYS (30) days.

Layout, per project:  <data>/<project>/trash/images/   and   <data>/<project>/trash/videos/
Each folder has a `trash.json` manifest: original location, job, scene, reason, time deleted.

What goes to the trash:
- images the reviewer or the QC agent rejected (`sweep_rejected`),
- images/clips the user deletes from the dashboard,
- a clip that is replaced by a re-generated one (the runner moves the old file aside first).
"""
import json
import math
import os
import shutil
import time
from typing import Dict, List, Optional

from .pipeline import Pipeline

KINDS = ("images", "videos", "audio")
DAY = 86400.0


def retention_days() -> int:
    try:
        return max(int(os.environ.get("TRASH_DAYS", "30")), 1)
    except ValueError:
        return 30


def _project_dir(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id))


def trash_dir(data_dir: str, project_id: int, kind: str) -> str:
    if kind not in KINDS:
        raise ValueError(f"unknown trash kind '{kind}'")
    path = os.path.join(_project_dir(data_dir, project_id), "trash", kind)
    os.makedirs(path, exist_ok=True)
    return path


def _manifest_path(folder: str) -> str:
    return os.path.join(folder, "trash.json")


def _load(folder: str) -> List[Dict]:
    try:
        with open(_manifest_path(folder), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(folder: str, entries: List[Dict]) -> None:
    with open(_manifest_path(folder), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)


def move_to_trash(path: str, data_dir: str, project_id: int, kind: str, reason: str,
                  job_id: Optional[int] = None, scene_idx: Optional[int] = None,
                  now: Optional[float] = None) -> Optional[str]:
    """Move one file into the trash. Returns the new path, or None when the file does not exist."""
    if not path or not os.path.isfile(path):
        return None
    folder = trash_dir(data_dir, project_id, kind)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now or time.time()))
    stem, ext = os.path.splitext(os.path.basename(path))
    name, n = f"{stem}__{stamp}{ext}", 1
    while os.path.exists(os.path.join(folder, name)):
        n += 1
        name = f"{stem}__{stamp}_{n}{ext}"
    dest = os.path.join(folder, name)
    original = os.path.relpath(path, _project_dir(data_dir, project_id))
    shutil.move(path, dest)
    entries = _load(folder)
    entries.append({"file": name, "original": original.replace("\\", "/"), "job_id": job_id, "scene_idx": scene_idx,
                    "reason": reason, "deleted_at": now or time.time()})
    _save(folder, entries)
    return dest


def items(data_dir: str, project_id: int, kind: str, now: Optional[float] = None) -> List[Dict]:
    """Trash entries, newest first, with `path` and `days_left`."""
    folder = trash_dir(data_dir, project_id, kind)
    current = now or time.time()
    out = []
    for e in _load(folder):
        path = os.path.join(folder, e["file"])
        if not os.path.exists(path):
            continue
        left = retention_days() - (current - e["deleted_at"]) / DAY
        out.append({**e, "path": path, "days_left": max(math.ceil(left), 0)})
    return sorted(out, key=lambda x: x["deleted_at"], reverse=True)


def find_for_job(data_dir: str, project_id: int, kind: str, job_id: int) -> Optional[str]:
    for e in items(data_dir, project_id, kind):
        if e.get("job_id") == job_id:
            return e["path"]
    return None


def restore(data_dir: str, project_id: int, kind: str, file_name: str) -> str:
    """Put a trashed file back where it came from (refuses to overwrite something that exists there)."""
    folder = trash_dir(data_dir, project_id, kind)
    entries = _load(folder)
    entry = next((e for e in entries if e["file"] == file_name), None)
    if entry is None:
        raise KeyError(f"'{file_name}' is not in the trash")
    target = os.path.join(_project_dir(data_dir, project_id), *entry["original"].split("/"))
    if os.path.exists(target):
        raise ValueError(f"cannot restore: '{entry['original']}' already exists")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.move(os.path.join(folder, file_name), target)
    _save(folder, [e for e in entries if e["file"] != file_name])
    return target


DELETED_DIR = "_deleted"          # whole folders of deleted projects wait here for the same retention period


def park_project_folder(data_dir: str, project_id: int, now: Optional[float] = None) -> Optional[str]:
    """Move a deleted project's folder (pictures, clips, its own trash) aside instead of erasing it at once. Returns the new path."""
    src = os.path.join(data_dir, str(project_id))
    if not os.path.isdir(src):
        return None
    import shutil
    folder = os.path.join(data_dir, DELETED_DIR)
    os.makedirs(folder, exist_ok=True)
    stamp = int(now or time.time())
    dest = os.path.join(folder, f"{project_id}__{stamp}")
    shutil.move(src, dest)
    return dest


def _purge_deleted_projects(data_dir: str, current: float, limit: float) -> int:
    import shutil
    folder = os.path.join(data_dir, DELETED_DIR)
    removed = 0
    for name in os.listdir(folder) if os.path.isdir(folder) else []:
        stamp = name.rsplit("__", 1)[-1]
        if stamp.isdigit() and current - int(stamp) >= limit:
            shutil.rmtree(os.path.join(folder, name), ignore_errors=True)
            removed += 1
    return removed


def purge_expired(data_dir: str, now: Optional[float] = None, days: Optional[int] = None) -> int:
    """Delete trash entries (and parked folders of deleted projects) older than the retention period. Returns items removed."""
    limit = (days or retention_days()) * DAY
    current = now or time.time()
    removed = 0
    if not os.path.isdir(data_dir):
        return 0
    removed += _purge_deleted_projects(data_dir, current, limit)
    for name in os.listdir(data_dir):
        for kind in KINDS:
            folder = os.path.join(data_dir, name, "trash", kind)
            if not os.path.isdir(folder):
                continue
            keep = []
            for e in _load(folder):
                path = os.path.join(folder, e["file"])
                if current - e["deleted_at"] >= limit:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    removed += 1
                elif os.path.exists(path):
                    keep.append(e)
            _save(folder, keep)
    return removed


def _swept_path(data_dir: str, project_id: int) -> str:
    return os.path.join(trash_dir(data_dir, project_id, "images"), "swept.json")


def _swept(data_dir: str, project_id: int) -> set:
    try:
        with open(_swept_path(data_dir, project_id), encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def sweep_rejected(pipeline: Pipeline, data_dir: str, project_id: int) -> int:
    """Move the image file of every rejected image job into the trash, once per job (idempotent, cheap to call
    often). A job already swept is remembered, so a file the user restores is not thrown away again."""
    rows = pipeline.conn.execute(
        "SELECT j.id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' AND j.state='rejected'", (project_id,)).fetchall()
    done = _swept(data_dir, project_id)
    moved = 0
    for r in rows:
        if r["id"] in done:
            continue
        path = os.path.join(_project_dir(data_dir, project_id), "images", f"job_{r['id']}.png")
        if move_to_trash(path, data_dir, project_id, "images", "bị loại", r["id"], r["idx"]):
            moved += 1
        done.add(r["id"])
    if moved or len(done) != len(_swept(data_dir, project_id)):
        with open(_swept_path(data_dir, project_id), "w", encoding="utf-8") as f:
            json.dump(sorted(done), f)
    return moved
