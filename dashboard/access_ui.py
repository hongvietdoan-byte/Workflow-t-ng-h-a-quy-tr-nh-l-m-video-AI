"""Quyền theo dự án trên giao diện (đợt F, 02/10): chế độ CHỈ XEM khóa mọi nút ghi, băng chữ nói rõ mức quyền, chỗ quản lý người theo dõi.

Lõi (core/access.py) mới là chỗ chặn thật: mọi hàm ghi / gửi job / duyệt / cất đều kiểm quyền và báo lỗi tiếng Việt. Lớp này chỉ làm cho
người xem khỏi bấm vào chỗ sẽ bị từ chối: widget ghi bị `disabled` (một lần vá Streamlit, bật theo phiên bằng st.session_state['_ro_screen']
để cả các fragment tự chạy lại cũng bị khóa). Nút xem chi tiết (khóa `sel_btn_…`) và tải về vẫn dùng được.
"""
import functools
from contextlib import contextmanager

import streamlit as st

from core import access

WRITE_WIDGETS = ("button", "checkbox", "toggle", "radio", "selectbox", "multiselect", "select_slider", "slider", "text_input", "text_area",
                 "number_input", "date_input", "time_input", "file_uploader", "color_picker", "data_editor", "pills", "segmented_control",
                 "feedback", "form_submit_button", "camera_input", "audio_input", "chat_input")
VIEW_KEY_PREFIXES = ("sel_btn_", "home_open_", "inb_")           # buttons that only open / look (detail dialog, open a project)
FLAG = "_ro_screen"
_installed = False


def is_read_only() -> bool:
    try:
        return bool(st.session_state.get(FLAG))
    except Exception:  # noqa: BLE001 - outside a script run
        return False


def _harmless(args, kwargs) -> bool:
    key = kwargs.get("key")
    return isinstance(key, str) and key.startswith(VIEW_KEY_PREFIXES)


def _wrap_method(orig):
    @functools.wraps(orig)
    def wrapper(self, *args, **kwargs):
        if is_read_only() and not _harmless(args, kwargs):
            kwargs["disabled"] = True
        return orig(self, *args, **kwargs)
    wrapper._ro_wrapped = True
    return wrapper


def _wrap_plain(orig):
    @functools.wraps(orig)
    def wrapper(*args, **kwargs):
        if is_read_only() and not _harmless(args, kwargs):
            kwargs["disabled"] = True
        return orig(*args, **kwargs)
    wrapper._ro_wrapped = True
    return wrapper


def install() -> None:
    """Patch the Streamlit input widgets once per process: they become `disabled` while the session flag is set."""
    global _installed
    if _installed:
        return
    from streamlit.delta_generator import DeltaGenerator
    for name in WRITE_WIDGETS:
        method = getattr(DeltaGenerator, name, None)
        if method is not None and not getattr(method, "_ro_wrapped", False):
            setattr(DeltaGenerator, name, _wrap_method(method))
        plain = getattr(st, name, None)
        if plain is not None and not getattr(plain, "_ro_wrapped", False):
            setattr(st, name, _wrap_plain(plain))
    _installed = True


def set_read_only(on: bool) -> None:
    if on:
        install()
    st.session_state[FLAG] = bool(on)


@contextmanager
def read_only(on: bool = True):
    """Everything drawn inside has its input widgets disabled (used for popovers drawn outside the project screens)."""
    prev = is_read_only()
    if on:
        set_read_only(True)
    try:
        yield
    finally:
        st.session_state[FLAG] = prev


def level_text(level) -> str:
    return {"admin": "Owner", "own": "chủ dự án", "edit": "theo dõi · được sửa", "view": "theo dõi · chỉ xem"}.get(level, "không có quyền")


def banner(p, pid: int) -> None:
    """One short line under the top bar when the person is not the project's creator / Owner: whose project it is and what they may do."""
    from dashboard import common as C
    if not C.auth_on():
        return
    lvl = C.project_level(p, pid)
    if lvl in ("admin", "own", None):
        if lvl == "admin":
            creator = (p.project(pid)["created_by"] or "").strip()
            if not creator:
                st.info("Dự án chưa có chủ (dự án cũ) — chỉ Owner thấy. Gán chủ ở 👥 Nhóm → “Quyền theo dự án”.")
        return
    creator = (p.project(pid)["created_by"] or "").strip() or "chưa rõ"
    if lvl == "view":
        st.warning(f"👁 Chế độ CHỈ XEM — dự án của {creator}; mọi nút ghi (duyệt, gen, sửa, cất) bị khóa. "
                   "Nhờ chủ dự án hoặc Owner nâng lên “Được sửa” nếu cần làm.")
    else:
        st.info(f"Dự án của {creator} — bạn được cấp quyền SỬA (theo dõi): duyệt, gen, sửa như chủ; không cất / xóa / đổi người theo dõi.")


def watchers_editor(p, pid: int, key: str = "w") -> None:
    """List of the project's watchers with a level each; add / change / remove. Owner and the project's creator only."""
    from dashboard import common as C
    conn = p.conn
    user = C.access_user()
    if not access.can_manage(conn, pid, user):
        st.caption("Chỉ Owner hoặc chủ dự án đổi danh sách người theo dõi.")
        for w in access.list_watchers(conn, pid):
            st.caption(f"• {w['email']} — {access.LEVEL_LABEL[w['level']]}")
        return
    current = access.list_watchers(conn, pid)
    if not current:
        st.caption("Chưa ai theo dõi dự án này. Chỉ chủ dự án và Owner thấy nó.")
    for w in current:
        c1, c2, c3 = st.columns([3, 1.6, 1], vertical_alignment="center")
        c1.markdown(f"**{w['email']}**")
        new = c2.selectbox("Mức", list(access.LEVELS), index=list(access.LEVELS).index(w["level"]), format_func=access.LEVEL_LABEL.get,
                           key=f"{key}_lvl_{pid}_{w['email']}", label_visibility="collapsed")
        if new != w["level"]:
            _try(lambda: access.set_watcher(conn, user, pid, w["email"], new), f"Đã đổi {w['email']} sang “{access.LEVEL_LABEL[new]}”")
        if c3.button("Bỏ", key=f"{key}_rm_{pid}_{w['email']}"):
            _try(lambda: access.remove_watcher(conn, user, pid, w["email"]), f"Đã bỏ {w['email']} khỏi danh sách theo dõi")
    taken = {w["email"] for w in current}
    creator = (p.project(pid)["created_by"] or "").strip().lower()
    candidates = [u["email"] for u in _users(conn) if u["role"] != "owner" and u["active"] and u["email"] not in taken and u["email"] != creator]
    if not candidates:
        st.caption("Không còn tài khoản nào để thêm (Owner mời người mới ở 👥 Nhóm).")
        return
    a1, a2, a3 = st.columns([3, 1.6, 1], vertical_alignment="bottom")
    who = a1.selectbox("Thêm người theo dõi", candidates, key=f"{key}_new_{pid}")
    lvl = a2.selectbox("Mức", list(access.LEVELS), format_func=access.LEVEL_LABEL.get, key=f"{key}_newlvl_{pid}",
                       help="Chỉ xem: thấy dự án nhưng mọi nút ghi bị khóa. Được sửa: duyệt, gen, sửa như chủ (không cất / xóa).")
    if a3.button("Thêm", key=f"{key}_add_{pid}", type="primary"):
        _try(lambda: access.set_watcher(conn, user, pid, who, lvl), f"Đã thêm {who} — {access.LEVEL_LABEL[lvl]}")


def _users(conn) -> list:
    from core import auth
    return auth.list_users(conn)


def _try(fn, done: str) -> None:
    try:
        fn()
    except access.AccessDenied as e:
        st.error(str(e))
    else:
        st.toast(done)
        st.rerun()


def team_panel(p) -> None:
    """👥 Nhóm → Quyền theo dự án (Owner): pick a project, manage its watchers; give an old project with no creator to someone."""
    from dashboard import common as C
    conn = p.conn
    user = C.access_user()
    rows = conn.execute("SELECT id, name, created_by FROM projects ORDER BY id DESC").fetchall()
    if not rows:
        st.caption("Chưa có dự án.")
        return
    orphans = [r for r in rows if not (r["created_by"] or "").strip()]
    pid = st.selectbox("Dự án", [r["id"] for r in rows], key="access_pick",
                       format_func=lambda i: next(f"#{r['id']} {r['name']} — " + (r["created_by"] or "chưa có chủ") for r in rows if r["id"] == i))
    watchers_editor(p, pid, "team")
    if orphans:
        st.markdown(f"**Dự án chưa có chủ ({len(orphans)})** — chỉ Owner thấy cho tới khi gán chủ")
        users = [u["email"] for u in _users(conn) if u["role"] != "owner" and u["active"]]
        if users:
            o1, o2, o3 = st.columns([3, 3, 1], vertical_alignment="bottom")
            target = o1.selectbox("Dự án cũ", [r["id"] for r in orphans], key="orphan_pick", format_func=lambda i: f"#{i} " + next(
                r["name"] for r in orphans if r["id"] == i))
            owner = o2.selectbox("Gán chủ", users, key="orphan_owner")
            if o3.button("Gán", key="orphan_go"):
                _try(lambda: access.assign_creator(conn, user, target, owner), f"Đã gán #{target} cho {owner}")
        else:
            st.caption("Chưa có tài khoản thành viên để gán — mời người ở khối “Mời người mới”.")
