"""Tab Kịch bản kiểu chat — Đợt 2 (người dùng 07/10; cờ chat_first): dự án bắt đầu từ chat, Đạo diễn dẫn việc kế trong luồng chat,
kết quả Director kể lại trong chat, video động tác chờ được tự gắn khi cảnh có motion prompt."""
import os
import shutil
import tempfile
import unittest

from core import chat_flow as F
from core import chat_intake as I
from core.db import connect
from core.pipeline import Pipeline


class NameTests(unittest.TestCase):
    def test_the_first_plain_line_names_the_project(self):
        self.assertEqual(F.project_name("Khủng Long Đỏ\nCẢNH 1 - NGÀY", [], "07/10"), "Khủng Long Đỏ")

    def test_a_scene_heading_is_not_a_name(self):
        self.assertEqual(F.project_name("CẢNH 1 - ĐÊM, RỪNG\nSương mù", [], "07/10"), "Sương mù")

    def test_a_file_names_it_when_there_is_no_text(self):
        self.assertEqual(F.project_name("", ["kich_ban_tet.docx"], "07/10"), "kich ban tet")

    def test_nothing_at_all_gives_the_time(self):
        self.assertEqual(F.project_name("", [], "07/10 18:00"), "Dự án 07/10 18:00")

    def test_long_lines_are_cut(self):
        self.assertTrue(F.project_name("x" * 90, [], "t").endswith("…"))


class StartTests(unittest.TestCase):
    def test_a_project_started_from_the_chat_has_the_new_project_defaults(self):
        p = Pipeline(connect())
        pid = F.start_project(p, "Khủng Long Đỏ", [], "07/10")
        proj = p.project(pid)
        self.assertEqual((proj["name"], proj["aspect"], proj["genre"], proj["game"]), ("Khủng Long Đỏ", "9:16", "SHORT_FORM", "FF"))


class GuideTests(unittest.TestCase):
    ST = {"scenes": 4, "characters": ["Kelly", "Maxim"], "no_anchor": ["Maxim"], "locked": False}

    def test_the_plan_step_names_what_is_missing(self):
        line = F.guide("plan", self.ST, missing=["Tháp Đồng Hồ"])
        self.assertIn("4 cảnh", line)
        self.assertIn("Tháp Đồng Hồ", line)

    def test_the_lock_step_names_the_anchors_waiting(self):
        self.assertIn("Maxim", F.guide("lock", self.ST))

    def test_waiting_files_are_said_first(self):
        self.assertTrue(F.guide("next", self.ST, waiting=2).startswith("Còn **2 tệp**"))

    def test_nothing_to_add_before_the_analysis(self):
        self.assertEqual(F.guide("analyse", self.ST), "")

    def test_the_director_run_is_told_with_the_flagged_scenes(self):
        note = F.director_note({"characters": 2, "scenes": 4, "flagged": [2, 5]}, self.ST, missing=["Tháp"])
        for word in ("2 nhân vật", "Kelly", "4 cảnh", "**2**", "**5**", "Tháp", "Maxim"):
            self.assertIn(word, note)


class RetryTests(unittest.TestCase):
    def test_a_waiting_motion_video_is_attached_once_the_scene_has_motion(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p = Pipeline(connect())
        pid = p.create_project("x")
        sid = p.create_scene(pid, 1, "CẢNH 1")
        it = I.receive(p, d, pid, [("nhay.mp4", b"\x00\x00\x00\x18ftypmp42")], "động tác cảnh 1")[0]
        self.assertEqual(I.retry_waiting(p, d, pid), [])                       # no motion yet → keeps waiting, nothing said
        self.assertEqual(len(I.pending(d, pid)), 1)
        p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?, 'x', 'pending')", (sid,))
        said = I.retry_waiting(p, d, pid)
        self.assertEqual(len(said), 1)
        self.assertIn("cảnh 1", said[0])
        self.assertEqual(I.pending(d, pid), [])
        self.assertTrue(it["sure"])


if __name__ == "__main__":
    unittest.main()


class ScreenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for k, v in (("PIPELINE_DB", os.path.join(self.tmp, "m.sqlite")), ("PIPELINE_DATA", os.path.join(self.tmp, "projects")),
                     ("KNOWLEDGE_USER_DIR", os.path.join(self.tmp, "knowledge_user")), ("FEATURE_CHAT_FIRST", "1")):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        self.p = Pipeline(connect(os.environ["PIPELINE_DB"]))

    def app(self):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"), default_timeout=30)

    def test_the_first_message_starts_a_project_and_lands_in_its_chat(self):
        at = self.app().run()                                                      # no project yet → the start box is there
        self.assertFalse(at.exception)
        at.chat_input(key="home_start").set_value("Khủng Long Đỏ\nCẢNH 1 - NGÀY, SÂN\nKelly chạy ra sân.").run()
        self.assertFalse(at.exception)
        row = Pipeline(connect(os.environ["PIPELINE_DB"])).conn.execute("SELECT id, name FROM projects").fetchone()
        self.assertEqual(row["name"], "Khủng Long Đỏ")
        from core import script_chat
        msgs = script_chat.history(Pipeline(connect(os.environ["PIPELINE_DB"])), row["id"])
        self.assertTrue(any("Kelly chạy ra sân" in m["text"] for m in msgs if m["role"] == "user"))
        self.assertTrue(any(b.key == f"btn_analyse_{row['id']}" and not b.disabled for b in at.button))   # ready for ▶ Phân tích

    def test_the_one_primary_button_is_in_the_chat(self):
        from core.llm_io import store_scene_analysis
        from tests.test_llm_io_preflight import ANALYSIS
        pid = self.p.create_project("Demo")
        self.p.create_scene(pid, 1, "CẢNH 1")
        store_scene_analysis(self.p, pid, ANALYSIS)
        at = self.app().run()
        self.assertFalse(at.exception)
        ctas = [b for b in at.button if b.key.startswith(f"script-cta")]
        self.assertEqual(len(ctas), 1)                                              # drawn once — in the chat, not again in the hero
        self.assertTrue(any("Bước kế" in m.value or "Duyệt & khóa" in m.value or "ảnh mốc" in m.value for m in at.markdown),
                        [m.value for m in at.markdown][-6:])


class SeenOnScreenTests(ScreenTests):
    """Lỗi thấy khi chụp màn thật 07/10 (cờ chat_first): (1) 'ảnh của Kelly' không nhận ra Kelly vì Director chưa chạy (tên chỉ có trong
    cảnh đã tách); (2) sau ▶ Phân tích, lời nhận kịch bản + nút ▶ Phân tích cũ vẫn treo trong chat; (3) ô chọn vai vẽ trắng không chữ."""

    def test_names_of_the_analysed_scenes_are_known_before_the_director(self):
        pid = self.p.create_project("x")
        sid = self.p.create_scene(pid, 1, "CẢNH 1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", ('{"characters": ["KELLY"]}', sid))
        self.p.conn.commit()
        self.assertIn("KELLY", I.known_names(self.p.conn, pid))
        g = I.guess("image", "kelly.png", "ảnh của Kelly", I.known_names(self.p.conn, pid), 1)
        self.assertEqual((g["role"], g["name"], g["sure"]), ("character", "KELLY", True))

    def test_after_the_analysis_the_old_receipt_and_button_are_gone(self):
        at = self.app().run()
        at.chat_input(key="home_start").set_value("Khủng Long Đỏ\nCẢNH 1 - NGÀY, SÂN\nKelly chạy ra sân.\nCẢNH 2 - ĐÊM, PHÒNG\nMaxim ngủ.").run()
        pid = Pipeline(connect(os.environ["PIPELINE_DB"])).conn.execute("SELECT id FROM projects").fetchone()[0]
        next(b for b in at.button if b.key == f"btn_analyse_{pid}").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(any(b.key == f"btn_analyse_{pid}" for b in at.button))
        self.assertFalse(any("Hiểu là" in m.value for m in at.markdown))

    def test_the_role_choice_is_a_plain_radio(self):
        pid = self.p.create_project("x")
        d = os.environ["PIPELINE_DATA"]
        it = I.receive(self.p, d, pid, [("IMG_1.png", b"\x89PNG")], "")[0]
        at = self.app().run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        self.assertTrue(any(r.key == f"ci_{pid}_{it['id']}_role" for r in at.radio))

    def test_the_top_next_step_line_points_into_the_chat(self):
        from dashboard import next_step
        pid = self.p.create_project("x")
        self.assertIn("khung chat", next_step.next_action(self.p, pid, 1)[0])            # was "… ở 1a" (a card that is gone)
        self.p.create_scene(pid, 1, "CẢNH 1")
        text = next_step.next_action(self.p, pid, 1)[0]
        self.assertIn("Lập kế hoạch", text)
        self.assertNotIn("1d", text)
