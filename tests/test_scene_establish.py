"""Flag scene_establishing (người dùng chốt 2026-09-27): each script scene first gets one wide establishing picture of its place and light,
sent with every shot of the scene as the shared place reference; the shots wait for it; it is priced like any picture."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_runner, scene_establish, shots
from tests.test_v3 import kenta_project
from tests._flags import flags_clear, flags_on, flags_on_ctx, flags_on_deco  # noqa: F401


class EstablishTests(unittest.TestCase):
    def setUp(self):
        flags_on(self, "scene_establishing")
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
        flags_clear("scene_establishing")
        r = self.runner()
        job = self.p.job(self.p.create_job(self.first["id"], "image_gen"))
        self.assertFalse(r._wait(job))
        self.assertEqual(scene_establish.light_sentence({"time": "night"}), "")
        self.assertIsNone(scene_establish.reference(self.data, self.pid, self.first["data"]["story_scene"]))


if __name__ == "__main__":
    unittest.main()


class EstablishTraineeTests(EstablishTests):
    """B6 học việc 08/10: scene_establishing 🎓 — drawn apart (establish/trainee/), the shot never waits, no light sentence, no ref."""

    def setUp(self):
        super().setUp()
        from tests._flags import flags_trainee
        flags_trainee(self, "scene_establishing")

    def _drive(self, r, job, n=4):
        for _ in range(n):
            r._wait(job)

    def test_the_shots_wait_for_the_wide_picture_then_send_it_as_the_place(self):
        r = self.runner()
        job = self.p.job(self.p.create_job(self.first["id"], "image_gen"))
        scene = self.first["data"]["story_scene"]
        self.assertFalse(r._wait(job))                                      # never holds the shot
        self._drive(r, job)
        self.assertIsNone(scene_establish.picture(self.data, self.pid, scene))   # the real index never sees it
        self.assertIsNone(scene_establish.reference(self.data, self.pid, scene))
        self.assertEqual(scene_establish.light_sentence({"time": "night"}), "")
        args = r._submit_args(job)
        self.assertFalse(any("establish" in str(x) for x in (args[1] if len(args) > 1 else []) or []))
        self.assertNotIn("readable", args[0])
        own = scene_establish._load(self.data, self.pid, True).get(str(scene)) or {}
        self.assertEqual(own.get("state"), "ready")
        self.assertIn(os.path.join("establish", "trainee"), own["path"])
        n = self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='trainee_establishing'").fetchone()[0]
        self.assertEqual(n, 1)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='establishing'").fetchone()[0], 0)
        log = self.p.conn.execute("SELECT feature, decision, subject FROM trainee_log").fetchall()
        self.assertEqual([(x["feature"], x["decision"], x["subject"]) for x in log], [("scene_establishing", "establish", f"scene:{scene}")])

    def test_one_picture_per_script_scene(self):
        r = self.runner()
        scenes = {row["data"]["story_scene"] for row in self.rows}
        for row in self.rows:
            job = self.p.job(self.p.create_job(row["id"], "image_gen"))
            self._drive(r, job)
        n = self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='trainee_establishing'").fetchone()[0]
        self.assertEqual(n, len(scenes))

    def test_an_indoor_scene_is_recorded_as_skip(self):
        d = dict(self.first["data"], location="INT. bedroom")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.first["id"]))
        self.p.conn.commit()
        scene = d["story_scene"]
        for row in self.rows:                                               # every shot of that scene is indoor
            if row["data"].get("story_scene") == scene and row["id"] != self.first["id"]:
                self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                                    (json.dumps(dict(row["data"], location="INT. bedroom"), ensure_ascii=False), row["id"]))
        self.p.conn.commit()
        r = self.runner()
        job = self.p.job(self.p.create_job(self.first["id"], "image_gen"))
        self._drive(r, job, 3)
        log = self.p.conn.execute("SELECT decision, would_do FROM trainee_log").fetchall()
        self.assertEqual([x["decision"] for x in log], ["skip"])
        self.assertEqual(json.loads(log[0]["would_do"])["reason"], "establish_skip_indoor")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='trainee_establishing'").fetchone()[0], 0)


class EstablishDirectionL19Tests(unittest.TestCase):
    """KLD-18 / bài học L19 (duyệt 08/10, cảnh nhảy #22): the establishing picture must LOOK THE SAME WAY as the background the shots
    need. Turns 1–2: a model-drawn wide view from outside the wall / another direction dragged every shot's background wrong; turn 3: the
    3D render on the camera's own axis kept the background right for 11,5 s. So at a 3D place the establishing picture IS the render
    (0 USD, no picture model); a model-drawn one whose direction differs from the first frame's camera is not used, and said."""

    def setUp(self):
        flags_on(self, "scene_establishing", "place_render_refs")
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        rows = shots.shots_of(self.p, self.pid)
        self.scene = rows[0]["data"]["story_scene"]
        self.rows = scene_establish.scene_rows(self.p.conn, self.pid, self.scene)
        from core import place_refs
        self._m = mock.patch.object(place_refs, "missing", return_value=False)
        self._m.start()
        self.addCleanup(self._m.stop)
        from core.providers import MockImageProvider
        self.provider = MockImageProvider(polls_to_finish=1)
        self.sent = []
        real = self.provider.submit
        def submit(*a, **k):
            mid = real(*a, **k)                                             # a TypeError (no per-job model) is not a send
            self.sent.append(a)
            return mid
        self.provider.submit = submit
        self.said = []

    def _plates(self, degs):
        """plates/index.json: the scene's shots rendered, shot i looking at background degs[i] (the first row = the first frame)."""
        from PIL import Image
        idx = {}
        for i, r in enumerate(self.rows):
            if i >= len(degs):
                break
            d = os.path.join(self.data, "cache", str(r["id"]))
            os.makedirs(d, exist_ok=True)
            plate = os.path.join(d, "plate.png")
            Image.new("RGB", (36, 64), (40 + i, 90, 120)).save(plate)
            idx[str(r["id"])] = {"plate": plate, "key": f"k{r['id']}", "spot": "bac_thang_giua", "place": "Tháp Đồng Hồ",
                                 "view": {"background_deg": degs[i]}}
        os.makedirs(os.path.join(self.data, str(self.pid), "plates"), exist_ok=True)
        with open(os.path.join(self.data, str(self.pid), "plates", "index.json"), "w", encoding="utf-8") as f:
            json.dump(idx, f)
        return idx

    def _step(self, trainee=False):
        return scene_establish.step(self.p.conn, self.pid, self.scene, self.provider, self.data,
                                    say=lambda sev, code, msg: self.said.append((sev, code, msg)), trainee=trainee)

    def _paid(self, stage="establishing"):
        return self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage=?", (stage,)).fetchone()[0]

    def test_a_3d_place_gets_the_render_on_the_wide_shot_axis_for_0_usd(self):
        idx = self._plates([140.0] * len(self.rows))
        self.assertEqual(self._step(), "ready")
        path = scene_establish.picture(self.data, self.pid, self.scene)
        self.assertTrue(path and os.path.exists(path))
        rec = scene_establish._load(self.data, self.pid)[str(self.scene)]
        self.assertEqual(rec["source"], "render_3d")
        self.assertIn(rec["render"], [v["plate"] for v in idx.values()])
        self.assertEqual(self.sent, [])                                     # no paid picture model
        self.assertEqual(self._paid(), 0)
        self.assertEqual(self._step(), "ready")                             # stays, still 0 USD
        self.assertEqual(self.sent, [])

    def test_no_3d_draws_with_the_model_as_before(self):
        self.assertEqual(self._step(), "waiting")
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self._paid(), 1)
        self.assertNotEqual(scene_establish._load(self.data, self.pid)[str(self.scene)].get("source"), "render_3d")

    def test_a_model_picture_facing_another_way_is_not_used(self):
        if len(self.rows) < 2:
            self.skipTest("cảnh cần ≥ 2 shot")
        from core import place_refs
        # no render for the scene (Blender failed) — the model draws from a reference whose direction is known (180°) but the first
        # frame's camera looks at 20°
        with mock.patch.object(place_refs, "scene_render_rec", return_value=None), \
                mock.patch.object(scene_establish, "scene_pictures", return_value=["ref_180.png"]), \
                mock.patch.object(scene_establish, "pictures_deg", return_value=180.0), \
                mock.patch.object(scene_establish, "first_frame_deg", return_value=20.0):
            self.assertEqual(self._step(), "skipped")
        self.assertEqual(self.sent, [])
        self.assertEqual(self._paid(), 0)
        rec = scene_establish._load(self.data, self.pid)[str(self.scene)]
        self.assertEqual(rec["state"], "failed")
        self.assertIn("hướng", rec["error"])
        self.assertTrue(any(code == "establish_direction" for _, code, _ in self.said))
        self.assertIsNone(scene_establish.reference(self.data, self.pid, self.scene))

    def test_a_ready_model_picture_whose_direction_differs_is_dropped(self):
        from core import place_refs
        with mock.patch.object(place_refs, "scene_render_rec", return_value=None), \
                mock.patch.object(scene_establish, "pictures_deg", return_value=30.0), \
                mock.patch.object(scene_establish, "first_frame_deg", return_value=30.0):
            self.assertEqual(self._step(), "waiting")
            for _ in range(3):
                if self._step() == "ready":
                    break
            self.assertIsNotNone(scene_establish.picture(self.data, self.pid, self.scene))
        with mock.patch.object(place_refs, "scene_render_rec", return_value=None), \
                mock.patch.object(scene_establish, "pictures_deg", return_value=30.0), \
                mock.patch.object(scene_establish, "first_frame_deg", return_value=210.0):
            self.assertEqual(self._step(), "skipped")
        self.assertIsNone(scene_establish.picture(self.data, self.pid, self.scene))
        self.assertTrue(any(code == "establish_direction" for _, code, _ in self.said))

    def test_trainee_uses_the_render_too_and_still_does_not_act(self):
        from tests._flags import flags_trainee
        flags_trainee(self, "scene_establishing")
        self._plates([140.0] * len(self.rows))
        self.assertEqual(self._step(trainee=True), "ready")
        self.assertIsNone(scene_establish.picture(self.data, self.pid, self.scene))     # the real index never sees it
        self.assertIsNone(scene_establish.reference(self.data, self.pid, self.scene))
        own = scene_establish._load(self.data, self.pid, True)[str(self.scene)]
        self.assertEqual(own["source"], "render_3d")
        self.assertIn(os.path.join("establish", "trainee"), own["path"])
        self.assertEqual(self.sent, [])
        self.assertEqual(self._paid("trainee_establishing") + self._paid(), 0)
        self.assertEqual(self.said, [])                                     # nothing shown
        log = self.p.conn.execute("SELECT decision, cost_usd FROM trainee_log").fetchall()
        self.assertEqual([(x["decision"], x["cost_usd"]) for x in log], [("establish", 0.0)])


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
