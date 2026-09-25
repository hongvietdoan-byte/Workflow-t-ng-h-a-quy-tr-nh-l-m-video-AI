"""Editor: subtitles never sit on a face (knowledge/editor/safe_zones.md rule 2-3, kế hoạch V4 5.1). The subtitle stays in ONE place
for the whole video (bottom band of the common safe box) and a whole line moves to the top band only when its shot puts eyes or mouth
in the bottom band — mostly close-ups on a vertical frame, where the bottom band of the safe box (about 55-64 % of the height) is
exactly the mouth and chin.

Where the face is: on the real frame at the line's time when the YuNet face model is on this computer (OpenCV FaceDetectorYN,
data/models/face_detection_yunet_2023mar.onnx, downloaded 2026-09-25 with the person's permission; FACE_MODEL names another file) —
on the 2A pictures it found every Free Fire face (confidence 0.87-0.95). Without it, from the DP's shot table (shot size + angle words).
A composited shot (gói bối cảnh) knows its character box exactly and can pass it as `zones` directly.

Numbers are fractions of the frame height for a 9:16 frame, eyes-to-mouth span of the main face; measured on the 2A frames by eye,
to be refined on real frames.
"""
import json
import os
import subprocess
import tempfile
from typing import Callable, Dict, List, Optional, Tuple

FACE_MODEL = os.path.join(os.path.dirname(__file__), "..", "data", "models", "face_detection_yunet_2023mar.onnx")
MIN_FACE = 0.03              # faces smaller than 3 % of the frame height (far people in a wide shot) do not move a subtitle

# eyes-to-mouth span (top, bottom) of the main face by shot size, 9:16 frame
KEEP_CLEAR = {"ECU": (0.20, 0.80), "CU": (0.30, 0.66), "MCU": (0.22, 0.46), "MS": (0.15, 0.32), "MLS": (0.14, 0.26)}
_RAISED = ("low angle", "from below", "góc thấp")
_LOWERED = ("high angle", "from above", "góc cao")


def keep_clear(data: Dict) -> Optional[Tuple[float, float]]:
    """(top, bottom) of the part of the frame a subtitle must not cover for this shot, or None (wide shot: faces are small)."""
    size = str(data.get("size") or data.get("shot_size") or "").upper()
    span = KEEP_CLEAR.get(size)
    if span is None:
        return None
    words = f"{data.get('start_frame') or ''} {data.get('angle') or ''}".lower()
    shift = 0.0
    if any(w in words for w in _RAISED) or str(data.get("angle") or "").lower() == "low":
        shift = 0.05                      # camera below the face: the face sits lower in the frame
    elif any(w in words for w in _LOWERED) or str(data.get("angle") or "").lower() == "high":
        shift = -0.04
    if "foreground" in words or "tiền cảnh" in words:
        shift += 0.03
    return (max(0.0, span[0] + shift), min(1.0, span[1] + shift))


def zones(conn, project_id: int) -> Dict[int, Tuple[float, float]]:
    """Scene idx -> keep-clear span for every shot of the project that has one."""
    out = {}
    for r in conn.execute("SELECT idx, data FROM scenes WHERE project_id=?", (project_id,)):
        span = keep_clear(json.loads(r["data"] or "{}"))
        if span is not None:
            out[r["idx"]] = span
    return out


def _overlap(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def bands(height: int, fontsize: int, lines: int, bottom_margin: float, top_margin: float) -> Dict[str, Tuple[float, float]]:
    """Where a subtitle of `lines` lines sits (fractions of the height) in the bottom and the top position."""
    h = lines * fontsize * 1.25 / height
    bottom = (1.0 - bottom_margin - h, 1.0 - bottom_margin)
    top = (top_margin, top_margin + h)
    return {"bottom": bottom, "top": top}


def model_path() -> Optional[str]:
    path = os.environ.get("FACE_MODEL") or FACE_MODEL
    return path if os.path.exists(path) else None


def face_spans(image_path: str, model: Optional[str] = None) -> Optional[List[Tuple[float, float]]]:
    """(top, bottom) of every face on a picture, fractions of its height; None when no detector is available (not the same as [])."""
    model = model or model_path()
    if not model:
        return None
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return None
        h, w = img.shape[:2]
        det = cv2.FaceDetectorYN.create(model, "", (w, h), 0.6, 0.3, 50)
        _, faces = det.detect(img)
    except Exception:  # noqa: BLE001 - a broken model / frame: fall back to the shot table
        return None
    out = []
    for f in (faces if faces is not None else []):
        top, height = float(f[1]) / h, float(f[3]) / h
        if height >= MIN_FACE:
            out.append((max(0.0, top), min(1.0, top + height)))
    return out


def video_spans(video: str, cues: List, ffmpeg: str, model: Optional[str] = None) -> Dict[int, Tuple[float, float]]:
    """Cue index -> the band its faces cover, read on the real frames at the start, middle and end of the line (one span that
    covers every face seen). Cues without a face are left out; {} when no detector is available."""
    model = model or model_path()
    if not model:
        return {}
    out = {}
    work = tempfile.mkdtemp()
    try:
        for i, c in enumerate(cues):
            spans = []
            for n, t in enumerate((c.start + 0.15, (c.start + c.end) / 2, max(c.start, c.end - 0.15))):
                frame = os.path.join(work, f"c{i}_{n}.png")
                subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", f"{max(t, 0):.2f}", "-i", video, "-frames:v", "1", frame],
                               capture_output=True, timeout=60)
                found = face_spans(frame, model) if os.path.exists(frame) else None
                spans += found or []
            if spans:
                out[i] = (min(s[0] for s in spans), max(s[1] for s in spans))
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    return out


def placements(cues: List, zone_of: Dict[int, Tuple[float, float]], height: int, fontsize: int, lines_of, bottom_margin: float,
               top_margin: float, seen: Optional[Dict[int, Tuple[float, float]]] = None) -> Dict[int, str]:
    """Cue index -> "top" for the lines that would cover a face at the bottom and are clear (or clearer) at the top.
    seen: cue index -> faces found on the real frames (wins over the shot-table guess for that line)."""
    out = {}
    for i, c in enumerate(cues):
        span = (seen or {}).get(i) or zone_of.get(getattr(c, "scene", None))
        if span is None:
            continue
        b = bands(height, fontsize, lines_of(c), bottom_margin, top_margin)
        low, high = _overlap(b["bottom"], span), _overlap(b["top"], span)
        if low > 0 and high < low:
            out[i] = "top"
    return out
