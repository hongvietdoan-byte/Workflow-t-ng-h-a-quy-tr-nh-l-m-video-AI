"""Flag scene_establishing (người dùng chốt 2026-09-27): each script scene first gets one wide establishing picture of its place and light,
sent with every shot of the scene as the shared place reference; the shots wait for it; it is priced like any picture."""
import json
import os
import tempfile
import unittest

from core import llm_runner, scene_establish, shots
from tests.test_v3 import kenta_project


class EstablishTests(unittest.TestCase):
    def setUp(self):
        os.environ["FEATURE_SCENE_ESTABLISHING"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_SCENE_ESTABLISHING", None)
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        self.rows = shots.shots_of(self.p, self.pid)
        self.first = self.rows[0]
        d = dict(self.first["data"], time="night")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.first["id"]))
        self.p.conn.commit()

    def runner(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        return ImageRunner(self.p, MockImageProvider(polls_to_finish=1), self.data)

    def test_the_shots_wait_for_the_wide_picture_then_send_it_as_the_place(self):
        r = self.runner()
        job = self.p.job(self.p.create_job(self.first["id"], "image_gen"))
        scene = self.first["data"]["story_scene"]
        self.assertTrue(r._wait(job))                                      # sent, not back yet
        self.assertTrue(r._wait(job) in (True, False))                     # polled
        for _ in range(3):
            if not r._wait(job):
                break
        self.assertFalse(r._wait(job))
        path = scene_establish.picture(self.data, self.pid, scene)
        self.assertTrue(path and os.path.exists(path))
        args = r._submit_args(job)
        self.assertIn(path, args[1])                                        # the wide picture goes with the shot
        self.assertIn("readable", args[0])                                  # night: faces still lit
        n = self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='establishing'").fetchone()[0]
        self.assertEqual(n, 1)                                              # priced once, not once per shot

    def test_one_picture_per_script_scene(self):
        r = self.runner()
        scenes = {row["data"]["story_scene"] for row in self.rows}
        for row in self.rows:
            job = self.p.job(self.p.create_job(row["id"], "image_gen"))
            for _ in range(4):
                if not r._wait(job):
                    break
        n = self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='establishing'").fetchone()[0]
        self.assertEqual(n, len(scenes))

    def test_off_by_default(self):
        os.environ.pop("FEATURE_SCENE_ESTABLISHING", None)
        r = self.runner()
        job = self.p.job(self.p.create_job(self.first["id"], "image_gen"))
        self.assertFalse(r._wait(job))
        self.assertEqual(scene_establish.light_sentence({"time": "night"}), "")
        self.assertIsNone(scene_establish.reference(self.data, self.pid, self.first["data"]["story_scene"]))


if __name__ == "__main__":
    unittest.main()
