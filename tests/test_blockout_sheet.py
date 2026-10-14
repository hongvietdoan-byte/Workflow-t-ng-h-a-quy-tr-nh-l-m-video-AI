"""Tấm duyệt thuần PIL và gói lưu tách biệt model3d cũ."""
from copy import deepcopy
from PIL import Image
import pytest
from core import blockout_sheet as sheet
from tests.test_blockout import box, plan


def test_sheet_labels_grid_standing_and_png(tmp_path):
    output = tmp_path / "approval.png"
    result = sheet.render_top_view(plan(box("wall", loai="tuong")), [[0, 0]], output)
    assert Image.open(output).size == (1200, 1000)
    assert result["blocks"][0]["label"] == "wall · tuong · 1×1×2 m"
    assert "K11" in result["cells"] and len(result["cells"]) == 400
    assert result["standing"][0]["at"] == [0, 0]
    assert result["light_direction"] == 90


@pytest.mark.parametrize("source, level", [("anh", "do"), ("kho", "vang")])
def test_problem_blocks_are_colored(tmp_path, source, level):
    p = plan(box("a", nguon=source))
    if level == "do":
        p["khoi"].append(box("b"))
    path = tmp_path / "issues.png"
    result = sheet.render_top_view(p, [], path)
    b = result["blocks"][0]
    assert b["level"] == level and b["color"] == sheet.COLORS[level]
    # Kiểm màu từ PNG thật ở một điểm trong khối, tránh đường nhãn.
    x, y = b["polygon"][0]
    assert Image.open(path).getpixel((round(x + 4), round(y - 4)))[:3] == b["color"]


def test_location_pack_roundtrip_and_hash():
    p = plan(box())
    packed = sheet.to_location_pack(p, "Hồng Việt", 1)
    assert packed["kind"] == "blockout" and packed["nguoi_duyet"] == "Hồng Việt"
    assert packed["ngay"] and packed["issues"] == []
    assert sheet.from_location_pack(packed) == p
    changed = deepcopy(p); changed["khoi"][0]["tam"][0] += 1
    assert sheet.to_location_pack(changed, "Hồng Việt", 2)["sha256"] != packed["sha256"]
    packed["plan"]["khoi"][0]["tam"][0] += 1
    with pytest.raises(ValueError, match="sha"):
        sheet.from_location_pack(packed)
    assert p["khoi"][0]["tam"] == [3, 3]


def test_red_plan_refused_and_yellow_preserved():
    with pytest.raises(ValueError, match="ĐỎ"):
        sheet.to_location_pack(plan(box("a"), box("b")), "Việt", 1)
    packed = sheet.to_location_pack(plan(box(nguon="kho")), "Việt", 1)
    assert packed["issues"][0]["muc"] == "vang"


@pytest.mark.parametrize("who, version", [("", 1), ("Việt", 0), ("Việt", True)])
def test_missing_approval_refused(who, version):
    with pytest.raises(ValueError):
        sheet.to_location_pack(plan(box()), who, version)


# ---- Lỗi 1: tên ô neo lưới chuẩn mục 2.3 (stage_grid), không neo góc sàn ----------------------------------------------
from core import blockout as bo
from core import stage_grid as sg


def _floor(p, w, d):
    p["san"]["kich_thuoc"] = [w, d]
    return p


@pytest.mark.parametrize("w, d", [(8, 6), (7, 5), (20, 20)])
def test_cell_names_follow_stage_grid(tmp_path, w, d):
    stage = sg.make_stage([0, 0, 0])
    result = sheet.render_top_view(_floor(plan(), w, d), [], tmp_path / "g.png")
    # Ô chứa (0,5; 0,5) phải là K11 như solver/Director gọi.
    assert sg.cell_name(stage, .5, .5) == "K11" and "K11" in result["cells"]
    by_name = {c["name"]: c for c in result["cell_boxes"]}
    assert by_name["K11"]["x0"] == 0 and by_name["K11"]["y0"] == 0
    # Góc Tây-Nam của sàn mang đúng tên ô chuẩn chứa điểm đó.
    sw = sg.cell_name(stage, -w / 2 + 1e-6, -d / 2 + 1e-6)
    assert sw in result["cells"]
    assert by_name[sw]["x0"] == -w / 2 and by_name[sw]["y0"] == -d / 2
    # Mọi ô (kể cả ô biên bị cắt) có tên = cell_name tại điểm giữa phần nằm trong sàn.
    for c in result["cell_boxes"]:
        assert c["name"] == sg.cell_name(stage, (c["x0"] + c["x1"]) / 2, (c["y0"] + c["y1"]) / 2)
        assert c["x0"] == -w / 2 or float(c["x0"]).is_integer()


def test_odd_floor_grid_on_whole_metres(tmp_path):
    result = sheet.render_top_view(_floor(plan(), 7, 5), [], tmp_path / "g.png")
    xs = {c["x0"] for c in result["cell_boxes"]}
    assert {-3.5, -3, 0, 3} <= xs and -2.5 not in xs
    assert len(result["cells"]) == 8 * 6
    assert {"G8", "N13"} <= set(result["cells"])     # ô biên cắt nửa ở hai góc Tây-Nam / Đông-Bắc


# ---- Lỗi 2: chỗ đứng dạng dict {"tam": [x,y]} được vẽ; dạng rác báo VÀNG, không bỏ im lặng -----------------------------
def test_standing_dict_and_list_drawn(tmp_path):
    result = sheet.render_top_view(plan(), [{"tam": [.5, .5]}, [0, 0]], tmp_path / "s.png")
    assert [s["at"] for s in result["standing"]] == [[.5, .5], [0, 0]]
    assert [s["label"] for s in result["standing"]] == ["Đứng 1", "Đứng 2"]


def test_standing_garbage_reported(tmp_path):
    result = sheet.render_top_view(plan(), ["rác", [0, 0]], tmp_path / "s.png")
    assert [s["label"] for s in result["standing"]] == ["Đứng 2"]
    assert any(i["path"] == "cho_dung[0]" and i["muc"] == "vang" and "không vẽ" in i["loi"] for i in result["issues"])


# ---- Lỗi 3: issues lúc duyệt là lịch sử; luật đổi → đọc được + cảnh báo, SHA vẫn nghiêm --------------------------------
def test_old_pack_readable_when_rules_change(monkeypatch):
    p = plan(box())
    packed = sheet.to_location_pack(p, "Việt", 1)
    original = bo.check_geometry

    def stricter(plan, cho_dung=None, vat_kich_ban=None):
        return original(plan, cho_dung, vat_kich_ban) + [bo._issue("vang", "khoi[0]", "luật mới", "new_rule")]
    monkeypatch.setattr(bo, "check_geometry", stricter)
    with pytest.warns(UserWarning, match="luật kiểm đã đổi"):
        got = sheet.from_location_pack(packed)
    assert got == p
    info = sheet.read_location_pack(packed)
    assert info["plan"] == p and info["can_duyet_lai"] is True and info["co_do"] is False
    assert "luật kiểm đã đổi" in info["canh_bao"] and info["issues_hien_tai"][-1]["code"] == "new_rule"
    assert info["issues_luc_duyet"] == []
    tampered = deepcopy(packed)
    tampered["plan"]["khoi"][0]["tam"][0] += 1
    with pytest.raises(ValueError, match="sha"):
        sheet.from_location_pack(tampered)


def test_old_pack_with_new_red_rule_reported_not_silent(monkeypatch):
    packed = sheet.to_location_pack(plan(box()), "Việt", 1)
    original = bo.check_geometry
    monkeypatch.setattr(bo, "check_geometry", lambda plan, cho_dung=None, vat_kich_ban=None:
                        original(plan, cho_dung, vat_kich_ban) + [bo._issue("do", "khoi[0]", "luật đỏ mới", "new_red")])
    info = sheet.read_location_pack(packed)
    assert info["can_duyet_lai"] is True and info["co_do"] is True and "ĐỎ" in info["canh_bao"]
    with pytest.warns(UserWarning, match="ĐỎ"):
        sheet.from_location_pack(packed)


def test_unchanged_rules_no_warning(recwarn):
    packed = sheet.to_location_pack(plan(box(nguon="kho")), "Việt", 1)
    info = sheet.read_location_pack(packed)
    assert info["can_duyet_lai"] is False and info["canh_bao"] == "" and info["co_do"] is False
    sheet.from_location_pack(packed)
    assert not [w for w in recwarn if "luật kiểm" in str(w.message)]


def test_tampered_issues_still_need_valid_list():
    packed = sheet.to_location_pack(plan(box()), "Việt", 1)
    packed["issues"] = "hỏng"
    with pytest.raises(ValueError, match="issues"):
        sheet.from_location_pack(packed)

# Đ13v2: hồi quy thuần dữ liệu, không gọi provider/API.
def _legacy_pack(p, ngay="2026-10-12T08:30:00+07:00"):
    import hashlib, json
    return {"kind": "blockout", "schema_version": 1, "phien_ban": 1,
            "nguoi_duyet": "Việt", "ngay": ngay, "issues": [], "plan": deepcopy(p),
            "sha256": hashlib.sha256(json.dumps(p, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()}


def test_d13_old_pillow_fallback_real_png(monkeypatch, tmp_path):
    default = sheet.ImageFont.load_default()
    def old_default():
        return default
    monkeypatch.setattr(sheet.ImageFont, "truetype", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(sheet.ImageFont, "load_default", old_default)
    assert sheet._font(10) is default
    sheet.render_top_view(plan(), [], tmp_path / "old.png")
    with Image.open(tmp_path / "old.png") as png:
        assert png.format == "PNG" and png.size == sheet.SIZE


def test_d13_numeric_geometry_and_semantics():
    p = plan(box()); q = deepcopy(p)
    q["khoi"][0]["tam"] = [3.0, 3.0]
    assert sheet._sha(p) == sheet._sha(q)
    for value in [True, "3", 3.0000000000000004, 2**100, 2**100 + 1]:
        q["khoi"][0]["tam"][0] = value
        assert sheet._sha(q) != sheet._sha(p)
    q = deepcopy(p); q["khoi"][0]["mo_ta_ngan"] += "!"
    assert sheet._sha(q) != sheet._sha(p)
    assert sheet._sha({"san": {"z": 2**100}}) != sheet._sha({"san": {"z": 2**100 + 1}})
    assert sheet._sha({"san": {"z": 2**100}}) == sheet._sha({"san": {"z": float(2**100)}})
    assert sheet._sha({"khoi": [{"id": "a"}, {"id": "b"}]}) != sheet._sha({"khoi": [{"id": "b"}, {"id": "a"}]})
    assert sheet._sha({"khoi": [{"vat_kho": 3}]}) != sheet._sha({"khoi": [{"vat_kho": 3.0}]})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_d13_hash_nonfinite_rejected(value):
    with pytest.raises(ValueError):
        sheet._sha({"san": {"z": value}})


def test_d13_old_raw_hash_strict_and_immutable():
    packed = _legacy_pack(plan(box())); original = deepcopy(packed)
    assert sheet.from_location_pack(packed) == packed["plan"]
    assert packed == original
    packed["plan"]["khoi"][0]["tam"][0] = 3.0
    with pytest.raises(ValueError, match="sha"):
        sheet.read_location_pack(packed)


@pytest.mark.parametrize("ngay", ["2026-10-12", "2026-10-12T08:30:00"])
def test_d13_naive_legacy_warns_new_refuses(ngay):
    packed = _legacy_pack(plan(box()), ngay); original = deepcopy(packed)
    info = sheet.read_location_pack(packed)
    assert info["can_duyet_lai"] and "múi giờ" in info["canh_bao"] and not info["co_do"]
    with pytest.warns(UserWarning, match="múi giờ"):
        assert sheet.from_location_pack(packed) == packed["plan"]
    assert packed == original and info["issues_luc_duyet"] == []
    new = sheet.to_location_pack(plan(box()), "Việt", 1)
    assert new["schema_version"] == 2
    new["ngay"] = ngay
    with pytest.raises(ValueError, match="múi giờ"):
        sheet.read_location_pack(new)


def test_d13_new_hash_never_legacy_fallback():
    packed = sheet.to_location_pack(plan(box()), "Việt", 1)
    packed["sha256"] = _legacy_pack(packed["plan"])["sha256"]
    with pytest.raises(ValueError, match="sha"):
        sheet.read_location_pack(packed)
    packed = sheet.to_location_pack(plan(box()), "Việt", 1)
    packed["schema_version"] = True
    with pytest.raises(ValueError, match="schema"):
        sheet.read_location_pack(packed)


def test_d13_all_geometry_numeric_fields_and_serialized_roundtrip():
    import json
    p = plan(box())
    p["loi_mo"] = [{"tam": [0, 0], "kich_thuoc": [1, 1], "huong": 0}]
    p["khoi"][0]["kich_thuoc_chuan"] = [1, 1, 2]
    p["khoi"][0]["z"] = 0
    def floats(item):
        if type(item) is int:
            return float(item)
        if isinstance(item, list):
            return [floats(v) for v in item]
        if isinstance(item, dict):
            return {k: floats(v) for k, v in item.items()}
        return item
    q = floats(p)
    assert sheet._sha(p) == sheet._sha(q)
    pack = sheet.to_location_pack(p, "Việt", 1)
    pack["plan"] = q
    assert sheet.from_location_pack(json.loads(json.dumps(pack))) == q
    pack["ngay"] = "2026-10-12T08:30:00+07:00"
    assert not sheet.read_location_pack(pack)["can_duyet_lai"]
    q["khoi"][0]["tam"][0] = "3"
    with pytest.raises(ValueError, match="sha"):
        sheet.read_location_pack(pack)


def test_d13_legacy_naive_and_changed_red_rules_preserve_history(monkeypatch):
    pack = _legacy_pack(plan(box()), "2026-10-12")
    original = deepcopy(pack)
    monkeypatch.setattr(bo, "check_geometry", lambda *a, **k: [bo._issue("do", "san", "luật mới đỏ", "new_red")])
    info = sheet.read_location_pack(pack)
    assert info["co_do"] and info["can_duyet_lai"]
    assert "múi giờ" in info["canh_bao"] and "luật kiểm đã đổi" in info["canh_bao"] and "ĐỎ" in info["canh_bao"]
    assert info["issues_luc_duyet"] == [] and pack == original
    info["plan"]["san"]["z"] = 100
    assert pack == original


def test_d13_nested_metadata_not_geometry():
    p = plan(box())
    p["khoi"][0]["metadata"] = {"z": 3, "tam": [3, 3], "huong": 3}
    for field in ("z", "tam", "huong"):
        q = deepcopy(p)
        q["khoi"][0]["metadata"][field] = [3.0, 3.0] if field == "tam" else 3.0
        assert sheet._sha(p) != sheet._sha(q)
        pack = sheet.to_location_pack(p, "Việt", 1)
        pack["plan"] = q
        with pytest.raises(ValueError, match="sha"):
            sheet.read_location_pack(pack)


def test_d13_bitmap_font_fails_clearly_before_png(monkeypatch, tmp_path):
    bitmap = sheet.ImageFont.load_default_imagefont()
    monkeypatch.setattr(sheet.ImageFont, "truetype", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(sheet.ImageFont, "load_default", lambda: bitmap)
    output = tmp_path / "missing_unicode.png"
    with pytest.raises(ValueError, match="font Unicode"):
        sheet.render_top_view(plan(), [], output)
    assert not output.exists()
