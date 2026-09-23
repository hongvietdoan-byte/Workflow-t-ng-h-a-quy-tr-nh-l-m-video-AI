import os
import tempfile
import threading
import time
import unittest

from core import autopilot, perf
from core.adapters.http import ApiClient, HttpResponse
from core.db import connect
from core.music import MockAudioProvider
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider, ProviderError
from core.runner import ImageRunner, VideoRunner
from core.throttle import THROTTLE, Throttle
from tests.test_perf_queue import fake_render, make_projects, wait


class CappedVideo:
    """Shared mock provider that behaves like a service allowing only `cap` tasks in flight (HTTP 429 beyond that)."""
    name = "capped-mock"

    def __init__(self, cap):
        self.cap, self.inner, self.lock = cap, MockVideoProvider(polls_to_finish=3), threading.Lock()
        self.inflight, self.rejected, self.peak = set(), 0, 0

    def usage_info(self, *a, **k):
        return self.inner.usage_info(*a, **k)

    def submit(self, *a, **k):
        with self.lock:
            if len(self.inflight) >= self.cap:
                self.rejected += 1
                raise ProviderError("rate limited (HTTP 429)", code="rate_limited", transient=True)
            task = self.inner.submit(*a, **k)
            self.inflight.add(task)
            self.peak = max(self.peak, len(self.inflight))
            return task

    def status(self, task_id):
        with self.lock:
            st = self.inner.status(task_id)
            if st.state != "running":
                self.inflight.discard(task_id)
            return st

    def download(self, *a, **k):
        return self.inner.download(*a, **k)

    def cancel(self, *a, **k):
        return self.inner.cancel(*a, **k)


class ThrottleUnitTests(unittest.TestCase):
    def test_grows_after_clean_successes_and_halves_on_rate_limit(self):
        t = Throttle(start=2, maximum=6, up_every=3)
        for _ in range(3):
            t.on_success("video_gen")
        self.assertEqual(t.limit("video_gen"), 3)
        for _ in range(30):
            t.on_success("video_gen")
        self.assertEqual(t.limit("video_gen"), 6)                     # never above the maximum
        t.on_rate_limited("video_gen")
        self.assertEqual(t.limit("video_gen"), 3)
        t.on_rate_limited("video_gen")
        t.on_rate_limited("video_gen")
        self.assertEqual(t.limit("video_gen"), 1)                     # never below one
        self.assertEqual(t.info("video_gen")["hits"], 3)
        self.assertEqual(t.limit("image_gen"), 2)                     # kinds are independent
        self.assertFalse(t.allow("video_gen", 1))
        self.assertTrue(Throttle(start=2, maximum=0).allow("video_gen", 999))   # disabled

    def test_http_429_is_a_wait_not_a_failure(self):
        client = ApiClient("http://x", "tok", "ua", transport=lambda *a: HttpResponse(429, b"slow down"))
        with self.assertRaises(ProviderError) as ctx:
            client.get("/anything")
        self.assertTrue(ctx.exception.transient)
        self.assertEqual(ctx.exception.code, "rate_limited")


class OnePassSubmitTests(unittest.TestCase):
    """One click on "Submit" must fill the allowed number of slots (it used to count each job it had just started twice)."""
    def setUp(self):
        THROTTLE.reset()
        self._saved = (THROTTLE.start, THROTTLE.maximum, THROTTLE.up_every)
        THROTTLE.start, THROTTLE.maximum, THROTTLE.up_every = 4, 20, 5

    def tearDown(self):
        THROTTLE.start, THROTTLE.maximum, THROTTLE.up_every = self._saved
        THROTTLE.reset()

    def test_a_single_pass_submits_as_many_jobs_as_the_limit_allows(self):
        tmp = tempfile.mkdtemp()
        p = Pipeline(connect(os.path.join(tmp, "m.sqlite")))
        pid = p.create_project("slots")
        for i in range(1, 8):
            sid = p.create_scene(pid, i, f"s{i}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", ('{"image_prompt": "a hero"}', sid))
            p.conn.commit()
            p.create_job(sid, "image_gen")
        runner = ImageRunner(p, MockImageProvider(polls_to_finish=5), os.path.join(tmp, "projects"), max_concurrent=10)
        self.assertEqual(runner.submit_pending(pid), 4)                     # the limit (4), not 2
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs WHERE state='running'").fetchone()[0], 4)
        self.assertEqual(runner.submit_pending(pid), 0)                     # full: the rest waits for a free slot


class LearningTests(unittest.TestCase):
    def setUp(self):
        THROTTLE.reset()
        self._saved = (THROTTLE.start, THROTTLE.maximum, THROTTLE.up_every)
        THROTTLE.start, THROTTLE.maximum, THROTTLE.up_every = 8, 20, 4   # start far above what the "service" allows

    def tearDown(self):
        THROTTLE.start, THROTTLE.maximum, THROTTLE.up_every = self._saved
        THROTTLE.reset()

    def test_a_service_that_allows_three_is_learned_without_losing_a_job(self):
        tmp = tempfile.mkdtemp()
        db, data = os.path.join(tmp, "m.sqlite"), os.path.join(tmp, "projects")
        p, ids = make_projects(db, 6)
        service = CappedVideo(cap=3)

        def factory(pipeline, data_dir):
            from core import llm_runner
            return autopilot.Context(data_dir, ImageRunner(pipeline, MockImageProvider(polls_to_finish=1), data_dir),
                                     VideoRunner(pipeline, service, data_dir), llm_runner.MockLlm(), MockAudioProvider(), fake_render)

        mgr = autopilot.Manager(db, data, factory, poll_sec=0.01, max_parallel=6)
        for i in ids:
            autopilot.set_gates(p, i, {"bible": False})   # unattended run (checkpoint: test_v2)
            autopilot.start(p, i)
            mgr.start(i)
        self.assertTrue(wait(db, ids, ("done", "needs_attention", "error", "stopped"), 120))
        p = Pipeline(connect(db))
        self.assertEqual([autopilot.status(p, i)["state"] for i in ids], ["done"] * 6)
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs WHERE state='failed'").fetchone()[0], 0)   # 429 never burns a retry
        self.assertGreater(service.rejected, 0)                        # it did bump into the ceiling ...
        self.assertLessEqual(service.peak, 3)                          # ... and never exceeded it
        self.assertGreater(THROTTLE.info("video_gen")["hits"], 0)
        self.assertLess(THROTTLE.limit("video_gen"), 8)                 # learned that 8 is too many
        self.assertIn("video_gen", perf.snapshot(p.conn)["learned"])


if __name__ == "__main__":
    unittest.main()
