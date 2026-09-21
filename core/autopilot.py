"""Fully automatic mode for SHORT clips: the user approves the scene breakdown, everything else runs by itself.

Human gate: the scene breakdown (Director output: scenes + Character Bible). After "approve & run":
  images (Deepix) -> QC (Claude Vision, thresholds decide) -> motion prompts (Claude, auto-approved)
  -> videos (Clip AI) -> one background track (Clip AI music, optional) -> final render.

Design:
- `tick()` looks at the database, does the next useful thing and returns. It is idempotent, so a crash, a restart
  or a "Resume" click simply continues where the project stands.
- A background thread (`Manager`) calls tick() every few seconds; progress lives in the database so any browser
  window can show it.
- Fail-safe: anything that needs a human (a scene out of retries, a risk-control block, a spending cap, a missing
  provider) STOPS the run with a clear note instead of guessing; nothing else is skipped or approved blindly.
- Spending is capped by the number of jobs per scene (retries included), not just by good behaviour.
"""
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import diag, ffmpeg_studio, final_cut, llm_io, llm_runner, music, perf
from .pipeline import Pipeline

RUNNING, WAITING, STOPPED, ATTENTION, DONE, ERROR = "running", "waiting", "stopped", "needs_attention", "done", "error"
QUEUED = "queued"   # approved, waiting for a free slot (see Manager.max_parallel)
PHASE_LABELS = {"images": "Gen ảnh + QC", "motion": "Motion prompt", "videos": "Gen video", "music": "Nhạc nền",
                "render": "Ghép & render", "done": "Hoàn tất"}
MAX_SCENES = int(os.environ.get("AUTOPILOT_MAX_SCENES", "12"))
LOG_KEEP = 60


@dataclass
class Context:
    """Everything a tick needs (injectable so tests can use mock providers)."""
    data_dir: str
    image_runner: object
    video_runner: object
    llm: object
    audio: Optional[object] = None
    render: Optional[Callable] = None   # (pipeline, project_id, data_dir, music_path) -> output path


def default_render(p: Pipeline, project_id: int, data_dir: str, music_path: Optional[str]) -> str:
    clips = [c for c in final_cut.collect_clips(p, data_dir, project_id) if c["path"]]
    if not clips:
        raise ValueError("no clips to render")
    durations = [final_cut.clip_seconds(c["path"], c["requested_sec"]) for c in clips]
    out_dir = os.path.join(data_dir, str(project_id), "output")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "FINAL_VIDEO.mp4")
    keep = bool(p.project(project_id)["video_audio"])
    return ffmpeg_studio.render_final([c["path"] for c in clips], out, durations, "cut", 1.0, music_path, 0.6,
                                      keep_audio=keep)


def default_context(p: Pipeline, data_dir: str) -> Context:
    """Providers from the environment (IMAGE_PROVIDER, VIDEO_PROVIDER, ANTHROPIC_API_KEY / LLM_PROVIDER, AUDIO_PROVIDER)."""
    from .adapters import factory
    from .runner import ImageRunner, VideoRunner
    image, video = factory.image_provider(), factory.video_provider()
    if image is None or video is None:
        raise ValueError("Chưa cấu hình nhà cung cấp ảnh/video (IMAGE_PROVIDER, VIDEO_PROVIDER).")
    llm = llm_runner.client_from_env()
    if llm is None:
        raise ValueError("Chưa có Claude API (ANTHROPIC_API_KEY): chế độ tự động cần để chấm QC và viết motion prompt.")
    return Context(data_dir, ImageRunner(p, image, data_dir), VideoRunner(p, video, data_dir), llm,
                   music.audio_provider(), default_render)


# ---- state helpers ----------------------------------------------------------------------------
def status(p: Pipeline, project_id: int) -> Dict:
    row = p.project(project_id)
    return {"state": row["autopilot_state"] or "idle", "note": row["autopilot_note"] or "",
            "beat": row["autopilot_beat"], "log": json.loads(row["autopilot_log"] or "[]")}


def _set(p: Pipeline, pid: int, state: Optional[str] = None, note: Optional[str] = None) -> None:
    if state is not None:
        p.conn.execute("UPDATE projects SET autopilot_state=? WHERE id=?", (state, pid))
    if note is not None:
        p.conn.execute("UPDATE projects SET autopilot_note=? WHERE id=?", (note, pid))
    p.conn.execute("UPDATE projects SET autopilot_beat=? WHERE id=?", (time.time(), pid))
    p.conn.commit()


def _d(p: Pipeline, pid: int, stage: str, severity: str, message: str, code: Optional[str] = None) -> None:
    diag.record(p.conn, stage, severity, message, code, pid)


def _log(p: Pipeline, pid: int, message: str) -> None:
    entries = json.loads(p.project(pid)["autopilot_log"] or "[]")
    if entries and entries[-1]["msg"] == message:
        return
    entries.append({"at": time.strftime("%H:%M:%S"), "msg": message})
    p.conn.execute("UPDATE projects SET autopilot_log=? WHERE id=?", (json.dumps(entries[-LOG_KEEP:], ensure_ascii=False), pid))
    p.conn.commit()


def is_stale(p: Pipeline, project_id: int, poll_sec: float = 15) -> bool:
    """'running' in the database but no thread has ticked for a while (server restarted / thread died)."""
    s = status(p, project_id)
    return s["state"] == RUNNING and (s["beat"] is None or time.time() - s["beat"] > max(poll_sec * 4, 60))


def problems(p: Pipeline, project_id: int, ctx: Optional[Context] = None) -> List[str]:
    """Reasons the automatic mode cannot start yet (empty list = ready)."""
    out = []
    scenes = p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    if not scenes:
        return ["Chưa có cảnh: upload kịch bản và bấm Phân tích."]
    if len(scenes) > MAX_SCENES:
        out.append(f"Chế độ này dành cho clip ngắn: tối đa {MAX_SCENES} cảnh (kịch bản có {len(scenes)}).")
    if not p.conn.execute("SELECT 1 FROM characters WHERE project_id=?", (project_id,)).fetchone():
        out.append("Chưa có Character Bible: chạy Director trước.")
    missing = [f"S{s['idx']:02d}" for s in scenes if not (json.loads(s["data"] or "{}").get("image_prompt") or "").strip()]
    if missing:
        out.append("Cảnh chưa có prompt ảnh: " + ", ".join(missing) + " (chạy Director hoặc điền tay).")
    if p.project(project_id)["paused"]:
        out.append("Dự án đang PAUSE.")
    if ctx is None:
        try:
            ctx = default_context(p, os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")))
        except ValueError as e:
            out.append(str(e))
    if ctx is not None and ctx.render is default_render:
        try:
            ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            out.append("Chưa có ffmpeg để ghép video (đặt FFMPEG_PATH).")
    return out


def _owner(p: Pipeline, project_id: int, user: Optional[str]) -> None:
    """Remember who runs this project: every job the background thread creates is counted for them."""
    if user:
        p.conn.execute("UPDATE projects SET autopilot_user=? WHERE id=?", (user, project_id))
        p.conn.commit()


def start(p: Pipeline, project_id: int, user: Optional[str] = None) -> None:
    """The user approved the scene breakdown: lock the Character Bible, use automatic QC and mark the run as started."""
    _owner(p, project_id, user)
    llm_io.lock_character_bible(p, project_id)
    p.set_mode(project_id, "auto")
    p.set_review_floor(project_id, None)   # nothing may wait for a human
    p.set_paused(project_id, False)
    _set(p, project_id, RUNNING, "Đã duyệt phân cảnh, đang chạy tự động")
    _log(p, project_id, "Bạn đã duyệt phân cảnh → bắt đầu chạy tự động")


def resume(p: Pipeline, project_id: int, user: Optional[str] = None) -> None:
    """Continue after a stop / needs_attention / error / restart (the tick picks up where the project stands)."""
    _owner(p, project_id, user)
    p.set_paused(project_id, False)
    _set(p, project_id, RUNNING, "Tiếp tục chạy tự động")
    _log(p, project_id, "Tiếp tục chạy tự động")


def progress(p: Pipeline, project_id: int, data_dir: str) -> List[tuple]:
    """(label, done, total) for the checklist shown while the run is going."""
    n = _count(p, "SELECT COUNT(*) FROM scenes WHERE project_id=?", project_id)
    distinct = lambda kind, state: _count(p, "SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type=?"  # noqa: E731
                                          " AND state=?", project_id, kind, state)
    motion = _count(p, "SELECT COUNT(*) FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?"
                       " AND m.state='approved'", project_id)
    drafts_dir, selected_dir = music.project_dirs(data_dir, project_id)
    final = os.path.exists(os.path.join(data_dir, str(project_id), "output", "FINAL_VIDEO.mp4"))
    return [("Ảnh đã duyệt", distinct("image_gen", "approved"), n), ("Motion prompt đã duyệt", motion, n),
            ("Video đã gen", distinct("video_gen", "succeeded"), n),
            ("Nhạc nền", 1 if os.listdir(selected_dir) else 0, 1), ("Video cuối", 1 if final else 0, 1)]


def stop(p: Pipeline, project_id: int, note: str = "Đã dừng theo yêu cầu") -> None:
    _set(p, project_id, STOPPED, note)
    _log(p, project_id, note)


# ---- the tick ---------------------------------------------------------------------------------
def _count(p: Pipeline, sql: str, *args) -> int:
    return p.conn.execute(sql, args).fetchone()[0]


def _job_caps(p: Pipeline, pid: int):
    n = _count(p, "SELECT COUNT(*) FROM scenes WHERE project_id=?", pid)
    per_scene = p.project(pid)["max_retry_count"] + 2
    return n * per_scene, n * per_scene


def _scene_rows(p: Pipeline, pid: int):
    return p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()


def _has(p: Pipeline, scene_id: int, kind: str, states: str) -> bool:
    return bool(_count(p, f"SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type=? AND state IN ({states})", scene_id, kind))


def _blocked_scenes(p: Pipeline, pid: int) -> List[str]:
    """Scenes that ran out of retries or were blocked by risk control: only a human can decide what to do."""
    notes = []
    for r in p.conn.execute("SELECT j.id, j.type, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id"
                            " WHERE j.project_id=? AND j.escalated=1 AND j.state IN ('failed','rejected')", (pid,)):
        notes.append(f"cảnh {r['idx']}: hết số lần thử ({'ảnh' if r['type'] == 'image_gen' else 'video'})")
    for r in p.conn.execute("SELECT DISTINCT s.idx FROM content_moderation_failures f JOIN jobs j ON j.id=f.job_id"
                            " JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.state='failed'", (pid,)):
        notes.append(f"cảnh {r['idx']}: bị chặn risk control")
    return sorted(set(notes))


def _active(p: Pipeline, pid: int, kind: str) -> int:
    return _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type=? AND state IN ('queued','running','retryable')",
                  pid, kind)


def _images_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Returns None when every scene has an approved image, else a progress message."""
    cap_images, _ = _job_caps(p, pid)
    for scene in _scene_rows(p, pid):
        if _has(p, scene["id"], "image_gen", "'approved','queued','running','succeeded','pending_review','retryable','failed'"):
            continue  # done, in progress, or failed (failed ones are retried below, never re-created blindly)
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type='image_gen' AND escalated=1", scene["id"]):
            continue  # a human must decide
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", pid) >= cap_images:
            raise _Stop(BUDGET_NOTE)
        _daily_cap(p)
        p.conn.execute("UPDATE scenes SET state='ready' WHERE id=? AND state='needs_attention'", (scene["id"],))
        p.create_job(scene["id"], "image_gen")
    ctx.image_runner.submit_pending(pid)
    ctx.image_runner.poll_once(pid)
    for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='failed' AND escalated=0",
                            (pid,)).fetchall():
        p.retry(j["id"], "autopilot: thử lại")  # ordinary failure: counts toward the retry limit, then a human decides
    if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", pid):
        r = llm_runner.run_qc_batch(p, pid, ctx.llm, ctx.data_dir)
        if r["failed"]:
            _log(p, pid, f"QC lỗi ở {len(r['failed'])} ảnh: {r['failed'][0][1]}")
            if any("API key" in m or "auth" in m.lower() for _, m in r["failed"]):
                raise _Stop("Claude API từ chối khóa (ANTHROPIC_API_KEY)")
    for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review'", (pid,)):
        p.approve(j["id"], "ai_agent", "autopilot")
    done = sum(1 for s in _scene_rows(p, pid) if _has(p, s["id"], "image_gen", "'approved'"))
    total = len(_scene_rows(p, pid))
    return None if done == total else f"Ảnh: {done}/{total} đã duyệt"


class _Stop(Exception):
    pass


BUDGET_NOTE = "Đã chạm trần số job (kể cả gen lại) — dừng để tránh tốn credit"
DAILY_NOTE = "Đã chạm trần job trong ngày (AUTOPILOT_DAILY_JOBS) — dừng; bấm Tiếp tục ngày mai hoặc nâng trần"


def _daily_cap(p: Pipeline) -> None:
    limit = perf.daily_limit()
    if limit and perf.jobs_today(p.conn) >= limit:
        raise _Stop(DAILY_NOTE)


def _motion_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    rows = _scene_rows(p, pid)
    missing = [s for s in rows if not _count(p, "SELECT COUNT(*) FROM motion_prompts WHERE scene_id=?", s["id"])]
    if missing:
        r = llm_runner.run_motion(p, pid, ctx.llm, ctx.data_dir)
        _log(p, pid, f"Claude viết {r['scenes']} motion prompt")
    for s in rows:
        m = p.conn.execute("SELECT state FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone()
        if m is not None and m["state"] != "approved":
            llm_io.approve_motion_prompt(p, s["id"])
    done = sum(1 for s in rows if _count(p, "SELECT COUNT(*) FROM motion_prompts WHERE scene_id=? AND state='approved'", s["id"]))
    return None if done == len(rows) else f"Motion prompt: {done}/{len(rows)}"


def _videos_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    _, cap_videos = _job_caps(p, pid)
    for r in llm_io.ready_for_video(p, pid):
        if _has(p, r["scene_id"], "video_gen", "'queued','running','succeeded','retryable','failed'"):
            continue  # failed ones: retried below unless blocked by risk control (then a human decides)
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type='video_gen' AND escalated=1", r["scene_id"]):
            continue
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen'", pid) >= cap_videos:
            raise _Stop(BUDGET_NOTE)
        _daily_cap(p)
        p.create_job(r["scene_id"], "video_gen")
    ctx.video_runner.submit_pending(pid)
    ctx.video_runner.poll_once(pid)
    for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='failed' AND escalated=0", (pid,)).fetchall():
        blocked = _count(p, "SELECT COUNT(*) FROM content_moderation_failures WHERE job_id=?", j["id"])
        if not blocked:
            p.retry(j["id"], "autopilot: thử lại")   # ordinary failure: one more attempt (counts toward the limit)
    rows = _scene_rows(p, pid)
    done = sum(1 for s in rows if _has(p, s["id"], "video_gen", "'succeeded'"))
    return None if done == len(rows) else f"Video: {done}/{len(rows)} xong"


def _music_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    if ctx.audio is None:
        return None
    drafts_dir, selected_dir = music.project_dirs(ctx.data_dir, pid)
    if os.listdir(selected_dir):
        return None
    drafts = music.load_drafts(drafts_dir)
    if not drafts:
        brief = music.default_brief(p, pid)
        music.submit_drafts(ctx.audio, drafts_dir, brief["prompt"], brief["length_ms"], True, 1, ledger=(p.conn, pid))
        _log(p, pid, "Đã gửi 1 bản nhạc nền")
        return "Nhạc nền: đang tạo"
    music.refresh_drafts(ctx.audio, drafts_dir)
    drafts = music.load_drafts(drafts_dir)
    ok = [i for i, d in enumerate(drafts) if d["state"] == "succeeded"]
    if ok:
        music.select_draft(drafts_dir, selected_dir, ok[0])
        return None
    if any(d["state"] == "running" for d in drafts):
        return "Nhạc nền: đang tạo"
    _log(p, pid, "Nhạc nền không tạo được → ghép không nhạc")
    _d(p, pid, "music", "warn", "nhạc nền không tạo được, video cuối sẽ KHÔNG có nhạc (lỗi âm thầm)", "degraded")
    return None


def tick(p: Pipeline, project_id: int, ctx: Context) -> str:
    """One step of the run. Returns the resulting state."""
    st = status(p, project_id)["state"]
    if st != RUNNING:
        return st
    p.actor = p.project(project_id)["autopilot_user"]
    if p.project(project_id)["paused"]:
        _set(p, project_id, note="Đang PAUSE")
        return RUNNING
    try:
        phases = [("images", _images_phase), ("motion", _motion_phase), ("videos", _videos_phase),
                  ("music", _music_phase)]
        for name, fn in phases:
            progress = fn(p, project_id, ctx)
            if progress is not None:
                blocked = _blocked_scenes(p, project_id)
                idle = not (_active(p, project_id, "image_gen") or _active(p, project_id, "video_gen"))
                if blocked and idle and name in ("images", "videos"):
                    note = "Cần bạn xử lý: " + "; ".join(blocked)
                    _set(p, project_id, ATTENTION, note)
                    _log(p, project_id, note)
                    _d(p, project_id, "autopilot", "warn", note, "needs_attention")
                    return ATTENTION
                _set(p, project_id, note=f"{PHASE_LABELS[name]} — {progress}")
                _log(p, project_id, f"{PHASE_LABELS[name]}: {progress}")
                return RUNNING
        music_file = None
        drafts_dir, selected_dir = music.project_dirs(ctx.data_dir, project_id)
        chosen = os.listdir(selected_dir)
        if chosen:
            music_file = os.path.join(selected_dir, chosen[0])
        out = (ctx.render or default_render)(p, project_id, ctx.data_dir, music_file)
        _set(p, project_id, DONE, f"Xong: {out}")
        _log(p, project_id, "Đã ghép video cuối")
        return DONE
    except _Stop as e:
        _set(p, project_id, STOPPED, str(e))
        _log(p, project_id, str(e))
        _d(p, project_id, "autopilot", "warn", str(e), "stopped")
        return STOPPED
    except (llm_runner.LlmError, ValueError, OSError, ffmpeg_studio.FFmpegError, ffmpeg_studio.FFmpegNotFound) as e:
        _set(p, project_id, ERROR, f"Lỗi: {e}")
        _log(p, project_id, f"Lỗi: {str(e)[:200]}")
        render_error = isinstance(e, (ffmpeg_studio.FFmpegError, ffmpeg_studio.FFmpegNotFound))
        _d(p, project_id, "render" if render_error else "autopilot", "error", f"{type(e).__name__}: {e}", "error")
        return ERROR


def run_until_done(p: Pipeline, project_id: int, ctx: Context, max_ticks: int = 200) -> str:
    """Synchronous driver (tests, command line): tick until the run is over or a human is needed."""
    state = RUNNING
    for _ in range(max_ticks):
        state = tick(p, project_id, ctx)
        if state != RUNNING:
            return state
    return state


# ---- background thread ------------------------------------------------------------------------
class Manager:
    """Runs projects in background threads (one per project), at most `max_parallel` at a time; the rest wait in a
    FIFO queue and start as slots free up. Progress is in the database, so a page reload or another browser window
    sees the same thing."""

    def __init__(self, db_path: str, data_dir: str, context_factory: Callable = default_context, poll_sec: float = 15,
                 max_parallel: Optional[int] = None):
        self.db_path, self.data_dir, self.factory, self.poll_sec = db_path, data_dir, context_factory, poll_sec
        self.max_parallel = max_parallel if max_parallel is not None else int(os.environ.get("AUTOPILOT_MAX_PARALLEL", "2"))
        self._threads: Dict[int, threading.Thread] = {}
        self._queue: List[int] = []
        self._lock = threading.RLock()

    def alive(self, project_id: int) -> bool:
        t = self._threads.get(project_id)
        return bool(t and t.is_alive())

    def running_count(self) -> int:
        return sum(1 for t in self._threads.values() if t.is_alive())

    def queued(self, project_id: int) -> bool:
        return project_id in self._queue

    def position(self, project_id: int) -> int:
        """1-based place in the queue (0 = not queued)."""
        return self._queue.index(project_id) + 1 if project_id in self._queue else 0

    def queue_length(self) -> int:
        return len(self._queue)

    def start(self, project_id: int) -> bool:
        """Start now if a slot is free, otherwise wait in the queue. False when already running or queued."""
        with self._lock:
            if self.alive(project_id):
                return False
            if project_id in self._queue:
                self._queue.remove(project_id)   # re-queued (e.g. resumed after a stop): goes to the back
            if self.running_count() >= self.max_parallel:
                self._queue.append(project_id)
                self._note_queue()
                return True
            self._launch(project_id)
            return True

    def _launch(self, project_id: int) -> None:
        t = threading.Thread(target=self._loop, args=(project_id,), daemon=True, name=f"autopilot-{project_id}")
        self._threads[project_id] = t
        t.start()

    def _note_queue(self) -> None:
        from .db import connect
        p = Pipeline(connect(self.db_path))
        for n, pid in enumerate(self._queue, 1):
            _set(p, pid, QUEUED, f"Xếp hàng (vị trí {n}): chạy tối đa {self.max_parallel} dự án cùng lúc")
            _log(p, pid, "Xếp hàng chờ tới lượt")

    def _promote(self) -> None:
        from .db import connect
        with self._lock:
            p = Pipeline(connect(self.db_path))
            while self._queue and self.running_count() < self.max_parallel:
                pid = self._queue.pop(0)
                if status(p, pid)["state"] != QUEUED:
                    continue   # stopped or reset while waiting
                _set(p, pid, RUNNING, "Tới lượt, bắt đầu chạy")
                self._launch(pid)
            for n, pid in enumerate(self._queue, 1):
                _set(p, pid, note=f"Xếp hàng (vị trí {n}): chạy tối đa {self.max_parallel} dự án cùng lúc")

    def _loop(self, project_id: int) -> None:
        try:
            self._run(project_id)
        finally:
            # after this thread has ended, so its slot counts as free
            threading.Timer(0.05, self._promote).start()

    def _run(self, project_id: int) -> None:
        from .db import connect
        p = Pipeline(connect(self.db_path))
        try:
            ctx = self.factory(p, self.data_dir)
        except Exception as e:  # noqa: BLE001 - report configuration problems in the UI, never die silently
            _set(p, project_id, ERROR, f"Không khởi động được: {e}")
            _d(p, project_id, "autopilot", "error", f"không khởi động được: {e}", "config")
            _log(p, project_id, f"Không khởi động được: {e}")
            return
        while True:
            try:
                state = tick(p, project_id, ctx)
            except Exception as e:  # noqa: BLE001
                _set(p, project_id, ERROR, f"Lỗi không lường trước: {e}")
                _d(p, project_id, "autopilot", "error", f"lỗi không lường trước {type(e).__name__}: {e}", "unexpected")
                _log(p, project_id, f"Lỗi không lường trước: {str(e)[:200]}")
                return
            if state != RUNNING:
                return
            time.sleep(self.poll_sec)
