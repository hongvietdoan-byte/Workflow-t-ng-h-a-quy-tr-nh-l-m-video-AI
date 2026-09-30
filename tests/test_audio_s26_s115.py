"""S1.15 (Eleven Music v2.5 model option in the adapter) + S2.6 (Seed Audio 1.0 request, checked before paying) — 2026-10-01."""
import json
import unittest

from core import music
from core.adapters.clipai_audio import ClipAIAudioProvider
from core.providers import ProviderError
from tests.test_adapters import TOKEN, FakeTransport, ok

REFS = ["https://cdn.example/a.mp3", "https://cdn.example/b.mp3", "https://cdn.example/c.mp3"]


def body_of(call):
    return json.loads(call["body"].decode("utf-8"))


class MusicModelTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.t.on("POST", "/api/sound/generate", ok({"asset_id": 9, "status": "processing"}))
        self.p = ClipAIAudioProvider(TOKEN, transport=self.t)

    def test_default_stays_music_v2(self):
        self.p.generate_music("calm", 30000)
        self.assertEqual(body_of(self.t.calls[0])["model"], "music_v2")

    def test_v2_5_is_sent_as_named(self):
        self.p.generate_music("calm", 30000, model="music_v2_5")
        body = body_of(self.t.calls[0])
        self.assertEqual((body["model"], body["provider"], body["type"]), ("music_v2_5", "elevenlabs", "music"))
        self.assertEqual(body["input_params"]["music_length_ms"], 30000)

    def test_unknown_model_refused_before_paying(self):
        with self.assertRaises(ProviderError) as e:
            self.p.generate_music("calm", model="music_v9")
        self.assertEqual(e.exception.code, "unsupported_model")
        self.assertEqual(self.t.calls, [])

    def test_mock_accepts_model(self):
        self.assertTrue(music.MockAudioProvider().generate_music("x", 4000, True, name="m", model="music_v2_5"))


class SeedAudioTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.p = ClipAIAudioProvider(TOKEN, transport=self.t)

    def test_body_shape_matches_web_client(self):
        self.t.on("POST", "/api/sound/generate", ok({"asset_id": 1727, "status": "processing"}))
        self.assertEqual(self.p.generate_seed_audio("[1.0s:2.0s] Kelly (@Audio1): “Anh nói đi.”", REFS), "1727")
        b = body_of(self.t.calls[0])
        self.assertEqual((b["provider"], b["type"], b["model"]), ("seedance", "tts", "seed-audio-1.0"))
        self.assertEqual(b["references"], [{"audio_url": u} for u in REFS])
        self.assertTrue(b["enable_subtitle"])
        self.assertFalse(b["aigc_watermark"])
        self.assertEqual((b["speech_rate"], b["loudness_rate"], b["pitch_rate"]), (0, 0, 0))
        self.assertNotIn("input_params", b)          # the web sends the settings at the top level

    def test_refusals_before_paying(self):
        cases = [dict(text=""), dict(text="x" * 3001), dict(text="ok", reference_audio_urls=REFS + ["https://cdn.example/d.mp3"]),
                 dict(text="ok", reference_audio_urls=REFS[:1], reference_image_url="https://cdn.example/i.png"),
                 dict(text="ok", reference_audio_urls=["C:/local.mp3"]), dict(text="ok", sample_rate=22050),
                 dict(text="ok", output_format="flac")]
        for kw in cases:
            with self.subTest(kw=list(kw)):
                with self.assertRaises(ProviderError):
                    self.p.generate_seed_audio(**kw)
        self.assertEqual(self.t.calls, [])

    def test_image_reference_alone(self):
        b = ClipAIAudioProvider.seed_audio_body("ok", reference_image_url="https://cdn.example/i.png")
        self.assertEqual(b["references"], [{"image_url": "https://cdn.example/i.png"}])

    def test_asset_returns_whole_item(self):
        item = {"id": 5, "status": "failed", "provider_error": {"message": "Seed Audio error: 400"}, "input_params": {"x": 1}}
        self.t.on("GET", "/api/sound/audio-list", ok({"items": [item]}))
        self.assertEqual(self.p.asset("tts", "5"), item)
        self.assertIsNone(self.p.asset("tts", "6"))


if __name__ == "__main__":
    unittest.main()
