"""tools/tower_pack.py cameras / moves follow the registered model (2026-09-29: FFXN → official export, other spot names)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import tower_pack  # noqa: E402

OFFICIAL = {"anchor": [-217.07, 132.04, 30.0], "default_spot": "plaza_front",
            "spots": {"plaza_front": {"at": [-217.07, 116.0, 9.38]}, "level_9_4": {"at": [-220.1, 121.8, 9.38]},
                      "level_3_8": {"at": [-237.4, 122.6, 3.83]}}}
FFXN = {"anchor": [12.68, -31.13, 33.5], "default_spot": "plaza_front",
        "spots": {"plaza_front": {"at": [12.68, -19.0, 25.93]}, "lower_yard": {"at": [7.8, -6.6, 22.4]},
                  "level_26_0": {"at": [5.96, -20.9, 25.96]}}}


class TowerPackTests(unittest.TestCase):
    def test_official_model_without_ffxn_spot_names(self):
        cams = tower_pack.cameras(OFFICIAL)
        names = [c["name"] for c in cams]
        self.assertIn("eye_plaza_front_thap", names)
        self.assertIn("eye_plaza_front_nguoc", names)
        self.assertEqual(len([n for n in names if n.endswith("_nguoc")]), 3)
        tower = next(c for c in cams if c["name"] == "eye_plaza_front_thap")
        self.assertAlmostEqual(tower["look_at"][2], 26.5)            # anchor 30 − 3.5, not the FFXN 30 m
        moves = tower_pack.animations(OFFICIAL, False)
        self.assertEqual([m["name"] for m in moves], ["di_bo_vao", "vong_quanh_thap", "can_cau_len"])
        self.assertAlmostEqual(moves[2]["keys"][1]["look_at"][2], 32.5)

    def test_ffxn_heights_unchanged(self):
        moves = tower_pack.animations(FFXN, False)
        self.assertEqual(moves[1]["keys"][0]["look_at"][2], 32.0)
        self.assertEqual(moves[0]["keys"][2]["look_at"][2], 34.0)
        self.assertEqual(moves[2]["keys"][1]["look_at"][2], 36.0)
        self.assertTrue(any(c["name"].startswith("eye_lower_yard_") for c in tower_pack.cameras(FFXN)))   # covered spot views kept


if __name__ == "__main__":
    unittest.main()
