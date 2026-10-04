"""S0.14 T2 (2026-09-29): a Kling clip with dialogue must NAME who is speaking.

Why: the official Kling 3.0 guide ties every dialogue line to a character name in the prompt; the one hands-on test found Kling's weak
spot is splitting the lines between characters (research/craft/trung_quoc/LUOT_2.md, sources [19][22]). Kling cannot speak Vietnamese,
so our lines are TTS laid on afterwards — the line itself does not go into the prompt, but the model still has to open the RIGHT mouth.
Prompts written by code already say "X speaks (mouth moving, no sound)." (seedance_refs.shot_motion); prompts written by Claude (prompt
03) or joined for a camera set-up may not.

- `problems(prompt, rows)`: the speakers the prompt never names next to a speaking word ([] = fine). Checked only when it matters:
  two or more different speakers in the clip, or a speaker sharing the frame with someone else (whose mouth moves is ambiguous).
- `fix_sentence(rows, missing)`: the sentence to add ("KENTA speaks (mouth moving, no sound). KELLY listens, mouth closed.").
  Adding it changes what a paid model receives → only with the feature `speaker_tags` (off until a real run shows it helps);
  the check itself is free and always reported (CHUAN luật 1: không im lặng).
"""
import re
from typing import Dict, List, Sequence

from . import dialogue

FEATURE = "speaker_tags"

# a speaking word in the same sentence as the name: "Kenta answers", "Maxim asks Kenta", "KELLY speaks (mouth moving…)"
_SPEAK = re.compile(r"\b(speak|say|said|talk|tell|told|ask|answer|repl|respond|shout|call|whisper|yell|scream|cr(?:y|ies)\s+out|murmur|"
                    r"mutter|explain|blurt|admit|warn|reproach|plead|beg|demand|protest|insist|confess|announce|exclaim|"
                    r"mouth(?:s|ing)?\s+(?:the\s+)?words?|mouth moving|lips (?:in sync|moving))\w*", re.I)
_SENTENCE = re.compile(r"[.!?]+(?=\s|$)|\n+")      # "3.5 s" is not an end; not ";": "…beside Maxim; he turns and speaks" is still one thought about Maxim


def is_kling(model) -> bool:
    return "kling" in str(model or "").lower()


def speakers(data: Dict) -> List[str]:
    """Who speaks in this shot (upper case, film order, once each); on-screen text / notes are not voices."""
    out = []
    for d in data.get("dialogue") or []:
        if not isinstance(d, dict):
            continue
        who = str(d.get("speaker") or "").strip().upper()
        if who and not dialogue.is_non_speaker(who) and str(d.get("text") or "").strip() and who not in out:
            out.append(who)
    return out


def on_screen(data: Dict) -> List[str]:
    return [str(c).strip().upper() for c in data.get("characters") or [] if str(c).strip()]


def applies(rows: Sequence[Dict]) -> bool:
    """≥ 2 different speakers in the clip, or a speaker with somebody else in the frame."""
    talk = {w for d in rows for w in speakers(d)}
    if len(talk) >= 2:
        return True
    return any(speakers(d) and len(set(on_screen(d))) >= 2 for d in rows)


def named(prompt: str, who: str) -> bool:
    """`who` appears in one sentence together with a speaking word."""
    name = re.compile(rf"(?<![\w]){re.escape(who)}(?![\w])", re.I)
    return any(name.search(s) and _SPEAK.search(s) for s in _SENTENCE.split(prompt or ""))


def problems(prompt: str, rows: Sequence[Dict]) -> List[str]:
    """Speakers of the clip (rows = the shots' data dicts it carries) the prompt does not name as speaking."""
    if not applies(rows):
        return []
    out = []
    for d in rows:
        for who in speakers(d):
            if who not in out and not named(prompt, who):
                out.append(who)
    return out


def fix_sentence(rows: Sequence[Dict], missing: Sequence[str]) -> str:
    """What to add: the missing speakers named as speaking (no sound — the Vietnamese voice comes later), and the other people in the
    frame of those shots as listening with their mouths closed."""
    if not missing:
        return ""
    talk = {w for d in rows for w in speakers(d)}
    quiet = []
    for d in rows:
        if any(w in missing for w in speakers(d)):
            quiet += [c for c in on_screen(d) if c not in talk and c not in quiet]
    return " ".join([f"{w} speaks (mouth moving, no sound)." for w in missing] + [f"{c} listens, mouth closed." for c in quiet])


def apply(prompt: str, rows: Sequence[Dict], limit: int = 0) -> Dict:
    """{"missing": [...], "prompt": the prompt to send, "added": the sentence added ("" when the flag is off / nothing missing /
    it would not fit under `limit` characters), "why_not": the reason nothing was added although something is missing}."""
    from . import features
    missing = problems(prompt, rows)
    out = {"missing": missing, "prompt": prompt, "added": "", "why_not": ""}
    if not missing:
        return out
    if not features.on(FEATURE):
        out["why_not"] = f"cờ {FEATURE} đang TẮT"
        return out
    add = fix_sentence(rows, missing)
    new = f"{prompt.rstrip()} {add}".strip()
    if limit and len(new) > limit:
        out["why_not"] = f"thêm câu thì vượt {limit} ký tự"
        return out
    out.update(prompt=new, added=add)
    return out


def message(label: str, res: Dict) -> str:
    """The diag line (Vietnamese) for one clip / shot."""
    who = ", ".join(res["missing"])
    if res["added"]:
        return f"{label}: prompt Kling chưa nêu tên người nói ({who}) — đã thêm: \"{res['added']}\""
    return (f"{label}: prompt Kling chưa nêu tên người nói ({who}) — model dễ mở nhầm miệng (Kling chia thoại giữa nhân vật chưa chuẩn, "
            f"S0.14 T2); chưa thêm vì {res['why_not']}")
