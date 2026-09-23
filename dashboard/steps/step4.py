"""Step 4: video generation."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import auto_poll_videos, dialogue_panel


# ---- step 4 --------------------------------------------------------------------------
def step4(p: Pipeline, pid: int):
    ready = llm_io.ready_for_video(p, pid)
    dialogue_panel(p, pid, "s4")
    runner = video_runner(p)
    models = ["(mặc định: kling-v3-omni)", "kling", "kling-o1", "seedance", "seedance-fast", "seedance-2.5"]
    proj = p.project(pid)
    current = proj["video_model"]
    with st.container(border=True):
        m1, m2, m3 = st.columns([2, 2.4, 2.6], vertical_alignment="center")
        m1.markdown(ui.badge(f"{len(ready)} cảnh sẵn sàng gen", "b-info") +
                    ' <span class="muted">ảnh + prompt đã duyệt</span>', unsafe_allow_html=True)
        choice = m2.selectbox("Model video", models, index=models.index(current) if current in models else 0,
                              key=f"vmodel_{pid}", help="Kling Omni / Seedance; bộ lọc kiểm duyệt khác nhau theo model")
        if (choice if choice in models[1:] else None) != current:
            p.set_video_model(pid, choice if choice in models[1:] else None)
        audio_on = m3.checkbox("🔊 Model tự tạo âm thanh / lời thoại", bool(proj["video_audio"]), key=f"vaudio_{pid}",
                               help="Bật: Kling `sound` / Seedance `generate_audio`. Nhân vật có thể nói (khớp môi do model tự "
                                    "xử lý) nếu lời thoại được ghi trong motion prompt. Có thể đổi giá; chưa thử thật.")
        if audio_on != bool(proj["video_audio"]):
            p.set_video_audio(pid, audio_on)
        if subjects_visible(p, pid):
            n_subj = p.conn.execute("SELECT COUNT(*) c FROM characters WHERE project_id=? AND subject_status='active'",
                                    (pid,)).fetchone()["c"]
            use_subj = st.checkbox(f"🧩 Gắn ảnh chủ thể nhân vật vào video (Seedance) — {n_subj} nhân vật có chủ thể active",
                                   bool(proj["use_subjects"]), key=f"vsubj_{pid}",
                                   help="Chỉ Seedance. Mỗi cảnh gắn chủ thể của các nhân vật xuất hiện trong cảnh (kho chủ thể ở Bước 1). "
                                        "Chưa thử thật; ảnh chủ thể tính vào giới hạn số ảnh tham chiếu.")
            if use_subj != bool(proj["use_subjects"]):
                p.set_use_subjects(pid, use_subj)
        if runner is None:
            st.caption("ℹ Clip AI chưa cấu hình: chỉ theo dõi job thủ công.")
            with st.expander("Cách cấu hình"):
                st.write("Đặt VIDEO_PROVIDER=clipai và CLIPAI_TOKEN (biến môi trường), xem docs/RUNBOOK.md.")
        else:
            st.caption(f"Provider video: {runner.provider.name}" + (" (giả lập)" if runner.provider.name == "mock" else " (gọi API thật, tốn credit)"))
        allowed = show_estimate(video_estimate(p, pid), runner)
        if p.conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type='video_gen' AND state='running' LIMIT 1", (pid,)).fetchone():
            st.info("🔄 Video đang được tạo: trang tự cập nhật, clip xong sẽ tự hiện; bạn không cần bấm gì.")
            auto_poll_videos(pid)
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("▶ Tạo job gen video", disabled=not ready, type="primary"):
            for r in ready:
                exists = p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen'"
                                        " AND state NOT IN ('cancelled','rejected')", (r["scene_id"],)).fetchone()
                if not exists:
                    p.create_job(r["scene_id"], "video_gen")
            st.rerun()
        if c2.button("⟳ Submit + Poll 1 lần", disabled=runner is None or not allowed):
            submitted = runner.submit_pending(pid)
            st.toast(f"Đã gửi {submitted} · {runner.poll_once(pid)}")
            st.rerun()
        if c3.button("▶ Chạy heartbeat tới khi xong", disabled=runner is None or not allowed):
            with st.spinner("Đang chạy heartbeat…"):
                runner.run(pid, interval=float(os.environ.get("HEARTBEAT_SEC", "90")))
            st.rerun()
        if c4.button("↻ Retry tất cả job fail", key="btn_bad_retry"):
            for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='failed'"
                                    " AND escalated=0", (pid,)).fetchall():
                act(lambda: p.retry(j["id"], "retry all"))
            st.rerun()
    jobs = p.conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id"
                          " WHERE j.project_id=? AND j.type='video_gen' AND j.state!='rejected' ORDER BY s.idx, j.id",
                          (pid,)).fetchall()
    done = sum(1 for j in jobs if j["state"] == "succeeded")
    running = sum(1 for j in jobs if j["state"] == "running")
    failed = sum(1 for j in jobs if j["state"] == "failed")
    blocked = p.conn.execute("SELECT COUNT(*) c FROM content_moderation_failures f JOIN jobs j ON j.id=f.job_id"
                             " WHERE j.project_id=?", (pid,)).fetchone()["c"]
    with st.container(border=True):
        extra = (ui.badge(f"{running} running", "b-info") if running else "") + " " + \
                (ui.badge(f"{failed} failed", "b-bad") if failed else "")
        ui.html(ui.card_title("Tiến độ batch") + ui.progress(done, len(jobs), extra))
        if blocked:
            st.caption(f"⚠ {blocked} lần bị chặn risk control — chi tiết ở “⚠ Rủi ro” góc trên.")
    size = "Vừa"
    for j in jobs:
        clip = j["result_path"] if j["state"] == "succeeded" and j["result_path"] and os.path.exists(j["result_path"]) else None
        with st.container(border=True):
            a, b, c, d = st.columns([1.2, 1.6, 1, 2.2], vertical_alignment="center")
            a.markdown(f"**Cảnh {j['idx']}**")
            b.markdown(ui.state_badge(j["state"]) + (" " + ui.badge("⚠ escalated", "b-warn") if j["escalated"] else ""),
                       unsafe_allow_html=True)
            c.caption(f"retry {j['retry_count']}")
            with d:
                if j["state"] in ("queued", "running") and st.button("■ Cancel", key=f"vc_{j['id']}"):
                    act(lambda: runner.cancel_job(j["id"]) if runner else p.cancel(j["id"]))
                    st.rerun()
                if j["state"] == "failed" and not j["escalated"] and st.button("↻ Retry", key=f"vr_{j['id']}"):
                    act(lambda: p.retry(j["id"], "retry"))
                    st.rerun()
                if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"vrs_{j['id']}",
                                                help="Đã hết số lần thử: bắt đầu lại với một job video mới"):
                    if act(lambda: p.restart_job(j["id"]), "Đã xếp hàng job video mới"):
                        st.rerun()
                if clip and st.button("↻ Gen lại video", key=f"vregen_{j['id']}",
                                      help="Chưa ưng: clip này vào thùng rác (giữ 30 ngày) và xếp hàng một video mới. "
                                           "Muốn đổi cách quay thì sửa motion prompt ở Bước 3 trước."):
                    if act(lambda: regen.regenerate_video(p, C.DATA, j["id"]), "Đã xếp hàng gen lại video"):
                        st.rerun()
            if clip:
                show_video(clip, size)
            scene_expander(p, j["scene_id"], with_motion=True)
