"""Khung chat Kịch bản nhận mọi tệp (người dùng 07/10, Khủng Long Đỏ mục 10 — Đợt 1; cờ `chat_first`, core/chat_intake.py).

Ảnh / video / nhạc thả vào ô chat: chắc → gắn ngay + một dòng ✅ trong chat; không chắc → một thẻ hỏi lại ngay trong luồng chat
(chọn vai, tên / nhân vật / cảnh, ✔ Gắn hoặc ✖ Bỏ). Không gọi model; phân tích ảnh phong cách bằng Claude là nút có giá riêng."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from core import chat_intake as I
from core import script_chat as Chat

_NO_ONE = "— chưa gắn cho ai —"


def handle_files(p: Pipeline, pid: int, files, text: str) -> None:
    """The media files of one chat message → the inbox; the sure ones are put in place at once, the others are asked in the chat."""
    media = [(f.name, f.getvalue()) for f in files if I.file_type(f.name) != "script"]
    if not media:
        return
    try:
        items = I.receive(p, C.DATA, pid, media, text)
    except ERRORS as e:
        Chat.append(p, pid, "assistant", f"⚠ {e}")
        return
    for it in items:
        if not it["sure"]:
            Chat.append(p, pid, "assistant", f"❓ “{it['file']}” dùng làm gì? Chọn ở thẻ ngay dưới ({it['why']}).")
            continue
        try:
            msg = I.apply(p, C.DATA, pid, it["id"], it["role"], name=it["name"], who=it["who"], scene=it["scene"])
        except (*ERRORS, assets.AssetError) as e:
            Chat.append(p, pid, "assistant", f"⚠ “{it['file']}”: {e} — chọn lại ở thẻ ngay dưới.")
        else:
            Chat.append(p, pid, "assistant", f"✅ {msg} · nhận ra vì {it['why']}.")


def _preview(it) -> None:
    if it["type"] == "image":
        try:
            st.image(it["path"], width=110)
        except Exception as e:  # noqa: BLE001 - a broken picture must not take the whole tab down; said instead
            st.caption(f"⚠ Không xem trước được ảnh ({type(e).__name__}) — tệp có thể hỏng.")
    elif it["type"] == "audio":
        st.audio(it["path"])
    else:
        st.markdown("🎞")


def pending_cards(p: Pipeline, pid: int) -> None:
    """One ask-back card per waiting file, inside the chat (the ✔ Gắn button puts it where the chosen role says)."""
    try:
        for line in I.retry_waiting(p, C.DATA, pid):              # Đợt 2: video động tác chờ motion prompt → tự gắn khi cảnh đã có
            Chat.append(p, pid, "assistant", "✅ " + line + " (cảnh vừa có motion prompt).")
    except (*ERRORS, assets.AssetError) as e:
        st.error(f"Chưa tự gắn được video chờ: {e}")
    items = I.pending(C.DATA, pid)
    if not items:
        return
    names = I.known_names(p.conn, pid)
    bible = [r[0] for r in p.conn.execute("SELECT name FROM characters WHERE project_id=? ORDER BY id", (pid,))]
    idxs = [r[0] for r in p.conn.execute("SELECT idx FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
    for it in items:
        k = f"ci_{pid}_{it['id']}"
        with st.chat_message("assistant"), st.container(border=True):
            a, b = st.columns([1, 4], vertical_alignment="top")
            with a:
                _preview(it)
            with b:
                st.markdown(f"**{escape(it['file'])}** dùng làm gì?")
                roles = list(I.ROLES_BY_TYPE[it["type"]])
                role = st.radio("Dùng làm", roles, index=roles.index(it["role"]) if it["role"] in roles else None, horizontal=True,
                                format_func=I.ROLES.get, key=f"{k}_role", label_visibility="collapsed")
                name = who = scene = None
                if role in I.NEEDS_NAME:
                    opts = names
                    name = st.selectbox("Tên", opts, index=opts.index(it["name"]) if it["name"] in opts else None, key=f"{k}_name",
                                        accept_new_options=True, placeholder="chọn hoặc gõ tên mới")
                elif role == "outfit":
                    opts = [_NO_ONE] + bible
                    who = st.selectbox("Của nhân vật", opts, index=opts.index(it["who"]) if it["who"] in opts else 0, key=f"{k}_who")
                    who = None if who == _NO_ONE else who
                    if not bible:
                        cap("Chưa có Character Bible (chạy Director trước) — ảnh vẫn lưu vào Kho, gắn cho nhân vật sau.")
                    name = st.text_input("Tên bộ đồ (để trống: “<nhân vật> — trang phục”)", key=f"{k}_label")
                elif role == "motion_ref":
                    scene = st.selectbox("Cho cảnh", idxs, index=idxs.index(it["scene"]) if it["scene"] in idxs else None,
                                         format_func=lambda i: f"Cảnh {i}", key=f"{k}_scene", placeholder="chọn cảnh")
                c1, c2 = st.columns(2)
                if c1.button("✔ Gắn", type="primary", disabled=role is None, key=f"{k}_go", width="stretch"):
                    try:
                        msg = I.apply(p, C.DATA, pid, it["id"], role, name=name, who=who, scene=scene)
                    except (*ERRORS, assets.AssetError) as e:
                        st.error(str(e))
                    else:
                        Chat.append(p, pid, "assistant", "✅ " + msg)
                        st.rerun()
                if c2.button("✖ Bỏ tệp", key=f"{k}_drop", width="stretch"):
                    I.drop(C.DATA, pid, it["id"])
                    Chat.append(p, pid, "assistant", f"Đã bỏ “{it['file']}”.")
                    st.rerun()


def style_offer(p: Pipeline, pid: int) -> None:
    """Pictures saved as style from the chat → the ONE priced button that drafts the World Bible from them (skill style-analyst)."""
    folder = os.path.join(C.DATA, str(pid), "style_refs")
    paths = sorted(os.path.join(folder, f) for f in os.listdir(folder)) if os.path.isdir(folder) else []
    if not paths or st.session_state.get(f"wb_draft_{pid}"):
        return
    n = min(len(paths), style.MAX_REFS)
    llm = llm_client()
    with st.chat_message("assistant"):
        st.markdown(f"Có **{len(paths)} ảnh phong cách**. Claude soạn nháp World Bible từ {n} ảnh — bạn xem và Lưu ở ⚙ Chi tiết.")
        if st.button("🤖 Phân tích ảnh phong cách" + cost.llm_tag(cost.llm_estimate(p.conn, "style", 1, images=n), 1),
                     key=f"ci_style_{pid}", disabled=llm is None, help=None if llm else claude_hint()):
            from dashboard.steps.step1_prep import WB_LABELS
            try:
                draft = style.analyse(llm, paths, note=lambda m: diag.record(p.conn, "director", "warn", m, "bad_json_retry", pid))
            except ERRORS as e:
                st.error(str(e))
            else:
                for key, _, _ in WB_LABELS:
                    st.session_state[f"wb_{key}_{pid}"] = draft.get(key) or ""
                st.session_state[f"wb_draft_{pid}"] = draft
                Chat.append(p, pid, "assistant", "Đã soạn nháp World Bible từ ảnh phong cách — mở ⚙ Chi tiết › 🎨 Phong cách để xem và Lưu.")
                st.rerun()


def guide_bubble(p: Pipeline, pid: int) -> None:
    """Đợt 2: after the analysis, the Đạo diễn says the next thing to do in the chat with the ONE primary button of the moment (the hero
    of the screen no longer draws it when chat_first is on — same keys, same functions: step1_v2._primary_action)."""
    from core import chat_flow as F
    from dashboard.steps import step1_v2 as V
    from dashboard.steps.step1 import _lock_and_go
    scenes = p.conn.execute("SELECT idx, title, state, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    if not scenes:
        return
    chars = p.conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,)).fetchall()
    s = F.state(p, pid)
    b_on, b_locked, b_total, b_spent = V._budget_state(p, pid)
    kind = V.next_kind(p, pid, scenes, chars, s["locked"], b_locked, b_on)
    try:
        from core import asset_checklist
        missing = (asset_checklist.get(p, pid) or {}).get("missing") or []
    except Exception:  # noqa: BLE001 - a hint only; the checklist panel says its own errors
        missing = []
    with st.chat_message("assistant"):
        line = F.guide(kind, s, missing, len(I.pending(C.DATA, pid)))
        if line:
            st.markdown(line)
        V._primary_action(p, pid, kind, scenes, chars, b_total, b_spent, _lock_and_go)
