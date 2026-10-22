"""V3.1 M2.2 — field readers BYĐ A2a–A2f (docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md mục 4, 4.1).

Cờ MẸ `byd_fields` (TẮT) + mỗi reader một cờ con `byd_fields_a2<x>` (TẮT, cần mẹ). Cờ tắt ⇒ nơi gọi đi đường cũ y nguyên (gói gửi +
hash lineage giống từng byte, golden #24 / #27). Cờ bật:
- BYĐ v2 có trường → đọc trường (provenance `byd_v2`);
- BYĐ v1 / thiếu trường / chưa có BYĐ → đường cũ (đọc chữ / dò bí danh / suy từ chỗ đứng) + một dòng ⚙ Chẩn đoán `byd_fallback`
  (luật 1 CHUAN_XAY_DUNG: không im lặng khi thiếu đầu vào) — KHÔNG chặn, không đổi gói so với đường cũ.
Không gọi model, không ghi `scenes.data`, 0 USD."""
from typing import Dict, List, Optional

from . import shot_intent

MOTHER = "byd_fields"
CODES = ("a2a", "a2b", "a2c", "a2d", "a2e", "a2f")
FALLBACK = "byd_fallback"          # mã diag: reader bật nhưng BYĐ không có trường → đường cũ
MISMATCH = "byd_field_mismatch"    # mã diag: trường v2 trỏ tới thứ không dùng được (kho_id không thuộc dự án / không ảnh) — REVIEW


def flag(code: str) -> str:
    if code not in CODES:
        raise ValueError(f"reader BYĐ lạ: {code!r}")
    return f"{MOTHER}_{code}"


def mother_on() -> bool:
    from . import features
    return features.on(MOTHER)


def enabled(code: str) -> bool:
    """Reader `code` chạy khi CẢ cờ mẹ và cờ con bật (cờ con một mình = không tác dụng, features.unmet_all nói ra)."""
    from . import features
    return features.on(MOTHER) and features.on(flag(code))


def is_v2(scene) -> bool:
    return shot_intent.version(shot_intent.byd_of(scene)) == shot_intent.BYD_V


def note(conn, code: str, scene, message: str, *, kind: str = FALLBACK, project_id: Optional[int] = None,
         stage: str = "image") -> None:
    """Một dòng ⚙ Chẩn đoán (mức warn) — không bao giờ làm vỡ nơi gọi (diag.record tự giữ dòng không ghi được)."""
    if conn is None:
        return
    try:
        from . import diag
        scene_id = scene.get("id") if isinstance(scene, dict) else None
        sid = scene_id if isinstance(scene_id, int) else None
        diag.record(conn, stage, "warn", f"BYĐ {code.upper()}: {message}", code=kind, project_id=project_id, scene_id=sid)
    except Exception:  # noqa: BLE001 - chẩn đoán không được làm hỏng đường gen
        pass


def kho_ids(scene, groups=("vat", "thanh_phan")) -> Optional[List[int]]:
    """Mã Kho BYĐ v2 khai trong các nhóm (thứ tự khai, không trùng). None = không phải v2 hoặc có mục không khai `kho_id` (v2 bắt buộc —
    thiếu thì nơi gọi KHÔNG đoán phần còn lại: đi đường cũ + byd_fallback)."""
    if not is_v2(scene):
        return None
    out: List[int] = []
    for g in groups:
        items, _, _ = shot_intent.read(scene, g, [])
        if not isinstance(items, list):
            return None
        for it in items:
            if not isinstance(it, dict):
                return None
            k = it.get("kho_id")
            if type(k) is not int:
                if g == "thanh_phan":
                    continue          # người không khai kho_id: nhân vật đi đường link_characters, không phải ảnh vật
                return None
            if k not in out:
                out.append(k)
    return out


# ---- lineage (mục 4.1, G22) -------------------------------------------------------------------------------------------------
IMAGE_GROUPS = ("thanh_phan", "vat", "noi_chon", "khung")
NOI_CHON_DERIVED = ("thoi_gian", "thoi_tiet")   # bản chép của shot time / weather (trigger) — đã có trong hash qua `weather`


def image_part(scene_data: Dict) -> Optional[Dict]:
    """Phần BYĐ vào image_spec_hash khi cờ mẹ bật; None (không thêm khóa — hash cũ) khi cờ tắt hoặc shot chưa có BYĐ."""
    byd = shot_intent.byd_of(scene_data)
    if byd is None or not mother_on():
        return None
    part = {g: byd.get(g) for g in IMAGE_GROUPS if g in byd}
    if isinstance(part.get("noi_chon"), dict):
        part["noi_chon"] = {k: v for k, v in part["noi_chon"].items() if k not in NOI_CHON_DERIVED}
    return part


def motion_part(scene_data: Dict) -> Optional[Dict]:
    byd = shot_intent.byd_of(scene_data)
    if byd is None or not mother_on():
        return None
    may = byd.get("may") if isinstance(byd.get("may"), dict) else {}
    return {"hanh_dong": byd.get("hanh_dong"), "chuyen_dong": may.get("chuyen_dong")}
