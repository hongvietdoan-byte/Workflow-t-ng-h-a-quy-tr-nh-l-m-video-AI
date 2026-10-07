"""Khung chat Kịch bản nhận mọi tệp (người dùng 07/10, Khủng Long Đỏ mục 10 — Đợt 1; cờ `chat_first`):
ảnh / video / nhạc thả vào chat → code xếp loại 0 USD; chắc thì gắn ngay vào đúng chỗ cũ (Kho, video ref cảnh, thư mục nhạc),
không chắc thì HỎI LẠI (luật 3: không đoán) — tệp nằm chờ trong hộp chờ của dự án tới khi người chọn."""
import os
import shutil
import tempfile
import unittest

from core import chat_intake as I
from core.db import connect
from core.pipeline import Pipeline

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc"
       b"\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82")


class GuessTests(unittest.TestCase):
    def test_file_types_by_extension(self):
        self.assertEqual(I.file_type("a.PNG"), "image")
        self.assertEqual(I.file_type("nhay.mp4"), "video")
        self.assertEqual(I.file_type("nhac.m4a"), "audio")
        self.assertEqual(I.file_type("kich_ban.docx"), "script")
        self.assertIsNone(I.file_type("virus.exe"))

    def test_a_character_name_in_the_words_makes_a_sure_character_picture(self):
        g = I.guess("image", "IMG_001.png", "ảnh của Kelly", ["Kelly", "Maxim"], 3)
        self.assertEqual((g["role"], g["name"], g["sure"]), ("character", "Kelly", True))

    def test_outfit_words_with_a_character_go_to_that_character(self):
        g = I.guess("image", "bo_do.png", "đây là bộ đồ Khủng Long của Kelly", ["Kelly"], 3)
        self.assertEqual((g["role"], g["who"], g["sure"]), ("outfit", "Kelly", True))

    def test_the_clock_tower_is_not_an_outfit(self):
        g = I.guess("image", "thap.png", "Tháp Đồng Hồ", ["Kelly"], 3)              # "đồ" trong "Đồng Hồ" không phải bộ đồ
        self.assertNotEqual(g["role"], "outfit")

    def test_a_picture_with_no_hint_is_asked_never_guessed(self):
        g = I.guess("image", "IMG_002.jpg", "", ["Kelly"], 3)
        self.assertFalse(g["sure"])
        self.assertIsNone(g["role"])

    def test_a_dance_video_for_a_named_scene_is_a_sure_motion_reference(self):
        g = I.guess("video", "dance.mp4", "video động tác nhảy cho cảnh 3", [], 5)
        self.assertEqual((g["role"], g["scene"], g["sure"]), ("motion_ref", 3, True))

    def test_a_scene_number_out_of_range_is_asked(self):
        g = I.guess("video", "dance.mp4", "động tác cảnh 9", [], 5)
        self.assertFalse(g["sure"])
        self.assertIsNone(g["scene"])

    def test_audio_needs_the_word_music_to_be_sure(self):
        self.assertEqual(I.guess("audio", "x.mp3", "nhạc nền", [], 1)["role"], "music")
        self.assertTrue(I.guess("audio", "x.mp3", "nhạc đoạn 2", [], 1)["sure"])
        self.assertEqual(I.guess("audio", "x.mp3", "nhạc đoạn 2", [], 1)["role"], "music2")
        self.assertFalse(I.guess("audio", "x.mp3", "", [], 1)["sure"])

    def test_each_role_belongs_to_its_file_type(self):
        for ftype, roles in I.ROLES_BY_TYPE.items():
            for role in roles:
                self.assertIn(role, I.ROLES, f"{ftype}:{role}")


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("chat")
        for i in (1, 2):
            self.p.create_scene(self.pid, i, f"CẢNH {i}")
        self.p.conn.execute("INSERT INTO characters(project_id, name, description) VALUES (?, 'Kelly', 'cô gái')", (self.pid,))
        self.p.conn.commit()

    def test_files_wait_in_the_inbox_until_someone_decides(self):
        items = I.receive(self.p, self.dir, self.pid, [("IMG_1.png", PNG), ("song.mp3", b"ID3")], "")
        self.assertEqual(len(items), 2)
        self.assertEqual(len(I.pending(self.dir, self.pid)), 2)                 # survives a reload: kept on disk, not in the session
        for it in items:
            self.assertTrue(os.path.exists(it["path"]))
        I.drop(self.dir, self.pid, items[1]["id"])
        self.assertEqual([x["id"] for x in I.pending(self.dir, self.pid)], [items[0]["id"]])

    def test_one_caption_for_several_files_is_not_applied_to_all_of_them(self):
        """Chụp màn 07/10: 'ảnh kelly là ảnh của Kelly, ảnh còn lại để tham khảo' + 2 ảnh → cả 2 bị gắn KELLY. Nhiều tệp một câu: chỉ
        tệp mà TÊN TỆP cũng khớp mới chắc; tệp kia hỏi lại."""
        a, b = I.receive(self.p, self.dir, self.pid, [("kelly.png", PNG), ("IMG_2041.png", PNG)],
                         "ảnh kelly là ảnh của Kelly, ảnh còn lại để tham khảo")
        self.assertEqual((a["role"], a["name"], a["sure"]), ("character", "Kelly", True))
        self.assertFalse(b["sure"])

    def test_unknown_file_types_are_refused_and_said(self):
        with self.assertRaises(ValueError):
            I.receive(self.p, self.dir, self.pid, [("a.exe", b"MZ")], "")

    def test_a_character_picture_goes_to_the_project_kho(self):
        it = I.receive(self.p, self.dir, self.pid, [("k.png", PNG)], "Kelly")[0]
        msg = I.apply(self.p, self.dir, self.pid, it["id"], "character", name="Kelly")
        row = self.p.conn.execute("SELECT a.kind, a.name FROM assets a JOIN project_assets pa ON pa.asset_id=a.id WHERE pa.project_id=?",
                                  (self.pid,)).fetchone()
        self.assertEqual((row["kind"], row["name"]), ("character", "Kelly"))
        self.assertIn("Kelly", msg)
        self.assertEqual(I.pending(self.dir, self.pid), [])                      # decided → leaves the inbox

    def test_a_motion_reference_is_attached_to_the_scene(self):
        it = I.receive(self.p, self.dir, self.pid, [("nhay.mp4", b"\x00\x00\x00\x18ftypmp42")], "")[0]
        with self.assertRaises(ValueError):                                     # no motion prompt yet → said, the video keeps waiting
            I.apply(self.p, self.dir, self.pid, it["id"], "motion_ref", scene=2)
        self.assertEqual(len(I.pending(self.dir, self.pid)), 1)
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=2", (self.pid,)).fetchone()[0]
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?, 'x', 'pending')", (sid,))
        I.apply(self.p, self.dir, self.pid, it["id"], "motion_ref", scene=2)
        path = self.p.conn.execute("SELECT ref_video_path FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()[0]
        self.assertTrue(path and os.path.exists(path))

    def test_music_replaces_the_chosen_track(self):
        it = I.receive(self.p, self.dir, self.pid, [("song.mp3", b"ID3")], "nhạc nền")[0]
        I.apply(self.p, self.dir, self.pid, it["id"], "music")
        self.assertEqual(os.listdir(os.path.join(self.dir, str(self.pid), "music")), ["selected.mp3"])

    def test_missing_answers_are_refused_not_guessed(self):
        it = I.receive(self.p, self.dir, self.pid, [("k.png", PNG)], "")[0]
        with self.assertRaises(ValueError):
            I.apply(self.p, self.dir, self.pid, it["id"], "character")            # no name
        with self.assertRaises(ValueError):
            I.apply(self.p, self.dir, self.pid, it["id"], "music")                # a picture cannot be music
        self.assertEqual(len(I.pending(self.dir, self.pid)), 1)                  # still waiting

    @unittest.skipUnless(shutil.which("ffmpeg"), "cần ffmpeg")
    def test_the_sound_of_a_dance_video_becomes_the_second_music(self):
        import subprocess
        src = os.path.join(self.dir, "src.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=1", "-shortest", "-c:v", "libx264", "-c:a", "aac", src], check=True)
        with open(src, "rb") as f:
            it = I.receive(self.p, self.dir, self.pid, [("nhay.mp4", f.read())], "lấy nhạc đoạn 2 từ video này")[0]
        self.assertEqual((it["role"], it["sure"]), ("video_music2", True))
        I.apply(self.p, self.dir, self.pid, it["id"], it["role"])
        self.assertEqual(os.listdir(os.path.join(self.dir, str(self.pid), "music2")), ["second.m4a"])


if __name__ == "__main__":
    unittest.main()


class ChatFirstScreenTests(unittest.TestCase):
    """Cờ chat_first BẬT: khung chat lớn ở đầu tab, các thẻ cũ gấp vào ⚙ Chi tiết, tệp chờ hiện thành thẻ hỏi lại trong chat."""
    def setUp(self):
        from core.llm_io import store_scene_analysis
        from tests.test_llm_io_preflight import ANALYSIS
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.data = os.path.join(self.tmp, "projects")
        for k, v in (("PIPELINE_DB", os.path.join(self.tmp, "m.sqlite")), ("PIPELINE_DATA", self.data),
                     ("KNOWLEDGE_USER_DIR", os.path.join(self.tmp, "knowledge_user")), ("FEATURE_CHAT_FIRST", "1")):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        self.p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        self.pid = self.p.create_project("Demo")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        self.p.conn.execute("INSERT INTO characters(project_id, name, description) VALUES (?, 'Kelly', 'cô gái')", (self.pid,))
        self.p.conn.commit()

    def open(self):
        from streamlit.testing.v1 import AppTest
        app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
        return AppTest.from_file(app, default_timeout=30).run()

    def test_the_chat_is_the_first_card_and_the_rest_is_folded(self):
        at = self.open()
        self.assertFalse(at.exception)
        self.assertTrue(any(c.key == f"box_in_{self.pid}" for c in at.get("chat_input")))
        self.assertFalse(any(e.label.startswith("📥 Nhập / thay kịch bản") for e in at.expander))  # chat luôn mở, không gấp

    def test_a_waiting_picture_is_asked_in_the_chat_and_attached_by_one_click(self):
        it = I.receive(self.p, self.data, self.pid, [("IMG_9.png", PNG)], "")[0]
        at = self.open()
        self.assertTrue(any(r.key == f"ci_{self.pid}_{it['id']}_role" for r in at.radio))
        at.radio(key=f"ci_{self.pid}_{it['id']}_role").set_value("location").run()
        at.selectbox(key=f"ci_{self.pid}_{it['id']}_name").set_value("Kelly").run()
        next(b for b in at.button if b.key == f"ci_{self.pid}_{it['id']}_go").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([e.value for e in at.error], [])
        self.assertEqual(I.pending(self.data, self.pid), [])
        row = self.p.conn.execute("SELECT a.kind, a.name FROM assets a JOIN project_assets pa ON pa.asset_id=a.id WHERE pa.project_id=? "
                                  "AND a.kind='location'", (self.pid,)).fetchone()
        self.assertEqual(row["name"], "Kelly")

    def test_a_sure_file_is_attached_at_once_and_said_in_the_chat(self):
        from core import script_chat
        from dashboard.steps.step1_intake import handle_files

        class F:
            name, getvalue = "k.png", staticmethod(lambda: PNG)
        from dashboard import common
        old, common.DATA = common.DATA, self.data
        self.addCleanup(setattr, common, "DATA", old)
        handle_files(self.p, self.pid, [F()], "ảnh của Kelly")
        self.assertEqual(I.pending(self.data, self.pid), [])
        self.assertTrue(script_chat.history(self.p, self.pid)[-1]["text"].startswith("✅"))
