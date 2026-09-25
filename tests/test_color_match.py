"""D7 (knowledge/editor/editing.md E5): shots of one place are compared by black / white points and the cast of grey things (not
the average colour, which follows the content), and a drifting shot can be pulled toward its anchor."""
import json
import os
import subprocess
import tempfile
import unittest

import numpy as np

from core import color_match as cm, ffmpeg_studio


def frame(tint=(1.0, 1.0, 1.0), lo=0.05, hi=0.85, jacket=False):
    """A grey wall (the neutral), a dark and a bright patch, all under one light (`tint`); optional big yellow jacket (content)."""
    img = np.ones((90, 60, 3), np.float32) * 0.5
    img[:10] = lo
    img[-10:] = hi
    if jacket:
        img[20:70, 10:50] = (0.9, 0.8, 0.1)
    return np.clip(img * np.array(tint, np.float32), 0, 1)


class StatsTests(unittest.TestCase):
    def test_content_does_not_count_as_a_colour_difference(self):
        plain, dressed = cm.stats(frame()), cm.stats(frame(jacket=True))
        self.assertFalse(cm.deviation(dressed, plain)["off"])                 # a yellow jacket is not a warmer light

    def test_a_warm_cast_and_a_darker_shot_are_caught(self):
        base = cm.stats(frame())
        warm = cm.stats(frame(tint=(1.1, 1.0, 0.9)))
        self.assertTrue(cm.deviation(warm, base)["off"])
        self.assertGreater(cm.deviation(warm, base)["cast"], cm.CAST_WARN)
        dark = cm.stats(frame(lo=0.0, hi=0.6))
        self.assertGreater(cm.deviation(dark, base)["levels"], cm.LEVELS_WARN)

    def test_the_correction_moves_toward_the_anchor_within_limits(self):
        base, warm = cm.stats(frame()), cm.stats(frame(tint=(1.1, 1.0, 0.9)))
        fix = cm.correction(warm, base)
        self.assertLess(fix["gain"][0], 1)                                    # less red
        self.assertGreater(fix["gain"][2], 1)                                 # more blue
        self.assertTrue(all(1 - cm.MAX_GAIN <= g <= 1 + cm.MAX_GAIN for g in fix["gain"]))

    def test_groups_are_one_place_one_scene_one_size_class(self):
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("colour")
        rows = []
        for idx, (scene, size, place) in enumerate([(1, "WS", "tháp"), (1, "MS", "tháp"), (1, "CU", "tháp"), (1, "ECU", "tháp"),
                                                    (2, "WS", "tháp"), (1, "MS", "nhà")], 1):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                           (json.dumps({"story_scene": scene, "size": size, "location": place}), sid))
            rows.append({"scene_id": sid, "idx": idx, "path": None})
        p.conn.commit()
        self.assertEqual(cm.groups(p.conn, pid, rows), [[0, 1], [2, 3]])        # wide with medium, close with close; alone = no match


class ApplyTests(unittest.TestCase):
    def test_a_warm_clip_is_pulled_back(self):
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            self.skipTest("no ffmpeg")
        d = tempfile.mkdtemp()
        ref, warm = os.path.join(d, "ref.mp4"), os.path.join(d, "warm.mp4")
        for path, colour in ((ref, "0x808080"), (warm, "0x998066")):
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=160x284:d=1", "-vf",
                            "drawbox=y=0:w=160:h=20:color=black:t=fill,drawbox=y=264:w=160:h=20:color=white:t=fill",
                            "-pix_fmt", "yuv420p", path], check=True)
        a, w = cm.measure(ref, ff), cm.measure(warm, ff)
        before = cm.deviation(w, a)["cast"]
        fixed = cm.apply(warm, os.path.join(d, "fixed.mp4"), cm.correction(w, a), ff)
        after = cm.deviation(cm.measure(fixed, ff), a)["cast"]
        self.assertLess(after, before * 0.6)


if __name__ == "__main__":
    unittest.main()
