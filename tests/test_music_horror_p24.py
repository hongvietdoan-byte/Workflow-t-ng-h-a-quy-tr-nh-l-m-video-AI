"""#24 (08/10, teaser Halloween "HĐ Trồi lên & HĐ Khóc ai oán"): the music had no horror tone, the Director wrote
{"tone": "commercial", "ending": "button"} and the three drafts were briefed "Clear, confident energy … a short comic final hit"
under a ghost crawling out of a well. The mood and the Director's music below are #24's own (DB, project 24)."""
import unittest

from core import music_intent, music_timing
from tests.test_music_intent import project

P24_MOOD = "rùng rợn, hồi hộp, bí ẩn rồi chuyển sang ai oán trước khi cắt sang quảng cáo"
P24_MUSIC = {"music": {"tone": "commercial", "motif": "jumpscare_reveal", "ending": "button"}}


class HorrorToneTests(unittest.TestCase):
    def test_p24_commercial_horror_is_scored_as_horror(self):
        p, pid = project([(1, P24_MOOD, 22.0, {})], director=P24_MUSIC)
        b = music_timing.brief(p, pid)
        self.assertEqual(b["intent"]["tone"]["tone"], "horror")
        text = b["prompt"]
        for gone in ("comic button", "comic final hit", "confident energy", "product moment", "hopeful", "tender"):
            self.assertNotIn(gone, text)
        self.assertIn("horror teaser", text)
        self.assertIn("stinger", text)
        self.assertIn("dread", text)
        self.assertEqual(b["intent"]["ending"]["kind"], "cliffhanger")
        self.assertIn("button", b["intent"]["ending"]["why"])

    def test_horror_words_win_over_crying(self):
        p, pid = project([(1, "rùng rợn, bí ẩn", 5.0, {}), (2, "ai oán, khóc", 5.0, {})])
        tone = music_intent.read_tone(p, pid, music_timing.sections(p, pid))
        self.assertEqual(tone["tone"], "horror")
        b = music_timing.brief(p, pid)
        self.assertIn("eerie lament", b["prompt"])
        self.assertNotIn("solo piano", b["prompt"])

    def test_a_cheerful_commercial_stays_commercial(self):
        p, pid = project([(1, "tươi vui, sôi động", 10.0, {})], director={"music": {"tone": "commercial"}})
        self.assertEqual(music_timing.brief(p, pid)["intent"]["tone"]["tone"], "commercial")

    def test_button_is_kept_for_a_comedy(self):
        p, pid = project([(1, "hài hước", 6.0, {})], director={"music": {"tone": "comedy", "ending": "button"}})
        self.assertEqual(music_timing.brief(p, pid)["intent"]["ending"]["kind"], "button")


if __name__ == "__main__":
    unittest.main()
