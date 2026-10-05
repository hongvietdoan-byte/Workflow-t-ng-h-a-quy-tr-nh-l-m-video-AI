"""S14.31 · Biên kịch chỉ viết thứ DỰNG ĐƯỢC (người dùng chấm 05/10: 5/5 kịch bản khó quay chuẩn). 0 USD, không gọi model.

Ba việc, đều bằng code:
  1. kit(conn, pid)        'thứ dựng chắc được' của Kho — nơi có file 3D dựng bối cảnh (map + khu vực; ảnh Kho đơn thuần không đủ — người dùng 05/10), nhân vật có ảnh chuẩn đã duyệt
                            + trang phục mặc định, kỹ năng có hồ sơ. Biên kịch đọc danh sách này thay vì cả Kho.
  2. anchors               các điểm then chốt người dùng chốt (nhân vật + trang phục, nơi, diễn biến, cú chốt, có/không gameplay-giao diện).
                            Thiếu hoặc nằm ngoài kit → hỏi lại (gate), KHÔNG gọi Claude.
  3. check_scenes(...)     sau lượt viết: cảnh giao diện / màn hình điện thoại / sảnh / combat gameplay, nơi ngoài kit → cảnh bị CHẶN;
                            check_anchors(...): điểm then chốt phải còn trong kịch bản.
"""
import os
import re
from typing import Dict, List, Optional, Tuple

from . import assets

# ---- the points the person must fix before the Biên kịch is paid (ý 6) -------------------------------------------------------------------
ANCHOR_LABELS = {
    "characters": "nhân vật (chọn trong Kho)",
    "costume": "trang phục (ghi 'mặc định' hoặc tên bộ có trong hồ sơ)",
    "place": "nơi quay (map + khu vực trong Kho)",
    "plot": "diễn biến chính / mâu thuẫn",
    "ending": "cú chốt / kết",
    "gameplay_ui": "có hay không cảnh gameplay / giao diện (ghi 'có' hoặc 'không')",
}
YES, NO = ("co", "có"), ("khong", "không")
OVERLAP = 0.5                 # share of an anchor's content words that must still be in the script


def clean_anchors(raw: Optional[Dict]) -> Dict:
    raw = raw or {}
    chars = raw.get("characters") or []
    if isinstance(chars, str):
        chars = [c for c in re.split(r"[,;\n]", chars)]
    out = {"characters": [str(c).strip().upper() for c in chars if str(c).strip()]}
    for k in ("costume", "place", "plot", "ending"):
        out[k] = str(raw.get(k) or "").strip()
    g = assets.fold(str(raw.get("gameplay_ui") or ""))
    out["gameplay_ui"] = "co" if g in YES or g.startswith("co ") else "khong" if g in NO or g.startswith("khong") else ""
    # S14.35: a place outside the Kho — what kind it is (the person says; never guessed) and how the set is made
    pk = assets.fold(str(raw.get("place_kind") or "")).replace("_", " ")
    kind = "real_life" if pk.startswith(("doi thuong", "real life", "ngoai game")) else "game_map" if pk.startswith(("map", "game")) else ""
    sc = assets.fold(str(raw.get("scene_choice") or "")).replace("_", " ")
    choice = "meshy" if sc.startswith(("meshy", "3d")) else "ref_image" if sc.startswith(("ref", "anh", "image", "dao dien")) else ""
    if kind:
        out["place_kind"] = kind
    if kind == "real_life" and choice:
        out["scene_choice"] = choice
    return out


def missing_anchors(anchors: Optional[Dict]) -> List[str]:
    """Labels of the key points the person has not said yet."""
    a = clean_anchors(anchors)
    return [label for k, label in ANCHOR_LABELS.items() if not a.get(k)]


# ---- what can be built for sure ------------------------------------------------------------------------------------------------------
_STANDARD_ROLES = ("front_standard", "design_sheet", "full_body", "half_body")
_CAMERA_PLATES = ("eye_level", "low_angle", "high_angle")


def _brief(text: str, n: int = 220) -> str:
    return re.sub(r"\s+", " ", (text or "").split("[AI đọc ảnh]")[0]).strip()[:n]


def kit(conn, pid: int, game: str = "FF") -> Dict[str, List[Dict]]:
    """{"places": [{name, spots: [labels], names}], "characters": [{name, outfit, names}], "skills": [{character, skill}]}."""
    from . import location_pack, skill_dossier
    out: Dict[str, List[Dict]] = {"places": [], "characters": [], "skills": [], "excluded": []}
    for a in assets.list_assets(conn, game, None, pid):
        names = [a["name"]] + [x.strip() for x in str(a.get("aliases") or "").split(",") if x.strip()]
        if a["kind"] == "location":
            entry = location_pack.model3d(conn, a["id"])
            plates = [i for i in a["images"] if i.get("role") in _CAMERA_PLATES]
            if entry and not os.path.exists(assets.resolve(entry["path"]) or ""):     # rà: the entry names a file that is gone
                out["excluded"].append({"name": a["name"], "why": f"file 3D không còn trên đĩa ({entry['path']})"
                                        + ("" if plates else " và không có nền ngang tầm mắt")})
                entry = None
            if not entry and plates and not any(x["name"] == a["name"] for x in out["excluded"]):                    # người dùng 05/10: ảnh Kho làm ref cho bối cảnh đều bị lệch → chỉ nơi có file 3D dựng bối cảnh
                out["excluded"].append({"name": a["name"], "why": "chưa có file 3D dựng bối cảnh (chỉ có ảnh Kho làm tham chiếu — dễ bị lệch)"})
            if entry:
                spots = [str(v.get("label") or k) for k, v in ((entry or {}).get("spots") or {}).items()]
                out["places"].append({"name": a["name"], "names": names, "spots": spots, "has_3d": bool(entry)})
        elif a["kind"] in ("character", "pet"):
            if not any(i.get("role") in _STANDARD_ROLES and not assets.is_skin(i) for i in a["images"]):
                continue
            prof = assets.get_profile(conn, a["id"])
            approved = _brief(prof.get("must_keep") or prof.get("identity") or "") if prof.get("approved") else ""
            draft = "" if approved else _brief(a.get("description") or "")
            out["characters"].append({"name": a["name"], "names": names, "outfit": approved or draft, "draft": bool(draft)})
    have = {assets.fold(c["name"]) for c in out["characters"]}
    for d in (skill_dossier.load(n) for n in skill_dossier.names()):
        if d and d.get("active", True) and assets.fold(d.get("character") or "") in have:
            out["skills"].append({"character": d["character"], "skill": d.get("skill_vi") or d.get("skill_en") or ""})
    return out


def has_phrase(text: str, phrase: str) -> bool:
    """`phrase` is in `text` as whole words ("nha" is not in "nha tho"); both folded."""
    t, f = assets.fold(text), assets.fold(phrase)
    return bool(f) and re.search(r"(?<!\w)" + re.escape(f) + r"(?!\w)", t) is not None


def _find(items: List[Dict], text: str) -> Optional[Dict]:
    """The item whose name (or alias) is in `text` as a whole phrase."""
    for it in items:
        if any(has_phrase(text, n) for n in it.get("names") or [it["name"]]):
            return it
    return None


def place_in_kit(k: Dict, where: str) -> Optional[Dict]:
    """A place name, or one of its areas, as a scene heading / the person wrote it."""
    hit = _find(k["places"], where)
    if hit:
        return hit
    return next((p for p in k["places"] if any(has_phrase(where, s) for s in p["spots"])), None)


# ---- S14.35: a place outside the game that the Kho does not have yet -----------------------------------------------------------------
SCENE_CHOICES = {"ref_image": "Đạo diễn tạo ảnh bối cảnh làm tham chiếu", "meshy": "Meshy dựng 3D bối cảnh (tốn tiền — chỉ ghi, chưa chạy)"}


def kho_place(conn, pid: int, name: str, game: str = "FF") -> Optional[Dict]:
    """The Kho location (any, with or without 3D) whose name or alias is in `name` — the Kho's own 'loại tài sản' says it is a game map."""
    items = []
    for a in assets.list_assets(conn, game, None, pid):
        if a["kind"] == "location":
            items.append({"name": a["name"], "names": [a["name"]] + [x.strip() for x in str(a.get("aliases") or "").split(",") if x.strip()]})
    return _find(items, name)


def place_state(conn, pid: int, k: Dict, anchors: Optional[Dict]) -> Dict:
    """{"state": empty / in_kit / kho_no_3d / game_map_no_3d / needs_scene / ask}. A place not in the Kho at all is a game map or a
    real-life place only because the person SAID so (`place_kind`); not said → ask (0 USD), never guessed from the words."""
    a = clean_anchors(anchors)
    place = a["place"]
    if not place:
        return {"state": "empty"}
    if place_in_kit(k, place):
        return {"state": "in_kit"}
    if kho_place(conn, pid, place):
        return {"state": "kho_no_3d"}
    if a.get("place_kind") == "real_life":
        return {"state": "needs_scene", "choice": a.get("scene_choice") or ""}
    if a.get("place_kind") == "game_map":
        return {"state": "game_map_no_3d"}
    return {"state": "ask"}


def scene_est_usd(choice: str) -> Optional[float]:
    """Meshy: 'model' credits × USD per credit × up to MAX_TRIES (1 + 2 redo — counted high). A reference picture: inside the picture step."""
    if choice != "meshy":
        return None
    from . import meshy
    return round(meshy.CREDITS["model"] * meshy.usd_per_credit() * meshy.MAX_TRIES_PER_CHARACTER, 2)


def scene_needs(conn, pid: int) -> List[Dict]:
    """Sets the idea needs made (listed in the asset checklist; nothing is run): [{name, choice, label, est_usd, note}]."""
    from . import idea_to_script
    inputs = idea_to_script.get_state(conn, pid).get("inputs") or {}
    a = clean_anchors(inputs.get("anchors"))
    if place_state(conn, pid, kit(conn, pid), a)["state"] != "needs_scene":
        return []
    ch = a.get("scene_choice") or ""
    est = scene_est_usd(ch)
    note = ("chưa chọn cách tạo — Đạo diễn mặc định tạo ảnh bối cảnh; muốn Meshy 3D thì chọn ở khung nhập" if not ch else
            f"ước ≤ {est:.2f} USD (1 + 2 lần dựng lại), CHƯA chạy — người dùng duyệt giá rồi mới dựng" if ch == "meshy" else
            "ảnh bối cảnh nằm trong bước tạo ảnh của Đạo diễn (giá tính ở ước giá ảnh)")
    return [{"name": a["place"], "choice": ch, "label": SCENE_CHOICES.get(ch, "chưa chọn (mặc định: Đạo diễn tạo ảnh)"), "est_usd": est, "note": note}]


def gate(conn, pid: int, inputs: Dict) -> List[str]:
    """Why the Biên kịch must not be called yet (0 USD): missing key points, or key points outside what can be built."""
    a = clean_anchors((inputs or {}).get("anchors"))
    miss = missing_anchors(a)
    why = ([f"Thiếu điểm then chốt — hãy cho biết: {'; '.join(miss)}. Dự án tạo trước S14.31 chưa có các điểm này: mở ⚙ Thiết lập, "
            "điền rồi bấm 💡 Ý tưởng mới (bắt đầu lại từ lượt 1)"] if miss else [])
    k = kit(conn, pid)
    box = [str(c).upper() for c in (inputs or {}).get("characters") or []]
    for c in list(dict.fromkeys(a["characters"] + box)):
        if not _find(k["characters"], c):
            why.append(f"nhân vật {c} chưa có ảnh chuẩn đã duyệt trong Kho — chọn nhân vật khác hoặc bổ sung ảnh chuẩn")
    st = place_state(conn, pid, k, a)["state"]
    if st == "ask":
        why.append(f"nơi {a['place']} không có trong Kho — cho biết đây là map game hay nơi đời thường (ngoài game); "
                   "đời thường thì chọn cách tạo bối cảnh (ảnh do Đạo diễn tạo / Meshy 3D)")
    elif st == "game_map_no_3d":
        why.append(f"nơi {a['place']} là map game nhưng chưa có mô hình 3D trong Kho — chọn nơi khác hoặc bổ sung tư liệu")
    elif st == "kho_no_3d":
        gone = next((x for x in k["excluded"] if has_phrase(a["place"], x["name"])), None)
        why.append(f"nơi {a['place']} " + (f"bị loại khỏi danh sách dựng được: {gone['why']}" if gone else
                                           "chưa có mô hình 3D / nền ngang tầm mắt trong Kho") + " — chọn nơi khác hoặc bổ sung tư liệu")
    return why


# ---- what the Biên kịch is told -------------------------------------------------------------------------------------------------------
RULES = """## Ràng buộc DỰNG ĐƯỢC (xưởng chỉ dựng chắc được những thứ dưới đây — người dùng đã chấm hỏng kịch bản vi phạm)
- Chỉ dùng NƠI, NHÂN VẬT, KỸ NĂNG trong danh sách "Thứ dựng chắc được". Nơi ghi rõ **map + khu vực**; không dùng nơi chung chung ("phòng khách", "thành phố").
  Ngoài danh sách = không dựng được → không viết, hoặc hỏi lại người dùng.
- Trang phục nhân vật = trang phục mặc định ghi trong danh sách (không thêm áo choàng, mũ, phụ kiện không có trong hồ sơ).
- CẤM viết cảnh phải dựng lại giao diện game: màn hình điện thoại đang chơi Free Fire, sảnh chờ, menu, bảng xếp hạng, nút bấm, HUD đầy đủ,
  và combat gameplay (nhảy dù, bắn nhau có cover, góc nhìn người chơi, vòng bo). Chưa có tư liệu chứng minh dựng được. Chỉ khi người dùng
  ghi "có gameplay/giao diện" mới được viết, và vẫn ghi rõ trong `notes` đó là phần rủi ro.
- Kỹ thuật NÉ: quay người chơi NGOÀI ĐỜI (nhân vật 3D ở nơi trong danh sách), KHÔNG quay màn hình điện thoại; muốn người xem hiểu tình huống trong
  trận thì cho **thanh máu + tên + số đội hiện trên đầu nhân vật** thay vì dựng giao diện. Một cảnh = một nơi, một việc, camera xa/trung/cận rõ.
- Nhịp và nhân quả phải hợp lý: việc lớn cần đủ thời gian và bước đệm (nhảy dù → đáp đất → tìm đồ → giao tranh → thắng; không thể vừa
  nhảy dù bắn một chút đã Booyah). Thời lượng cảnh tương xứng việc xảy ra trong cảnh.
- Mỗi kịch bản phải có MỘT điểm nhấn (khoảnh khắc người xem nhớ): hình ảnh, câu thoại hoặc cú xoay — nêu rõ ở `notes`."""


def kit_block(k: Dict) -> str:
    lines = ["## Thứ dựng chắc được (CHỈ chọn trong danh sách này)"]
    lines.append("Nơi (map — khu vực): " + ("; ".join(f"{p['name']} — " + (", ".join(p["spots"]) or "mặc định") for p in k["places"]) or "(trống)"))
    lines.append("Nhân vật (trang phục mặc định): " + ("; ".join(
        f"{c['name']} — " + (f"{c['outfit']} (hồ sơ chưa duyệt — lấy từ mô tả, chưa chắc đúng)" if c.get("draft") else
                             c["outfit"] or "chưa có hồ sơ trang phục") for c in k["characters"]) or "(trống)"))
    lines.append("Kỹ năng có hồ sơ: " + ("; ".join(f"{s['character']} — {s['skill']}" for s in k["skills"]) or "(không có)"))
    if k.get("excluded"):
        lines.append("Đã loại, KHÔNG dùng: " + "; ".join(f"{x['name']} ({x['why']})" for x in k["excluded"]))
    if not k["places"] or not k["characters"]:
        lines.append("Danh sách trống một phần: KHÔNG được tự bịa nơi / nhân vật — ghi vào `notes` rằng Kho thiếu gì.")
    return "\n".join(lines)


def anchors_block(inputs: Dict) -> str:
    a = clean_anchors((inputs or {}).get("anchors"))
    if not any(v for v in a.values()):
        return ""
    return ("## Điểm then chốt người dùng đã chốt (KHÔNG ĐƯỢC ĐỔI — chỉ mở rộng chi tiết quanh chúng, không bịa thêm nhân vật / nơi / kết khác)\n"
            f"- Nhân vật: {', '.join(a['characters'])}\n- Trang phục: {a['costume']}\n- Nơi quay: {a['place']}\n- Diễn biến chính: {a['plot']}\n"
            f"- Cú chốt / kết: {a['ending']}\n- Gameplay / giao diện: {'CÓ' if a['gameplay_ui'] == 'co' else 'KHÔNG (cấm hoàn toàn)'}")


def custom_place_block(conn, pid: int, k: Dict, inputs: Dict) -> str:
    """S14.35: the one real-life place the person said needs a set made. Empty (prompt unchanged) for every other idea."""
    a = clean_anchors((inputs or {}).get("anchors"))
    if place_state(conn, pid, k, a)["state"] != "needs_scene":
        return ""
    return (f"## Nơi ngoài game cần tạo bối cảnh\n- {a['place']}: nơi đời thường chưa có trong Kho; xưởng sẽ tạo bối cảnh riêng "
            f"({SCENE_CHOICES.get(a.get('scene_choice') or '', 'Đạo diễn tạo ảnh bối cảnh làm tham chiếu')}). Chỉ dùng ĐÚNG nơi này làm bối cảnh; "
            "tả rõ vật dụng và góc nhìn cần có trong bối cảnh (bàn, tủ, quạt trần…) để tạo bối cảnh đủ; không thêm nơi đời thường khác.")


def blocks(conn, pid: int, inputs: Dict) -> str:
    k = kit(conn, pid)
    return "\n\n".join(x for x in (RULES, kit_block(k), custom_place_block(conn, pid, k, inputs), anchors_block(inputs)) if x)


# ---- the code check after the writing turn (0 USD) ------------------------------------------------------------------------------------
# Heuristic by design (rà S14.31): only specific game phrases, and only in the description / heading — never in what a person says.
_UI = [("màn hình điện thoại", r"man hinh (dien thoai|choi game|game)|cam dien thoai (choi|ngam)|dien thoai dang choi"),
       ("giao diện game", r"giao dien (game|free fire|ff|tran dau|nguoi choi|choi game)|\bmenu (game|chinh|free fire|chon)|bang xep hang|joystick|minimap|"
                          r"nut ban (tren|trong) |ban do nho"),
       ("sảnh chờ", r"sanh cho|sanh game|\blobby\b|man hinh (cho|chon nhan vat)")]
_GAMEPLAY = [("combat gameplay", r"nhay du|vong bo|thu hep bo|goc nhin (nguoi choi|thu nhat)|bat cover|ban ha guc|ha guc (doi thu|ke dich)")]
_HUD = r"\bhud\b|thanh may|so doi|ten nguoi choi"
_ON_HEAD = r"tren dau"
def _said(line: str) -> bool:
    """'KELLY: …' (speaker all in capitals, short); 'Cận màn hình điện thoại: …' is a description of what the camera shows."""
    who, sep, rest = line.partition(":")
    who = who.strip()
    return bool(sep and rest.strip() and 1 < len(who) <= 30 and who == who.upper() and any(c.isalpha() for c in who))


def _scene_hits(heading: str, body: str) -> List[str]:
    """Hits in the heading + the description lines; a line someone SAYS ("NAME: …") is dialogue, not what the camera shows."""
    shown = [ln for ln in body.splitlines() if not _said(ln)]
    raw = heading + "\n" + "\n".join(shown)
    t = assets.fold(raw)
    hits = [name for name, rx in _UI + _GAMEPLAY if re.search(rx, t)]
    if re.search(r"\bUI\b", raw):                         # the capitals only: "ui da" is an exclamation
        hits.append("giao diện game")
    if re.search(r"\bhud\b", t) and not re.search(_ON_HEAD, t):
        hits.append("HUD")
    return hits


_TIME_WORDS = {"ngay", "dem", "sang", "chieu", "toi", "trua", "hoang hon", "binh minh", "ban ngay", "ban dem", "s", "giay", "phut", "p"}


def _only_time(text: str) -> bool:
    """'NGÀY', '5-10s', 'ĐÊM' — a heading part that says when, not where."""
    f = assets.fold(text)
    return not f or all(w in _TIME_WORDS or re.fullmatch(r"[0-9]+(s|p|g|h)?", w) for w in f.split())


def _where(heading: str) -> str:
    """The place of a scene heading ("" = the heading names none: only a time)."""
    m = re.match(r"^\s*c[ảa]nh\s*\d+\s*[-–—:.]\s*(.*)$", heading, re.I)
    rest = (m.group(1) if m else heading).strip()
    where = rest.split(",", 1)[-1].strip() if "," in rest else rest
    return "" if _only_time(where) else where


def check_scenes(scenes, k: Dict, anchors: Dict, custom_place: str = "") -> Tuple[List[str], List[str], List[Dict]]:
    """(problems, flags, blocked_scenes) — interface / gameplay scenes and places outside the kit. The person's 'có gameplay' turns the
    first into a flag (said, not silent). `custom_place` (S14.35) = the real-life place that needs a set made: its scenes are flagged, not blocked."""
    problems, flags, blocked = [], [], []
    allowed = clean_anchors(anchors)["gameplay_ui"] == "co"
    for s in scenes:
        why = []
        hits = _scene_hits(s.heading, s.text)
        if hits and not allowed:
            why.append("cảnh dựng giao diện / gameplay chưa có tư liệu dựng được: " + ", ".join(hits))
        elif hits:
            flags.append(f"cảnh {s.idx}: có {', '.join(hits)} — rủi ro (chưa có tư liệu dựng được), người dùng đã chọn 'có'")
        where = _where(s.heading)
        if not where:
            why.append("thiếu nơi quay — tiêu đề cảnh chỉ có thời gian, cần 'CẢNH n - <thời gian>, <nơi trong Kho>'")
        elif not place_in_kit(k, where) and custom_place and (has_phrase(where, custom_place) or has_phrase(custom_place, where)):
            flags.append(f"cảnh {s.idx}: nơi {custom_place} ngoài game, chưa có trong Kho — cần tạo bối cảnh (ảnh ref do Đạo diễn tạo hoặc Meshy 3D, "
                         "xem bảng kê tài nguyên)")
        elif not place_in_kit(k, where):
            why.append(f"nơi {where} chưa có mô hình 3D / gói bối cảnh trong Kho")
        if why:
            blocked.append({"scene": s.idx, "why": why})
            problems += [f"cảnh {s.idx}: {w}" for w in why]
    return problems, sorted(set(flags)), blocked


def _words(text: str) -> List[str]:
    return [w for w in assets.fold(text).split() if len(w) >= 3]


def _kept(anchor: str, text: str) -> bool:
    need = set(_words(anchor))
    return not need or len(need & set(_words(text))) / len(need) >= OVERLAP


def check_anchors(scenes, anchors: Dict) -> List[str]:
    """The key points the person fixed must still be in the script (problems: 'điểm then chốt bị mất: …')."""
    a = clean_anchors(anchors)
    if not any(v for v in a.values()) or not scenes:
        return []
    whole = "\n".join(s.heading + "\n" + s.text for s in scenes)
    lost = []
    for c in a["characters"]:
        if not has_phrase(whole, c):
            lost.append(f"nhân vật {c}")
    if a["place"] and not has_phrase(whole, a["place"]):
        lost.append(f"nơi {a['place']}")
    if a["plot"] and not _kept(a["plot"], whole):
        lost.append(f"diễn biến chính ({a['plot']})")
    if a["ending"] and not _kept(a["ending"], "\n".join(s.heading + "\n" + s.text for s in scenes[-2:])):
        lost.append(f"cú chốt ({a['ending']})")
    return [f"điểm then chốt bị mất: {x}" for x in lost]
