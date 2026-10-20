"""V3.1 M1.4a (rủi ro R2, người dùng duyệt 20/10): máy chính có ANTHROPIC_API_KEY thật trong môi trường User — không đường nào được
tự gọi Claude API trả phí khi chưa khai LLM_PROVIDER=anthropic, và `claude -p` không bao giờ nhận key/endpoint trả phí.
Toàn bộ là giả lập: không lời gọi API / tiến trình claude thật nào."""
import contextlib
import io
import os
import unittest
from unittest import mock

from core import llm_runner as lr

KEY = "sk-ant-gia-lap-m14a"
ONLY_KEY = {"ANTHROPIC_API_KEY": KEY, "LLM_PROVIDER": ""}


def _no_paid_api():
    """Any attempt to build the paid client fails the test loudly."""
    return mock.patch.object(lr.AnthropicClient, "from_env", side_effect=AssertionError("gọi Claude API trả phí ngoài ý muốn"))


class ProviderSelectionTests(unittest.TestCase):
    def test_only_a_key_gives_no_client_and_says_why(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, ONLY_KEY), mock.patch.object(lr, "_WARNED_KEY_ONLY", False), _no_paid_api(), \
                contextlib.redirect_stderr(err):
            self.assertIsNone(lr.client_from_env())
        self.assertIn(lr.NO_PROVIDER_HINT, err.getvalue())
        self.assertNotIn(KEY, err.getvalue())

    def test_nothing_set_is_quiet_none(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "LLM_PROVIDER": ""}), contextlib.redirect_stderr(err):
            self.assertIsNone(lr.client_from_env())
        self.assertEqual(err.getvalue(), "")

    def test_the_paid_api_only_when_declared(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": KEY, "LLM_PROVIDER": "anthropic"}):
            self.assertEqual(lr.client_from_env().name, "anthropic")

    def test_provider_status_and_missing_hint(self):
        with mock.patch.dict(os.environ, ONLY_KEY):
            self.assertEqual(lr.provider_status(), (None, lr.NO_PROVIDER_HINT))
            self.assertEqual(lr.missing_hint(), lr.NO_PROVIDER_HINT)
            self.assertIn("LLM_PROVIDER=claude_cli", lr.missing_hint())
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            kind, why = lr.provider_status()
            self.assertIsNone(kind)
            self.assertIn("không hợp lệ", why)
            self.assertEqual(lr.missing_hint(), why)
            self.assertIsNone(lr.client_from_env())
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "claude_cli"}):
            self.assertEqual(lr.provider_status()[0], "claude_cli")
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "mock"}):
            self.assertEqual(lr.provider_status()[0], "mock")
            self.assertEqual(lr.client_from_env().name, "mock-llm")   # provider giả vẫn chạy như cũ


class ClaudeCliEnvTests(unittest.TestCase):
    PAID = {"ANTHROPIC_API_KEY": KEY, "ANTHROPIC_AUTH_TOKEN": "tok", "ANTHROPIC_BASE_URL": "https://x.invalid",
            "ANTHROPIC_CUSTOM_HEADERS": "h: 1", "KEEP_ME": "1"}

    def test_clean_env_drops_the_four_paid_variables(self):
        with mock.patch.dict(os.environ, self.PAID):
            env = lr.ClaudeCliClient.clean_env()
        for k in lr.ClaudeCliClient.PAID_KEYS:
            self.assertNotIn(k, {x.upper() for x in env})
        self.assertEqual(env.get("KEEP_ME"), "1")

    def test_the_claude_subprocess_never_receives_the_key(self):
        calls = []

        class Done:
            stdout, returncode, stderr = '{"result": "OK", "is_error": false, "usage": {}}', 0, ""

        def run(args, **kw):
            calls.append(kw)
            return Done()

        with mock.patch.dict(os.environ, self.PAID):
            reply = lr.ClaudeCliClient(run=run).complete("x")
        self.assertEqual(reply.text, "OK")
        env = calls[0]["env"]
        self.assertIsNotNone(env)
        for k in lr.ClaudeCliClient.PAID_KEYS:
            self.assertNotIn(k, {x.upper() for x in env})
        self.assertNotIn(KEY, "".join(env.values()))
        self.assertEqual(env.get("KEEP_ME"), "1")


class CliErrorCodeTests(unittest.TestCase):
    def test_new_limit_and_credit_messages(self):
        self.assertEqual(lr.cli_error_code("You've hit your limit · resets 3am (Asia/Saigon)"), "usage_limit")
        self.assertEqual(lr.cli_error_code("Credit balance is too low"), "out_of_credit")
        self.assertEqual(lr.cli_error_code("Failed to authenticate"), "auth")
        self.assertEqual(lr.cli_error_code("something else"), "cli_error")


class BackgroundPathsTests(unittest.TestCase):
    """Đường nền / tự động (không ai bấm) với chỉ có key: không dựng client trả phí, nói rõ lý do."""

    def test_autoqc_can_run_is_false_with_only_a_key(self):
        from core import autoqc
        from core.db import connect
        conn = connect(":memory:")
        with mock.patch.dict(os.environ, ONLY_KEY), _no_paid_api(), contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(autoqc, "waiting", return_value=3), mock.patch.object(autoqc, "active", return_value=False), \
                mock.patch.object(autoqc, "last_error", return_value=None):
            self.assertFalse(autoqc.can_run(conn, 1))

    def test_change_review_round_runs_code_rules_only_and_says_so(self):
        from core import bg_poll, change_review
        seen = {}
        notes = []

        def process(conn, data_dir, client=None, **kw):
            seen["client"] = client
            return {"reviewed": 0}

        with mock.patch.dict(os.environ, ONLY_KEY), _no_paid_api(), contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(change_review, "enabled", return_value=True), \
                mock.patch.object(change_review, "process_pending", side_effect=process), \
                mock.patch.object(bg_poll.diag, "record", side_effect=lambda *a, **k: notes.append(a)), \
                mock.patch.object(lr, "db_file", return_value=None):
            bg_poll.change_review_round(object(), "data")
        self.assertIn("client", seen)
        self.assertIsNone(seen["client"])                      # code_only, never the paid API
        self.assertTrue(any(lr.NO_PROVIDER_HINT in str(a) for a in notes), notes)

    def test_autopilot_refuses_with_only_a_key_and_says_why(self):
        from core import autopilot
        from core.adapters import factory
        p = mock.MagicMock()
        with mock.patch.dict(os.environ, ONLY_KEY), _no_paid_api(), contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(factory, "image_provider", return_value=object()), \
                mock.patch.object(factory, "video_provider", return_value=object()), \
                mock.patch.object(lr, "db_file", return_value=None):
            with self.assertRaises(ValueError) as e:
                autopilot.default_context(p, "data")
        self.assertIn(lr.NO_PROVIDER_HINT, str(e.exception))

    def test_user_facing_hints_use_the_shared_text(self):
        from core.adapters import check
        with mock.patch.dict(os.environ, ONLY_KEY), _no_paid_api(), contextlib.redirect_stderr(io.StringIO()):
            name, ok, msg = check.check_llm()
        self.assertFalse(ok)
        self.assertIn(lr.NO_PROVIDER_HINT, msg)


if __name__ == "__main__":
    unittest.main()
