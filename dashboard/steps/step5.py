"""Step 5: sound (music, effects, voice) and final render / subtitles / export."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import resize_panel


# ---- step 5a -------------------------------------------------------------------------
def preview_with_track(p: Pipeline, pid: int, music_path: str, tag: str) -> None:
    out = os.path.join(project_dir(pid, "output"), f"preview_music_{tag}.mp4")
    with st.spinner("Đang ghép bản xem thử (clip + nhạc)…"):
        ok = act(lambda: final_cut.preview_with_music(p, C.DATA, pid, music_path, out,
                                                      keep_audio=bool(p.project(pid)["video_audio"])),
                 "Đã tạo bản xem thử")
    if ok:
        st.session_state[f"prev5a_{pid}"] = (out, tag)
        st.rerun()


def step5a(p: Pipeline, pid: int):
    drafts_dir, selected_dir = music.project_dirs(C.DATA, pid)
    try:
        provider = music.audio_provider()
    except ProviderError as e:
        st.error(f"Clip AI audio: {e}")
        provider = None
    has_clips = any(c["path"] for c in final_cut.collect_clips(p, C.DATA, pid))

    files = os.listdir(selected_dir)
    with st.container(border=True):
        a, b = st.columns([3, 2], vertical_alignment="center")
        a.markdown(ui.card_title("Nhạc nền đang chọn") + (ui.badge(files[0], "b-ok") if files else ui.badge("chưa chọn / không dùng")),
                   unsafe_allow_html=True)
        if files:
            spath = os.path.join(selected_dir, files[0])
            ui.html(ui.waveform_svg(_peaks(spath, os.path.getmtime(spath))))
            st.audio(spath)
            if has_clips and b.button("🎬 Xem thử với video", key=f"prev_sel_{pid}"):
                preview_with_track(p, pid, spath, "selected")
        with st.expander("Upload nhạc có sẵn / bỏ nhạc"):
            up = st.file_uploader("Upload nhạc nền", type=["mp3", "wav", "m4a"], key=f"music_{pid}")
            if up and st.button("Dùng bản này"):
                music.clear_selected(selected_dir)
                with open(os.path.join(selected_dir, "selected" + os.path.splitext(up.name)[1]), "wb") as f:
                    f.write(up.getvalue())
                st.rerun()
            if st.button("Không dùng nhạc"):
                music.clear_selected(selected_dir)
                st.rerun()
    shown = st.session_state.get(f"prev5a_{pid}")
    if shown and os.path.exists(shown[0]):
        with st.container(border=True):
            ui.html(ui.card_title("Xem thử: clip + nhạc", shown[1]))
            show_video(shown[0], "Vừa")
    if not has_clips:
        st.caption("Chưa có clip nào (Bước 4) nên chưa thể xem thử nhạc cùng video.")

    with st.container(border=True):
        if provider is None:
            st.info("Chưa cấu hình tạo nhạc: đặt AUDIO_PROVIDER=clipai (hoặc VIDEO_PROVIDER=clipai) và CLIPAI_TOKEN, "
                    "hoặc upload nhạc có sẵn ở trên.")
        else:
            ui.html(ui.card_title("Music Brief", "gợi ý từ mood các cảnh — bạn sửa được") + ui.badge(
                provider.name + (" · giả lập" if provider.name == "mock-audio" else " · music_v2 · tốn credit"), "b-info"))
            brief = music.default_brief(p, pid)
            prompt = st.text_area("Prompt nhạc (≤ 2000 ký tự)", brief["prompt"], key=f"mprompt_{pid}", height=90)
            c1, c2, c3 = st.columns(3)
            seconds = c1.number_input("Độ dài (giây)", 3, 600, max(3, brief["length_ms"] // 1000), key=f"mlen_{pid}")
            instrumental = c2.checkbox("Không lời (instrumental)", brief["instrumental"], key=f"minst_{pid}")
            count = c3.number_input("Số bản nháp", 1, 5, 3, key=f"mcount_{pid}")
            b1, b2, b3 = st.columns([2, 2, 3])
            if b1.button(f"✨ Tạo {int(count)} bản nháp", type="primary", disabled=not prompt.strip()):
                n = music.submit_drafts(provider, drafts_dir, prompt, int(seconds) * 1000, instrumental, int(count),
                                        ledger=(p.conn, pid))
                st.toast(f"Đã gửi {n} bản")
                st.rerun()
            if b2.button("⟳ Kiểm tra + tải về"):
                counts = music.refresh_drafts(provider, drafts_dir)
                st.toast(f"Đang chạy {counts['running']} · xong {counts['succeeded']} · lỗi {counts['failed']}")
                st.rerun()
    drafts = music.load_drafts(drafts_dir)
    for start in range(0, len(drafts), 3):
        cols = st.columns(3)
        for col, (i, d) in zip(cols, list(enumerate(drafts))[start:start + 3]):
            with col, st.container(border=True):
                ui.html(f'<div class="cardhead"><b>Bản {chr(65 + i) if i < 26 else i + 1}</b><span class="grow"></span>'
                        f'{ui.state_badge(d["state"])}'
                        + (f' <span class="muted">{d["duration_ms"] / 1000:.0f}s</span>' if d.get("duration_ms") else "")
                        + '</div>')
                if d["state"] == "failed":
                    st.warning(f"Không tạo được: {d.get('message')} (không tự gửi lại để tránh tốn credit)")
                elif d.get("file"):
                    wpath = os.path.join(drafts_dir, d["file"])
                    ui.html(ui.waveform_svg(_peaks(wpath, os.path.getmtime(wpath))))
                    st.audio(wpath)
                    if has_clips and st.button("🎬 Xem thử với video", key=f"prevd_{pid}_{i}"):
                        preview_with_track(p, pid, wpath, f"draft_{i + 1}")
                    if st.button("Chọn bản này", key=f"pick_{pid}_{i}", type="primary"):
                        if act(lambda: music.select_draft(drafts_dir, selected_dir, i), "Đã chọn nhạc nền"):
                            st.rerun()
                else:
                    ui.html('<div class="wave"></div><span class="muted">đang tạo… bấm ‘Kiểm tra + tải về’</span>')
    if drafts and st.button("Xóa danh sách bản nháp"):
        shutil.rmtree(drafts_dir, ignore_errors=True)
        st.rerun()
    with st.expander("🎧 Hiệu ứng âm thanh & giọng đọc (tùy chọn)"):
        extras_section(p, pid, provider)


def extras_section(p: Pipeline, pid: int, provider):
    """Sound effects and voice-over: generate, preview, and choose what goes into the final mix."""
    directory = audio_lib.assets_dir(C.DATA, pid)
    with st.container(border=True):
        ui.html(ui.card_title("Hiệu ứng âm thanh & giọng đọc", "tùy chọn — trộn vào video ở Bước 5b"))
        if provider is None:
            st.caption("Cần cấu hình nhà cung cấp âm thanh (AUDIO_PROVIDER hoặc VIDEO_PROVIDER=clipai) để tạo mới.")
        else:
            t_sfx, t_tts = st.tabs(["SFX", "Giọng đọc (TTS)"])
            with t_sfx:
                s_prompt = st.text_input("Mô tả hiệu ứng (≤ 2000 ký tự)", key=f"sfx_p_{pid}",
                                         placeholder="A heavy stone door opens slowly")
                c1, c2, c3 = st.columns([2, 1, 2])
                s_sec = c1.number_input("Độ dài (giây, 0.5–30)", 0.5, 30.0, 3.0, 0.5, key=f"sfx_d_{pid}")
                s_loop = c2.checkbox("Loop", False, key=f"sfx_l_{pid}")
                if c3.button("✨ Tạo SFX", disabled=not s_prompt.strip(), key=f"sfx_go_{pid}"):
                    entry = audio_lib.submit_sfx(provider, directory, s_prompt, s_sec, s_loop, ledger=(p.conn, pid))
                    st.toast("Đã gửi SFX" if entry["asset_id"] else f"Lỗi: {entry['message']}")
                    st.rerun()
            with t_tts:
                voices = st.session_state.get(f"voices_{pid}")
                if voices is None:
                    try:
                        voices = provider.voice_actors(owner="official")
                    except ProviderError as e:
                        st.error(f"Không lấy được danh sách giọng: {e}")
                        voices = []
                    st.session_state[f"voices_{pid}"] = voices
                if not voices:
                    st.caption("Chưa có giọng nào để chọn.")
                else:
                    v = st.selectbox("Giọng", voices, format_func=lambda x: f"{x.get('name')} (#{x.get('id')})",
                                     key=f"tts_v_{pid}")
                    t_text = st.text_area("Nội dung (≤ 2000 ký tự)", key=f"tts_t_{pid}", height=80)
                    d1, d2 = st.columns(2)
                    t_model = d1.selectbox("Model", ["eleven_v3", "eleven_multilingual_v2", "eleven_turbo_v2_5"],
                                           key=f"tts_m_{pid}")
                    t_lang = d2.text_input("Mã ngôn ngữ (tùy chọn, vd vi, en)", key=f"tts_l_{pid}")
                    if st.button("✨ Tạo giọng đọc", disabled=not t_text.strip(), key=f"tts_go_{pid}"):
                        entry = audio_lib.submit_tts(provider, directory, t_text, int(v["id"]), str(v.get("name", "")),
                                                     t_model, t_lang.strip() or None, ledger=(p.conn, pid))
                        st.toast("Đã gửi giọng đọc" if entry["asset_id"] else f"Lỗi: {entry['message']}")
                        st.rerun()
            if st.button("⟳ Kiểm tra + tải về", key=f"ax_refresh_{pid}"):
                counts = audio_lib.refresh(provider, directory)
                st.toast(f"Đang chạy {counts['running']} · xong {counts['succeeded']} · lỗi {counts['failed']}")
                st.rerun()
        overlaps = audio_lib.overlapping_tts(directory)
        if overlaps:
            st.warning(f"⚠ {len(overlaps)} chỗ giọng đọc đè lên nhau (2 người nói cùng lúc) — thời điểm bắt đầu "
                      "chỉ là ước lượng, không khớp với độ dài giọng đọc thật đã tạo ra.")
            if st.button("🗓 Xếp lại theo thoại (hết chồng tiếng)", key=f"ax_reschedule_{pid}"):
                cues = subtitles.build_cues(p, C.DATA, pid, st.session_state.get(f"tr_{pid}", "cut"),
                                            float(st.session_state.get(f"fade_{pid}", 1.0)))
                n = audio_lib.schedule_by_cues(directory, cues)
                st.toast(f"Đã xếp lại {n} dòng giọng đọc theo đúng thứ tự, không còn chồng tiếng" if n else
                        "Không khớp được dòng thoại nào với phụ đề (kiểm tra lại nội dung có đúng như kịch bản không)")
                st.rerun()
        items = audio_lib.load(directory)
        for i, e in enumerate(items):
            with st.container(border=True):
                ui.html(f'<div class="cardhead"><b>{audio_lib.KINDS.get(e["kind"], e["kind"])}</b>'
                        f'<span class="muted">{e["label"][:90]}</span><span class="grow"></span>{ui.state_badge(e["state"])}</div>')
                if e["state"] == "failed":
                    st.warning(f"Không tạo được: {e.get('message')} (không tự gửi lại để tránh tốn credit)")
                elif e.get("file"):
                    st.audio(os.path.join(directory, e["file"]))
                a, b, c, d = st.columns([2, 1.3, 2, 1], vertical_alignment="center")
                use = a.checkbox("Đưa vào bản ghép", e["use"], key=f"ax_use_{pid}_{i}", disabled=e["state"] != "succeeded")
                start = b.number_input("Bắt đầu (giây)", 0.0, 600.0, float(e["start"]), 0.5, key=f"ax_st_{pid}_{i}")
                vol = c.slider("Âm lượng", 0.0, 2.0, float(e["volume"]), 0.05, key=f"ax_vol_{pid}_{i}")
                if d.button("Xóa", key=f"ax_rm_{pid}_{i}"):
                    audio_lib.remove(directory, i)
                    st.rerun()
                if e["state"] == "succeeded" and (use, start, vol) != (e["use"], e["start"], e["volume"]):
                    audio_lib.set_mix(directory, i, use, start, vol)


# ---- step 5b -------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _peaks(path: str, mtime: float):
    return waveform.peaks(path)


@st.cache_data(show_spinner=False)
def _has_audio(path: str, mtime: float) -> bool:
    return ffmpeg_studio.has_audio(path)


@st.cache_data(show_spinner=False)
def _probe(path: str, mtime: float, requested):
    return final_cut.clip_seconds(path, requested)


def step5b(p: Pipeline, pid: int):
    vdir = project_dir(pid, "videos")
    clips = final_cut.collect_clips(p, C.DATA, pid)
    present = [c for c in clips if c["path"]]
    missing = [c for c in clips if not c["path"]]
    left, right = st.columns([1.7, 1], gap="large")
    chosen, durations = [], []
    out = os.path.join(project_dir(pid, "output"), "FINAL_VIDEO.mp4")
    with left:
        with st.container(border=True):
            ui.html(ui.card_title("Clip theo thứ tự cảnh", f"{len(present)} có sẵn / {len(clips)} mục · lấy tự động từ Bước 4"))
            vsize = "Vừa"
            if not present:
                st.info("Chưa có clip nào. Chạy Bước 4 (gen video) hoặc nhập clip thủ công bên dưới.")
            names = ", ".join(f"cảnh {c['idx']}" + (f" ({c['state']})" if c["state"] else "") for c in missing if c["idx"])
            if names:
                st.warning(f"Thiếu clip: {names} — bản ghép sẽ bỏ qua các cảnh này.")
            for c in present:
                label = f"Cảnh {c['idx']} — {c['title']}" if c["idx"] else c["title"]
                base = os.path.basename(c["path"])
                real = _probe(c["path"], os.path.getmtime(c["path"]), c["requested_sec"])
                a, b, d = st.columns([3, 1, 1], vertical_alignment="center")
                use = a.checkbox(label, True, key=f"use_{pid}_{base}")
                sec = d.number_input("Giây", 0.5, 60.0, float(round(real, 2)), 0.1, key=f"sec_{pid}_{base}",
                                     label_visibility="collapsed")
                if b.checkbox("Xem", False, key=f"see_{pid}_{base}"):
                    show_video(c["path"], vsize)
                if use:
                    chosen.append(c["path"])
                    durations.append(sec)
                if c.get("scene_id"):
                    scene_expander(p, c["scene_id"], with_motion=True)
            with st.expander("Nhập clip thủ công (tên file theo thứ tự, vd 01.mp4)"):
                up = st.file_uploader("Clip .mp4", type=["mp4"], accept_multiple_files=True, key=f"vid_{pid}")
                if up and st.button("Lưu clip"):
                    for f in up:
                        with open(os.path.join(vdir, f.name), "wb") as fh:
                            fh.write(f.getvalue())
                    st.rerun()
        if os.path.exists(out):
            with st.container(border=True):
                ui.html(ui.card_title("Preview", "FINAL_VIDEO.mp4") + ui.badge("succeeded", "b-ok")
                        + f' <span class="muted">{os.path.getsize(out) / 1e6:.1f} MB</span>')
                show_video(out, "Vừa")
                with open(out, "rb") as f:
                    st.download_button("⬇ Tải FINAL_VIDEO.mp4", f, file_name="FINAL_VIDEO.mp4", mime="video/mp4")
                resize_panel(pid, out)
        subtitle_panel(p, pid, out)
        music_branch(p, pid)
    with right, st.container(border=True):
        ui.html(ui.card_title("Tùy chọn render"))
        transition = st.radio("Transition", ["cut", "crossfade", "dip_to_black"], horizontal=True, key=f"tr_{pid}",
                              format_func=lambda t: {"cut": "Cut", "crossfade": "Cross-fade", "dip_to_black": "Dip to black"}[t])
        fade = st.slider("Thời gian chuyển cảnh (giây)", 0.3, 2.0, 1.0, 0.1, key=f"fade_{pid}",
                         disabled=transition == "cut")
        music_dir = project_dir(pid, "music")
        tracks = os.listdir(music_dir)
        volume = st.slider("Âm lượng nhạc nền", 0.0, 1.0, 0.6, 0.05, key=f"vol_{pid}", disabled=not tracks)
        st.caption(f"Nhạc nền: {tracks[0]} (chọn ở Bước 5a)" if tracks else "Không có nhạc nền (chọn ở Bước 5a nếu cần).")
        keep = st.checkbox("🔊 Giữ âm thanh gốc của clip (lời thoại do model tạo)", bool(p.project(pid)["video_audio"]),
                           key=f"keepaud_{pid}", help="Nhạc nền được trộn bên dưới lời thoại. Cần MỌI clip đã chọn có âm thanh.")
        if keep and chosen:
            silent_clips = [os.path.basename(c) for c in chosen if not _has_audio(c, os.path.getmtime(c))]
            if silent_clips:
                st.warning("Clip không có âm thanh: " + ", ".join(silent_clips) + " → âm thanh gốc sẽ bị bỏ cho cả bản ghép.")
        extras = audio_lib.mix_list(audio_lib.assets_dir(C.DATA, pid))
        st.caption(f"Hiệu ứng / giọng đọc đưa vào bản ghép: {len(extras)} (chọn ở Bước 5a)")
        problems = final_cut.render_problems(durations, transition, fade)
        for msg in problems:
            st.warning(msg)
        if durations and not problems:
            st.info(f"Tổng thời lượng dự kiến: {final_cut.total_seconds(durations, transition, fade):.1f} giây · {len(chosen)} clip")
        if st.button("▶ Render Final", disabled=bool(problems), type="primary", width="stretch"):
            music_file = os.path.join(music_dir, tracks[0]) if tracks else None
            with st.spinner("Đang render…"):
                ok = act(lambda: ffmpeg_studio.render_final(chosen, out, durations, transition, fade, music_file, volume, extras, keep),
                         "Render xong")
            if ok:
                st.rerun()


def subtitle_panel(p: Pipeline, pid: int, out: str) -> None:
    """Step 5: automatic subtitles from the script's dialogue (language, font, size...), burned into a copy of the final video."""
    settings = subtitles.get_settings(p, pid)
    fonts = subtitles.discover()
    default = subtitles.default_font(fonts)
    with st.expander("🔤 Phụ đề tự động (từ lời thoại trong kịch bản)", expanded=os.path.exists(out)):
        st.caption("Lấy các dòng thoại `TÊN: lời` của từng cảnh, chia thời gian trong clip theo độ dài câu (ước lượng, **không phải nhận dạng "
                   "giọng nói**), có thể dịch sang ngôn ngữ khác bằng Claude, rồi in vào một bản sao của video cuối. Bạn sửa được chữ và "
                   "thời điểm trước khi in.")
        llm = llm_client()
        c1, c2, c3 = st.columns([2, 2, 1.4])
        langs = list(subtitles.LANGS)
        lang = c1.selectbox("Ngôn ngữ phụ đề", langs, index=langs.index(settings["lang"]) if settings["lang"] in langs else 0,
                            format_func=lambda k: subtitles.LANGS[k], key=f"sub_lang_{pid}")
        families = [f.family for f in fonts]
        current = settings["font"] if settings["font"] in families else (default.family if default else None)
        font_name = c2.selectbox("Font", families, index=families.index(current) if current in families else 0, key=f"sub_font_{pid}",
                                 help="Mặc định GFF Latin Bold (font Free Fire). Font không có đủ chữ của ngôn ngữ chọn sẽ được đổi tự động.") \
            if families else None
        size = c3.selectbox("Cỡ chữ", list(subtitles.SIZES), index=list(subtitles.SIZES).index(settings["size"]),
                            format_func=lambda k: subtitles.SIZES[k][0], key=f"sub_size_{pid}")
        d1, d2, d3 = st.columns([1.4, 1.4, 2.2], vertical_alignment="bottom")
        pos = d1.selectbox("Vị trí", list(subtitles.POSITIONS), index=list(subtitles.POSITIONS).index(settings["pos"]),
                           format_func=lambda k: subtitles.POSITIONS[k][0], key=f"sub_pos_{pid}")
        color = d2.selectbox("Màu chữ", list(subtitles.COLORS), index=list(subtitles.COLORS).index(settings["color"]),
                             format_func=lambda k: subtitles.COLORS[k][0], key=f"sub_color_{pid}")
        speaker = d3.checkbox("Ghi tên người nói trước câu", settings["speaker"], key=f"sub_speaker_{pid}")
        auto = st.checkbox("Tự thêm phụ đề khi chạy tự động hoàn toàn", settings["enabled"], key=f"sub_auto_{pid}")
        new = {"enabled": auto, "lang": lang, "font": font_name or "", "size": size, "pos": pos, "color": color, "speaker": speaker}
        if new != {k: settings[k] for k in new}:
            subtitles.save_settings(p, pid, new)
        up = st.file_uploader("Thêm font riêng (.ttf / .otf)", type=["ttf", "otf"], key=f"sub_fontup_{pid}")
        if up is not None and st.button("Thêm font này", key=f"sub_fontadd_{pid}"):
            try:
                subtitles.save_uploaded_font(up.name, up.getvalue())
            except subtitles.SubtitleError as e:
                st.error(str(e))
            else:
                st.rerun()
        if lang != "src" and llm is None:
            st.markdown(":orange[Dịch sang ngôn ngữ khác cần Claude (ANTHROPIC_API_KEY hoặc LLM_PROVIDER=claude_cli). Chưa có thì chỉ dùng được “Giữ nguyên ngôn ngữ kịch bản”.]")
        key = f"sub_cues_{pid}"
        if st.button("📝 Tạo danh sách phụ đề", key=f"sub_make_{pid}", type="primary", disabled=lang != "src" and llm is None):
            try:
                cues = subtitles.build_cues(p, C.DATA, pid, st.session_state.get(f"tr_{pid}", "cut"), float(st.session_state.get(f"fade_{pid}", 1.0)))
                if not cues:
                    st.info("Chưa có dòng thoại nào (cần dòng `TÊN: lời` trong cảnh) hoặc chưa có clip ở Bước 4.")
                else:
                    with st.spinner("Đang dịch…" if lang != "src" else "Đang tạo…"):
                        cues = subtitles.translate(llm, cues, lang)
                    st.session_state[key] = [{"Cảnh": c.scene, "Người nói": c.speaker, "Bắt đầu (s)": c.start, "Kết thúc (s)": c.end,
                                              "Nội dung": c.text} for c in cues]
            except ERRORS + (subtitles.SubtitleError,) as e:
                st.error(str(e))
        rows = st.session_state.get(key)
        if rows:
            edited = st.data_editor(rows, hide_index=True, width="stretch", key=f"sub_table_{pid}",
                                    disabled=["Cảnh", "Người nói"], num_rows="fixed")
            table = edited.to_dict("records") if hasattr(edited, "to_dict") else edited
            cues = [subtitles.Cue(float(r["Bắt đầu (s)"]), float(r["Kết thúc (s)"]), str(r["Nội dung"]).strip(), str(r["Người nói"] or ""),
                                  r["Cảnh"]) for r in table if str(r["Nội dung"]).strip()]
            font, note = subtitles.font_for_text(subtitles.font_by_family(fonts, font_name) if font_name else default, fonts,
                                                 " ".join(c.text for c in cues))
            if note:
                st.markdown(f":orange[{escape(note)}]")
            bad = [c for c in cues if c.end <= c.start]
            if bad:
                st.error("Có dòng kết thúc trước khi bắt đầu: sửa lại cột thời gian.")
            b1, b2 = st.columns(2)
            srt = subtitles.to_srt(cues, speaker)
            b1.download_button("⬇ Tải file .srt", srt.encode("utf-8"), file_name=f"phu_de_{lang}.srt", mime="application/x-subrip",
                               key=f"sub_srt_{pid}")
            if b2.button("🔥 In phụ đề vào video", key=f"sub_burn_{pid}", disabled=not os.path.exists(out) or bool(bad)):
                target = os.path.join(project_dir(pid, "output"), f"FINAL_VIDEO_sub_{lang}.mp4")
                try:
                    with st.spinner("Đang in phụ đề (mã hóa lại video)…"):
                        res = subtitles.burn(out, cues, target, font, size, pos, color, speaker)
                except ERRORS + (subtitles.SubtitleError,) as e:
                    st.error(str(e))
                else:
                    st.session_state[f"sub_done_{pid}"] = res
            if not os.path.exists(out):
                st.caption("Ghép video cuối trước, rồi mới in được phụ đề.")
        done = st.session_state.get(f"sub_done_{pid}")
        if done and os.path.exists(done["video"]):
            st.success(f"Đã in {done['cues']} dòng bằng font {done['font']}" + ("" if done["font_verified"] else " (không xác nhận được font, có thể bị thay)"))
            show_video(done["video"], "Vừa")
            with open(done["video"], "rb") as f:
                st.download_button(f"⬇ Tải {os.path.basename(done['video'])}", f, file_name=os.path.basename(done["video"]), mime="video/mp4",
                                   key=f"sub_dl_{pid}")


def sfx_assistant(p: Pipeline, pid: int) -> None:
    """One button: AI reads the scenes and the sound library and proposes effects; the person reviews, edits and adds them."""
    n = sound_lib.counts(p.conn)
    if not n:
        return
    key = f"sfxplan_{pid}"
    with st.container(border=True):
        ui.html(ui.card_title("🎧 Hiệu ứng âm thanh", "AI đọc kịch bản + kho của bạn, đề xuất chỗ cần điểm nhấn / chuyển cảnh"))
        if not n.get("sfx"):
            st.caption("Kho âm thanh chưa có hiệu ứng nào.")
        else:
            wish = st.text_input("Yêu cầu thêm (không bắt buộc)", key=f"sfx_wish_{pid}",
                                 placeholder="vd: ít thôi, chỉ ở chuyển cảnh · thêm tiếng va chạm ở cảnh 3")
            transition = st.session_state.get(f"tr_{pid}", "cut")
            fade = float(st.session_state.get(f"fade_{pid}", 1.0))
            if st.button("🤖 AI tự đề xuất hiệu ứng", key=f"sfx_ai_go_{pid}", type="primary"):
                client = llm_client()
                try:
                    with st.spinner("AI đang đọc các cảnh và chọn hiệu ứng…"):
                        st.session_state[key] = sfx_plan.propose(client, p, C.DATA, pid, transition, fade, wish)
                except (sfx_plan.SfxPlanError, llm_runner.LlmError) as e:
                    st.error(str(e))
            plan = st.session_state.get(key)
            if plan is not None:
                if plan["summary"]:
                    st.info(plan["summary"])
                if not plan["cues"]:
                    st.caption("AI không thấy chỗ nào cần thêm hiệu ứng.")
                else:
                    import pandas as pd
                    frame = pd.DataFrame([{"Dùng": True, "Giây": c["at"], "Cảnh": c["scene"], "Hiệu ứng": c["name"], "Thư mục": c["folder"],
                                           "Âm lượng": c["volume"], "Vì sao": c["reason"]} for c in plan["cues"]])
                    edited = st.data_editor(frame, key=f"sfx_table_{pid}", hide_index=True, width="stretch",
                                            disabled=["Cảnh", "Hiệu ứng", "Thư mục", "Vì sao"],
                                            column_config={"Giây": st.column_config.NumberColumn(min_value=0.0, step=0.1),
                                                           "Âm lượng": st.column_config.NumberColumn(min_value=0.0, max_value=1.5, step=0.05)})
                    b1, b2 = st.columns([2, 1])
                    if b1.button("✅ Thêm các hiệu ứng đã chọn vào video", key=f"sfx_apply_{pid}", type="primary"):
                        chosen = [{"id": plan["cues"][i]["id"], "at": float(row["Giây"]), "volume": float(row["Âm lượng"])}
                                  for i, row in edited.iterrows() if row["Dùng"]]
                        added = sfx_plan.apply(p, C.DATA, pid, chosen)
                        st.session_state.pop(key, None)
                        st.toast(f"Đã thêm {added} hiệu ứng (chỉnh tiếp ở mục Hiệu ứng âm thanh & giọng đọc bên trên)")
                        st.rerun()
                    if b2.button("Bỏ đề xuất", key=f"sfx_drop_{pid}"):
                        st.session_state.pop(key, None)
                        st.rerun()
        if n.get("music"):
            mode = p.project(pid)["music_mode"] == "library"
            auto = st.checkbox("Nhạc nền: ưu tiên lấy từ kho của tôi thay vì để AI tạo (tiết kiệm credit; AI tạo nhạc vẫn là mặc định)", mode,
                               key=f"music_mode_{pid}")
            if auto != mode:
                p.conn.execute("UPDATE projects SET music_mode=? WHERE id=?", ("library" if auto else None, pid))
                p.conn.commit()


def step5(p: Pipeline, pid: int):
    """Music and the final render are one step now."""
    ui.html(ui.card_title("🎞 Ghép & render", "cắt ghép clip; nhạc nền và phụ đề là các nhánh phụ"))
    step5b(p, pid)


def music_branch(p: Pipeline, pid: int) -> None:
    """Background music as a side branch of the render step (like the subtitles): AI-made music first, the own library as support."""
    _, selected_dir = music.project_dirs(C.DATA, pid)
    st.markdown("---")
    ui.html(ui.card_title("🎵 Nhạc nền (nhánh phụ)", "AI tạo nhạc theo mood các cảnh; kho nhạc của bạn chỉ hỗ trợ")
            + (ui.badge("đã chọn", "b-ok") if os.listdir(selected_dir) else ui.badge("chưa chọn")))
    step5a(p, pid)
    sfx_assistant(p, pid)
