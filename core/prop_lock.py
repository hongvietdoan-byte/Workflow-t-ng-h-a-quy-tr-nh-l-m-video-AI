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
    """The shot's own words — without its dialogue / narration lines (12/10, #27 shot 14: the narrator saying "…ném bom keo…" put a
    glue wall lock into the picking-up picture; core/assets._without_spoken_lines)."""
    data = data or {}
    return " ".join(assets._without_spoken_lines(str(data.get(k) or "")) if k == "text" else str(data.get(k) or "") for k in _TEXT_KEYS)


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
    hits = [v for v in _variants(asset) if _says_variant(asset, v, said)]
    if len(hits) > 1:      # rà 14/10: "skin Gloowall OB56" also fits "skin Gloowall OB55" by the 'skin + a shared word' rule — the
        full = [v for v in hits if _says_full(asset, v, said)]   # variant whose whole phrase is said wins (not the first in the Kho)
        hits = full or hits
    return hits[0] if hits else None


def _says_full(asset: Dict, variant: str, said: List[str]) -> bool:
    toks = _variant_tokens(variant)
    own = [t for t in toks if t not in _name_tokens(asset)]
    return bool(own) and any(said[i:i + len(toks)] == toks for i in range(len(said) - len(toks) + 1))


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def scene_text(conn, project_id: Optional[int], data: Dict) -> str:
    """Câu kịch bản của CẢNH chứa shot (story_scenes.text theo `story_scene` của shot) — '' khi không biết cảnh / không có bảng."""
    n = (data or {}).get("story_scene")
    if conn is None or project_id is None or n is None:
        return ""
    try:
        row = conn.execute("SELECT text FROM story_scenes WHERE project_id=? AND idx=?", (project_id, int(n))).fetchone()
    except Exception:  # noqa: BLE001 - CSDL cũ không có bảng / story_scene lạ: không có câu cảnh (không đoán)
        return ""
    return str((row["text"] if row else "") or "")


def _mentions(asset: Dict, sentence: str) -> bool:
    """Câu nhắc món này: tên / tên khác của món, hoặc từ chung của loại món (giữ dấu: 'kéo' ≠ 'keo')."""
    cat = category(asset)
    return bool((cat and _SHOT_RX[cat].search(sentence)) or _named(asset, assets._said_words(sentence)))


def scene_variants(conn, project_id: Optional[int], data: Dict, asset: Dict) -> List[str]:
    """Các dạng (variant ảnh Kho) của món mà câu kịch bản CẢNH nói, chỉ xét câu có nhắc món ("tường keo (skin thang máy)") —
    gốc lỗi #30 14/10: kịch bản cảnh ghi dạng, Đạo diễn chia shot bỏ mất chữ, shot rơi về dạng mặc định. Bỏ lời thoại."""
    if not _variants(asset):
        return []
    text = assets._without_spoken_lines(scene_text(conn, project_id, data))
    found = [chosen_variant(asset, s) for s in _SENT_SPLIT.split(text) if s.strip() and _mentions(asset, s)]
    return list(dict.fromkeys(v for v in found if v))


def variant_source(conn, project_id: Optional[int], data: Dict, asset: Dict, text: str):
    """(dạng, nguồn) — MỘT nguồn sự thật cho dạng món của shot: chữ shot nói dạng → (dạng, 'shot'); không nói → dạng câu kịch bản cảnh
    nói (đúng MỘT dạng) → (dạng, 'scene'); cảnh nói nhiều dạng khác nhau → (None, 'ambiguous'), không đoán; không gì → (None, None)."""
    v = chosen_variant(asset, text)
    if v is not None:
        return v, "shot"
    found = scene_variants(conn, project_id, data, asset)
    if len(found) == 1:
        return found[0], "scene"
    return None, ("ambiguous" if found else None)


def usable_images(asset: Dict, text: str, variant: Optional[str] = "", keep_mannequin: bool = False) -> List[Dict]:
    """Only the pictures of the form the shot speaks of: a picture with a `variant` goes only when the text names that variant;
    otherwise only the plain pictures (none → no picture: the form is said in words). `variant` given (variant_source — the scene's
    form carried down) wins over reading `text`; "" = read the text as before.
    14/10 #30: a Kho picture with a size-guide MANNEQUIN (#367 3.png, sort −1 — it came first) is never the object's picture: it went
    to shot 1 (only running, no wall) as "the object Bom keo: draw it exactly like this" + the mannequin sentence. It goes only as the
    DEPLOYED picture of a shot where the object appears (skill_objects.deployed_pictures reads the Kho pictures itself)."""
    from .skill_objects import is_mannequin_image
    v = chosen_variant(asset, text) if variant == "" else variant
    imgs = [i for i in asset.get("images") or [] if keep_mannequin or not is_mannequin_image(i)]
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
    for name in _present(conn, project_id, data):
        hit = table.get(assets.fold(str(name)))
        if hit and hit[1] in guns and hit[0] not in out.get(hit[1], []):
            out.setdefault(hit[1], []).append(hit[0])
    return out


def _present(conn, project_id: int, data: Dict) -> List[str]:
    """Rà Đ16v3 (12/10): the shot's characters + any character with a locked gun the shot's TEXT names ("Xúc Tu Đỏ fires the RPK"
    with characters=['KELLY'] — that character is in the shot too)."""
    names = [str(n) for n in (data or {}).get("characters") or []]
    said = " " + assets.fold(shot_text(data)) + " "
    have = {assets.fold(n) for n in names}
    for n in weapon_table(conn, project_id):
        if assets.fold(n) not in have and " " + assets.fold(n) + " " in said:
            names.append(n)
    return names


# a gun action in the same sentence as the gun's name (only then a mismatch is RED; a gun lying around, said in dialogue, or a word
# that is also a gun's name — "a hawk circles", "a scorpion crawls" — is YELLOW: the shot's own guns are locked by name anyway)
_GUN_ACTION = re.compile(r"(?<!\w)(?:fir(?:e|es|ed|ing)|shoot(?:s|ing)?|shot|aim(?:s|ed|ing)?|hold(?:s|ing)?|held|carr(?:y|ies|ying|ied)|"
                         r"wield(?:s|ing)?|grip(?:s|ping)?|reload(?:s|ing)?|points?|pointing|cầm|bắn|ngắm|giương|chĩa|nạp đạn|xả đạn)(?!\w)", re.I)


def _gun_sentences(text: str, asset: Dict) -> List[str]:
    """Sentences that name this gun AS a gun: its name written as in the Kho (case kept — "HAWK"/"RPK", not "a hawk"), or any
    spelling right next to a gun word."""
    out = []
    for sent in re.split(r"(?<=[.!?;])\s+|\n", text or ""):
        for n in assets.names_of(asset):
            n = n.strip()
            if len(assets.fold(n)) < 2:
                continue
            exact = re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", sent)
            loose = re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", sent, re.I)
            if exact and (n.isupper() or not n.isalpha() or n != n.lower()) or loose and _SHOT_RX["gun"].search(
                    sent[max(loose.start() - 25, 0):loose.end() + 25]):
                out.append(sent)
                break
    return out


def _unlocked_people(conn, project_id: int, data: Dict) -> List[str]:
    """Present characters with no gun locked, in a project that locks guns to characters."""
    table = {assets.fold(n) for n in weapon_table(conn, project_id)}
    if not table:
        return []
    return [str(n) for n in _present(conn, project_id, data) if assets.fold(str(n)) not in table]


_POV = re.compile(r"(?<!\w)(?:POV|first[- ]person(?: view)?|góc nhìn (?:thứ nhất|người thứ nhất))(?!\w)", re.I)
_OTS = re.compile(r"(?<!\w)(?:ots|over[- ]the[- ]shoulder|qua vai|third[- ]person|GAME_TPS)(?!\w)", re.I)


_NOT_THIS_CAMERA_BEFORE = re.compile(r"(?:\w+['’]s|\b(?:enemy|enemies|his|her|their|someone|another|other))\s+$", re.I)
_NOT_THIS_CAMERA_AFTER = re.compile(r"^[\s-]*(?:feed|footage|screen|monitor|display|video|shooter|style|game|cam\b)", re.I)


def _affirmative_angle(pattern, source: str, camera: bool = False) -> bool:
    """Dùng cùng nghĩa phủ định cho cả góc thứ nhất và góc qua vai/TPS. camera=True (chữ tự do, rà 12/10): bỏ "Maxim's POV" / "enemy
    POV" (góc của người khác — người cầm súng vẫn hiện trong khung), "first-person shooter", "POV feed" trên màn hình."""
    for clause in re.split(r"[.;,\n]", source):
        for m in pattern.finditer(clause):
            if re.search(r"(?:\b(?:no|not|never|without|avoid|remove)\b|không|tránh|bỏ)(?:\s+\w+){0,4}\s*$",
                         clause[:m.start()], re.I):
                continue
            if camera and (_NOT_THIS_CAMERA_BEFORE.search(clause[:m.start()]) or _NOT_THIS_CAMERA_AFTER.search(clause[m.end():])):
                continue
            return True
    return False


def is_pov(data: Dict) -> bool:
    """Góc thứ nhất rõ; không lấy câu thoại, phủ định hoặc góc qua vai/TPS. Rà 12/10: trường góc máy (angle / camera_angle / camera)
    đã ghi góc khác (eye / low / high…) thì nó thắng chữ tự do."""
    data = data or {}
    fields = {}
    for k in ("angle", "camera_angle", "camera", "shot", "size"):
        v = data.get(k)
        fields[k] = " ".join(str(x) for x in v.values()) if isinstance(v, dict) else str(v or "")
    explicit = " ".join(fields.values())
    if _affirmative_angle(_OTS, explicit):
        return False
    angle = " ".join(fields[k] for k in ("angle", "camera_angle", "camera")).strip()
    if angle:
        return _affirmative_angle(_POV, angle)
    for source in (fields["shot"], fields["size"], shot_text(data)):
        for clause in re.split(r"[.;\n]", source):
            if _affirmative_angle(_OTS, clause):
                continue
            if _affirmative_angle(_POV, clause, camera=True):
                return True
    return False


def pov_gun_issue(conn, project_id: int, data: Dict) -> Optional[Dict]:
    if not enabled() or not is_pov(data):
        return None
    pool, words, text, generic = _scan(conn, project_id, data)
    if generic["gun"] or any(c == "gun" and _named(a, words) for a, c in pool):
        return {"level": "warn", "part": "dao_cu", "msg": "POV có súng: Free Fire không có góc nhìn thứ nhất khi cầm súng — kiểm lại góc quay; vẫn cho gen, không thêm câu/ảnh súng khóa"}
    return None


def suppress_pov_gun_refs(conn, project_id: int, data: Dict, refs):
    """Bộ storyboard có thể chứa súng của shot khác; chỉ bỏ ảnh đạo cụ súng, giữ ảnh người."""
    if not enabled() or not is_pov(data):
        return refs
    gun_names = {a["name"] for a in assets.project_assets(conn, project_id) if category(a) == "gun"}
    return [r for r in refs if not (r.get("role") == "object" and r.get("label") in gun_names)]


def prioritize_gun_refs(conn, project_id: int, data: Dict, refs, sendable):
    """Cùng số slot: ảnh súng khóa hợp lệ chỉ thay nền rộng, không lấy slot nguồn khác."""
    if not enabled() or is_pov(data):
        return refs
    import os
    def key(path):
        return os.path.normcase(os.path.abspath(assets.resolve(path)))
    out = list(refs)
    sent = {key(r["path"]) for r in out if r.get("path")}
    for lk in locks(conn, project_id, data):
        if lk["category"] != "gun" or not lk["image"]:
            continue
        path = lk["image"]["path"]
        if key(path) in sent:
            continue
        at = next((i for i, r in enumerate(out) if r.get("role") == "place_wide"), None)
        if at is None:
            break
        ref = {"path": path, "label": lk["asset"]["name"], "role": "object"}
        if sendable(ref):
            out[at] = ref
            sent.add(key(path))
    return out


def locks(conn, project_id: int, data: Dict) -> List[Dict]:
    """The project props this shot is about: [{asset, category, named, variant, form, image}] — a prop the text names, or the ONE
    prop of a kind the text only says by its common word. [] when the flag is off."""
    if not enabled() or project_id is None:
        return []
    pool, words, text, generic = _scan(conn, project_id, data)
    holders = _holders(conn, project_id, data, pool)
    out = []
    for cat in CATEGORIES:
        if cat == "gun" and is_pov(data):
            continue
        mine = [a for a, c in pool if c == cat]
        named = [a for a in mine if _named(a, words)]
        chosen = named or (mine if generic[cat] and len(mine) == 1 else [])
        if cat == "gun" and holders and (generic[cat] or named):
            # Đ16v3: the guns locked to the characters in this shot, each by name (plus a gun the text names itself)
            chosen = list({a["id"]: a for a in [a for a in mine if a["id"] in holders] + named}.values())
        for a in chosen:
            v, source = variant_source(conn, project_id, data, a, text)
            pics = usable_images(a, text, variant=v)
            out.append({"asset": a, "category": cat, "named": a in named, "variant": v, "variant_from": source, "form": form_text(a, v),
                        "has_forms": bool(_forms(a.get("description") or "") or _variants(a)), "image": pics[0] if pics else None,
                        "mannequin_dropped": not pics and bool(usable_images(a, text, variant=v, keep_mannequin=True)),
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
# rà gộp Đ16v2 (12/10): only a scale LABEL ("In-game scale:", "Tỉ lệ:", a sentence starting "Scale:") — not "Damage scale: 1.2";
# the text runs to the END of its sentence ("approx. 3.0 head-heights; held two-handed" kept whole — `_scale_span`)
_SCALE_LABEL = re.compile(r"(?:(?<!\w)in-game\s+scale|(?:^|(?<=[.;:,(]\s)|(?<=[\]—–-]\s)|(?<=\())scale|(?<!\w)(?:relative size|tỉ lệ|tỷ lệ|kích thước so người))"
                          r"\s*:\s*", re.I)
_NOT_END = re.compile(r"(?:approx|ca|e\.g|i\.e|vs|no|st)$", re.I)


def _scale_span(source: str):
    """(start, end, text) of the scale label + its words up to the end of the sentence, or None."""
    m = _SCALE_LABEL.search(source or "")
    if not m:
        return None
    i = m.end()
    while i < len(source):
        ch = source[i]
        if ch == "\n":
            break
        if ch == "." and not (i + 1 < len(source) and source[i + 1].isdigit()) and not _NOT_END.search(source[m.end():i]):
            break
        i += 1
    text = source[m.end():i].strip(" ;")
    return (m.start(), min(i + 1, len(source)), text) if text else None

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
        span = _scale_span(source)
        if span:
            return span[2]
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
            if re.search(r"(?:\bno|\bnot|\bnever|\bwithout|không|chứ không phải)\s+(?:an?\s+|the\s+)?$", text[:m.start()], re.I):
                continue                                   # rà gộp Đ16v2: "no translucent amber glue wall" keeps its meaning
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


def variant_notes(conn, project_id: Optional[int], data: Dict) -> List[str]:
    """Luật 1 (không im lặng): câu kịch bản cảnh nói dạng món mà chữ shot không mang → code mang dạng xuống (nói rõ); cảnh nói nhiều
    dạng khác nhau → không đoán (nói rõ). [] khi cờ tắt / không có gì."""
    out = []
    for lk in locks(conn, project_id, data):
        name = lk["asset"]["name"]
        if lk.get("variant_from") == "scene":
            out.append(f"dạng '{lk['variant']}' của {name} lấy từ câu kịch bản cảnh {data.get('story_scene')} — chữ shot không ghi dạng "
                       "(Đạo diễn chia shot bỏ mất); code đã mang dạng xuống shot (ảnh Kho đúng dạng + câu khóa)")
        elif lk.get("variant_from") == "ambiguous":
            found = scene_variants(conn, project_id, data, lk["asset"])
            out.append(f"câu kịch bản cảnh {data.get('story_scene')} nói {name} ở nhiều dạng ({', '.join(found)}) mà chữ shot không ghi "
                       "dạng nào — không đoán, dùng dạng mặc định; ghi đích danh dạng vào chữ shot")
    return out


def issues(conn, project_id: int, data: Dict) -> List[Dict]:
    """VÀNG (never a stop): the shot says a common word of a kind with several project props of that kind and names none — not
    guessed; a locked prop without any description in the Kho. Lỗi hệ thống 3 (cờ riêng skill_object_guard): + VÀNG vật kỹ năng
    (core/skill_objects.issues — từ dễ hiểu sai, gợi ý ghép code) — [] khi cờ đó tắt."""
    from . import skill_objects
    skill = skill_objects.issues(conn, project_id, data) if project_id is not None else []
    if not enabled() or project_id is None:
        return skill
    pool, words, _text, generic = _scan(conn, project_id, data)
    holders = _holders(conn, project_id, data, pool)
    out = []
    pov_issue = pov_gun_issue(conn, project_id, data)
    if pov_issue:
        out.append(pov_issue)
    guns = [a for a, c in pool if c == "gun"]
    if holders and (generic["gun"] or any(_named(a, words) for a in guns)):
        # Đ16v3: a gun the text names that is locked to nobody in this shot → ĐỎ before a paid picture
        owners = {i: names for i, names in holders.items()}
        people = [assets.fold(n) for n in _present(conn, project_id, data)]
        for a in guns:
            if not _named(a, words) or a["id"] in owners:
                continue
            locked = "; ".join(f"{', '.join(n)} → {next((g['name'] for g in guns if g['id'] == i), i)}" for i, n in owners.items())
            sents = _gun_sentences(_text, a)
            used = [x for x in sents if _GUN_ACTION.search(x) and (
                any(" " + p + " " in " " + assets.fold(x) + " " for p in people)
                or re.search(r"(?<!\w)(?:he|she|they|his|her|their|anh ta|cô ấy|hắn|họ)(?!\w)", x, re.I))]
            if used:
                out.append({"level": "red", "part": "dao_cu",
                            "msg": f"chữ shot cho nhân vật dùng súng {a['name']} (\"{used[0][:80]}\") nhưng không ai trong shot được khóa súng này "
                                   f"(đã khóa: {locked}) — sửa chữ shot theo súng đã khóa; nếu người cầm {a['name']} có trong shot thì thêm họ vào "
                                   "nhân vật của shot hoặc gán súng ở Bước 1"})
            elif sents:
                out.append({"level": "warn", "part": "dao_cu",
                            "msg": f"chữ shot nhắc súng {a['name']} mà không ai trong shot được khóa súng này (đã khóa: {locked}) — kiểm lại"})
        # hộp thư 14:35 (#27 shot 16): "four enemies … with SKORP submachine guns" — SKORP is KELLY's. Attributing a gun from free text is
        # fragile (rà: 10 ordinary sentences came out wrong) → only ever YELLOW, never a stop. Per clause: the present person written
        # NEAREST before the gun (not across "by / bị / được": passive), else a group word (enemies / soldiers / lính…) when the gun's
        # owner is not a group-like character; the owner there → fine. Fields are joined as sentences (never glued into one).
        present = _present(conn, project_id, data)
        group_rx = re.compile(r"(?<!\w)(?:enem(?:y|ies)|soldiers?|guards?|troops?|squad|they all|all of them|lính|địch|kẻ thù|cả nhóm|bọn)(?!\w)", re.I)
        joined = ". ".join(str((data or {}).get(k) or "").strip().rstrip(".") for k in _TEXT_KEYS if str((data or {}).get(k) or "").strip())
        flagged = set()
        for a in guns:
            if a["id"] not in owners or a["id"] in flagged:
                continue                                  # locked to nobody in the shot: handled above
            mine = {assets.fold(n) for n in owners[a["id"]]}
            owner_is_group = any(group_rx.search(n) or re.search(r"(?<!\w)(?:linh|dich|enemy|soldier|guard)(?!\w)", assets.fold(n))
                                 for n in owners[a["id"]])
            for sent in _gun_sentences(joined, a):
                for clause in re.split(r",|;|(?<!\w)(?:while|as|when|and|but|who|which|whereas|trong khi|còn|và|đang|khi)(?!\w)",
                                       sent, flags=re.I):
                    if not _gun_sentences(clause, a):
                        continue
                    gun_at = min((m.start() for n in assets.names_of(a) if len(assets.fold(n)) >= 2
                                  for m in re.finditer(r"(?<!\w)" + re.escape(n.strip()) + r"(?!\w)", clause, re.I)), default=0)
                    head = clause[:gun_at]
                    if re.search(r"(?<!\w)(?:by|bị|được|from|of|của)(?!\w)", head, re.I):
                        continue                          # passive / possession: "shot by Kelly with her SKORP", "SKORP của Kelly"
                    folded = assets.fold(head)
                    found = [(folded.rfind(assets.fold(n)), n) for n in present if (" " + assets.fold(n) + " ") in " " + folded + " "]
                    if found:
                        who = max(found)[1]
                        if assets.fold(who) in mine:
                            continue
                    else:
                        g = group_rx.search(head)
                        if not g or owner_is_group or any(" " + m + " " in " " + assets.fold(clause) + " " for m in mine):
                            continue                      # "Lính địch ngã… trước làn đạn SKORP của Kelly": the owner is in the clause
                        who = g.group(0)
                    out.append({"level": "warn", "part": "dao_cu",
                                "msg": f"chữ shot có vẻ cho {who} dùng {a['name']} — súng này khóa cho {', '.join(owners[a['id']])} (\"{clause.strip()[:80]}\"); "
                                       "kiểm lại theo bảng gán súng (mỗi người súng của mình)"})
                    flagged.add(a["id"])
                    break
                if a["id"] in flagged:
                    break
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
    for msg in variant_notes(conn, project_id, data):
        out.append({"level": "warn", "part": "dao_cu", "msg": msg})
    for lk in locks(conn, project_id, data):
        if lk.get("mannequin_dropped"):              # rà 14/10: lọc hình nộm làm hết ảnh — nói, không im lặng
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": f"món Kho {lk['asset']['name']}: bỏ ảnh hình nộm khỏi khóa vật — vật chỉ còn tả bằng chữ "
                               "(thêm ảnh sạch không có hình nộm ở Kho nếu cần giống mẫu)"})
        if lk["category"] == "gun" and not weapon_scale(conn, lk["asset"], lk["variant"]):
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": f"món Kho {lk['asset']['name']} thiếu tỉ lệ — loại súng chưa rõ hoặc mâu thuẫn; thêm 'Tỉ lệ:' vào mô tả/hồ sơ hoặc kích thước ở Kho"})
        if not lk["form"]:
            out.append({"level": "warn", "part": "dao_cu",
                        "msg": f"món Kho {lk['asset']['name']} chưa có mô tả — prompt chỉ nêu được tên; thêm mô tả ở Kho"})
        elif lk["has_forms"] and lk["variant"]:
            default = _form_attributes(form_text(lk["asset"], None))
            skin = _form_attributes(lk["form"])
            spans = [m.span() for name in assets.names_of(lk["asset"])
                     for m in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", _text, re.I)]
            spans += [m.span() for m in _SHOT_RX[lk["category"]].finditer(_text)]
            nearby = []
            # Thuộc tính phải sát cụm đạo cụ; skin nằm giữa màu và tên vẫn cùng cụm.
            prefix = re.compile(r"(?:" + _ATTRIBUTE_RX.pattern + r")(?:[ -]+(?:" + _ATTRIBUTE_RX.pattern
                                + r"))*[ -]+(?:skin\s+)?$", re.I)
            suffix = re.compile(r"\s+(?:is|made of|of|là|bằng|màu)\s+((?:" + _ATTRIBUTE_RX.pattern
                                + r")(?:[ -]+(?:" + _ATTRIBUTE_RX.pattern + r"))*)(?=\s*(?:[.;,!?]|$))", re.I)
            for a, b in spans:
                if _OTHER_NOUN_HEAD.match(_text[b:]):
                    continue
                before = prefix.search(_text[:a])
                if before and not re.search(r"(?:\bno|\bnot|\bnever|\bwithout|\black(?:s)?|không(?: có)?|chứ không phải)\s+$",
                                            _text[:before.start()], re.I):
                    nearby.extend(m.group().lower() for m in _ATTRIBUTE_RX.finditer(before.group()))
                after = suffix.match(_text, b)
                if after:
                    nearby.extend(m.group().lower() for m in _ATTRIBUTE_RX.finditer(after.group(1)))
            conflict = [w for w in nearby if _ATTRIBUTE_KEY.get(w) in default - skin]
            if conflict:
                out.append({"level": "warn", "part": "dao_cu",
                            "msg": f"mâu thuẫn dạng: {lk['asset']['name']} chọn {lk['variant']} nhưng chữ shot tả thuộc tính mặc định "
                                   f"({', '.join(dict.fromkeys(conflict))}) — sửa chữ shot hoặc chọn lại dạng"})
        elif lk["has_forms"] and lk["variant"] is None:
            said = _colour_words(lk["asset"], lk["category"], _text)
            if said:
                out.append({"level": "warn", "part": "dao_cu",
                            "msg": f"chữ shot tả {lk['asset']['name']} bằng màu/chất liệu khác ({', '.join(said)}) mà món khóa ở dạng "
                                   f"mặc định ({lk['form'][:60]}) — câu khóa đè lên, nên sửa chữ shot cho khỏi mâu thuẫn"})
    return out + skill


def prompt_part(conn, project_id: int, data: Dict) -> str:
    """The 'Prop lock' sentences of the picture prompt ('' when off / nothing to lock — the prompt then stays byte for byte)."""
    if not enabled():
        return ""
    bits = []
    for lk in locks(conn, project_id, data):
        a, form = lk["asset"], lk["form"]
        if lk["category"] == "gun":
            # Nhãn tỉ lệ chỉ xuất hiện ở câu chuẩn ưu tiên, tránh 2 nguồn trái nhau.
            span = _scale_span(form)                    # rà gộp Đ16v2/v3: the whole "In-game scale: …" sentence leaves the form
            if span:
                form = (form[:span[0]] + form[span[1]:])
            form = re.sub(r"\s{2,}", " ", form).strip(" .;,")
        over = f"; this overrides any other colour or material described above for it" if form and lk["has_forms"] else ""
        if lk.get("holders"):
            # Đ16v3: whose gun it is — each present character gets their own locked gun, never another one
            who = " and ".join(lk["holders"])
            others = [x["asset"] for x in locks(conn, project_id, data) if x["asset"]["id"] != a["id"] and x["category"] == "gun"]
            slung_here = any(_SLUNG.search(sent) and not any(_gun_sentences(sent, o) for o in others)
                             for sent in re.split(r"(?<=[.!?;,])\s+", shot_text(data)))
            slung = ("; when it is slung on the back it is this same gun at its true size, worn across the back, not in the hands"
                     if slung_here else "")
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
                    r"[^.]*?as its reference picture shows")   # rà Đ16v3: never across into the next prop's sentence
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


def missing_refs(conn, project_id: int, data: Dict, refs) -> List[str]:
    """Ảnh khóa còn thiếu trong GÓI CUỐI; cùng tên nhưng khác ảnh/dạng vẫn thiếu."""
    import os
    def key(path):
        return os.path.normcase(os.path.abspath(assets.resolve(path)))
    sent = {key(r["path"]) for r in refs if r.get("path")}
    return [x["asset"]["name"] for x in reference_images(conn, project_id, data)
            if key(x["image"]["path"]) not in sent]
