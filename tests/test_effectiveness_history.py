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


class PanelAndDeliveryHookTests(unittest.TestCase):
    """📌 Lưu mốc in the effectiveness panel (📊 Theo dõi, UI v2) and the snapshot taken after a delivery."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "m.sqlite")
        patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.dir, "projects"),
                                               "KNOWLEDGE_USER_DIR": os.path.join(self.dir, "k"), "FEATURE_UI_V2": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("mốc")

    def tearDown(self):
        self.p.conn.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def rows(self):
        return self.p.conn.execute("SELECT project_id, trigger FROM effectiveness_snapshots ORDER BY id").fetchall()

    def test_pin_button_saves_a_snapshot_and_opening_the_page_does_not(self):
        from streamlit.testing.v1 import AppTest
        app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
        at = AppTest.from_file(app, default_timeout=60)
        at.session_state["step"] = "📊 Theo dõi"
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.rows(), [])                               # opening the page takes no snapshot
        next(b for b in at.button if b.key == f"eff_snap_{self.pid}").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual([tuple(r) for r in self.rows()], [(self.pid, "manual")])
        next(b for b in at.button if b.key == f"eff_snap_{self.pid}").click().run()     # same minute → still one row
        self.assertEqual(len(self.rows()), 1)

    def test_two_milestones_show_a_chart_and_what_changed(self):
        from streamlit.testing.v1 import AppTest
        with mock.patch("core.features.on", side_effect=lambda n: n == "film_crew"):
            effectiveness.snapshot(self.p.conn, self.pid, PRICING, "manual", now=T0)
        with mock.patch("core.features.on", side_effect=lambda n: n == "lip_sync"):
            effectiveness.snapshot(self.p.conn, self.pid, PRICING, "delivery", now=T0.replace(minute=9))
        at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"), default_timeout=60)
        at.session_state["step"] = "📊 Theo dõi"
        at.run()
        self.assertFalse(at.exception, at.exception)
        captions = "\n".join(c.value for c in at.caption)
        self.assertIn("2 mốc", captions)
        self.assertIn("Bật cờ: lip_sync", captions)
        self.assertIn("Tắt cờ: film_crew", captions)

    def test_after_delivery_hook_records_a_delivery_snapshot_and_never_breaks_the_delivery(self):
        from dashboard.steps import step5
        step5.snapshot_after_delivery(self.p, self.pid)
        self.assertEqual([tuple(r) for r in self.rows()], [(self.pid, "delivery")])
        with mock.patch("core.effectiveness.snapshot", side_effect=RuntimeError("hỏng")), \
                mock.patch.object(step5.st, "warning") as warn:
            step5.snapshot_after_delivery(self.p, self.pid)            # a failure is said, not raised
        warn.assert_called_once()


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


class ReviewFixTests(unittest.TestCase):
    """S14.19 rà soát: dashboard.env flags, a fuller knowledge fingerprint, old-style finished projects, --project."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        patcher = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": os.path.join(self.dir, "k")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_knowledge_fp_changes_with_one_line_of_the_director_prompt(self):
        from core import knowledge
        before = effectiveness.knowledge_fp()
        real = knowledge._read

        def edited(path):
            text = real(path)
            return text + "\nmột dòng mới" if path.replace("\\", "/").endswith("prompts/01_director_scene_analysis.md") else text
        with mock.patch.object(knowledge, "_read", side_effect=edited):
            after = effectiveness.knowledge_fp()
        self.assertNotEqual(before.split("|")[0], after.split("|")[0])
        self.assertEqual(before.split("|")[1], after.split("|")[1])          # motion did not change

    def test_knowledge_fp_covers_genre_files_and_golden(self):
        from core import knowledge
        real = knowledge._read
        for tail in ("knowledge/genre/SHORT_FORM.md", "eval/golden.json", "knowledge/ff_gameplay_visual.md"):
            before = effectiveness.knowledge_fp()
            with mock.patch.object(knowledge, "_read",
                                   side_effect=lambda p, t=tail: real(p) + ("x" if p.replace("\\", "/").endswith(t) else "")):
                self.assertNotEqual(before, effectiveness.knowledge_fp(), tail)

    def make_db(self):
        db = os.path.join(self.dir, "m.sqlite")
        data = os.path.join(self.dir, "projects")
        conn = connect(db)
        p = Pipeline(conn)
        old = p.create_project("cũ kiểu v1")
        extra = p.create_project("chưa xong")
        conn.close()
        os.makedirs(os.path.join(data, str(old), "output"))
        with open(os.path.join(data, str(old), "output", "FINAL_VIDEO.mp4"), "wb") as f:
            f.write(b"x")
        return db, data, old, extra

    def rows(self, db):
        conn = connect(db)
        try:
            return [tuple(r) for r in conn.execute("SELECT project_id FROM effectiveness_snapshots ORDER BY id")]
        finally:
            conn.close()

    def test_old_style_final_video_counts_and_project_option_adds(self):
        from tools import effectiveness_baseline
        db, data, old, extra = self.make_db()
        conn = connect(db)
        self.assertEqual(effectiveness.finished_projects(conn), [])
        self.assertEqual(effectiveness.finished_projects(conn, data), [old])
        conn.close()
        with redirect_stdout(io.StringIO()):
            effectiveness_baseline.main(["--db", db, "--data", data, "--project", str(extra), "--yes", "--env", os.devnull])
        self.assertEqual(self.rows(db), [(None,), (old,), (extra,)])

    def test_tool_reads_dashboard_env_flags(self):
        from core import features
        from tools import effectiveness_baseline
        db, data, _, _ = self.make_db()
        env = os.path.join(self.dir, "dashboard.env")
        name = next(n for n, f in features.FEATURES.items() if not f["verified"])
        with open(env, "w", encoding="utf-8") as f:
            f.write(f"# thử\nFEATURE_{name.upper()}=1\n")
        with mock.patch.dict(os.environ, {}), mock.patch.object(features, "settings",
                                                                 return_value={"preset": "custom", "flags": {}}):
            os.environ.pop(f"FEATURE_{name.upper()}", None)
            n_before = len(effectiveness.flags_on())
            out = io.StringIO()
            with redirect_stdout(out):
                effectiveness_baseline.main(["--db", db, "--data", data, "--env", env])
            self.assertIn(name, out.getvalue())
            self.assertEqual(len(effectiveness.flags_on()), n_before + 1)

if __name__ == "__main__":
    unittest.main()
