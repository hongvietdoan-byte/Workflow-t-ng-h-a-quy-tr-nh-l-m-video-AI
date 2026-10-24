"""CX23-A2F-ALIAS: bộ đề xuất bí danh Kho chạy offline, chỉ fixture giả."""

import os
import json
import sqlite3
from contextlib import nullcontext
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _fake_environment():
    # Cô lập toàn bộ env của test module; test cần cờ chỉ dùng dict giả riêng.
    with mock.patch.object(os, "environ", {"PYTHONUTF8": "1"}):
        yield


def _asset(asset_id, name, aliases="", *, game="FF", kind="location", profile=None):
    return {
        "id": asset_id,
        "name": name,
        "aliases": aliases,
        "game": game,
        "kind": kind,
        "profile": profile or {},
    }


def test_asset_adapter_schema_exposes_existing_alias_field():
    # Chỉ dùng CSDL in-memory và thay toàn bộ os.environ trước import/gọi code.
    with mock.patch.object(os, "environ", {}):
        from core import assets
        from core.db import connect

        conn = connect(":memory:")
        try:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(assets)")}
            assert "aliases" in columns
            asset_id = conn.execute(
                "INSERT INTO assets (game, kind, name, aliases) VALUES ('FF','location',?,?)",
                ("Tháp Đồng Hồ", "Clock Tower"),
            ).lastrowid
            conn.commit()

            row = assets.get(conn, asset_id)
            assert row["aliases"] == "Clock Tower"
        finally:
            conn.close()


def test_scan_proposes_exact_catalog_match_and_does_not_guess(monkeypatch):
    from tools import kho_place_alias
    from core import assets

    rows = [
        _asset(1, "Tháp Đồng Hồ"),
        _asset(2, "Clock Tower", "Tháp Đồng Hồ"),
        _asset(3, "Biệt thự"),
        _asset(4, "Village", ""),  # Đã có tên tiếng Anh, không thuộc danh sách thiếu.
    ]
    monkeypatch.setattr(assets, "list_assets", lambda *_a, **_kw: rows)
    before = [dict(row) for row in rows]

    result = kho_place_alias.scan_locations(object())

    assert [item["id"] for item in result] == [1, 3]
    assert result[0]["suggested_alias"] == "Clock Tower"
    assert result[0]["source"] == "mục Kho FF trùng tên"
    assert result[1]["suggested_alias"] is None
    assert result[1]["source"] == "không có nguồn tiếng Anh khớp chính xác"
    assert rows == before


def test_scan_with_conflicting_catalog_names_leaves_suggestion_blank(monkeypatch):
    from tools import kho_place_alias
    from core import assets

    rows = [
        _asset(1, "Tháp Đồng Hồ"),
        _asset(2, "Clock Tower", "Tháp Đồng Hồ"),
        _asset(3, "Tower Plaza", "Tháp Đồng Hồ"),
    ]
    monkeypatch.setattr(assets, "list_assets", lambda *_a, **_kw: rows)

    result = kho_place_alias.scan_locations(object())

    assert len(result) == 1
    assert result[0]["suggested_alias"] is None
    assert result[0]["source"] == "nhiều nguồn tiếng Anh khớp; cần duyệt thủ công"


def test_open_database_is_read_only_and_query_only(tmp_path):
    from tools import kho_place_alias

    path = tmp_path / "fixture.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE fixture (value TEXT)")
        conn.execute("INSERT INTO fixture VALUES ('fake')")

    conn = kho_place_alias.open_readonly(path)
    try:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        assert conn.execute("SELECT value FROM fixture").fetchone()[0] == "fake"
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("UPDATE fixture SET value='changed'")
    finally:
        conn.close()


def test_open_readonly_does_not_create_a_missing_database(tmp_path):
    from tools import kho_place_alias

    path = tmp_path / "must-not-be-created.sqlite"
    with pytest.raises(FileNotFoundError):
        kho_place_alias.open_readonly(path)
    assert not path.exists()


def test_write_uses_backup_before_single_atomic_update(tmp_path, monkeypatch):
    from tools import kho_place_alias

    path = tmp_path / "fixture.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY, game TEXT, kind TEXT, name TEXT, aliases TEXT)")
        conn.execute("INSERT INTO assets VALUES (1, 'FF', 'location', 'Tháp Đồng Hồ', '')")
        conn.execute("INSERT INTO assets VALUES (2, 'FF', 'location', 'Clock Tower', 'Tháp Đồng Hồ')")

    monkeypatch.setattr(kho_place_alias, "_manifest_path", lambda _path: path)
    backup_state = []

    def backup(db):
        with sqlite3.connect(db) as conn:
            backup_state.append(conn.execute("SELECT aliases FROM assets WHERE id=1").fetchone()[0])

    written = kho_place_alias.write_proposals(
        path,
        [{"id": 1, "name": "Tháp Đồng Hồ", "aliases": "", "suggested_alias": "Clock Tower"}],
        backup=backup,
    )

    with sqlite3.connect(path) as conn:
        alias = conn.execute("SELECT aliases FROM assets WHERE id=1").fetchone()[0]
    assert backup_state == [""]
    assert written == 1
    assert alias == "Clock Tower"


def test_backup_failure_prevents_any_database_write(tmp_path, monkeypatch):
    from tools import kho_place_alias

    path = tmp_path / "fixture.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY, game TEXT, kind TEXT, name TEXT, aliases TEXT)")
        conn.execute("INSERT INTO assets VALUES (1, 'FF', 'location', 'Tháp Đồng Hồ', '')")
        conn.execute("INSERT INTO assets VALUES (2, 'FF', 'location', 'Clock Tower', 'Tháp Đồng Hồ')")
    monkeypatch.setattr(kho_place_alias, "_manifest_path", lambda _path: path)

    def backup(_db):
        raise RuntimeError("backup fixture failed")

    with pytest.raises(RuntimeError):
        kho_place_alias.write_proposals(
            path,
            [{"id": 1, "name": "Tháp Đồng Hồ", "aliases": "", "suggested_alias": "Clock Tower"}],
            backup=backup,
        )
    with sqlite3.connect(path) as conn:
        alias = conn.execute("SELECT aliases FROM assets WHERE id=1").fetchone()[0]
    assert alias == ""


def test_write_rejects_an_unverified_alias_and_preserves_database(tmp_path, monkeypatch):
    from tools import kho_place_alias

    path = tmp_path / "fixture.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY, game TEXT, kind TEXT, name TEXT, aliases TEXT)")
        conn.execute("INSERT INTO assets VALUES (1, 'FF', 'location', 'Tháp Đồng Hồ', '')")
    monkeypatch.setattr(kho_place_alias, "_manifest_path", lambda _path: path)

    with pytest.raises(RuntimeError):
        kho_place_alias.write_proposals(
            path,
            [{"id": 1, "name": "Tháp Đồng Hồ", "aliases": "", "suggested_alias": "Invented Name"}],
            backup=lambda _db: None,
        )
    with sqlite3.connect(path) as conn:
        alias = conn.execute("SELECT aliases FROM assets WHERE id=1").fetchone()[0]
    assert alias == ""


def test_conflict_rolls_back_all_alias_updates(tmp_path, monkeypatch):
    from tools import kho_place_alias

    path = tmp_path / "fixture.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY, game TEXT, kind TEXT, name TEXT, aliases TEXT)")
        conn.execute("INSERT INTO assets VALUES (1, 'FF', 'location', 'Tháp Đồng Hồ', '')")
    monkeypatch.setattr(kho_place_alias, "_manifest_path", lambda _path: path)

    with pytest.raises(RuntimeError):
        kho_place_alias.write_proposals(
            path,
            [
            {"id": 1, "name": "Tháp Đồng Hồ", "aliases": "", "suggested_alias": "Clock Tower"},
            {"id": 999, "name": "Missing Place", "aliases": "", "suggested_alias": "Missing Place"},
            ],
            backup=lambda _db: None,
        )
    with sqlite3.connect(path) as conn:
        alias = conn.execute("SELECT aliases FROM assets WHERE id=1").fetchone()[0]
    assert alias == ""


def test_backup_uses_don_rac_sao_luu_command(tmp_path, monkeypatch):
    from tools import kho_place_alias

    db = tmp_path / "fixture.sqlite"
    db.touch()
    monkeypatch.setattr(kho_place_alias, "_manifest_path", lambda _path: db)
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr(kho_place_alias.subprocess, "run", run)
    fake_env = {
        "PATH": "C:\\fake-bin",
        "SYSTEMROOT": "C:\\fake-windows",
        "TEMP": "C:\\fake-temp",
        "PYTHONUTF8": "1",
        "API_SECRET_SENTINEL": "fake-secret-value",
    }
    with mock.patch.object(os, "environ", fake_env):
        kho_place_alias.backup_database(db)

    command = calls[0][0]
    assert Path(command[1]).name == "don_rac.py"
    assert "sao-luu" in command and "--lam-that" in command
    child_env = calls[0][1]["env"]
    assert child_env.get("PATH") == "C:\\fake-bin"
    assert child_env.get("SYSTEMROOT") == "C:\\fake-windows"
    assert child_env.get("TEMP") == "C:\\fake-temp"
    assert child_env.get("PYTHONUTF8") == "1"
    assert child_env.get("API_SECRET_SENTINEL") is None


def test_write_mode_requires_explicit_per_id_approval(tmp_path, capsys):
    from tools import kho_place_alias

    path = tmp_path / "fixture.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY, game TEXT, kind TEXT, name TEXT, aliases TEXT)")
        conn.execute("INSERT INTO assets VALUES (1, 'FF', 'location', 'Tháp Đồng Hồ', '')")
        conn.execute("INSERT INTO assets VALUES (2, 'FF', 'location', 'Clock Tower', 'Tháp Đồng Hồ')")
    before = path.read_bytes()

    with pytest.raises(SystemExit) as error:
        kho_place_alias.main(["--db", str(path), "--lam-that"])

    assert error.value.code == 2
    assert path.read_bytes() == before


def test_cli_writes_only_individually_approved_suggestions(tmp_path, monkeypatch, capsys):
    from tools import kho_place_alias

    path = tmp_path / "fake-manifest.sqlite"
    path.touch()
    captured = []
    rows = [
        {"id": 1, "name": "Tháp Đồng Hồ", "aliases": "", "suggested_alias": "Clock Tower", "source": "catalog fixture"},
        {"id": 2, "name": "Nhà Thờ", "aliases": "", "suggested_alias": "Old Church", "source": "catalog fixture"},
    ]
    monkeypatch.setattr(kho_place_alias, "open_readonly", lambda _path: nullcontext(object()))
    monkeypatch.setattr(kho_place_alias, "scan_locations", lambda _conn: rows)
    monkeypatch.setattr(kho_place_alias, "write_proposals", lambda _path, selected: captured.extend(selected) or len(selected))

    assert kho_place_alias.main(["--db", str(path), "--lam-that", "--duyet", "2=Old Church"]) == 0
    output = capsys.readouterr().out

    assert "CHẾ ĐỘ GHI" in output
    assert "ID và bí danh đã duyệt: 2=Old Church" in output
    assert "Đã ghi 1 bí danh đã duyệt" in output
    assert [row["id"] for row in captured] == [2]


def test_cli_rejects_approved_alias_if_current_preview_changed(tmp_path, monkeypatch, capsys):
    from tools import kho_place_alias

    path = tmp_path / "fake-manifest.sqlite"
    path.touch()
    captured = []
    rows = [
        {"id": 2, "name": "Nhà Thờ", "aliases": "", "suggested_alias": "Old Church", "source": "catalog fixture"}
    ]
    monkeypatch.setattr(kho_place_alias, "open_readonly", lambda _path: nullcontext(object()))

    def scan(_conn):
        return rows

    monkeypatch.setattr(kho_place_alias, "scan_locations", scan)
    monkeypatch.setattr(
        kho_place_alias,
        "write_proposals",
        lambda _path, selected: captured.extend(selected) or len(selected),
    )

    assert kho_place_alias.main(["--db", str(path)]) == 0  # preview: 2=Old Church
    rows[0] = {**rows[0], "suggested_alias": "Church of the Village"}

    assert kho_place_alias.main(
        ["--db", str(path), "--lam-that", "--duyet", "2=Old Church"]
    ) == 2
    capsys.readouterr()
    assert captured == []


def test_cli_defaults_to_print_only_on_a_fake_manifest(tmp_path, capsys):
    fake_env = {}
    with mock.patch.object(os, "environ", fake_env):
        from core.db import connect
        from tools import kho_place_alias

        path = tmp_path / "fixture.sqlite"
        conn = connect(str(path))
        conn.execute(
            "INSERT INTO assets (game, kind, name, aliases) VALUES ('FF','location',?,?)",
            ("Tháp Đồng Hồ", ""),
        )
        conn.execute(
            "INSERT INTO assets (game, kind, name, aliases) VALUES ('FF','location',?,?)",
            ("Clock Tower", "Tháp Đồng Hồ"),
        )
        conn.commit()
        conn.close()
        before = path.read_bytes()

        assert kho_place_alias.main(["--db", str(path)]) == 0
        printed = capsys.readouterr().out

    assert "Tháp Đồng Hồ" in printed
    assert "Clock Tower" in printed
    assert "CHẾ ĐỘ CHỈ ĐỌC" in printed
    assert path.read_bytes() == before


def test_a2f_uses_adapter_alias_in_setting_and_plate_sentence():
    fake_env = {"FEATURE_BYD_FIELDS": "1", "FEATURE_BYD_FIELDS_A2F": "1"}
    with mock.patch.object(os, "environ", fake_env):
        from core import assets, runner
        from core.db import connect
        from core.pipeline import Pipeline

        pipeline = Pipeline(connect(":memory:"))
        conn = pipeline.conn
        project_id = pipeline.create_project("a2f-alias-fixture")
        conn.execute("UPDATE projects SET game='FF' WHERE id=?", (project_id,))
        asset_id = conn.execute(
            "INSERT INTO assets (game, kind, name, aliases) VALUES ('FF','location',?,?)",
            ("Tháp Đồng Hồ", "Clock Tower"),
        ).lastrowid
        conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (project_id, asset_id))
        conn.commit()
        place = assets.get(conn, asset_id)
        scene = {"byd": {"byd_v": 2, "noi_chon": {"kho_id": asset_id}}}
        try:
            with mock.patch.object(runner, "indoor_spot", return_value=None):
                setting = runner._place_part(conn, project_id, scene, place, True, [])
            plate = runner.plate_place_name(conn, project_id, scene, place, "Tháp Đồng Hồ")
            assert "Setting: Clock Tower" in setting
            assert "Background: exactly the 3D render picture" in setting
            assert plate == "Clock Tower"
        finally:
            conn.close()


def test_area_registry_includes_tool_and_test_without_version_bump():
    repo_root = Path(__file__).resolve().parents[1]
    registry = json.loads((repo_root / "devsys" / "areas.json").read_text(encoding="utf-8"))
    assets_area = next(area for area in registry["areas"] if area["id"] == "assets")

    assert registry["version"] == 92
    assert "tools/kho_place_alias.py" in assets_area["assets"]
    assert "tests/test_kho_place_alias.py" in assets_area["tests"]
