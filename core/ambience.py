"""A room-tone / ambience bed under each script scene, from the person's own sound library (knowledge/editor/editing.md E3, việc code
D4 + D5) — no AI, no credit.

Why: without a continuous bed the cuts "gasp" (the sound drops to silence between effects) and a snowy night or a storm sounds
unfinished. `sfx_plan` places ACCENTS (hits, whooshes); this is the other layer: one long, quiet sound per scene, chosen by the scene's
weather first (rain / storm → thunderstorm, sandstorm → windy desert…), then its place (street, town → city / traffic; forest, island →
birds), faded in and out at the scene's edges, looped when shorter than the scene.

    choose(conn, data) -> the library sound for a shot / scene (or None: nothing fits — said, never a random sound)
    beds(p, pid, rows, durations, work_dir) -> extras for the mix [{"path", "start", "volume", "scene", "sound"}]
"""
import json
import os
import re
from typing import Dict, List, Optional, Sequence

from . import ffmpeg_studio

VOLUME = 0.12                 # ~-18 dB under the dialogue (ambience is felt, not listened to)
FADE_S = 0.6
MIN_SECONDS = 8.0             # a shorter file loops audibly
# (words in the scene) -> words to look for in the library sound's name / what YAMNet heard, best first
WEATHER = {"storm": ("thunderstorm", "thunder", "rain"), "rain": ("rain", "thunderstorm"), "sandstorm": ("windy desert", "wind"),
           "snowfall": ("wind", "winter"), "snow": ("wind", "winter"), "fog": ("wind",), "cloudy": ("wind",)}
NIGHT = ("night", "cricket", "insect", "đêm", "dế")
PLACES = ((re.compile(r"street|city|town|thị trấn|phố|đường|nhà|house|market|chợ|khu dân cư", re.I), ("busy city street", "street traffic", "city")),
          (re.compile(r"forest|rừng|island|đảo|jungle|garden|vườn|park|công viên|field|cánh đồng", re.I), ("bird ambience", "bird", "nature")),
          (re.compile(r"desert|sa mạc|canyon|hẻm núi", re.I), ("windy desert", "wind")))


def _query(data: Dict) -> Sequence[str]:
    from . import plate_env
    weather = plate_env.weather_of(data)[0]
    if weather in WEATHER:
        return WEATHER[weather]
    if plate_env.time_of(data) == "night":
        return NIGHT       # #7 (2026-09-25): the empty night plaza got "Busy City Street" — a night scene takes a night sound or none
    place = f"{data.get('location') or ''} {data.get('image_prompt') or ''}"
    for pat, words in PLACES:
        if pat.search(place):
            return words
    return ()


def choose(conn, data: Dict) -> Optional[Dict]:
    words = _query(data)
    if not words:
        return None
    rows = conn.execute("SELECT id, path, name, duration, heard FROM sounds WHERE voice=0 AND duration>=?", (MIN_SECONDS,)).fetchall()
    for w in words:                                     # the first word that matches wins; the longest file of it (fewer loops)
        word = re.compile(rf"(?<![\w]){re.escape(w)}(?![\w])", re.I)     # whole words: "Crunk Knight" is not a night sound
        hits = [r for r in rows if word.search(f"{r['name']} {r['heard'] or ''}") and os.path.exists(r["path"])]
        if hits:
            best = max(hits, key=lambda r: r["duration"] or 0)
            return {"id": best["id"], "path": best["path"], "name": best["name"], "word": w}
    return None


def _bed(src: str, seconds: float, out: str, ffmpeg: str) -> str:
    fade_out = max(seconds - FADE_S, 0)
    ffmpeg_studio.run([ffmpeg, "-y", "-stream_loop", "-1", "-i", src, "-t", f"{seconds:.2f}", "-af",
                       f"afade=t=in:d={FADE_S},afade=t=out:st={fade_out:.2f}:d={FADE_S},aformat=sample_rates=48000:channel_layouts=stereo",
                       out])
    return out


def beds(conn, rows: List[Dict], durations: List[float], work_dir: str, transition: str = "cut", fade: float = 1.0,
         ffmpeg: Optional[str] = None) -> Dict:
    """One bed per script scene on the render's timeline. {"extras": [...], "missing": [scene numbers with nothing that fits]}."""
    ff = ffmpeg or ffmpeg_studio.find_ffmpeg()
    overlap = fade if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    spans: List[Dict] = []
    t = 0.0
    for r, d in zip([r for r in rows if r.get("path")], durations):
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (r.get("scene_id"),)).fetchone() if r.get("scene_id") else None
        data = json.loads(row["data"] or "{}") if row else {}
        sc = data.get("story_scene") or data.get("sequence") or r.get("idx")
        if not spans or spans[-1]["scene"] != sc:
            spans.append({"scene": sc, "start": t, "end": t, "data": data})
        spans[-1]["end"] = t + float(d)
        t += float(d) - overlap
    os.makedirs(work_dir, exist_ok=True)
    extras, missing = [], []
    for s in spans:
        pick = choose(conn, s["data"])
        if pick is None:
            missing.append(s["scene"])
            continue
        seconds = max(s["end"] - s["start"], 1.0)
        out = _bed(pick["path"], seconds, os.path.join(work_dir, f"bed_{s['scene']}.wav"), ff)
        extras.append({"path": out, "start": round(s["start"], 2), "volume": VOLUME, "scene": s["scene"], "sound": pick["name"]})
    return {"extras": extras, "missing": missing}
