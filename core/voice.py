"""Character voices (TTS) for the dialogue — the main way Vietnamese lines are spoken (the video models' own speech does not
cover Vietnamese reliably).

Each character has a `voice_profile` in the Character Bible ({"voice_id", "voice_name", "model", "persona"}). Every dialogue line
(core.dialogue.scene_lines) is voiced once with its speaker's voice; the REAL length of the voice then sets the clip length (instead
of a syllable estimate), and once the clips exist the lines are laid on the final timeline in speaking order without overlap —
which is also where the subtitles take their timing from.
"""
import json
import math
import os
from typing import Dict, List, Optional

from . import audio_lib, dialogue, ffmpeg_studio, final_cut

# AU-a (GĐ-G): Multilingual v2 has no Vietnamese in ElevenLabs' language list (29 languages) — the model guessed the language and
# Vietnamese lines came out with a foreign accent / wrong tones. v3 (70+ languages) and Turbo/Flash v2.5 list Vietnamese.
DEFAULT_MODEL = "eleven_v3"
VI_MODELS = ("eleven_v3", "eleven_flash_v2_5", "eleven_turbo_v2_5")


def vi_model(model: Optional[str]) -> str:
    """The TTS model used for a Vietnamese line: the saved one when it speaks Vietnamese, else the default (old profiles saved v2)."""
    return model if model in VI_MODELS else DEFAULT_MODEL
_PRON = os.path.join(os.path.dirname(__file__), "..", "data", "pronunciation_vi.json")
SAMPLE_VI = "Xin chào, tôi là {name}. Trận này mình đi loot trước rồi leo rank nhé, Booyah!"
LEAD = 0.3          # seconds of picture before the first line of a clip
TAIL = 0.4          # seconds after the last line
GAP = 0.15          # between two lines
J_LEAD = 0.25       # D1 (editing.md E1): a new speaker is heard this long before the cut to their shot (J-cut, ~6 frames at 24 fps)


def get_profile(row) -> Dict:
    try:
        return json.loads(row["voice_profile"] or "{}")
    except (ValueError, KeyError, IndexError, TypeError):
        return {}


def set_profile(conn, project_id: int, name: str, profile: Optional[Dict]) -> None:
    clean = None
    if profile and profile.get("voice_id"):
        clean = json.dumps({"voice_id": int(profile["voice_id"]), "voice_name": str(profile.get("voice_name") or ""),
                            "model": profile.get("model") or DEFAULT_MODEL, "persona": str(profile.get("persona") or "")},
                           ensure_ascii=False)
    conn.execute("UPDATE characters SET voice_profile=? WHERE project_id=? AND name=?", (clean, project_id, name))
    conn.commit()


def _norm(name: str) -> str:
    return " ".join((name or "").upper().split())


def profiles(conn, project_id: int) -> Dict[str, Dict]:
    """SPEAKER (upper case) -> voice profile, for characters that have one."""
    out = {}
    for r in conn.execute("SELECT name, voice_profile FROM characters WHERE project_id=?", (project_id,)):
        prof = get_profile(r)
        if prof.get("voice_id"):
            out[_norm(r["name"])] = prof
    return out


def planned_lines(conn, project_id: int) -> List[Dict]:
    """Every dialogue line of the project with the voice it will get (None when the speaker has no voice yet)."""
    voices = profiles(conn, project_id)
    out = []
    from . import voice_direction
    for s in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        data = json.loads(s["data"] or "{}")
        how = voice_direction.deliveries(data)
        for n, (who, said) in enumerate(dialogue.scene_lines(data), 1):
            out.append({"scene_id": s["id"], "idx": s["idx"], "line": n, "speaker": who, "text": said,
                        "voice": voices.get(_norm(who)), "delivery": how[n - 1] if n <= len(how) else None})
    return out


# ---- Vietnamese voices (kế hoạch v3, GĐ4 — API only) --------------------------------------------------------------------------
_VOICES_VI = os.path.join(os.path.dirname(__file__), "..", "data", "voices_vi.json")


def _clean_name(name) -> str:
    """'ClipAI_Voice Kelly VN' -> 'voice kelly vn' (the team voices come back with the 'ClipAI_' prefix)."""
    text = str(name or "").strip()
    if text.lower().startswith("clipai_"):
        text = text[len("clipai_"):]
    return " ".join(text.lower().split())


def voice_config() -> Dict:
    """data/voices_vi.json: the preferred Vietnamese voices (team clones with the 'VN' suffix, 2 male + 2 female) and the game codes
    whose team voices are listed. Read again only when the file changes (it is asked once per voice on every page draw)."""
    try:
        stamp = os.path.getmtime(_VOICES_VI)
    except OSError:
        return {}
    if _config_cache.get("stamp") != stamp:
        try:
            with open(_VOICES_VI, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        _config_cache.update(stamp=stamp, data=data if isinstance(data, dict) else {})
    return _config_cache["data"]


_config_cache: Dict = {}


def preferred(v: Dict) -> Optional[Dict]:
    """The preferred-voice entry this voice matches (by id or name), else None."""
    name = _clean_name(v.get("name"))
    for entry in voice_config().get("preferred") or []:
        if (entry.get("id") is not None and entry.get("id") == v.get("id")) or (entry.get("name") and _clean_name(entry["name"]) == name):
            return entry
    return None


def display_name(v: Dict) -> str:
    return str(v.get("name") or "").replace("ClipAI_", "", 1).strip()


def speaks_vi(v: Dict) -> bool:
    """A Clip AI voice that lists Vietnamese (`languages` or `labels.language`), or one of the preferred Vietnamese team voices
    (cloned voices come back with no language at all)."""
    langs = v.get("languages") or []
    labels = v.get("labels") if isinstance(v.get("labels"), dict) else {}
    return "vi" in langs or labels.get("language") == "vi" or preferred(v) is not None


def voice_gender(v: Dict) -> str:
    labels = v.get("labels") if isinstance(v.get("labels"), dict) else {}
    return (labels.get("gender") or (preferred(v) or {}).get("gender") or "").lower()


def vietnamese_first(voices: List[Dict]) -> List[Dict]:
    """The preferred Vietnamese team voices first (in the order of data/voices_vi.json), then the other voices that speak Vietnamese,
    then the rest — one entry per name (the library lists some twice under two ids)."""
    entries = voice_config().get("preferred") or []
    seen, pref, vi, other = set(), [], [], []
    for v in voices:
        key = _clean_name(v.get("name"))
        if key in seen:
            continue
        seen.add(key)
        (pref if preferred(v) else vi if speaks_vi(v) else other).append(v)
    pref.sort(key=lambda v: entries.index(preferred(v)))
    return pref + vi + other


def library(provider) -> List[Dict]:
    """Every voice the Dashboard can use: the official library (all pages) + the team voices of each game code in
    data/voices_vi.json (e.g. FF clones). A team list that cannot be read does not hide the official voices (reported by the caller
    only when everything fails)."""
    from .providers import ProviderError
    voices = list(provider.voice_actors(owner="official"))
    for code in voice_config().get("game_codes") or []:
        try:
            voices += [{**v, "team": code} for v in provider.voice_actors(game_code=code)]
        except ProviderError:
            continue
    return vietnamese_first(voices)


def casting_pool(voices: List[Dict]) -> List[Dict]:
    """AU-b: the voices offered for Vietnamese dialogue — only those listing Vietnamese. None -> empty (the caller says so) instead of
    silently casting a foreign voice to read Vietnamese."""
    return [v for v in vietnamese_first(voices) if speaks_vi(v)]


def pronunciation() -> Dict[str, str]:
    try:
        with open(_PRON, encoding="utf-8") as f:
            return dict(json.load(f).get("words") or {})
    except (OSError, ValueError):
        return {}


def speakable(text: str, words: Optional[Dict[str, str]] = None) -> str:
    """The text sent to TTS: English game words and names written the way a Vietnamese voice should say them (whole words,
    any case). The subtitles keep the original text."""
    import re
    words = pronunciation() if words is None else words
    for src in sorted(words, key=len, reverse=True):
        text = re.sub(r"(?<![\w])" + re.escape(src) + r"(?![\w])", words[src], text, flags=re.IGNORECASE)
    return text


def previews_dir(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "voice_previews")


def preview(provider, data_dir: str, project_id: int, voice_id: int, voice_name: str, character: str, ledger=None) -> Dict:
    """Voice one Vietnamese sample sentence with this voice (kept apart from the dialogue lines and the mix)."""
    directory = previews_dir(data_dir, project_id)
    os.makedirs(directory, exist_ok=True)
    text = speakable(SAMPLE_VI.format(name=character.title()))
    return audio_lib.submit_tts(provider, directory, text, voice_id, voice_name, DEFAULT_MODEL, None, ledger=ledger,
                                extra={"preview_for": character, "voice_id": voice_id})


def _line_items(directory: str) -> List[tuple]:
    return [(i, e) for i, e in enumerate(audio_lib.load(directory)) if e["kind"] == "tts" and e.get("scene_id")]


def slow_end(text: str) -> str:
    """The TTS text of a line being made again because its end was cut: a trailing "…" makes eleven_v3 finish the last word and let
    it fall (trial 2A, "Không liên quan đến ông.": 0,64 s cut mid-word → 1,12 s, 4,5 syllables/s, clean ending). Subtitles keep the line."""
    text = text.rstrip()
    return text if text.endswith(("…", "...")) else text.rstrip(".!?") + ("…" if not text.endswith(("!", "?")) else text[-1] + "…")


def generate(conn, project_id: int, provider, data_dir: str, scene_ids=None, ledger=True, slow=None) -> Dict:
    """Voice every line that has no voice yet (or whose text / voice changed). Returns {"sent", "skipped", "no_voice": [speakers]}.
    slow: scene ids whose lines are sent with a trailing "…" (a redo of a line whose end was cut)."""
    from . import features, voice_direction
    directory = audio_lib.assets_dir(data_dir, project_id)
    have = {(e["scene_id"], e.get("line")): (i, e) for i, e in _line_items(directory)}
    sent, skipped, no_voice = 0, 0, set()
    for ln in planned_lines(conn, project_id):
        if scene_ids is not None and ln["scene_id"] not in scene_ids:
            continue
        if not ln["voice"]:
            no_voice.add(ln["speaker"] or "(không tên)")
            continue
        model = vi_model(ln["voice"].get("model"))
        how = ln.get("delivery") if features.on("voice_direction") else None   # GĐ4: the Director's direction of the line
        old = have.get((ln["scene_id"], ln["line"]))
        if old is not None:
            i, e = old
            same = e.get("text") == ln["text"] and e.get("voice_id") == ln["voice"]["voice_id"] and e.get("delivery") == how
            if same and e["state"] in ("running", "succeeded"):
                skipped += 1
                continue
            audio_lib.remove(directory, i)                  # the line or the voice changed: make it again
            have = {(e2["scene_id"], e2.get("line")): (j, e2) for j, e2 in _line_items(directory)}
        extra = {"scene_id": ln["scene_id"], "scene_idx": ln["idx"], "line": ln["line"], "speaker": ln["speaker"],
                 "text": ln["text"], "voice_id": ln["voice"]["voice_id"], "dialogue": True}
        said = speakable(ln["text"])
        if slow and ln["scene_id"] in slow:
            said = slow_end(said)
            extra["slow_end"] = True
        if how:
            extra["delivery"] = how
            said = voice_direction.spoken_text(said, how, model)
        audio_lib.submit_tts(provider, directory, said, ln["voice"]["voice_id"], ln["voice"].get("voice_name", ""),
                             model, None, ledger=(conn, project_id) if ledger else None,
                             extra=extra, params=voice_direction.params(how, model))
        sent += 1
    return {"sent": sent, "skipped": skipped, "no_voice": sorted(no_voice)}


def scene_seconds(conn, project_id: int, data_dir: str) -> Dict[int, float]:
    """scene_id -> seconds the voiced lines need (lines + gaps), only for scenes whose every line has a finished voice."""
    directory = audio_lib.assets_dir(data_dir, project_id)
    done: Dict[int, List[float]] = {}
    for _, e in _line_items(directory):
        if e["state"] == "succeeded" and e.get("duration_ms"):
            done.setdefault(e["scene_id"], []).append(e["duration_ms"] / 1000.0)
    expected: Dict[int, int] = {}
    for ln in planned_lines(conn, project_id):
        expected[ln["scene_id"]] = expected.get(ln["scene_id"], 0) + 1
    return {sid: round(sum(d) + GAP * (len(d) - 1), 2) for sid, d in done.items() if len(d) >= expected.get(sid, 0)}


def fit_durations(conn, project_id: int, data_dir: str) -> List[Dict]:
    """Size each voiced scene's clip to its real voice (lead + lines + tail), within what the scene's model can make.
    Only lengthens (a longer clip than the voice is fine). Returns the changes."""
    from .dialogue import max_clip_seconds
    from .pipeline import Pipeline
    changes = []
    p = Pipeline(conn)
    for sid, secs in scene_seconds(conn, project_id, data_dir).items():
        row = conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        if row is None:
            continue
        need = math.ceil(LEAD + secs + TAIL)
        target = min(need, max_clip_seconds(p, project_id, sid))
        if target > float(row["duration_sec"] or 0):
            conn.execute("UPDATE motion_prompts SET duration_sec=? WHERE scene_id=?", (target, sid))
            changes.append({"scene_id": sid, "from": row["duration_sec"], "to": target, "short": need > target})
    conn.commit()
    return changes


def place_on_timeline(conn, project_id: int, data_dir: str, transition: str = "cut", fade: float = 1.0,
                      clip_paths: Optional[List[str]] = None, durations: Optional[List[float]] = None) -> int:
    """Put every voiced line on the final video's timeline: inside its scene's clip, in speaking order, never overlapping the
    previous line's real audio; switch it on for the mix. Returns how many lines were placed.
    durations: the seconds each clip gets in the render (D2: the edited ones), else each clip's real length."""
    directory = audio_lib.assets_dir(data_dir, project_id)
    items = audio_lib.load(directory)
    clips = [c for c in final_cut.collect_clips_for_render(conn, data_dir, project_id, clip_paths)]
    if durations is not None and len(durations) == len(clips):
        clips = [{**c, "_seconds": float(d)} for c, d in zip(clips, durations)]
    rendered = {c.get("scene_id") for c in clips}
    for e in items:                                  # D1: the lines of a clip left out of this render must not play at old times
        if e["kind"] == "tts" and e.get("dialogue") and e.get("scene_id") not in rendered:
            e["use"] = False
    overlap = fade if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    from . import lipsync
    synced = lipsync.synced_scene_ids(data_dir, project_id)
    from . import features
    j_cut = features.on("j_cut")
    t, placed, prev_end, prev_speaker = 0.0, 0, -1.0, None
    for clip in clips:
        length = clip.get("_seconds") or final_cut.clip_seconds(clip["path"], clip["requested_sec"])
        lines = sorted([e for e in items if e["kind"] == "tts" and e.get("scene_id") == clip.get("scene_id")
                        and e["state"] == "succeeded" and e.get("file")], key=lambda e: e.get("line") or 0)
        # a lip-synced clip speaks its lines at fixed seconds (lipsync.shot_audio): they are laid there, never pushed later
        cursor = t + LEAD if clip.get("scene_id") in synced else max(t + LEAD, prev_end + GAP)
        if (j_cut and lines and t > 0 and clip.get("scene_id") not in synced and prev_speaker
                and (lines[0].get("speaker") or "") != prev_speaker):
            cursor = max(t - J_LEAD, prev_end + GAP)          # never over the previous line's real audio
        for e in lines:
            e.update(start=round(cursor, 2), use=True)
            cursor += (e.get("duration_ms") or 0) / 1000.0 + GAP
            prev_end = cursor - GAP
            prev_speaker = e.get("speaker") or prev_speaker
            placed += 1
        t += length - overlap
    audio_lib._save(directory, items)
    return placed


def cues(conn, project_id: int, data_dir: str) -> List:
    """Subtitle cues taken from the placed voice lines (exact timing); empty when no line is voiced."""
    from .subtitles import Cue
    out = []
    for _, e in _line_items(audio_lib.assets_dir(data_dir, project_id)):
        if e["state"] == "succeeded" and e.get("use") and e.get("duration_ms"):
            out.append(Cue(round(e["start"], 2), round(e["start"] + e["duration_ms"] / 1000.0, 2), e.get("text") or "",
                           e.get("speaker") or "", e.get("scene_idx")))
    return sorted(out, key=lambda c: c.start)


def status(conn, project_id: int, data_dir: str) -> Dict:
    """For the dashboard: lines total / voiced / running / failed / speakers without a voice."""
    directory = audio_lib.assets_dir(data_dir, project_id)
    planned = planned_lines(conn, project_id)
    made = {(e["scene_id"], e.get("line")): e for _, e in _line_items(directory)}
    counts = {"total": len(planned), "succeeded": 0, "running": 0, "failed": 0, "missing": 0}
    for ln in planned:
        e = made.get((ln["scene_id"], ln["line"]))
        if e is None or e.get("text") != ln["text"]:
            counts["missing"] += 1
        else:
            counts[e["state"]] = counts.get(e["state"], 0) + 1
    counts["no_voice"] = sorted({ln["speaker"] or "(không tên)" for ln in planned if not ln["voice"]})
    return counts


def exists_file(data_dir: str, project_id: int, entry: Dict) -> bool:
    return bool(entry.get("file")) and os.path.exists(os.path.join(audio_lib.assets_dir(data_dir, project_id), entry["file"]))


def timeline_extras(conn, project_id: int, data_dir: str, scene_seconds_list) -> List[Dict]:
    """Voice lines laid on a timeline made of [(scene_id, seconds), ...] (e.g. the animatic), as mix extras — without changing the
    saved placement of the final render."""
    directory = audio_lib.assets_dir(data_dir, project_id)
    items = [e for _, e in _line_items(directory) if e["state"] == "succeeded" and e.get("file")]
    out, t, prev_end = [], 0.0, -1.0
    for sid, seconds in scene_seconds_list:
        cursor = max(t + LEAD, prev_end + GAP)
        for e in sorted([e for e in items if e.get("scene_id") == sid], key=lambda e: e.get("line") or 0):
            path = os.path.join(directory, e["file"])
            if os.path.exists(path):
                out.append({"path": path, "start": round(cursor, 2), "volume": 1.0})
            cursor += (e.get("duration_ms") or 0) / 1000.0 + GAP
            prev_end = cursor - GAP
        t += seconds
    return out
