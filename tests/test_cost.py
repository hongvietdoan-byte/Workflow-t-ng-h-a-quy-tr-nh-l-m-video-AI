import json
import os
import tempfile
import unittest

from core import cost
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner

PRICING = {"currency": "credits", "confirm_batch_at": 10,
           "per_image": {"img-model": 3},
           "per_video_second": {"kling-v3-omni:pro": 2, "vid:std": None},
           "per_video_clip": {"clip-model:hd": 50}}


def full(pricing=None):
    base = {"currency": "credits", "confirm_batch_at": 10, "per_image": {}, "per_video_second": {},
            "per_video_clip": {}}
    base.update(pricing or {})
    return base


class CostTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", max_retry=2)

    def ready_scene(self, idx, seconds=5):
        scene = self.p.create_scene(self.pid, idx, f"S{idx}")
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=?", (scene,))
        self.p.conn.commit()
        return scene

    def with_video_prompt(self, scene, idx, seconds=5):
        job = self.p.create_job(scene)
        self.p.start(job)
        self.p.succeed(job)
        self.p.approve(job)
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": idx, "motion_prompt": "push", "duration_sec": seconds}]})
        approve_motion_prompt(self.p, scene)

    def test_missing_pricing_file_gives_safe_defaults(self):
        data = cost.load_pricing(os.path.join(tempfile.mkdtemp(), "nope.json"))
        self.assertEqual((data["confirm_batch_at"], data["per_image"]), (10, {}))

    def test_shipped_template_has_no_invented_prices(self):
        """per_image (Deepix) has no public source: it is unfilled, or the provisional average measured from the web total (2026-09-26,
        documented in _note_per_image — the only allowed source). per_video_second may carry approximate USD estimates (2026-09-22,
        explicit user request), but only values that trace back to the documented public listing (listed_usd_per_video_second) --
        never a number invented without a source."""
        data = cost.load_pricing(cost.DEFAULT_PRICING_PATH)
        self.assertNotIn("_error", data)
        filled = {v for v in data["per_image"].values() if v is not None}
        self.assertTrue(not filled or ("_note_per_image" in data and all(str(v) in data["_note_per_image"] for v in filled)))
        listed = set(data.get("listed_usd_per_video_second", {}).values()) - {None}
        self.assertTrue(all(v is None or v in listed for v in data["per_video_second"].values()))

    def test_image_estimate_counts_fresh_and_queued_and_applies_retry_range(self):
        for i in (1, 2, 3):
            self.ready_scene(i)
        self.p.create_job(self.p.conn.execute("SELECT id FROM scenes WHERE idx=1").fetchone()["id"])
        est = cost.estimate_images(self.p, self.pid, full(PRICING), "img-model")
        self.assertEqual((est["items"], est["min"], est["max"]), (3, 9, 27))
        unknown = cost.estimate_images(self.p, self.pid, full(PRICING), "other-model")
        self.assertFalse(unknown["known"])
        self.assertIn("chưa có giá", cost.format_estimate(unknown))
        self.assertIn("9.0 credits", cost.format_estimate(est))

    def test_video_estimate_clamps_duration_and_supports_clip_pricing(self):
        for idx, seconds in ((1, 5), (2, 2)):
            self.with_video_prompt(self.ready_scene(idx), idx, seconds)
        clamp = lambda s: min(max(round(s), 3), 15)
        est = cost.estimate_videos(self.p, self.pid, full(PRICING), "kling-v3-omni", "pro", clamp)
        self.assertEqual((est["items"], est["seconds"], est["min"], est["max"]), (2, 8, 16, 48))
        per_clip = cost.estimate_videos(self.p, self.pid, full(PRICING), "clip-model", "hd", clamp)
        self.assertEqual(per_clip["min"], 100)
        unknown = cost.estimate_videos(self.p, self.pid, full(PRICING), "vid", "std", clamp)
        self.assertFalse(unknown["known"])

    def test_no_pending_work_is_known_and_free(self):
        est = cost.estimate_videos(self.p, self.pid, full(PRICING), "kling-v3-omni", "pro", lambda s: s)
        self.assertEqual((est["items"], est["known"], est["min"]), (0, True, 0.0))

    def test_ledger_records_submissions_and_prices_real_providers_only(self):
        scene = self.ready_scene(1)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", ('{"image_prompt": "misty forest"}', scene))
        self.p.conn.commit()
        self.p.create_job(scene)
        directory = tempfile.mkdtemp()
        provider = MockImageProvider()
        ImageRunner(self.p, provider, directory).submit_pending(self.pid)
        events = self.p.conn.execute("SELECT * FROM usage_events").fetchall()
        self.assertEqual([(e["kind"], e["provider"], e["quantity"]) for e in events], [("image", "mock-image", 1)])
        self.assertEqual(cost.spend_summary(self.p.conn, self.pid, full(PRICING))["credits"], 0.0)
        provider.name = "deepix"
        provider.usage_info = lambda: ("img-model", "image")
        job = self.p.create_job(scene)
        ImageRunner(self.p, provider, directory).submit_pending(self.pid)
        spend = cost.spend_summary(self.p.conn, self.pid, full(PRICING))
        self.assertEqual((spend["images"], spend["credits"], spend["unknown_prices"]), (2, 3.0, []))

    def test_video_ledger_uses_billed_seconds(self):
        scene = self.ready_scene(1)
        self.with_video_prompt(scene, 1, 12)
        self.p.create_job(scene, "video_gen")
        provider = MockVideoProvider()
        provider.name = "clipai"
        provider.usage_info = lambda model=None, duration=5: ("kling-v3-omni", "pro", 12)
        VideoRunner(self.p, provider, tempfile.mkdtemp()).submit_pending(self.pid)
        spend = cost.spend_summary(self.p.conn, self.pid, full(PRICING))
        self.assertEqual((spend["clips"], spend["seconds"], spend["credits"]), (1, 12, 24))
        unpriced = cost.spend_summary(self.p.conn, self.pid, full({"per_video_second": {}}))
        self.assertEqual(unpriced["unknown_prices"], ["kling-v3-omni:pro"])


class DashboardCostTests(unittest.TestCase):
    def test_video_step_shows_estimate_and_spend(self):
        from streamlit.testing.v1 import AppTest
        tmp = tempfile.mkdtemp()
        pricing = os.path.join(tmp, "pricing.json")
        with open(pricing, "w", encoding="utf-8") as f:
            json.dump({"per_video_second": {"kling-v3-omni:pro": 2}}, f)
        db = os.path.join(tmp, "m.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("Demo")
        scene = p.create_scene(pid, 1, "S1")
        job = p.create_job(scene)
        p.start(job)
        p.succeed(job)
        p.approve(job)
        store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "push", "duration_sec": 5}]})
        approve_motion_prompt(p, scene)
        env = {"PIPELINE_DB": db, "PIPELINE_DATA": os.path.join(tmp, "d"), "PIPELINE_PRICING": pricing}
        os.environ.update(env)
        try:
            app = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
            at = AppTest.from_file(app, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
            self.assertFalse(at.exception)
            texts = " ".join(i.value for i in at.info)
            self.assertIn("Ước tính chi phí", texts)
            self.assertIn("10.0 credits", texts)
        finally:
            for k in env:
                os.environ.pop(k, None)


if __name__ == "__main__":
    unittest.main()
