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
TTS_PARAM_RANGES = {"speed": (0.7, 1.2), "stability": (0.0, 1.0), "similarity_boost": (0.0, 1.0), "style": (0.0, 1.0)}
# S1.15 (2026-10-01): the web "Text to Music" list offers music_v2_5 = Eleven Music v2.5 next to music_v2 (read from the web bundle;
# the public skill 1.3.1 still lists only music_v2). Whether the API takes it is proven by a real call — docs/KET_QUA_S2_6_S1_15_2026-10-01.md.
MUSIC_MODELS = ("music_v2", "music_v2_5")
# S2.6: Seed Audio 1.0 ("All-in-one Voice" on the web) — one request = a whole track (several voices + SFX + music), Vietnamese,
# [1.0s:2.5s] time marks, optional sentence/word time stamps. Body shape copied from the web client (2026-10-01): provider
# 'seedance', type 'tts', the settings at the top level (not in input_params); references = 1 image OR up to 3 audio clips
# (each ≤ 30 s / 10 MB); text ≤ 3000 characters; no SSML.
SEED_AUDIO_MODEL = "seed-audio-1.0"
SEED_TEXT_LIMIT = 3000
SEED_MAX_AUDIO_REFS = 3
SEED_SAMPLE_RATES = (8000, 16000, 24000, 32000, 44100, 48000)
SEED_FORMATS = ("mp3", "wav", "pcm", "ogg_opus")
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
                       name: str = "music", model: Optional[str] = None) -> str:
        """model: None = DEFAULT_MODELS['music'] (music_v2); 'music_v2_5' = Eleven Music v2.5 (S1.15). Unknown names are refused
        here, before anything is paid."""
        model = model or DEFAULT_MODELS["music"]
        if model not in MUSIC_MODELS:
            raise ProviderError(f"unknown music model '{model}'. Allowed: {list(MUSIC_MODELS)}", code="unsupported_model")
        prompt = self._check_text("music prompt", prompt)
        params: Dict = {"force_instrumental": bool(instrumental)}
        if length_ms is not None:
            params["music_length_ms"] = int(min(max(length_ms, MUSIC_MS[0]), MUSIC_MS[1]))
        return self._generate("music", name, model, {"prompt": prompt}, params)

    @staticmethod
    def seed_audio_body(text: str, reference_audio_urls=(), reference_image_url: Optional[str] = None, name: str = "seed-audio",
                        subtitles: bool = True, sample_rate: int = 44100, output_format: str = "mp3") -> Dict:
        """The request for one Seed Audio 1.0 track, checked before anything is paid (S2.6)."""
        text = (text or "").strip()
        if not text:
            raise ProviderError("Seed Audio text is empty", code="bad_input")
        if len(text) > SEED_TEXT_LIMIT:
            raise ProviderError(f"Seed Audio text is {len(text)} characters; Clip AI allows at most {SEED_TEXT_LIMIT}",
                                code="prompt_too_long")
        audios = [u for u in (reference_audio_urls or []) if u]
        if reference_image_url and audios:
            raise ProviderError("Seed Audio takes a reference image OR reference audio, not both", code="bad_input")
        if len(audios) > SEED_MAX_AUDIO_REFS:
            raise ProviderError(f"Seed Audio takes at most {SEED_MAX_AUDIO_REFS} reference audio clips ({len(audios)} given)",
                                code="bad_input")
        for url in audios + ([reference_image_url] if reference_image_url else []):
            if not str(url).startswith(("http://", "https://")):
                raise ProviderError(f"Seed Audio reference must be an http(s) URL: {url!r}", code="bad_input")
        if int(sample_rate) not in SEED_SAMPLE_RATES:
            raise ProviderError(f"sample_rate {sample_rate} not in {list(SEED_SAMPLE_RATES)}", code="bad_input")
        if output_format not in SEED_FORMATS:
            raise ProviderError(f"output_format {output_format!r} not in {list(SEED_FORMATS)}", code="bad_input")
        refs = [{"image_url": reference_image_url}] if reference_image_url else [{"audio_url": u} for u in audios]
        # speech_rate / loudness_rate / pitch_rate: the web always sends them (0 = unchanged), so do we. NOT the cause of the
        # provider's "Seed Audio error: 400": assets 1727 (without them) and 30780 (with them) failed the same way (2026-10-01).
        # Unproven so far: the reference URLs (web uploads local files through /kling/upload) or sample_rate 44100 (guide lists
        # 48K/24K/16K/8K). Until one real track succeeds this path is experimental only (not wired into the pipeline).
        return {"provider": "seedance", "type": "tts", "model": SEED_AUDIO_MODEL, "text": text, "name": (name or "seed-audio")[:100],
                "output_format": output_format, "sample_rate": int(sample_rate), "speech_rate": 0, "loudness_rate": 0, "pitch_rate": 0,
                "enable_subtitle": bool(subtitles), "aigc_watermark": False, "references": refs}

    def generate_seed_audio(self, text: str, reference_audio_urls=(), reference_image_url: Optional[str] = None,
                            name: str = "seed-audio", subtitles: bool = True, sample_rate: int = 44100,
                            output_format: str = "mp3") -> str:
        """Submit one Seed Audio 1.0 track; returns the asset id (poll with status('tts', id))."""
        body = self.seed_audio_body(text, reference_audio_urls, reference_image_url, name, subtitles, sample_rate, output_format)
        data = self.client.post_json(PATH_GENERATE, body) or {}
        asset_id = data.get("asset_id")
        if asset_id is None:
            raise ProviderError("Seed Audio create returned no asset_id", code="bad_response")
        if data.get("status") == "failed":
            raise ProviderError(data.get("provider_error") or "Seed Audio creation failed", code="task_failed")
        return str(asset_id)

    def asset(self, category: str, asset_id: str) -> Optional[dict]:
        """The whole audio-list item (for fields status() does not keep, e.g. Seed Audio subtitle time stamps)."""
        for page in range(1, _PAGES + 1):
            data = self.client.get(PATH_LIST, {"category": category, "page": page, "page_size": 50}) or {}
            for item in data.get("items") or []:
                if str(item.get("id")) == str(asset_id):
                    return item
            if len(data.get("items") or []) < 50:
                break
        return None

    def generate_sfx(self, prompt: str, duration_seconds: Optional[float] = None, loop: bool = False,
                     name: str = "sfx") -> str:
        prompt = self._check_text("sound effect prompt", prompt)
        params: Dict = {"loop": bool(loop)}
        if duration_seconds is not None:
            params["duration_seconds"] = float(min(max(duration_seconds, 0.5), 30))
        return self._generate("sound_effect", name, DEFAULT_MODELS["sound_effect"], {"prompt": prompt}, params)

    def generate_tts(self, text: str, voice_actor_id: int, model: str = "eleven_v3",
                     language_code: Optional[str] = None, name: str = "tts", params: Optional[Dict] = None) -> str:
        """params: voice direction (core/voice_direction.py) — speed 0.7..1.2, stability / similarity_boost / style 0..1 (skill
        clipai-1.3.1 reference.md); a value out of range is refused here, before anything is paid."""
        text = self._check_text("TTS text", text)
        if model not in TTS_MODELS:
            raise ProviderError(f"unknown TTS model '{model}'. Allowed: {list(TTS_MODELS)}", code="unsupported_model")
        extra = {"language_code": language_code} if language_code else {}
        for key, (low, high) in TTS_PARAM_RANGES.items():
            if (params or {}).get(key) is None:
                continue
            value = params[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
                raise ProviderError(f"TTS {key}={value!r} ngoài khoảng {low}..{high}", code="bad_input")
            extra[key] = float(value)
        return self._generate("tts", name, model, {"text": text, "voice_actor_id": int(voice_actor_id)}, extra)

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
                     page_size: int = 100, game_code: Optional[str] = None) -> List[dict]:
        """Every page (the official library has 118 voices > one page of 100). `owner` only accepts 'official' (else code 1110);
        `game_code='FF'` lists the team's cloned voices (web: AI Audio → Voice Actors → FF), checked 2026-09-24."""
        out: List[dict] = []
        size = min(max(page_size, 1), 100)
        for page in range(1, _PAGES + 1):
            data = self.client.get(PATH_VOICES, {"owner": owner, "keyword": keyword, "game_code": game_code, "page": page,
                                                 "page_size": size}) or {}
            items = list(data.get("items") or [])
            out += items
            total = data.get("total")
            if len(items) < size or (isinstance(total, int) and len(out) >= total):
                break
        return out
