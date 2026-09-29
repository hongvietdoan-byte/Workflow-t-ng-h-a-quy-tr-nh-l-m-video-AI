"""Lip sync option (c) of S4.6 — a "dialogue take": ONE Seedance clip for a whole stretch of dialogue, with ONE voice track of every line
at its planned second, the lines written in the prompt with their seconds and speaker. From the user's working ClipAI prompt
(docs/PHAN_TICH_PROMPT_KHOP_MOI_2026-09-29.md, 7 blocks): head (format, length locked to the audio), reference assets (one role per
picture / audio), characters & blocking (C1/C2 labels), the lip-sync directive (jaw, teeth, visemes, mouth shut in silence), a timeline
of whole seconds with "Dialogue (NAME / lipsync @Audio1): line", and continuity & avoid.

Why (analysis §3): #8 lip-synced shot by shot (a 4 s clip per line, cut shorter) and the mouth drifted at the cut; with two people in
frame the model had to guess who speaks. Here the model is told who speaks when. Tested against (a) in the S4.6 round 2 A/B — this
module only builds the send, it decides nothing on its own."""
import math
import os
import subprocess
from typing import Dict, List, Optional

from . import voice

TAIL = 0.6                 # picture after the last line (the reaction), seconds
MAX_SECONDS = 15           # Seedance clip length limit on the API (clipai.effective_duration)
PROMPT_LIMIT = 5000        # ClipAI reference-mode prompt limit (the user's prompt: 3 673 / 5 000)

STYLE = {
    "ingame": ("Style: Garena Free Fire in-game 3D character render, exactly like the reference pictures — stylized mobile-game "
               "proportions, clear gameplay lighting; not anime, not 2D, not cel-shaded, not live action."),
    "real3d": ("Style: realistic 3D CGI animation, Unreal Engine 5 quality, subsurface-scattering skin, detailed facial rig; every "
               "character keeps the face, hair and outfit of their reference picture."),
}
AVOID = {
    "ingame": "photorealistic skin, live-action look, film colour grading",
    "real3d": "anime face, cel-shaded face, flat 2D mouth",
}
AVOID_COMMON = ("frozen or closed mouth while the character speaks, mouth moving during silence, the wrong person moving their lips, "
                "pasted-on face, cartoon eyes, on-screen text, burned-in subtitles, watermark, Chinese characters, outfit changes, extra people")


def segments(lines: List[Dict], lead: float = voice.LEAD, gap: float = 0.35) -> List[Dict]:
    """[{speaker, text, file, start, end}] — each voiced line ({speaker, text, file, duration_ms}) one after the other: `lead` seconds of
    picture first, `gap` between lines (a speaker change needs a breath — longer than voice.GAP inside one shot)."""
    out, t = [], lead
    for ln in lines:
        d = (ln.get("duration_ms") or 0) / 1000.0
        if d <= 0:
            raise ValueError(f"line without a length (not voiced yet?): {ln.get('speaker')}: {ln.get('text')}")
        out.append({"speaker": ln["speaker"], "text": ln["text"], "file": ln.get("file"), "start": round(t, 3), "end": round(t + d, 3)})
        t += d + gap
    return out


def length(segs: List[Dict]) -> float:
    return round(segs[-1]["end"] + TAIL, 3) if segs else 0.0


def billed_seconds(segs: List[Dict]) -> int:
    """Whole seconds the clip is asked for (≥ 4, the Seedance minimum). Too long for one clip → an error, not a silent cut."""
    s = max(4, math.ceil(length(segs) - 1e-6))
    if s > MAX_SECONDS:
        raise ValueError(f"đoạn thoại dài {length(segs):.1f} s > {MAX_SECONDS} s của một clip — tách thành hai đoạn")
    return s


def mix(segs: List[Dict], directory: str, out: str, ffmpeg: str, seconds: Optional[float] = None) -> str:
    """The dialogue track: every line at its start, silence around, `seconds` long (default: the billed length) — Audio1 of the send."""
    total = float(seconds or billed_seconds(segs))
    cmd = [ffmpeg, "-y", "-loglevel", "error"]
    for s in segs:
        cmd += ["-i", os.path.join(directory, s["file"])]
    parts = "".join(f"[{i}:a]adelay={int(s['start'] * 1000)}|{int(s['start'] * 1000)},aresample=44100[a{i}];" for i, s in enumerate(segs))
    mixin = "".join(f"[a{i}]" for i in range(len(segs)))
    flt = parts + f"{mixin}amix=inputs={len(segs)}:normalize=0,apad,atrim=0:{total:.3f}[out]"
    cmd += ["-filter_complex", flt, "-map", "[out]", "-ac", "1", "-ar", "44100", out]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if proc.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"không ghép được track thoại: {(proc.stderr or '')[-300:]}")
    return out


def _stamp(a: float, b: float) -> str:
    """Seedance 2.5 reads whole seconds: the window that contains the line."""
    lo, hi = int(math.floor(a)), max(int(math.ceil(b)), int(math.floor(a)) + 1)
    return f"[00:{lo:02d} - 00:{hi:02d}]"


def prompt(cast: List[Dict], segs: List[Dict], style: str = "ingame", place: str = "", composition: bool = True,
           beats: Optional[Dict] = None, aspect: str = "9:16") -> str:
    """The 7-block prompt. cast: [{name, where, pose, identity?, acting?}] in the order of their identity pictures; composition: Image 1
    is the storyboard picture of the take (its framing and positions), the identity pictures follow. beats: {segment index: what the
    listeners / the body do meanwhile}, "end": the reaction after the last line."""
    if style not in STYLE:
        raise ValueError(f"unknown style {style!r}")
    beats = beats or {}
    label = {c["name"].upper(): f"C{i}" for i, c in enumerate(cast, 1)}
    total = billed_seconds(segs)
    first = 2 if composition else 1
    head = (f"Format {aspect}, one continuous take of {total} seconds, no cuts. The clip length matches Audio1 one to one — do not "
            f"stretch or compress time. {STYLE[style]}" + (f" Place: {place}." if place else ""))
    refs = ["REFERENCE ASSETS:"]
    if composition:
        refs.append("Image1 = the opening frame: framing, camera distance and where each person stands — start exactly like it.")
    for i, c in enumerate(cast):
        who = f"{label[c['name'].upper()]} {c['name']}"
        refs.append(f"Image{first + i} = identity of {who} only (face, hair, outfit{', ' + c['identity'] if c.get('identity') else ''}) "
                    "— not the framing.")
    refs.append("Audio1 = the whole Vietnamese dialogue of this take: timing, pauses, emotion and the phonemes each mouth shape follows.")
    chars = ["CHARACTERS & BLOCKING:"] + [
        f"{label[c['name'].upper()]} ({c['name']}): {c.get('where', '')}; {c.get('pose', '')}. Matches Image{first + i}.".replace(" ; ", " ")
        for i, c in enumerate(cast)]
    speakers = sorted({s["speaker"].upper() for s in segs}, key=lambda n: label.get(n, n))
    lip = ("AUDIO & LIP-SYNC: " + " and ".join(f"{label.get(n, n)} {n}" for n in speakers)
           + " speak Audio1 in Vietnamese. Sync the mouth, jaw, teeth and tongue to every syllable, vowel and consonant of their own "
             "lines only, with the emotion of the voice. Only the person named in the timeline moves their lips; everyone else keeps "
             "the mouth closed or still. The mouth closes in every silence.")
    tl = ["TIMELINE:"]
    for i, s in enumerate(segs):
        who = f"{s['speaker']} / {label.get(s['speaker'].upper(), '')} lipsync @Audio1"
        extra = f" {beats[i].rstrip('.')}." if beats.get(i) else ""
        tl.append(f"{_stamp(s['start'], s['end'])} Dialogue ({who}): \"{s['text']}\"{extra}")
    if total - segs[-1]["end"] > 0.3:
        tl.append(f"{_stamp(segs[-1]['end'], total)} No one speaks; mouths closed; a small reaction.{(' ' + beats['end']) if beats.get('end') else ''}")
    tail = (f"CONTINUITY & AVOID: every character matches their identity picture for the whole take. Avoid: {AVOID[style]}, "
            f"{AVOID_COMMON}.")
    text = "\n".join([head, "\n".join(refs), "\n".join(chars), lip, "\n".join(tl), tail])
    if len(text) > PROMPT_LIMIT:
        raise ValueError(f"prompt {len(text)} ký tự > {PROMPT_LIMIT}")
    return text
