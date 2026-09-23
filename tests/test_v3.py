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


if __name__ == "__main__":
    unittest.main()
