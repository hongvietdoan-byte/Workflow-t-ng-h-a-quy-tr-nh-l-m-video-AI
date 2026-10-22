"""Hợp đồng core/layout_facts (người dùng 22/10: một nguồn sự thật bố cục cho C-3D-GOC-A / C-3D-GOC-B / C-QC-BOCUC).
Đổi khóa / kiểu ở đây = tăng layout_facts.VERSION + báo hộp thư cho hai gói kia."""
import json

import pytest

from core import layout_facts as lf
from core.db import connect
from core.pipeline import Pipeline
from tests import golden

KEYS = {"version", "scene_id", "story_scene", "spot", "mates", "anchor_scene_id", "ref_scene_id", "camera", "people", "landmarks",
        "positions", "horizon", "missing", "provenance"}
CAMERA_KEYS = {"source", "pos", "aim", "yaw_deg", "pitch_deg", "lens_mm", "height_m", "setup", "angle", "size"}
PERSON_KEYS = {"name", "side", "source", "height_pct", "dist_m"}
HORIZON_KEYS = {"plate_row", "image_row", "mismatch", "measured", "reasons", "job_id"}


def stage(look_y=10.0, x=0.0):
    return {"location": [x, 0.0, 1.6], "look_at": [x, look_y, 1.6], "lens": 35, "props": []}


def project(shots):
    """shots: [(size, spot, extra dict)] — một cảnh truyện, shot_no theo thứ tự."""
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("lf")
    ids = []
    for i, (size, spot, extra) in enumerate(shots, 1):
        sid = p.create_scene(pid, i, f"shot {i}")
        d = {"story_scene": 1, "shot_no": i, "size": size, "plate_spot": spot, "characters": ["KELLY"], "image_prompt": "x"}
        d.update(extra or {})
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        ids.append(sid)
    p.conn.commit()
    return p, pid, ids


@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setenv("FEATURE_STORYBOARD_API", "1")
    monkeypatch.setenv("FEATURE_ANCHOR_BY_SPOT", "1")
    monkeypatch.setenv("FEATURE_STAGE_CAMERA", "1")


def test_contract_keys_and_version(tmp_path):
    p, pid, ids = project([("WS", "a", {}), ("MS", "b", {}), ("CU", "b", {})])
    f = lf.facts_for_shot(p.conn, pid, ids[1], str(tmp_path))
    assert set(f) == KEYS and f["version"] == lf.VERSION == 1
    assert set(f["camera"]) == CAMERA_KEYS and set(f["horizon"]) == HORIZON_KEYS
    assert f["people"] and set(f["people"][0]) == PERSON_KEYS
    assert f["positions"] == {} and isinstance(f["landmarks"], list)


def test_missing_says_why_instead_of_guessing(tmp_path):
    p, pid, ids = project([("WS", "", {})])
    f = lf.facts_for_shot(p.conn, pid, ids[0], str(tmp_path))
    text = " ".join(f["missing"])
    assert f["spot"] is None and "plate_spot" in text
    assert f["camera"]["source"] == "none" and "chưa có máy" in text
    assert "world_map" in text and "R2" in text and "R3" in text
    assert f["people"][0]["side"] == "unknown"


def test_spot_mates_and_widest_reference(tmp_path):
    p, pid, ids = project([("WS", "a", {}), ("MS", "b", {}), ("WS", "b", {}), ("CU", "b", {})])
    f = lf.facts_for_shot(p.conn, pid, ids[3], str(tmp_path))
    assert f["spot"] == "b" and sorted(f["mates"]) == [ids[1], ids[2]]
    assert f["ref_scene_id"] == ids[2]                      # rộng nhất tại chỗ b, không phải shot WS ở chỗ a
    assert lf.facts_for_shot(p.conn, pid, ids[2], str(tmp_path))["ref_scene_id"] is None   # chính là shot rộng nhất


def test_stage_camera_yaw_pitch_height(tmp_path):
    p, pid, ids = project([("WS", "a", {"stage_camera": stage()})])
    cam = lf.facts_for_shot(p.conn, pid, ids[0], str(tmp_path))["camera"]
    assert cam["source"] == "stage_camera" and cam["yaw_deg"] == 90.0 and cam["height_m"] == 1.6
    assert abs(cam["pitch_deg"]) < 0.5 and cam["lens_mm"] == 35


@pytest.mark.parametrize("a, b, want", [
    ({"stage_camera": stage(10)}, {"stage_camera": stage(10, x=2.0)}, True),
    ({"stage_camera": stage(10)}, {"stage_camera": stage(-10)}, False),              # ngược trục: trái/phải đổi
    ({"camera_setup": "A1"}, {"camera_setup": "A1"}, True),
    ({"camera_setup": "A1"}, {"camera_setup": "B2"}, None),                           # khác tên góc máy: không biết, không đoán
    ({}, {}, None),
])
def test_same_view(tmp_path, a, b, want):
    p, pid, ids = project([("WS", "b", a), ("MS", "b", b)])
    fa, fb = (lf.facts_for_shot(p.conn, pid, i, str(tmp_path)) for i in ids)
    assert lf.same_view(fa, fb) is want


def test_expected_side_from_same_spot_reference(tmp_path):
    p, pid, ids = project([("WS", "b", {"camera_setup": "A1", "blocking": "KELLY stands frame-left by the wall"}),
                           ("MS", "b", {"camera_setup": "A1", "blocking": "KELLY aims"}),
                           ("CU", "b", {"camera_setup": "C3", "blocking": "KELLY breathes"})])
    got = lf.expected_side(p.conn, pid, ids[1], str(tmp_path), "KELLY")
    assert got["side"] == "left" and got["ref_scene_id"] == ids[0]
    other = lf.expected_side(p.conn, pid, ids[2], str(tmp_path), "KELLY")
    assert other["side"] is None and "phía trục" in other["why"]
    own = lf.expected_side(p.conn, pid, ids[0], str(tmp_path), "KELLY")
    assert own["side"] == "left" and own["ref_scene_id"] is None


def test_reverse_angle_never_copies_the_side(tmp_path):
    p, pid, ids = project([("WS", "b", {"stage_camera": stage(10), "blocking": "KELLY frame-right"}),
                           ("MS", "b", {"stage_camera": stage(-10), "blocking": "KELLY turns"})])
    got = lf.expected_side(p.conn, pid, ids[1], str(tmp_path), "KELLY")
    assert got["side"] is None and "ngược phía trục" in got["why"]


def test_horizon_reads_the_latest_plate_layout_record(tmp_path):
    p, pid, ids = project([("WS", "a", {"stage_camera": stage()})])
    d = tmp_path / str(pid)
    d.mkdir()
    (d / "plate_layout.json").write_text(json.dumps([
        {"job_id": 3, "scene_id": ids[0], "mismatch": False, "measured": True, "horizon_image": 0.4, "horizon_plate": 0.5},
        {"job_id": 9, "scene_id": ids[0], "mismatch": True, "measured": True, "horizon_image": 0.8, "reasons": ["chân trời lệch"]},
        {"job_id": 12, "scene_id": 999, "mismatch": False}]), encoding="utf-8")
    h = lf.facts_for_shot(p.conn, pid, ids[0], str(tmp_path))["horizon"]
    assert h["job_id"] == 9 and h["mismatch"] is True and h["image_row"] == 0.8 and h["reasons"] == ["chân trời lệch"]
    assert h["plate_row"] is not None                   # từ máy 3D (stage_facts.horizon), không từ bản ghi


def test_landmarks_come_from_stage_facts_not_a_second_formula(tmp_path):
    case = golden.stage_facts_cases()[0]
    p, pid, ids = project([("WS", "a", {"stage_camera": case["stage_camera"]})])
    f = lf.facts_for_shot(p.conn, pid, ids[0], str(tmp_path))
    from core import stage_facts
    want = [x for x in stage_facts.derive({"stage_camera": case["stage_camera"]}, render=False)["facts"] if x["kind"] == "in_frame"]
    assert len(f["landmarks"]) == len(want)
    assert all(l["source"] == "stage_facts" for l in f["landmarks"])


def test_side_in_blocking_matches_the_qc_reading():
    assert lf.side_in_blocking("KELLY crouches at frame-left, MAXIM frame right", "MAXIM") == "right"
    assert lf.side_in_blocking("KELLY stands frame-centre", "KELLY") == "center"
    assert lf.side_in_blocking("KELLY stands; frame-left is the wall", "KELLY") is None


def test_stage_camera_flag_off_ignores_old_coordinates(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_STAGE_CAMERA", "0")
    p, pid, ids = project([("WS", "a", {"stage_camera": stage(), "camera_setup": "A1"})])
    f = lf.facts_for_shot(p.conn, pid, ids[0], str(tmp_path))
    assert f["camera"]["source"] == "camera_plan" and f["camera"]["yaw_deg"] is None and f["horizon"]["plate_row"] is None
