"""Hộp thư 12/10 19:58 (#27 job 776): a script and the Dashboard's background round both sent one queued job (2 Deepix tasks, one paid for
nothing) — the runner's turn lock is per process. Cờ send_claim: the job is claimed in the database before any paid step; the second
sender (other connection = other process) skips it. Không API (MockImageProvider)."""
import json
import os
import sqlite3
import time
from unittest import mock

from core import send_claim
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner

ON = {"FEATURE_SEND_CLAIM": "1"}
OFF = {"FEATURE_SEND_CLAIM": "0"}


def _setup(tmp_path):
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("#27 thử")
    sid = p.create_scene(pid, 1, "S1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "a hero on a rooftop"}), sid))
    p.conn.commit()
    return db, p, pid, p.create_job(sid, "image_gen")


def _race(tmp_path, env):
    """Runner A (the script) is inside provider.submit when runner B (the background round, its own connection) sends the same job."""
    db, p, pid, jid = _setup(tmp_path)
    calls = []
    other = ImageRunner(Pipeline(connect(db)), MockImageProvider(), str(tmp_path / "data"))

    class Racing(MockImageProvider):
        def submit(self, *a, **k):
            calls.append("A")
            if len(calls) == 1:
                orig = other.provider.submit
                other.provider.submit = lambda *x, **y: calls.append("B") or orig(*x, **y)
                other.submit_pending(pid, only={jid})
            return super().submit(*a, **k)
    first = ImageRunner(p, Racing(), str(tmp_path / "data"))
    with mock.patch.dict(os.environ, env):
        first.submit_pending(pid, only={jid})
    return p, jid, calls


def test_without_the_flag_the_race_sends_twice(tmp_path):
    p, jid, calls = _race(tmp_path, OFF)
    assert calls.count("A") + calls.count("B") == 2                  # the bug as it happened on #27 job 776


def test_with_the_flag_one_job_one_send(tmp_path):
    p, jid, calls = _race(tmp_path, ON)
    assert calls == ["A"]
    assert p.job(jid)["state"] == "running" and p.job(jid)["external_id"]
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='send_claimed'").fetchone()[0] == 1
    assert p.conn.execute("SELECT COUNT(*) FROM job_send_claims").fetchone()[0] == 0     # released after the pass


def test_a_dead_senders_claim_expires(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    assert send_claim.claim(p.conn, jid, "dead")
    assert not send_claim.claim(p.conn, jid, "me")
    p.conn.execute("UPDATE job_send_claims SET at=?", (time.time() - send_claim.CLAIM_TTL_S - 1,))
    p.conn.commit()
    assert send_claim.claim(p.conn, jid, "me")


def test_a_sent_job_is_skipped_by_the_late_sender(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    with mock.patch.dict(os.environ, ON):
        ImageRunner(p, MockImageProvider(), str(tmp_path / "data")).submit_pending(pid)
    job = connect(db).execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    late = connect(db)
    queued_copy = dict(job) | {"state": "queued"}                  # what the other process read before the send
    fresh, note = send_claim.take(late, queued_copy, {"owner": "late", "ids": []})
    assert fresh is None and "running" in note[2]


def test_flag_off_still_respects_another_processs_claim(tmp_path):
    """Rà 12/10 (TRUNG): only the Dashboard turned the flag on (dashboard.env) — the script without it must still not send a job the
    Dashboard holds."""
    db, p, pid, jid = _setup(tmp_path)
    other = connect(db)
    assert send_claim.claim(other, jid, "dashboard")
    calls = []
    prov = MockImageProvider()
    orig = prov.submit
    prov.submit = lambda *a, **k: calls.append(1) or orig(*a, **k)
    with mock.patch.dict(os.environ, OFF):
        ImageRunner(p, prov, str(tmp_path / "data")).submit_pending(pid)
        assert calls == [] and p.job(jid)["state"] == "queued"
        send_claim.release(other, jid, "dashboard")
        ImageRunner(p, prov, str(tmp_path / "data")).submit_pending(pid)
    assert calls == [1] and p.job(jid)["state"] == "running"
    assert p.conn.execute("SELECT COUNT(*) FROM job_send_claims").fetchone()[0] == 0     # flag off: never claims itself


def test_a_database_error_skips_the_job_and_keeps_the_pass(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    jid2 = p.create_job(p.conn.execute("SELECT id FROM scenes").fetchone()[0], "image_gen")
    real = send_claim.claim
    def flaky(conn, job_id, owner):
        if job_id == jid:
            raise sqlite3.OperationalError("database is locked")
        return real(conn, job_id, owner)
    with mock.patch.dict(os.environ, ON), mock.patch.object(send_claim, "claim", flaky):
        ImageRunner(p, MockImageProvider(), str(tmp_path / "data")).submit_pending(pid)
    assert p.job(jid)["state"] == "queued" and p.job(jid2)["state"] == "running"
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='send_claim_error'").fetchone()[0] == 1


def test_claims_of_a_held_job_are_released_and_it_is_sent_next_pass(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    r = ImageRunner(p, MockImageProvider(), str(tmp_path / "data"))
    with mock.patch.dict(os.environ, ON):
        with mock.patch.object(ImageRunner, "_submit_args", lambda self, job: (_ for _ in ()).throw(RuntimeError("boom"))):
            try:
                r.submit_pending(pid)
            except RuntimeError:
                pass
        assert p.conn.execute("SELECT COUNT(*) FROM job_send_claims").fetchone()[0] == 0      # finally released it
        r.submit_pending(pid)
    assert p.job(jid)["state"] == "running"


def test_two_threads_two_connections_one_send(tmp_path):
    """Two senders on their own connections (as two processes), started together: one task."""
    import threading
    db, p, pid, jid = _setup(tmp_path)
    calls, gate = [], threading.Barrier(2)

    class Slow(MockImageProvider):
        def submit(self, *a, **k):
            calls.append(1)
            time.sleep(0.3)
            return super().submit(*a, **k)

    def go():
        runner = ImageRunner(Pipeline(connect(db)), Slow(), str(tmp_path / "data"))
        gate.wait()
        runner._send_claims = None
        from core import runner as R
        with mock.patch.object(R, "_turn", lambda *a: threading.RLock()):   # a separate process does not share the turn lock
            runner.submit_pending(pid, only={jid})
    with mock.patch.dict(os.environ, ON):
        ts = [threading.Thread(target=go) for _ in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
    assert len(calls) == 1
