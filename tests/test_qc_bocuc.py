"""C-QC-BOCUC (người dùng 14/10 qc-team-off: checklist Tổ QC phải có lỗi bố cục / chỗ đứng; 22/10 "làm đi" + "giữ liên kết chặt"):
mệnh đề bố cục đọc core/layout_facts (một nguồn), mức tối đa 'minor' (D07), học việc ghi 'flag' = giữ cho người."""
import json

import pytest

from core import qc_measure, qc_rules, qc_spec, qc_team, trainee
from core.db import connect
from core.pipeline import Pipeline


def stage(look_y=10.0):
    return {"location": [0.0, 0.0, 1.6], "look_at": [0.0, look_y, 1.6], "lens": 35, "props": []}


@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setenv("FEATURE_STORYBOARD_API", "1")
    monkeypatch.setenv("FEATURE_ANCHOR_BY_SPOT", "1")
    monkeypatch.setenv("FEATURE_STAGE_CAMERA", "1")


def project(shots):
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("bocuc")
    out = []
    for i, extra in enumerate(shots, 1):
        sid = p.create_scene(pid, i, f"shot {i}")
        d = {"story_scene": 1, "shot_no": i, "characters": ["KELLY"], "image_prompt": "x", "plate_spot": "b"}
        d.update(extra)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        out.append((sid, p.create_job(sid, "image_gen"), d))
    p.conn.commit()
    return p, pid, out


def spec(p, pid, shot, tmp_path):
    sid, job, d = shot
    return qc_spec.compile_frame(p.conn, pid, job, d, profiles={}, data_dir=str(tmp_path))


def test_same_spot_same_side_of_axis_gets_a_minor_layout_assertion(tmp_path):
    p, pid, s = project([{"size": "WS", "camera_setup": "A1", "blocking": "KELLY frame-left behind the wall"},
                         {"size": "MS", "camera_setup": "A1", "blocking": "KELLY aims"}])
    out = spec(p, pid, s[1], tmp_path)
    lay = [a for a in out["assertions"] if a["type"] == "layout"]
    assert len(lay) == 1 and lay[0]["expected"] == "left" and lay[0]["severity_if_false"] == "minor"
    assert lay[0]["source"] == "cung_cho:shot 1" and "cùng chỗ b" in lay[0]["claim_vi"]


def test_reverse_angle_or_unknown_axis_makes_no_side_claim_and_says_why(tmp_path):
    p, pid, s = project([{"size": "WS", "stage_camera": stage(10), "blocking": "KELLY frame-left"},
                         {"size": "MS", "stage_camera": stage(-10), "blocking": "KELLY turns"},
                         {"size": "CU", "camera_setup": "Z9", "blocking": "KELLY breathes"}])
    for shot, word in ((s[1], "ngược phía trục"), (s[2], "không biết")):
        out = spec(p, pid, shot, tmp_path)
        assert not [a for a in out["assertions"] if a["type"] == "layout"]
        assert any(word in w for w in out["layout_missing"])


def test_own_blocking_side_is_not_doubled(tmp_path):
    p, pid, s = project([{"size": "WS", "camera_setup": "A1", "blocking": "KELLY frame-left"},
                         {"size": "MS", "camera_setup": "A1", "blocking": "KELLY frame-right now"}])
    lay = [a for a in spec(p, pid, s[1], tmp_path)["assertions"] if a["type"] == "layout"]
    assert [a["expected"] for a in lay] == ["right"] and lay[0]["source"] == "blocking"


def test_background_vs_render_is_code_only_and_never_blocks(tmp_path):
    p, pid, s = project([{"size": "WS", "camera_setup": "A1"}])
    sid, job, d = s[0]
    (tmp_path / str(pid)).mkdir()
    (tmp_path / str(pid) / "plate_layout.json").write_text(json.dumps(
        [{"job_id": job, "scene_id": sid, "mismatch": True, "measured": True, "reasons": ["mảng phẳng che cảnh xa"]}]), encoding="utf-8")
    out = spec(p, pid, s[0], tmp_path)
    place = [a for a in out["assertions"] if a["type"] == "place"]
    assert len(place) == 1 and place[0]["how"] == "code" and place[0]["severity_if_false"] == "minor"
    code = qc_measure.measure_frame(str(tmp_path / "none.png"), d, out["assertions"])
    assert code[place[0]["id"]]["status"] == "certain_fail"
    v = qc_rules.frame_verdict([place[0]], {}, code)
    assert v["verdict"] == "minor" and v["fails"][0]["type"] == "place"


def test_no_record_for_this_job_is_said_not_guessed(tmp_path):
    p, pid, s = project([{"size": "WS", "camera_setup": "A1"}])
    out = spec(p, pid, s[0], tmp_path)
    assert not [a for a in out["assertions"] if a["type"] == "place"]
    assert any("plate_layout_qc" in w for w in out["layout_missing"])


def test_without_connection_nothing_changes():
    d = {"characters": ["KELLY"], "blocking": "KELLY aims", "size": "MS"}
    out = qc_spec.compile_frame(None, 1, 1, d, profiles={})
    assert "layout_missing" not in out and not [a for a in out["assertions"] if a["type"] in ("layout", "place")]


@pytest.mark.parametrize("boxes, cast, want, status", [
    ([(0.05, 0.2, 0.25, 0.4)], ["KELLY"], "left", "certain_ok"),
    ([(0.05, 0.2, 0.25, 0.4)], ["KELLY"], "right", "certain_fail"),
    ([(0.40, 0.2, 0.52, 0.4)], ["KELLY"], "left", "uncertain"),           # gần đường giữa: không chắc
    ([(0.60, 0.2, 0.75, 0.4)], ["KELLY"], "left", "certain_fail"),
    ([(0.44, 0.2, 0.58, 0.4)], ["KELLY"], "center", "certain_ok"),
    ([(0.05, 0.2, 0.15, 0.4)], ["KELLY"], "centre", "certain_fail"),
    ([(0.05, 0.2, 0.2, 0.4), (0.7, 0.2, 0.8, 0.4)], ["KELLY", "MAXIM"], "left", "not_measurable"),
    ([], ["KELLY"], "left", "not_measurable"),                            # quay lưng: không mặt
    (None, ["KELLY"], "left", "not_measurable"),
])
def test_layout_side_measure(boxes, cast, want, status):
    assert qc_measure._layout_side(boxes, cast, {"expected": want})["status"] == status


def test_trainee_records_flag_for_layout_fails_and_scores_it_as_reject():
    assert qc_team.decision_of({"verdict": "minor", "fails": [{"type": "place"}]}) == "flag"
    assert qc_team.decision_of({"verdict": "minor", "fails": [{"type": "gesture"}]}) == "pass"
    assert qc_team.decision_of({"verdict": "block", "fails": [{"type": "layout"}]}) == "block"
    assert trainee.RULES["qc_team"]["pred"]["flag"] == "reject"


def test_inferred_side_never_drives_gaze_to_a_block(tmp_path, monkeypatch):
    """Rà 22/10 (CAO): bên SUY từ shot cùng chỗ không được dùng chọn mặt cho hướng nhìn (có thoại = block)."""
    p, pid, s = project([{"size": "WS", "camera_setup": "A1", "characters": ["KELLY", "MAXIM"],
                          "blocking": "KELLY frame-left, MAXIM frame-right"},
                         {"size": "MS", "camera_setup": "A1", "characters": ["KELLY", "MAXIM"],
                          "blocking": "KELLY looking at MAXIM", "dialogue": [{"speaker": "KELLY", "text": "Go"}]}])
    out = spec(p, pid, s[1], tmp_path)
    assert {a["source"] for a in out["assertions"] if a["type"] == "layout"} == {"cung_cho:shot 1"}
    monkeypatch.setattr(qc_measure, "faces", lambda path: [(0.05, 0.2, 0.2, 0.4), (0.7, 0.2, 0.85, 0.4)])
    monkeypatch.setattr(qc_measure, "gaze", lambda path, box: {"side": "left", "confidence": "high"})
    monkeypatch.setattr(qc_measure, "sky", lambda path: None)
    code = qc_measure.measure_frame("x.png", s[1][2], out["assertions"])
    gaze = next(a for a in out["assertions"] if a["type"] == "gaze")
    assert code[gaze["id"]]["status"] == "not_measurable"         # như trước C-QC-BOCUC: hai mặt cỡ gần nhau, không biết của ai


def test_old_blocking_side_is_now_measured_by_code(monkeypatch):
    d = {"characters": ["KELLY"], "blocking": "KELLY stands frame-right", "size": "MS"}
    out = qc_spec.compile_frame(None, 1, 1, d, profiles={})
    lay = next(a for a in out["assertions"] if a["type"] == "layout")
    monkeypatch.setattr(qc_measure, "faces", lambda path: [(0.05, 0.2, 0.2, 0.4)])
    monkeypatch.setattr(qc_measure, "sky", lambda path: None)
    code = qc_measure.measure_frame("x.png", d, out["assertions"])
    assert code[lay["id"]]["status"] == "certain_fail"
    assert qc_rules.frame_verdict([lay], {}, code)["verdict"] == "minor"
