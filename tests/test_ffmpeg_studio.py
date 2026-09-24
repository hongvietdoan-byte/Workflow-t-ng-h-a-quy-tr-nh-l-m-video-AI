import os
import unittest
from unittest import mock

from core import ffmpeg_studio as f


class FFmpegStudioTests(unittest.TestCase):
    def test_concat_list_escapes_and_orders(self):
        path = f.write_concat_list(["a.mp4", "it's b.mp4"])
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        finally:
            os.remove(path)
        self.assertTrue(lines[0].startswith("file '") and lines[0].endswith("a.mp4'"))
        self.assertIn("it'\\''s b.mp4", lines[1])

    def test_concat_cmd(self):
        cmd = f.build_concat_cmd("list.txt", "out.mp4")
        self.assertEqual(cmd[:6], ["ffmpeg", "-y", "-f", "concat", "-safe", "0"])
        self.assertEqual(cmd[-1], "out.mp4")

    def test_crossfade_offsets_for_three_clips(self):
        cmd = f.build_crossfade_cmd(["a", "b", "c"], [5, 5, 5], "o.mp4", fade=1.0)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("[0:v][1:v]xfade=transition=fade:duration=1.0:offset=4.0[v1]", graph)
        self.assertIn("[v1][2:v]xfade=transition=fade:duration=1.0:offset=8.0[v2]", graph)
        self.assertEqual(cmd[cmd.index("-map") + 1], "[v2]")

    def test_crossfade_validation(self):
        with self.assertRaises(ValueError):
            f.build_crossfade_cmd(["a"], [5], "o.mp4")
        with self.assertRaises(ValueError):
            f.build_crossfade_cmd(["a", "b"], [1.0, 5], "o.mp4", fade=1.0)

    def test_mux_music_fades_and_trims_to_video(self):
        cmd = f.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", video_duration=60, fade=1.5, volume=0.5)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("atrim=0:60", graph)
        self.assertIn("afade=t=out:st=58.5:d=1.5", graph)
        self.assertIn("volume=0.5", graph)
        self.assertIn("-shortest", cmd)

    def test_missing_ffmpeg_raises(self):
        with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch("shutil.which", return_value=None):
            os.environ.pop("FFMPEG_PATH", None)
            with self.assertRaises(f.FFmpegNotFound):
                f.find_ffmpeg()

    def test_render_final_runs_expected_steps(self):
        calls = []
        with mock.patch.object(f, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(f, "run", side_effect=calls.append), \
                mock.patch.object(os, "remove"), mock.patch.object(f, "_commit"):   # D6: no real file to move
            f.render_final(["a", "b"], "o.mp4", durations=[5, 5], transition="crossfade", music="m.mp3")
        self.assertEqual(len(calls), 2)
        self.assertIn("xfade", " ".join(calls[0]))
        self.assertIn("atrim=0:9.0", " ".join(calls[1]))


if __name__ == "__main__":
    unittest.main()
