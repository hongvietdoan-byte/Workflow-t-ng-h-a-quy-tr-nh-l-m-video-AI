"""Bỏ qua lỗi rà soát phải có EP, lý do, snapshot và audit nguyên tử."""
import json
import os
import sqlite3
from unittest import mock

import pytest

with mock.patch.object(os, "environ", {}):
    from core import change_review as CR, stage_desk

USER = {"email": "ep@example.test", "role": "member"}
ACTOR = {"kind": "human", "who": "ep@example.test"}


@pytest.fixture
def conn(tmp_path):
    with mock.patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "DASHBOARD_AUTH": "on"}), \
         mock.patch.object(CR, "enabled", return_value=True), \
         mock.patch.object(CR, "motion_enabled", return_value=False), \
         mock.patch.object(stage_desk, "is_executive_producer", return_value=True):
        c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
        c.executescript("""
          CREATE TABLE users(email TEXT,role TEXT,active INTEGER);
          INSERT INTO users VALUES('ep@example.test','member',1);
          CREATE TABLE scenes(id INTEGER PRIMARY KEY,project_id INTEGER,idx INTEGER);
          INSERT INTO scenes VALUES(1,10,1);
          CREATE TABLE change_events(id INTEGER PRIMARY KEY, project_id INTEGER,scene_id INTEGER,kind TEXT,
            state TEXT,note TEXT,reviewed_at TEXT);
          INSERT INTO change_events VALUES(1,10,1,'scene','failed','fixture','2026-10-24T01:00:00.111');
          CREATE TABLE change_findings(id INTEGER PRIMARY KEY,event_id INTEGER,project_id INTEGER,scene_id INTEGER,
            source TEXT,level TEXT,khau TEXT,msg TEXT,de_xuat TEXT,at TEXT,status TEXT DEFAULT 'open',resolved_at TEXT,resolved_by TEXT);
          CREATE TABLE audit_log(at TEXT,email TEXT,action TEXT,detail TEXT);
        """)
        CR.refresh_failed_findings(c, 10)
        yield c
        c.close()


def skip(c, *, snapshot=None, pid=10, actor=ACTOR, user=USER, reason="Đã kiểm thủ công bản giả"):
    return CR.dismiss_failed_review(c, 1, pid, actor=actor, user=user, reason=reason,
                                    expected_snapshot=snapshot or CR.failed_review_snapshot(c, 1, pid))


def test_skip_audited_and_releases_only_shown_failure(conn):
    skip(conn)
    assert CR.blocking(conn, 1) is None
    row = conn.execute("SELECT action,detail FROM audit_log").fetchone()
    detail = json.loads(row["detail"])
    assert row["action"] == "change_review_bypass"
    assert detail["reason"] == "Đã kiểm thủ công bản giả" and detail["finding_id"] == 1
    conn.execute("INSERT INTO change_events VALUES(2,10,1,'scene','failed','new fixture','2026-10-24T01:00:01')")
    conn.commit()
    assert CR.blocking(conn, 1) is not None


@pytest.mark.parametrize("reason", [None, "", "  ", "x" * 1001])
def test_reason_required_without_writes(conn, reason):
    with pytest.raises(ValueError): skip(conn, reason=reason)
    assert CR.open_findings(conn, 10)[0]["status"] == "open"
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0


@pytest.mark.parametrize("actor,user", [({"kind":"ai","who":"ep@example.test"},USER),
    ({"kind":"human","who":"other@example.test"},USER), (ACTOR,None)])
def test_only_authenticated_matching_human(conn, actor, user):
    with pytest.raises(ValueError): skip(conn, actor=actor, user=user)
    assert CR.blocking(conn, 1) is not None


def test_non_ep_or_revoked_user_cannot_skip(conn):
    with mock.patch.object(stage_desk, "is_executive_producer", return_value=False):
        with pytest.raises(ValueError): skip(conn)
    conn.execute("UPDATE users SET active=0"); conn.commit()
    with pytest.raises(ValueError): skip(conn)
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0


@pytest.mark.parametrize("change", ["INSERT INTO change_events VALUES(2,10,1,'scene','failed','new','2026-10-24T01:00:00.222')",
    "UPDATE change_events SET reviewed_at='2026-10-24T01:00:00.222', note='again' WHERE id=1"])
def test_unseen_failure_even_same_second_rejects_stale_snapshot(conn, change):
    stamp = CR.failed_review_snapshot(conn, 1, 10)
    conn.execute(change); conn.commit()
    with pytest.raises(ValueError): skip(conn, snapshot=stamp)
    assert CR.blocking(conn, 1) is not None


def test_project_scope_and_legacy_bypass_closed(conn):
    with pytest.raises(ValueError): skip(conn, pid=20)
    with pytest.raises(ValueError): CR.close(conn, 1, "dismissed", "untrusted")
    assert CR.blocking(conn, 1) is not None


@pytest.mark.parametrize("outer", [False, True])
def test_audit_failure_rolls_back_and_preserves_caller(conn, outer):
    conn.execute("DROP TABLE audit_log"); conn.commit()
    if outer: conn.execute("UPDATE users SET role='member'")
    with pytest.raises(ValueError): skip(conn)
    assert conn.in_transaction is outer
    assert CR.open_findings(conn, 10)[0]["status"] == "open"


def test_outer_rollback_restores_bypass_and_audit(conn):
    conn.execute("UPDATE users SET role='member'")
    skip(conn)
    assert conn.in_transaction
    conn.rollback()
    assert CR.open_findings(conn, 10)[0]["status"] == "open"
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0


def test_same_event_fails_again_after_skip_even_in_same_second(conn):
    with mock.patch.object(CR, "_now", return_value="2026-10-24T01:00:00Z"):
        conn.execute("UPDATE change_findings SET at='2026-10-24T01:00:00Z'"); conn.commit()
        skip(conn)
        conn.execute("UPDATE change_events SET reviewed_at='2026-10-24T01:00:00.222',note='new after bypass'")
        conn.commit()
        assert CR.failed_review_summary(conn, 10)
        assert CR.blocking(conn, 1) is not None


def test_feature_off_or_cached_owner_cannot_bypass(conn):
    with mock.patch.object(CR, "enabled", return_value=False):
        with pytest.raises(ValueError): skip(conn)
    with mock.patch.object(stage_desk, "is_executive_producer", side_effect=lambda c,p,u: u["role"] == "owner"):
        with pytest.raises(ValueError): skip(conn, user=dict(USER, role="owner"))
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0


def test_audit_keeps_only_version_hashes_and_redacts_reason(conn):
    skip(conn, reason="token=FAKE_SECRET_SENTINEL_123456789")
    detail = json.loads(conn.execute("SELECT detail FROM audit_log").fetchone()[0])
    assert detail["reason"] == "token=***"
    assert list(detail["event_versions"]) == ["1"]
    assert len(detail["event_versions"]["1"]) == 64
