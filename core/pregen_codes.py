"""V3.1 M2.7 — bộ mã chung của lớp kiểm TRƯỚC gen (ảnh: core/image_pregen.py, video: core/video_pregen.py). Chỉ hằng + mô tả, 0 logic.

Một lỗi = {ma, muc: DO | VANG, ly_do}. `ma` là khóa dưới đây; giá trị chuỗi của mã video cũ giữ nguyên (test K3 cũ không đổi).
`ERRORS` ánh xạ mã → mã lỗi gốc trong sổ `devsys/errors.json` (D09: diag = lần phát sinh, sổ = định nghĩa) để đếm lần xảy ra theo lỗi gốc.
Thiết kế: docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md mục 3.
"""
from __future__ import annotations

from typing import Dict, Tuple

DO, VANG = "do", "vang"
REVIEW = "review"                       # mức shadow: lỗi ĐỎ được ghi để người xem, không giữ job (cờ image_pregen)

# mã: (loại — chung / anh / video, mô tả ngắn tiếng Việt)
CODES: Dict[str, Tuple[str, str]] = {
    # chung ảnh + video
    "tham_chieu": ("chung", "ảnh / video tham chiếu: đọc được, trong trần số ảnh của model, không bị bỏ im lặng"),
    "van_tay": ("chung", "vân tay gói: gen lại phải đổi đầu vào so với lần trước (N10)"),
    "byd": ("chung", "chưa có bảng ý đồ shot (BYĐ)"),
    "byd_draft": ("chung", "BYĐ nháp do code dựng (shot chèn) — chờ người duyệt ở Bước 3"),
    "ky_tu": ("chung", "prompt vượt trần ký tự của model, câu bắt buộc không được cắt (M2.8)"),
    "khoi_giu_cho": ("chung", "nền 3D còn khối giữ chỗ mà prompt thiếu câu giải thích khối (M2.4, G1)"),
    "loi_kiem": ("chung", "lớp kiểm trước gen lỗi — chưa kiểm được"),
    # ảnh
    "nen_3d": ("anh", "gói ảnh mang nền 3D không phải máy hiện tại của shot (plate_package_mixed)"),
    "cong_thuc": ("anh", "prompt ảnh sai công thức (prompt_formula)"),
    "bo_cuc_kho": ("anh", "nơi chốn có bố cục trong Kho nhưng dự án chưa nối (assets.missing_layout)"),
    # video (K3, core/video_pregen.py)
    "khung_dau": ("video", "khung đầu = ảnh đã duyệt hiện hành của shot"),
    "khung_cuoi": ("video", "khung cuối đã duyệt + khớp ket_thuc BYĐ"),
    "thoi_luong": ("video", "thời lượng hợp model + thoại"),
    "chuyen_dong": ("video", "motion đủ nhịp đầu–đỉnh–cuối + chuyển động máy trong enum"),
}

# mã → lỗi gốc trong devsys/errors.json (chỉ mã đã có lỗi gốc; tests/test_image_pregen.py kiểm mọi id có trong sổ)
ERRORS: Dict[str, Tuple[str, ...]] = {
    "khoi_giu_cho": ("P31-G1",),
    "ky_tu": ("P31-G13", "P31-G54"),
    "khung_dau": ("P31-G28",),
}


def describe(ma: str) -> str:
    """Mô tả một mã (mã lạ → chính mã, không ném)."""
    return CODES.get(ma, ("", ma))[1]
