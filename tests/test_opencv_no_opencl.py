"""OpenCV nạp ở MỘT chỗ (core.clip_measure._cv) và luôn tắt OpenCL.

15/10: OpenCV 5.0 + driver GPU máy chính treo vô hạn ở ORB detectAndCompute khi OpenCL bật (CPU 0,012 s). Khóa: sau khi nạp qua _cv,
cv2.ocl.useOpenCL() là False (kể cả khi code khác đã bật trước), và không module nào trong core/ tự `import cv2`.
"""
import re
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")

CORE = Path(__file__).resolve().parents[1] / "core"


def test_loading_cv2_through_core_turns_opencl_off():
    from core import framing_guard
    cv2.ocl.setUseOpenCL(True)          # some other code turned it on first
    assert framing_guard._cv().ocl.useOpenCL() is False


def test_orb_on_a_detailed_picture_returns():
    import numpy as np
    from core import framing_guard
    img = np.random.default_rng(1).integers(0, 255, (360, 640, 3), dtype=np.uint8)
    shape, k, d = framing_guard._features(img)
    assert len(k) > 0 and cv2.ocl.useOpenCL() is False


def test_no_core_module_imports_cv2_on_its_own():
    own = [f"{p.name}:{i}" for p in sorted(CORE.rglob("*.py")) if p.name != "clip_measure.py"
           for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
           if re.match(r"\s*(import cv2\b|from cv2\b)", line)]
    assert not own, f"nạp cv2 qua core.clip_measure._cv() (tắt OpenCL), không tự import: {own}"
