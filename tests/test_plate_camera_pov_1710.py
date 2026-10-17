"""17/10 #31 shot 1/2/3/5: a POV shot (angle 'pov') — the camera IS the character's eyes. Before: camera_for put it in front of the
spot looking back (180° wrong: shot 3 rendered the empty wall behind Kelly, not the two doors) and view_of turned the background
round. Now: the camera stands at the spot's eye height and looks where the spot / plate_view says; no stand-in at the camera."""
import math
import unittest

from core import plate_camera as pc
from core import plate_choice

SPOT = (4.6, 0.45, 0.0)                    # #31 'goc_nhin_kelly_2_cua'
FACING = 323.0                              # the spot looks at the two doors (view point [1.6, 4.3])


def _yaw(cam):
    loc, aim = cam["camera"]["location"], cam["camera"]["look_at"]
    return math.degrees(math.atan2(aim[0] - loc[0], aim[1] - loc[1])) % 360


class PovCameraTests(unittest.TestCase):
    def test_pov_camera_stands_at_the_eyes_and_looks_forward(self):
        cam = pc.camera_for({"angle": "pov", "size": "WS"}, SPOT, FACING, 1.75)
        loc = cam["camera"]["location"]
        self.assertAlmostEqual(loc[0], SPOT[0], places=2)
        self.assertAlmostEqual(loc[1], SPOT[1], places=2)
        self.assertAlmostEqual(loc[2], 1.75 * pc.POV_EYE_SHARE, places=2)
        self.assertAlmostEqual(_yaw(cam), FACING, delta=0.5)                 # looks at the doors, not back at the wall
        self.assertAlmostEqual(cam["pitch_deg"], 0.0, delta=0.5)
        self.assertTrue(cam["pov"])
        self.assertTrue(cam["camera"]["pov"])
        self.assertIsNone(cam["subject_box"])                                 # nobody stands in a POV frame
        self.assertIn("pov", cam["why"])

    def test_pov_ignores_behind_and_keeps_the_shot_lens(self):
        a = pc.camera_for({"angle": "pov", "size": "WS", "lens_mm": 20}, SPOT, FACING, 1.75, behind=True)
        self.assertAlmostEqual(_yaw(a), FACING, delta=0.5)
        self.assertEqual(a["camera"]["lens"], 20)

    def test_pov_looking_down_tilts_down(self):
        cam = pc.camera_for({"angle": "pov", "size": "MS", "action": "Kelly looks down at the floor"}, SPOT, FACING, 1.75)
        if pc.looks_down({"angle": "pov", "action": "Kelly looks down at the floor"}):
            self.assertLess(cam["pitch_deg"], -10)

    def test_the_wide_of_a_pov_stays_at_the_eyes(self):
        cam = pc.camera_for({"angle": "pov", "size": "WS"}, SPOT, FACING, 1.75)
        wide = pc.wide_for(cam["camera"], 1.75, frame_h=cam["frame_h_m"])
        self.assertEqual(wide["location"], cam["camera"]["location"])          # pulled back = through the wall behind
        self.assertLess(wide["lens"], cam["camera"]["lens"] + 1e-6)
        self.assertTrue(wide["wide"])

    def test_other_angles_unchanged(self):
        cam = pc.camera_for({"angle": "eye", "size": "WS"}, SPOT, FACING, 1.75)
        self.assertAlmostEqual(_yaw(cam), (FACING + 180) % 360, delta=0.5)   # in front of the character, looking at them
        self.assertNotIn("pov", cam["camera"])


class PovViewTests(unittest.TestCase):
    ENTRY = {"spots": {"s": {"at": list(SPOT), "facing": FACING}}, "default_spot": "s", "anchor": [1.6, 4.3, 1.0]}

    def test_spot_default_background_is_where_the_pov_looks(self):
        v = plate_choice.view_of(self.ENTRY, dict(self.ENTRY["spots"]["s"], name="s"), {"angle": "pov"})
        self.assertAlmostEqual(v["background_deg"], FACING, delta=0.5)
        self.assertAlmostEqual(v["facing_deg"], FACING, delta=0.5)            # camera_for looks along it

    def test_script_landmark_pov_looks_at_the_landmark(self):
        data = {"angle": "pov", "plate_view": {"background": "landmark", "why": "thấy hai cửa"}}
        v = plate_choice.view_of(self.ENTRY, dict(self.ENTRY["spots"]["s"], name="s"), data)
        to_mark = plate_choice.bearing(SPOT, self.ENTRY["anchor"])
        self.assertAlmostEqual(v["background_deg"], to_mark, delta=0.5)
        cam = pc.camera_for(data, SPOT, v["facing_deg"], 1.75)
        self.assertAlmostEqual(_yaw(cam), to_mark, delta=0.5)

    def test_eye_shot_view_unchanged(self):
        v = plate_choice.view_of(self.ENTRY, dict(self.ENTRY["spots"]["s"], name="s"), {"angle": "eye"})
        self.assertAlmostEqual(v["background_deg"], (FACING + 180) % 360, delta=0.5)


if __name__ == "__main__":
    unittest.main()
