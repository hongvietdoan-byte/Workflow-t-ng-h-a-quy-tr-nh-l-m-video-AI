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


# ---- A11: thông điệp end_frame_skill_object theo vật thật, không viết cứng "ném keo" / "tường" ----
def _skill_runner(said):
    from types import SimpleNamespace
    return SimpleNamespace(p=SimpleNamespace(conn=None), _scene_data=lambda job: {"action": "the ice tower rises"},
                           _diag_once=lambda job, level, code, msg: said.append((code, msg)))


def test_skill_object_message_names_real_object():
    from unittest.mock import patch
    from core import end_frames, runner, skill_objects
    said = []
    with patch.object(end_frames, "skip_reason", return_value=end_frames.SKILL_SKIP), \
         patch.object(skill_objects, "rising_names", return_value=["Tháp băng"]):
        assert runner.VideoRunner._skill_object_appears(_skill_runner(said), {"scene_id": 5, "project_id": 1}, "end_5.png")
    (code, msg), = said
    assert code == "end_frame_skill_object"                       # trang Chẩn đoán lọc theo code: giữ nguyên
    assert "ném keo" not in msg and "tường" not in msg
    assert "Tháp băng" in msg and "GHÉP" in msg and "KHÔNG kèm" in msg and "end_5.png" in msg


def test_skill_object_message_without_known_name():
    from unittest.mock import patch
    from core import end_frames, runner, skill_objects
    said = []
    with patch.object(end_frames, "skip_reason", return_value=end_frames.SKILL_SKIP), \
         patch.object(skill_objects, "rising_names", return_value=[]):
        runner.VideoRunner._skill_object_appears(_skill_runner(said), {"scene_id": 5, "project_id": 1}, "")
    msg = said[0][1]
    assert "ném keo" not in msg and "tường" not in msg and "vật kỹ năng" in msg


def test_rising_names_only_objects_in_rising_sentence():
    from unittest.mock import patch
    from core import skill_objects
    tower = {"name": "Tháp băng"}
    with patch.object(skill_objects, "skill_assets", return_value=[tower]), \
         patch.object(skill_objects, "_names_of", side_effect=lambda items: [a["name"] for a in items] + ["ice tower"]):
        assert skill_objects.rising_names(None, 1, {"action": "The ice tower shoots up in front of Kenta."}) == ["Tháp băng"]
        assert skill_objects.rising_names(None, 1, {"action": "Kenta runs. The ice tower stands behind him."}) == []


def test_no_hardcoded_glue_words_in_runner_messages():
    """A11: lời nhắn diag của runner không còn viết cứng "(ném keo)" cho mọi vật kỹ năng."""
    src = (ROOT / "core" / "runner.py").read_text(encoding="utf-8")
    assert "(ném keo)" not in src
