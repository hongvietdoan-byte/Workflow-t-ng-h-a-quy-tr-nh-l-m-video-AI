import os
import sqlite3
from datetime import datetime, timezone
from typing import Mapping, Optional

from .states import REVIEWABLE, InvalidTransition, JobState, check_transition


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hard_floors(kind: str = "image") -> dict:
    """{criterion: minimum score} of the QC checklist's blocking criteria (data/qc_checklist.json `hard_floor`)."""
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "data", "qc_checklist.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    items = data.get("video_criteria" if kind == "video" else "criteria") or []
    return {c["key"]: float(c["hard_floor"]) for c in items if isinstance(c.get("hard_floor"), (int, float))}


def hard_failures(scores: Mapping[str, float], kind: str = "image") -> list:
    """Blocking criteria scored below their floor, as 'criterion 0.40 < 0.60'."""
    floors = hard_floors(kind)
    return [f"{k} {v:.2f} < {floors[k]:.2f}" for k, v in scores.items() if k in floors and v < floors[k]]


AUTO_RETRY_CAP = 2          # automatic (QC) retries per picture/clip — user decision 2026-09-24; people may retry more by hand
PLAIN_RESEND = "gửi lại nguyên đầu vào"
"""retry_reason prefix of a plain resend after a provider failure (same input, nothing to fix): a note for people, NEVER sent to a model
(core.runner.model_fix). Only provider/transient failures are resent this way — a picture/clip that came out wrong needs a fix."""


def _combine_fix(previous: Optional[str], new: str) -> str:
    """The fix sentences for the next try: this QC's issues plus the one before (a fix that worked must not be lost next time)."""
    from .runner import RESEND_NOTE
    parts = [p for p in (previous or "", new or "") if p and not p.startswith(RESEND_NOTE) and not p.startswith("QC ")
             and not p.startswith(PLAIN_RESEND)]
    seen, out = set(), []
    for p in parts:
        if p.strip() not in seen:
            seen.add(p.strip())
            out.append(p.strip().rstrip("."))
    return (". Also: ".join(out[-2:]) + ".")[:700] if out else new

def cheap_while_testing(conn, project_id: int) -> bool:
    """A project made while a budget test round is on (core.budget enabled) starts in the cheap test mode (test_quality = 1: low
    picture resolution, 720p / Kling std / Seedance Fast clips) — the user: "chỉ cần test hiệu quả". Returns True when switched on."""
    try:
        from . import budget
        if not budget.get(conn)["enabled"]:
            return False
        conn.execute("UPDATE projects SET test_quality=1 WHERE id=?", (project_id,))
        conn.commit()
        return True
    except Exception:  # noqa: BLE001 - an old database without the column / settings table keeps the normal mode
        return False


class PipelinePaused(Exception):
    pass


class Pipeline:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.actor: Optional[str] = None   # who is working (dashboard user name); stamped on the jobs created through this object

    # ---- projects / scenes / jobs -------------------------------------
    def create_project(self, name: str, operating_mode: str = "human_qc",
                       threshold: float = 0.85, max_retry: int = 3, created_by: Optional[str] = None,
                       aspect: Optional[str] = None, genre: Optional[str] = None, model_priority: Optional[str] = None,
                       game: Optional[str] = None) -> int:
        """aspect / genre / model_priority left None keep the v1 behaviour (the dashboard sets them for new projects).
        The id is never one a deleted project used (its spend history, outputs and folder keep that id)."""
        used = [self.conn.execute(sql).fetchone()[0] or 0 for sql in (
            "SELECT MAX(id) FROM projects", "SELECT MAX(project_id) FROM usage_events", "SELECT MAX(deleted_project_id) FROM usage_events",
            "SELECT MAX(project_id) FROM outputs",
            "SELECT MAX(project_id) FROM diag_events")]
        cur = self.conn.execute(
            "INSERT INTO projects (id, name, operating_mode, qc_auto_pass_threshold, max_retry_count, created_at, created_by,"
            " aspect, genre, genre_locked, model_priority)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)", (max(used) + 1, name, operating_mode, threshold, max_retry, _now(), created_by,
                                                aspect, genre, 1 if genre else 0, model_priority))
        if game:
            self.conn.execute("UPDATE projects SET game=? WHERE id=?", (game, cur.lastrowid))
        self.conn.commit()
        cheap_while_testing(self.conn, cur.lastrowid)
        return cur.lastrowid

    def set_project_field(self, project_id: int, field: str, value) -> None:
        """Plain v2 project settings (aspect, genre, model_priority, qc_video, render_settings, qc_policy, autopilot_gates, pilot)."""
        allowed = {"aspect", "genre", "genre_locked", "model_priority", "qc_video", "render_settings", "qc_policy",
                   "autopilot_gates", "autopilot_saved_cfg", "pilot", "shot_mode", "style_profile", "test_quality", "look",
                   "director_raw", "director_intent_raw", "image_model", "dialogue_trim"}
        if field not in allowed:
            raise ValueError(f"unknown project setting '{field}'")
        self.conn.execute(f"UPDATE projects SET {field}=? WHERE id=?", (value, project_id))
        self.conn.commit()

    def project(self, project_id: int) -> sqlite3.Row:
        return self.conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()

    def delete_project(self, project_id: int, data_dir: Optional[str] = None) -> None:
        """Remove a project with its scenes, jobs, results and own assets. Spend history (usage_events) is kept, the project id moved to
        `deleted_project_id` (new projects never reuse it); the files are parked in <data>/_deleted for the trash retention period."""
        from . import assets
        c = self.conn
        jobs = "(SELECT id FROM jobs WHERE project_id=?)"
        c.execute(f"UPDATE usage_events SET job_id=NULL WHERE job_id IN {jobs}", (project_id,))
        c.execute("UPDATE usage_events SET deleted_project_id=project_id, project_id=NULL WHERE project_id=?", (project_id,))
        for table in ("job_events", "qc_results", "review_log", "content_moderation_failures"):
            c.execute(f"DELETE FROM {table} WHERE job_id IN {jobs}", (project_id,))
        c.execute("UPDATE jobs SET parent_job_id=NULL WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM jobs WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM motion_prompts WHERE scene_id IN (SELECT id FROM scenes WHERE project_id=?)", (project_id,))
        for table in ("scenes", "story_scenes", "characters", "project_assets", "outputs", "diag_events"):
            c.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
        for r in c.execute("SELECT id FROM assets WHERE project_id=?", (project_id,)).fetchall():
            assets.delete(c, r["id"])
        c.execute("DELETE FROM projects WHERE id=?", (project_id,))
        c.commit()
        if data_dir:
            from .trash import park_project_folder
            park_project_folder(data_dir, project_id)

    def set_mode(self, project_id: int, mode: str) -> None:
        self.conn.execute("UPDATE projects SET operating_mode=? WHERE id=?", (mode, project_id))
        self.conn.commit()

    def set_threshold(self, project_id: int, threshold: float) -> None:
        self.conn.execute("UPDATE projects SET qc_auto_pass_threshold=? WHERE id=?", (threshold, project_id))
        self.conn.commit()

    def set_review_floor(self, project_id: int, floor: Optional[float]) -> None:
        """Auto mode 'review zone': scores in [floor, threshold) wait for a human instead of auto-rejecting.
        None disables the zone (below threshold = auto-reject)."""
        self.conn.execute("UPDATE projects SET qc_review_floor=? WHERE id=?", (floor, project_id))
        self.conn.commit()

    def set_reject_floor(self, project_id: int, floor: Optional[float]) -> None:
        """Images scoring below this are rejected automatically in BOTH modes (and a new one is queued).
        None disables it."""
        self.conn.execute("UPDATE projects SET qc_reject_floor=? WHERE id=?", (floor, project_id))
        self.conn.commit()

    def set_video_audio(self, project_id: int, on: bool) -> None:
        """Ask the video model to generate its own audio track (speech/ambience; Kling `sound`, Seedance
        `generate_audio`). Off by default: it may change the price and needs dialogue written into the prompt."""
        self.conn.execute("UPDATE projects SET video_audio=? WHERE id=?", (1 if on else 0, project_id))
        self.conn.commit()

    def set_max_retry(self, project_id: int, max_retry: int) -> None:
        """How many automatic re-gens a rejected job gets before it is escalated to a human, unfixed."""
        self.conn.execute("UPDATE projects SET max_retry_count=? WHERE id=?", (max_retry, project_id))
        self.conn.commit()

    def set_storyboard_mode(self, project_id: int, on: bool) -> None:
        """Deepix has no scriptable Storyboard tool (web UI only) — this is the workaround: when on, each scene's
        image generation also gets the PREVIOUS scene's approved image as an extra reference (image-to-image),
        so style/lighting/palette carry over the way a real storyboard would, without a Storyboard API to call."""
        self.conn.execute("UPDATE projects SET storyboard_mode=? WHERE id=?", (1 if on else 0, project_id))
        self.conn.commit()

    def set_motion_ref_video(self, scene_id: int, path: Optional[str], refer_type: str = "feature") -> None:
        """A local video the generator copies MOTION from for this scene (never appearance — that still comes only
        from the approved first-frame image / Character Bible). `refer_type`: "feature" copies the motion into a new
        clip (default), "base" edits the given clip instead — only meaningful on Kling. `path=None` clears it."""
        self.conn.execute("UPDATE motion_prompts SET ref_video_path=?, ref_video_type=? WHERE scene_id=?",
                          (path, refer_type, scene_id))
        self.conn.commit()

    def set_script_text(self, project_id: int, text: str) -> None:
        self.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (text, project_id))
        self.conn.commit()

    def add_scene_next(self, project_id: int, title: str = "") -> int:
        """Append an empty scene after the last one (for scripts the parser could not split). Returns its idx."""
        idx = (self.conn.execute("SELECT COALESCE(MAX(idx),0) m FROM scenes WHERE project_id=?",
                                 (project_id,)).fetchone()["m"]) + 1
        self.create_scene(project_id, idx, title or f"CẢNH {idx}")
        return idx

    def delete_scene(self, project_id: int, idx: int) -> None:
        """Remove a scene that has no jobs yet (a scene with images/videos must be handled through its jobs)."""
        row = self.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (project_id, idx)).fetchone()
        if row is None:
            raise KeyError(f"scene {idx} does not exist")
        if self.conn.execute("SELECT 1 FROM jobs WHERE scene_id=?", (row["id"],)).fetchone():
            raise ValueError(f"cảnh {idx} đã có ảnh/video nên không xóa được; hãy loại các bản đã gen trước")
        self.conn.execute("DELETE FROM motion_prompts WHERE scene_id=?", (row["id"],))
        self.conn.execute("DELETE FROM scenes WHERE id=?", (row["id"],))
        self.conn.commit()

    def reopen_approved(self, job_id: int, note: Optional[str] = None, respawn: bool = True, fix: Optional[str] = None) -> str:
        """The user changed their mind about an approved IMAGE: reject it and (by default) queue a new one.
        Videos already made from it are not touched. `fix`: the words the model gets (English); None = the person's `note` itself,
        "" = nothing (the input already changed — e.g. the scene was edited — so a Vietnamese system note must not reach the model)."""
        job = self.job(job_id)
        if job["type"] != "image_gen":
            raise ValueError("only approved images can be reopened")
        if self.state(job_id) != JobState.APPROVED:
            raise InvalidTransition(f"job {job_id} is {self.state(job_id).value}, not approved")
        self._log_review(job_id, "user", "reject", note or "bỏ duyệt")
        self.transition(job_id, JobState.REJECTED, actor="user", note=note or "bỏ duyệt")
        if respawn:  # a fresh job, not an automatic retry: a user asking for another take is not capped by max_retry_count
            self._insert_job(job["project_id"], job["scene_id"], "image_gen", parent_job_id=job_id,
                             retry_count=0, retry_reason=note if fix is None else (fix.strip() or None))
        return "rejected"

    def restart_job(self, job_id: int) -> int:
        """Escalated job (retries used up): start the scene's image/video over with a fresh job (retry count 0).
        Without this an escalated scene would stay stuck in 'needs_attention'. Returns the new job id."""
        job = self.job(job_id)
        if not job["escalated"]:
            raise InvalidTransition(f"job {job_id} is not escalated")
        state = self.state(job_id)
        if state == JobState.FAILED:
            self.transition(job_id, JobState.RETRYABLE, note="restart")
            self.transition(job_id, JobState.CANCELLED, note="restart")
        elif state not in (JobState.REJECTED, JobState.CANCELLED):
            raise InvalidTransition(f"job {job_id} is {state.value}, cannot restart")
        self.conn.execute("UPDATE jobs SET escalated=0 WHERE id=?", (job_id,))
        if not self.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND escalated=1", (job["scene_id"],)).fetchone():
            self.conn.execute("UPDATE scenes SET state='ready' WHERE id=? AND state='needs_attention'", (job["scene_id"],))
        self.conn.commit()
        return self.create_job(job["scene_id"], job["type"])

    def set_game(self, project_id: int, game: str) -> None:
        """Game the characters belong to (FF has the signed copyright agreement for Seedance subjects)."""
        self.conn.execute("UPDATE projects SET game=? WHERE id=?", (game, project_id))
        self.conn.commit()

    def set_use_subjects(self, project_id: int, on: bool) -> None:
        """Attach the active Seedance subjects of a scene's characters to its video requests (Seedance only)."""
        self.conn.execute("UPDATE projects SET use_subjects=? WHERE id=?", (1 if on else 0, project_id))
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
        who = self.actor
        if who is None and parent_job_id is not None:   # a retry made by the system belongs to whoever started the original
            row = self.conn.execute("SELECT created_by FROM jobs WHERE id=?", (parent_job_id,)).fetchone()
            who = row["created_by"] if row else None
        cur = self.conn.execute(
            "INSERT INTO jobs (project_id, scene_id, type, state, parent_job_id, retry_count,"
            " retry_reason, created_at, updated_at, created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (project_id, scene_id, job_type, JobState.QUEUED.value, parent_job_id, retry_count,
             retry_reason, now, now, who))
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

    def retry(self, job_id: int, reason: Optional[str] = None, fix: Optional[str] = None) -> Optional[int]:
        """failed -> retryable -> new queued job (parent link). Returns None if escalated.
        `reason` is for people (job history). Without `fix` this is a plain resend of the same input — honest only after a provider /
        transient failure — and nothing extra reaches the model (retry_reason = PLAIN_RESEND…); `fix` (English, e.g. the person's
        own sentence) is what the model gets on the next try."""
        if self.state(job_id) != JobState.FAILED:
            raise InvalidTransition(f"job {job_id} is {self.state(job_id).value}, only failed jobs can be retried")
        if self._retries_exhausted(self.job(job_id)):
            self._escalate(self.job(job_id))
            return None
        self.transition(job_id, JobState.RETRYABLE, note=reason)
        fix = (fix or "").strip()
        carried = fix or (PLAIN_RESEND + (f" ({reason})" if reason else ""))
        return self._spawn_retry(job_id, carried, close_old=JobState.CANCELLED)

    def resend(self, job_id: int, reason: str) -> int:
        """failed -> retryable -> cancelled, and the SAME attempt queued again (retry count unchanged): the provider never created the
        task, so this is not a new try and must not use up max_retry_count. Returns the new job id."""
        job = self.job(job_id)
        self.transition(job_id, JobState.RETRYABLE, note=reason)
        self.transition(job_id, JobState.CANCELLED, note="gửi lại (nhà cung cấp không tạo task)")
        return self._insert_job(job["project_id"], job["scene_id"], job["type"], parent_job_id=job_id,
                                retry_count=job["retry_count"], retry_reason=reason)

    # ---- QC / review ---------------------------------------------------
    def set_qc_autofix(self, project_id: int, on: bool) -> None:
        """On: a picture the QC agent finds faulty is regenerated automatically (its issues go into the retry prompt) up to
        max_retry_count times; only a picture that passes, or that is still faulty after the last try, reaches the person."""
        self.conn.execute("UPDATE projects SET qc_autofix=? WHERE id=?", (1 if on else 0, project_id))
        self.conn.commit()

    def apply_qc(self, job_id: int, scores: Mapping[str, float], issues: Optional[str] = None, autofix: bool = False) -> str:
        """... Returns 'already_processed' instead of raising when the picture was already judged by another check in the
        meantime (the automatic background check and a manual click can land on the same picture)."""
        if self.state(job_id) != JobState.SUCCEEDED:
            return "already_processed"
        """Record per-criterion scores, then decide per project operating_mode.

        Returns 'approved', 'rejected', 'escalated' or 'pending_review'.
        `issues` (concrete defects found by the QC agent) is appended to the notes, so an automatic reject
        feeds them into the retry prompt.
        """
        job = self.job(job_id)
        proj = self.project(job["project_id"])
        threshold = proj["qc_auto_pass_threshold"]
        overall = sum(scores.values()) / len(scores)
        hard = hard_failures(scores, "video" if job["type"] == "video_gen" else "image")
        fix = (issues or "").strip()             # the QC's own fix sentences (English, for the model): what a retry changes
        if hard:                                  # a wrong face / broken hands cannot be averaged away by good lighting
            issues = ("Tiêu chí chặn cứng dưới mức sàn: " + ", ".join(hard) + (f". {issues}" if issues else ""))
        suffix = f" — {issues}" if issues else ""
        passed = overall >= threshold and not hard
        auto = proj["operating_mode"] == "auto"
        floor = proj["qc_review_floor"]
        review_zone = auto and not passed and floor is not None and overall >= floor
        reject_floor = proj["qc_reject_floor"]
        too_low = reject_floor is not None and overall < reject_floor
        for criterion, score in scores.items():
            self.conn.execute(
                "INSERT INTO qc_results (job_id, criterion, score, threshold_at_time, auto_decision)"
                " VALUES (?,?,?,?,?)",
                (job_id, criterion, score, threshold,
                 ("fail" if too_low else "pass" if passed else "review" if review_zone else "fail") if auto
                 else ("fail" if too_low else None)))
        self.conn.commit()
        hold = None if passed else self._no_auto_retry(job, scores, threshold, fix)
        if too_low and not (autofix and not auto):  # far below the bar: not worth a human's time (with auto-fix on, the fix branch below handles it)
            if hold:
                return self._hold(job_id, f"QC {overall:.2f} < mức tối thiểu {reject_floor} — {hold}{suffix}")
            return self.reject(job_id, "ai_agent", f"QC {overall:.2f} < mức tối thiểu {reject_floor}{suffix}", fix=fix)
        if not auto:
            if autofix and not passed:
                if self._retries_exhausted(job) or hold:  # F5: no paid retry with the same input — keep it for the person, flagged
                    return self._hold(job_id, f"QC {overall:.2f} < {threshold} — " + (hold or f"sau {job['retry_count']} lần tự sửa")
                                      + f" — cần bạn xem{suffix}")
                self.transition(job_id, JobState.PENDING_REVIEW, actor="ai_agent", note=f"QC {overall:.2f} < {threshold}, tự sửa{suffix}")
                self.reject(job_id, "ai_agent", f"QC {overall:.2f} < {threshold}{suffix}", fix=fix)   # the new job's prompt carries the fix
                return "auto_fix"
            self.transition(job_id, JobState.PENDING_REVIEW, actor="ai_agent",
                            note=f"QC {overall:.2f} (suggestion only){suffix}")
            return "pending_review"
        if passed:
            self.approve(job_id, "ai_agent", f"QC {overall:.2f} >= {threshold}")
            return "approved"
        if review_zone:
            self.transition(job_id, JobState.PENDING_REVIEW, actor="ai_agent",
                            note=f"QC {overall:.2f} in review zone [{floor}, {threshold}){suffix}")
            return "pending_review"
        if hold:
            return self._hold(job_id, f"QC {overall:.2f} < {threshold} — {hold}{suffix}")
        return self.reject(job_id, "ai_agent", f"QC {overall:.2f} < {threshold}{suffix}", fix=fix)

    def _no_auto_retry(self, job, scores: Mapping[str, float], threshold: float, fix: str) -> Optional[str]:
        """F5 (user decision 2026-09-24): an automatic retry only when its input changes, at most AUTO_RETRY_CAP times per shot,
        and never a third time for the same fault. Returns why not (Vietnamese, for the person), or None."""
        if not fix:
            return "QC không nêu lỗi cụ thể để sửa — gen lại sẽ gửi y hệt đầu vào (không tự gen lại)"
        if job["retry_count"] >= AUTO_RETRY_CAP:
            return f"đã tự gen lại {job['retry_count']} lần (tối đa {AUTO_RETRY_CAP})"
        floors = hard_floors("video" if job["type"] == "video_gen" else "image")
        failing = {k for k, v in scores.items() if v < threshold or (k in floors and v < floors[k])}
        if job["parent_job_id"] and failing:
            before = {r["criterion"] for r in self.conn.execute(
                "SELECT criterion FROM qc_results WHERE job_id=? AND score < threshold_at_time", (job["parent_job_id"],))}
            if before and failing <= before:
                return ("cùng lỗi lặp lại sau khi sửa (" + ", ".join(sorted(failing)) + ") — cần sửa lớp gốc (Bible/ảnh tham chiếu/"
                        "prompt/khung cắt) thay vì gen lại")
        return None

    def _hold(self, job_id: int, note: str) -> str:
        self.transition(job_id, JobState.PENDING_REVIEW, actor="ai_agent", note=note)
        self.conn.execute("UPDATE jobs SET escalated=1 WHERE id=?", (job_id,))
        self.conn.commit()
        return "needs_review"

    def approve(self, job_id: int, reviewer_type: str = "user", note: Optional[str] = None) -> None:
        self._require_reviewable(job_id)
        self._log_review(job_id, reviewer_type, "approve", note)
        self.transition(job_id, JobState.APPROVED, actor=reviewer_type, note=note)

    def reject(self, job_id: int, reviewer_type: str = "user", note: Optional[str] = None,
               respawn: bool = True, fix: Optional[str] = None) -> str:
        """Reject and spawn a retry job (unless respawn=False = plain delete); escalate when
        max_retry_count is exceeded."""
        self._require_reviewable(job_id)
        self._log_review(job_id, reviewer_type, "reject", note)
        self.transition(job_id, JobState.REJECTED, actor=reviewer_type, note=note)
        if not respawn:
            return "rejected"
        # W4: the model gets only the fix sentences (the person's note, or the QC's issues added to the earlier fixes) — never the
        # score line or the Vietnamese note meant for people
        reason = note if fix is None else _combine_fix(self.job(job_id)["retry_reason"], fix)
        new_id = self._spawn_retry(job_id, reason, auto=reviewer_type == "ai_agent")
        return "rejected" if new_id else "escalated"

    def keepable_rejected(self, scene_id: int, kind: str = "video_gen"):
        """The last result the QC agent rejected for this scene, when its file is still the scene's latest result (no later job
        made a file, none is being made) — the person may keep it instead of paying for another take. Row or None."""
        row = self.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type=? AND state='rejected' AND result_path IS NOT NULL"
                                " ORDER BY id DESC LIMIT 1", (scene_id, kind)).fetchone()
        if row is None or not os.path.exists(row["result_path"]):
            return None
        if self.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type=? AND id>? AND (result_path IS NOT NULL OR state='running')",
                             (scene_id, kind, row["id"])).fetchone():
            return None
        last = self.conn.execute("SELECT reviewer_type FROM review_log WHERE job_id=? ORDER BY id DESC LIMIT 1", (row["id"],)).fetchone()
        return row if last is not None and last["reviewer_type"] == "ai_agent" else None

    def keep_rejected(self, job_id: int, note: Optional[str] = None) -> None:
        """The person overrides the QC agent: the rejected result is approved as it is and the takes queued after it are dropped."""
        job = self.job(job_id)
        keep = self.keepable_rejected(job["scene_id"], job["type"])
        if keep is None or keep["id"] != job_id:
            raise InvalidTransition(f"job {job_id} cannot be kept (not the scene's last QC-rejected result with its file)")
        for later in self.conn.execute("SELECT id, state FROM jobs WHERE scene_id=? AND type=? AND id>?",
                                       (job["scene_id"], job["type"], job_id)).fetchall():
            state = JobState(later["state"])
            if state == JobState.FAILED:
                self.transition(later["id"], JobState.RETRYABLE, note="giữ bản QC đã loại")
                state = JobState.RETRYABLE
            if state in (JobState.QUEUED, JobState.RETRYABLE):
                self.transition(later["id"], JobState.CANCELLED, actor="user", note="giữ bản QC đã loại")
            self.conn.execute("UPDATE jobs SET escalated=0 WHERE id=?", (later["id"],))
        self.conn.execute("UPDATE scenes SET state='ready' WHERE id=? AND state='needs_attention'", (job["scene_id"],))
        self._log_review(job_id, "user", "approve", note or "giữ bản QC đã loại")
        self.transition(job_id, JobState.APPROVED, actor="user", note=note or "giữ bản QC đã loại")

    def _require_reviewable(self, job_id: int) -> None:
        if self.state(job_id) not in REVIEWABLE:
            raise InvalidTransition(f"job {job_id} is {self.state(job_id).value}, not reviewable")

    def _log_review(self, job_id: int, reviewer_type: str, decision: str, note: Optional[str]) -> None:
        self.conn.execute(
            "INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,?)",
            (job_id, reviewer_type, decision, note, _now()))
        self.conn.commit()

    def _spawn_retry(self, job_id: int, reason: Optional[str],
                     close_old: Optional[JobState] = None, auto: bool = False) -> Optional[int]:
        job = self.job(job_id)
        if self._retries_exhausted(job) or (auto and job["retry_count"] + 1 > AUTO_RETRY_CAP):
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
