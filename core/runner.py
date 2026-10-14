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
import shutil
import subprocess
import sqlite3
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

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

# Lỗi A (08/10, #24 job 578–584): why a queued job is held by _wait — {job_id: (Vietnamese reason, time)}. Written each time _wait holds a
# job, removed when it is sent. The step 2 screen says the real reason ("sẽ tự gửi khi …") instead of "bấm ▶ Gen ảnh"; core.bg_poll
# sends the job by itself once the reason is gone. Same process as the dashboard (the background round runs inside it).
WAIT_REASONS: Dict[int, Tuple[str, float]] = {}
# K3 rà: a job held by the check before gen (video_pregen ĐỎ) — {job id: (reason, when held)}. Module-level like WAIT_REASONS: the
# dashboard builds a NEW VideoRunner on every refresh, so per-runner memory (_diag_once) would let the hold note + the notes written while
# building the request (Kho chủ thể, bản cao, prompt cắt) repeat on every heartbeat. A held job is re-checked at most every
# PREGEN_RECHECK_S (a send asked for this very job — `only` — re-checks at once); its notes are written once per (job, code, text).
PREGEN_HELD: Dict[int, Tuple[str, float]] = {}
PREGEN_RECHECK_S = 30.0
_PREGEN_SAID: set = set()
_RENDER_RETRIED: Dict[Tuple[int, int], float] = {}   # (project, scene) whose missing 3D render a clip already had made again once
WAIT_FRESH_SEC = 300


def wait_reason(job_id: int) -> Optional[str]:
    """The reason _wait last gave for this queued job (None = none known in the last 5 minutes)."""
    hit = WAIT_REASONS.get(job_id)
    return hit[0] if hit and time.time() - hit[1] < WAIT_FRESH_SEC else None


HOLD_CODES = ("change_review_hold", "video_pregen_hold", "final_wait", "end_frame_wait", "video_gate_hold")
"""C7 (13/10): diag codes the video runner writes when it KEEPS a queued job (Tổ rà soát, kiểm trước gen ĐỎ, bản cao chờ)."""


def held_reason(conn, job_id: int) -> Optional[str]:
    """C7: why a QUEUED job is not sent — the runner's fresh reason (wait_reason), else the newest hold note it wrote in diag (survives
    a restart / another process). None = nothing known (it simply waits for its turn)."""
    why = wait_reason(job_id)
    if why:
        return why
    try:
        row = conn.execute("SELECT message FROM diag_events WHERE job_id=? AND code IN (%s) ORDER BY last_at DESC, id DESC LIMIT 1"
                           % ",".join("?" * len(HOLD_CODES)), (job_id, *HOLD_CODES)).fetchone()
    except Exception:  # noqa: BLE001 - an old database without diag: nothing known
        return None
    return f"(lần giữ gần nhất) {row['message']}" if row else None


class RedrawWithFix(Exception):
    """A downloaded result that must not be used (e.g. a location-pack picture drawn without the green backdrop): the job fails and a
    new try goes with `fix` (English, for the model)."""

    def __init__(self, message: str, fix: str):
        super().__init__(message)
        self.fix = fix


class UpgradeCutFailed(Exception):
    """A paid 1080p upgrade whose shot part could not be cut where the draft was cut: the job fails (red, diag final_cut) and is
    NOT retried — a retry pays again; the 1080p clip is kept as <idx>_group.mp4 for ✂ cắt tay (0 USD)."""


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


def _probe(path: str) -> Optional[float]:
    """Seconds of a local clip, None when unreadable (no ffprobe / not a media file)."""
    try:
        from .ffmpeg_studio import probe_duration
        got = probe_duration(path) if path and os.path.isfile(path) else None
        return float(got) if got else None
    except Exception:  # noqa: BLE001
        return None


def _span(part, edges, trim, whole, lone_ref: bool) -> Dict:
    """12/10 (#24): where a take's file was taken from its task's whole clip — {"start", "length" (None = to the end), "trim" (the
    start shots.trim_clip cut at, None = not trimmed), "lone_ref", "whole"}. A final upgraded from this take's task is cut the same way."""
    start, length = (float(part[0]), float(part[1])) if part else (0.0, None)
    if isinstance(edges, dict):
        head, tail = float(edges.get("head") or 0), float(edges.get("tail") or 0)
        start += head
        if length is not None:
            length -= head + tail
    return {"start": round(start, 3), "length": None if length is None else round(length, 3),
            "trim": round(float(trim["start"]), 3) if isinstance(trim, dict) and "start" in trim else None,
            "lone_ref": bool(lone_ref), "whole": round(float(whole), 3) if whole else None}


def _with_whole(span: Dict, measured: Optional[float]) -> Dict:
    """`span` with "whole" = the measured seconds of the task's whole clip; not measured → None (never guessed from the parts)."""
    return dict(span, whole=round(float(measured), 3) if measured else None)


def _copy_package(conn, source, job_id: int, new_ext: Optional[str] = None) -> None:
    """K1a: a job that holds a task it did not send itself (a multi-shot follower → its leader's request; a relinked job → the
    first send under the provider's real id) carries that request's sent_package. A ledger, never a gate: never raises."""
    try:
        row = conn.execute("SELECT sent_package, external_id FROM jobs WHERE id=?", (source["id"],)).fetchone()
        if row is None or not row["sent_package"]:
            return
        pkg = row["sent_package"]
        if new_ext is not None:
            data = json.loads(pkg)
            data["relinked_from"], data["external_id"] = data.get("external_id") or row["external_id"], str(new_ext)
            pkg = json.dumps(data, ensure_ascii=False)
        conn.execute("UPDATE jobs SET sent_package=? WHERE id=?", (pkg, job_id))
    except Exception:  # noqa: BLE001
        pass


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

    def _thread_diag(self, job, code: str, severity: str = "info"):
        """Lỗi 13 (08/10): a log called from ANOTHER thread (place_refs.ensure_async) cannot use this runner's connection ('SQLite objects
        created in a thread can only be used in that same thread' → the place_render notes were lost). Each message opens its own
        connection to the same database file; an in-memory database (tests) falls back to the runner's own one."""
        from .place_refs import _db_path
        kind = "image" if self.job_type == "image_gen" else "video"
        db = _db_path(self.p.conn)
        ids = (job["project_id"], job["scene_id"], job["id"])
        if not db:
            return lambda m: self._diag(job, severity, code, m)

        def log(message: str) -> None:
            c = None
            try:
                c = sqlite3.connect(db, timeout=60)
                c.row_factory = sqlite3.Row
                diag.record(c, kind, severity, message, code, *ids)
            except Exception as e:  # noqa: BLE001 - a note must never break the render thread; say it on stderr
                import sys
                print(f"[diag] place_render note lost: {e}: {message}", file=sys.stderr)
            finally:
                if c is not None:
                    c.close()
        return log

    # ---- hooks -----------------------------------------------------------
    def _submit_args(self, job) -> Optional[Tuple]:
        raise NotImplementedError

    def _submit_kwargs(self, job) -> Dict:
        """Extra keyword arguments (frame format, per-scene resolution) — only for providers that declare `supports_aspect`,
        so simpler providers (and test doubles) keep receiving the v1 call."""
        return {}

    def _hold_prefix(self, job, why: str) -> str:
        return "stale_input"

    def _draft_approved_at(self, job) -> Optional[str]:
        """C9: lúc NGƯỜI duyệt nháp mà job bản cao này nâng lên (None = không phải lệnh nâng từ nháp đã duyệt)."""
        return None

    def _gate_hold(self, job) -> Optional[str]:
        """V7: lý do GIỮ job trước khi gửi (cổng đầu vào), None = được gửi."""
        return None

    def _blocked(self, job) -> Optional[str]:
        """A reason not to send this job now (it would be made from outdated inputs); None = go."""
        return None

    def _rewrite_redraw(self, job, dest: str, e: "RedrawWithFix"):
        """Đợt C 09/10 (người dùng duyệt): vẽ lại tự động vì đo lớp 0 → Đạo diễn viết lại prompt của shot trước (cờ director_rewrite, như
        lần gen lại QC loại) thay vì chỉ nối câu "Fix" cuối prompt. Gọi khi take còn sống, kèm tệp lỗi (Claude xem); hết lượt tự gen lại
        thì không viết lại (không tốn tiền cho một take không làm). None = giữ cách cũ (câu sửa)."""
        from .pipeline import _combine_fix
        try:
            if self.p._retries_exhausted(self.p.job(job["id"])):
                return None
            self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, job["id"]))
            self.p.conn.commit()
            return self.p._rewrite_before_retry(self.p.job(job["id"]), _combine_fix(job["retry_reason"], e.fix), note=str(e),
                                                qc={"root_cause": "layer0", "problem": str(e), "fix": e.fix}, by="qc")
        except Exception as ex:  # noqa: BLE001 - the redraw still goes, with the old fix sentence (said)
            self._diag(job, "warn", "director_rewrite_fallback", f"không viết lại được prompt trước khi vẽ lại ({type(ex).__name__}: {ex})")
            return None

    def _wait(self, job) -> bool:
        """True = leave the job queued for now (not an error)."""
        return False

    def _stale_plates(self, job, rows) -> bool:
        """KLD-6 (08/10, #22: the hand redraw went out on the OLD render after a spot move — 1,80 USD): a shot of `rows` whose 3D
        render in plates/index.json is not the plan's any more is rendered again in the background (Blender, 0 USD) and the job
        waits — on every path (hand buttons, autopilot, picture and reference-only video). Said once per 10 minutes (diag)."""
        from . import place_refs
        pid = job["project_id"]
        res = place_refs.resolution_of(self.p.project(pid))
        stale = place_refs.stale(self.p.conn, self.data_dir, pid, res)
        if -1 in stale:
            self._diag(job, "warn", "plate_stale", stale[-1]["why"])
            return False
        hit = [(r["id"], stale[r["id"]]) for r in rows if r["id"] in stale]
        if not hit:
            return False
        for sid, item in hit:
            self._diag(job, "warn", "plate_stale", place_refs.stale_note(self.p.conn, self.data_dir, pid, res, sid, item))
        place_refs.ensure_async(self.p.conn, pid, self.data_dir, res, log=self._thread_diag(job, "place_render"))
        return True

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

    def _superseded(self, job) -> Optional[str]:
        """Why a finished take must not become the shot's file (video: a final of a draft that is no longer the approved one), or None."""
        return None

    # ---- shared ----------------------------------------------------------
    def _dir(self, project_id: int, kind: str) -> str:
        directory = os.path.join(self.data_dir, str(project_id), kind)
        os.makedirs(directory, exist_ok=True)
        return directory

    def _jobs(self, project_id: int, state: str):
        return self.p.conn.execute("SELECT * FROM jobs WHERE project_id=? AND type=? AND state=? ORDER BY id",
                                   (project_id, self.job_type, state)).fetchall()

    def _diag_once(self, job, severity: str, code: str, message: str) -> None:
        """A note written once per job (the prompt is built for the check before sending AND for the send — F1 sửa #11)."""
        said = self.__dict__.setdefault("_said_once", set())
        key = (job["id"], code, message)
        if key in said:
            return
        said.add(key)
        self._diag(job, severity, code, message)

    def _hold(self, job, reason: str) -> bool:
        """_wait holds this job: remember why (WAIT_REASONS, read by the screen) and return True."""
        WAIT_REASONS[job["id"]] = (reason, time.time())
        return True

    def submit_pending(self, project_id: int, only=None, wait_s: float = 0) -> int:
        """Send the project's queued jobs (those _wait does not hold). only = the job ids allowed (core.bg_poll: the person's jobs).
        wait_s (lỗi B 08/10): a person's click waits up to this long for the turn — the background round / the page's polling held it
        and the click used to return 0 silently, the jobs only queued."""
        lock = _turn(project_id, self.job_type)
        if not lock.acquire(blocking=wait_s > 0, timeout=wait_s if wait_s > 0 else -1):
            return 0                       # M3: another thread is sending this project's jobs right now
        from . import send_claim                  # hộp thư 12/10 19:58: one sender per job across PROCESSES too (cờ send_claim)
        outer = self.__dict__.get("_send_claims")
        self._send_claims = claims = {"owner": send_claim.new_owner(), "ids": []} if send_claim.enabled() else None
        try:
            sent = self._submit_pending(project_id, only)
        finally:
            self._send_claims = outer
            for jid in (claims or {}).get("ids", ()):
                send_claim.release(self.p.conn, jid, claims["owner"])
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

    def _submit_pending(self, project_id: int, only=None) -> int:
        if self.p.project(project_id)["paused"]:
            return 0
        slots = self.max_concurrent - len(self._jobs(project_id, "running"))
        submitted = 0
        for job in self._jobs(project_id, "queued"):
            if slots <= 0:
                break
            if only is not None and job["id"] not in only:
                continue
            if submitted and self.p.project(project_id)["paused"]:
                break               # T2: paused while this pass was sending — the jobs sent so far are running, send no more
            if self._wait(job):
                WAIT_REASONS.setdefault(job["id"], ("chờ điều kiện gửi (ảnh/clip đi trước, nhóm shot)", time.time()))
                continue            # v3: this job is sent later (after the previous shot's picture / with its multi-shot group)
            WAIT_REASONS.pop(job["id"], None)
            from . import send_claim                 # hộp thư 12/10 19:58: re-read + another process's claim, BEFORE any paid step
            fresh, note = send_claim.take(self.p.conn, job, getattr(self, "_send_claims", None))
            if fresh is None:
                if note:
                    self._diag_once(job, *note)
                continue
            job = fresh
            if job["external_id"]:
                # T2: its task already exists at the provider (a multi-shot follower given the leader's task, relink_failed, or a send
                # whose RUNNING step was lost) — sending it again would pay twice. It only moves to RUNNING; the next poll fetches it.
                # Checked BEFORE _blocked (rà soát B1a): stale inputs must not write off a task already paid for.
                stale = self._blocked(job)
                self._running(job["id"], "đã có task ở nhà cung cấp — không gửi lại")
                if stale:
                    from .prompt_formula import FORMULA_MARK    # F1 sửa #11: a formula stop is not an "outdated input"
                    what = stale if FORMULA_MARK in stale else f"đầu vào đã cũ ({stale})"
                    self._diag(job, "warn", "stale_paid", f"{what} — nhưng task {job['external_id']} đã trả tiền — lấy kết "
                                                          "quả về, không gửi lại")
                else:
                    self._diag(job, "info", "already_sent", f"job đã có task {job['external_id']} ở nhà cung cấp — chuyển sang đang chạy, "
                                                            "không gửi lại (tránh trả tiền 2 lần)")
                slots -= 1
                continue
            from . import change_review          # 10/10 Tổ rà soát tác động: mục đỏ còn mở → GIỮ chờ (sửa / bỏ qua thì tự gửi tiếp)
            held = None
            if job["scene_id"]:
                group = getattr(self, "_sends_group", lambda j: None)(job) or []
                since = self._draft_approved_at(job)     # C9: bản cao nâng từ nháp NGƯỜI đã duyệt — mục đỏ cũ / khâu ảnh không giữ
                passed: List[str] = []
                for sid in [job["scene_id"]] + [g["id"] for g in group if g["id"] != job["scene_id"]]:
                    held = change_review.blocking(self.p.conn, sid, self.data_dir, since=since, notes=passed)
                    if held:
                        break
                if not held and passed:
                    self._diag_once(job, "warn", "change_review_upgrade",
                                    "VÀNG: bản cao nâng từ nháp bạn đã duyệt — không giữ vì mục đỏ cũ hơn lúc duyệt / khâu nháp đã "
                                    "có: " + "; ".join(passed[:3]) + (f" (+{len(passed) - 3})" if len(passed) > 3 else ""))
            if held:
                WAIT_REASONS[job["id"]] = (held, time.time())
                self._diag_once(job, "warn", "change_review_hold", f"chưa gửi: {held}")
                continue
            gate = self._gate_hold(job)                  # V7: ảnh khung đầu chưa qua kiểm nền 3D / nhóm liền mạch chưa duyệt đủ ảnh
            if gate:
                WAIT_REASONS[job["id"]] = (gate, time.time())
                self._diag_once(job, "warn", "video_gate_hold", f"chưa gửi: {gate}")
                continue
            try:
                blocked = self._blocked(job)
            except (OSError, ValueError, ProviderError) as error:
                if self._pregen_prepare_error(job, error):
                    continue
                raise
            if blocked:
                prefix = self._hold_prefix(job, blocked)  # C3: a final waiting for the person is not an outdated input
                self._diag(job, "warn", prefix, f"không gửi: {blocked}")
                self._running(job["id"])                 # QUEUED→FAILED is not a transition (core/states.py): RUNNING, then fail
                self.p.fail(job["id"], f"{prefix}: {blocked}")
                continue
            try:
                args = self._submit_args(job)
            except (OSError, ValueError, ProviderError) as error:
                if self._pregen_prepare_error(job, error):
                    continue
                raise
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
            if only is None and self._pregen_cooling(job):
                continue            # K3 rà: held by the check before gen a moment ago — no rebuild of the request on every heartbeat
            try:
                kwargs = self._prepare_kwargs(job) if getattr(self.provider, "supports_aspect", False) else {}
            except (OSError, ValueError, ProviderError) as error:
                if self._pregen_prepare_error(job, error):
                    continue
                raise
            if kwargs.get("_wait"):                  # rà F3: a passing provider error — stays queued, said, not failed, not sent
                said = self.__dict__.setdefault("_final_waits", set())
                if job["id"] not in said:             # said once, not on every heartbeat
                    said.add(job["id"])
                    self._diag(job, "info", "final_wait", kwargs["_wait"])
                WAIT_REASONS[job["id"]] = (kwargs["_wait"], time.time())
                continue
            if kwargs.get("_hold"):                  # F3: the request may not go out unasked (a new paid final) — said, not sent
                prefix = self._hold_prefix(job, kwargs["_hold"])
                self._diag(job, "warn", prefix, f"không gửi: {kwargs['_hold']}")
                self._running(job["id"])
                self.p.fail(job["id"], f"{prefix}: {kwargs['_hold']}")
                continue
            if self._pregen(job, args, kwargs):      # K3 (cờ video_pregen): ĐỎ → giữ chờ người, các job khác vẫn gửi
                continue
            with budget.SPEND_LOCK:            # limit check + ledger entry as one step: two projects must not both pass the cap
                over = self._over_budget(job, args, kwargs)
                if over:
                    self._diag(job, "warn", "budget", over)
                    break                        # a real stop (S14.16: the service is out of credit): leave everything queued, say why
                try:
                    kwargs = self._finish_kwargs(job, kwargs)
                except (OSError, ValueError, ProviderError) as error:
                    if self._pregen_prepare_error(job, error):
                        continue
                    raise
                sent_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("_")}   # '_' keys: the runner's notes, never sent
                try:
                    if kwargs.get("_from_sample"):       # N1: a final made from its approved Seedance 2.5 draft (draft_task)
                        task_id = self.provider.submit_final_from_sample(kwargs["_from_sample"], resolution=kwargs.get("resolution"))
                    else:
                        task_id = self.provider.submit(*args, **sent_kwargs)
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
                # K1a: the package really sent, in the SAME transaction as the task id (before _stamp, which pops the runner's list
                # of sent pictures). Built (pictures hashed) and written BEFORE the task id: no file reading while the write lock is
                # held, and a package UPDATE that fails (even one SQLite answers with a rollback) cannot take the task id with it — the
                # task id UPDATE below always runs after. A ledger, never a gate: its warnings are said after the ledger entry.
                package_warns = self._write_sent_package(job, args, kwargs, sent_kwargs, task_id)
                self.p.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (task_id, job["id"]))
                for col, value in self._stamp(job, args).items():
                    self.p.conn.execute(f"UPDATE jobs SET {col}=? WHERE id=?", (value, job["id"]))
                try:
                    self._running(job["id"])
                except InvalidTransition as e:
                    self.p.conn.commit()                    # keep the task id: it is the only link to what may be billed
                    self._record_usage(job, args, kwargs)
                    self._say_package(job, package_warns)
                    self._cancelled_in_flight(job, task_id, e)
                    continue
                self._record_usage(job, args, kwargs)       # the spending ledger first: a failing package note never skips it
                self._say_package(job, package_warns)
            slots -= 1
            submitted += 1
        return submitted

    def _build_package(self, job, args, kwargs, sent_kwargs, task_id):
        """(JSON text of the package, warnings) for this send — one builder for the ledger (_write_sent_package) and the K3 check before
        gen (_pregen: the same package BEFORE the send, task_id None). Never raises (sent_package.safe_build)."""
        from . import sent_package
        kind = self.job_type.split("_")[0]
        if kwargs.get("_from_sample"):
            extra = sent_package.draft_of(self.p.conn, kwargs["_from_sample"])
            return sent_package.safe_build(
                self.provider.submit_final_from_sample, (kwargs["_from_sample"],), {"resolution": kwargs.get("resolution")},
                kind=kind, provider=self.provider, external_id=task_id, model=extra.pop("draft_model", None),
                call="submit_final_from_sample", extra=extra)
        return sent_package.safe_build(self.provider.submit, tuple(args), sent_kwargs, kind=kind, provider=self.provider,
                                       external_id=task_id, meta=getattr(self, "_sent", {}).get(job["id"]))

    def _prepare_kwargs(self, job):
        return self._submit_kwargs(job)

    def _finish_kwargs(self, job, kwargs):
        return kwargs

    def _pregen_prepare_error(self, job, error):
        return False

    def _pregen(self, job, args, kwargs) -> bool:
        """K3 (A17): code check of the request right before it is paid for; True = held (not sent). Only the video runner checks."""
        return False

    def _pregen_cooling(self, job) -> bool:
        """K3 rà: True = the job was held by _pregen less than PREGEN_RECHECK_S ago — stays queued with its reason, not re-checked yet."""
        return False

    def _write_sent_package(self, job, args, kwargs, sent_kwargs, task_id) -> List[str]:
        """K1a (core/sent_package.py): jobs.sent_package = what really left — the same args / kwargs the provider got. Never raises;
        returns the warnings (unreadable picture, package not written) for _say_package."""
        try:
            pkg, warns = self._build_package(job, args, kwargs, sent_kwargs, task_id)
            if pkg is not None:
                self.p.conn.execute("UPDATE jobs SET sent_package=? WHERE id=?", (pkg, job["id"]))
            return warns
        except Exception as e:  # noqa: BLE001 - a ledger, never a gate: the task exists, the send stands
            return [f"không ghi được gói gửi ({type(e).__name__}: {e}) — job vẫn gửi, sent_package để trống"]

    def _say_package(self, job, warns) -> None:
        for w in warns or []:
            try:
                self._diag(job, "warn", "sent_package", w)
            except Exception:  # noqa: BLE001 - a ledger note, never a gate: the send and its ledger entry stand
                pass

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
                    aside = self._superseded(job)
                    if self.job_type == "video_gen" and not aside:   # KLD-2 (08/10): the older take keeps its file (trash) + its result_path
                        from . import takes
                        takes.make_room(self.p.conn, self.data_dir, job, target)
                    else:
                        trash.move_to_trash(target, self.data_dir, job["project_id"], "images", "bị thay bằng bản gen lại", job["id"])
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
                    plan = self._rewrite_redraw(job, dest, e)
                    self.p.fail(job["id"], f"redraw: {e}")
                    counts["failed"] += 1
                    if self.p.retry(job["id"], str(e), fix=plan.apply() if plan is not None else e.fix) is not None:
                        counts["retried"] += 1
                    continue
                except UpgradeCutFailed as e:         # rà 12/10: said red in diag (final_cut); never retried (a retry pays again)
                    self.p.fail(job["id"], f"final_cut: {e}")
                    counts["failed"] += 1
                    continue
                self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, job["id"]))
                self.p.conn.commit()
                self.p.succeed(job["id"])
                if aside:                              # 13/10: paid for, kept aside under its own name, never the shot's take
                    self._diag(job, "warn", "superseded_final", f"bản cao xong nhưng {aside} — để riêng {os.path.basename(dest)}, "
                                                                "cho nghỉ (không thay clip của shot)")
                    from . import quality_tier
                    quality_tier.retire_superseded_finals(self.p, job["scene_id"])
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
        _copy_package(self.p.conn, job, new_id, new_ext)      # K1a: the same (one) send, now under the real task id
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


def draft_approved_at(conn, job) -> Optional[str]:
    """C9 (rà chuỗi 13/10): job video bản cao (quality_tier 'final') có nháp gốc NGƯỜI đã duyệt → giờ duyệt nháp đó (review_log);
    None = không phải lệnh nâng từ nháp đã duyệt. Dùng chung runner + autopilot (R10 rà S4: hai nơi quyết giống nhau)."""
    keys = job.keys()
    if "quality_tier" not in keys or job["quality_tier"] != "final" or "draft_job_id" not in keys or not job["draft_job_id"]:
        return None
    row = conn.execute("SELECT reviewer_type, decision, decided_at FROM review_log WHERE job_id=? ORDER BY id DESC LIMIT 1",
                       (job["draft_job_id"],)).fetchone()
    if row is None or row["reviewer_type"] != "user" or row["decision"] != "approve":
        return None
    return row["decided_at"]


class VideoRunner(_Runner):
    job_type = "video_gen"

    def _draft_approved_at(self, job) -> Optional[str]:
        return draft_approved_at(self.p.conn, job)

    def _gate_hold(self, job) -> Optional[str]:
        from . import video_gate
        if self._draft_approved_at(job):            # nâng từ nháp đã duyệt: ảnh đầu đã qua mắt người ở bản nháp
            return None
        return video_gate.hold(self.p.conn, self.data_dir, job)

    def _hold_prefix(self, job, why: str) -> str:
        """C3 (13/10): 'final_hold' for a final the runner keeps for the person ("bản cao bị chặn: cần xác nhận…" / nháp cũ) — the
        "↻ Xếp hàng lại từ đầu vào mới" button would turn it into a NEW paid draft; 'stale_input' otherwise (as before)."""
        from . import quality_tier
        if quality_tier.enabled() and str(why).startswith("bản cao bị chặn"):
            return quality_tier.hold_prefix(self.p.conn, job)
        return "stale_input"

    def _choice(self, job) -> Dict:
        from . import model_router
        return model_router.scene_choice(self.p.conn, job["scene_id"])

    def _blocked(self, job) -> Optional[str]:
        from . import lineage, quality_tier
        if quality_tier.enabled() and "quality_tier" in job.keys() and job["quality_tier"] == "final":
            gate = quality_tier.final_block(self.p.conn, job["scene_id"])   # N1: no final from an unapproved / outdated draft
            gate = gate or quality_tier.superseded_by(self.p.conn, job)    # 13/10: a final of an older draft — a newer one is approved
            if gate:
                return f"bản cao bị chặn: {gate}"
            if not job["external_id"]:          # F3 (#24): a final that cannot come from its draft is a NEW paid gen — never unasked
                route = quality_tier.final_route(self.p.conn, job, self.provider)
                self.__dict__.setdefault("_final_routes", {})[job["id"]] = route
                hold = quality_tier.needs_confirm(job, route)
                if hold:
                    return f"bản cao bị chặn: {hold}"
        # F1 sửa #4: a job that sends its group (Kling multi-shot / Seedance group / camera set-up) pays for every shot's prompt
        group = self._sends_group(job) or []
        ids = [r["id"] for r in group] if group else []
        ids = ids if job["scene_id"] in ids else [job["scene_id"]] + ids
        idx = {r["id"]: r.get("idx") if isinstance(r, dict) else r["idx"] for r in group}
        # rà F5 mục 3 (09/10): ô "sẵn sàng" báo đỏ "chưa có motion prompt" → chỗ gửi cũng chặn (CHUAN luật 1: không im lặng khi thiếu
        # đầu vào — một clip nhóm thiếu prompt của một shot vẫn trả tiền cả nhóm)
        empty = [sid for sid in ids if not ((self._motion(sid) or {"motion_prompt": ""})["motion_prompt"] or "").strip()]
        if empty:
            names = [f"S{idx[s]:02d}" if isinstance(idx.get(s), int) else f"shot #{s}" for s in empty]
            return "chưa có motion prompt (" + ", ".join(names) + ") — viết ở Bước 3 (Storyboard · tab Motion)"
        row = lineage.scan(self.p.conn, job["project_id"]).get(job["scene_id"]) or {}
        if row.get("motion_stale"):
            return f"motion prompt đang cũ ({row['motion_stale']}) — viết lại / duyệt lại ở Bước 3"
        from . import prompt_formula             # F1 (09/10): a motion prompt that breaks the formula is not paid for
        reds = []
        for sid in ids:
            red = prompt_formula.red_issues(self.p.conn, sid, "motion",
                                            gore_hinted=lambda sid=sid: self._gore_hinted(job, group, sid))
            if red and len(ids) > 1:
                n = idx.get(sid)
                red = [f"S{n:02d} {x}" if isinstance(n, int) else f"shot #{sid} {x}" for x in red]
            reds += red
        if reds:
            return "prompt sai công thức — sửa ở Bước 3: " + " · ".join(reds)
        if self._refs(job):
            return self._ref_lint(job)
        return None

    def _pregen(self, job, args, kwargs) -> bool:
        """K3 (A17, core/video_pregen.py, cờ video_pregen — tắt = y cũ): kiểm gói video TRƯỚC khi trả tiền. ĐỎ → không gửi: job ở lại hàng
        đợi chờ người (WAIT_REASONS, như Tổ rà soát giữ) + một dòng ⚙ Chẩn đoán; sửa đầu vào xong lượt gửi sau tự đi. VÀNG → gửi + ghi.
        Lớp kiểm hỏng → ĐỎ có lý do (không gửi khi chưa kiểm được). Chỉ giữ job này: vòng gửi đi tiếp sang job khác (lô / autopilot)."""
        from . import video_pregen
        if not video_pregen.enabled():
            PREGEN_HELD.pop(job["id"], None)
            self.__dict__.get("_pregen_fingerprints", {}).pop(job["id"], None)
            return False
        try:
            sent_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("_")}
            pkg, _ = self._build_package(job, args, kwargs, sent_kwargs, None)
            group = self._sends_group(job) or []
            plan = video_pregen.plan_of(job, args, kwargs, pkg, self.data_dir, [r["id"] for r in group])
            # pictures waiting to go through the Subject Library (sent as asset://, not measured by the adapter) — rà video #27 12/10
            plan["hosted_pending"] = [x for d in self.__dict__.get("_pregen_deferred", []) for x in d.get("local") or []]
            issues = video_pregen.check(self.p.conn, job["scene_id"], plan)
        except Exception as e:  # noqa: BLE001 - a check that cannot run must not let the money go (luật 1: không im lặng)
            issues = [{"ma": "loi_kiem", "muc": video_pregen.DO,
                       "ly_do": f"lớp kiểm trước gen lỗi ({type(e).__name__}: {e}) — chưa gửi khi chưa kiểm được"}]
        reds = [i for i in issues if i["muc"] == video_pregen.DO]
        for i in issues:
            if i["muc"] != video_pregen.DO:
                self._pregen_note(job, "video_pregen", f"kiểm trước gen (vàng, vẫn gửi): {i['ly_do']}")
        if not reds:
            PREGEN_HELD.pop(job["id"], None)
            self.__dict__.setdefault("_pregen_fingerprints", {})[job["id"]] = video_pregen.fingerprint(plan["package"])
            return False
        line = "kiểm trước gen chặn: " + video_pregen.summary(reds)
        now = time.time()
        WAIT_REASONS[job["id"]] = (line, now)
        PREGEN_HELD[job["id"]] = (line, now)
        self._pregen_note(job, "video_pregen_hold", f"chưa gửi — {line}")
        return True

    def _pregen_note(self, job, code: str, message: str) -> None:
        """One ⚙ Chẩn đoán line per (job, code, text) for the life of the process (not per runner object — see PREGEN_HELD)."""
        key = (job["id"], code, message)
        if key in _PREGEN_SAID:
            return
        if len(_PREGEN_SAID) > 5000:
            _PREGEN_SAID.clear()
        _PREGEN_SAID.add(key)
        super()._diag(job, "warn", code, message)

    def _prepare_kwargs(self, job):
        from . import video_pregen
        self._pregen_local = video_pregen.enabled()
        self._pregen_deferred = []
        try:
            return self._submit_kwargs(job)
        finally:
            self._pregen_local = False

    def _pregen_prepare_error(self, job, error):
        from . import video_pregen
        if not video_pregen.enabled():
            return False
        line = f"kiểm trước gen chặn: không chuẩn bị được tệp / tham chiếu ({type(error).__name__}: {error}) — chỉ giữ shot này"
        now = time.time()
        WAIT_REASONS[job["id"]] = PREGEN_HELD[job["id"]] = (line, now)
        self._pregen_note(job, "video_pregen_hold", f"chưa gửi — {line}")
        return True

    def _finish_kwargs(self, job, kwargs):
        from . import seedance_refs
        for pending in self.__dict__.get("_pregen_deferred", []):
            hosted = self._hosted_pictures(job, pending["pictures"], clean=pending["clean"])
            if hosted is None:
                hosted = [path for _, path in pending["pictures"]]
                if pending.get("mark_fallback"):
                    out_dir = os.path.join(self.data_dir, str(job["project_id"]), "refs_marked")
                    style = pending.get("mark_style") or seedance_refs.mark_style(self.p.conn, pending.get("scene_ids") or [])
                    hosted = [seedance_refs.mark(path, out_dir, style) for path in hosted]
                    if pending.get("scene_ids"):     # rà S2 13/10 mục 6: the style really sent, never an assumed "eye_plus"
                        seedance_refs.note_sent(self.p.conn, pending["scene_ids"], style)
                    source = pending.get("last_frame")
                    if source and kwargs.get("last_frame") and kwargs.get("_last_frame_source") == source:
                        kwargs["last_frame"] = seedance_refs.mark(source, out_dir, style)   # V5: the drawn end frame (an unmarked
                        #                                     copy for the library) marked like the rest of this send
            elif pending.get("scene_ids"):
                seedance_refs.note_sent(self.p.conn, pending["scene_ids"], "hosted")
            pending["local"][:] = hosted
        self._pregen_deferred = []
        return kwargs

    def _build_package(self, job, args, kwargs, sent_kwargs, task_id):
        pkg, warns = super()._build_package(job, args, kwargs, sent_kwargs, task_id)
        fingerprint = self.__dict__.get("_pregen_fingerprints", {}).get(job["id"])
        if pkg and task_id is not None and fingerprint:
            body = json.loads(pkg)
            body["pregen_fingerprint"] = fingerprint
            pkg = json.dumps(body, ensure_ascii=False)
        return pkg, warns

    def _pregen_cooling(self, job) -> bool:
        from . import video_pregen
        if not video_pregen.enabled():
            PREGEN_HELD.pop(job["id"], None)
            self.__dict__.get("_pregen_fingerprints", {}).pop(job["id"], None)
            return False
        hit = PREGEN_HELD.get(job["id"])
        if not hit or time.time() - hit[1] >= PREGEN_RECHECK_S:
            return False
        WAIT_REASONS[job["id"]] = hit
        return True

    def _diag(self, job, severity: str, code, message: str) -> None:
        """K3 rà: while a job is held by the check before gen, the notes written when its request is rebuilt (Kho chủ thể, bản cao,
        prompt cắt, giọng…) are said once, not on every re-check."""
        try:
            held = job["id"] in PREGEN_HELD
        except (TypeError, KeyError, IndexError):
            held = False
        if held:
            key = (job["id"], "held:" + str(code), message)
            if key in _PREGEN_SAID:
                return
            _PREGEN_SAID.add(key)
        super()._diag(job, severity, code, message)

    def _gore_hinted(self, job, group, scene_id: int) -> bool:
        """F1 sửa #5: does the FF gore-restraint sentence really go with this shot on this job's send path? A Kling multi-shot group:
        the shot's own multi_prompt entry (ClipAI ignores the whole-clip motion there); any other path: the clip's prompt as built.
        Nothing to send yet (inputs missing): True — no money goes out, the base check says what is missing."""
        from . import looks, shots
        proj = self.p.project(job["project_id"])
        if group and not self._refs(job) and shots.mode(proj) == "multishot":
            return bool(self._multi_prompt(job, proj, group, say=False)[1].get(scene_id))
        args = self._submit_args(job)
        return True if not args else looks._GORE_TAG in str(args[1])

    def _multi_prompt(self, job, proj, group, say: bool = True):
        """Kling multi-shot: each shot's own prompt (≤ KLING_SHOT_PROMPT_LIMIT) — who speaks (S0.14) and, FF project, the gore-restraint
        sentence (F1 sửa #5a: ClipAI drops the whole-clip motion in multi-shot, so the sentence goes into each shot's entry; added only
        when it fits). Returns (entries, {scene_id: restraint sentence in the entry})."""
        from . import looks, shots, speaker_lint
        from .adapters.clipai import KLING_SHOT_PROMPT_LIMIT
        entries, hinted = [], {}
        for r in group:
            m = {"prompt": self._motion(r["id"])["motion_prompt"], "duration": shots.billed_shot_seconds(r["data"])}
            res = speaker_lint.apply(m["prompt"], [r["data"]], KLING_SHOT_PROMPT_LIMIT)
            if res["missing"]:
                m["prompt"] = res["prompt"]
                if say:
                    self._diag(job, "warn", "speaker_unnamed", speaker_lint.message(f"S{r['idx']:02d}", res))
            scan = m["prompt"] + " " + " ".join(str(r["data"].get(k) or "") for k in ("image_prompt", "action", "end_state"))
            out = looks.gore_restraint(proj, m["prompt"], video=True, scan=scan)
            if out != m["prompt"] and len(out) <= KLING_SHOT_PROMPT_LIMIT:
                m["prompt"] = out
            elif out != m["prompt"] and say:
                self._diag_once(job, "warn", "gore_restraint", f"S{r['idx']:02d}: không thêm được câu chỉ GỢI máu/xác — prompt shot sẽ "
                                                                f"quá {KLING_SHOT_PROMPT_LIMIT} ký tự")
            hinted[r["id"]] = looks._GORE_TAG in m["prompt"]
            entries.append(m)
        if say and any(hinted.values()):
            self._diag_once(job, "info", "gore_restraint", "dự án FF: shot có máu/vết thương/xác — đã thêm câu chỉ GỢI vào prompt "
                                                           "từng shot (Kling nhiều shot)")
        return entries, hinted

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
        frames = [self._start_frame(job["project_id"], r["id"]) for r in rows]
        ids = seedance_refs.identity_pictures(self.p.conn, job["project_id"], rows, seedance_refs.MAX_PICTURES - len(rows))
        places = seedance_refs.place_pictures(self.data_dir, job["project_id"], rows)
        secs = [self._cut_seconds(r) for r in group] if group else [float(args[3])]
        audio = bool(self._take_segments(job, rows)) if group else bool(self._lip_sync_audio_planned(job))
        tail = self._ref_end_sentence(job, group, len(rows) + len(ids) + len(places))    # 11/10: the end frame = one more picture
        problems = seedance_refs.lint_group(args[1] + ("\n" + tail if tail else ""), len(rows),
                                            len([f for f in frames if f]) + len(ids) + len(places) + bool(tail),
                                            len(rows) + len(ids) + len(places) + bool(tail), secs, audio,
                                            model=args[4])
        from . import place_refs
        if place_refs.enabled():
            rendered = {i for ref in places for i in ref["shots"]}
            for i, row in enumerate(rows, 1):
                if i not in rendered and place_refs.wants_render(self.p.conn, job["project_id"], row["data"]):
                    problems.append(f"Shot {i} thiếu render địa điểm 3D; tạo lại render trước khi gửi video.")
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
            from . import voice as _voice
            offs = lipsync.line_offsets(lines, _voice.LIP_LEAD)     # a take shot is made with its voice: the line on a whole second
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
        """The request's keyword arguments; N1 (flag two_tier_quality) then sets the job's tier: a draft goes at the model's lowest
        tier (Seedance 2.5 `draft=True` 480p), a final from a live 2.5 draft is sent from that draft at quality_tier.FINAL_RESOLUTION
        (`_from_sample`, read by _submit_pending — the ledger and the spend check see the 1080p tier), else at the normal (high) tier."""
        out = self._base_submit_kwargs(job)
        from . import quality_tier
        if not quality_tier.enabled() or "quality_tier" not in job.keys():
            return out
        if job["quality_tier"] == "draft":
            return quality_tier.low_tier(out, self._choice(job).get("model"))
        if job["quality_tier"] == "direct" and quality_tier.draft_resolution_sent(self._choice(job), out):
            # lỗi 8 #27 (896/901): bậc ghi lúc tạo job (direct) và đường lúc gửi (nháp 2.5 480p của nhóm) lệch → job 'direct' bị gửi 2.5
            # 480p KHÔNG draft=True: không nâng 1080p được, không phải bản giao. Đường lúc gửi thắng: gửi như nháp, ghi lại bậc
            self.p.conn.execute("UPDATE jobs SET quality_tier='draft', draft_job_id=NULL WHERE id=?", (job["id"],))
            self.p.conn.commit()
            self._diag_once(job, "info", "tier_to_draft", "job gen thẳng mà đường của shot lúc gửi là nháp Seedance 2.5 480p → gửi như NHÁP "
                                                     "(draft=True, nâng 1080p được sau khi duyệt), không gửi 480p gen thẳng")
            return quality_tier.low_tier(out, self._choice(job).get("model"))
        if job["quality_tier"] == "final":
            shared = self._final_shared_task(job)    # 12/10: one group clip upgraded once — the other shots are cut from it
            if shared:
                self.__dict__.get("_final_routes", {}).pop(job["id"], None)
                return {**out, **shared}
            route = self.__dict__.get("_final_routes", {}).pop(job["id"], None) or quality_tier.final_route(self.p.conn, job,
                                                                                                         self.provider)
            if route["from_sample"]:
                return {**out, "resolution": quality_tier.FINAL_RESOLUTION, "_from_sample": route["from_sample"]}
            if route.get("transient"):           # rà F3: the draft's expiry could not be read now — wait, try again next pass
                return {**out, "_wait": f"bản cao chờ: {route['why']} — thử lại lượt sau"}
            hold = quality_tier.needs_confirm(job, route)
            if hold:                             # F3 (#24): not sent — _submit_pending fails the job with this reason
                return {**out, "_hold": f"bản cao bị chặn: {hold}"}
            confirmed = quality_tier.confirmed_new(job)
            out["resolution"] = quality_tier.final_resolution(self._choice(job).get("model"))   # E1: the choice says 480p (draft)
            self._diag(job, "warn" if confirmed else "info", "final_resend",
                       f"bản cao gen MỚI ở {out['resolution']} — {quality_tier.NEW_GEN} ({route['why']})"
                       + ("; người dùng đã xác nhận" if confirmed else "; tự gen lại kèm câu sửa (trần 1)"))
        return out

    def _base_submit_kwargs(self, job) -> Dict:
        from . import formats, quality_tier, shots
        proj = self.p.project(job["project_id"])
        out = {}
        aspect = formats.project_aspect(proj)
        if aspect:
            out["aspect_ratio"] = formats.spec(aspect)["clip"]
        choice = self._choice(job)
        if choice.get("resolution"):
            out["resolution"] = choice["resolution"]
        if choice.get("res_source") == "override" and out.get("resolution") in ("std", "pro", "4k"):
            out["kling_mode"] = out.pop("resolution")      # 09/10: ô "Chất lượng" của Kling = chế độ std / pro / 4k
        if quality_tier.cheap_mode(proj) and choice.get("res_source") != "override":
            # v3 cheap test mode: 720p, Kling std (N1: ignored with flag two_tier_quality); chất lượng người chọn cho shot thắng
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
        if self._refs(job):                  # Seedance reference only (P2m): every picture marked, no start frame (end frame: below)
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
            if not group:                    # 11/10 (#24 job 662/664): the drawn end state (K1) goes with a reference-only shot too —
                end = self._end_frame(job, choice.get("model") or "seedance", chain=False)   # the adapter sends it as the LAST
                if end:                                                                  # reference picture with its role sentence
                    from . import features, seedance_refs
                    clean = features.on("seedance_subjects") and getattr(self.provider, "supports_subjects", False)
                    pics = out["reference_only"] or []
                    deferred = self.__dict__.get("_pregen_local") and self.__dict__.get("_pregen_deferred")
                    if clean and not deferred and not all(isinstance(x, dict) for x in pics):
                        clean = False            # V5 (rà gốc 13/10): the Subject Library refused (Kho đầy) — marked like the rest
                    out_dir = os.path.join(self.data_dir, str(job["project_id"]), "refs_marked")
                    # the same treatment as the other pictures of this send: marked (real-person filter, P2m) or, with the Subject
                    # Library, an unmarked copy ≤ 1280 px; K3 checks the drawn file itself (`_last_frame_source`, never sent)
                    out["last_frame"] = seedance_refs.mark(end, out_dir, style="none" if clean else
                                                           seedance_refs.mark_style(self.p.conn, [job["scene_id"]]))
                    out["_last_frame_source"] = end
                    if clean and deferred and deferred[-1].get("mark_fallback"):
                        deferred[-1]["last_frame"] = end    # decided in _finish_kwargs with the other pictures (V5)
            return out
        if group and mode != "multishot":
            pass                         # H5 camera set-up: one continuous prompt (in the motion argument), no multi_prompt
        elif group:
            out["multi_prompt"] = self._multi_prompt(job, self.p.project(job["project_id"]), group)[0]   # S0.14 + F1 sửa #5a
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
            end = self._end_frame(job, choice.get("model") or "")
            if end:
                out["last_frame"] = end                   # K2: Seedance last_frame; Kling Omni end_frame (only with K1 on)
        return out

    def _ref_end_sentence(self, job, group, n_pictures: int) -> str:
        """The role sentence the adapter adds for a reference-only shot's end frame (picture n_pictures + 1), "" when none goes."""
        if group or not self._end_frame(job, self._choice(job).get("model") or "seedance", chain=False):
            return ""
        from .adapters.clipai import ref_end_frame_sentence
        return ref_end_frame_sentence(n_pictures + 1)

    def _end_frame(self, job, model: str, chain: bool = True) -> Optional[str]:
        """The one place that decides a shot's end frame (per-shot send and reference-only send). chain: the next shot's approved
        picture of a continuing shot (shots.last_frame_for) first — the reference-only way never had it, so it asks without. Then the
        drawn end state (K1, flag end_frames). Seedance takes it always, Kling Omni only with K1 on. A model whose rules
        (data/provider_rules.json) take no end frame: not sent, said (VÀNG with the reason — never dropped silently)."""
        from . import end_frames, shots
        end = shots.last_frame_for(self.p.conn, self.data_dir, job["scene_id"]) if chain else None
        drawn = end is None
        if drawn and end_frames.enabled():
            if end_frames.skip_reason(self.p.conn, job["scene_id"], self._scene_data(job)):
                row = end_frames.current(self.p.conn, job["scene_id"])     # R3 (rà S3): never drawn / sent — said once (GHÉP)
                self._skill_object_appears(job, (row["path"] if row is not None else None) or "")
                return None
            if end_frames.sent_without(self.p.conn, job["scene_id"]):       # C3: the person's button — never the drawn one, said once
                self._diag_once(job, "info", "end_frame_off", f"clip gửi KHÔNG kèm khung cuối: {end_frames.OFF_NOTE} (nút trên thẻ Bước 4) "
                                "— bấm “🖼 Vẽ khung cuối” rồi gen lại nếu cần cảnh kết đúng end_state")
                return None
            end = end_frames.usable_path(self.p.conn, job["scene_id"])      # K1: the drawn end state
            if not end:                  # C5 (rà chuỗi 13/10): a shot that needs one goes without it — said once, never silently
                why = end_frames.missing_reason(self.p.conn, job["scene_id"])
                if why:
                    self._diag_once(job, "warn", "end_frame_missing", f"clip gửi KHÔNG kèm khung cuối: {why} — bấm “🖼 Vẽ khung cuối” "
                                    "trên thẻ Bước 4 rồi gen lại nếu cần cảnh kết đúng end_state")
        if not end or not ("seedance" in (model or "") or end_frames.enabled()):
            return None
        from . import video_rules
        from .adapters.clipai import resolve_model
        try:
            canonical, family = resolve_model(model or None)
        except Exception:  # noqa: BLE001 - an unknown name is judged by the adapter, as before
            return end
        if drawn and self._runs_in_place(job, canonical, family):
            return None                  # the next shot's picture (chain) stays: that one IS where this shot ends
        if drawn and self._skill_object_appears(job, end):
            return None
        if drawn and self._same_ground(job, end):
            return None
        if self._end_frame_off_distance(job, end, drawn):
            return None
        r = video_rules.rule(canonical)
        if r and not r.get("end_frame" if family == "omni" else "last_frame", False):
            self._diag_once(job, "warn", "end_frame_unsupported", f"có khung cuối ({os.path.basename(end)}) nhưng "
                            f"{r.get('label') or canonical} không nhận khung cuối (data/provider_rules.json) — clip gửi không kèm "
                            "khung cuối, cảnh kết thúc theo prompt")
            return None
        return end

    def _end_frame_off_distance(self, job, end: str, drawn: bool) -> bool:
        """Flag framing_guard (lỗi hệ thống 2, #27 shot 16 job 889 / 898): an end frame at another camera distance / shot size than the
        start picture makes the model cut or drag the person — not sent, said once (VÀNG with the numbers, core/framing_guard).
        Could not measure → said, sent as before."""
        from . import framing_guard, shots
        if not framing_guard.enabled():
            return False
        start = shots.approved_image_path(self.p.conn, self.data_dir, job["project_id"], shots.image_scene(self.p.conn, job["scene_id"]))
        res = framing_guard.end_frame_check(start, end)
        if not res:
            return False
        what = "khung cuối vẽ" if drawn else "ảnh duyệt của shot sau (khung cuối nối tiếp)"
        if res.get("ok") is False:
            self._diag_once(job, "warn", "end_frame_distance", f"{res['why']} — clip gửi KHÔNG kèm {what} ({os.path.basename(end)}, cờ "
                            f"{framing_guard.FLAG}); vẽ lại khung cuối cùng khoảng cách máy với ảnh đầu nếu cần khung cuối")
            return True
        if res.get("ok") is None:
            if not self._scene_data(job).get("characters") and res.get("scale") is not None:
                return False             # R6 (rà S3): no one in the shot, the background measured — no "cỡ người" VÀNG noise
            acting = self._person_acts(job)
            if acting:                   # V3 (rà gốc 13/10, G7): end_284_21 (Kelly behind the wall) went → 907 jumped 0,6 s
                self._diag_once(job, "warn", "end_frame_distance", f"chưa đo được khoảng cách máy / cỡ người của {what} "
                                f"({os.path.basename(end)}): {res.get('note')} — shot có người {acting}: clip gửi KHÔNG kèm khung cuối "
                                f"(cờ {framing_guard.FLAG}; không đo được không coi là đạt); vẽ lại khung cuối thấy rõ mặt nếu cần")
                return True
            self._diag_once(job, "warn", "end_frame_distance", f"chưa đo được khoảng cách máy của {what} ({os.path.basename(end)}): "
                            f"{res.get('note')} — vẫn gửi, cần xem bằng mắt")
        return False

    def _scene_data(self, job) -> Dict:
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
        return json.loads(row["data"] or "{}") if row is not None else {}

    def _person_acts(self, job) -> Optional[str]:
        """V3: "di chuyển" when the shot's people move through space (spec: an unmeasured end frame is not sent only then), None for
        everything else. R6 (rà S3): a body action in place (shoot / strike) no longer counts — an end_state hiding the face on
        purpose (behind a wall, turned away) is a right end frame; it goes, said VÀNG. TODO (spec V3): measure the body box."""
        from . import motion_physics
        data = self._scene_data(job)
        if not data.get("characters") and not data.get("action"):
            return None
        return "di chuyển" if motion_physics.moves_through_space(motion_physics.shot_action(data)) else None

    def _skill_object_appears(self, job, end: str) -> bool:
        """V3 (rà gốc 13/10; người dùng 21:31 — tường keo XUẤT HIỆN LUÔN): a shot where the skill object appears (thrown) gets no drawn
        end frame — a model morphing towards a wall standing in the last frame draws it growing / wrong (#27 shot 16: 6 clips); the
        build is the code composite (hard cut). Under flag framing_guard (off by default) with skill_object_guard on; said once."""
        from . import framing_guard, skill_objects
        from . import end_frames               # R3 (rà S3): ONE rule with queue / tick / card (end_frames.skip_reason)
        if not end_frames.skip_reason(self.p.conn, job["scene_id"], self._scene_data(job)):
            return False
        self._diag_once(job, "warn", "end_frame_skill_object", f"shot có vật kỹ năng xuất hiện (ném keo) — clip gửi KHÔNG kèm khung cuối "
                        f"vẽ{f' ({os.path.basename(end)})' if end else ''}; dựng bằng GHÉP code cắt cứng sang khung có tường (`py {skill_objects.COMPOSE_TOOL}`)")
        return True

    def _same_ground(self, job, end: str) -> bool:
        """V12 (rà gốc 13/10, G12; flags locomotion_end_frame + framing_guard — the OpenCV measure): a run / walk the camera follows whose
        drawn end frame shows the start picture's place at the same size (no ground covered) → not sent, said once."""
        from . import features, framing_guard, motion_physics, shots
        if not features.on(motion_physics.LOCOMOTION_FLAG) or not framing_guard.enabled():
            return False
        data = self._scene_data(job)
        if not motion_physics.follows(data.get("camera_move")) or not motion_physics.moves_through_space(motion_physics.shot_action(data)):
            return False
        start = shots.approved_image_path(self.p.conn, self.data_dir, job["project_id"], shots.image_scene(self.p.conn, job["scene_id"]))
        why = motion_physics.same_ground(data, framing_guard.end_frame_check(start, end))
        if why:
            self._diag_once(job, "warn", "locomotion_end_frame", f"{why} — clip gửi KHÔNG kèm khung cuối vẽ ({os.path.basename(end)}, cờ "
                            f"{motion_physics.LOCOMOTION_FLAG} + {framing_guard.FLAG})")
        return bool(why)

    def _runs_in_place(self, job, canonical: str, family: str) -> bool:
        """Flag locomotion_end_frame (hộp thư 12/10 18:13, #27 job 782): a run / walk generated much longer than the shot gets no drawn
        end frame — said once (VÀNG), never dropped silently."""
        from . import features, motion_physics
        from .adapters.clipai import effective_duration
        if not features.on(motion_physics.LOCOMOTION_FLAG):
            return False
        row = self.p.conn.execute("SELECT id, data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
        if row is None:
            return False
        data = json.loads(row["data"] or "{}")
        secs = self._cut_seconds({"id": row["id"], "data": data})
        if secs <= 0:
            return False
        why = motion_physics.in_place_risk(data, secs, effective_duration(canonical, family, math.ceil(secs - 1e-6)))
        if why:
            self._diag_once(job, "warn", "locomotion_end_frame", f"{why} — clip gửi KHÔNG kèm khung cuối vẽ (cờ {motion_physics.LOCOMOTION_FLAG})")
        return bool(why)

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
        people = [(n, path) for n, path in seedance_refs.identity_pictures(conn, job["project_id"], rows, 8)
                  if not n.endswith(seedance_refs.OUTFIT_TAG)]      # one identity picture per PERSON (the outfit picture is not a person)
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

    def _render_gap(self, job) -> Optional[str]:
        """08/10 (#24): a shot of a reference-only clip without its 3D place render failed the send at once ('thiếu render địa điểm
        3D; tạo lại render' — a person has no button for that). Now, like a picture (ImageRunner._wait), the render is made / measured
        again ONCE in the background (Blender, 0 USD; a plate wrongly judged flat is re-measured by location_pack) and the clip waits;
        a shot still without a render after that goes to the send check, which says why."""
        from . import place_refs, seedance_refs
        pid = job["project_id"]
        rows = self._ref_rows(job, self._sends_group(job) or [])
        rendered = {i for ref in seedance_refs.place_pictures(self.data_dir, pid, rows) for i in ref["shots"]}
        gaps = [(i, r) for i, r in enumerate(rows, 1) if i not in rendered and place_refs.wants_render(self.p.conn, pid, r["data"])]
        if not gaps:
            return None
        thread = place_refs._RUNNING.get(pid)
        if thread is not None and thread.is_alive():
            return "đang dựng nền 3D (0 USD) — sẽ tự gửi khi xong"
        todo = [(i, r) for i, r in gaps if (pid, r["id"]) not in _RENDER_RETRIED]
        if not todo:
            return None                     # already tried once: the send check fails it and says why
        for _, r in todo:
            _RENDER_RETRIED[(pid, r["id"])] = time.time()
        place_refs.ensure_async(self.p.conn, pid, self.data_dir, place_refs.resolution_of(self.p.project(pid)),
                                log=self._thread_diag(job, "place_render"))
        return "dựng / đo lại nền 3D cho " + ", ".join(f"shot {i}" for i, _ in todo) + " (0 USD) — sẽ tự gửi khi xong"

    def _ref_rows(self, job, group) -> list:
        return group or [{"id": job["scene_id"], "data": json.loads(self.p.conn.execute(
            "SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")}]

    def _reference_pictures(self, job, group) -> list:
        """The marked pictures of a reference-only send: each shot's approved storyboard picture in film order, then one identity
        picture per character (at most 9 in all)."""
        from . import seedance_refs, shots
        conn = self.p.conn
        rows = self._ref_rows(job, group)
        frames = [self._start_frame(job["project_id"], r["id"]) for r in rows]
        labels = [f"P{job['project_id']}_S{r['id']}_frame" for r, f in zip(rows, frames) if f]
        frames = [f for f in frames if f]
        ids = seedance_refs.identity_pictures(conn, job["project_id"], rows, seedance_refs.MAX_PICTURES - len(rows))
        places = seedance_refs.place_pictures(self.data_dir, job["project_id"], rows)
        extras = [(f"P{job['project_id']}_{n}", path) for n, path in ids]
        extras += [(f"P{job['project_id']}_place_{k}", ref["path"]) for k, ref in enumerate(places, 1)]
        hosted = self._hosted_pictures(job, list(zip(labels, frames))
                                       + extras, clean=True)
        style = seedance_refs.mark_style(conn, [r["id"] for r in rows])   # lỗi hệ thống 4: "eye_plus" unless ref_mark_off_face
        if hosted:
            if self.__dict__.get("_pregen_local"):
                self._pregen_deferred[-1]["mark_fallback"] = True
                self._pregen_deferred[-1]["mark_style"] = style
                self._pregen_deferred[-1]["scene_ids"] = [r["id"] for r in rows]   # decided in _finish_kwargs
            else:
                seedance_refs.note_sent(conn, [r["id"] for r in rows], "hosted")
            return hosted
        seedance_refs.note_sent(conn, [r["id"] for r in rows], style)
        out_dir = os.path.join(self.data_dir, str(job["project_id"]), "refs_marked")
        return [seedance_refs.mark(p, out_dir, style) for p in frames + [path for _, path in extras]]

    subject_library = None          # S4.7: the Seedance Subject Library (tests set a double; else core.adapters.factory's)

    def _hosted_pictures(self, job, pictures, clean: bool = False) -> Optional[list]:
        """S4.7 (flag seedance_subjects): [(label, local picture)] → [{"uri": "asset://…"}] in the same order — each picture uploaded to
        the ClipAI Subject Library once (by its bytes, core.subjects.ensure_picture) and sent reviewed, so no red mark is needed. None
        when the flag is off, the provider is not ClipAI, or ANY picture has no active asset (said; the caller sends as before).
        clean: send an unmarked copy at most 1280 px (seedance_refs.mark style "none") — what the marked way would have resized too."""
        from . import features, seedance_refs
        if not features.on("seedance_subjects") or not pictures or not getattr(self.provider, "supports_subjects", False):
            return None
        if self.__dict__.get("_pregen_local"):
            if clean:
                out_dir = os.path.join(self.data_dir, str(job["project_id"]), "refs_clean")
                pictures = [(label, seedance_refs.mark(path, out_dir, style="none")) for label, path in pictures]
                clean = False
            local = [path for _, path in pictures]
            self._pregen_deferred.append({"local": local, "pictures": list(pictures), "clean": clean})
            return local
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
        # 08/10 (#24): 'pending_review' was left out — with "Tôi duyệt hết" every clip waits there, so the redo of shot 3 (a part of
        # the S01–S03 group clip) waited forever, silently, for shot 1 to "have a clip". A clip waiting for the person IS a clip.
        return bool(self.p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN "
                                        "('succeeded','pending_review','approved')", (scene_id,)).fetchone())

    def _lead_failure(self, scene_id: int) -> Optional[str]:
        """The failure note of the group leader's newest clip job when it failed, else None."""
        row = self.p.conn.execute("SELECT id, state FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id DESC LIMIT 1",
                                  (scene_id,)).fetchone()
        if row is None or row["state"] != "failed":
            return None
        return (self.p.failure_note(row["id"]) or "lỗi không rõ")[:200]

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

    def _chain_frame(self, project_id: int, scene_id: int) -> Optional[str]:
        """07/10 Khủng Long Đỏ: a shot marked `start_from_prev_clip` starts on the LAST frame of the previous shot's approved clip — the
        three dance clips were made apart and the cuts jumped in moves and clothes. The frame is cut once per clip (file named by the
        clip's job). None when the shot is not marked or the previous clip is not approved yet."""
        from . import ffmpeg_studio
        row = self.p.conn.execute("SELECT idx, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
        if row is None or not json.loads(row["data"] or "{}").get("start_from_prev_clip"):
            return None
        from . import takes
        before = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx<? ORDER BY idx DESC LIMIT 1",
                                     (project_id, row["idx"])).fetchone()
        # KLD-2 (08/10): the take the person chose for the previous shot (#22: 560 chosen, 569 newer — rows were swapped by hand)
        prev = takes.used(self.p.conn, before["id"], skip_cancelled=False) if before else None
        if (prev is None or prev["state"] != "approved"      # the LATEST take of the previous shot: an older approved clip being
                or not prev["result_path"] or not os.path.exists(prev["result_path"])):   # remade must not be chained (07/10)
            return None
        out = os.path.join(self._dir(project_id, "chain"), f"scene_{scene_id}_from_job_{prev['id']}.png")
        if not os.path.exists(out):
            subprocess.run([ffmpeg_studio.find_ffmpeg(), "-y", "-loglevel", "error", "-sseof", "-0.1", "-i", prev["result_path"],
                            "-frames:v", "1", "-update", "1", out], capture_output=True)
        return out if os.path.exists(out) else None

    def _start_frame(self, project_id: int, scene_id: int) -> Optional[str]:
        """The picture a shot's clip starts on: the previous clip's last frame (start_from_prev_clip), else its approved storyboard."""
        from . import shots
        return self._chain_frame(project_id, scene_id) or shots.approved_image_path(self.p.conn, self.data_dir, project_id, scene_id)

    def _waits_for_prev_clip(self, job) -> bool:
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
        return bool(row and json.loads(row["data"] or "{}").get("start_from_prev_clip")
                    and self._chain_frame(job["project_id"], job["scene_id"]) is None)

    def _wait(self, job) -> bool:
        """Kling multi-shot: the first shot of a group sends for the whole group once every shot of it has an approved motion
        prompt; the other shots wait for their part of that clip (unless the first shot already has its clip: then a remade
        shot is sent on its own). K1: a shot whose end frame is still being drawn waits for it."""
        from . import end_frames, shots
        from . import place_refs
        if place_refs.enabled() and self._refs(job) and \
                self._stale_plates(job, self._ref_rows(job, self._sends_group(job) or [])):
            return self._hold(job, "đang render lại nền 3D đã cũ (0 USD) — sẽ tự gửi khi render xong")   # KLD-6
        if place_refs.enabled() and self._refs(job):
            gap = self._render_gap(job)
            if gap:
                return self._hold(job, gap)
        if self._waits_for_prev_clip(job):  # 07/10: starts on the previous clip's last frame — that clip is approved first
            return self._hold(job, "chờ bạn duyệt clip cảnh trước (cảnh này bắt đầu từ khung cuối clip đó) — duyệt xong sẽ tự gửi")
        if end_frames.enabled():
            row = end_frames.current(self.p.conn, job["scene_id"])
            if row is not None and row["state"] in ("queued", "running") and not end_frames.skip_reason(self.p.conn, job["scene_id"]) \
                    and not end_frames.sent_without(self.p.conn, job["scene_id"]):    # C3: the person chose to send it without
                # C5: held WITH the reason (card / inbox), never silently. R8 (rà S3): also in diag (end_frame_wait ∈ HOLD_CODES) so
                # held_reason reads it after WAIT_FRESH_SEC / in another process; R1/R7: the real reason (autopilot's row waiting, cap)
                why = end_frames.missing_reason(self.p.conn, job["scene_id"]) or "đang vẽ khung cuối"
                line = f"chờ khung cuối: {why} (shot đổi trạng thái) — clip tự gửi kèm khung cuối khi vẽ xong"
                self._diag_once(job, "info", "end_frame_wait", line)
                return self._hold(job, line)
        group = shots.group_of(self.p.conn, job["scene_id"]) or []
        if len(group) < 2:
            return False
        if self._refs(job) and self._covered(job["scene_id"], group):
            return True                   # its part comes with a group clip already sent
        run = self._redo_run(job, group)
        if run and run[0]["id"] != job["scene_id"]:
            return True                   # the run's first shot sends the group clip for it
        if group[0]["id"] != job["scene_id"] and not run:
            if not self._has_clip(group[0]["id"]):
                idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (group[0]["id"],)).fetchone()
                lead = f" (S{idx['idx']:02d})" if idx else ""
                why = self._lead_failure(group[0]["id"])         # F1 sửa #4: a leader stopped (e.g. prompt sai công thức) is said here
                lead_job = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id DESC LIMIT 1",
                                              (group[0]["id"],)).fetchone()
                pregen = PREGEN_HELD.get(lead_job["id"]) if lead_job else None
                from . import video_pregen
                if pregen and video_pregen.enabled():
                    return self._hold(job, f"chờ clip nhóm gửi từ shot đầu nhóm{lead} — {pregen[0]}; sửa đầu vào shot đó, phần này đi cùng clip nhóm")
                return self._hold(job, f"chờ clip nhóm gửi từ shot đầu nhóm{lead} — "
                                  + (f"shot đầu nhóm đang hỏng ({why}) — sửa rồi gửi lại shot đó, phần này đi cùng clip nhóm" if why
                                     else "gửi shot đó trước, phần này đi cùng clip nhóm"))
            return False
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
        path = self._chain_frame(job["project_id"], job["scene_id"]) or             os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{img['id']}.png")
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
            # V1 (rà gốc 13/10; S2 → S3): each render measured against the approved start frames (flag plate_view_sentence)
            starts = ({r["id"]: self._start_frame(job["project_id"], r["id"]) for r in rows}
                      if seedance_refs.plate_view_on() else None)
            places = seedance_refs.place_pictures(self.data_dir, job["project_id"], rows, starts=starts)
            segs = self._take_segments(job, rows)
            block = ""
            if segs:                                   # S4.2: who says which line at which second (the lines stay in Vietnamese)
                from . import dialogue_take
                block = dialogue_take.group_block(segs, [n for n, _ in ids if not n.endswith(seedance_refs.OUTFIT_TAG)])
            # F5-A: real sizes of the library objects (the well), short form, once — dropped first when the prompt would pass the limit
            motion = no_minor_age(seedance_refs.prompt(parts, ids, clip_seconds=duration, model=model, places=places,
                                                       scales=_object_scales(conn, job["project_id"], rows),
                                                       reserve=(len(block) + 1 if block else 0)
                                                       + len(self._ref_end_sentence(job, group, len(rows) + len(ids) + len(places))) + 1
                                                       + _skill_reserve(conn, job["project_id"],
                                                                        _reserve_text(parts, ids, places, model_fix(job["retry_reason"])))))
            if block:
                motion += "\n" + block
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
        motion = _skill_object_guard(self, job, motion, "video", group)   # lỗi hệ thống 3 (cờ skill_object_guard)
        motion = self._gore_restraint(job, proj, motion, group, model)
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
        from .adapters.clipai import PROMPT_LIMITS
        shown = [("Ảnh khung đầu (clip bắt đầu từ đúng ảnh này)", path)]
        if "seedance" in (model or ""):
            shown += [(f"Ảnh tham chiếu: {r['label']}", r["path"]) for r in assets.scene_references(
                conn, job["project_id"], json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"]
                                                    or "{}"))]
        motion = chat_rewrite(self, job, "video", motion, shown, model,
                                   limit=PROMPT_LIMITS.get(model or "") or (PROMPT_LIMITS["kling"] if "kling" in str(model or "").lower() else 4000))
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
                from . import video_pregen
                from .adapters.clipai import SEEDANCE_REFS_WITH_FIRST_FRAME
                keep_missing = video_pregen.enabled() and SEEDANCE_REFS_WITH_FIRST_FRAME and not self._refs(job)
                self._diag(job, "warn", "missing_reference",
                          ("ảnh tham chiếu không đọc được (giữ để lớp kiểm trước gen báo chặn): " if keep_missing else
                           "ảnh tham chiếu không đọc được (bỏ qua, video vẫn gen): ") + ", ".join(r["label"] for r in missing))
                if not keep_missing:
                    image_refs = [r for r in image_refs if r not in missing]
        ref_video = None
        if mp["ref_video_path"] and os.path.exists(mp["ref_video_path"]):
            ref_video = {"path": mp["ref_video_path"], "refer_type": mp["ref_video_type"] or "feature"}
        elif mp["ref_video_path"]:
            from . import video_pregen
            if video_pregen.enabled():
                ref_video = {"path": mp["ref_video_path"], "refer_type": mp["ref_video_type"] or "feature"}
            self._diag(job, "warn", "missing_reference",
                      (f"video tham chiếu chuyển động không đọc được (giữ để lớp kiểm trước gen báo chặn): {mp['ref_video_path']}"
                       if ref_video else f"video tham chiếu chuyển động không đọc được (bỏ qua, video vẫn gen): {mp['ref_video_path']}"))
        if skill:            # S10.4: the skill way sends its pictures / videos as keyword arguments (_submit_kwargs) — not twice
            subj_refs, image_refs, ref_video = [], [], None
        if proj["video_audio"] or subj_refs or image_refs or ref_video:  # extra args only when used: older providers keep working
            args += (bool(proj["video_audio"]), subj_refs or None, image_refs or None, ref_video)
        return args

    def _gore_restraint(self, job, proj, motion: str, group, model) -> str:
        """F1-B luật tầng 1 (FF): blood / gore of the clip only hinted. Judged on the motion text and the Director's picture words of the
        clip's shots (the start frame may carry what the motion text does not repeat). Kept within the model's prompt limit (the look
        sentence still to come is counted): over it, the sentence is left out and said — never a blocked send."""
        from . import looks
        from .adapters.clipai import PROMPT_LIMITS
        rows = [r["data"] for r in group] if group else [json.loads(self.p.conn.execute(
            "SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")]
        scan = motion + " " + " ".join(str(d.get(k) or "") for d in rows for k in ("image_prompt", "action", "end_state"))
        out = looks.gore_restraint(proj, motion, video=True, scan=scan)
        if out == motion:
            return motion
        limit = PROMPT_LIMITS.get(model or "") or (PROMPT_LIMITS["kling"] if "kling" in str(model or "").lower() else 4000)
        if len(out) + len(looks.video_sentence(proj)) + 1 > limit:
            self._diag_once(job, "warn", "gore_restraint", f"không thêm được câu chỉ GỢI máu/xác: prompt sẽ quá {limit} ký tự")
            return motion
        self._diag_once(job, "info", "gore_restraint", "dự án FF: clip có máu/vết thương/xác — đã thêm câu chỉ GỢI, không thấy rõ")
        return out

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
            ids = [r["id"] for r in group] if group else [job["scene_id"]]
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            step = seedance_refs.next_route(data, bool(group))
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
        name = f"{idx:02d}_final{job['id']}_nhap_cu.mp4" if self._superseded(job) else f"{idx:02d}.mp4"   # 13/10: never over NN.mp4
        return os.path.join(self._dir(job["project_id"], "videos"), name)

    def _superseded(self, job) -> Optional[str]:
        from . import quality_tier
        return quality_tier.superseded_by(self.p.conn, job)

    def _after_download(self, job, path: str) -> str:
        """v3 shot rows: the model makes at least 3-4 s, a shot may be shorter -> keep the full clip as <idx>_raw.mp4 and cut the
        shot's own length into <idx>.mp4, so render, voice placement and subtitles all use the cut length. A Kling multi-shot
        clip is first split into one clip per shot of its group; the other shots' jobs are completed with their part."""
        from . import shots
        draft = self._upgrade_draft(job)
        if draft is not None:                  # 12/10 (#24): a final made from its draft's task is cut where the draft was cut
            done = self._finish_upgrade(job, path, draft)
            if done is not None:
                return done
        sent = json.loads(job["sent_group"]) if "sent_group" in job.keys() and job["sent_group"] else None
        group = ([{"id": g["id"], "idx": g["idx"], "refs": bool(g.get("refs")),
                   "data": {"duration_s": g["duration_s"], "exact": bool(g.get("exact")), "offset": g.get("offset")}} for g in sent]
                 if sent
                 else self._sends_group(job))       # M10: the group as it was sent (a later re-plan must not mis-cut a paid clip)
        part, edges, whole = None, None, None
        if group:
            whole = _probe(path)               # rà 12/10: the whole group clip measured (== <idx>_group.mp4), before it is cut; not
            parts = self._finish_group(job, path, group, whole=whole)   # measured → no "whole" (never the parts' sum / res["end"])
            edges = self._clean_edges(job, path)
            part = parts[0] if isinstance(parts, list) and parts else None
        else:
            whole = _probe(path)
        lone_ref = False
        trim: Dict = {}
        try:
            lone_ref = not group and bool(self._refs(job))
            if not lone_ref:                   # 28/09: a lone Seedance shot's prompt spreads the action over the whole clip (>= 4 s) —
                shots.trim_clip(self.p, job["scene_id"], path, out=trim)   # cut to its 1-2 s plan, S5·1 lost the fall: kept whole instead
            else:                              # S2.5 (cờ motion_trim): cut at its busiest window, never under the action's floor
                shots.trim_clip(self.p, job["scene_id"], path, lone_ref=True, out=trim)
        except Exception as e:  # noqa: BLE001 - a clip that cannot be cut is still a usable (longer) clip
            self._diag(job, "warn", "trim_error", f"không cắt được clip theo độ dài shot ({type(e).__name__}: {e}); dùng nguyên clip")
        self._save_span(job["id"], _span(part, edges, trim, whole, lone_ref) if (part or not group) else None)
        if not group:
            from . import lipsync
            rec = lipsync.index(self.data_dir, job["project_id"]).get(str(job["scene_id"])) or {}
            if rec.get("state") == "generate_sent" and rec.get("job_id") == job["id"]:
                lipsync.mark(self.data_dir, job["project_id"], job["scene_id"], state="done")
        return path

    def _clean_edges(self, job, path: str) -> Optional[Dict]:
        """S4.5: a shot cut from a group clip loses the neighbouring shot's frames left at its edges — said, never silent. Returns the
        seconds dropped ({"head", "tail"}) or None (recorded in the take's clip_span)."""
        from . import shots
        done = shots.clean_edges(path)
        if done:
            self._diag(job, "info", "stray_edges", f"bỏ khung của shot kề lẫn ở mép clip: đầu {done['head']} s, cuối {done['tail']} s "
                                                   "(điểm cắt clip nhóm lệch) — bản chưa bỏ lưu ở _edges.mp4")
            if done["head"] > 0:
                self._take_edge_shift(job, float(done["head"]))
        return done or None

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

    def _finish_group(self, leader, path: str, group, whole: Optional[float] = None) -> Optional[list]:
        """Cut a group clip into its shots; the followers' jobs get their part. Returns each shot's part [(start, seconds)] in the whole
        clip (None when the cut points are not known) — recorded on each take (clip_span) so its final is cut at the same place."""
        from . import formats, lineage, shots
        conn = self.p.conn
        if whole is None:
            whole = _probe(path)                  # the whole clip's seconds, measured before it is cut (None = unknown, not guessed)
        aside = self._superseded(leader)        # 13/10: a final of an older draft — its parts are kept aside, never the shots' clips
        tail = f"_final{leader['id']}_nhap_cu" if aside else ""
        dests = [path] + [os.path.join(self._dir(leader["project_id"], "videos"), f"{r['idx']:02d}{tail}.mp4") for r in group[1:]]
        from . import takes                     # F3 (#24 job 590/592/594): a group clip never overwrites the followers' older takes —
        for r, dest in zip(group[1:], dests[1:]):  # each goes to the trash under its own job, its result_path follows (↩ Dùng bản này)
            if not aside:
                takes.make_room(conn, self.data_dir, {"id": leader["id"], "scene_id": r["id"], "project_id": leader["project_id"]}, dest,
                                with_raw=True)
        parts = None
        if group[0].get("refs"):
            from . import seedance_refs
            res = seedance_refs.split(path, group, dests)
            self._take_done(leader, group, [0.0] + list(res["cuts"]))
            for code, sev, text in seedance_refs.split_notes(res, len(group)):   # said, not hidden: how the group was cut
                self._diag(leader, sev, code, text)
            try:
                bounds = [0.0] + [float(c) for c in res["cuts"]] + [float(res["end"])]
                parts = [(a, b - a) for a, b in zip(bounds, bounds[1:])] if len(bounds) == len(group) + 1 else None
            except (KeyError, TypeError, ValueError):
                parts = None                      # a split that did not say where it cut: the parts are not known (said on the final)
        else:
            shots.split_group_clip(path, group, dests)
            parts = shots.group_parts(group)
        aspect = formats.project_aspect(self.p.project(leader["project_id"]))
        for k, (r, dest) in enumerate(zip(group[1:], dests[1:]), 1):
            follower = conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND state='queued' ORDER BY id DESC LIMIT 1",
                                    (r["id"],)).fetchone()
            prev = None
            if aside:
                # the group clip covered the follower's queued take; it is not made by this clip any more — never sent alone (paid, unasked)
                if follower is not None:
                    self.p.transition(follower["id"], JobState.CANCELLED, actor="system",
                                      note=f"clip nhóm job {leader['id']} là bản cao bị thay ({aside}) — không gửi riêng; xếp lại khi cần")
                    follower = None
                prev = takes.used(conn, r["id"])     # the follower's take before this part, kept for chain_waits / _chain_frame
            jid = follower["id"] if follower else self.p.create_job(r["id"], "video_gen")
            mp = self._motion(r["id"])
            conn.execute("UPDATE jobs SET group_leader=?, external_id=?, model=?, input_hash=?, source_job_id=? WHERE id=?",
                         (leader["id"], leader["external_id"], leader["model"] or "kling",
                          lineage.video_input_hash(mp, aspect) if mp else None,
                          lineage.approved_image_id(conn, shots.image_scene(conn, r["id"])), jid))
            lead = conn.execute("SELECT quality_tier FROM jobs WHERE id=?", (leader["id"],)).fetchone()
            if lead is not None and lead["quality_tier"] == "draft":
                # lỗi 8 #27: leader gửi như nháp (kể cả đổi bậc lúc gửi) → phần của follower cũng là nháp 480p, không phải 'direct'
                conn.execute("UPDATE jobs SET quality_tier='draft', draft_job_id=NULL WHERE id=? AND quality_tier='direct'", (jid,))
            _copy_package(conn, leader, jid)       # K1a: a follower was sent as part of the leader's request (paid once)
            self._running(jid, f"phần của clip nhóm (job {leader['id']})")   # T2: one transaction with the leader's task id (paid once)
            edges = self._clean_edges(self.p.job(jid), dest)
            trim: Dict = {}
            try:
                shots.trim_clip(self.p, r["id"], dest, out=trim)
            except Exception as e:  # noqa: BLE001
                self._diag(self.p.job(jid), "warn", "trim_error", f"không cắt được clip theo độ dài shot: {e}")
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, jid))
            self._save_span(jid, _span(parts[k], edges, trim, whole, False) if parts else None)
            conn.commit()
            if aside:                              # 13/10: cancelled (takes.used skips it), never the follower shot's take; file kept
                self.p.transition(jid, JobState.CANCELLED, actor="system",
                                  note=f"bản cao cho nghỉ: phần của bản cao nhóm job {leader['id']} — {aside}")
                if prev is not None and takes.chosen(conn, r["id"]) is None:
                    takes.mark(conn, r["id"], prev["id"])   # the newest (cancelled) job never becomes the take read with skip_cancelled=False
            else:
                self.p.succeed(jid)
        return parts

    # ---- 12/10 (#24): bản cao nâng từ nháp = đúng đoạn nháp đã duyệt, follower cắt từ clip nhóm 1080p ------------------------------
    def _save_span(self, job_id: int, span: Optional[Dict]) -> None:
        """Where this take's file sits in its task's whole clip (jobs.clip_span) — a ledger: never raises, never blocks the take."""
        if span is None:
            return
        try:
            self.p.conn.execute("UPDATE jobs SET clip_span=? WHERE id=?", (json.dumps(span), job_id))
        except Exception:  # noqa: BLE001 - an old database without the column: the final says it cannot find the span
            pass

    def _upgrade_draft(self, job):
        """The draft job a downloaded `final` was upgraded from (submit_final_from_sample: the very task of that draft, at 1080p), or
        None (not a final / a NEW gen of the final). Read from the package really sent (K1a); a job without a package (old data) counts
        as upgraded when it could only have been (a Seedance 2.5 draft, no confirmed new gen, no fix sentence)."""
        if "quality_tier" not in job.keys() or job["quality_tier"] != "final" or not job["draft_job_id"]:
            return None
        draft = self.p.conn.execute("SELECT * FROM jobs WHERE id=?", (job["draft_job_id"],)).fetchone()
        if draft is None:
            return None
        try:
            call = json.loads(job["sent_package"] or "{}").get("call")
        except (ValueError, TypeError, AttributeError):
            call = None
        if call:
            return draft if call == "submit_final_from_sample" else None
        from . import quality_tier
        if quality_tier.confirmed_new(job) or model_fix(job["retry_reason"]) or \
                quality_tier._canonical(draft["model"])[0] != quality_tier.SAMPLE_MODEL:
            return None
        return draft

    def _span_of(self, job) -> Optional[Dict]:
        try:
            span = json.loads(job["clip_span"] or "null") if "clip_span" in job.keys() else None
        except (ValueError, TypeError):
            span = None
        return span if isinstance(span, dict) else None

    def _upgrade_members(self, draft) -> list:
        """The draft jobs carried by the draft's task, in shot order: [leader, followers…] for a group clip, [] for a lone clip."""
        from . import seedance_refs
        conn = self.p.conn
        lead = draft
        if draft["group_leader"] and draft["group_leader"] != draft["id"]:
            lead = conn.execute("SELECT * FROM jobs WHERE id=?", (draft["group_leader"],)).fetchone() or draft
        if not lead["sent_group"] and lead["id"] == draft["id"]:
            return []
        members = [m for m in seedance_refs.group_members(conn, lead["id"]) if m["external_id"] == lead["external_id"]]
        return members if len(members) >= 2 else []

    def _cut_span(self, scene_id: int, whole: str, dest: str, span: Dict) -> Optional[str]:
        """Cut `dest` out of `whole` at the draft's part (start + length, edges included) and trim it where the draft was trimmed — the
        same cutting functions as the draft (seedance_refs._cut_parts, shots.trim_clip). Returns what went wrong, or None."""
        from . import ffmpeg_studio, seedance_refs, shots
        start, length = float(span.get("start") or 0.0), span.get("length")
        if length is not None or start > 0:
            end = start + float(length) if length is not None else (_probe(whole) or 0.0)
            if end - start < 0.2:
                return f"đoạn {start:.3f}–{end:.3f} s không có trong clip"
            seedance_refs._cut_parts(whole, [start, end], [dest], ffmpeg_studio.find_ffmpeg())
            got = _probe(dest)
            if got is None or abs(got - (end - start)) > 0.35:   # _cut_parts copies the whole clip when ffmpeg fails: never kept silently
                return f"cắt đoạn {start:.3f}–{end:.3f} s ra {got if got is not None else '?'} s"
        elif os.path.normcase(os.path.abspath(whole)) != os.path.normcase(os.path.abspath(dest)):
            shutil.copyfile(whole, dest)
        if span.get("trim") is not None:
            shots.trim_clip(self.p, scene_id, dest, lone_ref=bool(span.get("lone_ref")), at=float(span["trim"]))
        return None

    def _finish_upgrade(self, job, path: str, draft) -> Optional[str]:
        """A final upgraded from its draft's task (#24 12/10): the 1080p clip is the draft's clip at a higher resolution, so the shot
        is cut at the draft's own part (#24 shot 05: 1,833–4,833 s, cut from 0 s before), and every other shot of that group clip gets
        its 1080p part too (02/03/09 stayed 480p) — 0 USD, nothing is sent again. None = the draft did not record its part (old take):
        the caller cuts as before, said in diag."""
        span = self._span_of(draft)
        members = self._upgrade_members(draft)
        if span is None:
            self._diag(job, "warn", "final_span_unknown",
                       f"bản cao nâng từ nháp job {draft['id']}: nháp không ghi đoạn đã dùng (nháp làm trước 12/10) — cắt bản cao theo cách "
                       "cũ, có thể KHÁC đoạn nháp đã duyệt: xem lại" + (" ; các shot khác của clip nhóm không được cắt 1080p tự động"
                                                                         if members else ""))
            return None
        whole = os.path.splitext(path)[0] + "_group.mp4"   # rà 12/10: always a copy — never cut a file onto itself (whole == path)
        shutil.copyfile(path, whole)                      # the whole 1080p clip, kept for ✂ cắt lại (seedance_refs.recut)
        try:
            err = self._cut_span(job["scene_id"], whole, path, span)
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        if err:
            self._diag(job, "error", "final_cut", f"không cắt được bản cao đúng đoạn nháp job {draft['id']} ({err}) — clip 1080p đã trả "
                       f"tiền giữ ở {os.path.basename(whole)} (✂ cắt tay, 0 USD); không gửi lại")
            if os.path.exists(path):
                os.remove(path)                           # a wrong part (the whole clip) is never left as the shot's file
            raise UpgradeCutFailed(err)
        measured = _probe(whole)
        self._save_span(job["id"], _with_whole(span, measured))
        for m in members:
            if m["scene_id"] != job["scene_id"]:
                self._upgrade_follower(job, m, whole, measured)
        return path

    def _upgrade_follower(self, final, draft, whole: str, measured: Optional[float] = None) -> None:
        """One other shot of the upgraded group clip: its 1080p part, cut where its draft part was — a job `final` of that shot (a
        queued one is used), with the draft's stamp; never a second paid task. Not cut (said VÀNG, the shot is made again instead):
        its draft is not the approved one, its inputs changed after the draft, it already has another final, or the part is unknown."""
        from . import quality_tier, takes
        conn = self.p.conn
        sid = draft["scene_id"]
        idx = conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()["idx"]
        rows = conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND quality_tier='final' AND id!=? "
                            "AND state NOT IN ('failed','cancelled','rejected') ORDER BY id DESC", (sid, final["id"])).fetchall()
        queued = [r for r in rows if r["state"] == "queued" and not r["external_id"]]
        approved = quality_tier.approved_draft(conn, sid)
        span = self._span_of(draft)
        why = None
        if len(rows) > len(queued):
            why = f"shot đã có bản cao khác (job {next(r['id'] for r in rows if r['id'] not in {q['id'] for q in queued})})"
        elif approved is None or approved["id"] != draft["id"]:
            why = "nháp của shot trong clip nhóm chưa được bạn duyệt (hoặc bạn đã duyệt một nháp khác)"
        else:
            stale = quality_tier.draft_stale_reason(conn, draft)
            if stale:
                why = f"đầu vào đã đổi sau khi duyệt nháp ({stale}) — cần gen lại shot này"
            elif span is None:
                why = "nháp không ghi đoạn đã dùng trong clip nhóm (nháp làm trước 12/10)"
        if why:
            self._diag(final, "warn", "final_follower_skipped",
                       f"S{idx:02d}: không cắt bản cao từ clip nhóm 1080p (job {final['id']}): {why}. Clip nhóm 1080p giữ ở "
                       f"{os.path.basename(whole)} (✂ cắt tay, 0 USD); không gửi thêm task")
            return
        jid = queued[0]["id"] if queued else self.p._insert_job(final["project_id"], sid, "video_gen", quality_tier="final",
                                                                 draft_job_id=draft["id"])
        videos = self._dir(final["project_id"], "videos")
        dest = os.path.join(videos, f"{idx:02d}.mp4")
        tmp_dir = os.path.join(videos, ".upgrade_tmp")    # rà 12/10: cut aside first — the draft's file moves only once the cut is right
        os.makedirs(tmp_dir, exist_ok=True)
        tmp = os.path.join(tmp_dir, f"{idx:02d}.mp4")
        tmp_raw = os.path.splitext(tmp)[0] + "_raw.mp4"
        conn.execute("UPDATE jobs SET group_leader=?, external_id=?, model=?, input_hash=?, source_job_id=?, draft_job_id=? WHERE id=?",
                     (final["id"], final["external_id"], final["model"] or draft["model"], draft["input_hash"], draft["source_job_id"],
                      draft["id"], jid))
        _copy_package(conn, final, jid)        # sent as part of the final's request (paid once, one ledger row on the final)
        self._running(jid, f"phần bản cao của clip nhóm 1080p (job {final['id']}) — đúng đoạn nháp job {draft['id']}, không gửi thêm task")
        for old in (tmp, tmp_raw):
            if os.path.exists(old):
                os.remove(old)
        try:
            err = self._cut_span(sid, whole, tmp, span)
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        if not err:
            try:
                takes.make_room(conn, self.data_dir, {"id": jid, "scene_id": sid, "project_id": final["project_id"]}, dest, with_raw=True)
                os.replace(tmp, dest)
                if os.path.exists(tmp_raw):
                    os.replace(tmp_raw, os.path.splitext(dest)[0] + "_raw.mp4")
            except Exception as e:  # noqa: BLE001
                err = f"đưa phần đã cắt vào chỗ lỗi ({type(e).__name__}: {e})"
        if err:
            self._diag(self.p.job(jid), "error", "final_follower_cut", f"S{idx:02d}: không cắt được phần bản cao từ clip nhóm 1080p ({err}) — "
                       "file nháp của shot giữ nguyên; cắt tay ở ✂ (0 USD)")
            for bad in (tmp, tmp_raw):
                if os.path.exists(bad):
                    os.remove(bad)                  # a wrong part (the whole clip) is never left as the shot's file
            self.p.fail(jid, f"final_follower_cut: {err}")
            return
        conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, jid))
        self._save_span(jid, _with_whole(span, measured))
        conn.commit()
        self.p.succeed(jid)

    def _final_shared_task(self, job) -> Optional[Dict]:
        """A final whose draft task is already being upgraded by another final job (a group clip carries several shots): never a second
        paid upgrade of the same task — wait for that clip (its part is cut from it, _upgrade_follower), or stop when it is done.
        Only a real upgrade is held (rà 12/10): a NEW gen of the final (e.g. a Kling group, a fix, a confirmed new gen) never waits.
        Several queued finals of one draft task, none sent yet: the lowest id goes first, the others wait (never paid twice)."""
        if not self._upgrade_candidate(job):
            return None
        conn = self.p.conn
        task = conn.execute("SELECT external_id FROM jobs WHERE id=?", (job["draft_job_id"],)).fetchone()["external_id"]
        rows = conn.execute(
            "SELECT f.* FROM jobs f JOIN jobs d ON d.id=f.draft_job_id WHERE f.type='video_gen' AND f.quality_tier='final' "
            "AND f.id!=? AND d.external_id=? ORDER BY f.id DESC", (job["id"], task)).fetchall()
        upgrades = set()
        for r in rows:
            try:
                call = json.loads(r["sent_package"] or "{}").get("call")
            except (ValueError, TypeError, AttributeError):
                call = None
            if call == "submit_final_from_sample" and r["external_id"]:
                upgrades.add(r["id"])
        other = next((r for r in rows if r["state"] in ("running", "succeeded", "pending_review", "approved")
                      and (r["id"] in upgrades or (r["group_leader"] and r["group_leader"] in upgrades))), None)
        if other is None:
            first = next((r for r in rows if r["state"] == "queued" and not r["external_id"] and r["id"] < job["id"]
                          and self._upgrade_candidate(r)), None)
            if first is not None:
                return {"_wait": f"task nháp này sẽ được nâng 1080p ở job {first['id']} (gửi trước) — phần shot này cắt từ clip đó, "
                                 "không gửi thêm task"}
            return None
        if other["state"] == "running":
            return {"_wait": f"clip nhóm 1080p của task nháp này đang nâng ở job {other['id']} — phần shot này cắt từ clip đó, không gửi thêm task"}
        return {"_hold": f"clip nhóm 1080p của task nháp này đã có ở job {other['id']} (đã trả tiền) — không nâng lần 2; phần shot này "
                         "không cắt được từ clip đó (xem chẩn đoán final_follower_skipped): gen nháp lại shot này"}

    def _upgrade_candidate(self, job) -> bool:
        """A final that would be sent as an upgrade of its draft's task: a Seedance 2.5 draft with a task, no fix sentence, no
        confirmed new gen (the same test as _upgrade_draft for a job without a package)."""
        from . import quality_tier
        if "quality_tier" not in job.keys() or job["quality_tier"] != "final" or not job["draft_job_id"]:
            return False
        draft = self.p.conn.execute("SELECT model, external_id FROM jobs WHERE id=?", (job["draft_job_id"],)).fetchone()
        if draft is None or not draft["external_id"]:
            return False
        if quality_tier.confirmed_new(job) or model_fix(job["retry_reason"]):
            return False
        return quality_tier._canonical(draft["model"])[0] == quality_tier.SAMPLE_MODEL


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


def layout_frame_job(conn, project_id: int, scene_data):
    """12/10 (#27 shot 11–12): the picture of the OTHER shot (before or after) named by the scene's `continuity_from` (its idx) — a shot back at the same
    spot after a branch (another `sequence`, so neither the storyboard anchor nor the previous frame reaches it) keeps the people's
    spots from it. The approved picture first, else its newest picture waiting for review (row with `id`, `state`), None without one."""
    idx = (scene_data or {}).get("continuity_from")
    if not isinstance(idx, int) or isinstance(idx, bool):
        return None
    return conn.execute("SELECT j.id, j.state FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.project_id=? AND s.idx=?"
                        " AND j.type='image_gen' AND j.state IN ('approved','pending_review','succeeded')"
                        " ORDER BY (j.state='approved') DESC, j.id DESC LIMIT 1", (project_id, idx)).fetchone()


def layout_reference(runner, job, data):
    """The `continuity_from` shot's picture as a 'layout_from' reference, or None. Never silent: a named shot without a picture, or
    with one not approved yet, is reported."""
    want = (data or {}).get("continuity_from")
    if want is None:
        return None
    say = getattr(runner, "_diag_once", None) or getattr(runner, "_diag", None) or (lambda *a: None)  # args rebuilt every poll
    row = layout_frame_job(runner.p.conn, job["project_id"], data)
    path = os.path.join(runner.data_dir, str(job["project_id"]), "images", f"job_{row['id']}.png") if row else None
    if not path or not os.path.exists(path):
        say(job, "warn", "missing_reference", f"shot {want} (giữ bố cục — continuity_from) chưa có ảnh: không gửi được")
        return None
    if row["state"] != "approved":
        say(job, "warn", "layout_from_unapproved", f"giữ bố cục theo ảnh shot {want} (job {row['id']}) CHƯA duyệt")
    return {"path": path, "label": f"shot {want} (same place)", "role": "layout_from"}


def chain_previous(proj, scene_data) -> bool:
    """Send the previous approved frame as an extra reference? storyboard_mode 1 = always; 0 (default) / 2 = never. S14.9 (06/10):
    the automatic chaining inside a sequence (flag chain_previous_auto, GĐ6 F8/I2: a close-up dragged in the wide frame's layout)
    was removed — `scene_data` is kept for the callers."""
    return (proj["storyboard_mode"] or 0) == 1


_MINOR_AGE = re.compile(r"\b(?:[1-9]|1[0-7])[- ]?(?:-|\s)?years?[- ]old\b[,]?\s*", re.IGNORECASE)


def _reserve_text(parts, ids, places, fix=None) -> str:
    """The text `skill_objects.reserve` judges (rà S1+S2 13/10): the shots' motion, the NAMES the prompt numbers its pictures by
    ("Image 3 is Bom keo …" — a skill object named only there still gets the skin / ban sentences after the prompt is built) and the
    retry's fix."""
    names = [str(n) for n, _ in (ids or [])]
    names += [str(r.get("name") or os.path.splitext(os.path.basename(r.get("path") or ""))[0]) for r in (places or [])]
    return " ".join([p for p, _ in (parts or [])] + names + [fix or ""])


def _skill_reserve(conn=None, project_id=None, text=None) -> int:
    from . import skill_objects                      # lỗi hệ thống 3: room for the ban sentence added after the prompt (0 when off)
    return skill_objects.reserve(conn, project_id, text)   # rà S2 13/10 mục 7: skin room only with a skill object in the text


def _skill_object_guard(runner, job, text: str, what: str, group=None) -> str:
    """Lỗi hệ thống 3 (#27 13/10, cờ skill_object_guard — tắt: trả nguyên văn): câu nói tới vật kỹ năng (tường keo…) bỏ từ model hiểu
    thành vật thật (elevator/door/thang máy) + chữ tả quá trình mọc → "đã đứng sẵn" + câu cấm (core/skill_objects); đã thay gì → ghi
    diag. Video: shot ném keo (tường XUẤT HIỆN LUÔN, người dùng 13/10 21:31) → VÀNG gợi ý dựng bằng ghép code cắt cứng."""
    from . import skill_objects
    if not skill_objects.enabled() or not text:
        return text
    conn = runner.p.conn
    new, removed, names = skill_objects.guard_prompt(conn, job["project_id"], text)
    say = getattr(runner, "_diag_once", None) or getattr(runner, "_diag", None)
    if names and say:
        say(job, "info", "skill_object_words",
            f"vật kỹ năng {', '.join(names)}: prompt {what} thêm câu cấm (không cửa mở / không nhìn xuyên / không ai đứng trong)"
            + (" + thay từ dễ hiểu sai: " + ", ".join(removed) if removed else ""))
    if what == "video" and names and say:
        rows = group or [{"id": job["scene_id"], "data": json.loads((conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],))
                                                                       .fetchone() or {"data": "{}"})["data"] or "{}")}]
        if any(skill_objects.rises(r["data"]) for r in rows):
            say(job, "warn", "skill_object_compose",
                f"shot có {', '.join(names)} xuất hiện (ném keo) — tường xuất hiện luôn, prompt tả tường đã đứng sẵn đủ cao (không tả "
                f"mọc); model video hay vẽ sai vật kỹ năng (#27 shot 16: 6 lần gen hỏng) → gợi ý dựng bằng GHÉP code: clip người cắt "
                f"cứng sang khung cuối có tường + rung (`py {skill_objects.COMPOSE_TOOL}`)")
    return new


def no_minor_age(text: str) -> str:
    """No age under 18 in a prompt sent to a picture/video model: GPT Image 2.5 refused "KELLY, 17-year-old young woman … in
    darkness, eyes red" (safety system, 2026-09-25, trial 2A) while the same shot family without the age passed. The age adds nothing
    the reference pictures do not already show."""
    return _MINOR_AGE.sub("", text or "")


def lock_exceptions(data: Optional[Dict]) -> Dict[str, Dict]:
    """BYĐ `ngoai_le` of THIS shot per character name (core/lock_exceptions.for_shot — one source for every reader of the lock).
    11/10 #24 shots 9–10: the Character Lock ("keep … full-body glitch/noise effect; never … losing glitch effect") beat the shot's own
    exception "ảnh sạch" and both pictures came out with glitch streaks."""
    from . import lock_exceptions as lx
    return lx.for_shot(data)


def lock_note(conn, project_id: int, cast, data: Optional[Dict] = None) -> str:
    """Character Lock of the people in the shot, as one sentence for the image model (what must never drift). `data` (the scene) →
    the shot's BYĐ `ngoai_le` for a person overrides the matching lock clauses (lock_exceptions)."""
    from . import features, profile_digest
    parts = []
    exc = lock_exceptions(data)
    for r in conn.execute("SELECT name, lock_rules, outfit_image_ids FROM characters WHERE project_id=?", (project_id,)):
        if r["name"] not in (cast or []):
            continue
        if (r["outfit_image_ids"] or "").strip():
            # 07/10 Khủng Long Đỏ: MAXIM KL's lock came from the library profile of MAXIM with his everyday clothes ("black baseball cap
            # worn backwards, bomber jacket") and the costume's cap (black with red horns — user 08/10) was drawn as the plain black cap —
            # face/hair/build only here
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
    # F1-C (#22: KELLY's print "GREEN dinosaur" in the picture words, "blue dinosaur print" in the blocking) — one source for the costume;
    # phiên sửa: only when someone in the shot IS held to a costume (garment_profile; not when `may_change` frees the clothes)
    from . import lock_exceptions as lx
    for i, part in enumerate(parts):
        name, _, body = part.partition(": ")
        e = exc.get(name.strip().upper())
        if not e:
            continue
        body = lx.drop_excepted(body, e["items"])
        parts[i] = (f"{name}: {body}; " if body else f"{name}: ") + lx.note_en(name, e)
    if not parts:
        return ""
    from .prompt_formula import garment_profile
    held = any(garment_profile(conn, project_id, n) for n in (cast or []))
    return (" Identity lock — " + " | ".join(parts) + "."
            + (" The costume follows the profile above" + (" (or the OUTFIT image)" if any("OUTFIT image" in x for x in parts) else "")
               + "; any other colour word for these garments is wrong." if held else ""))


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


def chat_rewrite(runner, job, kind: str, assembled: str, images, model, limit: int = 4000) -> str:
    """D6 (cờ chat_prompts, TẮT): Claude nhìn đúng các ảnh sẽ gửi viết lại bản code ghép thành một prompt liền mạch (core/chat_prompt);
    tắt / không dùng được → bản code ghép như cũ (lý do vào diag). Module-level: works with any runner-like object (p + _diag)."""
    from . import chat_prompt
    if not chat_prompt.enabled():
        return assembled
    say = getattr(runner, "_diag_once", None) or getattr(runner, "_diag", None)
    return chat_prompt.rewrite(runner.p, job, kind, assembled, images, model=model, limit=limit,
                               say=(lambda lv, code, msg: say(job, lv, code, msg)) if say else None)


def build_image_prompt(conn, project_id: int, data: Dict, core: Optional[str] = None, fix: Optional[str] = None,
                       blocking_label: str = "Blocking", place_render: bool = False, light: str = "",
                       place_extra: Optional[List[str]] = None, camera_end: bool = False) -> Tuple[str, list]:
    """THE picture prompt of a shot (start picture and K1 end frame share it, so a safeguard added here reaches both). Returns
    (prompt, realism words removed). F1-C (09/10): assembled as named PARTS in the formula's order (docs/CONG_THUC_PROMPT_F0 mục 4,
    core/prompt_template.py): style → framing → people + action (Director text, blocking, gaze, acting, action_peak, skill phase) →
    the retry's fix → place → light → locks / rules (Character Lock, view notes, FF gore restraint) → quality close. Each part closes its
    own sentence; no age under 18 anywhere.
    place_render: the shot's own 3D render goes with the picture — the place sentence locks the background to it (F1-B) instead of the
    place's general description; the render's number is filled in by _finish_args (assets.RENDER_TAG).
    light / place_extra: the scene light sentence and the 3D spot's direction / geometry sentences (_submit_args) — placed in their
    parts instead of being glued to the end.
    10/10: the 3D stage's geometry facts (core/stage_facts, flag stage_camera + a shot with stage_camera) go right before the quality
    close; camera_end = the end frame of a moving camera."""
    from . import looks
    from . import prompt_template as pt
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    raw = data.get("image_prompt") if core is None else core
    text, removed = looks.clean_prompt(proj, raw or "")   # ff_gameplay_visual.md: these words pull the picture towards a realistic shooter
    look_quality = looks.quality_sentence(proj)
    # the look sentence says the style (and the quality): the Director's own clauses of the same words are said once, not twice
    words, quality = pt.split_director(text, drop_style=looks.of(proj) == "FF_INGAME", move_quality=bool(look_quality))
    place = assets.scene_location(conn, project_id, data)
    # Đ16v2: làm sạch riêng chữ shot gửi đi; giữ nguyên scene/Kho và phần mô tả khóa.
    from . import prop_lock
    lock_data = dict(data, image_prompt=raw or "")
    action, _ = prop_lock.clean_prompt(conn, project_id, lock_data, _action_part(data, words, blocking_label))
    fix, _ = prop_lock.clean_prompt(conn, project_id, lock_data, fix or "")
    parts = [looks.style_sentence(proj),
             framing_sentence(data),
             action,
             _prop_part(conn, project_id, data, raw),   # 12/10 (#27): the project's own gun / glue wall by name (flag project_prop_lock)
             f"Fix: {fix}" if fix else "",         # the retry's correction right after what it corrects, not at the tail
             _place_part(conn, project_id, data, place, place_render, list(place_extra or []) + [_object_scale(conn, project_id, data)]),
             light,
             _lock_part(conn, project_id, data, proj, text, fix),
             _geometry_part(conn, project_id, data, camera_end, place_render),
             pt.quality_part(look_quality, quality) if (look_quality or quality) else ""]
    prompt = pt.join(parts)
    if "Gore restraint:" in prompt:                # F1-B: "everything in focus" never reaches the hinted details
        prompt = looks.in_focus_except(prompt)
    return no_minor_age(prompt), removed


def _prop_part(conn, project_id: int, data: Dict, raw: Optional[str]) -> str:
    """12/10 (#27): 'Prop lock' — a shot saying only "assault rifle" / "glue wall" gets the project's own SKORP / Bom keo by name and
    description, in the form the shot names (core/prop_lock). '' when the flag is off (the prompt stays byte for byte)."""
    from . import prop_lock
    if not prop_lock.enabled():
        return ""
    return prop_lock.prompt_part(conn, project_id, dict(data, image_prompt=raw or ""))


def _geometry_part(conn, project_id: int, data: Dict, camera_end: bool = False, render: bool = False) -> str:
    """10/10 (#24 shot 4 + 8): the 3D stage's geometry facts of this camera (core/stage_facts) — computed by code, joined by code, not
    via the Director. Only when the stage_camera flag is on AND the shot has a stage camera; otherwise "" (the prompt stays as before).
    camera_end: the end frame of a moving camera (its end position). render: the shot's 3D render goes with the picture — without
    it the sentences never mention "the render" / its grey placeholder block (rà kỹ 10/10)."""
    from . import features, stage_facts
    if not features.on("stage_camera") or not data.get("stage_camera"):
        return ""
    return stage_facts.prompt_block(stage_facts.for_shot(conn, project_id, data, end=camera_end, render=render)["facts"])


def geometry_contradiction_notes(conn, project_id: int, data: Dict) -> List[str]:
    """Rà kỹ 10/10 (#24 shot 4 'its dark mouth facing us'): câu Director trái sự thật hình học của máy 3D → câu cảnh báo (prompt ảnh
    tự mâu thuẫn — câu máy nối ở cuối nói ngược). [] khi tắt cờ / không có stage_camera / không trái."""
    from . import features, stage_facts
    if not features.on("stage_camera") or not data.get("stage_camera"):
        return []
    facts = stage_facts.for_shot(conn, project_id, data)["facts"]
    return [f"prompt ảnh tự mâu thuẫn: câu Director \"{c['phrase']}\" trái sự thật hình học {c['fact']} — câu máy nối ở cuối nói "
            f"ngược; sửa câu Director (Kiểm tác động khâu 'cau')"
            for c in stage_facts.prompt_contradictions(data, facts)]     # 11/10: cả blocking / action_peak (cũng vào prompt ảnh)


def _action_part(data: Dict, words: str, blocking_label: str) -> str:
    """People + action: the Director's words, blocking (+ gaze), acting, the first frame mid-action, the skill phase."""
    from . import performance, skill_dossier
    from . import prompt_template as pt
    bits = [words]
    blocking = (data.get("blocking") or "").strip()
    if blocking:                                    # where each person stands/faces, so shots of one sequence agree
        bits.append(f"{blocking_label}: {blocking}")
        if _GAZE.search(blocking):                  # agent QC #8: eyes turned the wrong way (S2·4, S3·8) — the gaze is part of the shot
            bits.append("The gaze follows the blocking exactly: who looks at whom, toward frame-left or frame-right.")
    bits.append(performance.image_sentence(data))   # GĐ4: the Director's acting (director.md Đ4) at the start of the shot
    peak = str(data.get("action_peak") or "").strip().rstrip(".")
    if peak:                                        # S3.3: an action shot starts mid-movement, not from a standing pose (#8: fake running)
        bits.append(f"The first frame catches the action already under way: {peak}; mid-motion, not a standing pose.")
    if skill_dossier.enabled():                     # 30/09: the skill phase as the official video shows it + what is never drawn
        bits.append(skill_dossier.image_sentence(skill_dossier.shot_skill(data)))
    return pt.join(bits)


def _object_scales(conn, project_id: int, rows) -> List[str]:
    """F5-A: the short size sentences of a Seedance group (once each) — a broken library read never stops the clip."""
    from . import place_refs
    out = []
    for r in rows:
        try:
            out.append(place_refs.object_scale_sentence(conn, project_id, r["data"], short=True))
        except Exception:  # noqa: BLE001 - information only
            continue
    return list(dict.fromkeys(x for x in out if x))


def _object_scale(conn, project_id: int, data: Dict) -> str:
    """F5-A: real sizes of the library objects of the shot (the well of #24 is not in the 3D map) — empty when none is measured."""
    from . import place_refs
    try:
        return place_refs.object_scale_sentence(conn, project_id, data)
    except Exception:  # noqa: BLE001 - a sentence of information never stops the picture
        return ""


def _place_part(conn, project_id: int, data: Dict, place, place_render: bool, extra) -> str:
    from . import prompt_template as pt
    room = indoor_spot(conn, project_id, data)
    if room:                                       # 07/10 Khủng Long Đỏ: the place's outdoor words ("plaza, palms, sea") pulled a
        name = f" ({place['name']} map)" if place is not None else ""   # bedroom shot outside onto a balcony — what is RIGHT (L2)
        head = (f"Setting: INSIDE a room — {room}{name}. An interior with walls, ceiling and floor exactly as in the 3D render; only "
                "the room itself is visible, and the outside appears only through its windows.")
    elif place is not None and place_render:       # F1-B (#24): "grass, palms, sea" of the general words beat the render → locked to it
        head = assets.render_place_text(conn, place)
    elif place is not None:                        # B1: the place in words (+ real landmark heights), whatever pictures go
        head = assets.location_text(conn, place)
    else:
        head = ""
    return pt.join([head] + [x for x in (extra or []) if x])


def _lock_part(conn, project_id: int, data: Dict, proj, text: str, fix: Optional[str]) -> str:
    """Locks / rules: Character Lock, how each person looks from this side, and (FF) the gore restraint — judged on the Director's own
    words of the shot, not on a Lock or place text."""
    from . import looks
    from . import prompt_template as pt
    scan = " ".join(str(x or "") for x in (text, data.get("blocking"), data.get("action_peak"), fix,
                                           json.dumps(data.get("performance"), ensure_ascii=False) if data.get("performance") else ""))
    return pt.join([lock_note(conn, project_id, data.get("characters"), data), view_notes(conn, project_id, data),
                    looks.gore_sentence(proj, scan)])


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


_RENDER_LOCK = re.compile(r"Background: exactly the 3D render picture of this place" + re.escape(assets.RENDER_TAG) + r"[^.]*\.?")


def name_render(prompt: str, refs, fallback=None) -> Tuple[str, bool]:
    """F1-B: the background-lock sentence names the render by its number among the pictures REALLY sent ("Image 3"). A render dropped
    on the way (unreadable / over the limit) — F1 sửa #10: the lock sentence points at a picture that is not there and the place words
    were left out, so it is replaced by `fallback` (the place in words, assets.location_text; a callable is asked only then).
    Returns (prompt, render left unnamed)."""
    if assets.RENDER_TAG not in prompt:
        return prompt, False
    n = next((i for i, r in enumerate(refs or [], 1) if r.get("role") == "place_render"), None)
    if n:
        return prompt.replace(assets.RENDER_TAG, f" (Image {n})"), False
    words = (fallback() if callable(fallback) else fallback) or ""
    if words.strip():
        prompt = _RENDER_LOCK.sub(lambda _m: words.strip().rstrip(".") + ".", prompt, count=1)
    return prompt.replace(assets.RENDER_TAG, ""), True


def _place_words(runner, job) -> str:
    """The shot's place in words (assets.location_text) — name_render's fallback when the render picture is not sent."""
    try:
        conn = runner.p.conn
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
        place = assets.scene_location(conn, job["project_id"], json.loads((row["data"] if row else None) or "{}"))
        return assets.location_text(conn, place) if place else ""
    except Exception:  # noqa: BLE001 - no place words: the lock sentence is only left without its number (said by the caller)
        return ""


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
        layout = assets.missing_layout(self.p.conn, job["project_id"], json.loads(row["data"] or "{}"))
        if layout:
            return layout
        from . import prompt_formula             # F1 (09/10): a picture prompt that breaks the formula is not paid for
        red = prompt_formula.red_issues(self.p.conn, job["scene_id"], "image")
        return ("prompt ảnh sai công thức — sửa ở Bước 1/2: " + " · ".join(red)) if red else None

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
                                        log=self._thread_diag(job, "place_render"))
                return self._hold(job, "đang render nền 3D của cảnh (Blender, 0 USD) — sẽ tự gửi khi render xong")
            if self._stale_plates(job, rows):                # KLD-6: a render of another camera (moved spot…) — rebuilt first, 0 USD
                return self._hold(job, "đang render lại nền 3D đã cũ (chỗ đứng/góc máy đổi, 0 USD) — sẽ tự gửi khi render xong")
            held = place_refs.needs(self.data_dir, job["project_id"], job["scene_id"])
            if held:                                         # S5.7: no direction for a script-direction spot — wait, and say what to add
                self._diag(job, "error", "plate_view", held)
                return self._hold(job, f"thiếu hướng máy cho nền 3D — CẦN BẠN SỬA: {held} (sửa xong sẽ tự gửi)")
            bad = place_refs.broken(self.p.conn, self.data_dir, job["project_id"], job["scene_id"], data)
            if bad:                                          # F2 (09/10, #24 job 579): never sent without its 3D background
                idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
                why = (f"nền 3D của shot {idx['idx'] if idx else job['scene_id']} hỏng: {bad} — chọn lại góc / sửa chỗ đứng "
                       "(ảnh giữ chờ, không gửi thiếu nền)")
                self._diag(job, "error", "plate_broken", why)    # diag.record: one row per 10 minutes, a counter after
                return self._hold(job, f"CẦN BẠN SỬA: {why}")
        if scene_establish.shadow():                         # 🎓 học việc (B6 08/10): drawn apart, the shot never waits for it
            try:
                data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
                model = None
                if getattr(self.provider, "supports_model", False):
                    from . import image_models
                    model = image_models.of_project(self.p.project(job["project_id"]))
                scene_establish.step(self.p.conn, job["project_id"], data.get("story_scene"), self.provider, self.data_dir, model,
                                     trainee=True)
            except Exception as e:                       # noqa: BLE001 — học việc never breaks the real run
                import sys
                print(f"scene_establishing học việc lỗi job {job['id']}: {e}", file=sys.stderr)
        elif scene_establish.enabled():
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            model = None
            if getattr(self.provider, "supports_model", False):
                from . import image_models
                model = image_models.of_project(self.p.project(job["project_id"]))
            state = scene_establish.step(self.p.conn, job["project_id"], data.get("story_scene"), self.provider, self.data_dir, model,
                                         lambda sev, code, msg: self._diag(job, sev, code, msg))
            if state == "waiting":                           # the scene's wide establishing picture is drawn first
                return self._hold(job, "chờ ảnh toàn cảnh (establishing) của cảnh — sẽ tự gửi khi ảnh đó xong")
        if scene_storyboard.enabled() and getattr(self.provider, "supports_storyboard", False) and \
                scene_storyboard.waits(self.p.conn, self.data_dir, job["project_id"], job["scene_id"]):
            self._anchor_wait_note(job)                      # 08/10 lỗi 11: said, never a silent wait
            why = scene_storyboard.wait_reason(self.p.conn, self.data_dir, job["project_id"], job["scene_id"])
            return self._hold(job, (why or {}).get("text", "chờ ảnh neo của cảnh (storyboard)")
                              + ("" if (why or {}).get("stuck") else " — sẽ tự gửi khi ảnh neo xong"))
        proj = self.p.project(job["project_id"])
        chains = proj["storyboard_mode"] == 1
        if bool(shots.mode(proj)) and chains and shots.waits_for_previous_image(self.p.conn, job["scene_id"]):
            return self._hold(job, "chờ ảnh đã duyệt của shot trước (nối khung) — sẽ tự gửi khi bạn duyệt ảnh đó")
        from . import layout_follow                          # hộp thư 12/10 19:17 (cờ layout_from_follow): the continuity_from shot first
        if layout_follow.enabled():
            row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
            why = layout_follow.wait_reason(self.p.conn, job["project_id"], json.loads(row["data"] or "{}") if row else {})
            if why:
                return self._hold(job, why)
        return False

    def _pregen_cooling(self, job) -> bool:
        """A picture held by the package check less than PREGEN_RECHECK_S ago stays queued with its reason — no rebuild of the
        request (and no new diag row) on every heartbeat."""
        held = PREGEN_HELD.get(job["id"])
        if held and time.time() - held[1] < PREGEN_RECHECK_S:
            WAIT_REASONS[job["id"]] = held
            return True
        return False

    def _pregen(self, job, args, kwargs) -> bool:
        """#24 job 649 (11/10): the last check of the picture's package before it is paid for — every 3D background in it must be
        THIS shot's current camera (place_refs.package_problem). Otherwise ĐỎ: held with the reason (never sent, never silent)."""
        from . import place_refs
        from . import location_pack
        sent = getattr(self, "_sent", {}).get(job["id"])
        if not sent or not job["scene_id"]:
            return False
        why = place_refs.package_problem(sent, location_pack.plate_of(self.data_dir, job["project_id"], job["scene_id"]))
        if not why:
            PREGEN_HELD.pop(job["id"], None)
            return False
        line = f"CẦN BẠN SỬA: {why} — ảnh GIỮ CHỜ, không gửi (0 USD); render lại nền 3D / sửa góc máy rồi sẽ tự gửi"
        WAIT_REASONS[job["id"]] = PREGEN_HELD[job["id"]] = (line, time.time())
        self._diag_once(job, "error", "plate_package_mixed", line)
        self._sent.pop(job["id"], None)
        getattr(self, "_storyboard", {}).pop(job["id"], None)
        return True

    def _anchor_wait_note(self, job) -> None:
        """Lỗi 11 (#24): the job waits for its scene's anchor picture. When the anchor has NO picture job on its way (not queued / running),
        the wait never ends — say which shot to generate (diag, once per job; the step 2 screen reads scene_storyboard.wait_reason)."""
        try:
            reason = scene_storyboard.wait_reason(self.p.conn, self.data_dir, job["project_id"], job["scene_id"])
        except Exception:  # noqa: BLE001 - a note only, the wait itself stays
            return
        if not reason or not reason.get("stuck"):
            return
        seen = getattr(self, "_anchor_said", None)
        if seen is None:
            seen = self._anchor_said = set()
        if job["id"] in seen:
            return
        seen.add(job["id"])
        self._diag(job, "warn", "storyboard_anchor_missing", reason["text"])

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
        from . import place_refs
        render = place_refs.shot_ref(self.data_dir, job["project_id"], job["scene_id"]) if place_refs.enabled() else None
        from . import scene_establish
        from . import location_pack
        light = scene_establish.light_sentence(data)
        chosen = location_pack.script_sentence(conn, job["project_id"], data)   # S5.7: direction + extra lights of this shot
        geo = scale = ""
        if render is not None:                         # the render's real numbers (place_refs.geometry_sentence) — the place part
            place = assets.scene_location(conn, job["project_id"], data)
            entry = location_pack_entry(conn, place)
            geo = place_refs.geometry_sentence(render["_rec"], data, (entry or {}).get("sun_azimuth", 250.0))
            scale = place_refs.scale_sentence(render["_rec"], entry, data)   # F2 việc 4: measured prop sizes (empty if none)
        # F1-C: light / spot / geometry go into their parts of the formula (place → light), never glued after the quality close
        words_data, ground = self._plate_anchor_words(job, data, render)   # lỗi 1 #27 (cờ plate_anchored_image); tắt → (data, "")
        prompt, _ = build_image_prompt(conn, job["project_id"], words_data, fix=model_fix(job["retry_reason"]),
                                       place_render=render is not None, light=light or "",
                                       place_extra=([ground] if ground else []) + [chosen or "", geo or "", scale or ""])
        if "Geometry of this camera" in prompt:        # luật 1: stage_facts sentences added by code are said
            self._diag(job, "info", "stage_facts", "đã nối câu sự thật hình học của máy Sân khấu 3D (core/stage_facts) vào prompt ảnh")
            for note in geometry_contradiction_notes(conn, job["project_id"], data):   # rà kỹ 10/10: shot cũ, không change_event
                self._diag(job, "warn", "stage_facts_contradiction", note)
        if "Gore restraint:" in prompt:                # luật 1: a sentence added by code is said
            self._diag(job, "info", "gore_restraint", "dự án FF: shot có máu/vết thương/xác — đã thêm câu chỉ GỢI (bóng tối, ngoài nét, "
                       "bị che), không thấy rõ")
        proj = self.p.project(job["project_id"])
        chain = chain_previous(proj, data)
        from . import image_models
        model = image_models.of_project(proj)
        sheets = image_models.accepts_sheets(model) and getattr(self.provider, "supports_model", False)
        limit = min(image_models.max_refs(model, assets.MAX_REFERENCES), 12) if sheets else assets.MAX_REFERENCES
        keep = (1 if chain else 0) + (1 if data.get("continuity_from") is not None else 0)   # + the layout_from picture's slot
        refs = assets.scene_references(conn, job["project_id"], data,   # the previous frame keeps its slot
                                       limit=limit, reserve=keep, sheets=sheets)
        from . import scene_establish
        est = scene_establish.reference(self.data_dir, job["project_id"], data.get("story_scene"))
        if est and indoor_spot(conn, job["project_id"], data):   # an indoor shot: the 3D render of the room is the place, never the
            est = None                                           # outdoor wide picture of the scene (07/10 Khủng Long Đỏ)
        from .plate_choice import landmark_off_frame
        if est and landmark_off_frame(data):                     # 08/10 (#24 shot 4): the wide picture shows the landmark the camera
            est = None                                           # is turned away from — it pulled the tower into a reverse shot
        if est:                                        # the scene's wide establishing picture: the shared reference for the place
            refs = ([r for r in refs if r.get("role") != "location"][:max(limit - 2, 1)]
                    + [r for r in refs if r.get("role") == "location"][:1] + [est])
        if place_refs.enabled():                       # the shot's own 3D render replaces the library's place picture + real numbers
            ref = render
            if ref is not None:
                refs = place_refs.swap_in(refs, ref, limit)
                # F2 (09/10): this shot's own same-axis wide render replaces the scene's one-for-all wide picture
                refs = place_refs.add_wide(refs, place_refs.wide_for(conn, self.data_dir, job["project_id"], job["scene_id"], data), limit,
                                           reserve=keep)                   # the previous frame keeps its slot
                refs = place_refs.own_place_only(refs, ref)   # #24 job 649: locked stage camera → only its own render
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
        layout = layout_reference(self, job, data)
        if layout is not None and layout["path"] not in [r["path"] for r in refs]:   # never the same file twice
            refs = refs + [layout]
        return self._finish_args(job, prompt, refs)

    def _plate_anchor_words(self, job, data: Dict, render) -> Tuple[Dict, str]:
        """Lỗi hệ thống 1 sau #27 (cờ plate_anchored_image): (data cho prompt với image_prompt đã bỏ chữ tả nền của Đạo diễn, câu NỀN
        sinh từ plate + mốc 3D). Cờ tắt / shot không có render → (data, "") — prompt như cũ từng byte. Chữ bỏ → VÀNG; không biết mốc →
        VÀNG (không im lặng). Chỉ đổi chữ GỬI ĐI, không ghi lại scenes.data."""
        from . import plate_anchor
        if render is None or not plate_anchor.enabled():
            return data, ""
        conn = self.p.conn
        say = getattr(self, "_diag_once", self._diag)
        names = list(data.get("characters") or [])
        stripped, removed = plate_anchor.strip_scenery(data.get("image_prompt") or "", names)
        if removed:
            say(job, "warn", plate_anchor.CODE_WORDS, plate_anchor.words_note(removed))
        place = assets.scene_location(conn, job["project_id"], data)
        entry = location_pack_entry(conn, place)
        from . import place_refs
        w, h = place_refs.resolution_of(self.p.project(job["project_id"]))
        ground, notes = plate_anchor.background_sentence(render["_rec"], entry, (place or {}).get("name") or render.get("label") or "the place",
                                                         (entry or {}).get("landmark"), aspect=w / h if h else None)
        if notes:
            say(job, "warn", plate_anchor.CODE_BACKGROUND, "câu nền sinh từ plate thiếu dữ liệu: " + "; ".join(notes))
        return dict(data, image_prompt=stripped), ground

    def _finish_args(self, job, prompt: str, refs):
        """The picture job's (prompt, reference paths). Storyboard mode (feature storyboard_api, a provider that draws storyboard
        frames): the scene's shared references + the anchor frame replace the shot's own, and the storyboard fields go with the job
        (core/scene_storyboard.py, the web Weave Canvas way). Only the pictures that will really be sent are numbered in the note
        (a dropped picture used to shift "Image 2 is KELLY" onto the wrong person) — every dropped one is reported."""
        from . import features
        by_spot = features.on("anchor_by_spot")
        spot_jobs = getattr(self, "_storyboard_by_spot_jobs", set())
        if by_spot or job["id"] in spot_jobs:
            getattr(self, "_storyboard", {}).pop(job["id"], None)  # đổi nhóm/cờ; OFF chưa từng ON giữ cache cũ
        if by_spot:
            spot_jobs.add(job["id"])
            self._storyboard_by_spot_jobs = spot_jobs
        else:
            spot_jobs.discard(job["id"])  # OFF sau ON chỉ dọn một lần
        from . import image_models
        proj = self.p.project(job["project_id"])
        model = image_models.of_project(proj) if getattr(self.provider, "supports_model", False) else None
        from . import plate_anchor
        anchored = plate_anchor.enabled()
        if anchored:                                   # lỗi 1 #27: render của shot là ẢNH 1 (không bị trần số ảnh cắt, đánh số 1)
            refs = plate_anchor.plate_first(refs)
        refs, dropped = sendable_references(refs, model)
        if dropped:
            self._diag(job, "warn", "missing_reference", "ảnh tham chiếu không gửi được (bỏ khỏi yêu cầu và khỏi câu đánh số ảnh): "
                       + ", ".join(dropped))
        from . import prop_lock
        if prop_lock.enabled():
            row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
            lock_data = json.loads(row["data"] or "{}") if row else {}
            refs = prop_lock.suppress_pov_gun_refs(self.p.conn, job["project_id"], lock_data, refs)
            refs = prop_lock.prioritize_gun_refs(self.p.conn, job["project_id"], lock_data, refs,
                                                lambda ref: bool(sendable_references([ref], model)[0]))
        self._sent = getattr(self, "_sent", {})
        self._sent[job["id"]] = [{"label": r["label"], "role": r["role"], "file": os.path.basename(r["path"]),
                                  **({"plate_key": r["plate_key"]} if r.get("plate_key") else {})} for r in refs]   # KLD-6
        from . import scene_storyboard
        if scene_storyboard.enabled() and getattr(self.provider, "supports_storyboard", False):
            warning = scene_storyboard.anchor_warning(self.p.conn, self.data_dir, job["project_id"], job["scene_id"])
            if warning:
                getattr(self, "_diag_once", self._diag)(job, "warn", "storyboard_anchor_unapproved", warning)
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
                from .plate_choice import landmark_off_frame
                if landmark_off_frame(own):            # 08/10 (#24): camera turned away from the landmark — no picture showing it
                    est = None
                    shared = [r for r in shared if r.get("role") not in ("location", "landmark")]
                if est:                                # the scene's wide establishing picture: the shared reference for the place
                    shared = ([r for r in shared if r.get("role") != "location"][:6]
                              + [r for r in shared if r.get("role") == "location"][:1] + [est])
                from . import place_refs
                if place_refs.enabled():                # this frame's own 3D render replaces the library's place picture
                    own_render = place_refs.shot_ref(self.data_dir, job["project_id"], job["scene_id"])
                    shared = place_refs.swap_in(shared, own_render, 8)
                    if own_render is not None:                                # F2: + same-axis wide
                        shared = place_refs.add_wide(shared, place_refs.wide_for(self.p.conn, self.data_dir, job["project_id"],
                                                                                 job["scene_id"], own), 8)
                        shared = place_refs.own_place_only(shared, own_render)   # #24 job 649: locked stage camera → one plate
                from . import skill_dossier
                if skill_dossier.enabled():            # the skill frame of THIS shot rides with the shared references
                    row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
                    hit = skill_dossier.shot_skill(json.loads(row["data"] or "{}")) if row else None
                    shared = skill_dossier.add_reference(shared, skill_dossier.reference(hit), 8)
                from . import prop_lock
                shared = prop_lock.suppress_pov_gun_refs(self.p.conn, job["project_id"], own, shared)
                if anchored:                           # lỗi 1 #27: render của shot là ảnh 1 của storyboard (image_mapping theo thứ tự này)
                    shared = plate_anchor.plate_first(shared)
                shared, dropped = sendable_references(shared, model)     # before the mapping text is built from the list
                if dropped:
                    self._diag(job, "warn", "missing_reference", "ảnh tham chiếu storyboard không gửi được: " + ", ".join(dropped))
                shared = prop_lock.prioritize_gun_refs(self.p.conn, job["project_id"], own, shared,
                                                      lambda ref: bool(sendable_references([ref], model)[0]))
                previous = None
                srow = self.p.conn.execute("SELECT idx, data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
                sdata = json.loads(srow["data"] or "{}") if srow else {}
                if srow and chain_previous(proj, sdata):    # "always chain the previous shot" holds in storyboard mode too (07/10)
                    prev = previous_frame_job(self.p.conn, job["project_id"], srow["idx"], sdata.get("sequence"))
                    if prev is not None:
                        previous = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{prev['id']}.png")
                mark = None
                if scene_storyboard.turned_away(g, job["scene_id"]):   # lỗi D 08/10: the landmark's name for the away sentence
                    try:
                        mark = (location_pack_entry(self.p.conn, assets.scene_location(self.p.conn, job["project_id"], own))
                                or {}).get("landmark")
                    except Exception:  # noqa: BLE001 - no library tables (old test data): the generic words stay
                        mark = None
                layout = layout_reference(self, job, sdata)
                fields = scene_storyboard.job_fields(self.p.conn, self.data_dir, job["project_id"], job["scene_id"], shared, job["id"],
                                                     previous=previous, landmark=mark,
                                                     layout=layout["path"] if layout else None,
                                                     layout_label=layout["label"] if layout else None)
                if fields is not None and fields.get("anchor_skipped"):
                    view = own.get("plate_view")
                    view = view.get("background") if isinstance(view, dict) else view
                    if scene_storyboard.turned_away(g, job["scene_id"]):
                        why = f"shot quay khỏi mốc (plate_view {view})"
                        extra = ", thêm câu 'mốc không trong khung'"
                    elif scene_storyboard.other_spot(g, job["scene_id"]):   # rà 12/10: the reason said, not "quay khỏi mốc"
                        why = (f"shot đứng chỗ khác shot neo (plate_spot {own.get('plate_spot')} ≠ "
                               f"{g['anchor']['data'].get('plate_spot')})")
                        extra = ", thêm câu 'máy riêng'"
                    else:
                        why, extra = "shot có máy Sân khấu 3D riêng", ", thêm câu 'máy riêng'"
                    self._diag(job, "info", "storyboard_anchor_skipped",
                               f"{why}: KHÔNG gửi ảnh neo khung 1 (shot {g['anchor']['idx']}, có {mark or 'mốc'}) — chỉ ảnh nhân "
                               f"vật/trang phục + render 3D của shot, phiên storyboard riêng{extra}")
                if fields is not None:
                    refs = fields["refs"]
                    prompt = prompt.rstrip() + fields.get("cast_note", "")
                    self._storyboard = getattr(self, "_storyboard", {})
                    self._storyboard[job["id"]] = fields["storyboard"]
                    self._sent = getattr(self, "_sent", {})
                    self._sent[job["id"]] = [{"label": r["label"], "role": r.get("role", ""), "file": os.path.basename(r["path"]),
                                              **({"plate_key": r["plate_key"]} if r.get("plate_key") else {})}
                                             for r in refs] + [{"label": "storyboard", "role": "storyboard",
                                                                "file": fields["storyboard"]["storyboard_id"]}]
        if hasattr(self, "_diag"):                     # luật 1 (#24 shot 9, 11/10): a pictured person of the frame left out is said
            say = getattr(self, "_diag_once", self._diag)   # args are built every poll while the job waits: said once per job
            try:
                from . import scene_storyboard as _sb
                row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
                for who in (_sb.cast_missing(self.p.conn, job["project_id"], json.loads(row["data"] or "{}"), refs) if row else []):
                    say(job, "warn", "missing_reference",
                               f"nhân vật {who} có trong khung và có ảnh mẫu trong Kho nhưng gói gửi KHÔNG có ảnh nào của {who} — "
                               "model vẽ theo chữ, dễ lệch thiết kế (trần số ảnh / bộ lọc gói)")
            except Exception as e:  # noqa: BLE001 - a check must never stop the job; its failure is said
                say(job, "warn", "missing_reference", f"không kiểm được ảnh mẫu nhân vật trong gói: {type(e).__name__}: {e}")
        from . import prop_lock
        if prop_lock.enabled():
            row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
            lock_data = json.loads(row["data"] or "{}") if row else {}
            pov_issue = prop_lock.pov_gun_issue(self.p.conn, job["project_id"], lock_data)
            if pov_issue:
                getattr(self, "_diag_once", self._diag)(job, "warn", "prop_pov_gun", pov_issue["msg"])
        prompt, lost = name_render(prompt, refs, fallback=lambda: _place_words(self, job))
        if anchored:                                   # rà gộp lỗi 1: câu nền "as Image 1 shows it" theo gói THẬT (render rơi → bỏ câu)
            prompt = plate_anchor.fit_ground(prompt, refs)
        from . import prop_lock                        # rà 12/10: no "as its reference picture shows" for a prop picture not sent
        if prop_lock.enabled():                        # rà 12/10: one note per job (not every poll), info only for a sent package
            missing = prop_lock.missing_refs(self.p.conn, job["project_id"], lock_data, refs)
            if missing or refs:
                getattr(self, "_diag_once", self._diag)(job, "warn" if missing else "info", "prop_reference_dropped",
                    f"job {job['id']}: ảnh khóa KHÔNG có trong gói gửi cuối (trần ảnh / bộ lọc): " + ", ".join(missing)
                    + " — sửa gói tham chiếu trước gen; model chỉ nhận mô tả chữ" if missing else f"job {job['id']}: gói gửi cuối không thiếu ảnh khóa")
        prompt = prop_lock.match_refs(prompt, refs)
        prompt = _skill_object_guard(self, job, prompt, "ảnh")          # lỗi hệ thống 3 (cờ skill_object_guard)
        if lost and hasattr(self, "_diag"):
            self._diag(job, "warn", "missing_reference", "ảnh render 3D của shot không gửi được — bỏ câu khóa nền theo render, quay về "
                                                         "câu địa điểm bằng chữ")
        if refs:                                       # the chosen resources' pictures go with the prompt (image-to-image)
            text = assets.reference_note(refs) + "Scene: " + prompt
            if anchored:                               # lỗi 1 #27: "giữ đúng nền / kiến trúc / bố cục của ảnh 1" đứng đầu
                text = plate_anchor.with_keep(text, refs)
            text = chat_rewrite(self, job, "image", text, [(f"Image {i}: {r['label']} ({r['role']})", r["path"])
                                                          for i, r in enumerate(refs, 1)], model)
            return (text, [r["path"] for r in refs])
        return (chat_rewrite(self, job, "image", prompt, [], model),)

    def _after_download(self, job, path: str) -> str:
        """After the picture arrives: how well it kept the 3D render of the place (place_render_refs) and QC layer 0. S14.9: the
        location-pack green-screen composite (flag location_plates) was removed."""
        from . import place_refs
        if place_refs.enabled():                   # place_render_refs: did the model keep the place of the 3D render? (measured, said)
            # KLD-17: measured against the render of the spot in the PLAN (not a background the plan left), noted only (info), kept
            if place_refs.shot_ref(self.data_dir, job["project_id"], job["scene_id"]) is not None:
                sev, words = place_refs.measure(self.p.conn, self.data_dir, job["project_id"], job["scene_id"], job["id"], path,
                                                place_refs.resolution_of(self.p.project(job["project_id"])))
                self._diag(job, sev, "place_match", words)
            from . import camera_plan, plate_anchor
            if plate_anchor.enabled() and place_refs.shot_ref(self.data_dir, job["project_id"], job["scene_id"]) is not None:
                # lỗi 1 #27: shot có render → kiểm sau vẽ ĐỎ/VÀNG (không cần camera_plan; không đo được → VÀNG, không im lặng)
                from . import plate_layout_qc
                try:
                    got = plate_layout_qc.check_strict(self.p.conn, self.data_dir, job["project_id"], job["scene_id"], job["id"], path,
                                                       place_refs.resolution_of(self.p.project(job["project_id"])))
                    self._diag(job, got[0], plate_layout_qc.CODE, got[1])
                except Exception as e:  # noqa: BLE001 - a check must never lose the paid picture
                    self._diag(job, "warn", plate_layout_qc.CODE, f"VÀNG: không so được bố cục nền với render: {type(e).__name__}: {e}")
            elif camera_plan.enabled():            # G0 mục 5: layout of the picture vs the render (code, 0 USD) — marked, never redrawn
                from . import plate_layout_qc
                try:
                    got = plate_layout_qc.check_job(self.p.conn, self.data_dir, job["project_id"], job["scene_id"], job["id"], path,
                                                    place_refs.resolution_of(self.p.project(job["project_id"])))
                    if got:
                        self._diag(job, got[0], plate_layout_qc.CODE, got[1])
                except Exception as e:  # noqa: BLE001 - a check must never lose the paid picture
                    self._diag(job, "warn", plate_layout_qc.CODE, f"không so được bố cục nền với render: {type(e).__name__}: {e}")
        from . import qc_scene
        if qc_scene.shadow():                      # 🎓 học việc (B3 08/10): check, record the decision only — no layer0.json, no redraw
            self._trainee_layer0(job, path)
        elif qc_scene.enabled():                   # QC layer 0: code checks as the picture arrives (free)
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

    def _trainee_layer0(self, job, path: str) -> None:
        """🎓 scene_qc học việc: what layer 0 WOULD do (redraw / flag / pass) goes to trainee_log only — never shown before the person
        decides, never acts. A failure here must not touch the picture."""
        from . import qc_scene, trainee
        try:
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}")
            size: Dict = {}
            flags = qc_scene.check_frame(path, data, assets.flat_place(self.p.conn, job["project_id"], data), measure=size)
            flags = qc_scene.for_trainee(flags)     # KLD-16: a measured size is only a flag in học việc (SIZE_FROM not calibrated)
            sev = {f.get("severity") for f in flags}
            decision = "redraw" if "redraw" in sev else ("flag" if flags else "pass")
            trainee.record(self.p.conn, "scene_qc", job["project_id"], f"job:{job['id']}", decision,
                           would_do={"fix": " ".join(f.get("fix", "") for f in flags if f.get("severity") == "redraw"),
                                     "problems": [f.get("problem", "") for f in flags]},
                           detail={"size": size} if size else None,     # the (measured, planned) pair → qc_scene.size_calibration
                           scene_id=job["scene_id"], job_id=job["id"])
        except Exception as e:                       # noqa: BLE001 — học việc never breaks the real run
            import sys
            print(f"scene_qc học việc lỗi job {job['id']}: {e}", file=sys.stderr)

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
