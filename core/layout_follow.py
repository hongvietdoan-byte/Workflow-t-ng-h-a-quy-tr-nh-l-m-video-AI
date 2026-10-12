"""Hộp thư 12/10 19:17 (phiên máy chính `2b1f6ce`, #27 shot 15/17 keep shot 18's layout): a shot's `continuity_from` (another shot's idx,
before OR after it) sends that shot's picture as the 'layout_from' reference (core/runner.layout_reference). Three things around it
were missing — with the flag `layout_from_follow` (off by default: a picture called "outdated" can make an automatic run redraw it):

1. wait: the shot's picture waits while the named shot has no picture yet but one is on its way (a job queued / running) — sent
   before it, it went out without the layout picture (only a `missing_reference` warning). No job on the way = sent as before + warned.
2. pilot: a trial run that picks the shot also draws the named shot (`core.pilot.anchors_needed`), else the shot waited for ever.
3. outdated: the named shot redrawn and the new picture approved → the picture that kept its layout is "⚠ cũ" (core.lineage), read
   from the picture really sent (`jobs.sent_package`, role layout_from); no package on record = no alarm.
   And core.change_review checks the shots that keep a changed shot's layout (reverse of continuity_from)."""
import json
import re
from typing import Dict, List, Optional

FLAG = "layout_from_follow"


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _source_idx(data: Dict) -> Optional[int]:
    v = (data or {}).get("continuity_from")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def wait_reason(conn, project_id: int, data: Dict) -> Optional[str]:
    """Why this shot's picture waits for the shot it keeps the layout of, or None."""
    want = _source_idx(data)
    if want is None:
        return None
    from .runner import layout_frame_job
    if layout_frame_job(conn, project_id, data) is not None:
        return None
    coming = conn.execute("SELECT 1 FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.project_id=? AND s.idx=? AND j.type='image_gen'"
                          " AND j.state IN ('queued','running') LIMIT 1", (project_id, want)).fetchone()
    if coming is None:
        return None
    return f"chờ ảnh shot {want} (giữ bố cục — continuity_from) — sẽ tự gửi khi ảnh đó xong"


def source_scene_ids(conn, project_id: int, scene_ids: List[int]) -> List[int]:
    """The shots (scene ids, in order) the given shots keep the layout of, transitively, that are not among them."""
    out: List[int] = []
    todo = list(scene_ids)
    seen = set(scene_ids)
    while todo:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (todo.pop(0),)).fetchone()
        try:
            want = _source_idx(json.loads(row["data"] or "{}")) if row else None
        except (TypeError, ValueError):
            want = None
        if want is None:
            continue
        src = conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (project_id, want)).fetchone()
        if src is not None and src["id"] not in seen:
            seen.add(src["id"])
            out.append(src["id"])
            todo.append(src["id"])
    return out


def followers(conn, project_id: int, idx: int) -> List[int]:
    """Scene ids of the shots whose `continuity_from` is this shot's idx."""
    out = []
    for r in conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        try:
            if _source_idx(json.loads(r["data"] or "{}")) == idx:
                out.append(r["id"])
        except (TypeError, ValueError):
            continue
    return out


_JOB_FILE = re.compile(r"job_(\d+)\.png$")


def sent_layout_job(sent_package) -> Optional[int]:
    """The job id of the 'layout_from' picture really sent with a picture (its sent package), or None."""
    try:
        pkg = json.loads(sent_package) if isinstance(sent_package, str) else (sent_package or {})
    except (TypeError, ValueError):
        return None
    for r in (pkg or {}).get("refs") or []:
        if isinstance(r, dict) and r.get("role") == "layout_from":
            m = _JOB_FILE.search(str(r.get("path") or r.get("file") or "").replace("\\", "/"))
            if m:
                return int(m.group(1))
    return None


def stale_reason(conn, project_id: int, image_job_id: int, data: Dict) -> Optional[str]:
    """Why an approved picture that kept another shot's layout is outdated (that shot has a newer chosen picture), or None."""
    want = _source_idx(data)
    if want is None:
        return None
    row = conn.execute("SELECT sent_package FROM jobs WHERE id=?", (image_job_id,)).fetchone()
    sent = sent_layout_job(row["sent_package"]) if row is not None and "sent_package" in row.keys() else None
    if sent is None:
        return None
    from .runner import layout_frame_job
    now = layout_frame_job(conn, project_id, data)
    if now is None or now["id"] == sent or now["state"] != "approved":
        return None
    return f"ảnh shot {want} (giữ bố cục theo nó) đã vẽ lại — ảnh này dựng theo bản cũ (job {sent}, nay job {now['id']})"
