import os
import shutil
import struct
import tempfile
import time
import unittest
import zlib

from core import asset_vision, assets, llm_runner
from core.db import connect


def picture(w, h, seed=0):
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (seed, seed, seed)).save(buf, "PNG")
    return buf.getvalue()


class FakeVision:
    name = "fake-vision"

    def __init__(self, answer="Tóc đen ngắn, áo khoác da đen, đeo găng tay tím."):
        self.answer, self.prompts, self.images = answer, [], []

    def complete(self, prompt, images=()):
        self.prompts.append(prompt)
        self.images.append(list(images))
        return llm_runner.LlmReply(self.answer, 20, 10)


class Base(unittest.TestCase):
    def setUp(self):
        asset_vision._errors.clear()
        asset_vision._progress.clear()
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.db = os.path.join(self.dir, "m.sqlite")
        self.conn = connect(self.db)

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def wait(self, game="FF"):
        for _ in range(200):
            if not asset_vision.active(game):
                return
            time.sleep(0.05)
        self.fail("the background read did not finish")


class DescribeTests(Base):
    def test_the_sheet_is_used_alongside_single_figure_shots_and_the_answer_is_stored(self):
        a = assets.create(self.conn, "FF", "character", "KELLY", "Vốn ghi tay: nữ chiến binh.", "", None, "x")
        assets.add_image(self.conn, a, "sheet.png", picture(1536, 1024, 1))
        assets.add_image(self.conn, a, "full.png", picture(550, 800, 2))
        client = FakeVision()
        self.assertTrue(asset_vision.sync_one(self.conn, client, a))
        names = {os.path.basename(p) for _, p in client.images[0]}
        self.assertEqual(names, {"1.png", "2.png"})                        # the sheet AND a single-figure shot were both shown
        updated = assets.get(self.conn, a)
        self.assertTrue(updated["description"].startswith("Vốn ghi tay: nữ chiến binh."))   # the person's own note is kept
        self.assertIn(asset_vision.MARK, updated["description"])
        self.assertIn("Tóc đen ngắn", updated["description"])

    def test_running_again_replaces_the_ai_block_instead_of_stacking_it(self):
        a = assets.create(self.conn, "FF", "character", "KENTA", "", "", None, "x")
        assets.add_image(self.conn, a, "p.png", picture(550, 800, 3))
        asset_vision.sync_one(self.conn, FakeVision("Bản mô tả cũ."), a)
        asset_vision.sync_one(self.conn, FakeVision("Bản mô tả mới."), a)
        desc = assets.get(self.conn, a)["description"]
        self.assertEqual(desc.count(asset_vision.MARK), 1)
        self.assertIn("Bản mô tả mới.", desc)
        self.assertNotIn("Bản mô tả cũ.", desc)

    def test_a_prop_or_weapon_is_not_eligible_only_characters_and_pets_are(self):
        w = assets.create(self.conn, "FF", "weapon", "Katana", "", "", None, "x")
        assets.add_image(self.conn, w, "k.png", picture(400, 400, 4))
        self.assertEqual(asset_vision.pending(self.conn, "FF"), 0)


class BackgroundTests(Base):
    def test_it_reads_every_eligible_asset_once_and_skips_what_is_already_done(self):
        a1 = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.conn, a1, "a.png", picture(550, 800, 1))
        a2 = assets.create(self.conn, "FF", "pet", "Kactus", "", "", None, "x")
        assets.add_image(self.conn, a2, "b.png", picture(550, 800, 2))
        w = assets.create(self.conn, "FF", "weapon", "Katana", "", "", None, "x")
        assets.add_image(self.conn, w, "c.png", picture(400, 400, 3))
        self.assertEqual(asset_vision.pending(self.conn, "FF"), 2)
        self.assertTrue(asset_vision.start(self.db, "FF", lambda: FakeVision()))
        self.wait()
        self.assertEqual(asset_vision.pending(self.conn, "FF"), 0)
        self.assertIn(asset_vision.MARK, assets.get(self.conn, a1)["description"])
        self.assertIn(asset_vision.MARK, assets.get(self.conn, a2)["description"])
        self.assertNotIn(asset_vision.MARK, assets.get(self.conn, w)["description"])          # weapons are untouched
        self.assertEqual(asset_vision.progress("FF"), {"done": 2, "total": 2})

    def test_a_broken_claude_stops_and_reports_once_without_looping(self):
        a = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.conn, a, "a.png", picture(550, 800, 1))

        class Broken:
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("Claude Code chưa đăng nhập", code="auth")
        self.assertTrue(asset_vision.start(self.db, "FF", lambda: Broken()))
        self.wait()
        self.assertIn("chưa đăng nhập", asset_vision.last_error("FF"))
        self.assertNotIn(asset_vision.MARK, assets.get(self.conn, a)["description"])
        self.assertFalse(asset_vision.start(self.db, "FF", lambda: FakeVision()))              # not retried in a loop
        asset_vision.clear_error("FF")
        self.assertTrue(asset_vision.start(self.db, "FF", lambda: FakeVision()))
        self.wait()
        self.assertIn(asset_vision.MARK, assets.get(self.conn, a)["description"])

    def test_nothing_starts_without_a_claude_or_without_anything_pending(self):
        self.assertFalse(asset_vision.start(self.db, "FF", lambda: FakeVision()))              # nothing to read
        a = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.conn, a, "a.png", picture(550, 800, 1))
        self.assertFalse(asset_vision.start(self.db, "FF", lambda: None))                      # no Claude configured


class DashboardTests(Base):
    APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")

    def test_the_panel_shows_how_many_are_pending_and_starts_a_background_read(self):
        from streamlit.testing.v1 import AppTest
        a = assets.create(self.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.conn, a, "a.png", picture(550, 800, 1))
        # asset_vision.start()'s default client_factory is bound to the real llm_runner.client_from_env at import time, so a module-attribute
        # mock never reaches it from here: control it through the environment (LLM_PROVIDER=mock), exactly as production does.
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.dir, "projects"), "LLM_PROVIDER": "mock"})
        try:
            at = AppTest.from_file(self.APP, default_timeout=40).run()
            self.assertFalse(at.exception)
            self.assertTrue(any("1 mục nhân vật/thú cưng chưa được đọc" in c.value for c in at.caption))
            next(b for b in at.button if b.key == "asset_vision_go").click().run()
            self.assertFalse(at.exception)
            self.wait()
            self.assertIn(asset_vision.MARK, assets.get(self.conn, a)["description"])
        finally:
            os.environ.pop("PIPELINE_DB", None)
            os.environ.pop("PIPELINE_DATA", None)
            os.environ.pop("LLM_PROVIDER", None)


if __name__ == "__main__":
    unittest.main()
