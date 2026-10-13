import sqlite3
import subprocess
import sys
import time
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from core import director_lease
from core import llm_runner as lr
from core.db import connect
from core.pipeline import Pipeline


def test_two_connections_reject_duplicate_and_release(tmp_path):
    path = str(tmp_path / 'manifest.sqlite')
    started, finish = Event(), Event()

    def first():
        with sqlite3.connect(path) as conn:
            with director_lease.hold(conn, 27):
                started.set()
                assert finish.wait(5)

    with ThreadPoolExecutor(2) as pool:
        future = pool.submit(first)
        assert started.wait(5)
        with sqlite3.connect(path) as conn:
            assert director_lease.busy(conn, 27)
            with pytest.raises(director_lease.DirectorBusy, match='Đạo diễn đang chạy'):
                with director_lease.hold(conn, 27):
                    pytest.fail('duplicate entered')
        finish.set()
        future.result()
    with sqlite3.connect(path) as conn:
        assert not director_lease.busy(conn, 27)
        with pytest.raises(ValueError):
            with director_lease.hold(conn, 27):
                raise ValueError('failed')
        assert not director_lease.busy(conn, 27)


def test_bad_raw_redacts_before_trim():
    text = 'secret: abcdefghi C:\\private\\file /home/person/private sk-abcdefghijklmnop ' + 'x ' * 20000
    clean = director_lease.safe_reply(text)
    assert len(clean) <= director_lease.RAW_LIMIT
    for secret in ('abcdefghi', 'C:\\private', '/home/person', 'sk-abcdefghijklmnop'):
        assert secret not in clean


def test_wrappers_share_lock_before_attach_or_paid_call(tmp_path, monkeypatch):
    path = str(tmp_path / 'manifest.sqlite')
    conn = connect(path)
    p = Pipeline(conn)
    pid = p.create_project('t', 'auto')
    p.create_scene(pid, 1, 'CẢNH 1')
    conn.close()
    started, finish = Event(), Event()
    calls = []
    original = lr.assets.auto_attach
    attaches = []

    def attach(*args, **kwargs):
        attaches.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(lr.assets, 'auto_attach', attach)

    class Slow(lr.MockLlm):
        def complete(self, prompt, images=()):
            calls.append(True)
            started.set()
            assert finish.wait(10)
            return super().complete(prompt, images)

    def first():
        connection = connect(path)
        try:
            return lr.run_director(Pipeline(connection), pid, Slow())
        finally:
            connection.close()

    with ThreadPoolExecutor(2) as pool:
        future = pool.submit(first)
        assert started.wait(10)
        conn = connect(path)
        duplicate = Pipeline(conn)
        try:
            for run in (lambda: lr.run_director(duplicate, pid, Slow(), resume=True),
                        lambda: lr.run_director_scene(duplicate, pid, 1, Slow())):
                with pytest.raises(lr.LlmError) as exc:
                    run()
                assert exc.value.code == 'director_busy'
            assert len(calls) == len(attaches) == 1
        finally:
            finish.set()
            conn.close()
        assert future.result()['scenes'] == 1


def test_cross_process_dead_pid_and_stale_owner(tmp_path):
    path = str(tmp_path / 'manifest.sqlite')
    script = "from core import director_lease as d; import sqlite3,sys,time; c=sqlite3.connect(sys.argv[1]);\nclass Slow:\n def complete(self):\n  print('ready',flush=True); time.sleep(30)\nwith d.hold(c,27) as lease:\n d.GuardedClient(Slow(),lease).complete()"
    child = subprocess.Popen([sys.executable, '-c', script, path], stdout=subprocess.PIPE, text=True)
    conn = sqlite3.connect(path)
    try:
        assert child.stdout.readline().strip() == 'ready'
        with pytest.raises(director_lease.DirectorBusy):
            with director_lease.hold(conn, 27):
                pytest.fail('cross process duplicate')
        child.terminate()
        child.wait(10)
        with director_lease.hold(conn, 27) as old_owner:
            db = director_lease._open(director_lease._path(conn))
            db.execute('UPDATE leases SET heartbeat=?', (time.time() - director_lease.LEASE_SECONDS - 1,))
            db.commit()
            with director_lease.hold(conn, 27) as new_owner:
                assert old_owner != new_owner
                # Kết thúc chủ cũ không xóa chủ mới (cùng điều kiện DELETE ở finally).
                db.execute('DELETE FROM leases WHERE project=? AND owner=?', (27, old_owner[2]))
                db.commit()
                assert director_lease.busy(conn, 27)
            db.close()
        assert not director_lease.busy(conn, 27)
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(10)
        conn.close()


def test_failed_raw_keeps_good_plan_and_two_attempts(tmp_path):
    conn = connect(str(tmp_path / 'manifest.sqlite'))
    p = Pipeline(conn)
    pid = p.create_project('t', 'auto')
    p.create_scene(pid, 1, 'CẢNH 1')
    lr.run_director(p, pid, lr.MockLlm())
    good = p.project(pid)['director_raw']

    class Bad:
        def complete(self, *args):
            return lr.LlmReply('wrong secret: abcdefghi C:\\private\\file', 1, 1)

    for run in (lambda: lr.run_director(p, pid, Bad()), lambda: lr.run_director_scene(p, pid, 1, Bad())):
        with pytest.raises(lr.LlmError):
            run()
        assert not director_lease.busy(conn, pid)
        assert p.project(pid)['director_raw'] == good
    replies = director_lease.replies(conn, pid)
    assert len(replies) == 4
    assert {r[0] for r in replies} == {'single', 'scene:1'}
    assert all('abcdefghi' not in r[2] and 'C:\\private' not in r[2] for r in replies)
    conn.close()


def test_stale_reply_cannot_write_and_owner_release_keeps_new_lock(tmp_path):
    conn = connect(str(tmp_path / 'manifest.sqlite'))
    p = Pipeline(conn)
    pid = p.create_project('t', 'auto')
    p.create_scene(pid, 1, 'CẢNH 1')
    lr.run_director(p, pid, lr.MockLlm())
    good = p.project(pid)['director_raw']

    class Stolen(lr.MockLlm):
        def complete(self, *args):
            db = director_lease._open(director_lease._path(conn))
            db.execute('UPDATE leases SET owner=? WHERE project=?', ('new-owner', pid))
            db.commit()
            db.close()
            return super().complete(*args)

    with pytest.raises(lr.LlmError) as exc:
        lr.run_director(p, pid, Stolen())
    assert exc.value.code == 'director_expired'
    assert p.project(pid)['director_raw'] == good
    assert director_lease.busy(conn, pid)
    conn.close()


@pytest.mark.parametrize('bad_stage', ['A', 'B'])
def test_two_pass_raw_capture(bad_stage, monkeypatch):
    from tests.test_v3 import kenta_project
    monkeypatch.setenv('FEATURE_DIRECTOR_TWO_PASS', '1')
    p, pid = kenta_project()

    class Bad(lr.MockLlm):
        def complete(self, prompt, images=()):
            text = lr.plain(prompt)
            stage = 'A' if text.startswith('# Đạo diễn — Tầng A') else 'B'
            if stage == bad_stage:
                return lr.LlmReply('not JSON secret: abcdefghi', 1, 1)
            return super().complete(prompt, images)

    with pytest.raises(lr.LlmError):
        lr.run_director(p, pid, Bad())
    raw = director_lease.replies(p.conn, pid)
    assert len(raw) >= 2
    assert all(row[0].startswith(bad_stage) and 'abcdefghi' not in row[2] for row in raw)
    assert not director_lease.busy(p.conn, pid)


def test_byte_bound_and_literal_secret(monkeypatch):
    monkeypatch.setenv('CUSTOM_API_TOKEN', 'odd.literal.secret')
    text = director_lease.safe_reply('odd.literal.secret ' + 'Việt ' * 20000)
    assert 'odd.literal.secret' not in text
    assert len(text.encode('utf-8')) <= director_lease.RAW_LIMIT


def test_hard_timeout_fences_call_and_store(tmp_path):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    with director_lease.hold(conn, 27) as lease:
        db = director_lease._open(director_lease._path(conn))
        db.execute('UPDATE leases SET started=?', (time.time() - director_lease.MAX_RUN_SECONDS - 1,))
        db.commit()

        class Never:
            def complete(self):
                pytest.fail('expired owner called model')

        with pytest.raises(director_lease.LeaseLost):
            director_lease.GuardedClient(Never(), lease).complete()
        with pytest.raises(director_lease.LeaseLost):
            with director_lease.writing():
                pytest.fail('expired owner stored plan')
        with director_lease.hold(conn, 27):
            assert director_lease.busy(conn, 27)
        db.close()
    conn.close()


def test_raw_history_bounded(tmp_path):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    save = director_lease.capture(conn, 27, 'A')
    for index in range(25):
        save(str(index))
    rows = director_lease.replies(conn, 27)
    assert len(rows) == 20
    assert rows[0][2] == '24' and rows[-1][2] == '5'
    conn.close()


@pytest.mark.parametrize('expired_field,seconds', [('heartbeat', director_lease.LEASE_SECONDS), ('started', director_lease.MAX_RUN_SECONDS)])
def test_pending_call_blocks_expired_takeover_and_ui(tmp_path, expired_field, seconds):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    calls = []

    class Pending:
        def complete(self):
            calls.append('old')
            with director_lease._open(director_lease._path(conn)) as db:
                db.execute(f'UPDATE leases SET {expired_field}=?', (time.time() - seconds - 1,))
            assert director_lease.busy(conn, 27)
            with pytest.raises(director_lease.DirectorBusy):
                with director_lease.hold(conn, 27):
                    calls.append('new')
            return 'reply'

    with director_lease.hold(conn, 27) as lease:
        with pytest.raises(director_lease.LeaseLost):
            director_lease.GuardedClient(Pending(), lease).complete()
        assert not director_lease.busy(conn, 27)
        with director_lease.hold(conn, 27):
            assert director_lease.busy(conn, 27)
    assert calls == ['old']
    conn.close()


def test_cleanup_failure_preserves_original(tmp_path, monkeypatch):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    original = director_lease._open
    with pytest.warns(RuntimeWarning) as warning:
        with pytest.raises(ValueError, match='original client error'):
            with director_lease.hold(conn, 27):
                monkeypatch.setattr(director_lease, '_open', lambda path: (_ for _ in ()).throw(sqlite3.OperationalError('secret: abcdefghi')))
                raise ValueError('original client error')
    assert 'abcdefghi' not in str(warning[0].message)
    monkeypatch.setattr(director_lease, '_open', original)
    conn.close()


@pytest.mark.parametrize('truncated', [False, True])
def test_capture_failure_keeps_error_and_retry_count(tmp_path, monkeypatch, truncated):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    save = director_lease.capture(conn, 27, 'single')
    monkeypatch.setattr(director_lease, '_open', lambda path: (_ for _ in ()).throw(sqlite3.OperationalError('secret: abcdefghi')))
    calls = []

    class Bad:
        def complete(self, *args):
            calls.append(True)
            if truncated:
                raise lr.LlmError('cut answer', code='truncated', partial='secret: abcdefghi')
            return lr.LlmReply('bad secret: abcdefghi', 1, 1)

    with pytest.warns(RuntimeWarning) as warning:
        with pytest.raises(lr.LlmError) as exc:
            lr.ask_json(Bad(), 'prompt', lambda obj: obj, bad_reply=save)
    assert all('abcdefghi' not in str(w.message) for w in warning)
    assert exc.value.code == ('truncated' if truncated else 'bad_json')
    assert len(calls) == (1 if truncated else 2)
    if truncated:
        assert exc.value.partial == 'secret: abcdefghi'
    conn.close()


def test_replan_merged_failure_is_captured_and_diagnosed(monkeypatch):
    from tests.test_v3 import kenta_project
    from core import llm_io, diag
    monkeypatch.setenv('FEATURE_DIRECTOR_TWO_PASS', '1')
    p, pid = kenta_project()
    lr.run_director(p, pid, lr.MockLlm())
    good = {key: p.project(pid)[key] for key in ('director_raw', 'director_intent_raw')}
    monkeypatch.setattr(llm_io, 'validate_for_project', lambda *args: lambda obj: (_ for _ in ()).throw(llm_io.SchemaError('secret: abcdefghi')))
    with pytest.raises(lr.LlmError) as exc:
        lr.run_director_scene(p, pid, 1, lr.MockLlm())
    assert exc.value.code == 'bad_plan'
    raw = director_lease.replies(p.conn, pid)
    assert len(raw) == 1 and raw[0][0] == 'merged:scene:1'
    assert 'abcdefghi' not in raw[0][2] and len(raw[0][2].encode('utf-8')) <= director_lease.RAW_LIMIT
    assert any(row['code'] == 'bad_plan' for row in diag.recent(p.conn))
    assert good == {key: p.project(pid)[key] for key in good}
    p.conn.close()


def test_parallel_pending_count_does_not_clear_early(tmp_path):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    entered = [Event(), Event()]
    finish = [Event(), Event()]

    class Slow:
        def __init__(self, idx):
            self.idx = idx

        def complete(self):
            entered[self.idx].set()
            assert finish[self.idx].wait(5)
            return 'reply'

    with director_lease.hold(conn, 27) as lease:
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(director_lease.GuardedClient(Slow(idx), lease).complete) for idx in range(2)]
            try:
                assert all(event.wait(5) for event in entered)
                with director_lease._open(director_lease._path(conn)) as db:
                    db.execute('UPDATE leases SET started=?', (time.time() - director_lease.MAX_RUN_SECONDS - 1,))
                finish[0].set()
                with pytest.raises(director_lease.LeaseLost):
                    futures[0].result(5)
                assert director_lease.busy(conn, 27)
                with pytest.raises(director_lease.DirectorBusy):
                    with director_lease.hold(conn, 27):
                        pytest.fail('second call remains pending')
            finally:
                for event in finish:
                    event.set()
            with pytest.raises(director_lease.LeaseLost):
                futures[1].result(5)
        assert not director_lease.busy(conn, 27)
    conn.close()


def test_heartbeat_recovers_after_temporary_sqlite_error(tmp_path, monkeypatch):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    original = director_lease._open
    attempts, recovered = [], Event()
    monkeypatch.setattr(director_lease, 'HEARTBEAT_SECONDS', 0.01)

    def opening(path):
        if threading.current_thread() is not threading.main_thread():
            attempts.append(True)
            if len(attempts) == 1:
                raise sqlite3.OperationalError('secret: abcdefghi')
            recovered.set()
        return original(path)

    monkeypatch.setattr(director_lease, '_open', opening)
    with pytest.warns(RuntimeWarning) as warning:
        with director_lease.hold(conn, 27):
            assert recovered.wait(5)
    assert len(attempts) >= 2
    assert all('abcdefghi' not in str(w.message) for w in warning)
    conn.close()


def test_strict_warnings_keep_client_error_and_pending_fail_closed(tmp_path, monkeypatch, capsys):
    conn = sqlite3.connect(str(tmp_path / 'manifest.sqlite'))
    original = director_lease._open

    class Failed:
        def complete(self):
            monkeypatch.setattr(director_lease, '_open', lambda path: (_ for _ in ()).throw(sqlite3.OperationalError('secret: abcdefghi')))
            raise lr.LlmError('original client error', code='auth')

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        with pytest.raises(lr.LlmError) as exc:
            with director_lease.hold(conn, 27) as lease:
                director_lease.GuardedClient(Failed(), lease).complete()
    assert exc.value.code == 'auth' and str(exc.value) == 'original client error'
    assert 'abcdefghi' not in capsys.readouterr().err
    monkeypatch.setattr(director_lease, '_open', original)
    assert director_lease.busy(conn, 27)
    with pytest.raises(director_lease.DirectorBusy):
        with director_lease.hold(conn, 27):
            pytest.fail('uncertain pending marker must block')
    monkeypatch.setattr(director_lease, '_alive', lambda pid: False)
    with director_lease.hold(conn, 27):
        pass  # sau xác nhận tiến trình cũ đã chết, pending cũ được thu hồi
    conn.close()


def test_old_calling_mark_of_a_reused_pid_does_not_hold_for_ever(tmp_path):
    """Rà gộp Đ15v2 (12/10): a process died mid-call (mark left), Windows gave its PID to another process → the lease was held for
    ever with no way to free it. The whole-run cap applies to the mark too; the message carries the date."""
    import os
    conn = connect(str(tmp_path / 'm.sqlite'))
    db = director_lease._open(director_lease._path(conn))
    old = time.time() - 30 * 86400
    db.execute('INSERT INTO leases VALUES (27, ?, ?, ?, ?)', ('old', os.getpid(), old, old))     # a live PID (this test's)
    db.execute('INSERT INTO pending_calls VALUES (27, ?, 1)', ('old',))
    db.commit(); db.close()
    assert director_lease.busy(conn, 27) == ''
    with director_lease.hold(conn, 27):
        assert '/' in director_lease.busy(conn, 27)          # dd/mm shown


def test_ui_lease_storage_error_is_fail_closed(monkeypatch):
    from dashboard.steps import step1_director as ui
    import sqlite3
    messages=[]
    monkeypatch.setattr(ui.st,'warning',messages.append)
    monkeypatch.setattr(director_lease,'busy',lambda *a: (_ for _ in ()).throw(sqlite3.OperationalError('fake locked db')))
    running,replies=ui.lease_status(None,27)
    assert running and replies==[] and messages
    assert 'fake locked db' not in running
    monkeypatch.setattr(director_lease,'busy',lambda *a:'')
    monkeypatch.setattr(director_lease,'replies',lambda *a: (_ for _ in ()).throw(OSError('fake disk')))
    running,replies=ui.lease_status(None,27)
    assert running and replies==[] and len(messages)==2
