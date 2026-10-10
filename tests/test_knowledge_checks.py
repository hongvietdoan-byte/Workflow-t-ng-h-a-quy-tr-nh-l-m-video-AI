"""K0b nhánh A — hợp đồng bộ kỹ năng kiểm `knowledge/checks/<ID>.md` (kế hoạch kiểm soát 10/10 mục 4 "Bộ kỹ năng kiểm").

Tệp kỹ năng phải KHỚP `devsys/error_types.json`: đủ 24 loại đúng id (R1 thêm K1a), mỗi tệp có 4 mục bắt buộc, mọi enum Claude khai của loại xuất
hiện trong tệp, mọi `where` (file:tên) của code đo / Claude khai được nhắc, và mọi cờ của cách kiểm phụ thuộc cờ được ghi tên (cờ TẮT
thì không tính là có — thẩm định 3)."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKS = os.path.join(ROOT, "knowledge", "checks")
REQUIRED = ("## Câu hỏi khai được", "## Code kết luận thế nào", "## Đo bằng code hiện có", "## Ca lỗi thật")


def _types():
    with open(os.path.join(ROOT, "devsys", "error_types.json"), encoding="utf-8") as fh:
        return json.load(fh)["types"]


def test_l9_enum_covers_horizon_observations():
    from core import stage_facts
    item = next(t for t in _types() if t["id"] == "L9")
    declared = set(item["claude_khai"][0]["enum"])
    assert declared >= set(stage_facts.FACTS["pitch_horizon"]["observe"]["options"])


def test_l8_enum_covers_all_framing():
    from core import stage_grid
    item = next(t for t in _types() if t["id"] == "L8")
    assert set(item["claude_khai"][0]["enum"]) >= set(stage_grid.FRAMING)


def test_l12_enum_covers_byd_times():
    from core import shot_intent
    item = next(t for t in _types() if t["id"] == "L12")
    labels = {"dawn": "binh_minh", "day": "ngay", "dusk": "hoang_hon", "night": "dem"}
    assert set(shot_intent.THOI_GIAN) == set(labels)
    assert set(item["claude_khai"][0]["enum"]) >= set(labels.values())


def _read(tid):
    path = os.path.join(CHECKS, f"{tid}.md")
    assert os.path.isfile(path), f"thiếu tệp kỹ năng kiểm {path}"
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _flags(item):
    co = item.get("co")
    return [co] if isinstance(co, str) else list(co or [])


def test_one_file_per_type_and_no_extra():
    ids = [t["id"] for t in _types()]
    assert len(ids) == 24
    for tid in ids:
        _read(tid)
    extra = {f[:-3] for f in os.listdir(CHECKS) if f.endswith(".md") and f != "README.md"} - set(ids)
    assert not extra, f"tệp kỹ năng không có trong error_types.json: {sorted(extra)}"
    assert os.path.isfile(os.path.join(CHECKS, "README.md"))


def test_title_sections_enums_where_flags():
    for t in _types():
        text = _read(t["id"])
        first = text.splitlines()[0]
        assert first == f"# {t['id']} — {t['ten']}", (t["id"], first)
        for head in REQUIRED:
            assert re.search(rf"^{re.escape(head)}\b", text, re.M), f"{t['id']}: thiếu mục '{head}'"
        for k in t["claude_khai"]:
            for e in k["enum"]:
                assert e in text, f"{t['id']}: enum '{e}' của claude_khai không có trong tệp"
        for item in t["code_do"] + t["claude_khai"]:
            if item.get("where"):
                assert item["where"] in text, f"{t['id']}: thiếu nơi đo '{item['where']}'"
            for flag in _flags(item):
                assert f"`{flag}`" in text, f"{t['id']}: cách kiểm phụ thuộc cờ '{flag}' mà tệp không ghi tên cờ"
            if item.get("trang_thai") == "xay" and item.get("dot"):
                assert item["dot"] in text, f"{t['id']}: cách kiểm 'xay' đợt {item['dot']} không được ghi 'chưa có (đợt …)'"


def test_l4_lists_the_current_pose_enum():
    """Thẩm định 4 (C): L4.md phải liệt kê ĐÚNG `core/shot_intent.TU_THE` hiện tại (có nga_ngua, nam — solver đã hỗ trợ, số hình học còn tạm)."""
    from core import shot_intent
    text = _read("L4")
    for code in shot_intent.TU_THE:
        assert f"`{code}`" in text, f"L4.md thiếu tư thế `{code}` của TU_THE"
    # Đợt 2: người nộm Blender nằm cùng bao hình solver → prompt 29 đã mở; L4 phải nói đã mở + số còn tạm + còn chờ render thật
    assert "prompt 29 đã mở" in text
    assert "render thật" in text
    assert "chưa đo" in text
