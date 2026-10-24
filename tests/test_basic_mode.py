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
        with patch.object(simple_budget, "proposal", return_value={"total": 10.0, "incomplete": False, "qd3_complete": True}), \
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


def _ui_fixture():
    from types import SimpleNamespace
    import streamlit as st
    from dashboard.basic.views import render_workspace
    # Snapshot giả do test thay qua model.load; không mở DB hay provider thật.
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a, **kw: SimpleNamespace(fetchall=lambda: [])))
    render_workspace(p, 1, "fixture_data")


def test_five_screens_render_without_api_or_permission_changes(tmp_path):
    from streamlit.testing.v1 import AppTest
    from dashboard.basic import model, views
    state = {"project": {"id": 1, "name": "Phim giả M82", "paused": 0, "script_text": "CẢNH 1 - NGÀY\nKelly bước vào kho."},
             "scenes": [{"id": 1, "idx": 1, "title": "Kelly vào kho", "image_used": 0, "video_used": 0}],
             "jobs": [], "budget": {"approved": None, "recorded": 0, "held": 0, "limit": None,
                                      "ratio": None, "warning": False, "stages": {}},
             "idea": {}, "can_edit": False, "identity": {"email": "viewer@example.test", "role": "member"},
             "data_dir": str(tmp_path)}
    with patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}), \
            patch.object(model, "load", return_value=state), \
            patch.object(views.simple_budget, "proposal", return_value={"total": None, "incomplete": True}), \
            patch.object(views.paid_confirm, "enabled", return_value=False), \
            patch.object(views.cost, "load_pricing", return_value={}), \
            patch.object(views.cost, "estimate_images", return_value={"total": None}), \
            patch.object(views.cost, "estimate_videos_by_scene", return_value={"total": None}), \
            patch.object(views.actions, "send") as send:
        at = AppTest.from_function(_ui_fixture).run()
        for screen in model.SCREENS:
            at.selectbox[0].set_value(screen).run()
            assert not at.exception
            assert [t.value for t in at.title] == ["Chế độ Cơ bản"]
        assert not send.called
    assert state["can_edit"] is False


def test_media_paths_cannot_escape_project(tmp_path):
    from dashboard.basic.model import media_path
    root = tmp_path / "assets"
    project = root / "1"
    project.mkdir(parents=True)
    allowed = project / "clip.mp4"
    allowed.write_bytes(b"fixture")
    other = tmp_path / "private.txt"
    other.write_text("fake-only")
    assert media_path(root, 1, str(allowed)) == allowed
    assert media_path(root, 1, str(other)) is None


def test_send_requires_human_confirmation_before_any_provider(project):
    from dashboard.basic import actions
    with patch("dashboard.common.image_runner") as provider:
        with pytest.raises(ValueError):
            actions.send(project, 1, "fake", "images", confirmed=False)
        assert not provider.called


def test_off_flag_and_stage_one_hold_stop_before_provider_or_queue(project):
    from dashboard.basic import actions
    project.project = lambda pid: {"paused": 0}
    with patch("dashboard.common.image_runner") as provider, \
            patch("core.batch.queue_images") as queue:
        with patch.object(actions.simple_budget, "enabled", return_value=False):
            with pytest.raises(PermissionError):
                actions.send(project, 1, "fake", "images", confirmed=True)
        # Port chưa mở: ca này chỉ chứng minh HOLD, không chứng minh stale-quote.
        with patch.object(actions, "quote", return_value={"usd": 2, "fp": "new", "ids": [1]}), \
                patch("dashboard.paid_confirm.enabled", return_value=True):
            with pytest.raises(ValueError):
                actions.send(project, 1, "fake", "images", confirmed=True,
                             expected_quote={"usd": 1, "fp": "old", "ids": [1]})
        assert not provider.called and not queue.called


def test_future_confirmed_send_reuses_batch_only_after_selected_port_is_ready(project):
    from dashboard.basic import actions
    project.project = lambda pid: {"paused": 0}
    quote = {"usd": 1, "fp": "fixed", "ids": [1]}
    from unittest.mock import Mock
    runner = Mock()
    runner.submit_pending.return_value = 1
    with patch.object(actions, "selected_send_ready", return_value=True), \
            patch.object(actions, "quote", return_value=quote), \
            patch("dashboard.paid_confirm.enabled", return_value=True), \
            patch("dashboard.common.image_runner", return_value=runner), \
            patch("core.batch.queue_images", return_value={"created": 1, "redo": 0}) as queue:
        actions.send(project, 1, "fake", "images", confirmed=True, expected_quote=quote)
        assert queue.call_args.kwargs["confirmed"] is False  # không bỏ qua cổng ảnh
        context = queue.call_args.args[0]
        assert context is not project and context.conn is project.conn
        assert context.actor == "ep@example.test" and context.origin is None
        assert not hasattr(project, "actor") and not hasattr(project, "origin")
        runner.submit_pending.assert_called_once_with(1)


def test_stage_one_does_not_approve_legacy_warning_estimate(project):
    from core import simple_budget as B
    with patch.object(B, "proposal", return_value={"total": 10, "incomplete": False}):
        with pytest.raises(ValueError, match="40|dự toán"):
            B.approve(project, 1, expected_total=10, confirmed=True)
    assert B.get(project.conn, 1) is None


def test_stage_one_holds_send_before_provider_even_with_matching_quote(project):
    from dashboard.basic import actions
    project.project = lambda pid: {"paused": 0}
    quote = {"usd": 1, "fp": "fixed", "ids": [1]}
    with patch.object(actions, "quote", return_value=quote), \
            patch("dashboard.paid_confirm.enabled", return_value=True), \
            patch("dashboard.common.image_runner") as provider, \
            patch("core.batch.queue_images") as queue:
        with pytest.raises(ValueError, match="tập|M82B"):
            actions.send(project, 1, "fake", "images", confirmed=True, expected_quote=quote)
        assert not provider.called and not queue.called


def test_pasted_script_initializes_missing_idea_inputs_in_current_project(project):
    from dashboard.basic import actions
    from core import idea_to_script, script_parser
    text = "CẢNH 1 - NGÀY\nKelly bước vào kho."
    with patch.object(idea_to_script, "check_script", return_value={"ok": True, "problems": []}), \
            patch.object(idea_to_script, "parse", return_value=([SimpleNamespace(heading="CẢNH 1")], SimpleNamespace(paragraphs=[text]))), \
            patch.object(script_parser, "import_scenes") as imported:
        assert actions.use_script(project, 1, text) == 1
    state = idea_to_script.get_state(project.conn, 1)
    assert state["inputs"]["idea"] == text
    assert state["script"] == text and state["used"] is True
    context, pid = imported.call_args.args[:2]
    assert context is not project and context.conn is project.conn and pid == 1
    assert context.actor == "ep@example.test" and context.origin is None
    assert idea_to_script.get_state(project.conn, 999) == {}


def test_pasted_script_preserves_existing_idea_inputs(project):
    from dashboard.basic import actions
    from core import idea_to_script, script_parser
    text = "CẢNH 1 - NGÀY\nKelly bước vào kho."
    original = {"idea": "Ý tưởng đã chốt", "duration_s": 55, "anchors": {"ending": "Giữ kết"}}
    idea_to_script.save_state(project.conn, 1, {"inputs": original})
    with patch.object(idea_to_script, "check_script", return_value={"ok": True, "problems": []}), \
            patch.object(idea_to_script, "parse", return_value=([{}], SimpleNamespace(paragraphs=[text]))), \
            patch.object(script_parser, "import_scenes"):
        assert actions.use_script(project, 1, text) == 1
    assert idea_to_script.get_state(project.conn, 1)["inputs"] == original


@pytest.mark.parametrize("denied", ["off", "revoked"])
def test_pasted_script_cannot_create_state_when_flag_off_or_user_revoked(project, denied):
    from dashboard.basic import actions
    from core import idea_to_script
    if denied == "revoked":
        project.conn.execute("UPDATE users SET active=0 WHERE email='ep@example.test'")
    with patch.object(actions.simple_budget, "enabled", return_value=denied != "off"):
        with pytest.raises(PermissionError):
            actions.use_script(project, 1, "CẢNH 1 - NGÀY\nKelly bước vào kho.")
    assert idea_to_script.get_state(project.conn, 1) == {}


@pytest.mark.parametrize("callback", ["pause", "save", "use", "send"])
@pytest.mark.parametrize("fails", [False, True])
def test_callbacks_have_private_actor_context_and_preserve_original(project, callback, fails):
    from contextlib import ExitStack
    from unittest.mock import Mock
    from dashboard.basic import actions
    from core import idea_to_script
    project.actor = "original-agent"
    project.origin = {"kind": "autopilot-fixture"}
    user, origin = project.user, project.origin
    project.project = lambda pid: {"paused": 0}
    seen = []
    def capture(context):
        seen.append(context)
        if fails:
            raise RuntimeError("fixture-only")
        return 1
    # Méthode gắn trên lớp, giống Pipeline thật: copy phải bind self mới.
    class CallbackProject(SimpleNamespace):
        def set_paused(self, pid, paused):
            return capture(self)
    local_project = CallbackProject(**vars(project))
    with ExitStack() as stack:
        stack.enter_context(patch.object(idea_to_script, "start", side_effect=lambda conn, pid, text, p: capture(p)))
        stack.enter_context(patch.object(idea_to_script, "get_state", return_value={"inputs": {}}))
        stack.enter_context(patch.object(idea_to_script, "edit", side_effect=lambda conn, pid, text, p: capture(p)))
        stack.enter_context(patch.object(idea_to_script, "use_script", side_effect=lambda p, pid: capture(p)))
        quote = {"usd": 1, "ids": [1], "fp": "fake"}
        runner = Mock()
        runner.submit_pending.return_value = 1
        stack.enter_context(patch.object(actions, "selected_send_ready", return_value=True))
        stack.enter_context(patch.object(actions, "quote", return_value=quote))
        stack.enter_context(patch("dashboard.paid_confirm.enabled", return_value=True))
        stack.enter_context(patch("dashboard.common.image_runner", side_effect=lambda p: (capture(p), runner)[1]))
        stack.enter_context(patch("core.batch.queue_images", return_value={"created": 1}))
        calls = {"pause": lambda: actions.pause(local_project, 1, True),
                 "save": lambda: actions.save_idea(local_project, 1, "Ý tưởng giả"),
                 "use": lambda: actions.use_script(local_project, 1, "Kịch bản giả"),
                 "send": lambda: actions.send(local_project, 1, "fake", "images", confirmed=True, expected_quote=quote)}
        if fails:
            with pytest.raises(RuntimeError, match="fixture-only"):
                calls[callback]()
        else:
            calls[callback]()
    assert seen and all(context is not local_project for context in seen)
    assert all(context.conn is project.conn and context.actor == "ep@example.test" and context.origin is None for context in seen)
    assert all(context.user == {"email": "ep@example.test", "role": "member"} for context in seen)
    assert local_project.user is user and local_project.origin is origin
    assert local_project.actor == "original-agent"


def test_each_callback_resolves_fresh_identity_without_changing_previous_context(project):
    from dashboard.basic import actions
    from core import idea_to_script
    project.actor, project.origin = "original-agent", "autopilot-fixture"
    with patch.object(idea_to_script, "start", side_effect=lambda conn, pid, text, p: p) as start:
        first = actions.save_idea(project, 1, "Giả 1")
        project.user = {"email": "edit@example.test", "role": "owner-forged"}
        second = actions.save_idea(project, 1, "Giả 2")
    assert first is not second and first is not project and second is not project
    assert first.actor == "ep@example.test" and first.user["role"] == "member"
    assert second.actor == "edit@example.test" and second.user["role"] == "member"
    assert project.user["role"] == "owner-forged"
    assert project.actor == "original-agent" and project.origin == "autopilot-fixture"
    project.conn.execute("UPDATE users SET active=0 WHERE email='edit@example.test'")
    with patch.object(idea_to_script, "start") as start:
        with pytest.raises(PermissionError):
            actions.save_idea(project, 1, "Giả bị thu hồi")
        assert not start.called
    assert first.actor == "ep@example.test" and second.actor == "edit@example.test"
