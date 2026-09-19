import os
import tempfile
import unittest

from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import Pipeline
from core.providers import MockVideoProvider
from core.runner import VideoRunner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.dir = tempfile.mkdtemp()
        self.pid = self.p.create_project("t", max_retry=2)

    def scene_ready_for_video(self, idx, prompt="slow push-in"):
        scene = self.p.create_scene(self.pid, idx, f"S{idx}")
        img = self.p.create_job(scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": idx, "motion_prompt": prompt}]})
        approve_motion_prompt(self.p, scene)
        return scene

    def video_job(self, scene):
        return self.p.create_job(scene, "video_gen")

    def runner(self, **kw):
        return VideoRunner(self.p, MockVideoProvider(**kw), self.dir, max_concurrent=2)

    def test_full_success_downloads_ordered_files(self):
        jobs = [self.video_job(self.scene_ready_for_video(i)) for i in (1, 2)]
        r = self.runner(polls_to_finish=2)
        r.run(self.pid, interval=0, sleep=lambda s: None)
        self.assertEqual({self.p.state(j).value for j in jobs}, {"succeeded"})
        files = sorted(os.listdir(os.path.join(self.dir, str(self.pid), "videos")))
        self.assertEqual(files, ["01.mp4", "02.mp4"])

    def test_concurrency_limit(self):
        for i in (1, 2, 3):
            self.video_job(self.scene_ready_for_video(i))
        r = self.runner(polls_to_finish=5)
        self.assertEqual(r.submit_pending(self.pid), 2)
        self.assertEqual(r.submit_pending(self.pid), 0)

    def test_risk_control_is_logged_and_not_retried(self):
        job = self.video_job(self.scene_ready_for_video(1, "Wonder Woman flies"))
        self.runner().run(self.pid, interval=0, sleep=lambda s: None)
        self.assertEqual(self.p.state(job).value, "failed")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM content_moderation_failures").fetchone()[0], 1)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], 1)

    def test_transient_error_is_retried_and_then_succeeds(self):
        job = self.video_job(self.scene_ready_for_video(1))
        self.runner(polls_to_finish=1, transient_failures=1).run(self.pid, interval=0, sleep=lambda s: None)
        rows = self.p.conn.execute("SELECT id, state, parent_job_id FROM jobs WHERE type='video_gen'"
                                   " ORDER BY id").fetchall()
        self.assertEqual([r["state"] for r in rows], ["cancelled", "succeeded"])
        self.assertEqual(rows[1]["parent_job_id"], job)

    def test_transient_errors_exhaust_retries_and_escalate(self):
        self.video_job(self.scene_ready_for_video(1))
        self.runner(polls_to_finish=1, transient_failures=10).run(self.pid, interval=0, sleep=lambda s: None)
        last = self.p.conn.execute("SELECT * FROM jobs WHERE type='video_gen' ORDER BY id DESC").fetchone()
        self.assertEqual((last["state"], last["escalated"]), ("failed", 1))

    def test_missing_inputs_fail_fast(self):
        scene = self.p.create_scene(self.pid, 1, "S1")
        job = self.video_job(scene)
        self.runner().submit_pending(self.pid)
        self.assertEqual(self.p.state(job).value, "failed")

    def test_paused_project_submits_nothing_and_cancel_hits_provider(self):
        job = self.video_job(self.scene_ready_for_video(1))
        r = self.runner(polls_to_finish=9)
        self.p.set_paused(self.pid, True)
        self.assertEqual(r.submit_pending(self.pid), 0)
        self.p.set_paused(self.pid, False)
        r.submit_pending(self.pid)
        r.cancel_job(job)
        self.assertEqual(r.provider.cancelled, ["mock-1"])
        self.assertEqual(self.p.state(job).value, "cancelled")


if __name__ == "__main__":
    unittest.main()
