"""GĐ-E1 (docs/KE_HOACH_TONG_2026-09-24.md): the project look (ANIME / FF_INGAME) reaches the image prompt, the reference choice,
the Director, QC and the lineage; the image prompt states the framing in words (F9); automatic chaining needs the same framing (F8);
framing/scale/set now have QC floors (F11)."""
import json
import os
import shutil
import tempfile
import unittest

from PIL import Image

from core import assets, lineage, looks, prompts
from core.db import connect
from core.pipeline import Pipeline, hard_floors
from core.runner import framing_sentence, same_framing


class LookTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.conn = connect(":memory:")
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("P")
        self.sid = self.p.create_scene(self.pid, 1, "x")
        self.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                          (json.dumps({"image_prompt": "Kelly runs", "characters": ["KELLY"], "size": "MS"}), self.sid))
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'd')", (self.pid,))
        self.kelly = assets.create(self.conn, "FF", "character", "KELLY")
        for n, look in enumerate(("ingame", "anime")):
            path = os.path.join(self.dir, f"{look}.png")
            Image.new("RGB", (600, 700), (n * 90, 40, 40)).save(path)
            with open(path, "rb") as f:
                assets.add_image(self.conn, self.kelly, f"{look}.png", f.read(), role="half_body", look=look)
        assets.attach(self.conn, self.pid, self.kelly)
        self.conn.commit()

    def ref_look(self):
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["KELLY"], "size": "MS"})
        by_path = {i["path"]: i["look"] for i in assets.get(self.conn, self.kelly)["images"]}
        return by_path[refs[0]["path"]]

    def test_the_look_picks_its_own_standard_pictures_first(self):
        self.p.set_project_field(self.pid, "look", "ANIME")
        self.assertEqual(self.ref_look(), "anime")
        self.p.set_project_field(self.pid, "look", "FF_INGAME")
        self.assertEqual(self.ref_look(), "ingame")

    def test_the_look_reaches_the_image_prompt_the_director_and_qc(self):
        self.p.set_project_field(self.pid, "look", "FF_INGAME")
        proj = self.p.project(self.pid)
        self.assertIn("in-game 3D character art", looks.image_sentence(proj))
        self.assertIn("GIỐNG Y HỆT", prompts.build_director_bundle(self.p, self.pid))
        self.assertIn("in-game Free Fire", prompts.build_qc_bundle(self.p, self.sid))

    def wb(self, palette):
        self.conn.execute("UPDATE projects SET world_bible=? WHERE id=?", (json.dumps({"palette": palette}), self.pid))
        self.conn.commit()

    def test_changing_the_look_makes_pictures_outdated_but_projects_without_a_look_keep_their_hash(self):
        before = lineage.current_image_hash(self.conn, self.pid, self.sid)
        self.wb("warm")
        self.assertEqual(lineage.current_image_hash(self.conn, self.pid, self.sid), before)     # no look: unchanged (no mass "stale")
        self.p.set_project_field(self.pid, "look", "ANIME")
        anime = lineage.current_image_hash(self.conn, self.pid, self.sid)
        self.p.set_project_field(self.pid, "look", "FF_INGAME")
        self.assertNotEqual(lineage.current_image_hash(self.conn, self.pid, self.sid), anime)
        ingame = lineage.current_image_hash(self.conn, self.pid, self.sid)
        self.wb("cold")
        self.assertNotEqual(lineage.current_image_hash(self.conn, self.pid, self.sid), ingame)   # I8: World Bible counts too


class FramingTests(unittest.TestCase):
    def test_the_shot_size_is_said_in_words(self):
        self.assertIn("head and shoulders", framing_sentence({"size": "CU", "angle": "low"}))
        self.assertIn("low angle looking up", framing_sentence({"size": "CU", "angle": "low"}))
        self.assertIn("mid-chest", framing_sentence({"shot": "medium close-up, eye level"}))
        self.assertEqual(framing_sentence({}), "")

    def test_chaining_needs_the_same_framing(self):
        self.assertTrue(same_framing({"size": "MS", "angle": "eye"}, {"size": "MS"}))
        self.assertFalse(same_framing({"size": "WS"}, {"size": "CU"}))
        self.assertFalse(same_framing({"size": "MS", "angle": "high"}, {"size": "MS", "angle": "eye"}))

    def test_framing_scale_and_set_have_floors(self):
        floors = hard_floors("image")
        for key in ("composition", "scale", "set_match"):
            self.assertIn(key, floors)


if __name__ == "__main__":
    unittest.main()
