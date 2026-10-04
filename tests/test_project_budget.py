"""The project's budget by stage, locked by a person (core.project_budget, user 2026-09-28)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import cost, llm_runner, project_budget
from core.db import connect
from core.pipeline import Pipeline
from tests.test_v3 import kenta_project

ON = {"FEATURE_PROJECT_BUDGET": "1"}


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())

    def spend(self, kind, model, tier, qty, stage=None):
        cost.record_usage(self.p.conn, None, kind, "real", model, tier, qty, "unit", project_id=self.pid, stage=stage)

    @mock.patch.dict(os.environ, ON)
    def test_the_proposal_is_spent_plus_what_is_left_per_stage(self):
        self.spend("llm", "claude-sonnet-5", "output", 100000, stage="director")      # 1 USD of Director already spent
        prop = project_budget.propose(self.p, self.pid)
        self.assertEqual(set(prop["stages"]), set(project_budget.STAGES))
        d = prop["stages"]["claude_director"]
        self.assertAlmostEqual(d["spent"], 1.0, places=3)
        self.assertEqual(d["left_estimate"], 0.0)                                        # the Director has run
        self.assertAlmostEqual(prop["total"], round(sum(v["cap"] for v in prop["stages"].values()), 2), places=2)

    @mock.patch.dict(os.environ, ON)
    def test_locked_caps_warn_for_a_stage_and_only_a_person_raises_them_with_a_reason(self):
        # S14.16 (chính sách tiền 04/10): was "locked caps stop a stage" — past the line it now WARNS (warning), check never refuses
        project_budget.approve(self.p, self.pid, "a@x", {"stages": {k: {"cap": 0.5 if k == "images" else 1.0} for k in project_budget.STAGES},
                                                          "total": 5.5})
        self.assertIsNone(project_budget.warning(self.p.conn, self.pid, "images", 0.3))
        self.spend("image", "gpt-image-2.5-sunburst", "1152x2048", 9)                     # 9 pictures × ~0.052
        why = project_budget.warning(self.p.conn, self.pid, "images", 0.06)
        self.assertIn("khâu 'Ảnh'", why)
        self.assertIn("mức dự tính $0.50", why)
        self.assertIsNone(project_budget.check(self.p.conn, self.pid, "images", 0.06))
        with self.assertRaises(ValueError):
            project_budget.raise_cap(self.p.conn, self.pid, "images", 1.0, "a@x", "")      # a reason is required
        project_budget.raise_cap(self.p.conn, self.pid, "images", 1.0, "a@x", "vẽ lại 3 khung lỗi tay")
        self.assertIsNone(project_budget.warning(self.p.conn, self.pid, "images", 0.06))
        self.assertEqual(project_budget.get(self.p.conn, self.pid)["raises"][0]["why"], "vẽ lại 3 khung lỗi tay")

    @mock.patch.dict(os.environ, ON)
    def test_the_total_warns_even_when_a_stage_has_room(self):
        # S14.16: was "the total stops" — the total is a planned amount that warns
        project_budget.approve(self.p, self.pid, "a@x", {"stages": {k: {"cap": 10.0} for k in project_budget.STAGES}, "total": 1.0})
        self.spend("llm", "claude-sonnet-5", "output", 90000, stage="qc")                  # 0.9
        self.assertIn("TỔNG", project_budget.warning(self.p.conn, self.pid, "claude_qc", 0.2))
        self.assertIsNone(project_budget.check(self.p.conn, self.pid, "claude_qc", 0.2))

    def test_off_or_not_approved_no_project_lock(self):
        self.assertIsNone(project_budget.check(self.p.conn, self.pid, "images", 99.0))
        with mock.patch.dict(os.environ, ON):
            self.assertIsNone(project_budget.check(self.p.conn, self.pid, "images", 99.0))

    @mock.patch.dict(os.environ, ON)
    def test_the_automatic_run_waits_for_the_approved_budget_before_paying_for_pictures(self):
        from core import autopilot
        with self.assertRaises(autopilot._Wait) as w:
            autopilot._images_phase(self.p, self.pid, autopilot.Context(tempfile.mkdtemp(), None, None, llm_runner.MockLlm()))
        self.assertEqual(w.exception.gate, "budget")
        project_budget.set_target(self.p.conn, self.pid, 0.01)
        self.assertIn("VƯỢT mục tiêu", project_budget.gate_reason(self.p, self.pid))
        project_budget.approve(self.p, self.pid, "a@x")
        self.assertIsNone(project_budget.gate_reason(self.p, self.pid))

    @mock.patch.dict(os.environ, ON)
    def test_the_director_gets_the_target_as_an_input(self):
        from core import prompts
        self.assertNotIn("Ngân sách (người dùng đặt)", prompts.build_director_bundle(self.p, self.pid))
        project_budget.set_target(self.p.conn, self.pid, 12)
        self.assertIn("Ngân sách (người dùng đặt)", prompts.build_director_bundle(self.p, self.pid))

    def test_claude_stages_and_unverified_prices(self):
        self.assertEqual(project_budget.claude_stage("director"), "claude_director")
        self.assertEqual(project_budget.claude_stage("qc_agent"), "claude_qc")
        self.assertEqual(project_budget.claude_stage("video_analysis"), "claude_qc")
        self.assertEqual(project_budget.claude_stage("video"), "claude_qc")          # the clip QC (llm_runner stage "video")
        self.assertEqual(project_budget.claude_stage("motion"), "claude_motion")
        self.assertEqual(project_budget.claude_stage("style"), "claude_other")
        self.assertTrue(project_budget.unverified(cost.load_pricing(), "dreamina-seedance-2-0-fast-260128"))
        self.assertFalse(project_budget.unverified(cost.load_pricing(), "kling-v3-omni"))


class ClaudeProjectLockTests(unittest.TestCase):
    @mock.patch.dict(os.environ, ON)
    def test_a_claude_call_of_a_stage_over_its_locked_cap_is_sent_with_a_warning(self):
        # S14.16: was "is not sent" — the stage line only warns now (diag money_warning)
        from tests.test_llm_ledger import HttpResponse
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("t")
        project_budget.approve(p, pid, "a@x", {"stages": {k: {"cap": 0.01 if k == "claude_qc" else 5.0} for k in project_budget.STAGES},
                                                "total": 30.0})
        calls = []

        def send(*a):
            calls.append(1)
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": 10, "output_tokens": 10}}).encode())
        c = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, sleep=lambda s: None, ledger=db)
        with llm_runner.tagged("qc_agent", pid):
            c.converse([{"role": "user", "content": [{"type": "text", "text": "x"}]}], [], max_tokens=4000)   # worst ≈ 0.04 > 0.01
        self.assertEqual(len(calls), 1)
        warns = [r[0] for r in p.conn.execute("SELECT message FROM diag_events WHERE code='money_warning'")]
        self.assertTrue(any("Claude — QC" in w for w in warns), warns)


class UnknownPriceTests(unittest.TestCase):
    """T6 (S14.1 A1): a price the table does not know is not 0. S14.16: a locked project WARNS about it (estimated high, sent)."""
    def setUp(self):
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        self.p = Pipeline(connect(db))
        self.pid = self.p.create_project("t")

    def warned(self) -> str:
        return " ".join(r[0] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='money_warning'"))

    def lock(self):
        project_budget.approve(self.p, self.pid, "a@x", {"stages": {k: {"cap": 5.0} for k in project_budget.STAGES}, "total": 30.0})

    @mock.patch.dict(os.environ, ON)
    def test_none_is_warned_when_locked_and_points_to_the_price_table(self):
        self.lock()
        self.assertIsNone(project_budget.check(self.p.conn, self.pid, "images", None))      # S14.16: never refused
        why = project_budget.warning(self.p.conn, self.pid, "images", None)
        self.assertIsNotNone(why)
        self.assertIn("thiếu giá", why.lower())
        self.assertIn("Bảng giá", why)

    @mock.patch.dict(os.environ, ON)
    def test_none_passes_when_the_project_is_not_locked(self):
        self.assertIsNone(project_budget.check(self.p.conn, self.pid, "images", None))

    @mock.patch.dict(os.environ, ON)
    def test_an_unpriced_ledger_row_is_not_counted_as_zero_silently(self):
        self.lock()
        cost.record_usage(self.p.conn, None, "image", "deepix", "model-without-price", "1k", 1, "image", project_id=self.pid)
        self.assertEqual(project_budget.unpriced_by_stage(self.p.conn, self.pid)["images"], 1)
        why = project_budget.warning(self.p.conn, self.pid, "images", 0.05)               # S14.16: a warning, not a refusal
        self.assertIsNotNone(why)
        self.assertIn("1 dòng sổ chi", why.lower())
        self.assertIsNone(project_budget.warning(self.p.conn, self.pid, "videos", 0.05))    # another stage is not concerned

    @mock.patch.dict(os.environ, ON)
    def test_the_image_runner_sends_a_model_without_price_in_a_locked_project_with_a_warning(self):
        # S14.16: was "refuses" — estimated high and warned (diag), not stopped
        from core.providers import MockImageProvider
        from core.runner import ImageRunner

        class Fake(MockImageProvider):
            name = "deepix-fake"

            def usage_info(self, model=None):
                return "model-without-price", "1k"
        self.lock()
        r = ImageRunner(self.p, Fake(), tempfile.mkdtemp())
        self.assertIsNone(r._over_budget({"project_id": self.pid}, ("prompt", []), {}))
        self.assertIn("model-without-price", self.warned())

    @mock.patch.dict(os.environ, ON)
    def test_the_video_runner_sends_a_model_without_price_in_a_locked_project_with_a_warning(self):
        # S14.16: was "refuses" — estimated high and warned (diag), not stopped
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner

        class Fake(MockVideoProvider):
            name = "clipai-fake"

            def usage_info(self, model=None, duration=5, resolution=None):
                return "video-model-without-price", "720p", duration
        self.lock()
        r = VideoRunner(self.p, Fake(), tempfile.mkdtemp())
        self.assertIsNone(r._over_budget({"project_id": self.pid}, ("a.png", "prompt", None, 5, "video-model-without-price"), {}))
        self.assertIn("video-model-without-price", self.warned())


if __name__ == "__main__":
    unittest.main()
