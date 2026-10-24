"""Snapshot giả; không import DB/runtime/provider của pipeline."""
import os
import socket
import sqlite3
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
import pytest

with mock.patch.object(os, "environ", {}):
    from tools import kiem_cong as kg

NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
AT = "2026-10-25T10:00:00+00:00"

@pytest.fixture(autouse=True)
def isolated(tmp_path):
    with mock.patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "PYTHONUTF8": "1"}), \
         mock.patch.object(socket.socket, "connect", side_effect=AssertionError("no network")):
        yield

@pytest.fixture
def snapshot(tmp_path):
    path = tmp_path / "snapshot.sqlite"
    c = sqlite3.connect(path)
    c.executescript('''CREATE TABLE scenes(id INTEGER PRIMARY KEY,project_id INTEGER,data TEXT);
    CREATE TABLE jobs(id INTEGER PRIMARY KEY,project_id INTEGER,scene_id INTEGER,type TEXT,state TEXT,created_at TEXT,updated_at TEXT,sent_package TEXT);
    CREATE TABLE diag_events(id INTEGER PRIMARY KEY,project_id INTEGER,scene_id INTEGER,job_id INTEGER,at TEXT,last_at TEXT,stage TEXT,severity TEXT,code TEXT,count INTEGER);
    CREATE TABLE usage_events(id INTEGER PRIMARY KEY,project_id INTEGER,job_id INTEGER,kind TEXT,quantity REAL,at TEXT);
    CREATE TABLE qc_results(id INTEGER PRIMARY KEY,job_id INTEGER,criterion TEXT,score REAL,threshold_at_time REAL,auto_decision TEXT);''')
    pkg = {"v": 1, "at": AT, "prompt": "fixture", "refs": [], "params": {}, "provider": "fake", "model": "fake"}
    override = {"schema_version": 1, "project_id": 1, "scene_id": 1, "updated_at": AT, "revision": 1,
                "base_scene_revision": "a"*64, "base_package_hash": "b"*64, "edits": [], "reason": "fixture", "updated_by": "fixture"}
    c.execute("INSERT INTO scenes VALUES(1,1,?)", (json.dumps({"package_overrides": override}),))
    c.execute("INSERT INTO jobs VALUES(1,1,1,'video_gen','succeeded',?,?,?)", (AT,AT,json.dumps(pkg)))
    c.execute("INSERT INTO diag_events VALUES(1,1,1,1,?,?,'ui_step','info','ui_step:fixture',1)", (AT,AT))
    c.execute("INSERT INTO usage_events VALUES(1,1,1,'video',1,?)", (AT,))
    c.execute("INSERT INTO qc_results VALUES(1,1,'fixture',1,.5,'approve')")
    c.commit(); c.close()
    return path

def catalog(tmp_path):
    p = tmp_path / "catalog.json"
    p.write_text(json.dumps({"rows": [{"id":"M1", "title":"fixture", "criteria":"manual", "flags":[], "evidence":list(kg.EVIDENCE), "location":"fixture", "one_project":True,"offline":"fixture","risk":"fixture","manual":True}]}))
    return p

def test_complete_facts_not_full_gate(snapshot,tmp_path):
    report = kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)
    assert set(report["evidence"]) == set(kg.EVIDENCE)
    assert all(f["status"] == kg.PASS for f in report["evidence"].values())
    assert report["rows"][0]["status"] == kg.MISSING
    assert report["rows"][0]["checks"] == kg.PASS

@pytest.mark.parametrize("key,sql", [("jobs","DELETE FROM jobs"),("sent_package","UPDATE jobs SET sent_package='{'"),
    ("diag_events","UPDATE diag_events SET severity='error'"),("ui_step","UPDATE diag_events SET stage='other'"),
    ("ledger","UPDATE usage_events SET quantity=-1"),("qc","UPDATE qc_results SET score=0"),
    ("overrides","UPDATE scenes SET data='{'")])
def test_each_bad_evidence_never_pass(snapshot,tmp_path,key,sql):
    c=sqlite3.connect(snapshot); c.execute(sql); c.commit(); c.close()
    r=kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)
    assert r["evidence"][key]["status"] != kg.PASS
    assert r["rows"][0]["status"] != kg.PASS

def test_since_needs_own_time_and_real_timezone(snapshot,tmp_path):
    r=kg.run_report(snapshot,1,catalog(tmp_path),since="2026-10-25T16:00:00+07:00",now=NOW)
    assert r["evidence"]["jobs"]["count"] == 1
    assert r["evidence"]["qc"]["status"] == kg.MISSING
    with pytest.raises(ValueError): kg.run_report(snapshot,1,catalog(tmp_path),since="2026-10-25",now=NOW)

def test_scope_schema_readonly_and_hash(snapshot,tmp_path):
    before=hashlib.sha256(snapshot.read_bytes()).digest()
    r=kg.run_report(snapshot,2,catalog(tmp_path),now=NOW)
    assert all(f["status"] != kg.PASS for f in r["evidence"].values())
    assert hashlib.sha256(snapshot.read_bytes()).digest() == before
    c=kg.open_db_readonly(snapshot)
    with pytest.raises(sqlite3.OperationalError): c.execute("DELETE FROM jobs")
    c.close()

def test_future_badtime_nan_and_missing_schema(snapshot,tmp_path):
    c=sqlite3.connect(snapshot); c.execute("UPDATE jobs SET created_at='2099-01-01T00:00:00Z'"); c.execute("DROP TABLE usage_events"); c.commit(); c.close()
    r=kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)
    assert r["evidence"]["jobs"]["status"] != kg.PASS
    assert r["evidence"]["ledger"]["status"] == kg.MISSING

def test_cli_requires_db_and_output_cannot_touch_input(snapshot,tmp_path):
    with pytest.raises(SystemExit): kg.main(["--project","1"])
    assert kg.main(["--db",str(snapshot),"--project","1","--catalog",str(catalog(tmp_path)),"--md",str(snapshot)]) == 2


@pytest.mark.parametrize("sql,key", [
    ("UPDATE jobs SET sent_package=replace(sent_package, '\"v\": 1', '\"v\": NaN')", "sent_package"),
    ("UPDATE usage_events SET at='not-a-time'", "ledger"),
    ("UPDATE diag_events SET last_at='2099-01-01T00:00:00Z'", "ui_step"),
    ("UPDATE jobs SET sent_package=replace(sent_package, '\"at\"', '\"no_at\"')", "sent_package"),
])
def test_invalid_own_timestamp_and_json(snapshot,tmp_path,sql,key):
    c=sqlite3.connect(snapshot); c.execute(sql); c.commit(); c.close()
    report=kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)
    assert report["evidence"][key]["status"] != kg.PASS


def test_since_never_borrows_job_time(snapshot,tmp_path):
    c=sqlite3.connect(snapshot)
    c.execute("UPDATE jobs SET sent_package=replace(sent_package, ?, ?)", (AT,"2020-01-01T00:00:00Z"))
    c.execute("UPDATE usage_events SET at='2020-01-01T00:00:00Z'")
    c.commit(); c.close()
    r=kg.run_report(snapshot,1,catalog(tmp_path),since="2026-10-25T09:00:00Z",now=NOW)
    assert r["evidence"]["jobs"]["count"] == 1
    assert r["evidence"]["sent_package"]["count"] == 0
    assert r["evidence"]["ledger"]["count"] == 0


def test_report_has_no_database_content(snapshot,tmp_path):
    report=kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)
    serialized=json.dumps(report)+kg.render_markdown(report)
    assert "fixture" not in serialized
    assert "prompt" not in serialized


def test_cli_rejects_existing_output_before_read(snapshot,tmp_path):
    out=tmp_path / "existing.md"; out.write_text("fixture")
    with mock.patch.object(kg,"run_report",side_effect=AssertionError("must validate first")):
        assert kg.main(["--db",str(snapshot),"--project","1","--md",str(out)]) == 2
    assert out.read_text() == "fixture"


def test_rejects_data_output_and_snapshot_symlink(snapshot,tmp_path):
    out=tmp_path / "data" / "report.md"
    assert kg.main(["--db",str(snapshot),"--project","1","--md",str(out)]) == 2
    link=tmp_path / "linked.sqlite"
    try:
        link.symlink_to(snapshot)
    except OSError:
        pytest.skip("Máy không cho tạo symlink")
    with pytest.raises(ValueError):
        kg.open_db_readonly(link)


def test_qc_evidence_adapter_joins_and_scopes(snapshot,tmp_path):
    c=sqlite3.connect(snapshot)
    c.executescript("DROP TABLE qc_results; CREATE TABLE qc_runs(qc_run_id TEXT,project_id INTEGER,finished_at TEXT,status TEXT,error TEXT); CREATE TABLE qc_findings(qc_run_id TEXT,created_at TEXT,status TEXT,severity TEXT,qc_code TEXT);")
    c.execute("INSERT INTO qc_runs VALUES('a',1,?,'ok',NULL)",(AT,))
    c.execute("INSERT INTO qc_findings VALUES('a',?,'open','INFO','fixture')",(AT,))
    c.execute("INSERT INTO qc_runs VALUES('b',2,?,'error',NULL)",(AT,))
    c.commit(); c.close()
    r=kg.run_report(snapshot,1,catalog(tmp_path),since="2026-10-25T09:00:00Z",now=NOW)
    assert r["evidence"]["qc"]["status"] == kg.PASS
    assert r["evidence"]["qc"]["count"] == 2


def test_run_uses_consistent_read_transaction(snapshot,tmp_path):
    queries=[]
    original=kg.open_db_readonly
    def traced(path):
        conn=original(path); conn.set_trace_callback(queries.append); return conn
    with mock.patch.object(kg,"open_db_readonly",side_effect=traced):
        kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)
    assert queries[0] == "BEGIN"
    assert not any(q.split()[0] in ("INSERT","UPDATE","DELETE","CREATE","ALTER","DROP") for q in queries)


def test_package_invalid_ref_schema_cannot_pass(snapshot,tmp_path):
    c=sqlite3.connect(snapshot)
    pkg={"v":1,"at":AT,"prompt":"fixture","refs":[{}],"params":{},"provider":"fake","model":"fake"}
    c.execute("UPDATE jobs SET sent_package=?",(json.dumps(pkg),)); c.commit(); c.close()
    r=kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)
    assert r["evidence"]["sent_package"]["status"] == kg.FAIL


@pytest.mark.parametrize("status,severity,expected", [
    ("open","BLOCK",kg.FAIL),("open","REVIEW",kg.FAIL),
    ("open","high",kg.FAIL),("invented","INFO",kg.FAIL),
    ("resolved","INFO",kg.MISSING),("overridden","REVIEW",kg.MISSING),
    ("false_positive","BLOCK",kg.MISSING),
])
def test_findings_use_real_contract(snapshot,tmp_path,status,severity,expected):
    c=sqlite3.connect(snapshot)
    c.executescript("DROP TABLE qc_results; CREATE TABLE qc_runs(qc_run_id TEXT,project_id INTEGER,finished_at TEXT,status TEXT,error TEXT); CREATE TABLE qc_findings(qc_run_id TEXT,created_at TEXT,status TEXT,severity TEXT,qc_code TEXT);")
    c.execute("INSERT INTO qc_runs VALUES('a',1,?,'ok',NULL)",(AT,))
    c.execute("INSERT INTO qc_findings VALUES('a',?,?,?,'fixture')",(AT,status,severity))
    c.commit(); c.close()
    assert kg.run_report(snapshot,1,catalog(tmp_path),now=NOW)["evidence"]["qc"]["status"] == expected


@pytest.mark.parametrize("duplicate",[False,True])
def test_catalog_requires_nonempty_unique_rows(snapshot,tmp_path,duplicate):
    path=catalog(tmp_path)
    content=json.loads(path.read_text())
    content["rows"] = content["rows"]*2 if duplicate else []
    path.write_text(json.dumps(content))
    with pytest.raises(ValueError):
        kg.run_report(snapshot,1,path,now=NOW)


@pytest.mark.parametrize("parent",["missing","missing_project_column"])
@pytest.mark.parametrize("job_id,expected",[(None,kg.PASS),(2,kg.MISSING)])
def test_parent_scope_schema_and_null_foreign_key(tmp_path,parent,job_id,expected):
    path=tmp_path / "snapshot.sqlite"
    c=sqlite3.connect(path)
    c.execute("CREATE TABLE usage_events(project_id INTEGER,job_id INTEGER,kind TEXT,quantity REAL,at TEXT)")
    if parent == "missing_project_column":
        c.execute("CREATE TABLE jobs(id INTEGER)")
        c.execute("INSERT INTO jobs VALUES(2)")
    c.execute("INSERT INTO usage_events VALUES(1,?,'llm',1,?)",(job_id,AT))
    c.commit(); c.close()
    r=kg.run_report(path,1,catalog(tmp_path),now=NOW)
    assert r["evidence"]["ledger"]["status"] == expected
