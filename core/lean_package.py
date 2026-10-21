"""V3.1 M2.10 (C-M210-DESIGN): gói gửi TỐI GIẢN — SHADOW. docs/KE_HOACH_GOI_GUI_TOI_GIAN_2026-10-21.md.

Từ gói THẬT đã gửi (`jobs.sent_package`) + BYĐ v2 của shot (đọc qua `shot_intent`) dựng một gói tối giản BÊN CẠNH: bộ ref tối thiểu (mỗi ref bỏ có
mã lý do), một dòng vai / ref (đánh số theo model), thân lệnh 2–4 câu, các câu GIỮ chép nguyên từ gói thật — rồi so sánh (độ dài, ref giữ / bỏ,
họ câu GIỮ / BỎ / ĐỔI, trường BYĐ không còn được nói). KHÔNG BAO GIỜ gửi; không đổi gói thật; không gọi mạng / tiền.

Cờ `lean_package` (TẮT, verified False): runner `_Runner._say_package` chỉ gọi `enabled()` rồi về khi TẮT. Công cụ chạy tay trên gói đã gửi:
`tools/lean_package_shadow.py` (CSDL mở chỉ đọc). Hàm `shadow()` thuần, không bao giờ ném lỗi (lỗi → báo cáo có khóa `loi`)."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

FLAG = "lean_package"
DIAG_CODE = "lean_package"
V = 1

IMAGE_TYPES = ("anh_1_nguoi", "anh_nhieu_nguoi", "anh_co_vat", "anh_doi_dang")
VIDEO_TYPES = ("video_khung_dau", "video_dau_cuoi", "video_ref_hanh_dong", "video_khong_khung_dau")

# Trần TỐI GIẢN (≤ trần cứng của model — data/provider_rules.json, knowledge/reference_assets_prompting.md). Kling: có video ≤ 4 ảnh (tài liệu
# B), có khung đầu → element ≤ 3. Seedance 2.5 cứng 30 ảnh, tài liệu khuyên 1–8 chủ thể. Ảnh Deepix gpt-image cứng 16.
CAPS = {"image": 6, "seedance": 8, "kling": 7, "kling_video_ref": 4, "kling_first_frame_people": 3, "generic": 8}
# Vượt trần → bỏ theo thứ tự này (thứ ít cần nhất trước); còn vượt → chỉ cảnh báo, không bỏ người / khung / nền.
REMOVE_ORDER = ("atmosphere_sky", "previous_scene", "object", "character_form")
# Thứ tự ref trong gói tối giản: khung → nền → người → dạng → vật → cảnh trước → trời → video.
ORDER = ("start_frame", "last_frame", "place_render", "location", "landmark", "character", "character_form", "object",
         "previous_scene", "atmosphere_sky", "reference_video")
PLACE_ROLES = ("place_render", "location", "landmark", "atmosphere_place")
KNOWN_ROLES = set(ORDER) | {"atmosphere_place"}

# Họ câu của builder hiện tại → quyết (GIU / BO / DOI) + lý do — bảng mục 4 tài liệu. Mẫu khớp ĐẦU câu (hoặc trong câu với `in`).
SENTENCE_FAMILIES: Dict[str, Dict] = {
    "plate_lead": {"re": r"^Image 1 is (this shot's 3D render|the EXACT background)", "quyet": "DOI", "ly_do": "→ 1 dòng vai nền (nói 4 lần một ý)"},
    "ref_grouped": {"re": r"^Reference images are attached", "quyet": "BO", "ly_do": "không mang thông tin"},
    "role_line": {"re": r"^(Images? \d+(/\d+)*|@Image \d+|<<<image_\d+>>>) (is|are|show)", "quyet": "DOI", "ly_do": "→ dòng vai ngắn (lấy gì / không lấy gì)"},
    "swap_rule": {"re": r"^Each person keeps ONLY", "quyet": "DOI", "ly_do": "→ 1 câu 'never swap' khi ≥ 2 người"},
    "different_people": {"re": r"^The people are different individuals", "quyet": "DOI", "ly_do": "gộp vào câu 'never swap'"},
    "refs_not_pose": {"re": r"^The reference images set who each person is", "quyet": "BO", "ly_do": "dòng vai đã nói 'not pose, camera'"},
    "form_exception": {"re": r"^Exception: .* special form", "quyet": "BO", "ly_do": "ảnh dạng mang (dòng vai dạng)"},
    "anchor_rule": {"re": r"^Before drawing, pick ONE", "quyet": "BO", "ly_do": "trùng dòng vai — thử A/B"},
    "exaggerate": {"re": r"^If two people would otherwise look similar", "quyet": "BO", "ly_do": "trùng dòng vai — thử A/B"},
    "place_decides": {"re": r"^(Scene: )?The place is decided by the 3D render", "quyet": "BO", "ly_do": "trùng dòng vai nền"},
    "take_from_text": {"re": r"^Take from the text only", "quyet": "BO", "ly_do": "trùng dòng vai nền"},
    "style": {"re": r"^(Render style|Style lock):", "quyet": "GIU", "ly_do": "giữ câu đầu: model hay trôi phong cách"},
    "style_more": {"re": r"^Stylized mobile-game proportions", "quyet": "BO", "ly_do": "ảnh mang"},
    "framing": {"re": r"^Framing:", "quyet": "DOI", "ly_do": "sinh từ BYĐ may"},
    "weapon_scale": {"re": r"^Weapon scale:", "quyet": "GIU", "ly_do": "ảnh vật không cho cỡ so với người"},
    "fix": {"re": r"^Fix:", "quyet": "GIU", "ly_do": "sửa của người / QC"},
    "setting": {"re": r"^Setting:", "quyet": "BO", "ly_do": "không mang thông tin"},
    "background_exact": {"re": r"^Background: exactly the 3D render", "quyet": "BO", "ly_do": "trùng dòng vai nền"},
    "real_sizes": {"re": r"^Real sizes:", "quyet": "BO", "ly_do": "trùng câu đo M3.3"},
    "plate_measure": {"re": r"^Background — measured on the 3D map", "quyet": "BO", "ly_do": "ảnh nền mang"},
    "draw_bg_only": {"re": r"^Draw the background only as Image 1", "quyet": "BO", "ly_do": "trùng dòng vai nền"},
    "camera_scale": {"re": r"^Camera and scale, measured", "quyet": "GIU", "ly_do": "cỡ người trong khung — ảnh không nói được"},
    "identity_lock": {"re": r"^Identity lock —", "quyet": "BO", "ly_do": "ảnh người mang; chữ trái ảnh kéo nhau"},
    "costume_profile": {"re": r"^The costume of .* follows the profile", "quyet": "BO", "ly_do": "ảnh người mang"},
    "focus": {"re": r"^Background in focus", "quyet": "GIU", "ly_do": "lỗi DOF đã gặp"},
    "not_in_frame": {"re": r"NOT in this frame", "in": True, "quyet": "GIU", "ly_do": "sinh lại từ BYĐ khong_duoc_co"},
    "back_view": {"re": r"stays with the back to the camera", "in": True, "quyet": "GIU", "ly_do": "sinh lại từ BYĐ thay=lung"},
    "hint_only": {"re": r"only hinted", "in": True, "quyet": "GIU", "ly_do": "an toàn nội dung"},
    "annotation": {"re": r"^Any white banner or red mark", "quyet": "GIU", "ly_do": "ảnh tham chiếu có nhãn"},
    "never_mark": {"re": r"^Never draw a plus sign", "quyet": "GIU", "ly_do": "ảnh tham chiếu có nhãn"},
    "same_place": {"re": r"^Same place, same light", "quyet": "BO", "ly_do": "không mang thông tin"},
    "buildings_keep": {"re": r"^The buildings and the landmark behind", "quyet": "BO", "ly_do": "khung đầu mang"},
    "plate_view": {"re": r"only a reference for the shape and material", "in": True, "quyet": "BO", "ly_do": "ref nơi chốn bỏ khi có khung đầu"},
    "storyboard_frame": {"re": r"is the storyboard frame of Shot", "in": True, "quyet": "DOI", "ly_do": "→ dòng vai khung đầu"},
    "multi_shot_head": {"re": r"^One clip with \d+ shots", "quyet": "GIU", "ly_do": "cấu trúc clip nhiều shot"},
    "ignore_words": {"re": r"ignore any clothing or hair words", "in": True, "quyet": "BO", "ly_do": "thân lệnh mới không tả áo / tóc"},
}
CARRY = ("style", "weapon_scale", "fix", "camera_scale", "focus", "hint_only", "annotation", "never_mark", "multi_shot_head")

CO_EN = {"EWS": "Extreme wide shot", "WS": "Wide shot", "GAME_TPS": "Third-person game view behind the shoulder",
         "MLS": "Medium long shot", "MS": "Medium shot", "MCU": "Medium close-up", "CU": "Close-up", "ECU": "Extreme close-up"}
DO_CAO_EN = {"ngang": "eye-level camera", "thap": "low camera", "cao": "high camera", "tren_dau": "overhead camera"}
GOC_EN = {"cui": "looking down", "ngua": "looking up"}
MOVE_EN = {"dung_yen": "static", "lui": "slowly pulling back", "tien": "slowly pushing in"}
CACH_EN = {"cam": "holds it", "deo": "wears it", "dat": "it lies nearby", "nem": "throws it"}
TU_THE_EN = {"dung": "standing", "ngoi": "sitting", "quy": "kneeling", "bo": "crawling",
             "nga_ngua": "fallen on the back, propped on the hands", "nam": "lying down"}
SILENT_WHY = {"truyen": "chữ hiểu ý (TEXT_ONLY) — không gửi", "noi_chon": "ảnh nền / khung đầu mang",
              "thanh_phan[].vung": "chưa nói — vị trí do ảnh nền / khung đầu (rủi ro nhiều người)",
              "thanh_phan[].kho_id": "ảnh người mang", "vat[].kho_id": "ảnh vật mang", "vat[].bien_the": "chưa kiểm được (M2.3)",
              "khung": "ảnh nền / khung đầu mang", "ngoai_le": "chưa dùng — rủi ro: điều trái có chủ đích không được nói",
              "am_chu.nhac": "âm thanh — không thuộc gói hình", "am_chu.sfx": "âm thanh — không thuộc gói hình",
              "am_chu.popup": "dựng — không thuộc gói hình", "am_chu.phu_de": "dựng — không thuộc gói hình"}
SKIP_FIELDS = ("shot", "byd_v", "_p")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


# ---- tiện ích ----------------------------------------------------------------------------------------------------------------
def fold(text) -> str:
    """Tên so khớp: bỏ dấu, HOA, ký tự lạ → cách ('YÊU NỮ TÀ LINH DẠNG 1' == 'YEU_NU_TA_LINH_DANG_1')."""
    s = unicodedata.normalize("NFD", str(text or "").replace("đ", "d").replace("Đ", "D"))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", s).upper().split())


def show(name) -> str:
    return " ".join(str(name or "").replace("_", " ").split())


def family(kind: str, model: Optional[str]) -> str:
    m = str(model or "").lower()
    if "kling" in m:
        return "kling"
    if "seedance" in m:
        return "seedance"
    if kind == "image":
        return "image"
    return "generic"


def tag(fam: str, n: int, video: bool = False) -> str:
    if video:
        return {"kling": f"<<<video_{n}>>>", "seedance": f"@Video {n}"}.get(fam, f"Video {n}")
    return {"kling": f"<<<image_{n}>>>", "seedance": f"@Image {n}"}.get(fam, f"Image {n}")


def sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"@<(])|\n+", str(text or ""))
    return [p.strip() for p in parts if p and p.strip()]


def _byd(data) -> Tuple[Optional[Dict], str]:
    from . import shot_intent
    b = shot_intent.byd_of(data)
    if b is None:
        return None, "thieu"
    return b, "byd_v2" if shot_intent.version(b) == shot_intent.BYD_V else "byd_v1"


def _cast(byd: Optional[Dict]) -> Dict[str, Dict]:
    """{tên fold: mục thanh_phan} cho người / thứ có mặt (vai khác khong_duoc_co)."""
    out = {}
    for c in (byd or {}).get("thanh_phan") or []:
        if isinstance(c, dict) and c.get("vat") and c.get("vai") != "khong_duoc_co":
            out[fold(c["vat"])] = c
    return out


def _absent(byd: Optional[Dict]) -> List[str]:
    return [show(c["vat"]) for c in (byd or {}).get("thanh_phan") or []
            if isinstance(c, dict) and c.get("vat") and c.get("vai") == "khong_duoc_co"]


def _things(byd: Optional[Dict]) -> Optional[Dict[str, Dict]]:
    """{tên fold: mục vat} — None khi BYĐ không có nhóm vat (không lọc vật)."""
    if not isinstance(byd, dict) or "vat" not in byd:
        return None
    from . import shot_intent
    out = {}
    for v in shot_intent.vat_items(byd):
        if isinstance(v, dict) and v.get("vat"):
            out[fold(v["vat"])] = v
    return out


def _form_by_beat(c: Optional[Dict]) -> bool:
    return isinstance((c or {}).get("dang"), dict)


def _form_name(c: Optional[Dict]) -> Optional[str]:
    d = (c or {}).get("dang")
    if isinstance(d, dict):
        d = d.get("ket_thuc") or d.get("dinh") or d.get("bat_dau")
    if isinstance(d, list):
        d = d[0] if d else None
    return show(d) if d else None


def _back_only(c: Optional[Dict]) -> bool:
    views = [v.strip() for v in str((c or {}).get("thay") or "").split("|") if v.strip()]
    return views == ["lung"]


# ---- phân loại + chọn ref ------------------------------------------------------------------------------------------------------
def classify(kind: str, refs: List[Dict], byd: Optional[Dict], prev_byd: Optional[Dict] = None) -> Tuple[str, List[str]]:
    """(loại shot chính, thẻ phụ). Thẻ: nhieu_nguoi, co_vat, doi_dang, doi_nen, nhieu_nguoi_3."""
    roles = [r.get("role") for r in refs]
    cast = _cast(byd)
    people = len(cast) if byd else len({fold(r.get("label")) for r in refs if r.get("role") == "character"})
    tags = []
    if people >= 2:
        tags.append("nhieu_nguoi")
    if people >= 3:
        tags.append("nhieu_nguoi_3")
    things = _things(byd)
    if (things if things is not None else [r for r in refs if r.get("role") == "object"]):
        tags.append("co_vat")
    if any(c.get("dang") not in (None, "", [], {}) for c in cast.values()) or "character_form" in roles:
        tags.append("doi_dang")
    kho = ((byd or {}).get("noi_chon") or {}).get("kho_id")
    pkho = ((prev_byd or {}).get("noi_chon") or {}).get("kho_id") if isinstance(prev_byd, dict) else None
    if kho is not None and pkho is not None and kho != pkho:
        tags.append("doi_nen")
    if kind == "video":
        if "reference_video" in roles:
            main = "video_ref_hanh_dong"
        elif "last_frame" in roles:
            main = "video_dau_cuoi"
        elif "start_frame" in roles:
            main = "video_khung_dau"
        else:
            main = "video_khong_khung_dau"
    else:
        main = ("anh_doi_dang" if "doi_dang" in tags else "anh_nhieu_nguoi" if "nhieu_nguoi" in tags
                else "anh_co_vat" if "co_vat" in tags else "anh_1_nguoi")
    return main, tags


def select(kind: str, refs: List[Dict], byd: Optional[Dict], model: Optional[str]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """(giữ, bỏ, cảnh báo). Mỗi mục giữ / bỏ: {i (vị trí trong gói thật), role, label, sha256, ly_do}. Không đoán vai lạ."""
    fam = family(kind, model)
    roles = [r.get("role") for r in refs]
    first = kind == "video" and "start_frame" in roles
    cast = _cast(byd)
    things = _things(byd)
    trong_nha = ((byd or {}).get("noi_chon") or {}).get("trong_nha") is True
    keep: List[Dict] = []
    drop: List[Dict] = []
    warns: List[Dict] = []
    seen_sha: Dict[str, int] = {}
    seen_key: set = set()
    has_place = any(r.get("role") == "place_render" for r in refs)
    if byd is None:
        warns.append({"ma": "thieu_byd", "loi": "shot chưa có BYĐ — giữ mọi người / vật có ảnh (chỉ bỏ trùng), không lọc theo khung"})

    def item(i, r, why):
        return {"i": i, "param": r.get("param"), "role": r.get("role"), "label": r.get("label"), "path": r.get("path"),
                "sha256": r.get("sha256"), "ly_do": why}

    for i, r in enumerate(refs):
        role, label, sha = r.get("role"), r.get("label"), r.get("sha256")
        name = fold(label)
        if sha and sha in seen_sha:
            drop.append(item(i, r, "trung_sha"))
            continue
        why = None
        if role in ("start_frame", "last_frame"):
            why = "khung_dau" if role == "start_frame" else "khung_cuoi"
        elif role == "reference_video":
            why = "hanh_dong_tu_video"
        elif role in PLACE_ROLES:
            if first:
                drop.append(item(i, r, "khung_dau_mang_noi_chon"))
                continue
            if ("place" in seen_key) or (role != "place_render" and has_place):
                drop.append(item(i, r, "nen_rong_trung" if role == "place_render" else "trung_nen"))
                continue
            seen_key.add("place")
            why = "nen_chinh"
        elif role == "character":
            c = cast.get(name)
            if byd is not None and c is None:
                drop.append(item(i, r, "khong_trong_khung"))
                continue
            if ("character", name) in seen_key:
                drop.append(item(i, r, "goc_thu_2"))
                continue
            if first and _back_only(c):
                drop.append(item(i, r, "chi_thay_lung"))
                continue
            seen_key.add(("character", name))
            why = "dinh_danh"
        elif role == "character_form":
            c = cast.get(name)
            if byd is not None and c is None:
                drop.append(item(i, r, "khong_trong_khung"))
                continue
            if ("character_form", name) in seen_key:
                drop.append(item(i, r, "goc_thu_2"))
                continue
            if first and not _form_by_beat(c):
                drop.append(item(i, r, "khung_dau_da_o_dang"))
                continue
            seen_key.add(("character_form", name))
            why = "bien_hinh" if _form_by_beat(c) else "dang"
        elif role == "object":
            v = (things or {}).get(name)
            if things is not None and v is None:
                drop.append(item(i, r, "vat_khong_trong_byd"))
                continue
            if ("object", name) in seen_key:
                drop.append(item(i, r, "goc_thu_2"))
                continue
            if first and v is not None and v.get("cach") in ("dat", "deo"):
                drop.append(item(i, r, "khung_dau_mang_vat"))
                continue
            seen_key.add(("object", name))
            why = "vat_dong" if first else "vat"
        elif role == "atmosphere_sky":
            if trong_nha:
                drop.append(item(i, r, "trong_nha"))
                continue
            if "sky" in seen_key:
                drop.append(item(i, r, "goc_thu_2"))
                continue
            seen_key.add("sky")
            why = "bau_troi"
        elif role == "previous_scene":
            if "prev" in seen_key or first:
                drop.append(item(i, r, "goc_thu_2" if "prev" in seen_key else "khung_dau_mang_noi_chon"))
                continue
            seen_key.add("prev")
            why = "noi_canh_truoc"
        else:
            why = "vai_khong_ro"
            warns.append({"ma": "vai_khong_ro", "loi": f"ref #{i + 1} vai '{role}' ({label or 'không nhãn'}) — giữ nguyên, không đoán vai"})
        if sha:
            seen_sha[sha] = i
        keep.append(item(i, r, why))
    rank = {role: n for n, role in enumerate(ORDER)}
    keep.sort(key=lambda x: (rank.get(x["role"], len(ORDER)), x["i"]))
    _cap(fam, kind, keep, drop, warns)
    return keep, drop, warns


def _cap(fam: str, kind: str, keep: List[Dict], drop: List[Dict], warns: List[Dict]) -> None:
    has_video = any(k["role"] == "reference_video" for k in keep)
    if fam == "kling":
        cap = CAPS["kling_video_ref"] if has_video else CAPS["kling"]
        if any(k["role"] == "start_frame" for k in keep):
            people = [k for k in keep if k["role"] == "character"]
            for k in people[CAPS["kling_first_frame_people"]:]:
                keep.remove(k)
                drop.append(dict(k, ly_do="vuot_tran_model"))
    else:
        cap = CAPS.get(fam, CAPS["generic"])
    images = lambda: [k for k in keep if k["role"] != "reference_video"]   # noqa: E731
    for role in REMOVE_ORDER:
        while len(images()) > cap:
            hit = [k for k in keep if k["role"] == role]
            if not hit:
                break
            keep.remove(hit[-1])
            drop.append(dict(hit[-1], ly_do="vuot_tran_model"))
    if len(images()) > cap:
        warns.append({"ma": "vuot_tran_con_lai", "loi": f"còn {len(images())} ảnh > trần tối giản {cap} ({fam}) — không bỏ khung / nền / người"})


# ---- chữ ---------------------------------------------------------------------------------------------------------------------
def role_lines(kind: str, keep: List[Dict], byd: Optional[Dict], model: Optional[str]) -> List[str]:
    fam = family(kind, model)
    cast = _cast(byd)
    things = _things(byd) or {}
    form_of = {fold(k["label"]): n for n, k in enumerate(keep, 1) if k["role"] == "character_form"}
    out, nimg, nvid = [], 0, 0
    for k in keep:
        role, name = k["role"], show(k.get("label")) or "this"
        if role == "reference_video":
            nvid += 1
            out.append(f"{tag(fam, nvid, True)} gives only the movement and timing — not its people, outfits, place, camera or HUD text.")
            continue
        nimg += 1
        t = tag(fam, nimg)
        c = cast.get(fold(k.get("label")))
        if role == "start_frame":
            line = (f"{t} is the first frame (作为首帧): start exactly on it — its framing, place and the people's positions."
                    if fam == "seedance" else f"{t} is the first frame: start exactly on it — its framing, place and the people's positions.")
        elif role == "last_frame":
            line = f"{t} is the last frame: end exactly on it."
        elif role in PLACE_ROLES:
            line = f"{t} is the exact background (3D render from this camera): keep its layout and sizes; draw the people into it."
        elif role == "character":
            fn = form_of.get(fold(k.get("label")))
            if fn is not None or (c and c.get("dang") not in (None, "", [], {})):
                line = f"{t} is {name}: face, hair and build only — NOT the clothes or their colours."
            else:
                line = f"{t} is {name}: face, hair, outfit and build — not the pose, camera or background."
        elif role == "character_form":
            form = _form_name(c) or "special"
            line = f"{t} is {name} in the {form} form: body surface, colours, glow and transparency — not the hair, pose or camera."
        elif role == "object":
            v = things.get(fold(k.get("label"))) or {}
            who = f" ({show(v['nguoi'])} {CACH_EN.get(v.get('cach'), 'has it')})" if v.get("nguoi") else ""
            line = f"{t} is the object {name}{who}: exact shape and colours."
        elif role == "atmosphere_sky":
            line = f"{t} is the sky only: draw the sky like this wherever it shows — nothing else from it."
        elif role == "previous_scene":
            line = f"{t} is the previous shot: same people, outfits and light — not its framing."
        else:
            line = f"{t} is a reference ({k.get('role') or 'unknown role'}{', ' + name if k.get('label') else ''})."
        out.append(line)
    return out


def _camera(byd: Optional[Dict]) -> Optional[str]:
    may = (byd or {}).get("may")
    if not isinstance(may, dict) or not may.get("co"):
        return None
    bits = [CO_EN.get(str(may["co"]), str(may["co"]))]
    if may.get("do_cao") in DO_CAO_EN:
        bits.append(DO_CAO_EN[may["do_cao"]])
    if may.get("goc") in GOC_EN:
        bits.append(GOC_EN[may["goc"]])
    mv = may.get("chuyen_dong")
    mv = mv.get("kieu") if isinstance(mv, dict) else mv
    if mv in MOVE_EN:
        bits.append(MOVE_EN[mv])
    return ", ".join(bits) + "."


def _end_states(byd: Optional[Dict], only_end: bool) -> Optional[str]:
    bits = []
    for h in (byd or {}).get("hanh_dong") or []:
        if not isinstance(h, dict) or not h.get("ai"):
            continue
        a = TU_THE_EN.get(((h.get("bat_dau") or {}).get("tu_the")) or "")
        b = TU_THE_EN.get(((h.get("ket_thuc") or {}).get("tu_the")) or "")
        if only_end and b:
            bits.append(f"{show(h['ai'])} ends {b}")
        elif a and b and a != b:
            bits.append(f"{show(h['ai'])} goes from {a} to {b}")
        elif a:
            bits.append(f"{show(h['ai'])} is {a}")
    return ("; ".join(bits) + ".") if bits else None


def body(kind: str, byd: Optional[Dict], scene_text: str, has_video: bool, many: bool, model: Optional[str]) -> Tuple[List[str], List[str], List[Dict]]:
    """(thân lệnh 2–4 câu, trường BYĐ đã nói, cảnh báo)."""
    said, warns, out = [], [], []
    cam = _camera(byd)
    if cam:
        out.append(cam)
        said += [f"may.{k}" for k in ("co", "do_cao", "goc", "chuyen_dong") if ((byd or {}).get("may") or {}).get(k) not in (None, "")]
    if has_video:
        fam = family(kind, model)
        end = _end_states(byd, only_end=True)
        out.append(f"Follow {tag(fam, 1, True)} for the movement and its timing; do not change it." + (f" {end}" if end else ""))
        if end:
            said.append("hanh_dong")
    else:
        sc = sentences(scene_text)
        if sc:
            act = " ".join(sc[:2])
            words = act.split()
            if len(words) > 60:
                act = " ".join(words[:60]).rstrip(",;") + "."
                warns.append({"ma": "cat_chu_canh", "loi": "chữ shot dài — thân lệnh lấy 60 từ đầu (2 câu)"})
            out.append(act)
        else:
            st = _end_states(byd, only_end=False)
            if st:
                out.append(st)
                said.append("hanh_dong")
            else:
                warns.append({"ma": "thieu_chu_canh", "loi": "không có chữ shot / hanh_dong BYĐ — thân lệnh thiếu hành động"})
    lines = []
    for t in ((byd or {}).get("am_chu") or {}).get("thoai") or []:
        if isinstance(t, dict) and str(t.get("cau") or "").strip():
            lines.append(f'{show(t.get("ai")) or "Someone"} says in Vietnamese: "{str(t["cau"]).strip()}"')
    if lines:
        out.append("; ".join(lines) + "; the others keep their mouths closed.")
        said.append("am_chu.thoai")
    if many:
        out.append("The people are different individuals: never swap faces, hair or outfits between them.")
    return out[:4], said, warns


def families(prompt: str) -> Tuple[List[Dict], Dict[str, List[str]]]:
    """(họ câu có trong prompt thật [{ma, quyet, ly_do, n, chars}], {mã: [câu]})."""
    found: Dict[str, Dict] = {}
    text: Dict[str, List[str]] = {}
    for s in sentences(prompt):
        hit = "khac"
        for ma, f in SENTENCE_FAMILIES.items():
            if (re.search(f["re"], s) if f.get("in") else re.match(f["re"], s)):
                hit = ma
                break
        f = SENTENCE_FAMILIES.get(hit, {"quyet": "?", "ly_do": "chữ shot / câu khác — thân lệnh thay"})
        row = found.setdefault(hit, {"ma": hit, "quyet": f["quyet"], "ly_do": f["ly_do"], "n": 0, "chars": 0})
        row["n"] += 1
        row["chars"] += len(s)
        text.setdefault(hit, []).append(s)
    return list(found.values()), text


def _present(byd: Optional[Dict]) -> List[str]:
    out: List[str] = []

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                if not path and k in SKIP_FIELDS:
                    continue
                walk(x, f"{path}.{k}" if path else k)
        elif isinstance(v, list):
            if v and all(isinstance(x, dict) for x in v):
                for x in v:
                    walk(x, path + "[]")
            elif v:
                out.append(path)
        elif v not in (None, ""):
            out.append(path)
    walk(byd or {}, "")
    return list(dict.fromkeys(out))


def _silent_why(field: str) -> str:
    for k in sorted(SILENT_WHY, key=len, reverse=True):
        if field == k or field.startswith(k + ".") or field.startswith(k + "["):
            return SILENT_WHY[k]
    return "chưa dùng trong gói tối giản"


# ---- dựng + so sánh ------------------------------------------------------------------------------------------------------------
def build(pkg: Dict, data: Optional[Dict], kind: str, prev_data: Optional[Dict] = None) -> Dict:
    """Báo cáo shadow từ gói thật (dict) + scenes.data của shot. Không gửi, không ghi gì."""
    refs = [r for r in pkg.get("refs") or [] if isinstance(r, dict)]
    model = pkg.get("model")
    byd, prov = _byd(data)
    prev_byd = _byd(prev_data)[0] if prev_data else None
    loai, tags = classify(kind, refs, byd, prev_byd)
    keep, drop, warns = select(kind, refs, byd, model)
    lines = role_lines(kind, keep, byd, model)
    has_video = any(k["role"] == "reference_video" for k in keep)
    people = [k for k in keep if k["role"] == "character"]
    many = len(_cast(byd)) >= 2 if byd else len(people) >= 2
    scene_text = str((data or {}).get("image_prompt" if kind == "image" else "action") or "")
    core_body, said, w2 = body(kind, byd, scene_text, has_video, many, model)
    warns += w2
    if "nhieu_nguoi_3" in tags:
        warns.append({"ma": "nhieu_nguoi_3", "loi": "≥ 3 người: 1 ảnh / người — cần khung đầu đủ người (luật 12); A/B trước khi bật"})
    real_prompt = str(pkg.get("prompt") or "")
    fams, fam_text = families(real_prompt)
    if "multi_shot_head" in fam_text:
        warns.append({"ma": "nhieu_shot", "loi": "clip nhiều shot — gói tối giản chỉ dựa BYĐ shot đầu nhóm (job.scene_id)"})
    safety: List[str] = []
    absent = _absent(byd)
    if absent:
        safety.append(f"{', '.join(absent)} {'is' if len(absent) == 1 else 'are'} NOT in this frame — do not draw them, not even in the background.")
        said.append("thanh_phan[].vai")
    elif "not_in_frame" in fam_text:
        safety += fam_text["not_in_frame"]
    backs = [show(c["vat"]) for c in _cast(byd).values() if _back_only(c)]
    if backs:
        safety.append(f"{', '.join(backs)} stays with the back to the camera for the whole shot.")
        said.append("thanh_phan[].thay")
    elif "back_view" in fam_text:
        safety += fam_text["back_view"]
    has_object = any(k["role"] == "object" for k in keep)
    for ma in CARRY:
        if ma == "weapon_scale" and not has_object:
            continue
        got = fam_text.get(ma) or []
        safety += got[:1] if ma == "style" else got
    names = {"character": "thanh_phan[].vat", "character_form": "thanh_phan[].dang", "object": "vat[].vat"}
    for k in keep:
        if k["role"] in names:
            said.append(names[k["role"]])
        if k["role"] == "object":
            said += ["vat[].nguoi", "vat[].cach"]
    prompt = " ".join(lines + core_body + safety)
    present = _present(byd)
    said = list(dict.fromkeys(said))
    da_noi = [f for f in present if f in said or any(f.startswith(s + ".") or f.startswith(s + "[") for s in said)]
    silent = [{"truong": f, "ly_do": _silent_why(f)} for f in present if f not in da_noi]
    real_chars, gon_chars = len(real_prompt), len(prompt)
    return {
        "v": V, "kind": kind, "model": model, "family": family(kind, model), "loai": loai, "the": tags,
        "that": {"chars": real_chars, "words": len(real_prompt.split()), "refs": len(refs)},
        "gon": {"chars": gon_chars, "words": len(prompt.split()), "refs": len(keep)},
        "ty_le_chars": round(gon_chars / real_chars, 3) if real_chars else None,
        "ref_giu": keep, "ref_bo": drop, "cau_cu": fams,
        "phu_byd": {"provenance": prov, "da_noi": da_noi, "khong_con_noi": silent},
        "canh_bao": warns,
        "goi_gon": {"note": "gói tối giản SHADOW — KHÔNG gửi, chỉ để so sánh (M2.10)", "prompt": prompt,
                    "refs": [{k: r[k] for k in ("param", "role", "label", "path", "sha256")} for r in keep],
                    "role_lines": lines, "body": core_body, "cau_giu": safety},
    }


def shadow(pkg_text, data: Optional[Dict], *, kind: str, job_id=None, prev_data: Optional[Dict] = None) -> Dict:
    """build() từ chữ JSON của jobs.sent_package; KHÔNG BAO GIỜ ném lỗi — lỗi → {job_id, kind, loi}."""
    try:
        pkg = json.loads(pkg_text) if isinstance(pkg_text, (str, bytes)) else pkg_text
        if not isinstance(pkg, dict):
            raise ValueError("gói gửi trống / không phải bảng JSON")
        rep = build(pkg, data if isinstance(data, dict) else {}, kind, prev_data if isinstance(prev_data, dict) else None)
    except Exception as e:  # noqa: BLE001 - shadow: said in the report, never stops anything
        return {"v": V, "job_id": job_id, "kind": kind, "loi": f"{type(e).__name__}: {e}"}
    rep["job_id"] = job_id
    return rep


def note(rep: Dict, path: Optional[str] = None) -> str:
    """Một dòng ⚙ Chẩn đoán (tiếng Việt, có số liệu)."""
    if rep.get("loi"):
        return f"gói tối giản (shadow, KHÔNG gửi): không dựng được — {rep['loi']}"
    bo = {}
    for r in rep["ref_bo"]:
        bo[r["ly_do"]] = bo.get(r["ly_do"], 0) + 1
    why = ", ".join(f"{k} ×{n}" for k, n in bo.items()) or "không bỏ ref"
    return (f"gói tối giản (shadow, KHÔNG gửi) [{rep['loai']}]: prompt {rep['that']['chars']}→{rep['gon']['chars']} ký tự, ref "
            f"{rep['that']['refs']}→{rep['gon']['refs']} ({why}); BYĐ không còn nói {len(rep['phu_byd']['khong_con_noi'])} trường"
            + (f"; tệp {path}" if path else ""))


def out_path(data_dir: str, project_id, job_id) -> str:
    return os.path.join(str(data_dir), "lean_package", str(project_id), f"job_{job_id}.json")


def write(rep: Dict, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def shadow_job(conn, data_dir: str, job) -> Tuple[Dict, str]:
    """Runner (cờ BẬT): đọc gói ĐÃ ghi của job + scenes.data + BYĐ shot trước (cùng dự án, idx liền trước) → báo cáo + tệp."""
    row = conn.execute("SELECT sent_package, type FROM jobs WHERE id=?", (job["id"],)).fetchone()
    data, prev = _scene_and_prev(conn, job["scene_id"])
    kind = "image" if (row and row[1] == "image_gen") else "video"
    rep = shadow(row[0] if row else None, data, kind=kind, job_id=job["id"], prev_data=prev)
    return rep, write(rep, out_path(data_dir, job["project_id"], job["id"]))


def _scene_and_prev(conn, scene_id) -> Tuple[Dict, Optional[Dict]]:
    def load(raw):
        try:
            d = json.loads(raw) if raw else {}
        except ValueError:
            d = {}
        return d if isinstance(d, dict) else {}
    row = conn.execute("SELECT project_id, idx, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if not row:
        return {}, None
    prev = conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx<? ORDER BY idx DESC LIMIT 1", (row[0], row[1])).fetchone()
    return load(row[2]), (load(prev[0]) if prev else None)
