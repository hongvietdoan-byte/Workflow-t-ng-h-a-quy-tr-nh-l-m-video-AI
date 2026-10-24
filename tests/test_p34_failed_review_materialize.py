"""Lần rà lỗi phải có mục đỏ trước khi có ai thử gửi gen; chỉ SQLite giả."""
import os
import sqlite3
import ast
from pathlib import Path
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
        # Production scenes và change_events đều có state: bắt lỗi SQL ambiguous.
        c.execute("ALTER TABLE scenes ADD COLUMN state TEXT DEFAULT 'ready'")
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
    conn.execute("INSERT INTO scenes(id,project_id,idx) VALUES(3,10,2)")
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


def test_failure_summary_sees_error_before_gate_without_writing(conn):
    event(conn)
    rows = CR.failed_review_summary(conn, 10)
    assert len(rows) == 1 and rows[0]["idx"] == 1
    assert rows[0]["reason"] == "Đăng nhập giả hết hạn"
    assert conn.in_transaction and CR.open_findings(conn, 10) == []
    conn.rollback()
    assert CR.failed_review_summary(conn, 10) == []


def test_failure_summary_hides_only_manual_closed_failures(conn):
    event(conn); conn.commit()
    CR.refresh_failed_findings(conn, 10)
    assert len(CR.failed_review_summary(conn, 10)) == 1
    conn.execute("UPDATE change_findings SET status='dismissed', resolved_by='ep-fake'")
    conn.commit()
    assert CR.failed_review_summary(conn, 10) == []
    event(conn, eid=2); conn.commit()
    assert len(CR.failed_review_summary(conn, 10)) == 1


def test_failure_summary_scope_flag_and_redaction(conn):
    event(conn, note="token=FAKE_SECRET_SENTINEL_123456789")
    event(conn, eid=2, sid=2, pid=20)
    conn.commit()
    assert CR.failed_review_summary(conn, 10)[0]["reason"] == "token=***"
    assert len(CR.failed_review_summary(conn, 20)) == 1
    with mock.patch.object(CR, "enabled", return_value=False):
        assert CR.failed_review_summary(conn, 10) == []


class ReadOnlyScreen:
    def __init__(self):
        self.messages = []
    def error(self, text):
        self.messages.append(text)
    def expander(self, text, **kwargs):
        self.messages.append(text)
        return self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def caption(self, text):
        self.messages.append(text)


def render_function(screen):
    source = (Path(__file__).resolve().parents[1] / "dashboard/change_review_ui.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "render")
    namespace = {"CR": CR, "st": screen}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "review_screen_fixture", "exec"), namespace)
    return namespace["render"]


def test_readonly_screen_never_says_no_findings_for_unmaterialized_error(conn):
    event(conn); conn.commit()
    conn.execute("ALTER TABLE change_events ADD COLUMN cost_usd REAL DEFAULT 0")
    screen = ReadOnlyScreen()
    p = type("FakePipeline", (), {"conn": conn})()
    render_function(screen)(p, 10, read_only=True)
    assert any(m.startswith("Rà soát LỖI:") for m in screen.messages)
    assert not any("không có mục lệch" in m for m in screen.messages)
    assert CR.open_findings(conn, 10) == []


def test_screen_read_error_cannot_be_reported_as_clean(conn):
    screen = ReadOnlyScreen()
    p = type("FakePipeline", (), {"conn": conn})()
    with mock.patch.object(CR, "failed_review_summary", side_effect=ValueError("fixture")):
        render_function(screen)(p, 10, read_only=True)
    assert screen.messages == ["Không đọc được trạng thái rà soát — chưa xác định cổng gen; thử tải lại trang."]
