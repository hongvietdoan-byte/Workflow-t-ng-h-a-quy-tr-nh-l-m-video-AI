"""DP5 — V3.1 M5.1 (cloud-C 20/10): repair router theo mã lỗi — CHỈ ĐỀ XUẤT (cờ `repair_router` TẮT; G2-6). Thiết kế
docs/V3_1_M5_THIET_KE_REPAIR_RELEASE_2026-10-20.md mục 2. Không gọi model, không tạo / gửi job, 0 USD."""
import os
import re
from unittest import mock

import pytest

from core import repair_router as R
from core.db import connect
from core.pipeline import Pipeline, SUBMIT_UNKNOWN

ON = mock.patch.dict(os.environ, {"FEATURE_REPAIR_ROUTER": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_REPAIR_ROUTER": ""})
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_m41_code_has_exactly_one_row():
    doc = open(os.path.join(ROOT, "docs", "V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md"), encoding="utf-8").read()
    table = doc.split("## 3.")[1].split("## 4.")[0]
    codes = set()
    for m in re.findall(r"^\| (QC-[A-Z0-9_\-/ ]+?) \|", table, re.M):
        head = m.split("/")[0].strip()
        codes.add(head)
        for tail in m.split("/")[1:]:                                   # "QC-A4-BLACK_FRAME / FREEZE_FRAME"
            tail = tail.strip()
            codes.add(tail if tail.startswith("QC-") else head.rsplit("-", 1)[0] + "-" + tail)
    codes -= {"QC-CR-INPUT_MISSING", "QC-SYS-QC_CRASH"}               # không phải lỗi của shot (thiết kế M5.1: qc_runs, không gen)
    assert codes and codes <= set(R.REPAIR_ACTIONS), sorted(codes - set(R.REPAIR_ACTIONS))


def test_registry_and_criteria_mapping_point_at_real_rows():
    import json
    reg = {x["id"] for x in json.load(open(os.path.join(ROOT, "devsys", "errors.json"), encoding="utf-8"))["items"]}
    assert {"P31-G51", "P31-G28", "P33-A5", "P31-G20"} <= reg                     # lỗi gốc của các dòng REFRAME / TRIM / REPLATE
    crit = json.load(open(os.path.join(ROOT, "data", "qc_checklist.json"), encoding="utf-8"))
    keys = {c["key"] for c in crit["criteria"]} | {c["key"] for c in crit["video_criteria"]}
    assert set(R.CRITERION_CODE) <= keys and set(R.CRITERION_CODE.values()) <= set(R.REPAIR_ACTIONS)


@pytest.fixture
def world(tmp_path):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("dp5")
    sid = p.create_scene(pid, 1, "S1")
    jid = p.create_job(sid, "image_gen")
    p.start(jid)
    p.succeed(jid)
    return p, pid, sid, jid


def _job(p, jid):
    return p.job(jid)


def test_happy_path_is_a_proposal_only(world):
    p, pid, sid, jid = world
    pl = R.plan(p.conn, _job(p, jid), "QC-L1-IDENTITY_DRIFT", fix="Keep Kelly's red hair and black jacket", limit=3)
    assert pl["action"] == "SWAP_REF+REWRITE_PROMPT" and pl["stop_code"] is None
    assert pl["auto_ok"] is False and pl["needs_person"] is True and (pl["attempt_no"], pl["limit"]) == (1, 3)


def test_stop_rules_in_order(world):
    p, pid, sid, jid = world
    j = _job(p, jid)
    assert R.plan(p.conn, j, "QC-L14-ARTIFACT", fix="x", limit=3, attempt=4)["stop_code"] == "REPAIR_LIMIT"
    assert R.plan(p.conn, j, "QC-L4-POSE_ACTION", fix=None, limit=3)["stop_code"] == "REPAIR_NO_INPUT_DELTA"     # viết lại mà không câu sửa
    assert R.plan(p.conn, j, "QC-L14-ARTIFACT", fix="x", limit=3, hold="cùng lỗi lặp lại")["stop_code"] == "REPAIR_NO_INPUT_DELTA"
    assert R.plan(p.conn, j, "QC-L13-CONTINUITY", fix="x", limit=3)["stop_code"] == "REPAIR_INTENT_CHANGE"      # D07: không tự sửa
    assert R.plan(p.conn, j, "QC-A2-SILENT_GAP", fix="x", limit=3)["stop_code"] == "REPAIR_REVIEW_ONLY"
    assert R.plan(p.conn, j, None, fix="x", limit=3)["stop_code"] == "REPAIR_UNMAPPED"
    p.set_paused(pid, True)
    assert R.plan(p.conn, j, "QC-L14-ARTIFACT", fix="x", limit=3)["stop_code"] == "REPAIR_PAUSED"


def test_submit_unknown_is_never_routed(world):
    p, pid, sid, jid = world
    j2 = p.create_job(sid, "video_gen")
    p.start(j2)
    p.fail(j2, f"{SUBMIT_UNKNOWN}: TimeoutError")
    p.set_paused(pid, True)                                     # dừng loại 1 đứng trước loại 2
    assert R.plan(p.conn, p.job(j2), "QC-L14-ARTIFACT", fix="x", limit=2)["stop_code"] == "REPAIR_SUBMIT_UNKNOWN"


def test_same_code_twice_in_the_chain_stops(world):
    p, pid, sid, jid = world
    with ON:
        R.observe(p.conn, _job(p, jid), ["hands_face"], fix="clean hands", limit=3)
    child = p._insert_job(pid, sid, "image_gen", parent_job_id=jid, retry_count=1)
    pl = R.plan(p.conn, p.job(child), "QC-L14-ARTIFACT", fix="clean hands, five fingers", limit=3)
    assert pl["stop_code"] == "REPAIR_SAME_CODE_TWICE"


def test_observe_flag_off_does_nothing(world):
    p, pid, sid, jid = world
    with OFF:
        assert R.observe(p.conn, _job(p, jid), ["character"], fix="x") == []
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code=?", (R.CODE,)).fetchone()[0] == 0


def test_observe_writes_one_plan_per_code_and_says_unmapped(world):
    p, pid, sid, jid = world
    with ON:
        plans = R.observe(p.conn, _job(p, jid), ["character", "hands_face", "mood_lighting"], fix="x", limit=3)
    assert [pl["qc_code"] for pl in plans] == ["QC-L1-IDENTITY_DRIFT", "QC-L14-ARTIFACT", None]
    msgs = [r[0] for r in p.conn.execute("SELECT message FROM diag_events WHERE code=?", (R.CODE,))]
    assert len(msgs) == 3 and all("không tự gửi job" in m for m in msgs) and any("REPAIR_UNMAPPED" in m for m in msgs)


def test_observe_never_raises(world):
    p, pid, sid, jid = world
    with ON, mock.patch.object(R, "plan", side_effect=RuntimeError("x")):
        assert R.observe(p.conn, _job(p, jid), ["character"], fix="x") == []


def _qc_world(tmp_path, name):
    p = Pipeline(connect(str(tmp_path / f"{name}.sqlite")))
    pid = p.create_project("dp5", "auto")
    sid = p.create_scene(pid, 1, "S1")
    jid = p.create_job(sid, "image_gen")
    p.start(jid)
    p.succeed(jid)
    return p, pid, jid


def test_apply_qc_decision_and_jobs_are_the_same_with_the_router(tmp_path):
    """Router chỉ ghi đề xuất: quyết định QC + số job (gen lại thật của đường cũ) giống hệt khi cờ bật / tắt."""
    scores = {"character": 0.2, "hands_face": 0.9, "composition": 0.9, "mood_lighting": 0.9, "consistency": 0.9, "scale": 0.9,
              "grounding": 0.9, "set_match": 0.9}
    out = {}
    for name, flag in (("off", OFF), ("on", ON)):
        p, pid, jid = _qc_world(tmp_path, name)
        with flag:
            decision = p.apply_qc(jid, scores, issues="Keep the red hair")
        jobs = [(r["type"], r["state"], r["parent_job_id"]) for r in p.conn.execute("SELECT * FROM jobs ORDER BY id")]
        out[name] = (decision, jobs)
        n = p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code=?", (R.CODE,)).fetchone()[0]
        assert (n > 0) == (name == "on")
    assert out["on"] == out["off"]
