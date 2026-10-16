"""16/10 người dùng: ảnh nhìn từ trên của sân khấu đánh số / làm mờ theo nhịp (top_beats.png), mũi tên đi theo lối (không xuyên hàng
rào), mặt cắt bỏ mái (top_cut), người nộm đủ màu khi > 4 người. 0 USD, không Blender."""
import copy
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import stage_auto, stage_solver
from tools import stage_grid as tool


def cell(i, j, **kw):
    c = {"cell": f"{i},{j}", "x": i + 0.5, "y": j + 0.5, "floor_z": 0.0, "top_z": 0.0, "status": "same"}
    c.update(kw)
    return c


def grid(n=8, wall_x=None, gap=None, cover_h=2.0):
    """Lưới n×n từ (-n/2, -n/2); wall_x = cột hàng rào (mái thấp cover_h) chừa ô gap."""
    out = []
    for i in range(-n // 2, n // 2):
        for j in range(-n // 2, n // 2):
            if i == wall_x and j != gap:
                out.append(cell(i, j, covered=True, top_z=cover_h, top_group="cay"))
            else:
                out.append(cell(i, j))
    return out


BLOCKING = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [-2.5, 0.5], "H": 1.7, "facing": 90, "label": "Kelly"},
                        {"key": "dich", "kind": "nguoi", "at": [2.5, 0.5], "H": 1.8, "facing": 270, "label": "Địch"}],
            "beats": {"n1": {"kelly": {"at": [-2.5, 0.5], "den": [-1.5, 0.5]}},
                      "n2": {"kelly": {"at": [2.0, 0.5]}, "dich": {"at": [2.5, 0.5], "tu_the": "nam", "facing": 90}},
                      "n3": {"kelly": {"at": [2.0, 0.5]}, "dich": {"at": [2.5, 0.5], "tu_the": "nam", "facing": 90}}}}
SPECS = [{"shot": 1, "nhip": "n1"}, {"shot": 2, "nhip": "n2"}, {"shot": 3, "nhip": "n3"}]


def beats_of(blocking=BLOCKING, specs=SPECS):
    return {sp["nhip"]: stage_solver.objects_from_blocking(blocking, None, sp["nhip"]) for sp in specs}


class WalkTest(unittest.TestCase):
    def test_low_hedge_blocks_but_ceiling_walks(self):
        w = tool.walk_grid([cell(0, 0, covered=True, top_z=2.14, top_group="cay"), cell(1, 0, covered=True, top_z=3.0, top_group="nha"),
                            cell(2, 0, obstacle=True), cell(3, 0, status="level"),
                            cell(4, 0, covered=True, top_z=2.45, top_group="tuong"),
                            cell(5, 0, covered=True, top_z=9.0, top_group="cay")])
        self.assertNotIn((0, 0), w)          # hàng rào mê cung #31 (2,14 m, cây)
        self.assertIn((1, 0), w)             # trần nhà 3 m
        self.assertNotIn((2, 0), w)
        self.assertEqual(w[(3, 0)], 3.0)     # khác tầng: đi được nhưng đắt
        self.assertIn((4, 0), w)             # rà 16/10: trần hành lang phòng hai cửa #31 (2,45 m, 'tuong') — không phải hàng rào
        self.assertIn((5, 0), w)             # tán cây cao

    def test_path_goes_round_hedge_through_gap(self):
        w = tool.walk_grid(grid(wall_x=0, gap=-3))
        pts = tool.walk_path(w, (-2.5, 2.5), (2.5, 2.5))
        self.assertIsNotNone(pts)
        self.assertEqual(pts[0], [-2.5, 2.5])
        self.assertEqual(pts[-1], [2.5, 2.5])
        cells = {(int(x // 1), int(y // 1)) for x, y in pts}
        self.assertTrue(all(c in w or c in ((-3, 2), (2, 2)) for c in cells))
        self.assertTrue(any(y < -2 for _, y in pts))   # vòng xuống ô hở ở hàng -3, không cắt thẳng qua cột 0

    def test_no_path_when_closed(self):
        w = tool.walk_grid(grid(wall_x=0, gap=None))
        self.assertIsNone(tool.walk_path(w, (-2.5, 2.5), (2.5, 2.5)))

    def test_no_diagonal_corner_cut(self):
        w = {(0, 0): 1.0, (1, 1): 1.0, (1, 0): 1.0}
        pts = tool.walk_path(w, (0.5, 0.5), (1.5, 1.5))
        self.assertIsNotNone(pts)
        w2 = {(0, 0): 1.0, (1, 1): 1.0}
        self.assertIsNone(tool.walk_path(w2, (0.5, 0.5), (1.5, 1.5)))


class StationsTest(unittest.TestCase):
    def test_stationary_beats_merge_and_den_kept(self):
        st = tool.beat_stations({"blocking": BLOCKING, "shot_specs": SPECS}, beats_of())
        kelly = st["kelly"]
        self.assertEqual([s["shots"] for s in kelly], [[1], [2, 3]])
        self.assertEqual(kelly[0]["den"], [-1.5, 0.5])
        dich = st["dich"]
        self.assertEqual([s["shots"] for s in dich], [[1], [2, 3]])
        self.assertEqual(dich[1]["tu_the"], "nam")
        self.assertEqual(tool.shots_label([2, 3, 4]), "2–4")
        self.assertEqual(tool.shots_label([2, 5]), "2,5")

    def test_cut_view_bounds_and_min(self):
        v = tool.cut_view_for(beats_of())
        self.assertGreaterEqual(v["size_m"], tool.CUT_MIN_M)
        self.assertAlmostEqual(v["centre"][0], 0.0, places=3)
        far = copy.deepcopy(BLOCKING)
        far["objects"][1]["at"] = [30.0, 0.5]
        far["beats"]["n2"]["dich"]["at"] = [30.0, 0.5]
        far["beats"]["n3"]["dich"]["at"] = [30.0, 0.5]
        v = tool.cut_view_for(beats_of(far))
        self.assertGreaterEqual(v["size_m"], 32.5 + 2 * tool.CUT_MARGIN_M - 0.01)


class ColoursTest(unittest.TestCase):
    def test_five_people_five_colours(self):
        objs = [{"key": f"p{i}", "kind": "nguoi", "at": [float(i), 0.0], "H": 1.7, "facing": 0, "label": f"P{i}"} for i in range(5)]
        beats = {"": stage_solver.objects_from_blocking({"objects": objs})}
        props = [p for p in tool.blender_props(copy.deepcopy(beats)) if p["kind"] == "person"]
        self.assertEqual(len({tuple(p["rgb"]) for p in props}), 5)
        with mock.patch.object(stage_auto, "tool", return_value=tool):
            words = stage_auto.mannequin_colours(beats, {f"p{i}": f"P{i}" for i in range(5)})
        self.assertEqual(sorted(words.values()), [f"P{i}" for i in range(5)])   # 16/10 #31 cảnh 4: người thứ 5 không bị mất

    def test_more_people_than_colours_keeps_names(self):
        objs = [{"key": f"p{i}", "kind": "nguoi", "at": [float(i), 0.0], "H": 1.7, "facing": 0} for i in range(8)]
        beats = {"": stage_solver.objects_from_blocking({"objects": objs})}
        with mock.patch.object(stage_auto, "tool", return_value=tool):
            words = stage_auto.mannequin_colours(beats, {f"p{i}": f"P{i}" for i in range(8)})
        self.assertEqual(words["orange"], "P0 / P7")    # màu quay vòng: ghi cả hai, không bỏ im lặng


class DrawTest(unittest.TestCase):
    def setUp(self):
        self.rd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.rd, ignore_errors=True)
        dump = lambda fn, d: json.dump(d, open(os.path.join(self.rd, fn), "w", encoding="utf-8"), ensure_ascii=False)
        dump("stage.json", {"top_view": {"centre": [0.0, 0.0], "size_m": 10.0, "px": 300}})
        dump("answer.json", {"blocking": BLOCKING, "shot_specs": SPECS})
        dump("setups.json", {"beats": beats_of()})
        dump("grid.json", {"cells": grid(wall_x=0, gap=-3)})
        dump("v2.json", {"shots": [{"shot": 1, "best": {"m": {"at": [-3.0, -3.0, 1.5], "yaw": 45.0}}},
                                   {"shot": 2, "best": {"m": {"at": [40.0, 0.0, 1.5], "yaw": 270.0}}}]})

    def test_draws_png_without_blender_files(self):
        from PIL import Image
        path = tool.draw_beats(self.rd)
        self.assertTrue(path and os.path.exists(path))
        self.assertEqual(Image.open(path).size, (300, 300))

    def test_uses_cut_projection_when_present(self):
        from PIL import Image
        Image.new("RGB", (200, 200), (90, 90, 90)).save(os.path.join(self.rd, "top_cut.png"))
        json.dump({"centre": [0.0, 0.0], "size_m": 8.0, "px": 200, "cut_m": 2.2}, open(os.path.join(self.rd, "top_cut.json"), "w"))
        self.assertEqual(Image.open(tool.draw_beats(self.rd)).size, (200, 200))

    def test_moving_camera_drawn_start_to_end(self):
        from PIL import Image
        v2 = {"shots": [{"shot": 1, "spec": {"may": {"kieu": "lui", "m": 1.0}},
                         "best": {"m": {"at": [-2.0, -2.0, 1.5], "yaw": 45.0},
                                  "end": {"m": {"at": [-2.7, -2.7, 1.5], "aim": [0.0, 0.0, 1.2]}}}}]}
        json.dump(v2, open(os.path.join(self.rd, "v2.json"), "w", encoding="utf-8"))
        before = Image.open(tool.draw_beats(self.rd)).convert("RGB")
        v2["shots"][0]["best"].pop("end")
        json.dump(v2, open(os.path.join(self.rd, "v2.json"), "w", encoding="utf-8"))
        after = Image.open(tool.draw_beats(self.rd)).convert("RGB")
        # máy cuối (−2,7; −2,7) → quanh điểm ảnh (69, 231) với khung 10 m / 300 px: chỉ có tam giác máy cuối khi máy chạy
        box = (55, 217, 84, 246)
        self.assertNotEqual(list(before.crop(box).getdata()), list(after.crop(box).getdata()))

    def test_missing_files_none(self):
        os.remove(os.path.join(self.rd, "setups.json"))
        self.assertIsNone(tool.draw_beats(self.rd))

    def test_stage_auto_hook_never_raises(self):
        broken = mock.Mock()
        broken.draw_beats.side_effect = RuntimeError("PIL hỏng")
        logs = []
        with mock.patch.object(stage_auto, "tool", return_value=broken):
            self.assertIsNone(stage_auto.draw_beats(self.rd, logs.append))
        self.assertIn("top_beats", logs[0])
        with mock.patch.object(stage_auto, "tool", return_value=tool):
            self.assertTrue(stage_auto.draw_beats(self.rd).endswith("top_beats.png"))

    def test_sheet(self):
        from PIL import Image
        Image.new("RGB", (90, 160), (200, 200, 200)).save(os.path.join(self.rd, "v2_shot1_clay_raw.png"))
        v2 = {"shots": [{"shot": 1, "spec": {"co": "MS", "do_cao": "ngang"}, "objs": {"kelly": {"kind": "nguoi", "label": "Kelly"}},
                         "best": {"ok": True, "clay": "v2_shot1_clay_raw.png",
                                  "m": {"at": [0, 0, 1], "yaw": 0, "lens": 35, "obj": {"kelly": {"seen_pct": 80}}}}}]}
        json.dump(v2, open(os.path.join(self.rd, "v2.json"), "w", encoding="utf-8"))
        out = os.path.join(self.rd, "sheet.png")
        self.assertEqual(tool.stage_sheet(self.rd, "#1 cảnh 1", out, tile_h=200), out)
        self.assertGreaterEqual(Image.open(out).height, 50 + 200 + 30 * 3 + 16)   # ô hẹp: chú thích xuống dòng, không tràn ô bên


if __name__ == "__main__":
    unittest.main()
