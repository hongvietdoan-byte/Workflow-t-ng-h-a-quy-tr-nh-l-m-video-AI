"""Step 1 · 💡 Ý tưởng thô → kịch bản (S11.1, core/idea_to_script.py; cờ `idea_to_script`). Four turns, each one approved by the person,
then a 2-column review (idea | script, what the Biên kịch added marked) and "Dùng kịch bản này" → Step 1 like a pasted script."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C

_CSS = """<style>
.idea-col{font-size:.9rem;line-height:1.55;white-space:pre-wrap;border:1px solid rgba(128,128,128,.3);border-radius:8px;padding:.6rem .8rem;
max-height:520px;overflow:auto}
.idea-col .h{font-weight:700}
.idea-col .new{background:rgba(255,196,0,.18);border-radius:3px}
.idea-col .nw{background:rgba(255,120,60,.35);border-radius:3px;font-weight:600}
</style>"""


def _marked_html(idea: str, script: str) -> str:
    from core import idea_to_script as I
    rows = []
    for ln in I.marked_lines(idea, script):
        text = escape(ln["text"])
        for w in ln["new_words"]:
            text = text.replace(escape(w), f'<span class="nw">{escape(w)}</span>', 1)
        cls = ("h " if ln["kind"] == "heading" else "") + ("new" if ln["new"] else "")
        rows.append(f'<span class="{cls.strip()}">{text}</span>' if cls.strip() else text)
    return '<div class="idea-col">' + "\n".join(rows) + "</div>"


def _paid(label: str, key: str, state) -> bool:
    from core import idea_to_script as I
    left = I.RUN_CAP_USD - float(state.get("spent") or 0)
    return st.button(f"{label} (≈ {I.TURN_USD:g} USD · còn {left:.2f} / {I.RUN_CAP_USD:g} USD cho ý tưởng này)", key=key, type="primary")


def idea_panel(p: Pipeline, pid: int) -> None:
    from core import idea_to_script as I
    ui.html(_CSS)
    state = I.get_state(p.conn, pid)
    inp = state.get("inputs") or {}
    st.caption("Viết 2–3 dòng ý tưởng; Biên kịch (Claude) hỏi lại, đưa 3 hướng, dàn ý theo giây rồi viết kịch bản đúng khuôn. Bạn duyệt từng "
               "bước; phần Biên kịch thêm được tô màu. Mọi lời gọi vào sổ chi, trần " + f"{I.RUN_CAP_USD:g} USD / ý tưởng.")
    with st.form(key=f"idea_form_{pid}"):
        idea = st.text_area("Ý tưởng", inp.get("idea", ""), height=90, placeholder="Kelly và Maxim tranh một thùng thính ở Đảo Quân Sự…")
        c1, c2, c3, c4 = st.columns(4)
        dur = c1.selectbox("Thời lượng (s)", I.DURATIONS, index=I.DURATIONS.index(inp.get("duration_s", 30)) if inp.get("duration_s") in I.DURATIONS else 1)
        aspect = c2.selectbox("Khung", ["9:16", "16:9", "1:1"], index=["9:16", "16:9", "1:1"].index(inp.get("aspect", "9:16")))
        platform = c3.selectbox("Nền tảng", I.PLATFORMS, index=I.PLATFORMS.index(inp["platform"]) if inp.get("platform") in I.PLATFORMS else 0)
        trend = c4.selectbox("Dùng trend", list(I.TREND_MODES), format_func=I.TREND_MODES.get,
                             index=list(I.TREND_MODES).index(inp.get("trend", "off")))
        lib = I.library(p.conn, pid)
        d1, d2, d3 = st.columns([2, 1.2, 1.4])
        chars = d1.multiselect("Nhân vật (Kho FF, để trống được)", sorted(set(n.upper() for n in lib["characters"])),
                               default=[c for c in inp.get("characters", []) if c in {n.upper() for n in lib["characters"]}])
        tone = d2.text_input("Giọng điệu", inp.get("tone", ""), placeholder="hài, dễ thương")
        cta = d3.text_input("CTA (đúng chữ, cảnh cuối)", inp.get("cta", ""), placeholder="Tải Free Fire ngay")
        new = st.form_submit_button("💡 Ý tưởng mới (bắt đầu lại từ lượt 1)" if inp else "💡 Bắt đầu")
    if new and act(lambda: I.start(p.conn, pid, idea, dur, aspect, platform, tone, chars, cta, trend)):
        st.rerun()
    if not state.get("inputs"):
        return
    client = C.llm_client()
    if client is None:
        st.info("Chưa có Claude (LLM_PROVIDER / ANTHROPIC_API_KEY) — không chạy được Biên kịch.")
        return
    st.caption(f"Đã dùng ≈ {float(state.get('spent') or 0):.3f} USD cho ý tưởng này.")

    # 1 — questions
    st.markdown("**1 · Hỏi lại**")
    if not state.get("questions"):
        if _paid("▶ Lượt 1: Biên kịch đọc ý tưởng + hỏi lại", f"idea_q_{pid}", state) and act(lambda: I.questions(p.conn, pid, client)):
            st.rerun()
        return
    if state.get("have"):
        st.caption("Đã có: " + "; ".join(state["have"]) + (" · Còn thiếu: " + "; ".join(state["missing"]) if state.get("missing") else ""))
    replies = []
    for i, q in enumerate(state["questions"]):
        prev = (state.get("answers") or [{}] * len(state["questions"]))[i] if state.get("answers") else {}
        replies.append(st.text_input(f"{q['q']} — mặc định: {q['default']}", "" if prev.get("defaulted") else prev.get("a", ""),
                                     key=f"idea_a_{pid}_{i}", help=q.get("why") or None))
    st.caption("Để trống = dùng đáp án mặc định (được ghi lại).")

    # 2 — directions
    st.markdown("**2 · Ba hướng**")
    if not state.get("directions"):
        if _paid("▶ Lượt 2: 3 hướng", f"idea_d_{pid}", state):
            def go():
                I.answer(p.conn, pid, replies)
                I.directions(p.conn, pid, client)
            if act(go):
                st.rerun()
        return
    labels = [f"{d['title']} — {d['logline']} · hook 3 s: {d['hook_3s']} · chốt: {d['payoff']}" + (f" · 📈 {d['trend_card']}" if d.get("trend_card") else "")
              for d in state["directions"]]
    choice = st.radio("Chọn hướng", range(3), format_func=lambda i: labels[i], index=state.get("chosen") or 0, key=f"idea_ch_{pid}")
    note = st.text_input("Ghi chú cho hướng đã chọn (không bắt buộc)", state.get("choice_note", ""), key=f"idea_note_{pid}")
    if st.button("↻ Hỏi lại 3 hướng khác", key=f"idea_redo_d_{pid}"):
        def redo():
            I.answer(p.conn, pid, replies)
            I.directions(p.conn, pid, client)
        if act(redo):
            st.rerun()

    # 3 — outline
    st.markdown("**3 · Dàn ý theo giây**")
    if not state.get("beats") or state.get("chosen") != choice:
        if _paid("▶ Lượt 3: dàn ý theo giây cho hướng này", f"idea_o_{pid}", state) and act(lambda: I.outline(p.conn, pid, client, choice, note)):
            st.rerun()
        return
    rows = [{"Nhịp": b["name"], "Giây": f"{b['start']:g}–{b['end']:g}", "Nơi": b.get("place", ""), "Ai": ", ".join(b.get("who") or []),
             "Chuyện gì": b.get("what", ""), "Thoại": " / ".join(f"{d.get('speaker')}: {d.get('line')}" for d in b.get("dialogue") or [])}
            for b in state["beats"]]
    st.dataframe(rows, hide_index=True, use_container_width=True)
    if state.get("question"):
        st.caption(f"Câu hỏi xuyên video: {state['question']}")
    for c in state.get("outline_checks") or []:
        (st.error if c["level"] == "block" else st.warning)(c["text"])

    # 4 — script
    st.markdown("**4 · Kịch bản**")
    if not state.get("script"):
        if _paid("▶ Lượt 4: viết kịch bản đầy đủ", f"idea_w_{pid}", state) and act(lambda: I.write(p.conn, pid, client)):
            st.rerun()
        return
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Ý tưởng gốc**")
        ui.html('<div class="idea-col">' + escape(inp["idea"]) + "</div>")
        if state.get("added"):
            st.caption("Biên kịch tự ghi phần thêm:")
            for a in state["added"]:
                st.caption(f"• {a.get('kind')}: {a.get('text')}")
    with right:
        st.markdown("**Kịch bản** — <span style='background:rgba(255,196,0,.25)'>dòng mới</span> · "
                    "<span style='background:rgba(255,120,60,.4)'>tên / nơi mới</span>", unsafe_allow_html=True)
        ui.html(_marked_html(inp["idea"], state["script"]))
    edited = st.text_area("Sửa tay kịch bản (giữ khuôn CẢNH n - …)", state["script"], height=220, key=f"idea_edit_{pid}")
    if edited.strip() != state["script"] and st.button("💾 Lưu bản sửa + kiểm lại", key=f"idea_save_{pid}"):
        if act(lambda: I.edit(p.conn, pid, edited)):
            st.rerun()
    chk = state.get("script_checks") or {}
    for t in chk.get("problems") or []:
        st.error(t)
    for t in chk.get("flags") or []:
        st.warning(t)
    has_scenes = bool(p.conn.execute("SELECT 1 FROM scenes WHERE project_id=?", (pid,)).fetchone())
    if st.button("✔ Dùng kịch bản này" + (" (dự án đã có cảnh — bấm ↺ Làm lại ở trên trước)" if has_scenes else ""),
                 key=f"idea_use_{pid}", type="primary", disabled=not chk.get("ok") or has_scenes):
        if act(lambda: st.toast(f"Đã đưa {I.use_script(p, pid)} cảnh vào Bước 1")):
            st.rerun()
