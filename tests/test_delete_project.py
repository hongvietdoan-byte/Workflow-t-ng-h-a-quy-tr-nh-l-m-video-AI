import os
import unittest

from streamlit.testing.v1 import AppTest

from core import assets, autopilot, llm_runner
from core.music import MockAudioProvider
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner
from tests.test_autopilot import fake_render
from tests.test_step1_flow import APP, split_only


class DeleteProjectTests(unittest.TestCase):
    def test_a_finished_project_is_removed_with_its_files_and_the_other_project_is_untouched(self):
        tmp, db, data, p, pid = split_only()
        other = p.create_project("keep me")
        ctx = autopilot.Context(data, ImageRunner(p, MockImageProvider(), data), VideoRunner(p, MockVideoProvider(polls_to_finish=1), data),
                                llm_runner.MockLlm(), MockAudioProvider(), fake_render)
        autopilot.set_gates(p, pid, {"bible": False})   # unattended run (checkpoint: test_v2)
        autopilot.start(p, pid)
        autopilot.run_until_done(p, pid, ctx)
        own = assets.create(p.conn, "ff", "prop", "Only here", "", "", pid, "x@y.z")
        self.assertTrue(os.path.isdir(os.path.join(data, str(pid))))
        p.delete_project(pid, data)
        for table in ("scenes", "jobs", "characters"):
            self.assertEqual(p.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id=?", (pid,)).fetchone()[0], 0, table)
        self.assertIsNone(p.project(pid))
        self.assertIsNone(assets.get(p.conn, own))
        self.assertFalse(os.path.exists(os.path.join(data, str(pid))))
        self.assertIsNotNone(p.project(other))
        parked = os.listdir(os.path.join(data, "_deleted"))                       # files kept for the trash period, not erased at once
        self.assertEqual(len(parked), 1)
        self.assertTrue(parked[0].startswith(f"{pid}__"))
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM outputs WHERE project_id=?", (pid,)).fetchone()[0], 0)

    def test_spend_history_keeps_the_project_and_a_new_project_never_reuses_its_id(self):
        from core.cost import record_usage
        tmp, db, data, p, pid = split_only()
        record_usage(p.conn, None, "audio", "clipai", "eleven_v3", "tts", 1, "clip", project_id=pid)
        biggest = p.conn.execute("SELECT MAX(id) FROM projects").fetchone()[0]
        p.delete_project(biggest, data)
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE project_id=? OR deleted_project_id=?",
                                        (pid, pid)).fetchone()[0], 1)
        self.assertGreater(p.create_project("new"), biggest)

    def test_parked_folders_are_purged_after_the_retention_period(self):
        import time
        from core import trash
        tmp, db, data, p, pid = split_only()
        os.makedirs(os.path.join(data, str(pid)), exist_ok=True)
        p.delete_project(pid, data)
        self.assertEqual(trash.purge_expired(data, now=time.time() + 5), 0)
        self.assertEqual(trash.purge_expired(data, now=time.time() + 400 * 86400), 1)
        self.assertEqual(os.listdir(os.path.join(data, "_deleted")), [])

    def test_the_dashboard_asks_first_then_deletes(self):
        tmp, db, data, p, pid = split_only()
        os.environ.update({"PIPELINE_DB": db, "PIPELINE_DATA": data})
        try:
            at = AppTest.from_file(APP, default_timeout=40).run()
            next(b for b in at.button if b.key == f"proj_del_{pid}").click().run()
            self.assertIsNotNone(p.project(pid))                                      # only asked so far
            next(b for b in at.button if b.key == f"proj_del_{pid}_yes").click().run()
            self.assertFalse(at.exception)
            self.assertIsNone(p.project(pid))
        finally:
            os.environ.pop("PIPELINE_DB", None)
            os.environ.pop("PIPELINE_DATA", None)


if __name__ == "__main__":
    unittest.main()
