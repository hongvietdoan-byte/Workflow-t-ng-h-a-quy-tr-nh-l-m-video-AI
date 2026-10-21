"""Coarse white model (S10.6, người dùng 30/09): a short clay video of the real 3D place with one coloured block per person, to lock where
each person stands, how they move and the camera — the official Seedance 2.5 "粗粒度白模" reference (sd25-pe: "每个几何体必须单独映射到最终
主体"). Test T3 (30/09) lost the third person when only words set the places; a block per person at a measured spot does not.

People are placed in metres from the camera of a spot of the place's 3D pack (location_pack model3d): `fwd` ahead of the camera, `right`
to its right; `to` moves them during the clip; `face` = "camera", another person's name, or [fwd, right]. The clip meets the reference
video rules of both services (≥ 3 s, both sides ≥ 704 px, square pixels) so it can go as @Video as it is."""
import math
import os
import subprocess
from typing import Dict, List, Optional

EYE = 1.6
COLORS = [("red", (0.85, 0.08, 0.08)), ("blue", (0.10, 0.30, 0.95)), ("yellow", (0.95, 0.80, 0.05)), ("green", (0.10, 0.70, 0.20)),
          ("purple", (0.55, 0.15, 0.80)), ("orange", (0.98, 0.45, 0.05))]


class WhiteboxError(Exception):
    pass


# V3.1 M3.2 (C-M32, cờ whitebox_height_dummy — TẮT = whitebox cũ: EYE 1,6 m, khối 1,8 m, nhắm ngực 1,2 m): người nộm đúng `height_m` hồ sơ Kho
# đã duyệt (thiếu → nói, không mặc định im lặng), máy ở mắt = EYE_SHARE × height_m; pitch "eye" ≤ EYE_MAX_DEG, "slightly_high" cúi
# SLIGHTLY_HIGH_DEG (khoảng 8–12°) — G2 (tỉ lệ người), G3 (#31 shot 28 khai eye mà pitch +17,3°), A10 (high 30° làm nền chỉ còn sàn)
DUMMY_FLAG = "whitebox_height_dummy"
EYE_SHARE = 0.93                                   # như plate_camera.camera_for (mắt = 0,93 × chiều cao)
SLIGHTLY_HIGH_DEG, SLIGHTLY_HIGH_RANGE = 10.0, (8.0, 12.0)
EYE_MAX_DEG = 5.0
FALLBACK_HEIGHT = 1.8
PITCH_ANGLES = ("eye", "slightly_high")


def dummy_enabled() -> bool:
    from . import features
    return features.on(DUMMY_FLAG)


def eye_height(height_m: float) -> float:
    if not height_m or float(height_m) <= 0:
        raise WhiteboxError(f"chiều cao nhân vật không hợp lệ ({height_m!r}) — cần `height_m` hồ sơ Kho")
    return float(height_m) * EYE_SHARE


def pitch_camera(feet_z: float, height_m: float, dist: float, angle: str = "eye") -> Dict[str, float]:
    """Máy cách nhân vật `dist` m, nhìn vào mắt nhân vật: "eye" → máy ở mắt (pitch 0); "slightly_high" → máy nâng để cúi SLIGHTLY_HIGH_DEG.
    → {"location_z", "aim_z", "pitch_deg"} (pitch âm = cúi)."""
    if angle not in PITCH_ANGLES:
        raise WhiteboxError(f"pitch '{angle}' không thuộc {'/'.join(PITCH_ANGLES)}")
    aim = float(feet_z) + eye_height(height_m)
    lift = float(dist) * math.tan(math.radians(SLIGHTLY_HIGH_DEG)) if angle == "slightly_high" else 0.0
    return {"location_z": aim + lift, "aim_z": aim, "pitch_deg": -SLIGHTLY_HIGH_DEG if lift else 0.0}


def pitch_note(angle: str, pitch_deg: float) -> Optional[str]:
    """VÀNG khi pitch đo được không khớp mức khai: "eye" mà |pitch| > EYE_MAX_DEG; "slightly_high" mà cúi ngoài 8–12°. Mức khác → None."""
    a = str(angle or "").lower()
    if a == "eye" and abs(pitch_deg) > EYE_MAX_DEG:
        return (f"shot khai angle 'eye' nhưng máy {'ngửa' if pitch_deg > 0 else 'cúi'} {abs(pitch_deg):.1f}° (> {EYE_MAX_DEG:g}°) — "
                "nền / người sẽ lệch tầm mắt")
    lo, hi = SLIGHTLY_HIGH_RANGE
    if a == "slightly_high" and not lo <= -pitch_deg <= hi:
        return f"shot khai 'slightly_high' (cúi {lo:g}–{hi:g}°) nhưng máy pitch {pitch_deg:+.1f}°"
    return None


def heights_of(conn, project_id: int, names: List[str]):
    """({tên: height_m}, [tên thiếu]) từ hồ sơ chuẩn Kho đã duyệt (assets.standard_for — như stage_auto)."""
    from . import assets
    got, missing = {}, []
    for n in names:
        prof = assets.standard_for(conn, project_id, n)
        if prof and prof.get("height_m"):
            got[n] = float(prof["height_m"])
        else:
            missing.append(n)
    return got, missing


def camera_of(m3d: Dict, spot: str) -> Dict:
    """The spot's eye-level camera: at the spot, looking along its `view` (surroundings spots) or at the landmark (the anchor)."""
    s = (m3d.get("spots") or {}).get(spot)
    if not s:
        raise WhiteboxError(f"không có chỗ đứng '{spot}' trong gói 3D (có: {', '.join(list(m3d.get('spots') or {})[:12])}…)")
    x, y, z = s["at"]
    tx, ty, tz = (s.get("view") or m3d.get("anchor") or [x, y + 10, z])[:3]
    return {"location": [x, y, z + EYE], "look_at": [tx, ty, max(z + EYE, min(tz, z + EYE + 3.0))], "ground_z": z}


def _axes(cam: Dict):
    fx, fy = cam["look_at"][0] - cam["location"][0], cam["look_at"][1] - cam["location"][1]
    n = math.hypot(fx, fy) or 1.0
    f = (fx / n, fy / n)
    return f, (f[1], -f[0])                        # right of the camera, z up


def _point(cam: Dict, fwd: float, right: float) -> List[float]:
    (fx, fy), (rx, ry) = _axes(cam)
    x0, y0 = cam["location"][0], cam["location"][1]
    return [x0 + fx * fwd + rx * right, y0 + fy * fwd + ry * right, cam["ground_z"]]


def plan(m3d: Dict, spot: str, people: List[Dict], seconds: float = 4.0, lens: float = 28.0, name: str = "whitebox",
         push_m: float = 0.0, aim: str = "people", heights: Optional[Dict[str, float]] = None, angle: str = "eye") -> Dict:
    """The render_plates animation of the white model. people: [{"name", "at": [fwd, right], "to": [fwd, right]?, "face": ...}].
    aim "people" (default): the camera looks at the middle of the group at chest height — the white model is about where people are
    (first render 30/09 aimed at the tower and left the three blocks at the bottom edge); "spot": the spot's own view.
    M3.2 (cờ whitebox_height_dummy): heights {tên: height_m hồ sơ Kho} → khối đúng chiều cao + `eye_m`; máy ở mắt nhóm, pitch theo
    `angle` (eye / slightly_high); thiếu chiều cao → khối FALLBACK_HEIGHT + câu trong "warnings". Cờ tắt: heights / angle bỏ qua."""
    if not people:
        raise WhiteboxError("white-model cần ít nhất một người")
    if len(people) > len(COLORS):
        raise WhiteboxError(f"tối đa {len(COLORS)} người (mỗi người một màu)")
    dummy = dummy_enabled()
    warnings: List[str] = []
    if dummy and angle not in PITCH_ANGLES:
        raise WhiteboxError(f"pitch '{angle}' không thuộc {'/'.join(PITCH_ANGLES)}")
    cam = camera_of(m3d, spot)
    where = {p["name"]: _point(cam, *p["at"]) for p in people}
    actors = []
    for (cname, rgb), p in zip(COLORS, people):
        start = _point(cam, *p["at"])
        end = _point(cam, *p["to"]) if p.get("to") else start

        def face_of(at):
            f = p.get("face", "camera")
            if f == "camera":
                return [cam["location"][0], cam["location"][1], at[2]]
            if isinstance(f, str):
                if f not in where:
                    raise WhiteboxError(f"'{p['name']}' nhìn về '{f}' — không có người này trong white-model")
                return where[f]
            return _point(cam, *f)
        height = float(p.get("height", FALLBACK_HEIGHT))
        actor = {"name": p["name"], "color": list(rgb), "color_name": cname, "height": height,
                 "keys": [{"t": 0.0, "location": start, "face": face_of(start)}, {"t": 1.0, "location": end, "face": face_of(end)}]}
        if dummy:
            known = p.get("height") or (heights or {}).get(p["name"])
            if not known:
                warnings.append(f"thiếu chiều cao {p['name']} (Kho → hồ sơ chuẩn `height_m`, đã duyệt) — khối tạm {FALLBACK_HEIGHT:g} m")
            actor["height"] = float(known or FALLBACK_HEIGHT)
            actor["eye_m"] = round(eye_height(actor["height"]), 4)
        actors.append(actor)
    if aim == "people":
        mid = [sum(a["keys"][0]["location"][i] for a in actors) / len(actors) for i in range(2)]
        cam = dict(cam, look_at=[mid[0], mid[1], cam["ground_z"] + 1.2])
    if dummy:                                       # máy ở mắt nhóm, pitch theo mức khai
        group_h = sum(a["height"] for a in actors) / len(actors)
        dist = math.hypot(cam["look_at"][0] - cam["location"][0], cam["look_at"][1] - cam["location"][1])
        z = pitch_camera(cam["ground_z"], group_h, dist, angle)
        cam = dict(cam, location=[cam["location"][0], cam["location"][1], z["location_z"]],
                   look_at=[cam["look_at"][0], cam["look_at"][1], z["aim_z"]])
    (fx, fy), _ = _axes(cam)
    cam_end = [cam["location"][0] + fx * push_m, cam["location"][1] + fy * push_m, cam["location"][2]]
    return {"name": name, "seconds": float(max(seconds, 3.2)), "fps": 24, "model_coords": True, "white": True, "lens": float(lens),
            "keys": [{"t": 0.0, "location": cam["location"], "look_at": cam["look_at"]},
                     {"t": 1.0, "location": cam_end, "look_at": cam["look_at"]}],
            "actors": actors, **({"warnings": warnings} if warnings else {})}


def role_line(anim: Dict, index: int = 1) -> str:
    """The prompt line of the white-model video, official template (coarse white model): what it gives, what not, each block → person."""
    maps = " ".join(f"The {a['color_name']} block in @Video {index} is {a['name']}." for a in anim["actors"])
    return (f"@Video {index} is a coarse white-model reference: it gives only where each person stands and faces, how they move, and the camera. "
            f"Do not take its plain grey clay look, its blocks or its empty surfaces. {maps}")


def to_mp4(frames_dir: str, fps: int, dst: str, ffmpeg: str = "ffmpeg") -> str:
    """Frames → mp4 that both services take: short side ≥ 704 px, square pixels, 24 fps."""
    vf = "scale='if(lt(iw,ih),max(704,iw),-2)':'if(lt(iw,ih),-2,max(704,ih))':flags=lanczos,setsar=1"
    subprocess.run([ffmpeg, "-y", "-v", "error", "-framerate", str(fps), "-i", os.path.join(frames_dir, "f_%04d.png"), "-vf", vf,
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", dst], check=True, capture_output=True)
    return dst


def render(m3d: Dict, anim: Dict, out_dir: str, resolution=(720, 1280), day: Optional[Dict] = None, timeout: int = 3600) -> str:
    """Render the white model with Blender (0 USD, the Blender queue) → mp4 path."""
    from . import location_pack, plates3d
    from .ffmpeg_studio import find_ffmpeg
    light = dict(day if day is not None else (m3d.get("light") or {}).get("day") or {})
    cfg = plates3d.plan(m3d["path"], out_dir, sky="A", sun_elevation=light.pop("sun_elevation", 45),
                        sun_azimuth=m3d.get("sun_azimuth", 250.0), resolution=resolution, cameras=[], only_cameras=True,
                        sky_extra=light or None, real_height_m=m3d.get("real_height_m"), samples=8,
                        stretch=location_pack.stretch_spec(m3d))
    cfg["depth"] = False
    cfg["animations"] = [anim]
    man = plates3d.render(cfg, timeout=timeout)
    got = next((a for a in man.get("animations") or [] if a["name"] == anim["name"]), None)
    if not got:
        raise WhiteboxError("Blender không trả về video white-model: " + "; ".join(man.get("warnings") or []))
    return to_mp4(os.path.join(cfg["out_dir"], got["folder"]), got["fps"], os.path.join(out_dir, anim["name"] + ".mp4"), find_ffmpeg())
