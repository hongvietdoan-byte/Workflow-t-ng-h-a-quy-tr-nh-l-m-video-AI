"""Step 4: video generation."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import auto_poll_videos, video_busy


def step4(p: Pipeline, pid: int):
    runner = video_runner(p)
    proj = p.project(pid)
    summ = lineage.summary(p.conn, pid)
    step_header("Bước 4 · Gen video + QC video", "mỗi cảnh một clip đúng nhân vật, đúng vật lý, khớp motion prompt",
                f"{summ['videos'][0]}/{summ['total']} cảnh có clip dùng được", summ["videos"][1])
    model_plan_panel(p, pid)
    with st.container(border=True):
        m1, m2 = st.columns(2)
        audio_on = m1.checkbox("🔊 Model tự tạo âm thanh (tiếng động, không khí)", bool(proj["video_audio"]), key=f"vaudio_{pid}",
                               help="Kling `sound` / Seedance `generate_audio`. Thoại tiếng Việt nên dùng giọng TTS ở Bước 3: theo blog Kling, "
                                    "giọng tự sinh của Kling 3.0 chỉ có 5 ngôn ngữ (chưa có tiếng Việt). Có thể đổi giá.")
        if audio_on != bool(proj["video_audio"]):
            p.set_video_audio(pid, audio_on)
        qc_on = m2.checkbox("🔍 Claude kiểm tra từng clip (giữ nhân vật, vật lý, khớp prompt, biến dạng)", bool(proj["qc_video"]),
                            key=f"vqc_{pid}", help="Clip đạt mới vào bản ghép; theo chính sách QC của dự án (tự gen lại hay chờ bạn duyệt).")
        if qc_on != bool(proj["qc_video"]):
            p.set_project_field(pid, "qc_video", 1 if qc_on else 0)
        if subjects_visible(p, pid):
            n_subj = p.conn.execute("SELECT COUNT(*) c FROM characters WHERE project_id=? AND subject_status='active'", (pid,)).fetchone()["c"]
            use_subj = st.checkbox(f"🧩 Gắn ảnh chủ thể nhân vật vào video (Seedance) — {n_subj} nhân vật có chủ thể active",
                                   bool(proj["use_subjects"]), key=f"vsubj_{pid}")
            if use_subj != bool(proj["use_subjects"]):
                p.set_use_subjects(pid, use_subj)
        if runner is None:
            st.caption("ℹ Clip AI chưa cấu hình (VIDEO_PROVIDER=clipai + CLIPAI_TOKEN, xem docs/RUNBOOK.md).")
        else:
            st.caption(f"Nhà cung cấp video: {runner.provider.name}" + (" (giả lập)" if runner.provider.name.startswith("mock") else " (gọi API thật, tốn credit)")
                       + f" · khung {formats.label(formats.project_aspect(proj))}")
        allowed_run = show_estimate(cost.estimate_videos_by_scene(p, pid, cost.load_pricing()), runner)
        stale_videos = [r for r in lineage.scan(p.conn, pid).values() if r["video_stale"]]
        c1, c2 = st.columns([2.6, 2])
        todo = batch.videos_to_make(p, pid)
        if c1.button(f"▶ Gen video ({len(todo)} cảnh sẵn sàng" + (f", {len(stale_videos)} đã cũ" if stale_videos else "") + ")",
                     type="primary", key=f"gen_vid_{pid}", disabled=runner is None or not allowed_run or not (todo or stale_videos)):
            def go():
                r = batch.queue_videos(p, pid, C.DATA)
                sent = runner.submit_pending(pid)
                st.toast(f"Xếp hàng {r['created']} clip mới, {r['redo']} clip làm lại · đã gửi {sent}")
            if act(go):
                st.rerun()
        failed = p.conn.execute("SELECT j.id FROM jobs j WHERE j.project_id=? AND j.type='video_gen' AND j.state='failed' AND j.escalated=0"
                                " AND NOT EXISTS (SELECT 1 FROM content_moderation_failures f WHERE f.job_id=j.id)", (pid,)).fetchall()
        prices = [cost.clip_estimate(p.conn, p.job(j["id"])["scene_id"]) for j in failed]
        total = None if any(x is None for x in prices) else sum(prices)
        if c2.button(f"↻ Gen lại clip lỗi ({len(failed)}){cost.price_tag(total, len(failed))}", key="btn_bad_retry", disabled=not failed,
                     help="Clip bị bộ lọc nội dung chặn không nằm trong nút này: sửa prompt trước."):
            for j in failed:
                act(lambda: p.retry(j["id"], "gen lại clip lỗi"))
            st.rerun()
        waiting = [j["id"] for j in p.conn.execute(
            "SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='pending_review' ORDER BY id", (pid,)).fetchall()]
        if waiting and confirm_all(f"vid_ok_all_{pid}", waiting, f"✔ Duyệt tất cả ({len(waiting)} clip)",
                                   f"Duyệt tất cả {len(waiting)} clip đang chờ duyệt?"):
            for jid in waiting:
                p.approve(jid, "user")
            st.rerun()
        if video_busy(p.conn, pid):
            auto_poll_videos(pid)
        problem = autoqc.video_last_error(pid)
        if problem:
            st.warning(f"⚠ Tự kiểm tra video đã dừng: {problem}")
            if st.button("↻ Thử kiểm tra lại", key=f"vqc_retry_{pid}"):
                autoqc.clear_video_error(pid)
                st.rerun()
    jobs = p.conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id"
                          " WHERE j.project_id=? AND j.type='video_gen' AND j.state!='cancelled' ORDER BY s.idx, j.id",
                          (pid,)).fetchall()
    latest = {}
    for j in jobs:
        latest[j["scene_id"]] = j
    blocked = p.conn.execute("SELECT COUNT(*) c FROM content_moderation_failures f JOIN jobs j ON j.id=f.job_id WHERE j.project_id=?",
                             (pid,)).fetchone()["c"]
    if blocked:
        st.caption(f"⚠ {blocked} lần bị bộ lọc nội dung chặn — chi tiết ở “⚠ Rủi ro” góc trên.")
    status = lineage.scan(p.conn, pid)
    for j in sorted(latest.values(), key=lambda x: x["idx"]):
        video_card(p, pid, j, runner, (status.get(j["scene_id"]) or {}).get("video_stale"))
    if not latest:
        st.caption("Chưa có clip nào: duyệt motion prompt ở Bước 3 rồi bấm “▶ Gen video”.")
    clip_set_panel(p, pid)
    experiments_panel(p, pid, runner)


def clip_set_panel(p: Pipeline, pid: int) -> None:
    """v3: consistency across ALL clips (clips made by different models drift in colour / look / faces) + the cut points between
    shots that continue each other."""
    usable = p.conn.execute("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='video_gen'"
                            " AND state IN ('succeeded','approved')", (pid,)).fetchone()[0]
    if usable < 2:
        return
    last = claude_tasks.last_clip_set_check(C.DATA, pid)
    label = "🎨 Kiểm tra đồng bộ cả bộ clip" + ("" if last is None else (" — ổn" if last.get("ok") and not last.get("issues")
                                                                         else f" — {len(last.get('issues') or [])} clip lệch"))
    with st.expander(label, expanded=bool(last and last.get("issues"))):
        st.caption("Claude xem khung giữa của mọi clip và các điểm nối giữa hai shot liền mạch: màu, ánh sáng, chất hình, nhân vật có "
                   "khớp nhau không (clip do các model khác nhau làm dễ lệch). Nên chạy trước khi dựng ở Bước 5.")
        client = llm_client()
        if st.button(f"🤖 Kiểm tra {usable} clip", key=f"clipqc_{pid}", disabled=client is None, help=None if client else claude_hint()):
            with st.spinner("Claude đang so cả bộ clip…"):
                act(lambda: claude_tasks.clip_set_consistency(p, pid, client, C.DATA))
            st.rerun()
        folder = os.path.join(C.DATA, str(pid), "qc_set", "clips")
        if last is not None:
            for name in ("clips_mid.png", "clips_cuts.png"):
                if os.path.exists(os.path.join(folder, name)):
                    show_image(os.path.join(folder, name), width="stretch")
            if last.get("summary"):
                st.info(last["summary"])
            for n, it in enumerate(last.get("issues") or []):
                c1, c2 = st.columns([4, 1.3], vertical_alignment="center")
                c1.markdown(f"**{C.unit_code(p, pid, it['idx'])}**: {escape(it['problem'])}"
                            + (f" → _{escape(it.get('fix') or '')}_" if it.get("fix") else ""))
                job = p.conn.execute("SELECT j.id FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.project_id=? AND s.idx=?"
                                     " AND j.type='video_gen' AND j.state IN ('succeeded','approved') ORDER BY j.id DESC LIMIT 1",
                                     (pid, it["idx"])).fetchone()
                if job and c2.button("↻ Gen lại clip này" + cost.price_tag(cost.clip_estimate(p.conn, p.job(job["id"])["scene_id"])),
                                     key=f"clipqc_redo_{pid}_{n}"):
                    act(lambda: regen.regenerate_video(p, C.DATA, job["id"], f"Đồng bộ cả bộ clip: {it.get('fix') or it['problem']}"),
                        "Đã xếp hàng gen lại")
                    st.rerun()



def _go_step3() -> None:
    st.session_state["step"] = STEPS[2]


def model_plan_panel(p: Pipeline, pid: int) -> None:
    """Which model for which scene, from the ClipAI model guide (no fixed default): recommendation + reason + price, overridable."""
    pricing = cost.load_pricing()
    rows = model_router.plan(p.conn, pid, pricing)
    ready = {r["scene_id"] for r in llm_io.ready_for_video(p, pid, include_stale=True)}
    has_mp = {r["scene_id"] for r in p.conn.execute("SELECT m.scene_id FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?", (pid,))}
    rows = [r for r in rows if r["scene_id"] in has_mp]
    proj = p.project(pid)
    prio = model_router.priority_of(proj)
    profiles = model_router.load_profiles()
    with st.expander(f"🎛 Model cho từng cảnh — ưu tiên “{profiles['priorities'][prio]['label']}”"
                     + (f" · ≈ ${model_router.total(rows):.2f}" if rows and model_router.total(rows) is not None else ""),
                     expanded=bool(rows)):
        st.caption("Theo slide ClipAI “Hôm nay tôi chọn mô hình video như thế nào”: cảnh then chốt / phức tạp / có video tham chiếu → Seedance 2.5; "
                   "cảnh thường → Seedance 2.0 hoặc 2.0 Fast; đối thoại nhiều nhân vật / cảnh chuyển tiếp rẻ → Kling 3.0 Omni. "
                   "MiniMax H3 và Seedance 2.0 Mini chỉ có trên web ClipAI (không gen tự động được). Đổi ưu tiên ở Bước 1 · 📐 Định dạng.")
        from core import shots as _shots
        if _shots.mode(proj) == "multishot":
            groups = _shots.multishot_groups(p.conn, pid)
            st.info(f"Kling multi-shot: {len(groups)} lần gen cho {sum(len(g) for g in groups)} shot (mỗi lần ≤ 15s, mỗi shot ≥ 3s rồi cắt đúng độ dài). "
                    "Shot đầu mỗi nhóm gửi cho cả nhóm khi mọi shot của nhóm đã duyệt motion prompt.")
        elif _shots.mode(proj) == "per_shot":
            st.caption("Chia shot: các shot cùng nhóm cảnh dùng chung một model; shot “nối liền” dùng Seedance thì kết thúc đúng ảnh khung đầu của shot sau.")
        if model_router.chosen_priority(proj) is None and not proj["video_model"]:
            st.warning("Dự án cũ chưa chọn ưu tiên model nên đang dùng mặc định cũ (Kling cho mọi cảnh).")
            if st.button("Dùng đề xuất theo cảnh (ưu tiên Cân bằng)", key=f"vm_prio_{pid}"):
                p.set_project_field(pid, "model_priority", model_router.DEFAULT_PRIORITY)
                st.rerun()
        if proj["video_model"]:
            st.warning(f"Dự án đang đặt MỘT model chung cho mọi cảnh (cách cũ): {proj['video_model']}.")
            if st.button("Bỏ model chung — dùng đề xuất theo cảnh", key=f"vm_clear_{pid}"):
                p.set_video_model(pid, None)
                st.rerun()
        if not rows:
            st.caption("Chưa có motion prompt nào: viết ở Bước 3.")
            return
        api = model_router.api_models(profiles)
        options = [None] + list(api)
        for r in rows:
            c0, c1, c2, c3 = st.columns([0.8, 2.2, 4, 1.4], vertical_alignment="center")
            c0.markdown(f"**{C.unit_code(p, pid, r['idx'])}**" + ("" if r["scene_id"] in ready else " ·"))
            cur = r["model"] if r["source"] == "override" else None
            pick = c1.selectbox("Model", options, index=options.index(cur) if cur in options else 0, key=f"vm_{pid}_{r['scene_id']}",
                                label_visibility="collapsed",
                                format_func=lambda a: f"Đề xuất: {api.get(r['recommended']['model'], {}).get('label', r['recommended']['model'])}"
                                if a is None else api[a]["label"])
            if pick != cur:
                act(lambda: model_router.set_override(p.conn, r["scene_id"], pick))
                st.rerun()
            c2.caption(r["reason"])
            c3.caption(f"{r['seconds']:g}s · " + (f"\\${r['cost']:.2f}" if r["cost"] is not None else "chưa có giá"))
        totals = {k: model_router.total(model_router.plan(p.conn, pid, pricing, priority=k)) for k in model_router.PRIORITIES}
        st.caption("So sánh tổng (chưa tính gen lại): " + " · ".join(
            f"{profiles['priorities'][k]['label']} ≈ " + (f"\\${v:.2f}" if v is not None else "?") for k, v in totals.items()))


def video_card(p: Pipeline, pid: int, j, runner, stale_reason) -> None:
    clip = j["result_path"] if j["state"] in ("succeeded", "pending_review", "approved") and j["result_path"] and os.path.exists(j["result_path"]) else None
    blocked = p.conn.execute("SELECT error_message FROM content_moderation_failures WHERE job_id=? ORDER BY id DESC LIMIT 1", (j["id"],)).fetchone()
    scores = qc_scores(p, j["id"])
    tag = cost.price_tag(cost.clip_estimate(p.conn, j["scene_id"]))          # M8: price on every button that sends a clip again
    with st.container(border=True):
        a, b, c = st.columns([1.2, 3, 2.4], vertical_alignment="center")
        a.markdown(f"**{C.unit_label(p, j['project_id'], j['idx'])}**")
        badges = ui.state_badge(j["state"], "video_gen") + (" " + ui.badge("⚠ cần xem", "b-warn") if j["escalated"] else "") \
            + (" " + ui.badge("bị chặn nội dung", "b-bad") if blocked else "") + (" " + ui.stale_badge(stale_reason) if stale_reason else "")
        b.markdown(badges + f' <span class="muted">{escape(j["model"] or "")} · gen lại {j["retry_count"]} lần</span>', unsafe_allow_html=True)
        if scores:
            mean = sum(s["score"] for s in scores) / len(scores)
            b.markdown(ui.qc_bar(mean, p.project(pid)["qc_auto_pass_threshold"]), unsafe_allow_html=True)
        with c:
            if j["state"] in ("queued", "running") and st.button("■ Hủy", key=f"vc_{j['id']}"):
                act(lambda: runner.cancel_job(j["id"]) if runner else p.cancel(j["id"]))
                st.rerun()
            if j["state"] == "pending_review":
                x, y = st.columns(2)
                if x.button("✔ Duyệt clip", key=f"va_{j['id']}", type="primary"):
                    act(lambda: p.approve(j["id"], "user"))
                    st.rerun()
                if y.button("✖ Loại & gen lại" + tag, key=f"vr_rej_{j['id']}"):
                    act(lambda: p.reject(j["id"], "user", st.session_state.get(f"vnote_{j['id']}") or None))
                    st.rerun()
            if j["state"] == "failed" and blocked:
                st.caption("Bị bộ lọc nội dung chặn: gen lại nguyên prompt sẽ lại bị chặn và tốn credit.")
                st.button("✏ Sửa motion prompt rồi gen lại", key=f"vfix_{j['id']}", on_click=_go_step3)
            elif j["state"] == "failed" and not j["escalated"] and st.button("↻ Gen lại" + tag, key=f"vr_{j['id']}"):
                act(lambda: p.retry(j["id"], "gen lại"))
                st.rerun()
            if j["escalated"] and not blocked and st.button("↺ Làm lại từ đầu" + tag, key=f"vrs_{j['id']}",
                                                            help="Đã hết số lần thử: bắt đầu lại với một job video mới"):
                if act(lambda: p.restart_job(j["id"]), "Đã xếp hàng video mới"):
                    st.rerun()
            if clip and j["state"] in ("succeeded", "approved") and st.button(
                    ("↻ Gen lại theo ảnh/prompt mới" if stale_reason else "↻ Gen lại video") + tag, key=f"vregen_{j['id']}",
                    help="Clip này vào thùng rác (giữ 30 ngày) và xếp hàng video mới. Muốn đổi cách quay thì sửa motion prompt ở Bước 3 trước."):
                if act(lambda: regen.regenerate_video(p, C.DATA, j["id"], f"làm lại vì {stale_reason}" if stale_reason else None),
                       "Đã xếp hàng gen lại video"):
                    st.rerun()
        if clip:
            left, right = st.columns([1, 2])
            src = job_image(pid, j["source_job_id"]) if j["source_job_id"] else None
            if src:
                left.caption("Ảnh khung đầu")
                with left:
                    show_image(src, width="stretch")
            with right:
                show_video(clip)
        if scores:
            st.caption(" · ".join(f"{CRITERIA_LABEL.get(s['criterion'], s['criterion'])} {s['score']:.2f}" for s in scores))
        keep = p.keepable_rejected(j["scene_id"]) if j["state"] in ("rejected", "queued", "failed", "retryable") else None
        if keep is not None:
            kept = qc_scores(p, keep["id"])
            mean = sum(s["score"] for s in kept) / len(kept) if kept else None
            with st.expander("👀 Bản QC đã loại" + (f" (QC {mean:.2f})" if mean is not None else "") + " — xem và giữ lại nếu dùng được",
                             expanded=j["state"] == "rejected"):
                show_video(keep["result_path"])
                if keep["retry_reason"] or kept:
                    st.caption("Lý do QC loại: " + escape((p.conn.execute("SELECT note FROM review_log WHERE job_id=? ORDER BY id DESC LIMIT 1",
                                                                          (keep["id"],)).fetchone() or {"note": ""})["note"] or "")[:400])
                if st.button("✔ Vẫn dùng bản này", key=f"vkeep_{keep['id']}", type="primary",
                             help="Bạn là người quyết định cuối: giữ clip QC đã loại, hủy lần gen lại đang chờ (không tốn thêm credit)."):
                    if act(lambda: p.keep_rejected(keep["id"]), "Đã giữ clip"):
                        st.rerun()
        if j["state"] == "pending_review":
            st.text_input("Ghi chú lý do loại (đưa vào lần gen lại)", key=f"vnote_{j['id']}")
        scene_expander(p, j["scene_id"], with_motion=True)



def experiments_panel(p: Pipeline, pid: int, runner) -> None:
    """Experiment (off the main path): Kling multi-shot for one sequence, to compare continuity with the per-scene clips."""
    from core import experiments, shots
    if shots.active(p, pid):       # v3 shot projects have the real thing (shot_mode = multishot)
        return
    seqs = experiments.sequences(p, pid)
    items = experiments.load(C.DATA, pid)
    if not seqs and not items:
        return
    with st.expander(f"🧪 Thử nghiệm: Kling multi-shot cho một nhóm cảnh ({len(items)})"):
        st.caption("Gen cả một nhóm cảnh liên tiếp trong MỘT lần (Kling 3.0 Omni, tối đa 15 giây) để so độ liền mạch với clip từng cảnh. "
                   "Kết quả KHÔNG tự vào bản ghép; tốn credit như một clip cùng độ dài.")
        if seqs and runner is not None:
            seq = st.selectbox("Nhóm cảnh", list(seqs), key=f"ms_seq_{pid}",
                               format_func=lambda k: f"Nhóm {k}: cảnh " + ", ".join(str(s["idx"]) for s in seqs[k]))
            if confirm_all(f"ms_go_{pid}", [seq], "🧪 Gen thử multi-shot", "Gen thử multi-shot cho nhóm này? (tốn credit)", st, "Có, gen thử"):
                act(lambda: experiments.kling_multishot(p, pid, seq, runner.provider, C.DATA), "Đã gửi thử nghiệm")
                st.rerun()
        if any(e["state"] == "running" for e in items) and runner is not None and st.button("⟳ Kiểm tra thử nghiệm", key=f"ms_refresh_{pid}"):
            act(lambda: experiments.refresh(runner.provider, C.DATA, pid))
            st.rerun()
        for e in reversed(items):
            st.markdown(f"- Nhóm {e['sequence']} (cảnh {', '.join(map(str, e['scenes']))}, {e['seconds']}s) · {ui.state_label(e['state'])}"
                        + (f" · {escape(e.get('message') or '')}" if e["state"] == "failed" else ""))
            if e.get("file") and os.path.exists(e["file"]):
                show_video(e["file"])
