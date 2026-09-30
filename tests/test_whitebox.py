"""S10.6 (30/09): coarse white model — one coloured block per person at a measured spot of the real 3D place, as a Seedance 2.5 reference."""
import math
import unittest

from core import whitebox

M3D = {"path": "x.fbx", "anchor": [0.0, 20.0, 30.0], "spots": {
    "front": {"at": [0.0, 0.0, 2.0], "label": "trước tháp"},
    "side": {"at": [5.0, 0.0, 2.0], "view": [15.0, 0.0, 3.0], "label": "nhìn sang đông"}}}


class WhiteboxTests(unittest.TestCase):
    def test_people_stand_where_the_camera_says(self):
        anim = whitebox.plan(M3D, "front", [{"name": "KENTA", "at": [8, -2]}, {"name": "ORION", "at": [10, 3], "face": "KENTA"}])
        cam = anim["keys"][0]
        self.assertEqual(cam["location"], [0.0, 0.0, 2.0 + whitebox.EYE])          # the spot, at eye height
        self.assertEqual(cam["look_at"], [0.5, 9.0, 3.2])                           # aimed at the group's middle, chest height
        kenta, orion = anim["actors"]
        self.assertEqual(kenta["keys"][0]["location"], [-2.0, 8.0, 2.0])          # camera looks north: ahead = +y, right = +x
        self.assertEqual(orion["keys"][0]["location"], [3.0, 10.0, 2.0])
        self.assertEqual(orion["keys"][0]["face"], kenta["keys"][0]["location"])  # Orion faces Kenta
        self.assertEqual(kenta["keys"][0]["face"][:2], [0.0, 0.0])                # default: faces the camera
        self.assertEqual((kenta["color_name"], orion["color_name"]), ("red", "blue"))
        self.assertGreaterEqual(anim["seconds"], 3.0)                             # ClipAI: reference videos ≥ 3 s
        self.assertTrue(anim["white"])

    def test_a_spot_with_a_view_looks_along_it_and_movement_is_keyed(self):
        anim = whitebox.plan(M3D, "side", [{"name": "KELLY", "at": [6, 0], "to": [3, 1]}], seconds=2, aim="spot")
        a = anim["actors"][0]
        self.assertEqual(a["keys"][0]["location"], [11.0, 0.0, 2.0])              # looking east: ahead = +x
        self.assertEqual(a["keys"][1]["location"], [8.0, -1.0, 2.0])              # right of an east-looking camera = -y
        self.assertEqual(anim["seconds"], 3.2)

    def test_the_prompt_maps_every_block_to_one_person(self):
        anim = whitebox.plan(M3D, "front", [{"name": "KENTA", "at": [8, 0]}, {"name": "ORION", "at": [9, 2]}, {"name": "KELLY", "at": [12, -3]}])
        line = whitebox.role_line(anim, 2)
        self.assertIn("@Video 2 is a coarse white-model reference", line)
        self.assertIn("The red block in @Video 2 is KENTA.", line)
        self.assertIn("The yellow block in @Video 2 is KELLY.", line)
        self.assertIn("Do not take its plain grey clay look", line)

    def test_errors_are_said(self):
        with self.assertRaises(whitebox.WhiteboxError):
            whitebox.plan(M3D, "nowhere", [{"name": "A", "at": [1, 0]}])
        with self.assertRaises(whitebox.WhiteboxError):
            whitebox.plan(M3D, "front", [])
        with self.assertRaises(whitebox.WhiteboxError):
            whitebox.plan(M3D, "front", [{"name": "A", "at": [1, 0], "face": "B"}])


if __name__ == "__main__":
    unittest.main()
