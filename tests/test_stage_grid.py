"""Bước 0 lưới sân khấu (KE_HOACH_DAT_MAY_3D 09/10 tối): ô ↔ tọa độ, đường đo từ gốc O, chiếu điểm, phía trục, phân nhóm vật."""
import math

import pytest

from core import stage_grid as sg


def stage(**kw):
    return sg.make_stage([-217.07, 116.0, 9.38], **kw)


def test_labels_and_origin_cell():
    st = stage()                                   # N = 20, ô 1 m: O ở góc Tây-Nam ô K11 (PHUONG_PHAP 2.3)
    assert st["cols"] == 20 and st["rows"] == 20
    assert sg.col_label(0) == "A" and sg.col_label(25) == "Z" and sg.col_label(26) == "AA"
    assert sg.col_index("AA") == 26 and sg.col_index("k") == 10
    assert sg.cell_name(st, 0, 0) == "K11"
    assert sg.cell_centre(st, "K11") == (0.5, 0.5)


def test_west_east_columns_south_north_rows():
    st = stage()
    assert sg.cell_name(st, 1.0, 0) == "L11"        # +x = Đông → cột sau
    assert sg.cell_name(st, -1.0, 0) == "J11"
    assert sg.cell_name(st, 0, 1.0) == "K12"        # +y = Bắc → hàng số lớn hơn
    assert sg.cell_name(st, -0.01, -0.01) == "J10"
    assert sg.cell_name(st, -9.9, -9.9) == "A1"
    assert sg.cell_name(st, 9.9, 9.9) == "T20"
    assert sg.cell_name(st, 10.0, 0) is None         # ngoài lưới
    for name in ("A1", "F8", "T20", "K11"):
        x, y = sg.cell_centre(st, name)
        assert sg.cell_name(st, x, y) == name
    with pytest.raises(ValueError):
        sg.cell_centre(st, "Z99")


def test_half_metre_cells():
    st = stage(cell_m=0.5, cols=11, rows=11)
    assert sg.cell_name(st, 0, 0) == "F6"
    assert sg.cell_centre(st, "G6") == (0.5, 0.0)


def test_model_relative_roundtrip():
    st = stage(floor_z_model=9.4)
    rel = sg.rel_from_model(st, [-215.07, 120.0, 11.4])
    assert rel == pytest.approx((2.0, 4.0, 2.0))
    assert sg.model_from_rel(st, rel) == pytest.approx((-215.07, 120.0, 11.4))
    st2 = dict(st, lift_z=3.29, factor=1.0)
    assert sg.scene_from_rel(st2, (0, 0, 0)) == pytest.approx((-217.07, 116.0, 9.4 + 3.29))
    assert sg.rel_from_scene(st2, (-217.07, 117.0, 12.69)) == pytest.approx((0.0, 1.0, 0.0))


def test_bearing_and_measure():
    assert sg.bearing_deg(0, 1) == pytest.approx(0)
    assert sg.bearing_deg(1, 0) == pytest.approx(90)
    assert sg.bearing_deg(0, -1) == pytest.approx(180)
    assert sg.bearing_deg(-1, 0) == pytest.approx(270)
    st = stage()
    m = sg.measure(st, (3.0, 4.0, 1.5))
    assert m["dist_m"] == 5.0 and m["bearing_deg"] == pytest.approx(36.87, abs=0.05) and m["dz_m"] == 1.5
    assert m["cell"] == "N15" and m["xyz"] == [3.0, 4.0, 1.5]


def test_offset_follows_bearing():
    p = sg.offset((0, 0, 0), 90, 2.0, dz=1.0)
    assert p == pytest.approx((2.0, 0.0, 1.0))
    p = sg.offset((1, 1, 0), 350, 2.0)
    assert sg.bearing_deg(p[0] - 1, p[1] - 1) == pytest.approx(350)


def test_look_and_project():
    cam, aim = (0, -5, 1.6), (0, 0, 1.6)
    yaw, pitch = sg.look(cam, aim)
    assert yaw == pytest.approx(0) and pitch == pytest.approx(0)
    u, v, depth = sg.project(cam, aim, (0, 0, 1.6), lens=36, aspect=16 / 9)
    assert (u, v, depth) == pytest.approx((0.5, 0.5, 5.0))
    u, v, _ = sg.project(cam, aim, (2.5, 0, 1.6), lens=36, aspect=16 / 9)   # tan_h = 18/36 = 0.5 → mép phải ở 2,5 m
    assert u == pytest.approx(1.0)
    _, v, _ = sg.project(cam, aim, (0, 0, 1.6 + 2.5 * 9 / 16), lens=36, aspect=16 / 9)
    assert v == pytest.approx(0.0)                    # mép trên
    assert sg.project(cam, aim, (0, -10, 1.6), lens=36, aspect=16 / 9) is None   # sau lưng máy
    assert sg.in_frame((0.3, 0.9, 4)) and not sg.in_frame((1.2, 0.5, 4)) and not sg.in_frame(None)


def test_ray_dir_is_inverse_of_project():
    cam, aim = (1, -6, 3.0), (0, 0, 0.8)
    for u, v in ((0.5, 0.5), (0.1, 0.2), (0.9, 0.95)):
        d = sg.ray_dir(cam, aim, u, v, lens=24, aspect=16 / 9)
        p = tuple(c + 7 * k for c, k in zip(cam, d))
        pu, pv, _ = sg.project(cam, aim, p, lens=24, aspect=16 / 9)
        assert (pu, pv) == pytest.approx((u, v), abs=1e-6)
    _, pitch = sg.look(cam, aim)
    assert pitch < -15                                # máy cao cúi


def test_axis_side_and_angle():
    a, b = (0, 0, 0), (0, 2, 0)                       # trục Kelly → giếng nhìn về Bắc
    assert sg.axis_side(a, b, (3, 1, 0)) == "right"   # Đông = bên phải khi nhìn từ a sang b
    assert sg.axis_side(a, b, (-3, 1, 0)) == "left"
    assert sg.axis_side(a, b, (0, 5, 0)) == "on"
    assert sg.angle_at((1, 0, 0), (0, 0, 0), (0, 1, 0)) == pytest.approx(90)


def test_cell_floor_status():
    assert sg.floor_status(0.1) == "same" and sg.floor_status(-0.15) == "same"
    assert sg.floor_status(0.4) == "step" and sg.floor_status(-1.2) == "level"
    assert sg.floor_status(None) == "none"
    assert sg.slope_deg([0, 0.035, 0.07], 1.0) == pytest.approx(math.degrees(math.atan(0.035)), abs=0.01)


def test_group_by_name():
    assert sg.group_by_name("Clocktower_Main", "M_Stone") == "thap"
    assert sg.group_by_name("Main_Large_Terrain03_plan", "Terrain") == "san"
    assert sg.group_by_name("OilDrums_plan2", "OilDrums_D_StdMat") == "khac"      # "_plan" là hậu tố của mọi object map FF
    assert sg.group_by_name("CLK_OUT_Tower001_LOD0_plan", "tower_01_StdMat") == "thap"
    assert sg.group_by_name("CMO_OUT_HugeHouse001_LOD0_plan", "Zone_J_House_tile_StdMat4") == "nha"
    assert sg.group_by_name("XH_House_02_Roof", "") == "nha"
    assert sg.group_by_name("Wall_low_01", "") == "tuong"
    assert sg.group_by_name("Stairs_A", "") == "bac"
    assert sg.group_by_name("GreenTree_03", "") == "cay"
    assert sg.group_by_name("STAGE_WELL", "") == "gieng"
    assert sg.group_by_name("STAGE_KELLY", "") == "nguoi"
    assert sg.group_by_name("Mesh.123", "Material.002") == "khac"


def test_group_by_shape():
    assert sg.group_by_shape(top_rel=30.0, size=(12, 12, 40)) == "thap"
    assert sg.group_by_shape(top_rel=8.0, size=(10, 8, 9)) == "nha"
    assert sg.group_by_shape(top_rel=0.9, size=(6, 0.4, 1.0)) == "tuong"
    assert sg.group_by_shape(top_rel=0.05, size=(80, 80, 3)) == "san"


def test_camera_geometry_formulas():
    h, v = sg.fov(36, 16 / 9)
    assert h == pytest.approx(2 * math.degrees(math.atan(0.5)))
    assert sg.horizon_w(0, 24, 9 / 16) == pytest.approx(0.5)
    assert sg.horizon_w(-10, 24, 9 / 16) < 0.5           # cúi → chân trời lên cao trong ảnh
    d = sg.frame_distance(2.0, 24, 9 / 16)              # tan(v/2) = 18/24
    assert d == pytest.approx(1.0 / 0.75)
    c = sg.camera_at((0, 0, 1.6), 180, 5.0, 4.6)        # cao hơn đích 3 m → D_h = 4
    assert c == pytest.approx((0.0, -4.0, 4.6))
    assert sg.camera_at((0, 0, 0), 0, 1.0, 3.0) is None
    assert sg.median([3, 1, 2]) == 2 and sg.median([1, 2, 3, 4]) == 2.5 and sg.median([]) is None
    assert (sg.EYE, sg.CHEST, sg.HIP) == (0.93, 0.72, 0.53)


def test_group_by_hit_splits_the_base_mesh():
    assert sg.group_by_hit("san", 0.02, 1.0) == "san"
    assert sg.group_by_hit("san", 0.4, 1.0) == "bac"
    assert sg.group_by_hit("san", 1.43, 1.0) == "tuong"      # đỉnh tường thấp quảng trường #24
    assert sg.group_by_hit("san", 0.8, 0.0) == "tuong"       # mặt đứng
    assert sg.group_by_hit("san", -6.2, 1.0) == "san_khac"   # sàn tầng dưới
    assert sg.group_by_hit("khac", 0.3, 0.7) == "doc"
    assert sg.group_by_hit("thap", 5.0, 0.0) == "thap"
