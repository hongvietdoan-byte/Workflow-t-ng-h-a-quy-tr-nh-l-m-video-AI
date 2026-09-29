"""S4.5 (after #8): video QC layer 0 — a stray cut at a shot clip's edge, a jerk, and cleaning the edges. Clips made with ffmpeg."""
import os
import shutil
import subprocess
import tempfile
import unittest

from core import clip_measure, shots
from core.ffmpeg_studio import find_ffmpeg, probe_duration


def _clip(path, parts):
    """parts: [(lavfi source, seconds)] joined with hard cuts."""
    ff = find_ffmpeg()
    tmp = []
    for i, (src, sec) in enumerate(parts):
        t = path + f".{i}.mp4"
        subprocess.run([ff, "-y", "-v", "quiet", "-f", "lavfi", "-i", f"{src}{':' if '=' in src else '='}size=320x568:rate=24", "-t", str(sec), "-pix_fmt", "yuv420p",
                        "-c:v", "libx264", t], check=True)
        tmp.append(t)
    lst = path + ".txt"
    with open(lst, "w") as fh:
        fh.writelines(f"file '{t}'\n" for t in tmp)
    subprocess.run([ff, "-y", "-v", "quiet", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", path], check=True)


@unittest.skipUnless(shutil.which("ffmpeg") or os.path.exists(str(find_ffmpeg())), "needs ffmpeg")
class ClipMeasureTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_the_next_shots_frames_at_the_end_are_found_and_dropped(self):
        path = os.path.join(self.dir, "a.mp4")
        _clip(path, [("testsrc2", 2.0), ("color=c=red", 0.25)])        # a shot, then 6 frames of another one
        res = clip_measure.jerks(path)
        self.assertEqual(res["flag"], "cut_inside")
        head, tail = clip_measure.stray_edges(path)
        self.assertEqual(head, 0.0)
        self.assertAlmostEqual(tail, 0.25, delta=0.05)
        done = shots.clean_edges(path)
        self.assertIsNotNone(done)
        self.assertAlmostEqual(probe_duration(path), 2.0, delta=0.1)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "a_edges.mp4")))    # the uncleaned clip is kept
        self.assertEqual(clip_measure.stray_edges(path), (0.0, 0.0))

    def test_a_cut_in_the_middle_is_not_an_edge(self):
        path = os.path.join(self.dir, "b.mp4")
        _clip(path, [("testsrc2", 1.5), ("color=c=blue", 1.5)])
        self.assertEqual(clip_measure.stray_edges(path), (0.0, 0.0))
        self.assertIsNone(shots.clean_edges(path))

    def test_a_steady_clip_has_no_flag(self):
        path = os.path.join(self.dir, "c.mp4")
        _clip(path, [("testsrc2", 2.0)])
        self.assertIsNone(clip_measure.jerks(path)["flag"])

    def test_the_lips_are_recorded_never_flagged(self):
        out = clip_measure.measure(os.path.join(self.dir, "none.mp4"), None, speaking=False)
        self.assertEqual(out["flags"], [])


if __name__ == "__main__":
    unittest.main()
