"""Step 1: script, resources, run mode, Director, Character Bible, storyboard, World Bible."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.steps.step1_v2 import cap, say, is_next  # noqa: F401  (v2: long captions / notes become a one-line summary + ⓘ)
from dashboard.steps.step1_run import *  # noqa: F401,F403  (S9.5: Step 1 split in parts)
from dashboard.steps.step1_run import _budget_summary  # noqa: F401
from dashboard.steps.step1_prep import *  # noqa: F401,F403  (S9.5: Step 1 split in parts)
from dashboard.steps.step1_characters import *  # noqa: F401,F403  (S9.5: Step 1 split in parts)
from dashboard.steps.step1_characters import _voices, _bible_summary, _anchor_reset  # noqa: F401
from dashboard.steps.step1_director import *  # noqa: F401,F403  (S9.5: Step 1 split in parts)
from dashboard.steps.step1_director import _director_summary, _replan_button, _paid_line, _crew_notes, _director_review  # noqa: F401


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


def _script_summary(p: Pipeline, pid: int, scenes) -> str:
    """One line for the folded script card: scenes / shots / dialogue lines / length of the script."""
    if not scenes:
        return "chưa có kịch bản"
    lines = sum(len(json.loads(s["data"] or "{}").get("dialogue") or []) for s in scenes)
    text = p.project(pid)["script_text"] or ""
    return f"📜 {_count_label(p, pid, scenes)} · {lines} câu thoại" + (f" · {len(text):,} ký tự".replace(",", ".") if text else "")


def analyse_script(p: Pipeline, pid: int, up=None, pasted: str = "", file=None) -> None:
    """▶ Phân tích (0 USD): read the file (uploader `up`, or a (name, bytes) `file` from the chat box) or the text, split the scenes,
    import them. One path for both screens (S14.21: was a closure inside script_input)."""
    if up is not None:
        res = script_reader.read_script(up.name, up.getvalue())
    elif file is not None:
        res = script_reader.read_script(file[0], file[1])
    else:
        res = script_reader.from_text(pasted)
    parsed = script_parser.split_scenes(res.paragraphs)
    script_parser.import_scenes(p, pid, parsed, full_text="\n\n".join(res.paragraphs))
    st.session_state["parse_info"] = res.info
    if len(parsed) == 1 and parsed[0].heading == "Mở đầu":
        st.session_state["parse_warn"] = ("Không thấy tiêu đề cảnh (vd “Cảnh 1”, “Scene 2”, “INT./EXT.”): "
                                          "cả kịch bản thành 1 cảnh. Hãy thêm/sửa cảnh thủ công.")
    st.toast(f"Đã tách {len(parsed)} cảnh")


def script_input(p: Pipeline, pid: int, with_reset: bool = True) -> bool:
    """The ways to put a script in (file / typed / raw idea) + the ▶ Phân tích button. Keys: up_/paste_/btn_analyse_/btn_bad_reset_.
    `with_reset` False: the reset button is drawn elsewhere (UI v2 puts it under "Tinh chỉnh"). Returns whether there is an input."""
    from core import idea_to_script
    if idea_to_script.enabled():                                # S14.21 (Đợt 3): one chat-style box for script / idea / "nói thêm"
        from dashboard.steps.step1_box import script_box
        return script_box(p, pid, with_reset)
    t_file, t_text = st.tabs(["📎 Tải file", "✍ Gõ / dán văn bản"])
    with t_file:
        up = st.file_uploader("Kịch bản", type=list(script_reader.SUPPORTED), key=f"up_{pid}", label_visibility="collapsed",
                              help="Word (.docx, kể cả kịch bản viết trong bảng), Excel (.xlsx), CSV/TSV, .txt, .md")
        cap("Đọc được: Word (.docx, cả bảng), Excel (.xlsx), CSV/TSV, .txt, .md. Kịch bản dạng bảng cần dòng tiêu đề cột như "
                   "Cảnh, Mô tả, Nhân vật, Lời thoại, Bối cảnh, Thời gian, Góc máy.")
    with t_text:
        pasted = st.text_area("Gõ hoặc dán kịch bản", key=f"paste_{pid}", height=170, label_visibility="collapsed",
                              placeholder="CẢNH 1 - ĐÊM, RỪNG ELDER\nSương mù phủ kín khu rừng…\nLYRA: Có thứ gì đó đang theo chúng ta.\n\n"
                                          "Dán cả bảng copy từ Excel / Google Sheets cũng được.")
    if with_reset:
        u2, u3, u4 = st.columns([2.4, 1.2, 4], vertical_alignment="center")
    else:
        u2, u4 = st.columns([2.4, 5.2], vertical_alignment="center")
        u3 = None
    has_input = up is not None or bool(pasted.strip())
    if u2.button("▶ Phân tích (tách cảnh)", disabled=not has_input, type="primary", key=f"btn_analyse_{pid}"):
        if act(lambda: analyse_script(p, pid, up, pasted)):
            st.rerun()
    from dashboard.design import components as D                   # v2: the hint about "file wins" is P3 → ⓘ; the state of the input stays as one line
    with u4:
        if has_input:
            D.line('<span class="script-sum">Sẵn sàng · bấm ▶ Phân tích</span>', "Nếu có cả file lẫn văn bản, hệ thống dùng file.",
                   f"script-input-hint-{pid}")
        else:
            st.caption("Chọn file hoặc dán văn bản, rồi bấm Phân tích.")
    if with_reset:
        with u3:
            reset_script_button(p, pid)
    return has_input


def parse_info_box() -> None:
    with st.expander("Hệ thống đã đọc kịch bản thế nào (kiểm tra lại)"):
        for line in st.session_state["parse_info"]:
            cap("• " + line)


def reset_script_button(p: Pipeline, pid: int) -> None:
    """↺ Làm lại: delete the scenes without a picture / job and the unlocked characters, so the script can be split again."""
    if confirm_all(f"btn_bad_reset_{pid}", ["reset"], "↺ Làm lại",
                   "Xóa các cảnh CHƯA có ảnh/video và các nhân vật CHƯA khóa để tách lại kịch bản? Cảnh đã có ảnh được giữ.",
                   st, "Có, xóa"):
        reset_unworked_scenes(p, pid)
        st.session_state.pop("parse_info", None)
        st.rerun()


def script_views(p: Pipeline, pid: int, proj, scenes, char_names) -> None:
    """Left: the whole script; right: the scenes (each one opens an editor)."""
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Kịch bản đầy đủ**")
        full = proj["script_text"] or "\n\n".join((json.loads(s["data"] or "{}").get("text") or s["title"] or "") for s in scenes)
        if full.strip():
            ui.html(script_html(full))
        else:
            cap("Chưa có kịch bản: tải file hoặc gõ/dán văn bản rồi bấm Phân tích.")
    with right:
        st.markdown("**Chia theo cảnh** · bấm vào từng cảnh để xem và sửa")
        if scenes:
            scene_list(p, pid, scenes, char_names)


def step1(p: Pipeline, pid: int):
    proj = p.project(pid)
    scenes = p.conn.execute("SELECT idx, title, state, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    chars = p.conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,)).fetchall()
    warnings = preflight.check_characters(p.conn, pid, preflight.load_blocklist()) if chars else []
    risky = {w["character"] for w in warnings}
    char_names = [c["name"] for c in chars]
    locked = any(c["locked"] for c in chars)
    stale = len(lineage.stale_scene_ids(p.conn, pid)) if scenes else 0
    from dashboard.steps.step1_v2 import step1_v2                       # S13 lane E (v2, the only composition since S14.14 G-a)
    return step1_v2(p, pid, proj, scenes, chars, risky, char_names, locked, stale)


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
    camera = {}
    if d.get("shot_no"):                                  # 07/10: a shot's size / angle / move could only be set by the Director
        from core import shots as _cam
        s1, s2, s3 = st.columns(3)
        for col, key, label, names in ((s1, "size", "Cỡ shot", _cam.SIZES), (s2, "angle", "Góc máy", _cam.ANGLES),
                                       (s3, "move", "Chuyển động máy", _cam.MOVES)):
            opts = [None] + list(names)
            camera[key] = col.selectbox(label + lk(key), opts, index=opts.index(d.get(key)) if d.get(key) in opts else 0,
                                        format_func=lambda v: "—" if v is None else v, key=f"{k}_{key}")
        routes = {None: "Tự động (gộp nhóm shot liền nhau)", "single": "Một clip riêng (Seedance, ảnh tham chiếu)",
                  "kling": "Một clip riêng (Kling, ảnh shot làm khung đầu)"}
        camera["video_route"] = st.selectbox("🎬 Đường gen video" + lk("video_route"), list(routes),
                                             index=list(routes).index(d.get("video_route")) if d.get("video_route") in routes else 0,
                                             format_func=routes.get, key=f"{k}_route",
                                             help="Gộp nhóm: nhiều shot một lần gen (model tự chia thời gian, shot ngắn dễ bị hụt). Shot cần "
                                                  "đúng khung với shot trước (cắt tại chỗ) nên đi khung đầu.")
        from core.delivery import TRANSITIONS_IN       # 07/10: the cut into the shot + a frame shake were set by no box
        names = {"cut": "Cắt thẳng", "match": "Khớp hình", "occlusion": "Che máy", "flash": "Chớp trắng", "dip": "Tối đi rồi sáng",
                 "whip": "Lia nhòe", "zoom_through": "Lao vào khung", "j_cut": "J-cut (tiếng vào trước)", "l_cut": "L-cut (tiếng kéo sau)"}
        t1, t2 = st.columns([3, 2])
        now = d.get("transition_in") if d.get("transition_in") in TRANSITIONS_IN else "cut"
        camera["transition_in"] = t1.selectbox("✨ Chuyển cảnh vào shot" + lk("transition_in"), list(TRANSITIONS_IN),
                                               index=list(TRANSITIONS_IN).index(now), format_func=lambda v: names.get(v, v),
                                               key=f"{k}_trans", help="Vẽ ở chỗ nối với shot trước khi dựng (Bản giao).")
        camera["shake_in"] = t2.checkbox("📳 Rung khung khi vào shot" + lk("shake_in"), bool(d.get("shake_in")), key=f"{k}_shake",
                                         help="Khung hình rung ngắn ngay lúc shot bắt đầu (như khi có tiếng va chạm) — vd khoảnh khắc hô biến.")
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
    # 0.5 s steps: the Director plans 2.5 s / 11.5 s shots — an int box cut them to 2 / 11 on every save (Khủng Long Đỏ, 06/10)
    duration = c10.number_input("Thời lượng đề xuất (giây)" + lk("duration_s"), 0.0, 15.0, float(d.get("duration_s") or 0), 0.5,
                                format="%.1f", key=f"{k}_dur", help="0 = để Director/Motion quyết")
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
        cap("🔒 = bạn đã sửa tay, Director chạy lại sẽ giữ nguyên.")
        if st.button("🔓 Cho Director điền lại các trường 🔒 của cảnh này", key=f"{k}_unlock"):
            act(lambda: llm_io.unlock_scene_fields(p, pid, idx))
            st.rerun()
    cap("Sửa cảnh đã có ảnh/video: các kết quả cũ sẽ hiện ⚠ cũ để bạn làm lại đúng phần bị ảnh hưởng.")
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
                       pause_before=(how.get("pause_before") or True) if r.get("Ngắt trước") else None)   # keeps "short"/"long"
            dlg.append({"speaker": str(r.get("Người nói") or "").strip(), "text": said,
                        "delivery": {x: v for x, v in how.items() if v is not None}})
        fields = {"location": location, "time": time_, "shot": shot, "mood": mood, "lighting": lighting,
                  "image_prompt": image_prompt, "location_asset": bg, "blocking": blocking, "emotional_intent": intent,
                  "sequence": int(sequence) or None, "camera_complexity": complexity, "shot_role": role,
                  "duration_s": round(float(duration), 2) or None}
        if rows or dlg:
            fields["dialogue"] = dlg
        if perf is not None:
            fields["performance"], fields["why"] = perf, why_text
        fields.update(camera)
        if char_names:
            fields["characters"] = cast
        if act(lambda: llm_io.update_scene(p, pid, idx, fields, text=text), f"Đã lưu cảnh {idx}"):
            st.rerun()
    with b2:
        if confirm_all(f"scene_del_{pid}_{idx}", [idx], "🗑 Xóa cảnh này", f"Xóa cảnh {idx}?", st, "Có, xóa cảnh"):
            if act(lambda: p.delete_scene(pid, idx), f"Đã xóa cảnh {idx}"):
                st.rerun()


@st.fragment
def scene_editor_box(pid: int, idx: int, char_names) -> None:
    """The scene editor is built only when asked for (02/10): an expander's body runs even when closed, and 8-30 editors (17 inputs, a table and
    two text areas each) made the whole script screen take 1+ s to draw. Being a fragment, typing in one scene redraws only that scene — on its
    own connection and a fresh read of the scene (the run that made the page lives in another thread)."""
    p = C.scoped(Pipeline(connect(C.DB)))
    if not st.toggle("✏ Mở trình sửa của cảnh này", key=f"sd_open_{pid}_{idx}"):
        return
    row = p.conn.execute("SELECT idx, title, state, data FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()
    if row is not None:
        scene_editor(p, pid, row, char_names)


def scene_list(p: Pipeline, pid: int, scenes, char_names) -> None:
    status = lineage.scan(p.conn, pid)
    by_idx = {r["idx"]: r for r in status.values()}
    with_bg = sum(1 for s in scenes if assets.scene_location(p.conn, pid, json.loads(s["data"] or "{}")))
    unit = "shot" if scenes and any(json.loads(s["data"] or "{}").get("shot_no") for s in scenes) else "cảnh"
    if with_bg != len(scenes):                            # v2 (P4): "all of them have one" is not worth a line
        cap(f"🏞 {with_bg}/{len(scenes)} {unit} đã có Background"
            + ("" if with_bg == len(scenes) else f" — {unit} chưa có thì không dựng được layout; chọn trong từng {unit} hoặc gắn địa điểm ở 1b"),
            summary=f"🏞 {with_bg}/{len(scenes)} {unit} đã có Background")
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
        say("warning", f"✂ Director đã bỏ {len(cuts)} câu thoại của kịch bản — xem lại (thêm lại câu vào shot bằng ô sửa shot nếu cần):\n"
            + "\n".join(f"- Cảnh {c['scene']} · {c['speaker']}: “{escape(c['text'])}”"
                         + (f" — ⚠ câu sau có thể là câu đáp lại ({escape(c['next'])})" if c["answered"] else "") for c in cuts),
            f"script-cuts-{pid}", f"✂ Director đã bỏ {len(cuts)} câu thoại của kịch bản — xem lại")
    try:
        fixed = (json.loads(p.project(pid)["director_raw"] or "{}").get("normalized") or []) if cuts or scenes else []
    except (ValueError, KeyError, IndexError, AttributeError):
        fixed = []
    if p.project(pid)["director_raw"]:
        with ui.fold("📋 Báo cáo Director & tổ làm phim", "đánh đổi · ghi chú kịch bản · Đạo diễn duyệt · kiểm tổ làm phim · code chuẩn hóa",
                     f"dirreport_{pid}", default_open=False) as report_open:     # E1.13: five cards → one
            if report_open:
                if fixed:
                    with st.expander(f"🔧 Code đã chuẩn hóa {len(fixed)} chỗ trong câu trả lời Director (thay vì hỏi lại Claude)"):
                        st.markdown("\n".join(f"- {escape(str(c))}" for c in fixed))
                paid = _paid_line(p, pid)
                if paid:
                    cap(paid)
                _crew_notes(p, pid)
                _director_review(p, pid)
    from contextlib import nullcontext
    # v2 (P3, long list): more than 6 rows scroll inside a labelled box instead of making the card as tall as the list
    with (st.container(height=460, key=f"script-rows-{pid}") if len(scenes) > 6 else nullcontext()):
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
                        cap("⚠ " + " · ".join(warn))
                lines = "; ".join(f"{x.get('speaker')}: {x.get('text')}" for x in d.get("dialogue") or [])
                head = [f"{_shots.label(d, s['idx'])} · {d.get('size')} · {d.get('role')} · {float(d.get('duration_s') or 0):g}s"
                        + (" · ⭐" if d.get("shot_role") == "hero" else ""),
                        (d.get("action") or "")[:60], lines[:70], scene_status_text(st_row) if st_row else ""]
                with st.expander("   |   ".join(x for x in head if x)):
                    scene_editor_box(pid, s["idx"], char_names)
                continue
            bits = [f"S{s['idx']:02d}" + (f" · nhóm {d['sequence']}" if d.get("sequence") else "")
                    + (" · ⭐" if d.get("shot_role") == "hero" else "") + (" · 🌀 phức tạp" if d.get("camera_complexity") == "complex" else ""),
                    " · ".join(filter(None, [d.get("time"), d.get("location")])), ", ".join(d.get("characters") or []),
                    scene_status_text(st_row) if st_row else ""]
            with st.expander("   |   ".join(x for x in bits if x)):
                scene_editor_box(pid, s["idx"], char_names)
    if st.button("➕ Thêm cảnh", key=f"scene_add_{pid}", help="Cho kịch bản mà công cụ không tự tách được"):
        act(lambda: p.add_scene_next(pid))
        st.rerun()


def _lock_and_go(p: Pipeline, pid: int) -> None:
    """Button callback: lock the Character Bible and move to Step 2 (a callback may still change the step selector)."""
    p = C.scoped(Pipeline(connect(C.DB)))                     # a callback runs in another thread than the one that made `p`
    try:
        llm_io.lock_character_bible(p, pid)
    except ERRORS as e:
        st.session_state["lock_error"] = str(e)
        return
    st.session_state["step"] = STEPS[2]                 # đợt 3: Storyboard (Ảnh + QC, Motion & giọng)

def reset_unworked_scenes(p: Pipeline, pid: int) -> None:
    """↺ Làm lại (the database part): delete the unlocked characters and the scenes without a job; S14.19: the person's remarks on those
    scenes stay, unlinked (user_feedback.scene_id is a foreign key — the delete failed with a remark attached)."""
    from core import feedback
    gone = [r[0] for r in p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs)", (pid,))]
    p.conn.execute("DELETE FROM characters WHERE project_id=? AND locked=0", (pid,))
    p.conn.execute("DELETE FROM motion_prompts WHERE scene_id IN (SELECT id FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs))", (pid,))
    feedback.detach(p.conn, scene_ids=gone)
    p.conn.execute("DELETE FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs)", (pid,))
    p.conn.commit()
    if not p.conn.execute("SELECT 1 FROM scenes WHERE project_id=?", (pid,)).fetchone():
        p.set_script_text(pid, None)
        p.conn.execute("DELETE FROM story_scenes WHERE project_id=?", (pid,))
        p.conn.commit()