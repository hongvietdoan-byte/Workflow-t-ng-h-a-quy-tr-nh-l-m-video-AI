"""S14.14 G-a (người dùng duyệt 05/10): giao diện v2 là MẶC ĐỊNH — không có FEATURE_UI_V2 trong môi trường thì `ui.v2_on()` là True,
và các màn nhóm nhẹ (Kịch bản step1_*, Video step4, 📊 Theo dõi admin, khung app/ui) chỉ còn lớp v2: kể cả FEATURE_UI_V2=0 cũng không
còn đường về giao diện cũ ở đó (nhóm nặng — Storyboard, Bản giao, Nhóm, header — vẫn đọc cờ tới G-b)."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard", "app.py")


def _env_without_ui_flag(tmp: str, **extra) -> dict:
    """os.environ minus FEATURE_UI_V2, a fresh feature-settings file (no 🧪 choice saved) and a temp database."""
    env = {k: v for k, v in os.environ.items() if k != "FEATURE_UI_V2"}
    env.update(FEATURE_SETTINGS_FILE=os.path.join(tmp, "fs.json"), PIPELINE_DB=os.path.join(tmp, "m.sqlite"),
               PIPELINE_DATA=os.path.join(tmp, "projects"), KNOWLEDGE_USER_DIR=os.path.join(tmp, "ku"), LLM_PROVIDER="mock", **extra)
    return env


def _html(at) -> str:
    parts = [m.value or "" for m in at.markdown] + [getattr(getattr(e, "proto", None), "body", "") or "" for e in at.get("html")]
    return "\n".join(x for x in parts if not x.lstrip().startswith("<style"))


class DefaultOnTests(unittest.TestCase):
    def test_flag_absent_means_v2_on(self):
        from dashboard import ui
        tmp = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, _env_without_ui_flag(tmp), clear=True):
            self.assertNotIn("FEATURE_UI_V2", os.environ)
            self.assertTrue(ui.v2_on())

    def test_flag_is_verified_in_the_feature_table(self):
        from core import features
        self.assertTrue(features.FEATURES["ui_v2"]["verified"])
        self.assertIn("S14.14", features.FEATURES["ui_v2"]["why"])


class LightScreensAlwaysV2Tests(unittest.TestCase):
    """AppTest of the real app: the Kịch bản screen (step1) draws the v2 hero/cards with no flag set — and still with FEATURE_UI_V2=0."""

    def _run(self, **extra):
        tmp = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, _env_without_ui_flag(tmp, **extra), clear=True):
            Pipeline(connect(os.environ["PIPELINE_DB"])).create_project("Dự án mặc định")
            at = AppTest.from_file(APP, default_timeout=90).run()
        self.assertFalse(at.exception, at.exception)
        return at

    def test_script_screen_is_v2_without_the_flag(self):
        at = self._run()
        html = _html(at)
        self.assertIn("v2-hero-title", html)                  # step1_v2 hero
        self.assertIn("Dự án mặc định", html)
        self.assertIn("v2-empty", html)                       # card ① empty state
        styles = "\n".join(m.value or "" for m in at.markdown if (m.value or "").lstrip().startswith("<style"))
        self.assertIn("v2-hero", styles)                      # the v2 design CSS (dashboard/design/theme.css) was injected

    def test_script_screen_has_no_old_layout_even_with_flag_off(self):
        at = self._run(FEATURE_UI_V2="0")
        html = _html(at)
        self.assertIn("v2-hero-title", html)                  # G-a: no old composition left in step1
        self.assertNotIn("1b · 🧰 Chuẩn bị", html)            # the old card title of step1.step1()

    def test_monitor_is_v2_even_with_flag_off(self):
        tmp = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, _env_without_ui_flag(tmp, FEATURE_UI_V2="0"), clear=True):
            Pipeline(connect(os.environ["PIPELINE_DB"])).create_project("Theo dõi")
            at = AppTest.from_file(APP, default_timeout=90)
            at.session_state["step"] = "📊 Theo dõi"
            at.run()
        self.assertFalse(at.exception, at.exception)
        labels = [e.label for e in at.expander]
        self.assertTrue(any("Tải theo loại job" in k for k in labels), labels)     # admin._monitor_v2 folds
        self.assertIn("perf_refresh", [b.key for b in at.button])
        self.assertIn("diag_dl", [b.key for b in at.get("download_button")])


if __name__ == "__main__":
    unittest.main()
