"""Đ10.6: ca #24 shot 9 dựng lại ngoại tuyến."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from core import features, prompts, prompt_formula as pf
from core.db import connect
from core.pipeline import Pipeline


def bundles():
    p=Pipeline(connect()); pid=p.create_project("ambient"); p.create_scene(pid,1,"Sương mù")
    try:
        return [prompts.build_director_bundle(p,pid), prompts.build_motion_bundle(p,pid),
                prompts.build_dp_bundle(p,pid,{"characters":[],"scenes":[{"idx":1}]},1)]
    finally:
        p.conn.close()


def test_off_byte_exact(monkeypatch, tmp_path):
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(tmp_path / "none.json"))
    monkeypatch.setenv("FEATURE_AMBIENT_MOTION", "0")
    expected=json.loads((Path(__file__).parent / "fixtures/ambient_motion_off.json").read_text(encoding="utf-8"))
    assert [s.encode("utf-8") for s in bundles()] == [s.encode("utf-8") for s in expected]


def test_rule_at_all_writers(monkeypatch):
    monkeypatch.setenv("FEATURE_AMBIENT_MOTION", "1")
    for text in bundles():
        assert "Lớp chuyển động nền" in text
        assert "motion_en" in text and "trời lặng" in text and "trong nhà" in text


def test_default_off(monkeypatch, tmp_path):
    monkeypatch.setenv("FEATURE_SETTINGS_FILE",str(tmp_path / "none.json"))
    monkeypatch.delenv("FEATURE_AMBIENT_MOTION",raising=False)
    assert features.on("ambient_motion") is False


@pytest.mark.parametrize("data,words", [
    ({"location":"sân giếng", "weather":"trời lặng, sương mù", "time":"đêm"}, "sương"),
    ({"location":"trong nhà", "weather":"trời lặng", "time":"đêm"}, "trong nhà"),
    ({"byd":{"noi_chon":{"thoi_tiet":"foggy","thoi_gian":"night"}}}, "sương"),
    ({}, "Thiếu"),
])
def test_missing_static_is_yellow(data, words):
    with patch("core.features.on", return_value=True):
        issues=pf.lint_motion("The clip starts on the first frame. Static camera. She holds her pose.",data)
    ambient=[i for i in issues if i["part"]=="chuyen_dong_nen"]
    assert len(ambient)==1 and ambient[0]["level"]=="warn"
    assert words in ambient[0]["msg"]


@pytest.mark.parametrize("text", ["Low fog drifts gently behind her.", "Leaves sway subtly in the background.", "Lamp light flickers softly.", "Sương lan nhẹ phía sau."])
def test_ambient_present(text):
    with patch("core.features.on", return_value=True):
        assert not [i for i in pf.lint_motion(text,{}) if i["part"]=="chuyen_dong_nen"]


def test_off_no_ambient_warning():
    with patch("core.features.on", return_value=False):
        assert not [i for i in pf.lint_motion("Static camera",{}) if i["part"]=="chuyen_dong_nen"]


def test_calm_suggestion_does_not_invent_wind_or_clouds():
    with patch("core.features.on", return_value=True):
        issues=pf.lint_motion("Static camera",{"location":"trong nhà", "weather":"trời lặng"})
    msg=next(i["msg"] for i in issues if i["part"]=="chuyen_dong_nen")
    assert "gió mạnh" not in msg and "mây trôi" not in msg


@pytest.mark.parametrize("text", ["No fog drifts behind her.", "Clouds remain still.", "She làm a move then lands.", "Low fog."])
def test_keywords_and_negated_motion_are_not_ambient(text):
    with patch("core.features.on", return_value=True):
        assert pf.ambient_issues(text,{})


def test_progressive_ambient():
    with patch("core.features.on", return_value=True):
        assert not pf.ambient_issues("Fog drifting gently in the background.",{})


@pytest.mark.parametrize("text", ["Static camera while fog drifts gently.", "She remains still as leaves sway."])
def test_static_camera_or_person_does_not_negate_background(text):
    with patch("core.features.on", return_value=True):
        assert not pf.ambient_issues(text,{})


def test_dependency_when_formula_off(monkeypatch):
    monkeypatch.setenv("FEATURE_AMBIENT_MOTION", "1")
    monkeypatch.setenv("FEATURE_PROMPT_FORMULA", "0")
    assert features.unmet("ambient_motion") == ["prompt_formula"]
    assert not pf.enabled()


def test_yellow_is_not_red_or_blocker():
    with patch("core.features.on", return_value=True):
        result=pf.review_shot({},None,"The clip starts on the first frame. Static camera. She holds her pose.", ff=False)
    assert any(i["part"] == "chuyen_dong_nen" for i in result["motion"])
    assert result["red"] is False


def test_motion_payload_carries_real_byd_weather_and_time(monkeypatch):
    monkeypatch.setenv("FEATURE_AMBIENT_MOTION", "1")
    p=Pipeline(connect()); pid=p.create_project("ambient"); sid=p.create_scene(pid,1,"Sương mù")
    data={"location":"sân giếng", "weather":"trời lặng", "time":"đêm",
          "byd":{"noi_chon":{"thoi_tiet":"foggy","thoi_gian":"night"}}}
    try:
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?",(json.dumps(data),sid)); p.conn.commit()
        job=p.create_job(sid); p.start(job); p.succeed(job); p.approve(job)
        text=prompts.build_motion_bundle(p,pid)
        payload=json.loads(text.split("# Cảnh đã có ảnh được duyệt\n```json\n")[1].split("\n```")[0])
        assert payload["scenes"][0]["ambient_context"] == data
        assert "sương" in payload["scenes"][0]["ambient_hint"]
    finally:
        p.conn.close()
