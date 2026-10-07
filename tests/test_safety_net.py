"""GĐ-D (docs/KE_HOACH_TONG_2026-09-24.md): no silent failure — library pictures resolve from any working folder (A1), the Director
never describes a known character blind, and features that failed in the real GĐ6 run stay off until a real test closes them."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import assets, autopilot, features, llm_runner, storyboard_gate
from core.db import connect
from core.pipeline import Pipeline


class PathTests(unittest.TestCase):
    def test_a_stored_relative_path_is_found_from_another_working_folder(self):
        rel = os.path.join("tests", os.path.basename(__file__))
        here = os.getcwd()
        os.chdir(tempfile.mkdtemp())
        try:
            self.assertFalse(os.path.exists(rel))
            self.assertTrue(os.path.exists(assets.resolve(rel)))
        finally:
            os.chdir(here)
        self.assertIsNone(assets.resolve(None))

    def test_missing_library_files_are_listed(self):
        conn = connect(":memory:")
        aid = assets.create(conn, "ff", "character", "KELLY")
        conn.execute("INSERT INTO asset_images (asset_id, path, sort) VALUES (?, 'data/assets/none/gone.png', 0)", (aid,))
        conn.commit()
        self.assertEqual([m["asset"] for m in assets.missing_files(conn)], ["KELLY"])


class DirectorBlindTests(unittest.TestCase):
    def test_the_director_is_not_called_when_a_known_characters_pictures_cannot_be_read(self):
        conn = connect(":memory:")
        p = Pipeline(conn)
        pid = p.create_project("P")
        p.set_script_text(pid, "CẢNH 1. NGÀY\nKelly chạy.")
        aid = assets.create(conn, "ff", "character", "KELLY")
        conn.execute("INSERT INTO asset_images (asset_id, path, sort) VALUES (?, 'data/assets/none/gone.png', 0)", (aid,))
        conn.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, aid))
        conn.commit()
        calls = []

        class Spy(llm_runner.MockLlm):
            def complete(self, prompt, images=()):
                calls.append(1)
                return super().complete(prompt, images)

        with self.assertRaises(llm_runner.LlmError) as err:
            llm_runner.run_director(p, pid, Spy())
        self.assertEqual(err.exception.code, "missing_reference")
        self.assertIn("KELLY", str(err.exception))
        self.assertEqual(calls, [])                                   # nothing paid


class FeatureFlagTests(unittest.TestCase):
    def test_unverified_features_are_off_and_can_be_switched_on_for_a_trial(self):
        with mock.patch.dict(os.environ, {"FEATURE_SETTINGS_FILE": os.path.join(tempfile.mkdtemp(), "none.json")}):
            os.environ.pop("FEATURE_J_CUT", None)
            self.assertFalse(features.FEATURES["j_cut"]["verified"])
            self.assertFalse(features.on("j_cut"))
            self.assertIn("j_cut", features.pending())
            with mock.patch.dict(os.environ, {"FEATURE_J_CUT": "1"}):
                self.assertTrue(features.on("j_cut"))


class RemovedFlagTests(unittest.TestCase):
    """S14.9 (Gói L, 06/10): 5 flags taken out of the code. An old FEATURE_<NAME>=1 line or an old choice saved in
    data/feature_settings.json never breaks anything: it is ignored (always off, as before) and said in 🧪."""
    GONE = ("layout_to_model", "chain_previous_auto", "setcheck_autofix", "location_plates")

    def setUp(self):
        self.file = os.path.join(tempfile.mkdtemp(), "feature_settings.json")
        env = mock.patch.dict(os.environ, {"FEATURE_SETTINGS_FILE": self.file})
        env.start()
        self.addCleanup(env.stop)

    def test_the_flags_are_gone_and_always_off(self):
        self.assertEqual(set(self.GONE), set(features.REMOVED))
        self.assertEqual(features.HARMFUL, ())
        for name in self.GONE:
            self.assertNotIn(name, features.FEATURES)
            with mock.patch.dict(os.environ, {"FEATURE_" + name.upper(): "1"}):
                self.assertFalse(features.on(name), name)
                self.assertIn(name, features.removed_in_use())
            self.assertNotIn(name, features.pending())
        self.assertEqual(features.removed_in_use(), {})                # an "=0" / no line says nothing

    def test_an_old_settings_file_naming_them_still_loads(self):
        import json
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump({"preset": "experimental", "flags": {"location_plates": True, "setcheck_autofix": True, "j_cut": True}}, f)
        s = features.settings()                                           # no error
        self.assertEqual((s["preset"], s["flags"]), ("experimental", {"j_cut": True}))
        self.assertFalse(features.on("location_plates"))
        self.assertFalse(features.on("setcheck_autofix"))
        self.assertTrue(features.on("j_cut"))
        said = features.removed_in_use()
        self.assertEqual(sorted(said), ["location_plates", "setcheck_autofix"])
        self.assertIn("S14.9", said["location_plates"])
        features.save_settings(flags={"layout_to_model": True, "j_cut": None})   # an old page naming a removed flag: ignored
        with open(self.file, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved, {"preset": "experimental", "flags": {}})       # the stale keys are dropped on save
        self.assertEqual(features.removed_in_use(), {})
        with self.assertRaises(ValueError):
            features.save_settings(flags={"no_such_flag": True})              # an unknown name is still an error

    def test_the_whole_set_check_only_reports_and_the_storyboard_shows_it(self):
        from tests.test_v3 import _approve_all_images, kenta_project
        p, pid = kenta_project()
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        _approve_all_images(p, pid, data)
        before = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", (pid,)).fetchone()[0]
        ctx = autopilot.Context(data_dir=data, image_runner=None, video_runner=None, llm=llm_runner.MockLlm())
        issue = {"ok": False, "issues": [{"idx": 2, "problem": "Kenta mặc áo khác các shot còn lại", "fix": "keep Kenta's jacket"}]}
        with mock.patch("core.claude_tasks.set_consistency", side_effect=lambda *a, **k: self._write(data, pid, issue)):
            autopilot._setcheck_phase(p, pid, ctx)
        after = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen'", (pid,)).fetchone()[0]
        self.assertEqual(after, before)                               # no paid redo
        sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=2", (pid,)).fetchone()[0]
        self.assertTrue(any("QC đồng bộ" in f for f in storyboard_gate.flags(p, pid, data)[sid]))

    @staticmethod
    def _write(data, pid, obj):
        folder = os.path.join(data, str(pid), "qc_set")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "result.json"), "w", encoding="utf-8") as f:
            json.dump(obj, f)
        return obj


if __name__ == "__main__":
    unittest.main()
