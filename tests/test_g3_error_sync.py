"""G3: đối soát trạng thái chỉ đọc; ✅ code không phải cổng chạy thật."""
import os
import sys
import socket
import subprocess
from contextlib import ExitStack
from unittest import mock
import pytest

with mock.patch.object(os, "environ", {}):
    from devsys import errors, plan_progress


@pytest.fixture(autouse=True)
def sandbox(tmp_path):
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "PYTHONUTF8": "1"}))
        stack.enter_context(mock.patch.object(socket.socket, "connect", side_effect=AssertionError("no network")))
        stack.enter_context(mock.patch.object(subprocess, "Popen", side_effect=AssertionError("no native process")))
        yield


def item(**kw):
    row = {"id": "P31-G1", "status": "OPEN", "plan_task": "M2.4", "fix_commit": [], "tests": [], "status_reason": ""}
    row.update(kw)
    return row


def plan(status="✅", gate="⬜"):
    return plan_progress.parse(f"- [ ] M2.4 · sửa code · nặng:1 · {status} · cổng: {gate} chưa chạy thật")


@pytest.mark.parametrize("status", ["OPEN", "IN_PROGRESS", "REOPENED"])
def test_done_code_reports_every_open_state_without_mutation(status):
    row = item(status=status)
    before = dict(row)
    found = errors.sync_findings({"items": [row]}, plan())
    assert found[0]["code"] == "PLAN_DONE_ERROR_OPEN"
    assert found[0]["suggested_status"] is None
    assert "commit" in found[0]["reason"] and "test" in found[0]["reason"]
    assert row == before


def test_done_code_can_suggest_only_checked_code_evidence_never_verified():
    row = item(fix_commit=["123abcd"], tests=["tests/test_fixture.py::test_ok"])
    found = errors.sync_findings({"items": [row]}, plan(), verify=lambda _: [])
    assert found[0]["suggested_status"] == "FIXED_UNVERIFIED"
    assert errors.sync_findings({"items": [row]}, plan(), verify=lambda _: ["commit không tồn tại"])[0]["suggested_status"] is None


@pytest.mark.parametrize("reason", ["M3.4 shadow chỉ phát hiện", "Còn mở phần allocator", "Chưa nối vào đường gen"])
def test_partial_shadow_code_is_not_a_completed_fix(reason):
    found = errors.sync_findings({"items": [item(fix_commit=["123abcd"], tests=["tests/test_x.py"], status_reason=reason)]},
                                 plan(), verify=lambda _: [])
    assert found[0]["suggested_status"] is None
    assert reason in found[0]["reason"]


def test_no_mismatch_for_unfinished_plan_or_fixed_error():
    assert errors.sync_findings({"items": [item()]}, plan("🔄")) == []
    assert errors.sync_findings({"items": [item(status="FIXED_UNVERIFIED")]}, plan()) == []


def test_code_checkmark_inside_gate_note_does_not_complete_code():
    parsed = plan_progress.parse("- [ ] M2.4 · code chưa xong · nặng:1 · ⬜ · ghi chú ✅ cũ · cổng: ⬜")
    assert errors.sync_findings({"items": [item()]}, parsed) == []


def test_cli_check_preserves_schema_exit_status_but_prints_sync_warnings(capsys):
    from tests.test_error_registry import _doc, _item
    with mock.patch.object(errors, "load_plan", return_value=plan()):
        assert errors.cmd_check(_doc(_item()), "fixture.json") == 0
    assert "PLAN_DONE_ERROR_OPEN" in capsys.readouterr().out


def test_evidence_checks_ancestor_path_and_exact_test_node_without_import(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text("class TestCase:\n    def test_green(self):\n        pass\n", encoding="utf-8")
    row = item(fix_commit=["123abcd (đã gộp)"], tests=["tests/test_example.py::TestCase::test_green"])
    assert errors.code_evidence_problems(row, str(tmp_path), commit_check=lambda sha: sha == "123abcd") == []
    assert errors.code_evidence_problems(row, str(tmp_path), commit_check=lambda _: False)
    for reference in ("../test_example.py", "tests/test_missing.py", "tests/test_example.py::test_green"):
        assert errors.code_evidence_problems({**row, "tests": [reference]}, str(tmp_path), commit_check=lambda _: True)


def test_no_proposal_from_checkmark_or_declared_but_unchecked_evidence():
    row = item(fix_commit=["not-a-sha"], tests=["tests/test_not_existing.py"])
    found = errors.sync_findings({"items": [row]}, plan())
    assert found[0]["suggested_status"] is None
    assert "không xác nhận" in found[0]["reason"]


def test_missing_test_run_is_not_verified_and_does_not_block_code_only_suggestion():
    row = item(fix_commit=["123abcd"], tests=["tests/test_fixture.py"], status_reason="chưa có bằng chứng chạy thật")
    finding = errors.sync_findings({"items": [row]}, plan(), verify=lambda _: [])[0]
    assert finding["suggested_status"] == "FIXED_UNVERIFIED"


def test_plan_parse_failure_is_visible():
    found = errors.sync_findings({"items": []}, {"bad": ["mã trùng"], "waves": []})
    assert found[0]["code"] == "PLAN_INVALID"


@pytest.mark.parametrize("scope", ["shadow chỉ phát hiện", "chưa nối luồng gen", "cờ thử_nghiệm TẮT"])
def test_plan_scope_can_prevent_suggestion_even_with_empty_item_reason(scope):
    parsed = plan_progress.parse(f"- [ ] M2.4 · sửa code · nặng:1 · ✅ · {scope} · cổng: ⬜ chưa chạy thật")
    row = item(fix_commit=["123abcd"], tests=["tests/test_fixture.py"])
    assert errors.sync_findings({"items": [row]}, parsed, verify=lambda _: [])[0]["suggested_status"] is None


def test_commit_cache_is_per_sync_call_and_never_survives_head_changes(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    rows = [item(id=f"P31-G{i}", fix_commit=["123abcd"], tests=["tests/test_x.py::test_ok"]) for i in (1, 2)]
    original = errors.code_evidence_problems
    with mock.patch.object(errors, "_commit_is_ancestor", return_value=True) as check, \
            mock.patch.object(errors, "code_evidence_problems", side_effect=lambda row, **kw: original(row, root=str(tmp_path), **kw)):
        assert len(errors.sync_findings({"items": rows}, plan())) == 2
        assert check.call_count == 1
        errors.sync_findings({"items": rows}, plan())
        assert check.call_count == 2


def test_catalog_golden_groups_keep_unknown_occurrences_and_no_verified():
    rows = {row["id"]: row for row in errors.load()["items"]}
    hold, replay = rows["V31-GOLDEN1"], rows["V31-GOLDEN2"]
    assert hold["status"] == "OPEN" and len(hold["job_ids"]) == 30
    assert "31" in hold["evidence"] and "1 job" in hold["status_reason"]
    assert replay["status"] == "FIXED_UNVERIFIED" and len(replay["job_ids"]) == 10
    assert replay["fix_commit"] and replay["tests"] and not replay["real_run_evidence"]
    assert rows["P31-G36"]["status"] == "IN_PROGRESS"
    assert all(rows[code]["status"] == "OPEN" for code in ("P31-G56", "P33-A7", "P33-A8", "P33-A9"))
