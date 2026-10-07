"""Khủng Long Đỏ mục 6 (người dùng 07/10): giá THẬT ClipAI Seedance 2.0 · 12 s · 1080p · 9:16 · không âm thanh = 2,93 USD; công thức
token của repo ra ≈ 4,08 (cao ~39 %). Hiệu chỉnh đúng tổ hợp đã đo (2.0 @ 1080p) bằng hệ số làm tròn LÊN (ước tính vẫn ≥ giá thật —
chính sách 'tính dư'); tổ hợp chưa có giá thật giữ công thức cũ."""
import unittest

from core import cost

S20, S25 = "dreamina-seedance-2-0-260128", "dreamina-seedance-2-5-260628"


class SeedancePriceTests(unittest.TestCase):
    def test_measured_case_matches_the_real_price_from_above(self):
        usd = cost.seedance_estimate(S20, "1080p", "9:16", 12)
        self.assertGreaterEqual(usd, 2.93)
        self.assertLessEqual(usd, 2.93 * 1.02)

    def test_factor_carries_over_to_other_lengths_and_ratios(self):
        self.assertAlmostEqual(cost.seedance_estimate(S20, "1080p", "9:16", 6) / cost.seedance_estimate(S20, "1080p", "9:16", 12), 0.5, 2)
        self.assertLess(cost.seedance_estimate(S20, "1080p", "16:9", 12, 5), cost.seedance_token_usd(
            S20, cost.seedance_tokens("1080p", "16:9", 12, 5), True))

    def test_unmeasured_cases_are_unchanged(self):
        self.assertAlmostEqual(cost.seedance_estimate(S20, "720p", "9:16", 12),
                               cost.seedance_token_usd(S20, cost.seedance_tokens("720p", "9:16", 12), False))
        self.assertAlmostEqual(cost.seedance_estimate(S25, "1080p", "9:16", 12),
                               cost.seedance_token_usd(S25, cost.seedance_tokens("1080p", "9:16", 12), False))

    def test_the_source_is_written_down(self):
        self.assertIn("2,93", cost.SEEDANCE_MEASURED[(S20, "1080p")]["source"])


if __name__ == "__main__":
    unittest.main()
