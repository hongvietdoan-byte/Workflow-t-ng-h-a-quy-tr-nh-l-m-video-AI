"""Ảnh / video thả vào chat Kịch bản khi cờ chat_first TẮT (người dùng 09/10; core/chat_refs.py): mỗi tệp chờ một thẻ trong luồng chat
— ảnh thu nhỏ / tên video + NÚT chọn vai (luật "đầu vào mơ hồ thì hỏi lại bằng nút, 0 USD"):
📄 Ảnh trang kịch bản (đọc chữ · ≈ giá — lời gọi Claude DUY NHẤT, chỉ khi bấm) · 🏙 Bối cảnh · 🪑 Đồ vật · 🧍 Nhân vật · 🎬 Video tham khảo · Hủy.
Nút bấm trong lượt chạy (không on_click, không fragment) → dùng Pipeline của lượt này. Tệp đã nằm trên đĩa từ lúc thả (một lần);
mỗi lần vẽ lại chỉ đọc pending.json + ảnh thu nhỏ có cache, không đọc lại video."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from core import chat_intake as Intake, chat_refs
from core import script_chat as Chat

IMAGE_ROLES = (("location", "🏙 Bối cảnh"), ("prop", "🪑 Đồ vật"), ("character", "🧍 Nhân vật"))


def _thumb(it) -> None:
    if it["type"] == "image":
        try:
            st.image(assets.thumbnail(it["path"], 220), width=110)
        except Exception as e:  # noqa: BLE001 - a broken picture must not take the tab down; said instead
            st.caption(f"⚠ Không xem trước được ảnh ({type(e).__name__}) — tệp có thể hỏng.")
    else:
        try:
            mb = os.path.getsize(it["path"]) / 1e6
        except OSError:
            mb = 0.0
        st.markdown(f"🎞 **{escape(it['file'])}**  \n{mb:.1f} MB")


def page_label(conn) -> str:
    usd = chat_refs.estimate(conn)
    return "📄 Ảnh trang kịch bản (đọc chữ · " + (f"≈ {usd:.2f} USD)" if usd is not None else "chưa có giá)")


def read_page(p: Pipeline, pid: int, it) -> bool:
    """(a) The priced click: Claude reads the page → the text goes into the script flow exactly like a paste (box_text → classify → ▶ Phân
    tích / auto split). Pages read one after another are joined (a script of several photographed pages)."""
    from dashboard.steps import step1_box as Box
    k, ss = Box._keys(pid), st.session_state
    out = {}
    if not act(lambda: out.setdefault("text", chat_refs.read_page(p, C.DATA, pid, it["id"], C.llm_client()))):
        return False
    text = out["text"]
    # rà 09/10: dự án đã có cảnh → _take đẩy trang trước sang pending / ask (và xóa text) — lấy chữ ở khóa đang có, theo thứ tự đó
    prev = next((t for t in ((ss.get(k[x]) or "").strip() for x in ("pending", "ask", "text")) if t), "") if ss.get(f"box_ocr_{pid}") else ""
    Chat.append(p, pid, "assistant", f"📄 Đã đọc chữ từ “{it['file']}” ({len(text):,} ký tự, Claude — đã ghi sổ chi):".replace(",", ".")
                + "\n\n" + text)
    Box._take(p, pid, (prev + "\n\n" + text) if prev else text)
    ss[f"box_ocr_{pid}"] = True
    rec = Box.receipt(ss.get(k["text"]) or "")
    if rec:
        Chat.append(p, pid, "assistant", rec)
    return True


def ref_list(p: Pipeline, pid: int) -> None:
    """Rà 09/10: danh sách tư liệu đã ghi (vào prompt Biên kịch / Đạo diễn) — xem + 🗑 bỏ từng dòng; hiện cả khi chưa có cảnh."""
    refs = chat_refs.items(p.conn, pid)
    if not refs:
        return
    with st.expander(f"📎 Tư liệu tham khảo ({len(refs)})"):
        for r in refs:
            a, b = st.columns([6, 1], vertical_alignment="center")
            a.markdown(f"**{escape(chat_refs.ROLE_LABELS.get(r.get('role'), str(r.get('role'))))}** · {escape(r.get('label') or '')}"
                       + (f" — “{escape(r['note'])}”" if r.get("note") else "") + f"  \n<small>tệp {escape(str(r.get('file') or ''))}</small>",
                       unsafe_allow_html=True)
            if b.button("🗑", key=f"crl_{pid}_{r.get('id')}", help="Bỏ tư liệu này khỏi danh sách (tệp trên đĩa giữ nguyên)"):
                if act(lambda r=r: access.need_edit(p, pid, "bỏ tư liệu") or chat_refs.remove(p.conn, pid, r.get("id"))):
                    Chat.append(p, pid, "assistant", f"Đã bỏ tư liệu “{r.get('label')}” khỏi danh sách — Biên kịch / Đạo diễn không đọc nữa.")
                    st.rerun()


def ref_cards(p: Pipeline, pid: int) -> None:
    items = Intake.pending(C.DATA, pid)
    for it in items:
        k = f"cr_{pid}_{it['id']}"
        with st.chat_message("assistant"), st.container(border=True):
            a, b = st.columns([1, 4], vertical_alignment="top")
            with a:
                _thumb(it)
            with b:
                st.markdown(f"**{escape(it['file'])}** dùng làm gì?" + (f" · ghi chú: “{escape(it['text'])}”" if it.get("text") else ""))
                if it["type"] not in ("image", "video"):
                    st.caption("Loại tệp này chưa dùng được ở đây (bật cờ chat_first để dùng nhạc).")
                    if st.button("Hủy", key=f"{k}_drop"):
                        Intake.drop(C.DATA, pid, it["id"])
                        st.rerun()
                    continue
                label = st.text_input("Nhãn (tên bối cảnh / đồ vật / nhân vật / video)", value=it.get("name") or "", key=f"{k}_label",
                                      placeholder="vd Nhà Kelly · Thùng thính · Kelly")
                role, page = None, False
                if it["type"] == "image":
                    page = st.button(page_label(p.conn), key=f"{k}_page", type="primary",
                                     help="Claude chép chữ trên ảnh thành kịch bản (một lời gọi, ghi sổ chi). Chỉ chạy khi bấm.")
                    cols = st.columns(len(IMAGE_ROLES) + 1)
                    for col, (r, lab) in zip(cols, IMAGE_ROLES):
                        if col.button(lab, key=f"{k}_{r}", width="stretch"):
                            role = r
                    drop = cols[-1].button("Hủy", key=f"{k}_drop", width="stretch")
                else:
                    c1, c2 = st.columns([3, 1])
                    if c1.button("🎬 Video tham khảo", key=f"{k}_video_ref", width="stretch"):
                        role = "video_ref"
                    drop = c2.button("Hủy", key=f"{k}_drop", width="stretch")
                if page and read_page(p, pid, it):
                    st.rerun()
                if role:
                    try:
                        msg = Intake.apply(p, C.DATA, pid, it["id"], role, name=label)
                    except (*ERRORS, assets.AssetError) as e:
                        st.error(str(e))
                    else:
                        Chat.append(p, pid, "assistant", "✅ " + msg + " · Biên kịch / Đạo diễn sẽ đọc tên + ghi chú (dạng chữ).")
                        st.rerun()
                if drop:
                    Intake.drop(C.DATA, pid, it["id"])
                    Chat.append(p, pid, "assistant", f"Đã bỏ “{it['file']}” — chưa làm gì.")
                    st.rerun()
