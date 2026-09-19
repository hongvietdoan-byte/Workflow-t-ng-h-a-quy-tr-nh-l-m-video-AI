import os
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class DashboardSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        os.environ["PIPELINE_DB"] = self.db
        os.environ["PIPELINE_DATA"] = os.path.join(self.tmp, "projects")

    def tearDown(self):
        os.environ.pop("PIPELINE_DB", None)
        os.environ.pop("PIPELINE_DATA", None)

    def seed(self):
        p = Pipeline(connect(self.db))
        pid = p.create_project("Demo")
        p.create_scene(pid, 1, "CẢNH 1")
        store_scene_analysis(p, pid, ANALYSIS)
        return p, pid

    def test_empty_state_prompts_project_creation(self):
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Chưa có dự án" in i.value for i in at.info))

    def test_every_step_renders_without_error(self):
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        options = list(at.radio(key="step").options)
        self.assertEqual(len(options), 7)
        for option in options:
            at.radio(key="step").set_value(option).run()
            self.assertFalse(at.exception, option)

    def test_create_image_jobs_and_mode_switch(self):
        p, pid = self.seed()
        from core.llm_io import lock_character_bible
        lock_character_bible(p, pid)
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        next(b for b in at.button if "Tạo job gen ảnh" in b.label).click().run()
        self.assertFalse(at.exception)
        rows = Pipeline(connect(self.db)).conn.execute("SELECT type, state FROM jobs").fetchall()
        self.assertEqual([(r["type"], r["state"]) for r in rows], [("image_gen", "queued")])
        at.radio(key=f"mode_{pid}").set_value("auto").run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["operating_mode"], "auto")

    def test_pause_button_sets_flag(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        next(b for b in at.button if "Pause" in b.label).click().run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["paused"], 1)

    def test_video_step_with_mock_provider_runs_to_completion(self):
        from core.llm_io import approve_motion_prompt, lock_character_bible, store_motion_prompts
        p, pid = self.seed()
        lock_character_bible(p, pid)
        scene = p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        img = p.create_job(scene)
        p.start(img)
        p.succeed(img)
        p.approve(img)
        store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        approve_motion_prompt(p, scene)
        os.environ["VIDEO_PROVIDER"] = "mock"
        os.environ["HEARTBEAT_SEC"] = "0"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
            next(b for b in at.button if "Tạo job gen video" in b.label).click().run()
            next(b for b in at.button if "heartbeat" in b.label).click().run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("VIDEO_PROVIDER", None)
            os.environ.pop("HEARTBEAT_SEC", None)
        row = Pipeline(connect(self.db)).conn.execute(
            "SELECT state, result_path FROM jobs WHERE type='video_gen'").fetchone()
        self.assertEqual(row["state"], "succeeded")
        self.assertTrue(os.path.exists(row["result_path"]))


if __name__ == "__main__":
    unittest.main()
