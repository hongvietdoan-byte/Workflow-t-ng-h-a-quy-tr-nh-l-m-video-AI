"""V3.1 M5.1 (DP5, cloud-C 20/10) — REPAIR ROUTER theo mã lỗi: CHỈ ĐỀ XUẤT. Thiết kế docs/V3_1_M5_THIET_KE_REPAIR_RELEASE_2026-10-20.md mục 2.

Cờ `repair_router` (mặc định TẮT — G2-6): tắt → không đọc, không ghi gì; đường gen lại hiện có (Pipeline.apply_qc / retry / _no_auto_retry,
AUTO_REGEN_LIMIT) y nguyên. Bật → mỗi lần QC không đạt, router lập `repair_plan` {qc_code, action, input_delta, attempt_no, limit, stop_code,
needs_person, auto_ok: False} và GHI (diag `repair_plan`) — KHÔNG tự tạo / gửi job (tự gửi = Cấp 3, C3-10 để sau). Mọi job vẫn qua runner
(spend_gate, pause_before_submit, poll_claim, submit_unknown — giữ nguyên).

Luật 6 CHUAN_XAY_DUNG: gen lại phải đổi đầu vào; tự động ảnh ≤ 3 / video ≤ 2; cùng lỗi 2 lần → dừng hỏi người, báo lớp cần sửa."""
from typing import Dict, Iterable, List, Optional

FLAG = "repair_router"
CODE = "repair_plan"

# qc_code → (hành động, đầu vào phải đổi, trần tự động {loại job: lần}, dừng hỏi người khi) — thiết kế mục 2.1
REPAIR_ACTIONS: Dict[str, tuple] = {
    "QC-PKG-VI_TEXT": ("FIX_PACKAGE", "dịch / bỏ chữ Việt khỏi prompt (video_pregen)", {"image_gen": 0, "video_gen": 0}, "sửa gói vẫn đỏ"),
    "QC-PKG-FORM_PICTURE_MISSING": ("FIX_PACKAGE", "gắn ảnh form từ Kho (_ref_lint)", {"image_gen": 0, "video_gen": 0},
                                    "Kho thiếu ảnh form → hỏi"),
    "QC-PKG-PROMPT_TOO_LONG": ("FIX_PACKAGE", "rút gọn theo trần ký tự video_rules", {"image_gen": 0, "video_gen": 0}, "vẫn quá trần"),
    "QC-L1-IDENTITY_DRIFT": ("SWAP_REF+REWRITE_PROMPT", "ảnh tham chiếu nhân vật / form khác (BYĐ kho_id) + câu sửa trang phục",
                             {"image_gen": 3, "video_gen": 2}, "lặp cùng mã lần 2; ref-only look-drift → hỏi ngay"),
    "QC-L2-FORM_OUTFIT": ("SWAP_REF+REWRITE_PROMPT", "ảnh form / trang phục khác + câu sửa", {"image_gen": 3, "video_gen": 2}, "lặp lần 2"),
    "QC-L3-EXTRA_PEOPLE": ("REWRITE_PROMPT", "câu 'only N people' + negative", {"image_gen": 3, "video_gen": 2}, "lặp lần 2"),
    "QC-L4-POSE_ACTION": ("REWRITE_PROMPT", "câu hành động theo BYĐ", {"image_gen": 3, "video_gen": 2}, "lặp lần 2; khác ý đồ BYĐ → hỏi"),
    "QC-V4-MOTION_VS_BYD": ("REWRITE_PROMPT", "motion prompt theo BYĐ", {"image_gen": 3, "video_gen": 2}, "lặp lần 2; khác ý đồ → hỏi"),
    "QC-L6-SIZE_MISMATCH": ("REFRAME", "khung cắt / câu cỡ cảnh (framing_guard)", {"image_gen": 3, "video_gen": 0},
                            "qua vai / ý đồ (A5) → REVIEW, không tự sửa"),
    "QC-L7-PROP_MISSING": ("REWRITE_PROMPT+SWAP_REF", "câu đạo cụ + ảnh vật (Kho)", {"image_gen": 3, "video_gen": 2}, "lặp lần 2"),
    "QC-L9-HORIZON_MISMATCH": ("REPLATE", "plate / camera 3D, nền khác", {"image_gen": 3, "video_gen": 0},
                               "nền không trời (G20) → không sửa; không có plate → hỏi"),
    "QC-L11-PLACE_MISMATCH": ("REPLATE", "plate / camera 3D, nền khác", {"image_gen": 3, "video_gen": 0}, "không có plate → hỏi"),
    "QC-L13-CONTINUITY": (None, "", {"image_gen": 0, "video_gen": 0}, "luôn REVIEW (D07) — đồ thị M3.4 chỉ shot phụ thuộc"),
    "QC-L14-ARTIFACT": ("REGEN_NEW_SEED", "seed mới + câu 'clean hands/face' (≠ câu lần trước)", {"image_gen": 3, "video_gen": 2},
                        "lặp lần 2"),
    "QC-V1-DRIFT": ("REWRITE_PROMPT|TRIM", "motion prompt / điểm cắt (TRIM 0 USD)", {"image_gen": 0, "video_gen": 2},
                    "TRIM đủ → không gen; lặp lần 2"),
    "QC-V1-FIRST_FRAME_MISMATCH": ("REWRITE_PROMPT|ROUTE_FIRST_FRAME", "chế độ khung đầu (M2.8) / câu khóa khung đầu",
                                   {"image_gen": 0, "video_gen": 2}, "lặp lần 2"),
    "QC-V2-JERK_FREEZE": ("REWRITE_PROMPT|TRIM", "motion prompt / điểm cắt", {"image_gen": 0, "video_gen": 2}, "TRIM đủ → không gen"),
    "QC-V2-STILL_OVER_1_5S": ("REWRITE_PROMPT|TRIM", "motion prompt / cắt đoạn đứng", {"image_gen": 0, "video_gen": 2}, "TRIM đủ → không gen"),
    "QC-V2-REF_TRANSITION": ("TRIM", "cắt đầu clip / làm ref mới bỏ khúc chuyển cảnh (B8)", {"image_gen": 0, "video_gen": 0},
                             "không gen lại vì lỗi của ref"),
    "QC-V3-LIP_SYNC": ("RESYNC|REGEN", "độ lệch audio (0 USD) rồi clip", {"image_gen": 0, "video_gen": 2}, "lặp lần 2"),
    "QC-A2-PEAK_OVER": ("RERENDER", "limiter / thông số dựng (0 USD)", {"image_gen": 0, "video_gen": 0}, "vẫn báo sau 2 lần dựng"),
    "QC-A4-LENGTH_MISMATCH": ("RERENDER", "độ dài shot / dựng (0 USD)", {"image_gen": 0, "video_gen": 0}, "vẫn báo sau 2 lần dựng"),
    "QC-A4-DELIVERY_RES": ("RERENDER", "cỡ khung giao (0 USD)", {"image_gen": 0, "video_gen": 0}, "vẫn báo sau 2 lần dựng"),
    "QC-A4-BLACK_FRAME": ("RERENDER", "điểm nối / clip đen (0 USD)", {"image_gen": 0, "video_gen": 0}, "vẫn báo sau 2 lần dựng"),
    "QC-A4-FREEZE_FRAME": ("RERENDER", "điểm nối / clip đứng (0 USD)", {"image_gen": 0, "video_gen": 0}, "vẫn báo sau 2 lần dựng"),
    "QC-A2-SILENT_GAP": (None, "", {"image_gen": 0, "video_gen": 0}, "REVIEW (im lặng có thể là ý đồ)"),
}
# Tiêu chí QC hiện có (data/qc_checklist.json) → qc_code. Chỉ những cặp chắc nghĩa; tiêu chí khác (mood_lighting, consistency, scale,
# grounding, physics) chưa có mã → kế hoạch dừng REPAIR_UNMAPPED (nói rõ, không đoán).
CRITERION_CODE = {"character": "QC-L1-IDENTITY_DRIFT", "identity": "QC-L1-IDENTITY_DRIFT", "hands_face": "QC-L14-ARTIFACT",
                  "artifacts": "QC-L14-ARTIFACT", "composition": "QC-L6-SIZE_MISMATCH", "set_match": "QC-L7-PROP_MISSING",
                  "motion_match": "QC-V4-MOTION_VS_BYD"}
REVIEW_ONLY = frozenset({"QC-L13-CONTINUITY", "QC-A2-SILENT_GAP"})
INTENT_CODES = frozenset({"QC-L13-CONTINUITY"})
STOP_CODES = ("REPAIR_SUBMIT_UNKNOWN", "REPAIR_PAUSED", "REPAIR_LIMIT", "REPAIR_SAME_CODE_TWICE", "REPAIR_NO_INPUT_DELTA",
              "REPAIR_INTENT_CHANGE", "REPAIR_REVIEW_ONLY", "REPAIR_UNMAPPED")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def codes_for(failing: Iterable[str]) -> List[str]:
    """qc_code của các tiêu chí không đạt (giữ thứ tự, không trùng); tiêu chí chưa có mã → bỏ (plan nói REPAIR_UNMAPPED)."""
    out: List[str] = []
    for c in failing:
        code = CRITERION_CODE.get(c)
        if code and code not in out:
            out.append(code)
    return out


def _parent_codes(conn, job) -> List[str]:
    """qc_code của kế hoạch đã ghi cho job cha (cùng chuỗi gen lại) — diag `repair_plan` mở bằng "[QC-…]"."""
    if not job["parent_job_id"]:
        return []
    rows = conn.execute("SELECT message FROM diag_events WHERE code=? AND job_id=?", (CODE, job["parent_job_id"])).fetchall()
    return [r[0].split("]", 1)[0].lstrip("[") for r in rows if r[0].startswith("[QC-")]


def plan(conn, job, qc_code: Optional[str], fix: Optional[str] = None, limit: Optional[int] = None,
         attempt: Optional[int] = None, hold: Optional[str] = None) -> Dict:
    """Kế hoạch sửa cho MỘT lỗi của job (không ghi gì). Luật dừng theo thứ tự thiết kế mục 2.2; `auto_ok` luôn False (chỉ đề xuất)."""
    from .pipeline import AUTO_REGEN_LIMIT, SUBMIT_UNKNOWN
    kind = job["type"]
    row = REPAIR_ACTIONS.get(qc_code or "")
    action, delta, caps, ask = row if row else (None, "", {}, "")
    cap = caps.get(kind, AUTO_REGEN_LIMIT.get(kind, 0)) if row else 0
    if limit is not None:
        cap = min(cap, limit) if cap else 0
    attempt = (job["retry_count"] or 0) + 1 if attempt is None else attempt
    out = {"job_id": job["id"], "qc_code": qc_code, "action": action, "input_delta": delta, "fix": (fix or "").strip() or None,
           "attempt_no": attempt, "limit": cap, "stop_code": None, "needs_person": True, "auto_ok": False, "ask_when": ask}
    row_note = conn.execute("SELECT note FROM job_events WHERE job_id=? AND to_state='failed' ORDER BY id DESC LIMIT 1",
                            (job["id"],)).fetchone()          # = Pipeline.failure_note (ghi chú lần hỏng cuối)
    note = str(row_note[0] or "") if row_note else ""
    paused = conn.execute("SELECT paused FROM projects WHERE id=?", (job["project_id"],)).fetchone()
    stop = None
    if SUBMIT_UNKNOWN in note:
        stop = "REPAIR_SUBMIT_UNKNOWN"                       # 1: không bao giờ tự tạo job — người đối soát nhà cung cấp trước
    elif paused is not None and paused[0]:
        stop = "REPAIR_PAUSED"                              # 2
    elif row is None:
        stop = "REPAIR_UNMAPPED"                            # tiêu chí chưa có mã M4.1 — không đoán hành động
    elif cap <= 0 and action and not action.startswith(("FIX_PACKAGE", "TRIM", "RERENDER", "RESYNC")):
        stop = "REPAIR_LIMIT"                               # 3 (gen lại 0 lần cho loại job này)
    elif cap and attempt > cap:
        stop = "REPAIR_LIMIT"
    elif qc_code in INTENT_CODES:
        stop = "REPAIR_INTENT_CHANGE"                       # 6 — mã không bao giờ tự sửa: nói đúng lý do của nó trước "không đổi đầu vào"
    elif qc_code in REVIEW_ONLY or action is None:
        stop = "REPAIR_REVIEW_ONLY"                         # 7
    elif qc_code in _parent_codes(conn, job):
        stop = "REPAIR_SAME_CODE_TWICE"                     # 4: cùng mã 2 lần liền trong chuỗi → sửa lớp gốc
    elif not delta or (action and "REWRITE" in action and not out["fix"]) or hold:
        stop = "REPAIR_NO_INPUT_DELTA"                      # 5: không đổi đầu vào / _no_auto_retry đã từ chối (luật 6)
    out["stop_code"] = stop
    out["why"] = hold if stop == "REPAIR_NO_INPUT_DELTA" and hold else None
    return out


def _say(conn, job, p: Dict) -> None:
    from . import diag
    head = f"[{p['qc_code'] or 'chưa có mã'}] "
    body = (f"đề xuất {p['action'] or '(không tự sửa)'} — đổi: {p['input_delta'] or '—'}; lần {p['attempt_no']}/{p['limit']}"
            + (f"; DỪNG {p['stop_code']}" + (f" ({p['why']})" if p.get("why") else "") + (f" — {p['ask_when']}" if p['ask_when'] else "")
               if p["stop_code"] else "") + " · chỉ đề xuất, không tự gửi job (cờ repair_router)")
    diag.record(conn, "video" if job["type"] == "video_gen" else "image", "info", head + body, CODE, job["project_id"],
                scene_id=job["scene_id"], job_id=job["id"])


def observe(conn, job, failing: Iterable[str], fix: Optional[str] = None, hold: Optional[str] = None,
            limit: Optional[int] = None) -> List[Dict]:
    """Pipeline.apply_qc (QC không đạt): cờ bật → một kế hoạch mỗi qc_code (+ một cho tiêu chí chưa có mã), ghi diag; trả danh sách.
    Cờ tắt → [] không đọc / ghi gì. Không bao giờ ném lỗi (chỉ đề xuất — đường QC thật đi tiếp)."""
    if not enabled():
        return []
    try:
        failing = list(failing)
        codes = codes_for(failing)
        plans = [plan(conn, job, c, fix, limit=limit, hold=hold) for c in codes]
        if any(c not in CRITERION_CODE for c in failing):
            plans.append(plan(conn, job, None, fix, limit=limit, hold=hold))
        for p in plans:
            _say(conn, job, p)
        return plans
    except Exception as e:  # noqa: BLE001 - a proposal never breaks the QC
        try:
            from . import diag
            diag.record(conn, "system", "warn", f"repair router (đề xuất) lỗi ({type(e).__name__}: {e}) — QC thật không đổi", CODE,
                        job["project_id"], job_id=job["id"])
        except Exception:  # noqa: BLE001
            pass
        return []
