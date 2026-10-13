"""13/10 #27 shot 16: khung cuối (core.end_frames.prompt_for) đọc data['end_state'] nhưng update_scene không nhận trường này — câu
'Kelly ló mắt qua mép tường' cũ thắng mọi câu sửa. Sửa tay end_state phải ghi được và được khóa (🔒) như các trường khác."""
import json
import unittest

from core import llm_io
from core.db import connect
from core.pipeline import Pipeline


class UpdateSceneEndStateTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("p27")
        sid = self.p.create_scene(self.pid, 16, "shot 16")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(
            {"shot_no": 16, "image_prompt": "x", "end_state": "Kelly peeking over the wall"}), sid))
        self.p.conn.commit()

    def data(self):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=16", (self.pid,)).fetchone()[0])

    def test_end_state_is_editable_and_locked(self):
        changed = llm_io.update_scene(self.p, self.pid, 16, {"end_state": "Kelly fully hidden behind a wall taller than her"})
        self.assertEqual(changed, ["end_state"])
        self.assertEqual(self.data()["end_state"], "Kelly fully hidden behind a wall taller than her")
        self.assertIn("end_state", self.data()["_user_locked"])

    def test_end_state_must_be_text(self):
        with self.assertRaises(llm_io.SchemaError):
            llm_io.update_scene(self.p, self.pid, 16, {"end_state": 3})

    def test_none_end_state_is_empty_text_not_an_error(self):
        llm_io.update_scene(self.p, self.pid, 16, {"end_state": None})   # insert_scene_after passes None (rà quy ước 7)
        self.assertEqual(self.data()["end_state"], "")

    def test_end_frame_drawn_for_the_old_end_state_is_not_used(self):
        from core import end_frames
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=16", (self.pid,)).fetchone()[0]
        row = {"scene_id": sid, "prompt": "at the end of the action: Kelly peeking over the wall. One single frame"}
        self.assertFalse(end_frames.end_state_changed(self.p.conn, row))
        llm_io.update_scene(self.p, self.pid, 16, {"end_state": "Kelly fully hidden"})
        self.assertTrue(end_frames.end_state_changed(self.p.conn, row))
        self.assertFalse(end_frames.end_state_changed(self.p.conn, {"scene_id": sid, "prompt": None}))   # never sent: not judged


if __name__ == "__main__":
    unittest.main()
