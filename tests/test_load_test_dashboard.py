"""Đảm bảo entrypoint M8.3 mới dùng chung harness hiện có, không tạo nhánh đo thứ hai."""

import os
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _isolated_environment():
    with mock.patch.object(os, "environ", {"PYTHONUTF8": "1"}):
        yield


def test_main_delegates_arguments_and_exit_code_to_shared_harness(monkeypatch):
    from tools import load_test_dashboard, load_test_ui

    seen = []

    def fake_main(argv=None):
        seen.append(argv)
        return 7

    monkeypatch.setattr(load_test_ui, "main", fake_main)

    result = load_test_dashboard.main(["--levels", "1,5,10", "--projects", "4", "--shots", "30"])

    assert result == 7
    assert seen == [["--levels", "1,5,10", "--projects", "4", "--shots", "30"]]
