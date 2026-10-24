"""Áp ý đồ máy vào bản JSON N4; không ghi state/máy hoặc chạy đo."""
import copy
import hashlib
import json
import math

from core.stage_grid import CAMERA_SIDES


def controls_revision(answer):
    """Khóa theo ý nghĩa JSON, không đưa nội dung người dùng vào widget key."""
    canonical = json.dumps(answer, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def answer_specs(answer):
    if not isinstance(answer, dict):
        return []
    if isinstance(answer.get("shot_specs"), list):
        return [s for s in answer["shot_specs"] if isinstance(s, dict)]
    rows = answer.get("shots")
    if not isinstance(rows, list):
        return []
    return [r["shot_spec"] for r in rows if isinstance(r, dict)
            and r.get("ket_luan") == "sua_may" and isinstance(r.get("shot_spec"), dict)]


def apply_camera_controls(answer, selections):
    if not isinstance(answer, dict) or not isinstance(selections, dict):
        raise ValueError("Câu trả lời và lựa chọn máy phải là đối tượng JSON.")
    result = copy.deepcopy(answer)
    specs = answer_specs(result)
    for shot, choice in selections.items():
        if not isinstance(choice, dict):
            raise ValueError("Lựa chọn máy phải là đối tượng theo từng shot.")
        matches = [s for s in specs if s.get("shot") == shot]
        if len(matches) != 1:
            raise ValueError("Lựa chọn máy không còn khớp đúng một shot_spec; nạp lại JSON.")
        spec = matches[0]
        side = choice.get("camera_side")
        if side is not None:
            if side not in CAMERA_SIDES:
                raise ValueError("Phía máy phải là front/back/left/right.")
            spec["camera_side"] = side
        minimums = choice.get("minimums")
        if minimums is not None and not isinstance(minimums, dict):
            raise ValueError("Ngưỡng vật phụ phải là đối tượng theo khóa vật.")
        if minimums and not isinstance(spec.get("thanh_phan"), list):
            raise ValueError("JSON cần danh sách thanh_phan trước khi áp ngưỡng vật phụ.")
        for key, minimum in (minimums or {}).items():
            components = [c for c in spec["thanh_phan"] if isinstance(c, dict) and c.get("vat") == key and c.get("vai") == "phu"]
            if len(components) != 1:
                raise ValueError("Vật phụ đã đổi trong JSON; chọn lại ngưỡng thấy.")
            if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not math.isfinite(minimum) or not 0 <= minimum <= 100:
                raise ValueError("Ngưỡng thấy phải là số hữu hạn từ 0 đến 100%.")
            components[0]["thay_min"] = minimum
    return result
