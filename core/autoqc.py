"""Automatic check of freshly generated pictures, before a person sees them.

When a picture has been generated, Claude looks at it next to the chosen resources' reference pictures and scores it (character right?
hands / face? composition? mood? nothing extra?). With the project's "auto-fix" switch on, a faulty picture is regenerated with the problems
written into its prompt, up to the project's retry limit; only a picture that passes, or is still faulty after the last try, is put in front of
the person (with the scores and the problems). Runs in a background thread, one project at a time, so the page stays responsive.
A failure (Claude Code not logged in, no key, time-out) is remembered and shown, and is not retried in a loop.
"""
import os
import threading
import time
from typing import Callable, Dict, Optional, Tuple

from . import diag, llm_provider, llm_runner
from .db import connect
from .pipeline import Pipeline
from .states import JobState

RETRY_AFTER = 300                       # seconds before a failed check is tried again on its own
_lock = threading.Lock()
_active = set()
_errors: Dict[int, Tuple[str, float]] = {}
_FILE_LOCKS: Dict[str, object] = {}


def _lock_path(db_path: str, kind: str, project_id: int) -> str:
    return os.path.abspath(db_path) + f".autoqc-{kind}-{project_id}.lock"


def _claim(db_path: str, kind: str, project_id: int) -> bool:
    """Rà 12/10 (bg_autoqc): `_active` is per process — a second Dashboard process on the same database (or the page after Streamlit
    reloads this module) would check, and pay Claude for, the same pictures twice. An OS lock on `<db>.autoqc-<kind>-<project>.lock`
    is held while the check runs; a dead process frees it. False = another process / module copy is checking this project."""
    if db_path in ("", ":memory:"):
        return True
    path = _lock_path(db_path, kind, project_id)
    if path in _FILE_LOCKS:
        return False
    try:
        fh = open(path, "a+b")
    except OSError:
        return True                                   # no lock file possible: keep the in-process lock only (old behaviour)
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return False
    _FILE_LOCKS[path] = fh
    return True


def _release(db_path: str, kind: str, project_id: int) -> None:
    fh = _FILE_LOCKS.pop(_lock_path(db_path, kind, project_id), None) if db_path not in ("", ":memory:") else None
    if fh is None:
        return
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    fh.close()


def active(project_id: int) -> bool:
    return project_id in _active


def last_error(project_id: int) -> Optional[str]:
    entry = _errors.get(project_id)
    if entry and time.time() - entry[1] < RETRY_AFTER:
        return entry[0]
    return None


def clear_error(project_id: int) -> None:
    _errors.pop(project_id, None)
    _codes.pop(("image", project_id), None)


def waiting(conn, project_id: int) -> int:
    """Generated pictures not checked yet."""
    return conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", (project_id,)).fetchone()[0]


def can_run(conn, project_id: int, client_factory: Optional[Callable] = None) -> bool:
    """True when there is something to check, nothing is running / broken, and a Claude is configured."""
    if active(project_id) or last_error(project_id) or not waiting(conn, project_id):
        return False
    try:
        return (client_factory or llm_provider.project_factory(llm_runner.db_file(conn), project_id))() is not None
    except llm_runner.LlmError:
        return False


def start(db_path: str, data_dir: str, project_id: int, client_factory: Optional[Callable] = None) -> bool:
    """Start checking this project's unchecked pictures in the background. True if a check was started."""
    conn = connect(db_path)
    per_job = client_factory is None             # rà C-RA-M14B: như video — mỗi ảnh chấm bằng provider chụp lúc tạo job của nó
    client_factory = client_factory or llm_provider.project_factory(db_path, project_id)   # V3.1 M1.4b: Claude của dự án → sổ chi
    try:
        with _lock:
            if not can_run(conn, project_id, client_factory) or not _claim(db_path, "image", project_id):
                return False
            _active.add(project_id)
    finally:
        conn.close()
    threading.Thread(target=_work, args=(db_path, data_dir, project_id, client_factory, per_job), daemon=True,
                     name=f"autoqc-{project_id}").start()
    return True


_codes: Dict[Tuple[str, int], str] = {}          # M7.4 (rà C-M74): mã lỗi dừng (LlmError.code / no_client) — vòng nền phân loại theo MÃ


def last_error_code(kind: str, project_id: int) -> Optional[str]:
    """Mã của lần tự kiểm dừng gần nhất ("image" / "video"): STOP_CODES của llm_runner hoặc "no_client"; None = không dừng vì Claude."""
    return _codes.get((kind, project_id))


def _fail(conn, project_id: int, message: str, code: Optional[str] = None) -> None:
    _errors[project_id] = (message, time.time())
    if code:
        _codes[("image", project_id)] = code
    diag.record(conn, "qc", "warn", f"tự kiểm tra ảnh dừng: {message}", "autoqc", project_id)


def _work(db_path: str, data_dir: str, project_id: int, client_factory: Callable, per_job: bool = False) -> None:
    conn = None
    try:
        conn = connect(db_path)
        p = Pipeline(conn)
        client = client_factory()
        if client is None:
            _fail(conn, project_id, "chưa có Claude: " + llm_provider.missing_hint_for(conn, project_id), code="no_client")
            return
        jobs = llm_provider.JobClients(conn, db_path).or_default(client) if per_job else None
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
                llm_runner.run_qc(p, row["id"], jobs(row["id"]) if jobs is not None else client, data_dir, autofix=autofix)
            except llm_runner.LlmError as e:
                if e.code in llm_runner.STOP_CODES:      # V3.1 M1.4a: + usage_limit / out_of_credit
                    _fail(conn, project_id, str(e), code=e.code)
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
            _release(db_path, "image", project_id)


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
    per_job = client_factory is None             # V3.1 M1.4b: mặc định → mỗi clip chấm bằng provider chụp lúc tạo job của nó
    client_factory = client_factory or llm_provider.project_factory(db_path, project_id)
    try:
        with _lock:
            if video_active(project_id) or video_last_error(project_id) or not claude_tasks.unchecked_videos(p, project_id):
                return False
            try:
                if client_factory() is None:
                    return False
            except llm_runner.LlmError:
                return False
            if not _claim(db_path, "video", project_id):
                return False
            _video_active.add(project_id)
    finally:
        conn.close()
    threading.Thread(target=_video_work, args=(db_path, data_dir, project_id, client_factory, per_job), daemon=True,
                     name=f"autoqc-video-{project_id}").start()
    return True


def _video_work(db_path: str, data_dir: str, project_id: int, client_factory: Callable, per_job: bool = False) -> None:
    from . import claude_tasks
    conn = None
    try:
        conn = connect(db_path)
        p = Pipeline(conn)
        client = client_factory()
        jobs = llm_provider.JobClients(conn, db_path).or_default(client) if per_job else None
        for _ in range(200):
            todo = claude_tasks.unchecked_videos(p, project_id)
            if not todo or client is None:
                break
            try:
                claude_tasks.qc_video(p, todo[0], jobs(todo[0]) if jobs is not None else client, data_dir)
            except llm_runner.LlmError as e:
                if e.code in llm_runner.STOP_CODES:      # V3.1 M1.4a: + usage_limit / out_of_credit
                    _video_errors[project_id] = (str(e), time.time())
                    _codes[("video", project_id)] = e.code
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
            _release(db_path, "video", project_id)
