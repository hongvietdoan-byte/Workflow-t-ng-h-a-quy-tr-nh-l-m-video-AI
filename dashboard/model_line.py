"""F4 (09/10, người dùng duyệt): màn chọn model gọn — MỘT dòng mỗi shot "model · nháp → cao · giữ nội dung? · ≈ USD".

Hàm thuần (không Streamlit, chỉ ĐỌC): dùng `model_router.scene_choice / plan / label`, `quality_tier.group_path / final_resolution /
e1_estimate`, `cost.seedance_estimate` (giá F3). Không gửi gì, không ghi gì.

- `shot_line(conn, pid, scene_id, row=None)` → dict một shot (xem docstring);
- `shot_lines(conn, pid)` → {scene_id: dict} tính `plan` MỘT lần (bảng Model + thẻ clip);
- `film_line(conn, pid)` → "Phim X s ≈ Y USD — mục tiêu < 30 USD (đạt)" (E1 khi cờ two_tier_quality bật, không thì tổng `plan`).
Cờ two_tier_quality tắt → dòng chỉ có model + độ phân giải (không phần nháp / cao)."""
import os
from typing import Dict, Optional

UPSCALE_AT_EDIT = "1080p"
SOURCE_TEXT = {"override": "bạn chọn", "project": "model chung dự án", "legacy": "mặc định cũ", "auto": "đề xuất"}


def _two_tier() -> bool:
    try:
        from dashboard import quality_ui
        return quality_ui.enabled()
    except Exception:  # noqa: BLE001 - a broken flag read never breaks the screen
        return False


def _resolve(model: Optional[str]):
    """(canonical, family) of a model alias / id; (model, None) when unknown (mock / web-only)."""
    try:
        from core.adapters.clipai import resolve_model
        return tuple(resolve_model(model)[:2])
    except Exception:  # noqa: BLE001
        return model, None


def _ratio(conn, pid: int) -> str:
    from core import formats
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    return formats.spec(formats.project_aspect(proj))["clip"] if proj is not None else "16:9"


def _low_resolution(canonical: Optional[str]) -> Optional[str]:
    from core import video_rules
    res = video_rules.rule(canonical or "").get("resolutions") or []
    return res[0] if res else None


def _plan_row(conn, pid: int, scene_id: int) -> Optional[Dict]:
    from core import cost, model_router
    return next((r for r in model_router.plan(conn, pid, cost.load_pricing()) if r["scene_id"] == scene_id), None)


def shot_line(conn, pid: int, scene_id: int, row: Optional[Dict] = None, ratio: Optional[str] = None) -> Dict:
    """Một shot: {"model", "model_text" ("Seedance 2.5 · nháp 480p → cao 1080p" / "Seedance 2.0 · 720p → phóng 1080p lúc dựng" /
    "Kling 3.0 Omni · pro"), "keeps_content" (nháp → cao giữ nội dung? True / False; None = không có bước nháp), "usd" (≈, theo clip
    nhóm; 0 = nằm trong clip nhóm của shot khác; None = chưa có giá), "in_group", "source" (đề xuất / bạn chọn …), "why" (lý do),
    "warning" (model_router — E1, vd. Seedance 2.0 ở shot nháp-trước), "path" (draft_first / direct / None), "text" (cả dòng)}.
    `row` = hàng `model_router.plan` của shot (truyền vào để khỏi tính lại cả kế hoạch)."""
    from core import cost, model_router
    row = row if row is not None else _plan_row(conn, pid, scene_id)
    if row is None:                                  # shot chưa có trong kế hoạch: lựa chọn trần, không giá
        row = {**model_router.scene_choice(conn, scene_id), "billed_seconds": None, "cost": None, "seconds": None}
    model, res = row.get("model"), row.get("resolution")
    canonical, family = _resolve(model)
    two_tier = _two_tier()
    billed = row.get("billed_seconds")
    in_group = billed is not None and float(billed) <= 0
    keeps, way, usd = None, None, row.get("cost")
    name = model_router.label(model)                 # tên thật + bậc mặc định của model ("Seedance 2.0 · 720p")
    base = name.split(" · ")[0]
    if family == "omni":
        model_text = model_router.label(model, res or os.environ.get("CLIPAI_KLING_MODE", "pro"))
    elif two_tier and family == "seedance":
        from core import quality_tier as qt
        way = qt.group_path(conn, scene_id)
        sec = max(float(billed or 0), 4.0)
        ratio = ratio or _ratio(conn, pid)
        if way == "draft_first":
            low = res if canonical == qt.SAMPLE_MODEL and res else (_low_resolution(canonical) or res or "480p")
            keeps = canonical == qt.SAMPLE_MODEL
            # như quality_tier._final_usd: nâng từ nháp 2.5 → FINAL_RESOLUTION; gen mới → mức cao nhất luật model cho phép
            final = qt.FINAL_RESOLUTION if keeps else qt.final_resolution(model)
            model_text = f"{base} · nháp {low} → cao {final}" + ("" if keeps else " (gen mới)")
            if not in_group and billed is not None:
                parts = [cost.seedance_estimate(canonical, low, ratio, sec), cost.seedance_estimate(canonical, final, ratio, sec)]
                usd = None if any(v is None for v in parts) else sum(parts)
        else:
            res = res or qt.E1_DIRECT_RESOLUTION
            model_text = f"{base} · {res}" + (f" → phóng {UPSCALE_AT_EDIT} lúc dựng" if res in ("480p", "720p") else "")
            if not in_group and billed is not None:
                usd = cost.seedance_estimate(canonical, res, ratio, sec)
    else:
        model_text = model_router.label(model, res)
    if in_group:
        usd = 0.0
    source = SOURCE_TEXT.get(row.get("source"), "đề xuất")
    parts = [model_text]
    if keeps is not None:
        parts.append("giữ nội dung nháp ✓" if keeps else "KHÔNG giữ nội dung nháp")
    parts.append("trong clip nhóm" if in_group else (f"≈ {usd:.2f} USD" if usd is not None else "chưa có giá"))
    parts.append(source)
    return {"model": model, "model_text": model_text, "keeps_content": keeps, "usd": None if usd is None else round(usd, 4),
            "in_group": in_group, "source": source, "why": row.get("reason") or "", "warning": row.get("warning"), "path": way,
            "text": " · ".join(parts)}


def shot_lines(conn, pid: int) -> Dict[int, Dict]:
    """{scene_id: shot_line} của cả dự án — `plan` tính MỘT lần."""
    from core import cost, model_router
    ratio = _ratio(conn, pid)
    return {r["scene_id"]: shot_line(conn, pid, r["scene_id"], r, ratio) for r in model_router.plan(conn, pid, cost.load_pricing())}


def film_line(conn, pid: int) -> Dict:
    """{"text": "Phim 20 s ≈ 6.10 USD — mục tiêu < 30 USD (đạt)", "help", "usd", "within"} — ước tính CẢ PHIM một lượt (chưa tính gen
    lại). Cờ two_tier_quality bật → quality_tier.e1_estimate (E1); tắt → tổng model_router.plan, cùng mục tiêu < 30 / 60 USD."""
    from core import cost, model_router
    from core import quality_tier as qt
    if _two_tier():
        est = qt.e1_estimate(conn, pid)
        usd, seconds, target, help_ = est["usd"], est["film_seconds"], est["target_usd"], est["line"]
    else:
        rows = model_router.plan(conn, pid, cost.load_pricing())
        usd = model_router.total(rows)
        seconds = sum(float(r.get("seconds") or 0) for r in rows)
        target = next((cap for limit, cap in qt.FILM_TARGETS if seconds < limit), None)
        help_ = "Tổng giá các clip theo model từng cảnh (một lượt, chưa tính gen lại)."
    within = None if usd is None or target is None else usd < target
    text = f"Phim {seconds:.0f} s ≈ " + (f"{usd:.2f} USD" if usd is not None else "chưa có giá")
    if target is not None:
        text += f" — mục tiêu < {target:.0f} USD" + ("" if within is None else (" (đạt)" if within else " (VƯỢT)"))
    return {"text": text, "help": help_, "usd": usd, "within": within, "target_usd": target}
