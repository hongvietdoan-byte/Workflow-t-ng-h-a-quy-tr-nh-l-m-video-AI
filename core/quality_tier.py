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
STATES = ("none", "draft_running", "draft_review", "draft_ok", "draft_stale", "final_running", "final_review", "final_ok", "direct_ok")
RETRY_LIMIT = {"draft": 2, "final": 1}
"""Số lần TỰ gen lại tối đa theo bậc (5a.3): nháp 2 → hết thì dừng, báo người dùng; bản cao 1 (dựa trên nháp đã duyệt)."""
SAMPLE_MODEL = "dreamina-seedance-2-5-260628"
FINAL_RESOLUTION = "1080p"
"""Bản cao nâng từ nháp Seedance 2.5 (`draft_task`): mặc định 1080p (clipai.submit_final_from_sample tham số hóa)."""
MAY_DIFFER = "nội dung có thể khác bản nháp"
# ---- E1 (người dùng chốt 09/10, docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md mục 5–5b; F3) --------------------------------------------
# Shot dễ (path direct) → gen thẳng Seedance 2.0 720p, lúc dựng phóng 1080p bằng ffmpeg (không AI — quyết định 07/10). Shot khó /
# quan trọng / chưa rõ (draft_first) → nháp Seedance 2.5 `draft=True` 480p → người duyệt → nâng 1080p TỪ NHÁP (giữ nội dung).
E1_DIRECT_MODEL, E1_DIRECT_RESOLUTION = "seedance", "720p"
E1_DRAFT_MODEL, DRAFT_RESOLUTION = "seedance-2.5", "480p"
SEEDANCE_20 = "dreamina-seedance-2-0-260128"
NEW_GEN = "bản cao sẽ là gen mới, nội dung khác nháp"
"""Cảnh báo khi bản cao KHÔNG nâng được từ nháp (nháp không phải Seedance 2.5 / hết hạn / không còn mã task)."""
NEED_CONFIRM = "cần xác nhận gen MỚI bản cao"
"""Mở đầu lý do chặn job `final` không nâng được từ nháp mà người chưa xác nhận (runner không tự gửi — #24 tự gửi lại ở 720p)."""
READ_FAIL = "không đọc được hạn bản nháp"
"""Rà F3: lỗi TẠM khi hỏi nhà cung cấp hạn bản nháp (mạng / dịch vụ) — job bản cao giữ hàng đợi thử lại, không fail, không tính là
"không nâng được" (upgrade_block)."""
UPGRADE_UNMEASURED = "giá nâng 2.5 → 1080p từ nháp là ƯỚC TÍNH (chưa đo thật)"
FILM_TARGETS = ((60.0, 30.0), (120.0, 60.0))
"""(phim dưới N giây, trần USD): < 1 phút < 30 USD, < 2 phút < 60 USD (người dùng 09/10)."""
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
    """draft_first | direct. Ghi đè của người (motion_prompts.quality_path) thắng nhãn Đạo diễn; easy → direct; complex / unknown → nháp
    trước; chưa có nhãn → theo kiểm chéo (shot_complexity.score: complex → nháp, còn lại gen thẳng — người dùng 09/10)."""
    row = conn.execute("SELECT quality_path FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    chosen = row["quality_path"] if row is not None else None
    if chosen in ("draft_first", "direct"):
        return chosen
    level = difficulty(conn, scene_id)["level"]
    if level is None:            # 09/10: chưa có nhãn (dự án cũ / chưa qua kiểm chéo) → kiểm chéo ngay: rõ khó → nháp, còn lại gen thẳng
        from . import shot_complexity
        drow = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
        try:
            data = json.loads((drow["data"] if drow else None) or "{}")
        except ValueError:
            data = {}
        return "draft_first" if shot_complexity.score(data)["suggest"] == "complex" else "direct"
    return "direct" if level == "easy" else "draft_first"


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
            # đợt B 09/10 (#24 chạy thử): người đổi ô Chất lượng sau lần gen trước (vd. bản cao 2.5 → 720p gen thẳng) thì lần gen lại theo
            # đường MỚI — kế thừa bậc cũ làm job 'final' bị chặn "đầu vào đã đổi sau khi duyệt nháp" và hỏng, không ra clip
            now = group_path(conn, scene_id)
            if (parent["quality_tier"] == "direct") == (now == "direct"):
                return {"quality_tier": parent["quality_tier"], "draft_job_id": parent["draft_job_id"]}
    # rà F3: theo đường của NHÓM gen chung (group_path) — e1_choice gửi cả nhóm bằng nháp 2.5 480p khi có shot khó, nên job của shot dễ
    # trong nhóm đó cũng là `draft` (không thì đi bậc direct: 2.5 480p KHÔNG kèm draft=True, không nâng 1080p được)
    return {"quality_tier": "direct" if group_path(conn, scene_id) == "direct" else "draft", "draft_job_id": None}


def _canonical(model: Optional[str]):
    """(canonical, family) of a ClipAI model name; (model, None) when unknown (mock / web-only)."""
    try:
        from .adapters.clipai import resolve_model
        return resolve_model(model)
    except Exception:  # noqa: BLE001
        return model, None


def group_path(conn, scene_id: int) -> str:
    """path() của shot, nhưng shot nằm trong nhóm gen chung (một clip cho cả nhóm) → nhóm có shot nháp-trước thì cả nhóm nháp-trước
    (một lần gửi chỉ có một model / một bậc)."""
    try:
        from . import shots
        group = shots.group_of(conn, scene_id) or []
    except Exception:  # noqa: BLE001 - no shot table (old project): the shot alone
        group = []
    ids = [r["id"] for r in group] or [scene_id]
    return "draft_first" if any(path(conn, sid) == "draft_first" for sid in ids) else "direct"


def e1_choice(conn, scene_id: int, choice: Dict) -> Dict:
    """E1 (cờ two_tier_quality BẬT — model_router.scene_choice gọi): model + độ phân giải theo đường của shot, chỉ cho họ Seedance
    (Kling / model khác giữ đường cũ). Người chọn tay (`source == "override"`) thắng; shot nháp-trước mà model chọn tay không phải
    Seedance 2.5 → `warning` = NEW_GEN (bản cao không nâng từ nháp được). Shot kỹ năng / khớp môi (c) giữ Seedance 2.5 (cần 2.5)."""
    canonical, family = _canonical(choice.get("model"))
    if family != "seedance":
        return choice
    way = group_path(conn, scene_id)
    if choice.get("source") == "override":
        if way == "draft_first" and canonical != SAMPLE_MODEL:
            return {**choice, "warning": f"{choice.get('model')} ở shot nháp-trước: {NEW_GEN} (chỉ Seedance 2.5 nâng được từ nháp)"}
        return choice
    if way == "direct":
        if choice.get("skill") or choice.get("take"):
            return {**choice, "resolution": E1_DIRECT_RESOLUTION, "e1": "direct",
                    "reason": choice["reason"] + " — E1: shot dễ — gen thẳng 720p (giữ Seedance 2.5 vì cách này cần 2.5), dựng phóng 1080p"}
        return {**choice, "model": E1_DIRECT_MODEL, "resolution": E1_DIRECT_RESOLUTION, "e1": "direct",
                "reason": choice["reason"] + " — E1: shot dễ — 2.0 720p, dựng phóng 1080p"}
    return {**choice, "model": E1_DRAFT_MODEL, "resolution": DRAFT_RESOLUTION, "e1": "draft_first",
            "reason": choice["reason"] + " — E1: shot khó / quan trọng / chưa rõ — nháp Seedance 2.5 480p, duyệt rồi nâng 1080p từ nháp"}


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
    if any(tier(j) in ("final", "direct") and j["state"] in _ACTIVE for j in jobs):
        return "final_running"
    if any(tier(j) in ("final", "direct") and j["state"] in _REVIEW for j in jobs):
        return "final_review"           # 09/10 (người dùng, #24): bản cao đã gen xong, chờ duyệt — không phải "đang gen"
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


def upgrade_block(conn, draft) -> Optional[str]:
    """Vì sao bản cao KHÔNG nâng được từ nháp này (None = nâng được, theo dữ liệu trong máy — hạn nháp ở nhà cung cấp kiểm lúc gửi,
    final_route): nháp không phải Seedance 2.5, không còn mã task, hoặc lần gửi bản cao trước đã bị chặn vì không nâng được."""
    if draft is None:
        return "chưa có bản nháp người đã duyệt"
    if _canonical(draft["model"])[0] != SAMPLE_MODEL:
        return f"bản nháp làm bằng {draft['model'] or '?'} (chỉ Seedance 2.5 nâng được từ nháp)"
    if not draft["external_id"]:
        return "không có mã task bản nháp ở nhà cung cấp"
    row = conn.execute("SELECT e.note FROM jobs j JOIN job_events e ON e.job_id=j.id WHERE j.draft_job_id=? AND j.quality_tier='final' "
                       "AND e.to_state='failed' AND e.note LIKE ? AND e.note NOT LIKE ? ORDER BY e.id DESC LIMIT 1",
                       (draft["id"], f"%{NEED_CONFIRM}%", f"%{READ_FAIL}%")).fetchone()   # rà F3: lỗi đọc hạn tạm thời không tính
    if row is not None:
        return "lần gửi bản cao trước không nâng được từ nháp (nháp hết hạn / nhà cung cấp không xác nhận)"
    return None


def final_offer(conn, scene_id: int) -> Dict:
    """Nút bản cao của một shot (UI + nút gom): {"upgrade": nâng từ nháp được?, "why": lý do không nâng được, "usd": giá ước tính}; không
    nâng được thì thêm "res" (độ phân giải thật của lần gen mới) + "res_note" (câu nói rõ cho nút / hộp xác nhận)."""
    why = upgrade_block(conn, approved_draft(conn, scene_id))
    out = {"upgrade": why is None, "why": why, "usd": scene_final_price(conn, scene_id)}
    if why:                                  # rà F3: the new gen's REAL resolution, said on the button and in the question
        from . import model_router
        model = model_router.scene_choice(conn, scene_id)["model"]
        res = final_resolution(model)
        name = model_router.label(model).split(" · ")[0]
        out.update(res=res, res_note=f"gen mới ở {res}" + ("" if res == FINAL_RESOLUTION else
                                                            f" — {name} qua API chưa có {FINAL_RESOLUTION}, lúc dựng phóng {FINAL_RESOLUTION}"))
    return out


def request_final(p, scene_id: int, actor: str = "user", confirm_new: bool = False) -> int:
    """Người bấm "Gen bản cao": job `final` gắn nháp đã duyệt (retry_count 0 — việc người dùng, không tính trần). ValueError khi
    cờ tắt / nháp chưa duyệt / nháp cũ / bản cao đang làm.
    F3 (#24): bản cao KHÔNG nâng được từ nháp (upgrade_block) = một lần gen MỚI, nội dung khác nháp → chỉ tạo job khi người xác nhận rõ
    (`confirm_new=True`) và có giá (scene_final_price); xác nhận được ghi vào `jobs.confirm_new` (runner chỉ gửi khi có)."""
    if not enabled():
        raise ValueError("Tính năng 2 bậc chất lượng đang tắt (two_tier_quality)")
    conn = p.conn
    block = final_block(conn, scene_id)
    if block:
        raise ValueError(f"Chưa gen bản cao được: {block}")
    if state(conn, scene_id) in ("final_running", "final_review", "final_ok"):
        raise ValueError("Shot đã có bản cao (đang làm hoặc đã duyệt)")
    draft = approved_draft(conn, scene_id)
    why = upgrade_block(conn, draft)
    usd = scene_final_price(conn, scene_id) if why else None
    if why and not confirm_new:
        from . import model_router
        res = final_resolution(model_router.scene_choice(conn, scene_id)["model"])
        raise ValueError(f"Bản cao không nâng được từ nháp ({why}) — {NEW_GEN} (gen mới ở {res})"
                         + (f", ≈ {usd:.2f} USD (ước tính)" if usd is not None else ", chưa có giá")
                         + ": bấm “⬆ Gen MỚI bản cao” và xác nhận")
    if why and usd is None:
        raise ValueError(f"Bản cao không nâng được từ nháp ({why}) và chưa tính được giá gen mới — không gửi (luật chi phí)")
    project_id = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()["project_id"]
    jid = p._insert_job(project_id, scene_id, "video_gen", quality_tier="final", draft_job_id=draft["id"])
    if why:
        conn.execute("UPDATE jobs SET confirm_new=? WHERE id=?",
                     (json.dumps({"by": actor, "usd": round(usd, 4), "why": why, "at": time.time()}, ensure_ascii=False), jid))
        conn.commit()
    return jid


def confirmed_new(job) -> bool:
    """Người đã xác nhận gen MỚI bản cao cho job này (request_final confirm_new)."""
    return "confirm_new" in job.keys() and bool(job["confirm_new"])


def needs_confirm(job, route: Dict) -> Optional[str]:
    """Job `final` không nâng được từ nháp (route["from_sample"] None) mà người CHƯA xác nhận gen mới → lý do chặn (bắt đầu bằng
    NEED_CONFIRM); None = được gửi. Lần tự gen lại bản cao kèm câu sửa (trần 1, RETRY_LIMIT) không cần xác nhận lại."""
    from .runner import model_fix
    if route.get("from_sample") or route.get("transient") or confirmed_new(job) or model_fix(job["retry_reason"]):
        return None
    return f"{NEED_CONFIRM} — {NEW_GEN} ({route.get('why') or 'không nâng được từ nháp'})"


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
        return {"from_sample": None, "why": f"{READ_FAIL} ({e})", "transient": True}
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
        out.update(draft=True, resolution=DRAFT_RESOLUTION)
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
    {"usd", "scenes": [{scene_id, idx, state, model, seconds, usd}], "unknown": [scene_id] (không tính được giá)}.
    F3: nâng được từ nháp (upgrade_block None) → Seedance 2.5 @ FINAL_RESOLUTION; không nâng được → gen MỚI bằng model của shot (E1:
    Seedance 2.5) ở final_resolution; nhóm gen chung một clip → giá cả nhóm ở shot đầu, shot sau 0 (`_clip_seconds`)."""
    proj, ratio = _proj_ratio(conn, pid)
    billed = _clip_seconds(conn, pid)
    out = {"usd": 0.0, "scenes": [], "unknown": []}
    for s in conn.execute("SELECT s.id, s.idx, m.duration_sec FROM scenes s JOIN motion_prompts m ON m.scene_id=s.id "
                          "WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall():
        st = state(conn, s["id"])
        if st in ("final_running", "final_review", "final_ok", "direct_ok") or group_path(conn, s["id"]) == "direct":   # rà F3: nhóm trộn = nháp
            continue
        seconds = float(s["duration_sec"] or 0)
        model, usd = _final_usd(conn, s["id"], proj, ratio, billed.get(s["id"], seconds))
        if usd is None:
            out["unknown"].append(s["id"])
        else:
            out["usd"] += usd
        out["scenes"].append({"scene_id": s["id"], "idx": s["idx"], "state": st, "model": model, "seconds": seconds, "usd": usd})
    out["usd"] = round(out["usd"], 4)
    return out


def _proj_ratio(conn, pid: int):
    from . import formats
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    return proj, (formats.spec(formats.project_aspect(proj))["clip"] if proj is not None else "16:9")


def _mp_seconds(conn, scene_id: int) -> Optional[float]:
    row = conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    return float(row["duration_sec"]) if row is not None and row["duration_sec"] else None


def _clip_groups(conn, pid: int) -> Dict[int, tuple]:
    """{scene_id: (shot đầu nhóm, giây clip cả nhóm)} cho mọi shot trong một nhóm Seedance gen chung (seedance_refs.groups)."""
    out: Dict[int, tuple] = {}
    try:
        from . import seedance_refs
        if not seedance_refs.enabled(conn, pid):
            return out
        for g in seedance_refs.groups(conn, pid):
            secs = [seedance_refs.floored(r["data"], _mp_seconds(conn, r["id"]) or float(r["data"].get("duration_s") or 0)) for r in g]
            whole = float(seedance_refs.seconds(secs))
            for r in g:
                out[r["id"]] = (g[0]["id"], whole)
    except Exception:  # noqa: BLE001 - no group data: every shot priced alone (higher — tính dư)
        return {}
    return out


def _clip_seconds(conn, pid: int) -> Dict[int, float]:
    """{scene_id: giây clip tính tiền} cho các nhóm Seedance gen chung (seedance_refs.groups): shot đầu = giây cả nhóm, shot sau = 0
    (nằm trong clip nhóm). Shot không trong nhóm: không có khóa (người gọi dùng giây của shot)."""
    return {sid: (whole if lead == sid else 0.0) for sid, (lead, whole) in _clip_groups(conn, pid).items()}


def final_resolution(model: Optional[str]) -> str:
    """Độ phân giải bản cao của một model: FINAL_RESOLUTION nếu luật model có (hoặc không rõ luật), không thì mức cao nhất của nó
    (Seedance 2.0 Fast API chỉ 480/720)."""
    from . import video_rules
    res = video_rules.rule(_canonical(model)[0] or "").get("resolutions") or []
    return FINAL_RESOLUTION if not res or FINAL_RESOLUTION in res else res[-1]


def _final_usd(conn, scene_id: int, proj, ratio: str, seconds: float):
    """(model, USD ước tính) của bản cao một shot: nâng từ nháp (2.5 @ 1080p — UPGRADE_UNMEASURED) hoặc gen mới bằng model của shot."""
    from . import cost, model_router
    if seconds <= 0:
        return SAMPLE_MODEL, 0.0                      # made inside its group's clip (priced on the group's first shot)
    if upgrade_block(conn, approved_draft(conn, scene_id)) is None:
        return SAMPLE_MODEL, cost.seedance_estimate(SAMPLE_MODEL, FINAL_RESOLUTION, ratio, max(seconds, 4.0))
    model = model_router.scene_choice(conn, scene_id, proj)["model"]
    canonical, family = _canonical(model)
    if family == "seedance":
        return model, cost.seedance_estimate(canonical, final_resolution(model), ratio, max(seconds, 4.0))
    per = model_router.price_per_sec(model)
    return model, (per * seconds if per is not None else None)


def scene_final_price(conn, scene_id: int) -> Optional[float]:
    """USD ước tính của bản cao MỘT shot (nút ⬆ Gen bản cao / Gen MỚI bản cao): theo clip nhóm như final_estimate. Rà F3: shot sau của
    một nhóm gen chung mà shot đầu CHƯA có bản cao (đang làm / đã duyệt) → bấm nó là kéo cả clip nhóm → giá cả nhóm (không phải 0)."""
    row = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return None
    proj, ratio = _proj_ratio(conn, row["project_id"])
    lead, whole = _clip_groups(conn, row["project_id"]).get(scene_id, (scene_id, None))
    if lead != scene_id:
        if state(conn, lead) in ("final_running", "final_review", "final_ok"):
            return 0.0                                  # made inside the group clip already on its way
        usd = _final_usd(conn, lead, proj, ratio, whole)[1]
    else:
        usd = _final_usd(conn, scene_id, proj, ratio, whole if whole is not None else (_mp_seconds(conn, scene_id) or 0.0))[1]
    return None if usd is None else round(usd, 4)


def batch_final_price(conn, scene_ids) -> Optional[float]:
    """Rà F3: USD của nút gom bản cao cho các shot `scene_ids` — mỗi nhóm gen chung tính MỘT lần (clip nhóm), shot lẻ theo giá riêng;
    None khi có shot chưa tính được giá."""
    ids = list(scene_ids)
    if not ids:
        return 0.0
    row = conn.execute("SELECT project_id FROM scenes WHERE id=?", (ids[0],)).fetchone()
    groups = _clip_groups(conn, row["project_id"]) if row is not None else {}
    total, seen = 0.0, set()
    for sid in ids:
        lead = groups.get(sid, (sid, None))[0]
        if lead in seen:
            continue
        seen.add(lead)
        usd = scene_final_price(conn, lead if lead in ids else sid)
        if usd is None:
            return None
        total += usd
    return round(total, 4)


def e1_estimate(conn, pid: int, pricing: Optional[Dict] = None) -> Dict:
    """USD dự kiến CẢ PHIM theo E1 (một lượt, chưa tính gen lại): shot dễ (direct) Seedance 2.0 720p; shot nháp-trước nháp 2.5 480p +
    nâng 2.5 1080p (UPGRADE_UNMEASURED); Kling / model khác theo giá hàng model_router.plan. Clip nhóm tính một lần (giây nhóm).
    Để Bước 1 / AI Dev System báo "phim X s ≈ Y USD, mục tiêu < 30 / 60". {"usd", "film_seconds", "target_usd", "within", "direct",
    "draft_first", "other", "unknown", "note", "line"}."""
    from . import cost, model_router
    _, ratio = _proj_ratio(conn, pid)
    out = {"usd": 0.0, "film_seconds": 0.0, "direct": 0, "draft_first": 0, "other": 0, "unknown": [], "note": UPGRADE_UNMEASURED}
    for r in model_router.plan(conn, pid, pricing):
        out["film_seconds"] += float(r.get("seconds") or 0)
        billed = float(r.get("billed_seconds") or 0)
        if billed <= 0:
            continue
        canonical, family = _canonical(r["model"])
        if family != "seedance":
            out["other"] += 1
            if r.get("cost") is None:
                out["unknown"].append(r["scene_id"])
            else:
                out["usd"] += r["cost"]
            continue
        sec = max(billed, 4.0)
        if group_path(conn, r["scene_id"]) == "direct":
            model = canonical if r.get("skill") or r.get("take") or r.get("source") == "override" else SEEDANCE_20
            out["usd"] += cost.seedance_estimate(model, E1_DIRECT_RESOLUTION, ratio, sec) or 0.0
            out["direct"] += 1
        else:
            out["usd"] += (cost.seedance_estimate(SAMPLE_MODEL, DRAFT_RESOLUTION, ratio, sec) or 0.0) + \
                          (cost.seedance_estimate(SAMPLE_MODEL, FINAL_RESOLUTION, ratio, sec) or 0.0)
            out["draft_first"] += 1
    out["usd"] = round(out["usd"], 2)
    out["film_seconds"] = round(out["film_seconds"], 1)
    out["target_usd"] = next((cap for limit, cap in FILM_TARGETS if out["film_seconds"] < limit), None)
    out["within"] = None if out["target_usd"] is None else out["usd"] < out["target_usd"]
    target = (f", mục tiêu < {out['target_usd']:.0f} USD — " + ("ĐẠT" if out["within"] else "VƯỢT")) if out["target_usd"] else ""
    out["line"] = (f"Phim {out['film_seconds']:.0f} s ≈ {out['usd']:.2f} USD (E1: {out['direct']} clip 2.0 720p, {out['draft_first']} "
                   f"nháp 2.5 480p + nâng 1080p, {out['other']} model khác{target}; {UPGRADE_UNMEASURED})")
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
