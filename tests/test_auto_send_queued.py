"""Lỗi A + B (08/10, dự án #24): job ảnh người dùng đã bấm gửi bị runner._wait giữ (render nền 3D, ảnh neo…) nằm 'queued' mãi tới khi
có người bấm lại (job 578–584 nằm 22 phút sau khi render xong); lần bấm '▶ Gen ảnh' đầu chỉ xếp hàng mà không gửi.
Nay: core.bg_poll.send_ready tự gửi khi hết lý do chờ (qua đúng submit_pending của nút: tạm dừng, cổng tiền, khóa lượt…); lý do chờ thật
được ghi (runner.WAIT_REASONS) và màn Bước 2 nói 'sẽ tự gửi khi …'; một cú bấm chờ lượt gửi thay vì trả 0 im lặng."""
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from unittest import mock

from core import bg_poll, diag, place_refs, runner as R
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner


class AutoSendTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.data = os.path.join(self.dir, "projects")
        self.provider = MockImageProvider()
        self.pid = self.p.create_project("#24 thử")

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def job(self, pid=None, idx=1):
        pid = pid or self.pid
        sid = self.p.create_scene(pid, idx, f"S{idx}")
        self.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "a hero on a rooftop"}), sid))
        self.conn.commit()
        return self.p.create_job(sid, "image_gen")

    def make(self, conn, kind):
        return ImageRunner(Pipeline(conn), self.provider, self.data)

    def codes(self, code):
        return self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code=?", (code,)).fetchone()[0]

    def test_a_job_held_for_the_3d_render_is_sent_by_itself_once_the_render_is_there(self):
        jid = self.job()
        render = {"missing": True}
        started = []
        with mock.patch.object(place_refs, "enabled", lambda: True), \
                mock.patch.object(place_refs, "missing", lambda *a: render["missing"]), \
                mock.patch.object(place_refs, "ensure_async", lambda *a, **k: started.append(1) or True), \
                mock.patch.object(place_refs, "stale", lambda *a: {}), \
                mock.patch.object(place_refs, "needs", lambda *a: None), \
                mock.patch.object(place_refs, "shot_ref", lambda *a: None):
            bg_poll.send_ready(self.conn, self.make)                  # the render is not there: the job waits, and says why
            self.assertEqual(self.p.job(jid)["state"], "queued")
            self.assertTrue(started)
            self.assertIn("render nền 3D", R.wait_reason(jid))
            self.assertIn("sẽ tự gửi", R.wait_reason(jid))
            render["missing"] = False                                  # Blender finished — nobody clicks anything
            res = bg_poll.send_ready(self.conn, self.make)
        self.assertEqual(self.p.job(jid)["state"], "running")
        self.assertEqual(res[(self.pid, "image")]["sent"], 1)
        self.assertIsNone(R.wait_reason(jid))
        self.assertEqual(self.codes("bg_auto_send"), 1)

    def test_paused_archived_autopilot_and_its_own_jobs_are_left_alone(self):
        paused = self.p.create_project("tạm dừng")
        j_paused = self.job(paused)
        self.p.set_paused(paused, True)
        archived = self.p.create_project("đã cất")
        j_arch = self.job(archived)
        self.conn.execute("UPDATE projects SET archived=1 WHERE id=?", (archived,))
        waiting = self.p.create_project("tự động chờ ở cổng")
        j_wait = self.job(waiting)
        self.conn.execute("UPDATE projects SET autopilot_state='waiting' WHERE id=?", (waiting,))
        j_auto = self.job(idx=2)
        self.conn.execute("UPDATE jobs SET origin='auto' WHERE id=?", (j_auto,))   # a stopped automatic run's own job
        j_mine = self.job(idx=3)
        self.conn.commit()
        bg_poll.send_ready(self.conn, self.make)
        for jid in (j_paused, j_arch, j_wait, j_auto):
            self.assertEqual(self.p.job(jid)["state"], "queued", jid)
        self.assertEqual(self.p.job(j_mine)["state"], "running")

    def test_an_old_queued_job_is_not_sent_by_itself_and_that_is_said(self):
        jid = self.job()
        self.conn.execute("UPDATE jobs SET created_at='2026-10-01T00:00:00+00:00' WHERE id=?", (jid,))
        self.conn.commit()
        bg_poll.send_ready(self.conn, self.make)
        self.assertEqual(self.p.job(jid)["state"], "queued")
        self.assertEqual(self.codes("bg_send_old"), 1)

    def test_the_money_gate_still_applies(self):
        jid = self.job()
        with mock.patch.object(ImageRunner, "_over_budget", lambda *a: "hết credit (thử)"):
            bg_poll.send_ready(self.conn, self.make)
        self.assertEqual(self.p.job(jid)["state"], "queued")
        self.assertEqual(self.codes("budget"), 1)

    def test_a_script_cap_that_stopped_sends_nothing(self):
        jid = self.job()
        cap = mock.Mock(stopped="DỪNG")
        with mock.patch("core.script_cap.active", lambda: cap):
            self.assertEqual(bg_poll.send_ready(self.conn, self.make), {})
        self.assertEqual(self.p.job(jid)["state"], "queued")

    def test_a_click_waits_for_the_turn_instead_of_returning_0(self):
        # lỗi B: the page's / background poll held the project's turn when the person clicked → submit_pending returned 0, only queued
        jid = self.job()
        lock = R._turn(self.pid, "image_gen", self.conn)
        held = threading.Event()

        def poller():
            with lock:
                held.set()
                time.sleep(0.5)
        t = threading.Thread(target=poller)
        t.start()
        held.wait(2)
        runner = ImageRunner(self.p, self.provider, self.data)
        self.assertEqual(runner.submit_pending(self.pid), 0)          # the old silent skip (still the background's behaviour)
        self.assertEqual(runner.submit_pending(self.pid, wait_s=5), 1)
        t.join()
        self.assertEqual(self.p.job(jid)["state"], "running")

    def test_the_round_sends_after_polling(self):
        jid = self.job()
        with mock.patch.object(bg_poll, "default_runner", lambda data_dir: self.make), \
                mock.patch("core.db.connect", lambda path: connect(os.path.join(self.dir, "m.sqlite"))):
            out = bg_poll.round_once("ignored", self.data)
        self.assertEqual(out[(self.pid, "image_send")]["sent"], 1)
        self.conn.close()
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.assertEqual(Pipeline(self.conn).job(jid)["state"], "running")

    def test_step2_says_the_real_reason_and_that_it_will_be_sent(self):
        from dashboard.steps import step2
        jid = self.job()
        R.WAIT_REASONS[jid] = ("đang render nền 3D của cảnh (Blender, 0 USD) — sẽ tự gửi khi render xong", time.time())
        other = self.job(idx=2)
        text = step2.queued_text(self.p, self.pid, 2)
        self.assertIn("TỰ GỬI", text)
        self.assertIn(f"job {jid}: đang render nền 3D", text)
        self.assertIn("1 ảnh chưa có lý do chờ", text)
        self.assertNotIn("bấm **▶ Gen ảnh**", text)
        R.WAIT_REASONS.pop(jid, None)
        R.WAIT_REASONS.pop(other, None)


class SelfFixSendTests(unittest.TestCase):
    """Hộp thư 12/10 00:55 (#24 job 679/680): QC tự sửa tạo job origin 'auto' ngoài chạy tự động → không ai gửi, kẹt queued."""
    setUp, tearDown, job, make = AutoSendTests.setUp, AutoSendTests.tearDown, AutoSendTests.job, AutoSendTests.make

    def retry(self, pid=None, idx=5):
        parent = self.job(pid, idx)
        self.conn.execute("UPDATE jobs SET state='failed' WHERE id=?", (parent,))
        child = self.p._insert_job(pid or self.pid, self.p.job(parent)["scene_id"], "image_gen", parent_job_id=parent,
                                   retry_count=1, retry_reason="QC tự sửa", origin="auto")
        self.conn.commit()
        return child

    def test_self_fix_redo_without_a_run_stays_queued_when_the_flag_is_off(self):
        jid = self.retry()
        with mock.patch("core.features.on", lambda n: False):
            bg_poll.send_ready(self.conn, self.make)
        self.assertEqual(self.p.job(jid)["state"], "queued")

    def test_self_fix_redo_without_a_run_is_sent_with_the_flag(self):
        jid = self.retry()
        with mock.patch("core.features.on", lambda n: n == "auto_send_self_fix"):
            bg_poll.send_ready(self.conn, self.make)
        self.assertEqual(self.p.job(jid)["state"], "running")

    def test_a_stopped_run_keeps_its_redo_and_a_first_auto_job_is_never_sent(self):
        stopped = self.p.create_project("đã dừng tự động")
        j_stopped = self.retry(stopped)
        self.conn.execute("UPDATE projects SET autopilot_state='stopped', autopilot_beat=? WHERE id=?", (time.time() + 1, stopped))
        first = self.job(idx=6)
        self.conn.execute("UPDATE jobs SET origin='auto' WHERE id=?", (first,))       # not a redo: an automatic run's own first job
        running = self.p.create_project("đang tự động")
        j_running = self.retry(running)
        self.conn.execute("UPDATE projects SET autopilot_state='running' WHERE id=?", (running,))
        self.conn.commit()
        with mock.patch("core.features.on", lambda n: n == "auto_send_self_fix"):
            bg_poll.send_ready(self.conn, self.make)
        for jid in (j_stopped, first, j_running):
            self.assertEqual(self.p.job(jid)["state"], "queued", jid)

    def test_the_money_gate_still_applies_to_a_self_fix_redo(self):
        jid = self.retry()
        with mock.patch("core.features.on", lambda n: n == "auto_send_self_fix"), \
                mock.patch.object(ImageRunner, "_over_budget", lambda *a: "hết credit (thử)"):
            bg_poll.send_ready(self.conn, self.make)
        self.assertEqual(self.p.job(jid)["state"], "queued")

    def test_a_redo_made_after_the_run_stopped_is_sent_and_said_as_a_self_fix(self):
        for state in bg_poll.SELF_FIX_AFTER_STOP:
            pid = self.p.create_project(f"tự động {state}")
            self.conn.execute("UPDATE projects SET autopilot_state=?, autopilot_beat=? WHERE id=?", (state, time.time() - 120, pid))
            jid = self.retry(pid)                     # QC rejected a shot the person made by hand after stopping the run
            with mock.patch("core.features.on", lambda n: n == "auto_send_self_fix"):
                bg_poll.send_ready(self.conn, self.make)
            self.assertEqual(self.p.job(jid)["state"], "running", state)
        said = [r[0] for r in self.conn.execute("SELECT message FROM diag_events WHERE code='bg_auto_send'")]
        self.assertTrue(said and all("job tự sửa" in m and "bạn đã bấm gửi" not in m for m in said), said)


if __name__ == "__main__":
    unittest.main()
