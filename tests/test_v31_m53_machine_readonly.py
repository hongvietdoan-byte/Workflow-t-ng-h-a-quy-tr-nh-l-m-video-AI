"""M5.3 --may-chinh: chỉ dùng CSDL và tệp fixture giả, không đụng dữ liệu máy chính."""
import hashlib
import importlib.util
import os
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
_IMPORT_ENV = {"PATH": "fixture-path", "SYSTEMROOT": "fixture-system", "TEMP": "fixture-temp", "PYTHONUTF8": "1"}
with patch.object(os, "environ", _IMPORT_ENV):
    _spec = importlib.util.spec_from_file_location("pilot_a_m53_fixture", ROOT / "tools" / "pilot_a.py")
    P = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(P)


def _make_fake_machine(root: Path) -> Path:
    data = root / "data"
    projects = data / "projects" / "fixture"
    projects.mkdir(parents=True)
    (projects / "result.bin").write_bytes(b"fixture-only-result")
    (data / "427.png").write_bytes(b"fixture-asset-427")
    (data / "367.png").write_bytes(b"fixture-asset-367")
    (root / "dashboard.env").write_text("FEATURE_EXAMPLE=1\nAPI_KEY=DO_NOT_READ_OR_REPORT\n", encoding="utf-8")

    db_path = data / "manifest.sqlite"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE scenes(id INTEGER PRIMARY KEY, project_id INTEGER, idx INTEGER, data TEXT);
        CREATE TABLE story_scenes(id INTEGER PRIMARY KEY, project_id INTEGER, idx INTEGER, data TEXT);
        CREATE TABLE jobs(id INTEGER PRIMARY KEY, project_id INTEGER, scene_id INTEGER, type TEXT, state TEXT,
                          result_path TEXT, sent_package TEXT, sent_refs TEXT);
        CREATE TABLE asset_images(id INTEGER PRIMARY KEY, asset_id INTEGER, path TEXT, sha256 TEXT);
        CREATE TABLE change_events(id INTEGER PRIMARY KEY, at TEXT, project_id INTEGER, scene_id INTEGER, state TEXT,
                                  keys TEXT, before TEXT, after TEXT);
        CREATE TABLE job_events(id INTEGER PRIMARY KEY, job_id INTEGER, from_state TEXT, to_state TEXT, actor TEXT, note TEXT, at TEXT);
        CREATE TABLE diag_events(id INTEGER PRIMARY KEY, project_id INTEGER, job_id INTEGER, code TEXT, count INTEGER, message TEXT);
        CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    scene_rows = [(n, 31, n, json.dumps({"text": f"FAKE_SCENE_{n}"})) for n in (4, 6, 8, 27, 28, 29, 30, 33, 35, 36)]
    scene_rows += [(100 + n, 33, n, json.dumps({"text": f"FAKE_SCENE_33_{n}"})) for n in (2, 6)]
    conn.executemany("INSERT INTO scenes VALUES (?,?,?,?)", scene_rows)
    conn.executemany("INSERT INTO story_scenes VALUES (?,?,?,?)", [
        (1, 31, 4, "FAKE_STORY_4"), (2, 31, 6, "FAKE_STORY_6"), (3, 31, 8, "FAKE_STORY_8"), (4, 33, 2, "FAKE_STORY_33")])
    job_rows = [
        (1162, 33, 102, "video_gen", "approved", "data/projects/fixture/result.bin", "FAKE_PRIVATE_PROMPT", "FAKE_PRIVATE_REF"),
        (1163, 33, 106, "video_gen", "approved", "data/projects/fixture/result.bin", "FAKE_PRIVATE_PROMPT_2", "FAKE_PRIVATE_REF_2"),
        (1058, 31, 27, "image_gen", "approved", "data/projects/fixture/result.bin", "FAKE_PRIVATE_PROMPT_3", "FAKE_PRIVATE_REF_3"),
    ]
    conn.executemany("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)", job_rows)
    conn.executemany("INSERT INTO asset_images VALUES (?,?,?,?)", [
        (427, 427, "data/427.png", "fixture-sha-427"), (367, 367, "data/367.png", "fixture-sha-367")])
    conn.execute("INSERT INTO change_events VALUES (1,'2026-10-17T10:00:00',31,4,'pending','[\"noi_chon\"]','FAKE_BEFORE','FAKE_AFTER')")
    conn.execute("INSERT INTO job_events VALUES (1,1162,'queued','done','fixture','FAKE_NOTE','2026-10-17T10:00:00')")
    conn.execute("INSERT INTO diag_events VALUES (1,31,1058,'FAKE_DIAG',1,'FAKE_DIAG_MESSAGE')")
    conn.execute("INSERT INTO app_settings VALUES ('fixture_setting','not-a-secret')")
    conn.execute("PRAGMA user_version=7")
    conn.commit()
    conn.close()
    return db_path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_fingerprints(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): _sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def test_open_readonly_uses_uri_mode_ro_and_preserves_fake_db(tmp_path):
    db_path = _make_fake_machine(tmp_path)
    before = _sha(db_path)

    conn = P.open_db_readonly(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 3
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        conn.execute("PRAGMA query_only=OFF")
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO jobs VALUES (999,31,1,'video_gen','queued',NULL,NULL,NULL)")
    finally:
        conn.close()

    assert _sha(db_path) == before


def test_machine_capture_covers_seven_cases_without_disclosing_fixture_content(tmp_path):
    db_path = _make_fake_machine(tmp_path)
    before = _sha(db_path)
    data_before = _tree_fingerprints(tmp_path / "data")

    report = P.capture_may_chinh(tmp_path)

    assert [row["id"] for row in report["cases"]] == [
        "payload_sent_package", "qc_result_files", "kho_reference_images", "scene_continuity",
        "change_lineage", "job_recovery", "machine_provenance"]
    assert report["database"]["sha256_before"] == before
    assert report["database"]["sha256_after"] == before
    assert report["database"]["unchanged"] is True
    assert _tree_fingerprints(tmp_path / "data") == data_before
    assert all(row["status"] in {"available", "partial", "missing"} for row in report["cases"])
    rendered = json.dumps(report, ensure_ascii=False)
    for private_value in ("FAKE_PRIVATE_PROMPT", "FAKE_PRIVATE_REF", "FAKE_SCENE_", "FAKE_BEFORE", "FAKE_AFTER",
                          "FAKE_DIAG_MESSAGE", "DO_NOT_READ_OR_REPORT", str(tmp_path)):
        assert private_value not in rendered


def test_machine_capture_never_opens_dashboard_env(tmp_path, monkeypatch):
    _make_fake_machine(tmp_path)
    original_open = Path.open

    def reject_dashboard_env(path, *args, **kwargs):
        if path.name.lower() == "dashboard.env":
            pytest.fail("snapshot must not read dashboard.env")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_dashboard_env)
    report = P.capture_may_chinh(tmp_path)

    provenance = next(row for row in report["cases"] if row["id"] == "machine_provenance")
    assert "feature_flags" not in provenance


def test_machine_capture_detects_wal_sidecar_change(tmp_path, monkeypatch):
    db_path = _make_fake_machine(tmp_path)
    wal_path = Path(str(db_path) + "-wal")
    original = P._database_fingerprints
    calls = 0

    def mutate_fake_wal_after_snapshot(path):
        nonlocal calls
        calls += 1
        fingerprints = original(path)
        if calls == 2:
            wal_path.write_bytes(b"fixture-wal-mutated-after-read")
            fingerprints = original(path)
        return fingerprints

    monkeypatch.setattr(P, "_database_fingerprints", mutate_fake_wal_after_snapshot)
    report = P.capture_may_chinh(tmp_path)

    assert report["database"]["wal_sha256_before"] != report["database"]["wal_sha256_after"]
    assert report["database"]["unchanged"] is False


def test_machine_capture_accounts_for_a_real_fake_wal_database(tmp_path):
    db_path = _make_fake_machine(tmp_path)
    writer = sqlite3.connect(db_path)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
        writer.execute("INSERT INTO app_settings VALUES ('wal_fixture', 'fixture-only')")
        writer.commit()
        wal_path = Path(str(db_path) + "-wal")
        assert wal_path.exists()

        report = P.capture_may_chinh(tmp_path)
    finally:
        writer.close()

    database = report["database"]
    assert database["journal_mode_before"].lower() == "wal"
    assert database["journal_mode_after"].lower() == "wal"
    assert database["wal_sha256_before"] == database["wal_sha256_after"]
    assert database["wal_sha256_before"] is not None
    assert database["unchanged"] is True


def test_machine_capture_does_not_follow_paths_outside_root(tmp_path):
    db_path = _make_fake_machine(tmp_path)
    outside = tmp_path.parent / "outside-secret.bin"
    outside.write_bytes(b"must-not-be-opened")
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE jobs SET result_path=? WHERE id=1162", ("../outside-secret.bin",))
    conn.commit()
    conn.close()

    report = P.capture_may_chinh(tmp_path)
    qc_case = next(row for row in report["cases"] if row["id"] == "qc_result_files")
    assert qc_case["outside_root_rejected"] >= 1
    rendered = json.dumps(report, ensure_ascii=False)
    assert "outside-secret" not in rendered


def test_pytest_child_environment_is_explicitly_allowlisted():
    fake_env = {"PATH": "safe-path", "SYSTEMROOT": "safe-system", "TEMP": "safe-temp",
                "API_KEY": "DO_NOT_FORWARD", "CLAUDE_API_KEY": "DO_NOT_FORWARD_EITHER", "PYTHONPATH": "secret-path"}
    with patch.object(P.os, "environ", fake_env):
        env = P._pytest_child_env(str(tmp_path := Path("safe-out")))

    assert env["PATH"] == "safe-path"
    assert env["SYSTEMROOT"] == "safe-system"
    assert env["PYTHONUTF8"] == "1"
    assert "API_KEY" not in env and "CLAUDE_API_KEY" not in env
    assert "secret-path" not in env["PYTHONPATH"]
    assert str(tmp_path) in env["PILOT_A_GUARD_OUT"]


def test_report_paths_inside_data_are_rejected(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    with pytest.raises(ValueError, match="ngoài dữ liệu"):
        P.validate_output_paths([str(data_root / "pilot.md")], [data_root])
    P.validate_output_paths([str(tmp_path / "pilot.md")], [data_root])


def test_changed_database_hash_turns_machine_run_red():
    report = {"verdict": {"ket_qua": "DAT_OFFLINE", "tieu_chi": {}}}
    P.add_may_chinh_integrity(report, {"database": {"unchanged": False}})
    assert report["verdict"]["ket_qua"] == "ROT"
    assert report["verdict"]["tieu_chi"]["c6"]["dat"] is False


def test_cli_without_machine_flag_never_opens_machine_snapshot(tmp_path, monkeypatch, capsys):
    report = {
        "python": "3.x", "pytest_rc": 0, "tail": ["fixture tests passed"],
        "cases": [], "khong_co_test": [], "may_chinh": [],
        "verdict": {"ket_qua": "DAT_OFFLINE", "ghi_chu": "fixture-only", "tieu_chi": {}},
    }
    monkeypatch.setattr(P, "run", lambda *_args, **_kwargs: report.copy())
    monkeypatch.setattr(P, "capture_may_chinh", lambda *_: pytest.fail("snapshot must be opt-in"))

    assert P.main(["--out-dir", str(tmp_path / "out")]) == 0
    assert "DAT_OFFLINE" in capsys.readouterr().out


def test_cli_machine_flag_uses_only_supplied_fake_root(tmp_path, monkeypatch, capsys):
    _make_fake_machine(tmp_path)
    report = {
        "python": "3.x", "pytest_rc": 0, "tail": ["fixture tests passed"],
        "cases": [], "khong_co_test": [], "may_chinh": [],
        "verdict": {"ket_qua": "DAT_OFFLINE", "ghi_chu": "fixture-only", "tieu_chi": {}},
    }
    monkeypatch.setattr(P, "run", lambda *_args, **_kwargs: report.copy())

    assert P.main(["--may-chinh", "--main-root", str(tmp_path), "--no-xdist",
                   "--out-dir", str(tmp_path / "output")]) == 0
    output = capsys.readouterr().out
    assert "SHA CSDL trước/sau" in output
    assert "DO_NOT_READ_OR_REPORT" not in output
    assert str(tmp_path) not in output


def test_cli_refuses_report_inside_fake_machine_data_before_running(tmp_path, monkeypatch):
    _make_fake_machine(tmp_path)
    monkeypatch.setattr(P, "run", lambda *_args, **_kwargs: pytest.fail("must validate output first"))

    with pytest.raises(ValueError, match="ngoài dữ liệu"):
        P.main(["--may-chinh", "--main-root", str(tmp_path), "--json",
                str(tmp_path / "data" / "report.json")])
