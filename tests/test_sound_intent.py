"""2026-09-26 — two reference documents read into the pipeline:
- "AI Director's Master Handbook" (director.md Đ2, Đ3, Đ9): the Director's sound intent per shot (`sound`: music cut / in / breath + the
  sounds the moment needs) reaches the sound designer and — with the feature `sound_intent` — the music of the render; a strong moment
  needs a shot long enough to land.
- "Free Fire In-Game Visual Replication Plan v1.0" (knowledge/ff_gameplay_visual.md): the Director reads what Free Fire gameplay looks
  like; an in-game project keeps realism words ("cinematic", "photorealistic", "bokeh"…) out of what goes to the picture / video model,
  and says what it removed."""
import json
import tempfile
import unittest

from core import director_report, ffmpeg_studio, looks, performance, prompts, sfx_plan, shots, sound_intent
from core.db import connect
from core.pipeline import Pipeline


def _shot(**kw):
    s = {"size": "MS", "angle": "eye", "camera_move": "static", "role": "action", "duration_s": 3.0, "action": "Kelly chạy",
         "image_prompt": "Kelly runs", "characters": ["KELLY"]}
    s.update(kw)
    return s


class CleanTests(unittest.TestCase):
    def test_a_usable_intent_is_kept_and_keep_alone_is_nothing(self):
        sound, problems = sound_intent.clean({"music": "Cut", "sfx": ["heavy breathing"], "why": "im lặng để câu nghe lỏm rơi nặng"})
        self.assertEqual(sound, {"music": "cut", "sfx": ["heavy breathing"], "why": "im lặng để câu nghe lỏm rơi nặng"})
        self.assertEqual(problems, [])
        self.assertEqual(sound_intent.clean({"music": "keep"}), (None, []))
        self.assertEqual(sound_intent.clean({"music": "keep", "why": "không có gì"}), (None, []))   # a reason alone does nothing

    def test_bad_parts_are_dropped_and_reported_never_refused(self):
        sound, problems = sound_intent.clean({"music": "fade", "sfx": ["a", "b", "c", "d"]})
        self.assertEqual(sound, {"sfx": ["a", "b", "c"]})
        self.assertEqual(len(problems), 2)
        self.assertEqual(sound_intent.clean("loud")[0], None)
        self.assertEqual(sound_intent.clean({"sfx": "gun cock click"})[0], {"sfx": ["gun cock click"]})

    def test_the_shot_row_keeps_the_intent(self):
        scene = {"idx": 1, "location": "Tháp", "characters": ["KELLY"]}
        data = shots.shot_data(scene, _shot(sound={"music": "breath", "sfx": ["swallow"], "why": "cú ngoặt"}), 1)
        self.assertEqual(data["sound"], {"music": "breath", "sfx": ["swallow"], "why": "cú ngoặt"})
        self.assertNotIn("sound", shots.shot_data(scene, _shot(sound={"music": "keep"}), 2))


class WarningTests(unittest.TestCase):
    def test_a_plan_the_code_can_see_is_wrong_is_reported(self):
        plan = [_shot(sound={"music": "breath"}), _shot(sound={"music": "in"}), _shot(sound={"music": "cut"}),
                _shot(sound={"music": "cut"}), _shot(), _shot()]
        text = " | ".join(sound_intent.warnings(plan))
        self.assertIn("shot 1: music 'breath'", text)
        self.assertIn("shot 2: music 'in'", text)
        self.assertIn("shot 4: music 'cut' khi nhạc đã tắt", text)
        self.assertIn("quá nửa phim không nhạc", text)          # cut at shot 3, never back: 12 of 18 s

    def test_a_peak_without_any_sound_intent_is_pointed_out(self):
        peak = _shot(performance={"intensity": 5, "face": "jaw drops, eyes wide"})
        self.assertTrue(any("cường độ 5" in w for w in sound_intent.warnings([_shot(), peak])))
        heard = dict(peak, sound={"sfx": ["held breath"]})
        self.assertEqual(sound_intent.warnings([_shot(), heard]), [])

    def test_the_director_report_shows_the_sound_warnings(self):
        obj = {"scenes": [{"idx": 1, "shots": [_shot(sound={"music": "in"}), _shot()]}]}
        report = director_report.report(obj, "")
        self.assertTrue(report["sound"])
        self.assertIn("🔊", director_report.text(report))


class MusicPlanTests(unittest.TestCase):
    def test_silences_land_on_the_render_timeline(self):
        datas = [{}, {"sound": {"music": "cut"}}, {}, {"sound": {"music": "in"}}, {"sound": {"music": "breath"}}]
        plan = sound_intent.music_plan(datas, [2.0, 3.0, 1.5, 2.5, 2.0])
        self.assertEqual(plan["off"], [(2.0, 6.5)])
        self.assertEqual(plan["breaths"], [9.0])
        self.assertEqual(plan["planned"], 3)

    def test_an_overlapping_transition_shortens_the_timeline_and_a_missing_in_runs_to_the_end(self):
        datas = [{}, {"sound": {"music": "cut"}}, {}]
        plan = sound_intent.music_plan(datas, [3.0, 3.0, 3.0], "crossfade", 1.0, ("crossfade",))
        self.assertEqual(plan["off"], [(2.0, 7.0)])            # starts 3 − 1; total 9 − 2 overlaps

    def test_a_silence_never_runs_longer_than_the_cap_and_a_repeated_cut_opens_a_new_one(self):
        """Trial #8 (2026-09-28): cut at shot 16, cut again at 21/23/25/26/27, in at 28 → 27 s without music."""
        m = lambda v: {"sound": {"music": v}}                                                  # noqa: E731
        datas = [{}, m("cut"), {}, {}, {}, {}, m("cut"), {}, m("cut"), m("in"), {}]
        plan = sound_intent.music_plan(datas, [2.0] * 11)
        self.assertEqual(plan["off"], [(2.0, 10.0), (16.0, 18.0)])      # back at 10 s (8 s cap); the cut at 12 s is too soon: ignored
        self.assertEqual((plan["auto_in"], plan["ignored_cuts"]), ([10.0], [12.0]))
        odd = sound_intent.music_plan([{}, m("cut"), {}, {}], [2.0, 5.0, 5.0, 2.0])
        self.assertEqual(odd["off"], [(2.0, 10.0)])                      # back exactly 8 s after it stopped, not at the next cut
        tail = sound_intent.music_plan([{}, m("cut"), {}, {}, {}, {}, {}], [2.0] * 7)
        self.assertEqual((tail["off"], tail["auto_in"]), ([(2.0, 10.0)], [10.0]))           # no "in" at all: still back after 8 s
        self.assertEqual(sound_intent.music_plan(datas, [2.0] * 11, max_off=0)["off"], [(2.0, 18.0)])   # cap off = the old rule
        shots = [dict(d, duration_s=2.0) for d in datas]
        self.assertTrue(any("tự cho nhạc vào lại" in w for w in sound_intent.warnings(shots)))

    def test_the_music_filter_goes_silent_in_the_spans_and_dips_before_breaths(self):
        cmd = ffmpeg_studio.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", 10, breaths=[8.0], music_off=[(2.0, 5.0)])
        chain = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("volume='min(1,", chain)
        env = dict(ffmpeg_studio.music_envelope([8.0], [(2.0, 5.0)]))
        self.assertEqual((env[2.0], env[5.0], env[6.5]), (0.0, 0.0, 1.0))     # silent 2–5 s, back to full over 1,5 s
        self.assertEqual((env[7.4], env[8.0], env[8.05]), (0.05, 0.05, 1.0))  # breath before the turn at 8 s
        plain = ffmpeg_studio.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", 10)
        self.assertNotIn("volume='", plain[plain.index("-filter_complex") + 1])

    def test_a_long_silence_ramps_out_holds_then_creeps_back_softly(self):
        """#8 re-render (người dùng 2026-09-28): the music went off and on with no softness."""
        f = ffmpeg_studio
        env = f.music_envelope([], [(10.0, 18.0)])
        g = lambda t: next(v for k, v in env if k == t)                          # noqa: E731
        self.assertEqual((g(10.0 - f.OFF_FADE), g(10.0), g(10.0 + f.OFF_HOLD)), (1.0, 0.0, 0.0))
        self.assertEqual(g(10.0 + f.OFF_HOLD + f.OFF_RISE), f.OFF_LOW)          # back quietly before the silence ends
        self.assertEqual((g(18.0), g(18.0 + f.IN_FADE)), (f.OFF_LOW, 1.0))
        self.assertTrue(all(0.0 <= v <= 1.0 for _, v in env))

    def test_the_render_reads_the_plan_from_the_shot_rows(self):
        from core import delivery
        p = Pipeline(connect(":memory:"))
        pid = p.create_project("P")
        rows = []
        for idx, sound in enumerate([None, {"music": "cut"}, {"music": "in"}], 1):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"sound": sound} if sound else {}), sid))
            rows.append({"path": f"c{idx}.mp4", "scene_id": sid})
        plan = delivery.sound_plan(p, rows, [2.0, 2.0, 2.0])
        self.assertEqual(plan["off"], [(2.0, 4.0)])


class RealMusicSilenceTests(unittest.TestCase):
    """delivery.render with real ffmpeg: the music really goes silent between the Director's `cut` and `in` (the filter string alone
    proves nothing — ffmpeg has to accept and apply it)."""

    def _mean_db(self, ff, path, start, length):
        import re
        import subprocess
        out = subprocess.run([ff, "-hide_banner", "-ss", str(start), "-t", str(length), "-i", path, "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(re.search(r"mean_volume: (-?[\d.]+) dB", out).group(1))

    def _render(self, flag: str):
        import os
        import subprocess
        from unittest import mock
        from core import delivery, final_cut
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            raise unittest.SkipTest("no ffmpeg")
        data = tempfile.mkdtemp()
        p = Pipeline(connect())
        pid = p.create_project("render", aspect="9:16")
        for idx, sound in enumerate([None, {"music": "cut"}, {"music": "in"}], 1):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(dict({"story_scene": 1, "shot_no": idx, "size": "MS"},
                                                                                 **({"sound": sound} if sound else {}))), sid))
            path = final_cut.clip_path(data, pid, idx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x808080:s=270x480:d=2", "-pix_fmt", "yuv420p",
                            path], check=True)
        p.conn.commit()
        music = os.path.join(data, "m.m4a")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=8", "-c:a", "aac", music], check=True)
        settings = dict(delivery.get_settings(p, pid), keep_audio=False, transition="cut")
        with mock.patch.dict(os.environ, {"FEATURE_SOUND_INTENT": flag}):
            res = delivery.render(p, pid, data, music_path=music, settings=settings)
        man = json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()["manifest"])
        return ff, res["path"], man

    def test_the_music_is_out_from_cut_to_in_when_the_feature_is_on(self):
        ff, path, man = self._render("1")
        self.assertTrue(man["sound_intent"]["applied"])
        self.assertEqual(man["sound_intent"]["off"], [[2.0, 4.0]])
        before, gap, after = (self._mean_db(ff, path, a, 1.2) for a in (0.5, 2.4, 4.4))
        self.assertLess(gap, -60)                          # silence (the encoder leaves only noise)
        self.assertGreater(before, -40)
        self.assertGreater(after, -40)

    def test_off_the_music_plays_on_and_the_manifest_says_what_was_not_applied(self):
        ff, path, man = self._render("0")
        self.assertEqual(man["sound_intent"], {"applied": False, "planned": 2, "why": "cờ sound_intent đang TẮT"})
        self.assertGreater(self._mean_db(ff, path, 2.4, 1.2), -40)


class SoundDesignerTests(unittest.TestCase):
    def test_the_sound_designer_is_told_the_directors_intent(self):
        scenes = [{"idx": 1, "start": 0, "length": 3, "mood": "", "shot": "", "text": "",
                   "sound": {"music": "cut", "sfx": ["gun cock click"], "why": "mối đe dọa"}}]
        prompt = sfx_plan.build_prompt(scenes, [], 3)
        self.assertIn("director_sound", prompt)
        self.assertIn("Ý đồ âm thanh của Đạo diễn", prompt)
        self.assertNotIn("Ý đồ âm thanh của Đạo diễn", sfx_plan.build_prompt([dict(scenes[0], sound=None)], [], 3))

    def test_a_requested_sound_nobody_placed_is_listed(self):
        scenes = [{"idx": 1, "start": 0.0, "length": 3.0, "sound": {"sfx": ["heavy breathing"]}},
                  {"idx": 2, "start": 3.0, "length": 2.0, "sound": {"sfx": ["beep"]}},
                  {"idx": 3, "start": 5.0, "length": 2.0}]
        self.assertEqual(sound_intent.unmet(scenes, [{"at": 1.0}]), [{"idx": 2, "sfx": ["beep"]}])
        self.assertEqual(sound_intent.unmet(scenes, []), [{"idx": 1, "sfx": ["heavy breathing"]}, {"idx": 2, "sfx": ["beep"]}])
        self.assertEqual(sound_intent.unmet(scenes, [{"at": 1.0}, {"at": 2.5}]), [])     # 2.5 is within 0.6 s before shot 2


class HoldTests(unittest.TestCase):
    def test_a_strong_moment_cut_away_at_once_is_reported(self):
        strong = {"intensity": 4, "face": "eyes go wide, breath stops"}
        fast = [_shot(), _shot(duration_s=1.2, performance=strong), _shot(duration_s=1.0, performance=strong), _shot(duration_s=1.5)]
        self.assertTrue(any("chưa kịp thấm" in w for w in performance.warnings(fast)))
        held = fast[:3] + [_shot(duration_s=2.5, role="reaction")]
        self.assertFalse(any("chưa kịp thấm" in w for w in performance.warnings(held)))


class InGameLookTests(unittest.TestCase):
    def test_realism_words_are_removed_only_in_an_in_game_project(self):
        text, removed = looks.clean_prompt({"look": "FF_INGAME"},
                                           "Cinematic still of Kelly by the crates, photorealistic, shallow depth of field, bokeh.")
        self.assertEqual(text, "Kelly by the crates.")
        self.assertEqual(len(removed), 4)
        self.assertEqual(looks.clean_prompt({"look": "FF_INGAME"}, "Kenta, not photorealistic, warm light")[0], "Kenta, warm light")
        self.assertEqual(looks.clean_prompt({"look": "FF_INGAME"}, "an unrealistic dream")[1], [])
        self.assertEqual(looks.clean_prompt({"look": "ANIME"}, "cinematic lighting"), ("cinematic lighting", []))
        self.assertIn("realistic military shooter", looks.image_sentence({"look": "FF_INGAME"}))
        self.assertIn("PUBG", looks.video_negative({"look": "FF_INGAME"}, "blurry"))
        self.assertEqual(looks.video_negative({"look": "ANIME"}, "blurry"), "blurry")

    def test_the_picture_prompt_is_cleaned_and_the_removal_is_recorded(self):
        from core import llm_runner
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        from tests.test_v3 import kenta_project
        p, pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        p.set_project_field(pid, "look", "FF_INGAME")
        row = shots.shots_of(p, pid)[0]
        data = dict(row["data"], image_prompt="cinematic still of Kenta in the hangar, photorealistic, bokeh")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
        p.conn.commit()
        job = p.create_job(row["id"], "image_gen")
        args = ImageRunner(p, MockImageProvider(), tempfile.mkdtemp())._submit_args(p.job(job))
        scene_part = args[0].split("Render style")[0]
        self.assertIn("Kenta in the hangar", scene_part)
        self.assertNotIn("photorealistic", scene_part.lower())
        self.assertNotIn("bokeh", scene_part.lower())
        note = p.conn.execute("SELECT message FROM diag_events WHERE code='look_words_removed'").fetchone()
        self.assertIsNotNone(note)
        self.assertIn("photorealistic", note["message"])

    def test_the_director_reads_what_gameplay_looks_like(self):
        p = Pipeline(connect(":memory:"))
        pid = p.create_project("P")
        p.create_scene(pid, 1, "x")
        bundle = prompts.build_director_bundle(p, pid)
        self.assertIn("Free Fire gameplay thật trông thế nào", bundle)
        self.assertIn("không** phải kho cảnh", bundle)
        self.assertEqual(looks.motion_note(p.project(pid)), "")
        p.set_project_field(pid, "look", "FF_INGAME")
        self.assertIn("KHÔNG viết chữ", looks.motion_note(p.project(pid)))


if __name__ == "__main__":
    unittest.main()
