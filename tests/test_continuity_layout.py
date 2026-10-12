"""Hộp thư 12/10 15:51 (người dùng: "hướng đi của nhân vật và bố cục của cảnh cần nhất quán"), cờ continuity_layout: ca #27 dựng lại
từ mô tả — hướng ghi trong image_prompt/blocking không được kiểm; shot 3→4 đi ngược chiều vào cổng; cổng đổi bên khi quay lại cùng chỗ;
đồng đội nằm biến mất ở shot sau cùng chỗ. Không gọi API."""
import os
from unittest import mock

from core import continuity

ON = {"FEATURE_CONTINUITY_LAYOUT": "1"}
OFF = {"FEATURE_CONTINUITY_LAYOUT": "0"}


def s(prompt, chars=("KELLY",), **kw):
    return dict({"image_prompt": prompt, "characters": list(chars), "angle": "eye", "camera_move": "static"}, **kw)


def run(plan, env=ON):
    with mock.patch.dict(os.environ, env):
        return continuity.layout_warnings(plan), continuity.axis_warnings(plan)


def test_sides_written_in_image_prompt_are_checked_now():
    plan = [(1, 1, s("Kelly frame-left, Kenta frame-right, facing each other", chars=("KELLY", "KENTA"))),
            (1, 2, s("Kenta on the left, Kelly on the right", chars=("KELLY", "KENTA")))]
    assert run(plan)[1] and "đổi bên" in run(plan)[1][0]
    assert not [w for w in run(plan, OFF)[1] if "đổi bên" in w]          # off: the old reading (start_frame only) — nothing to check


def test_walking_into_the_same_gate_from_behind_then_facing_camera_is_flagged():
    plan = [(1, 3, s("Camera behind Kelly as she walks into the torii gate.", plate_spot="cong")),
            (1, 4, s("Kelly walks into the torii gate, facing camera.", plate_spot="cong"))]
    lay = run(plan)[0]
    assert any("đi ngược chiều" in w and "1·4" in w for w in lay), lay
    same = [(1, 3, plan[0][2]), (1, 4, s("Camera behind Kelly, she walks into the torii gate.", plate_spot="cong"))]
    assert not any("đi ngược chiều" in w for w in run(same)[0])


def test_walking_into_something_without_camera_side_is_said():
    lay = run([(1, 1, s("Kelly walks toward the gate."))])[0]
    assert lay and "không ghi máy" in lay[0]


def test_a_fixed_thing_keeps_its_side_in_every_shot_of_the_place_even_scenes_apart():
    plan = [(1, 1, s("Camera behind Kelly. The torii gate is on the left, the glue wall on the right.", plate_spot="san_cong")),
            (3, 1, s("Kelly at the well.", plate_spot="gieng")),
            (6, 2, s("Camera behind Kelly. The torii gate is on the right.", plate_spot="san_cong"))]
    lay = run(plan)[0]
    assert any("'gate'" in w and "6·2" in w and "1·1" in w for w in lay), lay
    turned = [plan[0], (6, 2, s("Kelly faces camera. The torii gate is on the right.", plate_spot="san_cong"))]
    assert not any("'gate'" in w for w in run(turned)[0])               # camera turned round: the sides flip on purpose


def test_someone_lying_there_vanishing_from_the_next_shot_of_the_same_place_is_flagged():
    plan = [(2, 1, s("Kenta lies unconscious by the wall while Kelly kneels.", chars=("KELLY", "KENTA"), plate_spot="tuong")),
            (2, 2, s("Kelly stands up and reloads.", plate_spot="tuong"))]
    lay = run(plan)[0]
    assert any("KENTA" in w and "biến mất" in w for w in lay), lay
    elsewhere = [plan[0], (2, 2, s("Kelly stands up and reloads.", plate_spot="cong"))]
    assert not any("biến mất" in w for w in run(elsewhere)[0])


def test_flag_off_says_nothing():
    plan = [(1, 1, s("Kelly walks toward the gate."))]
    assert run(plan, OFF)[0] == []
