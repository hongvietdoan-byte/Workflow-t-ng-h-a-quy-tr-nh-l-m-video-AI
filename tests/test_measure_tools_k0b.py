"""K0b — đo công cụ (tools/measure_tools_k0b.py): phần thuần — góc thân trên từ landmark, áp ngưỡng, bảng đúng/sai."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import measure_tools_k0b as m  # noqa: E402


def _lm(sh, hip, vis=0.9):
    """33 landmark giả (x, y, visibility) chuẩn hóa; vai 11/12 tại `sh`, hông 23/24 tại `hip`."""
    pts = [(0.5, 0.5, 0.0)] * 33
    pts[11] = pts[12] = (sh[0], sh[1], vis)
    pts[23] = pts[24] = (hip[0], hip[1], vis)
    return pts


def test_upright_is_zero():
    assert abs(m.torso_angle(_lm((0.5, 0.3), (0.5, 0.6)), 100, 100)) < 1e-6


def test_horizontal_is_ninety():
    assert abs(m.torso_angle(_lm((0.2, 0.5), (0.6, 0.5)), 100, 100) - 90) < 1e-6


def test_aspect_ratio_used():
    # dx 0.1 trên ảnh rộng 200 = 20 px; dy 0.2 trên cao 100 = 20 px → 45°
    assert abs(m.torso_angle(_lm((0.4, 0.3), (0.5, 0.5)), 200, 100) - 45) < 1e-6


def test_upside_down_counts_from_vertical():
    # vai dưới hông (lộn ngược) → 180°
    assert abs(m.torso_angle(_lm((0.5, 0.8), (0.5, 0.4)), 100, 100) - 180) < 1e-6


def test_low_visibility_none():
    assert m.torso_angle(_lm((0.5, 0.3), (0.5, 0.6), vis=0.1), 100, 100) is None
    assert m.torso_angle(None, 100, 100) is None


def test_3d_counts_depth_lean():
    pts = [(0.0, 0.0, 0.0, 0.0)] * 33
    for i in (11, 12):
        pts[i] = (0.0, -0.4, 0.4, 0.9)          # vai cao 0,4 m, ngả 0,4 m theo chiều sâu (2D thấy thẳng)
    for i in (23, 24):
        pts[i] = (0.0, 0.0, 0.0, 0.9)
    assert abs(m.torso_angle_3d(pts) - 45) < 1e-6
    assert m.torso_angle_3d(None) is None


def test_classify_threshold():
    assert m.classify(50, 35) == "nga"
    assert m.classify(20, 35) == "thang"
    assert m.classify(None, 35) == "khong_do"


def test_score_counts_and_unmeasured():
    rows = [{"nhan": "nga", "goc": 50}, {"nhan": "thang", "goc": 10}, {"nhan": "thang", "goc": 40},
            {"nhan": "nga", "goc": None}]
    s = m.score(rows, 35)
    assert s == {"nguong": 35, "do_duoc": 3, "khong_do": 1, "dung": 2, "sai": 1,
                 "bao_nham": 1, "bo_sot": 0}


def test_best_threshold_picks_min_errors():
    rows = [{"nhan": "nga", "goc": 60}, {"nhan": "nga", "goc": 45}, {"nhan": "thang", "goc": 30},
            {"nhan": "thang", "goc": 5}]
    best = m.best_threshold(rows, range(10, 80, 5))
    assert best["sai"] == 0 and 30 < best["nguong"] <= 45
