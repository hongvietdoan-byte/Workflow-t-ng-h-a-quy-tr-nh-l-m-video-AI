"""TON_DONG_2026-09-27 mục A: A4 (R1), A5 (R3), A14 (R2), A21 (R4) — lỗi nhỏ người chấm bộ kỹ năng tìm ra."""
import unittest

from core import continuity, director_report, ffmpeg_studio


class TradeoffKindTests(unittest.TestCase):          # A4 / R1
    def test_an_unknown_kind_is_reported_and_read_by_its_words(self):
        trade = [{"kind": "lines", "chose": "nhịp", "gave_up": "câu thoại của Maxim", "why": "x", "scene": 1}]
        self.assertEqual(director_report.unknown_kinds(trade), ["lines"])
        self.assertEqual(director_report._uncovered([("bỏ câu thoại", {1})], trade), [])
        self.assertEqual(director_report.unknown_kinds([{"kind": "dropped_line"}, {"gave_up": "x"}]), [])

    def test_fallback_words_do_not_take_the_frame_or_reading_time(self):
        self.assertEqual(director_report._uncovered([("lệch khung thời lượng", set())],
                                                    [{"chose": "x", "gave_up": "khung hình rộng", "why": "x"}]),
                         ["lệch khung thời lượng"])
        self.assertEqual(director_report._uncovered([("lệch khung thời lượng", set())],
                                                    [{"chose": "x", "gave_up": "khung 30 s của kịch bản", "why": "x"}]), [])
        self.assertEqual(director_report._uncovered([("bỏ câu thoại", set())],
                                                    [{"chose": "x", "gave_up": "thời gian đọc câu", "why": "x"}]),
                         ["bỏ câu thoại"])

    def test_the_report_text_names_the_unknown_kind(self):
        obj = {"scenes": [{"idx": 1, "shots": [{"role": "hook", "duration_s": 3, "characters": []}]}],
               "tradeoffs": [{"kind": "lines", "chose": "nhịp", "gave_up": "nhạc", "why": "x"}]}
        r = director_report.report(obj, "CẢNH 1\nKenta đi vào.")
        self.assertEqual(r["tradeoffs_unknown_kind"], ["lines"])
        self.assertIn("`tradeoffs.kind` không thuộc danh sách (lines)", director_report.text(r))


class MoneyShotOnlyForPromoTests(unittest.TestCase):  # A5 / R3
    def _obj(self, genre):
        return {"genre": genre, "scenes": [{"idx": 1, "shots": [{"role": "hook", "duration_s": 3}]}]}

    def test_a_drama_without_money_shot_is_not_warned(self):
        for genre in ("CINEMA_DRAMA", "SHORT_FORM", None):
            self.assertEqual(director_report.opening_and_product(self._obj(genre)), [], genre)

    def test_a_commercial_without_money_shot_is_warned(self):
        w = director_report.opening_and_product(self._obj("commercial"))
        self.assertEqual(len(w), 1)
        self.assertIn("money_shot", w[0])


class AxisNegationWindowTests(unittest.TestCase):    # A14 / R2
    def test_the_negation_stops_at_a_comma(self):
        self.assertTrue(continuity._OnPurpose.search("không đẹp, máy cố ý vượt trục"))
        self.assertTrue(continuity._OnPurpose.search("not pretty. the camera crosses the line"))
        self.assertFalse(continuity._OnPurpose.search("không để vượt trục"))
        self.assertFalse(continuity._OnPurpose.search("never crosses the axis"))


class DynamicLoudnormReasonTests(unittest.TestCase):  # A21 / R4
    def _msg(self, before):
        return " ".join(ffmpeg_studio.loudness_problems({"lufs": -14.0, "true_peak_dbfs": -1.6, "mode": "dynamic", "before": before}))

    def test_no_lra_measured_is_not_blamed_on_the_peaks(self):
        msg = self._msg({"lufs": -20.0, "lra": None, "true_peak_dbfs": -3.0})
        self.assertIn("không đo được dải động", msg)
        self.assertNotIn("đỉnh quá cao", msg)

    def test_a_wide_lra_and_a_high_peak_are_told_apart(self):
        self.assertIn("LRA 14", self._msg({"lufs": -20.0, "lra": 14.0, "true_peak_dbfs": -9.0}))
        self.assertIn("đỉnh quá cao", self._msg({"lufs": -20.0, "lra": 6.0, "true_peak_dbfs": -2.0}))

    def test_an_old_result_without_the_first_pass_still_says_it(self):
        self.assertIn("NÉN", self._msg(None))


class DirectorWeakSpotConditionTests(unittest.TestCase):  # S0.14 T5
    def test_both_director_prompts_carry_the_condition_not_a_ban(self):
        from core import prompts
        for intent_only in (False, True):
            text = prompts.role_text("director.md", intent_only=intent_only)
            self.assertIn("Điểm yếu chung của model video — điều kiện cân nhắc, không phải luật cấm", text)
            self.assertIn("dồn", text)


if __name__ == "__main__":
    unittest.main()
