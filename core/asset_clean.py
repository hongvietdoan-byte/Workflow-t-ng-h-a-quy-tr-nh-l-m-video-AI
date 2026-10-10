"""R1 — ảnh mẫu Kho bẩn / mô tả Kho lệch ảnh mẫu (kế hoạch kiểm soát `docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md` mục 4b
dòng 4–5, K1a). Hàm THUẦN, không gọi model, không ghi CSDL. Khâu L5 (Hồ sơ / ảnh mẫu Kho), một lần khi ảnh mẫu được duyệt / dùng.

(a) Claude KHAI thứ thấy trên ảnh mẫu theo enum `THAY` (N4: khai điều thấy, không khai đúng/sai) + mô tả ngắn → `check` so hồ sơ Kho
    (must_keep, identity, mô tả, khai_bao_chu): thứ không có trong hồ sơ → VÀNG `ngoai_ho_so` (#24 job 623: máu / tóc trên giếng
    `1.png` lan vào mọi shot). `nguoi_khac` / `nen_roi` không bao giờ thuộc hồ sơ → luôn VÀNG. Không khai / ngoài enum → VÀNG.
(b) Mô tả Kho ↔ khai báo (khai_bao_chu ưu tiên, chưa có thì must_keep) lệch MÀU CHÍNH cùng món → VÀNG `mo_ta_lech`
    (#418: mô tả 'đai đỏ ngang eo', ảnh mẫu = đai gai đen + khóa tam giác đỏ) — sửa Kho, không sửa prompt. Dùng
    `identity_declare.color_conflicts` (một nguồn so màu).
(c) Trạng thái ảnh mẫu do NGƯỜI duyệt: ô `anh_mau_sach` trong `assets.profile` {đường dẫn ảnh: {trang_thai, nguoi, ngay}}.
    Gói chỉ nên nhận ảnh `sach` — HIỆN CHỈ GHI trạng thái: `GOI_CHI_NHAN_SACH = False` → `ref_status(...)["chan"]` luôn False tới khi
    bật (sau cờ, đợt sau). Chưa nối vào pipeline.
"""
import re
import unicodedata
from typing import Dict, List, Optional

from core import identity_declare as idd

THAY = ("mau", "toc", "chu", "nguoi_khac", "nen_roi", "khac")          # trùng devsys/error_types.json R1 claude_khai[0].enum
LUON_NGOAI = ("nguoi_khac", "nen_roi")                                  # ảnh mẫu của MỘT vật không bao giờ cần người khác / nền rối
TU_KHOA = {
    "mau": ("blood", "bloody", "bloodstain", "bloodstained", "gore", "máu"),
    "toc": tuple(idd.ITEMS["hair"][0]) + ("tóc",),
    "chu": ("text", "logo", "letter", "letters", "lettering", "label", "sign", "writing", "chữ", "nhãn"),
}
KEY = "anh_mau_sach"
TRANG_THAI_ANH = ("sach", "chua_duyet", "ban")
GOI_CHI_NHAN_SACH = False          # chỉ ghi trạng thái; bật khi nối gói (cờ TẮT tới lúc đó)
STOP = {"trên", "dưới", "quanh", "trong", "ngoài", "của", "with", "from", "around", "near", "the", "and", "một", "những", "các"}


def _low(text) -> str:
    return unicodedata.normalize("NFC", str(text or "")).lower()


def _has(words, text: str) -> bool:
    return any(re.search(r"(?<![\w])" + re.escape(_low(w)) + r"(?![\w])", text) for w in words)


def profile_text(profile: Optional[Dict], mo_ta: str = "") -> str:
    p = profile or {}
    parts = [p.get("must_keep"), p.get("identity"), mo_ta]
    for it in p.get(idd.KBC_KEY) or []:
        if isinstance(it, dict):
            parts += [it.get("mon"), it.get("dau_hieu")] + list(it.get("dong_nghia") or []) + list(it.get("hoa_tiet") or [])
    parts = [", ".join(map(str, x)) if isinstance(x, list) else x for x in parts]
    return _low(" ; ".join(str(x) for x in parts if x))


def _in_profile(loai: str, mo_ta: str, text: str) -> bool:
    if loai in LUON_NGOAI:
        return False
    if loai in TU_KHOA and _has(TU_KHOA[loai], text):
        return True
    if loai == "khac":
        words = [w for w in re.findall(r"[\w-]+", _low(mo_ta)) if len(w) >= 4 and w not in STOP]
        return bool(words) and _has(words, text)
    return False


def check(thay, profile: Optional[Dict], mo_ta: str = "") -> List[Dict]:
    """thay = [{loai ∈ THAY, mo_ta}] Claude khai thấy trên ảnh mẫu (None = chưa khai) → [{muc, ma, loai?, mon?, mo_ta?, loi}].
    Rỗng = qua. Mọi mục hiện là VÀNG (chưa đo báo nhầm)."""
    out: List[Dict] = []
    text = profile_text(profile, mo_ta)
    if not text.strip():
        out.append({"muc": "vang", "ma": "khong_co_ho_so", "loi": "hồ sơ Kho không có must_keep / mô tả / khai_bao_chu — không có gì để so"})
    if thay is None:
        out.append({"muc": "vang", "ma": "chua_khai", "loi": "chưa có khai báo thứ thấy trên ảnh mẫu — ảnh chưa được coi là sạch"})
    for it in thay or []:
        loai = it.get("loai") if isinstance(it, dict) else None
        if loai not in THAY:
            out.append({"muc": "vang", "ma": "ngoai_enum", "loai": loai,
                        "loi": f"khai '{it}' ngoài enum ({', '.join(THAY)}) — không kết luận được"})
            continue
        if text.strip() and _in_profile(loai, it.get("mo_ta") or "", text):
            continue
        out.append({"muc": "vang", "ma": "ngoai_ho_so", "loai": loai, "mo_ta": it.get("mo_ta"),
                    "loi": f"ảnh mẫu có '{loai}' ({it.get('mo_ta') or '—'}) không có trong hồ sơ Kho — làm sạch ảnh hoặc người duyệt"})
    if (profile or {}) and str(mo_ta or "").strip():
        decl, _ = idd.declare_from_profile(profile)
        for c in idd.color_conflicts(mo_ta, decl):
            out.append({"muc": "vang", "ma": "mo_ta_lech", "mon": c["mon"], "loi": c["loi"]})
    return out


def verdict(rows: List[Dict]) -> str:
    return "do" if any(r["muc"] == "do" for r in rows) else ("vang" if rows else "qua")


def _key(path: str) -> str:
    return str(path or "").replace("\\", "/").strip().lower()


def with_state(profile: Optional[Dict], anh: str, trang_thai: str, nguoi: Optional[str] = None, ngay: Optional[str] = None) -> Dict:
    """Bản sao hồ sơ có trạng thái ảnh mẫu `anh` (người duyệt). Không ghi CSDL — người gọi lưu qua assets."""
    if trang_thai not in TRANG_THAI_ANH:
        raise ValueError(f"trạng thái ảnh mẫu '{trang_thai}' ngoài {TRANG_THAI_ANH}")
    p = dict(profile or {})
    states = dict(p.get(KEY) or {})
    states[_key(anh)] = {"trang_thai": trang_thai, "nguoi": nguoi, "ngay": ngay}
    p[KEY] = states
    return p


def ref_status(profile: Optional[Dict], anh: str, chan: Optional[bool] = None) -> Dict:
    """{anh, trang_thai, goi_nhan, chan, ly_do}: gói chỉ nhận ảnh `sach`; `chan` chỉ True khi bật (mặc định GOI_CHI_NHAN_SACH=False)."""
    st = ((profile or {}).get(KEY) or {}).get(_key(anh)) or {}
    tt = st.get("trang_thai") if st.get("trang_thai") in TRANG_THAI_ANH else "chua_duyet"
    ok = tt == "sach"
    gate = GOI_CHI_NHAN_SACH if chan is None else chan
    return {"anh": anh, "trang_thai": tt, "goi_nhan": ok, "chan": bool(gate and not ok),
            "ly_do": None if ok else f"ảnh mẫu '{anh}' chưa được người duyệt 'sach' (đang {tt})"}
