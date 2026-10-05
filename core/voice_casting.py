"""S14.26 (05/10): Vietnamese voices cast from the scene analysis itself, 0 USD.

1. The Director (same Claude call — prompt block `prompt_block`, only when the feature is on) writes for every speaking character
   `voice_traits` {gender: nam|nữ|không rõ, age, personality}. Code checks the gender enum (`clean_traits`); a speaker without traits
   or with an unreadable gender is reported (diag + the returned report), never guessed.
2. `apply` casts by rule from data/voices_vi.json (`voice.voice_config`): men ↔ the male voices, women ↔ the female voices, in the file's
   order; the role with most lines takes the first free voice. The choice goes into the character's voice profile with "auto": True —
   the person changes it in Character Bible (a saved choice drops "auto" and is never overwritten, not even by a new analysis).
3. More roles of one gender than voices → a voice is used again with a `variant`: pitch ±2–3 semitones (ffmpeg after the TTS,
   `shift_pitch`, 0 USD) + a ClipAI `speed` (input_params 0.7–1.2), so two roles on one voice do not sound the same. `shared_voices`
   tells the screen which roles share a voice.
"""
import json
import os
from typing import Dict, List, Optional, Tuple

from . import voice

FEATURE = "auto_voice_cast"
GENDERS = ("nam", "nữ", "không rõ")
_ALIASES = {"nam": "nam", "male": "nam", "m": "nam", "man": "nam", "boy": "nam", "trai": "nam", "con trai": "nam",
            "nữ": "nữ", "nu": "nữ", "female": "nữ", "f": "nữ", "woman": "nữ", "girl": "nữ", "gái": "nữ", "con gái": "nữ",
            "không rõ": "không rõ", "khong ro": "không rõ", "unknown": "không rõ", "": "không rõ"}
_CONFIG_GENDER = {"male": "nam", "female": "nữ"}
# A voice used again: the n-th extra use takes VARIANTS[n-1] (cycled). Pitch in semitones (± 2–3: two roles on one voice must not sound
# the same, more would sound processed); speed inside ClipAI's 0.7–1.2.
VARIANTS = ({"pitch": 3.0, "speed": 1.05}, {"pitch": -3.0, "speed": 0.95}, {"pitch": 2.0, "speed": 1.1}, {"pitch": -2.0, "speed": 0.9})
SPEED_RANGE = (0.7, 1.2)
PROMPT_MARK = "Giọng lồng tiếng của nhân vật (`voice_traits`)"


def enabled() -> bool:
    from . import features
    return features.on(FEATURE)


def prompt_block() -> str:
    """Asked of the Director in the same call (feature on). Empty when off — the cached prompt stays the same."""
    if not enabled():
        return ""
    return (f"# {PROMPT_MARK}\n"
            "Với MỖI nhân vật trong `characters` có lời thoại, thêm trường `voice_traits`: "
            '`{"gender": "nam" | "nữ" | "không rõ", "age": "độ tuổi ngắn, vd \\"khoảng 20\\", \\"trung niên\\"", '
            '"personality": "tính cách thể hiện qua giọng, ≤ 8 từ, vd \\"lì lợm, nói nhanh\\""}` — tiếng Việt, lấy từ kịch bản/ảnh. '
            "Không đoán được giới tính thì ghi \"không rõ\" (không bịa). *Vì sao:* code dùng trường này gắn giọng tiếng Việt cho vai "
            "(0 USD, không cần lượt Claude riêng); thiếu trường thì vai đó chưa có giọng và người dùng phải chọn tay.")


def clean_traits(value) -> Tuple[Optional[Dict], List[str]]:
    """(traits {gender, age, personality} or None, problems). The gender is one of GENDERS; synonyms (male/female…) are mapped,
    anything else becomes "không rõ" and is reported. Never refuses the Director's answer (it is paid for)."""
    if value is None:
        return None, []
    if not isinstance(value, dict):
        return None, [f"voice_traits phải là object {{gender, age, personality}} — nhận {type(value).__name__}, bỏ"]
    problems = []
    raw = " ".join(str(value.get("gender") or "").strip().lower().split())
    gender = _ALIASES.get(raw)
    if gender is None:
        problems.append(f"voice_traits.gender '{value.get('gender')}' — chỉ nhận {', '.join(GENDERS)}; coi là 'không rõ'")
        gender = "không rõ"
    out = {"gender": gender}
    for key in ("age", "personality"):
        text = value.get(key)
        if text is not None and not isinstance(text, (dict, list)) and str(text).strip():
            out[key] = str(text).strip()[:80]
    return out, problems


def get_traits(row) -> Dict:
    try:
        return json.loads(row["voice_traits"] or "{}") or {}
    except (ValueError, KeyError, IndexError, TypeError):
        return {}


def persona(traits: Dict) -> str:
    """'nam, khoảng 25, nóng tính' — the profile's persona line written from the traits."""
    return ", ".join(x for x in (traits.get("gender") if traits.get("gender") != "không rõ" else "", traits.get("age"),
                                 traits.get("personality")) if x)


def _speaking_order(conn, project_id: int) -> List[str]:
    """Speakers (upper case) by number of lines, most first; ties by who speaks first."""
    count, first = {}, {}
    for n, ln in enumerate(voice.planned_lines(conn, project_id)):
        who = voice._norm(ln["speaker"])
        if not who:
            continue
        count[who] = count.get(who, 0) + 1
        first.setdefault(who, n)
    return sorted(count, key=lambda w: (-count[w], first[w]))


def pools() -> Dict[str, List[Dict]]:
    """gender (nam/nữ) -> the preferred voices of data/voices_vi.json in the file's order, retired ones left out."""
    out = {"nam": [], "nữ": []}
    for e in voice.voice_config().get("preferred") or []:
        g = _CONFIG_GENDER.get(str(e.get("gender") or "").lower())
        if g and e.get("id") is not None and not voice.retired(e):
            out[g].append(e)
    return out


def _variant(uses: int) -> Optional[Dict]:
    return None if uses <= 0 else dict(VARIANTS[(uses - 1) % len(VARIANTS)])


def store_traits(conn, project_id: int, characters: List[Dict]) -> Tuple[Dict[str, Dict], List[str]]:
    """Write every character's cleaned traits (a missing field keeps what was there). Returns (traits by NAME upper, problems)."""
    found, problems = {}, []
    for c in characters or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        if "voice_traits" not in c:
            continue
        traits, bad = clean_traits(c.get("voice_traits"))
        problems += [f"{c['name']}: {b}" for b in bad]
        if traits:
            found[voice._norm(c["name"])] = traits
            conn.execute("UPDATE characters SET voice_traits=? WHERE project_id=? AND name=?",
                         (json.dumps(traits, ensure_ascii=False), project_id, c["name"]))
    conn.commit()
    return found, problems


def apply(conn, project_id: int) -> Dict:
    """Cast every speaking character that has no voice, or an "auto" one that no longer fits its gender. A voice the person chose
    (no "auto") is never touched and counts as used. Returns {"assigned": [names], "kept": [names], "unknown": [names],
    "shared": {voice_id: [names]}, "problems": [..]}."""
    rows = {voice._norm(r["name"]): r for r in conn.execute("SELECT name, voice_profile, voice_traits FROM characters WHERE project_id=?",
                                                            (project_id,))}
    order = [w for w in _speaking_order(conn, project_id) if w in rows]
    report = {"assigned": [], "kept": [], "unknown": [], "shared": {}, "problems": []}
    by_gender = pools()
    if not by_gender["nam"] and not by_gender["nữ"]:
        report["problems"].append("không có giọng ưu tiên nào trong data/voices_vi.json (mục `preferred` có `gender`) — chưa tự gắn giọng; "
                                  "chọn tay ở Character Bible hoặc bấm 🤖 Claude chọn giọng")
        return report
    gender_of_voice = {e["id"]: g for g, pool in by_gender.items() for e in pool}
    uses: Dict[int, int] = {}
    todo = []
    for who in order:
        r = rows[who]
        prof, traits = voice.get_profile(r), get_traits(r)
        g = traits.get("gender")
        fits = prof.get("voice_id") and (not prof.get("auto") or gender_of_voice.get(prof["voice_id"]) == g)
        if fits:                                         # the person's choice, or an auto voice still right: kept (no re-paid TTS)
            uses[prof["voice_id"]] = uses.get(prof["voice_id"], 0) + 1
            report["kept"].append(r["name"])
        elif g not in ("nam", "nữ"):
            report["unknown"].append(r["name"])
        else:
            todo.append((r, g, traits))
    for r, g, traits in todo:
        pool = by_gender[g]
        if not pool:
            report["problems"].append(f"{r['name']}: data/voices_vi.json không có giọng {g} — chưa gắn giọng")
            continue
        pick = min(pool, key=lambda e: (uses.get(e["id"], 0), pool.index(e)))     # least used first, then the file's order
        n = uses.get(pick["id"], 0)
        uses[pick["id"]] = n + 1
        prof = {"voice_id": pick["id"], "voice_name": str(pick.get("name") or ""), "persona": persona(traits), "auto": True}
        var = _variant(n)
        if var:
            prof["variant"] = var
        voice.set_profile(conn, project_id, r["name"], prof)
        report["assigned"].append(r["name"])
    for who in report["unknown"]:
        report["problems"].append(f"{who}: chưa rõ giới tính (Director không ghi `voice_traits.gender` nam/nữ) — chưa tự gắn giọng; "
                                  "chọn tay hoặc 🤖 Claude chọn giọng")
    report["shared"] = shared_voices(conn, project_id)
    return report


def after_analysis(conn, project_id: int, obj: Dict) -> Optional[Dict]:
    """Called once the Director's answer is stored: traits saved, missing ones reported, voices cast by rule. None when the feature is
    off. A failure is written to diag and returned — the paid analysis stays saved."""
    if not enabled():
        return None
    from . import diag
    try:
        found, problems = store_traits(conn, project_id, obj.get("characters") or [])
        named = {voice._norm(c.get("name")) for c in obj.get("characters") or [] if isinstance(c, dict)}
        speakers = set(_speaking_order(conn, project_id))
        for c in obj.get("characters") or []:
            who = voice._norm(c.get("name")) if isinstance(c, dict) else ""
            if who in speakers and who not in found:
                problems.append(f"{c['name']}: Director thiếu trường `voice_traits` (giới tính/tuổi/tính cách) cho vai có thoại")
        report = apply(conn, project_id) if named else {"assigned": [], "kept": [], "unknown": [], "shared": {}, "problems": []}
        report["problems"] = problems + report["problems"]
    except Exception as e:  # noqa: BLE001 - reported below, the stored analysis must not be lost
        diag.record(conn, "director", "error", f"Tự gắn giọng theo luật lỗi: {e}", "auto_voice_cast", project_id)
        return {"assigned": [], "kept": [], "unknown": [], "shared": {}, "problems": [f"tự gắn giọng lỗi: {e}"], "error": str(e)}
    if report["assigned"]:
        diag.record(conn, "director", "info", "Tự gắn giọng (0 USD, data/voices_vi.json): " + ", ".join(report["assigned"]),
                    "auto_voice_cast", project_id)
    if report["shared"]:
        diag.record(conn, "director", "info", "Dùng chung giọng (có biến thể cao độ): " + share_text(report["shared"]),
                    "auto_voice_shared", project_id)
    if report["problems"]:
        diag.record(conn, "director", "warn", "Gắn giọng: " + "; ".join(report["problems"])[:380], "auto_voice_missing", project_id)
    return report


def shared_voices(conn, project_id: int) -> Dict[int, List[str]]:
    """voice_id -> names of the characters that use it, only where two or more share one."""
    out: Dict[int, List[str]] = {}
    for r in conn.execute("SELECT name, voice_profile FROM characters WHERE project_id=? ORDER BY id", (project_id,)):
        prof = voice.get_profile(r)
        if prof.get("voice_id"):
            out.setdefault(prof["voice_id"], []).append(r["name"])
    return {k: v for k, v in out.items() if len(v) > 1}


def variant_text(prof: Dict) -> str:
    var = prof.get("variant") or {}
    if not var.get("pitch"):
        return ""
    return f"biến thể {var['pitch']:+g} nửa cung" + (f", tốc độ ×{var['speed']:g}" if var.get("speed") else "")


def share_text(shared: Dict[int, List[str]]) -> str:
    return "; ".join(f"#{vid}: {', '.join(names)}" for vid, names in shared.items())


def tts_params(params: Dict, variant: Optional[Dict]) -> Dict:
    """The line's TTS input_params with the variant's speed folded in (multiplied with a directed pace, kept inside 0.7–1.2)."""
    if not variant or not variant.get("speed"):
        return params
    speed = float(params.get("speed") or 1.0) * float(variant["speed"])
    return {**params, "speed": round(min(max(speed, SPEED_RANGE[0]), SPEED_RANGE[1]), 3)}


# ---- pitch after the TTS (ffmpeg, 0 USD) ------------------------------------------------------------------------------------------
RATE = 44100


def pitch_filter(semitones: float) -> str:
    """Pitch up/down by `semitones` keeping the length: resample to a known rate, play it faster/slower (asetrate), back to the rate,
    then undo the speed change (atempo) — works with any ffmpeg build (no rubberband needed)."""
    ratio = 2 ** (float(semitones) / 12)
    return f"aresample={RATE},asetrate={RATE * ratio:.0f},aresample={RATE},atempo={1 / ratio:.6f}"


def build_pitch_cmd(src: str, dst: str, semitones: float, ffmpeg: str = "ffmpeg") -> List[str]:
    return [ffmpeg, "-y", "-hide_banner", "-i", src, "-af", pitch_filter(semitones), dst]


def shift_pitch(path: str, semitones: float, ffmpeg: Optional[str] = None) -> str:
    """Change the voice file in place (written to a temp file next to it, then swapped). Raises on an ffmpeg failure."""
    from . import ffmpeg_studio
    root, ext = os.path.splitext(path)
    tmp = f"{root}.pitch{ext}"
    ffmpeg_studio.run(build_pitch_cmd(path, tmp, semitones, ffmpeg or ffmpeg_studio.find_ffmpeg()))
    os.replace(tmp, path)
    return path
