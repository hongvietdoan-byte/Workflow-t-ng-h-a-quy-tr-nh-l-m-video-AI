"""Composite a green-screen character onto a location-pack plate (kế hoạch V4 1.2 + 1.6 step 5) — numpy + Pillow (+ ffmpeg for clips),
no AI, no credit. The background stays the plate's own pixels; everything below is about the character looking like it is THERE:

  1. key         green -> alpha by how much green beats red/blue, soft edge; despill (green fringe on hair and skin removed)
  2. place       the character's head top / feet / centre lined up with where the virtual camera puts them (plate_camera box)
  3. shadow      the plate rendered WITH the stand-in's shadow (shadow.png) is the background, so the real shadow is on the ground
  4. occlusion   plate pixels nearer to the camera than the character (depth picture) stay in front of them (railing, pillar)
  5. colour      the plate's time/weather grade (60 %), then part of the way to the light around them (mean/contrast per channel)
  6. light wrap  a blurred rim of the background bleeds over the character's edge (the edge stops looking cut out)
  7. fog         the same fog as the plate at the character's own distance
Falling rain/snow is added after, over everything (plate_env.overlay_still / overlay_video).

`composite_video` does the same per frame for a character clip made on green (mode 2); the placement is measured once on the first
frame so the character does not jitter.
"""
import os
import subprocess
from typing import Dict, Optional, Sequence, Tuple

from . import ffmpeg_studio, plate_env

MATCH_STRENGTH = 0.35       # how far the character's colour moves toward the light around them
GRADE_STRENGTH = 0.6        # share of the plate's time/weather grade put on the character too (the green picture was asked for the
                            # same light, but AI pictures come out brighter — trial 2026-09-25: a day-lit Kelly glowed on a night plate)
WRAP = 0.28                 # light wrap strength on the edge band


class CompositeError(ValueError):
    """Shown to the person as it is."""


def _np():
    import numpy as np
    return np


def _load(path: str, size: Optional[Tuple[int, int]] = None, mode: str = "RGB"):
    np = _np()
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert(mode)
        if size and im.size != size:
            im = im.resize(size, Image.LANCZOS)
        return np.asarray(im, dtype=np.float32) / 255.0


def _blur(arr, radius: int):
    np = _np()
    from PIL import Image, ImageFilter
    if radius <= 0:
        return arr
    if arr.ndim == 2:
        im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8"), "L").filter(ImageFilter.GaussianBlur(radius))
        return np.asarray(im, dtype=np.float32) / 255.0
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8"), "RGB").filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(im, dtype=np.float32) / 255.0


def key_green(rgb, low: float = 0.06, high: float = 0.22):
    """alpha (1 = character) and the despilled colour. Greenness = green minus the larger of red and blue."""
    np = _np()
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    green = g - np.maximum(r, b)
    alpha = 1.0 - np.clip((green - low) / (high - low), 0, 1)
    alpha = _blur(alpha, 1)                                    # 1-2 px soft edge (hair), no jaggies
    alpha = np.clip((alpha - 0.05) / 0.9, 0, 1)
    out = rgb.copy()
    limit = np.maximum(r, b)
    spill = g > limit
    out[..., 1] = np.where(spill, limit + (g - limit) * 0.15, g)   # despill: green cannot beat red/blue by more than a hair
    return alpha, out


def bbox(alpha, thresh: float = 0.5) -> Optional[Tuple[int, int, int, int]]:
    np = _np()
    ys, xs = np.where(alpha > thresh)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def placement(alpha, target_box: Sequence[float], size: Tuple[int, int]) -> Dict:
    """Scale + offset that line the keyed character up with the camera's box (fractions of the frame, feet at the bottom).
    A waist-up picture (the character is cut by the bottom of the picture) was made in the shot's own framing: same size, head top
    and centre lined up. A full body is scaled to the box height and stood on the box's feet line."""
    w, h = size
    box = bbox(alpha)
    if box is None:
        raise CompositeError("ảnh phông xanh không có nhân vật (tách phông ra rỗng) — kiểm tra nền có đúng xanh #00FF00 không")
    x0, y0, x1, y1 = box
    tx0, ty0, tx1, ty1 = target_box
    base = w / alpha.shape[1]                                   # the green picture resized to the plate's size first
    cut = y1 >= alpha.shape[0] - 2
    if cut or ty1 > 1.0:
        scale = base
        dy = ty0 * h - y0 * scale
    else:
        scale = max(base * 0.6, min(base * 1.6, (ty1 - ty0) * h / max(y1 - y0, 1)))
        dy = ty1 * h - y1 * scale
    dx = (tx0 + tx1) / 2 * w - (x0 + x1) / 2 * scale
    return {"scale": round(scale, 4), "dx": round(dx, 1), "dy": round(dy, 1), "cut": bool(cut), "char_box": box}


def _transform(arr, place: Dict, size: Tuple[int, int], fill=0.0):
    """Scale then shift an array into a frame of `size` (outside = fill)."""
    np = _np()
    from PIL import Image
    w, h = size
    sh, sw = arr.shape[0], arr.shape[1]
    nw, nh = max(1, int(round(sw * place["scale"]))), max(1, int(round(sh * place["scale"])))
    if arr.ndim == 2:
        im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8"), "L").resize((nw, nh), Image.LANCZOS)
        src = np.asarray(im, dtype=np.float32) / 255.0
        out = np.full((h, w), fill, dtype=np.float32)
    else:
        im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8"), "RGB").resize((nw, nh), Image.LANCZOS)
        src = np.asarray(im, dtype=np.float32) / 255.0
        out = np.full((h, w, 3), fill, dtype=np.float32)
    ox, oy = int(round(place["dx"])), int(round(place["dy"]))
    sx0, sy0 = max(0, -ox), max(0, -oy)
    dx0, dy0 = max(0, ox), max(0, oy)
    cw, ch = min(nw - sx0, w - dx0), min(nh - sy0, h - dy0)
    if cw > 0 and ch > 0:
        out[dy0:dy0 + ch, dx0:dx0 + cw] = src[sy0:sy0 + ch, sx0:sx0 + cw]
    return out


def match_colour(char, alpha, background, strength: float = MATCH_STRENGTH):
    """Move the character's per-channel mean and contrast part of the way toward the background around them."""
    np = _np()
    m = alpha > 0.5
    if m.sum() < 50:
        return char
    ring = (_blur(alpha, 25) > 0.02) & ~m
    ref = background[ring] if ring.sum() > 50 else background.reshape(-1, 3)
    cm, cs = char[m].mean(0), char[m].std(0) + 1e-4
    rm, rs = ref.mean(0), ref.std(0) + 1e-4
    target_m = cm + (rm - cm) * strength
    target_s = cs + (rs - cs) * strength * 0.5
    return np.clip((char - cm) / cs * target_s + target_m, 0, 1)


def grain(img, alpha=None):
    """Fine noise of a picture: the spread of what a small blur takes away (on the character only when alpha is given)."""
    np = _np()
    detail = (img - _blur(img, 1)).mean(axis=2)
    sel = detail[alpha > 0.5] if alpha is not None else detail.reshape(-1)
    return float(np.std(sel)) if sel.size > 50 else 0.0


def match_grain(char, alpha, background, seed: int = 1):
    """D8 (editing.md E5): a render / plate has its own fine noise, the green-screen character another (usually cleaner) — the eye reads
    the clean one as "pasted". Noise is added to the character up to the plate's level (never removed)."""
    np = _np()
    missing = grain(background) ** 2 - grain(char, alpha) ** 2
    if missing <= 1e-7:
        return char
    rnd = np.random.RandomState(seed)
    noise = rnd.normal(0, missing ** 0.5, alpha.shape).astype(np.float32)[..., None]
    return np.clip(char + noise * (alpha[..., None] > 0), 0, 1)


def light_wrap(char, alpha, background, strength: float = WRAP):
    np = _np()
    edge = np.clip(_blur(1 - alpha, 6) * alpha * 2.2, 0, 1)[..., None]
    return char * (1 - edge * strength) + _blur(background, 8) * edge * strength


def occluders(depth_path: Optional[str], depth_range, size: Tuple[int, int], distance_m: float):
    """1 where the plate has something nearer than the character (it must stay in front of them)."""
    np = _np()
    if not depth_path or not depth_range or not os.path.exists(depth_path):
        return None
    dist = plate_env.distance_map(depth_path, depth_range, size)
    return _blur((dist < distance_m * 0.85).astype(np.float32), 1)   # the floor just before the feet is not a wall


def composite(green_path: str, plate: Dict, out_path: str, env: Optional[Dict] = None, mask_out: Optional[str] = None,
              place: Optional[Dict] = None, seed: int = 1) -> Dict:
    """plate = an entry of location_pack.index (plate, shadow, depth, depth_range_m, subject_box, distance_m). Writes the composite
    (and the character mask) and returns {"path", "mask", "placement", "occluded_share"}."""
    np = _np()
    from PIL import Image
    env = env or plate.get("env") or {"time": "day", "weather": "clear"}
    back_path = plate.get("shadow") if plate.get("shadow") and os.path.exists(plate["shadow"]) else plate["plate"]
    with Image.open(back_path) as im:
        size = im.size
    background = _load(back_path)
    green = _load(green_path)
    alpha, char = key_green(green)
    place = place or placement(alpha, plate["subject_box"], size)
    alpha = _transform(alpha, place, size)
    char = _transform(char, place, size)
    occ = occluders(plate.get("depth"), plate.get("depth_range_m"), size, float(plate.get("distance_m") or 3.0))
    occluded = 0.0
    if occ is not None:
        before = float(alpha.sum()) or 1.0
        alpha = alpha * (1 - occ)
        occluded = 1 - float(alpha.sum()) / before
    char = char * (1 - GRADE_STRENGTH) + plate_env.grade(char, env) * GRADE_STRENGTH
    char = match_colour(char, alpha, background)
    char = light_wrap(char, alpha, background)
    char = match_grain(char, alpha, background, seed)       # a new grain every frame of a clip (a fixed one reads as dirt)
    if plate_env.fog_amount(env) > 0:
        char = plate_env.apply_fog(char, np.full(alpha.shape, float(plate.get("distance_m") or 3.0)), env)
    a = alpha[..., None]
    out = background * (1 - a) + char * a
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype("uint8")).save(out_path)
    if mask_out:
        Image.fromarray((np.clip(alpha, 0, 1) * 255).astype("uint8"), "L").save(mask_out)
    return {"path": out_path, "mask": mask_out, "placement": place, "occluded_share": round(occluded, 3)}


def composite_video(green_clip: str, plate: Dict, out_path: str, ffmpeg: str, env: Optional[Dict] = None, fps: int = 24) -> Dict:
    """Mode 2: a character clip made on green, keyed frame by frame over the plate (placement from the first frame). Audio kept."""
    np = _np()
    import re
    import tempfile
    from PIL import Image
    probe = subprocess.run([ffmpeg, "-i", green_clip], capture_output=True, text=True, errors="replace")
    m = re.search(r", (\d{2,5})x(\d{2,5})", probe.stderr or "")
    if not m:
        raise CompositeError("không đọc được kích thước clip phông xanh")
    gw, gh = int(m.group(1)), int(m.group(2))
    with Image.open(plate.get("shadow") or plate["plate"]) as im:
        size = im.size
    reader = subprocess.Popen([ffmpeg, "-loglevel", "error", "-i", green_clip, "-r", str(fps), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                              stdout=subprocess.PIPE)
    writer = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
                               "-r", str(fps), "-i", "-", "-i", green_clip, "-map", "0:v", "-map", "1:a?", "-vf", ffmpeg_studio.TO_YUV709,
                               "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", *ffmpeg_studio.COLOR_TAGS, "-c:a", "copy",
                               "-shortest", out_path], stdin=subprocess.PIPE)   # RGB frames: converted with the BT.709 matrix they are tagged with
    work = tempfile.mkdtemp()
    place, n = None, 0
    try:
        while True:
            raw = reader.stdout.read(gw * gh * 3)
            if len(raw) < gw * gh * 3:
                break
            frame = os.path.join(work, "g.png")
            Image.fromarray(np.frombuffer(raw, dtype=np.uint8).reshape(gh, gw, 3)).save(frame)
            res = composite(frame, plate, os.path.join(work, "c.png"), env, place=place, seed=n + 1)
            place = res["placement"]
            writer.stdin.write(np.asarray(Image.open(res["path"]).convert("RGB"), dtype=np.uint8).tobytes())
            n += 1
    finally:
        writer.stdin.close()
        writer.wait()
        reader.wait()
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    if n == 0:
        raise CompositeError("clip phông xanh không có khung hình nào")
    return {"path": out_path, "frames": n, "placement": place}
