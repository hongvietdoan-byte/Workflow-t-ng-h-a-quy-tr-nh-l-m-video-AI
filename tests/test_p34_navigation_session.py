"""Mục 10: hàm Dashboard thật qua AST, auth/Streamlit giả; không mở CLI/CSDL/server."""
import ast
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[1]


def functions(path, names, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(nodes) == len(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, "exec"), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


class Stopped(Exception):
    pass


@pytest.fixture
def gate(tmp_path):
    fake_env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "PATH": str(tmp_path),
                "DASHBOARD_AUTH": "on", "PYTHONUTF8": "1"}
    with mock.patch.object(os, "environ", fake_env), \
         mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network blocked")), \
         mock.patch.object(subprocess, "Popen", side_effect=AssertionError("spawn blocked")), \
         mock.patch.object(subprocess, "run", side_effect=AssertionError("CLI blocked")):
        ui = SimpleNamespace(session_state={}, query_params={}, warning=mock.Mock(), info=mock.Mock(),
                             stop=mock.Mock(side_effect=Stopped), rerun=mock.Mock(side_effect=Stopped))
        member = SimpleNamespace(email="fixture@example.test", name="Fixture", role="member", perms=[])
        auth = SimpleNamespace(ensure_owner=mock.Mock(), identity=mock.Mock(return_value=None),
                               logout=mock.Mock(), OWNER_EMAIL="fixture-owner@example.test")
        machine = SimpleNamespace(session_refusal=mock.Mock(return_value=None))
        import core
        with mock.patch.object(core, "machine_auth", machine, create=True), \
             mock.patch.dict(sys.modules, {"core.machine_auth": machine}):
            login = mock.Mock()
            ns = {"st": ui, "auth": auth, "auth_on": lambda: os.environ["DASHBOARD_AUTH"] == "on",
                  "request_source": lambda: ("fixture", True), "C": SimpleNamespace(request_ip=lambda: "fixture"),
                  "login_screen": login, "sign_in": mock.Mock(return_value=False), "Pipeline": object,
                  "me": lambda: ui.session_state["identity"], "ui": SimpleNamespace(v2_on=lambda: False),
                  "escape": str, "user_bar": mock.Mock()}
            api = functions("dashboard/header.py", {"require_login", "remember_pid", "account_section"}, ns)
            yield SimpleNamespace(ui=ui, auth=auth, machine=machine, member=member, ns=ns, api=api, login=login)


def test_valid_session_repairs_missing_s_after_machine_guard(gate, capsys):
    gate.ui.session_state["auth_token"] = "fixture-session"
    gate.ui.query_params.update(pid="34", step="2", theme="dark")
    gate.auth.identity.return_value = gate.member
    def approved(*args):
        assert "s" not in gate.ui.query_params  # không xuất token trước cổng máy.
    gate.machine.session_refusal.side_effect = approved
    gate.api.require_login(None)
    assert gate.ui.query_params.get("s") == gate.ui.session_state["auth_token"]
    assert gate.ui.query_params["pid"] == "34" and gate.ui.query_params["theme"] == "dark"
    assert not gate.login.called and not gate.ui.warning.called
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_session_precedence_replaces_another_url_token(gate):
    gate.ui.session_state["auth_token"] = "fixture-session"
    gate.ui.query_params["s"] = "fixture-other"
    gate.auth.identity.return_value = gate.member
    gate.api.require_login(None)
    assert gate.ui.query_params.get("s") == gate.ui.session_state["auth_token"]
    assert gate.auth.identity.call_count == 1


def test_new_url_without_session_explains_missing_session_without_echo(gate):
    gate.ui.query_params.update(pid="34", step="2", extra="fixture-private-input")
    with pytest.raises(Stopped):
        gate.api.require_login(None)
    messages = [call.args[0] for call in gate.ui.warning.call_args_list]
    assert messages == ["Phiên đăng nhập không mang theo, đăng nhập lại."]
    assert "s" not in gate.ui.query_params and "identity" not in gate.ui.session_state
    assert gate.login.call_count == 1 and not gate.machine.session_refusal.called


def test_new_tab_with_valid_link_uses_canonical_identity_and_machine_check(gate):
    gate.ui.query_params.update(s="fixture-link", pid="34", step="2")
    gate.auth.identity.side_effect = [None, gate.member]
    gate.api.require_login(None)
    assert gate.ui.session_state["auth_token"] == gate.ui.query_params["s"]
    assert gate.ui.session_state["identity"]["email"] == gate.member.email
    assert gate.machine.session_refusal.call_count == 1
    assert not gate.login.called


def test_legacy_login_still_goes_through_sign_in_and_machine_guard(gate):
    gate.ui.query_params["login"] = "fixture@example.test"
    gate.auth.identity.side_effect = [None, gate.member]
    def signed_in(*args):
        gate.ui.session_state["auth_token"] = "fixture-new-session"
        gate.ui.query_params.pop("login", None)
        return True
    gate.ns["sign_in"].side_effect = signed_in
    gate.api.require_login(None)
    assert gate.ns["sign_in"].call_count == 1 and gate.machine.session_refusal.call_count == 1
    assert gate.ui.query_params.get("s") == gate.ui.session_state["auth_token"]
    assert not gate.ui.warning.called and not gate.login.called


@pytest.mark.parametrize("source", ["session", "url"])
def test_revoked_token_never_reappears_in_url(gate, source):
    if source == "session":
        gate.ui.session_state["auth_token"] = "fixture-revoked"
    else:
        gate.ui.query_params["s"] = "fixture-revoked"
    with pytest.raises(Stopped):
        gate.api.require_login(None)
    assert "s" not in gate.ui.query_params and "auth_token" not in gate.ui.session_state
    assert not gate.machine.session_refusal.called


def test_owner_link_from_another_machine_stays_denied(gate):
    gate.member.role = "owner"
    gate.ns["request_source"] = lambda: ("fixture-remote", False)
    gate.ui.query_params["s"] = "fixture-owner-link"
    gate.auth.identity.side_effect = [None, gate.member]
    with pytest.raises(Stopped):
        gate.api.require_login(None)
    assert "s" not in gate.ui.query_params and "auth_token" not in gate.ui.session_state
    assert not gate.machine.session_refusal.called


def test_machine_refusal_does_not_repair_session(gate):
    gate.ui.session_state["auth_token"] = "fixture-session"
    gate.auth.identity.return_value = gate.member
    gate.machine.session_refusal.return_value = "Máy chưa được duyệt."
    with pytest.raises(Stopped):
        gate.api.require_login(None)
    assert "s" not in gate.ui.query_params and "auth_token" not in gate.ui.session_state
    assert gate.ui.session_state["login_error"] == "Máy chưa được duyệt."


def test_auth_off_adds_no_session_to_url(gate):
    os.environ["DASHBOARD_AUTH"] = "off"
    gate.api.require_login(None)
    assert "s" not in gate.ui.query_params and not gate.auth.identity.called


def test_internal_callbacks_preserve_s_and_other_query_keys(gate):
    gate.ui.query_params.update(s="fixture-session", theme="dark")
    common = functions("dashboard/common.py", {"go_screen"},
                       {"st": gate.ui, "screen_label": lambda key: key, "SB_TABS": ("images", "motion")})
    common.go_screen(34, "storyboard", tab=1)
    gate.api.remember_pid(34)
    assert gate.ui.query_params == {"s": "fixture-session", "theme": "dark", "pid": "34"}
    assert gate.ui.session_state["global_pid"] == 34 and gate.ui.session_state["sb_tab"] == "motion"


def test_logout_removes_session_and_url_before_rerun(gate):
    gate.ui.session_state.update(auth_token="fixture-session", identity={"name": "Fixture", "email": "fixture@example.test", "role": "member"})
    gate.ui.query_params.update(s="fixture-session", login="fixture@example.test", pid="34")
    gate.ui.caption = mock.Mock()
    gate.ui.button = mock.Mock(return_value=True)
    with pytest.raises(Stopped):
        gate.api.account_section(SimpleNamespace(conn=None))
    assert "s" not in gate.ui.query_params and "login" not in gate.ui.query_params
    assert "auth_token" not in gate.ui.session_state and "identity" not in gate.ui.session_state
    assert gate.auth.logout.call_count == 1
