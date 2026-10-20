"""M2.9: cùng bảng ca lời dẫn đi qua các caller thật; không gọi dịch vụ."""
import importlib
import os
import socket
import subprocess
import sys
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

# name, speakers, cast: một nguồn duy nhất cho mọi caller.
CASES = [
    ("pov", ["LỜI DẪN"], []),
    ("silent_cast", ["LỜI DẪN"], ["KELLY"]),
    ("character", ["KELLY"], ["KELLY"]),
    ("mixed", ["LỜI DẪN", "KELLY"], ["KELLY"]),
    ("title_case", ["Lời dẫn"], []),
    ("english", ["NARRATOR"], []),
    ("vietnamese", ["người dẫn chuyện"], []),
]


class KnownNarrationBug(AssertionError):
    """Chỉ sai lệch đầu ra đã chứng minh ĐỎ; assert khác vẫn thất bại."""


def expect_known_output(actual, expected):
    if actual != expected:
        raise KnownNarrationBug("Sai lệch hồi quy lời dẫn đã biết")


@pytest.fixture(params=CASES, ids=[c[0] for c in CASES])
def case(request):
    name, speakers, cast = request.param
    # Chỉ những ca đã ĐỎ đúng lỗi gốc; control nhân vật vẫn assert thường.
    bugs = {"test_identity_warning": "G53", "test_qc_speaking": "G16",
            "test_hard_signs": "G17", "test_mark_skip_clears_old_index": "G15"}
    test_name = request.node.originalname
    if test_name in bugs and ("KELLY" not in speakers or (test_name == "test_identity_warning" and name == "mixed")):
        request.node.add_marker(pytest.mark.xfail(strict=True, raises=KnownNarrationBug, reason=bugs[test_name]))
    return SimpleNamespace(name=name, speakers=speakers, talking="KELLY" in speakers,
                           data={"dialogue": [{"speaker": s, "text": "Câu thử."} for s in speakers],
                                 "characters": cast, "size": "CU", "lip_sync": True, "shot_no": 1})


@pytest.fixture
def api(tmp_path):
    # Thay OBJECT trước import: không đọc/lưu/in môi trường hay credential của máy.
    with ExitStack() as stack:
        stack.enter_context(patch.object(os, "environ", {"LLM_PROVIDER": "mock",
            "FEATURE_SETTINGS_FILE": str(tmp_path / "flags.json"),
            "KNOWLEDGE_USER_DIR": str(tmp_path / "knowledge")}))
        stack.enter_context(patch.object(socket, "create_connection", side_effect=RuntimeError("offline")))
        stack.enter_context(patch.object(socket.socket, "connect", side_effect=RuntimeError("offline")))
        stack.enter_context(patch.object(subprocess, "Popen", side_effect=RuntimeError("no process")))
        if sys.platform == "win32":
            import winreg
            stack.enter_context(patch.object(winreg, "OpenKey", side_effect=OSError("offline registry")))
        else:
            stack.enter_context(patch.dict(sys.modules, {"winreg": SimpleNamespace(
                OpenKey=Mock(side_effect=OSError("offline registry")))}))
        unavailable = Mock(side_effect=RuntimeError("offline credentials"))
        stack.enter_context(patch.dict(sys.modules, {
            "keyring": SimpleNamespace(get_password=unavailable, get_credential=unavailable),
            "win32cred": SimpleNamespace(CredRead=unavailable, CredEnumerate=unavailable)}))
        stack.enter_context(patch.object(importlib.import_module("core.llm_runner"), "client_from_env",
                                         side_effect=RuntimeError("offline provider loader")))
        stack.enter_context(patch.object(importlib.import_module("core.model_router"), "load_profiles",
                                         side_effect=RuntimeError("offline model loader")))
        mods = {n: importlib.import_module("core." + n) for n in
                ("lipsync", "speaker_lint", "seedance_refs", "claude_tasks", "quality_tier", "runner", "clip_measure", "diag", "skill_dossier")}
        yield SimpleNamespace(**mods)


def entries(case):
    return [{"speaker": s, "text": "Câu thử.", "line": i, "duration_ms": 1250,
             "file": f"line_{i}.wav"} for i, s in enumerate(case.speakers)]


def test_narrator_recognition(api, case):
    assert [api.speaker_lint.is_narrator(s) for s in case.speakers] == [s != "KELLY" for s in case.speakers]


def test_method(api, case):
    assert api.lipsync._method(case.data) == ("generate" if case.talking else "skip")


def test_take_segments(api, case, tmp_path):
    runner = SimpleNamespace(data_dir=str(tmp_path), _group_secs=lambda rows: [6.0],
                             _choice=lambda job: {"model": "seedance-2.5"})
    with patch.object(api.lipsync, "enabled", return_value=True), patch.object(api.lipsync, "take_on", return_value=True), \
         patch.object(api.lipsync, "shot_lines", return_value=entries(case)):
        got = api.runner.VideoRunner._take_segments(runner, {"project_id": 1}, [{"id": 1, "data": case.data}])
    assert [s["speaker"] for s in got] == (["KELLY"] if case.talking else [])
    if case.talking:
        expected = api.lipsync.voice.LIP_LEAD + (1.25 + api.lipsync.voice.GAP if case.name == "mixed" else 0)
        assert got[0]["start"] == round(expected, 3)
        assert got[0]["end"] == round(expected + 1.25, 3)


def test_shot_audio(api, case, tmp_path):
    calls = []
    def ffmpeg(cmd, **kwargs):
        calls.append(cmd)
        from pathlib import Path
        Path(cmd[-1]).write_bytes(b"offline wav")
        return SimpleNamespace(returncode=0)
    with patch.object(api.lipsync, "shot_lines", return_value=entries(case)), \
         patch.object(subprocess, "run", side_effect=ffmpeg):
        got = api.lipsync.shot_audio(str(tmp_path), 1, 1, 6, "offline-ffmpeg")
    assert bool(got) == case.talking
    assert len(calls) == int(case.talking)
    if case.talking:
        assert [calls[0][i+1] for i, v in enumerate(calls[0]) if v == "-i"] == [os.path.join(api.lipsync.audio_lib.assets_dir(str(tmp_path), 1), f"line_{case.speakers.index('KELLY')}.wav")]
        expected = api.lipsync.voice.LIP_LEAD + (1.25 + api.lipsync.voice.GAP if case.name == "mixed" else 0)
        assert f"adelay={int(expected*1000)}|{int(expected*1000)}" in calls[0][calls[0].index("-filter_complex")+1]


def test_identity_warning(api, case):
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = None
    with patch.object(api.diag, "record") as record:
        api.seedance_refs._say_speakers_without_picture(conn, 1, [{"data": case.data}], set())
    messages = [c.args[3] for c in record.call_args_list]
    expect_known_output(len(messages), int(case.talking))
    if case.talking:
        assert "KELLY" in messages[0]
        expect_known_output(all(s not in messages[0] for s in case.speakers if s != "KELLY"), True)


def test_qc_speaking(api, case):
    with patch.object(importlib.import_module("core.shots"), "approved_image_path", return_value=None), \
         patch.object(api.claude_tasks, "_shot_voice", return_value=(None, None, None)) as voice, \
         patch.object(api.clip_measure, "measure", return_value={}) as measure:
        api.claude_tasks._measure_clip(SimpleNamespace(conn=Mock()), {"project_id": 1, "scene_id": 1, "id": 1}, "offline.mp4", case.data, None, "offline")
    expect_known_output(measure.call_args.kwargs["speaking"], case.talking)
    assert voice.call_count == int(case.talking)


def test_hard_signs(api, case):
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = None
    with patch.object(api.skill_dossier, "route_reason", return_value=None), \
         patch.object(api.quality_tier, "_group_take", return_value=None):
        got = api.quality_tier.hard_signs(conn, 1, case.data)
    expect_known_output("khớp môi / take thoại" in got, case.talking)


def test_mark_skip_clears_old_index(api, case, tmp_path):
    api.lipsync.mark(str(tmp_path), 1, 1, state="done", method="take", offsets=[1], job_id=4)
    assert api.lipsync.synced_scene_ids(str(tmp_path), 1) == {1}
    method = api.lipsync._method(case.data)
    api.lipsync.mark(str(tmp_path), 1, 1, method=method)
    expect_known_output(api.lipsync.synced_scene_ids(str(tmp_path), 1), {1} if case.talking else set())
    if not case.talking:
        assert not api.lipsync.index(str(tmp_path), 1).get("1", {}).get("offsets")


def test_take_off_never_loads_audio_or_model(api, case, tmp_path):
    runner = SimpleNamespace(data_dir=str(tmp_path), _group_secs=Mock(side_effect=RuntimeError("unexpected timing")),
                             _choice=Mock(side_effect=RuntimeError("unexpected model")))
    with patch.object(api.lipsync, "enabled", return_value=False), \
         patch.object(api.lipsync, "shot_lines", side_effect=RuntimeError("unexpected audio")):
        assert api.runner.VideoRunner._take_segments(runner, {"project_id": 1}, [{"id": 1, "data": case.data}]) == []
