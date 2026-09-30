"""S0.14 T4 (core/hero_takes): a ⭐ shot gets a second take, the layer-0 numbers pick one, a tie waits for the person."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import hero_takes
from core.db import connect
from core.pipeline import Pipeline


class HeroTakesTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("T4")
        self.tmp = tempfile.mkdtemp()
        self.sid = self.p.create_scene(self.pid, 1, "S1")
        self.other = self.p.create_scene(self.pid, 2, "S2")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_role": "hero"}), self.sid))
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_role": "normal"}), self.other))
        self.p.conn.commit()
        self.dest = os.path.join(self.tmp, "01.mp4")
        env = mock.patch.dict(os.environ, {"FEATURE_HERO_TAKES": "1"})
        env.start()
        self.addCleanup(env.stop)

    def _clip(self, scene_id, body: bytes, state="pending_review"):
        jid = self.p.create_job(scene_id, "video_gen")
        with open(self.dest, "wb") as f:
            f.write(body)
        self.p.conn.execute("UPDATE jobs SET state=?, result_path=?, external_id='x' WHERE id=?", (state, self.dest, jid))
        self.p.conn.commit()
        return jid

    def _step(self, flags=None, block=None):
        flags = flags or {}

        def measure(path, sid, d):
            with open(path, "rb") as f:
                return {"flags": ["x"] * flags.get(f.read(), 0)}
        return hero_takes.step(self.p, self.pid, self.tmp, lambda sid: block, measure=measure)

    def _second(self):
        return hero_takes.load(self.p.conn, self.pid)[str(self.sid)]["second"]

    def test_off_does_nothing(self):
        self._clip(self.sid, b"A")
        with mock.patch.dict(os.environ, {"FEATURE_HERO_TAKES": "0"}):
            self.assertEqual(self._step(), [])
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)

    def test_second_take_created_and_first_held(self):
        first = self._clip(self.sid, b"A")
        self._clip(self.other, b"N")                       # a normal shot never gets a second take
        lines = self._step()
        self.assertTrue(any("bản thứ 2" in x for x in lines))
        second = self._second()
        self.assertEqual(self.p.job(second)["state"], "queued")
        self.assertEqual(hero_takes.hold_reason(self.p.conn, self.p.job(first)), hero_takes.HOLD_WAIT)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "01_t4a.mp4")))
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE scene_id=?", (self.other,)).fetchone()[0], 1)

    def _finish_second(self, body: bytes):
        second = self._second()
        with open(self.dest, "wb") as f:                   # the runner downloads take 2 over NN.mp4
            f.write(body)
        self.p.conn.execute("UPDATE jobs SET state='pending_review', result_path=?, external_id='y' WHERE id=?", (self.dest, second))
        self.p.conn.commit()
        return second

    def test_first_wins_is_restored_as_the_shot_clip(self):
        first = self._clip(self.sid, b"A")
        self._step()
        second = self._finish_second(b"B")
        self._step(flags={b"A": 0, b"B": 2})
        self.assertEqual(self.p.job(second)["state"], "rejected")
        self.assertEqual(self.p.job(first)["result_path"], self.dest)
        with open(self.dest, "rb") as f:
            self.assertEqual(f.read(), b"A")
        self.assertIsNone(hero_takes.hold_reason(self.p.conn, self.p.job(first)))

    def test_second_wins(self):
        first = self._clip(self.sid, b"A")
        self._step()
        second = self._finish_second(b"B")
        self._step(flags={b"A": 1, b"B": 0})
        self.assertEqual(self.p.job(first)["state"], "rejected")
        with open(self.p.job(second)["result_path"], "rb") as f:
            self.assertEqual(f.read(), b"B")

    def test_tie_waits_for_the_person_then_drops_the_other(self):
        first = self._clip(self.sid, b"A")
        self._step()
        second = self._finish_second(b"B")
        self._step()
        self.assertEqual(hero_takes.hold_reason(self.p.conn, self.p.job(first)), hero_takes.HOLD_TIE)
        self.p.approve(first, "user", "chọn bản 1")
        self._step()
        self.assertEqual(self.p.job(second)["state"], "rejected")
        with open(self.dest, "rb") as f:
            self.assertEqual(f.read(), b"A")

    def test_blocked_by_cap_is_said(self):
        self._clip(self.sid, b"A")
        lines = self._step(block="shot đã gửi 3 lần")
        self.assertTrue(any("shot đã gửi 3 lần" in x for x in lines))
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)

    def test_pick(self):
        self.assertEqual(hero_takes.pick({"flags": []}, {"flags": ["a"]}), "first")
        self.assertIsNone(hero_takes.pick({"flags": []}, {"flags": []}))
        self.assertIsNone(hero_takes.pick(None, {"flags": []}))


if __name__ == "__main__":
    unittest.main()
