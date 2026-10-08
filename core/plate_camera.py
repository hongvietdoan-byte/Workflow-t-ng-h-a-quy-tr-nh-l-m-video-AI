"""Virtual camera of a shot on a 3D place (kế hoạch V4 1.6 step 1) — no AI, pure geometry.

From the DP's shot fields (size, angle, start_frame words, camera_setup) + where the character stands (a named spot of the place) +
the character's real height (standard profile height_m), it gives:
  - the Blender camera (location, look_at, lens — in the scene's metres, after scaling) for tools/render_plates.py
  - where the character will be in the frame (a box, fractions of the frame) — so the green-screen character is scaled and placed
    exactly where the plate expects them, and the composite, the shadow pass and the subtitle placement all agree.

Numbers (knowledge/roles/dp.md Q2, cinematography_basics.md): how much of the body a size shows and how much of the frame it fills;
the lens per size (wide = wider lens, close = longer lens, which also compresses the background like a real close-up).
Frame: vertical 9:16 by default; Blender's sensor (36 mm) spans the longer side ("AUTO" fit).
"""
import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

SENSOR_MM = 36.0
# size -> (share of the body from the top of the head that is in frame, share of the frame height it fills, lens mm)
FRAMING = {"EWS": (1.0, 0.18, 20), "WS": (1.0, 0.55, 24), "GAME_TPS": (1.0, 0.42, 24), "MLS": (0.75, 0.80, 32),
           "MS": (0.55, 0.82, 35), "MCU": (0.35, 0.85, 50), "CU": (0.22, 0.88, 65), "ECU": (0.12, 0.95, 85)}
DEFAULT_SIZE = "MS"
# top of the head below the frame's top edge (share of the frame). GĐ4 (dp.md Q3): in a vertical frame the app's top bar covers ~15 % —
# MS used to put the eyes at ~14 % (inside that bar); measured now (grader GĐ4, camera_for + project): eyes ~20 % (MLS), ~23 % (MS),
# ~28 % (MCU), ~33 % (CU) — the EYES leave the bar; the top of the head may still touch it
HEADROOM = {"EWS": 0.40, "WS": 0.14, "GAME_TPS": 0.30, "MLS": 0.14, "MS": 0.13, "MCU": 0.11, "CU": 0.05, "ECU": 0.02}
HIGH_TILT_DEG, OVERHEAD_TILT_DEG = 30.0, 60.0             # how far a high / overhead camera looks down at the frame's middle
SIDE_X = {"left": 0.36, "center": 0.5, "right": 0.64}      # where the character stands across the frame (rule of thirds, softened)
# F2 (người dùng duyệt 09/10, #24 shot 4): a "low" MCU put the camera 0,45 m above the ground and 0,97 m from the character, tilted 45°
# up — the render was sky only (horizon_y 1,9), flagged flat, dropped, and the picture went out with no background → the model guessed
# the well's height. Checks on every shot camera (no AI, 0 USD):
#  - an upward tilt keeps the horizon inside the frame (≤ HORIZON_KEEP of the half frame below the middle) unless the shot asks for the
#    sky; a camera lower than LOW_CAM_M never tilts up more than MAX_LOW_TILT_DEG — the camera is RAISED (same distance, same aim, so
#    the framing stays), never moved into the character;
#  - a camera closer than MIN_DIST_M[size] (a DP lens too short for the size) goes back along its axis with a longer lens (same
#    framing). The floors sit just under the sizes' own distances (MS 35 mm ≈ 1,11 m, MLS 32 mm ≈ 1,42 m, WS 24 mm ≈ 2,1 m), so
#    default cameras — and their cached renders in every project — do not change; only an extreme lens does.
HORIZON_KEEP = 0.8
LOW_CAM_M, MAX_LOW_TILT_DEG = 0.8, 30.0
MIN_DIST_M = {"EWS": 1.5, "WS": 1.5, "GAME_TPS": 1.5, "MLS": 1.2, "MS": 1.0}
MAX_LENS_MM = 200.0
SKY_WORDS = ("sky", "bầu trời", "nhìn lên trời", "ngước lên trời", "ngước nhìn trời")
# F2: the shot's same-axis WIDE view (sent with the shot's render): same yaw/pitch, camera pulled back along its axis, wider lens
WIDE_LENS_SHARE, WIDE_MIN_LENS = 0.6, 18.0
WIDE_SPAN_BODY, WIDE_SPAN_FRAME = 3.0, 2.5     # the wide frame spans ≥ 3 body heights and ≥ 2,5× the shot's frame at the character
WIDE_MIN_CAM_M = 0.3                           # a wide pulled back along an upward axis never sinks below this above the feet


def size_of(data: Dict) -> str:
    size = str(data.get("size") or data.get("shot_size") or "").upper()
    return size if size in FRAMING else DEFAULT_SIZE


def lens_of(data: Dict, default: float) -> float:
    """The DP's lens (shot field `lens_mm`, dp.md Q2: e.g. 24 mm close enlarges the foreground and stretches space, 135 mm compresses the background and separates the subject — what that
    means is the scene's intent, the DP records it in `why`) — the framing
    (how much of the body fills the frame) stays the size's, so a longer lens moves the camera back and flattens the background."""
    lens = data.get("lens_mm")
    if isinstance(lens, (int, float)) and not isinstance(lens, bool) and 14 <= lens <= 200:
        return float(lens)
    return default


def side_of(data: Dict) -> str:
    words = f"{data.get('start_frame') or ''} {data.get('blocking') or ''}".lower()
    for side, keys in (("left", ("frame-left", "frame left", "left of frame", "bên trái", "trái khung")),
                       ("right", ("frame-right", "frame right", "right of frame", "bên phải", "phải khung"))):
        if any(k in words for k in keys):
            return side
    return "center"


def vfov(lens_mm: float, aspect: float) -> float:
    """Vertical field of view (radians). aspect = width / height of the frame; the sensor spans the longer side."""
    if aspect < 1:                                          # vertical frame: the sensor spans the height
        return 2 * math.atan(SENSOR_MM / 2 / lens_mm)
    return 2 * math.atan(SENSOR_MM / 2 / lens_mm / aspect)


def wants_sky(data: Dict) -> bool:
    """The shot asks to look at the sky (then an upward tilt with the horizon out of frame is the intent, not an error)."""
    words = " ".join(str(data.get(k) or "") for k in ("start_frame", "camera_setup", "blocking", "image_prompt")).lower()
    # phiên sửa F2: whole words ("skyline", "skyscraper" are not the sky) and never negated ("no sky", "không thấy trời")
    for m in _SKY_RX.finditer(words):
        if not _SKY_NEG.search(words[max(0, m.start() - 24):m.start()]):
            return True
    return False


_SKY_RX = re.compile(r"\bsky\b|" + "|".join(re.escape(w) for w in SKY_WORDS[1:]))
_SKY_NEG = re.compile(r"(?:\b(?:no|not|without|never|nor)\s+(?:\w+\s+){0,2}|không\s+(?:thấy|có|nhìn thấy|lộ)?\s*(?:\w+\s+){0,1})$")


def _unit(v: Sequence[float]) -> Tuple[float, float, float]:
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def camera_for(data: Dict, spot: Sequence[float], facing_deg: float, height_m: float = 1.75, aspect: float = 9 / 16,
               name: str = "shot") -> Dict:
    """Camera for one shot. spot = where the character's feet are (scene metres); facing_deg = the direction the character faces,
    degrees clockwise from +y (0 = +y, 90 = +x). The camera stands in front of the character (they face it, as the start frames of
    FF shots do) unless the shot says over-the-shoulder / from behind.
    Returns {"camera": {name, location, look_at, lens, angle}, "subject_box": [x0, y0, x1, y1], "feet_y", "distance_m"}."""
    size = size_of(data)
    body_share, fill, lens = FRAMING[size]
    lens = lens_of(data, lens)
    angle = str(data.get("angle") or "eye").lower()
    from .plate_choice import is_behind
    behind = is_behind(data)                                  # one test, shared with the script's camera direction (S5.7)
    fov = vfov(lens, aspect)
    visible = height_m * body_share                          # metres of the body inside the frame (top of the head down)
    frame_h = visible / fill                                  # metres the frame spans at the character's distance
    dist = frame_h / (2 * math.tan(fov / 2))
    fixes: List[str] = []
    problem: Optional[str] = None
    floor = MIN_DIST_M.get(size)
    if floor and dist < floor - 1e-6:                         # F2: too close for the size — back along the axis, longer lens
        want = lens * floor / dist
        if want > MAX_LENS_MM:
            problem = (f"máy quá sát nhân vật ({dist:.2f} m với cỡ {size}) và không lùi được (cần ống {want:.0f} mm > {MAX_LENS_MM:g} mm)"
                       " — chọn lại cỡ cảnh / ống kính")
        else:
            fixes.append(f"máy cách nhân vật {dist:.2f} m (quá sát cho cỡ {size}) → lùi dọc trục còn {floor:g} m, ống {lens:g}→{want:.0f} mm "
                         "(giữ khung)")
            lens = round(want, 1)
            fov = vfov(lens, aspect)
            dist = frame_h / (2 * math.tan(fov / 2))
    head = height_m
    top_of_frame = head + frame_h * HEADROOM[size]
    centre_z = top_of_frame - frame_h / 2                     # height of the frame's middle at the character's distance
    eye = height_m * 0.93
    # high / overhead: a set tilt down onto the frame's middle (dp.md: high ≈ 30°, overhead ≈ 60°). Trial #8 (2026-09-27): a fixed
    # "head + 1.6 m" put a 2 m-away WS camera 56–62° down — the plate was the floor seen from above and the characters looked pasted on it
    cam_z = {"low": 0.45, "high": centre_z + dist * math.tan(math.radians(HIGH_TILT_DEG)),
             "overhead": centre_z + dist * math.tan(math.radians(OVERHEAD_TILT_DEG))}.get(angle, min(eye, centre_z + 0.2))
    if size in ("EWS", "GAME_TPS") and angle not in ("low",):
        cam_z = max(cam_z, head + 2.5)                        # game third-person / establishing: above the head
    if cam_z < centre_z and not wants_sky(data):              # F2: an upward tilt — keep the horizon in the frame
        cap = HORIZON_KEEP * math.tan(fov / 2)
        if cam_z < LOW_CAM_M:
            cap = min(cap, math.tan(math.radians(MAX_LOW_TILT_DEG)))
        tilt = (centre_z - cam_z) / dist
        if tilt > cap + 1e-9:
            new_z = centre_z - dist * cap
            fixes.append(f"máy cao {cam_z:.2f} m ngửa {math.degrees(math.atan(tilt)):.0f}° (chân trời ở "
                         f"{(0.5 + 0.5 * tilt / math.tan(fov / 2)) * 100:.0f}% — ngoài khung, chỉ thấy trời) → nâng máy lên {new_z:.2f} m, "
                         f"ngửa {math.degrees(math.atan(cap)):.0f}° (cùng khoảng cách, cùng điểm nhìn)")
            cam_z = new_z
    yaw = math.radians(facing_deg + (180 if behind else 0))
    fwd = (math.sin(yaw), math.cos(yaw), 0.0)                 # where the character looks
    right = (fwd[1], -fwd[0], 0.0)
    side = side_of(data)
    shift = (SIDE_X[side] - 0.5) * frame_h * aspect           # metres the character sits off the frame's middle
    cam = (spot[0] + fwd[0] * dist + right[0] * shift, spot[1] + fwd[1] * dist + right[1] * shift, spot[2] + cam_z)
    aim = (spot[0] + right[0] * shift, spot[1] + right[1] * shift, spot[2] + centre_z)
    box = subject_box(cam, aim, lens, aspect, spot, height_m)
    return {"camera": {"name": name, "location": [round(c, 3) for c in cam], "look_at": [round(c, 3) for c in aim], "lens": lens,
                       "angle": {"low": "low_angle", "high": "high_angle", "overhead": "high_angle"}.get(angle, "eye_level")},
            "subject_box": box, "feet_y": box[3], "distance_m": round(dist, 2), "size": size, "side": side, "behind": behind,
            "frame_h_m": round(frame_h, 3), "horizon_y": horizon_y(cam, aim, lens, aspect), "fixes": fixes, "problem": problem}


def horizon_y(cam: Sequence[float], aim: Sequence[float], lens: float, aspect: float) -> float:
    """Where the horizon line falls in the frame (fraction from the top; < 0 above the frame, > 1 below it = only sky), as
    tools/render_plates.py camera_info measures it."""
    d = [a - c for a, c in zip(aim, cam)]
    flat = math.hypot(d[0], d[1]) or 1e-9
    return round(0.5 + 0.5 * (d[2] / flat) / math.tan(vfov(lens, aspect) / 2), 3)


def wide_for(camera: Dict, height_m: float, aspect: float = 9 / 16, frame_h: Optional[float] = None) -> Dict:
    """F2: the same-axis WIDE view of a shot camera — the same direction (yaw and pitch: the aim vector is kept), the camera pulled
    back along that axis and a wider lens (× WIDE_LENS_SHARE, ≥ WIDE_MIN_LENS), so the place around the character's spot and the
    landmarks near it are seen exactly from the shot's side. A pull-back along an upward axis that would sink the camera under
    WIDE_MIN_CAM_M above the feet is lifted (direction kept). Returns a camera dict (location, look_at, lens, wide=True)."""
    cam, aim = list(camera["location"]), list(camera["look_at"])
    lens = float(camera.get("lens") or 35)
    f = _unit([a - c for a, c in zip(aim, cam)])
    to_aim = math.sqrt(sum((a - c) ** 2 for a, c in zip(aim, cam)))
    if frame_h is None:
        frame_h = 2 * to_aim * math.tan(vfov(lens, aspect) / 2)
    wlens = round(max(WIDE_MIN_LENS, min(lens, lens * WIDE_LENS_SHARE)), 1)
    span = max(WIDE_SPAN_BODY * height_m, WIDE_SPAN_FRAME * frame_h)
    back = max(span / (2 * math.tan(vfov(wlens, aspect) / 2)), to_aim * 1.5)
    loc = [a - fc * back for a, fc in zip(aim, f)]
    feet_z = ((camera.get("subject") or {}).get("location") or [None, None, None])[2]
    if feet_z is not None and loc[2] < float(feet_z) + WIDE_MIN_CAM_M:
        lift = float(feet_z) + WIDE_MIN_CAM_M - loc[2]
        loc[2] += lift
        aim = [aim[0], aim[1], aim[2] + lift]
    out = {k: v for k, v in camera.items() if k not in ("location", "look_at", "lens", "name")}
    return dict(out, location=[round(c, 3) for c in loc], look_at=[round(c, 3) for c in aim], lens=wlens, wide=True)


def project(cam: Sequence[float], aim: Sequence[float], lens: float, aspect: float, point: Sequence[float]) -> Optional[Tuple[float, float]]:
    """Where a scene point lands in the frame ((x, y) fractions, y down), pinhole camera looking from cam to aim with no roll."""
    f = _unit([a - c for a, c in zip(aim, cam)])
    r = _unit((f[1], -f[0], 0.0)) if abs(f[2]) < 0.999 else (1.0, 0.0, 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    d = [p - c for p, c in zip(point, cam)]
    z = sum(a * b for a, b in zip(d, f))
    if z <= 0.01:
        return None
    fov = vfov(lens, aspect)
    half_h = math.tan(fov / 2)
    half_w = half_h * aspect
    x = sum(a * b for a, b in zip(d, r)) / z
    y = sum(a * b for a, b in zip(d, u)) / z
    return 0.5 + 0.5 * x / half_w, 0.5 - 0.5 * y / half_h


def subject_box(cam, aim, lens, aspect, spot, height_m, width_m: Optional[float] = None) -> List[float]:
    """Frame box of a character standing at `spot` (feet) — a person about 0.28 of their height wide (shoulders + arms)."""
    width_m = width_m or height_m * 0.28
    f = _unit([a - c for a, c in zip(aim, cam)])
    r = _unit((f[1], -f[0], 0.0))
    pts = []
    for dz in (0.0, height_m):
        for s in (-0.5, 0.5):
            p = project(cam, aim, lens, aspect, (spot[0] + r[0] * s * width_m, spot[1] + r[1] * s * width_m, spot[2] + dz))
            if p:
                pts.append(p)
    if not pts:
        return [0.4, 0.4, 0.6, 0.9]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]


def plan_cameras(shots: List[Dict], spot_of, height_of, aspect: float = 9 / 16) -> Dict[int, Dict]:
    """scene id -> camera_for(...) for shots at a 3D place. Shots of one camera_setup with the same size share the first one's camera
    (the DP's coverage: one position, several shots). spot_of(shot) -> (xyz, facing_deg) or None; height_of(shot) -> metres."""
    out, setups = {}, {}
    for s in shots:
        data = s["data"]
        spot = spot_of(s)
        if spot is None:
            continue
        key = (data.get("story_scene"), data.get("camera_setup"), size_of(data)) if data.get("camera_setup") else None
        if key and key in setups:
            out[s["id"]] = dict(setups[key], shared_with=setups[key]["camera"]["name"])
            continue
        cam = camera_for(data, spot[0], spot[1], height_of(s), aspect, name=f"shot_{s['id']}")
        out[s["id"]] = cam
        if key:
            setups[key] = cam
    return out
