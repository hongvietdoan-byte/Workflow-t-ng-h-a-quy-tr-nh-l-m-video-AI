"""Step 5a extras: sound effects and voice-over (TTS) generated with Clip AI and mixed into the final video.

Assets live in `<data>/<project>/audio_assets/` (files + assets.json). Each finished asset can be switched on
for the mix with a start time (seconds from the beginning of the final video) and a volume. Failed assets are
reported and never resubmitted automatically (that would only burn credits).
"""
import json
import os
from typing import Dict, List, Optional

from .music import _ext, record_audio_usage
from .providers import ProviderError

KINDS = {"sound_effect": "SFX", "tts": "Giọng đọc"}


def assets_dir(data_dir: str, project_id: int) -> str:
    path = os.path.join(data_dir, str(project_id), "audio_assets")
    os.makedirs(path, exist_ok=True)
    return path


def _manifest(directory: str) -> str:
    return os.path.join(directory, "assets.json")


def load(directory: str) -> List[Dict]:
    try:
        with open(_manifest(directory), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(directory: str, items: List[Dict]) -> None:
    with open(_manifest(directory), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def _add(directory: str, kind: str, label: str, asset_id: Optional[str], message: Optional[str] = None) -> Dict:
    items = load(directory)
    entry = {"kind": kind, "label": label, "asset_id": asset_id, "file": None, "duration_ms": None,
             "state": "running" if asset_id else "failed", "message": message,
             "use": False, "start": 0.0, "volume": 1.0}
    items.append(entry)
    _save(directory, items)
    return entry


def add_local(directory: str, src_path: str, label: str, start: float = 0.0, volume: float = 1.0, duration_ms: Optional[int] = None) -> Dict:
    """Put a file of the person's own sound library into the mix (copied into the project, ready to use)."""
    import shutil
    ext = os.path.splitext(src_path)[1].lower()
    items = load(directory)
    n = len(items) + 1
    while os.path.exists(os.path.join(directory, f"local_{n}{ext}")):
        n += 1
    name = f"local_{n}{ext}"
    shutil.copyfile(src_path, os.path.join(directory, name))
    entry = {"kind": "sound_effect", "label": label, "asset_id": "local", "file": name, "duration_ms": duration_ms, "state": "succeeded",
             "message": None, "use": True, "start": max(float(start), 0.0), "volume": max(min(float(volume), 2.0), 0.0)}
    items.append(entry)
    _save(directory, items)
    return entry


def submit_sfx(provider, directory: str, prompt: str, duration_seconds: Optional[float] = None,
               loop: bool = False, ledger=None) -> Dict:
    try:
        asset_id = provider.generate_sfx(prompt, duration_seconds, loop, name="pipeline-sfx")
    except ProviderError as e:
        return _add(directory, "sound_effect", prompt, None, str(e))
    record_audio_usage(ledger, provider, "eleven_text_to_sound_v2")
    return _add(directory, "sound_effect", prompt, asset_id)


def submit_tts(provider, directory: str, text: str, voice_actor_id: int, voice_name: str = "",
               model: str = "eleven_v3", language_code: Optional[str] = None, ledger=None) -> Dict:
    label = (f"[{voice_name}] " if voice_name else "") + text
    try:
        asset_id = provider.generate_tts(text, voice_actor_id, model, language_code, name="pipeline-tts")
    except ProviderError as e:
        return _add(directory, "tts", label, None, str(e))
    record_audio_usage(ledger, provider, model)
    return _add(directory, "tts", label, asset_id)


def refresh(provider, directory: str) -> Dict[str, int]:
    """Poll every running asset once; download the finished ones."""
    items = load(directory)
    counts = {"running": 0, "succeeded": 0, "failed": 0}
    for e in items:
        if e["state"] == "running":
            try:
                st = provider.status(e["kind"], e["asset_id"])
                if st.state == "succeeded":
                    dest = os.path.join(directory, f"{e['kind']}_{e['asset_id']}.{_ext(provider)}")
                    provider.download(st.url, dest)
                    e.update(state="succeeded", file=os.path.basename(dest), duration_ms=st.duration_ms)
                elif st.state == "failed":
                    e.update(state="failed", message=st.message)
            except ProviderError as ex:
                if not ex.transient:
                    e.update(state="failed", message=str(ex))
        counts[e["state"]] = counts.get(e["state"], 0) + 1
    _save(directory, items)
    return counts


def set_mix(directory: str, index: int, use: bool, start: float, volume: float) -> None:
    items = load(directory)
    if use and items[index]["state"] != "succeeded":
        raise ValueError("only a finished asset can be used in the mix")
    items[index].update(use=bool(use), start=max(float(start), 0.0), volume=max(min(float(volume), 2.0), 0.0))
    _save(directory, items)


def remove(directory: str, index: int) -> None:
    items = load(directory)
    entry = items.pop(index)
    if entry.get("file"):
        try:
            os.remove(os.path.join(directory, entry["file"]))
        except OSError:
            pass
    _save(directory, items)


def mix_list(directory: str) -> List[Dict]:
    """Extras for the final render: finished assets switched on, in the order they were created."""
    return [{"path": os.path.join(directory, e["file"]), "start": e["start"], "volume": e["volume"]}
            for e in load(directory) if e["use"] and e["state"] == "succeeded" and e.get("file")
            and os.path.exists(os.path.join(directory, e["file"]))]
