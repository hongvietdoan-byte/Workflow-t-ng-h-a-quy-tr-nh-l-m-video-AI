"""Bếp đời thường có quạt trần — dựng bằng Blender (không tốn tiền), xuất .glb cho gói bối cảnh (S14.37).

Chạy:  blender -b --factory-startup -P tools/build_kitchen.py -- <out.glb>
Hệ tọa độ (mét, Z lên): phòng X 0..5.5, Y 0..4.5, cao 2.7. Quầy bếp sát tường bắc (y=4.5), tủ lạnh sát tường đông (x=5.5),
bàn ăn góc tây nam (1.5, 1.2) với quạt trần ngay trên, cửa sổ tường tây, cửa ra vào tường nam.
`SPOTS` là các chỗ đứng gợi ý (cùng hệ tọa độ) để đăng ký vào gói bối cảnh.
"""
import math
import sys

SPOTS = {
    "ban_bep": {"at": [2.8, 3.0, 0.0], "facing": 180.0, "label": "bàn bếp (quầy, bồn rửa, bếp) — nhìn về quầy bếp phía sau", "view": [2.8, 4.5, 1.2]},
    "tu_lanh": {"at": [4.0, 2.65, 0.0], "facing": 270.0, "label": "cạnh tủ lạnh (tủ lạnh ở phía sau)", "view": [5.5, 2.65, 1.2]},
    "ban_an_quat_tran": {"at": [1.5, 2.4, 0.0], "facing": 180.0, "label": "bên bàn ăn — quạt trần phía trên bàn (máy hất lên thấy quạt)", "view": [1.5, 1.2, 2.4]},
    "cua_vao": {"at": [3.4, 0.9, 0.0], "facing": 0.0, "label": "gần cửa vào — nhìn cả bếp và bàn ăn", "view": [3.4, 3.5, 1.2]},
}
W, D, H = 5.5, 4.5, 2.7


def main(out):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {}

    def mat(name, rgb, rough=0.6, metal=0.0, emit=0.0):
        if name not in mats:
            m = bpy.data.materials.new(name)
            m.use_nodes = True
            b = m.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = (*rgb, 1)
            b.inputs["Roughness"].default_value = rough
            b.inputs["Metallic"].default_value = metal
            if emit:
                b.inputs["Emission Color"].default_value = (*rgb, 1)
                b.inputs["Emission Strength"].default_value = emit
            mats[name] = m
        return mats[name]

    def box(name, x0, x1, y0, y1, z0, z1, m):
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        o = bpy.context.active_object
        o.name = name
        o.scale = (x1 - x0, y1 - y0, z1 - z0)
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(m)
        return o

    def cyl(name, x, y, z0, z1, r, m, verts=24):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=z1 - z0, location=(x, y, (z0 + z1) / 2))
        o = bpy.context.active_object
        o.name = name
        o.data.materials.append(m)
        return o

    wall = mat("tuong", (0.93, 0.88, 0.76), 0.9)
    floor = mat("san", (0.62, 0.50, 0.38), 0.45)
    ceil = mat("tran", (0.97, 0.96, 0.93), 0.9)
    wood = mat("go", (0.55, 0.36, 0.2), 0.5)
    cab = mat("tu_bep", (0.88, 0.84, 0.74), 0.5)
    top = mat("mat_quay", (0.25, 0.25, 0.27), 0.3)
    tile = mat("gach", (0.9, 0.93, 0.92), 0.2)
    steel = mat("inox", (0.72, 0.74, 0.76), 0.25, 0.9)
    dark = mat("den", (0.05, 0.05, 0.06), 0.4)
    white = mat("trang", (0.95, 0.95, 0.95), 0.3)
    sky = mat("ngoai_cua_so", (0.75, 0.88, 1.0), 1.0, emit=6.0)
    hall = mat("hanh_lang", (0.9, 0.8, 0.6), 1.0, emit=1.5)
    t = 0.1
    # vỏ phòng
    box("san", -t, W + t, -t, D + t, -t, 0, floor)
    box("tran", -t, W + t, -t, D + t, H, H + t, ceil)
    box("tuong_bac", -t, W + t, D, D + t, 0, H, wall)
    box("tuong_dong", W, W + t, 0, D, 0, H, wall)
    # tường tây có cửa sổ y 1.5..3.0, z 1.0..2.0
    box("tay_duoi", -t, 0, 0, D, 0, 1.0, wall)
    box("tay_tren", -t, 0, 0, D, 2.0, H, wall)
    box("tay_trai", -t, 0, 0, 1.5, 1.0, 2.0, wall)
    box("tay_phai", -t, 0, 3.0, D, 1.0, 2.0, wall)
    box("kinh_ngoai", -0.6, -0.5, 1.4, 3.1, 0.9, 2.1, sky)
    for n, (y0, y1, z0, z1) in {"k1": (1.45, 1.5, 1.0, 2.0), "k2": (3.0, 3.05, 1.0, 2.0), "k3": (1.5, 3.0, 0.97, 1.0), "k4": (1.5, 3.0, 2.0, 2.03)}.items():
        box("khung_" + n, -0.06, 0.04, y0, y1, z0, z1, white)
    box("khung_giua", -0.04, 0.02, 2.2, 2.25, 1.0, 2.0, white)
    # tường nam có cửa x 4.2..5.1, z 0..2.05
    box("nam_trai", -t, 4.2, -t, 0, 0, H, wall)
    box("nam_phai", 5.1, W + t, -t, 0, 0, H, wall)
    box("nam_tren", 4.2, 5.1, -t, 0, 2.05, H, wall)
    box("hanh_lang", 4.2, 5.1, -0.9, -0.8, 0, 2.05, hall)
    box("khung_cua", 4.15, 4.2, -t, 0, 0, 2.05, wood)
    box("khung_cua2", 5.1, 5.15, -t, 0, 0, 2.05, wood)
    # quầy bếp sát tường bắc (x 0.2..3.9), sâu 0.6
    box("tu_duoi", 0.2, 3.9, 3.9, D, 0.0, 0.88, cab)
    box("mat_quay", 0.2, 3.9, 3.85, D, 0.88, 0.92, top)
    box("op_gach", 0.2, 3.9, D - 0.03, D, 0.92, 1.5, tile)
    box("tu_tren", 0.2, 3.9, 4.15, D, 1.5, 2.25, cab)
    for i in range(1, 7):
        box(f"khe_tu_{i}", 0.2 + i * 0.6165 - 0.005, 0.2 + i * 0.6165 + 0.005, 4.14, 4.16, 1.5, 2.25, dark)
        box(f"khe_tu_duoi_{i}", 0.2 + i * 0.6165 - 0.005, 0.2 + i * 0.6165 + 0.005, 3.88, 3.9, 0.0, 0.88, dark)
    box("bon_rua", 1.2, 1.95, 4.0, 4.4, 0.8, 0.93, steel)
    box("long_bon", 1.27, 1.88, 4.05, 4.35, 0.82, 0.935, dark)
    cyl("voi_nuoc", 1.58, 4.42, 0.92, 1.18, 0.02, steel, 12)
    box("voi_ngang", 1.58 - 0.01, 1.58 + 0.01, 4.25, 4.43, 1.16, 1.2, steel)
    box("bep_ga", 2.5, 3.2, 3.98, 4.42, 0.92, 0.95, steel)
    for i, (bx, by) in enumerate([(2.68, 4.1), (3.02, 4.1), (2.68, 4.3), (3.02, 4.3)]):
        cyl(f"mat_bep_{i}", bx, by, 0.95, 0.97, 0.07, dark, 20)
    box("hut_mui", 2.4, 3.3, 4.0, D, 1.55, 1.75, steel)
    box("ong_hut", 2.7, 3.0, 4.2, D, 1.75, H, steel)
    # tủ lạnh sát tường đông
    box("tu_lanh", 4.85, W, 2.3, 3.0, 0.0, 1.85, steel)
    box("tu_lanh_khe", 4.83, 4.85, 2.3, 3.0, 1.2, 1.22, dark)
    box("tay_nam_tren", 4.80, 4.85, 2.35, 2.4, 1.3, 1.75, dark)
    box("tay_nam_duoi", 4.80, 4.85, 2.35, 2.4, 0.3, 0.9, dark)
    # bàn ăn giữa phòng + quạt trần ngay trên
    cx, cy = 1.5, 1.2
    box("mat_ban", cx - 0.65, cx + 0.65, cy - 0.43, cy + 0.43, 0.72, 0.76, wood)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box("chan_ban", cx + sx * 0.6 - 0.03, cx + sx * 0.6 + 0.03, cy + sy * 0.38 - 0.03, cy + sy * 0.38 + 0.03, 0, 0.72, wood)
    cyl("dia", cx, cy, 0.76, 0.775, 0.17, white, 32)
    cyl("vien_dia", cx, cy, 0.775, 0.785, 0.11, mat("dia_loi", (0.9, 0.9, 0.92), 0.2), 32)
    for k, (px, py) in enumerate([(cx - 0.95, cy), (cx + 0.95, cy)]):
        box(f"ghe_mat_{k}", px - 0.22, px + 0.22, py - 0.22, py + 0.22, 0.44, 0.48, wood)
        box(f"ghe_lung_{k}", px - 0.22 if k else px - 0.22, px + 0.22, py - 0.22, py - 0.18, 0.48, 0.9, wood)
        for sx in (-1, 1):
            for sy in (-1, 1):
                box("chan_ghe", px + sx * 0.19 - 0.015, px + sx * 0.19 + 0.015, py + sy * 0.19 - 0.015, py + sy * 0.19 + 0.015, 0, 0.44, wood)
    # quạt trần: ống treo + động cơ + 4 cánh + đèn
    cyl("quat_dai_tran", cx, cy, H - 0.04, H, 0.08, white, 20)
    cyl("quat_ong", cx, cy, H - 0.3, H - 0.04, 0.02, dark, 12)
    cyl("quat_dong_co", cx, cy, H - 0.42, H - 0.3, 0.12, dark, 24)
    cyl("quat_den", cx, cy, H - 0.52, H - 0.42, 0.09, mat("den_quat", (1.0, 0.95, 0.8), 0.3, emit=3.0), 24)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        r0, r1 = 0.14, 0.72
        mx, my = cx + math.cos(a) * (r0 + r1) / 2, cy + math.sin(a) * (r0 + r1) / 2
        bpy.ops.mesh.primitive_cube_add(size=1, location=(mx, my, H - 0.34))
        b = bpy.context.active_object
        b.name = f"canh_quat_{k}"
        b.scale = (r1 - r0, 0.16, 0.012)
        b.rotation_euler = (math.radians(6), 0, a)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        b.data.materials.append(wood)
    # đồ treo tường: đồng hồ
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.17, depth=0.04, location=(4.3, D - 0.02, 1.9), rotation=(math.radians(90), 0, 0))
    bpy.context.active_object.data.materials.append(white)
    bpy.context.active_object.name = "dong_ho_tuong"
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_apply=True)
    print("OK", out)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1])
