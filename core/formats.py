"""Frame format (aspect ratio) of a project: one choice drives the image size, the video ratio, the previz canvas, the render and
the subtitle margins, so a vertical short is vertical from the first picture instead of letterboxed at the end.

`projects.aspect` NULL = the v1 behaviour (provider defaults from the environment, 16:9).
"""
from typing import Dict, Optional, Tuple

DEFAULT_NEW = "9:16"                                   # new projects: most Free Fire clips go to TikTok / Reels / Shorts

ASPECTS: Dict[str, Dict] = {
    "16:9": {"label": "Ngang 16:9 (YouTube, màn hình)", "deepix": "2048x1152", "clip": "16:9", "canvas": (1920, 1080),
             "cell": (480, 270), "render": (1920, 1080)},
    "9:16": {"label": "Dọc 9:16 (TikTok, Reels, Shorts)", "deepix": "1152x2048", "clip": "9:16", "canvas": (1080, 1920),
             "cell": (270, 480), "render": (1080, 1920)},
    "1:1": {"label": "Vuông 1:1 (bài đăng)", "deepix": "1536x1536", "clip": "1:1", "canvas": (1080, 1080),
            "cell": (360, 360), "render": (1080, 1080)},
}


def project_aspect(row) -> Optional[str]:
    """The project's aspect, or None for a project made before v2 (keeps the provider defaults)."""
    try:
        value = row["aspect"]
    except (KeyError, IndexError):
        return None
    return value if value in ASPECTS else None


def spec(aspect: Optional[str]) -> Dict:
    return ASPECTS.get(aspect or "16:9", ASPECTS["16:9"])


def canvas(aspect: Optional[str]) -> Tuple[int, int]:
    return spec(aspect)["canvas"]


def label(aspect: Optional[str]) -> str:
    return spec(aspect)["label"] if aspect else "Mặc định cũ (16:9, theo cấu hình máy)"


def director_line(aspect: Optional[str]) -> str:
    """One sentence for the Director / Motion prompt, so framing and blocking are thought for the right frame."""
    if not aspect:
        return ""
    return {"16:9": "Khung hình NGANG 16:9: bố cục trải theo chiều ngang.",
            "9:16": "Khung hình DỌC 9:16 (điện thoại): đặt chủ thể theo chiều dọc, ưu tiên cỡ trung/cận, tránh xếp nhiều người "
                    "dàn ngang; chừa khoảng trên/dưới cho chữ.",
            "1:1": "Khung hình VUÔNG 1:1: chủ thể ở giữa, bố cục gọn."}[aspect]
