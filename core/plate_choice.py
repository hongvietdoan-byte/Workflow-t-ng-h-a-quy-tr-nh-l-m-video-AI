"""S5.7 (người dùng 29/09): the camera direction at a spot of a 3D place and the extra lights of a night shot are decided per shot from
the script — not constants of the place.

User's words: "Hướng máy ở góc dưới mái che (lower_yard ≡ level_22_4 của Tháp Đồng Hồ) không thể cố định sẵn, mà tùy vào kịch bản; cảnh
đêm cũng tùy kịch bản mà có dùng thêm đèn lấy ánh sáng hay không." Before this, a spot had one `facing` (set once, away from the landmark)
and every shot there saw the same background; the three covered-spot renders of 29/09 (`tools/tower_pack.py --only-covered`: ra / vào /
ngang) are now reference pictures only.

Shot fields the DP (Quay phim) writes — knowledge/roles/dp.md Q6, prompts/17_director_shots.md:
  plate_view        what is BEHIND the character in the frame, with the reason:
                    {"background": "landmark" | "away" | "left" | "right" | "scenery" | "spot:<name>" | <bearing°>, "why": "tiếng Việt"}
                    (a bare string / number is accepted too). landmark = the camera looks towards the place's landmark (the anchor);
                    away = the reverse; left / right = 90° off, as seen by someone at the spot facing the landmark; spot:<name> = towards
                    another spot; scenery = what the spot was registered to look at (its
                    `view` point — surroundings spots, 29/09; `view_out` for an indoor spot = out through its door / window); a number = compass bearing of the background, degrees clockwise from the model's +y.
  practical_lights  the extra light sources of the shot (or of its scene): [] = decided "none" (moon / sun only);
                    [{"kind": lamp|fire|screen|neon|torch|headlight|window, "where": behind|behind_left|behind_right|left|right|
                      front|front_left|front_right|above|background, "color": warm|orange|cool|blue|white|red|green|purple|pink|#rrggbb,
                      "why": "tiếng Việt"}] — `where` is seen from the camera (left = frame left).

Missing information is never filled in silently (docs/CHUAN_XAY_DUNG.md luật 1):
  - a spot marked `"direction": "script"` (the covered yard) without a usable `plate_view` → `needs`: no plate is rendered, the shot's picture
    waits, the autopilot says what to add;
  - any other spot without `plate_view` → `problem`: the spot's registered `facing` is used and the choice is reported;
  - a night shot without `practical_lights` → `problem`: rendered with moonlight only, and reported ("chưa quyết").
No AI, no credit: pure geometry and words.
"""
import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

VIEWS = ("landmark", "away", "left", "right", "scenery")
_VIEW_WORDS = {"landmark": ("landmark", "tower", "tháp", "mốc", "toward_landmark", "towards_landmark"),
               "away": ("away", "reverse", "ngược", "nguoc", "away_from_landmark"),
               "left": ("left", "trái", "trai", "ngang_trai"), "right": ("right", "phải", "phai", "ngang_phai")}
KINDS = {  # kind -> Blender light type, watts (bright enough to read through the night exposure -1.4 + grade: 400 W lamp = barely visible, 29/09), height above the character's feet (m), default colour, size (m) / cone (°), words
    "lamp": ("POINT", 1600.0, 2.8, "warm", 0.10, "a street / wall lamp"),
    "fire": ("POINT", 2000.0, 0.5, "orange", 0.40, "firelight (flickering flames)"),
    "screen": ("AREA", 150.0, 1.3, "cool", 0.40, "the glow of a screen"),
    "neon": ("AREA", 600.0, 2.4, "pink", 1.00, "a neon sign"),
    "torch": ("SPOT", 3000.0, 1.4, "white", 30.0, "a hand torch beam"),
    "headlight": ("SPOT", 5000.0, 0.8, "white", 50.0, "vehicle headlights"),
    "window": ("AREA", 1000.0, 2.0, "warm", 1.50, "light from a window"),
}
COLOURS = {"warm": (1.0, 0.72, 0.42), "orange": (1.0, 0.50, 0.20), "cool": (0.60, 0.75, 1.0), "blue": (0.35, 0.50, 1.0),
           "white": (1.0, 0.96, 0.90), "red": (1.0, 0.18, 0.15), "green": (0.30, 1.0, 0.45), "purple": (0.65, 0.35, 1.0),
           "pink": (1.0, 0.35, 0.70)}
# where (seen from the camera) -> (metres along the camera's look beyond the character, metres to the frame's right)
WHERE = {"behind": (2.5, 0.0), "behind_left": (2.2, -1.8), "behind_right": (2.2, 1.8), "left": (0.0, -2.2), "right": (0.0, 2.2),
         "front": (-1.5, 0.0), "front_left": (-1.3, -1.5), "front_right": (-1.3, 1.5), "above": (0.0, 0.0), "background": (8.0, 0.0)}
_WHERE_WORDS = {"behind": "from behind the character (rim light on hair and shoulders)",
                "behind_left": "from behind-left (rim light on the left edge of the character)",
                "behind_right": "from behind-right (rim light on the right edge of the character)",
                "left": "from the left of the frame (side light on that half of the face)",
                "right": "from the right of the frame (side light on that half of the face)",
                "front": "from the front (on the face)", "front_left": "from front-left (on the face)",
                "front_right": "from front-right (on the face)", "above": "from right above (top light, shadows under the brows)",
                "background": "in the background (a glow behind, the character mostly in silhouette)"}
MAX_LIGHTS = 3
NIGHT_TIMES = ("night",)


def is_behind(data: Dict) -> bool:
    """The camera stands behind the character (over the shoulder / back to camera) — the same test plate_camera.camera_for uses."""
    angle = str(data.get("angle") or "eye").lower()
    words = f"{data.get('start_frame') or ''} {data.get('angle') or ''}".lower()
    return angle == "ots" or "from behind" in words or "back to camera" in words or "quay lưng" in words


def bearing(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    """Compass bearing from a to b on the ground, degrees clockwise from +y (the convention of spot `facing`)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return None
    return round(math.degrees(math.atan2(dx, dy)) % 360.0, 1)


def script_view_spot(entry: Dict, spot_name: Optional[str]) -> bool:
    return str(((entry.get("spots") or {}).get(spot_name) or {}).get("direction") or "") == "script"


def _raw_view(data: Dict) -> Tuple[object, Optional[str]]:
    v = data.get("plate_view")
    if isinstance(v, dict):
        why = v.get("why")
        return v.get("background", v.get("toward")), (why.strip() if isinstance(why, str) and why.strip() else None)
    return v, None


def landmark_off_frame(data: Dict) -> bool:
    """08/10 (#24, việc 16): the shot's `plate_view` turns the camera away from the place's landmark (away / left / right) — a picture of
    the place that SHOWS the landmark (the Kho's Tháp Đồng Hồ) must not go with it: it pulled the tower into a reverse shot."""
    raw, _ = _raw_view(data or {})
    word = str(raw or "").strip().lower()
    return any(word in _VIEW_WORDS[k] for k in ("away", "left", "right")) if word else False


def _landmark_word(entry: Dict) -> str:
    return str(entry.get("landmark") or "the landmark")


def view_of(entry: Dict, spot: Dict, data: Dict) -> Dict:
    """The camera direction of a shot at `spot` (a spot dict with name/at/facing of `entry`).
    Returns {"background_deg", "facing_deg" (for plate_camera.camera_for), "view" (the value used), "source" ("script" | "spot_default"),
    "why", "words_vi" (Vietnamese, for the person), "words_en" (for a prompt without a plate), "problem", "needs"}."""
    raw, why = _raw_view(data)
    name = spot.get("name")
    at = spot["at"]
    anchor = entry.get("anchor")
    to_mark = bearing(at, anchor) if anchor else None
    mark = _landmark_word(entry)
    bg, view, words_vi, words_en, bad = None, None, "", "", None
    if raw is not None and raw != "":
        text = str(raw).strip().lower()
        kind = next((k for k, ws in _VIEW_WORDS.items() if text in ws), None)
        num = None
        try:
            num = float(text) if kind is None and not text.startswith("spot:") else None
        except ValueError:
            num = None
        if kind is not None:
            if to_mark is None:
                bad = f"hướng máy '{raw}' cần mốc (anchor) của bối cảnh mà bối cảnh chưa có"
            else:
                bg = (to_mark + {"landmark": 0, "away": 180, "left": -90, "right": 90}[kind]) % 360
                view = kind
                words_vi = {"landmark": "máy nhìn về phía mốc (mốc ở nền sau nhân vật)",
                            "away": "máy quay lưng về mốc (nền là phía ngược mốc, không thấy mốc)",
                            "left": "máy nhìn ngang, lệch 90° sang trái so với hướng nhìn về mốc",
                            "right": "máy nhìn ngang, lệch 90° sang phải so với hướng nhìn về mốc"}[kind]
                words_en = {"landmark": f"the camera looks towards {mark}: {mark} is behind the character (as far as the walls around "
                                        "let it be seen — the 3D render decides)",
                            "away": f"the camera looks away from {mark}: {mark} is NOT in the frame, behind the character is the "
                                    "opposite side of the place",
                            "left": f"the camera looks across the place: {mark} is off-frame to the right",
                            "right": f"the camera looks across the place: {mark} is off-frame to the left"}[kind]
        elif text in ("scenery", "view", "view_out", "cảnh quan", "canh quan"):
            point = spot.get("view_out") if text == "view_out" or (text != "view" and spot.get("indoor") and spot.get("view_out")) \
                else spot.get("view")
            bg = bearing(at, point) if isinstance(point, (list, tuple)) and len(point) >= 2 else None
            if bg is None:
                bad = f"hướng máy '{raw}': chỗ đứng '{name}' không có điểm nhìn cảnh quan đã đăng ký (`view` / `view_out`)"
            else:
                view = "scenery"
                words_vi = "máy nhìn theo hướng cảnh quan đã đăng ký của chỗ đứng"
                words_en = "the camera looks at the surroundings of this spot"
        elif text.startswith("spot:") or text in (entry.get("spots") or {}):
            other = text[5:].strip() if text.startswith("spot:") else text
            osp = (entry.get("spots") or {}).get(other)
            if osp is None:
                bad = f"hướng máy '{raw}': không có chỗ đứng '{other}' ở bối cảnh này"
            else:
                bg = bearing(at, osp["at"])
                if bg is None:
                    bad = f"hướng máy '{raw}': chỗ đứng '{other}' trùng chỗ nhân vật đứng — không ra hướng"
                else:
                    view = f"spot:{other}"
                    label = osp.get("label") or other
                    words_vi = f"máy nhìn về phía chỗ đứng '{other}' ({label})"
                    words_en = f"the camera looks towards {label} of the place"
        elif num is not None and math.isfinite(num):
            bg = num % 360
            view = f"{bg:g}"
            words_vi = f"nền theo hướng {bg:g}° (theo la bàn của mô hình)"
            words_en = ""
            if to_mark is not None:
                off = (bg - to_mark + 180) % 360 - 180
                words_en = (f"{mark} is in the background" if abs(off) < 25 else
                            f"{mark} is NOT in the frame" if abs(off) > 60 else
                            f"{mark} is at the {'right' if off < 0 else 'left'} edge of the background")
        else:
            bad = (f"hướng máy '{raw}' không hiểu được — dùng một trong {', '.join(VIEWS)}, 'spot:<tên chỗ đứng>' hoặc số độ")
    needs = problem = None
    source = "script"
    if bg is None:
        source = "spot_default"
        reason = bad or f"shot chưa ghi hướng máy (`plate_view`) ở chỗ đứng '{name}'"
        if script_view_spot(entry, name):
            needs = (f"{reason} — chỗ đứng '{name}' không có hướng cố định (người dùng 29/09: tùy kịch bản): Quay phim ghi `plate_view` "
                     "{\"background\": landmark|away|left|right|spot:<tên>|số độ, \"why\": …} rồi chạy lại; nền chưa render")
        else:
            problem = f"{reason} — dùng hướng mặc định của chỗ đứng ({float(spot.get('facing', 0)):g}°), chưa phải lựa chọn theo kịch bản"
        facing = float(spot.get("facing", 0.0))
        bg = (facing + (0 if is_behind(data) else 180)) % 360
        words_vi = "hướng mặc định của chỗ đứng (kịch bản chưa chọn)"
    elif why is None:
        problem = "hướng máy chưa ghi lý do (`plate_view.why`) — người duyệt không biết vì sao chọn hướng này"
    facing = (bg + (0 if is_behind(data) else 180)) % 360          # camera_for: the camera stands in front, the character faces it
    return {"background_deg": round(bg, 1), "facing_deg": round(facing, 1), "view": view, "source": source, "why": why,
            "words_vi": words_vi, "words_en": words_en, "problem": problem, "needs": needs}


# ---- extra lights --------------------------------------------------------------------------------------------------------------
def _colour(value, kind: str) -> Tuple[Tuple[float, float, float], str, Optional[str]]:
    if value is None or value == "":
        name = KINDS[kind][3]
        return COLOURS[name], name, None
    text = str(value).strip().lower()
    if text in COLOURS:
        return COLOURS[text], text, None
    m = re.fullmatch(r"#?([0-9a-f]{6})", text)
    if m:
        h = m.group(1)
        return tuple(round(int(h[i:i + 2], 16) / 255, 3) for i in (0, 2, 4)), f"#{h}", None
    name = KINDS[kind][3]
    return COLOURS[name], name, f"màu '{value}' không hiểu được — dùng '{name}'"


def raw_lights(data: Dict):
    """The shot's `practical_lights` (shot_data copies the scene's value onto its shots). None = not decided."""
    v = data.get("practical_lights")
    return v if isinstance(v, list) else None


def lights_of(data: Dict, env: Dict) -> Dict:
    """{"lights": [{"kind", "where", "color_name", "rgb", "why"}], "decided": bool, "problem": str|None}.
    Night without a decision is reported (rendered with moonlight only, never presented as a choice)."""
    raw = data.get("practical_lights")
    problems: List[str] = []
    if raw is not None and not isinstance(raw, list):
        problems.append("`practical_lights` phải là danh sách ([] = không thêm đèn)")
        raw = None
    out = []
    for i, item in enumerate(raw or []):
        if not isinstance(item, dict):
            problems.append(f"đèn {i + 1}: phải là {{kind, where, color, why}}")
            continue
        kind = str(item.get("kind") or "").strip().lower()
        where = str(item.get("where") or "").strip().lower().replace("-", "_").replace(" ", "_")
        if kind not in KINDS:
            problems.append(f"đèn {i + 1}: loại '{item.get('kind')}' không có ({', '.join(KINDS)}) — bỏ đèn này")
            continue
        if where not in WHERE:
            problems.append(f"đèn {i + 1} ({kind}): vị trí '{item.get('where')}' không có ({', '.join(WHERE)}) — bỏ đèn này")
            continue
        rgb, cname, cprob = _colour(item.get("color"), kind)
        if cprob:
            problems.append(f"đèn {i + 1} ({kind}): {cprob}")
        why = item.get("why") if isinstance(item.get("why"), str) and item.get("why").strip() else None
        if why is None:
            problems.append(f"đèn {i + 1} ({kind}): chưa ghi lý do (`why`)")
        out.append({"kind": kind, "where": where, "color_name": cname, "rgb": list(rgb), "why": why})
    if len(out) > MAX_LIGHTS:
        problems.append(f"{len(out)} đèn — chỉ giữ {MAX_LIGHTS} đèn đầu (nhiều đèn làm cảnh đêm mất tối)")
        out = out[:MAX_LIGHTS]
    decided = raw is not None
    if not decided and env.get("time") in NIGHT_TIMES:
        problems.append("cảnh đêm chưa quyết có thêm đèn hay không (`practical_lights`: [] = chỉ ánh trăng, hoặc liệt kê đèn/lửa/màn "
                        "hình theo kịch bản) — nền render chỉ có ánh trăng")
    return {"lights": out, "decided": decided, "problem": "; ".join(problems) or None}


def _unit2(dx: float, dy: float) -> Tuple[float, float]:
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def light_rigs(lights: List[Dict], subject: Sequence[float], camera: Sequence[float], height_m: float = 1.75) -> List[Dict]:
    """Blender lights (model coordinates, like the camera) for tools/render_plates.py: placed around the character relative to the
    camera's look (behind = beyond the character, left = frame left), aimed at the character's chest."""
    fx, fy = _unit2(subject[0] - camera[0], subject[1] - camera[1])
    rx, ry = fy, -fx                                               # frame right
    chest = [subject[0], subject[1], subject[2] + height_m * 0.7]
    out = []
    for lt in lights:
        btype, watts, h, _, size, _ = KINDS[lt["kind"]]
        along, side = WHERE[lt["where"]]
        z = subject[2] + (3.2 if lt["where"] == "above" else h)
        loc = [round(subject[0] + fx * along + rx * side, 3), round(subject[1] + fy * along + ry * side, 3), round(z, 3)]
        rig = {"type": btype, "location": loc, "look_at": [round(c, 3) for c in chest], "color": list(lt["rgb"]), "energy": watts,
               "kind": lt["kind"], "where": lt["where"]}
        if btype == "SPOT":
            rig["spot_deg"] = size
        else:
            rig["size"] = size
        out.append(rig)
    return out


def light_sentence(lights: List[Dict], decided: bool, time: str) -> str:
    """The extra lights in words for the picture prompt (the character must be lit like the plate is)."""
    if not lights:
        return ("No extra light source: only the moonlight lights the character." if decided and time in NIGHT_TIMES else "")
    parts = [f"{KINDS[lt['kind']][5]}, {lt['color_name']} colour, {_WHERE_WORDS[lt['where']]}" for lt in lights]
    return "Practical light chosen for this shot: " + "; ".join(parts) + ". Light the character with it consistently."


def light_words_vi(lights: List[Dict], decided: bool) -> str:
    if not decided:
        return "đèn: chưa quyết"
    if not lights:
        return "đèn: không thêm (chỉ trời/trăng)"
    return "đèn: " + ", ".join(f"{lt['kind']} {lt['color_name']} {lt['where']}" for lt in lights)
