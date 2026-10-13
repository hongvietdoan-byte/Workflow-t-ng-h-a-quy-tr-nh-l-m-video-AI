"""Khung "🚧 Cổng ảnh → video" (cờ video_gate — core/video_gate.py): clip đang chờ vì ảnh khung đầu lệch nền 3D (kiểm nền ĐỎ). Mỗi
shot một dòng: lý do đo + ô lý do + nút "Bỏ qua kiểm nền" (bắt buộc có lý do). Vẽ lại ảnh ở Bước 2 thì cổng tự mở khi ảnh mới đạt."""
import streamlit as st

from core import video_gate


def render(p, pid: int, data_dir: str, who=None, read_only: bool = False) -> None:
    if not video_gate.enabled():
        return
    try:
        rows = video_gate.red_images(p.conn, data_dir, pid)
    except Exception as e:  # noqa: BLE001 - the panel never breaks the screen: said
        st.caption(f"🚧 Cổng ảnh → video: không đọc được ({type(e).__name__}: {e})")
        return
    if not rows:
        return
    with st.expander(f"🚧 Cổng ảnh → video: {len(rows)} clip giữ vì ảnh khung đầu lệch nền 3D", expanded=True):
        st.caption("Clip chưa gửi (0 USD) tới khi ảnh khung đầu khớp render 3D. Vẽ lại ảnh ở Bước 2, hoặc chấp nhận nền này kèm lý do.")
        for r in rows:
            st.markdown(f"🔴 **S{r['idx']:02d}** (ảnh job {r['image_job_id']}): {r['msg']}")
            if read_only:
                continue
            a, b = st.columns([5, 1.4], vertical_alignment="bottom")
            reason = a.text_input("Lý do bỏ qua", key=f"vg_why_{r['image_job_id']}", placeholder="vd. nền lệch nhẹ, không thấy trong clip")
            if b.button("Bỏ qua kiểm nền", key=f"vg_skip_{r['image_job_id']}", disabled=len(reason.strip()) < 3):
                video_gate.skip(p.conn, r["image_job_id"], reason, who)
                st.rerun()
