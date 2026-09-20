"""Job runners: submit queued jobs, heartbeat-poll running ones, download results.

`VideoRunner` (Step 4) and `ImageRunner` (Step 2) share one loop; they differ only in what they
submit and where results are stored. Risk-control rejections are logged and never retried
automatically (that would only burn credits); transient errors are retried through the state
machine up to the project's max_retry_count.
"""
import json
import os
import time
from typing import Callable, Dict, Optional, Tuple

from . import subjects as subject_links
from . import trash
from .cost import record_usage
from .pipeline import Pipeline
from .preflight import record_failure
from .providers import RISK_CONTROL, ProviderError


class _Runner:
    job_type = ""

    def __init__(self, pipeline: Pipeline, provider, data_dir: str, max_concurrent: int = 5):
        self.p = pipeline
        self.provider = provider
        self.data_dir = data_dir
        self.max_concurrent = max_concurrent

    # ---- hooks -----------------------------------------------------------
    def _submit_args(self, job) -> Optional[Tuple]:
        raise NotImplementedError

    def _dest_path(self, job) -> str:
        raise NotImplementedError

    # ---- shared ----------------------------------------------------------
    def _dir(self, project_id: int, kind: str) -> str:
        directory = os.path.join(self.data_dir, str(project_id), kind)
        os.makedirs(directory, exist_ok=True)
        return directory

    def _jobs(self, project_id: int, state: str):
        return self.p.conn.execute("SELECT * FROM jobs WHERE project_id=? AND type=? AND state=? ORDER BY id",
                                   (project_id, self.job_type, state)).fetchall()

    def submit_pending(self, project_id: int) -> int:
        if self.p.project(project_id)["paused"]:
            return 0
        slots = self.max_concurrent - len(self._jobs(project_id, "running"))
        submitted = 0
        for job in self._jobs(project_id, "queued"):
            if slots <= 0:
                break
            args = self._submit_args(job)
            if args is None:
                self.p.start(job["id"])
                self.p.fail(job["id"], "missing inputs (approved image / motion prompt / image prompt)")
                continue
            try:
                task_id = self.provider.submit(*args)
            except ProviderError as e:
                if e.transient:
                    break  # network/server hiccup: leave the job queued, try again next heartbeat
                self.p.start(job["id"])
                self._record_provider_failure(job, e.code, str(e))
                self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
                continue
            self.p.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (task_id, job["id"]))
            self.p.conn.commit()
            self._record_usage(job, args)
            self.p.start(job["id"])
            slots -= 1
            submitted += 1
        return submitted

    def poll_once(self, project_id: int) -> Dict[str, int]:
        counts = {"succeeded": 0, "failed": 0, "retried": 0, "running": 0}
        for job in self._jobs(project_id, "running"):
            try:
                status = self.provider.status(job["external_id"])
            except ProviderError as e:
                if e.transient:
                    counts["running"] += 1  # keep polling on network/server errors
                    continue
                self._record_provider_failure(job, e.code, str(e))
                self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
                counts["failed"] += 1
                continue
            if status.state == "running":
                counts["running"] += 1
            elif status.state == "succeeded":
                try:
                    target = self._dest_path(job)
                    trash.move_to_trash(target, self.data_dir, job["project_id"],
                                        "videos" if self.job_type == "video_gen" else "images",
                                        "bị thay bằng bản gen lại", job["id"])
                    dest = self.provider.download(job["external_id"], target)
                except ProviderError as e:
                    if e.transient:
                        counts["running"] += 1
                        continue
                    self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
                    counts["failed"] += 1
                    continue
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

    def _record_usage(self, job, args) -> None:
        """Ledger entry per submission (each one may be billed by the provider)."""

    def _record_provider_failure(self, job, code, message: str) -> None:
        if code == RISK_CONTROL:
            record_failure(self.p.conn, job["id"], self.provider.name, message)

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
            active = self.p.conn.execute(
                "SELECT COUNT(*) c FROM jobs WHERE project_id=? AND type=? AND state IN ('queued','running')",
                (project_id, self.job_type)).fetchone()["c"]
            if active == 0 or self.p.project(project_id)["paused"]:
                return
            sleep(interval)


class VideoRunner(_Runner):
    job_type = "video_gen"

    def _submit_args(self, job):
        conn = self.p.conn
        mp = conn.execute("SELECT motion_prompt, negative_prompt, duration_sec FROM motion_prompts"
                          " WHERE scene_id=? AND state='approved'", (job["scene_id"],)).fetchone()
        img = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'"
                           " ORDER BY id DESC LIMIT 1", (job["scene_id"],)).fetchone()
        if mp is None or img is None:
            return None
        path = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{img['id']}.png")
        proj = self.p.project(job["project_id"])
        args = (path, mp["motion_prompt"], mp["negative_prompt"], mp["duration_sec"], proj["video_model"])
        refs = []
        if proj["use_subjects"] and "seedance" in (proj["video_model"] or ""):
            refs = subject_links.usable_for_scene(self.p, job["scene_id"], subject_links.reference_cap(proj["video_model"]))
        if proj["video_audio"] or refs:  # extra args only when used: older providers keep working
            args += (bool(proj["video_audio"]),) + ((refs,) if refs else ())
        return args

    def _record_usage(self, job, args) -> None:
        info = getattr(self.provider, "usage_info", None)
        if info is not None:
            model, tier, seconds = info(args[4], args[3])
            record_usage(self.p.conn, job["id"], "video", self.provider.name, model, tier, seconds, "second")

    def _dest_path(self, job) -> str:
        idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["idx"]
        return os.path.join(self._dir(job["project_id"], "videos"), f"{idx:02d}.mp4")


class ImageRunner(_Runner):
    job_type = "image_gen"

    def _submit_args(self, job):
        scene = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
        prompt = json.loads(scene["data"] or "{}").get("image_prompt")
        if not prompt:
            return None
        if job["retry_reason"]:
            prompt = f"{prompt}. Fix: {job['retry_reason']}"
        return (prompt,)

    def _record_usage(self, job, args) -> None:
        info = getattr(self.provider, "usage_info", None)
        if info is not None:
            model, tier = info()
            record_usage(self.p.conn, job["id"], "image", self.provider.name, model, tier, 1, "image")

    def _dest_path(self, job) -> str:
        return os.path.join(self._dir(job["project_id"], "images"), f"job_{job['id']}.png")
