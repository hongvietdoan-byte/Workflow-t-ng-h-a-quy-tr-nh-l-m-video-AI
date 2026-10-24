"""Callback người bấm: dùng lại nghiệp vụ và cổng hiện hành, không vòng tự gửi."""
from core import access, simple_budget


def _actor(p, pid, *, confirmed=False, paid=False):
    if not confirmed:
        raise ValueError("Cần người bấm xác nhận thao tác")
    who = simple_budget.current_user(p, pid)
    access.require(p.conn, pid, who, need="edit", action="thao tác ở chế độ Cơ bản")
    if paid and p.project(pid)["paused"]:
        raise ValueError("Đã tạm dừng — không gửi job mới")
    p.user = who
    p.actor = who["email"] if who else "user"
    return who


def pause(p, pid, paused):
    _actor(p, pid, confirmed=True)
    p.set_paused(pid, bool(paused))


def save_idea(p, pid, text):
    _actor(p, pid, confirmed=True)
    from core import idea_to_script
    return idea_to_script.start(p.conn, pid, text, p=p)


def use_script(p, pid, text):
    _actor(p, pid, confirmed=True)
    from core import idea_to_script
    idea_to_script.edit(p.conn, pid, text, p=p)
    return idea_to_script.use_script(p, pid)


def send(p, pid, data_dir, kind, *, confirmed=False):
    """Chỉ initial send; retry/reject/reopen/voice/music dành pha B."""
    _actor(p, pid, confirmed=confirmed, paid=True)
    from core import batch
    from dashboard import common as C, paid_confirm
    if not paid_confirm.enabled():
        raise PermissionError("Chờ bật lớp xác nhận giá trước khi gửi từ chế độ Cơ bản")
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
