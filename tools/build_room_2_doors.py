"""Phòng 2 cánh cửa (tập 2 dự án #31, cảnh 1 + 5) — căn phòng cũ ma ám theo key visual Playbook OB55, dựng bằng Blender (0 USD).

Chạy:  blender -b --factory-startup -P tools/build_room_2_doors.py -- <thư mục ra>
       (Blender bản Store: qua core.plates3d._run_in_store — xem tools/preview_room_2_doors.py)
Ra 3 file .glb CÙNG hệ tọa độ, CÙNG SPOTS, chỉ khác góc mở cửa (+ ánh tím–đỏ sau cửa 1 ở B/C):
  phong_2_cua_A_dong.glb      (A) cả hai cửa đóng — cảnh 1
  phong_2_cua_B_cua1_mo.glb   (B) cửa 1 mở (sau cửa ánh tím–đỏ thế giới song song), cửa 2 đóng — đầu cảnh 5
  phong_2_cua_C_ca_hai_mo.glb (C) cửa 1 + cửa 2 mở — cuối cảnh 5
Hệ tọa độ (mét, Z lên, +Y = bắc = "tường sau"): phòng X 0..5, Y 0..4.5, cao 2.6, tường dày 0.12 (ra phía ngoài).
Cửa 1 ở tường TÂY (trái, x=0) y 2.9..3.8; cửa 2 ở tường BẮC (sau, lệch phải, y=4.5) x 3.0..3.9; cao 2.05. Bản lề ở mép `hinge`
(gốc tọa độ của object cửa = trục bản lề) — cửa mở ra PHÍA NGOÀI (vào hành lang) nên không vướng người trong phòng.
Không vẽ số 1/2 lên cửa (ghép hậu kỳ), không mặt nạ, không chữ REC/giờ.
`SPOTS` theo quy ước core/plate_camera.camera_for: `at` = chân nhân vật, `facing` = độ theo chiều kim đồng hồ từ +y (0 = +y, 90 = +x),
máy đứng TRƯỚC mặt nhân vật; `view` = thứ ở nền sau lưng nhân vật.
"""
import math
import os
import sys

W, D, H = 5.0, 4.5, 2.6          # phòng
T = 0.12                         # tường
DOOR_W, DOOR_H, DOOR_T = 0.9, 2.05, 0.045
DOORS = {
    # wall: west (x=0, chạy theo y) | north (y=D, chạy theo x); lo..hi = khoảng lối đi trên tường; hinge = đầu có bản lề
    # 2 lối đi gần góc tây-bắc (cách nhau ~1,5 m) để một khung dọc 9:16 thấy CẢ hai (POV 16 mm, Kelly WS 24 mm)
    # bản lề phía nam: mở ~45° cánh gần song song tia nhìn của máy POV (góc đông-nam) — thấy cánh hé xiên + ánh tím trong lối
    # (bản lề phía bắc thì cánh mở che kín lối, nhìn như vẫn đóng — đã thử 15/10)
    "cua_1": {"wall": "west", "lo": 3.3, "hi": 3.3 + DOOR_W, "hinge": "lo"},
    "cua_2": {"wall": "north", "lo": 2.5, "hi": 2.5 + DOOR_W, "hinge": "hi"},
}
# góc mở (ra phía hành lang). Cửa 1 mở 45°: từ góc POV thấy cánh hé chéo trong lối — đọc ra "cửa đã mở"
OPEN_DEG = {"cua_1": 45.0, "cua_2": 80.0}
STATES = {
    "A": {"file": "phong_2_cua_A_dong.glb", "open": {"cua_1": 0.0, "cua_2": 0.0}, "glow": False},
    "B": {"file": "phong_2_cua_B_cua1_mo.glb", "open": {"cua_1": OPEN_DEG["cua_1"], "cua_2": 0.0}, "glow": True},
    "C": {"file": "phong_2_cua_C_ca_hai_mo.glb", "open": dict(OPEN_DEG), "glow": True},
}
INDOOR = {"exposure": 0.2, "fill_w": 8, "fill_color": [0.62, 0.74, 1.0], "fill_up_m": 0.3}   # sáng lạnh yếu cho máy trong phòng
POV_EYE_M = 1.55
SPOTS = {
    "goc_nhin_kelly_2_cua": {
        "at": [4.6, 0.45, 0.0], "facing": 323.0, "view": [1.6, 4.3, 1.05], "group": "phong_2_cua",
        "label": "góc nhìn thứ nhất Kelly — thấy CẢ 2 cửa (cửa 1 tường trái, cửa 2 tường sau lệch phải); máy tại 'at' cao mắt "
                 "1,55 m nhìn về 'view', ống 20 mm khung dọc 9:16 (hai lối lệch ±21°, khung ±27°)"},
    "kelly_giua_phong": {
        "at": [3.4, 2.1, 0.0], "facing": 144.0, "view": [1.2, 4.4, 1.2], "group": "phong_2_cua",
        "label": "Kelly giữa phòng trên tấm thảm — máy trước mặt cô, 2 cửa ở nền sau lưng (cỡ WS thấy cả 2 cửa; MS/MLS chỉ "
                 "thấy 1 cửa + góc phòng)"},
    "can_cua_1": {
        "at": [0.95, 3.75, 0.0], "facing": 90.0, "view": [0.0, 3.75, 1.1], "group": "phong_2_cua",
        "label": "cận cửa 1 (tường trái) — Kelly đứng trước cửa 1, máy đi vào cửa"},
    "can_cua_2": {
        "at": [2.95, 3.45, 0.0], "facing": 180.0, "view": [2.95, 4.5, 1.1], "group": "phong_2_cua",
        "label": "cận cửa 2 (tường sau, lệch phải) — Kelly đứng trước cửa 2, máy đi vào cửa"},
}
DEFAULT_SPOT = "goc_nhin_kelly_2_cua"
# đồ đạc chiếm sàn (x0, x1, y0, y1) — chỗ đứng không được nằm trong
FURNITURE = {"ke_sach": (0.6, 1.5, D - 0.36, D), "sofa": (4.05, W, 2.35, 4.25), "ban_den": (0.05, 0.5, 2.45, 2.9)}
NOTES = ("Mô hình procedural (tools/build_room_2_doors.py, không Meshy), mét, phòng 5x4,5x2,6 — căn phòng cũ ma ám key visual OB55: giấy "
         "dán tường lục giác xám-xanh, nẹp trắng ngà, sàn gỗ tối + thảm, dây cờ đỏ-xanh, kệ sách + TV CRT, bóng bay, sofa, đèn bàn ấm "
         "yếu. Cửa 1 tường trái (tây), cửa 2 tường sau lệch phải (bắc); bản lề thật, mở ra hành lang. 3 trạng thái = 3 file cùng hệ "
         "tọa độ + cùng SPOTS: A cả hai đóng (cảnh 1, mặc định), B cửa 1 mở + ánh tím-đỏ (đầu cảnh 5), C cả hai mở (cuối cảnh 5). "
         "Số 1/2 trên cửa ghép hậu kỳ. Phòng tối: đèn bàn chụp vải ấm cạnh cửa 1 (tường trái) là nguồn ấm duy nhất — shot đêm nên "
         "có practical_lights lamp warm phía trái/sau.")


def door_opening(name):
    """(x0, x1, y0, y1) của lối đi trong thân tường."""
    d = DOORS[name]
    if d["wall"] == "west":
        return (-T, 0.0, d["lo"], d["hi"])
    return (d["lo"], d["hi"], D, D + T)


def hinge_point(name):
    """Trục bản lề (x, y) — giữa bề dày tường, ở mép `hinge` của lối đi (lùi 0.02 cho khung)."""
    d = DOORS[name]
    off = 0.02 + DOOR_T / 2 + 0.003                       # ốp lòng 0.02 + nửa bề dày cánh: cánh mở không cắt vào tường
    edge = d[d["hinge"]] + (-off if d["hinge"] == "hi" else off)
    return (-T / 2, edge) if d["wall"] == "west" else (edge, D + T / 2)


def door_yaws(name):
    """(góc quay Z khi đóng, khi mở 90°) của object cửa. Cánh dựng ở hệ cục bộ chạy theo -X từ bản lề: hướng cánh = (-cos θ, -sin θ)."""
    d = DOORS[name]
    sign = 1.0 if d["hinge"] == "lo" else -1.0            # cánh đóng chạy từ bản lề về đầu kia của lối
    closed_dir = (0.0, sign) if d["wall"] == "west" else (sign, 0.0)
    out_dir = (-1.0, 0.0) if d["wall"] == "west" else (0.0, 1.0)   # ra phía hành lang
    closed = math.degrees(math.atan2(-closed_dir[1], -closed_dir[0]))
    opened = math.degrees(math.atan2(-out_dir[1], -out_dir[0]))
    opened = closed + ((opened - closed + 180) % 360 - 180)
    return closed, opened


def leaf_tip(name, deg):
    """(x, y) mép tự do của cánh khi mở `deg` độ — để kiểm cánh không quét vào trong phòng."""
    closed, opened = door_yaws(name)
    th = math.radians(closed + (opened - closed) * deg / 90.0)
    hx, hy = hinge_point(name)
    dw = DOOR_W - 0.07
    return hx - dw * math.cos(th), hy - dw * math.sin(th)


def door_problems():
    """Cửa phải nằm trọn trong tường (chừa ≥ 0.15 m mỗi bên cho nẹp), thấp hơn trần, hai cửa không chồng nhau."""
    out = []
    for name, d in DOORS.items():
        length = D if d["wall"] == "west" else W
        if not (0.15 <= d["lo"] < d["hi"] <= length - 0.15):
            out.append(f"{name}: lối {d['lo']}..{d['hi']} ra ngoài tường dài {length}")
        if abs((d["hi"] - d["lo"]) - DOOR_W) > 1e-6:
            out.append(f"{name}: lối rộng {d['hi'] - d['lo']:.2f} ≠ cánh {DOOR_W}")
    if DOOR_H > H - 0.2:
        out.append("cửa cao sát trần")
    return out


def spot_problems():
    out = []
    for name, sp in SPOTS.items():
        x, y, _ = sp["at"]
        if not (0.3 <= x <= W - 0.3 and 0.3 <= y <= D - 0.3):
            out.append(f"{name}: chân ngoài phòng / sát tường")
        for f, (x0, x1, y0, y1) in FURNITURE.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                out.append(f"{name}: đứng trong {f}")
        if not sp.get("label") or len(sp.get("view") or []) != 3:
            out.append(f"{name}: thiếu label/view")
    return out


def _bearing(frm, to):
    return math.degrees(math.atan2(to[0] - frm[0], to[1] - frm[1]))


def pov_span(spot="goc_nhin_kelly_2_cua"):
    """(độ lệch trái nhất, phải nhất) của 4 mép 2 lối đi so với hướng nhìn của máy POV — khung phải chứa cả hai."""
    sp = SPOTS[spot]
    cam = sp["at"][:2]
    centre = _bearing(cam, sp["view"])
    edges = []
    for name in DOORS:
        x0, x1, y0, y1 = door_opening(name)
        pts = [(0.0, y0), (0.0, y1)] if DOORS[name]["wall"] == "west" else [(x0, D), (x1, D)]
        edges += [((_bearing(cam, p) - centre + 180) % 360) - 180 for p in pts]
    return min(edges), max(edges)


def hfov_deg(lens_mm, aspect=9 / 16, sensor=36.0):
    """Góc ngang của khung dọc (Blender sensor fit AUTO: 36 mm theo cạnh dài = chiều cao)."""
    return math.degrees(2 * math.atan(sensor * aspect / 2 / lens_mm))


# ---- Blender ------------------------------------------------------------------------------------------------------------------
def main(out_dir):
    import bpy
    import numpy as np
    from mathutils import Vector
    os.makedirs(out_dir, exist_ok=True)
    tex_dir = os.path.join(out_dir, "tex")
    os.makedirs(tex_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(7)
    mats = {}

    def image(name, arr):
        h, w, _ = arr.shape
        img = bpy.data.images.new(name, w, h, alpha=False)
        rgba = np.concatenate([np.clip(arr, 0, 1), np.ones((h, w, 1))], axis=2).astype(np.float32)
        img.pixels.foreach_set(rgba.ravel())
        img.filepath_raw = os.path.join(tex_dir, name + ".png")
        img.file_format = "PNG"
        img.save()
        return img

    def mat(name, rgb, rough=0.6, metal=0.0, emit=0.0, img=None):
        if name not in mats:
            m = bpy.data.materials.new(name)
            m.use_nodes = True
            b = m.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = (*rgb, 1)
            b.inputs["Roughness"].default_value = rough
            b.inputs["Metallic"].default_value = metal
            if img is not None:
                t = m.node_tree.nodes.new("ShaderNodeTexImage")
                t.image = img
                m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
            if emit:
                b.inputs["Emission Color"].default_value = (*rgb, 1)
                b.inputs["Emission Strength"].default_value = emit
            mats[name] = m
        return mats[name]

    def world_uv(o, su, sv, off=(0.0, 0.0, 0.0)):
        """UV theo tọa độ thế giới (mét / kích thước ô ảnh) — hoa văn đúng tỉ lệ thật trên mọi mặt."""
        me = o.data
        uv = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
        mw = o.matrix_world
        for p in me.polygons:
            n = p.normal
            for li in p.loop_indices:
                co = mw @ me.vertices[me.loops[li].vertex_index].co - Vector(off)
                if abs(n.x) >= max(abs(n.y), abs(n.z)):
                    u, v = co.y, co.z
                elif abs(n.y) >= abs(n.z):
                    u, v = co.x, co.z
                else:
                    u, v = co.x, co.y
                uv.data[li].uv = (u / su, v / sv)

    def box(name, x0, x1, y0, y1, z0, z1, m, uv=None):
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        o = bpy.context.active_object
        o.name = name
        o.scale = (x1 - x0, y1 - y0, z1 - z0)
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(m)
        if uv:
            world_uv(o, *uv)
        return o

    def cyl(name, x, y, z0, z1, r, m, verts=24, r2=None):
        if r2 is None:
            bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=z1 - z0, location=(x, y, (z0 + z1) / 2))
        else:
            bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=z1 - z0, location=(x, y, (z0 + z1) / 2),
                                            end_fill_type="NOTHING")      # chụp đèn hở hai đầu: đèn shot đặt trong chụp hắt sáng ra
        o = bpy.context.active_object
        o.name = name
        o.data.materials.append(m)
        return o

    def ball(name, loc, r, m, sz=1.0):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=14, radius=r, location=loc)
        o = bpy.context.active_object
        o.name = name
        o.scale = (1, 1, sz)
        bpy.ops.object.transform_apply(scale=True)
        bpy.ops.object.shade_smooth()
        o.data.materials.append(m)
        return o

    def rod(name, p0, p1, r, m):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=d.length, location=(p0 + p1) / 2)
        o = bpy.context.active_object
        o.name = name
        o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        bpy.ops.object.transform_apply(rotation=True)
        o.data.materials.append(m)
        return o

    def tri(name, pts, m):
        me = bpy.data.meshes.new(name)
        me.from_pydata(pts, [], [(0, 1, 2)])
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        o.data.materials.append(m)
        return o

    # ---- ảnh hoa văn (tile được) ----
    def tile_noise(h, w, k=6, amp=1.0):
        yy, xx = np.mgrid[0:h, 0:w]
        out = np.zeros((h, w))
        for _ in range(k):
            fx, fy = rng.integers(1, 5, 2)
            ph = rng.uniform(0, 6.28)
            out += np.sin(2 * np.pi * (fx * xx / w + fy * yy / h) + ph)
        return out / k * amp

    def hex_wallpaper(wpx=256):
        hpx = int(round(wpx * math.sqrt(3)))
        yy, xx = np.mgrid[0:hpx, 0:wpx]
        x = (xx + 0.5) / wpx
        y = (yy + 0.5) / hpx * math.sqrt(3)
        best = np.full(x.shape, 9.0)
        s3 = math.sqrt(3)
        for cx, cy in ((0, 0), (1, 0), (0, s3), (1, s3), (0.5, s3 / 2)):
            dx, dy = x - cx, y - cy
            d = np.maximum(np.abs(dx), np.maximum(np.abs(0.5 * dx + s3 / 2 * dy), np.abs(-0.5 * dx + s3 / 2 * dy)))
            best = np.minimum(best, d)
        base = np.array([0.40, 0.42, 0.37])
        ring = np.array([0.25, 0.27, 0.24])
        inner = np.array([0.29, 0.31, 0.28])
        img = np.ones((hpx, wpx, 3)) * base
        img[(best > 0.33) & (best < 0.43)] = ring
        img[(best > 0.13) & (best < 0.19)] = ring * 1.1
        img[best <= 0.13] = inner
        grime = 1.0 + tile_noise(hpx, wpx, 8, 0.10) + rng.normal(0, 0.025, (hpx, wpx))
        return (img * grime[..., None])[::-1]

    def wood_floor(px=512, rows=10, tile_m=1.2):
        yy, xx = np.mgrid[0:px, 0:px]
        row = (yy * rows // px)
        tone = rng.uniform(0.75, 1.15, rows)[row]
        joint = rng.uniform(0, 1, rows)[row]
        u = xx / px
        grain = 1 + 0.12 * np.sin(2 * np.pi * (yy / px * rows * 7 + 0.6 * np.sin(2 * np.pi * (u * 3 + joint))))
        img = np.ones((px, px, 3)) * np.array([0.30, 0.20, 0.13])
        img *= (tone * grain)[..., None]
        gap = ((yy % (px // rows)) < 2) | (np.abs(((u - joint) % 1.0)) < 0.004)
        img[gap] *= 0.35
        img *= (1 + tile_noise(px, px, 6, 0.08) + rng.normal(0, 0.03, (px, px)))[..., None]
        return img

    def rug(wpx=384, hpx=256):
        yy, xx = np.mgrid[0:hpx, 0:wpx]
        bx = np.minimum(xx, wpx - 1 - xx) / wpx
        by = np.minimum(yy, hpx - 1 - yy) / hpx
        b = np.minimum(bx * wpx, by * hpx)
        img = np.ones((hpx, wpx, 3)) * np.array([0.28, 0.13, 0.11])
        img[(b > 14) & (b < 22)] = [0.47, 0.40, 0.30]
        img[(b > 28) & (b < 32)] = [0.17, 0.27, 0.30]
        cx, cy = (xx - wpx / 2) / wpx, (yy - hpx / 2) / hpx
        med = (np.abs(cx) + np.abs(cy) * 1.4) < 0.18
        img[med] = [0.18, 0.28, 0.31]
        img[(np.abs(cx) + np.abs(cy) * 1.4 < 0.10)] = [0.47, 0.40, 0.30]
        img *= (1 + rng.normal(0, 0.06, (hpx, wpx)) + tile_noise(hpx, wpx, 5, 0.1))[..., None]
        return img

    HEX_W = 0.24
    hex_uv = (HEX_W, HEX_W * math.sqrt(3))
    paper = mat("giay_dan_tuong", (1, 1, 1), 0.85, img=image("giay_luc_giac", hex_wallpaper()))
    floor = mat("san_go", (1, 1, 1), 0.55, img=image("san_go", wood_floor()))
    rugm = mat("tham", (1, 1, 1), 0.95, img=image("tham", rug()))
    trim = mat("nep_trang_nga", (0.52, 0.50, 0.43), 0.55)
    ceil = mat("tran", (0.16, 0.16, 0.15), 0.9)
    door_wood = mat("go_canh_cua", (0.20, 0.12, 0.07), 0.55)
    door_panel = mat("go_o_cua", (0.16, 0.095, 0.055), 0.5)
    brass = mat("dong_tay_nam", (0.55, 0.42, 0.20), 0.35, 0.9)
    iron = mat("sat_ban_le", (0.08, 0.08, 0.08), 0.5, 0.8)
    shelf_wood = mat("go_ke", (0.17, 0.10, 0.06), 0.6)
    tv_body = mat("vo_tv", (0.30, 0.29, 0.26), 0.5)
    tv_screen = mat("man_tv", (0.30, 0.42, 0.50), 0.15, emit=0.6)
    sofa_m = mat("sofa", (0.20, 0.11, 0.08), 0.95)
    sofa_c = mat("dem_sofa", (0.24, 0.14, 0.10), 0.95)
    red = mat("do", (0.50, 0.04, 0.05), 0.35)
    blue = mat("xanh_xam", (0.30, 0.40, 0.52), 0.35)
    navy = mat("xanh_dam", (0.12, 0.18, 0.30), 0.6)
    pale = mat("xanh_nhat", (0.55, 0.62, 0.66), 0.6)
    string_m = mat("day", (0.6, 0.6, 0.6), 0.8)
    shade = mat("chup_den", (1.0, 0.62, 0.30), 0.8, emit=2.5)
    bulb = mat("bong_den", (1.0, 0.75, 0.45), 0.3, emit=12.0)
    dark = mat("den", (0.02, 0.02, 0.025), 0.9)
    hall_wall = mat("tuong_hanh_lang", (0.06, 0.065, 0.065), 0.9)
    pic = mat("tranh", (0.10, 0.11, 0.12), 0.4)

    # ---- vỏ phòng ----
    box("san", -T, W + T, -T, D + T, -T, 0, floor, (1.2, 1.2))
    box("tran", -T, W + T, -T, D + T, H, H + T, ceil)
    box("tuong_dong", W, W + T, -T, D + T, 0, H, paper, hex_uv)
    box("tuong_nam", -T, W + T, -T, 0, 0, H, paper, hex_uv)
    (x0, x1, y0, y1) = door_opening("cua_1")
    box("tuong_tay_a", -T, 0, -T, y0, 0, H, paper, hex_uv)
    box("tuong_tay_b", -T, 0, y1, D + T, 0, H, paper, hex_uv)
    box("tuong_tay_tren", -T, 0, y0, y1, DOOR_H, H, paper, hex_uv)
    (x0, x1, y0, y1) = door_opening("cua_2")
    box("tuong_bac_a", -T, x0, D, D + T, 0, H, paper, hex_uv)
    box("tuong_bac_b", x1, W + T, D, D + T, 0, H, paper, hex_uv)
    box("tuong_bac_tren", x0, x1, D, D + T, DOOR_H, H, paper, hex_uv)
    # chân tường + phào trần (trắng ngà cũ), chừa lối đi
    for n, (a0, a1, b0, b1) in {"nam": (0, W, 0, 0.015), "dong": (W - 0.015, W, 0, D)}.items():
        box(f"chan_tuong_{n}", a0, a1, b0, b1, 0, 0.11, trim)
    for a0, a1 in ((0, DOORS["cua_1"]["lo"] - 0.08), (DOORS["cua_1"]["hi"] + 0.08, D)):
        box("chan_tuong_tay", 0, 0.015, a0, a1, 0, 0.11, trim)
    for a0, a1 in ((0, DOORS["cua_2"]["lo"] - 0.08), (DOORS["cua_2"]["hi"] + 0.08, W)):
        box("chan_tuong_bac", a0, a1, D - 0.015, D, 0, 0.11, trim)
    box("phao_nam", 0, W, 0, 0.05, H - 0.09, H, trim)
    box("phao_bac", 0, W, D - 0.05, D, H - 0.09, H, trim)
    box("phao_tay", 0, 0.05, 0, D, H - 0.09, H, trim)
    box("phao_dong", W - 0.05, W, 0, D, H - 0.09, H, trim)

    # ---- khung cửa (nẹp + ốp lòng) + hành lang sau lối đi ----
    C, P = 0.085, 0.02                                     # bản nẹp, nhô ra khỏi tường
    for name, d in DOORS.items():
        lo, hi = d["lo"], d["hi"]
        if d["wall"] == "west":
            box(f"{name}_nep_a", 0, P, lo - C, lo, 0, DOOR_H + C, trim)
            box(f"{name}_nep_b", 0, P, hi, hi + C, 0, DOOR_H + C, trim)
            box(f"{name}_nep_tren", 0, P, lo - C, hi + C, DOOR_H, DOOR_H + C, trim)
            box(f"{name}_long_a", -T, 0, lo, lo + 0.02, 0, DOOR_H, trim)
            box(f"{name}_long_b", -T, 0, hi - 0.02, hi, 0, DOOR_H, trim)
            box(f"{name}_long_tren", -T, 0, lo, hi, DOOR_H - 0.02, DOOR_H, trim)
            L = 4.0                                         # hành lang chạy về -x
            box(f"{name}_hl_san", -T - L, -T, lo - 0.2, hi + 0.2, -T, 0, floor, (1.2, 1.2))
            box(f"{name}_hl_tran", -T - L, -T, lo - 0.2, hi + 0.2, 2.35, 2.45, ceil)
            box(f"{name}_hl_tuong_a", -T - L, -T, lo - 0.3, lo - 0.2, 0, 2.45, hall_wall)
            box(f"{name}_hl_tuong_b", -T - L, -T, hi + 0.2, hi + 0.3, 0, 2.45, hall_wall)
            box(f"{name}_hl_cuoi", -T - L - 0.1, -T - L, lo - 0.3, hi + 0.3, 0, 2.45, hall_wall)
            box(f"{name}_hl_noi_tren", -T - 0.02, -T, lo - 0.2, hi + 0.2, DOOR_H, 2.45, hall_wall)
        else:
            box(f"{name}_nep_a", lo - C, lo, D - P, D, 0, DOOR_H + C, trim)
            box(f"{name}_nep_b", hi, hi + C, D - P, D, 0, DOOR_H + C, trim)
            box(f"{name}_nep_tren", lo - C, hi + C, D - P, D, DOOR_H, DOOR_H + C, trim)
            box(f"{name}_long_a", lo, lo + 0.02, D, D + T, 0, DOOR_H, trim)
            box(f"{name}_long_b", hi - 0.02, hi, D, D + T, 0, DOOR_H, trim)
            box(f"{name}_long_tren", lo, hi, D, D + T, DOOR_H - 0.02, DOOR_H, trim)
            L = 4.5                                         # hành lang chạy về +y, có dây đèn màu
            box(f"{name}_hl_san", lo - 0.2, hi + 0.2, D + T, D + T + L, -T, 0, floor, (1.2, 1.2))
            box(f"{name}_hl_tran", lo - 0.2, hi + 0.2, D + T, D + T + L, 2.35, 2.45, ceil)
            box(f"{name}_hl_tuong_a", lo - 0.3, lo - 0.2, D + T, D + T + L, 0, 2.45, hall_wall)
            box(f"{name}_hl_tuong_b", hi + 0.2, hi + 0.3, D + T, D + T + L, 0, 2.45, hall_wall)
            box(f"{name}_hl_cuoi", lo - 0.3, hi + 0.3, D + T + L, D + T + L + 0.1, 0, 2.45, hall_wall)
            box(f"{name}_hl_noi_tren", lo - 0.2, hi + 0.2, D + T, D + T + 0.02, DOOR_H, 2.45, hall_wall)
            cols = [(0.9, 0.1, 0.1), (0.1, 0.8, 0.2), (0.15, 0.3, 1.0), (1.0, 0.75, 0.1), (0.9, 0.2, 0.7)]
            for k in range(14):
                yk = D + T + 0.6 + k * 0.28
                for side, xx in (("a", lo - 0.15), ("b", hi + 0.15)):
                    c = cols[(k + (side == "b") * 2) % len(cols)]
                    ball(f"den_day_{side}_{k}", (xx, yk, 2.28 - 0.04 * math.sin(k * 1.3)), 0.022,
                         mat(f"den_mau_{cols.index(c)}", c, 0.4, emit=5.0))

    # ---- cánh cửa: gốc object = trục bản lề ----
    def make_door(name):
        d = DOORS[name]
        parts = []
        # dựng ở hệ cục bộ: bản lề tại gốc, cánh chạy theo -X (dài DOOR_W), dày theo Y
        dw = DOOR_W - 0.07                                 # chừa ốp lòng 2 bên + khe bản lề
        parts.append(box(f"{name}_canh", -dw, 0, -DOOR_T / 2, DOOR_T / 2, 0.01, DOOR_H - 0.01, door_wood))
        for sgn in (-1, 1):                                # ô cửa nổi hai mặt: 2 cột × 3 hàng
            yf = sgn * DOOR_T / 2
            ya, yb = (yf, yf + sgn * 0.012) if sgn > 0 else (yf + sgn * 0.012, yf)
            for (z0, z1) in ((0.12, 0.72), (0.84, 1.44), (1.56, 1.94)):
                for (u0, u1) in ((-dw + 0.10, -dw / 2 - 0.05), (-dw / 2 + 0.05, -0.10)):
                    parts.append(box(f"{name}_o", u0, u1, min(ya, yb), max(ya, yb), z0, z1, door_panel))
            yk = sgn * (DOOR_T / 2 + 0.012)
            parts.append(box(f"{name}_de_tay_nam", -dw + 0.04, -dw + 0.09, min(0, yk) - 0.006, max(0, yk) + 0.006, 0.86, 1.06, brass))
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.03, location=(-dw + 0.065, sgn * 0.075, 0.97))
            k = bpy.context.active_object
            k.data.materials.append(brass)
            parts.append(k)
        parts.append(box(f"{name}_co_tay_nam", -dw + 0.058, -dw + 0.072, -0.075, 0.075, 0.963, 0.977, brass))
        for z in (0.25, 1.0, 1.8):                         # 3 bản lề sắt ở mép bản lề
            parts.append(box(f"{name}_ban_le", -0.012, 0.012, -DOOR_T / 2 - 0.004, DOOR_T / 2 + 0.004, z, z + 0.1, iron))
        bpy.ops.object.select_all(action="DESELECT")
        for p in parts:
            p.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        o = bpy.context.active_object
        o.name = name
        bpy.context.scene.cursor.location = (0, 0, 0)       # gốc object = trục bản lề (đang ở gốc thế giới)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        # đặt vào tường: gốc (bản lề) về hinge_point; cánh đóng nằm dọc lối đi về phía `lo`
        hx, hy = hinge_point(name)
        o.location = (hx, hy, 0)
        closed, opened = door_yaws(name)
        o["closed_yaw_deg"], o["open_yaw_deg"] = closed, opened
        return o

    door_objs = {n: make_door(n) for n in DOORS}

    def set_open(name, deg):
        """deg 0 = đóng, 90 = mở vuông góc ra phía hành lang (quay quanh trục bản lề)."""
        closed, opened = door_yaws(name)
        o = door_objs[name]
        o.rotation_euler = (0, 0, math.radians(closed + (opened - closed) * deg / 90.0))

    # ---- đồ đạc ----
    # thảm giữa phòng
    rx0, rx1, ry0, ry1 = 1.2, 3.9, 1.2, 3.2
    rg = box("tham", rx0, rx1, ry0, ry1, 0, 0.012, rugm)
    world_uv(rg, rx1 - rx0, ry1 - ry0, (rx0, ry0, 0))
    # kệ sách sát tường sau + TV CRT
    kx0, kx1, ky0, ky1 = FURNITURE["ke_sach"]
    box("ke_hong_trai", kx0, kx0 + 0.03, ky0, ky1, 0, 1.8, shelf_wood)
    box("ke_hong_phai", kx1 - 0.03, kx1, ky0, ky1, 0, 1.8, shelf_wood)
    box("ke_lung", kx0, kx1, ky1 - 0.015, ky1, 0, 1.8, shelf_wood)
    shelves = (0.05, 0.45, 0.85, 1.3, 1.77)
    for i, z in enumerate(shelves):
        box(f"ke_tang_{i}", kx0, kx1, ky0, ky1, z, z + 0.03, shelf_wood)
    book_cols = [(0.35, 0.06, 0.05), (0.10, 0.16, 0.25), (0.40, 0.33, 0.20), (0.15, 0.20, 0.13), (0.30, 0.28, 0.26)]
    for i, (z, top) in enumerate(((0.08, 0.40), (0.48, 0.80), (1.33, 1.70))):
        x = kx0 + 0.05
        while x < kx1 - 0.12:
            bw = float(rng.uniform(0.025, 0.05))
            bh = float(rng.uniform(0.6, 0.95)) * (top - z)
            if rng.random() < 0.18:
                x += 0.08
                continue
            c = book_cols[int(rng.integers(0, len(book_cols)))]
            box(f"sach_{i}", x, x + bw, ky0 + 0.04, ky1 - 0.05, z, z + bh, mat(f"sach_{book_cols.index(c)}", c, 0.7))
            x += bw + 0.004
    # TV CRT trên tầng giữa
    tx0, tx1, tz0 = kx0 + 0.18, kx0 + 0.70, 0.88
    box("tv_vo", tx0, tx1, ky0 + 0.02, ky1 - 0.03, tz0, tz0 + 0.40, tv_body)
    box("tv_man", tx0 + 0.05, tx1 - 0.11, ky0 + 0.01, ky0 + 0.025, tz0 + 0.06, tz0 + 0.35, tv_screen)
    for j in range(2):
        cyl(f"tv_nut_{j}", tx1 - 0.06, ky0 + 0.015, tz0 + 0.20 + j * 0.07, tz0 + 0.22 + j * 0.07, 0.015, dark, 10)
    # bóng bay bên trái kệ (buộc dây xuống sàn)
    for i, (bx, by, bz, m) in enumerate(((1.75, 4.15, 1.95, red), (2.0, 4.2, 1.62, blue), (1.82, 4.0, 1.36, blue),
                                         (2.12, 3.98, 1.12, pale))):     # bóng bay giữa kệ sách và cửa 2, buộc dây xuống sàn
        ball(f"bong_bay_{i}", (bx, by, bz), 0.15, m, 1.18)
        rod(f"day_bong_{i}", (bx, by, bz - 0.18), (bx + 0.05, by - 0.08, 0.0), 0.002, string_m)
    # dây cờ tam giác: tường sau (từ góc trái tới nẹp cửa 2) + tường trái (trên cửa 1 về góc)
    def bunting(tag, p0, p1, sag, n):
        p0, p1 = Vector(p0), Vector(p1)
        pts = []
        for k in range(n + 1):
            t = k / n
            p = p0.lerp(p1, t)
            p.z -= sag * 4 * t * (1 - t)
            pts.append(p)
        for k in range(n):
            rod(f"day_co_{tag}_{k}", pts[k], pts[k + 1], 0.003, string_m)
            a, b = pts[k], pts[k + 1]
            m = (red, pale, navy)[k % 3]
            mid = (a + b) / 2
            tri(f"co_{tag}_{k}", [a.lerp(b, 0.1), a.lerp(b, 0.9), Vector((mid.x, mid.y, mid.z - 0.26))], m)
    bunting("bac", (0.08, D - 0.04, 2.42), (DOORS["cua_2"]["lo"] - 0.12, D - 0.04, 2.40), 0.32, 9)
    bunting("tay", (0.04, 0.2, 2.40), (0.04, DOORS["cua_1"]["lo"] - 0.15, 2.42), 0.25, 7)   # dừng trước cửa 1
    # sofa cũ sát tường đông, quay vào phòng
    sx0, sx1, sy0, sy1 = FURNITURE["sofa"]
    box("sofa_de", sx0, sx1 - 0.02, sy0, sy1, 0.08, 0.40, sofa_m)
    box("sofa_lung", sx1 - 0.24, sx1 - 0.02, sy0, sy1, 0.40, 0.92, sofa_m)
    box("sofa_tay_a", sx0, sx1 - 0.02, sy0, sy0 + 0.16, 0.40, 0.64, sofa_m)
    box("sofa_tay_b", sx0, sx1 - 0.02, sy1 - 0.16, sy1, 0.40, 0.64, sofa_m)
    for k in range(2):
        a0 = sy0 + 0.17 + k * (sy1 - sy0 - 0.34) / 2
        box(f"sofa_dem_{k}", sx0 + 0.04, sx1 - 0.26, a0 + 0.01, a0 + (sy1 - sy0 - 0.34) / 2 - 0.01, 0.40, 0.52, sofa_c)
        box(f"sofa_dem_lung_{k}", sx1 - 0.40, sx1 - 0.25, a0 + 0.02, a0 + (sy1 - sy0 - 0.34) / 2 - 0.02, 0.52, 0.86, sofa_c)
    for yy in (sy0 + 0.05, sy1 - 0.05):
        for xx in (sx0 + 0.05, sx1 - 0.07):
            cyl("chan_sofa", xx, yy, 0, 0.08, 0.025, shelf_wood, 8)
    # bàn đèn + đèn bàn chụp vải (nguồn sáng ấm yếu duy nhất)
    bx0, bx1, by0, by1 = FURNITURE["ban_den"]
    box("ban_den_mat", bx0, bx1, by0, by1, 0.55, 0.58, shelf_wood)
    for xx in (bx0 + 0.03, bx1 - 0.03):
        for yy in (by0 + 0.03, by1 - 0.03):
            box("ban_den_chan", xx - 0.015, xx + 0.015, yy - 0.015, yy + 0.015, 0, 0.55, shelf_wood)
    lx, ly = (bx0 + bx1) / 2, (by0 + by1) / 2
    cyl("den_de", lx, ly, 0.58, 0.62, 0.07, brass, 16)
    cyl("den_than", lx, ly, 0.62, 0.92, 0.012, brass, 8)
    ball("den_bong", (lx, ly, 0.95), 0.035, bulb)
    cyl("den_chup", lx, ly, 0.88, 1.10, 0.17, shade, 24, r2=0.10)
    # khung tranh cũ trên tường trái (gần phía máy)
    box("tranh_khung", 0, 0.03, 0.9, 1.6, 1.25, 1.85, shelf_wood)
    box("tranh_long", 0.03, 0.035, 0.95, 1.55, 1.30, 1.80, pic)
    # đôi dép cạnh cửa 1
    for k in range(2):
        box(f"dep_{k}", 0.7 + k * 0.13, 0.81 + k * 0.13, 3.0, 3.27, 0, 0.04, sofa_c)

    # ánh tím–đỏ của thế giới song song sau cửa 1 (chỉ B/C)
    def glow():
        lo, hi = DOORS["cua_1"]["lo"], DOORS["cua_1"]["hi"]
        g = mat("anh_tim_do", (0.62, 0.08, 0.40), 1.0, emit=1.4)
        box("anh_tim_do_cuoi", -T - 3.95, -T - 3.9, lo - 0.2, hi + 0.2, 0, 2.35, g)
        g2 = mat("anh_tim_do_mo", (0.40, 0.04, 0.25), 1.0, emit=0.25)
        box("anh_tim_do_tran", -T - 3.9, -T - 0.3, lo - 0.18, hi + 0.18, 2.33, 2.35, g2)
        # tường bắc hành lang (máy POV nhìn xiên vào lối thấy mặt này): ánh mờ loang — sáng ở xa + sát sàn, tối dần ra phía phòng
        # và lên trần; ô nhỏ 0,5 m × 0,33 m, cường độ giảm mượt + nhiễu nhẹ để không thành tấm hồng phẳng
        import random
        rnd = random.Random(5)
        nx, nz = 8, 7
        for k in range(nx):
            a0 = -T - 3.9 + k * (3.75 / nx)
            for j in range(nz):
                z0 = j * 2.33 / nz
                fx = (1 - k / nx) ** 1.6                    # xa sáng, gần tối
                fz = (1 - j / nz) ** 1.3                    # sàn sáng, trần tối
                e = round((0.03 + 0.45 * fx * fz) * rnd.uniform(0.75, 1.15), 3)
                gk = mat(f"anh_tim_do_tuong_{k}_{j}", (0.48, 0.05, 0.30), 1.0, emit=e)
                box(f"anh_tim_do_tuong_{k}_{j}", a0, a0 + 3.75 / nx, hi + 0.18, hi + 0.2, z0, z0 + 2.33 / nz, gk)

    made = []
    glow_on = False
    for key in ("A", "B", "C"):
        st = STATES[key]
        for n, deg in st["open"].items():
            set_open(n, deg)
        if st["glow"] and not glow_on:
            glow()
            glow_on = True
        path = os.path.join(out_dir, st["file"])
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True)
        made.append(path)
        print("OK", key, path)
    return made


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1])
