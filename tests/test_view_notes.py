"""Root fixes from the agent QC of #8 (2026-09-27): left/right and a reversed cap said for the shot's view (from behind vs facing), the gaze
tied to the blocking, a flashback lit differently from the present day."""
import os
import unittest
from unittest import mock

from core import runner, scene_establish
from tests._flags import flags_clear, flags_on, flags_on_ctx, flags_on_deco  # noqa: F401

KENTA = {"approved": True, "view_notes": {
    "facing_camera": "Facing the camera, KENTA's gauntlet arm (his LEFT) is on the RIGHT side of the frame",
    "from_behind": "Seen from behind, KENTA's gauntlet arm (his LEFT) is on the LEFT side of the frame"}}


class ViewNotesTests(unittest.TestCase):
    def test_which_view_the_shot_shows(self):
        ots = {"angle": "ots", "image_prompt": "medium shot over KENTA's shoulder, MAXIM facing him", "characters": ["KENTA", "MAXIM"]}
        self.assertTrue(runner.seen_from_behind(ots, "KENTA"))
        self.assertIsNone(runner.seen_from_behind(ots, "MAXIM"))          # an OTS shot without words for MAXIM: both notes, labelled
        self.assertFalse(runner.seen_from_behind({"angle": "eye", "image_prompt": "KENTA faces the camera"}, "KENTA"))
        self.assertTrue(runner.seen_from_behind({"blocking": "qua vai KENTA, Kelly ở giữa"}, "KENTA"))

    def test_the_note_of_the_view_goes_in(self):
        with mock.patch("core.assets.standard_for", side_effect=lambda c, p, n: KENTA if n == "KENTA" else None):
            behind = runner.view_notes(None, 1, {"characters": ["KENTA"], "image_prompt": "over KENTA's shoulder"})
            front = runner.view_notes(None, 1, {"characters": ["KENTA"], "angle": "eye", "image_prompt": "KENTA speaks"})
        self.assertIn("LEFT side of the frame", behind)
        self.assertNotIn("RIGHT side", behind)
        self.assertIn("RIGHT side of the frame", front)

    def test_a_flashback_has_its_own_light(self):
        flags_on(self, "scene_establishing")
        self.assertEqual(scene_establish.light_sentence({"time": "day", "action": "Flashback: Kenta nói với Maxim về lời hứa"}),
                         scene_establish.FLASHBACK)
        self.assertNotEqual(scene_establish.light_sentence({"time": "day", "action": "Kenta chạy"}), scene_establish.FLASHBACK)

    def test_scene_notes_that_mention_a_flashback_elsewhere_do_not_make_the_shot_one(self):
        """#8: scene 4's beat 'plant for the flashback promise in scene 5' turned every redraw of S4·2 into a sunset."""
        flags_on(self, "scene_establishing")
        shot = {"time": "day", "action": "Kelly nói lời trách móc", "image_prompt": "medium close-up, Kelly facing camera",
                "beat": {"setup": "plant trực tiếp cho lời hứa flashback ở Cảnh 5"},
                "lighting": "tông trung tính; flashback dùng ánh sáng ấm hơn"}
        self.assertFalse(scene_establish.is_flashback(shot))
        self.assertEqual(scene_establish.light_sentence(shot), scene_establish.LIGHT["day"])
        self.assertTrue(scene_establish.is_flashback({"flashback": True}))

    def test_a_storyboard_is_lit_as_a_flashback_only_when_every_frame_is_one(self):
        from core import scene_storyboard
        flags_on(self, "scene_establishing")
        conn = mock.MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        g = {"story_scene": 5, "shots": [{"data": {"time": "day", "action": "Kenta cõng Maxim"}},
                                          {"data": {"time": "day", "action": "Flashback: lời hứa"}}]}
        text = scene_storyboard.story_text(conn, 1, g)
        self.assertNotIn("FLASHBACK", text)
        self.assertIn(scene_establish.LIGHT["day"], text)

    def test_the_gaze_follows_the_blocking(self):
        self.assertTrue(runner._GAZE.search("MAXIM looking toward frame-left where KENTA runs"))
        self.assertFalse(runner._GAZE.search("three people run side by side"))


if __name__ == "__main__":
    unittest.main()
