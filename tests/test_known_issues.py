"""A paused / replaced stage carries its open faults (người dùng 2026-09-27): switching it back on shows them before any spend."""
import os
import unittest

from core import known_issues
from core.db import connect
from core.pipeline import Pipeline


class KnownIssuesTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("k")

    def test_every_stage_has_faults_with_a_fix(self):
        for key, st in known_issues.STAGES.items():
            self.assertTrue(st["label"] and st["status"], key)
            for bug, fix in st["open"]:
                self.assertTrue(bug.strip() and fix.strip(), key)

    def test_the_removed_plates_stage_is_never_said(self):
        # S14.9 (06/10): location_plates was removed from the code — its faults live in docs/TODO_LICH_SU.md, an old env line says nothing
        self.assertNotIn("location_plates", known_issues.STAGES)
        os.environ["FEATURE_LOCATION_PLATES"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_LOCATION_PLATES", None)
        self.assertNotIn("location_plates", [s["key"] for s in known_issues.active(self.p.conn, self.pid)])
        self.assertFalse(any("phông xanh" in line for line in known_issues.warning_lines(self.p.conn, self.pid)))

    def test_per_image_qc_faults_until_the_scene_qc_is_on(self):
        os.environ.pop("FEATURE_SCENE_QC", None)
        self.assertIn("per_image_qc", [s["key"] for s in known_issues.active(self.p.conn, self.pid)])
        os.environ["FEATURE_SCENE_QC"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_SCENE_QC", None)
        self.assertNotIn("per_image_qc", [s["key"] for s in known_issues.active(self.p.conn, self.pid)])

    def test_the_automatic_run_says_them(self):
        from core import autopilot
        autopilot.start(self.p, self.pid)
        codes = [r[0] for r in self.p.conn.execute("SELECT code FROM diag_events WHERE project_id=?", (self.pid,))]
        self.assertIn("known_issues", codes)


if __name__ == "__main__":
    unittest.main()
