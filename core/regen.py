"""Regeneration of a finished video: keep the old clip in the trash, queue a fresh job (a person's — or, with auto=True, the run's)."""
import os
from typing import Optional

from . import trash
from .pipeline import Pipeline


def regenerate_video(pipeline: Pipeline, data_dir: str, job_id: int, note: Optional[str] = None, fix: Optional[str] = None,
                     auto: bool = False) -> Optional[int]:
    """Move the clip of a succeeded video job to the trash, retire that job and queue a NEW video job for the scene.
    A person's take (default): never capped, the automatic count starts again at 0 (S14.16). `auto=True` (the run redoes it by itself,
    e.g. the plate fallback): counted on pipeline.AUTO_REGEN_LIMIT — at the limit nothing is touched, the job is escalated (📥) and None
    is returned.
    `note` (Vietnamese, for people) goes to the history; `fix` (English sentence for the video model, e.g. the clip-set QC's `fix`)
    becomes the new job's retry_reason, so the new take is NOT the same paid input again (luật 6). A redo whose input already
    changed (new picture / motion prompt / plate mode) passes no fix. Returns the new job id."""
    job = pipeline.job(job_id)
    if job["type"] != "video_gen":
        raise ValueError("only video jobs can be regenerated")
    if auto and pipeline._retries_exhausted(job):
        pipeline._escalate(job, limit=True)
        return None
    why = pipeline._same_input_regen(job, (fix or "").strip() or None)
    if why:                                            # N1 5a.4.4 (flag two_tier_quality): a redo must change its input
        if auto:
            pipeline._escalate(job)
            return None
        raise ValueError(f"không gen lại: {why}")
    actor = "ai_agent" if auto else "user"
    row = pipeline.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    path = job["result_path"] or os.path.join(data_dir, str(job["project_id"]), "videos", f"{row['idx']:02d}.mp4")
    from . import access
    access.need_edit_job(pipeline, job_id, "gen lại video")
    if job["state"] != "approved":
        pipeline._require_reviewable(job_id)           # checked BEFORE the paid rewrite (reject below would raise the same)
    # S14.17: the Director rewrites the motion prompt while the clip is still alive (review #1: no moment without a live take) and
    # while its file is still there (the faulty frames)
    plan = pipeline._rewrite_before_retry(job, (fix or "").strip() or None, note=note, by="qc" if auto else "user")
    if job["state"] == "approved":                     # an approved clip (video QC passed) can still be redone
        from .states import JobState
        pipeline._log_review(job_id, actor, "reject", note or "gen lại video")
        pipeline.transition(job_id, JobState.REJECTED, actor=actor, note=note or "gen lại video")
    else:
        pipeline.reject(job_id, actor, note or "gen lại video", respawn=False)  # raises unless the job is reviewable
    reason = plan.apply()
    trash.move_to_trash(path, data_dir, job["project_id"], "videos", "gen lại video", job_id, row["idx"])
    return pipeline._insert_job(job["project_id"], job["scene_id"], "video_gen", parent_job_id=job_id,
                                retry_count=job["retry_count"] + 1 if auto else 0, retry_reason=reason,
                                origin="auto" if auto else None)
