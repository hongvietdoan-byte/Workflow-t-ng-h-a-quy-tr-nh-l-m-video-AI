"""13/10 (tồn THẤP phiên rà PR #10): lưu cảnh Bước 1 gửi mọi ô — ô 'blocking' / 'emotional_intent' để trống ("") trên cảnh chưa
từng có trường đó bị coi là "người sửa tay" và vào `_user_locked` → lần Đạo diễn chạy lại không điền được. Ô trống = chưa có."""
import json
import unittest

from core import llm_io
from core.db import connect
from core.pipeline import Pipeline


class BlankFieldNotLockedTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("p")
        sid = self.p.create_scene(self.pid, 1, "shot 1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "image_prompt": "x"}), sid))
        self.p.conn.commit()

    def data(self):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()[0])

    def test_blank_boxes_on_missing_fields_are_not_locked(self):
        changed = llm_io.update_scene(self.p, self.pid, 1, {"image_prompt": "x", "blocking": "", "emotional_intent": "  "})
        self.assertEqual(changed, [])
        self.assertNotIn("blocking", self.data().get("_user_locked") or [])
        self.assertNotIn("emotional_intent", self.data().get("_user_locked") or [])

    def test_real_edit_is_still_locked(self):
        changed = llm_io.update_scene(self.p, self.pid, 1, {"blocking": "Kelly left, Kenta right", "emotional_intent": ""})
        self.assertEqual(changed, ["blocking"])
        self.assertEqual(self.data()["_user_locked"], ["blocking"])

    def test_clearing_a_filled_field_is_an_edit(self):
        llm_io.update_scene(self.p, self.pid, 1, {"blocking": "Kelly left"})
        changed = llm_io.update_scene(self.p, self.pid, 1, {"blocking": ""})
        self.assertEqual(changed, ["blocking"])


if __name__ == "__main__":
    unittest.main()
