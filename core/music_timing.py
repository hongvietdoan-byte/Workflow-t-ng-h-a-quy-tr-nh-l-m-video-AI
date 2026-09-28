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


def render_timeline(p: Pipeline, pid: int) -> Optional[Dict[int, float]]:
    """scene_id -> seconds in the latest final render (its manifest), or None before any render. #8 (2026-09-28): the score was
    composed on the planned 64 s while the cut was 84,5 s — a score made after a render follows the render."""
    row = p.conn.execute("SELECT manifest FROM outputs WHERE project_id=? AND kind='final' ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    try:
        tl = json.loads(row["manifest"] or "{}").get("timeline") if row else None
    except ValueError:
        tl = None
    if not tl:
        return None
    return {r["scene_id"]: float(r["seconds"]) for r in tl if r.get("scene_id")}


def sections(p: Pipeline, pid: int, seconds: Optional[Dict[int, float]] = None) -> List[Dict]:
    """The script sections on the real timeline: each shot lasts its clip's cut length (motion prompt duration, stretched to the voice),
    or — given `seconds` (render_timeline) — the length it has in the render. Each section keeps its shots ("shots") for the beats."""
    rows = p.conn.execute("SELECT s.id, s.idx, s.data, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id "
                          "WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    if seconds:
        rows = [r for r in rows if r["id"] in seconds]
    heads = {r["idx"]: r["heading"] for r in p.conn.execute("SELECT idx, heading FROM story_scenes WHERE project_id=?", (pid,))}
    out: List[Dict] = []
    t = 0.0
    for r in rows:
        d = json.loads(r["data"] or "{}")
        dur = float(seconds[r["id"]]) if seconds else float(r["duration_sec"] or d.get("duration_s") or 0)
        sc = d.get("story_scene") or r["idx"]
        if not out or out[-1]["scene"] != sc:
            out.append({"scene": sc, "heading": heads.get(sc, ""), "start": round(t, 2), "end": round(t, 2),
                        "mood": str(d.get("mood") or ""), "intent": str(d.get("emotional_intent") or ""),
                        "lighting": str(d.get("lighting") or ""), "spoken": 0.0, "shots": []})
        out[-1]["end"] = round(t + dur, 2)
        out[-1]["shots"].append({"start": round(t, 2), "data": d})
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


# #8 (2026-09-28): the moods are written in Vietnamese by the Director ("bí mật, nghẹt thở", "vỡ òa, đau đớn", "hoảng loạn, khẩn cấp") and
# the English-only words sent 4 scenes of 6 to the same "tense, driving hybrid score". The MOOD of the section decides (not its intent
# text, which tells the whole story); first match wins.
MOOD_STYLES = (
    (re.compile(r"ấm áp|hạnh phúc|hóa giải|ôm|reunion|embrace", re.I),
     "warm resolution: the love motif on strings and piano, swelling and hopeful"),
    (re.compile(r"hoảng loạn|khẩn cấp|panic|urgent", re.I),
     "urgent: a fast low ostinato and heartbeat drums, rising dread"),
    (re.compile(r"vỡ òa|đau đớn|tan vỡ|heartbreak", re.I),
     "heartbreak: the motif on a lone cello over aching strings, swelling then falling away"),
    (re.compile(r"bí mật|nghẹt thở|hồi hộp|secret|suspense|whisper", re.I),
     "hushed suspense: low sustained strings, a soft ticking pulse, holding its breath"),
    (re.compile(r"đùa|trêu|playful|banter", re.I),
     "uneasy lightness: soft pizzicato and light percussion over an uneasy pad"),
    (re.compile(r"đau|kìm nén|buồn|khóc|nước mắt|lonely|grief", re.I),
     "fragile: sparse solo piano with cold string pads, restrained, lots of space"),
)


def _style(sec: Dict, bpm: int = 100) -> str:
    for rx, style in MOOD_STYLES:
        if rx.search(sec.get("mood") or ""):
            return style
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


DEATH = re.compile(r"bị hạ|hạ gục|knocked|eliminat|chết|trúng đạn|gục", re.I)
FLASHBACK = re.compile(r"flashback|hồi tưởng|ký ức", re.I)
MAX_BEATS = 10
DRAMA_BPM_MAX = 110          # #8: 137 BPM was chosen only to put the turns on bar lines — too fast for a drama
PROMPT_MAX = 1990            # Clip AI text limit 2000 (core/adapters/clipai_audio.py)
MOTIF = "the love motif on a music-box / soft piano, dreamy and warm"


def beats(secs: List[Dict]) -> List[Tuple[float, int, str]]:
    """Story moments inside the sections the score should play with: (time, priority, English line). From the shot table, no model call:
    the Director's sound intent (music thins / back / a breath), a knock-down notice, a flashback span, emotional peaks, the last shot.
    Priority 1 is kept first when there are more than MAX_BEATS."""
    out: List[Tuple[float, int, str]] = []
    shots = [sh for sec in secs for sh in sec["shots"]]
    starts = {sec["start"] for sec in secs}
    fb_start = None
    thin: Dict[float, List[float]] = {}                  # the Director's "cut"s of one section: one sparse stretch, said once
    sec_of = {sh["start"]: sec["start"] for sec in secs for sh in sec["shots"]}
    for sh in shots:
        d, t = sh["data"], sh["start"]
        m = ((d.get("sound") or {}) if isinstance(d.get("sound"), dict) else {}).get("music")
        text = " ".join(str(d.get(x) or "") for x in ("action", "image_prompt"))
        notice = " ".join(str(x) for x in (d.get("on_screen_text") or []))
        if m == "cut":
            thin.setdefault(sec_of[t], []).append(t)
        elif m == "in" and t not in starts:
            out.append((t, 2, f"{_clock(t)} the music comes back in softly"))
        elif m == "breath" and t > 1.0:            # a breath before the first shot has nothing to breathe out of
            out.append((t, 3, f"{_clock(t)} a short held breath just before"))
        if notice and DEATH.search(notice + " " + text):
            out.append((t, 1, f"{_clock(t)} shock: a sharp low hit, then a stunned, sparse pulse"))
        is_fb = bool(d.get("flashback")) or bool(FLASHBACK.search(text))
        if is_fb and fb_start is None:
            fb_start = t
        if fb_start is not None and not is_fb:
            out.append((fb_start, 1, f"{_clock(fb_start)}-{_clock(t)} flashback: {MOTIF}"))
            fb_start = None
        acting = d.get("performance") if isinstance(d.get("performance"), dict) else {}
        if acting.get("intensity") == 5:
            out.append((t, 2, f"{_clock(t)} emotional peak: the fullest, most open moment so far"))
    if fb_start is not None:
        out.append((fb_start, 1, f"{_clock(fb_start)} flashback to the end: {MOTIF}"))
    for times in thin.values():
        a, b = min(times), max(times)
        out.append((a, 2, f"{_clock(a)}" + (f"-{_clock(b)}" if b > a else "") + " almost silent under the key lines"))
    if shots:
        t = shots[-1]["start"]
        out.append((t, 1, f"{_clock(t)} resolution: the love motif in full, warm and hopeful"))
    busy = {}                                    # a softer line at the same second as a stronger one says the same thing twice
    for t, pr, text in out:
        if "comes back in softly" not in text and "almost silent" not in text:
            busy[t] = True
    out = [b for b in out if not (("comes back in softly" in b[2] or "almost silent" in b[2]) and busy.get(b[0]))]
    seen, uniq = set(), []
    for b in sorted(out):
        if b[2] not in seen:
            seen.add(b[2])
            uniq.append(b)
    return sorted(sorted(uniq, key=lambda b: (b[1], b[0]))[:MAX_BEATS])


def brief(p: Pipeline, pid: int, seconds: Optional[Dict[int, float]] = None) -> Dict:
    """The score's brief, timed on the cut. Given `seconds` (the render's own lengths, render_timeline) it follows the render. Since #8
    (người dùng 2026-09-28: music is cheap next to video — the score may be creative as long as it follows the story): one love motif
    carries the film, the tempo may breathe, and the story beats inside the sections (beats) are written in."""
    secs = sections(p, pid, seconds)
    total = secs[-1]["end"] if secs else 0.0
    turns = [s["start"] for s in secs[1:]]
    bpm, err = choose_bpm(turns, hi=DRAMA_BPM_MAX)
    parts = [f"{_clock(s['start'])}-{_clock(s['end'])}: {_style(s, bpm)}." for s in secs]
    talky = sum(s["spoken"] for s in secs) > 0.4 * total if total else False
    moments = beats(secs)
    head = (f"Instrumental score for a {total:.0f}-second vertical Free Fire short drama, around {bpm} BPM (free to breathe slower in the "
            "tender parts). One simple, memorable love motif carries the whole film: introduced softly, strained in the conflict, bare in "
            "the memory, full at the end."
            + (" Dialogue sits over most of it: keep the mid frequencies clear, no busy melody under speech." if talky else "") + " ")
    # #8 (người dùng 2026-09-28): "nhạc vào không hợp lý, không có độ mềm mại" — a turn flows in over about a bar, the new mood arriving
    # on its time (music_fit reads these times back to move the sections onto the scenes as really cut)
    turn_line = (" Each section flows into the next over about one bar, the new mood arriving exactly at its time ("
                 + ", ".join(_clock(t) for t in turns) + ") - follow the story's emotion, no abrupt stops or jarring jumps." if turns else "")
    tail = f" End cleanly on a final hit at {_clock(total)}, no long tail. No vocals, no lyrics."
    keep = sorted(moments, key=lambda b: (b[1], b[0]))
    while True:                                   # the fewest-priority story moments go first when the prompt is too long
        shown = sorted(keep)
        prompt = (head + " ".join(parts) + turn_line
                  + (" Story moments: " + "; ".join(b[2] for b in shown) + "." if shown else "") + tail)
        if len(prompt) <= PROMPT_MAX or not keep:
            break
        keep = keep[:-1]
    return {"prompt": prompt[:PROMPT_MAX], "bpm": bpm, "beats": [b[2] for b in sorted(keep)], "error_s": err, "length_ms": int(round(total * 1000)) + TAIL_PAD_MS, "film_s": total,
            "sections": secs, "turns": turns}


def timed_brief(p: Pipeline, pid: int) -> Optional[Dict]:
    """The brief of `brief` in the shape music.submit_drafts / the Step 5 form use ({"prompt", "length_ms", "instrumental"} + bpm,
    turns, film_s), or None when the project has no timeline yet (no shot has a length)."""
    b = brief(p, pid, render_timeline(p, pid))
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
