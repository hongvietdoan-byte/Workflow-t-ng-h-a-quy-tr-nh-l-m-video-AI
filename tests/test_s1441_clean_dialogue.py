"""S14.41 (chấm phiếu 05c, 05/10): lời thoại sạch (không mày/tao, không nói tục) — kiểm bằng code sau lượt viết; luật Biên kịch mới
(lời thoại sạch + logic vật thể); ý tưởng mẫu 1 đổi (Kelly đoán rank của chính Kelly — người dùng chốt 05/10). 0 USD (MockLlm, không gọi API thật)."""
import json
import os
import unittest

from core import clean_dialogue as C, idea_to_script as I
from core.db import connect
from core.pipeline import Pipeline
from tests.test_idea_to_script import ANCHORS, IDEA, Recorder, make_kit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def words(text):
    return [h["word"] for h in C.find(text)]


class CleanWordsS1441(unittest.TestCase):
    def test_catches_pronouns_with_accents(self):
        self.assertEqual(words("KELLY: Của tao!"), ["tao"])
        self.assertEqual(words("MAXIM: Mày đứng lại!"), ["mày"])
        self.assertEqual(words("ALVARO: Chúng mày đâu hết rồi?"), ["chúng mày"])

    def test_catches_swears_accented_unaccented_and_short_forms(self):
        for line, want in (("KELLY: Địt mẹ, mất gà rồi!", "địt mẹ"), ("KELLY: dit me mat ga roi", "dit me"),
                           ("MAXIM: Đm, ai ăn rồi?", "đm"), ("MAXIM: dm ai an roi", "dm"), ("ALVARO: Vl thật!", "vl"),
                           ("ALVARO: vcl luôn", "vcl"), ("KELLY: dcm!", "dcm"), ("KELLY: Đéo ai nhường!", "đéo"),
                           ("KELLY: Mẹ kiếp!", "mẹ kiếp"), ("KELLY: VKL", "vkl")):
            with self.subTest(line=line):
                self.assertIn(want, words(line))

    def test_does_not_catch_clean_words_that_share_letters(self):
        clean = ("Máy hất lên quạt trần. Kelly tạo dáng, cầm quả táo. Maxim mày mò cái hộp, nhíu lông mày. Maxim cau mày, Kelly chau mày rồi nhíu mày, mặt mày hớn hở. "
                 "Chúc may mắn! Tảo biển. Đeo kính vào. Lớn quá. Model DM-2. Vlog của Kelly. Đầm xanh.")
        self.assertEqual(C.find(clean), [])

    def test_word_list_lives_in_an_editable_data_file(self):
        path = os.path.join(ROOT, "data", "clean_dialogue_words.json")
        data = json.load(open(path, encoding="utf-8"))
        self.assertIn("tao", data["pronouns"])
        self.assertIn("vcl", data["short_forms"])

    def test_missing_word_list_is_said_not_a_silent_pass(self):
        with self.assertRaises(C.WordListError):
            C.load(os.path.join(ROOT, "data", "khong_co_file_nay.json"))


class ScriptCheckS1441(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ý tưởng", operating_mode="human_qc")
        make_kit(self.p.conn)
        self.inputs = {"duration_s": 15, "anchors": dict(ANCHORS, characters=["KELLY", "MAXIM"], plot="", ending="")}

    def test_a_scene_with_dirty_dialogue_is_blocked_with_scene_and_word(self):
        bad = ("CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKelly và Maxim giằng thùng thính ở bãi cỏ.\nKELLY: Của tao!\n\n"
               "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nMaxim giật lại.\nMAXIM: Vcl, buông ra!")
        c = I.check_script(self.p.conn, self.pid, bad, self.inputs)
        self.assertFalse(c["ok"])
        self.assertEqual([b["scene"] for b in c["blocked_scenes"]], [1, 2])
        self.assertTrue(any("cảnh 1" in t and "tao" in t for t in c["problems"]))
        self.assertTrue(any("cảnh 2" in t and "vcl" in t for t in c["problems"]))

    def test_clean_rivalry_passes(self):
        ok = ("CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nKelly và Maxim giằng thùng thính ở bãi cỏ, máy lia theo.\n"
              "KELLY: Của tớ!\nMAXIM: Đừng hòng, cậu ơi!")
        c = I.check_script(self.p.conn, self.pid, ok, self.inputs)
        self.assertTrue(c["ok"], c["problems"])

    def test_outline_dialogue_is_checked_too(self):
        beats = [{"name": "hook", "start": 0, "end": 3, "dialogue": [{"speaker": "KELLY", "line": "Của tao!"}]},
                 {"name": "ending", "start": 3, "end": 15, "dialogue": []}]
        out = I.check_outline(beats, 15)
        self.assertTrue(any(o["level"] == "block" and "tao" in o["text"] for o in out))


class ScreenwriterRulesS1441(unittest.TestCase):
    def test_the_screenwriter_prompt_carries_the_new_rules(self):
        p = Pipeline(connect())
        pid = p.create_project("ý tưởng", operating_mode="human_qc")
        make_kit(p.conn)
        m = Recorder()
        I.start(p.conn, pid, IDEA, anchors=ANCHORS)
        I.questions(p.conn, pid, m)
        pr = m.prompts[0]
        self.assertIn("Lời thoại sạch", pr)
        self.assertIn("mày/tao", pr)
        self.assertIn("cộng đồng Free Fire", pr)
        self.assertIn("Logic vật thể", pr)
        self.assertIn("vụn gà", pr)
        self.assertIn("nhấc cao", pr)
        self.assertIn("không phải công thức", pr)

    def test_golden_idea_1_is_kelly_guessing_her_own_rank(self):
        ideas = json.load(open(os.path.join(ROOT, "data", "idea_golden", "ideas.json"), encoding="utf-8"))
        one = next(i for i in ideas if i["id"] == 1)
        self.assertIn("rank của chính Kelly", one["idea"])
        self.assertIn("rank của chính Kelly", one["anchors"]["plot"])
        self.assertNotIn("hạng của mình", one["idea"])


if __name__ == "__main__":
    unittest.main()
