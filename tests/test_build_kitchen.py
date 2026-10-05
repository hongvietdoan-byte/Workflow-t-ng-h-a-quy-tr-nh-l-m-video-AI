import importlib.util
import os
import unittest


class KitchenSpots(unittest.TestCase):
    def test_spots_inside_room(self):
        p = os.path.join(os.path.dirname(__file__), "..", "tools", "build_kitchen.py")
        spec = importlib.util.spec_from_file_location("bk", p)
        bk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bk)
        self.assertGreaterEqual(len(bk.SPOTS), 3)
        for name, sp in bk.SPOTS.items():
            x, y, z = sp["at"]
            self.assertTrue(0 < x < bk.W and 0 < y < bk.D, name)
            self.assertTrue(sp["label"], name)
