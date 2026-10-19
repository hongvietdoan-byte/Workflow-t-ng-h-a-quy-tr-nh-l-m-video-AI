"""G8 (19/10, #31 maze): `model3d.stretch` — parts of a game export lower than in the game (Cổng Trời maze hedge 2,2 m in the file,
≈ 3 m in the in-game video) set to the in-game height at render time; in the plate cache key only when set."""
import ast
import os
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from core import location_pack, plates3d


def _stretch_fn():
    """The real tools/render_plates.stretch_objects, loaded by AST with a fake bpy / Vector (no Blender)."""
    tree = ast.parse((Path(__file__).resolve().parents[1] / "tools/render_plates.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "stretch_objects")

    class Vec:
        def __init__(self, xyz):
            self.x, self.y, self.z = xyz

    class Ident:                                       # matrix_world = identity: world == local
        def __matmul__(self, v):
            return Vec((v.x, v.y, v.z))

        def inverted(self):
            return self
    ns = {"bpy": NS(context=NS(view_layer=NS(update=lambda: None))), "Vector": Vec, "log": lambda *_: None}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "render_plates.py", "exec"), ns)

    def mesh_obj(name, zs, users=1):
        verts = [NS(co=Vec((i, 0.0, z))) for i, z in enumerate(zs)]
        data = NS(vertices=verts, users=users, update=lambda: None)
        data.copy = lambda: NS(vertices=[NS(co=Vec((v.co.x, v.co.y, v.co.z))) for v in verts], users=1, update=lambda: None)
        return NS(name=name, data=data, matrix_world=Ident())
    def scaled_obj(name, zs, k):
        o = mesh_obj(name, zs)

        class Scale:                                   # world = local * k (an FBX object at 0.01 scale), inverse divides
            def __init__(self, f):
                self.f = f

            def __matmul__(self, v):
                return Vec((v.x * self.f, v.y * self.f, v.z * self.f))

            def inverted(self):
                return Scale(1.0 / self.f)
        o.matrix_world = Scale(k)
        return o
    return ns["stretch_objects"], mesh_obj, scaled_obj


class StretchObjectsTests(unittest.TestCase):
    def setUp(self):
        self.stretch, self.mesh_obj, self.scaled = _stretch_fn()

    def test_hedge_above_the_stone_grows_to_the_game_height(self):
        """Stone 68,04–69,04 stays; leaves 69,04–70,24 (1,2 m) stretch so the top is 68,04 + 3,0."""
        fence = self.mesh_obj("PKK_OUT_Fence001_LOD0_plan", [68.04, 68.54, 69.04, 69.64, 70.24])
        warn = []
        done = self.stretch([{"object": "PKK_OUT_Fence001", "height_m": 3.0, "keep_below_m": 1.0}], [fence], warn)
        zs = [round(v.co.z, 3) for v in fence.data.vertices]
        self.assertEqual(zs, [68.04, 68.54, 69.04, 70.04, 71.04])
        self.assertEqual(done[0]["from_m"], 2.2)
        self.assertEqual(done[0]["to_m"], 3.0)
        self.assertEqual(warn, [])

    def test_object_scale_is_undone_when_writing_back(self):
        """rà G8: the FBX fence is a 0.01-scaled object — heights are judged in world metres, written back in its own units."""
        fence = self.scaled("PKK_OUT_Fence001", [6804.0, 6904.0, 7024.0], 0.01)
        self.stretch([{"object": "PKK_OUT_Fence001", "height_m": 3.0, "keep_below_m": 1.0}], [fence], [])
        self.assertEqual([round(v.co.z, 2) for v in fence.data.vertices], [6804.0, 6904.0, 7104.0])

    def test_without_keep_the_whole_object_scales_from_its_base(self):
        wall = self.mesh_obj("Wall_A", [10.0, 11.0, 12.0])
        self.stretch([{"object": "Wall", "height_m": 4.0}], [wall], [])
        self.assertEqual([round(v.co.z, 3) for v in wall.data.vertices], [10.0, 12.0, 14.0])

    def test_missing_object_is_said_not_skipped_silently(self):
        other = self.mesh_obj("Tree", [0.0, 5.0])
        warn = []
        done = self.stretch([{"object": "PKK_OUT_Fence001", "height_m": 3.0}], [other], warn)
        self.assertTrue(done[0]["missing"])
        self.assertIn("PKK_OUT_Fence001", warn[0])
        self.assertEqual([v.co.z for v in other.data.vertices], [0.0, 5.0])

    def test_a_shared_mesh_is_copied_before_stretching(self):
        fence = self.mesh_obj("PKK_OUT_Fence001", [0.0, 2.0], users=2)
        shared = fence.data
        self.stretch([{"object": "PKK_OUT_Fence001", "height_m": 3.0}], [fence], [])
        self.assertIsNot(fence.data, shared)
        self.assertEqual([v.co.z for v in shared.vertices], [0.0, 2.0])           # the other user keeps the file's height


class StretchPlanAndKeyTests(unittest.TestCase):
    SPEC = [{"object": "PKK_OUT_Fence001", "height_m": 3.0, "keep_below_m": 1.0, "why": "video in-game 17/10"}]

    def test_cache_key_changes_only_when_set_and_not_with_the_note(self):
        cam, env = {"location": [0, 0, 0]}, {"time": "day", "weather": "clear"}
        base = {"sha256": "x"}
        k0 = location_pack.cache_key(base, cam, env, (10, 10))
        self.assertEqual(k0, location_pack.cache_key(dict(base, stretch=[]), cam, env, (10, 10)))
        k1 = location_pack.cache_key(dict(base, stretch=self.SPEC), cam, env, (10, 10))
        self.assertNotEqual(k0, k1)
        noted = [dict(self.SPEC[0], why="khác")]
        self.assertEqual(k1, location_pack.cache_key(dict(base, stretch=noted), cam, env, (10, 10)))

    def test_plan_carries_the_render_part_only(self):
        model = Path(__file__)                                 # any existing file
        cfg = plates3d.plan(str(model), "out", stretch=location_pack.stretch_spec({"stretch": self.SPEC}))
        self.assertEqual(cfg["stretch"], [{"object": "PKK_OUT_Fence001", "height_m": 3.0, "keep_below_m": 1.0}])
        self.assertNotIn("stretch", plates3d.plan(str(model), "out"))


class StretchReachesEveryRenderTests(unittest.TestCase):
    """rà G8: the stage grid (K1 / sơ đồ / previs) and the white model measure the same stretched geometry as the plates."""
    M3 = {"path": __file__, "real_height_m": None, "anchor": [0, 0, 0], "spots": {"a": {"at": [1.0, 2.0, 3.0]}},
          "stretch": [{"object": "Fence001", "height_m": 3.0, "keep_below_m": 1.0, "why": "video"}]}

    def _stage_grid(self):
        import importlib.util
        path = Path(__file__).resolve().parents[1] / "tools" / "stage_grid.py"
        spec = importlib.util.spec_from_file_location("stage_grid_g8", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_stage_grid_cfgs_carry_the_stretch_only_when_set(self):
        sg = self._stage_grid()
        cfg = sg.k1_cfg(self.M3, "a", "out")
        self.assertEqual(cfg["stretch"], [{"object": "Fence001", "height_m": 3.0, "keep_below_m": 1.0}])
        self.assertNotIn("stretch", sg.k1_cfg(dict(self.M3, stretch=None), "a", "out"))

    def test_stage_grid_blender_main_applies_it(self):
        src = (Path(__file__).resolve().parents[1] / "tools" / "stage_grid.py").read_text(encoding="utf-8")
        body = src[src.index("def blender_main"):]
        self.assertLess(body.index("rp.normalise_scale"), body.index("rp.stretch_objects"))

    def test_whitebox_passes_it_to_plan(self):
        from unittest import mock
        from core import whitebox
        seen = {}

        def fake_render(cfg, timeout=0):
            seen.update(cfg)
            raise RuntimeError("stop")
        with mock.patch.object(plates3d, "render", fake_render):
            with self.assertRaises(RuntimeError):
                whitebox.render(self.M3, {"name": "x"}, "out")
        self.assertEqual(seen["stretch"][0]["height_m"], 3.0)


if __name__ == "__main__":
    unittest.main()
