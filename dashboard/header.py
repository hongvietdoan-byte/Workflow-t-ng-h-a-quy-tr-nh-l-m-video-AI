"""Header: login, account bar, settings gear + dialogs, project bar (picker, risk, project settings, pause/cancel)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.admin import asset_library_panel, history, knowledge_panel, lessons_tab, price_editor, users_tab


def risk_popover(p: Pipeline, pid: int) -> None:
    """Small corner note: IP warnings and risk-control blocks seen so far in this project."""
    notes = preflight.risk_notes(p.conn, pid, preflight.load_blocklist())
    with st.popover(f"⚠ Rủi ro ({len(notes)})", help="Ghi chú rủi ro đã gặp: cảnh báo IP và các lần bị chặn risk control"):
        if not notes:
            st.caption("Chưa ghi nhận rủi ro nào.")
        for n in notes:
            tag = ui.badge("IP", "b-warn") if n["kind"] == "ip" else ui.badge("bị chặn", "b-bad")
            ui.html(f'{tag} <b>{escape(n["title"])}</b><br><span class="muted">{escape(n["detail"])}</span>')


def sign_in(conn, email: str) -> bool:
    """Try to sign this browser session in. True on success (the address remembers the e-mail for reloads)."""
    source, local = request_source()
    try:
        st.session_state["auth_token"] = auth.login(conn, email, source, local)
    except auth.AuthError as e:
        st.session_state["login_error"] = str(e)
        return False
    st.session_state.pop("login_error", None)
    st.query_params["login"] = auth.normalize_email(email)
    return True


def login_screen(conn) -> None:
    """Sign-in screen: only an e-mail. Nothing else is shown until someone signs in."""
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        ui.html('<div class="brand" style="font-size:20px"><i></i>AI Video Pipeline</div>')
        email = st.text_input("E-mail của bạn", key="login_email", placeholder="ten@garena.vn")
        if st.button("Vào Dashboard", key="login_btn", type="primary") and sign_in(conn, email):
            st.rerun()
        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])
        st.caption("Chỉ cần nhập e-mail. E-mail công ty được vào với quyền làm video; quyền khác do Owner cấp.")


def require_login(conn) -> None:
    """Sets st.session_state['identity']; shows the sign-in screen and stops the page when nobody is signed in."""
    if not auth_on():
        st.session_state["identity"] = {"email": "local", "name": "Local (đăng nhập tắt)", "role": "owner", "perms": []}
        return
    auth.ensure_owner(conn)
    ident = auth.identity(conn, st.session_state.get("auth_token"))
    if ident is None:
        st.session_state.pop("identity", None)
        st.session_state.pop("auth_token", None)
        remembered = st.query_params.get("login")          # a reload or a bookmark: ?login=ten@garena.vn
        if remembered and not st.session_state.get("login_tried") and sign_in(conn, remembered):
            st.session_state["login_tried"] = True
            ident = auth.identity(conn, st.session_state.get("auth_token"))
        st.session_state["login_tried"] = True
        if ident is None:
            login_screen(conn)
            st.stop()
    st.session_state["identity"] = {"email": ident.email, "name": ident.name, "role": ident.role, "perms": ident.perms}


def current_pid(p: Pipeline):
    """The project selected in the header dropdown (global_bar), read from session_state so the header row
    (rendered above the dropdown) already knows it in the same script run -- selectbox key="global_pid"."""
    ids = [r["id"] for r in p.conn.execute("SELECT id FROM projects ORDER BY id").fetchall()]
    pid = st.session_state.get("global_pid")
    return pid if pid in ids else (ids[0] if ids else None)


def new_project_control(p: Pipeline) -> None:
    """The "+ new project" action, next to the user's name -- a lightweight popover, not a full dialog."""
    with st.popover("➕ Dự án mới", help="Tạo dự án mới"):
        name = st.text_input("Tên dự án", key="new_name")
        if st.button("Tạo dự án", key="new_project_go", type="primary", disabled=not name.strip()):
            pid = p.create_project(name.strip(), created_by=me()["email"])
            st.session_state["global_pid"] = pid
            st.rerun()


def settings_menu(p: Pipeline, pid) -> None:
    """Gear icon next to sign-out: every settings-like feature opens as its own closable panel (st.dialog,
    native X) instead of living inline in the page. Kho tài nguyên/Bảng giá/Kho kiến thức only need the C.DB;
    Lịch sử/Bài học/Phân quyền act on the project selected in the header. Old ?step=history/lessons/users
    deep links still work -- they open the matching dialog once per browser session."""
    deep = st.query_params.get("step")
    if deep in ("history", "lessons", "users") and "deep_dialog_done" not in st.session_state:
        st.session_state["deep_dialog_done"] = True
        if deep == "history":
            open_dialog("dlg_history")
        elif deep == "lessons" and allowed("lessons"):
            open_dialog("dlg_lessons")
        elif deep == "users" and allowed("users"):
            open_dialog("dlg_users")
    with st.popover("⚙", help="Cài đặt"):
        if allowed("assets") and st.button("📁 Kho tài nguyên", key="settings_assets", width="stretch"):
            open_dialog("dlg_assets")
        if allowed("settings") and st.button("💲 Bảng giá", key="settings_pricing", width="stretch"):
            open_dialog("dlg_pricing")
        if allowed("knowledge") and st.button("📚 Kho kiến thức", key="settings_knowledge", width="stretch"):
            open_dialog("dlg_knowledge")
        if pid is not None:
            st.divider()
            if st.button("🗒 Lịch sử", key="settings_history", width="stretch"):
                open_dialog("dlg_history")
            if allowed("lessons") and st.button("🎓 Bài học", key="settings_lessons", width="stretch"):
                open_dialog("dlg_lessons")
            if allowed("users") and st.button("👥 Phân quyền", key="settings_users", width="stretch"):
                open_dialog("dlg_users")
    if st.session_state.get("dlg_assets"):
        _dialog_assets(p)
    if st.session_state.get("dlg_pricing"):
        _dialog_pricing()
    if st.session_state.get("dlg_knowledge"):
        _dialog_knowledge()
    if pid is not None and st.session_state.get("dlg_history"):
        _dialog_history(p, pid)
    if pid is not None and st.session_state.get("dlg_lessons"):
        _dialog_lessons(p, pid)
    if pid is not None and st.session_state.get("dlg_users"):
        _dialog_users(p, pid)


@st.dialog("📁 Kho tài nguyên", width="large", on_dismiss=lambda: close_dialog("dlg_assets"))
def _dialog_assets(p: Pipeline) -> None:
    asset_library_panel(p)


@st.dialog("💲 Bảng giá", on_dismiss=lambda: close_dialog("dlg_pricing"))
def _dialog_pricing() -> None:
    price_editor()


@st.dialog("📚 Kho kiến thức (Director, QC, Motion)", width="large", on_dismiss=lambda: close_dialog("dlg_knowledge"))
def _dialog_knowledge() -> None:
    knowledge_panel()


@st.dialog("🗒 Lịch sử", width="large", on_dismiss=lambda: close_dialog("dlg_history"))
def _dialog_history(p: Pipeline, pid: int) -> None:
    history(p, pid)


@st.dialog("🎓 Bài học", width="large", on_dismiss=lambda: close_dialog("dlg_lessons"))
def _dialog_lessons(p: Pipeline, pid: int) -> None:
    lessons_tab(p, pid)


@st.dialog("👥 Phân quyền", width="large", on_dismiss=lambda: close_dialog("dlg_users"))
def _dialog_users(p: Pipeline, pid: int) -> None:
    users_tab(p, pid)


def account_bar(p: Pipeline) -> None:
    """Identity + quick actions (new project, settings gear) + sign-out, all in one top bar."""
    conn = p.conn
    who = me()
    c1, c2, c3, c4 = st.columns([5, 1.6, 0.6, 1.1], vertical_alignment="center")
    role = "Owner" if who["role"] == "owner" else "Thành viên"
    c1.markdown(f"👤 **{escape(who['name'])}** · {escape(who['email'])} · {role}")
    with c2:
        new_project_control(p)
    with c3:
        settings_menu(p, current_pid(p))
    if not auth_on():
        c1.caption("Đăng nhập đang tắt (DASHBOARD_AUTH=off): mọi người đều là Owner.")
        return
    if c4.button("Đăng xuất", key="logout_btn"):
        auth.logout(conn, st.session_state.get("auth_token"))
        for key in ("auth_token", "identity", "login_tried"):
            st.session_state.pop(key, None)
        st.query_params.pop("login", None)
        st.rerun()


def user_bar() -> str:
    """Who is using the dashboard (honour system, no password). Kept in the address (?user=Ten) so a refresh or a
    bookmark remembers it; every job created from this browser is counted for this name."""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = clean_name(st.query_params.get("user", ""))
    c1, c2 = st.columns([2, 5], vertical_alignment="center")
    typed = clean_name(c1.text_input("👤 Tên của bạn", value=st.session_state["user_name"], placeholder="ví dụ: Viet",
                                     key="user_input", help="Để hệ thống ghi nhận ai đã gen video. Không cần mật khẩu."))
    if typed != st.session_state["user_name"]:
        st.session_state["user_name"] = typed
        st.query_params["user"] = typed
    if not typed:
        c2.markdown(":orange[Nhập tên trước khi gen ảnh/video để lượt gen được ghi cho bạn (nếu để trống sẽ tính là “chưa nhập tên”).]")
    return typed


def project_settings_popover(p: Pipeline, pid: int, proj) -> None:
    """Gear next to the project picker: QC mode/threshold + delete -- moved off the control bar itself
    (2026-09-22 cleanup, same "gear -> popover" pattern as the header's settings_menu) so that row only
    keeps the picker, the risk note and the frequently-used Pause/Resume/Cancel buttons."""
    with st.popover("⚙", help="Cấu hình dự án: chế độ QC, threshold, xóa dự án"):
        mode = st.radio("Chế độ QC", ["auto", "human_qc"], index=0 if proj["operating_mode"] == "auto" else 1,
                        horizontal=True, key=f"mode_{pid}")
        if mode != proj["operating_mode"]:
            p.set_mode(pid, mode)
        th = st.slider("QC threshold", 0.5, 1.0, float(proj["qc_auto_pass_threshold"]), 0.01, key=f"th_{pid}")
        if abs(th - proj["qc_auto_pass_threshold"]) > 1e-9:
            p.set_threshold(pid, th)
        max_retry = st.slider("Retry tối đa mỗi job (rồi báo cho bạn xử lý)", 1, 8, int(proj["max_retry_count"]), 1, key=f"maxretry_{pid}")
        if max_retry != proj["max_retry_count"]:
            p.set_max_retry(pid, max_retry)
        st.divider()
        st.caption("🗑 Xóa dự án cùng cảnh, ảnh, clip, nhạc và video đã tạo (tài nguyên trong kho chung không bị xóa; lịch sử chi tiêu được giữ). "
                   "Chỉ người tạo dự án mới xóa được (dự án cũ chưa ghi người tạo thì Owner xóa).")
        if not can_delete_project(proj):
            who = proj["created_by"]
            st.caption("Dự án này do " + (escape(who) if who else "người dùng cũ") + " tạo nên bạn không xóa được.")
        elif confirm_all(f"proj_del_{pid}", [pid], "🗑 Xóa dự án", f"Xóa hẳn dự án “{proj['name']}”? Không thể khôi phục.", st, "Có, xóa dự án"):
            autopilot.stop(p, pid, "Dự án bị xóa")
            p.cancel_all_active(pid)
            p.delete_project(pid, C.DATA)
            st.toast(f"Đã xóa dự án “{proj['name']}”")
            st.rerun()


def global_bar(p: Pipeline):
    """Project picker + per-project controls. Project creation and the Kho tài nguyên/Bảng giá/Kho kiến thức
    panels moved to the header (account_bar -> new_project_control / settings_menu); mode/threshold/delete
    moved into project_settings_popover so this row only keeps the picker, risk note and Pause/Resume/Cancel."""
    projects = p.conn.execute("SELECT id, name FROM projects ORDER BY id").fetchall()
    if not projects:
        st.info("Chưa có dự án. Bấm “➕ Dự án mới” ở đầu trang để bắt đầu.")
        return None
    with st.container(border=True):
        c0, c1, c2, c3, c4 = st.columns([1.4, 2.2, 1.3, 0.6, 3.0], vertical_alignment="center")
        c0.markdown('<div class="brand"><i></i>AI Video Pipeline</div>', unsafe_allow_html=True)
        ids = [r["id"] for r in projects]
        default_pid = current_pid(p)
        pid = c1.selectbox("Dự án", ids, index=ids.index(default_pid) if default_pid in ids else 0,
                           format_func=lambda i: next(r["name"] for r in projects if r["id"] == i), key="global_pid")
        proj = p.project(pid)
        with c2:
            risk_popover(p, pid)
        with c3:
            project_settings_popover(p, pid, proj)
        b1, b2, b3 = c4.columns(3)
        if b1.button("⏸ Pause", disabled=bool(proj["paused"]), key="btn_pause"):
            p.set_paused(pid, True)
            st.rerun()
        if b2.button("▶ Resume", disabled=not proj["paused"], key="btn_resume"):
            p.set_paused(pid, False)
            st.rerun()
        if b3.button("■ Cancel", key="btn_cancel"):
            st.toast(f"Đã hủy {p.cancel_all_active(pid)} job")
            st.rerun()
    if proj["paused"]:
        st.warning("Pipeline đang PAUSE — không job nào được bắt đầu.")
    spend_line(p, pid)
    ap = autopilot.status(p, pid)
    if ap["state"] in ("running", "queued"):
        st.caption(f"🚀 Chế độ tự động: {ap['note']} (xem chi tiết ở Bước 1)")
    return pid
