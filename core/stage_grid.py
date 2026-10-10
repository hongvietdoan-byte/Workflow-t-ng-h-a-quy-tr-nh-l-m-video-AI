"""Lưới sân khấu (kế hoạch đặt máy 3D, ĐỔI HƯỚNG 09/10 tối — Bước 0): phần hình học thuần Python, dùng được cả trong Blender.

Quy ước (người dùng chốt 09/10):
- Gốc O cố định theo CẢNH (một lần, lưu ở stage.json, mọi shot dùng chung): xy = tâm vùng diễn (chỗ đứng chính), z = điểm tia từ trên
  xuống chạm mặt sàn tại đó → mặt phẳng z = 0 là "sàn sân khấu"; mọi chiều cao tính từ mặt này.
- Trục: +x = Đông, +y = Bắc (đúng hệ model/Blender: facing 0 = +y). Phương vị độ theo chiều kim đồng hồ từ Bắc (như plate_camera.facing).
- Ô chỉ là TÊN gọi cho người ("F8") — docs/PHUONG_PHAP_SAN_KHAU_3D.md mục 2.3: i = ⌊x/c + N/2⌋ → chữ (Tây→Đông, A…Z, AA…),
  j = ⌊y/c + N/2⌋ + 1 → số (Nam→Bắc). N = 20, c = 1 → O ở góc Tây-Nam của ô K11 (tâm K11 = (0,5; 0,5)).
  Vị trí chính xác = tọa độ liên tục (m, 2 số lẻ) so với O.
- Sàn ô: |floor_z| ≤ 0,15 m = cùng mặt sàn (đứng được); lớn hơn = bậc (≤ 0,6 m) hoặc tầng khác.
Không import gì ngoài thư viện chuẩn math/unicodedata (Blender nạp file này theo đường dẫn).
"""
import math
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple

SAME_FLOOR_M = 0.15
STEP_MAX_M = 0.6
EYE, CHEST, HIP = 0.93, 0.72, 0.53     # tỉ lệ điểm nhìn trên người cao H (mục 4.2)
SENSOR_MM = 36.0                      # Blender: sensor_fit AUTO, 36 mm theo cạnh dài khung


def make_stage(origin_model: Sequence[float], cell_m: float = 1.0, cols: int = 20, rows: int = 20,
               floor_z_model: Optional[float] = None, lift_z: float = 0.0, factor: float = 1.0) -> Dict:
    """origin_model = [x, y, z] của chỗ đứng chính (tọa độ gốc của file 3D); floor_z_model = cao độ sàn chạm tia tại đó (z của O)."""
    z0 = float(origin_model[2] if floor_z_model is None else floor_z_model)
    return {"origin_model": [float(origin_model[0]), float(origin_model[1]), z0], "cell_m": float(cell_m), "cols": int(cols),
            "rows": int(rows), "north": "+y", "east": "+x", "lift_z": float(lift_z), "factor": float(factor)}


# ---- tên ô ------------------------------------------------------------------------------------------------------------------
def col_label(i: int) -> str:
    s, i = "", int(i)
    while True:
        s = chr(ord("A") + i % 26) + s
        i = i // 26 - 1
        if i < 0:
            return s


def col_index(label: str) -> int:
    n = 0
    for ch in label.strip().upper():
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def _half(stage: Dict) -> Tuple[float, float]:
    c = stage["cell_m"]
    return stage["cols"] * c / 2, stage["rows"] * c / 2


def cell_index(stage: Dict, x: float, y: float) -> Optional[Tuple[int, int]]:
    hx, hy = _half(stage)
    i, j = math.floor((x + hx) / stage["cell_m"]), math.floor((y + hy) / stage["cell_m"])
    if 0 <= i < stage["cols"] and 0 <= j < stage["rows"]:
        return i, j
    return None


def cell_name(stage: Dict, x: float, y: float) -> Optional[str]:
    ij = cell_index(stage, x, y)
    return None if ij is None else f"{col_label(ij[0])}{ij[1] + 1}"


def parse_cell(stage: Dict, name: str) -> Tuple[int, int]:
    s = name.strip().upper()
    k = 0
    while k < len(s) and s[k].isalpha():
        k += 1
    if k == 0 or k == len(s) or not s[k:].isdigit():
        raise ValueError(f"tên ô không hợp lệ: {name}")
    i, j = col_index(s[:k]), int(s[k:]) - 1
    if not (0 <= i < stage["cols"] and 0 <= j < stage["rows"]):
        raise ValueError(f"ô {name} ngoài lưới {col_label(stage['cols'] - 1)}{stage['rows']}")
    return i, j


def cell_centre(stage: Dict, name: str) -> Tuple[float, float]:
    i, j = parse_cell(stage, name)
    hx, hy = _half(stage)
    c = stage["cell_m"]
    return round(-hx + (i + 0.5) * c, 6) + 0.0, round(-hy + (j + 0.5) * c, 6) + 0.0


def cells(stage: Dict) -> List[Tuple[str, float, float]]:
    out = []
    for j in range(stage["rows"]):
        for i in range(stage["cols"]):
            name = f"{col_label(i)}{j + 1}"
            out.append((name, *cell_centre(stage, name)))
    return out


# ---- hệ tọa độ: so với O ↔ model ↔ scene Blender --------------------------------------------------------------------------
def rel_from_model(stage: Dict, p: Sequence[float]) -> Tuple[float, float, float]:
    o = stage["origin_model"]
    return tuple(round(float(p[k]) - o[k], 6) for k in range(3))


def model_from_rel(stage: Dict, r: Sequence[float]) -> Tuple[float, float, float]:
    o = stage["origin_model"]
    return tuple(o[k] + float(r[k]) for k in range(3))


def scene_from_rel(stage: Dict, r: Sequence[float]) -> Tuple[float, float, float]:
    """Như render_plates.to_scene: scene = model × factor (+ LIFT_Z ở z)."""
    m, f = model_from_rel(stage, r), stage.get("factor", 1.0)
    return m[0] * f, m[1] * f, m[2] * f + stage.get("lift_z", 0.0)


def rel_from_scene(stage: Dict, s: Sequence[float]) -> Tuple[float, float, float]:
    f = stage.get("factor", 1.0)
    return rel_from_model(stage, (s[0] / f, s[1] / f, (s[2] - stage.get("lift_z", 0.0)) / f))


# ---- đường đo ---------------------------------------------------------------------------------------------------------------
def bearing_deg(dx: float, dy: float) -> float:
    return math.degrees(math.atan2(dx, dy)) % 360.0


def offset(p: Sequence[float], bearing: float, dist: float, dz: float = 0.0) -> Tuple[float, float, float]:
    a = math.radians(bearing)
    return p[0] + math.sin(a) * dist, p[1] + math.cos(a) * dist, (p[2] if len(p) > 2 else 0.0) + dz


def measure(stage: Dict, r: Sequence[float], frm: Sequence[float] = (0.0, 0.0, 0.0)) -> Dict:
    """Điểm r (so với O): tọa độ, đường đo từ `frm` (mặc định O) — khoảng cách ngang, phương vị, chênh cao — và ô chứa nó."""
    dx, dy, dz = r[0] - frm[0], r[1] - frm[1], (r[2] if len(r) > 2 else 0.0) - (frm[2] if len(frm) > 2 else 0.0)
    return {"xyz": [round(float(v), 2) for v in (r[0], r[1], r[2] if len(r) > 2 else 0.0)],
            "dist_m": round(math.hypot(dx, dy), 2), "bearing_deg": round(bearing_deg(dx, dy), 1), "dz_m": round(dz, 2),
            "cell": cell_name(stage, r[0], r[1])}


def angle_at(a: Sequence[float], vertex: Sequence[float], b: Sequence[float]) -> float:
    u = [a[k] - vertex[k] for k in range(3)]
    v = [b[k] - vertex[k] for k in range(3)]
    nu, nv = math.sqrt(sum(x * x for x in u)), math.sqrt(sum(x * x for x in v))
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    c = max(-1.0, min(1.0, sum(x * y for x, y in zip(u, v)) / (nu * nv)))
    return math.degrees(math.acos(c))


def axis_side(a: Sequence[float], b: Sequence[float], p: Sequence[float], tol_m: float = 0.05) -> str:
    """Phía của p so với trục 180° a→b (nhìn từ a sang b), trên mặt ngang: tích có hướng."""
    ax, ay = b[0] - a[0], b[1] - a[1]
    px, py = p[0] - a[0], p[1] - a[1]
    n = math.hypot(ax, ay) or 1.0
    d = (ax * py - ay * px) / n                     # khoảng cách có dấu tới đường trục (+ = trái)
    return "on" if abs(d) <= tol_m else ("left" if d > 0 else "right")


# ---- máy: nhìn, chiếu điểm, tia ---------------------------------------------------------------------------------------------
def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _basis(cam, aim):
    f = _norm([aim[k] - cam[k] for k in range(3)])
    r = [f[1], -f[0], 0.0]                          # f × z
    if math.hypot(r[0], r[1]) < 1e-9:               # nhìn thẳng xuống/lên: chọn phải = +x
        r = [1.0, 0.0, 0.0]
    r = _norm(r)
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return f, r, u


def _tans(lens: float, aspect: float) -> Tuple[float, float]:
    t = SENSOR_MM / 2 / float(lens)
    return (t, t / aspect) if aspect >= 1 else (t * aspect, t)


def look(cam: Sequence[float], aim: Sequence[float]) -> Tuple[float, float]:
    """(phương vị máy nhìn, góc nghiêng — âm = cúi), độ."""
    d = [aim[k] - cam[k] for k in range(3)]
    return bearing_deg(d[0], d[1]), math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))


def project(cam, aim, p, lens: float, aspect: float):
    """Điểm p trong khung: (u, v, độ sâu) với u 0..1 trái→phải, v 0..1 trên→dưới; None khi sau lưng máy."""
    f, r, u = _basis(cam, aim)
    d = [p[k] - cam[k] for k in range(3)]
    z = sum(a * b for a, b in zip(d, f))
    if z <= 1e-6:
        return None
    th, tv = _tans(lens, aspect)
    x = sum(a * b for a, b in zip(d, r)) / z
    y = sum(a * b for a, b in zip(d, u)) / z
    return 0.5 + 0.5 * x / th, 0.5 - 0.5 * y / tv, z


def fov(lens: float, aspect: float) -> Tuple[float, float]:
    """(FOV ngang, FOV dọc) độ."""
    th, tv = _tans(lens, aspect)
    return 2 * math.degrees(math.atan(th)), 2 * math.degrees(math.atan(tv))


def horizon_w(pitch_deg: float, lens: float, aspect: float) -> float:
    """Đường chân trời trên ảnh (0 = mép trên): w_h = 0,5 + tan(pitch)/(2·tan(v/2)), pitch âm khi cúi (mục 6)."""
    return 0.5 + math.tan(math.radians(pitch_deg)) / (2 * _tans(lens, aspect)[1])


def frame_distance(h_f: float, lens: float, aspect: float) -> float:
    """D = (h_f/2)/tan(v/2): khoảng cách xiên để khung dọc chứa h_f mét (mục 5 bước 1)."""
    return h_f / 2 / _tans(lens, aspect)[1]


def camera_at(target: Sequence[float], alpha_deg: float, dist: float, cam_z: float) -> Optional[Tuple[float, float, float]]:
    """Mục 5 bước 3: C_xy = T_xy + D_h·(sin α, cos α), C_z cho trước, √(D_h² + (T_z − C_z)²) = D. None khi |T_z − C_z| > D."""
    dz = target[2] - cam_z
    if abs(dz) > dist:
        return None
    dh = math.sqrt(dist * dist - dz * dz)
    a = math.radians(alpha_deg)
    return target[0] + math.sin(a) * dh, target[1] + math.cos(a) * dh, cam_z


def median(vals: Sequence[float]) -> Optional[float]:
    v = sorted(vals)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def in_frame(puv, margin: float = 0.0) -> bool:
    return bool(puv) and -margin <= puv[0] <= 1 + margin and -margin <= puv[1] <= 1 + margin


def ray_dir(cam, aim, u: float, v: float, lens: float, aspect: float) -> Tuple[float, float, float]:
    f, r, up = _basis(cam, aim)
    th, tv = _tans(lens, aspect)
    x, y = (u - 0.5) * 2 * th, (0.5 - v) * 2 * tv
    return tuple(_norm([f[k] + x * r[k] + y * up[k] for k in range(3)]))


# ---- sàn ô ------------------------------------------------------------------------------------------------------------------
def in_well_foot_z(well_h: float, height: float, chest: float = CHEST) -> float:
    """Người đứng TRONG giếng (#24 yêu nữ bò lên): ngực ngang miệng giếng → chân ở z = cao giếng − chest·H (âm = dưới mặt sàn).
    Đầu + vai nhô lên trên miệng giếng một đoạn (1 − chest)·H."""
    return round(well_h - chest * height, 3)


def floor_status(dz: Optional[float]) -> str:
    if dz is None:
        return "none"
    a = abs(dz)
    return "same" if a <= SAME_FLOOR_M + 1e-9 else ("step" if a <= STEP_MAX_M else "level")


def slope_deg(zs: Sequence[float], step_m: float) -> float:
    """Độ dốc trung bình dọc một dãy cao độ cách nhau step_m."""
    if len(zs) < 2:
        return 0.0
    rise = (zs[-1] - zs[0]) / ((len(zs) - 1) * step_m)
    return math.degrees(math.atan(abs(rise)))


# ---- phân nhóm vật thể ------------------------------------------------------------------------------------------------------
NAME_GROUPS = [   # thứ tự = ưu tiên (từ khóa trong tên object + vật liệu, chữ thường)
    ("nguoi", ("stage_kelly", "stage_yeu", "stage_person", "mannequin")),
    ("gieng", ("stage_well",)),
    ("thap", ("clocktower", "clock_tower", "tower", "clock")),
    ("cay", ("tree", "plant", "bush", "grass", "shrub", "coco", "leaf", "palm", "foliage")),
    ("bac", ("stair", "step")),
    ("tuong", ("wall", "fence", "rail", "barrier")),
    ("nha", ("house", "building", "roof", "home", "door", "window", "bld")),
    ("san", ("terrain", "ground", "road", "floor", "plaza", "pave")),
]
# Bước 0 #24 (đo 09/10): mọi tên object của map FF chính thức kết thúc "_plan" (không phải "plane") → không dùng làm từ khóa sàn;
# cả quảng trường + tường thấp + bậc + lan can là MỘT mesh "CLK_OUT_Base002_LOD0_plan" (bbox 187×195 m) → tên chỉ tách được
# tháp / nhà / cây; trong mesh nền phải phân theo từng điểm trúng (group_by_hit).
BASE_MESH_KEYS = ("_base", "terrain")


def group_by_name(obj: str, mat: str = "") -> str:
    s = f"{obj} {mat}".lower()
    for g, keys in NAME_GROUPS:
        if any(k in s for k in keys):
            return g
    return "khac"


def group_by_shape(top_rel: float, size: Sequence[float]) -> str:
    """Khi tên vô nghĩa: theo đỉnh vật so với sàn sân khấu + kích thước bbox (m)."""
    sx, sy, sz = (float(v) for v in size[:3])
    small, big = min(sx, sy), max(sx, sy)
    if top_rel > 20 and small < 30:
        return "thap"
    if big > 40 and sz < 6 and top_rel < 0.6:
        return "san"
    if top_rel > 2.5 and small > 2:
        return "nha"
    if 0.3 <= top_rel <= 2.5 and small < 1.2:
        return "tuong"
    if top_rel < 0.6 and big > 20:
        return "san"
    return "khac"


def group_by_hit(group: str, z_rel: float, normal_z: float) -> str:
    """Nhóm của MỘT điểm tia trúng khi object là mesh nền gộp (sàn + tường thấp + bậc): theo cao độ so với sàn sân khấu và pháp tuyến.
    Nhóm theo tên khác (tháp, nhà, cây, giếng, người) giữ nguyên."""
    if group not in ("san", "khac"):
        return group
    if normal_z >= 0.9:                                   # mặt ngang
        a = abs(z_rel)
        if a <= SAME_FLOOR_M:
            return "san"
        if a <= STEP_MAX_M:
            return "bac"
        return "tuong" if 0 < z_rel <= 2.5 else ("san_khac" if z_rel < 0 else "nha")
    if normal_z <= 0.5:                                   # mặt đứng / dốc gắt
        return "tuong" if z_rel <= 2.5 else "nha"
    return "doc"                                          # mặt dốc vừa (ram, mái)


# ================================ Bước 1–2 (PHUONG_PHAP_SAN_KHAU_3D mục 5–8, 6b) ================================
# Bảng cỡ cảnh: GIỐNG HỆT core/plate_camera.FRAMING (test giữ khớp; file này không import plate_camera vì Blender nạp theo đường dẫn)
# cỡ -> (phần thân từ đỉnh đầu nằm trong khung, phần chiều cao khung nó chiếm, ống kính mm)
FRAMING = {"EWS": (1.0, 0.18, 20), "WS": (1.0, 0.55, 24), "GAME_TPS": (1.0, 0.42, 24), "MLS": (0.75, 0.80, 32),
           "MS": (0.55, 0.82, 35), "MCU": (0.35, 0.85, 50), "CU": (0.22, 0.88, 65), "ECU": (0.12, 0.95, 85)}
ALPHA_STEP = 15                                     # mục 8: 24 hướng


def point_state(cam, aim, p, lens: float, aspect: float, blocked_by: Optional[str] = None, margin: float = 0.04) -> Dict:
    """Nhãn hình phác (người dùng 09/10): 'in' = chấm đặc; 'blocked' = trong khung nhưng bị che → chấm rỗng "(bị che bởi …)";
    'out' = ngoài khung → KHÔNG chấm, mũi tên xám sát mép (`arrow`, u/v trong khung, lùi `margin`) chỉ hướng vật, `edge` = mép;
    'behind' = sau lưng máy (z_c ≤ 0) → không vẽ, chỉ ghi bảng. Ngoài khung thắng bị che."""
    pr = project(cam, aim, p, lens, aspect)
    if pr is None:
        return {"state": "behind", "uv": None, "edge": None, "arrow": None, "blocked_by": blocked_by}
    u, v = pr[0], pr[1]
    if in_frame(pr):
        return {"state": "blocked" if blocked_by else "in", "uv": (u, v), "edge": None, "arrow": None, "blocked_by": blocked_by,
                "depth": pr[2]}
    du, dv = u - 0.5, v - 0.5
    lim = 0.5 - margin
    tu = lim / abs(du) if abs(du) > 1e-12 else float("inf")
    tv = lim / abs(dv) if abs(dv) > 1e-12 else float("inf")
    t = min(tu, tv)
    edge = ("phai" if du > 0 else "trai") if tu <= tv else ("duoi" if dv > 0 else "tren")
    return {"state": "out", "uv": (u, v), "edge": edge, "arrow": (0.5 + du * t, 0.5 + dv * t), "blocked_by": blocked_by,
            "depth": pr[2]}


def layer_heights(layer: str, H: float) -> List[float]:
    """Mục 5 bước 2 — 3 độ cao máy (so với sàn) mỗi lớp: ngang = quanh mắt (±0,15 m); thấp = 0,5–0,7·H (không sát đất);
    cao = mắt + 0,5 / 0,75 / 1 m; trên đầu = mắt + 1,5 / 2,5 / 3,5 m."""
    e = EYE * H
    return {"ngang": [e - 0.15, e, e + 0.15], "thap": [0.5 * H, 0.6 * H, 0.7 * H], "cao": [e + 0.5, e + 0.75, e + 1.0],
            "tren_dau": [e + 1.5, e + 2.5, e + 3.5]}[layer]


def size_frame(size: str, H: float) -> Tuple[float, float, float]:
    """(h_f = mét khung dọc phải chứa, ống kính mm, phần khung nhân vật chiếm) theo FRAMING."""
    body, share, lens = FRAMING[size]
    return H * body / share, float(lens), share


def candidates(req: Dict, aspect: float) -> List[Dict]:
    """Mục 8 bước 1: 24 hướng (15°) × 3 độ cao theo lớp. C theo mục 5 bước 3 (khoảng xiên D = frame_distance(h_f)),
    pitch = atan2(T_z − C_z, D_h). Khi |T_z − C_z| > D (máy cao hơn khoảng cách khung) thì D_h = 0,34·D và ghi `note`."""
    T = [float(v) for v in req["aim"]]
    H = float(req.get("H", 1.7))
    h_f, lens, _ = size_frame(req["size"], H)
    lens = float(req.get("lens") or lens)
    D = frame_distance(h_f, lens, aspect)
    out = []
    for k in range(360 // ALPHA_STEP):
        alpha = k * ALPHA_STEP
        for h in layer_heights(req["layer"], H):
            C, note = camera_at(T, alpha, D, h), None
            if C is None:
                a = math.radians(alpha)
                C, note = (T[0] + math.sin(a) * 0.34 * D, T[1] + math.cos(a) * 0.34 * D, h), "máy cao hơn khoảng cách khung → D_h = 0,34·D"
            dh = math.hypot(C[0] - T[0], C[1] - T[1])
            out.append({"alpha": alpha, "h": round(h, 3), "at": [C[0], C[1], C[2]], "aim": T, "lens": lens, "D": D,
                        "pitch": math.degrees(math.atan2(T[2] - C[2], dh)), "layer": req["layer"], "size": req["size"], "note": note})
    return out


# Ngưỡng luật mục 7 — TẤT CẢ TẠM, chờ hiệu chỉnh trên shot người dùng chê/khen (bảng 9 shot #24 ở HANDOFF): (giá trị, lý do)
RULE_TH = {
    "L2_hit_pct": (80.0, "tạm, chờ hiệu chỉnh: theo mục 7; Bước 0 yêu nữ bị giếng che chân còn 67 % → phải hỏng"),
    "L3_rel": (0.15, "tạm, chờ hiệu chỉnh: theo mục 7 (±15 % so với bảng cỡ)"),
    "L5_thap_pct": (3.0, "tạm, chờ hiệu chỉnh: 3 % khung ≈ 70 tia/2304 — chóp tháp nhận ra được; Bước 0 toàn cảnh 25 %"),
    "L5_need_pct": (1.0, "tạm, chờ hiệu chỉnh: đạo cụ cần thấy ≥ 1 % khung (≈ 23 tia), nhỏ hơn thì model không vẽ đúng chỗ"),
    "L5_see_deg": (60.0, "tạm, chờ hiệu chỉnh: thấy mặt / lưng khi máy lệch ≤ 60° so với hướng mặt / sau lưng (3/4 vẫn tính)"),
    "L7_ngang": (12.0, "tạm, chờ hiệu chỉnh: theo mục 7, |pitch| ≤ 12°"),
    "L7_cui": (-20.0, "tạm, chờ hiệu chỉnh: theo mục 7; máy −6° từng bị khai là cúi"),
    "L7_ngua": (8.0, "tạm, chờ hiệu chỉnh: theo mục 7"),
    "L7_tren_dau": (-45.0, "tạm, chờ hiệu chỉnh: trên đầu = cúi gắt"),
    "L8_max_pct": (70.0, "tạm, chờ hiệu chỉnh: Bước 0 máy 3,4 m sàn 84,5 % là hỏng, máy cúi tính đúng sàn 57 % là đạt"),
    "L8_down_need_pct": (3.0, "tạm, chờ hiệu chỉnh: shot cúi phải có đạo cụ + người ≥ 3 % khung (Bước 0 góc b: giếng 14 %, Kelly 7,5 %)"),
    "L9_min_m": (0.3, "tạm, chờ hiệu chỉnh: theo mục 7"),
    "L9_max_pct": (10.0, "tạm, chờ hiệu chỉnh: theo mục 7 — vật rắn gần máy hơn nhân vật chiếm > 10 % khung"),
    "L10_lo": (0.85, "tạm, chờ hiệu chỉnh: giếng 'cao ngang hông' (Kho 420) ±15 %"),
    "L10_hi": (1.15, "tạm, chờ hiệu chỉnh: như trên"),
}


def _th(th: Optional[Dict], k: str) -> float:
    return float((th or {}).get(k, RULE_TH[k][0]))


def _adiff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def background_group(percent: Dict[str, float]) -> Optional[str]:
    """Nhóm nền chiếm nhiều nhất (L6): bỏ sàn, trời, đạo cụ dựng, người nộm."""
    bg = {g: v for g, v in percent.items() if g not in ("san", "troi", "gieng") and not g.startswith("nguoi")}
    return max(bg, key=bg.get) if bg else None


def check_rules(m: Dict, req: Dict, th: Optional[Dict] = None) -> Dict:
    """Mục 7: L1–L10 trên số đo `m` của một máy (Blender) theo ý đồ `req`. Trả {'ok', 'fail': [L…], 'why': {L: câu có số}}.
    Không tự đổi ý đồ. `th` = ghi đè ngưỡng (giá trị thường)."""
    why = {}
    pct = m.get("percent") or {}
    floor_ok = m.get("cam_floor") == "same" or (m.get("cam_floor") == "step" and req.get("cam_on_step"))
    if not floor_ok or m.get("cam_inside"):
        why["L1"] = f"sàn dưới máy '{m.get('cam_floor')}'" + (", máy nằm trong vật" if m.get("cam_inside") else "")
    hit = m.get("subject_hit_pct")
    if hit is None or hit < _th(th, "L2_hit_pct"):
        why["L2"] = f"nhân vật chính thấy {hit}% (< {_th(th, 'L2_hit_pct'):g}%)"
    exp = FRAMING[req["size"]][1] * 100
    fp = m.get("subject_frame_pct")
    if fp is None or abs(fp / exp - 1) > _th(th, "L3_rel"):
        why["L3"] = f"nhân vật chiếm {fp}% chiều cao khung, cỡ {req['size']} cần {exp:g}% ±{_th(th, 'L3_rel') * 100:g}%"
    if req.get("s0") and m.get("side") not in (req["s0"], "on") and not req.get("cross_ok"):
        why["L4"] = f"máy phía {m.get('side')} của trục, shot mở chọn {req['s0']}"
    l5 = []
    for g, want in (req.get("want") or {}).items():
        v = pct.get(g, 0.0)
        if want and v < _th(th, "L5_thap_pct"):
            l5.append(f"cần thấy {g} nhưng {v}%")
        if not want and v > 0:
            l5.append(f"không được thấy {g} nhưng {v}%")
    for g in req.get("need") or []:
        v = pct.get(g, 0.0)
        if v < _th(th, "L5_need_pct"):
            l5.append(f"cần thấy {g} ≥ {_th(th, 'L5_need_pct'):g}% nhưng {v}%")
    if req.get("see") in ("face", "back") and req.get("facing") is not None and m.get("alpha") is not None:
        ref = req["facing"] if req["see"] == "face" else (req["facing"] + 180) % 360
        if _adiff(m["alpha"], ref) > _th(th, "L5_see_deg"):
            l5.append(f"cần thấy {'mặt' if req['see'] == 'face' else 'lưng'}: máy ở {m['alpha']:g}°, lệch {_adiff(m['alpha'], ref):.0f}°")
    if l5:
        why["L5"] = "; ".join(l5)
    if req.get("family") and not req.get("reverse_ok"):
        bg = background_group(pct)
        if bg != req["family"]:
            why["L6"] = f"nền chính '{bg}' khác shot mở '{req['family']}'"
    p, lay = m.get("pitch"), req.get("layer")
    if p is not None and ((lay == "ngang" and abs(p) > _th(th, "L7_ngang")) or (lay == "cao" and p > _th(th, "L7_cui"))
                          or (lay == "thap" and p < _th(th, "L7_ngua")) or (lay == "tren_dau" and p > _th(th, "L7_tren_dau"))):
        why["L7"] = f"pitch {p:.1f}° không hợp lớp '{lay}'"
    bgp = {g: v for g, v in pct.items() if not g.startswith("nguoi")}     # nhân vật lấp khung (CU) là ý đồ, không phải "một màu"
    if bgp and not req.get("single_ok"):
        g, v = max(bgp.items(), key=lambda x: x[1])
        if v > _th(th, "L8_max_pct"):
            why["L8"] = f"'{g}' chiếm {v}% khung (> {_th(th, 'L8_max_pct'):g}%)"
    if lay in ("cao", "tren_dau") or (p is not None and p <= _th(th, "L7_cui")):
        sub = pct.get("gieng", 0.0) + sum(v for g, v in pct.items() if g.startswith("nguoi"))
        if sub < _th(th, "L8_down_need_pct"):
            why["L8"] = (why["L8"] + "; " if "L8" in why else "") + f"shot cúi chỉ có đạo cụ + người {sub:.1f}%"
    oc, om = m.get("occluder_pct") or 0.0, m.get("occluder_m")
    if oc > _th(th, "L9_max_pct") or (om is not None and om < _th(th, "L9_min_m")):
        why["L9"] = f"vật rắn trước nhân vật chiếm {oc}% khung, gần nhất {om} m"
    r = m.get("well_hip_ratio")
    if r is not None and not (_th(th, "L10_lo") <= r <= _th(th, "L10_hi")):
        why["L10"] = f"đỉnh giếng ÷ hông = {r}"
    fail = [f"L{k}" for k in range(1, 11) if f"L{k}" in why]
    return {"ok": not fail, "fail": fail, "why": why}


def rank_score(m: Dict, req: Dict) -> float:
    """Mục 8 bước 4: xếp ứng viên đạt theo ưu tiên của ý đồ — Σ trọng số × % khung của nhóm (req['rank']) − 0,5 × lệch cỡ (điểm %)."""
    pct = m.get("percent") or {}
    s = sum(float(w) * pct.get(g, 0.0) for g, w in (req.get("rank") or {}).items())
    if m.get("subject_frame_pct") is not None:
        s -= abs(m["subject_frame_pct"] - FRAMING[req["size"]][1] * 100) * 0.5
    return round(s, 2)


# ================================ v2: yêu cầu khung → đo → luật P/S (PHUONG_PHAP_SAN_KHAU_3D mục 3.2, 4, 7) ================================
# Vật trên sân khấu (từ blocking.json, tọa độ so với O): {"key", "kind": "nguoi"|"dao_cu"|"moc", "xy": [x, y], "z": chân/đáy,
#   người: "H", "facing", "rim_z" (đứng trong giếng: chỉ tính phần trên miệng giếng); đạo cụ/mốc: "h", "r"; "group" (nhóm tia), "own" (tiền tố
#   tên object Blender của chính nó), "label"}. Yêu cầu khung (shot_specs.json): mục 3.2 — "thanh_phan": [{vat, vai, vung, thay, co_pct}].
ROLES = ("chinh", "phu", "khong_duoc_co")
_U_ZONE = {"trai": (0.0, 1 / 3), "giua": (1 / 3, 2 / 3), "phai": (2 / 3, 1.0)}
_W_ZONE = {"tren": (0.0, 1 / 3), "giua": (1 / 3, 2 / 3), "duoi": (2 / 3, 1.0)}
VIEW_FACE_DEG, VIEW_BACK_DEG = 60.0, 120.0           # mục 4: mặt ≤ 60°, lưng ≥ 120°, còn lại nghiêng
VIEWS = ("mat", "lung", "nghieng")
GOC = ("ngang", "cui", "ngua")


def fold(s) -> str:
    """Chữ thường không dấu ('Phải' → 'phai', 'đ' → 'd') để so khóa do Director/người dùng gõ."""
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def _span(parts, table, what):
    lo = hi = None
    for p in parts:
        if p in ("*", ""):
            return None
        if p not in table:
            raise ValueError(f"vùng {what} '{p}' không hợp lệ (dùng {', '.join(table)})")
        a, b = table[p]
        lo, hi = (a, b) if lo is None else (min(lo, a), max(hi, b))
    return None if lo is None else (lo, hi)


def parse_zone(z) -> Dict:
    """Vùng đích trên lưới một phần ba (mục 3.2): "ngang-dọc", vd "phai-giua", "giua+phai-duoi", "trai" (chỉ ngang), "*-tren" (chỉ dọc).
    Nhận cả chữ có dấu / cách viết của Director: "1/3 phải, 1/3 giữa", "giữa dưới". Một chữ "tren"/"duoi" đứng riêng = chỉ dọc.
    Trả {"u": (lo, hi) | None, "w": (lo, hi) | None} (u trái→phải, w trên→dưới, 0..1)."""
    if z in (None, "", "*"):
        return {"u": None, "w": None}
    if isinstance(z, dict):
        return {"u": None if z.get("u") is None else tuple(z["u"]), "w": None if z.get("w") is None else tuple(z["w"])}
    s = fold(z).replace("1/3", " ")
    for ch in ",;/":
        s = s.replace(ch, "-")
    parts = [p.strip() for p in s.replace("|", "+").split("-") if p.strip()] or [""]
    if len(parts) == 1 and " " in parts[0]:
        parts = parts[0].split()
    parts = [[q.strip() for q in p.split("+")] for p in parts]
    if len(parts) > 2:
        raise ValueError(f"vùng '{z}': tối đa 2 phần (ngang-dọc)")
    if len(parts) == 1 and all(q in ("tren", "duoi") for q in parts[0]):
        return {"u": None, "w": _span(parts[0], _W_ZONE, "dọc")}
    return {"u": _span(parts[0], _U_ZONE, "ngang"), "w": _span(parts[1], _W_ZONE, "dọc") if len(parts) > 1 else None}


def zone_centre(zone: Dict, default_w: Optional[float] = None) -> Tuple[Optional[float], Optional[float]]:
    u = None if zone.get("u") is None else (zone["u"][0] + zone["u"][1]) / 2
    w = default_w if zone.get("w") is None else (zone["w"][0] + zone["w"][1]) / 2
    return u, w


def zone_miss(uv, zone: Dict) -> float:
    """Khoảng lệch (phần khung) của điểm uv ra ngoài vùng đích; 0 = trong vùng. None/không đo được = 1."""
    if not uv:
        return 1.0
    m = 0.0
    for k, val in (("u", uv[0]), ("w", uv[1])):
        r = zone.get(k)
        if r is not None:
            m = max(m, r[0] - val, val - r[1], 0.0)
    return m


def view_of(facing: float, obj_xy: Sequence[float], cam: Sequence[float]) -> str:
    """Mục 4: máy thấy mặt / lưng / nghiêng của người quay hướng `facing` (độ từ Bắc)."""
    to_cam = bearing_deg(cam[0] - obj_xy[0], cam[1] - obj_xy[1])
    a = abs((to_cam - facing + 180.0) % 360.0 - 180.0)
    return "mat" if a <= VIEW_FACE_DEG else ("lung" if a >= VIEW_BACK_DEG else "nghieng")


def obj_height(o: Dict) -> float:
    return float(o.get("body_height", o["H"]) if o["kind"] == "nguoi" else o["h"])


def lying(o: Dict) -> bool:
    return o["kind"] == "nguoi" and o.get("tu_the") in ("nam", "nga_ngua")


def lying_point(o: Dict, along: float, height: float, lat: float = 0.0):
    """Thân nằm: tâm sàn xy, đầu về facing, chân ngược lại; khoảng bao TẠM, chưa đo bằng Pose."""
    if o.get("facing") is None:
        raise ValueError("thân nằm thiếu facing — không xác định được đầu/chân")
    a = math.radians(float(o["facing"]))
    length = float(o.get("body_length", o["H"]))
    return (float(o["xy"][0]) + math.sin(a) * length * along + math.cos(a) * lat,
            float(o["xy"][1]) + math.cos(a) * length * along - math.sin(a) * lat,
            float(o.get("z", 0)) + obj_height(o) * height)


def object_points(o: Dict, cam: Optional[Sequence[float]] = None, co: Optional[str] = None) -> List[Tuple[float, float, float]]:
    """Mục 4: điểm phủ vật để đo % thấy. Người: 9 mức cao × 3 điểm ngang (theo trục phải của máy) = 27; đứng trong giếng chỉ giữ phần
    trên miệng giếng (`rim_z`); có `co` (thứ chính đo cỡ) thì chỉ giữ phần thân cỡ đó cần thấy (MCU: 35 % trên — S1 không đòi cả người).
    Đạo cụ trụ (giếng): đáy, giữa, miệng × tâm + 4 điểm vành = 15. Mốc (tháp): 9 điểm dọc trục."""
    x, y, z0 = float(o["xy"][0]), float(o["xy"][1]), float(o.get("z", 0.0))
    h = obj_height(o)
    if lying(o):
        body = FRAMING[co][0] if co in FRAMING else 1.0
        return [lying_point(o, .5 - body * k / 8, ht, lat)
                for k in range(9) for ht in (0.0, 1.0) for lat in (-.12, .12)]
    if o["kind"] == "nguoi":
        if cam is not None and math.hypot(cam[0] - x, cam[1] - y) > 1e-6:
            ra = math.radians(bearing_deg(cam[0] - x, cam[1] - y) + 90)
            rx, ry = math.sin(ra), math.cos(ra)
        else:
            rx, ry = 1.0, 0.0
        rim = o.get("rim_z")
        lo = z0 if co not in FRAMING else z0 + h * (1 - FRAMING[co][0])
        lo = lo if rim is None else max(lo, rim)
        span = z0 + h - lo
        pts = [(x + rx * lat, y + ry * lat, lo + span * (0.03 + 0.95 * k / 8)) for k in range(9) for lat in (-0.12, 0.0, 0.12)]
        if o.get("facing") is not None and co not in ("MCU", "CU", "ECU"):
            # mặt/mũi nhô 0,25 m theo hướng mặt ở tầm mắt (V2 #24 shot 7: mũi Kelly 'không được có' lọt góc khung mà 27 điểm thân không bắt)
            fa = math.radians(float(o["facing"]))
            pts.append((x + math.sin(fa) * 0.25, y + math.cos(fa) * 0.25, z0 + h * EYE))
        return pts
    if o["kind"] == "moc":
        # trục + 4 điểm mép (0,9·r) mỗi mức cao: mốc rộng (tháp 9,35 m) lọt MÉP khung mà trục ngoài khung — V2 09/10 shot 41/43 lọt S5
        rr = float(o.get("r", 0.0)) * 0.9
        return [(x + rr * dx, y + rr * dy, z0 + h * (k + 0.5) / 9) for k in range(9)
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))]
    r = float(o.get("r", 0.0)) * 0.9
    pts = []
    for fz in (0.05, 0.5, 1.0):
        zz = z0 + h * fz
        pts.append((x, y, zz))
        pts += [(x + r * math.sin(math.radians(a)), y + r * math.cos(math.radians(a)), zz) for a in (0, 90, 180, 270)]
    return pts


def size_span(o: Dict, co: Optional[str] = None) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """(điểm trên, điểm dưới) để đo cỡ trong khung. Người: đỉnh đầu → đáy phần thân của cỡ `co` (FRAMING), không thấp hơn miệng giếng
    khi đứng trong giếng; đạo cụ/mốc: miệng/đỉnh → đáy."""
    if lying(o):
        body = FRAMING[co][0] if co in FRAMING else 1.0
        return lying_point(o, .5, .5), lying_point(o, .5 - body, .5)
    x, y, z0 = float(o["xy"][0]), float(o["xy"][1]), float(o.get("z", 0.0))
    h = obj_height(o)
    top = z0 + h
    bot = z0
    if o["kind"] == "nguoi":
        body = FRAMING[co][0] if co in FRAMING else 1.0
        bot = top - h * body
        if o.get("rim_z") is not None:
            bot = max(bot, float(o["rim_z"]))
    return (x, y, top), (x, y, bot)


def anchor_point(o: Dict, co: Optional[str] = None) -> Tuple[float, float, float]:
    """Điểm đại diện để đặt vào vùng đích: giữa đoạn đo cỡ (người: phần thân trong khung của cỡ `co`)."""
    t, b = size_span(o, co)
    return tuple((a + c) / 2 for a, c in zip(t, b))


def zone_point(o: Dict, co: Optional[str] = None) -> Tuple[float, float, float]:
    """Điểm của vật được đặt vào vùng đích (S2). Người = MẮT (0,93·H — quy tắc một phần ba đặt mắt; với cỡ chặt tâm thân không thể nằm
    ở 1/3 trên, đo 09/10: MCU 'giua-tren' lệch 0,26 khung). Đạo cụ / mốc = giữa đoạn đo cỡ."""
    if o["kind"] == "nguoi":
        if lying(o):
            if co in ("EWS", "WS", "GAME_TPS"):
                return anchor_point(o, co)
            return lying_point(o, .45, EYE)
        return float(o["xy"][0]), float(o["xy"][1]), float(o.get("z", 0.0)) + EYE * float(o["H"])
    return anchor_point(o, co)


def projected_size(o: Dict, cam, aim, lens: float, aspect: float, co=None):
    """Người nằm đo cả bề dài ngang và cao; người khác giữ đúng số chiều cao cũ."""
    if lying(o):
        ps = [project(cam, aim, p, lens, aspect) for p in object_points(o, cam, co)]
        if any(p is None for p in ps):
            return None
        return max(max(p[i] for p in ps) - min(p[i] for p in ps) for i in (0, 1))
    t, b = size_span(o, co)
    pt, pb = project(cam, aim, t, lens, aspect), project(cam, aim, b, lens, aspect)
    return None if pt is None or pb is None else pb[1] - pt[1]


def frame_eval(cam, aim, lens: float, aspect: float, objs: Dict[str, Dict], co: Optional[str] = None,
               size_key: Optional[str] = None) -> Dict:
    """Giai đoạn (a) mục 6.5 — Python thuần: mỗi vật → % điểm trong khung, vị trí (u, w) (người: mắt; vật: tâm phần trong khung),
    cỡ (% chiều cao khung), hướng thấy; cộng pitch/yaw máy. `size_key` = vật đo cỡ theo `co` (thứ chính đầu tiên); vật khác cả thân."""
    yaw, pitch = look(cam, aim)
    out = {}
    for k, o in objs.items():
        pts = object_points(o, cam, co if k == size_key else None)
        pr = [project(cam, aim, p, lens, aspect) for p in pts]
        ins = [q for q in pr if in_frame(q)]
        size = projected_size(o, cam, aim, lens, aspect, co if k == size_key else None)
        cen = None if not ins else [round(sum(q[0] for q in ins) / len(ins), 3), round(sum(q[1] for q in ins) / len(ins), 3)]
        if o["kind"] == "nguoi":
            pe = project(cam, aim, zone_point(o, co if k == size_key else None), lens, aspect)
            uv = [round(pe[0], 3), round(pe[1], 3)] if in_frame(pe) else None
        else:
            uv = cen
        out[k] = {"n": len(pts), "in_pct": round(100.0 * len(ins) / len(pts), 1) if pts else 0.0, "uv": uv, "uv_than": cen,
                  "size_pct": None if size is None else round(100.0 * size, 1),
                  "view": view_of(o["facing"], o["xy"], cam) if o["kind"] == "nguoi" and o.get("facing") is not None else None,
                  "dist_m": round(math.dist(cam, anchor_point(o)), 2)}
    return {"obj": out, "pitch": round(pitch, 2), "yaw": round(yaw, 2)}


# Ngưỡng v2 — TẠM, chờ hiệu chỉnh bằng phản hồi người dùng (stage_feedback.jsonl, ≥ 3 phản hồi cùng chiều mới đổi — mục 7.3)
RULE_TH.update({
    "S1_nguoi_pct": (60.0, "tạm, chờ hiệu chỉnh: mục 7.2 — người chính thấy ≥ 60 % điểm phủ (trong giếng: phần trên miệng)"),
    "S1_dao_cu_pct": (50.0, "tạm, chờ hiệu chỉnh: mục 7.2 — đạo cụ chính thấy ≥ 50 %"),
    "S1_moc_pct": (25.0, "tạm, chờ hiệu chỉnh: mốc lớn (tháp 38 m) chỉ lọt một phần khung dọc; mục 7.2 chưa ghi số cho mốc"),
    "S2_tol": (0.08, "tạm, chờ hiệu chỉnh: mục 7.2 — tâm vật trong vùng đích ± 0,08 khung"),
    "S6_max_pct": (70.0, "tạm, chờ hiệu chỉnh: mục 7.2 — một nhóm ngoài yêu cầu > 70 % khung (đo #24: máy 3,4 m sàn 84,5 %)"),
})


def _seen(e: Dict) -> float:
    """% thấy: có số Blender (đã trừ bị che) thì dùng, không thì % trong khung (giai đoạn a)."""
    v = e.get("seen_pct")
    return float(e.get("in_pct") or 0.0) if v is None else float(v)


def check_spec(m: Dict, spec: Dict, objs: Dict[str, Dict], th: Optional[Dict] = None) -> Dict:
    """Luật P1–P4 (vật lý) + S1–S6 (sinh từ yêu cầu khung) — mục 7.1–7.2; thay L1/L5–L10 của cách dò mù. `m` = frame_eval (+ số Blender:
    seen_pct/blocked_by từng vật, percent, cam_floor, cam_inside, occluder_pct/_m, well_hip_ratio). Số nào chưa đo thì luật đó bỏ qua
    (giai đoạn a). Không tự đổi ý đồ. Trả {'ok', 'fail': [mã], 'why': {mã: câu có số}, 'phu': {vật: đạt?}, 'miss': tổng lệch vùng}."""
    why: Dict[str, List[str]] = {}

    def bad(code, txt):
        why.setdefault(code, []).append(txt)
    if "cam_floor" in m:
        if not (m.get("cam_floor") == "same" or (m.get("cam_floor") == "step" and spec.get("cam_on_step"))) or m.get("cam_inside"):
            bad("P1", f"sàn dưới máy '{m.get('cam_floor')}'" + (", máy nằm trong vật" if m.get("cam_inside") else ""))
    oc, om = m.get("occluder_pct"), m.get("occluder_m")
    if oc is not None and (oc > _th(th, "L9_max_pct") or (om is not None and om < _th(th, "L9_min_m"))):
        bad("P2", f"vật rắn trước thứ chính chiếm {oc}% khung, gần nhất {om} m")
    p, goc = m.get("pitch"), fold(spec.get("goc") or "")
    if p is not None and goc and ((goc == "ngang" and abs(p) > _th(th, "L7_ngang")) or (goc == "cui" and p > _th(th, "L7_cui"))
                                  or (goc == "ngua" and p < _th(th, "L7_ngua"))):
        bad("P3", f"pitch thật {p:.1f}° không phải '{spec.get('goc')}'")
    r = m.get("well_hip_ratio")
    if r is not None and not (_th(th, "L10_lo") <= r <= _th(th, "L10_hi")):
        bad("P4", f"đỉnh giếng ÷ hông = {r}")
    obj_m = m.get("obj") or {}
    first = next((c["vat"] for c in spec.get("thanh_phan", []) if c.get("vai") == "chinh"), None)
    tol = _th(th, "S2_tol")
    phu, miss = {}, 0.0
    for c in spec.get("thanh_phan", []):
        k, vai = c["vat"], c.get("vai")
        e = obj_m.get(k) or {}
        o = objs.get(k) or {}
        seen = _seen(e)
        lab = o.get("label", k)
        if vai == "khong_duoc_co":
            if seen > 0:
                bad("S5", f"{lab} không được có nhưng thấy {seen:g}%")
            continue
        zone = parse_zone(c.get("vung"))
        zm = zone_miss(e.get("uv"), zone) if (zone["u"] or zone["w"]) else 0.0
        want_view = [fold(v).strip() for v in str(c.get("thay") or "").split("|") if v.strip()]
        lo_hi = c.get("co_pct")
        if lo_hi is None and k == first and spec.get("co") in FRAMING:
            share = FRAMING[spec["co"]][1] * 100
            lo_hi = [share * (1 - _th(th, "L3_rel")), share * (1 + _th(th, "L3_rel"))]
        if vai == "phu":
            phu[k] = seen > 0 and zm <= tol and (not want_view or e.get("view") in want_view)
            continue
        need = _th(th, {"nguoi": "S1_nguoi_pct", "moc": "S1_moc_pct"}.get(o.get("kind"), "S1_dao_cu_pct"))
        if c.get("thay_min") is not None:              # ngưỡng riêng của shot do người dùng/Director chấp nhận (vd qua vai: vai che một phần)
            need = float(c["thay_min"])
        if seen < need:
            b = e.get("blocked_by")
            bad("S1", f"{lab} thấy {seen:g}% (< {need:g}%)" + (f", bị che bởi {b}" if b else ""))
        if e.get("uv") is None or zm > tol:
            bad("S2", f"{lab} ở {e.get('uv')} lệch vùng '{c.get('vung')}' {zm:.2f} khung (> {tol:g})")
        miss += zm
        sz = e.get("size_pct")
        if lo_hi and (sz is None or not (lo_hi[0] <= sz <= lo_hi[1])):
            bad("S3", f"{lab} chiếm {sz}% chiều cao khung, cần {lo_hi[0]:.0f}–{lo_hi[1]:.0f}%")
        if want_view and e.get("view") not in want_view:
            bad("S4", f"{lab}: máy thấy '{e.get('view')}', cần {'/'.join(want_view)}")
    pct = m.get("percent")
    if pct:
        listed = {(objs.get(c["vat"]) or {}).get("group") for c in spec.get("thanh_phan", []) if c.get("vai") != "khong_duoc_co"}
        out_ = {g: v for g, v in pct.items() if g not in listed}
        if out_:
            g, v = max(out_.items(), key=lambda x: x[1])
            if v > _th(th, "S6_max_pct"):
                bad("S6", f"'{g}' (ngoài yêu cầu) chiếm {v}% khung (> {_th(th, 'S6_max_pct'):g}%)")
    order = ["P1", "P2", "P3", "P4", "S1", "S2", "S3", "S4", "S5", "S6"]
    fail = [c for c in order if c in why]
    return {"ok": not fail, "fail": fail, "why": {c: "; ".join(why[c]) for c in fail}, "phu": phu, "miss": round(miss, 3)}
