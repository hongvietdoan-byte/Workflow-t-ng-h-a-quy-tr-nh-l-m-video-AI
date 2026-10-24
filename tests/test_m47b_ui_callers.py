"""Codex 1: callers M47B, dữ liệu và phiên hoàn toàn giả."""
import json
import os
from unittest import mock

with mock.patch.object(os, "environ", {"DASHBOARD_OWNER_EMAIL": "owner@example.test"}):
    from dashboard import qc_overrides_ui as ui
    from core import qc_overrides
    from tests.test_v31_m47b_overrides import _conn, _add_session, _FakeStreamlit


def test_viewer_has_no_edit_form_even_if_caller_omits_read_only(monkeypatch):
    conn = _conn()
    qc_overrides.migrate_up(conn)
    _add_session(conn, "fixture-viewer", "viewer@example.test")
    conn.commit()
    fake = _FakeStreamlit()
    fake.form = mock.Mock(side_effect=AssertionError("viewer must not have form"))
    monkeypatch.setattr(ui, "st", fake)
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    ui.render_override(conn, project_id=1, target_kind="finding", target_ref="f1", error_code="QC1", session_token="fixture-viewer")
    assert not fake.form.called


def test_target_fingerprint_is_canonical_and_revision_exact():
    first = ui.target_ref("finding", {"run": "r1", "finding": {"code": "QC1", "sha": "a"}})
    assert first == ui.target_ref("finding", {"finding": {"sha": "a", "code": "QC1"}, "run": "r1"})
    assert first != ui.target_ref("finding", {"run": "r2", "finding": {"code": "QC1", "sha": "a"}})
    assert first != ui.target_ref("finding", {"run": "r1", "finding": {"code": "QC1", "sha": "b"}})
    assert len(first) <= 200


def test_shadow_ledger_binds_source_run_finding_and_job(monkeypatch):
    calls = []
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    monkeypatch.setattr(ui, "render_override", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(ui, "st", mock.Mock())
    finding = {"qc_code": "QC1", "severity": "REVIEW", "why": "fixture"}
    result = {"video": [{"at": "fixture1", "findings": [finding]}], "evidence": [{"qc_run_id": "run1", "findings": [finding]}], "continuity": [finding]}
    ui.render_findings(None, 1, 7, result, session_token="fixture")
    assert len(calls) == 3
    assert len({c["target_ref"] for c in calls}) == 3
    assert all(c["error_code"] == "QC1" for c in calls)


def test_findings_and_project_off_do_not_touch_db_or_ui(monkeypatch):
    monkeypatch.setattr(qc_overrides, "enabled", lambda: False)
    fake = mock.Mock()
    monkeypatch.setattr(ui, "st", fake)
    ui.render_project(object(), 1, session_token=None)
    ui.render_findings(object(), 1, 9, {}, session_token=None)
    assert not fake.mock_calls


def test_image_force_is_held_when_no_safe_package_preview(monkeypatch):
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    fake = mock.Mock()
    monkeypatch.setattr(ui, "st", fake)
    assert ui.image_force_hold() is True
    assert fake.caption.called


def test_image_force_off_retains_legacy_no_render(monkeypatch):
    monkeypatch.setattr(qc_overrides, "enabled", lambda: False)
    fake = mock.Mock()
    monkeypatch.setattr(ui, "st", fake)
    assert ui.image_force_hold() is False
    assert not fake.mock_calls
