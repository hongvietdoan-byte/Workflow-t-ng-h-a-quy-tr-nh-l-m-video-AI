"""Tab Kịch bản — 'BỐ CỤC DASHBOARD GỌN' (người dùng 07/10, Khủng Long Đỏ):
  (1) danh sách > 6 cảnh nằm trong khung cuộn 460 px → trình sửa mở bên trong, nút 💾 Lưu cảnh bị khuất: khi đang sửa thì bỏ khung cuộn;
  (2) Lưu cảnh xong mục shot tự đóng (nhãn đổi theo thời lượng / trạng thái) → mục giữ mở theo công tắc ✏;
  (3) đổi 1 ô cho 6 shot ~30 thao tác → 'Sửa hàng loạt': chọn nhiều shot, đặt cùng giá trị (đường gen, chuyển cảnh, rung, nối clip)."""
import json
import os
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import llm_io
from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline
from dashboard.steps import step1
from tests.test_llm_io_preflight import ANALYSIS

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class BulkCoreTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("bulk")
        for i in (1, 2, 3):
            self.p.create_scene(self.pid, i, f"CẢNH {i}")

    def data(self, idx):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()["data"] or "{}")

    def test_sets_the_same_values_on_the_chosen_scenes_only(self):
        out = llm_io.update_scenes_bulk(self.p, self.pid, [1, 3], {"transition_in": "flash", "shake_in": True, "video_route": "single"})
        self.assertEqual(sorted(out), [1, 3])
        for i in (1, 3):
            d = self.data(i)
            self.assertEqual((d["transition_in"], d["shake_in"], d["video_route"]), ("flash", True, "single"))
            self.assertIn("transition_in", d["_user_locked"])                 # kept when the Director runs again, like a hand edit
        self.assertNotIn("transition_in", self.data(2))

    def test_only_the_bulk_fields_are_accepted(self):
        with self.assertRaises(ValueError):
            llm_io.update_scenes_bulk(self.p, self.pid, [1], {"image_prompt": "x"})
        with self.assertRaises(ValueError):
            llm_io.update_scenes_bulk(self.p, self.pid, [1], {"transition_in": "khong-co"})
        with self.assertRaises(ValueError):
            llm_io.update_scenes_bulk(self.p, self.pid, [], {"shake_in": True})


class LayoutTests(unittest.TestCase):
    def test_scroll_box_only_when_nobody_is_editing(self):
        self.assertEqual(step1.rows_box_height(8, editing=False), 460)
        self.assertIsNone(step1.rows_box_height(8, editing=True))           # the open editor and its 💾 button stay on the page
        self.assertIsNone(step1.rows_box_height(5, editing=False))


class ScreenTests(unittest.TestCase):
    def setUp(self):
        os.environ["DASHBOARD_EXPERT"] = "1"
        self.addCleanup(os.environ.pop, "DASHBOARD_EXPERT", None)
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        for k, v in (("PIPELINE_DB", self.db), ("PIPELINE_DATA", os.path.join(self.tmp, "projects")),
                     ("KNOWLEDGE_USER_DIR", os.path.join(self.tmp, "knowledge_user"))):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        p = Pipeline(connect(self.db))
        self.pid = p.create_project("Demo")
        p.create_scene(self.pid, 1, "CẢNH 1")
        store_scene_analysis(p, self.pid, ANALYSIS)

    def open(self):
        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state[f"fold_script_{self.pid}"] = True
        return at.run()

    def test_saving_keeps_the_scene_open(self):
        at = self.open()
        at.toggle(key=f"sd_open_{self.pid}_1").set_value(True).run()
        at.text_area(key=f"sd_{self.pid}_1_prompt").set_value("dark forest").run()
        next(b for b in at.button if b.key == f"sds_{self.pid}_1").click().run()
        self.assertFalse(at.exception)
        s01 = next(e for e in at.expander if e.label.startswith("S01"))
        self.assertTrue(s01.proto.expanded)
        self.assertTrue(any(b.key == f"sds_{self.pid}_1" for b in at.button))   # the editor is still there, no reopen needed


if __name__ == "__main__":
    unittest.main()


class MotionBoxTests(ScreenTests):
    def test_motion_prompt_is_edited_next_to_the_shot(self):
        p = Pipeline(connect(self.db))
        sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()["id"]
        p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, camera, duration_sec, negative_prompt, state)"
                       " VALUES (?, 'slow push in', 'push', 5, 'blur', 'approved')", (sid,))
        p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,'image_gen','approved',"
                       "'2026-10-07T00:00:00Z','2026-10-07T00:00:00Z')", (self.pid, sid))      # a motion prompt exists only after the picture
        p.conn.commit()
        at = self.open()
        at.toggle(key=f"sd_open_{self.pid}_1").set_value(True).run()
        at.text_area(key=f"sd_{self.pid}_1_motion").set_value("hero turns, camera orbits left").run()
        next(b for b in at.button if b.key == f"sd_{self.pid}_1_mps").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([e.value for e in at.error], [])
        row = Pipeline(connect(self.db)).conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        self.assertEqual((row["motion_prompt"], row["camera"], row["negative_prompt"]), ("hero turns, camera orbits left", "push", "blur"))
