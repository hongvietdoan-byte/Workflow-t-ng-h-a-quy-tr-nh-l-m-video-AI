"""Clip AI audio adapter: music, sound effects and TTS through the Clip AI gateway.

Contract source: the vendor skill/reference (clipai 1.3.1, "Public audio workflow"):
- POST /api/sound/generate only returns a submitted `asset_id` (status `processing`).
- The finished asset is found by scanning GET /api/sound/audio-list?category=... for that id;
  success needs `status=success` AND a managed `url`. `failed` carries `provider_error` and is
  never resubmitted automatically (that would only burn credits).
- TTS needs the numeric Clip AI `voice_actor_id` from /api/sound/voice-actors (not the provider voice id).
- Public limits: `text` / `prompt` at most 2000 characters.
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..providers import ProviderError
from .clipai import DEFAULT_BASE
from .http import ApiClient, Transport, clean_token, urllib_transport

USER_AGENT = "AIVideoPipeline-ClipAI-Audio/0.1"
PATH_GENERATE = "/api/sound/generate"
PATH_VOICES = "/api/sound/voice-actors"
PATH_LIST = "/api/sound/audio-list"

CATEGORIES = ("music", "sound_effect", "tts", "upload")
TEXT_LIMIT = 2000
MUSIC_MS = (3000, 600000)
DEFAULT_MODELS = {"music": "music_v2", "sound_effect": "eleven_text_to_sound_v2", "tts": "eleven_v3"}
TTS_MODELS = ("eleven_v3", "eleven_turbo_v2_5", "eleven_flash_v2_5", "eleven_multilingual_v2")   # v2: no Vietnamese
_PAGES = 5


@dataclass
class AudioStatus:
    state: str  # 'running' | 'succeeded' | 'failed'
    url: Optional[str] = None
    duration_ms: Optional[int] = None
    message: Optional[str] = None


class ClipAIAudioProvider:
    name = "clipai-audio"

    def __init__(self, token: str, base_url: str = DEFAULT_BASE, transport: Transport = urllib_transport):
        self.client = ApiClient(base_url, token, USER_AGENT, transport)

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "ClipAIAudioProvider":
        token = clean_token(os.environ.get("CLIPAI_TOKEN", ""))
        if not token:
            raise ProviderError("CLIPAI_TOKEN is not set (same token as the video provider; never commit it).",
                                code="config")
        return cls(token, os.environ.get("CLIPAI_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport)

    # ---- submit ---------------------------------------------------------
    def _generate(self, kind: str, name: str, model: str, fields: Dict, params: Dict) -> str:
        body = {"name": name or kind, "model": model, "provider": "elevenlabs", "type": kind, **fields,
                "input_params": {"output_format": "mp3", **params}}
        data = self.client.post_json(PATH_GENERATE, body) or {}
        asset_id = data.get("asset_id")
        if asset_id is None:
            raise ProviderError("audio create returned no asset_id", code="bad_response")
        if data.get("status") == "failed":
            raise ProviderError(data.get("provider_error") or "audio creation failed", code="task_failed")
        return str(asset_id)

    @staticmethod
    def _check_text(label: str, text: str) -> str:
        text = (text or "").strip()
        if not text:
            raise ProviderError(f"{label} is empty", code="bad_input")
        if len(text) > TEXT_LIMIT:
            raise ProviderError(f"{label} is {len(text)} characters; Clip AI allows at most {TEXT_LIMIT}",
                                code="prompt_too_long")
        return text

    def generate_music(self, prompt: str, length_ms: Optional[int] = None, instrumental: bool = True,
                       name: str = "music") -> str:
        prompt = self._check_text("music prompt", prompt)
        params: Dict = {"force_instrumental": bool(instrumental)}
        if length_ms is not None:
            params["music_length_ms"] = int(min(max(length_ms, MUSIC_MS[0]), MUSIC_MS[1]))
        return self._generate("music", name, DEFAULT_MODELS["music"], {"prompt": prompt}, params)

    def generate_sfx(self, prompt: str, duration_seconds: Optional[float] = None, loop: bool = False,
                     name: str = "sfx") -> str:
        prompt = self._check_text("sound effect prompt", prompt)
        params: Dict = {"loop": bool(loop)}
        if duration_seconds is not None:
            params["duration_seconds"] = float(min(max(duration_seconds, 0.5), 30))
        return self._generate("sound_effect", name, DEFAULT_MODELS["sound_effect"], {"prompt": prompt}, params)

    def generate_tts(self, text: str, voice_actor_id: int, model: str = "eleven_v3",
                     language_code: Optional[str] = None, name: str = "tts") -> str:
        text = self._check_text("TTS text", text)
        if model not in TTS_MODELS:
            raise ProviderError(f"unknown TTS model '{model}'. Allowed: {list(TTS_MODELS)}", code="unsupported_model")
        params = {"language_code": language_code} if language_code else {}
        return self._generate("tts", name, model, {"text": text, "voice_actor_id": int(voice_actor_id)}, params)

    # ---- status / download ----------------------------------------------
    def status(self, category: str, asset_id: str) -> AudioStatus:
        if category not in CATEGORIES:
            raise ProviderError(f"unknown audio category '{category}'", code="bad_input")
        for page in range(1, _PAGES + 1):
            data = self.client.get(PATH_LIST, {"category": category, "page": page, "page_size": 50}) or {}
            for item in data.get("items") or []:
                if str(item.get("id")) != str(asset_id):
                    continue
                state = item.get("status")
                if state == "success":
                    if not item.get("url"):
                        return AudioStatus("running")
                    return AudioStatus("succeeded", item["url"], item.get("duration_ms"))
                if state in ("failed", "deleted"):
                    return AudioStatus("failed", message=item.get("provider_error") or f"asset {state}")
                return AudioStatus("running")
            if len(data.get("items") or []) < 50:
                break
        return AudioStatus("running")

    def download(self, url: str, dest_path: str) -> str:
        return self.client.download(url, dest_path)

    def voice_actors(self, owner: Optional[str] = None, keyword: Optional[str] = None,
                     page_size: int = 100) -> List[dict]:
        data = self.client.get(PATH_VOICES, {"owner": owner, "keyword": keyword, "page": 1,
                                             "page_size": min(max(page_size, 1), 100)}) or {}
        return list(data.get("items") or [])
