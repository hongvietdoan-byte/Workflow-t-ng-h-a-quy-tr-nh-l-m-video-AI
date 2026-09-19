import os
import struct
import tempfile
import unittest
import wave
from unittest import mock

from core import ffmpeg_studio, waveform
from dashboard import ui


def write_wav(path, loud_then_quiet=True, channels=1):
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(8000)
        frames = b""
        for i in range(8000):
            amp = (20000 if i < 4000 else 2000) if loud_then_quiet else 10000
            frames += struct.pack("<h", amp if i % 2 else -amp) * channels
        w.writeframes(frames)


class WaveformTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_wav_peaks_follow_loudness_and_are_normalised(self):
        path = os.path.join(self.dir, "a.wav")
        write_wav(path)
        p = waveform.peaks(path, bars=10)
        self.assertEqual(len(p), 10)
        self.assertEqual(max(p), 1.0)
        self.assertGreater(p[0], 0.9)
        self.assertLess(p[-1], 0.2)

    def test_stereo_wav_is_supported(self):
        path = os.path.join(self.dir, "s.wav")
        write_wav(path, channels=2)
        self.assertEqual(len(waveform.peaks(path, bars=8)), 8)

    def test_non_wav_uses_ffmpeg_pcm_and_missing_ffmpeg_gives_empty(self):
        pcm = struct.pack("<8h", 100, -100, 400, -400, 200, -200, 50, -50)
        proc = mock.Mock(returncode=0, stdout=pcm)
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch("subprocess.run", return_value=proc):
            self.assertEqual(waveform.peaks("x.mp3", bars=4), [0.25, 1.0, 0.5, 0.125])
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", side_effect=ffmpeg_studio.FFmpegNotFound("x")):
            self.assertEqual(waveform.peaks("x.mp3"), [])

    def test_corrupt_wav_falls_back_without_crashing(self):
        path = os.path.join(self.dir, "bad.wav")
        with open(path, "wb") as f:
            f.write(b"not a wav")
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", side_effect=ffmpeg_studio.FFmpegNotFound("x")):
            self.assertEqual(waveform.peaks(path), [])

    def test_svg_has_one_bar_per_peak_and_placeholder_when_empty(self):
        svg = ui.waveform_svg([0.5, 1.0, 0.1])
        self.assertEqual(svg.count("<rect"), 3)
        self.assertIn('class="wave"', ui.waveform_svg([]))


if __name__ == "__main__":
    unittest.main()
