"""01/10 rà soát: B3 (ảnh gửi kèm video phải đúng tỉ lệ trước khi gửi) và B4 (CTA_TEXT không phải nhân vật)."""
import io
import unittest

from PIL import Image

from core import idea_to_script
from core.adapters import clipai


def _png(w, h):
    b = io.BytesIO()
    Image.new("RGB", (w, h), (10, 20, 30)).save(b, "PNG")
    return b.getvalue()


class B3Tests(unittest.TestCase):
    def test_sizes_of_bytes(self):
        self.assertEqual(clipai.image_sizes_of([_png(640, 360), b"not a picture"]), [(640, 360), (0, 0)])

    def test_a_wide_sheet_as_first_frame_or_ref_is_refused_before_sending(self):
        sizes = clipai.image_sizes_of([_png(1920, 1080), _png(1870, 500)])        # 3.74 : 1, like the 30/09 skill sheet
        bad = clipai.reference_image_problems("seedance", sizes)
        self.assertEqual(len(bad), 1)
        self.assertIn("ảnh 2", bad[0])

    def test_submit_refuses_a_bad_extra_picture_without_a_request(self):
        import os
        import tempfile
        calls = []

        class C:
            def post_multipart(self, *a, **k):
                calls.append(a)
                return {}
        d = tempfile.mkdtemp()
        first, wide = os.path.join(d, "a.png"), os.path.join(d, "w.png")
        open(first, "wb").write(_png(1280, 720))
        open(wide, "wb").write(_png(1870, 500))
        ad = clipai.ClipAIVideoProvider.__new__(clipai.ClipAIVideoProvider)
        ad.client = C()
        ad.resolution, ad.aspect_ratio, ad.kling_mode, ad.negative = "720p", "16:9", "pro", "ignore"
        with self.assertRaises(clipai.ProviderError) as cm:
            ad.submit(wide, "go", None, 5, model="dreamina-seedance-2-0-260128")
        self.assertEqual(cm.exception.code, "rule_violation")
        self.assertEqual(calls, [])


class B4Tests(unittest.TestCase):
    def test_cta_text_is_not_a_new_character(self):
        script = ("CẢNH 1 - 0-5s, Sân\nKELLY chạy.\nKELLY: Đi thôi!\n\n"
                  "CẢNH 2 - 5-10s, Sân\nMàn hình tối dần.\nCTA_TEXT: Tải game ngay\n")
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("b4")
        r = idea_to_script.check_script(p.conn, pid, script, {"duration_s": 60})
        self.assertFalse([f for f in r["flags"] if "CTA" in f.upper()], r["flags"])


if __name__ == "__main__":
    unittest.main()


class B5Tests(unittest.TestCase):
    def test_lost_picture_is_reloaded_from_source_or_unlinked(self):
        import os
        import tempfile
        from core import assets
        from core.db import connect
        conn = connect()
        d = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(d, "assets")             # the backup of unlinked rows goes into the library folder
        self.addCleanup(lambda: os.environ.pop("ASSET_DIR", None))
        src = os.path.join(d, "src.png")
        open(src, "wb").write(_png(400, 400))
        aid = assets.create(conn, "FF", "character", "B5TEST")
        conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, src_path, status) VALUES (?,?,?,?,?,?)",
                     (aid, os.path.join(d, "gone", "1.png"), "x", 1, src, "approved"))
        conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, src_path, status) VALUES (?,?,?,?,?,?)",
                     (aid, os.path.join(d, "gone", "2.png"), "y", 2, os.path.join(d, "nope.png"), "approved"))
        conn.commit()
        lost = {w["path"].split(os.sep)[-1]: w for w in assets.missing_files_detail(conn) if w["asset"] == "B5TEST"}
        self.assertTrue(lost["1.png"]["can_reload"])
        self.assertFalse(lost["2.png"]["can_reload"])
        self.assertTrue(assets.reload_image(conn, lost["1.png"]["id"]))
        self.assertFalse(assets.reload_image(conn, lost["2.png"]["id"]))
        self.assertEqual(len([w for w in assets.missing_files_detail(conn) if w["asset"] == "B5TEST"]), 1)
        # S14.4 (04/10): "gỡ liên kết tất cả" only drops the rows that can NOT be reloaded, after a JSON backup of them
        conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, src_path, status) VALUES (?,?,?,?,?,?)",
                     (aid, os.path.join(d, "gone", "3.png"), "z", 3, src, "approved"))
        conn.commit()
        self.assertEqual(assets.unlink_missing(conn), 1)
        left = [w for w in assets.missing_files_detail(conn) if w["asset"] == "B5TEST"]
        self.assertEqual([w["path"].split(os.sep)[-1] for w in left], ["3.png"])          # can still be reloaded: kept
        backups = [f for f in os.listdir(os.path.join(assets.root(), "_backup")) if f.startswith("unlink_missing_")]
        self.assertEqual(len(backups), 1)
        import json
        saved = json.load(open(os.path.join(assets.root(), "_backup", backups[0]), encoding="utf-8"))
        self.assertEqual([r["path"].split(os.sep)[-1] for r in saved["rows"]], ["2.png"])
        self.assertEqual(assets.unlink_missing(conn, only_unreloadable=False), 1)
        self.assertEqual([w for w in assets.missing_files_detail(conn) if w["asset"] == "B5TEST"], [])


class ReferenceUploadTests(unittest.TestCase):
    def test_project_only_pictures_are_approved_and_shared_ones_wait(self):
        from core import assets
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("refs")
        mine = assets.add_reference_images(p.conn, pid, "FF", "character", "Orion", [("a.png", _png(400, 600))], shared=False)
        row = p.conn.execute("SELECT status FROM asset_images WHERE asset_id=?", (mine["asset_id"],)).fetchone()
        self.assertEqual(row["status"], "approved")
        self.assertTrue(p.conn.execute("SELECT project_id FROM assets WHERE id=?", (mine["asset_id"],)).fetchone()["project_id"] == pid)
        shared = assets.add_reference_images(p.conn, pid, "FF", "location", "Sân thượng", [("b.png", _png(800, 450)), ("b.png", _png(800, 450))], shared=True)
        self.assertEqual((shared["added"], len(shared["skipped"])), (1, 1))                  # the same picture twice is kept once
        self.assertEqual(p.conn.execute("SELECT status FROM asset_images WHERE asset_id=?", (shared["asset_id"],)).fetchone()["status"], "pending")
        self.assertIsNone(p.conn.execute("SELECT project_id FROM assets WHERE id=?", (shared["asset_id"],)).fetchone()["project_id"])
        self.assertTrue(p.conn.execute("SELECT 1 FROM project_assets WHERE project_id=? AND asset_id=?", (pid, shared["asset_id"])).fetchone())
        with self.assertRaises(assets.AssetError):
            assets.add_reference_images(p.conn, pid, "FF", "character", " ", [], shared=False)
