"""08/10 dự án #24 (kịch bản thật ở tests/fixtures/p24_script.txt): khung chat 'Nhập / thay kịch bản'
- lỗi 3: lời "Đã nhận kịch bản 1 cảnh (… 1.565 ký tự)" hiện 2 lần (đã lưu thành tin chat + vẽ lại từ chữ còn trong khung); dán bản mới
  (1.610 ký tự) thì tin số cũ vẫn nằm sau tin mới;
- lỗi 4: lúc thẻ "Thêm vào / Thay thế" (hay "Thay / Hủy") đang chờ, ▶ Phân tích vẫn bấm được → tách chữ CŨ → ValueError 'Dự án đã có cảnh'."""
import os
import unittest
from unittest import mock

from core.db import connect
from core.pipeline import Pipeline
from dashboard.steps import step1_box

HERE = os.path.dirname(__file__)
SCRIPT = open(os.path.join(HERE, "fixtures", "p24_script.txt"), encoding="utf-8").read()
NEW = SCRIPT.replace("không lời thoại.", "không lời thoại, nhạc ma mị, có tiếng gió rít và tiếng khóc xa.")


class ScriptBoxP24Tests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("p24", operating_mode="human_qc")
        self.fake = mock.MagicMock()
        self.fake.session_state = {}
        self.k = step1_box._keys(self.pid)

    def test_receipt_already_in_the_chat_is_not_drawn_again(self):
        line = step1_box.receipt(SCRIPT)
        self.assertIn("Đã nhận kịch bản 1 cảnh", line)
        recent = [{"role": "user", "text": SCRIPT}, {"role": "assistant", "text": line}]
        self.assertEqual(step1_box.live_receipt(SCRIPT, None, recent), "")
        self.assertEqual(step1_box.live_receipt(SCRIPT, None, []), line)          # not in the chat yet → shown once

    def test_new_paste_over_a_split_script_drops_the_old_text_and_waits(self):
        self.p.create_scene(self.pid, 1, "S01")                                    # the first version was split already
        self.fake.session_state[self.k["text"]] = SCRIPT                            # the old text still in the box (flag chat_first off)
        with mock.patch.object(step1_box, "st", self.fake):
            step1_box._take(self.p, self.pid, NEW)
            self.assertTrue(step1_box.waiting_choice(self.pid))                     # ▶ Phân tích waits for the card
        ss = self.fake.session_state
        self.assertNotIn(self.k["text"], ss)                                        # no old "1.565 ký tự" receipt under the new one
        self.assertEqual(ss.get(self.k["ask"]) or ss.get(self.k["pending"]), NEW)

    def test_resolving_the_card_puts_the_new_text_up_for_analysis(self):
        self.p.create_scene(self.pid, 1, "S01")
        with mock.patch.object(step1_box, "st", self.fake):
            step1_box._take(self.p, self.pid, NEW)
            if self.fake.session_state.get(self.k["ask"]):
                step1_box.resolve(self.p, self.pid, "swap")
            with mock.patch("dashboard.steps.step1.reset_unworked_scenes"):
                step1_box.resolve(self.p, self.pid, "replace")
            self.assertFalse(step1_box.waiting_choice(self.pid))
        self.assertEqual(self.fake.session_state[self.k["text"]], NEW)


class ScriptViewP24Tests(unittest.TestCase):
    def test_full_script_html_has_no_raw_newline(self):
        """Lỗi 8 (08/10): ô 'Kịch bản đầy đủ' — mỗi xuống dòng thành 4–8 dòng trống (st.markdown cắt khối HTML ở dòng trống)."""
        from dashboard.steps.step1 import script_html
        html = script_html(SCRIPT)
        self.assertNotIn("\n", html)
        self.assertNotIn("<br><br><br>", html)                      # a blank line between paragraphs stays ONE empty line
        self.assertIn("<b>CẢNH 1 - ĐÊM, QUẢNG TRƯỜNG THÁP ĐỒNG HỒ</b>", html)


if __name__ == "__main__":
    unittest.main()
