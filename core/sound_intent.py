"""The Director's sound intent of a shot (knowledge/roles/director.md Đ9; from the "AI Director's Master Handbook" ch. V + VII, read
against this pipeline on 2026-09-26): sound is part of the emotional decision, not a post step. The handbook's shot list gives every
shot its sound next to its feeling — the music stops dead when the gun appears, no music while the villain thinks he has won, all sound
cut at the peak. Here the Director planned pictures only; the sound designer (core/sfx_plan.py) guessed the accents afterwards from the
scene text, and the one music silence (D6 `music_breath`) sat only before a TWIST section.

The field on a shot (optional — only where the moment needs sound to carry it):
    "sound": {"music": "keep|cut|in|breath", "sfx": ["short sound", ...], "why": "tiếng Việt: vì sao"}
- keep (default): the music goes on doing what it did.
- cut: the music stops dead at the start of the shot and stays out until a shot marked "in" (threat, a false calm, the moment
  before a reveal: silence makes the smallest sound loud).
- in: the music comes back at the start of the shot.
- breath: ~0.6 s of near-silence right before the shot, the music back on the shot itself (the hit lands) — same as D6.
- sfx: at most 3 sounds the moment needs (body sounds: breathing, a swallow, cloth, a grip; the one object sound: a click, a beep).
  The sound designer must place them, or say the library has none (never dropped in silence, CHUAN_XAY_DUNG luật 1).

The music part reaches the render only with the feature `sound_intent` on (not heard in a real cut yet — CHUAN luật 5); off, the
render's manifest says what was planned and not applied. The Director's answer is never refused for this field: bad parts are dropped
and reported.
"""
from typing import Dict, List, Optional, Sequence, Tuple

MUSIC = ("keep", "cut", "in", "breath")
MAX_SFX = 3
SFX_WINDOW = 0.6          # a requested sound counts as placed when a cue starts this close before the shot, or inside it
MOSTLY_SILENT = 0.5       # music held out for more than this share of the film: probably a forgotten "in"
MAX_OFF_S = 8.0           # trial #8 (2026-09-28): "cut" at shot 16, "cut" again at 21, 23, 25, 26, 27 and "in" only at 28 = 27 s without
                          # music (người dùng: "mất nhạc nền"). The Director meant a few silent moments, not one long hole: a silence
                          # ends MAX_OFF_S after it began, and a later "cut" opens a new one.
MIN_ON_S = 4.0            # after the music came back by itself, a "cut" this soon is the tail of the same long silence: ignored
                          # (#8 re-render: 3 silences of 8–9 s with 2 s of music between them still read as "no music")


def clean(value) -> Tuple[Optional[Dict], List[str]]:
    """(the usable sound intent or None, what was dropped and why). A plain "keep" with no sounds is None (nothing to do)."""
    if value is None:
        return None, []
    if not isinstance(value, dict):
        return None, ["sound phải là object {music, sfx, why} — bỏ"]
    out, problems = {}, []
    music = value.get("music")
    if isinstance(music, str) and music.strip().lower() in MUSIC:
        if music.strip().lower() != "keep":
            out["music"] = music.strip().lower()
    elif music is not None:
        problems.append(f"sound.music '{music}' không thuộc {'/'.join(MUSIC)} — bỏ")
    sfx = value.get("sfx")
    if isinstance(sfx, str):
        sfx = [sfx]
    if isinstance(sfx, list):
        items = [str(x).strip()[:60] for x in sfx if isinstance(x, (str, int, float)) and str(x).strip()]
        if len(items) > MAX_SFX:
            problems.append(f"sound.sfx có {len(items)} âm — giữ {MAX_SFX} âm đầu (âm cảm xúc ít mà đúng)")
        if items:
            out["sfx"] = items[:MAX_SFX]
    elif sfx is not None:
        problems.append("sound.sfx phải là danh sách chữ — bỏ")
    if out and isinstance(value.get("why"), str) and value["why"].strip():
        out["why"] = value["why"].strip()[:200]
    return (out or None), problems


def of(data: Dict) -> Dict:
    s = data.get("sound") if isinstance(data, dict) else None
    return s if isinstance(s, dict) else {}


def warnings(shots: List[Dict]) -> List[str]:
    """What the code can see in a plan (the shots of the whole film, in order). Soft: Director report + storyboard, never a refusal."""
    out: List[str] = []
    intents = [(k, clean(s.get("sound"))) for k, s in enumerate(shots, 1)]
    for k, (_, problems) in intents:
        out += [f"shot {k}: {p}" for p in problems]
    music_on, off_from, off_s, total, run, longest = True, None, 0.0, 0.0, 0.0, 0.0
    for k, (sound, _) in intents:
        dur = float(shots[k - 1].get("duration_s") or 0)
        m = (sound or {}).get("music")
        if m == "breath" and k == 1:
            out.append("shot 1: music 'breath' ở shot đầu — không có gì trước đó để lặng")
        if m == "in" and music_on:
            out.append(f"shot {k}: music 'in' nhưng nhạc đang có (không shot 'cut' nào trước) — không có tác dụng")
        if m == "cut":
            if not music_on:
                out.append(f"shot {k}: music 'cut' khi nhạc đã tắt từ shot {off_from} — không có tác dụng")
            else:
                music_on, off_from = False, k
        elif m == "in":
            music_on = True
        if not music_on:
            off_s += dur
            run += dur
            longest = max(longest, run)
        else:
            run = 0.0
        total += dur
    if total and off_s / total > MOSTLY_SILENT:
        out.append(f"nhạc tắt từ shot {off_from} ({off_s:.0f}/{total:.0f} s) — quá nửa phim không nhạc: thiếu shot 'in'?")
    if longest > MAX_OFF_S:
        out.append(f"nhạc tắt liền {longest:.0f} s — khoảng lặng dài hơn {MAX_OFF_S:g} s liền sẽ được bản dựng tự cho nhạc vào lại "
                   "(đặt 'in' sau khoảnh khắc cần lặng; muốn lặng lâu hơn thì chia thành nhiều khoảng 'cut' … 'in')")
    for k, s in enumerate(shots, 1):
        acting = s.get("performance") if isinstance(s.get("performance"), dict) else {}
        if acting.get("intensity") == 5 and not intents[k - 1][1][0]:
            out.append(f"shot {k}: đỉnh cảm xúc (cường độ 5) mà âm thanh không có ý đồ — nhạc giữ nguyên, không âm nào được nhấn "
                       "(im lặng, nhạc ngắt hay một âm nhỏ thường đẩy đỉnh mạnh hơn)")
    return out


def music_plan(datas: Sequence[Dict], durations: Sequence[float], transition: str = "cut", fade: float = 1.0,
               overlap_styles: Sequence[str] = (), max_off: float = MAX_OFF_S) -> Dict:
    """The music's silences on the render's timeline: {"off": [(start, end)], "breaths": [time], "planned": n, "auto_in": [time]}.
    `datas` and `durations` are the rendered shots in order (the clips' cut lengths); an overlapping transition shortens the timeline.
    A silence never runs longer than `max_off` (+ the rest of the shot it reaches): the music comes back at the next shot start and that
    time is listed in "auto_in" (the render's manifest and Step 5 say so — CHUAN luật 1)."""
    overlap = fade if transition in overlap_styles else 0.0
    t, off, breaths, planned, off_start, auto_in, ignored = 0.0, [], [], 0, None, [], []
    total = sum(float(d) for d in durations) - overlap * max(len(durations) - 1, 0)
    for data, d in zip(datas, durations):
        m = of(data).get("music")
        if m in ("cut", "in", "breath"):
            planned += 1
        if off_start is not None and m != "in" and max_off and t - off_start >= max_off - 1e-6:
            back = round(off_start + max_off, 2)          # too long a hole: the music is back MAX_OFF_S after it stopped
            off.append((off_start, back))
            auto_in.append(back)
            off_start = None
        if m == "cut" and off_start is None and auto_in and t - auto_in[-1] < MIN_ON_S - 1e-6:
            ignored.append(round(t, 2))
        elif m == "cut" and off_start is None:
            off_start = round(t, 2)
        elif m == "in" and off_start is not None:
            if t > off_start:
                off.append((off_start, round(t, 2)))
            off_start = None
        elif m == "breath" and t > 0.1 and off_start is None:
            breaths.append(round(t, 2))
        t += float(d) - overlap
    if off_start is not None and total > off_start:
        end = round(total, 2)
        if max_off and end - off_start > max_off + 1e-6 and not (off and off[-1][1] == off_start):
            auto_in.append(round(off_start + max_off, 2))
            end = round(off_start + max_off, 2)
        off.append((off_start, end))
    return {"off": off, "breaths": breaths, "planned": planned, "auto_in": auto_in, "ignored_cuts": ignored}


def unmet(scenes: Sequence[Dict], cues: Sequence[Dict]) -> List[Dict]:
    """Shots whose Director asked for sounds (sound.sfx) that no proposed cue covers: [{"idx", "sfx"}]. `scenes`: the sound
    designer's timeline rows (start, length, sound); `cues`: its proposal (at)."""
    out = []
    for s in scenes:
        wanted = of(s).get("sfx")
        if not wanted:
            continue
        a, b = float(s["start"]) - SFX_WINDOW, float(s["start"]) + float(s["length"])
        if not any(a <= float(c["at"]) <= b for c in cues):
            out.append({"idx": s.get("idx"), "sfx": wanted})
    return out
