"""Checks of a location-pack shot (kế hoạch V4 1.6 step 7) — measured, no AI:

  background_score   how much of the plate a clip (or a picture) kept, outside the character: edge structure + colour, 0..1, sampled
                     every 0.5 s. Mode 1 (the composite as the start frame) lets the video model redraw the whole frame; a clip that
                     redraws the tower is caught here (starting threshold 0.90, to be tuned on real clips).
  occluded_share     share of the character's box hidden by something nearer to the camera (from the depth picture) — a pillar right
                     in front of the camera (seen on the first real render, 2026-09-25) makes the location pack try another camera.
"""
import os
import subprocess
from typing import Dict, List, Optional, Sequence

THRESHOLD = 0.90


def _np():
    import numpy as np
    return np


def _gray(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _edges(gray):
    np = _np()
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def similarity(frame, plate, keep) -> float:
    """0..1 how alike two pictures are where `keep` is 1 (edges correlate + colours close)."""
    np = _np()
    k = keep > 0.5
    if k.sum() < 100:
        return 1.0
    ef, ep = _edges(_gray(frame))[k], _edges(_gray(plate))[k]
    ef, ep = ef - ef.mean(), ep - ep.mean()
    denom = float(np.sqrt((ef * ef).sum() * (ep * ep).sum())) or 1.0
    corr = max(0.0, float((ef * ep).sum()) / denom)
    colour = 1.0 - min(1.0, float(np.abs(frame[k] - plate[k]).mean()) * 4)
    return round(0.65 * corr + 0.35 * colour, 4)


def _load(path: str, size=None):
    np = _np()
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        if size and im.size != size:
            im = im.resize(size)
        return np.asarray(im, dtype=np.float32) / 255.0


def _keep_mask(mask_path: Optional[str], size, grow: int = 25):
    """1 = background to compare (the character and a margin around them are left out: they move)."""
    np = _np()
    if not mask_path or not os.path.exists(mask_path):
        return np.ones((size[1], size[0]), dtype=np.float32)
    from PIL import Image, ImageFilter
    with Image.open(mask_path) as im:
        m = im.convert("L").resize(size).filter(ImageFilter.MaxFilter(grow * 2 + 1))
    return 1.0 - np.asarray(m, dtype=np.float32) / 255.0


def picture_score(picture: str, plate: str, mask: Optional[str] = None) -> float:
    ref = _load(plate)
    size = (ref.shape[1], ref.shape[0])
    return similarity(_load(picture, size), ref, _keep_mask(mask, size))


def background_score(clip: str, plate: str, ffmpeg: str, mask: Optional[str] = None, step: float = 0.5,
                     max_frames: int = 30) -> Dict:
    """{"score": the worst sampled moment, "frames": [(t, score)], "ok": score >= THRESHOLD}."""
    import tempfile
    ref = _load(plate)
    size = (ref.shape[1], ref.shape[0])
    keep = _keep_mask(mask, size)
    work = tempfile.mkdtemp()
    out: List = []
    try:
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", clip, "-vf", f"fps={1 / step:g}", "-frames:v", str(max_frames),
                        os.path.join(work, "f_%03d.png")], capture_output=True, timeout=300)
        for i, name in enumerate(sorted(os.listdir(work))):
            out.append((round(i * step, 2), similarity(_load(os.path.join(work, name), size), ref, keep)))
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    worst = min((s for _, s in out), default=None)
    return {"score": worst, "frames": out, "ok": worst is not None and worst >= THRESHOLD}


def occluded_share(depth_path: Optional[str], depth_range, box: Sequence[float], distance_m: float, size=(1152, 2048)) -> float:
    """Share of the character's box (upper 85 %, the feet row touches the floor) covered by something nearer than them."""
    if not depth_path or not depth_range or not os.path.exists(depth_path):
        return 0.0
    from . import plate_env
    w, h = size
    dist = plate_env.distance_map(depth_path, depth_range, size)
    x0, y0 = max(0, int(box[0] * w)), max(0, int(box[1] * h))
    x1 = min(w, int(box[2] * w))
    y1 = min(h, int((box[1] + (min(box[3], 1.0) - box[1]) * 0.85) * h))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    region = dist[y0:y1, x0:x1]
    return round(float((region < distance_m * 0.85).mean()), 3)
