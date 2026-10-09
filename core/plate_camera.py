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
# P24 (người dùng duyệt ảnh #24, 09/10): the model copies the render's composition closely, so the 3D camera must speak the shot's
# camera language, not a generic one.
#  - shot 3 (ots MS, Kelly CÚI nhìn xuống giếng) had the camera −10° at 1,1 m looking level at the foot of the clock tower → the
#    picture showed the whole clock face while the script looks DOWN into the well. A high / ots shot whose action looks down tilts
#    LOOK_DOWN_PITCH_DEG (dp.md: a clear high ≈ 30–45°) — the background is the ground around the spot; anything tall leaves the top
#    of the frame (only its foot may stay). Over the shoulder the camera sits OTS_ABOVE_HEAD_M above the head and aims at the ground
#    beyond the character (where they look), never at their back.
#  - shot 5 (low WS): a camera 0,45 m above the ground behind a chest-high plaza wall saw only the wall ("tường cao"). A low camera
#    sits at LOW_CAM_SHARE of the character's height and tilts LOW_TILT_DEG up; a wall still in its way is found by rays in Blender
#    (tools/render_plates.py) and judged by clearance_fix below (pure: raise over a low wall, step in front of a wall the camera is
#    inside, say a tall wall right behind the character — never silent).
LOOK_DOWN_PITCH_DEG = 35.0
OTS_ABOVE_HEAD_M = 0.15
LOOK_DOWN_ANGLES = ("high", "ots")
LOW_CAM_SHARE, LOW_TILT_DEG = 0.5, 8.0
DOWN_WORDS = ("look down", "looks down", "looking down", "peer down", "peers down", "peering down", "peer into", "peers into",
              "peering into", "gaze down", "gazes down", "gazing down", "glance down", "glances down", "glancing down", "stare down",
              "stares down", "staring down", "leaning over", "leans over", "lean over", "bends over", "bending over",
              "nhìn xuống", "cúi nhìn", "cúi xuống", "cúi người", "ngó xuống", "nhòm xuống", "nhìn chằm chằm xuống")
# clearance (Blender rays, scene metres): the camera steps CLEAR_GAP_M in front of a face on its sight line; a wall closer than
# BG_NEAR_M behind the character that the camera is below is a "wall frame": raised over it (top + OVER_WALL_M) when the wall is no
# higher than the character + LOW_WALL_EXTRA_M, else reported (a house wall — choose another plate_view)
CLEAR_GAP_M, BG_NEAR_M, OVER_WALL_M, LOW_WALL_EXTRA_M = 0.3, 2.5, 0.15, 0.3
# rà P24: a face closer than CLEAR_GAP_M + MIN_CLEAR_M to the character leaves no room for a camera — reported, never moved there
MIN_CLEAR_M = 0.5                              # an over-the-shoulder camera still fits 0,5 m behind the head; closer = in the face
# rà P24: "looks down the alley / street…" is a direction along the ground, not a look DOWN (the camera must not tilt 35°)
AWAY_WORDS = ("alley", "alleyway", "street", "road", "corridor", "hall", "hallway", "path", "lane", "track", "tunnel", "avenue",
              "block", "runway", "row", "aisle", "line", "barrel", "sights", "scope", "length")


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
_DOWN_RX = re.compile("|".join(r"\b" + re.escape(w) + r"\b" for w in DOWN_WORDS))
_DOWN_NEG = re.compile(r"(?:\b(?:no|not|without|never|nor|doesn't|don't|isn't)\s+(?:\w+\s+){0,1}|(?:không|chưa|chẳng)\s+(?:\w+\s+){0,1})$")


_DOWN_AWAY = re.compile(r"\s+(?:the|a|an|this|that)\s+(?:\w+\s+)?(?:" + "|".join(AWAY_WORDS) + r")\b")


def looks_down(data: Dict) -> bool:
    """P24: the shot's action / blocking / start frame says the character looks DOWN (into the well, at the ground) — whole words,
    never negated ("không nhìn xuống", "does not look down"), never "looks down the (dark) alley / street" (a direction along the
    ground). camera_setup is not read (rà P24): "camera looks down at her" is the camera, not the character."""
    words = " ".join(str(data.get(k) or "") for k in ("action", "blocking", "start_frame")).lower()
    for m in _DOWN_RX.finditer(words):
        if _DOWN_AWAY.match(words, m.end()):
            continue
        if not _DOWN_NEG.search(words[max(0, m.start() - 24):m.start()]):
            return True
    return False


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
    why = {"distance": (f"cỡ {size}{'' if data.get('size') or data.get('shot_size') else ' (shot thiếu size — mặc định MS)'}: "
                        f"{body_share * 100:.0f}% thân trong khung, chiếm {fill * 100:.0f}% chiều cao khung, ống {lens:g} mm → "
                        f"khung rộng {frame_h:.2f} m ở chỗ nhân vật, máy cách {dist:.2f} m")}
    aim_z = centre_z                                          # height the camera aims at above the feet (the frame's middle)
    down = looks_down(data)
    down_ok = down and angle in LOOK_DOWN_ANGLES
    low_z = height_m * LOW_CAM_SHARE
    cam_z = {"low": low_z, "high": centre_z + dist * math.tan(math.radians(HIGH_TILT_DEG)),
             "overhead": centre_z + dist * math.tan(math.radians(OVERHEAD_TILT_DEG))}.get(angle, min(eye, centre_z + 0.2))
    if angle == "low" and low_z >= centre_z - dist * math.tan(math.radians(LOW_TILT_DEG)):
        # P24: a wide low shot's frame middle is below the camera — aim up a little so it still reads as a low angle
        aim_z = low_z + dist * math.tan(math.radians(LOW_TILT_DEG))
    if size in ("EWS", "GAME_TPS") and angle not in ("low",):
        cam_z = max(cam_z, head + 2.5)                        # game third-person / establishing: above the head
    if down_ok and not behind:                                # P24: high + looks down — a clear tilt onto the ground round the spot
        cam_z = max(cam_z, centre_z + dist * math.tan(math.radians(LOOK_DOWN_PITCH_DEG)))
    if cam_z < aim_z and not wants_sky(data):                 # F2: an upward tilt — keep the horizon in the frame
        cap = HORIZON_KEEP * math.tan(fov / 2)
        if cam_z < LOW_CAM_M:
            cap = min(cap, math.tan(math.radians(MAX_LOW_TILT_DEG)))
        tilt = (aim_z - cam_z) / dist
        if tilt > cap + 1e-9:
            new_z = aim_z - dist * cap
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
    aim = (spot[0] + right[0] * shift, spot[1] + right[1] * shift, spot[2] + aim_z)
    if down_ok and behind:
        # P24 shot 3: over the shoulder, looking where the character looks — down. The camera a little above the head, aimed at the
        # ground beyond the character so the tilt is LOOK_DOWN_PITCH_DEG (≤ 45° by construction; the aim never falls behind the
        # character — a far camera (WS/EWS) then tilts less, said in `why`)
        cam_z = height_m + OTS_ABOVE_HEAD_M
        reach = max(cam_z / math.tan(math.radians(LOOK_DOWN_PITCH_DEG)), dist + 0.5)
        cam = (cam[0], cam[1], spot[2] + cam_z)
        aim = (cam[0] - fwd[0] * reach, cam[1] - fwd[1] * reach, spot[2])
    box = subject_box(cam, aim, lens, aspect, spot, height_m)
    hz = horizon_y(cam, aim, lens, aspect)
    d = [a - c for a, c in zip(aim, cam)]
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    if down_ok:
        why["pitch"] = (f"angle '{angle}' + hành động nhìn xuống → cúi {pitch:.0f}° (đích {LOOK_DOWN_PITCH_DEG:g}°, khoảng 30–45°): "
                        "nền là mặt đất quanh chỗ đứng, vật cao (tháp) ra khỏi mép trên khung" + (" — qua vai, máy trên đầu "
                        f"{OTS_ABOVE_HEAD_M:g} m nhìn xuống chỗ nhân vật nhìn" if behind else ""))
    elif down:
        why["pitch"] = (f"hành động nhìn xuống nhưng angle '{angle}'" + ("" if data.get("angle") else " (shot thiếu angle — mặc định eye)")
                        + f" không thuộc {'/'.join(LOOK_DOWN_ANGLES)} → giữ máy theo angle, nghiêng {pitch:.0f}°")
    elif angle == "low":
        why["pitch"] = (f"angle 'low' → máy đặt từ {low_z:.2f} m ({LOW_CAM_SHARE:g}× chiều cao, không sát đất)"
                        + (f", nâng còn {cam_z:.2f} m để giữ chân trời trong khung" if abs(cam_z - low_z) > 1e-3 else "")
                        + f", ngửa {pitch:.0f}°; "
                        "tường chắn trên đường nhìn: Blender bắn tia kiểm (clearance)")
    else:
        why["pitch"] = (f"angle '{angle}'" + ("" if data.get("angle") else " (shot thiếu angle — mặc định eye)")
                        + f" → máy {cam_z:.2f} m, nghiêng {pitch:.0f}°")
    why["direction"] = (f"nhân vật nhìn {facing_deg % 360:g}°, máy " + ("sau lưng (qua vai)" if behind else "trước mặt")
                        + " — hướng theo plate_view của shot (luật trục 180° ở plate_choice)")
    return {"camera": {"name": name, "location": [round(c, 3) for c in cam], "look_at": [round(c, 3) for c in aim], "lens": lens,
                       "angle": {"low": "low_angle", "high": "high_angle", "overhead": "high_angle"}.get(angle, "eye_level")},
            "subject_box": box, "feet_y": box[3], "distance_m": round(dist, 2), "size": size, "side": side, "behind": behind,
            "frame_h_m": round(frame_h, 3), "horizon_y": hz, "pitch_deg": round(pitch, 1), "fixes": fixes, "problem": problem,
            "why": why}


def clearance_fix(location: Sequence[float], look_at: Sequence[float], feet: Sequence[float], height_m: float,
                  block_m: Optional[float] = None, bg_m: Optional[float] = None, bg_top_z: Optional[float] = None,
                  block_from: Optional[Sequence[float]] = None, move: bool = True) -> Dict:
    """P24: judge what Blender's rays found round a shot camera (pure; tools/render_plates.py measures, scene metres).
    block_m  = distance from block_from (the character's body, default the aim point) towards the camera to the first face (None =
               clear): the camera is inside / behind a wall → it moves along its own sight line until it is CLEAR_GAP_M in front of
               that face (same aim; the framing gets tighter — said). Measured from the character, not from the aim: a look-down
               shot aims at the ground beyond them (inside a well), and the well's rim is not a wall round the camera.
    bg_m     = horizontal distance from the camera, along its view, to the first face at the camera's height; bg_top_z = the top of
               that obstacle. A face closer than BG_NEAR_M behind the character while the camera looks level/up is a wall filling
               the frame: a low wall (≤ character + LOW_WALL_EXTRA_M) → the camera rises over it (top + OVER_WALL_M, same aim); a
               tall one → reported only (choose another plate_view / spot), never moved silently.
    rà P24: a face closer than CLEAR_GAP_M + MIN_CLEAR_M to the character leaves no room — reported, the camera is not moved (it
    would stand in the character's face). move=False (the same-axis WIDE view): nothing is moved, everything is reported (a wide
    pulled in to a wall is no longer a wide).
    Returns {"location", "look_at", "notes" (what was changed), "warnings" (what is wrong and left)}."""
    loc, aim = [float(c) for c in location], [float(c) for c in look_at]
    notes: List[str] = []
    warnings: List[str] = []
    sight = math.dist(aim, loc)
    seg = math.dist(block_from, loc) if block_from is not None else sight
    blocked = block_m is not None and 0 <= block_m < seg - 1e-6
    if blocked and (not move or block_m - CLEAR_GAP_M < MIN_CLEAR_M):
        warnings.append(f"vật cản trên đường nhìn cách nhân vật {block_m:.2f} m (máy ở {seg:.2f} m) — "
                        + ("không dời máy ảnh toàn cùng trục, ảnh toàn có thể chỉ thấy vật cản" if not move else
                           f"quá sát nhân vật (< {CLEAR_GAP_M + MIN_CLEAR_M:g} m), không còn chỗ đặt máy")
                        + "; chọn plate_view / chỗ đứng khác")
    elif blocked:
        pull = min(seg - max(block_m - CLEAR_GAP_M, 0.0), sight - 0.3)
        f = _unit([a - c for a, c in zip(aim, loc)])
        loc = [c + fc * pull for c, fc in zip(loc, f)]
        notes.append(f"máy nằm trong/sau vật cản (mặt vật cản cách nhân vật {block_m:.2f} m, máy ở {seg:.2f} m) → đưa máy tiến "
                     f"{pull:.2f} m dọc hướng nhìn ra trước mặt đó (cùng hướng nhìn, khung chặt hơn)")
    d = [a - c for a, c in zip(aim, loc)]
    flat = math.hypot(d[0], d[1])
    pitch = math.degrees(math.atan2(d[2], flat or 1e-9))
    to_subject = math.hypot(feet[0] - loc[0], feet[1] - loc[1])
    if bg_m is not None and bg_top_z is not None and pitch > -20.0 and bg_m < to_subject + BG_NEAR_M:
        behind_m = bg_m - to_subject
        top = float(bg_top_z) - float(feet[2])
        where = (f"cách sau nhân vật {behind_m:.2f} m" if behind_m >= 0 else f"trước nhân vật {-behind_m:.2f} m")
        if loc[2] >= float(bg_top_z) + OVER_WALL_M - 1e-6:
            pass                                               # the camera already sees over it
        elif top <= height_m + LOW_WALL_EXTRA_M and not move:
            warnings.append(f"nền ảnh toàn cùng trục là tường thấp {top:.2f} m {where} (máy cao {loc[2] - float(feet[2]):.2f} m) — "
                            "không dời máy ảnh toàn")
        elif top <= height_m + LOW_WALL_EXTRA_M:
            new_z = float(bg_top_z) + OVER_WALL_M
            notes.append(f"máy cao {loc[2] - float(feet[2]):.2f} m sau tường thấp {top:.2f} m {where} — nền chỉ là tường → nâng máy lên "
                         f"{new_z - float(feet[2]):.2f} m (nhìn qua tường, cùng điểm nhìn; góc thấp giảm)")
            loc[2] = new_z
        else:
            warnings.append(f"nền là vật cao {top:.1f} m {where} (máy cao {loc[2] - float(feet[2]):.2f} m) — ảnh sẽ chỉ thấy tường; "
                            "chọn plate_view / chỗ đứng khác")
    return {"location": [round(c, 3) for c in loc], "look_at": [round(c, 3) for c in aim], "notes": notes, "warnings": warnings}


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


STAGE_FIELD = "stage_camera"


def from_stage(sc: Dict, spot: Sequence[float], height_m: float, aspect: float = 9 / 16, name: str = "shot") -> Dict:
    """Sân khấu 3D v2 (cờ stage_camera): máy đã GIẢI + đo bằng tia (core/stage_solver, tools/stage_grid.py v2) và người dùng duyệt →
    dùng NGUYÊN (`locked`: render_plates không dời máy khi sát tường). sc = {"location", "look_at" (tọa độ model), "lens", "source",
    "pov"?, "move"?}. Cùng dạng trả về với camera_for."""
    cam = [float(v) for v in sc["location"]]
    aim = [float(v) for v in sc["look_at"]]
    lens = float(sc["lens"])
    d = [a - c for a, c in zip(aim, cam)]
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    angle = "high_angle" if pitch <= -15 else ("low_angle" if cam[2] - spot[2] < 0.6 * height_m or pitch >= 10 else "eye_level")
    box = subject_box(cam, aim, lens, aspect, spot, height_m)
    why = {"stage": f"máy GIẢI từ yêu cầu khung ({sc.get('source', 'stage_v2')}): cao {cam[2] - spot[2]:.2f} m trên chỗ đứng, "
                    f"nghiêng {pitch:.0f}°, ống {lens:g} mm — đã đo che khuất bằng tia, không tự chỉnh"}
    if sc.get("pov"):
        why["pov"] = f"góc nhìn của {sc['pov']}"
    if sc.get("move"):
        why["move"] = f"máy chuyển động trong shot: {sc['move']} (nền = khung ĐẦU)"
    return {"camera": {"name": name, "location": [round(c, 3) for c in cam], "look_at": [round(c, 3) for c in aim], "lens": lens,
                       "angle": angle, "locked": True, **({"props": sc["props"]} if sc.get("props") else {})},
            "subject_box": box, "feet_y": box[3], "distance_m": round(math.hypot(cam[0] - spot[0], cam[1] - spot[1]), 2), "size": None,
            "side": None, "behind": False, "frame_h_m": None, "horizon_y": horizon_y(cam, aim, lens, aspect), "pitch_deg": round(pitch, 1),
            "fixes": [], "problem": None, "why": why}


def plan_cameras(shots: List[Dict], spot_of, height_of, aspect: float = 9 / 16, setup_field: Optional[str] = None,
                 stage_field: Optional[str] = None) -> Dict[int, Dict]:
    """scene id -> camera_for(...) for shots at a 3D place. Shots of one camera_setup with the same size share the first one's camera
    (the DP's coverage: one position, several shots). spot_of(shot) -> (xyz, facing_deg) or None; height_of(shot) -> metres.
    G0 (flag director_camera_plan): `setup_field` = the shot field holding the Director's camera set-up of the scene (core/camera_plan
    writes `plate_setup` + `plate_setup_scene`); shots of one plan's set-up + one size + one spot (+ same angle, look-down, lens, sky)
    share the first one's camera (`shared_by` "plan") — so one cache
    key and one render. None (flag off) = exactly the old grouping."""
    out, setups = {}, {}
    for s in shots:
        data = s["data"]
        spot = spot_of(s)
        if spot is None:
            continue
        if stage_field and data.get(stage_field):       # Sân khấu 3D v2: máy đã giải + duyệt — một shot một máy, không gom
            out[s["id"]] = from_stage(data[stage_field], spot[0], height_of(s), aspect, name=f"shot_{s['id']}")
            continue
        if setup_field and data.get(setup_field):
            # rà G0: the set-up's plan (scene field; an old shot: its story_scene, none = the shot alone) + everything camera_for
            # reads from the shot besides the spot/facing — a look-down / other lens / other angle / sky shot is never merged
            scene = data.get(f"{setup_field}_scene") or data.get("story_scene") or f"shot_{s['id']}"
            key = (scene, "plan", str(data[setup_field]), size_of(data), tuple(round(float(c), 3) for c in spot[0]),
                   str(data.get("angle") or "eye").lower(), looks_down(data), lens_of(data, 0.0), wants_sky(data))
        else:
            key = (data.get("story_scene"), data.get("camera_setup"), size_of(data)) if data.get("camera_setup") else None
        if key and key in setups:
            out[s["id"]] = dict(setups[key], shared_with=setups[key]["camera"]["name"],
                                **({"shared_by": "plan"} if key[1] == "plan" else {}))
            continue
        cam = camera_for(data, spot[0], spot[1], height_of(s), aspect, name=f"shot_{s['id']}")
        out[s["id"]] = cam
        if key:
            setups[key] = cam
    return out
