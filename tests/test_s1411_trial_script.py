"""S14.11: kịch bản dự án thử 30 s (samples/du_an_thu_30s.txt) + bảng cờ/trần (docs/DU_AN_THU_30S_2026-10-06.md), 0 USD.
Kịch bản phải tách đúng như Dashboard tách (mở cảnh, thoại 2 người, kỹ năng ⭐, chuyển cảnh, CTA); tài liệu phải nêu MỌI cờ chưa
verified (dùng trong dự án thử hay không đo + lý do) — thêm cờ mới mà quên tài liệu thì test đỏ."""
import os
import re
import unittest

from core import dialogue, features, script_parser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "samples", "du_an_thu_30s.txt")
DOC = os.path.join(ROOT, "docs", "DU_AN_THU_30S_2026-10-06.md")


class TrialScriptTests(unittest.TestCase):
    def setUp(self):
        with open(SCRIPT, encoding="utf-8") as f:
            self.text = f.read()
        self.scenes = script_parser.split_scenes(self.text.splitlines())

    def test_four_scenes_three_speakers_and_an_end_card(self):
        card, scenes = script_parser.split_end_card(self.scenes)
        self.assertEqual(len(scenes), 4)
        self.assertTrue(card and "Kenta" in card)
        speakers = {n for s in scenes for n in s.characters}
        self.assertEqual(speakers, {"KELLY", "MAXIM", "KENTA"})
        self.assertEqual(scenes[0].characters, [])                                   # mở cảnh: không thoại
        self.assertGreaterEqual(len(scenes[1].characters), 2)                         # thoại 2 người

    def test_dialogue_fits_thirty_seconds(self):
        rows = [r for s in self.scenes for r in dialogue.lines(s.text)]
        self.assertGreaterEqual(len(rows), 5)
        self.assertLessEqual(dialogue.needed_seconds(rows), 22)                        # còn ≥ 8 s cho mở cảnh + kỹ năng không thoại

    def test_shot_types_named_for_the_director(self):
        low = self.text.lower()
        for word in ("toàn cảnh", "⭐", "lia nhòe", "text cuối"):
            self.assertIn(word, low)


class TrialDocTests(unittest.TestCase):
    def test_every_unverified_flag_is_listed(self):
        with open(DOC, encoding="utf-8") as f:
            doc = f.read()
        named = set(re.findall(r"`([a-z0-9_]+)`", doc))
        missing = [k for k, v in features.FEATURES.items() if not v["verified"] and k not in named]
        self.assertEqual(missing, [])
        self.assertIn("samples/du_an_thu_30s.txt", doc)
        self.assertIn("Tổng", doc)


if __name__ == "__main__":
    unittest.main()
