"""Step 4: video generation."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.widgets import auto_poll_videos, video_busy
from dashboard.design.screens.prompt_versions_ui import spin as _spin  # S14.17: spinner khi Đạo diễn viết lại prompt
from core.pipeline import MISSING_INPUT, STALE_INPUT  # KLD-1 (08/10): failures on the input are never resent unchanged


def _latest_jobs(p: Pipeline, pid: int) -> dict:
    jobs = p.conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id"
                          " WHERE j.project_id=? AND j.type='video_gen' AND j.state!='cancelled' ORDER BY s.idx, j.id",
                          (pid,)).fetchall()
    latest = {}
    for j in jobs:
        latest[j["scene_id"]] = j
    from core import takes
    for sid, j in list(latest.items()):                   # KLD-2 (08/10): the card shows the take the person chose for the shot
        pick = takes.chosen(p.conn, sid)
        if pick is not None and pick["id"] != j["id"]:
            latest[sid] = next(x for x in jobs if x["id"] == pick["id"])
    return latest


def _model_notes(p: Pipeline, pid: int, proj, on_cards=frozenset()) -> None:
    # F4 (09/10): người dùng phải THẤY model / chất lượng / giá từng shot và tự đổi được. Người dùng 09/10: model hiện DƯỚI THẺ CLIP
    # của từng cảnh (phim dài khó biết đang chỉnh cảnh nào) — bảng chỉ còn các shot CHƯA có thẻ clip (chọn model trước lần gen đầu).
    model_plan_panel(p, pid, skip=on_cards)


def step4(p: Pipeline, pid: int):
    runner = video_runner(p)
    proj = p.project(pid)
    summ = lineage.summary(p.conn, pid)
    return step4_v2(p, pid, runner, proj, summ)                       # UI v2: the only composition since S14.14 G-a (06/10)


# ---- UI v2 (S13, lane G) ---------------------------------------------------------------------------------------------------------
def step4_v2(p: Pipeline, pid: int, runner, proj, summ) -> None:
    """Hero + stats → batch bar → grid of glass clip cards → clip-set check → one 'Tinh chỉnh' card (settings, model plan, experiments).
    Layout containers are created in the visual order and filled in the order the logic needs (the switches first: they change the estimate)."""
    from dashboard.design import components as D
    from dashboard.design.screens import video_ui as V
    hero_c, bar_c, grid_c, set_c, tune_c = (st.container() for _ in range(5))
    latest = _latest_jobs(p, pid)
    with tune_c, D.card("vid-tune"):
        st.markdown(D.hero_html("Tinh chỉnh", "hiếm dùng — công tắc âm thanh / QC / chủ thể, chọn model từng cảnh, thử nghiệm"), unsafe_allow_html=True)
        with st.expander("⚙ Công tắc video (âm thanh · Claude kiểm tra · chủ thể)", expanded=False):
            _video_settings(p, pid, proj, runner)
        _model_notes(p, pid, proj, frozenset(latest))    # shots with a clip card change their model ON the card
    with bar_c, D.card("vid-bar"):
        _video_batch(p, pid, runner)
    blocked = p.conn.execute("SELECT COUNT(*) c FROM content_moderation_failures f JOIN jobs j ON j.id=f.job_id WHERE j.project_id=?",
                             (pid,)).fetchone()["c"]
    status = lineage.scan(p.conn, pid)
    ordered = sorted(latest.values(), key=lambda x: x["idx"])
    done, total, waiting, failed, busy = V.hero_stats(ordered, summ, 0.0)
    spend = V.video_spend(p.conn, pid)
    from core import chat_intake
    merged = chat_intake.enabled()                       # 07/10 cờ chat_first: bản đồ tiến độ đã nói số → chỉ nhãn khi có chuyện
    checking = sum(1 for j in ordered if j["state"] == "succeeded")
    if merged:                                           # chụp màn 07/10: '3 cần duyệt' nhưng nút 'Duyệt tất cả (2 clip)' — clip
        waiting -= checking                              # vừa gen còn đang tự kiểm (succeeded) không phải việc của người duyệt
    with hero_c, D.hero("vid"):
        pills = [(f"{waiting} cần duyệt", "warn")] if waiting else []
        pills += [(f"{checking} đang tự kiểm", "info")] if merged and checking else []
        pills += [(f"{failed} lỗi/loại", "bad")] if failed else []
        pills += [(f"{busy} đang chờ/gen", "info")] if busy else []
        pills += [(f"{blocked} bị chặn nội dung", "bad")] if blocked else []
        pills += [(f"đã chi {spend:.2f} USD", "mute")] if merged and spend else []   # thông tin riêng của thẻ số, giữ dạng nhãn
        st.markdown(D.hero_html("Video · gen & kiểm clip", "mỗi cảnh một clip đúng nhân vật, đúng vật lý, khớp motion prompt",
                                pills or [("Chưa có việc chờ", "mute")]), unsafe_allow_html=True)
        if not merged:
            c = st.columns(4)
            c[0].markdown(D.stat("Clip dùng được", f"{done} / {total}", f"{summ['videos'][1]} mục cũ" if summ["videos"][1] else ""),
                          unsafe_allow_html=True)
            c[1].markdown(D.stat("Chờ duyệt", str(waiting)), unsafe_allow_html=True)
            c[2].markdown(D.stat("Lỗi / đã loại", str(failed)), unsafe_allow_html=True)
            c[3].markdown(D.stat("Tiền video đã chi", f"{spend:.2f} USD"), unsafe_allow_html=True)
            st.markdown(D.meter(done / total if total else 0, "Tiến độ clip"), unsafe_allow_html=True)
        try:
            from core import budget
            b = budget.status(p.conn)
            if b.get("enabled") and b.get("usd"):
                st.markdown(D.meter(min(1.0, b["spent"] / b["usd"]), f"Ngân sách đợt thử: {b['spent']:.2f} / {b['usd']:.2f} USD", invert=True),
                            unsafe_allow_html=True)
        except Exception:  # noqa: BLE001 - the hero never breaks the page
            pass
    with grid_c:
        if not latest:
            st.markdown(D.empty_state("Chưa có clip nào", "Duyệt motion prompt ở tab Motion (Storyboard) rồi bấm “▶ Gen video” ở thanh trên."), unsafe_allow_html=True)
            st.button("✏ Mở Motion prompt (tab Motion)", key=f"vid-empty-go_{pid}", on_click=_go_step3)
        lines = _shot_lines(p, pid) if ordered else {}  # F4: dòng model của thẻ clip — kế hoạch model tính MỘT lần cho cả lưới
        plan_rows = _plan_rows(p, pid) if ordered else {}
        if ordered:
            _film_line(p, pid)
        from dashboard import readiness_ui              # F5-A: "sẵn sàng gen" từng clip — một lần cho cả lưới
        ready = readiness_ui.grid(p.conn, C.DATA, pid, "video", [j["scene_id"] for j in ordered], lines=lines or None) if ordered else {}
        with st.container(key="vid-grid"):              # 07/10 khung hẹp: theo HÀNG — xuống dòng vẫn đúng thứ tự cảnh (theme.css)
            for start in range(0, len(ordered), 3):
                for col, j in zip(st.columns(3), ordered[start:start + 3]):
                    with col:
                        video_card_v2(p, pid, j, runner, (status.get(j["scene_id"]) or {}).get("video_stale"), lines.get(j["scene_id"]),
                                      ready=ready.get(j["scene_id"]), plan_row=plan_rows.get(j["scene_id"]))
    with set_c:
        clip_set_panel(p, pid)
    if C.expert():
        with tune_c:
            experiments_panel(p, pid, runner)


def _video_settings(p: Pipeline, pid: int, proj, runner) -> None:
    """Audio / QC / subjects switches + which provider is used (state is saved as the boxes change)."""
    m1, m2 = st.columns(2)
    audio_on = m1.checkbox("🔊 Model tự tạo âm thanh (tiếng động, không khí)", bool(proj["video_audio"]), key=f"vaudio_{pid}",
                           help="Kling `sound` / Seedance `generate_audio`. Thoại tiếng Việt nên dùng giọng TTS ở tab Motion (Storyboard): theo blog Kling, "
                                "giọng tự sinh của Kling 3.0 chỉ có 5 ngôn ngữ (chưa có tiếng Việt). Có thể đổi giá.")
    if audio_on != bool(proj["video_audio"]):
        p.set_video_audio(pid, audio_on)
    qc_on = m2.checkbox("🔍 Claude kiểm tra từng clip (giữ nhân vật, vật lý, khớp prompt, biến dạng)", bool(proj["qc_video"]),
                        key=f"vqc_{pid}", help="Clip đạt mới vào bản ghép; theo chính sách QC của dự án (tự gen lại hay chờ bạn duyệt).")
    if qc_on != bool(proj["qc_video"]):
        p.set_project_field(pid, "qc_video", 1 if qc_on else 0)
    if subjects_visible(p, pid):
        n_subj = p.conn.execute("SELECT COUNT(*) c FROM characters WHERE project_id=? AND subject_status='active'", (pid,)).fetchone()["c"]
        from core.adapters import clipai as _clipai
        works = _clipai.SEEDANCE_REFS_WITH_FIRST_FRAME       # M7: the API drops subjects/references next to a first frame
        use_subj = st.checkbox(f"🧩 Gắn ảnh chủ thể nhân vật vào video (Seedance) — {n_subj} nhân vật có chủ thể active",
                               bool(proj["use_subjects"]) and works, key=f"vsubj_{pid}", disabled=not works,
                               help=None if works else "Chưa dùng được: Seedance từ chối ảnh chủ thể/ảnh tham chiếu khi clip đã có "
                               "khung đầu (mọi clip của pipeline đều có). Sẽ mở lại khi thử xong chế độ tham chiếu (K4).")
        if works and use_subj != bool(proj["use_subjects"]):
            p.set_use_subjects(pid, use_subj)
    if runner is None:
        st.caption("ℹ Clip AI chưa cấu hình (VIDEO_PROVIDER=clipai + CLIPAI_TOKEN, xem docs/RUNBOOK.md).")
    else:
        st.caption(f"Nhà cung cấp video: {runner.provider.name}" + (" (giả lập)" if runner.provider.name.startswith("mock") else " (gọi API thật, tốn credit)")
                   + f" · khung {formats.label(formats.project_aspect(proj))}")


def _video_batch(p: Pipeline, pid: int, runner) -> None:
    """Estimate, the batch buttons (gen / resend failed / approve all) and the notes about lip sync and the automatic check."""
    allowed_run = show_estimate(cost.estimate_videos_by_scene(p, pid, cost.load_pricing()), runner)
    # 07/10 Khủng Long Đỏ: the button sent the 'đã cũ' scenes too (scene 248, 249 ≈ 1,2 USD) and showed the alias 'seedance' (= 2.0,
    # not 2.5). Now: the list of what goes, with the REAL model + resolution; an outdated scene is remade only when ticked.
    plan = batch.video_plan(p, pid)
    new_rows = [r for r in plan if r["kind"] == "new"]
    stale_rows = {r["scene_id"]: r for r in plan if r["kind"] == "stale"}
    # 08/10 (#24): "gen thử 3 shot khó trước" had no way in the UI — the button sent every new scene. Now the new scenes are picked
    # too (all by default, so one click still sends everything) and the price follows what is picked.
    new_by_id = {r["scene_id"]: r for r in new_rows}
    all_new = len(new_rows)
    pick_key = f"gen_vid_new_{pid}"
    if st.session_state.get(pick_key + "_opts") != tuple(new_by_id):
        # 08/10 (#24): after a send the list changes; the old pick (scenes no longer new) was dropped by the widget and the box came
        # back EMPTY — the button then sent nothing. A changed list starts again from "every new scene".
        st.session_state[pick_key] = list(new_by_id)
        st.session_state[pick_key + "_opts"] = tuple(new_by_id)
    picked_new = st.multiselect(f"Cảnh mới sẽ gửi ({all_new}) — bỏ bớt để gen thử vài cảnh trước", list(new_by_id),
                                format_func=lambda sid: new_by_id[sid]["label"],
                                key=pick_key) if all_new > 1 else list(new_by_id)
    grown = [s for s in batch.with_groups(p.conn, new_rows, picked_new) if s in new_by_id]   # a shot brings its whole clip group
    if len(grown) > len(picked_new):
        st.caption("➕ Thêm cùng clip nhóm (một lần gen làm cả nhóm): "
                   + ", ".join(f"S{new_by_id[s]['idx']:02d}" for s in grown if s not in picked_new))
    new_rows = [new_by_id[s] for s in grown]
    picked = st.multiselect(f"Làm lại cảnh đã cũ ({len(stale_rows)}) — chỉ cảnh bạn chọn mới được gửi", list(stale_rows),
                            format_func=lambda sid: stale_rows[sid]["label"], key=f"gen_vid_stale_{pid}") if stale_rows else []
    send = new_rows + [stale_rows[s] for s in picked]
    if send:
        st.caption("Sẽ gửi: " + "; ".join(r["label"] for r in send))
    for line in batch.chain_waits(p, pid).values():
        st.info("⏳ " + line)
    from core import place_refs
    for line in place_refs.video_warnings(p.conn, C.DATA, pid):     # KLD-6: picture on an old 3D background / render not the plan's
        st.warning("🏞 " + line)
    c1, c2 = st.columns([2.6, 2])
    queued = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen' AND state='queued'", (pid,)).fetchone()[0]
    if send or queued or stale_rows:
        label = (f"▶ Gen video ({len(new_rows)} cảnh mới" + (f", làm lại {len(picked)}/{len(stale_rows)} cảnh đã cũ" if stale_rows else "")
                 + (f", {queued} clip đang chờ gửi" if queued else "") + ")"     # 07/10: resent / redone clips only wait in the queue
                 + (cost.video_batch_tag(p, pid) if len(new_rows) == all_new and not picked else batch.picked_tag(p, send)))
    else:                                               # điểm 6 (07/10): nothing to send → say WHY on the button, not '(0 cảnh mới)'
        from core import stage_map
        label = "▶ Gen video — " + stage_map.video_idle_reason(stage_map.build(p.conn, pid))
    if c1.button(label,
                 type="primary", key=f"gen_vid_{pid}", disabled=runner is None or not allowed_run or not (send or queued)):
        def go():
            r = batch.queue_videos(p, pid, C.DATA, only={x["scene_id"] for x in send})
            sent = runner.submit_pending(pid)
            st.toast(f"Xếp hàng {r['created']} clip mới, {r['redo']} clip làm lại · đã gửi {sent}")
        if act(go):
            st.rerun()
    # KLD-1 (08/10): job 559 của #22 hỏng vì đầu vào đã cũ nằm trong nút này → gửi lại y nguyên thành 566. Nút chỉ còn lỗi nhà cung cấp.
    failed = batch.provider_failures(p, pid)
    prices = [cost.clip_estimate(p.conn, p.job(j)["scene_id"]) for j in failed]
    total = None if any(x is None for x in prices) else sum(prices)
    if c2.button(f"↻ Gửi lại clip lỗi ({len(failed)}){cost.price_tag(total, len(failed))}", key="btn_bad_retry", disabled=not failed,
                 help="Gửi lại Y NGUYÊN đầu vào — chỉ dùng khi lỗi do nhà cung cấp (mạng, quá tải). Clip bị bộ lọc nội dung chặn "
                      "hoặc hỏng vì đầu vào đã cũ / thiếu không nằm trong nút này."):
        for jid in failed:
            act(lambda: p.retry(jid, "gửi lại clip lỗi (lỗi nhà cung cấp)", by_user=True))
        if runner is not None:
            act(lambda: runner.submit_pending(pid))   # 07/10: the retries only waited in the queue — nothing else sends them
        st.rerun()
    stale_failed = batch.input_failures(p, pid)
    if stale_failed:
        st.warning(f"⚠ {len(stale_failed)} clip hỏng vì đầu vào đã cũ / thiếu — không gửi lại y nguyên; xếp hàng lại từ đầu vào mới: "
                   + "; ".join(f"{C.unit_code(p, pid, r['idx'])} ({escape((r['note'] or '')[:80])})" for r in stale_failed))
        s_prices = [cost.clip_estimate(p.conn, r["scene_id"]) for r in stale_failed]
        s_total = None if any(x is None for x in s_prices) else sum(s_prices)
        if st.button(f"↻ Xếp hàng lại từ đầu vào mới ({len(stale_failed)}){cost.price_tag(s_total, len(stale_failed))}",
                     key=f"stale_requeue_{pid}", disabled=runner is None,
                     help="Job cũ đóng lại (chưa từng gửi, không tốn tiền); job mới dùng ảnh + motion prompt đang duyệt. Shot chưa duyệt "
                          "đủ đầu vào thì chỉ báo, không gửi."):
            out = {}
            if act(lambda: out.update(batch.requeue_input_failures(p, pid))):
                sent = runner.submit_pending(pid) if out.get("created") else 0
                st.toast(f"Xếp hàng {out.get('created', 0)} clip từ đầu vào mới · đã gửi {sent}"
                         + (" · chưa gửi: " + ", ".join(f"{C.unit_code(p, pid, i)} ({str((out.get('reasons') or {}).get(i, 'chưa đủ đầu vào'))[:80]})"
                                                       for i in out["not_ready"]) if out.get("not_ready") else ""))
            st.rerun()
    from core import lipsync as _lipsync
    if _lipsync.enabled() and not _lipsync.post_available():
        notes = [(r["idx"], _lipsync.no_post_note(json.loads(r["data"] or "{}")))
                 for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
        notes = [(i, n) for i, n in notes if n]
        if notes:                                   # S9 E4.3: no lip sync is a fault the person named — one line always
            st.warning(f"👄 {len(notes)} shot có thoại chưa khớp môi (không dùng sync.so) — mở ▸ để xem từng shot")
            with st.expander(f"👄 Khớp môi: {len(notes)} shot không có khớp môi sau (không dùng sync.so)"):
                for i, n in notes:
                    st.caption(f"{C.unit_code(p, pid, i)}: {n}")
    _draft_preview(p, pid)                               # 09/10: ghép xem cả bản nháp (0 USD), trước khi duyệt / gen bản cao
    from dashboard import quality_ui                      # N4: nút gom "⬆ Gen bản cao N cảnh — ≈ X USD (tham khảo)"
    if quality_ui.enabled():
        quality_ui.batch_block(p, pid, runner)
    waiting = [j["id"] for j in p.conn.execute(
        "SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='pending_review' ORDER BY id", (pid,)).fetchall()]
    if waiting and confirm_all(f"vid_ok_all_{pid}", waiting, f"✔ Duyệt tất cả ({len(waiting)} clip)",
                               f"Duyệt tất cả {len(waiting)} clip đang chờ duyệt?"):
        for jid in waiting:
            p.approve(jid, "user", note="gate_bulk")
        st.rerun()
    if video_busy(p.conn, pid):
        auto_poll_videos(pid)
    problem = autoqc.video_last_error(pid)
    if problem:
        st.warning(f"⚠ Tự kiểm tra video đã dừng: {problem}")
        if st.button("↻ Thử kiểm tra lại", key=f"vqc_retry_{pid}"):
            autoqc.clear_video_error(pid)
            st.rerun()


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
                   "khớp nhau không (clip do các model khác nhau làm dễ lệch). Nên chạy trước khi dựng ở màn Bản giao.")
        client = llm_client()
        if st.button(f"🤖 Kiểm tra {usable} clip" + cost.llm_tag(cost.llm_estimate(p.conn, "clipcheck", 1, images=2, ledger_stage="qc"), 1),
                     key=f"clipqc_{pid}", disabled=client is None, help=None if client else claude_hint()):
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
                if job and not (it.get("fix") or "").strip():
                    c2.caption("QC không nêu câu sửa — sửa motion prompt ở tab Motion (Storyboard)")
                elif job and c2.button("↻ Gen lại clip này" + cost.price_tag(cost.clip_estimate(p.conn, p.job(job["id"])["scene_id"])),
                                       key=f"clipqc_redo_{pid}_{n}", help="Gen lại với câu sửa của QC (tiếng Anh) — đầu vào khác lần trước"):
                    act(_spin(lambda: regen.regenerate_video(p, C.DATA, job["id"], f"Đồng bộ cả bộ clip: {it['problem']}", fix=it["fix"])),
                        "Đã xếp hàng gen lại")
                    st.rerun()



def _go_step3() -> None:
    C.go_screen(None, "storyboard", tab=1)                # the Motion tab of the Storyboard screen


def model_plan_panel(p: Pipeline, pid: int, skip=frozenset()) -> None:
    """Which model for which scene, from the ClipAI model guide (no fixed default). F4 (09/10): MỘT dòng mỗi shot
    "model · nháp → cao · giữ nội dung? · ≈ USD · đề xuất/bạn chọn" (dashboard.model_line) + MỘT nút "Đổi" (popover: model, độ phân
    giải, đường chất lượng); cảnh báo E1 ngay trên dòng; dòng ước tính cả phim trên đầu bảng. Giữ key cũ vm_{pid}_{sid}, qpath_{sid}."""
    from dashboard import model_line, quality_ui
    from dashboard.design import components as D
    pricing = cost.load_pricing()
    rows = model_router.plan(p.conn, pid, pricing)
    ready = {r["scene_id"] for r in llm_io.ready_for_video(p, pid, include_stale=True)}
    has_mp = {r["scene_id"] for r in p.conn.execute("SELECT m.scene_id FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?", (pid,))}
    rows = [r for r in rows if r["scene_id"] in has_mp and r["scene_id"] not in skip]
    proj = p.project(pid)
    prio = model_router.priority_of(proj)
    profiles = model_router.load_profiles()
    two_tier = quality_ui.enabled()
    with st.expander(f"🎛 Model cho từng cảnh — ưu tiên “{profiles['priorities'][prio]['label']}”", expanded=bool(rows)):
        if C.expert():
            st.caption("Theo slide ClipAI “Hôm nay tôi chọn mô hình video như thế nào”: cảnh then chốt / phức tạp / có video tham chiếu → Seedance 2.5; "
                       "cảnh thường → Seedance 2.0 hoặc 2.0 Fast; đối thoại nhiều nhân vật / cảnh chuyển tiếp rẻ → Kling 3.0 Omni. "
                       "MiniMax H3 và Seedance 2.0 Mini chỉ có trên web ClipAI (không gen tự động được). Đổi ưu tiên ở màn Kịch bản · 📐 Định dạng.")
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
        if skip:
            st.caption("🎛 Shot đã có clip: model hiện và đổi ngay dưới thẻ clip của shot đó (ô chọn Model / Cấu hình).")
        if not rows:
            if not skip:
                st.caption("Chưa có motion prompt nào: viết ở tab Motion (Storyboard).")
            return
        _film_line(p, pid)
        api = model_router.api_models(profiles)
        options = [None] + list(api)
        ratio = model_line._ratio(p.conn, pid)
        for r in rows:
            line = model_line.shot_line(p.conn, pid, r["scene_id"], r, ratio)
            text = f"**{C.unit_code(p, pid, r['idx'])}**" + ("" if r["scene_id"] in ready else " ·")
            if line["warning"]:
                text += " " + D.colored("warn", "⚠ " + line["warning"])
            st.markdown(text, unsafe_allow_html=True)
            _model_change(p, pid, r, line, options, two_tier)
        if C.expert():
            totals = {k: model_router.total(model_router.plan(p.conn, pid, pricing, priority=k)) for k in model_router.PRIORITIES}
            st.caption("So sánh tổng (chưa tính gen lại): " + " · ".join(
                f"{profiles['priorities'][k]['label']} ≈ " + (f"\\${v:.2f}" if v is not None else "?") for k, v in totals.items()))


def _model_change(p: Pipeline, pid: int, r, line, options, two_tier: bool) -> None:
    """The shot's model pickers, shown DIRECTLY (người dùng 09/10: không chữ "Đổi" — các ô chọn hiện sẵn, mặc định là model đề xuất,
    bấm vào để đổi model / cấu hình): model + đường chất lượng (two-tier) cạnh nhau; keys vm_{pid}_{sid}, qpath_{sid} — one place per
    shot: the clip card when it has one, else the Model table."""
    from dashboard import quality_ui
    cur = r["model"] if r["source"] == "override" else None
    c_model, c_path = st.columns(2) if two_tier else (st.container(), None)
    pick = c_model.selectbox("Model", options, index=options.index(cur) if cur in options else 0, key=f"vm_{pid}_{r['scene_id']}",
                        # KLD-23: the real model + resolution ("Seedance 2.0 · 720p"), never the bare alias / a vague label
                        # 09/10: "Đề xuất" = what the shot really gets without a pick (after cheap mode / E1), never the raw recommendation
                        format_func=lambda a, r=r: "Đề xuất: " + (model_router.label(r["model"], r.get("resolution")) if r["source"] != "override"
                                                                  else model_router.label(r["recommended"]["model"], r["recommended"].get("resolution")))
                        if a is None else model_router.label(a, r.get("resolution") if a == r["model"] else None))
    if pick != cur:
        act(lambda: model_router.set_override(p.conn, r["scene_id"], pick, p=p))
        st.rerun()
    if two_tier:
        qcur = quality_ui.quality_path(p.conn, r["scene_id"])
        keys = list(quality_ui.PATHS)
        qpick = c_path.selectbox("Cấu hình", keys, index=keys.index(qcur), key=f"qpath_{r['scene_id']}",
                             format_func=lambda k: {"auto": "Tự động (theo Đạo diễn)", "draft_first": "Nháp trước",
                                                    "direct": "Thẳng bản cao"}[k],
                             help="Nháp trước = nháp rẻ → bạn duyệt → nâng bản cao (chỉ Seedance 2.5 giữ nội dung nháp). "
                                  "Thẳng bản cao = gen một lần. Tự động = theo nhãn độ khó của Đạo diễn.")
        if qpick != qcur and quality_ui.set_quality_path(p.conn, r["scene_id"], qpick):
            st.rerun()
    if line:
        st.caption("🎛 " + line["text"], help=("Vì sao: " + line["why"]) if line.get("why") else None)


def _plan_rows(p: Pipeline, pid: int) -> dict:
    """{scene_id: model_router.plan row} — once per grid (the card's "Đổi")."""
    try:
        return {r["scene_id"]: r for r in model_router.plan(p.conn, pid, cost.load_pricing())}
    except Exception:  # noqa: BLE001 - no picker rather than a broken grid
        return {}


def _film_line(p: Pipeline, pid: int) -> None:
    from dashboard import model_line
    try:
        film = model_line.film_line(p.conn, pid)
        st.caption(f"🎬 **{film['text']}**", help=film["help"])
    except Exception:  # noqa: BLE001 - an estimate never breaks the screen
        pass


def _card_model(p: Pipeline, pid: int, scene_id: int, line, plan_row) -> None:
    """09/10 (người dùng): model của cảnh hiện NGAY DƯỚI thẻ clip — một dòng + nút "Đổi" (không ở bảng riêng)."""
    from dashboard import model_line, quality_ui
    from dashboard.design import components as D
    if line is None:
        try:
            line = model_line.shot_line(p.conn, pid, scene_id)
        except Exception:  # noqa: BLE001 - information only
            line = None
    if plan_row is not None:
        api = model_router.api_models(model_router.load_profiles())
        _model_change(p, pid, plan_row, line, [None] + list(api), quality_ui.enabled())
    elif line:
        st.caption("🎛 " + line["text"])
    if line and line.get("warning"):
        st.markdown(D.colored("warn", "⚠ " + line["warning"]), unsafe_allow_html=True)


def _shot_lines(p: Pipeline, pid: int) -> dict:
    """F4: {scene_id: model_line.shot_line} cho thẻ clip khi cờ two_tier_quality bật ({} khi tắt / đọc lỗi — thẻ tự tính hoặc như cũ)."""
    from dashboard import model_line, quality_ui
    if not quality_ui.enabled():
        return {}
    try:
        return model_line.shot_lines(p.conn, pid)
    except Exception:  # noqa: BLE001 - the line is information: never breaks the grid
        return {}


def video_card_v2(p: Pipeline, pid: int, j, runner, stale_reason, line=None, ready=None, plan_row=None) -> None:
    """One clip as a glass card (UI v2): player + first frame, state pill, measured notes as chips/rows, model/length/price line and
    the four actions always visible (✔ Duyệt · ↻ Gen lại · ✏ Sửa motion prompt · ✖ Loại); the rare ones sit in one “Thêm” popover.
    Every widget key of the classic card is kept (va_, vr_rej_, vregen_, vr_, vfix_, vfixtxt_, vnote_, vc_, vrl_, vrs_, vkeep_)."""
    from core import qc_scene
    from dashboard.design import components as D
    from dashboard.design.screens import video_ui as V
    jid, state = j["id"], j["state"]
    clip = j["result_path"] if state in ("succeeded", "pending_review", "approved") and j["result_path"] and os.path.exists(j["result_path"]) else None
    blocked = p.conn.execute("SELECT error_message FROM content_moderation_failures WHERE job_id=? ORDER BY id DESC LIMIT 1", (jid,)).fetchone()
    scores = qc_scores(p, jid)
    price = cost.clip_estimate(p.conn, j["scene_id"])
    tag = cost.price_tag(price)                                            # M8: price on every button that sends a clip again
    reviewable = state in ("pending_review", "succeeded")
    with D.card(f"vid-{jid}"):
        st.markdown(f"**{C.unit_label(p, j['project_id'], j['idx'])}**")
        pills = V.clip_pill(state)
        if j["escalated"]:
            pills += " " + D.pill("Cần xem", "warn")
        if blocked:
            pills += " " + D.pill("Bị chặn nội dung", "bad")
        if stale_reason:
            pills += " " + D.pill(f"Cũ · {stale_reason}", "warn")
        if scores:
            mean = sum(s["score"] for s in scores) / len(scores)
            pills += " " + D.pill(f"QC {mean:.2f}", V.score_kind(mean, p.project(pid)["qc_auto_pass_threshold"]))
        st.markdown(pills, unsafe_allow_html=True)
        from dashboard import readiness_ui                # F5-A: một dòng "sẵn sàng gen" + chi tiết (không nút mới)
        readiness_ui.line(ready)
        _card_model(p, pid, j["scene_id"], line, plan_row)   # 09/10: model của cảnh dưới thẻ, nút "Đổi" tại chỗ
        from dashboard import quality_ui                  # N4: 2 bậc chất lượng — chỉ khi cờ two_tier_quality bật và có core.quality_tier
        if quality_ui.enabled():
            quality_ui.card_block(p, pid, j["scene_id"], runner, line=line)
        if clip:
            left, right = st.columns(2)
            src = job_image(pid, j["source_job_id"]) if j["source_job_id"] else None
            if src:
                with left:
                    st.caption("Ảnh khung đầu")
                    show_image(src, width="stretch")
            with (right if src else st.container()):
                try:
                    st.video(clip)
                except Exception:  # noqa: BLE001 - unreadable file: say so instead of breaking the page
                    st.caption(f"⚠ Không phát được video: {os.path.basename(clip)}")
        elif state in ("queued", "running", "retryable"):
            st.markdown(D.shimmer(150), unsafe_allow_html=True)
        mp = p.conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=?", (j["scene_id"],)).fetchone()
        st.markdown(V.meta_line(model_router.job_label(p.conn, jid, j["model"]) if j["model"] else None, mp["duration_sec"] if mp else None, price, j["retry_count"]), unsafe_allow_html=True)
        if scores:                                                       # P3: the criteria behind ⓘ, one line outside
            D.line(V.scores_summary(scores, CRITERIA_LABEL), V.scores_md(scores, CRITERIA_LABEL), f"vid-{jid}-qc")
        try:
            flags = qc_scene.flags_of(C.DATA, pid, j["source_job_id"]) if j["source_job_id"] else []
        except Exception:  # noqa: BLE001 - a missing/broken layer-0 file never hides the clip
            flags = []
        if flags:
            D.line(V.layer0_summary(flags), V.layer0_md(flags), f"vid-{jid}-l0")
        from dashboard.design.screens import prompt_versions_ui     # S14.17: the Director rewrote the motion prompt → old/new + ↩
        prompt_versions_ui.panel(p, j["scene_id"], "video", act)
        qnote = p.conn.execute("SELECT note FROM review_log WHERE job_id=? AND note IS NOT NULL AND note!='' ORDER BY id DESC LIMIT 1", (jid,)).fetchone()
        if qnote:
            D.line(V.note_summary("Ghi chú QC", qnote["note"]), qnote["note"], f"vid-{jid}-note")
        if blocked:
            D.line('<span class="vid-sum">Đừng gen lại nguyên prompt — sửa motion prompt trước</span>',
                   "Bị bộ lọc nội dung chặn: gen lại nguyên prompt sẽ lại bị chặn và tốn credit — sửa motion prompt trước.\n\n"
                   + str(blocked["error_message"] or ""), f"vid-{jid}-blk")
        if state == "pending_review":
            st.text_input("Câu sửa cho lần gen lại (nên viết tiếng Anh)", key=f"vnote_{jid}")
        vfix = ""
        input_note = p.failure_note(jid) if state == "failed" else None
        stale_input = bool(input_note) and input_note.startswith((STALE_INPUT, MISSING_INPUT))
        can_resend = state == "failed" and not blocked and not j["escalated"] and not stale_input
        if stale_input:                                   # KLD-1 (08/10): never resent unchanged — the batch bar requeues it from new inputs
            st.caption("⚠ Hỏng vì đầu vào đã cũ / thiếu — không gửi lại y nguyên. Dùng “↻ Xếp hàng lại từ đầu vào mới” ở thanh trên.")
        if can_resend:
            vfix = st.text_input("Câu sửa (tiếng Anh) — trống = gửi lại y nguyên, chỉ khi lỗi do nhà cung cấp", key=f"vfixtxt_{jid}")
        # ---- the four actions, always visible -----------------------------------------------------------------------------------
        r1, r2 = st.columns(2)
        if r1.button("✔ Duyệt clip", key=f"va_{jid}", type="primary", disabled=not reviewable, width="stretch"):
            act(lambda: p.approve(jid, "user"))
            st.rerun()
        if can_resend:
            if r2.button(("↻ Gen lại với câu sửa" if vfix.strip() else "↻ Gửi lại") + tag, key=f"vr_{jid}", width="stretch",
                         help="Lỗi do nhà cung cấp: gửi lại, có thể kèm câu sửa."):
                act(lambda: p.retry(jid, "người dùng gen lại với câu sửa" if vfix.strip() else "gửi lại (lỗi nhà cung cấp)", fix=vfix, by_user=True))
                st.rerun()
        elif clip and state in ("succeeded", "pending_review", "approved"):
            if r2.button(("↻ Gen lại theo ảnh/prompt mới" if stale_reason else "↻ Gen lại video") + tag, key=f"vregen_{jid}", width="stretch",
                         help="Clip này vào thùng rác (giữ 30 ngày) và xếp hàng video mới. Muốn đổi cách quay thì sửa motion prompt trước."):
                if act(lambda: regen.regenerate_video(p, C.DATA, jid, f"làm lại vì {stale_reason}" if stale_reason else None),
                       "Đã xếp hàng gen lại video"):
                    st.rerun()
        elif not stale_input:
            r2.button("↻ Gen lại", key=f"vr_{jid}", disabled=True, width="stretch",
                      help="Chưa có clip để gen lại" if not blocked else "Bị chặn nội dung: sửa motion prompt rồi mới gen lại")
        readiness_ui.reason(ready)                       # F5-A: shot red → lý do ngay dưới nút gen lại
        r3, r4 = st.columns(2)
        r3.button("✏ Sửa motion prompt", key=f"vfix_{jid}", on_click=_go_step3, width="stretch",
                  help="Mở tab Motion của Storyboard (tab Motion).")
        if r4.button("✖ Loại & gen lại" + tag, key=f"vr_rej_{jid}", disabled=not reviewable, width="stretch",
                     help="Loại clip này và xếp hàng gen lại (kèm câu sửa nếu bạn nhập)."):
            act(_spin(lambda: p.reject(jid, "user", st.session_state.get(f"vnote_{jid}") or None)))
            if runner is not None:
                act(lambda: runner.submit_pending(j["project_id"]))   # 07/10: the redo only waited in the queue
            st.rerun()
        # ---- rare actions: one popover ------------------------------------------------------------------------------------------
        can_cancel = state in ("queued", "running")
        can_relink = state == "failed" and runner is not None and _written_off(p, j)
        can_restart = bool(j["escalated"] and not blocked)
        if can_cancel or can_relink or can_restart:
            with st.popover("⋯ Thêm", width="stretch"):
                if can_cancel and st.button("■ Hủy", key=f"vc_{jid}"):
                    act(lambda: runner.cancel_job(jid) if runner else p.cancel(jid))
                    st.rerun()
                if can_relink and st.button("🔎 Tìm task thật (không gửi lại)", key=f"vrl_{jid}",
                                            help="ClipAI đôi khi tạo task với mã khác mã đã trả về (W12b). Tìm theo prompt đã gửi; thấy thì nối lại "
                                                 "và tải clip, không tốn thêm tiền."):
                    found = []
                    if act(lambda: found.append(runner.relink_failed(jid))) and found[0]:
                        st.toast(f"Đã nối lại task thật → job {found[0]}; clip sẽ tải ở lần kiểm tra tới")
                        st.rerun()
                    elif found:
                        st.toast("Không thấy task nào khớp prompt — có thể ClipAI thật sự chưa tạo; bấm Gen lại")
                if can_restart and st.button("↺ Làm lại từ đầu" + tag, key=f"vrs_{jid}",
                                             help="Đã hết số lần thử: bắt đầu lại với một job video mới"):
                    if act(lambda: p.restart_job(jid), "Đã xếp hàng video mới"):
                        st.rerun()
        keep = p.keepable_rejected(j["scene_id"]) if state in ("rejected", "queued", "failed", "retryable") else None
        if keep is not None:
            kept = qc_scores(p, keep["id"])
            mean = sum(s["score"] for s in kept) / len(kept) if kept else None
            with st.expander("👀 Bản QC đã loại" + (f" (QC {mean:.2f})" if mean is not None else "") + " — xem và giữ lại nếu dùng được",
                             expanded=state == "rejected"):
                show_video(keep["result_path"])
                if keep["retry_reason"] or kept:
                    st.caption("Lý do QC loại: " + escape((p.conn.execute("SELECT note FROM review_log WHERE job_id=? ORDER BY id DESC LIMIT 1",
                                                                          (keep["id"],)).fetchone() or {"note": ""})["note"] or "")[:400])
                if st.button("✔ Vẫn dùng bản này", key=f"vkeep_{keep['id']}", type="primary",
                             help="Bạn là người quyết định cuối: giữ clip QC đã loại, hủy lần gen lại đang chờ (không tốn thêm credit)."):
                    if act(lambda: p.keep_rejected(keep["id"]), "Đã giữ clip"):
                        st.rerun()
        _take_versions(p, j)     # 09/10 (người dùng): chip v1 v2 v3 như thẻ ảnh; bỏ thanh "✂ Điểm cắt clip nhóm" khỏi thẻ
        scene_expander(p, j["scene_id"], with_motion=True)


GROUP_CUT_BY = {"detected": "dò được bằng scdet", "refined": "dò lại quanh mốc dự kiến", "plan": "theo số giây dự kiến (không dò được)",
                "user": "người dùng chỉnh tay"}


def group_cut_panel(p: Pipeline, j) -> None:
    """08/10 (#24 S08–S09): the cut seconds of a group clip, set by hand — the shot files are cut again from <name>_group.mp4, 0 USD
    (core.seedance_refs.recut). Shown on every shot card of the group; its keys carry the card's job id."""
    from core import seedance_refs
    leader_id = j["group_leader"] if "group_leader" in j.keys() and j["group_leader"] else j["id"]
    leader = p.job(leader_id)
    whole = seedance_refs.group_whole(leader)
    members = seedance_refs.group_members(p.conn, leader_id) if whole else []
    if len(members) < 2:
        return
    saved = seedance_refs.saved_cuts(whole) or {}
    length = ffmpeg_studio.probe_duration(whole) or 0.0
    cuts = list(saved.get("cuts") or [])
    if len(cuts) != len(members) - 1:                  # an older split: start from the parts' lengths
        cuts, t = [], 0.0
        for m in members[:-1]:
            t += ffmpeg_studio.probe_duration(m["result_path"]) if m["result_path"] and os.path.exists(m["result_path"]) else 0.0
            cuts.append(round(t, 3))
    shots = ", ".join(f"S{m['idx']:02d}" for m in members)
    with st.expander(f"✂ Điểm cắt clip nhóm {shots} — chỉnh tay (0 USD)", expanded=saved.get("by") == "plan"):
        how = GROUP_CUT_BY.get(saved.get("by"), "chưa ghi")
        st.caption(f"Clip nhóm gốc {length:.2f} s · đang cắt ở {cuts} s ({how})"
                   + (f" · dự kiến {saved['planned']} s" if saved.get("planned") else "")
                   + ". Xem clip gốc, nhập giây chuyển sang shot sau rồi bấm cắt lại — không gửi lại, không tốn tiền; "
                     "bản đã duyệt vẫn giữ trạng thái, shot đã có bản gen mới thì không bị ghi đè.")
        show_video(whole)
        cols = st.columns(len(cuts))
        new = [cols[k].number_input(f"S{members[k]['idx']:02d} → S{members[k + 1]['idx']:02d} (giây)", min_value=0.0,
                                    max_value=float(length), value=float(cuts[k]), step=1 / 24, format="%.3f",
                                    key=f"gcut_{j['id']}_{k}") for k in range(len(cuts))]
        if st.button("✂ Cắt lại theo số giây này (0 USD)", key=f"gcut_go_{j['id']}", width="stretch"):
            out = []
            if act(lambda: out.append(seedance_refs.recut(p, leader_id, new)), "Đã cắt lại clip nhóm"):
                if out and out[0]["skipped"]:
                    st.toast(f"Shot {out[0]['skipped']} đã có bản gen mới — không ghi đè")
                st.rerun()


def _draft_preview(p: Pipeline, pid: int) -> None:
    """09/10 (người dùng: "chưa có nút gộp xem bản draft"): một nút ghép bản đang dùng của mọi shot — kể cả nháp / chờ duyệt — thành
    một video để xem trọn bộ (core.final_cut.draft_preview, 0 USD, không phải bản giao)."""
    from core import final_cut
    out = os.path.join(C.DATA, str(pid), "output", "xem_nhap.mp4")
    if st.button("🎞 Ghép xem bản nháp (0 USD)", key=f"draft_cut_{pid}",
                 help="Ghép nhanh clip đang dùng của từng shot (cả nháp, cả bản chờ duyệt) theo thứ tự để xem trọn phim — không nhạc, "
                      "không phải bản giao, không tốn credit."):
        res = []
        if act(lambda: res.append(final_cut.draft_preview(p, C.DATA, pid, out))) and res:
            st.session_state[f"draft_cut_info_{pid}"] = res[0]
    info = st.session_state.get(f"draft_cut_info_{pid}")
    if info and os.path.exists(info["path"]):
        st.caption(f"Bản ghép xem: {len(info['shots'])} shot · {info['seconds']:.1f} s"
                   + (f" · thiếu clip shot {', '.join(str(i) for i in info['missing'])}" if info["missing"] else ""))
        show_video(info["path"])


def _take_versions(p: Pipeline, j) -> None:
    """09/10 (người dùng, #24): các bản gen của shot còn tệp riêng = chip v1 v2 v3… như thẻ ảnh (thay expander "🎞 Bản khác của shot").
    Bấm một chip → xem bản đó ngay dưới hàng chip + "✔ Dùng bản này cho shot" (KLD-2: chọn bản cho chuỗi nối và bản dựng, 0 USD).
    Chip đậm = bản đang dùng cho shot."""
    from core import takes
    from dashboard.design.screens import older_take_ui
    cur = takes.used(p.conn, j["scene_id"])
    rows = sorted(list(takes.candidates(p.conn, j["scene_id"])) + ([cur] if cur is not None else []), key=lambda r: r["id"])
    if len(rows) < 2:
        return
    key = f"vtake_{j['scene_id']}"
    ids = [r["id"] for r in rows]
    pick = st.session_state.get(key)
    if pick not in ids:
        pick = cur["id"] if cur is not None else ids[-1]
    st.caption(f"🎞 {len(rows)} bản của shot — chip đậm là bản đang dùng; bấm để xem / chọn bản khác (0 USD)")
    with st.container(key=f"vtakes-{j['scene_id']}"):
        cols = st.columns(len(rows), gap="small")
        for col, r, n in zip(cols, rows, range(1, len(rows) + 1)):
            used_now = cur is not None and r["id"] == cur["id"]
            if col.button(f"v{n}", key=f"vtk_{j['scene_id']}_{r['id']}", type="primary" if used_now else "secondary",
                          help=f"Job {r['id']} · {ui.state_label(r['state'], 'video_gen')}" + (" · đang dùng" if used_now else "")):
                st.session_state[key] = r["id"]
                st.rerun()
    o = next(r for r in rows if r["id"] == pick)
    if cur is not None and o["id"] == cur["id"]:
        return                                   # the card above already plays the take in use
    kept = qc_scores(p, o["id"])
    mean = sum(s["score"] for s in kept) / len(kept) if kept else None
    st.caption(f"v{ids.index(o['id']) + 1} · job {o['id']} · {ui.state_label(o['state'], 'video_gen')}"
               + (f" · QC {mean:.2f}" if mean is not None else "")
               + (f" · {model_router.job_label(p.conn, o['id'], o['model'])}" if o["model"] else ""))
    show_video(o["result_path"])
    if o["state"] in older_take_ui.USABLE:      # 08/10: the newer takes are closed without a redo; asks first if the used one is approved
        older_take_ui.use_button(p, o, cur, label="✔ Dùng bản này cho shot", key=f"vuse_{o['id']}")
    elif st.button("✔ Dùng bản này cho shot", key=f"vuse_{o['id']}",
                   help="Tệp của bản này thành clip của shot; bản đang dùng vào thùng rác (vẫn chọn lại được). Không tốn credit."):
        if act(lambda: takes.choose(p, C.DATA, o["id"]), "Đã đổi bản dùng cho shot"):
            st.rerun()


def experiments_panel(p: Pipeline, pid: int, runner) -> None:
    """Experiment (off the main path): Kling multi-shot for one sequence, to compare continuity with the per-scene clips."""
    from core import experiments, shots
    quality_samples_panel(p, pid, runner)
    items = experiments.load(C.DATA, pid)
    if shots.active(p, pid):       # v3 shot projects have the real multi-shot (shot_mode); only the grouped-generation tests are shown
        group_tests_panel([e for e in items if e.get("kind") == "group_test"])
        return
    seqs = experiments.sequences(p, pid)
    if not seqs and not items:
        return
    with st.expander(f"🧪 Thử nghiệm: Kling multi-shot cho một nhóm cảnh ({len(items)})"):
        st.caption("Gen cả một nhóm cảnh liên tiếp trong MỘT lần (Kling 3.0 Omni, tối đa 15 giây) để so độ liền mạch với clip từng cảnh. "
                   "Kết quả KHÔNG tự vào bản ghép; tốn credit như một clip cùng độ dài.")
        if seqs and runner is not None:
            seq = st.selectbox("Nhóm cảnh", list(seqs), key=f"ms_seq_{pid}",
                               format_func=lambda k: f"Nhóm {k}: cảnh " + ", ".join(str(s["idx"]) for s in seqs[k]))
            est = experiments.estimate(p, pid, seq)
            price = f"≈ ${est['usd']:.2f}" if est["usd"] is not None else "chưa có giá — trần ngân sách sẽ từ chối"
            if confirm_all(f"ms_go_{pid}", [seq], f"🧪 Gen thử multi-shot ({est['seconds']} s, {price})",
                           f"Gen thử multi-shot {est['seconds']} s cho nhóm này? Tốn {price}, tính vào trần ngân sách thử", st,
                           "Có, gen thử"):
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


def quality_samples_panel(p: Pipeline, pid: int, runner) -> None:
    from core import features, quality_samples as q
    if not features.on("seedance_sample_mode"):
        return
    with st.expander("🧪 So độ nét · Seedance 2.5", expanded=True):
        st.caption("Thử shot không thoại, không video tham chiếu, 4 giây: A là 720p để phóng AI; B là bản mẫu 480p rồi bản cuối 1080p; C là gen thẳng 1080p (chưa biết API có nhận, nếu từ chối thì ghi lỗi, không tính tiền). "
                   "Giữ ảnh và motion đã duyệt. Kết quả thử riêng; trần cả phép so 4 USD, mỗi bước gửi một lần.")
        rows = q.candidates(p, pid, C.DATA)
        items = q.load(C.DATA, pid)
        if rows and runner is not None:
            sid = st.selectbox("Shot thử độ nét", [r["id"] for r in rows], key=f"quality_scene_{pid}",
                               format_func=lambda x: f"Shot {next(r['idx'] for r in rows if r['id'] == x)}")
            for kind in ("direct", "draft", "final", "high"):
                entry = next((e for e in items if e["scene_id"] == sid and e["kind"] == kind), None)
                if entry:
                    st.caption(f"{q.LABELS[kind]} · {ui.state_label(entry['state'])}" +
                               (f" · {escape(entry.get('message') or '')}" if entry.get("message") else ""))
                    if entry.get("charge_uncertain"):
                        st.caption("Kết quả gửi chưa xác định; sổ chi tạm tính theo ước lượng, cần đối chiếu task trước khi gửi thêm.")
                    continue
                ready = kind != "final" or any(e["scene_id"] == sid and e["kind"] == "draft" and e["state"] == "succeeded"
                                              for e in items)
                if ready and confirm_all(f"quality_go_{pid}_{sid}_{kind}", [sid],
                                         f"Gen {q.LABELS[kind]} · ≈ ${q.estimate(kind):.2f}",
                                         f"Gen {q.LABELS[kind]} cho shot này, 4 giây, ≈ ${q.estimate(kind):.2f}?", st, "Có, gen thử"):
                    act(lambda: q.send(p, pid, sid, kind, runner.provider, C.DATA), "Đã xử lý lần gửi phép thử")
                    st.rerun()
        elif not rows:
            st.caption("Cần một shot ≤ 4 giây có ảnh và motion đã duyệt.")
        if runner is not None and any(e["state"] == "running" for e in items):
            if st.button("⟳ Lấy kết quả thử độ nét", key=f"quality_refresh_{pid}"):
                act(lambda: q.refresh(p, pid, runner.provider, C.DATA))
                st.rerun()
        for entry in items:
            if entry.get("file") and os.path.isfile(entry["file"]):
                st.caption(f"Scene {entry['scene_id']} · {q.LABELS[entry['kind']]}")
                show_video(entry["file"])


def group_tests_panel(items) -> None:
    """docs/PHAN_TICH_GOP_SHOT_2026-09-27.md: the same scene made by several grouped-generation methods (P1 Seedance first+last frame,
    P2 Seedance storyboard pictures as references, P3 Kling multi-shot), side by side for the person to judge (tools/experiments/group_test.py)."""
    if not items:
        return
    names = {"P1": "Seedance · khung đầu + cuối", "P2": "Seedance · ảnh storyboard làm tham chiếu", "P3": "Kling · multi-shot"}
    spent = sum(float(e.get("usd") or 0) for e in items)
    with st.expander(f"🧪 Thử gộp shot vào một lần gen — {len(items)} lần gen · ≈ {spent:.2f} USD", expanded=True):
        st.caption("Cùng một cảnh, cùng ảnh khung storyboard, mỗi cách một lần gen (không gen lại). So: đúng nhân vật từng shot, cắt đúng "
                   "số shot/thứ tự, bố cục khớp storyboard, liền mạch nơi chốn/ánh sáng, lỗi hình.")
        for m in sorted({e["method"] for e in items}):
            st.markdown(f"**{m} — {names.get(m, m)}**")
            cols = st.columns(max(len([e for e in items if e["method"] == m]), 1))
            for col, e in zip(cols, sorted((e for e in items if e["method"] == m), key=lambda e: e["group"])):
                col.caption(f"Nhóm {e['group']} · shot {', '.join(map(str, e['shots']))} · {e['seconds']} s trả tiền / {e['film_s']} s phim · "
                            f"≈ {float(e.get('usd') or 0):.2f} USD · {ui.state_label(e['state'])}")
                if e.get("file") and os.path.exists(e["file"]):
                    with col:
                        show_video(e["file"])
                elif e["state"] == "failed":
                    col.caption(f"❌ {escape(str(e.get('message') or ''))[:200]}")


def _written_off(p, j) -> bool:
    """A clip the dashboard gave up on because the task was 'not found' / 'not created' (it may exist under another id)."""
    row = p.conn.execute("SELECT note FROM job_events WHERE job_id=? AND to_state='failed' ORDER BY id DESC LIMIT 1", (j["id"],)).fetchone()
    return str((row["note"] if row else "") or "").startswith(("not_found", "not_created"))
