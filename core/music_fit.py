"""The chosen score, re-fitted to the film as it was really cut (free, ffmpeg only; kế hoạch sửa sau #8, S1).

Trial #8 (2026-09-28, người dùng: "nhạc nền cần đi theo diễn biến của kịch bản"): the score was composed on the 64 s timeline of the
moment (music_timing.brief — section turns at 0:08.0, 0:20.5, 0:35.1, 0:47.7, 0:54.7, final hit 1:03.7); the voices and remade clips
then made the film 84.5 s, so every musical turn landed in the wrong scene and the ending hit came 20 s early.

Each section of the score (between two turns the brief asked for) is moved onto its scene's real span: stretched or squeezed with
`atempo` when the change is small (pitch kept), looped with crossfades when the scene grew a lot, faded out when it shrank; sections are
joined with short crossfades, and the ending (final hit + tail) is kept after the film's last scene. The turns are read from the brief
saved with the drafts, so a track from the library (no brief) is left as it is — said, never guessed.
"""
import hashlib
import json
import math
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

from . import ffmpeg_studio

TURNS = re.compile(r"exactly at its time \(([^)]*)\)")
END_HIT = re.compile(r"final hit at (\d+):(\d+(?:\.\d+)?)")
FILM_S = re.compile(r"for a (\d+(?:\.\d+)?)-second")
END_LEAD = 1.0             # the score's final hit lands this long before the film ends
JOIN = 0.5                 # crossfade between two re-fitted sections (s)
TEMPO_MIN, TEMPO_MAX = 0.87, 1.15  # atempo range that still sounds like the same music (±13 %); beyond it the tempo is kept (the brief
                                   # asked one BPM for the whole score) and the section is looped or cut instead


def _clock(text: str) -> float:
    m, s = text.strip().split(":")
    return int(m) * 60 + float(s)


def planned(prompt: str) -> Optional[Dict]:
    """{"turns": [s], "end": s} the brief asked the composer for, or None when the prompt carries no timed turns."""
    m = TURNS.search(prompt or "")
    if not m:
        return None
    turns = [_clock(x) for x in m.group(1).split(",") if ":" in x]
    e = END_HIT.search(prompt)
    end = int(e.group(1)) * 60 + float(e.group(2)) if e else None
    if end is None:
        f = FILM_S.search(prompt)
        end = float(f.group(1)) if f else None
    if not turns or end is None or any(b <= a for a, b in zip([0.0] + turns, turns + [end])):
        return None
    return {"turns": turns, "end": end}


def film_turns(datas: Sequence[Dict], seconds: Sequence[float]) -> Tuple[List[float], float]:
    """Where each script scene starts on the render (story_scene changes) and the film's length."""
    turns, t, prev = [], 0.0, None
    for d, secs in zip(datas, seconds):
        sc = d.get("story_scene")
        if prev is not None and sc != prev:
            turns.append(round(t, 2))
        prev = sc
        t += float(secs)
    return turns, round(t, 2)


def segments(old_turns: Sequence[float], old_end: float, new_turns: Sequence[float], new_end: float) -> List[Dict]:
    """[{"a", "b" (in the score), "length" (on the film), "mode": tempo|loop|cut, "tempo"}] — one per section."""
    olds = list(zip([0.0] + list(old_turns), list(old_turns) + [old_end]))
    news = list(zip([0.0] + list(new_turns), list(new_turns) + [new_end]))
    out = []
    for (a, b), (x, y) in zip(olds, news):
        length, have = y - x, b - a
        ratio = length / have
        if TEMPO_MIN <= 1 / ratio <= TEMPO_MAX:
            out.append({"a": a, "b": b, "length": length, "mode": "tempo", "tempo": round(have / length, 4)})
        elif ratio > 1:
            out.append({"a": a, "b": b, "length": length, "mode": "loop", "tempo": 1.0})
        else:
            out.append({"a": a, "b": b, "length": length, "mode": "cut", "tempo": 1.0})
    return out


def build_cmd(src: str, out: str, segs: Sequence[Dict], tail: Tuple[float, float], ffmpeg: str = "ffmpeg") -> List[str]:
    """One ffmpeg call: every section cut from the score, fitted, and joined with JOIN-second crossfades; `tail` = (start, end) of the
    ending kept after the last section."""
    parts, labels = [], []
    n = len(segs) + 1
    parts.append(f"[0:a]asplit={n}" + "".join(f"[s{i}]" for i in range(n)))
    for i, g in enumerate(segs):
        target = g["length"] + JOIN                    # each join eats JOIN seconds: the sections keep their scene starts
        chain = f"[s{i}]atrim={g['a']:.3f}:{g['b']:.3f},asetpts=PTS-STARTPTS,atempo={g['tempo']}"
        if g["mode"] == "loop":
            have = (g["b"] - g["a"]) / g["tempo"]
            copies = max(2, int(math.ceil((target - have) / max(have - JOIN, 0.5))) + 1)
            chain += f",asplit={copies}" + "".join(f"[l{i}_{k}]" for k in range(copies))
            parts.append(chain)
            joined = f"[l{i}_0]"
            for k in range(1, copies):
                parts.append(f"{joined}[l{i}_{k}]acrossfade=d={JOIN}[j{i}_{k}]")
                joined = f"[j{i}_{k}]"
            parts.append(f"{joined}atrim=0:{target:.3f},afade=t=out:st={max(target - JOIN, 0):.3f}:d={JOIN}[g{i}]")
        else:
            parts.append(chain + f",atrim=0:{target:.3f},afade=t=out:st={max(target - JOIN, 0):.3f}:d={JOIN}[g{i}]")
        labels.append(f"[g{i}]")
    parts.append(f"[s{n - 1}]atrim={tail[0]:.3f}:{tail[1]:.3f},asetpts=PTS-STARTPTS[tail]")
    labels.append("[tail]")
    joined = labels[0]
    for k, lab in enumerate(labels[1:], 1):
        parts.append(f"{joined}{lab}acrossfade=d={JOIN}:c1=tri:c2=tri[x{k}]")
        joined = f"[x{k}]"
    return [ffmpeg, "-y", "-i", src, "-filter_complex", ";".join(parts), "-map", joined, "-c:a", "pcm_s16le", out]


def prompt_of(drafts: Sequence[Dict], drafts_dir: str, track: str) -> str:
    """The brief a selected track was composed from: the draft whose file is byte-identical to it ('' for a library track)."""
    try:
        size = os.path.getsize(track)
        with open(track, "rb") as f:
            head = hashlib.sha1(f.read(1 << 16)).hexdigest()
    except OSError:
        return ""
    for d in drafts:
        path = os.path.join(drafts_dir, d.get("file") or "")
        if d.get("state") == "succeeded" and d.get("file") and os.path.exists(path) and os.path.getsize(path) == size:
            with open(path, "rb") as f:
                if hashlib.sha1(f.read(1 << 16)).hexdigest() == head:
                    return d.get("prompt") or ""
    return ""


def fit(track: str, prompt: str, datas: Sequence[Dict], seconds: Sequence[float], work_dir: str) -> Dict:
    """{"path" (the fitted score, or the track unchanged), "fitted": bool, "why", "turns": [...]}."""
    plan = planned(prompt)
    if plan is None:
        return {"path": track, "fitted": False, "why": "bản nhạc không có mốc đổi đoạn đã hẹn (nhạc từ kho hoặc soạn không theo mốc) — giữ nguyên"}
    new_turns, total = film_turns(datas, seconds)
    if len(new_turns) != len(plan["turns"]):
        return {"path": track, "fitted": False,
                "why": f"nhạc soạn cho {len(plan['turns']) + 1} đoạn, phim có {len(new_turns) + 1} cảnh — giữ nguyên, nên soạn lại"}
    length = ffmpeg_studio.probe_duration(track) or plan["end"]
    tail_end = max(length, plan["end"] + 0.1)
    film_end = max(total - END_LEAD, (new_turns[-1] if new_turns else 0.0) + 1.0)   # the final hit just before the last frame
    segs = segments(plan["turns"], plan["end"], new_turns, film_end)
    key = hashlib.sha1(json.dumps([track, os.path.getmtime(track) if os.path.exists(track) else 0, segs], sort_keys=True).encode()).hexdigest()[:10]
    os.makedirs(work_dir, exist_ok=True)
    out = os.path.join(work_dir, f"music_fit_{key}.wav")
    if not os.path.exists(out):
        ffmpeg_studio.run(build_cmd(track, out, segs, (plan["end"], tail_end), ffmpeg_studio.find_ffmpeg()))
    return {"path": out, "fitted": True, "why": "", "turns": new_turns, "old_turns": plan["turns"],
            "modes": [g["mode"] for g in segs]}
