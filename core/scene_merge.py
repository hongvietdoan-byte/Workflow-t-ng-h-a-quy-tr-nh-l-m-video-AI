"""S14.35 ý 3 · gộp CẢNH liền nhau cùng nơi bằng code, sau lượt viết của Biên kịch (0 USD, không gọi model, prompt 23 không đổi).

Why: the Biên kịch often writes one scene per beat; a 15 s clip then has 5 scenes in the same place, each a cold cut, and the figures stand
still at every cut (người dùng 05/10). Here the code joins adjacent scenes of ONE place into one longer scene: the order of actions and every
line of dialogue are kept as they were.

Merged when ALL hold: same place (the heading's place), same time of day, the cast is the same or differs by one person (and shares someone),
neither scene is a flashback, neither says a costume change or an intended transition. Otherwise the scenes stay apart.

Continuity: at every join the last action of the scene before and the first action of the scene after are recorded (`joins`); at every cut
that stays, `cuts` says whether the next scene goes on from the same place (`continuous`) and, when it does, a parenthesised line at the end of
the scene tells the Director / DP to cut on movement from the end pose, not at a hard stop. The pipeline already carries this per shot
(`continuous_with_next`, `sequence`, the end frame of the shot before — prompts/17, core/end_frames.py); this only gives it the script-level hint.
"""
import re
from typing import Dict, List, Tuple

from . import assets, idea_buildable

_DAY_PARTS = ("ban ngay", "ban dem", "binh minh", "hoang hon", "ngay", "dem", "sang", "chieu", "toi", "trua")
_TRANSITION = re.compile(r"chuyen canh|cat sang|cat canh|mo dan|tat dan|\bfade\b|dissolve|transition|flashback|hoi tuong|time ?skip|"
                         r"(mot|vai|nhieu|\d+) ?(phut|gio|ngay|tuan|luc|lat) sau|hom sau|luc sau|trong luc do|cung luc do")
_COSTUME = re.compile(r"(thay|doi) (do|ao|trang phuc|bo|quan ao)|mac (bo|ao|trang phuc) (moi|khac)|\bao (moi|khac)\b|(bo|trang phuc) (moi|khac)")
_HEAD_NO = re.compile(r"^(\s*c[ảa]nh\s*)\d+", re.I)
_RANGE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(s|giây|giay)\b", re.I)
NOTE_MARK = "(Liền mạch với cảnh sau"


def _blocks(text: str) -> Tuple[List[str], List[Dict]]:
    """(preamble lines before the first heading, [{heading, lines}])."""
    from .script_parser import is_heading
    pre, blocks = [], []
    for ln in (text or "").splitlines():
        if is_heading(ln):
            blocks.append({"heading": ln.rstrip(), "lines": []})
        elif blocks:
            blocks[-1]["lines"].append(ln.rstrip())
        else:
            pre.append(ln.rstrip())
    for b in blocks:
        while b["lines"] and not b["lines"][-1].strip():
            b["lines"].pop()
        b["lines"] = [x for x in b["lines"] if x.strip()]
    return pre, blocks


def _speakers(lines: List[str]) -> set:
    out = set()
    for ln in lines:
        who, sep, _ = ln.partition(":")
        if sep and idea_buildable._said(ln):
            from .dialogue import is_non_speaker
            if not is_non_speaker(who.strip()):
                out.add(who.strip().upper())
    return out


def _cast(lines: List[str], everyone: set) -> set:
    """Speakers of the scene + the known names (speakers anywhere in the script) the description mentions."""
    text = "\n".join(lines)
    return _speakers(lines) | {n for n in everyone if idea_buildable.has_phrase(text, n)}


def _day_part(heading: str) -> str:
    f = assets.fold(heading.split(",", 1)[0])
    return next((w for w in _DAY_PARTS if re.search(r"(?<!\w)" + w + r"(?!\w)", f)), "")


def _action_lines(lines: List[str]) -> List[str]:
    """Description lines (no dialogue, no earlier continuity note)."""
    return [ln for ln in lines if ln.strip() and not idea_buildable._said(ln) and not ln.lstrip().startswith(NOTE_MARK)]


def _why_not(a: Dict, b: Dict, everyone: set) -> str:
    """'' = the two may be joined, else why not (also tells whether the cut can still be continuous: see `_continuous`)."""
    if not a["where"] or a["where"] != b["where"]:
        return "khác nơi"
    if _day_part(a["heading"]) != _day_part(b["heading"]):
        return "khác thời điểm trong ngày"
    fa, fb = assets.fold(a["heading"] + "\n" + "\n".join(a["lines"])), assets.fold(b["heading"] + "\n" + "\n".join(b["lines"]))
    if _TRANSITION.search(fa) or _TRANSITION.search(fb):
        return "có chuyển cảnh / nhảy thời gian chủ ý"
    if _COSTUME.search(fa) or _COSTUME.search(fb):
        return "có đổi trang phục"
    ca, cb = a["cast"], b["cast"]
    if ca and cb and (not (ca & cb) or len(ca ^ cb) > 1):
        return "khác bộ nhân vật"
    return ""


def _continuous(a: Dict, b: Dict) -> Tuple[bool, str]:
    """A cut that stays: does the next scene go on from where this one ends? (same place, same time of day, no intended transition)."""
    if not a["where"] or a["where"] != b["where"]:
        return False, "khác nơi"
    if _day_part(a["heading"]) != _day_part(b["heading"]):
        return False, "khác thời điểm trong ngày"
    fa, fb = assets.fold("\n".join(a["lines"])), assets.fold(b["heading"] + "\n" + "\n".join(b["lines"]))
    if _TRANSITION.search(fa) or _TRANSITION.search(fb):
        return False, "chuyển cảnh / nhảy thời gian chủ ý"
    return True, ""


def _heading_range(first: str, last: str) -> str:
    m1, m2 = _RANGE.search(first), _RANGE.search(last)
    if m1 and m2:
        return first[:m1.start()] + f"{m1.group(1)}-{m2.group(2)}{m1.group(3)}" + first[m1.end():]
    return first


def merge_script(text: str) -> Tuple[str, Dict]:
    """(new script text, report). report = {merged: [[old scene numbers joined]…], joins: [{scene, after_old, end_state, start_state}],
    cuts: [{from, to, continuous, reason, end_state, start_state}], kept: n}. Text without scene headings comes back unchanged."""
    pre, blocks = _blocks(text)
    rep: Dict = {"merged": [], "joins": [], "cuts": [], "kept": len(blocks)}
    if len(blocks) < 2:
        return text, rep
    everyone = set()
    for b in blocks:
        everyone |= _speakers(b["lines"])
    for i, b in enumerate(blocks, start=1):
        b["old"] = [i]
        b["where"] = assets.fold(idea_buildable._where(b["heading"]))
        b["cast"] = _cast(b["lines"], everyone)
    groups: List[Dict] = []
    for b in blocks:
        g = groups[-1] if groups else None
        if g is not None and not _why_not(g, b, everyone):
            last_action = (_action_lines(g["lines"]) or g["lines"] or [""])[-1]
            first_action = (_action_lines(b["lines"]) or b["lines"] or [""])[0]
            rep["joins"].append({"scene": len(groups), "after_old": g["old"][-1], "end_state": last_action.strip(), "start_state": first_action.strip()})
            g["lines"] = g["lines"] + b["lines"]
            g["cast"] = g["cast"] | b["cast"]
            g["old"] = g["old"] + b["old"]
            g["heading"] = _heading_range(g["heading"], b["heading"])
        else:
            groups.append({k: (list(v) if isinstance(v, list) else v) for k, v in b.items()})
    rep["merged"] = [g["old"] for g in groups if len(g["old"]) > 1]
    rep["kept"] = len(groups)
    out = list(pre)
    for n, g in enumerate(groups, start=1):
        nxt = groups[n] if n < len(groups) else None
        if nxt is not None:
            ok, why = _continuous(g, nxt)
            end = (_action_lines(g["lines"]) or g["lines"] or [""])[-1].strip()
            start = (_action_lines(nxt["lines"]) or nxt["lines"] or [""])[0].strip()
            rep["cuts"].append({"from": n, "to": n + 1, "continuous": ok, "reason": why, "end_state": end, "start_state": start})
            if ok and end:
                g["lines"] = g["lines"] + [f"{NOTE_MARK} — cảnh này kết ở \"{end}\"; cảnh sau tiếp ngay từ vị trí và tư thế đó, dựng liền theo chuyển động, "
                                           "không cắt cứng giữa nhịp.)"]
        head = _HEAD_NO.sub(lambda m: m.group(1) + str(n), g["heading"], count=1)
        out += ([""] if out else []) + [head] + g["lines"]
    new = "\n".join(out).strip()
    return (new if new != (text or "").strip() else text), rep
