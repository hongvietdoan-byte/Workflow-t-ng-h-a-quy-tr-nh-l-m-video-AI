"""S1 (kế hoạch sửa sau #8, 2026-09-28): QC of the finished cut by code, flashback look, held ending. Cases are the faults the person
found in the #8 delivery: names as subtitle lines, 27 s without music, a gunshot off its shot, peaks, very short shots, a long cut."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from core import ffmpeg_studio, final_qc

try:
    FFMPEG = ffmpeg_studio.find_ffmpeg()
except ffmpeg_studio.FFmpegNotFound:  # pragma: no cover
    FFMPEG = None
NEEDS_FFMPEG = unittest.skipUnless(FFMPEG, "cần ffmpeg")

SRT_8 = """1
00:00:00,200 --> 00:00:01,000
KELLY

2
00:00:01,380 --> 00:00:03,730
Anh thật sự… chọn anh ấy sao?

3
00:00:28,700 --> 00:00:29,380
Ừ.

4
00:00:45,960 --> 00:00:46,950
Kenta!
"""


class ChecksTests(unittest.TestCase):
    def test_a_name_alone_is_not_a_subtitle_line(self):
        issues = final_qc.check_srt(SRT_8, ["KELLY", "KENTA", "MAXIM"])
        self.assertEqual([(i["code"], i["at"]) for i in issues], [("srt_not_dialogue", 0.2)])     # "Kenta!" and "Ừ." are dialogue

    def test_length_against_the_shot_list(self):
        self.assertEqual(final_qc.check_length(63.7, 66.0), [])
        self.assertEqual(final_qc.check_length(63.7, 72.0)[0]["level"], "warn")
        self.assertEqual(final_qc.check_length(63.7, 83.0)[0]["level"], "block")                # #8: +30 %

    def test_a_long_music_hole_blocks_and_an_automatic_return_is_shown(self):
        issues = final_qc.check_music({"sound_intent": {"off": [(36.8, 64.0), (5.0, 9.0)], "auto_in": [44.8]}})
        self.assertEqual([(i["code"], i["level"]) for i in issues], [("music_hole", "block"), ("music_auto_in", "warn")])

    def test_peaks(self):
        self.assertEqual(final_qc.check_peak({"true_peak_dbfs": -0.4})[0]["level"], "block")
        self.assertEqual(final_qc.check_peak({"true_peak_dbfs": -1.2})[0]["level"], "warn")
        self.assertEqual(final_qc.check_peak({"true_peak_dbfs": -2.0}), [])
        self.assertEqual(final_qc.check_peak(None), [])

    def test_an_ai_effect_without_its_shot_blocks_and_one_over_a_line_is_shown(self):
        items = [{"kind": "tts", "use": True, "start": 41.37, "duration_ms": 2920},
                 {"kind": "sound_effect", "use": True, "label": "AI: Intervention Gun Shot", "start": 43.28, "duration_ms": 2100},
                 {"kind": "sound_effect", "use": True, "label": "AI: Whoosh", "start": 6.0, "duration_ms": 400, "anchor_idx": 5, "offset": 0}]
        codes = [(i["code"], i["level"]) for i in final_qc.check_effects(items)]
        self.assertEqual(codes, [("sfx_unanchored", "block"), ("sfx_over_speech", "warn")])

    def test_very_short_shots(self):
        issues = final_qc.check_short_shots([{"idx": 16, "seconds": 2.8}, {"idx": 17, "seconds": 0.46}, {"idx": 18, "seconds": 1.0}])
        self.assertEqual([(i["code"], i["at"]) for i in issues], [("short_shot", 2.8)])

    def test_summary_text(self):
        self.assertIn("không có lỗi", final_qc.summary({"ok": True, "blocks": 0, "warns": 0, "issues": []}))
        res = {"ok": False, "blocks": 1, "warns": 0, "issues": [final_qc._issue("peak", "block", "đỉnh")]}
        self.assertTrue(final_qc.summary(res).startswith("❌ Kiểm bản dựng: 1 lỗi chặn"))


class RunTests(unittest.TestCase):
    def test_run_reads_the_render_manifest_and_the_project(self):
        import json
        from core import delivery
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("qc")
        for i, secs in enumerate((2.0, 0.5, 2.0), 1):
            sid = p.create_scene(pid, i, f"s{i}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"duration_s": secs}), sid))
        p.conn.commit()
        self.assertEqual(final_qc.run(p, pid, tempfile.mkdtemp(), frames=False)["issues"][0]["code"], "no_render")
        delivery.record(p, pid, "final", "missing.mp4", None,
                        {"timeline": [{"idx": 1, "seconds": 3.0}, {"idx": 2, "seconds": 0.5}, {"idx": 3, "seconds": 3.0}],
                         "loudness": {"true_peak_dbfs": -0.2}, "sound_intent": {"off": [(1.0, 6.5)]}})
        res = final_qc.run(p, pid, tempfile.mkdtemp(), frames=False)
        self.assertEqual(sorted(i["code"] for i in res["issues"]), ["length", "peak", "short_shot"])
        self.assertEqual(res["blocks"], 2)                    # 6,5 s vs 4,5 s planned (+44 %) and the peak
        self.assertFalse(res["ok"])


@NEEDS_FFMPEG
class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _clip(self, name, seconds, audio="sine=frequency=440"):
        path = os.path.join(self.tmp, name)
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x3060C0:s=180x320:d={seconds}"]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"{audio}:duration={seconds}", "-shortest"]
        subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", path], check=True)
        return path

    def _pixel(self, path, t):
        png = os.path.join(self.tmp, f"f{t}.png")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(t), "-i", path, "-frames:v", "1", png], check=True)
        from PIL import Image
        return Image.open(png).convert("RGB").getpixel((90, 160))

    def test_a_flashback_is_warm_washed_out_and_flashes_white(self):
        src = self._clip("fb.mp4", 2.0)
        out = ffmpeg_studio.add_flashback(src, os.path.join(self.tmp, "fb_out.mp4"), 2.0)
        first, mid, plain = self._pixel(out, 0.0), self._pixel(out, 1.0), self._pixel(src, 1.0)
        self.assertGreater(min(first), 200)                                    # white flash in
        self.assertGreater(mid[0] - mid[2], plain[0] - plain[2])               # warmer than the plain blue clip
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), 2.0, delta=0.15)

    def test_the_last_frame_is_held(self):
        src = self._clip("end.mp4", 1.0)
        out = ffmpeg_studio.hold_last_frame(src, os.path.join(self.tmp, "end_out.mp4"), 1.5)
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), 2.5, delta=0.15)

    def test_hold_end_only_with_the_feature_and_only_when_short(self):
        from core import delivery
        src = self._clip("last.mp4", 1.0)
        paths, durations = [src], [1.0]
        with mock.patch.dict(os.environ, {"FEATURE_END_HOLD": "0"}):
            self.assertIsNone(delivery._hold_end(paths, durations, self.tmp))
        with mock.patch.dict(os.environ, {"FEATURE_END_HOLD": "1"}):
            self.assertEqual(delivery._hold_end(paths, durations, self.tmp), {"held_s": 1.5})
            self.assertEqual(durations, [2.5])
            self.assertNotEqual(paths[0], src)
            self.assertIsNone(delivery._hold_end([src], [3.0], self.tmp))

    def test_the_music_goes_on_after_the_last_ducked_line(self):
        """Trial #8 (2026-09-28): the ducked music stopped with the last voice line (79,6 s → end silent)."""
        bed = self._clip("bed.mp4", 6.0, audio="sine=frequency=220")
        voice = os.path.join(self.tmp, "v.wav")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=880:duration=1", voice], check=True)
        out = os.path.join(self.tmp, "mix.mp4")
        ffmpeg_studio.run(ffmpeg_studio.build_extras_mix_cmd(bed, [{"path": voice, "start": 1.0, "volume": 1.0}], out, has_audio=True,
                                                             ffmpeg=FFMPEG, duck=True))
        proc = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-ss", "4.5", "-t", "1", "-i", out, "-af", "volumedetect", "-f", "null", "-"],
                              capture_output=True, text=True)
        mean = float(proc.stderr.split("mean_volume:")[1].split("dB")[0])
        self.assertGreater(mean, -40.0)

    def test_a_hole_in_the_mix_is_found(self):
        loud = self._clip("a.mp4", 2.0)
        quiet = self._clip("b.mp4", 4.0, audio="anullsrc=r=48000:cl=mono")
        tail = self._clip("c.mp4", 3.0)
        lst = os.path.join(self.tmp, "l.txt")
        with open(lst, "w") as f:
            f.write("".join(f"file '{p}'\n" for p in (loud, quiet, tail)))
        joined = os.path.join(self.tmp, "j.mp4")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "copy", "-c:a", "aac", joined],
                       check=True)
        spans = final_qc.silent_spans(joined)
        self.assertEqual(len(spans), 1)
        self.assertAlmostEqual(spans[0][0], 2.0, delta=0.6)
        self.assertGreaterEqual(spans[0][1] - spans[0][0], 3.0)


if __name__ == "__main__":
    unittest.main()
