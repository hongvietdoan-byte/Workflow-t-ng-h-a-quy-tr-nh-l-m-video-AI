"""Time of day and weather of a location pack (kế hoạch V4 1.6 step 3) — no AI, no credit.

Two halves, so the same weather lands on the background AND on the character:
  1. on the 3D geometry, inside Blender (tools/render_plates.py): sun height / colour / strength, a transparent sky at night and dusk,
     snow on the faces that look up, wet ground, fog in the air   -> `blender_env`
  2. in 2D, after compositing (Pillow + numpy): a painted night / dusk sky behind the transparent sky, a colour grade, falling rain or
     snow, a lightning flash, haze                                  -> `finish_plate`, `overlay_still`, `overlay_video`

Names the Director writes (shot field `weather`, scene `time`) — a fixed list; anything else falls back to clear day and is reported.
"""
import math
import os
import random
import subprocess
from typing import Dict, List, Optional, Tuple

TIMES = ("dawn", "day", "dusk", "night")
WEATHERS = ("clear", "cloudy", "fog", "rain", "storm", "snow", "snowfall", "ice", "sandstorm")
_TIME_WORDS = {"night": ("đêm", "night", "tối", "khuya", "midnight"), "dusk": ("hoàng hôn", "chiều tà", "dusk", "sunset", "chạng vạng"),
               "dawn": ("bình minh", "dawn", "sunrise", "rạng sáng"), "day": ("ngày", "day", "trưa", "sáng", "noon", "morning")}

# sun: elevation°, strength, colour; exposure of the render
_SUN = {"dawn": (8, 1.6, (1.0, 0.72, 0.55), -0.6), "day": (45, 2.6, (1.0, 0.97, 0.92), -0.5),
        "dusk": (6, 1.8, (1.0, 0.55, 0.35), -0.7), "night": (38, 0.9, (0.55, 0.65, 1.0), -1.4)}
# geometry weather (0..1) for tools/render_plates.py
_GEOMETRY = {"fog": {"fog": 0.6}, "rain": {"wet": 0.8, "fog": 0.15}, "storm": {"wet": 1.0, "fog": 0.3},
             "snow": {"snow": 0.9, "fog": 0.1}, "snowfall": {"snow": 0.9, "fog": 0.25}, "ice": {"snow": 0.4, "wet": 0.6},
             "sandstorm": {"fog": 0.8}, "cloudy": {"fog": 0.05}}
# 2D grade: RGB multipliers + lift (added) per time, then per weather
_GRADE_TIME = {"dawn": ((1.02, 0.95, 0.92), (0.02, 0.01, 0.02)), "day": ((1.0, 1.0, 1.0), (0, 0, 0)),
               "dusk": ((1.05, 0.88, 0.80), (0.03, 0.01, 0.0)), "night": ((0.42, 0.47, 0.60), (0.0, 0.005, 0.02))}
_FOG_COLOUR = {"dawn": (0.78, 0.72, 0.70), "day": (0.80, 0.82, 0.85), "dusk": (0.72, 0.58, 0.52), "night": (0.10, 0.12, 0.17)}
_FOG_DENSITY = 0.045      # per metre at fog 1: ~50 % hidden at 15 m, a tower 40 m away is a silhouette
_GRADE_WEATHER = {"cloudy": ((0.92, 0.94, 0.97), (0.02, 0.02, 0.03)), "rain": ((0.85, 0.88, 0.95), (0.01, 0.02, 0.04)),
                  "storm": ((0.75, 0.80, 0.92), (0.0, 0.01, 0.04)), "fog": ((0.90, 0.92, 0.95), (0.06, 0.06, 0.07)),
                  "snow": ((0.96, 0.98, 1.04), (0.03, 0.03, 0.05)), "snowfall": ((0.95, 0.97, 1.04), (0.04, 0.04, 0.06)),
                  "ice": ((0.93, 0.98, 1.06), (0.02, 0.03, 0.05)), "sandstorm": ((1.05, 0.92, 0.72), (0.06, 0.04, 0.0))}
_FALLING = {"rain": "rain", "storm": "rain", "snowfall": "snow", "snow": None, "sandstorm": "dust"}


def time_of(data: Dict) -> str:
    raw = str(data.get("time_of_day") or data.get("time") or "").lower()
    if raw in TIMES:
        return raw
    for name, words in _TIME_WORDS.items():
        if any(w in raw for w in words):
            return name
    return "day"


def weather_of(data: Dict) -> Tuple[str, Optional[str]]:
    """(weather, problem) — an unknown value is not guessed silently: it falls back to clear and says so."""
    raw = str(data.get("weather") or "clear").strip().lower()
    if raw in WEATHERS:
        return raw, None
    return "clear", f"thời tiết '{raw}' không có trong danh sách ({', '.join(WEATHERS)}) — dùng trời quang"


def env_of(data: Dict) -> Dict:
    time, weather = time_of(data), weather_of(data)[0]
    return {"time": time, "weather": weather}


def blender_env(env: Dict, sun_azimuth: float = 250.0) -> Dict:
    """kwargs for plates3d.plan: sky mode (C = transparent sky, painted after, for night / dusk / dawn and bad weather), sun,
    geometry weather."""
    elev, strength, colour, exposure = _SUN[env["time"]]
    weather = env["weather"]
    if weather in ("rain", "storm", "fog", "sandstorm", "cloudy"):
        strength *= 0.55                                      # overcast: soft light, weak shadows
    transparent = env["time"] != "day" or weather in ("rain", "storm", "snowfall", "fog", "sandstorm")
    return {"sky": "C" if transparent else "A", "sun_elevation": elev, "sun_azimuth": sun_azimuth,
            "sky_extra": {"sun_strength": round(strength, 2), "sun_color": list(colour), "exposure": exposure},
            "weather": dict(_GEOMETRY.get(weather, {}))}


def key(env: Dict) -> str:
    return f"{env['time']}-{env['weather']}"


# ---- 2D ----------------------------------------------------------------------------------------------------------------------
def _np():
    import numpy as np
    return np


def paint_sky(width: int, height: int, env: Dict, seed: int = 1):
    """A sky picture (RGB float array 0..1) for a transparent render: gradient + stars + moon at night, warm band at dusk / dawn,
    flat grey for bad weather."""
    np = _np()
    t = np.linspace(0, 1, height)[:, None, None]
    time, weather = env["time"], env["weather"]
    if weather in ("rain", "storm", "fog", "snowfall", "cloudy"):
        top, low = ((0.10, 0.12, 0.16), (0.24, 0.27, 0.32)) if time == "night" else ((0.45, 0.48, 0.52), (0.68, 0.70, 0.73))
    elif weather == "sandstorm":
        top, low = (0.55, 0.42, 0.25), (0.78, 0.64, 0.42)
    elif time == "night":
        top, low = (0.02, 0.04, 0.11), (0.10, 0.16, 0.32)
    elif time in ("dusk", "dawn"):
        top, low = (0.20, 0.25, 0.48), (0.98, 0.58, 0.36)
    else:
        top, low = (0.32, 0.55, 0.90), (0.72, 0.84, 0.97)
    sky = np.array(top)[None, None, :] * (1 - t) + np.array(low)[None, None, :] * t
    sky = np.repeat(sky, width, axis=1)
    rnd = random.Random(seed)
    if time == "night" and weather in ("clear", "snow", "ice"):
        for _ in range(int(width * height / 5000)):
            x, y = rnd.randrange(width), rnd.randrange(int(height * 0.6))
            sky[y, x] = min(1.0, 0.55 + rnd.random() * 0.45)
        cx, cy, r = int(width * 0.22), int(height * 0.12), max(int(width * 0.045), 6)
        yy, xx = np.ogrid[:height, :width]
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        glow = np.clip(1 - d / (r * 6), 0, 1)[..., None] ** 2 * np.array([0.25, 0.30, 0.40])
        sky = np.clip(sky + glow, 0, 1)
        sky[d <= r] = (0.93, 0.95, 1.0)
    return sky


def grade(rgb, env: Dict):
    np = _np()
    mul, lift = _GRADE_TIME[env["time"]]
    out = rgb * np.array(mul) + np.array(lift)
    if env["weather"] in _GRADE_WEATHER:
        mul, lift = _GRADE_WEATHER[env["weather"]]
        out = out * np.array(mul) + np.array(lift)
    return np.clip(out, 0, 1)


def distance_map(depth_path: str, depth_range, size):
    """Metres from the camera for every pixel of a depth picture (white = near end of the range, black / transparent = far)."""
    np = _np()
    from PIL import Image
    with Image.open(depth_path) as im:
        d = im.convert("RGBA").resize(size)
        arr = np.asarray(d, dtype=np.float32) / 255.0
    near, far = float(depth_range[0]), float(depth_range[1])
    dist = near + (1.0 - arr[..., 0]) * (far - near)
    dist[arr[..., 3] < 0.5] = far * 10                           # empty sky: very far
    return dist


def fog_amount(env: Dict) -> float:
    return float(_GEOMETRY.get(env["weather"], {}).get("fog", 0.0))


def finish_plate(render_path: str, out_path: str, env: Dict, seed: int = 1, depth_path: Optional[str] = None,
                 depth_range=None) -> str:
    """A rendered plate -> the background of the shot: painted sky behind a transparent sky, fog laid by distance (depth picture),
    then the colour grade of the time and weather (the character gets the same grade and fog in core/composite.py)."""
    np = _np()
    from PIL import Image
    with Image.open(render_path) as im:
        rgba = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
    h, w = rgba.shape[:2]
    alpha = rgba[..., 3:4]
    rgb = rgba[..., :3]
    if float(alpha.min()) < 0.999:
        rgb = rgb * alpha + paint_sky(w, h, env, seed) * (1 - alpha)
    fog = fog_amount(env)
    if fog > 0 and depth_path and depth_range and os.path.exists(depth_path):
        rgb = apply_fog(rgb, distance_map(depth_path, depth_range, (w, h)), env)
    rgb = grade(rgb, env)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    Image.fromarray((rgb * 255 + 0.5).astype("uint8")).save(out_path)
    return out_path


def apply_fog(rgb, dist, env: Dict, amount: Optional[float] = None):
    """Fog in front of whatever is at `dist` metres (a plate, or the character at their own distance)."""
    np = _np()
    fog = fog_amount(env) if amount is None else amount
    if fog <= 0:
        return rgb
    t = 1.0 - np.exp(-_FOG_DENSITY * fog * np.asarray(dist, dtype=np.float32))
    t = t[..., None] if np.ndim(t) == 2 else t
    return rgb * (1 - t) + np.array(_FOG_COLOUR[env["time"]]) * t


def _streaks(w: int, h: int, kind: str, rnd, phase: float = 0.0):
    """One layer of falling rain / snow / dust (float alpha 0..1, and the colour)."""
    np = _np()
    layer = np.zeros((h, w), dtype=np.float32)
    if kind == "rain":
        n, length = int(w * h / 900), max(int(h * 0.03), 8)
        for _ in range(n):
            x, y0 = rnd.randrange(w), (rnd.randrange(h) + int(phase * h * 0.9)) % h
            for k in range(length):
                y, xx = y0 + k, x + k // 6
                if 0 <= y < h and 0 <= xx < w:
                    layer[y, xx] = max(layer[y, xx], 0.35)
        return layer, (0.80, 0.85, 0.95)
    if kind == "snow":
        n = int(w * h / 1500)
        for _ in range(n):
            x = (rnd.randrange(w) + int(math.sin(phase * 6 + rnd.random() * 6) * 6)) % w
            y = (rnd.randrange(h) + int(phase * h * 0.25)) % h
            r = 1 + rnd.randrange(3)
            layer[max(0, y - r):y + r, max(0, x - r):x + r] = 0.85
        return layer, (1.0, 1.0, 1.0)
    n = int(w * h / 600)
    for _ in range(n):
        x, y = (rnd.randrange(w) + int(phase * w * 0.6)) % w, rnd.randrange(h)
        layer[y, x] = 0.4
    return layer, (0.85, 0.72, 0.50)


def overlay_still(img_path: str, out_path: str, env: Dict, seed: int = 1) -> str:
    """Falling weather on a still (the start frame of a composited shot): one frozen layer of rain / snow / dust."""
    kind = _FALLING.get(env["weather"])
    from PIL import Image
    if not kind:
        if img_path != out_path:
            Image.open(img_path).save(out_path)
        return out_path
    np = _np()
    with Image.open(img_path) as im:
        rgb = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    h, w = rgb.shape[:2]
    layer, colour = _streaks(w, h, kind, random.Random(seed))
    rgb = rgb * (1 - layer[..., None]) + np.array(colour) * layer[..., None]
    Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype("uint8")).save(out_path)
    return out_path


def flash_times(duration: float, seed: int = 1, every: float = 3.5) -> List[float]:
    """Lightning moments of a storm clip (the whole frame flashes, background and character together)."""
    rnd = random.Random(seed)
    t, out = rnd.uniform(0.4, 1.2), []
    while t < duration - 0.3:
        out.append(round(t, 2))
        t += every * rnd.uniform(0.7, 1.4)
    return out


def overlay_video(video: str, out_path: str, env: Dict, ffmpeg: str, seed: int = 1, fps: int = 24) -> str:
    """Falling weather + lightning on a clip: frames are read, the layer of that moment added, and written back (numpy + ffmpeg
    pipes, no temp frames on disk). The audio of the clip is kept."""
    kind = _FALLING.get(env["weather"])
    storm = env["weather"] == "storm"
    if not kind and not storm:
        return video
    np = _np()
    probe = subprocess.run([ffmpeg, "-i", video], capture_output=True, text=True, errors="replace")
    import re
    m = re.search(r", (\d{2,5})x(\d{2,5})", probe.stderr or "")
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe.stderr or "")
    if not m:
        raise ValueError("không đọc được kích thước clip")
    w, h = int(m.group(1)), int(m.group(2))
    total = (int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))) if dur else 5.0
    flashes = flash_times(total, seed) if storm else []
    reader = subprocess.Popen([ffmpeg, "-loglevel", "error", "-i", video, "-r", str(fps), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                              stdout=subprocess.PIPE)
    from . import ffmpeg_studio
    writer = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
                               "-i", "-", "-i", video, "-map", "0:v", "-map", "1:a?", "-vf", ffmpeg_studio.TO_YUV709, "-c:v", "libx264",
                               "-crf", "18", "-pix_fmt", "yuv420p", *ffmpeg_studio.COLOR_TAGS, "-c:a", "copy", "-shortest", out_path],
                              stdin=subprocess.PIPE)          # RGB frames: converted with the BT.709 matrix they are tagged with
    rnd_layers = [random.Random(seed + k) for k in range(6)]
    n = 0
    try:
        while True:
            raw = reader.stdout.read(w * h * 3)
            if len(raw) < w * h * 3:
                break
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3).astype(np.float32) / 255.0
            t = n / fps
            if kind:
                layer, colour = _streaks(w, h, kind, random.Random(rnd_layers[n % 6].random() * 1e6), phase=(t * 1.7) % 1)
                frame = frame * (1 - layer[..., None]) + np.array(colour) * layer[..., None]
            for f in flashes:
                if f <= t < f + 0.25:
                    k = 1 - (t - f) / 0.25
                    frame = np.clip(frame * (1 + 1.6 * k) + 0.18 * k * np.array((0.8, 0.85, 1.0)), 0, 1)
            writer.stdin.write((np.clip(frame, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
            n += 1
    finally:
        writer.stdin.close()
        writer.wait()
        reader.wait()
    return out_path
