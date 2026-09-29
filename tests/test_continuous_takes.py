"""S3.4 (kế hoạch sau #8): each camera set-up films the WHOLE stretch of acting, and each shot is cut at its own place in that stretch —
the cut between angles lands mid-action (#8: every shot made alone, movement restarted at each cut)."""
import json
import os
import subprocess
import tempfile
import unittest

from core import shots
from core.db import connect
from core.ffmpeg_studio import find_ffmpeg, probe_duration
from core.pipeline import Pipeline


class ContinuousTakeTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("take")
        self.ids = []
        for i, (setup, sec) in enumerate((("A", 2.0), ("B", 1.5), ("A", 2.5), ("C", 1.0)), 1):
            sid = self.p.create_scene(self.pid, i, f"S{i}")
            data = {"shot_no": i, "story_scene": 1, "sequence": 1, "camera_setup": setup, "duration_s": sec,
                    "motion_en": {"action": f"action {i}"}, "shot": "medium shot, eye angle, static"}
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
            self.ids.append(sid)
        self.p.conn.commit()
        self.rows = shots._rows(self.p.conn, self.pid)

    def test_the_stretch_runs_from_the_first_to_the_last_shot_of_the_set_up(self):
        group = [self.rows[0], self.rows[2]]                           # set-up A: shots 1 and 3 (B between them)
        st = shots.stretch_of(self.p.conn, group)
        self.assertEqual([r["id"] for r in st["rows"]], self.ids[:3])
        self.assertEqual(st["offsets"][self.ids[0]], 0.0)
        self.assertEqual(st["offsets"][self.ids[2]], 3.5)             # after shot 1 (2 s) and shot 2 (1.5 s) of the other set-up
        text = shots.stretch_motion(st, [r["id"] for r in group], "medium shot")
        for want in ("0.0–2.0s: action 1", "2.0–3.5s: action 2", "3.5–6.0s: action 3", "ONE fixed camera"):
            self.assertIn(want, text)

    def test_a_stretch_longer_than_one_clip_is_not_used(self):
        self.assertIsNone(shots.stretch_of(self.p.conn, [self.rows[0], self.rows[2]], lambda r: 8.0))   # 3 × 8 s > one clip

    def test_each_shot_is_cut_at_its_offset(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "take.mp4")
        subprocess.run([find_ffmpeg(), "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=160x284:r=24:d=6", "-pix_fmt", "yuv420p", src],
                       check=True, capture_output=True)
        group = [{"id": self.ids[0], "idx": 1, "data": {"duration_s": 2.0, "exact": True, "offset": 0.0}},
                 {"id": self.ids[2], "idx": 3, "data": {"duration_s": 2.5, "exact": True, "offset": 3.5}}]
        out = shots.split_group_clip(src, group, [os.path.join(d, "a.mp4"), os.path.join(d, "b.mp4")])
        self.assertAlmostEqual(probe_duration(out[0]), 2.0, delta=0.1)
        self.assertAlmostEqual(probe_duration(out[1]), 2.5, delta=0.1)   # from 3.5 s, not from 2.0 s where shot 1 ended


if __name__ == "__main__":
    unittest.main()
