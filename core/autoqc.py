"""Automatic check of freshly generated pictures, before a person sees them.

When a picture has been generated, Claude looks at it next to the chosen resources' reference pictures and scores it (character right?
hands / face? composition? mood? nothing extra?). With the project's "auto-fix" switch on, a faulty picture is regenerated with the problems
written into its prompt, up to the project's retry limit; only a picture that passes, or is still faulty after the last try, is put in front of
the person (with the scores and the problems). Runs in a background thread, one project at a time, so the page stays responsive.
A failure (Claude Code not logged in, no key, time-out) is remembered and shown, and is not retried in a loop.
"""
import threading
import time
from typing import Callable, Dict, Optional, Tuple

from . import diag, llm_runner
from .db import connect
from .pipeline import Pipeline
from .states import JobState

RETRY_AFTER = 300                       # seconds before a failed check is tried again on its own
_lock = threading.Lock()
_active = set()
_errors: Dict[int, Tuple[str, float]] = {}


def active(project_id: int) -> bool:
    return project_id in _active


def last_error(project_id: int) -> Optional[str]:
    entry = _errors.get(project_id)
    if entry and time.time() - entry[1] < RETRY_AFTER:
        return entry[0]
    return None


def clear_error(project_id: int) -> None:
    _errors.pop(project_id, None)


def waiting(conn, project_id: int) -> int:
    """Generated pictures not checked yet."""
    return conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", (project_id,)).fetchone()[0]


def can_run(conn, project_id: int, client_factory: Optional[Callable] = None) -> bool:
    """True when there is something to check, nothing is running / broken, and a Claude is configured."""
    if active(project_id) or last_error(project_id) or not waiting(conn, project_id):
        return False
    try:
        return (client_factory or llm_runner.ledger_factory(llm_runner.db_file(conn)))() is not None
    except llm_runner.LlmError:
        return False


def start(db_path: str, data_dir: str, project_id: int, client_factory: Optional[Callable] = None) -> bool:
    """Start checking this project's unchecked pictures in the background. True if a check was started."""
    conn = connect(db_path)
    client_factory = client_factory or llm_runner.ledger_factory(db_path)      # every Claude call -> cost ledger + Claude cap
    with _lock:
        if not can_run(conn, project_id, client_factory):
            return False
        _active.add(project_id)
    threading.Thread(target=_work, args=(db_path, data_dir, project_id, client_factory), daemon=True, name=f"autoqc-{project_id}").start()
    return True


def _fail(conn, project_id: int, message: str) -> None:
    _errors[project_id] = (message, time.time())
    diag.record(conn, "qc", "warn", f"tự kiểm tra ảnh dừng: {message}", "autoqc", project_id)


def _work(db_path: str, data_dir: str, project_id: int, client_factory: Callable) -> None:
    conn = None
    try:
        conn = connect(db_path)
        p = Pipeline(conn)
        client = client_factory()
        if client is None:
            _fail(conn, project_id, "chưa có Claude (ANTHROPIC_API_KEY hoặc LLM_PROVIDER=claude_cli)")
            return
        from . import qc_scene
        if qc_scene.active():                              # QC per script scene (one call per scene once all its frames exist)
            r = qc_scene.run_ready_scenes(p, project_id, client, data_dir)
            if r["failed"]:
                _fail(conn, project_id, f"QC cảnh {r['failed'][0][0]}: {r['failed'][0][1]}")
            return
        for _ in range(300):
            row = conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded' ORDER BY id LIMIT 1",
                               (project_id,)).fetchone()
            if row is None:
                break
            autofix = bool(p.project(project_id)["qc_autofix"])
            try:
                llm_runner.run_qc(p, row["id"], client, data_dir, autofix=autofix)
            except llm_runner.LlmError as e:
                if e.code in ("auth", "config", "timeout", "cli_error", "rate_limit", "server_error"):
                    _fail(conn, project_id, str(e))
                    return
                # this picture could not be judged (bad answer twice): hand it to the person instead of looping on it
                p.transition(row["id"], JobState.PENDING_REVIEW, actor="ai_agent", note=f"tự kiểm tra lỗi: {e}")
    except Exception as e:  # noqa: BLE001 - a background check must never die silently
        if conn is not None:
            _fail(conn, project_id, f"{type(e).__name__}: {e}")
        else:
            _errors[project_id] = (f"{type(e).__name__}: {e}", time.time())
    finally:
        with _lock:
            _active.discard(project_id)


# ---- video clips (v2): same pattern, scores frames of each finished clip ---------------------------------------------------
_video_active = set()
_video_errors: Dict[int, Tuple[str, float]] = {}


def video_active(project_id: int) -> bool:
    return project_id in _video_active


def video_last_error(project_id: int) -> Optional[str]:
    entry = _video_errors.get(project_id)
    if entry and time.time() - entry[1] < RETRY_AFTER:
        return entry[0]
    return None


def clear_video_error(project_id: int) -> None:
    _video_errors.pop(project_id, None)


def start_video(db_path: str, data_dir: str, project_id: int, client_factory: Optional[Callable] = None) -> bool:
    """Check this project's finished, unscored clips in the background (project switch `qc_video`). True if started."""
    from . import claude_tasks
    conn = connect(db_path)
    p = Pipeline(conn)
    client_factory = client_factory or llm_runner.ledger_factory(db_path)
    with _lock:
        if video_active(project_id) or video_last_error(project_id) or not claude_tasks.unchecked_videos(p, project_id):
            return False
        try:
            if client_factory() is None:
                return False
        except llm_runner.LlmError:
            return False
        _video_active.add(project_id)
    threading.Thread(target=_video_work, args=(db_path, data_dir, project_id, client_factory), daemon=True,
                     name=f"autoqc-video-{project_id}").start()
    return True


def _video_work(db_path: str, data_dir: str, project_id: int, client_factory: Callable) -> None:
    from . import claude_tasks
    conn = None
    try:
        conn = connect(db_path)
        p = Pipeline(conn)
        client = client_factory()
        for _ in range(200):
            todo = claude_tasks.unchecked_videos(p, project_id)
            if not todo or client is None:
                break
            try:
                claude_tasks.qc_video(p, todo[0], client, data_dir)
            except llm_runner.LlmError as e:
                if e.code in ("auth", "config", "timeout", "cli_error", "rate_limit", "server_error"):
                    _video_errors[project_id] = (str(e), time.time())
                    diag.record(conn, "video", "warn", f"tự kiểm tra video dừng: {e}", "autoqc_video", project_id)
                    return
                p.transition(todo[0], JobState.PENDING_REVIEW, actor="ai_agent", note=f"tự kiểm tra video lỗi: {e}")
            except Exception as e:  # noqa: BLE001 - an unreadable clip goes to the person instead of looping
                diag.record(conn, "video", "warn", f"không kiểm tra được clip {todo[0]}: {e}", "autoqc_video", project_id)
                p.transition(todo[0], JobState.PENDING_REVIEW, actor="ai_agent", note=f"không kiểm tra được: {e}")
    except Exception as e:  # noqa: BLE001
        _video_errors[project_id] = (f"{type(e).__name__}: {e}", time.time())
    finally:
        with _lock:
            _video_active.discard(project_id)
