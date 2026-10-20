"""DP4 — V3.1 M4.1 (cloud-C 20/10): schema bằng chứng QC + ghi SHADOW (core/qc_evidence.py, cờ `qc_evidence` TẮT).
Theo thiết kế docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md mục 6 (test plan). CSDL tạm, 0 USD."""
import json
import os
from unittest import mock

import pytest

from core import qc_evidence as E
from core.db import connect

ON = mock.patch.dict(os.environ, {"FEATURE_QC_EVIDENCE": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_QC_EVIDENCE": ""})
SHA = "a" * 64


# ---- bảng mã (test_qc_codes) ---------------------------------------------------------------------------------------------------
def test_every_code_has_a_real_error_type_and_real_registry_ids():
    types, reg = E.error_types(), E.registry_ids()
    assert types and reg
    for code, (et, det, top, ids) in E.CODES.items():
        assert code.startswith("QC-") and et in types, code
        assert all(i in reg for i in ids), (code, ids)
        assert top in E.SEVERITIES


def test_no_model_code_may_block():
    assert all(det for code, (et, det, top, ids) in E.CODES.items() if top == "BLOCK")
    assert E.PREEXISTING_BLOCK <= {c for c, v in E.CODES.items() if v[1]}


# ---- validate (test_qc_evidence_schema) ----------------------------------------------------------------------------------------
def _f(**kw):
    base = E.finding("QC-V2-STILL_OVER_1_5S", "REVIEW", "segment", {"t0": 1, "t1": 3}, "đơ", "job:1", SHA, "x")
    base.update(kw)
    return base


def test_a_good_finding_is_valid():
    assert E.validate(_f()) == []


@pytest.mark.parametrize("bad,word", [({"severity": "HIGH"}, "severity"), ({"evidence_type": "guess"}, "evidence_type"),
                                      ({"artifact_sha": "abc"}, "sha256"), ({"registry_ids": ["P99-X1"]}, "registry_ids"),
                                      ({"error_type": "L1"}, "khác bảng mã"), ({"qc_code": "QC-NOPE"}, "qc_code lạ"),
                                      ({"status": "maybe"}, "status")])
def test_bad_fields_are_said(bad, word):
    assert any(word in p for p in E.validate(_f(**bad)))


def test_block_rules_d07():
    vlm = E.finding("QC-L13-CONTINUITY", "REVIEW", "vlm", {}, "x", "job:1", SHA, "x")
    vlm["severity"] = "BLOCK"
    assert any("tất định" in p for p in E.validate(vlm))                       # mã từ model không bao giờ BLOCK
    # C-FIX-DP345: BLACK/FREEZE nay trần REVIEW (G2-5) → luật hiệu chuẩn kiểm trên một mã tất định giả có trần BLOCK
    with mock.patch.dict(E.CODES, {"QC-A4-TEST_BLOCKABLE": ("A4", True, "BLOCK", ())}):
        det = E.finding("QC-A4-TEST_BLOCKABLE", "REVIEW", "segment", {"at": 2}, "đo", "final:1", SHA, "x")
        det["severity"] = "BLOCK"
        assert any("confidence_calibration" in p for p in E.validate(det))      # tất định nhưng chưa benchmark + duyệt
        det["confidence_calibration"] = {"benchmark_id": "m46-1", "precision": 0.97}
        assert E.validate(det) == []
    peak = E.finding("QC-A2-PEAK_OVER", "BLOCK", "metadata", {}, "đỉnh", "final:1", SHA, "x")
    assert E.validate(peak) == []                                               # đang chặn từ trước: chỉ chuẩn hóa cách ghi


def test_finding_never_exceeds_the_code_ceiling():
    assert E.finding("QC-L13-CONTINUITY", "BLOCK", "vlm", {}, "x", "job:1", None, "x")["severity"] == "REVIEW"


# ---- adapter (test_qc_evidence_adapters) ---------------------------------------------------------------------------------------
def test_from_final_qc_maps_codes_and_levels():
    res = {"issues": [{"code": "length", "level": "block", "msg": "dài", "at": None}, {"code": "peak", "level": "warn", "msg": "đỉnh"},
                      {"code": "silence", "level": "warn", "msg": "lặng", "at": 3.0}, {"code": "music_hole", "level": "block", "msg": "nhạc"},
                      {"code": "black_frame", "level": "warn", "msg": "đen", "at": 2.0}]}
    got = E.from_final_qc(res, "final:1", SHA)
    assert [(f["qc_code"], f["severity"]) for f in got] == [("QC-A4-LENGTH_MISMATCH", "BLOCK"), ("QC-A2-PEAK_OVER", "REVIEW"),
                                                           ("QC-A2-SILENT_GAP", "REVIEW"), ("QC-A4-BLACK_FRAME", "REVIEW")]
    assert all(E.validate(f) == [] for f in got)                      # music_hole chưa có mã M4.1 → bỏ có chủ đích


def test_from_final_qc_keeps_review_when_final_qc_only_warns():
    got = E.from_final_qc({"issues": [{"code": "black_frame", "level": "warn", "msg": "đen", "at": 2.0}]}, "final:1", SHA)
    # mức tối đa của mã là BLOCK nhưng final_qc chỉ "warn" → finding không được tự nâng lên chặn khi chưa benchmark
    assert got[0]["severity"] == "REVIEW"


def test_from_clip_measure():
    m = {"motion": {"flag": "jerk", "why": "giật ở 2 s", "cuts": [], "jerks": [2.0], "freezes": [1.9]}, "look": {"flag": None},
         "flags": ["jerk"]}
    got = E.from_clip_measure(m, "job:5", SHA)
    assert [f["qc_code"] for f in got] == ["QC-V2-JERK_FREEZE"] and E.validate(got[0]) == []


def test_normalize_shadow_records_of_m42_and_m43():
    m42 = {"artifact_id": "job:7", "artifact_sha": SHA, "findings": [
        {"qc_code": "QC-V2-STILL_OVER_1_5S", "error_type": "V2", "registry_ids": ["P31-G51"], "severity": "REVIEW",
         "evidence_type": "segment", "evidence": {}}]}
    m43 = {"project_id": 3, "expected": [{"qc_code": "QC-L13-CONTINUITY", "error_type": "L13", "registry_ids": ["P31-G52"],
                                          "severity": "REVIEW", "evidence_type": "metadata", "evidence": {}}], "observed": []}
    got = E.normalize_shadow(m42) + E.normalize_shadow(m43)
    assert [g["artifact_id"] for g in got] == ["job:7", "project:3"]
    assert all(E.validate(g) == [] for g in got)


# ---- migration + ghi shadow ----------------------------------------------------------------------------------------------------
def test_opening_the_database_creates_no_table(tmp_path):
    conn = connect(str(tmp_path / "m.sqlite"))
    assert not E.has_tables(conn)


def test_migrate_up_down(tmp_path):
    conn = connect(str(tmp_path / "m.sqlite"))
    assert E.migrate_up(conn) is True and E.migrate_up(conn) is False and E.has_tables(conn)
    with ON:
        E.record(conn, None, 1, "final", "Q9", "t", [_f()])
    with pytest.raises(ValueError):
        E.migrate_down(conn)
    E.migrate_down(conn, force=True)
    assert not E.has_tables(conn)


def test_record_flag_off_writes_nothing(tmp_path):
    conn = connect(str(tmp_path / "m.sqlite"))
    E.migrate_up(conn)
    with OFF:
        assert E.record(conn, str(tmp_path), 1, "final", "Q9", "t", [_f()]) is None
    assert conn.execute("SELECT COUNT(*) FROM qc_runs").fetchone()[0] == 0
    assert not os.path.exists(tmp_path / "1" / "qc_shadow")


def test_record_to_tables_or_to_jsonl(tmp_path):
    conn = connect(str(tmp_path / "m.sqlite"))
    with ON:
        rec = E.record(conn, str(tmp_path), 1, "final", "Q9", "t", [_f()])            # chưa có bảng → jsonl
    assert rec["stored"] == "jsonl"
    line = json.loads(open(tmp_path / "1" / "qc_shadow" / "qc_evidence.jsonl", encoding="utf-8").read())
    assert line["mode"] == "shadow" and line["findings"][0]["qc_code"] == "QC-V2-STILL_OVER_1_5S"
    E.migrate_up(conn)
    with ON:
        rec = E.record(conn, str(tmp_path), 1, "final", "Q9", "t", [_f(), _f()])
    assert rec["stored"] == "db"
    assert conn.execute("SELECT COUNT(*) FROM qc_findings WHERE qc_run_id=?", (rec["qc_run_id"],)).fetchone()[0] == 2


def test_record_never_raises():
    conn = mock.Mock()
    conn.execute.side_effect = RuntimeError("db hỏng")
    with ON, mock.patch("core.diag.record") as diag:
        assert E.record(conn, None, 1, "final", "Q9", "t", [_f()]) is None
    assert diag.call_args.args[4] == "qc_evidence"


# ---- shadow không đổi hành vi QC ----------------------------------------------------------------------------------------------
def test_final_qc_result_is_the_same_with_the_flag(tmp_path):
    from core import final_qc
    from core.pipeline import Pipeline
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("dp4")
    fin = {"id": 9, "path": str(tmp_path / "none.mp4"), "manifest": '{"timeline": [{"idx": 1, "seconds": 9.0}]}'}
    with mock.patch("core.lineage.latest_output", side_effect=lambda conn, pid_, kind: fin if kind == "final" else None):
        with OFF:
            a = final_qc.run(p, pid, str(tmp_path), frames=False)
        with ON:
            b = final_qc.run(p, pid, str(tmp_path), frames=False)
    assert a == b
    rows = [json.loads(x) for x in open(tmp_path / str(pid) / "qc_shadow" / "qc_evidence.jsonl", encoding="utf-8")]
    assert rows[0]["qc_path"] == "Q9" and rows[0]["scope"] == "final"
