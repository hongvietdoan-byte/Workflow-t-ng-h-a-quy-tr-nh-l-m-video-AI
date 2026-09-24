import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from core import ffmpeg_studio as f


def ffmpeg_available():
    return bool(os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg"))


class CommandTests(unittest.TestCase):
    def test_concat_with_audio_normalises_each_clip_and_maps_video_and_audio(self):
        cmd = f.build_concat_audio_cmd(["a.mp4", "b.mp4"], "o.mp4")
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("concat=n=2:v=1:a=1[v][a]", graph)
        self.assertEqual(graph.count("aformat=sample_rates=48000"), 2)
        self.assertNotIn("-an", cmd)
        self.assertIn("aac", cmd)

    def test_crossfade_audio_uses_acrossfade_and_default_stays_silent(self):
        silent = f.build_crossfade_cmd(["a", "b"], [5, 5], "o.mp4")
        self.assertIn("-an", silent)
        loud = f.build_crossfade_cmd(["a", "b", "c"], [5, 5, 5], "o.mp4", with_audio=True)
        graph = loud[loud.index("-filter_complex") + 1]
        self.assertEqual(graph.count("acrossfade=d=1.0"), 2)
        self.assertNotIn("-an", loud)

    def test_music_is_mixed_not_replacing_when_the_video_has_sound(self):
        replace = f.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", 30)
        mixed = f.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", 30, has_audio=True)
        self.assertNotIn("amix", replace[replace.index("-filter_complex") + 1])
        self.assertIn("[0:a][m]amix=inputs=2:normalize=0:duration=first[a]", mixed[mixed.index("-filter_complex") + 1])

    def test_a_clip_without_sound_gets_a_silent_track_instead_of_silencing_every_clip(self):
        """D4: it used to drop the sound of ALL clips when one clip had none."""
        calls = []
        with mock.patch.object(f, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(f, "has_audio", side_effect=lambda c: c == "a"), \
                mock.patch.object(f, "run", side_effect=calls.append), mock.patch.object(os, "remove"), \
                mock.patch.object(f, "_commit"):   # D6: no real file to move
            f.render_final(["a", "b"], "o.mp4", [5, 5], keep_audio=True)
        self.assertIn("anullsrc", " ".join(calls[0]))                     # b padded with silence
        self.assertIn("concat=n=2:v=1:a=1", " ".join(calls[1]))           # the sound of a is kept

    def test_music_and_extras_know_the_video_has_sound(self):
        calls = []
        with mock.patch.object(f, "find_ffmpeg", return_value="ffmpeg"), mock.patch.object(f, "has_audio", return_value=True), \
                mock.patch.object(f, "run", side_effect=calls.append), mock.patch.object(os, "remove"), \
                mock.patch.object(f, "_commit"):   # D6: no real file to move
            f.render_final(["a", "b"], "o.mp4", [5, 5], music="m.mp3", extras=[{"path": "x.mp3", "start": 0, "volume": 1}],
                           keep_audio=True)
        self.assertIn("amix=inputs=2", " ".join(calls[1]))      # music mixed with the dialogue
        self.assertIn("[0:a][e0]amix=inputs=2", " ".join(calls[2]))  # extras mixed with dialogue + music


@unittest.skipUnless(ffmpeg_available(), "ffmpeg not installed")
class RealFfmpegTests(unittest.TestCase):
    """Runs the real ffmpeg: clips with speech-like audio keep it in the final cut."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ff = f.find_ffmpeg()

    def clip(self, name, seconds, audio=True, hz=440):
        path = os.path.join(self.dir, name)
        cmd = [self.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"testsrc=d={seconds}:s=320x180:r=24"]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"sine=f={hz}:d={seconds}", "-c:a", "aac", "-shortest"]
        cmd += ["-pix_fmt", "yuv420p", path]
        subprocess.run(cmd, check=True)
        return path

    def test_cut_crossfade_and_music_keep_the_clip_audio(self):
        a, b = self.clip("a.mp4", 3), self.clip("b.mp4", 4, hz=880)
        music = os.path.join(self.dir, "m.wav")
        subprocess.run([self.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=2", music], check=True)
        self.assertTrue(f.has_audio(a))
        for transition, expected in (("cut", 7.0), ("crossfade", 6.0), ("dip_to_black", 6.0)):
            out = os.path.join(self.dir, f"o_{transition}.mp4")
            f.render_final([a, b], out, [3.0, 4.0], transition, 1.0, keep_audio=True)
            self.assertTrue(f.has_audio(out), transition)
            self.assertAlmostEqual(f.probe_duration(out), expected, delta=0.3)
        out = os.path.join(self.dir, "o_music.mp4")
        f.render_final([a, b], out, [3.0, 4.0], "cut", 1.0, music, 0.5, keep_audio=True)
        self.assertTrue(f.has_audio(out))
        self.assertAlmostEqual(f.probe_duration(out), 7.0, delta=0.3)
        out = os.path.join(self.dir, "o_all.mp4")
        f.render_final([a, b], out, [3.0, 4.0], "crossfade", 1.0, music, 0.5, [{"path": music, "start": 1, "volume": 0.5}],
                       keep_audio=True)
        self.assertTrue(f.has_audio(out))

    def test_a_silent_clip_gets_a_silent_track_and_the_others_keep_their_sound(self):
        # D4 (GĐ-G phần 1): a clip without sound used to silence the whole cut; it is now padded with silence instead
        a, b = self.clip("a.mp4", 3), self.clip("b.mp4", 3, audio=False)
        out = os.path.join(self.dir, "o.mp4")
        f.render_final([a, b], out, [3.0, 3.0], "cut", 1.0, keep_audio=True)
        self.assertTrue(f.has_audio(out))
        self.assertAlmostEqual(f.probe_duration(out), 6.0, delta=0.3)
        self.assertEqual([n for n in os.listdir(self.dir) if ".pad" in n or ".part-" in n], [])   # no temp file left (D6)


if __name__ == "__main__":
    unittest.main()
