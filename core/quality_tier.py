"""N1 — video 2 bậc chất lượng (người dùng chốt 08/10, docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 5a; cờ
`two_tier_quality`, TẮT tới khi chạy thật). Cờ tắt: mọi hàm ở đây không đổi gì, "Thử rẻ" (projects.test_quality) giữ như cũ.

Cờ bật:
- "Thử rẻ" bị bỏ qua hoàn toàn (`cheap_mode` = False).
- Mỗi job video mang `jobs.quality_tier`: `draft` (nháp bậc thấp nhất: Seedance 2.5 `draft=True` 480p, model khác bậc thấp nhất của
  nó), `final` (bản cao từ một nháp đã duyệt, `jobs.draft_job_id`) hoặc `direct` (gen thẳng bản cao).
- Đường đi của shot (`path` / `route`): người ghi đè ở `motion_prompts.quality_path` (draft_first / direct) thắng; không thì (quy ước
  người dùng 15/10 — sửa chỗ ghi nhầm 13/10 "mọi shot nháp"): shot ĐƠN GIẢN (nhãn Đạo diễn `scenes.data["difficulty"]` = easy, không bị
  code ép khó — `hard_signs`) → gen thẳng Seedance 2.5 720p, lúc dựng phóng ffmpeg lên 1080p; shot KHÓ / quan trọng / chưa rõ / THIẾU nhãn
  → nháp Seedance 2.5 480p → người duyệt → nâng 1080p từ nháp. Shot đang có job gen thẳng còn sống / đã duyệt giữ tuyến đó
  (`on_direct_route`), shot đã có nháp / bản cao giữ tuyến nháp (`on_draft_route`) — không đổi đường giữa chừng.
- Trần TỰ gen lại (pipeline.Pipeline.auto_limit): chuỗi nháp 2, bản cao 1. Bấm "Gen bản cao" là việc người dùng (đếm lại từ 0).
- Trạng thái từng shot TỰ SUY từ jobs + review_log (`state`), không lưu cứng.
- Mọi lần gen lại phải đổi đầu vào theo lỗi lần trước (`regen_refusal`, CHUAN_XAY_DUNG luật 3)."""
import json
import time
from typing import Dict, List, Optional

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
# Shot dễ (path direct) → gen thẳng 720p, lúc dựng phóng 1080p bằng ffmpeg (không AI — quyết định 07/10). Shot khó /
# quan trọng / chưa rõ (draft_first) → nháp Seedance 2.5 `draft=True` 480p → người duyệt → nâng 1080p TỪ NHÁP (giữ nội dung).
# Người dùng 13/10 tối: bỏ Seedance 2.0 — video HẾT Seedance 2.5 (2.0 duyệt ≈ 6 %, #24 0/20): nhánh dễ đổi model 2.0 → 2.5 720p.
# 15/10 người dùng nhắc lại + sửa chỗ phiên 13/10 ghi nhầm "MỌI shot nháp 480p": shot dễ (nhãn Đạo diễn, không bị code ép khó) vẫn gen thẳng
# 2.5 720p (+ ffmpeg 1080p lúc dựng; 480p phóng vào bản giao thì CẤM — final_cut.require_delivery_resolution); shot khó → nháp 480p.
E1_DIRECT_MODEL, E1_DIRECT_RESOLUTION = "seedance-2.5", "720p"
E1_DRAFT_MODEL, DRAFT_RESOLUTION = "seedance-2.5", "480p"
SEEDANCE_20 = "dreamina-seedance-2-0-260128"
NEW_GEN = "bản cao sẽ là gen mới, nội dung khác nháp"
"""Cảnh báo khi bản cao KHÔNG nâng được từ nháp (nháp không phải Seedance 2.5 / hết hạn / không còn mã task)."""
NEED_CONFIRM = "cần xác nhận gen MỚI bản cao"
"""Mở đầu lý do chặn job `final` không nâng được từ nháp mà người chưa xác nhận (runner không tự gửi — #24 tự gửi lại ở 720p)."""
READ_FAIL = "không đọc được hạn bản nháp"
"""Rà F3: lỗi TẠM khi hỏi nhà cung cấp hạn bản nháp (mạng / dịch vụ) — job bản cao giữ hàng đợi thử lại, không fail, không tính là
"không nâng được" (upgrade_block)."""
UPGRADE_UNMEASURED = "giá nâng là ƯỚC TÍNH; 2.5 480p → 1080p 9:16 đã đo 0,5254 USD/s (#24 job 670–676, 38 s, 19,964 USD, task_usage 11/10/2026); đường khác tính dư"
UPGRADE_USD_PER_SECOND = 0.5254


def upgrade_price(ratio: str, seconds: float) -> Optional[float]:
    """Chỉ đường nâng Seedance 2.5 nháp 480p → 1080p dọc đã đo; không gửi lại ref."""
    from . import cost
    if ratio == "9:16":
        return UPGRADE_USD_PER_SECOND * max(4.0, seconds)
    usd = cost.seedance_estimate(SAMPLE_MODEL, FINAL_RESOLUTION, ratio, max(4.0, seconds))
    return None if usd is None else usd * 1.5


def draft_seconds(conn, draft) -> Optional[float]:
    """Clip lẻ dùng giây file thật; nhóm dùng sổ/gói gửi vì leader có thể đã cắt."""
    if draft is None:
        return None
    try:   # 12/10 (#24 671/672/675 ghi 4 s): the whole clip of the draft's task as downloaded — a lone clip's file is cut (05: 3 of 5 s)
        span = json.loads(draft["clip_span"] or "null") if "clip_span" in draft.keys() else None
        if isinstance(span, dict) and span.get("whole") and float(span["whole"]) > 0:
            return float(span["whole"])
    except (ValueError, TypeError):
        pass
    import os
    from . import ffmpeg_studio
    try:
        grouped = bool(draft["group_leader"] or json.loads(draft["sent_group"] or "[]"))
    except (ValueError, TypeError):
        grouped = True  # thiếu bằng chứng clip nguyên: không lấy phần đã cắt làm cả task
    path = draft["result_path"]
    local = bool(path) and "://" not in str(path) and not str(path).startswith(("\\\\", "//"))
    if local and not os.path.isabs(path) and not os.path.exists(path):     # U5: cwd first (worktree / bản sao), then the repo
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    if not grouped and local and os.path.isfile(path):
        actual = ffmpeg_studio.probe_duration(path)
        if actual and actual > 0:
            return float(actual)
    usage = conn.execute("SELECT quantity FROM usage_events WHERE job_id=? AND kind='video' AND unit='second' ORDER BY id DESC LIMIT 1", (draft["id"],)).fetchone()
    if usage and usage["quantity"] > 0:
        return float(usage["quantity"])
    try:
        package = json.loads(draft["sent_package"] or "{}")
        value = (package.get("params") or {}).get("duration_sec")
        if value and float(value) > 0:
            return float(value)
        group = json.loads(draft["sent_group"] or "[]")
        if group:
            return max(4.0, sum(float(r["duration_s"]) for r in group))
    except (ValueError, TypeError, KeyError):
        pass
    if local:
        seconds = ffmpeg_studio.probe_duration(path) if os.path.isfile(path) else None
        if seconds and seconds > 0:
            return float(seconds)
    return None
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


def _scene_data(conn, scene_id: int) -> Dict:
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    try:
        data = json.loads((row["data"] if row else None) or "{}")
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def label_from_director(data: Dict) -> Optional[str]:
    """Nhãn dễ/khó do ĐẠO DIỄN ghi (easy / complex / unknown), None = thiếu. Rà vòng gop-1510 (chặt): CHỈ khi `difficulty_by` ==
    "director" (shot_complexity.reconcile ghi) — nhãn code tự điền ("check"), dữ liệu trước 15/10 không rõ ai ghi → None (đi KHÓ, có
    lý do). 'easy' mà `difficulty_why` rỗng → None (mục 4: ví dụ prompt cũ ghi sẵn 'easy' + why rỗng). Kiểm chéo hạ 'dễ' → 'chưa rõ'
    chỉ để HIỂN THỊ (quyết định 15/10): `difficulty_director` = 'easy' → 'easy'."""
    if not isinstance(data, dict) or data.get("difficulty_by") != "director":
        return None
    level = data.get("difficulty")
    if level == "unknown" and data.get("difficulty_director") == "easy":
        level = "easy"
    if level not in DIFFICULTY:
        return None
    if level == "easy" and not str(data.get("difficulty_why") or "").strip():
        return None
    return level


def hard_signs(conn, scene_id: int, data: Optional[Dict] = None) -> List[str]:
    """Dấu hiệu KHÓ mà code biết (quy ước 15/10) — có bất kỳ dấu hiệu nào thì shot đi nháp trước, kể cả Đạo diễn ghi 'dễ': video tham
    chiếu, shot kỹ năng, khớp môi / take thoại (của shot, hoặc của NHÓM gen chung — rà gop-1510 mục 8), ≥ 3 nhân vật, shot quan trọng
    (hero / money shot). Người dùng 15/10: KHÔNG ép khó chỉ vì 2 nhân vật / thoại + tay — điểm kiểm chéo shot_complexity chỉ để hiển thị."""
    data = _scene_data(conn, scene_id) if data is None else data
    signs: List[str] = []
    mp = conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    ref_video = bool(mp is not None and "ref_video_path" in mp.keys() and mp["ref_video_path"])
    if ref_video:
        signs.append("có video tham chiếu")
    skill = bool(data.get("skill_phase") or data.get("skill_phase_video"))
    if not skill:
        try:
            from . import skill_dossier
            skill = bool(skill_dossier.route_reason(data))
        except Exception:  # noqa: BLE001 - hồ sơ kỹ năng đọc lỗi: không có bằng chứng kỹ năng, các dấu hiệu khác vẫn xét
            skill = False
    if skill:
        signs.append("shot kỹ năng")
    voiced = data.get("lip_sync") is True
    if not voiced and data.get("shot_no"):
        try:
            from . import lipsync
            voiced = lipsync.enabled() and lipsync.voiced(lipsync.method_for(data))
        except Exception:  # noqa: BLE001
            voiced = False
    if voiced:
        signs.append("khớp môi / take thoại")
    else:
        mate = _group_take(conn, scene_id)
        if mate is not None:
            signs.append(f"nhóm gen chung có take thoại (shot #{mate})")
    cast = [c for c in data.get("characters") or [] if c]
    if len(cast) >= 3:
        signs.append(f"{len(cast)} nhân vật")
    if data.get("shot_role") == "hero" or data.get("money_shot") is True:
        signs.append("shot quan trọng")
    return signs


def _group_take(conn, scene_id: int) -> Optional[int]:
    """Rà gop-1510 mục 8: model_router chọn take thoại theo NHÓM gen chung (một shot có thoại thấy mặt → cả clip nhóm là take Seedance
    2.5 kèm track giọng) → shot góc rộng không thoại trong nhóm đó cũng khó. Trả id shot take khác trong nhóm, None = không có."""
    try:
        from . import lipsync, shots
        if not lipsync.enabled():
            return None
        group = shots.group_of(conn, scene_id) or []
    except Exception:  # noqa: BLE001 - no shot table / lip sync module: only the shot's own signs
        return None
    for r in group:
        if r.get("id") == scene_id:
            continue
        d = r.get("data")
        if not isinstance(d, dict):
            d = _scene_data(conn, r["id"])
        try:
            if lipsync.method_for(d) == "take":
                return r["id"]
        except Exception:  # noqa: BLE001
            continue
    return None


def _direct_rejected(conn, scene_id: int) -> bool:
    """Job video mới nhất (bỏ hủy / hỏng) là gen thẳng và người đã LOẠI: lần sau nháp trước (13/10, giữ)."""
    row = conn.execute("SELECT quality_tier, state FROM jobs WHERE scene_id=? AND type='video_gen' AND state NOT IN ('cancelled','failed') "
                       "ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()
    return row is not None and (row["quality_tier"] or "direct") == "direct" and row["state"] == "rejected"


def route(conn, scene_id: int) -> Dict:
    """{"path": draft_first|direct, "why": câu lý do} — đường đi của MỘT shot, luôn có lý do (không im lặng).
    Thứ tự: người ghi đè (quality_path) > job đang dùng (gen thẳng còn sống / đã duyệt giữ gen thẳng; đã có nháp / bản cao giữ nháp —
    không đổi đường giữa chừng) > clip gen thẳng bị loại → nháp > dấu hiệu khó code biết (`hard_signs`) → nháp > nhãn Đạo diễn: 'dễ' →
    gen thẳng Seedance 2.5 720p; 'khó' / 'chưa rõ' → nháp; THIẾU nhãn → coi là khó, nháp (quy ước người dùng 15/10).
    Cờ two_tier_quality tắt: đường cũ của `path` (không ai dùng tới bậc)."""
    row = conn.execute("SELECT quality_path FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    chosen = row["quality_path"] if row is not None else None
    if chosen in ("draft_first", "direct"):
        return {"path": chosen, "why": "bạn chọn " + ("nháp trước" if chosen == "draft_first" else "gen thẳng")}
    if not enabled():
        return {"path": _path_flag_off(conn, scene_id), "why": "cờ two_tier_quality tắt — đường cũ"}
    if on_direct_route(conn, scene_id):
        return {"path": "direct", "why": "clip gen thẳng đang chạy / chờ duyệt / đã duyệt — giữ tuyến, không đổi giữa chừng"}
    if on_draft_route(conn, scene_id):
        return {"path": "draft_first", "why": "shot đã có nháp / bản cao đang dùng — giữ tuyến nháp → nâng 1080p"}
    if _direct_rejected(conn, scene_id):
        return {"path": "draft_first", "why": "clip gen thẳng trước đã bị loại — lần này nháp trước"}
    data = _scene_data(conn, scene_id)
    signs = hard_signs(conn, scene_id, data)
    if signs:
        return {"path": "draft_first", "why": "shot khó (code ép: " + ", ".join(signs) + ")"}
    level = label_from_director(data)
    if level is None:
        if data.get("difficulty") in DIFFICULTY and not data.get("difficulty_by"):
            return {"path": "draft_first", "why": "nhãn dễ/khó ghi trước 15/10, không rõ Đạo diễn hay code ghi — coi là khó (chạy lại "
                                                  "Đạo diễn để có nhãn mới)"}
        if data.get("difficulty") == "easy" and data.get("difficulty_by") == "director":
            return {"path": "draft_first", "why": "Đạo diễn ghi 'dễ' nhưng không nêu căn cứ (difficulty_why) — coi là khó"}
        return {"path": "draft_first", "why": "Đạo diễn chưa gắn nhãn dễ/khó — coi là khó"}
    if level == "easy":
        return {"path": "direct", "why": "shot dễ (Đạo diễn gắn 'dễ', code không thấy dấu hiệu khó)"}
    return {"path": "draft_first", "why": "shot " + ("khó" if level == "complex" else "chưa rõ độ khó") + " (nhãn Đạo diễn)"}


def path(conn, scene_id: int) -> str:
    """draft_first | direct — `route(...)["path"]`."""
    return route(conn, scene_id)["path"]


def _path_flag_off(conn, scene_id: int) -> str:
    """Cờ tắt (đường cũ, không ai dùng tới bậc): easy → direct; complex / unknown → nháp; chưa nhãn → kiểm chéo shot_complexity."""
    if on_draft_route(conn, scene_id):
        # lỗi 8 #27 (13/10, shot 18): shot đã vào tuyến nháp → bản cao (job video mới nhất là draft / final) GIỮ tuyến đó tới khi NGƯỜI
        # chọn khác (quality_path) — nhãn 'easy' + nhóm Seedance tách theo độ dài prompt làm đường tự trôi sang 'direct' → gen lại ra job
        # direct 896/901 gửi 2.5 480p không draft=True, không nâng 1080p được
        return "draft_first"
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


def on_draft_route(conn, scene_id: int) -> bool:
    """Job video mới nhất của shot (bỏ job đã hủy / hỏng — gửi lại, bị thay, lỗi nhà cung cấp) mang bậc draft / final: shot đang ở
    tuyến nháp → bản cao. Job mới nhất không có bậc (quality_tier NULL — trước N1 / lúc cờ tắt) = không dính (theo nhãn như cũ).
    Về "tự động" (quality_path NULL) không thoát tuyến này — người thoát bằng cách chọn rõ gen thẳng / mức khác 1080p."""
    row = conn.execute("SELECT quality_tier FROM jobs WHERE scene_id=? AND type='video_gen' AND state NOT IN ('cancelled','failed') "
                       "ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()
    return row is not None and row["quality_tier"] in ("draft", "final")


def on_direct_route(conn, scene_id: int) -> bool:
    """13/10: job video mới nhất của shot (bỏ job đã hủy / hỏng) là gen thẳng (bậc direct, hoặc không bậc — trước N1) và còn sống
    (đang chờ / chạy / chờ duyệt / đã duyệt): shot giữ tuyến gen thẳng tới khi người loại clip đó hoặc chọn khác. Loại rồi → tự động
    về nháp trước (quyết định 13/10)."""
    row = conn.execute("SELECT quality_tier, state FROM jobs WHERE scene_id=? AND type='video_gen' AND state NOT IN ('cancelled','failed') "
                       "ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()
    return row is not None and (row["quality_tier"] or "direct") == "direct" and row["state"] in _ACTIVE + _REVIEW + ("approved",)


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
                if parent["quality_tier"] == "final" and parent["draft_job_id"]:
                    # lỗi 8 #27 (872 → 896): gen lại bản cao mà nháp của nó đã cũ (ảnh vẽ lại / motion đổi) → bản cao từ nháp đó bị chặn
                    # "đầu vào đã đổi" — tuyến đúng là nháp MỚI từ đầu vào mới rồi mới nâng bản cao
                    draft = conn.execute("SELECT * FROM jobs WHERE id=?", (parent["draft_job_id"],)).fetchone()
                    if draft is None or draft_stale_reason(conn, draft):
                        return {"quality_tier": "draft", "draft_job_id": None}
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


def group_route(conn, scene_id: int) -> Dict:
    """{"path", "why"} của NHÓM gen chung (như group_path): lý do là của shot làm cả nhóm nháp-trước (hoặc của chính shot)."""
    try:
        from . import shots
        group = shots.group_of(conn, scene_id) or []
    except Exception:  # noqa: BLE001
        group = []
    ids = [r["id"] for r in group] or [scene_id]
    own = route(conn, scene_id)
    if own["path"] == "draft_first" or len(ids) < 2:
        return own
    for sid in ids:
        other = route(conn, sid)
        if other["path"] == "draft_first":
            return {"path": "draft_first", "why": f"nhóm gen chung một clip có shot #{sid} nháp-trước: {other['why']}"}
    return own


def e1_choice(conn, scene_id: int, choice: Dict) -> Dict:
    """E1 (cờ two_tier_quality BẬT — model_router.scene_choice gọi): model + độ phân giải theo đường của shot, chỉ cho họ Seedance
    (Kling / model khác giữ đường cũ). Người chọn tay (`source == "override"`) thắng; shot nháp-trước mà model chọn tay không phải
    Seedance 2.5 → `warning` = NEW_GEN (bản cao không nâng từ nháp được). Shot kỹ năng / khớp môi (c) giữ Seedance 2.5 (cần 2.5)."""
    canonical, family = _canonical(choice.get("model"))
    if family != "seedance":
        return choice
    way = group_route(conn, scene_id)
    if choice.get("source") == "override":
        if way["path"] == "draft_first" and canonical != SAMPLE_MODEL:
            return {**choice, "warning": f"{choice.get('model')} ở shot nháp-trước: {NEW_GEN} (chỉ Seedance 2.5 nâng được từ nháp)"}
        return choice
    if way["path"] == "direct":
        tail = f" — {way['why']}: gen thẳng Seedance 2.5 720p, lúc dựng phóng ffmpeg lên 1080p"
        if choice.get("skill") or choice.get("take"):
            return {**choice, "resolution": E1_DIRECT_RESOLUTION, "e1": "direct",
                    "reason": choice["reason"] + tail + " (giữ Seedance 2.5 vì cách này cần 2.5)"}
        return {**choice, "model": E1_DIRECT_MODEL, "resolution": E1_DIRECT_RESOLUTION, "e1": "direct", "reason": choice["reason"] + tail}
    return {**choice, "model": E1_DRAFT_MODEL, "resolution": DRAFT_RESOLUTION, "e1": "draft_first",
            "reason": choice["reason"] + f" — {way['why']}: nháp Seedance 2.5 480p, duyệt rồi nâng 1080p từ nháp"}


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


def outdated_final(conn, job, ok=None, used=None) -> Optional[str]:
    """C1 (13/10 #27 shot 17, scene 285): bản cao ĐÃ DUYỆT `job` không còn là clip của shot — nháp gốc (`draft_job_id`) cũ hơn nháp
    NGƯỜI duyệt mới nhất (nháp 903 → final 905 duyệt; rồi nháp 915 duyệt), hoặc take đang dùng (`takes.used`) là một nháp mới hơn bản
    cao này. Lý do tiếng Việt, hoặc None (bản cao vẫn tính). Job không phải final đã duyệt → None. Không xóa / đổi job: chỉ thôi tính
    nó trong state() / final_source_problem() (bản cao cũ vẫn là một take người chọn lại được).
    `ok` = approved_draft(conn, scene), `used` = takes.used(conn, scene) nếu đã có sẵn ("" = chưa tính)."""
    if "quality_tier" not in job.keys() or job["quality_tier"] != "final" or job["state"] != "approved" or not job["draft_job_id"]:
        return None
    ok = ok if ok is not None else approved_draft(conn, job["scene_id"])
    if ok is not None and job["draft_job_id"] < ok["id"]:
        return f"bản cao #{job['id']} làm từ nháp cũ #{job['draft_job_id']} — nháp #{ok['id']} được duyệt sau"
    if used is None:
        from . import takes
        used = takes.used(conn, job["scene_id"])
    if (used is not None and used["id"] > job["id"] and (used["quality_tier"] or "") == "draft"
            and used["state"] in takes_usable()):     # nháp đang chạy / bị loại chưa phải "clip đang dùng"
        return f"clip đang dùng là nháp #{used['id']} (mới hơn bản cao #{job['id']})"
    return None


def takes_usable():
    from .takes import USABLE
    return USABLE


def final_source_problem(conn, scene_id: int) -> Optional[str]:
    """Task bản cao đã xong nhưng nguồn chưa đọc được: phục hồi, không tự trả tiền gen lại. C1: bản cao đã thay (outdated_final) bỏ qua."""
    from . import final_cut
    jobs = _video_jobs(conn, scene_id)
    ok = approved_draft(conn, scene_id)
    for job in reversed(jobs):
        if (job["quality_tier"] or "direct") not in ("final", "direct") or job["state"] != "approved":
            continue
        if outdated_final(conn, job, ok):
            continue
        if final_cut.measured_size(job["result_path"]) is None:
            return "Bản cao đã có nhưng không đo được clip gốc — kiểm tra/tải lại nguồn của task đã gửi trước khi giao; không gen lại"
        return None
    return None


_RETIRABLE = ("queued", "retryable") + _REVIEW    # bản cao chưa gửi / chờ gửi lại / đã xong chờ duyệt — "running" = đang tốn tiền, giữ


def superseded_by(conn, job, ok=None) -> Optional[str]:
    """Bản cao `job` làm từ một nháp KHÔNG còn là nháp người duyệt mới nhất (13/10 #27 shot 5: final 855 từ nháp 788 kẹt chờ duyệt
    trong khi nháp 878 mới được duyệt → shot hiện "Bản cao · chờ duyệt", request_final từ chối): lý do tiếng Việt, hoặc None.
    `ok` = approved_draft(conn, scene) nếu đã có sẵn. Job không phải final / không gắn nháp → None."""
    if "quality_tier" not in job.keys() or job["quality_tier"] != "final" or not job["draft_job_id"]:
        return None
    ok = ok if ok is not None else approved_draft(conn, job["scene_id"])
    if ok is not None:
        if job["draft_job_id"] == ok["id"]:
            return None
        return (f"làm từ nháp cũ #{job['draft_job_id']} — nháp #{ok['id']} mới được duyệt" if job["draft_job_id"] < ok["id"]
                else f"nháp #{job['draft_job_id']} của bản cao này không còn được duyệt")
    draft = conn.execute("SELECT state FROM jobs WHERE id=?", (job["draft_job_id"],)).fetchone()
    if draft is None or draft["state"] != "approved":
        return f"nháp #{job['draft_job_id']} của bản cao này không còn được duyệt"
    return None


def retire_superseded_finals(p, scene_id: int, actor: str = "system") -> List[int]:
    """Nháp mới vừa được NGƯỜI duyệt (Pipeline.approve / keep_rejected), bản cao đang chạy vừa xong (runner), hoặc có người/QC bấm
    duyệt một bản cao đã bị thay (Pipeline.approve, dữ liệu cũ): bản cao làm từ nháp không còn là nháp duyệt mới nhất mà chưa gửi /
    đang chờ duyệt thì cho nghỉ — chưa gửi (queued / retryable) → cancelled, đã xong (succeeded / pending_review) → rejected — kèm ghi
    chú trong job_events; không ghi review_log (không phải người/QC chấm clip). Bản cao đang chạy ở nhà cung cấp (running) để nguyên:
    tiền đã trả, state() vẫn tính. Gỡ cờ escalated (rà 13/10: autopilot._blocked_scenes đếm job escalated đã loại = "hết số lần
    thử"); take của shot đang trỏ vào bản vừa nghỉ (takes.used = job mới nhất khi chưa chọn) → chọn lại nháp người đã duyệt.
    Trả về id các job đã cho nghỉ."""
    from . import takes
    from .states import JobState
    conn = p.conn
    ok = approved_draft(conn, scene_id)
    done = []
    for j in _video_jobs(conn, scene_id):
        if j["state"] not in _RETIRABLE:
            continue
        why = superseded_by(conn, j, ok)
        if not why:
            continue
        to = JobState.CANCELLED if j["state"] in ("queued", "retryable") else JobState.REJECTED
        p.transition(j["id"], to, actor=actor, note=f"bản cao cho nghỉ: {why}")
        conn.execute("UPDATE jobs SET escalated=0 WHERE id=?", (j["id"],))
        done.append(j["id"])
    if done:
        conn.commit()
        used = takes.used(conn, scene_id)
        if ok is not None and used is not None and used["id"] in done:
            takes.mark(conn, scene_id, ok["id"])
    return done


def state(conn, scene_id: int) -> str:
    """Một trong STATES, suy từ jobs + review_log. Job video không mang bậc (trước N1) tính như gen thẳng.
    13/10: bản cao làm từ nháp cũ (superseded_by) chưa gửi / chờ duyệt không tính — shot theo nháp mới nhất người đã duyệt; bản cao ĐÃ
    DUYỆT của nháp cũ / không còn là clip đang dùng (outdated_final, C1) cũng không tính."""
    ok_draft = approved_draft(conn, scene_id)
    from . import takes
    used = takes.used(conn, scene_id)
    jobs = [j for j in _video_jobs(conn, scene_id) if not (j["state"] in _RETIRABLE and superseded_by(conn, j, ok_draft))
            and not outdated_final(conn, j, ok_draft, used)]     # C1: bản cao đã duyệt của nháp cũ không chặn nháp mới
    tier = lambda j: j["quality_tier"] or "direct"   # noqa: E731
    from . import final_cut
    def deliverable(j):
        size = final_cut.measured_size(j["result_path"])
        return bool(size and min(size) >= 720)
    if final_source_problem(conn, scene_id):
        return "final_review"
    if any(tier(j) == "final" and j["state"] == "approved" and deliverable(j) for j in jobs):
        return "final_ok"
    if any(tier(j) == "direct" and j["state"] == "approved" and deliverable(j) for j in jobs):
        return "direct_ok"
    if any(tier(j) in ("final", "direct") and j["state"] in _ACTIVE for j in jobs):
        return "final_running"
    if any(tier(j) in ("final", "direct") and j["state"] in _REVIEW for j in jobs):
        return "final_review"           # 09/10 (người dùng, #24): bản cao đã gen xong, chờ duyệt — không phải "đang gen"
    drafts = [j for j in jobs if tier(j) == "draft"]
    ok = ok_draft
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
    source_problem = final_source_problem(conn, scene_id)
    if source_problem:
        return {"upgrade": False, "why": source_problem, "usd": None}
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
    source_problem = final_source_problem(conn, scene_id)
    if source_problem:
        raise ValueError(source_problem)
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


def final_hold_note(note: Optional[str]) -> bool:
    """C3: the failure note of a final held for the PERSON (pipeline.FINAL_HOLD; old data: 'stale_input: bản cao bị chặn: cần xác nhận
    gen MỚI…' / '…nháp cũ…' written before 13/10) — not an outdated input, never requeued as a new paid draft."""
    from .pipeline import FINAL_HOLD
    note = note or ""
    if note.startswith(FINAL_HOLD):
        return True
    return "bản cao bị chặn:" in note and (NEED_CONFIRM in note or "nháp cũ #" in note or "không còn được duyệt" in note)


def hold_prefix(conn, job) -> str:
    """C3: failure-note prefix when the runner does not send a FINAL — pipeline.STALE_INPUT only when the approved draft's input really
    changed (a new draft from the new input is the way); otherwise FINAL_HOLD (waits for the person: confirm / newer draft)."""
    from .pipeline import FINAL_HOLD, STALE_INPUT
    if "quality_tier" not in job.keys() or job["quality_tier"] != "final":
        return STALE_INPUT
    ok = approved_draft(conn, job["scene_id"])
    if ok is not None and ok["id"] == job["draft_job_id"] and draft_stale_reason(conn, ok):
        return STALE_INPUT
    return FINAL_HOLD


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


def draft_resolution_sent(choice: Dict, kwargs: Dict) -> bool:
    """Lần gửi này là Seedance 2.5 ở 480p do ĐƯỜNG NHÁP (E1 draft_first, hoặc 1080p chỉ có qua nâng — `final_resolution`), không phải
    người tự chọn 480p gen thẳng: gửi như vậy mà thiếu draft=True thì không nâng được (lỗi 8 #27)."""
    if kwargs.get("resolution") != DRAFT_RESOLUTION or _canonical(choice.get("model"))[0] != SAMPLE_MODEL:
        return False
    return choice.get("e1") == "draft_first" or bool(choice.get("final_resolution"))


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
    groups = _clip_groups(conn, pid)
    billed = _clip_seconds(conn, pid)
    out = {"usd": 0.0, "scenes": [], "unknown": []}
    for s in conn.execute("SELECT s.id, s.idx, m.duration_sec FROM scenes s JOIN motion_prompts m ON m.scene_id=s.id "
                          "WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall():
        lead = groups.get(s["id"], (s["id"], None))[0]
        st = state(conn, lead)
        if lead != s["id"]:
            continue
        if final_source_problem(conn, lead):
            out["unknown"].append(lead)
            continue
        if st in ("final_running", "final_review", "final_ok", "direct_ok") or group_path(conn, s["id"]) == "direct":   # rà F3: nhóm trộn = nháp
            continue
        seconds = billed.get(s["id"], draft_seconds(conn, approved_draft(conn, s["id"])) or float(s["duration_sec"] or 0))
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
    superseded = set()
    try:
        from . import seedance_refs
        current = {r["scene_id"]: r for r in conn.execute(
            "SELECT * FROM jobs WHERE project_id=? AND type='video_gen' "
            "AND COALESCE(quality_tier,'')!='final' AND state IN ('approved','succeeded','pending_review') ORDER BY id", (pid,))}
        # Nhóm đã gửi sống độc lập với cờ định tuyến cho lần gen mới.
        for job in conn.execute("SELECT * FROM jobs WHERE project_id=? AND type='video_gen' AND sent_group IS NOT NULL AND state IN ('approved','succeeded','pending_review') ORDER BY id DESC", (pid,)):
            try:
                group = json.loads(job["sent_group"] or "[]")
                if not group or job["quality_tier"] == "final":
                    continue
                latest = current.get(job["scene_id"])
                if latest is not None and latest["id"] != job["id"]:
                    superseded.update(int(r["id"]) for r in group)
                    continue
                whole = draft_seconds(conn, job)
                if whole:
                    for member in group:
                        sid = int(member["id"])
                        latest = current.get(sid)
                        if (latest is not None and latest["id"] > job["id"]
                                and latest["group_leader"] != job["id"]):
                            superseded.add(sid)
                            continue  # nháp riêng mới hơn không thuộc task nhóm cũ
                        out.setdefault(sid, (job["scene_id"], whole))
            except (ValueError, TypeError, KeyError):
                continue
        if not seedance_refs.enabled(conn, pid):
            return out
        for g in seedance_refs.groups(conn, pid):
            secs = [seedance_refs.floored(r["data"], _mp_seconds(conn, r["id"]) or float(r["data"].get("duration_s") or 0)) for r in g]
            whole = float(seedance_refs.seconds(secs))
            for r in g:
                if r["id"] not in superseded and g[0]["id"] not in superseded:
                    out.setdefault(r["id"], (g[0]["id"], whole))
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
        return SAMPLE_MODEL, upgrade_price(ratio, seconds)
    model = model_router.scene_choice(conn, scene_id, proj)["model"]
    canonical, family = _canonical(model)
    if family == "seedance":
        ref = cost.video_reference_seconds(conn, scene_id)
        return model, cost.seedance_estimate(canonical, FINAL_RESOLUTION if canonical == SAMPLE_MODEL else final_resolution(model), ratio, max(seconds, 4.0), ref["seconds"])
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
    if final_source_problem(conn, lead):
        return None
    if lead != scene_id:
        if state(conn, lead) in ("final_running", "final_review", "final_ok"):
            return 0.0                                  # made inside the group clip already on its way
        usd = _final_usd(conn, lead, proj, ratio, whole)[1]
    else:
        usd = _final_usd(conn, scene_id, proj, ratio, whole if whole is not None else (draft_seconds(conn, approved_draft(conn, scene_id)) or _mp_seconds(conn, scene_id) or 0.0))[1]
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
    """USD dự kiến CẢ PHIM (một lượt, chưa tính gen lại; tên cũ E1): shot gen thẳng (shot dễ / người chọn / clip đang dùng — quy ước 15/10)
    Seedance 2.5 720p (phóng ffmpeg 1080p lúc dựng, 0 USD); shot nháp-trước (khó / chưa rõ / thiếu nhãn) nháp 2.5 480p +
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
        ref = cost.video_reference_seconds(conn, r["scene_id"], r)
        if ref["seconds"] is None:
            out["unknown"].append(r["scene_id"])
            continue
        sec = max(billed, 4.0)
        if group_path(conn, r["scene_id"]) == "direct":
            model = canonical if r.get("skill") or r.get("take") or r.get("source") == "override" else _canonical(E1_DIRECT_MODEL)[0]
            out["usd"] += cost.seedance_estimate(model, E1_DIRECT_RESOLUTION, ratio, sec, ref["seconds"]) or 0.0
            out["direct"] += 1
        else:
            out["usd"] += (cost.seedance_estimate(SAMPLE_MODEL, DRAFT_RESOLUTION, ratio, sec, ref["seconds"]) or 0.0) + \
                          (upgrade_price(ratio, sec) or 0.0)
            out["draft_first"] += 1
    out["usd"] = round(out["usd"], 2)
    out["film_seconds"] = round(out["film_seconds"], 1)
    out["target_usd"] = next((cap for limit, cap in FILM_TARGETS if out["film_seconds"] < limit), None)
    out["within"] = None if out["target_usd"] is None else out["usd"] < out["target_usd"]
    target = (f", mục tiêu < {out['target_usd']:.0f} USD — " + ("ĐẠT" if out["within"] else "VƯỢT")) if out["target_usd"] else ""
    out["line"] = (f"Phim {out['film_seconds']:.0f} s ≈ {out['usd']:.2f} USD ({out['draft_first']} nháp Seedance 2.5 480p + nâng 1080p, "
                   f"{out['direct']} shot dễ gen thẳng Seedance 2.5 720p (+ phóng ffmpeg 1080p), {out['other']} model khác{target}; {UPGRADE_UNMEASURED})")
    return out


def running_draft_final_estimate(conn, pid: int, rows, pricing) -> Dict:
    """Chỉ giá bản cao còn thiếu của nháp đã gửi; không gửi/đếm lại task nháp, kể cả cờ OFF."""
    from . import cost, model_router
    _, ratio = _proj_ratio(conn, pid)
    by_scene = {r["scene_id"]: r for r in rows}
    jobs = conn.execute("SELECT * FROM jobs WHERE project_id=? AND type='video_gen' "
                        "AND state IN ('running','approved') AND external_id IS NOT NULL AND external_id!='' ORDER BY id DESC", (pid,)).fetchall()
    covered, result = set(), {"usd": 0.0, "clips": 0, "seconds": 0.0, "finals_1080": 0, "warnings": [], "unknown": [], "covered": set()}
    for job in jobs:
        if job["state"] == "approved":
            # Chỉ nháp hiện tại người đã duyệt, nâng được; final_only là cùng quyết định của quote.
            if not cost.video_need(conn, job["scene_id"]).get("final_only"):
                continue
            draft = approved_draft(conn, job["scene_id"])
            if draft is None or draft["id"] != job["id"]:
                continue
        if job['quality_tier'] == 'draft' and job['group_leader']:
            leader = conn.execute("SELECT * FROM jobs WHERE id=? AND project_id=? AND type='video_gen'", (job['group_leader'], pid)).fetchone()
            if leader is not None and leader['external_id'] == job['external_id'] and leader['quality_tier'] == 'draft':
                job = leader
        try:
            ids = {int(r["id"]) for r in json.loads(job["sent_group"] or "[]")} or {job["scene_id"]}
        except (ValueError, TypeError, KeyError):
            ids = {job["scene_id"]}
        if ids & covered:
            continue
        covered.update(ids)
        if job["quality_tier"] != "draft":
            continue
        members = [by_scene[sid] for sid in ids if sid in by_scene]
        if not members:
            continue
        seconds = draft_seconds(conn, job) or sum(float(r.get("seconds") or r.get("billed_seconds") or 0) for r in members)
        seconds = max(4.0, seconds)
        canonical, _ = _canonical(job["model"])
        if canonical == SAMPLE_MODEL:
            usd = upgrade_price(ratio, seconds)
            result["finals_1080"] += 1
            result["warnings"].append(f"shot {job['scene_id']}: nháp đã gửi tiền; chỉ cộng bản cao còn thiếu — {UPGRADE_UNMEASURED}")
        else:
            model = members[0]["model"]
            res = final_resolution(model)
            model_canonical, model_family = _canonical(model)
            if model_family == "seedance":
                ref = cost.video_reference_seconds(conn, members[0]["scene_id"], members[0])
                usd = cost.seedance_estimate(model_canonical, res, ratio, seconds, ref["seconds"])
                result["warnings"].extend(ref["warnings"])
            else:
                per = model_router.price_per_sec(model, res, pricing)
                usd = None if per is None else per * seconds
            result["warnings"].append(f"shot {job['scene_id']}: nháp đang chạy đã gửi tiền; bản giao còn cần gen ≥ 720p")
        if usd is None:
            result["unknown"].append(f"bản cao sau nháp task {job['id']}")
        else:
            result["usd"] += usd
        result["covered"].update(ids)     # cả nhóm đã có lượt bản cao này — estimate_run không đếm lại shot nào trong nhóm
        result["clips"] += 1
        result["seconds"] += seconds
    return result


def delivery_quote(conn, pid: int, rows, pricing) -> list:
    """Không báo giá gen thẳng 480p như bản giao, kể cả cờ hai bậc đang tắt."""
    two_tier = enabled()
    from . import cost, formats, model_router
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    ratio = formats.spec(formats.project_aspect(proj))["clip"]
    result = []
    for row in rows:
        r = dict(row)
        res = str(r.get("resolution") or "")
        if res.endswith("p") and res[:-1].isdigit() and int(res[:-1]) < 720 and not (two_tier and group_path(conn, r["scene_id"]) == "draft_first"):
            r["resolution"] = "720p"
            per = model_router.price_per_sec(r["model"], "720p", pricing)
            r["cost"] = None if per is None else per * r["billed_seconds"]
            canonical, family = _canonical(r["model"])
            if family == "seedance":
                ref = cost.video_reference_seconds(conn, r["scene_id"], r)
                r["cost"] = cost.seedance_estimate(canonical, "720p", ratio, r["billed_seconds"], ref["seconds"])
            r["warnings"] = list(r.get("warnings") or []) + ["480p chỉ dùng xem nháp; bản giao cần nâng 1080p hoặc gen ≥ 720p (báo giá 720p)"]
        result.append(r)
    return result


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
            ref = cost.video_reference_seconds(conn, r["scene_id"], r)
            if ref["seconds"] is None:
                out.setdefault("unknown", []).extend(ref["warnings"])
                continue
            draft = cost.seedance_estimate(SAMPLE_MODEL, "480p", ratio, max(billed, 4.0), ref["seconds"])
            final = upgrade_price(ratio, max(billed, 4.0))
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
