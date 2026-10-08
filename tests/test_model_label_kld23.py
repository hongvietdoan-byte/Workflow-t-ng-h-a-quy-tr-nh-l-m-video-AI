"""KLD-23 (duyệt 08/10): the scene cards and the per-scene model picker say the REAL model and its resolution — on #22 the alias
`seedance` (= Seedance 2.0, not 2.5) was sent twice by mistake (≈ 3,60 USD)."""
import os
import re
import unittest

from core import model_router
from core.db import connect
from core.pipeline import Pipeline

ROOT = os.path.join(os.path.dirname(__file__), "..")


class ModelLabelTests(unittest.TestCase):
    def test_an_alias_says_the_real_model_and_its_resolution(self):
        self.assertEqual(model_router.label("seedance"), "Seedance 2.0 · 720p")
        self.assertEqual(model_router.label("seedance-2.5", "1080p"), "Seedance 2.5 · 1080p")
        self.assertEqual(model_router.label("seedance-fast"), "Seedance 2.0 Fast · 720p")
        self.assertEqual(model_router.label("dreamina-seedance-2-0-260128"), "Seedance 2.0 · 720p")     # a model id, as jobs keep it
        self.assertTrue(model_router.label("kling").startswith("Kling 3.0 Omni · "))
        self.assertIn("model lạ", model_router.label("abc"))

    def test_a_job_says_the_resolution_it_was_billed_at(self):
        p = Pipeline(connect())
        pid = p.create_project("thu", game="FF")
        sid = p.create_scene(pid, 1, "s1")
        jid = p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                             (pid, sid, "video_gen", "succeeded", "t", "t")).lastrowid
        p.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                       " VALUES (?,?,?,?,?,?,?,?,?)", (jid, pid, "video", "clipai", "dreamina-seedance-2-0-260128", "1080p", 5, "s", "t"))
        p.conn.commit()
        self.assertEqual(model_router.job_label(p.conn, jid, "seedance"), "Seedance 2.0 · 1080p")
        self.assertEqual(model_router.job_label(p.conn, 999999, "seedance-fast"), "Seedance 2.0 Fast · 720p")

    def test_the_cards_and_the_picker_use_the_real_name(self):
        step4 = open(os.path.join(ROOT, "dashboard", "steps", "step4.py"), encoding="utf-8").read()
        step3 = open(os.path.join(ROOT, "dashboard", "steps", "step3.py"), encoding="utf-8").read()
        self.assertNotRegex(step4, r"meta_line\(j\[\"model\"\]")                 # the clip card: not the bare alias of the job
        self.assertNotIn("{o['model']}", step4)                                   # the other takes of a shot
        self.assertNotIn("{choice['model']}", step3)                              # the motion card
        self.assertRegex(step4, r"format_func=.*model_router\.label")             # the per-scene picker
        self.assertFalse(re.search(r"api\[a\]\[\"label\"\]", step4))


if __name__ == "__main__":
    unittest.main()
