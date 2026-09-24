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


class CacheAndImageTests(unittest.TestCase):
    """GĐ-C2/C3: repeating prompt parts are cached (priced x1.25 once, then x0.1) and pictures are sent at a capped size."""

    def test_the_cached_parts_go_first_then_pictures_then_the_changing_part(self):
        from PIL import Image
        big = os.path.join(tempfile.mkdtemp(), "big.png")
        Image.new("RGB", (3000, 1500), (200, 10, 10)).save(big)
        calls = []
        c = llm_runner.AnthropicClient("sk-test", transport=_transport(calls), sleep=lambda s: None)
        c.complete("RULES" + llm_runner.CACHE_BREAK + "BIBLE" + llm_runner.CACHE_BREAK + "SHOT", [("Ảnh:", big)])
        blocks = calls[0]["messages"][0]["content"]
        self.assertEqual([b.get("text") for b in blocks[:2]], ["RULES", "BIBLE"])
        self.assertTrue(all(b["cache_control"] == {"type": "ephemeral"} for b in blocks[:2]))
        self.assertEqual(blocks[-1], {"type": "text", "text": "SHOT"})
        img = next(b for b in blocks if b["type"] == "image")
        import base64
        import io
        size = Image.open(io.BytesIO(base64.b64decode(img["source"]["data"]))).size
        self.assertEqual(max(size), llm_runner.IMAGE_EDGE)

    def test_cache_tokens_are_priced_from_the_input_price(self):
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)

        def send(method, url, headers, body, timeout):
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "OK"}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": 0, "output_tokens": 0,
                                                           "cache_creation_input_tokens": 1_000_000,
                                                           "cache_read_input_tokens": 1_000_000}}).encode())
        llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, ledger=db).complete("x")
        self.assertAlmostEqual(budget.llm_spent(conn), 2.0 * 1.25 + 2.0 * 0.1)

    def test_other_clients_and_people_never_see_the_cache_mark(self):
        text = "A" + llm_runner.CACHE_BREAK + "B"
        self.assertNotIn("<<<cache>>>", llm_runner.plain(text))
        seen = []
        cli = llm_runner.ClaudeCliClient(run=lambda args, **k: seen.append(k["input"]) or mock.Mock(
            returncode=0, stdout=json.dumps({"result": "OK", "usage": {}}), stderr=""))
        cli.complete(text)
        self.assertNotIn("<<<cache>>>", seen[0])

    def test_the_image_qc_prompt_marks_rules_and_project_parts_for_caching(self):
        from core import prompts
        from tests.test_v3 import kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (pid,)).fetchone()[0]
        parts = prompts.build_qc_bundle(p, sid).split(prompts.CACHE_BREAK)
        self.assertEqual(len(parts), 3)
        self.assertIn("Character Bible", parts[1])
        self.assertIn("Thông số cảnh", parts[2])


if __name__ == "__main__":
    unittest.main()
