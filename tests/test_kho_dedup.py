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


class _MergeHome(_Home):
    """Mục 303-giống (2 ảnh) + 414-giống (1 ảnh chờ duyệt, hồ sơ, alias), liên kết dự án / từ chối / nhân vật."""

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


class KhoMergeTests(_MergeHome):

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


# ---- rà độc lập 06/10 ------------------------------------------------------------------------------------------------------------
class MergeNeverTouchesAnotherInstallTests(_MergeHome):
    """Lỗi 1: chạy --db <bản sao> từ thư mục repo thật — resolve() dò cwd / REPO và kho_merge dời ẢNH THẬT của máy chính."""

    def test_pictures_of_the_working_folder_or_repository_are_never_moved(self):
        merge_file = os.path.join(self.home, "data", "assets", str(self.merge), "1.png")
        os.remove(merge_file)                                           # the copy has the row, not the file
        decoy_cwd = os.path.join(self.elsewhere, "data", "assets", str(self.merge), "1.png")
        fake_repo = os.path.join(self.tmp, "repo")
        decoy_repo = os.path.join(fake_repo, "data", "assets", str(self.merge), "1.png")
        for d in (decoy_cwd, decoy_repo):
            os.makedirs(os.path.dirname(d))
            open(d, "wb").write(b"real picture")
        with mock.patch.object(assets, "REPO", fake_repo):
            plan = kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
            self.assertIsNone(plan["moves"][0]["src"])
            self.assertIn("file mất", kho_merge.plan_text(plan))
            kho_merge.apply(self.conn, plan, self.db)
        self.assertTrue(os.path.isfile(decoy_cwd))
        self.assertTrue(os.path.isfile(decoy_repo))

    def test_resolve_stays_in_the_install_of_the_database(self):
        open(os.path.join(self.elsewhere, "x.png"), "wb").write(PNG)
        self.assertEqual(os.path.normcase(assets.resolve("x.png")), os.path.normcase(os.path.join(self.home, "x.png")))

    def test_plan_text_survives_a_picture_on_another_drive(self):
        plan = kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        with mock.patch.object(kho_merge.os.path, "relpath", side_effect=ValueError("path is on mount 'C:', start on mount 'D:'")):
            self.assertIn("1.png", kho_merge.plan_text(plan))


class BatchFlowsJoinTheExistingEntryTests(unittest.TestCase):
    """Lỗi 2: chặn trùng không được làm văng cả lô / cả nguồn; luồng tự động gắn ảnh vào mục có sẵn; mục chỉ-cho-dự án như cũ."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ, {"ASSET_DIR": os.path.join(self.dir, "assets")})
        env.start()
        self.addCleanup(env.stop)
        self.conn = connect()
        self.waggor = assets.create(self.conn, "FF", "pet", "Mr.Waggor")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def n_assets(self):
        return self.conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]

    def pics(self, aid):
        return self.conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", (aid,)).fetchone()[0]

    def project(self):
        pid = self.conn.execute("INSERT INTO projects (name, created_at) VALUES ('p', 0)").lastrowid
        self.conn.commit()
        return pid

    def test_add_files_puts_a_differently_spelled_name_into_the_existing_entry(self):
        rep = assets.add_files(self.conn, "FF", "pet", [("Mr. Waggor_front.png", PNG), ("Kactus.png", PNG + b"k")])
        self.assertEqual(rep["created"], ["Kactus"])
        self.assertEqual(self.n_assets(), 2)
        self.assertEqual(self.pics(self.waggor), 1)

    def test_sync_folder_puts_a_differently_spelled_name_into_the_existing_entry(self):
        folder = os.path.join(self.dir, "src")
        os.makedirs(folder)
        open(os.path.join(folder, "Mr. Waggor.png"), "wb").write(PNG)
        open(os.path.join(folder, "Kactus.png"), "wb").write(PNG + b"k")
        rep = assets.sync_folder(self.conn, folder, "FF", "pet")
        self.assertEqual(rep["created"], ["Kactus"])
        self.assertEqual(self.n_assets(), 2)
        self.assertEqual(self.pics(self.waggor), 1)

    def test_a_project_only_entry_is_not_blocked_by_a_shared_one(self):
        pid = self.project()
        rep = assets.add_reference_images(self.conn, pid, "FF", "pet", "Mr. Waggor", [("a.png", PNG)], shared=False)
        self.assertTrue(rep["created"])
        self.assertEqual(self.conn.execute("SELECT project_id FROM assets WHERE id=?", (rep["asset_id"],)).fetchone()[0], pid)
        with self.assertRaises(AssetError):                              # but twice in the same project is a duplicate
            assets.create(self.conn, "FF", "pet", "mr waggor", project_id=pid)

    def test_manual_create_box_refuses_then_creates_with_a_reason(self):
        from streamlit.testing.v1 import AppTest
        from tests.test_step1_flow import split_only
        tmp, db, data, p, _pid = split_only()
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": db, "PIPELINE_DATA": data, "ASSET_DIR": os.path.join(tmp, "assets"),
                                           "FEATURE_UI_V2": "1"})
        env.start()
        self.addCleanup(env.stop)
        assets.create(p.conn, "FF", "pet", "Mr.Waggor")
        app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
        at = AppTest.from_file(app, default_timeout=40).run()
        at.button(key="settings_assets").click().run()
        at.text_input(key="lib_new_name").set_value("Mr. Waggor").run()
        at.selectbox(key="lib_new_kind").set_value("pet").run()
        at.button(key="lib_new_go").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("#" in e.value and "Mr.Waggor" in e.value for e in at.error))
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM assets WHERE kind='pet'").fetchone()[0], 1)
        at.text_input(key="lib_new_dup_reason").set_value("bản skin khác").run()
        at.button(key="lib_new_go").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM assets WHERE kind='pet'").fetchone()[0], 2)

    def test_shared_reference_pictures_join_the_existing_entry(self):
        rep = assets.add_reference_images(self.conn, self.project(), "FF", "pet", "Mr. Waggor", [("a.png", PNG)], shared=True)
        self.assertEqual(rep["asset_id"], self.waggor)
        self.assertFalse(rep["created"])


class MergeJsonAndFileRefsTests(_MergeHome):
    """Lỗi 3: tham chiếu mục Kho nằm trong JSON (location_asset, bảng kê) / file (establish, models3d)."""

    def add_json_refs(self):
        c = self.conn
        ref = json.dumps({"location_asset": self.merge, "location": "bãi biển"}, ensure_ascii=False)
        c.execute("INSERT INTO scenes (project_id, idx, data) VALUES (?, 1, ?)", (self.p1, ref))
        c.execute("INSERT INTO story_scenes (project_id, idx, data) VALUES (?, 1, ?)", (self.p1, ref))
        c.execute("INSERT INTO scenes (project_id, idx, data) VALUES (?, 2, ?)", (self.p1, json.dumps({"location_asset": 99})))
        c.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)", (f"asset_checklist:{self.p1}",
                  json.dumps({"rows": [{"asset_id": self.merge, "name": "PET"}, {"asset_id": self.keep, "name": "X"}]})))
        c.commit()

    def test_dry_run_lists_every_kind_of_reference_even_when_zero(self):
        text = kho_merge.plan_text(kho_merge.make_plan(self.conn, self.keep, self.merge, self.db))
        for word in ("scenes.data.location_asset: 0", "story_scenes.data.location_asset: 0", "app_settings asset_checklist: 0",
                     "establish/index.json: 0", "models3d: 0"):
            self.assertIn(word, text)

    def test_json_references_move_in_the_same_transaction(self):
        self.add_json_refs()
        plan = kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        text = kho_merge.plan_text(plan)
        self.assertIn("scenes.data.location_asset: 1", text)
        self.assertIn("app_settings asset_checklist: 1", text)
        with mock.patch.object(kho_merge, "_write_audit", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                kho_merge.apply(self.conn, plan, self.db)
        self.assertEqual(json.loads(self.conn.execute("SELECT data FROM scenes WHERE idx=1").fetchone()[0])["location_asset"], self.merge)
        kho_merge.apply(self.conn, kho_merge.make_plan(self.conn, self.keep, self.merge, self.db), self.db)
        for t in ("scenes", "story_scenes"):
            d = json.loads(self.conn.execute(f"SELECT data FROM {t} WHERE idx=1").fetchone()[0])
            self.assertEqual(d, {"location_asset": self.keep, "location": "bãi biển"})
        self.assertEqual(json.loads(self.conn.execute("SELECT data FROM scenes WHERE idx=2").fetchone()[0])["location_asset"], 99)
        rows = json.loads(self.conn.execute("SELECT value FROM app_settings WHERE key=?", (f"asset_checklist:{self.p1}",)).fetchone()[0])["rows"]
        self.assertEqual([r["asset_id"] for r in rows], [self.keep, self.keep])

    def test_establish_or_models3d_references_refuse_unless_forced(self):
        est = os.path.join(self.home, "data", "projects", str(self.p1), "establish")
        os.makedirs(est)
        with open(os.path.join(est, "index.json"), "w", encoding="utf-8") as f:
            json.dump({"1": {"refs": [os.path.join("data", "assets", str(self.merge), "1.png")]}}, f)
        with self.assertRaises(kho_merge.MergeError) as e:
            kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        self.assertIn("establish", str(e.exception))
        plan = kho_merge.make_plan(self.conn, self.keep, self.merge, self.db, force_refs=True)
        self.assertIn("CẢNH BÁO", kho_merge.plan_text(plan))
        shutil.rmtree(est)
        os.makedirs(os.path.join(self.home, "data", "models3d", f"CHIM_C_NH_C_T_{self.merge}"))
        with self.assertRaises(kho_merge.MergeError) as e:
            kho_merge.make_plan(self.conn, self.keep, self.merge, self.db)
        self.assertIn("models3d", str(e.exception))


if __name__ == "__main__":
    unittest.main()
