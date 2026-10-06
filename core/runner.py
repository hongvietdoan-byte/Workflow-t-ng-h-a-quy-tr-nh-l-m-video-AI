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
from .states import InvalidTransition, JobState
from .preflight import record_failure
from .providers import RISK_CONTROL, ProviderError
from . import budget, throttle as throttle_store
from .throttle import THROTTLE

NOT_CREATED = "not_created"            # core.adapters.clipai.NOT_CREATED: task id returned, task never created
NOT_CREATED_RESENDS = 3
RESEND_NOTE = "gửi lại: nhà cung cấp không tạo task"


def _job_ids(job) -> dict:
    """job_id / scene_id of a job row (or a partial dict) for a diag line (S14.16 money warnings)."""
    keys = job.keys()
    return {"job_id": job["id"] if "id" in keys else None, "scene_id": job["scene_id"] if "scene_id" in keys else None}


def model_fix(retry_reason: Optional[str]) -> Optional[str]:
    """The fix sentence a retry sends to the picture/video model, or None. A resend of the same input after a provider failure
    (RESEND_NOTE / pipeline.PLAIN_RESEND) carries a note for people only — it is never put into the model's prompt. Nor does a take whose
    shot prompt the Director already rewrote (pipeline.REWRITE_NOTE, S14.17): the fix is in the prompt itself."""
    from .pipeline import PLAIN_RESEND, REWRITE_NOTE
    text = (retry_reason or "").strip()
    if not text or text.startswith(RESEND_NOTE) or text.startswith(PLAIN_RESEND) or text.startswith(REWRITE_NOTE):
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
            sent = self._submit_pending(project_id)
        finally:
            lock.release()
        self._script_cap_stop(project_id)
        return sent

    def _script_cap_stop(self, project_id: int) -> None:
        """S14.2 rà soát A2 (a): a command-line run hit its --max-usd (core.script_cap) — its queued jobs will never be sent, so they
        are cancelled (said in the job history), and once nothing sent is still running CapReached ends the script's wait loop now
        instead of after its 30–45 minute timeout. No lock active (dashboard / autopilot) → nothing."""
        from . import script_cap
        cap = script_cap.active()
        if cap is None or not cap.stopped:
            return
        for job in self._jobs(project_id, "queued"):
            try:
                self.p.transition(job["id"], JobState.CANCELLED, actor="script_cap",
                                  note="lệnh dòng lệnh chạm trần --max-usd — không gửi")
            except InvalidTransition:
                pass
        if not self._jobs(project_id, "running"):
            raise script_cap.CapReached(cap.stopped)

    def _submit_pending(self, project_id: int) -> int:
        if self.p.project(project_id)["paused"]:
            return 0
        slots = self.max_concurrent - len(self._jobs(project_id, "running"))
        submitted = 0
        for job in self._jobs(project_id, "queued"):
            if slots <= 0:
                break
            if submitted and self.p.project(project_id)["paused"]:
                break               # T2: paused while this pass was sending — the jobs sent so far are running, send no more
            if self._wait(job):
                continue            # v3: this job is sent later (after the previous shot's picture / with its multi-shot group)
            if job["external_id"]:
                # T2: its task already exists at the provider (a multi-shot follower given the leader's task, relink_failed, or a send
                # whose RUNNING step was lost) — sending it again would pay twice. It only moves to RUNNING; the next poll fetches it.
                # Checked BEFORE _blocked (rà soát B1a): stale inputs must not write off a task already paid for.
                stale = self._blocked(job)
                self._running(job["id"], "đã có task ở nhà cung cấp — không gửi lại")
                if stale:
                    self._diag(job, "warn", "stale_paid", f"đầu vào đã cũ ({stale}) nhưng task {job['external_id']} đã trả tiền — lấy kết "
                                                          "quả về, không gửi lại")
                else:
                    self._diag(job, "info", "already_sent", f"job đã có task {job['external_id']} ở nhà cung cấp — chuyển sang đang chạy, "
                                                            "không gửi lại (tránh trả tiền 2 lần)")
                slots -= 1
                continue
            blocked = self._blocked(job)
            if blocked:
                self._diag(job, "warn", "stale_input", f"không gửi: {blocked}")
                self._running(job["id"])                 # QUEUED→FAILED is not a transition (core/states.py): RUNNING, then fail
                self.p.fail(job["id"], f"stale_input: {blocked}")
                continue
            args = self._submit_args(job)
            if args is None and self._editing(job):
                continue            # M5: the person is editing this shot's motion prompt — wait for the approval, do not burn a try
            if args is None:
                self._diag(job, "error", "missing_input", "thiếu đầu vào (ảnh đã duyệt / motion prompt / prompt ảnh)")
                self._running(job["id"])
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
                    break                        # a real stop (S14.16: the service is out of credit): leave everything queued, say why
                try:
                    task_id = self.provider.submit(*args, **kwargs)
                except ProviderError as e:
                    if e.code == "rate_limited" and THROTTLE.on_rate_limited(self.job_type):   # halve the learned limit
                        self._throttle_changed()
                    if e.transient:
                        self._diag(job, "warn", e.code, f"gửi job bị từ chối/tạm lỗi, sẽ thử lại: {e}")
                        break  # network/server hiccup: leave the job queued, try again next heartbeat
                    if e.code == "out_of_credit":           # Data Pack P5: halt every later send to this service, say it once
                        from . import budget as _budget
                        _budget.halt(self.p.conn, self.provider.name, str(e))
                        self._diag(job, "error", e.code, f"HẾT TIỀN ở {self.provider.name} — đã dừng mọi lượt gửi; job giữ trong hàng "
                                   "đợi, nạp tiền rồi mở lại ở ⚙ → 💵 Ngân sách")
                        break
                    self._diag(job, "warn" if e.code == RISK_CONTROL else "error", e.code, f"gửi job thất bại: {e}")
                    self._running(job["id"])
                    switched = self._record_provider_failure(job, e.code, str(e))
                    self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
                    if switched:
                        self._retry_switched(job)
                    continue
                # T2: the task exists (and may be billed) from here on. Its id, its stamp and RUNNING are one transaction (the UPDATEs are
                # not committed; transition() commits them with the state) — never Pipeline.start(): a pause pressed while submit()
                # was in flight made start() raise and left a paid job queued, sent and paid again on the next pass.
                self.p.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (task_id, job["id"]))
                for col, value in self._stamp(job, args).items():
                    self.p.conn.execute(f"UPDATE jobs SET {col}=? WHERE id=?", (value, job["id"]))
                try:
                    self._running(job["id"])
                except InvalidTransition as e:
                    self.p.conn.commit()                    # keep the task id: it is the only link to what may be billed
                    self._record_usage(job, args, kwargs)
                    self._cancelled_in_flight(job, task_id, e)
                    continue
                self._record_usage(job, args, kwargs)
            slots -= 1
            submitted += 1
        return submitted

    def _running(self, job_id: int, note: Optional[str] = None) -> None:
        """QUEUED → RUNNING without Pipeline.start()'s pause check (T2): used once the task exists at the provider, or on the way to
        FAILED (QUEUED→FAILED is not a transition). Commits whatever the caller wrote on the job before it, in the same transaction."""
        self.p.transition(job_id, JobState.RUNNING, note=note)

    def _cancelled_in_flight(self, job, task_id: str, error: Exception) -> None:
        """T2: the job was cancelled (cancel_all_active) while submit() was in flight — the provider task exists and may be billed. Its
        id and ledger row are kept (written by the caller); the task is cancelled at the provider; the diagnostics say all of it."""
        state = self.p.job(job["id"])["state"]
        try:
            if str(getattr(self.provider, "name", "")).startswith(NO_CANCEL_API):
                asked = NO_CANCEL_NOTE                  # nothing to call: never claim a cancel that did not happen
            else:
                self.provider.cancel(task_id)
                asked = "đã yêu cầu hủy ở nhà cung cấp"
        except Exception as e:  # noqa: BLE001 - a provider without cancel (Deepix) / a network error: said, not hidden
            asked = f"KHÔNG hủy được ở nhà cung cấp ({type(e).__name__}: {e})"
        self._diag(job, "error", "cancelled_in_flight",
                   f"job bị hủy ({state}) trong lúc đang gửi — task {task_id} đã tạo ở {self.provider.name}, có thể đã tính tiền "
                   f"(đã ghi sổ chi); {asked}. Chi tiết: {error}")

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
        self._running(new_id, f"nối lại task thật {new_ext}")     # T2: one transaction with the task id; nothing is sent, so a pause does not stop it
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

    def cancel_all(self, project_id: int, other: Optional["_Runner"] = None, actor: str = "user") -> Dict:
        """T3: see the module function cancel_all (this runner + optionally the other kind's runner)."""
        pair = {self.job_type: self}
        if other is not None:
            pair[other.job_type] = other
        return cancel_all(self.p, project_id, video=pair.get("video_gen"), image=pair.get("image_gen"), actor=actor)

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
        audio = bool(self._take_segments(job, rows)) if group else bool(self._lip_sync_audio_planned(job))
        problems = seedance_refs.lint_group(args[1], len(rows), len([f for f in frames if f]) + len(ids), len(rows) + len(ids), secs, audio,
                                            model=args[4])
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
        return lipsync.voiced(lipsync.method_for(data))

    def _group_secs(self, rows) -> list:
        """The seconds each shot of a reference send asks for (a group's floored cut seconds; a lone shot its motion seconds)."""
        from . import seedance_refs
        if len(rows) == 1:
            mp = self._motion(rows[0]["id"])
            sec = (mp["duration_sec"] if mp is not None else None) or rows[0]["data"].get("duration_s") or 0
            return [float(math.ceil(float(sec) - 1e-6))]
        return [seedance_refs.floored(r["data"], self._cut_seconds(r)) for r in rows]

    def _take_segments(self, job, rows) -> list:
        """S4.2 (feature dialogue_take, option (c) of the S4.6 A/B): the voiced lines of the "take" shots of this reference send, at
        their seconds of the WHOLE clip — shot start (the same whole-second marks / stretch as seedance_refs.prompt) + the line's
        offset inside the shot (lipsync.line_offsets, as voice.place_on_timeline lays it). [{speaker, text, file, start, end,
        scene_id, shot_start, offsets}]; [] when the feature is off or no line of a take shot is voiced yet."""
        from . import lipsync, seedance_refs
        if not lipsync.enabled() or not lipsync.take_on():
            return []
        secs = self._group_secs(rows)
        model = self._choice(job).get("model")
        total = sum(secs) or 1.0
        clip = seedance_refs.seconds(secs)
        stretched = [x * clip / total for x in secs] if clip > total else list(secs)
        if seedance_refs.reads_seconds(model):
            starts = [float(a) for a, _ in seedance_refs.whole_marks(stretched)]
        else:
            starts, t = [], 0.0
            for x in stretched:
                starts.append(round(t, 3))
                t += x
        out = []
        for r, st in zip(rows, starts):
            if lipsync.method_for(r["data"]) != "take":
                continue
            lines = lipsync.shot_lines(self.data_dir, job["project_id"], r["id"])
            offs = lipsync.line_offsets(lines)
            for e, o in zip(lines, offs):
                a = round(st + o, 3)
                out.append({"speaker": e.get("speaker") or "", "text": e.get("text") or "", "file": e["file"], "start": a,
                            "end": round(a + (e.get("duration_ms") or 0) / 1000.0, 3), "scene_id": r["id"], "shot_start": st,
                            "offsets": offs})
        return out

    def _take_audio(self, job, rows) -> Optional[str]:
        """The group's dialogue track (Audio1): every take line at its second of the clip, silence around, the clip's length. Each
        take shot is marked sent (lipsync index: its planned start in the clip — the cut may move it, see _take_done)."""
        from . import audio_lib, dialogue_take, ffmpeg_studio, lipsync, seedance_refs
        segs = self._take_segments(job, rows)
        if not segs:
            return None
        out = os.path.join(lipsync._dir(self.data_dir, job["project_id"]), f"take_{job['id']}.wav")
        try:
            dialogue_take.mix(segs, audio_lib.assets_dir(self.data_dir, job["project_id"]), out, ffmpeg_studio.find_ffmpeg(),
                              seconds=seedance_refs.seconds(self._group_secs(rows)))
        except Exception as e:  # noqa: BLE001
            self._diag(job, "warn", "lipsync_audio", f"không ghép được track thoại của nhóm ({e}) — clip gửi không kèm giọng")
            return None
        for sid in dict.fromkeys(x["scene_id"] for x in segs):
            first = next(x for x in segs if x["scene_id"] == sid)
            lipsync.mark(self.data_dir, job["project_id"], sid, state="generate_sent", job_id=job["id"], method="take",
                         planned_start=first["shot_start"], offsets=first["offsets"])
        return out

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
        skill = self._skill_assets(job)
        if skill:                            # S10.4: first frame (by role sentence) + one picture per person + the skill video(s)
            out["reference_only"] = [skill["first_frame"]] + [p["path"] for p in skill["pictures"]]
            hosted = self._hosted_pictures(job, [(f"P{job['project_id']}_S{job['scene_id']}_first", skill["first_frame"])]
                                           + [(f"P{job['project_id']}_{p['who']}_{p['kind']}", p["path"]) for p in skill["pictures"]],
                                           clean=True)
            if hosted:
                out["reference_only"] = hosted
            out["reference_video"] = [{"path": v, "refer_type": "feature"} for v in skill["videos"]]
            return out
        group = self._sends_group(job)
        if self._refs(job):                  # Seedance reference only (P2m): every picture marked, no start / last frame
            out["reference_only"] = self._reference_pictures(job, group or [])
            if not group:
                audio = self._lip_sync_audio(job)
                if audio:
                    out["reference_audio"] = [audio]
            else:
                track = self._take_audio(job, group)             # S4.2: the group's dialogue track (feature dialogue_take)
                if track:
                    out["reference_audio"] = [track]
                else:
                    self._no_lip_sync_note(job, "seedance", group)
            return out
        if group and mode != "multishot":
            pass                         # H5 camera set-up: one continuous prompt (in the motion argument), no multi_prompt
        elif group:
            out["multi_prompt"] = [{"prompt": self._motion(r["id"])["motion_prompt"], "duration": shots.billed_shot_seconds(r["data"])}
                                   for r in group]
            from .adapters.clipai import KLING_SHOT_PROMPT_LIMIT
            from . import speaker_lint                 # S0.14 T2: each shot of the group names who speaks in it
            for r, m in zip(group, out["multi_prompt"]):
                res = speaker_lint.apply(m["prompt"], [r["data"]], KLING_SHOT_PROMPT_LIMIT)
                if res["missing"]:
                    m["prompt"] = res["prompt"]
                    self._diag(job, "warn", "speaker_unnamed", speaker_lint.message(f"S{r['idx']:02d}", res))
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
        if lipsync.voiced(lipsync.method_for(data)):
            self._diag(job, "warn", "lipsync_not_applied", f"shot cần khớp môi (tạo kèm giọng) nhưng gửi bằng {model or '?'}"
                       + (" trong clip chung của nhóm" if group else "") + " — clip giữ miệng của model, không khớp giọng")

    def _skill_hits(self, job) -> list:
        """S10.4: the skills of a shot routed to the skill-video way (model_router gave `skill`), else []."""
        if not self._choice(job).get("skill"):
            return []
        from . import skill_dossier
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
        return skill_dossier.shot_skills(data)

    def _skill_assets(self, job) -> Optional[Dict]:
        """{first_frame, people: [(name, path)], videos: [path]} of a skill shot: the approved picture of the shot as the first frame, one
        identity picture per person, one cut of the official skill video per skill — None when the first frame is missing (said)."""
        from . import seedance_refs, shots, skill_dossier
        hits = self._skill_hits(job)
        if not hits:
            return None
        conn = self.p.conn
        first = shots.approved_image_path(conn, self.data_dir, job["project_id"], job["scene_id"])
        if not first:
            self._diag(job, "error", "missing_input", "shot kỹ năng chưa có ảnh khung đầu đã duyệt — không gửi")
            return None
        rows = [{"id": job["scene_id"], "data": json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],))
                                                          .fetchone()["data"] or "{}")}]
        people = seedance_refs.identity_pictures(conn, job["project_id"], rows, 8)
        have = {skill_dossier._key(n) for n, _ in people}
        from . import assets
        links = assets.link_characters(conn, job["project_id"], [n for n, _ in people])
        pictures = []                                  # 30/09: front + turnaround sheet per person, clean skill sheet per skill
        for n, path in people:
            a = links.get(n)
            std = dict((role, img) for img, role in (assets.standard_set(a, True) if a else []))
            front = (std.get("character") or {}).get("path") or path
            pictures.append({"kind": "front", "who": n, "path": front})
            sheet = (std.get("sheet") or {}).get("path")
            if sheet and os.path.exists(sheet):
                pictures.append({"kind": "sheet", "who": n, "path": sheet})
        for h in hits:
            ss = skill_dossier.skill_sheet(h)
            if ss:
                pictures.append({"kind": "skill_sheet", "who": h["dossier"]["character"], "path": ss})
        for h in hits:                                # luật 1: a skill user without an identity picture is said, not skipped
            who = h["dossier"]["character"]
            if skill_dossier._key(who) not in have and who in [str(c) for c in rows[0]["data"].get("characters") or []]:
                self._diag(job, "warn", "missing_reference", f"shot kỹ năng: {who} chưa có ảnh định danh trong dự án (gắn tài nguyên ở Bước 1) — "
                           "clip chỉ giữ người này nhờ khung đầu")
        return {"first_frame": first, "people": people, "pictures": pictures, "videos": [skill_dossier.video_ref(h) for h in hits],
                "hits": hits}

    def _refs(self, job) -> bool:
        if self._skill_hits(job):                     # a skill shot goes its own way (S10.4), never in a reference group
            return False
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
        labels = [f"P{job['project_id']}_S{r['id']}_frame" for r, f in zip(rows, frames) if f]
        frames = [f for f in frames if f]
        ids = seedance_refs.identity_pictures(conn, job["project_id"], rows, seedance_refs.MAX_PICTURES - len(frames))
        hosted = self._hosted_pictures(job, list(zip(labels, frames))
                                       + [(f"P{job['project_id']}_{n}", path) for n, path in ids], clean=True)
        if hosted:
            return hosted
        out_dir = os.path.join(self.data_dir, str(job["project_id"]), "refs_marked")
        return [seedance_refs.mark(p, out_dir) for p in frames + [path for _, path in ids]]

    subject_library = None          # S4.7: the Seedance Subject Library (tests set a double; else core.adapters.factory's)

    def _hosted_pictures(self, job, pictures, clean: bool = False) -> Optional[list]:
        """S4.7 (flag seedance_subjects): [(label, local picture)] → [{"uri": "asset://…"}] in the same order — each picture uploaded to
        the ClipAI Subject Library once (by its bytes, core.subjects.ensure_picture) and sent reviewed, so no red mark is needed. None
        when the flag is off, the provider is not ClipAI, or ANY picture has no active asset (said; the caller sends as before).
        clean: send an unmarked copy at most 1280 px (seedance_refs.mark style "none") — what the marked way would have resized too."""
        from . import features, seedance_refs
        if not features.on("seedance_subjects") or not pictures or not getattr(self.provider, "supports_subjects", False):
            return None
        lib = self.subject_library
        if lib is None:
            from .adapters import factory
            try:
                lib = factory.subject_library()
            except ProviderError as e:
                self._diag(job, "warn", "subjects", f"không mở được Kho chủ thể ({e}) — gửi ảnh như cũ")
                return None
        if lib is None:
            self._diag(job, "warn", "subjects", "cờ seedance_subjects bật nhưng chưa có Kho chủ thể (SUBJECT_PROVIDER) — gửi ảnh như cũ")
            return None
        if clean:
            out_dir = os.path.join(self.data_dir, str(job["project_id"]), "refs_clean")
            pictures = [(label, seedance_refs.mark(path, out_dir, style="none")) for label, path in pictures]
        res = subject_links.picture_refs(self.p.conn, lib, pictures)
        if not res["refs"]:
            self._diag(job, "warn", "subjects", "Kho chủ thể chưa nhận đủ ảnh — gửi ảnh như cũ (đánh dấu): " + "; ".join(res["problems"]))
            return None
        new = sum(1 for r in res["refs"] if r["uploaded"])
        self._diag(job, "info", "subjects", f"gửi {len(res['refs'])} ảnh qua Kho chủ thể (tải mới {new}, dùng lại {len(res['refs']) - new})")
        return [{"uri": r["uri"]} for r in res["refs"]]

    def _lip_sync_audio(self, job) -> Optional[str]:
        """The shot's voice line file for a "generate" lip-sync shot (feature lip_sync), else None. Missing voice: said, not guessed."""
        from . import ffmpeg_studio, lipsync
        if not lipsync.enabled():
            return None
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
        if not lipsync.voiced(lipsync.method_for(data)):
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
        if len(group) < 2 or self._skill_hits(job):                    # S10.4: a skill shot is sent on its own
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
        stretch = self._stretch(group) if group and exact and not refs else None
        if stretch and sent:                   # S3.4: where each shot sits in the whole-stretch take (the cut is made there)
            for g in sent:
                g["offset"] = stretch["offsets"].get(g["id"])
        proj = self.p.project(job["project_id"])
        audio = bool(proj["video_audio"]) if "video_audio" in proj.keys() else False
        return {"input_hash": lineage.video_input_hash(mp, formats.project_aspect(proj), args[4], audio) if mp else None,   # M16
                "source_job_id": lineage.approved_image_id(self.p.conn, shots.image_scene(self.p.conn, job["scene_id"])),
                "model": args[4],
                "sent_group": json.dumps(sent) if sent else None}

    def _stretch(self, group) -> Optional[Dict]:
        """S3.4 (feature continuous_takes): the whole stretch a camera set-up films, or None (feature off / too long / not a set-up)."""
        from . import features, shots
        if not group or not features.on("continuous_takes") or self._refs_group(group):
            return None
        return shots.stretch_of(self.p.conn, group, self._cut_seconds)

    def _refs_group(self, group) -> bool:
        from . import seedance_refs
        return any(seedance_refs.uses_refs(self.p.conn, r["id"]) for r in group)

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
                stretch = self._stretch(group)
                if stretch:                                         # S3.4: this camera films the whole stretch of acting
                    duration = max(math.ceil(sum(stretch["seconds"]) - 1e-6), 3)
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
            segs = self._take_segments(job, rows)
            if segs:                                   # S4.2: who says which line at which second (the lines stay in Vietnamese)
                from . import dialogue_take
                motion += "\n" + dialogue_take.group_block(segs, [n for n, _ in ids])
        stretch = self._stretch(group) if setup else None
        if stretch:
            motion = no_minor_age(shots.stretch_motion(stretch, [r["id"] for r in group], str(group[0]["data"].get("shot") or "")))
        elif setup:
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
        lock = looks.video_sentence(proj)                       # S4.3: the look in every video prompt (#8: an anime close-up)
        if lock and lock not in motion:
            motion = f"{lock} {motion}"
        motion = self._speakers_named(job, model, motion, group, setup)
        negative = mp["negative_prompt"]
        from . import skill_dossier
        skill = self._skill_assets(job)
        if skill:                                     # S10.4: the official template — roles first, the effect NOT described again
            motion = skill_dossier.reference_block(skill["hits"], skill["pictures"]) + "\n[Event] " + motion
        elif skill_dossier.enabled():                 # 30/09: the skill phase in the clip's words + what is never drawn
            hit = skill_dossier.shot_skill(json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],))
                                                      .fetchone()["data"] or "{}"))
            if hit and hit["phase"]["video_en"] not in motion:
                motion = motion.rstrip() + skill_dossier.video_sentence(hit)
            negative = skill_dossier.video_negative(hit, negative)
        args = (path, motion, looks.video_negative(proj, negative), duration, model)
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
        if skill:            # S10.4: the skill way sends its pictures / videos as keyword arguments (_submit_kwargs) — not twice
            subj_refs, image_refs, ref_video = [], [], None
        if proj["video_audio"] or subj_refs or image_refs or ref_video:  # extra args only when used: older providers keep working
            args += (bool(proj["video_audio"]), subj_refs or None, image_refs or None, ref_video)
        return args

    def _speakers_named(self, job, model, motion: str, group, setup: bool) -> str:
        """S0.14 T2: a Kling clip whose prompt does not name who speaks → said in diag; with `speaker_tags` on, the sentence is added.
        A Kling multi-shot group is checked shot by shot in _submit_kwargs (its shots go in multi_prompt)."""
        from . import speaker_lint
        if not speaker_lint.is_kling(model) or (group and not setup):
            return motion
        if setup and group:
            rows = [r["data"] for r in group]
        else:
            row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
            rows = [json.loads((row["data"] if row else None) or "{}")]
        from .adapters.clipai import PROMPT_LIMITS
        res = speaker_lint.apply(motion, rows, PROMPT_LIMITS["kling"])
        if res["missing"]:
            self._diag(job, "warn", "speaker_unnamed", speaker_lint.message("clip", res))
        return res["prompt"]

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
        """S14.16 (core.money_policy): a real stop only (the service is out of credit); the trial / project amounts, a clip without
        a price (estimated high) and a broken price table WARN — said in diag, the clip is sent."""
        from . import spend_gate
        try:
            usage = self._usage(args, kwargs)
        except ProviderError as e:                       # e.g. a model the provider does not know: nothing to price, nothing sent
            return f"không tính được giá clip ({e})"
        model, tier, seconds = usage if usage else (None, None, 0)
        stop, warns, _est = spend_gate.assess(self.p.conn, "video", self.provider.name, job["project_id"], model, tier, seconds or 5,
                                              "videos")
        if not stop:
            spend_gate.warn(self.p.conn, warns, stage="video", project_id=job["project_id"], **_job_ids(job))
        return stop

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
                   "data": {"duration_s": g["duration_s"], "exact": bool(g.get("exact")), "offset": g.get("offset")}} for g in sent]
                 if sent
                 else self._sends_group(job))       # M10: the group as it was sent (a later re-plan must not mis-cut a paid clip)
        if group:
            self._finish_group(job, path, group)
            self._clean_edges(job, path)
        try:
            if group or not self._refs(job):   # 28/09: a lone Seedance shot's prompt spreads the action over the whole clip (>= 4 s) —
                shots.trim_clip(self.p, job["scene_id"], path)   # cut to its 1-2 s plan, S5·1 lost the fall: kept whole instead
            else:                              # S2.5 (cờ motion_trim): cut at its busiest window, never under the action's floor
                shots.trim_clip(self.p, job["scene_id"], path, lone_ref=True)
        except Exception as e:  # noqa: BLE001 - a clip that cannot be cut is still a usable (longer) clip
            self._diag(job, "warn", "trim_error", f"không cắt được clip theo độ dài shot ({type(e).__name__}: {e}); dùng nguyên clip")
        if not group:
            from . import lipsync
            rec = lipsync.index(self.data_dir, job["project_id"]).get(str(job["scene_id"])) or {}
            if rec.get("state") == "generate_sent" and rec.get("job_id") == job["id"]:
                lipsync.mark(self.data_dir, job["project_id"], job["scene_id"], state="done")
        return path

    def _clean_edges(self, job, path: str) -> None:
        """S4.5: a shot cut from a group clip loses the neighbouring shot's frames left at its edges — said, never silent."""
        from . import shots
        done = shots.clean_edges(path)
        if done:
            self._diag(job, "info", "stray_edges", f"bỏ khung của shot kề lẫn ở mép clip: đầu {done['head']} s, cuối {done['tail']} s "
                                                   "(điểm cắt clip nhóm lệch) — bản chưa bỏ lưu ở _edges.mp4")
            if done["head"] > 0:
                self._take_edge_shift(job, float(done["head"]))

    def _take_edge_shift(self, job, head: float) -> None:
        """S4.2 (01/10): dropping `head` seconds at the start of a take shot's clip moves its mouths `head` seconds earlier — the shift
        that voice.place_on_timeline uses grows by as much, or the voice lands late on the mouth."""
        from . import lipsync
        leader = job["group_leader"] if "group_leader" in job.keys() and job["group_leader"] else job["id"]
        rec = lipsync.index(self.data_dir, job["project_id"]).get(str(job["scene_id"])) or {}
        if rec.get("method") == "take" and rec.get("state") == "done" and rec.get("job_id") == leader:
            lipsync.mark(self.data_dir, job["project_id"], job["scene_id"], shift=round(float(rec.get("shift") or 0) + head, 3),
                         edge_head=round(head, 3))

    def _take_done(self, leader, group, starts) -> None:
        """S4.2: each take shot of this group clip is lip-synced; `shift` = where its part really starts in the clip minus where the
        dialogue track put it — voice.place_on_timeline moves its lines by that much so the voice stays on the mouth."""
        from . import lipsync
        idx = lipsync.index(self.data_dir, leader["project_id"])
        for r, st in zip(group, starts):
            rec = idx.get(str(r["id"])) or {}
            if rec.get("method") == "take" and rec.get("state") == "generate_sent" and rec.get("job_id") == leader["id"]:
                lipsync.mark(self.data_dir, leader["project_id"], r["id"], state="done",
                             shift=round(float(st) - float(rec.get("planned_start") or 0), 3))

    def _finish_group(self, leader, path: str, group) -> None:
        from . import formats, lineage, shots
        conn = self.p.conn
        dests = [path] + [os.path.join(self._dir(leader["project_id"], "videos"), f"{r['idx']:02d}.mp4") for r in group[1:]]
        if group[0].get("refs"):
            from . import seedance_refs
            res = seedance_refs.split(path, group, dests)
            self._take_done(leader, group, [0.0] + list(res["cuts"]))
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
            self._running(jid, f"phần của clip nhóm (job {leader['id']})")   # T2: one transaction with the leader's task id (paid once)
            self._clean_edges(self.p.job(jid), dest)
            try:
                shots.trim_clip(self.p, r["id"], dest)
            except Exception as e:  # noqa: BLE001
                self._diag(self.p.job(jid), "warn", "trim_error", f"không cắt được clip theo độ dài shot: {e}")
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, jid))
            conn.commit()
            self.p.succeed(jid)


NO_CANCEL_API = ("deepix",)
NO_CANCEL_NOTE = "Deepix không có lệnh hủy: đã bỏ khỏi hàng đợi phía mình; ảnh đã gửi vẫn tính tiền"
CANCEL_WAIT_S = 20.0                 # cancel_all waits this long for the project's send/poll turn, then says "busy"          # providers with no cancel endpoint (core/adapters/deepix.py: cancel() does nothing)


def cancel_all(p: Pipeline, project_id: int, video: Optional[_Runner] = None, image: Optional[_Runner] = None,
               actor: str = "user", wait: Optional[float] = None) -> Dict:
    """T3 (S14.3 B1a): the project's ■ Hủy / delete-project stop. Before: only Pipeline.cancel_all_active — the jobs were cancelled
    on our side while the providers kept generating (and billing) every running task.

    1. the right to edit is checked FIRST (a viewer must not reach the provider before being refused);
    2. the project's send/poll turn of both kinds is held, so no send is in flight while we cancel — waited for at most `wait`
       seconds; still busy (a long download / composite) → nothing is cancelled, {"busy": True} (never half a cancel);
    3. every running job — and every queued one that already has a task (old data) — with a task is cancelled at its provider — once per task (a multi-shot group shares one task), each call in
       its own try/except (one error never stops the rest, it is reported); Deepix has no cancel API: those pictures are only dropped
       from our queue and are still billed; a kind with no configured service (`video`/`image` None) is reported, not skipped silently;
    4. then Pipeline.cancel_all_active.
    Returns {"cancelled", "at_provider", "failed": [(task, error)], "no_cancel_api", "no_provider"}; cancel_note() words it."""
    from . import access
    access.need_edit(p, project_id, "hủy việc đang chạy")
    runners = {"video_gen": video, "image_gen": image}
    locks = [_turn(project_id, kind) for kind in ("image_gen", "video_gen")]          # one fixed order: never two orders, never a deadlock
    held = []
    for lock in locks:
        if not lock.acquire(timeout=CANCEL_WAIT_S if wait is None else wait):
            for h in reversed(held):
                h.release()
            return {"busy": True, "cancelled": 0, "at_provider": 0, "failed": [], "no_cancel_api": 0, "no_provider": 0}
        held.append(lock)
    try:
        report = {"busy": False, "cancelled": 0, "at_provider": 0, "failed": [], "no_cancel_api": 0, "no_provider": 0}
        done = set()
        rows = p.conn.execute("SELECT * FROM jobs WHERE project_id=? AND state IN ('running','queued') AND external_id IS NOT NULL ORDER BY id",
                              (project_id,)).fetchall()
        for job in rows:
            key = (job["type"], job["external_id"])
            if key in done:
                continue                    # the same task (multi-shot followers carry the leader's): one cancel call
            done.add(key)
            r = runners.get(job["type"])
            if r is None:
                report["no_provider"] += 1
                continue
            if str(getattr(r.provider, "name", "")).startswith(NO_CANCEL_API):
                report["no_cancel_api"] += 1
                continue
            try:
                r.provider.cancel(job["external_id"])
                report["at_provider"] += 1
            except Exception as e:  # noqa: BLE001 - one provider error must not leave the other tasks running; it is reported
                report["failed"].append((job["external_id"], f"{type(e).__name__}: {e}"))
                diag.record(p.conn, "image" if job["type"] == "image_gen" else "video", "error",
                            f"không hủy được task {job['external_id']} ở nhà cung cấp ({type(e).__name__}: {e}) — job vẫn bị hủy phía "
                            "mình; kiểm tra / hủy trên web nhà cung cấp", "cancel_failed", project_id, job["scene_id"], job["id"])
        report["cancelled"] = p.cancel_all_active(project_id, actor=actor)
        return report
    finally:
        for lock in reversed(locks):
            lock.release()


def cancel_note(report: Dict) -> str:
    """The person-facing sentence for cancel_all (toast). No refund is promised: ClipAI's refund policy is not verified."""
    if report.get("busy"):
        return ("Chưa hủy gì: dự án đang bận tải/ghép clip — thử lại sau ít phút. (Không hủy dở: việc ở nhà cung cấp và ở đây "
                "đều giữ nguyên.)")
    parts = [f"Đã hủy {report['cancelled']} việc."]
    if report["at_provider"]:
        parts.append(f"Đã yêu cầu nhà cung cấp dừng {report['at_provider']} task đang gen.")
    if report["no_cancel_api"]:
        parts.append(NO_CANCEL_NOTE.replace("đã bỏ", f"{report['no_cancel_api']} ảnh đã bỏ") + ".")
    if report["failed"]:
        parts.append(f"KHÔNG hủy được {len(report['failed'])} task ở nhà cung cấp ("
                     + ", ".join(t for t, _ in report["failed"][:5]) + ") — kiểm tra / hủy trên web nhà cung cấp.")
    if report["no_provider"]:
        parts.append(f"{report['no_provider']} task chưa hủy ở nhà cung cấp (dịch vụ chưa cấu hình ở máy này) — hủy trên web nhà cung cấp.")
    return " ".join(parts)


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


def chain_previous(proj, scene_data) -> bool:
    """Send the previous approved frame as an extra reference? storyboard_mode 1 = always; 0 (default) / 2 = never. S14.9 (06/10):
    the automatic chaining inside a sequence (flag chain_previous_auto, GĐ6 F8/I2: a close-up dragged in the wide frame's layout)
    was removed — `scene_data` is kept for the callers."""
    return (proj["storyboard_mode"] or 0) == 1


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
    for r in conn.execute("SELECT name, lock_rules, outfit_image_ids FROM characters WHERE project_id=?", (project_id,)):
        if r["name"] not in (cast or []):
            continue
        if (r["outfit_image_ids"] or "").strip():
            # 07/10 Khủng Long Đỏ: MAXIM KL's lock came from the library profile of MAXIM with his everyday clothes ("black baseball cap
            # worn backwards, bomber jacket") and the costume's red horned cap was drawn as the black cap — face/hair/build only here
            parts.append(f"{r['name']}: keep the face, hair and body build of the reference pictures; the clothes, cap and accessories "
                         "come ONLY from the OUTFIT image, never from the everyday look")
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
    peak = str(data.get("action_peak") or "").strip().rstrip(".")
    if peak:                                        # S3.3: an action shot starts mid-movement, not from a standing pose (#8: fake running)
        prompt += f" The first frame catches the action already under way: {peak}; mid-motion, not a standing pose."
    prompt += lock_note(conn, project_id, data.get("characters"))
    prompt += view_notes(conn, project_id, data)
    prompt += looks.image_sentence(proj)
    from . import skill_dossier
    if skill_dossier.enabled():                   # 30/09: the skill phase as the official video shows it + what is never drawn
        prompt += skill_dossier.image_sentence(skill_dossier.shot_skill(data))
    if fix:
        prompt = f"{prompt}. Fix: {fix}"
    place = assets.scene_location(conn, project_id, data)
    room = indoor_spot(conn, project_id, data)
    if room:                                       # 07/10 Khủng Long Đỏ: the place's outdoor words ("plaza, palms, sea") pulled a
        prompt += (f" Setting: INSIDE a room — {room} ({place['name']} map). An interior with walls and ceiling as in the 3D render; "
                   "no plaza, tower, sky or sea except what its windows show.")   # bedroom shot outside onto a balcony
    elif place is not None:                        # B1: the place in words (+ real landmark heights), whatever pictures go
        prompt += " " + assets.location_text(conn, place)
    return no_minor_age(prompt), removed


def indoor_spot(conn, project_id: int, data: Dict) -> Optional[str]:
    """The label of the shot's 3D spot when it is an indoor one (place_render_refs), else None."""
    from . import location_pack, place_refs
    if not place_refs.enabled():
        return None
    place = assets.scene_location(conn, project_id, data)
    entry = location_pack.model3d(conn, place["id"]) if place is not None else None
    if not entry:
        return None
    sp = location_pack.spot_for(entry, data)
    return (sp.get("label") or sp.get("name") or "indoor room") if sp.get("indoor") else None


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


def location_pack_entry(conn, place) -> Optional[Dict]:
    from . import location_pack
    return location_pack.model3d(conn, place["id"]) if place else None


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

    def _blocked(self, job) -> Optional[str]:
        """S5.2: a picture of a place the library describes, but the project does not resolve it — held before paying (the layout
        sentence would be missing: #8's tower came out as stacked terraces)."""
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
        if row is None:
            return None
        return assets.missing_layout(self.p.conn, job["project_id"], json.loads(row["data"] or "{}"))

    def _over_budget(self, job, args, kwargs) -> Optional[str]:
        model = (kwargs or {}).get("model")
        info = getattr(self.provider, "usage_info", None)
        if model is None and info is not None:
            try:
                model = info()[0]
            except Exception:  # noqa: BLE001 - a provider without a model name: estimated high as unknown (a warning, S14.16)
                model = None
        from . import spend_gate                 # S14.16: only a service out of credit stops; the caps / a missing price warn
        stop, warns, _est = spend_gate.assess(self.p.conn, "image", self.provider.name, job["project_id"], model, None, 1, "images")
        if not stop:
            spend_gate.warn(self.p.conn, warns, stage="image", project_id=job["project_id"], **_job_ids(job))
        return stop

    def _wait(self, job) -> bool:
        """v3: the picture of a shot that continues the previous one waits for that shot's approved picture (sent as reference —
        storyboard_mode 1 only since S14.9)."""
        from . import shots
        from . import scene_storyboard
        from . import scene_establish
        from . import place_refs
        if place_refs.enabled():                             # place_render_refs: the 3D renders of the shot's scene come first (0 USD)
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            rows = scene_establish.scene_rows(self.p.conn, job["project_id"], data.get("story_scene")) if data.get("story_scene") is not None                 else [{"id": job["scene_id"], "data": data}]
            if any(place_refs.missing(self.p.conn, self.data_dir, job["project_id"], r["id"], r["data"]) for r in rows):
                place_refs.ensure_async(self.p.conn, job["project_id"], self.data_dir, place_refs.resolution_of(self.p.project(job["project_id"])),
                                        log=lambda m: self._diag(job, "info", "place_render", m))
                return True
            held = place_refs.needs(self.data_dir, job["project_id"], job["scene_id"])
            if held:                                         # S5.7: no direction for a script-direction spot — wait, and say what to add
                self._diag(job, "error", "plate_view", held)
                return True
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
        proj = self.p.project(job["project_id"])
        chains = proj["storyboard_mode"] == 1
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
        prompt, _ = build_image_prompt(conn, job["project_id"], data, fix=model_fix(job["retry_reason"]))
        from . import scene_establish
        light = scene_establish.light_sentence(data)
        if light:
            prompt = f"{prompt} {light}"
        from . import location_pack
        chosen = location_pack.script_sentence(conn, job["project_id"], data)   # S5.7: direction + extra lights of this shot
        if chosen:
            prompt = f"{prompt} {chosen}"
        proj = self.p.project(job["project_id"])
        chain = chain_previous(proj, data)
        from . import image_models
        model = image_models.of_project(proj)
        sheets = image_models.accepts_sheets(model) and getattr(self.provider, "supports_model", False)
        limit = min(image_models.max_refs(model, assets.MAX_REFERENCES), 12) if sheets else assets.MAX_REFERENCES
        refs = assets.scene_references(conn, job["project_id"], data,   # the previous frame keeps its slot
                                       limit=limit, reserve=1 if chain else 0, sheets=sheets)
        from . import scene_establish
        est = scene_establish.reference(self.data_dir, job["project_id"], data.get("story_scene"))
        if est and indoor_spot(conn, job["project_id"], data):   # an indoor shot: the 3D render of the room is the place, never the
            est = None                                           # outdoor wide picture of the scene (07/10 Khủng Long Đỏ)
        if est:                                        # the scene's wide establishing picture: the shared reference for the place
            refs = ([r for r in refs if r.get("role") != "location"][:max(limit - 2, 1)]
                    + [r for r in refs if r.get("role") == "location"][:1] + [est])
        from . import place_refs
        if place_refs.enabled():                       # the shot's own 3D render replaces the library's place picture + real numbers
            ref = place_refs.shot_ref(self.data_dir, job["project_id"], job["scene_id"])
            if ref is not None:
                refs = place_refs.swap_in(refs, ref, limit)
                place = assets.scene_location(conn, job["project_id"], data)
                entry = location_pack_entry(conn, place)
                geo = place_refs.geometry_sentence(ref["_rec"], data, (entry or {}).get("sun_azimuth", 250.0))
                if geo:
                    prompt = f"{prompt} {geo}"
                prompt = f"{place_refs.PRECEDENCE} {prompt}"   # S5.5' 30/09: words about the place lost to the render otherwise
        from . import skill_dossier
        if skill_dossier.enabled():                    # 30/09: the phase's real frame from the skill video (the dossier)
            for problem in skill_dossier.shot_problems(data):
                self._diag(job, "warn", "skill_contradiction", problem)
            refs = skill_dossier.add_reference(refs, skill_dossier.reference(skill_dossier.shot_skill(data)), limit)
        if chain and len(refs) < limit:
            # Deepix has no scriptable Storyboard (web UI only, see docs/CLIPAI_FEATURES.md) — this chains the
            # previous scene's approved picture in as an extra image-to-image reference instead, so style/lighting
            # carry over the way a real storyboard would.
            prev = previous_frame_job(conn, job["project_id"], scene["idx"], data.get("sequence"))
            if prev is not None:
                prev_path = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{prev['id']}.png")
                if os.path.exists(prev_path):
                    refs = refs + [{"path": prev_path, "label": "previous scene", "role": "previous_scene"}]
        return self._finish_args(job, prompt, refs)

    def _finish_args(self, job, prompt: str, refs):
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
        self._sent[job["id"]] = [{"label": r["label"], "role": r["role"], "file": os.path.basename(r["path"])} for r in refs]
        from . import scene_storyboard
        if scene_storyboard.enabled() and getattr(self.provider, "supports_storyboard", False):
            g = scene_storyboard.group_of(self.p.conn, job["project_id"], job["scene_id"])
            if g is not None:
                shared = scene_storyboard.shared_references(      # only this shot's people (S4.6 #10)
                    self.p.conn, job["project_id"], g["shots"],
                    cast_of=next(s["data"] for s in g["shots"] if s["id"] == job["scene_id"]))
                from . import scene_establish
                est = scene_establish.reference(self.data_dir, job["project_id"], g["story_scene"])
                own = next((s["data"] for s in g["shots"] if s["id"] == job["scene_id"]), {})
                if est and indoor_spot(self.p.conn, job["project_id"], own):   # indoor: the room render, not the outdoor wide picture
                    est = None
                if est:                                # the scene's wide establishing picture: the shared reference for the place
                    shared = ([r for r in shared if r.get("role") != "location"][:6]
                              + [r for r in shared if r.get("role") == "location"][:1] + [est])
                from . import place_refs
                if place_refs.enabled():                # this frame's own 3D render replaces the library's place picture
                    shared = place_refs.swap_in(shared, place_refs.shot_ref(self.data_dir, job["project_id"], job["scene_id"]), 8)
                from . import skill_dossier
                if skill_dossier.enabled():            # the skill frame of THIS shot rides with the shared references
                    row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
                    hit = skill_dossier.shot_skill(json.loads(row["data"] or "{}")) if row else None
                    shared = skill_dossier.add_reference(shared, skill_dossier.reference(hit), 8)
                shared, dropped = sendable_references(shared, model)     # before the mapping text is built from the list
                if dropped:
                    self._diag(job, "warn", "missing_reference", "ảnh tham chiếu storyboard không gửi được: " + ", ".join(dropped))
                previous = None
                srow = self.p.conn.execute("SELECT idx, data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
                sdata = json.loads(srow["data"] or "{}") if srow else {}
                if srow and chain_previous(proj, sdata):    # "always chain the previous shot" holds in storyboard mode too (07/10)
                    prev = previous_frame_job(self.p.conn, job["project_id"], srow["idx"], sdata.get("sequence"))
                    if prev is not None:
                        previous = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{prev['id']}.png")
                fields = scene_storyboard.job_fields(self.p.conn, self.data_dir, job["project_id"], job["scene_id"], shared, job["id"],
                                                     previous=previous)
                if fields is not None:
                    refs = fields["refs"]
                    prompt = prompt.rstrip() + fields.get("cast_note", "")
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
        """After the picture arrives: how well it kept the 3D render of the place (place_render_refs) and QC layer 0. S14.9: the
        location-pack green-screen composite (flag location_plates) was removed."""
        from . import place_refs
        if place_refs.enabled():                   # place_render_refs: did the model keep the place of the 3D render? (measured, said)
            ref = place_refs.shot_ref(self.data_dir, job["project_id"], job["scene_id"])
            if ref is not None:
                score = place_refs.background_match(path, ref["path"], ref["_rec"].get("subject_box"))
                sev, words = place_refs.match_note(score)
                self._diag(job, sev, "place_match", words)
        from . import qc_scene
        if qc_scene.enabled():                     # QC layer 0: code checks as the picture arrives (free)
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            flags = qc_scene.check_frame(path, data, assets.flat_place(self.p.conn, job["project_id"], data))
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
