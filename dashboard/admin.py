"""Settings / monitoring panels: knowledge base, asset library, users, pricing, monitor, lessons, history."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C



def distill_panel(group: str, ov: dict) -> None:
    """Read all documents ONCE, keep a short playbook split by topic; the step then reads the playbook only."""
    st.markdown("**🧪 Chắt lọc thành cẩm nang ngắn**")
    st.caption("Claude đọc và phân tích toàn bộ tài liệu một lần, tổng kết thành cẩm nang ngắn chia rõ theo từng mảng nội dung "
               "(" + " · ".join(knowledge.DISTILL_SECTIONS[group][:5]) + " …). Sau đó bước này chỉ đọc cẩm nang, "
               "không đọc lại từng tài liệu.")
    d = ov["distilled"]
    include = st.checkbox("Gồm cả tài liệu kiến thức có sẵn (giảm thêm token mỗi lần chạy)",
                          bool(d.get("include_builtin")) if d["exists"] else False, key=f"kb_inc_{group}")
    inputs = knowledge.distill_inputs(group, include)
    src = sum(len(t) for _, t in inputs)
    st.caption(f"Nguồn để chắt lọc: {len(inputs)} tài liệu · {src:,} ký tự (≈ {knowledge.approx_tokens(src):,} token, chỉ đọc "
               f"một lần khi chắt lọc). Cẩm nang mục tiêu ≈ {knowledge.TARGET_CHARS[group]:,} ký tự.")
    if not d["exists"]:
        st.info("Chưa có cẩm nang: mỗi lần chạy bước này vẫn gửi nguyên các tài liệu.")
    elif d["active"]:
        st.success(f"Đang dùng cẩm nang ({d['chars']:,} ký tự ≈ {d['tokens']:,} token, tạo {d['created_at']}) thay cho "
                   f"≈ {ov['raw_tokens']:,} token tài liệu gốc.")
    elif not d["fresh"]:
        st.warning("Tài liệu đã thay đổi sau lần chắt lọc → cẩm nang đã cũ, tạm thời bước này dùng lại tài liệu gốc. "
                   "Hãy chắt lọc lại.")
    else:
        st.info("Cẩm nang đang TẮT: bước này dùng tài liệu gốc.")
    client = llm_client()
    if client is not None and inputs:
        if st.button(f"🤖 Chắt lọc bằng {llm_label(client)}", type="primary", key=f"kb_distill_{group}"):
            with st.spinner("Claude đang đọc và tổng kết tài liệu…"):
                ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_distill(group, client, include)))
            if ok:
                r = st.session_state.pop("llm_res")
                st.toast(f"Cẩm nang {r['chars']:,} ký tự từ {r['source_chars']:,} ký tự ({tokens_text(r)})")
                st.rerun()
    with st.expander("✍ Chắt lọc tay: prompt gửi Claude + dán cẩm nang"):
        if inputs:
            st.code(knowledge.build_distill_bundle(group, include), language="markdown")
        else:
            st.caption("Chưa có tài liệu để chắt lọc.")
        raw = st.text_area("Dán cẩm nang Claude trả về (Markdown, các mục `## `)", key=f"kb_paste_{group}", height=140)
        if st.button("Lưu cẩm nang", disabled=not raw.strip(), key=f"kb_save_{group}"):
            if act(lambda: knowledge.store_distilled(group, raw, include), "Đã lưu cẩm nang"):
                st.rerun()
    if d["exists"]:
        with st.expander("📘 Xem / sửa cẩm nang"):
            use = st.checkbox("Dùng cẩm nang thay cho tài liệu gốc", d["use"], key=f"kb_use_{group}")
            if use != d["use"]:
                knowledge.set_use_distilled(group, use)
                st.rerun()
            st.caption("Nguồn: " + ", ".join(d["sources"]))
            edited = st.text_area("Nội dung (sửa được)", d["text"], key=f"kb_edit_{group}", height=260)
            if st.button("Lưu chỉnh sửa", key=f"kb_edit_save_{group}", disabled=edited == d["text"]):
                if act(lambda: knowledge.store_distilled(group, edited, d["include_builtin"], d["use"]), "Đã lưu"):
                    st.rerun()
            if confirm_all(f"kb_dclear_{group}", ["x"], "🗑 Xóa cẩm nang", "Xóa cẩm nang (tài liệu gốc vẫn còn)?", st,
                           "Có, xóa"):
                knowledge.clear_distilled(group)
                st.rerun()


def knowledge_panel() -> None:
    """Where the Claude steps get their skills from: what ships with the project, what the user added, and a way to
    add more (documents are appended to that step's prompt while switched on)."""
    keys = list(knowledge.GROUPS)
    group = st.selectbox("Bước dùng Claude", keys, format_func=lambda k: knowledge.GROUPS[k][0], key="kb_group")
    _, purpose, _ = knowledge.GROUPS[group]
    ov = knowledge.overview(group)
    st.caption(purpose)
    m1, m2, m3 = st.columns(3)
    m1.metric("Tài liệu đang bật", sum(1 for d in ov["docs"] if d["enabled"]))
    m2.metric("Ký tự gửi Claude mỗi lần chạy", f"{ov['chars']:,}")
    m3.metric("≈ token mỗi lần chạy", f"{ov['tokens']:,}")
    st.caption(f"📁 Có sẵn (cùng mã nguồn, có trong git): `{ov['builtin_dir']}` và thư mục `prompts/`  ·  "
               f"📁 Bạn thêm (ngoài git): `{ov['user_dir']}`")
    if ov["tokens"] > 25_000:
        st.warning("Lượng tài liệu khá lớn: mỗi lần chạy bước này sẽ gửi ≈ %s token. Tắt bớt tài liệu ít dùng để tiết kiệm." % f"{ov['tokens']:,}")
    data_table([{"Tên": d["title"], "Nguồn": "có sẵn" if d["source"] == "builtin" else "bạn thêm",
                   "Ghi chú": d["note"], "Ký tự": d["chars"], "≈ token": knowledge.approx_tokens(d["chars"]),
                   "Bật": "✓" if d["enabled"] else "—",
                   "Cẩm nang thay thế": "✓" if d.get("replaced") else ""} for d in ov["docs"]],
                 width="stretch", hide_index=True, height=min(38 * (len(ov["docs"]) + 1) + 3, 260))
    distill_panel(group, ov)
    for d in ov["docs"]:
        tag = "" if d["source"] == "builtin" else " · bạn thêm"
        with st.expander(f"📄 {d['title']}{tag}"):
            text = knowledge.read_doc(group, d["source"], d["file"])
            ui.html('<div class="scriptfull">' + escape(text[:6000]) + ("\n…" if len(text) > 6000 else "") + "</div>")
            st.caption(f"{d['chars']:,} ký tự · {d['path']}")
            if d["source"] == "user":
                on = st.checkbox("Bật (gửi kèm mỗi lần chạy)", d["enabled"], key=f"kb_en_{group}_{d['file']}")
                if on != d["enabled"]:
                    knowledge.set_enabled(group, d["file"], on)
                    st.rerun()
                if confirm_all(f"kb_del_{group}_{d['file']}", [d["file"]], "🗑 Xóa tài liệu này",
                               f"Xóa “{d['title']}” khỏi kho?", st, "Có, xóa"):
                    if act(lambda: knowledge.remove_doc(group, d["file"]), "Đã xóa tài liệu"):
                        st.rerun()
            else:
                st.caption("Tài liệu có sẵn chỉ sửa được trong mã nguồn (thư mục knowledge/ và prompts/).")
    st.markdown("**➕ Thêm tài liệu để nâng cấp kho**")
    st.caption(f"File .md, .txt hoặc .docx; mỗi file tối đa {knowledge.MAX_DOC_CHARS:,} ký tự, tổng bổ sung tối đa "
               f"{knowledge.MAX_USER_CHARS:,} ký tự cho mỗi bước. Ví dụ: hướng dẫn phong cách của studio, kịch bản mẫu và "
               "kết quả bạn hài lòng, danh sách lỗi hay gặp.")
    up = st.file_uploader("Tài liệu", type=["md", "txt", "docx"], key=f"kb_up_{group}", label_visibility="collapsed")
    k1, k2 = st.columns(2)
    title = k1.text_input("Tên hiển thị (tùy chọn)", key=f"kb_title_{group}")
    note = k2.text_input("Ghi chú (tùy chọn)", key=f"kb_note_{group}")
    if st.button("⬆ Thêm vào kho", disabled=up is None, key=f"kb_add_{group}", type="primary"):
        if act(lambda: knowledge.add_doc(group, up.name, up.getvalue(), title, note), "Đã thêm tài liệu"):
            st.rerun()


def users_tab(p: Pipeline, pid: int) -> None:
    """Owner only: the permission table."""
    conn = p.conn
    actor = auth.Identity(me()["email"], me()["name"], me()["role"], me().get("perms", []))
    ui.html(ui.card_title("👥 Bảng phân quyền", "nhập e-mail và tick những gì người đó được dùng"))
    st.caption("Mọi người đều có các bước làm video (kể cả chế độ tự động). Ở đây bạn cấp thêm: cài đặt & bảng giá, kho kiến thức, theo dõi "
               "hiệu suất, bài học. Quản lý người dùng và tắt Dashboard chỉ dành cho Owner.")
    people = [u for u in auth.list_users(conn) if u["role"] != "owner"]
    st.markdown(f"**Owner:** {escape(auth.OWNER_EMAIL)} — toàn quyền, không ai đổi được.")
    perm_cols = list(auth.PERM_LABELS.items())
    if people:
        table = [{"E-mail": u["email"], "Được vào": u["active"],
                  **{label: key in u["perms"] for key, label in perm_cols},
                  "Đăng nhập gần nhất": u["last_login"] or "-"} for u in people]
        edited = st.data_editor(table, hide_index=True, width="stretch", key="perm_table",
                                disabled=["E-mail", "Đăng nhập gần nhất"])
        if st.button("💾 Lưu bảng phân quyền", key="perm_save", type="primary"):
            try:
                rows = [{"email": r["E-mail"], "active": bool(r["Được vào"]),
                         "perms": [key for key, label in perm_cols if r[label]]} for r in edited.to_dict("records")
                        ] if hasattr(edited, "to_dict") else [
                    {"email": r["E-mail"], "active": bool(r["Được vào"]), "perms": [k for k, l in perm_cols if r[l]]} for r in edited]
                changed = auth.apply_table(conn, actor, rows)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.success(f"Đã lưu ({changed} thay đổi). Có hiệu lực ngay, kể cả với người đang đăng nhập.")
    else:
        st.caption("Chưa có ai khác trong bảng. Người dùng e-mail công ty tự vào được ở quyền cơ bản (xem mục tên miền bên dưới).")
    with st.container(border=True):
        st.markdown("**Thêm e-mail**")
        c1, c2, c3 = st.columns([3, 3, 1.4], vertical_alignment="bottom")
        new_email = c1.text_input("E-mail", key="add_email", placeholder="ten@garena.vn")
        new_perms = c2.multiselect("Quyền thêm", list(auth.PERM_LABELS), format_func=lambda k: auth.PERM_LABELS[k], key="add_perms")
        if c3.button("Thêm", key="add_go", type="primary"):
            try:
                auth.add_user(conn, actor, new_email, new_perms)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.rerun()
    if people:
        with st.container(border=True):
            st.markdown("**Xóa khỏi bảng**")
            gone = st.selectbox("E-mail", [u["email"] for u in people], key="rm_email")
            if confirm_all("rm_user", [gone], "Xóa khỏi bảng", f"Xóa {gone}? (nếu là e-mail công ty, họ vẫn tự vào lại được ở quyền cơ bản)", st,
                           "Có, xóa"):
                try:
                    auth.remove_user(conn, actor, gone)
                except auth.AuthError as e:
                    st.error(str(e))
                else:
                    st.rerun()
    with st.container(border=True):
        st.markdown("**Ai tự vào được (quyền cơ bản)**")
        domains = st.text_input("Tên miền e-mail được tự vào làm Thành viên (cách nhau bằng dấu phẩy; để trống = chỉ e-mail trong bảng)",
                                ", ".join(auth.auto_domains(conn)), key="auto_domains")
        if st.button("Lưu tên miền", key="auto_domains_save"):
            try:
                auth.set_auto_domains(conn, actor, domains)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.success("Đã lưu")
        st.caption(f"Địa chỉ đưa cho người khác: {lan_address()}")
    st.markdown(colored("warn", "Không có mật khẩu: ai mở được Dashboard và gõ đúng e-mail của một người thì vào như người đó, kể cả Owner. "
                        "Chỉ dùng trong mạng tin cậy. Muốn Owner chỉ đăng nhập từ máy chạy Dashboard, đặt DASHBOARD_OWNER_LOCAL_ONLY=1."), unsafe_allow_html=True)
    with st.expander("Nhật ký (đăng nhập, thay đổi quyền)"):
        data_table([{"Lúc": r["at"], "Ai": r["email"] or "", "Việc": r["action"], "Chi tiết": r["detail"] or ""}
                      for r in auth.recent_audit(conn)], hide_index=True, use_container_width=True)


def _role_options(kind: str) -> dict:
    return {"": "— chưa rõ —", **assets.ROLES.get(kind, {})}


def _fresh(p: Pipeline) -> Pipeline:
    """A fragment redraws alone, in another thread than the run that made `p` (SQLite refuses to share a connection across threads): every
    library box works on its own connection, as the same person."""
    fresh = C.scoped(Pipeline(connect(C.DB)))
    fresh.actor = p.actor
    return fresh


REVIEW_PAGE = 24


def _rerun_here() -> None:
    """Redraw only the fragment the click came from; a full-script run (no fragment to scope to) redraws everything."""
    from streamlit.errors import StreamlitAPIException
    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def _rv_all(ids: list, on: bool) -> None:
    for i in ids:
        st.session_state[f"lib_rev_pick_{i}"] = on


@st.fragment
def library_review_box(p: Pipeline, game: str) -> None:
    """G2: pictures that came in without a person looking (folder sync, website, 3D render) wait here; the pipeline only uses approved
    ones. The role is guessed for free from the picture's shape — correct it when it is wrong.
    A fragment: every click here redraws only this box (not the whole library page); pick many pictures to approve / drop at once."""
    p = _fresh(p)
    waiting = assets.pending_images(p.conn, game)
    if not waiting:
        return
    shown = waiting[:max(REVIEW_PAGE, st.session_state.get(f"lib_rev_n_{game}", REVIEW_PAGE))]
    shown_ids = [w["id"] for w in shown]
    picked = [i for i in shown_ids if st.session_state.get(f"lib_rev_pick_{i}")]
    looks = {"": "— look —", **assets.LOOKS}

    def row_meta(w: dict) -> tuple:                     # what the person set on this row (or the suggestion)
        return (st.session_state.get(f"lib_rev_role_{w['id']}", w["role"] or ""), st.session_state.get(f"lib_rev_look_{w['id']}", w["look"] or ""))

    done = _rerun_here

    # the label stays the same while the count changes: a changed label makes Streamlit build the expander again, closed — after every click
    st.caption(f"📥 {len(waiting)} ảnh chờ duyệt")
    with st.expander("📥 Ảnh chờ duyệt — pipeline chưa dùng các ảnh này", expanded=False):
        st.caption("Tick các ảnh rồi duyệt / bỏ một lượt (bấm trong hộp này không tải lại cả trang). Chọn đúng vai trò (toàn thân / nửa người / cận mặt / "
                   "sau lưng…; bối cảnh: nền ngang tầm mắt / góc cao / toàn cảnh từ trên) và look — shot cận lấy ảnh cận mặt, shot quay lưng lấy ảnh sau lưng, "
                   "ảnh bản đồ chụp từ trên cao không bao giờ làm nền.")
        t1, t2, t3, t4, t5 = st.columns([1.2, 1.2, 2, 2, 2], vertical_alignment="center")
        t1.button("☑ Chọn hết", key=f"lib_rev_selall_{game}", on_click=_rv_all, args=(shown_ids, True))
        t2.button("☐ Bỏ chọn", key=f"lib_rev_selnone_{game}", on_click=_rv_all, args=(shown_ids, False))
        if t3.button(f"✔ Duyệt {len(picked)} ảnh đã chọn", key=f"lib_rev_okpick_{game}", disabled=not picked, type="primary"):
            for w in shown:
                if w["id"] in picked:
                    role, look = row_meta(w)
                    assets.set_image_meta(p.conn, w["id"], role=role, look=look, status="approved")
            done()
        if t4.button(f"✔ Duyệt cả {len(waiting)} ảnh (giữ vai trò)", key=f"lib_rev_all_{game}"):
            for w in waiting:
                role, look = row_meta(w)
                assets.set_image_meta(p.conn, w["id"], role=role, look=look, status="approved")
            done()
        ask = f"lib_rev_ask_{game}"
        if st.session_state.get(ask) and picked:
            st.warning(f"Bỏ {len(picked)} ảnh đã chọn? File ảnh sẽ bị xóa khỏi kho.")
            y, n = st.columns(2)
            if y.button("Có, bỏ", key=f"lib_rev_rmyes_{game}", type="primary"):
                for i in picked:
                    assets.remove_image(p.conn, i)
                    st.session_state.pop(f"lib_rev_pick_{i}", None)
                st.session_state[ask] = False
                done()
            if n.button("Không", key=f"lib_rev_rmno_{game}"):
                st.session_state[ask] = False
                done()
        elif t5.button(f"🗑 Bỏ {len(picked)} ảnh đã chọn", key=f"lib_rev_rmpick_{game}", disabled=not picked):
            st.session_state[ask] = True
            done()
        for w in shown:
            c_pick, c0, c1, c2, c3, c4 = st.columns([0.45, 1, 1.8, 1.6, 1.2, 1.4], vertical_alignment="center")
            c_pick.checkbox("Chọn", key=f"lib_rev_pick_{w['id']}", label_visibility="collapsed")
            try:
                c0.image(assets.thumbnail(w["path"]), width=90)
            except Exception:  # noqa: BLE001 - a broken file must not break the page
                c0.caption("(không đọc được ảnh)")
            c1.markdown(f"**{escape(w['asset'])}**")
            opts = _role_options(w["kind"])
            c2.selectbox("Vai trò", list(opts), index=list(opts).index(w["role"] or "") if (w["role"] or "") in opts else 0, format_func=opts.get,
                         key=f"lib_rev_role_{w['id']}", label_visibility="collapsed")
            c3.selectbox("Look", list(looks), index=list(looks).index(w["look"] or "") if (w["look"] or "") in looks else 0, format_func=looks.get,
                         key=f"lib_rev_look_{w['id']}", label_visibility="collapsed")
            a, b = c4.columns(2)
            if a.button("✔", key=f"lib_rev_ok_{w['id']}", help="Duyệt ảnh này"):
                role, look = row_meta(w)
                assets.set_image_meta(p.conn, w["id"], role=role, look=look, status="approved")
                done()
            if b.button("🗑", key=f"lib_rev_rm_{w['id']}", help="Bỏ ảnh này"):
                assets.remove_image(p.conn, w["id"])
                st.session_state.pop(f"lib_rev_pick_{w['id']}", None)
                done()
        if len(waiting) > len(shown):
            more = len(waiting) - len(shown)
            if st.button(f"… còn {more} ảnh — hiện thêm {min(more, REVIEW_PAGE)}", key=f"lib_rev_more_{game}"):
                st.session_state[f"lib_rev_n_{game}"] = len(shown) + REVIEW_PAGE
                done()


@st.fragment
def library_lost_box(p: Pipeline) -> None:
    p = _fresh(p)
    lost = assets.missing_files_detail(p.conn)
    if lost:                                    # B5 01/10: files gone from disk — fix on screen (reload from the source, or drop the link)
        st.caption(f"⚠ {len(lost)} ảnh trong Kho mất file")
        with st.expander("⚠ Ảnh trong Kho mất file", expanded=False):
            for w in lost[:30]:
                a1, a2, a3 = st.columns([4, 1.4, 1.4], vertical_alignment="center")
                a1.markdown(f"**{escape(w['asset'])}** · `{w['path']}`" + ("" if w["can_reload"] else " · nguồn không còn"))
                if a2.button("↻ Tải lại", key=f"lib_lost_reload_{w['id']}", disabled=not w["can_reload"],
                             help="Chép lại từ tệp gốc đã nhập"):
                    assets.reload_image(p.conn, w["id"])
                    _rerun_here()
                if a3.button("🔗 Gỡ liên kết", key=f"lib_lost_rm_{w['id']}", help="Xóa dòng hỏng khỏi Kho (file đã mất)"):
                    assets.remove_image(p.conn, w["id"])
                    _rerun_here()
            if st.button("🔗 Gỡ liên kết TẤT CẢ ảnh mất file", key="lib_lost_rm_all"):
                assets.unlink_missing(p.conn)
                _rerun_here()


def library_health(p: Pipeline, game: str) -> None:
    """G6: what the library still lacks, so a project is not started on a character without a close-up or a place without an
    eye-level background."""
    rows = [r for r in assets.health(p.conn, game) if r["missing"] or r["pending"] or r["unlabelled"]]
    if not rows:
        return
    with st.expander(f"🩺 Sức khỏe kho — {len(rows)} mục còn thiếu", expanded=False):
        data_table([{"Mục": r["name"], "Loại": r["kind"], "Ảnh đã duyệt": r["approved"], "Chờ duyệt": r["pending"],
                       "Chưa rõ vai trò": r["unlabelled"], "Còn thiếu": ", ".join(r["missing"])} for r in rows],
                     hide_index=True, use_container_width=True)


def profile_form(p: Pipeline, a: dict) -> None:
    """T1: the character's standard profile, approved once here and inherited by every project (the Director may not rewrite it)."""
    prof = assets.get_profile(p.conn, a["id"])
    label = "📋 Hồ sơ chuẩn" + (" · ✔ đã duyệt" if prof.get("approved") else " · chưa có" if not prof else " · nháp")
    if not st.checkbox(label, key=f"prof_open_{a['id']}"):
        return
    locks = p.conn.execute("SELECT pr.name AS project, c.lock_rules, c.description FROM characters c JOIN projects pr ON pr.id=c.project_id"
                           " WHERE c.lock_rules IS NOT NULL AND (c.ref_asset_id=? OR lower(c.name)=lower(?)) ORDER BY c.id DESC LIMIT 5",
                           (a["id"], a["name"])).fetchall()
    if locks and not prof:
        pick = st.selectbox("Lấy nháp từ Lock của dự án", range(len(locks)), format_func=lambda i: locks[i]["project"], key=f"prof_src_{a['id']}")
        if st.button("↧ Dùng làm nháp", key=f"prof_seed_{a['id']}"):
            seed = json.loads(locks[pick]["lock_rules"] or "{}")
            assets.set_profile(p.conn, a["id"], dict(seed, identity=(locks[pick]["description"] or "")[:300]), approved=False)
            st.rerun()
    identity = st.text_area("Nhận diện (mô tả ngắn, tiếng Anh cho model)", prof.get("identity", ""), key=f"prof_id_{a['id']}", height=60)
    keep = st.text_area("Luôn giữ (mặt, tóc, màu trang phục, phụ kiện)", prof.get("must_keep", ""), key=f"prof_keep_{a['id']}", height=60)
    may = st.text_input("Được đổi (tư thế, biểu cảm…)", prof.get("may_change", ""), key=f"prof_may_{a['id']}")
    forbid = st.text_input("Cấm lệch", prof.get("forbidden", ""), key=f"prof_forbid_{a['id']}")
    c1, c2 = st.columns(2)
    height = c1.number_input("Chiều cao thật (m)", 0.0, 30.0, float(prof.get("height_m") or 0), 0.01, key=f"prof_h_{a['id']}",
                             help="Để model vẽ đúng tỉ lệ với người khác và với bối cảnh (0 = chưa biết)")
    build = c2.text_input("Vóc dáng", prof.get("build", ""), key=f"prof_build_{a['id']}")
    ok = st.checkbox("✔ Duyệt — mọi dự án dùng hồ sơ này (thắng Lock của từng dự án)", bool(prof.get("approved")), key=f"prof_ok_{a['id']}")
    if st.button("💾 Lưu hồ sơ chuẩn", key=f"prof_save_{a['id']}"):
        assets.set_profile(p.conn, a["id"], {"identity": identity, "must_keep": keep, "may_change": may, "forbidden": forbid,
                                             "height_m": height, "build": build}, approved=ok)
        st.rerun()


@st.fragment
def plates3d_panel(p: Pipeline, game: str) -> None:
    """🏗 3D place -> empty eye-level / low / high backgrounds rendered by Blender on this computer (no AI, no credit), into the review
    box. How to test: docs/HUONG_DAN_3D.md."""
    p = _fresh(p)
    from core import plates3d
    with st.expander("🏗 Bối cảnh 3D — render nền trống người từ file 3D (Blender, không tốn credit)", expanded=False):
        blender = plates3d.find_blender()
        st.caption(("Blender: `" + blender + "`") if blender else "⚠ Chưa thấy Blender — cài Blender 5.0 hoặc đặt BLENDER_PATH trong dashboard.env.")
        folder = st.text_input("Thư mục file 3D (MODEL3D_DIR)", plates3d.model_dir(), key="p3d_dir")
        found = plates3d.models(folder)
        if not found:
            st.caption("Không thấy file .glb/.gltf/.fbx/.obj/.blend/.usd trong thư mục này. File 3D để trên máy, không đưa lên GitHub.")
            return
        pick = st.selectbox("File 3D", range(len(found)), format_func=lambda i: f"{found[i]['name']} · {found[i]['size_mb']} MB", key="p3d_file")
        model = found[pick]["path"]
        c1, c2 = st.columns(2)
        place = c1.text_input("Tên bối cảnh trong Kho", os.path.splitext(os.path.basename(model))[0], key="p3d_place")
        look = c2.selectbox("Look", ["ingame", "anime"], format_func=assets.LOOKS.get, key="p3d_look")
        sky = st.radio("Bầu trời", list(plates3d.SKIES), format_func=plates3d.SKIES.get, key="p3d_sky")
        c1, c2, c3 = st.columns(3)
        elev = c1.slider("Độ cao mặt trời (°)", 5, 85, 35, key="p3d_elev")
        azim = c2.slider("Hướng nắng (°)", 0, 355, 140, 5, key="p3d_azim")
        height = c3.number_input("Chiều cao thật phần cao nhất (m, 0 = tự đoán đơn vị)", 0.0, 500.0, 0.0, 1.0, key="p3d_h",
                                 help="Ví dụ chiều cao tháp đồng hồ. Không biết thì để 0: file > 500 đơn vị được coi là cm.")
        hdri = st.text_input("File HDRI (.hdr/.exr) cho cách B, hoặc ánh sáng cho cách C (để trống = trời vật lý)", "", key="p3d_hdri") \
            if sky in ("B", "C") else ""
        sky_pic = st.file_uploader("Ảnh trời chụp in-game để ghép (cách C)", type=["png", "jpg", "jpeg", "webp"], key="p3d_skypic") \
            if sky == "C" else None
        presets = st.multiselect("Góc máy", list(plates3d.PRESETS), default=list(plates3d.PRESETS), format_func=plates3d.PRESETS.get,
                                 key="p3d_presets")
        c1, c2 = st.columns(2)
        dec = c1.slider("Giữ lại % tam giác (map nặng: giảm)", 5, 100, 100, 5, key="p3d_dec")
        res = c2.selectbox("Khung", ["1280x720", "1920x1080", "720x1280"], key="p3d_res")
        if st.button("▶ Render nền (Blender, không tốn credit)", key="p3d_go", type="primary", disabled=not (blender and presets)):
            try:
                cfg = plates3d.plan(model, plates3d.out_dir(C.DATA, place), sky=sky, sun_elevation=elev, sun_azimuth=azim,
                                    hdri=hdri or None, presets=presets, real_height_m=height or None, decimate=dec / 100,
                                    resolution=tuple(int(x) for x in res.split("x")))
                with st.spinner("Blender đang render (map nặng có thể mất vài phút)…"):
                    st.session_state["p3d_manifest"] = plates3d.render(cfg)
            except plates3d.Plates3DError as e:
                st.error(str(e))
        m = st.session_state.get("p3d_manifest")
        if m:
            st.success(plates3d.summary(m))
            for w in m.get("warnings") or []:
                st.caption("⚠ " + w)
            cols = st.columns(min(len(m["plates"]), 6) or 1)
            for col, pl in zip(cols, m["plates"]):
                col.image(os.path.join(m["out_dir"], pl["file"]), caption=f"{pl['name']} · {pl['render_sec']} s", use_container_width=True)
            if st.button("📥 Đưa vào hộp chờ duyệt của Kho", key="p3d_add"):
                sky_path = None
                if sky_pic is not None:
                    sky_path = os.path.join(m["out_dir"], "sky_ingame" + os.path.splitext(sky_pic.name)[1].lower())
                    with open(sky_path, "wb") as f:
                        f.write(sky_pic.getvalue())
                r = plates3d.to_library(p.conn, m, game, place, sky_picture=sky_path, look=look)
                st.success(f"Đã thêm {len(r['added'])} ảnh nền vào “{place}” (chờ duyệt ở 📥 phía trên)."
                           + (f" Bỏ qua: {'; '.join(r['skipped'])}" if r["skipped"] else ""))
                st.session_state.pop("p3d_manifest", None)
                st.toast(f"Đã thêm {len(r['added'])} ảnh nền vào “{place}” (chờ duyệt)")
                st.rerun()


@st.fragment
def meshy_panel(p: Pipeline, game: str) -> None:
    """🧍 Character → 3D model (Meshy, paid credits) → rig, saved in data/models3d; its own renders go to the review box. Every call is
    estimated, checked against the caps and written to the ledger before it is sent (core/meshy.py)."""
    p = _fresh(p)
    from core import meshy
    with st.expander("🧍 Nhân vật 3D — dựng mô hình 3D + khung xương bằng Meshy (TỐN CREDIT)", expanded=False):
        # an expander's body runs even when closed: nothing (sheet cutting, the ledger) is done until the person opens the tool
        if not st.toggle("Mở công cụ", key="meshy_open"):
            st.caption("Bật để xem ảnh sẽ gửi, giá ước tính và các lần dựng.")
            return
        meshy.ensure_table(p.conn)
        client = meshy.meshy_client()
        cfg = meshy.settings(p.conn)
        spent = meshy.spent_credits(p.conn)
        st.caption((("Mã API: đã đặt (`MESHY_API_KEY`)." if client else
                     "⚠ Chưa có `MESHY_API_KEY` — chạy `setx MESHY_API_KEY \"msy_...\"` trong PowerShell rồi mở lại Dashboard.") +
                    f" Đã dùng ≈ {spent:g} credit (≈ \\${spent * meshy.usd_per_credit():.2f}) / trần \\${cfg['cap_usd']:g}"
                    f" · 1 credit ≈ \\${meshy.usd_per_credit():g} (MESHY_USD_PER_CREDIT)."))
        cap = st.number_input("Trần Meshy của đợt (USD)", 0.0, 1000.0, float(cfg["cap_usd"]), 5.0, key="meshy_cap")
        if cap != float(cfg["cap_usd"]) and st.button("Lưu trần", key="meshy_cap_save"):
            meshy.save_settings(p.conn, cap_usd=cap)
            _rerun_here()
        chars = [a for a in assets.list_assets(p.conn, game, "character", None, shared_only=True)]
        if not chars:
            st.caption("Kho chưa có nhân vật.")
            return
        pick = st.selectbox("Nhân vật", range(len(chars)), format_func=lambda i: chars[i]["name"], key="meshy_char")
        aid = chars[pick]["id"]
        sheets = [i for i in chars[pick].get("images") or [] if i.get("role") == "design_sheet"]
        sheet_id = None
        if sheets:
            labels = {i["id"]: f"#{i['id']} ({assets.STATUSES.get(i.get('status'), i.get('status'))})" for i in sheets}
            sheet_id = st.selectbox("Bảng nhiều góc để cắt 4 hướng", [None] + list(labels),
                                    format_func=lambda k: "tự chọn (bảng đã duyệt)" if k is None else labels[k], key="meshy_sheet")
        own = st.session_state.get(f"meshy_tp{aid}", "").strip()
        try:
            plan = meshy.plan(p.conn, aid, sheet_image_id=sheet_id, work_dir=os.path.join(C.DATA, "meshy_views"), texture_override=own or None)
        except meshy.MeshyError as e:
            st.error(str(e))
            return
        st.caption(f"Nguồn: {plan['source'] or '—'} · ước {plan['credits']} credit (≈ \\${plan['usd']}) + gắn khung xương "
                   f"{meshy.CREDITS['rig']} credit · lần dựng {meshy.tries(p.conn, aid)}/{meshy.MAX_TRIES_PER_CHARACTER}")
        for prob in plan["problems"]:
            st.warning(prob)
        keep = []
        if plan["views"]:
            cols = st.columns(len(plan["views"]))
            for k, (col, v) in enumerate(zip(cols, plan["views"])):
                col.image(v["image"], caption=v["view"], use_container_width=True)
                if col.checkbox("gửi", True, key=f"meshy_v{aid}_{k}"):
                    keep.append(k)
        st.caption("Câu texture: " + ("bạn tự viết." if plan["texture_by_person"] else "lấy từ hồ sơ chuẩn.") + " Đang gửi:")
        st.code(plan["texture_prompt"], language=None)
        st.text_area("Tự viết câu texture (để trống = lấy từ hồ sơ; dùng cho skin hồ sơ chưa tả, vd Wolfrahh đồ trắng)", key=f"meshy_tp{aid}",
                     max_chars=meshy.TEXTURE_PROMPT_MAX)
        ok = st.checkbox(f"Tôi đồng ý trả ≈ {plan['credits']} credit cho lần dựng này", key=f"meshy_ok{aid}")
        if st.button("▶ Dựng 3D (Meshy)", key="meshy_go", type="primary",
                     disabled=not (client and ok and keep and not plan["problems"] and keep and keep[0] == 0)):
            try:
                r = meshy.submit_model(p.conn, client, plan, view_ids=keep)
                st.success(f"Đã gửi — mã việc {r['task_id']}. Bấm 🔄 để cập nhật (thường vài phút).")
            except meshy.MeshyError as e:
                st.error(str(e))
        if keep and keep[0] != 0:
            st.caption("Ảnh đầu gửi đi phải là mặt trước (Meshy lấy ảnh đầu làm mặt chính).")
        rows = meshy.tasks(p.conn, aid)
        if rows:
            if st.button("🔄 Cập nhật + tải về", key="meshy_refresh", disabled=not client):
                for n in meshy.refresh(p.conn, client):
                    st.caption(n)
            for r in rows:
                st.markdown(f"**#{r['id']} · {r['kind']}** · {r['status']} · {r['credits'] if r['credits'] is not None else '≈' + str(r['credits_est'])}"
                            f" credit · {r['created_at']} UTC" + (f" · `{r['folder']}`" if r["folder"] else "") +
                            (f" · ⚠ {r['error']}" if r["error"] else ""))
                if r["kind"] == "model" and r["status"] == "DOWNLOADED":
                    c1, c2 = st.columns(2)
                    if c1.button("📥 Ảnh 4 hướng vào hộp chờ duyệt", key=f"meshy_lib{r['id']}"):
                        res = meshy.views_to_library(p.conn, r["id"])
                        st.success(f"Thêm {len(res['added'])} ảnh (chờ duyệt)." + (f" Bỏ qua: {res['skipped']}" if res["skipped"] else ""))
                    if c2.button(f"🦴 Gắn khung xương (≈ {meshy.CREDITS['rig']} credit)", key=f"meshy_rig{r['id']}", disabled=not client):
                        try:
                            rr = meshy.submit_rig(p.conn, client, r["id"])
                            st.success(f"Đã gửi gắn khung xương — mã việc {rr['task_id']}.")
                        except meshy.MeshyError as e:
                            st.error(str(e))



@st.fragment
def lib_sources_box(p, game) -> None:
    p = _fresh(p)
    with st.expander("🔄 Nguồn đồng bộ: thư mục tài nguyên (cập nhật kho bằng 1 cú bấm hoặc tự động)", expanded=not assets.list_sources(p.conn, game)):
        st.caption("Chọn một thư mục trên máy chạy Dashboard chứa ảnh (ví dụ thư mục đang đồng bộ với Google Drive). Kho sẽ giống thư mục đó: "
                   "ảnh mới được thêm, ảnh sửa được cập nhật, ảnh trùng không bị thêm hai lần; tên, mô tả bạn đã sửa trong Dashboard **không bị ghi đè**. "
                   "Bật “Tự động” thì mỗi lần mở Dashboard hệ thống tự kiểm tra thư mục có gì mới.")
        st.caption("Cấu trúc nhận được: `Lyra_front.png`, `Lyra_back.png` (cùng tên = một mục), hoặc thư mục `Lyra/1.png…`, hoặc chia theo thư mục con "
                   "`Nhân vật`, `Vũ khí`, `Thú cưng`, `Bản đồ`, `Đạo cụ`. Chỉ nhận JPG/PNG/WebP ≤ 10 MB, tối đa 6 ảnh mỗi mục.")
        for src in assets.list_sources(p.conn, game):
            with st.container(border=True):
                st.markdown(f"**{escape(src['path'])}**")
                st.caption(f"Lần đồng bộ gần nhất: {src['last_sync'] or 'chưa'}" + (f" — {escape(src['last_summary'])}" if src["last_summary"] else ""))
                c1, c2, c3 = st.columns([2, 3, 1.4], vertical_alignment="bottom")
                k = c1.selectbox("Loại mặc định", list(assets.KINDS), index=list(assets.KINDS).index(src["kind"]) if src["kind"] in assets.KINDS else 0,
                                 format_func=lambda x: assets.KINDS[x], key=f"src_kind_{src['id']}")
                ig = c2.text_input("Bỏ qua file/thư mục có từ (cách nhau bằng dấu phẩy)", src["ignore"] or "", key=f"src_ign_{src['id']}")
                auto = c3.checkbox("Tự động", bool(src["auto"]), key=f"src_auto_{src['id']}")
                if (k, ig.strip(), bool(auto)) != (src["kind"], (src["ignore"] or "").strip(), bool(src["auto"])):
                    assets.set_source(p.conn, src["id"], k, ig, auto)
                b1, b2, b3 = st.columns([1.6, 1.6, 1.6])
                rm = b3.checkbox("Xóa ảnh không còn trong thư mục", key=f"src_rm_{src['id']}")
                if b1.button("🔄 Đồng bộ ngay", key=f"src_run_{src['id']}", type="primary"):
                    try:
                        st.session_state[f"src_rep_{src['id']}"] = assets.run_source(p.conn, src["id"], me().get("email"), rm)
                    except (assets.AssetError, OSError) as e:
                        st.error(str(e))
                    else:
                        st.rerun()
                if confirm_all(f"src_del_{src['id']}", [src["id"]], "🗑 Bỏ nguồn này", "Bỏ thư mục này khỏi danh sách (ảnh đã nhập vẫn giữ)?", b2, "Có, bỏ"):
                    assets.remove_source(p.conn, src["id"])
                    _rerun_here()
                rep = st.session_state.get(f"src_rep_{src['id']}")
                if rep:
                    st.success(assets.summary(rep) or "Không có gì thay đổi")
                    for title, key in (("Mục mới", "created"), ("Không còn trong thư mục", "missing"), ("Lỗi / không nhận", "skipped")):
                        if rep[key]:
                            with st.expander(f"{title} ({len(rep[key])})"):
                                for item in rep[key][:80]:
                                    st.caption(f"• {item if isinstance(item, str) else item[0] + ' — ' + item[1]}")
        with st.container(border=True):
            st.markdown("**➕ Thêm thư mục nguồn**")
            path = st.text_input("Đường dẫn thư mục", key="lib_import_path",
                                 placeholder=r"G:\My Drive\Free Fire Save resources\ingame Free Fire\FF_Character_Reference")
            d1, d2 = st.columns([2, 3])
            default_kind = d1.selectbox("Loại mặc định (khi thư mục không nói rõ)", list(assets.KINDS), format_func=lambda k: assets.KINDS[k],
                                        key="lib_import_kind")
            ignore = d2.text_input("Bỏ qua file/thư mục có từ", assets.DEFAULT_IGNORE, key="lib_import_ignore")
            if st.button("Thêm và đồng bộ ngay", key="lib_import_go", disabled=not path.strip(), type="primary"):
                try:
                    sid = assets.add_source(p.conn, game, path, default_kind, ignore, True)
                    st.session_state[f"src_rep_{sid}"] = assets.run_source(p.conn, sid, me().get("email"))
                except (assets.AssetError, OSError) as e:
                    st.error(str(e))
                else:
                    st.rerun()
        st.caption("💡 Cách dễ nhất để luôn cập nhật: cài **Google Drive cho máy tính** (Drive for desktop), để thư mục tài nguyên ở chế độ "
                   "“Ngoại tuyến/Mirror”, rồi thêm chính thư mục đó làm nguồn với “Tự động” bật. Ai thêm ảnh lên Drive, lần mở Dashboard sau ảnh tự vào kho.")


@st.fragment
def lib_ff_site_box(p, game) -> None:
    p = _fresh(p)
    with st.expander("🌐 Cập nhật từ website Free Fire (ff.garena.com)"):
        st.caption("Đọc trang web chính thức: 6 bản đồ và mọi khu vực (tên, mô tả, ảnh), cùng 12 nhân vật / thú cưng / vũ khí mới nhất (tiểu sử, kỹ năng, chỉ số). "
                   "Mục đã có trong kho chỉ được **bổ sung** mô tả (đặt trong khối `[ff.garena.com]`, chạy lại thì thay khối đó) và ảnh chính thức, "
                   "không ghi đè phần bạn đã viết. Website không cho lấy toàn bộ danh sách nên đây chỉ là các mục mới nhất; phần còn lại vẫn lấy từ thư mục Drive. "
                   "Tự động chạy lại mỗi 30 ngày. Cần Node.js trên máy.")
        info = ff_site.status(p.conn)
        if info["last"] or info["text"]:
            st.caption(f"Lần gần nhất: {info['last'] or '—'} — {escape(info['text'])}")
        if st.button("🌐 Cập nhật ngay", key="ff_site_go", disabled=info["running"], type="primary"):
            if ff_site.start_background(C.DB, game, me().get("email")):
                st.toast("Đang đọc website ở nền, vài phút; bấm tải lại trang để xem kết quả")
            st.rerun()


@st.fragment
def lib_vision_box(p, game) -> None:
    p = _fresh(p)
    with st.expander("🤖 Đọc mô tả ngoại hình bằng Claude (nhân vật / thú cưng)"):
        st.caption("Ảnh đầu của mỗi nhân vật thường là một bảng thiết kế nhiều góc/tư thế (turn-around, bảng màu, phụ kiện) — rất nhiều chi tiết hữu ích, "
                   "nhưng gửi thẳng tấm đó cho AI vẽ ảnh lại làm nó chép lẫn lộn giữa các nhân vật trong cùng một cảnh, nên màn Storyboard không dùng tấm này làm ảnh "
                   "tham chiếu (xem “🖼 Ảnh tham chiếu” ở màn Kịch bản). Chữ thì không bị chép lẫn như vậy: nút này cho Claude **nhìn ảnh và viết lại** màu/kiểu tóc, "
                   "trang phục, phụ kiện thành một đoạn mô tả, lưu vào mô tả của mục (không đè phần bạn đã viết) — Director sẽ đọc được đoạn này khi phân tích kịch bản.")
        n_pending = asset_vision.pending(p.conn, game)
        st.caption(f"{n_pending} mục nhân vật/thú cưng chưa được đọc" if n_pending else "Mọi mục nhân vật/thú cưng đã được đọc.")
        prog = asset_vision.progress(game)
        if asset_vision.active(game) and prog["total"]:
            ui.progress_bar(prog["done"] / prog["total"], text=f"Đang đọc {prog['done']}/{prog['total']} mục…")
        problem = asset_vision.last_error(game)
        if problem:
            st.warning(f"⚠ Đã dừng: {problem}")
            if st.button("↻ Thử lại", key="asset_vision_retry"):
                asset_vision.clear_error(game)
                _rerun_here()
        vision_usd = cost.llm_estimate(p.conn, "asset_vision", n_pending, images=asset_vision.MAX_IMAGES)
        if st.button("🤖 Đọc mô tả ngoại hình" + cost.llm_tag(vision_usd, n_pending), key="asset_vision_go", disabled=not n_pending or asset_vision.active(game), type="primary"):
            if asset_vision.start(C.DB, game):
                st.toast("Đang đọc ở nền; bấm tải lại trang để xem tiến độ")
            _rerun_here()


@st.fragment
def lib_video_box(p, game) -> None:
    p = _fresh(p)
    with st.expander("📹 Phân tích video kỹ năng bằng Claude (nhân vật quay trong gameplay)"):
        st.caption("Tải video gameplay quay skill của một nhân vật — Claude nhìn các khung hình lấy mẫu đều theo thời gian và viết lại "
                   "nhận dạng nhân vật + kỹ năng/VFX thành chữ, MỖI câu gắn nhãn [OBSERVED] (thấy trực tiếp) / [EXPLICIT] (chữ overlay nói rõ) / "
                   "[INFERRED] (suy luận có lý do) / [UNKNOWN] (không xác nhận được) — video là bằng chứng gốc, không tự bịa sát thương/thời gian hồi/"
                   "tầm bắn nếu video không xác nhận. Bạn xem, sửa và tự chọn ảnh muốn giữ trước khi lưu — không tự động ghi gì cả.")
        characters = [a for a in assets.list_assets(p.conn, game, None, None, shared_only=True) if a["kind"] in ("character", "pet")]
        if not characters:
            st.caption("Kho chưa có nhân vật/thú cưng nào.")
        else:
            by_id = {a["id"]: a["name"] for a in characters}
            va_asset_id = st.selectbox("Nhân vật / thú cưng", list(by_id), format_func=lambda i: by_id[i], key="va_asset")
            va_video = st.file_uploader("Video gameplay (mp4/mov/webm/mkv, tối đa 200 MB)", type=["mp4", "mov", "webm", "mkv"], key="va_video")
            va_note = st.text_input("Ghi chú thêm cho Claude (tuỳ chọn)", key="va_note",
                                    placeholder="vd: chỉ nhìn skill chủ động, bỏ qua trang phục")
            va_count = st.slider("Số khung hình lấy mẫu", 4, video_analysis.MAX_FRAMES, 8, key="va_count")
            if st.button("🎬 Phân tích video" + cost.llm_tag(cost.llm_estimate(p.conn, "video_analysis", 1, images=va_count), 1),
                         key="va_go", disabled=not va_video, type="primary"):
                client = llm_client()
                if client is not None:
                    try:
                        with st.spinner("Đang trích khung hình + hỏi Claude…"):
                            tmp_dir = tempfile.mkdtemp(prefix="va_")
                            video_path = os.path.join(tmp_dir, va_video.name)
                            with open(video_path, "wb") as f:
                                f.write(va_video.getvalue())
                            meta = video_analysis.probe(video_path)
                            frames = video_analysis.extract_frames(video_path, os.path.join(tmp_dir, "frames"), va_count)
                            text = video_analysis.analyze(client, by_id[va_asset_id], frames, meta, va_note)
                    except (video_analysis.VideoAnalysisError, llm_runner.LlmError) as e:
                        st.error(str(e))
                    else:
                        st.session_state[f"va_draft_{va_asset_id}"] = {"text": text, "frames": frames, "source": va_video.name}
                        _rerun_here()
            draft = st.session_state.get(f"va_draft_{va_asset_id}")
            if draft:
                st.markdown(f"**Bản nháp phân tích — {by_id[va_asset_id]}** (từ `{draft['source']}`)")
                cols = st.columns(min(len(draft["frames"]), 5) or 1)
                keep = []
                for i, fp in enumerate(draft["frames"]):
                    with cols[i % len(cols)]:
                        st.image(fp, use_container_width=True)
                        if st.checkbox("Thêm làm ảnh tham chiếu", key=f"va_kf_{va_asset_id}_{i}"):
                            keep.append(fp)
                edited = st.text_area("Nội dung (sửa được trước khi lưu)", draft["text"], height=220, key=f"va_text_{va_asset_id}")
                b1, b2 = st.columns(2)
                if b1.button("💾 Lưu vào mô tả", key=f"va_save_{va_asset_id}", type="primary"):
                    asset = assets.get(p.conn, va_asset_id)
                    new_desc = video_analysis.with_block(asset["description"], edited, draft["source"])
                    assets.update(p.conn, va_asset_id, asset["name"], asset["aliases"], new_desc)
                    st.session_state.pop(f"va_draft_{va_asset_id}", None)
                    st.success("Đã lưu vào mô tả.")
                    st.rerun()
                if b2.button(f"🖼 Thêm {len(keep)} ảnh đã tick vào tài nguyên", key=f"va_addimg_{va_asset_id}", disabled=not keep):
                    added = 0
                    for fp in keep:
                        with open(fp, "rb") as f:
                            try:
                                assets.add_image(p.conn, va_asset_id, os.path.basename(fp), f.read())
                                added += 1
                            except assets.AssetError as e:
                                st.warning(str(e))
                    st.success(f"Đã thêm {added} ảnh.")
                    st.rerun()


@st.fragment
def lib_bulk_box(p, game) -> None:
    p = _fresh(p)
    with st.expander("⬆ Tải nhiều ảnh cùng lúc (tên file = tên tài nguyên)"):
        st.caption("Chọn nhiều ảnh một lượt: `Lyra_front.png` + `Lyra_back.png` thành một mục Lyra; mục đã có thì được thêm ảnh; ảnh trùng bị bỏ qua.")
        bulk_kind = st.selectbox("Loại", list(assets.KINDS), format_func=lambda k: assets.KINDS[k], key="lib_bulk_kind")
        bulk = st.file_uploader("Ảnh", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="lib_bulk_files")
        if st.button("Thêm vào kho", key="lib_bulk_go", disabled=not bulk):
            r = assets.add_files(p.conn, game, bulk_kind, [(f.name, f.getvalue()) for f in bulk], me().get("email"))
            st.success(f"Mục mới: {len(r['created'])}, ảnh thêm: {r['added']}, trùng bỏ qua: {r['unchanged']}" + (f", lỗi: {len(r['skipped'])}" if r["skipped"] else ""))
            for name, why in r["skipped"][:20]:
                st.caption(f"• {name} — {why}")


@st.fragment
def lib_sound_box(p) -> None:
    p = _fresh(p)
    with st.expander("🎼 Kho âm thanh (nhạc nền & hiệu ứng) — thư mục nguồn", expanded=not sound_lib.list_sources(p.conn)):
        st.caption("Thư mục chứa nhạc và hiệu ứng (mp3, wav, m4a, ogg, flac). Hệ thống chỉ liệt kê file (không mở từng file) nên thư mục vài GB vẫn xong ngay; "
                   "phân loại nhạc nền / hiệu ứng và tâm trạng (vui vẻ, sôi động, kịch tính, hài...) dựa theo tên thư mục. Ở màn Bản giao mọi người tìm, nghe thử và dùng.")
        for src in sound_lib.list_sources(p.conn):
            with st.container(border=True):
                st.markdown(f"**{escape(src['path'])}** · {src['tracks']} bản")
                st.caption(f"Lần quét gần nhất: {src['last_sync'] or 'chưa'}" + (f" — {escape(src['last_summary'])}" if src["last_summary"] else ""))
                s1, s2, s3 = st.columns([3, 1.2, 1.4], vertical_alignment="bottom")
                ig = s1.text_input("Bỏ qua thư mục có từ", src["ignore"] or "", key=f"snd_ign_{src['id']}")
                auto = s2.checkbox("Tự động", bool(src["auto"]), key=f"snd_auto_{src['id']}")
                if (ig.strip(), bool(auto)) != ((src["ignore"] or "").strip(), bool(src["auto"])):
                    sound_lib.set_source(p.conn, src["id"], ig, auto)
                if s3.button("🔄 Quét ngay", key=f"snd_scan_{src['id']}", type="primary"):
                    try:
                        sound_lib.scan(p.conn, src["id"])
                    except (sound_lib.SoundError, OSError) as e:
                        st.error(str(e))
                    else:
                        _rerun_here()
                if confirm_all(f"snd_del_{src['id']}", [src["id"]], "🗑 Bỏ nguồn này", "Bỏ thư mục khỏi kho âm thanh (file gốc không bị xóa)?", st, "Có, bỏ"):
                    sound_lib.remove_source(p.conn, src["id"])
                    _rerun_here()
        a1, a2 = st.columns([4, 1.4], vertical_alignment="bottom")
        snd_path = a1.text_input("Thêm thư mục âm thanh", key="snd_new_path", placeholder=r"G:\My Drive\...\Free Fire Save resources\Sound Effect")
        if a2.button("Thêm và quét", key="snd_new_go", disabled=not snd_path.strip(), type="primary"):
            try:
                sid = sound_lib.add_source(p.conn, snd_path)
                sound_lib.scan(p.conn, sid)
            except (sound_lib.SoundError, OSError) as e:
                st.error(str(e))
            else:
                _rerun_here()


@st.fragment
def lib_new_item_box(p, game) -> None:
    p = _fresh(p)
    with st.expander("➕ Thêm một mục"):
        c1, c2 = st.columns([3, 2])
        name = c1.text_input("Tên", key="lib_new_name")
        kind = c2.selectbox("Loại", list(assets.KINDS), format_func=lambda k: assets.KINDS[k], key="lib_new_kind")
        aliases = st.text_input("Tên gọi khác trong kịch bản (cách nhau bằng dấu phẩy)", key="lib_new_aliases")
        desc = st.text_area("Mô tả (ngoại hình, đặc điểm để Director dùng)", key="lib_new_desc", height=70)
        files = st.file_uploader("Ảnh tham khảo", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="lib_new_files")
        if st.button("Thêm vào kho", key="lib_new_go", disabled=not name.strip()):
            try:
                aid = assets.create(p.conn, game, kind, name, desc, aliases, None, me().get("email"))
                for f in files[: assets.MAX_IMAGES_PER_ASSET]:
                    assets.add_image(p.conn, aid, f.name, f.getvalue())
            except assets.AssetError as e:
                st.error(str(e))
            else:
                st.rerun()


@st.fragment
def lib_asset_card(p: Pipeline, a: dict, items: list) -> None:
    p = _fresh(p)
    with st.expander(f"{a['kind_label']} · {a['name']} · {len(a['images'])} ảnh"):
        if a["images"]:
            cols = st.columns(min(len(a["images"]), 6))
            for col, img in zip(cols, a["images"]):
                col.image(assets.thumbnail(img["path"]), width=110,
                          caption=assets.ROLES.get(a["kind"], {}).get(img.get("role") or "", "chưa rõ vai trò")
                          + (f" · {assets.LOOKS[img['look']]}" if img.get("look") in assets.LOOKS else ""))
                if col.button("Xóa ảnh", key=f"lib_img_rm_{img['id']}"):
                    assets.remove_image(p.conn, img["id"])
                    st.rerun()
        if a["description"]:
            st.caption(a["description"][:700])
        if a["kind"] in ("character", "pet"):
            profile_form(p, a)
        if st.checkbox("✏️ Sửa, gộp hoặc xóa mục này", key=f"lib_edit_{a['id']}"):     # the form only exists when asked for (keeps the page light)
            e_name = st.text_input("Tên", a["name"], key=f"lib_e_name_{a['id']}")
            e_alias = st.text_input("Tên gọi khác", a["aliases"], key=f"lib_e_alias_{a['id']}")
            e_desc = st.text_area("Mô tả", a["description"], key=f"lib_e_desc_{a['id']}", height=70)
            more = st.file_uploader("Thêm ảnh", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key=f"lib_e_up_{a['id']}")
            others = [x for x in items if x["id"] != a["id"]]
            if others:
                g1, g2 = st.columns([3, 1.4], vertical_alignment="bottom")
                names = {x["id"]: f"{x['kind_label']}: {x['name']}" for x in others}
                target = g1.selectbox("Gộp mục này vào mục khác (ảnh chuyển sang, tên này thành tên gọi khác)", [None] + list(names),
                                      format_func=lambda i: "— không gộp —" if i is None else names[i], key=f"lib_merge_{a['id']}")
                if target is not None and g2.button("Gộp", key=f"lib_merge_go_{a['id']}"):
                    try:
                        assets.merge(p.conn, a["id"], target)
                    except assets.AssetError as e:
                        st.error(str(e))
                    else:
                        st.rerun()
            b1, b2 = st.columns(2)
            if b1.button("💾 Lưu", key=f"lib_e_save_{a['id']}", type="primary"):
                try:
                    assets.update(p.conn, a["id"], e_name, e_alias, e_desc)
                    for f in more:
                        assets.add_image(p.conn, a["id"], f.name, f.getvalue())
                except assets.AssetError as e:
                    st.error(str(e))
                else:
                    st.rerun()
            if confirm_all(f"lib_del_{a['id']}", [a["id"]], "🗑 Xóa mục này", f"Xóa “{a['name']}” khỏi kho (các dự án đang dùng cũng mất)?", b2, "Có, xóa"):
                assets.delete(p.conn, a["id"])
                st.rerun()




def asset_library_panel(p: Pipeline) -> None:
    """Settings: the shared resource library (people with the Kho tài nguyên right)."""
    catalog = subjects.games()
    keys = list(catalog)
    game = st.selectbox("Game / loại nội dung", keys, format_func=lambda k: catalog[k][0], key="lib_game")
    items = assets.list_assets(p.conn, game, None, None, shared_only=True)
    st.caption(f"{len(items)} mục trong kho **{catalog[game][0]}**. Mọi dự án của game này đều chọn dùng được.")
    library_review_box(p, game)
    library_lost_box(p)
    library_health(p, game)
    plates3d_panel(p, game)
    meshy_panel(p, game)
    lib_sources_box(p, game)
    lib_ff_site_box(p, game)
    lib_vision_box(p, game)
    lib_video_box(p, game)
    lib_bulk_box(p, game)
    lib_sound_box(p)
    lib_new_item_box(p, game)
    kind_filter = st.radio("Xem", ["all"] + list(assets.KINDS), horizontal=True, key="lib_filter",
                           format_func=lambda k: "Tất cả" if k == "all" else assets.KINDS[k])
    query = st.text_input("Tìm theo tên", key="lib_query", placeholder="vd Lyra, Đền, Bermuda")
    shown = [a for a in items if (kind_filter == "all" or a["kind"] == kind_filter)
             and (not query.strip() or assets.fold(query) in assets.fold(a["name"] + " " + (a["aliases"] or "")))]
    per_page = 12                                     # every picture on the page is decoded on each rerun: never draw the whole library at once
    pages = max((len(shown) + per_page - 1) // per_page, 1)
    if pages > 1:
        page = int(st.number_input(f"Trang (có {len(shown)} mục, {pages} trang)", 1, pages, 1, key="lib_page"))
        shown = shown[(page - 1) * per_page: page * per_page]
    for a in shown:
        lib_asset_card(p, a, items)


# ---- history -------------------------------------------------------------------------
def trash_section(pid: int) -> None:
    """Deleted/rejected images and clips, kept for the retention period; restorable."""
    with st.container(border=True):
        ui.html(ui.card_title("🗑 Thùng rác", f"ảnh và video bị xóa/loại · tự xóa vĩnh viễn sau {trash.retention_days()} ngày"))
        t_img, t_vid = st.tabs(["Ảnh", "Video"])
        for tab, kind in ((t_img, "images"), (t_vid, "videos")):
            with tab:
                entries = trash.items(C.DATA, pid, kind)
                if not entries:
                    st.caption("Trống.")
                for e in entries:
                    a, b = st.columns([3, 1], vertical_alignment="center")
                    with a:
                        if kind == "images":
                            show_image(e["path"], width=220)
                        else:
                            with st.expander("▶ Xem video"):
                                st.video(e["path"])
                        scene = f"Cảnh {e['scene_idx']} · " if e.get("scene_idx") else ""
                        st.caption(f"{scene}{e['reason']} · xóa {time.strftime('%d/%m/%Y %H:%M', time.localtime(e['deleted_at']))}"
                                   f" · còn {e['days_left']} ngày · {e['original']}")
                    if b.button("↩ Khôi phục", key=f"tr_{kind}_{e['file']}"):
                        if act(lambda: trash.restore(C.DATA, pid, kind, e["file"]), "Đã khôi phục"):
                            st.rerun()


def effectiveness_panel(p: Pipeline, pid: int, nested: bool = False) -> None:
    """Is the workflow effective for the project in view: 5 figures from what the pipeline already records."""
    r = effectiveness.report(p.conn, pid, cost.load_pricing())
    ui.html(ui.card_title(f"🎯 Hiệu quả workflow — {p.project(pid)['name']}", "5 chỉ số, tính từ dữ liệu đã ghi; chưa đủ dữ liệu thì ghi rõ"))
    pct = (lambda v: "—" if v is None else f"{v:.0%}")
    num = (lambda v, d=1: "—" if v is None else f"{v:.{d}f}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Phút / giây video", num(r["wall_min_per_sec"]), help="Tổng thời gian từ lúc tạo dự án đến video xong gần nhất, chia cho số giây "
              f"video đã xong ({r['video_seconds']:g}s). Máy gen: {num(r['gen_min_per_sec'])} phút/giây.")
    c2.metric(f"Chi phí / giây ({r['currency']})", num(r["cost_per_sec"], 3),
              help="Theo bảng giá khai báo × lượt gửi đã ghi" + (f"; thiếu giá: {', '.join(r['unknown_prices'])}" if r["unknown_prices"] else ""))
    c3.metric("Đạt lần đầu (ảnh / video)", f"{pct(r['image']['first_pass'])} / {pct(r['video']['first_pass'])}",
              help=f"Số lần gen trung bình mỗi cảnh: ảnh {num(r['image']['tries_per_scene'])}, video {num(r['video']['tries_per_scene'])}")
    c4.metric("QC Agent đồng ý với người", pct(r["qc"]["agreement"]),
              help=f"Trên {r['qc']['pairs']} ảnh có cả điểm QC lẫn quyết định của người; AI chặt quá {r['qc']['ai_too_strict']}, "
                   f"lỏng quá {r['qc']['ai_too_lenient']} lần. Dùng để chỉnh ngưỡng QC.")
    c5.metric("Thao tác tay / cảnh", num(r["touches_per_scene"]), help=f"Duyệt / loại / hủy do người bấm: {r['touches']} lần")
    manual = st.number_input("Làm tay mất bao nhiêu phút cho 1 giây video (mặc định chung 30 phút — người dùng chốt; sửa để so thử, không lưu)",
                             min_value=0.0, value=effectiveness.MANUAL_MIN_PER_SEC, step=1.0, key=f"eff_manual_{pid}")
    summary = "\n".join(effectiveness.summary_lines(r, manual or None))
    if nested:                                  # already inside an expander (Streamlit forbids expander-in-expander)
        st.markdown("**📋 Bản tóm tắt để gửi báo cáo**")
        st.code(summary, language="text")
    else:
        with st.expander("📋 Bản tóm tắt để gửi báo cáo"):
            st.code(summary, language="text")


def compare_panel(p: Pipeline) -> None:
    """v3: the same script made in different ways (v2 / one clip per shot / Kling multi-shot) side by side, with the numbers and
    the person's 1–5 marks — the base of docs/V3_AB_REPORT.md."""
    from core import compare
    projects = access.filter_rows(p.conn, p.conn.execute("SELECT id, name FROM projects ORDER BY id DESC").fetchall(), C.access_user())
    with st.expander("⚖ So sánh các cách làm (cùng kịch bản)", expanded=False):
        chosen = st.multiselect("Chọn 2–3 dự án", [r["id"] for r in projects], max_selections=3, key="cmp_projects",
                                format_func=lambda i: next(f"#{r['id']} {r['name']}" for r in projects if r["id"] == i))
        if len(chosen) < 2:
            st.caption("Nhân bản dự án ở ⚙ → “🧬 Nhân bản dự án”, làm mỗi bản theo một cách, rồi chọn ở đây để so sánh.")
            return
        rows = [compare.metrics(p, i, C.DATA) for i in chosen]
        cols = st.columns(len(rows))
        for col, r in zip(cols, rows):
            with col:
                st.markdown(f"**#{r['project_id']} {escape(r['name'])}**  \n{escape(r['mode'] or 'v2')}")
                if r["final"] and os.path.exists(r["final"]):
                    show_video(r["final"])
                else:
                    st.caption("chưa có bản giao")
                old = r["scores"]
                new = {k: st.slider(label, 1, 5, int(old.get(k) or 3), key=f"cmp_{r['project_id']}_{k}")
                       for k, label in compare.CRITERIA.items()}
                note = st.text_area("Nhận xét", old.get("note", ""), key=f"cmp_note_{r['project_id']}", height=70)
                if st.button("💾 Lưu điểm", key=f"cmp_save_{r['project_id']}"):
                    compare.save_scores(p.conn, r["project_id"], {**new, "note": note})
                    st.toast("Đã lưu điểm")
                    st.rerun()                     # the table below was built before the save
        st.markdown(compare.report_markdown(rows).replace("$", "\\$"))      # "$" would start a formula
        st.caption("Chi phí theo bảng giá (ước tính); thời gian làm = từ job đầu tiên đến job cuối cùng của dự án.")


def monitor(p: Pipeline, pid: int) -> None:
    """Load and performance of the whole system (all projects), to spot overload before it costs credit."""
    if ui.v2_on():
        return _monitor_v2(p, pid)
    mgr = autopilot_manager(C.DB, C.DATA)
    snap = perf.snapshot(p.conn, mgr.queue_length(), mgr.running_count(), mgr.max_parallel)
    snap["projects"] = access.filter_rows(p.conn, snap["projects"], C.access_user())     # only the projects this person may see
    ui.html(ui.card_title("📊 Theo dõi hiệu suất & tải hệ thống", "toàn bộ dự án, làm mới bằng nút bên phải"))
    compare_panel(p)
    if st.button("↻ Làm mới", key="perf_refresh"):
        st.rerun()
    for msg in snap["alerts"]:
        st.markdown(colored("warn", f"⚠ {escape(str(msg))}"), unsafe_allow_html=True)
    if not snap["alerts"]:
        st.markdown(colored("ok", "✔ Chưa thấy dấu hiệu quá tải."), unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dự án chạy tự động", f"{mgr.running_count()}/{mgr.max_parallel}", help="AUTOPILOT_MAX_PARALLEL")
    c2.metric("Đang xếp hàng", mgr.queue_length())
    c3.metric("Job hôm nay", f"{snap['jobs_today']}/{snap['daily_limit'] or '∞'}", help="AUTOPILOT_DAILY_JOBS (giờ UTC)")
    c4.metric("Job đang chạy/chờ", sum(k["running"] + k["queued"] for k in snap["kinds"]))
    rows = []
    for k in snap["kinds"]:
        total = k["ok_24h"] + k["failed_24h"]
        rows.append({"Loại": dict(perf.KINDS)[k["kind"]], "Đang chạy": k["running"], "Chờ": k["queued"],
                     "Xong 1h": k["ok_1h"], "Lỗi 1h": k["failed_1h"], "Xong 24h": k["ok_24h"], "Lỗi 24h": k["failed_24h"],
                     "Tỉ lệ lỗi 24h": f"{k['failed_24h'] / total:.0%}" if total else "-",
                     "Thời gian TB": f"{k['avg_sec']:.0f}s" if k["avg_sec"] else "-",
                     "Gần đây / trước đó": (f"{k['recent_sec']:.0f}s / {k['earlier_sec']:.0f}s"
                                            if k["recent_sec"] and k["earlier_sec"] else "-")})
    data_table(rows, hide_index=True, use_container_width=True)
    st.caption("Mức song song tự học (tăng dần khi chạy êm, giảm một nửa khi nhà cung cấp báo quá tải 429): " + "; ".join(
        f"{dict(perf.KINDS)[k]}: {v['limit']} job cùng lúc, đã bị giới hạn {v['hits']} lần" for k, v in snap["learned"].items()))
    if snap["usage_today"]:
        st.caption("Dùng hôm nay: " + ", ".join(f"{q:g} {unit} ({kind})" for kind, unit, q in snap["usage_today"]))
    effectiveness_panel(p, pid)
    st.caption("👥 Số video / tiền theo người dùng → màn **Nhóm**. 📁 Bảng tất cả dự án và 🎬 sản phẩm đã hoàn tất → màn **⌂ Tất cả dự án**. "
               "Trang này chỉ giữ sức khỏe hệ thống: hàng đợi, tốc độ, lỗi, hiệu quả.")
    st.caption("Ngưỡng cảnh báo chỉnh bằng biến môi trường: PERF_MAX_ACTIVE, PERF_FAIL_WARN, PERF_SLOW_WARN; "
               "song song: AUTOPILOT_MAX_PARALLEL; trần ngày: AUTOPILOT_DAILY_JOBS. "
               "Chưa đo thời gian gọi Claude (QC/motion).")


    st.markdown("---")
    ui.html(ui.card_title("🩺 Giám sát từng khâu", "lỗi, lỗi âm thầm và chỗ chưa trơn tru trong 24h qua"))
    stages = diag.stage_table(p.conn)
    data_table([{"": diag.health(s), "Khâu": s["label"], "Job": "-" if s["jobs"] is None else str(s["jobs"]),
                   "Xong": "-" if s["ok"] is None else str(s["ok"]), "Lỗi": "-" if s["failed"] is None else str(s["failed"]),
                   "Gen lại": "-" if s["retried"] is None else str(s["retried"]), "Cảnh báo": s["warn"],
                   "Lỗi ghi nhận": s["error"]} for s in stages], hide_index=True, use_container_width=True)
    findings = diag.scan(p.conn, C.DATA, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
    st.markdown(f"**Vấn đề phát hiện ({len(findings)})** — gồm cả lỗi không ai báo (job kẹt, file mất, tiến trình chết, gen lại nhiều...)")
    if not findings:
        st.markdown(colored("ok", "✔ Chưa thấy vấn đề âm thầm."), unsafe_allow_html=True)
    for f in findings[:30]:
        color = "bad" if f["severity"] == "error" else "warn"
        st.markdown(colored(color, f"● {escape(diag.STAGE_LABEL.get(f['stage'], f['stage']))}") + f" {escape(diag.redact(f['title']))}"
                    + (f" — {escape(diag.redact(f['detail']))}" if f["detail"] else ""), unsafe_allow_html=True)
    if diag.lost():
        st.warning(f"⚠ {diag.lost()} sự kiện chẩn đoán không ghi được vào CSDL (bận/lỗi) từ lúc mở Dashboard — xem file "
                   "`data/manifest.sqlite.diag_lost.log`")
    events = diag.recent(p.conn, 24, 40)
    with st.expander(f"Sự kiện lỗi/cảnh báo gần đây ({len(events)})"):
        data_table([{"Giờ": e["last_at"][11:19], "Mức": e["severity"], "Khâu": e["stage"], "Mã": e["code"] or "",
                       "Lần": e["count"], "Dự án": str(e["project_id"] or ""), "Nội dung": e["message"]} for e in events],
                     hide_index=True, use_container_width=True)
    text = diag.report(p.conn, C.DATA, {"Đang chạy/xếp hàng": f"{mgr.running_count()}/{mgr.queue_length()}",
                                      "Mức song song tự học": {k: v["limit"] for k, v in snap["learned"].items()}})
    st.markdown("**📋 Báo cáo chẩn đoán** — bấm nút copy ở góc khung dưới (hoặc tải file), dán vào chat để mình sửa. "
                "Đã che khóa/token và đường dẫn cá nhân.")
    st.download_button("⬇ Tải báo cáo (.md)", text, file_name="bao_cao_chan_doan.md", key="diag_dl")
    st.code(text, language="markdown")
    st.caption("Giám sát luôn chạy nền khi có thao tác gọi nhà cung cấp/Claude; ngưỡng: DIAG_STUCK_IMAGE_MIN, "
               "DIAG_STUCK_VIDEO_MIN, DIAG_QUEUED_MIN, DIAG_RETRY_WARN.")


def _monitor_v2(p: Pipeline, pid: int) -> None:
    """UI v2 (flag ui_v2): same data and controls as `monitor`. Outside: 4 stats + system status (+ alerts/findings only when there are any);
    every detail table / explanation sits in a labelled expander (closed) or an ⓘ."""
    from dashboard.design import components as D
    from dashboard.design.screens.v2_tables import Raw, table
    mgr = autopilot_manager(C.DB, C.DATA)
    snap = perf.snapshot(p.conn, mgr.queue_length(), mgr.running_count(), mgr.max_parallel)
    snap["projects"] = access.filter_rows(p.conn, snap["projects"], C.access_user())     # only the projects this person may see
    busy = sum(k["running"] + k["queued"] for k in snap["kinds"])
    stages = diag.stage_table(p.conn)
    findings = diag.scan(p.conn, C.DATA, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
    events = diag.recent(p.conn, 24, 40)
    n_bad = sum(1 for s in stages if diag.health(s) == "🔴")
    n_warn = sum(1 for s in stages if diag.health(s) == "🟡")
    learned = "; ".join(f"{dict(perf.KINDS)[k]}: {v['limit']} job cùng lúc, đã bị giới hạn {v['hits']} lần" for k, v in snap["learned"].items())
    usage = ", ".join(f"{q:g} {unit} ({kind})" for kind, unit, q in snap["usage_today"])
    explain = ("**Các số ở trên**\n\n"
               "- Dự án chạy tự động: số dự án đang chạy / tối đa song song (`AUTOPILOT_MAX_PARALLEL`).\n"
               "- Job hôm nay: đã gửi / trần ngày (`AUTOPILOT_DAILY_JOBS`, tính theo giờ UTC).\n\n"
               "**Mức song song tự học** (tăng dần khi chạy êm, giảm một nửa khi nhà cung cấp báo quá tải 429): " + learned
               + ("\n\n**Dùng hôm nay:** " + usage if usage else "")
               + "\n\n👥 Số video / tiền theo người dùng → màn **Nhóm**. 📁 Bảng tất cả dự án và 🎬 sản phẩm đã hoàn tất → màn **⌂ Tất cả dự án**. "
               "Trang này chỉ giữ sức khỏe hệ thống: hàng đợi, tốc độ, lỗi, hiệu quả.\n\n"
               "Ngưỡng cảnh báo chỉnh bằng biến môi trường: `PERF_MAX_ACTIVE`, `PERF_FAIL_WARN`, `PERF_SLOW_WARN`; song song: `AUTOPILOT_MAX_PARALLEL`; "
               "trần ngày: `AUTOPILOT_DAILY_JOBS`. Chưa đo thời gian gọi Claude (QC/motion).\n\n"
               "Giám sát luôn chạy nền khi có thao tác gọi nhà cung cấp/Claude; ngưỡng: `DIAG_STUCK_IMAGE_MIN`, `DIAG_STUCK_VIDEO_MIN`, "
               "`DIAG_QUEUED_MIN`, `DIAG_RETRY_WARN`.")
    with D.hero("mon"):
        st.markdown(D.hero_html("📊 Theo dõi hiệu suất & tải hệ thống", "Toàn bộ dự án — làm mới bằng nút bên dưới.",
                                [("Quá tải", "bad") if snap["alerts"] else ("Chưa thấy quá tải", "ok")]), unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(D.stat("Dự án chạy tự động", f"{mgr.running_count()}/{mgr.max_parallel}"), unsafe_allow_html=True)
        c2.markdown(D.stat("Đang xếp hàng", str(mgr.queue_length())), unsafe_allow_html=True)
        c3.markdown(D.stat("Job hôm nay", f"{snap['jobs_today']}/{snap['daily_limit'] or '∞'}"), unsafe_allow_html=True)
        c4.markdown(D.stat("Job đang chạy/chờ", str(busy)), unsafe_allow_html=True)
        b1, b2, _ = st.columns([1.6, 1.9, 4.5], vertical_alignment="center")
        with b1:
            if st.button("↻ Làm mới", key="perf_refresh"):
                st.rerun()
        with b2:
            with D.info("mon-explain", label="Giải thích số liệu", help_text=D.md_plain(explain)):
                st.markdown(explain)
    for msg in snap["alerts"]:                       # only when there is one
        st.markdown(D.pill("Cảnh báo", "warn") + f" {escape(msg)}", unsafe_allow_html=True)
    with D.card("mon-status"):
        stage_pill = (D.pill(f"Khâu: {n_bad} lỗi", "bad") if n_bad else "") + (" " + D.pill(f"{n_warn} cảnh báo", "warn") if n_warn else "")
        found = (D.pill(f"{len(findings)} vấn đề phát hiện", "bad" if any(f["severity"] == "error" for f in findings) else "warn")
                 if findings else D.pill("Chưa thấy vấn đề âm thầm", "ok"))
        D.line((stage_pill or D.pill("Các khâu ổn", "ok")) + " " + found,
               "**Vấn đề phát hiện** gồm cả lỗi không ai báo (job kẹt, file mất, tiến trình chết, gen lại nhiều...). Bảng từng khâu, sự kiện "
               "và báo cáo chẩn đoán nằm ở các mục gập bên dưới.", "mon-status")
        show = (lambda f: st.markdown('<div class="mon-find">' + D.pill(diag.STAGE_LABEL.get(f["stage"], f["stage"]), "bad" if f["severity"] == "error" else "warn")
                                      + f" {escape(diag.redact(f['title']))}" + (f" — {escape(diag.redact(f['detail']))}" if f["detail"] else "") + "</div>",
                                      unsafe_allow_html=True))
        for f in findings[:3]:                       # a list > 3 items → the top 3 here, the rest in a labelled expander (still up to 30)
            show(f)
        if len(findings) > 3:
            with st.expander(f"Xem thêm {min(len(findings), 30) - 3} vấn đề khác", expanded=False):
                for f in findings[3:30]:
                    show(f)
        if diag.lost():
            st.warning(f"⚠ {diag.lost()} sự kiện chẩn đoán không ghi được vào CSDL (bận/lỗi) từ lúc mở Dashboard — xem file "
                       "`data/manifest.sqlite.diag_lost.log`")
    compare_panel(p)
    with st.expander("📈 Tải theo loại job — 24 giờ qua", expanded=False):
        rows = []
        for k in snap["kinds"]:
            total = k["ok_24h"] + k["failed_24h"]
            rate = k["failed_24h"] / total if total else None
            rows.append((dict(perf.KINDS)[k["kind"]], k["running"], k["queued"], k["ok_1h"], k["failed_1h"], k["ok_24h"], k["failed_24h"],
                         Raw(D.pill(f"{rate:.0%}", "bad" if rate >= 0.3 else "warn" if rate >= 0.1 else "ok") if rate is not None else "-"),
                         f"{k['avg_sec']:.0f}s" if k["avg_sec"] else "-",
                         f"{k['recent_sec']:.0f}s / {k['earlier_sec']:.0f}s" if k["recent_sec"] and k["earlier_sec"] else "-"))
        st.markdown(table(["Loại", "Đang chạy", "Chờ", "Xong 1h", "Lỗi 1h", "Xong 24h", "Lỗi 24h", "Tỉ lệ lỗi 24h", "Thời gian TB", "Gần đây / trước đó"],
                          rows, cls="mon-table", num_cols=(1, 2, 3, 4, 5, 6)), unsafe_allow_html=True)
        st.caption("Mức song song tự học (tăng dần khi chạy êm, giảm một nửa khi nhà cung cấp báo quá tải 429): " + learned)
        if usage:
            st.caption("Dùng hôm nay: " + usage)
    with st.expander("🎯 Hiệu quả workflow — 5 chỉ số của dự án đang xem", expanded=False):
        effectiveness_panel(p, pid, nested=True)
    health_pill = {"🔴": ("Lỗi", "bad"), "🟡": ("Cảnh báo", "warn"), "🟢": ("Ổn", "ok")}
    with st.expander("🩺 Giám sát từng khâu — lỗi, lỗi âm thầm và chỗ chưa trơn tru trong 24h qua", expanded=False):
        dash = (lambda v: "-" if v is None else str(v))
        st.markdown(table(["Tình trạng", "Khâu", "Job", "Xong", "Lỗi", "Gen lại", "Cảnh báo", "Lỗi ghi nhận"],
                          [(Raw(D.pill(*health_pill.get(diag.health(s), ("Ổn", "ok")))), s["label"], dash(s["jobs"]), dash(s["ok"]), dash(s["failed"]),
                            dash(s["retried"]), s["warn"], s["error"]) for s in stages], cls="mon-table", num_cols=(2, 3, 4, 5)),
                    unsafe_allow_html=True)
    with st.expander(f"Sự kiện lỗi/cảnh báo gần đây ({len(events)})", expanded=False):
        st.markdown(table(["Giờ", "Mức", "Khâu", "Mã", "Lần", "Dự án", "Nội dung"],
                          [(e["last_at"][11:19], Raw(D.pill(e["severity"], "bad" if e["severity"] == "error" else "warn")), e["stage"], e["code"] or "",
                            e["count"], str(e["project_id"] or ""), e["message"]) for e in events], cls="mon-table", num_cols=(4,),
                          empty="Chưa có sự kiện"), unsafe_allow_html=True)
    with st.expander("📋 Báo cáo chẩn đoán — copy hoặc tải file, dán vào chat để sửa", expanded=False):
        text = diag.report(p.conn, C.DATA, {"Đang chạy/xếp hàng": f"{mgr.running_count()}/{mgr.queue_length()}",
                                          "Mức song song tự học": {k: v["limit"] for k, v in snap["learned"].items()}})
        st.markdown("Bấm nút copy ở góc khung dưới (hoặc tải file), dán vào chat để mình sửa. Đã che khóa/token và đường dẫn cá nhân.")
        st.download_button("⬇ Tải báo cáo (.md)", text, file_name="bao_cao_chan_doan.md", key="diag_dl")
        st.code(text, language=None)


def lessons_tab(p: Pipeline, pid: int) -> None:
    """Learning across projects: repeated mistakes and monthly research become lessons a person approves."""
    conn = p.conn
    ui.html(ui.card_title("🎓 Bài học rút ra từ các dự án", "hệ thống tự phát hiện lỗi lặp lại; bạn duyệt thì mới vào kiến thức"))
    st.caption("Lỗi lặp lại (cùng loại, nhiều lần, nhiều dự án) và tài liệu mới tìm được sẽ thành **đề xuất**. Chỉ khi bạn bấm "
               "Duyệt, đề xuất mới vào Kho kiến thức của Director/QC/Motion. Sau đó nhớ chắt lọc lại cẩm nang ở Cài đặt.")
    llm = llm_runner.client_from_env(ledger=C.DB)
    c1, c2 = st.columns(2)
    n_rules = lessons.ready_count(conn) if llm is not None else 0
    if c1.button("🔎 Rút bài học từ các lỗi đã gặp" + cost.llm_tag(cost.llm_estimate(conn, "lessons", n_rules), n_rules),
                 key="ls_mine", use_container_width=True):
        try:
            made = lessons.propose(conn, llm)
            st.success(f"Có {made} đề xuất mới." if made else "Chưa có loại lỗi nào lặp đủ nhiều để đề xuất.")
        except ERRORS as e:
            st.error(str(e))
    if c2.button("🌐 Nghiên cứu tài liệu mới ngay" + cost.llm_tag(research.estimate(conn)), key="ls_research", use_container_width=True,
                 disabled=llm is None,
                 help=f"Cần ANTHROPIC_API_KEY. Giá trên nút là mức tối đa: token Claude + tối đa {research.MAX_SEARCHES} lượt tìm web "
                      "mỗi chủ đề (0,01 USD/lượt, ghi vào sổ chi)."):
        try:
            r = research.run(conn, llm)
            st.success(f"Nghiên cứu xong: {r['proposed']} đề xuất mới." + (f" Có lỗi: {r['errors'][0]}" if r["errors"] else ""))
        except ERRORS as e:
            st.error(str(e))
    monthly = st.checkbox("Tự nghiên cứu hàng tháng (khi mở Dashboard và đã đến hạn)", value=research.enabled(conn), key="ls_monthly",
                          help="Mặc định tắt vì tốn phí. Máy phải mở Dashboard ít nhất một lần trong tháng, hoặc dùng "
                               "tools/monthly_research.py với Task Scheduler.")
    if monthly != research.enabled(conn):
        lessons.set_meta(conn, "research_monthly", "1" if monthly else "0")
    last = lessons.meta(conn, "research_last_run")
    st.caption(f"Lần nghiên cứu gần nhất: {last or 'chưa có'}. Nội dung web coi là không đáng tin: chỉ thành đề xuất, không tự áp dụng.")
    proposed = lessons.list_lessons(conn, "proposed")
    st.markdown(f"**Đề xuất chờ duyệt ({len(proposed)})**")
    for row in proposed:
        with st.container(border=True):
            ev = json.loads(row["evidence"] or "{}")
            where = knowledge.GROUPS[row["group_name"]][0]
            origin = ("nghiên cứu web: " + ", ".join(ev.get("urls", []))) if row["source"] == "research" else (
                f"{ev.get('events')} lần ở {ev.get('projects')} dự án")
            st.markdown(f"**{escape(row['title'])}** · {escape(where)}")
            st.caption(f"Nguồn: {origin}")
            title = st.text_input("Tiêu đề", row["title"], key=f"ls_t_{row['id']}", label_visibility="collapsed")
            body = st.text_area("Nội dung quy tắc", row["body"], key=f"ls_b_{row['id']}", height=100)
            a, b, _ = st.columns([1, 1, 3])
            if a.button("👍 Duyệt", key=f"ls_ok_{row['id']}", type="primary"):
                lessons.edit(conn, row["id"], title, body)
                lessons.decide(conn, row["id"], True)
                st.rerun()
            if b.button("👎 Bỏ", key=f"ls_no_{row['id']}"):
                lessons.decide(conn, row["id"], False)
                st.rerun()
    approved = lessons.list_lessons(conn, "approved")
    with st.expander(f"Bài học đã duyệt ({len(approved)})"):
        for row in approved:
            st.markdown(f"- **{escape(row['title'])}** ({row['group_name']}): {escape(row['body'])}")
            if st.button("Gỡ bài học này", key=f"ls_rm_{row['id']}"):
                lessons.decide(conn, row["id"], False)
                st.rerun()
    lessons.harvest(conn)
    rows = lessons.clusters(conn)
    with st.expander(f"Các loại lỗi đã ghi nhận ({len(rows)})"):
        if rows:
            data_table([{"Bước": r["group"], "Loại lỗi": r["label"], "Số lần": r["events"], "Số dự án": r["projects"],
                           "Đủ để đề xuất": "có" if r["ready"] else "chưa"} for r in rows], hide_index=True,
                         use_container_width=True)
        else:
            st.caption("Chưa có lỗi nào được ghi nhận (lấy từ ảnh/video bị loại kèm lý do và các lần bị risk control chặn).")
        st.caption(f"Ngưỡng đề xuất: ≥{lessons.MIN_EVENTS} lần và ≥{lessons.MIN_PROJECTS} dự án.")


def history(p: Pipeline, pid: int):
    scenes = p.conn.execute("SELECT id, idx, title FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    if not scenes:
        st.caption("Chưa có cảnh.")
        trash_section(pid)
        return
    sid = st.selectbox("Cảnh", [s["id"] for s in scenes],
                       format_func=lambda i: next(f"{s['idx']} · {s['title']}" for s in scenes if s["id"] == i))
    jobs = p.conn.execute("SELECT * FROM jobs WHERE scene_id=? ORDER BY id", (sid,)).fetchall()
    scene_expander(p, sid, expanded=False, with_motion=True)
    size = "Vừa"
    with st.container(border=True):
        ui.html(ui.card_title("Lịch sử phiên bản", "so sánh các lần gen"))
        for start in range(0, len(jobs), 3):
            cols = st.columns(3)
            for col, (n, j) in zip(cols, list(enumerate(jobs, 1))[start:start + 3]):
                with col, st.container(border=True):
                    img = job_image(j["project_id"], j["id"])
                    if img:
                        show_image(img, width="stretch")
                    elif j["type"] == "video_gen" and j["result_path"] and os.path.exists(j["result_path"]):
                        show_video(j["result_path"], size)
                    scores = qc_scores(p, j["id"])
                    qc = f" · QC {sum(s['score'] for s in scores) / len(scores):.2f}" if scores else ""
                    ui.html(f'<div class="cardhead"><b>v{n}</b><span class="grow"></span>{ui.state_badge(j["state"])}</div>'
                            f'<div class="muted">{j["type"]}{qc}' + (f' · “{j["retry_reason"]}”' if j["retry_reason"] else "") + "</div>")
    with st.expander("Nhật ký chi tiết các job"):
        for j in jobs:
            st.markdown(f"**job #{j['id']} {j['type']}** — {j['state']} (retry {j['retry_count']})")
            data_table([dict(h) for h in p.history(j["id"])], width="stretch")
    trash_section(pid)


# ---- header --------------------------------------------------------------------------
def price_editor() -> None:
    """Edit data/pricing.json in the dashboard: copy the price the Clip AI web page shows before generating."""
    with st.container():
        st.caption("Web Clip AI hiện giá cho từng thiết lập trước khi bấm gen: chỉ cần chép lại. Ưu tiên tra: "
                   "`model:mức:Ns` (giá đúng thiết lập) → `model:mức` (giá mỗi clip) → giá mỗi giây. "
                   "Để trống = chưa biết giá (Dashboard vẫn đếm số lượng).")
        pricing = cost.load_pricing()
        c1, c2 = st.columns(2)
        currency = c1.text_input("Đơn vị tiền/credit", pricing["currency"], key="price_currency")
        confirm = c2.number_input("Xác nhận khi lô từ … mục trở lên", 1, 1000, int(pricing["confirm_batch_at"]),
                                  key="price_confirm")
        rows = st.data_editor(
            cost.pricing_to_rows(pricing), num_rows="dynamic", width="stretch", hide_index=True, key="price_rows",
            column_config={
                "kind": st.column_config.SelectboxColumn("Loại", options=list(cost.PRICE_KINDS), required=True,
                                                         width="large"),
                "key": st.column_config.TextColumn("Khóa", required=True, width="large"),
                "price": st.column_config.NumberColumn("Giá", min_value=0.0, format="%.4f"),
            })
        st.caption("Loại: " + " · ".join(f"`{k}` = {v}" for k, v in cost.PRICE_KINDS.items()))
        if st.button("💾 Lưu bảng giá", key="btn_save_prices"):
            try:
                base = dict(pricing, currency=currency.strip() or "credits", confirm_batch_at=int(confirm))
                cost.save_pricing(cost.rows_to_pricing(rows.to_dict("records") if hasattr(rows, "to_dict") else rows, base))
            except ValueError as e:
                st.error(str(e))
            else:
                st.toast("Đã lưu bảng giá")
                st.rerun()
