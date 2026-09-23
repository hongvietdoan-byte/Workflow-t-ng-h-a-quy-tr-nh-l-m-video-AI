"""An unexpected answer while polling a job (unknown task, a provider bug, a full disk) must not take the dashboard page down:
the job is kept, the problem is reported, the other jobs carry on."""
import os
import shutil
import tempfile
import unittest

from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider, ProviderError
from core.runner import ImageRunner


class PollRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("poll")
        self.sid = self.p.create_scene(self.pid, 1, "S1")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def running_job(self, external_id):
        jid = self.p.create_job(self.sid, "image_gen")
        self.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (external_id, jid))
        self.p.start(jid)
        return jid

    def test_the_simulators_report_an_unknown_task_instead_of_crashing(self):
        with self.assertRaises(ProviderError):
            MockImageProvider().status("img-99")
        with self.assertRaises(ProviderError):
            MockVideoProvider().status("vid-99")

    def test_an_unexpected_status_error_keeps_the_job_and_is_reported(self):
        class Broken(MockImageProvider):
            def status(self, task_id):
                raise KeyError(task_id)
        jid = self.running_job("x-1")
        counts = ImageRunner(self.p, Broken(), os.path.join(self.dir, "projects")).poll_once(self.pid)
        self.assertEqual(counts["running"], 1)
        self.assertEqual(self.p.job(jid)["state"], "running")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='status_error'").fetchone()[0], 1)

    def test_an_unexpected_download_error_keeps_the_job(self):
        class NoDisk(MockImageProvider):
            def status(self, task_id):
                from core.providers import TaskStatus
                return TaskStatus("succeeded")

            def download(self, task_id, dest):
                raise OSError("disk full")
        jid = self.running_job("x-2")
        ImageRunner(self.p, NoDisk(), os.path.join(self.dir, "projects")).poll_once(self.pid)
        self.assertEqual(self.p.job(jid)["state"], "running")


if __name__ == "__main__":
    unittest.main()
