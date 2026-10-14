"""Trái / phải của NHÂN VẬT → trái / phải của KHUNG — sự thật do code viết, không gọi model (người dùng 14/10, thử D6 #28/#29).

Gốc lỗi: kịch bản "Kelly đứng sát, núp ở bên TRÁI bức tường keo" → ảnh + clip Kelly núp bên phải khung. Trước đây trái/phải chỉ là LUẬT
CHỮ trong knowledge/model_guides/*.md (trái/phải là của nhân vật; máy sau lưng = cùng phía khung; máy trước mặt = ngược) — model có thể
không theo. Theo docs/DANH_GIA_VAI_DAO_DIEN_2026-10-14.md mục 3 ("Đạo diễn QUYẾT, code VIẾT sự thật"): code quy đổi và chèn MỘT câu rõ
ràng vào prompt ảnh + video (core/runner._side_truth, như skill_objects.SHAPE chèn câu tường keo).

    for_shot(script, data) -> {"sentence": str, "warn": str | None, "mentions": [...], "camera": "behind" | "front" | None}

Chữ đọc: CHỈ vế câu kịch bản gốc khớp shot (core/script_pose.script_poses; `action` của Đạo diễn hay viết trái/phải theo người xem nên
không đọc, chỉ dùng để tìm vế + tìm tên nhân vật). Chỉ khớp chữ CÓ DẤU "trái" / "phải" đứng sau
"bên / phía / sang / qua / tay" — "phải" một mình còn nghĩa "cần phải" ("Kelly phải núp") nên không bao giờ tính.
Hướng máy so với nhân vật: chỉ từ chữ của chính shot — sau lưng (plate_choice.is_behind: ots / GAME_TPS / "from behind" / "back to
camera") hoặc trước mặt (góc ngược / "facing the camera" / "front view" / "nhìn thẳng mặt"). Góc nghiêng (profile), cả hai, không chữ nào,
hay nhiều nhân vật (trái của ai?) → KHÔNG đoán: câu rỗng + `warn` nêu lý do (VÀNG ở ⚙ Chẩn đoán).
"""
import re
from typing import Dict, List, Optional, Tuple

FLAG = "side_truth"

# "bên trái", "phía bên phải", "sang trái", "qua phải", "về bên trái", "tay phải" — chữ có dấu (bỏ dấu "trai" = con trai, "phai" = phai màu)
_SIDE_VI = re.compile(r"(?<!\w)(bên|phía|sang|qua|tay)\s+(?:(?:bên|phía)\s+)?(trái|phải)(?!\w)", re.I)
_FRONT = re.compile(r"\breverse\b|góc ngược|đối diện (?:máy|camera|ống kính)|facing (?:the |towards? the )?(?:camera|viewer|lens)|"
                    r"faces? (?:the |towards? the )?(?:camera|viewer|lens)|toward(?:s)? (?:the )?camera|face[- ]on|front view|"
                    r"from the front|looking (?:straight )?(?:at|into) the (?:camera|lens)|nhìn thẳng (?:vào )?(?:mặt|máy|camera)|"
                    r"mặt hướng (?:về )?(?:phía )?(?:máy|camera)", re.I)
_PROFILE = re.compile(r"\bprofile\b|side[- ](?:on|view)|góc nghiêng|nhìn nghiêng|ngang hông", re.I)
_NEG = re.compile(r"(?:\bnot|\bnever|\bno|n't|không|chưa)\s+(?:\w+\s+){0,2}$", re.I)


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _nfc(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", text or "")


def mentions(text: str) -> List[Tuple[str, str]]:
    """[(cụm chữ như viết, 'left' | 'right')] — mỗi cụm một lần, theo thứ tự xuất hiện."""
    out, seen = [], set()
    for m in _SIDE_VI.finditer(_nfc(text)):
        phrase = re.sub(r"\s+", " ", m.group(0)).strip()
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            out.append((phrase, "left" if m.group(2).lower() == "trái" else "right"))
    return out


def _hit(rx: "re.Pattern", text: str) -> bool:
    for m in rx.finditer(text):
        if not _NEG.search(text[max(0, m.start() - 30):m.start()]):
            return True
    return False


def camera_relation(data: Dict) -> Tuple[Optional[str], str]:
    """('behind' | 'front' | None, lý do). Chỉ từ chữ máy của shot; không đủ chắc → None + lý do."""
    from . import plate_choice
    words = _nfc(" ".join(str(data.get(k) or "") for k in ("angle", "shot", "blocking", "start_frame")))
    behind = plate_choice.is_behind(data)
    front = _hit(_FRONT, words) or str(data.get("angle") or "").strip().lower() == "reverse"
    if behind and front:
        return None, "chữ máy của shot nói cả 'sau lưng' lẫn 'trước mặt' nhân vật"
    if _hit(_PROFILE, words) and not (behind or front):
        return None, "máy ngang hông nhân vật (góc nghiêng) — trái/phải của nhân vật là gần/xa máy, không phải trái/phải khung"
    if behind:
        return "behind", "máy sau lưng nhân vật"
    if front:
        return "front", "máy trước mặt nhân vật"
    return None, "shot không ghi máy sau lưng hay trước mặt nhân vật (angle / blocking / start_frame)"


def _who(data: Dict, text: str = "") -> Tuple[Optional[str], str]:
    cast = [c for c in (data.get("characters") or []) if isinstance(c, str) and c.strip()]
    if len(cast) == 1:
        return cast[0].strip(), ""
    named = [c for c in cast if re.search(r"(?<!\w)" + re.escape(c.strip()) + r"(?!\w)", text or "", re.I)]
    if len(named) == 1:                          # several in the shot, the side words name exactly one of them ("Kelly núp bên trái")
        return named[0].strip(), ""
    byd = data.get("byd") if isinstance(data.get("byd"), dict) else {}
    ai = list(dict.fromkeys(h.get("ai") for h in byd.get("hanh_dong") or [] if isinstance(h, dict) and h.get("ai")))
    if not cast and len(ai) == 1:
        return str(ai[0]), ""
    if not cast and not ai:
        return None, "shot không có nhân vật — không biết trái/phải của ai"
    return None, f"shot có {len(cast) or len(ai)} nhân vật — không biết trái/phải của ai"


def _frame(side: str, camera: str) -> str:
    return side if camera == "behind" else {"left": "right", "right": "left"}[side]


def sentence(name: str, camera: str, found: List[Tuple[str, str]]) -> str:
    where = ("the camera is behind " + name + ", so " + name + "'s left is FRAME-LEFT and right is FRAME-RIGHT"
             if camera == "behind" else
             "the camera is in front of " + name + ", facing them, so " + name + "'s left is FRAME-RIGHT and right is FRAME-LEFT")
    parts = "; ".join(f"'{p}' ({name}'s {s}) = FRAME-{_frame(s, camera).upper()}" for p, s in found)
    return f"Sides: left/right in the script are {name}'s own — {where}: {parts}."


def for_shot(script, data: Dict) -> Dict:
    """`script` = kịch bản gốc (chữ) hoặc chỉ mục của core/script_pose._index (dựng một lần cho cả phim)."""
    from . import script_pose
    out = {"sentence": "", "warn": None, "mentions": [], "camera": None}
    if not isinstance(data, dict):
        return out
    _, words = script_pose.script_poses(script, " ".join(str(data.get(k) or "") for k in ("action", "text"))) if script else ([], "")
    # only the person's own script: the Director's `action` often writes sides as the viewer sees them (#24 shot 12 "giếng sau lưng
    # yêu nữ bên phải" = frame-right) — reading it as the character's side would flip a correct shot
    found = mentions(words)
    out["mentions"] = found
    if not found:
        return out
    said = ", ".join(f"'{p}'" for p, _ in found)
    name, why_who = _who(data, words)
    if name is None:
        out["warn"] = f"kịch bản/shot ghi {said} — không quy đổi được trái/phải sang khung: {why_who}"
        return out
    camera, why = camera_relation(data)
    out["camera"] = camera
    if camera is None:
        out["warn"] = (f"kịch bản/shot ghi {said} — không quy đổi được trái/phải sang khung: {why}; ghi rõ máy sau lưng / trước mặt "
                       "hoặc viết frame-left / frame-right trong prompt")
        return out
    out["sentence"] = sentence(name, camera, found)
    return out


_SENTENCE = re.compile(r"Sides: left/right in the script are [^\n]*?FRAME-(?:LEFT|RIGHT)\.")


def kept_after_rewrite(assembled: str, prompt: str, limit: Optional[int] = None) -> str:
    """D6 (core/chat_prompt) rewrites the assembled prompt: the code's side sentence must survive — every FRAME-LEFT / FRAME-RIGHT it
    names still in the new prompt, else the sentence is added back word for word (code measures, the rewrite never decides sides).
    Added back past `limit` → the assembled prompt (it has the sentence and fits)."""
    m = _SENTENCE.search(assembled or "")
    if not m or prompt == assembled:
        return prompt
    need = {w.lower() for w in re.findall(r"=\s*(FRAME-(?:LEFT|RIGHT))", m.group(0))}
    have = {w.lower().replace(" ", "-") for w in re.findall(r"frame[- ](?:left|right)", prompt or "", re.I)}
    if need <= have:
        return prompt
    out = append(prompt, m.group(0))
    return assembled if limit and len(out) > limit else out


def append(text: str, line: str) -> str:
    if not line or line in (text or ""):
        return text
    return (text or "").rstrip() + ("\n" if "\n" in (text or "") else " ") + line
