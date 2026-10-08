"""Khủng Long Đỏ mục 6. 07/10 một ảnh chụp ghi Seedance 2.0 · 12 s · 1080p = 2,93 USD → hệ số 0,72. 08/10 đọc lại giá trên web ClipAI
(cùng 12 s · 9:16 · không âm thanh · không tham chiếu, chưa bấm tạo): 2.0 720p 1,81 · 2.0 1080p 4,08 · 2.5 720p 2,77 (mẫu 480p 1,29) ·
2.5 1080p 6,24 — đúng bằng công thức token của repo ở cả 4 mức. Hệ số 0,72 làm ước tính THẤP hơn giá thật (trái 'tính dư') → bỏ;
API cũng ghi số token thật = công thức ×1,01 (tools/clipai_price_check.py, 36 clip #22)."""
import unittest

from core import cost

S20, S25 = "dreamina-seedance-2-0-260128", "dreamina-seedance-2-5-260628"
WEB_0810 = {(S20, "720p"): 1.81, (S20, "1080p"): 4.08, (S25, "720p"): 2.77, (S25, "1080p"): 6.24}


class SeedancePriceTests(unittest.TestCase):
    def test_the_estimate_is_the_web_price_of_08_10(self):
        for (model, res), usd in WEB_0810.items():
            with self.subTest(model=model, res=res):
                self.assertAlmostEqual(cost.seedance_estimate(model, res, "9:16", 12), usd, delta=0.01)

    def test_no_factor_lowers_a_price_below_the_web(self):
        for key, m in cost.SEEDANCE_MEASURED.items():
            with self.subTest(key=key):
                self.assertGreaterEqual(m["factor"], 1.0)


if __name__ == "__main__":
    unittest.main()
