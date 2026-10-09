"""Sân khấu 3D v2 — V1 (PHUONG_PHAP_SAN_KHAU_3D mục 3.2, 4, 6, 7.2): vùng đích, hướng thấy, luật P/S, bộ giải máy góc nội tiếp."""
import math

import pytest

from core import stage_grid as sg
from core import stage_solver as ss

WELL = sg.offset((0.0, 0.0, 0.0), 350, 1.6)            # #24: Kelly ở O nhìn 350°, giếng cách 1,6 m
MARKS = {"thap_chan": {"xyz": [0.0, 16.04, -0.34]}, "thap_dinh": {"xyz": [0.0, 16.04, 38.11]},
         "thap_object": {"name": "CLK_OUT_Tower001_LOD0_plan", "bbox_size_m": [9.35, 9.35, 38.46]}}


def blocking(in_well=True):
    yeunu = {"key": "yeunu", "kind": "nguoi", "H": 1.7, "facing": 170, "label": "Yêu nữ"}
    yeunu.update({"in": "gieng"} if in_well else {"at": list(sg.offset(WELL, 350, 1.2)[:2])})
    return {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0, 0], "H": 1.7, "facing": 350, "label": "Kelly"},
                        {"key": "gieng", "kind": "gieng", "at": [WELL[0], WELL[1]], "h": 0.9, "d": 1.5, "hollow": in_well},
                        yeunu, {"key": "thap", "kind": "moc", "label": "Tháp"}],
            "axis": ["kelly", "gieng"], "aspect": "9:16"}


def objs(in_well=True):
    return ss.objects_from_blocking(blocking(in_well), MARKS)


# ---- vùng đích (3.2) ----------------------------------------------------------------------------------------------------------
def test_parse_zone_forms():
    t = 1 / 3
    assert sg.parse_zone("phai-giua") == {"u": (2 * t, 1.0), "w": (t, 2 * t)}
    assert sg.parse_zone("1/3 phải, 1/3 giữa") == sg.parse_zone("phai-giua")      # cách Director viết trong mục 3.2
    assert sg.parse_zone("giữa dưới") == {"u": (t, 2 * t), "w": (2 * t, 1.0)}
    assert sg.parse_zone("giua+phai-duoi")["u"] == (t, 1.0)                          # ghép 2 ô
    assert sg.parse_zone("trai") == {"u": (0.0, t), "w": None}                      # chỉ ngang
    assert sg.parse_zone("dưới") == {"u": None, "w": (2 * t, 1.0)}                  # chỉ dọc
    assert sg.parse_zone("*-tren") == {"u": None, "w": (0.0, t)}
    assert sg.parse_zone(None) == {"u": None, "w": None}
    with pytest.raises(ValueError):
        sg.parse_zone("ben canh")


def test_zone_miss_and_view():
    z = sg.parse_zone("phai-giua")
    assert sg.zone_miss((0.8, 0.5), z) == 0.0
    assert abs(sg.zone_miss((0.6, 0.5), z) - (2 / 3 - 0.6)) < 1e-9
    assert sg.zone_miss(None, z) == 1.0
    # Kelly nhìn 350°: máy phía trước (Bắc) thấy mặt, sau lưng (Nam) thấy lưng, phía Đông thấy nghiêng
    assert sg.view_of(350, (0, 0), (0, 3)) == "mat"
    assert sg.view_of(350, (0, 0), (0, -3)) == "lung"
    assert sg.view_of(350, (0, 0), (3, 0)) == "nghieng"


def test_in_well_person_only_counts_above_rim():
    o = objs()["yeunu"]
    assert abs(o["z"] - sg.in_well_foot_z(0.9, 1.7)) < 1e-9 and o["rim_z"] == 0.9
    pts = sg.object_points(o, (0, -3, 1.5))
    assert len(pts) == 28 and all(p[2] > 0.9 for p in pts)                 # 27 điểm thân trên miệng giếng + 1 điểm mặt/mũi
    top, bot = sg.size_span(o, "MS")
    assert bot[2] == 0.9 and abs(top[2] - (o["z"] + 1.7)) < 1e-9          # MS bị chặn ở miệng giếng


# ---- luật P/S (7.1–7.2) ---------------------------------------------------------------------------------------------------------
SPEC = {"shot": 3, "co": "MS", "goc": "cui", "thanh_phan": [
    {"vat": "yeunu", "vai": "chinh", "vung": "phai-giua", "thay": "mat", "co_pct": [15, 35]},
    {"vat": "gieng", "vai": "chinh", "vung": "giua-duoi"},
    {"vat": "kelly", "vai": "phu", "vung": "trai", "thay": "lung|nghieng"},
    {"vat": "thap", "vai": "khong_duoc_co"}]}


def good_m():
    return {"pitch": -30.0, "percent": {"san": 50.0, "gieng": 20.0, "nguoi_yeunu": 10.0, "nguoi_kelly": 10.0, "tuong": 10.0},
            "cam_floor": "same", "cam_inside": False, "occluder_pct": 0.0, "occluder_m": None, "well_hip_ratio": 1.0,
            "obj": {"yeunu": {"in_pct": 100, "seen_pct": 90, "uv": [0.8, 0.5], "size_pct": 25, "view": "mat"},
                    "gieng": {"in_pct": 100, "seen_pct": 80, "uv": [0.5, 0.8], "size_pct": 20},
                    "kelly": {"in_pct": 60, "seen_pct": 60, "uv": [0.2, 0.4], "size_pct": 60, "view": "lung"},
                    "thap": {"in_pct": 0, "seen_pct": 0, "uv": None}}}


def test_check_spec_passes_good_numbers():
    r = sg.check_spec(good_m(), SPEC, objs())
    assert r["ok"], r
    assert r["phu"] == {"kelly": True} and r["miss"] == 0.0


def test_check_spec_each_failure_named():
    def patch(k, **kw):
        m = good_m()
        m["obj"][k] = dict(m["obj"][k], **kw)
        return m
    cases = [("P1", dict(good_m(), cam_floor="level")), ("P1", dict(good_m(), cam_inside=True)),
             ("P2", dict(good_m(), occluder_pct=25.0, occluder_m=0.8)), ("P3", dict(good_m(), pitch=-6.0)),
             ("P4", dict(good_m(), well_hip_ratio=1.6)),
             ("S1", patch("yeunu", seen_pct=30)), ("S2", patch("gieng", uv=[0.9, 0.2])), ("S3", patch("yeunu", size_pct=60)),
             ("S4", patch("yeunu", view="lung")), ("S5", patch("thap", seen_pct=4.0)),
             ("S6", dict(good_m(), percent={"san": 84.5, "gieng": 5.0, "nguoi_yeunu": 5.0, "troi": 5.5}))]
    for code, m in cases:
        r = sg.check_spec(m, SPEC, objs())
        assert not r["ok"] and code in r["fail"], (code, r)
        assert r["why"][code]


def test_check_spec_stage_a_uses_in_frame_and_skips_unmeasured():
    m = sg.frame_eval((0.3, -3.0, 1.6), (0.0, 0.0, 1.2), 35, 9 / 16, objs(), co="MS", size_key="yeunu")
    r = sg.check_spec(m, SPEC, objs())
    assert not {"P1", "P2", "P4", "S6"} & set(r["fail"])                # chưa có số Blender → không chấm
    phu_bad = dict(good_m())
    phu_bad["obj"] = dict(phu_bad["obj"], kelly={"in_pct": 0, "seen_pct": 0, "uv": None})
    assert sg.check_spec(phu_bad, SPEC, objs())["ok"]                   # thứ phụ thiếu chỉ hạ hạng, không hỏng


def test_first_main_default_size_from_framing():
    spec = {"co": "WS", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua"}]}
    m = {"pitch": 0.0, "obj": {"kelly": {"in_pct": 100, "uv": [0.5, 0.5], "size_pct": 30, "view": "mat"}}}
    assert "S3" in sg.check_spec(m, spec, objs())["fail"]               # WS cần 55 % ± 15 %
    m["obj"]["kelly"]["size_pct"] = 55
    assert sg.check_spec(m, spec, objs())["ok"]


def test_v2_thresholds_provisional():
    for k in ("S1_nguoi_pct", "S1_dao_cu_pct", "S1_moc_pct", "S2_tol", "S6_max_pct"):
        assert k in sg.RULE_TH and "tạm" in sg.RULE_TH[k][1]


# ---- bộ giải (6.1–6.4) ---------------------------------------------------------------------------------------------------------
def test_inscribed_angle_matches_doc_example():
    """Mục 6.2 'Đã kiểm bằng số': Kelly (0; 0), yêu nữ (−0,28; 1,58), u 0,33 / 0,67, D_A 2,4 → C ≈ (1,72; −1,68) và (−0,12; 2,40)."""
    th = sg._tans(50, 16 / 9)[0]
    g = ss.gamma_for(0.33, 0.67, th)
    sols = ss.inscribed_solutions((0, 0), (-0.28, 1.58), g, 2.4)
    assert len(sols) == 2
    want = [(1.72, -1.68), (-0.12, 2.40)]
    for w in want:
        assert min(math.dist(w, s) for s in sols) < 0.05
    for C in sols:
        assert abs(math.dist(C, (0, 0)) - 2.4) < 1e-6
        assert abs(ss.signed_angle(C, (0, 0), (-0.28, 1.58)) - g) < 1e-6   # cùng dấu γ: cung đối xứng đã bị loại


def test_distance_for_size():
    tv = sg._tans(24, 9 / 16)[1]
    assert abs(ss.distance_for_size(1.7, 0.55, tv) - sg.frame_distance(1.7 / 0.55, 24, 9 / 16)) < 1e-9


def test_validate_reports_problems_without_guessing():
    o = objs()
    assert any("không có trong dàn cảnh" in e for e in ss.validate({"co": "WS", "thanh_phan": [{"vat": "ma", "vai": "chinh"}]}, o))
    assert any("không có thứ 'chinh'" in e for e in ss.validate({"co": "WS", "thanh_phan": [{"vat": "kelly", "vai": "phu"}]}, o))
    bad = {"co": "WS", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua"}, {"vat": "thap", "vai": "chinh", "vung": "giua"}]}
    assert any("mâu thuẫn" in e for e in ss.validate(bad, o))
    assert any("cỡ" in e for e in ss.validate({"co": "XL", "thanh_phan": [{"vat": "kelly", "vai": "chinh"}]}, o))
    r = ss.solve_shot({"co": "MS", "thanh_phan": [{"vat": "gieng", "vai": "chinh", "vung": "giua"}]}, o, 9 / 16)
    assert any("thiếu ý đồ hướng" in e for e in r["errors"]) and not r["cams"]


def test_solve_two_mains_hits_zones_and_size():
    spec = {"shot": 1, "co": "WS", "do_cao": "ngang", "goc": "ngang", "thanh_phan": [
        {"vat": "kelly", "vai": "chinh", "vung": "trai", "thay": "lung|nghieng"},
        {"vat": "gieng", "vai": "chinh", "vung": "giua-duoi"},
        {"vat": "thap", "vai": "phu", "vung": "giua+phai-tren"}]}
    r = ss.solve_shot(spec, objs(), 9 / 16)
    assert not r["errors"]
    sols = [c for c in r["cams"] if not c["fallback"]]
    assert 1 <= len(sols) <= 2
    best = r["cams"][0]
    assert best["check"]["ok"], best["check"]
    exact = [c for c in sols if c["check"]["ok"]]
    assert exact
    sh = ss.Shot(spec, objs(), 9 / 16)
    for c in exact:          # mắt Kelly ở tâm vùng ngang + đường 1/3 trên (mặc định), giếng giữa ngang — sau tinh chỉnh với pitch ≠ 0
        r = sh.residuals(c["at"], c["aim"])
        assert abs(r[0]) / ss.W_A <= ss.TOL_UV and abs(r[2]) <= ss.TOL_UV, r              # u của A và B trúng tâm vùng
        assert abs(c["eval"]["obj"]["kelly"]["uv"][1] - 1 / 3) <= 0.03     # mắt Kelly sát đường 1/3 trên (đích mặc định, A ưu tiên)
        # giếng ở 1/3 dưới + mắt Kelly 1/3 trên + cỡ WS cần máy thấp hơn lớp 'ngang' (± 0,3 m) → máy chạm đáy lớp, lệch còn trong dung sai S2
        assert sh.cz_range[0] - 1e-6 <= c["cz"] <= sh.cz_range[1] + 1e-6


def test_fallback_about_30_points():
    steps = ss._fallback_steps()
    assert 25 <= len(steps) <= 32 and (0, 1.0, 0.0) not in steps


def test_single_main_uses_view_direction():
    spec = {"shot": 7, "co": "MCU", "do_cao": "ngang", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua-tren", "thay": "mat"}]}
    r = ss.solve_shot(spec, objs(), 9 / 16)
    assert not r["errors"] and r["cams"]
    best = r["cams"][0]
    assert best["eval"]["obj"]["kelly"]["view"] == "mat" and best["check"]["ok"], best["check"]


def test_infeasible_spec_gets_advice():
    """Mâu thuẫn hướng thấy (yêu nữ trong giếng nhìn về Kelly, muốn thấy mặt yêu nữ bên PHẢI và Kelly bên TRÁI ở cỡ chặt) → không
    phương án nào đạt, có gợi ý bằng chữ — không im lặng, không tự nới luật."""
    r = ss.solve_shot(SPEC, objs(), 9 / 16)
    if not any(c["check"]["ok"] and c["c1_ok"] for c in r["cams"]):
        assert r["advice"] and all("→" in a for a in r["advice"])


def test_solve_scene_picks_s0_from_opening_shot():
    specs = [{"shot": 1, "co": "WS", "do_cao": "ngang", "thanh_phan": [
                {"vat": "kelly", "vai": "chinh", "vung": "trai-duoi"}, {"vat": "gieng", "vai": "chinh", "vung": "giua-duoi"}]},
             {"shot": 2, "co": "WS", "do_cao": "cao", "goc": "cui", "thanh_phan": [
                {"vat": "kelly", "vai": "chinh", "vung": "phai-duoi"}, {"vat": "gieng", "vai": "chinh", "vung": "giua-duoi"}]}]
    r = ss.solve_scene(specs, blocking(), 9 / 16, marks=MARKS)
    assert r["s0"] in ("left", "right")
    s2 = r["shots"][1]
    assert all(c["c1_ok"] == (c["side"] in (r["s0"], "on")) for c in s2["cams"])   # shot sau giữ phía trục của shot mở


def test_blender_props_well_first_and_in_well_foot():
    import importlib.util
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "stage_grid.py")
    spec = importlib.util.spec_from_file_location("stage_grid_tool", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    props = mod.blender_props(objs())
    assert props[0]["name"] == "WELL" and props[0]["hollow"]
    y = next(p for p in props if p.get("key") == "yeunu")
    assert abs(y["in_well"]["foot_z"] - sg.in_well_foot_z(0.9, 1.7)) < 1e-6
    # nhịp: Kelly đứng / ngã ngồi = 2 người nộm riêng; yêu nữ vắng ở nhịp đầu
    bl = dict(blocking(), beats={"dung": {"yeunu": {"hidden": True}},
                                 "nga": {"kelly": {"at": [0.04, -0.25], "H": 1.0, "tu_the": "ngoi"}}})
    beats = {b: ss.objects_from_blocking(bl, MARKS, b) for b in ("dung", "nga")}
    assert "yeunu" not in beats["dung"] and beats["nga"]["kelly"]["H"] == 1.0 and beats["nga"]["yeunu"]["rim_z"] == 0.9
    props = mod.blender_props(beats)
    kel = [p for p in props if p.get("key") == "kelly"]
    assert len(kel) == 2 and {p["name"] for p in kel} == {"KELLY_V0", "KELLY_V1"}
    assert beats["nga"]["kelly"]["own"] == "STAGE_KELLY_V1_" and beats["dung"]["kelly"]["own"] == "STAGE_KELLY_V0_"


def test_beat_errors_named():
    with pytest.raises(ValueError):
        ss.objects_from_blocking(dict(blocking(), beats={}), MARKS, "khong_co")
    with pytest.raises(ValueError):
        ss.objects_from_blocking({"objects": [{"key": "ke_lly", "kind": "nguoi", "at": [0, 0]}]})


def test_same_column_puts_camera_on_line_behind_a():
    """γ ≈ 0 (B cùng cột với A, vd giếng sau lưng yêu nữ): máy trên đường B→A kéo dài, B ở sau A."""
    bl = dict(blocking(), beats={"ra": {"yeunu": {"at": list(sg.offset(WELL, 170, 1.0)[:2]), "facing": 170}}})
    o = ss.objects_from_blocking(bl, MARKS, "ra")
    spec = {"co": "MLS", "do_cao": "thap", "thanh_phan": [{"vat": "yeunu", "vai": "chinh", "vung": "giua", "thay": "mat"},
                                                          {"vat": "gieng", "vai": "phu", "vung": "giua-duoi"}]}
    r = ss.solve_shot(spec, o, 9 / 16, fallback=False)
    c = r["cams"][0]
    assert "thẳng hàng" in c["tag"]
    y, w = o["yeunu"]["xy"], o["gieng"]["xy"]
    assert math.dist(c["at"][:2], w) > math.dist(c["at"][:2], y)                # máy ở phía yêu nữ, giếng sau lưng cô
    assert abs(ss.signed_angle(c["at"], y, w)) < 2.0


def test_size_range_used_when_target_distance_has_no_arc_point():
    """co_pct là KHOẢNG: ở khoảng cách đích không có điểm nhìn AB dưới γ → thử khoảng cách khác trong khoảng cỡ, ghi chú rõ."""
    bl = dict(blocking(), beats={"q": {"kelly": {"at": [0.043, -0.246], "H": 1.0, "tu_the": "ngoi"},
                                       "yeunu": {"at": [-0.104, 0.591], "facing": 170, "H": 1.2, "tu_the": "quy"}}})
    o = ss.objects_from_blocking(bl, MARKS, "q")
    spec = {"co": "WS", "do_cao": "cao", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "trai", "co_pct": [15, 40]},
                                                        {"vat": "yeunu", "vai": "chinh", "vung": "giua+phai"}]}
    r = ss.solve_shot(spec, o, 9 / 16, fallback=False)
    assert any("trong khoảng cỡ" in n for n in r["notes"]) and r["cams"]
    sz = r["cams"][0]["eval"]["obj"]["kelly"]["size_pct"]
    assert 15 <= sz <= 40


def test_same_column_different_rows_is_not_a_conflict():
    o = objs()
    ok = {"co": "WS", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua-duoi"}, {"vat": "gieng", "vai": "chinh", "vung": "giua"}]}
    assert not any("mâu thuẫn" in e for e in ss.validate(ok, o))                       # một bên ghi hàng dưới → tách được theo dọc
    assert not any("mâu thuẫn" in e for e in ss.validate(dict(ok, thanh_phan=[ok["thanh_phan"][0], dict(ok["thanh_phan"][1], vung="giua-giua")]), o))
    assert any("mâu thuẫn" in e for e in ss.validate(dict(ok, thanh_phan=[dict(ok["thanh_phan"][0], vung="giua"), ok["thanh_phan"][1]]), o))


def test_pov_camera_at_eye_and_dolly_back_checks_end_frame():
    """Góc nhìn nhân vật: máy ở MẮT người đó (người đó bỏ khỏi khung); máy lùi: khung cuối dời song song m mét, luật chấm cả khung cuối
    (bỏ cỡ + vùng). #24 shot 6–7 (người dùng 09/10: Kelly sợ bò lùi, máy lùi + rung nhẹ)."""
    bl = dict(blocking(), beats={"bo": {"kelly": {"at": [0.043, -0.246], "H": 1.0, "tu_the": "ngoi"},
                                        "yeunu": {"at": [-0.104, 0.591], "facing": 170, "H": 0.6, "tu_the": "bo"}}})
    o = ss.objects_from_blocking(bl, MARKS, "bo")
    spec = {"co": "MS", "ong_kinh": 24, "pov": "kelly", "may": {"kieu": "lui", "m": 1.0, "rung": "nhe"},
            "thanh_phan": [{"vat": "yeunu", "vai": "chinh", "vung": "giua-giua", "thay": "mat", "co_pct": [10, 90]}]}
    r = ss.solve_shot(spec, o, 9 / 16)
    assert not r["errors"] and len(r["cams"]) == 1 and "kelly" not in r["objs_used"]
    c = r["cams"][0]
    eye = (0.043, -0.246, sg.EYE * 1.0)
    assert math.dist(c["at"], eye) < 1e-3
    e = c["end"]
    assert abs(math.dist(e["at"][:2], c["at"][:2]) - 1.0) < 1e-3 and e["at"][2] == c["at"][2]
    assert math.dist(e["at"][:2], o["yeunu"]["xy"]) > math.dist(c["at"][:2], o["yeunu"]["xy"])     # lùi = xa yêu nữ hơn
    assert abs(sg.look(e["at"], e["aim"])[0] - sg.look(c["at"], c["aim"])[0]) < 0.01                # giữ hướng nhìn (tọa độ làm tròn 3–4 số lẻ)
    assert "co_pct" not in ss.end_spec(spec)["thanh_phan"][0] and ss.end_spec(spec)["co"] is None
    assert ss.move_errors({"kieu": "xoay", "m": 1}) and ss.move_errors({"kieu": "lui", "m": 0})


def test_end_spec_copy_in_tool_matches_solver():
    import importlib.util
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "stage_grid.py")
    spec_ = importlib.util.spec_from_file_location("stage_grid_tool2", p)
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    assert mod.ss_end_spec(SPEC) == ss.end_spec(SPEC)
