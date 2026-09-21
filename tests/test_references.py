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
        self.assertIn("Image 1 shows the character KELLY", note)
        self.assertIn("Image 2 shows the location Đảo Quân Sự", note)

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
        self.assertTrue(prompt.startswith("Reference images are attached."))
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


if __name__ == "__main__":
    unittest.main()
