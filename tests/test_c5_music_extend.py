"""C5d (#27 13/10, người dùng "kéo dài thêm nhạc"; cờ music_story_arc): bài nhạc NGẮN hơn chặng của nó được kéo dài — phần đầu nối mềm
vào một bản sao từ giữa bài, GIỮ đoạn kết gốc ở cuối (không lặp từ 0 s, không im). Quá ngắn để nối → im phần cuối, có câu báo."""
import os
import subprocess
import tempfile
import unittest

import pytest

from core import ffmpeg_studio as fs
from core import music_cues as mc


def _ff():
    try:
        return fs.find_ffmpeg()
    except fs.FFmpegNotFound:
        pytest.skip("ffmpeg not installed")


def _tone(ff, path, secs, end_freq=None):
    """`secs` s of 440 Hz; with end_freq the last 1 s is that tone instead (the track's own ending)."""
    if end_freq is None:
        subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=f=440:d={secs}:r=44100", path], check=True)
        return
    subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=f=440:d={secs - 1}:r=44100", "-f", "lavfi", "-i",
                    f"sine=f={end_freq}:d=1:r=44100", "-filter_complex", "[0][1]concat=n=2:v=0:a=1", path], check=True)


def _band_db(ff, path, a, b, freq):
    out = subprocess.run([ff, "-hide_banner", "-i", path, "-af", f"atrim={a}:{b},bandpass=f={freq}:w=60,astats=metadata=0", "-f", "null",
                          "-"], capture_output=True, text=True).stderr
    import re
    vals = re.findall(r"RMS level dB:\s*(-?inf|-?[\d.]+)", out)
    return -120.0 if not vals or "inf" in vals[-1] else float(vals[-1])


class ExtendTests(unittest.TestCase):
    def test_a_short_chapter_track_is_extended_and_keeps_its_own_ending(self):
        ff = _ff()
        with tempfile.TemporaryDirectory() as d:
            main, short, bed = (os.path.join(d, n) for n in ("main.wav", "short.wav", "bed.wav"))
            _tone(ff, main, 20)
            _tone(ff, short, 12, end_freq=1200)
            notes = []
            mc.assemble([{"path": main, "start": 0, "join": "enter"}, {"path": short, "start": 6.0, "join": "cut"}], 22.0, bed, notes)
            self.assertAlmostEqual(fs.probe_duration(bed), 22.0, delta=0.1)
            self.assertGreater(mc.rms_db(bed, 18.5, 20.5), -40)                 # not silent where the 12 s track used to stop (18 s)
            self.assertGreater(_band_db(ff, bed, 21.1, 21.9, 1200), _band_db(ff, bed, 21.1, 21.9, 440) + 10)   # its ending at the end
            self.assertTrue(notes and "kéo dài" in notes[0], notes)
            self.assertFalse([f for f in os.listdir(d) if ".ext" in f])           # temporary copy removed

    def test_long_enough_track_is_untouched_and_too_short_one_is_said(self):
        self.assertIsNone(mc.extend_cmd("x.wav", 30.0, 20.0, "o.wav"))
        self.assertIsNone(mc.extend_cmd("x.wav", 9.0, 20.0, "o.wav"))            # too short to join: played as it is
        ff = _ff()
        with tempfile.TemporaryDirectory() as d:
            main, tiny, bed = (os.path.join(d, n) for n in ("main.wav", "tiny.wav", "bed.wav"))
            _tone(ff, main, 20)
            _tone(ff, tiny, 5)
            notes = []
            mc.assemble([{"path": main, "start": 0, "join": "enter"}, {"path": tiny, "start": 6.0, "join": "cut"}], 22.0, bed, notes)
            self.assertTrue(notes and "quá ngắn" in notes[0], notes)
            long_one = os.path.join(d, "long.wav")
            _tone(ff, long_one, 12)
            fs.run(mc.extend_cmd(long_one, 12.0, 40.0, os.path.join(d, "x.wav"), ff))     # many middles: still exactly long enough
            self.assertAlmostEqual(fs.probe_duration(os.path.join(d, "x.wav")), 40.2, delta=0.1)


if __name__ == "__main__":
    unittest.main()
