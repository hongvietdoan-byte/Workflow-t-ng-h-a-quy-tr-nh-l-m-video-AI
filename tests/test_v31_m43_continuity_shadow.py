"""V3.1 M4.3 (C-M43): logic xuyên shot SHADOW — vật cầm / dạng / hướng đi trên khung giữa 2 shot liền; đồ thị phụ thuộc; nối kết quả QC
logic chuỗi (Claude) thành 'cần xem'. Không gọi model, 0 USD, không chặn gì."""
import json
import os
from unittest import mock

from core import continuity_shadow as C


def _row(idx, seq="1", cast=("KELLY",), vat=None, action="", motion=""):
    data = {"characters": list(cast), "action": action}
    if vat is not None:
        data["byd"] = {"vat": vat}
    return {"idx": idx, "sequence": seq, "data": data, "motion": motion}


GUN = [{"vat": "AWM", "nguoi": "KELLY", "cach": "cam"}]


def test_flag_is_off_by_default():
    from core import features
    assert C.FLAG in features.FEATURES
    with mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_SHADOW": ""}):
        assert not C.enabled()


def test_held_gun_vanishing_in_the_next_shot_is_reported():
    res = C.build([_row(28, vat=GUN), _row(29, vat=[])])
    assert [f["evidence"]["attribute"] for f in res["findings"]] == ["cam"]
    f = res["findings"][0]
    assert f["severity"] == "REVIEW" and f["qc_code"] == "QC-L13-CONTINUITY" and "P31-G51" in f["registry_ids"]
    assert f["evidence"]["shots"] == [28, 29]


def test_kept_gun_is_an_edge_not_a_finding():
    res = C.build([_row(28, vat=GUN), _row(29, vat=GUN)])
    assert res["findings"] == [] and res["edges"] == [{"from": 28, "to": 29, "entity": "KELLY", "attribute": "cam", "value": "AWM"}]


def test_dropping_said_in_words_is_not_a_finding():
    res = C.build([_row(28, vat=GUN), _row(29, vat=[], action="Kelly drops the rifle and runs")])
    assert res["findings"] == []


def test_v1_strings_or_missing_byd_are_never_guessed():
    assert C.build([_row(1, vat=["AWM"]), _row(2, vat=[])])["findings"] == []          # v1: không biết ai cầm
    res = C.build([_row(1, vat=GUN), _row(2)])                                           # shot sau chưa có BYĐ
    assert res["findings"] == [] and res["unknown"] and res["unknown"][0]["shots"] == [1, 2]


def test_other_sequence_or_absent_character_has_no_expectation():
    assert C.build([_row(1, vat=GUN), _row(2, seq="2", vat=[])])["findings"] == []
    assert C.build([_row(1, vat=GUN), _row(2, cast=("SKORP",), vat=[])])["findings"] == []


def test_form_change_is_review_unless_the_words_say_why():
    forms = {1: {"KELLY": "ghost form"}, 2: {}}
    rows = [_row(1), _row(2)]
    got = C.build(rows, lambda d: forms[1] if d is rows[0]["data"] else forms[2])
    assert [f["evidence"]["attribute"] for f in got["findings"]] == ["dang"]
    rows[1]["data"]["action"] = "Kelly returns to reality, the ghost form fades"
    assert C.build(rows, lambda d: forms[1] if d is rows[0]["data"] else forms[2])["findings"] == []


def test_screen_direction_flip_without_a_turn():
    a = _row(36, motion="Kelly runs from left to right across the yard")
    b = _row(37, motion="Kelly runs towards frame-left, panicked")
    got = C.build([a, b])
    assert [f["evidence"]["attribute"] for f in got["findings"]] == ["huong_khung"] and "P31-G41" in got["findings"][0]["registry_ids"]
    b["motion"] = "Kelly turns around and runs towards frame-left"
    assert C.build([a, b])["findings"] == []


def test_direction_is_never_guessed():
    assert C.direction("Kelly runs to the left") is None                 # trái của ai? không đọc
    assert C.direction("from left to right, then from right to left") is None
    assert C.direction("moves towards frame-right") == "ltr"
    two = C.build([_row(1, cast=("KELLY", "SKORP"), motion="runs from left to right"),
                   _row(2, cast=("KELLY", "SKORP"), motion="runs from right to left")])
    assert two["findings"] == []                                         # hai người: hướng của ai không rõ


def test_dependents_follow_edges():
    edges = [{"from": 1, "to": 2}, {"from": 2, "to": 3}, {"from": 5, "to": 6}]
    assert C.dependents(edges, 1) == [2, 3] and C.dependents(edges, 3) == []


def test_claude_issues_become_findings():
    res = {"sequences": {"4": {"ok": False, "issues": [{"idx": 10, "problem": "nhặt súng trên thềm cỏ cao", "fix": "keep ground level"}]}}}
    obs = C.observed(res)
    assert obs[0]["evidence_type"] == "vlm" and obs[0]["evidence"]["shots"] == [10] and obs[0]["registry_ids"] == ["P31-G52"]
    assert C.observed(None) == [] and C.observed({"sequences": {"1": {"issues": ["bad"]}}}) == []


def _project(tmp_path):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("m43")
    for idx, vat, action in ((10, GUN, "Kelly aims"), (11, GUN, "Kelly walks"), (12, [], "Kelly looks around")):
        sid = p.create_scene(pid, idx, f"S{idx}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY"], "sequence": "4", "shot_no": idx,
                                                                            "action": action, "byd": {"vat": vat}}), sid))
    p.conn.commit()
    return p, pid


def test_run_flag_off_does_nothing(tmp_path):
    p, pid = _project(tmp_path)
    with mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_SHADOW": ""}):
        assert C.run(p, pid, str(tmp_path)) is None
    assert not os.path.exists(C.result_path(str(tmp_path), pid))


def test_run_flag_on_writes_graph_findings_and_shots_to_look_at(tmp_path):
    p, pid = _project(tmp_path)
    claude = {"sequences": {"4": {"issues": [{"idx": 10, "problem": "độ cao nền đổi", "fix": "x"}]}}}
    with mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_SHADOW": "1"}):
        rec = C.run(p, pid, str(tmp_path), claude)
    assert rec["mode"] == "shadow"
    assert [f["evidence"]["shots"] for f in rec["expected"]] == [[11, 12]]          # súng mất ở 12
    assert rec["can_xem"] == {"11": [10]}                                          # 11 phụ thuộc 10 (cùng cầm AWM)
    assert json.load(open(C.result_path(str(tmp_path), pid), encoding="utf-8"))["observed"]


def test_run_never_raises(tmp_path):
    p, pid = _project(tmp_path)
    with mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_SHADOW": "1"}), mock.patch.object(C, "build", side_effect=RuntimeError("x")):
        assert C.run(p, pid, str(tmp_path)) is None


def test_sequence_check_calls_the_shadow_after_its_own_result(tmp_path):
    from core import sequence_logic
    p, pid = _project(tmp_path)
    groups = {"4": {"rows": [{"idx": 10}, {"idx": 11}], "shown": {10, 11}, "sheets": []}}
    with mock.patch.dict(os.environ, {"FEATURE_QC_SEQUENCE_LOGIC": "1"}), \
         mock.patch.object(sequence_logic, "sequence_sheets", return_value=groups), \
         mock.patch.object(sequence_logic.claude_tasks, "_run", return_value={"ok": True, "issues": []}), \
         mock.patch.object(sequence_logic.prompts, "world_bible_text", return_value=""), \
         mock.patch.object(C, "run") as shadow:
        out = sequence_logic.check(p, pid, object(), str(tmp_path))
    assert out["ok"] is True and shadow.call_count == 1 and shadow.call_args.args[3] is out
