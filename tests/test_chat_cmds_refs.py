"""Người dùng 09/10 thử thật khung chat Kịch bản, 2 lỗi:
1. Dán kịch bản 1 cảnh → gõ "phân tích kịch bản này" → bot lại hỏi "Bạn muốn làm gì với tin này?" (câu lệnh bị coi là nội dung).
   Câu lệnh ngắn (phân tích / viết kịch bản đi / dùng làm ý tưởng / hủy) phải chạy đúng hành động, không hỏi lại, không thành nội dung.
2. Thả ảnh .jpg vào chat → "image/jpeg files are not allowed". Ảnh / video = (a) ảnh trang kịch bản → đọc chữ (Claude, nút có giá),
   (b) ảnh tham khảo bối cảnh / đồ vật / nhân vật, (c) video tham khảo → hỏi vai trò bằng nút (0 USD), ghi thành tư liệu của dự án,
   tư liệu vào prompt Biên kịch / Đạo diễn dạng chữ."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import chat_intake as Intake, chat_refs, llm_runner, script_chat as C
from core.db import connect
from core.pipeline import Pipeline

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc"
       b"\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82")
SCRIPT = "CẢNH 1 - ĐÊM, QUẢNG TRƯỜNG\nKelly đứng dưới tháp đồng hồ, gió rít.\nKELLY: Có ai không?"
IDEA = "Kelly và Maxim tranh một thùng thính ở Đảo Quân Sự, mở ra thì trống trơn."


class CommandRuleTests(unittest.TestCase):
    def test_short_commands_are_commands(self):
        for text, cmd in [("phân tích kịch bản này", "analyse"), ("phân tích", "analyse"), ("Phân tích!", "analyse"),
                          ("tách cảnh đi", "analyse"), ("chạy phân tích", "analyse"), ("▶ Phân tích", "analyse"),
                          ("phân tích kịch bản trên giúp mình", "analyse"),
                          ("viết kịch bản đi", "write"), ("viết kịch bản từ ý tưởng này", "write"),
                          ("dùng làm ý tưởng", "idea"), ("đây là ý tưởng", "idea"), ("đây là kịch bản", "script"),
                          ("hủy", "cancel"), ("huỷ", "cancel"), ("Hủy.", "cancel"), ("bỏ qua", "cancel")]:
            with self.subTest(text=text):
                self.assertEqual(C.command(text), cmd)
                self.assertEqual(C.intent(text), "command")

    def test_content_that_merely_contains_the_words_is_not_a_command(self):
        for text in ["phân tích tâm lý Kelly khi mất thính", "Huy", "huy chương vàng", "viết kịch bản về Kelly đi chợ",
                     "hủy diệt cả map rồi chạy bo", "CẢNH 1 - NHÀ\nphân tích", "phan tich", "Kelly phân tích kịch bản này"]:
            with self.subTest(text=text):
                self.assertIsNone(C.command(text))
                self.assertNotEqual(C.intent(text), "command")


class BoxCommandTests(unittest.TestCase):
    """step1_box._command (gọi ngay lúc đọc ô chat) — st giả, không model."""
    def setUp(self):
        from dashboard.steps import step1_box
        self.box = step1_box
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("cmd")
        self.st = mock.MagicMock()
        self.st.session_state = {}
        self.k = step1_box._keys(self.pid)
        patcher = mock.patch.object(step1_box, "st", self.st)
        patcher.start()
        self.addCleanup(patcher.stop)

    def last(self):
        return C.history(self.p, self.pid)[-1]["text"]

    def test_analyse_with_a_waiting_script_splits_it(self):
        self.st.session_state[self.k["text"]] = SCRIPT
        self.box._command(self.p, self.pid, "analyse")
        n = self.p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (self.pid,)).fetchone()[0]
        self.assertEqual(n, 1)
        self.assertNotIn(self.k["text"], self.st.session_state)
        self.assertNotIn(self.k["chatask"], self.st.session_state)
        self.assertIn("tách", self.last())

    def test_analyse_without_a_script_says_so(self):
        self.box._command(self.p, self.pid, "analyse")
        self.assertIn("Chưa có kịch bản", self.last())
        self.assertNotIn(self.k["chatask"], self.st.session_state)

    def test_analyse_on_an_idea_says_it_is_not_a_script(self):
        self.st.session_state[self.k["text"]] = IDEA
        self.box._command(self.p, self.pid, "analyse")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0], 0)
        self.assertIn("ý tưởng", self.last())
        self.assertEqual(self.st.session_state[self.k["text"]], IDEA)              # chữ cũ giữ nguyên

    def test_write_keeps_the_idea_and_does_not_become_the_idea(self):
        self.st.session_state[self.k["text"]] = IDEA
        self.box._command(self.p, self.pid, "write")
        self.assertEqual(self.st.session_state[self.k["text"]], IDEA)
        self.assertEqual(self.st.session_state[self.k["mode"]], "idea")

    def test_write_without_anything_says_so(self):
        self.box._command(self.p, self.pid, "write")
        self.assertNotIn(self.k["text"], self.st.session_state)
        self.assertIn("Chưa có ý tưởng", self.last())

    def test_idea_answers_the_waiting_question(self):
        self.st.session_state[self.k["chatask"]] = IDEA
        self.box._command(self.p, self.pid, "idea")
        self.assertNotIn(self.k["chatask"], self.st.session_state)
        self.assertEqual(self.st.session_state[self.k["text"]], IDEA)
        self.assertEqual(self.st.session_state[self.k["mode"]], "idea")

    def test_cancel_clears_the_question_or_the_waiting_text(self):
        self.st.session_state[self.k["chatask"]] = IDEA
        self.box._command(self.p, self.pid, "cancel")
        self.assertNotIn(self.k["chatask"], self.st.session_state)
        self.st.session_state[self.k["text"]] = SCRIPT
        self.box._command(self.p, self.pid, "cancel")
        self.assertNotIn(self.k["text"], self.st.session_state)
        self.box._command(self.p, self.pid, "cancel")
        self.assertIn("Không có gì", self.last())


class RefsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"ASSET_DIR": os.path.join(self.tmp, "assets")})
        env.start()
        self.addCleanup(env.stop)
        self.data = os.path.join(self.tmp, "projects")
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("refs")

    def test_new_roles_exist_for_pictures_and_videos(self):
        self.assertIn("script_page", Intake.ROLES_BY_TYPE["image"])
        self.assertIn("video_ref", Intake.ROLES_BY_TYPE["video"])

    def test_a_location_picture_becomes_a_reference_in_the_prompt(self):
        it = Intake.receive(self.p, self.data, self.pid, [("IMG_1.jpg", PNG)], "nhà Kelly ban đêm")[0]
        Intake.apply(self.p, self.data, self.pid, it["id"], "location", name="Nhà Kelly")
        refs = chat_refs.items(self.p.conn, self.pid)
        self.assertEqual([(r["role"], r["label"], r["note"]) for r in refs], [("location", "Nhà Kelly", "nhà Kelly ban đêm")])
        block = chat_refs.block(self.p.conn, self.pid)
        self.assertIn("Bối cảnh: Nhà Kelly", block)
        self.assertIn("nhà Kelly ban đêm", block)

    def test_a_reference_video_is_kept_under_the_project_data_dir(self):
        it = Intake.receive(self.p, self.data, self.pid, [("nhip.mp4", b"\x00\x00\x00 ftypmp42")], "")[0]
        Intake.apply(self.p, self.data, self.pid, it["id"], "video_ref", name="Nhịp chạy bo")
        r = chat_refs.items(self.p.conn, self.pid)[0]
        self.assertEqual((r["role"], r["label"]), ("video_ref", "Nhịp chạy bo"))
        self.assertTrue(os.path.isabs(r["path"]) or r["path"].startswith(self.data))
        self.assertTrue(os.path.commonpath([os.path.abspath(r["path"]), os.path.abspath(self.data)]) == os.path.abspath(self.data))
        self.assertTrue(os.path.exists(r["path"]))
        self.assertEqual(Intake.pending(self.data, self.pid), [])

    def test_script_page_is_not_a_free_attach(self):
        it = Intake.receive(self.p, self.data, self.pid, [("trang1.jpg", PNG)], "")[0]
        with self.assertRaises(ValueError):
            Intake.apply(self.p, self.data, self.pid, it["id"], "script_page")

    def test_no_refs_no_block_and_prompts_unchanged(self):
        self.assertEqual(chat_refs.block(self.p.conn, self.pid), "")

    def test_screenwriter_and_director_prompts_carry_the_list(self):
        from core import idea_to_script as I, prompts
        chat_refs.add(self.p.conn, self.pid, "prop", "Thùng thính", "thùng gỗ sơn đỏ", "box.jpg", None)
        state = {"inputs": {"idea": IDEA, "duration_s": 30, "aspect": "9:16", "platform": "TikTok"}}
        with mock.patch.object(I, "buildable_blocks", return_value=""):
            self.assertIn("Đồ vật: Thùng thính", I.build_prompt(self.p.conn, self.pid, state, 1))
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        self.assertIn("Đồ vật: Thùng thính", prompts.build_director_bundle(self.p, self.pid))

    def test_reading_a_script_page_calls_claude_once_tagged_with_the_picture(self):
        it = Intake.receive(self.p, self.data, self.pid, [("trang1.jpg", PNG)], "")[0]
        seen = {}

        class Client:
            def complete(inner, prompt, images=()):
                seen["tag"], seen["images"] = llm_runner.current_tag(), list(images)
                return llm_runner.LlmReply("CẢNH 1 - NGÀY, SÂN\nKelly chạy.", 10, 5)
        text = chat_refs.read_page(self.p, self.data, self.pid, it["id"], Client())
        self.assertTrue(text.startswith("CẢNH 1"))
        self.assertEqual(seen["tag"], (chat_refs.STAGE, self.pid))
        self.assertEqual(len(seen["images"]), 1)
        self.assertEqual(Intake.pending(self.data, self.pid), [])

    def test_unreadable_page_or_no_client_is_said_and_the_file_waits(self):
        it = Intake.receive(self.p, self.data, self.pid, [("mo.jpg", PNG)], "")[0]
        with self.assertRaises(ValueError):
            chat_refs.read_page(self.p, self.data, self.pid, it["id"], None)

        class Client:
            def complete(inner, prompt, images=()):
                return llm_runner.LlmReply(chat_refs.UNREADABLE, 10, 5)
        with self.assertRaises(ValueError):
            chat_refs.read_page(self.p, self.data, self.pid, it["id"], Client())
        self.assertEqual(len(Intake.pending(self.data, self.pid)), 1)

    def test_price_is_estimated_before_the_click(self):
        self.assertIsNotNone(chat_refs.estimate(self.p.conn))


class MediaRoutingTests(unittest.TestCase):
    """Cờ chat_first TẮT: ảnh thả vào chat vào hộp chờ (không bị đọc như file kịch bản, không tự gắn)."""
    def setUp(self):
        from dashboard.steps import step1_box
        from dashboard import common
        self.box = step1_box
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.data = os.path.join(self.tmp, "projects")
        old, common.DATA = common.DATA, self.data
        self.addCleanup(setattr, common, "DATA", old)
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("media")
        self.st = mock.MagicMock()
        self.st.session_state = {}
        patcher = mock.patch.object(step1_box, "st", self.st)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_accepted_types_include_pictures_and_videos_without_the_flag(self):
        types = self.box.accepted_types(False)
        for ext in ("png", "jpg", "jpeg", "webp", "mp4", "mov", "webm", "docx", "txt"):
            self.assertIn(ext, types)
        self.assertNotIn("mp3", types)

    def test_an_unknown_file_is_refused_in_vietnamese_and_not_kept(self):
        class F:
            name, getvalue = "virus.exe", staticmethod(lambda: b"MZ")
        self.box.media_in(self.p, self.pid, [F()], "", wide=False)
        self.assertEqual(Intake.pending(self.data, self.pid), [])
        msg = C.history(self.p, self.pid)[-1]["text"]
        self.assertIn("Chưa nhận loại tệp này", msg)
        self.assertIn("jpg", msg)

    def test_a_picture_waits_for_its_role(self):
        class F:
            name, getvalue = "trang1.jpg", staticmethod(lambda: PNG)
        self.box.media_in(self.p, self.pid, [F()], "ảnh kịch bản", wide=False)
        items = Intake.pending(self.data, self.pid)
        self.assertEqual([i["file"] for i in items], ["trang1.jpg"])
        self.assertNotIn(self.box._keys(self.pid)["file"], self.st.session_state)
        self.assertIn("trang1.jpg", C.history(self.p, self.pid)[-1]["text"])


class ChatAppTests(unittest.TestCase):
    """AppTest: màn Kịch bản thật (cờ idea_to_script bật, chat_first tắt), không model khi chỉ hiện."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.data = os.path.join(self.tmp, "projects")
        env = {"PIPELINE_DB": os.path.join(self.tmp, "m.sqlite"), "PIPELINE_DATA": self.data, "ASSET_DIR": os.path.join(self.tmp, "assets"),
               "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "knowledge_user"), "FEATURE_CHAT_FIRST": "0", "FEATURE_IDEA_TO_SCRIPT": "1"}
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)
        calls = mock.patch.object(llm_runner.MockLlm, "complete", side_effect=AssertionError("không được gọi model"))
        calls.start()
        self.addCleanup(calls.stop)
        self.p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        self.pid = self.p.create_project("Demo")

    def open(self):
        from streamlit.testing.v1 import AppTest
        app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
        at = AppTest.from_file(app, default_timeout=60)
        at.session_state["global_pid"] = self.pid
        at.run()
        self.assertFalse(at.exception, at.exception)
        return at

    def say(self, at, text):
        at.chat_input(key=f"box_in_{self.pid}").set_value(text).run()
        self.assertFalse(at.exception, at.exception)
        return at

    def keys(self, at):
        return {getattr(b, "key", None) for b in at.button}

    def test_analyse_command_after_a_pasted_script_splits_without_asking(self):
        at = self.say(self.open(), SCRIPT)
        self.say(at, "phân tích kịch bản này")
        self.assertNotIn(f"box_chatask_idea_{self.pid}", self.keys(at))
        n = self.p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (self.pid,)).fetchone()[0]
        self.assertEqual(n, 1)
        texts = [m["text"] for m in C.history(self.p, self.pid)]
        self.assertNotIn("Bạn muốn làm gì", " ".join(texts))

    def test_chat_input_takes_files_and_filters_them_itself(self):
        at = self.open()
        ci = at.chat_input(key=f"box_in_{self.pid}")
        self.assertEqual(list(ci.proto.file_type), [])        # không lọc ở trình duyệt (câu tiếng Anh) — media_in báo bằng tiếng Việt

    def test_a_waiting_picture_shows_role_buttons_and_a_place_is_recorded(self):
        it = Intake.receive(self.p, self.data, self.pid, [("IMG_7.jpg", PNG)], "")[0]
        at = self.open()
        k = f"cr_{self.pid}_{it['id']}"
        labels = {b.key: b.label for b in at.button if (b.key or "").startswith(k)}
        self.assertTrue(labels[f"{k}_page"].startswith("📄 Ảnh trang kịch bản"), labels)
        self.assertIn("USD", labels[f"{k}_page"])
        for suffix in ("location", "prop", "character", "drop"):
            self.assertIn(f"{k}_{suffix}", labels)
        self.assertNotIn(f"{k}_video_ref", labels)
        at.text_input(key=f"{k}_label").set_value("Sân trường").run()
        next(b for b in at.button if b.key == f"{k}_location").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual([r["label"] for r in chat_refs.items(self.p.conn, self.pid)], ["Sân trường"])
        self.assertEqual(Intake.pending(self.data, self.pid), [])

    def test_a_waiting_video_has_only_valid_buttons(self):
        it = Intake.receive(self.p, self.data, self.pid, [("ref.mp4", b"\x00\x00\x00 ftypmp42")], "")[0]
        at = self.open()
        k = f"cr_{self.pid}_{it['id']}"
        keys = {b.key for b in at.button if (b.key or "").startswith(k)}
        self.assertEqual(keys, {f"{k}_video_ref", f"{k}_drop"})

    def test_reading_a_page_only_on_click_then_it_is_the_script(self):
        it = Intake.receive(self.p, self.data, self.pid, [("trang1.jpg", PNG)], "")[0]

        class Client:
            calls = 0

            def complete(inner, prompt, images=()):
                Client.calls += 1
                return llm_runner.LlmReply(SCRIPT, 10, 5)
        with mock.patch("dashboard.common.llm_client", return_value=Client()):
            at = self.open()
            self.assertEqual(Client.calls, 0)                                  # chỉ hiện thẻ: chưa gọi
            next(b for b in at.button if b.key == f"cr_{self.pid}_{it['id']}_page").click().run()
            self.assertFalse(at.exception, at.exception)
        self.assertEqual(Client.calls, 1)
        self.assertIn("CẢNH 1", at.session_state[f"box_text_{self.pid}"])
        self.assertIn("Đã đọc chữ", " ".join(m["text"] for m in C.history(self.p, self.pid)))


if __name__ == "__main__":
    unittest.main()
