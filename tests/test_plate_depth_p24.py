"""08/10 dự án #24 (Tháp Đồng Hồ, plaza_front, đêm + sương): raw.png đúng nhưng plate.png PHẲNG một màu. Ảnh độ sâu render với exposure
đêm (-1.4) và mã hóa sRGB, đọc như tuyến tính → ~127 m cho mọi điểm → sương che ~97 %. Fixture = raw/depth thật thu nhỏ 288×512
(cache data/_plates3d/cache/f62a7be6e594c35ed567, depth_range [0.1, 281.46])."""
import os
import tempfile
import unittest

from core import plate_env as E

HERE = os.path.join(os.path.dirname(__file__), "fixtures", "plate24")
RAW, DEPTH = os.path.join(HERE, "raw.png"), os.path.join(HERE, "depth.png")
RANGE = [0.1, 281.46]
ENV = {"time": "night", "weather": "fog"}


class PlateDepthTests(unittest.TestCase):
    def test_distances_are_real_metres(self):
        d = E.distance_map(DEPTH, RANGE, (288, 512), exposure=-1.4)
        ground = d[470, 40:250]                         # near ground at the bottom of the frame
        tower = d[200, 100:200]                         # the clock tower behind the plaza
        self.assertLess(float(ground.max()), 10.0)
        self.assertTrue(8.0 < float(tower.mean()) < 30.0, tower.mean())

    def test_finished_plate_keeps_the_place_and_the_old_reading_is_caught(self):
        out = tempfile.mkdtemp()
        good = E.finish_plate(RAW, os.path.join(out, "good.png"), ENV, depth_path=DEPTH, depth_range=RANGE, depth_exposure=-1.4)
        self.assertIsNone(E.plate_problem(good, RAW))
        flat = E.finish_plate(RAW, os.path.join(out, "flat.png"), ENV, depth_path=DEPTH, depth_range=RANGE, depth_exposure=0.0)
        self.assertIsNotNone(E.plate_problem(flat, RAW))      # the reading before the fix → flagged, never sent as the place


class LocationPackFinishTests(unittest.TestCase):
    def test_legacy_exposure_and_finish_record_the_problem(self):
        import shutil
        from core import location_pack as L
        benv = E.blender_env(ENV)
        self.assertAlmostEqual(L._legacy_depth_exposure(benv, {"camera": {}}), -1.4)
        dest = tempfile.mkdtemp()
        rec = {"raw": shutil.copy(RAW, dest), "depth": shutil.copy(DEPTH, dest), "depth_range_m": RANGE, "depth_exposure": -1.4}
        L._finish(rec, dest, {"key": "f62a7be6e594", "env": ENV})
        self.assertIsNone(rec["problem"])
        rec["depth_exposure"] = 0.0                     # what the plate looked like before the fix
        L._finish(rec, dest, {"key": "f62a7be6e594", "env": ENV})
        self.assertIsNotNone(rec["problem"])


class PlateOfLegacyTests(unittest.TestCase):
    def test_a_record_finished_before_the_fix_counts_as_missing(self):
        import json
        from core import location_pack as L
        data = tempfile.mkdtemp()
        plate = os.path.join(data, "plate.png")
        open(plate, "wb").write(b"x")
        path = L._index_path(data, 24)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rec = {"plate": plate, "depth": DEPTH, "depth_range_m": RANGE}
        json.dump({"257": rec}, open(path, "w"))
        self.assertIsNone(L.plate_of(data, 24, 257))                 # #24 index: depth but no depth_exposure → finished again
        json.dump({"257": dict(rec, depth_exposure=-1.4, problem=None)}, open(path, "w"))
        self.assertIsNotNone(L.plate_of(data, 24, 257))
        json.dump({"257": dict(rec, depth_exposure=-1.4, problem="phẳng")}, open(path, "w"))
        self.assertIsNone(L.plate_of(data, 24, 257))


if __name__ == "__main__":
    unittest.main()
