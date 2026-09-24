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
        self.assertFalse(features.on("layout_to_model"))
        self.assertIn("setcheck_autofix", features.pending())
        with mock.patch.dict(os.environ, {"FEATURE_LAYOUT_TO_MODEL": "1"}):
            self.assertTrue(features.on("layout_to_model"))

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
