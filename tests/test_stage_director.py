"""Sân khấu 3D V3 (core/stage_director): kiểm câu trả lời của Director, câu gửi lại khi chưa đạt, so với bản viết tay — không gọi Claude."""
import copy
import json
import os

import pytest

from core import llm_io, llm_runner, cost
from core import stage_director as sd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "tools", "experiments", "stage_v2_p24")
MARKS = {"thap_chan": {"xyz": [0.0, 16.04, -0.34]}, "thap_dinh": {"xyz": [0.0, 16.04, 38.11]},
         "thap_object": {"name": "CLK_OUT_Tower001_LOD0_plan", "bbox_size_m": [9.35, 9.35, 38.46]}}


def inputs():
    inp = json.load(open(os.path.join(D, "v3_inputs.json"), encoding="utf-8"))
    inp["shots"] = [{"shot": k, "action": f"hành động {k}"} for k in range(1, 10)]
    return inp


def hand_answer():
    bl = json.load(open(os.path.join(D, "blocking.json"), encoding="utf-8"))
    sp = json.load(open(os.path.join(D, "shot_specs.json"), encoding="utf-8"))["shots"]
    return {"blocking": bl, "shot_specs": sp}


def test_hand_written_answer_is_valid():
    sd.validate_answer(hand_answer(), inputs(), MARKS)


def test_bad_answers_raise_schema_error_with_reason():
    a = hand_answer()
    a["shot_specs"] = a["shot_specs"][:8]
    with pytest.raises(llm_io.SchemaError, match="đúng các shot"):
        sd.validate_answer(a, inputs(), MARKS)
    a = hand_answer()
    next(o for o in a["blocking"]["objects"] if o["key"] == "gieng")["at"] = [0.0, 3.0]   # vật cố định bị dời
    with pytest.raises(llm_io.SchemaError, match="đổi vị trí"):
        sd.validate_answer(a, inputs(), MARKS)
    a = hand_answer()
    a["shot_specs"][0]["thanh_phan"][0]["vat"] = "ma"
    with pytest.raises(llm_io.SchemaError, match="không có trong dàn cảnh"):
        sd.validate_answer(a, inputs(), MARKS)
    a = hand_answer()
    a["shot_specs"][5]["may"] = {"kieu": "xoay", "m": 1}
    with pytest.raises(llm_io.SchemaError, match="chưa hỗ trợ"):
        sd.validate_answer(a, inputs(), MARKS)
    with pytest.raises(llm_io.SchemaError):
        sd.validate_answer({"x": 1}, inputs(), MARKS)


def test_prompt_has_facts_and_no_hand_answer():
    t = sd.build_prompt(inputs())
    assert "Không có quy định nào bắt phải thấy" in t and "Giếng" in t and "shot 9" in t
    assert "bam_mep" not in t and "\"cao_m\": 0.5" not in t and "[0.043, -0.246]" not in t   # không lộ đáp án viết tay
    t2 = sd.build_prompt(inputs(), prev={"a": 1}, feedback=["shot 3: S1 giếng 33 %"])
    assert "Lượt sửa" in t2 and "shot 3: S1 giếng 33 %" in t2


def test_feedback_prefers_blender_then_solver_advice():
    v2 = {"shots": [{"shot": 3, "best": {"ok": False, "tag": "giải", "check": {"why": {"S1": "Giếng thấy 33%"}}}},
                    {"shot": 4, "best": {"ok": True, "tag": "x", "check": {"why": {}}}}]}
    solve = {"shots": [{"shot": 3, "advice": ["không dùng"]}, {"shot": 5, "errors": ["thiếu ý đồ hướng"]}, {"shot": 4, "advice": []}]}
    fb = sd.feedback_from(solve, v2)
    assert len(fb) == 2 and "Giếng thấy 33%" in fb[0] and "thiếu ý đồ hướng" in fb[1]


def test_compare_rows():
    best = {"ok": True, "check": {"why": {}}, "m": {"at": [0, 0, 1], "yaw": 350, "pitch": -5, "cell": "K10"}}
    spec = {"thanh_phan": [{"vat": "kelly", "vai": "chinh"}]}
    hand = {"shots": [{"shot": 1, "spec": spec, "best": best}]}
    ai = {"shots": [{"shot": 1, "spec": dict(spec, pov="kelly"), "best": dict(best, m=dict(best["m"], at=[3, 4, 1], yaw=10))}]}
    r = sd.compare(hand, ai)[0]
    assert r["cam_dist_m"] == 5.0 and r["yaw_diff"] == 20.0 and r["ai_extra"] == {"pov": "kelly"} and r["ai_ok"] and r["hand_ok"]


def test_stage_has_own_token_cap_and_estimate():
    assert llm_runner.stage_settings(sd.STAGE)["max_tokens"] >= 16000      # G0 09/10: trần 8000 cắt câu trả lời
    assert sd.STAGE in cost.LLM_STAGE_TOKENS


def test_person_overlapping_well_must_declare_in():
    a = hand_answer()
    a["blocking"]["beats"]["bo"]["yeunu"] = {"at": [-0.278, 0.85], "facing": 170, "H": 0.6}     # sát thành giếng, không khai in
    with pytest.raises(llm_io.SchemaError, match="chồng lên"):
        sd.validate_answer(a, inputs(), MARKS)


def test_lying_person_without_facing_is_schema_error_not_solver_crash():
    """Rà 10/10 lỗi 1: người nằm / ngã ngửa thiếu facing phải bị trả lại Đạo diễn (SchemaError) lúc kiểm, không nổ ValueError lúc giải."""
    from core import stage_solver as ss
    a = hand_answer()
    kelly = next(o for o in a["blocking"]["objects"] if o["key"] == "kelly")
    kelly["tu_the"] = "nam"
    kelly.pop("facing")
    with pytest.raises(llm_io.SchemaError, match="cần facing"):
        sd.validate_answer(a, inputs(), MARKS)
    kelly["facing"] = 350                                   # có facing → giải được, không ném ra ngoài
    res = ss.solve_scene(a["shot_specs"][:1], a["blocking"], 9 / 16, MARKS)
    assert len(res["shots"]) == 1


def test_pose_outside_enum_is_schema_error_not_silent_standing():
    """Rà Đợt 2 (prompt 29 mở nga_ngua/nam): tư thế ngoài TU_THE (vd 'nga') trước đây bị giải im lặng như người đứng."""
    a = hand_answer()
    next(o for o in a["blocking"]["objects"] if o["key"] == "kelly")["tu_the"] = "nga"
    with pytest.raises(llm_io.SchemaError, match="tu_the"):
        sd.validate_answer(a, inputs(), MARKS)
    a = hand_answer()
    a["blocking"]["beats"]["bo"].setdefault("kelly", {})["tu_the"] = "lying"
    with pytest.raises(llm_io.SchemaError, match="tu_the"):
        sd.validate_answer(a, inputs(), MARKS)
