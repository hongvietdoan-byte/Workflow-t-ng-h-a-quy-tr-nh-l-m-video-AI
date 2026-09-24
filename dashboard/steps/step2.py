"""Step 2: image generation + QC."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import auto_poll_images, image_busy


def image_progress(p: Pipeline, pid: int, runner) -> None:
    """One plain answer to "is it generating?": progress per scene, and when nothing moves, the reason and what to press."""
    proj = p.project(pid)
    counts = {r["state"]: r["n"] for r in p.conn.execute(
        "SELECT state, COUNT(*) n FROM jobs WHERE project_id=? AND type='image_gen' AND state NOT IN ('rejected','cancelled') GROUP BY state", (pid,))}
    if not sum(counts.values()):
        return
    queued, running, failed = counts.get("queued", 0) + counts.get("retryable", 0), counts.get("running", 0), counts.get("failed", 0)
    summ = lineage.summary(p.conn, pid)
    done, stale = summ["images"]
    ap_running = autopilot.status(p, pid)["state"] in ("running", "queued")
    names = [r["name"] for r in p.conn.execute("SELECT name FROM characters WHERE project_id=?", (pid,))]
    linked = assets.link_characters(p.conn, pid, names) if names else {}
    with st.container(border=True):
        if linked:
            have = [n for n, a in linked.items() if a]
            lack = [n for n, a in linked.items() if not a]
            st.caption(("🖼 Ảnh tham chiếu gửi kèm mỗi cảnh: " + ", ".join(have) + "." if have else
                        "🖼 Chưa có nhân vật nào gắn tài nguyên: ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế).")
                       + (f" Chưa có ảnh tham chiếu cho: {', '.join(lack)}." if have and lack else ""))
        total = summ["total"] or 1
        st.progress(min(done / total, 1.0), text=f"{done}/{summ['total']} cảnh có ảnh đã duyệt · {queued} chờ gen · {running} đang gen · "
                                                  f"{failed} lỗi" + (f" · ⚠ {stale} ảnh cũ" if stale else ""))
        rows = p.conn.execute(
            "SELECT j.state, j.retry_count, j.escalated, s.idx, s.id sid, (SELECT AVG(score) FROM qc_results WHERE job_id=j.id) AS qc "
            "FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type='image_gen' AND j.state NOT IN ('rejected','cancelled') "
            "ORDER BY s.idx", (pid,)).fetchall()
        status = lineage.scan(p.conn, pid)
        if rows:
            client_ready = llm_client() is not None
            def label(r):
                if r["state"] == "succeeded":
                    return "Chờ Claude kiểm tra" if client_ready else "Chờ bạn duyệt (chưa có Claude)"
                text = ui.state_label(r["state"])
                if r["state"] == "approved" and (status.get(r["sid"]) or {}).get("image_stale"):
                    text += " · ⚠ cũ"
                return text + (" · ⚠ cần xem" if r["escalated"] else "")
            st.dataframe([{"Cảnh": r["idx"], "Trạng thái": label(r), "Điểm QC": f"{r['qc']:.2f}" if r["qc"] is not None else "—",
                           "Đã gen lại": r["retry_count"]} for r in rows],
                         hide_index=True, width="stretch", height=min(38 * (len(rows) + 1) + 3, 230))
        fixed = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND retry_count>0 AND state NOT IN ('cancelled')", (pid,)).fetchone()[0]
        flagged = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND escalated=1 AND state='pending_review'", (pid,)).fetchone()[0]
        if autoqc.active(pid):
            st.info("🔍 **Đang tự kiểm tra ảnh** bằng Claude (so từng người với ảnh tham chiếu + Character Lock).")
        if fixed:
            st.caption(f"🛠 Đã gen lại {fixed} lần" + (f" · {flagged} ảnh vẫn còn lỗi sau các lần sửa, đã đánh dấu để bạn xem." if flagged else "."))
        problem = autoqc.last_error(pid)
        if problem:
            st.warning(f"⚠ **Tự kiểm tra ảnh đã dừng**: {problem}")
            if st.button("↻ Thử kiểm tra lại", key=f"autoqc_retry_{pid}"):
                autoqc.clear_error(pid)
                st.rerun()
        if queued + running == 0:
            st.success("Không còn ảnh nào đang chờ gen" + (f" · {counts.get('pending_review', 0)} ảnh chờ bạn duyệt." if counts.get("pending_review") else "."))
        elif proj["paused"]:
            st.warning(f"⏸ Dự án đang **tạm dừng** nên {queued + running} ảnh xếp hàng nhưng chưa gửi. Bấm **▶ Tiếp tục** ở thanh trên cùng.")
        elif running:
            st.info(f"🔄 Đang tạo {running} ảnh, {queued} đang chờ. Trang tự cập nhật; ảnh xong tự hiện.")
        elif ap_running:
            st.info("🚀 Chế độ tự động đang xử lý các ảnh này (xem tiến độ ở Bước 1).")
        elif runner is None:
            st.warning(f"⚠ Deepix chưa được cấu hình (thiếu `DEEPIX_TOKEN`): {queued} ảnh đang chờ. Nhập ảnh thủ công ở từng cảnh, "
                       "hoặc nhờ quản trị cấu hình Deepix.")
        else:
            st.warning(f"⚠ {queued} ảnh đã xếp hàng nhưng chưa gửi: bấm **▶ Gen ảnh** ở trên.")


def step2(p: Pipeline, pid: int):
    proj = p.project(pid)
    runner = image_runner(p)
    summ = lineage.summary(p.conn, pid)
    step_header("Bước 2 · Ảnh + QC", "mỗi cảnh một ảnh đúng nhân vật, đúng bối cảnh, đã duyệt",
                f"{summ['images'][0]}/{summ['total']} cảnh có ảnh duyệt", summ["images"][1])
    pilot_panel(p, pid)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.4, 2, 2, 2.6], vertical_alignment="center")
        est_ok = True
        if runner is not None:
            est_ok = show_estimate(image_estimate(p, pid), runner)
        if c1.button("▶ Gen ảnh các cảnh chưa có / đã cũ", type="primary", key=f"gen_img_{pid}", disabled=not est_ok):
            def go():
                r = batch.queue_images(p, pid)
                sent = runner.submit_pending(pid) if runner is not None else 0
                st.toast(f"Xếp hàng {r['created']} ảnh mới, {r['redo']} ảnh làm lại" + (f" · đã gửi {sent}" if runner else "")
                         + (" · đang gen thử" if r["pilot"] else ""))
            if act(go):
                st.rerun()
        pending = [j["id"] for j in p.conn.execute(
            "SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review' ORDER BY id", (pid,)).fetchall()]
        if confirm_all("approve_all", pending, f"✔ Duyệt tất cả ({len(pending)} ảnh)", f"Duyệt tất cả {len(pending)} ảnh đang chờ duyệt?", c2):
            for jid in pending:
                p.approve(jid, "user")
            st.rerun()
        failed = p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='failed' AND escalated=0", (pid,)).fetchall()
        if c3.button(f"↻ Gen lại ảnh lỗi ({len(failed)})", key="reject_all", disabled=not failed):
            for j in failed:
                act(lambda: p.retry(j["id"], "gen lại ảnh lỗi"))
            st.rerun()
        c4.markdown(ui.badge(ui.MODE_LABELS.get(proj["operating_mode"], proj["operating_mode"]), "b-pri")
                    + f' <span class="muted">{"Claude tự duyệt ảnh đạt" if proj["operating_mode"] == "auto" else "mọi ảnh chờ bạn duyệt"}</span>',
                    unsafe_allow_html=True)
        if runner is None:
            st.caption("ℹ Deepix chưa cấu hình: nhập ảnh thủ công cho từng cảnh (cách cấu hình: docs/RUNBOOK.md).")
        else:
            st.caption(f"Nhà cung cấp ảnh: {runner.provider.name}" + (" (giả lập)" if runner.provider.name.startswith("mock") else " (gọi API thật, tốn credit)")
                       + f" · khung {formats.label(formats.project_aspect(proj))}")
    image_progress(p, pid, runner)
    if image_busy(p.conn, pid):
        auto_poll_images(pid)                           # results, the automatic check and automatic fixes all show up by themselves
    qc_policy_panel(p, pid)
    set_check_panel(p, pid)
    shot_storyboard_panel(p, pid)

    client = llm_client()
    to_check = p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'",
                              (pid,)).fetchone()["c"]
    if client is None and to_check:
        st.warning(f"⚠ **Chưa có điểm QC**: {to_check} ảnh vừa gen chưa được chấm vì chưa có Claude ({claude_hint()}). "
                   "Trong lúc đó hãy tự xem từng ảnh (đúng nhân vật? đúng bối cảnh? lỗi tay/mặt?) rồi duyệt hoặc loại.")
    jobs = p.conn.execute(
        "SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    if not jobs:
        st.caption("Chưa có ảnh nào: bấm “▶ Gen ảnh các cảnh chưa có / đã cũ” (cần khóa Character Bible ở Bước 1 trước).")
        return
    history = {}
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
    stale = lineage.scan(p.conn, pid)
    grid, detail = st.columns([3, 1.15], gap="large")
    with grid:
        per_row = 3
        for start in range(0, len(shown_sids), per_row):
            cols = st.columns(per_row)
            for col, sid in zip(cols, shown_sids[start:start + per_row]):
                with col:
                    image_card_group(p, pid, history[sid], proj, (stale.get(sid) or {}).get("image_stale"))
        if not shown_sids:
            st.caption("Không có ảnh nào trong bộ lọc này.")
    with detail:
        job = next(j for j in jobs if j["id"] == st.session_state[sel_key])
        image_detail(p, pid, job, proj)


def image_card_group(p: Pipeline, pid: int, history: list, proj, stale_reason=None) -> None:
    """One card per SCENE: every redo adds an attempt to its history; ‹ › pages through them, only the newest is live."""
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
        image_card(p, pid, j, proj, read_only=not is_latest, stale_reason=stale_reason if is_latest else None)


def image_card(p: Pipeline, pid: int, j, proj, read_only: bool = False, stale_reason=None):
    jid, state = j["id"], j["state"]
    scores = qc_scores(p, jid)
    with st.container(border=True):
        img = job_image(pid, jid)
        if img:
            show_image(img, width="stretch")
        else:
            ui.html('<div style="height:120px;border-radius:8px;background:var(--bg);display:grid;place-items:center;'
                    f'color:var(--muted)">{"⏳ đang gen…" if state == "running" else "chưa có ảnh"}</div>')
        flag = " " + ui.badge("⚠ cần xem", "b-warn") if j["escalated"] else ""
        old = " " + ui.stale_badge(stale_reason) if stale_reason and state == "approved" else ""
        ui.html(f'<div class="cardhead"><b>{C.unit_label(p, j["project_id"], j["idx"])}</b><span class="grow"></span>{ui.state_badge(state)}{flag}{old}</div>')
        if scores:
            mean = sum(s["score"] for s in scores) / len(scores)
            ui.html(ui.qc_bar(mean, proj["qc_auto_pass_threshold"]))
        if read_only:
            if j["retry_reason"]:
                st.caption(f"Lý do gen lại lúc đó: {j['retry_reason'][:160]}")
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}", width="stretch"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state in ("succeeded", "pending_review"):
            a, b, c = st.columns(3)
            if a.button("✔ Duyệt", key=f"a_{jid}"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if b.button("✖ Loại", key=f"r_{jid}", help="Loại và gen lại (ghi chú lý do ở khung chi tiết bên phải)"):
                act(lambda: p.reject(jid, "user", st.session_state.get(f"note_{jid}") or None))
                st.rerun()
            if c.button("🔍 Xem", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state in ("queued", "running"):
            a, b = st.columns(2)
            if b.button("■ Hủy", key=f"c_{jid}"):
                act(lambda: p.cancel(jid))
                st.rerun()
            if a.button("🔍 Xem", key=f"sel_btn_{jid}", help="Chi tiết / nhập ảnh thủ công"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state == "failed" and not j["escalated"]:
            a, b = st.columns(2)
            if a.button("↻ Gen lại", key=f"retry_{jid}"):
                act(lambda: p.retry(jid, "gen lại"))
                st.rerun()
            if b.button("🔍 Xem", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        else:
            if stale_reason and state == "approved" and st.button("↻ Gen lại theo nội dung mới", key=f"stale_{jid}", type="primary"):
                if act(lambda: p.reopen_approved(jid, f"Nội dung cảnh đã đổi: {stale_reason}"), "Đã xếp hàng gen lại"):
                    st.rerun()
            if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"rs_{jid}", help="Đã hết số lần thử: bắt đầu lại cảnh này"):
                if act(lambda: p.restart_job(jid), "Đã xếp hàng ảnh mới cho cảnh"):
                    st.rerun()
            if st.button("🔍 Xem", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        scene_expander(p, j["scene_id"])


def image_detail(p: Pipeline, pid: int, j, proj):
    jid, state = j["id"], j["state"]
    with st.container(border=True):
        ui.html(ui.card_title(f"Chi tiết ảnh — {C.unit_label(p, j['project_id'], j['idx'])}", f"lần gen #{jid} · đã gen lại {j['retry_count']} lần"))
        ui.html(ui.state_badge(state))
        if j["retry_reason"]:
            st.caption(f"Lý do gen lại: {j['retry_reason']}")
        img = job_image(pid, jid)
        if img:
            show_image(img, width="stretch")
        scene_expander(p, j["scene_id"], expanded=True)
        scores = qc_scores(p, jid)
        if scores:
            ui.html('<div class="muted" style="font-weight:600;margin-top:8px">Điểm QC (Claude)</div>')
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
            with st.expander("Nâng cao: prompt QC + dán điểm tay"):
                st.code(llm_runner.plain(prompts.build_qc_bundle(p, j["scene_id"], C.DATA)), language="markdown")
                raw = st.text_area("JSON điểm QC từ Claude", key=f"qc_{jid}", height=100)
                if st.button("Chấm điểm", key=f"score_{jid}", disabled=not raw.strip()):
                    def score():
                        obj = llm_io.validate_qc_result(raw, prompts.qc_criteria())
                        st.toast(f"Quyết định: {p.apply_qc(jid, obj['criteria'])}")
                    if act(score):
                        st.rerun()
        if state in ("succeeded", "pending_review"):
            note = st.text_input("Ghi chú lý do loại (đưa vào prompt gen lại)", key=f"note_{jid}")
            a, b = st.columns(2)
            if b.button("✖ Loại & gen lại", key=f"dr_{jid}"):
                act(lambda: p.reject(jid, "user", note or None))
                st.rerun()
            if a.button("✔ Duyệt", key=f"da_{jid}", type="primary"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if st.button("🗑 Xóa (vào thùng rác, không gen lại)", key=f"dd_{jid}"):
                act(lambda: p.reject(jid, "user", note or "đã xóa", respawn=False))
                st.rerun()
        if state == "failed" and not j["escalated"] and st.button("↻ Gen lại", key=f"dretry_{jid}"):
            act(lambda: p.retry(jid, "retry"))
            st.rerun()
        if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"drs_{jid}", type="primary"):
            if act(lambda: p.restart_job(jid), "Đã xếp hàng job mới cho cảnh"):
                st.rerun()
        if state == "approved":
            r_note = st.text_input("Lý do bỏ duyệt (đưa vào prompt gen lại)", key=f"rn_{jid}")
            st.caption("Bỏ duyệt: motion prompt và video làm từ ảnh này sẽ hiện ⚠ cũ để làm lại.")
            if st.button("↩ Bỏ duyệt & gen lại ảnh", key=f"reopen_{jid}"):
                if act(lambda: p.reopen_approved(jid, r_note or None), "Đã bỏ duyệt, xếp hàng gen lại"):
                    st.rerun()



def qc_policy_panel(p: Pipeline, pid: int) -> None:
    """One QC policy instead of six knobs; the fine settings stay under 'Tùy chỉnh'."""
    proj = p.project(pid)
    current = qc_policy.current(proj)
    keys = list(qc_policy.PRESETS) + [qc_policy.CUSTOM]
    labels = {**{k: v["label"] for k, v in qc_policy.PRESETS.items()}, qc_policy.CUSTOM: "Tùy chỉnh"}
    with st.container(border=True):
        c1, c2 = st.columns([1.3, 4], vertical_alignment="center")
        pick = c1.selectbox("Chính sách QC ảnh", keys, index=keys.index(current), format_func=labels.get, key=f"qcpol_{pid}")
        if pick != current:
            qc_policy.apply(p, pid, pick)
            st.rerun()
        c2.caption((qc_policy.PRESETS[pick]["note"] + " ") if pick in qc_policy.PRESETS else "" + "")
        c2.caption("→ " + qc_policy.describe(proj))
        if pick == qc_policy.CUSTOM:
            with st.expander("Tùy chỉnh chi tiết", expanded=True):
                th = st.slider("Ngưỡng đạt", 0.5, 1.0, float(proj["qc_auto_pass_threshold"]), 0.01, key=f"th_{pid}")
                if abs(th - proj["qc_auto_pass_threshold"]) > 1e-9:
                    p.set_threshold(pid, th)
                max_retry = st.slider("Gen lại tối đa mỗi cảnh (rồi báo bạn)", 1, 8, int(proj["max_retry_count"]), 1, key=f"maxretry_{pid}")
                if max_retry != proj["max_retry_count"]:
                    p.set_max_retry(pid, max_retry)
                autofix = st.checkbox("Claude tự gen lại ảnh dưới ngưỡng trước khi đến bạn (mỗi lần tốn credit)", bool(proj["qc_autofix"]),
                                      key=f"autofix_{pid}")
                if autofix != bool(proj["qc_autofix"]):
                    p.set_qc_autofix(pid, autofix)
                floor_on = st.checkbox("Tự loại ảnh rất tệ", proj["qc_reject_floor"] is not None, key=f"rej_on_{pid}")
                reject_floor = st.slider("Mức loại ngay", 0.30, 0.80, float(proj["qc_reject_floor"] or 0.5), 0.05, key=f"rej_v_{pid}",
                                         disabled=not floor_on)
                new_reject = round(reject_floor, 2) if floor_on else None
                if new_reject != proj["qc_reject_floor"]:
                    p.set_reject_floor(pid, new_reject)
                if proj["operating_mode"] == "auto":
                    zone_on = st.checkbox("Vùng chờ review (giữa mức sàn và ngưỡng: chờ bạn thay vì tự loại)", proj["qc_review_floor"] is not None,
                                          key=f"zone_{pid}")
                    floor = st.slider("Mức sàn", 0.3, float(proj["qc_auto_pass_threshold"]),
                                      min(float(proj["qc_review_floor"] or 0.6), float(proj["qc_auto_pass_threshold"])), 0.01,
                                      key=f"floor_{pid}", disabled=not zone_on)
                    new_floor = floor if zone_on else None
                    if new_floor != proj["qc_review_floor"]:
                        p.set_review_floor(pid, new_floor)


def pilot_panel(p: Pipeline, pid: int) -> None:
    """Pilot before the batch: a few representative scenes first (game-asset-set-generator skill)."""
    n = p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]
    state = pilot.get(p, pid)
    has_images = p.conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type='image_gen' LIMIT 1", (pid,)).fetchone()
    if not state["enabled"]:
        if n >= pilot.MIN_SCENES and not has_images:
            c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
            c1.caption(f"💡 {n} cảnh: nên **gen thử {pilot.SIZE} cảnh đại diện** trước (cảnh then chốt + đầu mỗi nhóm), duyệt phong cách "
                       "và nhân vật rồi mới gen phần còn lại — lỗi lộ ra ở mẫu thử thay vì ở cả lô.")
            if c2.button("🧪 Bật gen thử trước", key=f"pilot_on_{pid}"):
                pilot.start(p, pid)
                st.rerun()
        return
    idx = [r["idx"] for r in p.conn.execute(f"SELECT idx FROM scenes WHERE id IN ({','.join('?' * len(state['scenes']))}) ORDER BY idx",
                                             state["scenes"])] if state["scenes"] else []
    if state["released"]:
        st.caption(f"🧪 Đã gen thử cảnh {', '.join(map(str, idx))} và mở gen cả lô.")
        return
    with st.container(border=True):
        ready = pilot.done(p, pid)
        st.markdown(f"🧪 **Gen thử trước**: chỉ cảnh {', '.join(map(str, idx))} được gen. "
                    + ("Các cảnh thử đã có ảnh duyệt — xem phong cách/nhân vật ổn chưa rồi mở gen cả lô." if ready
                       else "Duyệt ảnh các cảnh này trước."))
        c1, c2 = st.columns(2)
        if c1.button("✔ Mẫu thử ổn — gen phần còn lại", key=f"pilot_release_{pid}", type="primary", disabled=not ready):
            pilot.release(p, pid)
            st.rerun()
        if c2.button("Bỏ gen thử", key=f"pilot_off_{pid}"):
            pilot.save(p, pid, {"enabled": False, "scenes": [], "released": False})
            st.rerun()


def shot_storyboard_panel(p: Pipeline, pid: int) -> None:
    """Every start picture in film order with size, role, length and lines — and, before any video is paid for, the storyboard
    checkpoint (W1): flagged shots first, the characters' reference pictures next to each picture, one button to go on to video."""
    from core import shots, storyboard_gate
    rows = shots.shots_of(p, pid)
    if not rows:
        return
    is_v3 = any(r["data"].get("shot_no") for r in rows)
    total = sum(float(r["data"].get("duration_s") or 0) for r in rows)
    own = [r for r in rows if shots.needs_own_image(p.conn, r["id"])]      # multi-shot: later shots of a group use the group's picture
    have = [r for r in own if storyboard_gate.picture_path(p.conn, C.DATA, pid, r["id"])[0]]
    note = "" if len(own) == len(rows) else f" (multi-shot: {len(rows) - len(own)} shot dùng ảnh đầu nhóm)"
    gates = autopilot.get_gates(p, pid)
    waiting = gates.get("waiting_for") == "storyboard" and autopilot.status(p, pid)["state"] == "waiting"
    flags = storyboard_gate.flags(p, pid, C.DATA) if have else {}
    flagged = [r for r in rows if flags.get(r["id"])]
    title = (f"🎞 Storyboard — {len(have)}/{len(own)} ảnh · {len(rows)} {'shot' if is_v3 else 'cảnh'} · {total:.0f}s{note}"
             + (f" · ⚑ {len(flagged)} có cờ" if flagged else "") + (" · ⏸ CHỜ BẠN DUYỆT" if waiting else ""))
    with st.expander(title, expanded=waiting):
        st.caption("Ảnh khung đầu theo thứ tự phim: kiểm tra nhân vật (so với ảnh tài nguyên bên dưới), cỡ cảnh, nhịp, liên tục TRƯỚC khi gen "
                   "video — sửa ảnh rẻ hơn nhiều so với gen lại clip. ⚑ = điểm QC cho thấy lỗi dễ thấy (Claude chưa được hiệu chỉnh: "
                   "tự xem lại, không tin mù).")
        from core import features
        off = features.pending()
        if off:                                    # rule 5: a feature switched off until its real test is never a mystery
            st.caption("🧪 Đang tắt tới khi thử thật đạt: " + "; ".join(v["label"] for v in off.values())
                       + " (bật thử bằng FEATURE_<TÊN>=1, xem core/features.py).")
        if waiting:
            c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
            c1.warning(f"Chế độ tự động đang dừng ở đây: {storyboard_gate.summary(p, pid, C.DATA)}. Loại/gen lại shot sai ở danh sách ảnh bên trên, "
                       "rồi bấm duyệt để viết motion prompt và gen video.")
            if c2.button("✔ Duyệt storyboard — gen video", key=f"board_ok_{pid}", type="primary"):
                autopilot.resume(p, pid, p.actor)
                autopilot_manager(C.DB, C.DATA).start(pid)
                st.rerun()
        per_row = 6
        for k in range(0, len(rows), per_row):
            cols = st.columns(per_row)
            for col, r in zip(cols, rows[k:k + per_row]):
                d = r["data"]
                path, held = storyboard_gate.picture_path(p.conn, C.DATA, pid, r["id"])
                if path:
                    try:
                        col.image(path, width="stretch", caption="⏸ chờ bạn duyệt" if held else None)
                    except Exception:  # noqa: BLE001 - a corrupt / half-downloaded file must not take the page down
                        col.caption(f"⚠ Không đọc được ảnh: {os.path.basename(path)}")
                elif not shots.needs_own_image(p.conn, r["id"]):
                    lead = shots.image_scene(p.conn, r["id"])
                    col.caption("↳ tiếp nối trong clip multi-shot của "
                                + next((x["label"] for x in rows if x["id"] == lead), "shot đầu nhóm"))
                else:
                    col.caption("— chưa có ảnh")
                refs = [x for x in assets.scene_references(p.conn, pid, d) if x["role"] == "character"][:3]
                if refs:
                    col.image([x["path"] for x in refs], width=36, caption=[x["label"] for x in refs])
                lines = " / ".join(f"{x.get('speaker')}: {x.get('text')}" for x in d.get("dialogue") or [])
                col.caption(f"**{r['label']}** · {d.get('size') or d.get('shot') or ''} · {d.get('role') or ''}"
                            + (f" · {float(d.get('duration_s') or 0):g}s" if d.get("duration_s") else "")
                            + (" · ➜" if d.get("continuous_with_next") else "") + (f" — {lines[:80]}" if lines else ""))
                for why in flags.get(r["id"]) or []:
                    col.markdown(f":orange[⚑ {escape(why)}]")


def set_check_panel(p: Pipeline, pid: int) -> None:
    """Whole-set consistency (game-asset-set-generator three-layer QA): one look at all approved pictures together."""
    approved = p.conn.execute("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='image_gen' AND state='approved'",
                              (pid,)).fetchone()[0]
    if approved < 2:
        return
    last = claude_tasks.last_set_check(C.DATA, pid)
    label = "🎨 Kiểm tra đồng bộ cả bộ ảnh" + ("" if last is None else (" — ổn" if last.get("ok") and not last.get("issues")
                                                                         else f" — {len(last.get('issues') or [])} cảnh lệch"))
    with st.expander(label, expanded=bool(last and last.get("issues"))):
        st.caption("Claude xem MỘT tấm ghép mọi ảnh đã duyệt để tìm cảnh lệch phong cách/ánh sáng/màu/nhân vật so với cả bộ "
                   "(ảnh đẹp nhưng lạc tông vẫn là lỗi). Nên chạy trước khi sang Bước 3.")
        client = llm_client()
        if st.button(f"🤖 Kiểm tra {approved} ảnh đã duyệt", key=f"setqc_{pid}", disabled=client is None, help=None if client else claude_hint()):
            with st.spinner("Claude đang so cả bộ ảnh…"):
                act(lambda: claude_tasks.set_consistency(p, pid, client, C.DATA))
            st.rerun()
        sheet = os.path.join(C.DATA, str(pid), "qc_set", "contact_sheet.png")
        if last is not None:
            if os.path.exists(sheet):
                show_image(sheet, width="stretch")
            if last.get("summary"):
                st.info(last["summary"])
            for n, it in enumerate(last.get("issues") or []):
                c1, c2 = st.columns([4, 1.3], vertical_alignment="center")
                c1.markdown(f"**S{it['idx']:02d}**: {escape(it['problem'])}" + (f" → _{escape(it.get('fix') or '')}_" if it.get("fix") else ""))
                if c2.button("↻ Gen lại cảnh này", key=f"setqc_redo_{pid}_{n}"):
                    act(lambda: claude_tasks.redo_from_set_check(p, pid, it["idx"], it.get("fix") or it["problem"]), "Đã xếp hàng gen lại")
                    st.rerun()
