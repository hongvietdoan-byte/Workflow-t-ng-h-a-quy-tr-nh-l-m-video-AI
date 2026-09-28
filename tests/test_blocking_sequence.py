"""Blocking (where each person stands/faces) and sequences (scenes in one place, continuous action): the Director's schema, the
image prompt, and storyboard chaining inside one sequence instead of simply "the scene before"."""
import json
import os
import shutil
import tempfile
import unittest

from core import llm_io
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner, previous_frame_job


def analysis(scenes):
    return {"characters": [{"name": "Kelly", "description": "d"}, {"name": "Alok", "description": "d"}],
            "scenes": [dict({"location": "beach", "time": "day", "characters": ["Kelly"], "mood": "m", "lighting": "l",
                             "shot": "s", "image_prompt": f"shot {s['idx']}"}, **s) for s in scenes]}


class BlockingSequenceTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("seq")
        self.data_dir = os.path.join(self.dir, "projects")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def scenes(self, specs):
        for s in specs:
            self.p.create_scene(self.pid, s["idx"], f"S{s['idx']}")
        llm_io.store_scene_analysis(self.p, self.pid, analysis(specs))

    def data(self, idx):
        return json.loads(self.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()["data"])

    def approve(self, idx):
        """An approved picture for scene idx, with its file on disk (what storyboard mode chains in)."""
        sid = self.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()["id"]
        jid = self.p.create_job(sid, "image_gen")
        self.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
        self.conn.commit()
        folder = os.path.join(self.data_dir, str(self.pid), "images")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"job_{jid}.png"), "wb") as f:
            f.write(b"png")
        return jid

    def test_the_director_answer_keeps_sequence_and_blocking_and_bad_values_are_refused(self):
        self.scenes([{"idx": 1, "sequence": 1, "blocking": "Kelly frame-left facing right"}])
        self.assertEqual((self.data(1)["sequence"], self.data(1)["blocking"]), (1, "Kelly frame-left facing right"))
        for bad in ({"sequence": "1"}, {"sequence": 0}, {"sequence": True}, {"blocking": 3}):
            with self.assertRaises(llm_io.SchemaError):
                llm_io.validate_scene_analysis(analysis([dict({"idx": 1}, **bad)]))
        llm_io.validate_scene_analysis(analysis([{"idx": 1}]))                        # both stay optional

    def test_a_scene_edit_changes_blocking_and_sequence(self):
        self.scenes([{"idx": 1}])
        llm_io.update_scene(self.p, self.pid, 1, {"blocking": "  Alok center, background  ", "sequence": 2})
        self.assertEqual((self.data(1)["blocking"], self.data(1)["sequence"]), ("Alok center, background", 2))
        llm_io.update_scene(self.p, self.pid, 1, {"sequence": None})
        self.assertIsNone(self.data(1)["sequence"])

    def test_the_blocking_goes_into_the_image_prompt(self):
        self.scenes([{"idx": 1, "blocking": "Kelly frame-left, full body, feet on the ground"}])
        provider = MockImageProvider()
        runner = ImageRunner(self.p, provider, self.data_dir)
        sid = self.conn.execute("SELECT id FROM scenes WHERE project_id=?", (self.pid,)).fetchone()["id"]
        self.p.create_job(sid, "image_gen")
        runner.submit_pending(self.pid)
        self.assertEqual(provider.prompts["img-1"], "shot 1. Blocking: Kelly frame-left, full body, feet on the ground")

    def test_an_action_shot_starts_mid_movement(self):
        """S3.3 (#8: fake running — a standing start frame makes the model 'start up' at every cut)."""
        from core.runner import build_image_prompt
        self.scenes([{"idx": 1}])
        text, _ = build_image_prompt(self.conn, self.pid, {"image_prompt": "Kelly runs across the square",
                                                             "action_peak": "mid-stride, weight on the left foot"})
        self.assertIn("already under way: mid-stride, weight on the left foot", text)
        text, _ = build_image_prompt(self.conn, self.pid, {"image_prompt": "Kelly stands still"})
        self.assertNotIn("under way", text)
        from core import shots
        data = shots.shot_data({"idx": 1, "characters": []}, {"size": "MS", "role": "action", "duration_s": 2, "image_prompt": "x",
                                                                "action": "chạy", "action_peak": " mid-stride "}, 1)
        self.assertEqual(data["action_peak"], "mid-stride")

    def test_a_storyboard_frame_follows_the_same_sequence_not_just_the_scene_before(self):
        self.scenes([{"idx": 1, "sequence": 1}, {"idx": 2, "sequence": 2}, {"idx": 3, "sequence": 1}, {"idx": 4, "sequence": 3}])
        first = self.approve(1)
        self.approve(2)
        self.assertEqual(previous_frame_job(self.conn, self.pid, 3, 1)["id"], first)   # back in place 1: skips scene 2
        self.assertIsNone(previous_frame_job(self.conn, self.pid, 4, 3))                # a new sequence starts fresh

    def test_without_a_sequence_the_scene_right_before_is_used_as_before(self):
        self.scenes([{"idx": 1}, {"idx": 2}, {"idx": 3}])
        self.approve(1)
        second = self.approve(2)
        self.assertEqual(previous_frame_job(self.conn, self.pid, 3, None)["id"], second)
        self.assertIsNone(previous_frame_job(self.conn, self.pid, 1, None))            # the first scene has nothing before it
        self.conn.execute("UPDATE jobs SET state='rejected' WHERE id=?", (second,))
        self.conn.commit()
        self.assertIsNone(previous_frame_job(self.conn, self.pid, 3, None))            # only the scene right before counts

    def test_storyboard_mode_sends_the_frame_of_the_same_sequence(self):
        self.scenes([{"idx": 1, "sequence": 1}, {"idx": 2, "sequence": 2}, {"idx": 3, "sequence": 1}])
        first = self.approve(1)
        self.approve(2)
        self.p.set_storyboard_mode(self.pid, True)
        provider = MockImageProvider()
        runner = ImageRunner(self.p, provider, self.data_dir)
        sid = self.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=3", (self.pid,)).fetchone()["id"]
        self.p.create_job(sid, "image_gen")
        runner.submit_pending(self.pid)
        sent = next(iter(provider.references.values()))
        self.assertEqual([os.path.basename(x) for x in sent], [f"job_{first}.png"])
        self.assertIn("same side of the frame", next(iter(provider.prompts.values())))


if __name__ == "__main__":
    unittest.main()
