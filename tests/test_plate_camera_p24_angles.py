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


class _V:
    """Just enough of mathutils.Vector for tools/render_plates.clearance outside Blender."""
    def __init__(self, v):
        self.v = [float(c) for c in v]

    x = property(lambda s: s.v[0])
    y = property(lambda s: s.v[1])
    z = property(lambda s: s.v[2])
    length = property(lambda s: math.sqrt(sum(c * c for c in s.v)))

    def __iter__(self):
        return iter(self.v)

    def __add__(self, o):
        return _V([a + b for a, b in zip(self.v, o)])

    def __sub__(self, o):
        return _V([a - b for a, b in zip(self.v, o)])

    def __mul__(self, k):
        return _V([a * k for a in self.v])

    def normalized(self):
        n = self.length or 1.0
        return _V([a / n for a in self.v])


def _render_plates(ray_cast):
    """tools/render_plates.py loaded with a fake bpy whose scene.ray_cast is `ray_cast(origin, direction, distance)`."""
    import importlib.util
    import os
    import sys
    import types
    bpy = types.ModuleType("bpy")
    scene = types.SimpleNamespace(ray_cast=lambda dg, o, d, distance=1e30: ray_cast(_V(o), _V(d), distance))
    bpy.context = types.SimpleNamespace(scene=scene, evaluated_depsgraph_get=lambda: None)
    mu = types.ModuleType("mathutils")
    mu.Vector = _V
    old = {k: sys.modules.get(k) for k in ("bpy", "mathutils")}
    sys.modules.update(bpy=bpy, mathutils=mu)
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "render_plates.py")
        spec = importlib.util.spec_from_file_location("render_plates_p24_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in old.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


MISS = (False, None, None, None, None, None)


class ReviewFixTests(unittest.TestCase):
    """Rà độc lập nhánh P24 (09/10): 5 lỗi sửa kèm test đỏ → xanh."""

    def _cam(self, **extra):
        c = pc.camera_for({"size": "WS", "angle": "low"}, (0.0, 0.0, 0.0), 0.0, 1.75)["camera"]
        return dict(c, subject={"location": [0.0, 0.0, 0.0], "height_m": 1.75}, **extra)

    def test_1_moved_camera_reframes_the_subject_box(self):
        cam = self._cam()
        self.assertIsNone(location_pack.reframe(cam, {}, 9 / 16))
        near = [c * 0.5 for c in cam["location"][:2]] + [cam["location"][2]]
        rf = location_pack.reframe(cam, {"moved_from_m": cam["location"], "location_model": near}, 9 / 16)
        old = pc.subject_box(cam["location"], cam["look_at"], cam["lens"], 9 / 16, (0, 0, 0), 1.75)
        self.assertGreater(rf["subject_box"][3] - rf["subject_box"][1], old[3] - old[1])    # closer → the character is bigger
        self.assertLess(rf["distance_m"], math.hypot(*cam["location"][:2]))
        it = {"subject_box": old, "distance_m": 9.9}
        self.assertEqual(location_pack.frame_fields(it, {"reframed": rf})["subject_box"], rf["subject_box"])
        self.assertEqual(location_pack.frame_fields(it, {})["subject_box"], old)
        src = open(location_pack.__file__.replace("core", "tools").replace("location_pack.py", "render_plates.py"),
                   encoding="utf-8").read()
        self.assertIn("location_model", src)

    def test_2_a_ray_error_is_a_warning_not_a_crash(self):
        def boom(o, d, dist):
            raise RuntimeError("ray_cast exploded")
        rp = _render_plates(boom)
        warnings = []
        c = self._cam()
        out = rp.clearance(c, warnings)
        self.assertIn("skipped", out)
        self.assertTrue(any("ray_cast exploded" in w for w in warnings))

    def test_3_a_wall_right_at_the_character_is_reported_not_moved_into(self):
        cam = self._cam()
        fix = pc.clearance_fix(cam["location"], cam["look_at"], (0, 0, 0), 1.75, block_m=0.1,
                               block_from=[0, 0, cam["location"][2]])
        self.assertEqual(fix["location"], list(cam["location"]))
        self.assertTrue(fix["warnings"])
        self.assertEqual(fix["notes"], [])

    def test_4_looks_down_the_alley_and_camera_setup_do_not_tilt(self):
        self.assertFalse(pc.looks_down({"action": "she looks down the alley"}))
        self.assertFalse(pc.looks_down({"action": "Kelly looks down the dark street"}))
        self.assertFalse(pc.looks_down({"camera_setup": "camera looks down at her"}))
        self.assertTrue(pc.looks_down({"action": "she looks down the well"}))
        self.assertTrue(pc.looks_down({"action": "she looks down at the street below"}))

    def test_5_wide_is_only_warned_indoor_skips_background_and_top_ray_starts_above_the_hit(self):
        fix = pc.clearance_fix([0, 6, 1], [0, 0, 1], (0, 0, 0), 1.75, block_m=3.0, block_from=[0, 0, 1], move=False)
        self.assertEqual(fix["location"], [0.0, 6.0, 1.0])
        self.assertTrue(fix["warnings"])
        calls = []

        def wall(o, d, dist):                                        # a wall 1 m behind the character, 1,2 m high
            calls.append((list(o), list(d)))
            if d.z < -0.5:
                return (True, _V((o.x, o.y, 1.2)), None, 0, None, None)
            if abs(d.z) < 1e-6 and d.y < 0 and o.z < 1.4:
                return (True, _V((o.x, -1.0, o.z)), None, 0, None, None)
            return MISS
        rp = _render_plates(wall)
        c = self._cam()
        rp.clearance(dict(c), [])
        down = [o for o, d in calls if d[2] < -0.5]
        self.assertTrue(down)
        self.assertAlmostEqual(down[0][2], c["location"][2] + 3.0, places=3)   # where.z (camera height) + 3, not loc.z + 40
        calls.clear()
        out = rp.clearance(dict(c, indoor={"exposure": 1.5}), [])
        self.assertIsNone(out["background_m"])
        self.assertFalse([o for o, d in calls if d[2] < -0.5])


if __name__ == "__main__":
    unittest.main()
