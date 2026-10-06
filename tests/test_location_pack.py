"""Kế hoạch V4 GĐ2 — location pack: time/weather (plate_env), the registry + cached renders shared by projects (location_pack). S14.9
(06/10): the green-screen composite (core/composite.py, core/plate_qc.py, tier-2 photo plates) was removed with the flag location_plates —
only the check that the image runner never takes that path stays."""
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from core import assets, location_pack, plate_env
from core.db import connect
from core.pipeline import Pipeline

W, H = 90, 160


def save(arr, path, mode="RGB"):
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8"), mode).save(path)
    return path


def plate_files(d, sky_transparent=True):
    """A tiny plate: ground in the lower half, a 'tower' stripe, transparent sky; a depth picture (ground near at the bottom); a
    'shadow' plate a bit darker around the feet."""
    rgba = np.zeros((H, W, 4), np.float32)
    rgba[H // 2:, :, :3] = (0.4, 0.4, 0.38)
    rgba[:, 40:50, :3] = (0.55, 0.5, 0.45)
    rgba[H // 2:, :, 3] = 1
    rgba[:, 40:50, 3] = 1
    if not sky_transparent:
        rgba[..., 3] = 1
    raw = save(rgba, os.path.join(d, "raw.png"), "RGBA")
    depth = np.zeros((H, W, 4), np.float32)
    ys = np.linspace(0, 1, H)[:, None]
    depth[..., 0] = depth[..., 1] = depth[..., 2] = np.where(ys > 0.5, (ys - 0.5) * 2 * 0.9, 0.05)
    depth[..., 3] = rgba[..., 3]
    depth[:, 40:50, :3] = 0.3
    dpath = save(depth, os.path.join(d, "depth.png"), "RGBA")
    return raw, dpath


class EnvTests(unittest.TestCase):
    def test_script_words_become_time_and_weather(self):
        self.assertEqual(plate_env.time_of({"time": "ĐÊM"}), "night")
        self.assertEqual(plate_env.time_of({"time": "chiều tà"}), "dusk")
        self.assertEqual(plate_env.weather_of({"weather": "storm"}), ("storm", None))
        weather, problem = plate_env.weather_of({"weather": "mưa axit"})
        self.assertEqual(weather, "clear")
        self.assertIn("không có trong danh sách", problem)                      # never guessed silently

    def test_night_and_bad_weather_use_a_transparent_sky_and_geometry_weather(self):
        night = plate_env.blender_env({"time": "night", "weather": "snowfall"})
        self.assertEqual(night["sky"], "C")
        self.assertGreater(night["weather"]["snow"], 0.5)
        self.assertLess(night["sky_extra"]["sun_strength"], 1.5)
        self.assertEqual(plate_env.blender_env({"time": "day", "weather": "clear"})["sky"], "A")

    def test_finish_paints_the_sky_and_lays_fog_by_distance(self):
        d = tempfile.mkdtemp()
        raw, depth = plate_files(d)
        clear = plate_env.finish_plate(raw, os.path.join(d, "c.png"), {"time": "night", "weather": "clear"})
        arr = np.asarray(Image.open(clear), np.float32) / 255
        self.assertLess(arr[5, 5].mean(), 0.3)                                  # night sky painted where the render was empty
        foggy = plate_env.finish_plate(raw, os.path.join(d, "f.png"), {"time": "day", "weather": "fog"}, depth_path=depth,
                                       depth_range=[0.1, 60])
        plain = plate_env.finish_plate(raw, os.path.join(d, "p.png"), {"time": "day", "weather": "clear"})
        f, p = (np.asarray(Image.open(x), np.float32) / 255 for x in (foggy, plain))
        near, far = H - 2, H // 2 + 2
        self.assertLess(abs(f[near, 5] - p[near, 5]).mean(), abs(f[far, 5] - p[far, 5]).mean())   # far ground more fogged

    def test_falling_weather_on_a_still(self):
        d = tempfile.mkdtemp()
        base = save(np.full((H, W, 3), 0.2, np.float32), os.path.join(d, "b.png"))
        out = plate_env.overlay_still(base, os.path.join(d, "r.png"), {"time": "day", "weather": "rain"}, seed=2)
        self.assertGreater((np.asarray(Image.open(out), np.float32) / 255).max(), 0.3)
        self.assertEqual(plate_env.overlay_still(base, os.path.join(d, "n.png"), {"time": "day", "weather": "clear"}),
                         os.path.join(d, "n.png"))
        self.assertTrue(plate_env.flash_times(10, seed=1))


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"ASSET_DIR": os.path.join(self.tmp, "assets")})
        self.env.start()
        self.p = Pipeline(connect())
        self.model = os.path.join(self.tmp, "tower.glb")
        with open(self.model, "wb") as f:
            f.write(b"glTF-fake")
        self.place = assets.create(self.p.conn, "FF", "location", "Tháp Đồng Hồ")
        buf = io.BytesIO()
        Image.new("RGB", (64, 36), (90, 90, 90)).save(buf, "PNG")
        assets.add_image(self.p.conn, self.place, "a.png", buf.getvalue())
        self.p.conn.execute("UPDATE asset_images SET status='approved'")
        self.p.conn.commit()
        location_pack.set_model3d(self.p.conn, self.place, self.model, {"plaza_front": {"at": [12.68, -19.0, 25.93], "facing": 0}})
        self.calls = []

    def tearDown(self):
        self.env.stop()

    def project(self, name):
        pid = self.p.create_project(name, aspect="9:16")
        for i, (size, weather) in enumerate((("MS", "clear"), ("WS", "clear"), ("CU", "rain")), 1):
            sid = self.p.create_scene(pid, i, f"s{i}")
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(
                {"size": size, "characters": ["KELLY"], "location_asset": self.place, "time": "ĐÊM", "weather": weather,
                 "image_prompt": "Kelly looks up"}), sid))
        self.p.conn.commit()
        return pid

    def fake_render(self, cfg, blender=None, timeout=0):
        self.calls.append(cfg)
        plates = []
        for c in cfg["cameras"]:
            raw, depth = plate_files(cfg["out_dir"] if os.path.isdir(cfg["out_dir"]) else (os.makedirs(cfg["out_dir"]) or cfg["out_dir"]))
            name = c["name"]
            os.replace(raw, os.path.join(cfg["out_dir"], f"plate_{name}.png"))
            os.replace(depth, os.path.join(cfg["out_dir"], f"depth_{name}.png"))
            plates.append({"name": name, "file": f"plate_{name}.png", "depth_file": f"depth_{name}.png", "depth_range_m": [0.1, 60],
                           "camera": {"lens_mm": c["lens"]}})
        return {"plates": plates, "out_dir": cfg["out_dir"]}

    def test_register_plan_render_once_and_share_the_cache(self):
        entry = location_pack.model3d(self.p.conn, self.place)
        self.assertEqual(entry["default_spot"], "plaza_front")
        self.assertEqual(len(entry["sha256"]), 64)
        pid = self.project("a")
        data = os.path.join(self.tmp, "projects")
        idx = location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        self.assertEqual(len(idx), 3)
        self.assertEqual(len(self.calls), 2)                                    # night-clear and night-rain: one run each
        self.assertTrue(all(c["only_cameras"] if "only_cameras" in c else c["presets"] == [] for c in self.calls))
        self.assertEqual(self.calls[0]["sky"]["mode"], "C")
        rec = location_pack.plate_of(data, pid, int(next(iter(idx))))
        self.assertTrue(os.path.exists(rec["plate"]))
        other = self.project("b")                                                # same cameras, another project
        location_pack.ensure_plates(self.p.conn, other, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        self.assertEqual(len(self.calls), 2)                                    # nothing rendered again

    @mock.patch.dict(os.environ, {"FEATURE_LOCATION_PLATES": "1"})       # an old env line: S14.9 removed the flag, it does nothing
    def test_the_image_runner_never_waits_for_a_plate_nor_composites_on_green(self):
        """S14.9 (06/10): location_plates removed — with a rendered plate on disk the shot still draws a normal picture (no wait, no
        green prompt, no composite), exactly as with the flag off."""
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        pid = self.project("d")
        data = os.path.join(self.tmp, "projects")
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()["id"]
        self.p.create_job(sid, "image_gen")
        location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        provider = MockImageProvider()
        runner = ImageRunner(self.p, provider, data)
        self.assertEqual(runner.submit_pending(pid), 1)                          # no wait for the plate
        prompt = next(iter(provider.prompts.values()))
        self.assertNotIn("#00FF00", prompt)
        os.makedirs(os.path.join(data, str(pid), "images"), exist_ok=True)
        runner.poll_once(pid)
        job = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='image_gen'", (sid,)).fetchone()
        self.assertEqual(job["state"], "succeeded")
        self.assertFalse(os.path.exists(os.path.join(data, str(pid), "images", f"job_{job['id']}_green.png")))


class DayLightTests(unittest.TestCase):
    """2026-09-29: a place's own daylight (official FF export) for clear-day plates only, and in the cache key only when set."""
    def test_day_light_only_for_clear_day(self):
        entry = {"light": {"day": {"sun_elevation": 50, "view_transform": "Standard", "sun_strength": 4.5}}}
        day = {"sky": "A", "sun_elevation": 35, "sky_extra": {"sun_strength": 2.5, "exposure": -0.5}}
        out = location_pack.day_light(day, entry)
        self.assertEqual(out["sun_elevation"], 50)
        self.assertEqual(out["sky_extra"], {"sun_strength": 4.5, "exposure": -0.5, "view_transform": "Standard"})
        night = {"sky": "C", "sun_elevation": 20, "sky_extra": {"sun_strength": 0.5}}
        self.assertEqual(location_pack.day_light(night, entry), night)
        self.assertEqual(location_pack.day_light(day, {}), day)

    def test_cache_key_changes_with_light_only_when_set(self):
        cam, env = {"location": [0, 0, 0]}, {"time": "day", "weather": "clear"}
        base = {"sha256": "x"}
        k0 = location_pack.cache_key(base, cam, env, (10, 10))
        self.assertEqual(k0, location_pack.cache_key(dict(base, light=None), cam, env, (10, 10)))
        self.assertNotEqual(k0, location_pack.cache_key(dict(base, light={"day": {"exposure": 0}}), cam, env, (10, 10)))
