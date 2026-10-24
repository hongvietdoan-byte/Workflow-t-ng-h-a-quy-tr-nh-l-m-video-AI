"""Khung "🚧 Cổng ảnh → video" (cờ video_gate — core/video_gate.py): clip đang chờ vì ảnh khung đầu lệch nền 3D (kiểm nền ĐỎ). Mỗi
shot một dòng: lý do đo + ô lý do + nút "Bỏ qua kiểm nền" (bắt buộc có lý do). Vẽ lại ảnh ở Bước 2 thì cổng tự mở khi ảnh mới đạt.
R11 (rà S4): khung riêng cho clip chờ nhóm shot liền mạch — nút "Bỏ qua chờ nhóm" (bắt buộc có lý do)."""
import streamlit as st

from core import video_gate


def render(p, pid: int, data_dir: str, who=None, read_only: bool = False) -> None:
    if not video_gate.enabled():
        return
    try:
        rows = video_gate.red_images(p.conn, data_dir, pid)
        groups = video_gate.group_waits(p.conn, pid)
    except Exception as e:  # noqa: BLE001 - the panel never breaks the screen: said
        st.caption(f"🚧 Cổng ảnh → video: không đọc được ({type(e).__name__}: {e})")
        return
    if groups:
        _render_groups(p, groups, who, read_only)
    if not rows:
        return
    with st.expander(f"🚧 Cổng ảnh → video: {len(rows)} clip giữ vì ảnh khung đầu lệch nền 3D", expanded=True):
        st.caption("Clip chưa gửi (0 USD) tới khi ảnh khung đầu khớp render 3D. Vẽ lại ảnh ở Bước 2, hoặc chấp nhận nền này kèm lý do.")
        for r in rows:
            st.markdown(f"🔴 **S{r['idx']:02d}** (ảnh job {r['image_job_id']}): {r['msg']}")
            if read_only:
                continue
            a, b = st.columns([5, 1.4], vertical_alignment="bottom")
            minimum = video_gate.minimum_skip_reason_length()
            reason = a.text_input("Lý do bỏ qua", key=f"vg_why_{r['image_job_id']}",
                                  placeholder="vd. nền lệch nhẹ, không thấy trong clip",
                                  help=f"Cần lý do có nghĩa, tối thiểu {minimum} ký tự.")
            if b.button("Bỏ qua kiểm nền", key=f"vg_skip_{r['image_job_id']}", disabled=len(reason.strip()) < minimum):
                try:
                    video_gate.skip(p.conn, r["image_job_id"], reason, who,
                                    session_token=st.session_state.get("auth_token"))
                except (ValueError, PermissionError, RuntimeError) as e:
                    st.error(str(e))
                else:
                    st.rerun()


def _render_groups(p, groups, who, read_only: bool) -> None:
    """R11 (rà S4): clip chờ cả nhóm shot liền mạch duyệt ảnh — đường thoát: duyệt / bỏ ảnh ở Bước 2, hoặc Bỏ qua chờ nhóm có lý do."""
    with st.expander(f"🚧 Cổng ảnh → video: {len(groups)} clip chờ cả nhóm shot liền mạch duyệt ảnh", expanded=True):
        st.caption("Clip chưa gửi (0 USD) tới khi các shot cùng nhóm đã duyệt ảnh (tránh gen trước khi shot kề đổi nền). Duyệt / bỏ ảnh "
                   "ở Bước 2, hoặc gửi luôn kèm lý do.")
        for r in groups:
            st.markdown(f"🟡 **S{r['idx']:02d}** (ảnh job {r['image_job_id']}): " + ", ".join(r["missing"][:6]))
            if read_only:
                continue
            a, b = st.columns([5, 1.4], vertical_alignment="bottom")
            minimum = video_gate.minimum_skip_reason_length()
            reason = a.text_input("Lý do gửi không chờ nhóm", key=f"vg_gwhy_{r['image_job_id']}",
                                  placeholder="vd. shot kề không đổi nền, chỉ chờ duyệt",
                                  help=f"Cần lý do có nghĩa, tối thiểu {minimum} ký tự.")
            if b.button("Bỏ qua chờ nhóm", key=f"vg_gskip_{r['image_job_id']}", disabled=len(reason.strip()) < minimum):
                try:
                    video_gate.skip(p.conn, r["image_job_id"], reason, who, group=True,
                                    session_token=st.session_state.get("auth_token"))
                except (ValueError, PermissionError, RuntimeError) as e:
                    st.error(str(e))
                else:
                    st.rerun()
