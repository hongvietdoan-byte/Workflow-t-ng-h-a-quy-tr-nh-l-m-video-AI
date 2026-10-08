"""Bản đồ shot × khâu (người dùng 07/10, Đợt 3 tab kiểu chat; cờ `chat_first`): chia khâu và đường dẫn rõ, dễ phân biệt, đủ mà không thừa.

Mỗi cảnh/shot một hàng, mỗi khâu (Ảnh · Motion · Video) một ô với MỘT trạng thái: done (xong, còn mới) · stale (⚠ cũ, cần làm lại) ·
review (chờ duyệt) · running (đang gen) · failed (lỗi) · none (chưa làm). Trạng thái "xong/cũ" lấy từ core/lineage.scan (một nguồn,
như thanh bước); "đang gen / lỗi / chờ duyệt" từ job MỚI NHẤT của khâu. Chỉ đọc CSDL, 0 USD."""
from typing import Dict, List, Optional

from . import lineage

STAGES = (("image", "Ảnh"), ("motion", "Motion"), ("video", "Video"))
STATE_LABEL = {"done": "Xong", "stale": "Cũ — làm lại", "review": "Chờ duyệt", "running": "Đang gen", "failed": "Lỗi", "none": "Chưa làm"}
_JOB = {"pending_review": "review", "succeeded": "review", "queued": "running", "running": "running", "failed": "failed",
        "retryable": "failed"}


def _latest(conn, pid: int, kind: str) -> Dict[int, str]:
    rows = conn.execute("SELECT j.scene_id, j.state FROM jobs j WHERE j.project_id=? AND j.type=? AND j.id=(SELECT MAX(k.id) FROM jobs k "
                        "WHERE k.scene_id=j.scene_id AND k.type=?)", (pid, kind, kind)).fetchall()
    return {r["scene_id"]: r["state"] for r in rows}


def build(conn, pid: int) -> List[Dict]:
    """[{idx, image, motion, video}] in scene order."""
    scanned = lineage.scan(conn, pid)
    img_jobs, vid_jobs = _latest(conn, pid, "image_gen"), _latest(conn, pid, "video_gen")
    from .shots import needs_own_image
    out = []
    for sid, r in sorted(scanned.items(), key=lambda kv: kv[1]["idx"]):
        if r["image_stale"]:
            image = "stale"
        elif r["image_job_id"] or not needs_own_image(conn, sid):
            image = "done"
        else:
            image = _JOB.get(img_jobs.get(sid), "none")
        if r["motion_stale"]:
            motion = "stale"
        else:
            motion = {"approved": "done", "pending": "review"}.get(r["motion_state"], "none")
        if r["video_stale"]:
            video = "stale"
        elif r["video_state"] in lineage.USABLE_VIDEO:
            video = "done"
        else:
            video = _JOB.get(vid_jobs.get(sid), "none")
        out.append({"idx": r["idx"], "image": image, "motion": motion, "video": video})
    return out


def summary(rows: List[Dict]) -> Dict:
    """{counts: {stage: (done, total)}, current: the first stage not finished for every shot (None = all done or no shots)}."""
    total = len(rows)
    counts = {k: (sum(1 for r in rows if r[k] == "done"), total) for k, _ in STAGES}
    current: Optional[str] = next((k for k, _ in STAGES if counts[k][0] < total), None) if total else None
    return {"counts": counts, "current": current}


def video_idle_reason(rows: List[Dict]) -> str:
    """Bố cục điểm 6 (người dùng 07/10): why ▶ Gen video has nothing to send — said ON the button instead of a silent '(0 cảnh mới)'."""
    if not rows:
        return "chưa có cảnh — tách kịch bản trước"
    no_motion = sum(1 for r in rows if r["motion"] != "done" and r["video"] in ("none", "stale", "failed"))
    if no_motion:
        return f"{no_motion} cảnh chưa duyệt motion prompt (Storyboard › Motion)"
    running = sum(1 for r in rows if r["video"] == "running")
    if running:
        return f"{running} clip đang gen — chờ xong"
    review = sum(1 for r in rows if r["video"] == "review")
    if review:
        return f"{review} clip chờ duyệt — duyệt ở dưới"
    return "mọi cảnh đã có clip"
