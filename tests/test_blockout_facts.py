from core import blockout, stage_facts
from tests.test_blockout import plan, box


def test_generic_block_fact_keeps_real_object_and_library_id():
    props = blockout.to_props(plan(box(xy=(0, 0), mo_ta_ngan="tường gỗ", vat_kho=123)))
    data = {"stage_camera": {"location": [0, -6, 2], "look_at": [0, 0, 1], "lens": 25, "props": props}}
    facts = stage_facts.derive(data)["facts"]
    fact = next(f for f in facts if f["kind"] == "stand_in")
    assert "tường gỗ" in fact["prompt"] and "123" in fact["prompt"]
    assert "weathered stone" not in fact["prompt"]
    assert not next(f for f in stage_facts.derive(data, render=False)["facts"] if f["kind"] == "stand_in")["prompt"]


def test_block_with_library_id_has_no_missing_library_note(monkeypatch):
    """Khối có vat_kho tìm thấy trong Kho: không ghi chú 'không có vật Kho loại block' (khóa vật Kho là mã, không phải 'block')."""
    props = blockout.to_props(plan(box(xy=(0, 0), mo_ta_ngan="tường gỗ", vat_kho=123)))
    data = {"stage_camera": {"location": [0, -6, 2], "look_at": [0, 0, 1], "lens": 25, "props": props}}
    monkeypatch.setattr(stage_facts, "library_objects", lambda conn, pid, ps: {"123": {"name": "Tường gỗ", "desc_en": ""}})
    assert not [n for n in stage_facts.for_shot(None, 1, data)["notes"] if "block" in n]
    monkeypatch.setattr(stage_facts, "library_objects", lambda conn, pid, ps: {})
    assert [n for n in stage_facts.for_shot(None, 1, data)["notes"] if "123" in n]
