"""K1/K2 — end frames as first-class pictures (kế hoạch tổng K-a: a shot whose `end_state` changes something — a new position,
a fall, the result of an action — was sent with its start frame only, the model invented the ending, motion_match was low and the
clip was paid for again).

For such a shot a second picture is drawn: the same frame, framing and light as the approved start picture, at the moment of the
end state. The clip is then sent as first + last frame (Seedance `last_frame`, Kling Omni `end_frame` — both in the ClipAI skill
clipai-1.3.1 and in data/provider_rules.json `video_models`). A shot that continues into the next one already ends on the next
shot's start picture (shots.last_frame_for) and needs none.

End frames live in their own table (not image_gen jobs: many queries treat an approved image_gen job as THE start picture of its
shot). They pass through the same spending limit and ledger as pictures. Off until a real test (feature `end_frames`).
"""
import json
import os
from typing import Dict, List, Optional

from . import budget, features
from .cost import record_usage
from .pipeline import Pipeline
from .providers import ProviderError

FEATURE = "end_frames"


def _now_sql() -> str:
    return "datetime('now')"


def needed(data: Dict, shot_mode: Optional[str]) -> bool:
    """A shot that changes state and is made as its own clip (per shot; not a Kling multi-shot group, not a shot that continues
    into the next one — that one already ends on the next start picture)."""
    if shot_mode != "per_shot" or data.get("continuous_with_next"):
        return False
    return bool((data.get("end_state") or "").strip())


def _start_job(conn, scene_id: int):
    return conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                        (scene_id,)).fetchone()


def current(conn, scene_id: int):
    """The latest end frame row of a shot, or None."""
    return conn.execute("SELECT * FROM end_frames WHERE scene_id=? ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()


def usable_path(conn, scene_id: int) -> Optional[str]:
    """The end frame to send with the clip: ready, drawn from the shot's current start picture, file present."""
    row = current(conn, scene_id)
    start = _start_job(conn, scene_id)
    if row is None or row["state"] != "ready" or start is None or row["start_job_id"] != start["id"]:
        return None
    return row["path"] if row["path"] and os.path.exists(row["path"]) else None


def queue(p: Pipeline, project_id: int) -> List[int]:
    """Queue an end frame for every shot that needs one and has an approved start picture but no end frame from that picture yet
    (a new start picture makes the old end frame outdated). Returns the scene ids queued."""
    proj = p.project(project_id)
    mode = proj["shot_mode"] if "shot_mode" in proj.keys() else None
    out = []
    for s in p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        data = json.loads(s["data"] or "{}")
        start = _start_job(p.conn, s["id"])
        if not needed(data, mode) or start is None:
            continue
        row = current(p.conn, s["id"])
        if row is not None and row["start_job_id"] == start["id"] and row["state"] in ("queued", "running", "ready", "failed"):
            continue
        p.conn.execute("INSERT INTO end_frames (project_id, scene_id, start_job_id, state, created_at, updated_at)"
                       f" VALUES (?,?,?,'queued',{_now_sql()},{_now_sql()})", (project_id, s["id"], start["id"]))
        out.append(s["id"])
    p.conn.commit()
    return out


def prompt_for(p: Pipeline, project_id: int, scene_id: int) -> str:
    from .runner import framing_sentence, lock_note, no_minor_age
    data = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()["data"] or "{}")
    text = (framing_sentence(data) + "The SAME shot as the first image — same camera, framing, place and light — a few seconds later, "
            f"at the end of the action: {data.get('end_state', '').strip()}. One single frame, one moment only.")
    if (data.get("blocking") or "").strip():
        text += f" Blocking at the end: {data['blocking'].strip()}"
    return no_minor_age(text + lock_note(p.conn, project_id, data.get("characters")))


def _set(p: Pipeline, row_id: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    p.conn.execute(f"UPDATE end_frames SET {cols}, updated_at={_now_sql()} WHERE id=?", (*fields.values(), row_id))
    p.conn.commit()


def tick(p: Pipeline, project_id: int, provider, data_dir: str) -> Dict[str, int]:
    """Send queued end frames (the approved start picture + the characters' references go along), poll running ones, download."""
    from . import assets, formats, image_models
    counts = {"sent": 0, "ready": 0, "failed": 0, "running": 0}
    proj = p.project(project_id)
    for row in p.conn.execute("SELECT * FROM end_frames WHERE project_id=? AND state IN ('queued','running') ORDER BY id",
                              (project_id,)).fetchall():
        if row["state"] == "queued":
            start = os.path.join(data_dir, str(project_id), "images", f"job_{row['start_job_id']}.png")
            if not os.path.exists(start):
                _set(p, row["id"], state="failed", note="thiếu file ảnh khung đầu")
                counts["failed"] += 1
                continue
            data = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (row["scene_id"],)).fetchone()["data"] or "{}")
            refs = [{"path": start, "label": "start frame", "role": "previous_scene"}] + assets.scene_references(
                p.conn, project_id, data, limit=assets.MAX_REFERENCES - 1)
            prompt = prompt_for(p, project_id, row["scene_id"])
            kwargs = {}
            aspect = formats.project_aspect(proj)
            if aspect and getattr(provider, "supports_aspect", False):
                kwargs["size"] = formats.spec(aspect)["deepix"]
            if getattr(provider, "supports_model", False):
                kwargs["model"] = image_models.of_project(proj)
            with budget.SPEND_LOCK:
                over = budget.check_image(p.conn, provider.name)
                if over:
                    _set(p, row["id"], note=f"chờ: {over}")
                    break
                try:
                    ext = provider.submit(assets.reference_note(refs) + "Scene: " + prompt, [r["path"] for r in refs], **kwargs)
                except ProviderError as e:
                    if e.transient:
                        break
                    _set(p, row["id"], state="failed", note=f"{e.code or 'error'}: {e}")
                    counts["failed"] += 1
                    continue
                info = getattr(provider, "usage_info", None)
                if info is not None:
                    model, tier = info(kwargs["model"]) if kwargs.get("model") else info()
                    record_usage(p.conn, None, "image", provider.name, model, tier, 1, "image", project_id=project_id, stage="end_frame")
            _set(p, row["id"], state="running", external_id=ext, prompt=prompt)
            counts["sent"] += 1
            continue
        try:
            status = provider.status(row["external_id"])
        except ProviderError as e:
            if not e.transient:
                _set(p, row["id"], state="failed", note=f"{e.code or 'error'}: {e}")
                counts["failed"] += 1
            else:
                counts["running"] += 1
            continue
        if status.state == "succeeded":
            dest = os.path.join(data_dir, str(project_id), "images", f"end_{row['scene_id']}_{row['id']}.png")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                path = provider.download(row["external_id"], dest)
            except ProviderError as e:
                counts["running" if e.transient else "failed"] += 1
                if not e.transient:
                    _set(p, row["id"], state="failed", note=f"tải lỗi: {e}")
                continue
            _set(p, row["id"], state="ready", path=path)
            counts["ready"] += 1
        elif status.state == "running":
            counts["running"] += 1
        else:
            _set(p, row["id"], state="failed", note=f"{status.error_code}: {status.error_message}")
            counts["failed"] += 1
    return counts


def reject(p: Pipeline, row_id: int, note: Optional[str] = None) -> None:
    """The person does not want this end frame: the clip goes out with the start frame only (or a new one is queued by `redo`)."""
    _set(p, row_id, state="rejected", note=note or "người dùng loại")


def redo(p: Pipeline, scene_id: int) -> int:
    row = current(p.conn, scene_id)
    if row is not None and row["state"] not in ("rejected", "failed"):
        reject(p, row["id"], "làm lại")
    start = _start_job(p.conn, scene_id)
    project_id = p.conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()["project_id"]
    cur = p.conn.execute("INSERT INTO end_frames (project_id, scene_id, start_job_id, state, created_at, updated_at)"
                         f" VALUES (?,?,?,'queued',{_now_sql()},{_now_sql()})", (project_id, scene_id, start["id"] if start else None))
    p.conn.commit()
    return cur.lastrowid


def pending(p: Pipeline, project_id: int) -> int:
    return p.conn.execute("SELECT COUNT(*) FROM end_frames WHERE project_id=? AND state IN ('queued','running')",
                          (project_id,)).fetchone()[0]


def enabled() -> bool:
    return features.on(FEATURE)
