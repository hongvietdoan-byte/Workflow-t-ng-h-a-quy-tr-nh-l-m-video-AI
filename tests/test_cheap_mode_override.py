"""08/10 Khủng Long Đỏ #22: in the project's cheap test mode (`test_quality`) a model the person chose for ONE scene (`motion_prompts.video_model`)
must stay as chosen. Before the fix the cheap mode turned 'seedance-2.5' / 'seedance' into 'seedance-fast' even for that explicit choice, so
clips really made with 2.5 were shown as "đã cũ" and the project looked unfinished. A scene without a choice still gets the cheap Fast model."""
import unittest

from core import model_router
from core.db import connect
from core.pipeline import Pipeline


class CheapModeKeepsTheScenesOwnModelTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("cheap")
        self.sid = self.p.create_scene(self.pid, 1, "S1")
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?, 'x', 5, 'approved')", (self.sid,))
        self.p.conn.commit()

    def choose(self, model, cheap):
        self.p.conn.execute("UPDATE motion_prompts SET video_model=? WHERE scene_id=?", (model, self.sid))
        self.p.conn.execute("UPDATE projects SET test_quality=? WHERE id=?", (1 if cheap else 0, self.pid))
        self.p.conn.commit()
        return model_router.scene_choice(self.p.conn, self.sid)

    def test_explicit_choice_survives_cheap_mode(self):
        for model in ("seedance-2.5", "seedance"):
            got = self.choose(model, cheap=True)
            self.assertEqual(got["model"], model)
            self.assertEqual(got["source"], "override")

    def test_cheap_mode_still_turns_an_automatic_pick_into_fast(self):
        self.p.conn.execute("UPDATE projects SET model_priority='quality' WHERE id=?", (self.pid,)) if "model_priority" in [
            r[1] for r in self.p.conn.execute("PRAGMA table_info(projects)")] else None
        got = self.choose(None, cheap=True)
        self.assertNotIn(got["model"], ("seedance", "seedance-2.5"))


if __name__ == "__main__":
    unittest.main()
