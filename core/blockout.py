"""Nhánh C, mục 12b: schema + kiểm số thuần Python; CHƯA nối pipeline, không đọc Kho/data hay gọi Blender/model.

Mét, x Đông/y Bắc/z lên; `san={kich_thuoc:[dai,rong], z:0}` quanh O.
Khối có tam [x,y], kich_thuoc [[min,max] × 3], nguon kho/vat_quen/anh, huong độ quay quanh +z,
mo_ta_ngan, tùy chọn vat_kho, z (chân, mặc định sàn), kich_thuoc_chuan [dai,rong,cao] từ Kho/vật quen.
loi_mo là các vùng trống {tam:[x,y], kich_thuoc:[dai,rong], huong:0}; huong_sang là độ.
Nguồn Kho/vật quen thiếu số chuẩn → VÀNG, không giả vờ đã đối chiếu. Khoảng được lấy giữa khi kiểm/dựng;
chưa đo chiếu ngược (12b.1c), chưa lưu/duyệt Kho (12b.2). Khối cây/xe/cửa chỉ là hộp thay thế.
"""
import math
from itertools import combinations

TYPES = ("tuong", "bac", "cot", "hop", "tru", "cua", "lan_can", "mai", "cay_khoi", "xe_khoi")
SOURCES = ("kho", "vat_quen", "anh")
WALKWAY = .8
FLOOR_TOL = .05
OVERLAP_SHARE = .02  # Tạm: giao chân đế > 2% chân đế nhỏ hơn và giao chiều cao > 5 cm (bắt cả tường mỏng giao nhau).
# Chỉ cho mái chạm ĐỈNH tường/cột/trụ, không bỏ qua khi mái xuyên thân vật đỡ.
ROOF_SUPPORTS = ("tuong", "cot", "tru")


def _issue(level, path, reason, code="schema"):
    return {"muc": level, "path": path, "truong": path, "loi": reason, "code": code}


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _vector(v, n, positive=False):
    return isinstance(v, (list, tuple)) and len(v) == n and all(_number(x) and (not positive or x > 0) for x in v)


def validate(plan):
    """Sai schema → issue ĐỎ có đường dẫn, không nuốt đầu vào thiếu/hỏng."""
    out = []

    def need(ok, path, why):
        if not ok:
            out.append(_issue("do", path, why))
    if not isinstance(plan, dict):
        return [_issue("do", "plan", "phải là object")]
    floor = plan.get("san")
    need(isinstance(floor, dict), "san", "thiếu object sàn")
    if isinstance(floor, dict):
        need(_vector(floor.get("kich_thuoc"), 2, True), "san.kich_thuoc", "cần [dài, rộng] dương, hữu hạn (m)")
        need(_number(floor.get("z", 0)), "san.z", "cao độ sàn phải hữu hạn")
    need(_number(plan.get("huong_sang")), "huong_sang", "thiếu góc hướng sáng hữu hạn (độ)")
    blocks = plan.get("khoi")
    need(isinstance(blocks, list), "khoi", "thiếu danh sách khối")
    ids = set()
    for i, b in enumerate(blocks if isinstance(blocks, list) else []):
        p = f"khoi[{i}]"
        if not isinstance(b, dict):
            need(False, p, "khối phải là object")
            continue
        key = b.get("id")
        need(isinstance(key, str) and bool(key.strip()), p + ".id", "thiếu id chữ")
        if isinstance(key, str):
            need(key not in ids, p + ".id", "id trùng")
            ids.add(key)
        need(b.get("loai") in TYPES, p + ".loai", "loại khối không hợp lệ")
        need(b.get("nguon") in SOURCES, p + ".nguon", "nguồn phải là kho / vat_quen / anh")
        need(_vector(b.get("tam"), 2), p + ".tam", "cần [x,y] hữu hạn (m)")
        need(_number(b.get("huong")), p + ".huong", "thiếu góc hữu hạn (độ)")
        need(_number(b.get("z", 0)), p + ".z", "cao độ chân phải hữu hạn")
        need(isinstance(b.get("mo_ta_ngan"), str) and bool(b["mo_ta_ngan"].strip()), p + ".mo_ta_ngan", "thiếu mô tả ngắn")
        dims = b.get("kich_thuoc")
        need(isinstance(dims, list) and len(dims) == 3, p + ".kich_thuoc", "cần ba khoảng [min,max] dài/rộng/cao")
        for j, interval in enumerate(dims if isinstance(dims, list) and len(dims) == 3 else []):
            need(_vector(interval, 2, True) and interval[0] <= interval[1], f"{p}.kich_thuoc[{j}]", "khoảng phải dương, hữu hạn, min ≤ max")
        if "kich_thuoc_chuan" in b:
            need(_vector(b["kich_thuoc_chuan"], 3, True), p + ".kich_thuoc_chuan", "số chuẩn dài/rộng/cao phải dương")
        if "vat_kho" in b:
            need(isinstance(b["vat_kho"], (str, int)) and not isinstance(b["vat_kho"], bool), p + ".vat_kho", "mã Kho phải là chữ/số")
    openings = plan.get("loi_mo")
    need(isinstance(openings, list), "loi_mo", "thiếu danh sách lối mở")
    for i, op in enumerate(openings if isinstance(openings, list) else []):
        p = f"loi_mo[{i}]"
        if not isinstance(op, dict):
            need(False, p, "lối mở phải là object")
            continue
        need(_vector(op.get("tam"), 2), p + ".tam", "cần [x,y] hữu hạn")
        need(_vector(op.get("kich_thuoc"), 2, True), p + ".kich_thuoc", "cần dài/rộng dương")
        need(_number(op.get("huong", 0)), p + ".huong", "góc phải hữu hạn")
    return out


def _size(b):
    return [(lo + hi) / 2 for lo, hi in b["kich_thuoc"]]


def _rect(xy, size, angle):
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    return [(xy[0] + c * x - s * y, xy[1] + s * x + c * y)
            for x, y in [(-size[0] / 2, -size[1] / 2), (size[0] / 2, -size[1] / 2),
                         (size[0] / 2, size[1] / 2), (-size[0] / 2, size[1] / 2)]]


def _cross(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _inside(p, poly):
    return all(_cross(a, b, p) >= -1e-9 for a, b in zip(poly, poly[1:] + poly[:1]))


def _area(poly):
    return abs(sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def _intersection(subject, clip):
    """Giao hai đa giác lồi, giữ góc xoay (không dùng AABB để kết luận khối xoay chồng)."""
    out = subject[:]
    for a, b in zip(clip, clip[1:] + clip[:1]):
        old, out = out, []
        if not old:
            break
        prev = old[-1]
        for curr in old:
            dp, dc = _cross(a, b, prev), _cross(a, b, curr)
            if (dp >= 0) != (dc >= 0):
                t = dp / (dp - dc)
                out.append((prev[0] + t * (curr[0] - prev[0]), prev[1] + t * (curr[1] - prev[1])))
            if dc >= 0:
                out.append(curr)
            prev = curr
    return out


def _point_distance(p, poly):
    if _inside(p, poly):
        return 0.0
    ds = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        ds.append(math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy))
    return min(ds)


def check_geometry(plan, cho_dung=None, vat_kich_ban=None):
    """Kiểm 12b.1 a/b/d ở giữa khoảng; chỉ kết luận số, không tự sửa sơ đồ."""
    out = validate(plan)
    if out:
        return out
    blocks = plan["khoi"]
    sizes = [_size(b) for b in blocks]
    polys = [_rect(b["tam"], d, b["huong"]) for b, d in zip(blocks, sizes)]
    floor_z = plan["san"].get("z", 0)
    bases = [b.get("z", floor_z) for b in blocks]
    tops = [z + d[2] for z, d in zip(bases, sizes)]
    floor = _rect([0, 0], plan["san"]["kich_thuoc"], 0)

    def add(level, path, reason, code):
        out.append(_issue(level, path, reason, code))
    for i, b in enumerate(blocks):
        path = f"khoi[{i}]"
        if any(not _inside(p, floor) for p in polys[i]):
            add("do", path + ".tam", "chân đế ra ngoài sàn", "outside_floor")
        supported = any(j != i and abs(bases[i] - tops[j]) <= FLOOR_TOL
                        and b["loai"] == "mai" and blocks[j]["loai"] in ROOF_SUPPORTS
                        and _area(_intersection(polys[i], polys[j])) > .01 for j in range(len(blocks)))
        if abs(bases[i] - floor_z) > FLOOR_TOL and not supported:
            add("do", path + ".z", "chân khối không chạm sàn hoặc vật đỡ hợp lệ", "floating")
        ref = b.get("kich_thuoc_chuan")
        if ref is not None:
            for k, (actual, expected) in enumerate(zip(sizes[i], ref)):
                if abs(actual / expected - 1) > .2 + 1e-9:
                    add("vang", path + f".kich_thuoc[{k}]", f"cỡ {actual:g} m lệch >20% số chuẩn {expected:g} m", "size_reference")
        elif b["nguon"] in ("kho", "vat_quen"):
            add("vang", path + ".kich_thuoc_chuan", "thiếu số chuẩn Kho/vật quen — chưa đối chiếu kích thước", "reference_missing")
    for i, j in combinations(range(len(blocks)), 2):
        share = _area(_intersection(polys[i], polys[j])) / min(_area(polys[i]), _area(polys[j]))
        if share > OVERLAP_SHARE and min(tops[i], tops[j]) - max(bases[i], bases[j]) > FLOOR_TOL:
            add("do", f"khoi[{i}]/khoi[{j}]", f"khối chồng lấn chân đế {share:.0%} và giao chiều cao", "overlap")
    for n, op in enumerate(plan["loi_mo"]):
        poly = _rect(op["tam"], op["kich_thuoc"], op.get("huong", 0))
        if min(op["kich_thuoc"]) < WALKWAY:
            add("do", f"loi_mo[{n}].kich_thuoc", "lối mở hẹp hơn 0,8 m", "walkway")
        if any(not _inside(p, floor) for p in poly):
            add("do", f"loi_mo[{n}]", "lối mở ra ngoài sàn", "outside_floor")
        for i in range(len(blocks)):
            if bases[i] < floor_z + 1.7 and tops[i] > floor_z + FLOOR_TOL and _area(_intersection(poly, polys[i])) > .01:
                add("do", f"loi_mo[{n}]/khoi[{i}]", "vùng khai lối mở bị khối chắn — phải tách khối hai bên cửa", "opening_blocked")
    for n, point in enumerate(cho_dung or []):
        p = point.get("tam") if isinstance(point, dict) else point
        path = f"cho_dung[{n}]"
        if not _vector(p, 2):
            add("do", path, "chỗ đứng cần [x,y] hữu hạn", "schema")
            continue
        if not _inside(p, floor):
            add("do", path, "chỗ đứng ra ngoài sàn", "outside_floor")
        near = [i for i in range(len(blocks)) if bases[i] < floor_z + 1.7 and tops[i] > floor_z + FLOOR_TOL]
        for i in near:
            if _inside(p, polys[i]):
                add("do", path, f"chỗ đứng nằm trong khối {blocks[i]['id']}", "standing_blocked")
        for i, j in combinations(near, 2):
            if max(_point_distance(p, polys[i]), _point_distance(p, polys[j])) > 1:
                continue
            gap = min([_point_distance(q, polys[j]) for q in polys[i]] + [_point_distance(q, polys[i]) for q in polys[j]])
            if 0 < gap < WALKWAY - 1e-9:
                add("do", path, f"lối giữa {blocks[i]['id']} / {blocks[j]['id']} chỉ {gap:.2f} m (<0,8 m)", "walkway")
    names = {str(v).strip() for b in blocks for v in (b.get("vat_kho"), b["mo_ta_ngan"]) if v is not None}
    for i, name in enumerate(vat_kich_ban or []):
        if not isinstance(name, (str, int)) or isinstance(name, bool) or not str(name).strip():
            add("do", f"vat_kich_ban[{i}]", "mã/tên vật rỗng hoặc sai kiểu", "schema")
        elif str(name).strip() not in names:
            add("do", f"vat_kich_ban[{i}]", f"vật {name!r} chưa có khối (so đúng mã/chữ có dấu)", "missing_object")
    return out


def to_props(plan, stage=None):
    """Giữa khoảng → hợp đồng add_props kind=block (khối thay thế, không phải hình thật). Không gọi Blender."""
    issues = validate(plan)
    if issues:
        raise ValueError("; ".join(f"{i['path']}: {i['loi']}" for i in issues))
    props = [{"kind": "block", "id": b["id"], "shape": "cylinder" if b["loai"] in ("cot", "tru") else "box",
             "at": [*b["tam"], b.get("z", plan["san"].get("z", 0))], "size": _size(b), "rotation_deg": b["huong"],
             "label": b["mo_ta_ngan"], "source": b["nguon"], "stand_in": True} for b in plan["khoi"]]
    for p, b in zip(props, plan["khoi"]):
        if "vat_kho" in b:
            p["vat_kho"] = b["vat_kho"]
        if stage is not None:
            from .stage_grid import model_from_rel
            p["at"] = list(model_from_rel(stage, p["at"]))
    return props
