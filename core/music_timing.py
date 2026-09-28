"""Nhạc nền theo nhịp của bản dựng (người dùng 2026-09-25: "chưa có nhạc nền theo nhịp độ của clip").

The music brief is built by code from the REAL timeline (each shot's clip length after the voices stretched it, the script sections and
their mood), not from planned seconds: section boundaries become the music's turns, and the tempo is chosen so those turns land on a bar
line. No Claude call. The Dashboard / tools send the prompt to the music model (ClipAI · ElevenLabs music) and duck it under dialogue
when mixing (ffmpeg_studio.build_extras_mix_cmd(duck=True)).

    sections(p, pid)            [{scene, heading, start, end, mood, intent, spoken}]
    choose_bpm(times)           (bpm, worst error in seconds) — the turns on bar lines (4 beats)
    brief(p, pid)               {"prompt", "bpm", "length_ms", "sections", "turns", "error_s"}
"""
import json
import re
from typing import Dict, List, Optional, Sequence, Tuple

from .pipeline import Pipeline

BPM_RANGE = (70, 140)
SAD = re.compile(r"grief|sad|heartbr|tear|cry|lonely|melanch|sorrow|restrained|tender|bittersweet|buồn|khóc", re.I)
TENSE = re.compile(r"tens|urgent|action|fight|run|chase|suspic|curio|conflict|anger|angry|shock|twist|căng|gấp", re.I)
WARM = re.compile(r"warm|reunion|hope|love|relief|smile|embrace|ôm|ấm", re.I)


def sections(p: Pipeline, pid: int) -> List[Dict]:
    """The script sections on the real timeline: each shot lasts its clip's cut length (motion prompt duration, stretched to the voice)."""
    rows = p.conn.execute("SELECT s.id, s.idx, s.data, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id "
                          "WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    heads = {r["idx"]: r["heading"] for r in p.conn.execute("SELECT idx, heading FROM story_scenes WHERE project_id=?", (pid,))}
    out: List[Dict] = []
    t = 0.0
    for r in rows:
        d = json.loads(r["data"] or "{}")
        dur = float(r["duration_sec"] or d.get("duration_s") or 0)
        sc = d.get("story_scene") or r["idx"]
        if not out or out[-1]["scene"] != sc:
            out.append({"scene": sc, "heading": heads.get(sc, ""), "start": round(t, 2), "end": round(t, 2),
                        "mood": str(d.get("mood") or ""), "intent": str(d.get("emotional_intent") or ""),
                        "lighting": str(d.get("lighting") or ""), "spoken": 0.0})
        out[-1]["end"] = round(t + dur, 2)
        if d.get("dialogue"):
            out[-1]["spoken"] = round(out[-1]["spoken"] + dur, 2)
        t += dur
    return out


def choose_bpm(times: Sequence[float], lo: int = BPM_RANGE[0], hi: int = BPM_RANGE[1]) -> Tuple[int, float]:
    """The tempo whose bar lines (4 beats) fall closest to every turn (the worst miss is kept small); ties go to the middle tempo."""
    best = (lo, float("inf"))
    for bpm in range(lo, hi + 1):
        bar = 4 * 60.0 / bpm
        err = max((abs(t - round(t / bar) * bar) for t in times), default=0.0)
        if err < best[1] - 1e-6 or (abs(err - best[1]) < 1e-6 and abs(bpm - 100) < abs(best[0] - 100)):
            best = (bpm, err)
    return best[0], round(best[1], 3)


ACTION = re.compile(r"action|fight|chase|run|gameplay|battle|shoot|đánh|đuổi|chạy|bắn", re.I)


def _style(sec: Dict, bpm: int = 100) -> str:
    text = " ".join((sec["mood"], sec["intent"], sec["heading"], sec["lighting"]))
    half = " (half-time feel)" if bpm > 90 else ""
    if WARM.search(text) and not ACTION.search(text):
        return "warm, tender strings and soft piano, hopeful and resolving" + half
    if SAD.search(text) and not ACTION.search(text):      # "heartbroken, tense, restrained grief" is grief, not action
        return "sparse, emotional solo piano with soft cold string pads, slow and restrained, lots of space" + half
    if TENSE.search(text) or "gameplay" in text.lower() or "game_tps" in text.lower():
        return "tense, driving hybrid score: pulsing low synth bass, tight electronic percussion and light orchestral hits"
    return "understated cinematic underscore, soft pads and light percussion"


TAIL_PAD_MS = 4000      # the music model always fades its last ~5 s (trial 2A drafts): ask for 4 s more, the mix cuts at the film's end


def loudness(path: str, step: float = 0.5) -> List[float]:
    """dBFS per `step` seconds of an audio file (ffmpeg decode, no extra library)."""
    import array
    import math
    import subprocess
    from .ffmpeg_studio import find_ffmpeg
    raw = subprocess.run([find_ffmpeg(), "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    a = array.array("h", raw)
    n = int(8000 * step)
    return [20 * math.log10(max(1e-9, math.sqrt(sum(x * x for x in a[i:i + n]) / n) / 32768)) for i in range(0, len(a) - n + 1, n)]


def score_draft(path: str, turns: Sequence[float], total: float, step: float = 0.5) -> Dict:
    """How well a finished draft follows the cut: the level should RISE (or change clearly) at each section turn, and the music must
    still be playing near the film's end (not already faded). Trial 2A: of two drafts, one had no turn at 8,6 s at all."""
    db = loudness(path, step)
    if not db:
        return {"score": -99.0, "turn_jumps": [], "end_drop": 99.0}
    at = lambda t: max(0, min(len(db) - 1, int(t / step)))  # noqa: E731
    jumps = []
    for t in turns:
        before = sum(db[at(t - 2.0):at(t)]) / max(1, len(db[at(t - 2.0):at(t)]))
        after = max(db[at(t):at(t + 1.0) + 1])
        jumps.append(round(after - before, 1))
    mid = sorted(db[: at(total)])[len(db[: at(total)]) // 2] if at(total) > 0 else db[0]
    end = sum(db[at(total - 1.5):at(total)]) / max(1, len(db[at(total - 1.5):at(total)]))
    drop = round(mid - end, 1)
    score = sum(min(j, 8.0) for j in jumps) - max(0.0, drop - 3.0)
    return {"score": round(score, 1), "turn_jumps": jumps, "end_drop": drop}


def _clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def brief(p: Pipeline, pid: int) -> Dict:
    secs = sections(p, pid)
    total = secs[-1]["end"] if secs else 0.0
    turns = [s["start"] for s in secs[1:]]
    bpm, err = choose_bpm(turns)
    parts = []
    for s in secs:
        parts.append(f"{_clock(s['start'])}–{_clock(s['end'])}: {_style(s, bpm)}"
                     + (" (dialogue over it: keep the mid frequencies clear, no melody lead)" if s["spoken"] > 0.4 * (s["end"] - s["start"]) else ""))
    prompt = (f"Instrumental score for a {total:.0f}-second vertical Free Fire short drama, {bpm} BPM throughout so every change lands "
              f"on a bar line. " + " ".join(parts)
              # #8 (người dùng 2026-09-28): "nhạc vào không hợp lý, không có độ mềm mại" — a turn flows in over about a bar, the new
              # mood arriving on its time (music_fit reads these times back to move the sections onto the scenes as really cut)
              + (" Each section flows into the next over about one bar, the new mood arriving exactly at its time (" + ", ".join(_clock(t) for t in turns)
                 + ") — follow the story's emotion, no abrupt stops or jarring jumps." if turns else "")
              + f" End cleanly on a final hit at {_clock(total)}, no long tail. No vocals, no lyrics.")
    return {"prompt": prompt[:1500], "bpm": bpm, "error_s": err, "length_ms": int(round(total * 1000)) + TAIL_PAD_MS, "film_s": total,
            "sections": secs, "turns": turns}


def timed_brief(p: Pipeline, pid: int) -> Optional[Dict]:
    """The brief of `brief` in the shape music.submit_drafts / the Step 5 form use ({"prompt", "length_ms", "instrumental"} + bpm,
    turns, film_s), or None when the project has no timeline yet (no shot has a length)."""
    b = brief(p, pid)
    if not b["film_s"]:
        return None
    return {**b, "instrumental": True, "timed": True}


def pick_best(paths: Sequence[str], turns: Sequence[float], total: float) -> Optional[int]:
    """Index of the draft whose changes land best on the section turns (score_draft); None when none can be measured (no ffmpeg)."""
    best, best_score = None, None
    for i, path in enumerate(paths):
        try:
            score = score_draft(path, turns, total)["score"]
        except Exception:  # noqa: BLE001 - a draft that cannot be measured is skipped, never chosen blindly over one that can
            continue
        if best_score is None or score > best_score:
            best, best_score = i, score
    return best
