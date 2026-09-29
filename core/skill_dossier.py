"""Skill dossiers (người dùng 2026-09-30): a character's active skill kept as a folder — frames taken from the official skill video
(30 frames/s, each phase at the moment it is clearest), a storyboard picture of the phases, and skill.json with what each phase looks
like in words for the picture and the video model, what must never be drawn, and the rules for the script. #8 wrote Kenta's skill
from a few lines of text: he drew his katana and the tornado broke the wall — both wrong.

data/skills/<NAME>/skill.json + frames/*.jpg + storyboard_ky_nang.jpg (frames_png/ = the 1080p originals, kept out of git).
Feature `skill_dossier` (off until one short Kenta scene is tried for real)."""
import json
import os
import re
from typing import Dict, List, Optional

from . import features

FEATURE = "skill_dossier"
ROLE = "skill_phase"
SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "skills")


def enabled() -> bool:
    return features.on(FEATURE)


def _fold(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", str(text or "")).replace("đ", "d").replace("Đ", "D")
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()


def _key(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", _fold(name).upper())


def names(skills_dir: Optional[str] = None) -> List[str]:
    root = skills_dir or SKILLS_DIR
    if not os.path.isdir(root):
        return []
    return sorted(d for d in os.listdir(root) if os.path.exists(os.path.join(root, d, "skill.json")))


def load(name: str, skills_dir: Optional[str] = None) -> Optional[Dict]:
    """The dossier of a character (matched without accents / spaces / case), with `_dir` set; None when there is none."""
    root = skills_dir or SKILLS_DIR
    want = _key(name)
    for d in names(root):
        if want and _key(d) == want:
            with open(os.path.join(root, d, "skill.json"), encoding="utf-8") as f:
                out = json.load(f)
            out["_dir"] = os.path.join(root, d)
            return out
    return None


def for_names(people, skills_dir: Optional[str] = None) -> List[Dict]:
    seen, out = set(), []
    for n in people or []:
        d = load(str(n), skills_dir)
        if d is not None and d["character"] not in seen:
            seen.add(d["character"])
            out.append(d)
    return out


def _has(blob: str, word: str) -> bool:
    w = _fold(word)
    return bool(w) and re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", blob) is not None


def _shot_text(data: Dict) -> str:
    keys = ("text", "image_prompt", "action_peak", "action", "description", "shot", "end_state", "motion_prompt", "skill")
    return " " + _fold(" ".join(str(data.get(k) or "") for k in keys)) + " "


def phase(dossier: Dict, pid: str) -> Optional[Dict]:
    return next((p for p in dossier.get("phases") or [] if p["id"] == pid), None)


def shot_skill(data: Dict, skills_dir: Optional[str] = None) -> Optional[Dict]:
    """{dossier, phase} when this shot shows a character's skill: the Director's `skill_phase` ("KENTA:wind_fly" or a phase id when
    one dossier fits), else a skill keyword in the shot's words for a character in the shot — the phase then comes from the words
    (phase_hints; the most hits wins, ties go to the dossier's order) or the dossier's `default_phase`."""
    people = [str(c) for c in data.get("characters") or []]
    dossiers = for_names(people, skills_dir)
    if not dossiers:
        return None
    wanted = str(data.get("skill_phase") or "").strip()
    if wanted:
        who, _, pid = wanted.rpartition(":")
        for d in dossiers:
            if (not who or _key(who) == _key(d["character"])) and phase(d, pid):
                return {"dossier": d, "phase": phase(d, pid), "how": "skill_phase"}
    blob = _shot_text(data)
    for d in dossiers:
        if not any(_has(blob, k) for k in d.get("keywords") or []):
            continue
        order = [p["id"] for p in d["phases"]]
        hits = {pid: sum(1 for w in words if _has(blob, w)) for pid, words in (d.get("phase_hints") or {}).items()}
        best = max(hits.items(), key=lambda kv: (kv[1], -order.index(kv[0]) if kv[0] in order else -99), default=(None, 0))
        pid = best[0] if best[1] > 0 else d.get("default_phase") or order[0]
        return {"dossier": d, "phase": phase(d, pid), "how": "words"}
    return None


def image_sentence(hit: Optional[Dict]) -> str:
    if not hit:
        return ""
    d, p = hit["dossier"], hit["phase"]
    return (f" {d['character']}'s skill {d.get('skill_en') or ''}, exactly as in the game — {p['image_en']}"
            f" Never draw: {d.get('never_en', '')}.")


def video_sentence(hit: Optional[Dict]) -> str:
    if not hit:
        return ""
    return f" Skill effect exactly as in the game: {hit['phase']['video_en']}"


def video_negative(hit: Optional[Dict], negative: Optional[str]) -> Optional[str]:
    if not hit or not hit["dossier"].get("never_en"):
        return negative
    extra = hit["dossier"]["never_en"]
    return f"{negative.rstrip(', ')}, {extra}" if (negative or "").strip() else extra


def reference(hit: Optional[Dict]) -> Optional[Dict]:
    """The phase's frame from the official video as a reference picture (role skill_phase); None when the file is missing."""
    if not hit:
        return None
    path = os.path.join(hit["dossier"]["_dir"], hit["phase"]["frame"])
    if not os.path.exists(path):
        return None
    return {"path": path, "label": hit["dossier"]["character"], "role": ROLE, "phase": hit["phase"]["id"]}


_PEOPLE = ("character", "outfit", "sheet")


def add_reference(refs: List[Dict], ref: Optional[Dict], limit: int) -> List[Dict]:
    """The phase frame goes in instead of the character's 'related' picture (a skill icon says less than the real frame); when the
    list is full, the last picture that is not a person gives up its slot."""
    if ref is None:
        return refs
    out = [r for r in refs if not (r.get("role") == "related" and r.get("label") == ref["label"]) and r.get("role") != ROLE]
    while len(out) >= limit:
        drop = next((i for i in range(len(out) - 1, -1, -1) if out[i].get("role") not in _PEOPLE), None)
        if drop is None:
            return out
        out.pop(drop)
    people = [i for i, r in enumerate(out) if r.get("role") in _PEOPLE]
    at = people[-1] + 1 if people else 0          # right after the people, before the place
    return out[:at] + [ref] + out[at:]


def reference_note(tag: str, label: str) -> str:
    return (f"{tag} is a frame of the official game video of {label}'s skill at this very moment: copy the skill EFFECT only — its "
            f"shape, colour, transparency, size against the body, where it sits and what {label} holds — never its camera, place, "
            "people, health bars, buttons, red damage-direction marks (a red crescent shows where the hit came from — it is the game's "
            "interface, not the skill) or any on-screen text")


def contradictions(text: str, dossier: Dict) -> List[str]:
    blob = " " + _fold(text) + " "
    return [w for w in dossier.get("script_contradictions") or [] if _has(blob, w)]


def shot_problems(data: Dict, skills_dir: Optional[str] = None) -> List[str]:
    """Words of a skill shot that contradict the dossier (Vietnamese, for the diagnosis)."""
    hit = shot_skill(data, skills_dir)
    if not hit:
        return []
    bad = contradictions(_shot_text(data), hit["dossier"])
    if not bad:
        return []
    d = hit["dossier"]
    return [f"shot kỹ năng {d['character']} ({d['skill_vi']}) có chữ trái hồ sơ: " + ", ".join(bad)
            + f" — hồ sơ data/skills/{os.path.basename(d['_dir'])}: " + "; ".join(d.get("never_vi") or [])]


def director_block(people, skills_dir: Optional[str] = None) -> str:
    """The dossiers of the characters in the project, for the Director / DP / motion writer: phases in order with seconds, what is
    never drawn, the script rules, and the `skill_phase` field of a skill shot."""
    out = []
    for d in for_names(people, skills_dir):
        rows = "\n".join(f"- `{p['id']}` ({p['t'][0]:.1f}–{p['t'][1]:.1f} s): {p['vi']}" for p in d["phases"])
        seqs = "; ".join(f"{k}: {' → '.join(v)}" for k, v in (d.get("sequences") or {}).items())
        out.append(
            f"## HỒ SƠ KỸ NĂNG {d['character']} — {d['skill_vi']} ({d.get('version', '')}) — nguồn: video chính thức, xem từng khung\n"
            f"Hồ sơ này thắng mọi mô tả khác về kỹ năng {d['character']}. Cơ chế: {d.get('mechanism_vi', '')}\n"
            f"Các giai đoạn (đúng thứ tự, mốc giây trong video gốc):\n{rows}\n"
            f"Chuỗi hợp lệ: {seqs}\n"
            "KHÔNG ĐƯỢC viết / vẽ: " + "; ".join(d.get("never_vi") or []) + "\n"
            "Luật kịch bản:\n" + "\n".join(f"- {r}" for r in d.get("script_rules_vi") or []) + "\n"
            f"Shot có kỹ năng: ghi `skill_phase` = \"{d['character']}:<mã giai đoạn>\" (một giai đoạn chính mỗi shot) — code gửi kèm khung "
            f"hình thật của giai đoạn đó làm ảnh tham chiếu và câu tả chuẩn cho model ảnh + video.\n"
            f"Video: {d.get('video_method_vi', '')}")
    return "\n\n".join(out)
