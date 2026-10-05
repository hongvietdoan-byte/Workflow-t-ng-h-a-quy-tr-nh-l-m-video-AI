"""S14.43B (06/10/2026): Kho — gốc ảnh tuyệt đối, chặn thêm mục trùng, công cụ gộp mục trùng tools/kho_merge.py.

Bối cảnh: mục 414 'CHIM CÁNH CỤT' (S14.37) trùng mục 303 'Mr.Waggor' (nhập từ ff.garena.com); S14.33 mất 33 file ảnh vì
assets.root() tương đối theo thư mục đang chạy (hàng CSDL vào máy chính, file vào worktree bị dọn)."""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

from core import assets
from core.assets import AssetError
from core.db import connect
from tests.test_new_skills import PNG

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import kho_merge  # noqa: E402

CLEAN_ENV = {k: v for k, v in os.environ.items() if k not in ("ASSET_DIR", "PIPELINE_DB")}


class _Home(unittest.TestCase):
    """A fake install: <tmp>/home/data/manifest.sqlite + <tmp>/home/data/assets, and a different working folder <tmp>/elsewhere."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        self.elsewhere = os.path.join(self.tmp, "elsewhere")
        os.makedirs(os.path.join(self.home, "data"))
        os.makedirs(self.elsewhere)
        self.db = os.path.join(self.home, "data", "manifest.sqlite")
        env = mock.patch.dict(os.environ, dict(CLEAN_ENV, PIPELINE_DB=self.db), clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.cwd = os.getcwd()
        os.chdir(self.elsewhere)
        self.conn = connect(self.db)

    def tearDown(self):
        self.conn.close()
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---- A: assets.root() neo tuyệt đối ----------------------------------------------------------------------------------------------
class RootIsAnchoredTests(_Home):
    def test_root_is_absolute_and_next_to_the_database_from_any_working_folder(self):
        self.assertTrue(os.path.isabs(assets.root()))
        self.assertEqual(os.path.normcase(assets.root()), os.path.normcase(os.path.join(self.home, "data", "assets")))

    def test_root_without_any_setting_is_the_repository_not_the_working_folder(self):
        with mock.patch.dict(os.environ, CLEAN_ENV, clear=True):
            self.assertEqual(os.path.normcase(assets.root()), os.path.normcase(os.path.join(assets.REPO, "data", "assets")))

    def test_picture_written_from_another_working_folder_lands_next_to_the_database(self):
        aid = assets.create(self.conn, "FF", "pet", "Mr.Waggor")
        assets.add_image(self.conn, aid, "a.png", PNG)
        stored = self.conn.execute("SELECT path FROM asset_images WHERE asset_id=?", (aid,)).fetchone()[0]
        self.assertEqual(stored, os.path.join("data", "assets", str(aid), "1.png"))          # format of the stored path unchanged
        self.assertTrue(os.path.isfile(os.path.join(self.home, "data", "assets", str(aid), "1.png")))
        self.assertFalse(os.path.exists(os.path.join(self.elsewhere, "data")))                # nothing under the working folder
        self.assertTrue(os.path.isfile(assets.resolve(stored)))

    def test_delete_never_removes_a_folder_under_the_working_folder(self):
        aid = assets.create(self.conn, "FF", "pet", "Mr.Waggor")
        assets.add_image(self.conn, aid, "a.png", PNG)
        decoy = os.path.join(self.elsewhere, "data", "assets", str(aid))
        os.makedirs(decoy)
        open(os.path.join(decoy, "keep.png"), "wb").write(PNG)
        assets.delete(self.conn, aid)
        self.assertTrue(os.path.isfile(os.path.join(decoy, "keep.png")))
        self.assertFalse(os.path.exists(os.path.join(self.home, "data", "assets", str(aid))))

    def test_a_picture_folder_apart_from_the_database_is_reported(self):
        other = os.path.join(self.tmp, "other_assets")
        with mock.patch.dict(os.environ, {"ASSET_DIR": other}):
            msg = assets.root_warning()
        self.assertIn("other_assets", msg)
        self.assertIn("manifest.sqlite", msg)
        self.assertIsNone(assets.root_warning())


# ---- B: chặn thêm mục trùng ------------------------------------------------------------------------------------------------------
class DuplicateGuardTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ, {"ASSET_DIR": os.path.join(self.dir, "assets")})
        env.start()
        self.addCleanup(env.stop)
        self.conn = connect()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_name_key_ignores_case_accents_dots_and_spaces(self):
        self.assertEqual(assets.name_key("Mr.Waggor"), assets.name_key("Mr. Waggor"))
        self.assertEqual(assets.name_key("Mr.Waggor"), assets.name_key("mr waggor"))
        self.assertEqual(assets.name_key("CHIM CÁNH CỤT"), assets.name_key("chim canh cut"))
        self.assertNotEqual(assets.name_key("KENTA"), assets.name_key("KENTA OB55"))

    def test_an_alias_naming_an_existing_entry_is_refused_with_its_id(self):
        keep = assets.create(self.conn, "FF", "pet", "Mr.Waggor")
        with self.assertRaises(AssetError) as e:
            assets.create(self.conn, "FF", "pet", "CHIM CÁNH CỤT", aliases="chim cánh cụt, penguin, Mr. Waggor")
        self.assertIn(f"#{keep}", str(e.exception))
        self.assertIn("Mr.Waggor", str(e.exception))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0], 1)

    def test_a_name_spelled_differently_is_refused(self):
        assets.create(self.conn, "FF", "pet", "Mr.Waggor")
        for name in ("Mr. Waggor", "mr waggor", "MR-WAGGOR"):
            with self.assertRaises(AssetError):
                assets.create(self.conn, "FF", "pet", name)

    def test_another_kind_or_game_is_not_a_duplicate(self):
        assets.create(self.conn, "FF", "pet", "Mr.Waggor")
        assets.create(self.conn, "FF", "character", "Mr. Waggor")
        assets.create(self.conn, "AOV", "pet", "Mr. Waggor")

    def test_allow_duplicate_needs_a_reason_and_is_written_to_the_audit_log(self):
        assets.create(self.conn, "FF", "pet", "Mr.Waggor")
        with self.assertRaises(AssetError):
            assets.create(self.conn, "FF", "pet", "Mr. Waggor", allow_duplicate=True)
        aid = assets.create(self.conn, "FF", "pet", "Mr. Waggor", allow_duplicate=True, duplicate_reason="bản skin khác")
        self.assertTrue(aid)
        row = self.conn.execute("SELECT action, detail FROM audit_log ORDER BY id DESC").fetchone()
        self.assertEqual(row["action"], "kho_create_duplicate")
        self.assertIn("bản skin khác", row["detail"])

    def test_find_duplicates_lists_the_suspected_pairs(self):
        a = assets.create(self.conn, "FF", "pet", "Mr.Waggor")
        b = assets.create(self.conn, "FF", "pet", "CHIM CÁNH CỤT", aliases="penguin, Mr. Waggor", allow_duplicate=True,
                          duplicate_reason="dựng lại ca 414")
        assets.create(self.conn, "FF", "pet", "Kactus")
        pairs = assets.find_duplicates(self.conn)
        self.assertEqual([(p["a"]["id"], p["b"]["id"]) for p in pairs], [(a, b)])
        self.assertIn("mrwaggor", pairs[0]["keys"])


# ---- C: tools/kho_merge.py -------------------------------------------------------------------------------------------------------
PROFILE = json.dumps({"appearance": "béo tròn, khăn bandana", "approved": True}, ensure_ascii=False)


class KhoMergeTests(_Home):
    def setUp(self):
        super().setUp()
        c = self.conn
        self.keep = assets.create(c, "FF", "pet", "Mr.Waggor", "[ff.garena.com] Thú cưng: chuột lang.")
        assets.add_image(c, self.keep, "a.png", PNG)
        assets.add_image(c, self.keep, "b.png", PNG + b"1")
        self.merge = assets.create(c, "FF", "pet", "CHIM CÁNH CỤT", "Pet chim cánh cụt của Kelly.",
                                   "chim cánh cụt, cánh cụt, penguin, Mr Waggor, Mr. Waggor, Waggor", allow_duplicate=True,
                                   duplicate_reason="dựng lại ca 414")
        assets.add_image(c, self.merge, "k.png", PNG + b"2", status="pending")
        c.execute("UPDATE assets SET profile=? WHERE id=?", (PROFILE, self.merge))
        p1 = c.execute("INSERT INTO projects (name, created_at) VALUES ('a', 0)").lastrowid
        p2 = c.execute("INSERT INTO projects (name, created_at) VALUES ('b', 0)").lastrowid
        self.p1, self.p2 = p1, p2
        c.executemany("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", [(p1, self.merge), (p2, self.merge), (p2, self.keep)])
        c.execute("INSERT INTO project_assets_declined (project_id, asset_id) VALUES (?,?)", (p1, self.merge))
        c.execute("INSERT INTO characters (project_id, name, description, ref_asset_id) VALUES (?, 'PET', '', ?)", (p1, self.merge))
        c.commit()

    def count(self, sql, *a):
        return self.conn.execute(sql, a).fetchone()[0]

    def test_dry_run_changes_nothing_and_prints_the_plan(self):
        before = self.count("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", self.merge)
        plan = kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        text = kho_merge.plan_text(plan)
        self.assertEqual(plan["leftovers"], [])                                    # the planned file is not reported as a stray one
        self.assertIn("3.png", text)
        self.assertIn("Mr. Waggor", text)
        self.assertIn("project_assets", text)
        self.assertEqual(self.count("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", self.merge), before)
        self.assertTrue(os.path.isfile(os.path.join(self.home, "data", "assets", str(self.merge), "1.png")))
        self.assertFalse(os.path.exists(os.path.join(self.home, "data", "backup")))

    def test_apply_moves_everything_into_the_kept_entry(self):
        plan = kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        report = kho_merge.apply(self.conn, plan, self.db)
        self.assertTrue(os.path.isfile(report["backup"]))
        self.assertIn(f"manifest.before_kho_merge_", report["backup"])
        a = assets.get(self.conn, self.keep)
        self.assertEqual(a["name"], "Mr. Waggor")
        keys = [assets.name_key(x) for x in a["aliases"].split(",")]
        self.assertIn(assets.name_key("CHIM CÁNH CỤT"), keys)
        self.assertNotIn(assets.name_key("Mr. Waggor"), keys)                     # an alias equal to the name is dropped
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(a["description"].startswith("[ff.garena.com]"))
        self.assertIn("Pet chim cánh cụt của Kelly.", a["description"])
        self.assertEqual(json.loads(self.conn.execute("SELECT profile FROM assets WHERE id=?", (self.keep,)).fetchone()[0])["appearance"],
                         "béo tròn, khăn bandana")
        imgs = self.conn.execute("SELECT path, status FROM asset_images WHERE asset_id=? ORDER BY sort", (self.keep,)).fetchall()
        self.assertEqual([r["status"] for r in imgs], ["approved", "approved", "pending"])          # status kept
        self.assertEqual(imgs[2]["path"], os.path.join("data", "assets", str(self.keep), "3.png"))  # relative, no overwrite
        for r in imgs:
            self.assertTrue(os.path.isfile(assets.resolve(r["path"])))
        with open(assets.resolve(imgs[0]["path"]), "rb") as f:
            self.assertEqual(f.read(), PNG)                                                  # 1.png of the kept entry untouched
        self.assertIsNone(assets.get(self.conn, self.merge))
        self.assertFalse(os.path.exists(os.path.join(self.home, "data", "assets", str(self.merge))))
        self.assertEqual(self.count("SELECT COUNT(*) FROM project_assets WHERE asset_id=?", self.merge), 0)
        self.assertEqual(sorted(r[0] for r in self.conn.execute("SELECT project_id FROM project_assets WHERE asset_id=?", (self.keep,))),
                         [self.p1, self.p2])
        self.assertEqual(self.count("SELECT COUNT(*) FROM project_assets_declined WHERE asset_id=?", self.keep), 1)
        self.assertEqual(self.count("SELECT COUNT(*) FROM characters WHERE ref_asset_id=?", self.keep), 1)
        self.assertEqual(self.count("SELECT COUNT(*) FROM audit_log WHERE action='kho_merge'"), 1)

    def test_a_failure_half_way_restores_database_and_files(self):
        plan = kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        with mock.patch.object(kho_merge, "_write_audit", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                kho_merge.apply(self.conn, plan, self.db)
        self.assertEqual(assets.get(self.conn, self.merge)["name"], "CHIM CÁNH CỤT")
        self.assertEqual(assets.get(self.conn, self.keep)["name"], "Mr.Waggor")
        self.assertEqual(self.count("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", self.merge), 1)
        self.assertTrue(os.path.isfile(os.path.join(self.home, "data", "assets", str(self.merge), "1.png")))
        self.assertFalse(os.path.exists(os.path.join(self.home, "data", "assets", str(self.keep), "3.png")))
        self.assertEqual(self.count("SELECT COUNT(*) FROM project_assets WHERE asset_id=?", self.merge), 2)

    def test_running_twice_does_not_break_anything(self):
        kho_merge.apply(self.conn, kho_merge.make_plan(self.conn, self.keep, self.merge, self.db), self.db)
        snapshot = [tuple(r) for r in self.conn.execute("SELECT id, asset_id, path, status FROM asset_images ORDER BY id")]
        with self.assertRaises(kho_merge.MergeError):
            kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        self.assertEqual([tuple(r) for r in self.conn.execute("SELECT id, asset_id, path, status FROM asset_images ORDER BY id")], snapshot)

    def test_different_kinds_or_two_profiles_are_refused_before_any_change(self):
        other = assets.create(self.conn, "FF", "character", "Kelly")
        with self.assertRaises(kho_merge.MergeError):
            kho_merge.make_plan(self.conn, self.keep, other, self.db)
        self.conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps({"appearance": "khác"}), self.keep))
        self.conn.commit()
        with self.assertRaises(kho_merge.MergeError):
            kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)

    def test_command_line_dry_run_then_yes(self):
        self.conn.close()
        with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()) as out:
            kho_merge.main(["--db", self.db, "--keep", str(self.keep), "--merge", str(self.merge)])
        self.assertIn("CHẠY THỬ", out.getvalue())
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM assets WHERE id=?", (self.merge,)).fetchone()[0], 1)
        conn.close()
        with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()) as out:
            kho_merge.main(["--db", self.db, "--keep", str(self.keep), "--merge", str(self.merge), "--yes"])
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM assets WHERE id=?", (self.merge,)).fetchone()[0], 0)
        conn.close()
        with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()) as out:
            kho_merge.main(["--db", self.db, "--find-duplicates"])
        self.assertIn("Không thấy", out.getvalue())
        self.conn = connect(self.db)


if __name__ == "__main__":
    unittest.main()
