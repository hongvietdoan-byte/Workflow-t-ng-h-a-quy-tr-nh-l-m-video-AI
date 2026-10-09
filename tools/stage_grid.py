"""Lưới sân khấu — Bước 0 kế hoạch đặt máy 3D (docs/KE_HOACH_DAT_MAY_3D_2026-10-09.md, "ĐỔI HƯỚNG 09/10 tối"). 0 USD: Blender cục bộ.

Hai chế độ trong một file:
  * máy chủ (Python thường):  py tools/stage_grid.py --place 263 --spot plaza_front --out data/projects/24/stage_s0
      đọc model3d của bối cảnh trong CSDL (CHỈ ĐỌC), viết cfg.json, chạy Blender nền (lượt Blender chung của plates3d),
      rồi vẽ topgrid.png (ảnh trực giao + lưới + nhãn ô) và in bảng.
  * trong Blender (-P tools/stage_grid.py -- --config cfg.json): bắn tia, dựng đạo cụ/người nộm, render, ghi JSON.
Ra (trong --out): stage.json (gốc O cố định của cảnh), grid.json (mỗi ô: sàn so với O, vật trúng, bậc/tầng), objects.json (tên vật +
nhóm), top_raw.png/topgrid.png, try_wide.png, try_down.png, frames.json (lưới tia từ máy + số kiểm hình học).
Phần hình học thuần: core/stage_grid.py. Không ghi CSDL, không gọi API tốn tiền.
"""
import importlib.util
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sg = _load("stage_grid_pure", os.path.join(ROOT, "core", "stage_grid.py"))

try:
    import bpy  # noqa: F401
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

COLORS = {"thap": (0.85, 0.2, 0.2), "nha": (0.95, 0.55, 0.1), "tuong": (0.9, 0.85, 0.1), "bac": (0.6, 0.3, 0.9),
          "san": (0.5, 0.75, 0.5), "cay": (0.1, 0.55, 0.1), "gieng": (0.2, 0.5, 1.0), "nguoi": (1.0, 0.2, 0.8),
          "khac": (0.5, 0.5, 0.5), "troi": (0.6, 0.85, 1.0)}


# ================================================ trong Blender ================================================
def blender_main(cfg):
    import bpy
    from mathutils import Vector
    rp = _load("render_plates_mod", os.path.join(HERE, "render_plates.py"))
    out = cfg["out_dir"]
    os.makedirs(out, exist_ok=True)
    warnings = []
    t0 = time.time()
    meshes, _ = rp.load_model(cfg["model"], warnings)
    factor, (lo, hi) = rp.normalise_scale(meshes, cfg.get("real_height_m"), warnings)
    lift = rp.LIFT_Z
    scene = bpy.context.scene
    top_z = hi.z + 5

    def dg():
        return bpy.context.evaluated_depsgraph_get()

    def mat_of(obj, idx):
        try:
            o = obj.original if hasattr(obj, "original") else obj
            mi = o.data.polygons[idx].material_index
            m = o.material_slots[mi].material if mi < len(o.material_slots) else None
            return m.name if m else ""
        except Exception:  # noqa: BLE001
            return ""

    bbox_cache = {}

    def obj_box(obj):
        o = obj.original if hasattr(obj, "original") else obj
        if o.name not in bbox_cache:
            pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
            bbox_cache[o.name] = ([min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)])
        return bbox_cache[o.name]

    def down_layers(x, y, n=5):
        """Các lớp bề mặt dưới (x, y) scene, từ trên xuống: [(z, obj, mat, normal_z)]."""
        res, origin = [], Vector((x, y, top_z))
        d = dg()
        for _ in range(n):
            ok, loc, nor, idx, obj, _ = scene.ray_cast(d, origin, Vector((0, 0, -1)))
            if not ok or obj is None:
                break
            res.append((loc.z, obj, mat_of(obj, idx), nor.z))
            origin = loc - Vector((0, 0, 0.03))
        return res

    def floor_hit(x, y):
        for z, obj, mat, nz in down_layers(x, y, 8):
            if obj.name == "PLATES_GROUND" or obj.name.startswith("STAGE_"):
                continue
            if any(k in obj.name.lower() for k in rp.PLANT_NAMES):
                continue
            return z, obj, mat, nz
        return None

    # ---- gốc O: tia xuống tại chỗ đứng chính ----
    ox, oy, _oz = cfg["origin_model"]
    sx, sy = ox * factor, oy * factor
    h0 = floor_hit(sx, sy)
    if h0 is None:
        raise SystemExit("tia tại gốc O không chạm sàn")
    floor_model = (h0[0] - lift) / factor
    stage = sg.make_stage([ox, oy, floor_model], cell_m=cfg["cell_m"], cols=cfg["cols"], rows=cfg["rows"], lift_z=lift, factor=factor)
    stage.update({"origin_scene": [round(sx, 3), round(sy, 3), round(h0[0], 3)], "origin_on": h0[1].name,
                  "spot_z_model": _oz, "spot_vs_floor_m": round(_oz - floor_model, 3)})
    if cfg.get("mode") == "floor":                      # fix-spot: chỉ đo sàn dưới spot bằng tia từ trên xuống
        with open(os.path.join(out, "fix_spot.json"), "w", encoding="utf-8") as f:
            json.dump({"spot_at_model": cfg["origin_model"], "floor_z_model": round(floor_model, 3), "on": h0[1].name,
                       "normal_z": round(h0[3], 3), "diff_m": round(floor_model - _oz, 3)}, f, ensure_ascii=False, indent=1)
        print("[stage] floor done", flush=True)
        return

    def rel(v):
        return sg.rel_from_scene(stage, v)

    def scn(r):
        return Vector(sg.scene_from_rel(stage, r))

    # độ dốc quanh O (±2 m, bước 0,5 m)
    def line(dx, dy):
        zs = []
        for k in range(-4, 5):
            h = floor_hit(sx + dx * k * 0.5, sy + dy * k * 0.5)
            zs.append(h[0] if h else h0[0])
        return zs
    stage["slope_deg"] = {"E-W": round(sg.slope_deg(line(1, 0), 0.5), 2), "N-S": round(sg.slope_deg(line(0, 1), 0.5), 2)}

    # ---- lưới ô ----
    inv = {}

    def note(obj, mat, group):
        o = obj.original if hasattr(obj, "original") else obj
        e = inv.setdefault(o.name, {"object": o.name, "materials": {}, "hits": 0, "group_name": group})
        e["hits"] += 1
        e["materials"][mat] = e["materials"].get(mat, 0) + 1

    def classify(obj, mat):
        g = sg.group_by_name(obj.name, mat)
        if g == "khac" and obj.name != "PLATES_GROUND":
            lo_b, hi_b = obj_box(obj)
            g = sg.group_by_shape((hi_b[2] - lift) / factor - floor_model, [hi_b[k] - lo_b[k] for k in range(3)])
        return "san" if obj.name == "PLATES_GROUND" else g

    grid = []
    c_m = stage["cell_m"]
    act = cfg.get("acting_area", {"half_m": 3.0, "extra": []})       # vùng diễn: 6×6 m quanh O (+ quanh giếng) → 4×4 tia mỗi ô

    def offsets(k):
        return [((a + 0.5) / k - 0.5) * c_m for a in range(k)]

    def sample(cx, cy, k):
        out_ = []
        for px in offsets(k):
            for py in offsets(k):
                s = scn((cx + px, cy + py, 0))
                layers = down_layers(s.x, s.y, 8)
                fh = next(((z, o, m, nz) for z, o, m, nz in layers if o.name != "PLATES_GROUND" and not o.name.startswith("STAGE_")
                           and not any(w in o.name.lower() for w in rp.PLANT_NAMES)), None)
                out_.append((layers[0] if layers else None, fh))
        return out_

    def summarise(smp):
        floors = [rel((0, 0, f[0]))[2] for _, f in smp if f and f[3] >= 0.9]
        allf = [rel((0, 0, f[0]))[2] for _, f in smp if f]
        tops = [(rel((0, 0, t[0]))[2], t) for t, _ in smp if t]
        fz = sg.median(floors) if floors else sg.median(allf)
        r_ = {"floor_z": None if fz is None else round(fz, 3), "status": sg.floor_status(fz), "hits": len(allf),
              "flat_hits": len(floors)}
        if allf:
            r_["spread_m"] = round(max(allf) - min(allf), 3)
            r_["inner_step"] = r_["spread_m"] > sg.SAME_FLOOR_M
            nzs = [f[3] for _, f in smp if f]
            r_["slope_deg"] = round(math.degrees(math.acos(max(-1, min(1, sum(nzs) / len(nzs))))), 1)
        if tops:
            tz, t = max(tops, key=lambda x: x[0])
            r_["top_z"] = round(tz, 2)
            r_["top_on"], r_["top_mat"] = t[1].name, t[2]
            r_["top_group_name"] = classify(t[1], t[2])
            r_["top_group"] = sg.group_by_hit(r_["top_group_name"], tz, t[3])
            hi_over = tz - (fz or 0.0)
            r_["covered"] = hi_over > 2.0 and len(floors) > 0                      # mái / tầng trên, có sàn dưới
            r_["obstacle"] = (0.3 < hi_over <= 2.0) or (hi_over > 2.0 and not floors)
        return r_

    for name, cx, cy in sg.cells(stage):
        in_act = (abs(cx) <= act["half_m"] and abs(cy) <= act["half_m"]) or any(
            abs(cx - e[0]) <= e[2] and abs(cy - e[1]) <= e[2] for e in act.get("extra", []))
        k = 4 if in_act else 3
        smp = sample(cx, cy, k)
        cell = {"cell": name, "x": round(cx, 2), "y": round(cy, 2), "rays": f"{k}x{k}", "acting": in_act}
        cell.update(summarise(smp))
        fh = next((f for _, f in smp if f), None)
        if fh:
            cell.update(on=fh[1].name, mat=fh[2], group=classify(fh[1], fh[2]))
            if cell.get("floor_z") is not None:
                cell["group_hit"] = sg.group_by_hit(cell["group"], cell["floor_z"], 1.0)
        if in_act:                                       # so sánh: 3×3 trên cùng ô có bắt được bậc/gờ/vật hẹp như 4×4 không
            s3 = summarise(sample(cx, cy, 3))
            cell["cmp3x3"] = {k_: s3.get(k_) for k_ in ("floor_z", "status", "spread_m", "inner_step", "top_z", "obstacle")}
        for t, f in smp:
            if f:
                note(f[1], f[2], classify(f[1], f[2]))
            if t is not None:
                note(t[1], t[2], classify(t[1], t[2]))
        grid.append(cell)

    # ---- mốc: tháp ----
    marks = {}
    ax, ay = cfg["anchor_model"][0] * factor, cfg["anchor_model"][1] * factor
    tl = down_layers(ax, ay, 12)
    tf = floor_hit(ax, ay)
    tower_obj = tl[0][1] if tl else None
    if tower_obj is not None:
        lo_b, hi_b = obj_box(tower_obj)
        foot = rel((ax, ay, min(lo_b[2], tf[0] if tf else lo_b[2])))
        marks["thap_chan"] = sg.measure(stage, foot)
        marks["thap_dinh"] = sg.measure(stage, rel((ax, ay, hi_b[2])))
        marks["thap_object"] = {"name": tower_obj.name, "bbox_size_m": [round(hi_b[k] - lo_b[k], 2) for k in range(3)],
                                "top_hit_z": round(rel((0, 0, tl[0][0]))[2], 2)}
    marks["anchor_model"] = sg.measure(stage, sg.rel_from_model(stage, cfg["anchor_model"]))

    # ---- sân khấu: giếng + người nộm ----
    def mk_mat(name, rgb):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        if b is not None:
            b.inputs["Base Color"].default_value = (*rgb, 1)
            b.inputs["Roughness"].default_value = 0.8
        return m

    placed = {}
    # đo sàn của MỌI vật trước khi dựng bất kỳ khối nào: đáy khối trùng mặt sàn → tia xuống xuyên đáy khối đọc nhầm tầng rỗng −6,18 m
    # (lần chạy v2 09/10: yêu nữ đứng cách người nộm Kelly 5 cm bị đặt xuống −6,18 m, thấy 0 %)
    floor0 = {}
    for p in cfg.get("props", []):
        s = scn((p["at"][0], p["at"][1], 0))
        floor0[p["name"]] = floor_hit(s.x, s.y)
    for p in cfg.get("props", []):
        r = p["at"]
        s = scn((r[0], r[1], 0))
        fh = floor0[p["name"]]
        fz = fh[0] if fh else s.z
        frel = rel((0, 0, fz))[2]
        info = sg.measure(stage, (r[0], r[1], frel))
        info.update(kind=p["kind"], floor_status=sg.floor_status(frel))
        if p["kind"] == "well":
            # chân đế TRƯỚC khi dựng khối (đáy khối trùng mặt sàn: tia đi qua đáy sẽ đọc tầng dưới — đo lần 1 ra −6,18 m)
            base = []
            for ang in range(0, 360, 45):
                q = sg.offset((r[0], r[1], 0), ang, p["radius"] * 0.95)
                qs = scn((q[0], q[1], 0))
                f2 = floor_hit(qs.x, qs.y)
                base.append(None if f2 is None else round(rel((0, 0, f2[0]))[2], 3))
            info["base_floor_z"] = base
            info["base_ok"] = all(b is not None and abs(b - frel) <= sg.SAME_FLOOR_M for b in base)
            bpy.ops.mesh.primitive_cylinder_add(vertices=p.get("sides", 48), radius=p["radius"], depth=p["height"], location=(s.x, s.y, fz + p["height"] / 2))
            o = bpy.context.active_object
            o.name = "STAGE_WELL"
            o.data.materials.append(mk_mat("STAGE_WELL_stone", (0.45, 0.43, 0.40)))
            hole_z = fz + p["height"] + 0.005
            if p.get("hollow"):
                # vành + lòng rỗng (người đứng trong giếng): khoét trụ trong bằng Boolean; đáy tối nằm sát mặt sàn trong lòng giếng
                bpy.ops.mesh.primitive_cylinder_add(vertices=p.get("sides", 48), radius=p["radius"] - 0.18, depth=p["height"] + 0.4,
                                                    location=(s.x, s.y, fz + p["height"] / 2))
                cut = bpy.context.active_object
                mod = o.modifiers.new("well_hollow", "BOOLEAN")
                mod.operation, mod.object = "DIFFERENCE", cut
                bpy.context.view_layer.objects.active = o
                bpy.ops.object.modifier_apply(modifier=mod.name)
                bpy.data.objects.remove(cut, do_unlink=True)
                hole_z = fz + 0.01
            bpy.ops.mesh.primitive_cylinder_add(vertices=p.get("sides", 48), radius=p["radius"] - 0.18, depth=0.02, location=(s.x, s.y, hole_z))
            h = bpy.context.active_object
            h.name = "STAGE_WELL_hole"
            h.data.materials.append(mk_mat("STAGE_WELL_dark", (0.02, 0.02, 0.03)))
            info.update(radius_m=p["radius"], height_m=p["height"], top_z=round(frel + p["height"], 2), source=p.get("source"),
                        hollow=bool(p.get("hollow")))
        else:
            hgt = p["height"]
            body_h = hgt - 0.13                    # thân lên tới tâm đầu: không còn khe cổ (09/10: người nộm bò 0,6 m mất 46 % điểm vào khe)
            if p.get("in_well") is not None:
                # đứng TRONG giếng: chân dưới mặt sàn (z âm) là cố ý — ghi rõ, không tính là lỗi "khác mặt sàn"
                # mặt sàn lấy theo chân đế giếng (tia xuống tại tâm giếng đi qua đáy tối sát sàn → đọc tầng dưới −6,18 m, lần chạy 1)
                frel = placed["WELL"]["xyz"][2] + p["in_well"]["foot_z"]
                fz = scn((r[0], r[1], frel)).z
                info.update(xyz=[r[0], r[1], round(frel, 3)], floor_status="trong_gieng",
                            in_well=dict(p["in_well"], note="đứng trong giếng: chân dưới mặt sàn là cố ý"))
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.19, depth=body_h, location=(s.x, s.y, fz + body_h / 2))
            b = bpy.context.active_object
            b.name = f"STAGE_{p['name']}_body"
            col = tuple(p.get("rgb", (1.0, 0.4, 0.1)))
            b.data.materials.append(mk_mat(f"STAGE_{p['name']}_m", col))
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(s.x, s.y, fz + hgt - 0.13))
            hd = bpy.context.active_object
            hd.name = f"STAGE_{p['name']}_head"
            hd.data.materials.append(b.data.materials[0])
            # mũi chỉ hướng mặt
            f = math.radians(p.get("facing", 0))
            bpy.ops.mesh.primitive_cone_add(radius1=0.06, depth=0.18, location=(s.x + math.sin(f) * 0.2, s.y + math.cos(f) * 0.2, fz + hgt - 0.13))
            nz = bpy.context.active_object
            nz.name = f"STAGE_{p['name']}_nose"
            nz.rotation_euler = (math.pi / 2, 0, -f)
            nz.data.materials.append(b.data.materials[0])
            info.update(height_m=hgt, facing_deg=p.get("facing", 0), eye_z=round(frel + hgt * sg.EYE, 2),
                        chest_z=round(frel + hgt * sg.CHEST, 2), hip_z=round(frel + hgt * sg.HIP, 2), source=p.get("source"))
        if info.get("floor_status") not in ("same", "trong_gieng"):
            warnings.append(f"{p['name']} ở {info.get('cell')} đứng trên sàn '{info.get('floor_status')}' z {frel:.2f} m — kiểm chỗ đứng")
        placed[p["name"]] = info
    bpy.context.view_layer.update()

    # ---- ánh sáng + engine ----
    rp.add_ground(lo, hi)
    used = rp.setup_world({"mode": "A", "sun_elevation": 50, "sun_azimuth": 140, "exposure": -0.3}, warnings)
    try:
        rp.fix_terrain(None, warnings)
        rp.fix_foliage(warnings)
        rp.fix_water(warnings)
    except Exception as e:  # noqa: BLE001
        warnings.append(f"fix map: {e}")
    engine = rp.pick_engine(cfg.get("engine", "auto"), warnings)
    for owner, attr in ((getattr(scene, "eevee", None), "taa_render_samples"), (getattr(scene, "cycles", None), "samples")):
        if owner is not None and hasattr(owner, attr):
            setattr(owner, attr, int(cfg.get("samples", 16)))

    def render(path, res):
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = res[0], res[1], 100
        nonlocal engine
        try:
            return rp.render_to(path, False)
        except RuntimeError as e:
            warnings.append(f"{engine} lỗi ({e}) → Cycles")
            engine = rp.pick_engine("cycles", warnings)
            return rp.render_to(path, False)

    # ---- ảnh trực giao từ trên ----
    tv = cfg["top_view"]
    cd = bpy.data.cameras.new("STAGE_TOP")
    cd.type = "ORTHO"
    cd.ortho_scale = tv["size_m"]
    cd.clip_end = 1000
    cam = bpy.data.objects.new("STAGE_TOP", cd)
    scene.collection.objects.link(cam)
    c = scn((tv["centre"][0], tv["centre"][1], 0))
    cam.location = (c.x, c.y, hi.z + 20)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    top_sec = render(os.path.join(out, "top_raw.png"), (tv["px"], tv["px"]))

    # ---- máy thử + lưới tia ----
    frames = {}
    for cspec in cfg.get("cameras", []):
        loc_r = tuple(cspec["at"])
        aim_r = tuple(cspec["aim"])
        L, A = scn(loc_r), scn(aim_r)
        cd = bpy.data.cameras.new(cspec["name"])
        cd.lens = cspec["lens"]
        cd.clip_end = 2000
        cam = bpy.data.objects.new(cspec["name"], cd)
        scene.collection.objects.link(cam)
        cam.location = L
        rp.look_at(cam, list(A))
        scene.camera = cam
        res = cspec["res"]
        aspect = res[0] / res[1]
        sec = render(os.path.join(out, cspec["file"]), res)
        d = dg()
        nu, nv = cspec["rays"]
        counts, nearest, nearest_solid, cells_hit = {}, None, None, []
        for j in range(nv):
            row = []
            for i in range(nu):
                u, v = (i + 0.5) / nu, (j + 0.5) / nv
                dr = Vector(sg.ray_dir(list(L), list(A), u, v, cspec["lens"], aspect))
                ok, loc, nor, idx, obj, _ = scene.ray_cast(d, L, dr, distance=3000)
                if not ok or obj is None:
                    g, dist = "troi", None
                else:
                    o = obj.original if hasattr(obj, "original") else obj
                    mat = mat_of(obj, idx)
                    if o.name.startswith("STAGE_WELL"):
                        g = "gieng"
                    elif o.name.startswith("STAGE_"):
                        g = "nguoi_" + o.name.split("_")[1].lower()
                    else:
                        g = sg.group_by_hit(classify(o, mat), rel((0, 0, loc.z))[2], nor.z)
                    note(o, mat, g)
                    dist = (loc - L).length
                    if nearest is None or dist < nearest[0]:
                        nearest = (dist, o.name, g)
                    if g not in ("san", "gieng") and not g.startswith("nguoi") and (nearest_solid is None or dist < nearest_solid[0]):
                        nearest_solid = (dist, o.name, g, round(u, 2), round(v, 2))
                counts[g] = counts.get(g, 0) + 1
                row.append(g[:2])
            cells_hit.append(row)
        total = nu * nv
        # số kiểm hình học
        chk = {}
        cam_floor = floor_hit(L.x, L.y)
        cam_floor_rel = rel((0, 0, cam_floor[0]))[2] if cam_floor else None
        yaw, pitch = sg.look(loc_r, aim_r)
        chk["camera"] = dict(sg.measure(stage, loc_r), z_above_stage_m=round(loc_r[2], 2),
                             z_above_floor_below_m=None if cam_floor_rel is None else round(loc_r[2] - cam_floor_rel, 2),
                             floor_below=None if cam_floor is None else cam_floor[1].name, yaw_deg=round(yaw, 1),
                             pitch_deg=round(pitch, 1), lens_mm=cspec["lens"], res=res)
        targets = dict(cfg.get("targets", {}))
        targets.update({k: v for k, v in cspec.get("targets", {}).items()})
        tz = {}
        if "thap_chan" in marks:
            targets["thap_chan"] = marks["thap_chan"]["xyz"]
            targets["thap_dinh"] = marks["thap_dinh"]["xyz"]
        for k, p in targets.items():
            pr = sg.project(loc_r, aim_r, p, cspec["lens"], aspect)
            T = scn(p)
            seg = T - L
            ok, loc, _, _, obj, _ = scene.ray_cast(d, L, seg.normalized(), distance=max(seg.length - 0.15, 0.01))
            blocker = None
            if ok and obj is not None:
                o = obj.original if hasattr(obj, "original") else obj
                own = {"kelly": "STAGE_KELLY", "yeunu": "STAGE_YEUNU", "gieng": "STAGE_WELL",
                       "thap": marks.get("thap_object", {}).get("name") or "~"}.get(k.split("_")[0], "~")
                if not o.name.startswith(own):
                    blocker = {"object": o.name, "at_m": round((loc - L).length, 2)}
            tz[k] = {"in_frame": sg.in_frame(pr), "uv": None if pr is None else [round(pr[0], 3), round(pr[1], 3)],
                     "dist_m": round(seg.length, 2), "blocked_by": blocker}
        chk["targets"] = tz
        up = scene.ray_cast(d, L, Vector((0, 0, 1)))
        chk["camera"]["inside_object"] = bool(up[0] and up[2].z > 0.2)              # tia lên gặp mặt hướng lên = đang trong vật
        chk["camera"]["above"] = None if not up[0] else {"object": up[4].name, "m": round((up[1] - L).length, 2)}
        chk["camera"]["fov_h_v_deg"] = [round(x, 1) for x in sg.fov(cspec["lens"], aspect)]
        chk["horizon_w"] = round(sg.horizon_w(pitch, cspec["lens"], aspect), 3)
        for who in ("kelly", "yeunu"):
            ft, hd = tz.get(f"{who}_chan"), tz.get(f"{who}_dinh") or tz.get(f"{who}_mat")
            if ft and hd and ft["uv"] and hd["uv"]:
                chk[f"{who}_frame_height_pct"] = round(100 * (ft["uv"][1] - hd["uv"][1]), 1)
            pts_ = [v_ for k_, v_ in tz.items() if k_.startswith(who)]
            if pts_:
                chk[f"{who}_visible_pct"] = round(100 * sum(1 for v_ in pts_ if v_["in_frame"] and not v_["blocked_by"]) / len(pts_))
        wp = placed.get("WELL")
        if wp:
            chk["well_top_vs_hip"] = {n_: round(wp["top_z"] / placed[n_]["hip_z"], 2) for n_ in ("KELLY", "YEUNU") if n_ in placed}
        # hình phác clay (Workbench xám, đạo cụ/người tô màu theo vật)
        keep = scene.render.engine
        try:
            scene.render.engine = "BLENDER_WORKBENCH"
            shd = scene.display.shading
            shd.light, shd.color_type = "STUDIO", "OBJECT"
            for ob in scene.objects:
                if ob.type == "MESH":
                    ob.color = (0.72, 0.72, 0.72, 1) if not ob.name.startswith("STAGE_") else ob.color
            for ob_name, colr in (("STAGE_WELL", (0.35, 0.55, 0.95, 1)), ("STAGE_WELL_hole", (0.1, 0.1, 0.15, 1))):
                if bpy.data.objects.get(ob_name):
                    bpy.data.objects[ob_name].color = colr
            for ob in scene.objects:
                if ob.name.startswith("STAGE_KELLY"):
                    ob.color = (1.0, 0.55, 0.1, 1)
                elif ob.name.startswith("STAGE_YEUNU"):
                    ob.color = (0.9, 0.15, 0.2, 1)
            try:
                shd.show_cavity = True
            except AttributeError:
                pass
            if scene.world is not None:
                scene.world.color = (0.82, 0.86, 0.92)
            clay = cspec["file"].replace("try_", "view_").replace(".png", "_clay.png")
            clay = {"try_wide.png": "view_a_clay_raw.png", "try_down.png": "view_b_clay_raw.png"}.get(cspec["file"], clay)
            scene.render.resolution_x, scene.render.resolution_y = res[0], res[1]
            clay_sec = rp.render_to(os.path.join(out, clay), False)
            chk["clay"] = {"file": clay, "render_sec": round(clay_sec, 2)}
        except Exception as e:  # noqa: BLE001
            warnings.append(f"clay {cspec['name']}: {e}")
        finally:
            scene.render.engine = keep
        ax_a, ax_b = cfg["axis"]
        chk["axis_side"] = sg.axis_side(ax_a, ax_b, loc_r)
        if "thap_chan" in marks:
            chk["angle_cam_kelly_tower_deg"] = round(sg.angle_at(loc_r, ax_a, marks["thap_chan"]["xyz"]), 1)
        chk["camera"].update(at=list(loc_r), aim=list(aim_r))
        frames[cspec["name"]] = {"file": cspec["file"], "render_sec": round(sec, 1), "rays": [nu, nv],
                                 "percent": {g: round(100 * n / total, 1) for g, n in sorted(counts.items(), key=lambda x: -x[1])},
                                 "nearest_hit": None if nearest is None else {"m": round(nearest[0], 2), "object": nearest[1], "group": nearest[2]},
                                 "nearest_solid": None if nearest_solid is None else {"m": round(nearest_solid[0], 2), "object": nearest_solid[1],
                                                                                      "group": nearest_solid[2], "uv": nearest_solid[3:]},
                                 "checks": chk, "map": ["".join(r_) for r_ in [[x[0] for x in row] for row in cells_hit]]}

    # ---- Bước 2: ứng viên máy + luật L1–L10 (mục 5–8) và đo các shot hiện có — MỘT lượt Blender cho cả cảnh ----
    s1 = None
    if cfg.get("requests") or cfg.get("shots"):
        s1 = s1_block(cfg, stage, placed, marks, scene, dg(), scn, rel, mat_of, classify, Vector, bpy, rp, out, warnings)
    v2 = None
    if cfg.get("v2"):
        v2 = v2_block(cfg, stage, placed, marks, scene, dg(), scn, rel, mat_of, classify, Vector, bpy, rp, out, warnings)

    objects = []
    for name, e in inv.items():
        o = bpy.data.objects.get(name)
        box = obj_box(o) if o is not None else None
        top_rel = None if box is None else round((box[1][2] - lift) / factor - floor_model, 2)
        size = None if box is None else [round(box[1][k] - box[0][k], 2) for k in range(3)]
        e.update(top_rel_m=top_rel, bbox_size_m=size, group_shape=None if size is None else sg.group_by_shape(top_rel, size),
                 group_by_name=sg.group_by_name(name, " ".join(e["materials"])))
        objects.append(e)
    objects.sort(key=lambda e: -e["hits"])

    def dump(fn, data):
        with open(os.path.join(out, fn), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    stage["axis"] = cfg.get("axis")
    stage.update({"north": "+y của model/scene (θ = 0) — quy ước facing của plate_camera/location_pack; CHƯA có nguồn hướng Bắc trong game", "cell_rule": "|floor_z| ≤ 0,15 m cùng sàn; > 0,15 m bậc (≤ 0,6) / tầng khác; vật > 0,3 m = vật chắn", "marks": marks, "placed": placed,
                  "blender": bpy.app.version_string, "engine": engine, "sky": used, "warnings": warnings,
                  "top_view": dict(tv, render_sec=round(top_sec, 1)), "sec": round(time.time() - t0, 1)})
    dump("stage.json", stage)
    dump("grid.json", {"origin": stage["origin_model"], "cell_m": stage["cell_m"], "cells": grid})
    dump("objects.json", objects)
    dump("frames.json", frames)
    if s1 is not None:
        dump("s1.json", s1)
    if v2 is not None:
        dump("v2.json", v2)
    print("[stage] done", flush=True)


# nhãn hình phác: khóa → (chữ, tiền tố tên object "của chính nó" khi kiểm bị che)
LABEL_POINTS = (("kelly_dinh", "Kelly", "STAGE_KELLY"), ("yeunu_mat", "Yêu nữ", "STAGE_YEUNU"), ("gieng_tam", "Giếng", "STAGE_WELL"),
                ("thap_chan", "Tháp (chân)", "@tower"), ("thap_dinh", "Tháp (đỉnh)", "@tower"))


def s1_block(cfg, stage, placed, marks, scene, dgv, scn, rel, mat_of, classify, Vector, bpy, rp, out, warnings):
    """Đo mỗi máy bằng lưới tia (thành phần khung, % thấy nhân vật, cỡ trong khung, vật cản, chân trời, sàn dưới máy), chấm L1–L10,
    xếp ứng viên đạt; đo lại top-3 bằng lưới mịn và render hình phác; đo + render các shot hiện có."""
    f_ = stage.get("factor", 1.0)
    tower = (marks.get("thap_object") or {}).get("name") or "~"
    pts = {"kelly_dinh": [0.0, 0.0, placed["KELLY"]["height_m"]]}
    if "YEUNU" in placed:
        pts["yeunu_mat"] = [placed["YEUNU"]["xyz"][0], placed["YEUNU"]["xyz"][1], placed["YEUNU"]["eye_z"]]
    if "WELL" in placed:
        pts["gieng_tam"] = [placed["WELL"]["xyz"][0], placed["WELL"]["xyz"][1], placed["WELL"]["top_z"]]
    if "thap_chan" in marks:
        pts["thap_chan"], pts["thap_dinh"] = marks["thap_chan"]["xyz"], marks["thap_dinh"]["xyz"]
    well_hip = round(placed["WELL"]["top_z"] / placed["KELLY"]["hip_z"], 2) if "WELL" in placed else None

    def group_of(obj, idx, loc, nor):
        o = obj.original if hasattr(obj, "original") else obj
        if o.name.startswith("STAGE_WELL"):
            return o, "gieng"
        if o.name.startswith("STAGE_"):
            return o, "nguoi_" + o.name.split("_")[1].lower()
        return o, sg.group_by_hit(classify(o, mat_of(obj, idx)), rel((0, 0, loc.z))[2], nor.z)

    def blocked(L, P, own):
        seg = P - L
        ok, loc, _, _, obj, _ = scene.ray_cast(dgv, L, seg.normalized(), distance=max(seg.length - 0.15, 0.01))
        if not ok or obj is None:
            return None
        o = obj.original if hasattr(obj, "original") else obj
        return None if o.name.startswith(own) else o.name

    def measure(C_r, A_r, lens, res, rays, size, subj="KELLY"):
        L, A = scn(C_r), scn(A_r)
        aspect = res[0] / res[1]
        nu, nv = rays
        sp = placed[subj]
        H = sp["height_m"]
        subj_d = math.dist(C_r, (sp["xyz"][0], sp["xyz"][1], sp["chest_z"]))
        counts, occ, occ_m, near = {}, 0, None, None
        for j in range(nv):
            for i in range(nu):
                dr = Vector(sg.ray_dir(list(L), list(A), (i + 0.5) / nu, (j + 0.5) / nv, lens, aspect))
                ok, loc, nor, idx, obj, _ = scene.ray_cast(dgv, L, dr, distance=3000)
                if not ok or obj is None:
                    g = "troi"
                else:
                    o, g = group_of(obj, idx, loc, nor)
                    dist = (loc - L).length / f_
                    near = dist if near is None else min(near, dist)
                    if g not in ("san", "gieng", "troi") and not g.startswith("nguoi") and dist < subj_d - 0.3:
                        occ += 1
                        occ_m = dist if occ_m is None else min(occ_m, dist)
                counts[g] = counts.get(g, 0) + 1
        total = nu * nv
        # % thấy nhân vật: 9 mức cao × 3 điểm ngang (theo trục phải của máy) — chỉ tính điểm nằm trong khung
        yaw, pitch = sg.look(C_r, A_r)
        ra = math.radians(yaw + 90)
        seen = inside = 0
        for k in range(9):
            z = sp["xyz"][2] + H * (0.05 + 0.93 * k / 8)
            for lat in (-0.12, 0.0, 0.12):
                P = (sp["xyz"][0] + math.sin(ra) * lat, sp["xyz"][1] + math.cos(ra) * lat, z)
                if not sg.in_frame(sg.project(C_r, A_r, P, lens, aspect)):
                    continue
                inside += 1
                PS = scn(P)
                seg = PS - L
                ok, _, _, _, obj, _ = scene.ray_cast(dgv, L, seg.normalized(), distance=seg.length + 0.05)
                o = (obj.original if hasattr(obj, "original") else obj) if ok and obj is not None else None
                seen += 1 if o is not None and o.name.startswith(f"STAGE_{subj}") else 0
        # % thấy yêu nữ (cùng 9×3 điểm): điểm dưới miệng giếng khi đứng trong giếng mà bị cản → "bị che bởi giếng" (đúng ý: chỉ thấy phần trên)
        yv = None
        if "YEUNU" in placed and subj != "YEUNU":
            yp = placed["YEUNU"]
            yH, in_w = yp["height_m"], bool(yp.get("in_well"))
            rim = placed["WELL"]["top_z"] if "WELL" in placed else None
            cnt = {"thay": 0, "gieng": 0, "khac": 0, "ngoai_khung": 0}
            seen_z = []
            for k in range(9):
                z = yp["xyz"][2] + yH * (0.05 + 0.93 * k / 8)
                for lat in (-0.12, 0.0, 0.12):
                    P = (yp["xyz"][0] + math.sin(ra) * lat, yp["xyz"][1] + math.cos(ra) * lat, z)
                    if not sg.in_frame(sg.project(C_r, A_r, P, lens, aspect)):
                        cnt["ngoai_khung"] += 1
                        continue
                    seg = scn(P) - L
                    ok, _, _, _, obj, _ = scene.ray_cast(dgv, L, seg.normalized(), distance=seg.length + 0.05)
                    o = (obj.original if hasattr(obj, "original") else obj) if ok and obj is not None else None
                    if o is not None and o.name.startswith("STAGE_YEUNU"):
                        cnt["thay"] += 1
                        seen_z.append(z)
                    elif (o is not None and o.name.startswith("STAGE_WELL")) or (in_w and rim is not None and z < rim):
                        cnt["gieng"] += 1
                    else:
                        cnt["khac"] += 1
            yv = {"pct_thay": round(100 * cnt["thay"] / 27), "pct_che_gieng": round(100 * cnt["gieng"] / 27),
                  "pct_che_khac": round(100 * cnt["khac"] / 27), "pct_ngoai_khung": round(100 * cnt["ngoai_khung"] / 27),
                  "thay_tu_z": None if not seen_z else round(min(seen_z), 2), "thay_den_z": None if not seen_z else round(max(seen_z), 2),
                  "rim_z": rim, "in_well": in_w}
        body = sg.FRAMING[size][0]
        top = sg.project(C_r, A_r, (sp["xyz"][0], sp["xyz"][1], H), lens, aspect)
        bot = sg.project(C_r, A_r, (sp["xyz"][0], sp["xyz"][1], H * (1 - body)), lens, aspect)
        # sàn dưới máy: tia từ máy xuống (bỏ khối dựng); máy trong vật: tia lên gặp mặt hướng lên
        floor_rel, o_ = None, L.copy()
        for _ in range(6):
            ok, loc, nor, idx, obj, _ = scene.ray_cast(dgv, o_, Vector((0, 0, -1)), distance=200)
            if not ok or obj is None:
                break
            ob = obj.original if hasattr(obj, "original") else obj
            if not ob.name.startswith("STAGE_"):
                floor_rel = rel((0, 0, loc.z))[2]
                break
            o_ = loc - Vector((0, 0, 0.03))
        up = scene.ray_cast(dgv, L, Vector((0, 0, 1)), distance=500)
        labels = {}
        for key, label, own in LABEL_POINTS:
            if key not in pts:
                continue
            P = pts[key]
            b = blocked(L, scn(P), tower if own == "@tower" else own)
            stt = sg.point_state(C_r, A_r, P, lens, aspect, blocked_by=b)
            labels[key] = {"label": label, "state": stt["state"], "uv": stt["uv"] and [round(x, 3) for x in stt["uv"]],
                           "edge": stt["edge"], "arrow": stt["arrow"] and [round(x, 3) for x in stt["arrow"]], "blocked_by": b,
                           "dist_m": round(math.dist(C_r, P), 2)}
        return {"percent": {g: round(100 * n / total, 1) for g, n in sorted(counts.items(), key=lambda x: -x[1])},
                "rays": [nu, nv], "pitch": round(pitch, 1), "yaw": round(yaw, 1),
                "subject_hit_pct": None if not inside else round(100 * seen / inside), "subject_points_in_frame": inside,
                "subject_frame_pct": None if top is None or bot is None else round(100 * (bot[1] - top[1]), 1),
                "occluder_pct": round(100 * occ / total, 1), "occluder_m": None if occ_m is None else round(occ_m, 2),
                "nearest_m": None if near is None else round(near, 2),
                "cam_floor": sg.floor_status(floor_rel), "cam_floor_z": None if floor_rel is None else round(floor_rel, 2),
                "cam_above_floor_m": None if floor_rel is None else round(C_r[2] - floor_rel, 2),
                "cam_inside": bool(up[0] and up[2].z > 0.2), "side": sg.axis_side(cfg["axis"][0], cfg["axis"][1], C_r),
                "horizon_w": round(sg.horizon_w(pitch, lens, aspect), 3), "well_hip_ratio": well_hip,
                "at": [round(v, 3) for v in C_r], "aim": [round(v, 3) for v in A_r], "lens": lens, "cell": sg.cell_name(stage, C_r[0], C_r[1]),
                "labels": labels, "yeunu": yv}

    # hình phác Workbench (xám, đạo cụ/người màu) — một lần thiết lập cho mọi máy
    def clay_setup():
        scene.render.engine = "BLENDER_WORKBENCH"
        shd = scene.display.shading
        shd.light, shd.color_type = "STUDIO", "OBJECT"
        for ob in scene.objects:
            if ob.type == "MESH":
                ob.color = (0.72, 0.72, 0.72, 1)
                if ob.name.startswith("STAGE_WELL"):
                    ob.color = (0.35, 0.55, 0.95, 1) if ob.name == "STAGE_WELL" else (0.1, 0.1, 0.15, 1)
                elif ob.name.startswith("STAGE_KELLY"):
                    ob.color = (1.0, 0.55, 0.1, 1)
                elif ob.name.startswith("STAGE_YEUNU"):
                    ob.color = (0.9, 0.15, 0.2, 1)
        try:
            shd.show_cavity = True
        except AttributeError:
            pass
        if scene.world is not None:
            scene.world.color = (0.82, 0.86, 0.92)

    def clay(name, C_r, A_r, lens, res):
        cd = bpy.data.cameras.new(name)
        cd.lens, cd.clip_end = lens, 2000
        cam = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(cam)
        cam.location = scn(C_r)
        rp.look_at(cam, list(scn(A_r)))
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = res[0], res[1], 100
        fn = f"{name}_clay_raw.png"
        try:
            rp.render_to(os.path.join(out, fn), False)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"clay {name}: {e}")
            return None
        return fn

    s1cfg = cfg.get("s1", {})
    res, coarse, fine = s1cfg.get("res", [576, 1024]), s1cfg.get("coarse", [18, 32]), s1cfg.get("fine", [36, 64])
    aspect = res[0] / res[1]
    t0 = time.time()
    first = {}
    reqs_out = []
    for req in cfg.get("requests", []):
        rq = dict(req)
        for k in ("family", "s0"):
            if rq.get(k) == "@first":
                rq[k] = first.get(k)
        rows = []
        for c in sg.candidates(rq, aspect):
            m = measure(c["at"], c["aim"], c["lens"], res, coarse, rq["size"])
            m["alpha"], m["h"] = c["alpha"], c["h"]
            chk = sg.check_rules(m, rq)
            rows.append({"alpha": c["alpha"], "h": c["h"], "note": c["note"], "ok": chk["ok"], "fail": chk["fail"], "why": chk["why"],
                         "score": sg.rank_score(m, rq), "m": m, "c": c})
        good = sorted([r for r in rows if r["ok"]], key=lambda r: -r["score"])
        top = []
        for k, r in enumerate(good[:3]):
            c = r["c"]
            m = measure(c["at"], c["aim"], c["lens"], res, fine, rq["size"])       # đo lại bằng lưới mịn rồi chấm lại
            m["alpha"], m["h"] = c["alpha"], c["h"]
            chk = sg.check_rules(m, rq)
            top.append({"rank": k + 1, "alpha": c["alpha"], "h": c["h"], "pitch": round(c["pitch"], 1), "ok_fine": chk["ok"],
                        "fail_fine": chk["fail"], "why_fine": chk["why"], "score": sg.rank_score(m, rq), "m": m,
                        "name": f"{rq['name']}_{k + 1}"})
        if not first and top:
            first = {"family": sg.background_group(top[0]["m"]["percent"]), "s0": top[0]["m"]["side"]}
        fails = {}
        for r in rows:
            for L_ in r["fail"]:
                fails[L_] = fails.get(L_, 0) + 1
        reqs_out.append({"req": rq, "n": len(rows), "n_ok": len(good), "fail_counts": fails, "top": top,
                         "rows": [{k: v for k, v in r.items() if k not in ("m", "c")} | {"pct": r["m"]["percent"], "pitch": r["m"]["pitch"],
                                                                                      "frame_pct": r["m"]["subject_frame_pct"]} for r in rows]})
    shots_out = []
    for s in cfg.get("shots", []):
        C_r, A_r = sg.rel_from_model(stage, s["location"]), sg.rel_from_model(stage, s["look_at"])
        m = measure(C_r, A_r, s["lens"], res, fine, s["size"])
        rq = {"size": s["size"], "layer": s["layer"], "want": {}, "need": []}
        chk = sg.check_rules(m, rq)
        shots_out.append({"idx": s["idx"], "scene_id": s["scene_id"], "size": s["size"], "layer": s["layer"], "angle": s.get("angle"),
                          "ok": chk["ok"], "fail": chk["fail"], "why": chk["why"], "m": m, "name": f"shot{s['idx']}"})
    measure_sec = round(time.time() - t0, 1)
    keep = scene.render.engine
    try:
        clay_setup()
        for ro in reqs_out:
            for t in ro["top"]:
                t["clay"] = clay(t["name"], t["m"]["at"], t["m"]["aim"], t["m"]["lens"], res)
        for so in shots_out:
            so["clay"] = clay(so["name"], so["m"]["at"], so["m"]["aim"], so["m"]["lens"], res)
    finally:
        scene.render.engine = keep
    return {"requests": reqs_out, "shots": shots_out, "measure_sec": measure_sec, "res": res, "coarse": coarse, "fine": fine,
            "rule_th": {k: list(v) for k, v in sg.RULE_TH.items()}, "first": first}


def ss_end_spec(spec):
    """= core.stage_solver.end_spec (Blender không nạp package core): khung cuối chuyển động bỏ cỡ + vùng."""
    e = dict(spec, co=None)
    e["thanh_phan"] = [{k: v for k, v in c.items() if k not in ("co_pct", "vung")} for c in spec["thanh_phan"]]
    return e


def v2_block(cfg, stage, placed, marks, scene, dgv, scn, rel, mat_of, classify, Vector, bpy, rp, out, warnings):
    """Sân khấu 3D v2 giai đoạn (b) (PHUONG_PHAP mục 6.5, 7): mỗi shot đã được GIẢI ở máy chủ (core/stage_solver) thành vài phương án;
    ở đây đo bằng tia: thành phần khung, % thấy từng vật (trừ bị che, ghi vật che), vật cản sát ống kính, sàn dưới máy → luật P1–P4 +
    S1–S6 (sg.check_spec). Phương án đạt tốt nhất đo lại bằng lưới mịn + render hình phác. Nhãn chỉ cho thứ chính/phụ."""
    v2 = cfg["v2"]
    f_ = stage.get("factor", 1.0)
    persons = [p["name"] for p in cfg.get("props", []) if p.get("kind") == "person"]
    st = {"objs": {}, "well_hip": None, "dgv": dgv, "axis": cfg.get("axis")}

    def use(setup):
        """Nhịp của shot: chỉ hiện người nộm của nhịp đó (ẩn = không trúng tia, không render); vật + tỉ lệ giếng ÷ hông theo nhịp."""
        show = set(setup.get("show") or persons)
        for ob in scene.objects:
            if ob.name.startswith("STAGE_") and not ob.name.startswith("STAGE_WELL") and ob.type == "MESH":
                hide = not any(ob.name.startswith(f"STAGE_{n}_") for n in show)
                ob.hide_viewport = ob.hide_render = hide
        bpy.context.view_layer.update()
        st["dgv"] = bpy.context.evaluated_depsgraph_get()
        objs = setup["objs"]
        for k, o in objs.items():
            if o["kind"] == "moc" and marks.get(f"{k}_object"):             # tên object mốc (tháp) do K1 đo trong lượt này
                o["own"] = marks[f"{k}_object"]["name"]
        st["objs"] = objs
        st["axis"] = setup.get("axis") or cfg.get("axis")
        hips = [placed[o["prop"]]["hip_z"] for o in objs.values()
                if o["kind"] == "nguoi" and not o.get("in") and not o.get("tu_the") and o.get("prop") in placed]
        st["well_hip"] = round(placed["WELL"]["top_z"] / hips[0], 2) if ("WELL" in placed and hips) else None

    def group_of(obj, idx, loc, nor):
        o = obj.original if hasattr(obj, "original") else obj
        if o.name.startswith("STAGE_WELL"):
            return o, "gieng"
        if o.name.startswith("STAGE_"):
            return o, "nguoi_" + o.name.split("_")[1].lower()
        return o, sg.group_by_hit(classify(o, mat_of(obj, idx)), rel((0, 0, loc.z))[2], nor.z)

    def first_hit(L, P):
        seg = scn(P) - L
        ok, _, _, _, obj, _ = scene.ray_cast(st["dgv"], L, seg.normalized(), distance=seg.length + 0.05)
        return (obj.original if hasattr(obj, "original") else obj) if ok and obj is not None else None

    def measure(C_r, A_r, lens, res, rays, spec):
        L, A = scn(C_r), scn(A_r)
        aspect = res[0] / res[1]
        objs, dgv = st["objs"], st["dgv"]
        m = sg.frame_eval(C_r, A_r, lens, aspect, objs, co=spec["co"],
                          size_key=next(c["vat"] for c in spec["thanh_phan"] if c.get("vai") == "chinh"))
        chinh = [c["vat"] for c in spec["thanh_phan"] if c.get("vai") == "chinh"]
        size_key = chinh[0]
        near_main = min(math.dist(C_r, sg.anchor_point(objs[k])) for k in chinh)
        nu, nv = rays
        counts, occ, occ_m = {}, 0, None
        for j in range(nv):
            for i in range(nu):
                dr = Vector(sg.ray_dir(list(L), list(A), (i + 0.5) / nu, (j + 0.5) / nv, lens, aspect))
                ok, loc, nor, idx, obj, _ = scene.ray_cast(dgv, L, dr, distance=3000)
                if not ok or obj is None:
                    g = "troi"
                else:
                    o, g = group_of(obj, idx, loc, nor)
                    dist = (loc - L).length / f_
                    if g not in ("san", "gieng", "troi") and not g.startswith("nguoi") and dist < near_main - 0.3:
                        occ += 1
                        occ_m = dist if occ_m is None else min(occ_m, dist)
                counts[g] = counts.get(g, 0) + 1
        total = nu * nv
        for k, o in objs.items():                                          # % thấy = điểm trong khung mà tia tới chạm chính nó
            pts = sg.object_points(o, C_r, spec["co"] if k == size_key else None)
            seen, by = 0, {}
            for P in pts:
                if not sg.in_frame(sg.project(C_r, A_r, P, lens, aspect)):
                    continue
                hit = first_hit(L, P)
                if hit is not None and hit.name.startswith(o["own"]):
                    seen += 1
                elif hit is not None:
                    by[hit.name] = by.get(hit.name, 0) + 1
            e = m["obj"][k]
            e["seen_pct"] = round(100.0 * seen / len(pts), 1) if pts else 0.0
            e["blocked_by"] = max(by, key=by.get) if by else None
        floor_rel, o_ = None, L.copy()
        for _ in range(6):
            ok, loc, nor, idx, obj, _ = scene.ray_cast(dgv, o_, Vector((0, 0, -1)), distance=200)
            if not ok or obj is None:
                break
            ob = obj.original if hasattr(obj, "original") else obj
            if not ob.name.startswith("STAGE_"):
                floor_rel = rel((0, 0, loc.z))[2]
                break
            o_ = loc - Vector((0, 0, 0.03))
        up = scene.ray_cast(dgv, L, Vector((0, 0, 1)), distance=500)
        roles = {c["vat"]: c.get("vai") for c in spec["thanh_phan"]}
        labels = {}
        for k, o in objs.items():                                          # nhãn chỉ cho thứ chính / phụ (mục 7.4)
            if roles.get(k) not in ("chinh", "phu"):
                continue
            P = sg.zone_point(o, spec["co"] if roles[k] == "chinh" else None)
            hit = first_hit(L, P)
            b = None if hit is None or hit.name.startswith(o["own"]) else hit.name
            stt = sg.point_state(C_r, A_r, P, lens, aspect, blocked_by=b)
            labels[k] = {"label": o.get("label", k) + (" (chính)" if roles[k] == "chinh" else " (phụ)"), "state": stt["state"],
                         "uv": stt["uv"] and [round(x, 3) for x in stt["uv"]], "edge": stt["edge"],
                         "arrow": stt["arrow"] and [round(x, 3) for x in stt["arrow"]], "blocked_by": b}
        yaw, pitch = sg.look(C_r, A_r)
        m.update(percent={g: round(100 * n / total, 1) for g, n in sorted(counts.items(), key=lambda x: -x[1])}, rays=[nu, nv],
                 occluder_pct=round(100 * occ / total, 1), occluder_m=None if occ_m is None else round(occ_m, 2),
                 cam_floor=sg.floor_status(floor_rel), cam_floor_z=None if floor_rel is None else round(floor_rel, 2),
                 cam_above_floor_m=None if floor_rel is None else round(C_r[2] - floor_rel, 2), cam_inside=bool(up[0] and up[2].z > 0.2),
                 well_hip_ratio=st["well_hip"], horizon_w=round(sg.horizon_w(pitch, lens, aspect), 3), labels=labels,
                 at=[round(v, 3) for v in C_r], aim=[round(v, 4) for v in A_r], lens=lens, cell=sg.cell_name(stage, C_r[0], C_r[1]),
                 side=None if not st["axis"] else sg.axis_side(st["axis"][0], st["axis"][1], C_r))
        return m

    def clay(name, C_r, A_r, lens, res):
        scene.render.engine = "BLENDER_WORKBENCH"
        shd = scene.display.shading
        shd.light, shd.color_type = "STUDIO", "OBJECT"
        cols = {p["name"].split("_")[0]: tuple(p.get("rgb", (1.0, 0.45, 0.05))) for p in cfg.get("props", []) if p.get("kind") == "person"}
        for ob in scene.objects:
            if ob.type != "MESH":
                continue
            ob.color = (0.72, 0.72, 0.72, 1)
            if ob.name.startswith("STAGE_WELL"):
                ob.color = (0.35, 0.55, 0.95, 1) if ob.name == "STAGE_WELL" else (0.1, 0.1, 0.15, 1)
            elif ob.name.startswith("STAGE_"):
                ob.color = (*cols.get(ob.name.split("_")[1], (1.0, 0.45, 0.05)), 1)
        try:
            shd.show_cavity = True
        except AttributeError:
            pass
        if scene.world is not None:
            scene.world.color = (0.82, 0.86, 0.92)
        cd = bpy.data.cameras.new(name)
        cd.lens, cd.clip_end = lens, 2000
        cam = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(cam)
        cam.location = scn(C_r)
        rp.look_at(cam, list(scn(A_r)))
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = res[0], res[1], 100
        fn = f"{name}_clay_raw.png"
        try:
            rp.render_to(os.path.join(out, fn), False)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"clay {name}: {e}")
            return None
        return fn

    res, coarse, fine = v2.get("res", [576, 1024]), v2.get("coarse", [18, 32]), v2.get("fine", [36, 64])
    t0 = time.time()
    shots = []
    for su in v2["setups"]:
        spec = su["spec"]
        use(su)
        objs = st["objs"]
        rows = []
        for c in su["cands"]:
            m = measure(c["at"], c["aim"], c["lens"], res, coarse, spec)
            chk = sg.check_spec(m, spec, objs)
            c1 = c.get("c1_ok", True)
            rows.append({"tag": c["tag"], "fallback": c.get("fallback", False), "ok": chk["ok"] and c1, "c1_ok": c1, "check": chk, "m": m,
                         "c": c})
        rows.sort(key=lambda r: (not r["ok"], not r["c1_ok"], len(r["check"]["fail"]), r["check"]["miss"],
                                 -sum(r["check"]["phu"].values()), r["fallback"]))
        best = None
        if rows:
            c = rows[0]["c"]
            m = measure(c["at"], c["aim"], c["lens"], res, fine, spec)
            chk = sg.check_spec(m, spec, objs)
            best = {"tag": c["tag"], "fallback": c.get("fallback", False), "ok": chk["ok"] and c.get("c1_ok", True),
                    "c1_ok": c.get("c1_ok", True), "check": chk, "m": m, "name": f"v2_shot{su['shot']}"}
            if c.get("end"):                                                   # máy di chuyển: đo + chấm khung CUỐI (cỡ/vùng được đổi)
                me = measure(c["end"]["at"], c["end"]["aim"], c["lens"], res, fine, spec)
                ce = sg.check_spec(me, ss_end_spec(spec), objs)
                best["end"] = {"m": me, "check": ce, "name": f"v2_shot{su['shot']}_cuoi"}
                best["ok"] = best["ok"] and ce["ok"]
        shots.append({"shot": su["shot"], "spec": spec, "objs": objs, "n": len(rows), "n_ok": sum(1 for r in rows if r["ok"]), "best": best,
                      "rows": [{k: v for k, v in r.items() if k not in ("m", "c")} | {"at": r["m"]["at"], "pitch": round(r["m"]["pitch"], 1),
                                                                                      "pct": r["m"]["percent"]} for r in rows]})
    measure_sec = round(time.time() - t0, 1)
    keep = scene.render.engine
    try:
        for su, s in zip(v2["setups"], shots):
            if s["best"]:
                use(su)
                b = s["best"]["m"]
                s["best"]["clay"] = clay(s["best"]["name"], b["at"], b["aim"], b["lens"], res)
                if s["best"].get("end"):
                    e = s["best"]["end"]
                    e["clay"] = clay(e["name"], e["m"]["at"], e["m"]["aim"], e["m"]["lens"], res)
    finally:
        scene.render.engine = keep
    return {"shots": shots, "measure_sec": measure_sec, "res": res, "coarse": coarse, "fine": fine,
            "rule_th": {k: list(v) for k, v in sg.RULE_TH.items()}}


# ================================================ máy chủ ================================================
DEFAULT_DB = os.path.join(ROOT, "data", "manifest.sqlite")      # không phụ thuộc cwd; chạy từ worktree thì truyền --db


def _place_model3d(db, place):
    import sqlite3
    conn = sqlite3.connect(f"file:{os.path.abspath(db)}?mode=ro", uri=True)
    try:
        return json.loads(conn.execute("SELECT profile FROM assets WHERE id=?", (place,)).fetchone()[0])["model3d"]
    finally:
        conn.close()


def run_blender(cfg, out, timeout=1800):
    """Ghi cfg.json, chạy Blender nền (lượt Blender chung của plates3d), lưu blender.log; lỗi thì thoát kèm 15 dòng cuối."""
    sys.path.insert(0, ROOT)
    from core import plates3d
    cfg_path = os.path.join(out, "cfg.json" if cfg.get("mode") != "floor" else "cfg_floor.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    blender = plates3d.find_blender()
    if not blender:
        sys.exit("không tìm thấy Blender")
    args = ["-b", "--factory-startup", "-P", os.path.abspath(__file__), "--", "--config", cfg_path]
    with plates3d.blender_turn(owner="stage_grid"):
        if blender.startswith(plates3d.STORE):
            proc = plates3d._run_in_store(blender, args, out, timeout)
        else:
            import subprocess
            proc = subprocess.run([blender] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    with open(os.path.join(out, "blender.log"), "w", encoding="utf-8") as f:
        f.write(proc.stdout or "")
    if proc.returncode != 0 or "[stage]" not in (proc.stdout or ""):
        sys.exit("Blender lỗi:\n" + "\n".join((proc.stdout or "").splitlines()[-15:]))


def fix_spot_main(argv):
    """`fix-spot --place <id> --spot <tên> [--apply]`: đo sàn dưới spot bằng tia từ trên xuống (Blender, 0 USD). Không --apply: chỉ in
    z cũ / z mới. --apply: ghi z mới qua location_pack.set_model3d (giữ mọi khóa khác của model3d) — người dùng duyệt trước."""
    import argparse
    ap = argparse.ArgumentParser(prog="stage_grid.py fix-spot")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--place", type=int, required=True)
    ap.add_argument("--spot", required=True)
    ap.add_argument("--out", default=None, help="thư mục tạm cho cfg/log (mặc định <thư mục CSDL>/projects/_fix_spot)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    db = os.path.abspath(a.db)
    m3 = _place_model3d(db, a.place)
    if a.spot not in m3.get("spots", {}):
        sys.exit(f"không có spot '{a.spot}' ({', '.join(m3.get('spots', {}))})")
    spot = m3["spots"][a.spot]
    out = os.path.abspath(a.out or os.path.join(os.path.dirname(db), "projects", "_fix_spot"))
    os.makedirs(out, exist_ok=True)
    run_blender({"mode": "floor", "model": m3["path"], "out_dir": out, "real_height_m": m3.get("real_height_m"),
                 "origin_model": spot["at"], "cell_m": 1.0, "cols": 20, "rows": 20}, out, timeout=900)
    res = json.load(open(os.path.join(out, "fix_spot.json"), encoding="utf-8"))
    old, new = float(spot["at"][2]), float(res["floor_z_model"])
    print(f"place {a.place} spot {a.spot}: at = {spot['at']}  z cũ = {old:.3f}  sàn (tia từ trên xuống) = {new:.3f} trên {res['on']} "
          f"(n_z {res['normal_z']})  chênh = {new - old:+.3f} m")
    if not a.apply:
        print("(chưa ghi — thêm --apply để ghi z mới vào CSDL)")
        return
    import sqlite3
    sys.path.insert(0, ROOT)
    from core import location_pack
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        cur = json.loads(conn.execute("SELECT profile FROM assets WHERE id=?", (a.place,)).fetchone()["profile"])["model3d"]
        spots = json.loads(json.dumps(cur["spots"]))
        spots[a.spot]["at"] = [spots[a.spot]["at"][0], spots[a.spot]["at"][1], round(new, 3)]
        note = f"09/10 Sân khấu 3D: spot {a.spot} z {old:g} → {new:.3f} (tia từ trên xuống chạm {res['on']}; người dùng duyệt)."
        location_pack.set_model3d(conn, a.place, cur["path"], spots, default_spot=cur.get("default_spot"), anchor=cur.get("anchor"),
                                  real_height_m=cur.get("real_height_m"), sun_azimuth=cur.get("sun_azimuth", 250.0),
                                  notes=((cur.get("notes") or "") + " " + note).strip(), light=cur.get("light"))
    finally:
        conn.close()
    print("đã ghi:", note)


# ---- Bước 2: 3 yêu cầu góc máy mẫu cho #24 (Kelly ở O nhìn 350° về giếng; tháp ở Bắc 16 m) ----
def requests_24(facing, well):
    H = KELLY_H
    mid = [well[0] / 2, well[1] / 2, round((sg.CHEST * H + WELL_H) / 2, 3)]
    return [
        {"name": "R1_toan_canh", "title": "toàn cảnh mở thấy tháp + giếng + Kelly", "aim": [0.0, 0.0, round(sg.CHEST * H, 3)],
         "size": "WS", "layer": "ngang", "H": H, "want": {"thap": True}, "need": ["gieng"], "facing": facing,
         "rank": {"thap": 1.0, "gieng": 2.0, "nguoi_kelly": 1.0}},
        {"name": "R2_qua_vai", "title": "qua vai Kelly cúi nhìn giếng", "aim": mid, "size": "WS", "layer": "cao", "H": H,
         "see": "back", "need": ["gieng"], "facing": facing, "s0": "@first", "family": "@first",
         "rank": {"gieng": 2.0, "nguoi_kelly": 1.0}, "single_ok": False},
        # nhắm giữa phần thân trong khung MS (đỉnh đầu → 0,45·H): z = H·(1 − 0,55/2); lần đầu nhắm mắt thì cả 72 hỏng L3 (100–112 %)
        {"name": "R3_goc_nguoc", "title": "góc ngược thấy mặt Kelly, không thấy tháp",
         "aim": [0.0, 0.0, round(H * (1 - sg.FRAMING["MS"][0] / 2), 3)],
         "size": "MS", "layer": "thap", "H": H, "see": "face", "want": {"thap": False}, "facing": facing, "s0": "@first",
         "reverse_ok": True, "rank": {"nguoi_kelly": 1.0}},
    ]


def shots_of(db, project):
    """Camera hiện tại các shot từ location_pack.plan (CSDL chỉ đọc) → cỡ, lớp độ cao, vị trí (hệ model)."""
    import re
    import sqlite3
    sys.path.insert(0, ROOT)
    from core import location_pack
    conn = sqlite3.connect(f"file:{os.path.abspath(db)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        items = location_pack.plan(conn, project)
    finally:
        conn.close()
    layer = {"eye_level": "ngang", "high_angle": "cao", "low_angle": "thap", "overhead": "tren_dau"}
    out = []
    for it in items:
        c = it["camera"]
        mm = re.search(r"cỡ (\w+)", str((it.get("camera_why") or {}).get("distance", "")))
        out.append({"idx": it["idx"], "scene_id": it["scene_id"], "location": c["location"], "look_at": c["look_at"], "lens": c["lens"],
                    "angle": c.get("angle"), "layer": layer.get(c.get("angle"), "ngang"), "size": mm.group(1) if mm else "MS",
                    "spot": it["spot"]})
    return out


def s1_main(argv):
    """`s1 --out <dir> [--project 24]`: ứng viên máy + L1–L10 cho 3 yêu cầu mẫu + đo các shot hiện có, MỘT lượt Blender."""
    import argparse
    ap = argparse.ArgumentParser(prog="stage_grid.py s1")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--place", type=int, default=263)
    ap.add_argument("--spot", default="plaza_front")
    ap.add_argument("--project", type=int, default=24)
    ap.add_argument("--out", required=True)
    ap.add_argument("--facing", type=float, default=350.0)
    ap.add_argument("--well-dist", type=float, default=1.6)
    ap.add_argument("--draw-only", action="store_true")
    ap.add_argument("--yeunu-in-well", action="store_true", help="yêu nữ đứng trong giếng (ngực ngang miệng giếng), giếng rỗng")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    if not a.draw_only:
        m3 = _place_model3d(a.db, a.place)
        cfg = build_cfg(m3, m3["spots"][a.spot], out, a.facing, a.well_dist, yeunu_in_well=a.yeunu_in_well)
        well = cfg["props"][0]["at"]
        cfg.update(cameras=[], requests=requests_24(a.facing, well), shots=shots_of(a.db, a.project),
                   s1={"res": [576, 1024], "coarse": [18, 32], "fine": [36, 64]})
        run_blender(cfg, out, timeout=3600)
    draw_top(out, cams=[])
    draw_s1(out)
    report_s1(out)


def _overlay_clay(out, rec, footer):
    from PIL import Image, ImageDraw, ImageFont
    m = rec["m"]
    img = Image.open(os.path.join(out, rec["clay"])).convert("RGBA")
    W, H = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    try:
        font, big = ImageFont.truetype("arial.ttf", 13), ImageFont.truetype("arialbd.ttf", 17)
    except OSError:
        font = big = ImageFont.load_default()
    d.rectangle([0, 0, W, H * 0.15], fill=(255, 0, 0, 40))
    for t in (1 / 3, 2 / 3):
        d.line([(W * t, 0), (W * t, H)], fill=(255, 255, 255, 160), width=1)
        d.line([(0, H * t), (W, H * t)], fill=(255, 255, 255, 160), width=1)
    wh = m["horizon_w"]
    if 0 <= wh <= 1:
        d.line([(0, wh * H), (W, wh * H)], fill=(0, 120, 255, 230), width=2)
    d.text((6, min(max(wh, 0), 0.95) * H + 2), f"chân trời w_h = {wh:.3f}" + ("" if 0 <= wh <= 1 else " (ngoài khung)"),
           fill=(0, 80, 220, 255), font=font)
    draw_labels(d, W, H, m["labels"], big)
    d.rectangle([0, H - 64, W, H], fill=(255, 255, 255, 190))
    for k, line in enumerate(footer):
        d.text((6, H - 60 + 19 * k), line, fill=(0, 0, 0, 255), font=font)
    img = Image.alpha_composite(img, ov).convert("RGB")
    fn = rec["clay"].replace("_clay_raw.png", "_clay.png")
    img.save(os.path.join(out, fn))
    return fn


def _montage(out, files, fn, title):
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(os.path.join(out, f)) for f in files if f]
    if not ims:
        return
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * len(ims), h + 34), (255, 255, 255))
    for k, im in enumerate(ims):
        sheet.paste(im, (k * w, 34))
    try:
        font = ImageFont.truetype("arialbd.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    ImageDraw.Draw(sheet).text((8, 6), title, fill=(0, 0, 0), font=font)
    sheet.save(os.path.join(out, fn))


def draw_s1(out):
    s1 = json.load(open(os.path.join(out, "s1.json"), encoding="utf-8"))
    for ro in s1["requests"]:
        files, cams = [], []
        for t in ro["top"]:
            m = t["m"]
            if t.get("clay"):
                files.append(_overlay_clay(out, t, [
                    f"#{t['rank']} α {t['alpha']}° · cao {m['cam_above_floor_m']} m · pitch {m['pitch']}° · f {m['lens']:g} · ô {m['cell']}",
                    f"Kelly {m['subject_frame_pct']}% khung, thấy {m['subject_hit_pct']}% · " +
                    ", ".join(f"{g} {v}" for g, v in list(m["percent"].items())[:4]),
                    *([] if not m.get("yeunu") else [
                        f"yêu nữ thấy {m['yeunu']['pct_thay']}% (z {m['yeunu']['thay_tu_z']}–{m['yeunu']['thay_den_z']}) · "
                        f"giếng che {m['yeunu']['pct_che_gieng']}% · khác che {m['yeunu']['pct_che_khac']}% · ngoài khung {m['yeunu']['pct_ngoai_khung']}%"]),
                    "đạt L1–L10" if t["ok_fine"] else "lưới mịn hỏng: " + ",".join(t["fail_fine"])]))
            fov = sg.fov(m["lens"], s1["res"][0] / s1["res"][1])
            cams.append((f"#{t['rank']}", {"xyz": m["at"], "yaw_deg": m["yaw"], "fov_h_v_deg": list(fov), "cell": m["cell"]}))
        _montage(out, files, f"{ro['req']['name']}_top3.png", f"{ro['req']['title']} — top-3 / {ro['n_ok']} đạt / {ro['n']} ứng viên")
        draw_top(out, cams=cams, fn=f"{ro['req']['name']}_topgrid.png")
    files = []
    for so in s1["shots"]:
        m = so["m"]
        if so.get("clay"):
            files.append(_overlay_clay(out, so, [
                f"shot {so['idx']} {so['size']} {so['angle']} · cao {m['cam_above_floor_m']} m trên sàn · pitch {m['pitch']}° · f {m['lens']:g}",
                f"Kelly {m['subject_frame_pct']}% khung, thấy {m['subject_hit_pct']}% · " +
                ", ".join(f"{g} {v}" for g, v in list(m["percent"].items())[:4]),
                "đạt" if so["ok"] else "hỏng: " + ",".join(so["fail"])]))
    _montage(out, files, "shots24_clay.png", "#24 — 9 shot, camera hiện tại (location_pack.plan), hình phác + số đo")


def report_s1(out):
    s1 = json.load(open(os.path.join(out, "s1.json"), encoding="utf-8"))
    print(f"đo {s1['measure_sec']} s; shot mở → {s1['first']}")
    print("shot | cỡ/góc | cao trên sàn | pitch | Kelly %khung/thấy% | tháp% sàn% trời% tường% nhà% giếng% | cản% | luật hỏng")
    for so in s1["shots"]:
        m, p = so["m"], so["m"]["percent"]
        print(f"{so['idx']} | {so['size']}/{so['layer']} | {m['cam_above_floor_m']} ({m['cam_floor']}) | {m['pitch']} | "
              f"{m['subject_frame_pct']}/{m['subject_hit_pct']} | " + " ".join(str(p.get(g, 0)) for g in ("thap", "san", "troi", "tuong", "nha", "gieng"))
              + f" | {m['occluder_pct']}@{m['occluder_m']} | {','.join(so['fail']) or '-'}")
    for ro in s1["requests"]:
        print(f"{ro['req']['name']}: {ro['n_ok']}/{ro['n']} đạt; luật hỏng (số ứng viên) {ro['fail_counts']}")
        for t in ro["top"]:
            m = t["m"]
            print(f"   #{t['rank']} α {t['alpha']} cao {m['cam_above_floor_m']} pitch {m['pitch']} điểm {t['score']} "
                  f"{'đạt' if t['ok_fine'] else 'mịn hỏng ' + ','.join(t['fail_fine'])} | {m['percent']} | yêu nữ {m.get('yeunu')}")


# ================================ v2: giải máy từ yêu cầu khung (PHUONG_PHAP_SAN_KHAU_3D mục 6, 7, 10 — V1) ================================
ZONE_RGB = [(255, 0, 200), (0, 170, 255), (0, 200, 90), (255, 150, 0)]


def _aspect(blocking):
    a = str(blocking.get("aspect", "9:16"))
    w, h = (float(x) for x in a.split(":"))
    return w / h, ([576, 1024] if w < h else [1024, 576])


def blender_props(beats):
    """Vật của bộ giải theo từng nhịp ({nhịp: {key: vật}}) → props cho blender_main. Giếng trước (người 'trong giếng' tính chân theo giếng);
    mỗi tư thế khác nhau của một người = một người nộm riêng `STAGE_<KHÓA>_V<n>_…` (ẩn/hiện theo shot ở v2_block). Ghi `own`/`prop` vào vật."""
    if isinstance(next(iter(beats.values()), {}).get("kind"), str):          # một dàn cảnh không nhịp
        beats = {"": beats}
    wells = {}
    for objs in beats.values():
        for o in objs.values():
            if o["kind"] == "dao_cu" and o.get("shape") == "gieng":
                wells[o["key"]] = o
            elif o["kind"] == "dao_cu":
                raise SystemExit(f"v2: chưa dựng được khối thay thế cho '{o['key']}' (mới có giếng + người nộm)")
    if len(wells) > 1:
        raise SystemExit("v2: dàn cảnh có > 1 giếng — Blender chỉ dựng một STAGE_WELL")
    props = [{"name": "WELL", "kind": "well", "at": list(o["xy"]), "radius": o["r"], "height": o["h"], "sides": 8,
              "source": o.get("source") or WELL_SRC, "hollow": bool(o.get("hollow"))} for o in wells.values()]
    pal, variants = {}, {}
    colours = [[1.0, 0.45, 0.05], [0.85, 0.05, 0.1], [0.2, 0.75, 0.3], [0.6, 0.3, 0.9]]
    for objs in beats.values():
        for o in objs.values():
            if o["kind"] != "nguoi":
                continue
            sig = (o["key"], round(o["xy"][0], 3), round(o["xy"][1], 3), round(o.get("z", 0.0), 3), o["H"], o.get("facing"), o.get("in"))
            if sig not in variants:
                n = sum(1 for v in variants.values() if v["key"] == o["key"])
                rgb = pal.setdefault(o["key"], colours[len(pal) % len(colours)])
                p = {"name": f"{o['key'].upper()}_V{n}", "key": o["key"], "kind": "person", "at": list(o["xy"]), "height": o["H"],
                     "facing": o.get("facing") or 0.0, "source": o.get("source") or "blocking.json", "rgb": rgb}
                if o.get("in"):
                    p["in_well"] = {"foot_z": round(o["z"] - wells[o["in"]].get("z", 0.0), 3), "rule": "chân = cao giếng − 0,72·H"}
                variants[sig] = p
                props.append(p)
            o["prop"] = variants[sig]["name"]
            o["own"] = f"STAGE_{o['prop']}_"
    return props


def v2_main(argv):
    """`v2 --blocking b.json --specs s.json --out <dir> [--stage-from <dir K1>] [--solve-only] [--draw-only]`: K3 giải máy (thuần, ms)
    → K4 Blender đo phương án (một lượt) → hình phác có vùng đích + bảng. 0 USD."""
    import argparse
    sys.path.insert(0, ROOT)
    from core import stage_solver as ss
    ap = argparse.ArgumentParser(prog="stage_grid.py v2")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--blocking", required=True)
    ap.add_argument("--specs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage-from", default=None, help="thư mục K1 có stage.json + grid.json (mốc tháp, ô sàn); mặc định --out")
    ap.add_argument("--max-cands", type=int, default=31, help="số phương án mỗi shot gửi Blender (lời giải + đường lùi)")
    ap.add_argument("--solve-only", action="store_true", help="chỉ giải + kiểm giai đoạn (a), không chạy Blender")
    ap.add_argument("--draw-only", action="store_true")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    blocking = json.load(open(a.blocking, encoding="utf-8"))
    specs = json.load(open(a.specs, encoding="utf-8"))
    specs = specs.get("shots", specs) if isinstance(specs, dict) else specs
    aspect, res = _aspect(blocking)
    if not a.draw_only:
        src = os.path.abspath(a.stage_from or out)
        st = json.load(open(os.path.join(src, "stage.json"), encoding="utf-8"))
        grid = json.load(open(os.path.join(src, "grid.json"), encoding="utf-8"))["cells"]
        t0 = time.time()
        sol = ss.solve_scene(specs, blocking, aspect, marks=st.get("marks"), grid_cells=grid, stage=st)
        solve_ms = round(1000 * (time.time() - t0), 1)
        sol["solve_ms"] = solve_ms
        with open(os.path.join(out, "setups.json"), "w", encoding="utf-8") as f:
            json.dump(sol, f, ensure_ascii=False, indent=1)
        print(f"K3 giải {len(specs)} shot trong {solve_ms} ms; trục {blocking.get('axis')} s₀ = {sol['s0']}")
        for s in sol["shots"]:
            n_ok = sum(1 for c in s["cams"] if c["check"]["ok"] and c["c1_ok"])
            print(f"  shot {s['shot']}: {len(s['cams'])} phương án, {n_ok} đạt giai đoạn (a)" + "".join(f"\n    ! {e}" for e in s["errors"])
                  + "".join(f"\n    · {e}" for e in s["notes"] + s.get("advice", [])))
        if a.solve_only:
            return
        m3 = _place_model3d(a.db, blocking["place"])
        spot = m3["spots"][blocking["spot"]]
        beats = sol["beats"]
        props = blender_props(beats)
        setups = []
        for s in sol["shots"]:
            if s["errors"] or not s["cams"]:
                continue
            spec = next(p for p in specs if p.get("shot") == s["shot"])
            bo = {k: v for k, v in beats[spec.get("nhip") or ""].items() if k in (s.get("objs_used") or beats[spec.get("nhip") or ""])}
            cands = [{k: c.get(k) for k in ("tag", "at", "aim", "lens", "fallback", "c1_ok", "end")} for c in s["cams"][:a.max_cands]]
            for c in cands:
                if c["end"]:
                    c["end"] = {"at": c["end"]["at"], "aim": c["end"]["aim"]}
            setups.append({"shot": s["shot"], "spec": spec, "cands": cands, "objs": bo,
                           "show": [o["prop"] for o in bo.values() if o.get("prop")],
                           "axis": None if not blocking.get("axis") else
                           [list(beats[spec.get("nhip") or ""][k]["xy"]) + [0.0] for k in blocking["axis"]]})   # trục theo nhịp đầy đủ (POV bỏ người cầm máy khỏi vật)
        extra = [[o["xy"][0], o["xy"][1], 2.0] for bo in beats.values() for o in bo.values() if o["kind"] != "moc"]
        cfg = {"model": m3["path"], "out_dir": out, "real_height_m": m3.get("real_height_m"), "origin_model": spot["at"],
               "anchor_model": m3["anchor"], "cell_m": 1.0, "cols": 20, "rows": 20, "acting_area": {"half_m": 3.0, "extra": extra},
               "engine": "auto", "samples": 16, "top_view": {"centre": [0.0, 5.5], "size_m": 42.0, "px": 1260}, "props": props,
               "axis": sol["axis"], "targets": {}, "cameras": [],
               "v2": {"setups": setups, "res": res, "coarse": [18, 32], "fine": [36, 64]}}
        run_blender(cfg, out, timeout=3600)
    draw_v2(out)
    report_v2(out)


def _overlay_v2(out, best, spec, objs, footer):
    """Hình phác v2: lưới một phần ba, chân trời, vùng thanh trên 15 %, VÙNG ĐÍCH từng thứ chính (khung màu) + tâm đo được (chấm vuông
    cùng màu, nối bằng vạch khi lệch), nhãn chỉ thứ chính/phụ."""
    from PIL import Image, ImageDraw, ImageFont
    m = best["m"]
    img = Image.open(os.path.join(out, best["clay"])).convert("RGBA")
    W, H = img.size
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    try:
        font, big = ImageFont.truetype("arial.ttf", 13), ImageFont.truetype("arialbd.ttf", 16)
    except OSError:
        font = big = ImageFont.load_default()
    d.rectangle([0, 0, W, H * 0.15], fill=(255, 0, 0, 30))
    for t in (1 / 3, 2 / 3):
        d.line([(W * t, 0), (W * t, H)], fill=(255, 255, 255, 160), width=1)
        d.line([(0, H * t), (W, H * t)], fill=(255, 255, 255, 160), width=1)
    wh = m["horizon_w"]
    if 0 <= wh <= 1:
        d.line([(0, wh * H), (W, wh * H)], fill=(0, 120, 255, 200), width=2)
    k = 0
    for c in spec["thanh_phan"]:
        if c.get("vai") != "chinh":
            continue
        col = ZONE_RGB[k % len(ZONE_RGB)]
        k += 1
        z = sg.parse_zone(c.get("vung"))
        u0, u1 = z["u"] or (0.0, 1.0)
        w0, w1 = z["w"] or (0.0, 1.0)
        box = [u0 * W + 3, w0 * H + 3, u1 * W - 3, w1 * H - 3]
        for off in range(3):
            d.rectangle([box[0] + off, box[1] + off, box[2] - off, box[3] - off], outline=(*col, 230))
        lab = objs[c["vat"]].get("label", c["vat"])
        d.text((box[0] + 6, box[1] + 4), f"đích {lab}: {c.get('vung') or '—'}", fill=(*col, 255), font=font)
        uv = (m["obj"].get(c["vat"]) or {}).get("uv")
        if uv:
            x, y = uv[0] * W, uv[1] * H
            d.rectangle([x - 6, y - 6, x + 6, y + 6], fill=(*col, 255), outline=(0, 0, 0, 255))
            if sg.zone_miss(uv, z) > 0:
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                d.line([(x, y), (cx, cy)], fill=(*col, 200), width=2)
    draw_labels(d, W, H, m["labels"], big)
    d.rectangle([0, H - 20 * len(footer) - 6, W, H], fill=(255, 255, 255, 200))
    for i, line in enumerate(footer):
        d.text((6, H - 20 * len(footer) - 2 + 20 * i), line, fill=(0, 0, 0, 255), font=font)
    img = Image.alpha_composite(img, ov).convert("RGB")
    fn = best["clay"].replace("_clay_raw.png", "_clay.png")
    img.save(os.path.join(out, fn))
    return fn


def draw_v2(out):
    v2 = json.load(open(os.path.join(out, "v2.json"), encoding="utf-8"))
    files, cams = [], []
    for s in v2["shots"]:
        objs = s["objs"]
        b = s["best"]
        if not b or not b.get("clay"):
            continue
        m = b["m"]
        main = [c["vat"] for c in s["spec"]["thanh_phan"] if c.get("vai") == "chinh"]
        footer = [f"shot {s['shot']} {s['spec']['co']} · {s['spec'].get('muc_dich', '')[:60]}",
                  f"ô {m['cell']} · cao {m['cam_above_floor_m']} m · pitch {m['pitch']:.1f}° · f {m['lens']:g} · {b['tag']}",
                  " · ".join(f"{objs[k].get('label', k)} thấy {m['obj'][k]['seen_pct']:g}% cỡ {m['obj'][k]['size_pct']}%" for k in main),
                  ("ĐẠT P/S" if b["ok"] else "HỎNG " + "; ".join(f"{c}: {w}" for c, w in b["check"]["why"].items()))[:110]
                  + f" · {s['n_ok']}/{s['n']} phương án đạt"]
        files.append(_overlay_v2(out, b, s["spec"], objs, footer))
        if b.get("end") and b["end"].get("clay"):
            e, mv = b["end"], s["spec"].get("may") or {}
            em = e["m"]
            files.append(_overlay_v2(out, e, ss_end_spec(s["spec"]), objs, [
                f"shot {s['shot']} — KHUNG CUỐI: máy {mv.get('kieu')} {mv.get('m')} m" + (f", rung {mv['rung']}" if mv.get("rung") else ""),
                f"ô {em['cell']} · cao {em['cam_above_floor_m']} m · pitch {em['pitch']:.1f}°",
                " · ".join(f"{objs[k].get('label', k)} thấy {em['obj'][k]['seen_pct']:g}% cỡ {em['obj'][k]['size_pct']}%" for k in main if k in em["obj"]),
                ("ĐẠT" if e["check"]["ok"] else "HỎNG " + "; ".join(f"{c}: {w}" for c, w in e["check"]["why"].items()))[:110]]))
        fov = sg.fov(m["lens"], v2["res"][0] / v2["res"][1])
        cams.append((f"s{s['shot']}", {"xyz": m["at"], "yaw_deg": m["yaw"], "fov_h_v_deg": list(fov), "cell": m["cell"]}))
    for i in range(0, len(files), 5):
        _montage(out, files[i:i + 5], f"v2_shots_{i // 5 + 1}.png", "Sân khấu 3D v2 — máy GIẢI từ yêu cầu khung (khung màu = vùng đích, ô vuông = tâm đo được)")
    if os.path.exists(os.path.join(out, "stage.json")):
        draw_top(out, cams=cams, fn="v2_topgrid.png")


def report_v2(out):
    v2 = json.load(open(os.path.join(out, "v2.json"), encoding="utf-8"))
    print(f"K4 Blender đo {sum(s['n'] for s in v2['shots'])} phương án trong {v2['measure_sec']} s")
    print("shot | đạt/phương án | chọn | ô · cao · pitch | thấy% / cỡ% thứ chính | luật hỏng")
    for s in v2["shots"]:
        b = s["best"]
        if not b:
            print(f"{s['shot']} | 0/{s['n']} | — |")
            continue
        m = b["m"]
        main = [c["vat"] for c in s["spec"]["thanh_phan"] if c.get("vai") == "chinh"]
        print(f"{s['shot']} | {s['n_ok']}/{s['n']} | {b['tag']} | {m['cell']} · {m['cam_above_floor_m']} · {m['pitch']:.1f} | "
              + ", ".join(f"{k} {m['obj'][k]['seen_pct']:g}/{m['obj'][k]['size_pct']}" for k in main)
              + f" | {', '.join(b['check']['fail']) or '-'} {b['check']['why'] or ''}")
        if b.get("end"):
            e = b["end"]
            print(f"   └ khung cuối ({s['spec']['may']}): ô {e['m']['cell']} · pitch {e['m']['pitch']:.1f} | "
                  + ", ".join(f"{k} {e['m']['obj'][k]['seen_pct']:g}/{e['m']['obj'][k]['size_pct']}" for k in main if k in e["m"]["obj"])
                  + f" | {', '.join(e['check']['fail']) or 'đạt'} {e['check']['why'] or ''}")


def _scene_shots(db, pid):
    """Kịch bản từng shot của dự án (CSDL CHỈ ĐỌC): hành động + ghi chú khung cũ (blocking) + độ dài."""
    import sqlite3
    conn = sqlite3.connect(f"file:{os.path.abspath(db)}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    finally:
        conn.close()
    out = []
    for idx, data in rows:
        d = json.loads(data or "{}")
        out.append({"shot": idx, "action": d.get("action", ""), "ghi_chu_khung_cu": d.get("blocking", ""),
                    "do_dai": f"{d.get('duration')} s" if d.get("duration") else ""})
    return out


def _floor_notes(grid_cells, half=4.0):
    """Ô sàn quanh vùng diễn (±half m quanh O) không cùng mặt sàn / có vật chắn — căn cứ cho Director."""
    out = []
    for c in grid_cells:
        if abs(c["x"]) <= half and abs(c["y"]) <= half and (c.get("status") != "same" or c.get("obstacle")):
            out.append(f"ô {c['cell']} (tâm {c['x']:+.1f} Đ, {c['y']:+.1f} B): {c.get('status')}"
                       + (f", vật chắn cao {c.get('top_z')} m" if c.get("obstacle") else ""))
    return out or ["mọi ô trong ±4 m quanh O là mặt sàn phẳng, đứng được"]


def v3_main(argv):
    """`v3 --inputs v3_inputs.json --out <dir> --stage-from <dir K1> --hand <dir v2 bản tay> [--yes]`: Director (Claude) viết dàn cảnh +
    yêu cầu khung → K3/K4 (v2) → không đạt thì gửi lại kết quả đo, tối đa 2 lượt → so với bản viết tay. Không --yes: chỉ in ước tính."""
    import argparse
    sys.path.insert(0, ROOT)
    from core import cost, llm_runner
    from core import stage_director as sd
    ap = argparse.ArgumentParser(prog="stage_grid.py v3")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage-from", required=True)
    ap.add_argument("--hand", default=None, help="thư mục v2 của bản viết tay (v2.json) để so")
    ap.add_argument("--yes", action="store_true", help="gọi Claude thật (tốn tiền, ghi sổ chi)")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    inputs = json.load(open(a.inputs, encoding="utf-8"))
    st = json.load(open(os.path.join(a.stage_from, "stage.json"), encoding="utf-8"))
    grid = json.load(open(os.path.join(a.stage_from, "grid.json"), encoding="utf-8"))["cells"]
    inputs.setdefault("shots", _scene_shots(a.db, inputs["pid"]))
    inputs.setdefault("floor", _floor_notes(grid))
    import sqlite3
    conn = sqlite3.connect(os.path.abspath(a.db))
    conn.row_factory = sqlite3.Row
    try:
        one = cost.llm_estimate(conn, sd.STAGE, 1)
        worst = cost.llm_estimate(conn, sd.STAGE, 2 * sd.MAX_ROUNDS)
        m = cost.LLM_MARGIN
        print(f"V3 ước tính (model {cost.llm_model()}): 1 lượt ≈ {one * m:.3f} USD; tối đa {2 * sd.MAX_ROUNDS} lời gọi "
              f"(2 lượt sửa × hỏi lại khi sai mẫu) ≈ {worst * m:.3f} USD")
        if not a.yes:
            print("(chưa gọi — thêm --yes)")
            return
        client = llm_runner.client_from_env(ledger=llm_runner.db_file(conn))
        prev, feedback, rounds = None, [], []
        for rnd in range(1, sd.MAX_ROUNDS + 1):
            text = sd.build_prompt(inputs, prev, feedback)
            with open(os.path.join(out, f"prompt_r{rnd}.md"), "w", encoding="utf-8") as f:
                f.write(text)
            with llm_runner.tagged(sd.STAGE, inputs.get("pid")):
                obj, tin, tout = llm_runner.ask_json(client, text, lambda o: sd.validate_answer(o, inputs, st.get("marks")),
                                                     note=lambda s_: print("  !", s_))
            print(f"lượt {rnd}: Claude vào {tin} / ra {tout} token")
            bl = dict(obj["blocking"], place=inputs["place"], spot=inputs["spot"].split()[0], aspect=inputs.get("aspect", "9:16"))
            rd = os.path.join(out, f"r{rnd}")
            os.makedirs(rd, exist_ok=True)
            for fn, data in (("answer.json", obj), ("blocking.json", bl), ("shot_specs.json", {"shots": obj["shot_specs"]})):
                with open(os.path.join(rd, fn), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
            v2_main(["--db", a.db, "--blocking", os.path.join(rd, "blocking.json"), "--specs", os.path.join(rd, "shot_specs.json"),
                     "--out", rd, "--stage-from", a.stage_from])
            solve = json.load(open(os.path.join(rd, "setups.json"), encoding="utf-8"))
            v2 = json.load(open(os.path.join(rd, "v2.json"), encoding="utf-8"))
            feedback = sd.feedback_from(solve, v2)
            n_ok = sum(1 for s in v2["shots"] if s.get("best") and s["best"]["ok"])
            rounds.append({"round": rnd, "tokens": [tin, tout], "ok": n_ok, "n": len(obj["shot_specs"]), "feedback": feedback,
                           "can_hoi": obj.get("can_hoi")})
            print(f"lượt {rnd}: {n_ok}/{len(obj['shot_specs'])} shot đạt" + "".join(f"\n   → {x}" for x in feedback))
            if not feedback:
                break
            prev = obj
        res = {"rounds": rounds}
        if a.hand:
            hand = json.load(open(os.path.join(a.hand, "v2.json"), encoding="utf-8"))
            res["compare"] = sd.compare(hand, v2)
            print("shot | AI đạt | tay đạt | máy lệch m | hướng lệch ° | pitch AI/tay | thứ chính AI ↔ tay | thêm AI ↔ tay")
            for r in res["compare"]:
                print(f"{r['shot']} | {r['ai_ok']} | {r['hand_ok']} | {r.get('cam_dist_m')} | {r.get('yaw_diff')} | "
                      f"{r.get('pitch_ai')}/{r.get('pitch_hand')} | {r['ai_main']} ↔ {r['hand_main']} | {r['ai_extra']} ↔ {r['hand_extra']}")
        with open(os.path.join(out, "v3.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    finally:
        conn.close()


def host_main(argv=None):
    import argparse
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "v3":
        return v3_main(argv[1:])
    if argv and argv[0] == "fix-spot":
        return fix_spot_main(argv[1:])
    if argv and argv[0] == "s1":
        return s1_main(argv[1:])
    if argv and argv[0] == "v2":
        return v2_main(argv[1:])
    sys.path.insert(0, ROOT)
    from core import plates3d
    ap = argparse.ArgumentParser(description="Bước 0 lưới sân khấu (0 USD)")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--place", type=int, default=263)
    ap.add_argument("--spot", default="plaza_front")
    ap.add_argument("--out", required=True)
    ap.add_argument("--facing", type=float, default=350.0, help="hướng Kelly nhìn (độ từ Bắc) — #24: về giếng/tháp")
    ap.add_argument("--well-dist", type=float, default=1.6)
    ap.add_argument("--draw-only", action="store_true", help="chỉ vẽ lại topgrid.png + in bảng từ JSON đã có")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    if not a.draw_only:
        import sqlite3
        conn = sqlite3.connect(f"file:{os.path.abspath(a.db)}?mode=ro", uri=True)
        prof = json.loads(conn.execute("SELECT profile FROM assets WHERE id=?", (a.place,)).fetchone()[0])
        m3 = prof["model3d"]
        spot = m3["spots"][a.spot]
        cfg = build_cfg(m3, spot, out, a.facing, a.well_dist)
        cfg_path = os.path.join(out, "cfg.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        blender = plates3d.find_blender()
        if not blender:
            sys.exit("không tìm thấy Blender")
        args = ["-b", "--factory-startup", "-P", os.path.abspath(__file__), "--", "--config", cfg_path]
        with plates3d.blender_turn(owner="stage_grid"):
            if blender.startswith(plates3d.STORE):
                proc = plates3d._run_in_store(blender, args, out, 1800)
            else:
                import subprocess
                proc = subprocess.run([blender] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        with open(os.path.join(out, "blender.log"), "w", encoding="utf-8") as f:
            f.write(proc.stdout or "")
        if proc.returncode != 0 or not os.path.exists(os.path.join(out, "frames.json")):
            sys.exit("Blender lỗi:\n" + "\n".join((proc.stdout or "").splitlines()[-15:]))
    draw_top(out)
    for name, letter in (("try_wide", "a"), ("try_down", "b")):
        draw_clay(out, name, letter)
    report(out)


KELLY_H = 1.7          # Kho nhân vật 23 KELLY: profile.height_m = 1.7
YEUNU_H = 1.7          # nhân vật #24 30/31 không ghi chiều cao → mặc định, báo người dùng
WELL_H = round(sg.HIP * YEUNU_H, 2)   # Kho 420 "GIẾNG ĐÁ CỔ": "cao ngang hông" → 0,53 × 1,7 = 0,90 m
WELL_D = 1.5           # ảnh Kho 1127 (gieng_da_sach): bề ngang / chiều cao thành ≈ 1,7 → 1,7 × 0,9 ≈ 1,5 m; tám cạnh
WELL_SRC = "Kho 420 + ảnh 1127: cao ngang hông (0,53·1,7 = 0,90 m), rộng ≈ 1,7 × cao ≈ 1,5 m, tám cạnh"


def build_cfg(m3, spot, out, facing, well_dist, yeunu_in_well=False):
    """#24 thử: Kelly đứng ở O nhìn `facing` về giếng (trục Kelly→giếng), giếng trước mặt, yêu nữ bên kia giếng nhìn Kelly.
    `yeunu_in_well`: yêu nữ đứng ở TÂM giếng (bò lên), ngực ngang miệng giếng, giếng thành vành + lòng rỗng."""
    kelly = (0.0, 0.0, 0.0)
    well = sg.offset(kelly, facing, well_dist)
    woman = (well[0], well[1], 0.0) if yeunu_in_well else sg.offset(well, facing, 1.2)   # bên kia miệng giếng / trong giếng, nhìn Kelly
    foot = sg.in_well_foot_z(WELL_H, YEUNU_H) if yeunu_in_well else 0.0
    right = (facing + 90) % 360                               # phía máy theo sơ đồ G0 (#24: Đông của trục)
    # (a) toàn cảnh ngang tầm mắt sau lưng-chéo Kelly, phía phải trục, nhìn về giếng/tháp, ngửa nhẹ cho tháp vào khung
    cam_a = sg.offset(sg.offset(kelly, (facing + 180) % 360, 7.0), right, 2.0, dz=1.6)
    aim_a = sg.offset(kelly, facing, 10.0, dz=1.6 + 10.0 * math.tan(math.radians(14)) + 7.0 * math.tan(math.radians(14)))
    # (b) máy cao cúi nhìn miệng giếng (như shot 2 #24): phía phải trục, cao 3,4 m, cách tâm giếng 2,4 m
    # mục 5: T = giữa ngực Kelly và miệng giếng; α = phía phải trục, chếch về sau Kelly; khung dọc chứa 4 m; cao = mắt + 1 m
    t_b = ((kelly[0] + well[0]) / 2, (kelly[1] + well[1]) / 2, (sg.CHEST * KELLY_H + WELL_H) / 2)
    cam_b = sg.camera_at(t_b, (facing + 125) % 360, sg.frame_distance(4.0, 24, 9 / 16), sg.EYE * KELLY_H + 1.0)
    aim_b = t_b
    hk, hy = KELLY_H, YEUNU_H
    targets = {"kelly_chan": [*kelly[:2], 0.0], "kelly_hong": [*kelly[:2], sg.HIP * hk], "kelly_nguc": [*kelly[:2], sg.CHEST * hk],
               "kelly_mat": [*kelly[:2], sg.EYE * hk], "kelly_dinh": [*kelly[:2], hk],
               "gieng_tam": [well[0], well[1], WELL_H], "yeunu_chan": [woman[0], woman[1], foot],
               "yeunu_hong": [woman[0], woman[1], foot + sg.HIP * hy], "yeunu_mat": [woman[0], woman[1], foot + sg.EYE * hy]}
    yeunu = {"name": "YEUNU", "kind": "person", "at": list(woman[:2]), "height": YEUNU_H, "source": "chưa có trong hồ sơ — mặc định 1,7 m",
             "facing": (facing + 180) % 360, "rgb": [0.85, 0.05, 0.1]}
    if yeunu_in_well:
        yeunu["in_well"] = {"foot_z": foot, "rule": "chân = cao giếng − 0,72·H (ngực ngang miệng giếng, đầu + vai nhô lên)"}
    return {"model": m3["path"], "out_dir": out, "real_height_m": m3.get("real_height_m"), "origin_model": spot["at"],
            "anchor_model": m3["anchor"], "cell_m": 1.0, "cols": 20, "rows": 20, "acting_area": {"half_m": 3.0, "extra": [[well[0], well[1], 2.0]]}, "engine": "auto", "samples": 16,
            "top_view": {"centre": [0.0, 5.5], "size_m": 42.0, "px": 1260},
            "props": [{"name": "WELL", "kind": "well", "at": list(well[:2]), "radius": WELL_D / 2, "height": WELL_H, "sides": 8,
                       "source": WELL_SRC, "hollow": bool(yeunu_in_well)},
                      {"name": "KELLY", "kind": "person", "at": [0.0, 0.0], "height": KELLY_H, "source": "Kho nhân vật 23 KELLY height_m", "facing": facing, "rgb": [1.0, 0.45, 0.05]},
                      yeunu],
            "axis": [list(kelly), [well[0], well[1], 0.0]], "targets": targets,
            "cameras": [{"name": "try_wide", "file": "try_wide.png", "at": [round(v, 3) for v in cam_a], "aim": [round(v, 3) for v in aim_a],
                         "lens": 24, "res": [576, 1024], "rays": [36, 64]},
                        {"name": "try_down", "file": "try_down.png", "at": [round(v, 3) for v in cam_b], "aim": [round(v, 3) for v in aim_b],
                         "lens": 24, "res": [576, 1024], "rays": [36, 64]}]}


def draw_top(out, cams=None, fn="topgrid.png"):
    """topgrid.png: ảnh trực giao + lưới 1 m + nhãn ô, tô màu ô khác sàn, gốc O, mũi tên Bắc, tháp, giếng, người.
    `cams` = [(tên, {xyz, yaw_deg, fov_h_v_deg, cell})] — mặc định các máy thử trong frames.json; mỗi máy vẽ hình nón nhìn."""
    from PIL import Image, ImageDraw, ImageFont
    st = json.load(open(os.path.join(out, "stage.json"), encoding="utf-8"))
    grid = json.load(open(os.path.join(out, "grid.json"), encoding="utf-8"))
    tv = st["top_view"]
    px, size, cx, cy = tv["px"], tv["size_m"], tv["centre"][0], tv["centre"][1]
    s = px / size
    raw = os.path.join(out, "top_raw.png")
    img = Image.open(raw).convert("RGBA") if os.path.exists(raw) else Image.new("RGBA", (px, px), (40, 40, 40, 255))

    def P(x, y):
        return (x - cx) * s + px / 2, px / 2 - (y - cy) * s
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ov.load and ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype("arial.ttf", 11)
        big = ImageFont.truetype("arialbd.ttf", 18)
    except OSError:
        font = big = ImageFont.load_default()
    cm = st["cell_m"]
    tint = {"step": (255, 200, 0, 90), "level": (255, 40, 40, 110), "none": (0, 0, 0, 140)}
    for c in grid["cells"]:
        x0, y0 = P(c["x"] - cm / 2, c["y"] + cm / 2)
        x1, y1 = P(c["x"] + cm / 2, c["y"] - cm / 2)
        col = tint.get(c.get("status"))
        if c.get("obstacle"):
            col = (255, 120, 0, 120)
        if c.get("covered"):
            col = (120, 0, 200, 90)
        if col:
            d.rectangle([x0, y0, x1, y1], fill=col)
        if c.get("inner_step"):
            d.line([x0, y0, x1, y1], fill=(255, 200, 0, 200), width=1)
    hx, hy = st["cols"] * cm / 2, st["rows"] * cm / 2
    sub = cm / 4                                          # lưới phụ 0,25 m kẻ mờ, không tên (mục 2.3b)
    for i in range(int(st["cols"] * 4) + 1):
        x = -hx + i * sub
        d.line([P(x, -hy), P(x, hy)], fill=(255, 255, 255, 40), width=1)
    for j in range(int(st["rows"] * 4) + 1):
        y = -hy + j * sub
        d.line([P(-hx, y), P(hx, y)], fill=(255, 255, 255, 40), width=1)
    for i in range(st["cols"] + 1):
        x = -hx + i * cm
        d.line([P(x, -hy), P(x, hy)], fill=(255, 255, 255, 150), width=1)
    for j in range(st["rows"] + 1):
        y = -hy + j * cm
        d.line([P(-hx, y), P(hx, y)], fill=(255, 255, 255, 150), width=1)
    for c in grid["cells"]:
        x, y = P(c["x"] - cm / 2 + 0.05, c["y"] + cm / 2 - 0.05)
        d.text((x + 1, y + 1), c["cell"], fill=(0, 0, 0, 255), font=font)
        d.text((x, y), c["cell"], fill=(255, 255, 255, 255), font=font)
    ox, oy = P(0, 0)
    d.ellipse([ox - 6, oy - 6, ox + 6, oy + 6], outline=(255, 0, 255, 255), width=3)
    d.text((ox + 8, oy + 4), "O", fill=(255, 0, 255, 255), font=big)
    for k, pl in st.get("placed", {}).items():
        x, y = P(pl["xyz"][0], pl["xyz"][1])
        r = (pl.get("radius_m") or 0.25) * s
        d.ellipse([x - r, y - r, x + r, y + r], outline=(0, 160, 255, 255) if pl["kind"] == "well" else (255, 80, 0, 255), width=3)
        if pl.get("facing_deg") is not None:
            fa = math.radians(pl["facing_deg"])
            d.line([x, y, x + math.sin(fa) * 30, y - math.cos(fa) * 30], fill=(255, 80, 0, 255), width=3)
        d.text((x + r + 3, y - 9), f"{k} {pl['cell']}", fill=(255, 255, 255, 255), font=big)
    tw = st.get("marks", {}).get("thap_chan")
    if tw:
        x, y = P(tw["xyz"][0], tw["xyz"][1])
        d.rectangle([x - 8, y - 8, x + 8, y + 8], outline=(255, 30, 30, 255), width=3)
        d.text((x + 10, y - 9), f"THÁP (O→{tw['dist_m']} m, {tw['bearing_deg']}°)", fill=(255, 60, 60, 255), font=big)
    if cams is None:
        cams = [(n, fr["checks"]["camera"]) for n, fr in (json.load(open(os.path.join(out, "frames.json"), encoding="utf-8")) or {}).items()]
    for name, cam in cams:
        x, y = P(cam["xyz"][0], cam["xyz"][1])
        a = math.radians(cam["yaw_deg"])
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(0, 255, 0, 255))
        half = math.radians((cam.get("fov_h_v_deg") or [60, 0])[0] / 2)       # hình nón nhìn (FOV ngang) trên mặt sàn
        reach = 8 * s
        cone = [(x, y)] + [(x + math.sin(a + t) * reach, y - math.cos(a + t) * reach) for t in (-half, half)]
        d.polygon(cone, fill=(0, 255, 0, 22), outline=(0, 255, 0, 230))
        d.text((x + 7, y + 3), f"máy {name} {cam['cell']}", fill=(0, 255, 0, 255), font=big)
    ax_ = st.get("axis")
    if ax_:
        d.line([P(*ax_[0][:2]), P(*ax_[1][:2])], fill=(255, 255, 0, 255), width=2)
    d.polygon([(px - 40, 20), (px - 50, 50), (px - 30, 50)], fill=(255, 255, 255, 255))
    d.text((px - 46, 52), "B", fill=(255, 255, 255, 255), font=big)
    d.text((10, px - 26), "Cột A→T: Tây→Đông · Hàng 1→20: Nam→Bắc · ô 1 m (phụ 0,25 m) · vàng = bậc, đỏ = tầng khác, cam = vật chắn, tím = có mái che",
           fill=(255, 255, 255, 255), font=font)
    Image.alpha_composite(img, ov).convert("RGB").save(os.path.join(out, fn))


def draw_clay(out, name, letter):
    """view_<a|b>_clay.png: hình phác Workbench + nhãn (Kelly, Yêu nữ, Giếng, Tháp), lưới sàn 1 m chiếu từ số, một phần ba,
    đường chân trời w_h, vạch headroom, vùng thanh trên 15 %."""
    from PIL import Image, ImageDraw, ImageFont
    fr = json.load(open(os.path.join(out, "frames.json"), encoding="utf-8")).get(name)
    if not fr or not fr["checks"].get("clay"):
        return
    st = json.load(open(os.path.join(out, "stage.json"), encoding="utf-8"))
    chk, cam = fr["checks"], fr["checks"]["camera"]
    img = Image.open(os.path.join(out, chk["clay"]["file"])).convert("RGBA")
    W, H = img.size
    aspect = W / H
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    try:
        font, big = ImageFont.truetype("arial.ttf", 13), ImageFont.truetype("arialbd.ttf", 18)
    except OSError:
        font = big = ImageFont.load_default()
    C, A, f = cam["at"], cam["aim"], cam["lens_mm"]

    def uv(p):
        r = sg.project(C, A, p, f, aspect)
        return None if r is None or r[2] < 0.3 else (r[0] * W, r[1] * H)
    hx = st["cols"] * st["cell_m"] / 2
    for k in range(-int(hx), int(hx) + 1):                       # lưới sàn 1 m (z = 0)
        for line in (((k, -hx), (k, hx)), ((-hx, k), (hx, k))):
            pts = [uv((line[0][0] + (line[1][0] - line[0][0]) * t / 40, line[0][1] + (line[1][1] - line[0][1]) * t / 40, 0.0))
                   for t in range(41)]
            for p0, p1 in zip(pts, pts[1:]):
                if p0 and p1 and max(abs(p0[0]), abs(p1[0])) < 4 * W and max(abs(p0[1]), abs(p1[1])) < 4 * H:
                    d.line([p0, p1], fill=(40, 40, 40, 90 if k else 200), width=1 if k else 2)
    d.rectangle([0, 0, W, H * 0.15], fill=(255, 0, 0, 40))
    d.text((6, H * 0.15 - 18), "vùng thanh trên 15 %", fill=(160, 0, 0, 255), font=font)
    for t in (1 / 3, 2 / 3):
        d.line([(W * t, 0), (W * t, H)], fill=(255, 255, 255, 160), width=1)
        d.line([(0, H * t), (W, H * t)], fill=(255, 255, 255, 160), width=1)
    wh = chk["horizon_w"]
    if 0 <= wh <= 1:
        d.line([(0, wh * H), (W, wh * H)], fill=(0, 120, 255, 230), width=2)
    d.text((6, min(max(wh, 0), 0.97) * H + 2), f"chân trời w_h = {wh:.3f}" + ("" if 0 <= wh <= 1 else " (ngoài khung)"),
           fill=(0, 80, 220, 255), font=font)
    t = chk["targets"]
    head = t.get("kelly_dinh")
    if head and head["uv"]:
        y = head["uv"][1] * H
        d.line([(W * 0.05, y), (W * 0.95, y)], fill=(255, 140, 0, 230), width=2)
        d.text((W * 0.55, y - 16), f"headroom Kelly {head['uv'][1] * 100:.1f}%", fill=(200, 90, 0, 255), font=font)
    labels = {}
    for key, label, _own in LABEL_POINTS:
        v = t.get(key)
        if not v:
            continue
        p = st.get("marks", {}).get(key, {}).get("xyz") if key.startswith("thap") else (cfg_targets(out) or {}).get(key)
        if p is None:
            continue
        b = (v.get("blocked_by") or {}).get("object")
        labels[key] = dict(sg.point_state(C, A, p, f, aspect, blocked_by=b), label=label)
    draw_labels(d, W, H, labels, big)
    d.text((6, H - 40), f"máy {name}: ô {cam['cell']}, cao {cam['z_above_stage_m']} m, pitch {cam['pitch_deg']}°, f {f} mm",
           fill=(0, 0, 0, 255), font=font)
    d.text((6, H - 22), f"clay render {chk['clay']['render_sec']} s", fill=(0, 0, 0, 255), font=font)
    Image.alpha_composite(img, ov).convert("RGB").save(os.path.join(out, f"view_{letter}_clay.png"))


def cfg_targets(out):
    try:
        return json.load(open(os.path.join(out, "cfg.json"), encoding="utf-8")).get("targets")
    except OSError:
        return None


def draw_labels(d, W, H, labels, font):
    """Nhãn hình phác theo sg.point_state (người dùng 09/10): trong khung = chấm đặc; bị che = chấm rỗng "(bị che bởi …)";
    ngoài khung = KHÔNG chấm, mũi tên xám sát mép chỉ hướng vật + "… ngoài khung"; sau lưng máy = không vẽ (chỉ ở bảng)."""
    for key, v in labels.items():
        stt = v["state"]
        if stt == "behind":
            continue
        if stt in ("in", "blocked"):
            x, y = v["uv"][0] * W, v["uv"][1] * H
            if stt == "in":
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(0, 0, 0, 255))
                txt = v["label"]
            else:
                d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(0, 0, 0, 255), width=2)
                txt = f"{v['label']} (bị che bởi {str(v['blocked_by'])[:28]})"
            tx = min(max(x + 8, 4), W - 8 * len(txt) - 4) if x + 8 * len(txt) > W else x + 8
            d.text((tx, y - 22), txt, fill=(0, 0, 0, 255), font=font)
            continue
        ax, ay = v["arrow"][0] * W, v["arrow"][1] * H              # ngoài khung: mũi tên xám sát mép
        du, dv = v["uv"][0] - 0.5, v["uv"][1] - 0.5
        n = math.hypot(du * W, dv * H) or 1.0
        ux, uy = du * W / n, dv * H / n
        tail = (ax - ux * 34, ay - uy * 34)
        grey = (90, 90, 90, 255)
        d.line([tail, (ax, ay)], fill=grey, width=4)
        d.polygon([(ax + ux * 6, ay + uy * 6), (ax - ux * 10 - uy * 8, ay - uy * 10 + ux * 8),
                   (ax - ux * 10 + uy * 8, ay - uy * 10 - ux * 8)], fill=grey)
        txt = f"{v['label']} ngoài khung"
        tw = 8 * len(txt)
        tx = min(max(tail[0] - tw / 2, 4), W - tw - 4)
        ty = min(max(tail[1] + (-26 if uy > 0 else 8), 4), H - 24)
        d.text((tx, ty), txt, fill=(70, 70, 70, 255), font=font)


def report(out):
    st = json.load(open(os.path.join(out, "stage.json"), encoding="utf-8"))
    grid = json.load(open(os.path.join(out, "grid.json"), encoding="utf-8"))["cells"]
    fr = json.load(open(os.path.join(out, "frames.json"), encoding="utf-8"))
    cnt = {}
    for c in grid:
        cnt[c.get("status")] = cnt.get(c.get("status"), 0) + 1
    print("O model", st["origin_model"], "scene", st["origin_scene"], "trên", st["origin_on"], "dốc", st["slope_deg"])
    print("ô:", cnt, "có mái:", sum(1 for c in grid if c.get("covered")), "bậc trong ô:", sum(1 for c in grid if c.get("inner_step")))
    for k, v in list(st["marks"].items()) + list(st["placed"].items()):
        print(f"  {k:12s} {v}")
    for n, f in fr.items():
        print(n, f["percent"], "gần nhất", f["nearest_hit"], "vật rắn gần nhất", f["nearest_solid"])
        print("   máy", f["checks"]["camera"])
        print("   phía trục", f["checks"]["axis_side"], "góc máy-Kelly-tháp", f["checks"].get("angle_cam_kelly_tower_deg"),
              {k: v for k, v in f["checks"].items() if k not in ("camera", "targets", "axis_side", "angle_cam_kelly_tower_deg")})
        for t, v in f["checks"]["targets"].items():
            print(f"     {t:10s} {v}")


if __name__ == "__main__":
    if IN_BLENDER:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        with open(argv[argv.index("--config") + 1], encoding="utf-8") as fh:
            blender_main(json.load(fh))
    else:
        host_main()
