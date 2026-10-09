"""Bước 1–2 Sân khấu 3D (PHUONG_PHAP_SAN_KHAU_3D mục 5–8, 6b + "Người dùng quyết 09/10"): phân loại điểm cho nhãn hình phác,
ứng viên máy 24 hướng × 3 độ cao, luật L1–L10 bằng số."""
import math

from core import plate_camera
from core import stage_grid as sg

CAM, AIM, LENS, ASP = (0.0, -5.0, 1.6), (0.0, 0.0, 1.6), 24, 9 / 16     # máy ở Nam nhìn Bắc, khung dọc


# ---- nhãn hình phác: trong / ngoài + mép / sau máy / bị che ----------------------------------------------------------------
def test_point_in_frame():
    r = sg.point_state(CAM, AIM, (0.0, 0.0, 1.6), LENS, ASP)
    assert r["state"] == "in" and abs(r["uv"][0] - 0.5) < 1e-6 and r["arrow"] is None


def test_point_out_right_gives_arrow_on_right_edge():
    r = sg.point_state(CAM, AIM, (8.0, 0.0, 1.6), LENS, ASP)          # xa về Đông = bên phải khung
    assert r["state"] == "out" and r["edge"] == "phai"
    assert r["arrow"][0] > 0.9 and 0.4 < r["arrow"][1] < 0.6         # mũi tên sát mép phải, giữa chiều cao
    assert 0 <= r["arrow"][0] <= 1 and 0 <= r["arrow"][1] <= 1


def test_point_out_top_and_left():
    assert sg.point_state(CAM, AIM, (0.0, 0.0, 30.0), LENS, ASP)["edge"] == "tren"   # đỉnh tháp cao
    assert sg.point_state(CAM, AIM, (-8.0, 0.0, 1.6), LENS, ASP)["edge"] == "trai"
    assert sg.point_state(CAM, AIM, (0.0, -4.0, -3.0), LENS, ASP)["edge"] == "duoi"


def test_point_behind_camera_is_not_drawn():
    r = sg.point_state(CAM, AIM, (0.0, -9.0, 1.6), LENS, ASP)          # sau lưng máy (z_c ≤ 0)
    assert r["state"] == "behind" and r["uv"] is None and r["arrow"] is None


def test_point_blocked_in_frame():
    r = sg.point_state(CAM, AIM, (0.0, 0.0, 1.6), LENS, ASP, blocked_by="STAGE_WELL")
    assert r["state"] == "blocked" and r["blocked_by"] == "STAGE_WELL" and r["uv"] is not None
    # ngoài khung thì "ngoài khung" thắng "bị che" (không chấm trong ảnh)
    assert sg.point_state(CAM, AIM, (8.0, 0.0, 1.6), LENS, ASP, blocked_by="X")["state"] == "out"


# ---- ứng viên máy (mục 5, 8) -----------------------------------------------------------------------------------------------
def test_framing_table_matches_plate_camera():
    assert sg.FRAMING == plate_camera.FRAMING


def test_layer_heights_three_per_layer():
    H = 1.7
    for layer in ("ngang", "thap", "cao", "tren_dau"):
        hs = sg.layer_heights(layer, H)
        assert len(hs) == 3 and hs == sorted(hs)
    assert min(sg.layer_heights("thap", H)) >= 0.5 * H - 1e-9          # thấp: từ 0,5·H, không sát đất
    assert min(sg.layer_heights("cao", H)) >= sg.EYE * H + 0.5 - 1e-9  # cao: mắt + 0,5–1 m
    assert max(sg.layer_heights("cao", H)) <= sg.EYE * H + 1.0 + 1e-9


def test_candidates_24_directions_by_3_heights():
    req = {"aim": [0.0, 0.0, 1.22], "size": "WS", "layer": "ngang", "H": 1.7}
    cs = sg.candidates(req, 9 / 16)
    assert len(cs) == 72
    assert sorted({c["alpha"] for c in cs}) == [15 * k for k in range(24)]
    D = sg.frame_distance(1.7 * 1.0 / 0.55, 24, 9 / 16)                 # WS: cả thân, chiếm 55 % chiều cao khung, ống 24
    for c in cs:
        C, T = c["at"], c["aim"]
        assert abs(math.dist(C, T) - D) < 1e-6
        assert abs(c["pitch"] - math.degrees(math.atan2(T[2] - C[2], math.hypot(T[0] - C[0], T[1] - C[1])))) < 1e-6
        assert c["lens"] == 24
        a = math.degrees(math.atan2(C[0] - T[0], C[1] - T[1])) % 360    # máy đứng ở phương vị α so với T
        assert abs((a - c["alpha"] + 180) % 360 - 180) < 1e-6


def test_candidates_cao_points_down():
    cs = sg.candidates({"aim": [0.0, 0.0, 1.0], "size": "MS", "layer": "cao", "H": 1.7}, 9 / 16)
    assert all(c["pitch"] < 0 for c in cs)


# ---- luật L1–L10 (mục 7) ---------------------------------------------------------------------------------------------------
def good():
    return {"cam_floor": "same", "cam_inside": False, "subject_hit_pct": 100.0, "subject_frame_pct": 55.0, "side": "right",
            "percent": {"troi": 30.0, "san": 30.0, "thap": 12.0, "nha": 10.0, "nguoi_kelly": 10.0, "gieng": 8.0},
            "pitch": 2.0, "occluder_pct": 0.0, "occluder_m": None, "well_hip_ratio": 1.0, "alpha": 165.0}


REQ = {"size": "WS", "layer": "ngang", "s0": "right", "want": {"thap": True}, "need": ["gieng"], "facing": 350.0}


def test_rules_pass_on_good_numbers():
    r = sg.check_rules(good(), REQ)
    assert r["ok"] and r["fail"] == []


def test_rules_each_failure_named():
    cases = [("L1", {"cam_floor": "level"}), ("L1", {"cam_inside": True}), ("L2", {"subject_hit_pct": 50.0}),
             ("L3", {"subject_frame_pct": 20.0}), ("L4", {"side": "left"}),
             ("L5", {"percent": {"troi": 50.0, "san": 40.0, "nguoi_kelly": 6.0, "gieng": 4.0}}),
             ("L7", {"pitch": -20.0}), ("L9", {"occluder_pct": 25.0, "occluder_m": 0.8}), ("L10", {"well_hip_ratio": 1.6})]
    for rule, patch in cases:
        r = sg.check_rules(dict(good(), **patch), REQ)
        assert not r["ok"] and rule in r["fail"], (rule, r)
        assert r["why"][rule]


def test_rule_l5_no_landmark_and_l8_floor_only():
    req = dict(REQ, want={"thap": False}, need=[])
    assert "L5" in sg.check_rules(good(), req)["fail"]                       # thấy tháp khi ý đồ "không thấy tháp"
    down = dict(REQ, layer="cao", want={}, need=[])
    m = dict(good(), pitch=-35.0, percent={"san": 84.5, "nguoi_kelly": 2.0, "troi": 13.5})   # Bước 0: máy 3,4 m chỉ thấy sàn
    r = sg.check_rules(m, down)
    assert "L8" in r["fail"] and "L7" not in r["fail"]
    cu = dict(REQ, size="CU", want={}, need=[])                               # CU: Kelly lấp khung là ý đồ (shot 8 #24)
    assert "L8" not in sg.check_rules(dict(good(), percent={"nguoi_kelly": 93.7, "san": 6.3}), cu)["fail"]


def test_rule_l6_family_and_reverse_ok():
    req = dict(REQ, family="thap")
    m = dict(good(), percent={"nha": 40.0, "san": 30.0, "thap": 5.0, "nguoi_kelly": 10.0, "gieng": 8.0, "troi": 7.0})
    assert "L6" in sg.check_rules(m, req)["fail"]
    assert "L6" not in sg.check_rules(m, dict(req, reverse_ok=True))["fail"]


def test_rule_see_face_or_back():
    # Kelly nhìn 350°: máy ở α = 350 (trước mặt) thấy mặt; α = 170 (sau lưng) thấy lưng
    face = dict(REQ, see="face", want={}, need=[])
    assert "L5" not in sg.check_rules(dict(good(), alpha=345.0), face)["fail"]
    assert "L5" in sg.check_rules(dict(good(), alpha=170.0), face)["fail"]
    back = dict(REQ, see="back", want={}, need=[])
    assert "L5" not in sg.check_rules(dict(good(), alpha=180.0), back)["fail"]


def test_thresholds_marked_provisional():
    assert all("tạm" in v[1] for v in sg.RULE_TH.values())
