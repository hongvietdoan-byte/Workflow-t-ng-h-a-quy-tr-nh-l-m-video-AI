"""AU-f: check every voiced dialogue line before it goes into a video — free, on this machine, no paid call.

Two layers:
1. Always (needs only ffmpeg): the voice's real length against the line's syllables (a voice far too short was cut; far too long
   rambles or repeats), and long silences inside it (a stall mid-sentence), via ffmpeg `silencedetect`.
2. When `faster-whisper` is installed (`pip install faster-whisper`, model downloaded once, runs offline): speech → text, compared
   word by word with the line (missing / wrong words, the end of the sentence cut off).

A line that fails is flagged (kept, never deleted); `redo()` makes it again on request. The automatic run does not redo on its own
until this check has passed a real test (rule 5 — `features.voice_check_redo`).
"""
import difflib
import os
import re
import subprocess
from typing import Callable, Dict, List, Optional

from . import audio_lib, dialogue, ffmpeg_studio

SYLL_PER_SEC_MAX = 6.5      # faster than this, words were dropped / the audio was cut (trial 2A: a cut Kenta line ran 7,8/s;
                            # normal Vietnamese TTS measured 2,9–5,7/s)
CHECK_VERSION = 2           # bump when the rules change, so lines checked under the old rules are checked again
TAIL_SEC, TAIL_DB = 0.08, -15.0   # the last 80 ms still this loud = the voice stops mid-word (trial 2A: -1,1 dB on the cut line;
                                  # clean endings measured -20 to -91 dB)
SYLL_PER_SEC_MIN = 1.6      # slower than this (after the fixed pause), the voice drags, repeats or trails off
EXTRA_SEC = 1.2             # breath + lead-in allowed on top of the slowest normal pace
SILENCE_DB = -40
SILENCE_MIN = 0.9           # a pause this long inside a line (not at its ends) is a stall
MATCH_MIN = 0.75            # heard words vs written words, below this the line is misread
_START = re.compile(r"silence_start:\s*([\d.]+)")
_END = re.compile(r"silence_end:\s*([\d.]+)")


# ---- layer 1: length + silences -------------------------------------------------------------------------------------
def silences(path: str) -> List[tuple]:
    """[(start, end)] of the silent stretches ffmpeg finds (empty when ffmpeg is missing)."""
    try:
        proc = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-hide_banner", "-nostats", "-i", path, "-af",
                               f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN}", "-f", "null", "-"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    except (ffmpeg_studio.FFmpegNotFound, OSError):
        return []
    starts = [float(x) for x in _START.findall(proc.stderr or "")]
    ends = [float(x) for x in _END.findall(proc.stderr or "")]
    return [(s, ends[i] if i < len(ends) else None) for i, s in enumerate(starts)]


_MAX_VOL = re.compile(r"max_volume:\s*(-?[\d.]+|-inf)\s*dB")


def tail_db(path: str, seconds: float = TAIL_SEC) -> Optional[float]:
    """Peak level (dBFS) of the last `seconds` of a voice file, or None when ffmpeg cannot tell."""
    try:
        proc = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-hide_banner", "-nostats", "-sseof", f"-{seconds}", "-i", path,
                               "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
    except (ffmpeg_studio.FFmpegNotFound, OSError):
        return None
    m = _MAX_VOL.search(proc.stderr or "")
    if not m:
        return None
    return -120.0 if m.group(1) == "-inf" else float(m.group(1))


def tail_problems(level: Optional[float]) -> List[str]:
    """Trial 2A: eleven_v3 now and then stops a short line mid-word; the file then ends at full loudness."""
    if level is not None and level > TAIL_DB:
        return [f"đuôi câu bị cắt (80 ms cuối vẫn to {level:.1f} dB) — tạo lại câu này"]
    return []


def length_problems(text: str, seconds: Optional[float], gaps: List[tuple]) -> List[str]:
    out = []
    syl = max(dialogue.syllables(text), 1)
    if seconds is None:
        return ["không đọc được độ dài file giọng"]
    if seconds < 0.3 or syl / seconds > SYLL_PER_SEC_MAX:
        out.append(f"giọng quá ngắn ({seconds:.1f}s cho {syl} âm tiết) — có thể bị cắt/thiếu chữ")
    elif seconds > syl / SYLL_PER_SEC_MIN + EXTRA_SEC:
        out.append(f"giọng quá dài ({seconds:.1f}s cho {syl} âm tiết) — có thể đọc lặp/kéo dài")
    for start, end in gaps:
        if end is None:
            if start < 0.2:
                out.append("gần như toàn im lặng")
            continue                                   # silence running to the end = tail, not a stall
        if start > 0.2 and end < seconds - 0.2:
            out.append(f"ngắt quãng {end - start:.1f}s giữa câu (giây {start:.1f})")
    return out


# ---- layer 2: speech to text ----------------------------------------------------------------------------------------
_model = None


def asr_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("faster_whisper") is not None
    except (ImportError, ValueError):
        return False


def transcribe(path: str) -> Optional[str]:
    """The words heard in the file (Vietnamese), or None when no speech-to-text is installed. Model: VOICE_ASR_MODEL (default 'small')."""
    global _model
    if not asr_available():
        return None
    from faster_whisper import WhisperModel   # noqa: PLC0415 - optional dependency
    if _model is None:
        _model = WhisperModel(os.environ.get("VOICE_ASR_MODEL", "small"), device="auto", compute_type="int8")
    segments, _ = _model.transcribe(path, language="vi", beam_size=5, vad_filter=False)
    return " ".join(s.text.strip() for s in segments).strip()


def _words(text: str) -> List[str]:
    return re.findall(r"\w+", (text or "").lower(), re.UNICODE)


def compare(written: str, heard: str) -> Dict:
    """{"score", "missing_end", "problems"} — how well the heard words follow the written line (accents kept: in Vietnamese they
    change the word)."""
    a, b = _words(written), _words(heard)
    if not a:
        return {"score": 1.0, "missing_end": False, "problems": []}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    score = sm.ratio()
    blocks = [m for m in sm.get_matching_blocks() if m.size]
    last = blocks[-1].a + blocks[-1].size if blocks else 0
    missing_end = len(a) - last >= max(2, len(a) // 5)
    problems = []
    if missing_end:
        problems.append("thiếu cuối câu: “" + " ".join(a[last:])[:60] + "”")
    if score < MATCH_MIN:
        problems.append(f"nghe ra khác câu gốc (khớp {score:.0%}): “{heard[:80]}”")
    return {"score": round(score, 3), "missing_end": missing_end, "problems": problems}


# ---- one line / a whole project -------------------------------------------------------------------------------------
def check_line(path: str, text: str, asr: Optional[Callable[[str], Optional[str]]] = transcribe) -> Dict:
    """{"ok", "problems", "seconds", "heard", "score", "asr"} for one voice file."""
    seconds = ffmpeg_studio.probe_duration(path)
    problems = length_problems(text, seconds, silences(path) if seconds else []) + (tail_problems(tail_db(path)) if seconds else [])
    heard = asr(path) if asr else None
    res = {"seconds": seconds, "heard": heard, "score": None, "asr": heard is not None}
    if heard is not None:
        cmp = compare(text, heard)
        res["score"] = cmp["score"]
        problems += cmp["problems"]
    res.update(ok=not problems, problems=problems)
    return res


def check_project(data_dir: str, project_id: int, asr: Optional[Callable[[str], Optional[str]]] = transcribe) -> Dict:
    """Check every finished dialogue voice not checked yet in its current form (same file + same text). The result is kept on the
    line (`check`) and shown in Step 3. Returns {"checked", "bad", "asr"}."""
    directory = audio_lib.assets_dir(data_dir, project_id)
    items = audio_lib.load(directory)
    checked = bad = 0
    for e in items:
        if e.get("kind") != "tts" or not e.get("dialogue") or e.get("state") != "succeeded" or not e.get("file"):
            continue
        path = os.path.join(directory, e["file"])
        if not os.path.exists(path):
            continue
        stamp = [e["file"], round(os.path.getmtime(path), 2), e.get("text"), asr_ready(asr), CHECK_VERSION]   # ASR / new rules re-check
        old = e.get("check") or {}
        if old.get("stamp") == stamp:
            bad += 0 if old.get("ok") else 1
            continue
        res = check_line(path, e.get("text") or "", asr if asr_ready(asr) else None)
        res["stamp"] = stamp
        e["check"] = res
        checked += 1
        bad += 0 if res["ok"] else 1
    audio_lib._save(directory, items)
    return {"checked": checked, "bad": bad, "asr": asr_ready(asr)}


def asr_ready(asr) -> bool:
    return asr is not None and (asr is not transcribe or asr_available())


def bad_lines(data_dir: str, project_id: int) -> List[Dict]:
    directory = audio_lib.assets_dir(data_dir, project_id)
    return [e for e in audio_lib.load(directory) if e.get("kind") == "tts" and e.get("dialogue")
            and (e.get("check") or {}).get("ok") is False]


def redo(conn, project_id: int, provider, data_dir: str) -> Dict:
    """Make the flagged lines again (one TTS call each — counted against the audio cap). Returns voice.generate's result."""
    from . import voice
    directory = audio_lib.assets_dir(data_dir, project_id)
    scene_ids = set()
    for i in reversed([i for i, e in enumerate(audio_lib.load(directory)) if e.get("kind") == "tts" and e.get("dialogue")
                       and (e.get("check") or {}).get("ok") is False]):
        scene_ids.add(audio_lib.load(directory)[i].get("scene_id"))
        audio_lib.remove(directory, i)
    if not scene_ids:
        return {"sent": 0, "skipped": 0, "no_voice": []}
    return voice.generate(conn, project_id, provider, data_dir, scene_ids=scene_ids, slow=scene_ids)
