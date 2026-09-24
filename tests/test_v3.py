"""Kế hoạch v3: reference-video analysis (GĐ1). Later phases add their tests here."""
import json
import os
import tempfile
import unittest

from core import llm_runner
from core import reference_analysis as ra


class ReferenceAnalysisTests(unittest.TestCase):
    def test_shots_from_cuts_drops_flash_frames_and_cuts_at_the_ends(self):
        shots = ra.shots_from_cuts([0.1, 2.0, 2.1, 5.0, 9.9], 10.0)
        self.assertEqual([(s["start"], s["end"]) for s in shots], [(0.0, 2.0), (2.0, 5.0), (5.0, 10.0)])
        self.assertEqual([s["i"] for s in shots], [1, 2, 3])
        with self.assertRaises(ra.ReferenceAnalysisError):
            ra.shots_from_cuts([1.0], 0)

    def test_cuts_from_diffs_finds_global_and_local_peaks_once(self):
        diffs = [(round(t * 0.2, 1), 3.0) for t in range(60)]
        diffs[10] = (2.0, 80.0)              # a hard cut
        diffs[11] = (2.2, 70.0)              # the same cut seen twice -> one cut
        diffs[40] = (8.0, 30.0)              # a cut inside a quiet frame (local peak)
        cuts = ra.cuts_from_diffs(diffs)
        self.assertEqual(cuts, [2.0, 8.0])
        self.assertEqual(ra.cuts_from_diffs([]), [])

    def test_labels_must_use_the_fixed_vocabulary_and_cover_every_shot(self):
        ok = {"shots": [{"i": 1, "size": "WS", "angle": "eye", "camera_move": "static", "role": "hook"},
                        {"i": 2, "size": "GAME_TPS", "angle": "high", "camera_move": "track", "role": "action", "vfx": True}],
              "overall": {}}
        self.assertIs(ra.validate_labels(ok, 2), ok)
        with self.assertRaises(ValueError):
            ra.validate_labels(ok, 3)                                          # shot 3 missing
        bad = json.loads(json.dumps(ok))
        bad["shots"][0]["size"] = "close-up"
        with self.assertRaises(ValueError):
            ra.validate_labels(bad, 2)

    def test_mock_labelling_saves_text_only_and_feeds_the_statistics(self):
        shots = ra.shots_from_cuts([1.0, 2.5, 4.0], 6.0)
        meta = {"duration_sec": 6.0, "width": 1080, "height": 1920}
        labels = ra.label(llm_runner.MockLlm(), "INGAME", meta, shots, [], title="thử")
        merged = ra.merge_labels(shots, labels)
        self.assertEqual(merged[0]["role"], "hook")
        self.assertEqual(merged[-1]["role"], "ending")
        folder = tempfile.mkdtemp()
        path = ra.save_record("INGAME", "https://www.youtube.com/watch?v=abcdefghijk", "thử", meta, merged,
                              labels["overall"], research_dir=folder)
        self.assertTrue(path.endswith(os.path.join("INGAME", "abcdefghijk.json")))
        recs = ra.load_records("INGAME", research_dir=folder)
        stats = ra.style_stats(recs)
        self.assertEqual((stats["videos"], stats["shots"]), (1, 4))
        self.assertEqual(stats["opens_with"], {"hook": 1})
        self.assertIn("shot/phút", ra.stats_markdown("INGAME", stats))
        with self.assertRaises(ra.ReferenceAnalysisError):
            ra.save_record("NOT_A_STYLE", "x.mp4", "x", meta, merged, research_dir=folder)

    def test_style_knowledge_files_exist_for_every_style(self):
        root = os.path.join(os.path.dirname(__file__), "..", "knowledge")
        for style in ra.STYLES:
            self.assertTrue(os.path.exists(os.path.join(root, "ff_styles", f"{style}.md")), style)
        self.assertTrue(os.path.exists(os.path.join(root, "ff_directing.md")))


SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "kenta_xuyen_tuong_cuop_kill.txt")


def kenta_project(shot_mode="per_shot", style="SHORT_FILM"):
    from core import script_parser
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    pid = p.create_project("kenta", aspect="9:16", genre="SHORT_FORM", model_priority="balanced")
    if shot_mode:
        p.set_project_field(pid, "shot_mode", shot_mode)
    if style:
        p.set_project_field(pid, "style_profile", style)
    with open(SAMPLE, encoding="utf-8") as f:
        text = f.read()
    script_parser.import_scenes(p, pid, script_parser.split_scenes([ln for ln in text.splitlines() if ln.strip()]), full_text=text)
    return p, pid


class ShotLayerTests(unittest.TestCase):
    def test_the_director_splits_every_scene_into_shots_without_repeating_lines(self):
        from core import dialogue, shots
        p, pid = kenta_project()
        self.assertEqual(len(shots.story_scenes(p, pid)), 3)
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        rows = shots.shots_of(p, pid)
        self.assertGreater(len(rows), 12)
        self.assertEqual([r["idx"] for r in rows], list(range(1, len(rows) + 1)))
        self.assertEqual(rows[0]["label"], "S01·1")
        spoken = [line for r in rows for line in dialogue.scene_lines(r["data"])]
        self.assertEqual(len(spoken), 14)                       # every line of the script exactly once
        self.assertEqual(len(shots.story_scenes(p, pid)), 3)     # the script's scenes are kept apart
        silent = next(r for r in rows if r["data"]["role"] == "reaction")
        self.assertEqual(dialogue.scene_lines(silent["data"]), [])

    def test_a_v2_project_keeps_one_row_per_scene(self):
        p, pid = kenta_project(shot_mode=None, style=None)
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        rows = p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertFalse(any(json.loads(r["data"]).get("shot_no") for r in rows))

    def test_director_bundle_carries_the_shot_rules_and_the_style_only_in_shot_mode(self):
        from core import prompts
        p, pid = kenta_project()
        bundle = prompts.build_director_bundle(p, pid)
        self.assertIn("# Phân shot (dự án chia shot", bundle)
        self.assertIn("Phong cách dựng của dự án (SHORT_FILM)", bundle)
        p2, pid2 = kenta_project(shot_mode=None, style=None)
        self.assertNotIn("# Phân shot", prompts.build_director_bundle(p2, pid2))

    def test_shots_are_not_replaced_once_pictures_exist_and_bad_shots_are_refused(self):
        from core import llm_io, shots
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        p.create_job(shots.shots_of(p, pid)[0]["id"])
        with self.assertRaises(llm_io.SchemaError):
            llm_runner.run_director(p, pid, llm_runner.MockLlm())
        with self.assertRaises(shots.ShotError):
            shots.validate([{"size": "HUGE", "role": "action", "duration_s": 2, "image_prompt": "x", "action": "y"}], "s", set())

    def test_a_short_shot_is_priced_and_sent_at_the_model_minimum(self):
        from core import model_router
        self.assertEqual(model_router.billed_seconds("kling", 1.5), 3.0)
        self.assertEqual(model_router.billed_seconds("seedance", 2.0), 4.0)
        self.assertEqual(model_router.billed_seconds("seedance-2.5", 26), 26.0)

    def test_v2_fingerprints_do_not_change(self):
        from core import lineage
        data = {"image_prompt": "a", "blocking": "b", "text": "KENTA: đi", "duration_s": 5}
        old_image = lineage._hash({"scene": {k: data.get(k) for k in lineage.IMAGE_KEYS}, "cast": [], "aspect": ""})
        self.assertEqual(lineage.image_spec_hash(data, [], None), old_image)
        self.assertEqual(lineage.motion_spec_hash(data), lineage._hash({k: data.get(k) for k in lineage.MOTION_KEYS}))
        self.assertNotEqual(lineage.motion_spec_hash({**data, "action": "chạy"}), lineage.motion_spec_hash(data))

    def test_video_jobs_of_shots_ask_for_whole_seconds_not_below_the_plan(self):
        from core import batch, llm_io
        from core.providers import MockImageProvider, MockVideoProvider
        from core.runner import ImageRunner, VideoRunner
        p, pid = kenta_project()
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        llm_io.lock_character_bible(p, pid)
        img = ImageRunner(p, MockImageProvider(), data)
        batch.queue_images(p, pid)
        img.submit_pending(pid)
        img.poll_once(pid)
        for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", (pid,)).fetchall():
            p.approve(j["id"], "user")
        llm_runner.run_motion(p, pid, llm_runner.MockLlm(), data)
        planned = {}
        for r in p.conn.execute("SELECT m.scene_id, m.duration_sec FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
                                " WHERE s.project_id=?", (pid,)).fetchall():
            llm_io.approve_motion_prompt(p, r["scene_id"])
            planned[r["scene_id"]] = r["duration_sec"]
        provider = MockVideoProvider()
        provider.max_concurrent = 99
        vr = VideoRunner(p, provider, data)
        vr.max_concurrent = 99
        batch.queue_videos(p, pid, data)
        vr.submit_pending(pid)
        sent = [t["duration"] for t in provider._tasks.values()]
        self.assertTrue(sent)
        self.assertTrue(all(float(d).is_integer() for d in sent))
        self.assertLess(min(planned.values()), 3)                # the plan has shots shorter than any model's minimum
        self.assertEqual(sorted(sent), sorted(__import__("math").ceil(v - 1e-6) for v in planned.values())[:len(sent)])

    def test_a_downloaded_clip_is_cut_to_the_shot_length_and_the_full_clip_is_kept(self):
        import subprocess
        from core import ffmpeg_studio, shots
        try:
            ffmpeg = ffmpeg_studio.find_ffmpeg()
        except Exception:  # noqa: BLE001
            self.skipTest("ffmpeg not installed")
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        row = shots.shots_of(p, pid)[0]                        # a 1.5 s shot
        path = os.path.join(tempfile.mkdtemp(), "01.mp4")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=160x284:d=4", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", path], check=True)
        self.assertTrue(shots.trim_clip(p, row["id"], path))
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(path), 1.5, delta=0.15)
        self.assertTrue(os.path.exists(path.replace(".mp4", "_raw.mp4")))
        self.assertFalse(shots.trim_clip(p, row["id"], path))   # already short enough


def _set_data(p, scene_id, **fields):
    row = p.conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    data = {**json.loads(row["data"] or "{}"), **fields}
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene_id))
    p.conn.commit()


def _approve_all_images(p, pid, data):
    from core import batch, llm_io
    from core.providers import MockImageProvider
    from core.runner import ImageRunner
    llm_io.lock_character_bible(p, pid)
    img = ImageRunner(p, MockImageProvider(), data)
    img.max_concurrent = 99
    for _ in range(40):                                  # continuing shots wait for the previous approval: loop until done
        batch.queue_images(p, pid)
        img.submit_pending(pid)
        img.poll_once(pid)
        done = p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'", (pid,)).fetchall()
        for j in done:
            p.approve(j["id"], "user")
        if not p.conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type='image_gen' AND state IN ('queued','running')",
                              (pid,)).fetchone():
            break
    return img


def _approve_all_motion(p, pid, data):
    from core import llm_io
    llm_runner.run_motion(p, pid, llm_runner.MockLlm(), data)
    for r in p.conn.execute("SELECT m.scene_id FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?",
                            (pid,)).fetchall():
        llm_io.approve_motion_prompt(p, r["scene_id"])


class ConsistencyTests(unittest.TestCase):
    def test_a_continuing_shot_waits_for_the_previous_picture_and_ends_on_the_next_one(self):
        from core import batch, shots
        from core.providers import MockImageProvider, MockVideoProvider
        from core.runner import ImageRunner, VideoRunner
        p, pid = kenta_project()
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        rows = shots.shots_of(p, pid)
        _set_data(p, rows[0]["id"], continuous_with_next=True)
        from core import llm_io
        llm_io.lock_character_bible(p, pid)
        img = ImageRunner(p, MockImageProvider(), data)
        img.max_concurrent = 99
        batch.queue_images(p, pid)
        img.submit_pending(pid)
        second = p.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='image_gen'", (rows[1]["id"],)).fetchone()
        self.assertEqual(second["state"], "queued")                 # waits: shot 1 has no approved picture yet
        _approve_all_images(p, pid, data)
        _approve_all_motion(p, pid, data)
        p.conn.execute("UPDATE motion_prompts SET video_model='seedance' WHERE scene_id=?", (rows[0]["id"],))
        p.conn.commit()
        provider = MockVideoProvider()
        vr = VideoRunner(p, provider, data)
        vr.max_concurrent = 99
        batch.queue_videos(p, pid, data)
        vr.submit_pending(pid)
        sent = [t for t in provider._tasks.values() if t["last_frame"]]
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["last_frame"], shots.approved_image_path(p.conn, data, pid, rows[1]["id"]))

    def test_one_model_for_a_continuity_group_in_per_shot_mode(self):
        from core import model_router, shots
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        by_group = {}
        for r in shots.shots_of(p, pid):
            by_group.setdefault(r["data"]["story_scene"], set()).add(model_router.scene_choice(p.conn, r["id"])["model"])
        self.assertTrue(all(len(models) == 1 for models in by_group.values()))

    def test_kling_multishot_makes_one_clip_per_group_and_gives_each_shot_its_part(self):
        from core import batch, ffmpeg_studio, model_router, shots
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        try:
            ffmpeg_studio.find_ffmpeg()
        except Exception:  # noqa: BLE001
            self.skipTest("ffmpeg not installed")
        os.environ["MOCK_REAL_MEDIA"] = "1"
        try:
            p, pid = kenta_project(shot_mode="multishot")
            data = tempfile.mkdtemp()
            llm_runner.run_director(p, pid, llm_runner.MockLlm())
            rows = shots.shots_of(p, pid)
            self.assertEqual({model_router.scene_choice(p.conn, r["id"])["model"] for r in rows}, {"kling"})
            groups = shots.multishot_groups(p.conn, pid)
            self.assertTrue(all(sum(shots.billed_shot_seconds(r["data"]) for r in g) <= 15 for g in groups))
            multi = [g for g in groups if len(g) > 1]
            self.assertTrue(multi)
            _approve_all_images(p, pid, data)
            images = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", (pid,)).fetchone()[0]
            self.assertEqual(images, len(groups))                         # only the first shot of each group needs a picture
            _approve_all_motion(p, pid, data)
            self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?",
                                            (pid,)).fetchone()[0], len(rows))   # every shot still gets its motion prompt
            provider = MockVideoProvider(polls_to_finish=1)
            vr = VideoRunner(p, provider, data)
            vr.max_concurrent = 99
            batch.queue_videos(p, pid, data)
            for _ in range(10):                                           # the learned concurrency limit sends a few at a time
                vr.submit_pending(pid)
                vr.poll_once(pid)
            self.assertEqual(len(provider._tasks), len(groups))          # one generation per group
            self.assertEqual(sum(1 for t in provider._tasks.values() if t["multi_prompt"]), len(multi))
            done = p.conn.execute("SELECT scene_id, result_path, group_leader FROM jobs WHERE project_id=? AND type='video_gen'"
                                  " AND state='succeeded'", (pid,)).fetchall()
            self.assertEqual(len({d["scene_id"] for d in done}), len(rows))  # every shot got its clip
            follower = next(d for d in done if d["group_leader"])
            self.assertTrue(os.path.exists(follower["result_path"]))
            shot_len = shots.planned_seconds(p.conn, follower["scene_id"])
            self.assertAlmostEqual(ffmpeg_studio.probe_duration(follower["result_path"]), shot_len, delta=0.3)
            from core import claude_tasks, final_cut
            self.assertEqual(len(final_cut.usable_clips(p, data, pid)), len(rows))   # the _raw / _group originals never go in the cut
            result = claude_tasks.clip_set_consistency(p, pid, llm_runner.MockLlm(), data)
            self.assertIn("ok", result)
        finally:
            os.environ.pop("MOCK_REAL_MEDIA", None)


VOICES = [{"id": 30002, "name": "Xinghe Jiang", "languages": ["en", "vi"], "labels": {"gender": "male"}},
          {"id": 2, "name": "Xinghe Jiang", "languages": ["en", "vi"], "labels": {"gender": "male"}},
          {"id": 30007, "name": "Arabella", "languages": ["en", "vi"], "labels": {"gender": "female"}},
          {"id": 11, "name": "Rachel", "languages": ["en"], "labels": {"gender": "female", "language": "en"}},
          {"id": 12, "name": "Adam", "labels": {"gender": "male", "language": "en"}}]


class VietnameseVoiceTests(unittest.TestCase):
    def test_vietnamese_voices_come_first_once_each(self):
        from core import voice
        ordered = voice.vietnamese_first(VOICES)
        self.assertEqual([v["name"] for v in ordered], ["Xinghe Jiang", "Arabella", "Rachel", "Adam"])
        self.assertEqual([v["id"] for v in voice.casting_pool(VOICES)], [30002, 30007])
        self.assertEqual(len(voice.casting_pool(VOICES[3:])), 2)            # no Vietnamese voice at all: everything is offered
        self.assertEqual(voice.voice_gender(VOICES[2]), "female")

    def test_game_words_are_spelt_for_the_voice_but_not_inside_other_words(self):
        from core import voice
        words = {"loot": "lút", "Kenta": "Ken-ta", "IQ": "ai-kiu"}
        said = voice.speakable("Kenta đi LOOT, KENTAAAA! chưa làm lại IQ", words)
        self.assertEqual(said, "Ken-ta đi lút, KENTAAAA! chưa làm lại ai-kiu")
        self.assertTrue(voice.pronunciation())                              # data/pronunciation_vi.json is shipped

    def test_the_voice_says_the_spelt_line_while_subtitles_keep_the_script(self):
        from core import audio_lib, voice
        from core.music import MockAudioProvider
        p, pid = kenta_project()
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        for name in ("KELLY", "MAXIM", "KENTA"):
            voice.set_profile(p.conn, pid, name, {"voice_id": 30007, "voice_name": "Arabella"})
        voice.generate(p.conn, pid, MockAudioProvider(), data, ledger=False)
        items = [e for e in audio_lib.load(audio_lib.assets_dir(data, pid)) if e.get("dialogue")]
        loot = next(e for e in items if "loot" in e["text"])
        self.assertIn("lút", loot["label"])                                 # what was sent to TTS
        self.assertIn("loot", loot["text"])                                 # what subtitles and matching use
        voice.preview(MockAudioProvider(), data, pid, 30007, "Arabella", "KELLY")
        self.assertEqual(len(audio_lib.load(voice.previews_dir(data, pid))), 1)
        self.assertEqual(len([e for e in audio_lib.load(audio_lib.assets_dir(data, pid)) if e.get("dialogue")]), len(items))

    def test_casting_only_offers_voices_that_speak_vietnamese(self):
        from core import claude_tasks
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        claude_tasks.cast_voices(p, pid, llm_runner.MockLlm(), VOICES)
        chosen = {json.loads(r["voice_profile"] or "{}").get("voice_id") for r in
                  p.conn.execute("SELECT voice_profile FROM characters WHERE project_id=?", (pid,))}
        self.assertTrue(chosen <= {30002, 30007})


class BudgetAndCompareTests(unittest.TestCase):
    def test_the_spending_limit_is_off_until_a_test_round_starts(self):
        from core import budget, cost
        p, pid = kenta_project()
        self.assertIsNone(budget.check_video(p.conn, "clipai", "kling-v3-omni", "pro", 15))
        budget.restart(p.conn, usd=1.0)
        self.assertIsNone(budget.check_video(p.conn, "clipai", "kling-v3-omni", "pro", 5))       # $0.40 fits
        cost.record_usage(p.conn, None, "video", "clipai", "kling-v3-omni", "pro", 10, "second", pid)   # $0.80 spent
        self.assertIn("trần ngân sách", budget.check_video(p.conn, "clipai", "kling-v3-omni", "pro", 5))
        self.assertIsNone(budget.check_video(p.conn, "mock", "kling-v3-omni", "pro", 5))          # the simulator never counts
        budget.save(p.conn, image_cap=1)
        cost.record_usage(p.conn, None, "image", "deepix", "seedream", "default", 1, "image", pid)
        self.assertIn("ảnh", budget.check_image(p.conn, "deepix"))
        budget.stop(p.conn)
        self.assertIsNone(budget.check_video(p.conn, "clipai", "kling-v3-omni", "pro", 5))

    def test_a_job_over_the_limit_stays_queued(self):
        from core import batch, budget, cost
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        p, pid = kenta_project()
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        _approve_all_images(p, pid, data)
        _approve_all_motion(p, pid, data)
        budget.restart(p.conn, usd=1.0)
        cost.record_usage(p.conn, None, "video", "clipai", "kling-v3-omni", "pro", 12, "second", pid)     # $0.96 of $1
        provider = MockVideoProvider()
        provider.name = "clipai"                                     # priced like the real service
        provider.usage_info = lambda model=None, duration=5, resolution=None: ("kling-v3-omni", "pro", duration)
        vr = VideoRunner(p, provider, data)
        batch.queue_videos(p, pid, data)
        self.assertEqual(vr.submit_pending(pid), 0)
        self.assertTrue(p.conn.execute("SELECT 1 FROM diag_events WHERE code='budget'").fetchone())
        self.assertFalse(p.conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type='video_gen' AND state!='queued'",
                                        (pid,)).fetchone())

    def test_cheap_test_mode_never_asks_for_1080p_or_kling_pro(self):
        from core import batch, model_router
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        p, pid = kenta_project()
        p.set_project_field(pid, "model_priority", "quality")        # quality asks for Seedance 2.0 at 1080p
        p.set_project_field(pid, "test_quality", 1)
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        choices = [model_router.scene_choice(p.conn, r["id"]) for r in p.conn.execute("SELECT id FROM scenes WHERE project_id=?", (pid,))]
        self.assertFalse(any(c["resolution"] for c in choices))
        self.assertFalse({"seedance", "seedance-2.5"} & {c["model"] for c in choices})  # 2.0 and 2.5 became 2.0 Fast
        _approve_all_images(p, pid, data)
        _approve_all_motion(p, pid, data)
        provider = MockVideoProvider()
        vr = VideoRunner(p, provider, data)
        vr.max_concurrent = 99
        batch.queue_videos(p, pid, data)
        vr.submit_pending(pid)
        self.assertTrue(provider._tasks)
        self.assertTrue(all(t["kling_mode"] == "std" and t["resolution"] in (None, "720p") for t in provider._tasks.values()))

    def test_the_automatic_run_makes_one_picture_per_multishot_group(self):
        from core import autopilot, music, shots
        from core.providers import MockImageProvider, MockVideoProvider
        from core.runner import ImageRunner, VideoRunner
        p, pid = kenta_project(shot_mode="multishot")
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        data = tempfile.mkdtemp()

        def render(pp, i, d, m):
            out = os.path.join(d, str(i), "output", "FINAL_VIDEO.mp4")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "wb").write(b"x")
            return out
        ctx = autopilot.Context(data, ImageRunner(p, MockImageProvider(), data), VideoRunner(p, MockVideoProvider(polls_to_finish=1), data),
                                llm_runner.MockLlm(), music.MockAudioProvider(), render)
        autopilot.set_gates(p, pid, {"bible": False})
        autopilot.start(p, pid)
        from unittest import mock
        with mock.patch("core.claude_tasks.unchecked_videos", return_value=[]):     # the simulator's clips are not real videos
            self.assertEqual(autopilot.run_until_done(p, pid, ctx, max_ticks=400), autopilot.DONE)
        groups = shots.multishot_groups(p.conn, pid)
        count = lambda sql: p.conn.execute(sql, (pid,)).fetchone()[0]  # noqa: E731
        self.assertEqual(count("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'"), len(groups))
        self.assertEqual(count("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='video_gen' AND group_leader IS NULL"), len(groups))

    def test_a_seedance_real_person_refusal_moves_the_continuity_group_to_kling(self):
        from core import batch, model_router, shots
        from core.providers import MockVideoProvider, ProviderError
        from core.runner import VideoRunner
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        _approve_all_motion(p, pid, data)
        provider = MockVideoProvider()
        real_submit, calls = provider.submit, []

        def refuse_first(*a, **k):                     # only the first start picture is refused
            calls.append(a)
            if len(calls) == 1:
                raise ProviderError("[InputImageSensitiveContentDetected.PrivacyInformation] The request failed because the input "
                                    "image 'content[1]' may contain real person.", code="bad_request")
            return real_submit(*a, **k)
        provider.submit = refuse_first
        vr = VideoRunner(p, provider, data)
        vr.max_concurrent = 1
        batch.queue_videos(p, pid, data)
        first = p.conn.execute("SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' ORDER BY id LIMIT 1", (pid,)).fetchone()
        vr.submit_pending(pid)
        group = [r["id"] for r in shots.sequence_rows(p.conn, first["scene_id"])]
        self.assertGreater(len(group), 1)
        self.assertEqual({model_router.scene_choice(p.conn, sid)["model"] for sid in group}, {"kling"})
        other = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND id NOT IN (%s) LIMIT 1" % ",".join("?" * len(group)),
                               (pid, *group)).fetchone()
        self.assertIsNone(p.conn.execute("SELECT video_model FROM motion_prompts WHERE scene_id=?", (other["id"],)).fetchone()[0])

    def test_a_seedance_copyright_block_moves_the_scene_to_kling_but_kling_blocks_do_not(self):
        from core import model_router
        from core.providers import MockVideoProvider, RISK_CONTROL
        from core.runner import VideoRunner
        p, pid = kenta_project(shot_mode=None)
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        _approve_all_motion(p, pid, data)
        vr = VideoRunner(p, MockVideoProvider(), data)
        rows = p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
        msg = "The request failed because the output video may be related to copyright restrictions."
        vr._on_refused({"id": 0, "project_id": pid, "scene_id": rows[0]["id"], "model": "kling"}, RISK_CONTROL, msg)
        self.assertNotEqual(model_router.scene_choice(p.conn, rows[0]["id"])["source"], "override")
        vr._on_refused({"id": 0, "project_id": pid, "scene_id": rows[0]["id"], "model": "seedance-fast"}, RISK_CONTROL, msg)
        self.assertEqual(model_router.scene_choice(p.conn, rows[0]["id"])["model"], "kling")
        self.assertIsNone(p.conn.execute("SELECT video_model FROM motion_prompts WHERE scene_id=?", (rows[1]["id"],)).fetchone()[0])

    def test_the_automatic_run_stops_when_claude_is_out_of_usage(self):
        from core import autopilot
        with self.assertRaises(autopilot._Stop) as ctx:
            autopilot._stop_if_claude_blocked([(1, "Claude Code báo lỗi: You've hit your session limit · resets 7:20am")])
        self.assertIn("hết hạn mức", str(ctx.exception))
        autopilot._stop_if_claude_blocked([(1, "JSON không hợp lệ")])          # an ordinary QC failure does not stop the run

    def test_the_person_can_keep_a_clip_the_qc_agent_rejected_instead_of_paying_again(self):
        from core.states import InvalidTransition
        p, pid = kenta_project(shot_mode=None)
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        data = tempfile.mkdtemp()
        sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (pid,)).fetchone()["id"]
        jid = p.create_job(sid, "video_gen")
        clip = os.path.join(data, "01.mp4")
        open(clip, "wb").write(b"clip")
        p.start(jid)
        p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (clip, jid))
        p.succeed(jid)
        p.reject(jid, "ai_agent", "QC 0.6 < 0.82")                       # the QC agent queues another (paid) take
        retry = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND id>?", (sid, jid)).fetchone()["id"]
        self.assertEqual(p.keepable_rejected(sid)["id"], jid)
        p.keep_rejected(jid)
        self.assertEqual(p.state(jid).value, "approved")
        self.assertEqual(p.state(retry).value, "cancelled")
        other = p.create_job(sid, "video_gen")                           # a person's own rejection is not overridden this way
        p.start(other)
        p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (clip, other))
        p.succeed(other)
        p.reject(other, "user", "không đẹp", respawn=False)
        self.assertIsNone(p.keepable_rejected(sid))
        with self.assertRaises(InvalidTransition):
            p.keep_rejected(other)

    def test_a_kling_multishot_prompt_is_cut_to_512_characters_at_a_sentence(self):
        from core.adapters.clipai import KLING_SHOT_PROMPT_LIMIT, _shorten
        text = "Kenta draws his katana. " * 40
        out = _shorten(text, KLING_SHOT_PROMPT_LIMIT)
        self.assertLessEqual(len(out), 512)
        self.assertTrue(out.endswith("."))
        self.assertEqual(_shorten("short.", 512), "short.")

    def test_claude_api_calls_are_priced_in_the_ledger_and_stop_at_the_claude_cap(self):
        import json as _json
        from core import budget
        from core.adapters.http import HttpResponse
        from core.db import connect
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)
        calls = []

        def transport(method, url, headers, body, timeout):
            calls.append(url)
            return HttpResponse(200, _json.dumps({"content": [{"type": "text", "text": "OK"}],
                                                   "usage": {"input_tokens": 500_000, "output_tokens": 100_000}}).encode())
        client = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=transport, ledger=db)
        self.assertEqual(client.complete("hi").text, "OK")
        s = budget.status(conn)
        self.assertAlmostEqual(s["llm_spent"], 0.5 * 2.0 + 0.1 * 10.0)            # $2 / $10 per million tokens
        self.assertAlmostEqual(budget.spent(conn)["usd"], 2.0)                       # counts in the test round's total too
        budget.save(conn, llm_usd=2.0)                                               # the $2 are used up
        with self.assertRaises(llm_runner.LlmError) as err:
            client.complete("again")
        self.assertEqual(err.exception.code, "budget")
        self.assertEqual(len(calls), 1)                                              # refused before paying
        budget.restart_llm(conn, 5.0)                                                # topped up: count from now
        self.assertEqual(client.complete("after top-up").text, "OK")
        free = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=transport)   # no ledger: nothing written
        free.complete("x")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM usage_events WHERE kind='llm'").fetchone()[0], 4)

    def test_the_api_client_shrinks_a_picture_over_5_mb_and_leaves_room_for_a_long_answer(self):
        import base64 as _b64
        import json as _json
        import random
        from PIL import Image
        from core.adapters.http import HttpResponse
        path = os.path.join(tempfile.mkdtemp(), "sheet.png")
        rnd = random.Random(1)
        Image.frombytes("RGB", (1600, 1400), bytes(rnd.getrandbits(8) for _ in range(1600 * 1400 * 3))).save(path)
        self.assertGreater(os.path.getsize(path), 5 * 1024 * 1024)                  # like the contact sheet of a whole project
        sent = []

        def transport(method, url, headers, body, timeout):
            sent.append((_json.loads(body), timeout))
            return HttpResponse(200, _json.dumps({"content": [{"type": "text", "text": "OK"}], "usage": {}}).encode())
        llm_runner.AnthropicClient("sk-test", transport=transport).complete("check", [("Tấm ghép:", path)])
        payload, timeout = sent[0]
        image = next(b for b in payload["messages"][0]["content"] if b["type"] == "image")
        self.assertEqual(image["source"]["media_type"], "image/jpeg")
        self.assertLessEqual(len(_b64.b64decode(image["source"]["data"])), 5 * 1024 * 1024)
        self.assertEqual(payload["max_tokens"], 32000)                                 # a 26-shot Director plan is ~10-20k tokens
        self.assertGreaterEqual(timeout, 600)

    def test_every_dialog_the_dashboard_opens_is_known_to_open_dialog(self):
        import glob
        import re
        root = os.path.join(os.path.dirname(__file__), "..", "dashboard")
        text = "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(root, "**", "*.py"), recursive=True))
        flags = set(re.findall(r'open_dialog\("(dlg_\w+)"\)', text))
        known = set(re.search(r"DIALOG_FLAGS = \(([^)]*)\)", text).group(1).replace('"', "").replace(" ", "").split(","))
        self.assertTrue(flags)
        self.assertEqual(flags - known, set())        # a flag missing there never opens its dialog

    def test_a_clone_starts_from_the_same_point_without_any_result(self):
        from core import compare, shots
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        p.create_job(shots.shots_of(p, pid)[0]["id"])
        new = compare.clone_project(p, pid, "bản multi-shot", "multishot")
        self.assertEqual(shots.mode(p.project(new)), "multishot")
        self.assertEqual(len(shots.shots_of(p, new)), len(shots.shots_of(p, pid)))
        self.assertEqual(len(shots.story_scenes(p, new)), 3)
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM characters WHERE project_id=?", (new,)).fetchone()[0], 3)
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=?", (new,)).fetchone()[0], 0)
        self.assertEqual(p.project(new)["render_settings"], p.project(pid)["render_settings"])     # same end card
        bare = compare.clone_project(p, pid, "chạy lại Director", None, with_rows=False)
        self.assertEqual([r["title"] for r in p.conn.execute("SELECT title FROM scenes WHERE project_id=? ORDER BY idx", (bare,))],
                         [s["heading"] for s in shots.story_scenes(p, pid)])     # one row per script scene, as after the import
        llm_runner.run_director(p, bare, llm_runner.MockLlm())                    # the v2 Director works on the copy
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (bare,)).fetchone()[0], 3)

    def test_metrics_scores_and_report(self):
        from core import compare
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        other = compare.clone_project(p, pid, "v2", None, with_rows=False)
        compare.save_scores(p.conn, pid, {"characters": 4, "overall": 5, "note": "ổn", "bogus": 9})
        self.assertEqual(compare.get_scores(p.conn, pid), {"characters": 4, "overall": 5, "note": "ổn"})
        rows = [compare.metrics(p, i, tempfile.mkdtemp()) for i in (pid, other)]
        self.assertEqual(rows[0]["shots"], 25)
        table = compare.report_markdown(rows)
        self.assertIn("Số shot / clip", table)
        self.assertIn("Điểm của bạn — Tổng thể", table)


if __name__ == "__main__":
    unittest.main()
