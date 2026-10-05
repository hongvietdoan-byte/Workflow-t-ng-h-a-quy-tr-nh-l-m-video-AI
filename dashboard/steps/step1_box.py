"""Step 1 · khung nhập kịch bản hội thoại (S14.21, docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md Đợt 3; behind the flag
`idea_to_script` — off → the old 2 tabs of step1.script_input, exactly).

A conversation shell around priced widgets, NOT a free chat: one `st.chat_input` is the single way in for text (a pasted script, a raw
idea, or a "nói thêm" for the Biên kịch) and it NEVER calls a model. Code decides for 0 USD what the text is (idea_to_script.classify:
script → the old ▶ Phân tích split; idea → the Biên kịch's turns, each behind a button with its price; grey zone → ask, never guess —
luật 3), always with a one-click override. S14.38: the chat is the ONLY door in — no ✍ Sửa toàn văn (paste_) and no 📎 popover (up_): a file is dropped on the chat input
(same file types), the script in use is read-only under "Xem kịch bản" (st.code → copy, edit elsewhere, paste back into the chat).
A full script pasted while one is in use asks once before replacing it. Keys kept: btn_analyse_, btn_bad_reset_ (the flag-off tabs of
step1.script_input keep up_/paste_). No expander in the box itself: it sits inside the v2 "Nhập / thay" expander (C2)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard.steps.step1_v2 import cap, say  # noqa: F401

_SHOW_LINES, _SHOW_CHARS = 6, 400
_KIND_TEXT = {"script": "KỊCH BẢN", "idea": "Ý TƯỞNG"}


def _keys(pid: int) -> dict:
    return {"text": f"box_text_{pid}", "mode": f"in_mode_{pid}", "wish": f"box_wish_{pid}", "file": f"box_file_{pid}",
            "pending": f"box_pending_{pid}", "ask": f"box_ask_{pid}", "chat": f"box_in_{pid}"}


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
    body, foot = st.container(), st.container()                        # drawn in this order; the chat input is read FIRST (below)
    with foot:
        got = st.chat_input("Dán kịch bản, gõ ý tưởng, nói thêm cho Biên kịch, hoặc thả file (" +
                            " ".join(sorted(script_reader.SUPPORTED)) + ")…", key=k["chat"], accept_file=True,
                            file_type=list(script_reader.SUPPORTED))
        if got:
            _take(p, pid, got)
    state = I.get_state(p.conn, pid)
    with body:
        if state.get("inputs"):                                        # the ceiling of this idea (mẫu step1_v2 meter)
            from dashboard.design import components as D
            spent = float(state.get("spent") or 0)
            st.html(D.meter(spent / I.RUN_CAP_USD, f"Biên kịch: đã dùng ≈ {spent:.3f} / {I.RUN_CAP_USD:g} USD cho ý tưởng này", invert=True))
        text, file = ss.get(k["text"], "") or "", ss.get(k["file"])
        mode = "script" if file else None
        if not file and not text.strip() and not state.get("inputs") and not ss.get(k["pending"]) and not ss.get(k["ask"]):
            with st.chat_message("assistant"):
                st.markdown("Dán kịch bản (có tiêu đề **CẢNH 1 - …**) hoặc gõ vài dòng ý tưởng vào khung bên dưới; file thì thả vào khung. "
                            "Gõ vào khung không tốn tiền — chỉ nút có ghi giá mới gọi Claude.")
        else:
            with st.chat_message("user"):
                if file:
                    st.markdown(f"📎 {escape(file[0])}")
                if text.strip():
                    st.text(_preview(text))
                elif state.get("inputs"):
                    st.text(_preview(state["inputs"]["idea"]))
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
                    _verdict(pid, mode, bool(forced), c["why"])
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
        _cards(p, pid)
        has_input = bool(file) or bool(text.strip())
        ready = bool(file) or (bool(text.strip()) and (mode or ss.get(k["mode"]) or I.classify(text)["kind"]) == "script")
        if with_reset:
            u2, u3, u4 = st.columns([2.4, 1.2, 4], vertical_alignment="center")
        else:
            u2, u4 = st.columns([2.4, 5.2], vertical_alignment="center")
            u3 = None
        if u2.button("▶ Phân tích (tách cảnh)", disabled=not ready, type="primary", key=f"btn_analyse_{pid}"):
            if act(lambda: analyse_script(p, pid, None, text, file)):
                ss.pop(k["file"], None)
                st.rerun()
        u4.caption("Sẵn sàng · bấm ▶ Phân tích (0 USD)" if ready else
                   ("Ý tưởng → làm qua Biên kịch ở trên, hoặc bấm 'không phải, đây là kịch bản' để tách thẳng." if has_input
                    else "Dán kịch bản vào khung chat, rồi bấm Phân tích."))
        if with_reset:
            with u3:
                reset_script_button(p, pid)
    return has_input
