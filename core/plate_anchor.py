"""Lỗi hệ thống 1 sau #27 tập 1 (13/10, shot 17/21 — job 893 → 910, 744 → 911): ảnh vẽ không bám render 3D của shot.

Gốc lỗi: render nền (plate) đi lẫn ở vị trí thứ 7–8 trong ~9 ảnh tham chiếu, còn chữ của Đạo diễn trong prompt ảnh tự tả MỘT NỀN KHÁC
("Clock tower plaza, low retaining walls, red-roof houses in far background") → model vẽ theo chữ: tháp ở xa giữa khung, cầu thang, nhà
mái đỏ, trong khi render cho thấy chân tháp sát bên trái, cắt mép trên. Câu PRECEDENCE ("nền theo render, bỏ chữ trái render") có sẵn
nhưng model vẫn theo chữ. Người dùng phải viết tay câu nền đúng (job 910/911).

Công thức chung (cờ `plate_anchored_image`, cần `place_render_refs`; TẮT = đường cũ từng byte):
  (a) chữ NỀN của prompt ảnh SINH TỪ dữ liệu sân khấu 3D của plate (vị trí máy, mốc chiếu vào khung, khoảng cách tới mốc / tới vật chắn
      đầu tiên, chân trời) — `background_sentence`. Câu Đạo diễn CHỈ tả nền (không có người / đạo cụ / ánh sáng) bị BỎ; cụm "in front of /
      against … tower/house/building" trong câu có người bị bỏ — `strip_scenery` → diag VÀNG có trích chữ đã bỏ;
  (b) render là ẢNH 1 của gói gửi (`plate_first`) + câu `KEEP` "giữ đúng nền / kiến trúc / bố cục của ảnh 1" đứng đầu prompt;
  (c) kiểm sau vẽ bằng code (core/plate_layout_qc.verdict: chân trời + đường trời từng cột) → ĐỎ / VÀNG, không im lặng khi không đo được.
Không gọi model, 0 USD."""
import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

from . import features

FEATURE = "plate_anchored_image"
CODE_WORDS = "plate_anchor_words"
CODE_BACKGROUND = "plate_anchor_background"
ROLE = "place_render"

KEEP = ("Image 1 is this shot's 3D render: keep exactly the background, architecture and layout of Image 1 — the same camera position, "
        "height and direction, the same horizon line, the same buildings, walls, landmark and trees in the same places and at the same "
        "sizes; only the people and their props are drawn into it.")


def enabled() -> bool:
    """Bật khi cờ bật VÀ có render 3D làm ảnh tham chiếu (place_render_refs) — không có plate thì không có gì để bám."""
    return features.on(FEATURE) and features.on("place_render_refs")


# ---- (b) render là ảnh 1 ---------------------------------------------------------------------------------------------------------
def plate_first(refs: List[Dict]) -> List[Dict]:
    """Đưa ảnh render của shot (role place_render) lên đầu danh sách, giữ nguyên thứ tự các ảnh còn lại. Không có render → như cũ."""
    at = next((i for i, r in enumerate(refs or []) if r.get("role") == ROLE), None)
    if not at:                                      # None (không có) hoặc 0 (đã đứng đầu)
        return list(refs or [])
    return [refs[at]] + refs[:at] + refs[at + 1:]


def with_keep(prompt: str, refs: List[Dict]) -> str:
    """Câu KEEP đứng đầu prompt — chỉ khi ảnh 1 THẬT là render (render rơi khỏi gói thì không nói tới một ảnh không có)."""
    if refs and refs[0].get("role") == ROLE:
        return KEEP + " " + prompt
    return prompt


_GROUND = re.compile(r"\s*(?:Background — measured on the 3D map of [^\n]*?)?Draw the background only as Image 1 shows it: [^\n]*?"
                     r"nothing added, moved or removed\.")


def fit_ground(prompt: str, refs: List[Dict]) -> str:
    """Câu NỀN (background_sentence) theo gói THẬT gửi đi (rà gộp lỗi 1, 13/10): render là ảnh n ≠ 1 → đổi "Image 1" thành "Image n";
    render rơi khỏi gói (không đọc được / quá trần) → bỏ cả câu, không trỏ "Image 1" vào ảnh người — nền quay về chữ địa điểm
    (name_render) và việc mất render đã được báo (missing_reference)."""
    m = _GROUND.search(prompt or "")
    if not m:
        return prompt
    n = next((i for i, r in enumerate(refs or [], 1) if r.get("role") == ROLE), None)
    if n:
        prompt = agree_direction(prompt)
        m = _GROUND.search(prompt)
    if n == 1:
        return prompt
    if n:
        return prompt[:m.start()] + m.group(0).replace("Image 1", f"Image {n}") + prompt[m.end():]
    return (prompt[:m.start()] + prompt[m.end():]).strip()


# G6 (17/10, #31 shot 6/11/32): the DP's direction sentence (location_pack.script_sentence, from plate_view) said "the camera looks
# towards the villa: the villa is behind the character" while the plate's MEASURED sentence said "the villa is outside this frame (not
# visible)" (hedges / the angle hide it). The measured one is the truth of the render sent: a direction sentence that claims the
# opposite leaves the prompt (the plate itself was rendered with that direction — nothing else changes).
_DIRECTION = re.compile(r"\s*Camera direction chosen for this shot: [^.]*\.")
_CLAIMS_SEEN = re.compile(r"is behind the character|is in the background|edge of the background")
_CLAIMS_HIDDEN = re.compile(r"is NOT in the frame|is off-frame")


def agree_direction(prompt: str) -> str:
    """The prompt without a 'Camera direction chosen' sentence that contradicts the measured background sentence; unchanged otherwise."""
    g = _GROUND.search(prompt or "")
    if not g:
        return prompt
    ground = g.group(0)
    hidden = "is outside this frame (not visible)" in ground
    seen = bool(re.search(r"\bstands about [\d.]+ m from", ground))
    if not (hidden or seen):
        return prompt                                   # landmark unknown: nothing measured to contradict

    def fix(d):
        text = d.group(0)
        if (hidden and _CLAIMS_SEEN.search(text)) or (seen and _CLAIMS_HIDDEN.search(text)):
            return ""
        return text
    return _DIRECTION.sub(fix, prompt)


# ---- (a) nền sinh từ dữ liệu sân khấu 3D -------------------------------------------------------------------------------------------
def _third(u: float) -> str:
    return "the left third" if u < 1 / 3 else "the middle" if u < 2 / 3 else "the right third"


def landmark_facts(rec: Dict, entry: Optional[Dict], aspect: Optional[float] = None) -> Dict:
    """Mốc của bối cảnh (model3d.anchor) nhìn từ máy của plate — chiếu bằng code (stage_grid.project), không model:
    {"known": bool, "why" (khi không biết), "in_frame", "u", "base_v", "top_cut", "dist_subject_m", "dist_camera_m"}.
    Mốc là một cột đứng: chân (độ cao mặt đất chỗ nhân vật) → điểm neo (anchor z)."""
    from . import stage_grid as sg
    from .stage_facts import ASPECT
    cam = (rec or {}).get("camera_plan") or {}
    loc, aim, lens = cam.get("location"), cam.get("look_at"), cam.get("lens")
    anchor = (entry or {}).get("anchor")
    if not (isinstance(anchor, (list, tuple)) and len(anchor) >= 3):
        return {"known": False, "why": "bối cảnh chưa có mốc (model3d.anchor)"}
    if not (loc and aim and lens):
        return {"known": False, "why": "plate không có camera_plan (vị trí/hướng/ống kính máy)"}
    feet = ((cam.get("subject") or {}).get("location") or [None, None, None])
    ground = float(feet[2]) if feet[2] is not None else float(loc[2]) - 1.7
    a = float(aspect or ASPECT)
    top_z = max(float(anchor[2]), ground + 0.5)
    pts = []
    for k in range(11):                              # 11 điểm dọc thân mốc, chân → neo
        z = ground + (top_z - ground) * k / 10
        pts.append(sg.project(loc, aim, (float(anchor[0]), float(anchor[1]), z), float(lens), a))
    inside = [p for p in pts if p and 0.0 <= p[0] <= 1.0 and 0.0 <= p[1] <= 1.0]
    base, top = pts[0], pts[-1]
    out = {"known": True, "in_frame": bool(inside),
           "dist_camera_m": round(math.hypot(float(anchor[0]) - float(loc[0]), float(anchor[1]) - float(loc[1])), 1)}
    if feet[0] is not None:
        out["dist_subject_m"] = round(math.hypot(float(anchor[0]) - float(feet[0]), float(anchor[1]) - float(feet[1])), 1)
    if inside:
        us = [p[0] for p in inside]
        out["u"] = round(sum(us) / len(us), 3)
        out["base_v"] = round(base[1], 3) if base and 0.0 <= base[1] <= 1.0 and 0.0 <= base[0] <= 1.0 else None
        out["top_cut"] = bool(top is None or top[1] < 0.0)
    return out


def background_sentence(rec: Dict, entry: Optional[Dict], place_name: str, landmark_name: Optional[str] = None,
                        aspect: Optional[float] = None) -> Tuple[str, List[str]]:
    """(câu tiếng Anh tả NỀN của shot, ghi chú tiếng Việt những gì không biết). Chỉ từ số đo của plate + mốc 3D — không từ chữ kịch bản."""
    notes: List[str] = []
    mark = landmark_name or f"the main landmark of {place_name}"
    f = landmark_facts(rec, entry, aspect)
    bits = []
    if not f["known"]:
        notes.append(f["why"] + " — câu nền không nói vị trí mốc")
    elif f["in_frame"]:
        where = f"in {_third(f['u'])} of the frame"
        near = f.get("dist_subject_m")
        dist = f"about {near:.0f} m from the main character" if near is not None else f"about {f['dist_camera_m']:.0f} m from the camera"
        base = ("its base visible at about {:.0f}% from the top of the frame".format(f["base_v"] * 100)
                if f.get("base_v") is not None else "its base outside the frame")
        top = "rising past the top edge of the frame" if f.get("top_cut") else "its top inside the frame"
        bits.append(f"{mark} stands {dist}, {where}, {base}, {top}")
    else:
        bits.append(f"{mark} is outside this frame (not visible)")
    clear = (rec or {}).get("clearance") or {}
    if clear.get("background_m") is not None:
        bits.append(f"the first structure straight ahead of the camera is about {float(clear['background_m']):.1f} m from it")
    hz = ((rec or {}).get("camera") or {}).get("horizon_y")
    if hz is not None and 0.0 <= float(hz) <= 1.0:
        bits.append(f"the horizon line at {float(hz) * 100:.0f}% from the top")
    head = (f"Background — measured on the 3D map of {place_name} for this exact camera, as Image 1 shows it: "
            + "; ".join(bits) + ". " if bits else "")
    return (head + "Draw the background only as Image 1 shows it: the same buildings, walls, trees and landmark in the same places "
            "and sizes, nothing added, moved or removed."), notes


# ---- (a) bỏ chữ nền tự do của Đạo diễn -------------------------------------------------------------------------------------------
_SCENERY = re.compile(r"\b(?:background|backdrop|far distance|in the distance|distant|horizon|skyline|cityscape|landscape|scenery|"
                      r"buildings?|houses?|roofs?|rooftops?|red-roof|towers?|clock tower|staircases?|stairs|steps|walls?|plaza|square|"
                      r"courtyard|street|road|alley|trees?|palms?|forest|hills?|mountains?|sea|ocean|river|bridge|village|town|"
                      r"terrain|map)\b", re.I)
_PERSON = re.compile(r"\b(?:he|she|him|her|his|hers|they|them|their|character|characters|enemy|enemies|person|people|man|men|woman|"
                     r"women|girl|boy|soldier|soldiers|player|players|figure|figures|body|bodies|face|hands?|crowd|team|squad|"
                     r"teammates?|survivor|survivors)\b", re.I)
_PROP = re.compile(r"\b(?:glue|gloo|gloowall|gun|guns|rifle|weapon|weapons|smg|sniper|pistol|shotgun|grenade|vehicle|car|pet)\b", re.I)
_LIGHT = re.compile(r"\b(?:light|lighting|lit|sunlight|daylight|sun|sunny|shadows?|glow|glowing|mood|tone|dusk|dawn|night|fog|mist|"
                    r"rain|weather|sky|clouds?|kelvin|\d{3,4}\s?k|focus|blur\w*|sharp|bokeh|depth[ -]of[ -]field|style|"
                    r"proportions|texture)\b", re.I)          # ánh sáng + câu phong cách ("not blurred background") giữ nguyên
_HEAD = re.compile(r",\s*(?=(?:the\s+)?(?:far\s+)?(?:background|backdrop)\b)", re.I)   # ", BACKGROUND = …" giữa câu có người
_CLAUSE = re.compile(r"(?:[^.;!?]|[.;!?](?!\s|$))+(?:[.;!?]+(?=\s|$)|$)")   # "1.7 m", "gpt-image-2.5" không cắt câu
# cụm quan hệ tả NỀN trong câu có người: "in front of a clock tower and low red-roof house" (#22 KLD) — chỉ với vật nền xa
# (tháp / nhà / mái / đồi / biển…), không với tường / cây / bậc (chỗ người núp, đứng — dàn cảnh, không phải nền)
_FAR = r"(?:clock tower|towers?|houses?|buildings?|roofs?|rooftops|skyline|cityscape|village|town|hills?|mountains?|sea|ocean)"
_WORD = r"(?:(?!glue\b|gloo|gloowall\b)[\w'’-]+\s+)"
_PHRASE = re.compile(rf"\s*,?\s*\b(?:in front of|against|beneath|beside|next to)\s+{_WORD}{{0,6}}?{_FAR}\b"
                     rf"(?:\s*(?:,|and)\s+{_WORD}{{0,5}}?{_FAR}\b)*", re.I)


def _names_re(names: Sequence[str]) -> Optional["re.Pattern"]:
    words = [re.escape(str(n).strip()) for n in names or [] if str(n or "").strip()]
    return re.compile(r"(?:" + "|".join(words) + r")", re.I) if words else None


def _split_head(clause: str) -> List[str]:
    """Một vế "…, BACKGROUND = …" tách làm hai ở dấu phẩy trước chữ background (#27 shot 21: câu nền dính sau câu có người)."""
    parts = _HEAD.split(clause)
    return [parts[0]] + [", " + x for x in parts[1:]]


def _keeps(text: str, names: Optional["re.Pattern"]) -> bool:
    return bool(_PERSON.search(text) or _PROP.search(text) or _LIGHT.search(text) or (names and names.search(text)))


# G6 (17/10, #31 shot 6/11/13/14): "…, the villa silhouette faint in the far background between hedge tops" / "dark hedge walls and the
# villa's pale silhouette faint in the background" / "The villa rooftop is faintly visible beyond the hedges under the dark swirling sky"
# stayed: the clause also had a person / fog / sky word. A comma part about a far landmark (villa, tower, house, silhouette…) placed in
# the background / beyond / in the distance, with no person, prop or light source in it, goes — the plate's measured sentence decides
# whether that landmark is in the frame at all.
_MARK_NOUN = (r"(?:villas?|mansions?|castles?|manors?|palaces?|cathedrals?|churche?s?|clock tower|towers?|houses?|buildings?|roofs?|"
              r"rooftops?|skyline|cityscape|village|town|hills?|mountains?)")
# the part is ABOUT the landmark: its silhouette, or the landmark noun heads the part ("the villa …", "and the pale villa's …") — never
# a place phrase of the people around it ("far distance near the stone plaza of the Clock Tower" stays: test_plate_anchor_loi1)
# rà 17/10: "silhouette" alone is not a landmark ("a hooded silhouette waiting in the background", "the tall dark silhouette of the
# Unseen looming far away" are people / the monster) — only a silhouette OF a landmark noun in the same part
_MARK_SEG = re.compile(r"\bsilhouettes?\b[^,]*\b" + _MARK_NOUN + r"\b|\b" + _MARK_NOUN + r"\b[^,]*\bsilhouettes?\b|^\s*(?:and\s+)?(?:the\s+|a\s+|an\s+)?(?:[\w'’-]+\s+){0,2}?" + _MARK_NOUN + r"(?:'s|’s)?\b", re.I)
_AWAY = re.compile(r"\b(?:background|backdrop|beyond|in the distance|far distance|far away|distant|faint(?:ly)? visible)\b", re.I)
_SOURCE = re.compile(r"\b(?:light|lighting|lit|sunlight|moonlight|glow\w*|lamps?|lanterns?|fire)\b", re.I)


def _cut_far_segments(clause: str, who, removed: List[str]) -> str:
    m = re.search(r"[.;!?]+\s*$", clause)
    body, tail = (clause[:m.start()], clause[m.start():]) if m else (clause, "")
    segs = body.split(",")
    keep = []
    for seg in segs:
        if (_MARK_SEG.search(seg) and _AWAY.search(seg) and not _PERSON.search(seg) and not _PROP.search(seg)
                and not _SOURCE.search(seg) and not (who and who.search(seg))):
            removed.append(seg.strip())
            continue
        keep.append(seg)
    if len(keep) == len(segs):
        return clause
    return ",".join(keep) + tail


def strip_scenery(text: str, names: Sequence[str] = ()) -> Tuple[str, List[str]]:
    """(chữ đã bỏ phần tả nền, [đoạn đã bỏ]). Bỏ: (1) câu/vế (tách ở . ; ! ?) có chữ nền mà KHÔNG có người / tên nhân vật / đạo cụ / ánh
    sáng; (2) trong câu còn lại, cụm "in front of / against / beneath / beside / next to … tháp / nhà / mái / đồi / biển". Câu tả người
    đứng đâu (on the plaza, near the tower, behind the glue wall) GIỮ — đó là dàn cảnh, nền do render quyết."""
    src = str(text or "")
    if not src.strip():
        return src, []
    who = _names_re(names)
    removed: List[str] = []
    kept: List[str] = []
    pieces = [p for m in _CLAUSE.finditer(src) for p in _split_head(m.group(0))]
    for clause in pieces:
        body = clause.strip()
        if not body:
            continue
        if _SCENERY.search(body) and not _keeps(body, who):
            removed.append(body.strip(" ,").rstrip(".;!? "))
            end = re.search(r"[.;!?]+$", body)
            kept.append(end.group(0) if end else "")      # giữ dấu ngắt câu của vế bỏ ("…her; bright daylight")
            continue
        cut = _PHRASE.sub(lambda x: (removed.append(x.group(0).strip(" ,")) or ""), clause)
        kept.append(_cut_far_segments(cut, who, removed))
    if not removed:
        return src, []
    out = "".join(kept)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    out = re.sub(r"([.;!?])(?:\s*[.;!?])+", r"\1", out)    # "poses. ; ; ." → "poses."
    out = re.sub(r"([,;:])\s*(?=[,.;])", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip().lstrip(".;!?, ")
    return out, removed


def words_note(removed: List[str]) -> str:
    """Câu diag VÀNG (tiếng Việt) cho chữ nền đã bỏ — trích ngắn từng đoạn."""
    quoted = "; ".join(f"\"{r[:90]}{'…' if len(r) > 90 else ''}\"" for r in removed[:6])
    more = f" (+{len(removed) - 6} đoạn)" if len(removed) > 6 else ""
    return (f"prompt ảnh: đã BỎ {len(removed)} đoạn chữ tả nền của Đạo diễn (nền do render 3D quyết, câu nền sinh từ plate thay vào): "
            f"{quoted}{more} — sửa image_prompt / blocking nếu đoạn đó là dàn cảnh cần giữ")
