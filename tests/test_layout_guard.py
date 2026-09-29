"""S5.2 (kế hoạch sau #8, lỗi 1.4): a picture at a place the library describes is held when the project does not resolve the place —
its prompt would go without the layout sentence (#8's tower came out as stacked terraces)."""
import os
import tempfile
import unittest

from PIL import Image

from core import assets
from core.db import connect
from core.pipeline import Pipeline

LAYOUT = ("Real map: the clock tower stands directly on a wide, flat, open stone plaza; at most two low plaza levels joined by short "
          "steps, low chest-high retaining walls; 1-2 storey red-roof houses, grass, palms, sea around. " * 2 + "No stacked terraces.")


class LayoutGuardTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("g", game="FF")
        cur = self.p.conn.execute("INSERT INTO assets (game, kind, name, description) VALUES ('FF', 'location', 'Tháp Đồng Hồ', ?)", (LAYOUT,))
        self.aid = cur.lastrowid
        self.p.conn.commit()
        self.scene = {"location": "Tháp Đồng Hồ — quảng trường, chiều"}

    def test_held_when_the_place_is_not_attached(self):
        msg = assets.missing_layout(self.p.conn, self.pid, self.scene)
        self.assertIn("Tháp Đồng Hồ", msg)
        self.assertIsNone(assets.missing_layout(self.p.conn, self.pid, {"location": "một con hẻm"}))     # nothing the library knows

    def test_sent_when_the_place_resolves_and_the_layout_is_not_cut(self):
        pic = os.path.join(tempfile.mkdtemp(), "t.png")
        Image.new("RGB", (8, 8)).save(pic)
        self.p.conn.execute("INSERT INTO asset_images (asset_id, path) VALUES (?, ?)", (self.aid, pic))
        self.p.conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?, ?)", (self.pid, self.aid))
        self.p.conn.commit()
        self.assertIsNone(assets.missing_layout(self.p.conn, self.pid, self.scene))
        text = assets.location_text(self.p.conn, assets.scene_location(self.p.conn, self.pid, self.scene))
        self.assertIn("No stacked terraces", text)                     # the 300-character cut dropped the layout's end


class TierLineTests(unittest.TestCase):
    """S5.4: layer 0 counts long horizontal edges behind the people (calibrated 29/09: real-tower renders 0–3, #8 stacked frames 5–10)."""

    def _frame(self, stripes):
        from PIL import ImageDraw
        im = Image.new("RGB", (360, 640), (150, 170, 200))
        d = ImageDraw.Draw(im)
        for k in range(stripes):
            y = 260 + k * 40
            d.rectangle([0, y, 360, y + 20], fill=(90, 90, 90))
        path = os.path.join(tempfile.mkdtemp(), f"f{stripes}.png")
        im.save(path)
        return path

    def test_stacked_terraces_are_flagged_only_at_a_flat_place(self):
        from core import qc_scene
        flat, stacked = self._frame(1), self._frame(8)
        self.assertLess(qc_scene.tier_lines(flat), qc_scene.TIER_FLAG)
        self.assertGreaterEqual(qc_scene.tier_lines(stacked), qc_scene.TIER_FLAG)
        codes = lambda path, flat_place, size="MS": [f["code"] for f in qc_scene.check_frame(path, {"size": size}, flat_place)]  # noqa: E731
        self.assertIn("stacked_tiers", codes(stacked, True))
        self.assertNotIn("stacked_tiers", codes(stacked, False))           # a place not described as flat: stairs may be real
        self.assertNotIn("stacked_tiers", codes(stacked, True, "CU"))      # a close-up shows no place to count
        self.assertNotIn("stacked_tiers", codes(flat, True))


class PlaceStaleTests(LayoutGuardTests):
    """S5.3: the place's text / pictures changed → its frames are outdated; a picture made before S5.3 raises no false alarm."""

    def test_a_changed_place_makes_its_frame_outdated(self):
        import json
        from core import lineage
        pic = os.path.join(tempfile.mkdtemp(), "t.png")
        Image.new("RGB", (8, 8)).save(pic)
        self.p.conn.execute("INSERT INTO asset_images (asset_id, path) VALUES (?, ?)", (self.aid, pic))
        self.p.conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?, ?)", (self.pid, self.aid))
        sid = self.p.create_scene(self.pid, 1, "S1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(dict(self.scene, image_prompt="x")), sid))
        jid = self.p.create_job(sid, "image_gen")
        self.p.conn.execute("UPDATE jobs SET state='approved', input_hash=? WHERE id=?",
                            (lineage.current_image_hash(self.p.conn, self.pid, sid), jid))
        self.p.conn.commit()
        self.assertIsNone(lineage._scan(self.p.conn, self.pid)[sid]["image_stale"])
        self.p.conn.execute("UPDATE assets SET description='quảng trường nhiều tầng' WHERE id=?", (self.aid,))
        self.p.conn.commit()
        self.assertIn("bối cảnh", lineage._scan(self.p.conn, self.pid)[sid]["image_stale"])
        legacy = lineage._image_hash(json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"]),
                                     [], self.p.project(self.pid)["aspect"], self.p.project(self.pid))
        self.p.conn.execute("UPDATE jobs SET input_hash=? WHERE id=?", (legacy, jid))
        self.p.conn.commit()
        self.assertIsNone(lineage._scan(self.p.conn, self.pid)[sid]["image_stale"])     # made before S5.3: no false alarm


if __name__ == "__main__":
    unittest.main()
