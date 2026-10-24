"""Dữ liệu đọc cho năm màn Cơ bản; không gửi job hay tự duyệt nội dung."""
from pathlib import Path

from core import budget, gen_auth, project_budget, simple_budget

SCREENS = ("Ý tưởng + ngân sách", "Kịch bản", "Ảnh", "Video", "Tải bản giao")


def budget_view(p, pid):
    approved = simple_budget.get(p.conn, pid)
    stages = project_budget.ledger_by_stage(p.conn, pid)
    has_holds = p.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='llm_holds'").fetchone()
    held = budget.held(p.conn, pid) if has_holds else 0.0
    result = simple_budget.utilization(approved, recorded=sum(stages.values()), held=held)
    result.update(approved=approved, stages=stages)
    return result


def load(p, pid, data_dir):
    identity = simple_budget.current_user(p, pid)
    proj = dict(p.project(pid))
    scenes = [dict(r) for r in p.conn.execute("SELECT * FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
    jobs = [dict(r) for r in p.conn.execute("SELECT * FROM jobs WHERE project_id=? ORDER BY id", (pid,))]
    # Dùng cùng bộ đếm E4; không có lệnh reset hay suy lượt từ retry_count.
    counted = gen_auth.project_jobs(p.conn, pid)
    for scene in scenes:
        scene["image_used"] = len(gen_auth.attempts_in(counted, scene["id"], "image_gen"))
        scene["video_used"] = len(gen_auth.attempts_in(counted, scene["id"], "video_gen"))
    from core import access, idea_to_script
    return {"project": proj, "scenes": scenes, "jobs": jobs, "budget": budget_view(p, pid),
            "idea": idea_to_script.get_state(p.conn, pid), "can_edit": access.can_edit(p.conn, pid, identity),
            "identity": identity, "data_dir": data_dir}


def latest_job(state, sid, kind):
    return next((j for j in reversed(state["jobs"]) if j["scene_id"] == sid and j["type"] == kind), None)


def media_path(data_dir, pid, raw):
    """Không dùng đường dẫn tùy ý/symlink ngoài thư mục dự án cho media/download."""
    if not raw:
        return None
    root = (Path(data_dir) / str(pid)).resolve()
    path = Path(raw).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def issue_cards(state):
    out = []
    for job in state["jobs"]:
        if job["state"] in ("failed", "rejected", "escalated"):
            out.append({"what": "Cảnh chưa đạt hoặc chưa hoàn tất", "tried": "Máy đã ghi lại lần xử lý; chưa tự chi thêm",
                        "choice": "Giữ bản hiện tại hoặc mở Nâng cao để xem và sửa", "job_id": job["id"]})
    if not state["scenes"]:
        out.append({"what": "Đang giữ — chưa có kịch bản theo cảnh", "tried": "Chưa tạo ảnh/video",
                    "choice": "Gửi ý tưởng hoặc nhập kịch bản để bắt đầu"})
    return out
