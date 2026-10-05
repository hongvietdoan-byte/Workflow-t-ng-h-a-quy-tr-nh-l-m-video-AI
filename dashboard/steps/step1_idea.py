"""Step 1 · 💡 Ý tưởng thô → kịch bản (S11.1, core/idea_to_script.py; cờ `idea_to_script`). Four turns, each one approved by the person,
then a 2-column review (idea | script, what the Biên kịch added marked) and "Dùng kịch bản này" → Step 1 like a pasted script.

S14.21 (Đợt 3): drawn inside the script box (step1_box.py) — the idea comes from the box's chat input, the settings are a folded
`st.form` (⚙ Thiết lập), and the box's free "nói thêm" (`wish`) goes into the next paid turn. Every paid call stays behind `_paid`."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.steps.step1_v2 import cap, say, is_next  # noqa: F401  (v2: long captions / notes become a one-line summary + ⓘ)

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


def settings_summary(inp) -> str:
    """'30 s · 9:16 · TikTok · trend Tắt' — the folded ⚙ Thiết lập card in one line."""
    from core import idea_to_script as I
    if not inp:
        return "chưa đặt — mở, chọn rồi bấm 💡 Bắt đầu"
    return f"{inp.get('duration_s')} s · {inp.get('aspect')} · {inp.get('platform')} · trend {I.TREND_MODES.get(inp.get('trend', 'off'), '?')}"


def idea_settings_form(p: Pipeline, pid: int, idea: str) -> None:
    """Ngăn 0: the 6 settings in ONE st.form (enums → always valid; one rerun instead of six), folded to a line once started. The idea
    itself is not in the form any more: it is the text of the box (`idea`)."""
    from core import idea_to_script as I
    inp = I.get_state(p.conn, pid).get("inputs") or {}
    with ui.fold("⚙ Thiết lập", settings_summary(inp), f"idea_set_{pid}", default_open=not inp,
                 sub="thời lượng · khung · nền tảng · trend · nhân vật · giọng · CTA") as is_open:
        if not is_open:
            return
        with st.form(key=f"idea_form_{pid}"):
            c1, c2, c3, c4 = st.columns(4)
            dur = c1.selectbox("Thời lượng (s)", I.DURATIONS, index=I.DURATIONS.index(inp.get("duration_s", 30)) if inp.get("duration_s") in I.DURATIONS else 1)
            aspect = c2.selectbox("Khung", ["9:16", "16:9", "1:1"], index=["9:16", "16:9", "1:1"].index(inp.get("aspect", "9:16")))
            platform = c3.selectbox("Nền tảng", I.PLATFORMS, index=I.PLATFORMS.index(inp["platform"]) if inp.get("platform") in I.PLATFORMS else 0)
            trend = c4.selectbox("Dùng trend", list(I.TREND_MODES), format_func=I.TREND_MODES.get,
                                 index=list(I.TREND_MODES).index(inp.get("trend", "off")))
            d2, d3 = st.columns([1.2, 1.4])                      # rà S14.31: ONE list of people — the key points' (the old box is gone)
            tone = d2.text_input("Giọng điệu", inp.get("tone", ""), placeholder="hài, dễ thương")
            cta = d3.text_input("CTA (đúng chữ, cảnh cuối)", inp.get("cta", ""), placeholder="Tải Free Fire ngay")
            from core import idea_buildable as B
            k, an = B.kit(p.conn, pid), inp.get("anchors") or {}
            gone = [c for c in an.get("characters", []) if c.upper() not in [x["name"].upper() for x in k["characters"]]]
            if gone:                                              # rà: a saved choice that left the Kho is said, not dropped silently
                st.warning("Nhân vật đã chọn không còn trong danh sách dựng được: " + ", ".join(gone) + " — chọn lại.")
            if an.get("place") and an["place"] not in [x["name"] for x in k["places"]] and an.get("place_kind") != "real_life":
                st.warning(f"Nơi đã chọn ({an['place']}) không còn trong danh sách dựng được — chọn lại.")
            st.markdown("**Điểm then chốt** — bắt buộc; Biên kịch chỉ mở rộng chi tiết quanh các điểm này (thiếu thì không chạy, 0 USD)")
            e1, e2 = st.columns(2)
            kchars = [c["name"].upper() for c in k["characters"]]
            achars = e1.multiselect("Nhân vật (chỉ nhân vật có ảnh chuẩn trong Kho)", kchars, default=[c for c in an.get("characters", []) if c in kchars])
            costume = e2.text_input("Trang phục", an.get("costume", ""), placeholder="mặc định (hoặc tên bộ có hồ sơ)")
            kplaces = [pl["name"] for pl in k["places"]]
            place = e1.selectbox("Nơi quay (map có 3D / nền trong Kho)", [""] + kplaces,
                                 index=([""] + kplaces).index(an["place"]) if an.get("place") in kplaces else 0)
            # S14.35: a place outside the game that the Kho does not have yet -> "cần tạo bối cảnh" (ảnh ref do Đạo diễn tạo HOẶC Meshy 3D); only written down
            other = e1.text_input("…hoặc nơi KHÔNG có trong danh sách (ngoài game)", "" if an.get("place") in kplaces else an.get("place", ""),
                                  placeholder="bếp căn tin, văn phòng, lớp học…",
                                  help="Chỉ dùng khi nơi không có trong ô trên. Nếu nhập, phải nói rõ loại nơi — code không đoán.")
            pk_opts = ["", "đời thường (ngoài game)", "map game"]
            pk_cur = {"real_life": 1, "game_map": 2}.get(an.get("place_kind"), 0)
            place_kind = e2.radio("Loại nơi vừa nhập", pk_opts, index=pk_cur, horizontal=True,
                                  help="Map game chưa có file 3D vẫn bị chặn. Đời thường: đi tiếp, ghi vào bảng kê tài nguyên là 'cần tạo bối cảnh'.")
            sc_opts = ["", "Đạo diễn tạo ảnh bối cảnh làm ref", "Meshy dựng 3D (tốn tiền — chỉ ghi lựa chọn, chưa chạy)"]
            scene_choice = e2.radio("Cách tạo bối cảnh (nơi đời thường)", sc_opts, horizontal=True,
                                    index={"ref_image": 1, "meshy": 2}.get(an.get("scene_choice"), 0),
                                    help="Chưa chọn = Đạo diễn mặc định tạo ảnh. Meshy: chỉ ghi lựa chọn + ước giá vào bảng kê tài nguyên.")
            gp = e2.radio("Có cảnh gameplay / giao diện game?", ["", "không", "có"], horizontal=True,
                          index=["", "khong", "co"].index(an.get("gameplay_ui", "")) if an.get("gameplay_ui", "") in ("", "khong", "co") else 0,
                          help="'có' = chấp nhận rủi ro: chưa có tư liệu chứng minh dựng được màn hình điện thoại / sảnh / combat gameplay.")
            plot = st.text_input("Diễn biến chính / mâu thuẫn", an.get("plot", ""), placeholder="Kelly và Maxim tranh nhau thùng thính")
            ending = st.text_input("Cú chốt / kết", an.get("ending", ""), placeholder="mở thùng ra thì trống trơn")
            new = st.form_submit_button("💡 Ý tưởng mới (bắt đầu lại từ lượt 1)" if inp else "💡 Bắt đầu")
        if inp and idea.strip() and idea.strip() != inp.get("idea"):
            cap("Chữ trong khung khác ý tưởng đang làm — bấm 💡 Ý tưởng mới để bắt đầu lại với chữ mới (các lượt cũ bị bỏ).")
    if new and act(lambda: I.start(p.conn, pid, idea, dur, aspect, platform, tone, achars, cta, trend, p=p,
                                      anchors={"characters": achars, "costume": costume, "place": (other.strip() or place), "plot": plot,
                                               "ending": ending, "gameplay_ui": gp, "place_kind": place_kind if other.strip() else "",
                                               "scene_choice": scene_choice if other.strip() else ""})):
        st.rerun()


def turn_questions(p, pid, state, client, wish, used) -> list:
    """Lượt 1 + the answers. Returns the replies (None = stop drawing: the turn is not done yet)."""
    from core import idea_to_script as I
    st.markdown("**1 · Hỏi lại**")
    if not state.get("questions"):
        from core import idea_buildable as B
        why = B.gate(p.conn, pid, state.get("inputs") or {})
        if why:                                                    # S14.31 ý 6: ask for what is missing — no paid button, no call
            for n, t in enumerate(why):
                say("warning", t, f"script-idea-gate-{pid}-{n}")
            return None
        if _paid("▶ Lượt 1: Biên kịch đọc ý tưởng + hỏi lại", f"idea_q_{pid}", state) \
                and act(lambda: I.questions(p.conn, pid, client, wish=wish, p=p)):
            used()
            st.rerun()
        return None
    if state.get("have"):
        cap("Đã có: " + "; ".join(state["have"]) + (" · Còn thiếu: " + "; ".join(state["missing"]) if state.get("missing") else ""))
    replies = []
    for i, q in enumerate(state["questions"]):
        prev = (state.get("answers") or [{}] * len(state["questions"]))[i] if state.get("answers") else {}
        replies.append(st.text_input(f"{q['q']} — mặc định: {q['default']}", "" if prev.get("defaulted") else prev.get("a", ""),
                                     key=f"idea_a_{pid}_{i}", help=q.get("why") or None))
    cap("Để trống = dùng đáp án mặc định (được ghi lại).")
    return replies


def turn_directions(p, pid, state, client, wish, used, replies):
    """Lượt 2. Returns (choice, note) or None. "↻ Hỏi lại" only when the input changed (C8: same prompt = money for nothing)."""
    from core import idea_to_script as I
    st.markdown("**2 · Ba hướng**")
    if not state.get("directions"):
        if _paid("▶ Lượt 2: 3 hướng", f"idea_d_{pid}", state):
            def go():
                I.answer(p.conn, pid, replies)
                I.directions(p.conn, pid, client, wish=wish, p=p)
            if act(go):
                used()
                st.rerun()
        return None
    labels = [f"{d['title']} — {d['logline']} · hook 3 s: {d['hook_3s']} · chốt: {d['payoff']}" + (f" · 📈 {d['trend_card']}" if d.get("trend_card") else "")
              for d in state["directions"]]
    choice = st.radio("Chọn hướng", range(3), format_func=lambda i: labels[i], index=state.get("chosen") or 0, key=f"idea_ch_{pid}")
    note = st.text_input("Ghi chú cho hướng đã chọn (không bắt buộc)", state.get("choice_note", ""), key=f"idea_note_{pid}")
    changed = I.directions_input_changed(state, replies, wish)
    if st.button(f"↻ Hỏi lại 3 hướng khác (≈ {I.TURN_USD:g} USD)", key=f"idea_redo_d_{pid}", disabled=not changed,
                 help=None if changed else "Đổi câu trả lời ở lượt 1 hoặc nói thêm ở khung bên dưới trước — hỏi lại y hệt là trả tiền cho cùng một câu hỏi."):
        def redo():
            I.answer(p.conn, pid, replies)
            I.directions(p.conn, pid, client, wish=wish, p=p)
        if act(redo):
            used()
            st.rerun()
    return choice, note


def turn_outline(p, pid, state, client, wish, used, choice, note) -> bool:
    from core import idea_to_script as I
    st.markdown("**3 · Dàn ý theo giây**")
    if not state.get("beats") or state.get("chosen") != choice:
        if _paid("▶ Lượt 3: dàn ý theo giây cho hướng này", f"idea_o_{pid}", state) \
                and act(lambda: I.outline(p.conn, pid, client, choice, note, wish=wish, p=p)):
            used()
            st.rerun()
        return False
    rows = [{"Nhịp": b["name"], "Giây": f"{b['start']:g}–{b['end']:g}", "Nơi": b.get("place", ""), "Ai": ", ".join(b.get("who") or []),
             "Chuyện gì": b.get("what", ""), "Thoại": " / ".join(f"{d.get('speaker')}: {d.get('line')}" for d in b.get("dialogue") or [])}
            for b in state["beats"]]
    data_table(rows, hide_index=True, use_container_width=True)
    if state.get("question"):
        cap(f"Câu hỏi xuyên video: {state['question']}")
    for n, c in enumerate(state.get("outline_checks") or []):
        if c["level"] == "block":                                    # blocks the next step → stays a red box (P1)
            st.error(c["text"])
        else:
            say("warning", c["text"], f"script-idea-outline-{pid}-{n}")
    return True


def turn_script(p, pid, state, client, wish, used) -> None:
    from core import idea_to_script as I
    inp = state["inputs"]
    st.markdown("**4 · Kịch bản**")
    if not state.get("script"):
        if _paid("▶ Lượt 4: viết kịch bản đầy đủ", f"idea_w_{pid}", state) and act(lambda: I.write(p.conn, pid, client, wish=wish, p=p)):
            used()
            st.rerun()
        return
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Ý tưởng gốc**")
        ui.html('<div class="idea-col">' + escape(inp["idea"]) + "</div>")
        if state.get("added"):
            if ui.v2_on() and len(state["added"]) > 3:                 # v2 (list > 3): a count outside, the list in ⓘ
                from dashboard.design import components as D
                D.line(f'<span class="script-sum">Biên kịch tự ghi thêm {len(state["added"])} phần</span>',
                       "Biên kịch tự ghi phần thêm:\n\n" + "\n".join(f"- {a.get('kind')}: {a.get('text')}" for a in state["added"]),
                       f"script-idea-added-{pid}")
            else:
                cap("Biên kịch tự ghi phần thêm:")
                for a in state["added"]:
                    cap(f"• {a.get('kind')}: {a.get('text')}")
    with right:
        st.markdown("**Kịch bản** — <span style='background:rgba(255,196,0,.25)'>dòng mới</span> · "
                    "<span style='background:rgba(255,120,60,.4)'>tên / nơi mới</span>", unsafe_allow_html=True)
        ui.html(_marked_html(inp["idea"], state["script"]))
    edited = st.text_area("Sửa tay kịch bản (giữ khuôn CẢNH n - …)", state["script"], height=220, key=f"idea_edit_{pid}")
    if edited.strip() != state["script"] and st.button("💾 Lưu bản sửa + kiểm lại", key=f"idea_save_{pid}"):
        if act(lambda: I.edit(p.conn, pid, edited, p=p)):
            st.rerun()
    chk = state.get("script_checks") or {}
    for t in chk.get("problems") or []:
        st.error(t)
    flags = chk.get("flags") or []
    if ui.v2_on() and len(flags) > 2:                                  # v2 (list > 2): one line + the whole list in ⓘ
        from dashboard.design import components as D
        D.line(f'<span class="script-sum">{len(flags)} lưu ý về kịch bản</span>', "\n".join(f"- {t}" for t in flags), f"script-idea-flags-{pid}")
    else:
        for n, t in enumerate(flags):
            say("warning", t, f"script-idea-flag-{pid}-{n}")
    has_scenes = bool(p.conn.execute("SELECT 1 FROM scenes WHERE project_id=?", (pid,)).fetchone())
    if st.button("✔ Dùng kịch bản này" + (" (dự án đã có cảnh — bấm ↺ Làm lại ở trên trước)" if has_scenes else ""),
                 key=f"idea_use_{pid}", type="primary", disabled=not chk.get("ok") or has_scenes):
        if act(lambda: st.toast(f"Đã đưa {I.use_script(p, pid)} cảnh vào màn Kịch bản")):
            st.rerun()


def idea_turns(p: Pipeline, pid: int, wish: str = "", used=lambda: None) -> None:
    """The 4 paid turns after "💡 Bắt đầu". `wish` = the box's pending "nói thêm" (goes into the next paid turn; empty → the prompt is
    exactly the old one); `used()` is called once a turn that read it went through."""
    from core import idea_to_script as I
    ui.html(_CSS)
    state = I.get_state(p.conn, pid)
    if not state.get("inputs"):
        return
    client = C.llm_client()
    if client is None:
        say("info", "Chưa có Claude (LLM_PROVIDER / ANTHROPIC_API_KEY) — không chạy được Biên kịch.", f"script-idea-noclaude-{pid}")
        return
    cap(f"Đã dùng ≈ {float(state.get('spent') or 0):.3f} USD cho ý tưởng này.")
    replies = turn_questions(p, pid, state, client, wish, used)
    if replies is None:
        return
    picked = turn_directions(p, pid, state, client, wish, used, replies)
    if picked is None:
        return
    if turn_outline(p, pid, state, client, wish, used, *picked):
        turn_script(p, pid, state, client, wish, used)
