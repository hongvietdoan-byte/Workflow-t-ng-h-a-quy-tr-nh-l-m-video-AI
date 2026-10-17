"""DẠNG của nhân vật khai ở Kho phong cách (lỗi G2, 17/10 #31) — MỘT nguồn cho mọi nơi đọc khóa nhân vật / ảnh tham chiếu.

Vì sao: ở thế giới song song Kelly là DẠNG BÓNG MỜ PHÁT SÁNG (Kho #427, kind=style); prompt shot tả "ghost form" nhưng gói ảnh vẫn
khóa trang phục: ref Kelly áo vàng + "Identity lock — Kelly: … bright yellow zip-up track jacket …" + "The costume follows the profile
above" + "ignore any clothing or hair words in the scene text that contradict the reference images" → model bỏ dạng bóng mờ (V2V:
lúc bóng mờ lúc áo vàng). Lời miễn khóa trước đây chỉ đi qua BYĐ `ngoai_le` (core/lock_exceptions) của từng shot.

Cách khai (gọn, sửa được ngay ở mô tả Kho trên Dashboard, không cột / vai mới bắt buộc): một DÒNG trong mô tả mục Kho style
    Dạng của nhân vật: KELLY            (nhiều người: "KELLY, MAXIM"; tiếng Anh "Form of: KELLY" cũng nhận)
Style KHÔNG có dòng này → không phải dạng nhân vật → mọi thứ như cũ. Shot NHẮC tên / alias của style (khớp kiểu assets.name_spans, như
assets.atmosphere_refs; chữ thoại không tính) và người được khai có trong shot → người đó ở dạng này trong shot:
  - khóa giữ MẶT / TÓC / dáng người; bỏ khóa trang phục + màu áo (runner.lock_note, prompts.lock_text);
  - câu chung "ignore any clothing … words" không áp cho người đó; ảnh ref của người đó chỉ giữ mặt/tóc/dáng (assets.reference_note);
  - prompt nói rõ người đó ở dạng <tên dạng tiếng Anh> (+ câu tiếng Anh của mô tả Kho; chữ Việt không gửi model);
  - mục Kho có ảnh SẠCH vai `character_form` (đã duyệt, không HUD) → gửi làm ảnh dạng của người đó (assets.scene_references);
  - video (seedance_refs.prompt, adapters/clipai) đọc cùng dấu `form` trên ảnh ref.
Thuần dữ liệu, không gọi model.
"""
import re
from typing import Dict, List, Optional

ROLE = "character_form"            # vai ảnh Kho style: ảnh SẠCH (không HUD) của dạng nhân vật
_DECLARE = re.compile(r"^[ \t]*\[?[ \t]*(?:dạng của nhân vật|dang cua nhan vat|form of)[ \t]*:[ \t]*([^\]\n]+)", re.I | re.M)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
# Mệnh đề khóa nói về QUẦN ÁO / phụ kiện mặc trên người (tiếng Anh như hồ sơ chuẩn; vài chữ Việt cho khóa QC) — bỏ khi người ở dạng khác
_CLOTHES = re.compile(
    r"(?<!\w)(track ?suit|track jacket|track pants|jacket|coat|hoodie|sweater|cardigan|blazer|vest|shirt|t-shirt|tee|top|crop top|"
    r"blouse|bra|dress|gown|skirt|pants|trousers|jeans|shorts|leggings|tights|stockings|socks|shoes|sneakers|trainers|boots|heels|"
    r"sandals|zip|zip-up|zipper|sleeves?|collar|hood|stripes?|prints?|outfit|costume|clothes|clothing|garments?|uniform|cape|cloak|"
    r"scarf|gloves?|belt|choker|necklace|cap|hat|accessories|bodysuit|jumpsuit|overalls|mask|everyday look|OUTFIT image|áo|quần|giày|váy|trang phục)(?!\w)", re.I)


def declared(description: str) -> List[str]:
    """Tên nhân vật (VIẾT HOA) mà mục Kho khai là dạng của họ — [] khi không khai."""
    out: List[str] = []
    for m in _DECLARE.finditer(description or ""):
        for n in re.split(r"[,;/|]", m.group(1)):
            n = n.strip().strip(".").upper()
            if n and n not in out:
                out.append(n)
    return out


def english_name(asset: Dict) -> str:
    """Tên dạng gửi model: alias / tên đầu tiên không có chữ Việt ("ghost form"); không có thì tên bỏ dấu."""
    from .assets import fold, names_of
    from .seedance_refs import has_vietnamese
    return next((n.strip() for n in names_of(asset) if not has_vietnamese(n)), fold(asset.get("name") or "").strip().lower())


def english_words(asset: Dict, limit: int = 300) -> str:
    """Các câu KHÔNG có chữ Việt trong mô tả Kho (trừ dòng khai, thẻ [..]) — mô tả dạng gửi model."""
    from .seedance_refs import has_vietnamese
    text = _DECLARE.sub("", str(asset.get("description") or "").split("[AI đọc ảnh]")[0])
    keep = [s.strip() for s in _SENTENCE.split(text)
            if s.strip() and not has_vietnamese(s) and not s.strip().startswith("[")]
    return " ".join(keep)[:limit].strip()


def _shot_words(scene: Dict) -> List[str]:
    from .assets import _said_words, _without_spoken_lines
    return _said_words(" ".join([_without_spoken_lines(str(scene.get("text") or ""))]
                                + [str(scene.get(k) or "") for k in ("image_prompt", "location")]))


def for_shot(conn, project_id: int, scene: Optional[Dict], chosen: Optional[List[Dict]] = None) -> Dict[str, Dict]:
    """{TÊN NHÂN VẬT VIẾT HOA: {"form": tên tiếng Anh, "label": tên Kho, "words": câu tiếng Anh, "asset_id", "image": ảnh vai ROLE
    đã duyệt hoặc None}} cho người của shot đang ở một dạng shot nhắc tên. Không style nào khai dạng → {} (như cũ)."""
    from .assets import fold, name_spans, names_of, project_assets
    scene = scene or {}
    cast = {str(n).strip().upper() for n in scene.get("characters") or []}
    if not cast:
        return {}
    chosen = project_assets(conn, project_id) if chosen is None else chosen
    forms = [a for a in chosen if a.get("kind") == "style" and declared(a.get("description"))]
    if not forms:
        return {}
    words = _shot_words(scene)
    out: Dict[str, Dict] = {}
    for a in forms:
        if not any(len(fold(n)) >= 3 and name_spans(n, words) for n in names_of(a)):
            continue
        image = next((i for i in a.get("images") or [] if i.get("role") == ROLE and i.get("status") in (None, "approved")), None)
        for who in declared(a.get("description")):
            if who in cast and who in out and out[who]["asset_id"] != a["id"]:   # rà 17/10: never silent — the first style wins
                import logging
                logging.getLogger(__name__).warning("%s được khai dạng ở hai mục Kho style (%s, %s) trong cùng shot — dùng mục đầu",
                                                    who, out[who]["label"], a["name"])
            if who in cast and who not in out:
                out[who] = {"form": english_name(a), "label": a["name"], "words": english_words(a), "asset_id": a["id"],
                            "image": image}
    return out


def for_rows(conn, project_id: int, rows: List[Dict]) -> Dict[str, Dict]:
    """Dạng theo TỪNG shot của một clip nhiều shot (rà 17/10: gom setdefault áp dạng cả clip — #31 shot 30 Kelly bị bắn về thực tại
    mà câu vẫn khóa bóng mờ cả clip). {TÊN: for_shot(...) + "shots": [số thứ tự shot 1-based ở dạng], "all": dạng ở MỌI shot có người
    đó}. rows: [{"data": scene data}] theo thứ tự phim."""
    chosen = None
    out: Dict[str, Dict] = {}
    present: Dict[str, List[int]] = {}
    for i, r in enumerate(rows or [], 1):
        data = r["data"] or {}
        for n in data.get("characters") or []:
            present.setdefault(str(n).strip().upper(), []).append(i)
        if chosen is None:
            from .assets import project_assets
            chosen = project_assets(conn, project_id)
        for who, f in for_shot(conn, project_id, data, chosen).items():
            out.setdefault(who, dict(f, shots=[]))["shots"].append(i)
    for who, f in out.items():
        f["all"] = sorted(set(f["shots"])) == sorted(set(present.get(who, [])))
    return out


_LEAD = re.compile(r"^\s*(?:keep|never|always|no|not)\b[ \t:]*", re.I)    # tiền tố của CẢ mệnh đề ("never red jacket, blonde hair")
_CLOTHES_BODY = re.compile(r"(?<!\w)(skin-tight|skintight|face mask|face paint)(?!\w)", re.I)   # garment words that say skin / face
_BODY = re.compile(r"(?<!\w)(hair|hairstyle|haircut|bangs|fringe|ponytail|bun|braids?|face|eyes?|eyebrows?|skin|tóc|mặt|mắt)(?!\w)", re.I)


def without_clothes(body: str) -> str:
    """Chữ khóa của một người đã bỏ mọi mảnh (tách ';' / hết câu, rồi ',') nói về quần áo / phụ kiện mặc — giữ mặt, tóc, dáng, chiều
    cao. Rà 17/10: tiền tố keep/never của mệnh đề gắn lại vào phần còn lại (bỏ "never blue jacket" không được biến "never" thành mất →
    "short hair" thành yêu cầu ngược); mảnh nói về TÓC/MẶT/MẮT không bao giờ bỏ ("hair tied on top", "hair under a cap")."""
    keep = []
    for clause in str(body or "").split(";"):
        m = _LEAD.match(clause)                         # rà 17/10 vòng 2: the lead of a ';' clause covers EVERY sentence in it
        lead = m.group(0).strip() if m else ""          # ("never glasses. Beard" → "never glasses, Beard", never a bare "Beard")
        rest = clause[m.end():] if m else clause
        pieces = [x.strip().rstrip(".!?").strip() for x in re.split(r",|(?<=[.!?])\s+", rest)
                  if x.strip() and ((_BODY.search(x) and not _CLOTHES_BODY.search(x)) or not _CLOTHES.search(x))]
        txt = ", ".join(pieces).strip().rstrip(".").strip()
        if txt:
            keep.append(f"{lead} {txt}".strip())
    return "; ".join(keep)


def describe(f: Dict) -> str:
    return f"the {f['form']}" + (f" ({f['words'].rstrip('.')})" if f.get("words") else "")


def lock_en(name: str, f: Dict) -> str:
    """Câu cho model ảnh (runner.lock_note): người ở dạng này trong shot."""
    return (f"in THIS shot {name} is in {describe(f)} — keep only {name}'s face, hairstyle, hair colour and body build; the clothes, "
            f"their colours and the look of the body follow this form and the scene text, never {name}'s everyday outfit")


def ref_keep_en(label: str, f: Dict) -> str:
    """Phần 'giữ gì' của ảnh ref người ở dạng (assets.reference_note)."""
    return (f"same face, hairstyle and hair color, body build — NOT the clothes or their colours: in this shot {label} is in "
            f"{describe(f)}, so draw that form, not the outfit of this picture")


def note_vi(name: str, f: Dict) -> str:
    """Dòng khóa QC (prompts.lock_text)."""
    return (f"- **{name}** — ở dạng {f['label']} trong shot này: giữ mặt, tóc, dáng như ảnh tham chiếu; trang phục / màu áo / thân "
            "theo dạng đó và chữ của shot (đồ thường của hồ sơ KHÔNG áp dụng; thiếu áo của hồ sơ KHÔNG phải lỗi)")
