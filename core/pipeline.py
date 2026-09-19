import sqlite3
from datetime import datetime, timezone
from typing import Mapping, Optional

from .states import REVIEWABLE, InvalidTransition, JobState, check_transition


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PipelinePaused(Exception):
    pass


class Pipeline:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ---- projects / scenes / jobs -------------------------------------
    def create_project(self, name: str, operating_mode: str = "human_qc",
                       threshold: float = 0.85, max_retry: int = 3) -> int:
        cur = self.conn.execute(
            "INSERT INTO projects (name, operating_mode, qc_auto_pass_threshold, max_retry_count, created_at)"
            " VALUES (?,?,?,?,?)", (name, operating_mode, threshold, max_retry, _now()))
        self.conn.commit()
        return cur.lastrowid

    def project(self, project_id: int) -> sqlite3.Row:
        return self.conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()

    def set_mode(self, project_id: int, mode: str) -> None:
        self.conn.execute("UPDATE projects SET operating_mode=? WHERE id=?", (mode, project_id))
        self.conn.commit()

    def set_threshold(self, project_id: int, threshold: float) -> None:
        self.conn.execute("UPDATE projects SET qc_auto_pass_threshold=? WHERE id=?", (threshold, project_id))
        self.conn.commit()

    def set_video_model(self, project_id: int, model: Optional[str]) -> None:
        """Model used by the video provider (e.g. 'seedance', 'kling', 'minimax'); None = provider default."""
        self.conn.execute("UPDATE projects SET video_model=? WHERE id=?", (model or None, project_id))
        self.conn.commit()

    def set_paused(self, project_id: int, paused: bool) -> None:
        self.conn.execute("UPDATE projects SET paused=? WHERE id=?", (1 if paused else 0, project_id))
        self.conn.commit()

    def cancel_all_active(self, project_id: int, actor: str = "user") -> int:
        """Emergency stop: cancel every queued/running/retryable job of the project."""
        ids = [r["id"] for r in self.conn.execute(
            "SELECT id FROM jobs WHERE project_id=? AND state IN ('queued','running','retryable')", (project_id,))]
        for job_id in ids:
            self.transition(job_id, JobState.CANCELLED, actor=actor, note="cancel all")
        return len(ids)

    def create_scene(self, project_id: int, idx: int, title: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO scenes (project_id, idx, title) VALUES (?,?,?)", (project_id, idx, title))
        self.conn.commit()
        return cur.lastrowid

    def create_job(self, scene_id: int, job_type: str = "image_gen") -> int:
        project_id = self.conn.execute(
            "SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()["project_id"]
        return self._insert_job(project_id, scene_id, job_type)

    def job(self, job_id: int) -> sqlite3.Row:
        return self.conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()

    def state(self, job_id: int) -> JobState:
        return JobState(self.job(job_id)["state"])

    def _insert_job(self, project_id: int, scene_id: int, job_type: str,
                    parent_job_id: Optional[int] = None, retry_count: int = 0,
                    retry_reason: Optional[str] = None) -> int:
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO jobs (project_id, scene_id, type, state, parent_job_id, retry_count,"
            " retry_reason, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (project_id, scene_id, job_type, JobState.QUEUED.value, parent_job_id, retry_count,
             retry_reason, now, now))
        self._event(cur.lastrowid, None, JobState.QUEUED, "system", retry_reason)
        self.conn.commit()
        return cur.lastrowid

    def _event(self, job_id: int, from_state, to_state: JobState, actor: str, note: Optional[str]) -> None:
        self.conn.execute(
            "INSERT INTO job_events (job_id, from_state, to_state, actor, note, at) VALUES (?,?,?,?,?,?)",
            (job_id, from_state.value if from_state else None, to_state.value, actor, note, _now()))

    def transition(self, job_id: int, new_state: JobState, actor: str = "system",
                   note: Optional[str] = None) -> None:
        current = self.state(job_id)
        check_transition(current, new_state)
        self.conn.execute("UPDATE jobs SET state=?, updated_at=? WHERE id=?",
                          (new_state.value, _now(), job_id))
        self._event(job_id, current, new_state, actor, note)
        self.conn.commit()

    # ---- execution controls (Run / Fail / Retry / Cancel) -------------
    def start(self, job_id: int) -> None:
        if self.project(self.job(job_id)["project_id"])["paused"]:
            raise PipelinePaused("project is paused")
        self.transition(job_id, JobState.RUNNING)

    def succeed(self, job_id: int) -> None:
        self.transition(job_id, JobState.SUCCEEDED)

    def fail(self, job_id: int, note: Optional[str] = None) -> None:
        self.transition(job_id, JobState.FAILED, note=note)

    def cancel(self, job_id: int, actor: str = "user") -> None:
        self.transition(job_id, JobState.CANCELLED, actor=actor)

    def retry(self, job_id: int, reason: Optional[str] = None) -> Optional[int]:
        """failed -> retryable -> new queued job (parent link). Returns None if escalated."""
        if self.state(job_id) != JobState.FAILED:
            raise InvalidTransition(f"job {job_id} is {self.state(job_id).value}, only failed jobs can be retried")
        if self._retries_exhausted(self.job(job_id)):
            self._escalate(self.job(job_id))
            return None
        self.transition(job_id, JobState.RETRYABLE, note=reason)
        return self._spawn_retry(job_id, reason, close_old=JobState.CANCELLED)

    # ---- QC / review ---------------------------------------------------
    def apply_qc(self, job_id: int, scores: Mapping[str, float]) -> str:
        """Record per-criterion scores, then decide per project operating_mode.

        Returns 'approved', 'rejected', 'escalated' or 'pending_review'.
        """
        job = self.job(job_id)
        proj = self.project(job["project_id"])
        threshold = proj["qc_auto_pass_threshold"]
        overall = sum(scores.values()) / len(scores)
        passed = overall >= threshold
        auto = proj["operating_mode"] == "auto"
        for criterion, score in scores.items():
            self.conn.execute(
                "INSERT INTO qc_results (job_id, criterion, score, threshold_at_time, auto_decision)"
                " VALUES (?,?,?,?,?)",
                (job_id, criterion, score, threshold, ("pass" if passed else "fail") if auto else None))
        self.conn.commit()
        if not auto:
            self.transition(job_id, JobState.PENDING_REVIEW, actor="ai_agent",
                            note=f"QC {overall:.2f} (suggestion only)")
            return "pending_review"
        if passed:
            self.approve(job_id, "ai_agent", f"QC {overall:.2f} >= {threshold}")
            return "approved"
        return self.reject(job_id, "ai_agent", f"QC {overall:.2f} < {threshold}")

    def approve(self, job_id: int, reviewer_type: str = "user", note: Optional[str] = None) -> None:
        self._require_reviewable(job_id)
        self._log_review(job_id, reviewer_type, "approve", note)
        self.transition(job_id, JobState.APPROVED, actor=reviewer_type, note=note)

    def reject(self, job_id: int, reviewer_type: str = "user", note: Optional[str] = None) -> str:
        """Reject and spawn a retry job; escalate when max_retry_count is exceeded."""
        self._require_reviewable(job_id)
        self._log_review(job_id, reviewer_type, "reject", note)
        self.transition(job_id, JobState.REJECTED, actor=reviewer_type, note=note)
        new_id = self._spawn_retry(job_id, note)
        return "rejected" if new_id else "escalated"

    def _require_reviewable(self, job_id: int) -> None:
        if self.state(job_id) not in REVIEWABLE:
            raise InvalidTransition(f"job {job_id} is {self.state(job_id).value}, not reviewable")

    def _log_review(self, job_id: int, reviewer_type: str, decision: str, note: Optional[str]) -> None:
        self.conn.execute(
            "INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,?)",
            (job_id, reviewer_type, decision, note, _now()))
        self.conn.commit()

    def _spawn_retry(self, job_id: int, reason: Optional[str],
                     close_old: Optional[JobState] = None) -> Optional[int]:
        job = self.job(job_id)
        if self._retries_exhausted(job):
            self._escalate(job)
            return None
        next_count = job["retry_count"] + 1
        if close_old is not None:
            self.transition(job_id, close_old, note="superseded by retry")
        return self._insert_job(job["project_id"], job["scene_id"], job["type"],
                                parent_job_id=job_id, retry_count=next_count, retry_reason=reason)

    def _retries_exhausted(self, job: sqlite3.Row) -> bool:
        max_retry = self.project(job["project_id"])["max_retry_count"]
        return job["retry_count"] + 1 > max_retry

    def _escalate(self, job: sqlite3.Row) -> None:
        self.conn.execute("UPDATE jobs SET escalated=1 WHERE id=?", (job["id"],))
        self.conn.execute("UPDATE scenes SET state='needs_attention' WHERE id=?", (job["scene_id"],))
        self.conn.commit()

    # ---- queries -------------------------------------------------------
    def history(self, job_id: int):
        return self.conn.execute(
            "SELECT from_state, to_state, actor, note FROM job_events WHERE job_id=? ORDER BY id",
            (job_id,)).fetchall()
