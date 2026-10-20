"""DP8 — V3.1 M3.1 scene_world_map THỬ NGHIỆM offline (cờ world_map TẮT, G2-4). Fixture TỔNG HỢP theo #31: cảnh 4 mê cung (shot 13–18,
sân khấu 3D đo được), cảnh 6 xác bay (shot 26–29, chỉ BYĐ → quan hệ tương đối), cảnh 8 keo + địch (shot 34–38, chưa có gì → UNKNOWN).
Thiết kế docs/V3_1_M3_THIET_KE_WORLD_MAP_2026-10-20.md mục 2."""
import json
import os
import pathlib
import re
from unittest import mock

import pytest

from core import world_map as W

ON = mock.patch.dict(os.environ, {"FEATURE_WORLD_MAP": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_WORLD_MAP": ""})

STAGE = {"origin_model": [10.0, 5.0, 0.0], "axes": {"x": "E", "y": "N", "z": "up"},
         "marks": {"thap_chan": {"xyz": [0.0, 30.0, 0.0]}, "thap_dinh": {"xyz": [0.0, 30.0, 42.0]}}}
BLOCKING_C4 = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0.0, 0.0], "H": 1.68, "facing": 90, "label": "KELLY"},
                           {"key": "dich1", "kind": "nguoi", "at": [6.0, 2.0], "H": 1.8, "facing": 270, "label": "LÍNH ĐỊCH"},
                           {"key": "rao", "kind": "khoi", "at": [3.0, 1.0], "w": 0.3, "h": 1.5, "label": "rào"},
                           {"key": "thap", "kind": "moc", "label": "tháp"}],
               "beats": {"n1": {}, "n2": {"dich1": {"at": [4.0, 2.0]}}, "n3": {"dich1": {"hidden": True}}}}
SPECS_C4 = {"shots": [{"shot": 13, "nhip": "n1"}, {"shot": 14, "nhip": "n2"}, {"shot": 15, "nhip": "n2"}, {"shot": 16, "nhip": "n3"},
                      {"shot": 17, "nhip": "n3"}, {"shot": 18, "nhip": "n1"}]}
BYD_C6 = {26: {"shot": 26, "thanh_phan": [{"vat": "KELLY", "vai": "chinh", "vung": "trai"}, {"vat": "XAC", "vai": "phu", "vung": "phai"}],
               "vat": [{"ten": "AWM", "nguoi": "KELLY"}]},
          27: {"shot": 27, "thanh_phan": [{"vat": "KELLY", "vai": "chinh", "vung": "giua"}], "vat": ["AWM"]}}


def _stage(tmp_path, blocking=BLOCKING_C4, specs=SPECS_C4):
    k1 = tmp_path / "stage" / "mecung" / "k1_o"
    seg = tmp_path / "stage" / "mecung" / "doan_4"
    k1.mkdir(parents=True)
    seg.mkdir(parents=True)
    (k1 / "stage.json").write_text(json.dumps(STAGE), encoding="utf-8")
    (k1 / "grid.json").write_text(json.dumps({"cells": []}), encoding="utf-8")
    (seg / "blocking.json").write_text(json.dumps(blocking, ensure_ascii=False), encoding="utf-8")
    if specs is not None:
        (seg / "shot_specs.json").write_text(json.dumps(specs), encoding="utf-8")
    return str(k1), str(seg)


def _rows(m, key):
    return [(e["valid_from"], e["valid_to"], (e["transform"] or {}).get("xyz")) for e in m["entities"] if e["entity_id"] == key]


# ---- 3D (cảnh 4) ---------------------------------------------------------------------------------------------------------------
def test_scene4_3d_entities_follow_the_beats(tmp_path):
    k1, seg = _stage(tmp_path)
    m = W.build(4, k1_dir=k1, seg_dir=seg, world_id="p31_me_cung")
    assert m["kind"] == "3d" and W.check(m) == []
    assert _rows(m, "kelly") == [(13, 18, [0.0, 0.0, 0.0])]                       # đứng yên cả cảnh: một dòng
    assert _rows(m, "dich1") == [(13, 13, [6.0, 2.0, 0.0]), (14, 15, [4.0, 2.0, 0.0]), (18, 18, [6.0, 2.0, 0.0])]   # vắng 16–17
    thap = [e for e in m["entities"] if e["entity_id"] == "thap"][0]
    assert thap["transform"]["xyz"] == [0.0, 30.0, 0.0] and thap["dimensions"] == {"h": 42.0} and thap["source"] == "stage_marks"
    assert m["landmarks"][0]["entity_id"] == "thap"
    kelly = [e for e in m["entities"] if e["entity_id"] == "kelly"][0]
    assert kelly["dimensions"]["h"] == 1.68 and kelly["confidence"] == "do"
    assert m["origin"]["model_xyz"] == [10.0, 5.0, 0.0] and m["sources"]["blocking_json_sha"]


def test_missing_numbers_are_unknown_not_invented(tmp_path):
    bl = {"objects": [{"key": "xac", "kind": "khoi", "label": "xác"}, {"key": "thap", "kind": "moc", "from_marks": "khong_co"}]}
    k1, seg = _stage(tmp_path, bl, None)
    m = W.build(4, k1_dir=k1, seg_dir=seg)
    assert {e["entity_id"]: (e["transform"], e["confidence"]) for e in m["entities"]} == {"xac": (None, "unknown"), "thap": (None, "unknown")}
    assert all(e["valid_from"] is None for e in m["entities"]) and W.check(m) == []


# ---- tương đối (cảnh 6) / UNKNOWN (cảnh 8) / 2D ------------------------------------------------------------------------------
def test_scene6_relative_from_byd():
    m = W.build(6, byd=BYD_C6)
    assert m["kind"] == "relative" and W.check(m) == []
    assert m["relations"] == [{"a": "KELLY", "rel": "trai_cua", "b": "XAC", "frame": "may_shot", "valid_from": 26, "valid_to": 26,
                               "source": "byd"}]
    kelly = [e for e in m["entities"] if e["entity_id"] == "KELLY"][0]
    assert kelly["state"] == {"cam": ["AWM"]} and kelly["transform"] is None and (kelly["valid_from"], kelly["valid_to"]) == (26, 27)


def test_scene8_nothing_is_unknown_with_why(tmp_path):
    m = W.build(8, k1_dir=str(tmp_path / "none"), seg_dir=str(tmp_path / "none"), byd={34: {"shot": 34, "thanh_phan": [{"vat": "KELLY"}]}})
    assert m["kind"] == "unknown" and m["entities"] == [] and "không bịa" in m["why"] and "sân khấu 3D" in m["why"]
    assert W.check(m) == []
    assert W.build(8)["kind"] == "unknown"


def test_plan_2d_keeps_z_unknown(tmp_path):
    plan = tmp_path / "plan2d_8.json"
    plan.write_text(json.dumps({"by": "người dùng", "points": [{"entity_id": "tuong_keo", "xy": [2, 3], "valid_from": 34, "valid_to": 38}]}),
                    encoding="utf-8")
    m = W.build(8, plan2d_file=str(plan))
    assert m["kind"] == "2d" and m["entities"][0]["transform"]["xyz"] == [2.0, 3.0, None] and m["provenance"]["by"] == "human"
    assert W.check(m) == []


def test_check_refuses_invented_or_broken_maps():
    m = W.build(6, byd=BYD_C6)
    m["entities"][0]["transform"] = {"xyz": [1, 2, 3]}
    assert any("tương đối" in p for p in W.check(m))
    u = W.build(8)
    u["why"] = None
    assert any("why" in p for p in W.check(u))
    assert any("kind" in p for p in W.check(dict(u, kind="maybe", why="x")))


# ---- lưu, version, invalidation, cờ --------------------------------------------------------------------------------------------
def test_flag_off_reads_and_writes_nothing(tmp_path):
    k1, seg = _stage(tmp_path)
    with OFF:
        assert W.refresh(str(tmp_path), 31, 4, k1_dir=k1, seg_dir=seg) is None
    assert not (tmp_path / "31" / "world").exists()


def test_revision_bumps_only_when_a_source_changes(tmp_path):
    k1, seg = _stage(tmp_path)
    with ON:
        first = W.refresh(str(tmp_path), 31, 4, k1_dir=k1, seg_dir=seg)
        again = W.refresh(str(tmp_path), 31, 4, k1_dir=k1, seg_dir=seg)
        assert first["map_revision"] == again["map_revision"] == 1
        bl = json.loads(pathlib.Path(seg, "blocking.json").read_text(encoding="utf-8"))
        bl["objects"][0]["at"] = [1.0, 0.0]
        pathlib.Path(seg, "blocking.json").write_text(json.dumps(bl, ensure_ascii=False), encoding="utf-8")
        assert W.stale(W.load(str(tmp_path), 31, 4), W.sources(k1, seg)) == "blocking_changed"
        new = W.refresh(str(tmp_path), 31, 4, k1_dir=k1, seg_dir=seg)
    assert new["map_revision"] == 2 and W.load(str(tmp_path), 31, 4)["map_revision"] == 2
    old = json.loads((tmp_path / "31" / "world" / "history" / "scene_4_r1.json").read_text(encoding="utf-8"))
    assert old["invalidated"]["why"] == "blocking_changed" and old["invalidated"]["by_revision"] == 2
    assert W.entities_at(old, 13) == []                                          # số cũ không dùng
    assert [e["entity_id"] for e in W.entities_at(new, 16)] == ["kelly", "rao", "thap"]   # địch vắng ở nhịp n3


def test_geometry_change_is_said():
    assert W.stale({"sources": {"stage_json_sha": "a"}}, {"stage_json_sha": "b"}) == "geometry_changed"
    assert W.stale({"sources": {"byd": {"26": "a"}}}, {"byd": {"26": "b"}}) == "byd_changed"


def test_save_refuses_a_broken_map(tmp_path):
    u = W.build(8)
    u["kind"] = "nope"
    with pytest.raises(ValueError):
        W.save(str(tmp_path), 31, u)


def test_nothing_in_the_gen_path_reads_the_map():
    """G2-4: thử nghiệm offline — không module nào khác của core/ / dashboard/ import world_map."""
    root = pathlib.Path(__file__).resolve().parent.parent
    use = re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+[^\n]*\bworld_map\b|\bworld_map\.\w", re.M)   # import / gọi hàm (tên cờ không tính)
    users = [str(p.relative_to(root)) for d in ("core", "dashboard") for p in (root / d).rglob("*.py")
             if p.name != "world_map.py" and use.search(p.read_text(encoding="utf-8", errors="replace"))]
    assert users == []
