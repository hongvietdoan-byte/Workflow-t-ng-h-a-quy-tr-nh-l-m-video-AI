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
    # C-STAGE-VIEW (21/10): màn XEM sân khấu 3D (cờ stage_view_ui) chỉ đọc map để hiện — không thuộc đường gen; cấm ghi / dựng map
    # C-3D-GOC-B (22/10): nguồn bố cục chung core/layout_facts (positions) + bất biến R1 core/position_invariants chỉ ĐỌC map để báo —
    # không đưa vào gói gửi / mệnh đề QC, không ghi / dựng map
    read_only_views = {"dashboard/stage_view_ui.py", "core/layout_facts.py", "core/position_invariants.py"}
    # M4.8 N15 (24/10): Bàn đạo diễn 3D được DỰNG LẠI map theo yêu cầu người có quyền sửa, CHỈ khi cờ world_map BẬT — vẫn không thuộc đường gen
    flag_gated_editors = {"core/stage_desk.py"}
    assert [u for u in users if u.replace("\\", "/") not in read_only_views | flag_gated_editors] == []
    for ed in flag_gated_editors:
        src = (root / ed).read_text(encoding="utf-8")
        assert src.count("world_map.refresh(") == 1 and "if not world_map.enabled():" in src, ed
    for view in read_only_views:
        src = (root / view).read_text(encoding="utf-8")
        for word in ("world_map.refresh(", "world_map.save(", "world_map.build", "world_map._write("):
            assert word not in src, (view, word)


# ---- 22/10: dữ liệu thật để blocking.json trong THƯ MỤC LƯỢT (doan_<cảnh>/result.json → round) -----------------------------------
def _round_stage(tmp_path, round_name="cc_20261016_104931", blocking=True, k1=False, scene="4"):
    """Bố cục như data/projects/31/stage/kho265/doan_4: result.json round → <round>/{stage.json, grid.json, blocking.json, shot_specs.json}."""
    seg = tmp_path / "31" / "stage" / "kho265" / f"doan_{scene}"
    rd = seg / round_name
    rd.mkdir(parents=True)
    (seg / "result.json").write_text(json.dumps({"round": round_name.replace(os.sep, "/"), "cams": {"14": {}}}), encoding="utf-8")
    (rd / "stage.json").write_text(json.dumps(STAGE), encoding="utf-8")
    (rd / "grid.json").write_text(json.dumps({"cells": []}), encoding="utf-8")
    if blocking:
        (rd / "blocking.json").write_text(json.dumps(BLOCKING_C4, ensure_ascii=False), encoding="utf-8")
        (rd / "shot_specs.json").write_text(json.dumps(SPECS_C4), encoding="utf-8")
    k1_dir = None
    if k1:
        k1_dir = seg.parent / "k1_trungtammecung_60"
        k1_dir.mkdir()
        (k1_dir / "stage.json").write_text(json.dumps(dict(STAGE, origin_model=[1.0, 2.0, 3.0])), encoding="utf-8")
    return str(seg), str(rd), (str(k1_dir) if k1_dir else None)


def test_default_refresh_finds_the_round_blocking(tmp_path):
    """Lỗi 22/10: refresh mặc định (không truyền seg_dir) không bao giờ ra 3D — blocking ở doan_<cảnh>/<round>/, không ở doan_<cảnh>/."""
    seg, rd, _ = _round_stage(tmp_path)
    with ON:
        m = W.refresh(str(tmp_path), 31, 4)
    assert m["kind"] == "3d" and W.check(m) == []
    assert _rows(m, "kelly") == [(13, 18, [0.0, 0.0, 0.0])]
    assert m["origin"]["stage"] == "kho265" and m["provenance"]["round"] == "cc_20261016_104931"
    assert m["provenance"]["stage_json_from"] == "round"
    assert m["sources"]["blocking_json_sha"] == W.sources(rd, rd)["blocking_json_sha"]
    assert (tmp_path / "31" / "world" / "scene_4.json").exists()


def test_round_dir_with_explicit_k1_and_missing_k1_falls_back_to_round(tmp_path):
    seg, rd, k1 = _round_stage(tmp_path, k1=True)
    m = W.build(4, k1_dir=k1, seg_dir=seg)                                      # doan_<cảnh> → result.json → round
    assert m["kind"] == "3d" and m["origin"]["model_xyz"] == [1.0, 2.0, 3.0] and m["provenance"]["stage_json_from"] == "k1"
    gone = os.path.join(os.path.dirname(k1), "k1_mecungngarebac_42")             # #31 cảnh 4: K1 theo chỗ đứng chính hiện tại chưa đo
    m = W.build(4, k1_dir=gone, seg_dir=seg)
    assert m["kind"] == "3d" and m["provenance"]["stage_json_from"] == "round" and m["origin"]["model_xyz"] == [10.0, 5.0, 0.0]


def test_round_without_blocking_says_why_relative_and_unknown(tmp_path):
    """#31 cảnh 3: round 'crew/final' không có blocking.json → không 3D, map nói RÕ lý do (cả khi tương đối), không im lặng."""
    _round_stage(tmp_path, round_name=os.path.join("crew", "final"), blocking=False, scene="3")
    with ON:
        rel = W.refresh(str(tmp_path), 31, 3, byd=BYD_C6)
        unk = W.refresh(str(tmp_path), 31, 9)
    assert rel["kind"] == "relative" and "crew/final" in rel["why"] and "không có blocking.json" in rel["why"] and W.check(rel) == []
    assert unk["kind"] == "unknown" and "doan_9" in unk["why"] and "không bịa" in unk["why"]


def test_round_missing_on_disk_and_legacy_root_blocking(tmp_path):
    seg, rd, _ = _round_stage(tmp_path)
    pathlib.Path(seg, "result.json").write_text(json.dumps({"round": "cc_khong_co"}), encoding="utf-8")
    m = W.build(4, seg_dir=seg)
    assert m["kind"] == "unknown" and "cc_khong_co" in m["why"] and "không có trên đĩa" in m["why"]
    pathlib.Path(seg, "blocking.json").write_text(json.dumps(BLOCKING_C4, ensure_ascii=False), encoding="utf-8")   # đường cũ: dự phòng
    k1, _ = _stage(tmp_path / "k")
    m = W.build(4, k1_dir=k1, seg_dir=seg)
    assert m["kind"] == "3d" and m["provenance"]["round"] is None


def test_axes_read_from_real_k1_keys(tmp_path):
    seg, rd, _ = _round_stage(tmp_path)
    st = dict(STAGE)
    st.pop("axes")
    st.update(axis="x_dong_y_bac", east=[1, 0], north=[0, 1])
    pathlib.Path(rd, "stage.json").write_text(json.dumps(st), encoding="utf-8")
    assert W.build(4, seg_dir=seg)["axes"] == {"axis": "x_dong_y_bac", "east": [1, 0], "north": [0, 1]}
