"""09/10 (người dùng): dưới thẻ clip hai ô — "Model" + "Chất lượng" (480p / 720p / 1080p / 4K theo model cho phép), thay ô "Cấu hình".
Lõi: model_router.resolution_options / set_resolution / scene_choice (motion_prompts.video_resolution); runner gửi đúng mức (Kling =
kling_mode). Không gọi dịch vụ."""
import os
import unittest
from unittest import mock

from core import model_router, quality_tier
from tests import test_model_line_f4 as F4
from tests.test_model_line_f4 import _on
from tests.test_ui_quality_tier import TwoTierSeed


class OptionsTests(unittest.TestCase):
    def test_each_model_lists_only_its_levels(self):
        vals = lambda m: [v for v, _ in model_router.resolution_options(m)]   # noqa: E731
        self.assertEqual(vals("seedance"), ["480p", "720p", "1080p", "4k"])
        self.assertEqual(vals("seedance-fast"), ["480p", "720p"])
        self.assertEqual(vals("seedance-2.5"), ["480p", "720p"])               # flag off: API 2.5 has no 1080p
        self.assertEqual(vals("kling"), ["std", "pro", "4k"])
        self.assertEqual(dict(model_router.resolution_options("kling"))["pro"], "1080p (pro)")
        with _on():
            self.assertEqual(vals("seedance-2.5"), ["480p", "720p", "1080p"])  # 1080p = nháp 480p → nâng
        self.assertEqual(model_router.resolution_options("không-có"), [])


class CoreTests(unittest.TestCase):
    """Shot 1 dễ · 2 khó · 3 khó + Seedance 2.0 chọn tay · 4 Kling chọn tay (dữ liệu của ShotLineTests)."""
    setUp = F4.ShotLineTests.setUp

    def choice(self, i):
        return model_router.scene_choice(self.p.conn, self.sids[i])

    def test_pick_applies_and_bad_level_refused(self):
        c = self.p.conn
        model_router.set_resolution(c, self.sids[2], "4k")
        ch = self.choice(2)
        self.assertEqual((ch["model"], ch["resolution"], ch["res_source"]), ("seedance", "4k", "override"))
        from core import cost
        row = next(r for r in model_router.plan(c, self.pid, cost.load_pricing()) if r["scene_id"] == self.sids[2])
        self.assertEqual(row["resolution_pick"], "4k")
        self.assertGreater(row["usd_per_sec"], 1.0)                             # 4K không rơi về giá 720p (tính dư)
        with self.assertRaises(ValueError):
            model_router.set_resolution(c, self.sids[3], "1080p")               # Kling: std / pro / 4k only
        model_router.set_resolution(c, self.sids[3], "4k")
        self.assertEqual(self.choice(3)["resolution"], "4k")
        model_router.set_override(c, self.sids[2], "seedance-fast")             # model without 4K → back to the recommendation
        self.assertNotEqual(self.choice(2).get("res_source"), "override")
        model_router.set_resolution(c, self.sids[3], None)
        self.assertIsNone(model_router.chosen_resolution(c, self.sids[3]))

    def test_two_tier_paths_follow_the_pick(self):
        c = self.p.conn
        with _on():
            self.assertEqual(self.choice(1)["model"], "seedance-2.5")          # E1: shot khó → nháp 2.5
            model_router.set_resolution(c, self.sids[1], "720p")              # gen thẳng 720p — model stays 2.5 (pinned)
            self.assertEqual(quality_tier.path(c, self.sids[1]), "direct")
            ch = self.choice(1)
            self.assertEqual((ch["model"], ch["resolution"]), ("seedance-2.5", "720p"))
            model_router.set_resolution(c, self.sids[1], "1080p")             # 2.5 @ 1080p = nháp 480p → nâng 1080p
            self.assertEqual(quality_tier.path(c, self.sids[1]), "draft_first")
            ch = self.choice(1)
            self.assertEqual((ch["resolution"], ch["final_resolution"]), ("480p", "1080p"))
            model_router.set_resolution(c, self.sids[0], "1080p")             # shot dễ: 2.0 thẳng 1080p, không phóng lúc dựng
            from dashboard import model_line
            self.assertEqual(model_line.shot_line(c, self.pid, self.sids[0])["model_text"], "Seedance 2.0 · 1080p")
            model_router.set_resolution(c, self.sids[1], None)                # back to the Director's path
            self.assertIsNone(c.execute("SELECT quality_path FROM motion_prompts WHERE scene_id=?", (self.sids[1],)).fetchone()[0])

    def test_runner_sends_the_level(self):
        from core.runner import VideoRunner
        c = self.p.conn
        model_router.set_resolution(c, self.sids[3], "4k")
        model_router.set_resolution(c, self.sids[2], "1080p")
        runner = VideoRunner.__new__(VideoRunner)
        runner.p = self.p
        for sid, want in ((self.sids[3], {"kling_mode": "4k"}), (self.sids[2], {"resolution": "1080p"})):
            job = {"id": 0, "project_id": self.pid, "scene_id": sid}
            with mock.patch.object(VideoRunner, "_choice", return_value=model_router.scene_choice(c, sid)), \
                    mock.patch.object(VideoRunner, "_skill_assets", return_value=None):
                out = runner._base_submit_kwargs(job)
            for k, v in want.items():
                self.assertEqual(out.get(k), v, out)
            if "kling_mode" in want:
                self.assertNotIn("resolution", out)


class CardUiTests(TwoTierSeed):
    def test_quality_box_lists_model_levels_and_saves(self):
        self.p.set_project_field(self.pid, "model_priority", "balanced")
        self.on()
        at = self.open(3)
        box = next(s for s in at.selectbox if s.key == f"vres_{self.sids[0]}")
        self.assertEqual(box.label, "Chất lượng")
        self.assertIsNone(box.value)
        self.assertTrue(box.format_func(None).startswith("Đề xuất:"))
        self.assertFalse(any(s.label == "Cấu hình" for s in at.selectbox))
        opts = [o for o in box.options]
        self.assertIn("1080p (nháp 480p → nâng)", opts)                       # shot nháp 2.5 (E1)
        self.assertNotIn("4K", opts)
        box.set_value("720p").run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(model_router.chosen_resolution(self.p.conn, self.sids[0]), "720p")


if __name__ == "__main__":
    unittest.main()


class PickSavesInOneRunTests(TwoTierSeed):
    def test_model_pick_is_saved_by_callback(self):
        """09/10 (chọn bị lag): ô Model lưu qua callback → lượt chạy kế tiếp đã thấy model mới, ô Chất lượng theo model mới."""
        self.p.set_project_field(self.pid, "model_priority", "balanced")
        self.on()
        at = self.open(3)
        sid = self.sids[0]
        at.selectbox(key=f"vm_{self.pid}_{sid}").set_value("seedance").run()
        self.assertFalse(at.exception, at.exception)
        row = self.p.conn.execute("SELECT video_model FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        self.assertEqual(row[0], "seedance")
        self.assertIn("4K", at.selectbox(key=f"vres_{sid}").options)            # Seedance 2.0: 480p … 4K


class AnimaticNoteTests(unittest.TestCase):
    def test_note_says_what_is_missing(self):
        from dashboard.steps.step2 import animatic_note
        bare = animatic_note({"shots": 9, "seconds": 22.0, "voices": 0, "music": False, "subtitles": False, "missing": []})
        self.assertIn("chưa có thoại", bare)
        self.assertIn("chưa có nhạc", bare)
        self.assertIn("chỉ có hình", bare)
        full = animatic_note({"shots": 3, "seconds": 9.0, "voices": 2, "music": True, "subtitles": True, "missing": [2]})
        self.assertNotIn("chỉ có hình", full)
        self.assertIn("2 câu thoại · có nhạc · có phụ đề · ⚠ 1 shot chưa có ảnh", full)
