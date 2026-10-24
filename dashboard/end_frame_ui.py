"""C5 (rà chuỗi ảnh → video 13/10): thẻ Bước 4 — khung cuối của shot đổi trạng thái (cờ end_frames). Trước: luồng bấm tay không bao giờ
vẽ khung cuối, clip gửi thiếu khung cuối im lặng, Dashboard không có chỗ xem / vẽ lại. Ở đây: ảnh khung cuối đang dùng, lý do khi clip
sẽ gửi KHÔNG kèm khung cuối, nút vẽ / vẽ lại có giá (người bấm = đồng ý chi; vẽ chạy ở vòng tự cập nhật của Bước 4, qua sổ chi).

Vòng sửa sau rà S3 (RA_S3_S4 R1/R3): vòng tự cập nhật chỉ vẽ hàng NGƯỜI bấm (không vẽ hàng chạy tự động đã xếp khi chạy tự động dừng —
thẻ nói lý do + hiện nút có giá), không chạy với người chỉ xem, vẽ xong chỉ gửi clip của đúng shot đó; shot vật kỹ năng không có nút;
khung cuối runner đã bỏ lúc gửi thì thẻ nói "đã vẽ nhưng KHÔNG gửi" kèm lý do."""
import os

import streamlit as st
from dashboard import paid_confirm as P  # noqa: E402  (M8.0b: nút tốn tiền = giá + xác nhận một lần, cờ safe_paid_buttons)

from core import cost, end_frames, image_models

DRAWING = "đang vẽ khung cuối"
NO_START = "chưa có ảnh khung đầu đã duyệt"
NO_BUTTON = (DRAWING, NO_START, end_frames.SKILL_SKIP)


def card_block(p, pid: int, scene_id: int, act, runner=None) -> None:
    """Nothing when the feature is off or the shot needs no end frame."""
    if not end_frames.enabled():
        return
    why = end_frames.missing_reason(p.conn, scene_id)
    path = end_frames.usable_path(p.conn, scene_id)
    if not why and not path:
        return
    if path and os.path.exists(path):
        dropped = end_frames.dropped_reason(p.conn, scene_id, path)
        if dropped:
            st.image(path, caption="🏁 Khung cuối đã vẽ (lần gửi gần nhất không dùng)", width=180)
            st.caption(f"🏁 Khung cuối đã vẽ nhưng KHÔNG gửi: {dropped}")
        else:
            st.image(path, caption="🏁 Khung cuối gửi kèm clip", width=180)
    if why:
        st.caption(f"🏁 Khung cuối: {why}" + ("" if why == DRAWING else " — clip gửi KHÔNG kèm khung cuối"))
    _send_without(p, pid, scene_id, act, runner)
    if why in NO_BUTTON:
        return
    try:
        tag = cost.image_button_tag(image_models.of_project(p.project(pid)), 1)
    except Exception:  # noqa: BLE001 - an estimate never hides the button; the money gate still checks at sending
        tag = " · chưa ước được giá"
    label = "🔁 Vẽ lại khung cuối" if path else "🖼 Vẽ khung cuối"
    # rà M8.0c: vẽ khung cuối = 1 lần gen ảnh trả phí (Bước 4 vẽ hàng đã hỏi) → giá + xác nhận (cờ TẮT: nhãn như cũ)
    if P.paid_button(label, key=f"efr_{scene_id}", tag=tag, container=st,
                     help="Vẽ 1 ảnh khung cuối cùng khung / ánh sáng với ảnh đầu, đúng end_state của shot"):
        act(lambda: end_frames.redo(p, scene_id))
        st.rerun()


def _send_without(p, pid: int, scene_id: int, act, runner) -> None:
    """C3 (người dùng 14/10): the clip waits for an end frame nobody draws now (the automatic run stopped) — the person may send it
    without one. Price of the clip on the button; the reason goes to the clip's history (core/end_frames.send_without)."""
    from dashboard import common as C
    if C.read_only(p, pid) or not end_frames.held_without_autopilot(p.conn, scene_id):
        return
    try:
        tag = cost.price_tag(cost.clip_estimate(p.conn, scene_id))
    except Exception:  # noqa: BLE001 - an estimate never hides the button; the money gate still checks at sending
        tag = " · chưa ước được giá"
    if P.paid_button("▶ Gửi clip KHÔNG kèm khung cuối", key=f"efoff_{scene_id}", tag=tag, container=st,
                     help="Chạy tự động đã dừng nên không ai vẽ khung cuối: gửi clip ngay, cảnh kết theo prompt (không theo end_state vẽ). "
                      "Muốn có khung cuối thì bấm “🖼 Vẽ khung cuối” thay vì nút này."):
        who = (C.me().get("email") or None) if C.auth_on() else None
        done = {}
        if act(lambda: done.setdefault("jobs", end_frames.send_without(p, scene_id, who))) and done.get("jobs") and runner is not None:
            act(lambda: runner.submit_pending(pid, only=done["jobs"]))
        st.rerun()


def poll(p, pid: int, data_dir: str, video_runner=None) -> int:
    """Draw / download the end frames a PERSON asked for on this project (the Bước 4 poll; the autopilot draws its own). Returns how
    many became ready; a ready one lets its own held clip go (submit_pending only=[that shot's queued clip])."""
    if not end_frames.enabled():
        return 0
    ids = end_frames.asked_ids(p, pid)
    if not ids:
        return 0
    from dashboard import common as C
    if C.read_only(p, pid):                            # R1 (b): a 'Chỉ xem' watcher never triggers a paid send
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
    counts = end_frames.tick(p, pid, provider, data_dir, only_ids=ids)
    if counts["ready"] and video_runner is not None:
        marks = ",".join("?" * len(ids))
        scenes = [r[0] for r in p.conn.execute(f"SELECT scene_id FROM end_frames WHERE id IN ({marks}) AND state='ready'", ids)]
        jobs = [r[0] for r in p.conn.execute(
            f"SELECT id FROM jobs WHERE type='video_gen' AND state='queued' AND scene_id IN ({','.join('?' * len(scenes))}) ORDER BY id",
            scenes)] if scenes else []
        if jobs:
            video_runner.submit_pending(pid, only=jobs)   # R1 (a): only the clip that waited for this end frame
    return counts["ready"]
