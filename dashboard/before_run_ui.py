"""Khung "🧭 Trước khi chạy" ở Bước 1 (người dùng 10/10): MỘT expander gọn, mặc định đóng, tiêu đề tóm tắt số mục cần chú ý —
chỉ đọc (core.before_run.collect), 0 USD; mỗi mục nói "sửa ở đâu". C1 (15/10): mục ĐỎ "cờ sửa lỗi dự án trước còn TẮT" có nút
"Bật các cờ sửa lỗi" (features.save_settings, đúng đường màn 🧪) + "Bỏ qua có lý do" theo từng cờ; còn mục đó thì khung mở sẵn."""
import streamlit as st

from core import before_run


def box(conn, data_dir: str, pid: int) -> None:
    try:
        res = before_run.collect(conn, data_dir, pid)
    except Exception as e:  # noqa: BLE001 - the frame is information: never breaks Bước 1
        st.caption(f"🧭 Trước khi chạy: không đọc được ({type(e).__name__}: {str(e)[:160]})")
        return
    try:
        pending = before_run.fix_flags_pending(conn, pid)
    except Exception as e:  # noqa: BLE001
        pending = []
        st.caption(f"🩹 Cờ sửa lỗi: không đọc được ({type(e).__name__}: {str(e)[:160]})")
    with st.expander(before_run.title(res), expanded=bool(pending)):
        st.markdown(before_run.details_md(res))
        if pending:
            _fix_flag_controls(conn, pid, pending)


def _fix_flag_controls(conn, pid: int, pending) -> None:
    from dashboard import common as C
    free = [n for n in pending if not before_run.costly_fix_flag(n)]
    costly = [n for n in pending if n not in free]
    if free and st.button(f"🩹 Bật các cờ sửa lỗi ({len(free)}, 0 USD)", key=f"fixflags_on_{pid}", type="primary",
                          help="Bật thật các cờ sửa lỗi dự án trước đang TẮT, trừ cờ tốn tiền (ghi như màn 🧪 Tính năng thử, áp dụng cả máy)"):
        before_run.enable_fix_flags(free)
        C.log_ui(None, "bat_co_sua_loi", page="buoc1", project_id=pid, detail=",".join(free))
        st.rerun()
    if costly:
        st.caption("Cờ tốn tiền không bật hàng loạt — bật riêng ở 🧪 sau khi xem giá: " + ", ".join(costly))
    every = f"(tất cả {len(pending)} cờ)"
    c1, c2, c3 = st.columns([2, 4, 1.4], vertical_alignment="bottom")
    name = c1.selectbox("Cờ", [every] + pending, key=f"fixflags_pick_{pid}")
    reason = c2.text_input("Lý do bỏ qua (bắt buộc)", key=f"fixflags_reason_{pid}")
    if c3.button("Bỏ qua có lý do", key=f"fixflags_skip_{pid}"):
        names = pending if name == every else [name]
        try:
            for n in names:
                before_run.skip_fix_flag(conn, pid, n, reason, who=(C.me() or {}).get("email") or C.op_source())
        except ValueError as e:
            st.error(str(e))
            return
        C.log_ui(None, "bo_qua_co_sua_loi", page="buoc1", project_id=pid, detail=f"{','.join(names)}: {reason}")
        st.rerun()
