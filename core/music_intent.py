"""What the score is FOR in this film — tone, motif, ending, how a cue enters — read from the project, never assumed from #8 (S0.15 lượt 2,
gợi ý M1–M8, research/craft/draft/nhac_luot2_doi_chieu.md; người dùng duyệt 2026-09-29 "làm nốt hoàn thiện").

Why this module: the timed brief (core/music_timing.py) was written for trial #8, a love drama, and its answer became every film's
default: "vertical Free Fire short drama", "one love motif … full at the end", a flashback always "dreamy and warm", the last shot
always "resolution … hopeful", a tempo ceiling of 110 BPM, and the draft scorer rewarding only a RISE at each turn. A comedy, an
action piece or an MV got the same love-drama score. Here every one of those is a choice with a condition and a reason:

    read_tone(p, pid, secs)       {"tone", "also", "why", "source"} — Director's `music.tone` > project genre > words of moods/intents
    plan(p, pid, secs)            tone + profile (film noun, BPM ceiling, colour, turn manner) + motif + ending, and `notes` for what
                                  was missing (CHUAN luật 1: a neutral brief says it is neutral and why)
    turn_dirs(secs, styles)       per section turn: "up" | "down" | "change" (score_draft checks the change goes the way asked — M3)
    spotting_sheet(...)           the cue sheet a person can read before any paid draft (M8)

Where the explicit choices come from (all optional): the Director's JSON root `music` {"tone", "motif", "ending"} (prompt 19 / 17),
and on a shot `sound` {"music_fn", "enter", "bed"} (core/sound_intent.py). Nothing here calls a model.
"""
import json
import re
from typing import Dict, List, Optional, Sequence

TONES = {
    # film: the noun in the brief's first line · bpm_max: tempo ceiling (drama: #8 found 137 BPM too fast for a drama; comedy / action
    # / MV / promo move faster — nhac_luot2 C4) · colour: one line of how this kind of film uses music (nhac_theo_the_loai.md) ·
    # manner: how a section turn sounds unless the Director says otherwise · ending: the default last beat (M2)
    "drama": {"film": "short drama", "bpm_max": 110, "breathe": True, "ending": "resolve",
              "colour": "",
              "manner": "follow the story's emotion, no abrupt stops or jarring jumps"},
    "comedy": {"film": "short comedy", "bpm_max": 132, "breathe": False, "ending": "button",
               "colour": "Comic timing: play it straight-faced under the jokes; the instrument colour (pizzicato, marimba, plucks, "
                         "bouncy bass) says it is funny; stop dead right before a punchline and land back on the next cut.",
               "manner": "quick comic stops and restarts are welcome on the jokes"},
    "action": {"film": "action short", "bpm_max": 140, "breathe": False, "ending": "hit",
               "colour": "Driving percussion and a low pulse; pull back under the lines, hit with the cuts.",
               "manner": "punchy, the changes land on the cut"},
    "music_video": {"film": "music video", "bpm_max": 140, "breathe": False, "ending": "hit",
                    "colour": "The music leads and the pictures follow its sections.",
                    "manner": "the song's own sections set the turns"},
    "commercial": {"film": "promo", "bpm_max": 140, "breathe": False, "ending": "hit",
                   "colour": "Clear, confident energy; the product moment gets the biggest lift.",
                   "manner": "clear lifts on the turns"},
    # #24 (08/10, teaser Halloween "Trồi lên & Khóc ai oán"): with no horror tone the Director wrote "commercial" + "button" and the
    # three drafts came out "clear, confident energy … a short comic final hit" under a ghost crawling out of a well. Horror scores
    # by dread and silence: the scare is a stinger on the cut, the quiet before it is part of the score.
    "horror": {"film": "horror teaser", "bpm_max": 100, "breathe": False, "ending": "cliffhanger",
               "colour": "Horror: dread, not energy. Low drones, dissonant and bowed-metal strings, distant reverb, eerie textures; drop "
                         "to near-silence just before each scare and hit a sharp stinger exactly on it. No upbeat lift, no comic or "
                         "playful colour, no heroic theme.",
               "manner": "near-silence before a scare, then a sudden stinger on it"},
}
NEUTRAL = {"film": "short film", "bpm_max": 120, "breathe": False, "ending": "close", "colour": "", "manner": "follow the story"}

GENRE_TONE = {"MUSIC_VIDEO": "music_video", "COMMERCIAL": "commercial"}     # SHORT_FORM / CINEMA_DRAMA / ANIMATION say the format, not the tone

WORDS = {   # words of the Director's moods / emotional intents / headings that tell the tone (Vietnamese + English)
    "comedy": re.compile(r"comed|comic|funny|humou?r|\bgag\b|punchline|cheeky|prank|hài hước|hài kịch|gây hài|buồn cười|bật cười|gây cười|trò khăm|chơi khăm|"
                         r"tấu hài|lầy lội|ngớ ngẩn", re.I),
    "drama": re.compile(r"drama|grief|heartbr|tears?\b|\bcry|sorrow|betray|đau|khóc|nước mắt|tổn thương|hy sinh|tuyệt vọng|vỡ òa|nghẹn|"
                        r"phản bội|tình yêu|mất mát|hiểu lầm", re.I),
    "horror": re.compile(r"horror|creepy|eerie|dread|jump-?scare|ghost|haunt|kinh dị|rùng rợn|rợn người|ma quái|ghê rợn|"
                         r"rùng mình|hù dọa|hồn ma|bóng ma|quỷ|yêu nữ|tà linh|ai oán|halloween", re.I),
    "action": re.compile(r"\baction|fight|battle|chase|combat|shoot-?out|hành động|giao tranh|đấu súng|truy đuổi|đánh nhau|"
                         r"quyết chiến", re.I),
}
ROMANCE = re.compile(r"\blove\b|romance|tình yêu|người yêu|yêu thương|yêu anh|yêu em|ôm lấy|embrace", re.I)
WARM_END = re.compile(r"ấm áp|hạnh phúc|hóa giải|thấu hiểu|đoàn tụ|reunion|embrace|hope|warm|relief", re.I)

ENDINGS = {
    # kind -> (the last story beat, the tail). Every tail keeps "final hit at" (core/music_fit.py reads the end mark from it).
    "resolve": ("resolution: {theme} in full, warm and hopeful", "End cleanly on a final hit at {end}, no long tail."),
    "open": ("the end stays unresolved: hold the tension, no resolution", "Stop on an unresolved final hit at {end}, no tail."),
    "cliffhanger": ("cliffhanger: tension rising to the very last frame", "Cut off on a sharp unresolved final hit at {end}, no tail."),
    "button": ("the last gag: a short comic button right on it", "End on a short comic final hit at {end}, no tail."),
    "hit": ("finale: the fullest statement, then one strong hit", "End cleanly on a final hit at {end}, no long tail."),
    "close": ("the music closes simply", "End cleanly on a final hit at {end}, no long tail."),
}

FUNCTIONS = {   # the Director's `sound.music_fn` (a closed list the code can translate): why the music is there (M5, spotting [51][52])
    "tension": "builds pressure, holding back",
    "hide": "hides what the character feels: calm on top, uneasy underneath",
    "release": "releases: opens up, fuller",
    "reveal": "the reveal: one clear change of colour",
    "time": "time passes: a steady figure moving on",
    "place": "sets the place",
    "comic": "comic timing: straight-faced, stops before the punchline",
    "memory": "memory: a thinner, distant colour",
}
FUNCTIONS_VI = {"tension": "dồn nén", "hide": "che giấu cảm xúc", "release": "giải tỏa", "reveal": "lật mở", "time": "trôi thời gian",
                "place": "đặt nơi chốn", "comic": "nhịp hài", "memory": "ký ức"}
ENTERS = ("soft", "sudden")
BEDS = ("continuous", "sparse")
TONE_VI = {"drama": "chính kịch", "comedy": "hài", "horror": "kinh dị", "action": "hành động", "music_video": "MV", "commercial": "quảng cáo", None: "chưa rõ"}


def _json(text) -> Dict:
    try:
        v = json.loads(text or "{}")
    except (TypeError, ValueError):
        return {}
    return v if isinstance(v, dict) else {}


def director_music(p, pid: int) -> Dict:
    """The Director's optional root `music` {"tone", "motif", "ending"} (single call: director_raw; two passes: the kept intent)."""
    row = p.project(pid)
    keys = row.keys()
    for obj in (_json(row["director_raw"] if "director_raw" in keys else None),
                _json(row["director_intent_raw"] if "director_intent_raw" in keys else None).get("intent") or {}):
        m = obj.get("music") if isinstance(obj, dict) else None
        if isinstance(m, dict) and m:
            return m
    return {}


def _text(sec: Dict) -> str:
    return " ".join(str(sec.get(k) or "") for k in ("mood", "intent", "heading"))


def read_tone(p, pid: int, secs: Sequence[Dict], music: Optional[Dict] = None) -> Dict:
    """The film's tone and where it was read. Order: the Director's `music.tone` > a genre that IS a tone (MV, promo) > the words of
    the sections' moods / intents (the tone found in the most sections; a second one that is also present is kept in "also")."""
    music = director_music(p, pid) if music is None else music
    t = str(music.get("tone") or "").strip().lower()
    scary = sum(1 for s in secs if WORDS["horror"].search(_text(s)))
    if t == "commercial" and secs and scary * 2 >= len(secs):
        # #24: "commercial" says it is a promo (the format), the moods say what it sounds like — a horror teaser is scored as horror
        return {"tone": "horror", "also": ["commercial"], "source": "mood",
                "why": f"Đạo diễn ghi music.tone = commercial (định dạng quảng bá) nhưng {scary}/{len(secs)} cảnh có chữ kinh dị trong "
                       "mood / ý đồ → nhạc kinh dị"}
    if t in TONES:
        return {"tone": t, "also": [], "why": f"Đạo diễn ghi music.tone = {t}", "source": "director"}
    genre = (p.project(pid)["genre"] or "").upper()
    if genre in GENRE_TONE:
        return {"tone": GENRE_TONE[genre], "also": [], "why": f"thể loại dự án {genre}", "source": "genre"}
    counts = {k: sum(1 for s in secs if rx.search(_text(s))) for k, rx in WORDS.items()}
    ranked = sorted((n, k) for k, n in counts.items() if n)
    if not ranked:
        return {"tone": None, "also": [], "source": "none",
                "why": "không đọc được giọng điệu: dự án không có music.tone, thể loại dự án không nói giọng điệu"
                       + (f" ({genre})" if genre else "") + ", mood / ý đồ cảm xúc các cảnh trống hoặc không có chữ hài / chính kịch / hành động"}
    ranked.reverse()
    best_n = ranked[0][0]
    top = sorted(k for n, k in ranked if n == best_n)
    # a tie between comedy and something else: the comedy decides the colour (a funny film with a tense bit stays funny); then horror
    # (a ghost that cries "ai oán" is horror, not a drama — #24)
    tone = "comedy" if "comedy" in top else "horror" if "horror" in top else top[0]
    also = [k for n, k in ranked if k != tone]
    return {"tone": tone, "also": also, "source": "mood",
            "why": f"{counts[tone]}/{len(secs)} cảnh có chữ {TONE_VI[tone]} trong mood / ý đồ"
                   + (" (còn: " + ", ".join(f"{TONE_VI[k]} {counts[k]}" for k in also) + ")" if also else "")}


def motif(secs: Sequence[Dict], tone: Optional[str], music: Dict) -> Dict:
    """{"text": the theme's name or None, "why"}. A motif is a choice: the Director names it (music.motif), or — only for a drama whose
    story is about love (its intents say so) — "love motif", the #8 answer, kept where it fits. Otherwise none is asked for."""
    m = music.get("motif")
    if isinstance(m, str) and m.strip():
        name = m.strip()[:80]
        return {"text": name if "motif" in name.lower() or "theme" in name.lower() else f"{name} motif", "why": "Đạo diễn đặt motif"}
    if tone == "drama" and any(ROMANCE.search(_text(s)) for s in secs):
        return {"text": "love motif", "why": "chính kịch có chuyện tình (ý đồ cảnh nói tới tình yêu / cái ôm) → một motif tình yêu"}
    return {"text": None, "why": "không đặt motif (Đạo diễn không đặt; không phải chính kịch tình cảm)"}


def ending(secs: Sequence[Dict], tone: Optional[str], music: Dict) -> Dict:
    """{"kind", "why"} of the last beat (M2). The Director's `music.ending` decides; a drama ends in resolution only when its last
    scene is warm (else it is left open); other tones take their profile's ending."""
    k = str(music.get("ending") or "").strip().lower()
    if k == "button" and tone != "comedy":
        # #24: "button" is a comic button — on a horror teaser it asked for "a short comic final hit"; the tone's own ending instead
        kind = TONES.get(tone or "", NEUTRAL)["ending"]
        return {"kind": kind, "why": f"Đạo diễn ghi music.ending = button nhưng phim không phải hài ({TONE_VI.get(tone, tone)}) → {kind}"}
    if k in ENDINGS:
        return {"kind": k, "why": f"Đạo diễn ghi music.ending = {k}"}
    if tone == "drama":
        last = secs[-1] if secs else {}
        if WARM_END.search(_text(last)):
            return {"kind": "resolve", "why": "cảnh cuối ấm / hóa giải → nhạc giải quyết"}
        return {"kind": "open", "why": "chính kịch mà cảnh cuối không ấm / không hóa giải → kết mở, không tự thêm 'hopeful'"}
    prof = TONES.get(tone or "", NEUTRAL)
    return {"kind": prof["ending"], "why": f"mặc định của giọng điệu {TONE_VI.get(tone, tone)}"}


def plan(p, pid: int, secs: Sequence[Dict]) -> Dict:
    music = director_music(p, pid)
    tone = read_tone(p, pid, secs, music)
    prof = TONES.get(tone["tone"] or "", NEUTRAL)
    row = p.project(pid)
    keys = row.keys()
    fmt = " ".join(x for x in ("vertical" if (row["aspect"] if "aspect" in keys else "") == "9:16" else "",
                               "Free Fire" if (row["game"] if "game" in keys else "") == "FF" else "", prof["film"]) if x)
    notes = []
    if tone["tone"] is None:
        notes.append("giọng điệu chưa rõ — brief nhạc trung tính (" + tone["why"] + "); Đạo diễn ghi `music.tone` hoặc mood cảnh để brief "
                     "đọc được")
    if tone["tone"] == "music_video":
        notes.append("MV: nhạc thường có trước và hình theo nhạc — brief theo cảnh chỉ là nháp; chấm bản nháp theo điểm đổi đoạn không áp")
    return {"tone": tone, "profile": prof, "format": fmt, "motif": motif(secs, tone["tone"], music),
            "ending": ending(secs, tone["tone"], music), "music": music, "notes": notes}


# ---- turns: which way the music should change (M3) --------------------------------------------------------------------------------
ENERGY = ((re.compile(r"^(hushed|fragile|sparse|almost silent)|very sparse", re.I), 1),
          (re.compile(r"^(urgent|heartbreak|warm resolution|tense, driving|comic|driving)", re.I), 3))


def energy(style: str) -> int:
    for rx, level in ENERGY:
        if rx.search(style or ""):
            return level
    return 2


def _first_sound(sec: Dict) -> Dict:
    sh = (sec.get("shots") or [{}])[0].get("data") or {}
    s = sh.get("sound")
    return s if isinstance(s, dict) else {}


def turn_dirs(secs: Sequence[Dict], styles: Sequence[str]) -> List[str]:
    """For each section turn (sections 2…n): "down" when the new section opens on the Director's music cut or is quieter than the one
    before, "up" when louder, "change" when the same level (any clear change counts). S0.12: a turn can be a drop into silence."""
    out = []
    for i in range(1, len(secs)):
        if _first_sound(secs[i]).get("music") == "cut":
            out.append("down")
            continue
        a, b = energy(styles[i - 1]), energy(styles[i])
        out.append("up" if b > a else "down" if b < a else "change")
    return out


def enter_kind(sec: Dict) -> str:
    e = str(_first_sound(sec).get("enter") or "").lower()
    return e if e in ENTERS else "soft"


# ---- M8: the spotting sheet ------------------------------------------------------------------------------------------------------
def _clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def spotting_sheet(p, pid: int, b: Dict, build: Optional[str] = None, today: Optional[str] = None) -> str:
    """The brief as a cue sheet a person can read and comment on before a paid draft (pitch.dog [52]: which cut it is for, cue in/out
    + how, the one-line function, what changes inside, where the music deliberately stops). `b` = music_timing.brief()."""
    import datetime
    mi = b.get("intent") or {}
    tone = mi.get("tone") or {}
    lines = [f"# Phiếu spotting nhạc — dự án #{pid}", "",
             f"- Bản dựng: {build or 'theo bảng shot (chưa có bản dựng)'} · độ dài {b.get('film_s', 0):.1f} s · ngày "
             f"{today or datetime.date.today().isoformat()} · trạng thái: **đề xuất** (chưa tạo nhạc)",
             f"- Giọng điệu: **{TONE_VI.get(tone.get('tone'), tone.get('tone'))}** — {tone.get('why', '')}",
             f"- Motif: {(mi.get('motif') or {}).get('text') or 'không'} — {(mi.get('motif') or {}).get('why', '')}",
             f"- Kết: {(mi.get('ending') or {}).get('kind', '')} — {(mi.get('ending') or {}).get('why', '')}",
             f"- Nhịp: {b.get('bpm')} BPM (trần {(mi.get('profile') or {}).get('bpm_max')}), lệch vạch ô nhịp tối đa {b.get('error_s')} s"]
    lines += [f"- ⚠ {n}" for n in mi.get("notes") or []]
    lines += ["", "| Cue | Vào | Ra | Kiểu vào | Đổi so với trước | Chức năng / màu nhạc | Bên trong |", "|---|---|---|---|---|---|---|"]
    secs, styles, dirs = b.get("sections") or [], b.get("styles") or [], b.get("turn_dirs") or []
    beats = b.get("beat_times") or []
    for i, s in enumerate(secs):
        inside = [text for t, text in beats if s["start"] <= t < s["end"] or (i == len(secs) - 1 and t >= s["start"])]
        fn = str(_first_sound(s).get("music_fn") or "")
        why = FUNCTIONS_VI.get(fn, "")
        lines.append(f"| 1M{i + 1} | {_clock(s['start'])} | {_clock(s['end'])} | {'—' if i == 0 else enter_kind(s)} | "
                     f"{'—' if i == 0 else dirs[i - 1] if i - 1 < len(dirs) else ''} | "
                     f"{(why + ' · ') if why else ''}{styles[i] if i < len(styles) else ''} | {'; '.join(inside) or '—'} |")
    off = [text for _, text in beats if "almost silent" in text]
    lines += ["", "Chỗ nhạc cố ý lặng / rút: " + ("; ".join(off) if off else "không có (Đạo diễn chưa đặt `sound.music=cut`)"),
              "", "Góp ý: sửa mood / `sound` của shot ở Bước 1 hoặc prompt nhạc ở Bước 5 rồi mới tạo bản nháp (tốn credit)."]
    return "\n".join(lines) + "\n"
