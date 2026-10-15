import importlib.util
import math
import os
import unittest


def _load():
    p = os.path.join(os.path.dirname(__file__), "..", "tools", "build_room_2_doors.py")
    spec = importlib.util.spec_from_file_location("room2", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Room2Doors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()

    def test_doors_inside_walls(self):
        self.assertEqual(self.m.door_problems(), [])

    def test_spots_inside_room_not_in_furniture(self):
        self.assertEqual(self.m.spot_problems(), [])
        for k in ("goc_nhin_kelly_2_cua", "kelly_giua_phong", "can_cua_1", "can_cua_2"):
            self.assertIn(k, self.m.SPOTS)
        self.assertIn(self.m.DEFAULT_SPOT, self.m.SPOTS)

    def test_pov_sees_both_doors_in_9_16(self):
        lo, hi = self.m.pov_span()
        half = self.m.hfov_deg(20) / 2                    # ống 20 mm của tools/preview_room_2_doors.py
        self.assertLess(max(abs(lo), abs(hi)), half - 3)

    def test_kelly_ws_sees_both_doors(self):
        from core import plate_camera
        sp = self.m.SPOTS["kelly_giua_phong"]
        cam = plate_camera.camera_for({"size": "WS"}, sp["at"], sp["facing"], 1.7, 9 / 16)["camera"]
        x, y, _ = cam["location"]
        self.assertTrue(0.2 < x < self.m.W - 0.2 and 0.2 < y < self.m.D - 0.2)   # máy trong phòng
        b = lambda a, p: math.degrees(math.atan2(p[0] - a[0], p[1] - a[1]))
        centre = b(cam["location"], cam["look_at"])
        half = self.m.hfov_deg(cam["lens"]) / 2
        for name in self.m.DOORS:
            x0, x1, y0, y1 = self.m.door_opening(name)
            pts = [(0.0, y0), (0.0, y1)] if self.m.DOORS[name]["wall"] == "west" else [(x0, self.m.D), (x1, self.m.D)]
            for p in pts:
                self.assertLess(abs((b(cam["location"], p) - centre + 180) % 360 - 180), half, name)

    def test_doors_swing_out_to_hall_not_into_room(self):
        for name, d in self.m.DOORS.items():
            for deg in (0, 45, 80, 90):
                tx, ty = self.m.leaf_tip(name, deg)
                if d["wall"] == "west":
                    self.assertLessEqual(tx, 0.0 + 1e-6, (name, deg))
                else:
                    self.assertGreaterEqual(ty, self.m.D - 1e-6, (name, deg))
            # đóng: mép tự do ở đầu kia của lối, trong lòng tường
            tx, ty = self.m.leaf_tip(name, 0)
            along = ty if d["wall"] == "west" else tx
            self.assertTrue(d["lo"] < along < d["hi"], name)

    def test_three_states_share_files_scheme(self):
        st = self.m.STATES
        self.assertEqual(set(st), {"A", "B", "C"})
        self.assertEqual(st["A"]["open"], {"cua_1": 0.0, "cua_2": 0.0})
        self.assertGreater(st["B"]["open"]["cua_1"], 0)
        self.assertEqual(st["B"]["open"]["cua_2"], 0.0)
        self.assertTrue(all(v > 0 for v in st["C"]["open"].values()))
        self.assertFalse(st["A"]["glow"])
        self.assertTrue(st["B"]["glow"] and st["C"]["glow"])


if __name__ == "__main__":
    unittest.main()
