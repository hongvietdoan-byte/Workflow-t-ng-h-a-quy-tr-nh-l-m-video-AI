"""S3.6 (kế hoạch sau #8): each shot's `transition_in` drawn at its cut, inside the two clips — the film's length never changes."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import delivery, ffmpeg_studio, shots
from core.db import connect
from core.pipeline import Pipeline


def clip(path, seconds=2.0, colour="blue"):
    subprocess.run([ffmpeg_studio.find_ffmpeg(), "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=160x284:r=24:d={seconds}",
                    "-pix_fmt", "yuv420p", path], check=True, capture_output=True)
    return path


class ShotTransitionTests(unittest.TestCase):
    def test_each_kind_gives_a_filter_and_a_plain_cut_none(self):
        for kind in ffmpeg_studio.EDGE_TRANSITIONS:
            self.assertTrue(ffmpeg_studio.edge_filter(2.0, head=kind, size=(160, 284)))
            self.assertTrue(ffmpeg_studio.edge_filter(2.0, tail=kind, size=(160, 284)))
        self.assertIn("zoompan", ffmpeg_studio.edge_filter(2.0, head="zoom_through", size=(160, 284)))   # crop cannot grow per frame
        for plain in ("cut", "match", "occlusion", "j_cut", None):
            self.assertIsNone(ffmpeg_studio.edge_filter(2.0, head=plain, tail=plain))
        self.assertIn("color=white", ffmpeg_studio.edge_filter(2.0, head="flash"))
        self.assertIn("color=black", ffmpeg_studio.edge_filter(2.0, tail="dip"))

    def test_the_clip_keeps_its_length(self):
        d = tempfile.mkdtemp()
        for kind in ffmpeg_studio.EDGE_TRANSITIONS:
            src = clip(os.path.join(d, f"{kind}.mp4"))
            dst = ffmpeg_studio.add_edges(src, os.path.join(d, f"{kind}_out.mp4"), 2.0, kind, kind)
            self.assertAlmostEqual(ffmpeg_studio.probe_duration(dst), 2.0, delta=0.1)
            self.assertEqual(ffmpeg_studio.probe_size(dst), (160, 284))

    def test_the_render_step_uses_the_next_shots_transition_at_the_tail(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        d = tempfile.mkdtemp()
        rows, paths = [], []
        for i, kind in enumerate((None, "flash", "cut"), 1):
            sid = p.create_scene(pid, i, f"S{i}")
            data = {"shot_no": i, "story_scene": 1}
            if kind:
                data["transition_in"] = kind
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
            path = clip(os.path.join(d, f"c{i}.mp4"))
            rows.append({"scene_id": sid, "idx": i, "path": path})
            paths.append(path)
        p.conn.commit()
        with mock.patch.dict("os.environ", {"FEATURE_SHOT_TRANSITIONS": "1"}):
            out = delivery._edge_transitions(p, rows, paths, [2.0, 2.0, 2.0], os.path.join(d, "_edges"))
        self.assertEqual([(o["idx"], o["head"], o["tail"]) for o in out], [(1, None, "flash"), (2, "flash", "cut")])
        self.assertTrue(paths[0].endswith("edge_1.mp4") and paths[1].endswith("edge_2.mp4") and paths[2].endswith("c3.mp4"))
        self.assertEqual(delivery._edge_transitions(p, rows, list(paths), [2.0] * 3, d), [])   # feature off: nothing

    def test_the_director_field_is_kept_only_when_known(self):
        base = {"size": "MS", "role": "action", "duration_s": 2, "image_prompt": "x", "action": "y"}
        self.assertEqual(shots.shot_data({"idx": 1}, dict(base, transition_in="whip"), 1)["transition_in"], "whip")
        self.assertNotIn("transition_in", shots.shot_data({"idx": 1}, dict(base, transition_in="star_wipe"), 1))
        self.assertNotIn("transition_in", shots.shot_data({"idx": 1}, dict(base, transition_in="cut"), 1))


if __name__ == "__main__":
    unittest.main()
