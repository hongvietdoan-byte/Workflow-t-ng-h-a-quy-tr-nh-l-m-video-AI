"""C4 (2026-09-24): effort and answer length per stage. The Director of a 58-second per-shot script ran out of 32k tokens at the
default effort (thinking counts against max_tokens): it now thinks at 'medium' with room for 64k, QC at 'low'; a cut answer keeps its
text (paid for) so one can see where the tokens went."""
import json
import os
import unittest
from unittest import mock

from core import llm_runner
from core.db import connect
from core.pipeline import Pipeline
from tests.test_llm_ledger import _transport


class EffortTests(unittest.TestCase):
    def client(self, calls, model="claude-sonnet-5", stop="end_turn"):
        return llm_runner.AnthropicClient("sk-test", model, transport=_transport(calls, stop), sleep=lambda s: None)

    def test_each_stage_gets_its_effort_and_length(self):
        calls = []
        c = self.client(calls)
        with llm_runner.tagged("director"):
            c.complete("plan")
        with llm_runner.tagged("qc"):
            c.complete("score")
        c.complete("other")
        self.assertEqual((calls[0]["output_config"], calls[0]["max_tokens"]), ({"effort": "medium"}, 64000))
        self.assertEqual((calls[1]["output_config"], calls[1]["max_tokens"]), ({"effort": "low"}, 16000))
        self.assertNotIn("output_config", calls[2])                           # unlisted stage: the API default
        self.assertEqual(calls[2]["max_tokens"], llm_runner.DEFAULT_MAX_TOKENS)

    def test_env_overrides_and_models_without_effort(self):
        calls = []
        with mock.patch.dict(os.environ, {"CLAUDE_EFFORT_DIRECTOR": "high", "CLAUDE_MAX_TOKENS_DIRECTOR": "50000"}):
            with llm_runner.tagged("director"):
                self.client(calls).complete("plan")
        self.assertEqual((calls[0]["output_config"], calls[0]["max_tokens"]), ({"effort": "high"}, 50000))
        with llm_runner.tagged("qc"):
            self.client(calls, model="claude-haiku-4-5").complete("x")
        self.assertNotIn("output_config", calls[1])                           # Haiku 4.5 refuses the effort field

    def test_a_cut_director_answer_is_kept_for_diagnosis(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        calls = []
        with mock.patch.object(llm_runner, "_director_references", return_value=[]), \
                mock.patch.object(llm_runner.prompts, "build_director_bundle", return_value="plan"):
            with self.assertRaises(llm_runner.LlmError) as e:
                llm_runner.run_director(p, pid, self.client(calls, stop="max_tokens"))
        self.assertEqual(e.exception.code, "truncated")
        self.assertIn("64000", str(e.exception))
        raw = json.loads(p.project(pid)["director_raw"])
        self.assertEqual((raw["truncated"], raw["text"]), (True, "OK"))


if __name__ == "__main__":
    unittest.main()
