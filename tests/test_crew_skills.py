"""V4 GĐ4 — the crew's skill books turned into code: the Director's acting (`performance`) and voice direction (`delivery`), the DP's
reason (`why`) and lens (`lens_mm`), the Director report's `tradeoffs` / `script_notes` checks, the location-pack block, the DP's
model limits generated from provider_rules.json, the right safe margin of subtitles."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import director_report, performance, plate_camera, prompts, shots, subtitles, voice_direction
from core.subtitles import Cue, Font

KELLY_SMILE = {"intensity": 3, "face": "lips pressed into a trembling smile, chin tight", "eyes": "wet, fixed on Kenta, blinking fast",
               "body": "shoulders drawn in", "timing": "holds, then looks down", "listener": "Kenta stays still, jaw tight",
               "motive": "cố không khóc trước mặt anh"}


def _shot(**kw):
    s = {"size": "MS", "angle": "eye", "camera_move": "static", "role": "dialogue", "duration_s": 3.0, "action": "Kelly nhìn Kenta",
         "image_prompt": "Kelly faces Kenta", "characters": ["KELLY"], "dialogue": []}
    s.update(kw)
    return s


class PerformanceTests(unittest.TestCase):
    def test_clean_keeps_the_good_parts_and_says_what_it_dropped(self):
        got, problems = performance.clean({"intensity": 9, "face": "  frown ", "eyes": 3})
        self.assertEqual(got, {"face": "frown"})
        self.assertEqual(len(problems), 2)                                       # intensity out of 1–5, eyes not text
        self.assertEqual(performance.clean("sad"), (None, [mock.ANY]))
        self.assertEqual(performance.clean(None), (None, []))

    def test_the_start_frame_gets_face_eyes_body_at_the_stated_strength(self):
        text = performance.image_sentence({"performance": KELLY_SMILE, "characters": ["KELLY", "KENTA"]})
        self.assertIn("intensity 3/5", text)
        self.assertIn("clear but natural", text)
        self.assertIn("trembling smile", text)
        self.assertIn("listener: Kenta stays still", text)                       # the listener is in the frame
        self.assertNotIn("holds, then", text)                                    # timing is for the motion prompt
        self.assertNotIn("cố không khóc", text)                                  # the motive is the reason, not a picture
        alone = performance.image_sentence({"performance": KELLY_SMILE, "characters": ["KELLY"]})
        self.assertNotIn("listener", alone)
        self.assertEqual(performance.image_sentence({}), "")

    def test_warnings_catch_over_and_dead_acting(self):
        plan = [_shot(size="CU", performance={"intensity": 5, "face": "looks sad"}),
                _shot(performance={"intensity": 5, "face": "screams"}), _shot(performance={"intensity": 5, "face": "sobs"}),
                _shot(role="reaction")]
        w = " | ".join(performance.warnings(plan))
        self.assertIn("cường độ 5 ở 3 shot", w)
        self.assertIn("shot 1: face \"looks sad\" chỉ là tên cảm xúc", w)   # a short phrase with an emotion word is caught too
        self.assertIn("thiếu performance: 4", w)
        flat = [_shot(performance={"intensity": 2, "face": "tight jaw"}) for _ in range(6)]
        self.assertIn("shot 1–6: 6 shot liền cùng cường độ 2", " ".join(performance.warnings(flat)))
        broken = flat[:3] + [_shot(performance={"intensity": 4, "face": "tight jaw"})] + flat[:3]
        self.assertFalse(any("phẳng" in x for x in performance.warnings(broken)))
        long_run = [_shot(performance={"intensity": 4, "face": "tight jaw"})] + flat + [_shot(performance={"intensity": 3, "face": "x y"})]
        self.assertTrue(any("shot 2–7" in x for x in performance.warnings(long_run)))   # one different shot no longer hides a run

    def test_a_close_up_shows_the_moment_one_step_smaller(self):
        peak = {"intensity": 5, "face": "tears run, mouth open in a silent sob"}
        self.assertIn("intensity 4/5", performance.image_sentence({"size": "CU", "performance": peak}))
        self.assertIn("intensity 5/5", performance.image_sentence({"size": "MS", "performance": peak}))
        self.assertEqual(performance.shown_intensity({"size": "ECU", "performance": {"intensity": 1}}), 1)
        self.assertEqual(performance.warnings([_shot()]), [])                    # a plan without the field: no noise

    def test_shot_rows_keep_the_new_fields(self):
        scene = {"idx": 1}
        data = shots.shot_data(scene, _shot(performance=KELLY_SMILE, why="qua vai Kenta: giữ trục", lens_mm=85.4,
                                            dialogue=[{"speaker": "KELLY", "text": "Em hiểu rồi…",
                                                       "delivery": {"pace": "slow", "intensity": 2, "pause_before": True}}]), 1)
        self.assertEqual(data["performance"]["intensity"], 3)
        self.assertEqual(data["why"], "qua vai Kenta: giữ trục")
        self.assertEqual(data["lens_mm"], 85)
        self.assertEqual(data["dialogue"][0]["delivery"], {"pace": "slow", "intensity": 2, "pause_before": True})
        bad = shots.shot_data(scene, _shot(performance="sad", lens_mm=5), 1)
        self.assertNotIn("performance", bad)
        self.assertNotIn("lens_mm", bad)

    def test_acting_changes_the_image_and_motion_fingerprints(self):
        from core import lineage
        base = shots.shot_data({"idx": 1}, _shot(), 1)
        acted = dict(base, performance=KELLY_SMILE)
        self.assertNotEqual(lineage.image_spec_hash(base, [], "9:16"), lineage.image_spec_hash(acted, [], "9:16"))
        self.assertNotEqual(lineage.motion_spec_hash(base), lineage.motion_spec_hash(acted))

    def test_the_picture_prompt_carries_the_acting(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        from tests.test_v3 import kenta_project
        from core import llm_runner
        p, pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        row = shots.shots_of(p, pid)[0]
        data = dict(row["data"], performance=KELLY_SMILE)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
        p.conn.commit()
        job = p.create_job(row["id"], "image_gen")
        args = ImageRunner(p, MockImageProvider(), tempfile.mkdtemp())._submit_args(p.job(job))
        self.assertIn("trembling smile", args[0])
        self.assertIn("intensity 3/5", args[0])


class VoiceDirectionTests(unittest.TestCase):
    def test_delivery_becomes_tts_parameters_and_words(self):
        how, problems = voice_direction.clean({"pace": "slow", "intensity": 4, "pause_before": True, "stress": "hiểu", "tag": "[Whispers]",
                                              "emotion": "resigned"})
        self.assertEqual(problems, [])
        self.assertEqual(voice_direction.params(how), {"speed": 0.9, "stability": voice_direction.NATURAL})
        peak, _ = voice_direction.clean({"intensity": 5})
        self.assertEqual(voice_direction.params(peak), {"stability": voice_direction.CREATIVE})   # Creative may drift: the peak only
        line = "Em hiểu rồi, anh đi đi…"
        self.assertEqual(voice_direction.spoken_text(line, how), "[whispers] … Em HIỂU rồi, anh đi đi…")
        self.assertNotIn("[", voice_direction.spoken_text(line, how, model="eleven_turbo_v2_5"))   # tags are v3 only
        self.assertEqual(voice_direction.spoken_text("Em hiểu rồi…", how), "… Em hiểu rồi…")    # ≤ 3 words: pause only
        calm, _ = voice_direction.clean({"intensity": 2})
        self.assertEqual(voice_direction.params(calm), {"stability": voice_direction.NATURAL})
        self.assertEqual(voice_direction.params(None), {})

    def test_unknown_values_are_dropped_and_reported(self):
        how, problems = voice_direction.clean({"pace": "very slow", "tag": "gunshot", "intensity": 0})
        self.assertIsNone(how)
        self.assertEqual(len(problems), 3)                                       # a sound-effect tag could be read out or played

    def test_the_adapter_refuses_a_value_out_of_range_before_paying(self):
        from core.adapters.clipai_audio import ClipAIAudioProvider
        from core.providers import ProviderError
        prov = ClipAIAudioProvider.__new__(ClipAIAudioProvider)
        sent = {}
        prov._check_text = lambda what, text: text
        prov._generate = lambda *a: sent.setdefault("args", a) and "id-1"
        prov.generate_tts("Chào", 7, params={"speed": 0.9, "stability": 0.0})
        self.assertEqual(sent["args"][4], {"speed": 0.9, "stability": 0.0})
        with self.assertRaises(ProviderError):
            prov.generate_tts("Chào", 7, params={"speed": 2.0})

    def test_generate_sends_the_direction_only_when_the_feature_is_on(self):
        from core import voice
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("voice")
        sid = p.create_scene(pid, 1, "s1")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "story_scene": 1, "dialogue": [
            {"speaker": "KELLY", "text": "Em hiểu rồi…", "delivery": {"pace": "slow", "intensity": 2}}]}, ensure_ascii=False), sid))
        p.conn.commit()
        p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', '')", (pid,))
        voice.set_profile(p.conn, pid, "KELLY", {"voice_id": 71, "voice_name": "Kelly VN"})
        calls = []

        class Prov:
            def generate_tts(self, text, vid, model, lang, name="tts", params=None):
                calls.append((text, params))
                return str(len(calls))
        data = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {"FEATURE_VOICE_DIRECTION": "0"}):
            voice.generate(p.conn, pid, Prov(), data, ledger=False)
        self.assertEqual(calls, [("Em hiểu rồi…", None)])                        # off: exactly as before
        with mock.patch.dict(os.environ, {"FEATURE_VOICE_DIRECTION": "1"}):
            voice.generate(p.conn, pid, Prov(), data, ledger=False)              # the direction changed what is sent: made again
            self.assertEqual(calls[-1][1], {"speed": 0.9, "stability": voice_direction.NATURAL})
            voice.generate(p.conn, pid, Prov(), data, ledger=False)              # unchanged: not paid twice
        self.assertEqual(len(calls), 2)
        self.assertIsNotNone(sid)


class DirectorReportTests(unittest.TestCase):
    SCRIPT = "KỊCH BẢN\n\nCẢNH 1 – 0–6 GIÂY\n\nKELLY:\n“Anh nói đi.”\n\nKENTA:\n“Bây giờ chưa được.”\n"

    def _answer(self, lines, **root):
        return dict({"scenes": [{"idx": 1, "shots": [_shot(duration_s=3.0, dialogue=[{"speaker": w, "text": t}]) for w, t in lines]}]},
                    **root)

    def test_a_sacrifice_without_tradeoffs_is_a_fault(self):
        r = director_report.report(self._answer([("KELLY", "Anh nói đi.")]), self.SCRIPT)
        self.assertEqual(r["unrecorded"], ["bỏ câu thoại"])
        self.assertIn("không ghi `tradeoffs`", director_report.text(r))
        ok = director_report.report(self._answer([("KELLY", "Anh nói đi.")], tradeoffs=[
            {"chose": "thời lượng", "gave_up": "câu của Kenta", "why": "khung 6 s", "scene": 1}]), self.SCRIPT)
        self.assertEqual(ok["unrecorded"], [])
        self.assertEqual(director_report.problems(r) - director_report.problems(ok), 1)

    def test_a_payoff_without_a_setup_is_reported(self):
        scenes = [{"idx": 1, "beat": {"want": "x", "plant": ""}, "shots": [_shot()]},
                  {"idx": 2, "beat": {"payoff": "Kenta cứu Maxim"}, "shots": [_shot()]}]
        self.assertEqual(director_report.payoff_unplanted({"scenes": scenes}), [2])
        scenes[0]["beat"]["plant"] = "Kenta: nhất định không để cô ấy biết"
        self.assertEqual(director_report.payoff_unplanted({"scenes": scenes}), [])
        from core import llm_io
        llm_io._check_beat({"want": "", "value": "tin → ngờ", "plant": "", "payoff": ""}, "beat")   # the new keys pass the schema
        self.assertEqual(llm_io._clean_beat({"want": "x", "mood": "?", "payoff": None}), {"want": "x", "payoff": ""})   # never refused
        self.assertIsNone(llm_io._clean_beat("một chuỗi"))

    def test_motion_and_qc_get_the_drawn_strength(self):
        close = performance.for_prompt({"size": "CU", "performance": {"intensity": 4, "face": "jaw tight"}})
        self.assertEqual((close["intensity"], close["shown_intensity"]), (4, 3))    # the curve keeps 4, the close-up is acted at 3
        self.assertIsNone(performance.for_prompt({"size": "CU"}))

    def test_script_notes_and_acting_are_reported(self):
        answer = self._answer([("KELLY", "Anh nói đi."), ("KENTA", "Bây giờ chưa được.")],
                              script_notes=[{"scene": 1, "kind": "logic", "note": "Kenta giấu gì? người xem chưa biết"}, {"note": ""}])
        answer["scenes"][0]["shots"][0]["performance"] = {"intensity": 2, "face": "tight jaw"}   # the field is in use
        r = director_report.report(answer, self.SCRIPT)
        self.assertEqual(len(r["script_notes"]), 1)
        self.assertEqual(r["unrecorded"], [])
        self.assertTrue(any("thiếu performance" in w for w in r["acting"]))


class LocationBlockTests(unittest.TestCase):
    def test_an_unknown_spot_is_reported(self):
        from core import location_pack
        entry = {"spots": {"plaza_front": {"at": [0, 0, 0]}}, "default_spot": "plaza_front"}
        self.assertIn("không có ở bối cảnh này", location_pack.spot_problem(entry, {"plate_spot": "roof"}))
        self.assertIsNone(location_pack.spot_problem(entry, {"plate_spot": "plaza_front"}))
        self.assertIsNone(location_pack.spot_problem(entry, {}))

    def test_the_director_learns_the_spots_and_names(self):
        from core import assets, location_pack
        from core.db import connect
        from core.pipeline import Pipeline
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch.dict(os.environ, {"ASSET_DIR": os.path.join(tmp, "assets"), "FEATURE_LOCATION_PLATES": "1"}):
            p = Pipeline(connect(os.path.join(tmp, "m.sqlite")))
            pid = p.create_project("tower")
            aid = assets.create(p.conn, "FF", "location", "Tháp Đồng Hồ", "", "", None, "x")
            assets.attach(p.conn, pid, aid)
            model = os.path.join(tmp, "tower.glb")
            with open(model, "wb") as f:
                f.write(b"glb")
            location_pack.set_model3d(p.conn, aid, model, {"plaza_front": {"at": [0, 0, 0], "label": "sân trước"}})
            block = location_pack.director_block(p.conn, pid)
            self.assertIn("`plaza_front` (sân trước)", block)
            self.assertIn("snowfall", block)
            self.assertIn('"green"', block)
        with mock.patch.dict(os.environ, {"FEATURE_LOCATION_PLATES": "0"}):
            self.assertEqual(location_pack.director_block(p.conn, pid), "")


class DpBookTests(unittest.TestCase):
    def test_the_model_limits_come_from_the_rules_table(self):
        from core import video_rules
        text = prompts.role_text("dp.md")
        self.assertNotIn(prompts.MODEL_RULES_MARK, text)
        for line in video_rules.summary_lines():
            self.assertIn(line, text)

    def test_a_longer_lens_moves_the_camera_back_and_keeps_the_framing(self):
        base = plate_camera.camera_for({"size": "MS"}, (0, 0, 0), 0)
        long = plate_camera.camera_for({"size": "MS", "lens_mm": 85}, (0, 0, 0), 0)
        self.assertEqual(long["camera"]["lens"], 85)
        self.assertGreater(long["distance_m"], base["distance_m"] * 2)
        box, box_long = base["subject_box"], long["subject_box"]
        self.assertAlmostEqual(box[1], box_long[1], delta=0.03)                # the head stays where the size puts it
        self.assertAlmostEqual(box[2] - box[0], box_long[2] - box_long[0], delta=0.06)


class LoudnessTests(unittest.TestCase):
    def test_a_file_is_measured_and_judged(self):
        import subprocess
        from core import ffmpeg_studio
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            self.skipTest("no ffmpeg")
        path = os.path.join(tempfile.mkdtemp(), "tone.wav")
        subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                        path], check=True)
        m = ffmpeg_studio.measure_loudness(path, ff)
        self.assertAlmostEqual(m["lufs"], -21.8, delta=1.0)                     # ffmpeg's default sine: 1/8 amplitude
        self.assertAlmostEqual(m["true_peak_dbfs"], -18.1, delta=0.5)
        self.assertIn("LUFS", ffmpeg_studio.loudness_problems(m)[0])            # too quiet for -14
        self.assertEqual(ffmpeg_studio.loudness_problems({"lufs": -14.7, "true_peak_dbfs": -2.9}), [])   # the #7 delivery (2026-09-25)
        self.assertIn("đỉnh thật", ffmpeg_studio.loudness_problems({"lufs": -14.0, "true_peak_dbfs": -0.2})[0])
        after = ffmpeg_studio.normalize_loudness(path, os.path.join(os.path.dirname(path), "n.mp4"), ff)
        self.assertAlmostEqual(after["lufs"], -14.0, delta=1.0)                 # a quiet file brought to the target
        self.assertLessEqual(after["true_peak_dbfs"], -1.0)

    def test_every_render_is_encoded_for_the_platforms(self):
        from core import ffmpeg_studio
        cmd = ffmpeg_studio.build_concat_cmd("list.txt", "out.mp4")
        self.assertIn("+faststart", cmd)
        self.assertEqual(cmd[cmd.index("-colorspace") + 1], "bt709")


class SafeZoneTests(unittest.TestCase):
    def test_vertical_subtitles_keep_clear_of_the_right_button_column(self):
        font = Font(path="x.ttf", family="Test Sans", label="Test", vietnamese=True)
        ass = subtitles.to_ass([Cue(0.0, 2.0, "Em hiểu rồi.", "KELLY", 1)], 1080, 1920, font, platform="chung")
        style = next(ln for ln in ass.splitlines() if ln.startswith("Style: Default"))
        ml, mr = style.split(",")[19:21]
        self.assertEqual((int(ml), int(mr)), (int(1080 * 0.06), int(1080 * 0.18)))   # Google Ads: 192 px free on the right (common box)
        wide = subtitles.to_ass([Cue(0.0, 2.0, "Hi.", "A", 1)], 1920, 1080, font)
        wstyle = next(ln for ln in wide.splitlines() if ln.startswith("Style: Default"))
        self.assertEqual(wstyle.split(",")[19:21], [str(int(1920 * 0.06))] * 2)


if __name__ == "__main__":
    unittest.main()
