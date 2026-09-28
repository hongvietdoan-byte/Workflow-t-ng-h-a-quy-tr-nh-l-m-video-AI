"""S2.5 (kế hoạch sau #8): a lone Seedance reference-only clip (≥ 4 s) is no longer kept whole — with the feature motion_trim it is cut
at its busiest window, never under the action's floor (#8: lone 4 s clips made the film long; cutting to the bare 1 s plan lost
S5·1's fall)."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import shots
from core.db import connect
from core.ffmpeg_studio import find_ffmpeg, probe_duration
from core.pipeline import Pipeline


def clip(path, still_s=2.5, moving_s=1.5):
    """still grey, then a moving test pattern — the action happens late."""
    ff = find_ffmpeg()
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=gray:s=160x284:r=24:d={still_s}",
                    "-f", "lavfi", "-i", f"testsrc2=s=160x284:r=24:d={moving_s}",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", path],
                   check=True, capture_output=True)
    return path


class LoneTrimTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        pid = self.p.create_project("trim")
        self.sid = self.p.create_scene(pid, 1, "S1")
        data = {"shot_no": 1, "duration_s": 1.0, "action": "Maxim falls to the ground"}
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), self.sid))
        self.p.conn.commit()
        self.dir = tempfile.mkdtemp()

    def test_off_the_clip_is_kept_whole(self):
        path = clip(os.path.join(self.dir, "a.mp4"))
        with mock.patch.dict("os.environ", {"FEATURE_MOTION_TRIM": "0"}):
            self.assertFalse(shots.trim_clip(self.p, self.sid, path, lone_ref=True))
        self.assertAlmostEqual(probe_duration(path), 4.0, delta=0.15)

    def test_on_the_clip_is_cut_at_the_action_and_keeps_the_floor(self):
        path = clip(os.path.join(self.dir, "b.mp4"))
        with mock.patch.dict("os.environ", {"FEATURE_MOTION_TRIM": "1"}):
            self.assertTrue(shots.trim_clip(self.p, self.sid, path, lone_ref=True))
        self.assertAlmostEqual(probe_duration(path), 2.0, delta=0.15)       # a big action keeps MIN_ACTION_SHOT, not the 1 s plan
        self.assertTrue(os.path.exists(os.path.join(self.dir, "b_raw.mp4")))
        prof = shots.motion_profile(path)
        self.assertGreater(sum(prof) / len(prof), 0.01)                     # the kept part is the moving one, not the still start


if __name__ == "__main__":
    unittest.main()
