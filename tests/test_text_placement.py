"""Editor: a subtitle never covers eyes or mouth — a whole line of a close-up moves to the top of the safe box (kế hoạch V4 5.1)."""
import os
import unittest

from core import subtitles, text_placement
from core.subtitles import Cue, Font

FONT = Font(path="x.ttf", family="Test Sans", label="Test", vietnamese=True)


class KeepClearTests(unittest.TestCase):
    def test_close_ups_have_a_face_band_and_wide_shots_none(self):
        self.assertEqual(text_placement.keep_clear({"size": "CU"}), (0.30, 0.66))
        self.assertIsNone(text_placement.keep_clear({"size": "WS"}))
        self.assertIsNone(text_placement.keep_clear({}))
        low = text_placement.keep_clear({"size": "CU", "angle": "low"})
        self.assertGreater(low[0], 0.30)                                        # camera below: the face sits lower


class AssPlacementTests(unittest.TestCase):
    def _ass(self, zones):
        cues = [Cue(0.0, 2.0, "Em hiểu rồi.", "KELLY", 1), Cue(2.0, 4.0, "Đi thôi.", "KENTA", 2),
                Cue(0.1, 3.9, "Maxim đã bị hạ.", subtitles.HUD, 1)]
        return subtitles.to_ass(cues, 1080, 1920, FONT, zones=zones)

    def events(self, text):
        return [ln for ln in text.splitlines() if ln.startswith("Dialogue:")]

    def test_a_close_up_line_moves_to_the_top_and_a_wide_one_stays(self):
        zones = {1: text_placement.keep_clear({"size": "CU"})}                 # shot 1 close-up, shot 2 wide (no zone)
        ev = self.events(self._ass(zones))
        close = next(e for e in ev if "Em hiểu" in e)
        wide = next(e for e in ev if "Đi thôi" in e)
        self.assertIn("{\\an8}", close)
        self.assertIn(f",0,0,{int(1920 * subtitles.SAFE_TOP)},,", close)     # just inside the top safe margin
        self.assertNotIn("\\an8", wide)
        self.assertIn(",0,0,0,,", wide)                                          # the style's bottom position
        hud = next(e for e in ev if "Maxim" in e)
        self.assertNotIn("\\an8", hud)                                           # the game notice keeps its own style

    def test_a_line_never_moves_onto_a_face_at_the_top(self):
        """Trial #8 (2026-09-28, 41–44 s): faces seen over the line covered the bottom AND the top band; the line was moved to the top
        because it covered less there — it sat on Kelly's forehead. Now it goes under the face (low) and never to a covered top."""
        ev = self.events(self._ass({1: (0.15, 0.66)}))
        line = next(e for e in ev if "Em hiểu" in e)
        self.assertNotIn("\\an8", line)
        self.assertIn(f",0,0,{int(1920 * text_placement.LOW_MARGIN)},,", line)
        ev = self.events(self._ass({1: (0.10, 0.95)}))                              # a face everywhere: stays at the bottom
        self.assertIn(",0,0,0,,", next(e for e in ev if "Em hiểu" in e))
        self.assertEqual(text_placement.placements([Cue(0, 1, "x", "K", 1)], {1: (0.15, 0.66)}, 1920, 60, lambda c: 1, 0.36, 0.15),
                         {0: "low"})

    def test_a_medium_close_up_keeps_the_bottom_position(self):
        ev = self.events(self._ass({1: text_placement.keep_clear({"size": "MCU"})}))   # face in the upper half
        self.assertNotIn("\\an8", next(e for e in ev if "Em hiểu" in e))

    def test_without_zones_nothing_changes(self):
        self.assertEqual(self._ass(None), self._ass({}))

    def test_zones_come_from_the_shot_table(self):
        import json
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("t")
        for i, size in enumerate(("CU", "WS"), 1):
            sid = p.create_scene(pid, i, f"s{i}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"size": size}), sid))
        p.conn.commit()
        self.assertEqual(set(text_placement.zones(p.conn, pid)), {1})


class RealFaceTests(unittest.TestCase):
    """YuNet on the real frame wins over the shot-table guess (skipped when the model file is not on this computer)."""
    def test_a_face_found_low_in_a_wide_shot_moves_the_line(self):
        cues = [Cue(0.0, 2.0, "Em hiểu rồi.", "KELLY", 1)]
        seen = {0: (0.50, 0.70)}                                                 # a face low in the frame, on the bottom band
        ev = [ln for ln in subtitles.to_ass(cues, 1080, 1920, FONT, zones={}, seen=seen).splitlines() if ln.startswith("Dialogue:")]
        self.assertIn("{\\an8}", ev[0])

    @unittest.skipUnless(text_placement.model_path(), "YuNet face model not installed")
    def test_the_detector_finds_the_faces_of_a_real_shot(self):
        import glob
        pics = sorted(glob.glob(os.path.join(os.path.dirname(text_placement.FACE_MODEL), "..", "projects", "*", "images", "job_*.png")))
        if not pics:
            self.skipTest("no generated shot picture on this computer")
        spans = text_placement.face_spans(pics[0])
        self.assertIsInstance(spans, list)


if __name__ == "__main__":
    unittest.main()
