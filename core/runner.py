"""Job runners: submit queued jobs, heartbeat-poll running ones, download results.

`VideoRunner` (Step 4) and `ImageRunner` (Step 2) share one loop; they differ only in what they
submit and where results are stored. Risk-control rejections are logged and never retried
automatically (that would only burn credits); transient errors are retried through the state
machine up to the project's max_retry_count.
"""
import json
import math
import os
import time
from typing import Callable, Dict, Optional, Tuple

from . import assets, diag, layout
from . import subjects as subject_links
from . import trash
from .cost import record_usage
from .pipeline import Pipeline
from .preflight import record_failure
from .providers import RISK_CONTROL, ProviderError
from .throttle import THROTTLE

NOT_CREATED = "not_created"            # core.adapters.clipai.NOT_CREATED: task id returned, task never created
NOT_CREATED_RESENDS = 3
RESEND_NOTE = "gửi lại: nhà cung cấp không tạo task"


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
            if args is None:
                self._diag(job, "error", "missing_input", "thiếu đầu vào (ảnh đã duyệt / motion prompt / prompt ảnh)")
                self.p.start(job["id"])
                self.p.fail(job["id"], "missing inputs (approved image / motion prompt / image prompt)")
                continue
            running_all = self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type=? AND state='running'",
                                              (self.job_type,)).fetchone()[0]
            if not THROTTLE.allow(self.job_type, running_all):       # already includes the jobs this pass has started (they are 'running' now)
                break  # learned limit for all projects together: wait for a slot
            kwargs = self._submit_kwargs(job) if getattr(self.provider, "supports_aspect", False) else {}
            over = self._over_budget(job, args, kwargs)
            if over:
                self._diag(job, "warn", "budget", over)
                break                        # v3 test spending limit: leave everything queued, say why
            try:
                task_id = self.provider.submit(*args, **kwargs)
            except ProviderError as e:
                if e.code == "rate_limited":
                    THROTTLE.on_rate_limited(self.job_type)   # halve the learned limit; the job stays queued
                if e.transient:
                    self._diag(job, "warn", e.code, f"gửi job bị từ chối/tạm lỗi, sẽ thử lại: {e}")
                    break  # network/server hiccup: leave the job queued, try again next heartbeat
                self._diag(job, "warn" if e.code == RISK_CONTROL else "error", e.code, f"gửi job thất bại: {e}")
                self.p.start(job["id"])
                self._record_provider_failure(job, e.code, str(e))
                self.p.fail(job["id"], f"{e.code or 'error'}: {e}")
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
                dest = self._after_download(job, dest)
                self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, job["id"]))
                self.p.conn.commit()
                self.p.succeed(job["id"])
                THROTTLE.on_success(self.job_type)
                counts["succeeded"] += 1
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
                self._on_refused(job, status.error_code, status.error_message or "")
                self.p.fail(job["id"], message)
                counts["failed"] += 1
                if status.transient and self.p.retry(job["id"], message) is not None:
                    counts["retried"] += 1
        return counts

    def _not_created(self, job, message: str) -> None:
        """The provider answered with a task id but never created the task (nothing generated, nothing billed): the submission
        leaves the ledger, the provider is treated as overloaded (fewer jobs at once), and the same attempt is sent again at once —
        without using up a retry — at most NOT_CREATED_RESENDS times in a row; then the scene waits for a person."""
        from .cost import cancel_usage
        cancel_usage(self.p.conn, job["id"])
        THROTTLE.on_rate_limited(self.job_type)
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

    def _record_provider_failure(self, job, code, message: str) -> None:
        if code == RISK_CONTROL:
            record_failure(self.p.conn, job["id"], self.provider.name, message)
        self._on_refused(job, code, message)

    def _on_refused(self, job, code, message: str) -> None:
        """Hook: react to a job the provider refused (VideoRunner: Seedance "real person" -> Kling)."""

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
        return None

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
        if group:
            out["multi_prompt"] = [{"prompt": self._motion(r["id"])["motion_prompt"], "duration": shots.billed_shot_seconds(r["data"])}
                                   for r in group]
        elif mode == "per_shot" and "seedance" in (choice.get("model") or ""):
            end = shots.last_frame_for(self.p.conn, self.data_dir, job["scene_id"])
            if end:
                out["last_frame"] = end
        return out

    def _motion(self, scene_id: int):
        return self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()

    def _has_clip(self, scene_id: int) -> bool:
        return bool(self.p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN ('succeeded','approved')",
                                        (scene_id,)).fetchone())

    def _sends_group(self, job):
        """The multi-shot group this job generates in one go (Kling multi-shot, first shot of a group whose other shots have no
        clip yet), else None — a shot remade later is sent on its own."""
        from . import shots
        if shots.mode(self.p.project(job["project_id"])) != "multishot":
            return None
        group = shots.multishot_group_of(self.p.conn, job["scene_id"]) or []
        if len(group) < 2 or group[0]["id"] != job["scene_id"] or any(self._has_clip(r["id"]) for r in group[1:]):
            return None
        return group

    def _wait(self, job) -> bool:
        """Kling multi-shot: the first shot of a group sends for the whole group once every shot of it has an approved motion
        prompt; the other shots wait for their part of that clip (unless the first shot already has its clip: then a remade
        shot is sent on its own)."""
        from . import shots
        if shots.mode(self.p.project(job["project_id"])) != "multishot":
            return False
        group = shots.multishot_group_of(self.p.conn, job["scene_id"]) or []
        if len(group) < 2:
            return False
        if group[0]["id"] != job["scene_id"]:
            return not self._has_clip(group[0]["id"])
        if self._sends_group(job) is None:
            return False
        return any((self._motion(r["id"]) or {"state": None})["state"] != "approved" for r in group)

    def _stamp(self, job, args) -> Dict:
        from . import formats, lineage
        mp = self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (job["scene_id"],)).fetchone()
        return {"input_hash": lineage.video_input_hash(mp, formats.project_aspect(self.p.project(job["project_id"]))) if mp else None,
                "source_job_id": lineage.approved_image_id(self.p.conn, job["scene_id"]), "model": args[4]}

    def _submit_args(self, job):
        conn = self.p.conn
        mp = conn.execute("SELECT motion_prompt, negative_prompt, duration_sec, ref_video_path, ref_video_type"
                          " FROM motion_prompts WHERE scene_id=? AND state='approved'", (job["scene_id"],)).fetchone()
        img = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'"
                           " ORDER BY id DESC LIMIT 1", (job["scene_id"],)).fetchone()
        if mp is None or img is None:
            return None
        path = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{img['id']}.png")
        proj = self.p.project(job["project_id"])
        model = self._choice(job)["model"]            # per scene (ClipAI model guide) — see core.model_router
        duration = mp["duration_sec"]
        if json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["data"] or "{}").get("shot_no"):
            duration = math.ceil(float(duration or 0) - 1e-6)   # v3 shot: never shorter than planned (it is cut afterwards)
            from . import shots
            group = self._sends_group(job)
            if group:                                             # the whole group's length, one Kling generation
                duration = sum(shots.billed_shot_seconds(r["data"]) for r in group)
                model = "kling"
        args = (path, mp["motion_prompt"], mp["negative_prompt"], duration, model)
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
        from . import budget
        usage = self._usage(args, kwargs)
        return budget.check_video(self.p.conn, self.provider.name, *usage) if usage else None

    def _on_refused(self, job, code, message: str) -> None:
        """Seedance's privacy filter refuses a start picture that looks like a real person (a realistic CGI frame too), and its
        copyright filter a clip of a known game character. Kling has neither: the scene — with its whole continuity group, one model per
        group — switches to Kling, so the retry goes through."""
        from .adapters.clipai import REAL_PERSON, classify_failure
        kind = code if code in (REAL_PERSON, RISK_CONTROL) else classify_failure(message)
        seedance = str(job["model"] or "").startswith("seedance")
        if not (kind == REAL_PERSON or (kind == RISK_CONTROL and seedance and "copyright" in (message or "").lower())):
            return
        from . import model_router, shots
        ids = [r["id"] for r in shots.sequence_rows(self.p.conn, job["scene_id"])] or [job["scene_id"]]
        for sid in ids:
            model_router.set_override(self.p.conn, sid, "kling")
        why = "ảnh giống người thật" if kind == REAL_PERSON else "video có thể dính bản quyền"
        self._diag(job, "warn", kind, f"Seedance từ chối ({why}) → {len(ids)} cảnh/shot chuyển sang Kling")

    def _dest_path(self, job) -> str:
        idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()["idx"]
        return os.path.join(self._dir(job["project_id"], "videos"), f"{idx:02d}.mp4")

    def _after_download(self, job, path: str) -> str:
        """v3 shot rows: the model makes at least 3-4 s, a shot may be shorter -> keep the full clip as <idx>_raw.mp4 and cut the
        shot's own length into <idx>.mp4, so render, voice placement and subtitles all use the cut length. A Kling multi-shot
        clip is first split into one clip per shot of its group; the other shots' jobs are completed with their part."""
        from . import shots
        group = self._sends_group(job)
        if group:
            self._finish_group(job, path, group)
        try:
            shots.trim_clip(self.p, job["scene_id"], path)
        except Exception as e:  # noqa: BLE001 - a clip that cannot be cut is still a usable (longer) clip
            self._diag(job, "warn", "trim_error", f"không cắt được clip theo độ dài shot ({type(e).__name__}: {e}); dùng nguyên clip")
        return path

    def _finish_group(self, leader, path: str, group) -> None:
        from . import formats, lineage, shots
        conn = self.p.conn
        dests = [path] + [os.path.join(self._dir(leader["project_id"], "videos"), f"{r['idx']:02d}.mp4") for r in group[1:]]
        shots.split_group_clip(path, group, dests)
        aspect = formats.project_aspect(self.p.project(leader["project_id"]))
        for r, dest in zip(group[1:], dests[1:]):
            follower = conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND state='queued' ORDER BY id DESC LIMIT 1",
                                    (r["id"],)).fetchone()
            jid = follower["id"] if follower else self.p.create_job(r["id"], "video_gen")
            mp = self._motion(r["id"])
            conn.execute("UPDATE jobs SET group_leader=?, external_id=?, model='kling', input_hash=?, source_job_id=? WHERE id=?",
                         (leader["id"], leader["external_id"], lineage.video_input_hash(mp, aspect) if mp else None,
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


def chain_previous(proj, scene_data) -> bool:
    """Send the previous approved frame as an extra reference? storyboard_mode 1 = always, 2 = never, 0 (default) = automatic:
    only inside a sequence (consecutive shots of one place / continuous action, as set by the Director or by hand)."""
    from . import features
    mode = proj["storyboard_mode"] or 0
    return mode == 1 or (mode == 0 and bool(scene_data.get("sequence")) and features.on("chain_previous_auto"))


def lock_note(conn, project_id: int, cast) -> str:
    """Character Lock of the people in the shot, as one sentence for the image model (what must never drift)."""
    parts = []
    for r in conn.execute("SELECT name, lock_rules FROM characters WHERE project_id=?", (project_id,)):
        if r["name"] not in (cast or []):
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


class ImageRunner(_Runner):
    job_type = "image_gen"

    def _submit_kwargs(self, job) -> Dict:
        from . import formats
        aspect = formats.project_aspect(self.p.project(job["project_id"]))
        return {"size": formats.spec(aspect)["deepix"]} if aspect else {}

    def _over_budget(self, job, args, kwargs) -> Optional[str]:
        from . import budget
        return budget.check_image(self.p.conn, self.provider.name)

    def _wait(self, job) -> bool:
        """v3: the picture of a shot that continues the previous one waits for that shot's approved picture (sent as reference)."""
        from . import shots
        from . import features
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
        if (data.get("blocking") or "").strip():       # where each person stands/faces, so shots of one sequence agree
            prompt = f"{prompt}. Blocking: {data['blocking'].strip()}"
        prompt += lock_note(conn, job["project_id"], data.get("characters"))
        if job["retry_reason"]:
            prompt = f"{prompt}. Fix: {job['retry_reason']}"
        proj = self.p.project(job["project_id"])
        chain = chain_previous(proj, data)
        from . import features
        plan = layout.layout_reference(self.data_dir, job["project_id"], scene["idx"], data) if features.on("layout_to_model") else None
        refs = assets.scene_references(conn, job["project_id"], data,   # the layout and the previous frame keep their slots
                                       reserve=(1 if chain else 0) + (1 if plan else 0))
        if plan:
            refs = [plan] + refs
        if chain and len(refs) < assets.MAX_REFERENCES:
            # Deepix has no scriptable Storyboard (web UI only, see docs/CLIPAI_FEATURES.md) — this chains the
            # previous scene's approved picture in as an extra image-to-image reference instead, so style/lighting
            # carry over the way a real storyboard would.
            prev = previous_frame_job(conn, job["project_id"], scene["idx"], data.get("sequence"))
            if prev is not None:
                prev_path = os.path.join(self.data_dir, str(job["project_id"]), "images", f"job_{prev['id']}.png")
                if os.path.exists(prev_path):
                    refs = refs + [{"path": prev_path, "label": "previous scene", "role": "previous_scene"}]
        place = assets.scene_location(conn, job["project_id"], data)
        if place is not None:                          # B1: the place in words (+ real landmark heights), whatever pictures go
            prompt += " " + assets.location_text(conn, place)
        self._sent = getattr(self, "_sent", {})
        self._sent[job["id"]] = [{"label": r["label"], "role": r["role"], "file": os.path.basename(r["path"])} for r in refs]
        if refs:                                       # the chosen resources' pictures go with the prompt (image-to-image)
            return (assets.reference_note(refs) + "Scene: " + prompt, [r["path"] for r in refs])
        return (prompt,)

    def _record_usage(self, job, args, kwargs=None) -> None:
        info = getattr(self.provider, "usage_info", None)
        if info is not None:
            model, tier = info()
            record_usage(self.p.conn, job["id"], "image", self.provider.name, model, tier, 1, "image")

    def _dest_path(self, job) -> str:
        return os.path.join(self._dir(job["project_id"], "images"), f"job_{job['id']}.png")
