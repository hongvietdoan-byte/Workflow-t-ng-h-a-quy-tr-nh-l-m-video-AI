"""V3.1 M3.4 (C-M34): continuity_state SHADOW — expected (BYĐ) / observed (QC shadow M4.2 + M4.3) / resolved (người, C3-4 chưa có) giữa các
shot liền + đồ thị phụ thuộc. Mức REVIEW, không chặn, không gọi model, 0 USD. Cờ `continuity_state` TẮT = không dựng, không ghi gì.
Chuỗi 3 shot giả: vật mất / đổi tay / giữ đúng."""
import json
import os
from unittest import mock

from core import continuity_state as S

ON = mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_STATE": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_STATE": ""})


def _row(idx, cast=("KELLY",), vat=None, seq="1", action="", motion="", hanh_dong=None, noi=None):
    data = {"characters": list(cast), "action": action}
    byd = {}
    if vat is not None:
        byd["vat"] = vat
    if hanh_dong is not None:
        byd["hanh_dong"] = hanh_dong
    if noi is not None:
        byd["noi_chon"] = noi
    if byd:
        data["byd"] = byd
    return {"idx": idx, "sequence": seq, "data": data, "motion": motion}


def _gun(who="KELLY"):
    return [{"vat": "AWM", "nguoi": who, "cach": "cam"}]


def _attrs(res):
    return [(f["evidence"]["attribute"], f["evidence"].get("kind")) for f in res["findings"]]


def test_flag_registered_and_off():
    from core import features
    assert S.FLAG in features.FEATURES
    with OFF:
        assert not S.enabled()


def test_registered_in_areas():
    areas = json.load(open(os.path.join(os.path.dirname(__file__), "..", "devsys", "areas.json"), encoding="utf-8"))
    a = next(x for x in areas["areas"] if "core/continuity_state.py" in x["code"])
    assert "tests/test_v31_m34_continuity_state.py" in a["tests"] and S.FLAG in a["flags"]


def test_three_shots_kept_right_is_edges_only():
    res = S.build([_row(1, vat=_gun()), _row(2, vat=_gun()), _row(3, vat=_gun())])
    assert res["findings"] == []
    assert [(e["from"], e["to"], e["attribute"]) for e in res["edges"]] == [(1, 2, "cam"), (2, 3, "cam")]
    assert all(s["status"] == "khop" for s in res["states"] if s["attribute"] == "cam")


def test_three_shots_thing_lost():
    res = S.build([_row(1, vat=_gun()), _row(2, vat=_gun()), _row(3, vat=[])])
    assert _attrs(res) == [("cam", "mat")]
    f = res["findings"][0]
    assert f["severity"] == "REVIEW" and f["evidence"]["shots"] == [2, 3] and f["qc_code"] == "QC-L13-CONTINUITY"


def test_three_shots_changes_hands():
    rows = [_row(1, cast=("KELLY", "SKORP"), vat=_gun("KELLY")), _row(2, cast=("KELLY", "SKORP"), vat=_gun("KELLY")),
            _row(3, cast=("KELLY", "SKORP"), vat=_gun("SKORP"))]
    res = S.build(rows)
    assert _attrs(res) == [("cam", "doi_tay")]
    assert res["findings"][0]["evidence"]["before"] == "KELLY" and res["findings"][0]["evidence"]["after"] == "SKORP"


def test_handing_over_said_in_words_is_not_a_finding():
    rows = [_row(1, cast=("KELLY", "SKORP"), vat=_gun("KELLY")),
            _row(2, cast=("KELLY", "SKORP"), vat=_gun("SKORP"), action="Kelly hands the rifle to Skorp")]
    assert S.build(rows)["findings"] == []


def test_v1_strings_and_missing_byd_are_unknown_not_guessed():
    res = S.build([_row(1, vat=["AWM"]), _row(2, vat=[])])
    assert res["findings"] == []
    res = S.build([_row(1, vat=_gun()), _row(2)])
    assert res["findings"] == [] and res["unknown"]


def test_posture_end_to_next_start():
    lie = [{"ai": "KELLY", "bat_dau": {"tu_the": "dung"}, "ket_thuc": {"tu_the": "nam"}}]
    up = [{"ai": "KELLY", "bat_dau": {"tu_the": "dung"}}]
    res = S.build([_row(1, hanh_dong=lie), _row(2, hanh_dong=up)])
    assert _attrs(res) == [("tu_the", None)]
    ok = S.build([_row(1, hanh_dong=lie), _row(2, hanh_dong=up, action="Kelly gets up slowly")])
    assert ok["findings"] == []
    same = S.build([_row(1, hanh_dong=lie), _row(2, hanh_dong=[{"ai": "KELLY", "bat_dau": {"tu_the": "nam"}}])])
    assert same["findings"] == [] and [e["attribute"] for e in same["edges"]] == ["tu_the"]


def test_place_changes_inside_a_sequence():
    res = S.build([_row(1, noi={"kho_id": 265}), _row(2, noi={"kho_id": 300})])
    assert _attrs(res) == [("noi", None)]
    assert S.build([_row(1, noi={"kho_id": 265}), _row(2, noi={"kho_id": 265})])["findings"] == []
    assert S.build([_row(1, noi={"kho_id": 265}), _row(2, seq="2", noi={"kho_id": 300})])["findings"] == []


def test_direction_reuses_m43_reading():
    res = S.build([_row(1, motion="Kelly runs from left to right"), _row(2, motion="Kelly runs towards frame-left")])
    assert _attrs(res) == [("huong_khung", None)]


def test_observed_deviation_marks_dependents_to_look_at():
    rows = [_row(1, vat=_gun()), _row(2, vat=_gun()), _row(3, vat=_gun())]
    obs = [{"qc_code": "QC-L13-CONTINUITY", "severity": "REVIEW", "evidence": {"shots": [1]}, "why": "súng biến mất trong clip"}]
    res = S.build(rows, observed=obs)
    assert res["can_xem"] == {"2": [1], "3": [1]}
    one = next(s for s in res["states"] if s["shot"] == 1 and s["attribute"] == "cam")
    assert one["observed"] and one["status"] == "lech_quan_sat" and one["resolved"] is None


def _project(tmp_path):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("m34")
    sids = []
    for idx, vat in ((10, _gun()), (11, _gun()), (12, [])):
        sid = p.create_scene(pid, idx, f"S{idx}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY"], "sequence": "4", "byd": {"vat": vat}}),
                                                              sid))
        sids.append(sid)
    p.conn.commit()
    return p, pid, sids


def test_observed_reads_m42_and_m43_files(tmp_path):
    p, pid, sids = _project(tmp_path)
    jid = p.create_job(sids[0], "video_gen")
    d = tmp_path / str(pid) / "qc_shadow"
    d.mkdir(parents=True)
    (d / "video_qc.jsonl").write_text(json.dumps({"job_ids": [jid], "findings": [{"qc_code": "QC-V2-STILL_OVER_1_5S",
                                                                                  "severity": "REVIEW", "why": "đứng yên"}]}) + "\n",
                                      encoding="utf-8")
    seq = tmp_path / str(pid) / "qc_set" / "sequence"
    seq.mkdir(parents=True)
    (seq / "continuity_shadow.json").write_text(json.dumps({"observed": [{"qc_code": "QC-L13-CONTINUITY", "evidence": {"shots": [11]},
                                                                          "why": "nền đổi"}]}), encoding="utf-8")
    obs = S.observed_of(p.conn, str(tmp_path), pid)
    assert sorted(o["evidence"]["shots"][0] for o in obs) == [10, 11]


def test_run_flag_off_writes_nothing(tmp_path):
    p, pid, _ = _project(tmp_path)
    with OFF:
        assert S.run(p, pid, str(tmp_path)) is None
    assert not os.path.exists(S.result_path(str(tmp_path), pid))


def test_run_flag_on_writes_the_state_file(tmp_path):
    p, pid, _ = _project(tmp_path)
    with ON:
        rec = S.run(p, pid, str(tmp_path))
    assert rec["mode"] == "shadow" and [f["evidence"]["shots"] for f in rec["findings"]] == [[11, 12]]
    assert json.load(open(S.result_path(str(tmp_path), pid), encoding="utf-8"))["states"]


def test_run_never_raises(tmp_path):
    p, pid, _ = _project(tmp_path)
    with ON, mock.patch.object(S, "build", side_effect=RuntimeError("x")):
        assert S.run(p, pid, str(tmp_path)) is None


def test_sequence_check_calls_the_state_after_the_m43_shadow(tmp_path):
    from core import sequence_logic
    p, pid, _ = _project(tmp_path)
    groups = {"4": {"rows": [{"idx": 10}, {"idx": 11}], "shown": {10, 11}, "sheets": []}}
    order = []
    with mock.patch.dict(os.environ, {"FEATURE_QC_SEQUENCE_LOGIC": "1"}), \
         mock.patch.object(sequence_logic, "sequence_sheets", return_value=groups), \
         mock.patch.object(sequence_logic.claude_tasks, "_run", return_value={"ok": True, "issues": []}), \
         mock.patch.object(sequence_logic.prompts, "world_bible_text", return_value=""), \
         mock.patch("core.continuity_shadow.run", side_effect=lambda *a: order.append("m43")), \
         mock.patch.object(S, "run", side_effect=lambda *a: order.append("m34")):
        sequence_logic.check(p, pid, object(), str(tmp_path))
    assert order == ["m43", "m34"]


def test_m43_module_untouched_by_reading():
    """Đề bài: không đụng core/continuity_shadow.py ngoài việc đọc."""
    import inspect
    src = inspect.getsource(S)
    assert "continuity_shadow." in src and "continuity_shadow.build" not in src and "continuity_shadow.run" not in src
