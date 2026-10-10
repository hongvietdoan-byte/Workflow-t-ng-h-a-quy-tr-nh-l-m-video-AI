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

# màu chuẩn → (đồng nghĩa tiếng Anh, tiếng Việt đã bỏ dấu)
COLORS = {
    "yellow": (("yellow", "golden", "gold", "mustard", "lemon", "amber"), ("vang",)),
    "black": (("black", "jet-black", "jet", "ebony", "onyx", "inky", "pitch-black"), ("den",)),
    "white": (("white", "ivory", "snow-white", "snowy", "pure-white"), ("trang",)),
    "red": (("red", "crimson", "scarlet", "blood-red", "ruby", "maroon"), ("do",)),
    "brown": (("brown", "chestnut", "chocolate", "brunette"), ("nau",)),
    "grey": (("grey", "gray", "silver", "ash"), ("xam", "bac")),
    "blue": (("blue", "navy", "azure", "cyan", "teal"), ("xanh duong", "xanh lam")),
    "green": (("green", "olive", "emerald", "lime"), ("xanh la",)),
    "pink": (("pink", "magenta", "rose"), ("hong",)),
    "purple": (("purple", "violet", "lilac"), ("tim",)),
    "orange": (("orange",), ("cam",)),
}
# "dark" = màu tối: khớp được màu mong đợi đen / nâu / xám (vd "short dark bob" cho tóc nâu đậm), không bao giờ tính là SAI màu.
WEAK_DARK = {"black", "brown", "grey", "blue"}

# món chuẩn → (đồng nghĩa tiếng Anh — cũng là chữ tìm trong prompt, tiếng Việt bỏ dấu — chỉ để tách mô tả Kho)
ITEMS = {
    "tracksuit": (("tracksuit", "track suit", "track jacket", "track pants", "tracksuit jacket", "jogging suit"), ()),
    "choker": (("choker",), ("vong co",)),
    "crop top": (("crop top", "crop-top", "cropped top"), ()),
    "sneakers": (("sneakers", "trainers", "running shoes"), ()),
    "heels": (("high heels", "heels", "stilettos", "pumps"), ("giay cao got",)),
    "dress": (("dress", "gown"), ("vay",)),
    "hair": (("hair", "haired", "bob", "ponytail", "braid", "locks"), ("toc",)),
    "eyes": (("eyes", "eye"), ("mat do", "hai mat", "mat tron")),
    "face": (("face", "faced", "mask"), ("mat",)),
    "hands": (("hands", "hand", "arms", "fingers"), ("tay",)),
    "nails": (("nails", "claws", "talons"), ("mong",)),
    "stockings": (("stockings", "tights", "socks", "leggings"), ("tat",)),
    "legs": (("legs", "leg", "feet"), ("chan",)),
    "belt": (("belt", "sash", "waistband"), ("dai",)),
    "glitch": (("glitch", "static", "digital noise", "distortion"), ("nhieu", "glitch")),
}
PATTERN_WORDS = ("stripe", "stripes", "stars", "star", "print", "lines", "pattern", "van ", "gach cheo", "soc")
SKIP_NO_COLOR = {"face"}          # "youthful face with light makeup": không màu → không phải khóa trang phục
INTENSITY = {"bright", "light", "pale", "deep", "matching", "a", "an", "the", "her", "his", "with", "and", "small", "thin"}
BOUNDARY = re.compile(r"[,.;:()]|\bwith\b|\band\b|\bunder\b|\bover\b|\bholding\b|\bwhile\b")


def fold(text: str) -> str:
    t = str(text or "").replace("đ", "d").replace("Đ", "D")
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


def _words_re(words) -> str:
    return r"(?<![\w])(?:" + "|".join(re.escape(w).replace(r"\ ", r"[\s-]+") for w in sorted(words, key=len, reverse=True)) + r")(?![\w])"


def _colors_in(text: str, vi: bool = False) -> List[str]:
    t = fold(text).replace("-", " ") if not vi else fold(text)
    out = []
    for base, (en, vn) in COLORS.items():
        words = vn if vi else tuple(w.replace("-", " ") for w in en)
        if re.search(_words_re(words), t):
            out.append(base)
    return out


def _item_of(text: str, vi: bool = False) -> Optional[str]:
    t = fold(text)
    best = None
    for base, (en, vn) in ITEMS.items():
        for w in (vn if vi else en):
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
    Mệnh đề có màu mà không có món (vd 'nửa dưới chuyển đỏ') → màu phụ của món ngay trước."""
    if vi is None:
        vi = not str(text or "").isascii()
    out: List[Dict] = []
    for clause in _split_clauses(text):
        head, _, tail = clause.partition(" with ")
        if any(fold(head).strip().startswith(p.strip()) or f" {p.strip()}" in f" {fold(head)}" for p in PATTERN_WORDS) \
                and _item_of(head, vi) is None:
            out.append({"mon": head.strip(), "hoa_tiet": True, "nguon": "suy"})
            continue
        item = _item_of(head if not vi else clause, vi)
        colors = _colors_in(head if not vi else clause, vi)
        if item is None:
            if colors and out and not out[-1].get("hoa_tiet"):
                out[-1]["mau_chinh"] += [c for c in colors if c not in out[-1]["mau_chinh"]]
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
            prev["mau_chinh"] += [c for c in colors if c not in prev["mau_chinh"]]
            continue
        out.append({"mon": item, "mau_chinh": colors[:2] + colors[2:], "dau_hieu": sign, "nguon": "suy"})
    return out


def _windows(prompt: str, item: str):
    """Mỗi lần prompt nhắc món: đoạn chữ từ ranh giới mệnh đề trước tới hết tên món (màu đứng trước danh từ)."""
    low = fold(prompt)
    for m in re.finditer(_words_re(ITEMS[item][0]), low):
        start = 0
        for b in BOUNDARY.finditer(low, 0, m.start()):
            start = b.end()
        yield low[start:m.end()]


def check(decl: List[Dict], prompt: str) -> List[Dict]:
    """[{mon, mau_chinh, trang_thai: co|thieu|thieu_mau|sai_mau, mau_thay, dau_hieu, dau_hieu_thay, muc}] — muc 'do' khi thiếu / sai màu
    (A18), None khi có. Họa tiết bỏ qua. `dau_hieu_thay` chỉ để báo (VÀNG ở K1a), không đổi trang_thai."""
    out = []
    for d in decl:
        if d.get("hoa_tiet"):
            continue
        item, want = d["mon"], list(d.get("mau_chinh") or [])
        wins = list(_windows(prompt, item))
        row = {"mon": item, "mau_chinh": want, "dau_hieu": d.get("dau_hieu"), "nguon": d.get("nguon"), "mau_thay": [],
               "dau_hieu_thay": None}
        if not wins:
            row.update(trang_thai="thieu", muc="do")
            out.append(row)
            continue
        status = "thieu_mau" if want else "co"
        for w in wins:
            seen = _colors_in(w)
            row["mau_thay"] += [c for c in seen if c not in row["mau_thay"]]
            dark = bool(re.search(r"\bdark\b", w))
            if not want:
                break
            if any(c in want for c in seen) or (dark and any(c in WEAK_DARK for c in want)):
                status = "co"
                break
            if seen and status == "thieu_mau":
                status = "sai_mau"
        if d.get("dau_hieu"):
            key = [x for x in re.findall(r"[a-z]+", fold(d["dau_hieu"])) if x not in INTENSITY]
            row["dau_hieu_thay"] = bool(key) and any(k in fold(prompt) for k in key)
        row.update(trang_thai=status, muc=None if status == "co" else "do")
        out.append(row)
    return out


OTHER_MARKERS = ("creature", "figure", "woman", "girl", "monster", "ghost")


def segment(prompt: str, markers: Dict[str, List[str]]) -> Dict[str, str]:
    """Chia prompt theo nhân vật: mỗi mệnh đề (, . ;) thuộc nhân vật được nhắc gần nhất (tên / từ đánh dấu); người lạ (OTHER_MARKERS
    không thuộc ai) → '_khac' — để màu tóc của 'bóng đen' không bị tính cho Kelly. Mệnh đề trước lần nhắc đầu: nếu chỉ một nhân vật thì
    thuộc nhân vật đó, không thì bỏ. Trả {tên: chữ}."""
    out: Dict[str, List[str]] = {k: [] for k in markers}
    owner, pending = None, []
    for clause in re.split(r"[,.;]", str(prompt or "")):
        low = fold(clause)
        hits = []
        for name, words in markers.items():
            for w in words:
                m = re.search(rf"(?<![\w]){re.escape(fold(w))}", low)
                if m:
                    hits.append((m.start(), name))
        if not hits:
            m = re.search(_words_re(OTHER_MARKERS), low)
            if m and not any(re.search(rf"(?<![\w]){re.escape(fold(w))}", low) for ws in markers.values() for w in ws):
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
    s = {"co": 0, "thieu": 0, "thieu_mau": 0, "sai_mau": 0}
    for r in rows:
        s[r["trang_thai"]] += 1
    return s
