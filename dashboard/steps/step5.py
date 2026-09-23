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
    """Background music: brief written by Claude from the scenes (or the template), drafts, choice; own file or none."""
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
        a.markdown(ui.card_title("🎵 Nhạc nền đang chọn") + (ui.badge(files[0], "b-ok") if files else ui.badge("chưa chọn / không dùng")),
                   unsafe_allow_html=True)
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
                st.rerun()
            if st.button("Không dùng nhạc", key=f"music_none_{pid}"):
                music.clear_selected(selected_dir)
                st.rerun()
    shown = st.session_state.get(f"prev5a_{pid}")
    if shown and os.path.exists(shown[0]):
        with st.container(border=True):
            ui.html(ui.card_title("Xem thử: clip + nhạc", shown[1]))
            show_video(shown[0])
    with st.container(border=True):
        if provider is None:
            st.info("Chưa cấu hình tạo nhạc (AUDIO_PROVIDER=clipai hoặc VIDEO_PROVIDER=clipai + CLIPAI_TOKEN); vẫn tải được nhạc có sẵn ở trên.")
        else:
            ui.html(ui.card_title("Brief nhạc", "Claude viết theo thể loại, ý đồ và nhịp từng cảnh — bạn sửa được") + ui.badge(
                provider.name + (" · giả lập" if provider.name == "mock-audio" else " · music_v2 · tốn credit"), "b-info"))
            key = f"mbrief_{pid}"
            client = llm_client()
            if st.button("🤖 Claude viết brief nhạc", key=f"mbrief_ai_{pid}", disabled=client is None, help=None if client else claude_hint()):
                with st.spinner("Claude đang viết brief…"):
                    brief = claude_tasks.music_brief(p, pid, client)
                st.session_state[key] = brief
                st.session_state[f"mprompt_{pid}"] = brief["prompt"]
                st.session_state[f"mlen_{pid}"] = max(3, brief["length_ms"] // 1000)
            brief = st.session_state.get(key) or music.default_brief(p, pid)
            if brief.get("brief"):
                st.caption(f"{brief['brief'].get('genre', '')} · {brief['brief'].get('tempo_bpm', '')} BPM · {brief['brief'].get('structure', '')}")
            prompt = st.text_area("Prompt nhạc (≤ 2000 ký tự)", brief["prompt"], key=f"mprompt_{pid}", height=90)
            c1, c2, c3 = st.columns(3)
            seconds = c1.number_input("Độ dài (giây)", 3, 600, max(3, brief["length_ms"] // 1000), key=f"mlen_{pid}")
            instrumental = c2.checkbox("Không lời (instrumental)", brief["instrumental"], key=f"minst_{pid}")
            count = c3.number_input("Số bản nháp", 1, 5, 3, key=f"mcount_{pid}")
            b1, b2 = st.columns(2)
            if b1.button(f"✨ Tạo {int(count)} bản nháp", type="primary", disabled=not prompt.strip(), key=f"mdraft_{pid}"):
                n = music.submit_drafts(provider, drafts_dir, prompt, int(seconds) * 1000, instrumental, int(count), ledger=(p.conn, pid))
                st.toast(f"Đã gửi {n} bản")
                st.rerun()
            if b2.button("⟳ Kiểm tra + tải nhạc về", key=f"mrefresh_{pid}"):
                counts = music.refresh_drafts(provider, drafts_dir)
                st.toast(f"Đang chạy {counts['running']} · xong {counts['succeeded']} · lỗi {counts['failed']}")
                st.rerun()
    drafts = music.load_drafts(drafts_dir)
    for start in range(0, len(drafts), 3):
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
                            st.rerun()
                else:
                    ui.html('<div class="wave"></div><span class="muted">đang tạo… bấm “Kiểm tra + tải nhạc về”</span>')
    if drafts and st.button("Xóa danh sách bản nháp", key=f"mclear_{pid}"):
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
                sig = f"{i}_{int(bool(e['use']))}_{e['start']}_{e['volume']}"   # file changed elsewhere (voice placement) -> fresh widgets
                use = a.checkbox("Đưa vào bản ghép", e["use"], key=f"ax_use_{pid}_{sig}", disabled=e["state"] != "succeeded")
                start = b.number_input("Bắt đầu (giây)", 0.0, 600.0, float(e["start"]), 0.5, key=f"ax_st_{pid}_{sig}")
                vol = c.slider("Âm lượng", 0.0, 2.0, float(e["volume"]), 0.05, key=f"ax_vol_{pid}_{sig}")
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
        auto = st.checkbox("Luôn thêm phụ đề khi xuất bản (cả chế độ tự động)", settings["enabled"], key=f"sub_auto_{pid}")
        new = {"enabled": auto, "lang": lang, "font": font_name or "", "size": size, "pos": pos, "color": color, "speaker": speaker,
               "speaker_colors": by_speaker}
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
        rs = delivery.get_settings(p, pid)
        if st.button("📝 Tạo danh sách phụ đề", key=f"sub_make_{pid}", type="primary", disabled=lang != "src" and llm is None):
            try:
                cues = subtitles.build_cues(p, C.DATA, pid, rs["transition"], rs["fade"])
                if not cues:
                    st.info("Chưa có dòng thoại nào hoặc chưa có clip ở Bước 4.")
                else:
                    with st.spinner("Đang dịch…" if lang != "src" else "Đang tạo…"):
                        cues = subtitles.translate(llm, cues, lang)
                    st.session_state[key] = [{"Cảnh": c.scene, "Người nói": c.speaker, "Bắt đầu (s)": c.start, "Kết thúc (s)": c.end,
                                              "Nội dung": c.text} for c in cues]
            except ERRORS + (subtitles.SubtitleError,) as e:
                st.error(str(e))
        rows = st.session_state.get(key)
        if rows:
            edited = st.data_editor(rows, hide_index=True, width="stretch", key=f"sub_table_{pid}", disabled=["Cảnh", "Người nói"], num_rows="fixed")
            table = edited.to_dict("records") if hasattr(edited, "to_dict") else edited
            cues = [subtitles.Cue(float(r["Bắt đầu (s)"]), float(r["Kết thúc (s)"]), str(r["Nội dung"]).strip(), str(r["Người nói"] or ""),
                                  r["Cảnh"]) for r in table if str(r["Nội dung"]).strip()]
            font, note = subtitles.font_for_text(subtitles.font_by_family(fonts, font_name) if font_name else default, fonts,
                                                 " ".join(c.text for c in cues))
            if note:
                st.markdown(f":orange[{escape(note)}]")
            fast = subtitles.density(cues)
            if fast:
                st.warning(f"{len(fast)} dòng đọc không kịp (> {subtitles.MAX_CPS:g} ký tự/giây) hoặc chồng dòng sau: "
                           + "; ".join(f"cảnh {d['scene']} “{d['text'][:30]}…” {d['cps']} ký tự/s" for d in fast[:4]))
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
                        st.toast(f"Đã thêm {added} hiệu ứng (chỉnh tiếp ở mục Hiệu ứng & giọng đọc thêm)")
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
    """Sound & delivery: clips → sound (music, effects, voices) → render → post (subtitles, end card, formats) → the deliverable."""
    fin = delivery.status(p, pid, C.DATA)["final"]
    step_header("Bước 5 · Âm thanh & xuất bản", "clip → âm thanh → dựng → phụ đề/card/kích thước → một bản giao",
                {"missing": "chưa dựng", "fresh": "bản giao mới nhất", "stale": "bản giao cũ"}[fin["state"]], 1 if fin["state"] == "stale" else 0)
    chosen, durations = clips_panel(p, pid)
    ui.html(ui.card_title("5.2 · 🔊 Âm thanh", "nhạc nền · hiệu ứng · giọng thoại (làm ở Bước 3)"))
    step5a(p, pid)
    sfx_assistant(p, pid)
    with st.expander("🎧 Hiệu ứng & giọng đọc thêm (tùy chọn)"):
        try:
            provider = music.audio_provider()
        except ProviderError:
            provider = None
        extras_section(p, pid, provider)
    render_panel(p, pid, chosen, durations)
    ui.html(ui.card_title("5.4 · ✨ Hậu kỳ", "phụ đề · card cuối · kích thước khác"))
    subtitle_panel(p, pid)
    end_card_panel(p, pid)
    exports_panel(p, pid)
    delivery_panel(p, pid, chosen, durations)





def clips_panel(p: Pipeline, pid: int):
    """5.1 The clips in scene order (usable ones ticked), their real lengths; returns (chosen paths, durations)."""
    vdir = project_dir(pid, "videos")
    clips = final_cut.collect_clips(p, C.DATA, pid)
    present = [c for c in clips if c["path"]]
    missing = [c for c in clips if not c["path"]]
    status = lineage.scan(p.conn, pid)
    chosen, durations = [], []
    with st.container(border=True):
        ui.html(ui.card_title("5.1 · 🎬 Clip theo thứ tự cảnh", f"{len(present)} có sẵn / {len(clips)} · lấy tự động từ Bước 4"))
        if not present:
            st.info("Chưa có clip nào. Chạy Bước 4 hoặc nhập clip thủ công bên dưới.")
        names = ", ".join(f"cảnh {c['idx']}" + (f" ({ui.state_label(c['state'], 'video_gen')})" if c["state"] else "") for c in missing if c["idx"])
        if names:
            st.warning(f"Thiếu clip: {names} — bản ghép sẽ bỏ qua các cảnh này.")
        for c in present:
            label = f"Cảnh {c['idx']} — {c['title']}" if c["idx"] else c["title"]
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
        with st.expander("Nhập clip thủ công (tên file theo thứ tự, vd 01.mp4)"):
            up = st.file_uploader("Clip .mp4", type=["mp4"], accept_multiple_files=True, key=f"vid_{pid}")
            if up and st.button("Lưu clip", key=f"vid_save_{pid}"):
                for f in up:
                    with open(os.path.join(vdir, f.name), "wb") as fh:
                        fh.write(f.getvalue())
                st.rerun()
    return chosen, durations


def render_panel(p: Pipeline, pid: int, chosen, durations) -> None:
    """5.3 Render settings (saved in the project: the automatic run uses the same) and the render itself."""
    s = delivery.get_settings(p, pid)
    with st.container(border=True):
        ui.html(ui.card_title("5.3 · 🎞 Dựng video cuối", "thiết lập lưu theo dự án — chế độ tự động dùng chung"))
        opts = ["cut", "crossfade", "dip_to_black"]
        transition = st.radio("Chuyển cảnh", opts, index=opts.index(s["transition"]), horizontal=True, key=f"tr_{pid}",
                              format_func=lambda t: {"cut": "Cắt", "crossfade": "Hòa tan", "dip_to_black": "Tối dần"}[t])
        fade = st.slider("Thời gian chuyển cảnh (giây)", 0.3, 2.0, float(s["fade"]), 0.1, key=f"fade_{pid}", disabled=transition == "cut")
        track = delivery.selected_music(C.DATA, pid)
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
        ui.html(ui.card_title("5.5 · 📦 Bản giao", "bản hoàn chỉnh nhất của lần dựng mới nhất") + ui.badge(*state))
        for r in fin["reasons"]:
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
                st.toast(f"Đã xuất bản: {len(res['layers']) + 1} file")
                st.rerun()
        best = stat["best"]
        if best and os.path.exists(best):
            show_video(best)
            with open(best, "rb") as f:
                st.download_button(f"⬇ Tải {os.path.basename(best)}", f, file_name=os.path.basename(best), mime="video/mp4", key=f"best_dl_{pid}")
        files = ([("Video cuối", fin["path"], None)] if fin.get("path") and os.path.exists(fin["path"]) else []) + \
            [({"subtitle": "Phụ đề", "endcard": "Card cuối", "export": "Bản xuất"}[x["kind"]], x["path"], x["stale"]) for x in stat["layers"]]
        for n, (label, path, stale) in enumerate(files):
            a, b = st.columns([4, 1.3], vertical_alignment="center")
            a.markdown(f"{label}: `{os.path.basename(path)}` · {os.path.getsize(path) / 1e6:.1f} MB" + (f" · :orange[⚠ {stale}]" if stale else ""))
            with open(path, "rb") as f:
                b.download_button("⬇ Tải", f, file_name=os.path.basename(path), mime="video/mp4", key=f"layer_dl_{pid}_{n}")
