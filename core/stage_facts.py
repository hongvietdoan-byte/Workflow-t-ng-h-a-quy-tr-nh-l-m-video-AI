"""Sự thật hình học của một shot có máy Sân khấu 3D (`stage_camera`) — MỘT nguồn, BA nơi dùng (người dùng 10/10, #24 shot 4 + 8).

Gốc lỗi: máy đã giải bằng code (location, look_at, lens, props) nhưng sự thật hình học không chảy sang các nơi dùng nó; mỗi nơi có
"niềm tin" riêng và mâu thuẫn: (1) prompt ảnh Director viết tay ("its dark mouth facing us" khi máy thấp hơn miệng giếng), (2) ảnh mẫu
Kho chụp từ trên nhìn xuống → model chép góc nhìn của ảnh mẫu, (3) QC hỏi Claude PHÁN XÉT ("place ok?") → model nhìn mà suy luận sai.

Sổ `FACTS`: mỗi loại sự thật =
  derive(ctx)        → [fact]  code tính từ stage_camera + vật (không model, 0 USD)
  prompt(fact, ctx)  → câu tiếng Anh nối vào prompt ảnh (code nối, không qua Director); "" = loại này không cần câu
  observe            → {"options": (... "unsure"), "question": fn(fact)} — model chỉ KHAI điều thấy (enum)
  judge(fact, seen)  → None (khớp) / "vang" (cần xem) / "do" (chắc chắn sai) — code so khai báo ↔ sự thật
  contradicts(fact)  → [regex] cụm chữ trong prompt Director trái sự thật (chỉ khi sự thật làm chúng sai)
Nơi dùng: core/runner.build_image_prompt (khối câu cuối prompt), core/change_audit (câu Director trái sự thật → mục 'cau' đỏ),
core/qc_spec.compile_frame (mệnh đề 'geometry' cho Tổ QC) + core/qc_scene (khối "Khai điều thấy" của QC lớp 1),
core/plate_layout_qc (chân trời giải tích thay đo mù trên render đêm).
Quy tắc: lỗi người dùng bắt mà QC lọt → thêm LOẠI / CA VÀNG vào đây (tests/golden/cases/<id>.json, định dạng tests/golden/README.md), không vá prompt.
Không có stage_camera → không sinh sự thật nào, nói rõ lý do (`missing`), không đoán.
"""
import math
import re
from typing import Callable, Dict, List, Optional, Sequence

from . import stage_grid as sg

ASPECT = 9 / 16            # khung dọc mặc định (place_refs.resolution_of: deepix 1152x2048) — render_plates cùng tỉ lệ
EPS_M = 0.05               # máy cách đỉnh vật < 5 cm: coi như ngang mép — không kết luận thấy / không thấy lòng
SURE_IN_PCT = 80.0         # vật thấy ≥ 80 % điểm phủ: "không có trong khung" là chắc chắn sai
THIRD_EDGE = 0.05          # cách ranh một phần ba < 0,05 khung: chấp nhận cả hai vùng
STAND_IN_KINDS = {"well"}  # tools/render_plates.add_props chỉ dựng khối thay thế cho các loại này
KIND_EN = {"well": "stone well"}
KIND_WORDS = {"well": ("well", "gieng")}     # tìm vật Kho cùng loại (tên / tên khác / mô tả, bỏ dấu)
UNSURE = "unsure"
LEVELS = (None, "vang", "do")


def _fold(text: str) -> str:
    return sg.fold(text)


# ---- ngữ cảnh -----------------------------------------------------------------------------------------------------------------
def stage_of(data: Dict, end: bool = False) -> Optional[Dict]:
    """{cam, aim, lens, props} từ data['stage_camera'] (end=True: khung cuối của máy chuyển động khi có move.end_*). None khi thiếu."""
    sc = (data or {}).get("stage_camera")
    if not isinstance(sc, dict):
        return None
    try:
        cam = [float(v) for v in sc["location"]]
        aim = [float(v) for v in sc["look_at"]]
        lens = float(sc["lens"])
        mv = sc.get("move") if isinstance(sc.get("move"), dict) else {}
        if end and mv.get("end_location") and mv.get("end_look_at"):
            cam = [float(v) for v in mv["end_location"]]
            aim = [float(v) for v in mv["end_look_at"]]
    except (KeyError, TypeError, ValueError):
        return None
    if len(cam) != 3 or len(aim) != 3 or lens <= 0:
        return None
    props = []
    for i, p in enumerate(sc.get("props") or []):
        try:
            props.append({"i": i, "kind": str(p.get("kind") or "prop"), "at": [float(v) for v in p["at"]], "radius": float(p["radius"]),
                          "height": float(p["height"]), "hollow": bool(p.get("hollow")), "sides": int(p.get("sides") or 0)})
        except (KeyError, TypeError, ValueError):
            continue
    return {"cam": cam, "aim": aim, "lens": lens, "props": props}


def missing_reason(data: Dict) -> Optional[str]:
    """Vì sao shot không có sự thật hình học (None = có)."""
    if not isinstance((data or {}).get("stage_camera"), dict):
        return "shot không có máy Sân khấu 3D (stage_camera) — không sinh sự thật hình học, không đoán"
    if stage_of(data) is None:
        return "stage_camera thiếu location / look_at / lens hợp lệ — không sinh sự thật hình học"
    return None


def _subject(p: Dict) -> str:
    return p["kind"] if p["i"] == 0 else f"{p['kind']}{p['i'] + 1}"


def _name(p: Dict, objects: Dict) -> str:
    return KIND_EN.get(p["kind"], p["kind"].replace("_", " "))


def _obj(p: Dict) -> Dict:
    """Prop → vật của stage_grid (trụ: đáy, giữa, miệng × tâm + 4 điểm vành) — dùng lại phép chiếu sẵn có, không viết lại."""
    return {"kind": "dao_cu", "xy": p["at"][:2], "z": p["at"][2], "h": p["height"], "r": p["radius"]}


def _third(u: float) -> str:
    return "left_third" if u < 1 / 3 else ("middle_third" if u < 2 / 3 else "right_third")


def _thirds_ok(u: float) -> List[str]:
    out = {_third(u)}
    for edge in (1 / 3, 2 / 3):
        if abs(u - edge) < THIRD_EDGE:
            out |= {_third(edge - 0.01), _third(edge + 0.01)}
    return sorted(out)


def _framing(ctx: Dict) -> Dict[str, Dict]:
    """frame_eval của mọi prop (một lần mỗi ngữ cảnh)."""
    if "_fe" not in ctx:
        objs = {_subject(p): _obj(p) for p in ctx["props"]}
        ctx["_fe"] = sg.frame_eval(ctx["cam"], ctx["aim"], ctx["lens"], ctx["aspect"], objs)["obj"] if objs else {}
    return ctx["_fe"]


def _fact(kind: str, subject: str, value, numbers: Dict, **kw) -> Dict:
    return {"kind": kind, "subject": subject, "id": f"{kind}:{subject}", "value": value, "numbers": numbers, **kw}


# ---- top_visible: thấy mặt trên / lòng của vật rỗng (giếng) hay chỉ thành ngoài --------------------------------------------------
def _derive_top(ctx: Dict) -> List[Dict]:
    out = []
    fe = _framing(ctx)
    for p in ctx["props"]:
        if not p["hollow"]:
            continue
        top = p["at"][2] + p["height"]
        cam_h = ctx["cam"][2] - p["at"][2]
        above = ctx["cam"][2] - top
        if abs(above) < EPS_M:
            continue                                   # ngang mép: không chắc — không sinh sự thật (không đoán)
        d = math.hypot(ctx["cam"][0] - p["at"][0], ctx["cam"][1] - p["at"][1])
        down = math.degrees(math.atan2(above, max(d, 0.01)))
        e = fe.get(_subject(p)) or {}
        out.append(_fact("top_visible", _subject(p), above > 0,
                         {"cam_above_ground_m": round(cam_h, 2), "rim_m": round(p["height"], 2), "cam_minus_rim_m": round(above, 2),
                          "dist_m": round(d, 2), "look_down_deg": round(down, 1), "in_pct": e.get("in_pct", 0.0)},
                         name=_name(p, ctx["objects"]), in_frame=bool(e.get("in_pct")), rim_in_frame=_rim_in_frame(ctx, p)))
    return out


def _rim_in_frame(ctx: Dict, p: Dict) -> bool:
    """Có điểm vành (miệng: tâm + 4 điểm mép ở đỉnh) nào trong khung — chỉ thấy chân thành giếng thì không nói gì về miệng."""
    top = [q for q in sg.object_points(_obj(p)) if abs(q[2] - (p["at"][2] + p["height"])) < 1e-6]
    return any(sg.in_frame(sg.project(ctx["cam"], ctx["aim"], q, ctx["lens"], ctx["aspect"])) for q in top)


def _prompt_top(f: Dict, ctx: Dict) -> str:
    n, x = f["name"], f["numbers"]
    if not f["in_frame"] or not f.get("rim_in_frame", True):
        return ""
    if not f["value"]:
        return (f"Camera height: the camera is {x['cam_above_ground_m']:.2f} m above the ground, LOWER than the {n} rim "
                f"({x['rim_m']:.2f} m high): only the outer wall of the {n} is visible, its top edge seen edge-on against the background — "
                f"the opening and the inside of the {n} are NOT visible from this height.")
    thin = " as a thin ellipse" if x["look_down_deg"] < 15 else ""
    return (f"Camera height: the camera is {x['cam_minus_rim_m']:.2f} m above the {n} rim and looks down on it at about "
            f"{x['look_down_deg']:.0f} degrees: the top of the rim and the dark opening are visible{thin}, the far inner wall only.")


def _judge_top(f: Dict, seen: str) -> Optional[str]:
    if seen == "not_in_frame":
        return "do" if f["in_frame"] and f["numbers"].get("in_pct", 0) >= SURE_IN_PCT else ("vang" if f["in_frame"] else None)
    if f["value"]:
        return None if seen in ("inside_visible", "only_outer_wall") else "vang"   # nhìn từ trên rất xiên: thành ngoài là chính — không đỏ
    return "do" if seen == "inside_visible" else None


# 10/10 (rà kỹ): "looking into the camera" / "staring into the distance" / "gazes into the fog, the old well at her back" từng bị bắt
# đỏ (giữ gen + dừng autopilot) — chỉ khớp khi tân ngữ của "into" là CHÍNH vật / lòng vật; "dark mouth" phải gắn với tên vật.
_INNER = r"(opening|mouth|hole|interior|inside|depths?)"
_DARK = rf"dark {_INNER}"
_NEG = re.compile(r"\b(hidden|not|no|never|without|cannot|can't)\b")


def _inside_patterns(words: Sequence[str]) -> List[str]:
    w = "(" + "|".join(re.escape(x) for x in words) + ")"
    return [r"\bmouth\b[^.;]{0,40}\bfacing (us|the camera|camera|the viewer)\b",
            rf"\b(look|peer|see|gaz|star)\w*\s+(straight\s+)?(down\s+)?into\s+(the|its)\s+(\w+\s+){{0,2}}({w}|{_INNER})\b",
            rf"\b{w}\b('s)?\W+(\w+\W+){{0,6}}?{_DARK}\b|\b{_DARK}\W+(\w+\W+){{0,6}}?{w}\b|\bits {_DARK}\b",
            rf"\b(inside|interior|depths?) of (the|its) ([a-z]+ ){{0,2}}{w}\b",
            r"\b(top[- ]down|bird'?s[- ]eye|overhead view)\b"]


def _contra_top(f: Dict) -> List[str]:
    return [] if f["value"] else _inside_patterns(KIND_WORDS.get(f["subject"].rstrip("0123456789"), (f["name"].split()[-1],)))


# ---- stand_in: khối thay thế tám cạnh trong render nền phải vẽ thành vật thật -------------------------------------------------
def _derive_stand_in(ctx: Dict) -> List[Dict]:
    fe = _framing(ctx)
    out = []
    for p in ctx["props"]:
        if p["kind"] not in STAND_IN_KINDS:
            continue
        e = fe.get(_subject(p)) or {}
        if not e.get("in_pct"):
            continue                                    # khối không lọt khung: không có gì phải dặn
        o = ctx["objects"].get(p["kind"]) or {}
        out.append(_fact("stand_in", _subject(p), True, {"in_pct": e["in_pct"], "sides": p["sides"]}, name=_name(p, ctx["objects"]),
                         library=o.get("name"), library_desc=o.get("desc_en") or "", in_frame=True))
    return out


def _prompt_stand_in(f: Dict, ctx: Dict) -> str:
    if not ctx.get("render", True):
        return ""                                       # không gửi render: không có khối xám nào để dặn (rà kỹ 10/10)
    sides = {8: "eight-sided", 6: "six-sided"}.get(f["numbers"].get("sides"), "plain")
    lib = f" (the library object \"{f['library']}\"{': ' + f['library_desc'] if f['library_desc'] else ''})" if f.get("library") else ""
    return (f"The grey {sides} block in the background render is a placeholder: draw it as the {f['name']}{lib}, real weathered "
            f"stone, not a flat block — the same place and size as the block.")


def _judge_stand_in(f: Dict, seen: str) -> Optional[str]:
    if seen == "flat_plain_block":
        return "do"
    if seen == "not_in_frame":
        return "vang" if f["numbers"].get("in_pct", 0) >= SURE_IN_PCT else None
    return None


# ---- in_frame: vật trong khung, vùng một phần ba, tỉ lệ khung ---------------------------------------------------------------
def _derive_in_frame(ctx: Dict) -> List[Dict]:
    out = []
    for subj, e in _framing(ctx).items():
        p = next(x for x in ctx["props"] if _subject(x) == subj)
        uv = e.get("uv")
        third = _third(uv[0]) if uv else "not_in_frame"
        out.append(_fact("in_frame", subj, third, {"in_pct": e["in_pct"], "u": uv[0] if uv else None, "v": uv[1] if uv else None,
                                                   "size_pct": e.get("size_pct")},
                         name=_name(p, ctx["objects"]), accept=_thirds_ok(uv[0]) if uv else ["not_in_frame"],
                         in_frame=bool(e["in_pct"])))
    return out


def _prompt_in_frame(f: Dict, ctx: Dict) -> str:
    x = f["numbers"]
    if not f["in_frame"]:
        return f"The {f['name']} is outside this frame (not visible)."
    where = {"left_third": "left third", "middle_third": "middle third", "right_third": "right third"}[f["value"]]
    part = "" if x["in_pct"] >= SURE_IN_PCT else ", only partly inside the frame"
    size = f", about {abs(x['size_pct']):.0f}% of the frame height" if x.get("size_pct") is not None and x["in_pct"] >= SURE_IN_PCT else ""
    tail = ", exactly where the render shows it" if ctx.get("render", True) else ""
    return f"The {f['name']} sits in the {where} of the frame{part}{size}{tail}."


def _judge_in_frame(f: Dict, seen: str) -> Optional[str]:
    x = f["numbers"]
    if seen in f["accept"]:
        return None
    if f["value"] == "not_in_frame":
        return "vang"                                   # vẽ thêm vật máy không thấy: cần xem, không chắc là lỗi khung
    if seen == "not_in_frame":
        return "do" if x["in_pct"] >= SURE_IN_PCT else "vang"
    opposite = {"left_third": "right_third", "right_third": "left_third"}.get(f["value"])
    return "do" if seen == opposite and x["in_pct"] >= SURE_IN_PCT else "vang"


# ---- pitch_horizon: góc cúi / ngửa + hàng chân trời (giải tích từ pitch + FOV) ----------------------------------------------
def horizon(cam: Sequence[float], aim: Sequence[float], lens: float, aspect: float = ASPECT) -> Dict:
    """{"pitch_deg", "w" (0 = mép trên), "third"} — sg.horizon_w (cùng công thức plate_camera.horizon_y / render_plates)."""
    _, pitch = sg.look(cam, aim)
    w = sg.horizon_w(pitch, lens, aspect)
    third = ("horizon_above_frame" if w < 0 else "horizon_below_frame" if w > 1
             else "horizon_top_third" if w < 1 / 3 else "horizon_middle_third" if w < 2 / 3 else "horizon_bottom_third")
    return {"pitch_deg": round(pitch, 1), "w": round(w, 3), "third": third}


def _derive_horizon(ctx: Dict) -> List[Dict]:
    h = horizon(ctx["cam"], ctx["aim"], ctx["lens"], ctx["aspect"])
    accept = {h["third"]}
    for edge, a, b in ((1 / 3, "horizon_top_third", "horizon_middle_third"), (2 / 3, "horizon_middle_third", "horizon_bottom_third"),
                       (0.0, "horizon_above_frame", "horizon_top_third"), (1.0, "horizon_bottom_third", "horizon_below_frame")):
        if abs(h["w"] - edge) < THIRD_EDGE:
            accept |= {a, b}
    return [_fact("pitch_horizon", "camera", h["third"], h, accept=sorted(accept), in_frame=True)]


def _prompt_horizon(f: Dict, ctx: Dict) -> str:
    x = f["numbers"]
    p = x["pitch_deg"]
    tilt = "level" if abs(p) < 3 else (f"tilted down about {-p:.0f} degrees" if p < 0 else f"tilted up about {p:.0f} degrees")
    line = {"horizon_above_frame": "the horizon is above the top edge of the frame: the frame shows ground, no sky line",
            "horizon_below_frame": "the horizon is below the bottom edge of the frame: the frame shows sky and tall things only",
            }.get(f["value"], f"the horizon line (eye level of the camera) sits about {x['w'] * 100:.0f}% down from the top of the frame")
    tail = ", as in the render" if ctx.get("render", True) else ""
    return f"Camera tilt: {tilt}; {line}{tail}."


_HORIZON_ORDER = ("horizon_above_frame", "horizon_top_third", "horizon_middle_third", "horizon_bottom_third", "horizon_below_frame")


def _judge_horizon(f: Dict, seen: str) -> Optional[str]:
    if seen in f["accept"] or seen == "horizon_not_visible" or seen not in _HORIZON_ORDER:
        return None                                    # chân trời bị nhà / sương che là bình thường
    # rà kỹ 10/10: vàng chỉ khi khai TRÁI HẲN (cách ≥ 2 vùng, vd đúng 'trên khung' mà khai 'một phần ba dưới') — lệch một vùng là mái
    # nhà / sương bị khai nhầm là chân trời, không biến mọi khung đêm thành doubt
    gap = min(abs(_HORIZON_ORDER.index(seen) - _HORIZON_ORDER.index(a)) for a in f["accept"] if a in _HORIZON_ORDER)
    return "vang" if gap >= 2 else None


UNSURE_QUIET = {"pitch_horizon"}   # khai 'unsure' chân trời (đêm sương) không làm vàng — loại khác: unsure vẫn vàng


# ---- ref_viewpoint: ảnh mẫu Kho chỉ cho dáng / chất liệu, không cho góc máy -------------------------------------------------
def _derive_ref_view(ctx: Dict) -> List[Dict]:
    out = []
    for f in _derive_top(ctx):
        p = next(x for x in ctx["props"] if _subject(x) == f["subject"])
        o = ctx["objects"].get(p["kind"]) or {}
        if f["value"] is False and f["in_frame"] and o.get("has_picture"):
            out.append(_fact("ref_viewpoint", f["subject"], "differs", {"cam_minus_rim_m": f["numbers"]["cam_minus_rim_m"]},
                             name=f["name"], library=o.get("name"), in_frame=True))
    return out


def _prompt_ref_view(f: Dict, ctx: Dict) -> str:
    return (f"The reference picture of the {f['name']} shows its look and material only, not the camera angle: draw it from this "
            f"frame's low camera, not from above as in that picture.")


def _judge_ref_view(f: Dict, seen: str) -> Optional[str]:
    return "vang" if seen == "copied_reference_angle" else None   # đỏ do top_visible quyết (cùng một lỗi, không đếm hai lần)


FACTS: Dict[str, Dict] = {
    "top_visible": {
        "derive": _derive_top, "prompt": _prompt_top, "judge": _judge_top, "contradicts": _contra_top,
        "observe": {"options": ("inside_visible", "only_outer_wall", "not_in_frame", UNSURE),
                    "question": lambda f: f"The {f['name']}: can you see INTO it (its opening / inside), or only its outer wall?"}},
    "stand_in": {
        "derive": _derive_stand_in, "prompt": _prompt_stand_in, "judge": _judge_stand_in, "contradicts": lambda f: [],
        "observe": {"options": ("drawn_as_real_object", "flat_plain_block", "not_in_frame", UNSURE),
                    "question": lambda f: f"The {f['name']}: is it drawn as a real {f['name']} (stones, texture) or as a flat plain block?"}},
    "in_frame": {
        "derive": _derive_in_frame, "prompt": _prompt_in_frame, "judge": _judge_in_frame, "contradicts": lambda f: [],
        "observe": {"options": ("left_third", "middle_third", "right_third", "not_in_frame", UNSURE),
                    "question": lambda f: f"Where is the {f['name']} in the picture (by its centre)?"}},
    "pitch_horizon": {
        "derive": _derive_horizon, "prompt": _prompt_horizon, "judge": _judge_horizon, "contradicts": lambda f: [],
        "observe": {"options": ("horizon_top_third", "horizon_middle_third", "horizon_bottom_third", "horizon_above_frame",
                                "horizon_below_frame", "horizon_not_visible", UNSURE),
                    "question": lambda f: "Where is the horizon line (far ground meets sky / far distance) in the picture?"}},
    "ref_viewpoint": {
        "derive": _derive_ref_view, "prompt": _prompt_ref_view, "judge": _judge_ref_view, "contradicts": lambda f: [],
        "observe": {"options": ("copied_reference_angle", "frame_camera_angle", "not_in_frame", UNSURE),
                    "question": lambda f: f"The {f['name']}: is it seen from high above (like a top-down product photo) or from this "
                                          f"frame's own low camera?"}},
}
REQUIRED = ("derive", "prompt", "observe", "judge", "contradicts")


# ---- API --------------------------------------------------------------------------------------------------------------------
def context(data: Dict, objects: Optional[Dict] = None, aspect: float = ASPECT, end: bool = False,
            render: bool = True) -> Optional[Dict]:
    st = stage_of(data, end=end)
    if st is None:
        return None
    return dict(st, aspect=float(aspect or ASPECT), objects=objects or {}, render=bool(render))


def derive(data: Dict, objects: Optional[Dict] = None, aspect: float = ASPECT, end: bool = False, render: bool = True) -> Dict:
    """{"facts": [...], "missing": lý do hoặc None}. Mỗi fact có prompt (câu) + question/options (khai) + contradicts (regex).
    render=False: ảnh không kèm render 3D của shot → câu không nhắc 'the render' / khối xám thay thế (rà kỹ 10/10)."""
    why = missing_reason(data)
    ctx = None if why else context(data, objects, aspect, end, render)
    if ctx is None:
        return {"facts": [], "missing": why or "không dựng được ngữ cảnh máy"}
    facts = []
    for kind, spec in FACTS.items():
        for f in spec["derive"](ctx):
            f["prompt"] = spec["prompt"](f, ctx)
            f["question"] = spec["observe"]["question"](f)
            f["options"] = list(spec["observe"]["options"])
            f["contradicts"] = spec["contradicts"](f)
            facts.append(f)
    return {"facts": facts, "missing": None}


def prompt_block(facts: List[Dict]) -> str:
    lines = [f["prompt"] for f in facts if f.get("prompt")]
    if not lines:
        return ""
    return "Geometry of this camera (computed from the 3D stage, overrides any other words about it): " + " ".join(lines)


def judge(f: Dict, seen: Optional[str]) -> Optional[str]:
    """Khai báo của model → None / 'vang' / 'do'. Thiếu / 'na' / ngoài danh sách = 'unsure' → 'vang' (không im lặng)."""
    seen = seen if seen in FACTS[f["kind"]]["observe"]["options"] else UNSURE
    if seen == UNSURE:
        return None if f["kind"] in UNSURE_QUIET else "vang"
    level = FACTS[f["kind"]]["judge"](f, seen)
    assert level in LEVELS, level
    return level


def emphasis(f: Dict) -> str:
    """Câu sửa NHẤN MẠNH khác câu sự thật (câu sự thật đã có trong prompt mà model vẫn vẽ sai — vẽ lại cùng câu là cùng đầu vào,
    rà kỹ 10/10 lỗi 4). "" khi loại này không có câu nhấn mạnh riêng."""
    n, x = f.get("name") or f["subject"], f.get("numbers") or {}
    if f["kind"] == "top_visible" and not f["value"]:
        return (f"Camera at knee height ({x.get('cam_above_ground_m', 0):.2f} m), the {n} rim ABOVE the lens: draw the {n} side-on as "
                f"a solid stone wall whose top edge is a straight line — no opening, no dark hole, nothing of its inside.")
    if f["kind"] == "top_visible":
        return f"Camera ABOVE the {n} rim: the top surface of the rim must be seen from above, as a ring."
    if f["kind"] == "stand_in":
        return f"Never a smooth plain block: the {n} is built of separate rough stones with visible joints and moss."
    if f["kind"] == "in_frame" and f["value"] != "not_in_frame":
        return f"Put the {n} in the {f['value'].replace('_', ' ')} of the frame, not elsewhere."
    if f["kind"] == "ref_viewpoint":
        return f"Do not copy the camera angle of the {n} reference picture: low camera, side view."
    return ""


def _sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.;!?])\s+|\n+", str(text or "")) if s.strip()]


def contradictions(text: str, facts: List[Dict]) -> List[Dict]:
    """Câu Director trái sự thật: [{fact, phrase, sentence, level, fix}]. Chỉ khi câu đó nhắc tới chính vật (tên loại, vd 'well') —
    'dark opening' của một cửa nhà không bị bắt nhầm. Đỏ chỉ khi vật lọt khung (in_frame) — không thì vàng."""
    out = []
    for f in facts:
        if not f.get("contradicts"):
            continue
        words = KIND_WORDS.get(f["subject"].rstrip("0123456789"), (f["name"].split()[-1],))
        for s in _sentences(text):
            low = s.lower()
            # the noun itself — not "well-lit" / "as well" (a false red would hold the shot's paid generation)
            if not any(re.search(rf"(?<!\bas )\b{re.escape(w)}\b(?!-)", low) for w in words):
                continue
            for pat in f["contradicts"]:
                if _DARK in pat and _NEG.search(low):
                    continue                           # "its dark mouth hidden / not visible": câu phủ định, không trái sự thật
                m = re.search(pat, low)
                if m:
                    out.append({"fact": f["id"], "phrase": m.group(0), "sentence": s.strip()[:300],
                                "level": "do" if f.get("in_frame") else "vang", "fix": f.get("prompt") or ""})
                    break
    return out


# ---- đọc Kho (một lần mỗi shot) -------------------------------------------------------------------------------------------
def library_objects(conn, pid: int, props: List[Dict]) -> Dict[str, Dict]:
    """{loại prop: {"name", "desc_en", "has_picture"}} — vật Kho (đồ vật, đã gắn dự án) cùng loại theo tên / tên khác / mô tả. Không
    tìm được → không có mục (câu dùng tên loại tiếng Anh, nói rõ ở `note_missing_library`)."""
    if conn is None or not props:
        return {}
    from . import assets
    try:
        objs = [a for a in assets.project_assets(conn, pid) if a.get("kind") in assets.SIZED_KINDS]
    except Exception:  # noqa: BLE001 - bảng thiếu (test / CSDL cũ): không có vật Kho
        return {}
    out = {}
    for p in props:
        words = KIND_WORDS.get(p["kind"], (p["kind"],))
        for a in objs:
            hay = _fold(" ".join(str(a.get(k) or "") for k in ("name", "aliases", "description")))
            if any(re.search(rf"(?<!\bas )\b{w}\b(?!-)", hay) for w in words):
                desc = str(a.get("description") or "")
                out[p["kind"]] = {"name": a.get("name"), "desc_en": desc[:120] if desc.isascii() else "",
                                  "has_picture": bool(a.get("images"))}
                break
    return out


def for_shot(conn, pid: int, data: Dict, aspect: Optional[float] = None, end: bool = False, render: bool = True) -> Dict:
    """derive() với vật Kho + tỉ lệ khung của dự án (lỗi đọc → 9:16, nói trong `notes`)."""
    notes = []
    if aspect is None:
        aspect = ASPECT
        if conn is not None:
            try:
                from . import place_refs
                proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
                if proj is not None:
                    w, h = place_refs.resolution_of(proj)
                    aspect = w / h
            except Exception:  # noqa: BLE001
                notes.append("không đọc được khung dự án — dùng 9:16")
    st = stage_of(data, end=end)
    objects = library_objects(conn, pid, st["props"]) if st else {}
    for p in (st or {}).get("props") or []:
        if p["kind"] not in objects:
            notes.append(f"không có vật Kho loại '{p['kind']}' trong dự án — câu dùng tên chung '{KIND_EN.get(p['kind'], p['kind'])}'")
    res = derive(data, objects, aspect, end, render)
    res["notes"] = notes
    return res


def observe_items(facts: List[Dict]) -> List[Dict]:
    """Các ô 'khai điều thấy' cho QC: [{id, question, options}] (chỉ sự thật có vật trong khung)."""
    return [{"id": f["id"], "question": f["question"], "options": f["options"]} for f in facts if f.get("in_frame")]


def options_union() -> List[str]:
    out: List[str] = []
    for spec in FACTS.values():
        out += [o for o in spec["observe"]["options"] if o not in out]
    return out
