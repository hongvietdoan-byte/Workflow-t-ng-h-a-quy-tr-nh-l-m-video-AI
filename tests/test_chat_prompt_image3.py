"""Kiểm thật #30 14/10: 6/7 lượt D6 bị chặn "mất mã ảnh / shot: Image 3" (≈ 0,04 USD/lượt vẫn trả). Gốc trên dữ liệu thật: gói ảnh
Image 1 render nền, Image 2 + Image 3 = HAI ảnh KELLY khác nhau (10.png, 12.png), bản code ghép viết "Images 2/3 show KELLY"; bản D6 duy
nhất qua (job 937, fixture) viết "Images 2 and 3 show KELLY" — code chỉ đọc ra Image 2. Claude KHÔNG bỏ ảnh; code đọc sai.
+ việc 5: bản bị từ chối → MỘT lượt sửa kèm đúng lỗi (qua sổ chi + ước tính), vẫn trượt → bản code ghép + diag.
+ việc 4: nút gen ảnh / video cộng giá D6 khi cờ bật."""
import json
import os
import unittest
from unittest import mock

from core import chat_prompt, cost
from tests.test_chat_prompt import ChatPromptTests, FakeClaude

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


ASSEMBLED_936 = _read("d6_p30_job936_assembled.txt")      # jobs.sent_package 936 (#30): the code-assembled prompt actually sent
D6_937 = _read("d6_p30_job937_d6.txt")                    # jobs.sent_package 937 (#30): the one D6 answer that passed


class RealP30Image3(unittest.TestCase):
    def test_real_answer_images_2_and_3_counts_both_pictures(self):
        sentence = next(s for s in D6_937.split(". ") if "Images 2 and 3" in s)   # Claude's own words, job 937
        self.assertEqual(sorted(chat_prompt._ref_units(sentence)), ["Image 2", "Image 3"])

    def test_real_p30_answer_without_the_slash_form_is_not_refused(self):
        # 937 passed only because it ALSO kept "Images 2/3" once later; the 6 refused answers (same brief, same 5–6 pictures) did not.
        self.assertIn("Images 2/3", D6_937)
        only_plural = D6_937.replace("locked to Images 2/3 only", "locked to these references only")
        self.assertEqual(chat_prompt.check(ASSEMBLED_936, D6_937, 4000), [])
        self.assertEqual(chat_prompt.check(ASSEMBLED_936, only_plural, 4000), [])

    def test_a_really_lost_picture_is_still_refused(self):
        lost = D6_937.replace("Images 2 and 3 show KELLY", "Image 2 shows KELLY").replace("Images 2/3", "Image 2")
        self.assertEqual(chat_prompt.check(ASSEMBLED_936, lost, 4000), ["mất mã ảnh / shot: Image 3"])
        self.assertTrue(chat_prompt.check("Images 2/3 KELLY. Image 1 render.", "Image 1 render with Image 2 and 3 people.", 999))

    def test_plural_lists_and_short_ranges(self):
        self.assertEqual(sorted(chat_prompt._ref_units("Images 2, 3 and 4 show KELLY")), ["Image 2", "Image 3", "Image 4"])
        self.assertEqual(sorted(chat_prompt._ref_units("Images 2–4 show KELLY")), ["Image 2", "Image 3", "Image 4"])
        self.assertEqual(sorted(chat_prompt._ref_units("Images 2/3 show KELLY")), ["Image 2", "Image 3"])

    def test_brief_allows_the_grouped_form_and_forbids_dropping_numbers(self):
        text = chat_prompt.build_text("image", "gpt-image", ASSEMBLED_936, [], {}, [], 4000)
        self.assertIn("Image 1, Image 2, Image 3, Image 4, Image 5", text)
        self.assertIn("Images 2 and 3", text)
        self.assertNotIn("không gộp", text)                     # the 14/10 line that pushed Claude to rewrite "Images 2/3"


class FixTurn(ChatPromptTests):
    GOOD = "Image 1 is the 3D PLACE render; Image 2 is KELLY holding her SKORP near the small tower."
    BAD = "Kelly holds her SKORP near the small tower of Image 1."

    def test_refused_answer_gets_one_fix_turn_told_the_fault(self):
        claude = FakeClaude([{"prompt": self.BAD}, {"prompt": self.GOOD}])
        with mock.patch.object(chat_prompt, "estimate", return_value=0.04) as est:
            self.assertEqual(self._rewrite(claude), self.GOOD)
        self.assertEqual(len(claude.calls), 2)
        self.assertEqual(est.call_count, 2)                                         # the fix turn is priced like the first
        fix = claude.calls[1]["prompt"]
        self.assertIn("Lượt sửa", fix)
        self.assertIn("thiếu Image 2", fix)
        self.assertIn(self.BAD, fix)
        self.assertEqual([p for _, p in claude.calls[1]["images"]], self.pics)
        self.assertTrue(any(code == "chat_prompt_fix_turn" and "0.040" in msg for _, code, msg in self.said))
        kept = json.loads(self.p.conn.execute("SELECT value FROM app_settings WHERE key=?",
                                              (chat_prompt.REFUSED_KEY.format(self.jid),)).fetchone()[0])
        self.assertEqual(kept[0]["prompt"], self.BAD)                               # the paid refused answer is kept as evidence

    def test_fix_turn_still_wrong_sends_the_assembled_and_never_pays_again_for_same_inputs(self):
        claude = FakeClaude([{"prompt": self.BAD}, {"prompt": self.BAD}])
        self.assertEqual(self._rewrite(claude), self._assembled())
        self.assertEqual(len(claude.calls), 2)
        self.assertTrue(any(code == "chat_prompt_refused" and "sau 1 lượt sửa" in msg for _, code, msg in self.said))
        nobody = FakeClaude([])
        self.assertEqual(self._rewrite(nobody), self._assembled())
        self.assertEqual(nobody.calls, [])

    def test_only_one_fix_turn_per_job(self):
        self._rewrite(FakeClaude([{"prompt": self.BAD}, {"prompt": self.GOOD}]))
        again = FakeClaude([{"prompt": self.BAD}])
        from tests.test_chat_prompt import ASSEMBLED
        self.assertEqual(self._rewrite(again, assembled=ASSEMBLED + " changed"), ASSEMBLED + " changed")
        self.assertEqual(len(again.calls), 1)

    def test_kept_refused_answer_is_used_when_the_check_now_accepts_it(self):
        self._rewrite(FakeClaude([{"prompt": self.BAD}, {"prompt": self.BAD}]))
        with mock.patch.object(chat_prompt, "check", return_value=[]):             # e.g. a corrected reading of the codes
            self.assertEqual(self._rewrite(FakeClaude([])), self.BAD)             # 0 USD: no call

    def _assembled(self):
        from tests.test_chat_prompt import ASSEMBLED
        return ASSEMBLED


class D6Price(unittest.TestCase):
    def test_d6_money_goes_to_the_director_line_not_other(self):
        from core import project_budget
        self.assertEqual(project_budget.claude_stage(chat_prompt.STAGE), "claude_director")   # was claude_other (cap 0,20)

    def test_off_changes_nothing(self):
        with mock.patch("core.features.on", return_value=False):
            self.assertEqual(cost.chat_prompt_estimate(None, 7), 0.0)
            self.assertEqual(cost.image_button_tag("gpt-image-2.5-sunburst", 1, shot=True),
                             cost.image_button_tag("gpt-image-2.5-sunburst", 1))

    def test_on_adds_one_call_plus_its_fix_turn_per_send(self):
        flags = mock.patch("core.features.on", side_effect=lambda n: n == chat_prompt.FLAG)
        with flags, mock.patch.object(cost, "llm_call_usd", return_value=0.05):
            self.assertAlmostEqual(cost.chat_prompt_estimate(None, 7), 0.70)          # 7 × (1 call + 1 fix turn) × 0.05
            est = {"usd": 0.36, "missing": False}
            with mock.patch("core.money_policy.estimate", return_value=est):
                self.assertEqual(cost.image_button_tag("gpt-image-2.5-sunburst", 7, shot=True), " · ≈ 1.06 USD (ước tính)")
                self.assertEqual(cost.image_button_tag("gpt-image-2.5-sunburst", 7), " · ≈ 0.36 USD (ước tính)")
            with mock.patch.object(cost, "_group_clips", return_value=[(1, None)]), \
                    mock.patch.object(cost, "clip_estimate", return_value=0.30):
                self.assertEqual(cost.video_button_tag(None, [1]), " · 1 clip ≈ 0.40 USD (ước tính, gồm D6 ≈ 0.10)")


if __name__ == "__main__":
    unittest.main()


class D6TokenCeilingTests(unittest.TestCase):
    def test_d6_has_its_own_ceiling_above_the_8000_default(self):
        # 14/10: D6 (stage chat_prompt) had no entry → the 8000 default; one paid D6 of #28–#30 stopped at exactly 8000 (cut answer)
        from core import llm_runner
        self.assertGreaterEqual(llm_runner.stage_settings(chat_prompt.STAGE)["max_tokens"], 12000)
