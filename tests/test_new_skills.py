import os
import shutil
import subprocess
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import ffmpeg_studio, knowledge, llm_runner, prompts, style
from core.db import connect
from core.pipeline import Pipeline
from tests.test_autopilot import Setup
from tests.test_keep_audio import ffmpeg_available

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cf00000301010018dd8db00000000049454e44ae426082")


class KnowledgeWiringTests(Setup):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_director_gets_the_directing_method_and_motion_gets_the_video_prompt_rules(self):
        self.build()
        self.assertIn("Phương pháp đạo diễn", prompts.build_director_bundle(self.p, self.pid))
        for pid_video_model in (None,):
            motion = prompts.build_motion_bundle(self.p, self.pid)
            self.assertIn("World Bible (khóa nhất quán", motion)          # t2v_prompt_structure.md
            self.assertIn("Cảnh hành động phức tạp", motion)             # motion_complex_shots.md
            self.assertNotIn("Seedance Director", motion)                # only for Seedance projects
        self.p.conn.execute("UPDATE projects SET video_model='seedance-2.0' WHERE id=?", (self.pid,))
        self.p.conn.commit()
        self.assertIn("Seedance — quy trình tối ưu prompt", prompts.build_motion_bundle(self.p, self.pid))

    def test_new_documents_are_listed_in_the_knowledge_settings(self):
        titles = {d["title"] for d in knowledge.overview("director")["docs"]}
        self.assertIn("Phương pháp đạo diễn", titles)
        motion = {d["title"] for d in knowledge.overview("motion")["docs"]}
        self.assertTrue({"Cấu trúc prompt video (World Bible + 7 đoạn)", "Cảnh hành động phức tạp", "Quy trình Seedance Director"} <= motion)


class WorldBibleTests(Setup):
    def test_saved_style_bible_reaches_director_and_motion_prompts(self):
        self.build()
        self.assertNotIn("World Bible của dự án", prompts.build_director_bundle(self.p, self.pid))
        style.save(self.p, self.pid, {"render_style": "2D cel-shaded, thick outline", "palette": "teal and amber", "physics": "  "})
        director = prompts.build_director_bundle(self.p, self.pid)
        self.assertIn("2D cel-shaded, thick outline", director)
        self.assertIn("teal and amber", director)
        self.assertNotIn("Vật lý/thời tiết", director)                       # empty fields are left out
        self.assertIn("teal and amber", prompts.build_motion_bundle(self.p, self.pid))
        style.save(self.p, self.pid, {})
        self.assertNotIn("World Bible của dự án", prompts.build_director_bundle(self.p, self.pid))

    def test_analysis_returns_a_draft_and_needs_a_picture(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "ref.png")
        with open(path, "wb") as f:
            f.write(PNG)
        draft = style.analyse(llm_runner.MockLlm(), [path])
        self.assertTrue(draft["render_style"] and draft["palette"])
        self.assertEqual(draft["confidence"], "medium")
        self.assertTrue(any("1 ảnh" in f for f in draft.get("check_flags", [])) or draft["confidence"] == "medium")
        with self.assertRaises(llm_runner.LlmError):
            style.analyse(llm_runner.MockLlm(), [os.path.join(tmp, "nothing.png")])

    def test_a_draft_missing_required_fields_is_rejected(self):
        class Bad:
            def complete(self, prompt, images=()):
                return llm_runner.LlmReply('{"render_style": "x"}', 1, 1)

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "ref.png")
        with open(path, "wb") as f:
            f.write(PNG)
        with self.assertRaises(llm_runner.LlmError):
            style.analyse(Bad(), [path])


@unittest.skipUnless(ffmpeg_available(), "ffmpeg not installed")
class ResizeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ff = ffmpeg_studio.find_ffmpeg()
        self.src = os.path.join(self.dir, "src.mp4")
        subprocess.run([self.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=6:s=640x360:r=24",
                        "-f", "lavfi", "-i", "sine=f=440:d=6", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", self.src], check=True)

    def test_output_has_the_requested_size_and_fits_the_limit(self):
        dst = os.path.join(self.dir, "out.mp4")
        res = ffmpeg_studio.resize_to_size(self.src, dst, 540, 960, max_mb=0.4)
        self.assertTrue(res["fits"])
        self.assertLessEqual(os.path.getsize(dst), 0.4 * 1e6)
        info = subprocess.run([self.ff, "-hide_banner", "-i", dst], capture_output=True, text=True).stderr
        self.assertIn("540x960", info)
        self.assertTrue(ffmpeg_studio.has_audio(dst))

    def test_without_a_limit_it_just_rescales_and_a_tiny_limit_is_refused(self):
        dst = os.path.join(self.dir, "plain.mp4")
        self.assertIsNone(ffmpeg_studio.resize_to_size(self.src, dst, 320, 180)["video_kbps"])
        with self.assertRaises(ValueError):
            ffmpeg_studio.resize_to_size(self.src, os.path.join(self.dir, "tiny.mp4"), 320, 180, max_mb=0.005)


class OldDatabaseTests(Setup):
    def test_style_bible_reads_do_not_crash_on_a_database_without_the_column(self):
        self.build()
        self.p.conn.execute("ALTER TABLE projects DROP COLUMN world_bible")     # a database from before the feature
        self.p.conn.commit()
        self.assertEqual(style.load(self.p, self.pid)["palette"], "")
        self.assertNotIn("World Bible của dự án", prompts.build_director_bundle(self.p, self.pid))


class PanelTests(unittest.TestCase):
    def setUp(self):
        os.environ["DASHBOARD_EXPERT"] = "1"      # these tests use the advanced panels (kế hoạch V4 5.3)
        self.addCleanup(os.environ.pop, "DASHBOARD_EXPERT", None)

    def test_style_panel_is_in_step_1(self):
        tmp = tempfile.mkdtemp()
        os.environ["PIPELINE_DB"] = os.path.join(tmp, "m.sqlite")
        os.environ["PIPELINE_DATA"] = os.path.join(tmp, "projects")
        try:
            Pipeline(connect(os.environ["PIPELINE_DB"])).create_project("demo")
            at = AppTest.from_file(APP, default_timeout=30).run()
            self.assertFalse(at.exception)
            self.assertTrue(any("Phong cách hình ảnh" in e.label for e in at.expander))
        finally:
            os.environ.pop("PIPELINE_DB", None)
            os.environ.pop("PIPELINE_DATA", None)


if __name__ == "__main__":
    unittest.main()
