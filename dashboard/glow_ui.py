"""Nút của bước kế sáng xanh (người dùng 07/10; cờ chat_first — core/next_glow.py): một <style> nhỏ mỗi lần vẽ, nhắm đúng khóa widget.
`targets` dùng chung cho dòng 'Việc tiếp theo' (shell_parts.next_line): chỉ nói 'nút sáng xanh' khi thật có nút đang sáng."""
import streamlit as st

from dashboard import common as C


def targets(p, pid: int, screen: int) -> list:
    """screen: 1 Kịch bản · 2 Storyboard · 3 Video (others → [])."""
    from core import chat_intake, next_glow, stage_map
    if not chat_intake.enabled() or screen not in (1, 2, 3):
        return []
    kind = None
    if screen == 1:
        from dashboard.steps import step1_v2 as V
        scenes = p.conn.execute("SELECT idx FROM scenes WHERE project_id=?", (pid,)).fetchall()
        chars = p.conn.execute("SELECT locked FROM characters WHERE project_id=?", (pid,)).fetchall()
        b_on, b_locked, _, _ = V._budget_state(p, pid)
        kind = V.next_kind(p, pid, scenes, chars, any(c["locked"] for c in chars), b_locked, b_on)
    return next_glow.target(screen, kind, stage_map.build(p.conn, pid), pid,
                            on_motion_tab=st.session_state.get("sb_tab") == C.SB_TABS[1])


def render(p, pid: int, step: str, visible) -> None:
    from core import next_glow
    screen = {C.STEPS[1]: 1, C.STEPS[2]: 2, C.STEPS[3]: 3}.get(step)
    css = next_glow.css(targets(p, pid, screen), list(visible)) if screen else ""
    if css:
        st.html(f"<style>{css}</style>")
