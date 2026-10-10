"""Sự thật hình học một nguồn (core/stage_facts, người dùng 10/10 #24 shot 4 + 8): hợp đồng của sổ FACTS + bộ ca vàng + 3 nơi dùng
(prompt ảnh, bộ kiểm tác động, QC). Ca vàng mới = một tệp tests/golden/cases/<id>.json có ky_vong.stage_facts (định dạng
tests/golden/README.md, K0a), test tự chạy hết."""
import json
import os
import sqlite3

import pytest

from core import change_audit, change_review, features, qc_rules, qc_scene, qc_spec, qc_team, stage_facts as sf
from tests import golden

GOLDEN = golden.stage_facts_cases()


def _case(name):
    return next(c for c in GOLDEN if c["name"] == name)


# ---- (i) hợp đồng của sổ ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("kind", sorted(sf.FACTS))
def test_every_fact_kind_is_complete(kind):
    spec = sf.FACTS[kind]
    for key in sf.REQUIRED:
        assert key in spec, f"{kind} thiếu {key}"
    for key in ("derive", "prompt", "judge", "contradicts"):
        assert callable(spec[key]), f"{kind}.{key} phải là hàm"
    obs = spec["observe"]
    assert callable(obs.get("question")) and sf.UNSURE in obs.get("options", ()), f"{kind}.observe cần question + 'unsure'"


def test_a_partial_kind_breaks_the_contract(monkeypatch):
    monkeypatch.setitem(sf.FACTS, "half", {"derive": lambda ctx: [], "prompt": lambda f, c: ""})
    with pytest.raises(AssertionError):
        test_every_fact_kind_is_complete("half")


def test_judge_answers_of_every_kind_are_levels():
    for c in GOLDEN:
        for f in sf.derive({"stage_camera": c["stage_camera"]}, c["objects"])["facts"]:
            for seen in f["options"] + [None, "na", "nonsense"]:
                assert sf.judge(f, seen) in sf.LEVELS


# ---- (ii) bộ ca vàng ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("case", GOLDEN, ids=[c["name"] for c in GOLDEN])
def test_golden(case):
    res = sf.derive({"stage_camera": case["stage_camera"]}, case["objects"])
    assert res["missing"] is None
    facts = {f["id"]: f for f in res["facts"]}
    for fid, value in case["expect"]["facts"].items():
        assert fid in facts, f"{case['name']}: thiếu sự thật {fid}"
        assert facts[fid]["value"] == value, (fid, facts[fid])
    block = sf.prompt_block(res["facts"])
    for s in case["expect"]["prompt_contains"]:
        assert s in block, (s, block)
    for s in case["expect"]["prompt_not_contains"]:
        assert s not in block, (s, block)
    con = sf.contradictions(case["image_prompt"], res["facts"])
    want = case["expect"]["contradiction"]
    if want is None:
        assert con == []
    else:
        assert any(c["level"] == want["level"] and want["phrase_contains"] in c["phrase"] for c in con), con
        assert all(c["fix"] for c in con)
    for fid, seen, level in case["expect"]["judge"]:
        assert sf.judge(facts[fid], seen) == level, (fid, seen)


def test_no_stage_camera_no_facts_said():
    res = sf.derive({"image_prompt": "a well"})
    assert res["facts"] == [] and "stage_camera" in res["missing"]
    assert sf.derive({"stage_camera": {"location": [0, 0, 1]}})["missing"]
    assert sf.prompt_block([]) == ""


def test_a_door_opening_is_not_the_well():
    facts = sf.derive({"stage_camera": _case("p24_shot4_low_camera_well")["stage_camera"]})["facts"]
    assert sf.contradictions("A dark opening of a house door behind her. Rain.", facts) == []
    assert sf.contradictions("A well-lit plaza, a dark opening of a doorway, Kelly as well.", facts) == []
    assert sf.contradictions("The well stands at the bottom of the frame.", facts) == []
    assert sf.contradictions("Kelly peers into the dark inside of the old well.", facts)


def test_horizon_is_the_render_formula():
    from core import plate_camera
    sc = _case("p24_shot8_stand_in_block")["stage_camera"]
    h = sf.horizon(sc["location"], sc["look_at"], sc["lens"])
    assert h["w"] == pytest.approx(plate_camera.horizon_y(sc["location"], sc["look_at"], sc["lens"], 9 / 16), abs=2e-3)


# ---- nơi dùng (a): prompt ảnh ------------------------------------------------------------------------------------------------
def _project():
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    pid = p.create_project("facts")
    return p, pid


def _prompt(monkeypatch, data, flag):
    from core import runner
    monkeypatch.setattr(features, "on", lambda n: flag and n == "stage_camera")
    p, pid = _project()
    return runner.build_image_prompt(p.conn, pid, dict(data))[0]


def test_image_prompt_gets_the_facts_block(monkeypatch):
    c = _case("p24_shot4_low_camera_well")
    text = _prompt(monkeypatch, {"image_prompt": c["image_prompt"], "stage_camera": c["stage_camera"], "size": "WS"}, True)
    assert "only the outer wall of the stone well" in text and "Geometry of this camera" in text


def test_image_prompt_unchanged_without_stage_camera_or_flag(monkeypatch):
    c = _case("p24_shot4_low_camera_well")
    plain = {"image_prompt": c["image_prompt"], "size": "WS"}
    assert _prompt(monkeypatch, plain, True) == _prompt(monkeypatch, plain, False)
    with_sc = dict(plain, stage_camera=c["stage_camera"])
    assert _prompt(monkeypatch, with_sc, False) == _prompt(monkeypatch, plain, False)


# ---- nơi dùng (a'): bộ kiểm tác động -----------------------------------------------------------------------------------------
def _db(data):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("CREATE TABLE scenes(id INTEGER PRIMARY KEY, project_id INT, idx INT, data TEXT);"
                    "CREATE TABLE assets(id INTEGER PRIMARY KEY, kind TEXT, name TEXT, profile TEXT);"
                    "CREATE TABLE jobs(id INTEGER PRIMARY KEY, scene_id INT, type TEXT, state TEXT, sent_refs TEXT);")
    c.execute("INSERT INTO scenes VALUES (1, 24, 4, ?)", (json.dumps(data),))
    return c


def test_director_sentence_against_the_facts_is_red_with_a_fix(monkeypatch, tmp_path):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    c = _case("p24_shot4_low_camera_well")
    res = change_audit.audit_shot(_db({"stage_camera": c["stage_camera"], "image_prompt": c["image_prompt"], "size": "WS"}),
                                  str(tmp_path), 24, 1)
    geo = [r for r in res if r["khau"] == "cau" and "mouth facing us" in r["msg"]]
    assert geo and geo[0]["muc"] == "do" and "only the outer wall" in geo[0]["de_xuat"]
    assert change_review._code_level(geo[0]) == "do"            # không bị hạ vàng (redraw_compare không tạo job)


def test_no_geometry_finding_without_stage_camera(monkeypatch, tmp_path):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    c = _case("p24_shot4_low_camera_well")
    res = change_audit.audit_shot(_db({"image_prompt": c["image_prompt"]}), str(tmp_path), 24, 1)
    assert not [r for r in res if "sự thật hình học" in r["msg"]]


# ---- nơi dùng (b): QC --------------------------------------------------------------------------------------------------------
def _frame_data(name):
    c = _case(name)
    return {"stage_camera": c["stage_camera"], "image_prompt": c["image_prompt"], "characters": [], "size": "WS"}


def test_compile_frame_adds_geometry_observations(monkeypatch):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    out = qc_spec.compile_frame(None, 24, 7, _frame_data("p24_shot4_low_camera_well"), profiles={})
    geo = [a for a in out["assertions"] if a["type"] == "geometry"]
    assert {a["fact"]["id"] for a in geo} >= {"top_visible:well", "stand_in:well"}
    assert all(a["observe"] == "geo" and sf.UNSURE in a["options"] for a in geo)
    monkeypatch.setattr(features, "on", lambda n: False)
    off = qc_spec.compile_frame(None, 24, 7, _frame_data("p24_shot4_low_camera_well"), profiles={})
    assert not [a for a in off["assertions"] if a["type"] == "geometry"]


def test_rules_turn_the_geometry_report_into_a_verdict(monkeypatch):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    geo = {a["fact"]["id"]: a for a in qc_spec.compile_frame(None, 24, 7, _frame_data("p24_shot4_low_camera_well"),
                                                              profiles={})["assertions"] if a["type"] == "geometry"}
    a = geo["top_visible:well"]
    r = qc_rules.assertion_result(a, {"answer": "true", "confidence": "high", "geo_seen": "inside_visible"}, None)
    assert r["state"] == "fail" and r["severity"] == "block"         # model nói 'ok', code: thấy lòng giếng là sai
    r = qc_rules.assertion_result(a, {"answer": "true", "confidence": "high", "geo_seen": "unsure"}, None)
    assert r["state"] == "unclear" and r["severity"] == "block"      # rà kỹ 10/10 lỗi 2: không hạ minor (pass im lặng)
    r = qc_rules.assertion_result(a, {"answer": "true", "confidence": "high", "geo_seen": "only_outer_wall"}, None)
    assert r["state"] == "ok"


def test_team_request_asks_geometry_and_keeps_the_old_schema(monkeypatch):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    geo = [a for a in qc_spec.compile_frame(None, 24, 7, _frame_data("p24_shot8_stand_in_block"), profiles={})["assertions"]
           if a["type"] == "geometry"]
    assert qc_team.schema_for([]) is qc_team.ANSWER_SCHEMA                  # khung không có sự thật: yêu cầu y hệt (replay cũ còn khớp)
    sch = qc_team.schema_for(geo)
    assert "flat_plain_block" in sch["properties"]["answers"]["items"]["properties"]["geo_seen"]["enum"]
    line = qc_team.request_line(geo[0], {})
    assert line["khai"] == ["geo_seen"] and sf.UNSURE in line["chọn"]


def test_scene_qc_block_and_code_overrides_place_ok():
    facts = {1: sf.derive({"stage_camera": _case("p24_shot4_low_camera_well")["stage_camera"]})["facts"]}
    block = qc_scene.geometry_block(facts)
    assert "Khai điều thấy" in block and "top_visible:well" in block and "unsure" in block
    ok = {"ok": True, "evidence": "giếng đá ở giữa phải khung, nền quảng trường"}
    frame = {"k": 1, "checks": {c: dict(ok) for c in qc_scene.CHECKS}, "verdict": "pass", "root_cause": "none",
             "geo": {"top_visible:well": "inside_visible", "stand_in:well": "bogus"}}
    obj = qc_scene.validate({"frames": [frame], "scene": {}}, [(1, "K1")])     # khóa mới / giá trị lạ không làm vỡ validate cũ
    notes = qc_scene.apply_geometry(obj, facts)
    f = obj["frames"][0]
    assert f["checks"]["place"]["ok"] is False and f["verdict"] == "fix" and f["root_cause"] == "prompt"
    assert "only the outer wall" in f["fix"] and notes
    frame2 = dict(frame, geo={}, checks={c: dict(ok) for c in qc_scene.CHECKS}, verdict="pass")
    obj2 = qc_scene.validate({"frames": [frame2], "scene": {}}, [(1, "K1")])
    qc_scene.apply_geometry(obj2, facts)
    assert obj2["frames"][0]["verdict"] == "doubt" and obj2["frames"][0]["checks"]["place"]["ok"] is True   # thiếu = unsure → vàng


def test_plate_layout_uses_the_analytic_horizon_when_the_render_shows_none(tmp_path):
    from PIL import Image
    from core import plate_layout_qc
    dark = os.path.join(str(tmp_path), "plate.png")
    Image.new("L", (90, 160), 10).save(dark)
    img = os.path.join(str(tmp_path), "img.png")
    im = Image.new("L", (90, 160), 30)
    im.paste(200, (0, 0, 90, 130))                      # chân trời ảnh ở ~81 % khung
    im.save(img)
    res = plate_layout_qc.compare(img, dark, None, horizon_expected=0.33)
    assert res["horizon_plate"] == pytest.approx(0.33) and res["horizon_source"] == "giai_tich" and res["mismatch"]
    assert plate_layout_qc.compare(img, dark, None)["horizon_plate"] is None     # cũ: không có số giải tích → như trước


# ---- rà kỹ 10/10: các lỗi phiên rà báo ---------------------------------------------------------------------------------------
def _shot4_facts(render=True):
    return sf.derive({"stage_camera": _case("p24_shot4_low_camera_well")["stage_camera"]}, render=render)["facts"]


def test_unsure_on_every_shot4_fact_is_doubt_not_a_silent_pass(monkeypatch):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    geo = [a for a in qc_spec.compile_frame(None, 24, 7, _frame_data("p24_shot4_low_camera_well"), profiles={})["assertions"]
           if a["type"] == "geometry"]
    assert len(geo) >= 4
    answers = {a["id"]: {"answer": "true", "confidence": "high", "geo_seen": "unsure"} for a in geo}
    v = qc_rules.frame_verdict(geo, answers, {})
    assert v["verdict"] == "doubt" and v["arbiter"], v["verdict"]


def test_horizon_unsure_or_one_band_off_stays_quiet():
    f = next(x for x in _shot4_facts() if x["kind"] == "pitch_horizon")
    assert sf.judge(f, "unsure") is None                       # khung đêm sương: không biến mọi khung thành doubt
    order = sf._HORIZON_ORDER
    i = order.index(f["value"])
    far = order[(i + 2) % len(order)] if (i + 2) < len(order) else order[i - 2]
    assert sf.judge(f, far) == "vang"
    near = [o for o in order if abs(order.index(o) - i) == 1 and o not in f["accept"]]
    assert all(sf.judge(f, o) is None for o in near)


def test_no_render_no_render_words():
    block = sf.prompt_block(_shot4_facts(render=False))
    assert "render" not in block and "placeholder" not in block and "only the outer wall" in block
    assert "placeholder" in sf.prompt_block(_shot4_facts(render=True))


def test_rim_out_of_frame_says_nothing_about_the_opening():
    f = next(x for x in _shot4_facts() if x["kind"] == "top_visible")
    assert "rim_in_frame" in f and f["rim_in_frame"] is True
    assert sf._prompt_top(dict(f, rim_in_frame=False), {}) == ""


def test_image_runner_says_the_self_contradicting_prompt(monkeypatch):
    from core import runner
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    c = _case("p24_shot4_low_camera_well")
    p, pid = _project()
    notes = runner.geometry_contradiction_notes(p.conn, pid, {"image_prompt": c["image_prompt"], "stage_camera": c["stage_camera"]})
    assert notes and "mouth facing us" in notes[0]
    assert runner.geometry_contradiction_notes(p.conn, pid, {"image_prompt": "Kelly by the well.", "stage_camera": c["stage_camera"]}) == []
    monkeypatch.setattr(features, "on", lambda n: False)
    assert runner.geometry_contradiction_notes(p.conn, pid, {"image_prompt": c["image_prompt"], "stage_camera": c["stage_camera"]}) == []


def test_old_shot_without_change_event_is_held(monkeypatch, tmp_path):
    monkeypatch.setattr(features, "on", lambda n: n in ("stage_camera", change_review.FLAG))
    c = _case("p24_shot4_low_camera_well")
    p, pid = _project()
    idx = p.add_scene_next(pid, "s4")
    sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()[0]
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                   (json.dumps({"image_prompt": c["image_prompt"], "stage_camera": c["stage_camera"], "size": "WS"}), sid))
    p.conn.execute("UPDATE change_events SET state='skipped'")
    p.conn.commit()
    why = change_review.blocking(p.conn, sid, str(tmp_path))
    assert why and "mouth facing us" in why
    fid = p.conn.execute("SELECT id FROM change_findings WHERE scene_id=? AND status='open' AND khau='cau'", (sid,)).fetchone()[0]
    change_review.close(p.conn, fid, "dismissed", "test")              # Bỏ qua → không ghi lại mục đó
    assert not (change_review.blocking(p.conn, sid, str(tmp_path)) or "").count("mouth facing us")
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")   # cờ change_review tắt: không ghi, không giữ
    assert change_review.blocking(p.conn, sid, str(tmp_path)) is None


def _red_frame(facts):
    ok = {"ok": True, "evidence": "giếng đá ở giữa phải khung, nền quảng trường"}
    frame = {"k": 1, "checks": {c: dict(ok) for c in qc_scene.CHECKS}, "verdict": "pass", "root_cause": "none",
             "geo": {"top_visible:well": "inside_visible"}}
    return qc_scene.validate({"frames": [frame], "scene": {}}, [(1, "K1")])


def test_geometry_fix_ignores_the_director_words_or_blames_the_model():
    facts = {1: [f for f in _shot4_facts() if f.get("in_frame")]}
    c = _case("p24_shot4_low_camera_well")
    obj = _red_frame(facts)
    qc_scene.apply_geometry(obj, facts, {1: c["image_prompt"]})
    f = obj["frames"][0]
    assert f["verdict"] == "fix" and f["root_cause"] == "prompt" and 'Ignore the words "' in f["fix"] and "mouth facing us" in f["fix"]
    obj = _red_frame(facts)
    qc_scene.apply_geometry(obj, facts, {1: "Kelly fallen by the old stone well, foggy plaza at night."})
    f = obj["frames"][0]
    top = next(x for x in facts[1] if x["kind"] == "top_visible")
    assert f["verdict"] == "fix" and f["root_cause"] == "model" and "knee height" in f["fix"] and top["prompt"] not in f["fix"]


def test_plate_layout_bright_or_dark_without_horizon_is_not_flagged(tmp_path):
    from PIL import Image
    from core import plate_layout_qc
    dark = os.path.join(str(tmp_path), "plate.png")
    Image.new("L", (90, 160), 10).save(dark)
    dimg = os.path.join(str(tmp_path), "dimg.png")
    Image.new("L", (90, 160), 12).save(dimg)                 # ảnh vẽ tối, không đo được chân trời
    assert plate_layout_qc.compare(dimg, dark, None, horizon_expected=0.33)["mismatch"] is False
    bright = os.path.join(str(tmp_path), "bright.png")
    Image.new("L", (90, 160), 200).save(bright)              # render sáng không có chân trời: không ép số giải tích
    img = os.path.join(str(tmp_path), "img.png")
    im = Image.new("L", (90, 160), 30)
    im.paste(200, (0, 0, 90, 130))
    im.save(img)
    res = plate_layout_qc.compare(img, bright, None, horizon_expected=0.33)
    assert res["horizon_source"] is None and res["horizon_plate"] is None