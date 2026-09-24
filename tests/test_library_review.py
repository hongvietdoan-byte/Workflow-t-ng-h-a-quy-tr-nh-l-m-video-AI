"""GĐ-E0a (G1/G2/G6, docs/KE_HOACH_TONG_2026-09-24.md): library pictures carry a role and a look; pictures that came in without a
person looking wait in a review box and are never used by the pipeline until approved; the health table says what is missing."""
import os
import shutil
import tempfile
import unittest

from PIL import Image

from core import assets
from core.db import connect
from core.pipeline import Pipeline


def picture(path, w, h):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (w, h), (w % 255, h % 255, 90)).save(path)
    return path


class ReviewBoxTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.conn = connect(":memory:")

    def test_synced_pictures_wait_for_a_person_and_are_not_used_until_approved(self):
        src = os.path.join(self.dir, "src")
        picture(os.path.join(src, "KELLY.png"), 400, 900)                   # tall: full body
        assets.sync_folder(self.conn, src, "FF", "character")
        kelly = assets.list_assets(self.conn, "FF")[0]
        self.assertEqual((len(kelly["images"]), len(kelly["pending"])), (0, 1))
        p = Pipeline(self.conn)
        pid = p.create_project("P")
        self.conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, kelly["id"]))
        self.conn.commit()
        self.assertEqual(assets.scene_references(self.conn, pid, {"characters": ["KELLY"]}), [])   # nothing pending is sent
        waiting = assets.pending_images(self.conn, "FF")
        self.assertEqual(waiting[0]["role"], "full_body")                    # free guess from the proportions
        assets.set_image_meta(self.conn, waiting[0]["id"], role="half_body", look="ingame", status="approved")
        refs = assets.scene_references(self.conn, pid, {"characters": ["KELLY"]})
        self.assertEqual([r["label"] for r in refs], ["KELLY"])
        img = assets.get(self.conn, kelly["id"])["images"][0]
        self.assertEqual((img["role"], img["look"]), ("half_body", "ingame"))

    def test_a_picture_the_person_uploads_is_approved_and_a_design_board_is_recognised(self):
        aid = assets.create(self.conn, "FF", "character", "MAXIM")
        with open(picture(os.path.join(self.dir, "sheet.png"), 2400, 1000), "rb") as f:
            assets.add_image(self.conn, aid, "sheet.png", f.read())
        img = assets.get(self.conn, aid)["images"][0]
        self.assertEqual((img["status"], img["role"]), ("approved", "design_sheet"))

    def test_health_lists_what_each_entry_lacks(self):
        kelly = assets.create(self.conn, "FF", "character", "KELLY")
        with open(picture(os.path.join(self.dir, "k.png"), 400, 900), "rb") as f:
            assets.add_image(self.conn, kelly, "k.png", f.read())
        place = assets.create(self.conn, "FF", "location", "Tháp đồng hồ")
        with open(picture(os.path.join(self.dir, "t.png"), 1600, 900), "rb") as f:
            assets.add_image(self.conn, place, "t.png", f.read(), role="top_down")
        rows = {r["name"]: r for r in assets.health(self.conn, "FF")}
        self.assertIn("cận mặt", rows["KELLY"]["missing"])
        self.assertIn("ảnh chuẩn anime", rows["KELLY"]["missing"])
        self.assertEqual(rows["Tháp đồng hồ"]["missing"], ["nền ngang tầm mắt"])   # a top-down map is not a background


if __name__ == "__main__":
    unittest.main()
