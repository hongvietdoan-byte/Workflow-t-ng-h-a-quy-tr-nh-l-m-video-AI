"""GĐ-C1 (docs/KE_HOACH_TONG_2026-09-24.md): every Claude API call goes through the cost ledger with its stage and project, and the
Claude cap refuses when the spend cannot be known (unpriced model, unreadable or unwritable ledger); a cut answer is reported."""
import glob
import json
import os
import re
import tempfile
import unittest
from unittest import mock

from core import budget, llm_runner
from core.adapters.http import HttpResponse
from core.db import connect

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _transport(calls, stop="end_turn"):
    def send(method, url, headers, body, timeout):
        calls.append(json.loads(body))
        return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "OK"}], "stop_reason": stop,
                                             "usage": {"input_tokens": 1000, "output_tokens": 200}}).encode())
    return send


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        self.conn = connect(self.db)
        self.calls = []

    def client(self, model="claude-sonnet-5", stop="end_turn", ledger=True):
        return llm_runner.AnthropicClient("sk-test", model, transport=_transport(self.calls, stop), sleep=lambda s: None,
                                          ledger=self.db if ledger else None)

    def rows(self):
        return self.conn.execute("SELECT stage, project_id, tier FROM usage_events WHERE kind='llm' ORDER BY id").fetchall()

    def test_calls_carry_their_stage_and_project(self):
        pid = self.conn.execute("INSERT INTO projects (name, created_at) VALUES ('P', 'x')").lastrowid
        self.conn.commit()
        c = self.client()
        with llm_runner.tagged("qc", pid):
            with llm_runner.tagged("asset_vision"):               # nested: keeps the outer project
                c.complete("a")
        c.complete("b")                                           # untagged: still in the ledger, as 'other'
        got = [(r["stage"], r["project_id"]) for r in self.rows()]
        self.assertEqual(got, [("asset_vision", pid)] * 2 + [("other", None)] * 2)

    def test_an_unpriced_model_is_refused_before_paying(self):
        with self.assertRaises(llm_runner.LlmError) as err:
            self.client("claude-unknown-9").complete("x")
        self.assertEqual(err.exception.code, "budget")
        self.assertEqual(self.calls, [])

    def test_a_dated_model_id_takes_the_price_of_its_family(self):
        self.client("claude-sonnet-5-20260901").complete("x")
        self.assertAlmostEqual(budget.llm_spent(self.conn), 1000 * 2.0 / 1e6 + 200 * 10.0 / 1e6)
        self.assertAlmostEqual(budget.token_price({"per_million_tokens": {"claude-opus-5": {"input": 5}, "claude-opus-5-5":
                                                                         {"input": 4}}}, "claude-opus-5-5-x", "input", 1e6), 4)

    def test_an_unreadable_ledger_refuses_instead_of_letting_the_call_through(self):
        c = self.client()
        with mock.patch.object(budget, "check_llm", side_effect=RuntimeError("locked")):
            with self.assertRaises(llm_runner.LlmError) as err:
                c.complete("x")
        self.assertEqual(err.exception.code, "budget")
        self.assertEqual(self.calls, [])

    def test_a_ledger_that_cannot_be_written_keeps_the_answer_then_refuses_the_next_call(self):
        c = self.client()
        with mock.patch("core.cost.record_usage", side_effect=RuntimeError("disk full")):
            self.assertEqual(c.complete("x").text, "OK")          # the paid answer is not lost
        with self.assertRaises(llm_runner.LlmError) as err:
            c.complete("y")
        self.assertEqual(err.exception.code, "budget")
        self.assertEqual(len(self.calls), 1)

    def test_a_cut_answer_is_recorded_and_reported_not_asked_again(self):
        c = self.client(stop="max_tokens")
        with self.assertRaises(llm_runner.LlmError) as err:
            llm_runner.ask_json(c, "json please", lambda o: o)
        self.assertEqual(err.exception.code, "truncated")
        self.assertEqual(len(self.calls), 1)                      # no second paid call for the same cut
        self.assertEqual(len(self.rows()), 2)                     # but the tokens are in the ledger

    def test_background_workers_get_a_ledger_bound_client(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-test"}):
            self.assertEqual(llm_runner.ledger_factory(self.db)().ledger, self.db)

    def test_no_code_path_builds_a_claude_client_without_the_ledger(self):
        bare = []
        for d in ("core", "dashboard", "tools"):
            for f in glob.glob(os.path.join(ROOT, d, "**", "*.py"), recursive=True):
                with open(f, encoding="utf-8") as fh:
                    # a call without the ledger, or the bare function used as a default factory
                    if re.search(r"client_from_env\(\s*\)|llm_runner\.client_from_env\b(?!\()", fh.read()):
                        bare.append(f)
        self.assertEqual(bare, [])


if __name__ == "__main__":
    unittest.main()
