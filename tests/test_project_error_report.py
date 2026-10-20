import importlib
import os
import sqlite3
from unittest.mock import patch

import pytest


@pytest.fixture
def report_module():
    with patch.object(os, "environ", {}):
        yield importlib.import_module("tools.project_error_report")


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "sample.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE jobs(id, project_id, shot_id, state, error, updated_at);
        CREATE TABLE diag_events(id, project_id, job_id, stage, severity, code, message, at, last_at, count);
        CREATE TABLE job_events(id, job_id, from_state, to_state, note, at);
        CREATE TABLE usage_events(id, project_id, job_id, cost_usd);
        INSERT INTO jobs VALUES(1,33,7,'failed','provider_failure','t3'),(2,33,8,'succeeded',NULL,'t4'),(3,99,9,'failed','other','t4');
        INSERT INTO diag_events VALUES(1,33,1,'video','error','repeat','do not export raw message','t1','t2',2),(2,33,1,'video','error','repeat','another','t2','t3',1),(3,99,3,'video','error','foreign','other','t1','t4',1);
        INSERT INTO job_events VALUES(1,2,'running','succeeded',NULL,'t1'),(2,2,'succeeded','succeeded','InvalidTransition','t4');
        INSERT INTO usage_events VALUES(1,33,1,0.25),(2,33,1,0.5),(3,99,3,9);
        """)
    return path


def test_group_schema_cost_readonly(report_module, sample):
    before = sample.read_bytes()
    result = report_module.build_report(sample, 33)
    rows = {row["group_key"]: row for row in result["errors"]}
    diag = rows["diag:repeat"]
    assert (diag["count"], diag["first_seen"], diag["last_seen"]) == (3, "t1", "t3")
    assert diag["job_ids"] == [1] and diag["shot_ids"] == [7]
    assert rows["job:provider_failure"]["failed_job_cost_usd"] == 0.75
    assert rows["transition:succeeded->succeeded"]["count"] == 1
    assert all(row["status"] == "OPEN" and row["real_run_evidence"] == [] for row in rows.values())
    assert "raw message" not in report_module.render_markdown(result)
    assert sample.read_bytes() == before


def test_missing_table_clear(report_module, tmp_path):
    path = tmp_path / "empty.sqlite"
    sqlite3.connect(path).close()
    with pytest.raises(ValueError, match="diag_events.*job_events.*jobs"):
        report_module.build_report(path, 33)


def test_optional_usage_unknown(report_module, sample):
    with sqlite3.connect(sample) as db:
        db.execute("DROP TABLE usage_events")
    result = report_module.build_report(sample, 33)
    assert "usage_events" in result["warnings"][0]
    assert all(row["failed_job_cost_usd"] is None for row in result["errors"])


def test_missing_file_not_created(report_module, tmp_path):
    path = tmp_path / "absent.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        report_module.build_report(path, 33)
    assert not path.exists()


def test_native_schema_failure_note_and_unknown_cost(report_module, tmp_path):
    path = tmp_path / "native.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE jobs(id, project_id, scene_id, type, state, created_at, updated_at);
        CREATE TABLE diag_events(id, at, last_at, stage, severity, code, message, project_id, scene_id, job_id, count);
        CREATE TABLE job_events(id, job_id, from_state, to_state, actor, note, at);
        CREATE TABLE usage_events(id, job_id, project_id, kind, provider, model, tier, quantity, unit, at);
        INSERT INTO jobs VALUES(1,33,3,'video_gen','retryable','t1','t3');
        INSERT INTO job_events VALUES(1,1,'running','failed','runner','timeout: detail omitted','t2');
        INSERT INTO usage_events VALUES(1,1,33,'video','fake','fake','draft',5,'second','t2');
        """)
    result = report_module.build_report(path, 33)
    assert result["errors"][0]["group_key"] == "job:timeout"
    assert result["errors"][0]["failed_job_cost_usd"] is None
    assert result["errors"][0]["shot_ids"] == [3]
    assert "UNKNOWN" in result["warnings"][0]


def test_sources_are_provenance_only(report_module, sample):
    result = report_module.build_report(sample, 33)
    row = next(r for r in result["errors"] if r["category"] == "transition")
    assert any(s["id"] == "P33-A1" and s["line"] > 0 for s in row["suggested_error_codes"])
    assert row["alias"] == [] and "PROPOSAL" in row["id"]
    assert report_module.main(["--db", str(sample), "--project", "33", "--json"]) == 0


def test_other_invalid_transition_and_usd_units(report_module, sample):
    with sqlite3.connect(sample) as db:
        db.execute("INSERT INTO job_events VALUES(3,1,'queued','approved',NULL,'t5')")
        db.execute("ALTER TABLE usage_events ADD COLUMN unit")
        db.execute("ALTER TABLE usage_events ADD COLUMN quantity")
        db.execute("UPDATE usage_events SET cost_usd=NULL,unit='USD',quantity=0.125 WHERE job_id=1")
    rows = {r["group_key"]: r for r in report_module.build_report(sample, 33)["errors"]}
    assert rows["transition:queued->approved"]["count"] == 1
    assert rows["job:provider_failure"]["failed_job_cost_usd"] == 0.25

def test_all_failed_attempts_count_and_dates(report_module, sample):
    with sqlite3.connect(sample) as db:
        db.executemany("INSERT INTO job_events VALUES(?,?,?,?,?,?)", [
            (3,1,'running','failed','timeout: first','t1'),
            (4,1,'running','failed','other: middle','t2'),
            (5,1,'running','failed','timeout: last','t5')])
    rows = {r['group_key']: r for r in report_module.build_report(sample, 33)['errors']}
    assert rows['job:timeout']['count'] == 2
    assert (rows['job:timeout']['first_seen'], rows['job:timeout']['last_seen']) == ('t1','t5')
    assert rows['job:other']['count'] == 1
    assert rows['job:timeout']['failed_job_cost_usd'] == 0.75
    assert [e['record_id'] for e in rows['job:timeout']['evidence']] == [3,5]


def test_nonfinite_cost_stays_unknown_json_finite(report_module, sample):
    import json
    with sqlite3.connect(sample) as db:
        db.execute('UPDATE usage_events SET cost_usd=? WHERE id=1', (float('inf'),))
    result = report_module.build_report(sample, 33)
    assert all(r['failed_job_cost_usd'] is None for r in result['errors'] if 1 in r['job_ids'])
    json.dumps(result, allow_nan=False)
