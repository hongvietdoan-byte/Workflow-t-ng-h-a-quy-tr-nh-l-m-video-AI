"""Chính sách tiền 04/10 (S14.16 — docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 6c; THAY quyết định "trần cứng" 28/09).

  * Giá chỉ để tham khảo. Mọi trần tiền (ngân sách dự án, đợt thử, Claude API, trần một việc / một khâu) là MỨC DỰ TÍNH dùng để so và
    CẢNH BÁO — không chặn. Cổng tiền (core.spend_gate, runner, llm_runner) vẫn ước tính trước và ghi sổ ngay sau khi gửi; khi lượt này
    làm vượt mức dự tính hoặc model chưa có giá, lượt vẫn đi và một cảnh báo có số liệu được trả về + ghi `diag` (mức warn, mã
    WARN_CODE) để UI (thanh 💵, hộp 📥) đọc.
  * Chỉ CHẶN khi: nhà cung cấp báo hết tiền (budget.halt / halted), dự án Tạm dừng (PipelinePaused), trần job/ngày của autopilot.
  * Ước tính tính DƯ: model/mức chưa có giá trong data/pricing.json → giá cao nhất đã biết của cùng model (không có thì của cùng loại)
    × SAFETY_FACTOR; model chưa xác minh giá (`_unverified_models`) × project_budget.UNVERIFIED_MARGIN (1,25) như trước.
  * Màu thanh 💵: vàng khi đã chi ≥ WARN_AT × mức dự tính, đỏ khi ≥ DANGER_AT ×.

Không đọc/ghi gì ngoài app_settings / diag_events / usage_events qua các module sẵn có; không gọi nhà cung cấp."""
import re
from typing import Dict, Iterable, List, Optional, Tuple

WARN_AT = 1.0          # thanh vàng: đã chi ≥ 100 % mức dự tính
DANGER_AT = 1.5        # thanh đỏ: đã chi ≥ 150 % mức dự tính ("vượt xa")
SAFETY_FACTOR = 1.5    # mức chưa có giá: giá cao nhất đã biết × 1,5 — để ước tính không bao giờ thấp hơn thực tế (người dùng 04/10)
WARN_CODE = "money_warning"          # mã diag của cảnh báo tiền (UI đọc mã này)
BLOCK_CODE = "budget"                # mã diag của lần CHẶN thật (hết tiền) — autopilot._budget_stop đọc mã này
NOTE_EVERY_MIN = 10                  # cùng một loại cảnh báo của cùng dự án: ghi diag tối đa 1 lần / 10 phút (lượt gửi vẫn trả câu đầy đủ)
ESTIMATED = "(ước tính)"


def level(spent: float, planned: Optional[float]) -> str:
    """'ok' | 'warn' (≥ WARN_AT × mức dự tính) | 'danger' (≥ DANGER_AT ×). Không có mức dự tính → 'ok'."""
    if not planned or planned <= 0:
        return "ok"
    share = float(spent or 0) / float(planned)
    return "danger" if share >= DANGER_AT - 1e-9 else "warn" if share >= WARN_AT - 1e-9 else "ok"


def over_pct(total: float, planned: Optional[float]) -> Optional[float]:
    """% vượt mức dự tính (0 khi chưa vượt), None khi không có mức dự tính."""
    if not planned or planned <= 0:
        return None
    return max(0.0, (float(total) / float(planned) - 1.0) * 100.0)


def warning_text(what: str, spent: float, planned: Optional[float], this_usd: Optional[float] = None,
                 missing: Iterable[str] = (), extra: str = "") -> str:
    """Một câu cảnh báo có số liệu: đã chi, mức dự tính, ước tính lượt này, % vượt, model thiếu giá. Lượt vẫn được gửi."""
    total = float(spent or 0) + float(this_usd or 0)
    parts = [f"⚠ {what}: đã chi ≈ ${float(spent or 0):.2f}"]
    if planned is not None:
        parts.append(f"mức dự tính ${float(planned):.2f}")
    if this_usd is not None:
        parts.append(f"lượt này ≈ ${float(this_usd):.2f} {ESTIMATED}")
    pct = over_pct(total, planned)
    if pct:
        parts.append(f"vượt {pct:.0f} %")
    miss = sorted({m for m in missing if m})
    if miss:
        parts.append("thiếu giá: " + ", ".join(miss))
    return ", ".join(parts) + (f" — {extra}" if extra else "") + " — VẪN GỬI (trần chỉ để cảnh báo; đặt lại mức dự tính ở 💵)"


def over(spent: float, planned: Optional[float], this_usd: float = 0.0) -> bool:
    """Lượt này làm tổng vượt mức dự tính (hoặc đã vượt từ trước)."""
    return planned is not None and float(spent or 0) + float(this_usd or 0) > float(planned) + 1e-9


# ---- ước tính tính dư -----------------------------------------------------------------------------------------------------------------
def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _video_rates(pricing: Dict, model: Optional[str] = None) -> Tuple[List[float], List[float]]:
    """(giá mỗi giây, giá mỗi clip phẳng) đã biết — của `model` (None = mọi model video)."""
    per_s, flat = [], []
    for key, v in (pricing.get("per_video_second") or {}).items():
        if _num(v) is not None and not key.startswith("_") and (model is None or key.split(":")[0] == model):
            per_s.append(_num(v))
    for key, v in (pricing.get("per_video_clip") or {}).items():
        if _num(v) is None or key.startswith("_") or (model is not None and key.split(":")[0] != model):
            continue
        m = re.search(r":(\d+(?:\.\d+)?)s$", key)
        if m and float(m.group(1)) > 0:
            per_s.append(_num(v) / float(m.group(1)))
        else:
            flat.append(_num(v))
    return per_s, flat


def _highest(table: Dict) -> Optional[float]:
    vals = [_num(v) for k, v in (table or {}).items() if not str(k).startswith("_") and _num(v) is not None]
    return max(vals) if vals else None


def estimate(kind: str, model: Optional[str], tier: Optional[str] = None, units: float = 1,
             pricing: Optional[Dict] = None) -> Dict:
    """Ước tính DƯ một lượt gửi: {"usd": float|None, "how": exact|unverified|model_max|kind_max|none, "missing": "model:mức"|None,
    "note": câu ngắn}. kind: image (units = số ảnh) | video (units = giây) | audio (units = lượt). usd None = không có giá nào cùng
    loại (âm thanh hiện chưa có giá: giới hạn theo lượt ở core.budget)."""
    from . import cost, project_budget
    pricing = pricing if pricing is not None else cost.load_pricing()
    units = float(units or 1)
    margin = project_budget.UNVERIFIED_MARGIN if model and project_budget.unverified(pricing, model) else 1.0
    if kind == "image":
        exact = _num((pricing.get("per_image") or {}).get(model)) if model else None
        if exact is not None:
            return _est(exact * units * margin, "unverified" if margin > 1 else "exact", None)
        best = _highest(pricing.get("per_image"))
        return _fallback(best, units, "kind_max", f"ảnh {model or '(không rõ model)'}")
    if kind == "video":
        exact = cost.clip_price(pricing, model, tier, units) if model else None
        if exact is not None:
            return _est(exact * margin, "unverified" if margin > 1 else "exact", None)
        name = f"{model or '(không rõ model)'}:{tier or '-'}"
        per_s, flat = _video_rates(pricing, model) if model else ([], [])
        how = "model_max"
        if not per_s and not flat:
            per_s, flat = _video_rates(pricing)
            how = "kind_max"
        cands = [r * units for r in per_s] + flat
        return _fallback(max(cands) if cands else None, 1.0, how, name, margin)
    if kind == "audio":
        exact = _num((pricing.get("per_audio") or {}).get(model)) if model else None
        if exact is not None:
            return _est(exact * units, "exact", None)
        best = _highest(pricing.get("per_audio"))
        return _fallback(best, units, "kind_max", f"âm thanh {model or '(không rõ model)'}")
    raise ValueError(f"money_policy.estimate: loại '{kind}' không hỗ trợ")


def _est(usd: Optional[float], how: str, missing: Optional[str], note: str = "") -> Dict:
    return {"usd": None if usd is None else round(usd, 4), "how": how, "missing": missing, "note": note}


def _fallback(best: Optional[float], units: float, how: str, name: str, margin: float = 1.0) -> Dict:
    if best is None:
        return _est(None, "none", name, f"{name} chưa có giá, cũng không có giá nào cùng loại để ước tính")
    usd = best * units * SAFETY_FACTOR * margin
    src = "cùng model" if how == "model_max" else "cùng loại"
    return _est(usd, how, name, f"{name} chưa có giá — ước tính ≈ ${usd:.2f} = giá cao nhất đã biết của {src} × {SAFETY_FACTOR:g}")


def token_price(pricing: Dict, model: str, tier: str, tokens: float) -> Tuple[Optional[float], bool]:
    """Giá token Claude, tính dư: (usd, ước-tính-thay?) — model chưa có giá dùng giá cao nhất đã biết của mức đó × SAFETY_FACTOR."""
    from . import budget
    exact = budget.token_price(pricing, model, tier, tokens)
    if exact is not None:
        return exact, False
    best = None
    for name in (pricing.get("per_million_tokens") or {}):
        if not str(name).startswith("_"):
            v = budget.token_price(pricing, name, tier, tokens)
            best = v if best is None or (v is not None and v > best) else best
    return (None, True) if best is None else (best * SAFETY_FACTOR, True)


# ---- ghi lại cảnh báo -------------------------------------------------------------------------------------------------------------------
def note(conn, text: str, *, stage: str = "system", project_id: Optional[int] = None, scene_id: Optional[int] = None,
         job_id: Optional[int] = None, key: str = "") -> None:
    """Ghi một cảnh báo tiền vào diag (warn, WARN_CODE). Cùng `key` + dự án đã ghi trong NOTE_EVERY_MIN phút → bỏ qua (một đợt gửi
    nhiều lượt không làm ngập bảng chẩn đoán; câu đầy đủ vẫn được trả cho nơi gọi). Không bao giờ ném lỗi."""
    if not text:
        return
    try:
        from . import diag
        tag = f"[{key}] " if key else ""
        if key:
            row = conn.execute("SELECT 1 FROM diag_events WHERE code=? AND COALESCE(project_id,0)=? AND message LIKE ?"
                               " AND (julianday('now') - julianday(last_at)) * 1440 < ? LIMIT 1",
                               (WARN_CODE, project_id or 0, tag.replace("%", "") + "%", NOTE_EVERY_MIN)).fetchone()
            if row is not None:
                return
        diag.record(conn, stage, "warn", tag + text, code=WARN_CODE, project_id=project_id, scene_id=scene_id, job_id=job_id)
    except Exception:  # noqa: BLE001 - a warning that cannot be written must not stop the paid send that was allowed
        pass


def recent(conn, hours: float = 24, project_ids: Optional[Iterable[int]] = None, limit: int = 20) -> List[Dict]:
    """Cảnh báo tiền gần đây (mới nhất trước) cho UI."""
    try:
        rows = conn.execute("SELECT * FROM diag_events WHERE code=? AND (julianday('now') - julianday(last_at)) * 24 < ?"
                            " ORDER BY last_at DESC, id DESC LIMIT ?", (WARN_CODE, hours, limit * 5)).fetchall()
    except Exception:  # noqa: BLE001 - no diag table yet
        return []
    ids = None if project_ids is None else {int(i) for i in project_ids}
    out = [dict(r) for r in rows if ids is None or r["project_id"] is None or int(r["project_id"]) in ids]
    return out[:limit]


def blocked_text(why: str, spent: Optional[float] = None, planned: Optional[float] = None, how_to_open: str = "") -> str:
    """Câu báo một lần CHẶN thật (hết tiền / tạm dừng / trần job ngày) — lý do, đã chi, mức dự tính, cách mở."""
    parts = [f"⛔ CHẶN: {why}"]
    if spent is not None:
        parts.append(f"đã chi ≈ ${float(spent):.2f}")
    if planned:
        parts.append(f"mức dự tính ${float(planned):.2f}")
    return ", ".join(parts) + (f" — cách mở: {how_to_open}" if how_to_open else "")
