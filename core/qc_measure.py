"""Tầng 0 của Tổ QC — code đo trước, model phán sau (docs/THIET_KE_TO_QC_2026-10-01.md mục 7, quyết định 19a: không dùng Pose).

  faces(path)            YuNet face boxes (fractions), sorted left → right
  gaze(path, box)        where a face's eyes look: "left" / "center" / "right" of the FRAME + confidence, from the MediaPipe face
                         landmarker's iris points against the eye corners (data/models/face_landmarker.task, already on this computer)
  sky(path)              colour of the top band: B−R and brightness (day / sunset / night reading)
  measure_frame(...)     the per-assertion code results: certain_ok / certain_fail / uncertain / not_measurable + numbers

Thresholds marked "đặt từ bộ đo vàng" are first guesses; GĐ3 sets them from labelled frames (mục 7.5), never trusted before.
"""
import re
from typing import Dict, List, Optional, Tuple

GAZE_SIDE = 0.12        # iris offset from the eye's middle, as a share of the eye width, to call a side (đặt từ bộ đo vàng)
GAZE_SURE = 0.20        # offset at which the side is "certain"
SKY_SUNSET_BR = -10     # top band B−R below this reads as warm sky (sunset / golden hour) — #8 lượt 3: sunset −29, midday +110…+128


def faces(path: str) -> Optional[List[Tuple[float, float, float, float]]]:
    from . import text_placement
    boxes = text_placement.face_boxes(path)
    return None if boxes is None else sorted(boxes, key=lambda b: b[0])


_landmarker = None


def _iris_offset(crop) -> Optional[float]:
    """Mean over both eyes of (iris x − eye middle x) / eye width on a face crop (BGR); negative = toward image-left. None when no mesh."""
    global _landmarker
    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    from .clip_measure import _cv, landmark_model_path
    model = landmark_model_path()
    if not model:
        return None
    if _landmarker is None:
        _landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model), running_mode=vision.RunningMode.IMAGE, num_faces=1,
            min_face_detection_confidence=0.3))
    rgb = np.ascontiguousarray(_cv().cvtColor(crop, _cv().COLOR_BGR2RGB))
    found = _landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).face_landmarks
    if not found or len(found[0]) < 478:
        return None
    p = found[0]
    offsets = []
    for iris, a, b in ((468, 33, 133), (473, 362, 263)):          # the two eyes: iris centre, eye corners
        lo, hi = min(p[a].x, p[b].x), max(p[a].x, p[b].x)
        width = hi - lo
        if width > 1e-4:
            offsets.append((p[iris].x - (lo + hi) / 2) / width)
    return sum(offsets) / len(offsets) if offsets else None


def gaze(path: str, box: Tuple[float, float, float, float]) -> Dict:
    """{"side": left/center/right/None, "offset", "confidence": high/medium/low} for one face box of a frame."""
    from .clip_measure import _cv
    cv2 = _cv()
    img = cv2.imread(path)
    if img is None:
        return {"side": None, "offset": None, "confidence": "low", "why": "không đọc được ảnh"}
    H, W = img.shape[:2]
    x0, y0, x1, y1 = box
    w, h = (x1 - x0) * W, (y1 - y0) * H
    m = 0.6
    X0, Y0 = int(max(0, x0 * W - w * m)), int(max(0, y0 * H - h * m))
    X1, Y1 = int(min(W, x1 * W + w * m)), int(min(H, y1 * H + h * m))
    if X1 - X0 < 20 or Y1 - Y0 < 20:
        return {"side": None, "offset": None, "confidence": "low", "why": "mặt quá nhỏ"}
    crop = img[Y0:Y1, X0:X1]
    scale = 384 / max(1, X1 - X0)
    off = _iris_offset(cv2.resize(crop, None, fx=scale, fy=scale))
    if off is None:
        return {"side": None, "offset": None, "confidence": "low", "why": "không dựng được lưới mặt"}
    side = "left" if off < -GAZE_SIDE else ("right" if off > GAZE_SIDE else "center")
    conf = "high" if abs(off) >= GAZE_SURE else ("medium" if abs(off) >= GAZE_SIDE else "low")
    return {"side": side, "offset": round(off, 3), "confidence": conf}


def sky(path: str) -> Optional[Dict]:
    """Mean colour of the top 12 % of the frame: {"b_minus_r", "brightness", "reading": day / warm / dark}."""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    w, h = im.size
    import numpy as np
    r, g, b = (float(v) for v in np.asarray(im.crop((0, 0, w, max(1, int(h * 0.12)))).resize((64, 8))).reshape(-1, 3).mean(axis=0))
    bright = (r + g + b) / 3
    reading = "dark" if bright < 55 else ("warm" if b - r < SKY_SUNSET_BR else "day")
    return {"b_minus_r": round(b - r), "brightness": round(bright), "reading": reading}


def _target_side(target: str, frame_names: List[str], layout: Dict[str, str]) -> Optional[str]:
    """Which frame side a gaze target is on: 'frame-left / off left' words, or another person's layout side."""
    t = str(target or "").lower()
    for side in ("left", "right"):
        if re.search(rf"(frame[- ]{side}|{side} of (the )?frame|off[- ]?(screen|frame) {side}|{side} off[- ]?(screen|frame)|\bto the {side}\b)", t):
            return side
    for n in frame_names:
        if n.lower() in t and layout.get(n) in ("left", "right"):
            return layout[n]
    return None


def measure_frame(path: str, data: Dict, assertions: List[Dict]) -> Dict:
    """Code results for the assertions a code measure can speak to: {assertion id: {"status", "value", "note"}}, plus "_faces" and
    "_sky". Status: certain_ok / certain_fail / uncertain / not_measurable. Nothing is decided here that a person has not set a
    threshold for: gaze and sky stay 'uncertain' unless the reading is strong."""
    out: Dict[str, Dict] = {}
    boxes = faces(path)
    out["_faces"] = {"count": None if boxes is None else len(boxes), "boxes": [[round(v, 3) for v in b] for b in boxes or []]}
    cast = [str(c).upper() for c in data.get("characters") or []]
    layout = {a["subject"]: a["expected"] for a in assertions if a["type"] == "layout"}
    for a in assertions:
        if a["type"] == "count":
            if boxes is None:
                out[a["id"]] = {"status": "not_measurable", "note": "không có bộ dò mặt"}
            elif len(boxes) > len(cast):
                out[a["id"]] = {"status": "uncertain", "value": len(boxes), "note": f"{len(boxes)} mặt, bảng shot {len(cast)} người "
                                                                                    "(bộ dò hay nhầm tay thành mặt — model xác nhận)"}
            else:
                out[a["id"]] = {"status": "uncertain", "value": len(boxes), "note": f"{len(boxes)} mặt thấy được (người quay lưng không có mặt)"}
        elif a["type"] == "gaze":
            # the face of this person: by layout side when the shot says it, else the only face
            if not boxes:
                out[a["id"]] = {"status": "not_measurable", "note": "không thấy mặt"}
                continue
            side = layout.get(a["subject"])
            if len(boxes) == 1 or side not in ("left", "right"):
                box = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))   # the main (largest) face when the side is not said
            else:
                box = boxes[0] if side == "left" else boxes[-1]
            if side not in ("left", "right") and len(boxes) > 1:
                areas = sorted((b[2] - b[0]) * (b[3] - b[1]) for b in boxes)
                if areas[-1] < 2 * areas[-2]:                                    # two faces of similar size: cannot tell whose
                    out[a["id"]] = {"status": "not_measurable", "note": "nhiều mặt cỡ gần nhau, không biết mặt nào của người này"}
                    continue
            g = gaze(path, box)
            want = _target_side(a["expected"], cast, layout)
            if g["side"] is None or want is None:
                out[a["id"]] = {"status": "not_measurable" if g["side"] is None else "uncertain", "value": g,
                                "note": g.get("why") or "không suy ra được hướng mong đợi từ chữ bảng shot"}
            elif g["confidence"] == "high":
                out[a["id"]] = {"status": "certain_ok" if g["side"] == want else "certain_fail", "value": g,
                                "note": f"mắt nhìn về {g['side']} khung, cần {want}"}
            else:
                out[a["id"]] = {"status": "uncertain", "value": g, "note": f"mắt nghiêng về {g['side']} (độ chắc {g['confidence']}), cần {want}"}
        elif a["type"] == "light":
            sk = sky(path)
            want = str((a["expected"] or {}).get("time") or "").lower()
            if sk is None or not want:
                out[a["id"]] = {"status": "not_measurable"}
            elif want in ("day", "noon", "midday", "morning") and sk["reading"] == "warm":
                out[a["id"]] = {"status": "uncertain", "value": sk, "note": f"trời ngả ấm (B−R {sk['b_minus_r']}) trong cảnh ban ngày — soi C4"}
            else:
                out[a["id"]] = {"status": "uncertain", "value": sk, "note": f"trời {sk['reading']} (B−R {sk['b_minus_r']})"}
    out["_sky"] = sky(path)
    return out
