"""S2 (kế hoạch sau #8): timeline by sound first — voices right after the Director, shots sized to the real voice, the total checked
against the script's target, the timeline locked before any picture (lỗi 1.2: #8 planned 58 s, came out 83 s)."""
import json
import unittest
from unittest import mock

from core import audio_first, audio_lib, autopilot, voice
from core.music import MockAudioProvider
from tests.test_v2 import Base


class AudioFirstTests(Base):
    def voiced(self):
        for name in ("KENTA", "KELLY", "MAXIM"):
            voice.set_profile(self.p.conn, self.pid, name, {"voice_id": 1, "voice_name": "Mock"})
        audio = MockAudioProvider()
        voice.generate(self.p.conn, self.pid, audio, self.data)
        audio_lib.refresh(audio, audio_lib.assets_dir(self.data, self.pid))
        return audio

    def script(self, text):
        self.p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (text, self.pid))
        self.p.conn.commit()

    def set_len(self, seconds):
        for r in self.p.conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (self.pid,)).fetchall():
            d = json.loads(r["data"] or "{}")
            d["duration_s"] = seconds
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), r["id"]))
        self.p.conn.commit()

    def test_a_shot_shorter_than_its_voice_is_lengthened_and_a_longer_one_kept(self):
        self.voiced()
        self.set_len(0.5)
        changes = audio_first.fit_shots(self.p.conn, self.pid, self.data)
        self.assertTrue(changes)
        for c in changes:
            data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (c["scene_id"],)).fetchone()["data"])
            self.assertGreater(data["duration_s"], 0.5)
            self.assertEqual(data["duration_from_voice"]["was"], 0.5)
        self.set_len(60)                                                       # a held shot longer than its line keeps its length
        self.assertEqual(audio_first.fit_shots(self.p.conn, self.pid, self.data), [])

    def test_the_length_gate_measures_against_the_script_target(self):
        self.script("THỜI LƯỢNG: 20–25 GIÂY\n...")
        n = self.p.conn.execute("SELECT COUNT(*) c FROM scenes WHERE project_id=?", (self.pid,)).fetchone()["c"]
        self.set_len(22 / n)
        self.assertTrue(audio_first.length_check(self.p.conn, self.pid)["ok"])
        self.set_len(33 / n)                                                   # 32 % over 25 s
        check = audio_first.length_check(self.p.conn, self.pid)
        self.assertFalse(check["ok"])
        self.assertAlmostEqual(check["off"], 0.32, delta=0.02)
        self.assertIn("dài hơn mục tiêu 20–25 s", audio_first.gate_message(check))
        self.script("không ghi thời lượng")
        self.assertTrue(audio_first.length_check(self.p.conn, self.pid)["ok"])   # no target: nothing to hold

    def test_the_run_voices_first_asks_when_the_length_is_off_then_locks(self):
        audio = self.voiced()
        self.script("THỜI LƯỢNG: 5 GIÂY")
        self.set_len(10)
        ctx = autopilot.Context(self.data, None, None, None, audio, None)
        with mock.patch.dict("os.environ", {"FEATURE_AUDIO_FIRST": "1"}):
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._voice_first_phase(self.p, self.pid, ctx)
            self.assertEqual(w.exception.gate, "length")
            autopilot.set_gates(self.p, self.pid, {"waiting_for": "length"})
            autopilot.resume(self.p, self.pid)                              # the person accepts the voiced length
            self.assertIsNone(autopilot._voice_first_phase(self.p, self.pid, ctx))
        locked = autopilot.get_gates(self.p, self.pid)["timeline_locked"]
        self.assertEqual(locked["by"], "voice")
        self.assertEqual(locked["total"], audio_first.planned_total(self.p.conn, self.pid))

    def test_a_speaker_without_a_voice_stops_the_run_before_any_picture(self):
        ctx = autopilot.Context(self.data, None, None, None, MockAudioProvider(), None)
        with mock.patch.dict("os.environ", {"FEATURE_AUDIO_FIRST": "1"}):
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._voice_first_phase(self.p, self.pid, ctx)
        self.assertEqual(w.exception.gate, "voices")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE type='image_gen'").fetchone()["c"], 0)

    def test_the_feature_off_changes_nothing(self):
        ctx = autopilot.Context(self.data, None, None, None, MockAudioProvider(), None)
        self.assertIsNone(autopilot._voice_first_phase(self.p, self.pid, ctx))
        self.assertFalse(autopilot.get_gates(self.p, self.pid).get("timeline_locked"))


if __name__ == "__main__":
    unittest.main()
