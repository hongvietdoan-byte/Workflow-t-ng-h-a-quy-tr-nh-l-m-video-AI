"""Khóa nhận diện bằng chữ (A18 / A20 kế hoạch kiểm soát, docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md) — hàm THUẦN, K0b chạy khô.

A20 tầng "chữ": mỗi món trang phục / nhận diện = tên món + màu chủ đạo (1–2) + ≤ 1 dấu hiệu. Hồ sơ Kho CHƯA có ô `khai_bao_chu`
(K0b tạo trường, K1a điền) → `declare_from_text` TẠM SUY các món từ `must_keep` (tiếng Anh) hoặc mô tả Kho (tiếng Việt) — mọi món suy
mang `nguon: "suy"`. `check(decl, prompt)` so với chữ prompt: mỗi món → co / thieu / thieu_mau / sai_mau (A18: thiếu / sai màu = ĐỎ).
Họa tiết (sọc, sao, viền…) KHÔNG kiểm ở chữ (A20: thuộc ảnh tham chiếu + QC sau gen) — chỉ ghi vào `hoa_tiet`.

Chưa nối vào pipeline (K1a). Không gọi model.
"""
import re
import unicodedata
from typing import Dict, List, Optional

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


def _item_of(text: str, vi: bool = False) -> Optional[str]:
    t = norm(text, vi)
    best = None
    for base, (en, vn) in ITEMS.items():
        for w in ((vn + en) if vi else en):
            m = re.search(_words_re([w]), t)
            if m and (best is None or m.start() < best[0] or (m.start() == best[0] and len(w) > best[2])):
                best = (m.start(), base, len(w))
    return best[1] if best else None


def _split_clauses(text: str) -> List[str]:
    """Tách theo dấu phẩy / chấm phẩy ở mức ngoài ngoặc; 'under' / 'over' tách hai món ("white crop top under a … jacket")."""
    depth, cur, out = 0, "", []
    for ch in str(text or ""):
        depth += ch == "("
        depth -= ch == ")"
        if ch in ",;" and depth == 0:
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
    for clause in _split_clauses(text):
        head, _, tail = clause.partition(" with ")
        if re.search(pat_re, norm(head, vi)) and _item_of(head, vi) is None:
            out.append({"mon": head.strip(), "hoa_tiet": True, "nguon": "suy"})
            continue
        item = _item_of(head if not vi else clause, vi)
        colors = _colors_in(head if not vi else clause, vi)
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
        out.append({"mon": item, "mau_chinh": colors[:2], "dau_hieu": sign, "nguon": "suy"})
    return out


COLOR_AFTER = re.compile(r"\s+(?:in|dyed|colou?red)\s+")
CLAUSE_END = re.compile(r"[,.;:()]")


def _windows(prompt: str, item: str):
    """Mỗi lần prompt nhắc món → (cửa sổ màu, mệnh đề). Cửa sổ màu = từ ranh giới mệnh đề trước tới hết tên món (màu đứng trước danh từ)
    + cụm 'in / dyed / colored <màu>' ngay sau danh từ tới ranh giới kế. Mệnh đề = tới dấu câu kế (để tìm dấu hiệu sau 'with').
    Món ngoài ITEMS (khai_bao_chu K1a) → tìm đúng tên món."""
    low = fold(prompt)
    for m in re.finditer(_words_re(ITEMS.get(item, ((fold(item),),))[0]), low):
        start = 0
        for b in BOUNDARY.finditer(low, 0, m.start()):
            start = b.end()
        end = m.end()
        after = COLOR_AFTER.match(low, end)
        if after:
            nb = BOUNDARY.search(low, after.end())
            end = nb.start() if nb else len(low)
        ce = CLAUSE_END.search(low, m.end())
        yield low[start:end], low[start:ce.start() if ce else len(low)]


def check(decl: List[Dict], prompt: str) -> List[Dict]:
    """[{mon, mau_chinh, trang_thai: co|thieu|thieu_mau|sai_mau, mau_thay, dau_hieu, dau_hieu_thay, muc}] — muc 'do' khi thiếu / sai màu
    (A18), None khi có. Họa tiết bỏ qua. `dau_hieu_thay` chỉ để báo (VÀNG ở K1a), không đổi trang_thai."""
    out = []
    real = [d for d in decl or [] if not d.get("hoa_tiet") and not d.get("khong_nhan_ra")]
    if not real:                                   # không có khóa nào để so → ĐỎ, không trả rỗng (trông như đạt)
        return [{"mon": None, "mau_chinh": [], "dau_hieu": None, "nguon": None, "mau_thay": [], "dau_hieu_thay": None,
                 "mau_phu_thieu": [], "trang_thai": "khong_co_khoa", "muc": "do"}]
    for d in real:
        item, want = d["mon"], list(d.get("mau_chinh") or [])
        wins = list(_windows(prompt, item))
        row = {"mon": item, "mau_chinh": want, "dau_hieu": d.get("dau_hieu"), "nguon": d.get("nguon"), "mau_thay": [],
               "dau_hieu_thay": None, "mau_phu_thieu": []}
        if not wins:
            row.update(trang_thai="thieu", muc="do")
            out.append(row)
            continue
        main_ok = partial = wrong = False
        for w, _ in wins:
            seen = _colors_in(w)
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
            row["dau_hieu_thay"] = bool(key) and bool(re.search(_words_re(key), text))
        row.update(trang_thai=status, muc=None if status == "co" else "do")
        out.append(row)
    return out


def unrecognized(decl: List[Dict]) -> List[str]:
    """Mệnh đề khóa không nhận ra món — báo cùng kết quả check (không im lặng bỏ)."""
    return [d["mon"] for d in decl or [] if d.get("khong_nhan_ra")]


OTHER_MARKERS = ("creature", "figure", "woman", "girl", "monster", "ghost")


def segment(prompt: str, markers: Dict[str, List[str]]) -> Dict[str, str]:
    """Chia prompt theo nhân vật: mỗi mệnh đề (, . ;) thuộc nhân vật được nhắc gần nhất (tên / từ đánh dấu); người lạ (OTHER_MARKERS
    không thuộc ai) → '_khac' — để màu tóc của 'bóng đen' không bị tính cho Kelly. Mệnh đề trước lần nhắc đầu: nếu chỉ một nhân vật thì
    thuộc nhân vật đó, không thì bỏ. Trả {tên: chữ}."""
    out: Dict[str, List[str]] = {k: [] for k in markers}
    owner, pending = None, []
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
                    hits.append((m.start(), name))
        if not hits:
            m = re.search(other_re, low)
            if m:
                hits.append((m.start(), "_khac"))
        if hits:
            owner = min(hits)[1]
        if owner is None:
            pending.append(clause)
        elif owner in out:
            out[owner].append(clause)
    if len(markers) == 1 and pending:
        out[next(iter(markers))] = pending + out[next(iter(markers))]
    return {k: ",".join(v) for k, v in out.items()}


def summary(rows: List[Dict]) -> Dict[str, int]:
    s = {"co": 0, "thieu": 0, "thieu_mau": 0, "sai_mau": 0, "khong_co_khoa": 0}
    for r in rows:
        s[r["trang_thai"]] = s.get(r["trang_thai"], 0) + 1
    return s
