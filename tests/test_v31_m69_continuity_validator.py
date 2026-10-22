"""V3.1 M6.9 (C-M61-M69): Continuity Validator SHADOW — gom phát hiện continuity_state (M3.4) + qc_evidence (M4.1) + observed M4.2/M4.3,
định tuyến về vai chủ theo Role Registry (M6.1) + devsys/errors.json, CHỈ ghi bằng chứng <dự án>/crew/continuity_validator.jsonl.
Không chặn, không giữ job, không gọi Claude/API. Cờ `continuity_validator` TẮT (hoặc crew_registry TẮT) = không chạy gì.
Fixture tổng hợp tái hiện #31 G51 (súng biến mất) / G52 (logic chuỗi) / G1 (đổi nơi chốn) → vai chủ đúng."""
import json
import os
from unittest import mock

from core import continuity_validator as V
from core import crew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "v31_m69_p31_continuity.json")
BOTH = mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_VALIDATOR": "1", "FEATURE_CREW_REGISTRY": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_VALIDATOR": "", "FEATURE_CREW_REGISTRY": ""})
NO_REG = mock.patch.dict(os.environ, {"FEATURE_CONTINUITY_VALIDATOR": "1", "FEATURE_CREW_REGISTRY": ""})


def _fixture():
    return json.load(open(FIXTURE, encoding="utf-8"))


def test_flag_registered_off_unverified_and_needs_registry():
    from core import features
    assert V.FLAG == "continuity_validator" and features.FEATURES[V.FLAG]["verified"] is False
    assert features.REQUIRES[V.FLAG] == ("crew_registry",)
    with OFF:
        assert not V.enabled()


def test_registered_in_areas_and_golden():
    areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))
    a = next(x for x in areas["areas"] if "core/continuity_validator.py" in x["code"])
    assert "tests/test_v31_m69_continuity_validator.py" in a["tests"] and V.FLAG in a["flags"]
    gold = json.load(open(os.path.join(ROOT, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
    blocks = [v["flags"] for v in gold.values() if isinstance(v, dict) and isinstance(v.get("flags"), dict)]
    assert len(blocks) == 2 and all(b.get(V.FLAG) is False for b in blocks)


def test_fixture_p31_routes_to_the_right_roles():
    fx = _fixture()
    rec = V.build(fx["rows"], fx.get("observed") or [], fx.get("qc_evidence") or [], crew.load())
    got = {(r["finding"]["qc_code"], r["finding"].get("attribute"), tuple(r["finding"]["shots"])): r["owner"] for r in rec["routed"]}
    assert got[("QC-L13-CONTINUITY", "cam", (28, 29))] == "director"                     # G51/G52: lệch ở BYĐ (layer byd) → Director sửa
    assert got[("QC-L13-CONTINUITY", "noi", (34, 35))] == "director"                     # G1: đổi nơi chốn trong BYĐ → Director xác nhận ý đồ
    assert got[("QC-L7-PROP_MISSING", None, (35,))] == "artist_3d"                       # G1: khối sân khấu render vào nền (layer stage)
    assert got[("QC-L13-CONTINUITY", "huong_khung", (35, 36))] == "director"             # G41: hướng chạy (L3)
    assert got[("QC-V2-STILL_OVER_1_5S", None, (13,))] == "video_prompt_artist"         # M4.2 observed (G51: đơ 6 s)
    assert got[("QC-L9-HORIZON_MISMATCH", None, (9,))] == "cinematographer"              # qc_evidence mã có vai riêng
    assert all(r["owner"] != "continuity_validator" for r in rec["routed"])              # QC độc lập
    assert rec["mode"] == "shadow" and rec["counts"]["routed"] == len(rec["routed"]) and rec["unrouted"] == []


def test_routed_item_says_how_and_whom_to_escalate():
    fx = _fixture()
    rec = V.build(fx["rows"], fx.get("observed") or [], fx.get("qc_evidence") or [], crew.load())
    r = next(r for r in rec["routed"] if r["owner"] == "artist_3d")
    assert r["via"].startswith("layer:stage") and r["registry_ids"] == ["P31-G1"] and "artist_3d" in r["candidates"]
    assert r["escalate"]["director"] and r["escalate"]["executive_producer"]
    assert r["phieu"] == {"to_role": "artist_3d", "status": "returned", "shadow": True}


def test_system_errors_go_to_engineer_not_creative_role():
    ev = [{"qc_code": "QC-L13-CONTINUITY", "registry_ids": ["P31-G33"], "evidence": {"shots": [3]}, "why": "API hết tiền"}]
    rec = V.build([], [], ev, crew.load())
    assert rec["routed"][0]["owner"] == "engineer" and "hop_thu" in rec["routed"][0]["kenh"]


def test_missing_inputs_are_said_not_silent():
    rec = V.build([], [], [], crew.load())
    assert rec["routed"] == [] and rec["inputs"]["rows"] == 0
    assert [t.split(":")[0] for t in rec["inputs"]["thieu"]] == ["rows", "observed", "qc_evidence"]


def _project(tmp_path):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("m69")
    gun = [{"vat": "AWM", "nguoi": "KELLY", "cach": "cam"}]
    for idx, vat in ((28, gun), (29, [])):
        sid = p.create_scene(pid, idx, f"S{idx}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY"], "sequence": "9", "byd": {"vat": vat}}),
                                                              sid))
    p.conn.commit()
    return p, pid


def _counts(p):
    return {t: p.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("jobs", "scenes", "motion_prompts", "usage_events")}


def test_run_flag_off_does_nothing(tmp_path):
    p, pid = _project(tmp_path)
    with OFF, mock.patch.object(crew, "load", side_effect=AssertionError("không được đọc registry")), \
            mock.patch("core.continuity_state.build", side_effect=AssertionError("không được dựng")):
        assert V.run(p, pid, str(tmp_path)) is None
    assert not os.path.exists(V.result_path(str(tmp_path), pid))


def test_run_without_registry_flag_does_nothing_but_says_so(tmp_path):
    p, pid = _project(tmp_path)
    with NO_REG, mock.patch("core.diag.record") as rec:
        assert V.run(p, pid, str(tmp_path)) is None
    assert not os.path.exists(V.result_path(str(tmp_path), pid))
    assert rec.called and "crew_registry" in rec.call_args.args[3]


def test_run_flag_on_writes_only_evidence(tmp_path):
    p, pid = _project(tmp_path)
    before = _counts(p)
    with BOTH, mock.patch("core.llm_runner.tagged", side_effect=AssertionError("không gọi Claude")):
        rec = V.run(p, pid, str(tmp_path))
        V.run(p, pid, str(tmp_path))
    assert rec and rec["routed"][0]["owner"] == "director"
    lines = open(V.result_path(str(tmp_path), pid), encoding="utf-8").read().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["mode"] == "shadow"                  # nối 1 dòng TÓM TẮT mỗi lần
    assert "routed" not in json.loads(lines[0]) and json.loads(lines[0])["counts"]["routed"] == 1
    latest = json.load(open(V.latest_path(str(tmp_path), pid), encoding="utf-8"))
    assert latest["routed"][0]["owner"] == "director"                                    # bản đầy đủ: ghi đè
    assert _counts(p) == before                                                            # không job, không sửa dữ liệu
    assert not os.path.exists(os.path.join(str(tmp_path), str(pid), "world", "continuity_state.json"))  # không ghi tệp của M3.4


def test_run_reads_qc_evidence_jsonl(tmp_path):
    p, pid = _project(tmp_path)
    d = tmp_path / str(pid) / "qc_shadow"
    d.mkdir(parents=True)
    (d / "qc_evidence.jsonl").write_text(json.dumps({"qc_run_id": "x", "findings": [
        {"qc_code": "QC-L6-SIZE_MISMATCH", "registry_ids": ["P33-A5"], "evidence": {"shots": [28]}, "why": "cỡ cảnh lệch"}]}) + "\n",
        encoding="utf-8")
    with BOTH:
        rec = V.run(p, pid, str(tmp_path))
    assert rec["inputs"]["qc_evidence"] == 1
    assert any(r["finding"]["qc_code"] == "QC-L6-SIZE_MISMATCH" and r["owner"] == "cinematographer" for r in rec["routed"])


def test_run_never_raises(tmp_path):
    p, pid = _project(tmp_path)
    with BOTH, mock.patch.object(V, "build", side_effect=RuntimeError("x")):
        assert V.run(p, pid, str(tmp_path)) is None


def test_sequence_check_calls_validator_after_continuity_state(tmp_path):
    from core import continuity_state, sequence_logic
    p, pid = _project(tmp_path)
    groups = {"9": {"rows": [{"idx": 28}, {"idx": 29}], "shown": {28, 29}, "sheets": []}}
    order = []
    with mock.patch.dict(os.environ, {"FEATURE_QC_SEQUENCE_LOGIC": "1"}), \
         mock.patch.object(sequence_logic, "sequence_sheets", return_value=groups), \
         mock.patch.object(sequence_logic.claude_tasks, "_run", return_value={"ok": True, "issues": []}), \
         mock.patch.object(sequence_logic.prompts, "world_bible_text", return_value=""), \
         mock.patch("core.continuity_shadow.run", side_effect=lambda *a: order.append("m43")), \
         mock.patch.object(continuity_state, "run", side_effect=lambda *a: order.append("m34")), \
         mock.patch.object(V, "run", side_effect=lambda *a: order.append("m69")):
        sequence_logic.check(p, pid, object(), str(tmp_path))
    assert order == ["m43", "m34", "m69"]


def test_cli_fixture_offline(tmp_path, capsys):
    assert V.main(["--fixture", FIXTURE, "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "video_prompt_artist" in out and "artist_3d" in out
    assert os.path.exists(os.path.join(str(tmp_path), "continuity_validator.jsonl"))


def test_module_never_sends_or_calls_models():
    import inspect
    src = inspect.getsource(V)
    for bad in ("create_job", "_insert_job", ".submit(", "spend_gate", "llm_runner", "claude_tasks", "reject(", "approve(", "retry("):
        assert bad not in src, bad


# ---- rà C-M61-M69 (VỪA-1, VỪA-2, THẤP) -----------------------------------------------------------------------------------------------
def test_byd_layer_goes_to_the_role_that_can_fix_it():
    fx = _fixture()
    rec = V.build(fx["rows"], [], [], crew.load())
    r = next(x for x in rec["routed"] if x["finding"]["attribute"] == "cam")
    assert r["owner"] == "director" and r["fix_field"] == "scenes.data.byd" and r["owner_cannot_fix"] is False
    assert crew.can_write(r["owner"], r["fix_field"])
    assert r["registry_owner"] == "video_prompt_artist"                                   # vai của loại lỗi vẫn được ghi


def test_no_layer_stage_owner_marked_when_cannot_fix():
    ev = [{"qc_code": "QC-L13-CONTINUITY", "registry_ids": ["P31-G51"], "evidence": {"shots": [3]},
           "actionability": {"layer": "lop_la"}, "why": "x"}]
    r = V.build([], [], ev, crew.load())["routed"][0]
    assert r["owner"] == "video_prompt_artist" and r["fix_field"] is None and r["owner_cannot_fix"] is None


def test_fallback_is_said_in_the_record():
    ev = [{"qc_code": "QC-L13-CONTINUITY", "registry_ids": ["KHONG-CO"], "evidence": {"shots": [3]}, "why": "x"}]
    r = V.build([], [], ev, crew.load())["routed"][0]
    assert r["via"] == "fallback" and "không vai nào nhận" in r["canh_bao"]


def test_odd_shots_do_not_crash():
    ev = [{"qc_code": "QC-L9-HORIZON_MISMATCH", "evidence": {"shots": [9, [1], {"a": 1}, "x"]}, "why": "x"}]
    assert V.build([], [], ev, crew.load())["routed"][0]["finding"]["shots"] == [9]


def _jsonl(tmp_path, pid, recs):
    d = tmp_path / str(pid) / "qc_shadow"
    d.mkdir(parents=True, exist_ok=True)
    (d / "qc_evidence.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")


def test_evidence_only_latest_run_and_open(tmp_path):
    p, pid = _project(tmp_path)
    old = {"qc_run_id": "r1", "scope": "final", "qc_path": "Q9", "findings": [
        {"qc_code": "QC-A4-BLACK_FRAME", "evidence": {}, "why": "đen (đã sửa)"}]}
    new = {"qc_run_id": "r2", "scope": "final", "qc_path": "Q9", "findings": [
        {"qc_code": "QC-A4-FREEZE_FRAME", "evidence": {}, "why": "đứng hình", "status": "open"},
        {"qc_code": "QC-A2-PEAK_OVER", "evidence": {}, "why": "đã xử lý", "status": "resolved"}]}
    other = {"qc_run_id": "r3", "scope": "clip", "qc_path": "Q3", "findings": [{"qc_code": "QC-V1-DRIFT", "evidence": {"shots": [28]}, "why": "trôi"}]}
    _jsonl(tmp_path, pid, [old, other, new])
    ev = V.read_evidence(p.conn, str(tmp_path), pid)
    assert sorted(f["qc_code"] for f in ev) == ["QC-A4-FREEZE_FRAME", "QC-V1-DRIFT"]
    assert {f["qc_run_id"] for f in ev} == {"r2", "r3"}


def test_evidence_from_tables(tmp_path):
    from core import qc_evidence
    p, pid = _project(tmp_path)
    qc_evidence.migrate_up(p.conn)
    with mock.patch.dict(os.environ, {"FEATURE_QC_EVIDENCE": "1"}):
        qc_evidence.record(p.conn, None, pid, "final", "Q9", "v", [dict(qc_evidence.finding(
            "QC-A4-BLACK_FRAME", "REVIEW", "segment", {"at": 1}, "đen cũ", "a", None, "s"))])
        qc_evidence.record(p.conn, None, pid, "final", "Q9", "v", [dict(qc_evidence.finding(
            "QC-A4-FREEZE_FRAME", "REVIEW", "segment", {"at": 2}, "đứng hình", "a", None, "s"), status="open"),
            dict(qc_evidence.finding("QC-A2-PEAK_OVER", "REVIEW", "segment", {"at": 3}, "x", "a", None, "s"), status="resolved")])
    ev = V.read_evidence(p.conn, str(tmp_path), pid)
    assert [f["qc_code"] for f in ev] == ["QC-A4-FREEZE_FRAME"] and ev[0]["qc_run_id"]
    with BOTH:
        rec = V.run(p, pid, str(tmp_path))
    assert any(r["finding"]["qc_code"] == "QC-A4-FREEZE_FRAME" and r["owner"] == "editor_vfx" for r in rec["routed"])


def test_run_end_to_end_with_m42_m43_files(tmp_path):
    p, pid = _project(tmp_path)
    sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=28", (pid,)).fetchone()[0]
    jid = p.create_job(sid, "video_gen")
    d = tmp_path / str(pid) / "qc_shadow"
    d.mkdir(parents=True)
    (d / "video_qc.jsonl").write_text(json.dumps({"job_ids": [jid], "findings": [{"qc_code": "QC-V2-STILL_OVER_1_5S", "registry_ids": ["P31-G51"],
                                                                                  "severity": "REVIEW", "why": "đứng yên",
                                                                                  "actionability": {"layer": "video"}}]}) + "\n", encoding="utf-8")
    seq = tmp_path / str(pid) / "qc_set" / "sequence"
    seq.mkdir(parents=True)
    (seq / "continuity_shadow.json").write_text(json.dumps({"observed": [{"qc_code": "QC-L13-CONTINUITY", "registry_ids": ["P31-G52"],
                                                                          "evidence": {"shots": [29]}, "why": "nền đổi"}]}), encoding="utf-8")
    with BOTH:
        rec = V.run(p, pid, str(tmp_path))
    srcs = {(r["finding"]["source"], r["finding"]["qc_code"]): r["owner"] for r in rec["routed"]}
    assert srcs[("M4.2", "QC-V2-STILL_OVER_1_5S")] == "video_prompt_artist"
    assert srcs[("M4.3", "QC-L13-CONTINUITY")] == "video_prompt_artist"
    assert srcs[("M3.4", "QC-L13-CONTINUITY")] == "director"
