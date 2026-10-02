import io
import os
import shutil
import sys
import tempfile
import unittest

from core import assets
from core.db import connect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import library_tidy  # noqa: E402


def png(w, h, color):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


def add(conn, aid, name, data, **kw):
    """add_image returns the path; this returns the new picture's id with its role cleared (as in the library before the tidy)."""
    path = assets.add_image(conn, aid, name, data, **kw)
    conn.execute("UPDATE asset_images SET role=? WHERE path=?", (kw.get("role"), path))
    conn.commit()
    return conn.execute("SELECT id FROM asset_images WHERE path=?", (path,)).fetchone()[0]


class LibraryTidyTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_roles_are_set_and_copies_and_icons_are_held_back_but_never_deleted(self):
        aid = assets.create(self.conn, "FF", "character", "ALOK")
        big = add(self.conn, aid, "a.png", png(550, 800, (200, 30, 30)))
        twin = add(self.conn, aid, "b.png", png(220, 320, (200, 30, 30)))     # same art, smaller
        half = add(self.conn, aid, "c.png", png(220, 394, (30, 200, 30)))
        icon = add(self.conn, aid, "d.png", png(100, 100, (30, 30, 200)))
        plan = library_tidy.plan_characters(self.conn)
        by = {k: v for k, v in plan.items()}
        ids = [i["id"] for i in assets.get(self.conn, aid)["images"]]
        self.assertEqual(len(ids), 4)
        library_tidy.apply_characters(self.conn, plan)
        rows = {r["id"]: (r["role"], r["status"]) for r in self.conn.execute("SELECT id, role, status FROM asset_images")}
        self.assertEqual(sorted(s for _, s in rows.values()).count("redundant"), 2)         # the smaller copy + the icon
        self.assertEqual(sorted(r for r, s in rows.values() if s == "approved"), ["full_body", "half_body"])
        for i in ids:
            self.assertTrue(os.path.exists(assets.resolve(self.conn.execute("SELECT path FROM asset_images WHERE id=?", (i,)).fetchone()[0])))
        self.assertEqual(len(by), 4)

    def test_a_character_whose_pictures_are_already_labelled_is_left_alone(self):
        aid = assets.create(self.conn, "FF", "character", "KELLY")
        add(self.conn, aid, "a.png", png(550, 800, (1, 2, 3)), role="back")
        add(self.conn, aid, "b.png", png(550, 800, (1, 2, 3)))
        self.assertEqual(library_tidy.plan_characters(self.conn), {})

    def test_redundant_pictures_are_not_used_and_not_in_the_review_box(self):
        aid = assets.create(self.conn, "FF", "character", "ALOK")
        iid = add(self.conn, aid, "a.png", png(550, 800, (9, 9, 9)))
        assets.set_image_meta(self.conn, iid, status="redundant")
        a = assets.get(self.conn, aid)
        self.assertEqual(a["images"], [])
        self.assertEqual(a["pending"], [])
        self.assertEqual(assets.pending_images(self.conn, "FF"), [])

    def test_a_number_named_place_is_dropped_and_an_island_copy_of_an_area_picture_is_held(self):
        junk = assets.create(self.conn, "FF", "location", "121212")
        add(self.conn, junk, "m.png", png(300, 300, (5, 5, 5)))
        island = assets.create(self.conn, "FF", "location", "Đảo Mặt Trời")
        area = assets.create(self.conn, "FF", "location", "Khu vực - Dock")
        data = png(400, 300, (50, 60, 70))
        i1 = add(self.conn, island, "x.png", data, sha256="same")
        add(self.conn, area, "x.png", data, sha256="same")
        plan = library_tidy.plan_locations(self.conn)
        self.assertEqual([j["name"] for j in plan["junk"]], ["121212"])
        self.assertEqual(plan["held"], [i1])
