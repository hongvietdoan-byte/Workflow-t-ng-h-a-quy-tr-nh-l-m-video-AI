"""Dashboard v2: lineage ('⚠ cũ'), Director v2 + hand-edit locks, frame format, per-scene video model, QC policy / hard criteria,
pilot, voices, delivery settings, knowledge routing, v2 Claude tasks (mock), automatic run with checkpoints."""
import json
import os
import tempfile
import unittest

from core import (autopilot, batch, claude_tasks, delivery, dialogue, formats, knowledge, lineage, llm_io, llm_runner, model_router,
                  pilot, prompts, qc_policy, script_parser, voice)
from core.db import connect
from core.music import MockAudioProvider
from core.pipeline import Pipeline, hard_failures
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner

SCRIPT = ["CẢNH 1 - ĐÊM, RỪNG", "KENTA: Đi thôi.", "CẢNH 2 - ĐÊM, RỪNG", "KELLY: Nhanh lên!", "KENTA: Chờ chút.",
          "CẢNH 3 - NGÀY, LÀNG", "MAXIM: Ăn đã."]


def fake_render(p, pid, data_dir, music_path):
    out = os.path.join(data_dir, str(pid), "output", "FINAL_VIDEO.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(b"FINAL")
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("v2", aspect="9:16", genre="SHORT_FORM", model_priority="balanced")
        script_parser.import_scenes(self.p, self.pid, script_parser.split_scenes(SCRIPT))
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())

    def sid(self, idx):
        return self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()["id"]

    def approve_images(self, runner=None):
        llm_io.lock_character_bible(self.p, self.pid)
        runner = runner or ImageRunner(self.p, MockImageProvider(), self.data)
        batch.queue_images(self.p, self.pid)
        runner.submit_pending(self.pid)
        runner.poll_once(self.pid)
        for j in self.p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", (self.pid,)):
            self.p.approve(j["id"], "user")
        return runner


class DirectorV2Tests(Base):
    def test_director_v2_fields_are_stored(self):
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid(2),)).fetchone()["data"])
        self.assertEqual([d["speaker"] for d in data["dialogue"]], ["KELLY", "KENTA"])
        self.assertIn(data["camera_complexity"], ("simple", "complex"))
        self.assertTrue(self.p.conn.execute("SELECT lock_rules FROM characters WHERE name='KENTA'").fetchone()["lock_rules"])

    def test_old_json_without_v2_fields_is_still_valid(self):
        llm_io.validate_scene_analysis({"characters": [{"name": "A", "description": "x"}],
                                        "scenes": [{"idx": 1, "location": "", "time": "", "mood": "", "lighting": "", "shot": "",
                                                    "image_prompt": "p", "characters": ["A"]}]})

    def test_rerunning_the_director_keeps_hand_edits_and_the_background(self):
        llm_io.update_scene(self.p, self.pid, 1, {"blocking": "KENTA frame-left", "location_asset": 7})
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid(1),)).fetchone()["data"])
        self.assertEqual(data["blocking"], "KENTA frame-left")
        self.assertEqual(data["location_asset"], 7)
        self.assertIn("blocking", data["_user_locked"])

    def test_null_from_the_director_never_wipes_a_value(self):
        llm_io.update_scene(self.p, self.pid, 1, {"location_asset": 9})
        llm_io.unlock_scene_fields(self.p, self.pid, 1)
        obj = {"characters": [{"name": "KENTA", "description": "d"}],
               "scenes": [{"idx": 1, "location": "x", "time": "", "mood": "", "lighting": "", "shot": "", "image_prompt": "p",
                           "characters": ["KENTA"], "location_asset": None}]}
        llm_io.store_scene_analysis(self.p, self.pid, obj)
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid(1),)).fetchone()["data"])
        self.assertEqual(data["location_asset"], 9)

    def test_dialogue_comes_from_the_structured_list(self):
        rows = dialogue.scene_lines({"dialogue": [{"speaker": "A", "text": "Xin chào"}], "text": "B: khác"})
        self.assertEqual(rows, [("A", "Xin chào")])


class LineageTests(Base):
    def test_editing_a_scene_marks_its_image_motion_and_video_outdated(self):
        runner = self.approve_images()
        sid = self.sid(1)
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        llm_io.approve_motion_prompt(self.p, sid)
        vr = VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)
        batch.queue_videos(self.p, self.pid, self.data)
        vr.submit_pending(self.pid)
        vr.poll_once(self.pid)
        self.assertIsNone(lineage.scan(self.p.conn, self.pid)[sid]["video_stale"])
        llm_io.update_scene(self.p, self.pid, 1, {"blocking": "someone new frame-right"})
        row = lineage.scan(self.p.conn, self.pid)[sid]
        self.assertTrue(row["image_stale"])
        self.assertTrue(row["motion_stale"])
        self.assertTrue(row["video_stale"])
        self.assertNotIn(sid, [r["scene_id"] for r in llm_io.ready_for_video(self.p, self.pid)])
        other = lineage.scan(self.p.conn, self.pid)[self.sid(2)]
        self.assertIsNone(other["image_stale"])                         # only the changed scene
        self.assertTrue(runner)

    def test_reopening_an_image_makes_the_motion_prompt_outdated(self):
        self.approve_images()
        sid = self.sid(2)
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        llm_io.approve_motion_prompt(self.p, sid)
        jid = lineage.approved_image_id(self.p.conn, sid)
        self.p.reopen_approved(jid, "đổi ý")
        self.assertEqual(lineage.scan(self.p.conn, self.pid)[sid]["motion_stale"], "ảnh của cảnh đã bị bỏ duyệt")

    def test_queue_images_redoes_only_outdated_pictures(self):
        self.approve_images()
        llm_io.update_scene(self.p, self.pid, 3, {"image_prompt": "a new prompt"})
        r = batch.queue_images(self.p, self.pid)
        self.assertEqual((r["created"], r["redo"]), (0, 1))


class FormatAndModelTests(Base):
    def test_vertical_project_sends_vertical_sizes(self):
        provider = MockImageProvider()
        self.approve_images(ImageRunner(self.p, provider, self.data))
        self.assertEqual(set(provider.sizes.values()), {formats.ASPECTS["9:16"]["deepix"]})

    def test_model_router_follows_the_slide(self):
        hero = {"shot_role": "hero", "camera_complexity": "complex", "characters": ["A"]}
        self.assertEqual(model_router.recommend(hero, "quality")["model"], "seedance-2.5")
        self.assertEqual(model_router.recommend({"characters": ["A"]}, "value")["model"], "seedance-fast")
        duo = {"characters": ["A", "B"], "dialogue": [{"speaker": "A", "text": "x"}, {"speaker": "B", "text": "y"}]}
        self.assertEqual(model_router.recommend(duo, "balanced")["model"], "kling")
        # K3: Seedance takes no per-person references next to a first frame, so a crowd no longer means Seedance
        self.assertEqual(model_router.recommend({"characters": ["A", "B", "C"]}, "balanced")["model"], "kling")
        # W11: the in-game Free Fire look goes to Kling (Seedance blocked in-game-looking people in GĐ6)
        self.assertEqual(model_router.recommend(hero, "quality", look="FF_INGAME")["model"], "kling")
        self.assertEqual(model_router.recommend(hero, "quality", look="ANIME")["model"], "seedance-2.5")

    def test_video_jobs_use_the_model_of_their_scene_and_the_project_ratio(self):
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        for s in (1, 2, 3):
            llm_io.approve_motion_prompt(self.p, self.sid(s))
        model_router.set_override(self.p.conn, self.sid(1), "seedance-2.5")
        provider = MockVideoProvider(polls_to_finish=1)
        vr = VideoRunner(self.p, provider, self.data)
        batch.queue_videos(self.p, self.pid, self.data)
        vr.submit_pending(self.pid)
        models = {t["model"] for t in provider._tasks.values()}
        self.assertIn("seedance-2.5", models)
        self.assertEqual({t["aspect_ratio"] for t in provider._tasks.values()}, {"9:16"})
        self.assertEqual(self.p.conn.execute("SELECT model FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid(1),)).fetchone()[0],
                         "seedance-2.5")


class QcTests(Base):
    def test_a_blocking_criterion_fails_the_picture_whatever_the_average(self):
        self.assertTrue(hard_failures({"character": 0.3, "hands_face": 1.0}))
        self.p.set_mode(self.pid, "auto")
        runner = ImageRunner(self.p, MockImageProvider(), self.data)
        llm_io.lock_character_bible(self.p, self.pid)
        batch.queue_images(self.p, self.pid)
        runner.submit_pending(self.pid)
        runner.poll_once(self.pid)
        jid = self.p.conn.execute("SELECT id FROM jobs WHERE state='succeeded' LIMIT 1").fetchone()["id"]
        scores = {k: 1.0 for k in prompts.qc_criteria()}
        scores["character"] = 0.3
        self.assertNotEqual(self.p.apply_qc(jid, scores), "approved")

    def test_qc_policy_presets_write_the_settings(self):
        qc_policy.apply(self.p, self.pid, "saver")
        row = self.p.project(self.pid)
        self.assertEqual((row["qc_auto_pass_threshold"], row["qc_autofix"], row["qc_policy"]), (0.75, 0, "saver"))
        self.assertIn("Ngưỡng đạt", qc_policy.describe(row))


class PilotTests(Base):
    def test_pilot_limits_the_first_batch(self):
        for i in range(4, 8):
            self.p.create_scene(self.pid, i, f"CẢNH {i}")
            llm_io.update_scene(self.p, self.pid, i, {"image_prompt": f"p{i}"})
        llm_io.lock_character_bible(self.p, self.pid)
        chosen = pilot.start(self.p, self.pid)
        r = batch.queue_images(self.p, self.pid)
        self.assertEqual(r["created"], len(chosen))
        pilot.release(self.p, self.pid)
        self.assertEqual(batch.queue_images(self.p, self.pid)["created"], 7 - len(chosen))


class VoiceTests(Base):
    def test_voices_are_made_per_line_and_size_the_clips(self):
        for name in ("KENTA", "KELLY", "MAXIM"):
            voice.set_profile(self.p.conn, self.pid, name, {"voice_id": 1, "voice_name": "Mock"})
        audio = MockAudioProvider()
        r = voice.generate(self.p.conn, self.pid, audio, self.data)
        self.assertEqual(r["sent"], 4)
        from core import audio_lib
        audio_lib.refresh(audio, audio_lib.assets_dir(self.data, self.pid))
        self.assertEqual(voice.status(self.p.conn, self.pid, self.data)["succeeded"], 4)
        self.assertEqual(voice.generate(self.p.conn, self.pid, audio, self.data)["sent"], 0)     # nothing changed: nothing resent
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=1")
        changes = voice.fit_durations(self.p.conn, self.pid, self.data)
        self.assertTrue(changes)


class KnowledgeTests(Base):
    def test_only_the_skill_notes_of_characters_in_the_project_are_sent(self):
        full = open(os.path.join(os.path.dirname(knowledge.__file__), "..", "knowledge", "ff_character_skills_visual.md"),
                    encoding="utf-8").read()
        part = knowledge.ff_skills_for(["KENTA"])
        self.assertIn("KENTA", part)
        self.assertLess(len(part), len(full) / 2)
        bundle = prompts.build_director_bundle(self.p, self.pid)
        self.assertIn("SHORT_FORM", bundle)
        self.assertIn("DỌC 9:16", bundle)


class ClaudeTaskTests(Base):
    def test_dialogue_review_and_motion_lint_run_with_the_mock(self):
        res = claude_tasks.review_dialogue(self.p, self.pid, llm_runner.MockLlm())
        self.assertIn("lines", res)
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        out = claude_tasks.lint_motion(self.p, self.pid, llm_runner.MockLlm())
        self.assertEqual(len(out["scenes"]), 3)
        self.assertTrue(self.p.conn.execute("SELECT lint FROM motion_prompts LIMIT 1").fetchone()["lint"])

    def test_character_lock_and_voice_casting(self):
        claude_tasks.character_lock(self.p, self.pid, "KELLY", llm_runner.MockLlm())
        self.assertIn("must_keep", self.p.conn.execute("SELECT lock_rules FROM characters WHERE name='KELLY'").fetchone()[0])
        cast = claude_tasks.cast_voices(self.p, self.pid, llm_runner.MockLlm(), [{"id": 5, "name": "Giọng A"}])
        self.assertTrue(cast["cast"])
        self.assertEqual(voice.profiles(self.p.conn, self.pid)["KENTA"]["voice_id"], 5)


class DeliveryTests(Base):
    def test_render_settings_are_kept_per_project(self):
        s = delivery.get_settings(self.p, self.pid)
        delivery.save_settings(self.p, self.pid, dict(s, transition="crossfade", fade=0.8))
        self.assertEqual(delivery.get_settings(self.p, self.pid)["transition"], "crossfade")
        with self.assertRaises(ValueError):
            delivery.save_settings(self.p, self.pid, dict(s, transition="spin"))

    def test_deliver_records_the_final_render(self):
        out = delivery.deliver(self.p, self.pid, self.data, render_fn=fake_render)
        self.assertTrue(out["final"].endswith("FINAL_VIDEO.mp4"))
        self.assertIsNotNone(lineage.latest_output(self.p.conn, self.pid, "final"))


class RealScriptTests(unittest.TestCase):
    """Found with the user's Free Fire script (2026-09-23): 'Kelly:' speakers, a 'TEXT CUỐI:' block, a preamble before scene 1."""
    SCRIPT = ["KỊCH BẢN FREE FIRE: KENTA XUYÊN TƯỜNG CƯỚP KILL?!", "Thời lượng: 45–55 giây", "Nhân vật: Kelly, Maxim, Kenta",
              "Bối cảnh: Map Đảo Quân Sự có thể chọn Tháp Đồng Hồ", "CẢNH 1: THÁCH THỨC KENTA", "*Kelly và Maxim núp sau tường.*",
              "Kelly: Maxim! Có địch bên kia!", "Maxim: Kenta đâu rồi?!", "CẢNH 2: CÚ TWIST", "*Maxim nhìn xuống: Kenta đã nhặt sạch đồ.*",
              "Maxim: KENTAAAA! TƯỜNG NÀY KHÔNG XUYÊN ĐƯỢC!!!", "TEXT CUỐI:", "“Kenta được làm lại kỹ năng. Maxim vẫn chưa được làm lại IQ!”"]

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("kenta", aspect="9:16", genre="SHORT_FORM", model_priority="balanced")
        script_parser.import_scenes(self.p, self.pid, script_parser.split_scenes(self.SCRIPT), full_text="\n".join(self.SCRIPT))

    def test_capitalised_speakers_are_dialogue_but_headings_and_actions_are_not(self):
        texts = [json.loads(r["data"])["text"] for r in self.p.conn.execute("SELECT data FROM scenes ORDER BY idx")]
        self.assertEqual(dialogue.lines(texts[0]), [("KELLY", "Maxim! Có địch bên kia!"), ("MAXIM", "Kenta đâu rồi?!")])
        self.assertEqual(len(dialogue.lines(texts[1])), 1)                      # the '*Maxim nhìn xuống: …*' action is not a line
        self.assertEqual(dialogue.lines("Ghi chú: quay đêm\nNhân vật: Kelly, Maxim"), [])

    def test_the_closing_text_becomes_the_end_card_not_part_of_the_last_scene(self):
        last = json.loads(self.p.conn.execute("SELECT data FROM scenes ORDER BY idx DESC LIMIT 1").fetchone()["data"])["text"]
        self.assertNotIn("TEXT CUỐI", last)
        card = delivery.get_settings(self.p, self.pid)["end_card"]
        self.assertTrue(card["enabled"])
        self.assertEqual(card["title"], "Kenta được làm lại kỹ năng. Maxim vẫn chưa được làm lại IQ!")

    def test_the_director_gets_what_the_script_says_before_scene_1(self):
        bundle = prompts.build_director_bundle(self.p, self.pid)
        self.assertIn("Thời lượng: 45–55 giây", bundle)
        self.assertIn("Map Đảo Quân Sự", bundle)


class WalkthroughFixTests(Base):
    """Bugs found by running the Kenta script through the dashboard (docs/V2_TEST_REPORT.md)."""

    def test_sizing_clips_to_the_dialogue_works_before_any_motion_prompt(self):
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid(1),)).fetchone()["data"])
        data["dialogue"] = [{"speaker": "KENTA", "text": "một hai ba bốn năm sáu bảy tám chín mười " * 3}]
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.sid(1)))
        self.p.conn.commit()
        entries = dialogue.check(self.p, self.pid)
        self.assertTrue(any(e["status"] == "extend" for e in entries))
        self.assertGreater(dialogue.extend(self.p, entries), 0)
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid(1),)).fetchone()["data"])
        self.assertGreater(data["duration_s"], 5)
        self.assertIn("duration_s", data["_user_locked"])       # the Director re-run and the motion prompt keep it

    def test_a_script_with_dialogue_gets_subtitles_in_its_delivery(self):
        from core import subtitles
        self.assertTrue(subtitles.get_settings(self.p, self.pid)["enabled"])
        silent = self.p.create_project("no dialogue")
        script_parser.import_scenes(self.p, silent, script_parser.split_scenes(["CẢNH 1", "Mưa rơi."]))
        self.assertFalse(subtitles.get_settings(self.p, silent)["enabled"])

    def test_music_brief_covers_the_whole_film(self):
        from core import music
        brief = claude_tasks.music_brief(self.p, self.pid, llm_runner.MockLlm())
        self.assertGreaterEqual(brief["length_ms"], music.default_brief(self.p, self.pid)["length_ms"])

    def test_simulated_spend_is_not_called_real(self):
        self.approve_images()
        from core import cost
        spend = cost.spend_summary(self.p.conn, self.pid, cost.load_pricing())
        self.assertEqual(spend["mock"], spend["events"])

    def test_gen_video_button_counts_only_scenes_without_a_clip(self):
        self.approve_images()
        todo = batch.videos_to_make(self.p, self.pid)
        if todo:
            batch.queue_videos(self.p, self.pid, self.data)
            self.assertEqual(batch.videos_to_make(self.p, self.pid), [])

    def test_simulators_write_real_media_in_the_project_frame_when_asked(self):
        from core import ffmpeg_studio
        os.environ["MOCK_REAL_MEDIA"] = "1"
        try:
            img = MockImageProvider()
            path = img.download(img.submit("x", size="1152x2048"), os.path.join(self.data, "a.png"))
            from PIL import Image
            w, h = Image.open(path).size
            self.assertLess(w, h)
            try:
                ffmpeg_studio.find_ffmpeg()
            except Exception:  # noqa: BLE001
                self.skipTest("ffmpeg not installed")
            vid = MockVideoProvider()
            clip = vid.download(vid.submit(path, "p", "", 4, aspect_ratio="9:16"), os.path.join(self.data, "a.mp4"))
            self.assertEqual(ffmpeg_studio.probe_size(clip), (360, 640))
        finally:
            os.environ.pop("MOCK_REAL_MEDIA", None)


class ReframeExportTests(Base):
    def test_a_square_crop_of_a_vertical_delivery_is_rebuilt_with_its_subtitles_and_card(self):
        import subprocess
        from unittest import mock
        from core import ffmpeg_studio, subtitles
        try:
            ffmpeg = ffmpeg_studio.find_ffmpeg()
        except Exception:  # noqa: BLE001
            self.skipTest("ffmpeg not installed")
        final = os.path.join(self.data, str(self.pid), "output", "FINAL_VIDEO.mp4")
        os.makedirs(os.path.dirname(final), exist_ok=True)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=360x640:d=3", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=stereo", "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        final], check=True)
        fid = delivery.record(self.p, self.pid, "final", final, None, {})
        cues = [subtitles.Cue(0.2, 2.0, "Đi thôi.", "KENTA", 1)]
        try:
            sub = delivery.subtitle_layer(self.p, self.pid, self.data, fid, cues=cues)
        except (subtitles.SubtitleError, ffmpeg_studio.FFmpegError) as e:
            self.skipTest(f"no subtitle burning here: {e}")
        self.assertEqual(json.loads(self.p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (sub["output_id"],))
                                    .fetchone()["manifest"])["cue_list"][0]["text"], "Đi thôi.")
        delivery.save_settings(self.p, self.pid, {**delivery.get_settings(self.p, self.pid),
                                                  "end_card": {**delivery.DEFAULT_CARD, "enabled": True, "title": "Hết"}})
        delivery.end_card_layer(self.p, self.pid, self.data)
        with mock.patch.object(delivery, "_reframe", wraps=delivery._reframe) as reframe:
            res = delivery.export_layer(self.p, self.pid, self.data, {"w": 480, "h": 480, "fit": "crop"})
        self.assertEqual(reframe.call_count, 1)
        self.assertEqual(ffmpeg_studio.probe_size(res["path"]), (480, 480))


class AutopilotV2Tests(Base):
    def ctx(self):
        return autopilot.Context(self.data, ImageRunner(self.p, MockImageProvider(), self.data),
                                 VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data), llm_runner.MockLlm(),
                                 MockAudioProvider(), fake_render)

    def test_waits_for_the_character_bible_then_runs_to_the_end_and_gives_the_review_mode_back(self):
        ctx = self.ctx()
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.WAITING)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)      # nothing paid before the approval
        autopilot.resume(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx, max_ticks=400), autopilot.WAITING)   # the storyboard (W1)
        self.assertEqual(autopilot.get_gates(self.p, self.pid)["waiting_for"], "storyboard")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], 0)   # no video paid yet
        autopilot.resume(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx, max_ticks=400), autopilot.DONE)
        self.assertEqual(self.p.project(self.pid)["operating_mode"], "human_qc")

    def test_without_the_checkpoint_it_runs_straight_through(self):
        autopilot.set_gates(self.p, self.pid, {"bible": False, "storyboard": False})
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, self.ctx(), max_ticks=400), autopilot.DONE)


if __name__ == "__main__":
    unittest.main()
