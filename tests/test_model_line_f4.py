"""F4 (09/10) — màn chọn model gọn: dashboard.model_line (một dòng mỗi shot) + bảng Model một nút "Đổi" + thẻ clip không còn ô
"Đường chất lượng" riêng + dòng ước tính cả phim (Video & Bước 1). Không gọi dịch vụ: mọi giá là ước tính từ bảng giá / công thức."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import model_router
from core.db import connect
from core.pipeline import Pipeline
from dashboard import model_line
from tests.test_ui_quality_tier import TwoTierSeed


def _on():
    return mock.patch.dict(os.environ, {"FEATURE_TWO_TIER_QUALITY": "1", "VIDEO_PROVIDER": "mock"})


class ShotLineTests(unittest.TestCase):
    """4 shot (ưu tiên Cân bằng): 1 dễ · 2 khó · 3 khó + người chọn Seedance 2.0 · 4 người chọn Kling."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": os.path.join(self.tmp, "m.sqlite"),
                                               "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                                               "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "k")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        self.pid = self.p.create_project("F4", model_priority="balanced")
        c = self.p.conn
        self.sids = []
        for idx, level in enumerate(["easy", "complex", "complex", "complex"], start=1):
            sid = self.p.create_scene(self.pid, idx, f"S{idx}")
            c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"difficulty": level}), sid))
            c.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?, 'x', 5, 'approved')", (sid,))
            self.sids.append(sid)
        c.commit()
        model_router.set_override(c, self.sids[2], "seedance")
        model_router.set_override(c, self.sids[3], "kling")

    def test_lines_with_two_tier_on(self):
        with _on():
            lines = model_line.shot_lines(self.p.conn, self.pid)
        easy, hard, mine, kling = (lines[s] for s in self.sids)
        self.assertEqual(easy["model_text"], "Seedance 2.0 · 720p → phóng 1080p lúc dựng")
        self.assertIsNone(easy["keeps_content"])
        self.assertEqual(easy["source"], "đề xuất")
        self.assertEqual(hard["model_text"], "Seedance 2.5 · nháp 480p → cao 1080p")
        self.assertTrue(hard["keeps_content"])
        self.assertIn("giữ nội dung nháp ✓", hard["text"])
        self.assertGreater(easy["usd"], 0)
        self.assertGreater(hard["usd"], easy["usd"])                            # nháp 480p + nâng 1080p > một clip 720p
        self.assertIsNone(hard["warning"])
        self.assertIs(mine["keeps_content"], False)                             # #24: nháp Seedance 2.0 → bản cao là gen mới
        self.assertIn("gen mới", mine["warning"])
        self.assertEqual(mine["source"], "bạn chọn")
        self.assertTrue(mine["model_text"].startswith("Seedance 2.0 · nháp"))
        self.assertIn("KHÔNG giữ nội dung nháp", mine["text"])
        self.assertTrue(kling["model_text"].startswith("Kling 3.0 Omni"), kling["model_text"])
        self.assertIsNone(kling["keeps_content"])
        self.assertIn("USD", easy["text"])
        with _on():
            one = model_line.shot_line(self.p.conn, self.pid, self.sids[1])     # without a plan row: the same line
        self.assertEqual(one["text"], hard["text"])

    def test_flag_off_has_no_draft_part_and_choices_stay(self):
        before = [r["video_model"] for r in self.p.conn.execute("SELECT video_model FROM motion_prompts ORDER BY scene_id")]
        lines = model_line.shot_lines(self.p.conn, self.pid)
        for sid in self.sids:
            self.assertNotIn("nháp", lines[sid]["model_text"])
            self.assertNotIn("phóng", lines[sid]["model_text"])
            self.assertIsNone(lines[sid]["keeps_content"])
            self.assertIsNone(lines[sid]["warning"])
        after = [r["video_model"] for r in self.p.conn.execute("SELECT video_model FROM motion_prompts ORDER BY scene_id")]
        self.assertEqual(before, after)                                          # reading a line never changes a saved choice

    def test_film_line(self):
        with _on():
            film = model_line.film_line(self.p.conn, self.pid)
        self.assertRegex(film["text"], r"^Phim 20 s ≈ \d+\.\d\d USD — mục tiêu < 30 USD \((đạt|VƯỢT)\)$")
        self.assertIn("E1", film["help"])
        self.assertTrue(model_line.film_line(self.p.conn, self.pid)["text"].startswith("Phim 20 s ≈"))   # flag off: plan total


class ModelTableUiTests(TwoTierSeed):
    def _expand(self, at):
        return [x for x in at.get("popover") if x.proto.popover.label == "Đổi"]

    def test_one_line_per_shot_one_change_button_and_film_line(self):
        self.p.set_project_field(self.pid, "model_priority", "balanced")
        self.on()
        at = self.open(3)
        self.assertEqual(len(self._expand(at)), len(self.sids))                  # one "Đổi" per shot, nothing else per row
        keys = {s.key for s in at.selectbox}
        self.assertTrue({f"vm_{self.pid}_{s}" for s in self.sids} <= keys)       # the old model keys, now inside "Đổi"
        self.assertTrue({f"qpath_{s}" for s in self.sids} <= keys)               # the path choice lives once, in "Đổi"
        caps = "\n".join(c.value for c in at.caption)
        self.assertIn("Phim 20 s ≈", caps)
        self.assertIn("đổi ngay dưới thẻ clip", caps)                            # 09/10: the model line + Đổi sit under each clip card
        self.assertIn("nháp 480p → cao 1080p", "\n".join(m.value for m in at.markdown) + caps)
        self.assertIn(f"qfinal_{self.sids[0]}", {b.key for b in at.button})       # F3's high-tier button stays on the card

    def test_card_has_no_path_picker_and_flag_off_runs(self):
        at = self.open(3)                                                        # flag off: no path picker anywhere, table still there
        self.assertFalse(any(s.key and s.key.startswith("qpath_") for s in at.selectbox))
        self.assertTrue(self._expand(at))
        self.on()
        at = self.open(3)
        paths = [s for s in at.selectbox if s.key and s.key.startswith("qpath_")]
        self.assertEqual(len(paths), len(self.sids))                             # once per shot (the card has none any more)
        self.assertFalse(at.exception)


if __name__ == "__main__":
    unittest.main()
