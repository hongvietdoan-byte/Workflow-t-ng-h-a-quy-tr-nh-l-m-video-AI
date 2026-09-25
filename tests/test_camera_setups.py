"""1.5 / H5 "quay theo vị trí máy" (flag camera_setups): shots of one script scene sharing a camera set-up are made as ONE continuous clip
from the first shot's picture, then cut at each shot's own seconds (trial 2A: shots 9+10 as one 4 s clip, 33% fewer paid seconds)."""
import json
import os
import unittest

from core import llm_runner, shots
from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project


class CameraSetupTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        os.environ["FEATURE_CAMERA_SETUPS"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CAMERA_SETUPS", None)
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        rows = [r for r in shots.shots_of(self.p, self.pid)]
        first = rows[0]["data"]["story_scene"]
        self.scene = [r for r in rows if r["data"]["story_scene"] == first]
        self.assertGreaterEqual(len(self.scene), 3, "the mock plan needs 3 shots in its first scene")
        for r, letter in zip(self.scene, "ABA"):                            # A B A: the set-up A is not consecutive
            d = dict(r["data"], camera_setup=letter)
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        self.p.conn.commit()
        self.a1, self.b, self.a2 = self.scene[0]["id"], self.scene[1]["id"], self.scene[2]["id"]

    def test_the_set_up_group_shares_the_first_picture(self):
        group = shots.group_of(self.p.conn, self.a2)
        self.assertEqual([r["id"] for r in group], [self.a1, self.a2])
        self.assertIsNone(shots.group_of(self.p.conn, self.b))              # B alone: made on its own
        self.assertFalse(shots.needs_own_image(self.p.conn, self.a2))       # one picture fewer
        self.assertEqual(shots.image_scene(self.p.conn, self.a2), self.a1)

    def test_one_continuous_clip_is_sent_for_the_set_up(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        vr = VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)
        leader = self.p.create_job(self.a1, "video_gen")
        follower = self.p.create_job(self.a2, "video_gen")
        self.assertTrue(vr._wait(self.p.job(follower)))                     # the later A shot waits for its part
        args = vr._submit_args(self.p.job(leader))
        self.assertIn("One continuous take from a single fixed camera set-up", args[1])
        secs = [vr._cut_seconds(r) for r in shots.group_of(self.p.conn, self.a1)]
        self.assertEqual(args[3], max(int(-(-sum(secs) // 1)), 3))          # the set-up's own length, rounded up
        self.assertNotIn("multi_prompt", vr._submit_kwargs(self.p.job(leader)))
        stamp = json.loads(vr._stamp(self.p.job(leader), args)["sent_group"])
        self.assertTrue(all(g["exact"] for g in stamp))                     # cut at the shots' own seconds, not 3 s each

    def test_the_set_up_clip_is_cut_at_the_shots_own_seconds(self):
        import subprocess
        import tempfile
        from core import ffmpeg_studio
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            self.skipTest("no ffmpeg")
        d = tempfile.mkdtemp()
        clip = os.path.join(d, "01.mp4")
        subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=64x64:d=4", "-c:v", "libx264", clip], check=True)
        group = [{"id": 1, "idx": 1, "data": {"duration_s": 2.4, "exact": True}}, {"id": 3, "idx": 3, "data": {"duration_s": 1.5, "exact": True}}]
        out = shots.split_group_clip(clip, group, [clip, os.path.join(d, "03.mp4")])
        lengths = [ffmpeg_studio.probe_duration(p) for p in out]
        self.assertAlmostEqual(lengths[1], 1.5, delta=0.15)                # not the multi-shot minimum of 3 s

    def test_off_by_default(self):
        os.environ.pop("FEATURE_CAMERA_SETUPS", None)
        self.assertIsNone(shots.group_of(self.p.conn, self.a2))
        self.assertTrue(shots.needs_own_image(self.p.conn, self.a2))


if __name__ == "__main__":
    unittest.main()
