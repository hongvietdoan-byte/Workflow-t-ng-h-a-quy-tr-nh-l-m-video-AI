import os
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import autopilot, perf
from core.db import connect
from core.pipeline import Pipeline
from tests.test_autopilot import Setup

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


def scene_ids(p, pid):
    return [r["id"] for r in p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]


class PerUserCountTests(Setup):
    def test_jobs_are_counted_for_the_person_who_created_them(self):
        self.build()
        s1, s2, s3 = scene_ids(self.p, self.pid)[:3]
        self.p.actor = "Viet"
        j1 = self.p.create_job(s1, "video_gen")
        self.p.create_job(s2, "video_gen")
        self.p.create_job(s1, "image_gen")
        self.p.actor = "Lan"
        self.p.create_job(s3, "video_gen")
        self.p.actor = None
        self.p.create_job(s3, "image_gen")                          # nobody typed a name
        self.p.conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (j1,))
        self.p.conn.commit()
        rows = {r["who"]: r for r in perf.by_user(self.p.conn)}
        self.assertEqual((rows["Viet"]["videos"], rows["Viet"]["videos_ok"], rows["Viet"]["images"]), (2, 1, 1))
        self.assertEqual(rows["Lan"]["videos"], 1)
        self.assertEqual(rows[perf.NO_NAME]["images"], 1)
        self.assertEqual([r["who"] for r in perf.by_user(self.p.conn)][0], "Viet")   # most videos first

    def test_a_retry_belongs_to_whoever_started_the_original_unless_someone_else_clicks(self):
        self.build()
        s1 = scene_ids(self.p, self.pid)[0]
        self.p.actor = "Viet"
        job = self.p.create_job(s1, "image_gen")
        self.p.start(job)
        self.p.fail(job, "boom")
        self.p.actor = None                                          # e.g. the background thread retrying
        retry = self.p.retry(job, "again")
        self.assertEqual(self.p.job(retry)["created_by"], "Viet")

    def test_the_automatic_run_counts_for_the_person_who_started_it(self):
        ctx = self.build()
        autopilot.start(self.p, self.pid, "Lan")
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        rows = {r["who"]: r for r in perf.by_user(self.p.conn)}
        self.assertEqual(list(rows), ["Lan"])
        n = self.p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (self.pid,)).fetchone()[0]
        self.assertEqual(rows["Lan"]["videos_ok"], n)
        self.assertGreater(rows["Lan"]["seconds"], 0)

    def test_old_databases_get_the_new_columns(self):
        path = os.path.join(tempfile.mkdtemp(), "old.sqlite")
        conn = connect(path)
        conn.execute("ALTER TABLE jobs DROP COLUMN created_by")
        conn.execute("ALTER TABLE projects DROP COLUMN autopilot_user")
        conn.commit()
        conn.close()
        conn = connect(path)
        self.assertIn("created_by", {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")})
        self.assertIn("autopilot_user", {r["name"] for r in conn.execute("PRAGMA table_info(projects)")})


class NameBarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["PIPELINE_DB"] = os.path.join(self.tmp, "m.sqlite")
        os.environ["PIPELINE_DATA"] = os.path.join(self.tmp, "projects")
        p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        p.create_project("demo")
        # S14.14 G-a: ui_v2 is ON by default now; these tests read the classic 👥 Nhóm table (team_screen, nhóm nặng — G-b)
        from unittest import mock
        flag = mock.patch.dict(os.environ, {"FEATURE_UI_V2": "0"})
        flag.start()
        self.addCleanup(flag.stop)

    def tearDown(self):
        os.environ.pop("PIPELINE_DB", None)
        os.environ.pop("PIPELINE_DATA", None)

    def test_typing_a_name_is_remembered_in_the_address_and_shown_in_the_table(self):
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Nhập tên" in m.value for m in at.markdown))     # asks for a name while empty
        at.text_input(key="user_input").set_value("  Viet   Doan ").run()
        self.assertEqual(at.session_state["user_name"], "Viet Doan")          # tidied
        user = at.query_params["user"]                                         # AppTest: a list (≤ 1.64) or one string (1.65)
        self.assertIn("Viet Doan", [user] if isinstance(user, str) else list(user))
        self.assertFalse(any("Nhập tên" in m.value for m in at.markdown))

    def test_name_from_the_address_is_used(self):
        at = AppTest.from_file(APP, default_timeout=30)
        at.query_params["user"] = "Lan"
        at.run()
        self.assertEqual(at.text_input(key="user_input").value, "Lan")

    def test_monitor_tab_has_the_per_user_table(self):
        p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        pid = p.conn.execute("SELECT id FROM projects").fetchone()[0]
        p.conn.execute("INSERT INTO scenes (project_id, idx, data, state) VALUES (?,?,?,?)", (pid, 1, "{}", "ready"))
        p.conn.commit()
        sid = p.conn.execute("SELECT id FROM scenes").fetchone()[0]
        p.actor = "Viet"
        p.create_job(sid, "video_gen")
        at = AppTest.from_file(APP, default_timeout=30)
        at.query_params["step"] = "team"                 # 01/10: the per-person numbers live on the 👥 Nhóm screen now
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Nhóm" in m.value for m in at.markdown))
        self.assertTrue(any("Viet" in str(d.value) for d in at.dataframe))


if __name__ == "__main__":
    unittest.main()
