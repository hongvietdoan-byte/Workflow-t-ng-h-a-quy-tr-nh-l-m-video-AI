"""M82 pha A: luồng Cơ bản dùng DB/provider giả; không nối entrypoint production."""
import json
import os
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def project(tmp_path):
    with patch.object(os, "environ", {"DASHBOARD_AUTH": "on", "HOME": str(tmp_path),
                                    "USERPROFILE": str(tmp_path)}):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
        CREATE TABLE projects(id INTEGER PRIMARY KEY,name TEXT,created_by TEXT);
        CREATE TABLE users(email TEXT PRIMARY KEY,role TEXT,active INTEGER);
        CREATE TABLE project_watchers(project_id INTEGER,email TEXT,level TEXT);
        CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE audit_log(at TEXT,email TEXT,action TEXT,detail TEXT);
        INSERT INTO projects VALUES(1,'Phim giả','ep@example.test');
        INSERT INTO users VALUES('ep@example.test','member',1);
        INSERT INTO users VALUES('edit@example.test','member',1);
        INSERT INTO project_watchers VALUES(1,'edit@example.test','edit');
        INSERT INTO app_settings VALUES('project_budget:1','{"total":99,"locked":true,"approved_by":"cũ"}');
        """)
        p = SimpleNamespace(conn=conn, user={"email": "ep@example.test", "role": "member"})
        from core import simple_budget
        with patch.object(simple_budget, "proposal", return_value={"total": 10.0, "incomplete": False}), \
                patch.object(simple_budget, "enabled", return_value=True):
            yield p
        conn.close()


def test_auto_budget_is_separate_from_old_warning_cap(project):
    from core import simple_budget as B
    old = project.conn.execute("SELECT value FROM app_settings WHERE key='project_budget:1'").fetchone()[0]
    approved = B.approve(project, 1, expected_total=10.0, confirmed=True)
    assert approved["limit_usd"] == 10.0
    assert approved["approved_by"] == "ep@example.test"
    assert project.conn.execute("SELECT value FROM app_settings WHERE key='project_budget:1'").fetchone()[0] == old
    assert B.approve(project, 1, expected_total=10.0, confirmed=True) == approved


@pytest.mark.parametrize("identity", [None, {"email": "edit@example.test", "role": "member"},
                                    {"email": "missing@example.test", "role": "owner"}])
def test_budget_rejects_missing_identity_editor_and_forged_owner(project, identity):
    from core import simple_budget as B
    project.user = identity
    with pytest.raises(PermissionError):
        B.approve(project, 1, expected_total=10.0, confirmed=True)
    assert B.get(project.conn, 1) is None


def test_budget_requires_current_project_confirmation_and_current_quote(project):
    from core import simple_budget as B
    for pid, total, confirmed in ((999, 10, True), (1, 10, False), (1, 11, True)):
        with pytest.raises((PermissionError, ValueError)):
            B.approve(project, pid, expected_total=total, confirmed=confirmed)
    assert B.get(project.conn, 1) is None


def test_disabled_user_cannot_approve_even_with_old_session(project):
    from core import simple_budget as B
    project.conn.execute("UPDATE users SET active=0 WHERE email='ep@example.test'")
    with pytest.raises(PermissionError):
        B.approve(project, 1, expected_total=10.0, confirmed=True)


def test_approval_rollback_belongs_to_caller_transaction(project):
    from core import simple_budget as B
    project.conn.execute("BEGIN")
    B.approve(project, 1, expected_total=10.0, confirmed=True)
    project.conn.rollback()
    assert B.get(project.conn, 1) is None
    assert project.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0


def test_eighty_percent_includes_reservations_without_blocking_manual_spend():
    from core import simple_budget as B
    status = B.utilization({"limit_usd": 10}, recorded=7, held=1)
    assert status["warning"] is True and status["ratio"] == .8
    assert B.utilization(None, recorded=0, held=0)["ratio"] is None


def test_simple_mode_is_off_and_legacy_entrypoints_are_not_modified():
    from core import features
    assert features.FEATURES["simple_mode"]["verified"] is False
    assert not features.FEATURES["simple_mode"].get("default_on")
    from dashboard import basic
    with patch.object(basic, "enabled", return_value=False):
        assert basic.render(None, 1, None) is False
