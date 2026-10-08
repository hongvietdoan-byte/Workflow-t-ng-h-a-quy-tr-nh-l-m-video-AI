"""F2 (người dùng duyệt 09/10, docs/RA_SOAT_TRUOC_GEN_LAI_24_2026-10-08.md mục 1 hàng 2–3): nền 3D đúng trước khi gen (0 USD).

#24 shot 4: a "low" MCU (50 mm) camera 0,45 m above the ground, 0,97 m from the character, tilted 45° up — horizon_y 1,896 (sky
only) → flat → dropped → job 579 went out WITHOUT its render and the model guessed the well's height. Now:
- an upward camera keeps the horizon in the frame (raised, same distance, same aim); an impossible camera is said, not rendered;
- every 3D shot gets a same-axis WIDE render (same yaw/pitch, pulled back, wider lens) sent right after its own render, replacing the
  scene's one-for-all wide picture;
- a shot whose render is broken (flat / failed / camera impossible) is HELD with the reason (diag once per 10 minutes), never sent;
- a shot at a place without 3D keeps the old path.
Blender is faked (no real render in tests)."""
import json
import math
import os
import shutil
from unittest import mock

from core import location_pack, place_refs, plate_camera, scene_establish
from tests.test_plate_stale_kld6 import REAL_ENSURE, Base, OLD_FIELDS, plate_png

SHOT4 = {"size": "MCU", "angle": "low", "lens_mm": 50}
FEET4 = (-217.07, 116.0, 12.67)


def _dir(cam):
    d = [a - c for a, c in zip(cam["look_at"], cam["location"])]
    n = math.sqrt(sum(c * c for c in d))
    return [c / n for c in d]


class CameraTests(Base):
    def test_shot4_numbers_are_reproduced_then_reset(self):
        """Before F2 the camera was (-217.07, 116.97, 13.12) → (-217.07, 116.0, 14.1): 45° up, horizon 1.896 (only sky)."""
        before = plate_camera.horizon_y((-217.07, 116.97, 13.12), (-217.07, 116.0, 14.1), 50, 9 / 16)
        self.assertGreater(before, 1.0)
        cam = plate_camera.camera_for(SHOT4, FEET4, 0, 1.7)
        self.assertTrue(cam["fixes"] and "nâng máy" in cam["fixes"][0])
        self.assertIsNone(cam["problem"])
        self.assertTrue(0.0 <= cam["horizon_y"] <= 1.0)                  # the horizon is in the frame now
        loc, aim = cam["camera"]["location"], cam["camera"]["look_at"]
        self.assertGreaterEqual(loc[2] - FEET4[2], plate_camera.LOW_CAM_M)   # no longer 0,45 m off the ground
        self.assertAlmostEqual(aim[2], 14.097, places=2)                     # same aim → same framing
        self.assertAlmostEqual(cam["distance_m"], 0.97, places=2)
        tilt = math.degrees(math.atan2(aim[2] - loc[2], math.hypot(aim[0] - loc[0], aim[1] - loc[1])))
        self.assertLessEqual(tilt, plate_camera.MAX_LOW_TILT_DEG)

    def test_default_cameras_and_a_sky_shot_are_not_touched(self):
        for size in ("WS", "MLS", "MS", "MCU", "CU"):
            self.assertEqual(plate_camera.camera_for({"size": size}, (0, 0, 0), 0, 1.75)["fixes"], [], size)
        sky = plate_camera.camera_for(dict(SHOT4, start_frame="low angle looking up at the night sky"), FEET4, 0, 1.7)
        self.assertEqual(sky["fixes"], [])
        self.assertGreater(sky["horizon_y"], 1.0)

    def test_too_close_wide_lens_goes_back_along_the_axis(self):
        cam = plate_camera.camera_for({"size": "MS", "lens_mm": 14}, (0, 0, 0), 0, 1.75)
        self.assertGreaterEqual(cam["distance_m"], plate_camera.MIN_DIST_M["MS"] - 0.01)
        self.assertGreater(cam["camera"]["lens"], 14)
        with mock.patch.object(plate_camera, "MAX_LENS_MM", 20.0):
            bad = plate_camera.camera_for({"size": "MS", "lens_mm": 14}, (0, 0, 0), 0, 1.75)
        self.assertIn("không lùi được", bad["problem"])

    def test_every_3d_shot_plans_a_same_axis_wide(self):
        self.set_data(dict(OLD_FIELDS, plate_spot="plaza_front", size="MCU", angle="low", lens_mm=50))
        it = location_pack.plan(self.p.conn, self.pid)[0]
        shot, wide = it["camera"], it["wide"]["camera"]
        self.assertTrue(wide["wide"])
        for a, b in zip(_dir(shot), _dir(wide)):                          # same yaw AND pitch
            self.assertAlmostEqual(a, b, places=3)
        self.assertLess(wide["lens"], shot["lens"])
        self.assertGreaterEqual(wide["lens"], plate_camera.WIDE_MIN_LENS)
        far = lambda c: math.dist(c["location"], c["look_at"])          # noqa: E731
        self.assertGreater(math.dist(wide["location"], shot["look_at"]), far(shot))   # pulled back along the axis
        self.assertNotEqual(it["wide"]["key"], it["key"])
        self.assertTrue(it["camera_fixes"])                              # the low MCU of #24 is placed again here too


class SendTests(Base):
    def runner(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        self.provider = MockImageProvider()
        return ImageRunner(self.p, self.provider, self.data)

    def sent(self):
        row = self.p.conn.execute("SELECT sent_refs FROM jobs WHERE scene_id=?", (self.sid,)).fetchone()
        return json.loads(row["sent_refs"] or "[]")

    def test_wide_goes_with_the_render_and_replaces_the_scene_wide(self):
        self.render()
        rec = location_pack.index(self.data, self.pid)[str(self.sid)]
        self.assertTrue(os.path.exists(rec["wide"]["plate"]))
        est_png = plate_png(os.path.join(self.tmp, "establish.png"))
        est = {"path": est_png, "label": scene_establish.LABEL, "role": "location"}
        self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async") as ens, mock.patch.object(scene_establish, "reference", return_value=est):
            self.assertEqual(self.runner().submit_pending(self.pid), 1)
        ens.assert_not_called()
        sent = self.sent()
        roles = [s["role"] for s in sent]
        self.assertIn(place_refs.WIDE_ROLE, roles)
        self.assertEqual(roles.index(place_refs.WIDE_ROLE), roles.index(place_refs.ROLE) + 1)   # right after the shot's render
        self.assertTrue(any("WIDE same-axis" in s["label"] for s in sent))
        self.assertFalse(any(s["label"] == scene_establish.LABEL for s in sent))               # no one-for-all wide any more
        prompt = next(iter(self.provider.prompts.values()))
        self.assertIn("SAME camera direction", prompt)

    def test_old_index_without_wide_renders_it_first(self):
        self.render()
        path = os.path.join(self.data, str(self.pid), "plates", "index.json")
        idx = json.load(open(path, encoding="utf-8"))
        idx[str(self.sid)].pop("wide")
        json.dump(idx, open(path, "w", encoding="utf-8"))
        self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async") as ens:
            self.assertEqual(self.runner().submit_pending(self.pid), 0)
        ens.assert_called_once()

    def test_flat_render_holds_the_picture_and_says_it_once(self):
        with mock.patch.object(location_pack.plate_env, "plate_problem", return_value="nền 3D gần như MỘT MÀU"):
            self.render()
            self.p.create_job(self.sid, "image_gen")
            runner = self.runner()
            with mock.patch.object(place_refs, "ensure_async") as ens:
                self.assertEqual(runner.submit_pending(self.pid), 0)
                self.assertEqual(runner.submit_pending(self.pid), 0)
            ens.assert_not_called()
        self.assertEqual(self.provider.prompts, {})                       # nothing paid, nothing sent
        rows = self.p.conn.execute("SELECT message FROM diag_events WHERE code='plate_broken'").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("hỏng", rows[0]["message"])
        self.assertIn("chọn lại góc", rows[0]["message"])

    def test_impossible_camera_is_not_rendered_and_holds(self):
        self.set_data(dict(OLD_FIELDS, plate_spot="plaza_front", size="MS", lens_mm=14))
        with mock.patch.object(plate_camera, "MAX_LENS_MM", 20.0):
            self.render()
            self.assertEqual(self.renders, 0)
            self.p.create_job(self.sid, "image_gen")
            with mock.patch.object(place_refs, "ensure_async"):
                self.assertEqual(self.runner().submit_pending(self.pid), 0)
        codes = {r["code"] for r in self.p.conn.execute("SELECT code FROM diag_events")}
        self.assertTrue({"plate_camera", "plate_broken"} <= codes)

    def test_shot_without_3d_keeps_the_old_path(self):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"size": "WS", "characters": ["KELLY"], "image_prompt": "a street"}), self.sid))
        self.p.conn.commit()
        self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async") as ens:
            self.assertEqual(self.runner().submit_pending(self.pid), 1)
        ens.assert_not_called()
        self.assertFalse(any(s["role"] == place_refs.WIDE_ROLE for s in self.sent()))


class ScaleTests(Base):
    def test_scale_sentence_only_from_measured_props_near_the_spot(self):
        rec = {"camera_plan": {"subject": {"location": [0, 0, 0], "height_m": 1.7}}}
        entry = {"props": [{"name": "the well", "at": [1.0, 0.5, 0], "height_m": 0.85},
                           {"name": "the far tower", "at": [80, 0, 0], "height_m": 30}, {"name": "unmeasured", "at": [1, 1, 0]}]}
        s = place_refs.scale_sentence(rec, entry, {})
        self.assertIn("the well is 0.85 m tall — 50%", s)
        self.assertNotIn("tower", s)
        self.assertNotIn("unmeasured", s)
        self.assertEqual(place_refs.scale_sentence(rec, {}, {}), "")


class FixRoundTests(Base):
    """Phiên sửa F2 (09/10): lỗi tạm của Blender không giữ chờ vĩnh viễn, ngoại lệ không làm vòng render vô hạn, nút render lại."""
    def err_render(self, cfg, blender=None, timeout=0):
        self.renders += 1
        return {"error": "timeout", "plates": [], "out_dir": cfg["out_dir"]}

    def ensure(self, render):
        res = place_refs.resolution_of(self.p.project(self.pid))
        return REAL_ENSURE(self.p.conn, self.pid, self.data, self.tmp, res, blender="x", render=render)

    def state(self):
        d = self.data_of()
        return (place_refs.missing(self.p.conn, self.data, self.pid, self.sid, d),
                place_refs.broken(self.p.conn, self.data, self.pid, self.sid, d))

    def test_transient_failure_retries_after_10_minutes_then_holds_after_2_tries(self):
        clock = [1000.0]
        with mock.patch.object(location_pack, "_now", lambda: clock[0]):
            self.ensure(self.err_render)
            miss, bad = self.state()
            self.assertFalse(miss)                                        # lần 1: giữ chờ, có lý do
            self.assertTrue(bad)
            self.assertNotIn("forget_failures", bad)
            clock[0] += 601
            miss, bad = self.state()
            self.assertTrue(miss)                                         # cũ hơn 10 phút → thiếu → tự render lại
            self.assertIsNone(bad)
            self.ensure(self.err_render)
            self.assertEqual(self.renders, 2)
            clock[0] += 601
            miss, bad = self.state()
            self.assertFalse(miss)                                        # sau 2 lần: hỏng thật
            self.assertTrue(bad)
            self.ensure(self.err_render)
            self.assertEqual(self.renders, 2)                             # không render lại nữa

    def test_retry_button_forgets_only_this_shot(self):
        self.ensure(self.err_render)
        root = location_pack.cache_root(self.tmp)
        key = location_pack.index(self.data, self.pid)[str(self.sid)]["key"]
        self.assertTrue(os.path.exists(os.path.join(root, key, "failed.json")))
        other = os.path.join(root, "otherkey")
        os.makedirs(other)
        with open(os.path.join(other, "failed.json"), "w", encoding="utf-8") as f:
            json.dump({"reason": "x"}, f)
        self.p.create_job(self.sid, "image_gen")
        self.assertEqual([t[0] for t in place_refs.held_broken(self.p.conn, self.data, self.pid)], [self.sid])
        self.assertTrue(place_refs.retry_render(self.p.conn, self.data, self.pid, self.sid))
        self.assertFalse(os.path.exists(os.path.join(root, key, "failed.json")))
        self.assertTrue(os.path.exists(os.path.join(other, "failed.json")))
        self.assertEqual(self.state(), (True, None))
        self.assertEqual(place_refs.held_broken(self.p.conn, self.data, self.pid), [])

    def test_blender_exception_on_old_index_does_not_loop(self):
        from core import plates3d
        self.render()
        path = os.path.join(self.data, str(self.pid), "plates", "index.json")
        idx = json.load(open(path, encoding="utf-8"))
        wide_key = idx[str(self.sid)].pop("wide")["key"]
        json.dump(idx, open(path, "w", encoding="utf-8"))
        shutil.rmtree(os.path.join(location_pack.cache_root(self.tmp), wide_key))
        self.assertTrue(self.state()[0])

        def boom(cfg, blender=None, timeout=0):
            raise plates3d.Plates3DError("x")
        self.ensure(boom)                                                 # không ném ra
        self.assertEqual(self.state(), (False, None))                     # shot có nền hợp lệ: không giữ mãi

    def test_wide_keeps_the_previous_shot_slot(self):
        refs = [{"path": f"{i}.png", "role": "character"} for i in range(3)] + [{"path": "r.png", "role": place_refs.ROLE}]
        limit = 5
        out = place_refs.add_wide(refs, {"path": "w.png", "role": place_refs.WIDE_ROLE}, limit, reserve=1)
        self.assertLess(len(out), limit)                                  # runner: chain and len(refs) < limit → previous_scene

    def test_indoor_shot_gets_no_wide(self):
        from core import runner
        self.render()
        d = self.data_of()
        self.assertIsNotNone(place_refs.wide_for(self.p.conn, self.data, self.pid, self.sid, d))
        with mock.patch.object(runner, "indoor_spot", return_value="Kelly's bedroom"):
            self.assertIsNone(place_refs.wide_for(self.p.conn, self.data, self.pid, self.sid, d))

    def test_sky_words_are_whole_words_and_not_negated(self):
        self.assertFalse(plate_camera.wants_sky({"image_prompt": "city skyline, no sky"}))
        self.assertFalse(plate_camera.wants_sky({"image_prompt": "a skyscraper behind her"}))
        self.assertFalse(plate_camera.wants_sky({"image_prompt": "góc thấp, không thấy trời"}))
        self.assertTrue(plate_camera.wants_sky({"image_prompt": "looking up at the night sky"}))
        self.assertTrue(plate_camera.wants_sky({"start_frame": "ngước nhìn bầu trời"}))
