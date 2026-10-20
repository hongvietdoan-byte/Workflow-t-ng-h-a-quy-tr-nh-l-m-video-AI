"""V3.1 M1.2 (A1, docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md): a job SUCCEEDED twice (`InvalidTransition succeeded -> succeeded`) —
`core/bg_poll.poll_all` in a separate process and the Dashboard both polled the same running job; the runner's turn lock (`runner._turn`)
only works inside ONE process. The second poller moved the first one's fresh picture to the trash and downloaded it again, while the
first one's QC read it → `FileNotFoundError` → an automatic regeneration (paid twice, job 1162 → 1163).

`take()` runs for every running job the poll is about to ACT on (the provider said succeeded / failed — never for a job still running):
- with the flag `poll_claim` the poller CLAIMS the job (one row per job in `job_poll_claims`, INSERT OR IGNORE = one winner across
  processes), then re-reads it: a job another process already moved on (succeeded / failed / cancelled) or relinked to another task is
  skipped. The claim is held until the job's new state is committed, then released (`release`). A claim older than CLAIM_TTL_S (a process
  that died mid-download) no longer blocks: the next poller downloads it again (reconcile = the provider still has the result);
- without the flag (old behaviour) nothing is claimed and nothing is re-read; only a job another process holds a claim on is skipped
  (0 USD: a script without the flag must not undo what the Dashboard with the flag is doing).

Same flag, the send side: a submit whose outcome is UNKNOWN (a timeout / connection reset / 5xx after the request may have reached the
provider, or an unexpected exception inside provider.submit) is NOT left queued (the next pass would send it again and pay twice): the job
fails with the note prefix SUBMIT_UNKNOWN, is handed to the person (escalated), and Pipeline.retry refuses to resend it by itself — the
person reconciles with the provider first (relink when the task exists, ↻ gen lại when it does not)."""
import os
import sqlite3
import time
import uuid
from typing import Optional, Tuple

from . import features

CLAIM_TTL_S = 900                       # longer than any download (a 1080p clip included); a dead process frees the job after it
from .pipeline import SUBMIT_UNKNOWN  # noqa: E402 - failure-note prefix: never resent automatically (core.pipeline.retry)

_TABLE = "CREATE TABLE IF NOT EXISTS job_poll_claims (job_id INTEGER PRIMARY KEY, owner TEXT NOT NULL, at REAL NOT NULL)"

# A network error that certainly happened BEFORE the request left (nothing can exist at the provider): the old "stay queued" path is safe.
_NOT_SENT_HINTS = ("refused", "10061", "getaddrinfo", "name or service not known", "nodename nor servname", "no route to host",
                   "network is unreachable", "10051", "10065", "name resolution")
_UNKNOWN_CODES = ("network", "server_error")
_UNKNOWN_ANY = ("bad_response",)           # HTTP 200 with an unreadable body: the task may well exist
# A local error raised while the adapter builds the request (a picture it cannot read, a bad value) — nothing left the machine.
_LOCAL_ERRORS = (FileNotFoundError, IsADirectoryError, NotADirectoryError, PermissionError, ValueError, TypeError, KeyError)


def enabled() -> bool:
    return features.on("poll_claim")


def new_owner() -> str:
    return f"{os.getpid()}-{uuid.uuid4().hex[:12]}"


def holder(conn, job_id: int) -> Optional[str]:
    try:
        row = conn.execute("SELECT owner FROM job_poll_claims WHERE job_id=? AND at>=?", (job_id, time.time() - CLAIM_TTL_S)).fetchone()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            return None                 # the flag was never on with this database: nobody claims there
        raise
    return row[0] if row else None


def claim(conn, job_id: int, owner: str) -> bool:
    """True when `owner` holds the job's claim now. Commits (the claim must be visible to the other process before anything is done)."""
    now = time.time()
    conn.execute(_TABLE)                # made here only (flag on): flag off never touches the schema
    conn.execute("DELETE FROM job_poll_claims WHERE job_id=? AND at<?", (job_id, now - CLAIM_TTL_S))
    conn.execute("INSERT OR IGNORE INTO job_poll_claims (job_id, owner, at) VALUES (?,?,?)", (job_id, owner, now))
    conn.commit()
    return holder(conn, job_id) == owner


def release(conn, job_id: int, owner: Optional[str]) -> None:
    if not owner:
        return
    try:
        conn.execute("DELETE FROM job_poll_claims WHERE job_id=? AND owner=?", (job_id, owner))
        conn.commit()
    except Exception:  # noqa: BLE001 - a claim left behind expires after CLAIM_TTL_S; never stops the poll
        pass


def refresh(conn, job_id: int, owner: str) -> bool:
    """True when `owner` still holds the claim (its time is renewed): checked right before the job's new state is written, so a claim
    that expired during a long download / cut (another process took the job over) never writes a second time."""
    try:
        cur = conn.execute("UPDATE job_poll_claims SET at=? WHERE job_id=? AND owner=? AND at>=?",
                           (time.time(), job_id, owner, time.time() - CLAIM_TTL_S))
        conn.commit()
        return cur.rowcount == 1
    except sqlite3.Error:
        return False


def take(conn, job, owner: Optional[str]) -> Tuple[Optional[object], Optional[Tuple[str, str, str]]]:
    """(job row to act on, None) = go on; (None, (severity, code, message) or None) = skip it this round (said once by the caller).
    owner None = flag off: the job as read, unless another process holds a claim on it."""
    jid = job["id"]
    if owner is None:
        try:
            other = holder(conn, jid)
        except sqlite3.Error:
            return job, None            # flag off: a database hiccup here never changes the old behaviour
        if other:
            return None, ("info", "poll_claimed", "tiến trình khác đang tải kết quả job này (giữ chỗ trong CSDL) — không xử lý lần hai")
        return job, None
    try:
        if not claim(conn, jid, owner):
            return None, ("info", "poll_claimed", "tiến trình khác đang tải kết quả job này (giữ chỗ trong CSDL) — không xử lý lần hai")
        fresh = conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    except sqlite3.Error as e:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return None, ("warn", "poll_claim_error", f"không giữ chỗ tải kết quả được ({type(e).__name__}: {e}) — chưa xử lý, vòng sau hỏi lại")
    if fresh is None or fresh["state"] != "running" or (fresh["external_id"] or "") != (job["external_id"] or ""):
        release(conn, jid, owner)
        what = "đã xóa" if fresh is None else (f"'{fresh['state']}'" if fresh["state"] != "running" else "nối sang task khác")
        return None, ("info", "poll_claimed", f"job đã {what} ở nơi khác — không xử lý lần hai")
    return fresh, None


def unknown_outcome(error: BaseException) -> bool:
    """True = provider.submit failed in a way that does not prove the task was NOT created (it may be billed): never resend blindly.
    Any other exception counts (it escaped the adapter mid-call), except a local one raised before anything was sent."""
    from .providers import ProviderError
    if not isinstance(error, ProviderError):
        return not isinstance(error, _LOCAL_ERRORS)   # a ConnectionError (an OSError too) stays unknown
    if error.code in _UNKNOWN_ANY:
        return True
    if not error.transient or error.code not in _UNKNOWN_CODES:
        return False                    # rate limited (refused before generating), a refusal, a bad input: the old paths
    text = str(error).lower()
    return not any(h in text for h in _NOT_SENT_HINTS)
