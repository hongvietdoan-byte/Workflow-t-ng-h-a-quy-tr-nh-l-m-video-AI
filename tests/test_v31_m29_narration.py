"""V3.1 M2.9: lời dẫn ngoài khớp môi ở mọi caller (cờ narration_offscreen) — phần ngoài bảng ca của test_narration_regression."""
import ast
import json
import pathlib

import pytest

from core import features, lipsync

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def flags(tmp_path, monkeypatch):
    path = tmp_path / "flags.json"
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(path))
    monkeypatch.delenv("FEATURE_NARRATION_OFFSCREEN", raising=False)

    def set_(**on):
        path.write_text(json.dumps({"flags": on}), encoding="utf-8")
        features.settings()
    set_()
    return set_


NARR = {"dialogue": [{"speaker": "LỜI DẪN", "text": "Ngày ấy."}], "characters": ["KELLY"], "size": "CU", "lip_sync": True,
        "shot_no": 1}
KELLY = {"dialogue": [{"speaker": "KELLY", "text": "Chào."}], "characters": ["KELLY"], "size": "CU", "lip_sync": True, "shot_no": 1}


def test_talking_one_source():
    assert lipsync.talking(KELLY)
    assert not lipsync.talking(NARR)
    assert not lipsync.talking({"dialogue": [{"speaker": "KELLY (V.O.)", "text": "x"}], "characters": ["KELLY"], "shot_no": 1})
    assert not lipsync.talking({"dialogue": [{"speaker": "KENTA", "text": "x"}], "characters": ["KELLY"], "shot_no": 1})
    assert not lipsync.talking({"dialogue": [{"speaker": "CTA_TEXT", "text": "x"}], "shot_no": 1})
    assert not lipsync.talking(None)


@pytest.mark.parametrize("on", [False, True])
def test_forget_skipped_only_with_flag(flags, tmp_path, on):
    flags(narration_offscreen=on)
    lipsync.mark(str(tmp_path), 1, 7, state="done", method="generate", offsets=[1.0], job_id=3)
    assert lipsync.forget_skipped(str(tmp_path), 1, 7, NARR) is on
    assert lipsync.synced_scene_ids(str(tmp_path), 1) == (set() if on else {7})
    rec = lipsync.index(str(tmp_path), 1)["7"]
    assert ("offsets" in rec) is (not on) and ("job_id" in rec) is (not on)


def test_forget_skipped_keeps_talking_shot_and_writes_nothing_new(flags, tmp_path):
    flags(narration_offscreen=True)
    lipsync.mark(str(tmp_path), 1, 7, state="done", method="generate", offsets=[1.0], job_id=3)
    assert lipsync.forget_skipped(str(tmp_path), 1, 7, KELLY) is False
    assert lipsync.synced_scene_ids(str(tmp_path), 1) == {7}
    assert lipsync.forget_skipped(str(tmp_path), 1, 8, NARR) is False          # không có mục cũ: không tạo mục mới
    assert "8" not in lipsync.index(str(tmp_path), 1)


def test_mark_skip_flag_off_keeps_old_fields(flags, tmp_path):
    lipsync.mark(str(tmp_path), 1, 7, state="done", method="take", offsets=[1], job_id=4)
    lipsync.mark(str(tmp_path), 1, 7, method="skip")
    assert lipsync.index(str(tmp_path), 1)["7"] == {"state": "done", "method": "skip", "offsets": [1], "job_id": 4}


# AST: không caller nào còn suy "đang nói" từ `bool(<x>.get("dialogue"))` hay `<x>.get("lip_sync") is True` mà không qua cờ
# narration_offscreen / lipsync.talking. Danh sách cho phép = chỗ cũ giữ cho cờ TẮT (cùng hàm có hỏi offscreen_on/talking) hoặc
# chỗ không suy "đang nói" (shot_complexity: điểm hiển thị; lipsync._method: nguồn chuẩn, đã bỏ người dẫn).
ALLOWED_FUNCS = {("core/lipsync.py", "_method"), ("core/shot_complexity.py", "score")}


def _infers_talking(node) -> bool:
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "bool" and node.args:
        a = node.args[0]
        return (isinstance(a, ast.Call) and getattr(a.func, "attr", None) == "get" and a.args
                and isinstance(a.args[0], ast.Constant) and a.args[0].value == "dialogue")
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Is):
        a, b = node.left, node.comparators[0]
        return (isinstance(a, ast.Call) and getattr(a.func, "attr", None) == "get" and a.args and isinstance(a.args[0], ast.Constant)
                and a.args[0].value == "lip_sync" and isinstance(b, ast.Constant) and b.value is True)
    return False


def test_no_caller_infers_talking_without_flag():
    bad = []
    for path in sorted((ROOT / "core").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            hits = [n for n in ast.walk(fn) if _infers_talking(n)]
            if not hits or (rel, fn.name) in ALLOWED_FUNCS:
                continue
            src = ast.get_source_segment(path.read_text(encoding="utf-8"), fn) or ""
            if "offscreen_on(" in src or "talking(" in src:
                continue
            bad.append(f"{rel}:{fn.name}:{hits[0].lineno}")
    assert not bad, bad
