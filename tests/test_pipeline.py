import unittest

from core.db import connect
from core.pipeline import Pipeline, PipelinePaused
from core.states import InvalidTransition, JobState

GOOD = {"character": 0.95, "hands_face": 0.9, "composition": 0.9, "mood": 0.9}
BAD = {"character": 0.5, "hands_face": 0.4, "composition": 0.6, "mood": 0.5}
FIX = "Draw Kelly with short white hair."            # the QC's concrete fix: what makes an automatic retry worth paying for (F5)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())

    def make_job(self, mode="human_qc", max_retry=3, threshold=0.85):
        pid = self.p.create_project("t", mode, threshold, max_retry)
        scene = self.p.create_scene(pid, 1, "S01")
        job = self.p.create_job(scene)
        self.p.start(job)
        self.p.succeed(job)
        return pid, scene, job

    def test_invalid_transition_rejected(self):
        pid = self.p.create_project("t")
        job = self.p.create_job(self.p.create_scene(pid, 1))
        with self.assertRaises(InvalidTransition):
            self.p.succeed(job)

    def test_human_qc_always_waits_even_for_high_score(self):
        _, _, job = self.make_job("human_qc")
        self.assertEqual(self.p.apply_qc(job, GOOD), "pending_review")
        self.assertEqual(self.p.state(job), JobState.PENDING_REVIEW)
        self.p.approve(job, "user")
        self.assertEqual(self.p.state(job), JobState.APPROVED)

    def test_auto_mode_approves_above_threshold(self):
        _, _, job = self.make_job("auto")
        self.assertEqual(self.p.apply_qc(job, GOOD), "approved")
        row = self.p.conn.execute("SELECT reviewer_type, decision FROM review_log").fetchone()
        self.assertEqual((row["reviewer_type"], row["decision"]), ("ai_agent", "approve"))

    def test_auto_mode_rejects_below_threshold_and_spawns_retry(self):
        pid, scene, job = self.make_job("auto")
        self.assertEqual(self.p.apply_qc(job, BAD, issues=FIX), "rejected")
        self.assertEqual(self.p.state(job), JobState.REJECTED)
        child = self.p.conn.execute("SELECT * FROM jobs WHERE parent_job_id=?", (job,)).fetchone()
        self.assertEqual(child["state"], "queued")
        self.assertEqual(child["retry_count"], 1)
        self.assertEqual(child["retry_reason"], FIX)             # W4: only the fix goes to the model, no score line / Vietnamese note

    def test_user_reject_note_becomes_retry_reason(self):
        _, _, job = self.make_job("human_qc")
        self.p.apply_qc(job, GOOD)
        self.assertEqual(self.p.reject(job, "user", "Đổi sang áo đỏ"), "rejected")
        child = self.p.conn.execute("SELECT * FROM jobs WHERE parent_job_id=?", (job,)).fetchone()
        self.assertEqual(child["retry_reason"], "Đổi sang áo đỏ")

    def test_escalates_after_max_retry(self):
        pid, scene, job = self.make_job("auto", max_retry=2)
        results = []
        faults = [dict(GOOD, **{k: 0.1}) for k in ("character", "hands_face", "composition")]   # a different fault each time
        for n in range(3):
            results.append(self.p.apply_qc(job, faults[n], issues=f"fix {n}"))
            child = self.p.conn.execute(
                "SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()
            if child is None:
                break
            job = child["id"]
            self.p.start(job)
            self.p.succeed(job)
        self.assertEqual(results, ["rejected", "rejected", "needs_review"])   # the last try is kept for the person, flagged
        self.assertEqual(self.p.job(job)["escalated"], 1)

    def test_failed_job_retry_creates_child_and_respects_limit(self):
        pid = self.p.create_project("t", max_retry=1)
        job = self.p.create_job(self.p.create_scene(pid, 1))
        self.p.start(job)
        self.p.fail(job, "timeout")
        child = self.p.retry(job, "timeout")
        self.assertEqual(self.p.job(child)["retry_count"], 1)
        self.assertEqual(self.p.state(job), JobState.CANCELLED)
        self.p.start(child)
        self.p.fail(child, "timeout")
        self.assertIsNone(self.p.retry(child))
        self.assertEqual(self.p.job(child)["escalated"], 1)
        self.assertEqual(self.p.state(child), JobState.FAILED)

    def test_cannot_review_unfinished_job(self):
        pid = self.p.create_project("t")
        job = self.p.create_job(self.p.create_scene(pid, 1))
        with self.assertRaises(InvalidTransition):
            self.p.approve(job)

    def test_cancel_running_job_and_audit_trail(self):
        pid = self.p.create_project("t")
        job = self.p.create_job(self.p.create_scene(pid, 1))
        self.p.start(job)
        self.p.cancel(job)
        trail = [(h["from_state"], h["to_state"]) for h in self.p.history(job)]
        self.assertEqual(trail, [(None, "queued"), ("queued", "running"), ("running", "cancelled")])

    def test_mode_and_threshold_changes_take_effect(self):
        pid, _, job = self.make_job("human_qc")
        self.p.set_mode(pid, "auto")
        self.p.set_threshold(pid, 0.99)
        self.assertEqual(self.p.apply_qc(job, GOOD, issues=FIX), "rejected")

    def test_pause_blocks_start_and_cancel_all_stops_active(self):
        pid = self.p.create_project("t")
        scene = self.p.create_scene(pid, 1)
        a, b = self.p.create_job(scene), self.p.create_job(scene)
        self.p.start(a)
        self.p.set_paused(pid, True)
        with self.assertRaises(PipelinePaused):
            self.p.start(b)
        self.p.set_paused(pid, False)
        self.assertEqual(self.p.cancel_all_active(pid), 2)
        self.assertEqual({self.p.state(a), self.p.state(b)}, {JobState.CANCELLED})

    def test_review_zone_holds_middling_scores_for_a_human(self):
        pid, _, job = self.make_job("auto", threshold=0.85)
        self.p.set_review_floor(pid, 0.6)
        scores = {"character": 0.7, "hands_face": 0.7, "composition": 0.7, "mood": 0.7}
        self.assertEqual(self.p.apply_qc(job, scores), "pending_review")
        self.assertEqual(self.p.state(job), JobState.PENDING_REVIEW)
        row = self.p.conn.execute("SELECT DISTINCT auto_decision FROM qc_results").fetchone()
        self.assertEqual(row["auto_decision"], "review")
        self.p.approve(job, "user")

    def test_review_zone_still_rejects_below_floor_and_approves_above_threshold(self):
        pid, _, job = self.make_job("auto", threshold=0.85)
        self.p.set_review_floor(pid, 0.6)
        self.assertEqual(self.p.apply_qc(job, BAD, issues=FIX), "rejected")  # mean 0.5 < floor 0.6
        pid2, _, job2 = self.make_job("auto", threshold=0.85)
        self.p.set_review_floor(pid2, 0.6)
        self.assertEqual(self.p.apply_qc(job2, GOOD), "approved")

    def test_no_review_zone_keeps_old_behaviour(self):
        _, _, job = self.make_job("auto", threshold=0.85)
        self.assertIsNone(self.p.project(self.p.job(job)["project_id"])["qc_review_floor"])
        self.assertEqual(self.p.apply_qc(job, {"a": 0.7, "b": 0.7}, issues=FIX), "rejected")

    def test_no_paid_retry_without_a_fix_nor_for_the_same_fault_twice_nor_past_three(self):
        """F5 (user decision 2026-09-24): a retry must change the input; the same fault twice stops. S14.16 (04/10): was "past two" —
        a PICTURE gets at most 3 automatic retries (pipeline.AUTO_REGEN_LIMIT)."""
        _, _, job = self.make_job("auto", max_retry=5)
        self.assertEqual(self.p.apply_qc(job, BAD), "needs_review")                 # QC named nothing to fix: no identical resend
        self.assertEqual(self.p.job(job)["escalated"], 1)
        _, _, job = self.make_job("auto", max_retry=5)
        self.assertEqual(self.p.apply_qc(job, BAD, issues="fix A"), "rejected")
        child = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["id"]
        self.p.start(child)
        self.p.succeed(child)
        self.assertEqual(self.p.apply_qc(child, BAD, issues="fix B"), "needs_review")   # same criteria failed again
        self.assertIn("cùng lỗi", self.p.history(child)[-1]["note"])
        _, _, job = self.make_job("auto", max_retry=5)
        for n, fault in enumerate(["character", "hands_face", "composition"]):
            self.assertEqual(self.p.apply_qc(job, dict(GOOD, **{fault: 0.1}), issues=f"fix {n}"), "rejected")
            job = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["id"]
            self.p.start(job)
            self.p.succeed(job)
        self.assertEqual(self.p.apply_qc(job, dict(GOOD, mood=0.1), issues="fix 4"), "needs_review")   # 3 retries done
        self.assertIn("Also:", self.p.job(job)["retry_reason"])                         # the earlier fix is kept with the new one


if __name__ == "__main__":
    unittest.main()
