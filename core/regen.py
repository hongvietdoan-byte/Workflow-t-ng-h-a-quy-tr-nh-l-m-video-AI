"""User-driven regeneration of a finished video: keep the old clip in the trash, queue a fresh job."""
import os
from typing import Optional

from . import trash
from .pipeline import Pipeline


def regenerate_video(pipeline: Pipeline, data_dir: str, job_id: int, note: Optional[str] = None) -> int:
    """Move the clip of a succeeded video job to the trash, retire that job and queue a NEW video job for the scene.
    A fresh job (not an automatic retry) so a user who wants another take is not stopped by max_retry_count.
    Returns the new job id."""
    job = pipeline.job(job_id)
    if job["type"] != "video_gen":
        raise ValueError("only video jobs can be regenerated")
    row = pipeline.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    path = job["result_path"] or os.path.join(data_dir, str(job["project_id"]), "videos", f"{row['idx']:02d}.mp4")
    if job["state"] == "approved":                     # an approved clip (video QC passed) can still be redone by the person
        from .states import JobState
        pipeline._log_review(job_id, "user", "reject", note or "gen lại video")
        pipeline.transition(job_id, JobState.REJECTED, actor="user", note=note or "gen lại video")
    else:
        pipeline.reject(job_id, "user", note or "gen lại video", respawn=False)  # raises unless the job is reviewable
    trash.move_to_trash(path, data_dir, job["project_id"], "videos", "gen lại video", job_id, row["idx"])
    return pipeline.create_job(job["scene_id"], "video_gen")
