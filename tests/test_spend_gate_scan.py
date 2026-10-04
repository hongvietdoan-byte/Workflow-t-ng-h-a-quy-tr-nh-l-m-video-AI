"""S14.1 A1a — scan test (docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 3.1): a paid send outside the money gate must not come back.

(a) Every call that sends paid work — `.submit…(`, `post_multipart(`, `generate_tts|generate_music|generate_sfx(`, Deepix `cutout(` —
    in core/ dashboard/ tools/ sits in a function that uses `spend_gate.spend(`, or the old pattern `SPEND_LOCK` + `check_*` +
    `project_budget.check` in the same function or the same class. Otherwise it must be in the small allow-list below (each entry says
    why) or in PENDING ("CHỜ CHUYỂN": known, not moved yet, named after the S14 task that moves it) — the test stays green but the
    list is printed, never silent.
(b) Every call of `budget.check_image` / `budget.check_video` sits in a function that also calls `project_budget.check` (or the
    gate) — the end frame, establishing picture and multi-shot try had the trial cap only.
Entries that no longer match anything are reported too (a stale list hides nothing)."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = ("core", "dashboard", "tools")

SEND = re.compile(r"^(submit\w*|post_multipart|generate_tts|generate_music|generate_sfx|cutout)$")

# ---- allow-list: where a raw send is right, and why -------------------------------------------------------------------------------
PREFIX_OK = {
    "core/adapters/": "adapter = chính lời gọi HTTP tới nhà cung cấp; cổng nằm ở nơi gọi adapter",
    "tools/experiments/": "bài thử nghiệm/nghiệm thu: spend_cap riêng, tính vào claude_other (docstring core/project_budget.py)",
}
FILE_OK = {
    "core/providers.py": "giao thức + nhà cung cấp giả (mock), không tốn tiền",
    "tools/asset_polish.py": "công cụ dòng lệnh người dùng tự chạy, có xác nhận + giá riêng",
    "tools/h5_setup_test.py": "bài thử H5 dòng lệnh, có trần riêng",
    "tools/pilot_run.py": "chạy thử dòng lệnh: đi qua runner.submit_pending / music.submit_drafts (đã có cổng)",
    "tools/voice_trial.py": "thử giọng dòng lệnh: audio_lib.submit_tts (audio_refusal)",
}
CALLEE_OK = {
    "submit_pending": "runner._Runner.submit_pending — cổng SPEND_LOCK + _over_budget (check_* + project_budget.check)",
    "submit_drafts": "music.submit_drafts — audio_refusal (budget.check_audio) + record_audio_usage",
    "submit_tts": "audio_lib.submit_tts — audio_refusal + sổ âm thanh",
    "submit_sfx": "audio_lib.submit_sfx — audio_refusal + sổ âm thanh",
    "submitted": "không phải lời gửi (đọc trạng thái)",
    "submit_model": "Meshy — sổ credit riêng (core/meshy.py), không qua bảng giá USD",
    "submit_rig": "Meshy — sổ credit riêng (core/meshy.py)",
}
RECEIVER_OK = {"pool": "ThreadPoolExecutor.submit — không phải lời gọi trả tiền"}
# (file, function qualname) → (why, a text that must stay in the function so the reason does not rot)
FUNC_OK = {
    ("core/runner.py", "_Runner._submit_pending"): ("mẫu cũ giữ nguyên: SPEND_LOCK + self._over_budget (ImageRunner/VideoRunner gọi "
                                                   "check_* + project_budget.check, xem quét (b)); chuyển sang cổng ở nhánh A1b",
                                                   "SPEND_LOCK"),
    ("core/audio_lib.py", "submit_sfx"): ("âm thanh chưa có giá USD: audio_refusal (check_audio) giới hạn theo lượt", "audio_refusal("),
    ("core/audio_lib.py", "submit_tts"): ("âm thanh chưa có giá USD: audio_refusal (check_audio) giới hạn theo lượt", "audio_refusal("),
    ("core/music.py", "submit_drafts"): ("âm thanh chưa có giá USD: audio_refusal (check_audio) giới hạn theo lượt", "audio_refusal("),
}
# ---- CHỜ CHUYỂN: known raw sends not moved to the gate yet — the S14 task that moves each one --------------------------------------
PENDING = {
    ("core/lipsync.py", "post_tick"): "S14.1 A1b — lipsync qua spend_gate (nhánh khác; hiện SPEND_LOCK + check_video, thiếu project_budget)",
    ("core/storyboard_frames.py", "run"): "S14.1 A1 phần còn lại — provider.submit_storyboard_frame qua spend_gate",
    ("core/previz.py", "_deepix_cutout"): "S14.1 A1 phần còn lại — Deepix cutout (cờ PREVIZ_CUTOUT) chưa có sổ chi / cổng",
}
# (b): check_image / check_video without project_budget.check — the same waiting list
PENDING_B = {
    ("core/lipsync.py", "post_tick"): "S14.1 A1b — lipsync thiếu project_budget.check",
    ("core/autopilot.py", "_setcheck_block"): "S14.1 A1b — autopilot: kiểm trước khi xếp vẽ lại (lượt gửi thật vẫn qua ImageRunner "
                                               "có project_budget.check); dùng spend_gate.reason khi chuyển",
}


def _files():
    for d in DIRS:
        for f in sorted((ROOT / d).rglob("*.py")):
            yield f.relative_to(ROOT).as_posix(), f


def _callee(call: ast.Call):
    f = call.func
    if isinstance(f, ast.Attribute):
        recv = f.value
        name = recv.id if isinstance(recv, ast.Name) else recv.attr if isinstance(recv, ast.Attribute) else ""
        return f.attr, name
    if isinstance(f, ast.Name):
        return f.id, ""
    return None, ""


def _outer_function(tree, call):
    """The OUTERMOST function (method) containing the call — a nested helper belongs to the function that owns it."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and _contains(item, call):
                    return f"{node.name}.{item.name}", item, node
        if isinstance(node, ast.Module):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and _contains(item, call):
                    best = (item.name, item, None)
    return best or ("<module>", None, None)


def _contains(node, target):
    return node.lineno <= target.lineno <= (node.end_lineno or node.lineno) and any(n is target for n in ast.walk(node))


def _seg(src, node):
    return ast.get_source_segment(src, node) or "" if node is not None else ""


GATED = re.compile(r"spend_gate\.spend\(")


def _old_pattern(text):
    return "SPEND_LOCK" in text and re.search(r"check_(image|video|audio)\(", text) and "project_budget.check(" in text


def scan():
    """Returns (bad, waiting, used_ok) for (a)."""
    bad, waiting, used = [], [], set()
    for rel, f in _files():
        src = f.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"submit|post_multipart|generate_(tts|music|sfx)|cutout\(", src):
            continue
        tree = ast.parse(src)
        for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
            name, recv = _callee(call)
            if not name or not SEND.match(name):
                continue
            qual, fn, cls = _outer_function(tree, call)
            key = (rel, qual)
            where = f"{rel}:{call.lineno} {qual} → {name}("
            if fn is not None and isinstance(fn, ast.FunctionDef) and fn.name == name:
                continue                                         # recursion / the definition's own body
            if any(rel.startswith(p) for p in PREFIX_OK) or rel in FILE_OK:
                continue
            if name in CALLEE_OK or recv in RECEIVER_OK:
                used.add(("callee", name if name in CALLEE_OK else recv))
                continue
            fn_src, cls_src = _seg(src, fn), _seg(src, cls)
            if GATED.search(fn_src) or _old_pattern(fn_src) or (cls is not None and _old_pattern(cls_src)):
                continue
            if key in FUNC_OK:
                why, marker = FUNC_OK[key]
                used.add(key)
                if marker not in fn_src:
                    bad.append(f"{where} — danh sách trắng nói '{why}' nhưng hàm không còn '{marker}'")
                continue
            if key in PENDING:
                used.add(key)
                waiting.append(f"{where} — CHỜ CHUYỂN: {PENDING[key]}")
                continue
            bad.append(where)
    return bad, waiting, used


def scan_checks():
    """(b): check_image / check_video calls whose function has no project_budget.check (nor the gate)."""
    bad, waiting, used = [], [], set()
    for rel, f in _files():
        src = f.read_text(encoding="utf-8", errors="ignore")
        if "check_image(" not in src and "check_video(" not in src:
            continue
        if rel in ("core/budget.py", "core/spend_gate.py") or any(rel.startswith(p) for p in PREFIX_OK) or rel in FILE_OK:
            continue                                             # the definitions / the gate itself / allowed tools
        tree = ast.parse(src)
        for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
            name, _ = _callee(call)
            if name not in ("check_image", "check_video"):
                continue
            qual, fn, _cls = _outer_function(tree, call)
            fn_src = _seg(src, fn)
            if "project_budget.check(" in fn_src or GATED.search(fn_src):
                continue
            key = (rel, qual)
            if key in PENDING_B:
                used.add(key)
                waiting.append(f"{rel}:{call.lineno} {qual} → {name}( — CHỜ CHUYỂN: {PENDING_B[key]}")
                continue
            bad.append(f"{rel}:{call.lineno} {qual} → {name}( không kèm project_budget.check")
    return bad, waiting, used


class SpendGateScan(unittest.TestCase):
    def test_the_scan_finds_the_known_sends(self):
        bad, waiting, used = scan()
        self.assertIn(("core/runner.py", "_Runner._submit_pending"), used)       # the scan really sees the runner
        self.assertFalse(any("costume" in w for w in waiting + bad))           # moved to the gate

    def test_every_paid_send_goes_through_the_gate(self):
        bad, waiting, _ = scan()
        if waiting:
            print("\nCHỜ CHUYỂN sang spend_gate (" + str(len(waiting)) + "):\n  " + "\n  ".join(waiting))
        self.assertEqual(bad, [], "lời gửi tốn tiền ngoài cổng (dùng core.spend_gate.spend, hoặc thêm vào danh sách có lý do):\n"
                         + "\n".join(bad))

    def test_every_trial_cap_check_has_the_project_budget(self):
        bad, waiting, _ = scan_checks()
        if waiting:
            print("\nCHỜ CHUYỂN (check_* thiếu project_budget):\n  " + "\n  ".join(waiting))
        self.assertEqual(bad, [], "\n".join(bad))

    def test_no_stale_entry_in_the_lists(self):
        _, _, used = scan()
        _, _, used_b = scan_checks()
        stale = [k for k in list(FUNC_OK) + list(PENDING) if k not in used]
        stale += [("callee", k) for k in CALLEE_OK if ("callee", k) not in used and k not in ("submitted",)]
        stale += [k for k in PENDING_B if k not in used_b]
        self.assertEqual(stale, [], "mục danh sách không còn khớp lời gọi nào — xóa khỏi danh sách (đã chuyển xong?)")

    def test_the_moved_callers_use_the_gate(self):
        for rel in ("core/costume.py", "core/experiments.py", "core/scene_establish.py", "core/end_frames.py"):
            self.assertIn("spend_gate.spend(", (ROOT / rel).read_text(encoding="utf-8"), rel)


if __name__ == "__main__":
    unittest.main()
