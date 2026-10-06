"""Step 1 · khung nhập kịch bản hội thoại (S14.21, docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md Đợt 3; behind the flag
`idea_to_script` — off → the old 2 tabs of step1.script_input, exactly).

S14.47: lịch sử theo dự án, chat tự do gửi Claude qua sổ chi; các việc viết/gen giữ nút có giá.
Thiết kế cũ (S14.21): one `st.chat_input` is the single way in for text (a pasted script, a raw
idea, or a "nói thêm" for the Biên kịch) and it NEVER calls a model. Code decides for 0 USD what the text is (idea_to_script.classify:
script → the old ▶ Phân tích split; idea → the Biên kịch's turns, each behind a button with its price; grey zone → ask, never guess —
luật 3), always with a one-click override. S14.38: the chat is the ONLY door in — no ✍ Sửa toàn văn (paste_) and no 📎 popover (up_): a file is dropped on the chat input
(same file types), the script in use is read-only under "Xem kịch bản" (st.code → copy, edit elsewhere, paste back into the chat).
A full script pasted while one is in use asks once before replacing it. Keys kept: btn_analyse_, btn_bad_reset_ (the flag-off tabs of
step1.script_input keep up_/paste_). No expander in the box itself: it sits inside the v2 "Nhập / thay" expander (C2).
S14.43 mục 5: a script with headings but thin (idea_to_script.sparse) → Claude asks in the chat to write it out (priced turns only after "Có");
"viết kịch bản chi tiết từ dàn ý này" typed in the chat (idea_to_script.expand_request, by rule) → the Biên kịch path with that outline."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard.steps.step1_v2 import cap, say  # noqa: F401

_SHOW_LINES, _SHOW_CHARS = 6, 400
_KIND_TEXT = {"script": "KỊCH BẢN", "idea": "Ý TƯỞNG"}


def _keys(pid: int) -> dict:
    return {"text": f"box_text_{pid}", "mode": f"in_mode_{pid}", "wish": f"box_wish_{pid}", "file": f"box_file_{pid}",
            "pending": f"box_pending_{pid}", "ask": f"box_ask_{pid}", "chat": f"box_in_{pid}",
            "expand": f"box_expand_{pid}", "expand_off": f"box_expand_off_{pid}", "expand_msg": f"box_expand_msg_{pid}",
            "chatask": f"box_chatask_{pid}"}


def _take(p: Pipeline, pid: int, got) -> None:
    """What the chat input sent this run → session (a file → read as a script; text → script/idea text, or the next turn's wish when an
    idea is already being written and the new text reads as an idea too)."""
    from core import idea_to_script as I
    k, ss = _keys(pid), st.session_state
    text = got if isinstance(got, str) else (getattr(got, "text", None) or "")
    files = [] if isinstance(got, str) else list(getattr(got, "files", None) or [])
    if files:
        ss[k["file"]] = (files[0].name, files[0].getvalue())
        ss[k["mode"]] = "script"
    if not text.strip():
        return
    started = bool(I.get_state(p.conn, pid).get("inputs"))
    mode = ss.get(k["mode"]) or I.classify(ss.get(k["text"], "")).get("kind")
    req = None if files or (started and mode == "idea") else I.expand_request(text)   # rà: while an idea is written → a wish (below)
    if req is not None:                                                # S14.43 mục 5: "viết kịch bản chi tiết từ dàn ý này" (0 USD, by rule)
        _expand_from_chat(p, pid, req["rest"])
        return
    if (started and mode == "idea" and not files and I.classify(text)["kind"] != "script"
            and len(text.strip()) < I.IDEA_MAX_CHARS):                   # rà: "Lưu ý: …" / "Kelly: nói nhẹ hơn" is a wish, not a script
        ss[k["wish"]] = text.strip()                                   # "nói thêm" for the next paid turn (shown, removable)
        return
    if not files:
        d = decide(_scene_count(p, pid), text)
        if d["action"] == "replace":                                   # S14.38: a full script over one in use → ask once
            ss[k["pending"]] = text
            ss.pop(k["ask"], None)
            return
        if d["action"] == "ask":                                       # a few scenes / a snippet over one in use → never guess
            ss[k["ask"]] = text
            ss.pop(k["pending"], None)
            return
    ss[k["text"]] = text
    if not files:
        ss.pop(k["mode"], None)                                        # a new text is classified again
        ss.pop(k["expand"], None)


def _expand_from_chat(p: Pipeline, pid: int, rest: str) -> None:
    """The outline the request is about: pasted with it, else the text already in the box, else the script in use. None → said (luật 1)."""
    from core import idea_to_script as I
    k, ss = _keys(pid), st.session_state
    sources = (((rest or "").strip(), ""), ((ss.get(k["text"]) or "").strip(), "chữ đang có trong khung chat"),
               ((p.project(pid)["script_text"] or "").strip(), "kịch bản đang dùng của dự án"))
    outline, src = next(((t, s) for t, s in sources if t), ("", ""))
    if not outline:
        ss[k["expand_msg"]] = ("Chưa có dàn ý / kịch bản nào để viết chi tiết — dán dàn ý ngay dưới dòng yêu cầu (cùng một tin) rồi gửi lại. "
                               "Chưa tốn gì.")
        return
    if src:                                                            # rà: taken from elsewhere → say what and from where
        head = " / ".join(ln.strip() for ln in outline.splitlines() if ln.strip())[:160]
        ss[k["expand_msg"]] = f"Đã lấy dàn ý từ {src} để viết chi tiết (đoạn đầu: “{head}…”). Sai dàn ý thì dán dàn ý đúng ngay dưới dòng yêu cầu."
    else:
        ss.pop(k["expand_msg"], None)
    ss[k["text"]] = outline
    ss[k["mode"]] = "idea"                                             # → the Biên kịch's turns, each behind a priced button
    ss[k["expand"]] = "request"
    if I.get_state(p.conn, pid).get("inputs", {}).get("idea", "").strip() != outline:
        ss.pop(k["wish"], None)


def _expand_yes(pid: int) -> None:
    k, ss = _keys(pid), st.session_state
    ss[k["mode"]] = "idea"
    ss[k["expand"]] = "yes"


def _expand_no(pid: int, text: str) -> None:
    st.session_state[_keys(pid)["expand_off"]] = text.strip()


def sparse_offer(pid: int, text: str) -> None:
    """S14.43 mục 5: a script with headings but thin (I.sparse, 0 USD) → Claude ASKS in the chat whether to write it out; nothing is paid
    here — "Có" only switches to the Biên kịch path where every turn has its own priced button."""
    from core import idea_to_script as I
    k, ss = _keys(pid), st.session_state
    if not text.strip() or ss.get(k["expand_off"]) == text.strip():
        return
    s = I.sparse(text)
    if not s["sparse"]:
        return
    with st.chat_message("assistant"):
        st.markdown(f"**Kịch bản còn ngắn/sơ sài** ({escape('; '.join(s['why']))}) — bạn có muốn mình viết bổ sung cho chi tiết không? "
                    f"(≈ ${I.expand_usd():.2f} ước tính: 4 lượt Biên kịch × {I.TURN_USD:g} USD, trần {I.RUN_CAP_USD:g} USD; chưa tốn gì "
                    "cho tới khi bấm nút có ghi giá ở từng lượt)")
        a, b = st.columns(2)
        a.button("✍ Có, viết bổ sung chi tiết", key=f"box_expand_yes_{pid}", on_click=_expand_yes, args=(pid,), type="primary", width="stretch")
        b.button("Không, giữ nguyên", key=f"box_expand_no_{pid}", on_click=_expand_no, args=(pid, text), width="stretch")


def _scene_count(p: Pipeline, pid: int) -> int:
    return int(p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0])


def decide(existing: int, text: str) -> dict:
    """S14.38 (0 USD, no model): what to do with a text typed / pasted into the chat. {"action": "set" | "replace" | "ask", "scenes"}.
    No script in use → "set" (as before). A script in use: a FULL script (>= half as many scenes) → "replace" (one confirm card); a few
    scenes or a snippet with dialogue → "ask" (add or replace? never guess); a raw idea → "set" (the Biên kịch path, unchanged)."""
    from core import idea_to_script as I
    c = I.classify(text)
    if existing <= 0 or not (text or "").strip():
        return {"action": "set", "scenes": c.get("scenes", 0)}
    if c["kind"] == "script":
        full = c.get("scenes", 0) >= max(2, (existing + 1) // 2)
        return {"action": "replace" if full else "ask", "scenes": c.get("scenes", 0)}
    if c["kind"] == "unsure":
        return {"action": "ask", "scenes": 0}
    return {"action": "set", "scenes": 0}


def resolve(p: Pipeline, pid: int, choice: str) -> None:
    """The buttons of the two cards. choice: "replace" (confirm the pending script: clear the scenes without work like ↺ Làm lại, keep
    the text for ▶ Phân tích) · "swap" / "add" (from the ask card → become the pending replace; "add" = script in use + the new part)
    · "cancel"."""
    from core import access
    k, ss = _keys(pid), st.session_state
    if choice == "cancel":
        ss.pop(k["pending"], None)
        ss.pop(k["ask"], None)
        return
    if choice in ("swap", "add"):
        new = (ss.pop(k["ask"], "") or "").strip()
        cur = ((p.project(pid)["script_text"] or "") if choice == "add" else "").strip()
        ss[k["pending"]] = (cur + "\n\n" + new) if cur else new
        return
    new = ss.get(k["pending"]) or ""
    access.need_edit(p, pid, "thay kịch bản")                           # 'Chỉ xem' stays blocked
    from dashboard.steps.step1 import reset_unworked_scenes
    reset_unworked_scenes(p, pid)
    ss[k["text"]] = new
    ss.pop(k["pending"], None)
    ss.pop(k["mode"], None)
    ss.pop(k["file"], None)


def _set_mode(pid: int, mode: str) -> None:
    st.session_state[f"in_mode_{pid}"] = mode


def _wish_to_idea(pid: int) -> None:
    k, ss = _keys(pid), st.session_state
    ss[k["text"]] = ss.pop(k["wish"], "")
    ss.pop(k["mode"], None)


def _preview(text: str) -> str:
    lines = text.strip().splitlines()
    out = "\n".join(lines[:_SHOW_LINES])[:_SHOW_CHARS]
    return out + (f"\n… (+{len(lines) - _SHOW_LINES} dòng — xem nguyên văn ở “Xem kịch bản”)" if len(lines) > _SHOW_LINES else "")


def _verdict(pid: int, mode: str, forced: bool, why) -> None:
    """The one line under the person's message: what the code understood + the override (luật 3: said, never silent)."""
    reason = " · ".join(why or [])
    if mode == "unsure":
        st.markdown(f"**Đây là kịch bản hay ý tưởng?** Code chưa chắc ({escape(reason)}) — chọn một, chưa có gì chạy.")
        a, b = st.columns(2)
        a.button("📜 Đây là kịch bản", key=f"box_mode_script_{pid}", on_click=_set_mode, args=(pid, "script"), width="stretch")
        b.button("💡 Đây là ý tưởng", key=f"box_mode_idea_{pid}", on_click=_set_mode, args=(pid, "idea"), width="stretch")
        return
    other = "idea" if mode == "script" else "script"
    a, b = st.columns([3, 1.4], vertical_alignment="center")
    a.markdown(f"Hiểu là **{_KIND_TEXT[mode]}** ({'bạn chọn' if forced else escape(reason)})"
               + (" — ▶ Phân tích tách cảnh, 0 USD." if mode == "script" else " — Biên kịch viết thành kịch bản; mỗi lượt có nút ghi giá."))
    b.button("không phải, đây là " + ("ý tưởng" if other == "idea" else "kịch bản"), key=f"box_mode_{other}_{pid}",
             on_click=_set_mode, args=(pid, other), width="stretch")


def receipt(text: str, c: dict = None) -> str:
    """S14.36: the one-line card shown in the chat when a SCRIPT was pasted (0 USD, from I.classify): how many scenes were seen + the size
    of the paste. "" for an idea / grey zone / nothing (those have their own verdict line)."""
    from core import idea_to_script as I
    body = (text or "").strip()
    c = c or I.classify(body)
    if not body or c.get("kind") != "script":
        return ""
    lines = len([ln for ln in body.splitlines() if ln.strip()])
    return (f"Đã nhận kịch bản {c.get('scenes', 0)} cảnh ({lines} dòng · {len(body):,} ký tự)".replace(",", ".")
            + " — bấm ▶ Phân tích để tách cảnh (0 USD).")


def _cards(p: Pipeline, pid: int) -> None:
    """S14.38: the one-time confirm (full script over the one in use) and the ask (a few scenes / a snippet) — both 0 USD."""
    from core import idea_to_script as I
    k, ss = _keys(pid), st.session_state
    pend, ask = ss.get(k["pending"]), ss.get(k["ask"])
    if ss.get(k["chatask"]):
        _chat_ask(p, pid)
    if pend:
        n = I.classify(pend).get("scenes", 0)
        with st.chat_message("assistant"):
            st.markdown(f"**Thay kịch bản hiện tại bằng bản mới {n} cảnh?** Các cảnh chưa có ảnh/video của bản cũ sẽ bị xóa (như ↺ Làm lại); "
                        "cảnh đã có ảnh được giữ.")
            a, b = st.columns(2)
            if a.button("Thay", key=f"box_replace_yes_{pid}", type="primary", width="stretch"):
                if act(lambda: resolve(p, pid, "replace")):
                    st.rerun()
            b.button("Hủy", key=f"box_replace_no_{pid}", on_click=resolve, args=(None, pid, "cancel"), width="stretch")
    elif ask:
        with st.chat_message("assistant"):
            st.markdown("Bạn dán một đoạn / vài cảnh khi đã có kịch bản. **Thêm vào kịch bản hiện tại hay thay thế?** Chưa có gì bị đổi.")
            a, b, c = st.columns(3)
            for col, choice, label in ((a, "add", "➕ Thêm vào"), (b, "swap", "🔁 Thay thế")):
                if col.button(label, key=f"box_ask_{choice}_{pid}", width="stretch"):    # in-run (not on_click): uses this run's Pipeline
                    resolve(p, pid, choice)
                    st.rerun()
            c.button("Hủy", key=f"box_ask_no_{pid}", on_click=resolve, args=(None, pid, "cancel"), width="stretch")


def _chat_ask(p: Pipeline, pid: int) -> None:
    """Người dùng 06/10: tin nhắn chưa rõ ý (vd một ý tưởng ngắn không kèm câu yêu cầu) → HỎI LẠI bằng nút, chưa làm gì (0 USD).
    Chỉ nút 💬 gọi Claude (giá trên nhãn); 💡 / 📜 đi đúng luồng cũ (ý tưởng → Biên kịch với nút có giá; kịch bản → ▶ Phân tích)."""
    from core import script_chat as Chat, cost
    k, ss = _keys(pid), st.session_state
    text = ss.get(k["chatask"]) or ""
    est = cost.llm_estimate(p.conn, Chat.STAGE, 1) or 0.0
    with st.chat_message("assistant"):
        st.markdown("**Bạn muốn làm gì với tin này?** Mình chưa chắc nên hỏi lại — chưa có gì chạy, chưa tốn tiền.")
        a, b, c, d = st.columns([1.3, 1.3, 1.1, 0.7])
        if a.button("💡 Dùng làm ý tưởng", key=f"box_chatask_idea_{pid}", width="stretch"):
            _chat_choose(p, pid, "idea")
            st.rerun()
        if b.button(f"💬 Hỏi Claude · ≈ ${est:.2f}", key=f"box_chatask_chat_{pid}", width="stretch"):
            ss.pop(k["chatask"], None)
            act(lambda: Chat.send(p, pid, text, llm_client(), record_user=False))
            st.rerun()
        if c.button("📜 Đây là kịch bản", key=f"box_chatask_script_{pid}", width="stretch"):
            _chat_choose(p, pid, "script")
            st.rerun()
        if d.button("Hủy", key=f"box_chatask_no_{pid}", width="stretch"):
            ss.pop(k["chatask"], None)
            Chat.append(p, pid, "assistant", "Đã bỏ qua tin này — chưa làm gì.")
            st.rerun()


def _chat_choose(p: Pipeline, pid: int, mode: str) -> None:
    from core import script_chat as Chat
    k, ss = _keys(pid), st.session_state
    text = ss.pop(k["chatask"], "") or ""
    _take(p, pid, text)
    ss[k["mode"]] = mode
    Chat.append(p, pid, "assistant", "Dùng làm **ý tưởng** — Biên kịch viết thành kịch bản; mỗi lượt có nút ghi giá, chưa chạy gì."
                if mode == "idea" else "Coi là **kịch bản** — bấm ▶ Phân tích để tách cảnh (0 USD).")


def script_view(p: Pipeline, pid: int, scenes) -> None:
    """S14.38: the script in use, read-only and folded — copy it (st.code has the button), edit it anywhere, paste it back into the chat."""
    text = (p.project(pid)["script_text"] or "").strip()
    if not text:
        return
    with st.expander(f"Xem kịch bản ({len(scenes)} cảnh)"):
        cap("Chỉ đọc. Bấm biểu tượng sao chép ở góc khung, sửa ở nơi bạn quen, rồi dán lại vào khung chat.")
        st.code(text, language=None, wrap_lines=True)


def script_box(p: Pipeline, pid: int, with_reset: bool = True) -> bool:
    """Same contract as step1.script_input (keys, return value: is there an input).
    S14.36 layout: the chat is the centre — messages on top, the input under them; 📎 and ✍ Sửa toàn văn are two small popovers beside
    the input (same keys up_/paste_), the ▶ Phân tích row sits right under the messages. The input is read FIRST (containers draw in order)."""
    from core import idea_to_script as I
    from dashboard.steps.step1 import analyse_script, reset_script_button
    k, ss = _keys(pid), st.session_state
    from core import script_chat as Chat
    body, foot = st.container(), st.container()
    with foot:
        got = st.chat_input("Dán kịch bản, gõ ý tưởng, trao đổi với Claude hoặc thả file…", key=k["chat"], accept_file=True,
                            file_type=list(script_reader.SUPPORTED))
        if got:
            incoming = got if isinstance(got, str) else (getattr(got, "text", None) or "")
            files = [] if isinstance(got, str) else list(getattr(got, "files", None) or [])
            kind = "script" if files else Chat.intent(incoming)
            if kind == "ask" and I.get_state(p.conn, pid).get("inputs"):
                kind = "idea"                                          # đang viết một ý tưởng: câu ngắn = "nói thêm" cho lượt kế (như cũ)
            if kind == "ask":                                          # người dùng 06/10: không chắc → hỏi lại, chưa làm gì, 0 USD
                Chat.append(p, pid, "user", incoming)
                ss[k["chatask"]] = incoming
            elif kind == "chat":
                with st.spinner("Claude đang trả lời…"):
                    act(lambda: Chat.send(p, pid, incoming, llm_client()))
            else:
                Chat.append(p, pid, "user", incoming or f"📎 {files[0].name}")
                if kind == "edit":
                    # Understanding is free; rewriting remains a separate priced action.
                    ss[k["wish"]] = incoming
                    Chat.append(p, pid, "assistant", "Đã nhận yêu cầu sửa cảnh. Kịch bản chưa đổi; dùng nút viết lại có giá ở trình sửa cảnh bên dưới.")
                else:
                    _take(p, pid, got)
                    Chat.append(p, pid, "assistant", "Đã nhận file kịch bản — bấm ▶ Phân tích (0 USD)." if files else
                                (receipt(incoming) or "Đã nhận nội dung. Chọn ý tưởng/kịch bản hoặc dùng các nút Biên kịch có giá bên dưới."))
    with body:
        older, recent = Chat.window(p, pid)
        if older:
            with st.expander(f"Xem {len(older)} tin cũ hơn"):
                _messages(older)
        _messages(recent)
    state = I.get_state(p.conn, pid)
    with body:
        if state.get("inputs"):                                        # the ceiling of this idea (mẫu step1_v2 meter)
            from dashboard.design import components as D
            spent = float(state.get("spent") or 0)
            st.html(D.meter(spent / I.RUN_CAP_USD, f"Biên kịch: đã dùng ≈ {spent:.3f} / {I.RUN_CAP_USD:g} USD cho ý tưởng này", invert=True))
        text, file = ss.get(k["text"], "") or "", ss.get(k["file"])
        mode = "script" if file else None
        if not file and not text.strip() and not state.get("inputs") and not ss.get(k["pending"]) and not ss.get(k["ask"]) and not recent:
            with st.chat_message("assistant"):
                st.markdown("Dán kịch bản (có tiêu đề **CẢNH 1 - …**) hoặc gõ vài dòng ý tưởng vào khung bên dưới; file thì thả vào khung. "
                            "Kịch bản và ý tưởng được nhận diện miễn phí; chat tự do gửi ngay tới Claude (chi phí ở 💵).")
        elif file or text.strip() or state.get("inputs"):
            with st.chat_message("assistant"):
                c = I.classify(text if text.strip() else (state.get("inputs") or {}).get("idea", ""))
                forced = ss.get(k["mode"])
                mode = mode or forced or c["kind"]
                if file:
                    st.markdown("Có file → đọc như **KỊCH BẢN** (▶ Phân tích tách cảnh, 0 USD). Nếu có cả file lẫn văn bản, hệ thống dùng file.")
                    if file:
                        st.button("✕ Bỏ file này", key=f"box_file_drop_{pid}", on_click=lambda: (ss.pop(k["file"], None), ss.pop(k["mode"], None)))
                else:
                    if mode == "script" and text.strip():
                        st.markdown("**" + (receipt(text, c) or "Đã nhận kịch bản — bấm ▶ Phân tích (0 USD).") + "**")
                    if mode == "idea" and ss.get(k["expand"]) and c["kind"] == "script":
                        st.markdown("Bạn " + ("yêu cầu" if ss[k["expand"]] == "request" else "đồng ý") + " **viết bổ sung chi tiết từ dàn ý / "
                                    "kịch bản này** → Biên kịch (giữ cảnh, nơi, thoại có sẵn). Đặt ⚙ Thiết lập + điểm then chốt, rồi mỗi lượt "
                                    f"bấm nút có ghi giá (cả 4 lượt ≈ ${I.expand_usd():.2f}).")
                    _verdict(pid, mode, bool(forced), c["why"])
                    if mode == "script":
                        sparse_offer(pid, text)
                if mode == "idea":
                    from dashboard.steps.step1_idea import idea_settings_form, idea_turns
                    idea_settings_form(p, pid, text or (state.get("inputs") or {}).get("idea", ""))
                    idea_turns(p, pid, ss.get(k["wish"], ""), used=lambda: ss.pop(k["wish"], None))
            if ss.get(k["wish"]):
                with st.chat_message("user"):
                    st.markdown(f"💬 **Nói thêm cho lượt kế:** {escape(ss[k['wish']])}")
                    cap("Đi kèm lượt Biên kịch kế tiếp (bấm nút có giá); để trống thì lượt đó gửi y như trước.")
                    w1, w2 = st.columns(2)
                    w1.button("✕ Bỏ lời này", key=f"box_wish_drop_{pid}", on_click=lambda: ss.pop(k["wish"], None))
                    w2.button("↪ Không, đây là ý tưởng mới", key=f"box_wish_as_idea_{pid}", on_click=_wish_to_idea, args=(pid,))
        if ss.get(k["expand_msg"]):
            with st.chat_message("assistant"):
                st.markdown(escape(ss[k["expand_msg"]]))
                st.button("✕ Đã hiểu", key=f"box_expand_msg_drop_{pid}", on_click=lambda: ss.pop(k["expand_msg"], None))
        _cards(p, pid)
        has_input = bool(file) or bool(text.strip())
        ready = bool(file) or (bool(text.strip()) and (mode or ss.get(k["mode"]) or I.classify(text)["kind"]) == "script")
        with st.chat_message("assistant"):
            if st.button("▶ Phân tích (tách cảnh) · 0 USD", disabled=not ready, type="primary", key=f"btn_analyse_{pid}"):
                if act(lambda: analyse_script(p, pid, None, text, file)):
                    ss.pop(k["file"], None)
                    Chat.append(p, pid, "assistant", "Đã phân tích và tách cảnh (0 USD).")
                    st.rerun()
        if with_reset:
            reset_script_button(p, pid)
    return has_input


def _messages(messages):
    for message in messages:
        with st.chat_message(message["role"]):
            text = message["text"]
            if len(text) > _SHOW_CHARS or len(text.splitlines()) > _SHOW_LINES:
                st.text(_preview(text))
                with st.expander("Xem đầy đủ"):
                    st.markdown(text)
            else:
                st.markdown(text)
