"""Người dùng 07/10: (1) hiệu ứng nút sáng BẬT SẴN ở mọi tài khoản, ai muốn tắt thì tắt (công tắc riêng từng người, nhớ lần sau);
(2) nút bước chính ở các màn làm việc to và rõ hơn; (3) gộp khối trùng ở Storyboard (cờ chat_first: bản đồ tiến độ đã nói)."""
import os
import shutil
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import features, next_glow, user_prefs
from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class FlagTests(unittest.TestCase):
    def test_glow_is_on_by_default_without_any_setting(self):
        os.environ.pop("FEATURE_NEXT_GLOW", None)
        self.assertTrue(features.FEATURES["next_glow"]["verified"])
        self.assertTrue(features.on("next_glow"))

    def test_the_question_after_approve_all_lights_its_yes_button_too(self):
        self.assertIn(".st-key-approve_all_yes button", next_glow.css([("key", "approve_all")], []))

    def test_main_step_buttons_are_big(self):
        css = next_glow.big_css(7)
        for key in ("script-cta_7", "script-cta-lock_7", "gen_img_7", "approve_all", "llm_mot_7", "btn_ok_all", "gen_vid_7"):
            self.assertIn(f".st-key-{key} button", css)
        self.assertIn("min-height", css)


class ScreenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for k, v in (("PIPELINE_DB", os.path.join(self.tmp, "m.sqlite")), ("PIPELINE_DATA", os.path.join(self.tmp, "projects")),
                     ("KNOWLEDGE_USER_DIR", os.path.join(self.tmp, "ku"))):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        for k in ("FEATURE_CHAT_FIRST", "FEATURE_NEXT_GLOW"):
            os.environ.pop(k, None)
        self.p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        self.pid = self.p.create_project("x")
        self.p.create_scene(self.pid, 1, "CẢNH 1")

    def lit(self, at):
        return [h.proto.body for h in at.get("html") if "next-glow" in h.proto.body]

    def test_lit_for_everyone_even_with_the_chat_screen_off_and_off_for_a_person_who_turns_it_off(self):
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(self.lit(at)), 1)
        self.assertTrue(any(h for h in at.get("html") if "min-height" in h.proto.body and "gen_img_" in h.proto.body))   # big buttons
        user_prefs.set(self.p.conn, None, "next_glow", False)                    # this machine / person turned it off
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertEqual(self.lit(at), [])

    def test_the_person_switch_is_in_the_settings(self):
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertTrue(any(t.key == "pref_next_glow" for t in at.toggle))
        at.toggle(key="pref_next_glow").set_value(False).run()
        self.assertFalse(user_prefs.get(Pipeline(connect(os.environ["PIPELINE_DB"])).conn, None, "next_glow"))


class StoryboardMergeTests(unittest.TestCase):
    def test_no_repeated_counters_when_the_progress_map_is_on(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, v in (("PIPELINE_DB", os.path.join(tmp, "m.sqlite")), ("PIPELINE_DATA", os.path.join(tmp, "projects")),
                     ("KNOWLEDGE_USER_DIR", os.path.join(tmp, "ku")), ("FEATURE_CHAT_FIRST", "1")):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        pid = p.create_project("x")
        sid = p.create_scene(pid, 1, "CẢNH 1")
        p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,'image_gen','pending_review',"
                       "'t','t')", (pid, sid))
        p.conn.commit()
        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state["step"] = "Storyboard"
        at.run()
        self.assertFalse(at.exception)
        page = " ".join(m.value for m in at.markdown) + " ".join(h.proto.body for h in at.get("html"))
        self.assertNotIn("Đang gen / chờ gen", page)                              # the 4 counters → the progress map + pills
        self.assertFalse(any(e.label.startswith("Bảng trạng thái từng cảnh") for e in at.expander))
        self.assertTrue(any(e.label.startswith("🗺 Tiến độ") for e in at.expander))


if __name__ == "__main__":
    unittest.main()


class VideoMergeTests(unittest.TestCase):
    """Chụp màn 07/10 (màn Video): nhãn '3 cần duyệt' + thẻ 'Chờ duyệt 3' nhưng nút 'Duyệt tất cả (2 clip)' — clip vừa gen còn đang tự
    kiểm (succeeded) bị đếm là 'cần duyệt'. Cờ chat_first: số khớp nút, clip đang tự kiểm nói riêng; bỏ 4 thẻ số + thanh % (bản đồ đã nói)."""

    def test_counts_match_the_button_and_no_repeated_counters(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, v in (("PIPELINE_DB", os.path.join(tmp, "m.sqlite")), ("PIPELINE_DATA", os.path.join(tmp, "projects")),
                     ("KNOWLEDGE_USER_DIR", os.path.join(tmp, "ku")), ("FEATURE_CHAT_FIRST", "1")):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        pid = p.create_project("x")
        for i, state in enumerate(("pending_review", "pending_review", "succeeded"), 1):
            sid = p.create_scene(pid, i, f"CẢNH {i}")
            p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,'image_gen','approved','t','t')",
                           (pid, sid))
            p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?, 'x', 'approved')", (sid,))
            p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,'video_gen',?,'t','t')",
                           (pid, sid, state))
        p.conn.commit()
        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state["step"] = "Video"
        at.run()
        self.assertFalse(at.exception)
        page = " ".join(m.value for m in at.markdown) + " ".join(h.proto.body for h in at.get("html"))
        self.assertNotIn("Clip dùng được", page)
        self.assertIn("2 cần duyệt", page)
        self.assertNotIn("3 cần duyệt", page)
        self.assertIn("1 đang tự kiểm", page)
        self.assertTrue(any(b.key == f"vid_ok_all_{pid}" and "(2 clip)" in b.label for b in at.button))
