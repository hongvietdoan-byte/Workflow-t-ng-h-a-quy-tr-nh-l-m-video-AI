"""Kế hoạch V4, GĐ1 — M3 (one poller per project), the spending lock, and one Blender at a time on the computer."""
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from core import budget, plates3d
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner, _turn
from core.throttle import THROTTLE


class SlowStatus(MockImageProvider):
    """Holds each status question until released, to put two pollers in the same moment."""
    def __init__(self):
        super().__init__(polls_to_finish=1)
        self.gate = threading.Event()
        self.calls = 0

    def status(self, task_id):
        self.calls += 1
        self.gate.wait(5)
        return super().status(task_id)


def project(tmp, jobs=1):
    p = Pipeline(connect(os.path.join(tmp, "m.sqlite")))
    pid = p.create_project("m3")
    for i in range(1, jobs + 1):
        sid = p.create_scene(pid, i, f"s{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", ('{"image_prompt": "a hero"}', sid))
        p.conn.commit()
        p.create_job(sid, "image_gen")
    return p, pid


class OnePollerTests(unittest.TestCase):
    def setUp(self):
        THROTTLE.reset()

    def test_a_second_thread_skips_while_the_project_is_being_polled(self):
        tmp = tempfile.mkdtemp()
        p, pid = project(tmp)
        provider = SlowStatus()
        ImageRunner(p, provider, os.path.join(tmp, "projects")).submit_pending(pid)
        errors = []

        def autopilot_poll():                                    # the autopilot thread, with its own connection
            try:
                mine = Pipeline(connect(os.path.join(tmp, "m.sqlite")))
                ImageRunner(mine, provider, os.path.join(tmp, "projects")).poll_once(pid)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        first = threading.Thread(target=autopilot_poll)
        first.start()
        time.sleep(0.2)                                          # the first poll is now waiting inside provider.status
        other = Pipeline(connect(os.path.join(tmp, "m.sqlite")))   # the dashboard tab has its own connection
        second = ImageRunner(other, provider, os.path.join(tmp, "projects")).poll_once(pid)
        self.assertEqual(second, {"succeeded": 0, "failed": 0, "retried": 0, "running": 1})
        provider.gate.set()
        first.join(5)
        self.assertEqual(errors, [])
        self.assertEqual(provider.calls, 1)                       # asked once, downloaded once
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs WHERE state='succeeded'").fetchone()[0], 1)

    def test_the_lock_is_per_project_and_reentrant(self):
        a, b = _turn(101, "image_gen"), _turn(102, "image_gen")
        self.assertIsNot(a, b)
        self.assertIs(a, _turn(101, "image_gen"))
        self.assertIsNot(a, _turn(101, "video_gen"))
        with a:
            self.assertTrue(a.acquire(blocking=False))            # nested call in the same thread
            a.release()

    def test_submit_is_skipped_while_another_thread_submits(self):
        tmp = tempfile.mkdtemp()
        p, pid = project(tmp, jobs=2)
        runner = ImageRunner(p, MockImageProvider(), os.path.join(tmp, "projects"))
        lock = _turn(pid, "image_gen")
        held = threading.Event()
        done = threading.Event()

        def hold():
            with lock:
                held.set()
                done.wait(5)

        t = threading.Thread(target=hold)
        t.start()
        held.wait(5)
        self.assertEqual(runner.submit_pending(pid), 0)
        done.set()
        t.join(5)
        self.assertEqual(runner.submit_pending(pid), 2)


class SpendLockTests(unittest.TestCase):
    def test_limit_check_and_ledger_write_happen_under_one_lock(self):
        tmp = tempfile.mkdtemp()
        p, pid = project(tmp)
        runner = ImageRunner(p, MockImageProvider(), os.path.join(tmp, "projects"))
        seen = []
        real = runner._record_usage

        def record(job, args, kwargs=None):
            seen.append(budget.SPEND_LOCK._is_owned())             # noqa: SLF001 - RLock knows its owner
            return real(job, args, kwargs)

        runner._record_usage = record
        runner._over_budget = lambda job, args, kwargs: (seen.append(budget.SPEND_LOCK._is_owned()), None)[1]
        self.assertEqual(runner.submit_pending(pid), 1)
        self.assertEqual(seen, [True, True])


class BlenderQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"PLATES3D_LOCK": os.path.join(self.tmp, "blender.lock")})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_second_render_waits_for_the_first(self):
        # F5-B (09/10): was flaky on a busy machine — a fixed time.sleep(0.2) assumed the second thread had reached its wait loop
        # by then (waiting[-1] → IndexError when it had not). Now each step waits for an Event set by the thread itself.
        order = []
        release, first_in, second_waits = threading.Event(), threading.Event(), threading.Event()

        def first():
            with plates3d.blender_turn():
                order.append("first in")
                first_in.set()
                release.wait(60)
                order.append("first out")

        t = threading.Thread(target=first)
        t.start()
        self.assertTrue(first_in.wait(60))
        waiting = []

        def wait_step(_s):
            waiting.append(plates3d.queue_length())
            second_waits.set()                                    # the second render is inside its wait loop, lock still taken
            time.sleep(0.01)

        def second():
            with plates3d.blender_turn(sleep=wait_step):
                order.append("second in")

        t2 = threading.Thread(target=second)
        t2.start()
        self.assertTrue(second_waits.wait(60))
        self.assertEqual(order, ["first in"])
        self.assertEqual(waiting[0], 1)                           # the dashboard can show "1 render waiting"
        release.set()
        t.join(60)
        t2.join(60)
        self.assertFalse(t.is_alive() or t2.is_alive())
        self.assertEqual(order, ["first in", "first out", "second in"])
        self.assertEqual(plates3d.queue_length(), 0)
        self.assertFalse(os.path.exists(plates3d.lock_path()))

    def test_a_lock_left_by_a_dead_blender_is_taken_over(self):
        path = plates3d.lock_path()
        with open(path, "w") as f:
            f.write("999 old")
        old = time.time() - plates3d.LOCK_STALE_SEC - 5
        os.utime(path, (old, old))
        with plates3d.blender_turn(wait=1):
            self.assertTrue(os.path.exists(path))

    def test_gives_up_with_a_clear_message(self):
        with open(plates3d.lock_path(), "w") as f:
            f.write("busy")
        with self.assertRaises(plates3d.Plates3DError) as ctx:
            with plates3d.blender_turn(wait=0.05, sleep=lambda s: time.sleep(0.02)):
                pass
        self.assertIn("Blender đang bận", str(ctx.exception))

    def test_two_renders_in_the_same_second_get_their_own_folder(self):
        self.assertNotEqual(plates3d.out_dir(self.tmp, "Tháp Đồng Hồ"), plates3d.out_dir(self.tmp, "Tháp Đồng Hồ"))


if __name__ == "__main__":
    unittest.main()
