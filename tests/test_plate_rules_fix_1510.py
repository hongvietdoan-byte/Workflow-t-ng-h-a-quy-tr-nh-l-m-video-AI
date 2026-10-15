"""Rà quy ước 7 nhánh p31-plate-rules (docs/handoff/RA_P31_PLATE_RULES_2026-10-15.md) — mỗi mục CAO/VỪA một test (Blender giả):
 CAO-1 ảnh toàn hỏng chỉ giữ shot thật sự GỬI ảnh toàn (shot trong nhà / máy Sân khấu 3D khóa không gửi → không giữ);
 CAO-2 ảnh toàn lỗi tạm được render lại theo giờ (không thả shot đi thiếu ảnh toàn);
 CAO-3 nền cache làm theo bản hoàn thiện cũ → autopilot vẫn chạy ensure_plates (refresh_due);
 VỪA-4 nút "↻ Render lại nền 3D" xóa cả lỗi của ảnh toàn khi shot bị giữ vì ảnh toàn;
 VỪA-7 shadow.png nâng sáng cùng mức với plate.png; đèn practical không nâng; "QUÁ TỐI" không áp nền ban ngày;
 chỗ đứng trong nhà: máy mang `indoor` sang Blender (luật "máy dưới trần phòng" mới chạy được)."""
import json
import os
import shutil
from unittest import mock

import numpy as np
from PIL import Image

from core import location_pack, place_refs, plate_env
from tests.test_plate_stale_kld6 import REAL_ENSURE, SPOTS, Base, plate_png

ROOM = {"at": [30.0, 5.0, 3.0], "facing": 90, "label": "phòng nhỏ 2 cửa", "indoor": {"exposure": 1.5}}


class _Fix(Base):
    def ensure(self, render):
        res = place_refs.resolution_of(self.p.project(self.pid))
        return REAL_ENSURE(self.p.conn, self.pid, self.data, self.tmp, res, blender="x", render=render)

    def state(self):
        d = self.data_of()
        return (place_refs.missing(self.p.conn, self.data, self.pid, self.sid, d),
                place_refs.broken(self.p.conn, self.data, self.pid, self.sid, d))

    def rec(self):
        return location_pack.index(self.data, self.pid)[str(self.sid)]

    def no_wide(self, cfg, blender=None, timeout=0):
        """Blender returns the shot cameras only (a lasting failure of every wide)."""
        out = self.fake_render(cfg, blender, timeout)
        wides = {c["name"] for c in cfg["cameras"] if c.get("wide")}
        out["plates"] = [p for p in out["plates"] if p["name"] not in wides]
        return out

    def drop_wide(self):
        """An index whose wide was never rendered (old record) + its cache gone."""
        path = os.path.join(self.data, str(self.pid), "plates", "index.json")
        idx = json.load(open(path, encoding="utf-8"))
        key = idx[str(self.sid)].pop("wide")["key"]
        json.dump(idx, open(path, "w", encoding="utf-8"))
        shutil.rmtree(os.path.join(location_pack.cache_root(self.tmp), key))


class WideHoldTests(_Fix):
    def test_outdoor_shot_is_held_by_a_broken_wide(self):
        self.ensure(self.no_wide)
        rec = self.rec()
        self.assertIn("giữ ảnh shot tới khi có ảnh toàn", rec.get("failed", ""))
        missing, broken = self.state()
        self.assertFalse(missing)
        self.assertIn("ảnh toàn", broken)

    def test_indoor_shot_never_sends_a_wide_so_is_not_held(self):
        location_pack.set_model3d(self.p.conn, self.place, location_pack.model3d(self.p.conn, self.place)["path"],
                                  dict(SPOTS, phong=ROOM), default_spot="plaza_front")
        self.set_data(dict(self.data_of(), plate_spot="phong"))
        it = location_pack.plan(self.p.conn, self.pid)[0]
        self.assertEqual(it["camera"]["indoor"], ROOM["indoor"])                 # the room reaches Blender (ceiling rule, exposure)
        self.assertFalse(location_pack.wide_sent(it["camera"]))
        self.ensure(self.no_wide)
        rec = self.rec()
        self.assertNotIn("failed", rec)
        self.assertTrue(rec.get("wide_failed"))                                  # kept as a note only
        self.assertEqual(self.state(), (False, None))
        self.assertIsNotNone(location_pack.plate_of(self.data, self.pid, self.sid))

    def test_locked_stage_camera_never_holds_on_its_wide(self):
        self.assertFalse(location_pack.wide_sent({"locked": True}))
        self.assertTrue(location_pack.wide_sent({"location": [0, 0, 0]}))


class WideRetryTests(_Fix):
    def test_temporary_wide_failure_is_rendered_again_then_sent(self):
        from core import plates3d
        self.render()
        self.drop_wide()

        def boom(cfg, blender=None, timeout=0):
            raise plates3d.Plates3DError("x")
        clock = [1000.0]
        with mock.patch.object(location_pack, "_now", lambda: clock[0]):
            self.ensure(boom)
            self.assertIn("giữ ảnh shot", self.rec()["failed"])
            clock[0] += location_pack.RETRY_AFTER_S + 1
            self.assertTrue(self.state()[0])                                     # retry due → asks for the render again
            before = self.renders
            self.ensure(self.fake_render)
            self.assertEqual(self.renders, before + 1)                           # the wide really went to Blender again
            rec = self.rec()
            self.assertNotIn("failed", rec)
            self.assertTrue(os.path.exists(rec["wide"]["plate"]))                # sent WITH its wide, never without it

    def test_wide_failure_text_says_the_shot_waits(self):
        self.ensure(self.no_wide)
        wide_key = self.rec()["wide_key"]
        fail = json.load(open(os.path.join(location_pack.cache_root(self.tmp), wide_key, "failed.json"), encoding="utf-8"))
        self.assertIn("GIỮ CHỜ tới khi có ảnh toàn", fail["reason"])
        self.assertNotIn("gửi không kèm", fail["reason"])

    def test_retry_button_forgets_the_wide_of_a_shot_held_by_it(self):
        self.ensure(self.no_wide)
        wide_key = self.rec()["wide_key"]
        failed = os.path.join(location_pack.cache_root(self.tmp), wide_key, "failed.json")
        self.assertTrue(os.path.exists(failed))
        self.assertTrue(place_refs.retry_render(self.p.conn, self.data, self.pid, self.sid))
        self.assertFalse(os.path.exists(failed))
        self.ensure(self.fake_render)
        self.assertTrue(os.path.exists(self.rec()["wide"]["plate"]))


class RefreshTests(_Fix):
    def test_old_finish_in_the_index_reruns_ensure_plates(self):
        self.render()
        self.assertFalse(location_pack.refresh_due(self.data, self.pid))
        path = os.path.join(self.data, str(self.pid), "plates", "index.json")
        idx = json.load(open(path, encoding="utf-8"))
        idx[str(self.sid)]["wide"].pop("finish_v")
        json.dump(idx, open(path, "w", encoding="utf-8"))
        self.assertTrue(location_pack.refresh_due(self.data, self.pid))           # an old wide
        idx[str(self.sid)]["wide"]["finish_v"] = plate_env.FINISH_VERSION
        idx[str(self.sid)]["finish_v"] = 2
        json.dump(idx, open(path, "w", encoding="utf-8"))
        self.assertTrue(location_pack.refresh_due(self.data, self.pid))           # an old plate
        self.render()
        self.assertFalse(location_pack.refresh_due(self.data, self.pid))          # finished again (0 USD), not every tick

    def test_autopilot_runs_ensure_plates_when_keys_match_but_the_finish_is_old(self):
        from core import autopilot
        self.render()
        ctx = mock.Mock(data_dir=self.data)
        with mock.patch.object(location_pack, "ensure_plates") as ens:
            autopilot._plates_phase(self.p, self.pid, ctx)
        ens.assert_not_called()                                                  # keys match, finish current: nothing to do
        with mock.patch.object(location_pack, "refresh_due", return_value=True), \
                mock.patch.object(location_pack, "ensure_plates") as ens:
            autopilot._plates_phase(self.p, self.pid, ctx)
        ens.assert_called_once()


class LiftTests(_Fix):
    def test_shadow_takes_the_plates_gain_and_lamps_are_not_lifted(self):
        d = self.tmp
        raw, shadow = os.path.join(d, "raw.png"), os.path.join(d, "shadow_raw.png")
        Image.fromarray(np.full((64, 36, 4), (30, 30, 30, 255), dtype=np.uint8)).save(raw)
        Image.fromarray(np.full((64, 36, 4), (12, 12, 12, 255), dtype=np.uint8)).save(shadow)    # darker: its own gain would differ
        env = {"time": "night", "weather": "clear"}
        real = plate_env.dark_gain
        with mock.patch.object(plate_env, "dark_gain", side_effect=real) as g:
            rec = {"raw": raw, "shadow_raw": shadow}
            location_pack._finish(rec, d, {"key": "abcdef0123", "env": env})
        self.assertEqual(g.call_count, 1)                                         # measured on the plate only…
        p_mean = float(np.asarray(Image.open(rec["plate"]).convert("L"), dtype=np.float32).mean())
        s_mean = float(np.asarray(Image.open(rec["shadow"]).convert("L"), dtype=np.float32).mean())
        self.assertAlmostEqual(s_mean / p_mean, 12 / 30, delta=0.08)               # …and the shadow keeps the plate's ratio (same gain)
        self.assertEqual(plate_env.dark_gain(np.full((4, 4, 3), 0.1), np.ones((4, 4)), dict(env, practical=True)), 1.0)

    def test_too_dark_is_not_judged_on_a_day_plate(self):
        p = os.path.join(self.tmp, "dark.png")
        Image.fromarray(np.full((64, 36, 3), 25, dtype=np.uint8)).save(p)
        self.assertIn("QUÁ TỐI", plate_env.plate_problem(p) or "")
        self.assertNotIn("QUÁ TỐI", plate_env.plate_problem(p, dark_check=False) or "")
        rec = {"raw": plate_png(os.path.join(self.tmp, "r.png")), "time": None}
        location_pack._finish(rec, self.tmp, {"key": "abcdef0123", "env": {"time": "day", "weather": "clear"}})
        self.assertEqual((rec["time"], rec["finish_v"]), ("day", plate_env.FINISH_VERSION))


class AgentReviewTests(_Fix):
    """Rà quy ước 7 lần 2 (15/10): máy thật vào index, đêm có đèn không 'QUÁ TỐI', ảnh toàn tối vẫn gửi, hoàn thiện lỗi không lặp,
    ảnh toàn của shot trong nhà không bị đòi, không nâng SCRIPT_VERSION (ảnh đã duyệt không thành 'nền cũ')."""

    def test_index_camera_is_the_camera_blender_used(self):
        plan = {"location": [0, 4, 1], "look_at": [0, 0, 1], "lens": 24.0, "locked": False}
        self.assertIs(location_pack.effective_camera(plan, {"clearance": {"notes": []}}), plan)
        rec = {"clearance": {"location_model": [1.0, 2.0, 1.0], "look_at_model": [0.5, 0.0, 1.0], "lens": 16.0, "turned_deg": 40}}
        real = location_pack.effective_camera(plan, rec)
        self.assertEqual((real["location"], real["look_at"], real["lens"], real["turned_deg"]), ([1.0, 2.0, 1.0], [0.5, 0.0, 1.0], 16.0, 40))
        self.assertEqual(plan["lens"], 24.0)                                      # the plan itself untouched

        def moved(cfg, blender=None, timeout=0):
            out = self.fake_render(cfg, blender, timeout)
            for p in out["plates"]:
                p["clearance"] = {"notes": ["x"], "warnings": [], "location_model": [1.0, 2.0, 1.0], "lens": 16.0}
            return out
        self.ensure(moved)
        rec = self.rec()
        self.assertEqual((rec["camera_plan"]["location"], rec["camera_plan"]["lens"]), ([1.0, 2.0, 1.0], 16.0))
        self.assertNotEqual(rec["camera_planned"]["lens"], 16.0)

    def test_lit_night_is_not_judged_too_dark(self):
        self.assertFalse(location_pack.dark_judged({"time": "night", "practical": True}))
        self.assertTrue(location_pack.dark_judged({"time": "night"}))
        self.assertFalse(location_pack.dark_judged({"time": "day"}))

    def test_dark_wide_still_goes_with_a_note(self):
        with mock.patch.object(location_pack, "_recheck_problem",
                               side_effect=lambda rec, dest: "nền 3D QUÁ TỐI (độ sáng trung bình 30/255 < 40)" if "wide" in str(rec.get("why")) else None):
            self.ensure(self.fake_render)
        rec = self.rec()
        self.assertNotIn("failed", rec)
        self.assertTrue(os.path.exists(rec["wide"]["plate"]))
        self.assertIn("vẫn gửi", rec["wide_note"])

    def test_a_refinish_error_is_said_once_not_raised_every_tick(self):
        self.render()
        path = os.path.join(self.data, str(self.pid), "plates", "index.json")
        key = self.rec()["key"]
        meta = os.path.join(location_pack.cache_root(self.tmp), key, "meta.json")
        m = json.load(open(meta, encoding="utf-8"))
        m["finish_v"] = 1
        json.dump(m, open(meta, "w", encoding="utf-8"))
        with mock.patch.object(location_pack, "_finish", side_effect=OSError("raw hỏng")):
            self.ensure(self.fake_render)                                        # no exception out of the autopilot tick
        self.assertIn("không hoàn thiện lại được", self.rec()["failed"])
        self.assertFalse(location_pack.refresh_due(self.data, self.pid))           # failed records are not refreshed for ever
        self.assertTrue(os.path.exists(path))

    def test_indoor_shot_never_waits_for_its_wide(self):
        location_pack.set_model3d(self.p.conn, self.place, location_pack.model3d(self.p.conn, self.place)["path"],
                                  dict(SPOTS, phong=ROOM), default_spot="plaza_front")
        self.set_data(dict(self.data_of(), plate_spot="phong"))
        self.render()
        path = os.path.join(self.data, str(self.pid), "plates", "index.json")
        idx = json.load(open(path, encoding="utf-8"))
        idx[str(self.sid)].pop("wide", None)
        json.dump(idx, open(path, "w", encoding="utf-8"))
        self.assertEqual(self.state(), (False, None))

    def test_script_version_not_bumped_so_approved_pictures_stay_current(self):
        self.assertEqual(location_pack.SCRIPT_VERSION, "v4-1")
