"""DP11 — V3.1 M3.3 câu vị trí sinh từ world map (G41–G50, gốc P31-G46): CHỈ ĐỀ XUẤT + so câu hiện tại (REVIEW), cờ world_map_sentences
TẮT, không đổi prompt gửi đi. Fixture tổng hợp theo #31 (cảnh 4 mê cung 3D, cảnh 6 xác bay chỉ BYĐ). Thiết kế M3 mục 4."""
import os
from unittest import mock

from core import world_map as W
from tests.test_v31_dp8_world_map import BYD_C6, _stage

ON = mock.patch.dict(os.environ, {"FEATURE_WORLD_MAP": "1", "FEATURE_WORLD_MAP_SENTENCES": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_WORLD_MAP": "1", "FEATURE_WORLD_MAP_SENTENCES": ""})
# stage_camera ở tọa độ MODEL; gốc O của fixture = model [10, 5, 0] → máy đứng O + (-5, 0) nhìn về Đông (x+): phải khung = phía Nam (y−)
CAM_EAST = {"location": [5.0, 5.0, 1.6], "look_at": [15.0, 5.0, 1.6]}


def test_scene4_3d_sides_follow_the_camera(tmp_path):
    k1, seg = _stage(tmp_path)
    m = W.build(4, k1_dir=k1, seg_dir=seg)
    text, prov = W.position_sentence(m, 13, CAM_EAST)
    assert prov["placed"] == {"kelly": "centre", "rao": "centre", "dich1": "left", "thap": "left"}
    assert text.startswith("KELLY at frame centre") and "LÍNH ĐỊCH at frame left" in text and "tháp in the distance at frame left" in text
    _, back = W.position_sentence(m, 13, {"location": [25.0, 5.0, 1.6], "look_at": [35.0, 5.0, 1.6]})   # máy vượt qua mọi thứ
    assert back.get("out_of_frame") and "why" in back


def test_the_farther_one_on_the_same_side_is_behind(tmp_path):
    """G43: 'xác ở nền SAU LƯNG Kelly' — cùng phía khung, xa hơn ≥ 1,5 m."""
    bl = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0.0, 1.5], "H": 1.68, "label": "KELLY"},
                      {"key": "xac", "kind": "nguoi", "at": [4.0, 2.5], "H": 1.8, "label": "XÁC"}]}
    k1, seg = _stage(tmp_path, bl, None)
    text, _ = W.position_sentence(W.build(6, k1_dir=k1, seg_dir=seg), 26, CAM_EAST)
    assert text == "KELLY at frame left; XÁC at frame left, behind KELLY."


def test_relative_map_from_byd():
    text, prov = W.position_sentence(W.build(6, byd=BYD_C6), 26)
    assert text == "KELLY at frame left of XAC; KELLY holding AWM." and prov["placed"] == {"KELLY": "left", "XAC": "right"}
    assert W.position_sentence(W.build(6, byd=BYD_C6), 27)[0] == "KELLY holding AWM."


def test_no_guessing_without_map_or_camera(tmp_path):
    assert W.position_sentence(W.build(8), 34)[0] is None
    k1, seg = _stage(tmp_path)
    text, prov = W.position_sentence(W.build(4, k1_dir=k1, seg_dir=seg), 13, None)
    assert text is None and "máy" in prov["why"]
    assert W.position_sentence(dict(W.build(6, byd=BYD_C6), invalidated={"why": "byd_changed"}), 26)[0] is None


def test_review_flags_a_text_that_says_the_opposite_side():
    m = W.build(6, byd=BYD_C6)
    with ON:
        res = W.review(m, 26, "XAC floats on the left of the frame while Kelly crouches on the right")
        ok = W.review(m, 26, "Kelly on the left, XAC on the right")
    assert res["level"] == "REVIEW" and res["suggested"].startswith("KELLY at frame left")
    assert {x["entity"] for x in res["mismatches"]} == {"KELLY", "XAC"}
    assert ok["mismatches"] == []


def test_flag_off_review_does_nothing():
    with OFF:
        assert W.review(W.build(6, byd=BYD_C6), 26, "anything") is None
