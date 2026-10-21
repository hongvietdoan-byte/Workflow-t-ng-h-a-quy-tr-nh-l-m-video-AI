"""C-STAGE-VIEW (cloud-C 21/10): màn XEM sân khấu 3D trên Bước 2 — CHỈ ĐỌC, 0 USD, cờ `stage_view_ui` (TẮT = không gọi gì, Bước 2 y cũ).
Mỗi cảnh truyện một expander: tấm clay / khối, ảnh nền 3D từng shot + hướng máy, sơ đồ world map 2D (SVG tĩnh), người nộm đúng chiều cao
(M3.2) + câu vị trí (M3.3) nếu có, cảnh báo nền cũ / hỏng / map cũ bằng hàm cổng có sẵn; thiếu tệp → "chưa có <gì>, chạy <lệnh>".
Không nút render / gen / ghi; không ghi data/ hay CSDL (mtime + sha không đổi). Thư mục data tạm + CSDL tạm tổng hợp: 2 cảnh, 3 shot
(đủ dữ liệu / thiếu nền / world map cũ)."""
import hashlib
import inspect
import json
import os
import pathlib
from unittest import mock

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
ON = mock.patch.dict(os.environ, {"FEATURE_STAGE_VIEW_UI": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_STAGE_VIEW_UI": ""})


@pytest.fixture
def proj(tmp_path):
    from PIL import Image
    from core.db import connect
    from core.pipeline import Pipeline
    db = tmp_path / "m.sqlite"
    p = Pipeline(connect(str(db)))
    pid = p.create_project("sv")
    data_dir = tmp_path / "data" / "projects"
    rows = [(1, 1, 1, {"plate_view": "landmark"}), (2, 1, 2, {}), (3, 2, 1, {})]
    sids = {}
    for idx, scene, no, extra in rows:
        sid = p.create_scene(pid, idx, f"S{idx}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": scene, "shot_no": no, "characters": ["KELLY"],
                                                                            **extra}), sid))
        sids[idx] = sid
    p.conn.commit()
    plates = data_dir / str(pid) / "plates"
    plates.mkdir(parents=True)
    Image.new("RGB", (1152, 2048), "gray").save(plates / "s1.png")
    (plates / "index.json").write_text(json.dumps({str(sids[1]): {"plate": str(plates / "s1.png"), "place": "Mê cung", "key": "k1",
                                                                  "camera": {"location": [0, -5, 1.6], "look_at": [0, 0, 1.2]}}}),
                                       encoding="utf-8")
    world = data_dir / str(pid) / "world"
    world.mkdir(parents=True)
    ents = [{"entity_id": "kelly", "label": "KELLY", "kind": "nguoi", "transform": {"xyz": [1.0, 2.0, 0.0]}, "valid_from": None,
             "valid_to": None},
            {"entity_id": "rao", "label": "rào", "kind": "vat", "transform": {"xyz": [3.0, 1.0, 0.0]}, "valid_from": None, "valid_to": None}]
    (world / "scene_1.json").write_text(json.dumps({"scene": 1, "kind": "3d", "entities": ents, "sources": {}}), encoding="utf-8")
    (world / "scene_2.json").write_text(json.dumps({"scene": 2, "kind": "3d", "entities": ents, "sources": {},
                                                    "invalidated": {"why": "blocking_changed"}}), encoding="utf-8")
    return p, pid, str(data_dir), db, sids


def _snapshot(root, db):
    files = {str(f): f.stat().st_mtime_ns for f in pathlib.Path(root).rglob("*") if f.is_file()}
    return files, hashlib.sha256(pathlib.Path(db).read_bytes()).hexdigest()


def test_flag_registered_off_golden_and_areas():
    from core import features
    from dashboard import stage_view_ui as U
    assert U.FLAG == "stage_view_ui" and features.FEATURES[U.FLAG]["verified"] is False
    assert features.FEATURES[U.FLAG]["label"].startswith("Xem sân khấu 3D (chỉ đọc)")
    with OFF:
        assert not U.enabled()
    golden = json.loads((ROOT / "tests" / "golden" / "package_inputs.json").read_text(encoding="utf-8"))
    assert all(golden[k]["flags"][U.FLAG] is False for k in ("image", "video"))
    areas = json.loads((ROOT / "devsys" / "areas.json").read_text(encoding="utf-8"))
    step2 = next(a for a in areas["areas"] if a["id"] == "step2")
    assert "dashboard/stage_view_ui.py" in step2["code"] and "tests/test_v31_stage_view.py" in step2["tests"] and U.FLAG in step2["flags"]


def test_flag_off_calls_nothing(proj):
    from dashboard import stage_view_ui as U
    p, pid, data_dir, _, _ = proj
    with OFF, mock.patch.object(U, "st") as st, mock.patch.object(U, "collect", side_effect=AssertionError("đọc khi cờ tắt")):
        U.render(p, pid, data_dir)
    assert st.mock_calls == []


def test_step2_calls_it_above_the_gen_block():
    src = (ROOT / "dashboard" / "steps" / "step2.py").read_text(encoding="utf-8")
    call, gen = src.index("stage_view_ui.render(p, pid, C.DATA)"), src.index('D_card("sb-gen")')
    assert call < gen


def test_collect_groups_scenes_and_shots(proj):
    from dashboard import stage_view_ui as U
    p, pid, data_dir, _, sids = proj
    got = U.collect(p, pid, data_dir)
    assert [s["scene"] for s in got] == ["1", "2"]
    s1 = got[0]
    assert [sh["idx"] for sh in s1["shots"]] == [1, 2]
    assert s1["shots"][0]["plate"].endswith("s1.png") and s1["shots"][0]["plate_view"] == "landmark"
    assert s1["shots"][0]["camera"]["location"] == [0, -5, 1.6]
    assert s1["shots"][1]["plate"] is None
    assert any("chưa có nền 3D" in m and "shot 2" in m and "tools/location_pack.py" in m for m in s1["missing"])


def test_world_map_drawn_and_old_map_warned(proj):
    from dashboard import stage_view_ui as U
    p, pid, data_dir, _, _ = proj
    s1, s2 = U.collect(p, pid, data_dir)
    assert s1["world"]["points"] and "KELLY" in U.svg(s1["world"]["points"], s1["world"]["cameras"])
    assert any("world map" in w and "blocking_changed" in w for w in s2["warnings"])


def test_missing_stage_and_map_are_said_with_a_command(proj, tmp_path):
    from dashboard import stage_view_ui as U
    p, pid, data_dir, _, _ = proj
    os.remove(os.path.join(data_dir, str(pid), "world", "scene_1.json"))
    s1 = U.collect(p, pid, data_dir)[0]
    assert any("chưa có world map" in m for m in s1["missing"])
    assert any("chưa có sân khấu 3D" in m and "tools/stage_auto.py" in m for m in s1["missing"])


def test_reads_nothing_writes_nothing(proj):
    from dashboard import stage_view_ui as U
    p, pid, data_dir, db, _ = proj
    root = pathlib.Path(data_dir).parent
    before = _snapshot(root, db)
    with ON, mock.patch.object(U, "st"):
        U.render(p, pid, data_dir)
    p.conn.commit()
    assert _snapshot(root, db) == before


def test_paths_come_from_data_dir_not_cwd(proj, tmp_path, monkeypatch):
    from dashboard import stage_view_ui as U
    p, pid, data_dir, _, _ = proj
    elsewhere = tmp_path / "khac"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert U.collect(p, pid, data_dir)[0]["shots"][0]["plate"]


def test_thumbnail_is_small_and_big_files_are_refused(tmp_path):
    from PIL import Image
    from dashboard import stage_view_ui as U
    big = tmp_path / "b.png"
    Image.new("RGB", (2000, 3000), "red").save(big)
    img, why = U.thumb(str(big))
    assert img is not None and max(img.size) <= U.THUMB_PX and why is None
    with mock.patch.object(U, "MAX_BYTES", 10):
        img, why = U.thumb(str(big))
    assert img is None and "quá lớn" in why
    assert U.thumb(str(tmp_path / "khong_co.png"))[0] is None


def test_no_action_buttons_in_the_view():
    from dashboard import stage_view_ui as U
    src = inspect.getsource(U)
    assert "st.button" not in src and "form_submit" not in src
    for word in ("render(cfg", "submit", "ensure_async", "world_map.save", "world_map.refresh", ".execute(\"UPDATE", "INSERT", "CREATE"):
        assert word not in src, word


def test_dummy_heights_and_sentence_only_when_flags_on(proj):
    from dashboard import stage_view_ui as U
    p, pid, data_dir, _, _ = proj
    with mock.patch.dict(os.environ, {"FEATURE_WHITEBOX_HEIGHT_DUMMY": "1", "FEATURE_WORLD_MAP_SENTENCES": "1"}), \
         mock.patch("core.assets.standard_for", return_value={"height_m": 1.65}):
        s1 = U.collect(p, pid, data_dir)[0]
    assert s1["dummies"] == {"KELLY": 1.65}
    assert "sentence" in s1["shots"][0]
    with mock.patch.dict(os.environ, {"FEATURE_WHITEBOX_HEIGHT_DUMMY": "", "FEATURE_WORLD_MAP_SENTENCES": ""}):
        s1 = U.collect(p, pid, data_dir)[0]
    assert s1["dummies"] is None and "sentence" not in s1["shots"][0]
