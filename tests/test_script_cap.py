"""S14.2 — khóa cứng --max-usd cho script dòng lệnh (core/script_cap.py; mục 6d ý 6). 0 USD: client Claude giả, nhà cung cấp giả tên
thật, CSDL tạm. Kèm test quét: mọi script tools/ gọi API trả tiền phải đi qua script_cap (hoặc nằm trong danh sách trắng có lý do)."""
import argparse
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from core import budget, cost, llm_runner, script_cap
from core.adapters.http import HttpResponse
from core.db import connect

ROOT = Path(__file__).resolve().parent.parent


def _args(*argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    script_cap.add_argument(ap)
    return ap.parse_args(list(argv))


def _transport(calls):
    def send(method, url, headers, body, timeout):
        calls.append(json.loads(body))
        return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "OK"}], "stop_reason": "end_turn",
                                             "usage": {"input_tokens": 1000, "output_tokens": 200}}).encode())
    return send


class FromArgs(unittest.TestCase):
    def test_yes_without_max_usd_refuses_to_run(self):
        with self.assertRaises(SystemExit) as cm:
            script_cap.from_args(_args("--yes"), "thử")
        self.assertIn("--max-usd", str(cm.exception))

    def test_dry_run_has_no_cap_and_a_declared_cap_is_hard(self):
        self.assertIs(script_cap.from_args(_args(), "thử"), script_cap.NO_CAP)
        cap = script_cap.from_args(_args("--yes", "--max-usd", "0.5"), "thử", log=lambda *_: None)
        self.assertEqual(cap.max_usd, 0.5)
        with self.assertRaises(SystemExit):
            script_cap.from_args(_args("--yes", "--max-usd", "0"), "thử")
        with self.assertRaises(SystemExit):
            script_cap.require(_args(), "thử")                   # a script that always pays: no dry run without the cap


class CapRules(unittest.TestCase):
    def test_spent_plus_next_over_the_cap_stops_and_says_how_much(self):
        said = []
        cap = script_cap.ScriptCap(1.0, "đo", log=said.append)
        self.assertTrue(cap.allow(0.4))
        cap.add(0.4)
        cap.add(0.4)
        self.assertFalse(cap.allow(0.3))                         # 0.8 + 0.3 > 1.0
        self.assertIn("0.80", said[-1])
        self.assertFalse(cap.allow(0.0))                         # stopped once = stopped
        self.assertIn("ĐÃ DỪNG", cap.summary())

    def test_with_block_swallows_the_stop_so_results_after_it_are_kept(self):
        kept = []
        with script_cap.ScriptCap(0.1, "đo", log=lambda *_: None) as cap:
            cap.add(0.09)
            cap.guard(0.05)
            kept.append("không tới đây")
        kept.append("ghi kết quả")
        self.assertEqual(kept, ["ghi kết quả"])
        self.assertIsNone(script_cap.active())


class Hooks(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        self.conn = connect(self.db)

    def test_no_cap_active_changes_nothing(self):
        self.assertIsNone(script_cap.active())
        self.assertIsNone(budget.check_image(self.conn, "deepix", "gpt-image-2", 100))

    def test_image_sends_are_counted_from_the_ledger_rows_and_refused_past_the_cap(self):
        price = cost.load_pricing()["per_image"]["gpt-image-2"]          # 0.052
        with script_cap.ScriptCap(price * 2.5, "ảnh", log=lambda *_: None) as cap:
            sent = 0
            for _ in range(5):
                if budget.check_image(self.conn, "deepix", "gpt-image-2", 1):
                    break
                cost.record_usage(self.conn, None, "image", "deepix", "gpt-image-2", "image", 1, "image")
                sent += 1
            self.assertEqual(sent, 2)
            self.assertAlmostEqual(cap.spent, price * 2)
            self.assertIsNone(budget.check_image(self.conn, "mock", "gpt-image-2", 1) and None)
        self.assertIsNone(budget.check_image(self.conn, "deepix", "gpt-image-2", 1))   # the lock ends with its block

    def test_mock_provider_and_unpriced_audio_cost_nothing(self):
        with script_cap.ScriptCap(0.01, "âm", log=lambda *_: None) as cap:
            self.assertIsNone(budget.check_audio(self.conn, "clipai_audio"))
            cost.record_usage(self.conn, None, "image", "mock", "gpt-image-2", "image", 50, "image")
            self.assertEqual(cap.spent, 0.0)

    def test_claude_calls_stop_before_paying_past_the_cap(self):
        calls = []
        client = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=_transport(calls), sleep=lambda s: None)
        said = []
        with script_cap.ScriptCap(0.05, "claude", log=said.append) as cap:
            for _ in range(10):
                client.complete("x")
        # each call ≈ 0.004 USD paid; before each one the next is guessed ≈ 0.04 (≤ 4000 output tokens) → the 4th is refused
        self.assertEqual(len(calls), 3)
        self.assertAlmostEqual(cap.spent, 3 * 0.004, places=6)
        self.assertTrue(any("DỪNG" in s for s in said))
        self.assertTrue(any("đã chi ≈ $0.01" in s for s in said))


# ---- quét: script tools/ gọi API trả tiền phải dùng script_cap ---------------------------------------------------------------------
PAID = re.compile(r"client_from_env|\.submit\w*\(|submit_pending|submit_drafts|spend_gate\.spend|budget\.check_(image|video|audio)|"
                  r"ask_json|meshy\.submit|Provider\.from_env|scorer\.run\(")
# script → vì sao không cần trần USD
SCRIPT_OK = {
    "tools/voice_trial.py": "chỉ gửi âm thanh — chưa có giá USD; giới hạn theo lượt (audio_refusal / trần lượt âm thanh)",
    "tools/experiments/audio_s26_s115.py": "chỉ gửi âm thanh — chưa có giá USD; giới hạn theo lượt (budget.check_audio)",
    "tools/audit_run.py": "chỉ đọc trạng thái (.submitted), không gửi gì",
    "tools/recover_clips.py": "chỉ đọc video-list / tải clip đã trả tiền; không gửi job mới (docstring)",
    "tools/experiments/s411_s412_probe.py": "dò API chỉ đọc (user-info, video-list), không gửi job",
}


def paid_scripts(root: Path = ROOT):
    out = []
    for path in sorted(list((root / "tools").glob("*.py")) + list((root / "tools" / "experiments").glob("*.py"))):
        text = path.read_text(encoding="utf-8")
        if PAID.search(text):
            out.append((path.relative_to(root).as_posix(), "script_cap." in text))
    return out


class ScriptScan(unittest.TestCase):
    def test_every_paid_script_declares_a_hard_max_usd(self):
        missing = [f for f, ok in paid_scripts() if not ok and f not in SCRIPT_OK]
        self.assertEqual([], missing, "Script gọi API trả tiền mà không có trần cứng --max-usd (core/script_cap.py) — thêm "
                                      "script_cap.add_argument + from_args/require, hoặc thêm vào SCRIPT_OK kèm lý do")

    def test_allow_list_is_not_stale(self):
        found = {f: ok for f, ok in paid_scripts()}
        self.assertEqual([], [f for f in SCRIPT_OK if f not in found or found[f]])


if __name__ == "__main__":
    unittest.main()
