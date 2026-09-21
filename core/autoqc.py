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


def can_run(conn, project_id: int, client_factory: Callable = llm_runner.client_from_env) -> bool:
    """True when there is something to check, nothing is running / broken, and a Claude is configured."""
    if active(project_id) or last_error(project_id) or not waiting(conn, project_id):
        return False
    try:
        return client_factory() is not None
    except llm_runner.LlmError:
        return False


def start(db_path: str, data_dir: str, project_id: int, client_factory: Callable = llm_runner.client_from_env) -> bool:
    """Start checking this project's unchecked pictures in the background. True if a check was started."""
    conn = connect(db_path)
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
