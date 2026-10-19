"""Khung "🔎 Rà soát tác động" (cờ change_review — core/change_review.py): mục lệch còn mở sau mỗi thay đổi, mỗi mục một dòng + đề xuất
sửa + nút "✓ Đã sửa" / "Bỏ qua". Mục đỏ = gen tốn tiền của shot đang bị giữ; đóng mục (đã sửa / bỏ qua) thì lệnh chờ tự gửi tiếp."""
import streamlit as st

from core import change_review as CR

SOURCE_LABEL = {"claude": "Claude", CR.FAIL_SOURCE: "rà soát lỗi"}


def render(p, pid: int, who=None, read_only: bool = False, key: str = "cr") -> None:
    """`key`: tiền tố khóa nút — C4 (13/10) khung này hiện ở CẢ tab Ảnh (Bước 2) và tab Motion (Bước 3) trong cùng một lượt vẽ."""
    if not CR.enabled():
        return
    rows = CR.open_findings(p.conn, pid)
    spent = p.conn.execute("SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM change_events e WHERE state='reviewed' AND "
                           "(e.project_id=? OR e.scene_id IN (SELECT id FROM scenes WHERE project_id=?))", (pid, pid)).fetchone()
    red = sum(1 for r in rows if r["level"] == "do")
    head = (f"🔎 Rà soát tác động: {len(rows)} mục lệch đang mở" + (f" — 🔴 {red} mục giữ gen" if red else "")
            if rows else "🔎 Rà soát tác động: không có mục lệch")
    head += f" · đã rà {spent[0]} thay đổi, Claude ≈ {spent[1]:.2f} USD"
    with st.expander(head, expanded=bool(red)):
        if not rows:
            st.caption("Mỗi lần đổi kịch bản / shot / hồ sơ hay ảnh Kho, luật code + agent Claude rà các khâu liên quan (nền 3D, ảnh neo, câu "
                       "tả, motion, khung cuối, video, shot kề).")
            return
        for r in rows:
            tag = "🔴" if r["level"] == "do" else "🟡"
            shot = f"shot {r['idx']}" if r.get("idx") is not None else "chung"
            st.markdown(f"{tag} **{shot} · {r['khau']}** ({SOURCE_LABEL.get(r['source'], 'luật code')}): {r['msg']}"
                        + (f"  \n↳ đề xuất: {r['de_xuat']}" if r.get("de_xuat") else ""))
            if read_only:
                continue
            a, b, c = st.columns([1, 1, 6])
            if a.button("✓ Đã sửa", key=f"{key}_ok_{r['id']}"):
                CR.close(p.conn, r["id"], "resolved", who)
                st.rerun()
            if b.button("Bỏ qua", key=f"{key}_skip_{r['id']}", help="Chấp nhận lệch này — shot không bị giữ gen vì mục này nữa"):
                CR.close(p.conn, r["id"], "dismissed", who)
                st.rerun()
            if r["source"] == CR.FAIL_SOURCE and c.button("↻ Rà lại", key=f"{key}_rerun_{r['id']}",
                                                         help="G35: đã nạp tiền / hết lỗi — rà lại thay đổi này (giữ gen tới khi rà xong)"):
                try:
                    CR.rerun_failed(p.conn, r["id"], who)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
