"""C5 (rà chuỗi ảnh → video 13/10): thẻ Bước 4 — khung cuối của shot đổi trạng thái (cờ end_frames). Trước: luồng bấm tay không bao giờ
vẽ khung cuối, clip gửi thiếu khung cuối im lặng, Dashboard không có chỗ xem / vẽ lại. Ở đây: ảnh khung cuối đang dùng, lý do khi clip
sẽ gửi KHÔNG kèm khung cuối, nút vẽ / vẽ lại có giá (người bấm = đồng ý chi; vẽ chạy ở vòng tự cập nhật của Bước 4, qua sổ chi)."""
import os

import streamlit as st

from core import cost, end_frames, image_models

DRAWING = "đang vẽ khung cuối"
NO_START = "chưa có ảnh khung đầu đã duyệt"


def card_block(p, pid: int, scene_id: int, act) -> None:
    """Nothing when the feature is off or the shot needs no end frame."""
    if not end_frames.enabled():
        return
    why = end_frames.missing_reason(p.conn, scene_id)
    path = end_frames.usable_path(p.conn, scene_id)
    if not why and not path:
        return
    if path and os.path.exists(path):
        st.image(path, caption="🏁 Khung cuối gửi kèm clip", width=180)
    if why:
        st.caption(f"🏁 Khung cuối: {why}" + ("" if why == DRAWING else " — clip gửi KHÔNG kèm khung cuối"))
    if why in (DRAWING, NO_START):
        return
    try:
        tag = cost.image_button_tag(image_models.of_project(p.project(pid)), 1)
    except Exception:  # noqa: BLE001 - an estimate never hides the button; the money gate still checks at sending
        tag = " · chưa ước được giá"
    label = ("🔁 Vẽ lại khung cuối" if path else "🖼 Vẽ khung cuối") + tag
    if st.button(label, key=f"efr_{scene_id}", help="Vẽ 1 ảnh khung cuối cùng khung / ánh sáng với ảnh đầu, đúng end_state của shot"):
        act(lambda: end_frames.redo(p, scene_id))
        st.rerun()


def poll(p, pid: int, data_dir: str, video_runner=None) -> int:
    """Draw / download this project's queued end frames (the Bước 4 poll; the autopilot does its own). Returns how many became ready;
    a ready one lets its held clip go (submit_pending)."""
    if not end_frames.enabled() or not end_frames.pending(p, pid):
        return 0
    from core.adapters import factory
    from core.providers import ProviderError
    try:
        provider = factory.image_provider()
    except ProviderError as e:
        st.caption(f"⚠ Chưa vẽ được khung cuối: {e}")
        return 0
    if provider is None:
        st.caption("⚠ Chưa có nhà cung cấp ảnh (IMAGE_PROVIDER) — khung cuối chưa vẽ được, clip đang chờ")
        return 0
    counts = end_frames.tick(p, pid, provider, data_dir)
    if counts["ready"] and video_runner is not None:
        video_runner.submit_pending(pid)
    return counts["ready"]
