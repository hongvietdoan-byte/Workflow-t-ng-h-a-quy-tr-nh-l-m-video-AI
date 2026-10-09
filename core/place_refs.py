"""3D renders of the real place as REFERENCE pictures for the image model (feature `place_render_refs`, người dùng 2026-09-29).

Why: green-screen compositing on 3D plates was dropped after trial #8 (no ground contact, light mismatch);
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

S14.9 (06/10): the green-screen flag `location_plates` was removed from the code — this is the only user of the plates now."""
import json
import os
import sqlite3
import threading
from typing import Callable, Dict, List, Optional

from . import features

FEATURE = "place_render_refs"
ROLE = "place_render"
SIZE_ORDER = ("EWS", "WS", "GAME_TPS", "MLS", "MS", "MCU", "CU", "ECU")
LOW_MATCH = 0.35            # below this the model most likely redrew the place (calibrated on synthetic cases; to check on real runs)
# KLD-17 (duyệt 08/10): NOT calibrated on real runs — on #22 the number disagreed with the person (550–552 judged wrong, 556–558 right,
# 531/532 partly wrong; see docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md). Until True, place_match only notes the number (info, never warn)
# and keeps each measure as a pair (place_match.json) that the person's review labels — the data to set LOW_MATCH from later.
CALIBRATED = False
PAIRS_FILE = "place_match.json"

_RUNNING: Dict[int, threading.Thread] = {}
_LOCK = threading.Lock()


# S5.5' (30/09, project #13, 0,31 USD): with the render attached AND scene words describing another place ("stone plaza, the clock tower
# in background", the generic "Setting: … tower stands on a wide flat stone plaza"), gpt-image-2.5 drew the words: 5/5 shots a paved plaza
# + tower, 0/5 the house and grass of the render (the establishing picture, with no such words, matched the render). The render must win
# over words, said before the scene text.
PRECEDENCE = ("The place is decided by the 3D render image of this shot, not by words: wherever the scene or setting text below describes "
              "the ground, buildings, tower, walls or layout differently from that render (for example a paved plaza where the render shows "
              "grass, or a tower the render does not show), draw what the render shows and ignore those words. Take from the text only the "
              "people, their actions, expressions and the light.")


def enabled() -> bool:
    return features.on(FEATURE)


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
    # KLD-6: `plate_key` rides into the job's sent_refs — the picture remembers which background it was drawn on
    return {"path": rec["plate"], "label": rec.get("place") or "the place", "role": ROLE, "_rec": rec,
            **({"plate_key": rec["key"]} if rec.get("key") else {})}


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
    # both heights in the model's own frame: the render's info["height_m"] is AFTER the model was lifted to stand on z = 0 (30/09 dry
    # run on #8: a close-up said "camera 4.9 m above the ground" — 3.3 m of lift too many)
    lens, height = cam.get("lens"), (cam.get("location") or [None, None, None])[2]
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


def scene_render_rec(data_dir: str, pid: int, rows: List[Dict]) -> Optional[Dict]:
    """The widest shot's plate record among a script scene's shots (rows: [{id, data}]), with its `scene_id` — KLD-18: the scene's
    establishing picture IS this render (same axis as the widest shot's camera)."""
    from . import location_pack
    best = None
    for r in rows:
        rec = location_pack.plate_of(data_dir, pid, r["id"])
        if rec is None:
            continue
        size = str(r["data"].get("shot_size") or r["data"].get("shot") or "").upper()
        rank = SIZE_ORDER.index(size) if size in SIZE_ORDER else len(SIZE_ORDER)
        if best is None or rank < best[0]:
            best = (rank, dict(rec, scene_id=r["id"]))
    return best[1] if best else None


def scene_render(data_dir: str, pid: int, rows: List[Dict]) -> Optional[str]:
    """The widest shot's render among a script scene's shots (rows: [{id, data}])."""
    rec = scene_render_rec(data_dir, pid, rows)
    return rec["plate"] if rec else None


def missing(conn, data_dir: str, pid: int, scene_id: int, data: Dict) -> bool:
    """The shot needs a render that is neither there nor failed (then it waits for `ensure_async`). F2: a render whose same-axis wide
    view was never made (index records before 09/10) is missing too — the wide is rendered (Blender, 0 USD) before the picture goes."""
    from . import location_pack
    if not wants_render(conn, pid, data):
        return False
    rec = location_pack.plate_of(data_dir, pid, scene_id)
    if rec is not None:
        wide = rec.get("wide") or {}
        return not rec.get("wide_failed") and not (wide.get("plate") and os.path.exists(wide["plate"]))
    if location_pack.plate_retry_due(data_dir, pid, scene_id):
        return True                                  # phiên sửa F2: a temporary Blender failure, its retry time has come
    return not location_pack.plate_failed(data_dir, pid, scene_id) and not location_pack.plate_needs(data_dir, pid, scene_id)


def broken(conn, data_dir: str, pid: int, scene_id: int, data: Dict) -> Optional[str]:
    """F2 (người dùng duyệt 09/10, #24 shot 4): the shot needs its 3D render but the render failed / is flat / the camera could not be
    placed — the reason (Vietnamese), else None. The picture is then HELD (never sent bare: job 579 went out without its render and
    the model guessed the well's height)."""
    from . import location_pack
    if not wants_render(conn, pid, data) or location_pack.plate_of(data_dir, pid, scene_id) is not None:
        return None
    if location_pack.plate_needs(data_dir, pid, scene_id):
        return None                                  # S5.7: said by its own wait (thiếu hướng máy)
    if location_pack.plate_retry_due(data_dir, pid, scene_id):
        return None                                  # rendered again by itself (missing)
    return location_pack.plate_failed(data_dir, pid, scene_id)


def retry_render(conn, data_dir: str, pid: int, scene_id: int) -> bool:
    """Phiên sửa F2 — Step 2 "↻ Render lại nền 3D" (0 USD): forget THIS shot's failed render (camera + wide); `missing` then asks
    for it and the picture runner starts ensure_async. True when the shot had a failure to forget."""
    from . import location_pack
    return location_pack.forget_shot(data_dir, pid, scene_id)


def held_broken(conn, data_dir: str, pid: int) -> List[tuple]:
    """[(scene_id, idx, reason)] of the queued pictures held because their 3D render failed (`broken`) — the Step 2 retry buttons."""
    out = []
    rows = conn.execute("SELECT DISTINCT s.id, s.idx, s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? "
                        "AND j.type='image_gen' AND j.state IN ('queued','retryable') ORDER BY s.idx", (pid,)).fetchall()
    for r in rows:
        try:
            why = broken(conn, data_dir, pid, r["id"], json.loads(r["data"] or "{}"))
        except Exception:  # noqa: BLE001 - a button hint only; the wait itself is said by the runner
            why = None
        if why:
            out.append((r["id"], r["idx"], why))
    return out


WIDE_ROLE = "place_wide"
WIDE_LABEL = "WIDE same-axis view of this place"


def wide_ref(data_dir: str, pid: int, scene_id: int) -> Optional[Dict]:
    """F2: the shot's same-axis wide 3D render (same camera direction, pulled back, wider lens) as a reference, else None."""
    from . import location_pack
    rec = location_pack.plate_of(data_dir, pid, scene_id)
    wide = (rec or {}).get("wide") or {}
    if not wide.get("plate") or not os.path.exists(wide["plate"]):
        return None
    return {"path": wide["plate"], "label": f"{WIDE_LABEL} ({rec.get('place') or 'the place'})", "role": WIDE_ROLE,
            **({"plate_key": wide["key"]} if wide.get("key") else {})}


def wide_for(conn, data_dir: str, pid: int, scene_id: int, data: Dict) -> Optional[Dict]:
    """wide_ref, but never for an indoor shot (phiên sửa F2): pulled back along the axis, the wide camera of a room ends up behind a
    wall — the same rule as the scene's wide establishing picture (runner: indoor → the room's render is the place)."""
    from . import runner
    if runner.indoor_spot(conn, pid, data):
        return None
    return wide_ref(data_dir, pid, scene_id)


def add_wide(refs: List[Dict], wide: Optional[Dict], limit: int, reserve: int = 0) -> List[Dict]:
    """F2: the wide same-axis render goes right after the shot's own render and REPLACES the scene's one-for-all wide picture
    (scene_establish LABEL / role location) — two different wide views of one place would fight. Order kept: people > shot render >
    same-axis wide > the rest; over `limit` the last pictures go first (never the people, the render or the wide).
    reserve: slots kept free after it (phiên sửa F2: the previous shot's picture of a chained shot, appended by the runner)."""
    if wide is None:
        return refs
    from . import scene_establish
    keep = [r for r in refs if not (r.get("role") == "location" and r.get("label") == scene_establish.LABEL) and r.get("role") != WIDE_ROLE]
    at = next((i + 1 for i, r in enumerate(keep) if r.get("role") == ROLE), None)
    if at is None:
        at = next((i for i, r in enumerate(keep) if r.get("role") in ("location", "previous_scene", "layout")), len(keep))
    out = keep[:at] + [dict(wide)] + keep[at:]
    limit = max(limit - max(reserve, 0), 1)
    while len(out) > limit:
        drop = next((i for i in range(len(out) - 1, -1, -1) if out[i].get("role") not in ("character", "sheet", "outfit", ROLE, WIDE_ROLE)),
                    None)
        out.pop(len(out) - 1 if drop is None else drop)
    return out


def scale_sentence(rec: Optional[Dict], entry: Optional[Dict], data: Dict, height_m: Optional[float] = None,
                   near_m: float = 8.0) -> str:
    """F2 việc 4: the measured size of the place's props near the character's spot (the well's wall …) against the character — so the
    model does not guess the proportions (#24 shot 4: the well came out lower than in the other shots). Reads the place's registered
    `props` [{"name": "the well", "at": [x, y, z] (base, model coords), "height_m": 0.9}] (measured on the 3D model, e.g. with
    plates3d.ground_heights at the prop's top) within `near_m` of the character's feet. Empty when nothing is measured — never a
    guessed number. The caller (the prompt) adds it after geometry_sentence."""
    rec, entry = rec or {}, entry or {}
    feet = ((rec.get("camera_plan") or {}).get("subject") or {}).get("location")
    height = height_m or ((rec.get("camera_plan") or {}).get("subject") or {}).get("height_m")
    if not feet or not height:
        return ""
    bits = []
    for prop in entry.get("props") or []:
        at, h = prop.get("at"), prop.get("height_m")
        if not at or not isinstance(h, (int, float)) or h <= 0:
            continue
        if ((at[0] - feet[0]) ** 2 + (at[1] - feet[1]) ** 2) ** 0.5 > near_m:
            continue
        bits.append(f"{prop.get('name') or 'the landmark'} is {float(h):.2f} m tall — {float(h) / float(height) * 100:.0f}% of the "
                    f"character's height ({float(height):.2f} m)")
    if not bits:
        return ""
    return "Scale measured on the 3D map of this place: " + "; ".join(bits) + " — keep these proportions in every shot."


# ---- F5-A (09/10): vật Kho có kích thước thật → câu tỉ lệ so với người ------------------------------------------------------
# #24: giếng KHÔNG có trong bản đồ 3D (vật Kho #420) — scale_sentence chỉ đọc props của model 3D nên giếng không có số, model ảnh
# tự vẽ, thành giếng mỗi shot một độ cao. Giờ vật Kho (đạo cụ / vũ khí) mang height_m (màn Kho) và được nói so với một người.
PERSON_M = 1.7
OBJECT_TEXT_KEYS = ("image_prompt", "blocking", "start_frame", "action_peak", "location")


def shot_objects(conn, pid: int, data: Dict) -> List[Dict]:
    """Vật Kho (assets.SIZED_KINDS, đã gắn dự án) xuất hiện trong shot: có trong danh sách characters / props của shot, hoặc tên
    (hay tên gọi khác) được nhắc trong image_prompt / blocking / start_frame / action_peak / location (nguyên từ). Không truy vấn
    thêm ngoài assets.project_assets (đã nhớ theo lượt vẽ)."""
    from . import assets
    objs = [a for a in assets.project_assets(conn, pid) if a.get("kind") in assets.SIZED_KINDS]
    if not objs:
        return []
    listed = {assets.fold(str(x)) for k in ("characters", "props") for x in (data.get(k) or []) if isinstance(x, str)}
    words = assets._said_words(" ".join(str(data.get(k) or "") for k in OBJECT_TEXT_KEYS))
    out = []
    for a in objs:
        names = [n.strip() for n in assets.names_of(a) if len(assets.fold(n)) >= 3]
        if any(assets.fold(n) in listed for n in names) or any(assets.name_spans(n, words) for n in names):
            out.append(a)
    return out


def _english_name(asset: Dict) -> str:
    """Tên đưa vào prompt (tiếng Anh, không dấu): tên gọi khác không dấu đầu tiên, không thì tên bỏ dấu."""
    from . import assets
    for n in [asset.get("name") or ""] + (asset.get("aliases") or "").replace(";", ",").replace("|", ",").split(","):
        n = n.strip()
        if n and n.isascii():
            return n
    return assets.fold(asset.get("name") or "the object")


def _body_mark(ratio: float) -> str:
    for limit, words in ((0.3, "below knee height"), (0.45, "about mid-thigh height"), (0.62, "about waist height"),
                         (0.8, "about chest height"), (0.95, "about shoulder height"), (1.08, "about head height")):
        if ratio < limit:
            return words
    return f"about {ratio:.1f} times the height"


def object_scale_sentence(conn, pid: int, data: Dict, person_m: Optional[float] = None, short: bool = False) -> str:
    """Câu tỉ lệ của vật Kho trong shot có kích thước thật, vd 'the stone well rim is 0.9 m high — about waist height of a 1.7 m
    adult'. Vật chưa có số: không đoán, không câu (core/readiness báo warn). short=True: bản gọn cho motion Seedance."""
    person = float(person_m or PERSON_M)
    bits = []
    for a in shot_objects(conn, pid, data):
        size = a.get("size") or {}
        h = size.get("height_m")
        if not h:
            continue
        name = _english_name(a)
        wide = f", {size['width_m']:g} m wide" if size.get("width_m") else ""
        bits.append(f"the {name} is {h:g} m high{wide} — {_body_mark(h / person)} of a {person:g} m adult")
    if not bits:
        return ""
    if short:
        return "Real sizes: " + "; ".join(bits) + "."
    return ("Real sizes of the objects in this shot (measured): " + "; ".join(bits)
            + " — keep exactly these proportions against the people, the same in every shot.")


def unsized_objects(conn, pid: int) -> Dict[str, List[int]]:
    """{tên vật: [scene_id…]} của vật Kho CHƯA có chiều cao thật mà xuất hiện ở ≥ 2 shot của dự án (readiness: warn). Một lượt
    đọc bảng scenes."""
    from . import assets
    if not any(a.get("kind") in assets.SIZED_KINDS and not (a.get("size") or {}).get("height_m") for a in assets.project_assets(conn, pid)):
        return {}
    seen: Dict[str, List[int]] = {}
    for r in conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (pid,)).fetchall():
        try:
            data = json.loads(r["data"] or "{}")
        except ValueError:
            continue
        for a in shot_objects(conn, pid, data):
            if not (a.get("size") or {}).get("height_m"):
                seen.setdefault(a["name"], []).append(r["id"])
    return {k: v for k, v in seen.items() if len(v) >= 2}


def needs(data_dir: str, pid: int, scene_id: int) -> Optional[str]:
    """S5.7: the shot's render is held until the script decides something (a camera direction at a spot marked
    `"direction": "script"`) — the picture waits and the reason is said, never a render from a guessed direction."""
    from . import location_pack
    return location_pack.plate_needs(data_dir, pid, scene_id)


def stale(conn, data_dir: str, pid: int, resolution) -> Dict[int, Dict]:
    """KLD-6: the shots whose render in plates/index.json is not the plan's any more (location_pack.stale_plates) — never sent; the
    caller starts `ensure_async` (Blender, 0 USD) and waits. A plan that cannot be computed comes back as key -1 with the reason: the
    caller says it (diag) and goes on as before KLD-6 — a broken plan never holds a shot for ever."""
    from . import location_pack
    try:
        return location_pack.stale_plates(conn, pid, data_dir, resolution)
    except Exception as e:  # noqa: BLE001 - said by the caller's diag; the shot waits rather than going out on an unchecked render
        return {-1: {"idx": None, "old_spot": None, "new_spot": None, "why": f"không so được nền 3D với kế hoạch ({e})"}}


def stale_note(conn, data_dir: str, pid: int, resolution, scene_id: int, item: Dict) -> str:
    """The diag line of a stale render: why, and (after a spot move) the fields still naming the old place."""
    from . import location_pack
    note = f"shot {item.get('idx') or scene_id}: {item['why']}"
    if item.get("old_spot") and item.get("new_spot") and item["old_spot"] != item["new_spot"]:
        try:
            moved = [m for m in location_pack.move_report(conn, pid, data_dir, resolution) if m["scene_id"] == scene_id]
        except Exception:  # noqa: BLE001 - the move words are extra; the stale line is said anyway
            moved = []
        if moved:
            note += " · " + location_pack.move_words(moved[0])
    return note


def old_plate_images(conn, data_dir: str, pid: int, resolution) -> Dict[int, str]:
    """KLD-6: {scene_id: reason} — the shot's approved picture was drawn on a 3D background (its sent_refs `plate_key`) that is not
    the plan's now (spot / direction / light moved after the picture). Its clip would carry the old place: the autopilot does not send
    it, the Dashboard says it; a person may still send it. Pictures without a recorded key (made before KLD-6) are never held."""
    import json
    from . import location_pack
    rows = conn.execute(
        "SELECT j.scene_id, j.id, j.sent_refs FROM jobs j WHERE j.project_id=? AND j.type='image_gen' AND j.state='approved'"
        " AND j.id=(SELECT MAX(k.id) FROM jobs k WHERE k.scene_id=j.scene_id AND k.type='image_gen' AND k.state='approved')",
        (pid,)).fetchall()
    drawn = {}
    for r in rows:
        try:
            sent = json.loads(r["sent_refs"] or "[]")
        except ValueError:
            continue
        key = next((s.get("plate_key") for s in sent if isinstance(s, dict) and s.get("role") == ROLE and s.get("plate_key")), None)
        if key:
            drawn[r["scene_id"]] = (r["id"], key)
    if not drawn:
        return {}
    plans: Dict[tuple, Dict] = {}
    idx = location_pack.index(data_dir, pid)
    out = {}
    for sid, (jid, key) in drawn.items():
        rec = idx.get(str(sid)) or {}
        res = tuple(int(v) for v in (rec["res"] if rec.get("key") == key and rec.get("res") else resolution))   # its own size
        if res not in plans:
            plans[res] = {it["scene_id"]: it for it in location_pack.plan(conn, pid, res)}
        it = plans[res].get(sid)
        if it is not None and it["key"] == key:
            continue
        where = (f"chỗ đứng / hướng máy hiện tại: {it['spot']}" if it is not None else "shot không còn ở bối cảnh có mô hình 3D")
        out[sid] = (f"ảnh khung đầu (job {jid}) vẽ trên nền 3D cũ — {where}. Vẽ lại ảnh (nền mới tự dựng 0 USD) trước khi gen "
                    "video; chế độ tự chạy không tự gửi clip này, bạn bấm gửi tay vẫn được")
    return out


def video_warnings(conn, data_dir: str, pid: int) -> List[str]:
    """KLD-6, the Video screen: pictures drawn on an old 3D background + renders that are not the plan's (a reference-only send
    waits for the new one)."""
    if not enabled():
        return []
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    try:
        res = resolution_of(proj) if proj is not None else (1152, 2048)
        idx_of = {r["id"]: r["idx"] for r in conn.execute("SELECT id, idx FROM scenes WHERE project_id=?", (pid,))}
        lines = [f"Shot {idx_of.get(sid, sid)}: {why}" for sid, why in sorted(old_plate_images(conn, data_dir, pid, res).items())]
        lines += [f"Shot {item.get('idx') or idx_of.get(sid, sid)}: {item['why']}" for sid, item in sorted(stale(conn, data_dir, pid, res).items())]
    except Exception as e:  # noqa: BLE001 - the screen never breaks; the problem is said
        return [f"không kiểm được nền 3D của các shot ({e})"]
    return lines


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
    """(severity, words) for the diagnostics. KLD-17: only "info" until CALIBRATED — the number is noted, nobody is alarmed by it."""
    if score is None:
        return ("info", "không đo được độ khớp nền với render 3D")
    if not CALIBRATED:
        return ("info", f"độ khớp đường nét nền ↔ render 3D chỗ đứng trong kế hoạch: {score:.2f} "
                        f"(chỉ ghi số, chưa hiệu chỉnh — chưa dùng để cảnh báo)")
    if score < LOW_MATCH:
        return ("warn", f"nền lệch render 3D (độ khớp đường nét {score:.2f} < {LOW_MATCH}) — model có thể đã vẽ lại kiến trúc")
    return ("info", f"nền khớp render 3D (độ khớp đường nét {score:.2f})")


def _pairs_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), PAIRS_FILE)


def measure(conn, data_dir: str, pid: int, scene_id: int, job_id: int, image_path: str, resolution) -> tuple:
    """KLD-17: (severity, words) of how well the drawn picture kept the render of the shot's spot IN THE PLAN. The plates/index.json
    record is used only when it is the plan's (location_pack.stale_plates says nothing about it): a background the plan has left
    (spot / direction / light changed after the picture was sent) is not measured — the number would compare with the wrong place.
    Each measure is kept in <data_dir>/<pid>/place_match.json {job_id, scene_id, score, plate_key} for calibration (pairs())."""
    ref = shot_ref(data_dir, pid, scene_id)
    if ref is None:
        return ("info", "không có render 3D của shot — không đo độ khớp nền")
    gone = stale(conn, data_dir, pid, resolution)
    if -1 in gone:
        return ("info", "không đo độ khớp nền: " + gone[-1]["why"])
    if scene_id in gone:
        return ("info", "không đo độ khớp nền: render đang gắn khác chỗ đứng trong kế hoạch (" + gone[scene_id]["why"] + ")")
    score = background_match(image_path, ref["path"], ref["_rec"].get("subject_box"))
    if score is not None:
        path = _pairs_path(data_dir, pid)
        with _LOCK:
            try:
                with open(path, encoding="utf-8") as f:
                    rows = json.load(f)
            except (OSError, ValueError):
                rows = []
            rows = [r for r in rows if r.get("job_id") != job_id] + [
                {"job_id": job_id, "scene_id": scene_id, "score": round(float(score), 4), "plate_key": ref.get("plate_key")}]
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
    return match_note(score)


def pairs(conn, data_dir: str, pid: int) -> List[Dict]:
    """KLD-17: the kept measures with the PERSON's last review of each picture as label ("approve" / "reject", None = not looked at
    yet) — the QC's decisions are not a label. The rows to calibrate LOW_MATCH from (then CALIBRATED = True)."""
    try:
        with open(_pairs_path(data_dir, pid), encoding="utf-8") as f:
            rows = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for r in rows:
        last = conn.execute("SELECT decision FROM review_log WHERE job_id=? AND reviewer_type='user' ORDER BY decided_at DESC, rowid DESC"
                            " LIMIT 1", (r["job_id"],)).fetchone()
        out.append(dict(r, label=last[0] if last else None))
    return out
