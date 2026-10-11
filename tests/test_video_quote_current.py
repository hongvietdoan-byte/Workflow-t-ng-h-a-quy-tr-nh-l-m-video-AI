import json
import os
import unittest
from unittest import mock

from tests.test_cost_route_e1 import Base
from core import cost, lineage, model_router, quality_tier


class CurrentQuoteTests(Base):
    N = 9

    def proven_clip(self, sid):
        from core import sent_package
        image = lineage.approved_image_id(self.p.conn, sid)
        path = os.path.join(self.data, f"image-{sid}.png")
        with open(path, "wb") as f:
            f.write(b"fixture-image")
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (path, image))
        mp = self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        jid = self.p.create_job(sid, "video_gen")
        pkg = json.dumps({"refs": [{"path": path, "sha256": sent_package.sha256_of(path)}]})
        self.p.conn.execute("UPDATE jobs SET state='approved', source_job_id=?, input_hash=?, sent_package=? WHERE id=?",
                            (image, lineage.video_input_hash(mp, "9:16"), pkg, jid))
        return jid, path

    def test_same_image_job_overwritten_or_missing_sha_needs_generation(self):
        jid, path = self.proven_clip(self.s1)
        self.assertFalse(cost.video_need(self.p.conn, self.s1)["needed"])
        with open(path, "wb") as f:
            f.write(b"different-image")
        self.assertTrue(cost.video_need(self.p.conn, self.s1)["needed"])
        self.p.conn.execute("UPDATE jobs SET sent_package=NULL WHERE id=?", (jid,))
        self.assertTrue(cost.video_need(self.p.conn, self.s1)["needed"])

    def test_url_reference_is_unknown_without_probe(self):
        self.p.conn.execute("UPDATE motion_prompts SET ref_video_path='https://example.invalid/ref.mp4' WHERE scene_id=?", (self.s1,))
        with mock.patch("os.path.isfile", return_value=True), mock.patch("core.ffmpeg_studio.probe_duration", return_value=3.5) as probe:
            self.assertEqual(cost.video_reference_seconds(self.p.conn, self.s1)["seconds"], 15.0)
            probe.assert_not_called()

    def test_nine_shots_only_one_matches_current_inputs(self):
        self.proven_clip(self.sids[0])
        for i, sid in enumerate(self.sids[1:], 1):
            jid, _ = self.proven_clip(sid)
            if i % 2:
                self.p.conn.execute("UPDATE jobs SET input_hash=NULL WHERE id=?", (jid,))
                self.assertIn("thiếu bằng chứng", cost.video_need(self.p.conn, sid)["reason"])
            else:
                self.p.conn.execute("UPDATE jobs SET input_hash='old-motion' WHERE id=?", (jid,))
                self.assertIn("motion", cost.video_need(self.p.conn, sid)["reason"])
        self.p.conn.commit()
        for sid in (self.sids[4], self.sids[5], self.sids[7]):
            self.p.conn.execute("UPDATE motion_prompts SET ref_video_path='fake.mp4' WHERE scene_id=?", (sid,))
        with mock.patch.object(quality_tier, "enabled", return_value=False), mock.patch("os.path.isfile", return_value=True), mock.patch("core.ffmpeg_studio.probe_duration", return_value=3.5):
            est = cost.estimate_run(self.p, self.pid)
            rows = model_router.plan(self.p.conn, self.pid)
        self.assertEqual(est["counts"]["clips"], 8)
        self.assertTrue(est["warnings"])
        no_ref = sum(r["cost"] for r in rows[1:] if not r["input_video_s"])
        # Canonical từ adapter, cùng công thức token mà provider sử dụng.
        from core.adapters.clipai import resolve_model
        canonical = resolve_model(rows[4]["model"])[0]
        ref_price = cost.seedance_estimate(canonical, rows[4].get("resolution") or "720p", "9:16", 4, 3.5)
        self.assertEqual(est["videos"], round(no_ref + 3 * ref_price, 2))
        self.assertEqual([r["input_video_s"] for r in rows].count(3.5), 3)

    def test_missing_stamps_and_queued_job_need_generation(self):
        jid = self.p.create_job(self.s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
        self.assertTrue(cost.video_need(self.p.conn, self.s1)["needed"])
        self.p.conn.execute("UPDATE jobs SET state='queued' WHERE id=?", (jid,))
        self.assertTrue(cost.video_need(self.p.conn, self.s1)["needed"])

    def test_reference_seconds_use_local_probe_and_report_unknown(self):
        self.p.conn.execute("UPDATE motion_prompts SET ref_video_path='fake.mp4' WHERE scene_id=?", (self.s1,))
        with mock.patch("os.path.isfile", return_value=True), mock.patch("core.ffmpeg_studio.probe_duration", return_value=3.5):
            self.assertEqual(cost.video_reference_seconds(self.p.conn, self.s1), {"seconds": 3.5, "warnings": []})
        with mock.patch("core.ffmpeg_studio.probe_duration", return_value=None):
            self.assertEqual(cost.video_reference_seconds(self.p.conn, self.s1)["seconds"], 15.0)

    def test_paid_running_is_not_repriced_but_queued_and_retryable_are(self):
        jid = self.p.create_job(self.s1, "video_gen")
        for status, needed in (("queued", True), ("retryable", True), ("running", False)):
            self.p.conn.execute("UPDATE jobs SET state=?, external_id='paid-task' WHERE id=?", (status, jid))
            self.assertEqual(cost.video_need(self.p.conn, self.s1)["needed"], needed)

    def test_new_shots_have_no_old_clip_warning(self):
        with mock.patch.object(quality_tier, "enabled", return_value=False):
            est = cost.estimate_run(self.p, self.pid)
        self.assertEqual(est["warnings"], [])
