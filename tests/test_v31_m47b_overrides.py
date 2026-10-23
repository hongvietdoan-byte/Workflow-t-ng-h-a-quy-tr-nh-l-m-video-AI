import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import mock

import pytest

_IMPORT_ENV = {"DASHBOARD_OWNER_EMAIL": "owner@example.test"}
with mock.patch.object(os, "environ", _IMPORT_ENV):
    from core import access, auth, features, qc_overrides
    from dashboard import qc_overrides_ui


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_by TEXT)")
    conn.execute("CREATE TABLE users (email TEXT PRIMARY KEY, name TEXT, role TEXT NOT NULL, perms TEXT NOT NULL DEFAULT '[]', active INTEGER NOT NULL DEFAULT 1)")
    conn.execute("CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, email TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL)")
    conn.execute("CREATE TABLE project_watchers (project_id INTEGER, email TEXT, level TEXT, PRIMARY KEY(project_id,email))")
    conn.execute("INSERT INTO projects(id,name,created_by) VALUES (1,'fixture','owner@example.test')")
    conn.execute("INSERT INTO users(email,role,active) VALUES ('owner@example.test','owner',1),('editor@example.test','member',1),('viewer@example.test','member',1)")
    conn.execute("INSERT INTO project_watchers(project_id,email,level) VALUES (1,'editor@example.test','edit'),(1,'viewer@example.test','view')")
    _add_session(conn, "session-fixture-editor", "editor@example.test")
    conn.commit()
    return conn


def _add_session(conn, token, email, *, expires_at=None):
    created_at = auth._now()
    conn.execute(
        "INSERT INTO sessions(token_hash,email,created_at,expires_at) VALUES (?,?,?,?)",
        (auth._hash(token), email, created_at, expires_at if expires_at is not None else created_at + 3600),
    )


def _write(conn, session_token="session-fixture-editor", *, reason="Đã xem lại bằng chứng và xác nhận ngoại lệ phù hợp.", evidence=None):
    return qc_overrides.record(
        conn,
        project_id=1,
        target_kind="finding",
        target_ref="qc:run-1:finding-3",
        error_code="QC-L13-CONTINUITY",
        session_token=session_token,
        reason=reason,
        evidence=evidence if evidence is not None else {"type": "manual_review", "ref": "fixture/frame-3.png", "sha256": "a" * 64},
    )


def test_migration_is_explicit_and_idempotent_for_new_and_legacy_schemas():
    conn = _conn()
    assert not qc_overrides.has_table(conn)
    assert qc_overrides.migrate_up(conn) is True
    first_schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='overrides'").fetchone()[0]
    assert qc_overrides.migrate_up(conn) is False
    assert conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='overrides'").fetchone()[0] == first_schema
    assert qc_overrides.has_table(conn)

    legacy = _conn()
    legacy.execute("CREATE TABLE existing_legacy_row (id INTEGER PRIMARY KEY, value TEXT)")
    legacy.commit()
    assert qc_overrides.migrate_up(legacy) is True
    assert legacy.execute("SELECT COUNT(*) FROM existing_legacy_row").fetchone()[0] == 0
    assert qc_overrides.migrate_up(legacy) is False


def test_migration_failure_rolls_back_partial_schema():
    conn = _conn()
    conn.execute("CREATE TABLE overrides (id INTEGER PRIMARY KEY)")
    conn.commit()
    with pytest.raises(ValueError):
        qc_overrides.migrate_up(conn)
    assert not conn.in_transaction
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_overrides_%'").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("ddl", "message"),
    [
        (qc_overrides.DDL.replace(" REFERENCES projects(id) ON DELETE RESTRICT", ""), "khóa ngoại"),
        (qc_overrides.DDL.replace(
            ",\n    UNIQUE (project_id, target_kind, target_ref, revision)", ""), "UNIQUE"),
        (qc_overrides.DDL.replace("revision INTEGER NOT NULL CHECK (revision >= 1)", "revision INTEGER NOT NULL"), "CHECK"),
    ],
)
def test_migration_rejects_same_name_schema_missing_constraints(ddl, message):
    conn = _conn()
    conn.execute(ddl)
    conn.commit()
    with pytest.raises(ValueError, match=message):
        qc_overrides.migrate_up(conn)
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_overrides_%'").fetchone()[0] == 0


def test_schema_restricts_project_reference():
    conn = _conn()
    qc_overrides.migrate_up(conn)
    fk = conn.execute("PRAGMA foreign_key_list(overrides)").fetchall()
    assert any(row["table"] == "projects" and row["from"] == "project_id" for row in fk)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO overrides(project_id,target_kind,target_ref,error_code,actor_email,revision,reason,evidence_json,created_at) "
            "VALUES (999,'finding','ref','E1','editor@example.test',1,'Đã xem lại bằng chứng có liên quan.','{}','2026-01-01T00:00:00Z')"
        )


def test_migration_down_requires_explicit_force_when_history_exists(monkeypatch):
    conn = _conn()
    qc_overrides.migrate_up(conn)
    conn.commit()
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    _write(conn)
    with pytest.raises(ValueError):
        qc_overrides.migrate_down(conn)
    assert qc_overrides.has_table(conn)
    qc_overrides.migrate_down(conn, force=True)
    assert not qc_overrides.has_table(conn)


def test_flag_is_off_by_default(monkeypatch):
    assert features.FEATURES[qc_overrides.FLAG]["verified"] is False
    assert features.FEATURES[qc_overrides.FLAG].get("default_on") is not True
    monkeypatch.setattr(features, "settings", lambda: {"modes": {}, "flags": {}, "preset": "custom"})
    with mock.patch.object(os, "environ", {}):
        assert not qc_overrides.enabled()


def test_record_is_flagged_off_and_does_not_migrate_or_write(monkeypatch):
    conn = _conn()
    monkeypatch.setattr(qc_overrides, "enabled", lambda: False)
    with pytest.raises(qc_overrides.OverrideDisabled):
        _write(conn)
    assert not qc_overrides.has_table(conn)


def test_record_requires_a_human_editor_and_a_meaningful_reason_and_evidence(monkeypatch):
    conn = _conn()
    qc_overrides.migrate_up(conn)
    conn.commit()
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    for token in (None, "not-a-session", {"email": "editor@example.test", "role": "owner"}, "session-fixture-viewer"):
        with pytest.raises(access.AccessDenied):
            _write(conn, token)
    _add_session(conn, "session-fixture-viewer", "viewer@example.test")
    conn.commit()
    with pytest.raises(access.AccessDenied):
        _write(conn, "session-fixture-viewer")
    _add_session(conn, "session-fixture-expired", "editor@example.test", expires_at=auth._now() - 1)
    conn.commit()
    with pytest.raises(access.AccessDenied):
        _write(conn, "session-fixture-expired")
    with pytest.raises(TypeError):
        qc_overrides.record(
            conn, project_id=1, target_kind="finding", target_ref="r", error_code="E1",
            actor={"email": "editor@example.test", "role": "owner"}, reason="Đã xem lại bằng chứng hợp lệ.",
            evidence={"type": "fixture"},
        )
    conn.execute("UPDATE users SET active=0 WHERE email='editor@example.test'")
    conn.commit()
    with pytest.raises(access.AccessDenied):
        _write(conn)
    with pytest.raises(ValueError):
        _write(conn, reason="bỏ qua lỗi này")
    with pytest.raises(ValueError):
        _write(conn, evidence={})
    with pytest.raises(ValueError):
        _write(conn, evidence={"note": "x" * 17_000})
    assert conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0] == 0


def test_record_appends_revision_without_overwriting_prior_decision(monkeypatch):
    conn = _conn()
    qc_overrides.migrate_up(conn)
    conn.commit()
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    first = _write(conn)
    second = _write(conn, reason="Đã đối chiếu thêm khung hình và vẫn chấp nhận ngoại lệ.")
    assert (first["revision"], second["revision"]) == (1, 2)
    rows = conn.execute("SELECT revision, actor_email, reason, evidence_json FROM overrides ORDER BY revision").fetchall()
    assert len(rows) == 2
    assert rows[0]["actor_email"] == "editor@example.test"
    assert json.loads(rows[0]["evidence_json"])["sha256"] == "a" * 64
    assert qc_overrides.latest(conn, 1, "finding", "qc:run-1:finding-3")["revision"] == 2


def test_record_refuses_caller_transaction_with_stale_snapshot(monkeypatch):
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    conn = _conn()
    qc_overrides.migrate_up(conn)
    conn.commit()
    conn.execute("BEGIN")
    conn.execute("SELECT revision FROM overrides WHERE project_id=1").fetchall()
    with pytest.raises(qc_overrides.OverrideConflict, match="giao dịch hiện tại"):
        _write(conn)
    assert conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0] == 0
    conn.rollback()


def test_parallel_writers_serialize_revisions(tmp_path, monkeypatch):
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    setup = _conn()
    qc_overrides.migrate_up(setup)
    setup.commit()
    db_path = tmp_path / "overrides-concurrent.sqlite"
    disk = sqlite3.connect(db_path)
    setup.backup(disk)
    disk.close()
    setup.close()
    barrier = Barrier(2)

    def write_once():
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            barrier.wait(timeout=3)
            return ("ok", _write(conn))
        except Exception as exc:  # Chỉ giữ thông báo đã giới hạn, không in môi trường hay payload.
            return ("error", type(exc).__name__, str(exc)[:160])
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(lambda _n: write_once(), range(2)))
    assert all(result[0] == "ok" for result in rows), rows
    assert sorted(result[1]["revision"] for result in rows) == [1, 2]


def test_busy_begin_is_reported_as_override_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    setup = _conn()
    qc_overrides.migrate_up(setup)
    setup.commit()
    db_path = tmp_path / "overrides-locked.sqlite"
    disk = sqlite3.connect(db_path)
    setup.backup(disk)
    disk.close()
    setup.close()
    locker = sqlite3.connect(db_path, timeout=1)
    writer = sqlite3.connect(db_path, timeout=0)
    writer.row_factory = sqlite3.Row
    try:
        locker.execute("BEGIN IMMEDIATE")
        with pytest.raises(qc_overrides.OverrideConflict):
            _write(writer)
        assert not writer.in_transaction
    finally:
        locker.rollback()
        locker.close()
        writer.close()


def test_failed_commit_rolls_back_owned_transaction(monkeypatch):
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    conn = _conn()
    qc_overrides.migrate_up(conn)
    conn.commit()

    class CommitFailure:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def commit(self):
            raise sqlite3.OperationalError("fixture commit failure")

    with pytest.raises(sqlite3.OperationalError, match="fixture commit failure"):
        _write(CommitFailure(conn))
    assert not conn.in_transaction
    assert conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0] == 0


class _FakeStreamlit:
    def __init__(self, *, values=None, submit=False):
        self.values = values or {}
        self.submit = submit
        self.messages = []

    def expander(self, *args, **kwargs):
        return _NullContext()

    def form(self, *args, **kwargs):
        return _NullContext()

    def text_area(self, label, *, key, value="", **kwargs):
        return self.values.get(key, value)

    def form_submit_button(self, *args, **kwargs):
        return self.submit

    def __getattr__(self, name):
        if name in {"caption", "info", "error", "success", "write", "json", "rerun"}:
            return lambda *args, **kwargs: self.messages.append((name, args))
        raise AttributeError(name)


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_override_ui_flag_off_does_not_read_project_or_render(monkeypatch):
    class NoDatabase:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("cờ tắt không được đọc CSDL")

    fake = _FakeStreamlit()
    monkeypatch.setattr(qc_overrides_ui, "st", fake)
    monkeypatch.setattr(qc_overrides_ui.qc_overrides, "enabled", lambda: False)
    qc_overrides_ui.render_override(
        NoDatabase(), project_id=1, target_kind="finding", target_ref="fixture:f1",
        error_code="QC-1", session_token=None,
    )
    assert fake.messages == []


def test_override_ui_records_authenticated_editor_revision(monkeypatch):
    conn = _conn()
    qc_overrides.migrate_up(conn)
    conn.commit()
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    monkeypatch.setattr(qc_overrides_ui, "_widget_key", lambda *_args: "fixture-key")
    fake = _FakeStreamlit(values={
        "fixture-key_reason": "Đã xem lại khung hình và chấp nhận cảnh báo này.",
        "fixture-key_evidence": '{"type":"manual_review","ref":"fixture/frame-3.png"}',
    }, submit=True)
    monkeypatch.setattr(qc_overrides_ui, "st", fake)
    qc_overrides_ui.render_override(
        conn, project_id=1, target_kind="finding", target_ref="qc:run-1:finding-3",
        error_code="QC-L13-CONTINUITY", session_token="session-fixture-editor",
    )
    saved = qc_overrides.latest(conn, 1, "finding", "qc:run-1:finding-3")
    assert saved["revision"] == 1
    assert saved["actor_email"] == "editor@example.test"
    assert saved["evidence"] == {"type": "manual_review", "ref": "fixture/frame-3.png"}
    assert any(message[0] == "success" for message in fake.messages)


def test_override_ui_rejects_invalid_json_without_writing(monkeypatch):
    conn = _conn()
    qc_overrides.migrate_up(conn)
    conn.commit()
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    fake = _FakeStreamlit(submit=True)
    monkeypatch.setattr(qc_overrides_ui, "st", fake)
    monkeypatch.setattr(qc_overrides_ui, "_widget_key", lambda *_args: "fixture-key")
    fake.values = {
        "fixture-key_reason": "Đã xem lại khung hình và chấp nhận cảnh báo này.",
        "fixture-key_evidence": "not-json",
    }
    qc_overrides_ui.render_override(
        conn, project_id=1, target_kind="finding", target_ref="qc:run-1:finding-3",
        error_code="QC-L13-CONTINUITY", session_token="session-fixture-editor",
    )
    assert qc_overrides.latest(conn, 1, "finding", "qc:run-1:finding-3") is None
    assert any(message[0] == "error" for message in fake.messages)


def test_override_ui_viewer_cannot_write(monkeypatch):
    conn = _conn()
    qc_overrides.migrate_up(conn)
    _add_session(conn, "session-fixture-viewer", "viewer@example.test")
    conn.commit()
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    fake = _FakeStreamlit(submit=True)
    monkeypatch.setattr(qc_overrides_ui, "st", fake)
    qc_overrides_ui.render_override(
        conn, project_id=1, target_kind="finding", target_ref="qc:run-1:finding-3",
        error_code="QC-L13-CONTINUITY", session_token="session-fixture-viewer", read_only=True,
    )
    assert qc_overrides.latest(conn, 1, "finding", "qc:run-1:finding-3") is None
    assert not any(message[0] == "success" for message in fake.messages)

