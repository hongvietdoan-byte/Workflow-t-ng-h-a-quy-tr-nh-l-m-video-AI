"""Workflow effectiveness report: 5 figures from what the pipeline already records."""
import os
import shutil
import tempfile
import unittest

from core import effectiveness, llm_io
from core.db import connect
from core.pipeline import Pipeline

PRICING = {"currency": "usd", "per_image": {"img-model": 0.05}, "per_video_second": {"vid-model:pro": 0.1},
           "per_video_clip": {}, "per_audio": {}}


class EffectivenessTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("eff")
        self.sids = [self.p.create_scene(self.pid, i, f"S{i}") for i in (1, 2)]

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def picture(self, sid, scores, person):
        """An image job that ran, got QC scores, and was decided by a person. Returns the job id (and the retry's, if rejected)."""
        jid = self.p.create_job(sid, "image_gen")
        self.p.start(jid)
        self.p.succeed(jid)
        self.p.apply_qc(jid, scores)                          # human_qc: a suggestion only, the picture waits for the person
        if person == "approve":
            self.p.approve(jid)
        else:
            self.p.reject(jid)
        return jid

    def test_an_empty_project_says_not_enough_data_instead_of_zero(self):
        r = effectiveness.report(self.conn, self.pid, PRICING)
        self.assertIsNone(r["wall_min_per_sec"])
        self.assertIsNone(r["image"]["first_pass"])
        self.assertIsNone(r["qc"]["agreement"])
        self.assertIn("chưa đủ dữ liệu", "\n".join(effectiveness.summary_lines(r)))

    def test_first_pass_agreement_touches_and_cost_per_second(self):
        good = {k: 0.9 for k in ("a", "b")}
        bad = {k: 0.6 for k in ("a", "b")}                # under the 0.85 bar, above the 0.5 auto-reject floor
        self.picture(self.sids[0], good, "approve")          # scene 1: accepted at once, AI agreed
        self.picture(self.sids[1], good, "reject")           # scene 2: AI said pass, the person rejected -> a retry is queued
        retry = self.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND state='queued'", (self.sids[1],)).fetchone()["id"]
        self.p.start(retry)
        self.p.succeed(retry)
        self.p.apply_qc(retry, bad)
        self.p.approve(retry)                                # AI said fail, the person approved
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "m", "duration_sec": 5},
                                                                  {"idx": 2, "motion_prompt": "m", "duration_sec": 5}]})
        for sid in self.sids:
            vid = self.p.create_job(sid, "video_gen")
            self.p.start(vid)
            self.p.succeed(vid)
            self.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                              " VALUES (?,?,?,?,?,?,?,?,datetime('now'))", (vid, self.pid, "video", "clipai", "vid-model", "pro", 5, "second"))
        self.conn.commit()
        r = effectiveness.report(self.conn, self.pid, PRICING)
        self.assertEqual(r["video_seconds"], 10)
        self.assertEqual(r["image"]["first_pass"], 0.5)
        self.assertEqual(r["image"]["tries_per_scene"], 1.5)
        self.assertEqual(r["video"]["first_pass"], 1.0)
        self.assertEqual(r["qc"]["pairs"], 3)
        self.assertAlmostEqual(r["qc"]["agreement"], 1 / 3)
        self.assertEqual((r["qc"]["ai_too_lenient"], r["qc"]["ai_too_strict"]), (1, 1))
        self.assertAlmostEqual(r["cost_per_sec"], 0.1)
        self.assertEqual(r["touches"], 3)                    # approve, reject, approve
        self.assertEqual(r["touches_per_scene"], 1.5)
        self.assertIsNotNone(r["wall_min_per_sec"])
        lines = effectiveness.summary_lines(r, manual_min_per_sec=30)
        self.assertTrue(any(line.startswith("So với làm tay") for line in lines) or r["wall_min_per_sec"] == 0)


if __name__ == "__main__":
    unittest.main()
