"""S14.10 (Gói F1): devsys đo đúng — S1 cờ theo đúng luật core.features.on(), S2 bằng chứng test::Lớp::tên kiểm bằng ast, S3 nhập điểm
đối chiếu dấu vân tay của bản xuất, S11 dòng TODO chung nhiều khu vực chia điểm, S15 trích dẫn chạy thật phải là dòng có dấu hiệu chạy thật;
Đợt 6b hiệu quả vận hành; thang v2.1."""
import json
import os
import unittest
from unittest import mock

from devsys import collect
from tests import test_devsys as base
from tests.test_devsys import _mini_repo, _write


def tearDownModule():
    base.tearDownModule()


def _clean_env():
    """No FEATURE_* / FEATURE_SETTINGS_FILE from the machine running the tests."""
    return {k: v for k, v in os.environ.items() if not k.startswith("FEATURE_")}


class FlagsStateTests(unittest.TestCase):
    """S1: devsys must say a flag is ON exactly when the Dashboard would (core.features.on): the 🧪 screen choice and preset in
    data/feature_settings.json of the measured repo, then FEATURE_<NAME> from the environment / dashboard.env."""

    def setUp(self):
        self.root = _mini_repo()
        self.cfg = collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))

    def state(self, name):
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            return {f["name"]: f for f in collect.flags_state(self.root, self.cfg)}[name]

    def test_the_screen_choice_in_feature_settings_wins(self):
        _write(self.root, "data/feature_settings.json", json.dumps({"preset": "custom", "flags": {"lip_sync": True}}))
        f = self.state("lip_sync")
        self.assertTrue(f["on"], "chọn bật trên màn 🧪 (data/feature_settings.json) → Dashboard bật")
        self.assertIn("màn", f["on_why"])

    def test_the_stable_preset_turns_an_unverified_flag_off_even_with_dashboard_env(self):
        _write(self.root, "dashboard.env", "FEATURE_LIP_SYNC=1\n")
        self.assertTrue(self.state("lip_sync")["on"])                       # custom preset: dashboard.env decides
        _write(self.root, "data/feature_settings.json", json.dumps({"preset": "stable", "flags": {}}))
        f = self.state("lip_sync")
        self.assertFalse(f["on"], "preset Ổn định: cờ chưa thử thật luôn tắt, dashboard.env không bật được")
        self.assertEqual(f["env_source"], "dashboard.env")                  # where the env value came from is still shown

    def test_module_constants_named_flag_are_found_but_not_numbers(self):
        _write(self.root, "core/hero.py", 'FLAG = "lip_sync"\nCLAUDE_FLAG = "lip_sync"\nDARK_FLAG = 0.20\n')
        sites = self.state("lip_sync")["sites"]
        self.assertIn("core/hero.py:1", sites)
        self.assertIn("core/hero.py:2", sites)
        self.assertNotIn("core/hero.py:3", sites)

    def test_a_repo_without_features_on_falls_back_to_the_ast_reading(self):
        _write(self.root, "core/features.py", 'FEATURES = {"lip_sync": {"label": "x", "verified": True, "why": ""}}\n')
        f = self.state("lip_sync")
        self.assertTrue(f["on"])                                             # verified, nothing set → on
        self.assertIn("ast", f["on_why"])


if __name__ == "__main__":
    unittest.main()
