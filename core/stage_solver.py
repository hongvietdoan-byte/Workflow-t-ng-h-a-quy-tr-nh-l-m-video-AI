"""Sân khấu 3D v2 — K3: GIẢI máy từ yêu cầu khung của Director (docs/PHUONG_PHAP_SAN_KHAU_3D.md mục 6), thay cho dò mù 72 điểm.

Hình học thuần (0 USD, mili giây), chỉ chạy ở máy chủ; Blender chỉ đo lại phương án còn lại (giai đoạn b, tools/stage_grid.py v2).
  1. Khoảng cách từ cỡ: D_A = h_A / (2·s·tan(v/2))                                                    (6.1)
  2. Phương vị từ vùng đích của A và B: cung góc nội tiếp ∩ đường tròn (A, D_A) → ≤ 2 điểm C         (6.2)
     — chỉ một thứ chính: phương vị từ yêu cầu "thấy" (mặt: φ ± 30°, lưng: φ + 180° ± 30°, nghiêng: φ ± 90°)
  3. Độ cao theo lớp, cúi/ngửa từ vùng dọc của A                                                     (6.3)
  4. Tinh chỉnh Gauss-Newton trên phép chiếu thật (pitch ≠ 0 làm u lệch) đến khi lệch ≤ 0,02 khung
  5. Đường lùi ≈ 30 điểm quanh lời giải (α ± 5/10/15°, D ± 15 %, cao ± 0,3 m)                        (6.4)
Không tự đổi ý đồ: thiếu ý đồ hướng / mâu thuẫn → trả `errors`, không đoán.
"""
import math
from typing import Dict, List, Optional, Sequence, Tuple

from core import stage_grid as sg

TOL_UV = 0.02          # mục 6.3: lệch vùng ≤ 0,02 khung sau tinh chỉnh
W_A = 4.0              # trọng số phần dư vị trí A khi hệ dư phương trình (B có vùng dọc, máy chạm biên lớp độ cao)
DEFAULT_H = 1.7
SAME_ZONE_FAR_M = 1.0  # 3.2: hai thứ chính cùng một vùng ngang mà cách nhau hơn 1 m trên sàn → mâu thuẫn (chỉ đạt khi vật này che vật kia)


# ---- vật từ blocking.json ------------------------------------------------------------------------------------------------------
def beat_raw(blocking: Dict, beat: Optional[str] = None) -> Dict[str, Dict]:
    """Vật thô của một nhịp (3.1 "nhân vật theo từng nhịp"): `objects` gốc + `beats[beat]` ghi đè từng vật ({"hidden": true} = vắng mặt;
    ghi "at" mà không ghi "in" = bước ra khỏi giếng). Khóa vật chỉ chữ/số (tên object Blender STAGE_<KHÓA>_…)."""
    raw = {o["key"]: dict(o) for o in blocking.get("objects", [])}
    for k in raw:
        if not k.isalnum():
            raise ValueError(f"khóa vật '{k}' chỉ được chữ/số (không '_')")
    if beat is not None:
        if beat not in (blocking.get("beats") or {}):
            raise ValueError(f"nhịp '{beat}' không có trong blocking.beats ({', '.join(blocking.get('beats') or {})})")
        for k, ov in blocking["beats"][beat].items():
            if k not in raw:
                raise ValueError(f"nhịp '{beat}': vật '{k}' không có trong objects")
            if ov.get("hidden"):
                raw.pop(k)
                continue
            if "at" in ov and "in" not in ov:
                raw[k].pop("in", None)
            raw[k].update({a: b for a, b in ov.items() if b is not None})
            if ov.get("in") is None and "in" in ov:
                raw[k].pop("in", None)
    return raw


def objects_from_blocking(blocking: Dict, marks: Optional[Dict] = None, beat: Optional[str] = None) -> Dict[str, Dict]:
    """blocking.json → {key: vật} theo quy ước stage_grid v2. Vị trí so với O. Người "trong" giếng: chân = đáy giếng + in_well_foot_z,
    chỉ tính phần trên miệng. Mốc lấy từ `marks` của stage.json (vd tháp: thap_chan/thap_dinh/thap_object) — K1 đo một lần."""
    raw = beat_raw(blocking, beat)
    full = {o["key"]: o for o in blocking.get("objects", [])}
    out: Dict[str, Dict] = {}
    for k, o in raw.items():
        kind = o["kind"]
        e = {"key": k, "kind": "nguoi" if kind == "nguoi" else ("moc" if kind == "moc" else "dao_cu"), "label": o.get("label", k),
             "source": o.get("source")}
        if kind == "nguoi":
            e.update(xy=list(o.get("at", [0.0, 0.0])[:2]), z=float(o.get("z", 0.0)), H=float(o.get("H", DEFAULT_H)),
                     facing=o.get("facing"), group="nguoi_" + k.lower(), own="STAGE_" + k.upper())
            if o.get("tu_the"):
                e["tu_the"] = o["tu_the"]
            if o.get("in"):
                w = raw.get(o["in"]) or full[o["in"]]
                e["xy"] = list((o.get("at") or w["at"])[:2])    # ghi "at" = chỗ trong lòng giếng (vd bám mép gần), không thì tâm
                wz = float(w.get("z", 0.0))
                e["z"] = wz + sg.in_well_foot_z(float(w["h"]), e["H"])
                e["rim_z"] = wz + float(w["h"])
                e["in"] = o["in"]
        elif kind == "moc":
            mk = (marks or {})
            name = o.get("from_marks", k)
            if f"{name}_chan" not in mk:
                raise ValueError(f"mốc '{k}': stage.json chưa có marks.{name}_chan — chạy K1 (Bước 0) trước")
            foot, top = mk[f"{name}_chan"]["xyz"], mk[f"{name}_dinh"]["xyz"]
            ob = mk.get(f"{name}_object") or {}
            e.update(xy=[foot[0], foot[1]], z=float(foot[2]), h=float(top[2]) - float(foot[2]),
                     r=float(o.get("r", (ob.get("bbox_size_m") or [2.0])[0] / 2)), group=o.get("group", name), own=ob.get("name", "~"))
        else:
            e.update(xy=list(o["at"][:2]), z=float(o.get("z", 0.0)), h=float(o["h"]), r=float(o.get("d", 1.0)) / 2,
                     group=o.get("group", "gieng" if kind == "gieng" else k), own=o.get("own", "STAGE_WELL" if kind == "gieng" else "STAGE_" + k.upper()),
                     hollow=bool(o.get("hollow")), shape=kind)
        out[k] = e
    return out


# ---- kiểm yêu cầu trước khi giải (3.2) -----------------------------------------------------------------------------------------
def validate(spec: Dict, objs: Dict[str, Dict]) -> List[str]:
    errs = []
    co = spec.get("co")
    if co not in sg.FRAMING:
        errs.append(f"cỡ '{co}' không có trong bảng ({', '.join(sg.FRAMING)})")
    if sg.fold(spec.get("do_cao") or "ngang") not in ("ngang", "thap", "cao", "tren dau", "tren_dau"):
        errs.append(f"độ cao máy '{spec.get('do_cao')}' không hợp lệ (ngang / thấp / cao / trên đầu)")
    if spec.get("goc") and sg.fold(spec["goc"]) not in sg.GOC:
        errs.append(f"góc '{spec['goc']}' không hợp lệ (ngang / cúi / ngửa)")
    chinh = []
    for c in spec.get("thanh_phan", []):
        if c.get("vat") not in objs:
            errs.append(f"'{c.get('vat')}' không có trong dàn cảnh ({', '.join(objs)})")
            continue
        if c.get("vai") not in sg.ROLES:
            errs.append(f"{c['vat']}: vai '{c.get('vai')}' không hợp lệ ({', '.join(sg.ROLES)})")
        try:
            z = sg.parse_zone(c.get("vung"))
        except ValueError as e:
            errs.append(f"{c['vat']}: {e}")
            continue
        for v in str(c.get("thay") or "").split("|"):
            if v.strip() and sg.fold(v).strip() not in sg.VIEWS:
                errs.append(f"{c['vat']}: thấy '{v}' không hợp lệ (mặt / lưng / nghiêng)")
            elif v.strip() and objs[c["vat"]]["kind"] != "nguoi":
                errs.append(f"{c['vat']}: 'thấy mặt/lưng' chỉ dùng cho người")
        if c.get("vai") == "chinh":
            chinh.append((c["vat"], z))
    if not chinh:
        errs.append("không có thứ 'chinh' nào — Director phải ghi thứ bắt buộc trong khung")
    for i in range(len(chinh)):
        for j in range(i + 1, len(chinh)):
            (ka, za), (kb, zb) = chinh[i], chinh[j]
            # cùng ô ngang VÀ không tách được theo dọc (cùng ô dọc / không ghi dọc) → một vật phải che vật kia; khác hàng dọc thì
            # máy cao nhìn qua đầu vật gần được (09/10: sau lưng Kelly ngã, giếng ở trên — bị chặn oan lần đầu)
            if za["u"] and zb["u"] and za["u"] == zb["u"] and za["w"] == zb["w"]:
                d = math.dist(objs[ka]["xy"], objs[kb]["xy"])
                if d > SAME_ZONE_FAR_M:
                    errs.append(f"mâu thuẫn: {ka} và {kb} cùng vùng ngang mà cách nhau {d:.2f} m trên sàn (chỉ đạt khi vật này che vật kia)")
    return errs


# ---- hình học giải (6.1–6.2) ---------------------------------------------------------------------------------------------------
def _wrap(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


def signed_angle(C: Sequence[float], A: Sequence[float], B: Sequence[float]) -> float:
    """Góc ngang (độ) máy C thấy từ A sang B, dương khi B ở bên PHẢI A trong khung (phương vị theo chiều kim đồng hồ)."""
    return _wrap(sg.bearing_deg(B[0] - C[0], B[1] - C[1]) - sg.bearing_deg(A[0] - C[0], A[1] - C[1]))


def gamma_for(u_a: float, u_b: float, th: float) -> float:
    """6.2: γ = atan((u_B − 0,5)·2·tan(h/2)) − atan((u_A − 0,5)·2·tan(h/2)), độ (máy ngang)."""
    return math.degrees(math.atan((u_b - 0.5) * 2 * th) - math.atan((u_a - 0.5) * 2 * th))


def inscribed_solutions(A: Sequence[float], B: Sequence[float], gamma_deg: float, d_a: float) -> List[Tuple[float, float]]:
    """6.2: điểm C trên sàn thấy đoạn AB dưới góc có dấu γ (cung góc nội tiếp, bán kính L/(2 sin γ)) và cách A đúng d_a (ngang).
    Cung đối xứng cho góc ngược dấu → tự bị loại khi so dấu. Trả ≤ 2 điểm."""
    ax, ay, bx, by = float(A[0]), float(A[1]), float(B[0]), float(B[1])
    L = math.hypot(bx - ax, by - ay)
    g = math.radians(abs(gamma_deg))
    if L < 1e-6 or g < 1e-6 or g >= math.pi - 1e-6:
        return []
    R = L / (2 * math.sin(g))
    mx, my = (ax + bx) / 2, (ay + by) / 2
    nx, ny = -(by - ay) / L, (bx - ax) / L
    off = L / (2 * math.tan(g))
    out = []
    for s in (1.0, -1.0):
        ox, oy = mx + s * nx * off, my + s * ny * off
        dd = math.hypot(ox - ax, oy - ay)                   # = R (A nằm trên cung) → giao hai đường tròn (O, R) và (A, d_a)
        if dd < 1e-9 or d_a > dd + R + 1e-9 or d_a < abs(dd - R) - 1e-9:
            continue
        a = (d_a * d_a - R * R + dd * dd) / (2 * dd)
        h = math.sqrt(max(d_a * d_a - a * a, 0.0))
        px, py = ax + a * (ox - ax) / dd, ay + a * (oy - ay) / dd
        for t in (1.0, -1.0):
            C = (px + t * h * (oy - ay) / dd, py - t * h * (ox - ax) / dd)
            if abs(signed_angle(C, A, B) - gamma_deg) < 1e-4 and all(math.dist(C, q) > 1e-3 for q in out):
                out.append(C)
    return out


def distance_for_size(h_real: float, share: float, tv: float) -> float:
    """6.1: D_A = h_A / (2·s·tan(v/2))."""
    return h_real / (2 * share * tv)


def bearings_from_view(facing: float, view: str) -> List[float]:
    """Chỉ một thứ chính: phương vị máy (đứng ở đâu so với A) từ yêu cầu thấy. Mặt: φ ± 30° rồi φ; lưng: φ + 180° ± 30° rồi φ + 180°."""
    if view == "mat":
        return [(facing + 30) % 360, (facing - 30) % 360, facing % 360]
    if view == "lung":
        return [(facing + 150) % 360, (facing + 210) % 360, (facing + 180) % 360]
    return [(facing + 90) % 360, (facing - 90) % 360]


# ---- máy: tham số hóa + tinh chỉnh (6.3) ---------------------------------------------------------------------------------------
def _cam(A, theta, d, cz):
    a = math.radians(theta)
    return (A[0] + math.sin(a) * d, A[1] + math.cos(a) * d, cz)


def _aim(C, yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return (C[0] + math.cos(p) * math.sin(y), C[1] + math.cos(p) * math.cos(y), C[2] + math.sin(p))


def _solve_lin(M, b):
    n = len(b)
    a = [row[:] + [b[i]] for i, row in enumerate(M)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(a[r][c]))
        if abs(a[piv][c]) < 1e-12:
            return None
        a[c], a[piv] = a[piv], a[c]
        for r in range(n):
            if r != c:
                f = a[r][c] / a[c][c]
                for k in range(c, n + 1):
                    a[r][k] -= f * a[c][k]
    return [a[i][n] / a[i][i] for i in range(n)]


def gauss_newton(fun, x0: List[float], steps: int = 25, lam: float = 1e-6, h: float = 1e-4):
    """Bình phương tối thiểu nhỏ (≤ 4 biến): Jacobian số, có giảm bước. fun(x) → list phần dư (None = phương án hỏng)."""
    x = list(x0)
    r = fun(x)
    if r is None:
        return x, None
    cost = sum(v * v for v in r)
    for _ in range(steps):
        J = []
        for i in range(len(x)):
            xp = list(x)
            xp[i] += h
            rp = fun(xp)
            if rp is None:
                return x, r
            J.append([(rp[k] - r[k]) / h for k in range(len(r))])
        n = len(x)
        M = [[sum(J[i][k] * J[j][k] for k in range(len(r))) + (lam if i == j else 0.0) for j in range(n)] for i in range(n)]
        g = [-sum(J[i][k] * r[k] for k in range(len(r))) for i in range(n)]
        dx = _solve_lin(M, g)
        if dx is None:
            break
        t, improved = 1.0, False
        for _ in range(8):
            xn = [x[i] + t * dx[i] for i in range(n)]
            rn = fun(xn)
            if rn is not None and sum(v * v for v in rn) < cost:
                x, r, cost, improved = xn, rn, sum(v * v for v in rn), True
                break
            t /= 2
        if not improved or max(abs(v) for v in r) < 1e-5:
            break
    return x, r


class Shot:
    """Một yêu cầu khung đã chuẩn hóa: A, B, đích (u, w), cỡ, ống kính, độ cao máy."""

    def __init__(self, spec: Dict, objs: Dict[str, Dict], aspect: float):
        self.spec, self.objs, self.aspect = spec, objs, aspect
        self.co = spec["co"]
        self.lens = float(spec.get("ong_kinh") or sg.FRAMING[self.co][2])
        self.th, self.tv = sg._tans(self.lens, aspect)
        chinh = [c for c in spec["thanh_phan"] if c.get("vai") == "chinh"]
        self.a = chinh[0]
        zA = sg.parse_zone(self.a.get("vung"))
        self.A = objs[self.a["vat"]]
        # không ghi vùng dọc: người → mắt trên đường 1/3 trên (quy ước khung), vật → giữa khung
        self.uA, self.wA = sg.zone_centre(zA, default_w=1 / 3 if self.A["kind"] == "nguoi" else 0.5)
        self.uA = 0.5 if self.uA is None else self.uA
        self.pA = sg.zone_point(self.A, self.co)
        t, b = sg.size_span(self.A, self.co)
        self.hA = t[2] - b[2]
        cp = self.a.get("co_pct")
        self.share = (cp[0] + cp[1]) / 200.0 if cp else sg.FRAMING[self.co][1]
        rel = sg.RULE_TH["L3_rel"][0]
        self.share_range = (cp[0] / 100.0, cp[1] / 100.0) if cp else (self.share * (1 - rel), self.share * (1 + rel))
        # B = thứ chính thứ hai, hoặc thứ phụ có vùng ngang (mốc thứ hai — 6.2)
        self.b = None
        for c in chinh[1:] + [c for c in spec["thanh_phan"] if c.get("vai") == "phu"]:
            z = sg.parse_zone(c.get("vung"))
            if z["u"] is not None and math.dist(objs[c["vat"]]["xy"], self.A["xy"]) > 0.05:
                self.b = c
                self.uB, self.wB = sg.zone_centre(z)
                self.B = objs[c["vat"]]
                self.pB = sg.zone_point(self.B)
                self.b_weight = 1.0 if c.get("vai") == "chinh" else 0.5
                break
        layer = sg.fold(spec.get("do_cao") or "ngang").replace(" ", "_")
        Hs = [o["H"] for o in objs.values() if o["kind"] == "nguoi"]
        H = self.A["H"] if self.A["kind"] == "nguoi" else (max(Hs) if Hs else DEFAULT_H)
        self.layer = layer
        hs = sg.layer_heights(layer, H)
        self.cz = float(spec["cao_m"]) if spec.get("cao_m") is not None else hs[1]
        # B có cả vùng dọc → 5 phần dư, thả độ cao máy trong lớp (± 0,3 m) để hệ đủ ẩn (6.3: "cho pitch, giải ra C_z")
        self.cz_range = None if (spec.get("cao_m") is not None or self.b is None or self.wB is None) else (hs[0] - 0.3, hs[-1] + 0.3)

    def residuals(self, C, aim, with_size=True, with_b=True):
        pa = sg.project(C, aim, self.pA, self.lens, self.aspect)
        if pa is None:
            return None
        r = [W_A * (pa[0] - self.uA), W_A * (pa[1] - self.wA)]       # A (thứ chính đầu tiên) ưu tiên: không đạt hết thì B/cỡ chịu lệch
        if with_b and self.b is not None:
            pb = sg.project(C, aim, self.pB, self.lens, self.aspect)
            if pb is None:
                return None
            r.append(self.b_weight * (pb[0] - self.uB))
            if self.wB is not None:
                r.append(0.5 * self.b_weight * (pb[1] - self.wB))
        if with_size:
            t, b = sg.size_span(self.A, self.co)
            pt, pb_ = sg.project(C, aim, t, self.lens, self.aspect), sg.project(C, aim, b, self.lens, self.aspect)
            if pt is None or pb_ is None:
                return None
            r.append((pb_[1] - pt[1]) - self.share)
        return r

    def initial_aim(self, C):
        dx, dy, dz = self.pA[0] - C[0], self.pA[1] - C[1], self.pA[2] - C[2]
        yaw = sg.bearing_deg(dx, dy) - math.degrees(math.atan((self.uA - 0.5) * 2 * self.th))
        pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy))) - math.degrees(math.atan((0.5 - self.wA) * 2 * self.tv))
        return yaw, pitch

    def refine(self, theta, d, cz, free_theta=True, free_d=True):
        """Tinh chỉnh (6.3): biến = [θ?, d?, cao?, yaw, pitch]; dư = A về vùng, B về vùng, cỡ A."""
        A = self.A["xy"]
        yaw0, p0 = self.initial_aim(_cam(A, theta, d, cz))
        free_z = free_theta and free_d and self.cz_range is not None

        def unpack(x):
            k = 0
            th_, d_, z_ = theta, d, cz
            if free_theta:
                th_, k = x[k], k + 1
            if free_d:
                d_, k = x[k], k + 1
            if free_z:                                   # kẹp trong lớp (không trả None ở biên → GN vẫn trượt theo các biến khác)
                z_, k = min(max(x[k], self.cz_range[0]), self.cz_range[1]), k + 1
            return th_, d_, z_, x[k], x[k + 1]

        def fun(x):
            th_, d_, z_, yw, pt = unpack(x)
            if d_ < 0.2 or abs(pt) > 85:
                return None
            C = _cam(A, th_, d_, z_)
            return self.residuals(C, _aim(C, yw, pt), with_size=free_d, with_b=free_theta)
        x0 = ([theta] if free_theta else []) + ([d] if free_d else []) + ([cz] if free_z else []) + [yaw0, p0]
        x, r = gauss_newton(fun, x0)
        th_, d_, cz, yw, pt = unpack(x)
        C = _cam(A, th_, d_, cz)
        return {"theta": th_ % 360, "d": d_, "cz": cz, "at": [round(v, 3) for v in C], "aim": [round(v, 4) for v in _aim(C, yw, pt)],
                "yaw": yw % 360, "pitch": pt, "resid": None if r is None else round(max(abs(v) for v in r), 4)}


def _horizontal(d_slant: float, dz: float) -> float:
    return math.sqrt(d_slant * d_slant - dz * dz) if abs(dz) < d_slant else 0.34 * d_slant


def solve_shot(spec: Dict, objs: Dict[str, Dict], aspect: float, axis: Optional[Sequence] = None, s0: Optional[str] = None,
               grid: Optional[Dict[str, Dict]] = None, stage: Optional[Dict] = None, fallback: bool = True) -> Dict:
    """K3 cho một shot: lời giải (≤ 2–3) + đường lùi ≈ 30 điểm, mỗi phương án kèm frame_eval + check_spec giai đoạn (a), ô sàn dưới
    máy (grid.json nếu có), phía trục (C1). Xếp: đạt trước, rồi ít lệch vùng, rồi nhiều thứ phụ đạt. Không có lời giải → `errors`."""
    pov = spec.get("pov")
    errs = []
    if pov and pov not in objs:
        errs.append(f"pov '{pov}' không có trong dàn cảnh của nhịp")
    if spec.get("may"):
        errs += move_errors(spec["may"])
    eye = None
    if pov and pov in objs:                            # góc nhìn nhân vật: máy ở MẮT người đó, người đó không có trong khung
        po = objs[pov]
        eye = (po["xy"][0], po["xy"][1], po.get("z", 0.0) + sg.EYE * po["H"])
        objs = {k: v for k, v in objs.items() if k != pov}
    errs = validate(spec, objs) + errs
    res = {"shot": spec.get("shot"), "muc_dich": spec.get("muc_dich"), "errors": errs, "notes": [], "cams": [], "pov": pov,
           "objs_used": list(objs)}
    if errs:
        return res
    sh = Shot(spec, objs, aspect)
    A = sh.A["xy"]
    D = distance_for_size(sh.hA, sh.share, sh.tv)
    d0 = _horizontal(D, sh.pA[2] - sh.cz)
    starts = []                                        # (θ, d, tag, free_theta, free_d)
    if eye is not None:
        sh.cz = eye[2]
        th_e, d_e = sg.bearing_deg(eye[0] - A[0], eye[1] - A[1]), math.hypot(eye[0] - A[0], eye[1] - A[1])
        sol = sh.refine(th_e, d_e, sh.cz, free_theta=False, free_d=False)
        res["cams"].append(_judge(sh, sol, f"góc nhìn {pov} (máy ở mắt, cao {eye[2]:.2f} m)", axis, s0, grid, stage))
        res["lens"], res["layer"], res["share"], res["D_A"] = sh.lens, "pov", sh.share, round(D, 3)
        res["advice"] = advise(res, sh)
        return res
    if sh.b is not None:
        g = gamma_for(sh.uA, sh.uB, sh.th)
        if abs(g) < 0.5:                               # cùng cột dọc: máy trên đường B→A kéo dài (B ở sau A, vd giếng sau lưng yêu nữ)
            Bx = sh.B["xy"]
            starts.append((sg.bearing_deg(A[0] - Bx[0], A[1] - Bx[1]), d0, f"thẳng hàng {sh.b['vat']} sau {sh.a['vat']} (γ ≈ 0)", False, True))
        for C in ([] if starts else inscribed_solutions(A, sh.B["xy"], g, d0)):
            starts.append((sg.bearing_deg(C[0] - A[0], C[1] - A[1]), d0, f"giải góc nội tiếp γ {g:.1f}°", True, True))
        if not starts and abs(g) >= 0.5:
            # cỡ là một KHOẢNG (co_pct, hoặc bảng cỡ ± 15 %): thử khoảng cách khác trong khoảng đó, gần đích nhất trước; giữ khoảng cách cố định
            lo, hi = sh.share_range
            dmin, dmax = (_horizontal(distance_for_size(sh.hA, x, sh.tv), sh.pA[2] - sh.cz) for x in (hi, lo))
            for d_ in sorted((dmin + (dmax - dmin) * k / 12 for k in range(13)), key=lambda v: abs(v - d0)):
                sols = inscribed_solutions(A, sh.B["xy"], g, d_)
                if sols:
                    for C in sols:
                        starts.append((sg.bearing_deg(C[0] - A[0], C[1] - A[1]), d_,
                                       f"giải góc nội tiếp γ {g:.1f}° ở {d_:.2f} m (mép khoảng cỡ)", True, False))
                    res["notes"].append(f"ở khoảng đích {d0:.2f} m không có điểm thấy {sh.a['vat']}→{sh.b['vat']} dưới {g:.1f}° → dùng "
                                        f"{d_:.2f} m, vẫn trong khoảng cỡ {lo * 100:.0f}–{hi * 100:.0f}%")
                    break
        if not starts:
            res["notes"].append(f"không có điểm thấy {sh.a['vat']}→{sh.b['vat']} dưới góc {g:.1f}° ở mọi khoảng cách của cỡ — thử theo hướng thấy")
    if not starts:
        view = sg.fold(str(sh.a.get("thay") or "").split("|")[0]).strip()
        if view in sg.VIEWS and sh.A.get("facing") is not None:
            for th_ in bearings_from_view(float(sh.A["facing"]), view):
                starts.append((th_, d0, f"theo hướng thấy '{view}' (φ {sh.A['facing']:g}°)", False, True))
        else:
            res["errors"].append("thiếu ý đồ hướng: chỉ một thứ chính, không có thứ thứ hai có vùng ngang, không ghi 'thấy' mặt/lưng — "
                                 "Director ghi thêm (không tự chọn)")
            return res
    seen = []
    for th_, d_, tag, free_t, free_d in starts:
        sol = sh.refine(th_, d_, sh.cz, free_theta=free_t, free_d=free_d)
        if any(math.dist(sol["at"], q) < 0.05 for q in seen):
            continue
        seen.append(sol["at"])
        res["cams"].append(_judge(sh, sol, tag, axis, s0, grid, stage))
    if fallback and res["cams"]:
        base = sorted(res["cams"], key=_rank)[0]
        for k, (dth, kd, dz) in enumerate(_fallback_steps()):
            sol = sh.refine(base["theta"] + dth, base["d"] * kd, base["cz"] + dz, free_theta=False, free_d=False)
            sol["theta"], sol["d"] = (base["theta"] + dth) % 360, base["d"] * kd
            res["cams"].append(_judge(sh, sol, f"lùi α{dth:+g}° D×{kd:g} cao{dz:+g}", axis, s0, grid, stage, fallback=True))
    res["cams"].sort(key=_rank)
    res["lens"], res["layer"], res["share"], res["D_A"] = sh.lens, sh.layer, sh.share, round(D, 3)
    res["advice"] = advise(res, sh)
    return res


def advise(res: Dict, sh: "Shot") -> List[str]:
    """Nguyên tắc 4 (không im lặng): không phương án nào đạt → nói luật nào hỏng ở MỌI phương án + gợi ý sửa dàn cảnh/yêu cầu (người dùng quyết)."""
    cams = res["cams"]
    if not cams or any(c["check"]["ok"] and c["c1_ok"] for c in cams):
        return []
    n = len(cams)
    cnt: Dict[str, int] = {}
    for c in cams:
        for f in c["check"]["fail"] + ([] if c["c1_ok"] else ["C1"]):
            cnt[f] = cnt.get(f, 0) + 1
    th_lo, th_hi = min(c["theta"] for c in cams), max(c["theta"] for c in cams)
    hint = {"P1": "máy rơi vào ô không đứng được → đổi cỡ (máy xa/gần hơn) hoặc dời người 1 ô",
            "P3": f"pitch không hợp góc '{sh.spec.get('goc')}' → đổi độ cao máy (đang {sh.cz:.2f} m) hoặc vùng dọc của {sh.a['vat']}",
            "S1": "thứ chính bị che / lọt khung → dời vật che hoặc đổi cỡ",
            "S2": "không đặt được vào vùng đích → đổi vùng hoặc cỡ (hai thứ quá xa / quá gần nhau so với khung)",
            "S3": "cỡ không khớp → sửa co_pct hoặc cỡ cảnh",
            "S4": "hướng thấy không khớp chỗ máy bị ép tới (vùng trái/phải + khoảng cách theo cỡ) → đổi cỡ (máy xa/gần hơn), đảo vùng ngang "
                  "của hai thứ chính, hoặc bỏ yêu cầu 'thấy'",
            "S5": "thứ 'không được có' lọt khung → đổi hướng / ống kính dài hơn",
            "S6": "khung bị sàn/tường nuốt → hạ máy hoặc đổi góc",
            "C1": "vượt trục 180° → đảo vùng trái/phải hoặc ghi cross_ok nếu cố ý"}
    out = []
    for f, k in sorted(cnt.items(), key=lambda x: -x[1]):
        if k == n:
            ex = next((c["check"]["why"].get(f) for c in cams if f in c["check"]["why"]), None) or ""
            out.append(f"{f} hỏng ở cả {n} phương án (α {th_lo:.0f}–{th_hi:.0f}°){': ' + ex if ex else ''} → {hint.get(f, '')}")
    if not out:
        out.append(f"mỗi phương án hỏng một luật khác nhau ({', '.join(f'{f}×{k}' for f, k in cnt.items())}) → xem bảng, sửa yêu cầu")
    return out


def _fallback_steps():
    """6.4: ≈ 30 điểm quanh lời giải: α {0, ±5, ±10, ±15} × D {0,85; 1; 1,15} (21) + cao ± 0,3 m ở α {0, ±5} (6)."""
    out = [(a, k, 0.0) for a in (0, -5, 5, -10, 10, -15, 15) for k in (1.0, 0.85, 1.15) if not (a == 0 and k == 1.0)]
    out += [(a, 1.0, dz) for a in (0, -5, 5) for dz in (-0.3, 0.3)]
    return out


MOVES = {"lui": -1.0, "tien": 1.0}


def move_errors(mv: Dict) -> List[str]:
    k = sg.fold(mv.get("kieu") or "")
    if k not in MOVES:
        return [f"chuyển động máy '{mv.get('kieu')}' chưa hỗ trợ (lui / tien)"]
    if not (0 < float(mv.get("m") or 0) <= 5):
        return [f"quãng máy di chuyển {mv.get('m')} m phải trong (0; 5]"]
    return []


def move_end(C, aim, mv: Dict):
    """Khung CUỐI của máy lùi/tiến: dời song song theo hướng nhìn trên mặt ngang `m` mét (giữ hướng, giữ cao). Rung = ghi chú cho prompt
    chuyển động, không đổi khung."""
    f = [aim[0] - C[0], aim[1] - C[1]]
    n = math.hypot(*f) or 1.0
    k = MOVES[sg.fold(mv["kieu"])] * float(mv["m"]) / n
    dx, dy = f[0] * k, f[1] * k
    return [round(C[0] + dx, 3), round(C[1] + dy, 3), C[2]], [round(aim[0] + dx, 4), round(aim[1] + dy, 4), aim[2]]


def end_spec(spec: Dict) -> Dict:
    """Luật ở khung cuối chuyển động: vẫn đủ thứ chính / không có thứ cấm / đúng hướng thấy, nhưng cỡ + vùng được đổi theo chuyển động
    (máy lùi thì vật nhỏ lại, dồn về giữa) → bỏ co_pct, cỡ mặc định và vùng."""
    e = dict(spec, co=None)
    e["thanh_phan"] = [{k: v for k, v in c.items() if k not in ("co_pct", "vung")} for c in spec["thanh_phan"]]
    return e


def _p1_grid(C, grid, stage):
    if grid is None or stage is None:
        return None
    cell = sg.cell_name(stage, C[0], C[1])
    g = grid.get(cell) if cell else None
    if g is None or g.get("status") != "same" or g.get("obstacle"):
        return f"ô {cell}: {'ngoài lưới' if g is None else g.get('status')}{', vật chắn' if g and g.get('obstacle') else ''}"
    return None


def _judge(sh: Shot, sol: Dict, tag: str, axis, s0, grid, stage, fallback=False) -> Dict:
    C, aim = sol["at"], sol["aim"]
    ev = sg.frame_eval(C, aim, sh.lens, sh.aspect, sh.objs, co=sh.co, size_key=sh.a["vat"])
    m = dict(ev)
    pre = _p1_grid(C, grid, stage)
    chk = sg.check_spec(m, sh.spec, sh.objs)
    if pre:
        chk["fail"] = ["P1"] + [f for f in chk["fail"] if f != "P1"]
        chk["why"]["P1"] = pre
        chk["ok"] = False
    end = None
    if sh.spec.get("may"):
        Ce, Ae = move_end(C, aim, sh.spec["may"])
        eve = sg.frame_eval(Ce, Ae, sh.lens, sh.aspect, sh.objs)
        ce = sg.check_spec(dict(eve), end_spec(sh.spec), sh.objs)
        pe = _p1_grid(Ce, grid, stage)
        if pe:
            ce["fail"] = ["P1"] + [f for f in ce["fail"] if f != "P1"]
            ce["why"]["P1"] = pe
            ce["ok"] = False
        end = {"at": Ce, "aim": Ae, "eval": eve, "check": ce, "cell": None if stage is None else sg.cell_name(stage, Ce[0], Ce[1])}
        if not ce["ok"]:                               # khung cuối hỏng = phương án hỏng (ghi mã 'cuối:…')
            chk["ok"] = False
            chk["fail"] = chk["fail"] + [f"cuoi:{f}" for f in ce["fail"]]
            chk["why"].update({f"cuoi:{k}": v for k, v in ce["why"].items()})
    side = None if not axis else sg.axis_side(axis[0], axis[1], C)
    c1 = not (s0 and side not in (s0, "on") and not sh.spec.get("cross_ok"))
    return {"tag": tag, "fallback": fallback, "at": C, "aim": aim, "lens": sh.lens, "yaw": round(sol["yaw"], 2),
            "pitch": round(sol["pitch"], 2), "theta": round(sol["theta"], 2), "d": round(sol["d"], 3), "cz": round(sol["cz"], 3),
            "resid": sol["resid"], "cell": None if stage is None else sg.cell_name(stage, C[0], C[1]), "side": side, "c1_ok": c1,
            "eval": ev, "check": chk, "end": end}


def _rank(c: Dict):
    return (not (c["check"]["ok"] and c["c1_ok"]), not c["c1_ok"], len(c["check"]["fail"]), c["check"]["miss"],
            -sum(c["check"]["phu"].values()), c["fallback"])


def solve_scene(specs: List[Dict], blocking: Dict, aspect: float, marks: Optional[Dict] = None, grid_cells: Optional[List[Dict]] = None,
                stage: Optional[Dict] = None) -> Dict:
    """K3 cho cả cảnh: trục (blocking.axis = [key, key]) + phía máy s₀ (blocking.s0, hoặc lấy từ lời giải tốt nhất của shot đầu)."""
    objs = objects_from_blocking(blocking, marks)
    grid = {c["cell"]: c for c in grid_cells} if grid_cells else None
    s0 = blocking.get("s0")
    shots, beats = [], {}

    def axis_of(o):
        if not blocking.get("axis"):
            return None
        a, b = blocking["axis"]
        return [list(o[a]["xy"]) + [0.0], list(o[b]["xy"]) + [0.0]] if a in o and b in o else None
    axis = axis_of(objs)
    for sp in specs:
        bo = objects_from_blocking(blocking, marks, sp["nhip"]) if sp.get("nhip") else objs
        beats[sp.get("nhip") or ""] = bo
        r = solve_shot(sp, bo, aspect, axis=axis_of(bo), s0=s0, grid=grid, stage=stage)
        r["nhip"] = sp.get("nhip")
        if s0 is None and r["cams"] and axis:
            s0 = r["cams"][0]["side"] if r["cams"][0]["side"] != "on" else None
            if s0:
                r["notes"].append(f"shot mở chọn phía trục s₀ = {s0}")
        shots.append(r)
    return {"objs": objs, "beats": beats, "axis": axis, "s0": s0, "shots": shots}
