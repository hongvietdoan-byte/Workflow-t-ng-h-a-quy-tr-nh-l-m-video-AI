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

    def test_experimental_preset_is_everything_and_the_removed_three_stay_off(self):
        with self._clean_env():
            features.save_settings(preset="experimental")
            self.assertTrue(features.on(self.unverified))
            for h in ("setcheck_autofix", "layout_to_model", "chain_previous_auto"):   # S14.9: removed from the code, not just held off
                self.assertNotIn(h, features.FEATURES)
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

    def test_a_flag_that_needs_another_says_it_has_no_effect_alone(self):
        """S14.4 C1b (04/10): dialogue_take does nothing without lip_sync (runner checks lipsync.enabled()) — it looked ON."""
        features.save_settings(flags={"dialogue_take": True, "lip_sync": False})
        self.assertEqual(features.unmet("dialogue_take"), ["lip_sync"])
        self.assertIn("lip_sync", features.why_state("dialogue_take"))
        self.assertIn("không có tác dụng", features.why_state("dialogue_take"))
        self.assertIn("dialogue_take", features.unmet_all())
        features.save_settings(flags={"lip_sync": True})
        self.assertEqual(features.unmet("dialogue_take"), [])
        self.assertNotIn("không có tác dụng", features.why_state("dialogue_take"))
        for name, needs in features.REQUIRES.items():                      # every name is a real flag
            self.assertIn(name, features.FEATURES)
            self.assertTrue(all(n in features.FEATURES for n in needs))


class TraineeModeTests(unittest.TestCase):
    """B1 học việc (08/10, docs/KE_HOACH_HOC_VIEC_2026-10-08.md mục 1): on / trainee / off, thứ tự ưu tiên, `1` → học việc."""
    SEVEN = ("qc_team", "scene_qc", "scene_establishing", "camera_setups", "continuous_takes", "end_frames", "storyboard_auto_trust")

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "fs.json")
        clean = {"FEATURE_" + k.upper(): "" for k in features.FEATURES}
        self.p = mock.patch.dict(os.environ, {**clean, "FEATURE_SETTINGS_FILE": self.path})
        self.p.start()
        self.addCleanup(self.p.stop)

    def test_the_seven_are_literal_trainee_flags(self):
        self.assertEqual(sorted(features.trainee_list()), sorted(self.SEVEN))
        from devsys.collect import read_features                              # devsys reads FEATURES with ast: must be a literal
        self.assertTrue(all(read_features()[k].get("trainee") is True for k in self.SEVEN))

    def test_env_one_is_trainee_never_on(self):
        for env in ("1", "trainee", "on"):
            with mock.patch.dict(os.environ, {"FEATURE_QC_TEAM": env}):
                self.assertEqual(features.state("qc_team"), "trainee", env)
                self.assertFalse(features.on("qc_team"))
                self.assertTrue(features.shadow("qc_team") and features.active("qc_team"))
                self.assertIn("học việc", features.why_state("qc_team"))
        with mock.patch.dict(os.environ, {"FEATURE_QC_TEAM": "0"}):
            self.assertEqual(features.state("qc_team"), "off")
        self.assertEqual(features.state("qc_team"), "off")                     # default: not verified → off
        with mock.patch.dict(os.environ, {"FEATURE_J_CUT": "1"}):               # a flag without the mode keeps the old rule
            self.assertEqual(features.state("j_cut"), "on")
        with mock.patch.dict(os.environ, {"FEATURE_J_CUT": "trainee"}):
            self.assertEqual(features.state("j_cut"), "off")

    def test_order_screen_then_preset_then_env(self):
        with mock.patch.dict(os.environ, {"FEATURE_SCENE_QC": "1"}):
            features.save_settings(preset="stable")
            self.assertEqual(features.state("scene_qc"), "off")                # stable = only verified → học việc flags off
            features.save_settings(preset="experimental")
            self.assertEqual(features.state("scene_qc"), "trainee")            # experimental never pushes them to on
            features.save_settings(flags={"scene_qc": True})
            self.assertEqual(features.state("scene_qc"), "on")                 # the 🧪 screen wins over everything
            features.save_settings(modes={"scene_qc": "trainee"})
            self.assertEqual(features.state("scene_qc"), "trainee")
            features.save_settings(modes={"scene_qc": "off"})
            self.assertEqual(features.state("scene_qc"), "off")
            features.save_settings(modes={"scene_qc": None})
            self.assertEqual(features.state("scene_qc"), "trainee")            # back to the preset
        with mock.patch.dict(os.environ, {"FEATURE_SCENE_QC": "0"}):
            self.assertEqual(features.state("scene_qc"), "off")                # explicit 0 under experimental still holds
        with mock.patch.dict(os.environ, {"FEATURE_LOCATION_PLATES": "1"}):
            self.assertEqual(features.state("location_plates"), "off")         # removed wins

    def test_modes_never_leak_into_flags(self):
        features.save_settings(modes={"qc_team": "trainee", "end_frames": "on"})
        raw = json.load(open(self.path, encoding="utf-8"))
        self.assertNotIn("qc_team", raw["flags"])                             # old code reads flags with bool(v) → would be ON
        self.assertEqual(raw["modes"], {"qc_team": "trainee"})
        self.assertIs(raw["flags"]["end_frames"], True)
        self.assertTrue(all(isinstance(v, bool) for v in raw["flags"].values()))
        features.save_settings(flags={"qc_team": False})                       # a flags choice replaces the mode
        raw = json.load(open(self.path, encoding="utf-8"))
        self.assertNotIn("modes", raw)
        self.assertEqual(features.state("qc_team"), "off")
        with self.assertRaises(ValueError):
            features.save_settings(modes={"j_cut": "trainee"})                 # no học việc mode for that flag
        with self.assertRaises(ValueError):
            features.save_settings(modes={"qc_team": "maybe"})
        with open(self.path, "w", encoding="utf-8") as f:                       # a hand-edited "trainee" inside flags is NOT trainee
            json.dump({"preset": "custom", "modes": {"j_cut": "trainee", "scene_qc": "trainee"}}, f)
        self.assertEqual(features.state("j_cut"), "off")
        self.assertEqual(features.state("scene_qc"), "trainee")

    def test_on_unverified_and_pending_leave_trainee_out(self):
        with mock.patch.dict(os.environ, {"FEATURE_END_FRAMES": "1", "FEATURE_J_CUT": "1"}):
            self.assertNotIn("end_frames", features.on_unverified())
            self.assertIn("j_cut", features.on_unverified())
            self.assertNotIn("end_frames", features.pending())

    def test_qc_team_needs_scene_qc_by_active(self):
        features.save_settings(modes={"qc_team": "trainee"})
        self.assertEqual(features.unmet("qc_team"), ["scene_qc"])
        features.save_settings(modes={"scene_qc": "trainee"})
        self.assertEqual(features.unmet("qc_team"), [])

    def test_devsys_flags_state_has_the_mode(self):
        from devsys import collect
        rows = {r["name"]: r for r in collect.flags_state(collect.ROOT, {"areas": []}, files=[])}
        self.assertTrue(rows["qc_team"]["trainee"])
        self.assertIn(rows["qc_team"]["mode"], features.MODES)
        self.assertFalse(rows["j_cut"]["trainee"])
        self.assertIn(rows["j_cut"]["mode"], ("on", "off"))

    def test_module_helpers_follow_state(self):
        from core import end_frames, qc_scene, qc_team, scene_establish
        features.save_settings(modes={"scene_qc": "trainee", "qc_team": "trainee", "scene_establishing": "trainee",
                                      "end_frames": "trainee"})
        for m in (end_frames, qc_scene, qc_team, scene_establish):
            self.assertFalse(m.enabled(), m.__name__)
            self.assertTrue(m.shadow() and m.active(), m.__name__)
        features.save_settings(modes={"scene_qc": "on"})
        self.assertTrue(qc_scene.enabled() and qc_scene.active() and not qc_scene.shadow())


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
