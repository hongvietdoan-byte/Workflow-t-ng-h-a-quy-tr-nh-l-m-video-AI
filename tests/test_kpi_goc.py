import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools import kpi_goc


def _snapshot(bundle: Path, project_id: int, evidence=None):
    folder = bundle / f"#{project_id}"
    folder.mkdir(parents=True)
    db_path = folder / "manifest.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE jobs (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, state TEXT NOT NULL);
            CREATE TABLE usage_events (
                id INTEGER PRIMARY KEY, job_id INTEGER, project_id INTEGER, kind TEXT,
                provider TEXT, model TEXT, tier TEXT, quantity REAL, unit TEXT, at TEXT
            );
            CREATE TABLE scenes (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE qc_results (id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, criterion TEXT, score REAL);
            CREATE TABLE diag_events (id INTEGER PRIMARY KEY, project_id INTEGER, severity TEXT);
            """
        )
        conn.execute("INSERT INTO jobs VALUES (1, ?, 'succeeded')", (project_id,))
        conn.execute("INSERT INTO jobs VALUES (2, ?, 'failed')", (project_id,))
        conn.execute("INSERT INTO usage_events VALUES (1, 1, ?, 'video', 'clipai', 'm', 'draft', 4, 'second', '2026-10-01')", (project_id,))
        conn.execute("INSERT INTO usage_events VALUES (2, 2, ?, 'image', 'mock-image', 'm', 'draft', 1, 'image', '2026-10-01')", (project_id,))
        conn.execute("INSERT INTO scenes VALUES (1, ?, '{}')", (project_id,))
        conn.execute("INSERT INTO qc_results VALUES (1, 1, 'freeze', 0.2)")
        conn.execute("INSERT INTO diag_events VALUES (1, ?, 'warn')", (project_id,))
    entry = {"project_id": project_id, "label": f"#{project_id}", "db": f"#{project_id}/manifest.sqlite"}
    if evidence is not None:
        evidence_path = folder / "kpi_evidence.json"
        evidence_path.write_text(json.dumps({"schema_version": 1, "project_id": project_id, **evidence}), encoding="utf-8")
        entry["evidence"] = f"#{project_id}/kpi_evidence.json"
    return entry, db_path


def _evidence(project_id, *, extra_paid=0, samples=None, checks=None, scenes=None, clips=None):
    return {
        "mt1": {"coverage_complete": True, "system_error_paid_count": extra_paid},
        "mt2": {"coverage_complete": True, "samples": samples or []},
        "mt3": {"coverage_complete": True, "checks": checks or []},
        "mt4": {"coverage_complete": True, "scenes": scenes or []},
        "mt5": {"coverage_complete": True, "clips": clips or []},
    }


def _bundle(tmp_path):
    entries = {}
    dbs = {}
    for project_id in (24, 27, 31, 33):
        checks = [{"free_text_used": True, "unsafe_pass": project_id != 33 and i < 2, "source_ref": "golden/replay"} for i in range(10)]
        evidence = _evidence(
            project_id,
            extra_paid=1 if project_id == 31 else 0,
            samples=[{"kind": "draft", "estimate_usd": 120, "actual_usd": 100, "source_ref": "usage_events"}],
            checks=checks,
            scenes=[
                {"multi_shot": True, "shared_map": project_id == 33, "position_checks": [{"consistent": project_id == 33}]},
                {"multi_shot": True, "shared_map": True, "position_checks": [{"consistent": True}]},
            ],
            clips=[
                {"kind": "freeze", "bad": True, "detected_before_user": project_id == 33, "source_ref": "qc_results/review_log"},
                {"kind": "wrong_first_frame", "bad": True, "detected_before_user": True, "source_ref": "qc_results/review_log"},
                {"kind": "freeze", "bad": False, "detected_before_user": False, "source_ref": "qc_results/review_log"},
                {"kind": "wrong_first_frame", "bad": False, "detected_before_user": False, "source_ref": "qc_results/review_log"},
            ],
        )
        entry, db_path = _snapshot(tmp_path, project_id, evidence)
        entries[project_id] = entry
        dbs[project_id] = db_path
    manifest = {
        "schema_version": 1,
        "snapshot_kind": "isolated_copy",
        "baseline": [entries[31]],
        "current": [entries[33]],
        "mt3_baseline": [entries[24], entries[27], entries[31]],
    }
    (tmp_path / "kpi_goc_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path, dbs


def test_fixture_bundle_compares_five_kpis_and_normalizes_mt3(tmp_path):
    bundle, _ = _bundle(tmp_path)

    result = kpi_goc.measure_bundle(bundle)

    assert result["schema_version"] == 1
    assert result["metrics"]["MT1"]["current"]["system_error_paid_count"] == 0
    assert result["metrics"]["MT1"]["current"]["paid_usage_events"] == 1
    assert result["metrics"]["MT2"]["baseline"]["max_abs_error_percent"] == 20
    assert result["metrics"]["MT2"]["current"]["target_met"] is False
    assert result["metrics"]["MT3"]["baseline"]["project_ids"] == [24, 27, 31]
    assert result["metrics"]["MT3"]["baseline"]["leak_rate"] == 0.2
    assert result["metrics"]["MT3"]["current"]["leak_rate"] == 0
    assert result["metrics"]["MT3"]["reduction_percent"] == 100
    assert result["metrics"]["MT4"]["current"]["shared_map_coverage"] == 1
    assert result["metrics"]["MT5"]["current"]["by_kind"]["freeze"]["recall"] == 1
    assert result["metrics"]["MT5"]["current"]["freeze_recall"] == 1
    assert result["metrics"]["MT5"]["current"]["wrong_first_frame_recall"] == 1


def test_missing_curated_evidence_is_reported_as_not_measurable(tmp_path):
    entry31, _ = _snapshot(tmp_path, 31)
    entry33, _ = _snapshot(tmp_path, 33)
    entry24, _ = _snapshot(tmp_path, 24)
    entry27, _ = _snapshot(tmp_path, 27)
    manifest = {
        "schema_version": 1,
        "snapshot_kind": "isolated_copy",
        "baseline": [entry31],
        "current": [entry33],
        "mt3_baseline": [entry24, entry27, entry31],
    }
    (tmp_path / "kpi_goc_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = kpi_goc.measure_bundle(tmp_path)

    assert all(metric["status"] == "NOT_MEASURABLE" for metric in result["metrics"].values())
    assert "evidence" in result["metrics"]["MT1"]["reason"].lower()
    assert 24 in result["metrics"]["MT3"]["baseline"]["missing_evidence_project_ids"]


def test_database_snapshot_is_opened_read_only(tmp_path):
    bundle, dbs = _bundle(tmp_path)
    db_path = dbs[31]
    before = hashlib.sha256(db_path.read_bytes()).hexdigest()
    before_mtime = db_path.stat().st_mtime_ns

    facts = kpi_goc.read_db_facts(db_path, 31)

    assert facts["paid_usage_events"] == 1
    assert facts["job_count"] == 2
    assert facts["scene_count"] == 1
    assert hashlib.sha256(db_path.read_bytes()).hexdigest() == before
    assert db_path.stat().st_mtime_ns == before_mtime
    with pytest.raises(sqlite3.OperationalError):
        conn = kpi_goc.open_db_readonly(db_path)
        try:
            conn.execute("CREATE TABLE must_not_exist(x)")
        finally:
            conn.close()


def test_database_under_live_data_directory_is_rejected(tmp_path):
    fake_live = tmp_path / "AI-Video-Pipeline" / "data" / "fake.sqlite"
    fake_live.parent.mkdir(parents=True)
    with sqlite3.connect(fake_live) as conn:
        conn.execute("CREATE TABLE jobs(id INTEGER)")

    with pytest.raises(kpi_goc.KpiInputError):
        kpi_goc.open_db_readonly(fake_live)


def test_manifest_rejects_path_traversal_and_non_copy_root(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    outside = tmp_path / "outside.sqlite"
    with sqlite3.connect(outside) as conn:
        conn.execute("CREATE TABLE jobs(id INTEGER)")
    manifest = {
        "schema_version": 1,
        "snapshot_kind": "isolated_copy",
        "baseline": [{"project_id": 31, "label": "#31", "db": "../outside.sqlite"}],
        "current": [{"project_id": 33, "label": "#33", "db": "../outside.sqlite"}],
        "mt3_baseline": [],
    }
    (bundle / "kpi_goc_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(kpi_goc.KpiInputError):
        kpi_goc.measure_bundle(bundle)


def test_mt3_requires_the_declared_baseline_cohort(tmp_path):
    entries = {}
    for project_id in (31, 33):
        entry, _ = _snapshot(tmp_path, project_id, _evidence(project_id, checks=[]))
        entries[project_id] = entry
    manifest = {
        "schema_version": 1,
        "snapshot_kind": "isolated_copy",
        "baseline": [entries[31]],
        "current": [entries[33]],
        "mt3_baseline": [entries[31]],
    }
    (tmp_path / "kpi_goc_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = kpi_goc.measure_bundle(tmp_path)

    assert result["metrics"]["MT3"]["status"] == "NOT_MEASURABLE"
    assert result["metrics"]["MT3"]["baseline"]["project_ids"] == [31]
    assert result["metrics"]["MT3"]["baseline"]["required_project_ids"] == [24, 27, 31]
    assert "24" in result["metrics"]["MT3"]["baseline"]["reason"]


def test_mt4_counts_unlabeled_shared_map_as_unmeasured_not_success(tmp_path):
    evidence = _evidence(
        33,
        scenes=[
            {"multi_shot": True, "shared_map": True, "position_checks": [{"consistent": True}]},
            {"multi_shot": True, "position_checks": [{"consistent": True}]},
        ],
    )
    entry, _ = _snapshot(tmp_path, 33, evidence)
    baseline_entry, _ = _snapshot(tmp_path, 31, _evidence(31, scenes=[
        {"multi_shot": True, "shared_map": True, "position_checks": [{"consistent": True}]},
    ]))
    manifest = {
        "schema_version": 1,
        "snapshot_kind": "isolated_copy",
        "baseline": [baseline_entry],
        "current": [entry],
        "mt3_baseline": [],
    }
    (tmp_path / "kpi_goc_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = kpi_goc.measure_bundle(tmp_path)["metrics"]["MT4"]["current"]

    assert result["multi_shot_scenes"] == 2
    assert result["shared_map_coverage"] == 0.5
    assert result["coverage_complete"] is False
    assert result["status"] == "PARTIAL"


def test_cli_requires_an_explicit_snapshot_flag():
    assert kpi_goc.main([]) == 2


def test_cli_writes_only_to_a_path_outside_the_snapshot(tmp_path, capsys):
    bundle, _ = _bundle(tmp_path / "bundle")
    outside_report = tmp_path / "result.md"

    assert kpi_goc.main(["--ban-sao", str(bundle), "--out", str(outside_report)]) == 0
    assert outside_report.is_file()
    assert "MT3 dùng tỷ lệ lỗi lọt cổng" in outside_report.read_text(encoding="utf-8")
    capsys.readouterr()

    assert kpi_goc.main(["--ban-sao", str(bundle), "--out", str(bundle / "inside.md")]) == 2
    assert not (bundle / "inside.md").exists()
