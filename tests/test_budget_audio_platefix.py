"""Tests that were missing: budget.check_audio (the count cap for audio, which has no price) and (S14.9) the removed autopilot
phase `_plate_fallback_phase` (green-screen fallback of the flag location_plates) staying gone."""
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

    def test_the_count_cap_warns_on_the_next_audio(self):
        # S14.16 (chính sách tiền 04/10): was "stops the next audio" — the count is a planned amount that warns (warn_audio)
        budget.restart(self.p.conn)
        budget.save(self.p.conn, audio_cap=2)
        self.audio(n=1)
        self.assertIsNone(budget.warn_audio(self.p.conn, "clipai"))            # 1 made, the 2nd still fits
        self.audio(n=1)
        note = budget.warn_audio(self.p.conn, "clipai")
        self.assertIn("2 âm thanh", note)
        self.assertIn("mức dự tính 2", note)
        self.assertIsNone(budget.check_audio(self.p.conn, "clipai"))           # nothing refused
        self.audio(provider="mock", n=3)                                        # simulated audio never counts
        self.assertIn("2 âm thanh", budget.warn_audio(self.p.conn, "clipai"))
        budget.stop(self.p.conn)
        self.assertIsNone(budget.warn_audio(self.p.conn, "clipai"))

    def test_only_audio_since_the_round_started_counts(self):
        self.audio(n=3)
        budget.restart(self.p.conn)
        budget.save(self.p.conn, audio_cap=2, since="2999-01-01 00:00:00")     # a round that starts after every recorded audio
        self.assertIsNone(budget.check_audio(self.p.conn, "clipai"))


class PlateFallbackGoneTests(unittest.TestCase):
    """S14.9 (06/10): the green-screen fallback went with the flag location_plates — no phase left, a recorded 'place redrawn' clip
    and an old FEATURE_LOCATION_PLATES=1 line make nothing happen (as with the flag off)."""

    def test_the_phase_is_gone(self):
        self.assertFalse(hasattr(autopilot, "_plate_fallback_phase"))
        self.assertNotIn("platefix", autopilot.PHASE_LABELS)

    def test_an_old_env_line_regenerates_nothing(self):
        data = tempfile.mkdtemp()
        p = Pipeline(connect())
        pid = p.create_project("Nền 3D")
        sid = p.create_scene(pid, 1, "CẢNH 1")
        job = p.create_job(sid, "video_gen")
        p.start(job)
        p.succeed(job)
        from core import features
        with mock.patch.dict(os.environ, {"FEATURE_LOCATION_PLATES": "1"}), mock.patch.object(regen, "regenerate_video") as again:
            self.assertFalse(features.on("location_plates"))
            self.assertIsNone(autopilot._plates_phase(p, pid, autopilot.Context(data, None, None, None)))
        again.assert_not_called()


if __name__ == "__main__":
    unittest.main()
