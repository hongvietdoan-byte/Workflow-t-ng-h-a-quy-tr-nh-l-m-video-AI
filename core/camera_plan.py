"""G0 (người dùng 09/10, docs/KE_HOACH_DAT_MAY_3D_2026-10-09.md mục 🥇 G0): Đạo diễn lập sơ đồ cảnh + bộ góc máy dùng lại cho mỗi cảnh
liên tục quay trên bối cảnh có mô hình 3D, rồi xem render nền từng góc. Cờ `director_camera_plan` (TẮT mặc định — tắt thì không hàm nào
ở đây làm gì, location_pack.plan giữ cách gộp máy cũ).

Vì sao (#24): Director/Quay phim ghi `plate_view` TỪNG SHOT RIÊNG, không có sơ đồ chung → 9 shot cùng quảng trường ra nhiều hướng không
ăn khớp (shot 5, 7 nhìn sang Tây — mặt quảng trường người xem chưa thấy), không ai xem render nền trước khi vẽ ảnh.

Luồng (autopilot `_plates_phase`, hoặc `py tools/location_pack.py camera-plan`):
  1. before_plates — mỗi cảnh (story_scene × bối cảnh) chưa có sơ đồ: MỘT lượt Claude (khâu `director_camera_plan`, ước tính trước,
     qua sổ chi) đọc kịch bản + shot + hướng mốc/chỗ đứng tính từ `model3d.anchor` + ảnh topview nếu có → JSON: đạo cụ, chỗ đứng theo
     nhịp, trục 180°, 3–4 setup {phương vị độ, angle, tilt, mốc trong khung}, shot → setup + size + angle. CODE kiểm (check): angle
     theo setup, shot nhìn xuống mà setup máy ngang → tách setup cúi, vượt trục không lý do, nền chưa giới thiệu → diag. Ghi vào shot:
     `plate_setup`, `plate_view` = phương vị độ + lý do, `size`, `angle` (trường người khóa `_user_locked` giữ nguyên, báo).
  2. location_pack.plan: shot cùng `plate_setup` + cùng cỡ + cùng chỗ đứng → CÙNG camera (plate_camera.plan_cameras) → cùng cache key,
     render một lần.
  3. after_plates — mỗi setup một render (+ render shot mở): Claude (khâu `director_plate_review`) chỉ KHAI QUAN SÁT dạng enum
     (OBSERVATIONS); CODE (judge) kết luận khớp / không + lý do + cách sửa (model nhìn đúng nhưng hay kết luận sai —
     reference_qc_model_sees_but_misreasons). Không khớp → đổi phương vị / angle, render lại (Blender, 0 USD), tối đa
     MAX_REVIEW_ROUNDS vòng, rồi báo người dùng (diag error `director_plate_review`, ⚙ Chẩn đoán) — không im lặng.
Sơ đồ lưu ở <data_dir>/<pid>/plates/camera_plan.json (theo dự án; không phải đường dẫn tương đối cwd)."""
import copy
import json
import math
import os
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import diag, features

FLAG = "director_camera_plan"
STAGE = "director_camera_plan"
REVIEW_STAGE = "director_plate_review"
CODE = "director_camera_plan"
REVIEW_CODE = "director_plate_review"
SETUP_FIELD = "plate_setup"
SCENE_FIELD = "plate_setup_scene"      # rà G0: the plan (scene group key) the set-up belongs to — "A" of two plans is two cameras
CAMERA_LOCKS = ("plate_view", "angle")  # rà G0: a shot whose camera field the person locked keeps its OWN camera (no plate_setup)
PROMPT_FILE = "28_director_camera_plan.md"
PLAN_HEAD = "# Đạo diễn — sơ đồ cảnh và bộ góc máy"
REVIEW_HEAD = "# Đạo diễn — duyệt render nền"
ANGLES = ("low", "eye", "high", "overhead", "ots")
TILTS = ("down", "level", "up")
LANDMARK = ("yes", "no", "any")
SIDES = ("left", "right")
MAX_SETUPS = 6                     # 3–4 khuyên dùng (prompt); quá 6 = câu trả lời không dùng được
ON_AXIS_DEG = 30.0                 # máy cách đường trục ≤ 30° (nhìn dọc trục / góc ngược thẳng) không tính là một phía
FAMILY_DEG = 40.0                  # nền "cùng gia đình" shot mở (hoặc hướng ngược) khi lệch ≤ 40°
LANDMARK_OFF_DEG = 60.0            # muốn thấy mốc mà nhìn lệch mốc quá 60° → báo
MAX_REVIEW_ROUNDS = 2
MAX_TRIES = 2                      # a Claude failure (plan or look) is tried again by the autopilot at most this many times in all
ROTATE_STEPS = (25.0, -25.0)       # vòng sửa 1 / 2: xoay phương vị so với phương vị gốc của setup
LOOK_DOWN_ANGLES = ("high", "ots", "overhead")
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quan sát Claude được phép khai trên một render nền (chỉ điều THẤY — code kết luận)
OBSERVATIONS: Dict[str, str] = {
    "wall_near_blocking": "tường / vật chắn sát máy che phần lớn khung",
    "landmark_visible": "thấy mốc của bối cảnh (vd tháp đồng hồ), dù chỉ một phần",
    "landmark_not_visible": "không thấy mốc của bối cảnh",
    "camera_tilted_down": "máy cúi rõ: mặt đất chiếm phần lớn nền, không thấy đường chân trời hoặc nó sát mép trên",
    "camera_level": "máy ngang: đường chân trời quanh giữa khung",
    "camera_tilted_up": "máy ngửa: đường chân trời ở nửa dưới khung",
    "sky_dominant": "trời chiếm hơn nửa khung",
    "ground_dominant": "mặt đất / sàn chiếm hơn nửa khung",
    "background_same_as_opening": "cùng phía, cùng các khối nhà/kiến trúc với render shot mở (ảnh 2)",
    "background_differs_from_opening": "nền là một phía khác hẳn render shot mở (ảnh 2)",
    "open_area_visible": "thấy khoảng sân trống quanh chỗ nhân vật đứng",
    "render_broken": "render trống / đen / hỏng",
}
_CONTRADICT = (("landmark_visible", "landmark_not_visible"), ("camera_tilted_down", "camera_tilted_up"),
               ("camera_tilted_down", "camera_level"), ("camera_level", "camera_tilted_up"),
               ("background_same_as_opening", "background_differs_from_opening"))


def enabled() -> bool:
    return features.on(FLAG)


def project_resolution(conn, pid: int) -> Tuple[int, int]:
    """The render size of the project — the same as autopilot._plates_phase (so the CLI renders / reviews the autopilot's cache)."""
    from . import formats
    row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    size = formats.spec((formats.project_aspect(row) if row is not None else None) or "9:16")["deepix"]
    w, h = (int(v) for v in str(size).lower().split("x"))
    return w, h


def needs_plan(old: Optional[Dict], force: bool = False) -> bool:
    """A scene needs a (new) plan: forced, none yet, or failed with tries left (MAX_TRIES)."""
    return bool(force or old is None or (old.get("failed") and int(old.get("tries") or 0) < MAX_TRIES))


def drawn_shots(conn, group: Dict) -> List[int]:
    """idx of the group's shots that already have a picture (an image job with a result) — a new camera would make it stale."""
    out = []
    for s in group["shots"]:
        if conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND COALESCE(result_path,'')<>'' LIMIT 1",
                        (s["id"],)).fetchone():
            out.append(s["idx"])
    return out


def todo_groups(conn, pid: int, data_dir: str, force: bool = False) -> Tuple[List[Dict], List[str], Dict[str, List[int]]]:
    """(groups to plan, keys kept, {key: drawn shot idx} skipped) — one rule for before_plates and the CLI estimate."""
    plans = load_plans(data_dir, pid)
    todo, kept, drawn = [], [], {}
    for g in groups(conn, pid):
        if not needs_plan(plans.get(g["key"]), force):
            kept.append(g["key"])                         # a plan, or MAX_TRIES failures (said; `force` = the person asks again)
            continue
        done = drawn_shots(conn, g)
        if done and not force:
            drawn[g["key"]] = done
            continue
        todo.append(g)
    return todo, kept, drawn


def _angdiff(a: float, b: float) -> float:
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def _num(v) -> Optional[float]:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        return None
    return float(v)


# ---- storage --------------------------------------------------------------------------------------------------------------------
def plan_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "plates", "camera_plan.json")


def load_plans(data_dir: str, pid: int) -> Dict[str, Dict]:
    try:
        with open(plan_path(data_dir, pid), encoding="utf-8") as f:
            return (json.load(f) or {}).get("scenes") or {}
    except (OSError, ValueError):
        return {}


def _save_plans(data_dir: str, pid: int, plans: Dict[str, Dict]) -> None:
    path = plan_path(data_dir, pid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "scenes": plans}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


# ---- inputs ---------------------------------------------------------------------------------------------------------------------
def groups(conn, pid: int) -> List[Dict]:
    """[{key, place, entry, spot, shots}] — one per continuous scene (story_scene) and 3D place; shots in film order."""
    from . import location_pack
    out: Dict[tuple, Dict] = {}
    for s in location_pack.shots_at_3d_places(conn, pid):
        scene = s["data"].get("story_scene")
        key = str(scene) if scene not in (None, "") else f"shot{s['idx']}"
        g = out.setdefault((key, s["place"]["id"]), {"key": key, "place": s["place"], "entry": s["entry"], "shots": []})
        g["shots"].append(s)
    res = []
    keys = [k for k, _ in out]
    for (key, place_id), g in out.items():
        if keys.count(key) > 1:                       # one scene over two places: one plan per place
            g["key"] = f"{key}·{place_id}"
        g["shots"].sort(key=lambda s: s["idx"])
        g["spot"] = location_pack.spot_for(g["entry"], g["shots"][0]["data"])
        res.append(g)
    return res


def place_facts(entry: Dict, spot: Dict) -> Dict:
    """Directions from the spot: the landmark (model3d.anchor) and the other spots, degrees clockwise from +y, model units. What is
    missing is listed (`missing`) — said to the Director and in diag, never filled in."""
    from .plate_choice import bearing
    at = spot["at"]
    name = spot.get("name")
    facts: Dict = {"spot": name, "label": spot.get("label") or name, "landmark": entry.get("landmark") or "mốc của bối cảnh",
                   "spot_facing_deg": spot.get("facing"), "missing": []}
    anchor = entry.get("anchor")
    if isinstance(anchor, (list, tuple)) and len(anchor) >= 2:
        b = bearing(at, anchor)
        if b is not None:
            facts["landmark_bearing_deg"] = b
            facts["landmark_distance"] = round(math.hypot(anchor[0] - at[0], anchor[1] - at[1]), 1)
    if "landmark_bearing_deg" not in facts:
        facts["missing"].append("bối cảnh chưa có mốc (`model3d.anchor`) — không tính được hướng mốc/tháp từ chỗ đứng; phương vị "
                                "chỉ dựa vào các chỗ đứng khác")
    spots = []
    for other, sp in (entry.get("spots") or {}).items():
        if other == name or not isinstance(sp.get("at"), (list, tuple)):
            continue
        b = bearing(at, sp["at"])
        if b is None:
            continue
        spots.append({"name": other, "label": sp.get("label") or other, "bearing_deg": b,
                      "distance": round(math.hypot(sp["at"][0] - at[0], sp["at"][1] - at[1]), 1),
                      "height_diff": round(float(sp["at"][2]) - float(at[2]), 1) if len(sp["at"]) > 2 and len(at) > 2 else None})
    facts["spots"] = sorted(spots, key=lambda s: s["distance"])[:12]
    if not facts["spots"]:
        facts["missing"].append("bối cảnh chỉ có một chỗ đứng — không có điểm phụ để định hướng")
    view = spot.get("view")
    if isinstance(view, (list, tuple)) and len(view) >= 2:
        facts["scenery_bearing_deg"] = bearing(at, view)
    return facts


def topview_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "plates", "top_view.png")


_SHOT_KEYS = ("size", "angle", "characters", "action", "blocking", "start_frame", "end_state", "emotional_intent", "duration_s",
              "plate_view", "plate_spot")


def _shot_rows(group: Dict) -> List[Dict]:
    rows = []
    for s in group["shots"]:
        d = s["data"]
        row = {"idx": s["idx"], **{k: d[k] for k in _SHOT_KEYS if d.get(k) not in (None, "", [])}}
        lines = [f"{x.get('speaker') or x.get('character') or ''}: {x.get('line') or x.get('text') or ''}".strip(": ")
                 for x in d.get("dialogue") or [] if isinstance(x, dict)]
        if lines:
            row["dialogue"] = lines[:4]
        rows.append(row)
    return rows


def _story_scene(conn, pid: int, key: str) -> Optional[Dict]:
    try:
        idx = int(str(key).split("·")[0])
    except ValueError:
        return None
    row = conn.execute("SELECT heading, text, data FROM story_scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()
    return dict(row) if row else None


def build_prompt(conn, pid: int, group: Dict, data_dir: str) -> Tuple[str, List[Tuple[str, str]], List[str]]:
    """(text, images [(caption, path)], notes about missing inputs)."""
    facts = place_facts(group["entry"], group["spot"])
    notes = list(facts["missing"])
    images: List[Tuple[str, str]] = []
    top = topview_path(data_dir, pid)
    if os.path.exists(top):
        images.append(("Sơ đồ nhìn từ trên (vàng: nhân vật, xanh: máy hiện tại của các shot, xám: chỗ đứng):", top))
        top_line = "Ảnh kèm: sơ đồ nhìn từ trên của dự án (máy HIỆN TẠI — có thể sai, đó là điều bạn đang sửa)."
    else:
        notes.append(f"không có ảnh sơ đồ nhìn từ trên (topview) ở {top} — tạo bằng `py tools/location_pack.py topview --project {pid}`")
        top_line = "Ảnh kèm: không có ảnh sơ đồ nhìn từ trên (topview) — chỉ dựa vào bảng hướng ở trên."
    try:
        with open(os.path.join(_ROOT, "prompts", PROMPT_FILE), encoding="utf-8") as f:
            rules = f.read().strip()
    except OSError as e:
        raise RuntimeError(f"thiếu file prompt {PROMPT_FILE}: {e}") from e
    story = _story_scene(conn, pid, group["key"]) or {}
    parts = [PLAN_HEAD, "", rules, "",
             f"# Bối cảnh: {group['place']['name']} — chỗ đứng `{facts['spot']}` ({facts['label']})", "```json",
             json.dumps({k: v for k, v in facts.items() if k != "missing"}, ensure_ascii=False, indent=1), "```"]
    if facts["missing"]:
        parts.append("Thiếu căn cứ: " + "; ".join(facts["missing"]))
    parts.append(top_line)
    if story:
        parts += ["", f"# Kịch bản cảnh {group['key']}: {story.get('heading') or ''}".rstrip(), str(story.get("text") or "")[:3000]]
        sdata = str(story.get("data") or "")
        if sdata.strip() not in ("", "{}"):
            parts += ["Ý đồ cảnh (Director):", sdata[:1500]]
    parts += ["", f"# Các shot của cảnh ({len(group['shots'])} shot, theo thứ tự phim)", "```json",
              json.dumps(_shot_rows(group), ensure_ascii=False, indent=1), "```"]
    return "\n".join(parts), images, notes


# ---- the answer -----------------------------------------------------------------------------------------------------------------
def validate(obj, idxs: Sequence[int]) -> Dict:
    """Raises SchemaError (ask_json then asks again once) when the answer cannot be used."""
    from .llm_io import SchemaError
    from .plate_camera import FRAMING
    if not isinstance(obj, dict):
        raise SchemaError("cần một object JSON")
    setups = obj.get("setups")
    if not isinstance(setups, list) or not 1 <= len(setups) <= MAX_SETUPS:
        raise SchemaError(f"setups: cần 1–{MAX_SETUPS} setup (khuyên 3–4)")
    ids = []
    for i, st in enumerate(setups, 1):
        if not isinstance(st, dict) or not str(st.get("id") or "").strip():
            raise SchemaError(f"setup {i}: cần id")
        sid = str(st["id"]).strip().upper()
        if sid in ids:
            raise SchemaError(f"setup {sid}: id trùng")
        ids.append(sid)
        if _num(st.get("azimuth_deg")) is None:
            raise SchemaError(f"setup {sid}: azimuth_deg phải là số độ")
        if str(st.get("angle") or "").lower() not in ANGLES:
            raise SchemaError(f"setup {sid}: angle một trong {', '.join(ANGLES)}")
        if str(st.get("tilt") or "level").lower() not in TILTS:
            raise SchemaError(f"setup {sid}: tilt một trong {', '.join(TILTS)}")
        if str(st.get("landmark_in_frame") or "any").lower() not in LANDMARK:
            raise SchemaError(f"setup {sid}: landmark_in_frame một trong {', '.join(LANDMARK)}")
        if not str(st.get("intent") or "").strip() or not str(st.get("why") or "").strip():
            raise SchemaError(f"setup {sid}: cần intent + why (ý đồ và lý do)")
    shots = obj.get("shots")
    if not isinstance(shots, list):
        raise SchemaError("shots: cần danh sách shot → setup")
    seen = []
    for sh in shots:
        if not isinstance(sh, dict) or isinstance(sh.get("idx"), bool) or not isinstance(sh.get("idx"), int):
            raise SchemaError("shots: mỗi mục cần idx (số)")
        if sh["idx"] not in idxs:
            raise SchemaError(f"shot {sh['idx']}: không thuộc cảnh này ({', '.join(map(str, idxs))})")
        if sh["idx"] in seen:
            raise SchemaError(f"shot {sh['idx']}: gán hai lần")
        seen.append(sh["idx"])
        if str(sh.get("setup") or "").strip().upper() not in ids:
            raise SchemaError(f"shot {sh['idx']}: setup '{sh.get('setup')}' không có trong setups")
        if str(sh.get("size") or "").upper() not in FRAMING:
            raise SchemaError(f"shot {sh['idx']}: size một trong {', '.join(FRAMING)}")
        if sh.get("angle") not in (None, "") and str(sh["angle"]).lower() not in ANGLES:
            raise SchemaError(f"shot {sh['idx']}: angle một trong {', '.join(ANGLES)}")
    missing = [i for i in idxs if i not in seen]
    if missing:
        raise SchemaError(f"thiếu shot {', '.join(map(str, missing))} — mọi shot của cảnh cần một setup")
    axis = obj.get("axis")
    if not isinstance(axis, dict) or _num(axis.get("bearing_deg")) is None or str(axis.get("camera_side") or "").lower() not in SIDES:
        raise SchemaError("axis: cần bearing_deg (số) + camera_side left|right")
    return obj


def normalize(obj: Dict) -> Dict:
    """A validated answer with tidy values (upper-case ids, degrees in 0–360, lower-case words); bad props/beats are dropped."""
    out = {"setups": [], "shots": [], "props": [], "beats": []}
    for st in obj["setups"]:
        az = round(_num(st["azimuth_deg"]) % 360.0, 1)
        out["setups"].append({"id": str(st["id"]).strip().upper(), "intent": str(st["intent"]).strip(), "why": str(st["why"]).strip(),
                              "azimuth_deg": az, "azimuth_orig": az, "angle": str(st["angle"]).lower(),
                              "tilt": str(st.get("tilt") or "level").lower(),
                              "landmark_in_frame": str(st.get("landmark_in_frame") or "any").lower(),
                              "crosses_axis_why": str(st.get("crosses_axis_why") or "").strip()})
    angle_of = {s["id"]: s["angle"] for s in out["setups"]}
    for sh in sorted(obj["shots"], key=lambda s: s["idx"]):
        setup = str(sh["setup"]).strip().upper()
        out["shots"].append({"idx": sh["idx"], "setup": setup, "size": str(sh["size"]).upper(),
                             "angle": str(sh.get("angle") or angle_of[setup]).lower(), "why": str(sh.get("why") or "").strip()})
    for key in ("props", "beats"):
        for item in obj.get(key) or []:
            if isinstance(item, dict) and _num(item.get("bearing_deg")) is not None:
                out[key].append(dict(item, bearing_deg=round(_num(item["bearing_deg"]) % 360.0, 1)))
    ax = obj["axis"]
    out["axis"] = {"from": str(ax.get("from") or ""), "to": str(ax.get("to") or ""), "bearing_deg": round(_num(ax["bearing_deg"]) % 360, 1),
                   "camera_side": str(ax["camera_side"]).lower(), "why": str(ax.get("why") or "")}
    return out


def camera_side(azimuth_deg: float, axis_deg: float) -> Optional[str]:
    """Which side of the axis line the camera of a set-up stands on (None = on the line, ≤ ON_AXIS_DEG). The camera stands opposite
    to what it looks at (in front of the character, or behind them over the shoulder): its bearing from the character = azimuth+180."""
    rel = ((float(azimuth_deg) + 180.0) - float(axis_deg)) % 360.0
    off = min(rel % 180.0, 180.0 - rel % 180.0)
    if off <= ON_AXIS_DEG:
        return None
    return "right" if rel < 180.0 else "left"


def check(plan: Dict, group: Dict) -> Tuple[Dict, List[str]]:
    """The code's rules on a normalized plan (returns a corrected copy + notes for diag). Corrects only what has one right answer
    (angle = the set-up's; a look-down shot gets a tilted-down copy of its set-up); reports the rest (axis, background family)."""
    from .plate_camera import looks_down
    plan = copy.deepcopy(plan)
    notes: List[str] = []
    setups = {s["id"]: s for s in plan["setups"]}
    data_of = {s["idx"]: s["data"] for s in group["shots"]}
    for sh in plan["shots"]:
        st = setups[sh["setup"]]
        if sh["angle"] != st["angle"]:
            notes.append(f"shot {sh['idx']}: angle '{sh['angle']}' khác angle của setup {st['id']} ('{st['angle']}') — cùng setup là "
                         f"cùng một máy nên dùng '{st['angle']}'")
            sh["angle"] = st["angle"]
    for sh in plan["shots"]:
        st = setups[sh["setup"]]
        data = dict(data_of.get(sh["idx"]) or {}, angle=sh["angle"])
        if looks_down(data) and st["angle"] not in LOOK_DOWN_ANGLES:
            new_id = f"{st['id']}-DOWN"
            if new_id not in setups:
                setups[new_id] = dict(st, id=new_id, angle="high", tilt="down", landmark_in_frame="no",
                                      intent=f"{st['intent']} — bản cúi (code tách)",
                                      why="shot nhìn xuống: người xem phải thấy cái nhân vật thấy, máy cao cúi xuống "
                                          "(máy ngang sẽ quay lên vật cao phía sau)")
                plan["setups"].append(setups[new_id])
            notes.append(f"shot {sh['idx']} nhìn xuống mà setup {st['id']} máy '{st['angle']}' (không cúi) — chuyển sang setup "
                         f"{new_id}: cùng phương vị {st['azimuth_deg']:g}°, máy cao cúi xuống")
            sh["setup"], sh["angle"] = new_id, "high"
    first = min(plan["shots"], key=lambda s: s["idx"])
    opening = setups[first["setup"]]
    plan["opening_setup"] = opening["id"]
    axis = plan["axis"]
    side_vi = {"left": "trái", "right": "phải"}
    for st in plan["setups"]:
        side = camera_side(st["azimuth_deg"], axis["bearing_deg"])
        st["camera_side"] = side
        if side is not None and side != axis["camera_side"] and not st.get("crosses_axis_why"):
            notes.append(f"setup {st['id']} ({st['intent']}): máy ở phía {side_vi[side]} trục {axis['bearing_deg']:g}° trong khi sơ đồ "
                         f"chọn phía {side_vi[axis['camera_side']]} — vượt trục 180° mà không ghi lý do (crosses_axis_why): người "
                         "xem sẽ thấy nhân vật đổi hướng nhìn")
        d_open = _angdiff(st["azimuth_deg"], opening["azimuth_deg"])
        d_rev = _angdiff(st["azimuth_deg"], opening["azimuth_deg"] + 180.0)
        st["family"] = "opening" if d_open <= FAMILY_DEG else ("reverse" if d_rev <= FAMILY_DEG else "other")
        if st["family"] == "other":
            notes.append(f"setup {st['id']} ({st['intent']}) nhìn {st['azimuth_deg']:g}° — lệch {d_open:.0f}° so với nền shot mở (setup "
                         f"{opening['id']} {opening['azimuth_deg']:g}°) và không phải hướng ngược: nền chưa giới thiệu cho người xem "
                         "(#24 shot 5/7) — giữ nếu kịch bản cần, ghi lý do ở `why`")
    lb = (group.get("facts") or {}).get("landmark_bearing_deg")
    if lb is None:
        lb = place_facts(group["entry"], group["spot"]).get("landmark_bearing_deg")
    for st in plan["setups"]:
        if lb is not None and st["landmark_in_frame"] == "yes" and _angdiff(st["azimuth_deg"], lb) > LANDMARK_OFF_DEG:
            notes.append(f"setup {st['id']} muốn thấy mốc nhưng nhìn lệch mốc {_angdiff(st['azimuth_deg'], lb):.0f}° (mốc ở {lb:g}°)")
    return plan, notes


def apply(conn, pid: int, group: Dict, plan: Dict) -> Dict:
    """Write the plan onto the shots: plate_setup, plate_view (bearing + why), size, angle (+ the `shot` words when they change). A field
    the person locked (`_user_locked`) is kept and listed. {"changed": {idx: [fields]}, "locked": {idx: [fields]}}."""
    from .shots import SIZE_WORDS
    setups = {s["id"]: s for s in plan["setups"]}
    by_idx = {s["idx"]: s for s in group["shots"]}
    changed: Dict[int, List[str]] = {}
    locked_out: Dict[int, List[str]] = {}
    resized: Dict[int, str] = {}
    apart: Dict[int, List[str]] = {}
    for sh in plan["shots"]:
        row = by_idx.get(sh["idx"])
        if row is None:
            continue
        cur = conn.execute("SELECT data FROM scenes WHERE id=?", (row["id"],)).fetchone()
        if cur is None:
            continue
        data = json.loads(cur["data"] or "{}")
        locked = set(data.get("_user_locked") or [])
        st = setups[sh["setup"]]
        sh["angle"] = st["angle"]                          # one set-up = one camera (a review fix changes the set-up's angle)
        why = f"setup {st['id']}: {st['intent']} — {st['why']}" + (f"; shot: {sh['why']}" if sh.get("why") else "")
        if st.get("crosses_axis_why"):
            why += f"; vượt trục có chủ đích: {st['crosses_axis_why']}"
        want = {SETUP_FIELD: st["id"], SCENE_FIELD: group["key"], "plate_view": {"background": st["azimuth_deg"], "why": why},
                "size": sh["size"], "angle": sh["angle"]}
        did = []
        own = [k for k in CAMERA_LOCKS if k in locked and data.get(k) != want[k]]
        if own:                                            # rà G0: the person's camera field wins — the shot keeps its own camera
            want.pop(SETUP_FIELD)
            want.pop(SCENE_FIELD)
            apart[sh["idx"]] = own
            for k in (SETUP_FIELD, SCENE_FIELD):           # a set-up left from an earlier plan would still share a camera
                if k in data and k not in locked:
                    data.pop(k)
                    did.append(k)
        for k, v in want.items():
            if data.get(k) == v:
                continue
            if k in locked:
                locked_out.setdefault(sh["idx"], []).append(k)
                continue
            if k == "size" and data.get("size"):
                resized[sh["idx"]] = f"{data['size']}→{v}"
            data[k] = v
            did.append(k)
        if {"size", "angle"} & set(did) and data.get("size") in SIZE_WORDS and "shot" in locked:
            locked_out.setdefault(sh["idx"], []).append("shot")     # rà G0: the person's own `shot` words are kept
        elif {"size", "angle"} & set(did) and data.get("size") in SIZE_WORDS:
            data["shot"] = (f"{SIZE_WORDS[data['size']]}, {data.get('angle') or 'eye'} angle, "
                            f"{str(data.get('camera_move') or 'static').replace('_', ' ')}")
        row["data"] = data
        if did:
            conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
            changed[sh["idx"]] = did
    conn.commit()
    return {"changed": changed, "locked": locked_out, "resized": resized, "apart": apart}


def _client(conn):
    from . import llm_runner
    try:
        return llm_runner.client_from_env(ledger=llm_runner.db_file(conn))
    except llm_runner.LlmError:
        return None


def _estimate(conn, stage: str, calls: int, images: int) -> str:
    from . import cost
    try:
        usd = cost.llm_estimate(conn, stage, calls, images=images)
    except Exception:  # noqa: BLE001 - a price table problem: said, never a reason to stop
        usd = None
    return f"≈ {usd * cost.LLM_MARGIN:.3f} USD" if usd is not None else "chưa có giá Claude"


def _say(conn, pid: int, sev: str, msg: str, code: str = CODE, log: Callable[[str], None] = lambda m: None) -> None:
    diag.record(conn, "director", sev, msg, code, pid)
    log(msg)


def _say_new(conn, pid: int, sev: str, msg: str, code: str = CODE, log: Callable[[str], None] = lambda m: None) -> None:
    """rà G0: a state said at every autopilot tick (no Claude, picture already drawn, estimate) is written once — again only when the
    words change (diag.record alone merges for 10 minutes, then a new row every tick)."""
    try:
        seen = conn.execute("SELECT 1 FROM diag_events WHERE project_id=? AND COALESCE(code,'')=? AND message=? LIMIT 1",
                            (pid, code or "", diag.redact(msg)[:400])).fetchone()
    except Exception:  # noqa: BLE001 - no diag table: say it
        seen = None
    if not seen:
        _say(conn, pid, sev, msg, code, log)
    else:
        log(msg)                                          # 09/10 chạy thật #24: the person at the CLI still reads why nothing ran


def before_plates(conn, pid: int, data_dir: str, client=None, force: bool = False,
                  log: Callable[[str], None] = lambda m: None) -> Optional[Dict]:
    """Step 1–2 of G0 for every scene at a 3D place without a plan (force = again). None when the flag is off. Never raises: a
    failure is said (diag) and the shots keep their own plate_view (the old flow)."""
    if not enabled():
        return None
    from . import llm_runner
    res: Dict = {"planned": [], "kept": [], "failed": [], "drawn": []}
    plans = load_plans(data_dir, pid)
    todo, res["kept"], drawn = todo_groups(conn, pid, data_dir, force)
    for key, idxs in drawn.items():                       # rà G0: a new camera would make a paid picture stale — said, not planned
        res["drawn"].append(key)
        _say_new(conn, pid, "warn", f"Cảnh {key}: shot {', '.join(map(str, idxs))} đã có ảnh — không lập sơ đồ máy (đổi máy làm ảnh "
                                    "đã vẽ lệch nền 3D); muốn lập lại cả cảnh: py tools/location_pack.py camera-plan --project "
                                    f"{pid} --yes --force", log=log)
    if not todo:
        return res
    client = client if client is not None else _client(conn)
    if client is None:
        _say_new(conn, pid, "warn", "Chưa cấu hình Claude (ANTHROPIC_API_KEY / LLM_PROVIDER) — Đạo diễn chưa lập sơ đồ cảnh + bộ góc máy "
                                f"(G0) cho {len(todo)} cảnh; nền 3D dùng plate_view từng shot như cũ", log=log)
        return res
    for g in todo:
        try:
            text, images, notes = build_prompt(conn, pid, g, data_dir)
        except Exception as e:  # noqa: BLE001
            _say(conn, pid, "error", f"Cảnh {g['key']}: không dựng được đề bài sơ đồ cảnh ({type(e).__name__}: {e})", log=log)
            res["failed"].append(g["key"])
            continue
        for n in notes:
            _say(conn, pid, "warn", f"Cảnh {g['key']} — thiếu đầu vào sơ đồ: {n}", log=log)
        _say(conn, pid, "info", f"Cảnh {g['key']}: Đạo diễn lập sơ đồ cảnh + bộ góc máy ({len(g['shots'])} shot, {len(images)} ảnh) — "
                                f"ước tính {_estimate(conn, STAGE, 1, len(images))} (tối đa ×{2 * MAX_TRIES} "
                                f"{_estimate(conn, STAGE, 2 * MAX_TRIES, len(images))} nếu Claude lỗi / trả lời sai mẫu)", log=log)
        idxs = [s["idx"] for s in g["shots"]]
        try:
            with llm_runner.tagged(STAGE, pid):
                obj, _, _ = llm_runner.ask_json(client, text, lambda o: validate(o, idxs), images)
        except Exception as e:  # noqa: BLE001 - Claude error / bad answer twice: the old flow goes on, said
            old = plans.get(g["key"])
            if old and not old.get("failed"):             # rà G0: a forced re-plan that fails keeps the good plan the shots use
                old["last_error"] = {"error": f"{type(e).__name__}: {e}", "at": time.time()}
                _save_plans(data_dir, pid, plans)
                _say(conn, pid, "error", f"Cảnh {g['key']}: lập lại sơ đồ cảnh lỗi ({type(e).__name__}: {e}) — giữ sơ đồ cũ", log=log)
                res["failed"].append(g["key"])
                continue
            tries = int((plans.get(g["key"]) or {}).get("tries") or 0) + 1
            plans[g["key"]] = {"failed": f"{type(e).__name__}: {e}", "tries": tries, "at": time.time()}
            _save_plans(data_dir, pid, plans)             # an autopilot tick never pays for the same failure for ever
            _say(conn, pid, "error", f"Cảnh {g['key']}: không lập được sơ đồ cảnh ({type(e).__name__}: {e}) — lần {tries}/{MAX_TRIES}; "
                                     "nền 3D dùng plate_view từng shot như cũ"
                                     + (" — hết lượt tự thử, chạy lại tay: py tools/location_pack.py camera-plan --project "
                                        f"{pid} --force" if tries >= MAX_TRIES else ""), log=log)
            res["failed"].append(g["key"])
            continue
        plan, checks = check(normalize(obj), g)
        for c in checks:
            _say(conn, pid, "warn", f"Cảnh {g['key']} — sơ đồ máy: {c}", log=log)
        applied = apply(conn, pid, g, plan)
        for idx, fields in applied["locked"].items():
            _say(conn, pid, "warn", f"Cảnh {g['key']} shot {idx}: giữ {', '.join(fields)} bạn đã sửa tay (sơ đồ muốn đổi) — máy của "
                                    "shot có thể lệch setup", log=log)
        for idx, fields in applied["apart"].items():
            _say(conn, pid, "warn", f"Cảnh {g['key']} shot {idx}: dùng máy riêng (không vào góc máy của sơ đồ) vì bạn đã khóa "
                                    f"{', '.join(fields)}", log=log)
        for idx, move in applied["resized"].items():
            _say(conn, pid, "warn", f"Cảnh {g['key']} shot {idx}: sơ đồ đổi cỡ cảnh {move} — prompt ảnh của shot có thể còn tả cỡ cũ, "
                                    "xem lại trước khi vẽ", log=log)
        plan.update(checks=checks, input_notes=notes, applied=applied, at=time.time(),
                    facts=place_facts(g["entry"], g["spot"]), place=g["place"]["name"], spot=g["spot"].get("name"))
        plans[g["key"]] = plan
        _save_plans(data_dir, pid, plans)
        res["planned"].append(g["key"])
        _say(conn, pid, "info", f"Cảnh {g['key']}: sơ đồ {len(plan['setups'])} góc máy ("
                                + ", ".join(f"{s['id']} {s['azimuth_deg']:g}° {s['angle']}" for s in plan["setups"])
                                + f"), {len(applied['changed'])} shot đổi hướng/cỡ/góc", log=log)
    return res


# ---- step 4: the Director looks at each set-up's render ---------------------------------------------------------------------
def judge(observations: Sequence[str], setup: Dict, is_opening: bool, opening_az: Optional[float],
          landmark_bearing: Optional[float]) -> Dict:
    """CODE decides from what the model SAW (it sees right but often concludes wrong). {"ok", "reasons", "fix"} — fix = {"angle"?,
    "azimuth_deg"?, "rotate"?} or None when nothing sure can be changed (then a person decides)."""
    obs = {str(o).strip().lower() for o in observations or []}
    known = {o for o in obs if o in OBSERVATIONS}
    clash = [f"{a} + {b}" for a, b in _CONTRADICT if a in known and b in known]
    if clash:
        return {"ok": False, "reasons": ["quan sát tự mâu thuẫn (" + "; ".join(clash) + ") — không đoán, để người xem"], "fix": None}
    if not known:
        return {"ok": False, "reasons": ["không có quan sát nào dùng được" + (f" ({', '.join(sorted(obs))})" if obs else "")],
                "fix": None}
    if "render_broken" in known:
        return {"ok": False, "reasons": ["render nền trống / hỏng — lỗi Blender hoặc mô hình, không phải góc máy"], "fix": None}
    reasons: List[str] = []
    fix: Dict = {}
    angle, tilt, lm = setup.get("angle"), setup.get("tilt") or "level", setup.get("landmark_in_frame") or "any"
    if "wall_near_blocking" in known:
        reasons.append("tường / vật chắn sát máy che khung" + (" (góc thấp sát tường chắn)" if angle == "low" else ""))
        if angle == "low":
            fix["angle"] = "eye"
        else:
            fix["rotate"] = True
    if tilt == "down":
        if "camera_tilted_down" not in known:
            reasons.append("ý đồ cúi nhìn xuống nhưng render không cúi")
            fix.setdefault("angle", "high" if angle not in ("high", "overhead") else "overhead")
        if "landmark_visible" in known and lm != "yes":
            reasons.append("đang cúi mà vẫn thấy tháp/mốc — nền phải là mặt đất quanh chỗ đứng")
            fix.setdefault("angle", "high" if angle not in ("high", "overhead") else "overhead")
    elif tilt == "level" and ({"camera_tilted_down", "camera_tilted_up"} & known):
        reasons.append("ý đồ máy ngang mà render " + ("cúi" if "camera_tilted_down" in known else "ngửa"))
        if angle != "eye":
            fix.setdefault("angle", "eye")
    elif tilt == "up" and "camera_tilted_down" in known:
        reasons.append("ý đồ ngửa (góc thấp) mà render cúi")
        if "wall_near_blocking" not in known:
            fix.setdefault("angle", "low")
    if "sky_dominant" in known and tilt != "up":
        reasons.append("trời chiếm hơn nửa khung")
        fix.setdefault("angle", "eye")
    if lm == "yes" and "landmark_not_visible" in known:
        reasons.append("ý đồ thấy mốc mà render không thấy mốc")
        if landmark_bearing is not None:
            fix.setdefault("azimuth_deg", float(landmark_bearing))
        else:
            fix["rotate"] = True
    if lm == "no" and "landmark_visible" in known and tilt != "down":
        reasons.append("ý đồ không thấy mốc mà render thấy mốc")
        fix["rotate"] = True
    if (not is_opening and opening_az is not None and _angdiff(setup.get("azimuth_deg", 0), opening_az) <= FAMILY_DEG
            and "background_differs_from_opening" in known):
        reasons.append("nền khác gia đình nền shot mở")
        fix.setdefault("azimuth_deg", float(opening_az))
    if not reasons:
        return {"ok": True, "reasons": [], "fix": None}
    if "azimuth_deg" in fix:
        fix.pop("rotate", None)
    return {"ok": False, "reasons": reasons, "fix": fix or None}


def _apply_fix(st: Dict, fix: Dict, round_no: int) -> str:
    before = f"{st['azimuth_deg']:g}° {st['angle']}"
    if "azimuth_deg" in fix:
        st["azimuth_deg"] = round(float(fix["azimuth_deg"]) % 360.0, 1)
    elif fix.get("rotate"):
        step = ROTATE_STEPS[min(round_no, len(ROTATE_STEPS)) - 1]
        st["azimuth_deg"] = round((float(st.get("azimuth_orig", st["azimuth_deg"])) + step) % 360.0, 1)
    if fix.get("angle"):
        st["angle"] = fix["angle"]
        if st["angle"] == "eye" and st.get("tilt") == "up":
            st["tilt"] = "level"
    return f"{before} → {st['azimuth_deg']:g}° {st['angle']}"


def review_prompt(setup: Dict, plan: Dict, facts: Dict, is_opening: bool, with_opening: bool) -> str:
    obs = "\n".join(f"- `{k}`: {v}" for k, v in OBSERVATIONS.items())
    return "\n".join([
        REVIEW_HEAD, "",
        f"Ảnh 1: render nền 3D của góc máy **{setup['id']}** — ý đồ: {setup['intent']} (vì {setup['why']}). Máy nhìn "
        f"{setup['azimuth_deg']:g}°, angle `{setup['angle']}`, tilt `{setup.get('tilt')}`. Mốc của bối cảnh: {facts.get('landmark')}.",
        ("Ảnh 2: render nền của shot MỞ cảnh (setup " + str(plan.get("opening_setup")) + ") để so gia đình nền." if with_opening else
         "Đây là góc máy của shot mở cảnh." if is_opening else "Không có render shot mở để so."),
        "",
        "Chỉ KHAI những gì THẤY trong ảnh, chọn trong danh sách dưới (không kết luận khớp hay không — code kết luận theo luật):",
        obs, "",
        "Trả lời MỘT khối JSON: {\"setup\": \"" + setup["id"] + "\", \"observations\": [\"…\"], \"note\": \"một câu tả ngắn tiếng Việt\"}",
    ])


def _validate_review(obj) -> Dict:
    from .llm_io import SchemaError
    if not isinstance(obj, dict) or not isinstance(obj.get("observations"), list):
        raise SchemaError("cần {\"observations\": [...]} ")
    return obj


def after_plates(conn, pid: int, data_dir: str, data_root: str, client=None, render: Optional[Callable] = None,
                 blender: Optional[str] = None, resolution=(1152, 2048), log: Callable[[str], None] = lambda m: None) -> Optional[Dict]:
    """Step 4 of G0: every set-up not reviewed yet gets one look (its render + the opening render), the code judges, a fault is fixed
    and rendered again (≤ MAX_REVIEW_ROUNDS), then the person is told. None when the flag is off."""
    if not enabled():
        return None
    from . import llm_runner, location_pack
    res: Dict = {"setups": {}, "needs_person": []}
    plans = load_plans(data_dir, pid)
    todo = [(k, st) for k, plan in plans.items() if not plan.get("failed")
            for st in plan.get("setups") or [] if not (st.get("review") or {}).get("done")]
    if not todo:
        return res
    client = client if client is not None else _client(conn)
    if client is None:
        _say_new(conn, pid, "warn", f"Chưa cấu hình Claude — Đạo diễn chưa xem render nền của {len(todo)} góc máy (G0)", REVIEW_CODE,
                 log)
        return res
    _say_new(conn, pid, "info", f"Đạo diễn xem render nền {len(todo)} góc máy — ước tính {_estimate(conn, REVIEW_STAGE, len(todo), 2)} "
                            f"(tối đa {_estimate(conn, REVIEW_STAGE, len(todo) * (1 + MAX_REVIEW_ROUNDS), 2)} nếu phải sửa)",
         REVIEW_CODE, log)
    by_key = {g["key"]: g for g in groups(conn, pid)}
    rerender = {"render": render} if render is not None else {}
    for key, plan in plans.items():
        g = by_key.get(key)
        if g is None or plan.get("failed"):
            continue
        sid_of = {s["idx"]: s["id"] for s in g["shots"]}
        setups = {s["id"]: s for s in plan["setups"]}
        opening = setups.get(plan.get("opening_setup"))
        facts = plan.get("facts") or place_facts(g["entry"], g["spot"])

        def first_shot(setup_id):
            idxs = sorted(sh["idx"] for sh in plan["shots"] if sh["setup"] == setup_id and sh["idx"] in sid_of)
            return sid_of[idxs[0]] if idxs else None

        for st in plan["setups"]:
            if (st.get("review") or {}).get("done"):
                continue
            sid = first_shot(st["id"])
            if sid is None:
                st["review"] = {"ok": False, "done": True, "reasons": ["không shot nào dùng góc này"], "rounds": 0}
                continue
            is_opening = opening is not None and st["id"] == opening["id"]
            prev = st.get("review") or {}                 # resumed after a render that was not ready: the rounds already paid count
            rounds, fixes = int(prev.get("rounds") or 0), list(prev.get("fixes") or [])
            while True:
                rec = location_pack.plate_of(data_dir, pid, sid)
                want_key = next((it["key"] for it in location_pack.plan(conn, pid, resolution) if it["scene_id"] == sid), None)
                stale = rec is not None and want_key is not None and rec.get("key") not in (None, want_key)
                if stale:
                    rec = None                                # rà G0: the index still holds the OLD camera's render — not looked at
                if rec is None:
                    why = ("render đang gắn là của máy cũ, chưa có render máy mới" if stale else
                           location_pack.plate_failed(data_dir, pid, sid) or location_pack.plate_needs(data_dir, pid, sid)
                           or "chưa render")
                    reasons = [f"chưa có render nền: {why}"]
                    if (prev.get("reasons") or []) != reasons:  # rà G0: said once per reason, not at every autopilot tick
                        _say(conn, pid, "warn", f"Cảnh {key} · góc {st['id']}: chưa xem được render nền ({why}) — xem lại sau khi "
                                                "render", REVIEW_CODE, log)
                    st["review"] = {"ok": False, "done": False, "rounds": rounds, "fixes": fixes, "tries": prev.get("tries"),
                                    "reasons": reasons}
                    break
                images = [(f"Ảnh 1 — render nền góc {st['id']}:", rec["plate"])]
                orec = None
                if not is_opening and opening is not None and first_shot(opening["id"]) is not None:
                    orec = location_pack.plate_of(data_dir, pid, first_shot(opening["id"]))
                    if orec is not None:
                        images.append((f"Ảnh 2 — render nền shot mở (góc {opening['id']}):", orec["plate"]))
                text = review_prompt(st, plan, facts, is_opening, orec is not None)
                try:
                    with llm_runner.tagged(REVIEW_STAGE, pid):
                        obj, _, _ = llm_runner.ask_json(client, text, _validate_review, images)
                except Exception as e:  # noqa: BLE001 - said; the set-up stays unreviewed (tried again next time)
                    tries = int((st.get("review") or {}).get("tries") or 0) + 1
                    st["review"] = {"ok": False, "done": tries >= MAX_TRIES, "rounds": rounds, "tries": tries, "fixes": fixes,
                                    "reasons": [f"Claude lỗi: {type(e).__name__}: {e}"]}
                    if tries >= MAX_TRIES:
                        res["needs_person"].append(f"{key}·{st['id']}")
                    _say(conn, pid, "error", f"Cảnh {key} · góc {st['id']}: Đạo diễn không xem được render ({type(e).__name__}: {e}) — "
                                             f"lần {tries}/{MAX_TRIES}" + (" — dừng tự thử, cần bạn xem render" if tries >= MAX_TRIES
                                                                           else ""), REVIEW_CODE, log)
                    break
                obs = [str(o) for o in obj.get("observations") or []]
                verdict = judge(obs, st, is_opening, opening["azimuth_deg"] if opening else None, facts.get("landmark_bearing_deg"))
                if verdict["ok"]:
                    st["review"] = {"ok": True, "done": True, "rounds": rounds, "observations": obs, "fixes": fixes,
                                    "note": str(obj.get("note") or ""), "plate": rec["plate"]}
                    _say(conn, pid, "info", f"Cảnh {key} · góc {st['id']} ({st['intent']}): render nền khớp ý đồ"
                                            + (f" sau {rounds} vòng sửa" if rounds else ""), REVIEW_CODE, log)
                    break
                if verdict["fix"] is None or rounds >= MAX_REVIEW_ROUNDS:
                    st["review"] = {"ok": False, "done": True, "rounds": rounds, "observations": obs, "fixes": fixes,
                                    "reasons": verdict["reasons"], "note": str(obj.get("note") or ""), "plate": rec["plate"]}
                    res["needs_person"].append(f"{key}·{st['id']}")
                    _say(conn, pid, "error", f"Cảnh {key} · góc {st['id']} ({st['intent']}): render nền vẫn không khớp ý đồ sau {rounds} "
                                             f"vòng sửa — {'; '.join(verdict['reasons'])} — CẦN BẠN QUYẾT (đổi phương vị/cỡ ở sơ đồ "
                                             f"{plan_path(data_dir, pid)} hoặc chỉnh tay plate_view), xem {rec['plate']}",
                         REVIEW_CODE, log)
                    break
                rounds += 1
                change = _apply_fix(st, verdict["fix"], rounds)
                fixes.append({"round": rounds, "reasons": verdict["reasons"], "change": change, "observations": obs})
                _say(conn, pid, "info", f"Cảnh {key} · góc {st['id']}: không khớp ({'; '.join(verdict['reasons'])}) → sửa {change} "
                                        f"(vòng {rounds}/{MAX_REVIEW_ROUNDS}), render lại (0 USD)", REVIEW_CODE, log)
                apply(conn, pid, g, plan)
                try:
                    location_pack.ensure_plates(conn, pid, data_dir, data_root, resolution, blender=blender, log=log, **rerender)
                except Exception as e:  # noqa: BLE001 - said; never a paid look at the OLD render (rà G0)
                    st["review"] = {"ok": False, "done": False, "rounds": rounds, "fixes": fixes, "tries": prev.get("tries"),
                                    "reasons": [f"render lại lỗi: {type(e).__name__}: {e}"]}
                    _say(conn, pid, "error", f"Cảnh {key} · góc {st['id']}: render lại lỗi ({type(e).__name__}: {e}) — chưa xem lại "
                                             "(không trả tiền xem render cũ), thử lại ở lượt sau", REVIEW_CODE, log)
                    break
            res["setups"].setdefault(key, {})[st["id"]] = st.get("review")
            _save_plans(data_dir, pid, plans)
    return res


# ---- mock (LLM_PROVIDER=mock) -----------------------------------------------------------------------------------------------
def mock_answer(prompt: str) -> Dict:
    """A valid plan for the fake model: one set-up towards the landmark (or 0°) for every shot of the scene, sizes kept."""
    import re
    blocks = re.findall(r"```json\s*(.*?)```", prompt, re.S)
    facts = json.loads(blocks[-2]) if len(blocks) >= 2 else {}
    shots = json.loads(blocks[-1]) if blocks else []
    az = float(facts.get("landmark_bearing_deg") or 0.0)
    return {"props": [], "beats": [], "axis": {"from": "nhân vật", "to": "mốc", "bearing_deg": az, "camera_side": "left", "why": "giả lập"},
            "setups": [{"id": "A", "intent": "toàn cảnh về mốc (giả lập)", "why": "giả lập", "azimuth_deg": az, "angle": "eye",
                        "tilt": "level", "landmark_in_frame": "any"}],
            "shots": [{"idx": s["idx"], "setup": "A", "size": str(s.get("size") or "MS").upper(), "angle": "eye", "why": "giả lập"}
                      for s in shots]}


def mock_review(prompt: str) -> Dict:
    return {"observations": ["camera_level", "background_same_as_opening"], "note": "giả lập"}
