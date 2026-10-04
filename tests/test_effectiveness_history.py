"""S14.19 Đợt 1 (KE_HOACH_BO_NAO_PROMPT_TU_HOC): effectiveness snapshots — the figures AND what was on when they were taken."""
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest import mock

from core import effectiveness, feedback
from core.db import connect
from core.pipeline import Pipeline

PRICING = {"currency": "usd", "per_image": {}, "per_video_second": {}, "per_video_clip": {}, "per_audio": {}}
T0 = datetime(2026, 10, 5, 10, 0, 12)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("eff")
        self.p.create_scene(self.pid, 1, "S1")
        patcher = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": os.path.join(self.dir, "k")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def snap(self, at=T0, trigger="manual", pid="same"):
        return effectiveness.snapshot(self.conn, self.pid if pid == "same" else pid, PRICING, trigger, now=at)

    def test_two_clicks_in_the_same_minute_make_one_row(self):
        a = self.snap()
        b = self.snap(at=T0.replace(second=50))
        self.assertEqual(a, b)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM effectiveness_snapshots").fetchone()[0], 1)
        self.snap(at=T0.replace(minute=1))
        self.assertEqual(len(effectiveness.history(self.conn, self.pid)), 2)

    def test_row_carries_figures_flags_lessons_knowledge_and_satisfaction(self):
        feedback.add(self.conn, "delivery", project_id=self.pid, rating=5)
        self.conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, state)"
                          " VALUES ('x','director','k','t','b','s','approved')")
        with mock.patch("core.features.on", side_effect=lambda n: n in ("film_crew", "lip_sync")):
            sid = self.snap(trigger="delivery")
        row = self.conn.execute("SELECT * FROM effectiveness_snapshots WHERE id=?", (sid,)).fetchone()
        self.assertEqual(row["at"], "2026-10-05T10:00")
        self.assertEqual(row["trigger"], "delivery")
        self.assertEqual(json.loads(row["flags_on"]), ["film_crew", "lip_sync"])
        self.assertEqual(row["lessons_on"], 1)
        self.assertEqual(row["satisfaction"], 1.0)
        self.assertEqual(row["feedback_n"], 1)
        self.assertEqual(row["scenes"], 1)
        self.assertTrue(row["knowledge_fp"])
        self.assertEqual(json.loads(row["detail"])["scenes"], 1)

    def test_bad_trigger_is_refused(self):
        with self.assertRaises(ValueError):
            self.snap(trigger="page_open")

    def test_delta_says_what_changed(self):
        with mock.patch("core.features.on", side_effect=lambda n: n == "film_crew"):
            a = self.snap()
        feedback.add(self.conn, "delivery", project_id=self.pid, rating=1)
        self.conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, state)"
                          " VALUES ('x','motion','k','Bài mới','b','s','approved')")
        with mock.patch("core.features.on", side_effect=lambda n: n == "lip_sync"), \
                mock.patch("core.effectiveness.knowledge_fp", return_value="director:new|motion:new"):
            b = self.snap(at=T0.replace(minute=5))
        hist = {h["id"]: h for h in effectiveness.history(self.conn, self.pid)}
        d = effectiveness.delta(hist[a], hist[b])
        self.assertEqual(d["flags_added"], ["lip_sync"])
        self.assertEqual(d["flags_removed"], ["film_crew"])
        self.assertEqual(d["lessons_on"], (0, 1))
        self.assertEqual([x["title"] for x in d["lessons_added"]], ["Bài mới"])
        self.assertTrue(d["knowledge_changed"])
        self.assertEqual(d["metrics"]["satisfaction"], (None, 0.0, None))
        self.assertTrue(any("lip_sync" in line for line in d["changed"]))
        same = effectiveness.delta(hist[a], hist[a])
        self.assertEqual(same["changed"], [])

    def test_history_and_trend_and_system_snapshot(self):
        self.snap(at=T0)
        self.snap(at=T0.replace(minute=2))
        sys_id = self.snap(at=T0, pid=None)
        self.assertEqual(len(effectiveness.history(self.conn, self.pid)), 2)
        self.assertEqual([h["id"] for h in effectiveness.history(self.conn, None)], [sys_id])
        tr = effectiveness.trend(self.conn, "scenes", project_id=self.pid)
        self.assertEqual([v for _, v in tr], [1, 1])
        self.assertEqual(tr[0][0], "2026-10-05T10:00")
        with self.assertRaises(ValueError):
            effectiveness.trend(self.conn, "drop table")

    def test_finished_projects_are_the_delivered_ones(self):
        self.assertEqual(effectiveness.finished_projects(self.conn), [])
        self.conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?, 'final', 'x.mp4', '{}', 'now')",
                          (self.pid,))
        self.assertEqual(effectiveness.finished_projects(self.conn), [self.pid])


class BaselineToolTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "m.sqlite")
        conn = connect(self.db)
        p = Pipeline(conn)
        self.done = p.create_project("xong")
        p.create_project("dở")
        conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?, 'final', 'x.mp4', '{}', 'now')",
                     (self.done,))
        conn.commit()
        conn.close()
        patcher = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": os.path.join(self.dir, "k")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_tool(self, *args):
        from tools import effectiveness_baseline
        out = io.StringIO()
        with redirect_stdout(out):
            code = effectiveness_baseline.main(["--db", self.db, *args])
        return code, out.getvalue()

    def count(self):
        conn = connect(self.db)
        try:
            return [tuple(r) for r in conn.execute("SELECT project_id, trigger FROM effectiveness_snapshots ORDER BY id")]
        finally:
            conn.close()

    def test_without_yes_only_says_what_it_would_write(self):
        code, out = self.run_tool()
        self.assertEqual(code, 0)
        self.assertEqual(self.count(), [])
        self.assertIn("--yes", out)
        self.assertIn("xong", out)

    def test_with_yes_writes_one_system_and_one_per_finished_project(self):
        code, out = self.run_tool("--yes")
        self.assertEqual(code, 0)
        self.assertEqual(self.count(), [(None, "manual"), (self.done, "manual")])
        self.assertIn("0 USD", out)

    def test_missing_database_is_said(self):
        from tools import effectiveness_baseline
        out = io.StringIO()
        with redirect_stdout(out):
            code = effectiveness_baseline.main(["--db", os.path.join(self.dir, "nope.sqlite")])
        self.assertNotEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "nope.sqlite")))


if __name__ == "__main__":
    unittest.main()
