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


MAX_REDOS = 2              # luật 6 (người dùng chốt): an end frame is drawn again at most 2 times per start picture


def prompt_for(p: Pipeline, project_id: int, scene_id: int, fix: Optional[str] = None) -> str:
    """The end frame's prompt through THE picture prompt builder of the start picture (core.runner.build_image_prompt): the in-game
    look and its cleaning, the acting, the Lock, the place in words and no age under 18 reach the end frame too."""
    from .runner import build_image_prompt
    data = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()["data"] or "{}")
    core = ("The SAME shot as the first image — same camera, framing, place and light — a few seconds later, "
            f"at the end of the action: {data.get('end_state', '').strip()}. One single frame, one moment only.")
    prompt, _ = build_image_prompt(p.conn, project_id, data, core=core, fix=fix, blocking_label="Blocking at the end")
    return prompt


def _set(p: Pipeline, row_id: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    p.conn.execute(f"UPDATE end_frames SET {cols}, updated_at={_now_sql()} WHERE id=?", (*fields.values(), row_id))
    p.conn.commit()


def _usage_model(provider) -> Optional[str]:
    info = getattr(provider, "usage_info", None)
    try:
        return info()[0] if info is not None else None
    except Exception:  # noqa: BLE001 - a test double without a model
        return None


def _diag(p: Pipeline, row, severity: str, code: str, message: str) -> None:
    from . import diag
    diag.record(p.conn, "image", severity, message, code, row["project_id"], row["scene_id"])


def tick(p: Pipeline, project_id: int, provider, data_dir: str) -> Dict[str, int]:
    """Send queued end frames (the approved start picture + the characters' references go along), poll running ones, download.
    The same safeguards as the start picture: one prompt builder, reference gaps said, only sendable pictures numbered, what was sent
    kept (sent_refs), the spending limit and the ledger."""
    from . import assets, formats, image_models
    from .runner import sendable_references
    counts = {"sent": 0, "ready": 0, "failed": 0, "running": 0}
    proj = p.project(project_id)
    for row in p.conn.execute("SELECT * FROM end_frames WHERE project_id=? AND state IN ('queued','running') ORDER BY id",
                              (project_id,)).fetchall():
        if row["state"] == "queued":
            start = os.path.join(data_dir, str(project_id), "images", f"job_{row['start_job_id']}.png")
            if not os.path.exists(start):
                _set(p, row["id"], state="failed", note="thiếu file ảnh khung đầu")
                _diag(p, row, "error", "missing_input", "ảnh khung cuối không vẽ được: thiếu file ảnh khung đầu "
                      f"(job {row['start_job_id']}) — clip sẽ gửi không có khung cuối")
                counts["failed"] += 1
                continue
            data = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (row["scene_id"],)).fetchone()["data"] or "{}")
            for gap in assets.reference_gaps(p.conn, project_id, data):
                _diag(p, row, assets.gap_severity(gap), "missing_reference", f"khung cuối: {gap}")
            model = image_models.of_project(proj) if getattr(provider, "supports_model", False) else None
            refs = [{"path": start, "label": "start frame", "role": "previous_scene"}] + assets.scene_references(
                p.conn, project_id, data, limit=assets.MAX_REFERENCES - 1)
            refs, dropped = sendable_references(refs, model)
            if dropped:
                _diag(p, row, "warn", "missing_reference", "khung cuối: ảnh tham chiếu không gửi được (bỏ khỏi câu đánh số ảnh): "
                      + ", ".join(dropped))
            if not refs or refs[0]["role"] != "previous_scene":
                _set(p, row["id"], state="failed", note="ảnh khung đầu không gửi được")
                _diag(p, row, "error", "missing_input", "ảnh khung cuối không vẽ được: ảnh khung đầu không gửi được")
                counts["failed"] += 1
                continue
            prompt = prompt_for(p, project_id, row["scene_id"], fix=row["fix"] if "fix" in row.keys() else None)
            kwargs = {}
            aspect = formats.project_aspect(proj)
            if getattr(provider, "supports_aspect", False) and (aspect or proj["test_quality"]):
                kwargs["size"] = image_models.size_for(proj, model or image_models.of_project(proj))
            if model:
                kwargs["model"] = model
            with budget.SPEND_LOCK:
                over = budget.check_image(p.conn, provider.name, kwargs.get("model") or _usage_model(provider))
                if over:
                    _set(p, row["id"], note=f"chờ: {over}")
                    _diag(p, row, "warn", "budget", f"khung cuối chưa gửi: {over}")
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
                    used, tier = info(kwargs["model"]) if kwargs.get("model") else info()
                    record_usage(p.conn, None, "image", provider.name, used, tier, 1, "image", project_id=project_id, stage="end_frame")
            _set(p, row["id"], state="running", external_id=ext, prompt=prompt,
                 sent_refs=json.dumps([{"label": r["label"], "role": r["role"], "file": os.path.basename(r["path"])} for r in refs],
                                      ensure_ascii=False))
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


def redo(p: Pipeline, scene_id: int, fix: Optional[str] = None) -> int:
    """Draw the end frame again (the person asked). `fix` (English) goes into the new prompt so the input changes; at most MAX_REDOS
    redos per start picture (luật 6) — then the layer to fix is the shot's end_state / start picture, not another paid try."""
    start = _start_job(p.conn, scene_id)
    if start is None:
        raise ValueError("shot chưa có ảnh khung đầu đã duyệt — không vẽ khung cuối được")
    made = p.conn.execute("SELECT COUNT(*) FROM end_frames WHERE scene_id=? AND start_job_id=? AND external_id IS NOT NULL",
                          (scene_id, start["id"])).fetchone()[0]
    if made > MAX_REDOS:
        raise ValueError(f"khung cuối của shot này đã vẽ {made} lần (tối đa {MAX_REDOS} lần vẽ lại) — sửa end_state / ảnh khung đầu thay vì "
                         "vẽ lại")
    row = current(p.conn, scene_id)
    if row is not None and row["state"] not in ("rejected", "failed"):
        reject(p, row["id"], "làm lại")
    project_id = p.conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()["project_id"]
    cur = p.conn.execute("INSERT INTO end_frames (project_id, scene_id, start_job_id, state, fix, created_at, updated_at)"
                         f" VALUES (?,?,?,'queued',?,{_now_sql()},{_now_sql()})", (project_id, scene_id, start["id"], (fix or "").strip() or None))
    p.conn.commit()
    return cur.lastrowid


def pending(p: Pipeline, project_id: int) -> int:
    return p.conn.execute("SELECT COUNT(*) FROM end_frames WHERE project_id=? AND state IN ('queued','running')",
                          (project_id,)).fetchone()[0]


def enabled() -> bool:
    return features.on(FEATURE)
