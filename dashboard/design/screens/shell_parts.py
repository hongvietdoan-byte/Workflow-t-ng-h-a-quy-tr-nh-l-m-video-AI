"""Khung ứng dụng v2 (S13 nhánh B): dải hero của dự án + khối "Đặt lại thanh tiền" (chỉ Owner). Chỉ được gọi khi cờ ui_v2 bật.

Không đụng core: số liệu lấy từ những hàm app.py/header.py đã dùng (lineage, autopilot, project_budget, money_reset)."""
from html import escape
from typing import Callable, List, Tuple

import streamlit as st

from dashboard.design import components as D

# màn (chỉ số trong common.STEPS) → số bước của next_step.next_action
_NEXT_STEP = {1: 1, 2: 2, 3: 4, 4: 5}


def overall_progress(p, pid: int, done: list) -> float:
    """0..1 over the five stages: script (Bible locked) · pictures · motion · clips · final render. `done` = app.step_done()."""
    from core import lineage
    summ = lineage.summary(p.conn, pid)
    n = summ["total"]
    parts = [1.0 if done and done[0][0] == "done" else 0.0]
    for key in ("images", "motion", "videos"):
        parts.append(min(summ[key][0] / n, 1.0) if n else 0.0)
    parts.append(1.0 if len(done) > 4 and done[4][0] == "done" else 0.0)
    return sum(parts) / len(parts)


def status_pills(p, pid: int, proj) -> List[Tuple[str, str]]:
    from core import autopilot
    out: List[Tuple[str, str]] = []
    if proj["paused"]:
        out.append(("Tạm dừng", "warn"))
    ap = autopilot.status(p, pid)
    out.append({"running": ("Tự động: đang chạy", "info"), "queued": ("Tự động: đang xếp hàng", "info"),
                "waiting": ("Tự động: chờ bạn", "warn"), "needs_attention": ("Tự động: cần xem", "bad")
                }.get(ap["state"], ("Tự động: không chạy", "mute")))
    try:
        from core import project_budget
        if project_budget.enabled():
            data = project_budget.get(p.conn, pid) or {}
            out.append(("Ngân sách đã khóa", "ok") if data.get("locked") else ("Ngân sách chưa khóa", "warn"))
    except Exception:  # noqa: BLE001 - a status chip only
        pass
    return out


def next_line(p, pid: int, screen_index: int, data_dir: str) -> Tuple[str, str]:
    """(text, level) of the one-line "việc tiếp theo" for the current screen, read by code (dashboard/next_step.py)."""
    from dashboard import next_step
    step = _NEXT_STEP.get(screen_index, 1)
    try:
        res = next_step.next_action(p, pid, step, data_dir)
    except Exception:  # noqa: BLE001 - the strip must never break the page
        res = None
    return res if res else ("Chưa có việc nào đang chờ.", "done")


def short_text(text: str, limit: int = 96) -> str:
    """One-line version of a longer sentence (cut at a word, with …); the caller puts the full text in a ⓘ when this differs."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-·")
    return cut + "…"


def fold(label: str, body_md: str = "") -> None:
    """Chi tiết TRONG một POPOVER (popover không lồng được trong popover → mục gập có nhãn chữ; 02/10: bỏ glyph ⓘ cùng nút tròn)."""
    with st.expander("Chi tiết · " + label):
        if body_md:
            st.markdown(body_md)


_STAGES = ("Kịch bản", "Ảnh", "Motion", "Clip", "Bản giao")


def progress_details(pid: int, done: list) -> str:
    """The ⓘ of the overall-progress meter: what the percentage is made of + the per-stage state (the old meter label said the same in one line)."""
    mark = {"done": "xong", "stale": "đã cũ", "todo": "chưa xong"}
    rows = []
    for i, name in enumerate(_STAGES):
        state, text = done[i] if i < len(done) else ("todo", "")
        rows.append(f"- **{name}**: {mark.get(state, state)}" + (f" ({text})" if text else ""))
    return ("Tiến độ tổng = trung bình 5 phần: kịch bản (Bible đã khóa) · ảnh · motion · clip · bản giao.\n\n" + "\n".join(rows)
            + f"\n\nDự án #{pid}")


def project_hero(p, pid: int, done: list, screen_index: int, data_dir: str, level_fn: Callable) -> None:
    """The strip under the top bar on project screens: name · status pills · overall progress · 🎚 level · next step.
    Priority (docs/QUY_TAC_BO_CUC_UI_V2 §5): state pills + progress % + ONE next-step line outside; the breakdown, the project number and a
    long next-step sentence live in ⓘ."""
    proj = p.project(pid)
    frac = overall_progress(p, pid, done)
    text, level = next_line(p, pid, screen_index, data_dir)
    icon = {"wait": "⏸ ", "todo": "👉 Việc tiếp theo: ", "done": "✅ "}.get(level, "")
    short = short_text(text)
    with D.hero("shell"):
        # 02/10 (rà soát #10): hai CỘT liền thay cho hai hàng × hai cột — trước đây "Việc tiếp theo" bị căn giữa theo khối 🎚 cao bên phải
        # nên cách xa các pill; nay mỗi cột xếp sát từ trên xuống.
        left, right = st.columns([5, 4], vertical_alignment="top")
        with left:
            st.html(D.hero_html(proj["name"], "", status_pills(p, pid, proj)))
            if short != " ".join(text.split()):
                with D.info("shell-next", anchor=f'<div class="v2-note shell-next">{escape(icon + short)}</div>', help_text=D.md_plain(icon + text)):
                    st.markdown(icon + text)
            else:
                st.html(f'<div class="v2-note shell-next">{escape(icon + short)}</div>')
        with right:
            with D.info("shell-progress", anchor=D.meter(frac, "Tiến độ tổng"), help_text=D.md_plain(progress_details(pid, done))):
                st.markdown(progress_details(pid, done))
            with st.container(key="shell-level"):
                level_fn()


# ---- 💵 màu thanh theo mức dự tính (S14.16, core.money_policy) -------------------------------------------------------------------

_MONEY_COLOR = {"ok": "var(--ok)", "warn": "var(--warn)", "danger": "var(--bad)"}


def money_meter(spent: float, planned: float, text: str = "") -> str:
    """A 💵 meter coloured by the planned amount (chính sách tiền 04/10): green, yellow at ≥ money_policy.WARN_AT, red at ≥ DANGER_AT.
    The bar fills to 100 %; the number says the real share (it may pass 100 % — the caps warn, they do not stop)."""
    from core import money_policy
    share = float(spent or 0) / float(planned) if planned else 0.0
    color = _MONEY_COLOR[money_policy.level(spent, planned)]
    label = f'<div style="font-size:13px;color:var(--muted);margin-bottom:3px">{escape(text)}</div>' if text else ""
    return (f'{label}<div class="v2-meter-row"><div class="v2-meter"><i style="width:{min(share, 1.0) * 100:.0f}%;background:{color}">'
            f'</i></div><b>{share * 100:.0f}%</b></div>')


def money_flag(spent: float, planned: float) -> str:
    """' 🟡' / ' 🔴' after the 💵 label when the money passed the planned amount / passed it far ('' otherwise)."""
    from core import money_policy
    return {"warn": " 🟡", "danger": " 🔴"}.get(money_policy.level(spent, planned), "")


# ---- 💵 Đặt lại thanh tiền (chỉ Owner) -------------------------------------------------------------------------------------------

def last_reset_line(conn, bar: str, key=None) -> str:
    """HTML "Đặt lại lần cuối: <lúc> bởi <ai> — <vì sao>" ('' when never reset)."""
    from core import money_reset
    rec = money_reset.last(conn, bar, key)
    if not rec:
        return ""
    return (f'<div class="shell-last">Đặt lại lần cuối: {escape(str(rec.get("at", "")))} bởi {escape(str(rec.get("who", "?")))}'
            f' — {escape(str(rec.get("why", "")))}</div>')


def last_reset_md(conn, bar: str, label: str, key=None) -> str:
    """Markdown bullet "<label>: đặt lại lần cuối …" for the ⓘ of the 💵 card ('' when never reset)."""
    from core import money_reset
    rec = money_reset.last(conn, bar, key)
    if not rec:
        return ""
    return f"- **{label}** — đặt lại lần cuối: {rec.get('at', '')} bởi {rec.get('who', '?')} — {rec.get('why', '')}"


def money_reset_block(p, pid, project_has_budget: bool, actor: dict) -> None:
    """Owner-only block in the 💵 card. Tick the bars, give a REQUIRED reason, confirm twice; core.money_reset does the work (and refuses
    anyone who is not the Owner, so hiding this block is a convenience, not the guard)."""
    from core import money_reset
    from dashboard.common import confirm_all
    if actor.get("role") != "owner":
        return
    with st.expander("↺ Đặt lại thanh tiền (chỉ Owner)"):
        st.caption("Thanh đếm lại từ bây giờ; sổ chi giữ nguyên, mỗi lần đặt lại được ghi nhật ký.")
        bars = []
        # S14.6 (rà soát 04/10): mốc thanh đợt thử = mốc của ĐỢT ngân sách → chỉ đổi qua "▶ Bắt đầu đợt ngân sách mới" (core.budget_rounds),
        # nếu không đợt và thanh lệch nhau. Giữ khóa shell-mr-trial (ô bị khóa, chỉ đường sang đợt mới).
        st.checkbox("Đợt thử (tổng tiền cả đợt) — đặt lại bằng đợt mới", key="shell-mr-trial", value=False, disabled=True,
                    help="Thanh đợt thử đếm theo đợt ngân sách: mở 📅 Mức dùng theo ngày · đợt ngân sách → ▶ Bắt đầu đợt ngân sách mới.")
        st.caption("Thanh đợt thử: dùng 📅 Mức dùng theo ngày · đợt ngân sách → ▶ Bắt đầu đợt ngân sách mới (đóng đợt cũ + lưu tóm tắt).")
        if st.checkbox("Claude API", key="shell-mr-claude"):
            bars.append("claude")
        if project_has_budget and pid is not None:
            if st.checkbox("Ngân sách dự án này", key=f"shell-mr-project-{pid}"):
                bars.append("project")
        why = (st.text_input("Lý do (bắt buộc)", key="shell-mr-why", placeholder="ví dụ: nạp thêm tiền, bắt đầu đợt thử mới") or "").strip()
        ready = bool(bars) and bool(why)
        if not ready:
            st.caption("Cần chọn một thanh và nhập lý do.")
        names = ", ".join(money_reset.BARS[b].split(" (")[0] for b in bars)
        ids = (tuple(bars) + (why,)) if ready else ()
        if confirm_all("shell_mr_go", ids, "↺ Đặt lại các thanh đã chọn",
                       f"Đặt lại {names}? Thanh đếm lại từ bây giờ (sổ chi giữ nguyên). Lý do: {why}", st, "Có, đặt lại"):
            try:
                done = money_reset.reset(p.conn, actor, bars, why, project_id=pid if "project" in bars else None)
            except Exception as e:  # noqa: BLE001 - shown, never a crash of the bar
                st.error(f"Không đặt lại được: {e}")
                return
            st.toast("Đã đặt lại: " + ", ".join(sorted(done)))
            st.rerun()
