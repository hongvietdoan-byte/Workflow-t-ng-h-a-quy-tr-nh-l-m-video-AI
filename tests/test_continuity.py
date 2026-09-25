"""V5 / V6 (dp.md Q9, director.md Đ3): the 180° line and screen direction read from the DP's start-frame words, motifs that never come
back; V2: a hand edit of a shot keeps the Director's voice direction and can set the acting and the DP's reason."""
import json
import unittest

from core import continuity, llm_io


def shot(start, chars=("KELLY", "KENTA"), **kw):
    return dict({"start_frame": start, "characters": list(chars), "angle": "eye", "camera_move": "static"}, **kw)


class AxisTests(unittest.TestCase):
    def test_two_people_swapping_sides_is_flagged(self):
        plan = [(1, 1, shot("Kelly frame-left, Kenta frame-right, facing each other")),
                (1, 2, shot("Kenta on the left, Kelly on the right"))]
        w = continuity.axis_warnings(plan)
        self.assertEqual(len(w), 1)
        self.assertIn("đổi bên so với shot 1·1", w[0])

    def test_a_crossing_on_purpose_an_ots_an_orbit_or_another_scene_is_not(self):
        base = (1, 1, shot("Kelly frame-left, Kenta frame-right"))
        swapped = "Kenta frame-left, Kelly frame-right"
        for other in ((1, 2, shot(swapped, why="máy vượt trục có chủ đích")), (1, 2, shot(swapped, angle="ots")),
                      (1, 2, shot(swapped, camera_move="orbit")), (2, 1, shot(swapped))):
            self.assertEqual(continuity.axis_warnings([base, other]), [], other)

    def test_running_direction_flips_are_flagged(self):
        plan = [(3, 1, shot("Kelly runs from left to right", chars=("KELLY",))),
                (3, 2, shot("Kelly sprints toward frame-left", chars=("KELLY",)))]
        self.assertIn("đổi hướng chạy", continuity.axis_warnings(plan)[0])

    def test_a_motif_must_come_back(self):
        plan = [(1, 1, shot("x", motif="qua vai Kenta")), (6, 2, shot("x", motif="Qua vai Kenta")), (2, 1, shot("x", motif="vòng cổ"))]
        w = continuity.motif_warnings(plan)
        self.assertEqual(len(w), 1)
        self.assertIn("vòng cổ", w[0])


class HandEditTests(unittest.TestCase):
    def setUp(self):
        from core.db import connect
        from core.pipeline import Pipeline
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("edit")
        sid = self.p.create_scene(self.pid, 1, "s1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "image_prompt": "x", "dialogue": [
            {"speaker": "KELLY", "text": "Em hiểu rồi…", "delivery": {"pace": "slow", "emotion": "resigned"}}]}, ensure_ascii=False), sid))
        self.p.conn.commit()
        self.sid = sid

    def data(self):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"])

    def test_editing_the_lines_keeps_the_voice_direction(self):
        llm_io.update_scene(self.p, self.pid, 1, {"dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi…"}]})
        self.assertEqual(self.data()["dialogue"][0]["delivery"], {"pace": "slow", "emotion": "resigned"})
        llm_io.update_scene(self.p, self.pid, 1, {"dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi…",
                                                                "delivery": {"pace": "fast", "intensity": 4}}]})
        self.assertEqual(self.data()["dialogue"][0]["delivery"], {"pace": "fast", "intensity": 4})

    def test_the_acting_and_the_reason_can_be_set_and_cleared_by_hand(self):
        changed = llm_io.update_scene(self.p, self.pid, 1, {"performance": {"intensity": 3, "face": "tight smile"}, "why": "qua vai"})
        self.assertEqual(self.data()["performance"], {"intensity": 3, "face": "tight smile"})
        self.assertIn("performance", changed)
        self.assertIn("performance", self.data()["_user_locked"])                 # a Director run keeps the hand edit
        llm_io.update_scene(self.p, self.pid, 1, {"performance": {}, "why": ""})
        self.assertNotIn("performance", self.data())
        self.assertNotIn("why", self.data())



class TopViewTests(unittest.TestCase):
    def test_the_floor_plan_marks_cameras_on_opposite_sides(self):
        import os
        import tempfile
        from unittest import mock
        from core import location_pack
        entry = {"spots": {"plaza": {"at": [0, 0, 0]}, "far": {"at": [500, 500, 0]}}, "default_spot": "plaza"}
        def item(idx, cam):
            return {"idx": idx, "entry": entry, "camera": {"location": cam, "lens": 35, "subject": {"location": [0, 0, 0]}}}
        items = [item(1, [0, 3, 1.6]), item(2, [0.5, 3.5, 1.6]), item(3, [0, -3, 1.6])]
        out = os.path.join(tempfile.mkdtemp(), "top.png")
        with mock.patch.object(location_pack, "plan", return_value=items):
            res = location_pack.top_view(None, 1, out)
        self.assertTrue(os.path.exists(out))
        self.assertEqual(sorted(res["opposite"]), [(1, 3), (2, 3)])


if __name__ == "__main__":
    unittest.main()
