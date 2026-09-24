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
    """"+ new project": name plus the decisions every later step depends on — frame format, genre, model priority, game."""
    with st.popover("➕ Dự án mới", help="Tạo dự án mới"):
        st.text_input("Tên dự án", key="new_name")
        aspects = list(formats.ASPECTS)
        st.selectbox("Tỉ lệ khung", aspects, index=aspects.index(formats.DEFAULT_NEW), format_func=formats.label, key="new_aspect",
                     help="Ảnh, video, layout và bản dựng đều làm theo khung này ngay từ đầu (không phải thêm viền đen ở cuối).")
        genres = [None] + list(llm_io.GENRES)
        st.selectbox("Thể loại", genres, index=genres.index("SHORT_FORM"), key="new_genre",
                     format_func=lambda g: "Để Director tự chọn" if g is None else f"{g} — {llm_io.GENRES[g]}")
        prios = list(model_router.PRIORITIES)
        pr = model_router.load_profiles()["priorities"]
        st.selectbox("Ưu tiên model video", prios, index=prios.index(model_router.DEFAULT_PRIORITY), key="new_prio",
                     format_func=lambda k: pr[k]["label"], help="Theo slide ClipAI: Chất lượng / Cân bằng / Tiết kiệm.")
        catalog = subjects.games()
        games = list(catalog)
        st.selectbox("Game / nội dung", games, index=games.index("FF") if "FF" in games else 0, key="new_game",
                     format_func=lambda k: catalog[k][0])
        st.button("Tạo dự án", key="new_project_go", type="primary", disabled=not (st.session_state.get("new_name") or "").strip(),
                  on_click=_create_project, args=(p,))


def settings_menu(p: Pipeline, pid) -> None:
    """ONE gear: 'Dự án này' (review mode, QC policy, delete) and 'Hệ thống' (library, prices, knowledge, history, lessons, users,
    shut down). Each panel opens as its own closable dialog. Old ?step=history/lessons/users links still open the matching dialog."""
    deep = st.query_params.get("step")
    if deep in ("history", "lessons", "users") and "deep_dialog_done" not in st.session_state:
        st.session_state["deep_dialog_done"] = True
        if deep == "history":
            open_dialog("dlg_history")
        elif deep == "lessons" and allowed("lessons"):
            open_dialog("dlg_lessons")
        elif deep == "users" and allowed("users"):
            open_dialog("dlg_users")
    with st.popover("⚙", help="Cài đặt dự án và hệ thống"):
        if pid is not None:
            proj = p.project(pid)
            st.markdown("**Dự án này**")
            modes = list(ui.MODE_LABELS)
            mode = st.radio("Ai duyệt ảnh/clip", modes, index=modes.index(proj["operating_mode"]), format_func=ui.MODE_LABELS.get,
                            horizontal=True, key=f"mode_{pid}")
            if mode != proj["operating_mode"]:
                p.set_mode(pid, mode)
            st.caption("Chính sách QC (ngưỡng, tự gen lại) chỉnh ở Bước 2. Định dạng khung, thể loại, ưu tiên model ở Bước 1 · 1b.")
            if not can_delete_project(proj):
                who = proj["created_by"]
                st.caption("Dự án này do " + (escape(who) if who else "người dùng cũ") + " tạo nên bạn không xóa được.")
            elif confirm_all(f"proj_del_{pid}", [pid], "🗑 Xóa dự án", f"Xóa hẳn dự án “{proj['name']}” cùng ảnh, clip, nhạc, video? Không thể khôi phục.",
                             st, "Có, xóa dự án"):
                autopilot.stop(p, pid, "Dự án bị xóa")
                p.cancel_all_active(pid)
                p.delete_project(pid, C.DATA)
                st.toast(f"Đã xóa dự án “{proj['name']}”")
                st.rerun()
            if st.button("🗒 Lịch sử & thùng rác", key="settings_history", width="stretch"):
                open_dialog("dlg_history")
            cheap = st.checkbox("🧪 Thử rẻ (720p · Kling std · Seedance 2.0/2.5 → Fast)", bool(proj["test_quality"]), key=f"cheap_{pid}",
                                help="Cho đợt thử nghiệm: không gen 1080p, dùng bản rẻ hơn của model. Tắt khi làm video thật.")
            if cheap != bool(proj["test_quality"]):
                p.set_project_field(pid, "test_quality", 1 if cheap else 0)
                st.rerun()
            if st.button("🧬 Nhân bản dự án (để so sánh cách làm)", key="settings_clone", width="stretch"):
                open_dialog("dlg_clone")
            st.divider()
        st.markdown("**Hệ thống**")
        if allowed("assets") and st.button("📁 Kho tài nguyên", key="settings_assets", width="stretch"):
            open_dialog("dlg_assets")
        if allowed("settings") and st.button("💲 Bảng giá", key="settings_pricing", width="stretch"):
            open_dialog("dlg_pricing")
        if allowed("settings") and st.button("💵 Ngân sách thử", key="settings_budget", width="stretch"):
            open_dialog("dlg_budget")
        if allowed("knowledge") and st.button("📚 Kho kiến thức", key="settings_knowledge", width="stretch"):
            open_dialog("dlg_knowledge")
        if pid is not None and allowed("lessons") and st.button("🎓 Bài học", key="settings_lessons", width="stretch"):
            open_dialog("dlg_lessons")
        if pid is not None and allowed("users") and st.button("👥 Phân quyền", key="settings_users", width="stretch"):
            open_dialog("dlg_users")
        if allowed("shutdown"):
            if confirm_all("shutdown", ["go"], "⏻ Tắt Dashboard", "Tắt Dashboard ngay bây giờ? (việc chạy nền dừng, tiến độ đã lưu)", st, "Có, tắt"):
                stop = os.path.join(os.path.dirname(__file__), "..", "tools", "stop_dashboard.ps1")
                subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", stop],
                                 creationflags=0x00000008)
                st.info("Đang tắt… có thể đóng cửa sổ này.")
    if st.session_state.get("dlg_assets"):
        _dialog_assets(p)
    if st.session_state.get("dlg_pricing"):
        _dialog_pricing()
    if st.session_state.get("dlg_budget"):
        _dialog_budget(p)
    if pid is not None and st.session_state.get("dlg_clone"):
        _dialog_clone(p, pid)
    if st.session_state.get("dlg_knowledge"):
        _dialog_knowledge()
    if pid is not None and st.session_state.get("dlg_history"):
        _dialog_history(p, pid)
    if pid is not None and st.session_state.get("dlg_lessons"):
        _dialog_lessons(p, pid)
    if pid is not None and st.session_state.get("dlg_users"):
        _dialog_users(p, pid)


def _own(p: Pipeline) -> Pipeline:
    """A dialog's buttons rerun only the dialog, in another thread than the one that made `p` (SQLite refuses to share a
    connection across threads): every dialog works on its own connection, as the same person."""
    fresh = Pipeline(connect(C.DB))
    fresh.actor = p.actor
    return fresh


@st.dialog("📁 Kho tài nguyên", width="large", on_dismiss=lambda: close_dialog("dlg_assets"))
def _dialog_assets(p: Pipeline) -> None:
    p = _own(p)
    asset_library_panel(p)


@st.dialog("💵 Ngân sách thử", on_dismiss=lambda: close_dialog("dlg_budget"))
def _dialog_budget(p: Pipeline) -> None:
    """Hard spending limit of a test round (kế hoạch v3: ≤ $50): jobs that would pass it stay queued."""
    p = _own(p)
    from core import budget
    s = budget.status(p.conn)
    if s["enabled"]:
        st.markdown(f"**Đang bật** — tính từ {s['since']} (UTC): đã chi ≈ **\\${s['spent']:.2f} / \\${s['usd']:.0f}**, "
                    f"{s['images']}/{s['image_cap']} ảnh.")
        st.progress(min(s["spent"] / s["usd"], 1.0) if s["usd"] else 0.0)
        if s["unknown"]:
            st.caption("Chưa có giá cho: " + ", ".join(s["unknown"]) + " (không tính vào tổng).")
    else:
        st.markdown("**Đang tắt** — không giới hạn chi (dùng cho làm video thật).")
    st.caption("Giá theo bảng giá (ước tính từ slide ClipAI, chưa đo thật). Nhà cung cấp giả lập không tính. Việc vượt trần được giữ "
               "trong hàng đợi và báo lý do ở 📊 Theo dõi.")
    usd = st.number_input("Trần (USD)", 1.0, 1000.0, float(s["usd"]), 5.0, key="budget_usd")
    cap = st.number_input("Tối đa số ảnh Deepix (chưa có giá)", 0, 1000, int(s["image_cap"]), 10, key="budget_imgs")
    c1, c2 = st.columns(2)
    if c1.button("▶ Bắt đầu đợt thử (tính từ bây giờ)", key="budget_start", type="primary"):
        budget.save(p.conn, image_cap=int(cap))
        budget.restart(p.conn, usd)
        st.rerun()
    if s["enabled"] and c2.button("■ Tắt giới hạn", key="budget_stop"):
        budget.stop(p.conn)
        st.rerun()
    if s["enabled"] and (usd != s["usd"] or cap != s["image_cap"]) and st.button("💾 Lưu trần mới (giữ mốc bắt đầu)", key="budget_save"):
        budget.save(p.conn, usd=float(usd), image_cap=int(cap))
        st.rerun()
    st.divider()
    st.markdown(f"**🤖 Claude API** — đã dùng ≈ **\\${s['llm_spent']:.2f} / \\${s['llm_usd']:.2f}**"
                + (f" (tính từ {s['llm_since']} UTC)" if s["llm_since"] else "")
                + (" — **đã hết, Dashboard ngừng gọi Claude**" if s["llm_usd"] > 0 and s["llm_left"] <= 0 else ""))
    st.progress(min(s["llm_spent"] / s["llm_usd"], 1.0) if s["llm_usd"] > 0 else 0.0)
    st.caption("Luôn bật (kể cả khi tắt đợt thử): mỗi lần gọi Claude API ghi số token vào/ra × giá niêm yết (data/pricing.json); hết "
               "thì Dashboard dừng gọi Claude và báo. Tiền Claude cũng cộng vào trần đợt thử ở trên. Claude Code trên máy (claude_cli) "
               "không tính ở đây. Đặt 0 để bỏ trần.")
    llm_cap = st.number_input("Số tiền đang có trên tài khoản Claude API (USD)", 0.0, 10000.0, float(s["llm_usd"]), 1.0,
                              key="budget_llm_usd")
    d1, d2 = st.columns(2)
    if d1.button("💾 Vừa nạp tiền — tính lại từ bây giờ", key="budget_llm_restart"):
        budget.restart_llm(p.conn, llm_cap)
        st.rerun()
    if llm_cap != s["llm_usd"] and d2.button("💾 Chỉ đổi trần (giữ số đã dùng)", key="budget_llm_save"):
        budget.save(p.conn, llm_usd=float(llm_cap))
        st.rerun()


@st.dialog("🧬 Nhân bản dự án", on_dismiss=lambda: close_dialog("dlg_clone"))
def _dialog_clone(p: Pipeline, pid: int) -> None:
    """Same script, Character Bible (Lock, voices, references), World Bible and delivery settings — another way of making it."""
    p = _own(p)
    from core import compare, shots
    proj = p.project(pid)
    st.caption("Bản sao bắt đầu cùng điểm xuất phát (kịch bản, nhân vật, giọng, phong cách, thiết lập bản giao) nhưng chưa có ảnh/clip — "
               "dùng để so sánh cách làm trên cùng kịch bản.")
    name = st.text_input("Tên dự án mới", f"{proj['name']} — bản so sánh", key="clone_name")
    modes = list(shots.MODES)
    mode = st.selectbox("Cách chia cảnh của bản sao", modes, index=modes.index(shots.mode(proj)), format_func=lambda m: shots.MODES[m],
                        key="clone_mode")
    rows = st.checkbox("Giữ nguyên các cảnh/shot hiện tại (cùng kế hoạch của Director)", True, key="clone_rows",
                       help="Bỏ chọn để chạy lại Director ở bản sao (ví dụ đổi từ 'một clip mỗi cảnh' sang 'chia shot').")
    if st.button("🧬 Tạo bản sao", key="clone_go", type="primary", disabled=not name.strip()):
        new = compare.clone_project(p, pid, name.strip(), mode, with_rows=rows)
        st.success(f"Đã tạo dự án #{new} “{name.strip()}” — chọn ở ô Dự án trên cùng.")


@st.dialog("💲 Bảng giá", on_dismiss=lambda: close_dialog("dlg_pricing"))
def _dialog_pricing() -> None:
    price_editor()


@st.dialog("📚 Kho kiến thức (Director, QC, Motion)", width="large", on_dismiss=lambda: close_dialog("dlg_knowledge"))
def _dialog_knowledge() -> None:
    knowledge_panel()


@st.dialog("🗒 Lịch sử", width="large", on_dismiss=lambda: close_dialog("dlg_history"))
def _dialog_history(p: Pipeline, pid: int) -> None:
    p = _own(p)
    history(p, pid)


@st.dialog("🎓 Bài học", width="large", on_dismiss=lambda: close_dialog("dlg_lessons"))
def _dialog_lessons(p: Pipeline, pid: int) -> None:
    p = _own(p)
    lessons_tab(p, pid)


@st.dialog("👥 Phân quyền", width="large", on_dismiss=lambda: close_dialog("dlg_users"))
def _dialog_users(p: Pipeline, pid: int) -> None:
    p = _own(p)
    users_tab(p, pid)


def account_bar(p: Pipeline) -> None:
    """Who is signed in (one short line) + sign-out. Actions live in the project bar below."""
    who = me()
    c1, c4 = st.columns([8, 1.1], vertical_alignment="center")
    role = "Owner" if who["role"] == "owner" else "Thành viên"
    c1.caption(f"👤 {escape(who['name'])} · {escape(who['email'])} · {role}"
               + ("" if auth_on() else " · đăng nhập đang tắt (DASHBOARD_AUTH=off)"))
    if auth_on() and c4.button("Đăng xuất", key="logout_btn"):
        auth.logout(p.conn, st.session_state.get("auth_token"))
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




def global_bar(p: Pipeline):
    """ONE bar: brand · project · state · risk · pause/continue/cancel · new project · ⚙."""
    projects = p.conn.execute("SELECT id, name FROM projects ORDER BY id").fetchall()
    with st.container(border=True):
        c0, c1, c2, c3, c4, c5 = st.columns([1.3, 2.4, 1.1, 2.6, 1.3, 0.5], vertical_alignment="center")
        c0.markdown('<div class="brand"><i></i>AI Video Pipeline</div>', unsafe_allow_html=True)
        with c4:
            new_project_control(p)
        if not projects:
            with c5:
                settings_menu(p, None)
            st.info("Chưa có dự án. Bấm “➕ Dự án mới” để bắt đầu.")
            return None
        ids = [r["id"] for r in projects]
        default_pid = current_pid(p)
        pid = c1.selectbox("Dự án", ids, index=ids.index(default_pid) if default_pid in ids else 0,
                           format_func=lambda i: next(r["name"] for r in projects if r["id"] == i), key="global_pid",
                           label_visibility="collapsed")
        proj = p.project(pid)
        with c2:
            risk_popover(p, pid)
        b1, b2, b3 = c3.columns(3)
        if b1.button("⏸ Tạm dừng", disabled=bool(proj["paused"]), key="btn_pause"):
            p.set_paused(pid, True)
            st.rerun()
        if b2.button("▶ Tiếp tục", disabled=not proj["paused"], key="btn_resume"):
            p.set_paused(pid, False)
            st.rerun()
        if confirm_all("btn_cancel", [pid], "■ Hủy việc", "Hủy mọi ảnh/clip đang chờ hoặc đang gen của dự án này?", b3, "Có, hủy"):
            st.toast(f"Đã hủy {p.cancel_all_active(pid)} việc")
            st.rerun()
        with c5:
            settings_menu(p, pid)
    if proj["paused"]:
        st.warning("Dự án đang TẠM DỪNG — không ảnh/clip nào được gửi đi. Bấm ▶ Tiếp tục ở thanh trên.")
    spend_line(p, pid)
    ap = autopilot.status(p, pid)
    if ap["state"] in ("running", "queued", "waiting"):
        st.caption(f"🚀 Chế độ tự động: {ap['note']} (xem chi tiết ở Bước 1)")
    return pid



def _create_project(p: Pipeline) -> None:
    """Button callback (runs before the widgets, so it may still select the new project in the picker)."""
    name = (st.session_state.get("new_name") or "").strip()
    if not name:
        return
    p = Pipeline(connect(C.DB))                     # a callback runs in another thread than the one that made `p`
    pid = p.create_project(name, created_by=me()["email"], aspect=st.session_state.get("new_aspect"),
                           genre=st.session_state.get("new_genre"), model_priority=st.session_state.get("new_prio"),
                           game=st.session_state.get("new_game"))
    qc_policy.apply(p, pid, "balanced")
    st.session_state["global_pid"] = pid
    st.session_state["new_name"] = ""
