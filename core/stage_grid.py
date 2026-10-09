"""Lưới sân khấu (kế hoạch đặt máy 3D, ĐỔI HƯỚNG 09/10 tối — Bước 0): phần hình học thuần Python, dùng được cả trong Blender.

Quy ước (người dùng chốt 09/10):
- Gốc O cố định theo CẢNH (một lần, lưu ở stage.json, mọi shot dùng chung): xy = tâm vùng diễn (chỗ đứng chính), z = điểm tia từ trên
  xuống chạm mặt sàn tại đó → mặt phẳng z = 0 là "sàn sân khấu"; mọi chiều cao tính từ mặt này.
- Trục: +x = Đông, +y = Bắc (đúng hệ model/Blender: facing 0 = +y). Phương vị độ theo chiều kim đồng hồ từ Bắc (như plate_camera.facing).
- Ô chỉ là TÊN gọi cho người ("F8") — docs/PHUONG_PHAP_SAN_KHAU_3D.md mục 2.3: i = ⌊x/c + N/2⌋ → chữ (Tây→Đông, A…Z, AA…),
  j = ⌊y/c + N/2⌋ + 1 → số (Nam→Bắc). N = 20, c = 1 → O ở góc Tây-Nam của ô K11 (tâm K11 = (0,5; 0,5)).
  Vị trí chính xác = tọa độ liên tục (m, 2 số lẻ) so với O.
- Sàn ô: |floor_z| ≤ 0,15 m = cùng mặt sàn (đứng được); lớn hơn = bậc (≤ 0,6 m) hoặc tầng khác.
Không import gì ngoài math (Blender nạp file này theo đường dẫn).
"""
import math
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
