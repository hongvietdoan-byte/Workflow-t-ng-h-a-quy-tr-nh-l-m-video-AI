"""Step 5a extras: sound effects and voice-over (TTS) generated with Clip AI and mixed into the final video.

Assets live in `<data>/<project>/audio_assets/` (files + assets.json). Each finished asset can be switched on
for the mix with a start time (seconds from the beginning of the final video) and a volume. Failed assets are
reported and never resubmitted automatically (that would only burn credits).
"""
import json
import os
from typing import Dict, List, Optional

from . import access
from .music import _ext, audio_refusal, record_audio_usage
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


def _add(directory: str, kind: str, label: str, asset_id: Optional[str], message: Optional[str] = None,
         extra: Optional[Dict] = None) -> Dict:
    items = load(directory)
    entry = {"kind": kind, "label": label, "asset_id": asset_id, "file": None, "duration_ms": None,
             "state": "running" if asset_id else "failed", "message": message,
             "use": False, "start": 0.0, "volume": 1.0, **(extra or {})}
    items.append(entry)
    _save(directory, items)
    return entry


def add_local(directory: str, src_path: str, label: str, start: float = 0.0, volume: float = 1.0, duration_ms: Optional[int] = None,
              extra: Optional[Dict] = None) -> Dict:
    """Put a file of the person's own sound library into the mix (copied into the project, ready to use). `extra`: more fields of the
    entry (e.g. the shot an AI-placed effect belongs to: anchor_idx + offset)."""
    import shutil
    ext = os.path.splitext(src_path)[1].lower()
    items = load(directory)
    n = len(items) + 1
    while os.path.exists(os.path.join(directory, f"local_{n}{ext}")):
        n += 1
    name = f"local_{n}{ext}"
    shutil.copyfile(src_path, os.path.join(directory, name))
    entry = {"kind": "sound_effect", "label": label, "asset_id": "local", "file": name, "duration_ms": duration_ms, "state": "succeeded",
             "message": None, "use": True, "start": max(float(start), 0.0), "volume": max(min(float(volume), 2.0), 0.0), **(extra or {})}
    items.append(entry)
    _save(directory, items)
    return entry


def submit_sfx(provider, directory: str, prompt: str, duration_seconds: Optional[float] = None,
               loop: bool = False, ledger=None, p=None, project_id=None) -> Dict:
    if p is not None and project_id is not None:
        access.need_edit(p, project_id, "gửi hiệu ứng âm thanh")
    refused = audio_refusal(ledger, provider)
    if refused:
        return _add(directory, "sound_effect", prompt, None, refused)
    try:
        asset_id = provider.generate_sfx(prompt, duration_seconds, loop, name="pipeline-sfx")
    except ProviderError as e:
        return _add(directory, "sound_effect", prompt, None, str(e))
    record_audio_usage(ledger, provider, "eleven_text_to_sound_v2")
    return _add(directory, "sound_effect", prompt, asset_id)


def submit_tts(provider, directory: str, text: str, voice_actor_id: int, voice_name: str = "",
               model: str = "eleven_v3", language_code: Optional[str] = None, ledger=None, extra: Optional[Dict] = None,
               params: Optional[Dict] = None, p=None, project_id=None) -> Dict:
    """`extra` tags a dialogue line (scene_id, line, speaker, text, voice_id) so it can be placed on the timeline and
    subtitled from its real timing. Do not pass language_code for Vietnamese: ElevenLabs answers HTTP 400 (auto-detect works)."""
    if p is not None and project_id is not None:
        access.need_edit(p, project_id, "gửi giọng đọc")
    label = (f"[{voice_name}] " if voice_name else "") + text
    refused = audio_refusal(ledger, provider)
    if refused:                                  # never sent (spending cap / ledger): not a provider failure, nothing was paid
        return _add(directory, "tts", label, None, refused, {**(extra or {}), "refused": True})
    try:
        asset_id = (provider.generate_tts(text, voice_actor_id, model, language_code, name="pipeline-tts", params=params) if params
                    else provider.generate_tts(text, voice_actor_id, model, language_code, name="pipeline-tts"))
    except ProviderError as e:
        return _add(directory, "tts", label, None, str(e), {**(extra or {}), "error_code": e.code, "transient": bool(e.transient)})
    record_audio_usage(ledger, provider, model)
    return _add(directory, "tts", label, asset_id, extra=extra)


def mix_rows(items: List[Dict]) -> List[tuple]:
    """(index, entry) of the sound list shown in Bước 5 — without an old voice kept while its redo is made (voice_check
    'superseded': not in the mix, not to be deleted by hand; it goes or comes back by itself). Indexes stay those of `items`."""
    return [(i, e) for i, e in enumerate(items) if e.get("state") != "superseded"]


def update(directory: str, index: int, **fields) -> None:
    items = load(directory)
    items[index].update(fields)
    _save(directory, items)


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
                    e.update(state="failed", message=st.message, provider_failed=True)   # made and failed at the provider
            except ProviderError as ex:
                if not ex.transient:
                    e.update(state="failed", message=str(ex), error_code=ex.code, transient=False)
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


SFX_UNDER_SPEECH = 0.5     # trial #8 (2026-09-28): gunshot + impact + beep (peaks -6 / -0.4 / -4 dBFS) summed over a voice line at -0.3 dBFS,
                           # then squeezed by the peak limiter = the "tiếng rè" at 43 s. An effect that plays over a spoken line is halved.


def mix_list(directory: str) -> List[Dict]:
    """Extras for the final render: finished assets switched on, in the order they were created. A sound effect that overlaps a
    voice line switched on for the mix plays at SFX_UNDER_SPEECH of its volume (the words stay clear, the limiter is not driven hard)."""
    items = [e for e in load(directory) if e["use"] and e["state"] == "succeeded" and e.get("file")
             and os.path.exists(os.path.join(directory, e["file"]))]
    speech = [(e["start"], e["start"] + _duration(e)) for e in items if e["kind"] == "tts" and _duration(e) > 0]
    out = []
    for e in items:
        volume = e["volume"]
        if e["kind"] == "sound_effect":
            a, b = e["start"], e["start"] + (_duration(e) or 0.5)
            if any(a < y and x < b for x, y in speech):
                volume = round(volume * SFX_UNDER_SPEECH, 3)
        out.append({"path": os.path.join(directory, e["file"]), "start": e["start"], "volume": volume})
    return out


def missing_in_mix(directory: str) -> List[str]:
    """S14.4 C1b: labels of the finished sounds switched on for the mix whose file is gone — mix_list leaves them out, the render
    says so (diag) instead of shipping a video without them silently."""
    return [str(e.get("label") or e.get("file") or "?") for e in load(directory)
            if e["use"] and e["state"] == "succeeded" and (not e.get("file") or not os.path.exists(os.path.join(directory, e["file"])))]


def _duration(e: Dict) -> float:
    return (e.get("duration_ms") or 0) / 1000.0


def overlapping_tts(directory: str) -> List[Dict]:
    """Pairs of consecutive voice-over lines switched on for the mix whose REAL audio overlaps in time (two
    people talking at once): the final mix (`core/ffmpeg_studio.py::build_extras_mix_cmd`) just adds every
    track's waveform together with no ducking, so an overlap here is audible as cross-talk in the rendered
    video. Empty when nothing overlaps."""
    items = load(directory)
    on = sorted([(i, e) for i, e in enumerate(items) if e["kind"] == "tts" and e["use"] and e["state"] == "succeeded"],
               key=lambda pair: pair[1]["start"])
    out = []
    for (i, a), (j, b) in zip(on, on[1:]):
        a_end = a["start"] + _duration(a)
        if b["start"] < a_end - 1e-9:
            out.append({"a": i, "b": j, "overlap": round(a_end - b["start"], 2)})
    return out


def schedule_by_cues(directory: str, cues, min_gap: float = 0.12) -> int:
    """Move every voice-over line to a start time that follows speaking order without overlapping the previous
    line's REAL audio.

    The start time a person types (or a script computes) before the voice exists is only an estimate — usually
    `core/subtitles.py::build_cues()`, which shares out a scene's already-fixed clip length by syllable count.
    ElevenLabs often takes longer than that estimate to say the line, so the next cue's start (unaware of this)
    can land before the previous line finished (measured on a real render: 8 of 13 line-to-line joins
    overlapped, up to 1.29s — see PLAN.md 3.7b). This walks the cues in speaking order and pushes each line's
    start to `max(its own cue estimate, previous line's real end + min_gap)`, using the REAL `duration_ms` that
    came back from the provider, not the estimate.

    Matches each cue to the voice-over asset with the same line (the label after "[Voice name] "); a cue with
    no matching finished asset, or an asset already used by an earlier cue, is left alone. Returns how many
    starts were changed."""
    items = load(directory)
    by_text: Dict[str, List[int]] = {}
    for i, e in enumerate(items):
        if e["kind"] == "tts" and e["state"] == "succeeded":
            text = e["label"].split("] ", 1)[-1].strip()
            by_text.setdefault(text, []).append(i)
    changed = 0
    end = -min_gap                     # so the first line isn't pushed past its own cue start by the gap
    for cue in sorted(cues, key=lambda c: c.start):
        pool = by_text.get(cue.text.strip())
        if not pool:
            continue
        e = items[pool.pop(0)]
        new_start = round(max(cue.start, end + min_gap), 2)
        end = new_start + _duration(e)
        if not e["use"] or abs(e["start"] - new_start) > 1e-9:
            e.update(use=True, start=new_start)
            changed += 1
    if changed:
        _save(directory, items)
    return changed
