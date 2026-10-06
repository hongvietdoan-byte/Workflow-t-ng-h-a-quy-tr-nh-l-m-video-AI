"""S14.25 Đợt 6a (KE_HOACH_BO_NAO_PROMPT_TU_HOC mục 6a): góp ý của người dùng (core/feedback.py, bảng user_feedback) chảy vào `mistakes`
sau cờ `feedback_to_mistakes` (TẮT mặc định): chỉ kind delivery/scene, khâu director/image/motion, điểm ≤ 2, chữ ≥ 15 ký tự; khử trùng
bằng UNIQUE(source, ref_id); cờ tắt → không ghi gì."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import feedback, features, lessons
from core.db import connect
from core.pipeline import Pipeline

LOW = "Bàn tay nhân vật bị méo, thừa ngón ở cảnh mở đầu"


def _flag(value):
    return mock.patch.dict(os.environ, {"FEATURE_FEEDBACK_TO_MISTAKES": value})


class FeedbackToMistakesTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": self.dir,
                                                "FEATURE_SETTINGS_FILE": os.path.join(self.dir, "feature_settings.json")})
        self.env.start()
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.pid = self.p.create_project("t")

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def _mistakes(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM mistakes WHERE source='feedback'").fetchall()]

    def test_flag_exists_off_and_unverified(self):
        self.assertIn("feedback_to_mistakes", features.FEATURES)
        self.assertFalse(features.FEATURES["feedback_to_mistakes"]["verified"])
        with mock.patch.dict(os.environ, {}):
            os.environ.pop("FEATURE_FEEDBACK_TO_MISTAKES", None)
            self.assertFalse(features.on("feedback_to_mistakes"))

    def test_low_rating_becomes_one_mistake_with_source_ref_and_stage(self):
        fid = feedback.add(self.conn, "delivery", project_id=self.pid, stage="motion", rating=1, text=LOW)
        with _flag("1"):
            self.assertEqual(lessons.harvest(self.conn), 1)
        rows = self._mistakes()
        self.assertEqual(len(rows), 1)
        m = rows[0]
        self.assertEqual((m["source"], m["ref_id"], m["stage"], m["group_name"], m["project_id"]),
                         ("feedback", fid, "motion", "motion", self.pid))
        self.assertIn("tay", m["text"])
        handled = self.conn.execute("SELECT handled FROM user_feedback WHERE id=?", (fid,)).fetchone()[0]
        self.assertEqual(handled, f"mistake:{m['id']}")

    def test_director_and_image_stages_go_to_director_group(self):
        feedback.add(self.conn, "scene", project_id=self.pid, stage="director", rating=2, text="Kịch bản sai bối cảnh so với truyện gốc")
        feedback.add(self.conn, "scene", project_id=self.pid, stage="image", rating=2, text="Ảnh tối quá, không thấy rõ mặt")
        with _flag("1"):
            self.assertEqual(lessons.harvest(self.conn), 2)
        self.assertEqual(sorted((m["stage"], m["group_name"]) for m in self._mistakes()),
                         [("director", "director"), ("image", "director")])

    def test_duplicate_is_not_written_again(self):
        feedback.add(self.conn, "delivery", project_id=self.pid, stage="image", rating=2, text=LOW)
        with _flag("1"):
            self.assertEqual(lessons.harvest(self.conn), 1)
            self.assertEqual(lessons.harvest(self.conn), 0)
        self.assertEqual(len(self._mistakes()), 1)

    def test_flag_off_writes_nothing(self):
        fid = feedback.add(self.conn, "delivery", project_id=self.pid, stage="motion", rating=1, text=LOW)
        with _flag("0"):
            self.assertEqual(lessons.harvest(self.conn), 0)
        self.assertEqual(self._mistakes(), [])
        self.assertIsNone(self.conn.execute("SELECT handled FROM user_feedback WHERE id=?", (fid,)).fetchone()[0])

    def test_good_or_unfit_feedback_is_not_written(self):
        feedback.add(self.conn, "delivery", project_id=self.pid, stage="motion", rating=5, text="Rất ổn, dùng được ngay cho kênh")
        feedback.add(self.conn, "delivery", project_id=self.pid, stage="motion", rating=3, text="Tạm được nhưng hơi chậm nhịp")
        feedback.add(self.conn, "delivery", project_id=self.pid, stage="motion", rating=1, text="tệ")          # < 15 ký tự
        feedback.add(self.conn, "delivery", project_id=self.pid, stage="audio", rating=1, text="Giọng đọc bị rè, nhạc quá to")
        feedback.add(self.conn, "screen", screen="s2", stage="image", rating=1, text="Nút duyệt ảnh khó bấm quá trên màn nhỏ")
        feedback.add(self.conn, "delivery", project_id=self.pid, stage="motion", text=LOW)                        # không chấm điểm
        with _flag("1"):
            self.assertEqual(lessons.harvest(self.conn), 0)
        self.assertEqual(self._mistakes(), [])

    def test_untagged_feedback_is_kept_and_reported(self):
        feedback.add(self.conn, "delivery", project_id=self.pid, stage="motion", rating=1, text="Không đúng ý tôi chút nào cả")
        with _flag("1"):
            self.assertEqual(lessons.harvest(self.conn), 1)
        warn = self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='feedback_untagged'").fetchone()[0]
        self.assertEqual(warn, 1)


if __name__ == "__main__":
    unittest.main()
