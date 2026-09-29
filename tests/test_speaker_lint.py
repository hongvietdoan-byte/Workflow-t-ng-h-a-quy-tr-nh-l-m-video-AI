"""S0.14 T2: a Kling clip with dialogue names who speaks (core/speaker_lint.py)."""
import os
import unittest
from unittest import mock

from core import speaker_lint as sl

TWO = {"characters": ["KENTA", "KELLY"], "dialogue": [{"speaker": "KENTA", "text": "Đi thôi."}]}
ALONE = {"characters": ["KENTA"], "dialogue": [{"speaker": "KENTA", "text": "Đi thôi."}]}
CARD = {"characters": ["KENTA", "KELLY"], "dialogue": [{"speaker": "TEXT CUỐI", "text": "Free Fire"}]}


class SpeakerLintTest(unittest.TestCase):
    def test_alone_in_frame_not_checked(self):
        self.assertEqual(sl.problems("Kenta looks at the tower.", [ALONE]), [])

    def test_on_screen_text_is_not_a_voice(self):
        self.assertEqual(sl.problems("Two players stand.", [CARD]), [])

    def test_unnamed_speaker_found(self):
        self.assertEqual(sl.problems("Kenta and Kelly stand by the clock tower.", [TWO]), ["KENTA"])

    def test_named_in_same_sentence(self):
        self.assertEqual(sl.problems("Kelly waits. Kenta turns and says something to her.", [TWO]), [])
        self.assertEqual(sl.problems("KENTA speaks (mouth moving, no sound).", [TWO]), [])

    def test_name_and_speak_word_in_different_sentences(self):
        self.assertEqual(sl.problems("Kenta stands still. Someone speaks.", [TWO]), ["KENTA"])

    def test_decimal_is_not_a_sentence_end(self):
        self.assertEqual(sl.problems("At 3.5 s Kenta answers.", [TWO]), [])

    def test_two_speakers_across_shots(self):
        a = {"characters": ["KENTA"], "dialogue": [{"speaker": "KENTA", "text": "A"}]}
        b = {"characters": ["MAXIM"], "dialogue": [{"speaker": "MAXIM", "text": "B"}]}
        self.assertEqual(sl.problems("Kenta speaks. The camera pans.", [a, b]), ["MAXIM"])

    def test_fix_sentence_names_listener(self):
        self.assertEqual(sl.fix_sentence([TWO], ["KENTA"]),
                         "KENTA speaks (mouth moving, no sound). KELLY listens, mouth closed.")

    def test_flag_off_reports_only(self):
        with mock.patch.dict(os.environ, {"FEATURE_SPEAKER_TAGS": "0"}):
            res = sl.apply("Kenta and Kelly stand.", [TWO])
        self.assertEqual(res["missing"], ["KENTA"])
        self.assertEqual(res["prompt"], "Kenta and Kelly stand.")
        self.assertIn("TẮT", res["why_not"])
        self.assertIn("chưa thêm", sl.message("clip", res))

    def test_flag_on_adds_sentence(self):
        with mock.patch.dict(os.environ, {"FEATURE_SPEAKER_TAGS": "1"}):
            res = sl.apply("Kenta and Kelly stand.", [TWO])
        self.assertTrue(res["prompt"].endswith("KELLY listens, mouth closed."))
        self.assertIn("đã thêm", sl.message("clip", res))

    def test_flag_on_but_over_limit(self):
        with mock.patch.dict(os.environ, {"FEATURE_SPEAKER_TAGS": "1"}):
            res = sl.apply("Kenta and Kelly stand.", [TWO], limit=30)
        self.assertEqual(res["prompt"], "Kenta and Kelly stand.")
        self.assertIn("30", res["why_not"])

    def test_is_kling(self):
        self.assertTrue(sl.is_kling("kling-v3-omni"))
        self.assertFalse(sl.is_kling("dreamina-seedance-2-0-fast-260128"))
        self.assertFalse(sl.is_kling(None))

    def test_kling_speech_languages_in_rules(self):
        from core import video_rules
        text = "\n".join(video_rules.summary_lines())
        self.assertIn("không tiếng Việt", text)


if __name__ == "__main__":
    unittest.main()
