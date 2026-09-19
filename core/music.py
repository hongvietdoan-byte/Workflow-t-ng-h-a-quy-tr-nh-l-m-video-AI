"""Step 5a background music: brief -> N drafts (Clip AI music) -> pick one for the final mix.

Drafts live in `<data>/<project>/music_drafts/` (files + drafts.json); the chosen track is copied to
`<data>/<project>/music/selected.<ext>`, which is the only file the render step reads.
A failed draft is reported and never resubmitted automatically (it would only burn credits).
"""
import json
import math
import os
import shutil
import struct
import wave
from typing import Dict, List, Optional

from .pipeline import Pipeline
from .providers import ProviderError

MIN_MS, MAX_MS = 3000, 600000


class MockAudioProvider:
    """Simulates the audio provider: every asset succeeds on the first poll with a short generated tone."""
    name = "mock-audio"
    file_ext = "wav"

    def __init__(self):
        self._assets: Dict[str, dict] = {}
        self._next = 1

    def _create(self, category: str, ms: int) -> str:
        asset_id = str(self._next)
        self._next += 1
        self._assets[f"{category}:{asset_id}"] = {"ms": ms}
        return asset_id

    def generate_music(self, prompt, length_ms=None, instrumental=True, name="music"):
        return self._create("music", min(int(length_ms or 4000), 4000))

    def generate_sfx(self, prompt, duration_seconds=None, loop=False, name="sfx"):
        return self._create("sound_effect", int((duration_seconds or 1) * 1000))

    def generate_tts(self, text, voice_actor_id, model="eleven_v3", language_code=None, name="tts"):
        return self._create("tts", 1500)

    def status(self, category, asset_id):
        from .adapters.clipai_audio import AudioStatus
        asset = self._assets.get(f"{category}:{asset_id}", {"ms": 4000})  # dashboard reruns build a fresh mock
        return AudioStatus("succeeded", f"mock://{category}/{asset_id}", asset["ms"])

    def download(self, url, dest_path):
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with wave.open(dest_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            frames = b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 440 * i / 8000)))
                              for i in range(8000))
            w.writeframes(frames)
        return dest_path

    def voice_actors(self, owner=None, keyword=None, page_size=100):
        return [{"id": 1, "name": "Mock voice", "library_scope": "official"}]


def audio_provider():
    """AUDIO_PROVIDER = clipai | mock. Unset: follows VIDEO_PROVIDER=clipai (same token); else not configured."""
    kind = os.environ.get("AUDIO_PROVIDER", "").strip().lower()
    if not kind and os.environ.get("VIDEO_PROVIDER", "").strip().lower() == "clipai":
        kind = "clipai"
    if kind == "mock":
        return MockAudioProvider()
    if kind == "clipai":
        from .adapters.clipai_audio import ClipAIAudioProvider
        return ClipAIAudioProvider.from_env()
    return None


def _ext(provider) -> str:
    return getattr(provider, "file_ext", "mp3")


def project_dirs(data_dir: str, project_id: int):
    base = os.path.join(data_dir, str(project_id))
    drafts, selected = os.path.join(base, "music_drafts"), os.path.join(base, "music")
    os.makedirs(drafts, exist_ok=True)
    os.makedirs(selected, exist_ok=True)
    return drafts, selected


def total_duration_sec(pipeline: Pipeline, project_id: int) -> float:
    row = pipeline.conn.execute(
        "SELECT SUM(m.duration_sec) total FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=?", (project_id,)).fetchone()
    return float(row["total"] or 0)


def scene_moods(pipeline: Pipeline, project_id: int) -> List[str]:
    moods = []
    for row in pipeline.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)):
        mood = (json.loads(row["data"] or "{}") or {}).get("mood")
        if mood and mood not in moods:
            moods.append(mood)
    return moods


def default_brief(pipeline: Pipeline, project_id: int) -> Dict:
    """Editable starting point built from the scene moods and total length (the user refines it)."""
    moods = scene_moods(pipeline, project_id)
    seconds = total_duration_sec(pipeline, project_id) or 30
    prompt = ("Instrumental background music for a short cinematic video. Mood progression: "
              + (" -> ".join(moods) if moods else "calm, then building tension")
              + ". No vocals, steady pulse, room for sound effects.")
    return {"prompt": prompt, "length_ms": int(min(max(seconds * 1000, MIN_MS), MAX_MS)), "instrumental": True}


# ---- drafts manifest -------------------------------------------------------
def _manifest(drafts_dir: str) -> str:
    return os.path.join(drafts_dir, "drafts.json")


def load_drafts(drafts_dir: str) -> List[Dict]:
    try:
        with open(_manifest(drafts_dir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(drafts_dir: str, drafts: List[Dict]) -> None:
    with open(_manifest(drafts_dir), "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=1)


def submit_drafts(provider, drafts_dir: str, prompt: str, length_ms: Optional[int], instrumental: bool,
                  count: int = 3) -> int:
    """Submit `count` drafts; stops on the first submission error (kept in the manifest) and returns how many went out."""
    drafts = load_drafts(drafts_dir)
    sent = 0
    for _ in range(count):
        try:
            asset_id = provider.generate_music(prompt, length_ms, instrumental, name="pipeline-music")
        except ProviderError as e:
            drafts.append({"asset_id": None, "state": "failed", "message": str(e), "prompt": prompt, "file": None})
            break
        drafts.append({"asset_id": asset_id, "state": "running", "message": None, "prompt": prompt,
                       "length_ms": length_ms, "file": None})
        sent += 1
    _save(drafts_dir, drafts)
    return sent


def refresh_drafts(provider, drafts_dir: str) -> Dict[str, int]:
    """Poll every running draft once; download the audio of the ones that finished."""
    drafts = load_drafts(drafts_dir)
    counts = {"running": 0, "succeeded": 0, "failed": 0}
    for i, d in enumerate(drafts):
        if d["state"] == "running":
            try:
                st = provider.status("music", d["asset_id"])
                if st.state == "succeeded":
                    dest = os.path.join(drafts_dir, f"draft_{d['asset_id']}.{_ext(provider)}")
                    provider.download(st.url, dest)
                    d.update(state="succeeded", file=os.path.basename(dest), duration_ms=st.duration_ms)
                elif st.state == "failed":
                    d.update(state="failed", message=st.message)
            except ProviderError as e:
                if not e.transient:
                    d.update(state="failed", message=str(e))
        counts[d["state"]] = counts.get(d["state"], 0) + 1
    _save(drafts_dir, drafts)
    return counts


def select_draft(drafts_dir: str, selected_dir: str, index: int) -> str:
    draft = load_drafts(drafts_dir)[index]
    if draft["state"] != "succeeded" or not draft.get("file"):
        raise ValueError("this draft has no finished audio")
    clear_selected(selected_dir)
    src = os.path.join(drafts_dir, draft["file"])
    dest = os.path.join(selected_dir, "selected" + os.path.splitext(src)[1])
    shutil.copyfile(src, dest)
    return dest


def clear_selected(selected_dir: str) -> None:
    for name in os.listdir(selected_dir):
        os.remove(os.path.join(selected_dir, name))
