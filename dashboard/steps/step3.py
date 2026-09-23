"""Step 3: video motion prompts."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import dialogue_panel


def step3(p: Pipeline, pid: int):
    summ = lineage.summary(p.conn, pid)
    status = lineage.scan(p.conn, pid)
    approved_imgs = [r for r in status.values() if r["image_job_id"]]
    step_header("Bước 3 · Motion, giọng thoại & animatic", "viết cách chuyển động cho từng cảnh, làm giọng, xem nhịp — trước khi tốn credit video",
                f"{summ['motion'][0]}/{summ['total']} prompt đã duyệt", summ["motion"][1])
    rows = p.conn.execute("SELECT s.id sid, s.idx, s.data, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
                          " WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    stale_idx = sorted(r["idx"] for r in status.values() if r["motion_stale"] and r["image_job_id"])
    missing = [r for r in approved_imgs if r["motion_state"] is None]
    client = llm_client()
    with st.container(border=True):
        c1, c2, c3 = st.columns([2.6, 2, 2], vertical_alignment="center")
        todo = len(missing) + len(stale_idx)
        if c1.button(f"🤖 Viết motion prompt ({len(missing)} chưa có · {len(stale_idx)} đã cũ)", type="primary", key=f"llm_mot_{pid}",
                     disabled=client is None or not todo, help=None if client else claude_hint()):
            def go():
                r1 = llm_runner.run_motion(p, pid, client, C.DATA) if missing else {"scenes": 0}
                r2 = llm_runner.run_motion(p, pid, client, C.DATA, only_idx=stale_idx) if stale_idx else {"scenes": 0}
                st.toast(f"Đã viết {r1['scenes'] + r2['scenes']} motion prompt")
            with st.spinner("Claude đang viết motion prompt…"):
                if act(go):
                    st.rerun()
        waiting = [r["sid"] for r in rows if r["state"] != "approved"]
        if confirm_all("btn_ok_all", waiting, f"✔ Duyệt tất cả ({len(waiting)} prompt)", f"Duyệt tất cả {len(waiting)} motion prompt đang chờ?", c2):
            for sid in waiting:
                llm_io.approve_motion_prompt(p, sid)
            st.rerun()
        if c3.button(f"🔍 Rà motion prompt ({len(rows)})", key=f"lint_{pid}", disabled=client is None or not rows,
                     help="Checklist Seedance Final QC + 4 kiểm tra mơ hồ (tỉ lệ, vị trí, đường máy, thời điểm) cho cảnh phức tạp"):
            with st.spinner("Claude đang rà từng prompt…"):
                act(lambda: claude_tasks.lint_motion(p, pid, client))
            st.rerun()
        if client is None:
            st.caption(claude_hint())
        with st.expander("✍ Nâng cao: prompt gửi Claude (copy) & dán kết quả"):
            st.code(prompts.build_motion_bundle(p, pid), language="markdown")
            raw = st.text_area("Dán JSON motion prompts từ Claude", key=f"motion_{pid}", height=140)
            if st.button("▶ Lưu motion prompts", disabled=not raw.strip(), key=f"mot_paste_{pid}"):
                if act(lambda: llm_io.store_motion_prompts(p, pid, raw), "Đã lưu"):
                    st.rerun()
    voice_panel(p, pid)
    animatic_panel(p, pid)
    with st.container(border=True):
        ui.html(ui.card_title("Motion prompt từng cảnh", f"{len(rows)} cảnh"))
        if not rows:
            st.caption("Chưa có motion prompt: duyệt ảnh ở Bước 2 rồi bấm “🤖 Viết motion prompt”.")
        for r in rows:
            data = json.loads(r["data"] or "{}")
            srow = status.get(r["sid"]) or {}
            img_id = srow.get("image_job_id")
            choice = model_router.scene_choice(p.conn, r["sid"])
            c0, c1, c2, c3 = st.columns([1.2, 5, 1.4, 1.6], vertical_alignment="top")
            with c0:
                ui.html(f'<b>Cảnh {r["idx"]}</b>' + (" ⭐" if data.get("shot_role") == "hero" else "")
                        + (" 🌀" if data.get("camera_complexity") == "complex" else ""))
                path = job_image(pid, img_id) if img_id else None
                if path:
                    show_image(path, width=96)
            new = c1.text_area("Motion prompt", r["motion_prompt"], key=f"mp_{r['sid']}", height=90, label_visibility="collapsed")
            badge = ui.stale_badge(srow["motion_stale"]) if srow.get("motion_stale") else ui.state_badge(r["state"])
            c2.markdown(badge, unsafe_allow_html=True)
            c2.caption(f"{r['duration_sec']:g}s · {choice['model']}")
            if c3.button("Lưu chỉnh sửa", key=f"mps_{r['sid']}"):
                act(lambda: llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": r["idx"], "motion_prompt": new, "camera": r["camera"],
                                                                             "duration_sec": r["duration_sec"],
                                                                             "negative_prompt": r["negative_prompt"]}]}))
                st.rerun()
            if c3.button("✔ Duyệt", key=f"mpa_{r['sid']}", disabled=r["state"] == "approved" and not srow.get("motion_stale"), type="primary"):
                act(lambda: llm_io.approve_motion_prompt(p, r["sid"]))
                st.rerun()
            flags = json.loads(r["check_flags"] or "[]") if r["check_flags"] else []
            for f in flags:
                st.caption(f"⚑ {f}")
            lint = json.loads(r["lint"] or "{}") if r["lint"] else {}
            if lint:
                if lint.get("ok") and not lint.get("issues"):
                    st.caption("🔍 Rà prompt: ổn")
                else:
                    with st.container(border=True):
                        for issue in lint.get("issues") or []:
                            st.markdown(f":orange[🔍 {escape(str(issue))}]")
                        if lint.get("revised_prompt"):
                            st.caption("Bản sửa đề xuất: " + lint["revised_prompt"])
                            if st.button("Dùng bản sửa", key=f"lint_apply_{r['sid']}"):
                                act(lambda: claude_tasks.apply_lint(p, pid, r["sid"]), "Đã thay prompt (chờ duyệt lại)")
                                st.rerun()
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
            scene_expander(p, r["sid"])
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
    with st.expander(f"🎙 Giọng thoại (TTS) — {done}/{stat['total']} câu đã có giọng", expanded=done < stat["total"]):
        st.caption("Thoại tiếng Việt được đọc bằng giọng của từng nhân vật (chọn ở Bước 1 · Character Bible). Độ dài giọng THẬT đặt "
                   "thời lượng clip (thay cho ước lượng âm tiết), rồi được xếp lên video cuối không chồng tiếng và làm mốc cho phụ đề.")
        if stat["no_voice"]:
            st.warning("Chưa có giọng cho: " + ", ".join(stat["no_voice"]) + " → chọn ở Bước 1 (Character Bible → 🎙 Giọng).")
        c1, c2, c3 = st.columns(3)
        todo = stat["missing"] + stat.get("failed", 0)
        if c1.button(f"🎙 Tạo giọng cho {todo} câu", key=f"tts_gen_{pid}", type="primary", disabled=provider is None or not todo,
                     help="Mỗi câu một lần gọi TTS (tốn credit âm thanh). Câu đã có giọng và không đổi thì bỏ qua."):
            r = voice.generate(p.conn, pid, provider, C.DATA)
            st.toast(f"Đã gửi {r['sent']} câu, bỏ qua {r['skipped']}" + (f" · thiếu giọng: {', '.join(r['no_voice'])}" if r["no_voice"] else ""))
            st.rerun()
        if c2.button("⟳ Kiểm tra + tải về", key=f"tts_refresh_{pid}", disabled=provider is None):
            audio_lib.refresh(provider, audio_lib.assets_dir(C.DATA, pid))
            ch = voice.fit_durations(p.conn, pid, C.DATA)
            st.toast(f"Đã cập nhật; {len(ch)} clip được kéo dài cho vừa giọng" if ch else "Đã cập nhật")
            st.rerun()
        if c3.button("⏱ Đặt thời lượng clip theo giọng thật", key=f"tts_fit_{pid}"):
            ch = voice.fit_durations(p.conn, pid, C.DATA)
            short = [c for c in ch if c["short"]]
            st.toast(f"{len(ch)} clip được kéo dài" + (f"; {len(short)} cảnh thoại dài hơn clip tối đa của model — nên rút thoại" if short else ""))
            st.rerun()
        if stat.get("running"):
            voice_poll(pid)
        directory = audio_lib.assets_dir(C.DATA, pid)
        items = {(e.get("scene_id"), e.get("line")): e for e in audio_lib.load(directory) if e["kind"] == "tts" and e.get("scene_id")}
        cur = None
        for ln in voice.planned_lines(p.conn, pid):
            if ln["idx"] != cur:
                cur = ln["idx"]
                st.markdown(f"**Cảnh {cur}**")
            e = items.get((ln["scene_id"], ln["line"]))
            a, b = st.columns([3, 2], vertical_alignment="center")
            a.markdown(f"{escape(ln['speaker'] or '—')}: {escape(ln['text'])}")
            if e is None or e.get("text") != ln["text"]:
                b.caption("chưa có giọng" if ln["voice"] else "nhân vật chưa có giọng")
            elif e["state"] == "succeeded" and e.get("file"):
                b.audio(os.path.join(directory, e["file"]))
                b.caption(f"{(e.get('duration_ms') or 0) / 1000:.1f}s")
            else:
                b.caption(ui.state_label(e["state"], "audio") + (f": {e.get('message')}" if e.get("message") else ""))


def animatic_panel(p: Pipeline, pid: int) -> None:
    """The film's rhythm before any video credit: approved pictures × planned lengths + voices + music."""
    out = os.path.join(C.DATA, str(pid), "output", "ANIMATIC.mp4")
    with st.expander("🎞 Animatic — xem nhịp phim trước khi gen video", expanded=os.path.exists(out)):
        st.caption("Ghép ảnh đã duyệt theo thời lượng dự kiến của từng cảnh, kèm giọng thoại và nhạc (nếu đã có). Không tốn credit: "
                   "dùng để chỉnh nhịp, độ dài, thoại trước bước đắt nhất (video).")
        if st.button("🎞 Dựng animatic", key=f"anim_{pid}"):
            with st.spinner("Đang dựng animatic…"):
                ok = act(lambda: st.session_state.__setitem__(f"anim_res_{pid}", delivery.animatic(p, pid, C.DATA)))
            if ok:
                r = st.session_state.pop(f"anim_res_{pid}")
                st.toast(f"Animatic {r['seconds']:.0f}s, {r['scenes']} cảnh")
                st.rerun()
        if os.path.exists(out):
            show_video(out)
