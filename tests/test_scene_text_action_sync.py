"""08/10 dự án #24 shot 7: sửa ô 'Nội dung kịch bản của cảnh' rồi 💾 Lưu chỉ đổi scenes.data['text']; data['action'] (dòng tiêu đề
shot, Director / motion prompt đọc) giữ câu cũ → lệch. Lưu ô đó thì 'action' theo cùng."""
import json
import unittest

from core import llm_io
from core.db import connect
from core.pipeline import Pipeline

OLD = "Yêu nữ đứng thẳng, chậm rãi quay đầu nhìn về phía Kelly đang ngồi bệt"
NEW = "Yêu nữ đứng thẳng, tóc rủ che mặt, từ từ ngẩng lên nhìn Kelly"


class SceneTextActionSyncTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("p24")
        sid = self.p.create_scene(self.pid, 7, "CẢNH 1 · shot 7")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(
            {"shot_no": 7, "text": OLD, "action": OLD, "image_prompt": "x"}, ensure_ascii=False), sid))
        self.p.conn.commit()

    def data(self):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()[0])

    def test_saving_the_text_box_moves_the_action_too(self):
        changed = llm_io.update_scene(self.p, self.pid, 7, {"image_prompt": "x"}, text=NEW)
        d = self.data()
        self.assertEqual(d["text"], NEW)
        self.assertEqual(d["action"], NEW)
        self.assertIn("action", changed)                       # hand-edited → kept by a later Director run (🔒)

    def test_an_explicit_action_wins(self):
        llm_io.update_scene(self.p, self.pid, 7, {"image_prompt": "x", "action": "khác"} if "action" in llm_io.SCENE_FIELDS
                            else {"image_prompt": "x"}, text=OLD)
        self.assertEqual(self.data()["action"], OLD if "action" not in llm_io.SCENE_FIELDS else "khác")

    def test_a_v2_scene_without_action_gets_none(self):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=7", (json.dumps({"text": OLD, "image_prompt": "x"}), self.pid))
        self.p.conn.commit()
        llm_io.update_scene(self.p, self.pid, 7, {"image_prompt": "x"}, text=NEW)
        self.assertNotIn("action", self.data())


if __name__ == "__main__":
    unittest.main()
