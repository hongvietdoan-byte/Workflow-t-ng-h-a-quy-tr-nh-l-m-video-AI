"""Lần rà lỗi phải có mục đỏ trước khi có ai thử gửi gen; chỉ SQLite giả."""
import os
import sqlite3
from unittest import mock

import pytest

with mock.patch.object(os, "environ", {}):
    from core import change_review as CR


@pytest.fixture
def conn(tmp_path):
    with mock.patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}), \
         mock.patch.object(CR, "enabled", return_value=True), \
         mock.patch.object(CR, "motion_enabled", return_value=False):
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        c.executescript("""
            CREATE TABLE scenes(id INTEGER PRIMARY KEY, project_id INTEGER, idx INTEGER);
            CREATE TABLE change_events(id INTEGER PRIMARY KEY, project_id INTEGER, scene_id INTEGER,
                kind TEXT, state TEXT, note TEXT, reviewed_at TEXT);
            CREATE TABLE change_findings(id INTEGER PRIMARY KEY, event_id INTEGER, project_id INTEGER,
                scene_id INTEGER, source TEXT, level TEXT, khau TEXT, msg TEXT, de_xuat TEXT,
                at TEXT, status TEXT DEFAULT 'open', resolved_at TEXT, resolved_by TEXT);
            INSERT INTO scenes VALUES(1, 10, 1), (2, 20, 1);
        """)
        yield c
        c.close()


def event(conn, eid=1, sid=1, pid=10, kind="scene", state="failed", note="Đăng nhập giả hết hạn"):
    conn.execute("INSERT INTO change_events VALUES(?,?,?,?,?,?,?)",
                 (eid, pid, sid, kind, state, note, "2026-10-24T01:00:00"))


def test_materialize_without_blocking_is_idempotent_and_red(conn):
    event(conn); conn.commit()
    CR.refresh_failed_findings(conn, 10)
    rows = CR.open_findings(conn, 10)
    assert len(rows) == 1 and rows[0]["level"] == "do"
    assert rows[0]["event_id"] == 1
    CR.refresh_failed_findings(conn, 10)
    assert len(CR.open_findings(conn, 10)) == 1
    assert CR.blocking(conn, 1) is not None


def test_only_requested_project_and_enabled_kinds(conn):
    event(conn, sid=2, pid=20)
    event(conn, eid=2, kind="motion")
    conn.commit()
    CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10) == []
    assert CR.open_findings(conn, 20) == []
    with mock.patch.object(CR, "motion_enabled", return_value=True):
        CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10)[0]["event_id"] == 2


def test_dismissed_failure_stays_closed_but_new_failure_reopens(conn):
    event(conn); conn.commit()
    CR.refresh_failed_findings(conn, 10)
    row = CR.open_findings(conn, 10)[0]
    conn.execute("UPDATE change_findings SET status='dismissed', resolved_by='ep-fake' WHERE id=?", (row["id"],))
    conn.commit()
    CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10) == []
    event(conn, eid=2); conn.commit()
    CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10)[0]["event_id"] == 2


def test_quota_is_held_and_reviewed_failure_closes(conn):
    event(conn, state="code_only", note=CR.QUOTA_NOTE + "giả")
    conn.commit()
    CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10)[0]["level"] == "do"
    conn.execute("UPDATE change_events SET state='reviewed'"); conn.commit()
    CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10) == []


def test_caller_transaction_not_committed(conn):
    event(conn)
    CR.refresh_failed_findings(conn, 10)
    assert len(CR.open_findings(conn, 10)) == 1
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM change_events").fetchone()[0] == 0
    assert CR.open_findings(conn, 10) == []


def test_off_no_write(conn):
    event(conn); conn.commit()
    with mock.patch.object(CR, "enabled", return_value=False):
        CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10) == []


@pytest.mark.parametrize("outer", [False, True])
def test_partial_failure_rolls_back_only_own_writes(conn, outer):
    event(conn)
    conn.execute("INSERT INTO scenes VALUES(3,10,2)")
    conn.commit()
    if outer:
        event(conn, eid=9, sid=3)
    original = CR._hold_failed

    def fail_second(c, sid, kinds):
        if sid == 3:
            raise ValueError("échec simulé")
        return original(c, sid, kinds)

    with mock.patch.object(CR, "_hold_failed", side_effect=fail_second), pytest.raises(ValueError):
        CR.refresh_failed_findings(conn, 10)
    assert CR.open_findings(conn, 10) == []
    assert conn.in_transaction is outer
    assert conn.execute("SELECT COUNT(*) FROM change_events WHERE id=9").fetchone()[0] == int(outer)


def test_read_api_does_not_materialize_or_commit(conn):
    event(conn)
    assert CR.open_findings(conn, 10) == []
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM change_events").fetchone()[0] == 0
