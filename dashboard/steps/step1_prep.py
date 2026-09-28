"""Step 1 · 1b: format, resources, World Bible, image model, shot format, storyboard previz (split from step1.py, S9.5)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C

WB_LABELS = (("render_style", "Phong cách dựng hình", "vd: hoạt hình 3D mềm, không viền, chuyển sắc liên tục"),
             ("palette", "Bảng màu", "màu chủ đạo, màu điểm nhấn, phủ định (no bloom...)"),
             ("texture_finish", "Chất liệu / hoàn thiện", "hạt phim, tương phản, chất ống kính"),
             ("lighting_logic", "Logic ánh sáng (tùy chọn)", "ánh sáng đến từ nguồn nào"),
             ("era_lore", "Thời đại / thế giới (tùy chọn)", "ràng buộc để không lệch thời đại"),
             ("physics", "Vật lý / thời tiết (tùy chọn)", "mưa, trọng lực, chất liệu chuyển động thế nào"))


def world_bible_panel(p: Pipeline, pid: int) -> None:
    """Project style bible: typed, drafted by Claude from reference pictures, or taken from a saved preset; inherited by every prompt."""
    saved = style.load(p, pid)
    with st.expander("🎨 Phong cách hình ảnh (World Bible)" + (" ✓" if any(saved.values()) else " — chưa đặt"), expanded=False):
        st.caption("Khóa một bộ tham số phong cách dùng chung: Director, QC và Motion kế thừa cho **mọi** cảnh. Đặt TRƯỚC khi chạy Director. "
                   "Gõ tay, dùng mẫu đã lưu, hoặc tải 2–6 ảnh để Claude soạn nháp (skill style-analyst) rồi bạn sửa và Lưu.")
        presets = style.list_presets(p.conn)
        if presets:
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            pick = c1.selectbox("Dùng mẫu phong cách đã lưu", [None] + [x["id"] for x in presets], key=f"wb_preset_{pid}",
                                format_func=lambda i: "— chọn —" if i is None else next(x["name"] for x in presets if x["id"] == i))
            if pick is not None and c2.button("Áp dụng mẫu", key=f"wb_preset_go_{pid}"):
                style.use_preset(p, pid, pick)
                for key, _, _ in WB_LABELS:
                    st.session_state.pop(f"wb_{key}_{pid}", None)
                st.rerun()
        uploads = st.file_uploader("Ảnh tham khảo phong cách", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                   key=f"wb_up_{pid}")
        llm = llm_client()
        n_up = min(len(uploads or []), style.MAX_REFS)
        if st.button("🤖 Phân tích ảnh phong cách bằng Claude" + cost.llm_tag(cost.llm_estimate(p.conn, "style", 1, images=n_up), 1),
                     key=f"wb_run_{pid}", disabled=not uploads or llm is None, help=None if llm else claude_hint()):
            folder = project_dir(pid, "style_refs")
            paths = []
            for i, f in enumerate(uploads[:style.MAX_REFS], 1):
                path = os.path.join(folder, f"ref_{i}{os.path.splitext(f.name)[1].lower() or '.png'}")
                with open(path, "wb") as fh:
                    fh.write(f.getvalue())
                paths.append(path)
            try:
                draft = style.analyse(llm, paths, note=lambda m: diag.record(p.conn, "director", "warn", m, "bad_json_retry", pid))
            except ERRORS as e:
                st.error(str(e))
            else:
                for key, _, _ in WB_LABELS:
                    st.session_state[f"wb_{key}_{pid}"] = draft.get(key) or ""
                st.session_state[f"wb_draft_{pid}"] = draft
        draft = st.session_state.get(f"wb_draft_{pid}")
        if draft:
            st.info(draft.get("plain_note") or "Đã soạn bản nháp: xem và sửa các ô bên dưới rồi Lưu.")
            for flag in draft.get("check_flags") or []:
                st.markdown(f":orange[⚠ {escape(str(flag))}]")
            elements = draft.get("candidate_elements") or []
            if elements:
                st.markdown("**Yếu tố bầu không khí nhận ra** — tick để thêm vào “Chất liệu / hoàn thiện”:")
                for n, el in enumerate(elements):
                    if st.checkbox(f"{el.get('label', '')}: {el.get('prose', '')}", key=f"wb_el_{pid}_{n}",
                                   help=str(el.get("evidence", ""))):
                        cur = st.session_state.get(f"wb_texture_finish_{pid}", saved.get("texture_finish", ""))
                        if el.get("prose") and el["prose"] not in cur:
                            st.session_state[f"wb_texture_finish_{pid}"] = (cur + "; " if cur else "") + el["prose"]
        values = {}
        for key, label, hint in WB_LABELS:
            values[key] = st.text_area(label, value=saved.get(key, ""), key=f"wb_{key}_{pid}", placeholder=hint, height=68)
        c1, c2, c3 = st.columns([1.2, 1, 2], vertical_alignment="bottom")
        if c1.button("💾 Lưu World Bible", key=f"wb_save_{pid}", type="primary"):
            style.save(p, pid, values)
            st.success("Đã lưu. Director/Motion chạy sau sẽ dùng phong cách này.")
        if c2.button("Xóa", key=f"wb_clear_{pid}"):
            style.save(p, pid, {})
            for key, _, _ in WB_LABELS:
                st.session_state.pop(f"wb_{key}_{pid}", None)
            st.rerun()
        name = c3.text_input("Lưu làm mẫu dùng lại (tên mẫu)", key=f"wb_preset_name_{pid}", placeholder="vd FF trailer tối")
        if name.strip() and st.button("⭐ Lưu làm mẫu phong cách", key=f"wb_preset_save_{pid}"):
            act(lambda: style.save_preset(p, pid, name), f"Đã lưu mẫu “{name.strip()}”")


def assets_panel(p: Pipeline, pid: int) -> None:
    """Step 1, after the script is split: pick the resources (characters, weapons, pets, places...) that go with this script."""
    proj = p.project(pid)
    game = proj["game"]
    text = proj["script_text"] or "\n".join(json.loads(s["data"] or "{}").get("text", "") for s in
                                            p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)))
    chosen = assets.project_assets(p.conn, pid)
    chosen_ids = {a["id"] for a in chosen}
    suggested = [a for a in assets.find_in_text(p.conn, text, game, pid) if a["id"] not in chosen_ids]
    label = f"🧰 Tài nguyên đi kèm kịch bản — {len(chosen)} đã chọn" + (f" · {len(suggested)} gợi ý mới" if suggested else "")
    # S9 E1.5: open only while the project has nothing attached (suggestions alone no longer unfold it — #8 showed 3 wrong ones)
    with st.expander(label, expanded=not chosen):
        st.caption("Chọn nhân vật, vũ khí, thú cưng, bản đồ… có sẵn trong kho (hoặc tải ảnh riêng) để dùng cùng kịch bản. Director sẽ dùng đúng "
                   "tên và thiết kế này thay vì tự nghĩ ra, và ảnh của chúng là ảnh tham khảo khi gen. **Không bấm cũng được:** lúc chạy "
                   "Director, tài nguyên kịch bản nhắc đúng tên (có dấu) được tự gắn; tên trùng nhiều tài nguyên thì để bạn chọn; cái bạn đã "
                   "bỏ khỏi dự án không bị gắn lại.")
        if suggested:
            st.markdown("**Tìm thấy trong kịch bản** (gợi ý):")
            for a in suggested:
                c1, c2, c3 = st.columns([1, 6, 1.6], vertical_alignment="center")
                if a["images"]:
                    c1.image(assets.thumbnail(a["images"][0]["path"], 112), width=56)
                c2.markdown(f"**{escape(a['name'])}** · {a['kind_label']} · xuất hiện {a['mentions']} lần"
                            + (f" — {escape(a['description'][:90])}" if a["description"] else ""))
                if c3.button("➕ Dùng", key=f"as_use_{pid}_{a['id']}"):
                    assets.attach(p.conn, pid, a["id"])
                    st.rerun()
            if st.button("➕ Dùng tất cả gợi ý", key=f"as_use_all_{pid}"):
                for a in suggested:
                    assets.attach(p.conn, pid, a["id"])
                st.rerun()
        if chosen:
            st.markdown("**Đang dùng cho dự án này:**")
            for a in chosen:
                c1, c2, c3 = st.columns([1, 6, 1.4], vertical_alignment="center")
                if a["images"]:
                    c1.image(assets.thumbnail(a["images"][0]["path"], 112), width=56)
                scope = "riêng dự án" if a["project_id"] else "kho chung"
                c2.markdown(f"**{escape(a['name'])}** · {a['kind_label']} · {scope} · {len(a['images'])} ảnh")
                if c3.button("✖ Bỏ", key=f"as_drop_{pid}_{a['id']}"):
                    assets.detach(p.conn, pid, a["id"])
                    st.rerun()
        library = [a for a in assets.list_assets(p.conn, game, None, pid) if a["id"] not in chosen_ids]
        if library:
            labels = {a["id"]: f"{a['kind_label']}: {a['name']}" for a in library}
            pick = st.selectbox("Thêm từ kho", [None] + list(labels), key=f"as_pick_{pid}",
                                format_func=lambda i: "— chọn —" if i is None else labels[i])
            if pick is not None and st.button("➕ Thêm vào dự án", key=f"as_add_{pid}"):
                assets.attach(p.conn, pid, pick)
                st.rerun()
        elif not chosen:
            st.caption(f"Kho tài nguyên của game này đang trống. Người quản lý có thể thêm ở nút “⚙” (Cài đặt) → Kho tài nguyên; "
                       "hoặc bạn tải ảnh riêng ở dưới.")
        with st.container(border=True):
            st.markdown("**⬆ Tải ảnh riêng cho dự án này** (nhân vật gốc, đạo cụ…)")
            n1, n2 = st.columns([3, 2])
            name = n1.text_input("Tên", key=f"as_new_name_{pid}", placeholder="vd Lyra")
            kind = n2.selectbox("Loại", list(assets.KINDS), format_func=lambda k: assets.KINDS[k], key=f"as_new_kind_{pid}")
            desc = st.text_input("Mô tả ngắn (tùy chọn)", key=f"as_new_desc_{pid}", placeholder="tóc bạc dài, giáp xanh…")
            files = st.file_uploader("Ảnh (JPG/PNG/WebP, tối đa 10 MB mỗi ảnh)", type=["png", "jpg", "jpeg", "webp"],
                                     accept_multiple_files=True, key=f"as_new_files_{pid}")
            share = allowed("assets") and st.checkbox("Lưu cả vào kho dùng chung", key=f"as_new_share_{pid}")
            if st.button("Lưu vào dự án", key=f"as_new_go_{pid}", disabled=not (name.strip() and files)):
                try:
                    aid = assets.create(p.conn, game, kind, name, desc, "", None if share else pid, me().get("email"))
                    for f in files[: assets.MAX_IMAGES_PER_ASSET]:
                        assets.add_image(p.conn, aid, f.name, f.getvalue())
                    assets.attach(p.conn, pid, aid)
                except assets.AssetError as e:
                    st.error(str(e))
                else:
                    st.rerun()


def project_format_panel(p: Pipeline, pid: int) -> None:
    """Frame format, genre and model priority of the project: decided before the Director so every picture and clip is made for it."""
    proj = p.project(pid)
    aspect = formats.project_aspect(proj)
    genre = proj["genre"]
    prio = model_router.priority_of(proj)
    label = f"📐 Định dạng: {formats.label(aspect)} · thể loại {llm_io.GENRES.get(genre, 'chưa chọn')} · model: " \
            f"{model_router.load_profiles()['priorities'][prio]['label']}"
    with st.expander(label, expanded=aspect is None or not genre):
        c1, c2, c3 = st.columns(3)
        aspects = list(formats.ASPECTS)
        new_aspect = c1.selectbox("Tỉ lệ khung", aspects, index=aspects.index(aspect) if aspect else aspects.index(formats.DEFAULT_NEW),
                                  format_func=formats.label, key=f"fmt_aspect_{pid}",
                                  help="Ảnh (Deepix), video (Clip AI), layout và render đều theo khung này. Đổi sau khi đã có ảnh thì ảnh/video cũ sẽ báo ⚠ cũ.")
        genres = [None] + list(llm_io.GENRES)
        new_genre = c2.selectbox("Thể loại (hướng dẫn đạo diễn)", genres, index=genres.index(genre) if genre in genres else 0,
                                 format_func=lambda g: "Để Director tự chọn" if g is None else f"{g} — {llm_io.GENRES[g]}",
                                 key=f"fmt_genre_{pid}")
        prios = list(model_router.PRIORITIES)
        pr = model_router.load_profiles()["priorities"]
        new_prio = c3.selectbox("Ưu tiên model video", prios, index=prios.index(prio), key=f"fmt_prio_{pid}",
                                format_func=lambda k: pr[k]["label"], help=pr[prio]["note"])
        st.caption("Ưu tiên model theo slide ClipAI “Hôm nay tôi chọn mô hình video như thế nào”: " + pr[new_prio]["note"]
                   + " Model cụ thể được đề xuất cho TỪNG cảnh ở Bước 4, đổi được.")
        has_images = p.conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type='image_gen' AND state='approved' LIMIT 1",
                                    (pid,)).fetchone()
        if new_aspect != aspect:
            if has_images and aspect is not None:
                if confirm_all(f"fmt_aspect_ok_{pid}", [new_aspect], "Đổi tỉ lệ khung",
                               "Đã có ảnh duyệt: đổi tỉ lệ khung sẽ đánh dấu mọi ảnh/video là ⚠ cũ (cần gen lại). Đổi?", st, "Có, đổi"):
                    p.set_project_field(pid, "aspect", new_aspect)
                    st.rerun()
            else:
                p.set_project_field(pid, "aspect", new_aspect)
                st.rerun()
        if new_genre != genre:
            p.set_project_field(pid, "genre", new_genre)
            p.set_project_field(pid, "genre_locked", 1 if new_genre else 0)
            st.rerun()
        if model_router.chosen_priority(proj) is None:
            st.caption("Dự án cũ chưa chọn ưu tiên model: đang dùng Kling cho mọi cảnh.")
            if st.button("Dùng ưu tiên đã chọn ở trên", key=f"fmt_prio_set_{pid}"):
                p.set_project_field(pid, "model_priority", new_prio)
                st.rerun()
        elif new_prio != prio:
            p.set_project_field(pid, "model_priority", new_prio)
            st.rerun()
        shot_format_controls(p, pid, proj)


def image_model_control(p: Pipeline, pid: int, proj) -> None:
    """The Deepix picture model of this project (data/provider_rules.json). New pictures use it; existing ones are kept."""
    from core import image_models
    table = image_models.models()
    if not table:
        return
    options = [None] + list(table)
    cur = proj["image_model"] if "image_model" in proj.keys() and proj["image_model"] in table else None
    default = image_models.label(os.environ.get("DEEPIX_MODEL", "").strip() or image_models.DEFAULT)
    pick = st.selectbox("🖼 Model ảnh (Deepix)", options, index=options.index(cur), key=f"fmt_imgmodel_{pid}",
                        format_func=lambda m: f"Mặc định ({default})" if m is None else table[m]["label"],
                        help="Model vẽ ảnh khung đầu. Đổi model chỉ áp cho ảnh gen sau đó (ảnh đã có giữ nguyên). "
                             "Giá mỗi ảnh chưa đo — xem sổ chi sau khi chạy.")
    if pick is not None:
        st.caption(f"{table[pick].get('desc', '')} · tối đa {table[pick].get('max_refs')} ảnh tham chiếu")
    if pick != cur:
        p.set_project_field(pid, "image_model", pick)
        st.rerun()


def shot_format_controls(p: Pipeline, pid: int, proj) -> None:
    """v3: split scenes into shots (and how their clips are made) + the Free Fire editing style the Director follows."""
    from core import looks, reference_analysis, shots
    cur_look = looks.of(proj)
    options = [None] + list(looks.LOOKS)
    new_look = st.radio("🎨 Look hình", options, index=options.index(cur_look), horizontal=True, key=f"fmt_look_{pid}",
                        format_func=lambda k: "Chưa chọn" if k is None else looks.LOOKS[k]["label"],
                        help="Anime: nét vẽ anime, nhân vật giữ đúng nhận diện theo ảnh tài nguyên. Giống y hệt in-game: ảnh tài nguyên là "
                             "chuẩn tuyệt đối, video ưu tiên Kling. Đổi look khi đã có ảnh thì ảnh cũ bị đánh dấu “cũ”.")
    if new_look != cur_look:
        p.set_project_field(pid, "look", new_look)
        st.rerun()
    image_model_control(p, pid, proj)
    d1, d2 = st.columns(2)
    modes = list(shots.MODES)
    cur_mode = shots.mode(proj)
    new_mode = d1.selectbox("Cách chia cảnh", modes, index=modes.index(cur_mode), format_func=lambda m: shots.MODES[m],
                            key=f"fmt_shot_{pid}",
                            help="Chia shot: Director chia mỗi cảnh kịch bản thành nhiều shot ngắn (nhịp theo kịch bản), mỗi shot một ảnh + "
                                 "một clip. Kling multi-shot: các shot liền nhau của một nhóm cảnh gen chung một lần.")
    styles = [None] + list(reference_analysis.STYLES)
    cur_style = shots.style(proj)
    new_style = d2.selectbox("Phong cách dựng Free Fire", styles, index=styles.index(cur_style) if cur_style in styles else 0,
                             format_func=lambda s: "Chưa chọn" if s is None else reference_analysis.STYLES[s], key=f"fmt_style_{pid}",
                             help="Director học nhịp, cỡ cảnh, cách mở/kết từ video Free Fire thật của phong cách này (knowledge/ff_styles).")
    if new_mode != cur_mode:
        if shots.has_work(p.conn, pid):
            st.warning("Dự án đã có ảnh/video: đổi cách chia cảnh chỉ áp dụng khi chạy lại Director sau khi “↺ Làm lại”.")
        p.set_project_field(pid, "shot_mode", new_mode)
        st.rerun()
    if new_style != cur_style:
        p.set_project_field(pid, "style_profile", new_style)
        st.rerun()
    if new_mode:
        trim = bool(proj["dialogue_trim"]) if "dialogue_trim" in proj.keys() else False
        new_trim = st.checkbox("✂ Cho phép Director bỏ bớt câu thoại để shot đủ dài (không thêm, không sửa chữ câu giữ lại)", trim,
                               key=f"fmt_trim_{pid}", help="Kịch bản nhiều thoại trong ít giây làm shot quá ngắn (tốn tiền video). Câu bị bỏ "
                                                             "được liệt kê sau khi chạy Director; tắt thì mọi câu phải có.")
        if new_trim != trim:
            p.set_project_field(pid, "dialogue_trim", 1 if new_trim else 0)
            st.rerun()
    if new_mode and not shots.has_work(p.conn, pid) and not any(s["data"].get("shot_no") for s in shots.shots_of(p, pid)):
        st.caption("Chạy Director (1d) để chia các cảnh thành shot.")


def storyboard_panel(p: Pipeline, pid: int) -> None:
    """Previz 2D: lay out every shot on its background (people placed by perspective, by code), put them on one storyboard and let
    Claude check continuity. Nothing to approve: Step 2 simply follows the layouts; the sheet is there to look at."""
    board = os.path.join(previz.layouts_dir(C.DATA, pid), "storyboard.png")
    with st.container(border=True):
        ui.html(ui.card_title("1g · 🎬 Storyboard (dựng layout trước khi gen ảnh)",
                              "không bắt buộc · Bước 2 tự bám theo layout của cảnh nào đã dựng"))
        st.caption("Claude đọc góc máy/đường chân trời/mặt đất của ảnh bối cảnh (mỗi ảnh chỉ đọc 1 lần), đặt từng nhân vật theo "
                   "“Vị trí nhân vật” của cảnh; chương trình tự tính cỡ người theo phối cảnh và giữ chân trên mặt đất. "
                   "Chỉ cảnh đã có Background (ảnh bối cảnh trong kho) mới dựng được. Không phải duyệt: sửa blocking rồi dựng lại nếu muốn.")
        client = llm_client()
        c1, c2 = st.columns(2)
        if c1.button("🎬 Dựng storyboard", key=f"pv_plan_{pid}", disabled=client is None, type="primary",
                     help=None if client else "Cần Claude (LLM_PROVIDER=claude_cli hoặc ANTHROPIC_API_KEY)"):
            with st.spinner("Claude đang đọc ảnh nền và dựng layout…"):
                if act(lambda: st.session_state.__setitem__("pv_res", previz.plan_layouts(p, pid, client, C.DATA))):
                    r = st.session_state.pop("pv_res")
                    msg = f"Đã dựng {len(r['laid_out'])} cảnh"
                    if r["skipped"]:
                        msg += f"; bỏ qua {len(r['skipped'])} cảnh chưa có Background"
                    st.toast(msg)
                    if r["moved"]:
                        st.session_state[f"pv_moved_{pid}"] = r["moved"]
        if c2.button("🔍 Claude rà storyboard", key=f"pv_review_{pid}", disabled=client is None or not os.path.exists(board)):
            with st.spinner("Claude đang rà lỗi liên tục…"):
                act(lambda: previz.review_storyboard(p, pid, client, C.DATA))
        if client is None:
            st.caption("Chưa cấu hình Claude: đặt LLM_PROVIDER=claude_cli (dùng hạn mức Claude Code trên máy) hoặc ANTHROPIC_API_KEY.")
        moved = st.session_state.get(f"pv_moved_{pid}")
        if moved:
            st.caption("Đã kéo chân về mặt đất (vị trí Claude đặt nằm ngoài vùng đứng được): "
                       + ", ".join(f"S{i:02d} {n}" for i, n in moved))
        if os.path.exists(board):
            st.image(board, width="stretch")
            review = previz.last_review(C.DATA, pid)
            if review is not None:
                if review["ok"] and not review["issues"]:
                    st.success("Claude rà storyboard: không thấy lỗi liên tục/bố cục.")
                for issue in review["issues"]:
                    st.warning(f"S{issue['idx']:02d}: {issue['problem']}" + (f" → {issue['fix']}" if issue.get("fix") else ""))


# siblings (bottom import: the parts use each other's functions at call time only)
from dashboard.steps.step1_run import *  # noqa: F401,F403
from dashboard.steps.step1_run import _budget_summary  # noqa: F401
from dashboard.steps.step1_characters import *  # noqa: F401,F403
from dashboard.steps.step1_characters import _voices, _bible_summary, _anchor_reset  # noqa: F401
from dashboard.steps.step1_director import *  # noqa: F401,F403
from dashboard.steps.step1_director import _director_summary, _replan_button, _paid_line, _crew_notes, _director_review  # noqa: F401
