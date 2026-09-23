"""Step 2: image generation + QC."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import auto_poll_images, image_busy


def image_progress(p: Pipeline, pid: int, runner) -> None:
    """One plain answer to "is it generating?": the progress, and when nothing moves, the reason and what to press."""
    proj = p.project(pid)
    counts = {r["state"]: r["n"] for r in p.conn.execute(
        "SELECT state, COUNT(*) n FROM jobs WHERE project_id=? AND type='image_gen' AND state NOT IN ('rejected','cancelled') GROUP BY state", (pid,))}
    total = sum(counts.values())
    if not total:
        return
    queued, running, failed = counts.get("queued", 0) + counts.get("retryable", 0), counts.get("running", 0), counts.get("failed", 0)
    done = counts.get("succeeded", 0) + counts.get("pending_review", 0) + counts.get("approved", 0)
    ap_running = autopilot.status(p, pid)["state"] in ("running", "queued")
    names = [r["name"] for r in p.conn.execute("SELECT name FROM characters WHERE project_id=?", (pid,))]
    linked = assets.link_characters(p.conn, pid, names) if names else {}
    with st.container(border=True):
        if linked:
            have = [n for n, a in linked.items() if a]
            lack = [n for n, a in linked.items() if not a]
            st.caption(("🖼 Ảnh tham chiếu gửi kèm mỗi cảnh (theo nhân vật trong cảnh): " + ", ".join(have) + "." if have else
                        "🖼 Chưa có nhân vật nào gắn tài nguyên: ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế).")
                       + (f" Chưa có ảnh tham chiếu cho: {', '.join(lack)} (vẽ theo mô tả)." if have and lack else ""))
        st.progress(done / total, text=f"{done}/{total} ảnh đã có · {queued} đang chờ · {running} đang gen · {failed} lỗi")
        rows = p.conn.execute(
            "SELECT j.state, j.retry_count, j.escalated, s.idx, (SELECT AVG(score) FROM qc_results WHERE job_id=j.id) AS qc "
            "FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type='image_gen' AND j.state NOT IN ('rejected','cancelled') "
            "ORDER BY s.idx", (pid,)).fetchall()
        if rows:
            client_ready = llm_client() is not None
            wait_label = "Chờ Claude kiểm tra" if client_ready else "Chờ bạn duyệt (chưa có Claude)"
            state_label = {"queued": "Chờ gen", "retryable": "Chờ gửi lại", "running": "Đang gen", "succeeded": wait_label,
                          "pending_review": "Chờ bạn duyệt", "approved": "Đã duyệt", "failed": "Lỗi"}
            st.dataframe([{"Cảnh": r["idx"], "Trạng thái": state_label.get(r["state"], r["state"]) + (" ⚠ cần xem" if r["escalated"] else ""),
                          "Điểm QC": f"{r['qc']:.2f}" if r["qc"] is not None else "—", "Đã tự sửa": r["retry_count"]} for r in rows],
                         hide_index=True, width="stretch", height=min(38 * (len(rows) + 1) + 3, 230))
        fixed = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND retry_count>0 AND state NOT IN ('cancelled')", (pid,)).fetchone()[0]
        flagged = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND escalated=1 AND state='pending_review'", (pid,)).fetchone()[0]
        if autoqc.active(pid):
            st.info("🔍 **Đang tự kiểm tra ảnh** bằng Claude (so từng người với ảnh tham chiếu). Ảnh lỗi sẽ được gen lại tự động; ảnh đạt mới đến chỗ bạn duyệt.")
        if fixed:
            st.caption(f"🛠 Đã tự gen lại {fixed} lần vì QC thấy lỗi" + (f" · {flagged} ảnh vẫn còn lỗi sau các lần sửa, đã đánh dấu để bạn xem." if flagged else "."))
        problem = autoqc.last_error(pid)
        if problem:
            st.warning(f"⚠ **Tự kiểm tra ảnh đã dừng**: {problem}")
            if st.button("↻ Thử kiểm tra lại", key=f"autoqc_retry_{pid}"):
                autoqc.clear_error(pid)
                st.rerun()
        if queued + running == 0:
            st.success("Không còn job nào chờ: " + (f"{counts.get('pending_review', 0)} ảnh đang chờ bạn duyệt." if counts.get("pending_review") else "xong."))
        elif proj["paused"]:
            st.warning(f"⏸ **Chưa tạo ảnh nào**: dự án đang **PAUSE** nên {queued + running} job xếp hàng nhưng không job nào được bắt đầu. Bấm **▶ Resume** ở thanh trên cùng.")
        elif running:
            st.info(f"🔄 **Đang tạo ảnh**: {running} ảnh đang được xử lý, {queued} đang chờ. Trang tự cập nhật, ảnh xong sẽ tự hiện; bạn không cần bấm gì.")
        elif ap_running:
            st.info("🚀 Chế độ tự động đang xử lý các ảnh này (xem tiến độ chi tiết ở Bước 1).")
        elif runner is None:
            st.warning(f"⚠ **Chưa tạo ảnh nào**: Deepix chưa được cấu hình (thiếu `DEEPIX_TOKEN`) nên hệ thống không tự gen. {queued} job đang chờ bạn "
                       "nhập ảnh thủ công ở từng cảnh, hoặc nhờ quản trị cấu hình Deepix.")
        else:
            st.warning(f"⚠ **Chưa tạo ảnh nào**: {queued} job đã xếp hàng nhưng chưa được gửi đi. Ở chế độ từng bước hãy bấm **⟳ Submit + Poll 1 lần** "
                       "hoặc **▶ Chạy heartbeat tới khi xong** bên dưới (hoặc dùng chế độ tự động).")


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
        pending = [j["id"] for j in p.conn.execute(
            "SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review' ORDER BY id",
            (pid,)).fetchall()]
        if confirm_all("approve_all", pending, f"✔ Duyệt tất cả ({len(pending)} ảnh)",
                       f"Duyệt tất cả {len(pending)} ảnh đang chờ duyệt?", c2):
            for jid in pending:
                p.approve(jid, "user")
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
    image_progress(p, pid, runner)
    if image_busy(p.conn, pid):
        auto_poll_images(pid)                           # results, the automatic check and automatic fixes all show up by themselves
    with st.expander("⚙ Thiết lập QC: tự loại ảnh điểm thấp · vùng chờ review"):
        f1, f2, f3 = st.columns([2, 3, 3], vertical_alignment="center")
        floor_on = f1.checkbox("Tự loại ảnh điểm thấp", proj["qc_reject_floor"] is not None, key=f"rej_on_{pid}",
                               help="Ảnh có điểm QC dưới mức này bị loại ngay (vào Thùng rác) và xếp hàng gen ảnh mới, "
                                    "ở cả hai chế độ. Ảnh điểm cao vẫn phải chờ bạn duyệt ở human_qc.")
        reject_floor = f2.slider("Dưới mức này tự loại + xếp hàng gen ảnh mới", 0.30, 0.80,
                                 float(proj["qc_reject_floor"] or 0.5), 0.05, key=f"rej_v_{pid}", disabled=not floor_on)
        f3.caption("Ảnh bị loại vào 🗑 Thùng rác (tab Lịch sử, giữ 30 ngày). Ảnh mới chỉ được gen khi bạn bấm chạy.")
        new_reject = round(reject_floor, 2) if floor_on else None
        if new_reject != proj["qc_reject_floor"] and (new_reject is None or proj["qc_reject_floor"] is None
                                                      or abs(new_reject - proj["qc_reject_floor"]) > 1e-9):
            p.set_reject_floor(pid, new_reject)
        autofix = st.checkbox(f"Tự kiểm tra bằng Claude và tự gen lại ảnh lỗi trước khi đến bạn duyệt (tối đa {proj['max_retry_count']} lần mỗi ảnh; mỗi lần gen tốn credit)",
                              bool(proj["qc_autofix"]), key=f"autofix_{pid}",
                              help="Ảnh vừa gen được so với ảnh tham chiếu của từng nhân vật. Ảnh đạt threshold mới đến bạn duyệt; ảnh lỗi được gen lại với lỗi ghi vào prompt. "
                                   "Tắt thì QC chỉ cho điểm gợi ý và mọi ảnh đều chờ bạn.")
        if autofix != bool(proj["qc_autofix"]):
            p.set_qc_autofix(pid, autofix)
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
        st.caption("ℹ Deepix chưa cấu hình: nhập ảnh thủ công cho từng job (cách cấu hình: docs/RUNBOOK.md).")
    else:
        st.caption(f"Provider ảnh: {runner.provider.name}" + (" (giả lập — ảnh 1x1)" if runner.provider.name == "mock-image" else " (gọi API thật, tốn credit)"))
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

    client = llm_client()
    to_check = p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'",
                              (pid,)).fetchone()["c"]
    if client is None and to_check:
        st.warning(f"⚠ **Chưa có điểm QC**: {to_check} ảnh vừa gen chưa được chấm vì chưa có Claude (cần `ANTHROPIC_API_KEY`, hoặc `LLM_PROVIDER=claude_cli` "
                   "để dùng Claude Code trên máy). Trong lúc đó hãy tự xem từng ảnh (đúng nhân vật? đúng bối cảnh? lỗi tay/mặt?) rồi ✓ duyệt hoặc ✕ loại.")
    jobs = p.conn.execute(
        "SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    if not jobs:
        st.caption("Chưa có job gen ảnh. Duyệt Character Bible ở Bước 1 rồi bấm ‘Tạo job gen ảnh’.")
        return
    history = {}                                          # scene_id -> its jobs, oldest first (every retry / "gen lại" kept, not just the newest)
    for j in jobs:
        history.setdefault(j["scene_id"], []).append(j)
    latest = {sid: hist[-1] for sid, hist in history.items()}
    counts = {k: sum(1 for j in latest.values() if j["state"] in v) for k, v in FILTER_STATES.items()}
    counts["all"] = len(latest)
    flt = st.radio("Lọc", list(FILTERS), horizontal=True, key=f"filter_{pid}", label_visibility="collapsed",
                   format_func=lambda k: f"{FILTERS[k]} {counts[k]}")
    shown_sids = [sid for sid, j in latest.items() if flt == "all" or j["state"] in FILTER_STATES[flt]]
    sel_key = f"sel_{pid}"
    if st.session_state.get(sel_key) not in {j["id"] for j in jobs}:
        st.session_state[sel_key] = latest[shown_sids[0]]["id"] if shown_sids else jobs[0]["id"]
    grid, detail = st.columns([3, 1.15], gap="large")
    with grid:
        per_row = 3
        for start in range(0, len(shown_sids), per_row):
            cols = st.columns(per_row)
            for col, sid in zip(cols, shown_sids[start:start + per_row]):
                with col:
                    image_card_group(p, pid, history[sid], proj)
        if not shown_sids:
            st.caption("Không có ảnh nào trong bộ lọc này.")
    with detail:
        job = next(j for j in jobs if j["id"] == st.session_state[sel_key])
        image_detail(p, pid, job, proj)


def image_card_group(p: Pipeline, pid: int, history: list, proj) -> None:
    """One card per SCENE (not per job): every "gen lại" adds an attempt to this scene's history instead of a new card in the
    grid, which would make a scene with several retries hard to tell apart from others once there are many scenes. ‹ › pages
    through the attempts; only the newest attempt is live (can be approved/rejected/retried), older ones are for comparison."""
    sid = history[0]["scene_id"]
    n = len(history)
    key = f"hist_{pid}_{sid}"
    pointer = min(st.session_state.get(key, n - 1), n - 1)
    j = history[pointer]
    is_latest = pointer == n - 1
    with st.container(border=True):
        if n > 1:
            nav = st.columns([1, 3, 1], vertical_alignment="center")
            if nav[0].button("‹", key=f"{key}_prev", disabled=pointer == 0, help="Bản trước"):
                st.session_state[key] = pointer - 1
                st.rerun()
            nav[1].markdown(f"<div style='text-align:center' class='muted'>Bản {pointer + 1}/{n}"
                            + ("" if is_latest else " · bản cũ") + "</div>", unsafe_allow_html=True)
            if nav[2].button("›", key=f"{key}_next", disabled=is_latest, help="Bản sau (mới hơn)"):
                st.session_state[key] = pointer + 1
                st.rerun()
        image_card(p, pid, j, proj, read_only=not is_latest)


def image_card(p: Pipeline, pid: int, j, proj, read_only: bool = False):
    jid, state = j["id"], j["state"]
    scores = qc_scores(p, jid)
    with st.container(border=True):
        img = job_image(pid, jid)
        if img:
            show_image(img, width="stretch")
        else:
            ui.html('<div style="height:120px;border-radius:8px;background:var(--bg);display:grid;place-items:center;'
                    f'color:var(--muted)">{"⏳ đang gen…" if state == "running" else "chưa có ảnh"}</div>')
        flag = " " + ui.badge("⚠ escalated", "b-warn") if j["escalated"] else ""
        ui.html(f'<div class="cardhead"><b>Cảnh {j["idx"]}</b><span class="grow"></span>{ui.state_badge(state)}{flag}</div>')
        if scores:
            mean = sum(s["score"] for s in scores) / len(scores)
            ui.html(ui.qc_bar(mean, proj["qc_auto_pass_threshold"]))
        if read_only:                                     # an older attempt: for comparison only, no approve/reject/retry here
            if j["retry_reason"]:
                st.caption(f"Lý do gen lại lúc đó: {j['retry_reason'][:160]}")
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}", width="stretch"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state in ("succeeded", "pending_review"):
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
        elif state == "failed" and not j["escalated"]:
            a, b = st.columns(2)
            if a.button("↻", key=f"retry_{jid}", help="Retry"):
                act(lambda: p.retry(jid, "retry"))
                st.rerun()
            if b.button("🔍", key=f"sel_btn_{jid}", help="Chi tiết"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        else:
            if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"rs_{jid}",
                                            help="Đã hết số lần thử: bắt đầu lại cảnh này với một job mới"):
                if act(lambda: p.restart_job(jid), "Đã xếp hàng job mới cho cảnh"):
                    st.rerun()
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        scene_expander(p, j["scene_id"])


def image_detail(p: Pipeline, pid: int, j, proj):
    jid, state = j["id"], j["state"]
    with st.container(border=True):
        ui.html(ui.card_title(f"Chi tiết ảnh — Cảnh {j['idx']}", f"job #{jid} · retry {j['retry_count']}"))
        ui.html(ui.state_badge(state))
        if j["retry_reason"]:
            st.caption(f"Lý do retry: {j['retry_reason']}")
        img = job_image(pid, jid)
        if img:
            show_image(img, width="stretch")
        scene_expander(p, j["scene_id"], expanded=True)
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
            client = llm_client()
            if client is not None:
                st.caption("🔍 Claude tự kiểm tra ảnh này ở nền (không cần bấm); xem tiến độ ở đầu Bước 2.")
            with st.expander("QC Agent — prompt & kết quả"):
                st.code(prompts.build_qc_bundle(p, j["scene_id"], C.DATA), language="markdown")
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
            if st.button("🗑 Xóa (vào thùng rác, không gen lại)", key=f"dd_{jid}"):
                act(lambda: p.reject(jid, "user", note or "đã xóa", respawn=False))
                st.rerun()
        if state == "failed" and not j["escalated"] and st.button("↻ Retry", key=f"dretry_{jid}"):
            act(lambda: p.retry(jid, "retry"))
            st.rerun()
        if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"drs_{jid}", type="primary"):
            if act(lambda: p.restart_job(jid), "Đã xếp hàng job mới cho cảnh"):
                st.rerun()
        if state == "approved":
            r_note = st.text_input("Lý do bỏ duyệt (đưa vào prompt gen lại)", key=f"rn_{jid}")
            st.caption("Video đã làm từ ảnh này không tự đổi; gen lại video ở Bước 4 nếu cần.")
            if st.button("↩ Bỏ duyệt & gen lại ảnh", key=f"reopen_{jid}"):
                if act(lambda: p.reopen_approved(jid, r_note or None), "Đã bỏ duyệt, xếp hàng gen lại"):
                    st.rerun()
