"""Features that change what is sent to a paid model but have not passed a real test (rule 5 of docs/CHUAN_XAY_DUNG.md): off by default
and kept out of the autopilot until a real run closes their test. `FEATURE_<NAME>=1` switches one on (e.g. for the GĐ-I trials).
When a real test passes, set `verified` to True here with the date and the report that shows it."""
import os
from typing import Dict

FEATURES: Dict[str, Dict] = {
    "layout_to_model": {
        "label": "Gửi ảnh bố cục ghép (nền map + hình cắt nhân vật) cho model ảnh",
        "verified": False,
        "why": "GĐ6 (R7/L1): model chép luôn góc máy từ trên cao và cỡ người tí hon của ảnh ghép, bất kể cỡ cảnh của shot",
    },
    "chain_previous_auto": {
        "label": "Tự nối ảnh shot trước làm ảnh tham chiếu trong cùng chuỗi",
        "verified": False,
        "why": "GĐ6 (F8/I2): nối bất kể cỡ cảnh/góc máy → shot cận kéo theo bố cục toàn cảnh của shot trước",
    },
    "voice_check_redo": {
        "label": "Chạy tự động: tạo lại giọng thoại bị cờ lỗi (cắt/thiếu chữ/ngắt quãng) một lần",
        "verified": False,
        "why": "AU-f mới (2026-09-24): ngưỡng độ dài/im lặng và so chữ nghe được chưa đo trên giọng Việt thật — cờ sai thì trả tiền TTS vô ích",
    },
    "setcheck_autofix": {
        "label": "QC đồng bộ cả bộ ảnh tự gen lại ảnh lệch (autopilot)",
        "verified": False,
        "why": "GĐ6 (R3/I4): chuẩn theo số đông của bộ ảnh, sửa sai người (Kenta→Maxim) rồi tự trả tiền gen lại",
    },
}


def on(name: str) -> bool:
    """True when the feature passed its real test, or the person switched it on with FEATURE_<NAME>=1 (0 switches it off)."""
    env = os.environ.get("FEATURE_" + name.upper(), "").strip().lower()
    if env in ("1", "true", "on", "yes"):
        return True
    if env in ("0", "false", "off", "no"):
        return False
    return bool(FEATURES[name]["verified"])


def pending() -> Dict[str, Dict]:
    """Features still waiting for their real test (shown to the person so an off feature is never a mystery)."""
    return {k: v for k, v in FEATURES.items() if not on(k)}
