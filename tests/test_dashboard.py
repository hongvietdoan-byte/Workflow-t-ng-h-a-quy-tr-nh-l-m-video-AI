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

    def test_music_step_with_mock_audio_creates_and_selects_draft(self):
        self.seed()
        os.environ["AUDIO_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
            self.assertFalse(at.exception)
            next(b for b in at.button if "bản nháp" in b.label).click().run()
            next(b for b in at.button if "Kiểm tra" in b.label).click().run()
            next(b for b in at.button if "Chọn bản này" in b.label).click().run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("AUDIO_PROVIDER", None)
        music_dir = os.path.join(self.tmp, "projects", "1", "music")
        self.assertEqual(os.listdir(music_dir), ["selected.wav"])

    def test_final_step_lists_generated_clips_and_shows_total(self):
        self.seed()
        videos = os.path.join(self.tmp, "projects", "1", "videos")
        os.makedirs(videos)
        open(os.path.join(videos, "01.mp4"), "wb").write(b"not a real video")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[5]).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("CẢNH 1" in c.label for c in at.checkbox))
        self.assertTrue(any("Tổng thời lượng dự kiến" in i.value for i in at.info))
        at.radio(key="tr_1").set_value("crossfade").run()
        self.assertTrue(any("crossfade cần ít nhất 2 clip" in w.value for w in at.warning))
        self.assertTrue(next(b for b in at.button if "Render Final" in b.label).disabled)

    def test_sfx_created_selected_and_counted_for_final_mix(self):
        self.seed()
        os.environ["AUDIO_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
            self.assertFalse(at.exception)
            at.text_input(key="sfx_p_1").set_value("door slam").run()
            next(b for b in at.button if "Tạo SFX" in b.label).click().run()
            next(b for b in at.button if "Kiểm tra" in b.label and b.key == "ax_refresh_1").click().run()
            at.checkbox(key="ax_use_1_0").set_value(True).run()
            self.assertFalse(at.exception)
            at.radio(key="step").set_value(at.radio(key="step").options[5]).run()
            self.assertTrue(any("đưa vào bản ghép: 1" in c.value for c in at.caption))
        finally:
            os.environ.pop("AUDIO_PROVIDER", None)

    def test_character_edit_and_unlock_from_dashboard(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.text_area(key=f"cd_{pid}_Lyra").set_value("Nữ, tóc đỏ").run()
        next(b for b in at.button if b.key == f"cs_{pid}_Lyra").click().run()
        self.assertFalse(at.exception)
        row = Pipeline(connect(self.db)).conn.execute("SELECT description FROM characters WHERE name='Lyra'").fetchone()
        self.assertEqual(row["description"], "Nữ, tóc đỏ")
        from core.llm_io import lock_character_bible
        lock_character_bible(Pipeline(connect(self.db)), pid)
        at = AppTest.from_file(APP, default_timeout=30).run()
        next(b for b in at.button if b.key == "btn_bad_unlock").click().run()
        self.assertEqual(Pipeline(connect(self.db)).conn.execute(
            "SELECT COUNT(*) c FROM characters WHERE locked=1").fetchone()["c"], 0)

    def test_llm_runner_buttons_with_mock_model(self):
        p = Pipeline(connect(self.db))
        pid = p.create_project("Demo")
        p.create_scene(pid, 1, "CẢNH 1")
        os.environ["LLM_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            next(b for b in at.button if b.key == f"llm_dir_{pid}").click().run()
            self.assertFalse(at.exception)
            self.assertFalse(at.error)
            row = Pipeline(connect(self.db)).conn.execute("SELECT name FROM characters").fetchone()
            self.assertEqual(row["name"], "Nhân vật chính")
            from core.llm_io import lock_character_bible
            lock_character_bible(Pipeline(connect(self.db)), pid)
            q = Pipeline(connect(self.db))
            scene = q.conn.execute("SELECT id FROM scenes").fetchone()["id"]
            job = q.create_job(scene)
            q.start(job)
            q.succeed(job)
            img = os.path.join(self.tmp, "projects", str(pid), "images")
            os.makedirs(img)
            with open(os.path.join(img, f"job_{job}.png"), "wb") as f:
                f.write(bytes([0x89]) + b"PNG" + b"0" * 20)
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
            next(b for b in at.button if b.key == f"llm_qc_all_{pid}").click().run()
            self.assertFalse(at.exception)
            state = Pipeline(connect(self.db)).conn.execute("SELECT state FROM jobs").fetchone()["state"]
            self.assertEqual(state, "pending_review")  # human_qc: mock scores wait for a person
        finally:
            os.environ.pop("LLM_PROVIDER", None)

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

    def test_image_step_with_mock_provider_generates_files(self):
        from core.llm_io import lock_character_bible
        p, pid = self.seed()
        lock_character_bible(p, pid)
        os.environ["IMAGE_PROVIDER"] = "mock"
        os.environ["HEARTBEAT_SEC"] = "0"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
            next(b for b in at.button if "Tạo job gen ảnh" in b.label).click().run()
            next(b for b in at.button if "heartbeat" in b.label).click().run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("IMAGE_PROVIDER", None)
            os.environ.pop("HEARTBEAT_SEC", None)
        row = Pipeline(connect(self.db)).conn.execute(
            "SELECT state, result_path FROM jobs WHERE type='image_gen'").fetchone()
        self.assertEqual(row["state"], "succeeded")
        self.assertTrue(os.path.exists(row["result_path"]))


if __name__ == "__main__":
    unittest.main()
