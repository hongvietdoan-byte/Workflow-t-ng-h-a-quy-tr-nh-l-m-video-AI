"""Nghiệm thu độc lập: đủ ma trận, không nâng cổng vì có bản ghi."""
import ast
import importlib
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def modules():
    with patch.object(os, "environ", {"PYTHONUTF8": "1"}):
        yield (importlib.import_module("tools.kiem_cong"),
               importlib.import_module("devsys.plan_progress"))


def test_catalog_matches_every_code_done_gate_open(modules):
    _, pp = modules
    catalog = json.loads((ROOT / "docs/kiem_cong_catalog.json").read_text(encoding="utf-8"))
    plan = pp.parse((ROOT / catalog["plan"]).read_text(encoding="utf-8"))
    expected = {t["id"] for w in plan["waves"] for t in w["tasks"]
                if t["status"] == "✅" and t["gate_status"] != "✅"}
    rows = catalog["rows"]
    assert len(rows) == len({r["id"] for r in rows})
    assert {r["id"] for r in rows} == expected
    matrix = (ROOT / "docs/KIEM_CONG_GOP_2026-10-25.md").read_text(encoding="utf-8")
    for row in rows:
        assert row["criteria"] and row["offline"] and row["location"] and row["risk"]
        assert "| " + row["id"] + " ·" in matrix


def test_every_proposed_flag_exists_in_static_registry(modules):
    catalog = json.loads((ROOT / "docs/kiem_cong_catalog.json").read_text(encoding="utf-8"))
    nodes = ast.parse((ROOT / "core/features.py").read_text(encoding="utf-8")).body
    node = next(n for n in nodes if isinstance(n, ast.AnnAssign)
                and isinstance(n.target, ast.Name) and n.target.id == "FEATURES")
    registry = ast.literal_eval(node.value)
    assert all(f in registry for row in catalog["rows"] for f in row["flags"])


def test_flag_dependency_closure_is_explicit_in_each_row():
    catalog = json.loads((ROOT / "docs/kiem_cong_catalog.json").read_text(encoding="utf-8"))
    nodes = ast.parse((ROOT / "core/features.py").read_text(encoding="utf-8")).body
    node = next(n for n in nodes if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "REQUIRES" for t in n.targets))
    requires = {ast.literal_eval(k): ast.literal_eval(v)
                for k, v in zip(node.value.keys, node.value.values) if k is not None}
    requires.update({"byd_fields_a2" + x: ("byd_fields",) for x in "abcdef"})
    # Core world_map.sentences_enabled checks this parent outside REQUIRES.
    requires["world_map_sentences"] = ("world_map",)
    for row in catalog["rows"]:
        flags = set(row["flags"])
        assert all(set(requires.get(f, ())) <= flags for f in flags)


def test_full_gate_does_not_pass_on_evidence_counts_alone(modules):
    checker, _ = modules
    facts = {name: {"status": "ĐẠT", "count": 10, "valid": 10,
                    "invalid": 0, "reasons": []}
             for name in ("jobs", "sent_package", "diag_events", "ui_step", "ledger", "qc", "overrides")}
    rows = [{"id": "M5.2", "title": "Cổng phát hành", "evidence": list(facts),
             "one_project": True, "manual": True}]
    result = checker.evaluate_catalog(rows, facts)
    assert result[0]["status"] == "THIẾU DỮ LIỆU"
    assert result[0].get("reasons")


def test_missing_one_required_source_never_passes(modules):
    checker, _ = modules
    facts = {"jobs": {"status": "ĐẠT", "count": 1, "valid": 1, "invalid": 0, "reasons": []},
             "ledger": {"status": "THIẾU DỮ LIỆU", "count": 0, "valid": 0,
                        "invalid": 0, "reasons": ["missing_table"]}}
    result = checker.evaluate_catalog(
        [{"id": "M1.6", "evidence": ["jobs", "ledger"], "one_project": True, "manual": False}], facts)
    assert result[0]["status"] != "ĐẠT"


def test_malformed_fake_payload_is_not_echoed_in_report(modules, tmp_path):
    checker, _ = modules
    path = tmp_path / "snapshot.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE jobs (id INTEGER, project_id INTEGER, scene_id INTEGER, "
                 "type TEXT, state TEXT, created_at TEXT, updated_at TEXT, sent_package TEXT)")
    conn.execute("INSERT INTO jobs VALUES (1,1,1,'video_gen','succeeded',"
                 "'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',?)",
                 ('{fake_private_payload_CX',))
    conn.commit()
    conn.close()
    result = checker.run_report(path, 1)
    # Only a deliberately fake sentinel is examined, never real credentials.
    assert "fake_private_payload_CX" not in json.dumps(result)
    assert result["evidence"]["sent_package"]["status"] != "ĐẠT"


def test_unknown_job_state_is_not_valid_evidence(modules, tmp_path):
    checker, _ = modules
    path = tmp_path / "snapshot.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE jobs (id INTEGER, project_id INTEGER, type TEXT, state TEXT, created_at TEXT)")
    conn.execute("INSERT INTO jobs VALUES (1,1,'video_gen','invented_state','2026-01-01T00:00:00Z')")
    conn.commit()
    conn.close()
    assert checker.run_report(path, 1)["evidence"]["jobs"]["status"] != "ĐẠT"


def test_cross_project_job_reference_cannot_be_valid_ledger(modules, tmp_path):
    checker, _ = modules
    path = tmp_path / "snapshot.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE jobs (id INTEGER, project_id INTEGER, type TEXT, state TEXT, created_at TEXT)")
    conn.execute("INSERT INTO jobs VALUES (2,2,'video_gen','succeeded','2026-01-01T00:00:00Z')")
    conn.execute("CREATE TABLE usage_events (project_id INTEGER, job_id INTEGER, kind TEXT, quantity REAL, at TEXT)")
    conn.execute("INSERT INTO usage_events VALUES (1,2,'video',1,'2026-01-01T00:00:00Z')")
    conn.commit()
    conn.close()
    assert checker.run_report(path, 1)["evidence"]["ledger"]["status"] != "ĐẠT"


def test_missing_parent_scope_cannot_validate_foreign_job(modules, tmp_path):
    checker, _ = modules
    path = tmp_path / "snapshot.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE usage_events (project_id INTEGER, job_id INTEGER, kind TEXT, quantity REAL, at TEXT)")
    conn.execute("INSERT INTO usage_events VALUES (1,2,'video',1,'2026-01-01T00:00:00Z')")
    conn.commit()
    conn.close()
    assert checker.run_report(path, 1)["evidence"]["ledger"]["status"] != "ĐẠT"


@pytest.mark.parametrize("known_parent,reason,status", [
    (True, "invalid_scope", "CHƯA ĐẠT"),
    (False, "missing_scope", "THIẾU DỮ LIỆU"),
])
def test_malformed_override_keeps_scope_diagnostics(modules, tmp_path, known_parent, reason, status):
    checker, _ = modules
    path = tmp_path / "snapshot.sqlite"
    conn = sqlite3.connect(path)
    if known_parent:
        conn.execute("CREATE TABLE scenes (id INTEGER, project_id INTEGER, data TEXT)")
        conn.execute("INSERT INTO scenes VALUES (2,2,'{}')")
    conn.execute("CREATE TABLE overrides (project_id INTEGER, scene_id INTEGER, data TEXT)")
    conn.execute("INSERT INTO overrides VALUES (1,2,'{')")
    conn.commit()
    conn.close()
    fact = checker.run_report(path, 1, since="2026-01-01T00:00:00Z")["evidence"]["overrides"]
    assert fact["status"] == status
    assert reason in fact["reasons"]
