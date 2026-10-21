"""V3.1 M2.7 — lớp code kiểm ẢNH TRƯỚC gen, cùng dạng + bộ mã với video (core/video_pregen.py, mã ở core/pregen_codes.py).
0 USD, chỉ đọc CSDL + tệp. Cờ `image_pregen`, MẶC ĐỊNH TẮT. Thiết kế: docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md mục 3.

MỨC SHADOW (việc DP9): cờ bật → ImageRunner._pregen chạy check() trên đúng gói sắp gửi và ghi mỗi lỗi một dòng ⚙ Chẩn đoán
`image_pregen_shadow` mức REVIEW — KHÔNG giữ job, không đổi gói gửi. Các điểm chặn cũ (ImageRunner._blocked: bố cục Kho / công thức
prompt; ImageRunner._pregen: nền 3D lẫn máy) vẫn chặn như nay ở mọi mức cờ. Mức giữ job theo ĐỎ (enforce) = việc sau (Cấp 3 khi bật).

check(conn, scene_id, plan) -> [{ma, muc: "do" | "vang", ly_do}] — `muc` là mức lỗi SẼ CÓ khi enforce; rỗng = đạt.
Mã: nen_3d · cong_thuc · bo_cuc_kho · tham_chieu · van_tay · byd / byd_draft · khoi_giu_cho · loi_kiem (một lớp kiểm hỏng).
Chưa kiểm (để việc khác): ky_tu (ngân sách ký tự — M2.8 / DP10, chưa có prompt_budget).

`plan` = cái runner SẮP gửi (plan_of dựng từ args / kwargs thật của provider.submit + gói core/sent_package dựng y lúc gửi + `sent` =
danh sách ảnh của _finish_args): {job_id, project_id, data_dir, prompt, references, size, model, storyboard, sent, dropped, package}.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from .pregen_codes import DO, REVIEW, VANG

FLAG = "image_pregen"
DIAG_CODE = "image_pregen_shadow"
# Mức shadow không ghi lại mã mà điểm chặn cũ đang tự nói (nen_3d = diag plate_package_mixed, cùng lời) — tránh hai dòng cùng nội dung (rà DP9 VỪA-2).
SHADOW_SKIP = ("nen_3d",)
_HAD_PICTURE = ("succeeded", "pending_review", "approved", "rejected")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _issue(ma: str, muc: str, ly_do: str) -> Dict[str, str]:
    return {"ma": ma, "muc": muc, "ly_do": ly_do}


def _data(conn, scene_id: int) -> Dict:
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    try:
        return json.loads(row["data"] or "{}") if row else {}
    except (TypeError, ValueError):
        return {}


# ---- lời người dùng đang quen: MỘT nguồn cho runner (điểm chặn cũ) và lớp kiểm này -------------------------------------------------
def plate_line(why: str) -> str:
    """Lời giữ ảnh khi gói mang nền 3D của máy khác (ImageRunner._pregen, diag plate_package_mixed) — mã nen_3d."""
    return f"CẦN BẠN SỬA: {why} — ảnh GIỮ CHỜ, không gửi (0 USD); render lại nền 3D / sửa góc máy rồi sẽ tự gửi"


def layout_reason(conn, project_id: int, data: Dict) -> Optional[str]:
    """S5.2: nơi chốn Kho có bố cục mà dự án chưa nối (ImageRunner._blocked) — mã bo_cuc_kho."""
    from . import assets
    return assets.missing_layout(conn, project_id, data) or None


def formula_reason(conn, scene_id: int) -> Optional[str]:
    """F1 (09/10): prompt ảnh sai công thức (ImageRunner._blocked) — mã cong_thuc."""
    from . import prompt_formula
    red = prompt_formula.red_issues(conn, scene_id, "image")
    return ("prompt ảnh sai công thức — sửa ở Bước 1/2: " + " · ".join(red)) if red else None


# ---- từng lớp kiểm -------------------------------------------------------------------------------------------------------------
def _check_plate(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    from . import location_pack, place_refs
    sent = plan.get("sent")
    if not sent:
        return
    why = place_refs.package_problem(sent, location_pack.plate_of(plan["data_dir"], plan["project_id"], scene_id))
    if why:
        out.append(_issue("nen_3d", DO, plate_line(why)))


def _check_layout(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    why = layout_reason(conn, plan["project_id"], data)
    if why:
        out.append(_issue("bo_cuc_kho", DO, why))


def _check_formula(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    why = formula_reason(conn, scene_id)
    if why:
        out.append(_issue("cong_thuc", DO, why))


def _check_refs(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    """Ảnh SẮP gửi: đọc được (cùng luật adapter Deepix), số ảnh ≤ trần model; ảnh _finish_args đã bỏ → VÀNG (model chỉ nhận chữ)."""
    from . import image_models
    from .adapters.deepix import MAX_REFERENCES, reference_problem
    refs = [str(r) for r in plan.get("references") or []]
    bad = [f"{r} ({p})" for r in refs for p in [reference_problem(r)] if p]
    if bad:
        out.append(_issue("tham_chieu", DO, "ảnh tham chiếu không gửi được: " + ", ".join(bad)))
    model = plan.get("model")
    cap = image_models.max_refs(model, MAX_REFERENCES) if model else MAX_REFERENCES
    if len(refs) > cap:
        out.append(_issue("tham_chieu", DO, f"{len(refs)} ảnh tham chiếu > trần {cap} ảnh của model {model or '(mặc định)'}"))
    dropped = list(plan.get("dropped") or [])
    if dropped:
        out.append(_issue("tham_chieu", VANG, "ảnh bị bỏ khỏi gói (model chỉ nhận chữ): " + ", ".join(dropped)))


def _check_fingerprint(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    """N10: gen lại ảnh phải đổi đầu vào. Cùng vân tay với video (video_pregen.fingerprint — một hàm băm gói)."""
    from .video_pregen import fingerprint
    fp = fingerprint(plan.get("package"))
    if fp is None:
        out.append(_issue("van_tay", DO, "không dựng được gói gửi để lấy vân tay — không biết lần này có đổi đầu vào so với lần trước "
                                         "không (N10)"))
        return
    prev = conn.execute("SELECT id, state, result_path, sent_package FROM jobs WHERE scene_id=? AND type='image_gen' AND id<>? "
                        "AND sent_package IS NOT NULL AND sent_package<>'' ORDER BY id DESC LIMIT 1",
                        (scene_id, plan.get("job_id") or -1)).fetchone()
    if prev is None or fingerprint(prev["sent_package"]) != fp:
        return
    if prev["result_path"] or prev["state"] in _HAD_PICTURE:
        out.append(_issue("van_tay", DO, f"gói ảnh trùng y lần gen trước (job {prev['id']}) — gen lại phải đổi đầu vào (N10): sửa "
                                         "prompt ảnh / tham chiếu / model, hoặc ghi câu sửa khi bấm gen lại"))
    else:
        out.append(_issue("van_tay", VANG, f"gửi lại y gói ảnh của job {prev['id']} (lần đó hỏng ở nhà cung cấp, chưa có ảnh)"))


def _check_byd(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    from . import shot_intent
    byd = shot_intent.byd_of(data)
    if byd is None:
        out.append(_issue("byd", VANG, "chưa có BYĐ — chưa kiểm được thành phần / máy của ảnh theo ý đồ shot"))
        return
    if shot_intent.is_draft(byd):                      # provenance M2.1 `_p` (M2.4 draft / from) — một nguồn với cổng video
        row = conn.execute("SELECT idx FROM scenes WHERE id=?", (shot_intent.draft_source(byd),)).fetchone() if conn else None
        src = f" từ shot {row['idx']}" if row else ""       # số shot như cổng video (không phải mã scene id)
        out.append(_issue("byd_draft", VANG, f"BYĐ nháp do code dựng{src} — duyệt ở Bước 3"))


def _check_stand_in(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    """G1 (M2.4): gói có render nền 3D của shot mà render còn khối giữ chỗ lọt khung → prompt phải có câu giải thích khối
    (core/stage_facts._prompt_stand_in), thiếu thì model vẽ khối xám thành vật thật lạ. Runner chỉ nối câu này khi cờ stage_camera bật và
    shot có stage_camera (runner._geometry_part) — ngoài điều kiện đó không đòi (rà DP9 VỪA-1). D6 (chat_prompts) viết lại prompt: dự phòng
    "placeholder" + tên khối, không khớp nguyên văn."""
    from . import features, place_refs, stage_facts
    if not features.on("stage_camera") or not data.get("stage_camera"):
        return
    if not any(s.get("role") == place_refs.ROLE for s in plan.get("sent") or []):
        return
    facts = [f for f in stage_facts.for_shot(conn, plan["project_id"], data, render=True)["facts"] if f["kind"] == "stand_in"]
    prompt = str(plan.get("prompt") or "")
    low = prompt.lower()
    lacking = [f["name"] for f in facts
               if f.get("prompt") and f["prompt"] not in prompt and not ("placeholder" in low and str(f["name"]).lower() in low)]
    if lacking:
        out.append(_issue("khoi_giu_cho", DO, "nền 3D còn khối giữ chỗ (" + ", ".join(lacking) + ") mà prompt thiếu câu giải thích "
                                              "khối — model dễ vẽ khối xám thành vật lạ (G1)"))


_CHECKS: List[Callable] = [_check_plate, _check_layout, _check_formula, _check_refs, _check_fingerprint, _check_byd, _check_stand_in]


# ---- cổng --------------------------------------------------------------------------------------------------------------------------
def check(conn, scene_id: int, plan: Dict) -> List[Dict[str, str]]:
    """Mọi lỗi của lần gửi ảnh `plan` cho shot `scene_id` (rỗng = đạt). Không gọi mạng, không tốn tiền. Một lớp kiểm hỏng → ĐỎ
    `loi_kiem` có lý do (không coi là đạt), các lớp khác vẫn chạy."""
    out: List[Dict[str, str]] = []
    data = _data(conn, scene_id)
    for fn in _CHECKS:
        try:
            fn(conn, scene_id, plan, data, out)
        except Exception as e:  # noqa: BLE001 - luật 1: một lớp kiểm không chạy được thì nói, không im lặng
            out.append(_issue("loi_kiem", DO, f"lớp kiểm {fn.__name__[7:]} lỗi ({type(e).__name__}: {e}) — chưa kiểm được"))
    return out


def plan_of(job, args, kwargs: Dict, package: Optional[str], data_dir: str, sent=None, dropped=None) -> Dict:
    """Dạng `plan` từ đúng args / kwargs mà runner sắp đưa provider.submit (ImageRunner._submit_args / _submit_kwargs)."""
    args = tuple(args or ())
    kw = dict(kwargs or {})
    try:
        pkg = json.loads(package) if package else None
    except (TypeError, ValueError):
        pkg = None
    return {"job_id": job["id"], "project_id": job["project_id"], "data_dir": data_dir,
            "prompt": args[0] if args else None, "references": list(args[1] or []) if len(args) > 1 else [],
            "size": kw.get("size"), "model": kw.get("model"), "storyboard": kw.get("storyboard"),
            "sent": list(sent or []), "dropped": list(dropped or []), "package": pkg}


def summary(issues: List[Dict]) -> str:
    """Một dòng tiếng Việt cho ⚙ Chẩn đoán."""
    return " · ".join(i["ly_do"] for i in issues)


def shadow_line(issue: Dict[str, Any]) -> str:
    """Dòng ⚙ Chẩn đoán mức shadow cho một lỗi: mức REVIEW, nói rõ mức sẽ có khi enforce và job VẪN GỬI."""
    sev = "ĐỎ" if issue["muc"] == DO else "VÀNG"
    return f"{REVIEW.upper()} (shadow, không giữ — sẽ là {sev} khi bật chặn) [{issue['ma']}] {issue['ly_do']}"


def preview(conn, project_id: int, data_dir: str) -> List[Dict]:
    """tools/pregen_check: lỗi đọc được từ dữ liệu shot khi CHƯA có job (bố cục Kho, công thức, BYĐ) — [{idx, scene_id, issues}].
    Lớp cần gói thật lúc gửi (nền 3D trong gói, ảnh tham chiếu, vân tay, khối giữ chỗ) chạy ở runner khi gửi, không đoán ở đây."""
    from . import shots
    out = []
    for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        if not shots.needs_own_image(conn, r["id"]):
            continue
        try:
            data = json.loads(r["data"] or "{}")
        except (TypeError, ValueError):
            data = {}
        plan = {"job_id": None, "project_id": project_id, "data_dir": data_dir, "prompt": data.get("image_prompt"), "references": [],
                "sent": [], "dropped": [], "package": None}
        issues: List[Dict] = []
        for fn in (_check_layout, _check_formula, _check_byd):
            try:
                fn(conn, r["id"], plan, data, issues)
            except Exception as e:  # noqa: BLE001 - như check()
                issues.append(_issue("loi_kiem", DO, f"lớp kiểm {fn.__name__[7:]} lỗi ({type(e).__name__}: {e}) — chưa kiểm được"))
        if issues:
            out.append({"idx": r["idx"], "scene_id": r["id"], "issues": issues})
    return out
