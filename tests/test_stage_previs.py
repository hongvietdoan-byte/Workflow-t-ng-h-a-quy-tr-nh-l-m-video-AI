"""Previs one-shot (tools/stage_previs.plan — thuần, không Blender): người nộm đi theo lối A* (vòng qua hàng rào), chạy đều giữ tổng
thời lượng kịch bản, máy bám nhân vật + kẹp tiêu cự, biến thể tư thế theo shot."""
import json
import math
import os
import shutil
import tempfile
import unittest

from tools import stage_previs as sp


def cell(i, j, **kw):
    c = {"cell": f"{i},{j}", "x": i + 0.5, "y": j + 0.5, "floor_z": 0.0, "top_z": 0.0, "status": "same"}
    c.update(kw)
    return c


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.rd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.rd, ignore_errors=True)
        cells = [cell(i, j, **({"covered": True, "top_z": 2.1, "top_group": "cay"} if i == 0 and j != -10 else {}))
                 for i in range(-10, 10) for j in range(-10, 10)]                   # hàng rào cột x=0, hở ở hàng y=-10
        objs = lambda x, y, prop, f: {"kelly": {"kind": "nguoi", "xy": [x, y], "facing": f, "prop": prop}}
        shots = [{"shot": 1, "spec": {"nhip": "a", "thanh_phan": [{"vat": "kelly", "vai": "chinh"}]}, "objs": objs(-5.5, 5.5, "KELLY_V0", 90),
                  "best": {"m": {"at": [-8.0, 5.5, 1.6], "aim": [-5.5, 5.5, 1.4], "lens": 32.0}}},
                 {"shot": 2, "spec": {"nhip": "b", "thanh_phan": [{"vat": "kelly", "vai": "chinh"}]}, "objs": objs(5.5, 5.5, "KELLY_V0", 270),
                  "best": {"m": {"at": [8.0, 5.5, 1.6], "aim": [5.5, 5.5, 1.4], "lens": 50.0}}},
                 {"shot": 3, "spec": {"nhip": "c", "thanh_phan": [{"vat": "kelly", "vai": "chinh"}]}, "objs": objs(5.5, 6.0, "KELLY_V1", 270),
                  "best": {"m": {"at": [8.0, 6.0, 1.0], "aim": [5.5, 6.0, 0.8], "lens": 35.0}}}]
        bl = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [-5.5, 5.5], "H": 1.7, "facing": 90}],
              "beats": {"a": {}, "b": {"kelly": {"at": [5.5, 5.5]}}, "c": {"kelly": {"at": [5.5, 6.0], "H": 1.19, "tu_the": "quy"}}}}
        for fn, d in (("v2.json", {"shots": shots}), ("answer.json", {"blocking": bl}), ("grid.json", {"cells": cells}),
                      ("inputs.json", {"shots": [{"shot": 1, "do_dai": "2.0 s"}, {"shot": 2, "do_dai": "3.0 s"}, {"shot": 3, "do_dai": "2.0 s"}]})):
            json.dump(d, open(os.path.join(self.rd, fn), "w", encoding="utf-8"))

    def test_routes_around_hedge_and_keeps_script_total(self):
        p = sp.plan(self.rd, uniform_run=True, lens_range=(24, 35))
        s = p["summary"]
        self.assertAlmostEqual(s["total_s"], 7.0, places=2)
        leg = s["paths"]["kelly"][0]
        self.assertTrue(leg["routed"])
        self.assertGreater(leg["m"], 20)                                 # vòng xuống chỗ hở y=-10, không xuyên thẳng 11 m
        keys = p["previs"]["people"][0]["keys"]
        self.assertTrue(any(k[2] < -8 for k in keys))                    # người nộm đi qua chỗ hở
        self.assertEqual(s["run_m_per_s"], s["paths"]["kelly"][0]["m_per_s"])

    def test_lens_clamped_and_camera_follows(self):
        p = sp.plan(self.rd, uniform_run=True, lens_range=(24, 35))
        lenses = [c[3] for c in p["previs"]["camera"]]
        self.assertTrue(all(24 <= x <= 35 for x in lenses))
        cam0 = p["previs"]["camera"][0]
        self.assertEqual(cam0[0], 0.0)
        self.assertAlmostEqual(cam0[1][0], -8.0, places=2)               # đầu cú máy = máy đo của shot 1
        yaw0 = math.degrees(math.atan2(cam0[2][0] - cam0[1][0], cam0[2][1] - cam0[1][1]))
        self.assertAlmostEqual(yaw0, 90.0, delta=1.0)                     # rà 16/10: hướng nhìn khung 0 = máy đo (chặn xoay hai chiều)
        self.assertLess(abs(p["previs"]["camera"][-1][1][0] - 8.0), 0.6)

    def test_camera_never_low_inside_hedge(self):
        p = sp.plan(self.rd, uniform_run=True)
        for t, at, aim, lens in p["previs"]["camera"]:
            if math.floor(at[0]) == 0 and -10 < math.floor(at[1]) <= 9:     # ô hàng rào (ngọn 2,1 m); ngoài lưới thử không có rào
                self.assertGreaterEqual(at[2], 2.1 + sp.HEDGE_CLEAR_M - 1e-6)

    def test_orbit_circles_subject_same_distance(self):
        a = sp.plan(self.rd, uniform_run=True, orbit=0.0)
        b = sp.plan(self.rd, uniform_run=True, orbit=120.0)
        self.assertEqual(b["summary"]["orbit_shots"], [1])                 # chỉ đoạn chạy (shot 1) được vòng
        keys = b["previs"]["people"][0]["keys"]
        T0 = b["summary"]["segment_s"][0]
        for (t, ca, aa, _), (_, cb, ab, _) in zip(a["previs"]["camera"], b["previs"]["camera"]):
            if 0.1 * T0 < t < 0.55 * T0:                                   # trước khi chuyển sang shot sau
                k = min(keys, key=lambda x: abs(x[0] - t))
                da, db = math.dist(ca[:2], k[1:3]), math.dist(cb[:2], k[1:3])
                self.assertAlmostEqual(da, db, delta=0.35)                 # cùng khoảng cách, chỉ đổi góc
                self.assertLess(math.dist(ab[:2], k[1:3]), 3.5)              # vẫn nhìn vào nhân vật
        mid = [(ca, cb) for t, ca, _, _ in a["previs"]["camera"] for t2, cb, _, _ in b["previs"]["camera"]
               if t == t2 and 0.45 * T0 < t < 0.55 * T0]
        self.assertTrue(mid and math.dist(mid[0][0][:2], mid[0][1][:2]) > 1.0)

    def rewrite(self, fn, fix):
        d = json.load(open(os.path.join(self.rd, fn), encoding="utf-8"))
        fix(d)
        json.dump(d, open(os.path.join(self.rd, fn), "w", encoding="utf-8"))

    def test_raised_floor_keeps_measured_camera_height(self):
        def raise_floor(g):
            for c in g["cells"]:
                if not c.get("covered"):
                    c["floor_z"] = 1.0
        self.rewrite("grid.json", raise_floor)
        cam0 = sp.plan(self.rd)["previs"]["camera"][0]
        self.assertAlmostEqual(cam0[1][2], 1.6, places=2)           # máy đo 1,6 m (so với O) — không bị hạ theo sàn ô
        self.assertAlmostEqual(cam0[2][2], 1.0 + sp.FOCUS_Z_M, places=2)  # shot chạy: nhìn ngực nhân vật trên sàn của nó

    def test_absent_person_closes_variant(self):
        def drop(v2):
            v2["shots"][1]["objs"] = {}
        self.rewrite("v2.json", drop)
        v = sp.plan(self.rd)["previs"]["people"][0]["variants"]
        self.assertEqual(v[0]["to"], 2.0)                             # vắng ở shot 2 (2–5 s) → ẩn, không gộp qua chỗ hở
        self.assertEqual(v[1]["from"], 5.0)

    def test_no_jump_when_main_subject_changes(self):
        def two(v2):
            v2["shots"][1]["objs"]["dich"] = {"kind": "nguoi", "xy": [-5.5, -5.5], "facing": 0, "prop": "DICH_V0"}
            v2["shots"][1]["spec"]["thanh_phan"] = [{"vat": "dich", "vai": "chinh"}]
            v2["shots"][1]["best"]["m"] = {"at": [-5.5, -8.0, 1.6], "aim": [-5.5, -5.5, 1.4], "lens": 32.0}
        self.rewrite("v2.json", two)
        p = sp.plan(self.rd)
        t1 = p["summary"]["segment_s"][0]
        at = min(p["previs"]["camera"], key=lambda c: abs(c[0] - t1))
        self.assertLess(abs(at[0] - t1), 0.2)
        self.assertLess(math.dist(at[1], [-5.5, -8.0, 1.6]), 0.8)       # đầu shot 2 = máy đã đo của shot 2 (neo vào địch, không vào Kelly)

    def test_ref_rules_checked_before_render(self):
        p = sp.plan(self.rd, duration=2.0)
        self.assertTrue(any("tối thiểu" in x for x in sp.ref_problems(p)))
        p = sp.plan(self.rd, res=(640, 1136))
        self.assertTrue(any("rộng" in x for x in sp.ref_problems(p)))

    def test_blend_same_subject_keeps_distance(self):
        p = sp.plan(self.rd, uniform_run=True, orbit=160)
        keys = p["previs"]["people"][0]["keys"]
        for t, at, _, _ in p["previs"]["camera"]:
            k = min(keys, key=lambda x: abs(x[0] - t))
            self.assertGreater(math.dist(at[:2], k[1:3]), 0.8)          # máy không lao qua đầu nhân vật lúc chuyển shot

    def test_line_of_sight_clears_hedge(self):
        p = sp.plan(self.rd, uniform_run=True, orbit=160)
        keys = p["previs"]["people"][0]["keys"]
        for t, at, _, _ in p["previs"]["camera"]:
            k = min(keys, key=lambda x: abs(x[0] - t))
            tz = k[3] + sp.FOCUS_Z_M
            d = math.dist(at[:2], k[1:3])
            for q in range(1, int(d / 0.25)):
                s_ = q * 0.25 / d
                if s_ >= 0.95:
                    break
                x, y = at[0] + (k[1] - at[0]) * s_, at[1] + (k[2] - at[1]) * s_
                if math.floor(x) == 0 and math.floor(y) != -10:          # ô rào (ngọn 2,1 m)
                    self.assertGreaterEqual(at[2] + (tz - at[2]) * s_, 2.1 - 0.35)

    def test_camera_turns_gently(self):
        fast = sp.plan(self.rd, uniform_run=True, orbit=160)["summary"]["max_cam_turn_deg_s"]
        calm = sp.plan(self.rd, uniform_run=True, orbit=0, extra={1: 3.0})["summary"]["max_cam_turn_deg_s"]
        self.assertLessEqual(max(calm, fast), sp.CAM_YAW_MAX_DEG_S + 1)  # người dùng 16/10: không quay gấp ở bất kỳ khung nào
        self.assertGreater(sp.plan(self.rd, extra={1: 3.0})["summary"]["total_s"], 9.9)

    def test_arc_blend_no_flip_when_opposite(self):
        # người dùng 16/10 "giây 9→10 máy văng tâm": hai đầu cung đối diện (~180°) quanh nhân vật → chiều cung không được đổi giữa khung
        def opposite(v2):
            v2["shots"][1]["best"]["m"] = {"at": [3.0, 5.5, 1.6], "aim": [5.5, 5.5, 1.4], "lens": 32.0}    # máy shot 2 ở phía TÂY
            v2["shots"][1]["objs"]["kelly"]["xy"] = [5.5, 5.5]
        self.rewrite("v2.json", opposite)
        cam = sp.plan(self.rd, uniform_run=True)["previs"]["camera"]
        steps = [math.dist(a[1][:2], b[1][:2]) / (b[0] - a[0]) for a, b in zip(cam, cam[1:])]
        keys = sp.plan(self.rd, uniform_run=True)["previs"]["people"][0]["keys"]
        v_subj = max(math.dist(a[1:3], b[1:3]) / max(b[0] - a[0], 1e-6) for a, b in zip(keys, keys[1:]))
        self.assertLess(max(steps), v_subj + 12.0)                        # không có cú nhảy vượt xa tốc độ nhân vật

    def test_rig_behind_left_follows_path_low(self):
        # người dùng 16/10: shot chạy trong mê cung → máy thấp sau lưng chếch trái (cảm giác lạc / mò đường), không bay cao
        p = sp.plan(self.rd, uniform_run=True, rig={1: "sau_trai"})
        keys = p["previs"]["people"][0]["keys"]
        T0 = p["summary"]["segment_s"][0]
        for t, at, aim, _ in p["previs"]["camera"]:
            if 0.2 * T0 < t < 0.45 * T0:
                k = min(keys, key=lambda x: abs(x[0] - t))
                self.assertLess(at[2] - k[3], 2.0)                           # ngang vai, không cần nâng qua rào
                self.assertLess(math.dist(at[:2], k[1:3]), 2.6)
                cell = (math.floor(at[0]), math.floor(at[1]))
                self.assertFalse(cell[0] == 0 and cell[1] != -10)            # máy không nằm trong ô hàng rào

    def test_rig_change_after_orbit_keeps_subject_in_frame(self):
        # người dùng 16/10 (#31 --orbit 60 --rig 7:sau_trai): máy vòng ngang hông shot trước → giàn sau lưng shot sau phải xoay ~180°;
        # trần xoay 60°/s trong cửa sổ chuyển cố định làm hướng nhìn tụt sau Kelly tới 128° (giây 3–7 không thấy Kelly). Ca thử:
        # orbit 160 đưa máy ra trước mặt → đổi sang giàn sau lưng = xoay ~180° (bản cũ lệch 30°)
        def run2(v2):
            v2["shots"][2]["objs"]["kelly"]["xy"] = [8.5, 9.0]                # shot 2 cũng chạy tiếp (5,5;5,5 → 8,5;9)
            v2["shots"][2]["best"]["m"] = {"at": [8.5, 6.5, 1.6], "aim": [8.5, 9.0, 1.4], "lens": 32.0}
        self.rewrite("v2.json", run2)
        p = sp.plan(self.rd, uniform_run=True, lens_range=(24, 35), orbit=160, rig={2: "sau_trai"}, extra={2: 2.0})
        keys = p["previs"]["people"][0]["keys"]

        def chest(t):
            for a, b in zip(keys, keys[1:]):
                if a[0] <= t <= b[0]:
                    u = (t - a[0]) / max(b[0] - a[0], 1e-9)
                    return [a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u, a[3] + (b[3] - a[3]) * u + sp.FOCUS_Z_M]
            return [keys[-1][1], keys[-1][2], keys[-1][3] + sp.FOCUS_Z_M]
        offs = []
        for t, at, aim, _ in p["previs"]["camera"]:
            v1, v2 = [a - b for a, b in zip(aim, at)], [a - b for a, b in zip(chest(t), at)]
            c = sum(x * y for x, y in zip(v1, v2)) / (math.hypot(*v1) * math.hypot(*v2) + 1e-9)
            offs.append(math.degrees(math.acos(max(-1.0, min(1.0, c)))))
        self.assertLess(max(offs), 20.0)                                    # Kelly luôn trong khung (khung dọc 28 mm ±20° ngang)
        self.assertLessEqual(p["summary"]["max_cam_turn_deg_s"], sp.CAM_YAW_MAX_DEG_S + 1)   # vẫn không quay gấp

    def test_capped_turn_orbits_camera_keeps_subject(self):
        # rà 16/10: trần xoay giữ hướng nhìn lại ở đầu shot sau (Kelly chạy 10 m/s qua góc) → Kelly trôi ra mép 44–60° → máy vòng quanh
        # nhân vật để ngực lệch ≤ FRAME_KEEP_DEG; khung 0 vẫn đúng máy đo (bản cũ lệch tối đa 79–115°)
        for kw in ({}, {"orbit": 160}):
            p = sp.plan(self.rd, uniform_run=True, **kw)
            keys = p["previs"]["people"][0]["keys"]
            for t, at, aim, _ in p["previs"]["camera"]:
                k = min(keys, key=lambda x: abs(x[0] - t))
                if abs(k[0] - t) > 0.02:
                    continue
                y_aim = math.atan2(aim[0] - at[0], aim[1] - at[1])
                y_ch = math.atan2(k[1] - at[0], k[2] - at[1])
                self.assertLess(abs(math.degrees((y_ch - y_aim + math.pi) % (2 * math.pi) - math.pi)), 20.0)
            self.assertLessEqual(p["summary"]["max_cam_turn_deg_s"], sp.CAM_YAW_MAX_DEG_S + 1)

    def cam_steps(self, p):
        cam = p["previs"]["camera"]
        return [math.dist(a[1], b[1]) / (b[0] - a[0]) for a, b in zip(cam, cam[1:])]

    def test_hold_in_frame_ramps_no_jump(self):
        # rà 16/10: shot đứng yên có bố cục lệch có chủ ý (25°) → khi vào cửa sổ chuyển, giữ-khung không được bật đột ngột làm máy giật;
        # chuyển giữa hai nhân vật khác nhau không được nhảy từ vòng quanh A sang vòng quanh B. Mốc so: cùng kế hoạch tắt giữ-khung
        def no_hold():
            old = sp.FRAME_KEEP_DEG
            sp.FRAME_KEEP_DEG = 180.0
            try:
                return max(self.cam_steps(sp.plan(self.rd, uniform_run=True)))
            finally:
                sp.FRAME_KEEP_DEG = old

        def offset(v2):
            v2["shots"][1]["best"]["m"] = {"at": [8.0, 5.5, 1.6], "aim": [5.5, 4.33, 1.4], "lens": 32.0}   # lệch ~25° khỏi Kelly
        self.rewrite("v2.json", offset)
        p = sp.plan(self.rd, uniform_run=True)
        self.assertLess(max(self.cam_steps(p)), no_hold() * 1.15 + 1.0)

        def two(v2):
            v2["shots"][1]["objs"]["dich"] = {"kind": "nguoi", "xy": [-5.5, -5.5], "facing": 0, "prop": "DICH_V0"}
            v2["shots"][1]["spec"]["thanh_phan"] = [{"vat": "dich", "vai": "chinh"}]
            v2["shots"][1]["best"]["m"] = {"at": [-5.5, -8.0, 1.6], "aim": [-5.5, -5.5, 1.4], "lens": 32.0}
        self.rewrite("v2.json", two)
        self.assertLess(max(self.cam_steps(sp.plan(self.rd, uniform_run=True))), no_hold() * 1.15 + 1.0)

    def test_variants_switch_by_shot(self):
        p = sp.plan(self.rd)
        names = [(v["name"], v["from"]) for v in p["previs"]["people"][0]["variants"]]
        self.assertEqual([n for n, _ in names], ["KELLY_V0", "KELLY_V1"])     # shot 1–2 cùng tư thế gộp; quỳ ở shot 3
        self.assertAlmostEqual(names[1][1], 5.0, places=2)

    def test_run_profile_slows_at_corner_keeps_total(self):
        # người dùng 16/10 "giây 8–9 bị che": smoothstep cả đoạn làm giữa đoạn nhanh 1,5 × trung bình ngay khúc rẽ 90° → máy không kịp
        # đón, bị kéo ra sau góc rào. Đoạn chạy: tăng / giảm tốc đều hai đầu, chạy đều giữa, chậm lại quanh khúc rẽ gấp
        pts = [[0.0, 0.0], [0.0, 10.0], [10.0, 10.0]]                         # rẽ 90° ở giữa
        at = sp._run_profile(pts, 20.0)
        self.assertAlmostEqual(at(0.0), 0.0, places=6)
        self.assertAlmostEqual(at(1.0), 20.0, places=3)
        n = 400
        v = [(at((k + 1) / n) - at(k / n)) * n / 20.0 for k in range(n)]      # tốc độ tương đối (1 = trung bình)
        mid = min(range(n), key=lambda k: abs(at(k / n) - 10.0))
        straight = min(range(n), key=lambda k: abs(at(k / n) - 5.0))
        self.assertLess(max(v), 1.35)                                         # không vọt 1,5 × như smoothstep
        self.assertLess(v[mid], 0.8 * v[straight])                            # chậm lại ở khúc rẽ
        two45 = sp._run_profile([[0.0, 0.0], [0.0, 9.0], [1.0, 10.0], [10.0, 10.0]], 9.0 + math.sqrt(2) + 9.0)
        L2 = 18.0 + math.sqrt(2)
        v2 = [(two45((k + 1) / n) - two45(k / n)) * n / L2 for k in range(n)]
        mid2 = min(range(n), key=lambda k: abs(two45(k / n) - (9.0 + math.sqrt(2) / 2)))
        self.assertLess(v2[mid2], 0.7 * v2[straight])                          # A* 8 hướng: hai đỉnh 45° = một khúc rẽ 90°
        p = sp.plan(self.rd, uniform_run=True)
        self.assertAlmostEqual(p["summary"]["total_s"], 7.0, places=2)       # giữ tổng thời lượng kịch bản
        keys = p["previs"]["people"][0]["keys"]
        v_subj = max(math.dist(a[1:3], b[1:3]) / max(b[0] - a[0], 1e-6) for a, b in zip(keys, keys[1:]))
        self.assertLess(max(self.cam_steps(p)), 1.5 * v_subj + 1.0)            # rà 16/10: né rào không làm máy giật giữa hai phía

    def test_polyline_and_unwrap(self):
        pt, h = sp._polyline_at([[0, 0], [0, 2], [2, 2]], 3.0)
        self.assertEqual(pt, [1.0, 2.0])
        self.assertAlmostEqual(h, 90.0)
        self.assertEqual(sp._unwrap(350, 10), 370)
        self.assertEqual(sp._secs("4.7 s"), 4.7)


if __name__ == "__main__":
    unittest.main()
