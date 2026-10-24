"""CX22-REPORT: fixtures giả, không đọc nhật ký/CSDL thật."""
import hashlib
import json
import os
import sqlite3
from unittest.mock import patch
import pytest

@pytest.fixture
def report_env(tmp_path):
    with patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path)}):
        from tools import project_report as R
        root = tmp_path / "repo"
        (root / "devsys").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "devsys/plans.json").write_text(json.dumps([{"chinh": True, "kieu": "viec_s", "file": "docs/plan.md"}]))
        (root / "docs/plan.md").write_text("### M0 — Giả\n- [x] M0.1 · Việc giả · nặng:1 · ✅\n", encoding="utf-8")
        yield R, root

def _log(folder, name, rows):
    folder.mkdir(exist_ok=True)
    (folder / name).write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

def _row(mid="a", tokens=10, **extra):
    return {"sessionId": "fake-session", "timestamp": "2026-10-23T18:00:00Z", "isSidechain": False,
            "message": {"id": mid, "model": "claude-sonnet-4", "usage": {"input_tokens": tokens, "output_tokens": 2}, "content": "SECRET_CANARY_EMAIL@example.test/private/path"}, **extra}

def test_seven_sections_unknown_and_no_private_payload(report_env):
    R, root = report_env
    report = R.collect_report(root, as_of="2026-10-24")
    md = R.render_markdown(report)
    assert len(report["sections"]) == 7
    assert "không có dữ liệu" in md
    assert {"tokens", "estimated_usd", "actual_usd", "held_usd"} <= report["metrics"].keys()
    assert report["metrics"]["actual_usd"]["value"] is None
    assert all({"source", "measured_at", "delta", "reason"} <= m.keys() for m in report["metrics"].values())
    assert "SECRET_CANARY" not in md

def test_plan_code_is_not_gate_completion(report_env):
    R, root = report_env
    report = R.collect_report(root, as_of="2026-10-24")
    assert report["metrics"]["code_pct"]["value"] == 100
    assert report["metrics"]["gate_pct"]["value"] == 0

def test_session_cumulative_snapshots_dedup_cross_file_and_month_saigon(report_env):
    R, root = report_env
    logs = root / "fake_sessions"
    _log(logs, "one.jsonl", [_row(), _row(tokens=15)])
    _log(logs, "two.jsonl", [_row(tokens=12), _row("b", 3, isSidechain=True, timestamp="2026-09-30T18:00:00Z")])
    result = R.collect_report(root, as_of="2026-10-24", session_dir=logs)
    tokens = result["token_groups"]
    assert {(x["month"], x["role"], x["input_tokens"]) for x in tokens} == {("2026-10", "main", 15), ("2026-10", "agent", 3)}
    assert result["metrics"]["tokens"]["value"] == 22
    serialized = json.dumps(result)
    assert "SECRET_CANARY" not in serialized and "fake-session" not in serialized

def test_missing_usage_conflict_and_missing_id_are_unknown_not_zero(report_env):
    R, root = report_env
    logs = root / "fake_sessions"
    conflict = _row(); conflict["message"]["model"] = "different-model"
    missing = _row("missing"); del missing["message"]["usage"]
    noid = _row(); del noid["message"]["id"]
    _log(logs, "data.jsonl", [_row(), conflict, missing, noid])
    result = R.collect_report(root, as_of="2026-10-24", session_dir=logs)
    assert result["metrics"]["tokens"]["value"] is None
    assert result["coverage"]["conflicts"] == 1 and result["coverage"]["missing_id"] == 1
    assert result["warnings"]

def test_readonly_db_does_not_create_bootstrap_or_touch_bytes(report_env):
    R, root = report_env
    db = root / "fake.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE usage_events(id INTEGER PRIMARY KEY, project_id INTEGER, kind TEXT, at TEXT, usd REAL)")
    conn.execute("INSERT INTO usage_events VALUES(1,31,'image','2026-10-24T00:00:00Z',2.5)")
    conn.commit(); conn.close()
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    result = R.collect_report(root, as_of="2026-10-24", db=db)
    assert result["metrics"]["actual_usd"]["value"] == 2.5
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    missing = root / "missing.sqlite"
    assert R.collect_report(root, as_of="2026-10-24", db=missing)["metrics"]["actual_usd"]["value"] is None
    assert not missing.exists()

def test_null_ledger_cost_does_not_silently_sum_to_zero(report_env):
    R, root = report_env
    db = root / "fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE usage_events(project_id INTEGER, kind TEXT, at TEXT, usd REAL)")
        conn.execute("INSERT INTO usage_events VALUES(31,'image','2026-10-24T00:00:00Z',NULL)")
    result = R.collect_report(root, as_of="2026-10-24", db=db)
    assert result["metrics"]["actual_usd"]["value"] is None

def test_output_only_docs_reports_and_structured_prior_delta(report_env):
    R, root = report_env
    report = R.collect_report(root, as_of="2026-10-17")
    md, sidecar = R.write_report(report, root)
    assert md.parent == root / "docs/reports" and sidecar.suffix == ".json"
    newer = R.collect_report(root, as_of="2026-10-24", baseline=sidecar)
    assert newer["metrics"]["code_pct"]["delta"] == 0
    altered = json.loads(sidecar.read_text()); altered["scope"] = "wrong"
    sidecar.write_text(json.dumps(altered))
    incompatible = R.collect_report(root, as_of="2026-10-24", baseline=sidecar)
    assert incompatible["metrics"]["code_pct"]["delta"] is None
    assert any("kỳ trước" in w for w in incompatible["warnings"])

def test_output_rejects_traversal_date_and_symlink(report_env, tmp_path):
    R, root = report_env
    report = R.collect_report(root, as_of="2026-10-24")
    report["as_of"] = "../../escape"
    with pytest.raises(ValueError): R.write_report(report, root)
    report["as_of"] = "2026-10-24"
    outside = tmp_path / "outside"; outside.mkdir()
    try: (root / "docs/reports").symlink_to(outside, target_is_directory=True)
    except OSError: pytest.skip("Máy không cấp quyền tạo symlink")
    with pytest.raises(ValueError): R.write_report(report, root)
    assert not list(outside.iterdir())
