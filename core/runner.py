"""Step 4 runner: submit queued video_gen jobs, heartbeat-poll running ones, download results.

Failure handling: risk-control rejections are logged (content_moderation_failures) and never
retried automatically (retrying would only burn credits); transient errors are retried up to
the project's max_retry_count via the state machine.
"""
import os
import time
from typing import Callable, Dict

from .pipeline import Pipeline
from .preflight import record_failure
from .providers import RISK_CONTROL, VideoProvider


class VideoRunner:
    def __init__(self, pipeline: Pipeline, provider: VideoProvider, data_dir: str,
                 max_concurrent: int = 5):
        self.p = pipeline
        self.provider = provider
        self.data_dir = data_dir
        self.max_concurrent = max_concurrent

    def _video_path(self, project_id: int, scene_idx: int) -> str:
        directory = os.path.join(self.data_dir, str(project_id), "videos")
        os.makedirs(directory, exist_ok=True)
        return os.path.join(directory, f"{scene_idx:02d}.mp4")

    def _inputs(self, job):
        conn = self.p.conn
        mp = conn.execute("SELECT motion_prompt, negative_prompt, duration_sec FROM motion_prompts"
                          " WHERE scene_id=? AND state='approved'", (job["scene_id"],)).fetchone()
        img = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'"
                           " ORDER BY id DESC LIMIT 1", (job["scene_id"],)).fetchone()
        if mp is None or img is None:
            return None
        path = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{img['id']}.png")
        return path, mp["motion_prompt"], mp["negative_prompt"], mp["duration_sec"]

    def _running(self, project_id: int):
        return self.p.conn.execute("SELECT * FROM jobs WHERE project_id=? AND type='video_gen'"
                                   " AND state='running' ORDER BY id", (project_id,)).fetchall()

    def submit_pending(self, project_id: int) -> int:
        if self.p.project(project_id)["paused"]:
            return 0
        slots = self.max_concurrent - len(self._running(project_id))
        queued = self.p.conn.execute("SELECT * FROM jobs WHERE project_id=? AND type='video_gen'"
                                     " AND state='queued' ORDER BY id", (project_id,)).fetchall()
        submitted = 0
        for job in queued:
            if slots <= 0:
                break
            inputs = self._inputs(job)
            if inputs is None:
                self.p.start(job["id"])
                self.p.fail(job["id"], "missing approved image or motion prompt")
                continue
            task_id = self.provider.submit(*inputs)
            self.p.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (task_id, job["id"]))
            self.p.conn.commit()
            self.p.start(job["id"])
            slots -= 1
            submitted += 1
        return submitted

    def poll_once(self, project_id: int) -> Dict[str, int]:
        counts = {"succeeded": 0, "failed": 0, "retried": 0, "running": 0}
        for job in self._running(project_id):
            status = self.provider.status(job["external_id"])
            if status.state == "running":
                counts["running"] += 1
            elif status.state == "succeeded":
                idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?",
                                          (job["scene_id"],)).fetchone()["idx"]
                dest = self.provider.download(job["external_id"], self._video_path(project_id, idx))
                self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, job["id"]))
                self.p.conn.commit()
                self.p.succeed(job["id"])
                counts["succeeded"] += 1
            else:
                message = f"{status.error_code}: {status.error_message}"
                if status.error_code == RISK_CONTROL:
                    record_failure(self.p.conn, job["id"], self.provider.name, status.error_message or "")
                self.p.fail(job["id"], message)
                counts["failed"] += 1
                if status.transient and self.p.retry(job["id"], message) is not None:
                    counts["retried"] += 1
        return counts

    def cancel_job(self, job_id: int) -> None:
        job = self.p.job(job_id)
        if job["external_id"] and job["state"] == "running":
            self.provider.cancel(job["external_id"])
        self.p.cancel(job_id)

    def run(self, project_id: int, interval: float = 90, max_iterations: int = 10_000,
            sleep: Callable[[float], None] = time.sleep) -> None:
        """Heartbeat loop: submit, poll, sleep — until nothing is queued or running."""
        for _ in range(max_iterations):
            self.submit_pending(project_id)
            self.poll_once(project_id)
            active = self.p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND type='video_gen'"
                                         " AND state IN ('queued','running')", (project_id,)).fetchone()["c"]
            if active == 0 or self.p.project(project_id)["paused"]:
                return
            sleep(interval)
