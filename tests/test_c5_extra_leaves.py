"""C5c (lỗi 10 #27): nhiều âm phụ → mỗi âm một WAV dài bằng phim (trễ nằm sẵn), đồ thị trộn cuối chỉ có đầu vào bắt đầu từ 0 — tránh đồ thị
nhiều đầu vào + adelay dài tự khóa. Ít âm: lệnh như cũ."""
import os
import subprocess
import tempfile
import unittest
from unittest import mock

import pytest

from core import ffmpeg_studio as fs
from core import music_cues


def _ff():
    try:
        return fs.find_ffmpeg()
    except fs.FFmpegNotFound:
        pytest.skip("ffmpeg not installed")


class LeafTests(unittest.TestCase):
    def setUp(self):
        self.ff = _ff()
        self.d = tempfile.mkdtemp()
        self.clip = os.path.join(self.d, "c.mp4")
        subprocess.run([self.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=12:s=64x64:r=24", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", self.clip], check=True)
        self.beep = os.path.join(self.d, "b.wav")
        subprocess.run([self.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=880:d=0.3:r=44100", self.beep], check=True)

    def _render(self, n):
        extras = [{"path": self.beep, "start": 1.0 + i, "volume": 1.0} for i in range(n)]
        out = os.path.join(self.d, f"out{n}.mp4")
        seen = []
        real = fs.build_extras_mix_cmd

        def spy(video, ex, *a, **k):
            seen.append([dict(e) for e in ex])
            return real(video, ex, *a, **k)

        with mock.patch.object(fs, "build_extras_mix_cmd", side_effect=spy):
            fs.render_final([self.clip], out, [12.0], "cut", 1.0, None, 0.5, extras, False, None)
        return out, seen[0]

    def test_many_sounds_are_laid_first_and_still_heard_at_their_second(self):
        out, mixed = self._render(fs.LEAF_FROM)
        self.assertTrue(all(e["start"] == 0 and e["path"].endswith(".wav") and ".leaf" in e["path"] for e in mixed))
        self.assertFalse([f for f in os.listdir(self.d) if ".leaf" in f])        # temporary files removed
        self.assertAlmostEqual(fs.probe_duration(out), 12.0, delta=0.2)
        loud, quiet = music_cues.rms_db(out, 3.0, 3.25), music_cues.rms_db(out, 3.5, 3.9)   # beep 3 starts at 3,0 s
        self.assertGreater(loud - quiet, 20)

    def test_few_sounds_keep_the_one_graph(self):
        _, mixed = self._render(fs.LEAF_FROM - 1)
        self.assertEqual([e["start"] for e in mixed], [1.0 + i for i in range(fs.LEAF_FROM - 1)])
        self.assertTrue(all(e["path"] == self.beep for e in mixed))


if __name__ == "__main__":
    unittest.main()
