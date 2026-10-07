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

    def test_music_comes_in_at_the_chosen_second(self):
        """07/10 Khủng Long Đỏ: the dance's own 34 s track must start with the dance (16 s), not with the film — real ffmpeg run."""
        import subprocess
        import tempfile
        import wave
        import numpy as np
        ff = f.find_ffmpeg()
        d = tempfile.mkdtemp()
        video, music, out, wav = (os.path.join(d, n) for n in ("v.mp4", "m.wav", "o.mp4", "o.wav"))
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=4", "-c:v", "libx264", video], check=True)
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=4", music], check=True)
        subprocess.run(f.build_mux_music_cmd(video, music, out, 4.0, fade=0.2, volume=1.0, ffmpeg=ff, start=2.0), check=True,
                       capture_output=True)
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", out, "-ac", "1", "-ar", "8000", wav], check=True)
        with wave.open(wav) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
        rms = lambda a, b: float(np.sqrt(np.mean(x[int(a * 8000):int(b * 8000)] ** 2)))  # noqa: E731
        self.assertLess(rms(0.2, 1.8), 50)                     # silent before 2 s
        self.assertGreater(rms(2.5, 3.5), 1000)                # the music from 2 s
        graph = f.build_mux_music_cmd("v", "m", "o", 51.5, start=16)
        self.assertIn("adelay=16000:all=1", " ".join(graph))
        self.assertIn("atrim=0:35.5", " ".join(graph))         # trimmed to what is left of the film

    def test_the_frame_punches_in_on_the_beats_of_the_music(self):
        """07/10 Khủng Long Đỏ (người dùng): the camera zooms in a little and shakes on the song's beats — real librosa + ffmpeg run."""
        import subprocess
        import tempfile
        import numpy as np
        from PIL import Image
        ff = f.find_ffmpeg()
        d = tempfile.mkdtemp()
        clicks, video, out = (os.path.join(d, n) for n in ("c.wav", "v.mp4", "o.mp4"))
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "aevalsrc='if(lt(mod(t,0.5),0.03),sin(2*PI*1000*t),0)':s=22050:d=8", clicks], check=True)   # 120 BPM clicks
        beats = f.music_beats(clicks, start=1.0, until=8.0)
        self.assertGreater(len(beats), 8)
        gaps = np.diff(beats)
        self.assertLess(abs(float(np.median(gaps)) - 0.5), 0.05)                # the 0.5 s beat found
        self.assertGreaterEqual(beats[0], 1.0)                                   # on the film timeline (music from 1 s)
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=160x288:d=8:r=24",
                        "-vf", "drawbox=x=0:y=114:w=160:h=60:c=white:t=fill", "-c:v", "libx264", "-pix_fmt", "yuv420p", video], check=True)
        f.add_pulse(video, out, [2.0], ff)
        def white_rows(sec):
            frame = os.path.join(d, f"f{sec}.png")
            subprocess.run([ff, "-y", "-loglevel", "error", "-ss", str(sec), "-i", out, "-frames:v", "1", frame], check=True)
            col = np.asarray(Image.open(frame).convert("L"))[:, 80]
            return int((col > 128).sum())
        self.assertEqual(f.probe_size(out), (160, 288))                          # same frame size, no border
        self.assertGreater(white_rows(2.02), white_rows(1.5))                    # the bar is bigger on the beat (zoomed in)
        self.assertEqual(f.pulse_filter([], 160, 288), "")

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
