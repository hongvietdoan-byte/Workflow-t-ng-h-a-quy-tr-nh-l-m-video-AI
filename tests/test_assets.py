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



def sync_and_approve(conn, *a, **k):
    """Folder sync puts new pictures in the review box (G2); these tests check how folders are read, so approve what came in.
    The review box itself is tested in tests/test_library_review.py."""
    rep = assets.sync_folder(conn, *a, **k)
    assets.approve_images(conn, [i["id"] for i in assets.pending_images(conn)])
    return rep


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
        self.put("Nhân vật", "Lyra_back.png", data=PNG + b"back")
        self.put("Nhân vật", "Kael 2.jpg")
        self.put("Vũ khí", "Cung băng", "1.png")
        self.put("Vũ khí", "Cung băng", "2.png", data=PNG + b"two")
        self.put("Bản đồ", "Rừng Elder.webp")
        self.put("Sói.png")                                                        # loose file: the default kind
        self.put("Nhân vật", "notes.txt", data=b"not a picture")
        self.put("Nhân vật", "huge.png", data=b"0" * (assets.MAX_IMAGE_BYTES + 1))
        res = assets.sync_folder(self.conn, os.path.join(self.dir, "src"), "FF", "pet")
        rows = {(a["kind"], a["name"]): len(a["images"]) + len(a["pending"]) for a in assets.list_assets(self.conn, "FF")}
        self.assertEqual(rows[("character", "Lyra")], 2)
        self.assertEqual(rows[("character", "Kael")], 1)
        self.assertEqual(rows[("weapon", "Cung băng")], 2)
        self.assertEqual(rows[("location", "Rừng Elder")], 1)
        self.assertEqual(rows[("pet", "Sói")], 1)
        self.assertEqual(len(res["skipped"]), 1)                                    # the >10 MB picture
        self.assertNotIn(("character", "notes"), rows)

    def test_importing_again_adds_to_existing_assets_instead_of_duplicating(self):
        self.put("Lyra_front.png")
        assets.sync_folder(self.conn, os.path.join(self.dir, "src"), "FF", "character")
        self.put("Lyra_side.png", data=PNG + b"side")
        assets.sync_folder(self.conn, os.path.join(self.dir, "src"), "FF", "character")
        found = assets.list_assets(self.conn, "FF")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["name"], "Lyra")
        with self.assertRaises(AssetError):
            assets.sync_folder(self.conn, os.path.join(self.dir, "missing"), "FF")


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
        self.assertIn("settings_assets", [b.key for b in at.button])                 # auth off = owner
        os.environ["DASHBOARD_AUTH"] = "on"
        conn = connect(self.db)
        owner = auth.Identity(auth.OWNER_EMAIL, "o", "owner", [])
        auth.ensure_owner(conn)
        auth.add_user(conn, owner, "editor@garena.vn", ["assets"])

        def button_keys(email):
            a = AppTest.from_file(APP, default_timeout=40).run()
            a.text_input(key="login_email").set_value(email)
            next(b for b in a.button if b.key == "login_btn").click().run()
            return [b.key for b in a.button]

        self.assertIn("settings_assets", button_keys("editor@garena.vn"))
        self.assertNotIn("settings_assets", button_keys("plain@garena.vn"))
        self.assertIn("assets", auth.PERM_LABELS)                                   # shows up as a column of the permission table



class SyncTests(unittest.TestCase):
    """Keeping the library in step with a folder that people keep adding to (for example a synced Google Drive folder)."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()
        self.src = os.path.join(self.dir, "src")

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def put(self, *parts, data=PNG):
        path = os.path.join(self.src, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def sync(self, **kw):
        return sync_and_approve(self.conn, self.src, "FF", "character", **kw)

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM asset_images").fetchone()[0]

    def test_a_second_run_only_does_the_difference(self):
        self.put("LYRA.png", data=PNG + b"1")
        self.put("KAEL.png", data=PNG + b"2")
        first = self.sync()
        self.assertEqual((sorted(first["created"]), first["added"]), (["KAEL", "LYRA"], 2))
        again = self.sync()
        self.assertEqual((again["added"], again["updated"], again["unchanged"], again["created"]), (0, 0, 2, []))
        self.put("ORIN.png", data=PNG + b"3")                                       # someone drops a new character in the folder
        third = self.sync()
        self.assertEqual((third["created"], third["added"], third["unchanged"]), (["ORIN"], 1, 2))
        self.assertEqual(self.count(), 3)

    def test_an_edited_file_replaces_its_picture_and_keeps_what_people_typed_in_the_dashboard(self):
        path = self.put("LYRA.png", data=PNG + b"old")
        self.sync()
        asset = assets.list_assets(self.conn, "FF")[0]
        assets.update(self.conn, asset["id"], "Lyra", "Lyra Bạc", "tóc bạc dài")        # edited by hand in the dashboard
        with open(path, "wb") as f:
            f.write(PNG + b"new version")
        rep = self.sync()
        self.assertEqual((rep["updated"], rep["added"]), (1, 0))
        after = assets.get(self.conn, asset["id"])
        self.assertEqual((after["name"], after["aliases"], after["description"]), ("Lyra", "Lyra Bạc", "tóc bạc dài"))
        with open(after["images"][0]["path"], "rb") as f:
            self.assertEqual(f.read(), PNG + b"new version")
        self.assertEqual(len(after["images"]), 1)

    def test_a_renamed_or_moved_picture_is_not_added_twice(self):
        old = self.put("LYRA.png", data=PNG + b"same picture")
        self.sync()
        os.rename(old, os.path.join(self.src, "LYRA_final.png"))
        rep = self.sync()
        self.assertEqual((rep["moved"], rep["added"]), (1, 0))
        self.assertEqual(self.count(), 1)

    def test_ignore_words_skip_frames_and_folders(self):
        self.put("LYRA.png", data=PNG + b"1")
        self.put("LYRA_khung.png", data=PNG + b"2")
        self.put("khung", "KAEL.png", data=PNG + b"3")
        self.put("Backup", "ORIN.png", data=PNG + b"4")
        rep = self.sync()
        self.assertEqual([a["name"] for a in assets.list_assets(self.conn, "FF")], ["LYRA"])
        self.assertEqual(rep["ignored"], 1)                                          # the file; the two folders are skipped whole
        custom = self.sync(ignore="")                                                # nothing ignored when the words are cleared
        self.assertGreaterEqual(len(custom["created"]), 2)

    def test_files_that_disappeared_are_reported_and_only_removed_on_request(self):
        keep = self.put("LYRA.png", data=PNG + b"1")
        gone = self.put("KAEL.png", data=PNG + b"2")
        self.sync()
        os.remove(gone)
        rep = self.sync()
        self.assertEqual(len(rep["missing"]), 1)
        self.assertIn("KAEL", rep["missing"][0])
        self.assertEqual(self.count(), 2)                                            # still there: nothing is deleted by default
        rep = self.sync(remove_missing=True)
        self.assertEqual((rep["removed"], self.count()), (1, 1))
        self.assertTrue(os.path.exists(keep))

    def test_a_saved_source_is_synced_automatically_only_when_its_folder_changed(self):
        self.put("LYRA.png", data=PNG + b"1")
        sid = assets.add_source(self.conn, "FF", self.src, "character")
        with self.assertRaises(AssetError):
            assets.add_source(self.conn, "FF", self.src)                              # no duplicates
        with self.assertRaises(AssetError):
            assets.add_source(self.conn, "FF", os.path.join(self.dir, "nowhere"))
        first = assets.auto_sync(self.conn)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["report"]["created"], ["LYRA"])
        self.assertIn("mục mới", assets.list_sources(self.conn)[0]["last_summary"])
        self.assertEqual(assets.auto_sync(self.conn), [])                             # nothing changed: no work
        self.put("KAEL.png", data=PNG + b"2")
        second = assets.auto_sync(self.conn)
        self.assertEqual(second[0]["report"]["created"], ["KAEL"])
        assets.set_source(self.conn, sid, "character", "khung", False)               # auto switched off: left alone
        self.put("ORIN.png", data=PNG + b"3")
        self.assertEqual(assets.auto_sync(self.conn), [])
        self.assertEqual(assets.run_source(self.conn, sid)["created"], ["ORIN"])     # but "sync now" still works

    def test_an_unavailable_folder_is_reported_not_fatal(self):
        self.put("LYRA.png")
        assets.add_source(self.conn, "FF", self.src)
        assets.auto_sync(self.conn)
        shutil.rmtree(self.src)                                                       # e.g. the Drive is not connected today
        self.assertEqual(assets.auto_sync(self.conn), [])
        self.assertIn("Lỗi", assets.list_sources(self.conn)[0]["last_summary"])
        self.assertEqual(self.count(), 1)                                             # the library keeps what it has

    def test_uploading_many_pictures_at_once_groups_by_name_and_skips_duplicates(self):
        files = [("LYRA_front.png", PNG + b"1"), ("LYRA_back.png", PNG + b"2"), ("KAEL.png", PNG + b"3"), ("LYRA_copy.png", PNG + b"1")]
        rep = assets.add_files(self.conn, "FF", "character", files)
        self.assertEqual((sorted(rep["created"]), rep["added"], rep["unchanged"]), (["KAEL", "LYRA"], 3, 1))
        again = assets.add_files(self.conn, "FF", "character", files)
        self.assertEqual((again["created"], again["added"], again["unchanged"]), ([], 0, 4))

    def test_old_databases_get_the_new_columns_and_table(self):
        path = os.path.join(self.dir, "old.sqlite")
        conn = connect(path)
        conn.execute("ALTER TABLE asset_images DROP COLUMN src_path")
        conn.execute("ALTER TABLE asset_images DROP COLUMN sha256")
        conn.execute("DROP TABLE asset_sources")
        conn.commit()
        conn.close()
        conn = connect(path)
        self.assertTrue({"src_path", "sha256"} <= {r["name"] for r in conn.execute("PRAGMA table_info(asset_images)")})
        self.assertEqual(assets.list_sources(conn), [])


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_merging_moves_the_pictures_keeps_them_on_disk_and_turns_the_name_into_an_alias(self):
        keep = assets.create(self.conn, "FF", "character", "CHRONO")
        dup = assets.create(self.conn, "FF", "character", "CHRONO1", aliases="Chrono Mới")
        assets.add_image(self.conn, keep, "a.png", PNG + b"a")
        assets.add_image(self.conn, dup, "b.png", PNG + b"b")
        assets.add_image(self.conn, dup, "c.png", PNG + b"c")
        p = Pipeline(self.conn)
        pid = p.create_project("m")
        assets.attach(self.conn, pid, dup)
        self.assertEqual(assets.merge(self.conn, dup, keep), 2)
        merged = assets.get(self.conn, keep)
        self.assertEqual(len(merged["images"]), 3)
        self.assertTrue(all(os.path.exists(i["path"]) for i in merged["images"]))          # files were moved, not lost with the old folder
        self.assertIsNone(assets.get(self.conn, dup))
        self.assertIn("CHRONO1", merged["aliases"])
        self.assertIn("Chrono Mới", merged["aliases"])
        self.assertEqual([a["name"] for a in assets.project_assets(self.conn, pid)], ["CHRONO"])   # projects follow the merge
        with self.assertRaises(AssetError):
            assets.merge(self.conn, keep, keep)

    def test_a_folder_of_descriptively_named_pictures_gives_one_asset_per_name(self):
        src = os.path.join(self.dir, "maps", "MAP Đảo Thế Kỷ")
        os.makedirs(src)
        for name, seed in (("burger 1.png", 1), ("burger 2.png", 2), ("khu vuc nha kinh 4.png", 3), ("cong dich chuyen.png", 4)):
            with open(os.path.join(src, name), "wb") as f:
                f.write(PNG + bytes([seed]))
        sync_and_approve(self.conn, os.path.join(self.dir, "maps"), "FF", "location")
        by = {a["name"]: len(a["images"]) for a in assets.list_assets(self.conn, "FF")}
        self.assertEqual(by, {"burger": 2, "khu vuc nha kinh": 1, "cong dich chuyen": 1})
        numbered = os.path.join(self.dir, "maps2", "Khu vực - Dock")
        os.makedirs(numbered)
        for n in (1, 2):
            with open(os.path.join(numbered, f"{n}.png"), "wb") as f:
                f.write(PNG + bytes([10 + n]))
        sync_and_approve(self.conn, os.path.join(self.dir, "maps2"), "FF", "location")
        self.assertEqual(len(next(a for a in assets.list_assets(self.conn, "FF") if a["name"] == "Khu vực - Dock")["images"]), 2)   # 1.png, 2.png: the folder names it

    def test_a_big_folder_is_sampled_evenly_instead_of_taking_the_first_shots(self):
        self.assertEqual(assets._spread([f"{i:02d}.png" for i in range(1, 67)], 6), ["01.png", "14.png", "27.png", "40.png", "53.png", "66.png"])
        self.assertEqual(assets._spread(["a", "b"], 6), ["a", "b"])
        src = os.path.join(self.dir, "maps")
        for n in range(1, 21):
            os.makedirs(os.path.join(src, "Khu vực - Đền"), exist_ok=True)
            with open(os.path.join(src, "Khu vực - Đền", f"{n:02d}.png"), "wb") as f:
                f.write(PNG + bytes([n]))
        rep = sync_and_approve(self.conn, src, "FF", "location")
        self.assertEqual(rep["added"], 6)
        labels = [i["label"] for i in assets.list_assets(self.conn, "FF")[0]["images"]]
        self.assertEqual(labels, ["01", "05", "09", "12", "16", "20"])                    # spread over the 20 shots

    def test_trailing_words_new_and_old_are_not_part_of_the_name(self):
        self.assertEqual(assets._stem_name("FORD new.png"), "FORD")
        self.assertEqual(assets._stem_name("Kelly_new_2.png"), "Kelly")
        self.assertEqual(assets._stem_name("A124.png"), "A124")


class BigPicturesAndMapsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()
        self.src = os.path.join(self.dir, "maps")
        self.saved_limit = assets.MAX_IMAGE_BYTES

    def tearDown(self):
        assets.MAX_IMAGE_BYTES = self.saved_limit
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def noise_png(self, path, size=700):
        import io
        from PIL import Image
        img = Image.frombytes("RGB", (size, size), os.urandom(size * size * 3))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, "PNG")

    def test_a_picture_over_the_limit_is_stored_as_a_smaller_copy_and_the_original_is_untouched(self):
        assets.MAX_IMAGE_BYTES = 300_000                                          # pretend 300 KB is the limit
        path = os.path.join(self.src, "Khu vực - Dock", "1.png")
        self.noise_png(path)
        original = os.path.getsize(path)
        self.assertGreater(original, assets.MAX_IMAGE_BYTES)
        rep = sync_and_approve(self.conn, self.src, "FF", "location")
        self.assertEqual((rep["added"], rep["skipped"]), (1, []))
        stored = assets.list_assets(self.conn, "FF")[0]["images"][0]["path"]
        self.assertTrue(stored.endswith(".jpg"))
        self.assertLessEqual(os.path.getsize(stored), assets.MAX_IMAGE_BYTES)
        self.assertEqual(os.path.getsize(path), original)
        again = sync_and_approve(self.conn, self.src, "FF", "location")          # and it is recognised next time
        self.assertEqual((again["unchanged"], again["added"]), (1, 0))

    def test_something_that_is_not_a_picture_is_still_refused_when_too_big(self):
        assets.MAX_IMAGE_BYTES = 1000
        aid = assets.create(self.conn, "FF", "location", "X")
        with self.assertRaises(AssetError):
            assets.add_image(self.conn, aid, "fake.png", b"0" * 5000)

    def test_unchanged_files_are_not_even_read_on_a_second_run(self):
        self.noise_png(os.path.join(self.src, "A.png"), 50)
        sync_and_approve(self.conn, self.src, "FF", "location")
        real_open = open
        opened = []

        def spy(file, *a, **k):
            if str(file).startswith(self.src):
                opened.append(file)
            return real_open(file, *a, **k)

        from unittest import mock
        with mock.patch("builtins.open", spy):
            rep = sync_and_approve(self.conn, self.src, "FF", "location")
        self.assertEqual((rep["unchanged"], opened), (1, []))                        # matters for a 4 GB folder on a network drive

    def test_a_map_of_areas_gives_one_asset_per_area_and_one_for_the_whole_map(self):
        for area in ("Khu vực - Dock", "Khu vực - Forest Red", "Khu vực - Mill"):
            for n in (1, 2):
                self.noise_png(os.path.join(self.src, "MAP Đảo Mặt Trời", area, f"{n}.png"), 30)
        self.noise_png(os.path.join(self.src, "MAP Đảo Thế Kỷ", "1.png"), 30)           # a map without areas
        rep = sync_and_approve(self.conn, self.src, "FF", "location")
        by = {a["name"]: a for a in assets.list_assets(self.conn, "FF")}
        self.assertIn("Khu vực - Dock", by)
        self.assertEqual(by["Khu vực - Dock"]["aliases"], "Dock")                    # what a script would call it
        self.assertEqual(by["Khu vực - Dock"]["description"], "Thuộc: MAP Đảo Mặt Trời")
        self.assertEqual(len(by["Khu vực - Dock"]["images"]), 2)
        whole = by["Đảo Mặt Trời"]                                                    # "MAP " dropped
        self.assertEqual(len(whole["images"]), 3)                                    # first picture of each area
        self.assertIn("Dock", whole["description"])
        self.assertIn("MAP Đảo Mặt Trời", whole["aliases"])
        self.assertIn("MAP Đảo Thế Kỷ", by)                                           # no areas: just the folder
        found = assets.find_in_text(self.conn, "Nhóm hạ cánh xuống Dock rồi chạy về Đảo Mặt Trời.", "FF")
        self.assertEqual(sorted(a["name"] for a in found), ["Khu vực - Dock", "Đảo Mặt Trời"])


class SyncDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.db, self.data, self.p, self.pid = split_only()
        self.src = os.path.join(self.tmp, "resources")
        os.makedirs(self.src)
        with open(os.path.join(self.src, "LYRA.png"), "wb") as f:
            f.write(PNG + b"1")
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data, "ASSET_DIR": os.path.join(self.tmp, "assets")})

    def tearDown(self):
        for k in ("PIPELINE_DB", "PIPELINE_DATA", "ASSET_DIR"):
            os.environ.pop(k, None)

    def test_adding_a_folder_source_syncs_it_and_shows_the_result(self):
        at = AppTest.from_file(APP, default_timeout=40).run()
        at.button(key="settings_assets").click().run()
        at.text_input(key="lib_import_path").set_value(self.src).run()
        next(b for b in at.button if b.key == "lib_import_go").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([a["name"] for a in assets.list_assets(self.p.conn, "FF")], ["LYRA"])
        self.assertEqual(len(assets.list_sources(self.p.conn)), 1)
        self.assertTrue(any("mục mới" in s.value for s in at.success))
        at.text_input(key="lib_import_path").set_value(os.path.join(self.tmp, "no-such-folder")).run()
        next(b for b in at.button if b.key == "lib_import_go").click().run()
        self.assertTrue(any("Không tìm thấy thư mục" in e.value for e in at.error))

    def test_opening_the_dashboard_picks_up_new_pictures_of_auto_folders(self):
        assets.add_source(self.p.conn, "FF", self.src, "character")
        at = AppTest.from_file(APP, default_timeout=40).run()
        self.assertFalse(at.exception)
        self.assertEqual([a["name"] for a in assets.list_assets(self.p.conn, "FF")], ["LYRA"])          # imported without any click
        with open(os.path.join(self.src, "KAEL.png"), "wb") as f:
            f.write(PNG + b"2")
        AppTest.from_file(APP, default_timeout=40).run()                                                  # a new session later
        self.assertEqual(sorted(a["name"] for a in assets.list_assets(self.p.conn, "FF")), ["KAEL", "LYRA"])

    def test_a_broken_source_does_not_stop_the_dashboard_from_opening(self):
        assets.add_source(self.p.conn, "FF", self.src, "character")
        shutil.rmtree(self.src)
        at = AppTest.from_file(APP, default_timeout=40).run()
        self.assertFalse(at.exception)


# ---- S14.4 C1a (04/10): merge không mất ảnh, xóa ảnh Kho vào thùng rác (khôi phục được), dọn sau 30 ngày --------------------------
class MergeKeepsEveryPictureTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _rows(self, aid):
        return [dict(r) for r in self.conn.execute("SELECT id, path, status FROM asset_images WHERE asset_id=? ORDER BY id", (aid,))]

    def test_pending_and_missing_file_pictures_move_too(self):
        keep = assets.create(self.conn, "FF", "character", "CHRONO")
        dup = assets.create(self.conn, "FF", "character", "CHRONO1")
        assets.add_image(self.conn, dup, "a.png", PNG + b"a")
        assets.add_image(self.conn, dup, "p.png", PNG + b"p", status="pending")
        gone = assets.add_image(self.conn, dup, "g.png", PNG + b"g")
        os.remove(gone)                                                    # file lost on disk, the row is still there
        self.assertEqual(assets.merge(self.conn, dup, keep), 3)
        rows = self._rows(keep)
        self.assertEqual(sorted(r["status"] for r in rows), ["approved", "approved", "pending"])
        self.assertEqual([w["asset"] for w in assets.pending_images(self.conn)], ["CHRONO"])   # still waiting for a person, not lost
        folder = os.path.normcase(os.path.join(assets.root(), str(keep)))
        self.assertTrue(all(os.path.normcase(r["path"]).startswith(folder) for r in rows))      # the lost one points into the new folder
        self.assertEqual(len(assets.missing_files(self.conn)), 1)                              # still reported, not silently dropped
        self.assertIsNone(assets.get(self.conn, dup))

    def test_a_full_target_is_refused_and_nothing_changes(self):
        keep = assets.create(self.conn, "FF", "character", "CHRONO")
        dup = assets.create(self.conn, "FF", "character", "CHRONO1")
        for i in range(assets.MAX_IMAGES_PER_ASSET - 1):
            assets.add_image(self.conn, keep, f"{i}.png", PNG + bytes([i]))
        assets.add_image(self.conn, dup, "b.png", PNG + b"b")
        assets.add_image(self.conn, dup, "c.png", PNG + b"c", status="pending")
        with self.assertRaises(AssetError) as e:
            assets.merge(self.conn, dup, keep)
        self.assertIn("còn 1", str(e.exception))                           # says how many places are left
        self.assertEqual(len(self._rows(dup)), 2)
        self.assertIsNotNone(assets.get(self.conn, dup))
        self.assertEqual(len(self._rows(keep)), assets.MAX_IMAGES_PER_ASSET - 1)

    def test_the_standard_profile_is_copied_or_the_merge_is_refused(self):
        keep = assets.create(self.conn, "FF", "character", "CHRONO")
        dup = assets.create(self.conn, "FF", "character", "CHRONO1")
        assets.set_profile(self.conn, dup, {"identity": "white hair"}, approved=True)
        assets.merge(self.conn, dup, keep)
        self.assertEqual(assets.get_profile(self.conn, keep)["identity"], "white hair")
        self.assertTrue(assets.get_profile(self.conn, keep)["approved"])
        other = assets.create(self.conn, "FF", "character", "CHRONO2")
        assets.set_profile(self.conn, other, {"identity": "black hair"}, approved=True)
        with self.assertRaises(AssetError):
            assets.merge(self.conn, other, keep)                           # two different approved profiles: a person decides
        self.assertIsNotNone(assets.get(self.conn, other))
        self.assertEqual(assets.get_profile(self.conn, keep)["identity"], "white hair")


class LibraryTrashTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect()
        self.aid = assets.create(self.conn, "FF", "character", "LYRA")

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_trashed_picture_is_hidden_kept_on_disk_and_restored(self):
        path = assets.add_image(self.conn, self.aid, "a.png", PNG + b"a")
        assets.add_image(self.conn, self.aid, "b.png", PNG + b"b", status="pending")
        first, = assets.get(self.conn, self.aid)["images"]
        pend, = assets.get(self.conn, self.aid)["pending"]
        assets.trash_image(self.conn, first["id"])
        assets.trash_image(self.conn, pend["id"])
        a = assets.get(self.conn, self.aid)
        self.assertEqual((a["images"], a["pending"], a["missing"]), ([], [], []))
        self.assertTrue(os.path.exists(path))                                         # the file stays until the trash is emptied
        self.assertEqual(sorted(r["id"] for r in assets.removed_images(self.conn, self.aid)), sorted([first["id"], pend["id"]]))
        self.assertEqual(assets.pending_images(self.conn), [])
        self.assertEqual(assets.list_assets(self.conn, "FF")[0]["images"], [])
        assets.restore_image(self.conn, first["id"])
        assets.restore_image(self.conn, pend["id"])
        a = assets.get(self.conn, self.aid)
        self.assertEqual([i["id"] for i in a["images"]], [first["id"]])                # back with the status it had
        self.assertEqual([i["id"] for i in a["pending"]], [pend["id"]])
        self.assertEqual(assets.removed_images(self.conn, self.aid), [])

    def test_a_trashed_picture_with_a_lost_file_is_not_reported_as_missing(self):
        path = assets.add_image(self.conn, self.aid, "a.png", PNG + b"a")
        old, = assets.get(self.conn, self.aid)["images"]
        assets.trash_image(self.conn, old["id"])
        os.remove(path)
        self.assertEqual(assets.missing_files(self.conn), [])
        self.assertEqual(assets.missing_files_detail(self.conn), [])
        with self.assertRaises(AssetError):                                           # nothing to bring back
            assets.restore_image(self.conn, old["id"])

    def test_trashed_pictures_free_their_place_and_a_full_asset_refuses_the_restore(self):
        assets.add_image(self.conn, self.aid, "a.png", PNG + b"a")
        old, = assets.get(self.conn, self.aid)["images"]
        assets.trash_image(self.conn, old["id"])
        for i in range(assets.MAX_IMAGES_PER_ASSET):                                  # the trashed one does not take a place
            assets.add_image(self.conn, self.aid, f"{i}.png", PNG + bytes([i]))
        with self.assertRaises(AssetError):
            assets.restore_image(self.conn, old["id"])
        self.assertEqual(len(assets.removed_images(self.conn, self.aid)), 1)

    def test_restoring_never_overwrites_a_newer_file(self):
        path = assets.add_image(self.conn, self.aid, "a.png", PNG + b"old")
        old, = assets.get(self.conn, self.aid)["images"]
        assets.trash_image(self.conn, old["id"])
        newer = assets.add_image(self.conn, self.aid, "a2.png", PNG + b"new")          # uploaded while the first was in the trash
        self.assertNotEqual(os.path.normcase(newer), os.path.normcase(path))
        assets.restore_image(self.conn, old["id"])
        self.assertEqual(len(assets.get(self.conn, self.aid)["images"]), 2)
        self.assertEqual(open(path, "rb").read(), PNG + b"old")
        self.assertEqual(open(newer, "rb").read(), PNG + b"new")

    def test_the_trash_is_emptied_after_the_retention_period(self):
        old_path = assets.add_image(self.conn, self.aid, "a.png", PNG + b"a")
        new_path = assets.add_image(self.conn, self.aid, "b.png", PNG + b"b")
        old, new = assets.get(self.conn, self.aid)["images"]
        assets.trash_image(self.conn, old["id"])
        assets.trash_image(self.conn, new["id"])
        self.conn.execute("UPDATE asset_images SET removed_at=datetime('now', '-31 days') WHERE id=?", (old["id"],))
        self.conn.commit()
        self.assertEqual(assets.purge_removed(self.conn, days=30), 1)
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(new_path))
        self.assertEqual([r["id"] for r in assets.removed_images(self.conn, self.aid)], [new["id"]])
        self.assertIsNone(self.conn.execute("SELECT 1 FROM asset_images WHERE id=?", (old["id"],)).fetchone())

    def test_remove_image_still_deletes_the_file_at_once(self):
        path = assets.add_image(self.conn, self.aid, "a.png", PNG + b"a")
        img, = assets.get(self.conn, self.aid)["images"]
        assets.remove_image(self.conn, img["id"])
        self.assertFalse(os.path.exists(path))

    def test_merge_carries_trashed_pictures_without_counting_them(self):
        keep = assets.create(self.conn, "FF", "character", "LYRA2")
        for i in range(assets.MAX_IMAGES_PER_ASSET):
            assets.add_image(self.conn, keep, f"{i}.png", PNG + bytes([i]))
        assets.trash_image(self.conn, assets.get(self.conn, keep)["images"][0]["id"])
        assets.add_image(self.conn, self.aid, "x.png", PNG + b"x")
        self.assertEqual(assets.merge(self.conn, self.aid, keep), 1)
        self.assertEqual(len(assets.get(self.conn, keep)["images"]), assets.MAX_IMAGES_PER_ASSET)
        self.assertEqual(len(assets.removed_images(self.conn, keep)), 1)


class LibraryKhoUiTests(unittest.TestCase):
    """The ⚙ → Kho buttons that lose data ask first (confirm_all); ui_v2 on."""

    def setUp(self):
        self.tmp, self.db, self.data, self.p, self.pid = split_only()
        self.env = {"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data, "ASSET_DIR": os.path.join(self.tmp, "assets"), "FEATURE_UI_V2": "1"}
        os.environ.update(self.env)

    def tearDown(self):
        for k in self.env:
            os.environ.pop(k, None)

    def _kho(self):
        at = AppTest.from_file(APP, default_timeout=40).run()
        at.button(key="settings_assets").click().run()
        self.assertFalse(at.exception)
        return at

    def test_deleting_a_picture_asks_then_trashes_it_and_it_can_be_restored(self):
        aid = assets.create(self.p.conn, "FF", "character", "LYRA")
        path = assets.add_image(self.p.conn, aid, "a.png", PNG + b"a")
        img, = assets.get(self.p.conn, aid)["images"]
        at = self._kho()
        at.button(key=f"lib_img_rm_{img['id']}").click().run()
        self.assertEqual(len(assets.get(self.p.conn, aid)["images"]), 1)               # only asked
        at.button(key=f"lib_img_rm_{img['id']}_yes").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(assets.get(self.p.conn, aid)["images"], [])
        self.assertTrue(os.path.exists(path))
        at.button(key=f"lib_img_restore_{img['id']}").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(assets.get(self.p.conn, aid)["images"]), 1)

    def test_merging_asks_first(self):
        keep = assets.create(self.p.conn, "FF", "character", "CHRONO")
        dup = assets.create(self.p.conn, "FF", "character", "CHRONO1")
        assets.add_image(self.p.conn, dup, "b.png", PNG + b"b", status="pending")
        at = self._kho()
        at.checkbox(key=f"lib_edit_{dup}").check().run()
        at.selectbox(key=f"lib_merge_{dup}").set_value(keep).run()
        at.button(key=f"lib_merge_go_{dup}").click().run()
        self.assertIsNotNone(assets.get(self.p.conn, dup))                              # only asked
        at.button(key=f"lib_merge_go_{dup}_yes").click().run()
        self.assertFalse(at.exception)
        self.assertIsNone(assets.get(self.p.conn, dup))
        self.assertEqual(len(assets.get(self.p.conn, keep)["pending"]), 1)

    def _lost(self, aid, name, src):
        self.p.conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, src_path, status) VALUES (?,?,?,?,?,?)",
                            (aid, os.path.join(self.tmp, "gone", name), name, 1, src, "approved"))
        self.p.conn.commit()
        return self.p.conn.execute("SELECT max(id) FROM asset_images").fetchone()[0]

    def test_unlink_all_asks_and_keeps_the_pictures_that_can_be_reloaded(self):
        aid = assets.create(self.p.conn, "FF", "character", "LYRA")
        src = os.path.join(self.tmp, "src.png")
        open(src, "wb").write(PNG)
        can = self._lost(aid, "1.png", src)
        cannot = self._lost(aid, "2.png", os.path.join(self.tmp, "nope.png"))
        at = self._kho()
        at.button(key="lib_lost_rm_all").click().run()
        self.assertEqual(len(assets.missing_files(self.p.conn)), 2)                     # only asked
        at.button(key="lib_lost_rm_all_yes").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m["id"] for m in assets.missing_files(self.p.conn)], [can])
        self.assertNotIn(cannot, [m["id"] for m in assets.missing_files(self.p.conn)])

    def test_a_reload_that_fails_says_why_instead_of_a_traceback(self):
        aid = assets.create(self.p.conn, "FF", "character", "LYRA")
        src = os.path.join(self.tmp, "huge.png")
        open(src, "wb").write(b"0" * (assets.MAX_IMAGE_BYTES + 1))                    # too big and not a picture: cannot be shrunk
        iid = self._lost(aid, "1.png", src)
        at = self._kho()
        at.button(key=f"lib_lost_reload_{iid}").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Không tải lại được" in e.value for e in at.error))


if __name__ == "__main__":
    unittest.main()
