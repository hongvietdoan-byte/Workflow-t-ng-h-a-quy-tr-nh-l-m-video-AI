import os
import tempfile
import time
import unittest
from unittest import mock

from core import autopilot, llm_runner, perf, script_parser
from core.db import connect
from core.music import MockAudioProvider
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner
from tests.test_autopilot import SAMPLE, Setup, fake_render


def make_projects(db, n):
    p = Pipeline(connect(db))
    ids = []
    for i in range(n):
        pid = p.create_project(f"clip {i}", "human_qc", 0.85, 2)
        paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
        script_parser.import_scenes(p, pid, script_parser.split_scenes(paragraphs))
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        ids.append(pid)
    return p, ids


def factory(pipeline, data_dir):
    return autopilot.Context(data_dir, ImageRunner(pipeline, MockImageProvider(), data_dir),
                             VideoRunner(pipeline, MockVideoProvider(polls_to_finish=1), data_dir),
                             llm_runner.MockLlm(), MockAudioProvider(), fake_render)


def wait(db, ids, want, seconds=60):
    deadline = time.time() + seconds
    while time.time() < deadline:
        p = Pipeline(connect(db))
        if all(autopilot.status(p, i)["state"] in want for i in ids):
            return True
        time.sleep(0.05)
    return False


class QueueTests(unittest.TestCase):
    def test_more_projects_than_slots_wait_in_line_and_all_finish(self):
        tmp = tempfile.mkdtemp()
        db, data = os.path.join(tmp, "m.sqlite"), os.path.join(tmp, "projects")
        p, ids = make_projects(db, 5)
        mgr = autopilot.Manager(db, data, factory, poll_sec=0.02, max_parallel=2)
        for i in ids:
            autopilot.set_gates(p, i, {"bible": False, "storyboard": False})   # unattended run (checkpoint: test_v2)
            autopilot.start(p, i)
            mgr.start(i)
        states = [autopilot.status(p, i)["state"] for i in ids]
        self.assertGreaterEqual(states.count("queued"), 1)          # 5 approved, only 2 slots
        self.assertEqual(mgr.queue_length(), states.count("queued"))
        peak, deadline = 0, time.time() + 90
        while time.time() < deadline:
            peak = max(peak, mgr.running_count())
            if all(autopilot.status(Pipeline(connect(db)), i)["state"] == "done" for i in ids):
                break
            time.sleep(0.02)
        self.assertLessEqual(peak, 2)                                # never more than the limit at once
        for i in ids:
            self.assertEqual(autopilot.status(Pipeline(connect(db)), i)["state"], "done")
        self.assertEqual(mgr.queue_length(), 0)

    def test_stopping_a_queued_project_removes_it_from_the_line(self):
        tmp = tempfile.mkdtemp()
        db, data = os.path.join(tmp, "m.sqlite"), os.path.join(tmp, "projects")
        p, ids = make_projects(db, 3)
        mgr = autopilot.Manager(db, data, factory, poll_sec=0.02, max_parallel=1)
        for i in ids:
            autopilot.set_gates(p, i, {"bible": False, "storyboard": False})   # unattended run (checkpoint: test_v2)
            autopilot.start(p, i)
            mgr.start(i)
        autopilot.stop(p, ids[2])
        self.assertTrue(wait(db, ids[:2], ("done",)))
        time.sleep(0.3)
        self.assertEqual(autopilot.status(Pipeline(connect(db)), ids[2])["state"], "stopped")   # never started
        self.assertFalse(mgr.alive(ids[2]))
        autopilot.resume(p, ids[2])
        self.assertTrue(mgr.start(ids[2]))                                                        # can be re-queued
        self.assertTrue(wait(db, [ids[2]], ("done",)))


class DatabaseModeTests(unittest.TestCase):
    def test_file_database_uses_wal_and_waits_for_locks(self):
        conn = connect(os.path.join(tempfile.mkdtemp(), "m.sqlite"))
        self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")   # many writer threads, no "database is locked"
        conn.close()


class RealImage(MockImageProvider):
    """Not named mock*: its sends are real ones for the daily cap (S14.1 mục 3.1 — the cap counts paid sends, not jobs)."""
    name = "deepix-fake"


class RealVideo(MockVideoProvider):
    name = "clipai-fake"


def paid_rows(conn, n, provider="deepix", kind="image", at="datetime('now')"):
    for _ in range(n):
        conn.execute("INSERT INTO usage_events (kind, provider, model, tier, quantity, unit, at) VALUES (?,?,'m','t',1,'image',"
                     + at + ")", (kind, provider))
    conn.commit()


class DailyCapGoneTests(Setup):
    """S14.18: the machine-wide daily cap AUTOPILOT_DAILY_JOBS is gone (limits are per person: core/person_limits, and per product).
    The tests that held the old cap now hold that the variable no longer stops anything; sends of the day are still counted to show."""

    def test_the_old_variable_no_longer_stops_the_run(self):
        ctx = self.build(image=RealImage(), video=RealVideo(polls_to_finish=1))
        paid_rows(self.p.conn, 50)                                   # far over the old cap
        with mock.patch.dict(os.environ, {"AUTOPILOT_DAILY_JOBS": "2"}):
            autopilot.set_gates(self.p, self.pid, {"bible": False, "storyboard": False})   # unattended run (checkpoint: test_v2)
            autopilot.start(self.p, self.pid)
            self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        self.assertNotIn("trong ngày", autopilot.status(self.p, self.pid)["note"])
        self.assertGreater(perf.jobs_today(self.p.conn), 2)
        self.assertFalse(hasattr(autopilot, "_daily_cap"))

    def test_a_waiting_redraw_is_sent_whatever_was_sent_today(self):
        ctx = self.build(image=RealImage(), video=RealVideo(polls_to_finish=1))
        paid_rows(self.p.conn, 50)
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchone()["id"]
        jid = self.p.create_job(sid, "image_gen")
        autopilot._set(self.p, self.pid, autopilot.WAITING, "chờ storyboard")
        autopilot.set_gates(self.p, self.pid, {"waiting_for": "storyboard"})
        with mock.patch.dict(os.environ, {"AUTOPILOT_DAILY_JOBS": "1"}):
            autopilot.serve_waiting(self.p, self.pid, ctx)
        self.assertNotEqual(self.p.job(jid)["state"], "queued")                 # sent

    def test_sends_of_the_day_are_still_counted_for_the_screen(self):
        self.build()
        paid_rows(self.p.conn, 3)                                    # sent today
        paid_rows(self.p.conn, 5, kind="audio")                      # not a picture / clip
        paid_rows(self.p.conn, 5, at="datetime('now', '-2 days')")   # another day
        paid_rows(self.p.conn, 4, provider="mock-image")             # simulated: free
        self.assertEqual(perf.sends_today(self.p.conn), 3)
        snap = perf.snapshot(self.p.conn)
        self.assertEqual(snap["sends_today"], 3)
        self.assertNotIn("daily_limit", snap)


class PerfTests(Setup):
    def test_snapshot_reports_throughput_durations_and_projects_after_a_run(self):
        ctx = self.build()
        autopilot.set_gates(self.p, self.pid, {"bible": False, "storyboard": False})   # unattended run (checkpoint: test_v2)
        autopilot.start(self.p, self.pid)
        autopilot.run_until_done(self.p, self.pid, ctx)
        snap = perf.snapshot(self.p.conn, 0, 0, 2)
        image, video = snap["kinds"]
        self.assertGreater(image["ok_24h"], 0)
        self.assertGreater(video["ok_24h"], 0)
        self.assertEqual(image["running"] + video["running"], 0)
        self.assertEqual(snap["projects"][0]["state"], "done")
        self.assertEqual(snap["projects"][0]["videos"], snap["projects"][0]["scenes"])
        self.assertGreater(snap["jobs_today"], 0)

    def test_portfolio_rows_covers_both_a_finished_autopilot_project_and_a_fresh_manual_one(self):
        """The portfolio table must show every project side by side -- autopilot or step-by-step,
        finished or not -- unlike the autopilot-only project_rows/snapshot table above."""
        ctx = self.build()
        autopilot.set_gates(self.p, self.pid, {"bible": False, "storyboard": False})   # unattended run (checkpoint: test_v2)
        autopilot.start(self.p, self.pid)
        autopilot.run_until_done(self.p, self.pid, ctx)
        fresh_pid = self.p.create_project("brand new", "human_qc", 0.85, 2)
        rows = {r["id"]: r for r in perf.portfolio_rows(self.p.conn, self.data)}
        finished, fresh = rows[self.pid], rows[fresh_pid]
        self.assertTrue(finished["done"])
        self.assertEqual(finished["step_label"], "✅ Hoàn tất")
        self.assertTrue(os.path.exists(finished["final_video"]))
        self.assertFalse(fresh["done"])
        self.assertIsNone(fresh["final_video"])
        self.assertEqual((fresh["step_label"], fresh["scenes"]), ("① Kịch bản", 0))

    def test_alerts_flag_overload_failures_slowdown_and_queue(self):
        base = {"kind": "video_gen", "running": 0, "queued": 0, "ok_1h": 0, "failed_1h": 0, "ok_24h": 0, "failed_24h": 0,
                "avg_sec": None, "recent_sec": None, "earlier_sec": None, "recent_fail_rate": 0.0, "recent_outcomes": 0}
        self.assertEqual(perf.alerts([base], 0, 0, 2), [])
        busy = dict(base, running=perf.MAX_ACTIVE, queued=3)
        self.assertTrue(any("cùng lúc" in a for a in perf.alerts([busy], 0, 0, 2)))
        failing = dict(base, recent_fail_rate=0.5, recent_outcomes=10)
        self.assertTrue(any("bị lỗi" in a for a in perf.alerts([failing], 0, 0, 2)))
        slow = dict(base, recent_sec=200, earlier_sec=60)
        self.assertTrue(any("chậm dần" in a for a in perf.alerts([slow], 0, 0, 2)))
        self.assertFalse(any("trần ngày" in a for a in perf.alerts([base], 0, 0, 2)))   # S14.18: no machine-wide daily cap
        self.assertTrue(any("xếp hàng" in a for a in perf.alerts([base], 2, 2, 2)))


if __name__ == "__main__":
    unittest.main()
