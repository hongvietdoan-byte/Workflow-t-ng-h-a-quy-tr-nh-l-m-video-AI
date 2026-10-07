"""One action per step instead of "create jobs" + "submit": queue what is missing or outdated, then send it.
Shared by the dashboard buttons and the automatic run, so both redo exactly the parts a change affected (core.lineage)."""
import json

from . import access
from typing import Dict, List

from . import lineage, llm_io, pilot, regen
from .pipeline import Pipeline

LIVE = "('queued','running','succeeded','pending_review','approved','retryable')"


class GateError(ValueError):
    """The manual "Gen ảnh" hit a gate the automatic run has (Bible contradicts the pictures, no Character Lock): nothing was queued."""


def image_gates(p: Pipeline, project_id: int) -> Dict[str, List[str]]:
    """The gates the automatic run applies before any picture is paid for (core.autopilot._director_phase), for the manual path:
    {"block": [...]} = a Bible that contradicts its library pictures (last check, no new Claude call) or a character without a Character
    Lock (O6) — the person must fix it or confirm; {"warn": [...]} = a character without a reference picture (drawn from words)."""
    from . import autopilot, claude_tasks
    block, warn = [], []
    try:
        flags = claude_tasks.bible_flags(p, project_id)
    except Exception as e:  # noqa: BLE001 - a check that cannot be read is a gate too (never silently passed)
        flags = {}
        block.append(f"không đọc được kết quả kiểm Bible ({type(e).__name__}: {e})")
    block += [f"mô tả {n} mâu thuẫn với ảnh tài nguyên: {m[0]}" for n, m in flags.items()]
    gaps = autopilot.bible_gaps(p, project_id)
    if gaps["no_lock"]:
        block.append("chưa có Character Lock (nét nhận diện phải giữ): " + ", ".join(gaps["no_lock"]))
    warn += [f"{n} chưa có ảnh tham chiếu ở Kho — model chỉ vẽ theo chữ, dễ lệch thiết kế" for n in gaps["no_picture"]]
    return {"block": block, "warn": warn}


def queue_images(p: Pipeline, project_id: int, confirmed: bool = False) -> Dict:
    """Image jobs for ready scenes without a live picture, and a redo for approved pictures made from an outdated spec.
    While a pilot is running only its scenes are queued. The automatic run's gates apply (image_gates): a blocking one raises
    GateError unless the person confirmed (`confirmed=True`, recorded as a diag); warnings are recorded as diags."""
    access.need_edit(p, project_id, "gửi gen ảnh")
    from . import diag
    conn = p.conn
    fresh = [r["id"] for r in conn.execute(
        f"SELECT id FROM scenes WHERE project_id=? AND state='ready' AND id NOT IN (SELECT scene_id FROM jobs WHERE type='image_gen'"
        f" AND state IN {LIVE}) ORDER BY idx", (project_id,))]
    stale = {sid: r for sid, r in lineage.scan(conn, project_id).items() if r["image_stale"] and r["image_job_id"]}
    from . import shots
    fresh = [sid for sid in fresh if shots.needs_own_image(conn, sid)]   # v3 multi-shot: later shots of a group need no picture
    fresh = pilot.allowed_scenes(p, project_id, fresh)
    redo_ids = pilot.allowed_scenes(p, project_id, [sid for sid in stale if not p.has_pending_take(sid, "image_gen")])   # S14.17 rà #2
    if fresh or redo_ids:
        gates = image_gates(p, project_id)
        if gates["block"] and not confirmed:
            raise GateError("Chưa gen ảnh: " + "; ".join(gates["block"]) + " — sửa ở Bước 1 (Character Bible / Lock) hoặc tick "
                            "“vẫn gen” nếu bạn đã xem và chấp nhận")
        if gates["block"]:
            diag.record(conn, "image", "warn", "người dùng xác nhận vẫn gen ảnh dù: " + "; ".join(gates["block"]), "gate_override",
                        project_id)
        for w in gates["warn"]:
            diag.record(conn, "image", "warn", w, "no_reference", project_id)
    for sid in fresh:
        p.create_job(sid, "image_gen")
    for sid in redo_ids:                              # the scene changed: the new input is the scene itself (no Vietnamese note to the model)
        p.reopen_approved(stale[sid]["image_job_id"], f"Nội dung cảnh đã đổi: {stale[sid]['image_stale']}", fix="")
    return {"created": len(fresh), "redo": len(redo_ids), "pilot": pilot.active(p, project_id)}


def videos_to_make(p: Pipeline, project_id: int) -> List[Dict]:
    """Scenes ready for video (image + motion prompt approved and current) that have no clip made or in progress yet."""
    return [r for r in llm_io.ready_for_video(p, project_id)
            if not p.conn.execute(f"SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN {LIVE}",
                                  (r["scene_id"],)).fetchone()]


def _stale_redos(p: Pipeline, project_id: int) -> List[Dict]:
    """Clips made from old inputs that a batch would remake (lineage 'video_stale', motion current + approved, no new take waiting)."""
    out = []
    for sid, r in lineage.scan(p.conn, project_id).items():
        if r["video_stale"] and r["video_job_id"] and not r["motion_stale"] and r["motion_state"] == "approved" \
                and r["video_state"] in ("succeeded", "approved", "pending_review") and not p.has_pending_take(sid, "video_gen"):
            out.append({"scene_id": sid, "job_id": r["video_job_id"], "why": r["video_stale"]})
    return out


def video_plan(p: Pipeline, project_id: int) -> List[Dict]:
    """07/10 Khủng Long Đỏ: what '▶ Gen video' would send, one row per scene: {"scene_id", "idx", "kind": new|stale, "model_name",
    "label", "why"}. The model is the REAL one (alias 'seedance' = Seedance 2.0) with its resolution, so a person sees the price level."""
    from . import model_router
    from .adapters import clipai
    rows = [{"scene_id": r["scene_id"], "kind": "new", "why": ""} for r in videos_to_make(p, project_id)]
    rows += [{"scene_id": r["scene_id"], "kind": "stale", "why": f"đã cũ: {r['why']}"} for r in _stale_redos(p, project_id)]
    for r in rows:
        r["idx"] = p.conn.execute("SELECT idx FROM scenes WHERE id=?", (r["scene_id"],)).fetchone()["idx"]
        try:
            ch = model_router.scene_choice(p.conn, r["scene_id"])
            r["model_name"] = clipai.display_name(ch.get("model"), ch.get("resolution") or "mặc định")
        except Exception as e:  # noqa: BLE001 - a scene whose model cannot be read is said, not hidden
            r["model_name"] = f"không đọc được model ({type(e).__name__})"
        r["label"] = f"S{r['idx']:02d} · {r['model_name']}" + (f" · {r['why']}" if r["why"] else "")
    return sorted(rows, key=lambda r: (r["kind"] != "new", r["idx"]))


def chain_waits(p: Pipeline, project_id: int) -> Dict[int, str]:
    """07/10: queued clips of shots marked start_from_prev_clip that wait for the previous shot's clip to be APPROVED (VideoRunner
    sends them only then) → {scene_id: 'S03 chờ duyệt clip cảnh S02'}, so the screen says why nothing is sent."""
    out: Dict[int, str] = {}
    rows = p.conn.execute("SELECT s.id, s.idx, s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND "
                          "j.type='video_gen' AND j.state='queued'", (project_id,)).fetchall()
    for r in rows:
        if not json.loads(r["data"] or "{}").get("start_from_prev_clip"):
            continue
        prev = p.conn.execute("SELECT s.idx, (SELECT j.state FROM jobs j WHERE j.scene_id=s.id AND j.type='video_gen' ORDER BY j.id DESC"
                              " LIMIT 1) AS st FROM scenes s WHERE s.project_id=? AND s.idx<? ORDER BY s.idx DESC LIMIT 1",
                              (project_id, r["idx"])).fetchone()
        if prev is not None and prev["st"] != "approved":
            out[r["id"]] = f"S{r['idx']:02d} chờ duyệt clip cảnh S{prev['idx']:02d} (cảnh này bắt đầu từ khung cuối clip đó)" + (
                "" if prev["st"] else " — cảnh trước chưa có clip")
    return out


def queue_videos(p: Pipeline, project_id: int, data_dir: str, only=None) -> Dict:
    """Video jobs for scenes whose image + motion prompt are approved and current, and a redo for clips made from old inputs.
    `only` (07/10 Khủng Long Đỏ): the scene ids the person ticked — nothing else is created or remade (None = every scene: autopilot)."""
    access.need_edit(p, project_id, "gửi gen video")
    conn = p.conn
    created = 0
    for r in llm_io.ready_for_video(p, project_id):
        if only is not None and r["scene_id"] not in only:
            continue
        if not conn.execute(f"SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN {LIVE}", (r["scene_id"],)).fetchone():
            p.create_job(r["scene_id"], "video_gen")
            created += 1
    redo = 0
    for r in _stale_redos(p, project_id):        # S14.17 rà #2: a new take already waits → not remade (that would be a 2nd paid job)
        if only is not None and r["scene_id"] not in only:
            continue
        regen.regenerate_video(p, data_dir, r["job_id"], f"làm lại vì {r['why']}")   # input changed: no fix
        redo += 1
    return {"created": created, "redo": redo}
