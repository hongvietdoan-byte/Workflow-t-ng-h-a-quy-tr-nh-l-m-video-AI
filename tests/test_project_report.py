"""CX22-REPORT: fixtures giả, không đọc nhật ký/CSDL thật."""
import hashlib
import json
import os
import sqlite3
from unittest.mock import patch
from pathlib import Path
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
        from datetime import datetime
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None): return cls(2026, 10, 24, 14, 0, tzinfo=R.VN)
        with patch.object(R, "datetime", Clock):
            yield R, root

def _log(folder, name, rows):
    folder.mkdir(exist_ok=True)
    (folder / name).write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

def _row(mid="a", tokens=10, **extra):
    return {"sessionId": "fake-session", "timestamp": "2026-10-23T18:00:00Z", "isSidechain": False,
            "message": {"id": mid, "model": "claude-sonnet-4", "usage": {"input_tokens": tokens, "output_tokens": 2, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}, "content": "SECRET_CANARY_EMAIL@example.test/private/path"}, **extra}

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
    assert report["metrics"]["build_tokens"]["value"] is None
    assert report["metrics"]["video_operation_tokens"]["value"] is None
    assert "chưa tách được xây công cụ" in md

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
    altered = json.loads(sidecar.read_text(encoding="utf-8")); altered["scope"] = "wrong"
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


def test_real_schema_usage_is_not_claimed_as_actual_usd(report_env):
    R, root = report_env
    db = root / "real_shape_fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE usage_events(project_id INTEGER, kind TEXT, provider TEXT, model TEXT, tier TEXT, quantity REAL, unit TEXT, at TEXT)")
        conn.execute("INSERT INTO usage_events VALUES(31,'image','mock','fake','',2,'image','2026-10-24T00:00:00Z')")
    report = R.collect_report(root, as_of="2026-10-24", db=db)
    assert report["metrics"]["actual_usd"]["value"] is None
    assert report["metrics"]["ledger_rows"]["value"] == 1
    assert "không có USD" in report["metrics"]["actual_usd"]["reason"]


def test_holds_use_only_active_llm_ttl_not_queued_or_allocated_reserves(report_env):
    R, root = report_env
    from datetime import datetime
    now = datetime(2026, 10, 24, 14, 0, tzinfo=R.VN)
    db = root / "holds_fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript("CREATE TABLE llm_holds(at TEXT, usd REAL); CREATE TABLE project_reserves(state TEXT,usd REAL); CREATE TABLE jobs(state TEXT,usd REAL);")
        conn.executemany("INSERT INTO llm_holds VALUES(?,?)", [("2026-10-24 06:45:00", 2), ("2026-10-24 06:29:59", 100), ("2026-10-24 07:01:00", 500)])
        conn.execute("INSERT INTO project_reserves VALUES('active',900)")
        conn.execute("INSERT INTO jobs VALUES('queued',700)")
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return now
    with patch.object(R, "datetime", Clock):
        result = R.collect_report(root, as_of="2026-10-24", db=db)
    assert result["metrics"]["held_usd"]["value"] == 2


def test_unknown_role_cache_and_model_do_not_export_freeform_or_assume_zero(report_env):
    R, root = report_env
    folder = root / "fake_sessions"
    row = _row()
    del row["isSidechain"]
    del row["message"]["usage"]["cache_read_input_tokens"]
    row["message"]["model"] = "SECRET_CANARY"
    _log(folder, "a.jsonl", [row])
    result = R.collect_report(root, as_of="2026-10-24", session_dir=folder)
    assert result["metrics"]["tokens"]["value"] is None
    assert result["token_groups"][0]["role"] == "UNKNOWN"
    assert result["token_groups"][0]["cache_read_input_tokens"] is None
    assert "SECRET_CANARY" not in json.dumps(result)


def test_nested_agent_logs_are_deduped_without_reading_sibling_projects(report_env):
    R, root = report_env
    folder = root / "fake_sessions"
    nested = folder / "subagents"
    folder.mkdir(); nested.mkdir()
    row = _row(); del row["isSidechain"]; row["agentId"] = "fake-agent"
    _log(nested, "agent.jsonl", [row])
    sibling = root / "fake_sessions_other_project"
    _log(sibling, "private.jsonl", [_row("other", 999)])
    result = R.collect_report(root, as_of="2026-10-24", session_dir=folder)
    assert result["token_groups"][0]["role"] == "agent"
    assert result["metrics"]["tokens"]["value"] == 12 and result["coverage"]["files"] == 1


def test_estimates_do_not_treat_auto_limit_as_budget_and_bad_total_unknown(report_env):
    R, root = report_env
    db = root / "estimates_fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE app_settings(key TEXT,value TEXT)")
        conn.execute("INSERT INTO app_settings VALUES('simple_auto_limit:31',?)", (json.dumps({"limit_usd": 999}),))
        conn.execute("INSERT INTO app_settings VALUES('project_budget:31',?)", (json.dumps({"total": 2.5, "locked": True}),))
    report = R.collect_report(root, as_of="2026-10-24", db=db)
    assert report["metrics"]["estimated_usd"]["value"] == 2.5
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO app_settings VALUES(?,?)", ("project_budget:32", json.dumps({"total": None})))
    assert R.collect_report(root, as_of="2026-10-24", db=db)["metrics"]["estimated_usd"]["value"] is None


def test_cli_standalone_without_pythonpath_writes_only_scoped_reports(report_env, tmp_path):
    R, root = report_env
    import subprocess
    import sys
    before = {p.relative_to(root) for p in root.rglob("*") if p.is_file()}
    env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "TEMP": str(tmp_path), "TMP": str(tmp_path), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, str(Path(R.__file__)), "--root", str(root), "--as-of", "2026-10-24", "--week"], env=env, cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0
    new = {p.relative_to(root) for p in root.rglob("*") if p.is_file()} - before
    assert new and all(str(p).replace("\\", "/").startswith("docs/reports/") for p in new)
    report = json.loads((root / "docs/reports/BAO_CAO_DU_AN_2026-10-24.json").read_text(encoding="utf-8"))
    assert report["metrics"]["code_pct"]["value"] == 100


def test_legacy_decision_phase_unknown_and_mail_reply_uses_actual_event_kind(report_env):
    R, root = report_env
    (root / "data").mkdir()
    (root / "data/decisions.json").write_text(json.dumps({"items": [{"id": "legacy-1", "status": "done", "text": "SECRET_CANARY"}, {"id": "pending-1", "phase": "PROPOSED", "text": "SECRET_CANARY"}]}))
    (root / "devsys/errors.json").write_text(json.dumps({"items": [{"id": "G1", "stage": "L2", "category": "image", "status": "OPEN", "severity": "high", "note": "SECRET_CANARY"}]}))
    mail = root / "hop_thu/su_kien"; mail.mkdir(parents=True)
    (mail / "ask.json").write_text(json.dumps({"kind": "hoi", "text": "SECRET_CANARY"}))
    (mail / "answer.json").write_text(json.dumps({"kind": "tra_loi", "reply_to": "ask.json", "text": "SECRET_CANARY"}))
    report = R.collect_report(root, as_of="2026-10-24")
    assert report["metrics"]["ep_decisions"]["value"] == 1
    assert report["metrics"]["decision_phase_unknown"]["value"] == 1
    assert report["metrics"]["mail_questions"]["value"] == 0
    assert report["ep_pending"] == [{"id": "pending-1", "phase": "PROPOSED"}]
    assert report["open_error_items"][0]["id"] == "G1"
    assert "SECRET_CANARY" not in json.dumps(report) and "SECRET_CANARY" not in R.render_markdown(report)


def test_first_pass_uses_events_not_reset_retry_counter(report_env):
    R, root = report_env
    db = root / "quality_fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript("CREATE TABLE jobs(id INTEGER, project_id INTEGER, scene_id INTEGER, type TEXT,retry_count INTEGER); CREATE TABLE job_events(id INTEGER,job_id INTEGER,from_state TEXT,to_state TEXT,at TEXT);")
        conn.executemany("INSERT INTO jobs VALUES(?,31,?,'image_gen',0)", [(1,1), (2,2), (3,2)])
        events = [(1,1,None,"queued"), (2,1,"queued","running"), (3,1,"review","approved"), (4,2,None,"queued"), (5,2,"queued","running"), (6,2,"review","rejected"), (7,3,None,"queued"), (8,3,"queued","running"), (9,3,"review","approved")]
        conn.executemany("INSERT INTO job_events VALUES(?,?,?,?,?)", [(eid,jid,frm,to,f"2026-10-24T00:00:{eid:02d}Z") for eid,jid,frm,to in events])
    report = R.collect_report(root, as_of="2026-10-24", db=db)
    assert report["metrics"]["first_pass_rate"]["value"] == 50
    image = report["quality_history"][0]
    assert image["reviewed"] == 2 and image["first_pass"] == 1 and image["regenerated"] == 1
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO jobs VALUES(4,31,3,'image_gen',0)")
    report = R.collect_report(root, as_of="2026-10-24", db=db)
    assert report["metrics"]["first_pass_rate"]["value"] is None
    assert report["quality_history"][0]["unknown"] == 1


def test_rejected_only_is_in_first_pass_denominator_but_unjudged_queued_is_not(report_env):
    R, root = report_env
    db = root / "judgments_fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript("CREATE TABLE jobs(id INTEGER, project_id INTEGER, scene_id INTEGER, type TEXT); CREATE TABLE job_events(id INTEGER,job_id INTEGER,from_state TEXT,to_state TEXT,at TEXT);")
        conn.executemany("INSERT INTO jobs VALUES(?,31,?,'image_gen')", [(1,1),(2,2),(3,3)])
        events = [(1,1,None,"queued"),(2,1,"queued","running"),(3,1,"review","approved"),(4,2,None,"queued"),(5,2,"queued","running"),(6,2,"review","rejected"),(7,3,None,"queued")]
        conn.executemany("INSERT INTO job_events VALUES(?,?,?,?,?)", [(eid,jid,frm,to,f"2026-10-24T00:00:{eid:02d}Z") for eid,jid,frm,to in events])
    report = R.collect_report(root, as_of="2026-10-24", db=db)
    assert report["metrics"]["first_pass_rate"]["value"] == 50
    assert report["quality_history"][0]["reviewed"] == 2
    assert report["quality_history"][0]["unknown"] == 0


def test_automatically_reads_prior_week_sidecar_and_source_scope_must_match(report_env):
    R, root = report_env
    R.write_report(R.collect_report(root, as_of="2026-10-17"), root)
    report = R.collect_report(root, as_of="2026-10-24")
    assert report["metrics"]["code_pct"]["delta"] == 0
    changed_source = R.collect_report(root, as_of="2026-10-24", session_dir=root / "another-scope")
    assert changed_source["metrics"]["code_pct"]["delta"] is None
    assert any("kỳ trước" in w for w in changed_source["warnings"])


def test_optional_pdf_mocked_local_tools_whitelist_network_off_and_confinement(report_env):
    R, root = report_env
    from types import SimpleNamespace
    report = R.collect_report(root, as_of="2026-10-24")
    markdown, _ = R.write_report(report, root)
    commands = []
    def fake_run(args, *, env, cwd, **kwargs):
        commands.append(args)
        assert set(env) <= {"PATH", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "TEMP", "TMP", "PYTHONUTF8"}
        assert Path(cwd).is_relative_to(root / "docs/reports")
        assert env["HOME"] == str(cwd) and env["USERPROFILE"] == str(cwd)
        if len(commands) == 1:
            target = next(x.split("=", 1)[1] for x in args if x.startswith("--output="))
            Path(target).write_text("<html><head></head><body>fixture</body></html>", encoding="utf-8")
        else:
            assert "--no-pdf-header-footer" in args and "--disable-background-networking" in args and "--host-resolver-rules=MAP * ~NOTFOUND" in args
            assert "Content-Security-Policy" in (Path(cwd) / "report.html").read_text(encoding="utf-8")
            target = next(x.split("=", 1)[1] for x in args if x.startswith("--print-to-pdf="))
            Path(target).write_bytes(b"%PDF-1.7 fixture-only")
        return SimpleNamespace(returncode=0)
    def fake_browser(args, env, cwd):
        return fake_run(args, env=env, cwd=cwd).returncode == 0
    with patch.object(R, "_pdf_tools", return_value=("fake-pandoc", "fake-browser")), patch.object(R.subprocess, "run", side_effect=fake_run), patch.object(R, "_browser_process", side_effect=fake_browser):
        pdf, warning = R.render_pdf(markdown, root)
    assert not warning and pdf.parent == root / "docs/reports" and pdf.read_bytes().startswith(b"%PDF-")
    assert len(commands) == 2
    assert not list((root / "docs/reports").glob(".report-pdf-*"))
    with pytest.raises(ValueError): R.render_pdf(root / "outside.md", root)
    with patch.object(R, "_pdf_tools", return_value=(None, None)), patch.object(R.subprocess, "run") as run:
        pdf, warning = R.render_pdf(markdown, root)
        assert pdf is None and "không có đủ" in warning and not run.called


def test_renderer_timeout_stops_only_owned_process_tree(report_env, tmp_path):
    R, root = report_env
    import subprocess
    from unittest.mock import Mock
    process = Mock()
    process.pid = 123456789
    process.poll.return_value = None
    process.communicate.side_effect = [subprocess.TimeoutExpired(["fake-browser"], 60), (b"", b"")]
    fake_env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "SYSTEMROOT": "C:/Windows"}
    with patch.object(R.subprocess, "Popen", return_value=process) as opened, patch.object(R.subprocess, "run") as killed, patch.object(R.os, "killpg", create=True):
        assert R._browser_process(["fake-browser", "--headless=new"], fake_env, tmp_path) is False
    assert opened.call_args.kwargs["env"] == fake_env
    if os.name == "nt":
        assert killed.call_args.args[0][1:] == ["/PID", "123456789", "/T", "/F"]
        assert killed.call_args.kwargs["env"] == fake_env
    assert process.kill.called and process.communicate.call_count == 2


@pytest.mark.parametrize("extension", ["md", "json"])
def test_output_replaces_hardlink_instead_of_truncating_external_inode(report_env, tmp_path, extension):
    R, root = report_env
    directory = root / "docs/reports"; directory.mkdir()
    outside = tmp_path / ("outside-" + extension)
    outside.write_bytes(b"fake-external-must-remain")
    target = directory / ("BAO_CAO_DU_AN_2026-10-24." + extension)
    try: os.link(outside, target)
    except OSError: pytest.skip("Filesystem không hỗ trợ hardlink fixture")
    R.write_report(R.collect_report(root, as_of="2026-10-24"), root)
    assert outside.read_bytes() == b"fake-external-must-remain"
    assert target.read_bytes() != outside.read_bytes()
    assert not list(directory.glob(".report-write-*"))

def test_readonly_snapshot_reads_committed_wal_without_changing_database_or_wal(report_env):
    R, root = report_env
    db = root / "wal-fake.sqlite"
    writer = sqlite3.connect(db)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        writer.execute("CREATE TABLE usage_events(project_id INTEGER,at TEXT,usd REAL)")
        writer.execute("INSERT INTO usage_events VALUES(31,'2026-10-24T00:00:00Z',4.5)")
        writer.commit()
        wal = Path(str(db) + "-wal")
        before = (hashlib.sha256(db.read_bytes()).hexdigest(), hashlib.sha256(wal.read_bytes()).hexdigest())
        result = R.collect_report(root, as_of="2026-10-24", db=db)
        after = (hashlib.sha256(db.read_bytes()).hexdigest(), hashlib.sha256(wal.read_bytes()).hexdigest())
        assert result["metrics"]["actual_usd"]["value"] == 4.5
        assert before == after
    finally:
        writer.close()


def test_date_cutoff_filters_ledger_and_output_delivery_counts(report_env):
    R, root = report_env
    db = root / "cutoff-fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript("CREATE TABLE usage_events(project_id INTEGER,at TEXT,usd REAL); CREATE TABLE outputs(kind TEXT,created_at TEXT); CREATE TABLE deliveries(project_id INTEGER,delivered_at TEXT);")
        for stamp, pid, usd in [("2026-10-24T16:59:59Z",31,2.5),("2026-10-24T17:00:00Z",32,100)]:
            conn.execute("INSERT INTO usage_events VALUES(?,?,?)", (pid,stamp,usd))
            conn.execute("INSERT INTO outputs VALUES('final',?)", (stamp,))
            conn.execute("INSERT INTO deliveries VALUES(?,?)", (pid,stamp))
    result = R.collect_report(root, as_of="2026-10-24", db=db)
    assert result["metrics"]["ledger_rows"]["value"] == 1
    assert result["metrics"]["final_outputs"]["value"] == 1
    assert result["metrics"]["delivered_projects"]["value"] == 1
    assert result["metrics"]["actual_usd"]["value"] == 2.5


def test_missing_dates_are_unknown_and_historical_budget_is_not_replayed(report_env):
    R, root = report_env
    db = root / "missing-date-fake.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript("CREATE TABLE usage_events(project_id INTEGER,usd REAL); CREATE TABLE outputs(kind TEXT); CREATE TABLE deliveries(project_id INTEGER); CREATE TABLE app_settings(key TEXT,value TEXT);")
        conn.execute("INSERT INTO usage_events VALUES(31,2.5)")
        conn.execute("INSERT INTO outputs VALUES('final')")
        conn.execute("INSERT INTO deliveries VALUES(31)")
        conn.execute("INSERT INTO app_settings VALUES('project_budget:31',?)", (json.dumps({"total": 9, "approved_at": "2026-10-24T01:00:00Z"}),))
    result = R.collect_report(root, as_of="2026-10-17", db=db)
    assert all(result["metrics"][k]["value"] is None for k in ("ledger_rows", "final_outputs", "delivered_projects", "estimated_usd"))


@pytest.mark.parametrize("broken", ["all-conflict", "missing-session"])
def test_activity_is_unknown_when_session_coverage_is_incomplete(report_env, broken):
    R, root = report_env
    folder = root / "fake_sessions"
    row = _row()
    if broken == "all-conflict":
        other = _row(); other["message"]["model"] = "claude-opus-4"
        rows = [row, other]
    else:
        del row["sessionId"]
        rows = [row]
    _log(folder, "data.jsonl", rows)
    result = R.collect_report(root, as_of="2026-10-24", session_dir=folder)
    assert result["metrics"]["sessions"]["value"] is None
    assert result["metrics"]["days"]["value"] is None
