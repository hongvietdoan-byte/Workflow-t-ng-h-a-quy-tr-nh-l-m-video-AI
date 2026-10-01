"""Step 5: sound (music, effects, voice) and final render / subtitles / export."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C


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
    """Background music: brief written by Claude from the scenes (or the template), drafts, choice; own file or none."""
    drafts_dir, selected_dir = music.project_dirs(C.DATA, pid)
    try:
        provider = music.audio_provider()
    except ProviderError as e:
        st.error(f"Clip AI audio: {e}")
        provider = None
    has_clips = any(c["path"] for c in final_cut.collect_clips(p, C.DATA, pid))
    files = os.listdir(selected_dir)
    off = music.is_off(p, pid)
    with st.container(border=True):
        a, b = st.columns([3, 2], vertical_alignment="center")
        a.markdown(ui.card_title("🎵 Nhạc nền đang chọn") + (ui.badge(files[0], "b-ok") if files else
                                                             ui.badge("không dùng nhạc (đã chọn)", "b-info") if off else ui.badge("chưa chọn")),
                   unsafe_allow_html=True)
        if off and not files:
            st.caption("Chạy tự động sẽ không tạo nhạc cho dự án này. Chọn/tải một bản nhạc bên dưới để dùng lại nhạc.")
        if files:
            spath = os.path.join(selected_dir, files[0])
            ui.html(ui.waveform_svg(_peaks(spath, os.path.getmtime(spath))))
            st.audio(spath)
            if has_clips and b.button("🎬 Xem thử với video", key=f"prev_sel_{pid}"):
                preview_with_track(p, pid, spath, "selected")
        with st.expander("Tải nhạc có sẵn / bỏ nhạc"):
            up = st.file_uploader("Tải nhạc nền", type=["mp3", "wav", "m4a"], key=f"music_{pid}")
            if up and st.button("Dùng bản này", key=f"music_up_go_{pid}"):
                music.clear_selected(selected_dir)
                with open(os.path.join(selected_dir, "selected" + os.path.splitext(up.name)[1]), "wb") as f:
                    f.write(up.getvalue())
                music.set_off(p, pid, False)
                st.rerun()
            if st.button("Không dùng nhạc", key=f"music_none_{pid}", disabled=off and not files,
                         help="Được ghi nhớ: chạy tự động sẽ không tự tạo nhạc (tốn credit) cho dự án này"):
                music.clear_selected(selected_dir)
                music.set_off(p, pid, True)
                st.rerun()
    shown = st.session_state.get(f"prev5a_{pid}")
    if shown and os.path.exists(shown[0]):
        with st.container(border=True):
            ui.html(ui.card_title("Xem thử: clip + nhạc", shown[1]))
            show_video(shown[0])
    drafts_now = music.load_drafts(drafts_dir)
    with ui.fold("Brief nhạc & bản nháp", f"🎼 {sum(1 for d in drafts_now if d['state'] == 'succeeded')} bản nháp xong"
                 + (f" · đang chọn {files[0]}" if files else " · chưa chọn") + " · mở để viết brief / soạn thêm",
                 f"mbrief_fold_{pid}", default_open=not files) as brief_open:  # S9 E5.3
        if brief_open:
            if provider is None:
                st.info("Chưa cấu hình tạo nhạc (AUDIO_PROVIDER=clipai hoặc VIDEO_PROVIDER=clipai + CLIPAI_TOKEN); vẫn tải được nhạc có sẵn ở trên.")
            else:
                ui.html(ui.card_title("Brief nhạc", "Claude viết theo thể loại, ý đồ và nhịp từng cảnh — bạn sửa được") + ui.badge(
                    provider.name + (" · giả lập" if provider.name == "mock-audio" else " · music_v2 · tốn credit"), "b-info"))
                key = f"mbrief_{pid}"
                client = llm_client()
                if st.button("🤖 Claude viết brief nhạc" + cost.llm_tag(cost.llm_estimate(p.conn, "music_brief", 1)), key=f"mbrief_ai_{pid}", disabled=client is None, help=None if client else claude_hint()):
                    with st.spinner("Claude đang viết brief…"):
                        brief = claude_tasks.music_brief(p, pid, client)
                    st.session_state[key] = brief
                    st.session_state[f"mprompt_{pid}"] = brief["prompt"]
                    st.session_state[f"mlen_{pid}"] = max(3, brief["length_ms"] // 1000)
                brief = st.session_state.get(key) or _timed_brief(p, pid) or music.default_brief(p, pid)
                if brief.get("timed"):
                    st.caption(f"Theo nhịp dựng: {brief['bpm']} BPM, đổi đoạn ở "
                               + (", ".join(f"{t:.1f}s" for t in brief["turns"]) or "—") + " — nên tạo 2 bản rồi chọn bản khớp hơn")
                    tone = ((brief.get("intent") or {}).get("tone") or {})
                    if tone:
                        from core import music_intent
                        st.caption(f"Giọng điệu nhạc: **{music_intent.TONE_VI.get(tone.get('tone'), tone.get('tone'))}** — {tone.get('why', '')}")
                    for note in brief.get("notes") or []:
                        st.warning(note)
                    with st.expander("📋 Phiếu spotting (đọc / góp ý trước khi tạo nhạc)"):   # S0.15 M8
                        from core import music_timing
                        st.markdown(music_timing.spotting(p, pid, brief))
                if brief.get("brief"):
                    st.caption(f"{brief['brief'].get('genre', '')} · {brief['brief'].get('tempo_bpm', '')} BPM · {brief['brief'].get('structure', '')}")
                prompt = st.text_area("Prompt nhạc (≤ 2000 ký tự)", brief["prompt"], key=f"mprompt_{pid}", height=90)
                c1, c2, c3 = st.columns(3)
                seconds = c1.number_input("Độ dài (giây)", 3, 600, max(3, brief["length_ms"] // 1000), key=f"mlen_{pid}")
                instrumental = c2.checkbox("Không lời (instrumental)", brief["instrumental"], key=f"minst_{pid}")
                count = c3.number_input("Số bản nháp", 1, 5, 3, key=f"mcount_{pid}")
                b1, b2 = st.columns(2)
                if b1.button(f"✨ Tạo {int(count)} bản nháp" + budget.audio_tag(p.conn, int(count)), type="primary", disabled=not prompt.strip(), key=f"mdraft_{pid}"):
                    n = music.submit_drafts(provider, drafts_dir, prompt, int(seconds) * 1000, instrumental, int(count), ledger=(p.conn, pid))
                    st.toast(f"Đã gửi {n} bản")
                    st.rerun()
                if b2.button("⟳ Kiểm tra + tải nhạc về", key=f"mrefresh_{pid}"):
                    counts = music.refresh_drafts(provider, drafts_dir)
                    st.toast(f"Đang chạy {counts['running']} · xong {counts['succeeded']} · lỗi {counts['failed']}")
                    st.rerun()
    drafts = music.load_drafts(drafts_dir)
    show_drafts = brief_open or any(d["state"] == "running" for d in drafts)   # S9 E5.3: the drafts fold with the brief
    for start in (range(0, len(drafts), 3) if show_drafts else []):
        cols = st.columns(3)
        for col, (i, d) in zip(cols, list(enumerate(drafts))[start:start + 3]):
            with col, st.container(border=True):
                ui.html(f'<div class="cardhead"><b>Bản {chr(65 + i) if i < 26 else i + 1}</b><span class="grow"></span>'
                        f'{ui.state_badge(d["state"], "audio")}'
                        + (f' <span class="muted">{d["duration_ms"] / 1000:.0f}s</span>' if d.get("duration_ms") else "") + '</div>')
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
                            music.set_off(p, pid, False)
                            st.rerun()
                else:
                    ui.html('<div class="wave"></div><span class="muted">đang tạo… bấm “Kiểm tra + tải nhạc về”</span>')
    if show_drafts and drafts and confirm_all(f"mclear_{pid}", [d.get("file") or str(i) for i, d in enumerate(drafts)], "Xóa danh sách bản nháp",
                              "Xóa mọi bản nháp nhạc? Các bản đã tạo (đã trả tiền) sẽ mất.", st, "Có, xóa"):
        shutil.rmtree(drafts_dir, ignore_errors=True)
        st.rerun()


def extras_section(p: Pipeline, pid: int, provider):
    """Sound effects and voice-over: generate, preview, and choose what goes into the final mix."""
    directory = audio_lib.assets_dir(C.DATA, pid)
    with st.container(border=True):
        ui.html(ui.card_title("Hiệu ứng âm thanh & giọng đọc", "tùy chọn — trộn vào video khi dựng (5.3)"))
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
                if c3.button("✨ Tạo SFX" + budget.audio_tag(p.conn), disabled=not s_prompt.strip(), key=f"sfx_go_{pid}"):
                    entry = audio_lib.submit_sfx(provider, directory, s_prompt, s_sec, s_loop, ledger=(p.conn, pid))
                    st.toast("Đã gửi SFX" if entry["asset_id"] else f"Lỗi: {entry['message']}")
                    st.rerun()
            with t_tts:
                voices = st.session_state.get(f"voices_{pid}")
                if voices is None:
                    try:
                        voices = voice.library(provider)       # official + team voices, the preferred Vietnamese ones first
                    except ProviderError as e:
                        st.error(f"Không lấy được danh sách giọng: {e}")
                        voices = []
                    st.session_state[f"voices_{pid}"] = voices
                if not voices:
                    st.caption("Chưa có giọng nào để chọn.")
                else:
                    v = st.selectbox("Giọng", voices, key=f"tts_v_{pid}",
                                     format_func=lambda x: ("⭐ " if voice.preferred(x) else "") + f"{voice.display_name(x)} (#{x.get('id')})")
                    t_text = st.text_area("Nội dung (≤ 2000 ký tự)", key=f"tts_t_{pid}", height=80)
                    d1, d2 = st.columns(2)
                    t_model = d1.selectbox("Model", ["eleven_v3", "eleven_turbo_v2_5", "eleven_multilingual_v2"],
                                           key=f"tts_m_{pid}")
                    t_lang = d2.text_input("Mã ngôn ngữ (tùy chọn, vd vi, en)", key=f"tts_l_{pid}")
                    if st.button("✨ Tạo giọng đọc" + budget.audio_tag(p.conn), disabled=not t_text.strip(), key=f"tts_go_{pid}"):
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
                sig = f"{i}_{int(bool(e['use']))}_{e['start']}_{e['volume']}"   # file changed elsewhere (voice placement) -> fresh widgets
                use = a.checkbox("Đưa vào bản ghép", e["use"], key=f"ax_use_{pid}_{sig}", disabled=e["state"] != "succeeded")
                start = b.number_input("Bắt đầu (giây)", 0.0, 600.0, float(e["start"]), 0.5, key=f"ax_st_{pid}_{sig}")
                vol = c.slider("Âm lượng", 0.0, 2.0, float(e["volume"]), 0.05, key=f"ax_vol_{pid}_{sig}")
                if d.button("Xóa", key=f"ax_rm_{pid}_{i}", help="Chuyển file vào thùng rác của dự án (khôi phục được trong thời hạn lưu)"):
                    if e.get("file"):
                        trash.move_to_trash(os.path.join(directory, e["file"]), C.DATA, pid, "audio", "xóa ở Bước 5")
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




def subtitle_panel(p: Pipeline, pid: int, out: str = None) -> None:
    """5.4 Subtitles: from the voiced lines (exact timing) or the script's dialogue (estimated), language, font, colour per character,
    reading-speed check, .srt / .xlsx review sheet, burned into a copy of the latest render."""
    settings = subtitles.get_settings(p, pid)
    fonts = subtitles.discover()
    default = subtitles.default_font(fonts)
    final = lineage.latest_output(p.conn, pid, "final")
    has_final = final is not None and os.path.exists(final["path"])
    with st.expander("🔤 Phụ đề", expanded=has_final and settings["enabled"]):
        st.caption("Câu đã có giọng thoại lấy đúng thời điểm giọng nói; câu chưa có giọng thì ước lượng theo độ dài câu. Dịch được sang "
                   "ngôn ngữ khác bằng Claude. In vào một bản sao — video cuối gốc giữ nguyên.")
        llm = llm_client()
        c1, c2, c3 = st.columns([2, 2, 1.4])
        langs = list(subtitles.LANGS)
        lang = c1.selectbox("Ngôn ngữ phụ đề", langs, index=langs.index(settings["lang"]) if settings["lang"] in langs else 0,
                            format_func=lambda k: subtitles.LANGS[k], key=f"sub_lang_{pid}")
        families = [f.family for f in fonts]
        current = settings["font"] if settings["font"] in families else (default.family if default else None)
        font_name = c2.selectbox("Font", families, index=families.index(current) if current in families else 0, key=f"sub_font_{pid}",
                                 help="Mặc định GFF Latin Bold (font Free Fire). Font thiếu chữ của ngôn ngữ chọn sẽ được đổi tự động.") if families else None
        size = c3.selectbox("Cỡ chữ", list(subtitles.SIZES), index=list(subtitles.SIZES).index(settings["size"]),
                            format_func=lambda k: subtitles.SIZES[k][0], key=f"sub_size_{pid}")
        d1, d2, d3, d4 = st.columns([1.3, 1.3, 1.8, 1.8], vertical_alignment="bottom")
        pos = d1.selectbox("Vị trí", list(subtitles.POSITIONS), index=list(subtitles.POSITIONS).index(settings["pos"]),
                           format_func=lambda k: subtitles.POSITIONS[k][0], key=f"sub_pos_{pid}")
        color = d2.selectbox("Màu chữ", list(subtitles.COLORS), index=list(subtitles.COLORS).index(settings["color"]),
                             format_func=lambda k: subtitles.COLORS[k][0], key=f"sub_color_{pid}")
        speaker = d3.checkbox("Ghi tên người nói trước câu", settings["speaker"], key=f"sub_speaker_{pid}")
        by_speaker = d4.checkbox("Mỗi nhân vật một màu", settings.get("speaker_colors", False), key=f"sub_colors_{pid}")
        plats = list(subtitles.PLATFORMS)
        platform = st.selectbox("Vùng an toàn theo nền tảng đăng", plats, index=plats.index(settings.get("platform") or "tiktok"),
                                format_func=lambda k: subtitles.PLATFORMS[k]["label"], key=f"sub_platform_{pid}",
                                help="TikTok: chừa ~130 px trên, ~484 px dưới (chú thích + nút), ~140 px phải (cột nút) của khung 1080×1920. "
                                     "Chung: vùng chung của TikTok + Reels + Shorts (chữ cao hơn, ở khoảng giữa khung).")
        karaoke = st.checkbox("Chữ sáng dần theo giọng (kiểu video ngắn)", settings.get("karaoke", False), key=f"sub_karaoke_{pid}",
                              help="Từ chưa nói màu xám, sáng lên khi được nói — thời gian chia theo độ dài chữ (không nghe giọng).")
        auto = st.checkbox("Luôn thêm phụ đề khi xuất bản (cả chế độ tự động)", settings["enabled"], key=f"sub_auto_{pid}")
        new = {"enabled": auto, "lang": lang, "font": font_name or "", "size": size, "pos": pos, "color": color, "speaker": speaker,
               "speaker_colors": by_speaker, "karaoke": karaoke, "platform": platform}
        if new != {k: settings.get(k) for k in new}:
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
            st.markdown(f":orange[Dịch sang ngôn ngữ khác cần Claude ({claude_hint()}).]")
        key = f"sub_cues_{pid}"
        if st.button("📝 Tạo danh sách phụ đề" + (cost.llm_tag(cost.llm_estimate(p.conn, "subtitles", 1)) if lang != "src" else ""), key=f"sub_make_{pid}", type="primary", disabled=lang != "src" and llm is None):
            try:
                cues = delivery.subtitle_cues(p, pid, C.DATA)   # D2: timed on the latest render (its clips, seconds, transition)
                if not cues:
                    st.info("Chưa có dòng thoại nào hoặc chưa có clip ở Bước 4.")
                else:
                    with st.spinner("Đang dịch…" if lang != "src" else "Đang tạo…"):
                        shown = subtitles.localize(llm, cues, lang, C.DATA, pid)   # D8: saved translations / fixes reused
                    st.session_state[key] = [{"Cảnh": c.scene, "Người nói": c.speaker, "Bắt đầu (s)": c.start, "Kết thúc (s)": c.end,
                                              "Nội dung": s.text, "Câu gốc": c.text} for c, s in zip(cues, shown)]
                    st.session_state[f"sub_lang_rows_{pid}"] = lang
            except ERRORS + (subtitles.SubtitleError,) as e:
                st.error(str(e))
        rows = st.session_state.get(key)
        if rows:
            order = ["Cảnh", "Người nói", "Bắt đầu (s)", "Kết thúc (s)", "Nội dung"] + (["Câu gốc"] if lang != "src" else [])
            edited = st.data_editor(rows, hide_index=True, width="stretch", key=f"sub_table_{pid}", disabled=["Cảnh", "Người nói", "Câu gốc"],
                                    num_rows="fixed", column_order=order)
            table = edited.to_dict("records") if hasattr(edited, "to_dict") else edited
            cues = [subtitles.Cue(float(r["Bắt đầu (s)"]), float(r["Kết thúc (s)"]), str(r["Nội dung"]).strip(), str(r["Người nói"] or ""),
                                  r["Cảnh"]) for r in table if str(r["Nội dung"]).strip()]
            made_lang = st.session_state.get(f"sub_lang_rows_{pid}", lang)
            fixes = [(subtitles.Cue(0, 0, str(r.get("Câu gốc") or ""), str(r["Người nói"] or ""), r["Cảnh"]), str(r["Nội dung"]))
                     for r in table if r.get("Câu gốc")]
            if fixes and subtitles.remember_edits(C.DATA, pid, made_lang, fixes):
                st.caption("✔ Đã ghi nhớ câu sửa tay — lần in phụ đề sau (kể cả chạy tự động) dùng câu này, không dịch lại.")
            font, note = subtitles.font_for_text(subtitles.font_by_family(fonts, font_name) if font_name else default, fonts,
                                                 " ".join(c.text for c in cues))
            if note:
                st.markdown(f":orange[{escape(note)}]")
            fast = subtitles.density(cues, delivery.cut_times(p, pid))
            if fast:
                why = lambda d: (f"{d['cps']} ký tự/s" if d["cps"] > subtitles.MAX_CPS else "chồng dòng sau" if d["overlap"]  # noqa: E731
                                 else f"hiện < {subtitles.MIN_CUE_S:g} s" if d["brief"] else "sát dòng sau (< 2 khung)" if d["close"]
                                 else f"vắt qua điểm cắt {d['across_cut']:g} s")
                st.warning(f"{len(fast)} dòng khó đọc (> {subtitles.MAX_CPS:g} ký tự/giây, hiện quá ngắn, sát/chồng dòng sau hoặc vắt "
                           "qua điểm cắt): " + "; ".join(f"cảnh {d['scene']} “{d['text'][:30]}…” {why(d)}" for d in fast[:4]))
            bad = [c for c in cues if c.end <= c.start]
            if bad:
                st.error("Có dòng kết thúc trước khi bắt đầu: sửa lại cột thời gian.")
            b1, b2, b3 = st.columns(3)
            b1.download_button("⬇ File .srt", subtitles.to_srt(cues, speaker).encode("utf-8"), file_name=f"phu_de_{lang}.srt",
                               mime="application/x-subrip", key=f"sub_srt_{pid}")
            b2.download_button("⬇ Bảng duyệt .xlsx", subtitles.to_xlsx(cues), file_name=f"phu_de_{lang}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"sub_xlsx_{pid}")
            if b3.button("🔥 In phụ đề vào video", key=f"sub_burn_{pid}", disabled=not has_final or bool(bad)):
                try:
                    with st.spinner("Đang in phụ đề…"):
                        res = delivery.subtitle_layer(p, pid, C.DATA, final["id"], llm, cues, force=True)
                except ERRORS + (subtitles.SubtitleError,) as e:
                    st.error(str(e))
                else:
                    if res:
                        st.toast(f"Đã in {res['cues']} dòng bằng font {res['font']}")
                        st.rerun()
            if not has_final:
                st.caption("Dựng video cuối trước (5.3), rồi mới in được phụ đề.")


def sfx_assistant(p: Pipeline, pid: int) -> None:
    """One button: AI reads the scenes and the sound library and proposes effects; the person reviews, edits and adds them."""
    n = sound_lib.counts(p.conn)
    if not n:
        return
    key = f"sfxplan_{pid}"
    n_ai = sum(1 for e in audio_lib.load(audio_lib.assets_dir(C.DATA, pid)) if e.get("kind") == "sound_effect" and e.get("use"))
    with ui.fold("🎧 Hiệu ứng âm thanh", f"🎧 {n_ai} hiệu ứng trong bản trộn (gắn theo shot) · mở để AI đề xuất lại / chỉnh",
                 f"sfx_{pid}", default_open=False,
                 sub="AI đọc kịch bản + kho của bạn, đề xuất chỗ cần điểm nhấn / chuyển cảnh") as sfx_open:  # S9 E5.4
        if sfx_open:
            if not n.get("sfx"):
                st.caption("Kho âm thanh chưa có hiệu ứng nào.")
            else:
                wish = st.text_input("Yêu cầu thêm (không bắt buộc)", key=f"sfx_wish_{pid}",
                                     placeholder="vd: ít thôi, chỉ ở chuyển cảnh · thêm tiếng va chạm ở cảnh 3")
                transition = st.session_state.get(f"tr_{pid}", "cut")
                fade = float(st.session_state.get(f"fade_{pid}", 1.0))
                if st.button("🤖 AI tự đề xuất hiệu ứng" + cost.llm_tag(cost.llm_estimate(p.conn, "sfx", 1)), key=f"sfx_ai_go_{pid}", type="primary"):
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
                    if plan.get("unmet"):
                        st.warning("🔊 Âm Đạo diễn yêu cầu mà chưa có hiệu ứng nào đặt vào: " + " · ".join(
                            f"shot {u['idx']}: {', '.join(u['sfx'])}" for u in plan["unmet"])
                            + " — thêm tay ở mục Hiệu ứng, hoặc bổ sung âm đó vào kho âm thanh.")
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
                            st.toast(f"Đã thêm {added} hiệu ứng (chỉnh tiếp ở mục Hiệu ứng & giọng đọc thêm)")
                            st.rerun()
                        if b2.button("Bỏ đề xuất", key=f"sfx_drop_{pid}"):
                            st.session_state.pop(key, None)
                            st.rerun()
            if n.get("music"):
                mode = p.project(pid)["music_mode"] == "library"
                auto = st.checkbox("Nhạc nền: ưu tiên lấy từ kho của tôi thay vì để AI tạo (tiết kiệm credit; AI tạo nhạc vẫn là mặc định)", mode,
                                   key=f"music_mode_{pid}", disabled=music.is_off(p, pid),
                                   help="Đang chọn 'Không dùng nhạc'" if music.is_off(p, pid) else None)
                if auto != mode:
                    p.conn.execute("UPDATE projects SET music_mode=? WHERE id=?", ("library" if auto else None, pid))
                    p.conn.commit()


def step5(p: Pipeline, pid: int):
    """Sound & delivery: clips → sound (music, effects, voices) → render → post (subtitles, end card, formats) → the deliverable."""
    stat = delivery.status(p, pid, C.DATA)
    state = "stale" if stat["final"]["state"] == "fresh" and stat.get("best_stale") else stat["final"]["state"]
    step_header("Bản giao · Âm thanh & xuất bản", "clip → âm thanh → dựng → phụ đề/card/kích thước → một bản giao",
                {"missing": "chưa dựng", "fresh": "bản giao mới nhất", "stale": "bản giao cũ"}[state], 1 if state == "stale" else 0)
    from dashboard import next_step                                     # S9 E0.1: the next thing to do, one line
    ui.html(next_step.band(p, pid, 5, C.DATA))
    chosen, durations = clips_panel(p, pid)
    ui.html(ui.card_title("5.2 · 🔊 Âm thanh", "nhạc nền · hiệu ứng · giọng thoại (làm ở Bước 3)"))
    step5a(p, pid)
    sfx_assistant(p, pid)
    if not C.expert():                     # never silent: two voices at once is said in normal mode too
        overlaps = audio_lib.overlapping_tts(audio_lib.assets_dir(C.DATA, pid))
        if overlaps:
            st.warning(f"⚠ {len(overlaps)} chỗ giọng đọc đè lên nhau — bấm ▶ Dựng video cuối (giọng tự xếp theo clip) hoặc bật ⚙ → "
                       "Chế độ chuyên gia để xếp lại tay.")
    if C.expert():
        with st.expander("🎧 Hiệu ứng & giọng đọc thêm (tùy chọn)"):
            try:
                provider = music.audio_provider()
            except ProviderError as e:                 # U1: say why the audio buttons are missing instead of hiding it
                provider = None
                st.caption(f"⚠ Chưa dùng được dịch vụ âm thanh: {e}")
            extras_section(p, pid, provider)
    timeline_panel(p, pid)
    render_panel(p, pid, chosen, durations)
    ui.html(ui.card_title("5.4 · ✨ Hậu kỳ", "phụ đề · card cuối · kích thước khác"))
    subtitle_panel(p, pid)
    end_card_panel(p, pid)
    exports_panel(p, pid)
    delivery_panel(p, pid, chosen, durations)





def timeline_panel(p: Pipeline, pid: int) -> None:
    """S9.6: the whole film on one timeline before rendering — shots, lines, music on/off, effects, subtitles (tier 2: folded)."""
    from core import timeline_view
    try:
        data = timeline_view.tracks(p, C.DATA, pid)
    except Exception as e:  # noqa: BLE001 - the page goes on; said
        st.caption(f"⚠ Không dựng được timeline tổng: {type(e).__name__}: {e}")
        return
    if not data["shots"]:
        return
    off = sum(b["end"] - b["start"] for b in data.get("music_off") or [])
    summary = (f"{data['total']:.1f} s · {len(data['shots'])} shot · {len(data['voice'])} câu thoại · {len(data['sfx'])} hiệu ứng · "
               f"{len(data['subs'])} dòng phụ đề" + (f" · nhạc tắt {off:.1f} s" if off else ""))
    with ui.fold("🗺 Timeline tổng", summary, f"timeline_{pid}", default_open=False,
                 sub="xem mọi thứ nằm ở đâu trước khi dựng — rê chuột lên khối để xem chữ") as is_open:
        if is_open:
            ui.html(timeline_view.html(data))
            for n in data["notes"]:
                st.caption("⚠ " + n)


def clips_panel(p: Pipeline, pid: int):
    """5.1 The clips in scene order (usable ones ticked), their real lengths; returns (chosen paths, durations)."""
    clips = final_cut.collect_clips(p, C.DATA, pid)
    present = [c for c in clips if c["path"]]
    missing = [c for c in clips if not c["path"]]
    status = lineage.scan(p.conn, pid)
    chosen, durations = [], []
    total_s = sum(_probe(c["path"], os.path.getmtime(c["path"]), c["requested_sec"]) for c in present if c["usable"])
    with ui.fold("5.1 · 🎬 Clip theo thứ tự cảnh", f"🎬 {sum(1 for c in present if c['usable'])}/{len(clips)} clip dùng được · "
                 f"{total_s:.1f} s · mở để bỏ / chỉnh độ dài từng clip", f"clips_{pid}", default_open=bool(missing) or not present,
                 sub=f"{len(present)} có sẵn / {len(clips)} · lấy tự động từ Bước 4") as clips_open:  # S9 E5.1
        if not clips_open:                 # folded: every usable clip at its real length (as the automatic run does)
            for c in present:
                if c["usable"]:
                    chosen.append(c["path"])
                    durations.append(float(_probe(c["path"], os.path.getmtime(c["path"]), c["requested_sec"])))
        if clips_open:
            if not present:
                st.info("Chưa có clip nào. Chạy Bước 4" + (" hoặc nhập clip thủ công bên dưới." if C.expert()
                                                              else " (nhập clip thủ công: bật ⚙ → Chế độ chuyên gia)."))
            names = ", ".join(f"cảnh {c['idx']}" + (f" ({ui.state_label(c['state'], 'video_gen')})" if c["state"] else "") for c in missing if c["idx"])
            if names:
                st.warning(f"Thiếu clip: {names} — bản ghép sẽ bỏ qua các cảnh này.")
            for c in present:
                label = f"{C.unit_label(p, pid, c['idx'])} — {c['title']}" if c["idx"] else c["title"]
                base = os.path.basename(c["path"])
                real = _probe(c["path"], os.path.getmtime(c["path"]), c["requested_sec"])
                srow = status.get(c.get("scene_id")) or {}
                a, b, d = st.columns([3, 1.4, 1], vertical_alignment="center")
                note = "" if c["usable"] else f" · {ui.state_label(c['state'], 'video_gen')}"
                use = a.checkbox(label + note + (" · ⚠ cũ" if srow.get("video_stale") else ""), c["usable"], key=f"use_{pid}_{base}")
                sec = d.number_input("Giây", 0.5, 60.0, float(round(real, 2)), 0.1, key=f"sec_{pid}_{base}", label_visibility="collapsed")
                if b.checkbox("Xem", False, key=f"see_{pid}_{base}"):
                    show_video(c["path"])
                if use:
                    chosen.append(c["path"])
                    durations.append(sec)
                if c.get("scene_id"):
                    scene_expander(p, c["scene_id"], with_motion=True)
            if C.expert():
                with st.expander("Nhập clip thủ công (tên file theo thứ tự, vd 01.mp4)"):
                    up = st.file_uploader("Clip .mp4", type=["mp4"], accept_multiple_files=True, key=f"vid_{pid}")
                    if up and st.button("Lưu clip", key=f"vid_save_{pid}"):
                        for f in up:
                            act(lambda: final_cut.save_manual_clip(C.DATA, pid, f.name, f.getvalue()))
                        st.rerun()
    return chosen, durations


def render_panel(p: Pipeline, pid: int, chosen, durations) -> None:
    """5.3 Render settings (saved in the project: the automatic run uses the same) and the render itself."""
    s = delivery.get_settings(p, pid)
    with st.container(border=True):
        ui.html(ui.card_title("5.3 · 🎞 Dựng video cuối", "thiết lập lưu theo dự án — chế độ tự động dùng chung"))
        opts = ["cut", "crossfade", "dip_to_black"]
        tr_names = {"cut": "Cắt", "crossfade": "Hòa tan", "dip_to_black": "Tối dần"}
        track = delivery.selected_music(C.DATA, pid)
        transition, fade, volume, keep = s["transition"], float(s["fade"]), float(s["music_volume"]), bool(s["keep_audio"])
        with ui.fold("⚙ Thiết lập dựng", f"{tr_names[s['transition']]} · nhạc {float(s['music_volume']):g} · "
                     + ("giữ âm clip" if s["keep_audio"] else "không giữ âm clip") + (f" · {os.path.basename(track)}" if track else " · không nhạc"),
                     f"render_set_{pid}", default_open=False) as set_open:          # S9 E5.6: saved in the project; folded = those
            if set_open:
                transition = st.radio("Chuyển cảnh", opts, index=opts.index(s["transition"]), horizontal=True, key=f"tr_{pid}",
                                      format_func=lambda t: tr_names[t])
                fade = st.slider("Thời gian chuyển cảnh (giây)", 0.3, 2.0, float(s["fade"]), 0.1, key=f"fade_{pid}", disabled=transition == "cut")
                volume = st.slider("Âm lượng nhạc nền", 0.0, 1.0, float(s["music_volume"]), 0.05, key=f"vol_{pid}", disabled=not track)
                st.caption(f"Nhạc nền: {os.path.basename(track)}" if track else "Không có nhạc nền (chọn ở 5.2).")
                keep = st.checkbox("🔊 Giữ âm thanh gốc của clip (tiếng động do model tạo)", bool(s["keep_audio"]), key=f"keepaud_{pid}",
                                   help="Nhạc và giọng thoại được trộn lên trên. Cần MỌI clip đã chọn có âm thanh.")
        new = dict(s, transition=transition, fade=fade, music_volume=volume, keep_audio=keep)
        if (transition, fade, volume, keep) != (s["transition"], s["fade"], s["music_volume"], s["keep_audio"]):
            delivery.save_settings(p, pid, new)
        if keep and chosen:
            silent_clips = [os.path.basename(c) for c in chosen if not _has_audio(c, os.path.getmtime(c))]
            if silent_clips:
                st.warning("Clip không có âm thanh: " + ", ".join(silent_clips) + " → âm thanh gốc sẽ bị bỏ cho cả bản ghép.")
        voiced = voice.status(p.conn, pid, C.DATA)
        extras = audio_lib.mix_list(audio_lib.assets_dir(C.DATA, pid))
        st.caption(f"Giọng thoại đã tạo: {voiced.get('succeeded', 0)}/{voiced['total']} câu (tự xếp theo clip khi dựng) · hiệu ứng/giọng khác trong bản trộn: {len(extras)}")
        problems = final_cut.render_problems(durations, transition, fade)
        for msg in problems:
            st.warning(msg)
        if durations and not problems:
            st.info(f"Tổng thời lượng dự kiến: {final_cut.total_seconds(durations, transition, fade):.1f} giây · {len(chosen)} clip")
        if st.button("▶ Dựng video cuối", disabled=bool(problems), type="primary", key=f"render_{pid}", width="stretch"):
            with st.spinner("Đang dựng…"):
                ok = act(lambda: delivery.render(p, pid, C.DATA, "auto", chosen, durations), "Dựng xong")
            if ok:
                st.rerun()
        loudness_line(p, pid)
        viewer_check_panel(p, pid)
        cover_panel(p, pid)


def viewer_check_panel(p: Pipeline, pid: int) -> None:
    """GĐ4 (editing.md E9, D13): the newest delivery (with subtitles / card when made) as a sheet of frames with the app's interface
    bands painted over and a phone-size copy — free, a few seconds of ffmpeg."""
    row = p.conn.execute("SELECT path, kind FROM outputs WHERE project_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    if not row or not os.path.exists(row["path"] or ""):
        return
    final = p.conn.execute("SELECT path FROM outputs WHERE project_id=? AND kind='final' ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    plain = final["path"] if final and row["kind"] != "final" and os.path.exists(final["path"] or "") else None
    key = f"viewer_{pid}"
    if st.button("🧐 Tự rà như người xem (chồng vùng giao diện app + bản cỡ điện thoại)", key=f"{key}_go",
                 help="Miễn phí. Vùng đỏ = nút/chữ của app (trên 15 %, dưới 35 %, phải 18 %); báo mặt nằm dưới vùng đó."):
        from core import viewer_check
        out = os.path.join(os.path.dirname(row["path"]), "viewer_check.png")
        with st.spinner("Đang lấy khung…"):
            ok = act(lambda: st.session_state.__setitem__(key, viewer_check.sheet(row["path"], out, plain=plain)))
        if not ok:
            return
    res = st.session_state.get(key)
    if res and os.path.exists(res["path"]):
        if res["hidden"]:
            st.warning("⚠ Mặt nằm dưới giao diện app ở: " + ", ".join(f"{f['t']:g}s ({'/'.join(f['faces_hidden'])})"
                                                                    for f in res["frames"] if f["faces_hidden"]))
        if res.get("text_hidden"):
            st.warning("⚠ Chữ nằm dưới giao diện app ở: " + ", ".join(f"{f['t']:g}s ({'/'.join(f['text_hidden'])})"
                                                                    for f in res["frames"] if f.get("text_hidden")))
        elif not res.get("text_checked"):
            st.caption("Chữ: bản mới nhất là bản dựng gốc (chưa in chữ) — kiểm chữ sau khi in phụ đề / card.")
        if not res["hidden"] and res["frames"] and not res["frames"][0].get("faces_seen"):
            st.caption("Không có model dò mặt (data/models/face_detection_yunet_2023mar.onnx) — chỉ xem bằng mắt.")
        st.image(res["path"], caption=f"{os.path.basename(row['path'])} — {len(res['frames'])} khung")


def loudness_line(p: Pipeline, pid: int) -> None:
    """GĐ4 (editing.md E8): the loudness of the newest render, measured when it was made (target −14 LUFS, true peak ≤ −1,5 dBTP)."""
    row = p.conn.execute("SELECT manifest FROM outputs WHERE project_id=? AND kind='final' ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    try:
        man = json.loads(row["manifest"] or "{}") if row else {}
    except (ValueError, TypeError):
        man = {}
    off = [c for c in man.get("color_match") or [] if c.get("off")]
    if off:                                   # GĐ4 D7: shots of one place that drift from their anchor
        st.caption("🎨 Màu: " + ", ".join(f"shot {c['idx']} lệch shot {c['anchor_idx']} (điểm đen/trắng {c['levels']:g}, ám màu {c['cast']:g})"
                                          + (" — đã khớp" if c.get("fixed") else "") for c in off)
                   + ("" if any(c.get("fixed") for c in off) else " · bật cờ khớp màu (FEATURE_SHOT_COLOR_MATCH=1) để tự sửa bản sao"))
    amb = man.get("ambience")
    if amb:                                   # GĐ4 D4/D5: which bed each scene got, and the scenes the library had nothing for
        st.caption("🌧 Âm nền: " + (", ".join(f"cảnh {b['scene']}: {b['sound']}" for b in amb.get("beds") or []) or "không cảnh nào")
                   + (f" · chưa có âm hợp trong thư viện cho cảnh {', '.join(map(str, amb['missing']))}" if amb.get("missing") else ""))
    m = man.get("loudness")
    if not m or m.get("lufs") is None:
        return
    text = (f"🔊 Độ to bản dựng mới nhất: {m['lufs']:g} LUFS · đỉnh thật {m.get('true_peak_dbfs')} dBTP · LRA {m.get('lra')} LU"
            + (f" (đã chuẩn hóa từ {m['before']['lufs']:g} LUFS)" if m.get("normalized") else "") + " — mục tiêu −14 LUFS, đỉnh ≤ −1,5")
    (st.warning if m.get("problems") else st.caption)(text + ("".join(f" · ⚠ {x}" for x in m.get("problems") or [])))


def cover_panel(p: Pipeline, pid: int) -> None:
    """editing.md E11: the cover picture of the latest render (the ⭐ shot, else the strongest acting) — free, one ffmpeg frame."""
    if st.button("🖼 Lấy ảnh bìa từ bản dựng mới nhất (miễn phí)", key=f"cover_go_{pid}",
                 help="Khung giữa shot ⭐ (hoặc shot diễn mạnh nhất). Ảnh bìa là khung người lướt thấy trước khi video chạy."):
        act(lambda: st.session_state.__setitem__(f"cover_{pid}", delivery.cover_image(p, pid, C.DATA)))
    res = st.session_state.get(f"cover_{pid}")
    if res and os.path.exists(res["path"]):
        st.image(res["path"], width=220, caption=f"{res['t']:g}s — {res['why']}")


def end_card_panel(p: Pipeline, pid: int) -> None:
    s = delivery.get_settings(p, pid)
    card = dict(s["end_card"])
    with st.expander("🪧 Card chữ cuối video" + (" ✓" if card.get("enabled") else ""), expanded=False):
        st.caption("Khung chữ tĩnh ghép vào cuối video (kêu gọi, thông điệp, ngày ra mắt…). Font tự chọn loại có đủ dấu tiếng Việt.")
        enabled = st.checkbox("Thêm card cuối khi xuất bản", card.get("enabled", False), key=f"card_on_{pid}")
        title = st.text_input("Dòng chính", card.get("title", ""), key=f"card_title_{pid}")
        subtitle = st.text_input("Dòng phụ (tùy chọn)", card.get("subtitle", ""), key=f"card_sub_{pid}")
        c1, c2, c3 = st.columns(3)
        seconds = c1.number_input("Thời lượng (giây)", 1.0, 10.0, float(card.get("seconds") or 3.0), 0.5, key=f"card_sec_{pid}")
        bg = c2.color_picker("Màu nền", card.get("bg") or "#000000", key=f"card_bg_{pid}")
        fg = c3.color_picker("Màu chữ", card.get("color") or "#FFFFFF", key=f"card_fg_{pid}")
        new = dict(card, enabled=enabled, title=title, subtitle=subtitle, seconds=seconds, bg=bg, color=fg)
        if new != card:
            delivery.save_settings(p, pid, dict(s, end_card=new))
        if st.button("🪧 Thêm card vào bản mới nhất", key=f"card_go_{pid}", disabled=not (title or subtitle)):
            with st.spinner("Đang ghép card…"):
                act(lambda: delivery.end_card_layer(p, pid, C.DATA, card=dict(new, enabled=True)), "Đã thêm card cuối")
            st.rerun()


EXPORT_PRESETS = {"Dọc 1080×1920 (TikTok/Reels/Shorts)": (1080, 1920), "Ngang 1920×1080 (YouTube)": (1920, 1080),
                  "Vuông 1080×1080": (1080, 1080), "Dọc 4:5 1080×1350 (bài đăng)": (1080, 1350)}


def exports_panel(p: Pipeline, pid: int) -> None:
    s = delivery.get_settings(p, pid)
    exports = list(s["exports"])
    with st.expander(f"📐 Xuất thêm kích thước / dung lượng ({len(exports)})", expanded=False):
        st.caption("Tạo bản ở kích thước khác từ bản hoàn chỉnh mới nhất (có phụ đề, card nếu có). “Cắt khung” lấp đầy khung (không viền đen), "
                   "“Giữ nguyên hình” thêm viền. Giới hạn MB: mã hóa 2 lượt, tự nén lại nếu vượt.")
        for n, e in enumerate(exports):
            a, b = st.columns([4, 1])
            a.markdown(f"- {e['w']}×{e['h']} · {'cắt khung' if e.get('fit') == 'crop' else 'giữ nguyên hình'}"
                       + (f" · ≤ {e['max_mb']:g} MB" if e.get("max_mb") else ""))
            if b.button("Bỏ", key=f"exp_rm_{pid}_{n}"):
                delivery.save_settings(p, pid, dict(s, exports=[x for i, x in enumerate(exports) if i != n]))
                st.rerun()
        c1, c2, c3 = st.columns([2.2, 1.4, 1.2])
        preset = c1.selectbox("Kích thước", list(EXPORT_PRESETS), key=f"exp_preset_{pid}")
        fit = c2.selectbox("Cách vừa khung", ["crop", "pad"], format_func=lambda f: {"crop": "Cắt khung", "pad": "Giữ nguyên hình"}[f],
                           key=f"exp_fit_{pid}")
        mb = c3.number_input("Tối đa MB (0 = không)", 0.0, 2000.0, 0.0, 1.0, key=f"exp_mb_{pid}")
        w, h = EXPORT_PRESETS[preset]
        d1, d2 = st.columns(2)
        if d1.button("➕ Thêm vào danh sách xuất bản", key=f"exp_add_{pid}"):
            delivery.save_settings(p, pid, dict(s, exports=exports + [{"w": w, "h": h, "max_mb": mb or None, "fit": fit}]))
            st.rerun()
        if d2.button("Xuất ngay bản này", key=f"exp_now_{pid}"):
            with st.spinner("Đang mã hóa…"):
                act(lambda: st.session_state.__setitem__(f"exp_res_{pid}", delivery.export_layer(p, pid, C.DATA,
                                                                                                  {"w": w, "h": h, "max_mb": mb or None, "fit": fit})))
            res = st.session_state.pop(f"exp_res_{pid}", None)
            if res:
                (st.success if res["fits"] else st.warning)(f"Xong: {res['size_mb']:.1f} MB" + ("" if res["fits"] else " — vẫn vượt giới hạn"))


def delivery_panel(p: Pipeline, pid: int, chosen, durations) -> None:
    """5.5 The deliverable: the most finished up-to-date version, its layers, and one button for the whole chain."""
    stat = delivery.status(p, pid, C.DATA)
    fin = stat["final"]
    with st.container(border=True):
        state = {"missing": ("chưa có", ""), "fresh": ("mới nhất", "b-ok"), "stale": ("⚠ cũ", "b-warn")}[fin["state"]]
        if fin["state"] == "fresh" and stat.get("best_stale"):
            state = ("⚠ cũ", "b-warn")            # D7: the render is current but its subtitles / card / format are not
        ui.html(ui.card_title("5.5 · 📦 Bản giao", "bản hoàn chỉnh nhất của lần dựng mới nhất") + ui.badge(*state))
        for r in fin["reasons"] + ([stat["best_stale"]] if stat.get("best_stale") else []):
            st.caption(f"⚠ {r}")
        if st.button("📦 Xuất bản đầy đủ (dựng → phụ đề → card → các kích thước)", type="primary", key=f"deliver_{pid}",
                     disabled=not chosen, width="stretch"):
            with st.spinner("Đang xuất bản…"):
                ok = act(lambda: st.session_state.__setitem__(f"deliver_res_{pid}", delivery.deliver(p, pid, C.DATA, llm_client(),
                                                                                                    clips=chosen, durations=durations)))
            if ok:
                res = st.session_state.pop(f"deliver_res_{pid}")
                for w in res["warnings"]:
                    st.warning(w)
                if res.get("qc") is not None:
                    st.session_state[f"final_qc_{pid}"] = res["qc"]
                st.toast(f"Đã xuất bản: {len(res['layers']) + 1} file")
                st.rerun()
        best = stat["best"]
        if best and os.path.exists(best):
            show_video(best)
            with open(best, "rb") as f:
                st.download_button(f"⬇ Tải {os.path.basename(best)}", f, file_name=os.path.basename(best), mime="video/mp4", key=f"best_dl_{pid}")
        files = ([("Video cuối", fin["path"], None)] if fin.get("path") and os.path.exists(fin["path"]) else []) + \
            [({"subtitle": "Phụ đề", "endcard": "Card cuối", "ailabel": "Nhãn AI", "export": "Bản xuất"}.get(x["kind"], x["kind"]), x["path"], x["stale"]) for x in stat["layers"]]
        for n, (label, path, stale) in enumerate(files):
            a, b = st.columns([4, 1.3], vertical_alignment="center")
            a.markdown(f"{label}: `{os.path.basename(path)}` · {os.path.getsize(path) / 1e6:.1f} MB" + (f" · :orange[⚠ {stale}]" if stale else ""))
            with open(path, "rb") as f:
                b.download_button("⬇ Tải", f, file_name=os.path.basename(path), mime="video/mp4", key=f"layer_dl_{pid}_{n}")
        _final_qc(p, pid, bool(fin.get("path")))


def _final_qc(p, pid, has_render: bool):
    """S1.9 (after trial #8): the finished cut measured by code — length, music holes, effects off their shot, peaks, subtitle lines
    that are not dialogue, subtitles on faces, very short shots. Runs after every delivery; the button measures again (free)."""
    from core import features, final_qc
    trying = features.on_unverified()
    if trying:                                       # S6.3: which parts of this cut are still being tried out
        with st.expander(f"🧪 Bản dựng đang dùng {len(trying)} tính năng chưa kiểm thật"):
            st.markdown("\n".join(f"- `{k}` — {escape(v['label'])}" for k, v in sorted(trying.items())))
            st.caption("Bật bằng FEATURE_<TÊN>=1 trong dashboard.env. Sau khi một lần chạy thật chứng minh tính năng đúng, ghi `verified` "
                       "trong core/features.py (kèm ngày, dự án, số đo) — bản giao chính nên chỉ dùng tính năng đã kiểm.")
    key = f"final_qc_{pid}"
    if has_render and st.button("🔎 Kiểm bản dựng (miễn phí, ~30 s)", key=f"final_qc_btn_{pid}"):
        with st.spinner("Đang đo bản dựng…"):
            act(lambda: st.session_state.__setitem__(key, final_qc.run(p, pid, C.DATA)))
    res = st.session_state.get(key)
    if not res:
        return
    text = final_qc.summary(res)
    (st.success if res["ok"] and not res["warns"] else st.error if res["blocks"] else st.warning)(text.splitlines()[0])
    for i in res["issues"]:
        st.caption(f"{final_qc._MARK.get(i['level'], '⚠')} {i['msg']}")


def _timed_brief(p, pid):
    """The score brief timed on the real cut (core/music_timing.py) for shot projects; None otherwise."""
    from core import music_timing, shots
    try:
        return music_timing.timed_brief(p, pid) if shots.active(p, pid) else None
    except Exception:  # noqa: BLE001 - the plain brief still works
        return None
