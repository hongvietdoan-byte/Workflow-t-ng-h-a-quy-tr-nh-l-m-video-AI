"""Nút bước chính to + nút của bước kế sáng xanh (người dùng 07/10; cờ next_glow BẬT sẵn mọi tài khoản — core/next_glow.py): một <style>
nhỏ mỗi lần vẽ, nhắm đúng khóa widget. Mỗi người tắt phần sáng riêng ở ⚙ → Hệ thống (core/user_prefs, nhớ lần sau).
`targets` dùng chung cho dòng 'Việc tiếp theo' (shell_parts.next_line): chỉ nói 'nút sáng xanh' khi thật có nút đang sáng."""
import streamlit as st

from dashboard import common as C


def targets(p, pid: int, screen: int) -> list:
    """screen: 1 Kịch bản · 2 Storyboard · 3 Video (others → [])."""
    from core import next_glow, stage_map
    if screen not in (1, 2, 3) or not lit_for_me(p):
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


def _email():
    return C.me().get("email") if C.auth_on() else None


def lit_for_me(p) -> bool:
    from core import features, user_prefs
    return features.on("next_glow") and user_prefs.get(p.conn, _email(), "next_glow")


def _save_switch() -> None:
    """Callback: runs in a later script run — opens its own connection (a callback must not reuse the run's sqlite connection)."""
    from core import user_prefs
    from core.db import connect
    user_prefs.set(connect(C.DB), _email(), "next_glow", bool(st.session_state.get("pref_next_glow")))


def person_switch(p) -> None:
    """⚙ → Hệ thống: this person's own switch (kept in the database, so it holds next time)."""
    from core import features, user_prefs
    if not features.on("next_glow"):
        return
    st.toggle("✨ Nút bước kế sáng xanh", value=user_prefs.get(p.conn, _email(), "next_glow"), key="pref_next_glow",
              on_change=_save_switch,
              help="Nút cần bấm tiếp sáng xanh kèm nhãn 👉 Bấm tiếp (giúp người mới). Chỉ đổi cho tài khoản của bạn.")


def render(p, pid: int, step: str, visible) -> None:
    from core import features, next_glow
    screen = {C.STEPS[1]: 1, C.STEPS[2]: 2, C.STEPS[3]: 3}.get(step)
    if not screen or not features.on("next_glow"):
        return
    css = next_glow.big_css(pid) + next_glow.css(targets(p, pid, screen), list(visible))
    st.html(f"<style>{css}</style>")
