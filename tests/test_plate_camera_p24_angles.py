"""Người dùng duyệt ảnh #24 (09/10): máy 3D đặt sai so với ngôn ngữ máy của shot, model ảnh chép render sát nên ảnh sai.
 - shot 3 (ots MS, Kelly CÚI nhìn xuống giếng): máy cúi -10° nhìn ngang vào chân tháp → thấy cả mặt đồng hồ;
 - shot 5 (low WS): máy cao 0,45 m sát tường chắn ngang ngực → tường thành "tường cao";
 - shot 4 (low MCU): nền chỉ là bức tường áp sát.
core/plate_camera: độ cúi theo angle + hành động, khoảng cách theo size, máy thấp không áp sát tường (kiểm bằng tia trong Blender,
quyết bằng hàm thuần clearance_fix), lý do chọn số ghi vào `why`; cache key đổi khi máy đổi."""
import math
import unittest

from core import location_pack
from core import plate_camera as pc

SPOT = (-217.07, 116.0, 12.67)        # plaza_front (#24), mét cảnh
SHOT3 = {"angle": "ots", "size": "MS",
         "action": "Qua vai Kelly đang đứng cúi nhìn xuống giếng: một cái bóng đen lướt ngang qua miệng giếng",
         "blocking": "camera behind Kelly right shoulder, Kelly standing at the well rim, leaning slightly over it"}


def pitch(cam):
    d = [a - b for a, b in zip(cam["look_at"], cam["location"])]
    return math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))


class LookDownTests(unittest.TestCase):
    def test_ots_looking_down_into_the_well_tilts_down_clearly(self):
        out = pc.camera_for(SHOT3, SPOT, 0.0, 1.75)
        p = pitch(out["camera"])
        self.assertLessEqual(p, -25.0)
        self.assertGreaterEqual(p, -45.0)
        self.assertLess(out["horizon_y"], 0.0)                       # horizon (and the tower above it) out of the top of the frame
        self.assertLess(out["camera"]["location"][1], SPOT[1])        # still from behind (over the shoulder)
        self.assertIn("pitch", out["why"])

    def test_high_angle_looking_down_tilts_more_than_a_plain_high(self):
        plain = pitch(pc.camera_for({"size": "MS", "angle": "high"}, SPOT, 0.0, 1.75)["camera"])
        down = pitch(pc.camera_for({"size": "MS", "angle": "high", "action": "Kelly looks down at the ground"}, SPOT, 0.0, 1.75)["camera"])
        self.assertLess(down, plain - 3)
        self.assertGreaterEqual(down, -45.0)

    def test_negated_or_missing_angle_keeps_the_old_camera(self):
        old = pc.camera_for({"size": "MS", "angle": "ots"}, SPOT, 0.0, 1.75)["camera"]
        neg = pc.camera_for({"size": "MS", "angle": "ots", "action": "Kelly không nhìn xuống, nhìn thẳng"}, SPOT, 0.0, 1.75)["camera"]
        self.assertEqual(old, neg)
        # no angle: eye-level default, the look-down words do not move the camera (said in `why`)
        noangle = pc.camera_for({"size": "MS", "action": "cúi nhìn xuống giếng"}, SPOT, 0.0, 1.75)
        self.assertEqual(noangle["camera"], pc.camera_for({"size": "MS"}, SPOT, 0.0, 1.75)["camera"])
        self.assertIn("angle", noangle["why"].get("pitch", ""))


class DistanceTests(unittest.TestCase):
    def test_distance_grows_with_the_size(self):
        d = [pc.camera_for({"size": s}, SPOT, 0.0, 1.75)["distance_m"] for s in ("CU", "MCU", "MS", "WS", "EWS")]
        self.assertEqual(d, sorted(d))
        self.assertGreater(d[3], d[2] * 1.5)
        self.assertIn("distance", pc.camera_for({"size": "WS"}, SPOT, 0.0, 1.75)["why"])


class LowCameraTests(unittest.TestCase):
    def test_low_wide_camera_is_not_at_ground_height_and_tilts_up_a_little(self):
        out = pc.camera_for({"size": "WS", "angle": "low"}, SPOT, 90.0, 1.75)
        cam = out["camera"]
        self.assertGreaterEqual(cam["location"][2] - SPOT[2], 0.8)   # not 0,45 m (a chest-high wall filled the frame)
        self.assertGreater(pitch(cam), 2.0)                            # still a low angle: looks up
        self.assertLess(pitch(cam), 15.0)
        self.assertLess(out["feet_y"], 1.0)                            # feet still in the WS frame

    def test_camera_inside_a_wall_moves_in_front_of_it_with_a_note(self):
        cam = pc.camera_for({"size": "WS", "angle": "low"}, SPOT, 90.0, 1.75)["camera"]
        to_cam = math.dist(cam["look_at"], cam["location"])
        fix = pc.clearance_fix(cam["location"], cam["look_at"], SPOT, 1.75, block_m=to_cam - 0.8)
        self.assertLess(math.dist(cam["look_at"], fix["location"]), to_cam - 0.8)   # in front of the wall face
        self.assertEqual(fix["look_at"], cam["look_at"])
        self.assertTrue(fix["notes"])

    def test_low_camera_behind_a_chest_high_wall_is_raised_over_it(self):
        cam = pc.camera_for({"size": "WS", "angle": "low"}, SPOT, 90.0, 1.75)["camera"]
        flat = math.hypot(cam["look_at"][0] - cam["location"][0], cam["look_at"][1] - cam["location"][1])
        fix = pc.clearance_fix(cam["location"], cam["look_at"], SPOT, 1.75, bg_m=flat + 0.8, bg_top_z=SPOT[2] + 1.25)
        self.assertGreaterEqual(fix["location"][2], SPOT[2] + 1.25 + 0.1)
        self.assertTrue(fix["notes"])
        tall = pc.clearance_fix(cam["location"], cam["look_at"], SPOT, 1.75, bg_m=flat + 0.8, bg_top_z=SPOT[2] + 6.0)
        self.assertEqual(tall["location"], list(cam["location"]))      # a house wall: never silently moved, but said
        self.assertTrue(tall["warnings"])
        free = pc.clearance_fix(cam["location"], cam["look_at"], SPOT, 1.75, bg_m=flat + 12.0, bg_top_z=SPOT[2] + 1.25)
        self.assertEqual((free["notes"], free["warnings"]), ([], []))


    def test_block_is_measured_from_the_character_not_from_the_aim_in_the_well(self):
        cam = pc.camera_for(SHOT3, SPOT, 0.0, 1.75)["camera"]
        body = [SPOT[0], SPOT[1], cam["location"][2]]
        seg = math.dist(body, cam["location"])
        clear = pc.clearance_fix(cam["location"], cam["look_at"], SPOT, 1.75, block_m=None, block_from=body)
        self.assertEqual(clear["location"], list(cam["location"]))
        wall = pc.clearance_fix(cam["location"], cam["look_at"], SPOT, 1.75, block_m=seg - 0.2, block_from=body)
        self.assertLess(math.dist(body, wall["location"]), seg - 0.2)

    def test_render_plates_can_load_the_pure_module_by_path(self):
        """tools/render_plates.py (inside Blender, no repo on sys.path) loads core/plate_camera.py by its file path."""
        import importlib.util
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "plate_camera.py")
        spec = importlib.util.spec_from_file_location("plate_camera_pure_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(callable(mod.clearance_fix))
        src = open(os.path.join(os.path.dirname(path), "..", "tools", "render_plates.py"), encoding="utf-8").read()
        self.assertIn('"core", "plate_camera.py"', src)
        self.assertIn("clearance_fix(", src)


class CacheKeyTests(unittest.TestCase):
    def test_cache_key_changes_when_the_camera_changes_and_why_is_not_part_of_it(self):
        entry = {"sha256": "abc", "real_height_m": 30}
        env = {"time": "night", "weather": "fog"}
        old = pc.camera_for({"size": "MS", "angle": "ots"}, SPOT, 0.0, 1.75)
        new = pc.camera_for(SHOT3, SPOT, 0.0, 1.75)
        k = lambda c: location_pack.cache_key(entry, c["camera"], env, (1152, 2048))  # noqa: E731
        self.assertNotEqual(k(old), k(new))
        self.assertNotIn("why", new["camera"])                         # the reasons go to meta.json, not into the key
        eye = pc.camera_for({"size": "MS"}, SPOT, 0.0, 1.75)           # an unchanged shot keeps its key (old cache still used)
        self.assertEqual(eye["camera"], {"name": "shot", "location": eye["camera"]["location"], "look_at": eye["camera"]["look_at"],
                                         "lens": 35, "angle": "eye_level"})


if __name__ == "__main__":
    unittest.main()
