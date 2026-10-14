"""Chạy tương tác offline thật; không cần DB, mạng hay hồ sơ Chrome người dùng."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("with_fake_credentials", [False, True])
def test_browser_stage_editor(tmp_path, monkeypatch, with_fake_credentials):
    # Cách ly toàn bộ môi trường trước lookup/runtime; teardown phục hồi nguyên trạng.
    monkeypatch.setattr(os, "environ", {"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows",
                                      "USERPROFILE": "C:/Users/hongviet.doan",
                                      "TEMP": str(tmp_path), "TMP": str(tmp_path)})
    if with_fake_credentials:
        os.environ.update({"ANTHROPIC_API_KEY": "fixture-not-a-key", "OPENAI_API_KEY": "fixture-not-a-key",
                           "D11_MODEL_REGISTRY": "fixture-only"})
    # Các module chạy/lookup chỉ import sau dict giả; monkeypatch teardown cả hai ca.
    import shutil
    import subprocess

    assert (ROOT / "mockup/ban_dung_3d.html").is_file(), "thiếu màn bàn dựng"
    node = shutil.which("node")
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    if bundled.is_file():
        node = str(bundled)
    if not node:
        pytest.skip("không có Node để chạy Playwright")
    run = subprocess.run([node, str(ROOT / "tools/qa_ban_dung_d11.js")], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", timeout=90,
                         env=dict(os.environ, PYTHONUTF8="1", D11_SHOT_DIR=str(tmp_path)))
    if run.returncode == 77:
        pytest.skip(run.stdout.strip())
    assert run.returncode == 0, run.stdout + run.stderr
    assert "1440+1280: console=0 overflow=0" in run.stdout


def test_the_check_writes_its_screenshots_where_it_is_told():
    """Hộp thư 12/10 21:05: chạy cả bộ test SỬA 4 ảnh tài liệu `docs/images/d11/ban_dung_*.png` có trong git — ảnh chụp của lượt kiểm
    phải vào thư mục tạm (D11_SHOT_DIR); chỉ chạy tay script mới ghi lại ảnh tài liệu."""
    js = (ROOT / "tools/qa_ban_dung_d11.js").read_text(encoding="utf-8")
    assert "process.env.D11_SHOT_DIR" in js
    src = Path(__file__).read_text(encoding="utf-8")
    assert "D11_SHOT_DIR=str(tmp_path)" in src
