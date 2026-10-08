"""N3 — nhạc nền theo ĐƯỜNG CẢM XÚC của cả câu chuyện (người dùng chốt 08/10, docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md mục 3).

The score follows the story's turns (opening → rising tension → the turn → climax → ending), not the shot list: one chapter of the arc
may run over several scenes / clips, and a chapter changes on the second the story turns in the real cut (music_timing.sections on the
render's lengths, minus the crossfades), landed on a downbeat when the beats are known. ONE continuous AI piece carries the whole arc
(music_timing.brief(arc=...) writes each chapter and its second); a separate track only where the material changes for good (a shot
marked `sound.music_source = "song"`: the dance on its own song) — joined by a crossfade, a held breath before a turn / climax, or a
cut when the Director wants the change sudden. Where the music comes in is read from the Director's `sound.music` (no seconds by hand,
#22 set 1,8 s / 18,08 s). Music is cheap next to video: DRAFTS drafts per AI track for the person to choose (still priced first and
written in the ledger: budget.audio_tag(conn, n, "music_v2")). Flag `music_story_arc` (off = the old behaviour).

    plan(p, pid, seconds=None, overlap=0, beats=None)  {"chapters", "turns", "tracks", "enter", "source", "notes"}
    save / load (data/<pid>/music_cues/cues.json)       the extra tracks the person chose (a file, optional start / join)
    assemble(tracks, total, out)                        the tracks laid into one music bed (ducked and mixed like one track)
    duck_depth(voice_db, duck)                          dB the music dips under a synthetic voice at that level (8–12 wanted)
"""
import json
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Optional, Sequence

STAGES = ("open", "build", "turn", "climax", "end")
STAGE_VI = {"open": "mở đầu", "build": "căng dần", "turn": "bước ngoặt", "climax": "cao trào", "end": "kết"}
STAGE_EN = {"open": "opening", "build": "rising tension", "turn": "the turn", "climax": "climax", "end": "ending"}
HEAD_STAGES = (   # first match wins: a "CAO TRÀO" heading is the climax even when it also says "căng"
    ("climax", re.compile(r"cao trào|climax|đỉnh điểm", re.I)),
    ("turn", re.compile(r"twist|bước ngoặt|\bngoặt\b|lật mặt|plot twist|\breveal", re.I)),
    ("end", re.compile(r"\bkết\b|kết thúc|hạ màn|ending|resolution|epilogue|outro", re.I)),
    ("open", re.compile(r"mở đầu|mở màn|\bhook\b|setup|giới thiệu|opening|\bintro", re.I)),
    ("build", re.compile(r"căng|xung đột|leo thang|truy đuổi|rising|conflict|tension|\bbuild", re.I)),
)
DRAFTS = 3            # music is cheap: three drafts per AI track for the person to choose from (người dùng 08/10)
SNAP_MAX = 0.5        # a turn moves onto a downbeat only this close (s)
XFADE = 1.0           # crossfade between two tracks (s)
BREATH = 0.6          # the held breath before a turn / climax track (same as D6 music_breath)
END_FADE = 0.3        # the outgoing track's fade before a breath


def _num(x) -> float:
    return round(float(x), 2)


def _sound(sec: Dict) -> Dict:
    sh = (sec.get("shots") or [{}])[0].get("data") or {}
    s = sh.get("sound")
    return s if isinstance(s, dict) else {}


def _material(sec: Dict) -> str:
    for sh in sec.get("shots") or []:
        d = sh.get("data") or {}
        snd = d.get("sound") if isinstance(d.get("sound"), dict) else {}
        if str(snd.get("music_source") or d.get("music_source") or "").lower() == "song":
            return "song"
    return "score"


def _peak(sec: Dict) -> bool:
    return any(((sh.get("data") or {}).get("performance") or {}).get("intensity") == 5 for sh in sec.get("shots") or []
               if isinstance((sh.get("data") or {}).get("performance"), dict))


def _stages(p, pid: int, secs: List[Dict]) -> (List[str], str):
    """One stage per script section and where it was read: the Director's `music.arc` > the section headings > position + peak."""
    from . import music_intent
    arc = music_intent.director_music(p, pid).get("arc")
    if isinstance(arc, list) and any(isinstance(a, dict) and a.get("stage") in STAGES for a in arc):
        marks = sorted((int(a.get("scene") or 0), a["stage"]) for a in arc if isinstance(a, dict) and a.get("stage") in STAGES)
        out = []
        for s in secs:
            st = "open"
            for sc, stage in marks:
                try:
                    if int(s["scene"]) >= sc:
                        st = stage
                except (TypeError, ValueError):
                    pass
            out.append(st)
        return out, "director"
    found = []
    for s in secs:
        st = next((stage for stage, rx in HEAD_STAGES if rx.search(str(s.get("heading") or ""))), None)
        found.append(st)
    if any(found):
        out, last = [], "open"
        for st in found:                      # a heading that says nothing continues the chapter before it
            last = st or last
            out.append(last)
        return out, "heading"
    n = len(secs)
    out = []
    for i, s in enumerate(secs):
        out.append("open" if i == 0 else "end" if i == n - 1 else "climax" if _peak(s) else "build")
    return out, "position"


def _join(sec: Dict, stage: str, material_changes: bool) -> str:
    snd = _sound(sec)
    if str(snd.get("enter") or "").lower() == "sudden":
        return "cut"
    if snd.get("music") == "breath" or (material_changes and stage in ("turn", "climax")):
        return "breath"
    return "crossfade"


def _snap(t: float, beats: Optional[Sequence[float]]) -> (float, bool):
    if not beats:
        return t, False
    b = min(beats, key=lambda x: abs(float(x) - t))
    return (_num(b), True) if abs(float(b) - t) <= SNAP_MAX else (t, False)


def plan(p, pid: int, seconds: Optional[Dict[int, float]] = None, overlap: float = 0.0,
         beats: Optional[Sequence[float]] = None) -> Dict:
    """The story's emotional arc on the cut. `seconds` = {scene_id: s} of the render (else the planned lengths), `overlap` = the
    crossfade between clips (s), `beats` = downbeats of the music on the film's timeline (ffmpeg_studio.music_beats)."""
    from . import music_timing
    secs = music_timing.sections(p, pid, seconds)
    if not secs:
        return {"chapters": [], "turns": [], "tracks": [], "enter": 0.0, "source": "none", "notes": ["chưa có shot nào có độ dài"]}
    k, starts, off, enter = 0, [], False, None
    for s in secs:                            # each section's start on the cut: every clip after the first overlaps the one before
        starts.append(_num(s["start"] - overlap * k))
        for sh in s["shots"]:
            m = ((sh.get("data") or {}).get("sound") or {}).get("music") if isinstance((sh.get("data") or {}).get("sound"), dict) else None
            off = True if m == "cut" else False if m == "in" else off
            if enter is None and not off:
                enter = _num(sh["start"] - overlap * k)
            k += 1
    film_end = _num(secs[-1]["end"] - overlap * (k - 1))
    stages, source = _stages(p, pid, secs)
    chapters: List[Dict] = []
    for i, (s, st) in enumerate(zip(secs, stages)):
        mat = _material(s)
        if chapters and chapters[-1]["stage"] == st and chapters[-1]["material"] == mat:
            ch = chapters[-1]
            if s["scene"] not in ch["scenes"]:
                ch["scenes"].append(s["scene"])
            ch["sections"].append(i)
            if s["end"] - s["start"] > ch["_longest"]:
                ch["_longest"], ch["mood"] = s["end"] - s["start"], s.get("mood") or ""
            continue
        start, snapped = (starts[i], False) if not chapters else _snap(starts[i], beats)
        changes = bool(chapters) and chapters[-1]["material"] != mat
        chapters.append({"stage": st, "stage_vi": STAGE_VI[st], "start": start, "end": None, "scenes": [s["scene"]], "sections": [i],
                         "material": mat, "join": "enter" if not chapters else _join(s, st, changes), "mood": s.get("mood") or "",
                         "snapped": snapped, "_longest": s["end"] - s["start"]})
    for a, b in zip(chapters, chapters[1:]):
        a["end"] = b["start"]
    chapters[-1]["end"] = film_end
    for c in chapters:
        c.pop("_longest", None)
    tracks: List[Dict] = []
    for i, c in enumerate(chapters):
        if tracks and tracks[-1]["material"] == c["material"]:
            tracks[-1]["chapters"].append(i)
            tracks[-1]["end"] = c["end"]
        else:
            tracks.append({"material": c["material"], "start": c["start"], "end": c["end"], "chapters": [i], "join": c["join"]})
    notes = []
    for t in tracks[1:]:
        if t["material"] == "score":
            notes.append(f"nhạc nền nối lại từ {t['start']} s sau bài gốc — cần bản nhạc riêng (cues.json) nếu muốn có nhạc ở đó")
    return {"chapters": chapters, "turns": [c["start"] for c in chapters[1:]], "tracks": tracks, "enter": enter or 0.0,
            "source": source, "notes": notes}


def brief_line(chapters: Sequence[Dict], clock) -> str:
    """The arc in one sentence of the brief (one continuous piece, each chapter from its second)."""
    return (" It is ONE continuous piece that carries the emotional arc of the whole story, not a new cue per shot: "
            + ", then ".join(f"{STAGE_EN[c['stage']]} from {clock(c['start'])}" for c in chapters) + ".")


# ---- the person's extra tracks -------------------------------------------------------------------------------------------------
def cues_dir(data_dir: str, project_id: int) -> str:
    d = os.path.join(data_dir, str(project_id), "music_cues")
    os.makedirs(d, exist_ok=True)
    return d


def save(data_dir: str, project_id: int, cues: Sequence[Dict]) -> str:
    """cues = [{"file": name in music_cues/, "start": s (optional — the story decides), "join": crossfade|breath|cut (optional)}]."""
    path = os.path.join(cues_dir(data_dir, project_id), "cues.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tracks": [{k: c[k] for k in ("file", "start", "join") if c.get(k) is not None} for c in cues]}, f, ensure_ascii=False)
    return path


def load(data_dir: str, project_id: int) -> List[Dict]:
    """The saved extra tracks whose file is there ({"path", "file", "start"?, "join"?}); none without cues.json."""
    d = os.path.join(data_dir, str(project_id), "music_cues")
    try:
        with open(os.path.join(d, "cues.json"), encoding="utf-8") as f:
            raw = json.load(f).get("tracks") or []
    except (OSError, ValueError, AttributeError):
        return []
    out = []
    for c in raw:
        if isinstance(c, dict) and c.get("file") and os.path.exists(os.path.join(d, c["file"])):
            out.append({**c, "path": os.path.join(d, c["file"])})
    return out


def price_tag(conn, ai_tracks: int = 1) -> str:
    """What the drafts of the arc cost, shown before the click (luật chi phí)."""
    from . import budget
    return budget.audio_tag(conn, DRAFTS * max(ai_tracks, 1), "music_v2")


# ---- one music bed --------------------------------------------------------------------------------------------------------------
def bed_cmd(tracks: Sequence[Dict], total: float, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """tracks = [{"path", "start" (film s), "join"}], the first is the main music. The bed starts at the first track's start; each
    track plays to the next one's change: crossfade = XFADE s across the change, breath = the old one fades out BREATH s before and the
    new one comes in on the change, cut = straight on the change."""
    t0 = float(tracks[0]["start"])
    length = max(float(total) - t0, 0.5)
    cmd, parts, labels = [ffmpeg, "-y", "-loglevel", "error"], [], []
    for i, t in enumerate(tracks):
        s = float(t["start"]) - t0
        join = t.get("join") if i else "enter"
        pos = max(s - XFADE / 2, 0.0) if join == "crossfade" else s
        fin = XFADE if join == "crossfade" else 0.05
        nxt = tracks[i + 1] if i + 1 < len(tracks) else None
        if nxt is None:
            end, fout = length, 0.0
        else:
            ns, nj = float(nxt["start"]) - t0, nxt.get("join") or "crossfade"
            end, fout = ((ns + XFADE / 2, XFADE) if nj == "crossfade" else (ns - BREATH, END_FADE) if nj == "breath" else (ns, 0.05))
        dur = max(end - pos, 0.1)
        chain = f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={fin:.3f}"
        if fout:
            chain += f",afade=t=out:st={max(dur - fout, 0):.3f}:d={fout:.3f}"
        ms = int(round(pos * 1000))
        chain += (f",adelay={ms}|{ms}" if ms else "") + f"[t{i}]"
        cmd += ["-i", t["path"]]
        parts.append(chain)
        labels.append(f"[t{i}]")
    parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,apad=whole_dur={length:.3f},"
                 f"atrim=0:{length:.3f}[a]")
    return cmd + ["-filter_complex", ";".join(parts), "-map", "[a]", "-t", f"{length:.3f}", "-c:a", "pcm_s16le", out]


def assemble(tracks: Sequence[Dict], total: float, out: str) -> str:
    from . import ffmpeg_studio
    ffmpeg_studio.run(bed_cmd(tracks, total, out, ffmpeg_studio.find_ffmpeg()))
    return out


# ---- measuring ------------------------------------------------------------------------------------------------------------------
def rms_db(path: str, a: float, b: float) -> float:
    """RMS level (dBFS) of [a, b] s of a file; −120 for digital silence."""
    from . import ffmpeg_studio
    proc = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-hide_banner", "-i", path, "-af", f"atrim={a}:{b},astats=metadata=0",
                           "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    vals = re.findall(r"RMS level dB:\s*(-?inf|-?[\d.]+)", proc.stderr or "")
    if not vals:
        raise RuntimeError("không đo được RMS: " + (proc.stderr or "")[-300:])
    return -120.0 if "inf" in vals[-1] else float(vals[-1])


def duck_depth(voice_db: float, duck: Optional[str] = None) -> float:
    """How many dB the music dips under a voice of `voice_db` dBFS RMS with the `duck` sidechain (default ffmpeg_studio.duck_filter()).
    Synthetic signals: the voice = band-passed pink noise with 4 Hz syllables (3–9 s of 12), the music = a two-tone pad; the dip is the
    music's level before the voice minus its level under it (the compressor's gain follows the key only, not the music's level)."""
    from . import ffmpeg_studio
    ff = ffmpeg_studio.find_ffmpeg()
    duck = duck or ffmpeg_studio.duck_filter()
    with tempfile.TemporaryDirectory() as d:
        raw, v, m, o = (os.path.join(d, n) for n in ("raw.wav", "v.wav", "m.wav", "o.wav"))
        ffmpeg_studio.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anoisesrc=c=pink:a=1:d=6:r=44100:seed=7",
                           "-af", "highpass=f=200,lowpass=f=3500,volume='0.6+0.4*sin(2*PI*4*t)':eval=frame,adelay=3000|3000,apad=whole_dur=12",
                           "-ac", "2", raw])
        gain = voice_db - rms_db(raw, 3.5, 8.5)
        ffmpeg_studio.run([ff, "-y", "-loglevel", "error", "-i", raw, "-af", f"volume={gain:.3f}dB", v])
        ffmpeg_studio.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=220:d=12:r=44100", "-f", "lavfi", "-i",
                           "sine=f=330:d=12:r=44100", "-filter_complex", "[0][1]amix=2,volume=0.3", "-ac", "2", m])
        ffmpeg_studio.run([ff, "-y", "-loglevel", "error", "-i", m, "-i", v, "-filter_complex", f"[1:a]apad[k];[0:a][k]{duck}[o]",
                           "-map", "[o]", o])
        return round(rms_db(o, 0.5, 2.5) - rms_db(o, 4.0, 8.5), 2)
