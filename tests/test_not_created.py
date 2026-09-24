"""W12: ClipAI answers with a task id but never creates the task (real runs 2026-09-22/24: 16 such Kling tasks, absent from the
account's whole list). The status check must look past the first list page, report 'not created' quickly, and the runner must take
the submission out of the ledger and send the same attempt again — without using up a retry — at most 3 times in a row."""
import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from core.adapters.clipai import ClipAIVideoProvider
from core.adapters.http import HttpResponse
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import Pipeline
from core.runner import VideoRunner
from core.throttle import THROTTLE


class FakeClipAI:
    """omni-video-submit hands out T1, T2, ...; video-list serves `listed` (newest first) in pages of 50."""

    def __init__(self, filler=0):
        self.listed = [{"id": i, "task_id": f"OLD{i}", "task_status": 2, "video_url": "https://cdn.example/o.mp4"} for i in range(filler)]
        self.created, self.drop, self.list_calls = 0, 0, 0

    def __call__(self, method, url, headers, body, timeout):
        if "cdn.example" in url:
            return HttpResponse(200, b"VIDEO")
        if method == "POST":
            self.created += 1
            tid = f"T{self.created}"
            if self.drop > 0:
                self.drop -= 1                     # accepted and dropped: never shows up in the list
            else:
                self.listed.insert(0, {"id": 1000 + self.created, "task_id": tid, "task_status": 1})
            return HttpResponse(200, json.dumps({"code": 0, "data": {"tasks": [{"task_id": tid, "task_status": "submitted"}]}}).encode())
        self.list_calls += 1
        q = parse_qs(urlparse(url).query)
        page, size = int(q["page"][0]), int(q["pageSize"][0])
        return HttpResponse(200, json.dumps({"code": 0, "data": {"data": self.listed[(page - 1) * size: page * size]}}).encode())


class NotCreatedTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        p = self.p = Pipeline(connect())
        self.pid = p.create_project("t", max_retry=1)
        scene = p.create_scene(self.pid, 1, "S1")
        img = p.create_job(scene)
        p.start(img), p.succeed(img), p.approve(img)
        os.makedirs(os.path.join(self.dir, str(self.pid), "images"))
        with open(os.path.join(self.dir, str(self.pid), "images", f"job_{img}.png"), "wb") as f:
            f.write(b"png")
        store_motion_prompts(p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        approve_motion_prompt(p, scene)
        self.job = p.create_job(scene, "video_gen")
        self.fake = FakeClipAI()
        self.runner = VideoRunner(p, ClipAIVideoProvider("tok", "https://clipai.example", self.fake), self.dir)
        THROTTLE._limit.clear()

    def poll(self, n):
        for _ in range(n):
            self.runner.poll_once(self.pid)

    def ledger(self):
        return self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE kind='video'").fetchone()[0]

    def test_a_dropped_order_leaves_the_ledger_and_is_sent_again_without_using_a_retry(self):
        self.fake.drop = 1
        self.runner.submit_pending(self.pid)
        self.assertEqual(self.ledger(), 1)
        self.poll(6)
        self.assertEqual(self.p.state(self.job).value, "cancelled")
        self.assertEqual(self.ledger(), 0)                                  # nothing was created, nothing is counted
        new = self.p.conn.execute("SELECT * FROM jobs WHERE parent_job_id=?", (self.job,)).fetchone()
        self.assertEqual((new["state"], new["retry_count"]), ("queued", 0))  # same attempt, retries untouched
        self.assertIn("không tạo task", new["retry_reason"])
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='not_created'").fetchone())
        self.runner.submit_pending(self.pid)                                # the second send is created and finishes
        self.fake.listed[0].update(task_status=2, video_url="https://cdn.example/t2.mp4")
        self.poll(1)
        self.assertEqual(self.p.state(new["id"]).value, "succeeded")
        self.assertEqual(self.ledger(), 1)

    def test_a_provider_that_keeps_dropping_stops_after_three_resends(self):
        self.fake.drop = 10
        for _ in range(5):
            self.runner.submit_pending(self.pid)
            self.poll(6)
        jobs = self.p.conn.execute("SELECT * FROM jobs WHERE type='video_gen' ORDER BY id").fetchall()
        self.assertEqual(len(jobs), 4)                                      # the first send + 3 resends
        self.assertEqual((jobs[-1]["state"], jobs[-1]["escalated"]), ("failed", 1))
        self.assertEqual(self.fake.created, 4)
        self.assertEqual(self.ledger(), 0)

    def test_a_running_task_below_the_first_page_is_still_found(self):
        self.fake = FakeClipAI(filler=0)
        self.runner.provider.client.transport = self.fake
        self.runner.submit_pending(self.pid)
        self.fake.listed += [{"id": i, "task_id": f"NEW{i}", "task_status": 1} for i in range(70)]
        self.fake.listed.append(self.fake.listed.pop(0))                     # our task now sits on page 2
        self.poll(8)
        self.assertEqual(self.p.state(self.job).value, "running")          # not declared lost
        self.fake.listed[-1].update(task_status=2, video_url="https://cdn.example/t1.mp4")
        self.poll(1)
        self.assertEqual(self.p.state(self.job).value, "succeeded")

    def test_one_list_read_serves_all_jobs_of_a_round(self):
        provider = ClipAIVideoProvider("tok", "https://clipai.example", self.fake, list_ttl=60)
        self.fake.listed = [{"id": i, "task_id": f"X{i}", "task_status": 1} for i in range(3)]
        for i in range(3):
            provider.status(f"omni:X{i}")
        self.assertEqual(self.fake.list_calls, 1)


if __name__ == "__main__":
    unittest.main()


class CapTest(unittest.TestCase):
    def test_dropped_orders_do_not_use_up_the_autopilot_job_cap(self):
        from core import autopilot
        from core.runner import RESEND_NOTE
        p = Pipeline(connect())
        pid = p.create_project("t")
        scene = p.create_scene(pid, 1)
        first = p.create_job(scene, "video_gen")
        p.start(first), p.fail(first, "not_created: x")
        p.resend(first, RESEND_NOTE + " (1/3)")
        self.assertEqual(autopilot._video_sends(p, pid), 1)


class PersistentCountersTest(NotCreatedTest):
    """GĐ-A2: the dashboard builds a new provider on every poll — the counters live on the job rows, and a task hidden below many
    newer tasks (shared token, several projects) is never called 'not created' (it could still be running and billed)."""

    def fresh_runner(self):
        return VideoRunner(self.p, ClipAIVideoProvider("tok", "https://clipai.example", self.fake), self.dir)

    def test_a_new_provider_on_every_poll_still_reaches_the_verdict(self):
        self.fake.drop = 1
        self.fresh_runner().submit_pending(self.pid)
        for _ in range(6):
            self.fresh_runner().poll_once(self.pid)
        self.assertEqual(self.p.state(self.job).value, "cancelled")
        self.assertEqual(self.ledger(), 0)

    def test_a_task_hidden_under_newer_tasks_is_not_resent(self):
        import time as _t
        self.fake.drop = 1
        self.fresh_runner().submit_pending(self.pid)
        newer = int(_t.time()) + 3600
        self.fake.listed = [{"id": 10_000 + i, "task_id": f"N{i}", "task_status": 1, "created_at": newer} for i in range(800)]
        for _ in range(12):
            self.fresh_runner().poll_once(self.pid)
        job = self.p.job(self.job)
        self.assertEqual((job["state"], job["escalated"]), ("failed", 1))                 # stops for a person
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], 1)   # nothing resent
        self.assertEqual(self.ledger(), 1)                                               # may still be billed: kept in the ledger
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='not_found'").fetchone())
