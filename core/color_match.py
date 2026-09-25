"""Colour matching between the shots of one place (knowledge/editor/editing.md E5, việc code D7) — no AI, no credit.

Why: every clip is drawn by a video model on its own, so two shots of the same place, same moment, come back in different tones (one
warmer, one darker). A viewer sees the jump at the cut. A colourist fixes the shot first, then matches the shots of a scene to one
anchor by what does not depend on the content of the frame: the **black and white points** and the **colour cast of neutral (grey)
things** — not the average colour (a close-up of a yellow jacket and a wide shot of the same street have different averages but should
have the same light). This module reads those numbers from the clips.

    measure(path)           -> {"neutral": [r, g, b] mean of the low-saturation pixels, "lo" / "hi": 5 % / 95 % luminance} (0..1)
    groups(conn, pid, rows) -> shots that must match: same script scene / `sequence` and same place
    plan(...)               -> per clip: the anchor, the cast / levels deviation, the correction (per-channel gain + levels), limited
    apply(src, dst, fix)    -> the clip with the correction (ffmpeg lutrgb), sound copied

The deviation is always measured and kept with the render (manifest `color_match`); the correction is applied only with the feature
`shot_color_match` on (it changes the picture — CHUAN_XAY_DUNG rule 5).
"""
import json
import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Sequence

from . import ffmpeg_studio

CAST_WARN = 0.035            # distance of the neutral colour (normalised r, g, b) above which a cast difference shows at the cut
LEVELS_WARN = 0.08           # black / white point difference (0..1 luminance) above which one shot reads darker / flatter
STRENGTH = 0.7               # how far a shot is moved toward its anchor (1 = all the way; a model's tone is not always wrong)
MAX_GAIN = 0.2               # never more than ±20 % per channel — a bigger jump is a picture problem (redo), not a grade
NEUTRAL_SAT = 0.25           # a pixel this unsaturated counts as "grey" (walls, concrete, sky haze) — 0,15 dropped a grey wall under
                             # a warm light (+10 % red) out of the neutrals, so the very cast to find was not seen
CLOSE_SIZES = ("MCU", "CU", "ECU")


def _np():
    import numpy
    return numpy


def measure(path: str, ffmpeg: Optional[str] = None) -> Optional[Dict]:
    """Middle frame of a clip → neutral colour + 5 % / 95 % luminance (0..1). None when it cannot be read."""
    ff = ffmpeg or ffmpeg_studio.find_ffmpeg()
    dur = ffmpeg_studio.probe_duration(path) or 0
    with tempfile.TemporaryDirectory() as work:          # measured on every render: nothing may pile up
        frame = os.path.join(work, "mid.png")
        proc = subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{max(dur / 2, 0):.2f}", "-i", path,
                               "-frames:v", "1", "-vf", "scale=270:-2", frame], capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(frame):
            return None
        from PIL import Image
        with Image.open(frame) as im:
            return stats(_np().asarray(im.convert("RGB"), _np().float32) / 255)


def stats(rgb) -> Dict:
    np = _np()
    px = rgb.reshape(-1, 3)
    lum = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mx, mn = px.max(axis=1), px.min(axis=1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    grey = px[(sat < NEUTRAL_SAT) & (lum > 0.08) & (lum < 0.92)]
    base = grey if len(grey) >= 0.02 * len(px) else px      # almost nothing grey: fall back to the whole frame (said in the report)
    return {"neutral": [round(float(x), 4) for x in base.mean(axis=0)], "neutral_share": round(len(grey) / len(px), 3),
            "lo": round(float(np.percentile(lum, 5)), 4), "hi": round(float(np.percentile(lum, 95)), 4)}


def _norm(c: Sequence[float]) -> List[float]:
    s = sum(c) or 1e-6
    return [x / s for x in c]


def deviation(shot: Dict, anchor: Dict) -> Dict:
    cast = sum((x - y) ** 2 for x, y in zip(_norm(shot["neutral"]), _norm(anchor["neutral"]))) ** 0.5
    levels = max(abs(shot["lo"] - anchor["lo"]), abs(shot["hi"] - anchor["hi"]))
    return {"cast": round(float(cast), 4), "levels": round(float(levels), 4),
            "off": cast > CAST_WARN or levels > LEVELS_WARN}


def groups(conn, project_id: int, rows: Sequence[Dict]) -> List[List[int]]:
    """Indexes (into `rows`) of shots that must look alike: same script scene (or `sequence`) AND same place. A group of one needs no match."""
    keyed: Dict = {}
    for i, r in enumerate(rows):
        if not r.get("scene_id"):
            continue
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (r["scene_id"],)).fetchone()
        data = json.loads(row["data"] or "{}") if row else {}
        # a close-up's black / white points follow the face, a wide shot's the place: only shots of one size class are compared
        # (#7, 2026-09-25: a CU against its WS anchor read 0,14 "levels" apart from the content alone)
        close = str(data.get("size") or "").upper() in CLOSE_SIZES
        scene = data.get("story_scene") or data.get("sequence")
        if scene is None:                  # an old one-clip-per-scene project: scenes of one place are day AND night — never pulled together
            continue
        key = (scene, str(data.get("location_asset") or data.get("location") or "").lower(), close)
        keyed.setdefault(key, []).append(i)
    return [g for g in keyed.values() if len(g) > 1]


def correction(shot: Dict, anchor: Dict, strength: float = STRENGTH) -> Dict:
    """Per-channel gain that brings the neutral colour to the anchor's cast (brightness kept), + a levels move toward the anchor's
    black / white points; all limited."""
    ns, na = _norm(shot["neutral"]), _norm(anchor["neutral"])
    gains = []
    for s, a in zip(ns, na):
        g = 1 + ((a / s if s > 1e-4 else 1.0) - 1) * strength
        gains.append(round(min(max(g, 1 - MAX_GAIN), 1 + MAX_GAIN), 4))
    lo = shot["lo"] + (anchor["lo"] - shot["lo"]) * strength
    hi = shot["hi"] + (anchor["hi"] - shot["hi"]) * strength
    scale = min(max(max(hi - lo, 0.05) / max(shot["hi"] - shot["lo"], 0.05), 1 - MAX_GAIN), 1 + MAX_GAIN)
    return {"gain": gains, "scale": round(scale, 4), "src_lo": shot["lo"], "dst_lo": round(lo, 4)}


def plan(stats_list: Sequence[Optional[Dict]], group_list: List[List[int]]) -> List[Dict]:
    """For every clip of a group: its anchor (the group's first clip — where the place is set up), deviation and correction."""
    out = []
    for g in group_list:
        anchor = g[0]
        if not stats_list[anchor]:
            continue
        for i in g[1:]:
            if not stats_list[i]:
                continue
            dev = deviation(stats_list[i], stats_list[anchor])
            out.append(dict(dev, clip=i, anchor=anchor, fix=correction(stats_list[i], stats_list[anchor]),
                            grey_share=stats_list[i]["neutral_share"]))
    return out


def _lut(fix: Dict) -> str:
    """lutrgb expression per channel: levels (move the black point, stretch) then the channel gain; values stay 0..255."""
    lo_s, lo_d = fix["src_lo"] * 255, fix["dst_lo"] * 255
    return "lutrgb=" + ":".join(f"{name}='clip(((val-{lo_s:.2f})*{fix['scale']}+{lo_d:.2f})*{g},0,255)'"
                                for name, g in zip("rgb", fix["gain"]))


def apply(src: str, dst: str, fix: Dict, ffmpeg: Optional[str] = None) -> str:
    ff = ffmpeg or ffmpeg_studio.find_ffmpeg()
    ffmpeg_studio.run([ff, "-y", "-i", src, "-vf", _lut(fix), *ffmpeg_studio._ENCODE, "-c:a", "copy", dst])
    return dst


def check_and_fix(conn, project_id: int, rows: Sequence[Dict], work_dir: str, fix: bool = False) -> Dict:
    """Measure the clips of the render that share a place, report the shots that drift from their anchor; with fix=True, write
    corrected copies and return their paths (the originals are never touched). {"report": [...], "paths": {clip index: new path}}."""
    group_list = groups(conn, project_id, rows)
    stats_list: List[Optional[Dict]] = [None] * len(rows)
    for i in sorted({i for g in group_list for i in g}):
        if rows[i].get("path"):
            stats_list[i] = measure(rows[i]["path"])
    items = plan(stats_list, group_list)
    paths = {}
    if fix:
        os.makedirs(work_dir, exist_ok=True)
        for it in items:
            if it["off"]:
                paths[it["clip"]] = apply(rows[it["clip"]]["path"], os.path.join(work_dir, f"match_{it['clip']:03d}.mp4"), it["fix"])
    report = [{"idx": rows[it["clip"]].get("idx"), "anchor_idx": rows[it["anchor"]].get("idx"), "cast": it["cast"],
               "levels": it["levels"], "off": it["off"], "grey_share": it["grey_share"], "fixed": it["clip"] in paths} for it in items]
    return {"report": report, "paths": paths}
