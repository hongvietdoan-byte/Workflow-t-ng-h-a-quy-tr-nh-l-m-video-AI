"""12/10 (#27, người dùng: "những cảnh có góc cam từ trên xuống vẫn bị lỗi tỉ lệ và bố cục, fix tận gốc"): the Free Fire third-person
camera was "head + 2.5 m" about 2.5 m away — ~50° down, the character 17 % of the render and drawn ~40 % by the model; an 'eye' EWS was
forced into a top view; a shot saying "camera BEHIND Kelly" was rendered from the front. No API call."""
from core import place_refs, plate_camera as pc
from core.plate_choice import is_behind


def test_game_tps_is_a_gentle_tilt_from_behind_not_a_top_view():
    r = pc.camera_for({"size": "GAME_TPS", "angle": "high"}, (0, 0, 0), 0.0, 1.7)
    assert r["behind"] is True
    assert -15.0 <= r["pitch_deg"] <= -8.0                       # a gentle tilt down, never ~50°
    assert r["distance_m"] >= pc.TPS_DIST_M - 1e-6
    x0, y0, x1, y1 = r["subject_box"]
    assert 0.2 <= y1 - y0 <= 0.4 and y1 <= 0.9 and y0 >= 0.4     # the whole body in the lower part of the frame
    assert 0.2 <= r["horizon_y"] <= 0.5


def test_eye_level_ews_is_not_forced_from_above_but_high_ews_is():
    eye = pc.camera_for({"size": "EWS", "angle": "eye"}, (0, 0, 0), 0.0, 1.7)
    high = pc.camera_for({"size": "EWS", "angle": "high"}, (0, 0, 0), 0.0, 1.7)
    assert abs(eye["pitch_deg"]) < 10.0
    assert high["pitch_deg"] < -20.0


def test_camera_behind_words_in_the_shot_put_the_camera_behind():
    assert is_behind({"blocking": "camera BEHIND Kelly; Kelly seen from behind, walking away"})
    assert is_behind({"size": "GAME_TPS"})
    assert not is_behind({"blocking": "Kelly faces the camera", "angle": "eye"})


def test_geometry_sentence_says_the_body_share():
    rec = {"subject_box": [0.42, 0.41, 0.58, 0.58], "distance_m": 2.7}
    s = place_refs.geometry_sentence(rec, {"characters": ["KELLY"]})
    assert "about 17% of the frame height" in s and "never bigger" in s and "main character" in s


def test_prop_lock_shot_text_skips_narration_lines():
    from core import prop_lock
    shot = {"image_prompt": "Kelly crouches to pick up a SKORP.", "text": "Kelly nhặt súng\nLỜI DẪN: bạn ném bom keo chắn tầm nhìn."}
    assert "bom keo" not in prop_lock.shot_text(shot) and "nhặt súng" in prop_lock.shot_text(shot)


def test_behind_words_negated_or_about_another_person_do_not_flip_the_camera():
    assert not is_behind({"blocking": "Kelly faces us, she is never seen from behind"})
    assert not is_behind({"blocking": "Maxim lies with his back to the camera, Kelly faces the camera"})


def test_tps_look_down_keeps_the_over_the_shoulder_rig_and_the_wide_view_backs_off_from_the_character():
    down = pc.camera_for({"size": "GAME_TPS", "angle": "high", "action": "Kelly looks down into the well"}, (0, 0, 0), 0.0, 1.7)
    assert "rig" not in down["camera"] and down["distance_m"] < pc.TPS_DIST_M
    tps = pc.camera_for({"size": "GAME_TPS", "angle": "high"}, (0, 0, 0), 0.0, 1.7)
    assert tps["camera"]["rig"] == "tps" and "tps" in tps["why"]
    w = pc.wide_for(tps["camera"], 1.7)
    assert abs(w["location"][1]) < 10.0 and w["location"][2] < 4.5      # not ~11 m back and 4 m up behind the far aim
