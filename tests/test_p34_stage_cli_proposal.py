"""Đề xuất JSON N4 bằng client giả; không ghi máy/state, không Blender/CLI thật."""
import copy
import ast
import json
import os
import shutil
import sqlite3
import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

with mock.patch.object(os,"environ",{}):
    from core import stage_cli_proposal as proposal, stage_desk as desk, llm_runner as runner, llm_provider

REAL_CONTEXT=proposal._context


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    fake={"HOME":str(tmp_path),"USERPROFILE":str(tmp_path),"PATH":str(tmp_path),"DASHBOARD_AUTH":"off"}
    with mock.patch.object(os,"environ",fake), \
         mock.patch.object(socket.socket,"connect",side_effect=AssertionError("network blocked")), \
         mock.patch.object(subprocess,"run",side_effect=AssertionError("CLI blocked")), \
         mock.patch.object(subprocess,"Popen",side_effect=AssertionError("spawn blocked")):
        yield


@pytest.fixture
def setup(tmp_path):
    context={"stage":"dp_stage_specs","phase":"quay_phim","revision":"fixture-rev","prompt":"fixture",
             "images":[],"validate":lambda obj: obj if isinstance(obj,dict) and obj.get("fixture_ok") is True else (_ for _ in ()).throw(ValueError("fixture schema"))}
    calls=[]
    class FakeCli(runner.ClaudeCliClient):
        name="claude-cli"
        def __init__(self): self.ledger=str(tmp_path/"ledger.sqlite")
        def complete(self,text,images=()):
            calls.append(runner.current_tag())
            return runner.LlmReply('{"fixture_ok":true}',10,2)
    client=FakeCli()
    with mock.patch.object(proposal,"_context",return_value=context), \
         mock.patch.object(desk,"segment",return_value={"id":"fixture","scene":"A","stage":"fixture"}), \
         mock.patch.object(desk,"_db_path",return_value=client.ledger), \
         mock.patch.object(desk,"_need_edit",return_value=None), \
         mock.patch.object(desk,"_sync",side_effect=lambda *args:args[-1]()), \
         mock.patch.object(llm_provider,"resolve",return_value=("claude_cli","project")), \
         mock.patch.object(llm_provider,"client_for_project",return_value=client), \
         mock.patch.object(runner,"cli_input_estimate",return_value={"estimated_input_tokens":123}), \
         mock.patch.object(proposal,"_budget_ready",return_value=True):
        yield SimpleNamespace(context=context,calls=calls,client=client)


def test_proposal_uses_project_client_tag_ledger_and_shared_estimate(setup):
    quote=proposal.quote(None,34,"fixture","A",user=None)
    assert quote["ok"] and quote["estimated_input_tokens"] == 123
    assert "ước tính" in quote["tag"]
    result=proposal.generate(None,34,"fixture","A",who={"kind":"human"},user=None,
                             expected_revision=quote["revision"],confirmed=True)
    assert result["ok"] and result["answer"]["fixture_ok"] is True
    assert setup.calls == [("dp_stage_specs",34)]
    assert "answer" not in quote


def test_confirmation_and_stale_quote_stop_before_call(setup):
    for confirmed,revision in ((False,"fixture-rev"),(True,"old")):
        result=proposal.generate(None,34,"fixture","A",who=None,user=None,expected_revision=revision,confirmed=confirmed)
        assert not result["ok"]
    assert not setup.calls


def test_no_other_provider_or_ep_approval_phase_is_called(setup):
    with mock.patch.object(llm_provider,"resolve",return_value=("anthropic","project")):
        assert not proposal.quote(None,34,"fixture","A")["ok"]
    setup.context["phase"]="duyet"
    assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    assert not setup.calls


def test_edit_permission_lock_and_missing_ledger_stop_generation(setup):
    with mock.patch.object(desk,"_need_edit",return_value={"ok":False,"errors":["fixture denied"]}):
        assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    with mock.patch.object(desk,"_sync",return_value={"ok":False,"errors":["fixture lock"]}):
        assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    with mock.patch.object(desk,"_db_path",return_value=None):
        assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    assert not setup.calls


def test_no_api_fallback_even_if_provider_changes_during_client_creation(setup):
    with mock.patch.object(llm_provider,"client_for_project",return_value=SimpleNamespace(name="anthropic")):
        assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    assert not setup.calls


def test_bad_json_or_auth_error_does_not_ingest_or_write_state(setup):
    before=copy.deepcopy({k:v for k,v in setup.context.items() if k!="validate"})
    with mock.patch.object(setup.client,"complete",return_value=runner.LlmReply("not-json",10,2)):
        result=proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)
        assert not result["ok"] and "answer" not in result
    with mock.patch.object(setup.client,"complete",side_effect=runner.LlmError("fixture",code="auth")):
        assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    assert {k:v for k,v in setup.context.items() if k!="validate"} == before


def test_role_without_canonical_cli_budget_is_blocked(setup):
    with mock.patch.object(proposal,"_budget_ready",return_value=False):
        assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    assert not setup.calls


@pytest.mark.parametrize("stage",["director_stage_blocking","dp_stage_specs","dp_stage_review","director_stage_approve"])
@pytest.mark.parametrize("enabled",[False,True])
def test_role_cli_argv_uses_canonical_budget_only_when_enabled(stage,enabled,tmp_path):
    from core import features
    args_seen=[]
    def fake(args,**kwargs):
        args_seen.append(args)
        return SimpleNamespace(returncode=0,stdout=json.dumps({"result":"{}","usage":{}}),stderr="")
    client=runner.ClaudeCliClient(model="fixture-model",run=fake)
    with mock.patch.object(shutil,"which",return_value=str(tmp_path/"fixture-cli")), \
         mock.patch.object(features,"on",side_effect=lambda name:enabled if name == "cli_call_budget" else False), \
         runner.tagged(stage,34):
        client._complete_once("fixture")
    args=args_seen[0]
    assert ("--max-turns" in args) is enabled
    if enabled:
        assert args[args.index("--max-turns")+1] == "1"
        assert args[args.index("--tools")+1] == ""
    else:
        assert args == [str(tmp_path/"fixture-cli"),"-p","--output-format","json","--no-session-persistence","--model","fixture-model"]
    estimate=runner.cli_input_estimate(stage,"fixture",0)
    assert estimate["method"] == "visible_prompt_chars_only"
    assert runner.CLI_TOKEN_STAGE_POLICY[stage] == runner.CLI_TOKEN_STAGE_POLICY["other"]


def test_worker_rechecks_pinned_proposal_before_ingest(setup):
    from core import stage_auto
    def start(conn,pid,data_dir,seg,action,who,work):
        return work(conn,lambda message:None)
    with mock.patch.object(desk,"_start",start), \
         mock.patch.object(stage_auto,"crew_answer",side_effect=AssertionError("stale must not ingest")):
        result=desk.load_answer(None,34,"fixture","A",{},who=None,expected_proposal_revision="old")
    assert not result["ok"]


def test_manual_load_retains_existing_path_without_proposal_lookup(setup):
    from core import stage_auto
    def start(conn,pid,data_dir,seg,action,who,work): return work(conn,lambda message:None)
    with mock.patch.object(desk,"_start",start),mock.patch.object(stage_auto,"crew_answer",return_value={"ok":True}), \
         mock.patch.object(proposal,"_context",side_effect=AssertionError("manual path unchanged")):
        assert desk.load_answer(None,34,"fixture","A",{},who=None)["ok"]


@pytest.fixture
def context_setup(tmp_path):
    from core import stage_auto as sa, stage_crew as crew
    status={"buttons":["N4"],"phase":"quay_phim","inputs_changed":False}
    state={"phase":"quay_phim","fp":"fixture-fp"}
    with mock.patch.object(desk,"segment",return_value={"id":"fixture","scene":"A","stage":"fixture"}), \
         mock.patch.object(desk,"scene_status",return_value=status), \
         mock.patch.object(desk,"seg_dir",return_value=str(tmp_path)), \
         mock.patch.object(desk,"_read",return_value={"marks":{}}), \
         mock.patch.object(sa,"k1_cached",return_value=str(tmp_path)), \
         mock.patch.object(sa,"base_dir",return_value=str(tmp_path)), \
         mock.patch.object(sa,"inputs_for",return_value=({},[])), \
         mock.patch.object(sa,"stored_state_before",return_value=None), \
         mock.patch.object(sa,"preflight",return_value=[]), \
         mock.patch.object(sa,"fingerprint",return_value="fixture-fp"), \
         mock.patch.object(sa,"_crew_load",return_value=state), \
         mock.patch.object(sa,"_crew_view",return_value=(None,[],[])), \
         mock.patch.object(sa,"ensure_k1_seg",side_effect=AssertionError("no Blender")), \
         mock.patch.object(sa,"_crew_save",side_effect=AssertionError("proposal must not save state")), \
         mock.patch.object(crew,"prompt_for",return_value="fixture"), \
         mock.patch.object(crew,"validator",return_value=lambda obj:obj):
        yield SimpleNamespace(status=status,state=state)


def test_real_context_is_readonly_and_ignores_only_own_lock(context_setup):
    context_setup.status["buttons"]=["N2"]
    with pytest.raises(proposal.ProposalError): REAL_CONTEXT(None,34,"fixture","A")
    first=REAL_CONTEXT(None,34,"fixture","A",locked=True)
    context_setup.state["reviews"]=1
    assert REAL_CONTEXT(None,34,"fixture","A",locked=True)["revision"] != first["revision"]
    context_setup.status["inputs_changed"]=True
    with pytest.raises(proposal.ProposalError): REAL_CONTEXT(None,34,"fixture","A",locked=True)


def test_missing_k1_never_starts_blender(context_setup):
    from core import stage_auto
    with mock.patch.object(stage_auto,"k1_cached",return_value=None):
        with pytest.raises(proposal.ProposalError): REAL_CONTEXT(None,34,"fixture","A")


def test_ui_generates_draft_and_resets_n4_confirmation_without_ingesting(setup):
    import dashboard
    class FakeUI:
        session_state={"fixture_N4_ok":True}
        def checkbox(self,*args,**kwargs): return True
        def button(self,*args,**kwargs): return False
        def caption(self,*args,**kwargs): pass
        def error(self,*args,**kwargs): raise AssertionError("unexpected error")
        def rerun(self): pass
    source=(Path(__file__).resolve().parents[1]/"dashboard/stage_desk_ui.py").read_text(encoding="utf-8")
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name == "_cli_proposal_controls")
    fake=FakeUI(); namespace={"st":fake,"json":json}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"proposal_ui_fixture","exec"),namespace)
    with mock.patch.object(dashboard,"paid_confirm",SimpleNamespace(paid_button=lambda *args,**kwargs:True),create=True), \
         mock.patch.object(desk,"load_answer",side_effect=AssertionError("separate N4 confirmation required")):
        namespace["_cli_proposal_controls"](None,34,"fixture","A","fixture",None,None,False)
    assert fake.session_state["fixture_N4_ok"] is False
    assert fake.session_state["fixture_N4_proposal_revision"] == "fixture-rev"
    assert json.loads(fake.session_state["fixture_N4_json"])["fixture_ok"] is True


def test_invalid_connection_is_filtered_without_sending():
    assert not proposal.quote("fixture-not-db",34,"fixture","A")["ok"]


def test_client_ledger_mismatch_stops_before_completion(setup):
    setup.client.ledger="fixture-other-ledger"
    assert not proposal.generate(None,34,"fixture","A",who=None,expected_revision="fixture-rev",confirmed=True)["ok"]
    assert not setup.calls


def test_review_image_turns_use_shared_canonical_rule(tmp_path):
    from core import features
    images=[]
    for index in range(3):
        path=tmp_path/f"fixture{index}.png"; path.write_bytes(b"fixture")
        images.append((f"fixture{index}",str(path)))
    seen=[]
    def fake(args,**kwargs):
        seen.append(args)
        return SimpleNamespace(returncode=0,stdout=json.dumps({"result":"{}","usage":{}}),stderr="")
    client=runner.ClaudeCliClient(run=fake)
    with mock.patch.object(shutil,"which",return_value=str(tmp_path/"fixture-cli")), \
         mock.patch.object(features,"on",side_effect=lambda name:name == "cli_call_budget"), runner.tagged("dp_stage_review",34):
        client._complete_once("fixture",images)
    assert seen[0][seen[0].index("--max-turns")+1] == "4"
    assert seen[0][seen[0].index("--tools")+1] == "Read"


@pytest.fixture
def rights_setup(tmp_path):
    path=tmp_path/"rights.sqlite"
    conn=sqlite3.connect(path); conn.row_factory=sqlite3.Row
    conn.executescript("CREATE TABLE users(email TEXT,role TEXT,active INTEGER);"
                       "CREATE TABLE projects(id INTEGER,name TEXT,created_by TEXT,llm_provider TEXT);"
                       "CREATE TABLE project_watchers(project_id INTEGER,email TEXT,level TEXT);")
    conn.execute("INSERT INTO users VALUES('fixture@example.test','member',1)")
    conn.execute("INSERT INTO projects VALUES(34,'fixture','creator@example.test','claude_cli')")
    conn.execute("INSERT INTO project_watchers VALUES(34,'fixture@example.test','edit')")
    conn.commit()
    calls=[]
    class FakeCli(runner.ClaudeCliClient):
        def __init__(self): self.ledger=str(path)
        def complete(self,text,images=()):
            calls.append(runner.current_tag()); return runner.LlmReply('{"fixture_ok":true}',10,2)
    context={"stage":"dp_stage_specs","phase":"quay_phim","revision":"fixture-rev","prompt":"fixture","images":[],"validate":lambda obj:obj}
    identity={"email":"fixture@example.test","role":"owner"}  # role phiên có thể cũ; DB mới là nguồn chuẩn.
    fake_env={"HOME":str(tmp_path),"USERPROFILE":str(tmp_path),"PATH":str(tmp_path),"DASHBOARD_AUTH":"on"}
    with mock.patch.object(os,"environ",fake_env), \
         mock.patch.object(proposal,"_context",return_value=context), \
         mock.patch.object(desk,"segment",return_value={"id":"fixture","scene":"A","stage":"fixture"}), \
         mock.patch.object(desk,"_sync",side_effect=lambda *args:args[-1]()), \
         mock.patch.object(llm_provider,"resolve",return_value=("claude_cli","project")), \
         mock.patch.object(llm_provider,"client_for_project",return_value=FakeCli()), \
         mock.patch.object(runner,"cli_input_estimate",return_value={"estimated_input_tokens":123}):
        yield SimpleNamespace(conn=conn,calls=calls,user=identity)
    conn.close()


def test_auth_on_requires_identity_before_provider_or_ledger(rights_setup):
    with mock.patch.object(llm_provider,"resolve",side_effect=AssertionError("identity must be checked first")):
        assert not proposal.quote(rights_setup.conn,34,"fixture","A",user=None)["ok"]
        assert not proposal.generate(rights_setup.conn,34,"fixture","A",who=None,user=None,
                                     expected_revision="fixture-rev",confirmed=True)["ok"]
    assert not rights_setup.calls


def test_fresh_active_member_with_project_edit_can_generate(rights_setup):
    assert proposal.generate(rights_setup.conn,34,"fixture","A",who=None,user=rights_setup.user,
                             expected_revision="fixture-rev",confirmed=True)["ok"]
    assert rights_setup.calls == [("dp_stage_specs",34)]


@pytest.mark.parametrize("mutation",["UPDATE users SET active=0", "DELETE FROM project_watchers",
                                     "UPDATE users SET role='member'; DELETE FROM project_watchers"])
def test_revocation_between_outer_guard_and_lock_blocks_cli(rights_setup,mutation):
    if "role='member'" in mutation:
        rights_setup.conn.execute("UPDATE users SET role='owner'")
    def revoked(*args):
        rights_setup.conn.executescript(mutation)
        return args[-1]()
    with mock.patch.object(desk,"_sync",side_effect=revoked):
        result=proposal.generate(rights_setup.conn,34,"fixture","A",who=None,user=rights_setup.user,
                                 expected_revision="fixture-rev",confirmed=True)
    assert not result["ok"]
    assert not rights_setup.calls


def test_cached_owner_cannot_override_fresh_db_role(rights_setup):
    rights_setup.conn.execute("DELETE FROM project_watchers")
    assert not proposal.quote(rights_setup.conn,34,"fixture","A",user=rights_setup.user)["ok"]


def test_pinned_n4_worker_rechecks_fresh_identity_before_ingest(rights_setup):
    from core import stage_auto
    def revoked(conn,pid,data_dir,seg,action,who,work):
        conn.execute("UPDATE users SET active=0")
        return work(conn,lambda message:None)
    with mock.patch.object(desk,"_start",revoked), \
         mock.patch.object(stage_auto,"crew_answer",side_effect=AssertionError("revoked must not ingest")):
        result=desk.load_answer(rights_setup.conn,34,"fixture","A",{},who=None,user=rights_setup.user,
                                expected_proposal_revision="fixture-rev")
    assert not result["ok"]
