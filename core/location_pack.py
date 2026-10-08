"""Location pack (kế hoạch V4 mục 1): a place of the library with its 3D model registered once — spots where characters stand — so
every shot set there gets a background rendered from its own camera (pixel-true place), shared across projects through a cache.

Registry: the place's `assets.profile` JSON keeps `model3d` =
    {"path", "sha256", "real_height_m" (None = the model's own metres), "anchor": [x, y, z] of the landmark (model coordinates),
     "spots": {"plaza_front": {"at": [x, y, z], "facing": 0, "label": "..."}, ...}, "default_spot": "plaza_front",
     "sun_azimuth": 250, "notes": ""}
Shot fields the DP writes: `plate_spot` (a spot name; else the default), `weather`, scene `time`, and (S5.7, người dùng 29/09 — decided
per shot from the script, never a constant of the place) `plate_view` (the camera direction: what is behind the character) and
`practical_lights` (extra lights of a night shot) — core/plate_choice.py. A spot may be marked `"direction": "script"` (the covered yard of the
clock tower): it has no fixed direction, a shot there without `plate_view` gets no plate until the DP writes one.
Per-project index: <data>/<pid>/plates/index.json  (scene id -> the plate files of its camera + where the character goes).
Cache: <data root>/_plates3d/cache/<key>/ — key = model sha + camera + time/weather + size + script version: two projects with the
same camera render once.
"""
import hashlib
import json
import os
import re
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
                notes: str = "", light: Optional[Dict] = None) -> Dict:
    """Register (or update) the 3D model of a place. The other profile keys are kept. `light`: {"day": {sun_elevation, and sky keys
    such as view_transform / look / exposure / strength / sun_strength / sun_color}} — how this model looks like the game in daylight
    (2026-09-29, official FF export: Blender's default view washed it out); None keeps what the place had."""
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
    if light is None:
        light = (prof.get("model3d") or {}).get("light")
    prof["model3d"] = {"path": os.path.abspath(path), "sha256": _file_sha(path), "real_height_m": real_height_m, "anchor": anchor,
                       "spots": {k: {"at": [float(v) for v in sp["at"]], "facing": float(sp.get("facing", 0)),
                                     "label": sp.get("label", k),
                                     # 2026-09-29 surroundings: what the camera looks at from here (not the landmark) + a group name
                                     **({"view": [float(v) for v in sp["view"]]} if sp.get("view") else {}),
                                     **({"group": str(sp["group"])} if sp.get("group") else {}),
                                     # inside a house (29/09): lighting for its camera + a second view out through a door / window
                                     **({"indoor": dict(sp["indoor"])} if sp.get("indoor") else {}),
                                     **({"view_out": [float(v) for v in sp["view_out"]]} if sp.get("view_out") else {}),
                                     # S5.7 (người dùng 29/09): no fixed camera direction here — each shot's `plate_view` decides
                                     **({"direction": "script"} if sp.get("direction") == "script" else {})}
                           for k, sp in spots.items()},
                       "default_spot": default_spot if default_spot in spots else next(iter(spots)), "sun_azimuth": float(sun_azimuth),
                       "notes": notes, **({"light": light} if light else {})}
    old = (json.loads(row["profile"]) if row["profile"] else {}).get("model3d") or {}
    if old.get("landmark"):
        prof["model3d"]["landmark"] = old["landmark"]
    conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps(prof, ensure_ascii=False), asset_id))
    conn.commit()
    return prof["model3d"]


def set_script_view(conn, asset_id: int, spot_names: List[str], on: bool = True, landmark: Optional[str] = None) -> Dict:
    """S5.7: mark spots whose camera direction is chosen per shot from the script (`"direction": "script"` — a shot there without
    `plate_view` gets no plate and is reported), and optionally name the landmark in English for prompts ("the clock tower")."""
    row = conn.execute("SELECT profile FROM assets WHERE id=?", (asset_id,)).fetchone()
    prof = json.loads(row["profile"]) if row is not None and row["profile"] else {}
    entry = prof.get("model3d")
    if not isinstance(entry, dict):
        raise LocationPackError("bối cảnh này chưa gắn mô hình 3D")
    for name in spot_names:
        if name not in (entry.get("spots") or {}):
            raise LocationPackError(f"không có chỗ đứng '{name}' ({', '.join(entry.get('spots') or {})})")
        if on:
            entry["spots"][name]["direction"] = "script"
        else:
            entry["spots"][name].pop("direction", None)
    if landmark is not None:
        entry["landmark"] = landmark.strip() or None
    conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps(prof, ensure_ascii=False), asset_id))
    conn.commit()
    return entry


_STOP = {"khu", "vuc", "cho", "tai", "o", "va", "cua", "the", "a", "of", "and", "at", "in", "on", "dao", "quan", "su", "thap", "ho",
         "phia", "nhin", "canh", "tren", "duoi", "chan", "trong", "sau", "truoc", "ben", "voi", "mot", "cac"}
# The place's own name is dropped as a phrase, not word by word: "dong" stopped as a word also dropped "đông" (east) — "phòng ngủ tầng 2
# nhà lớn phía Đông" then stood in the square's 3-storey house (Khủng Long Đỏ, 06/10)
_PLACE_NAMES = re.compile(r"\b(thap )?dong ho\b")


def _words(text: str) -> set:
    folded = _PLACE_NAMES.sub(" ", assets.fold(text or ""))
    folded = re.sub(r"\b(?:tang|floor) (\d)\b", r"tang t\1", folded)   # "tầng 2" names the `_t2` spot (a 1-char "2" is dropped below)
    return {w for w in re.findall(r"[a-z0-9]+", folded) if len(w) >= 2 and w not in _STOP}


def auto_spot(entry: Dict, data: Dict) -> Optional[str]:
    """30/09 dry run on #8: every one of 33 shots stood on the default spot although the scenes said "khu nhà ở dưới chân tháp",
    "góc khuất gần khu nhà", "chiến trường…" (`plate_spot` is only written when the Director sees the spot list). A shot without
    `plate_spot`: the spot whose label shares the most words with the shot's place / text (≥ 1 meaningful word), else None.
    Indoor spots only when the shot says it is inside (trong nhà / inside / indoor / room / phòng).
    The scene's place words (`location` / `set`, the same on every shot of a script scene) are matched first, the shot's own words only
    when they match nothing — S5.5' 30/09: matching each shot's prompt put shots 20/21/23 of one conversation at the tower's foot and
    22/24 on the south-west meadow 150 m away."""
    spots = entry.get("spots") or {}
    blob = " ".join(str(data.get(k) or "") for k in ("location", "set", "text", "image_prompt", "blocking"))
    inside = bool(re.search(r"\b(trong nha|inside|indoor|interior|room|phong|living room|bedroom|kitchen)\b", assets.fold(blob)))

    def best_for(words):
        best, score = None, 0
        for name, sp in spots.items():
            if bool(sp.get("indoor")) != inside:
                continue
            head, _, rest = str(sp.get("label") or "").partition(" — ")    # "đồng cỏ tây nam — bậc thang, dãy nhà…": the head
            s = 2 * len(words & _words(f"{head} {name.replace('_', ' ')}")) + len(words & (_words(rest) - _words(head)))   # names it
            if s > score:
                best, score = name, s
        return best
    return best_for(_words(" ".join(str(data.get(k) or "") for k in ("location", "set")))) or best_for(_words(blob))


def spot_for(entry: Dict, data: Dict) -> Dict:
    spots = entry.get("spots") or {}
    name = data.get("plate_spot") if data.get("plate_spot") in spots else None
    name = name or auto_spot(entry, data) or entry.get("default_spot")
    sp = spots.get(name) or spots.get(entry.get("default_spot")) or next(iter(spots.values()))
    return dict(sp, name=name if name in spots else entry.get("default_spot"))


def spot_problem(entry: Dict, data: Dict) -> Optional[str]:
    """A `plate_spot` the place does not have falls back to a spot matched from the shot's words, else the default — said, never
    silent (CHUAN_XAY_DUNG rule 1)."""
    name = data.get("plate_spot")
    if name and name not in (entry.get("spots") or {}):
        guess = auto_spot(entry, data)
        return (f"chỗ đứng '{name}' không có ở bối cảnh này ({', '.join(entry.get('spots') or {})}) — dùng "
                + (f"'{guess}' (khớp chữ mô tả shot)" if guess else f"'{entry.get('default_spot')}'"))
    return None


SCRIPT_CHOICES = (
    "- `plate_view` (mọi shot ở nơi có mô hình 3D — hướng máy KHÔNG cố định theo chỗ đứng, chọn theo kịch bản): "
    "`{\"background\": \"landmark|away|left|right|scenery|spot:<tên chỗ đứng>|<số độ>\", \"why\": \"tiếng Việt\"}` = cái gì ở NỀN "
    "sau nhân vật: `landmark` máy nhìn về mốc (mốc ở nền), `away` quay lưng về mốc (không thấy mốc), `left`/`right` nhìn ngang, "
    "`scenery` hướng cảnh quan đã đăng ký của chỗ đứng (trong nhà: nhìn ra cửa). "
    "Suy từ kịch bản: trục diễn (giữ cùng phía trục với shot trước, trừ khi cố ý vượt trục), ai đứng đâu, người xem cần thấy gì "
    "ở nền (mốc để nhận ra nơi; bỏ mốc khi cần nền gọn cho cảm xúc). Chỗ đứng ghi \"bắt buộc\" mà thiếu `plate_view` → nền "
    "không render, ảnh shot phải chờ. Lập SƠ ĐỒ CẢNH trước (08/10): trục chính (nhân vật phía nào vật mốc gần, mốc nền phía nào), MỘT "
    "bên trục cho mọi góc ngang (đổi bên phải ghi \"vượt trục\" + lý do), shot ngược / nhìn thẳng mặt nhân vật → `away`, qua vai nhìn "
    "về mốc → `landmark`, xen hướng để hậu cảnh đổi theo góc — thiếu `plate_view` thì mọi shot rơi về một hướng mặc định (cùng một nền).\n"
    "- `practical_lights` (cảnh `night` — BẮT BUỘC quyết; ghi ở shot hoặc ở cảnh): `[]` = chỉ ánh trăng; hoặc tối đa 3 "
    "`{\"kind\": \"lamp|fire|screen|neon|torch|headlight|window\", \"where\": \"behind|behind_left|behind_right|left|right|"
    "front|front_left|front_right|above|background\", \"color\": \"warm|orange|cool|blue|white|red|green|purple|pink|#rrggbb\", "
    "\"why\": \"tiếng Việt\"}` — chỉ đèn mà kịch bản có lý do (đèn đường, lửa trại, màn hình điện thoại, đèn pin…); "
    "`where` nhìn từ máy.")


def director_block(conn, pid: int) -> str:
    """V4 GĐ4 (dp.md Q6): what the Director / DP must know to write `plate_spot`, `weather` for a project whose places have a
    registered 3D model (renders as reference pictures, place_render_refs) — the spots by name, the fixed weather / time names. Empty
    when the feature is off or no place of the project has a model. S14.9 (06/10): the green-screen version (flag location_plates,
    `plate_mode`) was removed."""
    from . import place_refs
    if not place_refs.enabled():
        return ""
    rows = []
    for a in assets.project_assets(conn, pid):
        entry = model3d(conn, a["id"]) if a.get("kind") == "location" else None
        if not entry:
            continue
        spots = "; ".join(f"`{k}` ({v.get('label') or k}{', trong nhà' if v.get('indoor') else ''}"
                          + (", **hướng máy tùy kịch bản — bắt buộc `plate_view`**" if v.get("direction") == "script" else "") + ")"
                          for k, v in (entry.get("spots") or {}).items())
        rows.append(f"- **{a['name']}**: chỗ đứng {spots} — mặc định `{entry.get('default_spot')}`")
    if not rows:
        return ""
    # 30/09: the renders are reference pictures — spot + time/weather matter, no plate_mode
    return ("# Bối cảnh có mô hình 3D (ảnh render đúng góc máy từng shot đi kèm làm tham chiếu cho model vẽ)\n" + "\n".join(rows) + "\n"
            "- `plate_spot`: chỗ đứng hợp với nơi của shot (quảng trường, khu nhà, trong nhà…) — không ghi thì code tự chọn theo chữ "
            "mô tả nơi của shot, không khớp thì dùng mặc định. Các shot của một đoạn nối tiếp nên đứng cùng chỗ.\n"
            f"- `weather` (shot hoặc cảnh): chỉ một trong {', '.join(plate_env.WEATHERS)}; `time` của cảnh: {', '.join(plate_env.TIMES)}.\n"
            + SCRIPT_CHOICES)



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


def day_light(benv: Dict, entry: Dict) -> Dict:
    """A clear-day render (sky A) of a place with its own `light.day` takes that light (sun height, view, exposure …) over the generic
    day values; night / dusk / bad weather (sky C, painted after) keep plate_env's light."""
    day = (entry.get("light") or {}).get("day")
    if not day or benv.get("sky") != "A":
        return benv
    out = dict(benv, sky_extra=dict(benv.get("sky_extra") or {}, **{k: v for k, v in day.items() if k != "sun_elevation"}))
    if "sun_elevation" in day:
        out["sun_elevation"] = day["sun_elevation"]
    return out


def cache_root(data_root: str) -> str:
    return os.path.join(data_root, "_plates3d", "cache")


def cache_key(entry: Dict, camera: Dict, env: Dict, resolution) -> str:
    cam = {k: v for k, v in camera.items() if k != "name"}          # the camera, not which shot of which project asked for it
    parts = {"model": entry["sha256"], "h": entry.get("real_height_m"), "cam": cam, "env": env, "res": list(resolution), "v": SCRIPT_VERSION}
    if entry.get("light"):                                          # only when set: the keys of places without it stay the same
        parts["light"] = entry["light"]
    blob = json.dumps(parts, sort_keys=True)
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
    if rec and rec.get("depth") and rec.get("depth_exposure") is None:
        return None             # lỗi 14 (08/10): finished before the depth fix (may be flat) — "missing" so ensure_plates finishes it again
    if rec and rec.get("problem"):
        return None             # a flat / emptied plate is never sent as the place
    return rec if rec and os.path.exists(rec.get("plate", "")) else None


def plate_needs(data_dir: str, pid: int, scene_id: int) -> Optional[str]:
    """S5.7: what the shot's plate is waiting for from the script (a camera direction at a script-view spot), else None."""
    return (index(data_dir, pid).get(str(scene_id)) or {}).get("needs")


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
    """One item per shot at a 3D place: its camera (model coordinates), the character box, the time/weather and the cache key.
    S5.7: the camera direction comes from the shot's `plate_view` and the extra lights from `practical_lights` (core/plate_choice) —
    both are part of the camera, so of the cache key: a changed direction or light is a new plate. `needs` = the plate must not be
    rendered yet (a script-view spot without a direction); `view_problem` / `light_problem` = reported, rendered anyway."""
    from . import plate_choice
    shots = shots_at_3d_places(conn, pid)
    aspect = resolution[0] / resolution[1]
    views = {s["id"]: plate_choice.view_of(s["entry"], spot_for(s["entry"], s["data"]), s["data"]) for s in shots}
    cams = plate_camera.plan_cameras(
        shots, lambda s: ((spot_for(s["entry"], s["data"])["at"]), views[s["id"]]["facing_deg"]),
        lambda s: _height(conn, pid, s["data"]), aspect)
    out = []
    for s in shots:
        cam = cams.get(s["id"])
        if cam is None:
            continue
        env = plate_env.env_of(s["data"])
        sp = spot_for(s["entry"], s["data"])
        height = _height(conn, pid, s["data"])
        view = views[s["id"]]
        if cam.get("shared_with"):                      # one camera set-up = one position: a different direction is not taken silently
            first = next((views[o["id"]] for o in shots if f"shot_{o['id']}" == cam["shared_with"]), None)
            if first is not None and first["background_deg"] != view["background_deg"]:
                view = dict(first, problem=(f"shot cùng camera_setup với {cam['shared_with']} nên dùng hướng máy của shot đó "
                                            f"({first['background_deg']:g}°), không phải hướng shot này ghi ({view['background_deg']:g}°)"),
                            needs=first["needs"])
        lit = plate_choice.lights_of(s["data"], env)
        camera = dict(cam["camera"], model_coords=True, subject={"location": sp["at"], "height_m": height})
        if lit["lights"]:
            camera["lights"] = plate_choice.light_rigs(lit["lights"], sp["at"], camera["location"], height)
            env = dict(env, practical=True)             # plate_env.grade: a lit night keeps its lamps (the character gets the same)
        out.append({"scene_id": s["id"], "idx": s["idx"], "place": s["place"]["name"], "entry": s["entry"], "camera": camera, "env": env,
                    "subject_box": cam["subject_box"], "distance_m": cam["distance_m"], "spot": sp["name"],
                    "key": cache_key(s["entry"], camera, env, resolution), "weather_problem": plate_env.weather_of(s["data"])[1],
                    "spot_problem": spot_problem(s["entry"], s["data"]), "view": view, "view_problem": view["problem"],
                    "needs": view["needs"], "lights": lit["lights"], "lights_decided": lit["decided"],
                    "light_problem": lit["problem"]})
    return out


def layout_words(it: Dict) -> str:
    """S5.7: the chosen direction + light of a planned shot in Vietnamese, for the person (plan command, diag, index)."""
    from . import plate_choice
    v = it["view"]
    return (f"{it['spot']} · {v['words_vi']} (nền {v['background_deg']:g}°)" + (f" — lý do: {v['why']}" if v.get("why") else "")
            + f" · {it['env']['time']}/{it['env']['weather']} · " + plate_choice.light_words_vi(it["lights"], it["lights_decided"]))


def _cached(root: str, key: str) -> Optional[Dict]:
    meta = os.path.join(root, key, "meta.json")
    try:
        with open(meta, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError):
        return None
    return rec if all(os.path.exists(rec.get(k, "")) for k in ("plate", "raw")) else None


def _legacy_depth_exposure(benv: Dict, it: Dict) -> float:
    """The exposure (stops) a depth picture rendered BEFORE the 08/10 fix carries: the sky's exposure (+ a room's extra)."""
    exp = float((benv.get("sky_extra") or {}).get("exposure", -0.5))
    indoor = (it.get("camera") or {}).get("indoor")
    if indoor:
        exp += float(indoor.get("exposure", 1.5))
    return exp


def _finish(rec: Dict, dest: str, it: Dict) -> None:
    """Sky, fog by distance, grade -> plate.png (+ shadow.png); then the flat-plate check (`problem`, lỗi 14)."""
    seed = int(it["key"][:6], 16)
    rec["plate"] = plate_env.finish_plate(rec["raw"], os.path.join(dest, "plate.png"), it["env"], seed=seed,
                                          depth_path=rec.get("depth"), depth_range=rec.get("depth_range_m"),
                                          depth_exposure=rec.get("depth_exposure") or 0.0)
    if rec.get("shadow_raw"):
        rec["shadow"] = plate_env.finish_plate(rec["shadow_raw"], os.path.join(dest, "shadow.png"), it["env"], seed=seed,
                                               depth_path=rec.get("depth"), depth_range=rec.get("depth_range_m"),
                                               depth_exposure=rec.get("depth_exposure") or 0.0)
    rec["problem"] = plate_env.plate_problem(rec["plate"], rec.get("raw"))


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
        if it.get("needs"):
            log(f"Shot {it['idx']}: {it['needs']}")
            continue                                      # S5.7: no direction for a script-view spot — never a default plate
        if _cached(root, it["key"]) is None and _failed(root, it["key"]) is None:
            missing.setdefault((it["entry"]["sha256"], plate_env.key(it["env"])), []).append(it)
    for group in missing.values():
        first = group[0]
        benv = day_light(plate_env.blender_env(first["env"], first["entry"].get("sun_azimuth", 250.0)), first["entry"])
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
        cfg["owner"] = f"dự án #{pid}"                    # the Blender lock / Dashboard say which project holds this computer's Blender
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
            rec["depth_exposure"] = (float(p["depth_exposure"]) if p.get("depth_exposure") is not None
                                     else _legacy_depth_exposure(benv, it))
            _finish(rec, dest, it)
            with open(os.path.join(dest, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
    before = index(data_dir, pid)
    idx = {}
    for it in items:
        # KLD-6: the size the record was made at (stale_plates judges it at that size) + the spot the shot stood on before a move
        # (move_report lists the fields still naming it, also after this new render)
        extra = {"res": [int(v) for v in resolution]}
        old = before.get(str(it["scene_id"])) or {}
        moved = old.get("spot") if old.get("spot") and old.get("spot") != it["spot"] else old.get("moved_from")
        if moved and moved != it["spot"]:
            extra["moved_from"] = moved
        if it.get("needs"):
            idx[str(it["scene_id"])] = {"key": it["key"], "needs": it["needs"], "place": it["place"], "spot": it["spot"], **extra}
            continue
        rec = _cached(root, it["key"])
        if rec is None:
            why = _failed(root, it["key"])
            if why:
                idx[str(it["scene_id"])] = {"key": it["key"], "failed": why, "place": it["place"], "spot": it["spot"], **extra}
            continue
        if rec.get("depth") and rec.get("depth_exposure") is None:
            # lỗi 14 (08/10): a plate finished before the depth fix read its depth wrongly — finished again from the same render (0 USD)
            benv = day_light(plate_env.blender_env(it["env"], it["entry"].get("sun_azimuth", 250.0)), it["entry"])
            rec["depth_exposure"] = _legacy_depth_exposure(benv, it)
            _finish(rec, os.path.join(root, it["key"]), it)
            with open(os.path.join(root, it["key"], "meta.json"), "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
            log(f"Shot {it['idx']}: nền 3D làm lại phần sương/màu (đọc độ sâu đúng) — 0 USD")
        bad = rec["problem"] if "problem" in rec else plate_env.plate_problem(rec["plate"], rec.get("raw"))
        if bad:                                           # never sent as "the place": the shot draws without this background
            why = f"Shot {it['idx']} ({it['place']}, {plate_env.key(it['env'])}): {bad} — không gửi nền này; xem {rec['plate']}"
            diag.record(conn, "image", "error", why, "plate_flat", project_id=pid, scene_id=it["scene_id"])
            log(why)
            idx[str(it["scene_id"])] = {"key": it["key"], "failed": why, "place": it["place"], "spot": it["spot"], **extra}
            continue
        idx[str(it["scene_id"])] = dict(rec, key=it["key"], env=it["env"], subject_box=it["subject_box"], distance_m=it["distance_m"],
                                        spot=it["spot"], place=it["place"], camera_plan=it["camera"], view=it["view"],
                                        lights=it["lights"], lights_decided=it["lights_decided"], layout_vi=layout_words(it), **extra)
    path = _index_path(data_dir, pid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return idx


# ---- KLD-6 (người dùng duyệt 08/10): the background in plates/index.json against the plan, on EVERY path ----
# Khủng Long Đỏ #22: scenes 254–256 moved to `bac_thang_giua`; only the autopilot compared plan() with the index, the hand redraw drew
# on the OLD render and the old words ("flat stone plaza, low red-roof house") beat it — 1,80 USD.
def stale_plates(conn, pid: int, data_dir: str, resolution=(1152, 2048)) -> Dict[int, Dict]:
    """{scene_id: {idx, old_spot, new_spot, why}} for every shot whose index record was made for another camera (spot, direction, lens,
    light, time/weather, model…) than plan() gives now — the record's background is not this shot's any more. A record is judged at
    the size it was made at (`res`, else `resolution`); a shot never rendered is missing, not stale; a record of a shot no longer at a
    3D place is stale too (its old render would still be sent)."""
    idx = index(data_dir, pid)
    if not idx:
        return {}
    plans: Dict[tuple, Dict[int, Dict]] = {}

    def planned(res) -> Dict[int, Dict]:
        res = tuple(int(v) for v in res)
        if res not in plans:
            plans[res] = {it["scene_id"]: it for it in plan(conn, pid, res)}
        return plans[res]
    out: Dict[int, Dict] = {}
    for sid, rec in idx.items():
        try:
            scene_id = int(sid)
        except ValueError:
            continue
        res = rec.get("res") or resolution
        if rec.get("res") and abs(res[0] / res[1] - resolution[0] / resolution[1]) > 0.01:
            it = planned(resolution).get(scene_id)          # the frame's shape changed: the record's camera cannot be this shot's
            why = "khung hình của dự án đã đổi"
        else:
            it = planned(res).get(scene_id)
            why = None
        if it is not None and it["key"] == rec.get("key") and why is None:
            continue
        old, new = rec.get("spot"), (it or {}).get("spot")
        if it is None:
            why = why or "shot không còn ở bối cảnh có mô hình 3D"
        elif why is None:
            why = f"chỗ đứng đổi {old} → {new}" if old and new and old != new else "hướng máy / cỡ cảnh / đèn / thời tiết của shot đã đổi"
        out[scene_id] = {"idx": (it or {}).get("idx"), "old_spot": old, "new_spot": new,
                         "why": f"nền 3D đã cũ ({why}) — dựng lại nền (0 USD, Blender) trước khi gửi"}
    return out


MOVE_FIELDS = ("location", "image_prompt", "blocking", "spatial_state", "action")
# the place words of a spot label, in the label's Vietnamese and the prompts' English (folded, regex): a field naming a place word of
# ANOTHER spot that the new spot does not have still describes the old place (#22: "plaza" = quảng trường, "red-roof" = mái đỏ)
_PLACE_TERMS = {
    "quảng trường": (r"quang truong", r"plaza", r"town square"),
    "mái đỏ": (r"mai do", r"red[- ]?roof"),
    "đồng cỏ": (r"dong co", r"meadow", r"grass", r"lawn"),
    "cầu thang": (r"cau thang", r"bac thang", r"stair", r"\bsteps\b"),
    "tháp": (r"\bthap\b", r"tower"),
    "đồi": (r"tren doi", r"doi phia", r"\bhills?\b", r"hillside"),
    "cao tốc": (r"cao toc", r"highway"),
    "bãi xe": (r"bai xe", r"parking", r"\bvans?\b", r"\bcars?\b"),
    "dừa": (r"rang dua", r"cay dua", r"\bpalms?\b", r"coconut"),
    "trạm gác": (r"tram gac", r"guard ?(post|tower|house)", r"watchtower"),
    "biển quảng cáo": (r"bien quang cao", r"billboard"),
    "trong nhà": (r"trong nha", r"\binside\b", r"\bindoors?\b", r"interior"),
    "phòng ngủ": (r"phong ngu", r"bedroom"),
    "phòng khách": (r"phong khach", r"living room"),
    "bếp": (r"\bbep\b", r"kitchen"),
    "nhà 3 tầng": (r"nha 3 tang", r"three[- ]stor", r"3[- ]stor"),
    "hai tầng": (r"hai tang", r"two[- ]stor", r"2[- ]stor"),
}
_NEGATION = re.compile(r"\b(?:do not|don't|never|without|avoid|không|đừng|chớ)\b[^.;:\n]*", re.IGNORECASE)
_NUMBER_WORDS = {"mot", "hai", "ba", "bon", "nam", "sau", "bay", "tam", "chin", "muoi"}   # "Hai người" is not "hai tầng"


def _terms(text: str) -> set:
    folded = assets.fold(_NEGATION.sub(" ", text or ""))
    return {name for name, pats in _PLACE_TERMS.items() if any(re.search(p, folded) for p in pats)}


def _label_words(text: str) -> set:
    """The words of a Vietnamese label WITH their marks ("đông" east ≠ "động" in "động tác"), without stop words and numbers."""
    words = re.findall(r"\w+", _NEGATION.sub(" ", (text or "").lower()))
    return {w for w in words if len(w) >= 2 and not w.isdigit() and assets.fold(w) not in _STOP | _NUMBER_WORDS}


def spot_mentions(entry: Dict, data: Dict, old_spot: str, new_spot: str, motion: str = "") -> Dict[str, List[str]]:
    """KLD-6, checklist feedback_scene_location_change_checklist: after a shot moves from `old_spot` to `new_spot`, the fields that
    still name the old place — {field: [words]} for location / image_prompt / blocking / spatial_state / action (+ `motion_prompt`).
    Two signals: a Vietnamese word of the old spot's label the new label lacks ("lớn", "đông"), and a place word (both languages) of
    any spot of this place the new spot does not have ("plaza", "red-roof"). Negated clauses ("Do NOT add … plaza") are not read.
    Only a warning: the person reads the words and decides."""
    spots = entry.get("spots") or {}
    old_label = str((spots.get(old_spot) or {}).get("label") or "")
    new_label = str((spots.get(new_spot) or {}).get("label") or "")
    old_words = _label_words(old_label) - _label_words(new_label)
    place_terms = set().union(*[_terms(f"{sp.get('label') or ''} {name.replace('_', ' ')}") for name, sp in spots.items()]) if spots else set()
    other_terms = place_terms - _terms(f"{new_label} {new_spot.replace('_', ' ')}")
    texts = {k: str(data.get(k) or "") for k in MOVE_FIELDS}
    if motion:
        texts["motion_prompt"] = motion
    out: Dict[str, List[str]] = {}
    for field, text in texts.items():
        hits = sorted(_label_words(text) & old_words) + sorted(_terms(text) & other_terms)
        if hits:
            out[field] = hits
    return out


def _motion_text(conn, scene_id: int) -> str:
    try:
        row = conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    except Exception:  # noqa: BLE001 - old test databases without the table
        return ""
    return str(row["motion_prompt"] or "") if row else ""


def move_report(conn, pid: int, data_dir: str, resolution=(1152, 2048)) -> List[Dict]:
    """[{scene_id, idx, old_spot, new_spot, stale, fields}] — shots that moved to another spot (a record still on the old spot =
    `stale`, or a new render that remembers `moved_from`) whose fields still name the old place. Empty once the fields are fixed."""
    idx = index(data_dir, pid)
    if not idx:
        return []
    stale = stale_plates(conn, pid, data_dir, resolution)
    out = []
    for it in plan(conn, pid, resolution):
        rec = idx.get(str(it["scene_id"])) or {}
        s = stale.get(it["scene_id"])
        old = s["old_spot"] if s and s.get("old_spot") and s["old_spot"] != it["spot"] else rec.get("moved_from")
        if not old or old == it["spot"]:
            continue
        data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (it["scene_id"],)).fetchone()["data"] or "{}")
        fields = spot_mentions(it["entry"], data, old, it["spot"], _motion_text(conn, it["scene_id"]))
        if fields:
            out.append({"scene_id": it["scene_id"], "idx": it["idx"], "old_spot": old, "new_spot": it["spot"], "stale": bool(s),
                        "fields": fields})
    return out


def move_words(item: Dict) -> str:
    """One Vietnamese line of move_report for the person (Dashboard, diag, autopilot)."""
    fields = "; ".join(f"{k} ({', '.join(v)})" for k, v in item["fields"].items())
    return (f"đổi chỗ đứng {item['old_spot']} → {item['new_spot']} nhưng các trường còn nhắc chỗ cũ: {fields} — sửa đồng bộ "
            "location / image_prompt / blocking / spatial_state / action / motion prompt (chữ cũ thắng render 3D: #22 mất 1,80 USD)")


# ---- light of a 3D render (place_render_refs prompt sentence) ----
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


def script_sentence(conn, pid: int, data: Dict) -> str:
    """S5.7: for a picture drawn WITHOUT a plate at a place that has a 3D model (feature off, or the render failed): the camera
    direction and the extra lights the DP chose for this shot, in words — so the layout sentence of the place is read from the right
    side (is the landmark in the frame or behind the camera?). A default direction is not presented as a choice (nothing is said)."""
    from . import plate_choice
    try:
        place = assets.scene_location(conn, pid, data)
    except Exception:  # noqa: BLE001 - no library tables (old test data)
        return ""
    entry = model3d(conn, place["id"]) if place else None
    if not entry or not entry.get("spots"):
        return ""
    bits = []
    view = plate_choice.view_of(entry, spot_for(entry, data), data)
    if view["source"] == "script" and view["words_en"]:
        bits.append(f"Camera direction chosen for this shot: {view['words_en']}.")
    env = plate_env.env_of(data)
    lit = plate_choice.lights_of(data, env)
    light = plate_choice.light_sentence(lit["lights"], lit["decided"], env["time"])
    if light:
        bits.append(light)
    return " ".join(bits)


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
