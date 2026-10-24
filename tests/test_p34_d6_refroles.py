"""Job 1202: còn số ảnh nhưng mất vai; fixture ngoại tuyến, không đọc dự án thật."""
from unittest import mock
import os
from contextlib import ExitStack
import socket
import subprocess
import sys
from types import SimpleNamespace
import pytest

with mock.patch.object(os, "environ", {"PYTHONUTF8": "1"}):
    from core import chat_prompt, seedance_refs
    from core.runner import VideoRunner


@pytest.fixture(autouse=True)
def isolated_test_runtime(tmp_path):
    """Tự an toàn cả khi chạy pytest thường, không cần harness bên ngoài."""
    fake = {"PYTHONUTF8": "1", "HOME": str(tmp_path / "home"), "USERPROFILE": str(tmp_path / "home"),
            "PIPELINE_DATA": str(tmp_path / "projects"), "FEATURE_SETTINGS_FILE": str(tmp_path / "flags.json"),
            "KNOWLEDGE_USER_DIR": str(tmp_path / "knowledge"), "FEATURE_BASELINE_FILE": "",
            "PLATES3D_LOCK": str(tmp_path / "blender.lock"), "BG_POLL": "0", "DASHBOARD_AUTH": "off"}
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(os, "environ", fake))
        stack.enter_context(mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network disabled")))
        stack.enter_context(mock.patch.object(subprocess, "Popen", side_effect=AssertionError("native disabled")))
        no_credentials = SimpleNamespace(get_password=lambda *a, **k: None, CredRead=mock.Mock(side_effect=FileNotFoundError))
        stack.enter_context(mock.patch.dict(sys.modules, {"keyring": no_credentials, "win32cred": no_credentials}))
        try:
            import winreg
        except ImportError:
            pass
        else:
            stack.enter_context(mock.patch.object(winreg, "OpenKey", side_effect=FileNotFoundError))
        from core.providers import MockVideoProvider, MockImageProvider
        stack.enter_context(mock.patch("core.adapters.factory.video_provider", side_effect=MockVideoProvider))
        stack.enter_context(mock.patch("core.adapters.factory.image_provider", side_effect=MockImageProvider))
        stack.enter_context(mock.patch("core.adapters.factory.subject_library", return_value=None))
        stack.enter_context(mock.patch("core.llm_provider._client", return_value=None))
        stack.enter_context(mock.patch("core.prompt_rewrite.client_for", return_value=None))
        yield


BEFORE = ("Image 1 is the storyboard frame of Shot 1: Shot 1 starts with exactly this composition, framing and these character positions.\n"
          "Image 2 is ROI TIM: identity only (face, hair, outfit) — not the framing. "
          "Image 3 is ROI DO: identity only (face, hair, outfit) — not the framing.\n"
          "Image 4 is the 3D PLACE render for Shot 1: buildings stay fixed.\n"
          "Any white banner or red mark on a reference picture is an annotation, never part of the video.")
AFTER = "Shot 1: Image 1 sets a dance; Image 2 and Image 3 dance beside Image 4."


def test_d6_numbers_without_roles_rejected():
    assert any("vai" in x for x in chat_prompt.check(BEFORE, AFTER, 5000, lock_roles=True))


def test_d6_input_locks_full_roles():
    with mock.patch.object(chat_prompt, "guide_for", return_value="fake"):
        text = chat_prompt.build_text("video", "seedance", BEFORE, [], {}, [], 5000)
    assert "KHÓA" in text
    for role in seedance_refs.role_clauses(BEFORE):
        assert role in text


def test_final_guard_repairs_job_1202_and_preserves_compatible_bytes():
    roles = seedance_refs.role_clauses(BEFORE)
    with mock.patch.object(os, "environ", {}):
        r = object.__new__(VideoRunner)
        r.provider = mock.Mock(negative="none")
        r._diag_once = mock.Mock()
        job = {"id": 1202, "scene_id": 7}
        kwargs = {"reference_only": ["a", "b", "c", "d"], "_reference_roles": roles}
        args = ("unused", AFTER, None, 4, "seedance")
        fixed = r._guard_reference_roles(job, args, kwargs)
        for role in roles:
            assert role in fixed[1]
        assert r._guard_reference_roles(job, fixed, kwargs) == fixed
        assert r._guard_reference_roles(job, ("unused", BEFORE, None, 4, "seedance"), kwargs)[1] == BEFORE


def test_final_guard_holds_unknown_metadata_and_overflow():
    with mock.patch.object(os, "environ", {}):
        r = object.__new__(VideoRunner)
        r.provider = mock.Mock(negative="none")
        r._diag_once = mock.Mock()
        job = {"id": 1202, "scene_id": 7}
        for text, roles in [(AFTER, []), ("x" * 4000, seedance_refs.role_clauses(BEFORE))]:
            assert r._guard_reference_roles(job, ("unused", text, None, 4, "seedance"),
                                            {"reference_only": ["a", "b", "c", "d"], "_reference_roles": roles}) is None


def test_preview_hold_does_not_write_runner_memory():
    from core.runner import WAIT_REASONS
    r = object.__new__(VideoRunner)
    r.provider = mock.Mock(negative="none")
    r._preview = True
    r._diag_once = mock.Mock()
    before = dict(WAIT_REASONS)
    assert r._guard_reference_roles({"id": 1202, "scene_id": 7}, ("unused", AFTER, None, 4, "seedance"),
                                    {"reference_only": ["unknown"]}) is None
    assert WAIT_REASONS == before


def test_d6_cache_and_cap_return_restore_without_an_extra_llm_call():
    from types import SimpleNamespace
    from core.runner import chat_rewrite
    r = SimpleNamespace(p=mock.Mock())
    with mock.patch.object(chat_prompt, "enabled", return_value=True), \
            mock.patch.object(chat_prompt, "rewrite", return_value=AFTER) as rw:
        out = chat_rewrite(r, {"id": 1202}, "video", BEFORE, [], "seedance")
    assert rw.call_count == 1
    for role in seedance_refs.role_clauses(BEFORE):
        assert role in out


def test_role_loss_alone_does_not_pay_for_a_d6_fix_turn(tmp_path):
    from core.pipeline import Pipeline
    from core.db import connect
    from tests.test_chat_prompt import FakeClaude
    p = Pipeline(connect())
    pid = p.create_project("fixture job 1202")
    sid = p.create_scene(pid, 1, "shot fixture")
    jid = p.create_job(sid, "video_gen")
    claude = FakeClaude([{"prompt": AFTER}])
    with mock.patch.object(chat_prompt, "enabled", return_value=True), \
            mock.patch.object(chat_prompt, "estimate", return_value=0), \
            mock.patch.object(chat_prompt, "guide_for", return_value="fake"):
        out = chat_prompt.rewrite(p, p.job(jid), "video", BEFORE, [], model="seedance", client=claude)
    assert len(claude.calls) == 1
    for role in seedance_refs.role_clauses(BEFORE):
        assert role in out


def test_role_repair_overflow_and_conflict_never_pay_a_fix_turn():
    from core.pipeline import Pipeline
    from core.db import connect
    from tests.test_chat_prompt import FakeClaude
    cases = [
        (BEFORE + "\n" + "x" * (999 - len(BEFORE)), AFTER + "x" * (850 - len(AFTER)), 900),
        (BEFORE, AFTER + "\nImage 2 is the PLACE render for Shot 1: copy the scenery.", 5000),
        (BEFORE, BEFORE + "\nImage 2 is the PLACE render for Shot 1: copy the scenery.", 5000),
    ]
    for assembled, answer, limit in cases:
        p = Pipeline(connect())
        pid = p.create_project("fixture role conflict")
        sid = p.create_scene(pid, 1, "shot fixture")
        jid = p.create_job(sid, "video_gen")
        claude = FakeClaude([{"prompt": answer}])
        with mock.patch.object(chat_prompt, "enabled", return_value=True), \
                mock.patch.object(chat_prompt, "estimate", return_value=0), \
                mock.patch.object(chat_prompt, "guide_for", return_value="fake"):
            assert chat_prompt.rewrite(p, p.job(jid), "video", assembled, [], model="seedance", limit=limit, client=claude) == assembled
        assert len(claude.calls) == 1
        import json
        calls = json.loads(p.conn.execute("SELECT value FROM app_settings WHERE key=?", (chat_prompt.CALLS_KEY.format(jid),)).fetchone()[0])
        assert calls.get("fix", 0) == 0


def test_final_guard_holds_conflict_even_when_canonical_is_also_present():
    r = object.__new__(VideoRunner)
    r.provider = mock.Mock(negative="none")
    r._diag_once = mock.Mock()
    text = BEFORE + "\nImage 2 is the PLACE render for Shot 1: copy the scenery."
    assert seedance_refs.keep_roles(BEFORE, text, 5000) == BEFORE
    assert r._guard_reference_roles({"id": 1202, "scene_id": 7}, ("unused", text, None, 4, "seedance"),
                                    {"reference_only": ["a", "b", "c", "d"], "_reference_roles": seedance_refs.role_clauses(BEFORE)}) is None


def test_first_last_ref_first_multishot_have_no_reference_only_role_obligation():
    r = object.__new__(VideoRunner)
    args = ("first", "motion", None, 4, "seedance")
    for kwargs in ({}, {"last_frame": "last"}, {"image_references": [{"label": "person", "path": "ref"}]},
                   {"multi_prompt": [{"prompt": "shot", "duration": 4}]}):
        assert r._guard_reference_roles({"id": 1202, "scene_id": 7}, args, kwargs) == args


def test_final_guard_counts_end_sentence_negative_and_skips_existing_sample():
    from core.adapters.clipai import ref_end_frame_sentence
    r = object.__new__(VideoRunner)
    r.provider = mock.Mock(negative="append")
    r._diag_once = mock.Mock()
    job = {"id": 1202, "scene_id": 7}
    role = "Image 1 is ROI TIM: identity only (face, hair, outfit) — not the framing."
    kwargs = {"reference_only": ["a"], "_reference_roles": [role], "last_frame": "end"}
    text = role + "x" * (4000 - len(role) - len(ref_end_frame_sentence(2)) - 1)
    assert r._guard_reference_roles(job, ("a", text, None, 4, "seedance"), kwargs)[1] == text
    assert r._guard_reference_roles(job, ("a", text, "ban", 4, "seedance"), kwargs) is None
    args = ("a", AFTER, None, 4, "seedance")
    assert r._guard_reference_roles(job, args, {"reference_only": ["unknown"], "_from_sample": "sample"}) == args


def test_actual_source_roles_keep_forms_objects_place_and_fail_closed_on_missing_frame():
    from core import kho_profile
    from types import SimpleNamespace
    r = object.__new__(VideoRunner)
    r.p = SimpleNamespace(conn=mock.Mock())
    r.data_dir = "fixture-only"
    r._start_frame = mock.Mock(return_value="start")
    r._ref_end_sentence = mock.Mock(return_value="")
    rows = [{"id": 7, "data": {}}, {"id": 8, "data": {}}]
    identities = [("ROI TIM", "tim"), ("ROI DO" + seedance_refs.FORM_TAG, "form"),
                  ("VAT" + seedance_refs.OBJECT_TAG, "object"), ("ROI TIM" + seedance_refs.OUTFIT_TAG, "outfit")]
    places = [{"path": "place", "shots": [1, 2], "view": "same"}]
    with mock.patch.object(seedance_refs, "identity_pictures", return_value=identities), \
            mock.patch.object(seedance_refs, "place_pictures", return_value=places), \
            mock.patch.object(kho_profile, "forms_for_rows", return_value={}), \
            mock.patch("core.features.on", return_value=False):
        sources = r._reference_sources({"project_id": 34, "scene_id": 7}, rows)
        assert len(sources) == 7
        assert "identity only" in sources[2]["role"]
        assert "whole body, clothes" in sources[3]["role"]
        assert "the object VAT" in sources[4]["role"]
        assert "the OUTFIT ROI TIM" in sources[5]["role"]
        assert "render for Shot 1, Shot 2" in sources[6]["role"]
        r.p.project = lambda pid: {"shot_mode": "per_shot"}
        r._choice = lambda job: {"model": "seedance-2.5"}
        r._skill_assets = lambda job: None
        r._sends_group = lambda job: rows
        r._refs = lambda job: True
        r._take_audio = lambda *args: None
        r._no_lip_sync_note = mock.Mock()
        r._hosted_pictures = mock.Mock(return_value=None)
        r.provider = mock.Mock(negative="none")
        r._diag_once = mock.Mock()
        job = {"id": 1202, "project_id": 34, "scene_id": 7}
        with mock.patch.object(seedance_refs, "mark", side_effect=lambda path, *a, **k: path), \
                mock.patch.object(seedance_refs, "note_sent"):
            kwargs = r._base_submit_kwargs(job)
        canonical = seedance_refs.prompt([("dance", 1)] * 2, identities, places=places, forms={})
        args = ("unused", canonical, None, 4, "seedance-2.5")
        assert kwargs["reference_only"] == [s["path"] for s in sources]
        assert r._guard_reference_roles(job, args, kwargs) == args
        r._start_frame.side_effect = lambda pid, sid: "start" if sid == 7 else None
        broken = r._reference_sources({"project_id": 34, "scene_id": 7}, rows)
        assert all(not s["role"] for s in broken)
        with mock.patch.object(seedance_refs, "mark", side_effect=lambda path, *a, **k: path), \
                mock.patch.object(seedance_refs, "note_sent"):
            kwargs = r._base_submit_kwargs(job)
        assert r._guard_reference_roles(job, args, kwargs) is None


def test_send_pipeline_filters_private_metadata_and_holds_before_provider():
    from tests import test_seedance_refs as fixture
    case = fixture.SeedanceRefTests()
    case.setUp()
    try:
        r = case._ready()
        jid = case.p.create_job(case.ids[0], "video_gen")
        args = ("unused", AFTER, None, 4, "seedance")
        kwargs = {"reference_only": ["a", "b", "c", "d"], "_reference_roles": seedance_refs.role_clauses(BEFORE)}
        with mock.patch.object(r, "_wait", return_value=False), \
                mock.patch.object(r, "_blocked", return_value=None), \
                mock.patch.object(r, "_gate_hold", return_value=None), \
                mock.patch.object(r, "_desk_hold", return_value=None), \
                mock.patch("core.change_review.blocking", return_value=None), \
                mock.patch.object(r, "_submit_args", return_value=args), \
                mock.patch.object(r, "_prepare_kwargs", return_value=kwargs):
            assert r.submit_pending(case.pid) == 1
        task = next(iter(r.provider._tasks.values()))
        for role in kwargs["_reference_roles"]:
            assert role.lower() in task["prompt"]
        assert case.p.job(jid)["state"] == "running"
        # Chữ ký MockVideoProvider.submit là nghiêm: metadata riêng lọt ra sẽ TypeError.
        r.provider.submit = mock.Mock(side_effect=AssertionError("không được gửi"))
        jid2 = case.p.create_job(case.ids[-1], "video_gen")
        with mock.patch.object(r, "_wait", return_value=False), \
                mock.patch.object(r, "_blocked", return_value=None), \
                mock.patch.object(r, "_gate_hold", return_value=None), \
                mock.patch.object(r, "_desk_hold", return_value=None), \
                mock.patch("core.change_review.blocking", return_value=None), \
                mock.patch.object(r, "_submit_args", return_value=args), \
                mock.patch.object(r, "_prepare_kwargs", return_value={"reference_only": ["unknown"]}):
            assert r.submit_pending(case.pid) == 0
        r.provider.submit.assert_not_called()
        assert case.p.job(jid2)["state"] == "queued"
    finally:
        case.doCleanups()
