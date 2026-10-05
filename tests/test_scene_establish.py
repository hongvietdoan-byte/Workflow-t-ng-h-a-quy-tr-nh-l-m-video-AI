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


class PlacePicturesPathTests(unittest.TestCase):
    """06/10: place_pictures checked the stored RELATIVE path ("data/assets/…") against the working folder, so a Dashboard / tool
    started elsewhere (a worktree, another folder) found no place picture — the wide establishing shot then went out with no place
    reference. It now goes through assets.resolve (S14.43B: anchored at the install folder of PIPELINE_DB)."""

    def test_relative_library_picture_found_from_another_working_folder(self):
        import sqlite3
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, "data", "assets", "7"))
        with open(os.path.join(home, "data", "assets", "7", "1.png"), "wb") as f:
            f.write(b"x")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE asset_images (id INTEGER PRIMARY KEY, asset_id INT, path TEXT, status TEXT, role TEXT)")
        conn.execute("INSERT INTO asset_images (asset_id, path, status, role) VALUES (7, ?, 'approved', 'eye_level')",
                     (os.path.join("data", "assets", "7", "1.png"),))
        old_env, old_cwd = os.environ.get("PIPELINE_DB"), os.getcwd()
        os.environ["PIPELINE_DB"] = os.path.join(home, "data", "manifest.sqlite")
        elsewhere = tempfile.mkdtemp()
        os.chdir(elsewhere)
        try:
            pics = scene_establish.place_pictures(conn, 7)
        finally:
            os.chdir(old_cwd)
            if old_env is None:
                os.environ.pop("PIPELINE_DB", None)
            else:
                os.environ["PIPELINE_DB"] = old_env
        self.assertEqual(pics, [os.path.join(home, "data", "assets", "7", "1.png")])
