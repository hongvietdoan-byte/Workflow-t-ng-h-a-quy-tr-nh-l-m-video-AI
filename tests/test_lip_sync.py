"""S4.5: clip_measure.lip_sync — mouth landmarks against the voice, line by line. Synthetic mouth series and voices (the landmark model
is not needed: the tracks are handed in); the real calibration is tools/lip_sync_calibrate.py."""
import math
import os
import shutil
import subprocess
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np

from core import claude_tasks, clip_measure as cm
from core.ffmpeg_studio import find_ffmpeg

FPS = 24.0
N = 120                                               # 5 s


def _voice(spans, seed=1):
    """A per-frame envelope: syllables (~5 a second, random loudness) inside each (start, end) second span, silence elsewhere."""
    rng = np.random.default_rng(seed)
    env = np.zeros(N)
    for a, b in spans:
        for i in range(int(a * FPS), int(b * FPS)):
            env[i] = (0.3 + 0.7 * rng.random()) * abs(math.sin(math.pi * 5 * i / FPS))
    return env


def _mouth(env, late=0.0, rest=0.01, seed=2):
    """A mouth that follows `env` `late` seconds late (smoothed like a real jaw), resting slightly open."""
    rng = np.random.default_rng(seed)
    m = np.convolve(np.roll(env, int(late * FPS)), np.ones(3) / 3, mode="same") * 0.08 + rest
    return list(m + rng.normal(0, 0.002, len(m)))


def _track(x, series):
    return {"x": x, "open": list(series)}


def _wav(path, env):
    """A 16 kHz wav whose loudness per video frame is `env` (a 200 Hz tone)."""
    hop = int(16000 / FPS)
    t = np.arange(hop * len(env)) / 16000
    x = np.sin(2 * np.pi * 200 * t) * np.repeat(env, hop) * 0.8
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return path


class SyncTurnsTests(unittest.TestCase):
    def test_synced_mouth_scores_high_and_is_found(self):
        env = _voice([(0.5, 2.0)])
        still = [0.01] * N
        rows = cm.sync_turns([_track(100, still), _track(400, _mouth(env))], env, FPS, [{"speaker": "A", "start": 0.5, "end": 2.0}])
        self.assertGreater(rows[0]["score"], cm.LIP_SYNC_MIN)
        self.assertEqual(rows[0]["face_x"], 400)
        self.assertLess(rows[0]["wrong_time"], rows[0]["score"] - cm.LIP_MARGIN)

    def test_mouth_a_second_late_scores_low(self):
        env = _voice([(0.5, 2.0)])
        rows = cm.sync_turns([_track(400, _mouth(env, late=1.0))], env, FPS, [{"speaker": "A", "start": 0.5, "end": 2.0}])
        self.assertLess(rows[0]["score"], cm.LIP_SYNC_MIN)

    def test_each_speaker_found_on_their_own_face(self):
        env = _voice([(0.3, 1.7), (2.1, 2.8)])
        first, second = env.copy(), env.copy()
        first[int(2.0 * FPS):] = 0
        second[:int(2.0 * FPS)] = 0
        rows = cm.sync_turns([_track(500, _mouth(first)), _track(350, _mouth(second, seed=3))], env, FPS,
                             [{"speaker": "MAXIM", "start": 0.3, "end": 1.7}, {"speaker": "KENTA", "start": 2.1, "end": 2.8}])
        self.assertEqual([r["face_x"] for r in rows], [500, 350])
        self.assertTrue(all(r["score"] > cm.LIP_SYNC_MIN for r in rows))

    def test_face_not_seen_during_the_line_is_said_not_scored(self):
        env = _voice([(0.5, 2.0)])
        lost = [None] * N
        rows = cm.sync_turns([_track(400, lost)], env, FPS, [{"speaker": "A", "start": 0.5, "end": 2.0}])
        self.assertNotIn("score", rows[0])
        self.assertIn("note", rows[0])

    def test_no_room_to_move_the_voice_gives_no_wrong_time(self):
        env = _voice([(0.2, 4.8)])
        rows = cm.sync_turns([_track(400, _mouth(env))], env, FPS, [{"speaker": None, "start": 0.2, "end": 4.8}])
        self.assertIsNone(rows[0]["wrong_time"])

    def test_voiced_span(self):
        env = _voice([(1.0, 2.5)])
        a, b = cm.voiced_span(list(env), FPS)
        self.assertAlmostEqual(a, 1.0, delta=0.1)
        self.assertAlmostEqual(b, 2.5, delta=0.1)
        self.assertIsNone(cm.voiced_span([0.0] * N, FPS))


@unittest.skipUnless(shutil.which("ffmpeg") or os.path.exists(str(find_ffmpeg())), "needs ffmpeg")
class LipSyncTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.model = os.path.join(self.dir, "face_landmarker.task")
        open(self.model, "wb").close()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _run(self, mouth, env, turns=None):
        wav = _wav(os.path.join(self.dir, "v.wav"), env)
        with mock.patch.dict(os.environ, {"LIP_MODEL": self.model}), mock.patch.dict("sys.modules", {"mediapipe": mock.MagicMock()}):
            return cm.lip_sync("clip.mp4", wav, turns, tracks=([_track(400, mouth)], FPS, N))

    def test_synced_clip_passes(self):
        env = _voice([(0.5, 2.0)])
        out = self._run(_mouth(env), env)
        self.assertIsNone(out["flag"], out)
        self.assertEqual(len(out["turns"]), 1)

    def test_late_mouth_is_flagged_with_the_line_named(self):
        env = _voice([(0.5, 2.0)])
        out = self._run(_mouth(env, late=1.0), env, [{"speaker": "KELLY", "start": 0.5, "end": 2.0}])
        self.assertEqual(out["flag"], "lips_off_voice")
        self.assertIn("KELLY", out["why"])

    def test_without_the_model_it_says_so(self):
        with mock.patch.dict(os.environ, {"LIP_MODEL": os.path.join(self.dir, "none.task")}), \
                mock.patch.object(cm, "LANDMARK_MODEL", os.path.join(self.dir, "none.task")):
            out = cm.lip_sync("clip.mp4", None)
        self.assertIsNone(out["flag"])
        self.assertIn("face_landmarker", out["note"])

    def test_silent_voice_is_said_not_passed(self):
        out = self._run(_mouth(np.zeros(N)), np.zeros(N))
        self.assertIsNone(out["flag"])
        self.assertIn("giọng", out["note"])

    def test_shot_voice_of_another_length_is_not_compared_line_by_line(self):
        wav_dir = os.path.join(self.dir, "7", "lipsync")
        os.makedirs(wav_dir)
        _wav(os.path.join(wav_dir, "shot_5.wav"), np.zeros(N))          # 5 s voice
        clip = os.path.join(self.dir, "c.mp4")
        subprocess.run([find_ffmpeg(), "-y", "-v", "quiet", "-f", "lavfi", "-i", "color=c=gray:size=160x284:rate=24", "-t", "3",
                        "-pix_fmt", "yuv420p", clip], check=True)                # 3 s clip (cut after generation)
        audio, turns, note = claude_tasks._shot_voice(self.dir, 7, 5, clip)
        self.assertIsNone(audio)
        self.assertIn("đã cắt", note)
        self.assertEqual(claude_tasks._shot_voice(self.dir, 7, 6, clip)[2][:9], "chưa có f")


if __name__ == "__main__":
    unittest.main()
