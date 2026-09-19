"""Unified control dashboard (V1 skeleton): one tool, stepper by step order, per-step control buttons.

Run:  py -m streamlit run dashboard/app.py
Claude steps (Director / QC / motion prompt) use copy-paste JSON until the API runner is wired in.
"""
import json
import os
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import ffmpeg_studio, llm_io, preflight, prompts, script_parser  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline, PipelinePaused  # noqa: E402
from core.providers import MockImageProvider, MockVideoProvider  # noqa: E402
from core.runner import ImageRunner, VideoRunner  # noqa: E402
from core.states import InvalidTransition, JobState  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))
DATA = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))
STEPS = ["1 · Kịch bản & phân tích", "2 · Gen ảnh + QC", "3 · Video Prompt", "4 · Gen video",
         "5a · Nhạc nền", "5b · Ghép & Render", "Lịch sử"]
BADGE = {"queued": "⚪", "running": "🔵", "succeeded": "🟢", "failed": "🔴", "retryable": "🟠",
         "pending_review": "🟣", "approved": "✅", "rejected": "❌", "cancelled": "⛔"}
ERRORS = (InvalidTransition, llm_io.SchemaError, PipelinePaused, ffmpeg_studio.FFmpegNotFound,
          ffmpeg_studio.FFmpegError, ValueError, KeyError)


def video_runner(p: Pipeline):
    """Real Clip AI adapter is not wired yet; VIDEO_PROVIDER=mock enables a simulated provider for demos."""
    if os.environ.get("VIDEO_PROVIDER") == "mock":
        return VideoRunner(p, MockVideoProvider(), DATA)
    return None


def image_runner(p: Pipeline):
    """Real Deepix adapter is not wired yet; IMAGE_PROVIDER=mock enables a simulated provider for demos."""
    if os.environ.get("IMAGE_PROVIDER") == "mock":
        return ImageRunner(p, MockImageProvider(), DATA)
    return None


def project_dir(pid: int, *parts: str) -> str:
    path = os.path.join(DATA, str(pid), *parts)
    os.makedirs(path, exist_ok=True)
    return path


def act(fn, success: str = ""):
    """Run an action, show errors instead of crashing, rerun on success."""
    try:
        fn()
    except ERRORS as e:
        st.error(f"{type(e).__name__}: {e}")
        return False
    if success:
        st.toast(success)
    return True


def global_bar(p: Pipeline):
    projects = p.conn.execute("SELECT id, name FROM projects ORDER BY id").fetchall()
    with st.expander("➕ Tạo dự án mới", expanded=not projects):
        name = st.text_input("Tên dự án", key="new_name")
        if st.button("Tạo dự án") and name.strip():
            p.create_project(name.strip())
            st.rerun()
    if not projects:
        st.info("Chưa có dự án. Hãy tạo dự án để bắt đầu.")
        return None
    c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
    ids = [r["id"] for r in projects]
    pid = c1.selectbox("Dự án", ids, format_func=lambda i: next(r["name"] for r in projects if r["id"] == i))
    proj = p.project(pid)
    mode = c2.radio("Chế độ QC", ["auto", "human_qc"], index=0 if proj["operating_mode"] == "auto" else 1,
                    horizontal=True, key=f"mode_{pid}")
    if mode != proj["operating_mode"]:
        p.set_mode(pid, mode)
    th = c3.slider("QC threshold", 0.5, 1.0, float(proj["qc_auto_pass_threshold"]), 0.01, key=f"th_{pid}")
    if abs(th - proj["qc_auto_pass_threshold"]) > 1e-9:
        p.set_threshold(pid, th)
    b1, b2, b3 = c4.columns(3)
    if b1.button("⏸ Pause", disabled=bool(proj["paused"])):
        p.set_paused(pid, True)
        st.rerun()
    if b2.button("▶ Resume", disabled=not proj["paused"]):
        p.set_paused(pid, False)
        st.rerun()
    if b3.button("■ Cancel tất cả"):
        st.toast(f"Đã hủy {p.cancel_all_active(pid)} job")
        st.rerun()
    if proj["paused"]:
        st.warning("Pipeline đang PAUSE — không job nào được bắt đầu.")
    return pid


def step1(p: Pipeline, pid: int):
    st.subheader("① Input kịch bản")
    up = st.file_uploader("script.docx", type=["docx"], key=f"up_{pid}")
    c1, c2 = st.columns(2)
    if c1.button("▶ Chạy phân tích (tách cảnh)", disabled=up is None):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(up.getvalue())
        try:
            scenes = script_parser.parse_docx(f.name)
        finally:
            os.remove(f.name)
        if act(lambda: script_parser.import_scenes(p, pid, scenes), f"Đã tách {len(scenes)} cảnh"):
            st.rerun()
    if c2.button("↺ Reset bước 1 (xóa cảnh + nhân vật chưa khóa)"):
        p.conn.execute("DELETE FROM characters WHERE project_id=? AND locked=0", (pid,))
        p.conn.execute("DELETE FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs)", (pid,))
        p.conn.commit()
        st.rerun()
    scenes = p.conn.execute("SELECT idx, title, state FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    st.caption(f"{len(scenes)} cảnh")
    if scenes:
        st.subheader("② Director — phân tích (Character Bible + thông số cảnh)")
        with st.expander("Prompt gửi Claude (copy)"):
            st.code(prompts.build_director_bundle(p, pid), language="markdown")
        raw = st.text_area("Dán JSON kết quả từ Claude", key=f"analysis_{pid}", height=160)
        if st.button("Lưu phân tích", disabled=not raw.strip()):
            if act(lambda: llm_io.store_scene_analysis(p, pid, raw), "Đã lưu Character Bible + thông số cảnh"):
                st.rerun()
    chars = p.conn.execute("SELECT name, description, wardrobe, locked FROM characters WHERE project_id=?",
                           (pid,)).fetchall()
    if chars:
        st.subheader("Character Bible")
        st.dataframe([dict(c) for c in chars], width="stretch")
        warnings = preflight.check_characters(p.conn, pid, preflight.load_blocklist())
        for w in warnings:
            st.warning(f"⚠ IP rủi ro: **{w['character']}** ~ {w['entry']} ({w['reason']})")
        if st.button("✔ Duyệt & khóa Character Bible → mở Bước 2", type="primary"):
            act(lambda: llm_io.lock_character_bible(p, pid), "Đã khóa Character Bible")
            st.rerun()
    if scenes:
        st.subheader("③ Bảng phân cảnh")
        st.dataframe([dict(s) for s in scenes], width="stretch")


def step2(p: Pipeline, pid: int):
    proj = p.project(pid)
    st.caption(f"Chế độ hiện tại: **{proj['operating_mode']}** — "
               + ("QC Agent tự duyệt theo threshold" if proj["operating_mode"] == "auto"
                  else "mọi ảnh chờ bạn duyệt"))
    c1, c2, c3 = st.columns(3)
    if c1.button("▶ Tạo job gen ảnh (cảnh READY)"):
        rows = p.conn.execute(
            "SELECT id FROM scenes WHERE project_id=? AND state='ready' AND id NOT IN"
            " (SELECT scene_id FROM jobs WHERE type='image_gen' AND state NOT IN ('rejected','cancelled'))",
            (pid,)).fetchall()
        for r in rows:
            p.create_job(r["id"], "image_gen")
        st.toast(f"Đã tạo {len(rows)} job")
        st.rerun()
    if c2.button("✔ Approve tất cả đang chờ duyệt"):
        for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen'"
                                " AND state='pending_review'", (pid,)).fetchall():
            p.approve(j["id"], "user")
        st.rerun()
    if c3.button("↻ Gen lại tất cả FAIL"):
        for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='failed'",
                                (pid,)).fetchall():
            act(lambda: p.retry(j["id"], "retry all"))
        st.rerun()
    runner = image_runner(p)
    if runner is None:
        st.info("Kết nối Deepix chưa bật (đặt IMAGE_PROVIDER khi có adapter): nhập ảnh thủ công cho từng job bên dưới.")
    else:
        st.success(f"Provider ảnh: {runner.provider.name} (giả lập — ảnh 1x1, không phải ảnh thật)")
        r1, r2 = st.columns(2)
        if r1.button("⟳ Submit + Poll 1 lần (ảnh)"):
            submitted = runner.submit_pending(pid)
            st.toast(f"Đã gửi {submitted} · {runner.poll_once(pid)}")
            st.rerun()
        if r2.button("▶ Chạy heartbeat tới khi xong (ảnh)"):
            with st.spinner("Đang gen ảnh…"):
                runner.run(pid, interval=float(os.environ.get("HEARTBEAT_SEC", "90")))
            st.rerun()
    jobs = p.conn.execute(
        "SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    for j in jobs:
        jid, state = j["id"], j["state"]
        with st.container(border=True):
            st.markdown(f"**Cảnh {j['idx']}** — job #{jid} {BADGE.get(state, '')} `{state}` · retry {j['retry_count']}"
                        + (" · ⚠ escalated" if j["escalated"] else ""))
            if j["retry_reason"]:
                st.caption(f"Lý do retry: {j['retry_reason']}")
            img = os.path.join(DATA, str(pid), "images", f"job_{jid}.png")
            if os.path.exists(img):
                st.image(img, width=320)
            qc = p.conn.execute("SELECT criterion, score FROM qc_results WHERE job_id=?", (jid,)).fetchall()
            if qc:
                st.caption("QC: " + " · ".join(f"{q['criterion']} {q['score']:.2f}" for q in qc))
            if state in ("queued", "running"):
                up = st.file_uploader("Nhập ảnh", type=["png", "jpg", "jpeg"], key=f"img_{jid}")
                if up and st.button("Xác nhận ảnh đã có", key=f"ok_{jid}"):
                    with open(os.path.join(project_dir(pid, "images"), f"job_{jid}.png"), "wb") as f:
                        f.write(up.getvalue())

                    def done():
                        if p.state(jid) == JobState.QUEUED:
                            p.start(jid)
                        p.succeed(jid)
                    if act(done):
                        st.rerun()
                if st.button("■ Cancel", key=f"c_{jid}"):
                    act(lambda: p.cancel(jid))
                    st.rerun()
            elif state == "succeeded":
                with st.expander("QC Agent — prompt & kết quả"):
                    st.code(prompts.build_qc_bundle(p, j["scene_id"]), language="markdown")
                    raw = st.text_area("JSON điểm QC từ Claude", key=f"qc_{jid}", height=100)
                    if st.button("Chấm điểm", key=f"score_{jid}", disabled=not raw.strip()):
                        def score():
                            obj = llm_io.validate_qc_result(raw, prompts.qc_criteria())
                            st.toast(f"Quyết định: {p.apply_qc(jid, obj['criteria'])}")
                        if act(score):
                            st.rerun()
            if state in ("succeeded", "pending_review"):
                note = st.text_input("Ghi chú reject (đưa vào prompt gen lại)", key=f"note_{jid}")
                a, b = st.columns(2)
                if a.button("✔ Approve", key=f"a_{jid}"):
                    act(lambda: p.approve(jid, "user"))
                    st.rerun()
                if b.button("✖ Reject & Gen lại", key=f"r_{jid}"):
                    act(lambda: p.reject(jid, "user", note or None))
                    st.rerun()
            if state == "failed":
                if st.button("↻ Retry", key=f"retry_{jid}"):
                    act(lambda: p.retry(jid, "retry"))
                    st.rerun()


def step3(p: Pipeline, pid: int):
    approved = p.conn.execute(
        "SELECT s.idx FROM scenes s WHERE s.project_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE j.scene_id=s.id"
        " AND j.type='image_gen' AND j.state='approved') ORDER BY s.idx", (pid,)).fetchall()
    st.caption(f"{len(approved)} cảnh đã có ảnh được duyệt")
    st.code(open(os.path.join("prompts", "03_video_motion.md"), encoding="utf-8").read(), language="markdown")
    raw = st.text_area("Dán JSON motion prompts từ Claude", key=f"motion_{pid}", height=140)
    if st.button("▶ Lưu motion prompts", disabled=not raw.strip()):
        if act(lambda: llm_io.store_motion_prompts(p, pid, raw), "Đã lưu"):
            st.rerun()
    rows = p.conn.execute(
        "SELECT s.id sid, s.idx, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    if st.button("✔ Duyệt tất cả", disabled=not rows):
        for r in rows:
            llm_io.approve_motion_prompt(p, r["sid"])
        st.rerun()
    for r in rows:
        with st.container(border=True):
            st.markdown(f"**Cảnh {r['idx']}** — `{r['state']}` · {r['duration_sec']}s")
            new = st.text_area("Motion prompt", r["motion_prompt"], key=f"mp_{r['sid']}", height=70)
            a, b = st.columns(2)
            if a.button("Lưu chỉnh sửa", key=f"mps_{r['sid']}"):
                act(lambda: llm_io.store_motion_prompts(
                    p, pid, {"scenes": [{"idx": r["idx"], "motion_prompt": new, "camera": r["camera"],
                                         "duration_sec": r["duration_sec"],
                                         "negative_prompt": r["negative_prompt"]}]}))
                st.rerun()
            if b.button("✔ Duyệt", key=f"mpa_{r['sid']}", disabled=r["state"] == "approved"):
                act(lambda: llm_io.approve_motion_prompt(p, r["sid"]))
                st.rerun()


def step4(p: Pipeline, pid: int):
    ready = llm_io.ready_for_video(p, pid)
    runner = video_runner(p)
    st.caption(f"{len(ready)} cảnh sẵn sàng gen video (ảnh + motion prompt đã duyệt)")
    if runner is None:
        st.info("Kết nối Clip AI/Kling chưa bật (đặt VIDEO_PROVIDER khi có adapter). "
                "Vẫn có thể tạo job xếp hàng để theo dõi state machine.")
    else:
        st.success(f"Provider: {runner.provider.name} (giả lập — không tạo video thật)")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("▶ Tạo job gen video", disabled=not ready):
        for r in ready:
            exists = p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen'"
                                    " AND state NOT IN ('cancelled','rejected')", (r["scene_id"],)).fetchone()
            if not exists:
                p.create_job(r["scene_id"], "video_gen")
        st.rerun()
    if c2.button("⟳ Submit + Poll 1 lần", disabled=runner is None):
        submitted = runner.submit_pending(pid)
        st.toast(f"Đã gửi {submitted} · {runner.poll_once(pid)}")
        st.rerun()
    if c3.button("▶ Chạy heartbeat tới khi xong", disabled=runner is None):
        with st.spinner("Đang chạy heartbeat…"):
            runner.run(pid, interval=float(os.environ.get("HEARTBEAT_SEC", "90")))
        st.rerun()
    if c4.button("↻ Retry tất cả job fail"):
        for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='failed'"
                                " AND escalated=0", (pid,)).fetchall():
            act(lambda: p.retry(j["id"], "retry all"))
        st.rerun()
    jobs = p.conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id"
                          " WHERE j.project_id=? AND j.type='video_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    done = sum(1 for j in jobs if j["state"] == "succeeded")
    if jobs:
        st.progress(done / len(jobs), text=f"{done} / {len(jobs)} hoàn thành")
    fails = p.conn.execute("SELECT job_id, error_message FROM content_moderation_failures f JOIN jobs j"
                           " ON j.id=f.job_id WHERE j.project_id=?", (pid,)).fetchall()
    for f in fails:
        st.warning(f"Risk control (job #{f['job_id']}): {f['error_message']}")
    for j in jobs:
        a, b, c = st.columns([3, 1, 1])
        a.markdown(f"Cảnh {j['idx']} — job #{j['id']} {BADGE.get(j['state'], '')} `{j['state']}` · retry {j['retry_count']}"
                   + (" · ⚠ escalated" if j["escalated"] else ""))
        if j["state"] in ("queued", "running") and b.button("■ Cancel", key=f"vc_{j['id']}"):
            act(lambda: runner.cancel_job(j["id"]) if runner else p.cancel(j["id"]))
            st.rerun()
        if j["state"] == "failed" and not j["escalated"] and c.button("↻ Retry", key=f"vr_{j['id']}"):
            act(lambda: p.retry(j["id"], "retry"))
            st.rerun()


def step5a(p: Pipeline, pid: int):
    st.caption("Music Brief → 3 bản nháp cần nhà cung cấp nhạc (chưa chọn). Hiện hỗ trợ upload nhạc có sẵn.")
    st.code(open(os.path.join("prompts", "04_music_brief.md"), encoding="utf-8").read(), language="markdown")
    up = st.file_uploader("Upload nhạc nền", type=["mp3", "wav", "m4a"], key=f"music_{pid}")
    if up and st.button("Dùng bản này"):
        with open(os.path.join(project_dir(pid, "music"), "selected" + os.path.splitext(up.name)[1]), "wb") as f:
            f.write(up.getvalue())
        st.rerun()
    if st.button("Không dùng nhạc"):
        for name in os.listdir(project_dir(pid, "music")):
            os.remove(os.path.join(project_dir(pid, "music"), name))
        st.rerun()
    files = os.listdir(project_dir(pid, "music"))
    st.write("Nhạc đang chọn:", files[0] if files else "không dùng")


def step5b(p: Pipeline, pid: int):
    vdir = project_dir(pid, "videos")
    up = st.file_uploader("Nhập clip video (.mp4) — tên file theo thứ tự cảnh, vd 01.mp4",
                          type=["mp4"], accept_multiple_files=True, key=f"vid_{pid}")
    if up and st.button("Lưu clip"):
        for f in up:
            with open(os.path.join(vdir, f.name), "wb") as out:
                out.write(f.getvalue())
        st.rerun()
    clips = sorted(f for f in os.listdir(vdir) if f.lower().endswith(".mp4"))
    st.write("Clip theo thứ tự:", clips or "chưa có")
    transition = st.radio("Transition", ["cut", "crossfade"], horizontal=True)
    durations = None
    if transition == "crossfade" or os.listdir(project_dir(pid, "music")):
        durations = [st.number_input(f"Độ dài {c} (giây)", 2.0, 60.0, 5.0, key=f"d_{c}") for c in clips]
    if st.button("▶ Render Final", disabled=not clips, type="primary"):
        music_dir = project_dir(pid, "music")
        music = os.path.join(music_dir, os.listdir(music_dir)[0]) if os.listdir(music_dir) else None
        out = os.path.join(project_dir(pid, "output"), "FINAL_VIDEO.mp4")
        if act(lambda: ffmpeg_studio.render_final([os.path.join(vdir, c) for c in clips], out, durations,
                                                  transition, music=music), "Render xong"):
            st.video(out)


def history(p: Pipeline, pid: int):
    scenes = p.conn.execute("SELECT id, idx, title FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    if not scenes:
        st.caption("Chưa có cảnh.")
        return
    sid = st.selectbox("Cảnh", [s["id"] for s in scenes],
                       format_func=lambda i: next(f"{s['idx']} · {s['title']}" for s in scenes if s["id"] == i))
    for j in p.conn.execute("SELECT * FROM jobs WHERE scene_id=? ORDER BY id", (sid,)).fetchall():
        with st.expander(f"job #{j['id']} {j['type']} — {j['state']} (retry {j['retry_count']})"):
            img = os.path.join(DATA, str(pid), "images", f"job_{j['id']}.png")
            if os.path.exists(img):
                st.image(img, width=240)
            st.dataframe([dict(h) for h in p.history(j["id"])], width="stretch")


def main():
    st.set_page_config(layout="wide", page_title="AI Video Pipeline")
    st.title("AI Video Pipeline")
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    p = Pipeline(connect(DB))
    pid = global_bar(p)
    if pid is None:
        return
    step = st.radio("Bước", STEPS, horizontal=True, key="step", label_visibility="collapsed")
    st.divider()
    {STEPS[0]: step1, STEPS[1]: step2, STEPS[2]: step3, STEPS[3]: step4, STEPS[4]: step5a,
     STEPS[5]: step5b, STEPS[6]: history}[step](p, pid)


main()
