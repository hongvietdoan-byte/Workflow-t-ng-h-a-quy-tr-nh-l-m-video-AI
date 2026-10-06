"""S14.25 (Bộ não prompt Đợt 6a): góp ý người dùng chấm thấp chảy vào `mistakes` sau cờ `feedback_to_mistakes` (TẮT mặc định) —
có nguồn (source='feedback', ref_id = id góp ý, stage), khử trùng, không ghi khi cờ tắt, góp ý tốt / góp ý về phần mềm không chảy vào."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import feedback, features, lessons
from core.db import connect

LONG = "tay nhân vật bị thừa ngón ở cảnh cận"


def _on(name):
    return name == "feedback_to_mistakes"


class FeedbackToMistakesTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        self.conn = connect()
        for name in ("p1", "p2"):
            self.conn.execute("INSERT INTO projects (name, created_at) VALUES (?, '2026-10-01T00:00:00Z')", (name,))
        self.conn.commit()

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _mistakes(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM mistakes ORDER BY id")]

    def test_flag_exists_and_is_off(self):
        self.assertIn("feedback_to_mistakes", features.FEATURES)
        self.assertFalse(features.FEATURES["feedback_to_mistakes"]["verified"])

    def test_low_rating_makes_one_mistake_with_source_and_stage(self):
        fid = feedback.add(self.conn, "scene", project_id=1, stage="motion", rating=2, text=LONG)
        with mock.patch.object(features, "on", side_effect=_on):
            out = feedback.to_mistakes(self.conn)
        self.assertEqual(out["added"], 1)
        (m,) = self._mistakes()
        self.assertEqual((m["source"], m["ref_id"], m["stage"], m["group_name"], m["project_id"]), ("feedback", fid, "motion", "motion", 1))
        self.assertIn("thừa ngón", m["text"])
        row = self.conn.execute("SELECT handled FROM user_feedback WHERE id=?", (fid,)).fetchone()
        self.assertEqual(row["handled"], f"mistake:{m['id']}")

    def test_director_and_image_go_to_the_director_group(self):
        feedback.add(self.conn, "delivery", project_id=1, stage="director", rating=1, text="kịch bản không khớp cảnh quay cuối")
        feedback.add(self.conn, "scene", project_id=2, stage="image", rating=2, text=LONG)
        with mock.patch.object(features, "on", side_effect=_on):
            feedback.to_mistakes(self.conn)
        self.assertEqual([(m["stage"], m["group_name"]) for m in self._mistakes()], [("director", "director"), ("image", "director")])

    def test_rerun_and_duplicate_text_do_not_write_again(self):
        feedback.add(self.conn, "scene", project_id=1, stage="image", rating=1, text=LONG)
        dup = feedback.add(self.conn, "scene", project_id=1, stage="image", rating=2, text="  Tay nhân vật bị THỪA ngón ở cảnh cận. ")
        with mock.patch.object(features, "on", side_effect=_on):
            first = feedback.to_mistakes(self.conn)
            again = feedback.to_mistakes(self.conn)
        self.assertEqual((first["added"], again["added"]), (1, 0))
        self.assertEqual(len(self._mistakes()), 1)
        self.assertEqual(first["skipped"].get("trùng"), 1)
        h = self.conn.execute("SELECT handled FROM user_feedback WHERE id=?", (dup,)).fetchone()["handled"]
        self.assertTrue(h.startswith("bỏ qua: trùng"), h)

    def test_same_text_other_project_still_counts(self):
        feedback.add(self.conn, "scene", project_id=1, stage="image", rating=1, text=LONG)
        feedback.add(self.conn, "scene", project_id=2, stage="image", rating=1, text=LONG)
        with mock.patch.object(features, "on", side_effect=_on):
            self.assertEqual(feedback.to_mistakes(self.conn)["added"], 2)                     # 2 dự án = bằng chứng xuyên dự án

    def test_flag_off_writes_nothing(self):
        fid = feedback.add(self.conn, "scene", project_id=1, stage="motion", rating=1, text=LONG)
        with mock.patch.object(features, "on", return_value=False):
            out = feedback.to_mistakes(self.conn)
            lessons.harvest(self.conn)
        self.assertEqual(out, {"added": 0, "skipped": {}, "off": True})
        self.assertEqual(self._mistakes(), [])
        self.assertIsNone(self.conn.execute("SELECT handled FROM user_feedback WHERE id=?", (fid,)).fetchone()["handled"])

    def test_good_screen_short_and_other_stage_do_not_flow_and_are_counted(self):
        feedback.add(self.conn, "scene", project_id=1, stage="image", rating=4, text=LONG)            # tốt
        feedback.add(self.conn, "scene", project_id=1, stage="image", rating=3, text=LONG)            # trung bình
        feedback.add(self.conn, "screen", screen="step2", stage="image", rating=1, text=LONG)         # góp ý phần mềm → devsys
        feedback.add(self.conn, "scene", project_id=1, stage="image", rating=1, text="xấu quá")       # < 15 ký tự
        feedback.add(self.conn, "delivery", project_id=1, stage="audio", rating=1, text=LONG)         # khâu ngoài director/image/motion
        feedback.add(self.conn, "delivery", project_id=1, rating=1, text=LONG)                        # không ghi khâu
        feedback.add(self.conn, "delivery", project_id=1, rating=1)                                   # chỉ chấm, không chữ
        with mock.patch.object(features, "on", side_effect=_on):
            out = feedback.to_mistakes(self.conn)
        self.assertEqual(out["added"], 0)
        self.assertEqual(self._mistakes(), [])
        self.assertEqual(out["skipped"].get("chữ quá ngắn"), 2)
        self.assertEqual(out["skipped"].get("khâu không học"), 1)
        self.assertEqual(out["skipped"].get("thiếu khâu"), 1)
        handled = [r["handled"] for r in self.conn.execute("SELECT handled FROM user_feedback ORDER BY id")]
        self.assertEqual(handled[:3], [None, None, None])                                         # tốt / screen: không đánh dấu

    def test_harvest_includes_feedback_and_unclassified_is_kept_with_a_warning(self):
        feedback.add(self.conn, "scene", project_id=1, stage="image", rating=1, text="cảm giác cả cảnh rất khó chịu")
        with mock.patch.object(features, "on", side_effect=_on):
            added = lessons.harvest(self.conn)
        self.assertEqual(added, 1)
        self.assertEqual(len(self._mistakes()), 1)                                                # không gán tag vẫn ghi
        self.assertTrue(self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='feedback_unclassified'").fetchone()[0])

    def test_one_complaint_is_not_a_lesson(self):
        feedback.add(self.conn, "scene", project_id=1, stage="image", rating=1, text=LONG)
        with mock.patch.object(features, "on", side_effect=_on):
            lessons.harvest(self.conn)
            self.assertFalse(any(c["ready"] for c in lessons.clusters(self.conn)))               # van MIN_EVENTS / MIN_PROJECTS giữ nguyên


if __name__ == "__main__":
    unittest.main()
