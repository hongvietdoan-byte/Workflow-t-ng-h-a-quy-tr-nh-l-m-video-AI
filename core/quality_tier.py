"""N1 — video 2 bậc chất lượng (người dùng chốt 08/10, docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 5a; cờ
`two_tier_quality`, TẮT tới khi chạy thật). Cờ tắt: mọi hàm ở đây không đổi gì, "Thử rẻ" (projects.test_quality) giữ như cũ.

Cờ bật:
- "Thử rẻ" bị bỏ qua hoàn toàn (`cheap_mode` = False).
- Mỗi job video mang `jobs.quality_tier`: `draft` (nháp bậc thấp nhất: Seedance 2.5 `draft=True` 480p, model khác bậc thấp nhất của
  nó), `final` (bản cao từ một nháp đã duyệt, `jobs.draft_job_id`) hoặc `direct` (gen thẳng bản cao).
- Đường đi của shot (`path`): người ghi đè ở `motion_prompts.quality_path` (draft_first / direct) thắng; không thì nhãn Đạo diễn
  `scenes.data["difficulty"]` (HỢP ĐỒNG với nhánh Đạo diễn: "easy" | "complex" | "unknown", kèm `difficulty_why`): easy → direct,
  complex / unknown / thiếu → draft_first.
- Trần TỰ gen lại (pipeline.Pipeline.auto_limit): chuỗi nháp 2, bản cao 1. Bấm "Gen bản cao" là việc người dùng (đếm lại từ 0).
- Trạng thái từng shot TỰ SUY từ jobs + review_log (`state`), không lưu cứng.
- Mọi lần gen lại phải đổi đầu vào theo lỗi lần trước (`regen_refusal`, CHUAN_XAY_DUNG luật 3)."""
import json
import time
from typing import Dict, Optional

TIERS = ("draft", "final", "direct")
PATHS = ("auto", "draft_first", "direct")
DIFFICULTY = ("easy", "complex", "unknown")
STATES = ("none", "draft_running", "draft_review", "draft_ok", "draft_stale", "final_running", "final_ok", "direct_ok")
RETRY_LIMIT = {"draft": 2, "final": 1}
"""Số lần TỰ gen lại tối đa theo bậc (5a.3): nháp 2 → hết thì dừng, báo người dùng; bản cao 1 (dựa trên nháp đã duyệt)."""
SAMPLE_MODEL = "dreamina-seedance-2-5-260628"
FINAL_RESOLUTION = "1080p"
"""Bản cao nâng từ nháp Seedance 2.5 (`draft_task`): mặc định 1080p (clipai.submit_final_from_sample tham số hóa)."""
MAY_DIFFER = "nội dung có thể khác bản nháp"
_ACTIVE = ("queued", "running", "retryable")
_REVIEW = ("succeeded", "pending_review")


def enabled() -> bool:
    from . import features
    return features.on("two_tier_quality")


def cheap_mode(proj) -> bool:
    """"Thử rẻ" của dự án còn hiệu lực không: cờ two_tier_quality bật → không bao giờ (bỏ qua test_quality hoàn toàn)."""
    if proj is None or "test_quality" not in proj.keys() or not proj["test_quality"]:
        return False
    return not enabled()


# ---- đường đi của shot -----------------------------------------------------------------------------------------------------------
def difficulty(conn, scene_id: int) -> Dict:
    """{"level": easy|complex|unknown|None, "why"} — nhãn Đạo diễn ghi trong scenes.data (None = chưa ghi)."""
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    try:
        data = json.loads((row["data"] if row else None) or "{}")
    except ValueError:
        data = {}
    level = data.get("difficulty")
    return {"level": level if level in DIFFICULTY else None, "why": data.get("difficulty_why")}


def path(conn, scene_id: int) -> str:
    """draft_first | direct. Ghi đè của người (motion_prompts.quality_path) thắng nhãn Đạo diễn; easy → direct; còn lại → nháp trước."""
    row = conn.execute("SELECT quality_path FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    chosen = row["quality_path"] if row is not None else None
    if chosen in ("draft_first", "direct"):
        return chosen
    return "direct" if difficulty(conn, scene_id)["level"] == "easy" else "draft_first"


def set_path(conn, scene_id: int, value: str) -> None:
    """Người dùng ghi đè đường đi của shot (auto = theo Đạo diễn)."""
    if value not in PATHS:
        raise ValueError(f"quality_path phải là một trong {PATHS}")
    conn.execute("UPDATE motion_prompts SET quality_path=? WHERE scene_id=?", (None if value == "auto" else value, scene_id))
    conn.commit()


def tier_for_new_job(conn, scene_id: int, parent_job_id: Optional[int] = None) -> Dict:
    """Bậc của một job video mới: lần thử lại mang bậc + nháp của job cha; job mới theo đường đi của shot (draft / direct)."""
    if parent_job_id is not None:
        parent = conn.execute("SELECT quality_tier, draft_job_id FROM jobs WHERE id=?", (parent_job_id,)).fetchone()
        if parent is not None and parent["quality_tier"]:
            return {"quality_tier": parent["quality_tier"], "draft_job_id": parent["draft_job_id"]}
    return {"quality_tier": "direct" if path(conn, scene_id) == "direct" else "draft", "draft_job_id": None}


def retry_limit(job) -> Optional[int]:
    """Trần tự gen lại theo bậc của job (None = không phải job 2 bậc hoặc cờ tắt → trần cũ)."""
    if not enabled() or "quality_tier" not in job.keys():
        return None
    return RETRY_LIMIT.get(job["quality_tier"] or "")


# ---- trạng thái tự suy -----------------------------------------------------------------------------------------------------------
def _video_jobs(conn, scene_id: int):
    return conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id", (scene_id,)).fetchall()


def _approved_by_person(conn, job_id: int) -> bool:
    row = conn.execute("SELECT reviewer_type, decision FROM review_log WHERE job_id=? ORDER BY id DESC LIMIT 1", (job_id,)).fetchone()
    return row is not None and row["decision"] == "approve" and row["reviewer_type"] == "user"


def approved_draft(conn, scene_id: int):
    """Nháp mới nhất NGƯỜI đã duyệt (QC máy duyệt chưa đủ: 'Người duyệt nháp' — 5a / mục 1 bước 2), hoặc None."""
    for j in reversed(_video_jobs(conn, scene_id)):
        if j["quality_tier"] == "draft" and j["state"] == "approved" and _approved_by_person(conn, j["id"]):
            return j
    return None


def draft_stale_reason(conn, draft) -> Optional[str]:
    """Đầu vào hiện tại của shot khác đầu vào bản nháp đã duyệt (KLD-1 stale_input): lý do tiếng Việt, hoặc None."""
    return _input_changed(conn, draft)


def _input_changed(conn, job) -> Optional[str]:
    """Đầu vào hiện tại (ảnh đã duyệt, motion prompt / thời lượng / model / âm thanh) khác dấu đầu vào job đã gửi: lý do, hoặc None.
    Job chưa có dấu (chưa gửi / dữ liệu cũ) → None (không chứng minh được là đổi)."""
    from . import lineage
    mp = conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (job["scene_id"],)).fetchone()
    if mp is None:
        return "motion prompt đã bị xóa"
    if mp["state"] != "approved":
        return "motion prompt đang sửa / chưa duyệt lại"
    image = lineage.approved_image_id(conn, job["scene_id"])
    try:
        from .shots import image_scene
        base = image_scene(conn, job["scene_id"])
        if base and base != job["scene_id"]:
            image = lineage.approved_image_id(conn, base)
    except Exception:  # noqa: BLE001 - no shot table data (old projects): the shot's own picture
        pass
    if job["source_job_id"] and image != job["source_job_id"]:
        return "ảnh đã được thay"
    if job["input_hash"]:
        proj = conn.execute("SELECT * FROM projects WHERE id=?", (job["project_id"],)).fetchone()
        aspect = proj["aspect"] if proj is not None else None
        if not lineage.video_hash_ok(job["input_hash"], mp, aspect, lineage._video_model(conn, job["scene_id"], proj, mp),
                                     lineage._audio(proj)):
            return "motion prompt / thời lượng / model / âm thanh đã đổi"
    return None


def state(conn, scene_id: int) -> str:
    """Một trong STATES, suy từ jobs + review_log. Job video không mang bậc (trước N1) tính như gen thẳng."""
    jobs = _video_jobs(conn, scene_id)
    tier = lambda j: j["quality_tier"] or "direct"   # noqa: E731
    if any(tier(j) == "final" and j["state"] == "approved" for j in jobs):
        return "final_ok"
    if any(tier(j) == "direct" and j["state"] == "approved" for j in jobs):
        return "direct_ok"
    if any(tier(j) in ("final", "direct") and j["state"] in _ACTIVE + _REVIEW for j in jobs):
        return "final_running"
    drafts = [j for j in jobs if tier(j) == "draft"]
    ok = approved_draft(conn, scene_id)
    newer = [j for j in drafts if ok is None or j["id"] > ok["id"]]
    if any(j["state"] in _ACTIVE for j in newer):
        return "draft_running"
    if any(j["state"] in _REVIEW or (j["state"] == "approved" and not _approved_by_person(conn, j["id"])) for j in newer):
        return "draft_review"
    if ok is not None:
        return "draft_stale" if draft_stale_reason(conn, ok) else "draft_ok"
    return "none"


def final_block(conn, scene_id: int) -> Optional[str]:
    """Vì sao CHƯA được gen bản cao từ nháp (None = được): nháp chưa duyệt / đầu vào đã đổi sau khi duyệt nháp."""
    ok = approved_draft(conn, scene_id)
    if ok is None:
        st = state(conn, scene_id)
        return {"draft_running": "bản nháp đang gen", "draft_review": "bản nháp chưa được người duyệt"}.get(
            st, "chưa có bản nháp người đã duyệt")
    stale = draft_stale_reason(conn, ok)
    if stale:
        return f"đầu vào đã đổi sau khi duyệt nháp ({stale}) — gen nháp lại từ đầu vào mới"
    return None


def request_final(p, scene_id: int, actor: str = "user") -> int:
    """Người bấm "Gen bản cao": job `final` gắn nháp đã duyệt (retry_count 0 — việc người dùng, không tính trần). ValueError khi
    cờ tắt / nháp chưa duyệt / nháp cũ / bản cao đang làm."""
    if not enabled():
        raise ValueError("Tính năng 2 bậc chất lượng đang tắt (two_tier_quality)")
    conn = p.conn
    block = final_block(conn, scene_id)
    if block:
        raise ValueError(f"Chưa gen bản cao được: {block}")
    if state(conn, scene_id) in ("final_running", "final_ok"):
        raise ValueError("Shot đã có bản cao (đang làm hoặc đã duyệt)")
    draft = approved_draft(conn, scene_id)
    project_id = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()["project_id"]
    return p._insert_job(project_id, scene_id, "video_gen", quality_tier="final", draft_job_id=draft["id"])


# ---- gửi bản cao -----------------------------------------------------------------------------------------------------------------
def final_route(conn, job, provider) -> Dict:
    """Cách gửi một job `final`: {"from_sample": draft external id | None, "why": lý do không nâng từ nháp (→ gửi lại đúng đầu vào
    ở bậc cao, MAY_DIFFER)}. Nâng từ nháp chỉ khi: nháp là Seedance 2.5, còn mã task, nhà cung cấp xác nhận là bản nháp còn hạn, và
    job này không mang câu sửa (bản cao gen lại kèm câu sửa phải gửi lại đầu vào — draft_task không nhận prompt)."""
    from .runner import model_fix
    draft = conn.execute("SELECT * FROM jobs WHERE id=?", (job["draft_job_id"],)).fetchone() if job["draft_job_id"] else None
    if draft is None:
        return {"from_sample": None, "why": "không có bản nháp gắn với job"}
    if model_fix(job["retry_reason"]):
        return {"from_sample": None, "why": "bản cao gen lại kèm câu sửa — gửi lại đầu vào (bản nháp không nhận prompt sửa)"}
    try:
        from .adapters.clipai import resolve_model
        canonical = resolve_model(draft["model"])[0]
    except Exception:  # noqa: BLE001 - unknown model name: not the 2.5 sample
        canonical = draft["model"]
    if canonical != SAMPLE_MODEL:
        return {"from_sample": None, "why": f"bản nháp làm bằng {draft['model'] or '?'} (chỉ Seedance 2.5 nâng được từ nháp)"}
    if not draft["external_id"] or not hasattr(provider, "submit_final_from_sample"):
        return {"from_sample": None, "why": "không có mã task bản nháp ở nhà cung cấp"}
    try:
        meta = provider.task_usage(draft["external_id"]) if hasattr(provider, "task_usage") else None
    except Exception as e:  # noqa: BLE001 - cannot confirm the sample: resend instead of paying blind
        return {"from_sample": None, "why": f"không đọc được hạn bản nháp ({e})"}
    expiry = float((meta or {}).get("draft_expired_at") or 0)
    if expiry > 1e12:
        expiry /= 1000
    if not meta or not meta.get("is_draft") or expiry <= time.time():
        return {"from_sample": None, "why": "bản nháp đã hết hạn ở nhà cung cấp"}
    return {"from_sample": draft["external_id"], "why": None}


def low_tier(kwargs: Dict, model: Optional[str]) -> Dict:
    """Bậc thấp nhất của model cho một job nháp: Seedance 2.5 `draft=True` (480p, nâng lên bản cao được); Seedance khác độ phân giải
    thấp nhất trong luật model; Kling chế độ std."""
    from . import video_rules
    try:
        from .adapters.clipai import resolve_model
        canonical, family = resolve_model(model)
    except Exception:  # noqa: BLE001 - unknown model (mock): lowest known resolution only
        canonical, family = model, None
    out = dict(kwargs)
    if canonical == SAMPLE_MODEL:
        out.update(draft=True, resolution="480p")
    elif family == "omni":
        out.pop("resolution", None)
        out["kling_mode"] = "std"
    else:
        res = video_rules.rule(canonical or "").get("resolutions") or ["480p"]
        out["resolution"] = res[0]
    return out


# ---- kiểm khâu gen lại (5a.4.4) --------------------------------------------------------------------------------------------------
def regen_refusal(conn, job, new_reason: Optional[str]) -> Optional[str]:
    """Lần gen lại này có đổi đầu vào theo lỗi lần trước không (CHUAN_XAY_DUNG luật 3). Trả lý do TỪ CHỐI (tiếng Việt) khi prompt
    gửi model (câu sửa) y hệt lần trước VÀ đầu vào (ảnh / motion prompt / model) không đổi; None = được gen lại.
    Job hỏng vì lỗi nhà cung cấp (failed, không phải đầu vào cũ) được gửi lại nguyên đầu vào — không có gì để sửa."""
    from .pipeline import MISSING_INPUT, STALE_INPUT
    from .runner import model_fix
    if job["type"] != "video_gen":
        return None
    if job["state"] == "failed":
        note = conn.execute("SELECT note FROM job_events WHERE job_id=? AND to_state='failed' ORDER BY id DESC LIMIT 1",
                            (job["id"],)).fetchone()
        if not (note and (note["note"] or "").startswith((STALE_INPUT, MISSING_INPUT))):
            return None
    norm = lambda t: " ".join((t or "").split()).rstrip(". ").lower()   # noqa: E731 - "Fix a." == "fix a"
    new_fix, old_fix = model_fix(new_reason), model_fix(job["retry_reason"])
    if new_fix and norm(new_fix) != norm(old_fix):
        return None
    if not job["input_hash"] and not job["source_job_id"]:
        return None                                   # never sent / old data: nothing proves the input is the same
    if _input_changed(conn, job):
        return None
    return ("gen lại y nguyên lần trước (ảnh, motion prompt, model không đổi" + (", câu sửa trùng lần trước" if new_fix else
            ", không có câu sửa") + ") — ghi lỗi cần sửa (QC / ghi chú của bạn) hoặc sửa đầu vào trước (CHUAN_XAY_DUNG luật 3)")


# ---- giá bản cao còn phải gen ----------------------------------------------------------------------------------------------------
def final_estimate(conn, pid: int) -> Dict:
    """Tổng giá (tham khảo) các bản cao CÒN PHẢI GEN của dự án: mọi shot đường nháp-trước chưa có bản cao (đang làm / đã duyệt).
    Nháp Seedance 2.5 → giá 2.5 @ FINAL_RESOLUTION (cost.seedance_estimate); model khác → model_router.price_per_sec × giây.
    {"usd", "scenes": [{scene_id, idx, state, model, seconds, usd}], "unknown": [scene_id] (không tính được giá)}."""
    from . import cost, formats, model_router
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    ratio = formats.spec(formats.project_aspect(proj))["clip"] if proj is not None else "16:9"
    out = {"usd": 0.0, "scenes": [], "unknown": []}
    for s in conn.execute("SELECT s.id, s.idx, m.duration_sec FROM scenes s JOIN motion_prompts m ON m.scene_id=s.id "
                          "WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall():
        st = state(conn, s["id"])
        if st in ("final_running", "final_ok", "direct_ok") or path(conn, s["id"]) == "direct":
            continue
        seconds = float(s["duration_sec"] or 0)
        draft = approved_draft(conn, s["id"])
        model = (draft["model"] if draft is not None else None) or model_router.scene_choice(conn, s["id"], proj)["model"]
        try:
            from .adapters.clipai import resolve_model
            canonical = resolve_model(model)[0]
        except Exception:  # noqa: BLE001
            canonical = model
        if canonical == SAMPLE_MODEL:
            usd = cost.seedance_estimate(SAMPLE_MODEL, FINAL_RESOLUTION, ratio, max(seconds, 4.0))
        else:
            per = model_router.price_per_sec(model)
            usd = per * seconds if per is not None and seconds else None
        if usd is None:
            out["unknown"].append(s["id"])
        else:
            out["usd"] += usd
        out["scenes"].append({"scene_id": s["id"], "idx": s["idx"], "state": st, "model": model, "seconds": seconds, "usd": usd})
    out["usd"] = round(out["usd"], 4)
    return out


def run_estimate(conn, pid: int, rows, pricing: Optional[Dict] = None) -> Dict:
    """08/10 (#24): phần ước tính chạy tự động mà quy trình 2 bậc THÊM vào giá từng shot (cost.estimate_run, các hàng model_router.plan
    chưa gen): shot nháp-trước trả thêm một NHÁP (bậc thấp nhất của model, như `low_tier`) và — nháp Seedance 2.5 — bản cao ở
    FINAL_RESOLUTION thay cho độ phân giải hàng `plan` ghi. Tính dư (luật chi phí): giá bậc thấp không có → lấy giá hàng (cao hơn).
    Cờ tắt → 0. {"usd", "drafts": số nháp, "finals_1080": số bản cao 2.5 nâng lên 1080p}."""
    out = {"usd": 0.0, "drafts": 0, "finals_1080": 0}
    if not enabled():
        return out
    from . import cost, formats, model_router, video_rules
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    ratio = formats.spec(formats.project_aspect(proj))["clip"] if proj is not None else "16:9"
    for r in rows:
        billed = float(r.get("billed_seconds") or 0)
        if billed <= 0 or path(conn, r["scene_id"]) == "direct":
            continue
        model, row_usd = r["model"], r.get("cost")
        try:
            from .adapters.clipai import resolve_model
            canonical, family = resolve_model(model)
        except Exception:  # noqa: BLE001 - unknown model: priced like the row
            canonical, family = model, None
        if canonical == SAMPLE_MODEL:
            draft = cost.seedance_estimate(SAMPLE_MODEL, "480p", ratio, max(billed, 4.0))
            final = cost.seedance_estimate(SAMPLE_MODEL, FINAL_RESOLUTION, ratio, max(billed, 4.0))
            if final is not None and final > (row_usd or 0.0):
                out["usd"] += final - (row_usd or 0.0)
                out["finals_1080"] += 1
        else:
            low = None if family == "omni" else ((video_rules.rule(canonical or "").get("resolutions") or [None])[0])
            per = model_router.price_per_sec(model, low, pricing)
            draft = per * billed if per is not None else None
        out["usd"] += draft if draft is not None else (row_usd or 0.0)
        out["drafts"] += 1
    out["usd"] = round(out["usd"], 4)
    return out
