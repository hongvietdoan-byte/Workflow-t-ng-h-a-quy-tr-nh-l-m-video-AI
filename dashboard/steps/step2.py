"""Step 2: image generation + QC."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import auto_poll_images, image_busy
from dashboard.design.screens.prompt_versions_ui import spin as _spin  # S14.17: spinner khi Đạo diễn viết lại prompt
from core import image_models


def D_card(key: str):
    from dashboard.design import components
    return components.card(key)


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
    with (D_card("sb-progress") if ui.v2_on() else st.container(border=True)):
        v2 = ui.v2_on()
        if v2:
            from dashboard.design.screens import storyboard_cards as SB
        if linked and v2:                                 # v2: một dòng; danh sách có/thiếu ảnh tham chiếu vào ⓘ
            have = [n for n, a in linked.items() if a]
            lack = [n for n, a in linked.items() if not a]
            detail = (("**Có ảnh tham chiếu:** " + ", ".join(have) + "\n\n" if have else
                       "Chưa có nhân vật nào gắn tài nguyên: ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế).\n\n")
                      + (f"**Chưa có ảnh tham chiếu cho:** {', '.join(lack)}" if lack else ""))
            SB.note(f"🖼 Ảnh tham chiếu: {len(have)}/{len(linked)} nhân vật" + ("" if have else " — vẽ theo mô tả chữ"), detail, "sb-prog-refs",
                    kind="" if have else "warn")
        elif linked:
            have = [n for n, a in linked.items() if a]
            lack = [n for n, a in linked.items() if not a]
            st.caption(("🖼 Ảnh tham chiếu gửi kèm mỗi cảnh: " + ", ".join(have) + "." if have else
                        "🖼 Chưa có nhân vật nào gắn tài nguyên: ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế).")
                       + (f" Chưa có ảnh tham chiếu cho: {', '.join(lack)}." if have and lack else ""))
        from core import chat_intake
        merged = chat_intake.enabled()                    # 07/10 cờ chat_first: thanh % + bảng trạng thái = bản đồ tiến độ + thẻ ảnh
        total = summ["total"] or 1
        if not merged:
            ui.progress_bar(min(done / total, 1.0), text=f"{done}/{summ['total']} cảnh có ảnh đã duyệt · {queued} chờ gen · {running} đang gen · "
                                                    f"{failed} lỗi" + (f" · ⚠ {stale} ảnh cũ" if stale else ""))
        rows = p.conn.execute(
            "SELECT j.state, j.retry_count, j.escalated, s.idx, s.id sid, (SELECT AVG(score) FROM qc_results WHERE job_id=j.id) AS qc "
            "FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type='image_gen' AND j.state NOT IN ('rejected','cancelled') "
            "ORDER BY s.idx", (pid,)).fetchall()
        status = lineage.scan(p.conn, pid)
        if rows and not merged:
            client_ready = llm_client() is not None
            def label(r):
                if r["state"] == "succeeded":
                    return "Chờ Claude kiểm tra" if client_ready else "Chờ bạn duyệt (chưa có Claude)"
                text = ui.state_label(r["state"])
                if r["state"] == "approved" and (status.get(r["sid"]) or {}).get("image_stale"):
                    text += " · ⚠ cũ"
                return text + (" · ⚠ cần xem" if r["escalated"] else "")
            if ui.v2_on():                                                        # rule 7: HTML table, folded (the cards show the same)
                from dashboard.design.screens import storyboard_cards as SB
                with st.expander(f"Bảng trạng thái từng cảnh ({len(rows)} cảnh)", expanded=False):
                    st.markdown(SB.status_table(p, pid), unsafe_allow_html=True)
            else:
                data_table([{"Cảnh": r["idx"], "Trạng thái": label(r), "Điểm QC": f"{r['qc']:.2f}" if r["qc"] is not None else "—",
                               "Đã gen lại": r["retry_count"]} for r in rows],
                             hide_index=True, width="stretch", height=min(38 * (len(rows) + 1) + 3, 230))
        fixed = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND retry_count>0 AND state NOT IN ('cancelled')", (pid,)).fetchone()[0]
        flagged = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND escalated=1 AND state='pending_review'", (pid,)).fetchone()[0]
        if autoqc.active(pid):
            st.info("🔍 **Đang tự kiểm tra ảnh** bằng Claude (so từng người với ảnh tham chiếu + Character Lock).")
        if fixed and v2:
            SB.note(f"🛠 Đã gen lại {fixed} lần" + (f" · {flagged} ảnh còn lỗi, cần xem" if flagged else ""),
                    f"🛠 Đã gen lại {fixed} lần" + (f" · {flagged} ảnh vẫn còn lỗi sau các lần sửa, đã đánh dấu để bạn xem." if flagged else "."), "sb-prog-fixed",
                    kind="warn" if flagged else "")
        elif fixed:
            st.caption(f"🛠 Đã gen lại {fixed} lần" + (f" · {flagged} ảnh vẫn còn lỗi sau các lần sửa, đã đánh dấu để bạn xem." if flagged else "."))
        problem = autoqc.last_error(pid)
        if problem:
            if v2:
                SB.note("⚠ Tự kiểm tra ảnh đã dừng", f"**Tự kiểm tra ảnh đã dừng**: {problem}", "sb-prog-autoqc", kind="warn")
            else:
                st.warning(f"⚠ **Tự kiểm tra ảnh đã dừng**: {problem}")
            if st.button("↻ Thử kiểm tra lại", key=f"autoqc_retry_{pid}"):
                autoqc.clear_error(pid)
                st.rerun()
        if queued + running == 0:
            if not v2:                                    # v2: hero + thanh dính đã nói số ảnh chờ duyệt
                st.success("Không còn ảnh nào đang chờ gen" + (f" · {counts.get('pending_review', 0)} ảnh chờ bạn duyệt." if counts.get("pending_review") else "."))
        elif proj["paused"]:
            st.warning(f"⏸ Dự án đang **tạm dừng** nên {queued + running} ảnh xếp hàng nhưng chưa gửi. Bấm **▶ Tiếp tục** ở thanh trên cùng.")
        elif running:
            st.info(f"🔄 Đang tạo {running} ảnh, {queued} đang chờ. Trang tự cập nhật; ảnh xong tự hiện.")
        elif ap_running:
            st.info("🚀 Chế độ tự động đang xử lý các ảnh này (xem tiến độ ở màn Kịch bản).")
        elif runner is None:
            _no = (f"⚠ Deepix chưa được cấu hình (thiếu `DEEPIX_TOKEN`): {queued} ảnh đang chờ. Nhập ảnh thủ công ở từng cảnh, "
                   "hoặc nhờ quản trị cấu hình Deepix.")
            if v2:
                SB.note(f"⚠ Deepix chưa cấu hình: {queued} ảnh đang chờ", _no, "sb-prog-nodeepix", kind="warn")
            else:
                st.warning(_no)
        else:
            waits = queued_waits(p, pid)                  # 08/10 lỗi 11: a queued picture may wait for its scene's anchor shot
            if waits:
                st.warning(f"⚠ {queued} ảnh đã xếp hàng nhưng chưa gửi — " + "; ".join(waits)
                           + ". Bấm ▶ Gen ảnh chỉ gửi được khi ảnh neo đã có.")
            else:
                st.warning(f"⚠ {queued} ảnh đã xếp hàng nhưng chưa gửi: bấm **▶ Gen ảnh** ở trên.")


def queued_waits(p: Pipeline, pid: int) -> list:
    """Lỗi 11 (#24): the reasons queued pictures are held in storyboard mode (scene_storyboard.wait_reason), one per anchor."""
    from core import scene_storyboard
    if not scene_storyboard.enabled():
        return []
    out, seen = [], set()
    for r in p.conn.execute("SELECT scene_id FROM jobs WHERE project_id=? AND type='image_gen' AND state='queued'", (pid,)).fetchall():
        try:
            why = scene_storyboard.wait_reason(p.conn, C.DATA, pid, r["scene_id"])
        except Exception:  # noqa: BLE001 - a hint only
            why = None
        if why and why["anchor_id"] not in seen:
            seen.add(why["anchor_id"])
            out.append(why["text"])
    return out


def step2(p: Pipeline, pid: int):
    proj = p.project(pid)
    runner = image_runner(p)
    summ = lineage.summary(p.conn, pid)
    v2 = ui.v2_on()
    if v2:
        from dashboard.design.screens import storyboard_cards as SB
        SB.hero(p, pid, summ, proj)
    else:
        step_header("Storyboard · Ảnh + QC", "mỗi cảnh một ảnh đúng nhân vật, đúng bối cảnh, đã duyệt",
                    f"{summ['images'][0]}/{summ['total']} cảnh có ảnh duyệt", summ["images"][1])
    from dashboard import next_step                                     # S9 E0.1: the next thing to do, one line
    if not v2:                                                            # v2: the shell header already shows the next step
        ui.html(next_step.band(p, pid, 2, C.DATA))
    if not C.read_only(p, pid) and autopilot_manager(C.DB, C.DATA).wake(pid, user=C.access_user()):      # S6.4: a redraw asked for while the run waits at the storyboard is sent
        _wake = "⏳ Chạy tự động đang chờ bạn ở cổng — ảnh vẽ lại bạn vừa yêu cầu đang được gửi (trong trần đã duyệt)."
        if v2:
            SB.note("⏳ Đang gửi ảnh vẽ lại bạn vừa yêu cầu", _wake, "sb-wake")
        else:
            st.caption(_wake)
    pilot_panel(p, pid)
    from core import known_issues
    active_issues = known_issues.active(p.conn, pid)
    if active_issues and v2:                             # v2: một dòng tóm tắt + MỘT expander đóng
        SB.known_issues(active_issues)
    elif active_issues:                                  # S9 E2.1: one red line always; the details fold
        st.error(f"⚠ {len(active_issues)} khâu đang dùng có lỗi đã biết ("
                 + ", ".join(f"{x['label']}: {len(x['open'])} lỗi" for x in active_issues) + ") — mở ▸ bên dưới để xem hướng sửa")
    for st_ in ([] if v2 else active_issues):         # paused / replaced stages still in use: their open faults, before any spend
        with st.expander(f"⚠ Khâu có lỗi đã biết: {st_['label']} — {len(st_['open'])} lỗi chưa sửa"):
            st.caption(st_["status"])
            for bug, fix in st_["open"]:
                st.markdown(f"- **Lỗi:** {bug}  \n  **Hướng sửa:** {fix}")
            if st_["fixed"]:
                st.caption("Đã sửa: " + "; ".join(st_["fixed"]))
    with (D_card("sb-gen") if v2 else st.container(border=True)):
        if v2:                                            # v2: hai nút; ước tính tiền một dòng; cảnh báo ưu tiên thấp vào ⓘ
            c1, c3 = st.columns([3, 2.4], vertical_alignment="center")
            c2 = c4 = None
        else:
            c1, c2, c3, c4 = st.columns([2.4, 2, 2, 2.6], vertical_alignment="center")
        est_ok = True
        est = image_estimate(p, pid)
        if runner is not None:
            est_ok = SB.show_estimate(est, runner) if v2 else show_estimate(est, runner)
        gates = batch.image_gates(p, pid)                 # the automatic run's gates apply to this button too
        if v2 and gates["warn"]:
            SB.note(f"⚠ {len(gates['warn'])} lưu ý trước khi gen ảnh", "\n".join(f"- ⚠ {w}" for w in gates["warn"]), "sb-gen-warn", kind="warn")
        else:
            for w in gates["warn"]:
                st.caption(f"⚠ {w}")
        forced = False
        if gates["block"]:
            if v2:                                        # lỗi chặn (P1) luôn hiện; lời khuyên sửa vào tooltip của ô tick
                st.warning("Gen ảnh bị chặn: " + "; ".join(gates["block"]))
                forced = st.checkbox("Tôi đã xem, vẫn gen ảnh (ghi lại vào 📊 Theo dõi)", key=f"gen_img_force_{pid}",
                                     help="Chế độ tự động sẽ DỪNG ở đây trước khi gen ảnh. Sửa ở màn Kịch bản (Character Bible / Lock).")
            else:
                st.warning("Chế độ tự động sẽ DỪNG ở đây trước khi gen ảnh: " + "; ".join(gates["block"]) + ". Sửa ở màn Kịch bản (Character Bible / Lock).")
                forced = st.checkbox("Tôi đã xem, vẫn gen ảnh (ghi lại vào 📊 Theo dõi)", key=f"gen_img_force_{pid}")
        unit = est.get("unit_over", est["unit_price"])            # S14.16: a missing price shows its high estimate
        img_price = None if unit is None else unit * est["items"]
        queued = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='queued'", (pid,)).fetchone()[0]
        if c1.button("▶ Gen ảnh các cảnh chưa có / đã cũ" + (f" · gửi {queued} ảnh đang chờ" if queued else "")   # 07/10: queued
                     + cost.price_tag(img_price, est["items"]), type="primary", key=f"gen_img_{pid}",    # redraws waited
                     disabled=(not est_ok and not queued) or (bool(gates["block"]) and not forced)):
            def go():
                r = batch.queue_images(p, pid, confirmed=forced)
                sent = runner.submit_pending(pid) if runner is not None else 0
                st.toast(f"Xếp hàng {r['created']} ảnh mới, {r['redo']} ảnh làm lại" + (f" · đã gửi {sent}" if runner else "")
                         + (" · đang gen thử" if r["pilot"] else ""))
            if act(go):
                st.rerun()
        pending = [j["id"] for j in p.conn.execute(
            "SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review' ORDER BY id", (pid,)).fetchall()]
        if v2:
            pass                                          # duyệt hàng loạt: thanh hành động dính ở cuối lưới ảnh
        elif confirm_all("approve_all", pending, f"✔ Duyệt tất cả ({len(pending)} ảnh)", f"Duyệt tất cả {len(pending)} ảnh đang chờ duyệt?", c2):
            for jid in pending:
                p.approve(jid, "user", note="gate_bulk")
            st.rerun()
        # KLD-1 (08/10): a picture failed on an outdated / missing input is not resent unchanged (Pipeline.retry refuses stale_input)
        failed = [{"id": jid} for jid in batch.provider_failures(p, pid, "image_gen")]
        if c3.button(f"↻ Gửi lại ảnh lỗi ({len(failed)}){cost.price_tag(None if unit is None else unit * len(failed), len(failed))}",
                     key="reject_all", disabled=not failed,
                     help="Gửi lại Y NGUYÊN đầu vào — chỉ dùng khi lỗi do nhà cung cấp (mạng, quá tải, không tạo task). Ảnh ra sai thì "
                          "mở ảnh và ghi câu sửa (tiếng Anh) để lần gen có đầu vào khác."):
            for j in failed:
                act(lambda: p.retry(j["id"], "gửi lại ảnh lỗi (lỗi nhà cung cấp)", by_user=True))
            st.rerun()
        mode_text = f'{ui.MODE_LABELS.get(proj["operating_mode"], proj["operating_mode"])}: ' + (
            "Claude tự duyệt ảnh đạt" if proj["operating_mode"] == "auto" else "mọi ảnh chờ bạn duyệt")
        if v2:                                            # nhà cung cấp + chế độ: một dòng, chi tiết trong ⓘ
            if runner is None:
                SB.note("ℹ Deepix chưa cấu hình — nhập ảnh thủ công cho từng cảnh", "Cách cấu hình: docs/RUNBOOK.md.\n\n" + mode_text, "sb-gen-prov")
            else:
                SB.note(f"Ảnh: {runner.provider.name}" + (" (giả lập)" if runner.provider.name.startswith("mock") else " · API thật")
                        + f" · khung {formats.label(formats.project_aspect(proj))}",
                        f"Nhà cung cấp ảnh: {runner.provider.name}" + (" (giả lập)" if runner.provider.name.startswith("mock") else " (gọi API thật, tốn credit)")
                        + f" · khung {formats.label(formats.project_aspect(proj))}\n\n" + mode_text, "sb-gen-prov")
        else:
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
    if v2:
        return grid_v2(p, pid, proj)
    if C.expert():
        qc_policy_panel(p, pid)
    if C.expert():
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
        st.caption("Chưa có ảnh nào: bấm “▶ Gen ảnh các cảnh chưa có / đã cũ” (cần khóa Character Bible ở màn Kịch bản trước).")
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


def grid_v2(p: Pipeline, pid: int, proj) -> None:
    """UI v2 (cờ ui_v2): thanh lọc → lưới thẻ kính 4 cột → MỘT thanh hành động dính → các mục gập (chính sách QC, kiểm bộ ảnh, storyboard)."""
    from dashboard.design.screens import storyboard_cards as SB
    from dashboard.design import components as D
    client = llm_client()
    to_check = p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", (pid,)).fetchone()["c"]
    if client is None and to_check:
        SB.note(f"⚠ Chưa có điểm QC cho {to_check} ảnh (chưa có Claude)",
                f"**Chưa có điểm QC**: {to_check} ảnh vừa gen chưa được chấm vì chưa có Claude ({claude_hint()}). "
                "Trong lúc đó hãy tự xem từng ảnh (đúng nhân vật? đúng bối cảnh? lỗi tay/mặt?) rồi duyệt hoặc loại.", "sb-noqc", kind="warn")
    jobs = p.conn.execute(
        "SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    if not jobs:
        st.markdown(D.empty_state("Chưa có ảnh nào", "Bấm “▶ Gen ảnh các cảnh chưa có / đã cũ” ở trên (cần khóa Character Bible ở Kịch bản trước)."),
                    unsafe_allow_html=True)
    else:
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
        with st.container(key="sb-grid"):                             # 07/10 khung hẹp: 2 thẻ/hàng dưới 1100 px (theme.css)
            for col, sid in zip(D.grid(len(shown_sids), 4), shown_sids):  # 02/10: shared n-column card grid (components.grid)
                with col:
                    SB.image_group_v2(p, pid, history[sid], proj, (stale.get(sid) or {}).get("image_stale"))
        if not shown_sids:
            st.markdown(D.empty_state("Không có ảnh nào trong bộ lọc này", "Chọn “Tất cả” để xem lại mọi cảnh."), unsafe_allow_html=True)
    SB.action_bar(p, pid)
    if C.expert():
        qc_policy_panel(p, pid)
        set_check_panel(p, pid)
    shot_storyboard_panel(p, pid, gate_button=False)


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
        retake = "" if read_only else cost.image_button_tag(image_models.of_project(proj), 1, retake_conn=p.conn)   # S14.2 A2
        if read_only:
            if j["retry_reason"]:
                st.caption(f"Lý do gen lại lúc đó: {j['retry_reason'][:160]}")
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}", width="stretch"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state in ("succeeded", "pending_review"):
            a, b, c = st.columns(3)
            st.caption("✖ Loại = gen lại 1 ảnh" + retake)
            if a.button("✔ Duyệt", key=f"a_{jid}"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if b.button("✖ Loại", key=f"r_{jid}", help="Loại và gen lại (ghi chú lý do ở khung chi tiết bên phải)"):
                act(_spin(lambda: p.reject(jid, "user", st.session_state.get(f"note_{jid}") or None)))
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
            st.caption("↻ Gửi lại 1 ảnh" + retake)
            if a.button("↻ Gửi lại", key=f"retry_{jid}", help="Gửi lại y nguyên — chỉ khi lỗi do nhà cung cấp. Muốn sửa thì 🔍 Xem → câu sửa."):
                act(lambda: p.retry(jid, "gửi lại (lỗi nhà cung cấp)", by_user=True))
                st.rerun()
            if b.button("🔍 Xem", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        else:
            if stale_reason and state == "approved" and st.button("↻ Gen lại theo nội dung mới" + retake, key=f"stale_{jid}", type="primary"):
                if act(lambda: p.reopen_approved(jid, f"Nội dung cảnh đã đổi: {stale_reason}", fix=""), "Đã xếp hàng gen lại"):
                    st.rerun()
            if j["escalated"] and st.button("↺ Làm lại từ đầu" + retake, key=f"rs_{jid}", help="Đã hết số lần thử: bắt đầu lại cảnh này"):
                if act(lambda: p.restart_job(jid), "Đã xếp hàng ảnh mới cho cảnh"):
                    st.rerun()
            if st.button("🔍 Xem", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        scene_expander(p, j["scene_id"])


def image_detail(p: Pipeline, pid: int, j, proj, on_card: bool = False):
    """`on_card` (UI v2): the review buttons and the reason inputs live on the picture's card, so this panel is the look-closer view."""
    jid, state = j["id"], j["state"]
    retake = cost.image_button_tag(image_models.of_project(proj), 1, retake_conn=p.conn)   # S14.2 A2: one picture again
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
                st.caption("🔍 Claude tự kiểm tra ảnh này ở nền (không cần bấm); xem tiến độ ở đầu màn Storyboard.")
            if C.expert():
                with st.expander("Nâng cao: prompt QC + dán điểm tay"):
                    st.code(llm_runner.plain(prompts.build_qc_bundle(p, j["scene_id"], C.DATA)), language="markdown")
                    raw = st.text_area("JSON điểm QC từ Claude", key=f"qc_{jid}", height=100)
                    if st.button("Chấm điểm", key=f"score_{jid}", disabled=not raw.strip()):
                        def score():
                            obj = llm_io.validate_qc_result(raw, prompts.qc_criteria())
                            st.toast(f"Quyết định: {p.apply_qc(jid, obj['criteria'])}")
                        if act(score):
                            st.rerun()
        if on_card:
            st.caption("Duyệt / Loại / Vẽ lại và ô lý do nằm ngay trên thẻ ảnh.")
            return
        if state in ("succeeded", "pending_review"):
            note = st.text_input("Câu sửa cho lần gen lại (đưa vào prompt — nên viết tiếng Anh, vd “Kelly wears the yellow jacket”)",
                                 key=f"note_{jid}")
            a, b = st.columns(2)
            if b.button("✖ Loại & gen lại" + retake, key=f"dr_{jid}"):
                act(_spin(lambda: p.reject(jid, "user", note or None)))
                st.rerun()
            if a.button("✔ Duyệt", key=f"da_{jid}", type="primary"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if st.button("🗑 Xóa (vào thùng rác, không gen lại)", key=f"dd_{jid}"):
                act(lambda: p.reject(jid, "user", note or "đã xóa", respawn=False))
                st.rerun()
        if state == "failed" and not j["escalated"]:
            fix = st.text_input("Câu sửa cho model (tiếng Anh) — để trống = gửi lại y nguyên (chỉ khi lỗi do nhà cung cấp)",
                                key=f"dfix_{jid}")
            if st.button(("↻ Gen lại với câu sửa" if fix.strip() else "↻ Gửi lại (lỗi nhà cung cấp)") + retake, key=f"dretry_{jid}"):
                act(lambda: p.retry(jid, "người dùng gen lại với câu sửa" if fix.strip() else "gửi lại (lỗi nhà cung cấp)", fix=fix, by_user=True))
                st.rerun()
        if j["escalated"] and st.button("↺ Làm lại từ đầu" + retake, key=f"drs_{jid}", type="primary"):
            if act(lambda: p.restart_job(jid), "Đã xếp hàng job mới cho cảnh"):
                st.rerun()
        if state == "approved":
            r_note = st.text_input("Lý do bỏ duyệt (đưa vào prompt gen lại)", key=f"rn_{jid}")
            st.caption("Bỏ duyệt: motion prompt và video làm từ ảnh này sẽ hiện ⚠ cũ để làm lại.")
            if st.button("↩ Bỏ duyệt & gen lại ảnh" + retake, key=f"reopen_{jid}"):
                if act(_spin(lambda: p.reopen_approved(jid, r_note or None)), "Đã bỏ duyệt, xếp hàng gen lại"):
                    st.rerun()



def qc_policy_panel(p: Pipeline, pid: int) -> None:
    """One QC policy instead of six knobs; the fine settings stay under 'Tùy chỉnh'."""
    proj = p.project(pid)
    current = qc_policy.current(proj)
    keys = list(qc_policy.PRESETS) + [qc_policy.CUSTOM]
    labels = {**{k: v["label"] for k, v in qc_policy.PRESETS.items()}, qc_policy.CUSTOM: "Tùy chỉnh"}
    v2 = ui.v2_on()
    with (st.expander(f"⚙ Chính sách QC ảnh — {labels[current]}", expanded=False) if v2 else st.container(border=True)):
        c1, c2 = st.columns([1.3, 4], vertical_alignment="center")
        pick = c1.selectbox("Chính sách QC ảnh", keys, index=keys.index(current), format_func=labels.get, key=f"qcpol_{pid}")
        if pick != current:
            qc_policy.apply(p, pid, pick)
            st.rerun()
        c2.caption((qc_policy.PRESETS[pick]["note"] + " ") if pick in qc_policy.PRESETS else "" + "")
        c2.caption("→ " + qc_policy.describe(proj))
        if pick == qc_policy.CUSTOM and not C.expert():  # S9 E2.3: technical settings only in expert mode
            st.caption("Chỉnh ngưỡng / số lần gen lại / tự sửa: bật ⚙ → 🧠 Chế độ chuyên gia.")
        if pick == qc_policy.CUSTOM and C.expert():
            with (st.container(border=True) if v2 else st.expander("Tùy chỉnh chi tiết", expanded=True)):   # v2: đã nằm trong expander, không lồng thêm
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
            _tip = (f"💡 {n} cảnh: nên **gen thử {pilot.SIZE} cảnh đại diện** trước (cảnh then chốt + đầu mỗi nhóm), duyệt phong cách "
                    "và nhân vật rồi mới gen phần còn lại — lỗi lộ ra ở mẫu thử thay vì ở cả lô.")
            if ui.v2_on():
                from dashboard.design.screens import storyboard_cards as SB
                with c1:
                    SB.note(f"💡 {n} cảnh: nên gen thử {pilot.SIZE} cảnh đại diện trước", _tip, "sb-pilot-tip")
            else:
                c1.caption(_tip)
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
        _msg = (f"🧪 **Gen thử trước**: chỉ cảnh {', '.join(map(str, idx))} được gen. "
                + ("Các cảnh thử đã có ảnh duyệt — xem phong cách/nhân vật ổn chưa rồi mở gen cả lô." if ready
                   else "Duyệt ảnh các cảnh này trước."))
        if ui.v2_on():
            from dashboard.design.screens import storyboard_cards as SB
            SB.note(f"🧪 Gen thử trước: chỉ cảnh {', '.join(map(str, idx))}" + (" · mẫu thử đã duyệt" if ready else " · duyệt các cảnh này trước"), _msg, "sb-pilot-msg")
        else:
            st.markdown(_msg)
        c1, c2 = st.columns(2)
        left = [] if ready else pilot.unapproved(p, pid)      # lỗi 17: a grey button says why
        if left:
            st.caption(f"Còn {len(left)} ảnh thử chưa duyệt: " + ", ".join(left) + " — duyệt xong mới mở gen cả lô.")
        if c1.button("✔ Mẫu thử ổn — gen phần còn lại", key=f"pilot_release_{pid}", type="primary", disabled=not ready,
                     help=("Còn ảnh thử chưa duyệt: " + ", ".join(left)) if left else None):
            pilot.release(p, pid)
            st.rerun()
        if c2.button("Bỏ gen thử", key=f"pilot_off_{pid}"):
            pilot.save(p, pid, {"enabled": False, "scenes": [], "released": False})
            st.rerun()


def animatic_box(p: Pipeline, pid: int) -> None:
    """S2.4 (kế hoạch sau #8): the film as it will be cut — storyboard pictures for their locked seconds with a slow move, the voice
    lines, the music and the subtitles — before any video is paid for (0 USD, ffmpeg)."""
    from core import animatic, delivery
    out_dir = delivery.output_dir(C.DATA, pid)
    done = next((os.path.join(out_dir, f) for f in ("ANIMATIC_sub.mp4", "ANIMATIC.mp4") if os.path.exists(os.path.join(out_dir, f))), None)
    c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
    _about = ("🎬 **Animatic** — xem cả phim bằng ảnh storyboard + giọng + nhạc + phụ đề theo đúng độ dài từng shot, TRƯỚC khi trả tiền "
              "video (0 USD). Ảnh tĩnh có đẩy / lia nhẹ theo chuyển động máy: để xem nhịp, thứ tự, độ dài — không phải diễn xuất.")
    if ui.v2_on():
        from dashboard.design.screens import storyboard_cards as SB
        with c1:
            SB.note("🎬 Animatic — xem nhịp cả phim · 0 USD", _about, "sb-board-anim")
    else:
        c1.caption(_about)
    if c2.button("🎬 Dựng animatic" if not done else "🔄 Dựng lại animatic", key=f"animatic_{pid}"):
        with st.spinner("Đang dựng animatic (khoảng 1 phút)…"):
            try:
                r = animatic.build(p, pid, C.DATA)
                st.session_state[f"animatic_note_{pid}"] = (
                    f"{r['shots']} shot · {r['seconds']:g} s · {r['voices']} câu thoại · " + ("có nhạc" if r["music"] else "chưa có nhạc")
                    + (" · có phụ đề" if r["subtitles"] else "") + (f" · ⚠ {len(r['missing'])} shot chưa có ảnh (thẻ tối)" if r["missing"] else ""))
                done = r["path"]
            except Exception as e:  # noqa: BLE001 - said on the page, the storyboard stays usable
                st.error(f"Không dựng được animatic: {e}")
    if done:
        note = st.session_state.get(f"animatic_note_{pid}")
        if note:
            st.caption(note)
        player, _ = st.columns([1, 2])            # a 9:16 player at full width is taller than the screen
        player.video(done)


def shot_storyboard_panel(p: Pipeline, pid: int, gate_button: bool = True) -> None:
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
    v2 = ui.v2_on()
    with st.expander(title, expanded=waiting and not v2):                  # v2: luôn đóng (nút duyệt nằm ở thanh dính)
        _about = ("Ảnh khung đầu theo thứ tự phim: kiểm tra nhân vật (so với ảnh tài nguyên bên dưới), cỡ cảnh, nhịp, liên tục TRƯỚC khi gen "
                  "video — sửa ảnh rẻ hơn nhiều so với gen lại clip. ⚑ = điểm QC cho thấy lỗi dễ thấy (Claude chưa được hiệu chỉnh: "
                  "tự xem lại, không tin mù).")
        from core import features
        off = features.pending()
        _off = ("🧪 Đang tắt tới khi thử thật đạt: " + "; ".join(v["label"] for v in off.values())
                + " (bật thử bằng FEATURE_<TÊN>=1, xem core/features.py).") if off else ""
        if v2:
            from dashboard.design.screens import storyboard_cards as SB
            SB.note("Ảnh khung đầu theo thứ tự phim — xem trước khi gen video", _about + ("\n\n" + _off if _off else ""), "sb-board-about")
        else:
            st.caption(_about)
            if off:                                # rule 5: a feature switched off until its real test is never a mystery
                st.caption(_off)
        animatic_box(p, pid)
        if waiting:
            c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
            _stop = (f"Chế độ tự động đang dừng ở đây: {storyboard_gate.summary(p, pid, C.DATA)}. Loại/gen lại shot sai ở danh sách ảnh bên trên, "
                     "rồi bấm duyệt để viết motion prompt và gen video.")
            if v2:
                with c1:
                    SB.note("⏸ Tự động đang dừng ở cổng storyboard: " + storyboard_gate.summary(p, pid, C.DATA), _stop, "sb-board-stop", kind="warn")
            else:
                c1.warning(_stop)
            if not gate_button:
                if not v2:
                    c2.caption("Nút duyệt ở thanh hành động cuối lưới ảnh.")
            elif c2.button("✔ Duyệt storyboard — gen video" + cost.video_batch_tag(p, pid), key=f"board_ok_{pid}", type="primary"):
                autopilot.resume(p, pid, p.actor)
                autopilot_manager(C.DB, C.DATA).start(pid, user=C.access_user())
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
                    _warn(col, f"⚑ {why}")


def set_check_panel(p: Pipeline, pid: int) -> None:
    """Whole-set consistency (game-asset-set-generator three-layer QA): one look at all approved pictures together."""
    approved = p.conn.execute("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='image_gen' AND state='approved'",
                              (pid,)).fetchone()[0]
    if approved < 2:
        return
    last = claude_tasks.last_set_check(C.DATA, pid)
    label = "🎨 Kiểm tra đồng bộ cả bộ ảnh" + ("" if last is None else (" — ổn" if last.get("ok") and not last.get("issues")
                                                                         else f" — {len(last.get('issues') or [])} cảnh lệch"))
    v2 = ui.v2_on()
    with st.expander(label, expanded=bool(last and last.get("issues")) and not v2):       # v2: luôn đóng; nhãn đã nói "N cảnh lệch"
        _about = ("Claude xem MỘT tấm ghép mọi ảnh đã duyệt để tìm cảnh lệch phong cách/ánh sáng/màu/nhân vật so với cả bộ "
                  "(ảnh đẹp nhưng lạc tông vẫn là lỗi). Nên chạy trước khi sang tab Motion (Storyboard).")
        if v2:
            from dashboard.design.screens import storyboard_cards as SB
            SB.note("Claude so cả bộ ảnh đã duyệt để tìm cảnh lệch tông", _about, "sb-setqc-about")
        else:
            st.caption(_about)
        client = llm_client()
        if st.button(f"🤖 Kiểm tra {approved} ảnh đã duyệt" + cost.llm_tag(cost.llm_estimate(p.conn, "setcheck", 1, images=1,
                                                                                            ledger_stage="qc"), 1),
                     key=f"setqc_{pid}", disabled=client is None, help=None if client else claude_hint()):
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
                from core import money_policy        # S14.16: the same high estimate as the money gate
                img_unit = money_policy.estimate("image", image_models.of_project(p.project(pid)))["usd"]
                if not (it.get("fix") or "").strip():
                    c2.caption("QC không nêu câu sửa — sửa prompt ảnh ở màn Kịch bản")
                elif c2.button("↻ Gen lại cảnh này" + cost.price_tag(img_unit), key=f"setqc_redo_{pid}_{n}",
                               help="Gen lại với câu sửa của QC (tiếng Anh) — đầu vào khác lần trước"):
                    act(lambda: claude_tasks.redo_from_set_check(p, pid, it["idx"], it["fix"]), "Đã xếp hàng gen lại")
                    st.rerun()


def _warn(target, text) -> None:
    """Orange warning line: Streamlit colour text is 3.4:1 on the light theme, so v2 uses the theme warn colour (class sb-warn)."""
    if ui.v2_on():
        target.markdown(f'<span class="sb-warn">{escape(str(text))}</span>', unsafe_allow_html=True)
    else:
        target.markdown(f":orange[{escape(str(text))}]")
