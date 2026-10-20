"""V3.1 M1.2 (A1, A15 — docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md): two processes (bg_poll in its own process + the Dashboard) polled the
same running job — it SUCCEEDED twice (`InvalidTransition succeeded -> succeeded`), the second poller trashed/re-downloaded the picture the
first one's QC was reading (FileNotFoundError → an automatic, paid redraw). Cờ poll_claim: claim across processes (core/poll_claim.py);
results written to a temp file then os.replace (core/safe_download.py, not behind the flag). Same flag: a submit with an UNKNOWN outcome
is never resent automatically — marked for reconciliation. Không API: provider giả, 2 kết nối SQLite = 2 tiến trình."""
import json
import os
import threading
import time
from unittest import mock

import pytest

from core import poll_claim, safe_download
from core import runner as R
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider, ProviderError
from core.runner import ImageRunner
from core.states import InvalidTransition

ON = {"FEATURE_POLL_CLAIM": "1"}
OFF = {"FEATURE_POLL_CLAIM": "0"}
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


def _setup(tmp_path):
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("#33 thử")
    sid = p.create_scene(pid, 1, "S1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "a hero on a rooftop"}), sid))
    p.conn.commit()
    return db, p, pid, p.create_job(sid, "image_gen")


def _own_turn():
    """A separate process does not share the runner's turn lock (runner._turn is per process)."""
    return mock.patch.object(R, "_turn", lambda *a, **k: threading.RLock())


def _succeeded_events(p, jid):
    return p.conn.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND to_state='succeeded'", (jid,)).fetchone()[0]


def _race(tmp_path, env):
    """Runner A (Dashboard) is inside provider.download when runner B (bg_poll in its own process, own connection) polls the same job."""
    db, p, pid, jid = _setup(tmp_path)
    data = str(tmp_path / "data")
    downloads, errors = [], []
    shared = MockImageProvider()
    other = ImageRunner(Pipeline(connect(db)), shared, data)

    class Racing(MockImageProvider):
        pass
    orig_download = MockImageProvider.download

    def download(self, task_id, dest_path):
        downloads.append(dest_path)
        if len(downloads) == 1:
            try:
                other.poll_once(pid)
            except InvalidTransition as e:          # the bug as it happened: the slower poller cannot succeed it again
                errors.append(str(e))
        return orig_download(self, task_id, dest_path)

    with mock.patch.dict(os.environ, env), _own_turn():
        first = ImageRunner(p, shared, data)
        first.submit_pending(pid)
        with mock.patch.object(MockImageProvider, "download", download):
            try:
                first.poll_once(pid)
            except InvalidTransition as e:
                errors.append(str(e))
    return p, jid, downloads, errors


def test_flag_off_two_pollers_succeed_one_job_twice(tmp_path):
    """ĐỎ khi tắt cờ = hành vi cũ (lỗi A1 như trên #33): hai lần tải, InvalidTransition succeeded -> succeeded."""
    p, jid, downloads, errors = _race(tmp_path, OFF)
    assert len(downloads) == 2
    assert errors and "succeeded" in errors[0]


def test_flag_on_two_pollers_one_success_no_invalid_transition(tmp_path):
    p, jid, downloads, errors = _race(tmp_path, ON)
    assert errors == []
    assert len(downloads) == 1                                   # the second process did not trash / re-download it
    assert p.job(jid)["state"] == "succeeded" and _succeeded_events(p, jid) == 1
    assert os.path.isfile(p.job(jid)["result_path"])
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='poll_claimed'").fetchone()[0] == 1
    assert p.conn.execute("SELECT COUNT(*) FROM job_poll_claims").fetchone()[0] == 0     # released after the job's new state


def test_two_threads_two_connections_poll_together_one_success(tmp_path):
    """Two pollers on their own connections (as two processes), started together on one finished job."""
    db, p, pid, jid = _setup(tmp_path)
    data = str(tmp_path / "data")
    shared = MockImageProvider()
    with mock.patch.dict(os.environ, ON), _own_turn():
        ImageRunner(p, shared, data).submit_pending(pid)
    gate, downloads, errors = threading.Barrier(2), [], []
    orig = MockImageProvider.download

    def slow(self, task_id, dest):
        downloads.append(1)
        time.sleep(0.3)
        return orig(self, task_id, dest)

    def go():
        r = ImageRunner(Pipeline(connect(db)), shared, data)
        gate.wait()
        try:
            r.poll_once(pid)
        except Exception as e:  # noqa: BLE001
            errors.append(e)
    with mock.patch.dict(os.environ, ON), _own_turn(), mock.patch.object(MockImageProvider, "download", slow):
        ts = [threading.Thread(target=go) for _ in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
    assert errors == [] and len(downloads) == 1
    assert _succeeded_events(p, jid) == 1


def test_crash_mid_download_is_reconciled_after_the_claim_expires(tmp_path):
    """A poller died holding the claim (mid-download): the job stays running, nobody downloads it twice meanwhile; once the claim is
    older than CLAIM_TTL_S the next poll downloads it once and succeeds it."""
    db, p, pid, jid = _setup(tmp_path)
    data = str(tmp_path / "data")
    shared = MockImageProvider()
    with mock.patch.dict(os.environ, ON), _own_turn():
        r = ImageRunner(p, shared, data)
        r.submit_pending(pid)
        dead = connect(db)
        assert poll_claim.claim(dead, jid, "dead-process")
        target = r._dest_path(p.job(jid))
        stale_part = safe_download.part_path(target)          # its half-written temp file
        open(stale_part, "wb").write(b"half")
        os.utime(stale_part, (time.time() - safe_download.STALE_PART_S - 5,) * 2)
        assert r.poll_once(pid)["succeeded"] == 0
        assert p.job(jid)["state"] == "running" and not os.path.exists(target)
        dead.execute("UPDATE job_poll_claims SET at=?", (time.time() - poll_claim.CLAIM_TTL_S - 1,))
        dead.commit()
        assert r.poll_once(pid)["succeeded"] == 1
    assert _succeeded_events(p, jid) == 1 and os.path.isfile(target)
    assert not os.path.exists(stale_part)                     # the dead process's temp is cleaned


def test_flag_off_still_respects_another_processs_poll_claim(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    data = str(tmp_path / "data")
    with mock.patch.dict(os.environ, OFF), _own_turn():
        r = ImageRunner(p, MockImageProvider(), data)
        r.submit_pending(pid)
        other = connect(db)
        assert poll_claim.claim(other, jid, "dashboard")
        assert r.poll_once(pid)["succeeded"] == 0
        poll_claim.release(other, jid, "dashboard")
        assert r.poll_once(pid)["succeeded"] == 1


def test_flag_off_never_creates_the_claim_table(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    with mock.patch.dict(os.environ, OFF), _own_turn():
        r = ImageRunner(p, MockImageProvider(), str(tmp_path / "data"))
        r.submit_pending(pid)
        assert r.poll_once(pid)["succeeded"] == 1
    assert p.conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='job_poll_claims'").fetchone()[0] == 0


# ---- A15: temp file + os.replace (no half-written result, WinError 32 tried again) ---------------------------------------------------

class HalfWriter(MockImageProvider):
    """Writes the result in two parts; between them a reader (QC / the Dashboard) looks at the FINAL path."""
    def __init__(self, target_of, seen):
        super().__init__()
        self.target_of, self.seen = target_of, seen

    def download(self, task_id, dest_path):
        with open(dest_path, "wb") as f:
            f.write(PNG[:8])
            f.flush()
            target = self.target_of()
            self.seen.append(open(target, "rb").read() if os.path.exists(target) else None)
            f.write(PNG[8:])
        return dest_path


def test_reader_never_sees_a_half_written_result(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    seen = []
    r = ImageRunner(p, MockImageProvider(), str(tmp_path / "data"))
    r.provider = HalfWriter(lambda: r._dest_path(p.job(jid)), seen)
    r.submit_pending(pid)
    assert r.poll_once(pid)["succeeded"] == 1
    assert seen == [None]                                      # nothing at the final name while it was being written
    path = p.job(jid)["result_path"]
    assert path == r._dest_path(p.job(jid)) and open(path, "rb").read() == PNG     # same path, full content (result unchanged)
    assert [f for f in os.listdir(os.path.dirname(path)) if ".part-" in f] == []


def test_replace_tries_again_while_the_file_is_held(tmp_path):
    src, dest = tmp_path / "a.part-1.png", tmp_path / "a.png"
    src.write_bytes(PNG)
    real, calls = os.replace, []

    def held_twice(a, b):
        calls.append(1)
        if len(calls) <= 2:
            raise PermissionError(32, "The process cannot access the file because it is being used by another process")
        return real(a, b)
    with mock.patch.object(safe_download.os, "replace", held_twice):
        safe_download.replace(str(src), str(dest), sleep=lambda s: None)
    assert len(calls) == 3 and dest.read_bytes() == PNG


def test_download_error_removes_the_temp_and_keeps_the_job_running(tmp_path):
    db, p, pid, jid = _setup(tmp_path)

    class Broken(MockImageProvider):
        def download(self, task_id, dest_path):
            open(dest_path, "wb").write(b"half")
            raise ProviderError("download failed (HTTP 502)", code="download", transient=True)
    r = ImageRunner(p, Broken(), str(tmp_path / "data"))
    r.submit_pending(pid)
    assert r.poll_once(pid)["running"] == 1 and p.job(jid)["state"] == "running"
    folder = os.path.dirname(r._dest_path(p.job(jid)))
    assert os.listdir(folder) == []


# ---- submit with an unknown outcome: never resent, marked for reconciliation --------------------------------------------------------

def _timeout_provider(err):
    class TimesOut(MockImageProvider):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def submit(self, *a, **k):
            self.calls += 1
            raise err
    return TimesOut()


@pytest.mark.parametrize("err", [ProviderError("network error: timed out", code="network", transient=True),
                                 ProviderError("server error (HTTP 504)", code="server_error", transient=True),
                                 RuntimeError("connection aborted mid-upload")])
def test_unknown_submit_is_not_resent_and_is_marked_for_reconciliation(tmp_path, err):
    db, p, pid, jid = _setup(tmp_path)
    prov = _timeout_provider(err)
    r = ImageRunner(p, prov, str(tmp_path / "data"))
    with mock.patch.dict(os.environ, ON):
        r.submit_pending(pid)
        r.submit_pending(pid)                                   # next heartbeat
        assert prov.calls == 1
        job = p.job(jid)
        assert job["state"] == "failed" and job["escalated"] == 1
        assert p.failure_note(jid).startswith(poll_claim.SUBMIT_UNKNOWN)
        assert p.retry(jid, "autopilot: thử lại sau lỗi tạm thời") is None        # automatic retry refused
        assert p.conn.execute("SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0] == 0
        assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code=?", (poll_claim.SUBMIT_UNKNOWN,)).fetchone()[0] == 1
        assert p.retry(jid, "người dùng đã đối soát", by_user=True) is not None    # the person reconciled: may resend


def test_unknown_submit_flag_off_keeps_the_old_resend(tmp_path):
    db, p, pid, jid = _setup(tmp_path)
    prov = _timeout_provider(ProviderError("network error: timed out", code="network", transient=True))
    with mock.patch.dict(os.environ, OFF):
        r = ImageRunner(p, prov, str(tmp_path / "data"))
        r.submit_pending(pid)
        r.submit_pending(pid)
    assert prov.calls == 2 and p.job(jid)["state"] == "queued"      # old behaviour: stays queued, sent again


@pytest.mark.parametrize("err", [ProviderError("network error: [WinError 10061] connection refused", code="network", transient=True),
                                 ProviderError("rate limited (HTTP 429)", code="rate_limited", transient=True)])
def test_not_sent_errors_keep_the_old_queued_path_with_the_flag(tmp_path, err):
    db, p, pid, jid = _setup(tmp_path)
    prov = _timeout_provider(err)
    with mock.patch.dict(os.environ, ON), mock.patch.object(R.THROTTLE, "on_rate_limited", lambda *a: False):   # no global limit change
        ImageRunner(p, prov, str(tmp_path / "data")).submit_pending(pid)
    assert p.job(jid)["state"] == "queued"


def test_a_claim_that_expired_mid_download_does_not_write_twice(tmp_path):
    """Rà agent: TTL shorter than a long download + cut → the other process took over; the slow one must not succeed it again."""
    db, p, pid, jid = _setup(tmp_path)
    data = str(tmp_path / "data")
    shared = MockImageProvider()
    orig = MockImageProvider.download

    def slow(self, task_id, dest):
        late = connect(db)                                        # meanwhile: our claim expired, another process took the job
        late.execute("UPDATE job_poll_claims SET owner='other', at=?", (time.time(),))
        late.commit()
        return orig(self, task_id, dest)
    with mock.patch.dict(os.environ, ON), _own_turn():
        r = ImageRunner(p, shared, data)
        r.submit_pending(pid)
        with mock.patch.object(MockImageProvider, "download", slow):
            assert r.poll_once(pid)["succeeded"] == 0
    assert p.job(jid)["state"] == "running" and _succeeded_events(p, jid) == 0
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='poll_claim_lost'").fetchone()[0] == 1


@pytest.mark.parametrize("err,unknown", [(FileNotFoundError("ảnh tham chiếu không có"), False), (ValueError("bad size"), False),
                                         (ConnectionResetError(10054, "reset"), True),
                                         (ProviderError("invalid JSON response: b'<html>'", code="bad_response"), True),
                                         (ProviderError("HTTP 400: bad prompt", code="http_error"), False)])
def test_unknown_outcome_classification(err, unknown):
    assert poll_claim.unknown_outcome(err) is unknown


def test_final_cut_does_not_list_a_result_still_downloading(tmp_path):
    from core import final_cut
    db, p, pid, jid = _setup(tmp_path)
    data = str(tmp_path / "data")
    folder = os.path.dirname(final_cut.clip_path(data, pid, 0))
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, "01.part-123-abcd1234.mp4"), "wb").write(b"half")
    names = [c["title"] for c in final_cut.collect_clips(p, data, pid) if c.get("extra")]
    assert names == []
