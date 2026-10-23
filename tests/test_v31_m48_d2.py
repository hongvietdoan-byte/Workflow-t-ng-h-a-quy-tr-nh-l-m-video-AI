"""CX23-M48-D2: Đợt 2 bàn đạo diễn — tests đỏ→xanh cho N12/N14/N15/N16.

Chỉ dùng thư mục và SQLite tạm; không mở Blender thật, không gọi API, không chạm dữ liệu dự án thật.
"""
import hashlib
import json
import os
import sqlite3
from types import SimpleNamespace
from unittest import mock

import pytest

from core import stage_auto, stage_desk
from tools import stage_previs


def _m48_d2_ui_page():
    from types import SimpleNamespace
    from dashboard import stage_desk_ui
    stage_desk_ui.render_scene(SimpleNamespace(conn=object()), 7, "data/fixture", "3")


def _db_sha(conn):
    return hashlib.sha256("\n".join(conn.iterdump()).encode("utf-8")).hexdigest()


def test_stage_previs_run_extracts_cli_work_and_passes_options(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE marker(value TEXT)")
    before = _db_sha(conn)
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "cfg.json").write_text("{}", encoding="utf-8")
    (rd / "v2.json").write_text(json.dumps({"shots": [{"shot": 10, "best": {"m": {"camera": "fixture"}}}]}), encoding="utf-8")
    seg = {"scene": "3", "stage": "room", "place": {"id": 7}, "entry": {}, "shots": []}
    planned = {"previs": {"duration": 4.0, "res": [720, 1280]}, "summary": {"unrouted": [], "total_s": 4.0}}
    with mock.patch.object(stage_auto, "segments", return_value=[seg]), \
         mock.patch.object(stage_auto, "result_round", return_value=str(rd)), \
         mock.patch.object(stage_previs, "plan", return_value=planned) as plan, \
         mock.patch.object(stage_previs, "ref_problems", return_value=[]), \
         mock.patch("stage_grid.run_blender_safe") as blender, \
         mock.patch.object(stage_previs, "encode", side_effect=lambda frames, prefix, fps, path: path):
        out = stage_previs.run(conn, 7, "3", shots={10}, out=str(tmp_path / "out"),
                               opts={"uniform_run": True, "lens_range": (24, 35), "orbit": 35})
    assert out["ok"] is True
    assert plan.call_args.kwargs["uniform_run"] is True
    assert plan.call_args.kwargs["lens_range"] == (24, 35)
    assert plan.call_args.kwargs["orbit"] == 35
    assert blender.call_args.kwargs["timeout"] == 3600
    assert _db_sha(conn) == before


def test_stage_previs_run_rejects_unrouted_without_creating_output(tmp_path):
    conn = sqlite3.connect(":memory:")
    rd = tmp_path / "round"
    rd.mkdir()
    out = tmp_path / "out"
    seg = {"scene": "3", "stage": "room", "place": {"id": 7}, "entry": {}, "shots": []}
    planned = {"previs": {"duration": 4.0, "res": [720, 1280]}, "summary": {"unrouted": [10]}}
    with mock.patch.object(stage_auto, "segments", return_value=[seg]), \
         mock.patch.object(stage_auto, "result_round", return_value=str(rd)), \
         mock.patch.object(stage_previs, "plan", return_value=planned), \
         mock.patch.object(stage_previs, "ref_problems", return_value=[]), \
         mock.patch("stage_grid.run_blender_safe") as blender:
        result = stage_previs.run(conn, 7, "3", out=str(out), opts={})
    assert result["ok"] is False
    assert "không tìm được lối" in result["errors"][0]
    assert not out.exists()
    blender.assert_not_called()


def test_stage_previs_run_rejects_mixed_shots_without_measurements_instead_of_silently_omitting(tmp_path):
    conn = sqlite3.connect(":memory:")
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "v2.json").write_text(json.dumps({"shots": [
        {"shot": 10, "best": {"m": {"camera": "fixture"}}},
        {"shot": 11, "best": None},
    ]}), encoding="utf-8")
    seg = {"scene": "3", "stage": "room", "place": {"id": 7}, "entry": {}, "shots": []}
    output = tmp_path / "out"
    with mock.patch.object(stage_auto, "segments", return_value=[seg]), \
         mock.patch.object(stage_auto, "result_round", return_value=str(rd)), \
         mock.patch.object(stage_previs, "plan") as plan, \
         mock.patch("stage_grid.run_blender_safe") as blender:
        result = stage_previs.run(conn, 7, "3", shots={10, 11}, out=str(output), opts={})
    assert result["ok"] is False
    assert "11" in result["errors"][0] and "không có máy đo được" in result["errors"][0]
    assert not output.exists()
    plan.assert_not_called()
    blender.assert_not_called()


def test_n12_progress_shows_output_paths_and_actual_shots():
    from dashboard import stage_desk_ui

    pr = {"state": "done", "action": "N12", "label": "Previs cục bộ", "updated": "fixture",
          "step": "đã render clay + depth", "result": {
              "ok": True, "path": "D:/fixture/scene_clay.mp4", "depth_path": "D:/fixture/scene_depth.mp4",
              "plan_path": "D:/fixture/scene_plan.json", "summary": {"shots": [10, 12]},
          }}
    with mock.patch.object(stage_desk_ui.st, "success") as success, \
         mock.patch.object(stage_desk_ui.st, "caption") as caption, \
         mock.patch.object(stage_desk_ui.st, "code") as code:
        stage_desk_ui._show_progress(pr)
    success.assert_called_once()
    captions = " ".join(str(call.args[0]) for call in caption.call_args_list)
    assert "shot" in captions.casefold() and "10, 12" in captions
    paths = " ".join(str(call.args[0]) for call in code.call_args_list)
    assert "scene_clay.mp4" in paths and "scene_depth.mp4" in paths and "scene_plan.json" in paths


def test_stage_previs_plan_only_writes_new_plan_without_blender_or_database_change(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE marker(value TEXT)")
    before = _db_sha(conn)
    rd = tmp_path / "round"
    rd.mkdir()
    output = tmp_path / "out"
    seg = {"scene": "3", "stage": "room", "place": {"id": 7}, "entry": {}, "shots": []}
    planned = {"previs": {"duration": 4.0}, "summary": {"unrouted": [], "total_s": 4.0}}
    with mock.patch.object(stage_auto, "segments", return_value=[seg]), \
         mock.patch.object(stage_auto, "result_round", return_value=str(rd)), \
         mock.patch.object(stage_previs, "plan", return_value=planned), \
         mock.patch.object(stage_previs, "ref_problems", return_value=[]), \
         mock.patch("stage_grid.run_blender_safe") as blender:
        result = stage_previs.run(conn, 7, "3", out=str(output), opts={"plan_only": True})
    assert result["ok"] is True
    assert json.loads((tmp_path / "out" / os.path.basename(result["plan_path"])).read_text(encoding="utf-8")) == planned
    assert not list(output.glob("*_blender"))
    blender.assert_not_called()
    assert _db_sha(conn) == before


def test_n12_runs_background_previs_with_read_only_database(tmp_path):
    db = tmp_path / "fixture.sqlite"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE marker(value TEXT)")
    conn.execute("INSERT INTO marker VALUES('before')")
    conn.commit()
    before = _db_sha(conn)
    seg = {"id": "3@room", "scene": "3", "stage": "room", "shots": [{"idx": 10}]}
    seen = {}

    def fake_run(background_conn, *_args, **_kwargs):
        try:
            background_conn.execute("INSERT INTO marker VALUES('after')")
        except sqlite3.OperationalError:
            seen["write_blocked"] = True
        else:
            seen["write_blocked"] = False
        return {"ok": True}

    with mock.patch.object(stage_desk, "_need_edit", return_value=None), \
         mock.patch.object(stage_desk, "segment", return_value=seg), \
         mock.patch.object(stage_desk, "seg_dir", return_value=str(tmp_path / "segment")), \
         mock.patch("tools.stage_previs.run", side_effect=fake_run):
        result = stage_desk.previs(conn, 7, str(tmp_path), "3", shots={10}, who={"kind": "human", "who": "fake"})
        assert result["ok"] is True and result["started"] is True
        assert stage_desk.wait(7, timeout=5)

    progress = json.loads((tmp_path / "segment" / stage_desk.PROGRESS_FILE).read_text(encoding="utf-8"))
    assert progress["state"] == "done"
    assert seen == {"write_blocked": True}
    assert _db_sha(conn) == before
    conn.close()


def test_crew_user_pick_accepts_only_history_and_does_not_write_database(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE marker(value TEXT)")
    before = _db_sha(conn)
    seg = {"id": "3@room", "scene": "3", "shots": [{"idx": 10}, {"idx": 11}]}
    state_dir = tmp_path / "segment" / "crew"
    state_dir.mkdir(parents=True)
    state_file = state_dir / "state.json"
    original = {"phase": "duyet", "shot_hist": {"10": ["m1", "m2"]}, "accepted": {}}
    state_file.write_text(json.dumps(original), encoding="utf-8")
    def inline_sync(_data_dir, _pid, _seg, _action, _who, _conn, fn):
        return fn()
    with mock.patch.object(stage_desk, "segment", return_value=seg), \
         mock.patch.object(stage_desk, "seg_dir", return_value=str(state_dir.parent)), \
         mock.patch.object(stage_desk, "_sa", return_value=SimpleNamespace(CREW_DIR="crew")), \
         mock.patch.object(stage_desk, "_sync", side_effect=inline_sync):
        bad = stage_desk.crew_user_pick(conn, 7, str(tmp_path), "3", 10, "m9", {"kind": "human", "who": "x"})
        assert bad["ok"] is False
        assert json.loads(state_file.read_text(encoding="utf-8")) == original
        good = stage_desk.crew_user_pick(conn, 7, str(tmp_path), "3", 10, "m1", {"kind": "human", "who": "x"})
    assert good["ok"] is True
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["accepted"]["10"] == "m1"
    assert stage_auto._crew_pick({}, state, "10") == "m1"
    assert _db_sha(conn) == before


def test_world_map_refresh_is_hidden_when_flag_is_off(tmp_path):
    conn = sqlite3.connect(":memory:")
    seg = {"id": "3@room", "scene": "3", "stage": "room", "shots": []}
    with mock.patch.object(stage_desk, "segment", return_value=seg), \
         mock.patch("core.world_map.enabled", return_value=False), \
         mock.patch("core.world_map.refresh") as refresh:
        result = stage_desk.refresh_world_map(conn, 7, str(tmp_path), "3", {"kind": "human", "who": "x"})
    assert result["ok"] is False
    refresh.assert_not_called()


def test_n15_refresh_when_enabled_does_not_write_database(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE marker(value TEXT)")
    before = _db_sha(conn)
    seg = {"id": "3@room", "scene": "3", "stage": "room", "shots": []}
    sa = SimpleNamespace(k1_cached=mock.Mock(return_value=str(tmp_path / "k1")),
                         base_dir=mock.Mock(return_value=str(tmp_path / "base")))
    with mock.patch.object(stage_desk, "_need_edit", return_value=None), \
         mock.patch.object(stage_desk, "segment", return_value=seg), \
         mock.patch.object(stage_desk, "seg_dir", return_value=str(tmp_path / "segment")), \
         mock.patch.object(stage_desk, "_sa", return_value=sa), \
         mock.patch("core.world_map.enabled", return_value=True), \
         mock.patch("core.world_map.refresh", return_value={"kind": "fixture", "why": "fixture", "map_revision": "fixture"}) as refresh, \
         mock.patch("core.world_map.path", return_value=str(tmp_path / "world-map.json")):
        result = stage_desk.refresh_world_map(conn, 7, str(tmp_path), "3", {"kind": "human", "who": "fake"})
    assert result["ok"] is True
    refresh.assert_called_once()
    assert _db_sha(conn) == before


def test_stage_family_suggestions_are_yellow_and_do_not_merge():
    segs = [
        {"stage": "kho1", "place": {"id": 1}, "entry": {"stage_family": None, "spots": {"door": [1]}}},
        {"stage": "kho2", "place": {"id": 2}, "entry": {"stage_family": None, "spots": {"door": [1]}}},
    ]
    suggestions = stage_auto.family_suggestions(segs)
    assert suggestions == [{"place_ids": [1, 2], "spots": {"door": [1]}, "family": None,
                           "members": [{"place_id": 1, "stage": "kho1", "declared": None},
                                       {"place_id": 2, "stage": "kho2", "declared": None}], "declared_conflict": False}]
    assert stage_auto.family_hints(segs)
    assert [s["stage"] for s in segs] == ["kho1", "kho2"]
    assert stage_auto.family_suggestions([
        {"stage": "kho1", "place": {"id": 3}, "entry": {"spots": {}}},
        {"stage": "kho2", "place": {"id": 4}, "entry": {"spots": {}}},
    ]) == []


def test_set_family_wrapper_uses_existing_store_write_and_requires_two_places(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE assets(id INTEGER PRIMARY KEY, profile TEXT)")
    for asset_id in (1, 2):
        conn.execute("INSERT INTO assets(id,profile) VALUES(?,?)", (asset_id, json.dumps({"model3d": {"file": "fake.blend"}})))
    seg = {"id": "3@room", "scene": "3", "stage": "kho1", "place": {"id": 1},
           "entry": {"stage_family": None, "spots": {"door": [1]}}, "shots": [{"id": 1, "idx": 10}]}
    seg2 = {"id": "4@room", "scene": "4", "stage": "kho2", "place": {"id": 2},
            "entry": {"stage_family": None, "spots": {"door": [1]}}, "shots": [{"id": 2, "idx": 11}]}
    class NoopHolds:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    with mock.patch.object(stage_desk, "segment", return_value=seg), \
         mock.patch.object(stage_auto, "segments", return_value=[seg, seg2]), \
         mock.patch.object(stage_desk, "hold_segments", return_value=NoopHolds()):
        short = stage_desk.set_family(conn, 7, str(tmp_path), "3", [1], "room", {"kind": "human", "who": "x"})
        assert short["ok"] is False
        assert json.loads(conn.execute("SELECT profile FROM assets WHERE id=1").fetchone()[0])["model3d"].get("stage_family") is None
        result = stage_desk.set_family(conn, 7, str(tmp_path), "3", [1, 2], "room", {"kind": "human", "who": "x"})
    assert result["ok"] is True
    assert all(json.loads(row[0])["model3d"]["stage_family"] == "room"
               for row in conn.execute("SELECT profile FROM assets ORDER BY id"))


def test_set_family_validates_all_before_writing_any_asset():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE assets(id INTEGER PRIMARY KEY, profile TEXT)")
    conn.execute("INSERT INTO assets(id,profile) VALUES(1,?)", (json.dumps({"model3d": {"file": "fake.blend"}}),))
    before = _db_sha(conn)
    with pytest.raises(ValueError):
        stage_auto.set_family(conn, [1, 99], "room")
    assert _db_sha(conn) == before


def test_stage_desk_ui_routes_new_controls_to_core(tmp_path):
    from dashboard import stage_desk_ui
    from streamlit.testing.v1 import AppTest

    suggestion = {"place_ids": [1, 2], "spots": {"door": [1]}, "family": "room", "members": []}
    status = {"scene": "3", "seg_id": "3@room", "stage": "room", "shots": [10], "phase": "xong", "label": "đã chốt",
              "k1": True, "inputs_changed": False, "inputs_known": True, "marks": {}, "cams": [], "cams_this_stage": [],
              "bad": {}, "round": {"id": 1}, "sheet": None, "drawn": [], "revs": {}, "lock": None, "progress": None,
              "running": False, "user_approves": True, "buttons": ["N12", "N14", "N15", "N16"],
              "shot_hist": {"10": ["m1", "m2"]}, "accepted": {"10": "m1"}, "family_suggestions": [suggestion]}
    core_calls = {name: mock.MagicMock(return_value={"ok": True}) for name in
                  ("previs", "crew_user_pick", "refresh_world_map", "set_family")}
    with mock.patch.object(stage_desk_ui, "enabled", return_value=True), \
         mock.patch.object(stage_desk_ui, "_identity", return_value=({"kind": "human", "who": "fake"}, {"id": "fake"}, False)), \
         mock.patch.object(stage_desk, "scene_status", return_value=status), \
         mock.patch.object(stage_desk, "is_executive_producer", return_value=True), \
         mock.patch.multiple(stage_desk, **core_calls):
        at = AppTest.from_function(_m48_d2_ui_page, default_timeout=30).run()
        assert not at.exception
        for key in ("desk_7_3_N12", "desk_7_3_N14_10", "desk_7_3_N15", "desk_7_3_N16_0"):
            assert any(button.key == key for button in at.button)
        for key in ("desk_7_3_N12", "desk_7_3_N14_10", "desk_7_3_N15", "desk_7_3_N16_0"):
            next(button for button in at.button if button.key == key).click().run()
    assert all(call.called for call in core_calls.values())
    assert core_calls["crew_user_pick"].call_args.args[4:] == (10, "m1")
