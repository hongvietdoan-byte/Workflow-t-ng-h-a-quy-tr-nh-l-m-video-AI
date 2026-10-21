"""V3.1 M2.5 (C-M25): write guard cấp trường chế độ SHADOW theo docs/V3_1_M0_10_BAO_VE_DU_LIEU_2026-10-20.md (mục 2, 3.3, 4.1).
core/write_guard: shadow chỉ GHI diag (field_conflict / field_review / stale_write) — KHÔNG chặn, KHÔNG đổi dữ liệu (byte giống); enforce = C3-6
(chưa làm → NotImplementedError). Cờ `field_guard` TẮT = không đọc thêm, không ghi gì. Nối dần các đường ghi L1–L6.
Quyết định đã chốt: take người chọn = USER_LOCKED; prompt khóa → REVIEW_REQUIRED (lúc enforce). CSDL tạm, 0 USD."""
import json
import os
from unittest import mock

import pytest

from core import write_guard as G
from core.db import connect
from core.pipeline import Pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ON = mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_FIELD_GUARD": ""})
AI = G.actor("ai", "director")
HUMAN = G.actor("human", "a@b.c")


@pytest.fixture
def db(tmp_path):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("m25")
    sid = p.create_scene(pid, 1, "S1")
    data = {"image_prompt": "người viết", "video_route": "kling", "duration_s": 4.0, "characters": ["KELLY"], "size": "MS",
            "_user_locked": ["image_prompt", "video_route", "duration_s"]}
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    p.conn.commit()
    return p, pid, sid


def _data(p, sid):
    return p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0]


def _diags(p, code=None):
    q = "SELECT code, message FROM diag_events" + (" WHERE code=?" if code else "")
    return p.conn.execute(q, (code,) if code else ()).fetchall()


# ---- cờ ----------------------------------------------------------------------------------------------------------------------
def test_flag_registered_off_and_in_golden_inputs():
    from core import features
    assert G.FLAG in features.FEATURES and features.FEATURES[G.FLAG]["verified"] is False
    with OFF:
        assert not G.enabled()
    golden = json.load(open(os.path.join(ROOT, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
    assert all(golden[k]["flags"][G.FLAG] is False for k in ("image", "video"))


def test_registered_in_areas():
    areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))
    hit = [a for a in areas["areas"] if "core/write_guard.py" in a["code"]]
    assert hit and "tests/test_v31_m25_write_guard.py" in hit[0]["tests"] and G.FLAG in hit[0]["flags"]


# ---- trạng thái + đánh giá thuần (4.1) -----------------------------------------------------------------------------------------
def test_state_reads_old_lock_list_and_new_state():
    d = {"_user_locked": ["image_prompt"], "_field_state": {"characters": G.REVIEW_REQUIRED}}
    assert G.state(d, "image_prompt") == G.USER_LOCKED and G.state(d, "characters") == G.REVIEW_REQUIRED
    assert G.state(d, "size") == G.AUTO and G.state({}, "byd.vat") == G.AUTO
    assert G.state({"_user_locked": ["byd"]}, "byd.vat") == G.USER_LOCKED            # khóa cây byd


def test_g1_ai_on_locked_field_would_keep():
    ev = G.assess({"image_prompt": "a", "_user_locked": ["image_prompt"]}, {"image_prompt": "b"}, AI)
    assert [(e["code"], e["would"], e["field"]) for e in ev] == [("field_conflict", "keep", "image_prompt")]


def test_g2_ai_on_auto_field_nothing():
    assert G.assess({"size": "MS"}, {"size": "WS"}, AI) == []


def test_g3_human_never_flagged():
    assert G.assess({"image_prompt": "a", "_user_locked": ["image_prompt"]}, {"image_prompt": "b"}, HUMAN) == []


def test_g4_review_field_with_value_would_review():
    ev = G.assess({"characters": ["KELLY"]}, {"characters": ["KELLY", "SKORP"]}, AI)
    assert [(e["code"], e["would"]) for e in ev] == [("field_review", "review")]
    assert G.assess({}, {"characters": ["KELLY"]}, AI) == []                       # chưa có giá trị: ghi tự do


def test_g5_stale_revision():
    ev = G.assess({"_rev": 4}, {"size": "WS"}, AI, expected_rev=3)
    assert [e["code"] for e in ev] == ["stale_write"]


def test_stale_when_the_row_changed_since_it_was_read():
    read = {"size": "MS", "layout": None}
    now = {"size": "WS", "layout": None}
    ev = G.assess(read, {"layout": {"x": 1}}, G.actor("auto", "previz"), current=now)
    assert [(e["code"], e["fields"]) for e in ev] == [("stale_write", ["size"])]


def test_g7_derived_field_free():
    assert G.assess({"_user_locked": ["formula_check"]}, {"formula_check": {"ok": 1}}, AI) == []


def test_same_value_is_not_a_conflict():
    assert G.assess({"image_prompt": "a", "_user_locked": ["image_prompt"]}, {"image_prompt": "a"}, AI) == []


def test_delete_counts_as_a_change():
    ev = G.assess({"video_route": "kling", "_user_locked": ["video_route"]}, {"video_route": G.DELETE}, AI)
    assert ev and ev[0]["new"] is None


# ---- observe / write_scene ---------------------------------------------------------------------------------------------------
def test_flag_off_observe_does_nothing(db):
    p, _, sid = db
    with OFF, mock.patch.object(G, "_load", side_effect=AssertionError("đọc CSDL khi cờ tắt")):
        assert G.observe(p.conn, sid, {"image_prompt": "x"}, AI) is None
    assert _diags(p) == []


def test_shadow_records_diag_and_never_changes_data(db):
    p, _, sid = db
    before = _data(p, sid)
    with ON:
        ev = G.observe(p.conn, sid, {"image_prompt": "AI viết"}, AI)
    assert [e["code"] for e in ev] == ["field_conflict"] and _data(p, sid) == before
    rows = _diags(p, "field_conflict")
    assert rows and "image_prompt" in rows[0]["message"] and "shadow" in rows[0]["message"]


def test_write_scene_shadow_result_and_enforce_not_built(db):
    p, _, sid = db
    with ON:
        res = G.write_scene(p.conn, sid, {"image_prompt": "AI viết", "size": "WS"}, AI)
        assert res["applied"] is False and res["mode"] == "shadow" and res["kept_locked"] == ["image_prompt"]
        assert res["proposals"] == {"image_prompt": "AI viết"}
        with pytest.raises(NotImplementedError):
            G.write_scene(p.conn, sid, {"size": "WS"}, AI, mode="enforce")


def test_observe_never_raises(db):
    p, _, sid = db
    with ON, mock.patch.object(G, "assess", side_effect=RuntimeError("x")):
        assert G.observe(p.conn, sid, {"size": "WS"}, AI) is None


# ---- nối các đường ghi L1–L6 (shadow: dữ liệu ghi y như cũ + diag) ----------------------------------------------------------------
def test_l2_audio_first_on_locked_duration(db, tmp_path):
    from core import audio_first
    p, pid, sid = db
    with ON, mock.patch("core.voice.scene_seconds", return_value={sid: 6.0}):
        changes = audio_first.fit_shots(p.conn, pid, str(tmp_path))
    assert changes and json.loads(_data(p, sid))["duration_s"] > 4.0                 # vẫn ghi như cũ (shadow)
    assert _diags(p, "field_conflict")


def test_l3_route_ladder_on_chosen_route(db):
    from core import seedance_refs
    p, _, sid = db
    with ON:
        seedance_refs.set_route(p.conn, [sid], "seedance")
    assert json.loads(_data(p, sid))["video_route"] == "seedance" and _diags(p, "field_conflict")


def test_l4_prompt_rewrite_on_locked_prompt_but_not_revert(db):
    from core import prompt_rewrite
    p, _, sid = db
    with ON:
        prompt_rewrite._set_prompt(p.conn, sid, "image", "AI viết lại", actor=G.actor("ai", "director_rewrite"))
        assert len(_diags(p, "field_conflict")) == 1
        prompt_rewrite._set_prompt(p.conn, sid, "image", "bản cũ", actor=G.actor("human", "a@b.c"))
    assert len(_diags(p, "field_conflict")) == 1 and json.loads(_data(p, sid))["image_prompt"] == "bản cũ"


def test_l4_callers_pass_the_actor():
    import inspect
    from core import prompt_rewrite
    assert 'actor=write_guard.actor("ai", "director_rewrite")' in inspect.getsource(prompt_rewrite.save_rewrite)
    assert 'actor=write_guard.actor("human"' in inspect.getsource(prompt_rewrite.revert)


def test_l5_byd_fill_on_locked_byd(db):
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import byd_fill
    p, _, sid = db
    d = json.loads(_data(p, sid))
    d.update(byd={"thanh_phan": []}, shot_no=3, _user_locked=d["_user_locked"] + ["byd"])
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
    with ON:
        byd_fill.fill_numbers(p.conn, [{"id": sid}])
    assert json.loads(_data(p, sid))["byd"]["shot"] == 3 and _diags(p, "field_conflict")


def test_l6_formula_write_after_a_change_in_between(db):
    from core import prompt_formula
    p, _, sid = db
    read = json.loads(_data(p, sid))
    d = dict(read, size="WS")                                                       # người sửa xen giữa
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
    with ON:
        prompt_formula._write(p.conn, sid, read, {"ok": True})
        assert _diags(p, "stale_write") == []          # rà M25-1: giữa giao dịch nơi gọi → chưa ghi (không commit hộ)
        p.conn.commit()
        G.flush(p.conn)
    rows = _diags(p, "stale_write")
    assert rows and "size" in rows[0]["message"]


def test_l1_motion_prompt_by_ai_on_locked(db):
    from core import llm_io
    p, pid, sid = db
    img = p.create_job(sid)
    p.start(img)
    p.succeed(img)
    p.approve(img)
    llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "người viết motion"}]})
    d = json.loads(_data(p, sid))
    d["_user_locked"].append("motion_prompt")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
    with ON:
        llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "AI viết motion"}]}, actor=G.actor("ai", "director"))
    got = p.conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()[0]
    assert got == "AI viết motion" and _diags(p, "field_conflict")


def test_l1_ai_callers_pass_the_actor():
    for f in ("core/llm_runner.py", "core/seedance_refs.py", "core/claude_tasks.py", "mcp_servers/project_db.py"):
        src = open(os.path.join(ROOT, f), encoding="utf-8").read()
        assert "store_motion_prompts(" in src and "write_guard.actor(" in src, f


def test_flag_off_paths_are_byte_identical(db, tmp_path):
    from core import seedance_refs
    p, _, sid = db
    with OFF:
        seedance_refs.set_route(p.conn, [sid], "seedance")
    assert json.loads(_data(p, sid))["video_route"] == "seedance" and _diags(p) == []
