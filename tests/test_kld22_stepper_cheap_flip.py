"""08/10 #22 Khủng Long Đỏ (9/9 clip đã duyệt, video cuối đã dựng): thanh trên vẫn hiện "⚠ Video · 5/9 ⚠4", "Bản giao · cũ",
"Ngân sách chưa khóa" + "👉 Duyệt & KHÓA ngân sách". Đọc dữ liệu thật: 4 clip làm trong "Thử rẻ" bằng seedance-fast (dấu input_hash có
model = seedance-fast); khi cờ two_tier_quality bật, Thử rẻ bị bỏ qua → scene_choice trả 'seedance' → dấu không khớp → clip "cũ" → dự án
"chưa xong" (project_budget.finished False) → nhắc khóa ngân sách. Đổi Thử rẻ (hay cờ bỏ qua nó) chỉ đổi bậc giá, không làm clip cũ."""
import unittest
from unittest import mock

from core import lineage, project_budget, quality_tier
from core.db import connect
from core.pipeline import Pipeline


class CheapFlipDoesNotOutdateClipsTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect(":memory:"))
        c = self.p.conn
        self.pid = self.p.create_project("kld")
        cols = [r[1] for r in c.execute("PRAGMA table_info(projects)")]
        c.execute("UPDATE projects SET test_quality=1" + (", model_priority='quality'" if "model_priority" in cols else "")
                  + " WHERE id=?", (self.pid,))
        self.sid = self.p.create_scene(self.pid, 1, "S1")
        img = self.p.create_job(self.sid, "image_gen")
        c.execute("UPDATE jobs SET state='approved' WHERE id=?", (img,))
        c.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state, image_job_id) VALUES (?, 'x', 5, 'approved', ?)",
                  (self.sid, img))
        mp = c.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (self.sid,)).fetchone()
        aspect = c.execute("SELECT aspect FROM projects WHERE id=?", (self.pid,)).fetchone()[0]
        vid = self.p.create_job(self.sid, "video_gen")
        c.execute("UPDATE jobs SET state='approved', model='seedance-fast', source_job_id=?, input_hash=? WHERE id=?",
                  (img, lineage.video_input_hash(mp, aspect, "seedance-fast", False), vid))
        c.commit()

    def _summary(self):
        return lineage._summary(self.p.conn, self.pid)

    def test_clip_made_in_cheap_mode_stays_fresh_when_two_tier_ignores_cheap_mode(self):
        with mock.patch.object(quality_tier, "enabled", return_value=False):
            self.assertEqual(self._summary()["videos"], (1, 0))          # made and judged in Thử rẻ
        with mock.patch.object(quality_tier, "enabled", return_value=True):
            self.assertEqual(self._summary()["videos"], (1, 0))          # flag on: Thử rẻ ignored, the clip is still current
            self.assertTrue(project_budget.finished(self.p.conn, self.pid))

    def test_cheap_mode_turned_off_by_hand_does_not_outdate_either(self):
        self.p.conn.execute("UPDATE projects SET test_quality=0 WHERE id=?", (self.pid,))
        self.p.conn.commit()
        with mock.patch.object(quality_tier, "enabled", return_value=False):
            self.assertEqual(self._summary()["videos"], (1, 0))

    def test_a_real_change_still_outdates(self):
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='khác' WHERE scene_id=?", (self.sid,))
        self.p.conn.commit()
        with mock.patch.object(quality_tier, "enabled", return_value=True):
            self.assertEqual(self._summary()["videos"], (0, 1))


if __name__ == "__main__":
    unittest.main()
