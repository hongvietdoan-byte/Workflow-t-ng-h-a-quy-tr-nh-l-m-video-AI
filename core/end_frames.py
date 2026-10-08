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
from . import access
import json
import os
from typing import Dict, List, Optional

from . import features, spend_gate
from .pipeline import Pipeline
from .providers import ProviderError

FEATURE = "end_frames"


def _now_sql() -> str:
    return "datetime('now')"


def route(data: Dict) -> str:
    """How the clip of this shot would go out: 'seedance_ref' (reference-only Seedance group: no last frame) or 'first_last'."""
    from . import features, seedance_refs
    return "seedance_ref" if features.on("seedance_ref_groups") and seedance_refs.eligible(data) else "first_last"


def needed(data: Dict, shot_mode: Optional[str], ignore_route: bool = False) -> bool:
    """A shot that changes state and is made as its own clip (per shot; not a Kling multi-shot group, not a shot that continues
    into the next one — that one already ends on the next start picture). `ignore_route=True` (B4 🎓 học việc): judge the shot
    itself even when its clip goes out as a Seedance reference group — the plan is recorded, nothing is drawn."""
    if shot_mode != "per_shot" or data.get("continuous_with_next"):
        return False
    if not ignore_route and route(data) == "seedance_ref":
        return False                  # a reference-only Seedance clip takes no last frame — drawing one would be paid for nothing
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
    access.need_edit(p, project_id, "gửi vẽ khung cuối")
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


# S14.16 (mục 6c.3, thay MAX_REDOS = 2 của luật 6 cũ): a person's redo is never capped; the run's own redos of one shot's end frame
# follow pipeline.AUTO_REGEN_LIMIT["image_gen"] (3), counted since the person's last redo (app_settings key _AUTO_KEY).
_AUTO_KEY = "end_frame_auto_redos:{}"


def _auto_count(conn, scene_id: int) -> int:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_AUTO_KEY.format(scene_id),)).fetchone()
    try:
        return int(row[0]) if row else 0
    except (TypeError, ValueError):
        return 0


def _set_auto_count(conn, scene_id: int, n: int) -> None:
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (_AUTO_KEY.format(scene_id), str(int(n))))


def prompt_for(p: Pipeline, project_id: int, scene_id: int, fix: Optional[str] = None) -> str:
    """The end frame's prompt through THE picture prompt builder of the start picture (core.runner.build_image_prompt): the in-game
    look and its cleaning, the acting, the Lock, the place in words and no age under 18 reach the end frame too."""
    from .runner import build_image_prompt
    data = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()["data"] or "{}")
    core = ("The SAME shot as the first image — same camera, framing, place and light — a few seconds later, "
            f"at the end of the action: {data.get('end_state', '').strip()}. One single frame, one moment only.")
    from . import skill_dossier
    if skill_dossier.enabled():                   # the end frame shows the skill's END phase (skill_phase_end)
        data = skill_dossier.at_end(data)
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
            from . import skill_dossier
            if skill_dossier.enabled():               # the real frame of the skill's end phase
                end = skill_dossier.at_end(data)
                refs = skill_dossier.add_reference(refs, skill_dossier.reference(skill_dossier.shot_skill(end)), assets.MAX_REFERENCES)
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
            from . import quality_tier                # N1: flag two_tier_quality on → "Thử rẻ" ignored
            if getattr(provider, "supports_aspect", False) and (aspect or quality_tier.cheap_mode(proj)):
                kwargs["size"] = image_models.size_for(proj, model or image_models.of_project(proj))
            if model:
                kwargs["model"] = model
            # S14.1: the gate adds the project's locked budget (it was skipped), a paused project and 'out_of_credit' → halt
            with spend_gate.spend(p.conn, "image", provider.name, project_id=project_id,
                                  model=kwargs.get("model") or _usage_model(provider), ledger_stage="end_frame") as slot:
                if slot.over:
                    _set(p, row["id"], note=f"chờ: {slot.over}")
                    _diag(p, row, "warn", "budget", f"khung cuối chưa gửi: {slot.over}")
                    break
                try:
                    ext = slot.send(provider.submit, assets.reference_note(refs) + "Scene: " + prompt, [r["path"] for r in refs], **kwargs)
                except ProviderError as e:
                    if e.transient:
                        break
                    _set(p, row["id"], state="failed", note=f"{e.code or 'error'}: {e}")
                    counts["failed"] += 1
                    continue
                info = getattr(provider, "usage_info", None)
                if info is not None:
                    used, tier = info(kwargs["model"]) if kwargs.get("model") else info()
                    slot.record(model=used, tier=tier)
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


def redo(p: Pipeline, scene_id: int, fix: Optional[str] = None, auto: bool = False) -> int:
    """Draw the end frame again. `fix` (English) goes into the new prompt so the input changes. The person asked (default): never
    capped, the automatic count starts again. `auto=True` (the run by itself): at most pipeline.AUTO_REGEN_LIMIT["image_gen"] since the
    person's last redo — then the layer to fix is the shot's end_state / start picture (ValueError, said)."""
    access.need_edit_scene(p, scene_id, "vẽ lại khung cuối")
    start = _start_job(p.conn, scene_id)
    if start is None:
        raise ValueError("shot chưa có ảnh khung đầu đã duyệt — không vẽ khung cuối được")
    from .pipeline import AUTO_REGEN_LIMIT
    limit = AUTO_REGEN_LIMIT["image_gen"]
    done = _auto_count(p.conn, scene_id)
    if auto and done >= limit:
        raise ValueError(f"Cần bạn quyết — khung cuối của shot này đã tự vẽ lại {done} lần (tối đa {limit}) — sửa end_state / ảnh khung "
                         "đầu, hoặc bấm vẽ lại tay")
    _set_auto_count(p.conn, scene_id, done + 1 if auto else 0)
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


def shadow() -> bool:
    """🎓 học việc (B1 08/10): runs and records its decision, never acts."""
    return features.shadow(FEATURE)


def active() -> bool:
    """On or học việc — for choosing a branch only."""
    return features.active(FEATURE)
