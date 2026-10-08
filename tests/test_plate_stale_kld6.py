"""KLD-6 (người dùng duyệt 08/10, tổng hợp 3 lượt Khủng Long Đỏ): the 3D background of a shot is compared with the plan on EVERY path.

Khủng Long Đỏ #22: scenes 254–256 moved from `nha_lon_dong` to `bac_thang_giua`; the autopilot compares plan() with plates/index.json
but the hand redraw did not — the redraw went out with the OLD render and the old prompt words ("flat stone plaza, low red-roof house")
won over the render (1,80 USD). Now:
- a shot whose index record was made for another camera than plan() gives now is STALE: the picture waits while Blender renders the
  new background (0 USD), on the hand path too; a reference-only video send waits the same way;
- a picture already drawn on an old background holds the autopilot's video (said on the Dashboard); a person may still send it;
- after a spot move, the fields that still name the old place (location, image_prompt, blocking, spatial_state, action, motion prompt)
  are listed."""
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from core import assets, location_pack, place_refs
from core.db import connect
from core.pipeline import Pipeline

W, H = 90, 160
REAL_ENSURE = location_pack.ensure_plates
ON = {"FEATURE_PLACE_RENDER_REFS": "1"}

OLD = "nha_lon_dong"
NEW = "bac_thang_giua"
SPOTS = {"plaza_front": {"at": [12.68, -19.0, 25.93], "facing": 0, "label": "quảng trường trước tháp (cách 16 m)"},
         OLD: {"at": [30.0, 5.0, 3.0], "facing": 90, "label": "nhà lớn phía đông (hai tầng)"},
         "nha_do_nam": {"at": [-20.0, -40.0, 2.0], "facing": 180, "label": "dãy nhà mái đỏ phía nam"},
         NEW: {"at": [-25.0, 14.0, 3.9], "facing": 298,
               "label": "chân cầu thang nhiều tầng giữa nhà 3 tầng và Tháp Đồng Hồ (người dùng chọn 07/10, vòng xanh)"}}

# #22 scene 254 BEFORE the fix (backup manifest.before_kld_stairs_20261007_180118) — the words that beat the render
OLD_FIELDS = {"location": "Trước nhà lớn phía Đông, Tháp Đồng Hồ",
              "image_prompt": "Free Fire in-game 3D render, vertical frame, wide shot, two stylized young characters dancing side by side "
                              "on a flat stone plaza in front of a clock tower and low red-roof house, bright warm midday sunlight",
              "blocking": "Maxim frame-left, Kelly frame-right, both full body on open stone plaza, clock tower and red-roof house "
                          "visible behind, facing camera",
              "spatial_state": "Maxim stands frame-left and Kelly frame-right on the plaza, both mid-step with arms raised.",
              "action": "Maxim Khủng Long và Kelly Khủng Long đứng cạnh nhau trên sân đá trước nhà lớn, bắt đầu nhảy đồng đều theo "
                        "nhịp nhạc (đoạn 1)."}
# #22 scene 255 AFTER the fix (current database) — must not be reported
NEW_FIELDS = {"location": "Chân cầu thang nhiều tầng giữa nhà 3 tầng và Tháp Đồng Hồ",
              "image_prompt": "Free Fire in-game 3D render, two stylized characters dancing standing ON the paved stone landing at the "
                              "foot of one broad flight of stone steps: the clock tower stands at the top of the stairs left of centre. "
                              "BACKGROUND LOCK: copy its staircase, retaining walls, clock tower and three-storey house. Do NOT add "
                              "palm trees, grass fields, cars, red-roof houses or an open flat plaza, and do not use the wide place "
                              "picture's viewpoint.",
              "blocking": "Maxim Khủng Long frame-left, Kelly Khủng Long frame-right, same staircase background",
              "spatial_state": "Both still in matching dance positions, continuing to face camera on the stone landing at the foot of "
                               "the staircase.",
              "action": "Hai người tiếp tục nhảy đồng đều, chuyển sang đoạn nhạc 2 với động tác mạnh và dứt khoát hơn."}


def plate_png(path):
    Image.fromarray(np.full((H, W, 4), 120, np.uint8), "RGBA").save(path)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = mock.patch.dict(os.environ, {"ASSET_DIR": os.path.join(self.tmp, "assets"), **ON})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.p = Pipeline(connect())
        model = os.path.join(self.tmp, "tower.glb")
        with open(model, "wb") as f:
            f.write(b"glTF-fake")
        self.place = assets.create(self.p.conn, "FF", "location", "Tháp Đồng Hồ")
        buf = io.BytesIO()
        Image.new("RGB", (64, 36), (90, 90, 90)).save(buf, "PNG")
        assets.add_image(self.p.conn, self.place, "a.png", buf.getvalue())
        self.p.conn.execute("UPDATE asset_images SET status='approved'")
        self.p.conn.commit()
        location_pack.set_model3d(self.p.conn, self.place, model, SPOTS, default_spot="plaza_front")
        self.data = os.path.join(self.tmp, "projects")
        self.renders = 0
        self.pid = self.p.create_project("kld", aspect="9:16")
        self.sid = self.p.create_scene(self.pid, 1, "s1")
        self.set_data(dict(OLD_FIELDS, plate_spot=OLD))

    def set_data(self, data):
        base = {"size": "WS", "characters": ["KELLY"], "location_asset": self.place, "time": "day", "weather": "clear"}
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(dict(base, **data), ensure_ascii=False), self.sid))
        self.p.conn.commit()

    def data_of(self):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"])

    def fake_render(self, cfg, blender=None, timeout=0):
        self.renders += 1
        os.makedirs(cfg["out_dir"], exist_ok=True)
        plates = []
        for c in cfg["cameras"]:
            plate_png(os.path.join(cfg["out_dir"], f"plate_{c['name']}.png"))
            plates.append({"name": c["name"], "file": f"plate_{c['name']}.png", "camera": {"lens_mm": c["lens"]}})
        return {"plates": plates, "out_dir": cfg["out_dir"]}

    def render(self, resolution=None, *_, **__):
        res = resolution or place_refs.resolution_of(self.p.project(self.pid))
        return REAL_ENSURE(self.p.conn, self.pid, self.data, self.tmp, res, blender="x", render=self.fake_render)


class StaleTests(Base):
    def test_same_plan_is_not_stale_and_a_moved_spot_is(self):
        self.render()
        self.assertEqual(location_pack.stale_plates(self.p.conn, self.pid, self.data, place_refs.resolution_of(self.p.project(self.pid))), {})
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        stale = location_pack.stale_plates(self.p.conn, self.pid, self.data, place_refs.resolution_of(self.p.project(self.pid)))
        self.assertIn(self.sid, stale)
        self.assertEqual((stale[self.sid]["old_spot"], stale[self.sid]["new_spot"]), (OLD, NEW))
        self.assertIn("dựng lại", stale[self.sid]["why"])
        self.assertIn("0 USD", stale[self.sid]["why"])

    def test_a_record_made_at_another_size_is_judged_at_its_own_size(self):
        """tools/location_pack.py and old tests render at their own size: the record keeps the size, so it is not called stale (a
        render loop) just because the project's picture size is bigger."""
        self.render((W, H))
        rec = location_pack.index(self.data, self.pid)[str(self.sid)]
        self.assertEqual(rec.get("res"), [W, H])
        self.assertEqual(location_pack.stale_plates(self.p.conn, self.pid, self.data, (1152, 2048)), {})

    def test_moved_from_is_kept_in_the_index_after_the_new_render(self):
        self.render()
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        self.render()
        rec = location_pack.index(self.data, self.pid)[str(self.sid)]
        self.assertEqual((rec["spot"], rec.get("moved_from")), (NEW, OLD))
        self.render()                                                      # the same plan again: the move is still remembered
        self.assertEqual(location_pack.index(self.data, self.pid)[str(self.sid)].get("moved_from"), OLD)


class MentionTests(Base):
    def test_the_22_fields_before_the_fix_are_all_reported(self):
        entry = location_pack.model3d(self.p.conn, self.place)
        found = location_pack.spot_mentions(entry, OLD_FIELDS, OLD, NEW)
        self.assertEqual(set(found), {"location", "image_prompt", "blocking", "spatial_state", "action"})
        self.assertTrue(any("plaza" in w or "quảng trường" in w for w in found["image_prompt"]))
        self.assertTrue(any("mái đỏ" in w or "red" in w for w in found["image_prompt"]))
        self.assertIn("lớn", " ".join(found["action"]))

    def test_the_22_fields_after_the_fix_are_clean(self):
        """'Do NOT add … red-roof houses or an open flat plaza' is a negation, 'động tác' is not 'đông', 'Hai người' is not 'hai tầng'."""
        entry = location_pack.model3d(self.p.conn, self.place)
        found = location_pack.spot_mentions(entry, NEW_FIELDS, OLD, NEW)
        self.assertEqual(found, {})

    def test_the_motion_prompt_is_checked_too(self):
        entry = location_pack.model3d(self.p.conn, self.place)
        found = location_pack.spot_mentions(entry, NEW_FIELDS, OLD, NEW, motion="Slow push-in across the flat stone plaza.")
        self.assertIn("motion_prompt", found)

    def test_move_report_lists_the_fields_until_they_are_fixed(self):
        self.render()
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        report = location_pack.move_report(self.p.conn, self.pid, self.data, place_refs.resolution_of(self.p.project(self.pid)))
        self.assertEqual(len(report), 1)
        self.assertTrue(report[0]["stale"])                                # before the new render
        self.render()
        report = location_pack.move_report(self.p.conn, self.pid, self.data, place_refs.resolution_of(self.p.project(self.pid)))
        self.assertEqual([(r["old_spot"], r["new_spot"], r["stale"]) for r in report], [(OLD, NEW, False)])
        line = location_pack.move_words(report[0])
        for field in ("location", "image_prompt", "blocking", "spatial_state", "action"):
            self.assertIn(field, line)
        self.set_data(dict(NEW_FIELDS, plate_spot=NEW))
        self.assertEqual(location_pack.move_report(self.p.conn, self.pid, self.data,
                                                   place_refs.resolution_of(self.p.project(self.pid))), [])

    def test_no_move_no_report(self):
        self.render()
        self.assertEqual(location_pack.move_report(self.p.conn, self.pid, self.data,
                                                   place_refs.resolution_of(self.p.project(self.pid))), [])


class ImagePathTests(Base):
    """The hand redraw (a queued image job, no autopilot) — the path that lost 1,80 USD on #22."""
    def runner(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        self.provider = MockImageProvider()
        return ImageRunner(self.p, self.provider, self.data)

    def test_unchanged_plan_sends_at_once_with_its_render(self):
        """#22 round 3 (index key == plan key): nothing changes — no wait, no new render."""
        self.render()
        self.p.create_job(self.sid, "image_gen")
        n = self.renders
        with mock.patch.object(place_refs, "ensure_async") as ens:
            self.assertEqual(self.runner().submit_pending(self.pid), 1)
        ens.assert_not_called()
        self.assertEqual(self.renders, n)
        key = location_pack.index(self.data, self.pid)[str(self.sid)]["key"]
        self.assertTrue(any(key in r for r in next(iter(self.provider.references.values()))))

    def test_hand_redraw_after_a_spot_move_waits_for_the_new_render(self):
        self.render()
        old_key = location_pack.index(self.data, self.pid)[str(self.sid)]["key"]
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        self.p.create_job(self.sid, "image_gen")
        runner = self.runner()
        with mock.patch.object(place_refs, "ensure_async", return_value=True) as ens:
            self.assertEqual(runner.submit_pending(self.pid), 0)          # never sent with the old render
        ens.assert_called_once()
        notes = [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='plate_stale'")]
        self.assertTrue(notes and "nền 3D đã cũ" in notes[0] and OLD in notes[0] and NEW in notes[0])
        self.assertIn("image_prompt", notes[0])                            # the old words are named with the move
        self.render()                                                      # what ensure_async does (Blender, 0 USD)
        with mock.patch.object(place_refs, "ensure_async") as ens:
            self.assertEqual(runner.submit_pending(self.pid), 1)
        new_key = location_pack.index(self.data, self.pid)[str(self.sid)]["key"]
        self.assertNotEqual(new_key, old_key)
        refs = next(iter(self.provider.references.values()))
        self.assertTrue(any(new_key in r for r in refs))
        self.assertFalse(any(old_key in r for r in refs))
        sent = json.loads(self.p.conn.execute("SELECT sent_refs FROM jobs WHERE scene_id=?", (self.sid,)).fetchone()["sent_refs"])
        self.assertIn(new_key, [s.get("plate_key") for s in sent])         # the picture remembers which background it was drawn on


class VideoPathTests(Base):
    def approved_image(self, plate_key):
        jid = self.p.create_job(self.sid, "image_gen")
        sent = [{"label": "KELLY", "role": "character", "file": "k.png"}]
        if plate_key is not None:
            sent.append({"label": "Tháp Đồng Hồ", "role": place_refs.ROLE, "file": "plate.png", "plate_key": plate_key})
        self.p.conn.execute("UPDATE jobs SET state='approved', sent_refs=? WHERE id=?", (json.dumps(sent), jid))
        self.p.conn.commit()
        return jid

    def test_a_picture_drawn_on_an_old_background_is_found(self):
        self.render()
        old_key = location_pack.index(self.data, self.pid)[str(self.sid)]["key"]
        res = place_refs.resolution_of(self.p.project(self.pid))
        self.approved_image(old_key)
        self.assertEqual(place_refs.old_plate_images(self.p.conn, self.data, self.pid, res), {})
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        held = place_refs.old_plate_images(self.p.conn, self.data, self.pid, res)
        self.assertIn(self.sid, held)
        self.assertIn("nền 3D cũ", held[self.sid])
        self.assertTrue(any("nền 3D cũ" in w for w in place_refs.video_warnings(self.p.conn, self.data, self.pid)))

    def test_a_picture_without_a_recorded_background_is_not_held(self):
        """Pictures made before KLD-6 carry no plate key (all of #22): never held on a guess."""
        self.render()
        self.approved_image(None)
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        self.assertEqual(place_refs.old_plate_images(self.p.conn, self.data, self.pid,
                                                     place_refs.resolution_of(self.p.project(self.pid))), {})

    def test_reference_only_send_waits_for_the_new_render(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        self.render()
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        jid = self.p.create_job(self.sid, "video_gen")
        runner = VideoRunner(self.p, MockVideoProvider(), self.data)
        with mock.patch.object(VideoRunner, "_refs", return_value=True), \
                mock.patch.object(place_refs, "ensure_async", return_value=True) as ens:
            self.assertTrue(runner._wait(self.p.job(jid)))
        ens.assert_called_once()
        self.render()
        with mock.patch.object(VideoRunner, "_refs", return_value=True), \
                mock.patch.object(place_refs, "ensure_async") as ens:
            self.assertFalse(runner._wait(self.p.job(jid)))
        ens.assert_not_called()


class AutopilotTests(Base):
    def ctx(self):
        return mock.Mock(data_dir=self.data)

    def test_videos_phase_does_not_send_a_clip_of_a_picture_on_an_old_background(self):
        from core import autopilot, llm_io
        ctx = self.ctx()
        with mock.patch.object(llm_io, "ready_for_video", return_value=[{"scene_id": self.sid}]), \
                mock.patch.object(place_refs, "old_plate_images", return_value={self.sid: "ảnh khung đầu vẽ trên nền 3D cũ"}):
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._videos_phase(self.p, self.pid, ctx)
        self.assertEqual(w.exception.gate, "plates")
        self.assertIn("nền 3D cũ", str(w.exception))
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], 0)
        ctx.video_runner.submit_pending.assert_not_called()
        # the person looked and pressed "Tiếp tục": the same hold is not raised again (sending is theirs to decide)
        autopilot.set_gates(self.p, self.pid, {"waiting_for": "plates"})
        autopilot.resume(self.p, self.pid)
        with mock.patch.object(llm_io, "ready_for_video", return_value=[{"scene_id": self.sid}]), \
                mock.patch.object(place_refs, "old_plate_images", return_value={self.sid: "ảnh khung đầu vẽ trên nền 3D cũ"}), \
                mock.patch.object(autopilot, "_create_job") as create:
            try:
                autopilot._videos_phase(self.p, self.pid, ctx)
            except autopilot._Wait as e:                                   # any later gate is fine — not this one
                self.assertNotEqual(e.gate, "plates")
            except Exception:  # noqa: BLE001 - the rest of the phase runs on mocks
                pass
        create.assert_called()

    def test_plates_phase_holds_pictures_while_old_words_remain_after_a_move(self):
        from core import autopilot
        self.render()
        self.set_data(dict(self.data_of(), plate_spot=NEW))
        with mock.patch.object(location_pack, "ensure_plates", side_effect=lambda *a, **k: self.render()):
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._plates_phase(self.p, self.pid, self.ctx())
        self.assertEqual(w.exception.gate, "plates")
        self.assertIn("image_prompt", str(w.exception))
        self.set_data(dict(NEW_FIELDS, plate_spot=NEW))                    # fields fixed → no hold
        with mock.patch.object(location_pack, "ensure_plates", side_effect=lambda *a, **k: self.render()):
            self.assertIsNone(autopilot._plates_phase(self.p, self.pid, self.ctx()))


if __name__ == "__main__":
    unittest.main()
