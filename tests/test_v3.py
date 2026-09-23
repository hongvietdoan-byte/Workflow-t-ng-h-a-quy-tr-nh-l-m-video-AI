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


if __name__ == "__main__":
    unittest.main()
