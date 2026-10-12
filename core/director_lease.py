"""Khóa Đạo diễn chung theo CSDL/dự án; sổ riêng tránh commit giao dịch pipeline."""
import contextlib
import contextvars
import ctypes
import os
import re
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
import warnings
from datetime import datetime

from . import diag

RAW_LIMIT = 16000
LEASE_SECONDS = 900
HEARTBEAT_SECONDS = 30
PENDING_GRACE = 3600       # rà gộp 12/10: a call mark older than the run cap + this is a dead process's leftover
MAX_RUN_SECONDS = 6 * 3600  # ngừng lượt treo dù PID và thread heartbeat còn sống
_memory_paths = {}
_memory_guard = threading.Lock()
_current = contextvars.ContextVar('director_owner', default=None)


class LeaseLost(BaseException):
    """Không cho Tầng B gom lỗi rồi ghi kế hoạch của lượt đã mất quyền."""


def checkpoint(lease=None):
    lease = lease or _current.get()
    if lease is None:
        return
    path, project, owner = lease
    with contextlib.closing(_open(path)) as db:
        row = db.execute('SELECT owner,heartbeat,started FROM leases WHERE project=?', (project,)).fetchone()
        if not row or row[0] != owner or time.time() - row[1] >= LEASE_SECONDS or time.time() - row[2] >= MAX_RUN_SECONDS:
            raise LeaseLost('Lượt Đạo diễn đã hết hạn hoặc mất khóa — dừng, không ghi kế hoạch')


@contextlib.contextmanager
def writing():
    """Giữ giao dịch sổ khóa khi ghi kế hoạch: không takeover giữa kiểm và ghi."""
    lease = _current.get()
    if lease is None:
        yield
        return
    path, project, owner = lease
    with contextlib.closing(_open(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT owner,heartbeat,started FROM leases WHERE project=?', (project,)).fetchone()
        if not row or row[0] != owner or time.time() - row[1] >= LEASE_SECONDS or time.time() - row[2] >= MAX_RUN_SECONDS:
            raise LeaseLost('Lượt Đạo diễn đã hết hạn hoặc mất khóa — dừng, không ghi kế hoạch')
        try:
            yield
        finally:
            db.rollback()  # chỉ giữ hàng rào; ghi kế hoạch nằm trong manifest riêng


class GuardedClient:
    def __init__(self, client, lease):
        self.client, self.lease = client, lease

    def __getattr__(self, name):
        return getattr(self.client, name)

    def complete(self, *args, **kwargs):
        with _calling(self.lease):
            reply = self.client.complete(*args, **kwargs)
        checkpoint(self.lease)
        return reply


def _warning(path, project, action):
    # Không đưa nội dung reply, đường dẫn hoặc exception chứa secret vào log dự phòng.
    message = f'Đạo diễn: lỗi sổ khóa khi {action}; dự án #{project}. Cần kiểm tra chẩn đoán.'
    manifest = path.removesuffix('.director.sqlite')
    try:
        if manifest != path and os.path.isfile(manifest):
            with contextlib.closing(sqlite3.connect(manifest, timeout=1)) as conn:
                conn.row_factory = sqlite3.Row
                if conn.execute("SELECT 1 FROM sqlite_master WHERE name='diag_events'").fetchone():
                    diag.record(conn, 'director', 'warn', message, 'director_lease_storage', project)
                    return
    except Exception:
        pass
    try:
        warnings.warn(message, RuntimeWarning, stacklevel=2)
    except Exception:  # warnings=error hoặc log hỏng cũng không được che lỗi gốc
        try:
            print(message, file=sys.stderr)
        except Exception:
            pass


@contextlib.contextmanager
def _calling(lease):
    """Đánh dấu atomic trước gửi; owner sống có call pending thì không takeover."""
    path, project, owner = lease
    with contextlib.closing(_open(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT owner,heartbeat,started FROM leases WHERE project=?', (project,)).fetchone()
        if not row or row[0] != owner or time.time() - row[1] >= LEASE_SECONDS or time.time() - row[2] >= MAX_RUN_SECONDS:
            raise LeaseLost('Lượt Đạo diễn đã hết hạn hoặc mất khóa — dừng, không gửi thêm')
        db.execute('INSERT INTO pending_calls VALUES (?,?,1) ON CONFLICT(project,owner) DO UPDATE SET count=count+1', (project, owner))
        db.commit()
    try:
        yield
    finally:
        failed = sys.exc_info()[0] is not None
        try:
            with contextlib.closing(_open(path)) as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('UPDATE pending_calls SET count=count-1 WHERE project=? AND owner=?', (project, owner))
                db.execute('DELETE FROM pending_calls WHERE project=? AND owner=? AND count<=0', (project, owner))
                db.commit()
        except Exception:
            _warning(path, project, 'kết thúc lời gọi')
            if not failed:
                raise


class DirectorBusy(RuntimeError):
    pass


def _path(conn):
    path = conn.execute('PRAGMA database_list').fetchone()[2]
    if path:
        return path + '.director.sqlite'
    with _memory_guard:
        if conn not in _memory_paths:
            _memory_paths[conn] = os.path.join(tempfile.gettempdir(), f'director-{os.getpid()}-{uuid.uuid4().hex}.sqlite')
        return _memory_paths[conn]


def _open(path):
    db = sqlite3.connect(path, timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS leases (project INTEGER PRIMARY KEY, owner TEXT, pid INTEGER, started REAL, heartbeat REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS bad_replies (id INTEGER PRIMARY KEY, project INTEGER, stage TEXT, at REAL, text TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS pending_calls (project INTEGER, owner TEXT, count INTEGER, PRIMARY KEY(project,owner))')
    db.commit()
    return db


def _alive(pid):
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # không có quyền đọc PID: giữ khóa
        try:
            code = ctypes.c_ulong()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _active(row, db):
    if not row or not _alive(row[2]):
        return False
    pending = db.execute('SELECT 1 FROM pending_calls WHERE project=? AND owner=? AND count>0', (row[0], row[1])).fetchone()
    # rà gộp Đ15v2 (12/10): a "calling" mark left by a process that died mid-call, its PID then reused (Windows) — never held for ever:
    # a live call still holds past the run cap (no overlapping run), but not past PENDING_GRACE after it (a real call times out long before)
    if pending and time.time() - row[3] < MAX_RUN_SECONDS + PENDING_GRACE:
        return True
    return time.time() - row[4] < LEASE_SECONDS and time.time() - row[3] < MAX_RUN_SECONDS


def message(started):
    return f'Đạo diễn đang chạy cho dự án này (bắt đầu {datetime.fromtimestamp(started):%d/%m %H:%M}) — chờ xong'


def busy(conn, project):
    with contextlib.closing(_open(_path(conn))) as db:
        row = db.execute('SELECT project,owner,pid,started,heartbeat FROM leases WHERE project=?', (project,)).fetchone()
        return message(row[3]) if _active(row, db) else ''


@contextlib.contextmanager
def hold(conn, project):
    path, owner = _path(conn), uuid.uuid4().hex
    with contextlib.closing(_open(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT project,owner,pid,started,heartbeat FROM leases WHERE project=?', (project,)).fetchone()
        if _active(row, db):
            db.rollback()
            raise DirectorBusy(message(row[3]))
        now = time.time()
        db.execute('DELETE FROM pending_calls WHERE project=?', (project,))
        db.execute('INSERT OR REPLACE INTO leases VALUES (?,?,?,?,?)', (project, owner, os.getpid(), now, now))
        db.commit()
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(HEARTBEAT_SECONDS):
            if time.time() - now >= MAX_RUN_SECONDS:
                return
            try:
                with contextlib.closing(_open(path)) as db:
                    db.execute('UPDATE leases SET heartbeat=? WHERE project=? AND owner=?', (time.time(), project, owner))
                    db.commit()
            except (sqlite3.Error, OSError):
                _warning(path, project, 'cập nhật heartbeat')

    worker = threading.Thread(target=heartbeat, daemon=True)
    worker.start()
    context_token = _current.set((path, project, owner))
    try:
        yield (path, project, owner)
    finally:
        failed = sys.exc_info()[0] is not None
        _current.reset(context_token)
        stop.set()
        worker.join(timeout=11)
        try:
            with contextlib.closing(_open(path)) as db:
                db.execute('DELETE FROM leases WHERE project=? AND owner=? AND NOT EXISTS (SELECT 1 FROM pending_calls WHERE project=? AND owner=? AND count>0)', (project, owner, project, owner))
                db.commit()
        except Exception:
            _warning(path, project, 'nhả khóa')
            if not failed:
                raise


def safe_reply(text):
    # Giá trị bí mật có thể không mang tiền tố sk-/Bearer.
    for key, value in os.environ.items():
        if re.search(r'(?i)(key|token|secret|password)', key) and len(value) >= 6:
            text = str(text).replace(value, '***')
    text = diag.redact(text)
    text = re.sub(r'(?i)\b[A-Z]:[\\/][^\s\"<>]+|(?<!\w)/(?:[^\s\"<>/]+/)+[^\s\"<>]*|\\\\[^\s\"<>]+', '[đường dẫn]', text)
    return text.encode('utf-8')[:RAW_LIMIT].decode('utf-8', errors='ignore')


def capture(conn, project, stage):
    path = _path(conn)  # lấy trước khi callback chạy trên thread Quay phim

    def save(text):
        try:
            with contextlib.closing(_open(path)) as db:
                db.execute('INSERT INTO bad_replies(project,stage,at,text) VALUES (?,?,?,?)', (project, stage, time.time(), safe_reply(text)))
                db.execute('DELETE FROM bad_replies WHERE project=? AND id NOT IN (SELECT id FROM bad_replies WHERE project=? ORDER BY id DESC LIMIT 20)', (project, project))
                db.commit()
        except Exception:
            _warning(path, project, 'lưu câu trả lời sai định dạng')
    return save


def replies(conn, project):
    with contextlib.closing(_open(_path(conn))) as db:
        return db.execute('SELECT stage,at,text FROM bad_replies WHERE project=? ORDER BY id DESC', (project,)).fetchall()
