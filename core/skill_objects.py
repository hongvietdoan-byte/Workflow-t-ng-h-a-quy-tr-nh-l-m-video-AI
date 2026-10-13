"""Vật kỹ năng / hiệu ứng kỹ năng — công thức chung (cờ `skill_object_guard`, LỖI HỆ THỐNG 3 của #27, 13/10).

Gốc lỗi (#27 shot 16–19): Kho mô tả skin Gloowall OB55 là "tường dạng cửa thang máy kim loại xám…" (assets.description của Bom keo,
id 367) → Đạo diễn dịch thành "grey metal elevator-door panels", "elevator-skin glue wall", "closed doors" → model video hiểu là
THANG MÁY THẬT (cửa mở, nhìn xuyên, người đứng trong). 6 lần gen video shot 16 đều hỏng; bản giao dựng bằng GHÉP code
(`data/projects/27/videos/16_ghep_tuong.mp4`: clip ném + khung cuối trồi lên 7 khung + rung).

Công thức (cho mọi vật kỹ năng — tường keo, sau này thêm loại vào SKILL_CATEGORIES):
(a) chữ: câu nào nói tới vật kỹ năng thì bỏ từ gây hiểu sai (elevator / lift / door / thang máy / cửa) → tả theo hình dạng + chất liệu
    ("flat metal panels"), và luôn kèm câu cấm (không cửa mở, không nhìn xuyên, không ai đứng trong). Áp lúc GỬI (prompt ảnh + motion),
    lúc đưa Kho cho Đạo diễn (assets.context_text) — dữ liệu nguồn không bị sửa, phần đã thay được báo (luật 1).
(b) dựng: shot có vật kỹ năng MỌC LÊN mà đi gen video → VÀNG gợi ý dựng bằng ghép code (`compose_plan`, `compose`,
    CLI `tools/skill_object_composite.py`): clip người ném tới lúc vật chạm đất + khung cuối (vật đã dựng) trồi lên từ dưới + rung.

Cờ tắt → không đổi gì (từng byte). 0 USD, không gọi API."""
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

SKILL_CATEGORIES = ("glue",)        # prop_lock.CATEGORIES đang là vật kỹ năng (súng thì không)

# (mẫu, thay bằng) — thứ tự quan trọng: cụm dài trước. Chỉ áp trong câu nói tới vật kỹ năng.
_EN_FIXES: List[Tuple[re.Pattern, object]] = [
    (re.compile(r"(?<!\w)(?:an?\s+)?(?:elevator|lift)[- ]?doors?(?:[- ]style)?(?:\s+(panels?))?(?!\w)", re.I),
     lambda m: ("" if not re.match(r"an?\s", m.group(0), re.I) else "a ") + "flat "
     + (m.group(1) or ("panels" if re.search(r"doors(?!\w)", m.group(0), re.I) else "panel"))),
    (re.compile(r"(?<!\w)(?:an?\s+)?(?:elevator|lift)[- ](?:skin|style)(?!\w)", re.I),
     lambda m: ("" if not re.match(r"an?\s", m.group(0), re.I) else "a ") + "metal-panel skin"),
    (re.compile(r"(?<!\w)(?:an\s+)?elevators?(?!\w)", re.I),
     lambda m: ("a " if re.match(r"an\s", m.group(0), re.I) else "") + "metal-panel"),
    (re.compile(r"(?<!\w)doorways?(?!\w)", re.I), lambda m: "panel"),
    (re.compile(r"(?<!\w)(?:(?:closed|sliding|shut|open(?:ing)?)\s+)?doors(?!\w)", re.I), lambda m: "flat panels"),
    (re.compile(r"(?<!\w)(?:(?:closed|sliding|shut|open(?:ing)?)\s+)?door(?!\w)", re.I), lambda m: "flat panel"),
    (re.compile(r"(?<!\w)cabins?(?!\w)", re.I), lambda m: "panel"),
]
_VI_FIXES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?<!\w)(?:cánh\s+)?cửa\s+thang\s+máy(?!\w)", re.I), "tấm phẳng"),
    (re.compile(r"(?<!\w)thang\s+máy(?!\w)", re.I), "tấm kim loại"),
    (re.compile(r"(?<!\w)cánh\s+cửa(?!\w)", re.I), "tấm phẳng"),
    (re.compile(r"(?<!\w)cửa(?!\w)", re.I), "tấm"),
]
# what the misreading words are (shown in warnings / the Director note)
MISREAD_RX = re.compile(r"(?<!\w)(?:elevators?|lifts?[- ]doors?|doors?|doorways?|cabins?|thang\s+máy|cửa)(?!\w)", re.I)
# "the wall shoots up" — the skill object appears in the shot (where a video model draws it worst)
_RISES = re.compile(r"(?<!\w)(?:pops?|popping|shoots?|shooting|springs?|springing|rises?|rising|risen|bursts?|grows?|growing|erupts?)"
                    r"(?:\s+\w+){0,2}?\s+(?:up|out of the ground|from the ground)(?!\w)|"
                    r"(?<!\w)(?:throws?|throwing|flicks?|tosses?|tossing|hurls?)\s+(?:\w+\s+){0,3}(?:glue|gloo)\w*(?:[ -]grenades?|[ -]bombs?)?|"
                    r"ném\s+bom\s+keo|mọc\s+(?:lên|ngay)|dựng\s+lên|trồi\s+lên|bật\s+lên", re.I)
_WALL = re.compile(r"(?<!\w)walls?(?!\w)", re.I)

FORBID = ("{names} is a solid skill object standing on the ground, not part of a building: one closed solid surface with no opening "
          "of any kind, no room or space inside, nothing is seen through it and nobody stands in it.")


def enabled() -> bool:
    try:
        from . import features
        return features.on("skill_object_guard")
    except Exception:  # noqa: BLE001 - unreadable settings: the old behaviour (off)
        return False


def skill_assets(conn, project_id: Optional[int]) -> List[Dict]:
    """The project's Kho weapons / props that are skill objects (prop_lock.category in SKILL_CATEGORIES)."""
    if conn is None or project_id is None:
        return []
    from . import assets, prop_lock
    try:
        return [a for a in assets.project_assets(conn, project_id) if prop_lock.category(a) in SKILL_CATEGORIES]
    except Exception:  # noqa: BLE001 - a check never stops a send
        return []


def _generic_rx():
    from . import prop_lock
    return [prop_lock._SHOT_RX[c] for c in SKILL_CATEGORIES]


def _name_rx(names: Sequence[str]):
    names = [n.strip() for n in names if n and len(n.strip()) >= 3]
    if not names:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")(?!\w)", re.I)


def _names_of(items: Sequence[Dict]) -> List[str]:
    from . import assets
    out: List[str] = []
    for a in items:
        out += [n for n in assets.names_of(a) if n.strip()]
    return list(dict.fromkeys(out))


def mentions(text: str, names: Sequence[str] = ()) -> bool:
    """The text speaks of a skill object (its Kho name / alias, or the category's common word: glue wall, gloo wall…)."""
    if not text:
        return False
    rx = _name_rx(names)
    return bool((rx and rx.search(text)) or any(r.search(text) for r in _generic_rx()))


def _sentences(text: str) -> List[str]:
    return re.split(r"(?<=[.!?;\n])", text)


def sanitize(text: str, names: Sequence[str] = ()) -> Tuple[str, List[str]]:
    """(text, the words replaced): in every sentence that speaks of a skill object (or of 'the wall' in a text that does), the words
    a model reads as a real lift / door are replaced by shape words. Other sentences are untouched (a house door stays a door)."""
    if not text or not mentions(text, names):
        return text, []
    rx = _name_rx(names)
    removed: List[str] = []
    out = []
    for sent in _sentences(text):
        about = (rx and rx.search(sent)) or any(r.search(sent) for r in _generic_rx()) or _WALL.search(sent)
        if about and MISREAD_RX.search(sent):
            for pat, rep in _EN_FIXES + _VI_FIXES:
                def sub(m, rep=rep):
                    removed.append(m.group(0).strip())
                    return rep(m) if callable(rep) else rep
                sent = pat.sub(sub, sent)
            sent = re.sub(r"\bflat flat\b", "flat", sent)
            sent = re.sub(r"[ \t]{2,}", " ", sent)
        out.append(sent)
    return "".join(out), list(dict.fromkeys(removed))


def forbid_sentence(names: Sequence[str]) -> str:
    label = " / ".join(names[:2]) if names else "The glue wall"
    return FORBID.format(names=label[0].upper() + label[1:])


def _present_names(conn, project_id, text: str) -> Tuple[List[str], bool]:
    """(Kho names of the skill objects the text names, the category's common word said)."""
    items = skill_assets(conn, project_id)
    named = [a["name"] for a in items if (_name_rx(_names_of([a])) or re.compile("$^")).search(text or "")]
    generic = any(r.search(text or "") for r in _generic_rx())
    if not named and generic and len(items) == 1:
        named = [items[0]["name"]]
    return named, generic


def guard_prompt(conn, project_id: Optional[int], text: str) -> Tuple[str, List[str], List[str]]:
    """(text to send, the words replaced, the skill objects found). Flag off / no skill object in the text → (text, [], [])."""
    if not enabled() or not text:
        return text, [], []
    named, generic = _present_names(conn, project_id, text)
    if not named and not generic:
        return text, [], []
    names = _names_of([a for a in skill_assets(conn, project_id) if a["name"] in named])
    new, removed = sanitize(text, names)
    sentence = forbid_sentence(named or ["the glue wall"])
    if sentence not in new:
        new = new.rstrip() + ("\n" if "\n" in new else " ") + sentence
    return new, removed, named or ["glue wall"]


def reserve() -> int:
    """Characters the send may add after a model-limited prompt is built (the ban sentence + a longer name); 0 when off."""
    return len(FORBID) + 40 if enabled() else 0


def rises(data: Dict, names: Sequence[str] = ()) -> bool:
    """The shot shows the skill object APPEARING (thrown, popping / shooting up) — what a video model draws worst (#27 shot 16)."""
    from . import prop_lock
    text = prop_lock.shot_text(data or {})
    motion = (data or {}).get("motion_en") or {}
    if isinstance(motion, dict):
        text += " " + " ".join(str(v) for v in motion.values() if isinstance(v, str))
    # only in a sentence about the skill object ("the tower rising out of the frame" is not one — #27 shot 17)
    return any(_RISES.search(s) and (mentions(s, names) or _WALL.search(s)) for s in _sentences(text))


COMPOSE_TOOL = "tools/skill_object_composite.py"


def compose_plan(data: Dict, scene_id: Optional[int] = None) -> Dict:
    """The structured suggestion 'build this shot by compositing in code' (as #27 shot 16)."""
    return {
        "route": "compose",
        "why": "model video vẽ sai vật kỹ năng (#27 shot 16: 6 lần gen đều hỏng) — ghép bằng code rẻ và chắc hơn",
        "steps": ["gen video CHỈ phần người (ném / chạy), không tả vật kỹ năng mọc lên",
                  "vẽ khung cuối có vật kỹ năng đã dựng xong (end_state)",
                  f"ghép: py {COMPOSE_TOOL} --clip <clip người> --end <khung cuối> --cut <giây vật chạm đất> --out <mp4>"],
        "tool": COMPOSE_TOOL,
        "scene_id": scene_id,
    }


def issues(conn, project_id: Optional[int], data: Dict) -> List[Dict]:
    """VÀNG (never a stop) for the prompt formula (part 'dao_cu'): misreading words written about a skill object (replaced at send),
    and a shot where the skill object appears → suggest the code composite. [] when off / nothing found."""
    if not enabled() or not data:
        return []
    from . import prop_lock
    text = prop_lock.shot_text(data)
    motion = data.get("motion_en") or {}
    if isinstance(motion, dict):
        text += " " + " ".join(str(v) for v in motion.values() if isinstance(v, str))
    named, generic = _present_names(conn, project_id, text)
    if not named and not generic:
        return []
    who = ", ".join(named) or "vật kỹ năng"
    out = []
    names = _names_of([a for a in skill_assets(conn, project_id) if a["name"] in named])
    _, bad = sanitize(text, names)
    if bad:
        out.append({"level": "warn", "part": "dao_cu",
                    "msg": f"chữ shot tả {who} bằng từ dễ bị model hiểu thành vật thật ({', '.join(bad[:4])}) — khi gửi code thay bằng "
                           "từ hình dạng/chất liệu + câu cấm; nên sửa chữ shot cho khớp"})
    if rises(data, names):
        plan = compose_plan(data)
        out.append({"level": "warn", "part": "dao_cu", "suggest": plan,
                    "msg": f"shot có {who} mọc lên — model video hay vẽ sai vật kỹ năng; gợi ý dựng bằng GHÉP code (khung cuối + mọc lên "
                           f"+ rung, `{COMPOSE_TOOL}`) thay vì gen cả hiệu ứng"})
    return out


def director_note(asset: Dict) -> str:
    """The sentence after a skill object in the Director's Kho block ('' when off / not a skill object)."""
    from . import prop_lock
    if not enabled() or prop_lock.category(asset) not in SKILL_CATEGORIES:
        return ""
    return (" — VẬT KỸ NĂNG: khi viết prompt tả theo hình dạng/chất liệu (tấm kim loại phẳng, khung, đèn…), KHÔNG dùng chữ "
            "thang máy / cửa / elevator / door / lift (model vẽ thành thang máy thật, cửa mở, người đứng trong)")


def director_description(asset: Dict, text: str) -> str:
    """The skill object's own Kho description for the Director with the misreading words replaced (unchanged when off / other)."""
    from . import prop_lock
    if not enabled() or prop_lock.category(asset) not in SKILL_CATEGORIES:
        return text
    return sanitize(text, _names_of([asset]) + ["tường"])[0]


# ---- (b) dựng bằng ghép code ------------------------------------------------------------------------------------------------
def wall_top(end_img, base_img, min_share: float = 0.5, diff: int = 40) -> int:
    """Row where the skill object starts in the end frame: the first row from the top where ≥ min_share of the width differs from the
    clip frame at the cut (the object covers the frame wide, the person alone does not). No such row: the lower half."""
    import numpy as np
    a = np.asarray(end_img, dtype=np.int16)
    b = np.asarray(base_img, dtype=np.int16)
    changed = (np.abs(a - b).max(axis=2) > diff).mean(axis=1)
    rows = np.nonzero(changed >= min_share)[0]
    return int(rows[0]) if len(rows) else a.shape[0] // 2


def _shift(img, dx: int, dy: int):
    """img moved by (dx, dy) px, the uncovered edge repeated (no wrap-around seam)."""
    import numpy as np
    h, w = img.shape[:2]
    p = max(abs(dx), abs(dy))
    if not p:
        return img
    padded = np.pad(img, ((p, p), (p, p), (0, 0)), mode="edge")
    return padded[p - dy:p - dy + h, p - dx:p - dx + w]


def composite_frames(clip_frames: List, end_img, cut_index: int, total: int, rise: int = 7, shake: int = 8, shake_px: int = 10,
                     top: Optional[int] = None) -> List:
    """Frames (numpy RGB) of the composite: the clip up to cut_index, then the end frame's object part rising from the bottom over
    `rise` frames on top of the clip (still running, last frame held), then the end frame shaking `shake` frames (decaying), held to
    `total`. Pure function — tested without ffmpeg."""
    import numpy as np
    end = np.asarray(end_img).copy()
    h, w = end.shape[:2]
    cut_index = max(0, min(cut_index, len(clip_frames) - 1))
    if top is None:
        top = wall_top(end, clip_frames[cut_index])
    part = end[top:]
    out = [np.asarray(f) for f in clip_frames[:cut_index]]
    for k in range(1, rise + 1):
        base = np.asarray(clip_frames[min(cut_index + k - 1, len(clip_frames) - 1)]).copy()
        shown = int(round(part.shape[0] * k / rise))
        if shown:
            base[h - shown:] = part[:shown]
        out.append(base)
    for k in range(shake):
        amp = int(round(shake_px * (1 - k / max(shake, 1))))
        dx, dy = (amp if k % 2 == 0 else -amp), (amp // 2 if k % 4 < 2 else -(amp // 2))
        out.append(_shift(end, dx, dy))
    while len(out) < total:
        out.append(end)
    return out[:total]


def compose(clip: str, end_frame: str, out: str, cut_s: float, rise: int = 7, shake: int = 8, shake_px: int = 10,
            top: Optional[int] = None, ffmpeg: Optional[str] = None) -> Dict:
    """Write the composite mp4 (same size / fps / length as the clip, no sound). Returns the numbers used (said by the CLI)."""
    import subprocess
    import cv2
    import numpy as np
    from PIL import Image
    cap = cv2.VideoCapture(clip)
    if not cap.isOpened():
        raise FileNotFoundError(f"không mở được clip: {clip}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    if not frames:
        raise ValueError(f"clip không có khung: {clip}")
    h, w = frames[0].shape[:2]
    end = np.asarray(Image.open(end_frame).convert("RGB").resize((w, h), Image.LANCZOS))
    cut = int(round(cut_s * fps))
    if top is None:
        top = wall_top(end, frames[max(0, min(cut, len(frames) - 1))])
    result = composite_frames(frames, end, cut, len(frames), rise, shake, shake_px, top)
    if ffmpeg is None:
        from .ffmpeg_studio import find_ffmpeg
        ffmpeg = find_ffmpeg()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    proc = subprocess.Popen([ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", f"{fps:g}",
                             "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", out], stdin=subprocess.PIPE)
    for f in result:
        proc.stdin.write(np.ascontiguousarray(f, dtype=np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg ghép lỗi")
    return {"out": out, "fps": fps, "frames": len(result), "cut_frame": cut, "wall_top": top, "rise": rise, "shake": shake}
