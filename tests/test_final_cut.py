import os
import tempfile
import unittest
from unittest import mock

from core import ffmpeg_studio, final_cut
from core.db import connect
from core.llm_io import store_motion_prompts
from core.pipeline import Pipeline


class FinalCutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("Demo")
        for i, title in ((1, "Mở đầu"), (2, "Cao trào"), (3, "Kết")):
            self.p.create_scene(self.pid, i, title)
        os.makedirs(os.path.join(self.tmp, str(self.pid), "videos"))

    def touch(self, name):
        path = os.path.join(self.tmp, str(self.pid), "videos", name)
        open(path, "wb").write(b"x")
        return path

    def test_collect_orders_by_scene_flags_missing_and_appends_extras(self):
        self.touch("01.mp4")
        self.touch("03.mp4")
        self.touch("bonus.mp4")
        clips = final_cut.collect_clips(self.p, self.tmp, self.pid)
        self.assertEqual([c["idx"] for c in clips], [1, 2, 3, None])
        self.assertEqual([bool(c["path"]) for c in clips], [True, False, True, True])
        self.assertEqual(clips[3]["title"], "bonus.mp4")

    def test_collect_reports_job_state_and_requested_length(self):
        scene = self.p.conn.execute("SELECT id FROM scenes WHERE idx=2").fetchone()["id"]
        img = self.p.create_job(scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        job = self.p.create_job(scene, "video_gen")
        self.p.start(job)
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 2, "motion_prompt": "push", "duration_sec": 7}]})
        clip = final_cut.collect_clips(self.p, self.tmp, self.pid)[1]
        self.assertEqual((clip["state"], clip["requested_sec"], clip["path"]), ("running", 7, None))

    def test_clip_seconds_fallbacks(self):
        with mock.patch.object(ffmpeg_studio, "probe_duration", return_value=4.2):
            self.assertEqual(final_cut.clip_seconds("a.mp4", 9), 4.2)
        with mock.patch.object(ffmpeg_studio, "probe_duration", return_value=None):
            self.assertEqual(final_cut.clip_seconds("a.mp4", 9), 9)
            self.assertEqual(final_cut.clip_seconds("a.mp4", None), final_cut.DEFAULT_SECONDS)

    def test_totals_and_problems(self):
        self.assertEqual(final_cut.total_seconds([5, 5, 5], "cut", 1), 15)
        self.assertEqual(final_cut.total_seconds([5, 5, 5], "crossfade", 1), 13)
        self.assertTrue(final_cut.render_problems([], "cut", 1))
        self.assertTrue(final_cut.render_problems([5], "crossfade", 1))
        self.assertTrue(final_cut.render_problems([5, 0.8], "crossfade", 1))
        self.assertEqual(final_cut.render_problems([5, 5], "crossfade", 1), [])

    def test_probe_parses_ffmpeg_banner(self):
        proc = mock.Mock(stderr="  Duration: 00:01:02.50, start: 0.000000, bitrate: 900 kb/s")
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch("subprocess.run", return_value=proc):
            self.assertEqual(ffmpeg_studio.probe_duration("a.mp4"), 62.5)
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", side_effect=ffmpeg_studio.FFmpegNotFound("x")):
            self.assertIsNone(ffmpeg_studio.probe_duration("a.mp4"))

    def test_music_is_padded_and_volume_passed_through(self):
        cmd = ffmpeg_studio.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", 30)
        self.assertIn("apad", " ".join(cmd))
        calls = []
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(ffmpeg_studio, "run", side_effect=calls.append), mock.patch.object(os, "remove"):
            ffmpeg_studio.render_final(["a", "b"], "o.mp4", [5, 5], music="m.mp3", music_volume=0.3)
        self.assertIn("volume=0.3", " ".join(calls[1]))

    def test_dip_to_black_uses_fadeblack_and_overlaps_like_crossfade(self):
        cmd = ffmpeg_studio.build_crossfade_cmd(["a", "b"], [5, 5], "o.mp4", 1.0, style="fadeblack")
        self.assertIn("xfade=transition=fadeblack", " ".join(cmd))
        self.assertEqual(final_cut.total_seconds([5, 5, 5], "dip_to_black", 1), 13)
        self.assertTrue(final_cut.render_problems([5], "dip_to_black", 1))
        calls = []
        with mock.patch.object(ffmpeg_studio, "find_ffmpeg", return_value="ffmpeg"),                 mock.patch.object(ffmpeg_studio, "run", side_effect=calls.append):
            ffmpeg_studio.render_final(["a", "b"], "o.mp4", [5, 5], "dip_to_black")
        self.assertIn("fadeblack", " ".join(calls[0]))
        self.assertIn("xfade=transition=fade:", " ".join(ffmpeg_studio.build_crossfade_cmd(["a", "b"], [5, 5], "o.mp4")))


if __name__ == "__main__":
    unittest.main()
