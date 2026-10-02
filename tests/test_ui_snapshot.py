"""S13.3: logic của tools/ui_snapshot.py không cần trình duyệt (ma trận chụp, tên file, viewport, index.md, dữ liệu mẫu) + font Inter đi kèm."""
import os
import sqlite3
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ui_snapshot as U  # noqa: E402


class MatrixTest(unittest.TestCase):
    def test_full_matrix_covers_widths_themes_zooms(self):
        rich = [s for s in U.build_matrix() if s.state == "rich"]
        self.assertEqual({s.width for s in rich}, {1280, 1440, 1630, 1920})
        self.assertEqual({s.theme for s in rich}, {"dark", "light"})
        self.assertEqual({s.zoom for s in rich}, {100, 80})
        self.assertEqual(len(rich), 4 * 2 * 2 * (len(U.SCREENS) + len(U.OVERLAYS)))

    def test_extra_states_only_at_base_combo_and_project_screens(self):
        extra = [s for s in U.build_matrix() if s.state != "rich"]
        self.assertTrue(extra)
        self.assertTrue(all((s.width, s.theme, s.zoom) == U.BASE_STATE_COMBO for s in extra))
        self.assertTrue(all(s.screen in U.PROJECT_SCREENS + ("home",) for s in extra))

    def test_subset_is_small(self):
        sub = U.build_matrix(subset=True)
        self.assertLessEqual(len(sub), 12)
        self.assertEqual({s.width for s in sub}, {1440})

    def test_filters_and_bad_values(self):
        got = U.build_matrix(widths="1280", themes="light", zooms="80", only="home,money", states="rich")
        self.assertEqual(len(got), 2)
        with self.assertRaises(ValueError):
            U.build_matrix(widths="999")

    def test_names_roundtrip_and_unique(self):
        shots = U.build_matrix()
        names = [U.shot_name(s) for s in shots]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(U.parse_name(names[5]), shots[5])
        self.assertIsNone(U.parse_name("random.webp"))

    def test_zoom_80_widens_the_css_page_but_keeps_image_width(self):
        v = U.viewport(1440, 80, 1000)
        self.assertEqual((v["width"], v["height"]), (1800, 1250))
        self.assertAlmostEqual(v["width"] * v["deviceScaleFactor"], 1440)
        self.assertEqual(U.viewport(1280, 100, 900)["width"], 1280)


class IndexTest(unittest.TestCase):
    def test_index_lists_every_shot_and_total(self):
        rows = [{"state": "rich", "screen": "home", "theme": "dark", "width": 1440, "zoom": 100, "file": "a.webp", "bytes": 2048, "height": 900, "cut": False},
                {"state": "rich", "screen": "storyboard", "theme": "dark", "width": 1440, "zoom": 100, "file": "b.webp", "bytes": 4096, "height": 3000, "cut": True}]
        md = U.index_markdown("2026-10-02", rows, 6144, ["ghi chú"])
        self.assertIn("(a.webp)", md)
        self.assertIn("(b.webp)", md)
        self.assertIn("⚠ cắt", md)
        self.assertIn("2 ảnh", md)
        self.assertIn("ghi chú", md)


class SampleDataTest(unittest.TestCase):
    def test_sample_data_has_states_long_names_and_30_scenes(self):
        with tempfile.TemporaryDirectory() as d:
            res = U.build_sample_data(os.path.join(d, "x"), "rich", n_projects=12, images=False)
            self.assertEqual(len(res["projects"]), 12)
            self.assertEqual(res["projects"][0][1], U.LONG_NAME)
            c = sqlite3.connect(res["db"])
            self.assertEqual(c.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (res["projects"][0][0],)).fetchone()[0], 30)
            states = {r[0] for r in c.execute("SELECT autopilot_state FROM projects")}
            self.assertTrue({"running", "error", "waiting"} <= states)
            self.assertTrue(any(os.path.exists(os.path.join(res["data"], str(pid), "output", "FINAL_VIDEO.mp4")) for pid, _n, k in res["projects"] if k == "done"))
            c.close()

    def test_primary_empty_has_no_scenes(self):
        with tempfile.TemporaryDirectory() as d:
            res = U.build_sample_data(os.path.join(d, "e"), "empty", n_projects=3, images=False)
            c = sqlite3.connect(res["db"])
            self.assertEqual(c.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (res["projects"][0][0],)).fetchone()[0], 0)
            c.close()


class FontTest(unittest.TestCase):
    FILES = ("inter-latin-wght-normal.woff2", "inter-latin-ext-wght-normal.woff2", "inter-vietnamese-wght-normal.woff2", "LICENSE")

    def test_font_files_present_license_and_served_copy_identical(self):
        for f in self.FILES:
            a, b = os.path.join(ROOT, "assets", "fonts", f), os.path.join(ROOT, "dashboard", "static", "fonts", f)
            self.assertTrue(os.path.exists(a), a)
            with open(a, "rb") as x, open(b, "rb") as y:
                self.assertEqual(x.read(), y.read(), f"{f}: bản phục vụ khác bản gốc assets/fonts")
        with open(os.path.join(ROOT, "assets", "fonts", self.FILES[0]), "rb") as fh:
            self.assertEqual(fh.read(4), b"wOF2")

    def test_theme_declares_font_face_with_swap_and_config_enables_static(self):
        with open(os.path.join(ROOT, "dashboard", "design", "theme.css"), encoding="utf-8") as f:
            css = f.read()
        self.assertEqual(css.count("@font-face"), 3)
        self.assertEqual(css.count("font-display: swap"), 3)
        for f in self.FILES[:3]:
            self.assertIn("/app/static/fonts/" + f, css)
        with open(os.path.join(ROOT, ".streamlit", "config.toml"), encoding="utf-8") as f:
            self.assertRegex(f.read(), r"enableStaticServing\s*=\s*true")


if __name__ == "__main__":
    unittest.main()
