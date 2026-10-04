"""UI v2 helpers of the Video screen (lane G, S13). Pure presentation: job state -> the fixed review vocabulary, small HTML chips,
the numbers of the hero. Nothing here changes the pipeline; `dashboard/steps/step4.py` calls these only when `ui.v2_on()`."""
from html import escape
from typing import Dict, List, Optional, Tuple

from dashboard.design import components as D

# job state (video_gen) -> (fixed label/kind via components.FRAME_STATES key)
_STATE = {"succeeded": "review", "pending_review": "review", "approved": "approved", "rejected": "rejected", "failed": "failed",
          "queued": "queued", "running": "working"}


def clip_pill(state: str) -> str:
    """The state pill of one clip card: Cần duyệt / Đang làm / Đã duyệt / Từ chối / Lỗi / Chờ gen (retryable keeps its own words)."""
    if state == "retryable":
        return D.pill("Chờ gửi lại", "warn")
    key = _STATE.get(state)
    return D.frame_state_pill(key) if key else D.pill(state, "mute")


def score_kind(score: float, threshold: Optional[float]) -> str:
    t = float(threshold or 0.85)
    return "ok" if score >= t else "warn" if score >= t - 0.15 else "bad"


def score_chips(scores, labels: Dict[str, str]) -> str:
    """QC criteria as small labelled chips: 'Đúng nhân vật 0.91'."""
    return " ".join(D.pill(f"{labels.get(s['criterion'], s['criterion'])} {s['score']:.2f}", score_kind(s["score"], s["threshold_at_time"]))
                    for s in scores)


def layer0_rows(flags: List[Dict]) -> str:
    """Layer-0 measurements (code checks of the first frame) as a short labelled list: one line per flag, never a wall of text."""
    if not flags:
        return ""
    rows = "".join(f'<div class="vid-l0row">{D.pill("Vẽ lại" if f.get("severity") == "redraw" else "Lưu ý", "bad" if f.get("severity") == "redraw" else "warn")}'
                   f'<span>{escape(str(f.get("problem") or ""))[:160]}</span></div>' for f in flags[:4])
    more = f'<div class="vid-l0row"><span>… và {len(flags) - 4} đo khác</span></div>' if len(flags) > 4 else ""
    return f'<div class="vid-l0"><small>Đo lớp 0 (ảnh khung đầu)</small>{rows}{more}</div>'


def meta_line(model: Optional[str], seconds: Optional[float], usd: Optional[float], retries: int) -> str:
    bits = [escape(model or "model mặc định")]
    if seconds:
        bits.append(f"{seconds:g} s")
    bits.append(f"≈ {usd:.2f} USD (ước tính)" if usd is not None else "chưa có giá")
    bits.append(f"gen lại {retries} lần")
    return '<div class="vid-meta">' + " · ".join(bits) + "</div>"


def note_row(label: str, text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    return f'<div class="vid-note"><small>{escape(label)}</small><span>{escape(text)[:220]}</span></div>'


def video_spend(conn, pid: int) -> float:
    """USD of the video submissions of this project (declared prices, mock excluded) — the 'tiền video đã chi' of the hero."""
    from core import cost
    pricing = cost.load_pricing()
    total = 0.0
    for r in conn.execute("SELECT model, tier, quantity FROM usage_events WHERE project_id=? AND kind='video' AND provider NOT LIKE 'mock%'", (pid,)):
        total += cost.clip_price(pricing, r["model"], r["tier"], r["quantity"]) or 0.0
    return total


def hero_stats(latest: List, summ: Dict, spend: float) -> Tuple[int, int, int, int, int]:
    """(clips usable, scenes total, waiting for review, failed, running/queued) from the latest job of every scene."""
    waiting = sum(1 for j in latest if j["state"] in ("pending_review", "succeeded"))
    failed = sum(1 for j in latest if j["state"] in ("failed", "rejected"))
    busy = sum(1 for j in latest if j["state"] in ("queued", "running", "retryable"))
    return summ["videos"][0], summ["total"], waiting, failed, busy


# ---- progressive disclosure (docs/QUY_TAC_BO_CUC_UI_V2.md §5): one summary line outside, the full content behind ⓘ ---------------------
def layer0_summary(flags: List[Dict]) -> str:
    redraw = sum(1 for f in flags if f.get("severity") == "redraw")
    first = str(flags[0].get("problem") or "")
    return D.pill(f"Đo lớp 0: {len(flags)} điểm", "bad" if redraw else "warn") + f' <span class="vid-sum">{escape(first[:70])}{"…" if len(first) > 70 else ""}</span>'


def layer0_md(flags: List[Dict]) -> str:
    return "**Đo lớp 0 (code đo ảnh khung đầu, miễn phí)**\n\n" + "\n".join(
        f"- {'Vẽ lại' if f.get('severity') == 'redraw' else 'Lưu ý'}: {f.get('problem') or ''}" + (f" → _{f['fix']}_" if f.get("fix") else "")
        for f in flags)


def scores_summary(scores, labels: Dict[str, str]) -> str:
    low = min(scores, key=lambda s: s["score"])
    return f'<span class="vid-sum">Tiêu chí QC · thấp nhất: {escape(labels.get(low["criterion"], low["criterion"]))} {low["score"]:.2f}</span>'


def scores_md(scores, labels: Dict[str, str]) -> str:
    return "\n".join(f"- {labels.get(s['criterion'], s['criterion'])}: **{s['score']:.2f}** (ngưỡng {s['threshold_at_time']})" for s in scores)


def note_summary(label: str, text: str) -> str:
    text = (text or "").strip()
    return f'<span class="vid-sum"><b>{escape(label)}:</b> {escape(text[:80])}{"…" if len(text) > 80 else ""}</span>'
