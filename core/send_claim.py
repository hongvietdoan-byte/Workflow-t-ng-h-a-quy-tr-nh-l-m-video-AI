"""Hộp thư 12/10 19:58 (#27 job 776): a queued job sent TWICE by two processes — a script's `ImageRunner.submit_pending(27, only={776})`
and the Dashboard's background round (`bg_poll.send_ready`) both read it as 'queued' and both called the provider (Deepix tasks
500888 + 500889, one paid for nothing, diag `cancelled_in_flight` 'running -> running'). The runner's turn lock (`runner._turn`) only
works inside one process.

`take()` runs for every job the sending pass is about to work on, BEFORE any paid step:
- always (flag or not, 0 USD, nothing sent changes): a job another sender holds a claim on is skipped, and the job is re-read — one the
  other process already moved on (running / cancelled) is skipped, one that got its task id meanwhile goes the "already sent" way;
- with the flag `send_claim` this sender also CLAIMS the job (one row per job, INSERT OR IGNORE = one winner across processes).
Claims are released at the end of the pass; a claim older than CLAIM_TTL_S (a process that died mid-send) no longer blocks. A database
error never sends the job blind: it is skipped this pass, said."""
import os
import sqlite3
import time
import uuid
from typing import Dict, Optional, Tuple

from . import features

CLAIM_TTL_S = 900                                  # longer than any send (video upload included); a dead process frees the job after it


def enabled() -> bool:
    return features.on("send_claim")


def new_owner() -> str:
    return f"{os.getpid()}-{uuid.uuid4().hex[:12]}"


_TABLE = "CREATE TABLE IF NOT EXISTS job_send_claims (job_id INTEGER PRIMARY KEY, owner TEXT NOT NULL, at REAL NOT NULL)"


def holder(conn, job_id: int) -> Optional[str]:
    try:
        row = conn.execute("SELECT owner FROM job_send_claims WHERE job_id=? AND at>=?", (job_id, time.time() - CLAIM_TTL_S)).fetchone()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            return None                            # a database not made by core.db.connect (old copy, test): nobody claims there
        raise
    return row[0] if row else None


def claim(conn, job_id: int, owner: str) -> bool:
    """True when `owner` holds the job's claim now. Commits (the claim must be visible to the other process before anything is paid)."""
    now = time.time()
    conn.execute(_TABLE)                           # normally made by core.db (SCHEMA); a database not made there gets it here
    conn.execute("DELETE FROM job_send_claims WHERE job_id=? AND at<?", (job_id, now - CLAIM_TTL_S))
    conn.execute("INSERT OR IGNORE INTO job_send_claims (job_id, owner, at) VALUES (?,?,?)", (job_id, owner, now))
    conn.commit()
    return holder(conn, job_id) == owner


def release(conn, job_id: int, owner: str) -> None:
    try:
        conn.execute("DELETE FROM job_send_claims WHERE job_id=? AND owner=?", (job_id, owner))
        conn.commit()
    except Exception:  # noqa: BLE001 - a claim left behind expires after CLAIM_TTL_S; never stops the pass
        pass


def take(conn, job, claims: Optional[Dict]) -> Tuple[Optional[object], Optional[Tuple[str, str, str]]]:
    """(fresh job row, None) = go on with it; (None, (severity, code, message) or None) = skip it this pass (said once by the caller)."""
    jid = job["id"]
    try:
        if claims is None:
            other = holder(conn, jid)
            if other:
                return None, ("info", "send_claimed", "tiến trình khác đang gửi job này (giữ chỗ trong CSDL) — không gửi lần hai")
        else:
            if not claim(conn, jid, claims["owner"]):
                return None, ("info", "send_claimed", "tiến trình khác đang gửi job này (giữ chỗ trong CSDL) — không gửi lần hai")
            claims["ids"].append(jid)
        fresh = conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    except sqlite3.Error as e:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return None, ("warn", "send_claim_error", f"không kiểm/giữ chỗ gửi được ({type(e).__name__}: {e}) — CHƯA gửi, lượt sau thử lại")
    if fresh is None or fresh["state"] != "queued":
        return None, ("info", "send_claimed", f"job đã sang '{fresh['state'] if fresh else 'đã xóa'}' ở nơi khác — không gửi")
    return fresh, None
