"""Khung "🧭 Trước khi chạy" ở Bước 1 (người dùng 10/10): MỘT expander gọn, mặc định đóng, tiêu đề tóm tắt số mục cần chú ý —
chỉ đọc (core.before_run.collect), 0 USD, KHÔNG nút mới (mỗi mục nói "sửa ở đâu")."""
import streamlit as st

from core import before_run


def box(conn, data_dir: str, pid: int) -> None:
    try:
        res = before_run.collect(conn, data_dir, pid)
    except Exception as e:  # noqa: BLE001 - the frame is information: never breaks Bước 1
        st.caption(f"🧭 Trước khi chạy: không đọc được ({type(e).__name__}: {str(e)[:160]})")
        return
    with st.expander(before_run.title(res), expanded=False):
        st.markdown(before_run.details_md(res))
