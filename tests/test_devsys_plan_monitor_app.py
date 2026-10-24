"""AppTest cho ba trang giám sát, với mọi nguồn/biến môi trường được thay bằng fixture."""
import os
from unittest import mock


def test_monitor_panel_renders_on_all_three_devsys_pages(monkeypatch, tmp_path):
    fake_env = {
        "PATH": r"C:\fixture\bin", "PATHEXT": ".COM;.EXE;.BAT;.CMD", "SYSTEMROOT": r"C:\fixture\windows",
        "WINDIR": r"C:\fixture\windows", "TEMP": r"C:\fixture\temp", "TMP": r"C:\fixture\temp",
        "USERPROFILE": r"C:\fixture\user", "APPDATA": r"C:\fixture\user\appdata",
        "LOCALAPPDATA": r"C:\fixture\user\local", "PROGRAMDATA": r"C:\fixture\programdata",
        "HOME": r"C:\fixture\user", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
    }
    with mock.patch.object(os, "environ", fake_env):
        from streamlit.testing.v1 import AppTest
        from devsys import (admin_auth, answers, collect, lao_dai_channel, plan_map, plan_monitor,
                           plan_progress, plans, pipeline_maps, scorer, scores, stages)

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plan = tmp_path / "plan.md"
        plan.write_text("\n".join([
            "<!-- tien-do -->", "<!-- /tien-do -->", "", "### M4 — Fixture",
            "- [ ] M4.1 · Task giả · nặng:1 · ⬜", "", "### M9 — Giám sát",
            "- [ ] M9.0 · Quy tắc · nặng:1 · ✅", "", "## 6. Nhật ký", "",
        ]), encoding="utf-8")
        snap = {"head": {}, "generated_at": "fixture", "collect_s": 0, "working": [],
                "latest_run": None, "tests_stale": None}
        monkeypatch.setattr(collect, "status_key", lambda _root: "fixture-key")
        monkeypatch.setattr(collect, "load_areas", lambda *_a, **_k: {"areas": []})
        monkeypatch.setattr(collect, "collect", lambda *_a, **_k: snap)
        monkeypatch.setattr(collect, "area_health", lambda *_a, **_k: {})
        monkeypatch.setattr(collect, "tests_running", lambda *_a, **_k: None)
        monkeypatch.setattr(scorer, "fingerprint", lambda *_a, **_k: "fixture-fingerprint")
        monkeypatch.setattr(scores, "load_all", lambda *_a, **_k: ([], []))
        monkeypatch.setattr(scores, "rubric_hash", lambda *_a, **_k: "fixture-rubric")
        monkeypatch.setattr(plans, "inventory", lambda *_a, **_k: {"error": None, "items": []})
        monkeypatch.setattr(plan_progress, "main_plan_file", lambda *_a, **_k: str(plan))
        monkeypatch.setattr(plan_progress, "spend", lambda *_a, **_k: None)
        monkeypatch.setattr(stages, "load_stages", lambda: {"dot_hien_tai": "M4"})
        monkeypatch.setattr(answers, "load", lambda: {})
        monkeypatch.setattr(answers, "default_path", lambda: str(tmp_path / "answers.json"))
        monkeypatch.setattr(admin_auth, "take_link", lambda: None)
        monkeypatch.setattr(lao_dai_channel, "render", lambda *_a, **_k: None)
        monkeypatch.setattr(plan_monitor, "load_history", lambda _root: ([], []))
        monkeypatch.setattr(plan_monitor, "prepare", lambda _root: {
            "bundle": {"input_hash": "fixture-hash"}, "estimate": {"input_tokens": 12, "usd_api": 0.0}
        })
        monkeypatch.setattr(plan_monitor, "check_auto_triggers", lambda *_a, **_k: {"state": "disabled", "spawned": []})
        fake_plan_model = {"unmapped": [], "stale": [], "unknown_stage": [], "total": 0.0, "total_gate": 0.0,
                           "gate_warnings": [], "current": "M4", "next": {"id": "M4.1"},
                           "waves": [{"id": "M4", "name": "M4 Fixture", "pct": 0.0, "pct_gate": 0.0,
                                      "tasks": [{"id": "M4.1", "status": "🔄", "commit": "", "title": "Fixture",
                                                 "gate_status": "⬜"}]}], "rows": []}
        monkeypatch.setattr(plan_map, "build", lambda: (fake_plan_model, "<svg/>", "<svg/>"))
        monkeypatch.setattr(plan_map, "load_map", lambda: {"M4.1": ["L1"]})
        monkeypatch.setattr(pipeline_maps, "build_model", lambda: {"warnings": [], "moc_date": "fixture"})
        monkeypatch.setattr(pipeline_maps, "record_history", lambda *_a, **_k: False)
        monkeypatch.setattr(pipeline_maps, "db_path", lambda: str(tmp_path / "no-db.sqlite"))
        monkeypatch.setattr(pipeline_maps, "projects", lambda *_a, **_k: [])
        monkeypatch.setattr(pipeline_maps, "svg_dashboard", lambda *_a, **_k: "<svg/>")
        monkeypatch.setattr(pipeline_maps, "svg_khau", lambda *_a, **_k: "<svg/>")
        monkeypatch.setattr(pipeline_maps, "svg_truong", lambda *_a, **_k: "<svg/>")
        monkeypatch.setattr(pipeline_maps, "load", lambda: {"dashboard": {"cells": []}, "truong": {"nodes": []}})
        monkeypatch.setattr(pipeline_maps, "changes", lambda: [])
        monkeypatch.setattr(pipeline_maps, "vs_moc", lambda *_a, **_k: [])
        monkeypatch.setattr(pipeline_maps, "all_items", lambda *_a, **_k: [])

        app = AppTest.from_file(os.path.join(root, "devsys", "app.py"), default_timeout=30)
        app.run()
        has_initial_error = bool(app.exception)
        assert not has_initial_error, "AppTest lỗi khi dựng trang fixture"
        assert any("Giám sát kế hoạch V3.1" in row.value for row in app.subheader)
        for page, title in (
            ("📋 Kế hoạch đang chạy", "📋 Kế hoạch đang chạy"),
            ("🗺 Sơ đồ tiến độ", "🗺 Sơ đồ tiến độ"),
            ("🧭 Sơ đồ dây chuyền", "🧭 Sơ đồ dây chuyền"),
        ):
            app.radio[0].set_value(page).run()
            has_page_error = bool(app.exception)
            assert not has_page_error, f"AppTest lỗi khi dựng trang {page}"
            assert any(row.value == title for row in app.title)
            assert app.info, f"Trang {page} không hiển thị trạng thái rỗng cho dữ liệu fixture"

