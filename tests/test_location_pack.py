"""Kế hoạch V4 GĐ2 — location pack: time/weather (plate_env), compositing (composite), plate checks (plate_qc), the registry + cached
renders shared by projects (location_pack), and the image runner making green-screen pictures composited on the plate."""
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from core import assets, composite, location_pack, plate_env, plate_qc
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


def green_char(d, box=(30, 40, 60, 150)):
    img = np.zeros((H, W, 3), np.float32)
    img[:] = (0, 1, 0)
    x0, y0, x1, y1 = box
    img[y0:y1, x0:x1] = (0.9, 0.8, 0.1)                      # a yellow "tracksuit"
    return save(img, os.path.join(d, "green.png"))


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


class CompositeTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        raw, depth = plate_files(self.d, sky_transparent=False)
        self.plate = {"plate": raw, "depth": depth, "depth_range_m": [0.1, 60], "subject_box": [0.3, 0.2, 0.7, 0.95],
                      "distance_m": 6.0, "env": {"time": "day", "weather": "clear"}}

    def test_the_character_is_keyed_placed_and_the_background_kept(self):
        res = composite.composite(green_char(self.d), self.plate, os.path.join(self.d, "c.png"), mask_out=os.path.join(self.d, "m.png"))
        out = np.asarray(Image.open(res["path"]), np.float32) / 255
        mask = np.asarray(Image.open(res["mask"]), np.float32) / 255
        self.assertLess(out[..., 1].max() - np.maximum(out[..., 0], out[..., 2]).min(), 1.0)
        self.assertFalse(((out[..., 1] > 0.8) & (out[..., 0] < 0.2) & (out[..., 2] < 0.2)).any())   # no green left
        ys, xs = np.where(mask > 0.5)
        self.assertAlmostEqual(ys.max() / H, 0.95, delta=0.04)                 # feet on the camera's feet line
        self.assertAlmostEqual((xs.min() + xs.max()) / 2 / W, 0.5, delta=0.05)
        self.assertEqual(plate_qc.picture_score(res["path"], self.plate["plate"], res["mask"]), 1.0)

    def test_something_nearer_than_the_character_stays_in_front(self):
        self.plate["distance_m"] = 40.0                                         # the "tower" stripe (depth 0.3) is nearer
        res = composite.composite(green_char(self.d), self.plate, os.path.join(self.d, "c.png"), mask_out=os.path.join(self.d, "m.png"))
        self.assertGreater(res["occluded_share"], 0.05)

    def test_an_empty_green_picture_is_refused_with_a_reason(self):
        empty = save(np.tile(np.array([0, 1, 0], np.float32), (H, W, 1)), os.path.join(self.d, "e.png"))
        with self.assertRaises(composite.CompositeError):
            composite.composite(empty, self.plate, os.path.join(self.d, "x.png"))


class QcTests(unittest.TestCase):
    def test_a_redrawn_background_scores_low(self):
        d = tempfile.mkdtemp()
        raw, _ = plate_files(d, sky_transparent=False)
        other = np.random.RandomState(1).rand(H, W, 3).astype(np.float32)
        redrawn = save(other, os.path.join(d, "r.png"))
        self.assertEqual(plate_qc.picture_score(raw, raw), 1.0)
        self.assertLess(plate_qc.picture_score(redrawn, raw), plate_qc.THRESHOLD)


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

    def test_green_prompt_frames_and_lights_the_character_like_the_plate(self):
        pid = self.project("c")
        data = os.path.join(self.tmp, "projects")
        idx = location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        rec = next(iter(idx.values()))
        text = location_pack.green_prompt({"size": "MS"}, rec)
        self.assertIn("#00FF00", text)
        self.assertIn("mm lens", text)
        self.assertIn("moonlight", text)

    @mock.patch.dict(os.environ, {"FEATURE_LOCATION_PLATES": "1"})
    def test_the_image_runner_waits_for_the_plate_then_composites_the_green_picture(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        pid = self.project("d")
        data = os.path.join(self.tmp, "projects")
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()["id"]
        self.p.create_job(sid, "image_gen")
        tmp = self.tmp

        class GreenProvider(MockImageProvider):
            def download(self, task_id, dest_path):
                return green_char(os.path.dirname(dest_path) or tmp) and os.replace(os.path.join(os.path.dirname(dest_path), "green.png"),
                                                                                   dest_path) or dest_path

        provider = GreenProvider()
        runner = ImageRunner(self.p, provider, data)
        self.assertEqual(runner.submit_pending(pid), 0)                          # no plate yet: waits (not failed)
        location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (W, H), blender="x", render=self.fake_render)
        self.assertEqual(runner.submit_pending(pid), 1)
        prompt = next(iter(provider.prompts.values()))
        self.assertIn("#00FF00", prompt)
        self.assertNotIn("location", " ".join(r for r in next(iter(provider.references.values()))))
        os.makedirs(os.path.join(data, str(pid), "images"), exist_ok=True)
        runner.poll_once(pid)
        job = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='image_gen'", (sid,)).fetchone()
        self.assertEqual(job["state"], "succeeded")
        self.assertTrue(os.path.exists(location_pack.green_path(data, pid, job["id"])))
        out = np.asarray(Image.open(job["result_path"]), np.float32) / 255
        self.assertFalse(((out[..., 1] > 0.8) & (out[..., 0] < 0.2)).any())     # composited: no green backdrop left


class PhotoPlateTests(PackTests):
    """Tier 2: a place with no 3D model but a tagged in-game photo gives the plate (cropped to the frame, graded)."""
    def test_a_tagged_photo_becomes_the_plate(self):
        other = assets.create(self.p.conn, "FF", "location", "Forest Red")
        buf = io.BytesIO()
        Image.new("RGB", (320, 180), (120, 60, 40)).save(buf, "PNG")
        assets.add_image(self.p.conn, other, "p.png", buf.getvalue())
        self.p.conn.execute("UPDATE asset_images SET status='approved', role='eye_level' WHERE asset_id=?", (other,))
        self.p.conn.commit()
        pid = self.p.create_project("photo", aspect="9:16")
        sid = self.p.create_scene(pid, 1, "s1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"size": "MS", "location_asset": other, "time": "day"}), sid))
        self.p.conn.commit()
        data = os.path.join(self.tmp, "projects")
        self.assertTrue(location_pack.needs_plate(self.p.conn, pid, {"size": "MS", "location_asset": other}))
        added = location_pack.ensure_photo_plates(self.p.conn, pid, data, (W, H))
        rec = added[str(sid)]
        self.assertEqual(rec["tier"], 2)
        self.assertEqual(Image.open(rec["plate"]).size, (W, H))
        self.assertEqual(location_pack.plate_of(data, pid, sid)["tier"], 2)


if __name__ == "__main__":
    unittest.main()
