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


class FitWholeFilmTests(unittest.TestCase):
    """14/10 người dùng: một bài nhạc ngắn hơn phim phải "fit khớp với cả phim" — kéo dài giữ đoạn kết gốc, không lặp lại từ 0 s."""

    def test_short_single_music_is_stretched_to_the_film_with_its_own_ending(self):
        from core import delivery
        ff = _ff()
        with tempfile.TemporaryDirectory() as d:
            track = os.path.join(d, "m.wav")
            _tone(ff, track, 12, end_freq=1200)
            path, info = delivery.fit_music_to_film(track, 30.0, d)
            self.assertNotEqual(path, track)
            self.assertTrue(info["extended"])
            self.assertAlmostEqual(fs.probe_duration(path), 30.2, delta=0.1)
            self.assertGreater(_band_db(ff, path, 29.3, 30.1, 1200), _band_db(ff, path, 29.3, 30.1, 440) + 10)   # ends on its ending
            self.assertGreater(mc.rms_db(path, 20.0, 22.0), -40)                                                   # never silent

    def test_long_music_is_left_and_a_too_short_one_keeps_the_loop_and_says_so(self):
        from core import delivery
        ff = _ff()
        with tempfile.TemporaryDirectory() as d:
            long_one, tiny = os.path.join(d, "l.wav"), os.path.join(d, "t.wav")
            _tone(ff, long_one, 40)
            _tone(ff, tiny, 5)
            self.assertEqual(delivery.fit_music_to_film(long_one, 30.0, d), (long_one, None))
            path, info = delivery.fit_music_to_film(tiny, 30.0, d)
            self.assertEqual(path, tiny)
            self.assertFalse(info["extended"])
            self.assertIn("lặp lại từ đầu", info["note"])

    def test_render_sends_the_stretched_music(self):
        import json as _json
        from unittest import mock
        from core import delivery, final_cut
        from core.db import connect
        from core.pipeline import Pipeline
        ff = _ff()
        d = tempfile.mkdtemp()
        p = Pipeline(connect(":memory:"))
        pid = p.create_project("fit film")
        for idx in (1, 2):
            p.create_scene(pid, idx, f"s{idx}")
            clip = final_cut.clip_path(d, pid, idx)
            os.makedirs(os.path.dirname(clip), exist_ok=True)
            subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=10:s=64x64:r=24", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", clip], check=True)
        p.conn.commit()
        track = os.path.join(d, "m.wav")
        _tone(ff, track, 12, end_freq=1200)
        sent = {}
        real = fs.render_final

        def spy(paths, out, durations, transition, fade, music, *a, **k):
            sent["music"] = music
            return real(paths, out, durations, transition, fade, music, *a, **k)

        with mock.patch("core.features.on", return_value=False), mock.patch.object(fs, "render_final", side_effect=spy), \
                mock.patch("core.formats.spec", return_value={"render": None}), mock.patch.object(delivery, "_loudness", return_value={}):
            res = delivery.render(p, pid, d, music_path=track, settings=delivery.get_settings(p, pid))
        self.assertTrue(sent["music"].endswith("music_fit_film.wav"))
        man = _json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()["manifest"])
        self.assertTrue(man["music_fill"]["extended"])
