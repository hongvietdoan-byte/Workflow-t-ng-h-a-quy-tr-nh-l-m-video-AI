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


class PovReviewFixTests(unittest.TestCase):
    """rà quy ước 7 (17/10) của bản sửa POV."""

    def _pov(self, **kw):
        return pc.camera_for(dict({"angle": "pov", "size": "WS"}, **kw), SPOT, FACING, 1.75)

    def test_lights_keep_left_right_for_a_pov_camera(self):
        cam = self._pov()["camera"]
        rigs = plate_choice.light_rigs([{"kind": "lamp", "where": "left", "rgb": (1, 1, 1)}], list(SPOT), pc.light_origin(cam))
        loc = rigs[0]["location"]
        self.assertGreater(math.hypot(loc[0] - SPOT[0], loc[1] - SPOT[1]), 1.0)      # before: every light fell on the camera
        fwd = (math.sin(math.radians(FACING)), math.cos(math.radians(FACING)))
        right = (fwd[1], -fwd[0])
        self.assertLess((loc[0] - SPOT[0]) * right[0] + (loc[1] - SPOT[1]) * right[1], -1.0)   # frame left of the eyes

    def test_a_pov_and_a_front_shot_of_one_setup_do_not_share_a_camera(self):
        shots = [{"id": 1, "data": {"angle": "pov", "size": "WS", "camera_setup": "A", "story_scene": 1}},
                 {"id": 2, "data": {"angle": "eye", "size": "WS", "camera_setup": "A", "story_scene": 1}}]
        cams = pc.plan_cameras(shots, lambda s: (SPOT, FACING), lambda s: 1.75)
        self.assertTrue(cams[1].get("pov"))
        self.assertFalse(cams[2].get("pov"))
        self.assertNotIn("shared_with", cams[2])

    def test_pov_view_words_never_say_behind_the_character(self):
        entry = {"spots": {"s": {"at": list(SPOT), "facing": FACING}}, "default_spot": "s", "anchor": [1.6, 4.3, 1.0]}
        for bg in ("landmark", "away"):
            v = plate_choice.view_of(entry, dict(entry["spots"]["s"], name="s"),
                                     {"angle": "pov", "plate_view": {"background": bg, "why": "x"}})
            self.assertNotIn("character", v["words_en"])
            self.assertIn("eyes", v["words_en"])

    def test_pov_light_sentence_lights_no_character(self):
        lights = [{"kind": "lamp", "where": "left", "rgb": (1, 1, 1), "color_name": "warm", "name": "desk lamp"}]
        text = plate_choice.light_sentence(lights, True, "night", {"angle": "pov", "characters": ["Kelly"]})
        self.assertNotIn("Light the character", text)

    def test_pov_light_words_no_rim_light(self):
        from core import location_pack
        cam = self._pov()["camera"]
        rec = {"camera_plan": cam}
        self.assertEqual(location_pack.light_words(rec, FACING + 180, {"angle": "pov", "characters": ["Kelly"]}), "")

    def test_stage_pov_camera_on_the_spot_has_no_stand_in_box(self):
        sc = {"location": [SPOT[0], SPOT[1], 1.6], "look_at": [1.6, 4.3, 1.6], "lens": 20, "pov": "Kelly"}
        cam = pc.from_stage(sc, SPOT, 1.75)
        self.assertTrue(cam["camera"].get("pov"))
        self.assertIsNone(cam["subject_box"])
        far = pc.from_stage(dict(sc, location=[SPOT[0] + 3, SPOT[1], 1.6]), SPOT, 1.75)   # POV of someone else looking at the spot
        self.assertFalse(far["camera"].get("pov"))
        self.assertIsNotNone(far["subject_box"])

    def test_pov_travel_why_says_eyes(self):
        cam = pc.travel_camera({"angle": "pov", "size": "WS"}, SPOT, SPOT, (SPOT[0] - 3, SPOT[1] + 4, 0.0), "lead", 1.75)
        self.assertIn("POV", cam["why"]["travel"])
        self.assertNotIn("LÙI", cam["why"]["travel"])

    def test_side_truth_pov_left_is_frame_left(self):
        from core import side_truth
        self.assertEqual(side_truth.camera_relation({"angle": "pov"})[0], "behind")

    def test_geometry_sentence_keeps_the_eye_height_of_a_pov(self):
        from core import place_refs
        cam = dict(self._pov()["camera"], model_coords=True)
        text = place_refs.geometry_sentence({"camera_plan": cam, "camera": {}}, {"angle": "pov"})
        self.assertIn("1.6 m above the ground", text)


if __name__ == "__main__":
    unittest.main()
