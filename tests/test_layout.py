"""Scene layout (previz 2D): perspective sizes, feet kept on the ground, drawing order, cut-outs vs mannequins, storyboard sheet."""
import io
import os
import shutil
import tempfile
import unittest

from PIL import Image, ImageDraw

from core import layout

W, H = 1280, 720
ANALYSIS = {"camera": "eye", "horizon_y": 0.40, "ground": [[0, 0.62], [1, 0.62], [1, 1], [0, 1]],
            "landmarks": [{"name": "door", "box": [860 / W, 0.44, 940 / W, 0.62], "height_m": 2.0}]}


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.bg = os.path.join(self.dir, "bg.png")
        img = Image.new("RGB", (W, H), (150, 190, 230))
        ImageDraw.Draw(img).rectangle([0, int(0.4 * H), W, H], fill=(170, 150, 110))
        img.save(self.bg)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def shot(self, *people):
        return {"background": "bg", "redraw": False, "people": [dict({"facing": "camera"}, **p) for p in people]}

    def test_the_camera_height_comes_from_a_landmark_of_known_size(self):
        self.assertAlmostEqual(layout.camera_height(ANALYSIS), 2.0 * 0.22 / 0.18, places=3)
        no_landmark = dict(ANALYSIS, landmarks=[], camera_height_m=5.0)
        self.assertEqual(layout.camera_height(no_landmark), 5.0)
        self.assertEqual(layout.camera_height(dict(no_landmark, camera_height_m=None, camera="high")),
                         layout.DEFAULT_CAMERA_HEIGHT_M["high"])

    def test_a_person_beside_the_door_is_as_tall_as_the_door_says(self):
        door = 0.62 - 0.44
        self.assertAlmostEqual(layout.person_height(ANALYSIS, 0.62), door * 1.75 / 2.0, places=3)
        self.assertGreater(layout.person_height(ANALYSIS, 0.95), layout.person_height(ANALYSIS, 0.7))   # nearer = bigger

    def test_a_high_camera_makes_people_smaller_than_an_eye_level_one(self):
        high = {"camera": "high", "horizon_y": 0.1, "camera_height_m": 10, "ground": ANALYSIS["ground"]}
        self.assertLess(layout.person_height(high, 0.8), layout.person_height(dict(high, camera_height_m=1.6), 0.8))

    def test_feet_off_the_ground_are_moved_onto_it(self):
        self.assertEqual(layout.on_ground(ANALYSIS, (0.5, 0.8)), (0.5, 0.8))
        x, y = layout.on_ground(ANALYSIS, (0.8, 0.3))                           # on the wall / in the sky
        self.assertAlmostEqual(y, 0.62)
        self.assertAlmostEqual(x, 0.8)

    def test_people_are_drawn_farthest_first_and_a_move_is_reported(self):
        placed = layout.place(ANALYSIS, self.shot({"name": "A", "foot": [0.2, 0.95]}, {"name": "B", "foot": [0.8, 0.3]}))
        self.assertEqual([p["name"] for p in placed], ["B", "A"])
        self.assertTrue(placed[0]["moved"])
        self.assertFalse(placed[1]["moved"])

    def test_compose_draws_mannequins_and_the_note_says_who_is_which_colour(self):
        out = os.path.join(self.dir, "l.png")
        img, people = layout.compose(self.bg, ANALYSIS, self.shot({"name": "KELLY", "foot": [0.3, 0.9], "facing": "right"}), out_path=out)
        self.assertEqual(img.size, layout.SIZE)
        self.assertTrue(os.path.exists(out))
        torso = int((0.9 - people[0]["height"] * 0.7) * H)
        self.assertEqual(img.getpixel((int(0.3 * W), torso)), layout.COLORS[0])        # the red figure stands there
        note = layout.layout_note(people)
        self.assertIn("the red figure is KELLY", note)
        self.assertIn("keep its camera angle", note)

    def test_a_cut_out_picture_is_used_instead_of_a_mannequin(self):
        fig = Image.new("RGBA", (100, 300), (0, 0, 0, 0))
        ImageDraw.Draw(fig).rectangle([30, 10, 70, 299], fill=(10, 200, 10, 255))
        buf = os.path.join(self.dir, "kelly.png")
        fig.save(buf)
        img, people = layout.compose(self.bg, ANALYSIS, self.shot({"name": "KELLY", "foot": [0.5, 0.9]}), {"KELLY": buf})
        self.assertEqual(img.getpixel((W // 2, int(0.9 * H) - 40))[:3], (10, 200, 10))
        self.assertNotIn("figure is KELLY", layout.layout_note(people, has_cutouts=True))

    def test_an_opaque_picture_is_not_treated_as_a_cut_out(self):
        buf = io.BytesIO()
        Image.new("RGB", (50, 80), (1, 2, 3)).save(buf, "PNG")
        path = os.path.join(self.dir, "opaque.png")
        open(path, "wb").write(buf.getvalue())
        self.assertIsNone(layout._cutout(path))
        self.assertIsNone(layout._cutout(os.path.join(self.dir, "missing.png")))

    def test_bad_analyses_and_layouts_are_refused(self):
        for bad in ({}, dict(ANALYSIS, camera="drone"), dict(ANALYSIS, horizon_y=None), dict(ANALYSIS, ground=[[0, 1]]),
                    dict(ANALYSIS, landmarks=[{"name": "x", "box": [0.5, 0.5, 0.4, 0.6], "height_m": 2}])):
            with self.assertRaises(layout.LayoutError):
                layout.validate_set_analysis(bad)
        layout.validate_set_analysis(dict(ANALYSIS, camera="top", horizon_y=None))     # straight down needs no horizon
        with self.assertRaises(layout.LayoutError):
            layout.validate_shot_layout(self.shot({"name": "Nobody", "foot": [0.5, 0.9]}), cast=["KELLY"])
        with self.assertRaises(layout.LayoutError):
            layout.validate_shot_layout(self.shot({"name": "KELLY", "foot": [1.5, 0.9]}))
        with self.assertRaises(layout.LayoutError):
            layout.validate_shot_layout(self.shot({"name": "KELLY", "foot": [0.5, 0.9], "facing": "up"}))
        layout.validate_shot_layout(self.shot(), cast=["KELLY"])                       # an empty shot is fine

    def test_the_storyboard_puts_every_frame_on_one_sheet_even_a_missing_one(self):
        out = os.path.join(self.dir, "sb.png")
        layout.storyboard([(self.bg, "S01"), (self.bg, "S02"), (os.path.join(self.dir, "none.png"), "S03"), (self.bg, "S04")], out,
                          cols=3, cell=(160, 90))
        sheet = Image.open(out)
        self.assertEqual(sheet.size, (3 * (160 + 12) + 12, 2 * (90 + 26 + 12) + 12))


if __name__ == "__main__":
    unittest.main()
