"""Chạy tương tác offline thật; không cần DB, mạng hay hồ sơ Chrome người dùng."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_browser_stage_editor():
    assert (ROOT / "mockup/ban_dung_3d.html").is_file(), "thiếu màn bàn dựng"
    node = shutil.which("node")
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    if bundled.is_file():
        node = str(bundled)
    if not node:
        pytest.skip("không có Node để chạy Playwright")
    run = subprocess.run([node, str(ROOT / "tools/qa_ban_dung_d11.js")], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", timeout=90,
                         env=dict(os.environ, PYTHONUTF8="1"))
    if run.returncode == 77:
        pytest.skip(run.stdout.strip())
    assert run.returncode == 0, run.stdout + run.stderr
    assert "1440+1280: console=0 overflow=0" in run.stdout
