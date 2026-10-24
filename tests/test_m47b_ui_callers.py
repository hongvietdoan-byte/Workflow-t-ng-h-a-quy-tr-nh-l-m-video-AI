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
    ui.render_findings(_conn(), 1, 7, result, session_token="session-fixture-editor",
                       continuity_snapshot={"project_id": 1, "qc_version": "fixture-v1", "at": "fixture-run", "expected": [finding]})
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


def _override_app():
    import sqlite3
    import streamlit as st
    from unittest import mock
    from core import qc_overrides
    from dashboard import qc_overrides_ui
    from tests.test_v31_m47b_overrides import _conn
    if "fixture_conn" not in st.session_state:
        source = _conn()
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        source.backup(conn)
        source.close()
        qc_overrides.migrate_up(conn)
        conn.commit()
        st.session_state.fixture_conn = conn
    with mock.patch.object(qc_overrides, "enabled", lambda: True):
        qc_overrides_ui.render_override(st.session_state.fixture_conn, project_id=1, target_kind="finding", target_ref="fixture:f1", error_code="QC1", session_token="session-fixture-editor")
    st.caption("fixture_count=" + str(st.session_state.fixture_conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0]))


def test_apptest_form_can_submit_first_reason_and_evidence(tmp_path):
    from streamlit.testing.v1 import AppTest
    fake = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path), "DASHBOARD_OWNER_EMAIL": "owner@example.test", "FEATURE_SETTINGS_FILE": str(tmp_path / "flags.json"), "FEATURE_BASELINE_FILE": ""}
    with mock.patch.object(os, "environ", fake):
        at = AppTest.from_function(_override_app).run()
        assert not at.exception
        assert not at.button[0].disabled
        at.text_area[0].set_value("Đã kiểm lại bằng chứng và chấp nhận ngoại lệ này.")
        at.text_area[1].set_value('{"ref":"fixture/frame.png"}')
        at.button[0].click().run()
        assert not at.exception
        assert any(c.value == "fixture_count=1" for c in at.caption)


def test_apptest_invalid_reason_and_empty_evidence_do_not_write(tmp_path):
    from streamlit.testing.v1 import AppTest
    fake = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path), "DASHBOARD_OWNER_EMAIL": "owner@example.test", "FEATURE_SETTINGS_FILE": str(tmp_path / "flags.json"), "FEATURE_BASELINE_FILE": ""}
    with mock.patch.object(os, "environ", fake):
        at = AppTest.from_function(_override_app).run()
        at.text_area[0].set_value("ngắn")
        at.text_area[1].set_value('{"ref":"fixture/frame.png"}')
        at.button[0].click().run()
        assert not at.exception and bool(at.error)
        assert any(c.value == "fixture_count=0" for c in at.caption)
        at.text_area[0].set_value("Đã kiểm lại bằng chứng và chấp nhận ngoại lệ này.")
        at.text_area[1].set_value('{}')
        at.button[0].click().run()
        assert not at.exception and bool(at.error)
        assert any(c.value == "fixture_count=0" for c in at.caption)


def test_revoked_identity_rejected_before_any_finding_is_rendered(monkeypatch):
    conn = _conn()
    conn.execute("UPDATE users SET active=0 WHERE email='editor@example.test'")
    conn.commit()
    fake = mock.Mock()
    monkeypatch.setattr(ui, "st", fake)
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    ui.render_findings(conn, 1, 7, {"continuity": [{"qc_code": "QC1"}]}, session_token="session-fixture-editor")
    assert not fake.mock_calls


def test_finding_annotation_never_reuses_another_jobs_target(monkeypatch):
    conn = _conn()
    calls = []
    monkeypatch.setattr(ui, "st", mock.Mock())
    monkeypatch.setattr(ui, "render_override", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    result = {"evidence": [{"qc_run_id": "run1", "findings": [{"qc_code": "QC1", "evidence": {"frame": 1}}]}]}
    ui.render_findings(conn, 1, 7, result, session_token="session-fixture-editor")
    ui.render_findings(conn, 1, 8, result, session_token="session-fixture-editor")
    assert len(calls) == 2 and calls[0]["target_ref"] != calls[1]["target_ref"]


def test_existing_package_card_passes_exact_snapshot_to_override(monkeypatch):
    from dashboard import send_preview_ui as card
    from types import SimpleNamespace
    fake = mock.MagicMock()
    package = {"model": "fixture-model", "prompt": "fixture-only", "params": {}}
    fake.session_state = {"auth_token": "fixture-session", "sendpv_7": {"ok": True, "package": package, "refs": [], "notes": [], "price": None}}
    fake.button.return_value = False
    monkeypatch.setattr(card, "st", fake)
    monkeypatch.setattr(card.send_preview, "enabled", lambda: True)
    monkeypatch.setattr(card.send_preview, "shadow_cached", lambda *a: {"video": [], "continuity": [], "can_xem": [], "evidence": [], "notes": []})
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    calls = []
    ledgers = []
    monkeypatch.setattr(ui, "render_override", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(ui, "render_findings", lambda *a, **kw: ledgers.append((a, kw)))
    card.card_block(SimpleNamespace(conn=object()), 1, {"id": 7}, SimpleNamespace(data_dir="fixture"))
    assert len(calls) == 1
    assert calls[0]["target_ref"] == ui.target_ref("package", {"job": 7, "package": package})
    assert calls[0]["session_token"] == "fixture-session"
    assert len(ledgers) == 1 and ledgers[0][0][2] == 7


def _project_app():
    import json
    import sqlite3
    import streamlit as st
    from unittest import mock
    from dashboard import qc_overrides_ui
    from core import qc_overrides
    from tests.test_v31_m47b_overrides import _anchor_conn, _byd2
    if "fixture_conn" not in st.session_state:
        source = _anchor_conn([(1, "Kelly", False)], [(1, 1, _byd2(("Kelly", "chinh")))])
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        source.backup(conn)
        source.close()
        qc_overrides.migrate_up(conn)
        conn.commit()
        st.session_state.fixture_conn = conn
    with mock.patch.object(qc_overrides, "enabled", lambda: True):
        qc_overrides_ui.render_project(st.session_state.fixture_conn, 1, session_token="session-fixture-editor")


def test_project_byd_view_stays_open_on_form_rerun_and_q6c_is_review(tmp_path):
    from streamlit.testing.v1 import AppTest
    fake = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path), "DASHBOARD_OWNER_EMAIL": "owner@example.test", "FEATURE_SETTINGS_FILE": str(tmp_path / "flags.json"), "FEATURE_BASELINE_FILE": ""}
    with mock.patch.object(os, "environ", fake):
        at = AppTest.from_function(_project_app).run()
        assert not at.exception
        assert any("REVIEW Q6(c)" in item.value for item in at.warning)
        opener = next(button for button in at.button if button.label == "Mở BYĐ hiện tại")
        opener.click().run()
        assert not at.exception and bool(at.json)
        # A submit rerun keeps the selected BYĐ form mounted rather than disappearing.
        buttons = [button for button in at.button if button.label == "Ghi ngoại lệ"]
        buttons[-1].click().run()
        assert not at.exception and bool(at.json)
        assert bool(at.error)  # missing reason/evidence is rejected rather than recorded.


def _continuity_targets(monkeypatch, snapshot):
    conn = _conn()
    calls = []
    monkeypatch.setattr(ui, "st", mock.Mock())
    monkeypatch.setattr(ui, "render_override", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(qc_overrides, "enabled", lambda: True)
    finding = {"qc_code": "QC1", "severity": "REVIEW", "evidence": {"shots": [1]}}
    if snapshot is not None:
        snapshot = {"project_id": 1, "qc_version": "fixture-v1", **snapshot}
    ui.render_findings(conn, 1, 7, {"continuity": [finding]}, session_token="session-fixture-editor", continuity_snapshot=snapshot)
    return [call["target_ref"] for call in calls]


def test_continuity_new_snapshot_does_not_reuse_old_override(monkeypatch):
    finding = {"qc_code": "QC1", "severity": "REVIEW", "evidence": {"shots": [1]}}
    first = _continuity_targets(monkeypatch, {"at": "fixture-run1", "expected": [finding]})
    second = _continuity_targets(monkeypatch, {"at": "fixture-run2", "expected": [finding]})
    assert len(first) == len(second) == 1 and first != second


def test_continuity_same_snapshot_has_stable_identity(monkeypatch):
    finding = {"qc_code": "QC1", "severity": "REVIEW", "evidence": {"shots": [1]}}
    snapshot = {"at": "fixture-run1", "expected": [finding]}
    assert _continuity_targets(monkeypatch, snapshot) == _continuity_targets(monkeypatch, dict(snapshot))


def test_continuity_expected_observed_are_separate_targets(monkeypatch):
    finding = {"qc_code": "QC1", "severity": "REVIEW", "evidence": {"shots": [1]}}
    targets = _continuity_targets(monkeypatch, {"at": "fixture-run1", "expected": [finding], "observed": [finding]})
    assert len(targets) == len(set(targets)) == 2


def test_continuity_without_source_provenance_is_view_only(monkeypatch):
    assert _continuity_targets(monkeypatch, None) == []


def test_continuity_wrong_project_or_missing_run_is_view_only(monkeypatch):
    finding = {"qc_code": "QC1", "severity": "REVIEW", "evidence": {"shots": [1]}}
    assert _continuity_targets(monkeypatch, {"project_id": 2, "at": "fixture-run", "expected": [finding]}) == []
    assert _continuity_targets(monkeypatch, {"expected": [finding]}) == []
