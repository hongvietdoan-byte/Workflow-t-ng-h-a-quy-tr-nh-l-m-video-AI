"""01/10 đợt 2: 🧪 Tính năng thử — preset + chọn từng cờ trên màn hình (thay cho sửa dashboard.env)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import features


class FeatureSettingsTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "fs.json")
        self.p = mock.patch.dict(os.environ, {"FEATURE_SETTINGS_FILE": self.path})
        self.p.start()
        for k in list(os.environ):
            if k.startswith("FEATURE_") and k != "FEATURE_SETTINGS_FILE":
                self.p.new.pop(k, None) if False else None
        self.verified = next(k for k, v in features.FEATURES.items() if v["verified"])
        self.unverified = next(k for k, v in features.FEATURES.items() if not v["verified"] and k not in features.HARMFUL)

    def tearDown(self):
        self.p.stop()

    def _clean_env(self):
        return mock.patch.dict(os.environ, {"FEATURE_" + k.upper(): "" for k in features.FEATURES})

    def test_default_is_the_old_rule(self):
        with self._clean_env():
            self.assertEqual(features.settings()["preset"], "custom")
            self.assertTrue(features.on(self.verified))
            self.assertFalse(features.on(self.unverified))
            with mock.patch.dict(os.environ, {"FEATURE_" + self.unverified.upper(): "1"}):
                self.assertTrue(features.on(self.unverified))

    def test_stable_preset_ignores_unverified_env_flags(self):
        with self._clean_env(), mock.patch.dict(os.environ, {"FEATURE_" + self.unverified.upper(): "1"}):
            features.save_settings(preset="stable")
            self.assertFalse(features.on(self.unverified))
            self.assertTrue(features.on(self.verified))

    def test_experimental_preset_is_everything_but_the_harmful_three(self):
        with self._clean_env():
            features.save_settings(preset="experimental")
            self.assertTrue(features.on(self.unverified))
            for h in features.HARMFUL:
                self.assertFalse(features.on(h), h)
            with mock.patch.dict(os.environ, {"FEATURE_" + self.unverified.upper(): "0"}):
                self.assertFalse(features.on(self.unverified))            # an explicit off in the environment still holds

    def test_a_single_choice_wins_and_can_be_removed(self):
        with self._clean_env():
            features.save_settings(preset="stable", flags={self.unverified: True, self.verified: False})
            self.assertTrue(features.on(self.unverified))
            self.assertFalse(features.on(self.verified))
            self.assertEqual(features.why_state(self.unverified), "bạn chọn trên màn này")
            features.save_settings(flags={self.unverified: None, self.verified: None})
            self.assertFalse(features.on(self.unverified))
            self.assertTrue(features.on(self.verified))

    def test_bad_input_and_broken_file(self):
        with self.assertRaises(ValueError):
            features.save_settings(preset="nope")
        with self.assertRaises(ValueError):
            features.save_settings(flags={"khong_co": True})
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{broken")
        self.assertEqual(features.settings()["preset"], "custom")           # an unreadable file never switches anything

    def test_file_is_json(self):
        features.save_settings(preset="stable")
        self.assertEqual(json.load(open(self.path, encoding="utf-8"))["preset"], "stable")


if __name__ == "__main__":
    unittest.main()


class FeatureScreenTests(unittest.TestCase):
    """The 🧪 dialog, the 💵 card and the 3-group gear render and work (AppTest)."""
    def setUp(self):
        from core.db import connect as _c
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        self.env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": tempfile.mkdtemp(),
                                                "FEATURE_SETTINGS_FILE": os.path.join(tempfile.mkdtemp(), "fs.json")})
        self.env.start()
        from core.pipeline import Pipeline
        self.p = Pipeline(_c(self.db))
        self.pid = self.p.create_project("Dự án thử giao diện")

    def tearDown(self):
        self.env.stop()

    def test_money_card_gear_groups_and_features_dialog(self):
        from streamlit.testing.v1 import AppTest
        app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
        at = AppTest.from_file(app, default_timeout=60)
        at.session_state["global_pid"] = self.pid
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(any(b.key == "settings_features" for b in at.button))
        self.assertTrue(any(b.key == "mc_budget" for b in at.button))
        self.assertFalse(any(b.key in ("settings_pricing", "settings_budget") for b in at.button))     # moved into the 💵 card
        at.button(key="settings_features").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(any(k.startswith("feat_") for k in (t.key for t in at.toggle)))
        at.radio(key="feat_preset").set_value("stable").run()
        self.assertFalse(at.exception, at.exception)
        from core import features
        self.assertEqual(features.settings()["preset"], "stable")
