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
# line", "never crosses the axis") it says the opposite — keeping the line
_CROSSING = re.compile(r"(?:vượt|qua|nhảy) trục|cross(?:es|ing)? the (?:line|axis)|jump(?:s|ing)? the line", re.I)
_NEGATION = re.compile(r"(?:^|\s)(?:không|chưa|tránh|đừng|chớ|cấm|giữ|not|n't|don't|avoid|never|no)(?:\s+\S+){0,3}\s*$", re.I)


class _OnPurpose:
    @staticmethod
    def search(text: str) -> bool:
        return any(not _NEGATION.search(text[:m.start()]) for m in _CROSSING.finditer(text or ""))


_ON_PURPOSE = _OnPurpose()
_EXEMPT_ANGLES = ("pov", "overhead")


def _clauses(text: str) -> List[str]:
    return [c for c in re.split(r"[.;,]| and | while | với | và ", text or "") if c.strip()]


def sides(shot: Dict) -> Dict[str, int]:
    """name -> -1 (left) / +1 (right) from the shot's start frame words; a clause that names one person and one side decides."""
    out: Dict[str, int] = {}
    for clause in _clauses(str(shot.get("start_frame") or shot.get("blocking") or "")):
        named = [n for n in shot.get("characters") or [] if re.search(rf"\b{re.escape(n)}\b", clause, re.I)]
        left, right = bool(_LEFT.search(clause)), bool(_RIGHT.search(clause))
        if len(named) == 1 and left != right:
            out[named[0]] = -1 if left else 1
    return out


def direction(shot: Dict) -> Optional[int]:
    text = f"{shot.get('start_frame') or ''} {shot.get('end_state') or ''} {shot.get('action') or ''}"
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
