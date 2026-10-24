"""CX24-M610: dashboard phiếu lỗi theo vai, AppTest chỉ dùng dữ liệu tổng hợp."""
import hashlib
import json
from pathlib import Path

import pytest
from core import handoff
from core.db import connect
from core.pipeline import Pipeline
from streamlit.testing.v1 import AppTest


REGISTRY = {
    "fallback_owner": "director",
    "roles": [
        {"id": "director", "name": "Director", "owns_errors": {"codes": []}, "writes": []},
        {"id": "storyboard_artist", "name": "Storyboard Artist",
         "owns_errors": {"codes": ["QC-IMAGE-*"]}, "writes": ["image_prompt"]},
        {"id": "video_prompt_artist", "name": "Video Prompt Artist",
         "owns_errors": {"codes": ["QC-MOTION-*"]}, "writes": ["motion_prompt"]},
    ],
    "fields": {"blocked_field": {"owner": "storyboard_artist"}},
    "layer_fields": {"image_review": "blocked_field"},
}


def _args(data_dir, project_id, scene_id, shot_no, handoff_id, role, status, qc_code, layer=None):
    digest = hashlib.sha256(f"fixture-{handoff_id}".encode()).hexdigest()
    evidence = {"id": qc_code, "status": status, "path": f"projects/{project_id}/qc/{qc_code}.json"}
    if layer:
        evidence["layer"] = layer
    return {
        "data_dir": str(data_dir), "project_id": project_id, "scene_id": scene_id,
        "shot_no": shot_no, "from_role": "director", "to_role": role,
        "revision": {"scene_rev": 1, "byd_v": 1, "fields": {"image_prompt": 1}},
        "dependencies": [{"kind": "byd", "revision": 1}],
        "products": [{"path": f"projects/{project_id}/shot-{shot_no}.png", "sha256": digest}],
        "qc_evidence": [evidence],
        "approval_state": status, "handoff_id": handoff_id, "at": "2026-10-25T00:00:00+00:00",
    }


def _page(db_path, pid, data_dir, user):
    import streamlit as st

    from core.access import AccessDenied
    from core.db import connect
    from core.pipeline import Pipeline
    from dashboard.team_screen import error_tickets_panel

    p = Pipeline(connect(db_path))
    p.user = user
    try:
        error_tickets_panel(p, pid, data_dir=data_dir)
    except AccessDenied as exc:
        st.error(f"🔒 {exc}")
    finally:
        p.conn.close()


def _project(tmp_path, user=None):
    db_path = str(tmp_path / "tickets.sqlite")
    p = Pipeline(connect(db_path))
    pid = p.create_project("Dự án fixture", created_by="owner@example.test")
    if user and user.get("email") == "ep@example.test":
        p.conn.execute(
            "INSERT INTO project_executive_producers (project_id, email, added_by, added_at) VALUES (?,?,?,?)",
            (pid, user["email"], "owner@example.test", "fixture"),
        )
    elif user and user.get("email") in ("viewer@example.test", "editor@example.test"):
        p.conn.execute(
            "INSERT INTO project_watchers (project_id, email, level, added_by, added_at) VALUES (?,?,?,?,?)",
            (pid, user["email"], "edit" if user["email"] == "editor@example.test" else "view", "owner@example.test", "fixture"),
        )
    p.conn.commit()
    p.conn.close()
    return db_path, pid


def _enable_fixture_flags(monkeypatch, tmp_path):
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(tmp_path / "feature-settings.json"))
    monkeypatch.setenv("FEATURE_CREW_ERROR_TICKETS", "1")
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "1")
    monkeypatch.setenv("FEATURE_CREW_REGISTRY", "1")


def _seed(data_dir, pid):
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    handoff.record(**_args(data_dir, pid, 7, 3, "ticket-image", "storyboard_artist", "pending", "QC-IMAGE-1", "image_review"))
    handoff.record(**_args(data_dir, pid, 8, 4, "ticket-motion", "video_prompt_artist", "review", "QC-MOTION-2"))
    handoff.record(**_args(data_dir, pid, 9, 5, "ticket-fallback", "director", "escalated", "QC-UNMAPPED"))
    generic = _args(data_dir, pid, 10, 6, "handoff-without-qc", "director", "approved", "not-a-ticket")
    generic["qc_evidence"] = []
    handoff.record(**generic)


def test_list_for_project_returns_latest_row_per_handoff_id(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CREW_HANDOFF_SHADOW", "1")
    data_dir = tmp_path / "data"
    first = _args(data_dir, 24, 7, 3, "ticket-a", "storyboard_artist", "pending", "QC-IMAGE-1")
    handoff.record(**first, reason="Phân công đầu tiên")
    handoff.record(**{**first, "to_role": "video_prompt_artist", "at": "2026-10-25T00:05:00+00:00"},
                   reason="Chuyển do cần rà prompt")

    rows = handoff.list_for_project(str(data_dir), 24)

    assert len(rows) == 1
    assert rows[0]["to_role"] == "video_prompt_artist"
    assert rows[0]["reason"] == "Chuyển do cần rà prompt"


def test_ticket_panel_filters_by_role_shot_and_status(tmp_path, monkeypatch):
    _enable_fixture_flags(monkeypatch, tmp_path)
    from core import crew

    monkeypatch.setattr(crew, "load", lambda: REGISTRY)
    db_path, pid = _project(tmp_path, {"email": "ep@example.test", "role": "member"})
    data_dir = str(tmp_path / "shadow")
    _seed(data_dir, pid)

    at = AppTest.from_function(_page, args=(db_path, pid, data_dir, {"email": "ep@example.test", "role": "member"})).run()
    assert not at.exception, at.exception
    assert len(at.dataframe) == 1
    assert len(at.dataframe[0].value) == 3
    rows = at.dataframe[0].value
    image = rows.loc[rows["Mã QC"] == "QC-IMAGE-1"].iloc[0]
    fallback = rows.loc[rows["Mã QC"] == "QC-UNMAPPED"].iloc[0]
    assert image["owner_cannot_fix"] == "Có"
    assert "fallback Director" in fallback["Vai chủ"]
    assert fallback["owner_cannot_fix"] == "Chưa rõ"

    at.selectbox(key="m610_filter_role").set_value("video_prompt_artist")
    at.selectbox(key="m610_filter_shot").set_value(4)
    at.selectbox(key="m610_filter_status").set_value("review").run()

    rows = at.dataframe[0].value
    assert len(rows) == 1
    assert rows.iloc[0]["Mã QC"] == "QC-MOTION-2"
    assert rows.iloc[0]["Vai chủ"] == "Video Prompt Artist"


def test_ticket_transfer_requires_reason_and_appends_via_handoff(tmp_path, monkeypatch):
    _enable_fixture_flags(monkeypatch, tmp_path)
    from core import crew

    monkeypatch.setattr(crew, "load", lambda: REGISTRY)
    db_path, pid = _project(tmp_path, {"email": "ep@example.test", "role": "member"})
    data_dir = str(tmp_path / "shadow")
    _seed(data_dir, pid)

    at = AppTest.from_function(_page, args=(db_path, pid, data_dir, {"email": "ep@example.test", "role": "member"})).run()
    transfer = next(button for button in at.button if button.key == "m610_transfer_ticket-image")
    assert transfer.disabled

    at.text_area(key="m610_reason_ticket-image").set_value("Cần chuyển cho vai xử lý prompt").run()
    at.selectbox(key="m610_assign_ticket-image").set_value("video_prompt_artist").run()
    next(button for button in at.button if button.key == "m610_transfer_ticket-image").click().run()
    assert not at.exception, at.exception
    row = next(row for row in handoff.list_for_project(data_dir, pid) if row["handoff_id"] == "ticket-image")
    assert row["to_role"] == "video_prompt_artist"
    assert row["reason"] == "Cần chuyển cho vai xử lý prompt"


def test_ticket_transfer_denied_without_project_edit_right(tmp_path, monkeypatch):
    _enable_fixture_flags(monkeypatch, tmp_path)
    from core import crew

    monkeypatch.setattr(crew, "load", lambda: REGISTRY)
    db_path, pid = _project(tmp_path, {"email": "viewer@example.test", "role": "member"})
    data_dir = str(tmp_path / "shadow")
    _seed(data_dir, pid)

    at = AppTest.from_function(_page, args=(db_path, pid, data_dir, {"email": "viewer@example.test", "role": "member"})).run()
    at.text_area(key="m610_reason_ticket-image").set_value("Thử chuyển trái quyền").run()
    at.selectbox(key="m610_assign_ticket-image").set_value("video_prompt_artist").run()
    next(button for button in at.button if button.key == "m610_transfer_ticket-image").click().run()

    assert not at.exception, at.exception
    assert any("chỉ được XEM" in item.value for item in at.error)
    row = next(row for row in handoff.list_for_project(data_dir, pid) if row["handoff_id"] == "ticket-image")
    assert row["to_role"] == "storyboard_artist"


def test_non_ep_editor_and_unknown_target_role_are_denied(tmp_path, monkeypatch):
    _enable_fixture_flags(monkeypatch, tmp_path)
    from core import access, crew
    from dashboard.team_screen import _transfer_ticket

    monkeypatch.setattr(crew, "load", lambda: REGISTRY)
    db_path, pid = _project(tmp_path, {"email": "editor@example.test", "role": "member"})
    data_dir = str(tmp_path / "shadow")
    _seed(data_dir, pid)
    p = Pipeline(connect(db_path))
    p.user = {"email": "editor@example.test", "role": "member"}
    ticket = {"record": next(row for row in handoff.list_for_project(data_dir, pid) if row["handoff_id"] == "ticket-image")}

    assert access.level(p.conn, pid, p.user) == "edit"
    with pytest.raises(access.AccessDenied, match="Executive Producer"):
        _transfer_ticket(p, pid, ticket, "video_prompt_artist", "Có lý do", data_dir, REGISTRY)
    assert ticket["record"]["to_role"] == "storyboard_artist"
    p.conn.close()

    ep_tmp = tmp_path / "ep"
    ep_tmp.mkdir()
    db_path, pid = _project(ep_tmp, {"email": "ep@example.test", "role": "member"})
    data_dir = str(ep_tmp / "shadow")
    _seed(data_dir, pid)
    p = Pipeline(connect(db_path))
    p.user = {"email": "ep@example.test", "role": "member"}
    ticket = {"record": next(row for row in handoff.list_for_project(data_dir, pid) if row["handoff_id"] == "ticket-image")}
    from core.handoff import HandoffInputError

    with pytest.raises(HandoffInputError, match="Role Registry"):
        _transfer_ticket(p, pid, ticket, "unknown_role", "Có lý do", data_dir, REGISTRY)
    p.conn.close()


def test_flag_off_keeps_old_team_screen_without_ticket_io(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(tmp_path / "feature-settings.json"))
    monkeypatch.setenv("FEATURE_CREW_ERROR_TICKETS", "0")
    from core import handoff

    monkeypatch.setattr(handoff, "list_for_project", lambda *_args: (_ for _ in ()).throw(AssertionError("không được đọc JSONL")), raising=False)
    db_path, pid = _project(tmp_path)
    data_dir = str(tmp_path / "shadow")

    at = AppTest.from_function(_page, args=(db_path, pid, data_dir, None)).run()

    assert not at.exception, at.exception
    assert not any("Phiếu lỗi theo vai" in (item.value or "") for item in at.markdown)


def test_m610_flag_stays_off_in_experimental_preset_until_explicit_opt_in(tmp_path, monkeypatch):
    settings = tmp_path / "feature-settings.json"
    settings.write_text(json.dumps({"preset": "experimental", "flags": {}}), encoding="utf-8")
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(settings))
    monkeypatch.delenv("FEATURE_CREW_ERROR_TICKETS", raising=False)
    from core import features

    assert features.on("crew_error_tickets") is False
    monkeypatch.setenv("FEATURE_CREW_ERROR_TICKETS", "1")
    assert features.on("crew_error_tickets") is True


def test_ep_project_membership_opens_ticket_screen_route(tmp_path, monkeypatch):
    _enable_fixture_flags(monkeypatch, tmp_path)
    db_path, pid = _project(tmp_path, {"email": "ep@example.test", "role": "member"})
    from dashboard.team_screen import ticket_screen_visible

    p = Pipeline(connect(db_path))
    p.user = {"email": "ep@example.test", "role": "member"}
    assert ticket_screen_visible(p, pid) is True
    p.user = {"email": "viewer@example.test", "role": "member"}
    assert ticket_screen_visible(p, pid) is False
    p.conn.close()


def test_panel_resolves_dashboard_relative_data_root_to_absolute_fixture(tmp_path, monkeypatch):
    _enable_fixture_flags(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    from core import crew
    from dashboard import common

    monkeypatch.setattr(crew, "load", lambda: REGISTRY)
    monkeypatch.setattr(common, "DATA", "shadow")
    db_path, pid = _project(tmp_path, {"email": "ep@example.test", "role": "member"})
    data_dir = str(tmp_path / "shadow")
    _seed(data_dir, pid)

    at = AppTest.from_function(_page, args=(db_path, pid, None, {"email": "ep@example.test", "role": "member"})).run()

    assert not at.exception, at.exception
    assert len(at.dataframe[0].value) == 3
