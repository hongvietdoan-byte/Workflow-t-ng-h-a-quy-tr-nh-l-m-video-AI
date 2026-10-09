"""V4 Sân khấu 3D: shot có `stage_camera` (máy đã giải + duyệt) dùng NGUYÊN máy đó khi cờ stage_camera bật; cờ tắt → như cũ."""
from core import features, plate_camera


def shots():
    sc = {"location": [1.0, -3.0, 1.2], "look_at": [0.0, 0.0, 1.0], "lens": 24, "source": "test", "pov": "kelly"}
    return [{"id": 1, "data": {"size": "MS", "camera_setup": "A", "story_scene": 1, "stage_camera": sc}},
            {"id": 2, "data": {"size": "MS", "camera_setup": "A", "story_scene": 1}}]


def spot_of(s):
    return ([0.0, 0.0, 0.0], 0.0)


def test_stage_field_uses_locked_camera_and_never_groups():
    out = plate_camera.plan_cameras(shots(), spot_of, lambda s: 1.7, 9 / 16, stage_field=plate_camera.STAGE_FIELD)
    c1 = out[1]["camera"]
    assert c1["location"] == [1.0, -3.0, 1.2] and c1["look_at"] == [0.0, 0.0, 1.0] and c1["lens"] == 24 and c1["locked"]
    assert "pov" in out[1]["why"] and not out[1]["fixes"]
    assert "shared_with" not in out[2]                    # shot 2 cùng setup A KHÔNG mượn máy của shot có stage_camera


def test_flag_off_keeps_old_camera():
    out = plate_camera.plan_cameras(shots(), spot_of, lambda s: 1.7, 9 / 16)
    assert not out[1]["camera"].get("locked") and out[1]["camera"]["location"] != [1.0, -3.0, 1.2]


def test_flag_declared_off_by_default():
    assert "stage_camera" in features.FEATURES and not features.FEATURES["stage_camera"]["verified"]
