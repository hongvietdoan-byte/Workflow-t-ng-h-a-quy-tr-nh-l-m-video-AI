"""08/10 dự án #24 (test_quality=1 kế thừa, cờ two_tier_quality BẬT): code bỏ qua Thử rẻ (quality_tier.cheap_mode) nhưng thanh trên,
dòng 💵 và "Ước tính chạy tự động" vẫn ghi "🧪 Thử rẻ"; ước tính lại chưa tính nháp 480p + bản cao như quy trình 2 bậc thật."""
import json
import unittest
from unittest import mock

from core import cost, quality_tier
from core.db import connect
from core.pipeline import Pipeline
from dashboard import quality_ui


class ModeLabelTests(unittest.TestCase):
    def test_flag_on_says_two_tier_not_cheap(self):
        proj = {"test_quality": 1}
        with mock.patch.object(quality_ui, "enabled", return_value=True):
            short, full = quality_ui.mode_label(proj)
        self.assertNotIn("Thử rẻ", short)
        self.assertIn("2 bậc", short)
        self.assertIn("480p", full)

    def test_flag_off_keeps_cheap_chip_only_when_on(self):
        with mock.patch.object(quality_ui, "enabled", return_value=False):
            self.assertEqual(quality_ui.mode_label({"test_quality": 1})[0], "🧪 Thử rẻ")
            self.assertIsNone(quality_ui.mode_label({"test_quality": 0}))


class TwoTierEstimateTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("t")
        self.hard = self.p.create_scene(self.pid, 1, "S1")
        self.easy = self.p.create_scene(self.pid, 2, "S2")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"difficulty": "easy"}), self.easy))
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"difficulty": "complex"}), self.hard))   # 09/10: nhãn rõ
        for sid in (self.hard, self.easy):
            self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?, 'x', 5, 'approved')", (sid,))
        self.p.conn.commit()
        self.rows = [{"scene_id": self.hard, "model": "seedance-2.5", "billed_seconds": 5.0, "cost": 0.4},
                     {"scene_id": self.easy, "model": "seedance-2.5", "billed_seconds": 5.0, "cost": 0.4}]

    def test_flag_off_adds_nothing(self):
        with mock.patch.object(quality_tier, "enabled", return_value=False):
            self.assertEqual(quality_tier.run_estimate(self.p.conn, self.pid, self.rows)["usd"], 0.0)

    def test_draft_first_shot_pays_a_draft_and_the_1080p_final(self):
        with mock.patch.object(quality_tier, "enabled", return_value=True):
            got = quality_tier.run_estimate(self.p.conn, self.pid, self.rows, cost.load_pricing())
        self.assertEqual(got["drafts"], 1)                      # the easy shot goes straight to the high tier: no draft
        self.assertGreater(got["usd"], 0.0)
        self.assertEqual(got["finals_1080"], 1)
        text = cost.format_run_estimate({"images": 0, "videos": 1.0, "llm": 0.1, "total": 1.1, "max": 2.0, "unknown": [],
                                         "counts": {"images": 0, "clips": 2, "seconds": 10, "drafts": 1, "finals_1080": 1}})
        self.assertIn("1 nháp 480p", text)


if __name__ == "__main__":
    unittest.main()
