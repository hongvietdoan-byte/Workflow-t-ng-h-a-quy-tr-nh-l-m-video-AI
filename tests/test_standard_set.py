"""Standard 3 pictures per character (user choice 2026-09-24): 1 front on grey, 2 multi-angle design sheet, 3 related (skill).
A model that takes design sheets (GPT Image 2.5 Sunburst, tested) gets all three with a note per picture; any other model (Seedream,
video) never gets the sheet or the related picture — only the front picture, first."""
import os
import shutil
import tempfile
import unittest

from PIL import Image

from core import assets, image_models
from core.db import connect
from core.pipeline import Pipeline


class StandardSetTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.conn = connect(":memory:")
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("P")
        self.maxim = assets.create(self.conn, "FF", "character", "MAXIM")
        self.paths = {}
        for n, (w, h, role) in enumerate([(400, 1000, "full_body"), (1536, 1024, "design_sheet"), (128, 128, "related"),
                                          (500, 800, "front_standard"), (600, 700, "half_body")]):
            self.paths[role] = self.add(self.maxim, f"m{n}.png", w, h, n, role)
        assets.attach(self.conn, self.pid, self.maxim)
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'MAXIM', 'd')", (self.pid,))
        self.conn.commit()

    def add(self, aid, name, w, h, seed, role):
        path = os.path.join(self.dir, name)
        Image.new("RGB", (w, h), (seed * 40 % 255, 80, 120)).save(path)
        with open(path, "rb") as f:
            return assets.add_image(self.conn, aid, name, f.read(), role=role)

    def refs(self, sheets):
        return assets.scene_references(self.conn, self.pid, {"characters": ["MAXIM"], "size": "MS"}, sheets=sheets)

    def test_a_sheet_model_gets_front_sheet_related_in_that_order(self):
        got = [(r["role"], r["path"]) for r in self.refs(True)]
        self.assertEqual(got, [("character", self.paths["front_standard"]), ("sheet", self.paths["design_sheet"]),
                               ("related", self.paths["related"])])
        note = assets.reference_note(self.refs(True))
        self.assertIn("its colors are the true colors", note)
        self.assertIn("do NOT copy its layout", note)
        self.assertIn("never draw it as an icon", note)

    def test_other_models_never_get_the_sheet_or_the_related_picture(self):
        got = self.refs(False)
        self.assertEqual(got[0]["path"], self.paths["front_standard"])              # the grey front picture leads
        self.assertNotIn(self.paths["design_sheet"], [r["path"] for r in got])
        self.assertNotIn(self.paths["related"], [r["path"] for r in got])
        self.assertEqual({r["role"] for r in got}, {"character"})

    def test_without_a_front_standard_picture_the_automatic_pick_stays(self):
        self.conn.execute("UPDATE asset_images SET status='pending' WHERE role='front_standard'")
        self.conn.commit()
        self.assertEqual(assets.standard_set(assets.get(self.conn, self.maxim), True), [])
        got = self.refs(True)
        self.assertNotIn("sheet", [r["role"] for r in got])

    def test_a_hand_picked_picture_wins_over_the_standard_set(self):
        img = next(i for i in assets.get(self.conn, self.maxim)["images"] if i["role"] == "half_body")
        self.conn.execute("UPDATE characters SET ref_image_id=? WHERE name='MAXIM'", (img["id"],))
        self.conn.commit()
        self.assertEqual([r["path"] for r in self.refs(True)], [img["path"]])

    def test_only_the_tested_model_takes_sheets(self):
        self.assertTrue(image_models.accepts_sheets("gpt-image-2.5-sunburst"))
        for m in ("gpt-image-2.5-flare", "gpt-image-2", image_models.DEFAULT, None):
            self.assertFalse(image_models.accepts_sheets(m), m)


if __name__ == "__main__":
    unittest.main()
