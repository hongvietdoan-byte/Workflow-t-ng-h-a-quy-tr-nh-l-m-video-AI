"""Callback người bấm: dùng lại nghiệp vụ và cổng hiện hành, không vòng tự gửi."""
import math
from copy import copy

from core import access, simple_budget


def selected_send_ready():
    """Giai đoạn 1 HOLD cả lô; chỉ mở sau core port CX24-M82B đã được nghiệm thu.

    Không là cờ môi trường/tùy chọn người dùng: simple_mode không mở đường gửi này.
    """
    return False


def _actor(p, pid, *, confirmed=False, paid=False):
    if not simple_budget.enabled():
        raise PermissionError("Chế độ Cơ bản chưa được bật")
    if not confirmed:
        raise ValueError("Cần người bấm xác nhận thao tác")
    who = simple_budget.current_user(p, pid)
    access.require(p.conn, pid, who, need="edit", action="thao tác ở chế độ Cơ bản")
    if paid and p.project(pid)["paused"]:
        raise ValueError("Đã tạm dừng — không gửi job mới")
    # Giữ kết nối/transaction hiện hành, tách identity khỏi Pipeline dùng chung.
    context = copy(p)
    context.user = dict(who) if who else None
    context.actor = who["email"] if who else "user"
    context.origin = None  # thao tác người bấm, không kế thừa ngữ cảnh autopilot
    return context


def pause(p, pid, paused):
    p = _actor(p, pid, confirmed=True)
    p.set_paused(pid, bool(paused))


def save_idea(p, pid, text):
    p = _actor(p, pid, confirmed=True)
    from core import idea_to_script
    return idea_to_script.start(p.conn, pid, text, p=p)


def use_script(p, pid, text):
    p = _actor(p, pid, confirmed=True)
    from core import idea_to_script
    if "inputs" not in idea_to_script.get_state(p.conn, pid):
        # Nhập kịch bản trực tiếp không bắt buộc đã gửi ý tưởng trước đó.
        idea_to_script.start(p.conn, pid, text, p=p)
    idea_to_script.edit(p.conn, pid, text, p=p)
    return idea_to_script.use_script(p, pid)


def quote(p, pid, data_dir, kind):
    """Báo giá đúng lớp hiện có, ràng buộc cùng tập đầu vào và job chưa gửi."""
    if not selected_send_ready():
        raise ValueError("Đang giữ cả lô — chưa bảo đảm tập job gửi (chờ CX24-M82B)")
    from core import batch, cost, gen_auth, image_models
    from dashboard.paid_batch_preview import fingerprint
    pricing = cost.load_pricing()
    if kind == "images":
        est = cost.estimate_images(p, pid, pricing, image_models.of_project(p.project(pid)), data_dir=data_dir)
        ids = batch.image_targets(p, pid, include_queued=True)
        jtype = "image_gen"
    elif kind == "videos":
        est = cost.estimate_videos_by_scene(p, pid, pricing)
        ids = [r["scene_id"] for r in batch.video_plan(p, pid) if r["kind"] == "new"]
        jtype = "video_gen"
    else:
        raise ValueError("Thao tác không có trong luồng Cơ bản")
    usd = est.get("total")
    if isinstance(usd, bool) or not isinstance(usd, (int, float)) or not math.isfinite(usd) or usd < 0 or est.get("incomplete"):
        raise ValueError("Chưa đủ báo giá để gửi")
    if not ids:
        raise ValueError("Không có cảnh mới đủ điều kiện gửi")
    for sid in ids:
        used = gen_auth.attempts(p.conn, sid, jtype, since=gen_auth.cycle_start(data_dir, pid, sid, jtype))
        if len(used) >= gen_auth.LIMITS[jtype]:
            raise ValueError("Đang giữ — có cảnh đã hết lượt, cần EP xem riêng")
    return {"usd": usd, "ids": list(ids), "fp": fingerprint(p, pid, "basic_" + kind, data_dir)}


def send(p, pid, data_dir, kind, *, confirmed=False, expected_quote=None):
    """Chỉ initial send; retry/reject/reopen/voice/music dành pha B."""
    p = _actor(p, pid, confirmed=confirmed, paid=True)
    if not selected_send_ready():
        raise ValueError("Đang giữ cả lô — chưa bảo đảm tập job gửi (chờ CX24-M82B)")
    from core import batch
    from dashboard import common as C, paid_confirm
    if not paid_confirm.enabled():
        raise PermissionError("Chờ bật lớp xác nhận giá trước khi gửi từ chế độ Cơ bản")
    if expected_quote is None or quote(p, pid, data_dir, kind) != expected_quote:
        raise ValueError("Tập cảnh hoặc báo giá đã đổi — xem lại và xác nhận")
    if kind == "images":
        # Không dùng confirmed=True để bỏ qua cổng image_gates.
        runner = C.image_runner(p)
        if runner is None:
            raise ValueError("Chưa cấu hình dịch vụ ảnh — chưa xếp hàng")
        result = batch.queue_images(p, pid, confirmed=False, data_dir=data_dir)
    elif kind == "videos":
        runner = C.video_runner(p)
        if runner is None:
            raise ValueError("Chưa cấu hình dịch vụ video — chưa xếp hàng")
        # Không kèm cảnh cũ; giữ đúng danh sách mới do luồng hiện có tính.
        plan = batch.video_plan(p, pid)
        ids = [r["scene_id"] for r in plan if r["kind"] == "new"]
        result = batch.queue_videos(p, pid, data_dir, only=ids)
    else:
        raise ValueError("Thao tác không có trong luồng Cơ bản")
    result["sent"] = runner.submit_pending(pid)
    return result
