"""Unified control dashboard (V1): one tool, stepper by step order, per-step control buttons.

Run:  py -m streamlit run dashboard/app.py
Layout and colors follow mockup/dashboard.html (see dashboard/ui.py).
Claude steps (Director / QC / motion prompt) use copy-paste JSON until the API runner is wired in.
"""
import json
import os
import shutil
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import audio_lib, cost, ffmpeg_studio, final_cut, llm_io, music, preflight, prompts, script_parser  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline, PipelinePaused  # noqa: E402
from core.adapters import factory  # noqa: E402
from core.providers import ProviderError  # noqa: E402
from core.runner import ImageRunner, VideoRunner  # noqa: E402
from core.states import InvalidTransition, JobState  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
import ui  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))
DATA = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))
STEPS = ["1 · Kịch bản & phân tích", "2 · Gen ảnh + QC", "3 · Video Prompt", "4 · Gen video",
         "5a · Nhạc nền", "5b · Ghép & Render", "Lịch sử"]
ERRORS = (InvalidTransition, llm_io.SchemaError, PipelinePaused, ffmpeg_studio.FFmpegNotFound,
          ffmpeg_studio.FFmpegError, ValueError, KeyError)
CRITERIA_LABEL = {"character": "Đúng nhân vật", "hands_face": "Không lỗi tay/mặt", "composition": "Đúng bố cục",
                  "mood_lighting": "Đúng mood / ánh sáng", "consistency": "Không chi tiết thừa/sai"}
FILTERS = {"all": "Tất cả", "review": "Chờ duyệt", "pass": "Đã duyệt", "fail": "FAIL", "run": "Đang chạy"}
FILTER_STATES = {"review": ("succeeded", "pending_review"), "pass": ("approved",), "fail": ("failed", "rejected"),
                 "run": ("queued", "running")}


# ---- providers / cost helpers ---------------------------------------------------------
def video_runner(p: Pipeline):
    """Provider chosen by VIDEO_PROVIDER (clipai | mock); None when not configured."""
    try:
        provider = factory.video_provider()
    except ProviderError as e:
        st.error(f"Clip AI: {e}")
        return None
    return VideoRunner(p, provider, DATA) if provider else None


def image_runner(p: Pipeline):
    """Provider chosen by IMAGE_PROVIDER (deepix | mock); None when not configured."""
    try:
        provider = factory.image_provider()
    except ProviderError as e:
        st.error(f"Deepix: {e}")
        return None
    return ImageRunner(p, provider, DATA) if provider else None


def image_estimate(p: Pipeline, pid: int):
    from core.adapters.deepix import DEFAULT_MODEL
    return cost.estimate_images(p, pid, cost.load_pricing(), os.environ.get("DEEPIX_MODEL", DEFAULT_MODEL))


def video_estimate(p: Pipeline, pid: int):
    from core.adapters.clipai import effective_duration, resolve_model
    try:
        canonical, family = resolve_model(p.project(pid)["video_model"])
    except ProviderError:
        return None
    tier = os.environ.get("CLIPAI_KLING_MODE", "pro") if family == "omni" else os.environ.get("CLIPAI_RESOLUTION", "720p")
    return cost.estimate_videos(p, pid, cost.load_pricing(), canonical, tier,
                                lambda seconds: effective_duration(canonical, family, seconds))


def show_estimate(est, runner) -> bool:
    """Show the estimate; for real providers require a confirmation tick on large batches. Returns 'allowed'."""
    if est is None:
        return True
    if est["items"] == 0:
        return True
    st.info("Ước tính chi phí: " + cost.format_estimate(est))
    if runner is None or runner.provider.name.startswith("mock"):
        return True
    if est["items"] >= cost.load_pricing()["confirm_batch_at"]:
        return st.checkbox(f"Tôi xác nhận batch {est['items']} mục này sẽ tốn credit", key=f"confirm_{est['kind']}")
    return True


def spend_line(p: Pipeline, pid: int) -> None:
    spend = cost.spend_summary(p.conn, pid, cost.load_pricing())
    if not (spend["images"] or spend["clips"] or spend["audios"]):
        return
    text = (f"Đã ghi nhận (gửi API thật): {spend['images']} ảnh · {spend['clips']} clip ({spend['seconds']:.0f} giây)"
            f" · {spend['audios']} âm thanh")
    if spend["unknown_prices"]:
        text += " — chưa có giá cho: " + ", ".join(spend["unknown_prices"]) + " (điền data/pricing.json)"
    else:
        text += f" → khoảng {spend['credits']:.1f} {spend['currency']} theo giá khai báo"
    st.caption(text)


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


def job_image(pid: int, jid: int):
    path = os.path.join(DATA, str(pid), "images", f"job_{jid}.png")
    return path if os.path.exists(path) else None


def qc_scores(p: Pipeline, jid: int):
    return p.conn.execute("SELECT criterion, score, threshold_at_time FROM qc_results WHERE job_id=? ORDER BY id",
                          (jid,)).fetchall()


# ---- step completion (stepper checkmarks) ----------------------------------------------
def step_done(p: Pipeline, pid: int) -> list:
    q = lambda sql, *a: p.conn.execute(sql, a).fetchone()[0]  # noqa: E731
    scenes = q("SELECT COUNT(*) FROM scenes WHERE project_id=?", pid)
    approved_imgs = q("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='image_gen'"
                      " AND state='approved'", pid)
    motion = q("SELECT COUNT(*) FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?"
               " AND m.state='approved'", pid)
    videos = q("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='video_gen'"
               " AND state='succeeded'", pid)
    drafts_dir, selected_dir = music.project_dirs(DATA, pid)
    return [bool(q("SELECT COUNT(*) FROM characters WHERE project_id=? AND locked=1", pid)),
            bool(scenes) and approved_imgs >= scenes, bool(scenes) and motion >= scenes,
            bool(scenes) and videos >= scenes, bool(os.listdir(selected_dir)),
            os.path.exists(os.path.join(DATA, str(pid), "output", "FINAL_VIDEO.mp4")), False]


def step_label(done: list):
    marks = {name: ("✓  " if done[i] else "") + name for i, name in enumerate(STEPS)}
    return lambda name: marks[name]


# ---- header --------------------------------------------------------------------------
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
    with st.container(border=True):
        c0, c1, c2, c3, c4 = st.columns([1.5, 2, 2.3, 2, 3], vertical_alignment="center")
        c0.markdown('<div class="brand"><i></i>AI Video Pipeline</div>', unsafe_allow_html=True)
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
        if b1.button("⏸ Pause", disabled=bool(proj["paused"]), key="btn_pause"):
            p.set_paused(pid, True)
            st.rerun()
        if b2.button("▶ Resume", disabled=not proj["paused"], key="btn_resume"):
            p.set_paused(pid, False)
            st.rerun()
        if b3.button("■ Cancel", key="btn_cancel"):
            st.toast(f"Đã hủy {p.cancel_all_active(pid)} job")
            st.rerun()
    if proj["paused"]:
        st.warning("Pipeline đang PAUSE — không job nào được bắt đầu.")
    spend_line(p, pid)
    return pid


# ---- step 1 --------------------------------------------------------------------------
def step1(p: Pipeline, pid: int):
    scenes = p.conn.execute("SELECT idx, title, state, data FROM scenes WHERE project_id=? ORDER BY idx",
                            (pid,)).fetchall()
    chars = p.conn.execute("SELECT name, description, wardrobe, locked FROM characters WHERE project_id=?",
                           (pid,)).fetchall()
    warnings = preflight.check_characters(p.conn, pid, preflight.load_blocklist()) if chars else []
    risky = {w["character"] for w in warnings}
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        with st.container(border=True):
            ui.html(ui.card_title("① Input kịch bản"))
            up = st.file_uploader("script.docx", type=["docx"], key=f"up_{pid}")
            c1, c2 = st.columns(2)
            if c1.button("▶ Chạy phân tích (tách cảnh)", disabled=up is None, type="primary"):
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                    f.write(up.getvalue())
                try:
                    parsed = script_parser.parse_docx(f.name)
                finally:
                    os.remove(f.name)
                if act(lambda: script_parser.import_scenes(p, pid, parsed), f"Đã tách {len(parsed)} cảnh"):
                    st.rerun()
            if c2.button("↺ Reset bước 1", help="Xóa cảnh + nhân vật chưa khóa", key="btn_bad_reset"):
                p.conn.execute("DELETE FROM characters WHERE project_id=? AND locked=0", (pid,))
                p.conn.execute("DELETE FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs)", (pid,))
                p.conn.commit()
                st.rerun()
            if scenes:
                ui.html(ui.badge("succeeded", "b-ok") + f' <span class="muted">Đã tách {len(scenes)} cảnh · '
                        f'{len(chars)} nhân vật</span>')
        for w in warnings:
            ui.html(f'<div class="note-warn"><b>⚠ Pre-flight IP / Content check</b><br>{ui.badge("Rủi ro", "b-bad")} '
                    f'<b>{w["character"]}</b> ~ {w["entry"]} ({w["reason"]})</div>')
        if scenes:
            with st.container(border=True):
                ui.html(ui.card_title("② Director — phân tích", "Character Bible + thông số cảnh"))
                with st.expander("Prompt gửi Claude (copy)"):
                    st.code(prompts.build_director_bundle(p, pid), language="markdown")
                raw = st.text_area("Dán JSON kết quả từ Claude", key=f"analysis_{pid}", height=140)
                if st.button("Lưu phân tích", disabled=not raw.strip()):
                    if act(lambda: llm_io.store_scene_analysis(p, pid, raw), "Đã lưu Character Bible + thông số cảnh"):
                        st.rerun()
    with right:
        if chars:
            with st.container(border=True):
                ui.html(ui.card_title("Character Bible", f"{len(chars)} nhân vật"))
                for c in chars:
                    desc = c["description"] + (f" · {c['wardrobe']}" if c["wardrobe"] else "")
                    tag = (ui.badge("IP rủi ro", "b-bad") if c["name"] in risky else ui.badge("IP an toàn", "b-ok"))
                    if c["locked"]:
                        tag += " " + ui.badge("đã khóa", "b-pri")
                    ui.html(ui.item(c["name"], desc, tag))
                    if not c["locked"]:
                        with st.expander(f"Sửa {c['name']}"):
                            n_name = st.text_input("Tên", c["name"], key=f"cn_{pid}_{c['name']}")
                            n_desc = st.text_area("Mô tả", c["description"], key=f"cd_{pid}_{c['name']}", height=80)
                            n_ward = st.text_input("Trang phục / dấu hiệu", c["wardrobe"] or "", key=f"cw_{pid}_{c['name']}")
                            if st.button("Lưu", key=f"cs_{pid}_{c['name']}"):
                                if act(lambda: llm_io.update_character(p, pid, c["name"], n_desc, n_ward, n_name),
                                       f"Đã lưu {n_name}"):
                                    st.rerun()
                if any(c["locked"] for c in chars):
                    st.caption("Character Bible đang khóa. Muốn sửa phải mở khóa (ảnh đã gen vẫn theo mô tả cũ).")
                    if st.button("🔓 Mở khóa để sửa", key="btn_bad_unlock"):
                        act(lambda: llm_io.unlock_character_bible(p, pid), "Đã mở khóa Character Bible")
                        st.rerun()
        if scenes:
            with st.container(border=True):
                ui.html(ui.card_title("③ Bảng phân cảnh", f"{len(scenes)} cảnh"))
                rows = []
                for s in scenes:
                    d = json.loads(s["data"] or "{}")
                    rows.append({"Cảnh": f"S{s['idx']:02d}", "Bối cảnh": " · ".join(filter(None, [d.get("time"), d.get("location")])),
                                 "Nhân vật": ", ".join(d.get("characters") or []),
                                 "Ống kính / mood": " · ".join(filter(None, [d.get("shot"), d.get("mood")])),
                                 "Trạng thái": s["state"]})
                st.dataframe(rows, width="stretch", hide_index=True)
        if chars:
            with st.container(border=True):
                a, b = st.columns([2, 1], vertical_alignment="center")
                a.caption("Cần Approve & Lock để mở Bước 2")
                if b.button("✔ Duyệt & khóa → Bước 2", type="primary"):
                    act(lambda: llm_io.lock_character_bible(p, pid), "Đã khóa Character Bible")
                    st.rerun()


# ---- step 2 --------------------------------------------------------------------------
def step2(p: Pipeline, pid: int):
    proj = p.project(pid)
    runner = image_runner(p)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.2, 2, 2, 3], vertical_alignment="center")
        if c1.button("▶ Tạo job gen ảnh (cảnh READY)", type="primary"):
            rows = p.conn.execute(
                "SELECT id FROM scenes WHERE project_id=? AND state='ready' AND id NOT IN"
                " (SELECT scene_id FROM jobs WHERE type='image_gen' AND state NOT IN ('rejected','cancelled'))",
                (pid,)).fetchall()
            for r in rows:
                p.create_job(r["id"], "image_gen")
            st.toast(f"Đã tạo {len(rows)} job")
            st.rerun()
        if c2.button("✔ Approve tất cả đang chờ duyệt", key="approve_all"):
            for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen'"
                                    " AND state='pending_review'", (pid,)).fetchall():
                p.approve(j["id"], "user")
            st.rerun()
        if c3.button("↻ Gen lại tất cả FAIL", key="reject_all"):
            for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='failed'",
                                    (pid,)).fetchall():
                act(lambda: p.retry(j["id"], "retry all"))
            st.rerun()
        c4.markdown(ui.badge(f"Chế độ: {proj['operating_mode']} — "
                             + ("QC Agent tự duyệt theo threshold" if proj["operating_mode"] == "auto"
                                else "mọi ảnh chờ bạn duyệt"), "b-pri")
                    + f' <span class="muted">Retry tối đa {proj["max_retry_count"]}</span>', unsafe_allow_html=True)
    if proj["operating_mode"] == "auto":
        z1, z2, _ = st.columns([2, 3, 3], vertical_alignment="center")
        zone_on = z1.checkbox("Vùng chờ review", proj["qc_review_floor"] is not None, key=f"zone_{pid}",
                              help="Điểm nằm giữa mức sàn và threshold: QC Agent không tự loại mà chờ bạn duyệt.")
        floor = z2.slider("Mức sàn (dưới mức này tự loại)", 0.3, float(proj["qc_auto_pass_threshold"]),
                          min(float(proj["qc_review_floor"] or 0.6), float(proj["qc_auto_pass_threshold"])), 0.01,
                          key=f"floor_{pid}", disabled=not zone_on)
        new_floor = floor if zone_on else None
        if new_floor != proj["qc_review_floor"] and (new_floor is None or proj["qc_review_floor"] is None
                                                     or abs(new_floor - proj["qc_review_floor"]) > 1e-9):
            p.set_review_floor(pid, new_floor)
    if runner is None:
        st.info("Chưa cấu hình Deepix: đặt IMAGE_PROVIDER=deepix và DEEPIX_TOKEN (biến môi trường), hoặc nhập ảnh thủ công cho từng job.")
    else:
        st.success(f"Provider ảnh: {runner.provider.name}" + (" (giả lập — ảnh 1x1)" if runner.provider.name == "mock-image" else " (gọi API thật, tốn credit)"))
        allowed = show_estimate(image_estimate(p, pid), runner)
        r1, r2, _ = st.columns([2, 2, 4])
        if r1.button("⟳ Submit + Poll 1 lần (ảnh)", disabled=not allowed):
            submitted = runner.submit_pending(pid)
            st.toast(f"Đã gửi {submitted} · {runner.poll_once(pid)}")
            st.rerun()
        if r2.button("▶ Chạy heartbeat tới khi xong (ảnh)", disabled=not allowed):
            with st.spinner("Đang gen ảnh…"):
                runner.run(pid, interval=float(os.environ.get("HEARTBEAT_SEC", "90")))
            st.rerun()

    jobs = p.conn.execute(
        "SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    counts = {k: sum(1 for j in jobs if j["state"] in v) for k, v in FILTER_STATES.items()}
    counts["all"] = len(jobs)
    flt = st.radio("Lọc", list(FILTERS), horizontal=True, key=f"filter_{pid}", label_visibility="collapsed",
                   format_func=lambda k: f"{FILTERS[k]} {counts[k]}")
    shown = [j for j in jobs if flt == "all" or j["state"] in FILTER_STATES[flt]]
    if not jobs:
        st.caption("Chưa có job gen ảnh. Duyệt Character Bible ở Bước 1 rồi bấm ‘Tạo job gen ảnh’.")
        return
    sel_key = f"sel_{pid}"
    if st.session_state.get(sel_key) not in {j["id"] for j in jobs}:
        st.session_state[sel_key] = shown[0]["id"] if shown else jobs[0]["id"]
    grid, detail = st.columns([3, 1.15], gap="large")
    with grid:
        per_row = 3
        for start in range(0, len(shown), per_row):
            cols = st.columns(per_row)
            for col, j in zip(cols, shown[start:start + per_row]):
                with col:
                    image_card(p, pid, j, proj)
        if not shown:
            st.caption("Không có ảnh nào trong bộ lọc này.")
    with detail:
        job = next(j for j in jobs if j["id"] == st.session_state[sel_key])
        image_detail(p, pid, job, proj)


def image_card(p: Pipeline, pid: int, j, proj):
    jid, state = j["id"], j["state"]
    scores = qc_scores(p, jid)
    with st.container(border=True):
        img = job_image(pid, jid)
        if img:
            st.image(img, width="stretch")
        else:
            ui.html('<div style="height:120px;border-radius:8px;background:var(--bg);display:grid;place-items:center;'
                    f'color:var(--muted)">{"⏳ đang gen…" if state == "running" else "chưa có ảnh"}</div>')
        flag = " " + ui.badge("⚠ escalated", "b-warn") if j["escalated"] else ""
        ui.html(f'<div class="cardhead"><b>S{j["idx"]:02d}</b><span class="grow"></span>{ui.state_badge(state)}{flag}</div>')
        if scores:
            mean = sum(s["score"] for s in scores) / len(scores)
            ui.html(ui.qc_bar(mean, proj["qc_auto_pass_threshold"]))
        if state in ("succeeded", "pending_review"):
            a, b, c = st.columns(3)
            if a.button("✔", key=f"a_{jid}", help="Approve"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if b.button("✖", key=f"r_{jid}", help="Reject & gen lại (dùng ghi chú ở panel chi tiết)"):
                act(lambda: p.reject(jid, "user", st.session_state.get(f"note_{jid}") or None))
                st.rerun()
            if c.button("🔍", key=f"sel_btn_{jid}", help="Xem chi tiết"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state in ("queued", "running"):
            a, b = st.columns(2)
            if b.button("■", key=f"c_{jid}", help="Cancel"):
                act(lambda: p.cancel(jid))
                st.rerun()
            if a.button("🔍", key=f"sel_btn_{jid}", help="Chi tiết / nhập ảnh thủ công"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state == "failed":
            a, b = st.columns(2)
            if a.button("↻", key=f"retry_{jid}", help="Retry"):
                act(lambda: p.retry(jid, "retry"))
                st.rerun()
            if b.button("🔍", key=f"sel_btn_{jid}", help="Chi tiết"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        else:
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()


def image_detail(p: Pipeline, pid: int, j, proj):
    jid, state = j["id"], j["state"]
    with st.container(border=True):
        ui.html(ui.card_title(f"Chi tiết ảnh S{j['idx']:02d}", f"job #{jid} · retry {j['retry_count']}"))
        ui.html(ui.state_badge(state))
        if j["retry_reason"]:
            st.caption(f"Lý do retry: {j['retry_reason']}")
        img = job_image(pid, jid)
        if img:
            st.image(img, width="stretch")
        scores = qc_scores(p, jid)
        if scores:
            ui.html('<div class="muted" style="font-weight:600;margin-top:8px">QC checklist (Claude Vision)</div>')
            for s in scores:
                ui.html(f'<div class="crit"><span>{CRITERIA_LABEL.get(s["criterion"], s["criterion"])}</span>'
                        f'<b style="color:{ui.score_color(s["score"], proj["qc_auto_pass_threshold"])}">{s["score"]:.2f}</b></div>')
        if state in ("queued", "running"):
            up = st.file_uploader("Nhập ảnh thủ công", type=["png", "jpg", "jpeg"], key=f"img_{jid}")
            if up and st.button("Xác nhận ảnh đã có", key=f"ok_{jid}"):
                with open(os.path.join(project_dir(pid, "images"), f"job_{jid}.png"), "wb") as f:
                    f.write(up.getvalue())

                def done():
                    if p.state(jid) == JobState.QUEUED:
                        p.start(jid)
                    p.succeed(jid)
                if act(done):
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
            if b.button("✖ Reject & Gen lại", key=f"dr_{jid}"):
                act(lambda: p.reject(jid, "user", note or None))
                st.rerun()
            if a.button("✔ Approve", key=f"da_{jid}", type="primary"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
        if state == "failed" and st.button("↻ Retry", key=f"dretry_{jid}"):
            act(lambda: p.retry(jid, "retry"))
            st.rerun()


# ---- step 3 --------------------------------------------------------------------------
def step3(p: Pipeline, pid: int):
    approved = p.conn.execute(
        "SELECT s.idx FROM scenes s WHERE s.project_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE j.scene_id=s.id"
        " AND j.type='image_gen' AND j.state='approved') ORDER BY s.idx", (pid,)).fetchall()
    rows = p.conn.execute(
        "SELECT s.id sid, s.idx, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    with st.container(border=True):
        a, b = st.columns([3, 1], vertical_alignment="center")
        a.markdown(ui.badge(f"{len(approved)} cảnh đã có ảnh được duyệt", "b-info") +
                   ' <span class="muted">Knowledge Base · image-to-video</span>', unsafe_allow_html=True)
        if b.button("✔ Duyệt tất cả", disabled=not rows, key="btn_ok_all"):
            for r in rows:
                llm_io.approve_motion_prompt(p, r["sid"])
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
                ui.html(f'<b>S{r["idx"]:02d}</b>')
                path = job_image(pid, img_job["id"]) if img_job else None
                if path:
                    st.image(path, width=96)
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
            st.divider()


# ---- step 4 --------------------------------------------------------------------------
def step4(p: Pipeline, pid: int):
    ready = llm_io.ready_for_video(p, pid)
    runner = video_runner(p)
    models = ["(mặc định: kling-v3-omni)", "kling", "kling-o1", "seedance", "seedance-fast", "seedance-2.5"]
    current = p.project(pid)["video_model"]
    with st.container(border=True):
        m1, m2 = st.columns([3, 2], vertical_alignment="center")
        m1.markdown(ui.badge(f"{len(ready)} cảnh sẵn sàng gen video", "b-info") +
                    ' <span class="muted">ảnh + motion prompt đã duyệt</span>', unsafe_allow_html=True)
        choice = m2.selectbox("Model video (Kling Omni / Seedance; bộ lọc kiểm duyệt khác nhau theo model)", models,
                              index=models.index(current) if current in models else 0, key=f"vmodel_{pid}")
        if (choice if choice in models[1:] else None) != current:
            p.set_video_model(pid, choice if choice in models[1:] else None)
        if runner is None:
            st.info("Chưa cấu hình Clip AI: đặt VIDEO_PROVIDER=clipai và CLIPAI_TOKEN (biến môi trường). "
                    "Vẫn có thể tạo job xếp hàng để theo dõi state machine.")
        else:
            st.success(f"Provider video: {runner.provider.name}" + (" (giả lập — không tạo video thật)" if runner.provider.name == "mock" else " (gọi API thật, tốn credit)"))
        allowed = show_estimate(video_estimate(p, pid), runner)
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
                          " WHERE j.project_id=? AND j.type='video_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    done = sum(1 for j in jobs if j["state"] == "succeeded")
    running = sum(1 for j in jobs if j["state"] == "running")
    failed = sum(1 for j in jobs if j["state"] == "failed")
    with st.container(border=True):
        ui.html(ui.card_title("Tiến độ batch", "Clip AI"))
        extra = (ui.badge(f"{running} running", "b-info") if running else "") + " " + \
                (ui.badge(f"{failed} failed", "b-bad") if failed else "")
        ui.html(ui.progress(done, len(jobs), extra))
    fails = p.conn.execute("SELECT job_id, error_message FROM content_moderation_failures f JOIN jobs j"
                           " ON j.id=f.job_id WHERE j.project_id=?", (pid,)).fetchall()
    for f in fails:
        ui.html(f'<div class="note-warn"><b>⚠ Risk control</b> (job #{f["job_id"]}): {f["error_message"]}</div>')
    with st.container(border=True):
        ui.html(ui.card_title("Danh sách job", f"{len(jobs)} job"))
        for j in jobs:
            a, b, c, d = st.columns([1, 2, 1, 2], vertical_alignment="center")
            a.markdown(f"**S{j['idx']:02d}**")
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
                if j["state"] == "succeeded" and j["result_path"] and os.path.exists(j["result_path"]) \
                        and st.checkbox("▶ Xem", key=f"vsee_{j['id']}"):
                    st.video(j["result_path"])


# ---- step 5a -------------------------------------------------------------------------
def step5a(p: Pipeline, pid: int):
    drafts_dir, selected_dir = music.project_dirs(DATA, pid)
    try:
        provider = music.audio_provider()
    except ProviderError as e:
        st.error(f"Clip AI audio: {e}")
        provider = None
    with st.container(border=True):
        if provider is None:
            st.info("Chưa cấu hình tạo nhạc: đặt AUDIO_PROVIDER=clipai (hoặc VIDEO_PROVIDER=clipai) và CLIPAI_TOKEN, "
                    "hoặc upload nhạc có sẵn bên dưới.")
        else:
            ui.html(ui.card_title("Music Brief", "gợi ý từ mood các cảnh — bạn sửa được") + ui.badge(
                provider.name + (" · giả lập" if provider.name == "mock-audio" else " · music_v2 · tốn credit"), "b-info"))
            brief = music.default_brief(p, pid)
            prompt = st.text_area("Prompt nhạc (≤ 2000 ký tự)", brief["prompt"], key=f"mprompt_{pid}", height=100)
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
                    st.audio(os.path.join(drafts_dir, d["file"]))
                    if st.button("Chọn bản này", key=f"pick_{pid}_{i}", type="primary"):
                        if act(lambda: music.select_draft(drafts_dir, selected_dir, i), "Đã chọn nhạc nền"):
                            st.rerun()
                else:
                    ui.html('<div class="wave"></div><span class="muted">đang tạo… bấm ‘Kiểm tra + tải về’</span>')
    if drafts and st.button("Xóa danh sách bản nháp"):
        shutil.rmtree(drafts_dir, ignore_errors=True)
        st.rerun()
    with st.container(border=True):
        files = os.listdir(selected_dir)
        ui.html(ui.card_title("Nhạc nền đang chọn") + (ui.badge(files[0], "b-ok") if files else ui.badge("không dùng")))
        if files:
            st.audio(os.path.join(selected_dir, files[0]))
        with st.expander("Hoặc upload nhạc có sẵn"):
            up = st.file_uploader("Upload nhạc nền", type=["mp3", "wav", "m4a"], key=f"music_{pid}")
            if up and st.button("Dùng bản này"):
                music.clear_selected(selected_dir)
                with open(os.path.join(selected_dir, "selected" + os.path.splitext(up.name)[1]), "wb") as f:
                    f.write(up.getvalue())
                st.rerun()
        if st.button("Không dùng nhạc"):
            music.clear_selected(selected_dir)
            st.rerun()
    extras_section(p, pid, provider)


def extras_section(p: Pipeline, pid: int, provider):
    """Sound effects and voice-over: generate, preview, and choose what goes into the final mix."""
    directory = audio_lib.assets_dir(DATA, pid)
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
def _probe(path: str, mtime: float, requested):
    return final_cut.clip_seconds(path, requested)


def step5b(p: Pipeline, pid: int):
    vdir = project_dir(pid, "videos")
    clips = final_cut.collect_clips(p, DATA, pid)
    present = [c for c in clips if c["path"]]
    missing = [c for c in clips if not c["path"]]
    left, right = st.columns([1.7, 1], gap="large")
    chosen, durations = [], []
    out = os.path.join(project_dir(pid, "output"), "FINAL_VIDEO.mp4")
    with left:
        with st.container(border=True):
            ui.html(ui.card_title("Clip theo thứ tự cảnh", f"{len(present)} có sẵn / {len(clips)} mục · lấy tự động từ Bước 4"))
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
                    st.video(c["path"])
                if use:
                    chosen.append(c["path"])
                    durations.append(sec)
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
                st.video(out)
                with open(out, "rb") as f:
                    st.download_button("⬇ Tải FINAL_VIDEO.mp4", f, file_name="FINAL_VIDEO.mp4", mime="video/mp4")
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
        extras = audio_lib.mix_list(audio_lib.assets_dir(DATA, pid))
        st.caption(f"Hiệu ứng / giọng đọc đưa vào bản ghép: {len(extras)} (chọn ở Bước 5a)")
        problems = final_cut.render_problems(durations, transition, fade)
        for msg in problems:
            st.warning(msg)
        if durations and not problems:
            st.info(f"Tổng thời lượng dự kiến: {final_cut.total_seconds(durations, transition, fade):.1f} giây · {len(chosen)} clip")
        if st.button("▶ Render Final", disabled=bool(problems), type="primary", width="stretch"):
            music_file = os.path.join(music_dir, tracks[0]) if tracks else None
            with st.spinner("Đang render…"):
                ok = act(lambda: ffmpeg_studio.render_final(chosen, out, durations, transition, fade, music_file, volume, extras),
                         "Render xong")
            if ok:
                st.rerun()


# ---- history -------------------------------------------------------------------------
def history(p: Pipeline, pid: int):
    scenes = p.conn.execute("SELECT id, idx, title FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    if not scenes:
        st.caption("Chưa có cảnh.")
        return
    sid = st.selectbox("Cảnh", [s["id"] for s in scenes],
                       format_func=lambda i: next(f"{s['idx']} · {s['title']}" for s in scenes if s["id"] == i))
    jobs = p.conn.execute("SELECT * FROM jobs WHERE scene_id=? ORDER BY id", (sid,)).fetchall()
    with st.container(border=True):
        ui.html(ui.card_title("Lịch sử phiên bản", "so sánh các lần gen"))
        for start in range(0, len(jobs), 3):
            cols = st.columns(3)
            for col, (n, j) in zip(cols, list(enumerate(jobs, 1))[start:start + 3]):
                with col, st.container(border=True):
                    img = job_image(j["project_id"], j["id"])
                    if img:
                        st.image(img, width="stretch")
                    scores = qc_scores(p, j["id"])
                    qc = f" · QC {sum(s['score'] for s in scores) / len(scores):.2f}" if scores else ""
                    ui.html(f'<div class="cardhead"><b>v{n}</b><span class="grow"></span>{ui.state_badge(j["state"])}</div>'
                            f'<div class="muted">{j["type"]}{qc}' + (f' · “{j["retry_reason"]}”' if j["retry_reason"] else "") + "</div>")
    for j in jobs:
        with st.expander(f"job #{j['id']} {j['type']} — {j['state']} (retry {j['retry_count']})"):
            st.dataframe([dict(h) for h in p.history(j["id"])], width="stretch")


def main():
    st.set_page_config(layout="wide", page_title="AI Video Pipeline")
    ui.inject_css()
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    p = Pipeline(connect(DB))
    pid = global_bar(p)
    if pid is None:
        return
    step = st.radio("Bước", STEPS, horizontal=True, key="step", label_visibility="collapsed",
                    format_func=step_label(step_done(p, pid)))
    {STEPS[0]: step1, STEPS[1]: step2, STEPS[2]: step3, STEPS[3]: step4, STEPS[4]: step5a,
     STEPS[5]: step5b, STEPS[6]: history}[step](p, pid)


main()
