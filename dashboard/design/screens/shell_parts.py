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


def project_hero(p, pid: int, done: list, screen_index: int, data_dir: str, level_fn: Callable) -> None:
    """The strip under the top bar on project screens: name · status pills · overall progress · 🎚 level · next step."""
    proj = p.project(pid)
    frac = overall_progress(p, pid, done)
    text, level = next_line(p, pid, screen_index, data_dir)
    with D.hero("shell"):
        left, right = st.columns([5, 4], vertical_alignment="top")
        with left:
            st.html(D.hero_html(proj["name"], f"Dự án #{pid}", status_pills(p, pid, proj)))
        with right:
            st.html(D.meter(frac, "Tiến độ tổng (kịch bản · ảnh · motion · clip · bản giao)"))
        nxt, lvl = st.columns([5, 4], vertical_alignment="center")
        icon = {"wait": "⏸ ", "todo": "👉 Việc tiếp theo: ", "done": "✅ "}.get(level, "")
        nxt.html(f'<div class="v2-note shell-next">{escape(icon + text)}</div>')
        with lvl:
            with st.container(key="shell-level"):
                level_fn()


# ---- 💵 Đặt lại thanh tiền (chỉ Owner) -------------------------------------------------------------------------------------------

def last_reset_line(conn, bar: str, key=None) -> str:
    """HTML "Đặt lại lần cuối: <lúc> bởi <ai> — <vì sao>" ('' when never reset)."""
    from core import money_reset
    rec = money_reset.last(conn, bar, key)
    if not rec:
        return ""
    return (f'<div class="shell-last">Đặt lại lần cuối: {escape(str(rec.get("at", "")))} bởi {escape(str(rec.get("who", "?")))}'
            f' — {escape(str(rec.get("why", "")))}</div>')


def money_reset_block(p, pid, project_has_budget: bool, actor: dict) -> None:
    """Owner-only block in the 💵 card. Tick the bars, give a REQUIRED reason, confirm twice; core.money_reset does the work (and refuses
    anyone who is not the Owner, so hiding this block is a convenience, not the guard)."""
    from core import money_reset
    from dashboard.common import confirm_all
    if actor.get("role") != "owner":
        return
    with st.expander("↺ Đặt lại thanh tiền (chỉ Owner)"):
        st.caption("Thanh sẽ đếm lại từ bây giờ. Không xóa dòng chi nào trong sổ chi; mọi lần đặt lại được ghi vào nhật ký.")
        bars = []
        if st.checkbox("Đợt thử (tổng tiền cả đợt)", key="shell-mr-trial"):
            bars.append("trial")
        if st.checkbox("Claude API", key="shell-mr-claude"):
            bars.append("claude")
        if project_has_budget and pid is not None:
            if st.checkbox("Ngân sách dự án này", key=f"shell-mr-project-{pid}"):
                bars.append("project")
        why = (st.text_input("Lý do (bắt buộc)", key="shell-mr-why", placeholder="ví dụ: nạp thêm tiền, bắt đầu đợt thử mới") or "").strip()
        ready = bool(bars) and bool(why)
        if not ready:
            st.caption("Chọn ít nhất một thanh và nhập lý do để bấm được nút đặt lại.")
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
