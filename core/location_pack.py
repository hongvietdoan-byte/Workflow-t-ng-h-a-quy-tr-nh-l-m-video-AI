"""Location pack (kế hoạch V4 mục 1): a place of the library with its 3D model registered once — spots where characters stand — so
every shot set there gets a background rendered from its own camera (pixel-true place), shared across projects through a cache.

Registry: the place's `assets.profile` JSON keeps `model3d` =
    {"path", "sha256", "real_height_m" (None = the model's own metres), "anchor": [x, y, z] of the landmark (model coordinates),
     "spots": {"plaza_front": {"at": [x, y, z], "facing": 0, "label": "..."}, ...}, "default_spot": "plaza_front",
     "sun_azimuth": 250, "notes": ""}
Shot fields the DP writes: `plate_spot` (a spot name; else the default), `weather`, scene `time`.
Per-project index: <data>/<pid>/plates/index.json  (scene id -> the plate files of its camera + where the character goes).
Cache: <data root>/_plates3d/cache/<key>/ — key = model sha + camera + time/weather + size + script version: two projects with the
same camera render once.
"""
import hashlib
import json
import os
import shutil
from typing import Callable, Dict, List, Optional

from . import assets, plate_camera, plate_env, plates3d

SCRIPT_VERSION = "v4-1"          # bump when tools/render_plates.py changes what a plate looks like (old cache entries are not reused)


class LocationPackError(ValueError):
    """Shown to the person as it is."""


def model3d(conn, asset_id: Optional[int]) -> Optional[Dict]:
    if not asset_id:
        return None
    entry = assets.get_profile(conn, asset_id).get("model3d")
    return entry if isinstance(entry, dict) and entry.get("path") else None


def _file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def set_model3d(conn, asset_id: int, path: str, spots: Dict[str, Dict], default_spot: Optional[str] = None,
                anchor: Optional[List[float]] = None, real_height_m: Optional[float] = None, sun_azimuth: float = 250.0,
                notes: str = "") -> Dict:
    """Register (or update) the 3D model of a place. The other profile keys are kept."""
    if not os.path.exists(path):
        raise LocationPackError(f"không thấy file 3D: {path}")
    if not spots:
        raise LocationPackError("cần ít nhất một chỗ đứng (spot) cho nhân vật")
    for name, sp in spots.items():
        if not isinstance(sp.get("at"), (list, tuple)) or len(sp["at"]) != 3:
            raise LocationPackError(f"chỗ đứng {name}: cần 'at' = [x, y, z]")
    row = conn.execute("SELECT profile, kind FROM assets WHERE id=?", (asset_id,)).fetchone()
    if row is None or row["kind"] != "location":
        raise LocationPackError("chỉ gắn mô hình 3D cho mục loại bối cảnh")
    prof = json.loads(row["profile"]) if row["profile"] else {}
    prof["model3d"] = {"path": os.path.abspath(path), "sha256": _file_sha(path), "real_height_m": real_height_m, "anchor": anchor,
                       "spots": {k: {"at": [float(v) for v in sp["at"]], "facing": float(sp.get("facing", 0)),
                                     "label": sp.get("label", k)} for k, sp in spots.items()},
                       "default_spot": default_spot if default_spot in spots else next(iter(spots)), "sun_azimuth": float(sun_azimuth),
                       "notes": notes}
    conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps(prof, ensure_ascii=False), asset_id))
    conn.commit()
    return prof["model3d"]


def spot_for(entry: Dict, data: Dict) -> Dict:
    name = data.get("plate_spot") or entry.get("default_spot")
    spots = entry.get("spots") or {}
    sp = spots.get(name) or spots.get(entry.get("default_spot")) or next(iter(spots.values()))
    return dict(sp, name=name if name in spots else entry.get("default_spot"))


def spot_problem(entry: Dict, data: Dict) -> Optional[str]:
    """A `plate_spot` the place does not have falls back to the default spot — said, never silent (CHUAN_XAY_DUNG rule 1)."""
    name = data.get("plate_spot")
    if name and name not in (entry.get("spots") or {}):
        return f"chỗ đứng '{name}' không có ở bối cảnh này ({', '.join(entry.get('spots') or {})}) — dùng '{entry.get('default_spot')}'"
    return None


def director_block(conn, pid: int) -> str:
    """V4 GĐ4 (dp.md Q6): what the Director / DP must know to write `plate_spot`, `weather`, `plate_mode` for a project whose places
    have a registered 3D model — the spots by name, the fixed weather / time names, the two ways of making the clip. Empty when the
    feature is off or no place of the project has a model."""
    from . import features
    if not features.on("location_plates"):
        return ""
    rows = []
    for a in assets.project_assets(conn, pid):
        entry = model3d(conn, a["id"]) if a.get("kind") == "location" else None
        if not entry:
            continue
        spots = "; ".join(f"`{k}` ({v.get('label') or k})" for k, v in (entry.get("spots") or {}).items())
        rows.append(f"- **{a['name']}**: chỗ đứng {spots} — mặc định `{entry.get('default_spot')}`")
    if not rows:
        return ""
    return ("# Gói bối cảnh (nền là render 3D thật của nơi này — AI chỉ vẽ nhân vật)\n" + "\n".join(rows) + "\n"
            f"- `plate_spot`: tên một chỗ đứng ở trên (không ghi = mặc định; tên lạ bị đổi về mặc định và báo lại).\n"
            f"- `weather` (shot hoặc cảnh): chỉ một trong {', '.join(plate_env.WEATHERS)}; `time` của cảnh: {', '.join(plate_env.TIMES)}.\n"
            "- `plate_mode`: bỏ trống = cách 1 (ảnh khung đầu ghép sẵn, model video diễn trên nền thật — rẻ, nhưng model có thể vẽ lại "
            "nền; code chấm và tự chuyển cách 2 một lần); `\"green\"` = cách 2 (nhân vật diễn trên phông xanh, ghép từng khung lên nền — "
            "dùng cho shot mà nền PHẢI giữ nguyên: mốc nổi tiếng chiếm lớn trong khung, máy đứng yên).\n"
            "- Shot cận ở chân một công trình cao chỉ thấy chân công trình: muốn thấy mốc thì hạ máy (`angle: \"low\"`, ngửa lên) hoặc "
            "dùng trung/toàn.")



def _height(conn, pid: int, data: Dict) -> float:
    """Real height of the main character of the shot (standard profile height_m), else 1.75 m."""
    for name in data.get("characters") or []:
        prof = assets.standard_for(conn, pid, name)
        if prof and prof.get("height_m"):
            return float(prof["height_m"])
    return 1.75


def shots_at_3d_places(conn, pid: int) -> List[Dict]:
    """[{id, idx, data, place, entry}] for every shot whose place has a registered 3D model."""
    out = []
    for s in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        data = json.loads(s["data"] or "{}")
        place = assets.scene_location(conn, pid, data)
        entry = model3d(conn, place["id"]) if place else None
        if entry:
            out.append({"id": s["id"], "idx": s["idx"], "data": data, "place": place, "entry": entry})
    return out


def cache_root(data_root: str) -> str:
    return os.path.join(data_root, "_plates3d", "cache")


def cache_key(entry: Dict, camera: Dict, env: Dict, resolution) -> str:
    cam = {k: v for k, v in camera.items() if k != "name"}          # the camera, not which shot of which project asked for it
    blob = json.dumps({"model": entry["sha256"], "h": entry.get("real_height_m"), "cam": cam, "env": env, "res": list(resolution),
                       "v": SCRIPT_VERSION}, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:20]


def _index_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "plates", "index.json")


def index(data_dir: str, pid: int) -> Dict[str, Dict]:
    try:
        with open(_index_path(data_dir, pid), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def plate_of(data_dir: str, pid: int, scene_id: int) -> Optional[Dict]:
    rec = index(data_dir, pid).get(str(scene_id))
    return rec if rec and os.path.exists(rec.get("plate", "")) else None


def plate_failed(data_dir: str, pid: int, scene_id: int) -> Optional[str]:
    """Why Blender gave no plate for this shot's camera (the shot then draws a normal picture instead of waiting), else None."""
    rec = index(data_dir, pid).get(str(scene_id))
    return (rec or {}).get("failed")


def _failed(root: str, key: str) -> Optional[str]:
    try:
        with open(os.path.join(root, key, "failed.json"), encoding="utf-8") as f:
            return json.load(f).get("reason") or "Blender không trả về góc máy này"
    except (OSError, ValueError):
        return None


def forget_failures(data_root: str) -> int:
    """Let every camera Blender failed on be rendered again at the next run (after the model or Blender was fixed)."""
    root, n = cache_root(data_root), 0
    for key in (os.listdir(root) if os.path.isdir(root) else []):
        path = os.path.join(root, key, "failed.json")
        if os.path.exists(path):
            os.remove(path)
            n += 1
    return n


def plan(conn, pid: int, resolution=(1152, 2048)) -> List[Dict]:
    """One item per shot at a 3D place: its camera (model coordinates), the character box, the time/weather and the cache key."""
    shots = shots_at_3d_places(conn, pid)
    aspect = resolution[0] / resolution[1]
    cams = plate_camera.plan_cameras(
        shots, lambda s: ((spot_for(s["entry"], s["data"])["at"]), spot_for(s["entry"], s["data"])["facing"]),
        lambda s: _height(conn, pid, s["data"]), aspect)
    out = []
    for s in shots:
        cam = cams.get(s["id"])
        if cam is None:
            continue
        env = plate_env.env_of(s["data"])
        sp = spot_for(s["entry"], s["data"])
        camera = dict(cam["camera"], model_coords=True, subject={"location": sp["at"], "height_m": _height(conn, pid, s["data"])})
        out.append({"scene_id": s["id"], "idx": s["idx"], "place": s["place"]["name"], "entry": s["entry"], "camera": camera, "env": env,
                    "subject_box": cam["subject_box"], "distance_m": cam["distance_m"], "spot": sp["name"],
                    "key": cache_key(s["entry"], camera, env, resolution), "weather_problem": plate_env.weather_of(s["data"])[1],
                    "spot_problem": spot_problem(s["entry"], s["data"])})
    return out


def _cached(root: str, key: str) -> Optional[Dict]:
    meta = os.path.join(root, key, "meta.json")
    try:
        with open(meta, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError):
        return None
    return rec if all(os.path.exists(rec.get(k, "")) for k in ("plate", "raw")) else None


def ensure_plates(conn, pid: int, data_dir: str, data_root: str, resolution=(1152, 2048), blender: Optional[str] = None,
                  render: Callable = plates3d.render, log: Callable[[str], None] = lambda m: None) -> Dict[str, Dict]:
    """Every shot at a 3D place gets its plate (from the cache, else rendered — one Blender run per model + time/weather, cameras
    together), finished (sky, fog, grade) and written to the project's index. Returns the index.
    A camera Blender does not return is marked failed (failed.json + diag + log) and NOT rendered again at every autopilot tick; the
    index says so, and the shot draws a normal picture instead of waiting for a plate that will not come (forget_failures = retry)."""
    from . import diag
    items = plan(conn, pid, resolution)
    root = cache_root(data_root)
    missing: Dict[tuple, List[Dict]] = {}
    for it in items:
        if _cached(root, it["key"]) is None and _failed(root, it["key"]) is None:
            missing.setdefault((it["entry"]["sha256"], plate_env.key(it["env"])), []).append(it)
    for group in missing.values():
        first = group[0]
        benv = plate_env.blender_env(first["env"], first["entry"].get("sun_azimuth", 250.0))
        cams = []
        seen = set()
        for it in group:
            cam = dict(it["camera"], name=f"k{it['key']}")
            if cam["name"] not in seen:
                seen.add(cam["name"])
                cams.append(cam)
        out = plates3d.out_dir(data_root, first["place"])
        cfg = plates3d.plan(first["entry"]["path"], out, sky=benv["sky"], sun_elevation=benv["sun_elevation"],
                            sun_azimuth=benv["sun_azimuth"], resolution=resolution, samples=32, cameras=cams, only_cameras=True,
                            weather=benv["weather"], sky_extra=benv["sky_extra"], real_height_m=first["entry"].get("real_height_m"))
        log(f"Render nền 3D: {first['place']} · {plate_env.key(first['env'])} · {len(cams)} góc máy")
        manifest = render(cfg, blender or plates3d.find_blender(), timeout=1800)
        by_name = {p["name"]: p for p in manifest.get("plates", [])}
        for it in group:
            p = by_name.get(f"k{it['key']}")
            dest = os.path.join(root, it["key"])
            os.makedirs(dest, exist_ok=True)
            if p is None:
                why = (f"Blender không trả về góc máy của shot {it['idx']} ({first['place']}, {plate_env.key(first['env'])}) — shot này vẽ "
                       "ảnh thường (không ghép nền 3D); sửa mô hình/Blender rồi chạy lại với forget_failures")
                with open(os.path.join(dest, "failed.json"), "w", encoding="utf-8") as f:
                    json.dump({"reason": why, "manifest_error": manifest.get("error")}, f, ensure_ascii=False)
                diag.record(conn, "image", "warn", why, "plate_missing", project_id=pid, scene_id=it["scene_id"])
                log(why)
                continue
            rec = {"camera": p.get("camera"), "depth_range_m": p.get("depth_range_m"), "subject": p.get("subject")}
            for kind in ("file", "depth_file", "shadow_file"):
                if p.get(kind):
                    target = os.path.join(dest, {"file": "raw.png", "depth_file": "depth.png", "shadow_file": "shadow_raw.png"}[kind])
                    shutil.copyfile(os.path.join(manifest["out_dir"], p[kind]), target)
                    rec[{"file": "raw", "depth_file": "depth", "shadow_file": "shadow_raw"}[kind]] = target
            rec["plate"] = plate_env.finish_plate(rec["raw"], os.path.join(dest, "plate.png"), it["env"], seed=int(it["key"][:6], 16),
                                                  depth_path=rec.get("depth"), depth_range=rec.get("depth_range_m"))
            if rec.get("shadow_raw"):
                rec["shadow"] = plate_env.finish_plate(rec["shadow_raw"], os.path.join(dest, "shadow.png"), it["env"],
                                                       seed=int(it["key"][:6], 16), depth_path=rec.get("depth"),
                                                       depth_range=rec.get("depth_range_m"))
            with open(os.path.join(dest, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
    idx = {}
    for it in items:
        rec = _cached(root, it["key"])
        if rec is None:
            why = _failed(root, it["key"])
            if why:
                idx[str(it["scene_id"])] = {"key": it["key"], "failed": why, "place": it["place"]}
            continue
        idx[str(it["scene_id"])] = dict(rec, key=it["key"], env=it["env"], subject_box=it["subject_box"], distance_m=it["distance_m"],
                                        spot=it["spot"], place=it["place"], camera_plan=it["camera"])
    path = _index_path(data_dir, pid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return idx


# ---- the green-screen picture of a shot ----------------------------------------------------------------------------------------
_TIME_LIGHT = {"night": "night scene: dim cold blue moonlight, darker exposure, deep shadows",
               "dusk": "warm low golden-orange sunset light", "dawn": "soft pink low morning light", "day": "clear daylight"}
_WEATHER_ON_BODY = {"rain": "hair and clothes wet, raindrops on skin and clothes", "storm": "hair and clothes soaked, raindrops on them",
                    "snow": "a little snow on hair and shoulders, cold breath visible", "snowfall": "snow on hair and shoulders, cold breath visible",
                    "ice": "frost on the clothes, cold breath visible", "sandstorm": "dust on clothes and skin, squinting against the wind"}


def light_words(rec: Dict, sun_azimuth: float) -> str:
    """Where the sun/moon comes from, seen from this camera (the render's own light: tools/render_plates.py points the sun from
    azimuth a toward (cos a, sin a) on the ground plane)."""
    import math
    cam = (rec.get("camera_plan") or {})
    loc, aim = cam.get("location"), cam.get("look_at")
    if not loc or not aim:
        return ""
    fx, fy = aim[0] - loc[0], aim[1] - loc[1]
    n = math.hypot(fx, fy) or 1.0
    fx, fy = fx / n, fy / n
    lx, ly = math.cos(math.radians(sun_azimuth)), math.sin(math.radians(sun_azimuth))
    ahead, side = lx * fx + ly * fy, lx * fy - ly * fx
    where = "from behind them (rim light on hair and shoulders)" if ahead > 0.35 else "from the front" if ahead < -0.35 else ""
    lr = "from the right of the frame" if side > 0.3 else "from the left of the frame" if side < -0.3 else ""
    return "Main light " + " and ".join(w for w in (where, lr) if w) + "." if (where or lr) else ""


def green_prompt(data: Dict, rec: Dict, sun_azimuth: float = 250.0) -> str:
    """What is added to a shot's picture prompt when the place comes from its 3D plate: the character alone on flat green, framed and
    lit exactly as the plate's camera and light (so the composite needs no guessing)."""
    cam = rec.get("camera_plan") or {}
    env = rec.get("env") or {"time": "day", "weather": "clear"}
    x0, y0, x1, y1 = rec.get("subject_box") or (0.4, 0.1, 0.6, 0.9)
    height = (cam.get("location") or [0, 0, 1.5])[2] - ((cam.get("subject") or {}).get("location") or [0, 0, 0])[2]
    where = (f"head top at about {max(y0, 0) * 100:.0f}% from the top of the frame, "
             + (f"feet at {y1 * 100:.0f}% from the top (whole body visible)" if y1 <= 1.0 else "body cut by the bottom of the frame")
             + f", body centred at {((x0 + x1) / 2) * 100:.0f}% from the left")
    parts = [f"Camera: {cam.get('lens', 35):g} mm lens, {height:.1f} m above the ground, the character {rec.get('distance_m', 3):.1f} m away; "
             f"{where}.", f"Light: {_TIME_LIGHT.get(env['time'], '')}. {light_words(rec, sun_azimuth)}".strip()]
    if env["weather"] in _WEATHER_ON_BODY:
        parts.append(f"Weather on the character: {_WEATHER_ON_BODY[env['weather']]}.")
    parts.append("BACKGROUND: a perfectly flat, uniform pure chroma-key green (#00FF00) studio backdrop filling everything behind the "
                 "character — no floor, no shadow on the backdrop, no gradient, no objects, no green light on the character. Crisp clean "
                 "hair edges. The place is NOT drawn: it is added afterwards.")
    return " ".join(p for p in parts if p)


def needs_plate(conn, pid: int, data: Dict) -> bool:
    """The shot's place gives a plate: a registered 3D model (tier 1) or a tagged in-game photo (tier 2)."""
    place = assets.scene_location(conn, pid, data)
    return bool(place and (model3d(conn, place["id"]) or photo_for(place, data)))


def without_place(data: Dict) -> Dict:
    """Shot data for the green picture: no place pictures / words go to the image model (the plate is the place)."""
    return {k: v for k, v in data.items() if k not in ("location", "location_asset", "layout")}


def _qc_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "plates", "video_qc.json")


def video_qc(data_dir: str, pid: int) -> Dict[str, Dict]:
    try:
        with open(_qc_path(data_dir, pid), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def record_video_qc(data_dir: str, pid: int, scene_id: int, job_id: int, result: Dict, mode: str) -> None:
    store = video_qc(data_dir, pid)
    store[str(scene_id)] = {"job_id": job_id, "score": result.get("score"), "ok": result.get("ok"), "mode": mode,
                            "frames": result.get("frames", [])[:30], "fallback": bool(result.get("fallback"))}
    os.makedirs(os.path.dirname(_qc_path(data_dir, pid)), exist_ok=True)
    with open(_qc_path(data_dir, pid), "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)


def green_path(data_dir: str, pid: int, image_job_id: int) -> str:
    return os.path.join(data_dir, str(pid), "images", f"job_{image_job_id}_green.png")


def mask_path(data_dir: str, pid: int, image_job_id: int) -> str:
    return os.path.join(data_dir, str(pid), "images", f"job_{image_job_id}_mask.png")


def propose_spots(probe: Dict, anchor: Optional[List[float]] = None, min_area_m2: float = 20.0, limit: int = 6,
                  ignore_below_m: Optional[float] = None) -> Dict[str, Dict]:
    """Named spots from a floor probe (tools/render_plates.py probe): the biggest flat areas, each standing at its centre and facing
    AWAY from the landmark (anchor) — the camera stands where the character looks, so the landmark is behind them in the frame.
    Names say the height (`level_25_9_a`); the person renames them in the dashboard. Terrain far below the landmark is skipped."""
    import math
    out: Dict[str, Dict] = {}
    for a in probe.get("areas") or []:
        if a["area_m2"] < min_area_m2 or len(out) >= limit:
            continue
        x, y, z = a["centre"]
        if ignore_below_m is not None and z < ignore_below_m:
            continue
        facing = 0.0
        if anchor:
            dx, dy = x - anchor[0], y - anchor[1]
            facing = round(math.degrees(math.atan2(dx, dy)), 1) if (dx or dy) else 0.0
        base = f"level_{z:.1f}".replace(".", "_").replace("-", "m")
        name = base
        n = 0
        while name in out:
            n += 1
            name = f"{base}_{chr(96 + n)}"
        out[name] = {"at": [round(x, 3), round(y, 3), round(z, 3)], "facing": facing, "label": f"mặt phẳng cao {z:.1f} m ({a['area_m2']:.0f} m²)"}
    return out


# ---- tier 2: an in-game photo of the library as the plate (no 3D model for the place) -----------------------------------------
PHOTO_ROLES = {"low": "low_angle", "high": "high_angle", "overhead": "high_angle"}
ZOOM = {"EWS": 1.0, "WS": 1.0, "GAME_TPS": 1.0, "MLS": 1.2, "MS": 1.4, "MCU": 1.7, "CU": 2.0, "ECU": 2.4}


def photo_for(place: Dict, data: Dict) -> Optional[Dict]:
    """The place's approved in-game background photo for this shot's camera kind (eye level unless the shot is low / high); a map
    screenshot from above is never a plate (R7)."""
    want = PHOTO_ROLES.get(str(data.get("angle") or "").lower(), "eye_level")
    pics = [i for i in place.get("images") or [] if i.get("role") in ("eye_level", "low_angle", "high_angle")]
    pick = next((i for i in pics if i["role"] == want), None) or next((i for i in pics if i["role"] == "eye_level"), None)
    return pick


def photo_plate(photo_path: str, out_path: str, data: Dict, env: Dict, resolution=(1152, 2048)) -> str:
    """Crop the photo to the frame (9:16 from a 16:9 screenshot keeps the middle), closer for closer shots, graded for the time and
    weather. No depth: no fog by distance, no occlusion; no shadow pass (tier 2 is weaker than a 3D plate and says so)."""
    from PIL import Image
    w, h = resolution
    with Image.open(photo_path) as im:
        im = im.convert("RGB")
        zoom = ZOOM.get(plate_camera.size_of(data), 1.4)
        ch = im.height / zoom
        cw = min(im.width, ch * w / h)
        ch = cw * h / w
        cx, cy = im.width / 2, im.height * 0.55
        box = (int(max(0, cx - cw / 2)), int(max(0, min(im.height - ch, cy - ch / 2))),
               int(min(im.width, cx + cw / 2)), int(min(im.height, max(ch, cy + ch / 2))))
        crop = im.crop(box).resize((w, h), Image.LANCZOS)
    tmp = out_path + ".raw.png"
    crop.save(tmp)
    plate_env.finish_plate(tmp, out_path, env)
    os.remove(tmp)
    return out_path


def ensure_photo_plates(conn, pid: int, data_dir: str, resolution=(1152, 2048)) -> Dict[str, Dict]:
    """Tier 2 for the shots whose place has no 3D model but has a tagged in-game photo. Added to the project's index with
    "tier": 2 (the composite uses them the same way, without shadow / occlusion / distance fog)."""
    idx = index(data_dir, pid)
    added = {}
    for s in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        data = json.loads(s["data"] or "{}")
        place = assets.scene_location(conn, pid, data)
        if place is None or model3d(conn, place["id"]):
            continue
        photo = photo_for(place, data)
        if photo is None:
            continue
        env = plate_env.env_of(data)
        key = hashlib.sha1(json.dumps({"photo": photo["path"], "size": plate_camera.size_of(data), "env": env, "res": list(resolution)},
                                      sort_keys=True).encode()).hexdigest()[:20]
        out = os.path.join(data_dir, str(pid), "plates", f"photo_{key}.png")
        if not os.path.exists(out):
            os.makedirs(os.path.dirname(out), exist_ok=True)
            photo_plate(photo["path"], out, data, env, resolution)
        frame = plate_camera.camera_for(data, (0.0, 0.0, 0.0), 0.0, _height(conn, pid, data), resolution[0] / resolution[1])
        added[str(s["id"])] = {"plate": out, "tier": 2, "key": key, "env": env, "subject_box": frame["subject_box"],
                               "distance_m": frame["distance_m"], "place": place["name"], "photo": photo["path"],
                               "camera_plan": dict(frame["camera"], subject={"location": [0, 0, 0]})}
    if added:
        idx.update(added)
        path = _index_path(data_dir, pid)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=1)
    return added


def _font(px: int):
    """A font with Vietnamese marks for the drawings (Pillow's default has none), else the default."""
    from PIL import ImageFont
    for name in ("arial.ttf", "segoeui.ttf", "tahoma.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def top_view(conn, pid: int, out_png: str, size: int = 900) -> Dict:
    """V4 (dp.md Q7/Q9): the floor plan of a project's shots at their 3D places, seen from above — every spot, the character, and each
    shot's virtual camera (a triangle pointing where it looks, "shot · lens mm"). Two cameras on opposite sides of the same person in one
    scene are listed (the 180° line). Free, Pillow only. Returns {"path", "shots", "opposite": [(shot, shot)]}."""
    import math
    from PIL import Image, ImageDraw
    items = plan(conn, pid)
    if not items:
        raise LocationPackError("dự án chưa có shot nào ở bối cảnh có mô hình 3D")
    pts = []
    for it in items:                                  # the frame follows the cameras and the people (far spots would shrink them to a dot)
        pts += [it["camera"]["location"][:2], it["camera"]["subject"]["location"][:2]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 6.0) * 1.4
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    to_px = lambda x, y: (size / 2 + (x - cx) / span * size, size / 2 - (y - cy) / span * size)  # noqa: E731 - +y up
    img = Image.new("RGB", (size, size), (24, 26, 30))
    d = ImageDraw.Draw(img)
    font = _font(15)
    for name, sp in (items[0]["entry"].get("spots") or {}).items():
        x, y = to_px(*sp["at"][:2])
        if not (0 <= x <= size and 0 <= y <= size):
            continue
        d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(120, 120, 120))
        d.text((x + 8, y - 6), name, fill=(150, 150, 150), font=font)
    sides: Dict = {}
    for it in items:
        cam, subj = it["camera"]["location"], it["camera"]["subject"]["location"]
        sx, sy = to_px(*subj[:2])
        d.ellipse([sx - 7, sy - 7, sx + 7, sy + 7], fill=(250, 200, 40))
        px, py = to_px(*cam[:2])
        ang = math.atan2(sy - py, sx - px)
        tri = [(px + 14 * math.cos(ang), py + 14 * math.sin(ang)), (px + 8 * math.cos(ang + 2.4), py + 8 * math.sin(ang + 2.4)),
               (px + 8 * math.cos(ang - 2.4), py + 8 * math.sin(ang - 2.4))]
        d.polygon(tri, fill=(90, 170, 255))
        d.line([(px, py), (sx, sy)], fill=(60, 90, 130))
        d.text((px + 10, py + 6), f"shot {it['idx']} · {it['camera']['lens']:g} mm", fill=(200, 220, 255), font=font)
        side = (cam[0] - subj[0], cam[1] - subj[1])
        sides.setdefault(tuple(round(v, 1) for v in subj[:2]), []).append((it["idx"], side))
    opposite = []
    for shots_here in sides.values():
        for i, (a, va) in enumerate(shots_here):
            for b, vb in shots_here[i + 1:]:
                if va[0] * vb[0] + va[1] * vb[1] < 0:        # the two cameras look at the person from opposite half-planes
                    opposite.append((a, b))
    d.text((10, 10), f"Sơ đồ máy nhìn từ trên — vàng: nhân vật · xanh: máy ảo · xám: chỗ đứng · khung {span:.0f} m",
           fill=(230, 230, 230), font=font)
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    img.save(out_png)
    return {"path": out_png, "shots": len(items), "opposite": opposite}
