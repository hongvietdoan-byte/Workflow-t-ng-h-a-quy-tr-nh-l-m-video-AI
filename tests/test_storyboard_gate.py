"""W1 storyboard checkpoint: the run waits before any video credit, flags what the person should look at first (a wrong character,
framing that is plainly off, a multi-shot group whose first picture lacks people of the later shots), and comes back when a picture
changes after the approval."""
import json
import unittest

from core import autopilot, storyboard_gate
from core.db import connect
from core.pipeline import Pipeline

GOOD = {"character": .9, "hands_face": .9, "composition": .9, "mood_lighting": .9, "consistency": .9, "scale": .9, "grounding": .9,
        "set_match": .9}


class StoryboardGateTest(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", operating_mode="auto", threshold=0.5)

    def shot(self, idx, cast, **extra):
        sid = self.p.create_scene(self.pid, idx)
        data = {"shot_no": idx, "characters": cast, "duration_s": 4, "story_scene": 1, "sequence": "A", **extra}
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
        self.p.conn.commit()
        return sid

    def picture(self, sid, scores):
        jid = self.p.create_job(sid, "image_gen")
        self.p.start(jid), self.p.succeed(jid)
        self.p.apply_qc(jid, scores)
        if self.p.state(jid).value != "approved":
            self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
            self.p.conn.commit()
        return jid

    def test_flags_a_wrong_character_and_framing_that_is_plainly_off(self):
        a, b, c = self.shot(1, ["Kelly"]), self.shot(2, ["Kenta"]), self.shot(3, ["Maxim"])
        self.picture(a, GOOD)
        self.picture(b, dict(GOOD, character=.3))
        self.picture(c, dict(GOOD, composition=.4, set_match=.5))
        f = storyboard_gate.flags(self.p, self.pid)
        self.assertEqual(f[a], [])
        self.assertIn("nhân vật 0.30 dưới mức sàn", f[b])
        self.assertIn("bố cục/cỡ cảnh 0.40", f[c])
        self.assertIn("khớp bối cảnh 0.50", f[c])
        self.assertEqual(storyboard_gate.summary(self.p, self.pid), "2/3 shot có cờ cần xem")

    def test_a_multishot_group_whose_first_picture_lacks_a_later_shots_people_is_flagged(self):
        self.p.set_project_field(self.pid, "shot_mode", "multishot")
        lead, later = self.shot(1, ["Maxim"]), self.shot(2, ["Kenta", "Kelly"])
        self.picture(lead, GOOD)
        self.assertEqual(storyboard_gate.flags(self.p, self.pid)[later], ["ảnh đầu nhóm không có Kenta, Kelly"])
        self.assertEqual(storyboard_gate.fingerprint(self.p, self.pid), [self.p.conn.execute(
            "SELECT id FROM jobs WHERE scene_id=? AND state='approved'", (lead,)).fetchone()["id"]])   # one picture for the group

    def test_the_checkpoint_waits_and_comes_back_when_a_picture_changes(self):
        sid = self.shot(1, ["Kelly"])
        first = self.picture(sid, GOOD)
        with self.assertRaises(autopilot._Wait) as cm:
            autopilot._storyboard_phase(self.p, self.pid, None)
        self.assertEqual(cm.exception.gate, "storyboard")
        autopilot.set_gates(self.p, self.pid, {"waiting_for": "storyboard"})
        autopilot.resume(self.p, self.pid)
        self.assertIsNone(autopilot._storyboard_phase(self.p, self.pid, None))      # approved: the run goes on to video
        self.p.reopen_approved(first, "Đồng bộ cả bộ: redraw")                    # a later change to a picture ...
        self.picture(sid, GOOD)
        with self.assertRaises(autopilot._Wait):                                   # ... brings the checkpoint back
            autopilot._storyboard_phase(self.p, self.pid, None)

    def test_switched_off_it_never_waits(self):
        self.picture(self.shot(1, ["Kelly"]), GOOD)
        autopilot.set_gates(self.p, self.pid, {"storyboard": False})
        self.assertIsNone(autopilot._storyboard_phase(self.p, self.pid, None))

    def test_on_by_default(self):
        self.assertTrue(autopilot.get_gates(self.p, self.pid)["storyboard"])


if __name__ == "__main__":
    unittest.main()


class StoryboardPanelTest(unittest.TestCase):
    """Step 2 shows the waiting checkpoint, the flags and the approve button; the button resumes the run."""

    def test_panel_flags_and_approve_button(self):
        import os
        import tempfile
        from unittest import mock
        from streamlit.testing.v1 import AppTest
        tmp = tempfile.mkdtemp()
        db = os.path.join(tmp, "m.sqlite")
        env = {"PIPELINE_DB": db, "PIPELINE_DATA": os.path.join(tmp, "projects"), "KNOWLEDGE_USER_DIR": os.path.join(tmp, "k")}
        with mock.patch.dict(os.environ, env):
            p = Pipeline(connect(db))
            pid = p.create_project("Board", operating_mode="auto", threshold=0.5)
            sid = p.create_scene(pid, 1, "S1")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "characters": ["Kelly"], "duration_s": 4}), sid))
            jid = p.create_job(sid, "image_gen")
            p.start(jid), p.succeed(jid)
            p.apply_qc(jid, dict(GOOD, character=.3))
            p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
            folder = os.path.join(tmp, "projects", str(pid), "images")
            os.makedirs(folder)
            from PIL import Image
            Image.new("RGB", (90, 160), (90, 90, 90)).save(os.path.join(folder, f"job_{jid}.png"))
            p.conn.commit()
            autopilot.set_gates(p, pid, {"waiting_for": "storyboard"})
            p.conn.execute("UPDATE projects SET autopilot_state='waiting' WHERE id=?", (pid,))
            p.conn.commit()
            app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
            at = AppTest.from_file(app, default_timeout=30).run()
            step2 = next(o for o in at.radio(key="step").options if "2" in o)
            at.radio(key="step").set_value(step2).run()
            self.assertFalse(at.exception)
            text = " ".join(m.value for m in at.markdown)
            self.assertIn("nhân vật 0.30 dưới mức sàn", text)
            with mock.patch("dashboard.steps.step2.autopilot_manager") as mgr:
                at.button(key=f"board_ok_{pid}").click().run()
            self.assertFalse(at.exception)
            mgr.return_value.start.assert_called_once_with(pid)                # the background run is started again
            gates = autopilot.get_gates(Pipeline(connect(db)), pid)
            self.assertIsNone(gates["waiting_for"])
            self.assertEqual(gates["storyboard_ok"], [jid])
