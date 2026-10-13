"""Vật kỹ năng / hiệu ứng kỹ năng — công thức chung (cờ `skill_object_guard`, LỖI HỆ THỐNG 3 của #27, 13/10).

Gốc lỗi (#27 shot 16–19): Kho mô tả skin Gloowall OB55 là "tường dạng cửa thang máy kim loại xám…" (assets.description của Bom keo,
id 367) → Đạo diễn dịch thành "grey metal elevator-door panels", "elevator-skin glue wall", "closed doors" → model video hiểu là
THANG MÁY THẬT (cửa mở, nhìn xuyên, người đứng trong). 6 lần gen video shot 16 đều hỏng; bản giao dựng bằng GHÉP code
(`data/projects/27/videos/16_ghep_tuong.mp4`: clip ném + khung cuối trồi lên 7 khung + rung).

Công thức (cho mọi vật kỹ năng — tường keo, sau này thêm loại vào SKILL_CATEGORIES):
(a) chữ: câu nào nói tới vật kỹ năng thì bỏ từ gây hiểu sai (elevator / lift / door / thang máy / cửa) → tả theo hình dạng + chất liệu
    ("flat metal panels"), và luôn kèm câu cấm (không cửa mở, không nhìn xuyên, không ai đứng trong). Áp lúc GỬI (prompt ảnh + motion),
    lúc đưa Kho cho Đạo diễn (assets.context_text) — dữ liệu nguồn không bị sửa, phần đã thay được báo (luật 1).
(b) XUẤT HIỆN LUÔN (quyết định người dùng 13/10 21:31, thay cơ chế "mọc từ dưới lên"): dùng keo (ném) → tường xuất hiện ngay, khung
    sau đã có tường đứng sẵn đủ chiều cao. Chữ gửi không tả quá trình mọc (`standing_text`: rise/grow/emerge/shoots up/pops up/mọc/
    trồi → "already standing at full height") + câu cấm nói rõ; Kho thiếu ảnh dạng triển khai → chỉ VÀNG (không ĐỎ).
(c) dựng: shot ném keo đi gen video → VÀNG gợi ý dựng bằng ghép code (`compose_plan`, `compose`, CLI
    `tools/skill_object_composite.py`): clip người ném tới lúc vật chạm đất → CẮT CỨNG sang khung cuối (tường đứng sẵn) + rung.

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
    # V4 (rà gốc 13/10, G8): "metal-panel skin" made job 908 a plain steel wall (skin lost) — the skin is a PATTERN, said so; the
    # pattern itself comes from a picture (skin_sentence / DEPLOYED picture), never from metal words
    (re.compile(r"(?<!\w)(?:an?\s+)?(?:elevator|lift)[- ](skin|style)(?!\w)", re.I),
     lambda m: ("" if not re.match(r"an?\s", m.group(0), re.I) else "a ") + ("patterned skin" if m.group(1).lower() == "skin"
                                                                              else "patterned")),
    # rà S2 13/10 mục 4: a lone "elevator" → "patterned" too (never "metal-panel": the 908 plain steel slab)
    (re.compile(r"(?<!\w)(?:an\s+)?elevators?(?!\w)", re.I),
     lambda m: ("a " if re.match(r"an\s", m.group(0), re.I) else "") + "patterned"),
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
# a sentence about a real building's wall / door ("the warehouse door in the brick wall") is not about the skill object
_BUILDING = re.compile(r"(?<!\w)(?:houses?|buildings?|warehouses?|rooms?|towers?|shops?|stores?|garages?|homes?|apartments?|barns?|"
                       r"churche?s?|halls?|bricks?|nhà|phòng|tòa|cửa hàng|nhà kho)(?!\w)", re.I)

FORBID = ("{names} is a solid skill object standing on the ground, not part of a building: one closed solid surface with no opening "
          "of any kind, no room or space inside, nothing is seen through it and nobody stands in it. It appears at once at full height, "
          "never grows, rises or emerges.")

# rà S2 13/10 mục 2 (người dùng 21:31: tường keo XUẤT HIỆN LUÔN): the words that describe the object GROWING, in a sentence about it.
# pop / shoot / spring need "up" (a gun shoots); rise / grow / emerge / erupt do not.
STANDING = "already standing at full height"
_GROW_EN = re.compile(
    r"(?<!\w)(?:(?P<up>pops?|popp(?:ing|ed)|shoots?|shooting|shot|springs?|springing|sprang|sprung)"
    r"|(?P<v>rises?|rising|rose|risen|grows?|growing|grew|grown|emerges?|emerging|emerged|erupts?|erupting|erupted))"
    r"(?P<adv>(?:\s+(?:straight|right|quickly|suddenly|instantly|swiftly|rapidly|abruptly|fast))*)"
    r"(?P<part>(?:\s+(?:up(?:wards?)?|out\s+of\s+the\s+(?:ground|floor)|from\s+the\s+(?:ground|floor)|out|into\s+(?:view|place)))*)"
    r"(?:\s+to\s+(?:its|their|the)\s+full\s+height)?(?!\w)", re.I)
_GROW_VI = re.compile(r"(?<!\w)(?:mọc|trồi)(?:\s+(?:lên|ngay|thẳng))*(?!\w)", re.I)
_SUBJECT = re.compile(r"^(?:walls?|it|glue|gloo\w*|keo|tường|ob\d+)$", re.I)   # who grows: "the glue wall pops up", "it shoots up"
_OTHER_SUBJECT = re.compile(r"^(?:camera|sun|moon|smoke|dust|fog|mist|steam|sparks?|flames?|fire|she|he|they|we|you|tower|nhân|cô|anh)$",
                            re.I)


def _subject_is_object(before: str, names: Sequence[str]) -> Optional[str]:
    """The word before the growing verb (≤ 6 words back: "the glue wall of grey flat panels shoots up") that is the skill object
    ('it', 'wall', its name) — else None. Another subject met first stops it ("the camera rises over the wall", "the sun rises",
    "Kelly rises behind the wall" are not the object growing)."""
    own = {w.lower() for n in names for w in re.findall(r"\w+", n)}
    for word in reversed(re.findall(r"\w+", before)[-6:]):
        if _SUBJECT.match(word) or word.lower() in own:
            return word.lower()
        if _OTHER_SUBJECT.match(word) or word[:1].isupper() and word.isalpha() and word.lower() not in own:
            return None
    return None


_PERFECT = re.compile(r"(?<!\w)(?:has|have|had)\s+(?:\w+\s+)?$", re.I)          # "has (quickly) risen"
_BASE_AUX = re.compile(r"(?<!\w)(?:will|would|can|could|to|must|should)\s+(?:\w+\s+)?$", re.I)   # "will rise", "starts to grow"
_PAST = {"rose", "grew", "grown", "risen", "emerged", "erupted", "popped", "shot", "sprang", "sprung"}


def _standing(m, before: str = "") -> str:
    if m.group("up") and not re.search(r"(?<!\w)up", m.group("part") or "", re.I):
        return m.group(0)                                    # "shoots the gate" — not the object appearing
    verb = (m.group("up") or m.group("v")).lower()
    if _PERFECT.search(before):
        return "been " + STANDING                            # "has been already standing at full height"
    if _BASE_AUX.search(before):
        return "stand at full height at once"                # "will stand at full height at once"
    if verb.endswith("ing"):
        return STANDING
    if verb in _PAST:
        return "was " + STANDING
    return "is " + STANDING


def standing_text(text: str, names: Sequence[str] = ()) -> Tuple[str, List[str]]:
    """(text, the words replaced): in every sentence about the skill object (as `sanitize`), the words of it GROWING become
    "already standing at full height" — it appears at once (người dùng 13/10 21:31). Also "it pops up" / "the wall rises" in a
    sentence that does not name it. The ban sentence is left as written."""
    if not text or not mentions(text, names):
        return text, []
    rx = _name_rx(names)
    removed: List[str] = []
    out = []
    prev_about = False
    for sent in _sentences(text):
        if "never grows, rises or emerges" in sent:
            out.append(sent)
            continue
        about = ((rx and rx.search(sent)) or any(r.search(sent) for r in _generic_rx())
                 or (_WALL.search(sent) and not _BUILDING.search(sent)))

        # "it" counts only in a sentence about the object or right after one ("… glue wall … panels. As it pops up …"),
        # not "The drone hovers, then it rises"
        def sub(m, sent=sent, about=about, prev=prev_about):
            who = _subject_is_object(sent[:m.start()], names)
            if not who or not (about or (who == "it" and prev)):
                return m.group(0)
            rep = _standing(m, sent[:m.start()])
            if rep != m.group(0):
                removed.append(m.group(0).strip())
            return rep

        def sub_vi(m, sent=sent):
            if not _subject_is_object(sent[:m.start()], names):
                return m.group(0)
            removed.append(m.group(0).strip())
            return "đã đứng sẵn đủ cao"
        sent = _GROW_EN.sub(sub, sent)
        if about:
            sent = _GROW_VI.sub(sub_vi, sent)
        if sent.strip():
            prev_about = bool(about)
        out.append(sent)
    return "".join(out), list(dict.fromkeys(removed))


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
        about = ((rx and rx.search(sent)) or any(r.search(sent) for r in _generic_rx())
                 or (_WALL.search(sent) and not _BUILDING.search(sent)))
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
    from .seedance_refs import ascii_name       # rà S2 13/10 mục 3: no Vietnamese letters / lift words of a Kho name in the prompt
    names = [ascii_name(n) for n in names if n and not MISREAD_RX.search(n)]
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
    items = [a for a in skill_assets(conn, project_id) if a["name"] in named]
    names = _names_of(items)
    new, removed = sanitize(text, names)
    new, grown = standing_text(new, names)      # rà S2 13/10 mục 2: it appears at once, never described growing
    removed = removed + grown
    shown = deployed_marker(new)
    if shown:                                   # V4: the prompt maps a DEPLOYED picture → the skin is the one shown there
        new = re.sub(r"(?<!\w)patterned skin(?!\w)", f"skin pattern shown in Image {shown}", new)
    sentence = forbid_sentence(named or ["the glue wall"])
    if sentence not in new:
        new = new.rstrip() + ("\n" if "\n" in new else " ") + sentence
    skin = skin_sentence(items, new, removed, shown)
    if skin and skin not in new:
        new = new.rstrip() + " " + skin
    return new, removed, named or ["glue wall"]


# ---- V4 (rà gốc video #27 13/10, G8): the skin needs a PICTURE of the deployed object, words alone swap one fault for another ----
# 891: "elevator" words → a real lift (doors open); 908: the words replaced by metal words → a plain steel slab, skin gone. The only
# picture sent was the grenade (Bom keo 1.png). Formula: the Kho keeps a picture of the object DEPLOYED (the wall standing, with its
# skin) — an asset picture whose label / variant / file name says "triển khai" / "deployed"; it goes as a reference picture with the
# line `deployed_line` ("Image N is the DEPLOYED …") and the skin words point at it. A shot where the object APPEARS (rises) without
# such a picture is a ĐỎ before sending (send_issues), with the code-composite route suggested.
_DEPLOYED = ("trien khai", "deployed")
_DEPLOYED_RX = re.compile(r"Image (\d+) is the DEPLOYED ")


def deployed_marker(text: str) -> Optional[int]:
    m = _DEPLOYED_RX.search(text or "")
    return int(m.group(1)) if m else None


def deployed_line(number: int, name: str) -> str:
    return (f"Image {number} is the DEPLOYED {name} as it stands once it has appeared: copy its shape, height and skin; the surface "
            f"pattern of Image {number} is printed decoration on one solid block.")


def deployed_images(asset: Dict) -> List[Dict]:
    """The asset's pictures of the object deployed (label / variant / file name says "triển khai" / "deployed", accents ignored)."""
    from . import assets
    out = []
    for img in asset.get("images") or []:
        words = " " + assets.fold(" ".join(str(img.get(k) or "") for k in ("label", "variant")) + " "
                                  + os.path.splitext(os.path.basename(str(img.get("path") or "")))[0].replace("_", " ")) + " "
        if any(" " + w + " " in words for w in _DEPLOYED):
            out.append(img)
    return out


def deployed_pictures(conn, project_id: Optional[int], rows: Sequence[Dict]) -> List[Tuple[str, str]]:
    """[(Kho name, path)] — one DEPLOYED picture per skill object the shots speak of (flag off / none: [])."""
    if not enabled():
        return []
    from . import prop_lock
    text = " ".join(prop_lock.shot_text(r.get("data") or {}) for r in rows)
    named, _ = _present_names(conn, project_id, text)
    out = []
    for a in skill_assets(conn, project_id):
        pics = deployed_images(a) if a["name"] in named else []
        if pics and os.path.exists(pics[0]["path"]):
            out.append((a["name"], pics[0]["path"]))
    return out


def skin_sentence(items: Sequence[Dict], text: str, removed: Sequence[str], shown: Optional[int]) -> str:
    """'' unless the text speaks of the object's SKIN (the word 'skin', or its picture variant) — then where the skin comes from."""
    from . import prop_lock
    variant = next((v for a in items for v in [prop_lock.chosen_variant(a, text)] if v), None)
    if not variant and not re.search(r"(?<!\w)skin(?!\w)", text or "", re.I):
        return ""
    # rà S2 13/10 mục 3: the common word, never the Kho name / variant ("Bom keo", "… thang máy" → Vietnamese, a lift again)
    if shown:
        out = f"The glue wall skin is the pattern shown in Image {shown}: printed on one solid block, never separate metal plates."
    else:
        out = "The glue wall skin is a printed surface pattern on one solid block, never separate metal plates."
    return sanitize(out)[0]


def send_issues(conn, project_id: Optional[int], data: Dict) -> List[Dict]:
    """VÀNG of a CLIP send (never a stop — rà S2 13/10 mục 1, người dùng 21:31: a glue throw is never ĐỎ for the wall): the skill
    object appears in the shot and the Kho has no DEPLOYED picture of it — the skin is said in words only (891 lift / 908 plain
    steel). Shown with the prompt formula's VÀNG (issues); prompt_formula._clip_send_reds keeps only 'red' → nothing held.
    [] when off / nothing found / the Kho has the picture."""
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
    items = [a for a in skill_assets(conn, project_id) if a["name"] in named]
    if not rises(data, _names_of(items)):
        return []
    missing = [a["name"] for a in items if not deployed_images(a)]   # no Kho object attached: issues() says VÀNG (compose), not here
    if not missing:
        return []
    return [{"level": "warn", "part": "dao_cu",
             "msg": f"{', '.join(missing)}: chưa có ảnh dạng triển khai, skin tả bằng chữ — model video có thể vẽ sai skin (891 thang "
                    "máy thật, 908 tấm thép trơn). Nên thêm vào Kho ảnh tường đã đứng (đúng skin, nhãn ảnh ghi 'triển khai')"}]


SKIN_ROOM = 140                     # V4: the skin sentence (skin_sentence) added after the ban sentence


def reserve(conn=None, project_id: Optional[int] = None, text: Optional[str] = None) -> int:
    """Characters the send may add after a model-limited prompt is built (the ban sentence + a longer name + the skin sentence);
    0 when off. Rà S2 13/10 mục 7: given the prompt's text, the skin sentence's room only when it speaks of a skill object (else the
    sizes sentence of every Seedance prompt was cut for nothing); no text → all of it (as before)."""
    if not enabled():
        return 0
    room = len(FORBID) + 40
    if text is None:
        return room + SKIN_ROOM
    named, generic = _present_names(conn, project_id, text)
    return room + (SKIN_ROOM if named or generic else 0)


def rises(data: Dict, names: Sequence[str] = ()) -> bool:
    """The shot shows the skill object APPEARING (thrown; old texts: popping / shooting up) — what a video model draws worst (#27
    shot 16). It appears at once (người dùng 13/10 21:31): the prompt says it standing (standing_text), the build is a hard cut."""
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
        "steps": ["gen video CHỈ phần người (ném / chạy), không tả quá trình vật kỹ năng xuất hiện",
                  "vẽ khung cuối có vật kỹ năng đứng sẵn đủ chiều cao (end_state)",
                  f"ghép: py {COMPOSE_TOOL} --clip <clip người> --end <khung cuối> --cut <giây vật chạm đất> --out <mp4> "
                  "(cắt cứng: tường xuất hiện luôn + rung)"],
        "tool": COMPOSE_TOOL,
        "scene_id": scene_id,
    }


def issues(conn, project_id: Optional[int], data: Dict) -> List[Dict]:
    """VÀNG (never a stop) for the prompt formula (part 'dao_cu'): misreading words written about a skill object (replaced at send),
    a shot where the skill object appears → suggest the code composite (it appears at once), and the Kho lacking its DEPLOYED
    picture (send_issues). [] when off / nothing found."""
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
                    "msg": f"shot có {who} xuất hiện (ném keo) — tường xuất hiện luôn, khung sau đã đứng sẵn đủ cao (khi gửi code thay "
                           "chữ tả quá trình bằng 'already standing at full height'); model video hay vẽ sai vật kỹ năng → gợi ý dựng "
                           f"bằng GHÉP code (cắt cứng sang khung cuối + rung, `{COMPOSE_TOOL}`) thay vì gen cả hiệu ứng"})
        out += send_issues(conn, project_id, data)
    return out


def director_note(asset: Dict) -> str:
    """The sentence after a skill object in the Director's Kho block ('' when off / not a skill object)."""
    from . import prop_lock
    if not enabled() or prop_lock.category(asset) not in SKILL_CATEGORIES:
        return ""
    return (" — VẬT KỸ NĂNG: khi viết prompt tả theo hình dạng/chất liệu (tấm kim loại phẳng, khung, đèn…), KHÔNG dùng chữ "
            "thang máy / cửa / elevator / door / lift (model vẽ thành thang máy thật, cửa mở, người đứng trong); dùng keo (ném) thì "
            "tường XUẤT HIỆN LUÔN — khung sau đã đứng sẵn đủ cao, không tả quá trình mọc / trồi (rise / grow / emerge / pop up)")


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


def composite_frames(clip_frames: List, end_img, cut_index: int, total: int, rise: int = 0, shake: int = 8, shake_px: int = 10,
                     top: Optional[int] = None) -> List:
    """Frames (numpy RGB) of the composite: the clip up to cut_index, then (rise = 0, mặc định từ 13/10 21:31: tường XUẤT HIỆN LUÔN)
    a hard cut to the end frame shaking `shake` frames (decaying), held to `total`. rise > 0 only rebuilds an old composite: the end
    frame's object part rising from the bottom over `rise` frames first. Pure function — tested without ffmpeg."""
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


def compose(clip: str, end_frame: str, out: str, cut_s: float, rise: int = 0, shake: int = 8, shake_px: int = 10,
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
