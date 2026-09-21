import json
import os
import shutil
import struct
import tempfile
import unittest
import zlib

from core import assets
from core.adapters.deepix import DeepixImageProvider
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner
from tests.test_adapters import FakeTransport, TOKEN, ok


def png(seed):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" + bytes([seed, 0, 0]))) + chunk(b"IEND", b""))


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("refs")
        for name, seed in (("KELLY", 1), ("KENTA", 2), ("Kelly thức tỉnh", 3)):
            a = assets.create(self.conn, "FF", "character", name, "", "", None, "x")
            assets.add_image(self.conn, a, f"{name}.png", png(seed))
            assets.attach(self.conn, self.pid, a)
        loc = assets.create(self.conn, "FF", "location", "Đảo Quân Sự", "", "", None, "x")
        assets.add_image(self.conn, loc, "loc.png", png(9))
        assets.attach(self.conn, self.pid, loc)
        for n in ("Kelly", "Kenta", "Maxim"):
            self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (self.pid, n, f"{n}, tall"))
        self.conn.commit()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_bible_name_finds_its_chosen_asset_and_falls_back_to_the_text_description(self):
        linked = assets.link_characters(self.conn, self.pid, ["Kelly", "Kenta", "Maxim"])
        self.assertEqual(linked["Kelly"]["name"], "KELLY")                      # the exact match wins over "Kelly thức tỉnh"
        self.assertEqual(linked["Kenta"]["name"], "KENTA")
        self.assertIsNone(linked["Maxim"])                                     # nothing chosen for Maxim: drawn from the description

    def test_a_scene_gets_the_pictures_of_its_characters_and_its_place(self):
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["Kelly", "Maxim"], "location": "Bãi cát trên Đảo Quân Sự"})
        self.assertEqual([(r["label"], r["role"]) for r in refs], [("KELLY", "character"), ("Đảo Quân Sự", "location")])
        self.assertEqual(assets.scene_references(self.conn, self.pid, {"characters": ["Maxim"], "location": "Hang động"}), [])
        note = assets.reference_note(refs)
        self.assertIn("Image 1 is KELLY", note)
        self.assertIn("Image 2 is the location Đảo Quân Sự", note)

    def job(self, characters, location=""):
        sid = self.p.create_scene(self.pid, 1, "s")
        self.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                          (json.dumps({"image_prompt": "hero on a rooftop", "characters": characters, "location": location}), sid))
        self.conn.commit()
        return self.p.create_job(sid, "image_gen")

    def test_the_image_job_carries_the_pictures_to_the_provider(self):
        provider = MockImageProvider()
        runner = ImageRunner(self.p, provider, os.path.join(self.dir, "projects"))
        self.job(["Kelly", "Kenta"])
        self.assertEqual(runner.submit_pending(self.pid), 1)
        prompt = provider.prompts["img-1"]
        self.assertTrue(prompt.startswith("Reference images are attached"))
        self.assertTrue(prompt.endswith("Scene: hero on a rooftop"))
        self.assertEqual(len(provider.references["img-1"]), 2)
        self.assertTrue(all(os.path.exists(x) for x in provider.references["img-1"]))

    def test_a_scene_without_any_matching_resource_is_sent_as_before(self):
        provider = MockImageProvider()
        runner = ImageRunner(self.p, provider, os.path.join(self.dir, "projects"))
        self.job(["Maxim"])
        runner.submit_pending(self.pid)
        self.assertEqual(provider.prompts["img-1"], "hero on a rooftop")
        self.assertEqual(provider.references["img-1"], [])

    def test_deepix_switches_to_image_to_image_and_uploads_the_pictures(self):
        t = FakeTransport()
        t.on("POST", "/api/image-generator/conversation-create", ok({"id": 1, "msg_id": 55}))
        deepix = DeepixImageProvider(TOKEN, "https://deepix.example", t)
        a = assets.list_assets(self.conn, "FF", "character", None, shared_only=True)[0]
        self.assertEqual(deepix.submit("a scene", [a["images"][0]["path"], os.path.join(self.dir, "missing.png")]), "55")
        body = t.calls[0]["body"]
        self.assertIn(b'name="prompt_key"\r\n\r\n1', body)
        self.assertIn(b'name="message_type"\r\n\r\nimage-to-image', body)
        self.assertEqual(body.count(b'name="file[]"'), 1)                      # the missing file is skipped, not fatal
        t2 = FakeTransport()
        t2.on("POST", "/api/image-generator/conversation-create", ok({"id": 1, "msg_id": 56}))
        DeepixImageProvider(TOKEN, "https://deepix.example", t2).submit("no refs")
        self.assertIn(b'name="prompt_key"\r\n\r\n2', t2.calls[0]["body"])          # without pictures it stays text-to-image


class BestPictureTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def picture(self, w, h, name):
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new("RGBA", (w, h), (200, 0, 0, 0 if name == "cutout" else 255)).save(buf, "PNG")
        return buf.getvalue()

    def test_a_single_figure_beats_a_wide_character_sheet(self):
        a = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        for name, w, h in (("sheet", 1536, 1024), ("small", 220, 394), ("art", 550, 800)):
            assets.add_image(self.conn, a, f"{name}.png", self.picture(w, h, name))
        asset = assets.get(self.conn, a)
        self.assertEqual(os.path.basename(assets.best_reference(asset)["path"]), "3.png")            # the 550x800 portrait
        pid = Pipeline(self.conn).create_project("x")
        assets.attach(self.conn, pid, a)
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (pid, "Kelly", "d"))
        self.conn.commit()
        self.assertEqual(os.path.basename(assets.link_characters(self.conn, pid, ["Kelly"])["Kelly"]["ref"]["path"]), "3.png")

    def test_a_cut_out_picture_is_sent_on_a_plain_background(self):
        from core.adapters.deepix import flatten_transparency
        import io
        from PIL import Image
        out, name = flatten_transparency(self.picture(20, 30, "cutout"), "kelly.png")
        self.assertEqual(name, "kelly.png")
        img = Image.open(io.BytesIO(out))
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.getpixel((5, 5)), (232, 232, 232))                                     # not black
        opaque = self.picture(20, 30, "solid")
        self.assertEqual(flatten_transparency(opaque, "a.png")[0], opaque)                          # an opaque picture is left alone

    def test_the_prompt_ties_each_picture_to_one_person_and_forbids_mixing(self):
        note = assets.reference_note([{"label": "KELLY", "role": "character"}, {"label": "KENTA", "role": "character"}])
        self.assertIn("Image 1 is KELLY", note)
        self.assertIn("Image 2 is KENTA", note)
        self.assertIn("never swap or blend", note)


class MultiPictureTests(unittest.TestCase):
    """Automatic references: more than a single straight-on shot, and a good widescreen shot for a location."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("multi")

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def picture(self, w, h, seed=0):
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new("RGB", (w, h), (seed, seed, seed)).save(buf, "PNG")
        return buf.getvalue()

    def test_the_automatic_pick_is_two_single_figure_pictures_not_the_sheet_and_not_a_duplicate(self):
        a = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.conn, a, "sheet.png", self.picture(1536, 1024, 1))    # the composite turn-around board
        assets.add_image(self.conn, a, "full.png", self.picture(550, 800, 2))       # full-body
        assets.add_image(self.conn, a, "face.png", self.picture(400, 600, 3))       # a closer, smaller portrait
        asset = assets.get(self.conn, a)
        picked = assets.best_references(asset, 2)
        names = {os.path.basename(img["path"]) for img in picked}
        self.assertEqual(len(picked), 2)
        self.assertNotIn("1.png", names)                                            # the sheet (sorted first by id) is not among them
        self.assertEqual(names, {"2.png", "3.png"})

    def test_a_scene_sends_both_automatic_pictures_of_a_character_grouped_in_the_note(self):
        a = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.conn, a, "full.png", self.picture(550, 800, 2))
        assets.add_image(self.conn, a, "face.png", self.picture(400, 600, 3))
        assets.attach(self.conn, self.pid, a)
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (self.pid, "Kelly", "d"))
        self.conn.commit()
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["Kelly"]})
        self.assertEqual(len(refs), 2)
        self.assertEqual({r["label"] for r in refs}, {"KELLY"})
        note = assets.reference_note(refs)
        self.assertIn("Images 1/2 show KELLY", note)
        self.assertIn("different angles/details", note)

    def test_a_location_picks_the_widest_shot_not_a_tall_crop(self):
        loc = assets.create(self.conn, "FF", "location", "Đảo Quân Sự", "", "", None, "x")
        assets.add_image(self.conn, loc, "crop.png", self.picture(300, 900, 1))      # a tall detail crop
        assets.add_image(self.conn, loc, "wide.png", self.picture(1920, 1080, 2))    # the establishing shot
        asset = assets.get(self.conn, loc)
        self.assertEqual(os.path.basename(assets.best_reference(asset)["path"]), "2.png")

    def test_choosing_two_specific_pictures_by_hand_is_kept_and_wins_over_automatic(self):
        a = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        for i in range(3):
            assets.add_image(self.conn, a, f"p{i}.png", self.picture(550, 800, i))
        assets.attach(self.conn, self.pid, a)
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (self.pid, "Kelly", "d"))
        self.conn.commit()
        img_ids = [img["id"] for img in assets.get(self.conn, a)["images"]]
        assets.set_character_link(self.conn, self.pid, "Kelly", a, img_ids[0], [img_ids[0], img_ids[2]])
        linked = assets.link_characters(self.conn, self.pid, ["Kelly"])
        self.assertEqual([img["id"] for img in linked["Kelly"]["refs"]], [img_ids[0], img_ids[2]])


class ChoiceTests(ReferenceTests):
    """The person can change which asset / which picture is a character's reference; the choice wins over the automatic match."""

    def asset_id(self, name):
        return next(a["id"] for a in assets.list_assets(self.conn, "FF", None, None, shared_only=True) if a["name"] == name)

    def test_the_default_is_the_first_picture_and_a_chosen_picture_is_used_instead(self):
        kelly = self.asset_id("KELLY")
        assets.add_image(self.conn, kelly, "second.png", png(77))
        first, second = [i["id"] for i in assets.get(self.conn, kelly)["images"]]
        self.assertEqual(assets.link_characters(self.conn, self.pid, ["Kelly"])["Kelly"]["ref"]["id"], first)
        assets.set_character_link(self.conn, self.pid, "Kelly", kelly, second)
        self.assertEqual(assets.link_characters(self.conn, self.pid, ["Kelly"])["Kelly"]["ref"]["id"], second)
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["Kelly"]})
        self.assertTrue(refs[0]["path"].endswith("2.png"))                    # what image generation will really send

    def test_another_asset_or_no_picture_can_be_chosen(self):
        assets.set_character_link(self.conn, self.pid, "Maxim", self.asset_id("KENTA"))
        self.assertEqual(assets.link_characters(self.conn, self.pid, ["Maxim"])["Maxim"]["name"], "KENTA")   # Maxim had nothing by name
        assets.set_character_link(self.conn, self.pid, "Kelly", 0)
        self.assertIsNone(assets.link_characters(self.conn, self.pid, ["Kelly"])["Kelly"])                  # explicitly none: text only
        self.assertEqual(assets.scene_references(self.conn, self.pid, {"characters": ["Kelly"]}), [])
        assets.set_character_link(self.conn, self.pid, "Kelly", None)
        self.assertEqual(assets.link_characters(self.conn, self.pid, ["Kelly"])["Kelly"]["name"], "KELLY")  # back to automatic

    def test_the_character_bible_shows_the_pictures_and_saves_a_change(self):
        from streamlit.testing.v1 import AppTest
        from tests.test_step1_flow import APP
        db = os.path.join(self.dir, "m.sqlite")
        os.environ.update({"PIPELINE_DB": db, "PIPELINE_DATA": os.path.join(self.dir, "projects")})
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("PIPELINE_DB", "PIPELINE_DATA")])
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Ảnh tham chiếu của từng nhân vật — 2/3 đã có" in e.label for e in at.expander))
        at.selectbox(key=f"cref_{self.pid}_Kelly").set_value("none").run()
        self.assertFalse(at.exception)
        row = self.conn.execute("SELECT ref_asset_id FROM characters WHERE project_id=? AND name='Kelly'", (self.pid,)).fetchone()
        self.assertEqual(row["ref_asset_id"], 0)
        self.assertTrue(any("1/3 đã có" in e.label for e in at.expander))


if __name__ == "__main__":
    unittest.main()
