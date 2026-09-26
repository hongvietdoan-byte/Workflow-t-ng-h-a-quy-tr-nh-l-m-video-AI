"""Tests that were missing: budget.check_audio (the count cap for audio, which has no price) and the autopilot phase
`_plate_fallback_phase` (a clip that redrew the 3D place is made again ONCE on green screen)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import autopilot, budget, cost, location_pack, regen
from core.db import connect
from core.pipeline import Pipeline


class CheckAudioTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("Âm thanh")

    def audio(self, provider="clipai", n=1):
        for _ in range(n):
            cost.record_usage(self.p.conn, None, "audio", provider, "tts-vi", "default", 1, "call", self.pid)

    def test_off_until_a_test_round_starts(self):
        self.audio(n=5)
        self.assertIsNone(budget.check_audio(self.p.conn, "clipai"))

    def test_the_simulator_is_never_capped(self):
        budget.restart(self.p.conn)
        budget.save(self.p.conn, audio_cap=0)
        self.assertIsNone(budget.check_audio(self.p.conn, "mock"))
        self.assertIsNone(budget.check_audio(self.p.conn, "mock-audio"))

    def test_the_count_cap_stops_the_next_audio(self):
        budget.restart(self.p.conn)
        budget.save(self.p.conn, audio_cap=2)
        self.audio(n=1)
        self.assertIsNone(budget.check_audio(self.p.conn, "clipai"))           # 1 made, the 2nd still fits
        self.audio(n=1)
        note = budget.check_audio(self.p.conn, "clipai")
        self.assertIn("2 âm thanh", note)
        self.assertIn("trần 2", note)
        self.audio(provider="mock", n=3)                                        # simulated audio never counts
        self.assertIn("2 âm thanh", budget.check_audio(self.p.conn, "clipai"))
        budget.stop(self.p.conn)
        self.assertIsNone(budget.check_audio(self.p.conn, "clipai"))

    def test_only_audio_since_the_round_started_counts(self):
        self.audio(n=3)
        budget.restart(self.p.conn)
        budget.save(self.p.conn, audio_cap=2, since="2999-01-01 00:00:00")     # a round that starts after every recorded audio
        self.assertIsNone(budget.check_audio(self.p.conn, "clipai"))


class PlateFallbackPhaseTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("Nền 3D")
        self.sid = self.p.create_scene(self.pid, 1, "CẢNH 1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"text": "x", "plate_mode": "first_frame"}), self.sid))
        self.p.conn.commit()
        self.job = self.p.create_job(self.sid, "video_gen")
        self.p.start(self.job)
        self.p.succeed(self.job)
        self.ctx = autopilot.Context(self.data, None, None, None)
        os.environ["FEATURE_LOCATION_PLATES"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_LOCATION_PLATES", None)

    def qc(self, ok=False, mode="first_frame", fallback=False):
        location_pack.record_video_qc(self.data, self.pid, self.sid, self.job, {"score": 0.31, "ok": ok, "fallback": fallback}, mode)

    def plate_mode(self):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"]).get("plate_mode")

    def test_feature_off_does_nothing(self):
        os.environ["FEATURE_LOCATION_PLATES"] = "0"
        self.qc()
        with mock.patch.object(regen, "regenerate_video") as again:
            self.assertIsNone(autopilot._plate_fallback_phase(self.p, self.pid, self.ctx))
        again.assert_not_called()
        self.assertEqual(self.plate_mode(), "first_frame")

    def test_a_clip_that_kept_the_place_is_left_alone(self):
        for kwargs in ({"ok": True}, {"mode": "green"}, {"fallback": True}):
            self.qc(**kwargs)
            with mock.patch.object(regen, "regenerate_video") as again:
                self.assertIsNone(autopilot._plate_fallback_phase(self.p, self.pid, self.ctx))
            again.assert_not_called()

    def test_a_redrawn_place_is_made_again_once_on_green(self):
        self.qc()
        with mock.patch.object(regen, "regenerate_video", return_value=999) as again:
            msg = autopilot._plate_fallback_phase(self.p, self.pid, self.ctx)
            self.assertIn("cách 2", msg)
            self.assertIsNone(autopilot._plate_fallback_phase(self.p, self.pid, self.ctx))     # never twice for one shot
        again.assert_called_once()
        self.assertEqual(again.call_args[0][2], self.job)
        self.assertIn("phông xanh", again.call_args[0][3])
        self.assertEqual(self.plate_mode(), "green")                                           # the input changed
        self.assertTrue(location_pack.video_qc(self.data, self.pid)[str(self.sid)]["fallback"])

    def test_a_failed_regeneration_is_reported_and_not_retried(self):
        self.qc()
        with mock.patch.object(regen, "regenerate_video", side_effect=RuntimeError("hết lượt")) as again:
            self.assertIsNone(autopilot._plate_fallback_phase(self.p, self.pid, self.ctx))
            self.assertIsNone(autopilot._plate_fallback_phase(self.p, self.pid, self.ctx))
        again.assert_called_once()
        row = self.p.conn.execute("SELECT message FROM diag_events WHERE code='plate_fallback'").fetchone()
        self.assertIn("hết lượt", row["message"])

    def test_a_clip_that_is_not_usable_is_skipped(self):
        self.p.conn.execute("UPDATE jobs SET state='failed' WHERE id=?", (self.job,))
        self.p.conn.commit()
        self.qc()
        with mock.patch.object(regen, "regenerate_video") as again:
            self.assertIsNone(autopilot._plate_fallback_phase(self.p, self.pid, self.ctx))
        again.assert_not_called()
        self.assertEqual(self.plate_mode(), "first_frame")


if __name__ == "__main__":
    unittest.main()
