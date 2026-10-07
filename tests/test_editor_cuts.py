"""D1 J-cut, D6 music breath before a turn, D13 viewer check sheet (knowledge/editor/editing.md E1, E4, E9)."""
import json
import os
import subprocess
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np

from core import ffmpeg_studio, viewer_check


def _ff():
    try:
        return ffmpeg_studio.find_ffmpeg()
    except ffmpeg_studio.FFmpegNotFound:
        raise unittest.SkipTest("no ffmpeg")


class BreathTests(unittest.TestCase):
    def test_the_music_goes_quiet_just_before_the_turn(self):
        ff = _ff()
        d = tempfile.mkdtemp()
        src, out = os.path.join(d, "m.wav"), os.path.join(d, "o.wav")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=4", src], check=True)
        chain = "volume=1" + ffmpeg_studio.breath_filter([2.0])
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", src, "-af", chain, out], check=True)
        with wave.open(out) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
        rms = lambda a, b: float(np.sqrt(np.mean(x[int(a * sr):int(b * sr)] ** 2)))  # noqa: E731
        self.assertLess(rms(1.5, 1.95), rms(0.5, 1.2) * 0.1)                   # ~-26 dB in the 0,6 s before the turn
        self.assertGreater(rms(2.1, 2.8), rms(0.5, 1.2) * 0.8)                 # back on the turn
        self.assertEqual(ffmpeg_studio.breath_filter([]), "")

    def test_the_twist_is_found_on_the_render_timeline(self):
        from core import delivery
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("twist")
        for idx, heading in ((1, "CẢNH 1 – 0–8 GIÂY"), (2, "TWIST – 44–50 GIÂY")):
            p.conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,?,?,?,?)", (pid, idx, heading, "", "{}"))
        rows = []
        for idx, sc in ((1, 1), (2, 1), (3, 2)):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": sc, "shot_no": idx}), sid))
            rows.append({"scene_id": sid, "path": f"{idx}.mp4"})
        p.conn.commit()
        self.assertEqual(delivery.twist_times(p, pid, rows, [3.0, 2.5, 4.0]), [5.5])
        self.assertEqual(delivery.twist_times(p, pid, rows, [3.0, 2.5, 4.0], "crossfade", 0.5), [4.5])


    def test_the_frame_shakes_where_a_marked_shot_starts(self):
        """07/10 Khủng Long Đỏ: shake on the "hô biến" shots without an impact sound."""
        from core import delivery
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("shake")
        rows = []
        for idx, mark in ((1, False), (2, True), (3, True)):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": idx, **({"shake_in": True} if mark else {})}), sid))
            rows.append({"scene_id": sid, "path": f"{idx}.mp4"})
        p.conn.commit()
        self.assertEqual(delivery.shake_in_times(p, rows, [3.0, 2.5, 4.0]), [3.0, 5.5])
        self.assertEqual(delivery.shake_in_times(p, rows, [3.0, 2.5, 4.0], "crossfade", 0.5), [2.5, 4.5])


class MusicStartSettingTests(unittest.TestCase):
    def test_the_music_start_is_saved_and_changes_the_render_hash(self):
        from core import delivery
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("music start")
        before = delivery.render_hash(delivery.get_settings(p, pid))
        delivery.save_settings(p, pid, dict(delivery.get_settings(p, pid), music_start=16))
        s = delivery.get_settings(p, pid)
        self.assertEqual(s["music_start"], 16.0)
        self.assertNotEqual(delivery.render_hash(s), before)
        delivery.save_settings(p, pid, dict(s, music_start=0))
        self.assertEqual(delivery.render_hash(delivery.get_settings(p, pid)), before)   # 0 = the old renders stay current


class SecondMusicTests(unittest.TestCase):
    """07/10 Khủng Long Đỏ: one music for the room scene (0–17 s), the dance's own song from 17.04 s — the edit held only one."""

    def test_the_first_music_stops_where_the_second_comes_in(self):
        from core import ffmpeg_studio
        cmd = " ".join(ffmpeg_studio.build_mux_music_cmd("v", "m", "o", 51.5, fade=1.5, end=17.04))
        self.assertIn("atrim=0:17.04", cmd)
        self.assertIn("afade=t=out:st=16.74:d=0.3", cmd)                    # a short fade at the hand-over, no hole

    def test_the_second_music_is_cut_to_the_rest_of_the_film(self):
        import subprocess
        import tempfile
        from core import delivery, ffmpeg_studio
        d = tempfile.mkdtemp()
        song = os.path.join(d, "s.wav")
        subprocess.run([ffmpeg_studio.find_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=40", song],
                       check=True)
        e = delivery._second_music_extra(song, 17.04, 51.5, 0.6, d)
        self.assertEqual((e["start"], e["volume"]), (17.04, 0.6))
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(e["path"]), 34.46, delta=0.05)

    def test_second_music_and_its_start_are_kept_by_the_project(self):
        import tempfile
        from core import delivery
        from core.db import connect
        from core.pipeline import Pipeline
        d = tempfile.mkdtemp()
        p = Pipeline(connect())
        pid = p.create_project("m2")
        self.assertIsNone(delivery.second_music(d, pid))
        open(os.path.join(delivery.second_music_dir(d, pid), "second.m4a"), "wb").write(b"x")
        self.assertTrue(delivery.second_music(d, pid).endswith("second.m4a"))
        delivery.save_settings(p, pid, dict(delivery.get_settings(p, pid), music2_start=17.04))
        self.assertEqual(delivery.get_settings(p, pid)["music2_start"], 17.04)


class JCutTests(unittest.TestCase):
    def _items(self, data):
        from core import audio_lib
        return audio_lib.load(audio_lib.assets_dir(data, self.pid))

    def test_a_new_speaker_comes_in_before_the_cut_only_with_the_feature(self):
        from core import audio_lib, voice
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        self.pid = pid = p.create_project("j")
        data = tempfile.mkdtemp()
        sids = [p.create_scene(pid, i, f"s{i}") for i in (1, 2)]
        directory = audio_lib.assets_dir(data, pid)
        os.makedirs(directory, exist_ok=True)
        clips = []
        for i, (sid, who) in enumerate(zip(sids, ("KELLY", "KENTA")), 1):
            audio_lib._save(directory, audio_lib.load(directory) + [
                {"kind": "tts", "scene_id": sid, "line": 1, "speaker": who, "state": "succeeded", "file": f"t{i}.mp3",
                 "duration_ms": 1000, "dialogue": True, "label": who}])
            clips.append(os.path.join(data, f"{i}.mp4"))
        rows = [{"idx": i, "scene_id": sid, "path": c, "requested_sec": 3.0, "usable": True} for i, (sid, c) in enumerate(zip(sids, clips), 1)]
        with mock.patch("core.final_cut.collect_clips_for_render", return_value=rows):
            with mock.patch.dict(os.environ, {"FEATURE_J_CUT": "0"}):
                voice.place_on_timeline(p.conn, pid, data, durations=[3.0, 3.0])
                starts = [e["start"] for e in self._items(data)]
            self.assertEqual(starts, [voice.LEAD, 3.0 + voice.LEAD])
            with mock.patch.dict(os.environ, {"FEATURE_J_CUT": "1"}):
                voice.place_on_timeline(p.conn, pid, data, durations=[3.0, 3.0])
                starts = [e["start"] for e in self._items(data)]
            self.assertEqual(starts, [voice.LEAD, 3.0 - voice.J_LEAD])            # Kenta heard 0,25 s before his shot


class RealRenderTests(unittest.TestCase):
    """delivery.render end to end with real ffmpeg clips — a helper put under the render lock by mistake (GĐ4 after-work, e0c82ad)
    broke "▶ Dựng video cuối" while every test passed, because no test rendered for real."""

    def test_render_measures_loudness_and_colour_and_writes_the_file(self):
        from core import delivery, final_cut
        from core.db import connect
        from core.pipeline import Pipeline
        ff = _ff()
        data = tempfile.mkdtemp()
        p = Pipeline(connect())
        pid = p.create_project("render", aspect="9:16")
        for idx, colour in ((1, "0x808080"), (2, "0x998066")):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                           (json.dumps({"story_scene": 1, "shot_no": idx, "size": "MS", "location": "tháp"}), sid))
            path = final_cut.clip_path(data, pid, idx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=270x480:d=1.5", "-f", "lavfi",
                            "-i", "sine=frequency=440:duration=1.5", "-shortest", "-pix_fmt", "yuv420p", "-c:a", "aac", path], check=True)
        p.conn.commit()
        settings = dict(delivery.get_settings(p, pid), keep_audio=True)
        res = delivery.render(p, pid, data, music_path=None, settings=settings)
        self.assertTrue(os.path.exists(res["path"]))
        man = json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()["manifest"])
        self.assertIsNotNone(man["loudness"]["lufs"])
        self.assertEqual(len(man["color_match"]), 1)                              # shot 2 measured against shot 1


class EffectsTests(unittest.TestCase):
    def test_a_hit_shakes_the_frame_and_keeps_its_size(self):
        ff = _ff()
        d = tempfile.mkdtemp()
        src, out = os.path.join(d, "v.mp4"), os.path.join(d, "s.mp4")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=270x480:d=2", "-pix_fmt", "yuv420p", src], check=True)
        ffmpeg_studio.add_shake(src, out, [0.5], ff)
        self.assertEqual(ffmpeg_studio.probe_size(out), (270, 480))
        self.assertEqual(ffmpeg_studio.shake_filter([]), "")

    def test_only_hit_effects_give_a_shake(self):
        from core import audio_lib, delivery
        d = tempfile.mkdtemp()
        audio_lib._save(d, [{"kind": "sound_effect", "label": "AI: impact punch", "start": 3.2, "use": True, "state": "succeeded"},
                            {"kind": "sound_effect", "label": "AI: wind whoosh", "start": 1.0, "use": True, "state": "succeeded"},
                            {"kind": "sound_effect", "label": "Nổ lớn", "start": 5.0, "use": False, "state": "succeeded"}])
        self.assertEqual(delivery.impact_times(d), [3.2])

    def test_no_name_cards_and_no_hud_line_in_the_srt(self):
        """Trial #8 (2026-09-28, người dùng): character name cards removed; the .srt holds spoken lines only."""
        from core import subtitles
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("names")
        for idx, cast in ((1, ["KELLY"]), (2, ["KELLY", "KENTA"])):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": idx, "characters": cast}), sid))
        p.conn.commit()
        timeline = [{"idx": 1, "seconds": 3.0}, {"idx": 2, "seconds": 3.0}]
        with mock.patch.dict(os.environ, {"FEATURE_NAME_CARDS": "1"}):          # an old dashboard.env line changes nothing
            self.assertEqual(subtitles.build_cues(p, tempfile.mkdtemp(), pid, timeline=timeline), [])
        self.assertNotIn("name_cards", __import__("core.features", fromlist=["FEATURES"]).FEATURES)
        srt = subtitles.to_srt([subtitles.Cue(0.2, 1.0, "KELLY", subtitles.HUD, 1), subtitles.Cue(1.3, 3.0, "Anh thật sự…", "KELLY", 1)])
        self.assertNotIn("KELLY\n", srt)
        self.assertTrue(srt.startswith("1\n00:00:01,300"))


class AmbienceTests(unittest.TestCase):
    def setUp(self):
        from core.db import connect
        self.conn = connect()
        self.dir = tempfile.mkdtemp()
        for i, (name, heard, dur) in enumerate([("Busy City Street", "", 139.0), ("Bird Ambience", "", 115.0),
                                                ("Tiếng Sấm Sét HD", "Thunderstorm 1.00; Rain 0.9", 164.0),
                                                ("air horn violin", "Air horn 0.78; Wind instrument 0.29", 22.0),
                                                ("03 Kevin MacLeod - Crunk Knight", "", 120.0), ("Short rain", "Rain 0.9", 3.0)], 1):
            path = os.path.join(self.dir, f"{i}.wav")
            open(path, "wb").close()
            label = heard.split(" ")[0].rstrip(";") if heard else None
            self.conn.execute("INSERT INTO sounds (id, source_id, path, name, kind, duration, heard, heard_label, heard_score, voice)"
                              " VALUES (?,1,?,?,?,?,?,?,?,0)", (i, path, name, "sfx", dur, heard, label, 0.8 if label else None))
        self.conn.commit()

    def test_weather_then_time_then_place(self):
        from core import ambience
        self.assertEqual(ambience.choose(self.conn, {"weather": "storm", "location": "phố"})["name"], "Tiếng Sấm Sét HD")
        self.assertIsNone(ambience.choose(self.conn, {"weather": "fog"}))                        # never "air horn violin" for wind
        self.assertIsNone(ambience.choose(self.conn, {"time": "night", "location": "quảng trường phố"}))   # no "Crunk Knight"
        self.assertEqual(ambience.choose(self.conn, {"time": "day", "location": "Đảo Quân Sự — khu nhà"})["name"], "Busy City Street")
        self.assertEqual(ambience.choose(self.conn, {"location": "rừng thông"})["name"], "Bird Ambience")
        self.assertIsNone(ambience.choose(self.conn, {"location": "phòng kín"}))                     # nothing fits: no random sound

    def test_a_bed_never_holds_the_music_down(self):
        cmd = ffmpeg_studio.build_extras_mix_cmd("v.mp4", [{"path": "voice.wav", "start": 1, "volume": 1},
                                                            {"path": "bed.wav", "start": 0, "volume": 0.12, "key": False}],
                                                 "o.mp4", has_audio=True, duck=True)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("[e0]amix=inputs=1", graph)                                 # only the voice is the ducking key
        self.assertIn("[bed][vm][e1]amix=inputs=3", graph)                        # the bed is still in the mix


class MotionTrimTests(unittest.TestCase):
    def test_a_late_action_moves_the_cut_start_only_with_the_feature(self):
        from core import shots
        from core.db import connect
        from core.pipeline import Pipeline
        ff = _ff()
        d = tempfile.mkdtemp()
        raw = os.path.join(d, "r.mp4")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=96x168:d=3", "-f", "lavfi", "-i",
                        "color=c=white:s=24x24:d=3", "-filter_complex", "[0][1]overlay=x='if(gt(t,1.4),(t-1.4)*50,0)':y=60",
                        "-pix_fmt", "yuv420p", raw], check=True)             # still for 1,4 s, then a white square slides across
        p = Pipeline(connect())
        pid = p.create_project("m")
        sid = p.create_scene(pid, 1, "s1")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "role": "reaction"}), sid))
        p.conn.commit()
        with mock.patch.dict(os.environ, {"FEATURE_MOTION_TRIM": "1"}):
            start = shots.motion_start(p.conn, sid, raw, 1.0, 3.0)
            self.assertGreater(start, 0.3)
            self.assertLessEqual(start, shots.MOTION_MAX_SHIFT)
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "role": "dialogue"}), sid))
            self.assertEqual(shots.motion_start(p.conn, sid, raw, 1.0, 3.0), 0.0)     # a spoken shot keeps its seconds
        with mock.patch.dict(os.environ, {"FEATURE_MOTION_TRIM": "0"}):
            self.assertEqual(shots.motion_start(p.conn, sid, raw, 1.0, 3.0), 0.0)


class ViewerCheckTests(unittest.TestCase):
    def test_faces_under_the_app_bands_are_named(self):
        self.assertEqual(viewer_check.hidden_faces([(0.4, 0.02, 0.6, 0.12)]), ["top"])
        self.assertEqual(viewer_check.hidden_faces([(0.4, 0.30, 0.6, 0.45)]), [])
        self.assertEqual(viewer_check.hidden_faces([(0.4, 0.70, 0.6, 0.85)]), ["bottom"])
        self.assertEqual(viewer_check.hidden_faces([(0.85, 0.30, 0.98, 0.45)]), ["right"])       # behind the like / share column
        self.assertEqual(viewer_check.hidden_faces([(0.4, 0.02, 0.6, 0.12)], vertical=False), [])   # a 16:9 video has no app bands

    def test_a_sheet_is_made_from_a_video(self):
        ff = _ff()
        d = tempfile.mkdtemp()
        video = os.path.join(d, "v.mp4")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=270x480:d=2", "-pix_fmt", "yuv420p", video],
                       check=True)
        res = viewer_check.sheet(video, os.path.join(d, "sheet.png"), ff, count=4)
        self.assertTrue(os.path.exists(res["path"]))
        self.assertEqual(len(res["frames"]), 4)


if __name__ == "__main__":
    unittest.main()
