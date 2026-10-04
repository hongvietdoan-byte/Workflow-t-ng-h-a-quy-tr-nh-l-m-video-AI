"""Step 1 · 1c: the automatic run, its progress and the project budget (split from step1.py, S9.5)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.steps.step1_v2 import cap, say, is_next, reset_scope  # noqa: F401  (v2: long captions / notes become a one-line summary + ⓘ)


@st.fragment(run_every=5)
def autopilot_progress(pid: int) -> None:
    """Live progress (refreshes itself every 5 s while the page is open; the run itself lives in a background thread)."""
    reset_scope("ap")                    # 02/10: stable tooltip/popover keys across the 5 s refreshes → an open popover is not remounted (closed)
    p = C.scoped(Pipeline(connect(C.DB)))
    info = autopilot.status(p, pid)
    state = info["state"]
    tag = {"queued": ("xếp hàng", "b-warn"), "running": ("đang chạy", "b-info"), "done": ("hoàn tất", "b-ok"), "needs_attention": ("cần bạn xử lý", "b-warn"),
           "stopped": ("đã dừng", "b-warn"), "error": ("lỗi", "b-bad"), "waiting": ("chờ bạn duyệt", "b-pri")}.get(state, (state, ""))
    if ui.v2_on() and len(info["note"]) > 90:              # v2: the state badge + one line; the whole note in ⓘ
        from dashboard.design import components as D
        from dashboard.steps.step1_v2 import _short
        D.line(ui.badge(*tag) + f' <span class="script-sum">{escape(_short(info["note"], 80))}</span>', info["note"], f"script-auto-progress-{pid}")
    else:
        ui.html(ui.badge(*tag) + f' <span class="muted">{escape(info["note"])}</span>')
    for label, done, total in autopilot.progress(p, pid, C.DATA):
        ui.progress_bar(0 if not total else min(done / total, 1.0), text=f"{label}: {done}/{total}")
    if info["log"]:
        cap(" · ".join(f"{e['at']} {e['msg']}" for e in info["log"][-4:]), scope="ap")
    mgr = autopilot_manager(C.DB, C.DATA)
    stale = (autopilot.is_stale(p, pid, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
             or (state == "queued" and not mgr.queued(pid) and not mgr.alive(pid)))
    if stale:
        st.warning("Không thấy tiến trình chạy nền (có thể máy chủ vừa khởi động lại). Bấm “Tiếp tục”.")
    if state == "queued" and not stale:
        if st.button("■ Bỏ khỏi hàng đợi", key=f"ap_unqueue_{pid}"):
            autopilot.stop(p, pid)
            st.rerun()
    elif state == "running" and not stale:
        c1, c2 = st.columns(2)
        if c1.button("⏸ Tạm dừng", key=f"ap_pause_{pid}"):
            p.set_paused(pid, True)
        if c2.button("■ Dừng hẳn", key=f"ap_stop_{pid}"):
            autopilot.stop(p, pid)
            st.rerun()
    elif state in ("needs_attention", "stopped", "error", "waiting") or stale:
        label = "✔ Đã duyệt — tiếp tục" if state == "waiting" else "▶ Tiếp tục"
        if st.button(label, key=f"ap_resume_{pid}", type="primary"):
            autopilot.resume(p, pid, p.actor)
            autopilot_manager(C.DB, C.DATA).start(pid, user=C.access_user())
            st.rerun()
    if state == "done":
        out = os.path.join(C.DATA, str(pid), "output", "FINAL_VIDEO.mp4")
        if os.path.exists(out):
            show_video(out)


def _budget_summary(p: Pipeline, pid: int, data) -> str:
    from core import project_budget
    try:
        spent = sum(project_budget.spent_by_stage(p.conn, pid).values())
    except Exception:  # noqa: BLE001 - a summary line only
        return ""
    if data.get("locked"):
        return f"🔒 Đã khóa {float(data.get('total') or 0):.2f} USD · đã chi {spent:.2f} USD"
    try:                                             # S6.1 (Q7): the project's estimated total, visible without opening the panel
        est = f"dự tính ≈ {project_budget.propose(p, pid)['total']:.2f} USD · "
    except Exception:  # noqa: BLE001 - a summary line only
        est = ""
    return f"chưa duyệt · {est}đã chi {spent:.2f} USD"


def project_budget_panel(p: Pipeline, pid: int) -> None:
    """💵 The project's budget by stage (core.project_budget): computed by code from the shot table, approved and LOCKED by a person;
    after that only a person raises a stage's cap, with a reason."""
    from core import project_budget
    if not project_budget.enabled():
        return
    data = project_budget.get(p.conn, pid) or {}
    locked = bool(data.get("locked"))
    title = "💵 Ngân sách dự án" + (" — 🔒 ĐÃ KHÓA" if locked else
                                     (" — chưa duyệt" if ui.v2_on() else " — chưa duyệt (chạy tự động sẽ chờ trước khi gen ảnh)"))
    # v2: closed with one summary line (the hero button approves it); the "waits before pictures" sentence moves to the sub-title
    with ui.fold(title, _budget_summary(p, pid, data), f"budget_{pid}", default_open=is_next("budget", not locked),
                 sub="chạy tự động chờ bước này trước khi gen ảnh" if ui.v2_on() and not locked else "") as budget_open:  # E1.3
        if budget_open:
            try:
                prop = project_budget.propose(p, pid)
            except Exception as e:  # noqa: BLE001 - say it, never hide the panel
                say("warning", f"Không tính được ngân sách ({type(e).__name__}: {e})", f"script-budget-err-{pid}")
                return
            spent = project_budget.spent_by_stage(p.conn, pid)
            caps = data.get("caps") or {}
            rows = [{"Khâu": label, "Đã chi": f"{spent[k]:.2f}", "Còn cần (ước)": f"{prop['stages'][k]['left_estimate']:.2f}",
                     "Đề xuất trần": f"{prop['stages'][k]['cap']:.2f}", "Trần đã khóa": (f"{caps[k]:.2f}" if k in caps else "—")}
                    for k, label in project_budget.STAGES.items()]
            if ui.v2_on():                       # v2: a table that follows light/dark (st.dataframe is a canvas that stays light)
                from dashboard.design import components as D
                st.html(D.table(list(rows[0]), [list(r.values()) for r in rows], num_cols=(1, 2, 3, 4)))
            else:
                data_table(rows, hide_index=True, use_container_width=True)
            cap(f"Tổng đề xuất ≈ {prop['total']:.2f} USD" + (f" · tổng đã khóa {data['total']:.2f} USD" if locked else "")
                       + f" · đã chi {sum(spent.values()):.2f} USD. Đề xuất = đã chi + phần còn lại do CODE tính từ bảng shot + bảng giá, cộng "
                       f"{int(project_budget.IMAGE_REDO * 100)} % vẽ lại ảnh, {int(project_budget.VIDEO_REDO * 100)} % làm lại video, Claude ×"
                       f"{project_budget.LLM_MARGIN}; giá chưa xác minh (Seedance) ×{project_budget.UNVERIFIED_MARGIN}. Âm thanh chưa có giá: "
                       "vẫn giới hạn theo số lượt.")
            from core import cost as _cost                  # S6.6: how much Claude really read from the cache, per stage
            cached = [c for c in _cost.cache_stats(p.conn, pid) if c["input"] + c["cache_read"] + c["cache_write"]]
            if cached:
                cap("🧠 Claude đọc lại từ cache (rẻ ×0,1): " + " · ".join(
                    f"{c['stage']} {c['read_share'] * 100:.0f} % ({c['calls']} lượt)" for c in cached)
                    + " — khâu 0 % là chỗ nên xem lại cách gửi (prompt dưới 1024 token không cache; đổi ảnh phía trước làm mất cache sau).")
            target = st.number_input("Ngân sách mục tiêu (USD, để Director chia shot trong mức này; 0 = không đặt)", min_value=0.0,
                                     value=float(data.get("target") or 0.0), step=1.0, key=f"pb_target_{pid}")
            if (target or None) != (data.get("target") or None):
                project_budget.set_target(p.conn, pid, target or None)
            if data.get("target") and prop["total"] > float(data["target"]):
                say("warning", f"Đề xuất ≈ {prop['total']:.2f} USD VƯỢT mục tiêu {float(data['target']):.2f} USD — bớt shot khớp môi / giây "
                    "video / số shot (chia shot lại) trước khi duyệt.", f"script-budget-over-{pid}",
                    f"Đề xuất ≈ {prop['total']:.2f} USD vượt mục tiêu {float(data['target']):.2f} USD")
            if not locked:
                if confirm_all(f"pb_ok_{pid}", ["go"], f"✔ Duyệt & KHÓA ngân sách ≈ {prop['total']:.2f} USD",
                               f"Khóa ngân sách dự án ≈ {prop['total']:.2f} USD (trần từng khâu như bảng)? Sau khi khóa, mọi lời gọi trả tiền "
                               "vượt mức khâu hoặc tổng sẽ được CẢNH BÁO (vẫn gửi); chỉ người được nâng mức, kèm lý do.", st, "Có, khóa"):
                    project_budget.approve(p, pid, p.actor, prop)
                    st.rerun()
                return
            c1, c2, c3 = st.columns([1.2, 1, 2])
            stage = c1.selectbox("Nâng trần khâu", list(project_budget.STAGES), format_func=project_budget.STAGES.get, key=f"pb_stage_{pid}")
            add = c2.number_input("Thêm (USD)", min_value=0.0, value=0.0, step=0.5, key=f"pb_add_{pid}")
            why = c3.text_input("Lý do (bắt buộc)", key=f"pb_why_{pid}")
            if st.button("Nâng trần", key=f"pb_raise_{pid}", disabled=not (add > 0 and why.strip())):
                project_budget.raise_cap(p.conn, pid, stage, add, p.actor, why)
                st.rerun()
            for r in (data.get("raises") or [])[-5:]:
                cap(f"{r['at']} · {r['who']}: +{r['add_usd']:.2f} USD cho {project_budget.STAGES.get(r['stage'], r['stage'])} — {r['why']}")


def autopilot_panel(p: Pipeline, pid: int) -> None:
    """Fully automatic mode: approve the scene breakdown (and, by default, the Character Bible), the rest runs by itself."""
    if not allowed("autopilot"):
        return
    info = autopilot.status(p, pid)
    with st.container(border=True):
        ui.html(ui.card_title("🚀 Tự động hoàn toàn", "bạn duyệt phân cảnh (và nhân vật), phần còn lại tự chạy"))
        if info["state"] in ("queued", "running", "done", "needs_attention", "stopped", "error", "waiting"):
            autopilot_progress(pid)
            project_budget_panel(p, pid)
            if info["state"] not in ("running", "queued") and C.expert():      # E1.11: destructive, rarely used
                with st.expander("Chạy lại từ đầu cho dự án này"):
                    cap("Đặt lại trạng thái tự động (ảnh/video đã làm được giữ nguyên).")
                    if st.button("↺ Đặt lại chế độ tự động", key=f"ap_reset_{pid}"):
                        autopilot.reset(p, pid, C.DATA)
                        st.rerun()
            return
        cap("Chuỗi: Director → (dừng để bạn duyệt nhân vật, nếu bật) → dựng layout → ảnh + Claude QC → QC đồng bộ cả bộ → "
                   "(dừng để bạn duyệt storyboard, nếu bật) → motion prompt + rà prompt → giọng thoại → chọn model từng cảnh → video + QC video → nhạc, hiệu ứng → "
                   "bản giao (phụ đề, card cuối, bản xuất theo thiết lập ở màn Bản giao). Gặp việc cần người thì **dừng và báo**.")
        gates = autopilot.get_gates(p, pid)
        from contextlib import nullcontext
        # v2: the labels of the three gates may wrap (the core theme clips checkbox labels to one line and would hide half the sentence)
        with (st.container(key=f"script-gates-{pid}") if ui.v2_on() else nullcontext()):
            g1, g2 = st.columns(2)
            bible = g1.checkbox("Dừng để duyệt Character Bible + Character Lock + giọng + ảnh mốc trước khi gen", gates["bible"],
                                key=f"ap_gate_bible_{pid}", help="Nên bật: sai mô tả nhân vật sẽ lan ra MỌI cảnh (bài học từ lần hậu kiểm 2026-09-23).")
            pilot = g2.checkbox("Gen thử 2–3 cảnh đại diện trước, dừng để bạn xem rồi mới gen hết", gates["pilot"], key=f"ap_gate_pilot_{pid}",
                                help="Tiết kiệm credit ở dự án nhiều cảnh: lỗi phong cách/nhân vật lộ ra ở mẫu thử thay vì ở cả lô.")
            board = st.checkbox("Dừng ở **storyboard** (xem cả bộ ảnh khung đầu) trước khi gen video", gates["storyboard"],
                                key=f"ap_gate_board_{pid}",
                                help="Nên bật: ở đợt thử GĐ6 ~70% tiền video trả cho clip làm từ ảnh mà lỗi đã nhìn thấy trước (sai nhân vật, "
                                     "sai cỡ cảnh, nhóm multi-shot thiếu nhân vật). Xem ảnh không tốn tiền; gen video thì có.")
        if (bible, pilot, board) != (gates["bible"], gates["pilot"], gates["storyboard"]):
            autopilot.set_gates(p, pid, {"bible": bible, "pilot": pilot, "storyboard": board})
        issues = autopilot.problems(p, pid)
        for msg in issues:
            st.markdown(colored("bad", f"✖ {escape(str(msg))}"), unsafe_allow_html=True)
        scenes = p.conn.execute("SELECT COUNT(*) c FROM scenes WHERE project_id=?", (pid,)).fetchone()["c"]
        per = p.project(pid)["max_retry_count"] + 2
        run_est = None
        try:
            run_est = cost.estimate_run(p, pid)
        except Exception as e:  # noqa: BLE001 - never hide the button because an estimate failed; say it
            say("warning", f"Không ước tính được chi phí chạy tự động ({type(e).__name__}: {e}).", f"script-estimate-err-{pid}")
        if not issues:
            say("success", f"Sẵn sàng: {scenes} cảnh. Trần an toàn: tối đa {scenes * per} job ảnh và {scenes * per} job video (kể cả gen lại).",
                f"script-ready-{pid}", f"Sẵn sàng · {scenes} cảnh")
        if run_est is not None:
            say("info", "💵 Ước tính chạy tự động: " + cost.format_run_estimate(run_est).replace("$", "\\$")
                + ("  ·  🧪 chế độ Thử rẻ đang BẬT" if p.project(pid)["test_quality"] else ""), f"script-run-estimate-{pid}",
                f"💵 Ước tính chạy tự động ≈ {run_est['total']:.2f} USD (tối đa ≈ {run_est['max']:.2f})"
                + (" · ⚠ trần Claude không đủ" if run_est.get("llm_left") is not None and run_est["llm"] > run_est["llm_left"] else "")
                + (f" · {len(run_est['unknown'])} mục chưa có giá" if run_est.get("unknown") else "")
                + (" · 🧪 Thử rẻ" if p.project(pid)["test_quality"] else ""))
        project_budget_panel(p, pid)
        tag = f" (≈ {run_est['total']:.2f} USD)" if run_est is not None else ""
        if confirm_all(f"ap_start_{pid}", ["go"], "✔ Duyệt phân cảnh & chạy tự động" + tag,
                       "Bắt đầu chạy tự động? Sẽ gọi Deepix, Clip AI và Claude thật (tốn credit"
                       + (f", ước tính ≈ {run_est['total']:.2f} USD, tối đa ≈ {run_est['max']:.2f} USD" if run_est is not None else "")
                       + "). Trong lúc chạy, dự án chuyển sang “QC tự duyệt theo ngưỡng”; dừng hoặc xong sẽ trả lại cách duyệt cũ.",
                       st, "Có, chạy") and not issues:
            autopilot.start(p, pid, p.actor)
            autopilot_manager(C.DB, C.DATA).start(pid, user=C.access_user())
            st.rerun()
        if issues:
            cap("Hãy xử lý các mục đỏ ở trên trước khi bấm chạy.")


# siblings (bottom import: the parts use each other's functions at call time only)
from dashboard.steps.step1_prep import *  # noqa: F401,F403
from dashboard.steps.step1_characters import *  # noqa: F401,F403
from dashboard.steps.step1_characters import _voices, _bible_summary, _anchor_reset  # noqa: F401
from dashboard.steps.step1_director import *  # noqa: F401,F403
from dashboard.steps.step1_director import _director_summary, _replan_button, _paid_line, _crew_notes, _director_review  # noqa: F401
