"""Step 3: video motion prompts."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import dialogue_panel
from contextlib import nullcontext
from core import motion_prompt_lint


def _card(key: str):
    from dashboard.design import components
    return components.card(key)


def _info(key: str, anchor=None, help_text="Bấm để xem chi tiết"):
    """Chú thích (UI v2): chi tiết ưu tiên thấp nằm trong popover mở ngay khi bấm vào `anchor`, bên ngoài chỉ có tóm tắt."""
    from dashboard.design import components
    return components.info(key, anchor=anchor, help_text=help_text)


def step3(p: Pipeline, pid: int):
    summ = lineage.summary(p.conn, pid)
    status = lineage.scan(p.conn, pid)
    approved_imgs = [r for r in status.values() if r["image_job_id"]]
    v2 = ui.v2_on()
    rows = p.conn.execute("SELECT s.id sid, s.idx, s.data, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
                          " WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    if v2:
        from dashboard.design.screens import storyboard_cards as SB
        SB.motion_hero(p, pid, summ, rows)
    else:
        step_header("Storyboard · Motion & giọng thoại", "viết cách chuyển động cho từng cảnh, làm giọng — trước khi tốn credit video",
                    f"{summ['motion'][0]}/{summ['total']} prompt đã duyệt", summ["motion"][1])
    from dashboard import next_step                                     # S9 E0.1
    if not v2:                                                            # v2: the shell header already shows the next step
        ui.html(next_step.band(p, pid, 3, C.DATA))
    stale_idx = sorted(r["idx"] for r in status.values() if r["motion_stale"] and r["image_job_id"])
    missing = [r for r in approved_imgs if r["motion_state"] is None]
    client = llm_client()
    with (_card("sb-mot-tools") if v2 else st.container(border=True)):
        c1, c2, c3 = st.columns([2.6, 2, 2], vertical_alignment="center")
        todo = len(missing) + len(stale_idx)
        # 08/10: Seedance reference shots get their prompt from the Director's fields by code (as in the automatic run) — Claude only
        # for the frame-start shots
        from core import seedance_refs
        refs = {sid for sid in status if seedance_refs.uses_refs(p.conn, sid)}
        by_code_n = sum(1 for sid, r in status.items() if sid in refs and r["image_job_id"]
                        and (r["motion_state"] is None or r["motion_stale"]))
        claude_missing = [sid for sid, r in status.items() if sid not in refs and r["image_job_id"] and r["motion_state"] is None]
        claude_stale = [r["idx"] for sid, r in status.items() if sid not in refs and r["image_job_id"] and r["motion_stale"]]
        calls = (1 if claude_missing else 0) + (1 if claude_stale else 0)  # one Claude call per batch (all missing / all outdated)
        calls += 1 if by_code_n else 0                                     # + at most one call translating Vietnamese fields (overestimate)
        mot_usd = cost.llm_estimate(p.conn, "motion", calls, images=min(len(claude_missing) + len(claude_stale), 12))
        code_note = f" · {by_code_n} viết bằng code" if by_code_n else ""
        if c1.button(f"🤖 Viết motion prompt ({len(missing)} chưa có · {len(stale_idx)} đã cũ{code_note}){cost.llm_tag(mot_usd, calls)}",
                     type="primary", key=f"llm_mot_{pid}", disabled=(client is None and not by_code_n) or not todo,
                     help=None if client else claude_hint()):
            def go():
                code = seedance_refs.write_by_code(p, pid, client)
                if code["warn"]:
                    st.warning(code["warn"])
                again = lineage.scan(p.conn, pid)                           # what is left for Claude after the code step
                left_stale = sorted(r["idx"] for r in again.values() if r["motion_stale"] and r["image_job_id"])
                left_missing = any(r["image_job_id"] and r["motion_state"] is None for r in again.values())
                r1 = llm_runner.run_motion(p, pid, client, C.DATA) if left_missing and client else {"scenes": 0}
                r2 = llm_runner.run_motion(p, pid, client, C.DATA, only_idx=left_stale) if left_stale and client else {"scenes": 0}
                st.toast(f"Đã viết {code['by_code'] + r1['scenes'] + r2['scenes']} motion prompt"
                         + (f" ({code['by_code']} bằng code, không gọi Claude)" if code["by_code"] else ""))
            with st.spinner("Claude đang viết motion prompt…"):
                if act(go):
                    st.rerun()
        waiting = [r["sid"] for r in rows if r["state"] != "approved"]
        if confirm_all("btn_ok_all", waiting, f"✔ Duyệt tất cả ({len(waiting)} prompt)", f"Duyệt tất cả {len(waiting)} motion prompt đang chờ?", c2):
            for sid in waiting:
                llm_io.approve_motion_prompt(p, sid)
            st.rerun()
        if c3.button(f"🔍 Rà motion prompt ({len(rows)}){cost.llm_tag(cost.llm_estimate(p.conn, 'motion', 1 if rows else 0), 1 if rows else 0)}",
                     key=f"lint_{pid}", disabled=client is None or not rows,
                     help="Checklist Seedance Final QC + 4 kiểm tra mơ hồ (tỉ lệ, vị trí, đường máy, thời điểm) cho cảnh phức tạp"):
            with st.spinner("Claude đang rà từng prompt…"):
                act(lambda: claude_tasks.lint_motion(p, pid, client))
            st.rerun()
        if client is None:
            if v2:
                SB.note("Chưa có Claude — các nút bên trên tạm khóa", claude_hint(), "sb-mot-noclaude", kind="warn")
            else:
                st.caption(claude_hint())
        if C.expert():
            with st.expander("✍ Nâng cao: prompt gửi Claude (copy) & dán kết quả"):
                st.code(llm_runner.plain(prompts.build_motion_bundle(p, pid)), language="markdown")
                raw = st.text_area("Dán JSON motion prompts từ Claude", key=f"motion_{pid}", height=140)
                if st.button("▶ Lưu motion prompts", disabled=not raw.strip(), key=f"mot_paste_{pid}"):
                    if act(lambda: llm_io.store_motion_prompts(p, pid, raw), "Đã lưu"):
                        st.rerun()
    voice_panel(p, pid)
    motion_ok = sum(1 for r in rows if r["state"] == "approved") if rows and "state" in rows[0].keys() else 0
    with ui.fold("Motion prompt từng cảnh", f"🎬 {motion_ok}/{len(rows)} cảnh đã duyệt motion · mở để xem / sửa", f"motion_{pid}",
                 default_open=not rows or motion_ok < len(rows), sub=f"{len(rows)} cảnh") as motion_open:  # S9 E3.1
        if motion_open:
            if not rows:
                st.caption("Chưa có motion prompt: duyệt ảnh ở màn Storyboard rồi bấm “🤖 Viết motion prompt”.")
            voices = SB.scene_voice_map(p, pid) if v2 else {}
            for r in rows:
                data = json.loads(r["data"] or "{}")
                srow = status.get(r["sid"]) or {}
                img_id = srow.get("image_job_id")
                choice = model_router.scene_choice(p.conn, r["sid"])
                scene_box = _card(f"sb-mot-{r['sid']}") if v2 else nullcontext()
                scene_box.__enter__()
                flags = json.loads(r["check_flags"] or "[]") if r["check_flags"] else []
                end_warn = motion_prompt_lint.end_frame_problem(data, r["motion_prompt"])   # KLD-13: chỉ cảnh báo, 0 USD
                if end_warn:
                    flags = list(flags) + [end_warn]
                lint = json.loads(r["lint"] or "{}") if r["lint"] else {}
                if v2:                                         # P1: các pill; mọi chi tiết (cờ, rà prompt, nội dung kịch bản) trong ⓘ
                    with _info(f"sb-mot-{r['sid']}-more", SB.motion_pills(r, srow, voices, bool(img_id), flags, lint),
                               "Cờ kiểm tra, rà prompt, nội dung kịch bản — bấm để xem"):
                        if flags:
                            st.markdown("**Cờ kiểm tra**\n" + "\n".join(f"- ⚑ {f}" for f in flags))
                        if lint:
                            if lint.get("ok") and not lint.get("issues"):
                                st.markdown("**Rà prompt:** ổn")
                            else:
                                st.markdown("**Rà prompt**\n" + "\n".join(f"- 🔍 {i}" for i in lint.get("issues") or []))
                            if lint.get("revised_prompt"):
                                st.markdown("**Bản sửa đề xuất:** " + lint["revised_prompt"])
                        scene_expander(p, r["sid"])
                c0, c1, c2, c3 = st.columns([1.2, 5, 1.4, 1.6], vertical_alignment="top")
                with c0:
                    ui.html(f'<b>{C.unit_label(p, pid, r["idx"])}</b>' + (" ⭐" if data.get("shot_role") == "hero" else "")
                            + (" 🌀" if data.get("camera_complexity") == "complex" else ""))
                    path = job_image(pid, img_id) if img_id else None
                    if path:
                        show_image(path, width=96)
                new = c1.text_area("Motion prompt", r["motion_prompt"], key=f"mp_{r['sid']}", height=90, label_visibility="collapsed")
                badge = ui.stale_badge(srow["motion_stale"]) if srow.get("motion_stale") else ui.state_badge(r["state"])
                c2.markdown(badge, unsafe_allow_html=True)
                c2.caption(f"{r['duration_sec']:g}s · {model_router.label(choice['model'], choice.get('resolution'))}")   # KLD-23
                if c3.button("Lưu chỉnh sửa", key=f"mps_{r['sid']}"):
                    act(lambda: llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": r["idx"], "motion_prompt": new, "camera": r["camera"],
                                                                                 "duration_sec": r["duration_sec"],
                                                                                 "negative_prompt": r["negative_prompt"]}]}))
                    st.rerun()
                if c3.button("✔ Duyệt", key=f"mpa_{r['sid']}", disabled=r["state"] == "approved" and not srow.get("motion_stale")
                             and new == r["motion_prompt"], type="primary"):
                    if new != r["motion_prompt"]:          # M6: approving keeps what was just typed (it used to be thrown away)
                        act(lambda: llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": r["idx"], "motion_prompt": new, "camera": r["camera"],
                                                                                     "duration_sec": r["duration_sec"],
                                                                                     "negative_prompt": r["negative_prompt"]}]}))
                    act(lambda: llm_io.approve_motion_prompt(p, r["sid"]))
                    st.rerun()
                if not v2:
                    for f in flags:
                        st.caption(f"⚑ {f}")
                if v2 and lint.get("revised_prompt") and not (lint.get("ok") and not lint.get("issues")):
                    if st.button("Dùng bản sửa của rà prompt", key=f"lint_apply_{r['sid']}"):
                        act(lambda: claude_tasks.apply_lint(p, pid, r["sid"]), "Đã thay prompt (chờ duyệt lại)")
                        st.rerun()
                elif lint and not v2:
                    if lint.get("ok") and not lint.get("issues"):
                        st.caption("🔍 Rà prompt: ổn")
                    else:
                        with st.container(border=True):
                            for issue in lint.get("issues") or []:
                                _warn(st, f"🔍 {issue}")
                            if lint.get("revised_prompt"):
                                st.caption("Bản sửa đề xuất: " + lint["revised_prompt"])
                                if st.button("Dùng bản sửa", key=f"lint_apply_{r['sid']}"):
                                    act(lambda: claude_tasks.apply_lint(p, pid, r["sid"]), "Đã thay prompt (chờ duyệt lại)")
                                    st.rerun()
                if C.expert():
                    with st.expander("🎥 Video tham chiếu chuyển động" + (" — đã gắn" if r["ref_video_path"] else ""), expanded=False):
                        st.caption("Video chỉ cho model **chuyển động/nhịp/lực**; **diện mạo vẫn lấy từ ảnh khung đầu và ảnh tham chiếu**. "
                                   "Cảnh có video tham chiếu được đề xuất dùng Seedance (tham chiếu đa phương thức). Kling: 'feature' tạo clip mới theo "
                                   "chuyển động, 'base' sửa trực tiếp clip này; không dùng cùng lúc với âm thanh tự sinh của Kling.")
                        if r["ref_video_path"]:
                            st.caption(f"Đang gắn: `{os.path.basename(r['ref_video_path'])}`")
                            if st.button("✖ Bỏ video tham chiếu", key=f"mprv_clear_{r['sid']}"):
                                act(lambda: p.set_motion_ref_video(r["sid"], None), "Đã bỏ")
                                st.rerun()
                        up = st.file_uploader("Tải video tham chiếu (MP4)", type=["mp4", "mov", "webm"], key=f"mprv_up_{r['sid']}")
                        refer_type = st.radio("Kiểu tham chiếu (chỉ Kling)", ["feature", "base"], horizontal=True, key=f"mprv_type_{r['sid']}")
                        if st.button("⬆ Lưu video tham chiếu", key=f"mprv_save_{r['sid']}", disabled=up is None):
                            dest = os.path.join(project_dir(pid, "motion_ref"), f"scene_{r['idx']}_{up.name}")
                            with open(dest, "wb") as f:
                                f.write(up.getbuffer())
                            act(lambda: p.set_motion_ref_video(r["sid"], dest, refer_type), "Đã gắn video tham chiếu")
                            st.rerun()
                if not v2:
                    scene_expander(p, r["sid"])
                scene_box.__exit__(None, None, None)
                if not v2:
                    st.divider()



@st.fragment(run_every=5)
def voice_poll(pid: int) -> None:
    """While voice lines are being made: fetch the finished ones, size the clips to the real voice, redraw when something arrived."""
    try:
        provider = music.audio_provider()
    except ProviderError:
        provider = None
    conn = connect(C.DB)
    directory = audio_lib.assets_dir(C.DATA, pid)
    if provider is None or not any(e["state"] == "running" for e in audio_lib.load(directory)):
        st.rerun()
    before = sum(1 for e in audio_lib.load(directory) if e["state"] == "succeeded")
    audio_lib.refresh(provider, directory)
    after = sum(1 for e in audio_lib.load(directory) if e["state"] == "succeeded")
    if after != before:
        voice.fit_durations(conn, pid, C.DATA)
        st.rerun()
    st.caption(f"🔄 Đang tạo giọng… tự cập nhật mỗi 5 giây · {time.strftime('%H:%M:%S')}")


def voice_panel(p: Pipeline, pid: int) -> None:
    """Character voices for the dialogue (TTS is the main path for Vietnamese lines): make them, hear them, size the clips."""
    stat = voice.status(p.conn, pid, C.DATA)
    if not stat["total"]:
        return
    try:
        provider = music.audio_provider()
    except ProviderError as e:
        st.error(f"Clip AI audio: {e}")
        provider = None
    done = stat.get("succeeded", 0)
    v2 = ui.v2_on()
    if v2:
        from dashboard.design.screens import storyboard_cards as SB
    with st.expander(f"🎙 Giọng thoại (TTS) — {done}/{stat['total']} câu đã có giọng", expanded=done < stat["total"] and not v2):
        _about = ("Thoại tiếng Việt được đọc bằng giọng của từng nhân vật (chọn ở màn Kịch bản · Character Bible). Độ dài giọng THẬT đặt "
                  "thời lượng clip (thay cho ước lượng âm tiết), rồi được xếp lên video cuối không chồng tiếng và làm mốc cho phụ đề.")
        if v2:
            SB.note("Mỗi câu thoại đọc bằng giọng của nhân vật", _about, "sb-voice-about")
        else:
            st.caption(_about)
        if stat["no_voice"]:
            st.warning("Chưa có giọng cho: " + ", ".join(stat["no_voice"]) + " → chọn ở màn Kịch bản (Character Bible → 🎙 Giọng).")
        c1, c2, c3 = st.columns(3)
        todo = stat["missing"] + stat.get("failed", 0)
        if c1.button(f"🎙 Tạo giọng cho {todo} câu" + budget.audio_tag(p.conn, todo, "eleven_v3"), key=f"tts_gen_{pid}", type="primary", disabled=provider is None or not todo,
                     help="Mỗi câu một lần gọi TTS (tốn credit âm thanh; âm thanh chưa có giá nên trần đợt thử tính theo số lượt). "
                          "Câu đã có giọng và không đổi thì bỏ qua. Câu LỖI được gửi lại y nguyên — chỉ có ích khi lỗi do nhà cung cấp; "
                          "lỗi do câu/giọng thì sửa trước."):
            r = voice.generate(p.conn, pid, provider, C.DATA, by_person=True, p=p)
            st.toast(f"Đã gửi {r['sent']} câu, bỏ qua {r['skipped']}" + (f" · thiếu giọng: {', '.join(r['no_voice'])}" if r["no_voice"] else ""))
            st.rerun()
        if c2.button("⟳ Kiểm tra + tải về", key=f"tts_refresh_{pid}", disabled=provider is None):
            audio_lib.refresh(provider, audio_lib.assets_dir(C.DATA, pid))
            ch = voice.fit_durations(p.conn, pid, C.DATA)
            st.toast(f"Đã cập nhật; {len(ch)} clip được kéo dài cho vừa giọng" if ch else "Đã cập nhật")
            st.rerun()
        late = voice.pending_fits(p.conn, pid, C.DATA)
        if late:
            _late = (f"{len(late)} cảnh ĐÃ CÓ video ngắn hơn giọng thật — giữ clip (bản dựng giữ hình dưới câu dài) hoặc bấm nút bên "
                     "phải để làm lại các clip đó cho vừa giọng (tốn tiền video, clip nhóm làm lại cả nhóm).")
            if v2:
                SB.note(f"⚠ {len(late)} cảnh đã có video ngắn hơn giọng thật", _late, "sb-voice-late", kind="warn")
            else:
                st.warning(_late)
        if c3.button("⏱ Đặt thời lượng clip theo giọng thật" + (f" (làm lại {len(late)} clip đã có)" if late else "")
                     + cost.video_button_tag(p.conn, [x["scene_id"] for x in late], seconds={x["scene_id"]: x["need"] for x in late}),
                     key=f"tts_fit_{pid}",
                     help="Cảnh đã có video: thời lượng mới làm video cũ bị coi là cũ → chạy tự động làm lại (tốn tiền)."):
            ch = voice.fit_durations(p.conn, pid, C.DATA, with_clips=True)
            short = [c for c in ch if c["short"]]
            st.toast(f"{len(ch)} clip được kéo dài" + (f"; {len(short)} cảnh thoại dài hơn clip tối đa của model — nên rút thoại" if short else ""))
            st.rerun()
        if stat.get("running"):
            voice_poll(pid)
        k1, k2 = st.columns(2)
        asr = voice_check.asr_available()
        if k1.button("🎧 Kiểm giọng (miễn phí, chạy trên máy)", key=f"tts_check_{pid}", disabled=not done,
                     help="Đo độ dài so với số âm tiết, tìm ngắt quãng giữa câu" + (" và nghe lại thành chữ để so với câu gốc" if asr else
                                                                                   " (cài `pip install faster-whisper` để so cả chữ nghe được)")):
            with st.spinner("Đang kiểm giọng…"):
                r = voice_check.check_project(C.DATA, pid)
            st.toast(f"Đã kiểm {r['checked']} câu mới · {r['bad']} câu nghi lỗi" + ("" if r["asr"] else " (chưa so chữ: chưa cài faster-whisper)"))
            st.rerun()
        bad = voice_check.bad_lines(C.DATA, pid)
        if bad:
            used, allowed = voice_check.redo_counts(C.DATA, pid)      # T7 (S14.3): own count per line, ≤ MAX_REDOS per (câu, giọng)
            ids = tuple((b.get("scene_id"), b.get("line"), b.get("file")) for b in bad) if provider is not None else ()
            question = (f"Tạo lại {len(bad)} câu nghi lỗi? Mỗi câu một lần gọi TTS (tốn credit âm thanh, tính vào trần lượt âm thanh); "
                        f"mỗi câu tối đa {voice_check.MAX_REDOS} lần với cùng câu + giọng (đã dùng {used}/{allowed}). "
                        "Giọng cũ được giữ cho tới khi có bản mới.")
            if confirm_all(key=f"tts_redo_{pid}", ids=ids, label=f"🔁 Tạo lại {len(bad)} câu nghi lỗi (đã dùng {used}/{allowed} lượt)" + budget.audio_tag(p.conn, len(bad), "eleven_v3"),
                           question=question, container=k2, yes_label="Có, tạo lại"):
                r = voice_check.redo(p.conn, pid, provider, C.DATA, p=p)
                st.toast(f"Đã gửi lại {r['sent']} câu" + (f" · không tạo lại {len(r['refused'])} câu: {r['refused'][0]}"
                                                           if r.get("refused") else ""))
                st.rerun()
        directory = audio_lib.assets_dir(C.DATA, pid)
        items = {(e.get("scene_id"), e.get("line")): e for e in audio_lib.load(directory) if e["kind"] == "tts" and e.get("scene_id")}
        cur = None
        for ln in voice.planned_lines(p.conn, pid):
            if ln["idx"] != cur:
                cur = ln["idx"]
                st.markdown(f"**{C.unit_label(p, pid, cur)}**")
            e = items.get((ln["scene_id"], ln["line"]))
            a, b = st.columns([3, 2], vertical_alignment="center")
            a.markdown(f"{escape(ln['speaker'] or '—')}: {escape(ln['text'])}")
            if e is None or e.get("text") != ln["text"]:
                b.caption("chưa có giọng" if ln["voice"] else "nhân vật chưa có giọng")
            elif e["state"] == "succeeded" and e.get("file"):
                b.audio(os.path.join(directory, e["file"]))
                chk = e.get("check") or {}
                b.caption(f"{(e.get('duration_ms') or 0) / 1000:.1f}s" + (" · ✔ đã kiểm" if chk.get("ok") else ""))
                for prob in chk.get("problems") or []:
                    _warn(b, f"⚠ {prob}")
            else:
                b.caption(ui.state_label(e["state"], "audio") + (f": {e.get('message')}" if e.get("message") else ""))


def _warn(target, text) -> None:
    if ui.v2_on():
        target.markdown(f'<span class="sb-warn">{escape(str(text))}</span>', unsafe_allow_html=True)
    else:
        target.markdown(f":orange[{escape(str(text))}]")
