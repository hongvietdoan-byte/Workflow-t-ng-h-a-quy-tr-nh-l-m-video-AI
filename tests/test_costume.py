"""Changing a character's outfit with pictures + text: outfit pictures travel with the face picture, and a generated 2-picture
character set becomes the character's reference for the project."""
import io
import os
import shutil
import tempfile
import unittest

from PIL import Image

from core import assets, costume
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider


def picture(w, h, shade):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (shade, shade, shade)).save(buf, "PNG")
    return buf.getvalue()


class CostumeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.data = os.path.join(self.dir, "projects")
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("costume")
        self.kelly = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        for shade in (10, 20):
            assets.add_image(self.conn, self.kelly, f"k{shade}.png", picture(550, 800, shade))
        self.skin = assets.create(self.conn, "FF", "prop", "Áo giáp mùa hè", "", "", None, "x")
        assets.add_image(self.conn, self.skin, "skin.png", picture(600, 900, 200))
        for a in (self.kelly, self.skin):
            assets.attach(self.conn, self.pid, a)
        for n in ("Kelly", "Maxim"):
            self.conn.execute("INSERT INTO characters (project_id, name, description, wardrobe) VALUES (?,?,?,?)",
                              (self.pid, n, f"{n}, athletic", "summer armour"))
        self.conn.commit()
        self.skin_img = assets.get(self.conn, self.skin)["images"][0]["id"]

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_without_an_outfit_the_references_are_unchanged(self):
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["Kelly"]})
        self.assertEqual([r["role"] for r in refs], ["character", "character"])
        self.assertIn("outfit and its colors", assets.reference_note(refs))

    def test_an_outfit_takes_the_second_slot_and_the_note_splits_face_and_clothes(self):
        assets.set_outfit(self.conn, self.pid, "Kelly", [self.skin_img])
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["Kelly"]})
        self.assertEqual([(r["label"], r["role"]) for r in refs], [("KELLY", "character"), ("KELLY", "outfit")])   # 2 per person: face + outfit
        note = assets.reference_note(refs)
        self.assertIn("the OUTFIT KELLY wears in this video", note)
        self.assertIn("the clothes come from the OUTFIT image", note)
        assets.set_outfit(self.conn, self.pid, "Kelly", None)
        self.assertEqual(assets.outfit_images(self.conn, self.pid, "Kelly"), [])

    def test_a_person_without_pictures_can_still_wear_an_outfit_picture(self):
        assets.set_outfit(self.conn, self.pid, "Maxim", [self.skin_img])
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["Maxim"]})
        self.assertEqual([(r["label"], r["role"]) for r in refs], [("Maxim", "outfit")])

    def test_a_character_set_is_generated_linked_and_replaces_the_separate_outfit(self):
        assets.set_outfit(self.conn, self.pid, "Kelly", [self.skin_img])
        provider = MockImageProvider(polls_to_finish=2)
        provider.size = "2048x1152"
        waits = []
        result = costume.make_character_set(self.p, self.pid, "Kelly", provider, self.data, sleep=waits.append)
        self.assertEqual(provider.size, "2048x1152")                                   # the landscape size is put back
        self.assertEqual(len(provider.prompts), 2)
        self.assertTrue(all("full body" in pr and "the OUTFIT KELLY" in pr for pr in provider.prompts.values()))
        self.assertTrue(all(len(r) == 2 for r in provider.references.values()))       # face + outfit
        linked = assets.link_characters(self.conn, self.pid, ["Kelly"])["Kelly"]
        self.assertEqual(linked["id"], result["asset_id"])
        self.assertEqual(linked["name"], "KELLY · trang phục 1")
        self.assertEqual(len(linked["images"]), 2)
        self.assertEqual(assets.outfit_images(self.conn, self.pid, "Kelly"), [])       # the set already wears it
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM usage_events WHERE project_id=?", (self.pid,)).fetchone()[0], 2)
        self.assertEqual(len(waits), 1)

    def test_a_failed_picture_stops_with_an_error_and_links_nothing(self):
        from core.providers import ProviderError, TaskStatus

        class Failing(MockImageProvider):
            def status(self, task_id):
                return TaskStatus("failed", "risk_control", "blocked")
        with self.assertRaises(ProviderError):
            costume.make_character_set(self.p, self.pid, "Kelly", Failing(), self.data, sleep=lambda s: None)
        self.assertEqual(assets.link_characters(self.conn, self.pid, ["Kelly"])["Kelly"]["name"], "KELLY")


if __name__ == "__main__":
    unittest.main()
