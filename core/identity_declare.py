"""Khóa nhận diện bằng chữ (A18 / A20 kế hoạch kiểm soát, docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md) — hàm THUẦN, K0b chạy khô.

A20 tầng "chữ": mỗi món trang phục / nhận diện = tên món + màu chủ đạo (1–2) + ≤ 1 dấu hiệu. Ô `khai_bao_chu` của hồ sơ Kho (K0b phần 2
tạo schema `validate_khai_bao_chu`, K1a điền) được `declare_from_profile` ĐỌC trước; món chưa có ô → `declare_from_text` TẠM SUY từ
`must_keep` (tiếng Anh) hoặc mô tả Kho (tiếng Việt), mang `nguon: "suy"` + VÀNG nhắc điền một lần. `color_conflicts` = mô tả Kho ↔ khai
báo lệch màu chính (VÀNG). `check(decl, prompt, view)` so với chữ prompt: mỗi món → co / thieu / thieu_mau / sai_mau / khong_can.
Họa tiết (sọc, sao, viền…) KHÔNG kiểm ở chữ (A20: thuộc ảnh tham chiếu + QC sau gen) — chỉ ghi vào `hoa_tiet`.

LỌC THEO BYĐ (thẩm định 4 lỗ hổng #1 — chạy khô #24 đỏ 37 món / 7 shot mà QC thấy trang phục đúng): `byd_view(byd, vat)` lấy cỡ cảnh
(`may.co`), mặt/lưng (`thanh_phan[].thay`) và có-trong-khung của nhân vật; `check(..., view=…)` chỉ đòi chữ cho món NHÌN THẤY được:
món nằm dưới phần thân mà cỡ cảnh chứa (BODY_FROM_TOP so `core/stage_grid.FRAMING`: MCU không đòi giày / đai), quay lưng hẳn
(`thay` = lung) không đòi món chỉ thấy mặt trước (FRONT_ONLY: mặt nạ, choker, mặt, mắt), nhân vật không có trong khung / `khong_duoc_co`
không đòi gì. Món bị lọc → `trang_thai: "khong_can"` + `ly_do` (không im lặng). Món không biết vùng thân / cỡ cảnh không biết → VẪN đòi,
kèm `khong_loc` nói vì sao không lọc được.

MỨC (A18 kế hoạch `docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` A18 + 3.3b; mức theo A26 c — chỉ sai_mau / dau_hieu được ĐỎ): CHƯA ĐO báo nhầm (bảng gán nhãn
`docs/NHAN_BAO_NHAM_A18_2026-10-10.md`, ngưỡng A25) → `CHAN_DO = False`: mọi món bị báo là VÀNG; chỉ bật `CHAN_DO = True`
(hoặc `check(..., chan_do=True)`) khi báo nhầm đo được ≤ ngưỡng. Luật mức A26 (c) (người dùng 10/10): kể cả khi bật, CHỈ 'sai_mau'
(chữ nói NGƯỢC màu khóa) và món dấu hiệu (ô khai_bao_chu có dau_hieu, A20) được ĐỎ; 'thieu' / 'thieu_mau' của món thường LUÔN VÀNG
(ảnh tham chiếu giữ món — 14/15 mục đúng lỗi ảnh vẫn đúng). Chỉ 'khong_co_khoa' (thiếu đầu vào) ĐỎ ở cả hai chế độ.
A26 (b) 5 kiểu báo nhầm đã sửa: ống tay áo ≠ bàn tay (SLEEVE_VI) + tách câu '. '; câu nhóm ('both', 'two … characters') cho mọi nhân
vật trong khung (segment); vị ngữ 'face is a … pure-black mask' + '<món>less' theo hồ sơ; lưng/lưng-nghiêng bỏ món mặt trước thân
(FRONT_TORSO), không rõ hướng → ghi khong_loc; chân váy (skirt) + prompt tự giới hạn khung (prompt_cut) + món nhỏ ở WS/EWS (SMALL_ITEMS).

K1a (i) DẠNG (#24 S7 biến hình: hai dạng yêu nữ cùng khóa sân khấu 'yeunu' → món dạng 2 bị đòi khi ảnh vẽ dạng 1): BYĐ
`thanh_phan[].dang` (tùy chọn: chữ / danh sách / {nhip: chữ|danh sách}) khai dạng có mặt theo nhịp; `byd_view(..., dang=…, nhip=…)`
(ảnh = nhịp 'bat_dau') → dạng không có mặt ở nhịp đó = ngoài khung ('khong_can' + lý do). Người gọi nói nhân vật là một dạng mà BYĐ
không khai dạng ở nhịp → hành vi cũ (vẫn đòi) + `canh_bao` VÀNG "không rõ dạng" (ghi vào khong_loc từng món, không im lặng).
K1a (ii) BỊ CHE (#24 S9 dạng 2 quỳ ôm mặt): `hanh_dong[].<nhip>.che` (tùy chọn, CHE_ITEMS) cùng `tu_the` → món của vùng bị che là
'khong_can' + "bị che theo tư thế". Lý do có trường `che` riêng: tư thế một mình KHÔNG đủ — cùng 'quy', S8/S9 ôm mặt (mặt khuất) còn
quỳ nhìn thẳng thì lộ mặt; suy che từ tu_the sẽ biến đầu vào thiếu thành 'không cần' (CHUAN_XAY_DUNG: không im lặng).

Chưa nối vào pipeline (K1a). Không gọi model.
"""
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from core import stage_grid as sg

# A18 — chặn ĐỎ khi thiếu chữ? False tới khi đo báo nhầm đạt ngưỡng (xem docstring module + docs/NHAN_BAO_NHAM_A18_2026-10-10.md).
CHAN_DO = False

# màu chuẩn → (đồng nghĩa tiếng Anh, tiếng Việt CÒN DẤU — so trên chữ còn dấu: 'đen' ≠ 'đến', 'tím' ≠ 'tìm', 'đỏ' ≠ 'đó')
COLORS = {
    "yellow": (("yellow", "golden", "gold", "mustard", "lemon", "amber"), ("vàng",)),
    "black": (("black", "jet-black", "jet", "ebony", "onyx", "inky", "pitch-black"), ("đen",)),
    "white": (("white", "ivory", "snow-white", "snowy", "pure-white"), ("trắng",)),
    "red": (("red", "crimson", "scarlet", "blood-red", "ruby", "maroon"), ("đỏ",)),
    "brown": (("brown", "chestnut", "chocolate", "brunette"), ("nâu",)),
    "grey": (("grey", "gray", "silver"), ("xám", "bạc")),  # bỏ 'ash': 'ash-blonde' không phải xám
    "blue": (("blue", "navy", "azure", "cyan", "teal"), ("xanh dương", "xanh lam")),
    "green": (("green", "olive", "emerald", "lime"), ("xanh lá",)),
    "pink": (("pink", "magenta"), ("hồng",)),  # bỏ 'rose': 'rose gold', động từ 'rose'
    "purple": (("purple", "violet", "lilac"), ("tím",)),
    "orange": (("orange",), ("cam",)),
}
# "dark" = màu tối: khớp được màu mong đợi đen / nâu / xám (vd "short dark bob" cho tóc nâu đậm), không bao giờ tính là SAI màu.
WEAK_DARK = {"black", "brown", "grey", "blue"}

# món chuẩn → (đồng nghĩa tiếng Anh — cũng là chữ tìm trong prompt, tiếng Việt CÒN DẤU — chỉ để tách mô tả Kho; mô tả Việt nhận cả
# tên món tiếng Anh, vd 'choker đen')
ITEMS = {
    "tracksuit": (("tracksuit", "track suit", "track jacket", "track pants", "tracksuit jacket", "jogging suit"), ()),
    "choker": (("choker",), ("vòng cổ",)),
    "crop top": (("crop top", "crop-top", "cropped top"), ()),
    "sneakers": (("sneakers", "trainers", "running shoes"), ()),
    "heels": (("high heels", "heels", "stilettos", "pumps"), ("giày cao gót",)),
    "dress": (("dress", "gown"), ("váy",)),
    # A26 kiểu 5: chân váy bắt đầu ở hông (khác váy liền từ vai) — tiếng Việt 'váy' thành skirt khi mô tả có áo riêng (SEPARATE_TOP_VI)
    "skirt": (("skirt", "miniskirt", "mini skirt"), ("chân váy",)),
    "hair": (("hair", "haired", "bob", "ponytail", "braid", "locks"), ("tóc",)),
    "eyes": (("eyes", "eye"), ("mắt",)),
    "face": (("face", "faced"), ("mặt",)),
    "mask": (("face mask", "mask", "balaclava"), ("khẩu trang", "mặt nạ")),  # món riêng: có 'face' ≠ có khẩu trang
    "hands": (("hands", "hand", "arms", "fingers"), ("tay",)),
    "nails": (("nails", "claws", "talons"), ("móng",)),
    "stockings": (("stockings", "tights", "socks", "leggings"), ("tất",)),
    "legs": (("legs", "leg", "feet"), ("chân",)),
    "belt": (("belt", "sash", "waistband"), ("đai",)),
    "glitch": (("glitch", "static", "digital noise", "distortion"), ("nhiễu",)),
}
# Vùng thân của món (khóa ITEMS) = phần chiều cao người tính TỪ ĐỈNH ĐẦU nơi món bắt đầu thấy; cỡ cảnh chứa phần thân
# `framing_body(co)` (= stage_grid.FRAMING[co][0]: MLS 0,75, MS 0,55, MCU 0,35, CU 0,22, ECU 0,12) → món có vùng > phần đó không đòi.
# Món không có ở đây (glitch, món khai_bao_chu ngoài ITEMS) = không biết vùng → vẫn đòi. Người ngồi / quỳ: chưa chỉnh (K1a).
BODY_FROM_TOP = {"hair": 0.0, "face": 0.05, "eyes": 0.05, "mask": 0.07, "choker": 0.13, "crop top": 0.25, "tracksuit": 0.25,
                 "dress": 0.25, "hands": 0.45, "nails": 0.45, "belt": 0.45, "skirt": 0.45, "stockings": 0.6, "legs": 0.6,
                 "sneakers": 0.95, "heels": 0.95}
FRONT_ONLY = ("face", "eyes", "mask", "choker")   # chỉ thấy từ phía trước — quay lưng hẳn (thay = lung) không đòi
# A26 kiểu 4 (#24 S1/S3/S4): món mặt trước THÂN (áo crop mặc dưới áo khoác, vòng cổ ở cổ họng) khuất sớm hơn đầu — BYĐ có 'lung' mà
# không có 'mat' (lưng / lưng-nghiêng) → không đòi. Mặt / mắt / mặt nạ vẫn đòi khi lưng-nghiêng (nghiêng thấy mặt).
FRONT_TORSO = ("choker", "crop top")
# A26 kiểu 5 (#24 S2): món nhỏ chỉ vài điểm ảnh ở cỡ toàn → không đòi chữ (ảnh tham chiếu giữ món).
SMALL_ITEMS = ("choker", "nails")
SMALL_HIDDEN_AT = ("WS", "EWS")
# K1a (ii): vùng bị che (BYĐ hanh_dong[].<nhip>.che — khóa = shot_intent.CHE, test giữ khớp) → món (khóa ITEMS) khuất
CHE_ITEMS = {"mat": ("face", "eyes", "mask"), "toc": ("hair",), "co": ("choker",), "than": ("crop top", "tracksuit", "dress"),
             "eo": ("belt",), "tay": ("hands", "nails"), "chan": ("legs", "stockings"), "ban_chan": ("sneakers", "heels")}
IMAGE_NHIP = "bat_dau"      # ảnh tĩnh = khung đầu của shot
# Mô tả Kho tiếng Việt có áo riêng (áo croptop / áo thun…) → 'váy' trong cùng mô tả là chân váy (Kho 417: áo croptop + váy da đen ngắn)
SEPARATE_TOP_VI = re.compile(r"(?<![\w])(?:áo croptop|áo crop|croptop|crop top|áo thun|áo phông|áo sơ mi|áo ba lỗ)(?![\w])")
# A26 kiểu 1: 'tay áo' / 'áo … tay' = ống tay áo (chi tiết của áo), không phải bàn tay (Kho 416 'tay áo đen', 417 'áo khoác đỏ tay sọc đen')
SLEEVE_VI = re.compile(r"(?<![\w])tay áo(?![\w])|(?<![\w])áo(?![\w])[^,;]*?(?<![\w])tay(?![\w])")
PATTERN_WORDS = ("stripe", "stripes", "stars", "star", "print", "lines", "pattern", "vân", "gạch chéo", "sọc")  # so theo TỪ, không chuỗi con
SKIP_NO_COLOR = {"face"}          # "youthful face with light makeup": không màu → không phải khóa trang phục
INTENSITY = {"bright", "light", "pale", "deep", "matching", "a", "an", "the", "her", "his", "with", "and", "small", "thin"}
BOUNDARY = re.compile(r"[,.;:()]|\bwith\b|\band\b|\bunder\b|\bover\b|\bholding\b|\bwhile\b")


def fold(text: str) -> str:
    t = str(text or "").replace("đ", "d").replace("Đ", "D")
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


def norm(text: str, vi: bool = False) -> str:
    """Tiếng Anh: bỏ dấu + chữ thường. Tiếng Việt: chữ thường CÒN DẤU (NFC) — bỏ dấu làm 'đến' thành 'den' = đen, 'dài' = đai."""
    return unicodedata.normalize("NFC", str(text or "")).lower() if vi else fold(text)


VI_MARKS = set("ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")


def is_vi(text: str) -> bool:
    """Có chữ mang dấu tiếng Việt — ký tự ngoài ASCII khác (—, ', é…) KHÔNG làm must_keep tiếng Anh thành tiếng Việt."""
    return any(ch in VI_MARKS for ch in unicodedata.normalize("NFC", str(text or "")).lower())


def _words_re(words) -> str:
    return r"(?<![\w])(?:" + "|".join(re.escape(w).replace(r"\ ", r"[\s-]+") for w in sorted(words, key=len, reverse=True)) + r")(?![\w])"


def _colors_in(text: str, vi: bool = False) -> List[str]:
    t = fold(text).replace("-", " ") if not vi else norm(text, True)
    out = []
    for base, (en, vn) in COLORS.items():
        words = vn if vi else tuple(w.replace("-", " ") for w in en)
        if re.search(_words_re(words), t):
            out.append(base)
    return out


def _mask_sleeve(t: str) -> str:
    """Xóa chữ 'tay' của ống tay áo (giữ độ dài chuỗi): 'tay áo đen' → '       đen'; 'áo khoác đỏ tay sọc' → 'áo khoác đỏ     sọc'."""
    return SLEEVE_VI.sub(lambda m: (m.group(0)[:-3] + "   ") if m.group(0).endswith("tay") else " " * len(m.group(0)), t)


def _item_of(text: str, vi: bool = False) -> Optional[str]:
    t = norm(text, vi)
    if vi:
        t = _mask_sleeve(t)
    best = None
    for base, (en, vn) in ITEMS.items():
        for w in ((vn + en) if vi else en):
            m = re.search(_words_re([w]), t)
            if m and (best is None or m.start() < best[0] or (m.start() == best[0] and len(w) > best[2])):
                best = (m.start(), base, len(w))
    return best[1] if best else None


def _split_clauses(text: str) -> List[str]:
    """Tách theo dấu phẩy / chấm phẩy / chấm hết câu ('. ') ở mức ngoài ngoặc; 'under' / 'over' tách hai món ("white crop top under a …
    jacket"). Chấm hết câu (A26 kiểu 1): Kho 416 '… dép khủng long đỏ. Ảnh trang phục có người mẫu: tóc' — không gộp 'đỏ' vào tóc."""
    depth, cur, out = 0, "", []
    s = str(text or "")
    for i, ch in enumerate(s):
        depth += ch == "("
        depth -= ch == ")"
        if depth == 0 and (ch in ",;" or (ch == "." and (i + 1 == len(s) or s[i + 1].isspace()))):
            out.append(cur)
            cur = ""
        elif depth == 0 and ch != ")":
            cur += ch
    out.append(cur)
    res = []
    for c in out:
        res.extend(p for p in re.split(r"\s+(?:under|over)\s+", c) if p.strip())
    return [c.strip() for c in res if c.strip()]


def declare_from_text(text: str, vi: Optional[bool] = None) -> List[Dict]:
    """must_keep (Anh) / mô tả Kho (Việt) → [{mon, mau_chinh[], dau_hieu, nguon: 'suy'}] + món họa tiết (`hoa_tiet: True`, không kiểm).
    Mệnh đề có màu mà không có món (vd 'nửa dưới chuyển đỏ') → màu phụ của món ngay trước. Mệnh đề không nhận ra món (và không ghép
    được vào món trước) → `{mon: chữ gốc, khong_nhan_ra: True}` — báo ra, không im lặng bỏ (docs/CHUAN_XAY_DUNG.md)."""
    if vi is None:
        vi = is_vi(text)
    out: List[Dict] = []
    pat_re = _words_re(PATTERN_WORDS)
    skirt = vi and bool(SEPARATE_TOP_VI.search(norm(text, True)))     # có áo riêng → 'váy' là chân váy (A26 kiểu 5)
    for clause in _split_clauses(text):
        head, _, tail = clause.partition(" with ")
        if re.search(pat_re, norm(head, vi)) and _item_of(head, vi) is None:
            out.append({"mon": head.strip(), "hoa_tiet": True, "nguon": "suy"})
            continue
        item = _item_of(head if not vi else clause, vi)
        colors = _colors_in(head if not vi else clause, vi)
        if item == "dress" and skirt and not re.search(r"(?<![\w])(?:váy liền|đầm)(?![\w])", norm(clause, True)):
            item = "skirt"
        if item is None and vi and SLEEVE_VI.search(norm(clause, True)):
            # ống tay áo: 'tay áo đen' = chi tiết của áo (như 'grey sleeve stripes' tiếng Anh) → không kiểm ở chữ; câu tả CẢ áo mà áo
            # không có trong ITEMS ('áo khoác đỏ tay sọc đen') → không nhận ra (báo ra), không gộp màu vào món trước
            if re.match(r"\s*tay áo(?![\w])", norm(clause, True)):
                out.append({"mon": clause.strip(), "hoa_tiet": True, "chi_tiet": "ống tay áo — chi tiết của áo, không kiểm ở chữ",
                            "nguon": "suy"})
            else:
                out.append({"mon": clause.strip(), "khong_nhan_ra": True, "mau_thay": colors, "nguon": "suy"})
            continue
        if item is None:
            if colors and out and not out[-1].get("hoa_tiet") and not out[-1].get("khong_nhan_ra"):
                out[-1]["mau_chinh"] += [c for c in colors if c not in out[-1]["mau_chinh"]][:max(0, 2 - len(out[-1]["mau_chinh"]))]
            else:
                out.append({"mon": clause.strip(), "khong_nhan_ra": True, "mau_thay": colors, "nguon": "suy"})
            continue
        if item in SKIP_NO_COLOR and not colors:
            continue
        sign = None
        if tail.strip() and not vi:
            sign = " ".join(tail.split()[:4])
        elif not vi:
            mods = [w for w in re.findall(r"[a-z][a-z-]*", fold(head)) if w not in INTENSITY and not _colors_in(w)
                    and _item_of(w) is None and w not in ("dark", "zip-up", "chin-length", "high", "collar", "track", "top", "crop")]
            sign = mods[0] if mods else None
        prev = next((d for d in out if d.get("mon") == item), None)
        if prev:                                   # track jacket + track pants → một món 'tracksuit'
            prev["mau_chinh"] += [c for c in colors if c not in prev["mau_chinh"]][:max(0, 2 - len(prev["mau_chinh"]))]
            continue
        new = {"mon": item, "mau_chinh": colors[:2], "dau_hieu": sign, "nguon": "suy"}
        if not vi:
            # A26 kiểu 3: hồ sơ tự tả món bằng tính từ '<món>less' ('faceless smooth black face', Kho 418) → prompt viết 'faceless' cũng
            # là nhắc món đó. Chỉ khi chính hồ sơ có từ này (có căn cứ), không suy rộng.
            less = [f"{w}less" for w in ITEMS[item][0] if " " not in w and re.search(_words_re([f"{w}less"]), fold(head))]
            if less:
                new["dong_nghia"] = less
        out.append(new)
    return out


# ---- ô `khai_bao_chu` của hồ sơ Kho (A20, K0b phần 2) ----------------------------------------------------------------------------
# Sống trong assets.profile (JSON, cùng chỗ must_keep — core/assets.set_profile giữ ô khi lưu hồ sơ; không cột mới, không migration).
# Một món: {mon, dong_nghia[], mau_chinh[1–2] (khóa COLORS), mau_dong_nghia {màu: [từ]}, dau_hieu (≤ 1, chữ hoặc null), cach_viet[],
# hoa_tiet[] (chỉ cho QC sau gen — không kiểm ở chữ)}. Chữ dùng để SO prompt (mon, dong_nghia, cach_viet, mau_dong_nghia) phải tiếng Anh
# không dấu Việt và ≥ 3 ký tự: prompt được so sau khi bỏ dấu ('đai' → 'dai' khớp nhầm 'dài'); hoa_tiet viết tiếng Việt được.
KBC_KEY = "khai_bao_chu"
KBC_FIELDS = ("mon", "dong_nghia", "mau_chinh", "mau_dong_nghia", "dau_hieu", "cach_viet", "hoa_tiet")


def _kbc_word_problem(w) -> Optional[str]:
    if not isinstance(w, str) or not w.strip():
        return "phải là chữ, không rỗng"
    if is_vi(w):
        return f"'{w}' có dấu tiếng Việt — prompt so sau khi bỏ dấu, dễ khớp nhầm; viết tiếng Anh"
    if len(fold(w).strip()) < 3:
        return f"'{w}' quá ngắn (< 3 ký tự) — dễ khớp nhầm"
    return None


def validate_khai_bao_chu(items) -> List[Dict]:
    """Lỗi dạng [{muc: 'do', mon, loi}] — rỗng = hợp lệ. Không sửa ngầm."""
    if not isinstance(items, list):
        return [{"muc": "do", "mon": None, "loi": "khai_bao_chu phải là danh sách món"}]
    out, seen = [], set()
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            out.append({"muc": "do", "mon": f"#{i}", "loi": "món phải là bảng"})
            continue
        mon = it.get("mon")
        name = mon if isinstance(mon, str) and mon.strip() else f"#{i}"
        def bad(loi):
            out.append({"muc": "do", "mon": name, "loi": loi})
        for k in it:
            if k not in KBC_FIELDS:
                bad(f"trường lạ '{k}' (cho phép: {', '.join(KBC_FIELDS)})")
        if name.startswith("#"):
            bad("thiếu 'mon'")
        else:
            p = _kbc_word_problem(mon)
            if p:
                bad(f"mon {p}")
            if fold(mon) in seen:
                bad("trùng món")
            seen.add(fold(mon))
        colors = it.get("mau_chinh")
        if not isinstance(colors, list) or not 1 <= len(colors) <= 2:
            bad("mau_chinh phải có 1–2 màu")
        else:
            for c in colors:
                if c not in COLORS:
                    bad(f"màu '{c}' không có trong bảng ({', '.join(COLORS)})")
        for k in ("dong_nghia", "cach_viet", "hoa_tiet"):
            v = it.get(k)
            if v is None:
                continue
            if not isinstance(v, list):
                bad(f"{k} phải là danh sách")
                continue
            for w in v:
                p = _kbc_word_problem(w) if k != "hoa_tiet" else (None if isinstance(w, str) and w.strip() else "phải là chữ")
                if p:
                    bad(f"{k}: {p}")
        sign = it.get("dau_hieu")
        if sign is not None and not (isinstance(sign, str) and sign.strip()):
            bad("dau_hieu chỉ 1 dấu hiệu (chữ) hoặc null")
        elif sign is not None and _kbc_word_problem(sign):
            bad(f"dau_hieu {_kbc_word_problem(sign)}")
        if it.get("cach_viet") and sign is None:
            bad("cach_viet chỉ có nghĩa khi có dau_hieu")
        syn = it.get("mau_dong_nghia")
        if syn is not None:
            if not isinstance(syn, dict):
                bad("mau_dong_nghia phải là bảng {màu: [từ]}")
            else:
                for c, ws in syn.items():
                    if not isinstance(colors, list) or c not in colors:
                        bad(f"mau_dong_nghia '{c}' không thuộc mau_chinh")
                    for w in ws if isinstance(ws, list) else [None]:
                        p = _kbc_word_problem(w)
                        if p:
                            bad(f"mau_dong_nghia: {p}")
    return out


def _canonical(item: Dict) -> str:
    """Món chuẩn (khóa ITEMS) của một món khai_bao_chu — để biết món suy từ must_keep đã được khai chưa."""
    words = [item.get("mon") or ""] + list(item.get("dong_nghia") or [])
    return _item_of(", ".join(str(w) for w in words)) or fold(item.get("mon") or "")


def declare_from_profile(profile: Optional[Dict], mo_ta: str = "") -> Tuple[List[Dict], List[Dict]]:
    """Khai báo khóa của một hồ sơ Kho → (decl cho `check`, lỗi [{muc, mon, loi}]).
    Ưu tiên ô `khai_bao_chu` (nguon 'khai_bao_chu'); món trong must_keep (hoặc mô tả Kho khi chưa có must_keep) chưa có ô → vẫn suy
    (nguon 'suy') để kiểm, kèm VÀNG "nhắc điền một lần" (A20). Món khai sai dạng → ĐỎ và bỏ (món suy cùng tên thay chỗ)."""
    profile = profile or {}
    decl, issues, covered = [], [], set()
    kbc = profile.get(KBC_KEY)
    if kbc is not None:
        if not isinstance(kbc, list):
            issues += validate_khai_bao_chu(kbc)
            kbc = []
        for it in kbc:
            bad = validate_khai_bao_chu([it])
            if bad:
                issues += bad
                continue
            decl.append({"mon": it["mon"], "dong_nghia": list(it.get("dong_nghia") or []), "mau_chinh": list(it["mau_chinh"]),
                         "mau_dong_nghia": dict(it.get("mau_dong_nghia") or {}), "dau_hieu": it.get("dau_hieu"),
                         "cach_viet": list(it.get("cach_viet") or []), "hoa_tiet_qc": list(it.get("hoa_tiet") or []),
                         "nguon": KBC_KEY})
            covered.add(_canonical(it))
    mk = profile.get("must_keep")
    mk = ", ".join(map(str, mk)) if isinstance(mk, list) else str(mk or "")      # model có thể trả danh sách
    text = mk.strip() or str(mo_ta or "").strip()
    if not decl and not text:
        issues.append({"muc": "vang", "mon": None, "loi": "hồ sơ chưa có khai_bao_chu, must_keep lẫn mô tả — không có khóa để so"})
    for s in declare_from_text(text) if text else []:
        if s.get("hoa_tiet") or s.get("khong_nhan_ra"):
            decl.append(s)
            continue
        if s["mon"] in covered:
            continue
        decl.append(s)
        issues.append({"muc": "vang", "mon": s["mon"],
                       "loi": f"món '{s['mon']}' chưa có ô khai_bao_chu (đang suy từ chữ) — nhắc điền một lần trong hồ sơ Kho"})
    return decl, issues


def color_conflicts(mo_ta: str, decl: List[Dict]) -> List[Dict]:
    """Mô tả Kho ↔ khai báo (khai_bao_chu / must_keep) mâu thuẫn MÀU CHÍNH của cùng một món → VÀNG [{muc, mon, loi}].
    #24 shot 5/6: mô tả Kho cũ 'đai đỏ ngang eo' lệch ảnh mẫu (đai gai đen) → prompt viết đai đỏ. Mô tả không nói màu → không so."""
    if not str(mo_ta or "").strip():
        return []
    known = {}
    for d in decl or []:
        if d.get("hoa_tiet") or d.get("khong_nhan_ra") or not d.get("mau_chinh"):
            continue
        known.setdefault(_canonical(d) if d.get("nguon") == KBC_KEY else d["mon"], d)
    out = []
    for s in declare_from_text(mo_ta):
        if s.get("hoa_tiet") or s.get("khong_nhan_ra") or not s.get("mau_chinh"):
            continue
        d = known.get(s["mon"])
        if d and s["mau_chinh"][0] != d["mau_chinh"][0]:
            out.append({"muc": "vang", "mon": d["mon"],
                        "loi": f"mô tả Kho ghi '{s['mon']}' màu {s['mau_chinh'][0]}, khai báo ({d.get('nguon')}) ghi màu chính "
                               f"{d['mau_chinh'][0]} — sửa mô tả Kho theo ảnh mẫu (hoặc sửa khai báo)"})
    return out


COLOR_AFTER = re.compile(r"\s+(?:in|dyed|colou?red)\s+")
CLAUSE_END = re.compile(r"[,.;:()]")
# A26 kiểu 3: vị ngữ sau danh từ ('face is a smooth featureless pure-black mask', #24 S5/S6) — lấy ≤ 6 từ, dừng ở ranh giới / giới từ
# (không lấy màu của vật khác: 'face is turned away from the red light'). Tính từ '<món>less' ('faceless dark female creature', #24 S7) —
# ≤ 3 từ sau.
PREDICATE = re.compile(r"\s+(?:is|are)\s+")
STOP_WORDS = {"from", "to", "toward", "towards", "at", "in", "on", "of", "by", "into", "onto", "under", "over", "behind", "near", "as",
              "like", "against", "through", "than", "with"}   # 'with' (rà A26): 'hair is tied with a red ribbon' — màu của vật đi kèm


def _take_words(low: str, pos: int, n: int) -> int:
    """Vị trí hết ≤ n từ tính từ `pos`, dừng ở ranh giới mệnh đề (BOUNDARY) hoặc giới từ (STOP_WORDS)."""
    nb = BOUNDARY.search(low, pos)
    limit = nb.start() if nb else len(low)
    end = pos
    for i, m in enumerate(re.finditer(r"\S+", low[pos:limit])):
        if i >= n or m.group(0) in STOP_WORDS:
            break
        end = pos + m.end()
    return end


def _windows(prompt: str, item: str, extra=()):
    """Mỗi lần prompt nhắc món → (cửa sổ màu, mệnh đề). Cửa sổ màu = từ ranh giới mệnh đề trước tới hết tên món (màu đứng trước danh từ)
    + cụm 'in / dyed / colored <màu>' ngay sau danh từ tới ranh giới kế. Mệnh đề = tới dấu câu kế (để tìm dấu hiệu sau 'with').
    Món ngoài ITEMS (khai_bao_chu K1a) → tìm đúng tên món. `extra` = đồng nghĩa món từ khai_bao_chu."""
    low = fold(prompt)
    words = tuple(ITEMS.get(item, ((fold(item),),))[0]) + tuple(fold(w) for w in extra or () if str(w).strip())
    for m in re.finditer(_words_re(words), low):
        start = 0
        for b in BOUNDARY.finditer(low, 0, m.start()):
            start = b.end()
        end = m.end()
        after = COLOR_AFTER.match(low, end)
        pred = PREDICATE.match(low, end)
        if after:
            nb = BOUNDARY.search(low, after.end())
            end = nb.start() if nb else len(low)
        elif pred:
            end = _take_words(low, pred.end(), 6)
        elif m.group(0).endswith("less"):
            end = _take_words(low, end, 3)
        ce = CLAUSE_END.search(low, m.end())
        yield low[start:end], low[start:ce.start() if ce else len(low)]


def framing_body(co) -> Optional[float]:
    """Phần thân (từ đỉnh đầu) cỡ cảnh chứa — stage_grid.FRAMING[co][0]; cỡ không biết → None."""
    f = sg.FRAMING.get(str(co or "").strip().upper()) if co else None
    return f[0] if f else None


def _forms_at(decl, nhip: str) -> Optional[List[str]]:
    """BYĐ thanh_phan[].dang → các dạng có mặt ở `nhip`; không khai (hoặc bảng theo nhịp thiếu nhịp này) → None."""
    if isinstance(decl, dict):
        decl = decl.get(nhip)
    if decl is None:
        return None
    vals = [decl] if isinstance(decl, str) else list(decl) if isinstance(decl, list) else []
    out = [str(v).strip().lower() for v in vals if str(v or "").strip()]
    return out or None


def byd_view(byd: Optional[Dict], vat: str, dang: Optional[str] = None, nhip: str = IMAGE_NHIP) -> Optional[Dict]:
    """BYĐ → điều máy thấy của nhân vật `vat` (khóa sân khấu, so không phân biệt hoa/thường): {vat, co, thay [mat/lung/nghieng],
    trong_khung}. Không có BYĐ → None (check không lọc). Nhân vật không có trong `thanh_phan` (có người) hoặc `vai: khong_duoc_co` →
    trong_khung False. Thiếu khóa `vat` / BYĐ chưa có `thanh_phan` → trong_khung None + `khong_loc` (không lọc 'ngoài khung', vẫn đòi —
    rà độc lập #1: không biến thiếu đầu vào thành 'không cần').
    K1a: `dang` = nhân vật là MỘT dạng của khóa sân khấu dùng chung (#24 yêu nữ dạng 1/2) → so với thanh_phan[].dang ở `nhip`: dạng
    không có mặt → trong_khung False + `ngoai_khung` (lý do); BYĐ không khai dạng → `canh_bao` VÀNG "không rõ dạng", lọc như cũ.
    hanh_dong[ai = vat].<nhip> → `tu_the` + `che` (vùng bị che, CHE_ITEMS)."""
    if not isinstance(byd, dict):
        return None
    may = byd.get("may") if isinstance(byd.get("may"), dict) else {}
    key = str(vat or "").strip().lower()
    cast = [x for x in byd.get("thanh_phan") or [] if isinstance(x, dict)] if isinstance(byd.get("thanh_phan"), list) else []
    if not key or not cast:
        why = "thiếu khóa sân khấu của nhân vật" if not key else "BYĐ chưa có thanh_phan"
        return {"vat": vat, "co": may.get("co"), "thay": [], "trong_khung": None, "khong_loc": why}
    c = next((x for x in cast if str(x.get("vat") or "").strip().lower() == key), None)
    thay = [v.strip() for v in str((c or {}).get("thay") or "").split("|") if v.strip()]
    view = {"vat": vat, "co": may.get("co"), "thay": thay, "trong_khung": bool(c) and c.get("vai") != "khong_duoc_co"}
    warn = []
    if dang and view["trong_khung"]:
        forms = _forms_at(c.get("dang"), nhip)
        view.update(dang=forms, nhip=nhip)
        if forms is None:
            warn.append({"muc": "vang", "loi": f"không rõ dạng: '{vat}' có nhiều dạng mà BYĐ thanh_phan không khai 'dang' ở nhịp "
                                               f"{nhip} — vẫn đòi món của dạng '{dang}' như cũ"})
        elif str(dang).strip().lower() not in forms:
            view["trong_khung"] = False
            view["ngoai_khung"] = f"dạng '{dang}' không có mặt ở nhịp {nhip} (BYĐ thanh_phan dang = {', '.join(forms)})"
    acts = [h for h in byd.get("hanh_dong") or [] if isinstance(h, dict) and str(h.get("ai") or "").strip().lower() == key]
    st = next((h[nhip] for h in acts if isinstance(h.get(nhip), dict)), None)
    if st is not None:
        view.update(tu_the=st.get("tu_the"), nhip=nhip)
        che = st.get("che") or []
        che = che if isinstance(che, list) else [che]
        view["che"] = [str(p).strip() for p in che if str(p).strip() in CHE_ITEMS]
        bad = [str(p) for p in che if str(p).strip() not in CHE_ITEMS]
        if bad:
            warn.append({"muc": "vang", "loi": f"che {bad} không có trong bảng ({', '.join(CHE_ITEMS)}) — bỏ qua, món vẫn đòi"})
    if warn:
        view["canh_bao"] = warn
    return view


def _item_key(d: Dict) -> Optional[str]:
    if d["mon"] in ITEMS:
        return d["mon"]
    k = _canonical(d) if d.get("nguon") == KBC_KEY else None
    return k if k in ITEMS else None


def _not_needed(d: Dict, view: Optional[Dict]) -> Tuple[Optional[str], Optional[str]]:
    """(ly_do món KHÔNG cần có chữ, khong_loc = vì sao không lọc được) theo BYĐ. Cảnh báo VÀNG của view (không rõ dạng, che lạ) được
    ghép vào khong_loc của mọi món còn đòi — không im lặng."""
    ly_do, khong_loc = _not_needed_core(d, view)
    warn = "; ".join(w["loi"] for w in (view or {}).get("canh_bao") or [])
    if ly_do or not warn:
        return ly_do, khong_loc
    return None, "; ".join(x for x in (warn, khong_loc) if x)


def _not_needed_core(d: Dict, view: Optional[Dict]) -> Tuple[Optional[str], Optional[str]]:
    if view is None:
        return None, None
    if view.get("trong_khung") is None:                 # thiếu khóa / thiếu thanh_phan → không lọc gì, vẫn đòi
        return None, f"{view.get('khong_loc') or 'không biết nhân vật có trong khung'} — không lọc theo BYĐ, vẫn đòi"
    if not view.get("trong_khung"):
        return view.get("ngoai_khung") or f"nhân vật '{view.get('vat')}' không có trong khung theo BYĐ (thanh_phan)", None
    key = _item_key(d)
    che = [p for p in view.get("che") or [] if key in CHE_ITEMS.get(p, ())]
    if che:
        return (f"bị che theo tư thế ({view.get('tu_the') or 'không ghi tư thế'}; BYĐ che: {', '.join(che)} ở nhịp "
                f"{view.get('nhip') or IMAGE_NHIP}): '{d['mon']}' khuất"), None
    thay = set(view.get("thay") or [])
    if key in FRONT_ONLY and thay == {"lung"}:
        return f"quay lưng (BYĐ thay = lung): '{d['mon']}' chỉ thấy từ phía trước", None
    if key in FRONT_TORSO and "lung" in thay and "mat" not in thay:
        return f"quay lưng (BYĐ thay = {'|'.join(view.get('thay'))}): '{d['mon']}' ở mặt trước thân, khuất khi không quay mặt", None
    notes = []
    if key in FRONT_ONLY + FRONT_TORSO and not thay:
        notes.append(f"không rõ hướng (BYĐ không ghi mặt/lưng) — '{d['mon']}' chỉ thấy từ phía trước, vẫn đòi")
    co = str(view.get("co") or "").strip().upper()
    if key in SMALL_ITEMS and co in SMALL_HIDDEN_AT:
        return f"món nhỏ '{d['mon']}' chỉ vài điểm ảnh ở cỡ {co} — không đòi chữ (ảnh tham chiếu giữ món)", None
    body, cut = framing_body(view.get("co")), view.get("cat_prompt")
    if body is None and cut is None:
        notes.append(f"cỡ cảnh '{view.get('co')}' không biết — không lọc theo cỡ, vẫn đòi")
        return None, "; ".join(notes)
    if key not in BODY_FROM_TOP:
        notes.append(f"món '{d['mon']}' chưa có vùng thân (BODY_FROM_TOP) — không lọc theo cỡ, vẫn đòi")
        return None, "; ".join(notes)
    if body is not None and BODY_FROM_TOP[key] > body:
        return (f"cỡ {co} chỉ chứa {int(body * 100)} % thân từ đỉnh đầu; '{d['mon']}' ở "
                f"{int(BODY_FROM_TOP[key] * 100)} % — ngoài khung"), None
    if cut is not None and BODY_FROM_TOP[key] > cut:
        return (f"prompt tự giới hạn khung ('no legs' / 'chest up' / 'waist up' ≈ {int(cut * 100)} % thân); '{d['mon']}' ở "
                f"{int(BODY_FROM_TOP[key] * 100)} % — ngoài khung"), None
    return None, "; ".join(notes) or None


# A26 kiểu 5: prompt tự nói khung chỉ tới đâu (#22 S4/S6 'medium close-up from mid-chest up, no legs') → phần thân tối đa trong khung
PROMPT_CUT = ((r"(?<![\w])(?:mid[- ]?chest|chest)[- ]up(?![\w])", 0.35), (r"(?<![\w])waist[- ]up(?![\w])", 0.5),
              (r"(?<![\w])no legs(?![\w])", 0.55))


def prompt_cut(prompt: str) -> Optional[float]:
    """Phần thân (từ đỉnh đầu) mà chữ prompt tự giới hạn khung; không nói → None. Người gọi đặt vào view['cat_prompt']."""
    low = fold(prompt)
    hits = [v for pat, v in PROMPT_CUT if re.search(pat, low)]
    return min(hits) if hits else None


def check(decl: List[Dict], prompt: str, view: Optional[Dict] = None, chan_do: Optional[bool] = None) -> List[Dict]:
    """[{mon, mau_chinh, trang_thai: co|thieu|thieu_mau|sai_mau|khong_can, mau_thay, dau_hieu, dau_hieu_thay, muc, ly_do?, khong_loc?}].
    `view` = byd_view(...) → món máy không thấy được là 'khong_can' + ly_do (muc None); `view['cat_prompt']` (prompt_cut) = khung prompt
    tự giới hạn. `chan_do` (mặc định CHAN_DO) — luật mức A26 (c): True → CHỈ 'sai_mau' và món dấu hiệu (khai_bao_chu có dau_hieu) ĐỎ;
    'thieu' / 'thieu_mau' món thường LUÔN VÀNG; False → mọi thứ VÀNG. Chỉ khong_co_khoa luôn ĐỎ. Họa tiết bỏ qua. `dau_hieu_thay` chỉ
    để báo."""
    chan = CHAN_DO if chan_do is None else bool(chan_do)
    out = []
    real = [d for d in decl or [] if not d.get("hoa_tiet") and not d.get("khong_nhan_ra")]
    if not real:                                   # không có khóa nào để so → ĐỎ, không trả rỗng (trông như đạt)
        return [{"mon": None, "mau_chinh": [], "dau_hieu": None, "nguon": None, "mau_thay": [], "dau_hieu_thay": None,
                 "mau_phu_thieu": [], "trang_thai": "khong_co_khoa", "muc": "do"}]
    for d in real:
        item, want = d["mon"], list(d.get("mau_chinh") or [])
        ly_do, khong_loc = _not_needed(d, view)
        if ly_do:
            out.append({"mon": item, "mau_chinh": want, "dau_hieu": d.get("dau_hieu"), "nguon": d.get("nguon"), "mau_thay": [],
                        "dau_hieu_thay": None, "mau_phu_thieu": [], "trang_thai": "khong_can", "muc": None, "ly_do": ly_do})
            continue
        extra = list(d.get("dong_nghia") or ())
        if d.get("nguon") == KBC_KEY and item not in ITEMS and _canonical(d) in ITEMS:
            # món khai 'spiked belt' đã che món suy 'belt' (declare_from_profile) → nhận cả từ của loại đó, không ĐỎ oan 'thieu'
            extra += list(ITEMS[_canonical(d)][0])
        wins = list(_windows(prompt, item, extra))
        syn = {c: _words_re([fold(x).replace("-", " ") for x in ws]) for c, ws in (d.get("mau_dong_nghia") or {}).items() if ws}
        row = {"mon": item, "mau_chinh": want, "dau_hieu": d.get("dau_hieu"), "nguon": d.get("nguon"), "mau_thay": [],
               "dau_hieu_thay": None, "mau_phu_thieu": []}
        if khong_loc:
            row["khong_loc"] = khong_loc
        sign_item = d.get("nguon") == KBC_KEY and bool(d.get("dau_hieu"))    # A26 (c): món dấu hiệu khai trong khai_bao_chu
        if not wins:
            row.update(trang_thai="thieu", muc="do" if chan and sign_item else "vang")
            out.append(row)
            continue
        main_ok = partial = wrong = False
        for w, _ in wins:
            seen = _colors_in(w)
            seen += [c for c, rx in syn.items() if c not in seen and re.search(rx, w.replace("-", " "))]   # màu đồng nghĩa khai_bao_chu
            row["mau_thay"] += [c for c in seen if c not in row["mau_thay"]]
            if not want:
                continue
            dark = bool(re.search(r"\bdark\b", w))
            if want[0] in seen or (dark and want[0] in WEAK_DARK):
                main_ok = True                     # A18: màu CHÍNH (đầu tiên) bắt buộc
            elif any(c in want for c in seen):
                partial = True
            elif seen:
                wrong = True
        status = "co" if (not want or main_ok) else "thieu_mau" if (partial or not wrong) else "sai_mau"
        row["mau_phu_thieu"] = [c for c in want[1:] if c not in row["mau_thay"]] if want else []   # VÀNG ở K1a, không đổi trạng thái
        if d.get("dau_hieu"):
            key = [x for x in re.findall(r"[a-z]+", fold(d["dau_hieu"])) if x not in INTENSITY]
            text = " ".join(c for _, c in wins)
            alt = [fold(x) for x in d.get("cach_viet") or () if str(x).strip()]      # cách viết tương đương (khai_bao_chu)
            row["dau_hieu_thay"] = (bool(key) and bool(re.search(_words_re(key), text))) or bool(alt and re.search(_words_re(alt), text))
        muc = None if status == "co" else "do" if chan and (status == "sai_mau" or sign_item) else "vang"
        row.update(trang_thai=status, muc=muc)
        out.append(row)
    return out


def unrecognized(decl: List[Dict]) -> List[str]:
    """Mệnh đề khóa không nhận ra món — báo cùng kết quả check (không im lặng bỏ)."""
    return [d["mon"] for d in decl or [] if d.get("khong_nhan_ra")]


OTHER_MARKERS = ("creature", "figure", "woman", "girl", "monster", "ghost")
# Câu nhóm (A26 kiểu 2). 'both / each' không tính khi đi với bộ phận / 'other' ('both hands', 'each other'); 'all' chỉ dạng nói về người.
GROUP_RE = (r"(?<![\w])both(?![\w])(?!\s+(?:(?:her|his|its|their)\s+)?(?:hands|arms|legs|feet|eyes|ears|sides|ends|knees)(?![\w])"
            r"|\s+of\s+(?:her|his|its))"
            r"|(?<![\w])each(?![\w])(?!\s+(?:other|hand|arm|leg|foot|eye|side))"
            r"|(?<![\w])two(?:\s+[\w-]+){0,3}?\s+(?:characters|people|friends|heroes|players)(?![\w])"
            r"|(?<![\w])all\s+(?:of\s+them|the\s+characters|characters|two|three|four)(?![\w])")
# 'they' chỉ là câu nhóm khi mệnh đề có tên gần nhất gọi ≥ 2 nhân vật trong khung ('Kelly and Maxim walk, they wear masks')
THEY_RE = r"(?<![\w])they(?![\w])"
# Người lạ không gọi bằng OTHER_MARKERS ('two other characters', 'guards', 'the crowd') → không phải câu nhóm, thuộc '_khac' (rà A26)
STRANGER_RE = (r"(?<![\w])(?:(?<!each )other|others|another|guards?|npcs?|crowd|strangers?|bystanders?|passers?-?by|enemies|enemy"
               r"|soldiers?|villagers?)(?![\w])")


def segment(prompt: str, markers: Dict[str, List[str]]) -> Dict[str, str]:
    """Chia prompt theo nhân vật: mỗi mệnh đề (, . ;) thuộc nhân vật được nhắc gần nhất (tên / từ đánh dấu); người lạ (OTHER_MARKERS
    không thuộc ai) → '_khac' — để màu tóc của 'bóng đen' không bị tính cho Kelly. Mệnh đề trước lần nhắc đầu: nếu chỉ một nhân vật thì
    thuộc nhân vật đó, không thì bỏ. Trả {tên: chữ}.
    Hai tên trúng CÙNG chỗ (thẩm định 5 #4/#5): từ đánh dấu DÀI hơn thắng ('maxim kl' hơn 'maxim'); còn hòa (từ y hệt — hai dạng yêu nữ
    cùng 'creature', không phân biệt được bằng chữ) → mệnh đề thuộc CẢ HAI, không gán theo thứ tự tên (trước đây dạng 2 rỗng → báo nhầm)."""
    out: Dict[str, List[str]] = {k: [] for k in markers}
    owner, pending, last_named = None, [], set()
    other_re = _words_re(OTHER_MARKERS)
    clauses = []
    for clause in re.split(r"[,.;]", str(prompt or "")):
        # 'Kelly and a ghost girl in a white dress': có người lạ → tách thêm theo and / while để đồ người lạ không tính cho Kelly
        clauses += re.split(r"\band\b|\bwhile\b", clause) if re.search(other_re, fold(clause)) else [clause]
    for clause in clauses:
        low = fold(clause)
        hits = []
        for name, words in markers.items():
            for w in words:
                m = re.search(rf"(?<![\w]){re.escape(fold(w))}(?![\w])", low)
                if m:
                    hits.append((m.start(), -(m.end() - m.start()), name))
        stranger = not hits and bool(re.search(STRANGER_RE, low))
        group = re.search(GROUP_RE, low) or (re.search(THEY_RE, low) and len(last_named) >= 2)
        if not hits and markers and group and not stranger and not re.search(other_re, low):
            # A26 kiểu 2 (#22 S7–9): câu tả chung không gọi tên ('two stylized characters … both with the black mask') → của MỌI nhân
            # vật trong khung (markers = nhân vật có trong khung); chỉ mệnh đề này, mệnh đề sau vẫn theo người được nhắc gần nhất
            for o in markers:
                out[o].append(clause)
            continue
        if hits:
            last_named = {h[2] for h in hits}
        if not hits:
            m = re.search(other_re, low) or (re.search(STRANGER_RE, low) if stranger else None)
            if m:
                hits.append((m.start(), 0, "_khac"))
        if hits:
            best = min(h[:2] for h in hits)
            owner = [n for n in markers if (best[0], best[1], n) in hits] or ["_khac"]   # giữ thứ tự khai, hòa → cả nhóm
        if owner is None:
            pending.append(clause)
        else:
            for o in owner:
                if o in out:
                    out[o].append(clause)
    if len(markers) == 1 and pending:
        out[next(iter(markers))] = pending + out[next(iter(markers))]
    return {k: ",".join(v) for k, v in out.items()}


def summary(rows: List[Dict]) -> Dict[str, int]:
    s = {"co": 0, "thieu": 0, "thieu_mau": 0, "sai_mau": 0, "khong_can": 0, "khong_co_khoa": 0}
    for r in rows:
        s[r["trang_thai"]] = s.get(r["trang_thai"], 0) + 1
    return s
