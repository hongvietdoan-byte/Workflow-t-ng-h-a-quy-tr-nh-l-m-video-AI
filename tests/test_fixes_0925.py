"""Fixes after the user watched trial 2A (2026-09-25): Kenta's voice cut at the end, black "void" opening, a Clock Tower that did not look
like Free Fire's, no music following the cut; plus Blender from the Microsoft Store."""
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import assets, ffmpeg_studio, music_timing, plates3d, voice, voice_check


class VoiceTailTests(unittest.TestCase):
    def test_a_loud_last_80_ms_is_a_cut_line(self):
        self.assertTrue(voice_check.tail_problems(-1.1))          # Kenta, "Không liên quan đến ông." (0,64 s)
        self.assertTrue(voice_check.tail_problems(-12.1))         # Kenta, "Bây giờ chưa được."
        self.assertEqual(voice_check.tail_problems(-35.0), [])    # the redone line
        self.assertEqual(voice_check.tail_problems(None), [])

    def test_speaking_too_fast_is_flagged_at_the_new_limit(self):
        self.assertTrue(voice_check.length_problems("Không liên quan đến ông.", 0.64, []))   # 7,8 syllables/s passed the old limit (8)
        self.assertEqual(voice_check.length_problems("Không liên quan đến ông.", 1.04, []), [])

    def test_a_redo_ends_the_line_with_an_ellipsis(self):
        self.assertEqual(voice.slow_end("Không liên quan đến ông."), "Không liên quan đến ông…")
        self.assertEqual(voice.slow_end("Em hiểu rồi…"), "Em hiểu rồi…")
        self.assertEqual(voice.slow_end("Kenta!"), "Kenta!…")


class MusicTimingTests(unittest.TestCase):
    def test_the_tempo_puts_the_turns_on_bar_lines(self):
        bpm, err = music_timing.choose_bpm([8.6])
        self.assertLess(err, 0.05)
        bar = 240.0 / bpm
        self.assertAlmostEqual(8.6 / bar, round(8.6 / bar), delta=0.05)

    def test_grief_is_not_read_as_action(self):
        sad = {"mood": "heartbroken, tense, restrained grief", "intent": "", "heading": "CINEMATIC MỞ ĐẦU", "lighting": "night"}
        game = {"mood": "tense curiosity under casual banter", "intent": "", "heading": "CẢNH 1", "lighting": "day"}
        self.assertIn("piano", music_timing._style(sad))
        self.assertIn("percussion", music_timing._style(game))

    def test_the_music_is_asked_longer_than_the_film(self):
        self.assertEqual(music_timing.TAIL_PAD_MS, 4000)      # the model fades its last seconds; the mix cuts at the film's end


class LandmarkTests(unittest.TestCase):
    def test_close_and_medium_shots_get_the_landmark_wide_and_ecu_do_not(self):
        place = {"images": [{"role": "top_down", "path": "a"}, {"role": "detail", "path": "tower"}, {"role": "eye_level", "path": "plate"}]}
        self.assertEqual(assets.location_landmark(None, place, {"size": "MS"})["path"], "tower")
        self.assertEqual(assets.location_landmark(None, place, {"size": "CU"})["path"], "tower")
        self.assertIsNone(assets.location_landmark(None, place, {"size": "WS"}))      # a wide shot gets the eye-level plate instead
        self.assertIsNone(assets.location_landmark(None, place, {"size": "ECU"}))     # no background to speak of

    def test_an_indoor_picture_is_never_the_landmark(self):
        """30/09 thử #11: the indoor room of the 3D Kho went out as the Clock Tower's landmark and the shot moved indoors."""
        place = {"images": [{"role": "interior", "path": "room"}, {"role": "low_angle", "path": "tower_up"}, {"role": "eye_level", "path": "p"}]}
        self.assertEqual(assets.location_landmark(None, place, {"size": "MS"})["path"], "tower_up")
        self.assertIsNone(assets.location_landmark(None, {"images": [{"role": "interior", "path": "room"}]}, {"size": "MS"}))

    def test_the_note_forbids_copying_the_landmark_picture_s_camera(self):
        note = assets.reference_note([{"path": "x", "label": "Tháp Đồng Hồ", "role": "landmark"}])
        self.assertIn("LANDMARK", note)
        self.assertIn("NOT this picture's camera angle", note)


class DuckingTests(unittest.TestCase):
    def test_voices_press_the_music_down(self):
        cmd = ffmpeg_studio.build_extras_mix_cmd("v.mp4", [{"path": "a.mp3", "start": 1}], "o.mp4", has_audio=True, duck=True)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("sidechaincompress", graph)
        self.assertIn(ffmpeg_studio.PEAK_LIMIT, graph)
        plain = ffmpeg_studio.build_extras_mix_cmd("v.mp4", [{"path": "a.mp3", "start": 1}], "o.mp4", has_audio=True)
        self.assertNotIn("sidechaincompress", plain[plain.index("-filter_complex") + 1])

    @unittest.skipUnless(os.environ.get("FFMPEG_PATH") or subprocess.run(["where" if os.name == "nt" else "which", "ffmpeg"],
                                                                        capture_output=True).returncode == 0, "no ffmpeg")
    def test_real_ffmpeg_accepts_the_ducking_graph(self):
        ff = ffmpeg_studio.find_ffmpeg()
        d = tempfile.mkdtemp()
        v, a, o = (os.path.join(d, n) for n in ("v.mp4", "a.wav", "o.mp4"))
        subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=2", "-f", "lavfi", "-i",
                        "sine=f=220:d=2", "-shortest", "-c:v", "libx264", "-c:a", "aac", v], check=True)
        subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=660:d=1", a], check=True)
        ffmpeg_studio.run(ffmpeg_studio.build_extras_mix_cmd(v, [{"path": a, "start": 0.5}], o, has_audio=True, ffmpeg=ff, duck=True))
        self.assertTrue(os.path.getsize(o) > 0)


class GameNoticeTests(unittest.TestCase):
    """on_screen_text ("HỆ THỐNG: Maxim đã bị hạ.") was stored on the shot but never reached the video."""

    def setUp(self):
        import json
        from core.db import connect
        from core.pipeline import Pipeline
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        sid = self.p.create_scene(self.pid, 1, "twist")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "story_scene": 5, "dialogue": [],
                                                                               "on_screen_text": ["Maxim đã bị hạ."]}), sid))
        self.p.conn.commit()

    def test_the_notice_becomes_a_top_cue_not_a_subtitle(self):
        from core import subtitles
        cues = subtitles.build_cues(self.p, tempfile.mkdtemp(), self.pid, timeline=[{"idx": 1, "seconds": 1.5}])
        self.assertEqual([(c.text, c.speaker) for c in cues], [("Maxim đã bị hạ.", subtitles.HUD)])
        font = subtitles.Font("x.ttf", "GFF Latin Bold", "x", True)
        ass = subtitles.to_ass(cues, 1080, 1920, font, show_speaker=True, by_speaker=True)
        self.assertIn("Style: Hud,", ass)
        self.assertIn(",Hud,,0,0,0,,Maxim đã bị hạ.", ass)          # no "__hud__:" prefix, own style
        self.assertEqual(subtitles.density(cues), [])
        self.assertNotIn("__HUD__", subtitles.to_srt(cues, show_speaker=True))


class StoreBlenderTests(unittest.TestCase):
    def test_the_store_package_is_found_when_nothing_else_is(self):
        plates3d._STORE_CACHE.clear()                  # the answer is remembered per process (02/10): start clean, leave clean
        self.addCleanup(plates3d._STORE_CACHE.clear)
        fake = mock.Mock(stdout="BlenderFoundation.Blender_abc|C:\\Program Files\\WindowsApps\\Blender_5\n")
        with mock.patch.object(plates3d.os, "name", "nt"), mock.patch.object(plates3d.subprocess, "run", return_value=fake):
            got = plates3d.store_blender()
        self.assertTrue(got.startswith(plates3d.STORE + "BlenderFoundation.Blender_abc|"))
        self.assertTrue(got.endswith(os.path.join("Blender", "blender.exe")))


if __name__ == "__main__":
    unittest.main()
