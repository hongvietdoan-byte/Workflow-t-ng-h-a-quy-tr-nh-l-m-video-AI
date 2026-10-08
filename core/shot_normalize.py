"""Bộ chuẩn hóa shot (kế hoạch 2026-09-25, H1): code fixes what can be measured in a Director answer, instead of sending the whole
answer back to Claude (~$0,3 each time) or leaving it to the video bill.

Runs on the Director JSON before it is validated and stored (llm_io.validate_for_project), and records every change in
`obj["normalized"]` so the person sees what code did. Only fixed, known corrections — an unknown value is left alone (the validator
then sends it back to Claude, as before):

1. enum spellings: "over_shoulder" -> "ots", "close_up" -> "CU", a GAME_TPS shot's "behind"/"tps" angle -> "high"…
   (run 4 of "ANH CHỌN AI?" was sent back once for one such angle);
2. a spoken shot shorter than its line needs (dialogue.needed_seconds) is lengthened (run 3: 11 shots, 6,8 s short);
3. a silent shot under 1 s (not an insert) is merged into the neighbouring shot of the same scene that shares its people; a silent
   wide shot or one with on-screen text is lengthened instead (run 4: seven 0,5–0,6 s shots, each billed as a 3 s clip);
4. a wide shot under 1,5 s is lengthened (cannot be read);
5. the total is brought back under the script's length by shortening silent shots only (never a spoken one); what cannot be
   absorbed is reported, not hidden.
Never adds, removes or rewords a line of dialogue.
"""
import copy
import re
from typing import Dict, List, Optional, Tuple

from . import dialogue

# 08/10 (#24, người dùng chốt): a shot with nobody in it whose only content is waiting for a popup / icon / words added after
# ("nền tối mờ sương, chờ icon hiện ở hậu kỳ") costs a paid picture + clip and adds nothing — the popup goes over the LAST shot
_POST_ONLY = re.compile(r"chờ (?:icon|popup|pop-up|chữ|logo|biểu tượng)|ở hậu kỳ|hậu kỳ (?:đặt|ghép|chèn)|để hậu kỳ|post[- ]?production|"
                        r"overlay|placeholder|(?:icon|popup|logo|text|title)s? (?:will )?(?:to )?(?:appear|be added|pop)", re.I)
MAX_SHOT_S = 15.0

SILENT_MIN = 1.0
WIDE_MIN = 1.5
INSERT_MIN = 0.5
_WIDE = ("WS", "EWS")

SIZE_SYN = {"CLOSE_UP": "CU", "CLOSEUP": "CU", "CLOSE-UP": "CU", "EXTREME_CLOSE_UP": "ECU", "MEDIUM_CLOSE_UP": "MCU",
            "MEDIUM": "MS", "MEDIUM_SHOT": "MS", "MID": "MS", "WIDE": "WS", "WIDE_SHOT": "WS", "LS": "WS", "LONG_SHOT": "WS",
            "FULL_SHOT": "WS", "EXTREME_WIDE": "EWS", "ELS": "EWS", "EXTREME_LONG_SHOT": "EWS", "TPS": "GAME_TPS",
            "GAMEPLAY": "GAME_TPS", "GAME": "GAME_TPS", "MEDIUM_LONG_SHOT": "MLS", "MEDIUM_WIDE": "MLS", "COWBOY": "MLS",
            "AMERICAN_SHOT": "MLS"}
ANGLE_SYN = {"eye_level": "eye", "eye-level": "eye", "eyelevel": "eye", "low_angle": "low", "high_angle": "high",
             "over_shoulder": "ots", "over-the-shoulder": "ots", "over_the_shoulder": "ots", "overshoulder": "ots",
             "birds_eye": "overhead", "bird_eye": "overhead", "top_down": "overhead", "top": "overhead", "dutch_angle": "dutch",
             "canted": "dutch", "point_of_view": "pov"}
ANGLE_TPS = {"behind", "back", "tps", "third_person", "third-person", "rear", "over_back"}      # only for GAME_TPS -> "high"
MOVE_SYN = {"dolly_in": "push_in", "push": "push_in", "dolly_out": "pull_out", "pull": "pull_out", "tracking": "track",
            "follow": "track", "none": "static", "locked": "static", "static_shot": "static", "shaky": "handheld",
            "hand_held": "handheld", "whip_pan": "whip", "zoom_in": "zoom", "zoom_out": "zoom"}
ROLE_SYN = {"establishing": "setup", "establish": "setup", "reaction_shot": "reaction", "cutaway": "insert", "detail": "insert",
            "close": "ending", "outro": "ending", "intro": "hook"}


def _spoken(shot: Dict) -> List[Tuple[str, str]]:
    return [(str(d.get("speaker") or "").strip(), str(d.get("text") or "").strip()) for d in shot.get("dialogue") or []
            if isinstance(d, dict) and not dialogue.is_non_speaker(str(d.get("speaker") or ""))
            and str(d.get("text") or "").strip()]


def _dur(shot: Dict) -> float:
    v = shot.get("duration_s")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def _label(sc: Dict, k: int) -> str:
    return f"cảnh {sc.get('idx')} shot {k}"


def _fix_enums(sc: Dict, changes: List[str]) -> None:
    for k, s in enumerate(sc.get("shots") or [], 1):
        if not isinstance(s, dict):
            continue
        for key, table in (("size", SIZE_SYN), ("camera_move", MOVE_SYN), ("role", ROLE_SYN)):
            v = s.get(key)
            if isinstance(v, str):
                norm = v.strip().upper().replace(" ", "_") if key == "size" else v.strip().lower().replace(" ", "_")
                new = table.get(norm, norm if key == "size" else None)
                if key == "size" and new != v and new in {"ECU", "CU", "MCU", "MS", "MLS", "WS", "EWS", "GAME_TPS"}:
                    s[key], _ = new, changes.append(f"{_label(sc, k)}: {key} “{v}” → “{new}”")
                elif key != "size" and new and new != v:
                    s[key], _ = new, changes.append(f"{_label(sc, k)}: {key} “{v}” → “{new}”")
        v = s.get("angle")
        if isinstance(v, str):
            norm = v.strip().lower().replace(" ", "_")
            new = "high" if (s.get("size") == "GAME_TPS" and norm in ANGLE_TPS) else ANGLE_SYN.get(norm)
            if new and new != v:
                s["angle"] = new
                changes.append(f"{_label(sc, k)}: góc “{v}” → “{new}”" + (" (camera game sau lưng)" if s.get("size") == "GAME_TPS" else ""))


def _fit_speech(sc: Dict, changes: List[str]) -> None:
    for k, s in enumerate(sc.get("shots") or [], 1):
        need = dialogue.needed_seconds(_spoken(s))
        if need and _dur(s) + 1e-6 < need:
            changes.append(f"{_label(sc, k)}: {_dur(s):g}s → {need:g}s (đủ thời gian nói câu thoại)")
            s["duration_s"] = need


def _shares(a: Dict, b: Dict) -> bool:
    ca = {str(x).upper() for x in a.get("characters") or []}
    cb = {str(x).upper() for x in b.get("characters") or []}
    return bool(ca & cb) or (not ca and not cb)


def _merge_micro(sc: Dict, changes: List[str]) -> None:
    shots = sc.get("shots") or []
    k = 0
    while k < len(shots):
        s = shots[k]
        dur = _dur(s)
        silent = not _spoken(s)
        if not silent or dur >= SILENT_MIN or s.get("role") == "insert":
            k += 1
            continue
        if s.get("size") in _WIDE or s.get("on_screen_text"):
            floor = WIDE_MIN if s.get("size") in _WIDE else SILENT_MIN
            changes.append(f"{_label(sc, k + 1)}: {dur:g}s → {floor:g}s (" + ("toàn cảnh cần đủ để đọc" if s.get("size") in _WIDE
                                                                           else "có chữ trên màn hình") + ")")
            s["duration_s"] = floor
            k += 1
            continue
        prev = shots[k - 1] if k > 0 else None
        nxt = shots[k + 1] if k + 1 < len(shots) else None
        target, where = None, ""
        if nxt is not None and _shares(s, nxt):
            target, where = nxt, "đầu"
        elif prev is not None and _shares(s, prev):
            target, where = prev, "cuối"
        if target is None:                                   # nobody in common: keep it, but long enough to be worth a clip
            changes.append(f"{_label(sc, k + 1)}: {dur:g}s → {SILENT_MIN:g}s (shot im lặng quá ngắn, không có shot kề cùng người để gộp)")
            s["duration_s"] = SILENT_MIN
            k += 1
            continue
        act = str(s.get("action") or "").strip()
        target["action"] = (f"{act} → {target.get('action', '')}" if where == "đầu" else f"{target.get('action', '')} → {act}").strip(" →")
        target["duration_s"] = round(_dur(target) + dur, 2)
        if s.get("hero"):
            target["hero"] = True
        n_target = k + 2 if where == "đầu" else k
        changes.append(f"{_label(sc, k + 1)} ({dur:g}s, im lặng: “{act[:50]}”) gộp vào {where} shot {n_target} → shot đó dài "
                       f"{_dur(target):g}s")
        del shots[k]


def _fit_total(obj: Dict, target: Optional[Tuple[int, int]], planned: Dict[int, float], changes: List[str]) -> None:
    if not target:
        return
    scenes = [sc for sc in obj.get("scenes") or [] if isinstance(sc.get("shots"), list)]
    total = sum(_dur(s) for sc in scenes for s in sc["shots"])
    over = round(total - target[1], 2)
    if over <= 0.05:
        return

    def floor(s):
        return WIDE_MIN if s.get("size") in _WIDE else (INSERT_MIN if s.get("role") == "insert" else SILENT_MIN)

    def excess(sc):            # how far a script section runs past its own "– 8–20 GIÂY" time (0 when unknown)
        plan = planned.get(sc.get("idx"))
        return (sum(_dur(s) for s in sc["shots"]) - plan) if plan else 0.0
    cut = 0.0
    while over - cut > 0.05:
        # sections longest past their script time give first; inside a section, 0,1 s from each silent shot in turn (even trim)
        # a section is never cut below its own script time (story & emotion outrank the total — priority order, kế hoạch H3)
        room = [(sc, s) for sc in scenes for s in sc["shots"] if not _spoken(s) and _dur(s) - 0.1 >= floor(s) - 1e-6
                and (not planned.get(sc.get("idx")) or excess(sc) > 0.05)]
        if not room:
            break
        worst = max(excess(sc) for sc, _ in room)
        pick = [(sc, s) for sc, s in room if excess(sc) >= worst - 0.05] if worst > 0.05 else room
        for _, s in sorted(pick, key=lambda x: _dur(x[1]), reverse=True):
            if over - cut <= 0.05:
                break
            s["duration_s"] = round(_dur(s) - 0.1, 2)
            cut = round(cut + 0.1, 2)
    if cut:
        changes.append(f"tổng {total:g}s vượt khung {target[0]}–{target[1]}s: rút {cut:g}s từ các shot im lặng (không đụng shot có thoại)")
    note = (f"⚠ vẫn vượt khung {over - cut:.1f}s — thoại cần nhiều thời gian hơn kịch bản cho phép: bỏ câu (khi được phép) "
            "hoặc nới thời lượng")
    if over - cut > 0.05 and note not in (obj.get("normalized") or []):     # said once, not again on every re-check
        changes.append(note)


def post_only(shot: Dict) -> bool:
    """Nobody in the frame, no line, and the shot only waits for something added after (popup / icon / words / overlay)."""
    if not isinstance(shot, dict) or shot.get("characters") or _spoken(shot):
        return False
    words = " ".join(str(shot.get(k) or "") for k in ("action", "start_frame", "why", "image_prompt", "text"))
    return bool(_POST_ONLY.search(words))


def fold_post_only(obj: Dict, scenes: List[Dict], changes: List[str]) -> None:
    """Post-only shots → removed; their words become the end-card note of the film's LAST shot (`end_card_note`), their seconds go to
    that shot (≤ 15 s), and `obj["end_card"]` lists what was folded (Bước 5 builds the popup from the project's icons)."""
    last = None
    for sc in scenes:
        for s in sc["shots"]:
            if not post_only(s):
                last = s
    if last is None:
        return
    notes, seconds, labels = [], 0.0, []
    for sc in scenes:
        keep = [s for s in sc["shots"] if not post_only(s)]
        if not keep:
            continue                                    # a scene made only of such shots stays (nothing to put the popup on)
        for k, s in enumerate(sc["shots"], 1):
            if post_only(s):
                notes.append(str(s.get("action") or s.get("why") or "").strip())
                seconds += _dur(s)
                labels.append(_label(sc, k))
        sc["shots"] = keep
    if not labels:
        return
    note = " · ".join(n for n in notes if n)
    last["end_card_note"] = ((str(last.get("end_card_note") or "") + " · ") if last.get("end_card_note") else "") + note
    if seconds:
        last["duration_s"] = round(min(_dur(last) + seconds, MAX_SHOT_S), 2)
    obj["end_card"] = {"notes": notes, "folded_shots": labels, "seconds": round(seconds, 2)}
    changes.append(f"{', '.join(labels)}: shot chỉ chờ popup/hậu kỳ (không nhân vật) → bỏ, popup ghép lên shot cuối (+{seconds:g}s)")


def section_seconds(script_text: str) -> Dict[int, float]:
    """{script scene number: seconds} from timed headings such as "CẢNH 1 – 8–20 GIÂY" (numbered as the Director sees them)."""
    from . import script_parser
    from .director_report import _SECTION_TIME
    _, story = script_parser.split_end_card(script_parser.split_scenes([r for r in script_text.splitlines() if r.strip()]))
    out = {}
    for i, sc in enumerate(story, 1):
        m = _SECTION_TIME.search(sc.heading or "")
        if m:
            out[i] = float(int(m.group(2)) - int(m.group(1)))
    return out


def normalize(obj: Dict, script_text: str = "", target: Optional[Tuple[int, int]] = None, in_place: bool = False) -> Tuple[Dict, List[str]]:
    """(fixed answer, changes). `target` = (low, high) seconds; read from the script when not given."""
    if target is None and script_text:
        from .prompts import target_seconds
        target = target_seconds(script_text)
    planned = section_seconds(script_text) if script_text else {}
    out = obj if in_place else copy.deepcopy(obj)
    changes: List[str] = []
    scenes = [sc for sc in out.get("scenes") or [] if isinstance(sc, dict) and isinstance(sc.get("shots"), list)]
    fold_post_only(out, scenes, changes)
    for sc in scenes:
        _fix_enums(sc, changes)
        _fit_speech(sc, changes)
        _merge_micro(sc, changes)
        for k, s in enumerate(sc["shots"], 1):
            if s.get("size") in _WIDE and not _spoken(s) and _dur(s) < WIDE_MIN:
                changes.append(f"{_label(sc, k)}: toàn cảnh {_dur(s):g}s → {WIDE_MIN:g}s (cần đủ để đọc)")
                s["duration_s"] = WIDE_MIN
    _fit_total(out, target, planned, changes)
    for sc in scenes:
        for s in sc["shots"]:
            if isinstance(s.get("duration_s"), float):
                s["duration_s"] = round(s["duration_s"], 2)
    if changes:
        out["normalized"] = list(out.get("normalized") or []) + changes
    return out, changes
