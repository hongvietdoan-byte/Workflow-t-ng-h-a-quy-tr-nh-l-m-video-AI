"""S4.11 Sample Mode (removed in S14.9 — only the "it is gone" check stays) + S4.12 video edit (ClipAI Seedance 2.5, fields read from the ClipAI web app 2026-10-01) + the 2.5 first-frame
ratio fix (real refusal 2026-10-01: "For first-frame … generation, the output ratio follows the first-frame image")."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import cost
from core.adapters.clipai import ClipAIVideoProvider, video_edit_problems
from core.providers import ProviderError
from tests.test_adapters import TOKEN, FakeTransport, ctx_of, ok

GOOD_CLIP = {"width": 720, "height": 1280, "sar": "1:1", "fps": 24.0, "duration": 4.0}


class SampleModeAndEditTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.dir = tempfile.mkdtemp()
        self.image = os.path.join(self.dir, "img.png")
        with open(self.image, "wb") as f:
            f.write(b"\x89PNG-fake")
        self.clip = os.path.join(self.dir, "src.mp4")
        with open(self.clip, "wb") as f:
            f.write(b"mp4-fake")
        self.p = ClipAIVideoProvider(TOKEN, "https://clipai.example", self.t)
        self.t.on("POST", "/api/kling/seedance-video-submit", ok({"tasks": [{"task_id": "cgt-1", "task_status": "submitted"}]}))

    def env(self, **kw):
        return mock.patch.dict(os.environ, {("FEATURE_" + k.upper()): v for k, v in kw.items()})

    # ---- 2.5 first frame ratio (bug found by the real run) ----
    def test_seedance_2_5_first_frame_sends_adaptive_ratio(self):
        self.p.submit(self.image, "tear", None, 4, model="seedance-2.5", aspect_ratio="9:16", resolution="720p")
        self.assertEqual(ctx_of(self.t.calls[0])["ratio"], "adaptive")
        self.p.submit(self.image, "tear", None, 5, model="seedance", aspect_ratio="9:16")      # 2.0 keeps the set ratio
        self.assertEqual(ctx_of(self.t.calls[1])["ratio"], "9:16")
        self.p.submit(None, "@Image 1", None, 5, model="seedance-2.5", aspect_ratio="9:16", reference_only=[self.image])
        self.assertEqual(ctx_of(self.t.calls[2])["ratio"], "9:16")                              # no first frame: ratio is free

    # 07/10: người dùng duyệt khôi phục để so A+/B Khủng Long Đỏ.
    def test_sample_is_off_and_sends_nothing_without_its_flag(self):
        with self.env(seedance_sample_mode="0"):
            with self.assertRaises(ProviderError) as cm:
                self.p.submit(self.image, "p", None, 4, model="seedance-2.5", draft=True)
            self.assertEqual(cm.exception.code, "feature_off")
            with self.assertRaises(ProviderError):
                self.p.submit_final_from_sample("seedance:cgt-1")
        self.assertEqual(self.t.calls, [])

    def test_sample_forces_480p_and_normal_video_keeps_its_body(self):
        with self.env(seedance_sample_mode="1"):
            self.p.submit(self.image, "p", None, 4, model="seedance-2.5", resolution="720p", draft=True)
            ctx = ctx_of(self.t.calls[0])
            self.assertEqual((ctx["draft"], ctx["resolution"], ctx["ratio"]), (True, "480p", "adaptive"))
            with self.assertRaises(ProviderError):
                self.p.submit(self.image, "p", None, 4, model="seedance", draft=True)
        self.p.submit(self.image, "p", None, 4, model="seedance-2.5", resolution="720p")
        self.assertNotIn("draft", ctx_of(self.t.calls[1]))
        self.assertEqual(len(self.t.calls), 2)

    def test_final_from_sample_body_and_invalid_id_never_posts(self):
        with self.env(seedance_sample_mode="1"):
            self.p.submit_final_from_sample("seedance:cgt-1")
            ctx = ctx_of(self.t.calls[0])
            self.assertEqual(ctx["content"], [{"type": "draft_task", "draft_task": {"id": "cgt-1"}}])
            self.assertEqual((ctx["resolution"], ctx["video_num"]), ("1080p", 1))
            for bad in ("omni:T1", "seedance:", "seedance:cgt-1:other"):
                with self.assertRaises(ProviderError):
                    self.p.submit_final_from_sample(bad)
        self.assertEqual(len(self.t.calls), 1)

    # ---- S4.12 ----
    def test_video_edit_body(self):
        with self.env(seedance_video_edit="1"), mock.patch("core.adapters.clipai._probe_video", return_value=GOOD_CLIP):
            self.p.submit_video_edit(self.clip, "Edit @Video 1. The only change: …", "480p", [self.image])
        call = self.t.calls[0]
        ctx = ctx_of(call)
        self.assertEqual((ctx["omni_reference_task_type"], ctx["duration"], ctx["ratio"], ctx["resolution"]), ("edit", -1, "adaptive", "480p"))
        self.assertEqual([c.get("role") for c in ctx["content"]], [None, "reference_image", "reference_video"])
        body = call["body"].decode("utf-8", "replace")
        self.assertIn('name="video_files"', body)
        self.assertIn('name="image_files"', body)

    def test_video_edit_refuses_before_sending(self):
        with self.env(seedance_video_edit="0"):
            with self.assertRaises(ProviderError) as cm:
                self.p.submit_video_edit(self.clip, "Edit @Video 1", "480p")
            self.assertEqual(cm.exception.code, "feature_off")
        with self.env(seedance_video_edit="1"):
            with mock.patch("core.adapters.clipai._probe_video", return_value=dict(GOOD_CLIP, duration=1.08)):
                with self.assertRaises(ProviderError) as cm:
                    self.p.submit_video_edit(self.clip, "Edit @Video 1", "480p")      # #8 clip 01 as delivered is 1.08 s
            self.assertEqual(cm.exception.code, "rule_violation")
            with mock.patch("core.adapters.clipai._probe_video", return_value=GOOD_CLIP):
                for res in ("1080p",):
                    with self.assertRaises(ProviderError):
                        self.p.submit_video_edit(self.clip, "Edit @Video 1", res)
                with self.assertRaises(ProviderError):
                    self.p.submit_video_edit(self.clip, "   ", "480p")
        self.assertEqual(self.t.calls, [])

    def test_video_edit_rules(self):
        self.assertEqual(video_edit_problems(GOOD_CLIP), [])
        self.assertTrue(video_edit_problems({}))                                     # unreadable clip is a problem, not a pass
        self.assertTrue(video_edit_problems(dict(GOOD_CLIP, duration=31)))
        self.assertEqual(video_edit_problems(dict(GOOD_CLIP, width=1080, height=1920)), [])   # 2 073 600 px fits
        self.assertTrue(video_edit_problems(dict(GOOD_CLIP, width=1920, height=1440)))        # 2 764 800 px is too many
        self.assertEqual(video_edit_problems(dict(GOOD_CLIP, width=480, height=854)), [])

    # ---- real cost ----
    def test_web_price_formula(self):
        m = "dreamina-seedance-2-5-260628"
        # task cgt-20260930152127-74l59 (2026-09-30): 720p 9:16 5 s + a 4.04 s reference video billed 195 300 tokens
        self.assertAlmostEqual(cost.seedance_tokens("720p", "9:16", 5, 4.0417), 195300, delta=150)
        self.assertAlmostEqual(cost.seedance_estimate(m, "720p", "9:16", 5), 1.1556, places=3)     # = 0,23 USD/s listed
        self.assertAlmostEqual(cost.seedance_estimate(m, "480p", "9:16", 4), 0.4112, places=3)
        self.assertAlmostEqual(cost.seedance_estimate(m, "1080p", "9:16", 4), 2.0801, places=3)
        self.assertAlmostEqual(cost.seedance_estimate(m, "480p", "9:16", 4, 4), 0.4919, places=3)
        self.assertIsNone(cost.seedance_token_usd("kling-v3-omni", 1000, False))

    def test_task_usage_reads_billed_tokens(self):
        rows = [{"id": 9, "task_id": "cgt-1", "task_status": 2, "model_name": "dreamina-seedance-2-5-260628", "is_draft": True,
                 "draft_expired_at": 1791370000, "resolution": "480p", "duration": 4.0,
                 "extra_data": json.dumps({"has_video_input": False, "usage": {"total_tokens": 38430}})}]
        self.t.on("GET", "/api/kling/video-list", ok({"data": rows, "count": 1}, status="success"))
        u = self.p.task_usage("seedance:cgt-1")
        self.assertEqual((u["tokens"], u["is_draft"], u["has_video_input"]), (38430, True, False))
        self.assertAlmostEqual(u["usd"], 0.4112, places=3)


if __name__ == "__main__":
    unittest.main()
