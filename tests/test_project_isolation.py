"""Sau dự án Khủng Long Đỏ (08/10) — phân luồng từng dự án, phần không động tiền:
(b) khóa Blender cả máy: khóa cũ của một lượt render bị ngắt (PID chết / quá hạn) tự gỡ + diag; Dashboard thấy ai giữ khóa, chờ bao lâu.
(c) job ảnh/clip đang chạy ở nhà cung cấp vẫn được hỏi trạng thái và tải về khi KHÔNG có tab nào mở và dự án không chạy tự động —
    vòng hỏi nền, mỗi dự án tách biệt, lỗi một dự án không chặn dự án khác."""
import json
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

from core import bg_poll, plates3d
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider, TaskStatus
from core.runner import ImageRunner


class BlenderLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"PLATES3D_LOCK": os.path.join(self.tmp, "blender.lock")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_lock_names_its_project_and_the_dashboard_can_read_it(self):
        with plates3d.blender_turn(owner="dự án #22"):
            h = plates3d.holder()
            self.assertEqual(h["owner"], "dự án #22")
            self.assertEqual(h["pid"], os.getpid())
            self.assertTrue(h["alive"])
            self.assertIn("dự án #22", plates3d.status_text())
        self.assertIsNone(plates3d.holder())
        self.assertEqual(plates3d.status_text(), "")

    def test_a_lock_of_a_dead_process_is_taken_over_at_once_and_reported(self):
        path = plates3d.lock_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"pid": 424242, "owner": "dự án #7", "since_ts": time.time() - 30}, f)     # fresh, but its process is gone
        seen = []
        with mock.patch.object(plates3d, "pid_alive", lambda pid: pid != 424242):
            t0 = time.time()
            with plates3d.blender_turn(wait=60, owner="dự án #8", report=lambda msg, code, owner: seen.append((code, owner, msg))):
                self.assertEqual(plates3d.holder()["owner"], "dự án #8")
            self.assertLess(time.time() - t0, 5)                  # not the 1-hour stale age: the dead PID is enough
        self.assertEqual(seen[0][0], "blender_lock_stale")
        self.assertEqual(seen[0][1], "dự án #7")
        self.assertIn("424242", seen[0][2])
        with open(path + ".log", encoding="utf-8") as fh:
            self.assertIn("blender_lock_stale", fh.read())

    def test_an_old_format_lock_of_a_dead_process_is_taken_over(self):
        with open(plates3d.lock_path(), "w") as f:
            f.write("424243 2026-10-08 10:00:00")                  # written by the previous version of blender_turn
        with mock.patch.object(plates3d, "pid_alive", lambda pid: False):
            with plates3d.blender_turn(wait=1, report=lambda *a: None):
                pass

    def test_a_live_holder_is_waited_for_and_waiters_are_shown_with_their_time(self):
        path = plates3d.lock_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "owner": "dự án #3", "since_ts": time.time() - 125}, f)
        shown = []

        def sleep(_):
            shown.append(plates3d.status_text())
            time.sleep(0.02)
        with self.assertRaises(plates3d.Plates3DError):
            with plates3d.blender_turn(wait=0.1, sleep=sleep, owner="dự án #4"):
                pass
        self.assertTrue(os.path.exists(path))                     # a live holder is never removed
        self.assertIn("dự án #3", shown[-1])
        self.assertIn("2 phút", shown[-1])
        self.assertIn("dự án #4", shown[-1])                      # who waits
        self.assertEqual(plates3d.waiters(), [])

    def test_pid_alive_knows_this_process(self):
        self.assertTrue(plates3d.pid_alive(os.getpid()))
        self.assertFalse(plates3d.pid_alive(0))

    def test_render_puts_the_project_on_the_lock(self):
        seen = {}

        def fake(cfg, blender, run, timeout):
            seen["owner"] = plates3d.holder()["owner"]
            return {}
        with mock.patch.object(plates3d, "_render", fake):
            plates3d.render({"owner": "dự án #22", "out_dir": self.tmp})
        self.assertEqual(seen["owner"], "dự án #22")


class _Done(MockImageProvider):
    """A provider whose every task is finished: status says so, download writes a small file."""
    def status(self, task_id):
        if task_id.startswith("boom"):
            raise RuntimeError("provider down for this one")
        return TaskStatus("succeeded")

    def download(self, task_id, dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(b"\x89PNG\r\n")
        return dest


class BackgroundPollTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "m.sqlite")
        self.conn = connect(self.db)
        self.p = Pipeline(self.conn)
        self.data = os.path.join(self.dir, "projects")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def running_job(self, pid, external_id):
        sid = self.p.create_scene(pid, 1, "S1")
        jid = self.p.create_job(sid, "image_gen")
        self.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (external_id, jid))
        self.p.start(jid)
        return jid

    def test_without_a_page_and_without_autopilot_nothing_else_polls(self):
        # the only pollers are the page's fragment (dashboard/widgets.py) and the autopilot thread: the background round is the third
        pid = self.p.create_project("đóng tab")
        self.running_job(pid, "img-0")
        self.assertEqual(bg_poll.projects_with_running(self.conn), [(pid, "image")])

    def test_a_closed_tab_project_gets_its_picture_downloaded(self):
        pid = self.p.create_project("đóng tab")
        jid = self.running_job(pid, "img-1")
        res = bg_poll.poll_all(self.conn, lambda conn, kind: ImageRunner(Pipeline(conn), _Done(), self.data))
        self.assertEqual(self.p.job(jid)["state"], "succeeded")
        self.assertEqual(res[(pid, "image")]["succeeded"], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='bg_poll_done' AND project_id=?",
                                           (pid,)).fetchone()[0], 1)

    def test_one_broken_project_does_not_stop_the_other(self):
        bad = self.p.create_project("hỏng")
        good = self.p.create_project("tốt")
        self.running_job(bad, "x")
        jid = self.running_job(good, "img-2")

        def make(conn, kind):
            runner = ImageRunner(Pipeline(conn), _Done(), self.data)
            real = runner.poll_once

            def poll(project_id):
                if project_id == bad:
                    raise RuntimeError("database locked")
                return real(project_id)
            runner.poll_once = poll
            return runner
        res = bg_poll.poll_all(self.conn, make)
        self.assertIn("error", res[(bad, "image")])
        self.assertEqual(self.p.job(jid)["state"], "succeeded")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='bg_poll_error' AND project_id=?",
                                           (bad,)).fetchone()[0], 1)

    def test_no_provider_is_said_not_hidden(self):
        pid = self.p.create_project("không khóa API")
        self.running_job(pid, "img-3")
        res = bg_poll.poll_all(self.conn, lambda conn, kind: None)
        self.assertEqual(res[(pid, "image")], {"skipped": "no_provider"})

    def test_it_never_sends_anything_new(self):
        pid = self.p.create_project("không tiêu tiền")
        self.running_job(pid, "img-4")
        sid = self.p.create_scene(pid, 2, "S2")
        queued = self.p.create_job(sid, "image_gen")
        runner = ImageRunner(Pipeline(self.conn), _Done(), self.data)
        runner.submit_pending = mock.Mock(side_effect=AssertionError("background round must not send"))
        bg_poll.poll_all(self.conn, lambda conn, kind: runner)
        self.assertEqual(self.p.job(queued)["state"], "queued")

    def test_the_loop_runs_rounds_until_stopped_and_survives_a_crash(self):
        rounds = []

        def one_round(db_path):
            rounds.append(db_path)
            if len(rounds) == 1:
                raise RuntimeError("first round crashed")
        stop = bg_poll.loop(self.db, one_round=one_round, interval=0, max_rounds=3)
        self.assertEqual(len(rounds), 3)
        self.assertEqual(stop, 3)


if __name__ == "__main__":
    unittest.main()
