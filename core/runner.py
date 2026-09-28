"""Job runners: submit queued jobs, heartbeat-poll running ones, download results.

`VideoRunner` (Step 4) and `ImageRunner` (Step 2) share one loop; they differ only in what they
submit and where results are stored. Risk-control rejections are logged and never retried
automatically (that would only burn credits); transient errors are retried through the state
machine up to the project's max_retry_count.
"""
import json
import math
import os
import re
import threading
import time
from typing import Callable, Dict, Optional, Tuple

from . import assets, diag, layout
from . import subjects as subject_links
from . import trash
from .cost import record_usage
from .pipeline import Pipeline
from .preflight import record_failure
from .providers import RISK_CONTROL, ProviderError
from . import budget, throttle as throttle_store
from .throttle import THROTTLE

NOT_CREATED = "not_created"            # core.adapters.clipai.NOT_CREATED: task id returned, task never created
NOT_CREATED_RESENDS = 3
RESEND_NOTE = "gửi lại: nhà cung cấp không tạo task"


def model_fix(retry_reason: Optional[str]) -> Optional[str]:
    """The fix sentence a retry sends to the picture/video model, or None. A resend of the same input after a provider failure
    (RESEND_NOTE / pipeline.PLAIN_RESEND) carries a note for people only — it is never put into the model's prompt."""
    from .pipeline import PLAIN_RESEND
    text = (retry_reason or "").strip()
    if not text or text.startswith(RESEND_NOTE) or text.startswith(PLAIN_RESEND):
        return None
    return text

_turns: Dict[Tuple[int, str], threading.RLock] = {}
_turns_lock = threading.Lock()


class RedrawWithFix(Exception):
    """A downloaded result that must not be used (e.g. a location-pack picture drawn without the green backdrop): the job fails and a
    new try goes with `fix` (English, for the model)."""

    def __init__(self, message: str, fix: str):
        super().__init__(message)
        self.fix = fix


GREEN_FIX = ("Draw ONLY the characters on a perfectly flat, uniform pure chroma-key green (#00FF00) backdrop filling the whole frame "
             "behind them — no building, no tower, no sky, no floor, no ground, no scenery at all.")


def _turn(project_id: int, job_type: str) -> threading.RLock:
    """M3: one submitter/poller per project and job type in this process. The dashboard tab (every few seconds) and the autopilot
    thread used to poll the same job at once - the clip was downloaded twice and a follower job could be made twice. The thread
    that finds it busy skips this round (the other one does the work); re-entrant for nested calls in one thread."""
    with _turns_lock:
        lock = _turns.get((project_id, job_type))
        if lock is None:
            lock = _turns[(project_id, job_type)] = threading.RLock()
        return lock


class TaskMemory:
    """W12 counters of a provider task kept on its job rows (every job sharing the external id: a multi-shot group), so they survive
    the dashboard building a new provider on every poll and a restart. sent_at = when the job was sent (epoch seconds) or None."""

    def __init__(self, conn):
        self.conn = conn

    def state(self, external_id: str):
        row = self.conn.execute("SELECT id, task_seen, task_unseen FROM jobs WHERE external_id=? ORDER BY id LIMIT 1", (external_id,)).fetchone()
        if row is None:
            return False, 0, None
        ev = self.conn.execute("SELECT at FROM job_events WHERE job_id=? AND to_state='running' ORDER BY id LIMIT 1", (row["id"],)).fetchone()
        sent = None
        if ev is not None:
            from datetime import datetime
            try:
                sent = datetime.fromisoformat(ev["at"]).timestamp()
            except ValueError:
                sent = None
        return bool(row["task_seen"]), int(row["task_unseen"] or 0), sent

    def unseen(self, external_id: str) -> int:
        self.conn.execute("UPDATE jobs SET task_unseen=task_unseen+1 WHERE external_id=?", (external_id,))
        self.conn.commit()
        row = self.conn.execute("SELECT MAX(task_unseen) FROM jobs WHERE external_id=?", (external_id,)).fetchone()
        return int(row[0] or 0)

    def seen(self, external_id: str) -> None:
        self.conn.execute("UPDATE jobs SET task_seen=1, task_unseen=0 WHERE external_id=? AND (task_seen=0 OR task_unseen>0)", (external_id,))
        self.conn.commit()


class _Runner:
    job_type = ""

    def __init__(self, pipeline: Pipeline, provider, data_dir: str, max_concurrent: int = 5):
        self.p = pipeline
        self.provider = provider
        self.data_dir = data_dir
        self.max_concurrent = max_concurrent
        if hasattr(provider, "attach_memory"):
            provider.attach_memory(TaskMemory(pipeline.conn))
        throttle_store.load(pipeline.conn, THROTTLE)        # the limits learned before the last restart

    def _throttle_changed(self) -> None:
        throttle_store.save(self.p.conn, THROTTLE)

    def _diag(self, job, severity: str, code, message: str) -> None:
        diag.record(self.p.conn, "image" if self.job_type == "image_gen" else "video", severity, message, code,
                    job["project_id"], job["scene_id"], job["id"])

    # ---- hooks -----------------------------------------------------------
    def _submit_args(self, job) -> Optional[Tuple]:
        raise NotImplementedError

    def _submit_kwargs(self, job) -> Dict:
        """Extra keyword arguments (frame format, per-scene resolution) — only for providers that declare `supports_aspect`,
        so simpler providers (and test doubles) keep receiving the v1 call."""
        return {}

    def _blocked(self, job) -> Optional[str]:
        """A reason not to send this job now (it would be made from outdated inputs); None = go."""
        return None

    def _wait(self, job) -> bool:
        """True = leave the job queued for now (not an error)."""
        return False

    def _stamp(self, job, args) -> Dict:
        """Columns written on the job when it is sent: fingerprint of its inputs (core.lineage), source image, model."""
        return {}

    def _editing(self, job) -> bool:
        """A video job whose motion prompt exists but is waiting for approval again (just edited)."""
        if self.job_type != "video_gen":
            return False
        row = self.p.conn.execute("SELECT state FROM motion_prompts WHERE scene_id=?", (job["scene_id"],)).fetchone()
        return row is not None and row["state"] != "approved"

    def _dest_path(self, job) -> str:
        raise NotImplementedError

    def _after_download(self, job, path: str) -> str:
        """Hook after a result is downloaded (v3: a shot clip is cut to the shot's length). Returns the final path."""
        return path

    # ---- shared ----------------------------------------------------------
    def _dir(self, project_id: int, kind: str) -> str:
        directory = os.path.join(self.data_dir, str(project_id), kind)
        os.makedirs(directory, exist_ok=True)
        return directory

    def _jobs(self, project_id: int, state: str):
        return self.p.conn.execute("SELECT * FROM jobs WHERE project_id=? AND type=? AND state=? ORDER BY id",
                                   (project_id, self.job_type, state)).fetchall()

    def submit_pending(self, project_id: int) -> int:
        lock = _turn(project_id, self.job_type)
        if not lock.acquire(blocking=False):
            return 0                       # M3: another thread is sending this project's jobs right now
        try:
            return self._submit_pending(project_id)
        finally:
            lock.release()

    def _submit_pending(self, project_id: int) -> int:
        if self.p.project(project_id)["paused"]:
            return 0
        slots = self.max_concurrent - len(self._jobs(project_id, "running"))
        submitted = 0
        for job in self._jobs(project_id, "queued"):
            if slots <= 0:
                break
            if self._wait(job):
                continue            # v3: this job is sent later (after the previous shot's picture / with its multi-shot group)
            blocked = self._blocked(job)
            if blocked:
                self._diag(job, "warn", "stale_input", f"không gửi: {blocked}")
                self.p.start(job["id"])
                self.p.fail(job["id"], f"stale_input: {blocked}")
                continue
            args = self._submit_args(job)
            if args is None and self._editing(job):
                continue            # M5: the person is editing this shot's motion prompt — wait for the approval, do not burn a try
            if args is None:
                self._diag(job, "error", "missing_input", "thiếu đầu vào (ảnh đã duyệt / motion prompt / prompt ảnh)")
                self.p.start(job["id"])
                self.p.fail(job["id"], "missing inputs (approved image / motion prompt / image prompt)")
                continue
            running_all = self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type=? AND state='running'",
                                              (self.job_type,)).fetchone()[0]
            if not THROTTLE.allow(self.job_type, running_all, capped="mock" not in str(getattr(self.provider, "name", ""))):       # already includes the jobs this pass has started (they are 'running' now)
                break  # learned limit for all projects together: wait for a slot
            kwargs = self._submit_kwargs(job) if getattr(self.provider, "supports_aspect", False) else {}
            with budget.SPEND_LOCK:            # limit check + ledger entry as one step: two projects must not both pass the cap
                over = self._over_budget(job, args, kwargs)
                if over:
                    self._diag(job, "warn", "budget", over)
                    break                        # v3 test spending limit: leave everything queued, say why
                try:
                    task_id = self.provider.submit(*args, **kwargs)
                except ProviderError as e:
                    if e.code == "rate_limited" and THROTTLE.on_rate_limited(self.job_type):   # halve the learned limit
                        self._throttle_changed()
                    if e.transient:
                        self._diag(job, "warn", e.code, f"gửi job bị từ chối/tạm lỗi, sẽ thử lại: {e}")
                        break  # network/server hiccup: leave the job queued, try again next heartbeat
                    self._diag(job, "warn" if e.code == RISK_CONTROL else "error", e.code, f"gửi job thất bại: {e}")
                    self.p.start(job["id"])
                    switched = self._record_provider_failure(job, e.code, str(e))
                    self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
                    if switched:
                        self._retry_switched(job)
                    continue
                self.p.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (task_id, job["id"]))
                for col, value in self._stamp(job, args).items():
                    self.p.conn.execute(f"UPDATE jobs SET {col}=? WHERE id=?", (value, job["id"]))
                self.p.conn.commit()
                self._record_usage(job, args, kwargs)
            self.p.start(job["id"])
            slots -= 1
            submitted += 1
        return submitted

    def poll_once(self, project_id: int) -> Dict[str, int]:
        lock = _turn(project_id, self.job_type)
        if not lock.acquire(blocking=False):
            n = self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type=? AND state='running'",
                                    (project_id, self.job_type)).fetchone()[0]
            return {"succeeded": 0, "failed": 0, "retried": 0, "running": n}    # M3: another thread is polling it right now
        try:
            return self._poll_once(project_id)
        finally:
            lock.release()

    def _poll_once(self, project_id: int) -> Dict[str, int]:
        counts = {"succeeded": 0, "failed": 0, "retried": 0, "running": 0}
        for job in self._jobs(project_id, "running"):
            try:
                status = self.provider.status(job["external_id"])
            except ProviderError as e:
                if e.transient:
                    self._diag(job, "warn", e.code, f"hỏi trạng thái job gặp lỗi tạm: {e}")
                    counts["running"] += 1  # keep polling on network/server errors
                    continue
                self._diag(job, "error", e.code, f"hỏi trạng thái job thất bại: {e}")
                self._record_provider_failure(job, e.code, str(e))
                self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
                counts["failed"] += 1
                continue
            except Exception as e:  # noqa: BLE001 - an unexpected answer must not take the whole page down
                self._diag(job, "warn", "status_error", f"hỏi trạng thái job gặp lỗi không lường trước ({type(e).__name__}: {e}); "
                                                        "job giữ nguyên, sẽ hỏi lại")
                counts["running"] += 1
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
                    self._diag(job, "warn" if e.transient else "error", e.code, f"tải kết quả lỗi: {e}")
                    if e.transient:
                        counts["running"] += 1
                        continue
                    self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
                    counts["failed"] += 1
                    continue
                except Exception as e:  # noqa: BLE001 - e.g. disk full: keep the job, report it, keep the page alive
                    self._diag(job, "warn", "download_error", f"tải kết quả gặp lỗi không lường trước ({type(e).__name__}: {e}); sẽ thử lại")
                    counts["running"] += 1
                    continue
                try:
                    dest = self._after_download(job, dest)
                except RedrawWithFix as e:            # the result is unusable for a stated reason: a new try WITH the fix (luật 6)
                    self._diag(job, "error", "redraw", str(e))
                    self.p.fail(job["id"], f"redraw: {e}")
                    counts["failed"] += 1
                    if self.p.retry(job["id"], str(e), fix=e.fix) is not None:
                        counts["retried"] += 1
                    continue
                self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, job["id"]))
                self.p.conn.commit()
                self.p.succeed(job["id"])
                if THROTTLE.on_success(self.job_type):
                    self._throttle_changed()
                counts["succeeded"] += 1
            elif status.error_code in (NOT_CREATED, "not_found") and self._relink(job):
                counts["running"] += 1                  # W12b: the provider made it under a new id — follow that one
            elif status.error_code == NOT_CREATED:
                self._not_created(job, status.error_message or "")
                counts["failed"] += 1
            elif status.error_code == "not_found":         # maybe still running at the provider: never resend blindly (paid twice)
                self._diag(job, "error", "not_found", status.error_message or "không thấy task")
                self.p.fail(job["id"], f"not_found: {status.error_message}")
                self.p._escalate(self.p.job(job["id"]))
                counts["failed"] += 1
            else:
                message = f"{status.error_code}: {status.error_message}"
                self._diag(job, "warn" if status.error_code == RISK_CONTROL else "error", status.error_code,
                           f"nhà cung cấp báo job thất bại: {status.error_message}")
                if status.error_code == RISK_CONTROL:
                    record_failure(self.p.conn, job["id"], self.provider.name, status.error_message or "")
                switched = self._on_refused(job, status.error_code, status.error_message or "")
                self.p.fail(job["id"], message)
                counts["failed"] += 1
                if status.transient and self.p.retry(job["id"], message) is not None:
                    counts["retried"] += 1
                elif switched and self._retry_switched(job):
                    counts["retried"] += 1
        return counts

    def _relink(self, job) -> bool:
        """W12b: the provider created the task under another id (queue id → real id). Video only; False = not found that way."""
        return False

    def relink_failed(self, job_id: int) -> Optional[int]:
        """A job already written off as not found / not created whose task the provider did make under a new id: the same attempt is
        re-opened on that task (no new submission, nothing billed twice — the first submission's cost stays in the ledger) and the
        next poll downloads it. Returns the new job id, or None when no such task is found."""
        job = self.p.job(job_id)
        new_ext = self._find_real(job)
        if new_ext is None:
            return None
        new_id = self.p.resend(job_id, f"{RESEND_NOTE} (nối lại task thật {new_ext})")
        self.p.conn.execute("UPDATE jobs SET external_id=?, task_seen=0, task_unseen=0, input_hash=?, source_job_id=?, model=? WHERE id=?",
                            (new_ext, job["input_hash"], job["source_job_id"], job["model"], new_id))
        self.p.conn.execute("UPDATE jobs SET escalated=0 WHERE id IN (?, ?)", (job_id, new_id))
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=? AND state='needs_attention'", (job["scene_id"],))
        self.p.conn.commit()
        self.p.start(new_id)
        self._diag(job, "info", "relinked", f"task thật của job này mang mã khác ({new_ext}) — nối lại vào job {new_id}, không gửi lại")
        return new_id

    def _find_real(self, job) -> Optional[str]:
        return None

    def _not_created(self, job, message: str) -> None:
        """The provider answered with a task id but never created the task (nothing generated, nothing billed): the submission
        leaves the ledger, the provider is treated as overloaded (fewer jobs at once), and the same attempt is sent again at once —
        without using up a retry — at most NOT_CREATED_RESENDS times in a row; then the scene waits for a person."""
        from .cost import cancel_usage
        cancel_usage(self.p.conn, job["id"])
        THROTTLE.on_rate_limited(self.job_type)
        self._throttle_changed()
        self.p.fail(job["id"], f"{NOT_CREATED}: {message}")
        chain, parent = 0, job
        while parent is not None and (parent["retry_reason"] or "").startswith(RESEND_NOTE):
            chain += 1
            parent = self.p.job(parent["parent_job_id"]) if parent["parent_job_id"] else None
        if chain >= NOT_CREATED_RESENDS:
            self._diag(job, "error", NOT_CREATED, f"nhà cung cấp {chain + 1} lần liền không tạo task (đã bỏ khỏi sổ chi) — dừng shot này, "
                                                  "kiểm tra ClipAI rồi bấm gen lại")
            self.p._escalate(self.p.job(job["id"]))
            return
        new_id = self.p.resend(job["id"], f"{RESEND_NOTE} ({chain + 1}/{NOT_CREATED_RESENDS})")
        self._diag(job, "warn", NOT_CREATED, f"nhà cung cấp không tạo task (đã bỏ khỏi sổ chi) → gửi lại ngay, job {new_id}")

    def _record_usage(self, job, args, kwargs=None) -> None:
        """Ledger entry per submission (each one may be billed by the provider)."""

    def _over_budget(self, job, args, kwargs) -> Optional[str]:
        """A reason not to send (the test spending limit, core.budget), else None."""
        return None

    def _record_provider_failure(self, job, code, message: str) -> bool:
        if code == RISK_CONTROL:
            record_failure(self.p.conn, job["id"], self.provider.name, message)
        return bool(self._on_refused(job, code, message))

    def _on_refused(self, job, code, message: str) -> bool:
        """Hook: react to a job the provider refused (VideoRunner: Seedance "real person" -> Kling). True = the input was changed so
        that a new try can pass."""
        return False

    def _retry_switched(self, job) -> bool:
        """M14: the refusal already changed the input (the shot now goes to another model), but a risk-control refusal is not a
        transient error, so nobody sent it again and the shot sat there failed. One new try is queued at once — it uses up a try
        like any regeneration (max_retry_count still applies) and is not the same input as the one refused."""
        new_id = self.p.retry(job["id"], "nhà cung cấp từ chối → đổi model rồi gửi lại")
        if new_id is None:
            return False
        self._diag(job, "info", "switched_retry", f"đã đổi model sau khi bị từ chối → gửi lại (job {new_id})")
        return True

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

    def _choice(self, job) -> Dict:
        from . import model_router
        return model_router.scene_choice(self.p.conn, job["scene_id"])

    def _blocked(self, job) -> Optional[str]:
        from . import lineage
        row = lineage.scan(self.p.conn, job["project_id"]).get(job["scene_id"]) or {}
        if row.get("motion_stale"):
            return f"motion prompt đang cũ ({row['motion_stale']}) — viết lại / duyệt lại ở Bước 3"
        if self._refs(job):
            return self._ref_lint(job)
        return None

    def _ref_lint(self, job) -> Optional[str]:
        """Review 2026-09-27: what can be seen wrong in a reference-only request before paying — too long, Vietnamese left, pictures
        not matching the Image↔Shot table, 'no sound' with a voice. Shots under 1 s are said (not blocked)."""
        from . import seedance_refs
        args = self._submit_args(job)
        if not args:
            return None                                   # the base check says what is missing
        group = self._sends_group(job) or []
        rows = self._ref_rows(job, group)
        from . import shots as _sh
        frames = [_sh.approved_image_path(self.p.conn, self.data_dir, job["project_id"], r["id"]) for r in rows]
        ids = seedance_refs.identity_pictures(self.p.conn, job["project_id"], rows, seedance_refs.MAX_PICTURES - len(rows))
        secs = [self._cut_seconds(r) for r in group] if group else [float(args[3])]
        audio = not group and bool(self._lip_sync_audio_planned(job))
        problems = seedance_refs.lint_group(args[1], len(rows), len([f for f in frames if f]) + len(ids), len(rows) + len(ids), secs, audio)
        busy = seedance_refs.busy_shots(rows)
        if busy:
            self._diag(job, "warn", "busy_shot", "shot dồn ≥ 3 hành động (tài liệu Seedance 2.5: tả khái quát, chi tiết 1–2 điểm nhấn): "
                       + ", ".join(f"shot {i}" for i in busy))
        short = seedance_refs.short_shots(secs)
        if short:
            self._diag(job, "warn", "short_shot", "shot dưới 1 s trong clip nhóm (model dễ bỏ qua): " + ", ".join(f"shot {i}" for i in short))
        return "; ".join(problems) or None

    def _lip_sync_audio_planned(self, job) -> bool:
        from . import lipsync
        if not lipsync.enabled():
            return False
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
        return lipsync.method_for(data) == "generate"

    def _submit_kwargs(self, job) -> Dict:
        from . import formats, shots
        proj = self.p.project(job["project_id"])
        out = {}
        aspect = formats.project_aspect(proj)
        if aspect:
            out["aspect_ratio"] = formats.spec(aspect)["clip"]
        choice = self._choice(job)
        if choice.get("resolution"):
            out["resolution"] = choice["resolution"]
        if "test_quality" in proj.keys() and proj["test_quality"]:    # v3 cheap test mode: 720p, Kling std
            out.pop("resolution", None)
            out["kling_mode"] = "std"
        mode = shots.mode(proj)
        group = self._sends_group(job)
        if self._refs(job):                  # Seedance reference only (P2m): every picture marked, no start / last frame
            out["reference_only"] = self._reference_pictures(job, group or [])
            if not group:
                audio = self._lip_sync_audio(job)
                if audio:
                    out["reference_audio"] = [audio]
            else:
                self._no_lip_sync_note(job, "seedance", group)
            return out
        if group and mode != "multishot":
            pass                         # H5 camera set-up: one continuous prompt (in the motion argument), no multi_prompt
        elif group:
            out["multi_prompt"] = [{"prompt": self._motion(r["id"])["motion_prompt"], "duration": shots.billed_shot_seconds(r["data"])}
                                   for r in group]
            from .adapters.clipai import KLING_SHOT_PROMPT_LIMIT
            long = [f"S{r['idx']:02d} ({len(m['prompt'])} ký tự)" for r, m in zip(group, out["multi_prompt"])
                    if len(m["prompt"]) > KLING_SHOT_PROMPT_LIMIT]
            if long:                     # W13: the cut is visible (the end of the prompt — often the ending action — is lost)
                self._diag(job, "warn", "prompt_cut", f"prompt shot dài hơn {KLING_SHOT_PROMPT_LIMIT} ký tự, bị cắt khi gửi Kling: "
                           + ", ".join(long))
        if "seedance" in (choice.get("model") or "") and not group:
            audio = self._lip_sync_audio(job)
            if audio:
                out["reference_audio"] = [audio]              # V4 GĐ3: the clip speaks our voice line (lip sync at generation)
        else:
            self._no_lip_sync_note(job, choice.get("model"), group)
        if mode == "per_shot" and not group:
            end = shots.last_frame_for(self.p.conn, self.data_dir, job["scene_id"])
            from . import end_frames
            if end is None and end_frames.enabled():
                end = end_frames.usable_path(self.p.conn, job["scene_id"])      # K1: the drawn end state
            if end and ("seedance" in (choice.get("model") or "") or end_frames.enabled()):
                out["last_frame"] = end                   # K2: Seedance last_frame; Kling Omni end_frame (only with K1 on)
        return out

    def _no_lip_sync_note(self, job, model, group) -> None:
        """Luật 1: a shot planned to be made WITH its voice (lip sync "generate") that goes out on another model / inside a group clip
        gets no lip sync — said, not skipped silently."""
        from . import lipsync
        if not lipsync.enabled():
            return
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
        if lipsync.method_for(data) == "generate":
            self._diag(job, "warn", "lipsync_not_applied", f"shot cần khớp môi (tạo kèm giọng) nhưng gửi bằng {model or '?'}"
                       + (" trong clip chung của nhóm" if group else "") + " — clip giữ miệng của model, không khớp giọng")

    def _refs(self, job) -> bool:
        from . import seedance_refs
        return seedance_refs.uses_refs(self.p.conn, job["scene_id"])

    def _ref_rows(self, job, group) -> list:
        return group or [{"id": job["scene_id"], "data": json.loads(self.p.conn.execute(
            "SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")}]

    def _reference_pictures(self, job, group) -> list:
        """The marked pictures of a reference-only send: each shot's approved storyboard picture in film order, then one identity
        picture per character (at most 9 in all)."""
        from . import seedance_refs, shots
        conn = self.p.conn
        rows = self._ref_rows(job, group)
        frames = [shots.approved_image_path(conn, self.data_dir, job["project_id"], r["id"]) for r in rows]
        frames = [f for f in frames if f]
        ids = seedance_refs.identity_pictures(conn, job["project_id"], rows, seedance_refs.MAX_PICTURES - len(frames))
        out_dir = os.path.join(self.data_dir, str(job["project_id"]), "refs_marked")
        return [seedance_refs.mark(p, out_dir) for p in frames + [path for _, path in ids]]

    def _lip_sync_audio(self, job) -> Optional[str]:
        """The shot's voice line file for a "generate" lip-sync shot (feature lip_sync), else None. Missing voice: said, not guessed."""
        from . import ffmpeg_studio, lipsync
        if not lipsync.enabled():
            return None
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
        if lipsync.method_for(data) != "generate":
            return None
        mp = self._motion(job["scene_id"])
        length = float((mp["duration_sec"] if mp is not None and mp["duration_sec"] else None) or data.get("duration_s") or 4)
        try:
            seg = lipsync.shot_audio(self.data_dir, job["project_id"], job["scene_id"], max(length, 4.0), ffmpeg_studio.find_ffmpeg())
        except Exception as e:  # noqa: BLE001
            self._diag(job, "warn", "lipsync_audio", f"không cắt được giọng cho khớp môi ({e}) — clip gửi không kèm giọng")
            return None
        if seg is None:
            self._diag(job, "warn", "lipsync_audio", "shot khớp môi nhưng câu thoại chưa có giọng — tạo giọng (Bước 3) trước")
            return None
        lipsync.mark(self.data_dir, job["project_id"], job["scene_id"], state="generate_sent", job_id=job["id"], offsets=seg["offsets"],
                     method="generate")
        return seg["path"]

    def _find_real(self, job) -> Optional[str]:
        """W12b: the provider's real task for this job, recognised by the prompt that was sent (multi-shot groups send no single
        prompt — left to the old rule)."""
        finder = getattr(self.provider, "find_by_prompt", None)
        if finder is None or not job["external_id"] or (self._sends_group(job) and not self._refs(job)):
            return None
        args = self._submit_args(job)
        if not args:
            return None
        _, _, sent_at = TaskMemory(self.p.conn).state(job["external_id"])
        taken = {r[0] for r in self.p.conn.execute("SELECT external_id FROM jobs WHERE external_id IS NOT NULL")}
        try:
            return finder(job["external_id"], args[1], sent_at, taken)
        except ProviderError:
            return None

    def _relink(self, job) -> bool:
        new_ext = self._find_real(job)
        if new_ext is None:
            return False
        self.p.conn.execute("UPDATE jobs SET external_id=?, task_seen=0, task_unseen=0 WHERE id=?", (new_ext, job["id"]))
        self.p.conn.commit()
        self._diag(job, "info", "relinked", f"ClipAI tạo task thật với mã khác ({new_ext}) — theo dõi mã đó, không gửi lại")
        return True

    def _motion(self, scene_id: int):
        return self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()

    def _has_clip(self, scene_id: int) -> bool:
        return bool(self.p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN ('succeeded','approved')",
                                        (scene_id,)).fetchone())

    def _sends_group(self, job):
        """The multi-shot group this job generates in one go (Kling multi-shot, first shot of a group whose other shots have no
        clip yet), else None — a shot remade later is sent on its own. Seedance reference groups: several CONSECUTIVE shots of the
        group all waiting for a new clip are remade together (_redo_run) — #8 2026-09-28: 19 shots remade for their voices went
        out one by one (≥ 4 s billed each, ~0.48 USD) and two lost the characters' identity."""
        from . import shots
        group = shots.group_of(self.p.conn, job["scene_id"]) or []     # Kling multi-shot group, or an H5 camera set-up
        if len(group) < 2:
            return None
        if group[0]["id"] == job["scene_id"] and not any(self._has_clip(r["id"]) for r in group[1:]):
            return group
        run = self._redo_run(job, group)
        return run if run and run[0]["id"] == job["scene_id"] else None

    def _pending_clip(self, scene_id: int) -> bool:
        """The shot waits for a new clip: its newest video job has not been sent yet."""
        row = self.p.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id DESC LIMIT 1",
                                  (scene_id,)).fetchone()
        return row is not None and row["state"] in ("queued", "retryable")

    def _covered(self, scene_id: int, group) -> bool:
        """A group clip already sent (or being made) carries this shot's part."""
        ids = [r["id"] for r in group if r["id"] != scene_id]
        if not ids:
            return False
        rows = self.p.conn.execute("SELECT sent_group FROM jobs WHERE type='video_gen' AND state IN ('queued','running') AND sent_group"
                                   " IS NOT NULL AND scene_id IN (%s)" % ",".join("?" * len(ids)), ids).fetchall()
        for r in rows:
            try:
                if any(int(g.get("id")) == scene_id for g in json.loads(r["sent_group"]) or []):
                    return True
            except (ValueError, TypeError, AttributeError):
                continue
        return False

    def _redo_run(self, job, group=None):
        """Seedance reference group: the run of consecutive shots of the group (containing this job's shot) that all wait for a new
        clip and are not already carried by a group clip in flight — made again as ONE group clip. None when fewer than 2."""
        if not self._refs(job):
            return None
        from . import shots
        group = group or shots.group_of(self.p.conn, job["scene_id"]) or []
        runs, cur = [], []
        for r in group:
            if self._pending_clip(r["id"]) and not self._covered(r["id"], group):
                cur.append(r)
            else:
                if cur:
                    runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        for run in runs:
            if any(r["id"] == job["scene_id"] for r in run):
                return run if len(run) >= 2 else None
        return None

    def _wait(self, job) -> bool:
        """Kling multi-shot: the first shot of a group sends for the whole group once every shot of it has an approved motion
        prompt; the other shots wait for their part of that clip (unless the first shot already has its clip: then a remade
        shot is sent on its own). K1: a shot whose end frame is still being drawn waits for it."""
        from . import end_frames, shots
        if end_frames.enabled():
            row = end_frames.current(self.p.conn, job["scene_id"])
            if row is not None and row["state"] in ("queued", "running"):
                return True
        group = shots.group_of(self.p.conn, job["scene_id"]) or []
        if len(group) < 2:
            return False
        if self._refs(job) and self._covered(job["scene_id"], group):
            return True                   # its part comes with a group clip already sent
        run = self._redo_run(job, group)
        if run and run[0]["id"] != job["scene_id"]:
            return True                   # the run's first shot sends the group clip for it
        if group[0]["id"] != job["scene_id"] and not run:
            return not self._has_clip(group[0]["id"])
        if self._sends_group(job) is None:
            return False
        if self._refs(job) and any(shots.approved_image_path(self.p.conn, self.data_dir, job["project_id"], r["id"]) is None
                                   for r in group):
            return True                   # a reference group sends every shot's own picture: wait until all are approved
        return any((self._motion(r["id"]) or {"state": None})["state"] != "approved" for r in group)

    def _stamp(self, job, args) -> Dict:
        from . import formats, lineage
        from . import shots
        mp = self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (job["scene_id"],)).fetchone()
        group = self._sends_group(job)
        exact = shots.mode(self.p.project(job["project_id"])) != "multishot"   # H5 set-up: cut at the shots' own seconds
        refs = self._refs(job)
        from . import seedance_refs
        sent = ([{"id": r["id"], "idx": r["idx"], "exact": True, "refs": refs,
                  "duration_s": seedance_refs.floored(r["data"], self._cut_seconds(r)) if refs else self._cut_seconds(r)} for r in group]
                if group and exact
                else [{"id": r["id"], "idx": r["idx"], "duration_s": shots.billed_shot_seconds(r["data"])} for r in group] if group else None)
        proj = self.p.project(job["project_id"])
        audio = bool(proj["video_audio"]) if "video_audio" in proj.keys() else False
        return {"input_hash": lineage.video_input_hash(mp, formats.project_aspect(proj), args[4], audio) if mp else None,   # M16
                "source_job_id": lineage.approved_image_id(self.p.conn, shots.image_scene(self.p.conn, job["scene_id"])),
                "model": args[4],
                "sent_group": json.dumps(sent) if sent else None}

    def _cut_seconds(self, row) -> float:
        """A shot's length in the film: its motion prompt's seconds (stretched to the real voice), else the Director's."""
        mp = self._motion(row["id"])
        return round(float((mp["duration_sec"] if mp is not None and mp["duration_sec"] else None) or row["data"].get("duration_s") or 0), 2)

    def _submit_args(self, job):
        conn = self.p.conn
        mp = conn.execute("SELECT motion_prompt, negative_prompt, duration_sec, ref_video_path, ref_video_type"
                          " FROM motion_prompts WHERE scene_id=? AND state='approved'", (job["scene_id"],)).fetchone()
        from . import shots
        img = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'"   # M1: a later shot of a
                           " ORDER BY id DESC LIMIT 1", (shots.image_scene(conn, job["scene_id"]),)).fetchone()   # group has no picture
        if mp is None or img is None:
            return None
        path = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{img['id']}.png")
        green = self._green_source(job, img["id"])
        if green:
            path = green                              # V4 mode 2: the character acts on green, keyed onto the plate afterwards
        proj = self.p.project(job["project_id"])
        model = self._choice(job)["model"]            # per scene (ClipAI model guide) — see core.model_router
        duration = mp["duration_sec"]
        setup, group, secs = False, None, []
        if json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}").get("shot_no"):
            duration = math.ceil(float(duration or 0) - 1e-6)   # v3 shot: never shorter than planned (it is cut afterwards)
            from . import shots
            group = self._sends_group(job)
            refs = self._refs(job)
            setup = bool(group) and shots.mode(proj) != "multishot" and not refs
            if refs:                                              # Seedance reference only: the group's (or shot's) seconds, >= 4 s
                from . import seedance_refs
                secs = ([seedance_refs.floored(r["data"], self._cut_seconds(r)) for r in group] if group
                        else [float(duration or 0)])            # 28/09: a shot under ~1.5 s in a group was skipped by the model
                duration = seedance_refs.seconds(secs)
            elif setup:                                             # H5: one continuous take for the set-up's shots, cut afterwards
                secs = [self._cut_seconds(r) for r in group]
                duration = max(math.ceil(sum(secs) - 1e-6), 3)
            elif group:                                           # the whole group's length, one Kling generation
                duration = sum(shots.billed_shot_seconds(r["data"]) for r in group)
                model = "kling"
        motion = no_minor_age(mp["motion_prompt"])
        if secs and not setup and self._refs(job):
            from . import seedance_refs
            rows = self._ref_rows(job, group)
            parts = [((self._motion(r["id"]) or {"motion_prompt": ""})["motion_prompt"], s) for r, s in zip(rows, secs)]
            ids = seedance_refs.identity_pictures(conn, job["project_id"], rows, seedance_refs.MAX_PICTURES - len(rows))
            motion = no_minor_age(seedance_refs.prompt(parts, ids, clip_seconds=duration, model=model))
        if setup:
            motion = no_minor_age(shots.setup_motion([((self._motion(r["id"]) or {"motion_prompt": ""})["motion_prompt"], s)
                                                      for r, s in zip(group, secs)]))
        fix = model_fix(job["retry_reason"])
        if fix:
            motion = f"{motion} Fix: {fix}"      # W3: a retry sends the QC's fix, never the very same input again
            if secs and not setup and self._refs(job) and (group or []):
                motion = motion.replace(" Fix: ", " Fix (for the whole clip): ", 1)
        from . import looks
        motion, removed = looks.clean_prompt(proj, motion)       # ff_gameplay_visual.md: no realism words in an in-game project
        if removed:
            self._diag(job, "info", "look_words_removed",
                       "look in-game Free Fire: đã gỡ chữ kéo về tả thực khỏi prompt video — " + ", ".join(removed))
        args = (path, motion, looks.video_negative(proj, mp["negative_prompt"]), duration, model)
        subj_refs = []
        if proj["use_subjects"] and "seedance" in (model or ""):
            subj_refs = subject_links.usable_for_scene(self.p, job["scene_id"], subject_links.reference_cap(model))
        image_refs = []
        if "seedance" in (model or ""):
            # the project's own chosen resource pictures (same as Step 2's Deepix references) — automatic, no Subject Library upload needed
            scene_data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            image_refs = assets.scene_references(conn, job["project_id"], scene_data)
            missing = [r for r in image_refs if not os.path.exists(r["path"])]
            if missing:  # traceable: shows up in 📊 Theo dõi hiệu suất, points at exactly which picture went missing
                self._diag(job, "warn", "missing_reference",
                          "ảnh tham chiếu không đọc được (bỏ qua, video vẫn gen): " + ", ".join(r["label"] for r in missing))
                image_refs = [r for r in image_refs if r not in missing]
        ref_video = None
        if mp["ref_video_path"] and os.path.exists(mp["ref_video_path"]):
            ref_video = {"path": mp["ref_video_path"], "refer_type": mp["ref_video_type"] or "feature"}
        elif mp["ref_video_path"]:
            self._diag(job, "warn", "missing_reference",
                      f"video tham chiếu chuyển động không đọc được (bỏ qua, video vẫn gen): {mp['ref_video_path']}")
        if proj["video_audio"] or subj_refs or image_refs or ref_video:  # extra args only when used: older providers keep working
            args += (bool(proj["video_audio"]), subj_refs or None, image_refs or None, ref_video)
        return args

    def _usage(self, args, kwargs):
        info = getattr(self.provider, "usage_info", None)
        if info is None:
            return None
        resolution = (kwargs or {}).get("resolution") or (kwargs or {}).get("kling_mode")
        try:
            return info(args[4], args[3], resolution) if resolution else info(args[4], args[3])
        except TypeError:
            return info(args[4], args[3])

    def _record_usage(self, job, args, kwargs=None) -> None:
        usage = self._usage(args, kwargs)
        if usage is not None:
            model, tier, seconds = usage
            record_usage(self.p.conn, job["id"], "video", self.provider.name, model, tier, seconds, "second")

    def _over_budget(self, job, args, kwargs) -> Optional[str]:
        from . import budget, cost, project_budget
        try:
            usage = self._usage(args, kwargs)
        except ProviderError as e:                       # e.g. a model the provider does not know: nothing to price, nothing sent
            return f"không tính được giá clip ({e})"
        if usage:
            reason = budget.check_video(self.p.conn, self.provider.name, *usage)
            if reason or str(self.provider.name).startswith("mock"):
                return reason
            price = cost.clip_price(cost.load_pricing(), *usage) or 0.0
            return project_budget.check(self.p.conn, job["project_id"], "videos", price)
        return None if str(self.provider.name).startswith("mock") else budget.pricing_problem()

    def _on_refused(self, job, code, message: str) -> None:
        """Seedance's privacy filter refuses a start picture that looks like a real person (a realistic CGI frame too), and its
        copyright filter a clip of a known game character. Kling has neither: the scene — with its whole continuity group, one model per
        group — switches to Kling, so the retry goes through."""
        from .adapters.clipai import REAL_PERSON, classify_failure
        kind = code if code in (REAL_PERSON, RISK_CONTROL) else classify_failure(message)
        seedance = str(job["model"] or "").startswith("seedance")
        if not (kind == REAL_PERSON or (kind == RISK_CONTROL and seedance and "copyright" in (message or "").lower())):
            return
        if self._refs(job):                  # P2m group -> Seedance per shot -> Kling (the person's order, 2026-09-27)
            from . import seedance_refs
            group = self._sends_group(job)
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            step = seedance_refs.next_route(data, bool(group))
            ids = [r["id"] for r in group] if group else [job["scene_id"]]
            seedance_refs.set_route(self.p.conn, ids, step)
            why = "ảnh giống người thật" if kind == REAL_PERSON else "video có thể dính bản quyền"
            self._diag(job, "warn", kind, f"Seedance từ chối ({why}, dù ảnh đã đánh dấu) → {len(ids)} shot chuyển sang "
                       + ("Seedance từng shot" if step == "single" else "Kling từ khung đầu"))
            return True
        from . import model_router, shots
        ids = [r["id"] for r in shots.sequence_rows(self.p.conn, job["scene_id"])] or [job["scene_id"]]
        for sid in ids:
            model_router.set_override(self.p.conn, sid, "kling")
        why = "ảnh giống người thật" if kind == REAL_PERSON else "video có thể dính bản quyền"
        self._diag(job, "warn", kind, f"Seedance từ chối ({why}) → {len(ids)} cảnh/shot chuyển sang Kling")
        return True

    def _dest_path(self, job) -> str:
        idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["idx"]
        return os.path.join(self._dir(job["project_id"], "videos"), f"{idx:02d}.mp4")

    def _after_download(self, job, path: str) -> str:
        """v3 shot rows: the model makes at least 3-4 s, a shot may be shorter -> keep the full clip as <idx>_raw.mp4 and cut the
        shot's own length into <idx>.mp4, so render, voice placement and subtitles all use the cut length. A Kling multi-shot
        clip is first split into one clip per shot of its group; the other shots' jobs are completed with their part."""
        from . import shots
        sent = json.loads(job["sent_group"]) if "sent_group" in job.keys() and job["sent_group"] else None
        group = ([{"id": g["id"], "idx": g["idx"], "refs": bool(g.get("refs")),
                   "data": {"duration_s": g["duration_s"], "exact": bool(g.get("exact"))}} for g in sent]
                 if sent
                 else self._sends_group(job))       # M10: the group as it was sent (a later re-plan must not mis-cut a paid clip)
        if group:
            self._finish_group(job, path, group)
        try:
            if group or not self._refs(job):   # 28/09: a lone Seedance shot's prompt spreads the action over the whole clip (>= 4 s) —
                shots.trim_clip(self.p, job["scene_id"], path)   # cut to its 1-2 s plan, S5·1 lost the fall: kept whole instead
        except Exception as e:  # noqa: BLE001 - a clip that cannot be cut is still a usable (longer) clip
            self._diag(job, "warn", "trim_error", f"không cắt được clip theo độ dài shot ({type(e).__name__}: {e}); dùng nguyên clip")
        if not group:
            self._plate_video(job, path)
            from . import lipsync
            rec = lipsync.index(self.data_dir, job["project_id"]).get(str(job["scene_id"])) or {}
            if rec.get("state") == "generate_sent" and rec.get("job_id") == job["id"]:
                lipsync.mark(self.data_dir, job["project_id"], job["scene_id"], state="done")
        return path

    def _plate_mode(self, job) -> Optional[str]:
        """'green' (mode 2) / 'first_frame' (mode 1) for a shot with a location-pack plate, else None."""
        from . import features, location_pack
        if not features.on("location_plates") or location_pack.plate_of(self.data_dir, job["project_id"], job["scene_id"]) is None:
            return None
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
        return "green" if data.get("plate_mode") == "green" else "first_frame"

    def _green_source(self, job, image_job_id: int) -> Optional[str]:
        from . import location_pack
        if self._plate_mode(job) != "green":
            return None
        path = location_pack.green_path(self.data_dir, job["project_id"], image_job_id)
        return path if os.path.exists(path) else None

    def _plate_video(self, job, path: str) -> None:
        """V4: mode 2 — key the green clip onto the plate frame by frame; both modes — falling weather + lightning; mode 1 — how much of
        the plate the video model kept (plate_qc), recorded for the automatic run's fallback to mode 2."""
        mode = self._plate_mode(job)
        if mode is None:
            return
        from . import composite, ffmpeg_studio, location_pack, plate_env, plate_qc, shots
        plate = location_pack.plate_of(self.data_dir, job["project_id"], job["scene_id"])
        env = plate.get("env") or {"time": "day", "weather": "clear"}
        ffmpeg = ffmpeg_studio.find_ffmpeg()
        tmp = path + ".plate.mp4"
        try:
            if mode == "green":
                composite.composite_video(path, plate, tmp, ffmpeg, env)
                os.replace(tmp, path)
            done = plate_env.overlay_video(path, tmp, env, ffmpeg, seed=job["id"])
            if done == tmp:
                os.replace(tmp, path)
            if mode == "first_frame":
                img = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC"
                                          " LIMIT 1", (shots.image_scene(self.p.conn, job["scene_id"]),)).fetchone()
                mask = location_pack.mask_path(self.data_dir, job["project_id"], img["id"]) if img else None
                res = plate_qc.background_score(path, plate.get("shadow") or plate["plate"], ffmpeg, mask)
                location_pack.record_video_qc(self.data_dir, job["project_id"], job["scene_id"], job["id"], res, mode)
                if not res["ok"]:
                    self._diag(job, "warn", "plate_redrawn", f"video vẽ lại nền (điểm giống nền {res['score']}) — lần gen lại sẽ diễn trên phông "
                                                              "xanh rồi ghép (cách 2)")
        except Exception as e:  # noqa: BLE001 - the clip is still usable as it came
            self._diag(job, "warn", "plate_video", f"không xử lý được nền 3D cho clip ({type(e).__name__}: {e}) — dùng nguyên clip")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _finish_group(self, leader, path: str, group) -> None:
        from . import formats, lineage, shots
        conn = self.p.conn
        dests = [path] + [os.path.join(self._dir(leader["project_id"], "videos"), f"{r['idx']:02d}.mp4") for r in group[1:]]
        if group[0].get("refs"):
            from . import seedance_refs
            res = seedance_refs.split(path, group, dests)
            if res["by"] != "detected":       # said, not hidden: the parts may straddle a cut
                self._diag(leader, "warn", "group_cut_by_plan", f"clip nhóm {len(group)} shot không dò đủ {len(group) - 1} điểm cắt — "
                           f"cắt theo số giây dự kiến ({res['cuts']}); xem lại chỗ cắt ở Bước 4")
        else:
            shots.split_group_clip(path, group, dests)
        aspect = formats.project_aspect(self.p.project(leader["project_id"]))
        for r, dest in zip(group[1:], dests[1:]):
            follower = conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND state='queued' ORDER BY id DESC LIMIT 1",
                                    (r["id"],)).fetchone()
            jid = follower["id"] if follower else self.p.create_job(r["id"], "video_gen")
            mp = self._motion(r["id"])
            conn.execute("UPDATE jobs SET group_leader=?, external_id=?, model=?, input_hash=?, source_job_id=? WHERE id=?",
                         (leader["id"], leader["external_id"], leader["model"] or "kling",
                          lineage.video_input_hash(mp, aspect) if mp else None,
                          lineage.approved_image_id(conn, shots.image_scene(conn, r["id"])), jid))
            conn.commit()
            self.p.start(jid)
            try:
                shots.trim_clip(self.p, r["id"], dest)
            except Exception as e:  # noqa: BLE001
                self._diag(self.p.job(jid), "warn", "trim_error", f"không cắt được clip theo độ dài shot: {e}")
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, jid))
            conn.commit()
            self.p.succeed(jid)


def previous_frame_job(conn, project_id: int, idx: int, sequence=None):
    """The approved picture a storyboard frame follows on from: with a `sequence`, the nearest earlier scene of the SAME sequence
    (same place, continuous action — a new sequence starts fresh instead of copying another place); without one, the scene right
    before. Row with `id`, or None."""
    rows = conn.execute("SELECT s.idx, s.data, (SELECT j.id FROM jobs j WHERE j.scene_id=s.id AND j.type='image_gen'"
                        " AND j.state='approved' ORDER BY j.id DESC LIMIT 1) AS id FROM scenes s"
                        " WHERE s.project_id=? AND s.idx<? ORDER BY s.idx DESC", (project_id, idx)).fetchall()
    for r in rows:
        if sequence is None:
            return r if r["idx"] == idx - 1 and r["id"] is not None else None
        if json.loads(r["data"] or "{}").get("sequence") == sequence and r["id"] is not None:
            return r
    return None


FRAMING = {"ECU": "extreme close-up — only the face or one detail fills the frame",
           "CU": "close-up — head and shoulders fill the frame, no legs or full body",
           "MCU": "medium close-up — from mid-chest up, no legs",
           "MS": "medium shot — from the waist up",
           "MLS": "medium long shot — from the knees up, the place visible around",
           "WS": "wide shot — whole bodies visible, with the place around them",
           "EWS": "extreme wide shot — people small inside a large place",
           "GAME_TPS": "third-person game camera behind the character, slightly above the shoulder"}
CAMERA = {"eye": "camera at eye level", "low": "low angle looking up", "high": "high angle looking down", "overhead": "top-down view",
          "dutch": "tilted (dutch) camera", "ots": "over the shoulder", "pov": "first-person view"}


def framing_sentence(data: Dict) -> str:
    """F9/I1: the shot size and camera in words the image model follows ("MCU" alone was read as a full-body picture in GĐ6)."""
    size = data.get("size") or assets.shot_size(data)
    bits = [FRAMING[size]] if size in FRAMING else []
    if data.get("angle") in CAMERA:
        bits.append(CAMERA[data["angle"]])
    return ("Framing: " + ", ".join(bits) + ". ") if bits else ""


def same_framing(a: Dict, b: Dict) -> bool:
    """F8: a previous frame only helps when it was shot the same way (a wide frame drags its composition into a close-up)."""
    return (assets.shot_size(a) == assets.shot_size(b)) and (a.get("angle") or "eye") == (b.get("angle") or "eye")


def chain_previous(proj, scene_data) -> bool:
    """Send the previous approved frame as an extra reference? storyboard_mode 1 = always, 2 = never, 0 (default) = automatic:
    only inside a sequence (consecutive shots of one place / continuous action, as set by the Director or by hand)."""
    from . import features
    mode = proj["storyboard_mode"] or 0
    return mode == 1 or (mode == 0 and bool(scene_data.get("sequence")) and features.on("chain_previous_auto"))


_MINOR_AGE = re.compile(r"\b(?:[1-9]|1[0-7])[- ]?(?:-|\s)?years?[- ]old\b[,]?\s*", re.IGNORECASE)


def no_minor_age(text: str) -> str:
    """No age under 18 in a prompt sent to a picture/video model: GPT Image 2.5 refused "KELLY, 17-year-old young woman … in
    darkness, eyes red" (safety system, 2026-09-25, trial 2A) while the same shot family without the age passed. The age adds nothing
    the reference pictures do not already show."""
    return _MINOR_AGE.sub("", text or "")


def lock_note(conn, project_id: int, cast) -> str:
    """Character Lock of the people in the shot, as one sentence for the image model (what must never drift)."""
    from . import features, profile_digest
    parts = []
    for r in conn.execute("SELECT name, lock_rules FROM characters WHERE project_id=?", (project_id,)):
        if r["name"] not in (cast or []):
            continue
        short = profile_digest.for_character(conn, project_id, r["name"], "lock_medium") if features.on("profile_digest") else None
        if short:                                   # V4 4.4: the ≤ 500-character form of the approved profile (feature profile_digest)
            parts.append(f"{r['name']}: {short}")
            continue
        rules = assets.standard_for(conn, project_id, r["name"])        # T1: the approved library profile wins
        if rules is None:
            try:
                rules = json.loads(r["lock_rules"]) if r["lock_rules"] else None
            except ValueError:
                rules = None
        if not rules:
            continue
        bits = [f"keep {rules['must_keep']}" if rules.get("must_keep") else "",
                f"never {rules['forbidden']}" if rules.get("forbidden") else "",
                f"about {rules['height_m']:g} m tall" if rules.get("height_m") else ""]
        if any(bits):
            parts.append(f"{r['name']}: " + "; ".join(b for b in bits if b))
    return (" Identity lock — " + " | ".join(parts) + ".") if parts else ""


_GAZE = re.compile(r"\b(look|looks|looking|gaze|glanc|eyes|facing|stares?|nhìn)\w*", re.I)


def seen_from_behind(data: Dict, name: str) -> Optional[bool]:
    """True when the shot shows this character from behind (over their shoulder / their back), False when it plainly faces them, None
    when the words do not say."""
    words = " ".join(str(data.get(k) or "") for k in ("image_prompt", "blocking", "start_frame", "shot", "action"))
    n = re.escape(name)
    if re.search(rf"over\s+{n}'?s?\s+shoulder|{n}'?s?\s+(back|shoulder)\b|{n}\b[^.,;]{{0,40}}(back to (the )?camera|from behind|seen from behind)"
                 rf"|qua vai\s+{n}|lưng\s+{n}", words, re.I):
        return True
    if str(data.get("angle") or "").lower() == "ots":
        return None
    return False


def view_notes(conn, project_id: int, data: Dict) -> str:
    """Agent QC 2026-09-27 (#8): the profiles already said "LEFT arm gauntlet" and "cap worn backwards", yet from behind the model put
    KENTA's gauntlet on the wrong side (4 frames) and turned MAXIM's cap forward (5 frames) — it does not work out how left/right and a
    reversed cap look from the other side. Each profile's `view_notes` ({"facing_camera", "from_behind"}) says it for the shot's view."""
    parts = []
    cast = [str(n) for n in data.get("characters") or []]
    views = {n: seen_from_behind(data, n) for n in cast}
    if any(v is True for v in views.values()):       # over X's shoulder: the others face the camera
        views = {n: (False if v is None else v) for n, v in views.items()}
    for name in cast:
        rules = assets.standard_for(conn, project_id, str(name)) or {}
        notes = rules.get("view_notes") if isinstance(rules.get("view_notes"), dict) else {}
        if not notes:
            continue
        behind = views[name]
        if behind is True and notes.get("from_behind"):
            parts.append(notes["from_behind"])
        elif behind is False and notes.get("facing_camera"):
            parts.append(notes["facing_camera"])
        elif behind is None:
            parts += [f"If {name} is seen from behind: {notes['from_behind']}" if notes.get("from_behind") else "",
                      f"If {name} faces the camera: {notes['facing_camera']}" if notes.get("facing_camera") else ""]
    parts = [p for p in parts if p]
    return (" " + " ".join(p.rstrip(".") + "." for p in parts)) if parts else ""


def build_image_prompt(conn, project_id: int, data: Dict, core: Optional[str] = None, fix: Optional[str] = None,
                       blocking_label: str = "Blocking") -> Tuple[str, list]:
    """THE picture prompt of a shot (start picture and K1 end frame share it, so a safeguard added here reaches both): the in-game look
    cleaned of realism words, framing, the text (`core`, default the shot's image_prompt), blocking, the Director's acting, the Character
    Lock, the look sentence, the fix of a retry, the place in words, and no age under 18. Returns (prompt, realism words removed)."""
    from . import looks, performance
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    text = data.get("image_prompt") if core is None else core
    text, removed = looks.clean_prompt(proj, text or "")   # ff_gameplay_visual.md: these words pull the picture towards a realistic shooter
    prompt = framing_sentence(data) + text
    if (data.get("blocking") or "").strip():       # where each person stands/faces, so shots of one sequence agree
        prompt = f"{prompt.rstrip('.')}. {blocking_label}: {data['blocking'].strip()}"
        if _GAZE.search(data["blocking"]):          # agent QC #8: eyes turned the wrong way (S2·4, S3·8) — the gaze is part of the shot
            prompt += " The gaze follows the blocking exactly: who looks at whom, toward frame-left or frame-right."
    prompt += performance.image_sentence(data)     # GĐ4: the Director's acting (director.md Đ4) at the start of the shot
    prompt += lock_note(conn, project_id, data.get("characters"))
    prompt += view_notes(conn, project_id, data)
    prompt += looks.image_sentence(proj)
    if fix:
        prompt = f"{prompt}. Fix: {fix}"
    place = assets.scene_location(conn, project_id, data)
    if place is not None:                          # B1: the place in words (+ real landmark heights), whatever pictures go
        prompt += " " + assets.location_text(conn, place)
    return no_minor_age(prompt), removed


def sendable_references(refs, model: Optional[str], limit: Optional[int] = None) -> Tuple[list, list]:
    """The reference pictures that will really reach Deepix (readable, ≤ 10 MB, within the model's picture limit), and why the others
    are left out. The prompt's "Image 2 is KELLY" numbering must be built from the kept list, never from the list before the cut."""
    from . import image_models
    from .adapters.deepix import MAX_REFERENCES as DEEPIX_MAX, reference_problem
    cap = image_models.max_refs(model, DEEPIX_MAX) if model else DEEPIX_MAX
    cap = min(cap, limit) if limit else cap
    kept, dropped = [], []
    for r in refs:
        problem = reference_problem(r["path"])
        if problem:
            dropped.append(f"{r['label']} ({problem})")
        elif len(kept) >= cap:
            dropped.append(f"{r['label']} (quá {cap} ảnh model nhận)")
        else:
            kept.append(r)
    return kept, dropped


class ImageRunner(_Runner):
    job_type = "image_gen"

    def _submit_kwargs(self, job) -> Dict:
        from . import formats, image_models
        proj = self.p.project(job["project_id"])
        aspect = formats.project_aspect(proj)
        size = image_models.size_for(proj, image_models.of_project(proj))   # 🧪 cheap test mode: the smallest size the model takes
        out = {"size": size} if aspect or size != formats.spec(None)["deepix"] else {}
        if getattr(self.provider, "supports_model", False):
            out["model"] = image_models.of_project(proj)     # the project's picture model (Step 1)
        sb = getattr(self, "_storyboard", {}).pop(job["id"], None)
        if sb is not None:
            out["storyboard"] = sb                           # storyboard mode: prompt_key 14 + the group fields
        return out

    def _over_budget(self, job, args, kwargs) -> Optional[str]:
        from . import budget
        model = (kwargs or {}).get("model")
        info = getattr(self.provider, "usage_info", None)
        if model is None and info is not None:
            try:
                model = info()[0]
            except Exception:  # noqa: BLE001 - a provider without a model name: priced as unknown (refused while the limit is on)
                model = None
        reason = budget.check_image(self.p.conn, self.provider.name, model)
        if reason or str(self.provider.name).startswith("mock"):
            return reason
        from . import cost, project_budget
        price = cost._number(cost.load_pricing().get("per_image", {}).get(model)) if model else None
        return project_budget.check(self.p.conn, job["project_id"], "images", price or 0.0)

    def _plate(self, job, data=None):
        """The location-pack plate of this shot (feature location_plates), else None."""
        from . import features, location_pack
        if not features.on("location_plates"):
            return None
        return location_pack.plate_of(self.data_dir, job["project_id"], job["scene_id"])

    def _wait(self, job) -> bool:
        """v3: the picture of a shot that continues the previous one waits for that shot's approved picture (sent as reference).
        V4: a shot set at a 3D place waits for its plate (rendered by the automatic run's plates phase)."""
        from . import shots
        from . import features
        from . import scene_storyboard
        from . import scene_establish
        if scene_establish.enabled():
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            model = None
            if getattr(self.provider, "supports_model", False):
                from . import image_models
                model = image_models.of_project(self.p.project(job["project_id"]))
            state = scene_establish.step(self.p.conn, job["project_id"], data.get("story_scene"), self.provider, self.data_dir, model,
                                         lambda sev, code, msg: self._diag(job, sev, code, msg))
            if state == "waiting":
                return True                                  # the scene's wide establishing picture is drawn first
        if scene_storyboard.enabled() and getattr(self.provider, "supports_storyboard", False) and \
                scene_storyboard.waits(self.p.conn, self.data_dir, job["project_id"], job["scene_id"]):
            return True                                      # storyboard mode: the scene's anchor frame is drawn first
        if features.on("location_plates"):
            from . import location_pack
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            if location_pack.needs_plate(self.p.conn, job["project_id"], data) and self._plate(job) is None and \
                    not location_pack.plate_failed(self.data_dir, job["project_id"], job["scene_id"]):
                return True                                  # a failed render is not waited for: the shot draws a normal picture
        proj = self.p.project(job["project_id"])
        chains = proj["storyboard_mode"] == 1 or (proj["storyboard_mode"] != 2 and features.on("chain_previous_auto"))
        return bool(shots.mode(proj)) and chains and shots.waits_for_previous_image(self.p.conn, job["scene_id"])

    def _stamp(self, job, args) -> Dict:
        from . import lineage
        sent = getattr(self, "_sent", {}).pop(job["id"], None)
        return {"input_hash": lineage.current_image_hash(self.p.conn, job["project_id"], job["scene_id"]),
                "sent_refs": json.dumps(sent, ensure_ascii=False) if sent is not None else None}

    def _submit_args(self, job):
        conn = self.p.conn
        scene = conn.execute("SELECT idx, data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
        data = json.loads(scene["data"] or "{}")
        prompt = data.get("image_prompt")
        if not prompt:
            return None
        from . import looks
        cleaned, removed = looks.clean_prompt(self.p.project(job["project_id"]), prompt)
        if removed:                                    # ff_gameplay_visual.md: these words pull the picture towards a realistic shooter
            self._diag(job, "info", "look_words_removed",
                       "look in-game Free Fire: đã gỡ chữ kéo về tả thực khỏi prompt ảnh — " + ", ".join(removed))
            data["image_prompt"] = prompt = cleaned
        for gap in assets.reference_gaps(conn, job["project_id"], data):     # luật 1: a missing reference is said at generation time
            self._diag(job, assets.gap_severity(gap), "missing_reference", gap)
        plate = self._plate(job)
        if plate is not None:
            return self._green_args(job, data, plate)
        prompt, _ = build_image_prompt(conn, job["project_id"], data, fix=model_fix(job["retry_reason"]))
        from . import scene_establish
        light = scene_establish.light_sentence(data)
        if light:
            prompt = f"{prompt} {light}"
        proj = self.p.project(job["project_id"])
        chain = chain_previous(proj, data)
        from . import features
        plan = layout.layout_reference(self.data_dir, job["project_id"], scene["idx"], data) if features.on("layout_to_model") else None
        from . import image_models
        model = image_models.of_project(proj)
        sheets = image_models.accepts_sheets(model) and getattr(self.provider, "supports_model", False)
        limit = min(image_models.max_refs(model, assets.MAX_REFERENCES), 12) if sheets else assets.MAX_REFERENCES
        refs = assets.scene_references(conn, job["project_id"], data,   # the layout and the previous frame keep their slots
                                       limit=limit, reserve=(1 if chain else 0) + (1 if plan else 0), sheets=sheets)
        if plan:
            refs = [plan] + refs
        from . import scene_establish
        est = scene_establish.reference(self.data_dir, job["project_id"], data.get("story_scene"))
        if est:                                        # the scene's wide establishing picture: the shared reference for the place
            refs = ([r for r in refs if r.get("role") != "location"][:max(limit - 2, 1)]
                    + [r for r in refs if r.get("role") == "location"][:1] + [est])
        if chain and len(refs) < limit:
            # Deepix has no scriptable Storyboard (web UI only, see docs/CLIPAI_FEATURES.md) — this chains the
            # previous scene's approved picture in as an extra image-to-image reference instead, so style/lighting
            # carry over the way a real storyboard would.
            prev = previous_frame_job(conn, job["project_id"], scene["idx"], data.get("sequence"))
            if prev is not None and proj["storyboard_mode"] != 1 and not same_framing(json.loads(prev["data"] or "{}"), data):
                prev = None                            # F8: automatic chaining only between shots framed the same way
            if prev is not None:
                prev_path = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{prev['id']}.png")
                if os.path.exists(prev_path):
                    refs = refs + [{"path": prev_path, "label": "previous scene", "role": "previous_scene"}]
        return self._finish_args(job, prompt, refs)

    def _green_args(self, job, data, plate):
        """V4 location pack: the character alone on flat green, framed and lit as the plate's camera; only the characters'
        references go (the place is the plate — no place picture, no place words, no previous frame dragging a background)."""
        from . import location_pack, looks
        conn = self.p.conn
        shot = location_pack.without_place(data)
        prompt = framing_sentence(shot) + location_pack.place_free(data["image_prompt"])
        blocking = location_pack.place_free(data.get("blocking") or "")
        if blocking:
            prompt = f"{prompt}. Blocking: {blocking}"
        from . import performance
        prompt += performance.image_sentence(data)
        prompt += lock_note(conn, job["project_id"], data.get("characters"))
        prompt += looks.image_sentence(self.p.project(job["project_id"]))
        place = assets.scene_location(conn, job["project_id"], data)
        entry = location_pack.model3d(conn, place["id"]) if place else None
        prompt += " " + location_pack.green_prompt(data, plate, (entry or {}).get("sun_azimuth", 250.0))
        fix = model_fix(job["retry_reason"])
        if fix:
            prompt = f"{prompt}. Fix: {fix}"
        refs = assets.scene_references(conn, job["project_id"], shot, limit=assets.MAX_REFERENCES)
        refs = [r for r in refs if r.get("role") != "location"]
        prompt = no_minor_age(prompt)
        return self._finish_args(job, prompt, refs, without_place=True,
                                 extra_sent=[{"label": "plate", "role": "location_pack", "file": os.path.basename(plate["plate"])}])

    def _finish_args(self, job, prompt: str, refs, without_place: bool = False, extra_sent=None):
        """The picture job's (prompt, reference paths). Storyboard mode (feature storyboard_api, a provider that draws storyboard
        frames): the scene's shared references + the anchor frame replace the shot's own, and the storyboard fields go with the job
        (core/scene_storyboard.py, the web Weave Canvas way). Only the pictures that will really be sent are numbered in the note
        (a dropped picture used to shift "Image 2 is KELLY" onto the wrong person) — every dropped one is reported."""
        from . import image_models
        proj = self.p.project(job["project_id"])
        model = image_models.of_project(proj) if getattr(self.provider, "supports_model", False) else None
        refs, dropped = sendable_references(refs, model)
        if dropped:
            self._diag(job, "warn", "missing_reference", "ảnh tham chiếu không gửi được (bỏ khỏi yêu cầu và khỏi câu đánh số ảnh): "
                       + ", ".join(dropped))
        self._sent = getattr(self, "_sent", {})
        self._sent[job["id"]] = [{"label": r["label"], "role": r["role"], "file": os.path.basename(r["path"])} for r in refs] + \
            list(extra_sent or [])
        from . import scene_storyboard
        if scene_storyboard.enabled() and getattr(self.provider, "supports_storyboard", False):
            g = scene_storyboard.group_of(self.p.conn, job["project_id"], job["scene_id"])
            if g is not None:
                shared = scene_storyboard.shared_references(self.p.conn, job["project_id"], g["shots"], without_place=without_place)
                from . import scene_establish
                est = None if without_place else scene_establish.reference(self.data_dir, job["project_id"], g["story_scene"])
                if est:                                # the scene's wide establishing picture: the shared reference for the place
                    shared = ([r for r in shared if r.get("role") != "location"][:6]
                              + [r for r in shared if r.get("role") == "location"][:1] + [est])
                shared, dropped = sendable_references(shared, model)     # before the mapping text is built from the list
                if dropped:
                    self._diag(job, "warn", "missing_reference", "ảnh tham chiếu storyboard không gửi được: " + ", ".join(dropped))
                fields = scene_storyboard.job_fields(self.p.conn, self.data_dir, job["project_id"], job["scene_id"], shared, job["id"],
                                                     green=without_place)
                if fields is not None:
                    refs = fields["refs"]
                    self._storyboard = getattr(self, "_storyboard", {})
                    self._storyboard[job["id"]] = fields["storyboard"]
                    self._sent = getattr(self, "_sent", {})
                    self._sent[job["id"]] = [{"label": r["label"], "role": r.get("role", ""), "file": os.path.basename(r["path"])}
                                             for r in refs] + [{"label": "storyboard", "role": "storyboard",
                                                                "file": fields["storyboard"]["storyboard_id"]}]
        if refs:                                       # the chosen resources' pictures go with the prompt (image-to-image)
            return (assets.reference_note(refs) + "Scene: " + prompt, [r["path"] for r in refs])
        return (prompt,)

    def _after_download(self, job, path: str) -> str:
        """V4 location pack: the downloaded picture is the character on green — keep it (job_<id>_green.png, the video of mode 2
        starts from it), composite it on the plate into the job's picture, add falling weather."""
        plate = self._plate(job)
        if plate is None:
            from . import qc_scene
            if qc_scene.enabled():                     # QC layer 0: code checks as the picture arrives (free)
                data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
                flags = qc_scene.check_frame(path, data)
                qc_scene.record_flags(self.data_dir, job["project_id"], job["id"], flags)
                sure = [f for f in flags if f["severity"] == "redraw"]
                tried = str(job["retry_reason"] or "")
                again = [f for f in sure if f["fix"] in tried]
                if again:                              # luật 6: the same fault after its own fix → stop, a person decides (#8: CU
                    for f in again:                    # shots came out MCU 3 times running — 2 paid redraws for nothing)
                        f["severity"] = "flag"
                        f["problem"] += " (vẫn lỗi sau khi đã vẽ lại có câu sửa — để người xem)"
                    qc_scene.record_flags(self.data_dir, job["project_id"], job["id"], flags)
                    sure = [f for f in sure if f not in again]
                if sure:
                    raise RedrawWithFix("QC lớp 0: " + "; ".join(f["problem"] for f in sure), " ".join(f["fix"] for f in sure))
            return path
        from . import composite, location_pack, plate_env
        green = location_pack.green_path(self.data_dir, job["project_id"], job["id"])
        from . import composite as _composite
        share = _composite.green_share(path)
        if share is not None and share < _composite.MIN_GREEN_BORDER:
            os.replace(path, green)
            raise RedrawWithFix(f"model không vẽ phông xanh (viền ảnh chỉ {share:.0%} là xanh) — không ghép (sẽ thành khung chữ nhật dán lên "
                                "nền 3D); vẽ lại", GREEN_FIX)
        try:
            os.replace(path, green)
            res = composite.composite(green, plate, path, plate.get("env"),
                                      mask_out=location_pack.mask_path(self.data_dir, job["project_id"], job["id"]))
            plate_env.overlay_still(path, path, plate.get("env") or {"time": "day", "weather": "clear"}, seed=job["id"])
        except Exception as e:  # noqa: BLE001 - a picture that cannot be composited is shown as it came (and said)
            if os.path.exists(green) and not os.path.exists(path):
                os.replace(green, path)
            self._diag(job, "error", "composite", f"không ghép được nhân vật lên nền 3D ({type(e).__name__}: {e}) — ảnh giữ nguyên phông xanh")
            return path
        if res.get("occluded_share", 0) > 0.3:
            self._diag(job, "warn", "occluded", f"nhân vật bị vật phía trước che {res['occluded_share']:.0%} — xem lại chỗ đứng / góc máy")
        return path

    def _record_usage(self, job, args, kwargs=None) -> None:
        info = getattr(self.provider, "usage_info", None)
        if info is not None:
            chosen = (kwargs or {}).get("model")
            model, tier = info(chosen) if chosen else info()
            record_usage(self.p.conn, job["id"], "image", self.provider.name, model, tier, 1, "image")
            if chosen:                                   # which picture model made this job (A/B, cost per model)
                self.p.conn.execute("UPDATE jobs SET model=? WHERE id=?", (chosen, job["id"]))
                self.p.conn.commit()

    def _dest_path(self, job) -> str:
        return os.path.join(self._dir(job["project_id"], "images"), f"job_{job['id']}.png")
