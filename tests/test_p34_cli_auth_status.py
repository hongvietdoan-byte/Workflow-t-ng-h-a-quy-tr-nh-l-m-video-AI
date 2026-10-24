"""Auth CLI giả hoàn toàn: không chạy Claude/keyring hay mở credential."""
import ast
import json
import os
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace
from unittest import mock

import pytest

with mock.patch.object(os,"environ",{}):
    from core import cli_auth_status as auth
    from core.llm_runner import ClaudeCliClient


@pytest.mark.parametrize("message", ["Not logged in", "Please run /login", "not logged in · Please run /login"])
def test_cli_login_failures_have_explicit_auth_code(message):
    from core.llm_runner import cli_error_code
    assert cli_error_code(message) == "auth"


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    auth.clear_cache()
    fake={"HOME":str(tmp_path),"USERPROFILE":str(tmp_path),"PATH":str(tmp_path),"TEMP":str(tmp_path),"TMP":str(tmp_path)}
    with mock.patch.object(os,"environ",fake), \
         mock.patch.object(socket.socket,"connect",side_effect=AssertionError("network blocked")), \
         mock.patch.object(subprocess,"run",side_effect=AssertionError("real subprocess blocked")), \
         mock.patch.object(subprocess,"Popen",side_effect=AssertionError("real spawn blocked")), \
         mock.patch.object(auth.shutil,"which",return_value=str(tmp_path/"claude.cmd")):
        yield
    auth.clear_cache()


def fake_run(payload,returncode=0):
    calls=[]
    def run(args,**kwargs):
        calls.append({"args":args,"timeout":kwargs.get("timeout"),"shell":kwargs.get("shell"),
                      "cwd":kwargs.get("cwd"),"stdin":kwargs.get("stdin"),"stderr":kwargs.get("stderr")})
        return SimpleNamespace(returncode=returncode,stdout=json.dumps(payload),stderr="fixture ignored")
    return run,calls


def test_logged_in_email_uses_public_environment_and_safe_command():
    run,calls=fake_run({"loggedIn":True,"email":"fixture@example.test","extra":{"ignored":True}})
    with mock.patch.object(auth,"_owned_command",run), mock.patch.object(ClaudeCliClient,"clean_env",wraps=ClaudeCliClient.clean_env) as cleaned:
        result=auth.get_status("claude_cli")
    assert cleaned.call_count == 1
    assert result["status"] == "logged_in" and result["email"] == "fixture@example.test"
    assert set(result) == {"status","email","command","config_dir"}
    assert len(calls)==1 and calls[0]["args"][1:] == ["auth","status"]
    assert calls[0]["shell"] is False and 0 < calls[0]["timeout"] <= 10
    assert calls[0]["stdin"] == subprocess.DEVNULL and calls[0]["stderr"] == subprocess.DEVNULL
    assert not Path(calls[0]["cwd"]).exists()


@pytest.mark.parametrize("code",[0,1])
def test_logged_out_is_explicit_even_when_cli_exit_is_one(code):
    run,_=fake_run({"loggedIn":False,"email":"old@example.test"},code)
    with mock.patch.object(auth,"_owned_command",run):
        result=auth.get_status("claude_cli")
    assert result["status"] == "logged_out" and result["email"] is None


@pytest.mark.parametrize("payload,code",[({"loggedIn":"yes"},0),([],0),({"loggedIn":True},2)])
def test_bad_schema_or_failed_command_never_claims_login(payload,code):
    run,_=fake_run(payload,code)
    with mock.patch.object(auth,"_owned_command",run):
        assert auth.get_status("claude_cli")["status"] in ("invalid_response","command_failed")


def test_bad_json_output_is_not_returned():
    def run(*args,**kwargs):
        return SimpleNamespace(returncode=0,stdout="not-json",stderr="ignored")
    with mock.patch.object(auth,"_owned_command",run):
        assert auth.get_status("claude_cli")["status"] == "invalid_response"


@pytest.mark.parametrize("error,status",[(subprocess.TimeoutExpired("fixture",8),"timeout"),(OSError("fixture"),"command_failed")])
def test_execution_errors_are_filtered(error,status):
    with mock.patch.object(auth,"_owned_command",side_effect=error):
        result=auth.get_status("claude_cli")
    assert result["status"] == status
    assert set(result) == {"status","email","command","config_dir"}


def test_other_provider_does_not_even_prepare_cli():
    with mock.patch.object(ClaudeCliClient,"clean_env",side_effect=AssertionError("not selected")):
        assert auth.get_status("anthropic")["status"] == "not_selected"


def test_missing_binary():
    with mock.patch.object(auth.shutil,"which",return_value=None):
        assert auth.get_status("claude_cli")["status"] == "not_installed"


def test_cache_short_ttl_and_force_refresh():
    run,calls=fake_run({"loggedIn":True,"email":"fixture@example.test"})
    with mock.patch.object(auth,"_owned_command",run),mock.patch.object(auth.time,"monotonic",return_value=100):
        first=auth.get_status("claude_cli")
        assert auth.get_status("claude_cli") == first and len(calls)==1
        auth.get_status("claude_cli",force=True)
        assert len(calls)==2
    with mock.patch.object(auth,"_owned_command",run),mock.patch.object(auth.time,"monotonic",return_value=131):
        auth.get_status("claude_cli")
    assert len(calls)==3


def test_cache_does_not_cross_pipeline_home_or_config(tmp_path):
    run,calls=fake_run({"loggedIn":True})
    with mock.patch.object(auth,"_owned_command",run):
        first=auth.get_status("claude_cli")
        with mock.patch.object(os,"environ",{"HOME":str(tmp_path/"other"),"USERPROFILE":str(tmp_path/"other"),"PATH":str(tmp_path)}):
            second=auth.get_status("claude_cli")
        with mock.patch.object(os,"environ",{"HOME":str(tmp_path),"USERPROFILE":str(tmp_path),"PATH":str(tmp_path),"CLAUDE_CONFIG_DIR":str(tmp_path/"custom")}):
            third=auth.get_status("claude_cli")
    assert len(calls)==3 and first["config_dir"] != second["config_dir"] != third["config_dir"]


def header_function(fake_st,allowed):
    source=(Path(__file__).resolve().parents[1]/"dashboard/header.py").read_text(encoding="utf-8")
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name == "_pipeline_cli_status")
    namespace={"st":fake_st,"allowed":lambda _:allowed}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"header_fixture","exec"),namespace)
    return namespace["_pipeline_cli_status"]


def test_header_permissions_stop_before_provider_or_machine_lookup():
    with mock.patch.object(auth,"get_status",side_effect=AssertionError("private machine status")):
        header_function(None,False)(SimpleNamespace(),34)


@pytest.mark.parametrize("email",[None,"not-email","<b>fixture@example.test</b>"])
def test_missing_or_malformed_email_never_invalidates_login_or_gets_echoed(email):
    run,_=fake_run({"loggedIn":True,"email":email})
    with mock.patch.object(auth,"_owned_command",run):
        result=auth.get_status("claude_cli")
    assert result["status"] == "logged_in" and result["email"] is None


class FakePanel:
    def __init__(self,force=False): self.texts=[]; self.force=force
    def text(self,value): self.texts.append(value)
    def caption(self,*args,**kwargs): pass
    def code(self,*args,**kwargs): pass
    def button(self,*args,**kwargs): return self.force


def test_non_cli_project_panel_does_not_call_auth():
    from core import llm_provider
    with mock.patch.object(llm_provider,"resolve",return_value=("anthropic","project")), \
         mock.patch.object(auth,"get_status",side_effect=AssertionError("not selected")):
        header_function(FakePanel(),True)(SimpleNamespace(conn=None),34)


def test_panel_reports_unknown_email_and_force_refresh():
    from core import llm_provider
    panel=FakePanel(force=True)
    force_seen=[]
    def status(provider,*,force=False):
        force_seen.append(force)
        return {"status":"logged_in","email":None,"command":"fixture-cli","config_dir":"fixture-home"}
    with mock.patch.object(llm_provider,"resolve",return_value=("claude_cli","project")), \
         mock.patch.object(auth,"get_status",status):
        header_function(panel,True)(SimpleNamespace(conn=None),34)
    assert force_seen == [True]
    assert "Email: chưa xác định" in panel.texts
    assert "Claude Code của pipeline: Đã đăng nhập" in panel.texts


def test_machine_panel_only_called_by_permission_checked_dialog():
    source=(Path(__file__).resolve().parents[1]/"dashboard/header.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    callers=[n.name for n in tree.body if isinstance(n,ast.FunctionDef) and
             any(isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id == "_pipeline_cli_status" for c in ast.walk(n))]
    assert callers == ["_dialog_cli_auth"]


def test_dialog_registry_opens_cli_panel_and_closes_other_dialogs():
    source=(Path(__file__).resolve().parents[1]/"dashboard/common.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id == "DIALOG_FLAGS" for t in n.targets))
    opening=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == "open_dialog")
    state={"dlg_assets":True}
    namespace={"st":SimpleNamespace(session_state=state)}
    exec(compile(ast.Module(body=[assignment,opening],type_ignores=[]),"dialog_workflow_fixture","exec"),namespace)
    namespace["open_dialog"]("dlg_cli_auth")
    assert state.get("dlg_cli_auth") is True
    assert state["dlg_assets"] is False
    namespace["open_dialog"]("dlg_pricing")
    assert state["dlg_pricing"] is True
    assert state["dlg_cli_auth"] is False


def test_timeout_terminates_only_owned_windows_tree(tmp_path):
    events=[]
    class OwnedProcess:
        pid=765432
        returncode=None
        def communicate(self,timeout=None):
            events.append(("communicate",timeout))
            raise subprocess.TimeoutExpired("fixture",timeout)
        def poll(self): return self.returncode
        def kill(self): events.append(("kill",self.pid)); self.returncode=-1
        def wait(self,timeout=None): events.append(("wait",timeout)); self.returncode=-1
    process=OwnedProcess()
    def spawn(*args,**kwargs):
        events.append(("spawn",kwargs.get("creationflags"),kwargs.get("shell")))
        return process
    def terminate(args,**kwargs):
        events.append(("tree",args[1:]))
        process.returncode=-1
        return SimpleNamespace(returncode=0)
    with mock.patch.object(subprocess,"Popen",spawn), mock.patch.object(subprocess,"run",terminate):
        result=auth.get_status("claude_cli")
    assert result["status"] == "timeout"
    assert any(e[0] == "spawn" and e[1] and e[2] is False for e in events)
    assert ("tree",["/PID",str(process.pid),"/T","/F"]) in events
    assert any(e[0] == "wait" for e in events)
    assert next(i for i,e in enumerate(events) if e[0] == "tree") < next(i for i,e in enumerate(events) if e[0] == "wait")
    assert set(result) == {"status","email","command","config_dir"}


def test_unix_timeout_owns_session_and_kills_only_its_group():
    events=[]
    class OwnedProcess:
        pid=765433
        returncode=None
        def communicate(self,timeout=None): raise subprocess.TimeoutExpired("fixture",timeout)
        def poll(self): return self.returncode
        def kill(self): events.append(("parent",self.pid)); self.returncode=-1
        def wait(self,timeout=None): events.append(("wait",timeout)); self.returncode=-1
    process=OwnedProcess()
    def spawn(*args,**kwargs):
        events.append(("session",kwargs.get("start_new_session")))
        return process
    def kill_group(pid,signum):
        events.append(("group",pid)); process.returncode=-1
    with mock.patch.object(auth,"_windows",return_value=False), \
         mock.patch.object(subprocess,"Popen",spawn), mock.patch.object(os,"killpg",kill_group,create=True):
        result=auth.get_status("claude_cli")
    assert result["status"] == "timeout"
    assert events[:2] == [("session",True),("group",process.pid)]
    assert any(e[0] == "wait" for e in events)


def test_tree_command_error_still_kills_and_reaps_owned_parent():
    events=[]
    class OwnedProcess:
        pid=765434
        returncode=None
        def communicate(self,timeout=None): raise subprocess.TimeoutExpired("fixture",timeout)
        def poll(self): return self.returncode
        def kill(self): events.append(("kill",self.pid)); self.returncode=-1
        def wait(self,timeout=None): events.append(("wait",timeout))
    process=OwnedProcess()
    with mock.patch.object(subprocess,"Popen",return_value=process), \
         mock.patch.object(subprocess,"run",side_effect=OSError("fixture")):
        result=auth.get_status("claude_cli")
    assert result["status"] == "timeout"
    assert events == [("kill",process.pid),("wait",3)]


@pytest.mark.parametrize("mode,expected",[("success","logged_in"),("timeout","timeout"),("ioerror","command_failed")])
def test_owned_process_cleanup_and_pipe_close_on_every_exit(mode,expected):
    events=[]
    class Pipe:
        def close(self): events.append("pipe_closed")
    class OwnedProcess:
        pid=765435
        returncode=None
        stdout=Pipe()
        def communicate(self,timeout=None):
            if mode == "timeout": raise subprocess.TimeoutExpired("fixture",timeout)
            if mode == "ioerror": raise OSError("fixture")
            self.returncode=0
            return json.dumps({"loggedIn":True}),None
        def poll(self): return self.returncode
        def kill(self): events.append("owned_kill"); self.returncode=-1
        def wait(self,timeout=None): events.append("owned_wait"); self.returncode=-1
    process=OwnedProcess()
    def terminate(args,**kwargs):
        events.append("owned_tree")
        process.returncode=-1
        return SimpleNamespace(returncode=0)
    with mock.patch.object(subprocess,"Popen",return_value=process),mock.patch.object(subprocess,"run",terminate):
        result=auth.get_status("claude_cli")
    assert result["status"] == expected
    assert events[-1] == "pipe_closed"
    if mode != "success":
        assert "owned_tree" in events and "owned_wait" in events
