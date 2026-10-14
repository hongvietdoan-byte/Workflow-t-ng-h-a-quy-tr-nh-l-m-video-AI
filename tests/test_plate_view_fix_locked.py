"""Thử D6 14/10: diag `plate_view_fix` báo 'đổi' cả với shot người dùng đã KHÓA TAY hướng nền (CSDL giữ giá trị người khóa).
Shot khóa → không sửa, không báo 'đổi'; hình học vẫn sai → VÀNG 'giữ theo người'. Diag khớp CSDL sau khi lưu. 0 USD."""
import json
import unittest

from core import llm_io
from core.db import connect
from core.pipeline import Pipeline

FACE_ON = {"angle": "eye-level reverse, facing camera", "blocking": "Kelly facing camera", "plate_spot": "plaza_front"}


class LockedPlateViewFixTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")

    def _row(self, data):
        self.p.conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?,?,?,?)",
                            (self.pid, 1, "x", json.dumps(data, ensure_ascii=False)))

    def _diags(self):
        return [(r["severity"], r["message"]) for r in
                self.p.conn.execute("SELECT * FROM diag_events WHERE code='plate_view_fix' AND project_id=? ORDER BY id", (self.pid,))]

    def _obj(self, view="landmark"):
        return {"scenes": [{"idx": 1, "shots": [dict(FACE_ON, plate_view=view)]}]}

    def test_unlocked_face_on_landmark_is_changed_and_said(self):
        obj = self._obj()
        llm_io._plate_view_fix(self.p.conn, self.pid, obj)
        self.assertEqual(obj["scenes"][0]["shots"][0]["plate_view"]["background"], "away")
        d = self._diags()
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0][0], "info")
        self.assertIn("đổi", d[0][1])

    def test_hand_locked_landmark_is_kept_and_warned_not_changed(self):
        self._row({"story_scene": 1, "shot_no": 1, "plate_view": "landmark", "_user_locked": ["plate_view"]})
        obj = self._obj()
        llm_io._plate_view_fix(self.p.conn, self.pid, obj)
        self.assertEqual(obj["scenes"][0]["shots"][0]["plate_view"], "landmark")      # what store_plan will keep
        d = self._diags()
        self.assertEqual([lv for lv, _ in d], ["warn"])
        self.assertIn("người đã khóa hướng nền 'landmark'", d[0][1])
        self.assertIn("giữ theo người", d[0][1])
        self.assertNotIn("code đổi", d[0][1])

    def test_hand_locked_away_says_nothing_and_obj_matches_the_lock(self):
        self._row({"story_scene": 1, "shot_no": 1, "plate_view": "away", "_user_locked": ["plate_view"]})
        obj = self._obj("landmark")                                                   # the Director wrote landmark again
        llm_io._plate_view_fix(self.p.conn, self.pid, obj)
        self.assertEqual(obj["scenes"][0]["shots"][0]["plate_view"], "away")
        self.assertEqual(self._diags(), [])

    def test_a_lock_on_another_field_does_not_protect_plate_view(self):
        self._row({"story_scene": 1, "shot_no": 1, "plate_view": "landmark", "size": "CU", "_user_locked": ["size"]})
        obj = self._obj()
        llm_io._plate_view_fix(self.p.conn, self.pid, obj)
        self.assertEqual(obj["scenes"][0]["shots"][0]["plate_view"]["background"], "away")
        self.assertEqual([lv for lv, _ in self._diags()], ["info"])


if __name__ == "__main__":
    unittest.main()
