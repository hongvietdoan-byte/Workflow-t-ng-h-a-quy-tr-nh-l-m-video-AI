"""CLI ảnh ghép N5: chỉ dùng SQLite/đường dẫn tạm và Blender giả."""

import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _fake_environment():
    with mock.patch.object(os, "environ", {"PYTHONUTF8": "1"}):
        yield


@pytest.mark.parametrize("crew_flag", [False, True])
def test_cli_uses_n5_crew_preview_and_prints_per_shot_pick(tmp_path, monkeypatch, capsys, crew_flag):
    from core import camera_plan, db, features, stage_auto, stage_desk
    from tools import stage_auto as cli

    database = tmp_path / "fixture.sqlite"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE fixture (value TEXT)")
        conn.execute("INSERT INTO fixture VALUES ('fake')")
    real_connect = sqlite3.connect
    opened = []

    def track_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", track_connect)
    monkeypatch.setattr(db, "connect", lambda *_a, **_k: pytest.fail("beats must not use the migrating connection"))
    monkeypatch.setattr(features, "REQUIRES", {"stage_auto": []})
    monkeypatch.setattr(features, "on", lambda _name: True)
    segment = {
        "id": "1@fixture", "scene": "1", "stage": "fixture",
        "shots": [{"idx": 2}], "spots": {"door": [2]}, "main_spot": "door",
    }
    read_only_seen = []

    def segments(conn, _pid):
        read_only_seen.append(conn.execute("PRAGMA query_only").fetchone()[0] == 1)
        return [segment]

    monkeypatch.setattr(stage_auto, "segments", segments)
    monkeypatch.setattr(stage_auto, "family_hints", lambda _segs: [])
    monkeypatch.setattr(camera_plan, "drawn_shots", lambda *_a: [])

    preview = tmp_path / "crew" / "xem_ghep"
    preview.mkdir(parents=True)
    (preview / "top_cut.png").write_bytes(b"fake top cut")
    monkeypatch.setattr(stage_auto, "crew_preview", lambda *_a: {
        "dir": str(preview), "picked": {2: "crew/m3"}, "notes": ["ghi chú fixture"],
    })

    sheets = []

    def stage_sheet(_rd, title, output):
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"fake png")
        sheets.append((title, output))
        return output

    fake_tool = SimpleNamespace(top_cut=lambda *_a, **_k: None, draw_beats=lambda *_a: None, stage_sheet=stage_sheet)
    monkeypatch.setattr(stage_auto, "tool", lambda: fake_tool)
    n5_dir = tmp_path / "canonical-n5"
    monkeypatch.setattr(stage_desk, "seg_dir", lambda *_a: str(n5_dir))

    args = ["--project", "77", "--scene", "1", "--db", str(database), "--data-dir", str(tmp_path)]
    if crew_flag:
        args.append("--beats-crew")
    else:
        args.extend(["--beats", str(tmp_path / "custom-output")])

    assert cli._run(args, {}) is None
    captured = capsys.readouterr().out

    assert len(opened) == 1
    assert read_only_seen == [True]
    assert "shot 2 ← crew/m3" in captured
    assert "ghi chú fixture" in captured
    assert len(sheets) == 1
    if crew_flag:
        assert sheets[0][1] == str(n5_dir / "beats" / "san_khau_canh1.png")
    else:
        assert sheets[0][1] == str(tmp_path / "custom-output" / "san_khau_canh1.png")
    opened[0].close()


def test_beats_crew_requires_exactly_one_scene(tmp_path):
    from tools import stage_auto as cli

    with pytest.raises(SystemExit) as error:
        cli._run(["--project", "77", "--beats-crew", "--db", str(tmp_path / "missing.sqlite")], {})

    assert error.value.code == 2
    assert not (tmp_path / "missing.sqlite").exists()


@pytest.mark.parametrize("beats_args", [["--beats", ""], ["--beats", "custom", "--beats-crew"]])
def test_beats_flags_reject_ambiguous_or_empty_path_before_regular_execution(tmp_path, beats_args):
    from tools import stage_auto as cli

    with pytest.raises(SystemExit) as error:
        cli._run([*beats_args, "--yes", "--max-usd", "100", "--db", str(tmp_path / "missing.sqlite")], {})

    assert error.value.code == 2
    assert not (tmp_path / "missing.sqlite").exists()


def test_beats_crew_does_not_create_missing_database(tmp_path, monkeypatch, capsys):
    from core import features
    from tools import stage_auto as cli

    database = tmp_path / "not-created.sqlite"
    monkeypatch.setattr(features, "REQUIRES", {"stage_auto": []})
    monkeypatch.setattr(features, "on", lambda _name: True)

    assert cli._run(
        ["--project", "77", "--scene", "1", "--beats-crew", "--db", str(database)], {}
    ) == 2
    assert not database.exists()
    assert "Không mở được CSDL chỉ đọc" in capsys.readouterr().err


def test_shared_renderer_falls_back_to_saved_round_without_active_crew(tmp_path, monkeypatch):
    from core import stage_auto

    saved = tmp_path / "saved-round"
    saved.mkdir()
    (saved / "top_cut.png").write_bytes(b"fake top cut")
    output = tmp_path / "beats" / "sheet.png"
    seen = []

    def stage_sheet(source, title, target):
        seen.append((source, title, target))
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_bytes(b"fake png")
        return str(target)

    fake_tool = SimpleNamespace(top_cut=lambda *_a, **_k: None,
                                 draw_beats=lambda source: seen.append((source,)),
                                 stage_sheet=stage_sheet)
    segment = {"id": "1@fixture", "scene": "1", "shots": [{"idx": 2}]}
    monkeypatch.setattr(stage_auto, "crew_preview", lambda *_a: None)
    monkeypatch.setattr(stage_auto, "result_round", lambda *_a: str(saved))
    monkeypatch.setattr(stage_auto, "tool", lambda: fake_tool)

    result = stage_auto.render_beats_sheet(str(tmp_path), 77, segment, str(output))

    assert result["ok"] is True
    assert result["nguon"] == "luot_hien_tai"
    assert "lan_do" not in result
    assert seen[0] == (str(saved),)
    assert seen[1][0] == str(saved)
    assert output.is_file()


def test_shared_renderer_contains_malformed_crew_state_error(tmp_path, monkeypatch):
    from core import stage_auto

    monkeypatch.setattr(stage_auto, "crew_preview", lambda *_a: (_ for _ in ()).throw(AttributeError("bad fixture")))
    monkeypatch.setattr(stage_auto, "result_round", lambda *_a: pytest.fail("do not fall back after bad crew state"))

    result = stage_auto.render_beats_sheet(str(tmp_path), 77, {"scene": "1", "shots": [{"idx": 2}]},
                                           str(tmp_path / "unused.png"))

    assert result["ok"] is False
    assert "AttributeError" in result["errors"][0]
    assert "bad fixture" not in result["errors"][0]
