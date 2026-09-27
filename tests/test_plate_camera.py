"""Virtual camera of a shot on a 3D place (core/plate_camera.py): the character fills the frame the way the shot size says, stands on
the side the start frame says, and one camera set-up shares one camera."""
import unittest

from core import plate_camera as pc

SPOT = (12.68, -17.0, 25.93)          # clock tower plaza, in front of the tower (scene metres)


class FramingTests(unittest.TestCase):
    def test_a_wide_shot_shows_the_whole_body_and_a_medium_shot_cuts_at_the_waist(self):
        wide = pc.camera_for({"size": "WS"}, SPOT, 0.0, 1.70)
        x0, y0, x1, y1 = wide["subject_box"]
        self.assertAlmostEqual(y1 - y0, 0.55, delta=0.06)                    # full body over ~55 % of the frame
        self.assertLess(y1, 1.0)                                              # feet inside the frame
        ms = pc.camera_for({"size": "MS"}, SPOT, 0.0, 1.70)
        self.assertAlmostEqual(ms["subject_box"][1], pc.HEADROOM["MS"], delta=0.04)   # head near the top
        self.assertGreater(ms["subject_box"][3], 1.2)                         # legs out of frame
        self.assertLess(ms["distance_m"], wide["distance_m"])

    def test_close_up_uses_a_longer_lens_and_stands_closer(self):
        cu, ws = pc.camera_for({"size": "CU"}, SPOT, 0.0, 1.70), pc.camera_for({"size": "WS"}, SPOT, 0.0, 1.70)
        self.assertGreater(cu["camera"]["lens"], ws["camera"]["lens"])
        self.assertLess(cu["distance_m"], 2.0)

    def test_the_camera_stands_where_the_character_looks(self):
        cam = pc.camera_for({"size": "MS"}, SPOT, 0.0, 1.70)["camera"]        # facing +y
        self.assertGreater(cam["location"][1], SPOT[1])
        back = pc.camera_for({"size": "MS", "angle": "ots"}, SPOT, 0.0, 1.70)["camera"]
        self.assertLess(back["location"][1], SPOT[1])                         # over the shoulder: from behind

    def test_side_words_move_the_character_across_the_frame(self):
        left = pc.camera_for({"size": "MS", "start_frame": "Kelly frame-left, facing camera"}, SPOT, 0.0, 1.70)
        right = pc.camera_for({"size": "MS", "start_frame": "Kelly stands frame-right"}, SPOT, 0.0, 1.70)
        mid = lambda b: (b[0] + b[2]) / 2  # noqa: E731
        self.assertLess(mid(left["subject_box"]), 0.45)
        self.assertGreater(mid(right["subject_box"]), 0.55)

    def test_low_and_high_angles(self):
        low = pc.camera_for({"size": "MS", "angle": "low"}, SPOT, 0.0, 1.70)["camera"]
        high = pc.camera_for({"size": "MS", "angle": "high"}, SPOT, 0.0, 1.70)["camera"]
        self.assertLess(low["location"][2], SPOT[2] + 1.0)
        self.assertGreater(high["location"][2], SPOT[2] + 1.70)
        self.assertEqual((low["angle"], high["angle"]), ("low_angle", "high_angle"))

    def test_a_camera_setup_shares_one_camera(self):
        shots = [{"id": 1, "data": {"size": "MS", "camera_setup": "A", "story_scene": 1}},
                 {"id": 2, "data": {"size": "MS", "camera_setup": "A", "story_scene": 1}},
                 {"id": 3, "data": {"size": "CU", "camera_setup": "B", "story_scene": 1}}]
        cams = pc.plan_cameras(shots, lambda s: (SPOT, 0.0), lambda s: 1.70)
        self.assertEqual(cams[1]["camera"], cams[2]["camera"])
        self.assertNotEqual(cams[1]["camera"]["location"], cams[3]["camera"]["location"])

    def test_a_high_angle_tilts_about_30_degrees_even_close(self):
        """Trial #8 (2026-09-27): WS / MS 'high' 1–2 m away came out 56–62° down — the plate was the floor seen from above."""
        import math
        for size in ("WS", "MS", "CU"):
            c = pc.camera_for({"size": size, "angle": "high"}, SPOT, 0.0, 1.75)["camera"]
            d = [a - b for a, b in zip(c["look_at"], c["location"])]
            tilt = math.degrees(math.atan2(-d[2], math.hypot(d[0], d[1])))
            self.assertAlmostEqual(tilt, pc.HIGH_TILT_DEG, delta=3, msg=size)


if __name__ == "__main__":
    unittest.main()
