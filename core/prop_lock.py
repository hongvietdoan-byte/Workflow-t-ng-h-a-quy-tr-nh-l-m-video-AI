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


def locks(conn, project_id: int, data: Dict) -> List[Dict]:
    """The project props this shot is about: [{asset, category, named, variant, form, image}] — a prop the text names, or the ONE
    prop of a kind the text only says by its common word. [] when the flag is off."""
    if not enabled() or project_id is None:
        return []
    pool, words, text, generic = _scan(conn, project_id, data)
    out = []
    for cat in CATEGORIES:
        mine = [a for a, c in pool if c == cat]
        named = [a for a in mine if _named(a, words)]
        chosen = named or (mine if generic[cat] and len(mine) == 1 else [])
        for a in chosen:
            v = chosen_variant(a, text)
            pics = usable_images(a, text)
            out.append({"asset": a, "category": cat, "named": a in named, "variant": v, "form": form_text(a, v),
                        "has_forms": bool(_forms(a.get("description") or "") or _variants(a)), "image": pics[0] if pics else None})
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


def issues(conn, project_id: int, data: Dict) -> List[Dict]:
    """VÀNG (never a stop): the shot says a common word of a kind with several project props of that kind and names none — not
    guessed; a locked prop without any description in the Kho."""
    if not enabled() or project_id is None:
        return []
    pool, words, _text, generic = _scan(conn, project_id, data)
    out = []
    for cat in CATEGORIES:
        mine = [a for a, c in pool if c == cat]
        if generic[cat] and len(mine) > 1 and not any(_named(a, words) for a in mine):
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": f"chữ shot nói '{CATEGORIES[cat]['word']}' chung chung mà dự án gắn {len(mine)} món cùng loại ("
                               + ", ".join(a["name"] for a in mine) + ") — không đoán; ghi đích danh tên món trong prompt"})
    for lk in locks(conn, project_id, data):
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
        over = f"; this overrides any other colour or material described above for it" if form and lk["has_forms"] else ""
        if not lk["named"]:
            word = CATEGORIES[lk["category"]]["word"]
            bits.append(f"Prop lock: the {word} in this shot is {a['name']} from the project library"
                        + (f" — {form}" if form else "") + over
                        + (_DRAW_PIC if lk["image"] else _DRAW)
                        + f", never another {word}.")
        elif lk["has_forms"] and form:
            bits.append(f"Prop lock: {a['name']} in this shot — {form}{over}"
                        + ("; as its reference picture shows" if lk["image"] else "") + "; keep this one form.")
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
