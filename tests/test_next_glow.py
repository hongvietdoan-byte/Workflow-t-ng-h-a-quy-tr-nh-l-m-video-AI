"""Nút của bước kế sáng lên (người dùng 07/10: 'người mới chưa từng biết quy trình cũng dùng được'; cờ chat_first):
MỘT đích sáng mỗi lúc — nút cần bấm, hoặc tab / ô thanh bước khi việc kế nằm ở màn khác. Màu xanh lá, nhịp dịu; tắt chuyển động
(prefers-reduced-motion) → viền sáng đứng yên; nhãn '👉 Bấm tiếp' trên nút."""
import unittest

from core import next_glow as G

STEPS = ["⌂ Tất cả dự án", "Kịch bản", "Storyboard", "Video", "Bản giao"]


def rows(image="none", motion="none", video="none", n=2):
    return [{"idx": i + 1, "image": image, "motion": motion, "video": video} for i in range(n)]


class TargetTests(unittest.TestCase):
    def test_script_screen_follows_the_one_primary_action(self):
        self.assertEqual(G.target(1, "analyse", [], 5), [("key", "box_in_5")])
        self.assertEqual(G.target(1, "plan", rows(), 5), [("key", "script-cta_5")])
        self.assertEqual(G.target(1, "budget", rows(), 5), [("key", "script-cta-budget_5")])
        self.assertEqual(G.target(1, "lock", rows(), 5), [("key", "script-cta-lock_5")])
        self.assertEqual(G.target(1, "next", rows(), 5), [("key", "script-cta-next_5")])
        self.assertEqual(G.target(1, "auto", rows(), 5), [])                      # running by itself: nothing to press

    def test_storyboard_goes_images_then_review_then_motion_then_video(self):
        self.assertEqual(G.target(2, None, rows(), 5), [("key", "gen_img_5")])
        self.assertEqual(G.target(2, None, rows(image="review"), 5), [("key", "approve_all")])
        self.assertEqual(G.target(2, None, rows(image="running"), 5), [])          # wait: being made
        self.assertEqual(G.target(2, None, rows(image="done"), 5), [("tab", 2), ("key", "llm_mot_5")])
        self.assertEqual(G.target(2, None, rows(image="done"), 5, on_motion_tab=True), [("key", "llm_mot_5")])
        self.assertEqual(G.target(2, None, rows(image="done", motion="review"), 5, on_motion_tab=True), [("key", "btn_ok_all")])
        self.assertEqual(G.target(2, None, rows(image="done", motion="done"), 5), [("step", "Video")])

    def test_video_screen(self):
        self.assertEqual(G.target(3, None, rows("done", "done"), 5), [("key", "gen_vid_5")])
        self.assertEqual(G.target(3, None, rows("done", "done", "done"), 5), [("step", "Bản giao")])

    def test_css_has_the_glow_the_label_and_a_still_version(self):
        css = G.css([("key", "gen_img_5"), ("step", "Video"), ("tab", 2)], STEPS)
        self.assertIn(".st-key-gen_img_5 button", css)
        self.assertIn("@keyframes", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("Bấm tiếp", css)
        # DOM thật Streamlit 1.65 (đo bằng trình duyệt 07/10): mỗi ô thanh bước = div bọc label; tab = [role=tab][data-key=0..]
        self.assertIn('.st-key-step [role="radiogroup"] > :nth-child(4) label', css)     # Video = 4th screen in the bar
        self.assertIn('.st-key-sb_tab [role="tab"][data-key="1"]', css)
        self.assertEqual(G.css([], STEPS), "")

    def test_a_key_with_odd_characters_is_never_written_into_css(self):
        self.assertEqual(G.css([("key", "x}{body{display:none")], STEPS), "")


if __name__ == "__main__":
    unittest.main()


class ScreenTests(unittest.TestCase):
    def test_the_script_screen_lights_the_plan_button_after_the_split(self):
        import os, shutil, tempfile
        from streamlit.testing.v1 import AppTest
        from core.db import connect
        from core.pipeline import Pipeline
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for k, v in (("PIPELINE_DB", os.path.join(tmp, "m.sqlite")), ("PIPELINE_DATA", os.path.join(tmp, "projects")),
                     ("KNOWLEDGE_USER_DIR", os.path.join(tmp, "ku")), ("FEATURE_CHAT_FIRST", "1")):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        pid = p.create_project("x")
        p.create_scene(pid, 1, "CẢNH 1")
        at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"), default_timeout=30).run()
        self.assertFalse(at.exception)
        styles = [h.proto.body for h in at.get("html") if "next-glow" in h.proto.body]
        self.assertEqual(len(styles), 1)
        self.assertIn(f".st-key-script-cta_{pid} button", styles[0])
        os.environ["FEATURE_NEXT_GLOW"] = "0"                                   # 07/10: own flag (on by default), not chat_first
        self.addCleanup(os.environ.pop, "FEATURE_NEXT_GLOW", None)
        at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"), default_timeout=30).run()
        self.assertFalse([h for h in at.get("html") if "next-glow" in h.proto.body])     # flag off: nothing lit


class BandTests(unittest.TestCase):
    def test_the_next_step_line_says_where_the_lit_button_is(self):
        """Chụp màn 07/10: nút sáng có thể ở dưới lưới ảnh (ngoài màn) — dòng 'Việc tiếp theo' nói 'nút sáng xanh' để người mới tìm."""
        import os
        from core.db import connect
        from core.pipeline import Pipeline
        from dashboard.design.screens import shell_parts
        os.environ["FEATURE_CHAT_FIRST"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHAT_FIRST", None)
        p = Pipeline(connect())
        pid = p.create_project("x")
        p.create_scene(pid, 1, "CẢNH 1")
        text, level = shell_parts.next_line(p, pid, 1, "")
        self.assertEqual(level, "todo")
        self.assertTrue(text.startswith("🟢 Nút sáng xanh: "), text)
        os.environ["FEATURE_NEXT_GLOW"] = "0"
        self.addCleanup(os.environ.pop, "FEATURE_NEXT_GLOW", None)
        self.assertFalse(shell_parts.next_line(p, pid, 1, "")[0].startswith("🟢"))

    def test_no_lit_claim_when_nothing_is_lit(self):
        import os
        from core.db import connect
        from core.pipeline import Pipeline
        from dashboard.design.screens import shell_parts
        os.environ["FEATURE_CHAT_FIRST"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHAT_FIRST", None)
        p = Pipeline(connect())
        pid = p.create_project("x")
        sid = p.create_scene(pid, 1, "CẢNH 1")
        for kind, state in (("image_gen", "approved"), ("video_gen", "running")):   # the clip is being made: nothing to press
            p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,'t','t')",
                           (pid, sid, kind, state))
        p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?, 'x', 'approved')", (sid,))
        text, level = shell_parts.next_line(p, pid, 3, "")                       # Video screen while a clip is made — no lit button
        self.assertFalse(text.startswith("🟢"), text)


class VideoAndDeliveryTests(unittest.TestCase):
    """Người dùng 07/10 ('làm tiếp'): cùng cách 'một nút chính sáng, to, gọn' ở màn Video và Bản giao."""

    def test_video_screen_lights_approve_all_clips_when_clips_wait(self):
        self.assertEqual(G.target(3, None, rows("done", "done", "review"), 5), [("key", "vid_ok_all_5")])

    def test_delivery_screen_render_then_check(self):
        done = rows("done", "done", "done")
        self.assertEqual(G.target(4, None, done, 5, final="none"), [("key", "render_5")])
        self.assertEqual(G.target(4, None, done, 5, final="unchecked"), [("key", "final_qc_btn_5")])
        self.assertEqual(G.target(4, None, done, 5, final="ok"), [])
        self.assertEqual(G.target(4, None, rows("done", "done", "none"), 5, final="none"), [("step", "Video")])   # clips first

    def test_the_new_main_buttons_are_big_and_approve_all_clips_is_one_click(self):
        import os
        from dashboard.design import components as D
        css = G.big_css(5)
        for key in ("vid_ok_all_5", "render_5", "deliver_5"):
            self.assertIn(f".st-key-{key} button", css)
        os.environ["FEATURE_CHAT_FIRST"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHAT_FIRST", None)
        self.assertTrue(D.one_click("vid_ok_all_5"))
