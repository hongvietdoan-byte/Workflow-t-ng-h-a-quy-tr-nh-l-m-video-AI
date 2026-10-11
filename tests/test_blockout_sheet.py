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
