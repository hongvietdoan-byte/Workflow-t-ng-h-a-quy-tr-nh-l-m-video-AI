"""15/10 (#31, người dùng: "rà soát lại hết… viết thành luật bao quát để mọi dự án sau không dính các lỗi này"):
 1. phòng nhỏ: máy + ảnh toàn cùng trục không lọt ra ngoài tường — tiến vào trước tường và mở ống rộng giữ khung; hết chỗ thì xoay quanh
    nhân vật; máy trong nhà không có trần phía trên = nằm ngoài phòng → nền hỏng (shot chờ);
 2. đêm / hoàng hôn / bình minh: nền tự nâng sáng, nền vẫn quá tối = hỏng;
 3. ảnh toàn cùng trục hỏng giữ shot (không còn "gửi thiếu ảnh toàn");
 4. một cảnh nhiều chỗ đứng / bối cảnh → báo ở cổng nền 3D (mỗi cảnh một sân khấu chung)."""
import json
import math
import os
import sqlite3
import tempfile
import unittest

import numpy as np
from PIL import Image

from core import location_pack, plate_env
from core import plate_camera as pc
from tests.test_plate_camera_p24_angles import _V, _render_plates

ROOM = (0.0, 5.0, 0.0, 4.5, 2.6)          # x0, x1, y0, y1, ceiling (phòng 2 cửa #31)


def room_ray(o, d, dist):
    """First wall / ceiling of ROOM hit by a ray that starts inside it (outside: nothing — the walls are seen from inside only)."""
    x0, x1, y0, y1, top = ROOM
    if not (x0 <= o.x <= x1 and y0 <= o.y <= y1 and o.z <= top):
        return (False, None, None, 0, None, None)
    best = None
    for axis, lo, hi in ((0, x0, x1), (1, y0, y1), (2, None, top)):
        dv = list(d)[axis]
        if abs(dv) < 1e-9:
            continue
        for plane in (lo, hi):
            if plane is None:
                continue
            t = (plane - list(o)[axis]) / dv
            if 1e-6 < t <= dist and (best is None or t < best):
                best = t
    if best is None:
        return (False, None, None, 0, None, None)
    return (True, o + d * best, None, 0, None, None)


class ClearanceLensTests(unittest.TestCase):
    def test_pulled_camera_widens_its_lens_to_keep_the_frame(self):
        fix = pc.clearance_fix([0, 4, 1], [0, 0, 1], (0, 0, 0), 1.75, block_m=2.3, block_from=[0, 0, 1], lens=24.0)
        left = math.dist(fix["location"], [0, 0, 1])
        self.assertAlmostEqual(left, 2.0, places=2)
        self.assertEqual(fix["lens"], pc.MIN_FIX_LENS_SHOT)                     # 24 × 2/4 = 12 → floored at 14
        half = pc.clearance_fix([0, 4, 1], [0, 0, 1], (0, 0, 0), 1.75, block_m=3.3, block_from=[0, 0, 1], lens=24.0)
        self.assertAlmostEqual(half["lens"], 24.0 * 3.0 / 4.0, delta=0.1)       # 3 m of 4 m left → 18 mm keeps the frame
        self.assertIn("giữ khung", fix["notes"][0])

    def test_no_room_is_flagged_for_the_orbit(self):
        fix = pc.clearance_fix([0, 4, 1], [0, 0, 1], (0, 0, 0), 1.75, block_m=0.4, block_from=[0, 0, 1], lens=24.0)
        self.assertTrue(fix["no_room"])
        self.assertEqual(fix["location"], [0.0, 4.0, 1.0])
        locked = pc.clearance_fix([0, 4, 1], [0, 0, 1], (0, 0, 0), 1.75, block_m=0.4, block_from=[0, 0, 1], move=False)
        self.assertFalse(locked["no_room"])

    def test_orbit_keeps_distance_and_height(self):
        loc, aim = pc.orbit([2, 0, 1.5], [0, 0, 1], (0, 0, 0), 90)
        self.assertAlmostEqual(loc[0], 0, places=3)
        self.assertAlmostEqual(loc[1], 2, places=3)
        self.assertEqual(loc[2], 1.5)
        self.assertEqual(aim, [0.0, 0.0, 1.0])


class SmallRoomBlenderTests(unittest.TestCase):
    """tools/render_plates._clearance with a fake Blender room (5 × 4,5 m, ceiling 2,6 m) — #31 shot 2: Kelly near the south-east
    corner, the camera behind her landed outside the room."""

    def setUp(self):
        self.rp = _render_plates(room_ray)

    def cam(self, loc, wide=False):
        return {"name": "k", "location": list(loc), "look_at": [4.6, 0.45, 0.9], "lens": 24.0, "indoor": {"exposure": 0.2},
                "subject": {"location": [4.6, 0.45, 0.0], "height_m": 1.7}, **({"wide": True} if wide else {})}

    def test_camera_with_no_room_behind_turns_round_the_character_into_the_room(self):
        c = self.cam([6.4, -0.55, 0.91])
        out = self.rp.clearance(c, [])
        self.assertIn("turned_deg", out)
        x0, x1, y0, y1, _ = ROOM
        self.assertTrue(x0 < c["location"][0] < x1 and y0 < c["location"][1] < y1, c["location"])
        self.assertFalse(out.get("outside"))
        self.assertFalse(out.get("unplaceable"))
        self.assertIn("look_at_model", {**out, "look_at_model": 1})              # set by the caller after the move

    def test_wide_is_pulled_inside_with_a_wider_lens(self):
        c = self.cam([2.6, 2.45, 1.0], wide=True)                                  # 2,8 m from her, inside the room
        c["location"] = [1.0, 4.05, 1.0]
        c["lens"] = 18.0
        far = self.cam([-1.4, 6.45, 1.0], wide=True)                              # pulled back through the north-west corner
        far["lens"] = 18.0
        out = self.rp.clearance(far, [])
        self.assertTrue(out.get("moved_from_m"))
        x0, x1, y0, y1, _ = ROOM
        self.assertTrue(x0 < far["location"][0] < x1 and y0 < far["location"][1] < y1, far["location"])
        self.assertLess(far["lens"], 18.0)
        self.assertGreaterEqual(far["lens"], pc.MIN_FIX_LENS_WIDE)

    def test_locked_camera_outside_the_room_is_reported_outside(self):
        c = dict(self.cam([6.4, -0.55, 0.91]), locked=True)
        out = self.rp.clearance(c, [])
        self.assertTrue(out.get("outside"))
        self.assertTrue(location_pack.camera_problem({"clearance": out}))


class DarkPlateTests(unittest.TestCase):
    def _plate(self, level, path):
        Image.fromarray(np.full((64, 36, 3), level, dtype=np.uint8)).save(path)

    def test_night_plate_is_lifted_day_is_not(self):
        rgb = np.full((10, 10, 3), 30 / 255.0)
        alpha = np.ones((10, 10))
        night = plate_env.lift_dark(rgb, alpha, {"time": "night", "weather": "cloudy"})
        self.assertAlmostEqual(float(night.mean()) * 255, plate_env.DARK_TARGET, delta=1.0)
        self.assertIs(plate_env.lift_dark(rgb, alpha, {"time": "day", "weather": "clear"}), rgb)
        very = plate_env.lift_dark(np.full((10, 10, 3), 5 / 255.0), alpha, {"time": "night", "weather": "clear"})
        self.assertAlmostEqual(float(very.mean()) * 255, 5 * plate_env.DARK_MAX_GAIN, delta=0.5)

    def test_too_dark_plate_is_a_problem(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "p.png")
            self._plate(25, p)
            self.assertIn("QUÁ TỐI", plate_env.plate_problem(p) or "")
            noisy = (np.random.default_rng(1).integers(40, 140, (64, 36, 3))).astype(np.uint8)
            Image.fromarray(noisy).save(p)
            self.assertIsNone(plate_env.plate_problem(p))

    def test_old_finish_is_redone_and_camera_rule_beats_a_cached_fine(self):
        self.assertEqual(plate_env.FINISH_VERSION, 2)
        rec = {"problem": None, "clearance": {"outside": True}}
        self.assertIn("NGOÀI phòng", location_pack._recheck_problem(rec, tempfile.gettempdir()))
        self.assertIsNone(location_pack.camera_problem({"clearance": {"warnings": ["x"]}}))


class SceneStageTests(unittest.TestCase):
    def test_a_scene_at_two_spots_is_reported(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE scenes (id INTEGER PRIMARY KEY, data TEXT)")
        for sid, sc in ((1, 2), (2, 2), (3, 3), (4, 3)):
            conn.execute("INSERT INTO scenes VALUES (?, ?)", (sid, json.dumps({"story_scene": sc})))
        items = [{"scene_id": 1, "idx": 5, "place": "Cổng Trời", "spot": "me_cung"},
                 {"scene_id": 2, "idx": 7, "place": "Cổng Trời", "spot": "trung_tam_me_cung"},
                 {"scene_id": 3, "idx": 10, "place": "Cổng Trời", "spot": "trung_tam_me_cung"},
                 {"scene_id": 4, "idx": 11, "place": "Cổng Trời", "spot": "trung_tam_me_cung"}]
        rep = location_pack.stage_report(conn, items)
        self.assertEqual([r["scene"] for r in rep], ["2"])
        words = location_pack.stage_words(rep[0])
        self.assertIn("me_cung (shot 5)", words)
        self.assertIn("trung_tam_me_cung (shot 7)", words)

    def test_autopilot_holds_at_the_plates_gate(self):
        src = open(os.path.join(os.path.dirname(location_pack.__file__), "autopilot.py"), encoding="utf-8").read()
        self.assertIn("_stage_hold(p, pid, items)", src)


if __name__ == "__main__":
    unittest.main()
