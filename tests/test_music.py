import json
import os
import tempfile
import unittest
from unittest import mock

from core import music
from core.adapters.clipai_audio import ClipAIAudioProvider
from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline
from core.providers import ProviderError
from tests.test_adapters import TOKEN, FakeTransport, HttpResponse, ok
from tests.test_llm_io_preflight import ANALYSIS


def body_of(call):
    return json.loads(call["body"].decode("utf-8"))


class AudioAdapterTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.provider = ClipAIAudioProvider(TOKEN, transport=self.t)

    def test_music_request_shape_and_clamp(self):
        self.t.on("POST", "/api/sound/generate", ok({"asset_id": 7, "status": "processing"}))
        self.assertEqual(self.provider.generate_music("epic", length_ms=100, instrumental=True), "7")
        body = body_of(self.t.calls[0])
        self.assertEqual((body["type"], body["model"], body["prompt"]), ("music", "music_v2", "epic"))
        self.assertEqual(body["input_params"]["music_length_ms"], 3000)
        self.assertTrue(body["input_params"]["force_instrumental"])
        self.assertEqual(self.t.calls[0]["headers"]["Authorization"], f"Bearer {TOKEN}")

    def test_tts_needs_numeric_voice_and_known_model(self):
        self.t.on("POST", "/api/sound/generate", ok({"asset_id": 1, "status": "processing"}))
        self.provider.generate_tts("hello", 12, language_code="en")
        body = body_of(self.t.calls[0])
        self.assertEqual((body["type"], body["voice_actor_id"], body["model"]), ("tts", 12, "eleven_v3"))
        with self.assertRaises(ProviderError):
            self.provider.generate_tts("hello", 12, model="nope")

    def test_prompt_limit_and_empty(self):
        with self.assertRaises(ProviderError) as e:
            self.provider.generate_music("x" * 2001)
        self.assertEqual(e.exception.code, "prompt_too_long")
        with self.assertRaises(ProviderError):
            self.provider.generate_sfx("  ")

    def test_status_processing_success_failed(self):
        items = {"items": [{"id": 5, "status": "processing"}, {"id": 6, "status": "success", "url": "https://cdn/x.mp3",
                                                                "duration_ms": 9000},
                           {"id": 8, "status": "failed", "provider_error": "boom"}]}
        self.t.on("GET", "/api/sound/audio-list", ok(items))
        self.assertEqual(self.provider.status("music", "5").state, "running")
        done = self.provider.status("music", "6")
        self.assertEqual((done.state, done.url, done.duration_ms), ("succeeded", "https://cdn/x.mp3", 9000))
        failed = self.provider.status("music", "8")
        self.assertEqual((failed.state, failed.message), ("failed", "boom"))
        self.assertEqual(self.provider.status("music", "999").state, "running")

    def test_success_without_url_is_not_done(self):
        self.t.on("GET", "/api/sound/audio-list", ok({"items": [{"id": 6, "status": "success", "url": ""}]}))
        self.assertEqual(self.provider.status("music", "6").state, "running")

    def test_download_sends_no_token(self):
        self.t.on("GET", "*", HttpResponse(200, b"ID3data"))
        with tempfile.TemporaryDirectory() as d:
            dest = self.provider.download("https://cdn.example/x.mp3", os.path.join(d, "a.mp3"))
            self.assertEqual(open(dest, "rb").read(), b"ID3data")
        self.assertNotIn("Authorization", self.t.calls[0]["headers"])

    def test_from_env_requires_token(self):
        with mock.patch.dict(os.environ, {"CLIPAI_TOKEN": ""}):
            with self.assertRaises(ProviderError):
                ClipAIAudioProvider.from_env()


class MusicFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.drafts, self.selected = music.project_dirs(self.tmp, 1)

    def test_mock_full_flow(self):
        provider = music.MockAudioProvider()
        self.assertEqual(music.submit_drafts(provider, self.drafts, "calm", 5000, True, 3), 3)
        counts = music.refresh_drafts(provider, self.drafts)
        self.assertEqual(counts["succeeded"], 3)
        path = music.select_draft(self.drafts, self.selected, 1)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.listdir(self.selected), ["selected.wav"])
        music.select_draft(self.drafts, self.selected, 2)
        self.assertEqual(len(os.listdir(self.selected)), 1)

    def test_failed_draft_is_not_resubmitted_and_cannot_be_selected(self):
        class Failing(music.MockAudioProvider):
            def status(self, category, asset_id):
                from core.adapters.clipai_audio import AudioStatus
                return AudioStatus("failed", message="provider said no")

        provider = Failing()
        music.submit_drafts(provider, self.drafts, "calm", None, True, 1)
        self.assertEqual(music.refresh_drafts(provider, self.drafts)["failed"], 1)
        self.assertEqual(music.refresh_drafts(provider, self.drafts)["failed"], 1)
        self.assertEqual(len(provider._assets), 1)  # never re-submitted
        with self.assertRaises(ValueError):
            music.select_draft(self.drafts, self.selected, 0)

    def test_submit_error_is_recorded_and_stops(self):
        class Rejecting(music.MockAudioProvider):
            def generate_music(self, *a, **k):
                raise ProviderError("prompt too long", code="prompt_too_long")

        self.assertEqual(music.submit_drafts(Rejecting(), self.drafts, "x", None, True, 3), 0)
        drafts = music.load_drafts(self.drafts)
        self.assertEqual((len(drafts), drafts[0]["state"]), (1, "failed"))

    def test_default_brief_uses_scene_moods(self):
        p = Pipeline(connect(":memory:"))
        pid = p.create_project("Demo")
        p.create_scene(pid, 1, "CẢNH 1")
        store_scene_analysis(p, pid, ANALYSIS)
        brief = music.default_brief(p, pid)
        self.assertTrue(brief["instrumental"])
        self.assertGreaterEqual(brief["length_ms"], music.MIN_MS)
        for mood in music.scene_moods(p, pid):
            self.assertIn(mood, brief["prompt"])

    def test_provider_selection(self):
        with mock.patch.dict(os.environ, {"AUDIO_PROVIDER": "mock", "VIDEO_PROVIDER": ""}):
            self.assertEqual(music.audio_provider().name, "mock-audio")
        with mock.patch.dict(os.environ, {"AUDIO_PROVIDER": "", "VIDEO_PROVIDER": ""}):
            self.assertIsNone(music.audio_provider())


if __name__ == "__main__":
    unittest.main()
