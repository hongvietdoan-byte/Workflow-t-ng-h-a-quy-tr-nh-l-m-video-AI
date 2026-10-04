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
from . import access
import json
import re
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import audio_lib, previz, sfx_plan, sound_lib, subtitles, dialogue, diag, ffmpeg_studio, final_cut, llm_io, llm_runner, music, perf
from .pipeline import Pipeline, PipelinePaused

RUNNING, WAITING, STOPPED, ATTENTION, DONE, ERROR = "running", "waiting", "stopped", "needs_attention", "done", "error"
QUEUED = "queued"   # approved, waiting for a free slot (see Manager.max_parallel)
PHASE_LABELS = {"director": "Director (Character Bible + thông số cảnh)", "previz": "Dựng layout / storyboard", "images": "Gen ảnh + QC",
                "plates": "Nền 3D của bối cảnh (render theo góc máy)", "platefix": "Kiểm nền 3D trong clip", "lipsync": "Khớp môi (sau khi có clip)", "setcheck": "QC đồng bộ cả bộ ảnh", "endframes": "Ảnh khung cuối (shot đổi trạng thái)", "storyboard": "Duyệt storyboard trước khi gen video", "clips": "Xem clip còn lỗi", "motion": "Motion prompt", "voice": "Giọng thoại", "voicefirst": "Giọng trước hình (khóa timeline)", "storycheck": "Người xem lần đầu đọc bảng shot", "videos": "Gen video + QC video",
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


def default_context(p: Pipeline, data_dir: str) -> Context:
    """Providers from the environment (IMAGE_PROVIDER, VIDEO_PROVIDER, ANTHROPIC_API_KEY / LLM_PROVIDER, AUDIO_PROVIDER)."""
    from .adapters import factory
    from .runner import ImageRunner, VideoRunner
    image, video = factory.image_provider(), factory.video_provider()
    if image is None or video is None:
        raise ValueError("Chưa cấu hình nhà cung cấp ảnh/video (IMAGE_PROVIDER, VIDEO_PROVIDER).")
    llm = llm_runner.client_from_env(ledger=llm_runner.db_file(p.conn))     # Claude API calls -> cost ledger + Claude cap
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


def _tick_set(p: Pipeline, pid: int, state: Optional[str] = None, note: Optional[str] = None) -> bool:
    """A tick's own write: only while the run is still RUNNING in the database (one conditional UPDATE, so a stop() / reset() made
    by the person during the tick is never overwritten — S14.3 B1b). False = not written (the person stopped it meanwhile)."""
    cur = p.conn.execute("UPDATE projects SET autopilot_state=COALESCE(?, autopilot_state), autopilot_note=COALESCE(?, autopilot_note),"
                         " autopilot_beat=? WHERE id=? AND autopilot_state=?", (state, note, time.time(), pid, RUNNING))
    p.conn.commit()
    return cur.rowcount > 0


class _Stopped(Exception):
    """The run is no longer RUNNING (the person stopped / reset it during this tick): nothing more is sent or written."""


def _still_running(p: Pipeline, pid: int) -> None:
    """Checked right before a paid send / the delivery: stop() does not wait for the running tick (S14.3 B1b)."""
    if status(p, pid)["state"] != RUNNING:
        raise _Stopped()


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
    from . import shots
    n_story = shots.story_scene_count(p, project_id) if shots.active(p, project_id) else len(scenes)   # v3: count script scenes
    if n_story > MAX_SCENES:
        out.append(f"Chế độ này dành cho clip ngắn: tối đa {MAX_SCENES} cảnh (kịch bản có {n_story}).")
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
    access.need_edit(p, project_id, "bật chạy tự động")
    _owner(p, project_id, user)
    _save_cfg(p, project_id)
    if _count(p, "SELECT COUNT(*) FROM characters WHERE project_id=?", project_id) and not get_gates(p, project_id)["bible"]:
        llm_io.lock_character_bible(p, project_id)      # already analysed by hand and no review wanted: freeze it
    p.set_mode(project_id, "auto")
    p.set_review_floor(project_id, None)   # nothing may wait for a human
    p.set_paused(project_id, False)
    set_gates(p, project_id, {"bible_done": False, "pilot_done": False, "storyboard_ok": None, "waiting_for": None,
                              "job_cap_from": _last_job_id(p)})          # S14.16: machine-made jobs are counted from here
    _set(p, project_id, RUNNING, "Đã duyệt phân cảnh, đang chạy tự động")
    _log(p, project_id, "Bạn đã duyệt phân cảnh → bắt đầu chạy tự động")
    from . import known_issues
    for line in known_issues.warning_lines(p.conn, project_id):   # a paused stage switched back on shows its open faults first
        _d(p, project_id, "autopilot", "warn", "Khâu có lỗi đã biết chưa sửa: " + line, "known_issues")


def resume(p: Pipeline, project_id: int, user: Optional[str] = None) -> None:
    """Continue after a stop / a checkpoint / needs_attention / error / restart. At a checkpoint, continuing = the person approves it."""
    access.need_edit(p, project_id, "tiếp tục chạy tự động")
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
    elif gates.get("waiting_for") == "storyboard":
        from . import storyboard_gate
        _approve_held(p, project_id, "image_gen", "duyệt ở storyboard")
        set_gates(p, project_id, {"storyboard_ok": storyboard_gate.fingerprint(p, project_id), "waiting_for": None})
        _log(p, project_id, "Bạn đã duyệt storyboard → viết motion prompt và gen video")
    elif gates.get("waiting_for") == "voice_fit":        # "Tiếp tục" = keep the clips (remaking them is its own button)
        set_gates(p, project_id, {"waiting_for": None, "voice_fit_decided": "keep"})
    elif gates.get("waiting_for") == "length":           # S2.3: "Tiếp tục" = the voiced length is accepted (or the plan was edited:
        set_gates(p, project_id, {"waiting_for": None, "length_decided": True})   # the phase measures again and locks)
        _log(p, project_id, "Bạn đã xem độ dài theo giọng thật → khóa timeline và tiếp tục")
    elif gates.get("waiting_for") == "budget":           # approved in Bước 1 → the images phase checks it again
        set_gates(p, project_id, {"waiting_for": None})
    elif gates.get("waiting_for") == "clips":
        n = _approve_held(p, project_id, "video_gen", "giữ sau khi xem")
        set_gates(p, project_id, {"waiting_for": None})
        _log(p, project_id, f"Bạn đã xem {n} clip còn lỗi → tiếp tục")
    set_gates(p, project_id, {"job_cap_from": _last_job_id(p)})   # S14.16: the person looked — the job cap counts again from here
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
    rows += [("Video dùng được", summ["videos"][0], n), ("Nhạc nền", 1 if os.listdir(selected_dir) or music.is_off(p, project_id) else 0, 1),
             ("Bản giao", 1 if fin is not None or os.path.exists(os.path.join(data_dir, str(project_id), "output", "FINAL_VIDEO.mp4")) else 0, 1)]
    return rows


def stop(p: Pipeline, project_id: int, note: str = "Đã dừng theo yêu cầu") -> None:
    access.need_edit(p, project_id, "dừng chạy tự động")
    _set(p, project_id, STOPPED, note)
    _log(p, project_id, note)
    _restore_cfg(p, project_id)


# ---- the tick ---------------------------------------------------------------------------------
def _count(p: Pipeline, sql: str, *args) -> int:
    return p.conn.execute(sql, args).fetchone()[0]


def _last_job_id(p: Pipeline) -> int:
    return int(p.conn.execute("SELECT COALESCE(MAX(id), 0) FROM jobs").fetchone()[0])


def _shots(p: Pipeline, pid: int):
    """(image shots, video shots) of the project: shots that need their own start picture, every shot for its clip."""
    from .shots import needs_own_image
    rows = _scene_rows(p, pid)
    return sum(1 for r in rows if needs_own_image(p.conn, r["id"])), len(rows)


def _job_caps(p: Pipeline, pid: int) -> int:
    """Người dùng duyệt 04/10 (S14.16): the automatic run's job cap of a project, by the PRODUCT — image shots × (1 + automatic
    picture redos) + video shots × (1 + automatic clip redos), the limits from pipeline.AUTO_REGEN_LIMIT. Only machine-made jobs
    count (jobs.origin 'auto'): reaching it means something abnormal (a loop making jobs), never a person clicking."""
    from .pipeline import AUTO_REGEN_LIMIT
    images, videos = _shots(p, pid)
    return images * (1 + AUTO_REGEN_LIMIT["image_gen"]) + videos * (1 + AUTO_REGEN_LIMIT["video_gen"])


def _machine_jobs(p: Pipeline, pid: int) -> Dict[str, int]:
    """Machine-made picture / clip jobs of the project since the run was (re)started (gates job_cap_from) — an order the provider
    never created (resent at once, core.runner._not_created) is not an attempt and does not count."""
    from .runner import RESEND_NOTE
    since = int(get_gates(p, pid).get("job_cap_from") or 0)
    out = {"image_gen": 0, "video_gen": 0}
    for r in p.conn.execute("SELECT j.type, COUNT(*) n FROM jobs j WHERE j.project_id=? AND j.origin='auto' AND j.id>? AND"
                            " j.type IN ('image_gen','video_gen') AND NOT (j.state='cancelled' AND EXISTS (SELECT 1 FROM jobs r"
                            " WHERE r.parent_job_id=j.id AND r.retry_reason LIKE ?)) GROUP BY j.type",
                            (pid, since, RESEND_NOTE + "%")).fetchall():
        out[r["type"]] = r["n"]
    return out


JOB_CAP_NOTE = "Chạm trần job do máy tạo"


def _job_cap_reason(p: Pipeline, pid: int) -> Optional[str]:
    """The stop text (numbers, project, how to open) when the machine-made jobs reached the product cap, else None."""
    from .pipeline import AUTO_REGEN_LIMIT
    made = _machine_jobs(p, pid)
    total, cap = made["image_gen"] + made["video_gen"], _job_caps(p, pid)
    if cap <= 0 or total < cap:                         # a project without shots never "reaches" its cap
        return None
    images, videos = _shots(p, pid)
    name = p.project(pid)["name"]
    return (f"{JOB_CAP_NOTE} (trần job do máy) của dự án '{name}': đã có {total} job do máy tạo (ảnh {made['image_gen']}, video "
            f"{made['video_gen']}) / trần {cap} = {images} shot ảnh × {1 + AUTO_REGEN_LIMIT['image_gen']} + {videos} shot video × "
            f"{1 + AUTO_REGEN_LIMIT['video_gen']} — bất thường (có thể vòng lặp tạo job thừa), đã dừng. Cách mở: xem 📊 Theo dõi / "
            "chẩn đoán, sửa nguyên nhân rồi bấm Tiếp tục (đếm lại từ lúc đó)")


def _job_cap_check(p: Pipeline, pid: int) -> None:
    why = _job_cap_reason(p, pid)
    if why:
        _d(p, pid, "autopilot", "error", why, "job_cap")
        raise _Stop(why)


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
    unwritten = _count(p, "SELECT COUNT(*) FROM characters WHERE project_id=? AND TRIM(COALESCE(description,''))!=''", pid) == 0
    planned = any((json.loads(s["data"] or "{}").get("image_prompt") or "").strip()
                  for s in p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)))
    if not _count(p, "SELECT COUNT(*) FROM characters WHERE project_id=?", pid) or (unwritten and not planned):
        # no Bible yet, or a "chạy lại Director" clone whose Bible was reset (core.compare.FRESH_BIBLE) and whose scenes have no plan.
        # GĐ5: with FEATURE_DIRECTOR_TWO_PASS=1 on a shot project this is Tầng A + one Tầng B call per scene; resume = "Tiếp tục" after a
        # failed run asks only the scenes that failed (the paid Tầng A answer and the passed scenes are reused)
        r = llm_runner.run_director(p, pid, ctx.llm, resume=True)
        set_gates(p, pid, {"timeline_locked": None, "length_decided": None})   # S2: a new shot plan is measured again
        n_shots = _count(p, "SELECT COUNT(*) FROM scenes WHERE project_id=?", pid)
        _log(p, pid, f"Director: {r['characters']} nhân vật, {r['scenes']} cảnh" + (f", {n_shots} shot" if n_shots != r["scenes"] else "")
             + (f" — hai lượt ({r['calls']} lượt Claude, chưa thử thật)" if r.get("two_pass") else ""))
        if r.get("flagged"):                               # Đạo diễn duyệt: the person sees it at Bước 1 (the Bible gate still waits)
            _d(p, pid, "director", "warn", "Đạo diễn duyệt: cảnh " + ", ".join(map(str, r["flagged"])) + " lệch ý đồ — xem màn Kịch bản",
               "director_review")
    missing = [f"S{s['idx']:02d}" for s in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))
               if not (json.loads(s["data"] or "{}").get("image_prompt") or "").strip()]
    if missing:
        raise _Stop("Cảnh chưa có prompt ảnh sau khi chạy Director: " + ", ".join(missing) + " — điền tay hoặc sửa kịch bản rồi bấm Tiếp tục")
    gates = get_gates(p, pid)
    flags = {}
    try:                                                    # F1: a Bible that contradicts the pictures is caught before any picture
        from . import claude_tasks
        claude_tasks.bible_check(p, pid, ctx.llm)
        flags = claude_tasks.bible_flags(p, pid)
    except (llm_runner.LlmError, ValueError) as e:
        _d(p, pid, "director", "warn", f"không kiểm được Bible với ảnh tài nguyên: {e}", "bible_check_skipped")
        if not gates["bible_done"]:                         # luật 1: a gate that could not run STOPS (e.g. the Claude cap is reached)
            raise _Wait("bible", f"Không kiểm được Character Bible với ảnh tài nguyên ({str(e)[:160]}) — dừng trước khi gen ảnh. Xử lý "
                                 "lỗi (vd nạp thêm tiền Claude) rồi chạy lại để kiểm, hoặc bấm Tiếp tục nếu bạn đã tự so mô tả với ảnh "
                                 "(chạy tiếp không kiểm)")
    if flags and not gates["bible_done"]:
        raise _Wait("bible", "Mô tả nhân vật mâu thuẫn với ảnh tài nguyên: " + "; ".join(f"{n}: {m[0]}" for n, m in flags.items())
                    + " — sửa ở màn Kịch bản (đề xuất sửa có sẵn) rồi bấm Tiếp tục")
    gaps = bible_gaps(p, pid)
    if gaps["no_lock"] and not gates["bible_done"]:           # O6: a character without a Lock drifts from shot to shot
        raise _Wait("bible", "Nhân vật chưa có Character Lock (nét nhận diện phải giữ): " + ", ".join(gaps["no_lock"])
                    + " — viết Lock ở màn Kịch bản (hoặc duyệt hồ sơ chuẩn ở ⚙ → Kho) rồi bấm Tiếp tục")
    for name in gaps["no_picture"]:
        _d(p, pid, "director", "warn", f"{name} chưa có ảnh tham chiếu ở Kho — model chỉ vẽ theo chữ, dễ lệch thiết kế", "no_reference")
    if gates["bible"] and not gates["bible_done"]:
        raise _Wait("bible", "Chờ bạn duyệt Character Bible (mô tả, Character Lock, giọng, ảnh mốc) ở màn Kịch bản rồi bấm Tiếp tục")
    llm_io.lock_character_bible(p, pid)
    return None


def bible_gaps(p: Pipeline, pid: int) -> Dict[str, List[str]]:
    """O6: characters the pictures would draw without their Lock (no lock rules and no approved standard profile), and characters
    with no reference picture at all. Only characters that appear in a scene count."""
    from . import assets
    used = set()
    for s in p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)):
        used |= {str(c).upper() for c in (json.loads(s["data"] or "{}").get("characters") or [])}
    no_lock, no_picture = [], []
    for c in p.conn.execute("SELECT * FROM characters WHERE project_id=? ORDER BY name", (pid,)).fetchall():
        if used and c["name"].upper() not in used:
            continue
        has_lock = bool((c["lock_rules"] or "").strip()) if "lock_rules" in c.keys() else False
        if not has_lock and not assets.standard_for(p.conn, pid, c["name"]):
            no_lock.append(c["name"])
        refs = (c["ref_asset_id"] if "ref_asset_id" in c.keys() else None) or (c["ref_image_ids"] if "ref_image_ids" in c.keys() else None)
        if not refs and not assets.link_characters(p.conn, pid, [c["name"]]).get(c["name"]):
            no_picture.append(c["name"])
    return {"no_lock": no_lock, "no_picture": no_picture}


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
                _log(p, pid, f"Rà storyboard: {len(review['issues'])} lưu ý liên tục (xem màn Kịch bản)")
    except (llm_runner.LlmError, ValueError, OSError) as e:
        _log(p, pid, f"Không dựng được layout, gen ảnh theo cách cũ: {str(e)[:150]}")
        _d(p, pid, "previz", "warn", f"autopilot bỏ qua layout: {e}", "previz_skipped")
    with open(marker, "w") as f:
        f.write("1")
    return None


def _images_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Returns None when every scene has an up-to-date approved image, else a progress message. With the pilot checkpoint on, a few
    representative scenes are made first and the run waits for the person."""
    from . import lineage, pilot, project_budget
    why = project_budget.gate_reason(p, pid)
    if why:                                               # the budget is locked before the first paid picture (user 2026-09-28)
        raise _Wait("budget", why)
    gates = get_gates(p, pid)
    if gates["pilot"] and not gates["pilot_done"] and not pilot.active(p, pid):
        pilot.start(p, pid)
        _log(p, pid, "Gen thử các cảnh đại diện trước")
    stale = {sid: r for sid, r in lineage.scan(p.conn, pid).items() if r["image_stale"] and r["image_job_id"]}
    from .shots import needs_own_image
    for scene in _scene_rows(p, pid):
        if pilot.allowed_scenes(p, pid, [scene["id"]]) == []:
            continue
        if not needs_own_image(p.conn, scene["id"]):    # v3 multi-shot: later shots of a group start from the group's picture
            continue
        if scene["id"] in stale:
            _job_cap_check(p, pid)
            if _shot_sends(p, scene["id"], "image_gen") >= _shot_cap("image_gen"):      # W7: the shot's own cap
                _d(p, pid, "image", "warn", f"S{scene['idx']:02d}: ảnh đã cũ nhưng shot đã gửi {_shot_cap('image_gen')} lần — không tự "
                   "làm lại", "shot_cap")
                continue
            p.reopen_approved(stale[scene["id"]]["image_job_id"], f"Nội dung cảnh đã đổi: {stale[scene['id']]['image_stale']}", fix="")
            continue
        if _has(p, scene["id"], "image_gen", "'approved','queued','running','succeeded','pending_review','retryable','failed'"):
            continue
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type='image_gen' AND escalated=1", scene["id"]):
            continue
        _job_cap_check(p, pid)
        _daily_cap(p, ctx)
        p.conn.execute("UPDATE scenes SET state='ready' WHERE id=? AND state='needs_attention'", (scene["id"],))
        _create_job(p, ctx, scene["id"], "image_gen")
    _still_running(p, pid)
    ctx.image_runner.submit_pending(pid)
    _budget_stop(p, pid, "image_gen")
    ctx.image_runner.poll_once(pid)
    _retry_or_hold(p, pid, "image_gen")
    from . import qc_scene
    if qc_scene.enabled():                                  # QC per script scene: one Claude call once all its frames exist
        r = qc_scene.run_ready_scenes(p, pid, ctx.llm, ctx.data_dir)
        for s, applied in r["reviewed"]:
            _log(p, pid, f"QC cảnh {s}: " + ", ".join(f"{k} {v}" for k, v in applied.items()))
        if r.get("waiting"):
            _log(p, pid, "QC Claude theo cảnh đang tắt — khung mới của cảnh " + ", ".join(map(str, r["waiting"])) + " chờ người duyệt")
        if r["failed"]:
            _log(p, pid, f"QC cảnh lỗi ở cảnh {r['failed'][0][0]}: {r['failed'][0][1]}")
            _stop_if_claude_blocked([(s, m) for s, m in r["failed"]])
    elif _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", pid):
        r = llm_runner.run_qc_batch(p, pid, ctx.llm, ctx.data_dir)
        if r["failed"]:
            _log(p, pid, f"QC lỗi ở {len(r['failed'])} ảnh: {r['failed'][0][1]}")
            _stop_if_claude_blocked(r["failed"])
    held = _approve_unflagged(p, pid, "image_gen")         # W15: a picture below a floor waits for the person (storyboard)
    if pilot.active(p, pid):
        if pilot.done(p, pid):
            raise _Wait("pilot", "Ảnh các cảnh gen thử đã xong — xem ở màn Storyboard, ổn thì bấm Tiếp tục để gen phần còn lại")
        return "Ảnh gen thử: đang làm"
    fresh = lineage.summary(p.conn, pid)["images"][0]
    total = len(_scene_rows(p, pid))
    if held and fresh + len(held) >= total and not _active(p, pid, "image_gen"):
        return None                                        # the rest waits at the storyboard for the person's eyes
    return None if fresh == total else f"Ảnh: {fresh}/{total} đã duyệt"


SERVE_ROUNDS = 400                      # at most this many polls per wake-up (~1,7 h at 15 s): never a thread left spinning
SERVE_GATES = ("storyboard", "pilot")   # gates reached AFTER the budget was approved: a redraw the person asks for there is sent


def serve_waiting(p: Pipeline, pid: int, ctx: Context) -> bool:
    """S6.4 (PH 25, trial #8): the run waits at the storyboard / pilot gate and the person sends a picture back to be redrawn — the new
    job used to sit queued until someone pressed the Storyboard screen's button. While waiting at such a gate the pictures already asked for are sent
    and collected (the same caps and budget locks as the images phase; nothing new is created, nothing approved — the person decides).
    True while picture jobs are still queued / running."""
    from . import project_budget
    if status(p, pid)["state"] != WAITING or get_gates(p, pid).get("waiting_for") not in SERVE_GATES:
        return False
    if project_budget.approval_pending(p, pid):          # yes / no only: no cost estimate on every poll
        return False
    if not (_count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state IN ('queued','running')", pid)):
        return False
    try:
        _daily_cap(p)                     # review B1b: the queued redraw itself is not counted here (cap 1, 0 sent → it goes)
        sent = ctx.image_runner.submit_pending(pid)
        _budget_stop(p, pid, "image_gen")
        ctx.image_runner.poll_once(pid)
        _retry_or_hold(p, pid, "image_gen")
    except _Stop as e:                    # a lock reached: said, and the gate keeps waiting
        _log(p, pid, f"Đang chờ ở cổng — không gửi ảnh vẽ lại: {e}")
        return False
    if sent:
        _log(p, pid, f"Đang chờ ở cổng — đã gửi {sent} ảnh vẽ lại bạn yêu cầu")
    return bool(_active(p, pid, "image_gen"))


class _Stop(Exception):
    pass


_LOGIN_CODES = ("auth", "config")
_LIMIT_CODES = ("usage_limit", "rate_limit")


def _stop_if_claude_blocked(failed) -> None:
    """Claude cannot answer at all (login refused / not set up, the plan's usage limit reached, out of credit, a ledger that cannot
    be written): stop with a clear note instead of asking it again on every tick (a real run asked 1,500+ times while the limit lasted). Resume once
    Claude is available again. Read from LlmError.code (the failed texts are llm_runner.FailText) — never from words in the text
    (S14.3 B1b: a QC note mentioning 'author' or a 'rate limit' sign stopped the run)."""
    coded = [(getattr(m, "code", None), str(m)) for _, m in failed]
    hit = next((m for c, m in coded if c in _LOGIN_CODES), None)
    if hit:
        raise _Stop("Claude từ chối đăng nhập / khóa API hoặc chưa cấu hình (" + hit[-80:] + ")")
    hit = next((m for c, m in coded if c in _LIMIT_CODES), None)
    if hit:
        raise _Stop("Claude đã hết hạn mức sử dụng — bấm Tiếp tục khi hạn mức được làm mới (" + hit[-80:] + ")")
    hit = next((m for c, m in coded if c == "out_of_credit"), None)
    if hit:
        raise _Stop("Hết tiền trên tài khoản Anthropic — nạp thêm rồi mở lại ở ⚙ → 💵 Ngân sách, bấm Tiếp tục (" + hit[-120:] + ")")
    hit = next((m for c, m in coded if c == "ledger"), None)
    if hit:                                   # paid Claude calls could not be written down: every next call is refused until fixed
        raise _Stop("Không ghi được sổ chi Claude — kiểm tra CSDL, mở lại Dashboard rồi bấm Tiếp tục (" + hit[-120:] + ")")
    # S14.16 (core.money_policy): the money amounts only warn — a 'budget' code is no reason to stop the run any more




def _budget_stop(p: Pipeline, pid: int, kind: str) -> None:
    """The spending limit (core.budget) refused to send this project's queued jobs and nothing of that kind is running: STOP with the
    reason (a model without a price, a broken price table, the cap reached) instead of ticking forever on 'Gen ảnh…'."""
    if _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type=? AND state='running'", pid, kind) or \
            not _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type=? AND state='queued'", pid, kind):
        return
    row = p.conn.execute("SELECT message FROM diag_events WHERE project_id=? AND stage=? AND code='budget'"
                         " AND (julianday('now') - julianday(last_at)) * 1440 < 2 ORDER BY id DESC LIMIT 1",
                         (pid, "image" if kind == "image_gen" else "video")).fetchone()
    if row is not None:
        raise _Stop("Dừng vì ngân sách: " + row["message"])
DAILY_NOTE = ("Đã chạm trần lượt gửi ảnh/video thật trong ngày (AUTOPILOT_DAILY_JOBS) — dừng; bấm Tiếp tục ngày mai hoặc nâng trần")


def _real(runner) -> bool:
    name = str(getattr(getattr(runner, "provider", None), "name", "") or "")
    return bool(name) and not name.startswith("mock")


def _daily_cap(p: Pipeline, ctx: Optional[Context] = None) -> None:
    """S14.1 (mục 3.1): the automatic run's daily cap counts the REAL paid sends of the day (perf.sends_today: ledger rows of any
    project, button or run; simulated mock* providers cost nothing) + the jobs already queued that this run's (real) runners will
    send — counted only when a NEW job is about to be made (ctx given), only in projects whose run is going (running, not paused) and
    not yet sent (no external_id: a sent job is already a ledger row). AUTOPILOT_DAILY_JOBS=0 = off. Only the automatic run is
    capped — a person's button is not."""
    limit = perf.daily_limit()
    if not limit:
        return
    queued = 0
    if ctx is not None:
        kinds = [k for k, r in (("image_gen", ctx.image_runner), ("video_gen", ctx.video_runner)) if _real(r)]
        if kinds:
            queued = _count(p, "SELECT COUNT(*) FROM jobs j JOIN projects pr ON pr.id=j.project_id WHERE j.state='queued'"
                               " AND (j.external_id IS NULL OR j.external_id='') AND pr.autopilot_state=? AND COALESCE(pr.paused, 0)=0"
                               " AND j.type IN (" + ",".join("?" * len(kinds)) + ")", RUNNING, *kinds)
    sent = perf.sends_today(p.conn)
    if sent + queued >= limit:
        raise _Stop(_daily_note(p, sent, queued, limit))


def _daily_note(p: Pipeline, sent: int, queued: int, limit: int) -> str:
    """S14.16: a real stop says its numbers — sends of the day, queued ones counted, the cap, the money of the day, how to open."""
    try:
        from . import budget
        b = budget.get(p.conn)
        usd = budget.spent(p.conn, since=perf._sql_midnight())["usd"]
        money = f"; đã chi hôm nay ≈ ${usd:.2f}" + (f", mức dự tính đợt thử ${b['usd']:.2f}" if b["enabled"] else "")
    except Exception:  # noqa: BLE001 - the stop itself must still be said
        money = ""
    return (DAILY_NOTE + f" ({sent} lượt đã gửi" + (f" + {queued} job đang chờ gửi" if queued else "") + f", trần {limit} lượt/ngày"
            + money + ")")


def _create_job(p: Pipeline, ctx: Context, scene_id: int, kind: str) -> int:
    """A new picture / clip job of the automatic run, the daily cap checked and the job made under budget.SPEND_LOCK (two runs cannot
    both take the last place of the day)."""
    from . import budget
    p.conn.commit()        # never wait for the lock inside an open write transaction: the holder may need the database (deadlock)
    with budget.SPEND_LOCK:
        _daily_cap(p, ctx)
        return p.create_job(scene_id, kind)


def _storyboard_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Every start picture is ready: wait for the person to look at the whole storyboard before any video credit is spent (W1).
    A picture changed after the approval (redo, set check) brings the checkpoint back."""
    from . import storyboard_gate
    gates = get_gates(p, pid)
    held = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review'", (pid,)).fetchone()[0]
    if not held and (not gates["storyboard"] or gates.get("storyboard_ok") == storyboard_gate.fingerprint(p, pid)):
        return None                                         # pictures held below a floor stop here even with the checkpoint off
    if not held and _qc_trusted(p, pid, ctx):
        return None
    raise _Wait("storyboard", "Ảnh khung đầu đã đủ (" + storyboard_gate.summary(p, pid, ctx.data_dir if ctx else None) + (f", {held} ảnh dưới mức sàn chờ bạn xem" if held else "")
                              + ") — xem “🎞 Storyboard” ở màn Storyboard, sửa/gen lại shot sai, rồi bấm “Duyệt storyboard” để gen video")


def _plates_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """V4 location pack (feature location_plates): every shot set at a place with a registered 3D model gets its plate before any
    picture (one Blender run per place + time/weather, shared cache). A place with no 3D model is said once, not skipped silently."""
    from . import features, formats, location_pack, place_refs
    if not features.on("location_plates") and not place_refs.enabled():
        return None                                  # place_render_refs: the same renders, sent as reference pictures (no composite)
    size = formats.spec(formats.project_aspect(p.project(pid)) or "9:16")["deepix"]
    w, h = (int(v) for v in str(size).lower().split("x"))
    if features.on("location_plates"):
        photos = location_pack.ensure_photo_plates(p.conn, pid, ctx.data_dir, (w, h))     # tier 2: in-game photo of the place
        if photos:
            _log(p, pid, f"Nền từ ảnh chụp trong game (cấp 2, chưa có mô hình 3D): {len(photos)} shot")
    items = location_pack.plan(p.conn, pid)
    if not items:
        return None
    for it in items:
        if it["weather_problem"]:
            _d(p, pid, "image", "warn", f"shot {it['idx']}: {it['weather_problem']}", "weather")
        if it.get("spot_problem"):
            _d(p, pid, "image", "warn", f"shot {it['idx']}: {it['spot_problem']}", "plate_spot")
        if it.get("needs"):                               # S5.7: the shot's picture waits — said, with what to write
            _d(p, pid, "image", "error", f"shot {it['idx']}: {it['needs']}", "plate_view")
        elif it.get("view_problem"):
            _d(p, pid, "image", "warn", f"shot {it['idx']}: {it['view_problem']}", "plate_view")
        if it.get("light_problem"):
            _d(p, pid, "image", "warn", f"shot {it['idx']}: {it['light_problem']}", "practical_lights")
    idx = location_pack.index(ctx.data_dir, pid)
    if all(str(it["scene_id"]) in idx and idx[str(it["scene_id"])].get("key") == it["key"] for it in items):   # failed ones included
        return None
    location_pack.ensure_plates(p.conn, pid, ctx.data_dir, os.path.dirname(os.path.abspath(ctx.data_dir)), (w, h),
                                log=lambda m: _log(p, pid, m))
    return None


def _lipsync_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """V4 GĐ3: the finished clips of the "post" shots are lip-synced to our voice lines (sync.so). Without a key the step is said once
    and skipped — the clips keep their own mouths, never silently."""
    from . import ffmpeg_studio, features, lipsync
    if not features.on("lip_sync"):
        return None
    from .adapters import syncso
    provider = syncso.from_env_or_none() if lipsync.post_available() else None
    if provider is None:
        # user decision 2026-09-26: no sync.so account — close shots are made WITH the voice (Seedance), the rest keep their mouths.
        # Said once per shot (diag), never an error, never a paid call.
        marker = _marker(ctx, pid, ".lipsync_nokey")
        if not os.path.exists(marker):
            for s in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
                note = lipsync.no_post_note(json.loads(s["data"] or "{}"))
                if note:
                    diag.record(p.conn, "video", "info", f"S{s['idx']:02d}: {note}", "lipsync_no_post", pid, s["id"])
            open(marker, "w").close()
        return None
    if not any(r["method"] == "post" for r in lipsync.plan(p.conn, pid)):
        return None
    _still_running(p, pid)
    c = lipsync.post_tick(p, pid, ctx.data_dir, provider, ffmpeg_studio.find_ffmpeg(), log=lambda m: _log(p, pid, m))
    return f"Khớp môi: còn {c['running'] + c['sent']} clip" if c["running"] or c["sent"] else None


def _plate_fallback_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """V4: a mode-1 clip whose video model redrew the place (plate_qc below the threshold) is made again ONCE in mode 2 (the character
    acts on green and is keyed onto the plate) — a changed input, counted as a regeneration."""
    from . import features, location_pack, regen
    if not features.on("location_plates"):
        return None
    store = location_pack.video_qc(ctx.data_dir, pid)
    for sid, rec in store.items():
        if rec.get("ok") or rec.get("mode") != "first_frame" or rec.get("fallback"):
            continue
        row = p.conn.execute("SELECT data FROM scenes WHERE id=?", (int(sid),)).fetchone()
        job = p.conn.execute("SELECT * FROM jobs WHERE id=?", (rec["job_id"],)).fetchone()
        if row is None or job is None or job["state"] not in ("succeeded", "approved"):
            continue
        if p._retries_exhausted(job):                      # S14.16: at the clip's automatic limit no new clip — the scene is not
            p._limit_said(job)                             # switched to green screen either; the person decides (📥)
            location_pack.record_video_qc(ctx.data_dir, pid, int(sid), rec["job_id"], dict(rec, fallback=True), rec["mode"])
            continue
        data = json.loads(row["data"] or "{}")
        data["plate_mode"] = "green"
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), int(sid)))
        p.conn.commit()
        location_pack.record_video_qc(ctx.data_dir, pid, int(sid), rec["job_id"], dict(rec, fallback=True), rec["mode"])
        try:
            new = regen.regenerate_video(p, ctx.data_dir, rec["job_id"], f"nền bị vẽ lại (điểm {rec.get('score')}) → diễn trên phông xanh",
                                         auto=True)              # S14.16: counted on the clip's automatic limit
        except Exception as e:  # noqa: BLE001 - say it, never loop on it
            _d(p, pid, "video", "warn", f"shot {sid}: không gen lại được sang cách 2 ({e})", "plate_fallback")
            continue
        if new is None:                                      # the clip's automatic limit: the person decides (📥)
            continue
        _log(p, pid, f"Shot {sid}: video vẽ lại nền 3D → gen lại cách 2 (phông xanh + ghép), job {new}")
        return "Gen lại clip nền 3D (cách 2)"
    return None


def _end_frame_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """K1: every start picture is approved — draw the end frame of each shot that changes state (feature `end_frames`), so the
    storyboard shows both frames and the clip goes out as first + last frame."""
    from . import end_frames
    if not end_frames.enabled():
        return None
    queued = end_frames.queue(p, pid)
    if queued:
        _log(p, pid, f"Vẽ khung cuối cho {len(queued)} shot đổi trạng thái (K1)")
    provider = getattr(ctx.image_runner, "provider", None)
    if provider is None:
        return None
    end_frames.tick(p, pid, provider, ctx.data_dir)
    left = end_frames.pending(p, pid)
    return f"Khung cuối: còn {left} ảnh" if left else None


def _qc_trusted(p: Pipeline, pid: int, ctx: Optional[Context]) -> bool:
    """W8: the storyboard checkpoint is skipped when the QC agent has earned it on this look (effectiveness.look_trust) and the
    storyboard raises no flag — only with the feature `storyboard_auto_trust` on. The skip is written in the log with its numbers."""
    from . import effectiveness, features, image_models, storyboard_gate
    if not features.on("storyboard_auto_trust"):
        return False
    proj = p.project(pid)
    trust = effectiveness.look_trust(p.conn, proj["look"] if "look" in proj.keys() else None, image_models.of_project(proj))
    if not trust["trusted"] or any(storyboard_gate.flags(p, pid, ctx.data_dir if ctx else None).values()):
        return False
    set_gates(p, pid, {"storyboard_ok": storyboard_gate.fingerprint(p, pid)})
    _log(p, pid, f"Bỏ qua cổng storyboard: QC khớp người {trust['agreement']:.0%} trên {trust['pairs']} ảnh cùng look, "
                 "storyboard không có cờ (W8)")
    return True


def _motion_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Motion prompts for scenes without one or with an outdated one; then (once) the prompt check, whose revised prompts are used."""
    from . import claude_tasks, lineage, seedance_refs
    rows = _scene_rows(p, pid)
    if seedance_refs.enabled(p.conn, pid):
        try:                                               # ONE call: the Director's Vietnamese fields → English (review 2026-09-27)
            n = claude_tasks.translate_motion_fields(p, pid, ctx.llm)
            if n:
                _log(p, pid, f"Dịch trường hành động/diễn xuất sang tiếng Anh cho {n} shot (1 lượt Claude)")
        except (llm_runner.LlmError, ValueError) as e:
            _d(p, pid, "motion", "warn", f"không dịch được trường tiếng Việt ({e}) — prompt nhóm sẽ bị chặn khi gửi nếu còn tiếng Việt",
               "translate_skipped")
    stale_ids = [sid for sid, r in lineage.scan(p.conn, pid).items() if r["motion_stale"] and seedance_refs.uses_refs(p.conn, sid)]
    by_code = seedance_refs.code_motion(p, pid, redo_ids=stale_ids)   # Seedance reference shots: from the Director's fields, no Claude
    if by_code:
        _log(p, pid, f"Motion prompt viết bằng code (nhóm Seedance): {by_code} shot — không gọi Claude")
    missing = [s for s in rows if not _count(p, "SELECT COUNT(*) FROM motion_prompts WHERE scene_id=?", s["id"])]
    if missing:
        r = llm_runner.run_motion(p, pid, ctx.llm, ctx.data_dir)
        _log(p, pid, f"Claude viết {r['scenes']} motion prompt")
    stale = sorted(r["idx"] for r in lineage.scan(p.conn, pid).values() if r["motion_stale"] and r["image_job_id"])
    if stale:
        llm_runner.run_motion(p, pid, ctx.llm, ctx.data_dir, only_idx=stale)
        _log(p, pid, f"Viết lại motion prompt cảnh {', '.join(map(str, stale))} (ảnh/cảnh đã đổi)")
    marker = _marker(ctx, pid, ".lint_done")
    if not os.path.exists(marker) and not stale and rows and all(seedance_refs.uses_refs(p.conn, s["id"]) for s in rows):
        with open(marker, "w") as f:                       # every prompt came from the Director's fields: no Claude lint to pay for
            f.write("code")
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
    with sound off the lines are voiced later (TTS) and need the same time, so the same applies."""
    entries = dialogue.check(p, pid)
    bad = dialogue.problems(entries)
    if not bad:
        return
    fixed = dialogue.extend(p, entries)   # W16/D9: with the model's sound off the lines are voiced later (TTS) — they need the time too
    if fixed:
        _log(p, pid, f"Tăng thời lượng {fixed} clip cho vừa lời thoại")
    splits = [e for e in bad if e["status"] == "split"]
    if splits:
        raise _Stop("Thoại quá dài cho clip: " + "; ".join(f"S{e['idx']:02d} cần ~{e['needed']:g}s, tối đa {e['max']}s" for e in splits)
                    + " — rút gọn thoại hoặc tách cảnh rồi bấm Tiếp tục")


TRANSIENT = re.compile(r"timeout|timed out|rate.?limit|too many requests|\b429\b|\b50[0-4]\b|server_error|temporar|connection|"
                       r"network|reset by peer|unavailable|poll_error", re.I)
def _shot_cap(kind: str) -> int:
    """W7: sends of one shot the run makes by itself = 1 + pipeline.AUTO_REGEN_LIMIT (S14.16: picture 1 + 3, clip 1 + 2)."""
    from .pipeline import AUTO_REGEN_LIMIT
    return 1 + AUTO_REGEN_LIMIT.get(kind, 2)


def _transient(p: Pipeline, job_id: int) -> bool:
    """O5/W9: was the failure temporary (network, timeout, overload)? Only those are retried by themselves; a refusal or a bad
    input fails the same way again and costs again."""
    row = p.conn.execute("SELECT note FROM job_events WHERE job_id=? AND to_state='failed' ORDER BY id DESC LIMIT 1", (job_id,)).fetchone()
    return bool(row and TRANSIENT.search(row["note"] or ""))


def _shot_sends(p: Pipeline, scene_id: int, kind: str) -> int:
    """How many times this shot's picture/clip was really sent (an order the provider never created does not count)."""
    from .runner import RESEND_NOTE
    return _count(p, "SELECT COUNT(*) FROM jobs j WHERE j.scene_id=? AND j.type=? AND j.external_id IS NOT NULL AND NOT (j.state='cancelled'"
                     " AND EXISTS (SELECT 1 FROM jobs r WHERE r.parent_job_id=j.id AND r.retry_reason LIKE ?))",
                  scene_id, kind, RESEND_NOTE + "%")


def _retry_or_hold(p: Pipeline, pid: int, kind: str) -> None:
    for j in p.conn.execute("SELECT j.id, j.scene_id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type=?"
                            " AND j.state='failed' AND j.escalated=0", (pid, kind)).fetchall():
        if kind == "video_gen" and _count(p, "SELECT COUNT(*) FROM content_moderation_failures WHERE job_id=?", j["id"]):
            continue
        if _transient(p, j["id"]):
            p.retry(j["id"], "autopilot: thử lại sau lỗi tạm thời")    # automatic: at AUTO_REGEN_LIMIT pipeline escalates + says (📥)
        else:
            p.conn.execute("UPDATE jobs SET escalated=1 WHERE id=?", (j["id"],))
            p.conn.commit()
            _d(p, pid, "video" if kind == "video_gen" else "image", "warn",
               f"S{j['idx']:02d}: lỗi không tạm thời — không tự thử lại, xem ở Bước "
               + ("4" if kind == "video_gen" else "2"), "not_retried")


def _video_sends(p: Pipeline, pid: int) -> int:
    """Video jobs counted against the job cap: an order the provider never created (resent at once, core.runner._not_created) is
    not an attempt and must not use up the cap."""
    from .runner import RESEND_NOTE
    return _count(p, "SELECT COUNT(*) FROM jobs j WHERE j.project_id=? AND j.type='video_gen' AND NOT (j.state='cancelled' AND EXISTS"
                     " (SELECT 1 FROM jobs r WHERE r.parent_job_id=j.id AND r.retry_reason LIKE ?))", pid, RESEND_NOTE + "%")


def _flag_reasons(p: Pipeline, job) -> List[str]:
    """Why a result waiting for review must not be approved automatically: a blocking criterion below its floor (wrong face, broken
    hands, floating) or still faulty after the last automatic fix."""
    from .pipeline import hard_failures
    scores = {r["criterion"]: r["score"] for r in p.conn.execute("SELECT criterion, score FROM qc_results WHERE job_id=?", (job["id"],))}
    out = hard_failures(scores, "video" if job["type"] == "video_gen" else "image")
    if "scene_qc_hold" in scores:                          # QC per scene kept it for a person (doubt / shot table / code flag)
        out.append("QC cảnh giữ cho người xem")
    if job["escalated"]:
        out.append("hết lượt tự sửa")
    if job["type"] == "video_gen":
        from . import hero_takes
        t4 = hero_takes.hold_reason(p.conn, job)
        if t4:
            out.append(t4)
    return out


def _hero_block(p: Pipeline, pid: int, scene_id: int) -> Optional[str]:
    """S0.14 T4: why the ⭐ shot may not get its second take (None = it may) — the shot's send cap and the project's job cap hold."""
    if _shot_sends(p, scene_id, "video_gen") >= _shot_cap("video_gen"):
        return f"shot đã gửi {_shot_cap('video_gen')} lần"
    if _job_cap_reason(p, pid):
        return "đã chạm trần job do máy tạo của dự án"
    return None


def _approve_unflagged(p: Pipeline, pid: int, kind: str) -> List[str]:
    """Approve the waiting results that nothing flags; return 'S03: character 0.40 < 0.60' notes for the ones held for a person."""
    held = []
    for j in p.conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type=?"
                            " AND j.state='pending_review'", (pid, kind)).fetchall():
        why = _flag_reasons(p, j)
        if why:
            held.append(f"S{j['idx']:02d}: " + ", ".join(why))
        else:
            p.approve(j["id"], "ai_agent", "autopilot")
    return held


def _approve_held(p: Pipeline, pid: int, kind: str, note: str) -> int:
    """The person looked and went on: what was held for them counts as accepted."""
    rows = p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type=? AND state='pending_review'", (pid, kind)).fetchall()
    for r in rows:
        p.approve(r["id"], "user", note)
    return len(rows)


def _videos_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Clips for every scene (per-scene model), redo of outdated clips, Claude's video check when switched on."""
    from . import claude_tasks, lineage, regen
    for r in llm_io.ready_for_video(p, pid):
        if _has(p, r["scene_id"], "video_gen", "'queued','running','succeeded','retryable','failed','pending_review','approved'"):
            continue
        if _count(p, "SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type='video_gen' AND escalated=1", r["scene_id"]):
            continue
        _job_cap_check(p, pid)
        _create_job(p, ctx, r["scene_id"], "video_gen")
    for sid, r in lineage.scan(p.conn, pid).items():
        if r["video_stale"] and r["video_job_id"] and not r["motion_stale"] and r["video_state"] in ("succeeded", "approved"):
            _job_cap_check(p, pid)
            if _shot_sends(p, sid, "video_gen") >= _shot_cap("video_gen"):      # O3/W6: an outdated clip is not remade past the shot's cap
                _d(p, pid, "video", "warn", f"clip của shot #{sid} đã cũ ({r['video_stale']}) nhưng đã gửi {_shot_cap('video_gen')} lần — "
                   "không tự làm lại, xem ở màn Video", "shot_cap")
                continue
            regen.regenerate_video(p, ctx.data_dir, r["video_job_id"], f"làm lại vì {r['video_stale']}")
    _still_running(p, pid)
    ctx.video_runner.submit_pending(pid)
    _budget_stop(p, pid, "video_gen")
    ctx.video_runner.poll_once(pid)
    _retry_or_hold(p, pid, "video_gen")
    if claude_tasks.unchecked_videos(p, pid):
        r = claude_tasks.qc_video_batch(p, pid, ctx.llm, ctx.data_dir)
        if r["failed"]:
            _log(p, pid, f"QC video lỗi ở {len(r['failed'])} clip: {r['failed'][0][1][:120]}")
            _stop_if_claude_blocked(r["failed"])
    from . import hero_takes                                # S0.14 T4: a ⭐ shot gets a second take to choose from (flag hero_takes)
    for line in hero_takes.step(p, pid, ctx.data_dir, lambda sid: _hero_block(p, pid, sid)):
        _log(p, pid, line)
    held = _approve_unflagged(p, pid, "video_gen")         # W15: a clip still faulty after its fixes is never approved blindly
    if held and not _active(p, pid, "video_gen"):
        raise _Wait("clips", f"{len(held)} clip QC còn lỗi (" + "; ".join(held[:3]) + ") — xem ở màn Video: giữ, sửa hoặc gen lại, "
                             "rồi bấm Tiếp tục (clip còn chờ sẽ được giữ như bạn đã xem)")
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


TIMED_DRAFTS = 2                       # music model changes sections late/softly in some drafts (2A): make two, keep the better one


def _music_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    drafts_dir, selected_dir = music.project_dirs(ctx.data_dir, pid)
    if os.listdir(selected_dir):
        return None
    if music.is_off(p, pid):
        return None   # D5: "không dùng nhạc" is a choice, not a gap to fill with a paid track
    if _music_from_library(p, pid, ctx.data_dir):
        return None
    if ctx.audio is None:
        _music_from_library(p, pid, ctx.data_dir, fallback=True)
        return None
    drafts = music.load_drafts(drafts_dir)
    from . import music_timing, shots
    timed = music_timing.timed_brief(p, pid) if shots.active(p, pid) else None
    if not drafts:
        if timed:                    # the cut is known: a score timed on it (BPM on the section turns), 2 drafts to choose from
            music_timing.write_spotting(p, pid, drafts_dir, timed)       # S0.15 M8: the cue sheet the drafts were asked from
            for note in timed.get("notes") or []:
                _log(p, pid, "Nhạc nền: " + note)
            music.submit_drafts(ctx.audio, drafts_dir, timed["prompt"], timed["length_ms"], True, TIMED_DRAFTS, ledger=(p.conn, pid))
            _log(p, pid, f"Đã gửi {TIMED_DRAFTS} bản nhạc nền theo nhịp dựng ({timed['bpm']} BPM, {len(timed['turns'])} điểm đổi đoạn)")
            return "Nhạc nền: đang tạo"
        from . import claude_tasks
        brief = claude_tasks.music_brief(p, pid, ctx.llm)
        music.submit_drafts(ctx.audio, drafts_dir, brief["prompt"], brief["length_ms"], brief["instrumental"], 1, ledger=(p.conn, pid))
        _log(p, pid, "Đã gửi 1 bản nhạc nền" + (" (brief do Claude viết)" if brief.get("brief") else ""))
        return "Nhạc nền: đang tạo"
    music.refresh_drafts(ctx.audio, drafts_dir)
    drafts = music.load_drafts(drafts_dir)
    ok = [i for i, d in enumerate(drafts) if d["state"] == "succeeded"]
    if ok and timed and any(d["state"] == "running" for d in drafts):
        return "Nhạc nền: đang tạo"           # wait for every timed draft, then keep the one whose changes land on the cut
    if ok:
        chosen = ok[0]
        if timed and len(ok) > 1:
            best = music_timing.pick_best([os.path.join(drafts_dir, drafts[i].get("file") or "") for i in ok], timed["turns"],
                                          timed["film_s"], dirs=timed.get("turn_dirs"))
            if best is not None:
                chosen = ok[best]
                _log(p, pid, f"Chọn bản nhạc {chosen + 1}/{len(drafts)}: đổi đoạn khớp nhịp dựng nhất")
        music.select_draft(drafts_dir, selected_dir, chosen)
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
        if plan.get("unmet"):                 # director.md Đ9: a sound the Director asked for that the library could not give
            _d(p, pid, "music", "warn", ("Âm Đạo diễn yêu cầu mà chưa đặt được: " + "; ".join(
                f"shot {u['idx']}: {', '.join(u['sfx'])}" for u in plan["unmet"]))[:400], "sfx_unmet")
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
    st = status(p, project_id)["state"]
    if st != RUNNING:
        return st
    row = p.project(project_id)
    if "archived" in row.keys() and row["archived"]:       # 📦 Cất dự án (core/archive.py): a put-away project is never run
        _set(p, project_id, STOPPED, "Dự án đã cất (📦) — không chạy tự động")
        return STOPPED
    p.actor = row["autopilot_user"]
    if p.project(project_id)["paused"]:
        _set(p, project_id, note="Đang tạm dừng")
        return RUNNING
    before = p.origin
    p.origin = "auto"                                    # S14.16: every job the run makes is machine-made (jobs.origin, _job_caps)
    try:
        return _tick(p, project_id, ctx)
    except _Stopped:                                     # the person stopped / reset the run during this tick: their state stays
        return status(p, project_id)["state"]
    finally:
        p.origin = before


def _tick(p: Pipeline, project_id: int, ctx: Context) -> str:
    from . import delivery
    try:
        phases = [("director", _director_phase), ("storycheck", _story_check_phase), ("voicefirst", _voice_first_phase), ("previz", _previz_phase), ("plates", _plates_phase), ("images", _images_phase), ("setcheck", _setcheck_phase),
                  ("endframes", _end_frame_phase), ("storyboard", _storyboard_phase), ("motion", _motion_phase), ("voice", _voice_phase), ("videos", _videos_phase), ("music", _music_phase),
                  ("platefix", _plate_fallback_phase), ("lipsync", _lipsync_phase), ("sfx", _sfx_phase)]
        for name, fn in phases:
            progress_note = fn(p, project_id, ctx)
            if progress_note is not None:
                blocked = _blocked_scenes(p, project_id)
                idle = not (_active(p, project_id, "image_gen") or _active(p, project_id, "video_gen"))
                if blocked and idle and name in ("images", "videos"):
                    note = "Cần bạn xử lý: " + "; ".join(blocked)
                    if not _tick_set(p, project_id, ATTENTION, note):
                        raise _Stopped()
                    _log(p, project_id, note)
                    _d(p, project_id, "autopilot", "warn", note, "needs_attention")
                    return ATTENTION
                if not _tick_set(p, project_id, note=f"{PHASE_LABELS[name]} — {progress_note}"):
                    raise _Stopped()
                _log(p, project_id, f"{PHASE_LABELS[name]}: {progress_note}")
                return RUNNING
        _still_running(p, project_id)
        res = delivery.deliver(p, project_id, ctx.data_dir, ctx.llm, render_fn=ctx.render or default_render, subtitle_fn=ctx.subtitle)
        out = res["final"]
        names = {"subtitle": "phụ đề", "endcard": "card cuối", "ailabel": "nhãn AI", "export": "bản xuất"}
        extra = "".join(f" + {names.get(kind, kind)}: {path}" for kind, path in res["layers"])
        for w in res["warnings"]:
            _log(p, project_id, f"Xuất bản: {w[:120]}")
        if any(kind == "subtitle" for kind, _ in res["layers"]):
            _log(p, project_id, "Đã thêm phụ đề")
        qc = res.get("qc") or {}
        if qc.get("blocks"):                     # S1.9 (trial #8): a cut with a blocking fault is not "done" — the person looks first
            from . import final_qc
            note = f"Bản dựng có {qc['blocks']} lỗi chặn — xem màn Bản giao · Kiểm bản dựng: " + "; ".join(
                i["msg"] for i in qc["issues"] if i["level"] == "block")[:300]
            if not _tick_set(p, project_id, ATTENTION, note):
                raise _Stopped()
            _log(p, project_id, final_qc.summary(qc)[:600])
            _restore_cfg(p, project_id)
            return ATTENTION
        if not _tick_set(p, project_id, DONE, f"Xong: {out}{extra}"):
            raise _Stopped()
        _log(p, project_id, "Đã ghép video cuối")
        _restore_cfg(p, project_id)
        return DONE
    except _Wait as e:
        if not _tick_set(p, project_id, WAITING, str(e)):
            raise _Stopped()
        set_gates(p, project_id, {"waiting_for": e.gate})
        _log(p, project_id, str(e))
        return WAITING
    except PipelinePaused as e:                          # the money gate saw the project paused mid-tick (not a ValueError): wait
        if not _tick_set(p, project_id, note=f"Đang tạm dừng — {e}"):
            raise _Stopped()
        return RUNNING
    except _Stop as e:
        if not _tick_set(p, project_id, STOPPED, str(e)):
            raise _Stopped()
        _log(p, project_id, str(e))
        _d(p, project_id, "autopilot", "warn", str(e), "stopped")
        return STOPPED
    except (llm_runner.LlmError, ValueError, OSError, ffmpeg_studio.FFmpegError, ffmpeg_studio.FFmpegNotFound) as e:
        if not _tick_set(p, project_id, ERROR, f"Lỗi: {e}"):
            raise _Stopped()
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

    def _check_user(self, project_id: int, user, action: str) -> None:
        """`user` ({'email','role'}, core/access.py) comes from the dashboard session; None = the system. A person without the edit
        right on the project cannot start its run (it spends money)."""
        if user is not None:
            from .db import connect
            conn = connect(self.db_path)
            try:
                access.require(conn, project_id, user, "edit", action)
            finally:
                conn.close()

    def start(self, project_id: int, user=None) -> bool:
        """Start now if a slot is free, otherwise wait in the queue. False when already running or queued."""
        self._check_user(project_id, user, "bật chạy tự động")
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

    def wake(self, project_id: int, user=None) -> bool:
        """S6.4: the person asked for a redraw while the run waits at a storyboard / pilot gate — a thread sends and collects it
        (Manager._run → serve_waiting). False when nothing to do (not waiting there, already alive, no queued picture)."""
        from .db import connect
        self._check_user(project_id, user, "gửi lại ảnh khi chạy tự động đang chờ")
        p = Pipeline(connect(self.db_path))
        if (self.alive(project_id) or status(p, project_id)["state"] != WAITING
                or get_gates(p, project_id).get("waiting_for") not in SERVE_GATES
                or not _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='queued'", project_id)):
            return False
        with self._lock:
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
                if not _tick_set(p, project_id, ERROR, f"Lỗi không lường trước: {e}"):    # a stop made meanwhile stays (review B1b)
                    _d(p, project_id, "autopilot", "warn", f"lỗi sau khi đã dừng {type(e).__name__}: {e}", "unexpected")
                    return
                _d(p, project_id, "autopilot", "error", f"lỗi không lường trước {type(e).__name__}: {e}", "unexpected")
                _log(p, project_id, f"Lỗi không lường trước: {str(e)[:200]}")
                return
            if state == WAITING:              # S6.4: at a storyboard / pilot gate, redraws the person asked for are still made
                try:
                    for _ in range(SERVE_ROUNDS):
                        if not serve_waiting(p, project_id, ctx):
                            break
                        time.sleep(self.poll_sec)
                except Exception as e:  # noqa: BLE001 - said; the gate keeps waiting
                    _d(p, project_id, "autopilot", "warn", f"gửi ảnh vẽ lại khi chờ cổng lỗi {type(e).__name__}: {e}", "serve_waiting")
                return
            if state != RUNNING:
                return
            time.sleep(self.poll_sec)



# ---- gates (human checkpoints the person switches on) ----------------------------------------------------------------
GATE_DEFAULTS = {"bible": True, "pilot": False, "storyboard": True}


class _Wait(Exception):
    def __init__(self, gate: str, note: str):
        super().__init__(note)
        self.gate = gate


def get_gates(p: Pipeline, project_id: int) -> Dict:
    try:
        saved = json.loads(p.project(project_id)["autopilot_gates"] or "{}")
    except (ValueError, KeyError, IndexError, TypeError):
        saved = {}
    return {**GATE_DEFAULTS, "bible_done": False, "pilot_done": False, "storyboard_ok": None, "waiting_for": None, **saved}


def set_gates(p: Pipeline, project_id: int, changes: Dict) -> None:
    access.need_edit(p, project_id, "đổi cổng duyệt")
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
    access.need_edit(p, project_id, "đặt lại chạy tự động")
    p.conn.execute("UPDATE projects SET autopilot_state=NULL, autopilot_note=NULL WHERE id=?", (project_id,))
    p.conn.commit()
    set_gates(p, project_id, {"bible_done": False, "pilot_done": False, "storyboard_ok": None, "waiting_for": None})
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
    from . import qc_scene
    if qc_scene.enabled():
        return None                                         # the per-scene QC already looked at every scene's frames together
    from . import claude_tasks
    marker = _marker(ctx, pid, "qc_set", ".autopilot_done")
    if os.path.exists(marker) or len(_scene_rows(p, pid)) < 2:
        return None
    try:
        from . import features
        r = claude_tasks.set_consistency(p, pid, ctx.llm, ctx.data_dir)
        issues = r.get("issues") or []
        if not features.on("setcheck_autofix"):          # report only: the storyboard shows these to the person (O2/F3)
            if issues:
                _d(p, pid, "qc", "warn", "QC đồng bộ thấy lệch ở " + ", ".join(f"cảnh {it['idx']}" for it in issues)
                   + " — xem cờ ⚑ ở storyboard (không tự gen lại)", "set_check_report")
            _log(p, pid, "QC đồng bộ cả bộ ảnh: " + (f"{len(issues)} cảnh lệch, chờ bạn xem ở storyboard" if issues else "ổn"))
            issues = []
        redone = 0
        for it in issues:
            cap_why = _job_cap_reason(p, pid)
            if cap_why:
                _d(p, pid, "qc", "warn", f"QC đồng bộ: không gen lại cảnh {it['idx']} — {cap_why}", "set_check_cap")
                break
            why = _setcheck_block(p, pid, it, str(getattr(getattr(ctx.image_runner, "provider", None), "name", "") or ""))
            if why:
                _d(p, pid, "qc", "warn", f"QC đồng bộ: không tự gen lại cảnh {it['idx']} — {why}", "set_check_not_redone")
                continue
            try:
                if claude_tasks.redo_from_set_check(p, pid, it["idx"], it["fix"], auto=True) != "escalated":
                    redone += 1
            except Exception as e:  # noqa: BLE001 - one scene that cannot be redone must not stop the run, but it is said
                _d(p, pid, "qc", "warn", f"QC đồng bộ: không gen lại được cảnh {it['idx']} ({type(e).__name__}: {e})", "set_check_redo_failed")
                continue
        if redone or features.on("setcheck_autofix"):
            _log(p, pid, "QC đồng bộ cả bộ ảnh: " + (f"làm lại {redone} cảnh lệch" if redone else "ổn"))
    except (llm_runner.LlmError, ValueError, OSError) as e:
        _d(p, pid, "qc", "warn", f"autopilot bỏ qua QC đồng bộ: {e}", "set_check_skipped")
    with open(marker, "w") as f:
        f.write("1")
    return None if not _count(p, "SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state IN ('queued','running')", pid) \
        else "QC đồng bộ: đang gen lại cảnh lệch"


def _setcheck_block(p: Pipeline, pid: int, issue: Dict, provider_name: str = "") -> Optional[str]:
    """Why a set-check outlier must not be redrawn automatically (setcheck_autofix): no English fix sentence (the same input again),
    the shot's picture at its automatic limit (pipeline.AUTO_REGEN_LIMIT, S14.16), or the service is out of credit."""
    from . import image_models, spend_gate
    if not (issue.get("fix") or "").strip():
        return "QC không nêu câu sửa — gen lại sẽ gửi y hệt đầu vào"
    row = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, issue.get("idx"))).fetchone()
    if row is None:
        return "không có cảnh này"
    job = p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                         (row["id"],)).fetchone()
    if job is not None and p._retries_exhausted(job):
        p._limit_said(job)                                  # 📥 "Cần bạn quyết — đã tự gen lại N lần"
        return f"Cần bạn quyết — ảnh của shot đã tự gen lại {job['retry_count']} lần (tối đa {p.auto_limit(job)})"
    # S14.1 A1b / S14.16: the money gate asked before queueing the redraw — only a real stop (the service out of credit) holds it; the
    # caps only warn. The real send still goes through ImageRunner's own gate.
    over = spend_gate.reason(p.conn, "image", provider_name or "deepix", project_id=pid, model=image_models.of_project(p.project(pid)),
                             units=1, budget_stage="images")
    return f"ngân sách: {over}" if over else None


def _check_voices(p: Pipeline, pid: int, ctx: Context) -> None:
    """AU-f: free check of every voice (length, silences; speech-to-text when installed). Flags only — a redo (paid TTS) happens here
    once per project only when the check has passed its real test or is switched on (features.voice_check_redo)."""
    from . import features, voice_check
    try:
        res = voice_check.check_project(ctx.data_dir, pid)
    except Exception as e:  # noqa: BLE001 - a failing check must not stop the video; it is reported
        _d(p, pid, "voice", "warn", f"không kiểm được giọng thoại: {e}", "voice_check")
        return
    if not res["bad"]:
        return
    _d(p, pid, "voice", "warn", f"{res['bad']} câu thoại có giọng nghi lỗi (cắt/thiếu chữ/ngắt quãng) — nghe lại ở tab Motion (Storyboard) → 🎙 Giọng thoại",
       "voice_check")
    marker = os.path.join(audio_lib.assets_dir(ctx.data_dir, pid), "voice_redo_done")
    if features.on("voice_check_redo") and not os.path.exists(marker):
        open(marker, "w").close()
        r = voice_check.redo(p.conn, pid, ctx.audio, ctx.data_dir)
        _log(p, pid, f"Tạo lại {r['sent']} câu thoại bị cờ lỗi (1 lần)")


def _story_check_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """S3.2 (feature story_check): the first-time viewer reads the shot plan once (cached by what is on screen) — its reading goes to
    the log and, when it is lost somewhere, to 📊 Theo dõi and the Kịch bản screen. It never stops the run: the person reads it at the plan."""
    from . import features, story_check
    if not features.on("story_check") or ctx.llm is None:
        return None
    before = story_check.load(ctx.data_dir, pid)
    try:
        res = story_check.run(p, pid, ctx.llm, ctx.data_dir)
    except llm_runner.LlmError as e:
        _d(p, pid, "director", "warn", f"người xem lần đầu chưa đọc được bảng shot: {e}", "story_check_failed")
        return None
    if res and (not before or before.get("fingerprint") != res.get("fingerprint")):
        for line in story_check.lines(res)[:6]:
            _log(p, pid, line[:200])
        lost = [c for c in res.get("confusing") or [] if isinstance(c, dict)]
        if lost or (res.get("understood") or 5) <= 3:
            _d(p, pid, "director", "warn", f"người xem lần đầu hiểu {res.get('understood')}/5, {len(lost)} chỗ khó hiểu — xem màn Kịch bản",
               "story_unclear")
    return None


def _voice_first_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """S2 (feature audio_first): voice every line right after the Director, size the shots to the real voices, check the total
    against the script's target and lock the timeline — before a picture is paid for. Once locked, never again (a new Director
    run clears the gate)."""
    from . import audio_first, claude_tasks, features, voice
    if not features.on("audio_first") or get_gates(p, pid).get("timeline_locked"):
        return None
    stat = voice.status(p.conn, pid, ctx.data_dir)
    if not stat["total"]:
        return None
    if ctx.audio is None:
        _d(p, pid, "voice", "warn", "timeline theo âm thanh bật nhưng không có nhà cung cấp âm thanh — khóa timeline theo bảng shot "
                                    "của Director (chưa có giọng thật)", "no_audio_provider")
        set_gates(p, pid, {"timeline_locked": {"total": audio_first.planned_total(p.conn, pid), "by": "director"}})
        return None
    missing = audio_first.speakers_without_voice(p.conn, pid)
    if missing and ctx.llm is not None:                    # S2.1: a voice for every speaker before the first picture
        try:
            r = claude_tasks.cast_voices(p, pid, ctx.llm, voice.library(ctx.audio))
            if r.get("cast"):
                _log(p, pid, "Chọn giọng: " + ", ".join(str(c.get("name")) for c in r["cast"]))
        except llm_runner.LlmError as e:
            _d(p, pid, "voice", "warn", f"chưa chọn được giọng tự động: {e}", "no_voice")
        missing = audio_first.speakers_without_voice(p.conn, pid)
    if missing:
        raise _Wait("voices", "Chưa có giọng cho: " + ", ".join(missing) + " — chọn giọng ở màn Kịch bản → 🎙 Giọng rồi bấm chạy tiếp "
                              "(timeline được đo bằng giọng thật trước khi làm ảnh)")
    if stat["missing"] or stat.get("failed"):
        r = voice.generate(p.conn, pid, ctx.audio, ctx.data_dir)
        if r["sent"]:
            _log(p, pid, f"Gửi {r['sent']} câu thoại cho TTS (đo độ dài trước khi làm ảnh)")
    audio_lib.refresh(ctx.audio, audio_lib.assets_dir(ctx.data_dir, pid))
    stat = voice.status(p.conn, pid, ctx.data_dir)
    if stat.get("running") or stat["missing"]:
        return f"Giọng thoại (đo độ dài): {stat.get('succeeded', 0)}/{stat['total']}"
    changes = audio_first.fit_shots(p.conn, pid, ctx.data_dir)
    if changes:
        _log(p, pid, f"Kéo {len(changes)} shot cho vừa giọng thật: " + ", ".join(f"S{c['idx']:02d} {c['from']:g}→{c['to']:g} s"
                                                                           for c in changes[:8]))
    check = audio_first.length_check(p.conn, pid)
    ask = audio_first.gate_message(check)
    if ask and not get_gates(p, pid).get("length_decided"):
        _d(p, pid, "voice", "warn", ask, "length_off_target")
        raise _Wait("length", ask)
    set_gates(p, pid, {"timeline_locked": {"total": check["total"], "by": "voice"}})
    _log(p, pid, audio_first.lock_note(check))
    return None


def _voice_phase(p: Pipeline, pid: int, ctx: Context) -> Optional[str]:
    """Character voices for the dialogue (TTS), then clips sized to the real voice. Skipped (with a note) when there is no audio
    provider or a speaker has no voice: subtitles still carry the lines."""
    from . import voice
    stat = voice.status(p.conn, pid, ctx.data_dir)
    if not stat["total"]:
        return None
    if ctx.audio is None:                                  # luật 1: said as a diag (📊 Theo dõi), not only a log line
        _d(p, pid, "voice", "warn", f"không có nhà cung cấp âm thanh (AUDIO_PROVIDER) — {stat['total']} câu thoại không có giọng, "
                                    "chỉ có phụ đề", "no_audio_provider")
        return None
    if stat["missing"] or stat.get("failed"):
        r = voice.generate(p.conn, pid, ctx.audio, ctx.data_dir)
        if r["sent"]:
            _log(p, pid, f"Gửi {r['sent']} câu thoại cho TTS")
        if r["no_voice"]:
            _log(p, pid, "Chưa có giọng cho: " + ", ".join(r["no_voice"]) + " (các câu này chỉ có phụ đề)")
            _d(p, pid, "voice", "warn", "chưa có giọng cho: " + ", ".join(r["no_voice"]) + " — các câu của họ chỉ có phụ đề (chọn giọng ở "
                                        "màn Kịch bản → 🎙 Giọng)", "no_voice")
        for why in r.get("held") or []:
            _d(p, pid, "voice", "warn", f"không tự gửi lại câu thoại lỗi: {why}", "voice_not_resent")
    if stat.get("running") or stat["missing"]:
        audio_lib.refresh(ctx.audio, audio_lib.assets_dir(ctx.data_dir, pid))
        stat = voice.status(p.conn, pid, ctx.data_dir)
        if stat.get("running"):
            return f"Giọng thoại: {stat.get('succeeded', 0)}/{stat['total']}"
    _check_voices(p, pid, ctx)
    changes = voice.fit_durations(p.conn, pid, ctx.data_dir)       # scenes without a clip yet only
    if changes:
        _log(p, pid, f"Kéo dài {len(changes)} clip cho vừa giọng thật")
    late = voice.pending_fits(p.conn, pid, ctx.data_dir)
    if late and not get_gates(p, pid).get("voice_fit_decided"):
        _d(p, pid, "voice", "warn", f"{len(late)} clip đã có ngắn hơn giọng thật — chờ người quyết: làm lại các clip đó (tốn tiền video) "
                                    "hay giữ clip, bản dựng giữ hình dưới câu thoại dài", "voice_longer_than_clip")
        raise _Wait("voice_fit", f"{len(late)} clip đã làm ngắn hơn giọng thoại thật (giọng chọn sau khi có video). Chọn ở màn Video: làm lại "
                                 "các clip đó cho vừa giọng (tốn tiền video) hoặc giữ clip — bản dựng giữ hình dưới câu dài")
    return None
