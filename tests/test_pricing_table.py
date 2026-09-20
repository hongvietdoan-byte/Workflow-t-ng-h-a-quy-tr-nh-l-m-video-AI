import json
import os
import tempfile
import unittest

from core import cost
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import Pipeline

BASE = {"currency": "credits", "confirm_batch_at": 10, "note": "x", "per_image": {}, "per_video_second": {},
        "per_video_clip": {}, "per_audio": {}}


def pricing(**kw):
    return {**BASE, **kw}


class ClipPriceTests(unittest.TestCase):
    def test_lookup_order_exact_then_flat_clip_then_per_second(self):
        pr = pricing(per_video_clip={"m:t:5s": 30, "m:t": 50}, per_video_second={"m:t": 2, "n:t": 3})
        self.assertEqual(cost.clip_price(pr, "m", "t", 5), 30)      # exact setup price wins
        self.assertEqual(cost.clip_price(pr, "m", "t", 10), 50)     # flat per clip
        self.assertEqual(cost.clip_price(pr, "n", "t", 10), 30)     # per second x seconds
        self.assertIsNone(cost.clip_price(pr, "unknown", "t", 5))

    def test_estimate_prices_each_clip_by_its_own_duration(self):
        p = Pipeline(connect())
        pid = p.create_project("t", max_retry=1)
        for idx, sec in ((1, 5), (2, 10)):
            scene = p.create_scene(pid, idx, f"S{idx}")
            job = p.create_job(scene)
            p.start(job)
            p.succeed(job)
            p.approve(job)
            store_motion_prompts(p, pid, {"scenes": [{"idx": idx, "motion_prompt": "push", "duration_sec": sec}]})
            approve_motion_prompt(p, scene)
        pr = pricing(per_video_clip={"m:t:5s": 30, "m:t:10s": 55})
        est = cost.estimate_videos(p, pid, pr, "m", "t", lambda s: s)
        self.assertEqual((est["min"], est["max"], est["known"]), (85, 170, True))
        partial = cost.estimate_videos(p, pid, pricing(per_video_clip={"m:t:5s": 30}), "m", "t", lambda s: s)
        self.assertFalse(partial["known"])  # one clip has no price: no invented total


class RowsTests(unittest.TestCase):
    def test_roundtrip_keeps_prices_and_settings_and_adds_suggestions(self):
        pr = pricing(per_image={"img": 3}, per_video_clip={"kling-v3-omni:pro:5s": 12.5}, per_audio={"music_v2": None})
        rows = cost.pricing_to_rows(pr)
        self.assertIn({"kind": "per_image", "key": "img", "price": 3.0}, rows)
        suggested = [r for r in rows if r["price"] is None and r["kind"] == "per_video_clip"]
        self.assertTrue(suggested)
        self.assertNotIn("kling-v3-omni:pro:5s", [r["key"] for r in suggested])
        back = cost.rows_to_pricing(rows, pr)
        self.assertEqual(back["per_image"], {"img": 3.0})
        self.assertEqual(back["per_video_clip"]["kling-v3-omni:pro:5s"], 12.5)
        self.assertEqual((back["currency"], back["confirm_batch_at"], back["note"]), ("credits", 10, "x"))

    def test_validation_and_blank_rows(self):
        with self.assertRaises(ValueError):
            cost.rows_to_pricing([{"kind": "per_image", "key": "a", "price": -1}], BASE)
        with self.assertRaises(ValueError):
            cost.rows_to_pricing([{"kind": "per_image", "key": "", "price": 1}], BASE)
        with self.assertRaises(ValueError):
            cost.rows_to_pricing([{"kind": None, "key": "a", "price": 1}], BASE)
        ok = cost.rows_to_pricing([{"kind": None, "key": "", "price": None},
                                   {"kind": "per_audio", "key": "music_v2", "price": float("nan")}], BASE)
        self.assertEqual(ok["per_audio"], {"music_v2": None})

    def test_save_and_reload(self):
        path = os.path.join(tempfile.mkdtemp(), "pricing.json")
        cost.save_pricing(pricing(per_image={"img": 4}), path)
        self.assertEqual(cost.load_pricing(path)["per_image"], {"img": 4})
        self.assertEqual(json.load(open(path, encoding="utf-8"))["currency"], "credits")


if __name__ == "__main__":
    unittest.main()
