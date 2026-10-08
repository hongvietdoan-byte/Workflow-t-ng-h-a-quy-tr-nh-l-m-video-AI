"""Giá đọc trên web ClipAI 08/10 (người dùng: 'check giá hết các model để Dashboard báo đúng giá'), chưa bấm tạo:
- Kling 3.0 Omni 12 s 9:16 không tiếng: 720p ¥7 · 1080p ¥10 · 4K ¥36 (có tiếng 720p ¥10); Kling O1 10 s: 720p ¥6 · 1080p ¥8 — giá ¥ làm tròn
  tới 1 tệ, cộng nửa tệ rồi đổi 7,2 ¥/USD (tính dư).
- Giọng: Eleven v3 / Multilingual v2 10,3 ¢ cho 1 029 ký tự; Turbo v2.5 5,1 ¢. Nhạc Eleven Music v2 / v2.5: 7,5 ¢ / 30 s. SFX 1 ¢ / 5 s.
  Seed Audio 1.0: 15 ¢/phút.
Âm thanh trước đây ghi sổ 1 'item' không giá (Dashboard hiện 0 USD) → nay ghi theo ký tự / giây; dòng cũ 'item' dùng giá dư mỗi lượt."""
import os
import tempfile
import unittest

from core import budget, cost, music
from core.db import connect


def _row(kind, model, tier, quantity, unit):
    return {"kind": kind, "model": model, "tier": tier, "quantity": quantity, "unit": unit}


class WebPriceTests(unittest.TestCase):
    def setUp(self):
        self.pricing = cost.load_pricing()

    def test_tts_is_priced_by_characters(self):
        self.assertAlmostEqual(budget.row_usd(self.pricing, _row("audio", "eleven_v3", "default", 1029, "char")), 0.103, delta=0.002)
        self.assertAlmostEqual(budget.row_usd(self.pricing, _row("audio", "eleven_turbo_v2_5", "default", 1029, "char")), 0.051,
                               delta=0.002)

    def test_music_and_sfx_are_priced_by_seconds(self):
        self.assertAlmostEqual(budget.row_usd(self.pricing, _row("audio", "music_v2", "default", 30, "second")), 0.075, delta=0.001)
        self.assertAlmostEqual(budget.row_usd(self.pricing, _row("audio", "eleven_text_to_sound_v2", "default", 5, "second")), 0.01,
                               delta=0.001)

    def test_an_old_item_row_has_a_price_never_zero(self):
        for model in ("eleven_v3", "music_v2", "eleven_text_to_sound_v2"):
            with self.subTest(model=model):
                self.assertGreater(budget.row_usd(self.pricing, _row("audio", model, "default", 1, "item")) or 0, 0)

    def test_kling_follows_the_web(self):
        per = self.pricing["per_video_second"]
        for key, yuan, secs in (("kling-v3-omni:std", 7, 12), ("kling-v3-omni:pro", 10, 12), ("kling-v3-omni:4k", 36, 12),
                                ("kling-video-o1:std", 6, 10), ("kling-video-o1:pro", 8, 10)):
            with self.subTest(key=key):
                self.assertGreaterEqual(per[key] * secs * 7.2, yuan)          # never below the web
                self.assertLessEqual(per[key] * secs * 7.2, yuan + 0.6)

    def test_music_records_its_seconds(self):
        from core.pipeline import Pipeline
        conn = connect(":memory:")
        pid = Pipeline(conn).create_project("t")

        class P:
            name = "clipai-audio"

            def generate_music(self, *a, **k):
                return "a1"
        music.submit_drafts(P(), tempfile.mkdtemp(), "x", 30000, True, count=1, ledger=(conn, pid))
        r = conn.execute("SELECT quantity, unit FROM usage_events WHERE kind='audio'").fetchone()
        self.assertEqual((r["quantity"], r["unit"]), (30.0, "second"))


if __name__ == "__main__":
    unittest.main()
