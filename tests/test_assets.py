import os
import shutil
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import assets, auth, prompts
from core.assets import AssetError
from core.db import connect
from core.pipeline import Pipeline
from tests.test_new_skills import PNG
from tests.test_step1_flow import split_only

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_accents_and_case_are_ignored_when_matching_names(self):
        self.assertEqual(assets.fold("  Ông lão  ORIN!"), "ong lao orin")
        self.assertEqual(assets.fold("Đêm"), "dem")

    def test_create_validates_and_refuses_duplicates(self):
        aid = assets.create(self.conn, "FF", "character", "Lyra", "tóc bạc", "Lyra Silver, Lý Ra")
        self.assertEqual(assets.get(self.conn, aid)["kind_label"], "Nhân vật")
        with self.assertRaises(AssetError):
            assets.create(self.conn, "FF", "character", "lyra")                    # same name, same game and kind
        assets.create(self.conn, "AOV", "character", "Lyra")                        # another game: fine
        assets.create(self.conn, "FF", "pet", "Lyra")                               # another kind: fine
        for bad in (lambda: assets.create(self.conn, "FF", "character", "  "), lambda: assets.create(self.conn, "FF", "nope", "X")):
            with self.assertRaises(AssetError):
                bad()

    def test_images_are_checked_stored_and_removed(self):
        aid = assets.create(self.conn, "FF", "character", "Lyra")
        path = assets.add_image(self.conn, aid, "front.PNG", PNG)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(len(assets.get(self.conn, aid)["images"]), 1)
        for name, data in (("x.gif", PNG), ("big.png", b"0" * (assets.MAX_IMAGE_BYTES + 1)), ("empty.png", b"")):
            with self.assertRaises(AssetError):
                assets.add_image(self.conn, aid, name, data)
        for i in range(assets.MAX_IMAGES_PER_ASSET - 1):
            assets.add_image(self.conn, aid, f"{i}.png", PNG)
        with self.assertRaises(AssetError):
            assets.add_image(self.conn, aid, "one-too-many.png", PNG)
        image = assets.get(self.conn, aid)["images"][0]
        assets.remove_image(self.conn, image["id"])
        self.assertFalse(os.path.exists(image["path"]))
        assets.delete(self.conn, aid)
        self.assertIsNone(assets.get(self.conn, aid))
        self.assertFalse(os.path.exists(os.path.join(assets.root(), str(aid))))

    def test_shared_library_and_project_assets_are_separate_scopes(self):
        p = Pipeline(self.conn)
        one, two = p.create_project("one"), p.create_project("two")
        shared = assets.create(self.conn, "FF", "character", "Kael")
        mine = assets.create(self.conn, "FF", "prop", "Cây gậy", project_id=one)
        names = lambda **kw: {a["name"] for a in assets.list_assets(self.conn, "FF", **kw)}  # noqa: E731
        self.assertEqual(names(project_id=one), {"Kael", "Cây gậy"})
        self.assertEqual(names(project_id=two), {"Kael"})                           # project two cannot see project one's own asset
        self.assertEqual(names(shared_only=True), {"Kael"})
        assets.attach(self.conn, one, shared)
        assets.attach(self.conn, one, mine)
        assets.attach(self.conn, one, mine)                                         # twice is fine
        self.assertEqual([a["name"] for a in assets.project_assets(self.conn, one)], ["Kael", "Cây gậy"])             # ordered by kind, then name
        assets.detach(self.conn, one, shared)
        self.assertEqual(len(assets.project_assets(self.conn, one)), 1)

    def test_assets_named_in_the_script_are_found(self):
        assets.create(self.conn, "FF", "character", "Lyra", aliases="Lyra Bạc; Cô gái cung thủ")
        assets.create(self.conn, "FF", "character", "Kael")
        assets.create(self.conn, "FF", "pet", "Sói")
        assets.create(self.conn, "AOV", "character", "Orin")
        text = "LYRA: Có thứ gì đó đang theo chúng ta.\nCô gái cung thủ giương cung. Kael rút kiếm, kael quay lại. Con sói tru."
        found = assets.find_in_text(self.conn, text, "FF")
        self.assertEqual([(a["name"], a["mentions"]) for a in found], [("Kael", 2), ("Lyra", 2), ("Sói", 1)])
        self.assertNotIn("Orin", [a["name"] for a in found])                       # other game
        self.assertEqual(assets.find_in_text(self.conn, "Kaelan đi qua", "FF"), [])  # whole words only

    def test_chosen_assets_are_written_into_the_director_prompt_and_give_reference_pictures(self):
        p = Pipeline(self.conn)
        pid = p.create_project("dir")
        aid = assets.create(self.conn, "FF", "character", "Lyra", "tóc bạc dài, giáp xanh", "Lyra Bạc")
        assets.add_image(self.conn, aid, "front.png", PNG)
        self.assertEqual(assets.context_text(self.conn, pid), "")
        self.assertNotIn("Tài nguyên có sẵn", prompts.build_director_bundle(p, pid))
        assets.attach(self.conn, pid, aid)
        bundle = prompts.build_director_bundle(p, pid)
        self.assertIn("Tài nguyên có sẵn cho dự án này", bundle)
        self.assertIn("**Lyra** (tên khác: Lyra Bạc): tóc bạc dài, giáp xanh — có 1 ảnh tham khảo", bundle)
        self.assertEqual(len(assets.reference_paths(self.conn, pid)), 1)
        self.assertEqual(assets.reference_paths(self.conn, pid, kinds=("weapon",)), [])


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def put(self, *parts, data=PNG):
        path = os.path.join(self.dir, "src", *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def test_the_three_folder_layouts_are_understood(self):
        self.put("Nhân vật", "Lyra_front.png")
        self.put("Nhân vật", "Lyra_back.png")
        self.put("Nhân vật", "Kael 2.jpg")
        self.put("Vũ khí", "Cung băng", "1.png")
        self.put("Vũ khí", "Cung băng", "2.png")
        self.put("Bản đồ", "Rừng Elder.webp")
        self.put("Sói.png")                                                        # loose file: the default kind
        self.put("Nhân vật", "notes.txt", data=b"not a picture")
        self.put("Nhân vật", "huge.png", data=b"0" * (assets.MAX_IMAGE_BYTES + 1))
        res = assets.import_folder(self.conn, os.path.join(self.dir, "src"), "FF", "pet")
        rows = {(a["kind"], a["name"]): len(a["images"]) for a in assets.list_assets(self.conn, "FF")}
        self.assertEqual(rows[("character", "Lyra")], 2)
        self.assertEqual(rows[("character", "Kael")], 1)
        self.assertEqual(rows[("weapon", "Cung băng")], 2)
        self.assertEqual(rows[("location", "Rừng Elder")], 1)
        self.assertEqual(rows[("pet", "Sói")], 1)
        self.assertEqual(res["images_skipped"], 1)                                  # the >10 MB picture
        self.assertNotIn(("character", "notes"), rows)

    def test_importing_again_adds_to_existing_assets_instead_of_duplicating(self):
        self.put("Lyra_front.png")
        assets.import_folder(self.conn, os.path.join(self.dir, "src"), "FF", "character")
        self.put("Lyra_side.png")
        assets.import_folder(self.conn, os.path.join(self.dir, "src"), "FF", "character")
        found = assets.list_assets(self.conn, "FF")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["name"], "Lyra")
        with self.assertRaises(AssetError):
            assets.import_folder(self.conn, os.path.join(self.dir, "missing"), "FF")


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.db, self.data, self.p, self.pid = split_only()
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data, "ASSET_DIR": os.path.join(self.tmp, "assets")})

    def tearDown(self):
        for k in ("PIPELINE_DB", "PIPELINE_DATA", "ASSET_DIR"):
            os.environ.pop(k, None)
        os.environ["DASHBOARD_AUTH"] = "off"

    def test_step_1_suggests_the_library_assets_that_the_script_mentions(self):
        aid = assets.create(self.p.conn, "FF", "character", "Lyra", "tóc bạc")
        assets.create(self.p.conn, "FF", "character", "Không có trong kịch bản")
        at = AppTest.from_file(APP, default_timeout=40).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Tài nguyên đi kèm kịch bản" in e.label and "1 gợi ý mới" in e.label for e in at.expander))
        next(b for b in at.button if b.key == f"as_use_{self.pid}_{aid}").click().run()
        self.assertEqual([a["name"] for a in assets.project_assets(self.p.conn, self.pid)], ["Lyra"])
        self.assertTrue(any("1 đã chọn" in e.label for e in at.expander))

    def test_the_panel_only_appears_once_the_script_is_split(self):
        tmp = tempfile.mkdtemp()
        os.environ["PIPELINE_DB"] = os.path.join(tmp, "e.sqlite")
        Pipeline(connect(os.environ["PIPELINE_DB"])).create_project("empty")
        at = AppTest.from_file(APP, default_timeout=40).run()
        self.assertFalse(any("Tài nguyên đi kèm kịch bản" in e.label for e in at.expander))

    def test_library_tab_is_for_owner_and_people_with_the_right(self):
        at = AppTest.from_file(APP, default_timeout=40).run()
        self.assertIn("Kho tài nguyên", [t.label for t in at.tabs])                 # auth off = owner
        os.environ["DASHBOARD_AUTH"] = "on"
        conn = connect(self.db)
        owner = auth.Identity(auth.OWNER_EMAIL, "o", "owner", [])
        auth.ensure_owner(conn)
        auth.add_user(conn, owner, "editor@garena.vn", ["assets"])

        def labels(email):
            a = AppTest.from_file(APP, default_timeout=40).run()
            a.text_input(key="login_email").set_value(email)
            next(b for b in a.button if b.key == "login_btn").click().run()
            return [t.label for t in a.tabs]

        self.assertIn("Kho tài nguyên", labels("editor@garena.vn"))
        self.assertNotIn("Kho tài nguyên", labels("plain@garena.vn"))
        self.assertIn("assets", auth.PERM_LABELS)                                   # shows up as a column of the permission table


if __name__ == "__main__":
    unittest.main()
