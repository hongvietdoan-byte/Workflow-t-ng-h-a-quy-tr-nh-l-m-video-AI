"""CX23-DOI-SOAT: kiểm phân loại và đối chiếu bản đồ kế hoạch bằng dữ liệu giả."""
from __future__ import annotations

import pytest

from devsys import doi_soat, pipeline_maps as PM


def _item(item_id, color, *, why=(), tasks=None, khau=(), errors=()):
    return {"id": item_id, "label": item_id, "color": color, "why": list(why), "tasks": dict(tasks or {}),
            "khau": list(khau), "open_errors": list(errors), "inputs": {"plan": dict(tasks or {})}}


def test_each_classification_and_plan_proposal_are_explicit():
    red_done = doi_soat.classify_row(_item("L1", "do", why=["thiếu kiểm"], tasks={"M1": "✅"}))
    assert {"THIEU", "LECH"} <= set(red_done)

    yellow_no_task = doi_soat.classify_row(_item("c1", "vang", why=["lỏng: chỉ người"], khau=["L4"]))
    assert {"LONG", "KHONG_VIEC"} <= set(yellow_no_task)

    green_unfinished = doi_soat.classify_row(_item("c2", "xanh", tasks={"M2": "⬜"}))
    assert "LECH" in green_unfinished
    cancelled = doi_soat.classify_row(_item("c3", "do", why=["thiếu kiểm"], tasks={"M3": "✖"}))
    assert "LECH" not in cancelled

    open_error_no_plan = doi_soat.classify_row(_item("L14", "do", why=["kiểm thiếu"], errors=[{"id": "P31-G1"}]))
    assert {"LOI", "THIEU", "KHONG_VIEC"} <= set(open_error_no_plan)


def test_reconciliation_keeps_error_ids_task_status_and_stage_summary():
    model = {
        "khau": {"rows": [_item("L1", "do", why=["thiếu kiểm"], tasks={"M1": "✅"}, khau=["L1"])]},
        "dashboard": {"cells": [_item("c1", "vang", why=["lỏng"], tasks={"M2": "✅"}, khau=["L1"])]},
        "truong": {"nodes": [_item("n1", "do", why=["thiếu hàm"], khau=["L2"])]},
        "warnings": [],
    }
    errors = [{"id": "P31-G1", "title": "lỗi còn mở", "status": "OPEN", "stage": "L1", "plan_task": "M1",
               "source_document": "docs/a.md", "evidence": ["core/a.py:10"]}]
    result = doi_soat.build_reconciliation(model, errors, plan_status={"M1": "✅", "M2": "✅"})

    stage = next(r for r in result["rows"] if r["id"] == "L1")
    assert stage["open_error_ids"] == ["P31-G1"]
    assert stage["tasks"] == [{"id": "M1", "status": "✅"}]
    assert {"LOI", "THIEU", "LECH"} <= set(stage["types"])
    assert stage["proposal"]["title"] and stage["proposal"]["stage"] == "L1"
    assert stage["proposal"]["reason"] and stage["proposal"]["evidence"]
    # Cả ô vàng c1 (L1) và nút đỏ n1 (L2) cũng được tính vào tổng số khâu bị ảnh hưởng.
    assert result["summary"] == {"LOI": 1, "LONG": 1, "THIEU": 2, "LECH": 1, "KHONG_VIEC": 1}

    no_work = next(r for r in result["rows"] if r["id"] == "n1")
    assert "KHONG_VIEC" in no_work["types"] and no_work["proposal"] is not None


def test_open_error_with_completed_linked_plan_is_lech_not_unassigned():
    model = {"khau": {"rows": [_item("L3", "vang", why=["chỉ người"], tasks={"M3": "✅"}, khau=["L3"])]},
             "dashboard": {"cells": []}, "truong": {"nodes": []}, "warnings": []}
    errors = [{"id": "P31-G2", "title": "còn lỗi", "status": "OPEN", "stage": "L3", "plan_task": "M3"}]
    result = doi_soat.build_reconciliation(model, errors, plan_status={"M3": "✅"})
    row = result["rows"][0]
    assert {"LOI", "LONG", "LECH"} <= set(row["types"])
    assert "KHONG_VIEC" not in row["types"]
    assert row["open_errors"][0]["plan_task_status"] == "✅"


def test_recommendation_continues_an_active_task_instead_of_duplicating_it():
    model = {"khau": {"rows": [_item("L3", "do", why=["thiếu kiểm"], tasks={"M4.7": "🔄"}, khau=["L3"])]},
             "dashboard": {"cells": []}, "truong": {"nodes": []}, "warnings": []}
    result = doi_soat.build_reconciliation(model, [], plan_status={"M4.7": "🔄"})
    assert result["rows"][0]["proposal"]["title"].startswith("Tiếp tục M4.7")


def test_loose_expires_when_linked_plan_item_is_done():
    cell = {"id": "loose", "moc": "A", "khau": ["L4"], "plan": ["M4"], "flags": [], "loose": True,
            "loose_until_plan": ["M4"], "evidence": []}
    still_open = PM._cell_color(cell, ".", lambda _: "off", {"M4": "⬜"}, {}, set())
    completed = PM._cell_color(cell, ".", lambda _: "off", {"M4": "✅"}, {}, set())
    cancelled = PM._cell_color(cell, ".", lambda _: "off", {"M4": "✖"}, {}, set())
    assert still_open["color"] == "vang"
    assert completed["color"] == "xanh"
    assert cancelled["color"] == "vang"


def test_real_map_expired_loose_and_verified_evidence_are_corrected():
    model = PM.build_model()
    colors = {r["id"]: r["color"] for r in model["dashboard"]["cells"] + model["truong"]["nodes"]}
    for item_id in ("kb.fixflags", "kb.characters", "sb.pregate", "bg.popup", "t.regex"):
        assert colors[item_id] != "vang", item_id
    # BYĐ chưa hiển thị trên Dashboard là khoảng trống thật và phải còn đỏ.
    assert colors["kb.byd"] == "do"
    # t.forms: BYĐ dạng nối thật qua kho_profile → character_forms.names_match (bằng chứng phải trỏ chỗ ĐỌC ý đồ, không chỉ hàm tồn tại).
    doc = PM.load()
    nodes = {n["id"]: n for n in doc["truong"]["nodes"]}
    assert all(PM._evidence_ok(PM.ROOT, e, {}) for e in nodes["t.forms"]["evidence"])
    # t.plate: landmark_facts (số đo máy) CHƯA so với khung.moc_nen (ý đồ) — lỗ thật, phải còn đỏ (phiên chính 23/10).
    assert colors["t.plate"] == "do"


def test_live_mismatches_are_explained_and_never_auto_edit_the_plan():
    model = PM.build_model()
    from devsys import errors
    report = doi_soat.build_reconciliation(model, errors.load()["items"], plan_status=PM.plan_statuses())
    for row in report["rows"]:
        if row["types"]:
            assert row["proposal"] and row["proposal"]["reason"] and row["proposal"]["evidence"], row["id"]
    assert report["plan_changed"] is False


def test_markdown_export_is_deterministic_and_writes_only_requested_path(tmp_path):
    model = {"khau": {"rows": [_item("L14", "do", why=["thiếu kiểm"], khau=["L14"])]},
             "dashboard": {"cells": []}, "truong": {"nodes": []}, "warnings": []}
    result = doi_soat.build_reconciliation(model, [], plan_status={})
    text = doi_soat.render_markdown(result, generated_on="2026-10-23")
    output = tmp_path / "DOI_SOAT_KHAU_2026-10-23.md"
    doi_soat.write_markdown(output, text)
    assert output.read_text(encoding="utf-8").startswith("# Đối soát khâu")
    assert "L14" in output.read_text(encoding="utf-8")
    assert list(tmp_path.iterdir()) == [output]


def test_markdown_export_never_overwrites_an_existing_file(tmp_path):
    output = tmp_path / "DOI_SOAT_KHAU_2026-10-23.md"
    output.write_text("bản đã có", encoding="utf-8")

    with pytest.raises(FileExistsError):
        doi_soat.write_markdown(output, "bản mới")

    assert output.read_text(encoding="utf-8") == "bản đã có"


def test_markdown_renders_stage_labels_as_readable_text():
    model = {"khau": {"rows": [{"id": "L1", "label": ["Ý tưởng", "Kịch bản"], "color": "xanh",
                                  "why": [], "khau": ["L1"], "tasks": {"M1": "✅"}}]},
             "dashboard": {"cells": []}, "truong": {"nodes": []}, "warnings": []}
    report = doi_soat.build_reconciliation(model, [], plan_status={"M1": "✅"})

    text = doi_soat.render_markdown(report, generated_on="2026-10-23")

    assert "### L1 — Ý tưởng · Kịch bản" in text
    assert "['Ý tưởng'" not in text
