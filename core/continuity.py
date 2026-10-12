"""Continuity checks of a shot plan (knowledge/roles/dp.md Q9, director.md Đ3 — việc code V5, V6), code only, no Claude call.

  axis_warnings(shots)   the 180° line: two people seen left/right in one shot and swapped in a later shot of the same script scene
                         (the viewer thinks they changed places); a person running left→right then right→left in one scene
  motif_warnings(shots)  a motif (shot field `motif`, a short tag) that appears once is not a motif — it must come back

Read from the words the DP writes in `start_frame` / `end_state` (frame-left / frame-right, left to right…). Soft warnings for the
Director report and Step 1: a crossing written on purpose (`why` says "vượt trục" / "cross the line" — "giữ trục 180°" is NOT a
crossing), a POV or overhead shot, and a shot that moves the camera across the line (`orbit`) are not flagged. Over-the-shoulder
shots ARE checked (the A/B pair of a dialogue is where the line is crossed most). A shot of two people that says nobody's side cannot
be checked — said once per scene (CHUAN_XAY_DUNG luật 1: never silent when an input is missing).
"""
import re
from typing import Dict, List, Optional, Tuple

_LEFT = re.compile(r"\b(frame[- ]left|left of (the )?frame|on the left|left side|bên trái|trái khung)\b", re.I)
_RIGHT = re.compile(r"\b(frame[- ]right|right of (the )?frame|on the right|right side|bên phải|phải khung)\b", re.I)
_TO_RIGHT = re.compile(r"\b(left to right|toward(s)? (the )?(frame[- ])?right|to (the )?frame[- ]right|từ trái sang phải)\b", re.I)
_TO_LEFT = re.compile(r"\b(right to left|toward(s)? (the )?(frame[- ])?left|to (the )?frame[- ]left|từ phải sang trái)\b", re.I)
# a crossing written on purpose; with a negation up to 3 words before it ("không để vượt trục", "tránh vượt trục", "don't cross the
# line", "never crosses the axis") it says the opposite — keeping the line; the window stops at a comma / full stop (TON_DONG A14 / R2:
# "không đẹp, máy vượt trục" is a crossing on purpose)
_CROSSING = re.compile(r"(?:vượt|qua|nhảy) trục|cross(?:es|ing)? the (?:line|axis)|jump(?:s|ing)? the line", re.I)
_NEGATION = re.compile(r"(?:^|\s)(?:không|chưa|tránh|đừng|chớ|cấm|giữ|not|n't|don't|avoid|never|no)(?:\s+[^\s,;.!?:—]+){0,3}\s*$", re.I)


class _OnPurpose:
    @staticmethod
    def search(text: str) -> bool:
        return any(not _NEGATION.search(text[:m.start()]) for m in _CROSSING.finditer(text or ""))


_ON_PURPOSE = _OnPurpose()
_EXEMPT_ANGLES = ("pov", "overhead")
_MOVE = re.compile(r"(?<!\w)(?:run|runs|running|ran|walk|walks|walking|walked|sprint\w*|dash\w*|charg\w+|driv\w+|fl(?:y|ies|ying|ew)|"
                   r"mov(?:e|es|ing|ed)|rush\w*|chạy|đi|lao|phóng)(?!\w)", re.I)


def _clauses(text: str) -> List[str]:
    return [c for c in re.split(r"[.;,]| and | while | với | và ", text or "") if c.strip()]


def _layout_on() -> bool:
    try:
        from . import features
        return features.on("continuity_layout")
    except Exception:  # noqa: BLE001 - unreadable settings: the old checks only
        return False


def _frame_text(shot: Dict) -> str:
    """The words that place people on screen: start_frame (else blocking) — with `continuity_layout` (hộp thư 12/10 15:51, #27 wrote
    the sides in image_prompt / blocking only, so nothing was checked and nothing said) also blocking + image_prompt."""
    if _layout_on():
        return " . ".join(str(shot.get(k) or "") for k in ("start_frame", "blocking", "image_prompt") if shot.get(k))
    return str(shot.get("start_frame") or shot.get("blocking") or "")


def _sides_in(text: str, names) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for clause in _clauses(text):
        named = [n for n in names if re.search(rf"\b{re.escape(n)}\b", clause, re.I)]
        left, right = bool(_LEFT.search(clause)), bool(_RIGHT.search(clause))
        if len(named) == 1 and left != right and named[0] not in out:
            out[named[0]] = -1 if left else 1
    return out


def sides(shot: Dict) -> Dict[str, int]:
    """name -> -1 (left) / +1 (right) from the shot's start frame words; a clause that names one person and one side decides.
    With `continuity_layout`: a person the start frame does not place is read from the image prompt (the opening picture) — never
    from blocking, which tells the MOVE ("they swap places: Kelly ends on the right") (rà 12/10)."""
    names = [str(n) for n in shot.get("characters") or [] if isinstance(n, str)]
    out = _sides_in(str(shot.get("start_frame") or shot.get("blocking") or ""), names)
    if _layout_on():
        for n, v in _sides_in(str(shot.get("image_prompt") or ""), [n for n in names if n not in out]).items():
            out.setdefault(n, v)
    return out


def direction(shot: Dict) -> Optional[int]:
    text = f"{shot.get('start_frame') or ''} {shot.get('end_state') or ''} {shot.get('action') or ''}"
    if _layout_on():                 # rà 12/10: only clauses that MOVE ("Kelly glances toward the left" / light is not a run)
        text += " " + " . ".join(c for c in _clauses(f"{shot.get('blocking') or ''} . {shot.get('image_prompt') or ''}") if _MOVE.search(c))
    r, l = bool(_TO_RIGHT.search(text)), bool(_TO_LEFT.search(text))
    return (1 if r else -1) if r != l else None


def _exempt(shot: Dict) -> bool:
    return (str(shot.get("angle") or "") in _EXEMPT_ANGLES or shot.get("camera_move") == "orbit"
            or bool(_ON_PURPOSE.search(str(shot.get("why") or ""))))


def axis_warnings(shots: List[Tuple[int, int, Dict]]) -> List[str]:
    """shots: (script scene, shot number, shot) in film order."""
    out: List[str] = []
    seen: Dict[Tuple, Tuple[str, int]] = {}         # (scene, A, B) -> (where, sign of A's side minus B's) first seen
    moving: Dict[Tuple, Tuple[str, int]] = {}       # (scene, person) -> (where, direction) first seen
    unknown: Dict[int, List[str]] = {}               # scene -> two-person shots with no left/right words
    for scene, k, s in shots:
        tag = f"{scene}·{k}"
        if _exempt(s):
            continue
        sd = sides(s)
        if len(set(s.get("characters") or [])) >= 2 and len(sd) < 2:
            unknown.setdefault(scene, []).append(tag)
        names = sorted(sd)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if sd[a] == sd[b]:
                    continue
                order = 1 if sd[a] < sd[b] else -1         # 1 = A on the left of B
                key = (scene, a, b)
                if key in seen and seen[key][1] != order:
                    out.append(f"shot {tag}: {a} và {b} đổi bên so với shot {seen[key][0]} — vượt trục 180°? (ghi `why` nếu cố ý)")
                seen.setdefault(key, (tag, order))
        way = direction(s)
        if way is not None:
            for n in s.get("characters") or []:
                key = (scene, n)
                if key in moving and moving[key][1] != way:
                    out.append(f"shot {tag}: {n} đổi hướng chạy trên màn hình so với shot {moving[key][0]} — người xem tưởng quay đầu")
                moving.setdefault(key, (tag, way))
    for scene, tags in unknown.items():
        out.append(f"cảnh {scene}: không kiểm được trục 180° ở shot {', '.join(tags[:6])}" + ("…" if len(tags) > 6 else "")
                   + " — hai người trong khung mà `start_frame` không ghi ai bên trái/phải (frame-left / frame-right)")
    return out


# ---- hộp thư 12/10 15:51 (người dùng: "hướng đi của nhân vật và bố cục của cảnh cần nhất quán"), cờ `continuity_layout` ---------
# #27: shot 3→4 and 11–12 walked opposite ways into the same gate (one from behind, one facing camera); the gate / glue walls / enemies
# changed sides between shots of the same place (scene 1 ↔ scene 6); three team-mates lying in a spot vanished from the next shot there.
_BEHIND = re.compile(r"(?<!\w)(?:camera (?:is )?behind|from behind|seen from (?:the )?back|seen from behind|back to (?:the )?camera|"
                     r"walk(?:s|ing)? away from (?:the )?camera|rear view|third[- ]person (?:view|camera)|"
                     r"máy (?:ở )?sau lưng|từ phía sau|quay lưng về (?:phía )?máy|đi ra xa máy)(?!\w)", re.I)
_FRONT = re.compile(r"(?<!\w)(?:fac(?:ing|es|e) (?:the )?camera|toward(?:s)? (?:the )?camera|walk(?:s|ing)? toward(?:s)? (?:the )?camera|"
                    r"front view|head[- ]on|đối diện máy|hướng về máy|nhìn thẳng máy|đi về phía máy)(?!\w)", re.I)
_INTO = re.compile(r"(?<!\w)(?:walk(?:s|ing)?|run(?:s|ning)?|step(?:s|ping)?|head(?:s|ing)?|move(?:s|ing)?|go(?:es|ing)?)\s+"
                   r"(?:into|toward(?:s)?|through)\s+(?:the\s+)?([a-z][a-z\- ]{2,40}?)(?=[.,;]| and | while |$)|"
                   r"(?:đi|chạy|bước)\s+(?:vào|về phía|qua)\s+([^.,;]{3,30})", re.I)
_OBJ_SIDE = re.compile(r"(?:the|a|an)\s+([a-z][a-z\- ]{2,30}?)\s+(?:is\s+|stands\s+|stays\s+)?(?:on|at|to)\s+(?:the\s+)?"
                       r"(?:frame[- ])?(left|right)(?:\s+(?:side|of (?:the )?frame))?\b(?!\s+of\s+(?!(?:the\s+)?frame))|"
                       r"(?:frame[- ])?(left|right)(?:\s+side)?\s*[:—-]\s*(?:the\s+|a\s+)?([a-z][a-z\- ]{2,30}?)(?=[.,;]|$)", re.I)
_STILL = re.compile(r"(?<!\w)(?:lying(?!\s+to\b)|lies(?!\s+to\b)|lay(?!\s+(?:out|down the)\b)|slumped|unconscious|knocked out|motionless|standing still|sprawled|"
                    r"nằm|gục|bất tỉnh|bất động|đứng yên)(?!\w)", re.I)
_STOP_HEAD = {"camera", "frame", "shot", "side", "way", "her", "him", "them", "it", "left", "right"}
# (c) only things that stay put — a person or "a soldier" walks about between shots (rà 12/10)
_FIXED = {"gate", "torii", "wall", "walls", "door", "doorway", "tree", "building", "house", "tower", "well", "stairs", "staircase",
          "fence", "rock", "statue", "pillar", "column", "window", "bridge", "shrine", "temple", "car", "truck", "barrel", "crate",
          "container", "lamp", "lamppost", "sign", "bench", "fountain", "portal", "cổng", "tường", "cửa", "cây", "nhà", "tháp",
          "giếng", "cầu", "thang", "hàng", "rào", "đá", "tượng", "cột", "xe"}
_OBJ_SIDE_VI = re.compile(r"(cổng|tường|cửa|cây|nhà|tháp|giếng|cầu thang|hàng rào|tảng đá|tượng|cột|xe)[^.,;]{0,25}?"
                          r"(?:ở\s+)?(?:bên\s+|phía\s+)?(trái|phải)\s*(?:khung|màn hình)?", re.I)


def _said(rx, text: str) -> bool:
    """A match not negated by the words right before it ("not facing camera", "không quay lưng về máy")."""
    return any(not _NEGATION.search(text[:m.start()]) for m in rx.finditer(text))


def _facing(shot: Dict) -> Optional[str]:
    text = " ".join(str(shot.get(k) or "") for k in ("image_prompt", "blocking", "start_frame", "action"))
    b, f = _said(_BEHIND, text), _said(_FRONT, text)
    return ("behind" if b else "front") if b != f else None


def _place(shot: Dict) -> str:
    return re.sub(r"\s+", " ", str(shot.get("plate_spot") or shot.get("location") or "")).strip().lower()


_CUT = {"at", "in", "on", "with", "of", "from", "by", "near", "under", "behind", "past", "before", "after", "during", "toward", "towards",
        "lúc", "khi", "với", "của", "trong", "ở"}


def _head(phrase: str) -> str:
    """The thing named: the words up to a preposition / an -ly adverb, the last of them ("the dense bamboo forest at dusk" → forest);
    '' when a word of it is not a thing (camera, frame…)."""
    words = []
    for w in re.split(r"[\s\-]+", (phrase or "").lower()):
        if not w:
            continue
        if w in _CUT or (len(w) > 4 and w.endswith("ly")):
            break
        words.append(w)
    if not words or any(w in _STOP_HEAD for w in words):
        return ""
    return words[-1]


def _targets(shot: Dict) -> List[str]:
    text = " ".join(str(shot.get(k) or "") for k in ("image_prompt", "blocking", "action"))
    out = []
    for m in _INTO.finditer(text):
        h = _head(m.group(1) or m.group(2) or "")
        if h and h not in _STOP_HEAD:
            out.append(h)
    return out


def _object_sides(shot: Dict) -> Dict[str, int]:
    chars = {str(c).lower() for c in shot.get("characters") or []}
    text = " ".join(str(shot.get(k) or "") for k in ("image_prompt", "blocking", "start_frame"))
    out: Dict[str, int] = {}
    for m in _OBJ_SIDE.finditer(text):
        phrase, side = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        h = _head(phrase)
        if h in _FIXED and h not in chars and not any(h in c for c in chars):
            out.setdefault(h, -1 if side.lower() == "left" else 1)
    for m in _OBJ_SIDE_VI.finditer(text):
        out.setdefault(m.group(1).lower(), -1 if m.group(2).lower() == "trái" else 1)
    return out


def layout_warnings(shots: List[Tuple[int, int, Dict]]) -> List[str]:
    """Soft (VÀNG) checks of screen direction vs camera and of the place's layout, cờ `continuity_layout` ([] when off):
    (b) consecutive shots going INTO the same thing, one seen from behind and the other facing camera → they read as walking opposite
        ways; a shot going into/toward something that says neither "camera behind" nor "facing camera" → said (cannot be checked);
    (c) a fixed thing (gate, wall…) or a person written frame-left/right keeps its side in every shot of the same place (plate_spot /
        location), even when a later scene comes back to it — unless the camera is turned round (one behind, one facing);
    (d) someone lying / standing still in a place, the next shot of that same place (camera not turned round) without them."""
    if not _layout_on():
        return []
    out: List[str] = []
    prev = None
    sides_at: Dict[Tuple[str, str], Tuple[str, int, Optional[str]]] = {}
    unknown: Dict[int, List[str]] = {}                # scene -> shots going into something without a camera side (said once per scene)
    for scene, k, s in shots:
        tag = f"{scene}·{k}"
        if _exempt(s) or str(s.get("angle") or "").lower() == "ots":
            prev = (scene, k, s)                      # rà 12/10: an over-the-shoulder pair flips the sides on purpose
            continue
        face, targets, place = _facing(s), _targets(s), _place(s)
        if targets and face is None:
            unknown.setdefault(scene, []).append(f"{tag} ('{targets[0]}')")
        if prev is not None and prev[0] == scene:
            pf, pt = _facing(prev[2]), _targets(prev[2])
            common = set(targets) & set(pt)
            if common and face and pf and face != pf:
                out.append(f"shot {tag}: cùng đi vào '{sorted(common)[0]}' như shot {prev[0]}·{prev[1]} nhưng một shot máy sau lưng, một shot nhân "
                           "vật hướng về máy — người xem thấy đi ngược chiều (giữ cùng phía máy, hoặc ghi lý do)")
            close = (str(s.get("shot") or s.get("size") or "").upper() in ("CU", "ECU", "INSERT", "MCU")
                     or re.search(r"(?<!\w)(?:extreme close[- ]up|close[- ]up|insert|cận cảnh|đặc tả)(?!\w)", str(s.get("image_prompt") or ""), re.I))
            if place and place == _place(prev[2]) and not (face and pf and face != pf) and not close:
                gone = []
                for n in prev[2].get("characters") or []:
                    clause = next((c for c in _clauses(str(prev[2].get("image_prompt") or "") + " . " + str(prev[2].get("blocking") or ""))
                                   if re.search(rf"\b{re.escape(str(n))}\b", c, re.I)), "")
                    if clause and _STILL.search(clause) and n not in (s.get("characters") or []):
                        gone.append(str(n))
                if gone:
                    out.append(f"shot {tag}: {', '.join(gone)} đang nằm/đứng yên ở chỗ này trong shot {prev[0]}·{prev[1]} mà shot này (cùng chỗ, "
                               "máy không quay ngược) không có — người xem thấy biến mất (thêm vào nhân vật của shot, hoặc ghi máy nhìn hướng khác)")
        if place:
            for thing, side in _object_sides(s).items():  # rà 12/10: fixed things only — people walk about between shots
                key = (place, thing)
                if key in sides_at:
                    first_tag, first_side, first_face = sides_at[key]
                    same_side_camera = face == first_face   # both said and equal, or both unsaid; one unsaid → cannot tell
                    if side != first_side and same_side_camera:
                        out.append(f"shot {tag}: '{thing}' ở {'trái' if side < 0 else 'phải'} khung, shot {first_tag} cùng chỗ ghi "
                                   f"{'trái' if first_side < 0 else 'phải'} — giữ sơ đồ chỗ (hoặc ghi máy quay ngược / lý do)")
                else:
                    sides_at[key] = (tag, side, face)
        prev = (scene, k, s)
    for scene, tags in unknown.items():
        out.append(f"cảnh {scene}: shot {', '.join(tags[:5])}" + ("…" if len(tags) > 5 else "") + " đi vào/tới một chỗ mà không ghi máy ở "
                   "sau lưng hay trước mặt — không kiểm được hướng đi (ghi 'camera behind' / 'facing camera')")
    return out


def motif_warnings(shots: List[Tuple[int, int, Dict]]) -> List[str]:
    count: Dict[str, List[str]] = {}
    for scene, k, s in shots:
        tag = str(s.get("motif") or "").strip().lower()
        if tag:
            count.setdefault(tag, []).append(f"{scene}·{k}")
    return [f"motif \"{m}\" chỉ có ở shot {w[0]} — motif phải lặp lại (và biến tấu) mới thành motif" for m, w in count.items() if len(w) < 2]


# dp.md Q8: the scene's `lighting` is one reference table for all its shots, written as source — side — colour (K) — key:fill — tone
_LIGHT_PARTS = (("nguồn", re.compile(r"sun|moon|lamp|street ?light|daylight|fire|torch|neon|window|screen|candle|lantern|headlight|flash|sky|"
                                     r"mặt trời|trăng|đèn|lửa|cửa sổ|màn hình", re.I)),
                ("phía", re.compile(r"\b(frame[- ])?(front[- ]|back[- ])?(left|right)\b|from (the )?(behind|above|below|front|back)|overhead|"
                                    r"back ?light|rim|"
                                    r"top ?light|side ?light|bên (trái|phải)|phía (sau|trên|trước)|ngược sáng", re.I)),
                ("màu K", re.compile(r"\d{4}\s*K\b|warm|cold|cool|ấm|lạnh", re.I)),
                ("tỉ lệ", re.compile(r"key\s*:\s*fill|\d+\s*:\s*1\b", re.I)),
                ("tông", re.compile(r"high[- ]key|low[- ]key|tông (cao|thấp)", re.I)))


def lighting_warnings(scenes: List[Dict]) -> List[str]:
    """Scenes whose `lighting` misses parts of the dp.md Q8 template (soft; an empty lighting is said too — the shots then light
    themselves one by one and the light direction can change between them)."""
    out = []
    for sc in scenes:
        text = str(sc.get("lighting") or "").strip()
        if not text:
            out.append(f"cảnh {sc.get('idx')}: chưa có `lighting` — các shot tự chọn ánh sáng, hướng sáng dễ đổi giữa shot")
            continue
        missing = [name for name, rx in _LIGHT_PARTS if not rx.search(text)]
        if len(missing) >= 2:
            out.append(f"cảnh {sc.get('idx')}: `lighting` thiếu {', '.join(missing)} (mẫu: nguồn — phía — màu K — key:fill — tông)")
    return out
