"""Does the dialogue of a scene fit into its clip?

Lines like "LYRA: Có thứ gì đó đang theo chúng ta." are taken from the scene text. A clip that is shorter than the
time needed to say them gets a cut-off or rushed line, and the credit for that clip is wasted. No model is called:
speaking time is estimated from the number of syllables (Vietnamese: about one word per syllable).

  ok      fits with a little room
  tight   fits, barely
  extend  too long for the planned duration but the model can make a longer clip -> raise the duration
  split   too long even for the model's longest clip -> the scene has to be split (or the lines shortened)
"""
import json
import math
import os
import re
from typing import Dict, List, Tuple

RATE = float(os.environ.get("DIALOGUE_SYLLABLES_PER_SEC", "3.5"))     # comfortable speaking speed
BREATH = 0.5                                                          # seconds of room around the lines
DEFAULT_PLANNED = 5.0
_LINE = re.compile(r"^\s*([^:\n]{1,30}?)\s*:\s*(.+?)\s*$")


NOT_SPEAKERS = {"TEXT CUỐI", "CARD CUỐI", "CHỮ CUỐI", "END CARD", "GHI CHÚ", "LƯU Ý", "THỜI LƯỢNG", "NHÂN VẬT", "BỐI CẢNH",
                "ĐỊA ĐIỂM", "THỜI GIAN", "GÓC MÁY", "MÔ TẢ", "KỊCH BẢN", "NOTE", "CAMERA",
                "HỆ THỐNG", "SYSTEM", "THÔNG BÁO", "HUD", "CẤU TRÚC", "FLASHBACK", "FLASHBACK NGẮN",   # on-screen text, not a voice
                "TEXT", "CHỮ", "CAPTION", "ON-SCREEN TEXT", "ON SCREEN TEXT",
                # S14.4 C1b (04/10): text cards of a short ad are not a voice either (one list for every reader)
                "CTA", "CTA TEXT", "CTA_TEXT", "TITLE", "SUPER", "SUBTITLE", "LOGO", "CHỮ TRÊN MÀN", "CHỮ MÀN HÌNH",
                "CHỮ TRÊN MÀN HÌNH", "TIÊU ĐỀ", "PHỤ ĐỀ"}
# Names that only mean "on-screen text" WITH their accents: 'CHỮ' folds to 'chu', which is also a person's name (Chu).
_ACCENT_ONLY = {"chu"}


def _fold(text: str) -> str:
    """'Chữ trên màn' -> 'chu tren man'; 'CTA_TEXT' / 'CTA-TEXT' -> 'cta text' (same words, no accents, no case)."""
    import unicodedata
    text = unicodedata.normalize("NFD", (text or "").replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[\W_]+", " ", text.lower())).strip()


_NOT_SPEAKERS_FOLDED = {_fold(n) for n in NOT_SPEAKERS} - _ACCENT_ONLY


def is_non_speaker(name: str) -> bool:
    """True for a heading / on-screen text label ('CTA_TEXT', 'Chữ trên màn', 'TITLE'), compared without accents — except
    the words in `_ACCENT_ONLY`, matched with their accents only so a character named 'CHU' still speaks."""
    raw = re.sub(r"\s+", " ", str(name or "")).strip()
    return raw.upper() in NOT_SPEAKERS or _fold(raw) in _NOT_SPEAKERS_FOLDED


def _is_speaker(name: str) -> bool:
    """'KELLY' (capitals, the usual script style) or 'Kelly' / 'Ông Lão Orin' (every word capitalised, at most 3 words) — not a
    heading such as 'Ghi chú' or 'TEXT CUỐI'."""
    if not name or not any(ch.isalpha() for ch in name) or is_non_speaker(name):
        return False
    if name == name.upper():
        return True
    words = name.split()
    return len(words) <= 3 and all(w[0].isupper() for w in words if w)


def lines(text: str) -> List[Tuple[str, str]]:
    """(speaker, line) for every 'NAME: words' row. Speakers written in capitals ('KELLY:') or capitalised ('Kelly:');
    the speaker is returned in capitals so it matches the Character Bible."""
    out = []
    for row in (text or "").splitlines():
        m = _LINE.match(row)
        if not m:
            continue
        name, said = m.group(1).strip(), m.group(2).strip().strip('"“”')
        name = re.sub(r"\s*\(.*?\)\s*", "", name).strip()
        if _is_speaker(name) and said:
            out.append((name.upper(), said))
    return out


def scene_lines(scene_data: Dict) -> List[Tuple[str, str]]:
    """The scene's dialogue: the Director's structured `dialogue` list when there is one (v2), else the 'NAME: words' rows of
    the script text. Used by the length check, subtitles, voice-over and the motion prompt hint alike."""
    structured = scene_data.get("dialogue")
    if scene_data.get("shot_no") and not structured:
        return []            # v3 shot row: its lines are exactly `dialogue` (an action line must never be read as speech)
    if isinstance(structured, list) and structured:
        return [(str(d.get("speaker") or "").strip(), str(d.get("text") or "").strip()) for d in structured
                if isinstance(d, dict) and str(d.get("text") or "").strip()]
    return lines(scene_data.get("text", ""))


def norm(text: str) -> str:
    """A line compared as words only: quotes, case and spacing do not matter (the Director's copy vs the script's)."""
    return " ".join(re.sub(r"[\"“”'‘’«»]", "", str(text or "")).lower().split())


def syllables(said: str) -> int:
    return len(re.findall(r"\w+", said, re.UNICODE))


def needed_seconds(rows: List[Tuple[str, str]]) -> float:
    total = sum(syllables(said) for _, said in rows)
    return round(total / RATE + BREATH, 1) if total else 0.0


def max_clip_seconds(pipeline, project_id: int, scene_id=None) -> int:
    """Longest clip the scene's video model can make (per-scene model choice in v2; 15 s when unknown)."""
    from .adapters.clipai import effective_duration, resolve_model
    from .providers import ProviderError
    try:
        model = pipeline.project(project_id)["video_model"]
        if scene_id is not None:
            from . import model_router
            model = model_router.scene_choice(pipeline.conn, scene_id)["model"]
        canonical, family = resolve_model(model)[:2]
        return effective_duration(canonical, family, 999)
    except (ProviderError, ValueError, TypeError, KeyError):
        return 15


def voiced_seconds(voice: Dict[int, float], scene_id: int) -> float:
    """Real length of the scene's generated voice lines (seconds, gaps included) when all are made, else 0."""
    return float(voice.get(scene_id) or 0.0)


def check(pipeline, project_id: int, voice: Dict[int, float] = None) -> List[Dict]:
    """One entry per scene that has dialogue. `voice` = {scene_id: seconds of the real generated voice lines}: when known it
    replaces the syllable estimate (the clip is then sized to the actual voice)."""
    voice = voice or {}
    out = []
    for r in pipeline.conn.execute(
            "SELECT s.id, s.idx, s.data, m.duration_sec FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id"
            " WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall():
        data = json.loads(r["data"] or "{}")
        rows = scene_lines(data)
        if not rows:
            continue
        longest = max_clip_seconds(pipeline, project_id, r["id"])
        real = voiced_seconds(voice, r["id"])
        need = round(real + BREATH, 1) if real else needed_seconds(rows)
        planned = float(r["duration_sec"] or data.get("duration_s") or DEFAULT_PLANNED)
        if need > longest:
            status, advice = "split", f"Thoại cần ~{need:g}s nhưng model chỉ làm clip tối đa {longest}s: rút gọn thoại hoặc tách cảnh" \
                + (" (hoặc đổi cảnh này sang Seedance 2.5 — tối đa 30s — ở Bước 4)." if longest < 30 and need <= 30 else ".")
        elif need > planned:
            status, advice = "extend", f"Thoại cần ~{need:g}s, clip đang {planned:g}s: tăng lên {math.ceil(need)}s."
        elif need > planned * 0.9:
            status, advice = "tight", "Vừa khít, nên chừa thêm chút thời gian."
        else:
            status, advice = "ok", ""
        out.append({"scene_id": r["id"], "idx": r["idx"], "speakers": sorted({n for n, _ in rows if n}),
                    "syllables": sum(syllables(s) for _, s in rows), "needed": need, "planned": planned, "max": longest,
                    "target": min(math.ceil(need), longest), "status": status, "advice": advice, "measured": bool(real)})
    return out


def problems(entries: List[Dict]) -> List[Dict]:
    return [e for e in entries if e["status"] in ("extend", "split")]


def extend(pipeline, entries: List[Dict]) -> int:
    """Raise the planned duration of every 'extend' scene: the motion prompt's duration when the scene has one, and the
    scene's `duration_s` (marked as set by the person, so a motion prompt written later keeps it). Returns how many."""
    n = 0
    for e in entries:
        if e["status"] != "extend":
            continue
        cur = pipeline.conn.execute("UPDATE motion_prompts SET duration_sec=? WHERE scene_id=?", (e["target"], e["scene_id"]))
        row = pipeline.conn.execute("SELECT data FROM scenes WHERE id=?", (e["scene_id"],)).fetchone()
        if row is not None:
            data = json.loads(row["data"] or "{}")
            data["duration_s"] = e["target"]
            data["_user_locked"] = sorted(set(data.get("_user_locked") or []) | {"duration_s"})
            pipeline.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), e["scene_id"]))
        n += 1 if (cur.rowcount or row is not None) else 0
    pipeline.conn.commit()
    return n
