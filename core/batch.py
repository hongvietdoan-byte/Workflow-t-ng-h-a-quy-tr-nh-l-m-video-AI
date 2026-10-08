"""One action per step instead of "create jobs" + "submit": queue what is missing or outdated, then send it.
Shared by the dashboard buttons and the automatic run, so both redo exactly the parts a change affected (core.lineage)."""
import json

from . import access
from typing import Dict, List, Optional

from . import lineage, llm_io, pilot, regen, takes
from .pipeline import MISSING_INPUT, STALE_INPUT, Pipeline

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


def _draft_tier(conn, scene_id: int, model) -> Optional[str]:
    """The resolution label a new clip of this shot is sent at when it starts as a draft (flag two_tier_quality, shot path
    'draft_first' and no draft yet) — e.g. '480p' — or None (sent at the plan's resolution)."""
    from . import quality_tier
    if not quality_tier.enabled() or quality_tier.tier_for_new_job(conn, scene_id)["quality_tier"] != "draft":
        return None
    low = quality_tier.low_tier({}, model)
    return low.get("resolution") or ("std" if low.get("kling_mode") == "std" else None)


def picked_tag(p: Pipeline, rows: List[Dict]) -> str:
    """Price text for the clips the person picked on the Video screen (a subset of video_plan rows): each scene's own estimate
    (cost.clip_estimate), plus the automatic remakes like video_batch_tag (tính dư); a scene without a price is said."""
    from . import cost
    from .pipeline import AUTO_REGEN_LIMIT
    if not rows:
        return ""
    vals = [cost.clip_estimate(p.conn, r["scene_id"]) for r in rows]
    if any(v is None for v in vals):
        return f" · {len(rows)} clip, chưa có giá"
    total, redo = sum(vals), AUTO_REGEN_LIMIT["video_gen"]
    return f" · {len(rows)} clip ≈ {total:.2f} USD (ước tính; tự gen lại tối đa {redo} lần ≈ {total * (1 + redo):.2f})"


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
            res = ch.get("resolution") or "mặc định"
            draft = _draft_tier(p.conn, r["scene_id"], ch.get("model"))
            if draft is not None:          # 08/10 (#24): the first send of a draft-first shot goes at the LOW tier, not the plan's
                res = draft
            r["model_name"] = clipai.display_name(ch.get("model"), res) + (" (nháp)" if draft is not None else "")
        except Exception as e:  # noqa: BLE001 - a scene whose model cannot be read is said, not hidden
            r["model_name"] = f"không đọc được model ({type(e).__name__})"
        r["group"] = clip_group(p.conn, r["scene_id"])
        together = ""
        if len(r["group"]) > 1:
            idxs = [p.conn.execute("SELECT idx FROM scenes WHERE id=?", (g,)).fetchone()["idx"] for g in r["group"]]
            together = f" · clip nhóm S{min(idxs):02d}–S{max(idxs):02d}"
        r["label"] = f"S{r['idx']:02d} · {r['model_name']}{together}" + (f" · {r['why']}" if r["why"] else "")
    return sorted(rows, key=lambda r: (r["kind"] != "new", r["idx"]))


def clip_group(conn, scene_id: int) -> List[int]:
    """08/10 (#24): the scene ids made by ONE generation with this shot (Seedance reference group / Kling multi-shot / H5 set-up —
    shots.group_of, the runner's own rule), else [scene_id]. Picking shot 7 alone queued a job that waited forever: its group clip
    is sent from the group's first shot, which was not picked."""
    from . import shots
    try:
        group = shots.group_of(conn, scene_id) or []
    except Exception:  # noqa: BLE001 - no group information: the shot on its own
        group = []
    return [g["id"] for g in group] if len(group) > 1 else [scene_id]


def with_groups(conn, plan: List[Dict], picked) -> List[int]:
    """The picked scene ids grown to their whole clip groups (in film order), so no picked shot waits for an unpicked group leader."""
    by_id = {r["scene_id"]: r for r in plan}
    out: List[int] = []
    for sid in picked:
        for g in (by_id[sid].get("group") if sid in by_id else None) or [sid]:
            if g not in out:
                out.append(g)
    order = {r["scene_id"]: r["idx"] for r in plan}
    return sorted(out, key=lambda s: order.get(s, 0))


def chain_waits(p: Pipeline, project_id: int) -> Dict[int, str]:
    """07/10: queued clips of shots marked start_from_prev_clip that wait for the previous shot's clip to be APPROVED (VideoRunner
    sends them only then) → {scene_id: 'S03 chờ duyệt clip cảnh S02'}, so the screen says why nothing is sent."""
    out: Dict[int, str] = {}
    rows = p.conn.execute("SELECT s.id, s.idx, s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND "
                          "j.type='video_gen' AND j.state='queued'", (project_id,)).fetchall()
    for r in rows:
        if not json.loads(r["data"] or "{}").get("start_from_prev_clip"):
            continue
        prev = p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? AND idx<? ORDER BY idx DESC LIMIT 1",
                              (project_id, r["idx"])).fetchone()
        take = takes.used(p.conn, prev["id"], skip_cancelled=False) if prev is not None else None   # KLD-2: the chosen take
        st = take["state"] if take else None
        if prev is not None and st != "approved":
            out[r["id"]] = f"S{r['idx']:02d} chờ duyệt clip cảnh S{prev['idx']:02d} (cảnh này bắt đầu từ khung cuối clip đó)" + (
                "" if st else " — cảnh trước chưa có clip")
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


# ---- KLD-1 (08/10): "↻ Gửi lại clip lỗi" chỉ cho lỗi nhà cung cấp --------------------------------------------------------------------
def _input_failed(p: Pipeline, job_id: int) -> bool:
    return (p.failure_note(job_id) or "").startswith((STALE_INPUT, MISSING_INPUT))


def provider_failures(p: Pipeline, project_id: int, kind: str = "video_gen") -> List[int]:
    """Failed jobs a plain resend (same input) may fix: not escalated, not blocked by the content filter, and NOT failed on the input
    itself (`stale_input` / `missing inputs` — #22 job 559 was resent unchanged as 566 on old inputs)."""
    rows = p.conn.execute("SELECT j.id FROM jobs j WHERE j.project_id=? AND j.type=? AND j.state='failed' AND j.escalated=0"
                          " AND NOT EXISTS (SELECT 1 FROM content_moderation_failures f WHERE f.job_id=j.id) ORDER BY j.id",
                          (project_id, kind)).fetchall()
    return [r["id"] for r in rows if not _input_failed(p, r["id"])]


def input_failures(p: Pipeline, project_id: int, kind: str = "video_gen") -> List[Dict]:
    """Failed jobs the runner did not send because the input was outdated / missing, still the newest job of their shot:
    {id, scene_id, idx, note} — to be queued again from the CURRENT inputs (requeue_input_failures), never resent unchanged."""
    rows = p.conn.execute("SELECT j.id, j.scene_id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type=?"
                          " AND j.state='failed' AND j.escalated=0 AND NOT EXISTS (SELECT 1 FROM jobs k WHERE k.scene_id=j.scene_id"
                          " AND k.type=j.type AND k.id>j.id) ORDER BY s.idx", (project_id, kind)).fetchall()
    return [dict(r, note=p.failure_note(r["id"])) for r in rows if _input_failed(p, r["id"])]


def requeue_input_failures(p: Pipeline, project_id: int) -> Dict:
    """KLD-1: for each clip that failed on its input — the old job is closed (cancelled; it never reached the provider) and a NEW job
    is queued from the current approved picture + motion prompt; a shot whose inputs are not approved / current is listed, not queued.
    {"created": n, "not_ready": [idx…], "reasons": {idx: why}}. Sending (and paying) is the caller's runner.submit_pending, with the
    price on the button. F1 sửa #7: a shot whose motion prompt (or a shot of its group) still breaks the formula is not ready either —
    a new job would fail at once on the same check."""
    from .states import JobState
    from . import prompt_formula
    access.need_edit(p, project_id, "xếp hàng lại clip hỏng vì đầu vào cũ")
    ready = {r["scene_id"] for r in llm_io.ready_for_video(p, project_id)}
    created, not_ready, reasons = 0, [], {}
    for r in input_failures(p, project_id):
        if r["scene_id"] not in ready:
            not_ready.append(r["idx"])
            reasons[r["idx"]] = "chưa đủ đầu vào (ảnh / motion chưa duyệt hoặc đã cũ)"
            continue
        red = prompt_formula.group_red_issues(p.conn, r["scene_id"], "motion")
        if red:
            not_ready.append(r["idx"])
            reasons[r["idx"]] = "prompt sai công thức — sửa ở Bước 3: " + " · ".join(red)
            continue
        p.transition(r["id"], JobState.RETRYABLE, note="đầu vào đã cũ — xếp hàng lại từ đầu vào mới")
        p.transition(r["id"], JobState.CANCELLED, actor="user", note="đầu vào đã cũ — thay bằng job mới từ đầu vào mới")
        if not p.conn.execute(f"SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN {LIVE}", (r["scene_id"],)).fetchone():
            p.create_job(r["scene_id"], "video_gen")
            created += 1
    return {"created": created, "not_ready": not_ready, "reasons": reasons}
