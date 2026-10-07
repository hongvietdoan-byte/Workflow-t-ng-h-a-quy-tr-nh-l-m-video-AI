"""Thử A+/B: sổ chi, chống gửi trùng, mẫu hết hạn và dữ liệu kết quả hỏng."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core import llm_runner, shots
from core.pipeline import PipelinePaused
from core.providers import ProviderError
from tests.test_v3 import kenta_project, _approve_all_images, _approve_all_motion


class Provider:
    name = "mock_quality"
    def __init__(self):
        self.calls = []
        self.usage = {"is_draft": True, "draft_expired_at": time.time() + 86400, "duration": 4}
    def submit(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return f"seedance:cgt-{len(self.calls)}"
    def submit_final_from_sample(self, external_id):
        self.calls.append(external_id)
        return f"seedance:cgt-{len(self.calls)}"
    def task_usage(self, ext):
        return self.usage
    def status(self, ext):
        return SimpleNamespace(state="succeeded")
    def download(self, ext, dest):
        Path(dest).write_bytes(b"test-result")
        return dest


class QualitySamplesTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = kenta_project()
        self.data = tempfile.mkdtemp()
        self.sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchone()[0]
        self.provider = Provider()
        self.env = mock.patch.dict(os.environ, {"FEATURE_SEEDANCE_SAMPLE_MODE": "1", "FEATURE_SETTINGS_FILE":
                                              os.path.join(self.data, "flags.json")})
        self.env.start(); self.addCleanup(self.env.stop)
        image = str(Path(self.data)/"approved.png")
        Path(image).write_bytes(b"approved-image")
        self.plan = {"scene_id": self.sid, "seconds": 4, "aspect": "9:16", "prompt": "accepted motion",
                     "pictures": [], "image": image, "reference_only": False}

    def module(self):
        from core import quality_samples
        return quality_samples

    def send(self, kind, **kw):
        q = self.module()
        with mock.patch.object(q, "plan", return_value=self.plan):
            return q.send(self.p, self.pid, self.sid, kind, self.provider, self.data, **kw)

    def test_explicit_off_switch_blocks_before_network(self):
        with mock.patch.dict(os.environ, {"FEATURE_SEEDANCE_SAMPLE_MODE": "0"}):
            with self.assertRaises(ValueError):
                self.send("draft")
        self.assertEqual(self.provider.calls, [])

    def test_each_kind_sends_once_and_ledger_has_separate_resolution(self):
        for kind in ("direct", "draft"):
            first = self.send(kind)
            self.assertEqual(self.send(kind)["external_id"], first["external_id"])
        self.assertEqual(len(self.provider.calls), 2)
        tiers = [r[0] for r in self.p.conn.execute("SELECT tier FROM usage_events WHERE stage='quality_sample' ORDER BY id")]
        self.assertEqual(tiers, ["720p", "480p"])
        self.assertEqual([call[1]["draft"] for call in self.provider.calls], [False, True])

    def test_final_waits_for_successful_draft_and_refuses_expiry_or_missing_metadata(self):
        q = self.module()
        with self.assertRaises(ValueError):
            self.send("final")
        self.send("draft")
        with self.assertRaises(ValueError):
            self.send("final")
        q.refresh(self.p, self.pid, self.provider, self.data)
        for meta in (None, {"is_draft": False}, {"is_draft": True, "draft_expired_at": time.time()-1, "duration": 4}):
            self.provider.usage = meta
            with self.assertRaises(ValueError):
                self.send("final")
        self.assertEqual(len(self.provider.calls), 1)

    def test_final_is_separately_billed_and_does_not_touch_pipeline_jobs(self):
        q = self.module()
        before = list(self.p.conn.execute("SELECT id,state FROM jobs"))
        draft = self.send("draft")
        q.refresh(self.p, self.pid, self.provider, self.data)
        final = self.send("final")
        self.assertEqual(self.provider.calls[-1], draft["external_id"])
        self.assertEqual(self.send("final")["external_id"], final["external_id"])
        tiers = [r[0] for r in self.p.conn.execute("SELECT tier FROM usage_events WHERE stage='quality_sample' ORDER BY id")]
        self.assertEqual(tiers, ["480p", "1080p"])
        self.assertEqual(before, list(self.p.conn.execute("SELECT id,state FROM jobs")))

    def test_pair_cap_and_paused_project_block_before_network(self):
        with self.assertRaises(ValueError):
            self.send("direct", max_usd=0.01)
        self.p.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (self.pid,)); self.p.conn.commit()
        with self.assertRaises(PipelinePaused):
            self.send("draft")
        self.assertEqual(self.provider.calls, [])

    def test_broken_state_never_becomes_empty_or_sends_again(self):
        q = self.module()
        self.send("draft")
        path = Path(self.data)/str(self.pid)/"experiments"/"quality_samples.json"
        path.write_text("broken json", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.send("draft")
        self.assertEqual(len(self.provider.calls), 1)

    def test_uncertain_send_is_retained_and_never_retried_automatically(self):
        with mock.patch.object(self.provider, "submit", side_effect=ProviderError("connection lost", code="network_error")) as fn:
            with self.assertRaises(ProviderError):
                self.send("draft")
            self.send("draft")
            self.assertEqual(fn.call_count, 1)
        self.assertEqual(self.module().load(self.data, self.pid)[0]["state"], "uncertain")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='quality_sample'").fetchone()[0],1)

    def test_plan_uses_approved_inputs_and_place_mapping_with_absolute_data_root(self):
        from PIL import Image
        q = self.module()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        sid = shots.shots_of(self.p, self.pid)[0]["id"]
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=4 WHERE scene_id=?", (sid,)); self.p.conn.commit()
        image = shots.approved_image_path(self.p.conn, self.data, self.pid, sid)
        Image.new("RGB", (360,640)).save(image)
        plate = str(Path(self.data)/"place.png"); Image.new("RGB", (360,640)).save(plate)
        with mock.patch.dict(os.environ, {"FEATURE_PLACE_RENDER_REFS":"1"}), \
                mock.patch("core.seedance_refs.uses_refs", return_value=True), \
                mock.patch("core.place_refs.shot_ref", return_value={"path":plate}), \
                mock.patch("core.seedance_refs.identity_pictures", return_value=[]):
            candidate_ids = [r["id"] for r in q.candidates(self.p,self.pid,self.data)]
            self.assertIn(sid,candidate_ids)
            plan = q.plan(self.p,self.pid,sid,self.data)
            self.assertEqual(plan["pictures"], [image,plate])
            self.assertIn("Image 2 is the PLACE render for Shot 1",plan["prompt"])
            self.assertEqual(plan["seconds"],4)
        with self.assertRaises(ValueError):
            q.plan(self.p,self.pid,99999,self.data)

    def test_changed_prompt_between_a_and_b_is_rejected_before_network(self):
        self.send("direct")
        self.plan["prompt"] = "changed motion"
        with self.assertRaises(ValueError):
            self.send("draft")
        self.assertEqual(len(self.provider.calls),1)

    def test_dashboard_shows_estimates_and_waits_for_draft_before_final_button(self):
        from streamlit.testing.v1 import AppTest
        q = self.module()
        source = """
from types import SimpleNamespace
from tests.test_v3 import kenta_project
from dashboard.steps.step4 import quality_samples_panel
p,pid=kenta_project()
quality_samples_panel(p,pid,SimpleNamespace(provider=None))
"""
        with mock.patch.object(q,"candidates",return_value=[{"id":1,"idx":6}]), \
                mock.patch.object(q,"load",return_value=[]):
            app=AppTest.from_string(source).run(timeout=30)
            self.assertEqual(len(app.exception),0)
            labels=[b.label for b in app.button]
            self.assertTrue(any("720p" in x and "$" in x for x in labels))
            self.assertTrue(any("480p" in x and "$" in x for x in labels))
            self.assertFalse(any("1080p" in x for x in labels))
        entries=[{"scene_id":1,"kind":"draft","state":"succeeded","usd":0.415}]
        with mock.patch.object(q,"candidates",return_value=[{"id":1,"idx":6}]), \
                mock.patch.object(q,"load",return_value=entries):
            app=AppTest.from_string(source).run(timeout=30)
            self.assertEqual(len(app.exception),0)
            self.assertTrue(any("1080p" in b.label for b in app.button))
