"""Ca lỗi thật #24 job 649 (11/10, shot 9): gói gửi có HAI nền 3D — `78f582…/plate_lift.png` (máy Sân khấu 3D r12 đã duyệt, khung
cố ý không có nhà) + `eb1c59…/plate.png` (ảnh toàn cùng trục F2 của CHÍNH máy đó: lùi 4,8 m, ống 18 mm, chưa làm sáng — thấy nhà ở mép
trái). Model ghép nhà của ảnh toàn vào khung shot → nhà dính tường.

Luật (một nguồn sự thật = máy Sân khấu 3D khi có):
- shot có `stage_camera` (máy khóa, khung đã duyệt): chỉ gửi nền của CHÍNH máy đó — không ảnh toàn cùng trục, không ảnh toàn cảnh
  chung của cảnh (scene_establish), vì ảnh rộng hơn cho model thấy thứ khung cố ý bỏ ra;
- shot không có máy khóa: nền shot + ảnh toàn cùng trục CỦA CHÍNH nó (F2) — không nền nào khác;
- kiểm chặn trước khi gửi (ImageRunner._pregen): gói có nền khác khóa camera / ≥ 2 nền shot / ảnh toàn với máy khóa → ĐỎ có lý do,
  ảnh GIỮ CHỜ, không gửi (0 USD), không im lặng."""
import json
import os
from unittest import mock

from core import location_pack, place_refs, scene_establish
from core.runner import WAIT_REASONS
from tests.test_plate_stale_kld6 import OLD_FIELDS, Base, plate_png

STAGE = {"location": [10.0, 5.0, 4.6], "look_at": [30.0, 5.0, 4.0], "lens": 22, "source": "test stage r12"}


class _Send(Base):
    def setUp(self):
        super().setUp()
        from core import runner as runner_mod
        runner_mod.PREGEN_HELD.clear()                   # job ids repeat across test databases
        self.addCleanup(runner_mod.PREGEN_HELD.clear)

    def runner(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        self.provider = MockImageProvider()
        return ImageRunner(self.p, self.provider, self.data)

    def job_row(self):
        return self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=?", (self.sid,)).fetchone()

    def sent(self):
        return json.loads(self.job_row()["sent_refs"] or "[]")

    def diags(self, code):
        return self.p.conn.execute("SELECT * FROM diag_events WHERE code=?", (code,)).fetchall()


class StageCameraSendsOnlyItsOwnPlate(_Send):
    def setUp(self):
        super().setUp()
        self.env2 = mock.patch.dict(os.environ, {"FEATURE_STAGE_CAMERA": "1"})
        self.env2.start()
        self.addCleanup(self.env2.stop)
        self.set_data(dict(OLD_FIELDS, plate_spot="nha_lon_dong", stage_camera=STAGE))

    def test_locked_stage_camera_gets_no_wide_and_no_scene_wide(self):
        self.render()
        rec = location_pack.index(self.data, self.pid)[str(self.sid)]
        self.assertTrue(rec["camera_plan"].get("locked"))
        self.assertIsNone(place_refs.wide_for(self.p.conn, self.data, self.pid, self.sid, self.data_of()))
        est = {"path": plate_png(os.path.join(self.tmp, "establish.png")), "label": scene_establish.LABEL, "role": "location"}
        self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async"), mock.patch.object(scene_establish, "reference", return_value=est):
            self.assertEqual(self.runner().submit_pending(self.pid), 1)
        sent = self.sent()
        places = [s for s in sent if s.get("plate_key") or s["role"] in (place_refs.ROLE, place_refs.WIDE_ROLE)]
        self.assertEqual([s["plate_key"] for s in places], [rec["key"]])        # một nền, đúng máy hiện tại
        self.assertFalse(any(s["label"] == scene_establish.LABEL for s in sent))
        prompt = next(iter(self.provider.prompts.values()))
        self.assertNotIn("WIDE same-axis", prompt)


class PackageCheck(_Send):
    def test_unlocked_shot_keeps_its_own_same_axis_wide(self):
        self.render()
        rec = location_pack.index(self.data, self.pid)[str(self.sid)]
        self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async"):
            self.assertEqual(self.runner().submit_pending(self.pid), 1)
        keys = [s.get("plate_key") for s in self.sent() if s["role"] in (place_refs.ROLE, place_refs.WIDE_ROLE)]
        self.assertEqual(keys, [rec["key"], rec["wide"]["key"]])

    def test_a_plate_of_another_camera_holds_the_picture_red(self):
        """Job 649: a second background whose camera key is not this shot's (nor its own wide) — held, said, never sent."""
        self.render()
        foreign = plate_png(os.path.join(self.tmp, "old_plate.png"))
        bad_wide = {"path": foreign, "label": f"{place_refs.WIDE_LABEL} (x)", "role": place_refs.WIDE_ROLE, "plate_key": "eb1c59f2c163d86cbf53"}
        job = self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async"), mock.patch.object(place_refs, "wide_ref", return_value=bad_wide):
            self.assertEqual(self.runner().submit_pending(self.pid), 0)
        row = self.job_row()
        self.assertEqual(row["state"], "queued")
        self.assertIsNone(row["external_id"])
        self.assertEqual(self.provider.prompts, {})                     # nothing paid
        why = WAIT_REASONS.get(job, ("",))[0]
        self.assertIn("eb1c59f2c163d86cbf53", why)
        self.assertIn("CẦN BẠN SỬA", why)
        self.assertTrue(self.diags("plate_package_mixed"))
        self.assertEqual(self.diags("plate_package_mixed")[0]["severity"], "error")

    def test_held_picture_is_not_rebuilt_every_heartbeat(self):
        """Rà quy ước 7: a held job keeps its reason without rebuilding the request or adding diag rows on each tick."""
        from core import runner as runner_mod
        self.render()
        bad_wide = {"path": plate_png(os.path.join(self.tmp, "old.png")), "label": "w", "role": place_refs.WIDE_ROLE, "plate_key": "zzz"}
        job = self.p.create_job(self.sid, "image_gen")
        r = self.runner()
        with mock.patch.object(place_refs, "ensure_async"), mock.patch.object(place_refs, "wide_ref", return_value=bad_wide):
            for _ in range(3):
                self.assertEqual(r.submit_pending(self.pid), 0)
            self.assertEqual(sum(d["count"] for d in self.diags("plate_package_mixed")), 1)
            runner_mod.PREGEN_HELD[job] = (runner_mod.PREGEN_HELD[job][0], 0.0)      # cooled down: checked again, still held
            self.assertEqual(r.submit_pending(self.pid), 0)
        self.assertIn("zzz", WAIT_REASONS[job][0])
        runner_mod.PREGEN_HELD.pop(job, None)


class PackageProblemUnit(Base):
    REC = {"key": "aaa", "wide": {"key": "www"}, "camera_plan": {}}

    def test_own_plate_and_own_wide_pass(self):
        sent = [{"role": "character", "file": "k.png"}, {"role": place_refs.ROLE, "plate_key": "aaa", "file": "plate.png"},
                {"role": place_refs.WIDE_ROLE, "plate_key": "www", "file": "plate.png"}]
        self.assertIsNone(place_refs.package_problem(sent, self.REC))
        self.assertIsNone(place_refs.package_problem([{"role": "character", "file": "k.png"}], None))

    def test_foreign_key_two_renders_or_wide_with_locked_camera_are_red(self):
        foreign = [{"role": place_refs.ROLE, "plate_key": "aaa", "file": "p.png"},
                   {"role": place_refs.WIDE_ROLE, "plate_key": "old", "file": "plate.png"}]
        self.assertIn("old", place_refs.package_problem(foreign, self.REC))
        two = [{"role": place_refs.ROLE, "plate_key": "aaa", "file": "p.png"}, {"role": place_refs.ROLE, "plate_key": "aaa", "file": "q.png"}]
        self.assertTrue(place_refs.package_problem(two, self.REC))
        locked = dict(self.REC, camera_plan={"locked": True})
        own_wide = [{"role": place_refs.ROLE, "plate_key": "aaa", "file": "p.png"},
                    {"role": place_refs.WIDE_ROLE, "plate_key": "www", "file": "plate.png"}]
        self.assertTrue(place_refs.package_problem(own_wide, locked))
        est = [{"role": place_refs.ROLE, "plate_key": "aaa", "file": "p.png"},
               {"role": "location", "label": scene_establish.LABEL, "file": "e.png"}]
        self.assertTrue(place_refs.package_problem(est, locked))
        self.assertIsNone(place_refs.package_problem(est, self.REC))       # the scene wide is not a plate for an unlocked camera
        no_rec = [{"role": place_refs.ROLE, "plate_key": "aaa", "file": "p.png"}]
        self.assertTrue(place_refs.package_problem(no_rec, None))          # a plate sent while the shot has no plate record
