"""V3.1 M1.4a — sửa theo agent rà (20/10): hết hạn mức gói / hết tiền dừng cả lượt (STOP_CODES), lời báo đúng lý do khi đã khai
provider, Tổ rà soát không im lặng khi provider sai, tool kiểm client None, cảnh báo 'chỉ có key' in một lần mỗi tiến trình.
Toàn bộ giả lập: không lời gọi API / tiến trình claude thật nào."""
import contextlib
import glob
import io
import os
import re
import time
import unittest
from unittest import mock

from core import asset_vision, assets, autoqc, llm_runner as lr
from tests.test_asset_vision import Base as VisionBase, picture
from tests.test_autoqc import Base as QcBase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_TEXTS = ("Credit balance is too low", "You've hit your limit · resets 3am (Asia/Saigon)")


class Counting:
    """A Claude that always fails like the CLI does when the plan's limit / the credit is gone; counts the calls."""
    name = "counting"

    def __init__(self, text):
        self.text, self.calls = text, 0

    def complete(self, prompt, images=()):
        self.calls += 1
        raise lr.LlmError("Claude Code báo lỗi: " + self.text, code=lr.cli_error_code(self.text))


class StopCodesTests(unittest.TestCase):
    def test_limit_and_credit_codes_stop_a_round(self):
        for text in CLI_TEXTS:
            self.assertIn(lr.cli_error_code(text), lr.STOP_CODES)
        for code in ("auth", "config", "timeout", "cli_error", "rate_limit", "server_error"):    # the old list is kept
            self.assertIn(code, lr.STOP_CODES)

    def test_every_round_uses_the_shared_codes(self):
        for path, n in (("core/autoqc.py", 2), ("core/asset_vision.py", 1)):
            with open(os.path.join(ROOT, path), encoding="utf-8") as f:
                self.assertEqual(f.read().count("llm_runner.STOP_CODES"), n, path)


class AutoQcStopsTests(QcBase):
    def wait(self):
        for _ in range(200):
            if not autoqc.active(self.pid):
                return
            time.sleep(0.05)
        self.fail("the background check did not finish")

    def test_the_background_check_stops_once_instead_of_handing_every_picture_over(self):
        for n, text in enumerate(CLI_TEXTS):
            with self.subTest(text=text):
                autoqc._errors.clear()
                jobs = [self.generated_job(self.scene(10 * n + i)) for i in (1, 2, 3)]
                client = Counting(text)
                self.assertTrue(autoqc.start(self.db, self.data, self.pid, lambda: client))
                self.wait()
                self.assertEqual(client.calls, 1)
                self.assertIn(text[:20], autoqc.last_error(self.pid) or "")
                self.assertEqual([self.p.state(j).value for j in jobs], ["succeeded"] * 3)       # nothing handed to the person
                for j in jobs:
                    self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (j,))
                self.p.conn.commit()

    def test_the_qc_batch_stops_at_the_first_limit(self):
        self.generated_job(self.scene(1))
        self.generated_job(self.scene(2))
        client = Counting(CLI_TEXTS[0])
        summary = lr.run_qc_batch(self.p, self.pid, client, self.data)
        self.assertEqual((client.calls, len(summary["failed"])), (1, 1))
        self.assertEqual(summary["failed"][0][1].code, "out_of_credit")


class AssetVisionStopsTests(VisionBase):
    def test_the_background_read_stops_once(self):
        for i in (1, 2, 3):
            a = assets.create(self.conn, "FF", "character", f"K{i}", "", "", None, "x")
            assets.add_image(self.conn, a, f"{i}.png", picture(550, 800, i))
        client = Counting(CLI_TEXTS[1])
        self.assertTrue(asset_vision.start(self.db, "FF", lambda: client))
        self.wait()
        self.assertEqual(client.calls, 1)
        self.assertIn("hit your limit", asset_vision.last_error("FF"))


class MissingHintTests(unittest.TestCase):
    def test_a_declared_provider_that_cannot_be_built_is_not_called_undeclared(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": ""}):
            with self.assertRaises(lr.LlmError):
                lr.client_from_env()
            hint = lr.missing_hint()
        self.assertNotIn("chưa khai", hint)
        self.assertIn("ANTHROPIC_API_KEY", hint)
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "claude_cli"}), mock.patch("shutil.which", return_value=None):
            with self.assertRaises(lr.LlmError):
                lr.client_from_env()
            hint = lr.missing_hint()
        self.assertNotIn("chưa khai", hint)
        self.assertIn("claude", hint)

    def test_undeclared_and_unknown_keep_their_reason(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "", "ANTHROPIC_API_KEY": ""}):
            self.assertEqual(lr.missing_hint(), lr.NO_PROVIDER_HINT)
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            self.assertIn("không hợp lệ", lr.missing_hint())


class ChangeReviewWrongProviderTests(unittest.TestCase):
    def test_a_wrong_provider_without_a_key_is_said_not_silent(self):
        from core import bg_poll, change_review
        notes = []
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "openai", "ANTHROPIC_API_KEY": ""}), \
                mock.patch.object(change_review, "enabled", return_value=True), \
                mock.patch.object(change_review, "process_pending", return_value={"reviewed": 0}), \
                mock.patch.object(bg_poll.diag, "record", side_effect=lambda *a, **k: notes.append(a)), \
                mock.patch.object(lr, "db_file", return_value=None):
            bg_poll.change_review_round(object(), "data")
        self.assertTrue(any("không hợp lệ" in str(a) for a in notes), notes)


class ToolsCheckNoneTests(unittest.TestCase):
    def test_every_tool_that_builds_a_client_checks_none_with_the_shared_hint(self):
        bad = []
        for f in glob.glob(os.path.join(ROOT, "tools", "**", "*.py"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            for i, line in enumerate(lines):
                m = re.match(r"\s*(\w+) = llm_runner\.client_from_env\(", line)
                if not m:
                    continue
                after = "\n".join(lines[i + 1:i + 4])
                if f"{m.group(1)} is None" not in after or "missing_hint" not in after:
                    bad.append(f"{os.path.relpath(f, ROOT)}:{i + 1}")
        self.assertEqual(bad, [])

    def test_the_old_api_only_wording_is_gone(self):
        hits = []
        for f in glob.glob(os.path.join(ROOT, "tools", "**", "*.py"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                if "Chưa cấu hình Claude API" in fh.read():
                    hits.append(os.path.relpath(f, ROOT))
        self.assertEqual(hits, [])


class WarnOnceTests(unittest.TestCase):
    def test_the_key_only_line_is_printed_once_per_process(self):
        err = io.StringIO()
        with mock.patch.object(lr, "_WARNED_KEY_ONLY", False), \
                mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-gia-lap", "LLM_PROVIDER": ""}), \
                mock.patch.object(lr.AnthropicClient, "from_env", side_effect=AssertionError("API trả phí")), \
                contextlib.redirect_stderr(err):
            for _ in range(3):
                self.assertIsNone(lr.client_from_env())
        self.assertEqual(err.getvalue().count("[llm]"), 1)


if __name__ == "__main__":
    unittest.main()
