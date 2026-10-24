"""CX24-G1: tiến độ code tách cổng nghiệm thu, chỉ dùng kế hoạch giả."""
import os
from unittest import mock

import pytest


@pytest.fixture
def progress():
    with mock.patch.object(os, "environ", {}):
        from devsys import plan_progress
        yield plan_progress


def task(tid, status="✅", gate="", title="Việc thử", weight=1):
    return f"- [ ] {tid} · {title} · nặng:{weight} · {status} · abc1234 · ghi chú" + (
        f" · cổng: {gate}" if gate else "")


def test_old_task_defaults_gate_to_pending_without_changing_code(progress):
    plan = progress.parse("### M1 — Thử\n" + task("M1.1"))
    item = plan["waves"][0]["tasks"][0]
    assert item["status"] == "✅"
    assert item["commit"] == "abc1234"
    assert item["gate_status"] == "⬜"
    result = progress.summary(plan)
    assert result["total"] == result["total_code"] == 100.0
    assert result["total_gate"] == 0.0


def test_gate_percent_uses_weights_but_never_half_credit(progress):
    text = "### M1 — Thử\n" + "\n".join([
        task("M1.1", gate="✅ chạy thật logs/run.jsonl", weight=1),
        task("M1.2", "🔄", "⬜ chưa chạy", weight=2),
        task("M1.3", "✖", "⬜ bỏ", weight=3),
    ])
    result = progress.summary(progress.parse(text))
    assert result["total"] == 66.7
    assert result["total_gate"] == 33.3
    assert result["waves"][0]["pct_gate"] == 33.3
    assert result["waves"][0]["gate_done"] == 1


@pytest.mark.parametrize("gate", ["✅", "✅ chỉ có unit test", "✅ chưa kiểm thật"])
def test_gate_without_real_evidence_is_not_counted(progress, gate):
    result = progress.summary(progress.parse("### M1 — Thử\n" + task("M1.1", gate=gate)))
    assert result["total_gate"] == 0.0
    assert result["gate_warnings"]


@pytest.mark.parametrize("gate, accepted", [
    ("✅ commit abc1234 chạy thật", False),
    ("✅ ui_step #34 N5 lúc 09:46", True),
    ("✅ ảnh docs/images/demo.png dùng thật #34", True),
])
def test_dashboard_gate_requires_screenshot_or_ui_step(progress, gate, accepted):
    plan = progress.parse("### M4 — Thử\n" + task("M4.8", gate=gate, title="Bàn đạo diễn"))
    result = progress.summary(plan)
    assert result["total_gate"] == (100.0 if accepted else 0.0)
    assert bool(result["gate_warnings"]) is not accepted


def test_next_skips_dependency_hold_and_pause(progress):
    text = "### M1 — Thử\n" + "\n".join([
        task("M1.1", "⬜") + " · CHỜ PHỤ THUỘC / BẰNG CHỨNG",
        task("M1.2", "⏸"),
        task("M1.3", "⬜"),
    ])
    assert progress.summary(progress.parse(text))["next"]["id"] == "M1.3"


def test_table_and_cli_report_two_columns_and_gate_warning(progress, tmp_path, capsys):
    from tools import plan_progress as cli
    path = tmp_path / "plan.md"
    path.write_text("### M4 — Thử\n" + task("M4.8", gate="✅ commit abc1234"), encoding="utf-8")
    assert cli.main(["--file", str(path)]) == 0
    printed = capsys.readouterr().out
    assert "% code" in printed and "% cổng" in printed
    assert "M4.8" in printed and "ui_step" in printed


def test_gate_field_does_not_consume_following_note(progress):
    item = progress.parse("### M1 — Thử\n" + task(
        "M1.1", gate="✅ chạy thật logs/run.jsonl") + " · ghi chú sau")["waves"][0]["tasks"][0]
    assert item["gate_evidence"] == "chạy thật logs/run.jsonl"
    assert "ghi chú sau" in item["note"]


def test_declared_gate_cannot_pass_before_code_and_duplicate_is_warning(progress):
    text = "### M1 — Thử\n" + "\n".join([
        task("M1.1", "🔄", "✅ commit abc1234 chạy thật"),
        task("M1.2", gate="✅ chạy thật logs/run.jsonl") + " · cổng: ⬜ mâu thuẫn",
    ])
    result = progress.summary(progress.parse(text))
    assert result["total_gate"] == 0.0
    assert len(result["gate_warnings"]) == 2


def test_write_table_preserves_task_status_and_evidence(progress, tmp_path):
    line = task("M1.1", gate="✅ chạy thật logs/run.jsonl")
    path = tmp_path / "plan.md"
    path.write_text("<!-- tien-do -->\ncũ\n<!-- /tien-do -->\n### M1 — Thử\n" + line + "\n", encoding="utf-8")
    assert progress.write_table(str(path))
    assert line in path.read_text(encoding="utf-8")
    assert not progress.write_table(str(path))


@pytest.mark.parametrize("evidence", [
    "chạy thật", "máy chính", "sổ chi", "không có ui_step",
    "ảnh mockup/demo.png chưa QA", "ảnh docs/images/qa.png chưa dùng thật",
])
def test_gate_rejects_unspecific_negated_and_mockup_evidence(progress, evidence):
    result = progress.summary(progress.parse("### M1 — Thử\n" + task("M1.1", gate="✅ " + evidence)))
    assert result["total_gate"] == 0.0
    assert result["gate_warnings"]


def test_devsys_screen_also_requires_real_ui_evidence(progress):
    result = progress.summary(progress.parse("### M0 — Thử\n" + task(
        "M0.8", gate="✅ commit abc1234 chạy thật", title="AI Dev System: sơ đồ tiến độ")))
    assert result["total_gate"] == 0.0
    assert result["gate_warnings"]


def test_map_model_and_svg_distinguish_code_done_from_real_gate(progress):
    from devsys import plan_map
    text = "### M1 — Thử\n" + "\n".join([
        task("M1.1"), task("M1.2", gate="✅ chạy thật logs/run.jsonl"),
    ])
    model = plan_map.model(progress.parse(text), [], {"M1.1": ["NEN"], "M1.2": ["NEN"]})
    assert model["total"] == 100.0 and model["total_gate"] == 50.0
    for svg in (plan_map.roadmap_svg(model, "Thử"), plan_map.stages_svg(model, "Thử")):
        assert plan_map.CODE_DONE_COLOR in svg
        assert plan_map.STATUS_COLOR["✅"] in svg
        assert "code" in svg and "cổng" in svg


def test_both_pages_render_code_and_gate_with_fixture_only(tmp_path):
    from streamlit.testing.v1 import AppTest
    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "devsys", "app.py")
    script = "APP_PATH = " + repr(app_path) + "\n" + '''
import ast
import os
from pathlib import Path
from html import escape as _html_escape
import streamlit as st
from unittest import mock
from devsys import collect, answers, plan_progress, plan_map
ROOT = str(Path(APP_PATH).parent.parent)
# Thực thi đúng hàm trang từ source; bỏ startup/auth/collect toàn repo, chỉ cấp kế hoạch giả.
names = {"page_plan", "page_plan_map", "kpi", "escape", "_pct_text", "_short", "_wave_name", "_rel"}
tree = ast.parse(Path(APP_PATH).read_text(encoding="utf-8"))
tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
exec(compile(tree, APP_PATH, "exec"), globals())
_all_plans_board = mock.Mock()
_wave_body = mock.Mock()
_task_row = mock.Mock()
_answer_box = mock.Mock()
plan = plan_progress.parse("### M1 — Thử\\n- [ ] M1.1 · Việc giả · nặng:1 · ✅ · cổng: ⬜ chưa đo\\n")
model = plan_map.model(plan, [], {"M1.1": ["NEN"]})
with mock.patch.object(plan_progress, "load", return_value=plan), \\
     mock.patch.object(plan_progress, "spend", return_value=None), mock.patch.object(answers, "load", return_value={}):
    page_plan()
with mock.patch.object(plan_map, "build", return_value=(model, plan_map.roadmap_svg(model, "Fixture"), plan_map.stages_svg(model, "Fixture"))):
    page_plan_map()
'''
    with mock.patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
                                          "TEMP": str(tmp_path), "TMP": str(tmp_path),
                                          "PIPELINE_DB": str(tmp_path / "absent.sqlite")}):
        at = AppTest.from_string(script, default_timeout=120).run()
    assert not at.exception
    rendered = " ".join(x.value for x in at.markdown)
    assert "Tiến độ code" in rendered
    assert "Cổng nghiệm thu" in rendered
    assert "100" in rendered and "0" in rendered
    assert [title.value for title in at.title] == ["📋 Kế hoạch đang chạy", "🗺 Sơ đồ tiến độ"]
