"""📦 Cất dự án: hidden from the picker and the automatic run, nothing deleted, restorable from ⚙."""
import os
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import archive, autopilot
from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


def _counts(p, pid):
    return tuple(p.conn.execute(sql, (pid,)).fetchone()[0] for sql in (
        "SELECT COUNT(*) FROM scenes WHERE project_id=?", "SELECT COUNT(*) FROM characters WHERE project_id=?",
        "SELECT COUNT(*) FROM jobs WHERE project_id=?"))


class ArchiveCoreTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.old = self.p.create_project("Dự án cũ #1")
        self.new = self.p.create_project("Dự án thử mới")
        sid = self.p.create_scene(self.old, 1, "CẢNH 1")
        store_scene_analysis(self.p, self.old, ANALYSIS)
        self.p.create_job(sid)

    def test_archive_hides_pauses_and_keeps_every_row(self):
        before = _counts(self.p, self.old)
        archive.archive(self.p, self.old)
        self.assertEqual([r["id"] for r in archive.active_projects(self.p.conn)], [self.new])
        self.assertEqual([r["id"] for r in archive.archived_projects(self.p.conn)], [self.old])
        row = self.p.project(self.old)
        self.assertTrue(archive.is_archived(row))
        self.assertEqual(row["paused"], 1)                       # queued pictures/clips are not sent
        self.assertEqual(_counts(self.p, self.old), before)      # nothing deleted
        archive.restore(self.p, self.old)
        self.assertEqual([r["id"] for r in archive.active_projects(self.p.conn)], [self.old, self.new])
        self.assertEqual(self.p.project(self.old)["paused"], 1)  # still paused: nothing is sent by surprise after a restore

    def test_a_running_automatic_run_is_stopped_and_never_picked_up_again(self):
        autopilot.start(self.p, self.old)
        archive.archive(self.p, self.old)
        self.assertEqual(autopilot.status(self.p, self.old)["state"], autopilot.STOPPED)
        # even if something marks it running again (an old queue, a restart), the tick refuses to run it
        self.p.conn.execute("UPDATE projects SET autopilot_state='running', paused=0 WHERE id=?", (self.old,))
        self.p.conn.commit()
        self.assertEqual(autopilot.tick(self.p, self.old, autopilot.Context(tempfile.mkdtemp(), None, None, None)),
                         autopilot.STOPPED)
        self.assertIn("đã cất", autopilot.status(self.p, self.old)["note"])

    def test_an_idle_project_keeps_its_automatic_state(self):
        archive.archive(self.p, self.new)
        self.assertEqual(autopilot.status(self.p, self.new)["state"], "idle")


class ArchiveDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                           "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku")})
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("PIPELINE_DB", "PIPELINE_DATA", "KNOWLEDGE_USER_DIR")])
        self.p = Pipeline(connect(self.db))
        self.old = self.p.create_project("Dự án cũ #1")
        self.new = self.p.create_project("Dự án thử mới")

    def test_archive_from_the_gear_then_restore(self):
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["global_pid"] = self.old
        at.run()
        self.assertEqual(at.selectbox(key="global_pid").options, ["Dự án cũ #1", "Dự án thử mới"])
        at.button(key=f"proj_archive_{self.old}").click().run()
        at.button(key=f"proj_archive_{self.old}_yes").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(archive.is_archived(Pipeline(connect(self.db)).project(self.old)))
        at.run()
        self.assertEqual(at.selectbox(key="global_pid").options, ["Dự án thử mới"])
        self.assertEqual(at.selectbox(key="global_pid").value, self.new)
        at.button(key=f"proj_restore_{self.old}").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.selectbox(key="global_pid").options, ["Dự án cũ #1", "Dự án thử mới"])
        self.assertEqual(at.selectbox(key="global_pid").value, self.old)
        self.assertFalse([b for b in at.button if b.key and b.key.startswith("proj_restore_")])

    def test_everything_archived_says_where_to_restore(self):
        archive.archive(self.p, self.old)
        archive.archive(self.p, self.new)
        at = AppTest.from_file(APP, default_timeout=60).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("2 dự án đã cất" in i.value for i in at.info))
        self.assertTrue(any(b.key == f"proj_restore_{self.new}" for b in at.button))


if __name__ == "__main__":
    unittest.main()
