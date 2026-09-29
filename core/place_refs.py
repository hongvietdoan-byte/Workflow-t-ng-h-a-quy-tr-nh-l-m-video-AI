"""3D renders of the real place as REFERENCE pictures for the image model (feature `place_render_refs`, người dùng 2026-09-29).

Why: green-screen compositing on 3D plates was dropped after trial #8 (no ground contact, light mismatch — `location_plates` off);
the model drawing the whole scene is what works (#7: the tower renders as references gave both the tower and the quality). But the
library holds only 6 pictures per place, so a shot whose camera none of them matches got the nearest picture or words, and the model
redrew the architecture (#8's stacked terraces). With a registered 3D model (location_pack) every shot can have a render taken from
ITS OWN camera — free (Blender), cached across projects — and the model draws the people into that exact place:

- `shot_ref`       the shot's render (the location-pack plate of the shot's camera: character spot, shot size, angle, lens) — it
                   replaces the library's eye-level / landmark picture of the place (the scene's establishing picture stays).
- `scene_render`   the widest shot's render of a script scene — first reference of the scene's establishing picture.
- `geometry_sentence`  real numbers from the 3D camera for the prompt: lens, camera height, distance, where the character's head and
                   feet fall in the frame, the horizon line, where the sun comes from — the people get the right size in the place.
- `background_match`   after the picture comes back: edge agreement between the picture and the render outside the character's box
                   (0..1) — said in the diagnostics (a low score = the model redrew the place); measured, never an automatic redraw.
- `ensure_async`   renders missing plates in a background thread (the Step 2 buttons have no automatic plates phase); the shot waits.

Only when `location_plates` is off (with it on, the green-screen path owns the plates)."""
import os
import sqlite3
import threading
from typing import Callable, Dict, List, Optional

from . import features

FEATURE = "place_render_refs"
ROLE = "place_render"
SIZE_ORDER = ("EWS", "WS", "GAME_TPS", "MLS", "MS", "MCU", "CU", "ECU")
LOW_MATCH = 0.35            # below this the model most likely redrew the place (calibrated on synthetic cases; to check on real runs)

_RUNNING: Dict[int, threading.Thread] = {}
_LOCK = threading.Lock()


def enabled() -> bool:
    return features.on(FEATURE) and not features.on("location_plates")


def wants_render(conn, pid: int, data: Dict) -> bool:
    """The shot is set at a place with a registered 3D model."""
    from . import assets, location_pack
    place = assets.scene_location(conn, pid, data)
    return bool(place and location_pack.model3d(conn, place["id"]))


def shot_ref(data_dir: str, pid: int, scene_id: int) -> Optional[Dict]:
    from . import location_pack
    rec = location_pack.plate_of(data_dir, pid, scene_id)
    if rec is None:
        return None
    return {"path": rec["plate"], "label": rec.get("place") or "the place", "role": ROLE, "_rec": rec}


def swap_in(refs: List[Dict], ref: Optional[Dict], limit: int) -> List[Dict]:
    """The render takes the place's slot: the library's own place pictures (location / landmark) go, the scene's establishing picture
    and everything else stay; the render sits right after the people. Over `limit`, the last pictures go first."""
    if ref is None:
        return refs
    from . import scene_establish
    keep = [r for r in refs if not (r.get("role") == "landmark" or (r.get("role") == "location" and r.get("label") != scene_establish.LABEL))]
    at = next((i for i, r in enumerate(keep) if r.get("role") in ("location", "previous_scene", "layout")), len(keep))
    out = keep[:at] + [{k: v for k, v in ref.items() if not k.startswith("_")}] + keep[at:]
    return out[:max(limit, 1)]


def geometry_sentence(rec: Dict, data: Dict, sun_azimuth: float = 250.0) -> str:
    """The shot's camera and scale in words, from the render (so the model puts the people at the right size in the exact place)."""
    from . import location_pack
    cam = rec.get("camera_plan") or {}
    info = rec.get("camera") or {}
    bits = []
    lens, height = cam.get("lens"), info.get("height_m")
    subject_z = ((cam.get("subject") or {}).get("location") or [0, 0, None])[2]
    if lens and height is not None and subject_z is not None:
        bits.append(f"{float(lens):g} mm lens, camera {float(height) - float(subject_z):.1f} m above the ground")
    if data.get("characters") and rec.get("subject_box"):
        x0, y0, x1, y1 = rec["subject_box"]
        where = (f"the main character stands {float(rec.get('distance_m') or 0):.1f} m from the camera, head top at about "
                 f"{max(y0, 0) * 100:.0f}% from the top of the frame, "
                 + (f"feet at about {y1 * 100:.0f}%" if y1 <= 1.0 else "body cut by the bottom of the frame")
                 + f", centred at {((x0 + x1) / 2) * 100:.0f}% from the left")
        bits.append(where)
    if info.get("horizon_y") is not None and 0.0 <= float(info["horizon_y"]) <= 1.0:
        bits.append(f"the horizon line at {float(info['horizon_y']) * 100:.0f}% from the top")
    light = location_pack.light_words(rec, sun_azimuth) if rec.get("camera_plan") else ""
    if not bits and not light:
        return ""
    head = "Camera and scale, measured on the 3D map of this place: " + "; ".join(bits) + "." if bits else ""
    return (head + (" " + light if light else "")).strip()


def scene_render(data_dir: str, pid: int, rows: List[Dict]) -> Optional[str]:
    """The widest shot's render among a script scene's shots (rows: [{id, data}])."""
    from . import location_pack
    best = None
    for r in rows:
        rec = location_pack.plate_of(data_dir, pid, r["id"])
        if rec is None:
            continue
        size = str(r["data"].get("shot_size") or r["data"].get("shot") or "").upper()
        rank = SIZE_ORDER.index(size) if size in SIZE_ORDER else len(SIZE_ORDER)
        if best is None or rank < best[0]:
            best = (rank, rec["plate"])
    return best[1] if best else None


def missing(conn, data_dir: str, pid: int, scene_id: int, data: Dict) -> bool:
    """The shot needs a render that is neither there nor failed (then it waits for `ensure_async`)."""
    from . import location_pack
    return (wants_render(conn, pid, data) and location_pack.plate_of(data_dir, pid, scene_id) is None
            and not location_pack.plate_failed(data_dir, pid, scene_id))


def _db_path(conn) -> Optional[str]:
    row = conn.execute("PRAGMA database_list").fetchone()
    path = row[2] if row else ""
    return path or None


def ensure_async(conn, pid: int, data_dir: str, resolution, log: Callable[[str], None] = lambda m: None,
                 run: Optional[Callable] = None) -> bool:
    """Render the project's missing plates in a background thread (one per project; Blender runs one at a time anyway). True when a
    thread is (now) running. `run(pid)` replaces the work (tests)."""
    from . import location_pack
    with _LOCK:
        t = _RUNNING.get(pid)
        if t is not None and t.is_alive():
            return True
        db = _db_path(conn) if run is None else None
        if run is None and not db:
            return False                                    # an in-memory database cannot be opened from another thread

        def work():
            if run is not None:
                return run(pid)
            c = sqlite3.connect(db, timeout=60)
            c.row_factory = sqlite3.Row
            try:
                location_pack.ensure_plates(c, pid, data_dir, os.path.dirname(os.path.abspath(data_dir)), resolution, log=log)
            except Exception as e:  # noqa: BLE001 - said, never raised into the picture runner
                log(f"Render 3D làm ảnh tham chiếu lỗi: {e}")
            finally:
                c.close()

        t = threading.Thread(target=work, name=f"place_refs_{pid}", daemon=True)
        _RUNNING[pid] = t
        t.start()
        return True


def resolution_of(proj) -> tuple:
    from . import formats
    size = formats.spec(formats.project_aspect(proj) or "9:16")["deepix"]
    w, h = (int(v) for v in str(size).lower().split("x"))
    return (w, h)


def background_match(image_path: str, plate_path: str, box: Optional[List[float]] = None, side: int = 384) -> Optional[float]:
    """Edge agreement (F1 of Canny edges, 2 px tolerance) between the drawn picture and the render, outside the character's box
    (widened 15 %). 1 = the same architecture in the same places; ~0.1 = unrelated. None when a file cannot be read."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    a, b = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE), cv2.imread(plate_path, cv2.IMREAD_GRAYSCALE)
    if a is None or b is None:
        return None
    h = int(round(side * b.shape[0] / b.shape[1]))
    a, b = cv2.resize(a, (side, h), interpolation=cv2.INTER_AREA), cv2.resize(b, (side, h), interpolation=cv2.INTER_AREA)
    ea = cv2.Canny(cv2.GaussianBlur(a, (5, 5), 0), 60, 160) > 0
    eb = cv2.Canny(cv2.GaussianBlur(b, (5, 5), 0), 60, 160) > 0
    mask = np.ones_like(ea, dtype=bool)
    if box:
        x0, y0, x1, y1 = box
        pw, ph = (x1 - x0) * 0.15, (y1 - y0) * 0.15
        c0, c1 = int(max(x0 - pw, 0) * side), int(min(x1 + pw, 1) * side)
        r0, r1 = int(max(y0 - ph, 0) * h), int(min(y1 + ph, 1) * h)
        mask[r0:r1, c0:c1] = False
    kernel = np.ones((5, 5), np.uint8)
    da = cv2.dilate(ea.astype(np.uint8), kernel) > 0
    db = cv2.dilate(eb.astype(np.uint8), kernel) > 0
    ea, eb = ea & mask, eb & mask
    if eb.sum() < 50:
        return None                                              # an empty render (sky / flat wall): nothing to compare
    precision = (ea & db).sum() / max(ea.sum(), 1)
    recall = (eb & da).sum() / max(eb.sum(), 1)
    return round(float(2 * precision * recall / max(precision + recall, 1e-6)), 3)


def match_note(score: Optional[float]) -> tuple:
    """(severity, words) for the diagnostics."""
    if score is None:
        return ("info", "không đo được độ khớp nền với render 3D")
    if score < LOW_MATCH:
        return ("warn", f"nền lệch render 3D (độ khớp đường nét {score:.2f} < {LOW_MATCH}) — model có thể đã vẽ lại kiến trúc")
    return ("info", f"nền khớp render 3D (độ khớp đường nét {score:.2f})")
