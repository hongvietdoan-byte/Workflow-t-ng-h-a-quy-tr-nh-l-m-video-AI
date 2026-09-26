"""User-driven regeneration of a finished video: keep the old clip in the trash, queue a fresh job."""
import os
from typing import Optional

from . import trash
from .pipeline import Pipeline


def regenerate_video(pipeline: Pipeline, data_dir: str, job_id: int, note: Optional[str] = None, fix: Optional[str] = None) -> int:
    """Move the clip of a succeeded video job to the trash, retire that job and queue a NEW video job for the scene.
    A fresh job (not an automatic retry) so a user who wants another take is not stopped by max_retry_count.
    `note` (Vietnamese, for people) goes to the history; `fix` (English sentence for the video model, e.g. the clip-set QC's `fix`)
    becomes the new job's retry_reason, so the new take is NOT the same paid input again (luật 6). A redo whose input already
    changed (new picture / motion prompt / plate mode) passes no fix. Returns the new job id."""
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
    return pipeline._insert_job(job["project_id"], job["scene_id"], "video_gen", parent_job_id=job_id, retry_count=0,
                                retry_reason=(fix or "").strip() or None)
