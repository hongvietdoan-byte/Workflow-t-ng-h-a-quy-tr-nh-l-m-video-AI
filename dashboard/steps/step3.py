"""Step 3: video motion prompts."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import dialogue_panel


def step3(p: Pipeline, pid: int):
    approved = p.conn.execute(
        "SELECT s.idx FROM scenes s WHERE s.project_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE j.scene_id=s.id"
        " AND j.type='image_gen' AND j.state='approved') ORDER BY s.idx", (pid,)).fetchall()
    rows = p.conn.execute(
        "SELECT s.id sid, s.idx, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    dialogue_panel(p, pid, "s3")
    with st.container(border=True):
        a, b = st.columns([3, 1], vertical_alignment="center")
        a.markdown(ui.badge(f"{len(approved)} cảnh đã có ảnh được duyệt", "b-info") +
                   ' <span class="muted">Knowledge Base · image-to-video</span>', unsafe_allow_html=True)
        waiting = [r["sid"] for r in rows if r["state"] != "approved"]
        if confirm_all("btn_ok_all", waiting, f"✔ Duyệt tất cả ({len(waiting)} prompt)",
                       f"Duyệt tất cả {len(waiting)} motion prompt đang chờ?", b):
            for sid in waiting:
                llm_io.approve_motion_prompt(p, sid)
            st.rerun()
        client = llm_client()
        if client is not None and st.button("🤖 Sinh motion prompt bằng Claude (cảnh chưa có)", type="primary",
                                            key=f"llm_mot_{pid}"):
            with st.spinner("Claude đang viết motion prompt…"):
                ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_motion(p, pid, client, C.DATA)))
            if ok:
                r = st.session_state.pop("llm_res")
                st.toast(f"Đã lưu {r['scenes']} motion prompt ({tokens_text(r)})")
                st.rerun()
        with st.expander("Prompt gửi Claude (copy) & dán kết quả"):
            st.code(prompts.build_motion_bundle(p, pid), language="markdown")
            raw = st.text_area("Dán JSON motion prompts từ Claude", key=f"motion_{pid}", height=140)
            if st.button("▶ Lưu motion prompts", disabled=not raw.strip()):
                if act(lambda: llm_io.store_motion_prompts(p, pid, raw), "Đã lưu"):
                    st.rerun()
    with st.container(border=True):
        ui.html(ui.card_title("Video Motion Prompt", f"{len(rows)} cảnh"))
        if not rows:
            st.caption("Chưa có motion prompt. Dán JSON từ Claude ở trên.")
        for r in rows:
            img_job = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'"
                                     " ORDER BY id DESC LIMIT 1", (r["sid"],)).fetchone()
            c0, c1, c2, c3 = st.columns([1.2, 5, 1.1, 1.6], vertical_alignment="center")
            with c0:
                ui.html(f'<b>Cảnh {r["idx"]}</b>')
                path = job_image(pid, img_job["id"]) if img_job else None
                if path:
                    show_image(path, width=96)
            new = c1.text_area("Motion prompt", r["motion_prompt"], key=f"mp_{r['sid']}", height=70,
                               label_visibility="collapsed")
            c2.markdown(ui.badge("đã duyệt", "b-ok") if r["state"] == "approved" else ui.badge("chờ duyệt", "b-warn"),
                        unsafe_allow_html=True)
            c2.caption(f"{r['duration_sec']}s")
            if c3.button("Lưu chỉnh sửa", key=f"mps_{r['sid']}"):
                act(lambda: llm_io.store_motion_prompts(
                    p, pid, {"scenes": [{"idx": r["idx"], "motion_prompt": new, "camera": r["camera"],
                                         "duration_sec": r["duration_sec"],
                                         "negative_prompt": r["negative_prompt"]}]}))
                st.rerun()
            if c3.button("✔ Duyệt", key=f"mpa_{r['sid']}", disabled=r["state"] == "approved", type="primary"):
                act(lambda: llm_io.approve_motion_prompt(p, r["sid"]))
                st.rerun()
            with st.expander("🎥 Video tham chiếu chuyển động" + (" — đã gắn" if r["ref_video_path"] else ""),
                             expanded=False):
                st.caption("Video chỉ cho model **chuyển động/nhịp/lực** (vd clip gameplay thật của một skill); "
                          "**diện mạo nhân vật vẫn lấy từ ảnh khung đầu / Character Bible**, không lấy từ video này. "
                          "Kling: chọn 'feature' (mặc định, tạo clip mới theo chuyển động) hoặc 'base' (sửa trực tiếp "
                          "clip này). Seedance: luôn coi là ví dụ chuyển động, không phân biệt feature/base. "
                          "Không dùng cùng lúc với '🔊 Model tự tạo âm thanh' trên Kling (API sẽ từ chối).")
                if r["ref_video_path"]:
                    st.caption(f"Đang gắn: `{os.path.basename(r['ref_video_path'])}`")
                    if st.button("✖ Bỏ video tham chiếu", key=f"mprv_clear_{r['sid']}"):
                        act(lambda: p.set_motion_ref_video(r["sid"], None), "Đã bỏ")
                        st.rerun()
                up = st.file_uploader("Tải video tham chiếu (MP4)", type=["mp4", "mov", "webm"],
                                      key=f"mprv_up_{r['sid']}")
                refer_type = st.radio("Kiểu tham chiếu (chỉ Kling)", ["feature", "base"],
                                      horizontal=True, key=f"mprv_type_{r['sid']}")
                if st.button("⬆ Lưu video tham chiếu", key=f"mprv_save_{r['sid']}", disabled=up is None):
                    dest = os.path.join(project_dir(pid, "motion_ref"), f"scene_{r['idx']}_{up.name}")
                    with open(dest, "wb") as f:
                        f.write(up.getbuffer())
                    act(lambda: p.set_motion_ref_video(r["sid"], dest, refer_type), "Đã gắn video tham chiếu")
                    st.rerun()
            scene_expander(p, r["sid"])
            st.divider()
