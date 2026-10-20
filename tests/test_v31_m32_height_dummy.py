"""V3.1 M3.2 (C-M32, offline, G2-4): người nộm whitebox đúng `height_m` hồ sơ Kho + máy ở độ cao mắt (0,93 × height_m) và pitch `eye` (≤ 5°) /
`slightly_high` (cúi 8–12°). Cờ `world_map_height_dummy` TẮT = whitebox cũ y nguyên (EYE 1,6 m, khối 1,8 m, nhắm ngực 1,2 m). Hàm hình học
thuần + script Blender nhận tham số (không chạy Blender trong test)."""
import inspect
import json
import math
import os
from unittest import mock

import pytest

from core import whitebox as W

ON = mock.patch.dict(os.environ, {"FEATURE_WORLD_MAP_HEIGHT_DUMMY": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_WORLD_MAP_HEIGHT_DUMMY": ""})
M3D = {"path": "x.fbx", "spots": {"front": {"at": [0.0, 0.0, 2.0]}}}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_flag_registered_and_off():
    from core import features
    assert W.DUMMY_FLAG in features.FEATURES
    with OFF:
        assert not W.dummy_enabled()


def test_registered_in_areas():
    areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))
    a = next(x for x in areas["areas"] if "core/whitebox.py" in x["code"])
    assert "tests/test_v31_m32_height_dummy.py" in a["tests"] and W.DUMMY_FLAG in a["flags"]


def test_eye_height_is_share_of_body():
    assert W.eye_height(1.75) == pytest.approx(1.6275)
    with pytest.raises(W.WhiteboxError):
        W.eye_height(0)


def test_pitch_eye_is_level_and_slightly_high_looks_down_10():
    eye = W.pitch_camera(feet_z=2.0, height_m=1.7, dist=4.0, angle="eye")
    assert eye["pitch_deg"] == pytest.approx(0.0) and eye["location_z"] == pytest.approx(2.0 + 0.93 * 1.7)
    hi = W.pitch_camera(feet_z=2.0, height_m=1.7, dist=4.0, angle="slightly_high")
    assert hi["pitch_deg"] == pytest.approx(-W.SLIGHTLY_HIGH_DEG) and 8 <= W.SLIGHTLY_HIGH_DEG <= 12
    assert hi["aim_z"] == pytest.approx(eye["aim_z"])                         # nhìn cùng mắt nhân vật, máy nâng lên
    assert hi["location_z"] == pytest.approx(eye["aim_z"] + 4.0 * math.tan(math.radians(W.SLIGHTLY_HIGH_DEG)))
    with pytest.raises(W.WhiteboxError):
        W.pitch_camera(2.0, 1.7, 4.0, angle="dutch")


def test_pitch_note_g3():
    assert W.pitch_note("eye", 3.0) is None and W.pitch_note("eye", -4.9) is None
    assert "17" in W.pitch_note("eye", 17.3)                                   # #31 shot 28 pitch +17.3 khai eye → VÀNG
    assert W.pitch_note("slightly_high", -10.0) is None
    assert W.pitch_note("slightly_high", -20.0)
    assert W.pitch_note("high", -30.0) is None                                 # mức khác: không phải việc của hàm này


def test_flag_off_is_the_old_whitebox():
    with OFF:
        anim = W.plan(M3D, "front", [{"name": "KENTA", "at": [8, 0]}], heights={"KENTA": 1.5}, angle="slightly_high")
    assert anim["keys"][0]["location"][2] == 2.0 + W.EYE and anim["keys"][0]["look_at"][2] == 3.2
    assert anim["actors"][0]["height"] == 1.8 and "eye_m" not in anim["actors"][0] and not anim.get("warnings")


def test_flag_on_uses_profile_heights_and_eye_camera():
    with ON:
        anim = W.plan(M3D, "front", [{"name": "KENTA", "at": [8, 0]}, {"name": "ORION", "at": [8, 2]}],
                      heights={"KENTA": 1.6, "ORION": 1.8})
    k, o = anim["actors"]
    assert (k["height"], o["height"]) == (1.6, 1.8)
    assert k["eye_m"] == pytest.approx(0.93 * 1.6)
    cam = anim["keys"][0]
    assert cam["location"][2] == pytest.approx(2.0 + 0.93 * 1.7)              # mắt của nhóm (trung bình)
    assert cam["look_at"][2] == pytest.approx(cam["location"][2])             # eye: máy ngang
    assert not anim.get("warnings")


def test_flag_on_slightly_high_looks_down():
    with ON:
        anim = W.plan(M3D, "front", [{"name": "KENTA", "at": [8, 0]}], heights={"KENTA": 1.7}, angle="slightly_high")
    loc, aim = anim["keys"][0]["location"], anim["keys"][0]["look_at"]
    pitch = math.degrees(math.atan2(aim[2] - loc[2], math.hypot(aim[0] - loc[0], aim[1] - loc[1])))
    assert pitch == pytest.approx(-W.SLIGHTLY_HIGH_DEG, abs=0.05)
    assert W.pitch_note("slightly_high", pitch) is None


def test_missing_height_is_said_not_silent():
    with ON:
        anim = W.plan(M3D, "front", [{"name": "KENTA", "at": [8, 0]}], heights={})
    assert anim["actors"][0]["height"] == 1.8                                 # khối vẫn dựng được
    assert any("KENTA" in w and "height_m" in w for w in anim["warnings"])


def test_explicit_height_wins():
    with ON:
        anim = W.plan(M3D, "front", [{"name": "KENTA", "at": [8, 0], "height": 1.2}], heights={"KENTA": 1.7})
    assert anim["actors"][0]["height"] == 1.2 and not anim.get("warnings")


def test_heights_of_reads_the_approved_profile():
    with mock.patch("core.assets.standard_for", side_effect=lambda c, pid, n: {"height_m": 1.65} if n == "KELLY" else None):
        got, missing = W.heights_of(object(), 7, ["KELLY", "SKORP"])
    assert got == {"KELLY": 1.65} and missing == ["SKORP"]


def test_blender_script_reads_height_and_eye():
    src = open(os.path.join(ROOT, "tools", "render_plates.py"), encoding="utf-8").read()
    start = src.index("def add_actor(")
    body = src[start:src.index("\ndef ", start + 1)]
    assert 'actor.get("height", 1.8)' in body and 'actor.get("eye_m")' in body
