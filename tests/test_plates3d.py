"""GĐ-E0b: 3D place -> background plates (core/plates3d.py + tools/render_plates.py). The Dashboard side is tested with a fake Blender;
the real Blender script runs when BPY_PYTHON points to a Python with the `bpy` module (pip install bpy==5.0.1, same as Blender 5.0.1)."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

from core import assets, plates3d
from core.db import connect


def fake_blender(plates=("eye_000", "high_045"), code=0, stderr=""):
    """A stand-in for `blender -b -P render_plates.py`: writes plates + manifest like the real script."""
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        cfg = json.load(open(cmd[-1], encoding="utf-8"))
        items = []
        if code == 0:
            for k, n in enumerate(plates):
                img = Image.new("RGBA", (64, 36), (0, 0, 0, 0 if cfg["sky"]["mode"] == "C" else 255))   # sky (transparent for C)
                img.paste((120 + k, 130, 140, 255), (0, 18, 64, 36))                                     # ground/buildings
                img.save(os.path.join(cfg["out_dir"], f"plate_{n}.png"))
                angle = "high_angle" if n.startswith("high") else "eye_level"
                items.append({"name": n, "angle": angle, "file": f"plate_{n}.png", "render_sec": 1.5,
                              "set_analysis": {"camera": "high" if angle == "high_angle" else "eye", "horizon_y": 0.5,
                                               "camera_height_m": 1.6, "ground": [[0, .5], [1, .5], [1, 1], [0, 1]], "landmarks": []}})
            with open(os.path.join(cfg["out_dir"], "manifest.json"), "w", encoding="utf-8") as f:
                json.dump({"model": {"size_mb": 1.0, "triangles": 36, "import_sec": 0.1}, "plates": items, "engine": "BLENDER_EEVEE",
                           "scale_factor": 0.01, "sky": cfg["sky"], "warnings": []}, f)
        return subprocess.CompletedProcess(cmd, code, stdout="[plates] done", stderr=stderr)
    run.calls = calls
    return run


class Plates3DTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.model = os.path.join(self.dir, "model 3D", "thap dong ho.glb")
        os.makedirs(os.path.dirname(self.model))
        open(self.model, "wb").write(b"glTF")

    def test_models_in_the_folder_are_listed(self):
        open(os.path.join(self.dir, "model 3D", "notes.txt"), "w").write("x")
        self.assertEqual([m["name"] for m in plates3d.models(os.path.join(self.dir, "model 3D"))], ["thap dong ho.glb"])
        self.assertEqual(plates3d.models(os.path.join(self.dir, "none")), [])

    def test_official_export_four_folders_down_is_listed(self):
        """2026-09-29: Ingame_map_building/Ingame_map_building/ClockTower/T_30_XH_PCMAP_P16/asset.fbx was missed by the 3-level glob."""
        deep = os.path.join(self.dir, "model 3D", "Ingame_map_building", "Ingame_map_building", "ClockTower", "T_30_XH_PCMAP_P16")
        os.makedirs(deep)
        open(os.path.join(deep, "asset.fbx"), "wb").write(b"FBX")
        names = [m["name"] for m in plates3d.models(os.path.join(self.dir, "model 3D"))]
        self.assertIn(os.path.join("Ingame_map_building", "Ingame_map_building", "ClockTower", "T_30_XH_PCMAP_P16", "asset.fbx"), names)
        too_deep = os.path.join(self.dir, "model 3D", *["d"] * (plates3d.MODEL_DEPTH + 1))
        os.makedirs(too_deep)
        open(os.path.join(too_deep, "x.glb"), "wb").write(b"glTF")
        self.assertEqual(len(plates3d.models(os.path.join(self.dir, "model 3D"))), 2)

    def test_render_runs_blender_in_the_background_and_the_plates_wait_for_review_with_their_camera(self):
        run = fake_blender()
        cfg = plates3d.plan(self.model, os.path.join(self.dir, "out"), sky="C", real_height_m=32)
        manifest = plates3d.render(cfg, blender="/opt/blender/blender", run=run)
        self.assertEqual(run.calls[0][:4], ["/opt/blender/blender", "-b", "--factory-startup", "-P"])
        self.assertIn("36 tam giác", plates3d.summary(manifest))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "out", "render.log")))
        sky = os.path.join(self.dir, "sky.png")
        Image.new("RGB", (200, 100), (30, 90, 200)).save(sky)
        conn = connect(":memory:")
        res = plates3d.to_library(conn, manifest, "FF", "Tháp đồng hồ — Đảo Quân Sự", sky_picture=sky, look="ingame")
        self.assertEqual(res["added"], ["eye_000", "high_045"])
        place = assets.get(conn, res["asset_id"])
        self.assertEqual(place["images"], [])                                 # nothing is used before a person approves (G2)
        self.assertEqual({p["role"] for p in place["pending"]}, {"eye_level", "high_angle"})
        pixel = Image.open(place["pending"][0]["path"]).convert("RGB").getpixel((5, 5))
        self.assertEqual(pixel, (30, 90, 200))                                # sky C: the in-game sky behind the transparent sky
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM set_analyses").fetchone()[0], 2)   # exact camera, no paid reading

    def test_a_blender_failure_is_reported_with_the_end_of_its_log(self):
        cfg = plates3d.plan(self.model, os.path.join(self.dir, "out"))
        with self.assertRaises(plates3d.Plates3DError) as err:
            plates3d.render(cfg, blender="/opt/blender/blender", run=fake_blender(code=1, stderr="Error: bad file"))
        self.assertIn("bad file", str(err.exception))

    def test_without_a_graphics_card_the_render_is_retried_with_cycles(self):
        attempts = []

        def run(cmd, **kw):
            cfg = json.load(open(cmd[-1], encoding="utf-8"))
            attempts.append(cfg["engine"])
            if cfg["engine"] == "auto":
                return subprocess.CompletedProcess(cmd, -6, stdout="", stderr="Couldn't open libEGL.so.1")
            return fake_blender()(cmd, **kw)
        plates3d.render(plates3d.plan(self.model, os.path.join(self.dir, "out")), blender="/opt/blender/blender", run=run)
        self.assertEqual(attempts, ["auto", "cycles"])

    def test_plans_are_checked_before_starting_blender(self):
        with self.assertRaises(plates3d.Plates3DError):
            plates3d.plan(os.path.join(self.dir, "missing.glb"), self.dir)
        with self.assertRaises(plates3d.Plates3DError):
            plates3d.plan(self.model, self.dir, sky="B")                     # B needs a real HDRI file


@unittest.skipUnless(os.environ.get("BPY_PYTHON"), "set BPY_PYTHON to a Python with bpy==5.0.1 to run the real Blender script")
class RealBlenderTest(unittest.TestCase):
    def test_a_box_tower_in_centimetres_renders_level_plates_and_depth(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        model = os.path.join(d, "tower.glb")
        script = ("import bpy,sys\nbpy.ops.wm.read_factory_settings(use_empty=True)\n"
                  "bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,1500));bpy.context.active_object.scale=(600,600,3000)\n"
                  "bpy.ops.export_scene.gltf(filepath=sys.argv[-1],export_format='GLB')\n")
        subprocess.run([os.environ["BPY_PYTHON"], "-c", script, model], check=True, capture_output=True)
        cfg = plates3d.plan(model, os.path.join(d, "out"), sky="C", resolution=(160, 90), samples=2, presets=["eye_000", "high_045"])
        m = plates3d.render(cfg, blender=os.environ["BPY_PYTHON"], timeout=900)
        self.assertEqual(m["scale_factor"], 0.01)                             # 3000 units tall -> centimetres
        eye = m["plates"][0]
        self.assertAlmostEqual(eye["camera"]["pitch_deg"], 0, delta=0.5)     # level camera
        self.assertAlmostEqual(eye["set_analysis"]["horizon_y"], 0.5, delta=0.02)
        self.assertEqual(Image.open(os.path.join(d, "out", eye["file"])).mode, "RGBA")   # transparent sky for C
        self.assertTrue(os.path.exists(os.path.join(d, "out", eye["depth_file"])))


if __name__ == "__main__":
    unittest.main()


class GroundHeightsTests(unittest.TestCase):
    """2026-09-29: ground height under chosen points (surroundings spots) — a Blender run without a render."""
    def test_plan_carries_the_points_and_the_result_comes_back(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        model = os.path.join(d, "m.fbx")
        open(model, "wb").write(b"FBX")
        seen = {}

        def fake_render(cfg, blender=None, timeout=0):
            seen.update(cfg)
            return {"heights": [{"at": [p[0], p[1], 1.5], "on": "ground", "flat": True} for p in cfg["heights"]]}

        from unittest import mock
        with mock.patch.object(plates3d, "render", fake_render):
            out = plates3d.ground_heights(model, [(1, 2), [3, 4, 99]], os.path.join(d, "out"))
        self.assertEqual(seen["heights"], [[1, 2], [3, 4, 99]])
        self.assertEqual(seen["presets"], [])
        self.assertEqual([o["at"] for o in out], [[1, 2, 1.5], [3, 4, 1.5]])
        self.assertNotIn("heights", plates3d.plan(model, os.path.join(d, "o2")))
