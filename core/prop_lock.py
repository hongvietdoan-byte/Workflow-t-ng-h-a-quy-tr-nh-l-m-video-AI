"""Khóa đạo cụ dự án (cờ `project_prop_lock`, lỗi thật #27 12/10).

Kho gắn dự án có súng SKORP + Bom keo, nhưng Đạo diễn viết "assault rifle" / "glue wall" chung chung → model vẽ AK, tường keo mỗi shot
một kiểu, và khâu chọn ảnh tham chiếu (assets.scene_references, khớp TÊN trong chữ) không gửi ảnh Kho. Lớp này, cho mọi dự án:

- mỗi vũ khí / đạo cụ (kind weapon / prop) đã gắn dự án được xếp vào một LOẠI (súng, tường keo…) theo tên / tên khác / mô tả;
- chữ của shot (image_prompt, action, blocking, action_peak, text) có từ CHUNG của loại đó mà không có tên món Kho → câu "Prop lock"
  nêu đích danh món + mô tả (đọc từ assets.description) được chèn vào prompt ảnh và ảnh của món vào ảnh tham chiếu;
- dự án gắn NHIỀU món cùng loại và shot chỉ nói từ chung → KHÔNG đoán: cảnh báo VÀNG (formula_check, phần 'dao_cu');
- DẠNG (người dùng 12/10, Bom keo): mô tả có các đoạn "(a) MẶC ĐỊNH — …; (b) skin … — …"; ảnh Kho có `variant` (asset_images.variant)
  chỉ được gửi khi chữ shot nhắc variant đó ("Gloowall", "OB55"); không nhắc → dạng mặc định (đoạn có chữ "mặc định"/"default").

Cờ tắt → không đổi gì (prompt giống từng byte, ảnh tham chiếu như cũ). Không gọi API, 0 USD."""
import re
from typing import Dict, List, Optional

from . import assets

KINDS = ("weapon", "prop")

# loại → (từ để xếp món Kho, dạng bỏ dấu; từ chung trong chữ shot, giữ dấu — "kéo" (động từ) ≠ "keo"; tên gọi chung trong câu khóa)
CATEGORIES = {
    "glue": {"asset": ("keo", "glue", "gloo", "gloowall", "gloo wall", "tuong keo", "bom keo"),
             "shot": r"glue(?:[ -](?:walls?|grenades?|barriers?))?|gloo(?:[ -]walls?)?|gloowalls?|tường keo|bom keo|keo",
             "word": "glue wall"},
    "gun": {"asset": ("sung", "tieu lien", "sung truong", "rifle", "smg", "gun", "shotgun", "pistol", "sniper", "submachine gun"),
            "shot": r"assault rifles?|sniper rifles?|rifles?|sub-?machine ?guns?|machine ?guns?|smgs?|shotguns?|pistols?|handguns?|guns?|"
                    r"firearms?|weapons?|súng(?: trường| tiểu liên| ngắn)?|tiểu liên|vũ khí",
            "word": "gun"},
}
_SHOT_RX = {k: re.compile(r"(?<!\w)(?:" + v["shot"] + r")(?!\w)", re.I) for k, v in CATEGORIES.items()}
_TEXT_KEYS = ("image_prompt", "action", "blocking", "action_peak", "text")
_VARIANT_STOP = {"skin", "variant", "dang", "ban", "the", "and"}
_FORM = re.compile(r"\(([a-h])\)\s*(.+?)(?=\s*;\s*\([a-h]\)\s|\.\s|\.?\s*$)", re.S)
# rà 12/10: colour / material words the Director may give a locked prop ("translucent amber glue wall") against its library form
_COLOUR_RX = re.compile(r"(?<!\w)(?:amber|ice|icy|crystal(?:line)?|golden|gold|blue|red|green|purple|pink|orange|yellow|black|silver|"
                        r"glass|glassy|translucent|transparent|metal(?:lic)?|neon|glowing|hổ phách|băng|pha lê|trong suốt|kim loại|"
                        r"xanh(?: lam| dương| lá)?|đỏ|tím|hồng|cam|bạc)(?!\w)", re.I)
_DEFAULT_HEAD = re.compile(r"^\s*(?:mặc định|mac dinh|default)\s*[—:–-]*\s*", re.I)


def enabled() -> bool:
    try:
        from . import features
        return features.on("project_prop_lock")
    except Exception:  # noqa: BLE001 - unreadable settings: the old behaviour (off)
        return False


def shot_text(data: Dict) -> str:
    return " ".join(str((data or {}).get(k) or "") for k in _TEXT_KEYS)


def category(asset: Dict) -> Optional[str]:
    """The kind of thing a weapon / prop of the Kho is (glue checked first: "Bom keo" is a weapon too), else None."""
    if asset.get("kind") not in KINDS:
        return None
    for source in (" ".join(assets.names_of(asset)), str(asset.get("description") or "")[:160]):
        body = " " + assets.fold(source) + " "
        for cat, spec in CATEGORIES.items():
            if any(" " + w + " " in body for w in spec["asset"]):
                return cat
    return None


def _named(asset: Dict, words: List[str]) -> bool:
    return any(assets.name_spans(n, words) for n in assets.names_of(asset) if len(assets.fold(n)) >= 2)


def _variant_tokens(variant: str) -> List[str]:
    return [t for t in assets.fold(variant).split() if len(t) >= 3 and t not in _VARIANT_STOP]


def _variants(asset: Dict) -> List[str]:
    return list(dict.fromkeys(str(i.get("variant")).strip() for i in asset.get("images") or [] if str(i.get("variant") or "").strip()))


def _name_tokens(asset: Dict) -> set:
    return {t for n in assets.names_of(asset) for t in assets.fold(n).split()}


def _says_variant(asset: Dict, variant: str, said: List[str]) -> bool:
    """Rà 12/10: one shared token is not enough — "Gloowall" is the prop's own alias, "OB55" the event's name. The shot must say
    the variant's whole phrase ("Gloowall OB55") or "skin" right next to one of its words ("skin Gloowall", "OB55 skin")."""
    toks = _variant_tokens(variant)
    own = [t for t in toks if t not in _name_tokens(asset)]
    if not toks:
        return False
    n = len(toks)
    if own and any(said[i:i + n] == toks for i in range(len(said) - n + 1)):
        return True
    return any(w == "skin" and any(t in said[max(i - 2, 0):i] + said[i + 1:i + 3] for t in toks) for i, w in enumerate(said))


def chosen_variant(asset: Dict, text: str) -> Optional[str]:
    """The picture variant of this asset the shot names ("skin Gloowall OB55" ← "Gloowall OB55" / "skin Gloowall"), else None
    (the default form)."""
    said = assets.fold(text).split()
    return next((v for v in _variants(asset) if _says_variant(asset, v, said)), None)


def usable_images(asset: Dict, text: str) -> List[Dict]:
    """Only the pictures of the form the shot speaks of: a picture with a `variant` goes only when the text names that variant;
    otherwise only the plain pictures (none → no picture: the form is said in words)."""
    v = chosen_variant(asset, text)
    imgs = asset.get("images") or []
    if v is not None:
        return [i for i in imgs if str(i.get("variant") or "").strip() == v]
    return [i for i in imgs if not str(i.get("variant") or "").strip()]


def _forms(desc: str) -> List[str]:
    return [m.group(2).strip().rstrip(";,. ") for m in _FORM.finditer(desc or "")]


def _plain(desc: str) -> str:
    """The description without its source tags ("[ff.garena.com] …" and what follows a later tag), at most two sentences."""
    text = re.sub(r"^\s*\[[^\]]*\]\s*", "", desc or "")
    text = text.split("[", 1)[0].strip()
    sents = re.split(r"(?<=[.!?])\s+", text)
    out = " ".join(sents[:2]).strip()
    return out[:280].rstrip().rstrip(" .")         # rà 12/10: the sentence goes on after it (no ".;")


def form_text(asset: Dict, variant: Optional[str]) -> str:
    """The words of the form to draw: the description's "(x)" part of the named variant, else its "mặc định" part, else the plain
    description. '' when the Kho has no description (said by issues())."""
    desc = str(asset.get("description") or "")
    forms = _forms(desc)
    if forms:
        if variant:
            toks = _variant_tokens(variant)
            hit = next((f for f in forms if any(t in assets.fold(f).split() for t in toks)), None)
            return (hit or variant).strip()
        default = next((f for f in forms if re.search(r"\bmac dinh\b|\bdefault\b", assets.fold(f))), forms[0])
        return _DEFAULT_HEAD.sub("", default).strip()
    return _plain(desc)


def _scan(conn, project_id: int, data: Dict):
    """[(asset, category)] of the project, the shot's words, its text, and per category: generic word said?"""
    text = shot_text(data)
    words = assets._said_words(text)
    pool = [(a, category(a)) for a in assets.project_assets(conn, project_id)]
    pool = [(a, c) for a, c in pool if c]
    generic = {c: bool(_SHOT_RX[c].search(text)) for c in CATEGORIES}
    return pool, words, text, generic


# ---- Đ16 việc 3 (người dùng 12/10 13:19, #27): KHÓA SÚNG THEO NHÂN VẬT — "khóa sẵn nhiều súng, tránh tự ý dùng và gán sai" ----------
# characters.weapon_asset_id = the Kho weapon locked to a character in this video (like outfit_image_ids). With it, a shot that speaks
# of guns gets each present character's OWN gun by name (several guns in one project no longer end in a mere YELLOW).
_SLUNG = re.compile(r"(?<!\w)(?:slung|on (?:his|her|their) back|across (?:his|her|their) back|on the back|đeo (?:chéo )?(?:sau )?lưng|sau lưng)"
                    r"(?!\w)", re.I)


def set_weapon(conn, project_id: int, name: str, asset_id: Optional[int]) -> None:
    """Lock a Kho weapon to a character of the project (None = no gun locked)."""
    conn.execute("UPDATE characters SET weapon_asset_id=? WHERE project_id=? AND name=?",
                 (int(asset_id) if asset_id else None, project_id, name))
    conn.commit()


def weapon_table(conn, project_id: int) -> Dict[str, int]:
    """{character name: Kho weapon id} of the project (only characters with a gun locked)."""
    try:
        rows = conn.execute("SELECT name, weapon_asset_id FROM characters WHERE project_id=? AND weapon_asset_id IS NOT NULL",
                            (project_id,)).fetchall()
    except Exception:  # noqa: BLE001 - a database before the column: nothing locked
        return {}
    return {r["name"]: int(r["weapon_asset_id"]) for r in rows}


def _holders(conn, project_id: int, data: Dict, pool) -> Dict[int, List[str]]:
    """{gun asset id: [present characters it is locked to]} — only guns attached to the project (in `pool`)."""
    guns = {a["id"] for a, c in pool if c == "gun"}
    table = {assets.fold(n): (n, i) for n, i in weapon_table(conn, project_id).items()}
    out: Dict[int, List[str]] = {}
    for name in (data or {}).get("characters") or []:
        hit = table.get(assets.fold(str(name)))
        if hit and hit[1] in guns:
            out.setdefault(hit[1], []).append(hit[0])
    return out


def _unlocked_people(conn, project_id: int, data: Dict) -> List[str]:
    """Present characters with no gun locked, in a project that locks guns to characters."""
    table = {assets.fold(n) for n in weapon_table(conn, project_id)}
    if not table:
        return []
    return [str(n) for n in (data or {}).get("characters") or [] if assets.fold(str(n)) not in table]


def locks(conn, project_id: int, data: Dict) -> List[Dict]:
    """The project props this shot is about: [{asset, category, named, variant, form, image}] — a prop the text names, or the ONE
    prop of a kind the text only says by its common word. [] when the flag is off."""
    if not enabled() or project_id is None:
        return []
    pool, words, text, generic = _scan(conn, project_id, data)
    holders = _holders(conn, project_id, data, pool)
    out = []
    for cat in CATEGORIES:
        mine = [a for a, c in pool if c == cat]
        named = [a for a in mine if _named(a, words)]
        chosen = named or (mine if generic[cat] and len(mine) == 1 else [])
        if cat == "gun" and holders and (generic[cat] or named):
            # Đ16v3: the guns locked to the characters in this shot, each by name (plus a gun the text names itself)
            chosen = list({a["id"]: a for a in [a for a in mine if a["id"] in holders] + named}.values())
        for a in chosen:
            v = chosen_variant(a, text)
            pics = usable_images(a, text)
            out.append({"asset": a, "category": cat, "named": a in named, "variant": v, "form": form_text(a, v),
                        "has_forms": bool(_forms(a.get("description") or "") or _variants(a)), "image": pics[0] if pics else None,
                        "holders": holders.get(a["id"], []) if cat == "gun" else []})
    return out


def _colour_words(asset: Dict, category_: str, text: str) -> List[str]:
    """Colour / material words written next to (≤ 50 characters before, ≤ 30 after) the prop's common word or its name."""
    spans = [m.span() for m in _SHOT_RX[category_].finditer(text)]
    for n in assets.names_of(asset):
        if len(assets.fold(n)) >= 3:
            spans += [m.span() for m in re.finditer(r"(?<!\w)" + re.escape(n.strip()) + r"(?!\w)", text, re.I)]
    out = []
    for a, b in spans:
        out += [m.group(0).lower() for m in _COLOUR_RX.finditer(text[max(a - 50, 0):b + 30])]
    return list(dict.fromkeys(out))


# Heuristic đã được người dùng chốt Đ16v2: không phải số đo, không tự gán mét.
_WEAPON_TYPES = {
    "SMG": r"smgs?|sub[- ]?machine guns?|súng tiểu liên|tiểu liên",
    "rifle": r"(?:assault |sniper )?rifles?|súng trường|súng bắn tỉa",
    "pistol": r"pistols?|handguns?|súng lục|súng ngắn",
    "shotgun": r"shotguns?|súng săn",
}
_SCALE_LABEL = re.compile(r"(?<!\w)(?:scale|relative size|tỉ lệ|tỷ lệ|kích thước so người)\s*:\s*((?:[^.;\n]|(?<=\d)\.(?=\d))+)", re.I)
_TYPE_SCALE = {
    "SMG": "compact shoulder weapon, approximately forearm-to-shoulder length, not pistol-sized",
    "rifle": "long shoulder weapon, larger than a forearm",
    "pistol": "short hand-held weapon, smaller than a forearm; keep handgun proportions",
    "shotgun": "long shoulder weapon, larger than a forearm",
}


def weapon_scale(conn, asset: Dict, variant: Optional[str] = None) -> str:
    """Tỉ lệ hồ sơ/mô tả/số đo thắng ước lượng theo loại; loại mâu thuẫn không đoán.

    Dùng trường hồ sơ hiện có (must_keep/identity/build), nhãn 'Tỉ lệ:' trong mô tả,
    hoặc kích thước Kho. Không migration, không sửa hồ sơ và không API.
    """
    profile = assets.get_profile(conn, asset["id"])
    if not isinstance(profile, dict):
        profile = {}
    desc = form_text(asset, variant) if _forms(asset.get("description") or "") else re.sub(r"^\s*\[[^\]]*\]\s*", "", str(asset.get("description") or "")).split("[", 1)[0]
    for source in [str(profile.get(k) or "") for k in ("must_keep", "identity", "build")] + [desc]:
        m = _SCALE_LABEL.search(source)
        if m:
            return m.group(1).strip()
    size = asset.get("size") or {}
    if size:
        return "Library measured dimensions: " + ", ".join(f"{k.removesuffix('_m')} {float(size[k]):g} m" for k in ("height_m", "width_m") if k in size)
    body = " ".join([str(profile.get(k) or "") for k in ("identity", "must_keep", "build")]
                    + assets.names_of(asset) + [desc])
    kinds = set()
    for kind, pattern in _WEAPON_TYPES.items():
        for m in re.finditer(r"(?<!\w)(?:" + pattern + r")(?!\w)", body, re.I):
            if not re.search(r"(?:not|never|không(?: phải| là)?)\s+(?:an?\s+)?$", body[max(0, m.start() - 35):m.start()], re.I):
                kinds.add(kind)
    if len(kinds) != 1:
        return ""
    kind = next(iter(kinds))
    return f"Estimated {kind} proportions (not measured): {_TYPE_SCALE[kind]}"


# Cụm thuộc tính song ngữ; dùng riêng cho vệ sinh, giữ contract cảnh báo cũ.
_ATTRIBUTE_GROUPS = (
    ("black", "đen"), ("white", "trắng"), ("opaque", "đục"), ("grey", "gray", "xám"),
    ("brown", "nâu"), ("amber", "hổ phách"), ("red", "đỏ"), ("yellow", "vàng"),
    ("blue", "xanh lam", "xanh dương"), ("green", "xanh lá"), ("purple", "tím"),
    ("pink", "hồng"), ("orange", "cam"), ("silver", "bạc"), ("gold", "golden"),
    ("translucent", "transparent", "trong suốt"), ("metal", "metallic", "kim loại"),
    ("glass", "glassy"), ("ice", "icy", "băng"), ("crystal", "crystalline", "pha lê"),
    ("neon",), ("glowing",), ("xanh",),
)
_ATTRIBUTE_KEY = {word: i for i, group in enumerate(_ATTRIBUTE_GROUPS) for word in group}
_ATTRIBUTE_RX = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in sorted(_ATTRIBUTE_KEY, key=len, reverse=True)) + r")(?!\w)", re.I)
_OTHER_NOUN_HEAD = re.compile(r"(?:[- ](?:shaped|like)\b|\s+(?:toy|case|rack|bottle|lamp|light)\b)", re.I)


def _form_attributes(form: str):
    # Một màu được nêu trong mệnh đề phủ định không phải thuộc tính chuẩn.
    return {_ATTRIBUTE_KEY[m.group().lower()] for m in _ATTRIBUTE_RX.finditer(form)
            if not re.search(r"(?:not|no|never|không)\s+$", form[:m.start()], re.I)}


def clean_prompt(conn, project_id: int, data: Dict, text: str):
    """Bỏ màu/chất liệu mâu thuẫn CHỈ trong cụm tính từ sát trước món mặc định.

    Không dùng cửa sổ ký tự (dễ xóa màu vật cạnh bên), không sửa dữ liệu nguồn.
    Nhiều món cùng loại: chỉ khớp tên riêng, không đoán từ chung. Skin giữ nguyên.
    Trả (chữ gửi, các cụm đã bỏ) để Dashboard hiện cùng thay đổi thật.
    """
    if not enabled() or not text:
        return text, []
    pool, _, _, _ = _scan(conn, project_id, data)
    cuts = []
    prefix = re.compile(r"(?:" + _ATTRIBUTE_RX.pattern + r")(?:[ -]+(?:" + _ATTRIBUTE_RX.pattern + r"))*[ -]+$", re.I)
    suffix = re.compile(r"\s+(?:is|made of|of|là|bằng)\s+((?:" + _ATTRIBUTE_RX.pattern
                        + r")(?:[ -]+(?:" + _ATTRIBUTE_RX.pattern + r"))*)(?=\s*(?:[.;,!?]|$))", re.I)
    for lk in locks(conn, project_id, data):
        if lk["variant"] is not None or not lk["form"]:
            continue
        a, cat = lk["asset"], lk["category"]
        kept = _form_attributes(lk["form"])
        spans = []
        if sum(c == cat for _, c in pool) == 1:
            spans += [m.span() for m in _SHOT_RX[cat].finditer(text)]
        for name in assets.names_of(a):
            if len(assets.fold(name)) >= 3:
                spans += [m.span() for m in re.finditer(r"(?<!\w)" + re.escape(name.strip()) + r"(?!\w)", text, re.I)]
        for start, end in spans:
            if _OTHER_NOUN_HEAD.match(text[end:]):
                continue
            if cat == "glue":
                wall = re.match(r"[ -]walls?\b", text[end:], re.I)
                if wall:
                    end += wall.end()
            after = suffix.match(text, end)
            if after:
                descriptors = list(_ATTRIBUTE_RX.finditer(after.group(1)))
                conflicts = [m for m in descriptors if _ATTRIBUTE_KEY[m.group().lower()] not in kept]
                if conflicts and len(conflicts) == len(descriptors):
                    cuts.append((after.start(), after.end()))
                else:
                    for colour in conflicts:
                        left, right = after.start(1) + colour.start(), after.start(1) + colour.end()
                        while right < after.end(1) and text[right] in " -":
                            right += 1
                        if right == after.end(1):
                            while left > after.start(1) and text[left - 1] in " -":
                                left -= 1
                        cuts.append((left, right))
            m = prefix.search(text[:start])
            if not m:
                continue
            for colour in _ATTRIBUTE_RX.finditer(m.group(0)):
                if _ATTRIBUTE_KEY[colour.group().lower()] in kept:
                    continue
                left, right = m.start() + colour.start(), m.start() + colour.end()
                while right < start and text[right] in " -":
                    right += 1
                cuts.append((left, right))
    # Hợp nhất khoảng chồng nhau khi alias và từ chung cùng khớp một món.
    merged = []
    for left, right in sorted(set(cuts)):
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(right, merged[-1][1]))
        else:
            merged.append((left, right))
    removed = [text[left:right].strip(" -") for left, right in merged]
    for left, right in reversed(merged):
        text = text[:left] + text[right:]
    return text, removed


def issues(conn, project_id: int, data: Dict) -> List[Dict]:
    """VÀNG (never a stop): the shot says a common word of a kind with several project props of that kind and names none — not
    guessed; a locked prop without any description in the Kho."""
    if not enabled() or project_id is None:
        return []
    pool, words, _text, generic = _scan(conn, project_id, data)
    holders = _holders(conn, project_id, data, pool)
    out = []
    guns = [a for a, c in pool if c == "gun"]
    if holders and (generic["gun"] or any(_named(a, words) for a in guns)):
        # Đ16v3: a gun the text names that is locked to nobody in this shot → ĐỎ before a paid picture
        owners = {i: names for i, names in holders.items()}
        for a in guns:
            if _named(a, words) and a["id"] not in owners:
                locked = "; ".join(f"{', '.join(n)} → {next((g['name'] for g in guns if g['id'] == i), i)}" for i, n in owners.items())
                out.append({"level": "red", "part": "dao_cu",
                            "msg": f"chữ shot nêu súng {a['name']} nhưng không nhân vật nào trong shot được khóa súng này (đã khóa: {locked}) "
                                   "— sửa chữ shot theo súng đã khóa, hoặc đổi bảng gán súng ở Bước 1"})
        nobody = _unlocked_people(conn, project_id, data)
        if nobody:
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": "shot có súng nhưng nhân vật " + ", ".join(nobody) + " chưa được gán súng — không đoán; gán ở Bước 1 nếu họ cầm súng"})
    for cat in CATEGORIES:
        mine = [a for a, c in pool if c == cat]
        if cat == "gun" and holders:
            continue                                   # Đ16v3: the characters' own guns are locked by name — not a guess
        if generic[cat] and len(mine) > 1 and not any(_named(a, words) for a in mine):
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": f"chữ shot nói '{CATEGORIES[cat]['word']}' chung chung mà dự án gắn {len(mine)} món cùng loại ("
                               + ", ".join(a["name"] for a in mine) + ") — không đoán; ghi đích danh tên món trong prompt"})
    for lk in locks(conn, project_id, data):
        if lk["category"] == "gun" and not weapon_scale(conn, lk["asset"], lk["variant"]):
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": f"món Kho {lk['asset']['name']} thiếu tỉ lệ — loại súng chưa rõ hoặc mâu thuẫn; thêm 'Tỉ lệ:' vào mô tả/hồ sơ hoặc kích thước ở Kho"})
        if not lk["form"]:
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": f"món Kho {lk['asset']['name']} chưa có mô tả — prompt chỉ nêu được tên; thêm mô tả ở Kho"})
        elif lk["has_forms"] and lk["variant"] is None:
            said = _colour_words(lk["asset"], lk["category"], _text)
            if said:
                out.append({"level": "warn", "part": "dao_cu",
                            "msg": f"chữ shot tả {lk['asset']['name']} bằng màu/chất liệu khác ({', '.join(said)}) mà món khóa ở dạng "
                                   f"mặc định ({lk['form'][:60]}) — câu khóa đè lên, nên sửa chữ shot cho khỏi mâu thuẫn"})
    return out


def prompt_part(conn, project_id: int, data: Dict) -> str:
    """The 'Prop lock' sentences of the picture prompt ('' when off / nothing to lock — the prompt then stays byte for byte)."""
    if not enabled():
        return ""
    bits = []
    for lk in locks(conn, project_id, data):
        a, form = lk["asset"], lk["form"]
        if lk["category"] == "gun":
            # Nhãn tỉ lệ chỉ xuất hiện ở câu chuẩn ưu tiên, tránh 2 nguồn trái nhau.
            form = re.sub(r"\.\s*\.", ".", _SCALE_LABEL.sub("", re.sub(r"(?i)(?<!\w)in-game\s+(?=scale\s*:)", "", form))).strip(" .;")   # Đ16v3: "In-game scale: …" whole
        over = f"; this overrides any other colour or material described above for it" if form and lk["has_forms"] else ""
        if lk.get("holders"):
            # Đ16v3: whose gun it is — each present character gets their own locked gun, never another one
            who = " and ".join(lk["holders"])
            slung = (f"; when it is slung on the back it is this same gun at its true size, worn across the back, not in the hands"
                     if _SLUNG.search(shot_text(data)) else "")
            bits.append(f"Prop lock: the gun of {who} in this shot is {a['name']} from the project library"
                        + (f" — {form}" if form else "") + over + slung
                        + (_DRAW_PIC if lk["image"] else _DRAW)
                        + f", never another gun (only if {who} {'holds' if len(lk['holders']) == 1 else 'hold'} or {'carries' if len(lk['holders']) == 1 else 'carry'} a gun)." )
        elif not lk["named"]:
            word = CATEGORIES[lk["category"]]["word"]
            bits.append(f"Prop lock: the {word} in this shot is {a['name']} from the project library"
                        + (f" — {form}" if form else "") + over
                        + (_DRAW_PIC if lk["image"] else _DRAW)
                        + f", never another {word}.")
        elif lk["has_forms"] and form:
            bits.append(f"Prop lock: {a['name']} in this shot — {form}{over}"
                        + ("; as its reference picture shows" if lk["image"] else "") + "; keep this one form.")
        if lk["category"] == "gun":
            scale = weapon_scale(conn, a, lk["variant"])
            if scale:
                bits.append(f"Weapon scale: {a['name']} — {scale}.")
    return " ".join(bits)


_DRAW = "; draw exactly this one"
_DRAW_PIC = _DRAW + " as its reference picture shows"


def match_refs(prompt: str, refs) -> str:
    """Rà 12/10: the 'Prop lock' sentence of a prop whose picture did NOT make it into the pictures really sent (slots full, dropped
    on the way) no longer says "as its reference picture shows" — the prop is then drawn from the words. Unchanged when no lock."""
    if "Prop lock:" not in (prompt or ""):
        return prompt
    sent = {str(r.get("label") or "") for r in refs or []}

    def fix(m):
        name = m.group("name")
        return m.group(0) if name in sent else m.group(0).replace(" as its reference picture shows", "")
    rx = re.compile(r"Prop lock: (?:the [^.;]*? in this shot is (?P<name>.+?) from the project library|(?P<name2>.+?) in this shot —)"
                    r".*?as its reference picture shows")
    return rx.sub(lambda m: fix(_Named(m)), prompt).replace(";;", ";")


class _Named:
    """A match whose 'name' group is whichever of the two sentence shapes matched."""
    def __init__(self, m):
        self._m = m

    def group(self, key=0):
        if key == "name":
            return self._m.group("name") or self._m.group("name2")
        return self._m.group(key)


def reference_images(conn, project_id: int, data: Dict) -> List[Dict]:
    """[{asset, image}] the shot's locked props send as references (named or by their common word, the right form)."""
    return [{"asset": lk["asset"], "image": lk["image"]} for lk in locks(conn, project_id, data) if lk["image"] is not None]
