"""Step 1: script, resources, run mode, Director, Character Bible, storyboard, World Bible."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C



@st.fragment(run_every=5)
def autopilot_progress(pid: int) -> None:
    """Live progress (refreshes itself every 5 s while the page is open; the run itself lives in a background thread)."""
    p = Pipeline(connect(C.DB))
    info = autopilot.status(p, pid)
    state = info["state"]
    tag = {"queued": ("xếp hàng", "b-warn"), "running": ("đang chạy", "b-info"), "done": ("hoàn tất", "b-ok"), "needs_attention": ("cần bạn xử lý", "b-warn"),
           "stopped": ("đã dừng", "b-warn"), "error": ("lỗi", "b-bad"), "waiting": ("chờ bạn duyệt", "b-pri")}.get(state, (state, ""))
    ui.html(ui.badge(*tag) + f' <span class="muted">{escape(info["note"])}</span>')
    for label, done, total in autopilot.progress(p, pid, C.DATA):
        st.progress(0 if not total else min(done / total, 1.0), text=f"{label}: {done}/{total}")
    if info["log"]:
        st.caption(" · ".join(f"{e['at']} {e['msg']}" for e in info["log"][-4:]))
    mgr = autopilot_manager(C.DB, C.DATA)
    stale = (autopilot.is_stale(p, pid, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
             or (state == "queued" and not mgr.queued(pid) and not mgr.alive(pid)))
    if stale:
        st.warning("Không thấy tiến trình chạy nền (có thể máy chủ vừa khởi động lại). Bấm “Tiếp tục”.")
    if state == "queued" and not stale:
        if st.button("■ Bỏ khỏi hàng đợi", key=f"ap_unqueue_{pid}"):
            autopilot.stop(p, pid)
            st.rerun()
    elif state == "running" and not stale:
        c1, c2 = st.columns(2)
        if c1.button("⏸ Tạm dừng", key=f"ap_pause_{pid}"):
            p.set_paused(pid, True)
        if c2.button("■ Dừng hẳn", key=f"ap_stop_{pid}"):
            autopilot.stop(p, pid)
            st.rerun()
    elif state in ("needs_attention", "stopped", "error", "waiting") or stale:
        label = "✔ Đã duyệt — tiếp tục" if state == "waiting" else "▶ Tiếp tục"
        if st.button(label, key=f"ap_resume_{pid}", type="primary"):
            autopilot.resume(p, pid, p.actor)
            autopilot_manager(C.DB, C.DATA).start(pid)
            st.rerun()
    if state == "done":
        out = os.path.join(C.DATA, str(pid), "output", "FINAL_VIDEO.mp4")
        if os.path.exists(out):
            show_video(out)


def autopilot_panel(p: Pipeline, pid: int) -> None:
    """Fully automatic mode: approve the scene breakdown (and, by default, the Character Bible), the rest runs by itself."""
    if not allowed("autopilot"):
        return
    info = autopilot.status(p, pid)
    with st.container(border=True):
        ui.html(ui.card_title("🚀 Tự động hoàn toàn", "bạn duyệt phân cảnh (và nhân vật), phần còn lại tự chạy"))
        if info["state"] in ("queued", "running", "done", "needs_attention", "stopped", "error", "waiting"):
            autopilot_progress(pid)
            if info["state"] not in ("running", "queued"):
                with st.expander("Chạy lại từ đầu cho dự án này"):
                    st.caption("Đặt lại trạng thái tự động (ảnh/video đã làm được giữ nguyên).")
                    if st.button("↺ Đặt lại chế độ tự động", key=f"ap_reset_{pid}"):
                        autopilot.reset(p, pid, C.DATA)
                        st.rerun()
            return
        st.caption("Chuỗi: Director → (dừng để bạn duyệt nhân vật, nếu bật) → dựng layout → ảnh + Claude QC → QC đồng bộ cả bộ → "
                   "(dừng để bạn duyệt storyboard, nếu bật) → motion prompt + rà prompt → giọng thoại → chọn model từng cảnh → video + QC video → nhạc, hiệu ứng → "
                   "bản giao (phụ đề, card cuối, bản xuất theo thiết lập ở Bước 5). Gặp việc cần người thì **dừng và báo**.")
        gates = autopilot.get_gates(p, pid)
        g1, g2 = st.columns(2)
        bible = g1.checkbox("Dừng để duyệt Character Bible + Character Lock + giọng + ảnh mốc trước khi gen", gates["bible"],
                            key=f"ap_gate_bible_{pid}", help="Nên bật: sai mô tả nhân vật sẽ lan ra MỌI cảnh (bài học từ lần hậu kiểm 2026-09-23).")
        pilot = g2.checkbox("Gen thử 2–3 cảnh đại diện trước, dừng để bạn xem rồi mới gen hết", gates["pilot"], key=f"ap_gate_pilot_{pid}",
                            help="Tiết kiệm credit ở dự án nhiều cảnh: lỗi phong cách/nhân vật lộ ra ở mẫu thử thay vì ở cả lô.")
        board = st.checkbox("Dừng ở **storyboard** (xem cả bộ ảnh khung đầu) trước khi gen video", gates["storyboard"],
                            key=f"ap_gate_board_{pid}",
                            help="Nên bật: ở đợt thử GĐ6 ~70% tiền video trả cho clip làm từ ảnh mà lỗi đã nhìn thấy trước (sai nhân vật, "
                                 "sai cỡ cảnh, nhóm multi-shot thiếu nhân vật). Xem ảnh không tốn tiền; gen video thì có.")
        if (bible, pilot, board) != (gates["bible"], gates["pilot"], gates["storyboard"]):
            autopilot.set_gates(p, pid, {"bible": bible, "pilot": pilot, "storyboard": board})
        issues = autopilot.problems(p, pid)
        for msg in issues:
            st.markdown(f":red[✖ {msg}]")
        scenes = p.conn.execute("SELECT COUNT(*) c FROM scenes WHERE project_id=?", (pid,)).fetchone()["c"]
        per = p.project(pid)["max_retry_count"] + 2
        run_est = None
        try:
            run_est = cost.estimate_run(p, pid)
        except Exception as e:  # noqa: BLE001 - never hide the button because an estimate failed; say it
            st.warning(f"Không ước tính được chi phí chạy tự động ({type(e).__name__}: {e}).")
        if not issues:
            st.success(f"Sẵn sàng: {scenes} cảnh. Trần an toàn: tối đa {scenes * per} job ảnh và {scenes * per} job video (kể cả gen lại).")
        if run_est is not None:
            st.info("💵 Ước tính chạy tự động: " + cost.format_run_estimate(run_est).replace("$", "\\$")
                    + ("  ·  🧪 chế độ Thử rẻ đang BẬT" if p.project(pid)["test_quality"] else ""))
        tag = f" (≈ {run_est['total']:.2f} USD)" if run_est is not None else ""
        if confirm_all(f"ap_start_{pid}", ["go"], "✔ Duyệt phân cảnh & chạy tự động" + tag,
                       "Bắt đầu chạy tự động? Sẽ gọi Deepix, Clip AI và Claude thật (tốn credit"
                       + (f", ước tính ≈ {run_est['total']:.2f} USD, tối đa ≈ {run_est['max']:.2f} USD" if run_est is not None else "")
                       + "). Trong lúc chạy, dự án chuyển sang “QC tự duyệt theo ngưỡng”; dừng hoặc xong sẽ trả lại cách duyệt cũ.",
                       st, "Có, chạy") and not issues:
            autopilot.start(p, pid, p.actor)
            autopilot_manager(C.DB, C.DATA).start(pid)
            st.rerun()
        if issues:
            st.caption("Hãy xử lý các mục đỏ ở trên trước khi bấm chạy.")


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
    with st.expander(label, expanded=bool(suggested) or bool(chosen)):
        st.caption("Chọn nhân vật, vũ khí, thú cưng, bản đồ… có sẵn trong kho (hoặc tải ảnh riêng) để dùng cùng kịch bản. Director sẽ dùng đúng "
                   "tên và thiết kế này thay vì tự nghĩ ra, và ảnh của chúng là ảnh tham khảo khi gen.")
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


def script_html(text: str) -> str:
    """Whole script as a scrollable block; scene headings in bold so the scenes can be found at a glance."""
    lines = []
    for line in text.splitlines():
        safe = escape(line)
        lines.append(f"<b>{safe}</b>" if script_parser._HEADING.match(line) else safe)
    return '<div class="scriptfull">' + "\n".join(lines) + "</div>"


def _count_label(p: Pipeline, pid: int, scenes) -> str:
    """'3 cảnh' (v2) or '3 cảnh · 25 shot' (v3 shot rows)."""
    from core import shots
    if scenes and any(json.loads(s["data"] or "{}").get("shot_no") for s in scenes):
        return f"{shots.story_scene_count(p, pid)} cảnh · {len(scenes)} shot"
    return f"{len(scenes)} cảnh"


def step1(p: Pipeline, pid: int):
    proj = p.project(pid)
    scenes = p.conn.execute("SELECT idx, title, state, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    chars = p.conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,)).fetchall()
    warnings = preflight.check_characters(p.conn, pid, preflight.load_blocklist()) if chars else []
    risky = {w["character"] for w in warnings}
    char_names = [c["name"] for c in chars]
    locked = any(c["locked"] for c in chars)
    stale = len(lineage.stale_scene_ids(p.conn, pid)) if scenes else 0
    step_header("Bước 1 · Kịch bản & đạo diễn", "tách cảnh → chuẩn bị → Director → nhân vật → thoại → khóa",
                _count_label(p, pid, scenes) + f" · {len(chars)} nhân vật" + (" · đã khóa" if locked else ""), stale)

    with st.container(border=True):
        ui.html(ui.card_title("1a · 📜 Kịch bản", "toàn văn (trái) · chia theo cảnh (phải)"))
        if st.session_state.get("parse_warn") and scenes:
            st.warning(st.session_state["parse_warn"])
        t_file, t_text = st.tabs(["📎 Tải file", "✍ Gõ / dán văn bản"])
        with t_file:
            up = st.file_uploader("Kịch bản", type=list(script_reader.SUPPORTED), key=f"up_{pid}", label_visibility="collapsed",
                                  help="Word (.docx, kể cả kịch bản viết trong bảng), Excel (.xlsx), CSV/TSV, .txt, .md")
            st.caption("Đọc được: Word (.docx, cả bảng), Excel (.xlsx), CSV/TSV, .txt, .md. Kịch bản dạng bảng cần dòng tiêu đề cột như "
                       "Cảnh, Mô tả, Nhân vật, Lời thoại, Bối cảnh, Thời gian, Góc máy.")
        with t_text:
            pasted = st.text_area("Gõ hoặc dán kịch bản", key=f"paste_{pid}", height=170, label_visibility="collapsed",
                                  placeholder="CẢNH 1 - ĐÊM, RỪNG ELDER\nSương mù phủ kín khu rừng…\nLYRA: Có thứ gì đó đang theo chúng ta.\n\n"
                                              "Dán cả bảng copy từ Excel / Google Sheets cũng được.")
        u2, u3, u4 = st.columns([2.4, 1.2, 4], vertical_alignment="center")
        has_input = up is not None or bool(pasted.strip())
        if u2.button("▶ Phân tích (tách cảnh)", disabled=not has_input, type="primary", key=f"btn_analyse_{pid}"):
            def analyse():
                res = script_reader.read_script(up.name, up.getvalue()) if up is not None else script_reader.from_text(pasted)
                parsed = script_parser.split_scenes(res.paragraphs)
                script_parser.import_scenes(p, pid, parsed, full_text="\n\n".join(res.paragraphs))
                st.session_state["parse_info"] = res.info
                if len(parsed) == 1 and parsed[0].heading == "Mở đầu":
                    st.session_state["parse_warn"] = ("Không thấy tiêu đề cảnh (vd “Cảnh 1”, “Scene 2”, “INT./EXT.”): "
                                                      "cả kịch bản thành 1 cảnh. Hãy thêm/sửa cảnh thủ công.")
                st.toast(f"Đã tách {len(parsed)} cảnh")
            if act(analyse):
                st.rerun()
        u4.caption("Nếu có cả file lẫn văn bản, hệ thống dùng file." if has_input else "Chọn file hoặc dán văn bản, rồi bấm Phân tích.")
        if st.session_state.get("parse_info") and scenes:
            with st.expander("Hệ thống đã đọc kịch bản thế nào (kiểm tra lại)"):
                for line in st.session_state["parse_info"]:
                    st.caption("• " + line)
        with u3:
            if confirm_all(f"btn_bad_reset_{pid}", ["reset"], "↺ Làm lại",
                           "Xóa các cảnh CHƯA có ảnh/video và các nhân vật CHƯA khóa để tách lại kịch bản? Cảnh đã có ảnh được giữ.",
                           st, "Có, xóa"):
                p.conn.execute("DELETE FROM characters WHERE project_id=? AND locked=0", (pid,))
                p.conn.execute("DELETE FROM motion_prompts WHERE scene_id IN (SELECT id FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs))", (pid,))
                p.conn.execute("DELETE FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs)", (pid,))
                p.conn.commit()
                if not p.conn.execute("SELECT 1 FROM scenes WHERE project_id=?", (pid,)).fetchone():
                    p.set_script_text(pid, None)
                    p.conn.execute("DELETE FROM story_scenes WHERE project_id=?", (pid,))
                    p.conn.commit()
                st.session_state.pop("parse_info", None)
                st.rerun()
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("**Kịch bản đầy đủ**")
            full = proj["script_text"] or "\n\n".join((json.loads(s["data"] or "{}").get("text") or s["title"] or "") for s in scenes)
            if full.strip():
                ui.html(script_html(full))
            else:
                st.caption("Chưa có kịch bản: tải file hoặc gõ/dán văn bản rồi bấm Phân tích.")
        with right:
            st.markdown("**Chia theo cảnh** · bấm vào từng cảnh để xem và sửa")
            if scenes:
                scene_list(p, pid, scenes, char_names)
    ui.html(ui.card_title("1b · 🧰 Chuẩn bị", "làm TRƯỚC Director: định dạng, tài nguyên, phong cách"))
    project_format_panel(p, pid)
    if scenes:
        assets_panel(p, pid)
    if C.expert():
        world_bible_panel(p, pid)

    if scenes:
        ui.html(ui.card_title("1c · Chọn cách chạy", "tự động hoàn toàn, hoặc lần lượt từng bước"))
        auto_col, manual_col = st.columns(2, gap="large")
        with auto_col:
            autopilot_panel(p, pid)
        with manual_col, st.container(border=True):
            ui.html(ui.card_title("🧭 Lần lượt từng bước", "bạn kiểm soát và duyệt ở mỗi bước"))
            st.caption("1d Director → 1e Character Bible (Lock, giọng, ảnh mốc) → 1f Rà thoại → 1g Storyboard (tùy chọn) → khóa & sang Bước 2 "
                       "→ Bước 3 motion + giọng thoại → Bước 4 video → Bước 5 âm thanh & xuất bản. Hợp với dự án dài hoặc cần chỉnh kỹ.")
        director_panel(p, pid, chars)
    if chars:
        character_bible_panel(p, pid, chars, risky)
        dialogue_review_panel(p, pid)
        if C.expert():
            storyboard_panel(p, pid)
        with st.container(border=True):
            a, b = st.columns([2, 1], vertical_alignment="center")
            missing_anchor = [c["name"] for c in chars if not c["anchor_approved"]]
            a.caption("Xong nhân vật (và storyboard nếu dựng): duyệt & khóa rồi sang Bước 2."
                      + (f" Chưa duyệt ảnh mốc: {', '.join(missing_anchor)}." if missing_anchor else ""))
            b.button("✔ Duyệt & khóa → Bước 2", type="primary", key=f"lock_go_{pid}", on_click=_lock_and_go, args=(p, pid))
            if st.session_state.get("lock_error"):
                st.error(st.session_state.pop("lock_error"))


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


def character_reference_panel(p: Pipeline, pid: int, chars) -> None:
    """Character Bible: the reference picture(s) of each character, visible here and changeable (this is what image generation copies)."""
    linked = assets.link_characters(p.conn, pid, [c["name"] for c in chars])
    pool = [a for a in assets.project_assets(p.conn, pid) if a["kind"] in ("character", "pet") and a["images"]]
    saved = {r["name"]: r for r in p.conn.execute("SELECT name, ref_asset_id, ref_image_id, ref_image_ids FROM characters WHERE project_id=?", (pid,))}
    have = sum(1 for a in linked.values() if a)
    with st.expander(f"🖼 Ảnh tham chiếu của từng nhân vật — {have}/{len(chars)} đã có", expanded=have < len(chars) or not pool):
        st.caption("Đây là (những) ảnh mà bước gen ảnh sẽ **bám theo** (gương mặt, tóc, trang phục). Mặc định tự chọn theo tên, ưu tiên ảnh MỘT người rõ mặt "
                   "(không phải cả tấm bảng nhiều tư thế) và lấy thêm góc/chi tiết thứ hai nếu có, để nhân vật không bị lẫn với người khác trong cảnh. "
                   "Bạn đổi được sang tài nguyên khác, hoặc tự chọn 1-2 ảnh cụ thể. Muốn thêm tài nguyên, chọn ở mục “🧰 Tài nguyên đi kèm kịch bản” phía trên.")
        if not pool:
            st.warning("Dự án chưa chọn tài nguyên nhân vật nào, nên ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế). Chọn ở “🧰 Tài nguyên đi kèm kịch bản”.")
        options = ["auto", "none"] + [a["id"] for a in pool]
        labels = {"auto": "Tự động (theo tên)", "none": "Không dùng ảnh (vẽ theo mô tả)", **{a["id"]: f"{a['name']} ({len(a['images'])} ảnh)" for a in pool}}
        for c in chars:
            row = saved.get(c["name"])
            a = linked[c["name"]]
            with st.container(border=True):
                left, right = st.columns([1.1, 3], vertical_alignment="top")
                if a:
                    left.image([assets.thumbnail(img["path"], 220) for img in a["refs"]], width=105)
                else:
                    left.caption("— chưa có ảnh")
                right.markdown(f"**{escape(c['name'])}** — " + (f"dùng {len(a['refs'])} ảnh của **{escape(a['name'])}**" if a else "vẽ theo mô tả chữ"))
                mode = "auto" if row["ref_asset_id"] is None else ("none" if row["ref_asset_id"] == 0 else row["ref_asset_id"])
                if mode not in options:
                    mode = "auto"
                pick = right.selectbox("Ảnh tham chiếu lấy từ", options, options.index(mode), format_func=lambda o: labels[o], key=f"cref_{pid}_{c['name']}")
                new_asset = None if pick == "auto" else (0 if pick == "none" else pick)
                if pick != mode:                                     # another source picked: save it (automatic picture choice until chosen otherwise)
                    assets.set_character_link(p.conn, pid, c["name"], new_asset, None, None)
                    _anchor_reset(p, pid, c["name"])
                    st.rerun()
                shown = a if pick == "auto" else next((x for x in pool if x["id"] == pick), None)
                if shown and len(shown["images"]) > 1:
                    numbers = list(range(1, len(shown["images"]) + 1))
                    current_ids = {img["id"] for img in a["refs"]} if a and a["id"] == shown["id"] else set()
                    default = [i for i, img in enumerate(shown["images"], 1) if img["id"] in current_ids] or [1]
                    chosen_nums = right.multiselect("Dùng ảnh số (chọn 1-2 ảnh rõ mặt, nhiều góc/chi tiết thì càng chuẩn)", numbers, default,
                                                    key=f"cimg_{pid}_{c['name']}")
                    right.image([assets.thumbnail(img["path"], 160) for img in shown["images"]], width=70, caption=[str(i) for i in numbers])
                    if chosen_nums and set(chosen_nums) != set(default):
                        ids = [shown["images"][i - 1]["id"] for i in sorted(chosen_nums)]
                        assets.set_character_link(p.conn, pid, c["name"], shown["id"], ids[0], ids)
                        _anchor_reset(p, pid, c["name"])
                        st.rerun()
                outfit_panel(p, pid, c["name"], right)


def outfit_panel(p: Pipeline, pid: int, name: str, box) -> None:
    """A different outfit for this video, from pictures + text: pick outfit picture(s) from the library (another skin, a costume photo),
    optionally generate a 2-picture character set wearing it (it then becomes the reference; nothing to approve)."""
    current = assets.outfit_images(p.conn, pid, name)
    with box.popover("👗 Trang phục cho video này" + (f" — đang dùng {len(current)} ảnh" if current else ""), width="stretch"):
        st.caption("Muốn nhân vật mặc trang phục khác (skin khác, đồ theo kịch bản): chọn ảnh trang phục trong kho. Khi gen, mặt/tóc lấy từ ảnh "
                   "nhân vật, quần áo lấy từ ảnh trang phục. Mô tả thêm bằng chữ ở ô “Trang phục / dấu hiệu” (mục ✏ Sửa nhân vật).")
        pool = [a for a in assets.project_assets(p.conn, pid) if a["images"]]
        by_id = {img["id"]: (a, n) for a in pool for n, img in enumerate(a["images"], 1)}
        chosen = st.multiselect("Ảnh trang phục", list(by_id), [i["id"] for i in current if i["id"] in by_id],
                                format_func=lambda i: f"{by_id[i][0]['name']} · ảnh {by_id[i][1]}", key=f"outfit_{pid}_{name}",
                                max_selections=2)
        if chosen:
            st.image([assets.thumbnail(by_id[i][0]["images"][by_id[i][1] - 1]["path"], 160) for i in chosen], width=70)
        if [i["id"] for i in current] != chosen and st.button("💾 Lưu trang phục", key=f"outfit_save_{pid}_{name}"):
            assets.set_outfit(p.conn, pid, name, chosen)
            st.rerun()
        runner = image_runner(p) if current else None
        if current and st.button("🧍 Tạo bộ ảnh nhân vật mặc trang phục này (2 ảnh Deepix)", key=f"outfit_set_{pid}_{name}",
                                 disabled=runner is None, help="Chính diện + góc 3/4, toàn thân. Tạo xong tự thành ảnh tham chiếu của nhân vật "
                                                               "trong dự án này, mọi cảnh bám theo cùng một bộ; đổi lại được ở ô “Ảnh tham chiếu lấy từ”."):
            with st.spinner("Deepix đang vẽ bộ ảnh nhân vật (khoảng 1 phút)…"):
                if act(lambda: costume.make_character_set(p, pid, name, runner.provider, C.DATA), f"Đã tạo bộ ảnh cho {name}"):
                    st.rerun()


def subject_panel(p: Pipeline, pid: int, chars) -> None:
    """Seedance Subject Library: upload each character once, then attach it to Seedance videos."""
    proj = p.project(pid)
    rows = p.conn.execute("SELECT name, subject_asset_id, subject_status, subject_name FROM characters"
                          " WHERE project_id=?", (pid,)).fetchall()
    active = sum(1 for r in rows if r["subject_status"] == "active")
    with st.expander(f"🧩 Kho chủ thể Seedance — {active}/{len(rows)} nhân vật đã có"):
        catalog = subjects.games()
        keys = list(catalog)
        game = st.selectbox("Game / loại nội dung của dự án", keys,
                            index=keys.index(proj["game"]) if proj["game"] in keys else 0,
                            format_func=lambda k: catalog[k][0], key=f"game_{pid}")
        if game != proj["game"]:
            p.set_game(pid, game)
        if subjects.is_covered(game):
            st.success("Free Fire đã ký thỏa thuận bản quyền với Clip AI: chủ thể ở trạng thái active đã qua duyệt "
                       "người thật + bản quyền, dùng được trong Seedance.")
        else:
            st.warning("Game / nội dung này chưa có thỏa thuận bản quyền: chủ thể active chỉ qua duyệt người thật; "
                       "khi gen vẫn có thể bị chặn bản quyền.")
        with st.expander("➕ Thêm game / loại nội dung khác"):
            g_key = st.text_input("Mã ngắn (vd AOV, MV_CA_SI)", key=f"gnew_key_{pid}")
            g_label = st.text_input("Tên hiển thị", key=f"gnew_label_{pid}")
            g_cov = st.checkbox("Đã ký thỏa thuận bản quyền với Clip AI", False, key=f"gnew_cov_{pid}",
                                help="Chỉ tick khi thật sự có thỏa thuận; ảnh hưởng thông báo hiển thị.")
            if st.button("Thêm", key=f"gnew_{pid}", disabled=not (g_key.strip() and g_label.strip())):
                if act(lambda: subjects.add_game(g_key, g_label, g_cov), "Đã thêm"):
                    st.rerun()
        st.dataframe([{"Nhân vật": r["name"], "Trạng thái": subjects.STATUS_LABEL.get(r["subject_status"], r["subject_status"]),
                       "Tên trên kho": r["subject_name"] or ""} for r in rows], width="stretch", hide_index=True,
                     height=min(38 * (len(rows) + 1) + 3, 200))
        try:
            library = factory.subject_library()
        except ProviderError as e:
            st.error(f"Clip AI: {e}")
            return
        if library is None:
            st.caption("Cần CLIPAI_TOKEN và VIDEO_PROVIDER=clipai (hoặc SUBJECT_PROVIDER=mock để thử) để tải lên kho.")
            return
        who = st.selectbox("Nhân vật", [r["name"] for r in rows], key=f"subj_who_{pid}")
        up = st.file_uploader("Ảnh nhân vật (JPG / PNG / WebP)", type=["jpg", "jpeg", "png", "webp"],
                              key=f"subj_up_{pid}_{who}")
        default_name = f"{game}_{who}".replace(" ", "_")  # any name is fine; the prefix just keeps the library tidy
        name = st.text_input("Tên trên kho", default_name, key=f"subj_name_{pid}_{who}")
        b1, b2, b3 = st.columns(3)
        if b1.button("⬆ Tải lên kho chủ thể", disabled=up is None, key=f"subj_go_{pid}", type="primary"):
            suffix = os.path.splitext(up.name)[1] or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(up.getvalue())
            try:
                with st.spinner("Đang tải lên và chờ kho duyệt (có thể mất 1–3 phút)…"):
                    ok = act(lambda: subjects.link(p, pid, who, library.upload(f.name, name)), f"Đã có chủ thể cho {who}")
            finally:
                os.remove(f.name)
            if ok:
                st.rerun()
        if b2.button("⟳ Cập nhật trạng thái", key=f"subj_refresh_{pid}"):
            act(lambda: st.toast(f"{subjects.refresh(p, pid, library)} chủ thể vừa active"))
            st.rerun()
        if b3.button("Gỡ liên kết", key=f"subj_unlink_{pid}", help="Chỉ bỏ liên kết trong dự án; ảnh vẫn ở kho Clip AI"):
            subjects.unlink(p, pid, who)
            st.rerun()
        with st.expander("📥 Nhập chủ thể đã có trên kho"):
            try:
                assets = [a for a in library.list_assets("image") if a.get("asset_id")]
            except ProviderError as e:
                st.error(str(e))
                assets = []
            if not assets:
                st.caption("Kho chưa có ảnh nào (hoặc không đọc được).")
            else:
                pick = st.selectbox("Chủ thể trên kho", assets, key=f"subj_pick_{pid}",
                                    format_func=lambda a: f"{a.get('name')} · {a.get('provider_status')}")
                if st.button(f"Gắn cho {who}", key=f"subj_link_{pid}"):
                    act(lambda: subjects.link(p, pid, who, pick), f"Đã gắn cho {who}")
                    st.rerun()


def _acting_inputs(d, k, lk):
    """GĐ4 (director.md Đ4, dp.md Q7): the acting of a shot and the DP's reason, editable by hand (English for the models, the motive
    in Vietnamese). Returns (performance dict or {} to clear, why text)."""
    p0 = d.get("performance") if isinstance(d.get("performance"), dict) else {}
    st.markdown("**🎭 Diễn xuất của shot**" + lk("performance") + " — tả việc mặt/mắt/người làm (tiếng Anh), không chỉ tên cảm xúc")
    c1, c2, c3 = st.columns([1, 3, 3])
    level = c1.selectbox("Cường độ", [0, 1, 2, 3, 4, 5], index=int(p0.get("intensity") or 0), key=f"{k}_pint",
                         help="Độ mạnh của khoảnh khắc (1 gần như không thấy · 3 rõ tự nhiên · 5 đỉnh của phim). Cận: code tự vẽ nhỏ hơn 1 bậc.")
    face = c2.text_input("Mặt (face)", p0.get("face") or "", key=f"{k}_pface")
    eyes = c3.text_input("Mắt (eyes)", p0.get("eyes") or "", key=f"{k}_peyes")
    c4, c5, c6 = st.columns(3)
    body = c4.text_input("Người (body)", p0.get("body") or "", key=f"{k}_pbody")
    timing = c5.text_input("Nhịp (timing)", p0.get("timing") or "", key=f"{k}_ptime")
    listener = c6.text_input("Người nghe (listener)", p0.get("listener") or "", key=f"{k}_plisten")
    motive = st.text_input("Động cơ (vì sao — tiếng Việt)", p0.get("motive") or "", key=f"{k}_pmotive")
    why = st.text_input("🎥 Vì sao chọn góc/chuyển động này (Quay phim)" + lk("why"), d.get("why") or "", key=f"{k}_why")
    perf = {"intensity": level or None, "face": face, "eyes": eyes, "body": body, "timing": timing, "listener": listener, "motive": motive}
    return {x: v for x, v in perf.items() if v}, why


def scene_editor(p: Pipeline, pid: int, scene, char_names) -> None:
    """Detail of one scene: script text and spec (all editable). A field you change is kept when the Director runs again (🔒)."""
    idx = scene["idx"]
    d = json.loads(scene["data"] or "{}")
    k = f"sd_{pid}_{idx}"
    locked = set(d.get("_user_locked") or [])
    lk = lambda name: " 🔒" if name in locked else ""  # noqa: E731
    text = st.text_area("Nội dung kịch bản của cảnh", d.get("text", ""), key=f"{k}_text", height=110)
    c1, c2, c3 = st.columns(3)
    location = c1.text_input("Địa điểm" + lk("location"), d.get("location", ""), key=f"{k}_location")
    time_ = c2.text_input("Thời gian" + lk("time"), d.get("time", ""), key=f"{k}_time")
    shot = c3.text_input("Cỡ cảnh / góc máy" + lk("shot"), d.get("shot", ""), key=f"{k}_shot")
    c4, c5 = st.columns(2)
    mood = c4.text_input("Mood" + lk("mood"), d.get("mood", ""), key=f"{k}_mood")
    lighting = c5.text_input("Ánh sáng" + lk("lighting"), d.get("lighting", ""), key=f"{k}_lighting")
    intent = st.text_input("💡 Ý đồ cảm xúc (người xem phải cảm thấy gì)" + lk("emotional_intent"), d.get("emotional_intent") or "",
                           key=f"{k}_intent")
    cast = st.multiselect("Nhân vật trong cảnh" + lk("characters"), char_names, [c for c in d.get("characters") or [] if c in char_names],
                          key=f"{k}_cast")
    c6, c7 = st.columns([4, 1])
    blocking = c6.text_input("🧍 Vị trí nhân vật (blocking)" + lk("blocking"), d.get("blocking") or "", key=f"{k}_blocking",
                             help="Ai đứng bên trái/giữa/phải khung, tiền/hậu cảnh, nhìn về đâu. Các cảnh cùng nhóm giữ nguyên bên trái/phải.")
    seq_value = d.get("sequence") if isinstance(d.get("sequence"), int) else 0
    sequence = c7.number_input("Nhóm cảnh" + lk("sequence"), min_value=0, value=seq_value, step=1, key=f"{k}_seq",
                               help="Các cảnh liên tiếp cùng nơi, liền mạch dùng chung 1 số (0 = không nhóm).")
    c8, c9, c10 = st.columns(3)
    comp_opts = [None, "simple", "complex"]
    complexity = c8.selectbox("Độ phức tạp máy/hành động" + lk("camera_complexity"), comp_opts,
                              index=comp_opts.index(d.get("camera_complexity")) if d.get("camera_complexity") in comp_opts else 0,
                              format_func=lambda v: {None: "—", "simple": "Đơn giản", "complex": "Phức tạp (đánh nhau, đuổi, nhiều người)"}[v],
                              key=f"{k}_cx")
    role_opts = [None, "hero", "normal", "transition"]
    role = c9.selectbox("Vai trò cảnh" + lk("shot_role"), role_opts,
                        index=role_opts.index(d.get("shot_role")) if d.get("shot_role") in role_opts else 0,
                        format_func=lambda v: {None: "—", "hero": "⭐ Then chốt", "normal": "Thường", "transition": "Chuyển tiếp"}[v],
                        key=f"{k}_role")
    duration = c10.number_input("Thời lượng đề xuất (giây)" + lk("duration_s"), 0, 15, int(d.get("duration_s") or 0), 1, key=f"{k}_dur",
                                help="0 = để Director/Motion quyết")
    places = {a["id"]: a for a in assets.project_assets(p.conn, pid) if a["kind"] == "location" and a["images"]}
    current = d.get("location_asset")
    if isinstance(current, int) and current not in places:
        extra = assets.get(p.conn, current)
        if extra is not None and extra["images"]:
            places[current] = extra
    options = [None] + list(places)
    by_name = assets.scene_location(p.conn, pid, dict(d, location_asset=None))
    auto_label = f"Tự động theo tên địa điểm ({by_name['name']})" if by_name else "Tự động theo tên địa điểm (chưa khớp bối cảnh nào)"
    bg = st.selectbox("🏞 Background (ảnh in-game gửi kèm khi gen ảnh)" + lk("location_asset"), options,
                      index=options.index(current) if current in options else 0, key=f"{k}_bg",
                      format_func=lambda i: auto_label if i is None else places[i]["name"],
                      help="Chọn bối cảnh trong Kho tài nguyên của dự án. Để tự động thì dùng bối cảnh có tên nằm trong ô Địa điểm.")
    st.markdown("**🗣 Thoại của cảnh**" + lk("dialogue"))
    from core import voice_direction
    hows = voice_direction.deliveries(d)
    rows = [{"Người nói": w, "Lời thoại": t, "Nhịp giọng": ((hows[i] or {}).get("pace") or "") if i < len(hows) else "",
             "Cường độ giọng": ((hows[i] or {}).get("intensity") or 0) if i < len(hows) else 0,
             "Ngắt trước": bool((hows[i] or {}).get("pause_before")) if i < len(hows) else False}
            for i, (w, t) in enumerate(dialogue.scene_lines(d))]
    lines_edit = st.data_editor(rows or [{"Người nói": "", "Lời thoại": "", "Nhịp giọng": "", "Cường độ giọng": 0, "Ngắt trước": False}],
                                num_rows="dynamic", hide_index=True, width="stretch", key=f"{k}_dlg", column_config={
                                    "Người nói": st.column_config.SelectboxColumn(options=char_names + ["NARRATOR"], width="small"),
                                    "Nhịp giọng": st.column_config.SelectboxColumn(options=["", "slow", "normal", "fast"], width="small",
                                                                                   help="Chỉ đạo giọng (Đạo diễn Đ5) — dùng khi cờ voice_direction bật"),
                                    "Cường độ giọng": st.column_config.NumberColumn(min_value=0, max_value=5, step=1, width="small",
                                                                                   help="0 = không chỉ đạo; 5 = đỉnh (giọng biểu cảm nhất)"),
                                    "Ngắt trước": st.column_config.CheckboxColumn(width="small")})
    perf, why_text = _acting_inputs(d, k, lk) if d.get("shot_no") else (None, None)
    image_prompt = st.text_area("Prompt ảnh" + lk("image_prompt"), d.get("image_prompt", ""), key=f"{k}_prompt", height=80)
    if locked:
        st.caption("🔒 = bạn đã sửa tay, Director chạy lại sẽ giữ nguyên.")
        if st.button("🔓 Cho Director điền lại các trường 🔒 của cảnh này", key=f"{k}_unlock"):
            act(lambda: llm_io.unlock_scene_fields(p, pid, idx))
            st.rerun()
    st.caption("Sửa cảnh đã có ảnh/video: các kết quả cũ sẽ hiện ⚠ cũ để bạn làm lại đúng phần bị ảnh hưởng.")
    b1, b2 = st.columns(2)
    if b1.button("💾 Lưu cảnh", key=f"sds_{pid}_{idx}", type="primary"):
        table = lines_edit.to_dict("records") if hasattr(lines_edit, "to_dict") else lines_edit
        old_lines = [x for x in d.get("dialogue") or [] if isinstance(x, dict)]
        dlg = []
        for n, r in enumerate(table):
            said = str(r.get("Lời thoại") or "").strip()
            if not said:
                continue
            old = old_lines[n] if n < len(old_lines) and str(old_lines[n].get("text") or "").strip() == said else \
                next((x for x in old_lines if str(x.get("text") or "").strip() == said), {})
            how = dict(old.get("delivery") or {})         # emotion / stress / tag written by the Director stay (by the line's place)
            how.update(pace=str(r.get("Nhịp giọng") or "") or None, intensity=int(r.get("Cường độ giọng") or 0) or None,
                       pause_before=bool(r.get("Ngắt trước")) or None)
            dlg.append({"speaker": str(r.get("Người nói") or "").strip(), "text": said,
                        "delivery": {x: v for x, v in how.items() if v is not None}})
        fields = {"location": location, "time": time_, "shot": shot, "mood": mood, "lighting": lighting,
                  "image_prompt": image_prompt, "location_asset": bg, "blocking": blocking, "emotional_intent": intent,
                  "sequence": int(sequence) or None, "camera_complexity": complexity, "shot_role": role,
                  "duration_s": int(duration) or None}
        if rows or dlg:
            fields["dialogue"] = dlg
        if perf is not None:
            fields["performance"], fields["why"] = perf, why_text
        if char_names:
            fields["characters"] = cast
        if act(lambda: llm_io.update_scene(p, pid, idx, fields, text=text), f"Đã lưu cảnh {idx}"):
            st.rerun()
    with b2:
        if confirm_all(f"scene_del_{pid}_{idx}", [idx], "🗑 Xóa cảnh này", f"Xóa cảnh {idx}?", st, "Có, xóa cảnh"):
            if act(lambda: p.delete_scene(pid, idx), f"Đã xóa cảnh {idx}"):
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


def director_panel(p: Pipeline, pid: int, chars) -> None:
    locked = any(c["locked"] for c in chars)
    kept = llm_io.locked_fields(p.conn, pid)
    with st.container(border=True):
        ui.html(ui.card_title("1d · 🎬 Director", "Character Bible + thông số, ý đồ, thoại từng cảnh"))
        if kept:
            st.caption(f"🔒 {sum(len(r['fields']) for r in kept)} trường bạn đã sửa tay ở {len(kept)} cảnh được giữ nguyên khi chạy lại.")
        client = llm_client()
        if client is not None:
            from core import director_two_pass
            two = director_two_pass.enabled(p.project(pid))
            label = f"🤖 Chạy Director{' hai lượt' if two else ''} bằng {llm_label(client)}"
            if two:
                st.caption("🧪 Director hai lượt (cờ `director_two_pass`, chưa thử thật): Tầng A Đạo diễn viết Bible + ý đồ từng cảnh → "
                           "Tầng B Quay phim chia shot mỗi cảnh một lượt (phần chung cache) → code Đạo diễn duyệt bảng shot so với ý đồ.")
            try:                                   # luật chi phí: the estimate before the click (both ways, so the choice is informed)
                st.caption("💵 " + director_two_pass.estimate_text(director_two_pass.estimate(p, pid, client)))
            except Exception as e:  # noqa: BLE001 - an estimate that cannot be made is said, never hidden
                st.caption(f"💵 Chưa ước tính được chi phí Director ({type(e).__name__}: {e})")
            go = (confirm_all(f"llm_dir_{pid}", ["again"], label + " (chạy lại)",
                              "Character Bible đã khóa: chạy lại chỉ cập nhật thông số cảnh (trường bạn đã sửa tay được giữ), nhân vật đã khóa "
                              "không đổi. Chạy?", st, "Có, chạy lại") if locked
                  else st.button(label, type="primary", key=f"llm_dir_{pid}"))
            pending = director_two_pass.pending_scenes(p, pid) if two else []
            resume = bool(pending) and st.button(
                f"↻ Chỉ hỏi lại {len(pending)} cảnh lỗi (cảnh {', '.join(map(str, pending))})", key=f"llm_dir_resume_{pid}",
                help="Lần chạy trước dừng vì Quay phim chưa chia được các cảnh này. Dùng lại ý đồ Tầng A và các cảnh đã chia (đã trả tiền) "
                     "khi kịch bản/luật không đổi — chỉ trả tiền cho các cảnh lỗi.")
            if go or resume:
                with st.spinner("Claude đang phân tích kịch bản…"):
                    ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_director(p, pid, client, resume=resume)))
                if ok:
                    r = st.session_state.pop("llm_res")
                    st.toast(f"Đã lưu {r['characters']} nhân vật, {r['scenes']} cảnh ({tokens_text(r)})"
                             + (f" · {r['calls']} lượt Claude" if r.get("two_pass") else "")
                             + (f" · Đạo diễn duyệt: cảnh {', '.join(map(str, r['flagged']))} cần xem" if r.get("flagged") else ""))
                    st.rerun()
        else:
            st.caption(claude_hint() + " Hoặc dùng cách nhập tay bên dưới.")
        if C.expert():
            with st.expander("✍ Nâng cao: prompt gửi Claude + dán JSON kết quả", expanded=client is None and not chars):
                st.code(prompts.build_director_bundle(p, pid), language="markdown")
                raw = st.text_area("Dán JSON kết quả từ Claude", key=f"analysis_{pid}", height=120)
                if st.button("Lưu phân tích", disabled=not raw.strip(), key=f"dir_paste_{pid}"):
                    from core import director_two_pass

                    def _paste():
                        llm_io.store_scene_analysis(p, pid, raw)
                        director_two_pass.forget(p, pid)      # the pasted plan replaces any two-pass intent
                    if act(_paste, "Đã lưu Character Bible + thông số cảnh"):
                        st.rerun()


def _voices(pid: int):
    key = f"voices_{pid}"
    if key not in st.session_state:
        try:
            provider = music.audio_provider()
            st.session_state[key] = voice.library(provider) if provider else []   # official + team voices (FF 'VN' clones first)
        except ProviderError as e:
            st.session_state[key] = []
            st.caption(f"Không lấy được danh sách giọng: {e}")
    return st.session_state[key]


def voice_preview_row(p: Pipeline, pid: int, name: str, voice_id, voice_name) -> None:
    """🔈 Vietnamese sample sentence in the chosen voice (one short TTS — a little audio credit), to hear accent and tones."""
    if not voice_id:
        return
    directory = voice.previews_dir(C.DATA, pid)
    mine = [e for e in audio_lib.load(directory) if e.get("preview_for") == name and e.get("voice_id") == voice_id]
    b1, b2 = st.columns([1.4, 3], vertical_alignment="center")
    if b1.button("🔈 Nghe thử câu mẫu tiếng Việt", key=f"vprev_{pid}_{name}", help="Tạo 1 câu mẫu bằng giọng này (tốn một chút credit âm thanh)."):
        try:
            provider = music.audio_provider()
        except ProviderError as e:
            st.error(str(e))
            provider = None
        if provider is not None:
            voice.preview(provider, C.DATA, pid, voice_id, voice_name or "", name, ledger=(p.conn, pid))
            st.rerun()
    if mine:
        e = mine[-1]
        if e["state"] == "running":
            try:
                provider = music.audio_provider()
                if provider is not None:
                    audio_lib.refresh(provider, directory)
                    e = [x for x in audio_lib.load(directory) if x.get("preview_for") == name and x.get("voice_id") == voice_id][-1]
            except ProviderError:
                pass
        if e["state"] == "succeeded" and e.get("file"):
            b2.audio(os.path.join(directory, e["file"]))
        else:
            b2.caption(ui.state_label(e["state"], "audio") + (" — bấm lại sau vài giây" if e["state"] == "running" else ""))


def character_detail_panel(p: Pipeline, pid: int, c, voices, client, locked: bool, has_ref: bool = True) -> None:
    """Character Lock + voice + anchor of one character (skills: consistency designer, narration-writer)."""
    lock = claude_tasks.get_lock(c)
    prof = voice.get_profile(c)
    head = f"**{escape(c['name'])}** — " + ("🔒 Lock ✓" if lock else "🔒 chưa có Lock") + " · " \
           + (f"🎙 {escape(prof.get('voice_name') or str(prof.get('voice_id')))}" if prof.get("voice_id") else "🎙 chưa có giọng") \
           + " · " + ("🖼 ảnh mốc đã duyệt" if c["anchor_approved"] else "🖼 ảnh mốc chưa duyệt")
    with st.expander(head.replace("**", ""), expanded=False):
        st.markdown("**🔒 Character Lock** — điều không được lệch ở mọi cảnh (dùng cho prompt ảnh, QC ảnh, QC video)")
        k = f"lock_{pid}_{c['name']}"
        must = st.text_area("Bắt buộc giữ", lock.get("must_keep", ""), key=f"{k}_must", height=60, disabled=locked)
        may = st.text_input("Được đổi giữa các cảnh", lock.get("may_change", ""), key=f"{k}_may", disabled=locked)
        forb = st.text_area("Cấm lệch", lock.get("forbidden", ""), key=f"{k}_forb", height=60, disabled=locked)
        b1, b2 = st.columns(2)
        if b1.button("💾 Lưu Lock", key=f"{k}_save", disabled=locked):
            act(lambda: claude_tasks.set_lock(p, pid, c["name"], {"must_keep": must, "may_change": may, "forbidden": forb}), "Đã lưu")
            st.rerun()
        if b2.button("🤖 Claude viết Lock từ ảnh", key=f"{k}_ai", disabled=locked or client is None, help=None if client else claude_hint()):
            with st.spinner("Claude đang xem ảnh tham chiếu…"):
                if act(lambda: claude_tasks.character_lock(p, pid, c["name"], client), "Đã viết Character Lock"):
                    for suffix in ("must", "may", "forb"):
                        st.session_state.pop(f"{k}_{suffix}", None)
                    st.rerun()
        st.markdown("**🎙 Giọng nói (TTS)** — thoại tiếng Việt được đọc bằng giọng này (Bước 3)")
        if voices:
            ordered = voice.vietnamese_first(voices)          # v3: voices that list Vietnamese first (🇻🇳)
            ids = [None] + [v.get("id") for v in ordered]
            label = lambda v: ("⭐ " if voice.preferred(v) else "🇻🇳 " if voice.speaks_vi(v) else "") + voice.display_name(v) + (  # noqa: E731
                f" · {'nam' if voice.voice_gender(v) == 'male' else 'nữ'}" if voice.preferred(v) else "")
            names = {v.get("id"): label(v) for v in ordered}
            names.update({v.get("id"): label(v) for v in voices if v.get("id") not in names})
            cur = prof.get("voice_id") if prof.get("voice_id") in ids else None
            v1, v2 = st.columns([2, 3])
            pick = v1.selectbox("Giọng", ids, index=ids.index(cur), key=f"voice_{pid}_{c['name']}",
                                format_func=lambda i: "— chưa chọn —" if i is None else f"{names.get(i)} (#{i})")
            persona = v2.text_input("Cách nói (persona)", prof.get("persona", ""), key=f"persona_{pid}_{c['name']}",
                                    placeholder="câu ngắn, hay cà khịa, nói 'nha'…")
            if (pick, persona) != (cur, prof.get("persona", "")) and st.button("💾 Lưu giọng", key=f"voice_save_{pid}_{c['name']}"):
                voice.set_profile(p.conn, pid, c["name"], {"voice_id": pick, "voice_name": names.get(pick), "persona": persona} if pick else None)
                st.rerun()
            voice_preview_row(p, pid, c["name"], cur, names.get(cur))
        else:
            st.caption("Chưa có danh sách giọng (cần AUDIO_PROVIDER / Clip AI). Voice Design / Voice Clone chỉ có trên web ClipAI: tạo ở đó rồi chọn ở đây.")
        st.markdown("**🖼 Ảnh mốc** — ảnh tham chiếu bạn xác nhận là ĐÚNG nhân vật trước khi gen cả loạt")
        if c["anchor_approved"]:
            if st.button("↩ Bỏ duyệt ảnh mốc", key=f"anchor_off_{pid}_{c['name']}"):
                p.conn.execute("UPDATE characters SET anchor_approved=0 WHERE project_id=? AND name=?", (pid, c["name"]))
                p.conn.commit()
                st.rerun()
        elif not has_ref:
            st.caption("Chưa có ảnh tham chiếu: nhân vật đang vẽ theo mô tả chữ (dễ lệch giữa các cảnh). Chọn tài nguyên ở "
                       "“🧰 Tài nguyên đi kèm kịch bản” hoặc tạo bộ ảnh ở “👗 Trang phục cho video này”, rồi duyệt ảnh mốc.")
            if st.button("Vẫn vẽ theo mô tả chữ — bỏ qua ảnh mốc", key=f"anchor_on_{pid}_{c['name']}"):
                p.conn.execute("UPDATE characters SET anchor_approved=1 WHERE project_id=? AND name=?", (pid, c["name"]))
                p.conn.commit()
                st.rerun()
        elif st.button("✔ Ảnh tham chiếu ở trên là đúng — duyệt ảnh mốc", key=f"anchor_on_{pid}_{c['name']}"):
            p.conn.execute("UPDATE characters SET anchor_approved=1 WHERE project_id=? AND name=?", (pid, c["name"]))
            p.conn.commit()
            st.rerun()


def bible_check_box(p: Pipeline, pid: int, rows, client, locked: bool) -> None:
    """F1: the Bible text against the library pictures — mismatches shown with Claude's suggested wording, one click to use it."""
    flags = claude_tasks.bible_flags(p, pid)
    for r in rows:
        if r["name"] not in flags:
            continue
        res = json.loads(r["bible_check"] or "{}")
        box = st.container(border=True)
        box.warning(f"⚑ **{r['name']}**: mô tả mâu thuẫn với ảnh tài nguyên — " + "; ".join(flags[r["name"]]))
        fixed = (res.get("fixed_description") or "").strip()
        if fixed:
            box.caption(f"Đề xuất: {fixed}")
            if not locked and box.button("✔ Dùng đề xuất này", key=f"bfix_{pid}_{r['name']}"):
                act(lambda: llm_io.update_character(p, pid, r["name"], fixed, r["wardrobe"]), "Đã sửa mô tả theo ảnh")
                st.rerun()
    if client is not None and st.button("🔍 Kiểm mô tả nhân vật với ảnh tài nguyên (1 lượt Claude, chỉ nhân vật đổi từ lần kiểm trước)",
                                        key=f"bcheck_{pid}"):
        with st.spinner("Claude đang so mô tả với ảnh…"):
            act(lambda: claude_tasks.bible_check(p, pid, client), "Đã kiểm xong")
        st.rerun()


def character_bible_panel(p: Pipeline, pid: int, chars, risky) -> None:
    char_names = [c["name"] for c in chars]
    locked = any(c["locked"] for c in chars)
    rows = p.conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,)).fetchall()
    with st.container(border=True):
        head, status = st.columns([3, 2], vertical_alignment="center")
        head.markdown(ui.card_title("1e · 👥 Character Bible", f"{len(chars)} mục" + (" · 🔒 đã khóa" if locked else "")), unsafe_allow_html=True)
        if risky:
            status.caption(f"⚠ {len(risky)} mục có thể vướng IP (xem “⚠ Rủi ro” ở góc trên)")
        linked = assets.link_characters(p.conn, pid, char_names)
        st.dataframe([{"Nhân vật / đối tượng": r["name"],
                       "Mô tả": r["description"] + (f" · {r['wardrobe']}" if r["wardrobe"] else ""),
                       "Ảnh tham chiếu": (f"✔ {linked[r['name']]['name']} · {len(linked[r['name']]['refs'])} ảnh" if linked.get(r["name"]) else "— vẽ theo mô tả"),
                       "Lock": "✔" if r["lock_rules"] else "—",
                       "Giọng": voice.get_profile(r).get("voice_name") or ("—" if not voice.get_profile(r).get("voice_id") else "✔"),
                       "Ảnh mốc": "✔" if r["anchor_approved"] else "—",
                       "IP": "⚠" if r["name"] in risky else "",
                       } for r in rows], width="stretch", hide_index=True, height=min(38 * (len(rows) + 1) + 3, 260))
        client = llm_client()
        bible_check_box(p, pid, rows, client, locked)
        character_reference_panel(p, pid, chars)
        voices = _voices(pid)
        st.markdown("**🔒 Lock · 🎙 Giọng · 🖼 Ảnh mốc của từng nhân vật**")
        speakers = {ln["speaker"].upper() for ln in voice.planned_lines(p.conn, pid) if ln["speaker"]}
        no_voice = [r["name"] for r in rows if r["name"].upper() in speakers and not voice.get_profile(r).get("voice_id")]
        vi_pool = [v for v in voice.vietnamese_first(voices) if voice.speaks_vi(v)] if voices else []
        if voices:
            n_f = sum(1 for v in vi_pool if voice.voice_gender(v) == "female")
            n_pref = sum(1 for v in vi_pool if voice.preferred(v))
            st.caption(f"🇻🇳 {len(vi_pool)} giọng tiếng Việt ({n_f} nữ)"
                       + (f", ưu tiên ⭐ {n_pref} giọng clone Việt của team (hậu tố VN, `data/voices_vi.json`)" if n_pref else
                          " — chưa thấy giọng clone Việt của team (⭐): kiểm tra nhóm FF ở AI Audio → Voice Actors")
                       + ". Nên nghe thử câu mẫu. Từ tiếng Anh/tên riêng được đọc theo `data/pronunciation_vi.json`."
                       + (f" ⚠ {len(speakers)} nhân vật có thoại nhưng chỉ {len(vi_pool)} giọng tiếng Việt: sẽ phải dùng chung giọng." if 0 < len(vi_pool) < len(speakers) else ""))
        if no_voice and voices and client is not None:
            if st.button(f"🤖 Claude chọn giọng cho {len(no_voice)} nhân vật có thoại", key=f"cast_{pid}"):
                with st.spinner("Claude đang chọn giọng…"):
                    act(lambda: claude_tasks.cast_voices(p, pid, client, voices), "Đã chọn giọng")
                for r in rows:                     # the voice pickers must show the new choice, not their old widget value
                    st.session_state.pop(f"voice_{pid}_{r['name']}", None)
                    st.session_state.pop(f"persona_{pid}_{r['name']}", None)
                st.rerun()
        for r in rows:
            character_detail_panel(p, pid, r, voices, client, locked, has_ref=bool(linked.get(r["name"])))
        if subjects_visible(p, pid):
            subject_panel(p, pid, chars)
        with st.expander("✏ Sửa / thêm nhân vật, đối tượng · khóa"):
            if locked:
                st.caption("Character Bible đang khóa. Muốn sửa phải mở khóa (ảnh đã gen sẽ báo ⚠ cũ nếu mô tả đổi).")
                if st.button("🔓 Mở khóa để sửa", key="btn_bad_unlock"):
                    act(lambda: llm_io.unlock_character_bible(p, pid), "Đã mở khóa Character Bible")
                    st.rerun()
            else:
                who = st.selectbox("Chọn mục cần sửa", char_names, key=f"csel_{pid}")
                c = next(c for c in chars if c["name"] == who)
                n_name = st.text_input("Tên", c["name"], key=f"cn_{pid}_{c['name']}")
                n_desc = st.text_area("Mô tả", c["description"], key=f"cd_{pid}_{c['name']}", height=80)
                n_ward = st.text_input("Trang phục / dấu hiệu", c["wardrobe"] or "", key=f"cw_{pid}_{c['name']}")
                if st.button("Lưu", key=f"cs_{pid}_{c['name']}"):
                    if act(lambda: llm_io.update_character(p, pid, c["name"], n_desc, n_ward, n_name), f"Đã lưu {n_name}"):
                        st.rerun()
            st.markdown("**➕ Thêm nhân vật / đối tượng**")
            st.caption("Không chỉ người: cũng có thể là sinh vật, linh vật, đạo cụ… bất cứ thứ gì cần giống nhau ở mọi cảnh.")
            a_name = st.text_input("Tên", key=f"cadd_name_{pid}")
            a_desc = st.text_area("Mô tả ngoại hình", key=f"cadd_desc_{pid}", height=70)
            a_ward = st.text_input("Trang phục / dấu hiệu (tùy chọn)", key=f"cadd_ward_{pid}")
            if st.button("Thêm vào Character Bible", key=f"cadd_{pid}", disabled=not (a_name.strip() and a_desc.strip())):
                if act(lambda: llm_io.add_character(p, pid, a_name, a_desc, a_ward), f"Đã thêm {a_name}"):
                    st.rerun()


def dialogue_review_panel(p: Pipeline, pid: int) -> None:
    """Dialogue: length against the clip (real voice length when voiced) and Claude's review (narration-writer skill)."""
    entries = dialogue.check(p, pid, voice.scene_seconds(p.conn, pid, C.DATA))
    if not entries:
        return
    bad = dialogue.problems(entries)
    key = f"dlg_review_{pid}"
    with st.expander(f"1f · 🗣 Rà thoại — {len(entries)} cảnh có thoại" + (f", {len(bad)} cần chú ý" if bad else ", độ dài đều vừa"),
                     expanded=bool(bad) or key in st.session_state):
        for e in entries:
            icon = {"ok": "✔", "tight": "◐", "extend": "⚠", "split": "✖"}[e["status"]]
            color = {"ok": "green", "tight": "orange", "extend": "orange", "split": "red"}[e["status"]]
            st.markdown(f":{color}[{icon} S{e['idx']:02d}] {escape(', '.join(e['speakers']))} · "
                        + (f"giọng thật ≈ {e['needed']:g}s" if e["measured"] else f"{e['syllables']} âm tiết ≈ {e['needed']:g}s")
                        + f" / clip {e['planned']:g}s (model tối đa {e['max']}s)" + (f" — {escape(e['advice'])}" if e["advice"] else ""))
        fixable = [e for e in bad if e["status"] == "extend"]
        if fixable and st.button(f"⏱ Tự tăng thời lượng {len(fixable)} clip cho vừa thoại", key=f"dlg_fix_s1_{pid}"):
            dialogue.extend(p, entries)
            st.rerun()
        client = llm_client()
        if st.button("🤖 Claude rà thoại (6 lỗi thoại + độ dài)", key=f"dlg_ai_{pid}", disabled=client is None,
                     help=None if client else claude_hint()):
            with st.spinner("Claude đang đọc thoại…"):
                act(lambda: st.session_state.__setitem__(key, claude_tasks.review_dialogue(p, pid, client)))
        res = st.session_state.get(key)
        if res:
            if res.get("summary"):
                st.info(res["summary"])
            for n, ln in enumerate(res.get("lines") or []):
                with st.container(border=True):
                    st.markdown(f"**S{ln['idx']:02d} · câu {ln['line']}** {escape(ln.get('speaker') or '')} — {escape(ln.get('problem') or '')}")
                    new = st.text_input("Đề xuất", ln["suggestion"], key=f"dlg_sug_{pid}_{n}")
                    if st.button("Áp dụng câu này", key=f"dlg_apply_{pid}_{n}"):
                        if act(lambda: claude_tasks.apply_dialogue_fix(p, pid, ln["idx"], ln["line"], new), "Đã sửa thoại"):
                            res["lines"] = [x for x in res["lines"] if x is not ln]
                            st.rerun()
            for sp in res.get("split") or []:
                st.warning(f"S{sp.get('idx')}: nên tách cảnh — {sp.get('why', '')}")
            if not res.get("lines") and not res.get("split"):
                st.success("Claude không thấy lỗi thoại cần sửa.")


def _replan_button(p: Pipeline, pid: int, scene_idx: int, col) -> None:
    """1.4: re-plan the shots of one script scene (one cached Claude call, a few cents) — only while that scene and the later ones have
    no picture or clip yet."""
    later = [r["id"] for r in p.conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (pid,))
             if (json.loads(r["data"] or "{}").get("story_scene") or 0) >= scene_idx]
    if later and p.conn.execute("SELECT 1 FROM jobs WHERE scene_id IN (" + ",".join("?" * len(later)) + ") LIMIT 1", later).fetchone():
        return
    client = llm_client()
    if client is None:
        return
    if col.button("↻ Chia shot lại cảnh này", key=f"replan_{pid}_{scene_idx}",
                  help="Một lượt Claude chỉ cho cảnh này (phần luật chung được cache) — vài cent thay vì ~$0,3 của cả kịch bản. "
                       "Cảnh sau được ghi lại theo thứ tự phim, không đổi nội dung. Director hai lượt: Quay phim chia lại theo ý đồ "
                       "Tầng A đã lưu (không hỏi lại Đạo diễn)."):
        with st.spinner(f"Claude đang chia shot lại cảnh {scene_idx}…"):
            ok = act(lambda: st.session_state.__setitem__("replan_res", llm_runner.run_director_scene(p, pid, scene_idx, client)))
        if ok:
            r = st.session_state.pop("replan_res")
            st.toast(f"Cảnh {scene_idx}: {r['rows']} shot ({tokens_text(r)})")
            st.rerun()


def _paid_line(p: Pipeline, pid: int):
    """H6: seconds of video that will be billed for this shot plan (Kling, the model's minimum clip), one line per way of making it —
    worked out by code from the stored Director answer, before any picture or clip is paid for."""
    from core import director_report
    proj = p.project(pid)
    try:
        raw = json.loads(proj["director_raw"] or "{}")
        if not raw.get("scenes") or raw.get("truncated"):
            return None
        r = director_report.report(raw, proj["script_text"] or "")
    except Exception:  # noqa: BLE001 - an old or odd answer must not break Step 1
        return None
    s, u = r["paid_s"], r["paid_usd"]
    bits = [f"từng shot {s['per_shot']:g}s" + (f" ≈ ${u['per_shot']:g}" if u["per_shot"] else ""),
            f"gom theo cảnh (multi-shot) {s['per_scene']:g}s" + (f" ≈ ${u['per_scene']:g}" if u["per_scene"] else "")]
    if s["per_setup"] is not None:
        bits.append(f"theo vị trí máy ({s['setups']}) {s['per_setup']:g}s" + (f" ≈ ${u['per_setup']:g}" if u["per_setup"] else ""))
    return f"💵 Video phải trả tiền cho {r['total_s']:g}s phim (Kling, chưa tính gen lại): " + " · ".join(bits)


def _crew_notes(p: Pipeline, pid: int) -> None:
    """GĐ4 (knowledge/roles/): what the Director gave up (`tradeoffs`, and a sacrifice it did not write down), the acting checks
    (core/performance.py) and the Director's notes for the script writer — suggestions only, the lines are never changed."""
    from core import director_report
    proj = p.project(pid)
    try:
        raw = json.loads(proj["director_raw"] or "{}")
        if not raw.get("scenes") or raw.get("truncated"):
            return
        r = director_report.report(raw, proj["script_text"] or "")
    except Exception:  # noqa: BLE001 - an old or odd answer must not break Step 1
        return
    if r.get("unrecorded"):
        st.warning("⚠ Director đã hy sinh (" + ", ".join(r["unrecorded"]) + ") mà không ghi lý do (`tradeoffs`).")
    trade = [t for t in r["tradeoffs"] if isinstance(t, dict)]
    if trade:
        with st.expander(f"⚖ Director đã đánh đổi {len(trade)} chỗ"):
            st.markdown("\n".join(f"- Cảnh {t.get('scene', '?')}: chọn **{escape(str(t.get('chose') or ''))}**, bỏ "
                                  f"{escape(str(t.get('gave_up') or ''))} — {escape(str(t.get('why') or ''))}" for t in trade))
    if r.get("payoff_unplanted"):
        st.warning("⚠ Cảnh gặt lại điều chưa được gieo ở cảnh nào trước (`beat.payoff` không có `plant` trước đó): "
                   + ", ".join(map(str, r["payoff_unplanted"])))
    if r.get("continuity"):
        st.caption("🧭 Liền mạch: " + " · ".join(escape(w) for w in r["continuity"]))
    if r.get("acting"):
        st.caption("🎭 Diễn xuất: " + " · ".join(escape(w) for w in r["acting"]))
    if r.get("sound"):
        st.caption("🔊 Âm thanh: " + " · ".join(escape(w) for w in r["sound"]))
    if r.get("script_notes"):
        with st.expander(f"📝 Ghi chú kịch bản của Đạo diễn cho người viết ({len(r['script_notes'])}) — chỉ đề xuất, thoại không bị sửa"):
            st.markdown("\n".join(f"- Cảnh {n.get('scene', '?')}"
                                  + (f" · {escape(str(n['kind']))}" if n.get("kind") else "") + f": {escape(str(n['note']))}"
                                  for n in r["script_notes"]))


def _director_review(p: Pipeline, pid: int) -> None:
    """GĐ5 "Đạo diễn duyệt" (two-pass Director): code compared each scene's shots with the Director's intent — lines, seconds frame,
    focus character in frame, a hold shot after a strong moment. Flags need the person's eye; nothing is re-asked on its own."""
    from core import director_two_pass
    try:
        rv = json.loads(p.project(pid)["director_raw"] or "{}").get("review")
    except (ValueError, KeyError, AttributeError):
        rv = None
    if not isinstance(rv, dict) or not rv.get("scenes"):
        return
    rows = director_two_pass.review_text(rv)
    if rv.get("flagged"):
        st.warning("🎬 Đạo diễn duyệt bảng shot của Quay phim: cảnh " + ", ".join(map(str, rv["flagged"])) + " lệch ý đồ — xem lại "
                   "(sửa shot bằng ô sửa, hoặc “↻ Chia shot lại cảnh này” kèm lý do).")
    with st.expander(f"🎬 Đạo diễn duyệt ({len(rv['scenes']) - len(rv.get('flagged') or [])}/{len(rv['scenes'])} cảnh đạt ý đồ)"):
        st.markdown("\n".join(f"- {escape(r)}" for r in rows))
        notes = [f"Cảnh {r['idx']}: {n}" for r in rv["scenes"] for n in r.get("notes") or []]
        if notes:
            st.caption("Ghi chú diễn xuất / âm thanh theo từng cảnh: " + " · ".join(escape(n) for n in notes[:12]))


def scene_list(p: Pipeline, pid: int, scenes, char_names) -> None:
    status = lineage.scan(p.conn, pid)
    by_idx = {r["idx"]: r for r in status.values()}
    with_bg = sum(1 for s in scenes if assets.scene_location(p.conn, pid, json.loads(s["data"] or "{}")))
    unit = "shot" if scenes and any(json.loads(s["data"] or "{}").get("shot_no") for s in scenes) else "cảnh"
    st.caption(f"🏞 {with_bg}/{len(scenes)} {unit} đã có Background"
               + ("" if with_bg == len(scenes) else f" — {unit} chưa có thì không dựng được layout; chọn trong từng {unit} hoặc gắn địa điểm ở 1b"))
    proj = p.project(pid)
    modes = {0: "Tự động: nối trong cùng nhóm cảnh", 1: "Luôn nối cảnh liền trước", 2: "Không nối"}
    if C.expert():
        mode = st.radio("🔗 Nối ảnh cảnh trước (giữ liên tục ánh sáng/vị trí khi gen ảnh)", list(modes), horizontal=True,
                        index=list(modes).index(proj["storyboard_mode"] if proj["storyboard_mode"] in modes else 0),
                        format_func=modes.get, key=f"chain_{pid}",
                        help="Ảnh đã duyệt của cảnh trước (cùng nhóm) được gửi kèm làm tham chiếu khi gen ảnh cảnh sau — cách thay cho Storyboard của Deepix.")
    if C.expert():
        if mode != proj["storyboard_mode"]:
            p.conn.execute("UPDATE projects SET storyboard_mode=? WHERE id=?", (mode, pid))
            p.conn.commit()
    from core import shots as _shots
    story = {x["idx"]: x for x in _shots.story_scenes(p, pid)}
    cuts = _shots.dialogue_cuts(p, pid) if any(json.loads(s["data"] or "{}").get("shot_no") for s in scenes) else []
    if cuts:
        st.warning(f"✂ Director đã bỏ {len(cuts)} câu thoại của kịch bản — xem lại (thêm lại câu vào shot bằng ô sửa shot nếu cần):\n"
                   + "\n".join(f"- Cảnh {c['scene']} · {c['speaker']}: “{escape(c['text'])}”"
                                + (f" — ⚠ câu sau có thể là câu đáp lại ({escape(c['next'])})" if c["answered"] else "") for c in cuts))
    try:
        fixed = (json.loads(p.project(pid)["director_raw"] or "{}").get("normalized") or []) if cuts or scenes else []
    except (ValueError, KeyError, IndexError, AttributeError):
        fixed = []
    if fixed:
        with st.expander(f"🔧 Code đã chuẩn hóa {len(fixed)} chỗ trong câu trả lời Director (thay vì hỏi lại Claude)"):
            st.markdown("\n".join(f"- {escape(str(c))}" for c in fixed))
    paid = _paid_line(p, pid)
    if paid:
        st.caption(paid)
    _crew_notes(p, pid)
    _director_review(p, pid)
    cur_story = None
    for s in scenes:
        d = json.loads(s["data"] or "{}")
        st_row = by_idx.get(s["idx"])
        if d.get("shot_no"):                          # v3 shot rows: grouped under their script scene
            if d.get("story_scene") != cur_story:
                cur_story = d.get("story_scene")
                group = [json.loads(x["data"] or "{}") for x in scenes if json.loads(x["data"] or "{}").get("story_scene") == cur_story]
                total = sum(float(g.get("duration_s") or 0) for g in group)
                head_col, redo_col = st.columns([5, 2], vertical_alignment="center")
                head_col.markdown(f"**Cảnh {cur_story} — {escape((story.get(cur_story) or {}).get('heading') or '')}** · "
                                  f"{len(group)} shot · {total:.1f}s")
                _replan_button(p, pid, cur_story, redo_col)
                warn = _shots.pacing_warnings(group)
                if warn:
                    st.caption("⚠ " + " · ".join(warn))
            lines = "; ".join(f"{x.get('speaker')}: {x.get('text')}" for x in d.get("dialogue") or [])
            head = [f"{_shots.label(d, s['idx'])} · {d.get('size')} · {d.get('role')} · {float(d.get('duration_s') or 0):g}s"
                    + (" · ⭐" if d.get("shot_role") == "hero" else ""),
                    (d.get("action") or "")[:60], lines[:70], scene_status_text(st_row) if st_row else ""]
            with st.expander("   |   ".join(x for x in head if x)):
                scene_editor(p, pid, s, char_names)
            continue
        bits = [f"S{s['idx']:02d}" + (f" · nhóm {d['sequence']}" if d.get("sequence") else "")
                + (" · ⭐" if d.get("shot_role") == "hero" else "") + (" · 🌀 phức tạp" if d.get("camera_complexity") == "complex" else ""),
                " · ".join(filter(None, [d.get("time"), d.get("location")])), ", ".join(d.get("characters") or []),
                scene_status_text(st_row) if st_row else ""]
        with st.expander("   |   ".join(x for x in bits if x)):
            scene_editor(p, pid, s, char_names)
    if st.button("➕ Thêm cảnh", key=f"scene_add_{pid}", help="Cho kịch bản mà công cụ không tự tách được"):
        act(lambda: p.add_scene_next(pid))
        st.rerun()


def _lock_and_go(p: Pipeline, pid: int) -> None:
    """Button callback: lock the Character Bible and move to Step 2 (a callback may still change the step selector)."""
    p = Pipeline(connect(C.DB))                     # a callback runs in another thread than the one that made `p`
    try:
        llm_io.lock_character_bible(p, pid)
    except ERRORS as e:
        st.session_state["lock_error"] = str(e)
        return
    st.session_state["step"] = STEPS[1]


def _anchor_reset(p: Pipeline, pid: int, name: str) -> None:
    """Other reference pictures chosen: the approved anchor no longer applies."""
    p.conn.execute("UPDATE characters SET anchor_approved=0 WHERE project_id=? AND name=?", (pid, name))
    p.conn.commit()
