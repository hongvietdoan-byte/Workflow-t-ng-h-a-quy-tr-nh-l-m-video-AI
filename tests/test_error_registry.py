"""V3.1 M0.4 (D09): hợp đồng sổ lỗi devsys/errors.json — mỗi luật một ca đỏ (sổ sai) + sổ thật trong git phải sạch."""
import copy
import json
import os
import subprocess
import sys

import pytest

from devsys import errors

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _item(**kw):
    it = {"id": "P31-G1", "alias": ["G1"], "title": "Khối giữ chỗ bị mang sang cảnh khác",
          "source_document": "docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md:12", "project_ids": [31], "shot_ids": [], "job_ids": [],
          "stage": "L6", "category": "continuity", "root_cause_hypothesis": "", "root_cause_confirmed": "", "root_cause_id": None,
          "evidence": "x", "severity": "vua", "status": "OPEN", "first_seen": "2026-10-18", "last_seen": "2026-10-18",
          "affected_flows": [], "owner": "", "fix_commit": [], "tests": [], "real_run_evidence": [], "plan_workstream": "WS3",
          "plan_task": "M2.4", "dependencies": [], "reopen_history": [], "status_reason": ""}
    it.update(kw)
    return it


def _doc(*items):
    return {"schema_version": 1, "items": list(items)}


def test_clean_doc_has_no_problem():
    assert errors.problems(_doc(_item())) == []


def test_duplicate_id_and_alias_collision():
    p = errors.problems(_doc(_item(), _item()))
    assert any("trùng" in x and "P31-G1" in x for x in p)
    p = errors.problems(_doc(_item(), _item(id="P31-G2", alias=["G1"])))
    assert any("alias" in x for x in p)


def test_id_shape():
    assert any("dạng mã" in x for x in errors.problems(_doc(_item(id="g1"))))


def test_missing_field():
    it = _item()
    del it["evidence"]
    assert any("thiếu trường" in x for x in errors.problems(_doc(it)))


def test_unknown_status():
    assert any("status" in x for x in errors.problems(_doc(_item(status="DONE"))))


def test_verified_needs_commit_tests_and_real_run():
    p = errors.problems(_doc(_item(status="VERIFIED", fix_commit=["abc1234"], tests=["tests/test_x.py"])))
    assert any("real_run_evidence" in x for x in p)
    p = errors.problems(_doc(_item(status="VERIFIED", tests=["tests/test_x.py"], real_run_evidence=["#34 job 1"])))
    assert any("fix_commit" in x for x in p)
    ok = _item(status="VERIFIED", fix_commit=["abc1234"], tests=["tests/test_x.py"], real_run_evidence=["#34 job 1200"])
    assert errors.problems(_doc(ok)) == []


def test_fixed_unverified_needs_commit_and_tests_not_real_run():
    p = errors.problems(_doc(_item(status="FIXED_UNVERIFIED")))
    assert any("fix_commit" in x for x in p) and any("tests" in x for x in p)
    assert errors.problems(_doc(_item(status="FIXED_UNVERIFIED", fix_commit=["abc1234"], tests=["t"]))) == []


def test_wont_fix_needs_reason():
    assert any("lý do" in x for x in errors.problems(_doc(_item(status="WONT_FIX", status_reason=""))))
    assert errors.problems(_doc(_item(status="WONT_FIX", status_reason="không phải lỗi"))) == []


def test_open_needs_workstream():
    assert any("plan_workstream" in x for x in errors.problems(_doc(_item(plan_workstream=""))))
    assert any("plan_workstream" in x for x in errors.problems(_doc(_item(plan_workstream="WS9"))))


def test_reopened_needs_history():
    assert any("reopen_history" in x for x in errors.problems(_doc(_item(status="REOPENED"))))


def test_stage_severity_and_dates():
    assert any("stage" in x for x in errors.problems(_doc(_item(stage="L99"))))
    assert errors.problems(_doc(_item(stage=None))) == []          # lỗi hạ tầng không thuộc khâu nào
    assert any("severity" in x for x in errors.problems(_doc(_item(severity="nặng"))))
    assert any("last_seen" in x for x in errors.problems(_doc(_item(first_seen="2026-10-19", last_seen="2026-10-18"))))


def test_dependencies_and_root_cause_point_to_known_ids():
    assert any("dependencies" in x for x in errors.problems(_doc(_item(dependencies=["P31-G999"]))))
    assert any("root_cause_id" in x for x in errors.problems(_doc(_item(root_cause_id="P31-G999"))))
    two = _doc(_item(), _item(id="P31-G46", alias=["G46"], root_cause_id="P31-G1"))
    assert errors.problems(two) == []


def test_schema_version():
    d = _doc(_item())
    d["schema_version"] = 99
    assert any("schema_version" in x for x in errors.problems(d))


def test_real_registry_is_clean():
    doc = errors.load()
    assert errors.problems(doc) == []


def test_real_registry_coverage_and_no_invented_code():
    doc = errors.load()
    aliases = {a for it in doc["items"] for a in it["alias"]}
    want = {f"G{n}" for n in range(1, 59) if n != 25} | {f"A{n}" for n in range(1, 16)} | {f"B{n}" for n in range(1, 13)}
    assert want <= aliases
    assert "G25" not in aliases                                     # khuyết trong tài liệu nguồn — không bịa
    assert "G25" in doc.get("missing_codes", {})


def test_real_registry_sources_exist_and_name_the_code():
    for it in errors.load()["items"]:
        path, _, line = it["source_document"].partition(":")
        full = os.path.join(ROOT, path)
        assert os.path.exists(full), it["id"]
        text = open(full, encoding="utf-8").read().split("\n")[int(line) - 1]
        assert any(a in text for a in it["alias"]), (it["id"], it["source_document"])


def test_real_registry_never_verified_without_real_run():
    for it in errors.load()["items"]:
        assert it["status"] != "VERIFIED" or it["real_run_evidence"], it["id"]


def test_cli_check_and_list():
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run([sys.executable, "-m", "devsys.errors", "check"], cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run([sys.executable, "-m", "devsys.errors", "list", "--status", "OPEN"], cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "P31-G1" in r.stdout


def test_cli_check_fails_on_bad_file(tmp_path):
    bad = copy.deepcopy(_doc(_item(status="VERIFIED")))
    p = tmp_path / "e.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "devsys.errors", "check", "--file", str(p)], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONUTF8="1"))
    assert r.returncode == 1
