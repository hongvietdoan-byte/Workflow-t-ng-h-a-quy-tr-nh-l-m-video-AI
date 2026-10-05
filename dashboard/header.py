"""Header: login, account bar, settings gear + dialogs, project bar (picker, risk, project settings, pause/cancel)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from core import access, archive
from dashboard import access_ui, common as C, limits_ui
from dashboard.admin import asset_library_panel, history, knowledge_panel, lessons_tab, price_editor, users_tab


def _go_item(project_id, screen) -> None:
    C.go_screen(project_id, screen or "script")


INBOX_SHOWN = 3          # v2: how many inbox items stay outside the ⓘ fold


def inbox_card(p: Pipeline) -> None:
    """📥 Việc cần bạn (đợt 3): what waits for you across all projects — reviews, locks of money, the automatic run, services out of credit.
    The Owner can also list the whole team's (core/inbox.py)."""
    from core import inbox
    who = me()
    email = who.get("email", "") if auth_on() else ""
    is_owner = who.get("role") == "owner"
    can_money = is_owner or allowed("settings")
    mine = inbox.items(p.conn, email, is_owner, can_money, auth_on())
    with st.popover(f"📥 Việc cần bạn ({len(mine)})" + (" 🔴" if any(i["level"] == "bad" for i in mine) else ""), width="stretch",
                    help="Mọi việc đang chờ bạn ở mọi dự án: duyệt ảnh / clip, ảnh / clip gen lỗi, khóa ngân sách, chạy tự động đang dừng, dịch vụ hết tiền"):
        team_view = False
        if auth_on() and is_owner:
            team_view = st.radio("Phạm vi", ["Của tôi", "Cả nhóm"], horizontal=True, label_visibility="collapsed", key="inbox_scope") == "Cả nhóm"
        items = inbox.items(p.conn, email, is_owner, can_money, auth_on(), team_wide=True) if team_view else mine
        v2 = ui.v2_on()
        kind = ""
        if not v2 or len(items) > INBOX_SHOWN:             # v2: the type filter only matters once the list is longer than what is shown
            kind = st.selectbox("Loại việc", [""] + list(inbox.KINDS), format_func=lambda k: "Tất cả loại việc" if not k else k,
                                key="inbox_kind", label_visibility="collapsed")
        if kind:
            items = [i for i in items if i["kind"] == kind]
        if not items:
            st.caption("Không có việc nào đang chờ bạn." if not kind else "Không có việc loại này.")

        def draw(n: int, it) -> None:
            c1, c2 = st.columns([4, 1.2], vertical_alignment="center")
            tag = {"bad": "🔴", "wait": "⏸", "warn": "⚠", "todo": "👉"}.get(it["level"], "")
            c1.markdown(f"{tag} **{escape(it['kind'])}** — {escape(it['text'])}"
                        + (f"  \n<small>#{it['project_id']} {escape(it['project'])}" + (f" · việc của {escape(it['who'])}" if it["who"] else "")
                           + "</small>" if it["project_id"] else ""), unsafe_allow_html=True)
            if it["project_id"] and it["screen"]:
                c2.button("Mở →", key=f"inb_{n}", on_click=_go_item, args=(it["project_id"], it["screen"]), width="stretch")

        shown = items[:30]
        if v2 and len(shown) > INBOX_SHOWN:                 # v2: the first 3 stay outside, the rest fold into ⓘ
            for n, it in enumerate(shown[:INBOX_SHOWN]):
                draw(n, it)
            with st.expander(f"Còn {len(items) - INBOX_SHOWN} việc nữa"):
                for n, it in enumerate(shown[INBOX_SHOWN:], start=INBOX_SHOWN):
                    draw(n, it)
                if len(items) > 30:
                    st.caption(f"… còn {len(items) - 30} việc: lọc theo loại để xem tiếp.")
            return
        for n, it in enumerate(shown):
            draw(n, it)
        if len(items) > 30:
            st.caption(f"… còn {len(items) - 30} việc: lọc theo loại để xem tiếp.")


LEVEL_BUSY = ("running", "queued", "waiting", "needs_attention")     # the run holds the review mode + gates (autopilot._save_cfg)
LEGACY_KEYS = ("mode_{pid}", "ap_gate_bible_{pid}", "ap_gate_pilot_{pid}", "ap_gate_board_{pid}", "qcpol_{pid}")


def _level_changed(pid: int) -> None:
    """on_change of the 🎚 radio (runs before the widgets): write the three settings, then drop the older controls' remembered values so
    they show the new settings instead of writing the old ones back (Streamlit keeps a keyed widget's value between runs)."""
    from core import automation
    pick = st.session_state.get(f"level_{pid}")
    if not pick:
        return
    p = C.scoped(Pipeline(connect(C.DB)))                     # a callback runs in another thread than the one that made `p`
    try:
        automation.apply(p, pid, pick)
    except ValueError as e:
        st.session_state["level_error"] = str(e)
        return
    for k in LEGACY_KEYS:
        st.session_state.pop(k.format(pid=pid), None)


def level_bar(p: Pipeline, pid: int, compact: bool = False) -> None:
    """🎚 Mức tự động (đợt 3): one choice over who approves + the run's gates + QC strictness (core/automation.py). Only the project's
    creator or the Owner changes it; locked while the automatic run holds the project."""
    from core import automation
    info = autopilot.status(p, pid)
    busy = info["state"] in LEVEL_BUSY
    cur = automation.current(p, pid)
    keys = list(automation.LEVELS)
    proj = p.project(pid)
    creator = (proj["created_by"] or "").strip().lower() if "created_by" in proj.keys() else ""
    can = (not auth_on()) or not C.read_only(p, pid)        # đợt F: creator, Owner and "Được sửa" watchers
    st.session_state[f"level_{pid}"] = cur if cur in keys else None        # always show what the project really has
    c1, c2 = (st, st) if compact else st.columns([1, 5], vertical_alignment="center")    # v2: the hero strip gives it its own row
    c1.caption("🎚 Mức tự động")
    with (st.container() if compact else c2):
        st.radio("Mức tự động", keys, horizontal=True, label_visibility="collapsed", format_func=lambda k: automation.LEVELS[k]["label"],
                 disabled=busy or not can, key=f"level_{pid}", on_change=_level_changed, args=(pid,),
                 help=("Đang chạy tự động — đổi mức sau khi dừng." if busy else "Chỉ người có quyền sửa dự án (chủ, Owner, người theo dõi “Được sửa”) đổi mức." if not can
                       else "\n\n".join(f"**{v['label']}**: {v['desc']}" for v in automation.LEVELS.values())))
    err = st.session_state.pop("level_error", None)
    if err:
        st.warning(err)
    if compact and (cur not in keys or busy):         # v2: one short line, the full sentence in ⓘ
        from dashboard.design import components as D
        short = ("Tùy chỉnh tay — chọn một mức để đặt lại" if cur not in keys else "") + (" · " if cur not in keys and busy else "") \
            + ("đang chạy tự động nên chưa đổi được mức" if busy else "")
        full = (("**Tùy chỉnh:** bạn đã chỉnh tay cổng duyệt / chính sách QC / người duyệt — chọn một mức để đặt lại cả ba." if cur not in keys else "")
                + ("\n\n" if cur not in keys and busy else "")
                + ("**Đang chạy tự động:** chạy tự động đang giữ dự án nên không đổi được (lúc chạy luôn dùng QC tự duyệt, xong thì trả lại "
                   "chế độ bạn chọn)." if busy else ""))
        D.line(f'<span class="shell-status">{escape(short)}</span>', full, "shell-level-why")
    elif cur not in keys or busy:                     # the level's description is the radio's tooltip; speak only when it matters
        st.caption(("Tùy chỉnh: bạn đã chỉnh tay cổng duyệt / chính sách QC / người duyệt — chọn một mức để đặt lại cả ba."
                    if cur not in keys else "") + ("  ·  chạy tự động đang giữ dự án nên không đổi được (lúc chạy luôn dùng QC tự duyệt, "
                                                    "xong thì trả lại chế độ bạn chọn)" if busy else ""))


def risk_popover(p: Pipeline, pid: int) -> None:
    """Small corner note: IP warnings and risk-control blocks seen so far in this project."""
    notes = preflight.risk_notes(p.conn, pid, preflight.load_blocklist())
    if ui.v2_on():                                   # v2: lives inside the "Thêm" menu (a popover cannot hold a popover) → a labelled fold
        with st.expander(f"⚠ Rủi ro ({len(notes)})"):
            _risk_body(notes)
        return
    with st.popover(f"⚠ Rủi ro ({len(notes)})", help="Ghi chú rủi ro đã gặp: cảnh báo IP và các lần bị chặn risk control"):
        _risk_body(notes)


def screen_feedback(p: Pipeline, pid) -> None:
    """S14.19 Đợt 0: 💬 “Góp ý màn này” — what is wrong with the screen in view → user_feedback (kind 'screen', 0 USD).
    v2: a labelled fold inside “⋯ Thêm” (a popover cannot hold a popover); classic: a popover next to ⚠ Rủi ro.
    Open to a "Chỉ xem" watcher too: saying what is wrong with a screen changes nothing in the project."""
    prev = access_ui.is_read_only()
    access_ui.set_read_only(False)
    try:
        _screen_feedback_wrap(p, pid)
    finally:
        access_ui.set_read_only(prev)


def _screen_feedback_wrap(p: Pipeline, pid) -> None:
    if ui.v2_on():
        with st.expander("💬 Góp ý màn này"):
            _screen_feedback_body(p, pid)
        return
    with st.popover("💬 Góp ý", help="Góp ý màn này: chỗ nào khó dùng, thiếu, sai"):
        _screen_feedback_body(p, pid)


def _screen_feedback_body(p: Pipeline, pid) -> None:
    from core import feedback
    screen = str(st.session_state.get("step") or "")
    with st.form("fb_screen_form", clear_on_submit=True, border=False):
        text = st.text_area(f"Màn “{screen or 'này'}” chưa ổn chỗ nào?", key="fb_screen_text", height=80)
        stage = st.selectbox("Khâu", list(feedback.STAGES), index=list(feedback.STAGES).index("ui"), key="fb_screen_stage",
                             format_func=feedback.STAGES.get)
        sent = st.form_submit_button("💬 Gửi góp ý", key="fb_screen_send", width="stretch")
    if sent:
        if not (text or "").strip():
            st.warning("Góp ý trống — viết vài chữ rồi gửi lại.")
            return
        act(lambda: feedback.add(p.conn, "screen", project_id=pid, screen=screen or None, stage=stage, text=text,
                                 created_by=(p.user or {}).get("email") or p.actor), "Đã ghi góp ý — cảm ơn!")


def _risk_body(notes) -> None:
    if not notes:
        st.caption("Chưa ghi nhận rủi ro nào.")
    for n in notes:
        tag = ui.badge("IP", "b-warn") if n["kind"] == "ip" else ui.badge("bị chặn", "b-bad")
        ui.html(f'{tag} <b>{escape(n["title"])}</b><br><span class="muted">{escape(n["detail"])}</span>')


def sign_in(conn, email: str, passcode: str = None) -> bool:
    """Try to sign this browser session in. True on success (the address remembers the e-mail for reloads).
    The one way in, for the form and for an old ?login= link alike: with DASHBOARD_LAN=1 it goes through core/machine_auth (try limit,
    a member only from a machine the Owner approved, audit with the machine name); otherwise auth.login exactly as before."""
    from core import machine_auth
    source, local = request_source()
    st.session_state.pop("login_notice", None)
    try:
        st.session_state["auth_token"] = machine_auth.sign_in(conn, email, C.request_ip(), local, source, passcode)
    except machine_auth.MachinePending as e:            # S14.7: not an error — the Owner has to approve this PC first
        st.session_state.pop("login_error", None)
        st.session_state["login_notice"] = str(e)
        return False
    except auth.AuthError as e:
        st.session_state["login_error"] = str(e)
        return False
    st.session_state.pop("login_error", None)
    # S6.4 (kế hoạch sau #8): the address keeps the session's random token for reloads — never the e-mail (a shared link or a
    # screenshot used to show who was signed in)
    st.query_params.pop("login", None)
    st.query_params["s"] = st.session_state["auth_token"]
    return True


def login_screen(conn) -> None:
    """Sign-in screen: only an e-mail. Nothing else is shown until someone signs in."""
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        ui.html('<div class="brand" style="font-size:20px"><i></i>AI Video Pipeline</div>')
        email = st.text_input("E-mail của bạn", key="login_email", placeholder="ten@garena.vn")
        passcode = None
        if (email or "").strip().lower() == auth.OWNER_EMAIL and not request_source()[1]:
            passcode = st.text_input("Mã Owner (khi đăng nhập Owner từ máy khác)", type="password", key="login_passcode")
        if st.button("Vào Dashboard", key="login_btn", type="primary") and sign_in(conn, email, passcode):
            st.rerun()
        if st.session_state.get("login_notice"):
            st.info("⏳ " + st.session_state["login_notice"])
        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])
        from core import machine_auth
        if machine_auth.lan_on():
            st.caption("Chỉ cần nhập e-mail. Dashboard đang mở cho mạng LAN: thành viên chỉ vào được từ máy PC đã được Owner duyệt "
                       "(lần đầu từ một máy → gửi yêu cầu duyệt, chờ Owner ở 👥 Nhóm).")
        else:
            st.caption("Chỉ cần nhập e-mail. E-mail công ty được vào với quyền làm video; quyền khác do Owner cấp.")


def require_login(conn) -> None:
    """Sets st.session_state['identity']; shows the sign-in screen and stops the page when nobody is signed in."""
    if not auth_on():
        st.session_state["identity"] = {"email": "local", "name": "Local (đăng nhập tắt)", "role": "owner", "perms": []}
        return
    auth.ensure_owner(conn)
    ident = auth.identity(conn, st.session_state.get("auth_token"))
    if ident is None and st.query_params.get("s"):         # S6.4: a reload keeps the session by its token (?s=…), not by an e-mail
        by_link = auth.identity(conn, st.query_params.get("s"))
        if by_link is not None and not (by_link.role == "owner" and not request_source()[1]):   # an Owner link never works elsewhere
            st.session_state["auth_token"] = st.query_params.get("s")
            ident = by_link
        else:
            st.query_params.pop("s", None)
    if ident is None:
        st.session_state.pop("identity", None)
        st.session_state.pop("auth_token", None)
        remembered = st.query_params.get("login")          # an old bookmark ?login=ten@garena.vn — signed in once, then the address
        # carries the token instead (never the owner: see auth)
        if remembered and remembered.strip().lower() == auth.OWNER_EMAIL and not request_source()[1]:
            remembered = None                              # a link must not sign anyone in as Owner from another machine
        if remembered and not st.session_state.get("login_tried") and sign_in(conn, remembered):
            st.session_state["login_tried"] = True
            ident = auth.identity(conn, st.session_state.get("auth_token"))
        st.session_state["login_tried"] = True
        if ident is None:
            login_screen(conn)
            st.stop()
    from core import machine_auth                          # S14.7: a member's session works only from a machine approved for them
    refused = machine_auth.session_refusal(conn, ident.email, ident.role, C.request_ip(), request_source()[1])
    if refused:
        for key in ("auth_token", "identity"):
            st.session_state.pop(key, None)
        st.query_params.pop("s", None)
        st.session_state["login_error"] = refused
        login_screen(conn)
        st.stop()
    st.session_state["identity"] = {"email": ident.email, "name": ident.name, "role": ident.role, "perms": ident.perms}


def current_pid(p: Pipeline):
    """The project selected in the header dropdown (global_bar), read from session_state so the header row
    (rendered above the dropdown) already knows it in the same script run -- selectbox key="global_pid"."""
    ids = [r["id"] for r in archive.active_projects(p.conn, C.access_user())]          # 📦 archived projects are not offered
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
        limits_ui.usage_caption(p)                   # S14.18: dở x/2 · hôm nay y/2 · đang cất z/1 (Owner: không giới hạn)
        limits_ui.panel(p, "create")


def _restore_project(project_id: int) -> None:
    """Button callback (runs before the widgets, so it may still switch the picker to the restored project)."""
    from core import person_limits
    try:
        archive.restore(C.scoped(Pipeline(connect(C.DB))), project_id)  # a callback runs in another thread than the one that made `p`
    except person_limits.LimitReached as e:              # S14.18: 2 unfinished open already — GIỮ / BỎ (BỎ = swap in one move)
        limits_ui.remember(e, "restore", project_id)
        return
    limits_ui.clear()
    st.session_state["global_pid"] = project_id
    st.toast("Đã khôi phục dự án — dự án vẫn đang tạm dừng, bấm ▶ Tiếp tục khi muốn chạy tiếp")


def archived_list(p: Pipeline) -> None:
    """⚙ → 📦 Dự án đã cất: every put-away project with a restore button (nothing was deleted). S14.18: finished ones are listed apart
    in the "🏁 Kho dự án đã xong" (no limit); the 📦 list is the unfinished ones (a person keeps at most 1, core/person_limits)."""
    limits_ui.panel(p, "restore")
    done = archive.finished_projects(p.conn, C.access_user())
    if done:
        with st.expander(f"🏁 Kho dự án đã xong ({len(done)})"):
            st.caption("Dự án đã xuất bản giao rồi cất: giữ quá trình job, sổ chi, bản giao để tra cứu. Không giới hạn số lượng.")
            _archived_rows(p, done)
    rows = archive.parked_projects(p.conn, C.access_user())
    if not rows:
        return
    if ui.v2_on():                                   # v2: a fold (the list can be long) whose note is the old one-line caption
        with st.expander(f"📦 Dự án đã cất ({len(rows)})"):
            st.caption("Ẩn khỏi danh sách, không chạy tự động; dữ liệu còn nguyên.")
            _archived_rows(p, rows)
        return
    st.markdown(f"**📦 Dự án đã cất ({len(rows)})**")
    st.caption("Ẩn khỏi danh sách, không chạy tự động; dữ liệu còn nguyên.")
    _archived_rows(p, rows)


def _archived_rows(p, rows) -> None:
    for r in rows:
        c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
        c1.caption(f"#{r['id']} {escape(r['name'])}")
        if access.can_manage(p.conn, r["id"], C.access_user()):         # restore = Owner / the project's creator
            c2.button("↩ Khôi phục", key=f"proj_restore_{r['id']}", on_click=_restore_project, args=(r["id"],))
        else:
            c2.caption("Chỉ Owner / chủ dự án khôi phục")


def settings_menu(p: Pipeline, pid, label: str = "⚙") -> None:
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
    with st.popover(label, help="Cài đặt dự án và hệ thống"):
        account_section(p)
        # rà soát 01/10 (đợt 2): 11 mục → 3 nhóm. Tiền (ngân sách thử, bảng giá) ở thẻ 💵 trên thanh trên.
        t_proj, t_res, t_sys = st.tabs(["Dự án", "Tài nguyên & kiến thức", "Hệ thống"])
        with t_proj:
            if pid is not None:
                _settings_project(p, pid)
            else:
                st.caption("Chưa chọn dự án.")
            archived_list(p)
        with t_res:
            if allowed("assets") and st.button("📁 Kho tài nguyên", key="settings_assets", width="stretch"):
                open_dialog("dlg_assets")
            if allowed("knowledge") and st.button("📚 Kho kiến thức", key="settings_knowledge", width="stretch"):
                open_dialog("dlg_knowledge")
            if pid is not None and allowed("lessons") and st.button("🎓 Bài học", key="settings_lessons", width="stretch"):
                open_dialog("dlg_lessons")
        with t_sys:
            if st.toggle("🌙 Nền tối", value=ui.dark_on(), key="dark_toggle", help="Đổi nền sang tối cho đỡ chói; nhớ trong địa chỉ trang (?theme=dark). "
                                                                                    "Bảng dữ liệu vẫn nền sáng.") != ui.dark_on():
                ui.set_dark(not ui.dark_on())
                st.rerun()
            st.toggle("🧠 Chế độ chuyên gia", key="expert_mode",
                      help="Hiện mọi tùy chọn nâng cao: dán JSON tay, nối ảnh, World Bible, storyboard layout, chính sách QC, video tham chiếu, "
                           "kế hoạch model, thử nghiệm, bảng làm tay ở màn Bản giao. Tắt: mỗi bước chỉ hiện việc của một lần chạy thường.")
            if allowed("settings") and st.button("🧪 Tính năng thử", key="settings_features", width="stretch",
                                                 help="Bật / tắt từng tính năng chưa thử thật, hoặc chọn preset Ổn định / Thử nghiệm"):
                open_dialog("dlg_features")
            if st.button("📏 Giới hạn hệ thống", key="settings_limits", width="stretch",
                         help="Số cấu hình + số đo từ lịch sử job thật (kèm số mẫu), hàng đợi hiện tại, ước tính thời gian"):
                open_dialog("dlg_limits")
            if pid is not None and st.button("🗒 Lịch sử & thùng rác", key="settings_history", width="stretch"):
                open_dialog("dlg_history")
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
    if st.session_state.get("dlg_features"):
        _dialog_features(p)
    if pid is not None and st.session_state.get("dlg_clone"):
        _dialog_clone(p, pid)
    if st.session_state.get("dlg_knowledge"):
        _dialog_knowledge()
    if st.session_state.get("dlg_limits"):
        _dialog_limits(p)
    if pid is not None and st.session_state.get("dlg_history"):
        _dialog_history(p, pid)
    if pid is not None and st.session_state.get("dlg_lessons"):
        _dialog_lessons(p, pid)
    if pid is not None and st.session_state.get("dlg_users"):
        _dialog_users(p, pid)


def _settings_project(p: Pipeline, pid: int) -> None:
    """⚙ → Dự án: review mode, cheap test, clone, put away / delete — and (Owner / creator) who watches the project. A "Chỉ xem" watcher
    sees the settings with every input disabled (the core refuses the writes anyway: core/access.py)."""
    ro = C.read_only(p, pid)
    if ro:
        st.caption("👁 Chỉ xem — bạn không đổi được cài đặt dự án này.")
    with access_ui.read_only(ro):
        _settings_project_body(p, pid)
    if auth_on():
        with st.expander("👁 Người theo dõi dự án", expanded=False):
            access_ui.watchers_editor(p, pid, "set")


def _settings_project_body(p: Pipeline, pid: int) -> None:
    proj = p.project(pid)
    modes = list(ui.MODE_LABELS)
    mode = st.radio("Ai duyệt ảnh/clip", modes, index=modes.index(proj["operating_mode"]), format_func=ui.MODE_LABELS.get,
                    horizontal=True, key=f"mode_{pid}")
    if mode != proj["operating_mode"]:
        p.set_mode(pid, mode)
    v2 = ui.v2_on()
    where = "Chính sách QC (ngưỡng, tự gen lại) chỉnh ở màn Storyboard. Định dạng khung, thể loại, ưu tiên model ở màn Kịch bản · 1b."
    cheap_tip = ("Cho đợt thử nghiệm: ảnh ở kích thước nhỏ nhất model Deepix nhận cho khung dự án, không gen 1080p, dùng "
                 "bản rẻ hơn của model video. Dự án tạo khi đợt thử ngân sách đang bật tự bật chế độ này. Tắt khi làm video thật.")
    if v2:                                           # v2: the pointer + what "Thử rẻ" means fold into one ⓘ; the label stays short
        from dashboard.design.screens import shell_parts as SP
        SP.fold("Chỉnh ở đâu? · “Thử rẻ” là gì", f"{where}\n\n**🧪 Thử rẻ** = ảnh cỡ nhỏ nhất · 720p · Kling std · "
                f"Seedance 2.0/2.5 → Fast. {cheap_tip}")
    else:
        st.caption(where)
    cheap = st.checkbox("🧪 Thử rẻ" if v2 else "🧪 Thử rẻ (ảnh cỡ nhỏ nhất · 720p · Kling std · Seedance 2.0/2.5 → Fast)", bool(proj["test_quality"]),
                        key=f"cheap_{pid}", help=cheap_tip)
    if cheap != bool(proj["test_quality"]):
        p.set_project_field(pid, "test_quality", 1 if cheap else 0)
        st.rerun()
    if st.button("🧬 Nhân bản dự án (để so sánh cách làm)", key="settings_clone", width="stretch"):
        open_dialog("dlg_clone")
    if not can_delete_project(proj):                 # archive / delete = Owner or the creator (a "Được sửa" watcher may not)
        st.caption("Cất / xóa dự án: chỉ Owner hoặc chủ dự án (" + (escape(proj["created_by"]) if proj["created_by"] else "chưa có chủ") + ").")
        return
    if confirm_all(f"proj_archive_{pid}", [pid], "📦 Cất dự án này",
                   f"Cất dự án “{proj['name']}”? Dự án ẩn khỏi danh sách, tạm dừng và không chạy tự động; KHÔNG xóa gì "
                   "(ảnh, clip, chi tiêu giữ nguyên). Khôi phục bất cứ lúc nào ở ⚙ → Dự án → “📦 Dự án đã cất”.", st, "Có, cất"):
        from core import person_limits
        try:
            archive.archive(p, pid)
        except person_limits.LimitReached as e:      # S14.18: 1 unfinished project put away already — restore / delete / ask the Owner
            limits_ui.remember(e, "archive", pid)
        else:
            limits_ui.clear()
            st.toast(f"Đã cất dự án “{proj['name']}”")
            st.rerun()
    limits_ui.panel(p, "archive")
    if not can_delete_project(proj):
        who = proj["created_by"]
        st.caption("Dự án này do " + (escape(who) if who else "người dùng cũ") + " tạo nên bạn không xóa được.")
    elif confirm_all(f"proj_del_{pid}", [pid], "🗑 Xóa dự án", f"Xóa hẳn dự án “{proj['name']}” cùng ảnh, clip, nhạc, video? Không thể khôi phục.",
                     st, "Có, xóa dự án"):
        autopilot.stop(p, pid, "Dự án bị xóa")
        report = {}
        note = cancel_everything(p, pid, report)          # T3: the running tasks are stopped at the provider too, not only here
        if report.get("busy"):                            # nothing was cancelled: deleting now would orphan tasks still billing
            st.warning(f"Chưa xóa dự án. {note}")
            return
        p.delete_project(pid, C.DATA)
        st.toast(f"Đã xóa dự án “{proj['name']}”. {note}")
        st.rerun()


def cancel_everything(p: Pipeline, pid, report_out=None) -> str:
    """■ Hủy / delete project (T3, S14.3 B1a): core.runner.cancel_all — rights first, then the running tasks at ClipAI / Deepix (once
    per task), then every queued/running job here. A service not configured on this machine (video_runner / image_runner → None) is
    named in the note, never skipped silently. Returns the sentence for the toast."""
    from core import runner as job_runner
    report = job_runner.cancel_all(p, pid, video=C.video_runner(p), image=C.image_runner(p))
    if report_out is not None:
        report_out.update(report)              # the caller may need {"busy": True} (the turn stayed busy: nothing was cancelled)
    return job_runner.cancel_note(report)


def money_card(p: Pipeline, pid) -> None:
    """💵 ONE place for the money (rà soát 01/10, đợt 2): trial round, Claude API, services out of credit, this project's locked budget.
    Replaces ⚙ Ngân sách thử / ⚙ Bảng giá / the scattered lines — those two dialogs open from here."""
    from core import budget, project_budget
    s = budget.status(p.conn)
    claude_out = s["llm_usd"] > 0 and s["llm_left"] <= 0
    halts = s.get("out_of_credit") or {}
    flag = " 🔴" if halts else ""
    v2 = ui.v2_on()
    from dashboard.design.screens import shell_parts as SP
    if v2 and not flag:                              # S14.16: yellow past the planned amount, red far past it (money_policy)
        flags = [SP.money_flag(s["spent"], s["usd"]) if s["enabled"] else "", SP.money_flag(s["llm_spent"], s["llm_usd"])
                 if s["llm_usd"] > 0 else ""]
        flag = " 🔴" if " 🔴" in flags else " 🟡" if " 🟡" in flags else ""
    elif claude_out:
        flag = " 🔴"
    label = f"💵 {s['spent']:.2f}/{s['usd']:.0f}" if s["enabled"] else "💵 Tiền"
    if v2:
        label = "💵 Tiền" + (f" · {s['spent']:.2f}/{s['usd']:.0f}" if s["enabled"] else "")      # v2: always a word next to the icon
    from dashboard.design import components as D
    with st.popover(label + flag, help="Tiền còn lại theo dịch vụ + dự án; duyệt ngân sách dự án; bảng giá"):
        for service, h in halts.items():
            st.error(f"**{service}** báo HẾT TIỀN lúc {h.get('at')} — mọi lượt gửi tới dịch vụ này đang dừng.")
            # S14.7 (D1): mở lại một dịch vụ là việc tiền → chỉ người có quyền "Cài đặt & bảng giá" (hoặc Owner)
            if allowed("settings"):
                if st.button(f"Đã nạp tiền — mở lại {service}", key=f"mc_reopen_{service}"):
                    budget.reopen(p.conn, service)
                    st.rerun()
            else:
                st.caption("Nhờ Owner (hoặc người có quyền “Cài đặt & bảng giá”) mở lại dịch vụ sau khi nạp tiền.")
        more = []                                        # v2: P3 details collected here, drawn once in a "ⓘ Chi tiết" fold at the end
        if s["enabled"]:
            frac = min(s["spent"] / s["usd"], 1.0) if s["usd"] else 0.0
            if v2:
                st.html(SP.money_meter(s["spent"], s["usd"], f"Đợt thử: ${s['spent']:.2f} / mức dự tính ${s['usd']:.0f}"
                                       + (" — vượt (vẫn gọi)" if s["spent"] > s["usd"] else "")))
                more.append(f"- **Đợt thử:** {s['images']}/{s['image_cap']} ảnh · {s['audios']}/{s['audio_cap']} âm thanh")
                more.append(SP.last_reset_md(p.conn, "trial", "Đợt thử"))
            else:
                st.markdown(f"**Đợt thử:** \\${s['spent']:.2f} / \\${s['usd']:.0f} · {s['images']}/{s['image_cap']} ảnh · "
                            f"{s['audios']}/{s['audio_cap']} âm thanh")
                ui.progress_bar(frac, invert=True)
        else:
            st.caption("Đợt thử: tắt (không giới hạn chi).")
        if s["llm_usd"] > 0:
            if v2:
                st.html(SP.money_meter(s["llm_spent"], s["llm_usd"], f"Claude API: ${s['llm_spent']:.2f} / mức dự tính ${s['llm_usd']:.2f}"
                                       + (" — vượt (vẫn gọi)" if s["llm_spent"] > s["llm_usd"] else "")))
                more.append(SP.last_reset_md(p.conn, "claude", "Claude API"))
            else:
                st.markdown(f"**Claude API:** \\${s['llm_spent']:.2f} / \\${s['llm_usd']:.2f}" + (" — **đã hết**" if claude_out else ""))
                ui.progress_bar(min(s["llm_spent"] / s["llm_usd"], 1.0), invert=True)
        project_has_budget = False
        stage_table = ""
        if pid is not None and project_budget.enabled():
            data = project_budget.get(p.conn, pid) or {}
            project_has_budget = bool(data)
            spent = project_budget.spent_by_stage(p.conn, pid)
            if data.get("locked"):
                caps = data.get("caps") or {}
                total = float(project_budget.planned(p.conn, pid) or 0)
                if v2:                                   # S14.39: ONE summary line (SP.project_line) below; by-stage numbers are in the fold
                    more.append(SP.last_reset_md(p.conn, "project", "Ngân sách dự án này", pid))
                else:
                    st.markdown(f"**Dự án này 🔒** đã chi {sum(spent.values()):.2f} / trần {total:.2f} USD")
                rows = [{"Khâu": lb, "Đã chi": f"{spent[k]:.2f}", "Trần": f"{caps.get(k, 0):.2f}"} for k, lb in project_budget.STAGES.items()]
                if v2:                                   # per-stage budget = P3 → the ⓘ fold; rule 7: an HTML table follows the theme
                    stage_table = ('<table class="v2-table"><tr><th>Khâu</th><th>Đã chi</th><th>Trần</th></tr>' + "".join(
                        f"<tr><td>{escape(r['Khâu'])}</td><td>{r['Đã chi']}</td><td>{r['Trần']}</td></tr>" for r in rows) + "</table>")
                else:
                    data_table(rows, hide_index=True, width="stretch")
            else:
                try:
                    prop = project_budget.propose(p, pid)
                    if not v2:
                        st.markdown(f"**Dự án này:** chưa duyệt · dự tính ≈ {prop['total']:.2f} USD · đã chi {sum(spent.values()):.2f}")
                        try:                                               # S14.16: the approval shows the TOTAL estimated cost (tính dư)
                            st.markdown("💵 " + project_budget.cost_summary(p, pid)["md"])
                        except Exception as e:  # noqa: BLE001 - the approval still works; the missing estimate is said
                            st.caption(SP.summary_error(e))
                    if confirm_all(f"mc_ok_{pid}", ["go"], f"✔ Duyệt & KHÓA ngân sách ≈ {prop['total']:.2f} USD",
                                   f"Khóa ngân sách dự án ≈ {prop['total']:.2f} USD (trần từng khâu theo bảng ở màn Kịch bản)? Sau khi khóa, mọi lời "
                                   "gọi trả tiền vượt mức sẽ được CẢNH BÁO (vẫn gửi); chỉ người được nâng mức, kèm lý do.", st, "Có, khóa"):
                        project_budget.approve(p, pid, p.actor, prop)
                        st.rerun()
                except Exception as e:  # noqa: BLE001 - the card must never break the bar
                    # J1 (S14.4 C1b): the reason + what to do, not only the class name
                    diag.record(p.conn, "system", "warn", f"thẻ ngân sách dự án: {type(e).__name__}: {e}", "budget_card", pid)
                    st.caption(f"Chưa tính được ngân sách dự án: {str(e)[:160] or type(e).__name__}. Cách xử lý: kiểm tra dự án đã "
                               "tách cảnh và bảng giá (⚙ Cài đặt), rồi tải lại trang; vẫn lỗi thì gửi báo cáo ở ⚙ Chẩn đoán.")
        if v2 and pid is not None:                       # S14.39: ONE line for the open project + the per-stage detail in the fold
            try:
                cs = project_budget.cost_summary(p, pid)
                st.markdown("💵 **Dự án đang mở:** " + project_budget.md_safe(cs["line"]))
                more.insert(0, "**Đã chi + ước tính phần còn lại** (ước tính, tính dư)\n\n" + SP.summary_detail_md(cs))
            except Exception as e:  # noqa: BLE001 - the card must never break the bar; the missing estimate is said
                st.caption(SP.summary_error(e))
        if v2 and (stage_table or any(more)):
            with st.expander("Chi tiết"):
                if stage_table:
                    st.html(stage_table)
                st.markdown("\n".join(x for x in more if x))
        from dashboard.design.screens import money_days as MD
        can_days, can_set = MD.can_view(me()), allowed("settings")        # S14.6 Gói K: sổ chi MỌI dự án → người có quyền tiền / theo dõi
        if v2 and can_days and can_set:                                   # S14.39: three small buttons in one row
            c1, c2, c3 = st.columns(3)
            with c1:
                MD.open_button()                                          # mức dùng theo ngày + đợt ngân sách
            if c2.button("⚙ Đợt thử & Claude", key="mc_budget", width="stretch"):
                open_dialog("dlg_budget")
            if c3.button("💲 Bảng giá", key="mc_pricing", width="stretch"):
                open_dialog("dlg_pricing")
        else:
            if can_days:
                MD.open_button()                                          # mức dùng theo ngày + đợt ngân sách
            if can_set:
                b1, b2 = st.columns(2)
                if b1.button("⚙ Đợt thử & Claude", key="mc_budget", width="stretch"):
                    open_dialog("dlg_budget")
                if b2.button("💲 Bảng giá", key="mc_pricing", width="stretch"):
                    open_dialog("dlg_pricing")
        if v2:
            SP.reset_two_button(p, me())                                     # Owner: working button; others: locked + the reason
    from dashboard.design.screens import money_days as MD
    MD.dialog_if_open(me())


@st.dialog("🧪 Tính năng thử", width="large", on_dismiss=lambda: close_dialog("dlg_features"))
def _dialog_features(p: Pipeline) -> None:
    """Rà soát 01/10 (đợt 2): every feature flag with its state, why and evidence; a preset or one flag at a time — no dashboard.env."""
    from core import features
    st.caption("Tính năng đổi cách gửi tới model trả tiền nhưng chưa qua thử thật thì mặc định TẮT. Chọn preset hoặc bật / tắt từng cái; "
               "lựa chọn lưu ở máy này (data/feature_settings.json), có hiệu lực ngay cho việc gửi kế tiếp.")
    cur = features.settings()
    presets = list(features.PRESETS)
    pick = st.radio("Preset", presets, index=presets.index(cur["preset"]), format_func=features.PRESETS.get, key="feat_preset")
    if pick != cur["preset"]:
        features.save_settings(preset=pick)
        st.rerun()
    if cur["preset"] == "experimental":
        st.warning("Preset Thử nghiệm bật mọi tính năng chưa thử thật (trừ 3 cờ từng gây hại: " + ", ".join(features.HARMFUL)
                   + "). Có thể tốn tiền và đổi kết quả — dùng cho dự án thử có trần.")
    q = st.text_input("Tìm", key="feat_q", placeholder="tên hoặc lý do…").strip().lower()
    only_unv = st.checkbox("Chỉ tính năng chưa thử thật", False, key="feat_unv")
    rows = []
    for name, meta in features.FEATURES.items():
        if only_unv and meta["verified"]:
            continue
        if q and q not in name and q not in meta.get("label", "").lower() and q not in meta.get("why", "").lower():
            continue
        rows.append((name, meta))
    st.caption(f"{len(rows)} / {len(features.FEATURES)} tính năng · đang bật {sum(1 for n in features.FEATURES if features.on(n))}"
               f" · bật mà chưa thử thật {len(features.on_unverified())}")
    for name, meta in rows[:60]:
        c1, c2 = st.columns([5, 1.3], vertical_alignment="center")
        on = features.on(name)
        badge = "✅ đã thử thật" if meta["verified"] else "⚠ chưa thử thật"
        harmful = " · ⛔ từng gây hại" if name in features.HARMFUL else ""
        c1.markdown(f"**{escape(name)}** — {badge}{harmful}  \n{escape(meta.get('label', ''))}")
        c1.caption(f"{features.why_state(name)} · {escape(meta.get('why', ''))}")
        new = c2.toggle("Bật", on, key=f"feat_{name}")
        if new != on:
            features.save_settings(flags={name: new})
            st.rerun()
    if len(rows) > 60:
        st.caption(f"… còn {len(rows) - 60} tính năng: lọc bằng ô Tìm.")
    if cur["flags"] and st.button("↺ Bỏ mọi lựa chọn riêng (theo preset)", key="feat_reset"):
        features.save_settings(flags={k: None for k in list(cur["flags"])})
        st.rerun()


@st.dialog("📏 Giới hạn hệ thống", width="large", on_dismiss=lambda: close_dialog("dlg_limits"))
def _dialog_limits(p: Pipeline) -> None:
    """Kế hoạch V4 6.3: the limits as configured, what the job history measured (with n and a confidence — never a guess), the queue
    now, and how long the video step of a film should take."""
    from core import capacity
    p = _own(p)
    cfg = capacity.config()
    st.markdown("**Cấu hình** (số chính xác trong code / biến môi trường)")
    st.markdown(f"- Dự án tự chạy song song: **{cfg['autopilot_parallel']}** (`AUTOPILOT_MAX_PARALLEL`) · tối đa "
                f"**{cfg['autopilot_max_scenes']}** cảnh / dự án tự chạy\n"
                f"- Job chạy cùng lúc mỗi dự án: **{cfg['per_project_running']}** ảnh + **{cfg['per_project_running']}** video\n"
                f"- Toàn máy (tự học): bắt đầu {cfg['throttle_start']}, +1 sau {cfg['throttle_up_every']} lần thành công, tối đa "
                f"{cfg['throttle_max']}, gặp giới hạn tốc độ thì giảm nửa — đang ở: ảnh **{cfg['learned']['image_gen']}**, video "
                f"**{cfg['learned']['video_gen']}**\n"
                f"- Trần nhà cung cấp: video ClipAI **{cfg['provider_caps']['video_gen'] or 'không'}** · ảnh Deepix "
                f"**{cfg['provider_caps']['image_gen'] or 'chưa đo'}**\n"
                "- Không còn trần lượt gửi chung mỗi ngày (S14.18): giới hạn theo NGƯỜI (2 dự án dở · 2 dự án mới/ngày · 1 dự án dở cất) "
                "và theo sản phẩm (tự gen lại ảnh ≤ 3 / video ≤ 2, trần job theo dự án)")
    m = capacity.measured(p.conn)
    st.markdown("**Số đo từ lịch sử job** — *chờ* = trong pipeline (cổng duyệt, ảnh shot trước, hàng đợi); *chạy* = nhà cung cấp "
                "xếp hàng + tạo (bỏ shot đi theo nhóm multi-shot và task nối lại)")
    rows = []
    for kind, label in capacity.KINDS.items():
        for model, x in m[kind]["models"].items():
            rows.append({"Loại": label, "Model": model, "n": x["n"], "Tin cậy": x["confidence"],
                         "Chờ trung vị (s)": x["wait_s"]["median"], "Chạy trung vị (s)": x["run_s"]["median"],
                         "Chạy P90 (s)": x["run_s"]["p90"], "Mẫu chạy": x["run_s"]["n"],
                         "s chạy / s clip": x["run_per_clip_s"]["median"], "Tỉ lệ lỗi": x["fail_rate"],
                         "Bị giới hạn tốc độ": x["rate_limited"], "Ngày gần nhất": x["last_day"]})
    if rows:
        data_table(rows, hide_index=True, width="stretch")
    else:
        st.caption("Chưa có job nào xong — chưa đủ dữ liệu.")
    st.caption(" · ".join(f"{label}: chạy cùng lúc cao nhất {m[k]['peak']}, cao nhất không bị giới hạn tốc độ {m[k]['peak_without_rate_limit']}"
                          for k, label in capacity.KINDS.items()))
    q = capacity.queue(p.conn)
    st.markdown("**Hàng đợi bây giờ:** " + " · ".join(f"{capacity.KINDS[k]} {v['running']} đang chạy / {v['queued']} chờ" for k, v in q.items()))
    secs = st.number_input("Ước tính cho video dài (giây)", 5, 600, 60, 5, key="limits_secs")
    e = capacity.estimate(p.conn, secs, m=m)
    if e["minutes"] is None:
        st.info(e["note"])
    else:
        st.success(f"Video {secs} s ≈ **{e['minutes']:g} phút** cho bước video (chậm: ~{e['minutes_p90']:g} phút) — {e['note']} "
                   f"· model {e['model']}, n = {e['n']} ({e['confidence']})")


def _own(p: Pipeline) -> Pipeline:
    """A dialog's buttons rerun only the dialog, in another thread than the one that made `p` (SQLite refuses to share a
    connection across threads): every dialog works on its own connection, as the same person."""
    fresh = C.scoped(Pipeline(connect(C.DB)))
    fresh.actor = p.actor
    return fresh


@st.dialog("📁 Kho tài nguyên", width="large", on_dismiss=lambda: close_dialog("dlg_assets"))
def _dialog_assets(p: Pipeline) -> None:
    p = _own(p)
    asset_library_panel(p)


@st.dialog("💵 Ngân sách thử", on_dismiss=lambda: close_dialog("dlg_budget"))
def _dialog_budget(p: Pipeline) -> None:
    """Hard spending limit of a test round (kế hoạch v3: ≤ $50): jobs that would pass it stay queued."""
    if not allowed("settings"):        # S14.7 (D1): the flag may be stale / crafted — the right is checked again when drawn
        st.error("Ngân sách thử chỉ dành cho Owner hoặc người có quyền “Cài đặt & bảng giá”. Nhờ Owner cấp quyền ở 👥 Nhóm.")
        return
    p = _own(p)
    from core import budget
    s = budget.status(p.conn)
    for service, h in (s.get("out_of_credit") or {}).items():        # Data Pack P5: a service said it is out of money
        st.error(f"**{service}** báo HẾT TIỀN lúc {h.get('at')} — mọi lượt gửi tới dịch vụ này đang dừng. ({str(h.get('message'))[:160]})")
        if st.button(f"Đã nạp tiền — mở lại {service}", key=f"reopen_{service}"):
            budget.reopen(p.conn, service)
            st.rerun()
    if s["enabled"]:
        st.markdown(f"**Đang bật** — tính từ {s['since']} (UTC): đã chi ≈ **\\${s['spent']:.2f} / \\${s['usd']:.0f}**, "
                    f"{s['images']}/{s['image_cap']} ảnh, {s['audios']}/{s['audio_cap']} âm thanh.")
        ui.progress_bar(min(s["spent"] / s["usd"], 1.0) if s["usd"] else 0.0, invert=True)
        if s["unknown"]:
            st.caption("Chưa có giá cho: " + ", ".join(s["unknown"]) + " (không tính vào tổng).")
    else:
        st.markdown("**Đang tắt** — không giới hạn chi (dùng cho làm video thật).")
    st.caption("Giá theo bảng giá (ước tính từ slide ClipAI, chưa đo thật; ảnh Deepix giá tạm). Nhà cung cấp giả lập không tính. Việc "
               "vượt trần chỉ CẢNH BÁO (vẫn gửi, có số liệu ở 📥 và thanh 💵); chỉ chặn khi nhà cung cấp hết tiền, dự án tạm dừng hoặc "
               "trần ngày của chạy tự động. Model/mức chưa có giá được ước tính dư (không tính là \\$0); âm thanh chưa có giá "
               "nên chỉ đếm lượt; dự án mới tự bật 🧪 Thử rẻ.")
    usd = st.number_input("Trần (USD)", 1.0, 1000.0, float(s["usd"]), 5.0, key="budget_usd")
    cap = st.number_input("Tối đa số ảnh Deepix (ảnh có giá tạm — cũng tính vào trần USD)", 0, 1000, int(s["image_cap"]), 10, key="budget_imgs")
    acap = st.number_input("Tối đa số âm thanh — giọng/nhạc/SFX (chưa có giá)", 0, 5000, int(s["audio_cap"]), 50, key="budget_audio")
    c1, c2 = st.columns(2)
    from dashboard.design.screens import money_days   # S14.2: the trial start opens a budget round (bars and round stay in step)
    if money_days.trial_start_button(p.conn, me(), usd, cap, acap, c1):
        st.rerun()
    if s["enabled"] and c2.button("■ Tắt giới hạn", key="budget_stop"):
        budget.stop(p.conn)
        st.rerun()
    if s["enabled"] and (usd != s["usd"] or cap != s["image_cap"] or acap != s["audio_cap"]) \
            and st.button("💾 Lưu trần mới (giữ mốc bắt đầu)", key="budget_save"):
        budget.save(p.conn, usd=float(usd), image_cap=int(cap), audio_cap=int(acap))
        st.rerun()
    st.divider()
    st.markdown(f"**🤖 Claude API** — đã dùng ≈ **\\${s['llm_spent']:.2f} / \\${s['llm_usd']:.2f}**"
                + (f" (tính từ {s['llm_since']} UTC)" if s["llm_since"] else "")
                + (" — **đã vượt mức dự tính (vẫn gọi, chỉ cảnh báo)**" if s["llm_usd"] > 0 and s["llm_left"] <= 0 else ""))
    ui.progress_bar(min(s["llm_spent"] / s["llm_usd"], 1.0) if s["llm_usd"] > 0 else 0.0, invert=True)
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
        from core import person_limits
        try:
            new = compare.clone_project(p, pid, name.strip(), mode, with_rows=rows)
        except person_limits.LimitReached as e:      # S14.18: a copy is a new project — same limits as ➕ Dự án mới
            limits_ui.remember(e, "clone")
        else:
            limits_ui.clear()
            st.success(f"Đã tạo dự án #{new} “{name.strip()}” — chọn ở ô Dự án trên cùng.")
    limits_ui.panel(p, "clone")


@st.dialog("💲 Bảng giá", on_dismiss=lambda: close_dialog("dlg_pricing"))
def _dialog_pricing() -> None:
    if not allowed("settings"):        # S14.7 (D1): same re-check as the budget dialog (a stale flag opens it for anyone)
        st.error("Bảng giá chỉ dành cho Owner hoặc người có quyền “Cài đặt & bảng giá”.")
        return
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


def account_section(p: Pipeline) -> None:
    """Who is signed in + sign-out (or, with sign-in off, the name jobs are counted for) — at the top of ⚙."""
    who = me()
    role = "Owner" if who["role"] == "owner" else "Thành viên"
    st.caption(f"👤 {escape(who['name'])} · {escape(who['email'])} · {role}"
               + ("" if auth_on() else (" · đăng nhập đang tắt" if ui.v2_on() else " · đăng nhập đang tắt (DASHBOARD_AUTH=off)")))
    if not auth_on():
        user_bar()
    if auth_on() and st.button("Đăng xuất", key="logout_btn"):
        auth.logout(p.conn, st.session_state.get("auth_token"))
        for key in ("auth_token", "identity", "login_tried"):
            st.session_state.pop(key, None)
        st.query_params.pop("login", None)
        st.query_params.pop("s", None)
        st.rerun()


def user_bar() -> str:
    """Who is using the dashboard (honour system, no password). Kept in the address (?user=Ten) so a refresh or a
    bookmark remembers it; every job created from this browser is counted for this name."""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = clean_name(st.query_params.get("user", ""))
    typed = clean_name(st.text_input("👤 Tên của bạn", value=st.session_state["user_name"], placeholder="ví dụ: Viet",
                                     key="user_input", help="Để hệ thống ghi nhận ai đã gen video. Không cần mật khẩu."))
    if typed != st.session_state["user_name"]:
        st.session_state["user_name"] = typed
        st.query_params["user"] = typed
    if not typed and ui.v2_on():
        st.markdown(colored("warn", "Nhập tên để lượt gen được ghi cho bạn."), unsafe_allow_html=True)
    elif not typed:
        st.markdown(colored("warn", "Nhập tên trước khi gen ảnh/video để lượt gen được ghi cho bạn (nếu để trống sẽ tính là “chưa nhập tên”)."), unsafe_allow_html=True)
    return typed


def user_name() -> str:
    """The name typed in ⚙ (sign-in off), read without drawing the box — the address remembers it (?user=Ten)."""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = clean_name(st.query_params.get("user", ""))
    return st.session_state["user_name"]




def global_bar(p: Pipeline):
    """ONE bar: brand · project · state · risk · pause/continue/cancel · new project · ⚙."""
    projects = archive.active_projects(p.conn, C.access_user())          # 📦 archived projects are hidden (restore them in ⚙)
    if ui.v2_on():
        return _global_bar_v2(p, projects)
    with st.container(border=True):
        c0, c1, c2, c3, c4, c5, c6, c7 = st.columns([1.2, 2.0, 1.0, 1.9, 1.2, 1.5, 1.2, 0.5], vertical_alignment="center")
        c0.markdown('<div class="brand"><i></i>AI Video Pipeline</div>', unsafe_allow_html=True)
        with c4:
            new_project_control(p)
        if not projects:
            with c5:
                inbox_card(p)
            with c6:
                money_card(p, None)
            with c7:
                settings_menu(p, None)
            put_away = len(archive.archived_projects(p.conn, C.access_user()))
            st.info("Chưa có dự án. Bấm “➕ Dự án mới” để bắt đầu."
                    + (f" ({put_away} dự án đã cất — mở ⚙ → “📦 Dự án đã cất” để khôi phục.)" if put_away else ""))
            return None
        ids = [r["id"] for r in projects]
        default_pid = current_pid(p)
        pid = c1.selectbox("Dự án", ids, index=ids.index(default_pid) if default_pid in ids else 0,
                           format_func=lambda i: next(r["name"] for r in projects if r["id"] == i), key="global_pid",
                           label_visibility="collapsed")
        proj = p.project(pid)
        with c2:
            risk_popover(p, pid)
            screen_feedback(p, pid)
        b1, b3 = c3.columns(2)              # kế hoạch V4 5.3: one pause / continue button
        access_ui.set_read_only(auth_on() and C.read_only(p, pid))       # "Chỉ xem": pause / continue / cancel are disabled
        if proj["paused"]:
            if b1.button("▶ Tiếp tục", key="btn_resume", type="primary"):
                p.set_paused(pid, False)
                st.rerun()
        elif b1.button("⏸ Tạm dừng", key="btn_pause"):
            p.set_paused(pid, True)
            st.rerun()
        if confirm_all("btn_cancel", [pid], "■ Hủy việc", "Hủy mọi ảnh/clip đang chờ hoặc đang gen của dự án này?", b3, "Có, hủy"):
            st.toast(cancel_everything(p, pid))
            st.rerun()
        access_ui.set_read_only(False)
        with c5:
            inbox_card(p)
        with c6:
            money_card(p, pid)
        with c7:
            settings_menu(p, pid)
    if proj["paused"]:
        st.warning("Dự án đang TẠM DỪNG — không ảnh/clip nào được gửi đi. Bấm ▶ Tiếp tục ở thanh trên.")
    if st.session_state.get("step") not in (C.STEPS[0], C.STEPS[5], C.STEPS[6]):
        level_bar(p, pid)                                # a per-project control: not on ⌂ / Nhóm / Theo dõi
    status_line(p, pid)
    return pid


def _global_bar_v2(p: Pipeline, projects):
    """UI v2 top bar (S13 nhánh B): glass bar · gradient brand · project picker · ➕ Dự án mới · 📥 Việc cần bạn · 💵 Tiền · ⋯ Thêm · ⚙ Cài đặt.
    Pause / cancel / risk moved into the labelled "⋯ Thêm" menu (▶ Tiếp tục stays in the bar while paused). The hero strip, the 🎚 level and
    the status line are drawn by app.py right under this bar (shell_parts.project_hero)."""
    brand = '<div class="shell-brand" title="AI Video Pipeline"><i></i><span class="v2-grad-text">AI Video Pipeline</span></div>'
    with st.container(key="shell-bar"):
        if not projects:
            c0, c4, c5, c6, c7 = st.columns([3, 1.6, 2, 1.6, 1.6], vertical_alignment="center")
            c0.html(brand)
            with c4:
                new_project_control(p)
            with c5:
                inbox_card(p)
            with c6:
                money_card(p, None)
            with c7:
                settings_menu(p, None, "⚙ Cài đặt")
            put_away = len(archive.archived_projects(p.conn, C.access_user()))
            st.info("Chưa có dự án. Bấm “➕ Dự án mới” để bắt đầu."
                    + (f" ({put_away} dự án đã cất — mở ⚙ → “📦 Dự án đã cất” để khôi phục.)" if put_away else ""))
            return None
        ids = [r["id"] for r in projects]
        default_pid = current_pid(p)
        paused = False
        pid_now = default_pid if default_pid in ids else ids[0]
        paused = bool(p.project(pid_now)["paused"])
        widths = [2.3, 2.6, 1.6, 2.0, 1.8] + ([1.4] if paused else []) + [1.2, 1.5]
        cols = st.columns(widths, vertical_alignment="center")
        c0, c1, c4, c5, c6 = cols[:5]
        c_more, c_gear = cols[-2], cols[-1]
        c0.html(brand)
        pid = c1.selectbox("Dự án", ids, index=ids.index(default_pid) if default_pid in ids else 0,
                           format_func=lambda i: next(r["name"] for r in projects if r["id"] == i), key="global_pid",
                           label_visibility="collapsed")
        proj = p.project(pid)
        with c4:
            new_project_control(p)
        with c5:
            inbox_card(p)
        with c6:
            money_card(p, pid)
        access_ui.set_read_only(auth_on() and C.read_only(p, pid))       # "Chỉ xem": pause / continue / cancel are disabled
        if proj["paused"]:
            if cols[5].button("▶ Tiếp tục", key="btn_resume", type="primary", width="stretch"):
                p.set_paused(pid, False)
                st.rerun()
        with c_more:
            with st.popover("⋯ Thêm", help="Tạm dừng / hủy việc đang chờ, ghi chú rủi ro", width="stretch"):
                if not proj["paused"] and st.button("⏸ Tạm dừng dự án", key="btn_pause", width="stretch"):
                    p.set_paused(pid, True)
                    st.rerun()
                if confirm_all("btn_cancel", [pid], "■ Hủy việc đang chờ / đang gen", "Hủy mọi ảnh/clip đang chờ hoặc đang gen của dự án này?",
                               st, "Có, hủy"):
                    st.toast(cancel_everything(p, pid))
                    st.rerun()
                risk_popover(p, pid)
                screen_feedback(p, pid)
        access_ui.set_read_only(False)
        with c_gear:
            settings_menu(p, pid, "⚙ Cài đặt")
    if proj["paused"]:
        st.warning("Dự án đang TẠM DỪNG — không gửi ảnh/clip nào. Bấm ▶ Tiếp tục ở thanh trên.")
    return pid


def status_line(p: Pipeline, pid: int) -> None:
    """Kế hoạch V4 5.3: spending, the automatic run and the problems of this project in ONE line under the bar."""
    if ui.v2_on():
        return _status_line_v2(p, pid)
    bits = [] if auth_on() or user_name() else ["👤 chưa nhập tên (⚙)"]   # the name box moved into ⚙: say when it is empty
    spend = C.spend_text(p, pid)
    if spend:
        bits.append("💵 " + spend)
    proj = p.project(pid) if pid is not None else None
    if proj is not None and "test_quality" in proj.keys() and proj["test_quality"]:
        bits.append("🧪 Thử rẻ: ảnh cỡ nhỏ nhất · video 720p / Kling std / Seedance Fast")
    broken = cost.load_pricing().get("_error")
    if broken:                                          # luật 1: a broken price table stops every paid send — say it everywhere
        bits.append(f"🔴 {escape(broken)} — mọi job trả tiền bị chặn")
    try:                                                # what the four overview cards used to say, in the same one line
        from dashboard import overview
        c = overview._counts(p, pid)
        if c["queue"]:
            bits.append(f"hàng đợi: {c['queue'].get('image_gen', 0)} ảnh, {c['queue'].get('video_gen', 0)} clip")
        plates = overview._plates(pid)
        if plates:
            bits.append(plates)
    except Exception:  # noqa: BLE001 - a status bit only
        pass
    ap = autopilot.status(p, pid)
    if ap["state"] in ("running", "queued", "waiting"):
        bits.append(f"🚀 Tự động: {ap['note']}")
    problems = [f for f in C.diag_problems(p) if f.get("project_id") in (None, pid)]
    if problems:
        bits.append(f"🔴 {len(problems)} vấn đề (vd: {escape(diag.redact(problems[0]['title']))}) — tab “📊 Theo dõi”")
    budget = _budget_bit(p, pid)
    if budget:
        bits.append(budget)
    if bits:
        st.caption("  ·  ".join(bits))
    stale = code_changed_since_start()
    if stale:                                           # S6.4: #8 ran for hours on code older than the fixes on disk
        st.warning(f"⚠ Code đã đổi sau khi Dashboard khởi động ({stale}) — tắt / mở lại Dashboard để dùng bản mới "
                   "(các việc đang chạy vẫn dùng code cũ tới lúc đó).")


def _status_line_v2(p: Pipeline, pid: int) -> None:
    """UI v2 status line (người dùng 01/10): ONE short line of what needs a glance (P1/P2) + a ⓘ holding every detail the old line listed.
    Outside: spend count, queue size, the automatic run's state, number of problems, a low budget, a missing name. Inside ⓘ: all of it in full
    (spend with price, queue split, plates, the run's note, the problems' titles, the locked budget, the cheap-test note)."""
    from dashboard.design import components as D
    short, full = [], []                                # short = visible; full = markdown bullets for ⓘ
    if not (auth_on() or user_name()):
        short.append("👤 chưa nhập tên (⚙)")
        full.append("👤 chưa nhập tên (⚙)")
    spend = C.spend_text(p, pid)
    if spend:
        sp = cost.spend_summary(p.conn, pid, cost.load_pricing())
        short.append("💵 giả lập" if sp["mock"] and sp["mock"] == sp["events"] else f"💵 {sp['images']} ảnh · {sp['clips']} clip")
        full.append("💵 " + spend)
    proj = p.project(pid) if pid is not None else None
    if proj is not None and "test_quality" in proj.keys() and proj["test_quality"]:
        short.append("🧪 Thử rẻ")
        full.append("🧪 Thử rẻ: ảnh cỡ nhỏ nhất · video 720p / Kling std / Seedance Fast")
    blocker = ""
    broken = cost.load_pricing().get("_error")
    if broken:                                          # luật 1: a broken price table stops every paid send — P1, stays outside
        blocker = "🔴 Bảng giá lỗi — mọi job trả tiền bị chặn"
        full.append(f"🔴 {broken} — mọi job trả tiền bị chặn")
    try:
        from dashboard import overview
        c = overview._counts(p, pid)
        if c["queue"]:
            n_img, n_vid = c["queue"].get("image_gen", 0), c["queue"].get("video_gen", 0)
            short.append(f"hàng đợi {n_img + n_vid}")
            full.append(f"Hàng đợi: {n_img} ảnh, {n_vid} clip")
        plates = overview._plates(pid)
        if plates:
            full.append(plates)
    except Exception:  # noqa: BLE001 - a status bit only
        pass
    ap = autopilot.status(p, pid)
    if ap["state"] in ("running", "queued", "waiting"):
        short.append("🚀 Tự động " + {"running": "đang chạy", "queued": "xếp hàng", "waiting": "chờ bạn"}[ap["state"]])
        full.append(f"🚀 Tự động: {ap['note']}")
    problems = [f for f in C.diag_problems(p) if f.get("project_id") in (None, pid)]
    if problems:
        short.append(f"🔴 {len(problems)} vấn đề")
        full.append(f"🔴 {len(problems)} vấn đề — xem tab “📊 Theo dõi”:")
        full.extend(f"    - {diag.redact(x['title'])}" for x in problems[:8])
    budget = _budget_bit(p, pid)
    if budget:
        full.append(budget)
        low = _budget_left_frac(p, pid)
        if low is not None and low <= 0.2:              # money about to run out is P1
            short.append("🔒 ngân sách sắp hết")
    if blocker:
        st.error(blocker)
    if short or full:
        text = "  ·  ".join(escape(x) for x in short) or "Chi tiết"
        D.line(f'<span class="shell-status">{text}</span>', "\n".join(f"- {x}" if not x.startswith("    ") else x for x in full), "shell-status")
    stale = code_changed_since_start()
    if stale:                                           # S6.4: #8 ran for hours on code older than the fixes on disk
        D.note("warning", f"Code đã đổi sau khi Dashboard khởi động (`{stale}`) — tắt / mở lại Dashboard để dùng bản mới "
               "(các việc đang chạy vẫn dùng code cũ tới lúc đó).", "⚠ Code đã đổi sau khi Dashboard khởi động — tắt / mở lại để dùng bản mới.", "shell-stale", attention=True)


def _budget_left_frac(p: Pipeline, pid) -> "float | None":
    """Share of the locked project budget still left (None when there is none)."""
    try:
        from core import project_budget
        if pid is None or not project_budget.enabled():
            return None
        data = project_budget.get(p.conn, pid) or {}
        cap = float(data.get("total") or 0)
        if not data.get("locked") or cap <= 0:
            return None
        return max(cap - sum(project_budget.spent_by_stage(p.conn, pid).values()), 0.0) / cap
    except Exception:  # noqa: BLE001
        return None


_STARTED = __import__("time").time()


def code_changed_since_start() -> str:
    """S6.4: the newest core/ or dashboard/ file changed after this process started ('' when none) — Streamlit keeps the modules it
    imported, so a fix pulled from git does nothing until a restart."""
    import glob
    import os
    root = os.path.join(os.path.dirname(__file__), "..")
    newest, name = 0.0, ""
    for pattern in ("core/*.py", "core/adapters/*.py", "dashboard/*.py", "dashboard/steps/*.py"):
        for f in glob.glob(os.path.join(root, pattern)):
            try:
                t = os.path.getmtime(f)
            except OSError:
                continue
            if t > newest:
                newest, name = t, os.path.relpath(f, root).replace("\\", "/")
    return name if newest > _STARTED + 5 else ""


def _budget_bit(p: Pipeline, pid) -> str:
    """S6.4: the project's locked budget as used / cap / left, in the status line (it was only inside the Kịch bản screen)."""
    if pid is None:
        return ""
    try:
        from core import project_budget
        if not project_budget.enabled():
            return ""
        data = project_budget.get(p.conn, pid) or {}
        if not data.get("locked"):
            return ""
        spent = sum(project_budget.spent_by_stage(p.conn, pid).values())
        cap = float(data.get("total") or 0)
        return f"🔒 Ngân sách: đã dùng {spent:.2f} / trần {cap:.2f} USD (còn {max(cap - spent, 0):.2f})"
    except Exception:  # noqa: BLE001 - a status bit only
        return ""



def _create_project(p: Pipeline) -> None:
    """Button callback (runs before the widgets, so it may still select the new project in the picker)."""
    name = (st.session_state.get("new_name") or "").strip()
    if not name:
        return
    p = C.scoped(Pipeline(connect(C.DB)))                     # a callback runs in another thread than the one that made `p`
    from core import person_limits
    try:
        pid = p.create_project(name, created_by=me()["email"], aspect=st.session_state.get("new_aspect"),
                               genre=st.session_state.get("new_genre"), model_priority=st.session_state.get("new_prio"),
                               game=st.session_state.get("new_game"))
    except person_limits.LimitReached as e:                   # S14.18: said with its numbers + GIỮ / BỎ or the request to the Owner
        limits_ui.remember(e, "create")
        return
    limits_ui.clear()
    qc_policy.apply(p, pid, "balanced")
    from core import project_defaults             # S3.8: start from the way of working settled in the latest project
    copied = project_defaults.inherit(p.conn, pid, me()["email"])
    if copied:
        st.session_state["inherited_note"] = "Dự án mới kế thừa từ dự án gần nhất của bạn: " + ", ".join(copied)
    st.session_state["global_pid"] = pid
    st.session_state["new_name"] = ""
