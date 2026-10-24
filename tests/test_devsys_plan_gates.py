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
