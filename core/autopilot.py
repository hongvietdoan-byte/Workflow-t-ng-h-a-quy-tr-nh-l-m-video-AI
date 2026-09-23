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

from . import audio_lib, previz, sfx_plan, sound_lib, subtitles, dialogue, diag, ffmpeg_studio, final_cut, llm_io, llm_runner, music, perf
from .pipeline import Pipeline

RUNNING, WAITING, STOPPED, ATTENTION, DONE, ERROR = "running", "waiting", "stopped", "needs_attention", "done", "error"
QUEUED = "queued"   # approved, waiting for a free slot (see Manager.max_parallel)
PHASE_LABELS = {"director": "Director (Character Bible + thông số cảnh)", "previz": "Dựng layout / storyboard", "images": "Gen ảnh + QC",
                "setcheck": "QC đồng bộ cả bộ ảnh", "motion": "Motion prompt", "voice": "Giọng thoại", "videos": "Gen video + QC video",
                "music": "Nhạc nền", "sfx": "Hiệu ứng âm thanh", "render": "Xuất bản", "done": "Hoàn tất"}
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
    subtitle: Optional[Callable] = None  # (pipeline, project_id, data_dir, video_path, llm) -> dict | None


def default_render(p: Pipeline, project_id: int, data_dir: str, music_path: Optional[str]) -> str:
    """The project's saved render settings (the same the Step 5 render uses), every usable clip, voices placed on the timeline."""
    from . import delivery
    return delivery.render(p, project_id, data_dir, music_path)["path"]


def default_subtitle(p: Pipeline, pid: int, data_dir: str, video: str, llm) -> Optional[dict]:
    """Subtitles with the project's settings, timed from the voices / the SAVED transition (only when 'auto subtitles' is on)."""
    from . import delivery
    return delivery.subtitle_layer(p, pid, data_dir, llm=llm)


def default_context(p: Pipeline, data_dir: str) -> Context:
    """Providers from the environment (IMAGE_PROVIDER, VIDEO_PROVIDER, ANTHROPIC_API_KEY / LLM_PROVIDER, AUDIO_PROVIDER)."""
    from .adapters import factory
    from .runner import ImageRunner, VideoRunner
    image, video = factory.image_provider(), factory.video_provider()
    if image is None or video is None:
        raise ValueError("Chưa cấu hình nhà cung cấp ảnh/video (IMAGE_PROVIDER, VIDEO_PROVIDER).")
    llm = llm_runner.client_from_env()
    if llm is None:
        raise ValueError("Chưa có Claude (ANTHROPIC_API_KEY hoặc LLM_PROVIDER=claude_cli): chế độ tự động cần để chấm QC và viết motion prompt.")
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
    """The user approved the scene breakdown: automatic QC for the run (the previous review setting is restored at the end)."""
    _owner(p, project_id, user)
    _save_cfg(p, project_id)
    if _count(p, "SELECT COUNT(*) FROM characters WHERE project_id=?", project_id) and not get_gates(p, project_id)["bible"]:
        llm_io.lock_character_bible(p, project_id)      # already analysed by hand and no review wanted: freeze it
    p.set_mode(project_id, "auto")
    p.set_review_floor(project_id, None)   # nothing may wait for a human
    p.set_paused(project_id, False)
    set_gates(p, project_id, {"bible_done": False, "pilot_done": False, "waiting_for": None})
    _set(p, project_id, RUNNING, "Đã duyệt phân cảnh, đang chạy tự động")
    _log(p, project_id, "Bạn đã duyệt phân cảnh → bắt đầu chạy tự động")


def resume(p: Pipeline, project_id: int, user: Optional[str] = None) -> None:
    """Continue after a stop / a checkpoint / needs_attention / error / restart. At a checkpoint, continuing = the person approves it."""
    _owner(p, project_id, user)
    gates = get_gates(p, project_id)
    if gates.get("waiting_for") == "bible":
        llm_io.lock_character_bible(p, project_id)
        set_gates(p, project_id, {"bible_done": True, "waiting_for": None})
        _log(p, project_id, "Bạn đã duyệt Character Bible → tiếp tục")
    elif gates.get("waiting_for") == "pilot":
        from . import pilot
        pilot.release(p, project_id)
        set_gates(p, project_id, {"pilot_done": True, "waiting_for": None})
        _log(p, project_id, "Bạn đã duyệt ảnh mẫu thử → gen phần còn lại")
    _save_cfg(p, project_id)
    p.set_mode(project_id, "auto")
    p.set_paused(project_id, False)
    _set(p, project_id, RUNNING, "Tiếp tục chạy tự động")
    _log(p, project_id, "Tiếp tục chạy tự động")


def progress(p: Pipeline, project_id: int, data_dir: str) -> List[tuple]:
    """(label, done, total) for the checklist shown while the run is going — fresh results only (core.lineage)."""
    from . import lineage, voice
    summ = lineage.summary(p.conn, project_id)
    n = summ["total"]
    drafts_dir, selected_dir = music.project_dirs(data_dir, project_id)
    vs = voice.status(p.conn, project_id, data_dir)
    fin = lineage.latest_output(p.conn, project_id, "final")
    rows = [("Ảnh đã duyệt", summ["images"][0], n), ("Motion prompt đã duyệt", summ["motion"][0], n)]
    if vs["total"]:
        rows.append(("Giọng thoại", vs.get("succeeded", 0), vs["total"]))
    rows += [("Video dùng được", summ["videos"][0], n), ("Nhạc nền", 1 if os.listdir(selected_dir) else 0, 1),
             ("Bản giao", 1 if fin is not None or os.path.exists(os.path.join(data_dir, str(project_id), "output", "FINAL_VIDEO.mp4")) else 0, 1)]
    return rows


def stop(p: Pipeline, project_id: int, note: str = "Đã dừng theo yêu cầu") -> None:
    _set(p, project_id, STOPPED, note)
    _log(p, project_id, note)
    _restore_cfg(p, project_id)


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


def _director_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Claude writes the Character Bible and the scene specs (once). Then, when the 'review the characters' checkpoint is on, the run
    waits for the person before any picture is paid for (a wrong description would repeat in every scene)."""
    if not _count(p, "SELECT COUNT(*) FROM characters WHERE project_id=?", pid):
        r = llm_runner.run_director(p, pid, ctx.llm)
        _log(p, pid, f"Director: {r['characters']} nhân vật, {r['scenes']} cảnh")
    missing = [f"S{s['idx']:02d}" for s in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))
               if not (json.loads(s["data"] or "{}").get("image_prompt") or "").strip()]
    if missing:
        raise _Stop("Cảnh chưa có prompt ảnh sau khi chạy Director: " + ", ".join(missing) + " — điền tay hoặc sửa kịch bản rồi bấm Tiếp tục")
    gates = get_gates(p, pid)
    if gates["bible"] and not gates["bible_done"]:
        raise _Wait("bible", "Chờ bạn duyệt Character Bible (mô tả, Character Lock, giọng, ảnh mốc) ở Bước 1 rồi bấm Tiếp tục")
    llm_io.lock_character_bible(p, pid)
    return None


def _previz_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Lay the shots out once before any picture, and let Claude check the storyboard (continuity). Never blocks the run."""
    marker = _marker(ctx, pid, "layouts", ".autopilot_done")
    if os.path.exists(marker) or _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", pid):
        return None
    try:
        r = previz.plan_layouts(p, pid, ctx.llm, ctx.data_dir)
        _log(p, pid, f"Layout: dựng {len(r['laid_out'])} cảnh" + (f", {len(r['skipped'])} cảnh chưa có Background (gen như cũ)"
                                                                if r["skipped"] else ""))
        if r.get("storyboard"):
            review = previz.review_storyboard(p, pid, ctx.llm, ctx.data_dir)
            if review.get("issues"):
                _log(p, pid, f"Rà storyboard: {len(review['issues'])} lưu ý liên tục (xem Bước 1)")
    except (llm_runner.LlmError, ValueError, OSError) as e:
        _log(p, pid, f"Không dựng được layout, gen ảnh theo cách cũ: {str(e)[:150]}")
        _d(p, pid, "previz", "warn", f"autopilot bỏ qua layout: {e}", "previz_skipped")
    with open(marker, "w") as f:
        f.write("1")
    return None


def _images_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Returns None when every scene has an up-to-date approved image, else a progress message. With the pilot checkpoint on, a few
    representative scenes are made first and the run waits for the person."""
    from . import lineage, pilot
    gates = get_gates(p, pid)
    if gates["pilot"] and not gates["pilot_done"] and not pilot.active(p, pid):
        pilot.start(p, pid)
        _log(p, pid, "Gen thử các cảnh đại diện trước")
    cap_images, _ = _job_caps(p, pid)
    stale = {sid: r for sid, r in lineage.scan(p.conn, pid).items() if r["image_stale"] and r["image_job_id"]}
    for scene in _scene_rows(p, pid):
        if pilot.allowed_scenes(p, pid, [scene["id"]]) == []:
            continue
        if scene["id"] in stale:
            if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", pid) >= cap_images:
                raise _Stop(BUDGET_NOTE)
            p.reopen_approved(stale[scene["id"]]["image_job_id"], f"Nội dung cảnh đã đổi: {stale[scene['id']]['image_stale']}")
            continue
        if _has(p, scene["id"], "image_gen", "'approved','queued','running','succeeded','pending_review','retryable','failed'"):
            continue
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type='image_gen' AND escalated=1", scene["id"]):
            continue
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", pid) >= cap_images:
            raise _Stop(BUDGET_NOTE)
        _daily_cap(p)
        p.conn.execute("UPDATE scenes SET state='ready' WHERE id=? AND state='needs_attention'", (scene["id"],))
        p.create_job(scene["id"], "image_gen")
    ctx.image_runner.submit_pending(pid)
    ctx.image_runner.poll_once(pid)
    for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='failed' AND escalated=0",
                            (pid,)).fetchall():
        p.retry(j["id"], "autopilot: thử lại")
    if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", pid):
        r = llm_runner.run_qc_batch(p, pid, ctx.llm, ctx.data_dir)
        if r["failed"]:
            _log(p, pid, f"QC lỗi ở {len(r['failed'])} ảnh: {r['failed'][0][1]}")
            if any("API key" in m or "auth" in m.lower() for _, m in r["failed"]):
                raise _Stop("Claude từ chối đăng nhập / khóa API")
    for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review'", (pid,)):
        p.approve(j["id"], "ai_agent", "autopilot")
    if pilot.active(p, pid):
        if pilot.done(p, pid):
            raise _Wait("pilot", "Ảnh các cảnh gen thử đã xong — xem ở Bước 2, ổn thì bấm Tiếp tục để gen phần còn lại")
        return "Ảnh gen thử: đang làm"
    fresh = lineage.summary(p.conn, pid)["images"][0]
    total = len(_scene_rows(p, pid))
    return None if fresh == total else f"Ảnh: {fresh}/{total} đã duyệt"


class _Stop(Exception):
    pass


BUDGET_NOTE = "Đã chạm trần số job (kể cả gen lại) — dừng để tránh tốn credit"
DAILY_NOTE = "Đã chạm trần job trong ngày (AUTOPILOT_DAILY_JOBS) — dừng; bấm Tiếp tục ngày mai hoặc nâng trần"


def _daily_cap(p: Pipeline) -> None:
    limit = perf.daily_limit()
    if limit and perf.jobs_today(p.conn) >= limit:
        raise _Stop(DAILY_NOTE)


def _motion_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Motion prompts for scenes without one or with an outdated one; then (once) the prompt check, whose revised prompts are used."""
    from . import claude_tasks, lineage
    rows = _scene_rows(p, pid)
    missing = [s for s in rows if not _count(p, "SELECT COUNT(*) FROM motion_prompts WHERE scene_id=?", s["id"])]
    if missing:
        r = llm_runner.run_motion(p, pid, ctx.llm, ctx.data_dir)
        _log(p, pid, f"Claude viết {r['scenes']} motion prompt")
    stale = sorted(r["idx"] for r in lineage.scan(p.conn, pid).values() if r["motion_stale"] and r["image_job_id"])
    if stale:
        llm_runner.run_motion(p, pid, ctx.llm, ctx.data_dir, only_idx=stale)
        _log(p, pid, f"Viết lại motion prompt cảnh {', '.join(map(str, stale))} (ảnh/cảnh đã đổi)")
    marker = _marker(ctx, pid, ".lint_done")
    if not os.path.exists(marker):
        try:
            res = claude_tasks.lint_motion(p, pid, ctx.llm)
            fixed = 0
            for s in res.get("scenes") or []:
                sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, s["idx"])).fetchone()
                if sid and not s.get("ok") and claude_tasks.apply_lint(p, pid, sid["id"]):
                    fixed += 1
            _log(p, pid, f"Rà motion prompt: sửa {fixed} prompt" if fixed else "Rà motion prompt: ổn")
        except (llm_runner.LlmError, ValueError) as e:
            _d(p, pid, "motion", "warn", f"autopilot bỏ qua rà prompt: {e}", "lint_skipped")
        with open(marker, "w") as f:
            f.write("1")
    for s in rows:
        m = p.conn.execute("SELECT state FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone()
        if m is not None and m["state"] != "approved":
            llm_io.approve_motion_prompt(p, s["id"])
    done = sum(1 for s in rows if _count(p, "SELECT COUNT(*) FROM motion_prompts WHERE scene_id=? AND state='approved'", s["id"]))
    if done == len(rows):
        _dialogue_gate(p, pid)
    return None if done == len(rows) else f"Motion prompt: {done}/{len(rows)}"


def _dialogue_gate(p: Pipeline, pid: int) -> None:
    """Before any video credit is spent: dialogue must fit the clip. When the video model speaks the lines (sound on),
    clips that are too short are lengthened, and dialogue that cannot fit even the longest clip STOPS the run;
    with sound off the lines are voiced later (TTS), so it is only reported."""
    entries = dialogue.check(p, pid)
    bad = dialogue.problems(entries)
    if not bad:
        return
    if not p.project(pid)["video_audio"]:
        for e in bad:
            _d(p, pid, "motion", "warn", f"S{e['idx']:02d}: {e['advice']}", "dialogue_length")
        return
    fixed = dialogue.extend(p, entries)
    if fixed:
        _log(p, pid, f"Tăng thời lượng {fixed} clip cho vừa lời thoại")
    splits = [e for e in bad if e["status"] == "split"]
    if splits:
        raise _Stop("Thoại quá dài cho clip: " + "; ".join(f"S{e['idx']:02d} cần ~{e['needed']:g}s, tối đa {e['max']}s" for e in splits)
                    + " — rút gọn thoại hoặc tách cảnh rồi bấm Tiếp tục")


def _videos_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Clips for every scene (per-scene model), redo of outdated clips, Claude's video check when switched on."""
    from . import claude_tasks, lineage, regen
    _, cap_videos = _job_caps(p, pid)
    for r in llm_io.ready_for_video(p, pid):
        if _has(p, r["scene_id"], "video_gen", "'queued','running','succeeded','retryable','failed','pending_review','approved'"):
            continue
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type='video_gen' AND escalated=1", r["scene_id"]):
            continue
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen'", pid) >= cap_videos:
            raise _Stop(BUDGET_NOTE)
        _daily_cap(p)
        p.create_job(r["scene_id"], "video_gen")
    for sid, r in lineage.scan(p.conn, pid).items():
        if r["video_stale"] and r["video_job_id"] and not r["motion_stale"] and r["video_state"] in ("succeeded", "approved"):
            if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen'", pid) >= cap_videos:
                raise _Stop(BUDGET_NOTE)
            regen.regenerate_video(p, ctx.data_dir, r["video_job_id"], f"làm lại vì {r['video_stale']}")
    ctx.video_runner.submit_pending(pid)
    ctx.video_runner.poll_once(pid)
    for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='failed' AND escalated=0", (pid,)).fetchall():
        if not _count(p, "SELECT COUNT(*) FROM content_moderation_failures WHERE job_id=?", j["id"]):
            p.retry(j["id"], "autopilot: thử lại")   # ordinary failure: one more attempt (counts toward the limit)
    if claude_tasks.unchecked_videos(p, pid):
        r = claude_tasks.qc_video_batch(p, pid, ctx.llm, ctx.data_dir)
        if r["failed"]:
            _log(p, pid, f"QC video lỗi ở {len(r['failed'])} clip: {r['failed'][0][1][:120]}")
    for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='pending_review'", (pid,)):
        p.approve(j["id"], "ai_agent", "autopilot")
    fresh = lineage.summary(p.conn, pid)["videos"][0]
    total = len(_scene_rows(p, pid))
    return None if fresh == total else f"Video: {fresh}/{total} dùng được"


def _music_from_library(p: Pipeline, pid: int, data_dir: str, fallback: bool = False) -> bool:
    """Pick a background track of the person's own library that fits the scene moods (no credit spent). Used first only when the
    project asks for it; otherwise (fallback=True) only as a safety net when the AI music is unavailable or failed."""
    row = p.project(pid)
    if not fallback and not ("music_mode" in row.keys() and row["music_mode"] == "library"):
        return False
    picked = sound_lib.pick_music(p.conn, music.scene_moods(p, pid), music.total_duration_sec(p, pid), seed=pid)
    if picked is None:
        if not fallback:
            _log(p, pid, "Kho nhạc của bạn chưa có bản nhạc nền phù hợp → tạo bằng AI")
        return False
    _, selected_dir = music.project_dirs(data_dir, pid)
    try:
        music.use_library_track(selected_dir, picked["path"])
    except (ValueError, OSError) as e:
        _d(p, pid, "music", "warn", f"không dùng được nhạc từ kho ({picked['name']}): {e}", "library_music")
        return False
    _log(p, pid, f"Nhạc nền từ kho: {picked['name']}" + (f" ({picked['mood']})" if picked.get("mood") else ""))
    return True


def _music_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    drafts_dir, selected_dir = music.project_dirs(ctx.data_dir, pid)
    if os.listdir(selected_dir):
        return None
    if _music_from_library(p, pid, ctx.data_dir):
        return None
    if ctx.audio is None:
        _music_from_library(p, pid, ctx.data_dir, fallback=True)
        return None
    drafts = music.load_drafts(drafts_dir)
    if not drafts:
        from . import claude_tasks
        brief = claude_tasks.music_brief(p, pid, ctx.llm)
        music.submit_drafts(ctx.audio, drafts_dir, brief["prompt"], brief["length_ms"], brief["instrumental"], 1, ledger=(p.conn, pid))
        _log(p, pid, "Đã gửi 1 bản nhạc nền" + (" (brief do Claude viết)" if brief.get("brief") else ""))
        return "Nhạc nền: đang tạo"
    music.refresh_drafts(ctx.audio, drafts_dir)
    drafts = music.load_drafts(drafts_dir)
    ok = [i for i, d in enumerate(drafts) if d["state"] == "succeeded"]
    if ok:
        music.select_draft(drafts_dir, selected_dir, ok[0])
        return None
    if any(d["state"] == "running" for d in drafts):
        return "Nhạc nền: đang tạo"
    if _music_from_library(p, pid, ctx.data_dir, fallback=True):
        _log(p, pid, "Nhạc AI không tạo được → dùng nhạc từ kho của bạn")
        return None
    _log(p, pid, "Nhạc nền không tạo được → ghép không nhạc")
    _d(p, pid, "music", "warn", "nhạc nền không tạo được, video cuối sẽ KHÔNG có nhạc (lỗi âm thầm)", "degraded")
    return None


def _sfx_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Let the AI judge whether sound effects are worth adding (scene changes, accents) and add the ones it picks. Once per project;
    it may decide to add none. Failures never stop the video: it just goes without."""
    marker = os.path.join(audio_lib.assets_dir(ctx.data_dir, pid), "ai_sfx_done")
    if os.path.exists(marker) or ctx.llm is None or not p.conn.execute(f"SELECT 1 FROM sounds WHERE {sound_lib.TRUSTED_SQL} LIMIT 1").fetchone():
        return None
    if not [c for c in final_cut.collect_clips(p, ctx.data_dir, pid) if c["path"]]:
        return None
    try:
        plan = sfx_plan.propose(ctx.llm, p, ctx.data_dir, pid)
        chosen = [{"id": c["id"], "at": c["at"], "volume": c["volume"]} for c in plan["cues"]]
        added = sfx_plan.apply(p, ctx.data_dir, pid, chosen) if chosen else 0
        _log(p, pid, (f"Hiệu ứng âm thanh: thêm {added} — " if added else "Hiệu ứng âm thanh: không thêm — ") + (plan["summary"] or "AI thấy không cần")[:160])
    except sfx_plan.SfxPlanError as e:
        if e.not_ready:
            _log(p, pid, "Hiệu ứng âm thanh: bỏ qua (kho chưa được nghe/nhận dạng nên không tự chọn để tránh nhầm)")
            return None
        _log(p, pid, f"Hiệu ứng âm thanh bỏ qua: {str(e)[:120]}")
        _d(p, pid, "music", "warn", f"AI chọn hiệu ứng âm thanh thất bại, video cuối không có hiệu ứng: {e}", "sfx_plan")
    except (llm_runner.LlmError, OSError) as e:
        _log(p, pid, f"Hiệu ứng âm thanh bỏ qua: {str(e)[:120]}")
        _d(p, pid, "music", "warn", f"AI chọn hiệu ứng âm thanh thất bại, video cuối không có hiệu ứng: {e}", "sfx_plan")
    with open(marker, "w", encoding="utf-8") as f:
        f.write("done")
    return None


def tick(p: Pipeline, project_id: int, ctx: Context) -> str:
    """One step of the run. Returns the resulting state."""
    from . import delivery
    st = status(p, project_id)["state"]
    if st != RUNNING:
        return st
    p.actor = p.project(project_id)["autopilot_user"]
    if p.project(project_id)["paused"]:
        _set(p, project_id, note="Đang tạm dừng")
        return RUNNING
    try:
        phases = [("director", _director_phase), ("previz", _previz_phase), ("images", _images_phase), ("setcheck", _setcheck_phase),
                  ("motion", _motion_phase), ("voice", _voice_phase), ("videos", _videos_phase), ("music", _music_phase),
                  ("sfx", _sfx_phase)]
        for name, fn in phases:
            progress_note = fn(p, project_id, ctx)
            if progress_note is not None:
                blocked = _blocked_scenes(p, project_id)
                idle = not (_active(p, project_id, "image_gen") or _active(p, project_id, "video_gen"))
                if blocked and idle and name in ("images", "videos"):
                    note = "Cần bạn xử lý: " + "; ".join(blocked)
                    _set(p, project_id, ATTENTION, note)
                    _log(p, project_id, note)
                    _d(p, project_id, "autopilot", "warn", note, "needs_attention")
                    return ATTENTION
                _set(p, project_id, note=f"{PHASE_LABELS[name]} — {progress_note}")
                _log(p, project_id, f"{PHASE_LABELS[name]}: {progress_note}")
                return RUNNING
        res = delivery.deliver(p, project_id, ctx.data_dir, ctx.llm, render_fn=ctx.render or default_render, subtitle_fn=ctx.subtitle)
        out = res["final"]
        names = {"subtitle": "phụ đề", "endcard": "card cuối", "export": "bản xuất"}
        extra = "".join(f" + {names.get(kind, kind)}: {path}" for kind, path in res["layers"])
        for w in res["warnings"]:
            _log(p, project_id, f"Xuất bản: {w[:120]}")
        if any(kind == "subtitle" for kind, _ in res["layers"]):
            _log(p, project_id, "Đã thêm phụ đề")
        _set(p, project_id, DONE, f"Xong: {out}{extra}")
        _log(p, project_id, "Đã ghép video cuối")
        _restore_cfg(p, project_id)
        return DONE
    except _Wait as e:
        set_gates(p, project_id, {"waiting_for": e.gate})
        _set(p, project_id, WAITING, str(e))
        _log(p, project_id, str(e))
        return WAITING
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



# ---- gates (human checkpoints the person switches on) ----------------------------------------------------------------
GATE_DEFAULTS = {"bible": True, "pilot": False}


class _Wait(Exception):
    def __init__(self, gate: str, note: str):
        super().__init__(note)
        self.gate = gate


def get_gates(p: Pipeline, project_id: int) -> Dict:
    try:
        saved = json.loads(p.project(project_id)["autopilot_gates"] or "{}")
    except (ValueError, KeyError, IndexError, TypeError):
        saved = {}
    return {**GATE_DEFAULTS, "bible_done": False, "pilot_done": False, "waiting_for": None, **saved}


def set_gates(p: Pipeline, project_id: int, changes: Dict) -> None:
    gates = get_gates(p, project_id)
    gates.update(changes)
    p.set_project_field(project_id, "autopilot_gates", json.dumps(gates, ensure_ascii=False))


def _save_cfg(p: Pipeline, project_id: int) -> None:
    """Remember how the person reviews before the run switches the project to automatic QC (given back when it ends)."""
    row = p.project(project_id)
    if not row["autopilot_saved_cfg"]:
        p.set_project_field(project_id, "autopilot_saved_cfg", json.dumps(
            {"operating_mode": row["operating_mode"], "qc_review_floor": row["qc_review_floor"]}))


def _restore_cfg(p: Pipeline, project_id: int) -> None:
    raw = p.project(project_id)["autopilot_saved_cfg"]
    if not raw:
        return
    cfg = json.loads(raw)
    p.set_mode(project_id, cfg.get("operating_mode") or "human_qc")
    p.set_review_floor(project_id, cfg.get("qc_review_floor"))
    p.set_project_field(project_id, "autopilot_saved_cfg", None)


def reset(p: Pipeline, project_id: int, data_dir: Optional[str] = None) -> None:
    """Forget the automatic run's state (pictures and clips already made are kept)."""
    p.conn.execute("UPDATE projects SET autopilot_state=NULL, autopilot_note=NULL WHERE id=?", (project_id,))
    p.conn.commit()
    set_gates(p, project_id, {"bible_done": False, "pilot_done": False, "waiting_for": None})
    _restore_cfg(p, project_id)
    for marker in (os.path.join("layouts", ".autopilot_done"), os.path.join("qc_set", ".autopilot_done"), ".lint_done"):
        path = os.path.join(data_dir or os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")), str(project_id), marker)
        if os.path.exists(path):
            os.remove(path)


def _marker(ctx: Context, pid: int, *parts: str) -> str:
    path = os.path.join(ctx.data_dir, str(pid), *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _setcheck_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """One whole-set consistency look (once): outliers are redone with the fix sentence, within the job cap."""
    from . import claude_tasks
    marker = _marker(ctx, pid, "qc_set", ".autopilot_done")
    if os.path.exists(marker) or len(_scene_rows(p, pid)) < 2:
        return None
    try:
        r = claude_tasks.set_consistency(p, pid, ctx.llm, ctx.data_dir)
        issues = r.get("issues") or []
        cap_images, _ = _job_caps(p, pid)
        redone = 0
        for it in issues:
            if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", pid) >= cap_images:
                break
            try:
                claude_tasks.redo_from_set_check(p, pid, it["idx"], it.get("fix") or it["problem"])
                redone += 1
            except (ValueError, Exception):  # noqa: BLE001 - one scene that cannot be redone must not stop the run
                continue
        _log(p, pid, "QC đồng bộ cả bộ ảnh: " + (f"làm lại {redone} cảnh lệch" if redone else "ổn"))
    except (llm_runner.LlmError, ValueError, OSError) as e:
        _d(p, pid, "qc", "warn", f"autopilot bỏ qua QC đồng bộ: {e}", "set_check_skipped")
    with open(marker, "w") as f:
        f.write("1")
    return None if not _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state IN ('queued','running')", pid) \
        else "QC đồng bộ: đang gen lại cảnh lệch"


def _voice_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Character voices for the dialogue (TTS), then clips sized to the real voice. Skipped (with a note) when there is no audio
    provider or a speaker has no voice: subtitles still carry the lines."""
    from . import voice
    if ctx.audio is None:
        return None
    stat = voice.status(p.conn, pid, ctx.data_dir)
    if not stat["total"]:
        return None
    if stat["missing"]:
        r = voice.generate(p.conn, pid, ctx.audio, ctx.data_dir)
        if r["sent"]:
            _log(p, pid, f"Gửi {r['sent']} câu thoại cho TTS")
        if r["no_voice"]:
            _log(p, pid, "Chưa có giọng cho: " + ", ".join(r["no_voice"]) + " (các câu này chỉ có phụ đề)")
    if stat.get("running") or stat["missing"]:
        audio_lib.refresh(ctx.audio, audio_lib.assets_dir(ctx.data_dir, pid))
        stat = voice.status(p.conn, pid, ctx.data_dir)
        if stat.get("running"):
            return f"Giọng thoại: {stat.get('succeeded', 0)}/{stat['total']}"
    changes = voice.fit_durations(p.conn, pid, ctx.data_dir)
    if changes:
        _log(p, pid, f"Kéo dài {len(changes)} clip cho vừa giọng thật")
    return None
