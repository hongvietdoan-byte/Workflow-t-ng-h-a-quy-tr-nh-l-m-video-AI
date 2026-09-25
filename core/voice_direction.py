"""Voice direction of a dubbed line (kế hoạch V4 GĐ4, knowledge/roles/director.md Đ5): the Director writes a `delivery` for a line —
the feeling, how strong (1–5), the pace, a pause before it, the word to stress, an optional Eleven v3 audio tag — and this module turns
it into what the TTS call accepts (feature `voice_direction`, OFF until a real test closes it; CHUAN_XAY_DUNG rule 5).

What the TTS can take (official sources, knowledge/sources.md GĐ4 [Đ20]–[Đ23]; ClipAI skill clipai-1.3.1 reference.md):
  - ClipAI `input_params`: speed 0.7..1.2, stability / similarity_boost / style 0..1.
  - Eleven v3 has only three stability modes: 0.0 Creative (most expressive, may drift), 0.5 Natural, 1.0 Robust (steady, ignores
    direction). Audio tags need Creative or Natural. The playground says speed does not apply to v3 — sent anyway (inside the allowed
    range it does no harm) and marked "chưa thử thật".
  - v3 reads no SSML <break>: a pause is written as "…", a stressed word in CAPITALS, a tag like [whispers] before the words it colours.
Subtitles keep the script's words: only the text sent to the TTS changes.
"""
import re
from typing import Dict, List, Optional, Tuple

PACES = {"slow": 0.9, "normal": None, "fast": 1.1}
# Eleven v3 audio tags that colour a line without adding a sound effect (a whitelist: anything else could be read out loud)
TAGS = ("whispers", "sighs", "shouts", "laughs", "crying", "sarcastic", "excited", "curious", "nervous", "angry", "sad", "calm",
        "gulps", "clears throat")
SHORT_LINE_WORDS = 3                         # director.md Đ5: lines this short get no tag / stress
CREATIVE, NATURAL = 0.0, 0.5                # v3 stability modes (Robust 1.0 ignores direction — never chosen for a directed line)


def clean(value) -> Tuple[Optional[Dict], List[str]]:
    """(the usable delivery or None, what was dropped). Never refuses the Director's answer."""
    if value is None:
        return None, []
    if not isinstance(value, dict):
        return None, ["delivery phải là object {emotion, intensity, pace, pause_before, stress, tag} — bỏ"]
    out, problems = {}, []
    if isinstance(value.get("emotion"), str) and value["emotion"].strip():
        out["emotion"] = value["emotion"].strip()
    raw = value.get("intensity")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and 1 <= raw <= 5:
        out["intensity"] = int(round(raw))
    elif raw is not None:
        problems.append(f"delivery.intensity '{raw}' không phải số 1–5 — bỏ")
    pace = str(value.get("pace") or "").strip().lower()
    if pace in PACES:
        out["pace"] = pace
    elif pace:
        problems.append(f"delivery.pace '{pace}' — chỉ nhận {', '.join(PACES)}")
    if value.get("pause_before") is True:
        out["pause_before"] = True
    if isinstance(value.get("stress"), str) and value["stress"].strip():
        out["stress"] = value["stress"].strip()
    tag = str(value.get("tag") or "").strip().strip("[]").lower()
    if tag in TAGS:
        out["tag"] = tag
    elif tag:
        problems.append(f"delivery.tag '{tag}' không nằm trong danh sách an toàn ({', '.join(TAGS)}) — bỏ")
    return (out or None), problems


def params(delivery: Optional[Dict], model: str = "eleven_v3") -> Dict:
    """ClipAI TTS input_params of a directed line (empty = the voice's defaults, as before)."""
    if not delivery:
        return {}
    out: Dict = {}
    speed = PACES.get(delivery.get("pace") or "normal")
    if speed:
        out["speed"] = speed
    level = delivery.get("intensity")
    if model == "eleven_v3" and (level or delivery.get("tag")):
        out["stability"] = CREATIVE if (level or 0) >= 5 else NATURAL   # Creative "may hallucinate" (ElevenLabs): the peak line only
    return out


def spoken_text(text: str, delivery: Optional[Dict], model: str = "eleven_v3") -> str:
    """The words sent to the TTS: the stressed word in capitals, "…" for a pause before, the audio tag first (v3 only)."""
    if not delivery:
        return text
    out = text
    short = len(text.split()) <= SHORT_LINE_WORDS     # "Ừ." — v3 is unsteady on very short text: no tag, no capitals, only pace / pause
    word = None if short else delivery.get("stress")
    if word:
        out = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", lambda m: m.group(0).upper(), out, count=1, flags=re.IGNORECASE)
    if delivery.get("pause_before"):
        out = "… " + out
    if delivery.get("tag") and model == "eleven_v3" and not short:
        out = f"[{delivery['tag']}] " + out
    return out


def deliveries(scene_data: Dict) -> List[Optional[Dict]]:
    """The delivery of each line of a shot row, aligned with dialogue.scene_lines (same filter)."""
    structured = scene_data.get("dialogue")
    if not isinstance(structured, list):
        return []
    return [d.get("delivery") if isinstance(d.get("delivery"), dict) else None for d in structured
            if isinstance(d, dict) and str(d.get("text") or "").strip()]
