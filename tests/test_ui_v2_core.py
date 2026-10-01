"""S13 nhánh A: token giao diện v2 đạt tương phản đã hứa, thành phần escape đúng, cờ ui_v2 nạp lớp thiết kế, trang G1 dựng được."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from dashboard.design import components as D
from dashboard.design import tokens

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class TokenTests(unittest.TestCase):
    def test_promised_contrast_holds_in_both_themes(self):
        for theme in ("dark", "light"):
            for name, fg, bg, need in tokens.promised_pairs(theme):
                self.assertGreaterEqual(tokens.contrast_ratio(fg, bg), need, f"{theme}: {name} {fg} on {bg}")

    def test_ratio_function_matches_known_values(self):
        self.assertAlmostEqual(tokens.contrast_ratio("#000000", "#FFFFFF"), 21.0, places=1)
        self.assertAlmostEqual(tokens.contrast_ratio("#777777", "#FFFFFF"), 4.48, places=1)

    def test_css_vars_cover_every_token_and_no_size_below_12(self):
        css = tokens.css_vars("dark")
        for k in tokens.DARK:
            self.assertIn(f"--{k}:", css)
        self.assertIn("--grad-primary:", css)
        self.assertTrue(all(float(v.replace("px", "")) >= 12 for v in tokens.TYPE.values()))

    def test_theme_css_uses_only_stable_hooks(self):
        path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "design", "theme.css")
        css = open(path, encoding="utf-8").read()
        self.assertNotIn("st-emotion-cache", css)                 # emotion class names change with every Streamlit version
        self.assertNotRegex(css, r"font-size:\s*(\d|1[01])(\.\d+)?px")      # nothing under 12 px


class ComponentTests(unittest.TestCase):
    def test_everything_user_supplied_is_escaped(self):
        self.assertNotIn("<script", D.pill("<script>x</script>", "ok"))
        self.assertNotIn("<img", D.hero_html("<img src=x>", "<b>", [("<i>", "ok")]))
        self.assertIn("&lt;", D.empty_state("<b>", "<i>"))

    def test_meter_colour_follows_completion_and_inverts_for_money(self):
        self.assertIn("var(--bad)", D.meter(0.1))
        self.assertIn("var(--warn)", D.meter(0.5))
        self.assertIn("var(--info)", D.meter(0.8))
        self.assertIn("var(--ok)", D.meter(1.0))
        self.assertIn("var(--ok)", D.meter(0.3, invert=True))
        self.assertIn("var(--bad)", D.meter(0.95, invert=True))
        self.assertIn("100%", D.meter(7))                          # clamped

    def test_frame_states_are_the_fixed_vocabulary(self):
        for key, label in (("review", "Cần duyệt"), ("approved", "Đã duyệt"), ("rejected", "Từ chối"), ("failed", "Lỗi")):
            self.assertIn(label, D.frame_state_pill(key))
        self.assertIn("v2-run", D.frame_state_pill("working"))      # only a running job pulses


class FlagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        self.env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                                                "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku")})
        self.env.start()
        self.addCleanup(self.env.stop)
        from core.db import connect
        from core.pipeline import Pipeline
        Pipeline(connect(self.db)).create_project("v2")

    def test_flag_is_off_by_default_and_loads_nothing_new(self):
        at = AppTest.from_file(APP, default_timeout=60).run()
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(any("--grad-primary" in (m.value or "") for m in at.markdown))

    def test_flag_on_injects_the_design_layer_and_the_g1_slice_renders(self):
        with mock.patch.dict(os.environ, {"FEATURE_UI_V2": "1"}):
            at = AppTest.from_file(APP, default_timeout=90)
            at.query_params["step"] = "design"
            at.run()
            self.assertFalse(at.exception, at.exception)
            self.assertTrue(any("--grad-primary" in (m.value or "") for m in at.markdown))      # tokens injected
            self.assertTrue(any(b.key == "v2d_ok_3" for b in at.button))                         # a frame card with real widgets
            self.assertTrue(any("G1" in m.value for m in at.markdown))


if __name__ == "__main__":
    unittest.main()


class InfoTests(unittest.TestCase):
    def test_info_popover_and_summary_line_render_with_the_details_inside(self):
        def app():
            import streamlit as st
            from dashboard.design import components as D
            D.line("<b>3 khung cần duyệt</b>", "Chi tiết dài\n\n- khung 3\n- khung 5", key="demo")
            with D.info("other"):
                st.markdown("nội dung phụ")
        at = AppTest.from_function(app, default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)
        labels = [x.proto.popover.label for x in at.get("popover")]
        self.assertEqual(labels.count("ⓘ"), 2)                      # the glyph is always visible text, never hover-only
        self.assertTrue(any("khung cần duyệt" in m.value for m in at.markdown))
        self.assertTrue(any("khung 5" in m.value for m in at.markdown))         # the details are in the popover, not dropped
