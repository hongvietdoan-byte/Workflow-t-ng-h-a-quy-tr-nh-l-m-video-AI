"""V3.1 M7.3 (sổ v31-ep-k3-seedance-ref-groups-with-end-frames-2026-10-21, gốc B4): seedance_ref_groups + end_frames cùng chạy.

Trước: core/end_frames.py:32 — shot per_shot đủ điều kiện tuyến tham chiếu (Seedance ref-only) KHÔNG cần khung cuối → không vẽ, không
giữ clip, không báo; shot trong nhóm ref-only không thể có khung cuối riêng. Cờ con `ref_end_frames` (mặc định TẮT): shot có end_state
đi tuyến ref vẫn cần khung cuối — tách khỏi nhóm (gửi một mình, khung cuối đi như ảnh tham chiếu cuối có câu vai trò — adapter ClipAI);
model tuyến ref không nhận khung cuối (data/provider_rules.json `last_frame`) → không tách, báo VÀNG (REVIEW), không âm thầm bỏ.
CSDL tạm, provider giả, 0 USD."""
import json
import os
import unittest
from unittest import mock

from core import end_frames, features, model_router, seedance_refs, video_rules
from core.providers import MockImageProvider
from tests._flags import flags_on
from tests import test_seedance_refs as _sr

FLAG = "ref_end_frames"


class _Base(_sr.SeedanceRefTests):
    def set(self, sid, **fields):
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        d = dict(json.loads(row["data"] or "{}"), **fields)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        self.p.conn.commit()

    def data_of(self, sid):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])

    def group_ids(self):
        return [[r["id"] for r in g] for g in seedance_refs._groups(self.p.conn, self.pid)]

    def no_takes(self):
        rules = {k: (dict(v, refs_with_end_frame=False) if v.get("family") == "seedance" else v)
                 for k, v in video_rules.models().items()}
        return mock.patch.object(video_rules, "models", return_value=rules)


for _name in [n for n in dir(_sr.SeedanceRefTests) if n.startswith("test_")]:
    setattr(_Base, _name, None)


class RefEndFrames(_Base):
    def setUp(self):
        super().setUp()
        flags_on(self, "end_frames")
        self.target = self.ids[-1]
        self.set(self.target, end_state="Kenta lies on the ground, sword out of reach")

    def test_flag_registered_and_off_by_default(self):
        self.assertIn(FLAG, features.FEATURES)
        self.assertFalse(features.FEATURES[FLAG]["verified"])
        self.assertEqual(features.REQUIRES.get(FLAG), ("end_frames", "seedance_ref_groups"))

    def test_flag_off_ref_route_needs_no_end_frame_as_before(self):
        flags_on(self, FLAG, value=False)
        d = self.data_of(self.target)
        self.assertEqual(end_frames.route(d), "seedance_ref")
        self.assertFalse(end_frames.needed(d, "per_shot"))
        self.assertIn(self.target, self.group_ids()[0])
        self.assertIsNone(seedance_refs.end_split_reason(self.p.conn, self.target))
        self.assertIsNone(end_frames.ref_unsupported_reason(d, "per_shot"))

    def test_flag_on_ref_route_still_needs_its_end_frame(self):
        flags_on(self, FLAG)
        d = self.data_of(self.target)
        self.assertEqual(end_frames.route(d), "seedance_ref")
        self.assertTrue(end_frames.needed(d, "per_shot"))
        self.assertFalse(end_frames.needed(dict(d, continuous_with_next=True), "per_shot"))
        self.assertFalse(end_frames.needed(dict(d, end_state=""), "per_shot"))
        self.assertFalse(end_frames.needed(d, "multishot"))

    def test_flag_on_the_shot_leaves_its_group_and_says_why(self):
        flags_on(self, FLAG, value=False)
        before = self.group_ids()
        self.assertIn(self.target, before[0])
        flags_on(self, FLAG)
        after = self.group_ids()
        self.assertFalse(any(self.target in g for g in after))
        rest = [x for x in before[0] if x != self.target]
        self.assertGreater(len(rest), 1, "fixture: nhóm ≥ 3 shot")
        self.assertEqual(after[0], rest)                                # rà (d): kiểm chắc, không bỏ nhánh
        why = seedance_refs.end_split_reason(self.p.conn, self.target)
        self.assertIn("end_state", why)
        for sid in rest:
            self.assertIsNone(seedance_refs.end_split_reason(self.p.conn, sid))
        self.assertIsNone(seedance_refs.split_reason(self.p.conn, self.target))     # khung đầu (M2.8) không lẫn vào

    def test_end_frames_off_nothing_changes(self):
        flags_on(self, FLAG)
        flags_on(self, "end_frames", value=False)
        self.assertIn(self.target, self.group_ids()[0])
        self.assertFalse(end_frames.needed(self.data_of(self.target), "per_shot"))
        self.assertIsNone(seedance_refs.end_split_reason(self.p.conn, self.target))

    def test_model_without_end_frame_is_not_split_and_is_said(self):
        flags_on(self, FLAG)
        with self.no_takes():
            self.assertFalse(model_router.ref_mode_takes_end_frame())
            self.assertIn(self.target, self.group_ids()[0])
            self.assertFalse(end_frames.needed(self.data_of(self.target), "per_shot"))
            why = end_frames.ref_unsupported_reason(self.data_of(self.target), "per_shot")
            self.assertIn("không nhận khung cuối", why)
            self.assertIsNone(end_frames.ref_unsupported_reason(dict(self.data_of(self.target), end_state=""), "per_shot"))

    def test_queue_draws_the_end_frame_of_a_ref_shot(self):
        _sr._approve_all_images(self.p, self.pid, self.data)
        flags_on(self, FLAG, value=False)
        self.assertNotIn(self.target, end_frames.queue(self.p, self.pid))
        flags_on(self, FLAG)
        self.assertIn(self.target, end_frames.queue(self.p, self.pid))
        self.assertEqual(end_frames.missing_reason(self.p.conn, self.target), end_frames.AUTO_WAITING)   # có lý do, không im lặng

    def _drawn(self):
        vr = self._ready()
        img = MockImageProvider()
        end_frames.queue(self.p, self.pid)
        end_frames.tick(self.p, self.pid, img, self.data)
        end_frames.tick(self.p, self.pid, img, self.data)
        path = end_frames.usable_path(self.p.conn, self.target)
        self.assertTrue(path)
        _sr.real_png(path)
        return vr, path

    def test_send_goes_alone_with_the_end_frame_as_last_reference(self):
        flags_on(self, FLAG)
        vr, path = self._drawn()
        job = self.p.job(self.p.create_job(self.target, "video_gen"))
        self.assertFalse(vr._sends_group(job))
        with mock.patch("core.seedance_refs.mark", side_effect=lambda p, *a, **k: p):
            kw = vr._submit_kwargs(job)
        self.assertTrue(kw.get("reference_only"))
        self.assertEqual(kw.get("_last_frame_source"), path)
        self.assertEqual(kw.get("last_frame"), path)

    def test_sent_package_records_the_end_frame_split(self):
        flags_on(self, FLAG)
        vr, path = self._drawn()
        jid = self.p.create_job(self.target, "video_gen")
        vr.submit_pending(self.pid)
        pkg = json.loads(self.p.job(jid)["sent_package"] or "{}")
        self.assertTrue(pkg, "job gửi đi phải có gói")
        self.assertTrue(pkg["router_khung_cuoi"]["gui_mot_minh"])
        self.assertIn("end_state", pkg["router_khung_cuoi"]["ly_do"])
        self.assertNotIn("router", pkg)                                 # M2.8 khung đầu: cờ tắt, không có khóa

    def test_flag_off_sent_package_has_no_new_key_and_the_group_goes(self):
        flags_on(self, FLAG, value=False)
        vr = self._ready()
        lead = self.p.create_job(self.ids[0], "video_gen")
        self.assertEqual(vr.submit_pending(self.pid), 1)
        job = self.p.job(lead)
        pkg = json.loads(job["sent_package"] or "{}")
        self.assertTrue(pkg)
        self.assertNotIn("router_khung_cuoi", pkg)
        self.assertIn(self.target, [int(g["id"]) for g in json.loads(job["sent_group"] or "[]")])

    def test_model_without_end_frame_send_says_review(self):
        flags_on(self, FLAG)
        vr = self._ready()
        job = self.p.job(self.p.create_job(self.target, "video_gen"))
        with self.no_takes(), mock.patch("core.seedance_refs.mark", side_effect=lambda p, *a, **k: p):
            vr._submit_kwargs(job)
        said = [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='end_frame_ref_unsupported'")]
        self.assertEqual(len(said), 1)
        self.assertIn("không nhận khung cuối", said[0])

    def test_video_pregen_review_when_the_model_takes_none(self):
        from core import video_pregen
        flags_on(self, FLAG)
        out = []
        with self.no_takes():
            video_pregen._check_end(self.p.conn, self.ids[0], {"reference_only": ["a.png"], "group_ids": list(self.ids)},
                                    self.data_of(self.ids[0]), out)      # rà VỪA-1: shot dẫn đầu, shot cần khung cuối nằm trong nhóm
        self.assertIn(("khung_cuoi", "vang"), [(i["ma"], i["muc"]) for i in out])
        self.assertTrue(any(f"S{self.idx(self.target):02d}" in i["ly_do"] for i in out))
        out = []
        video_pregen._check_end(self.p.conn, self.target, {"reference_only": ["a.png"], "group_ids": [self.ids[0]]},
                                self.data_of(self.target), out)
        self.assertEqual([i for i in out if "không nhận khung cuối" in i["ly_do"]], [])

    def idx(self, sid):
        return self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()["idx"]

    def _said(self, code):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code=?", (code,))]

    def test_vua1_group_clip_says_review_for_a_member_shot(self):
        """Rà VỪA-1: model không nhận khung cuối → shot không tách, nằm trong clip nhóm của shot dẫn đầu — VÀNG vẫn phải nói."""
        flags_on(self, FLAG)
        vr = self._ready()
        jobs = [self.p.create_job(sid, "video_gen") for sid in self.ids]
        with self.no_takes():
            self.assertEqual(vr.submit_pending(self.pid), 1)              # một clip nhóm
        self.assertIn(self.target, [int(g["id"]) for g in json.loads(self.p.job(jobs[0])["sent_group"] or "[]")])
        said = self._said("end_frame_ref_unsupported")
        self.assertEqual(len(said), 1, said)
        self.assertIn(f"S{self.idx(self.target):02d}", said[0])

    def test_vua2_rollback_does_not_hold_a_shot_on_an_auto_queued_end_frame(self):
        """Rà VỪA-2: bật cờ → queue() xếp khung cuối; tắt cờ (rollback) → shot về nhóm, không còn bị giữ 'chờ khung cuối'."""
        lead = self.ids[0]
        self.set(lead, end_state="Kenta lies on the ground, sword out of reach")
        flags_on(self, FLAG)
        vr = self._ready()
        self.assertIn(lead, end_frames.queue(self.p, self.pid))
        job = self.p.job(self.p.create_job(lead, "video_gen"))
        self.assertTrue(vr._wait(job))                                    # cờ bật: chờ khung cuối (đúng)
        flags_on(self, FLAG, value=False)
        self.assertFalse(vr._wait(job))                                   # rollback: shot dẫn đầu gửi nhóm như cũ
        self.assertEqual(vr.submit_pending(self.pid), 1)
        self.assertNotEqual(self.p.job(job["id"])["state"], "queued")

    def test_vua2_a_person_asked_end_frame_still_holds_with_the_flag_off(self):
        """Hành vi cũ (cờ tắt): khung cuối NGƯỜI bấm vẽ (🔁) cho shot ref vẫn giữ clip tới khi vẽ xong."""
        flags_on(self, FLAG, value=False)
        vr = self._ready()
        end_frames.redo(self.p, self.target)
        job = self.p.job(self.p.create_job(self.target, "video_gen"))
        from core import runner
        vr._wait(job)
        self.assertIn("khung cuối", runner.wait_reason(job["id"]) or "")

    def test_no_end_frame_for_a_shot_a_group_clip_in_flight_carries(self):
        """Rà VỪA/THẤP: bật cờ giữa chừng — shot đã nằm trong clip nhóm đang bay không vẽ khung cuối thừa (không tính giá)."""
        from core import cost
        flags_on(self, FLAG, value=False)
        vr = self._ready()
        lead = self.p.create_job(self.ids[0], "video_gen")
        self.assertEqual(vr.submit_pending(self.pid), 1)
        self.assertIn(self.target, [int(g["id"]) for g in json.loads(self.p.job(lead)["sent_group"] or "[]")])
        flags_on(self, FLAG)
        self.assertEqual(cost.pending_end_frames(self.p, self.pid), 0)
        self.assertNotIn(self.target, end_frames.queue(self.p, self.pid))

    def test_a_skill_object_shot_is_not_split(self):
        """Rà THẤP (c): shot runner luôn bỏ khung cuối (vật kỹ năng → GHÉP) không tách khỏi nhóm."""
        flags_on(self, FLAG)
        with mock.patch.object(end_frames, "skip_reason", return_value="vật kỹ năng"):
            self.assertIn(self.target, self.group_ids()[0])
            self.assertIsNone(seedance_refs.end_split_reason(self.p.conn, self.target))

    def test_with_router_first_frame_both_reasons_and_the_price(self):
        """Rà THẤP (e): bật cả router_first_frame + ref_end_frames — hai shot tách, mỗi shot lý do riêng; giá clip riêng ≥ 4 s."""
        flags_on(self, FLAG, "router_first_frame")
        self.set(self.ids[0], start_from_prev_clip=True)
        groups = self.group_ids()
        self.assertFalse(any(self.ids[0] in g or self.target in g for g in groups))
        self.assertIn("start_from_prev_clip", seedance_refs.split_reason(self.p.conn, self.ids[0]))
        self.assertIsNone(seedance_refs.end_split_reason(self.p.conn, self.ids[0]))
        self.assertIn("end_state", seedance_refs.end_split_reason(self.p.conn, self.target))
        self.assertIsNone(seedance_refs.split_reason(self.p.conn, self.target))
        billed = next(r["billed_seconds"] for r in model_router.plan(self.p.conn, self.pid) if r["scene_id"] == self.target)
        self.assertGreaterEqual(billed, seedance_refs.SEEDANCE_MIN)

    def test_trainee_screen_no_longer_calls_end_frames_without_effect(self):
        from dashboard.design.screens import trainee_ui as TU
        flags_on(self, FLAG, value=False)
        self.assertIn("seedance_ref_groups", TU.no_effect_note("end_frames"))
        flags_on(self, FLAG)
        self.assertEqual(TU.no_effect_note("end_frames"), "")

    def test_flag_switched_on_while_a_group_clip_is_in_flight_does_not_send_the_part_twice(self):
        flags_on(self, FLAG, value=False)
        vr = self._ready()
        lead = self.p.create_job(self.ids[0], "video_gen")
        self.assertEqual(vr.submit_pending(self.pid), 1)
        self.assertIn(self.target, [int(g["id"]) for g in json.loads(self.p.job(lead)["sent_group"] or "[]")])
        flags_on(self, FLAG)
        b = self.p.create_job(self.target, "video_gen")
        self.assertTrue(vr._wait(self.p.job(b)))
        self.assertEqual(self.p.job(b)["state"], "queued")


class Rules(unittest.TestCase):
    def test_every_seedance_model_takes_an_end_frame_today(self):
        fam = {k: v for k, v in video_rules.models().items() if v.get("family") == "seedance"}
        self.assertTrue(fam)
        for k, v in fam.items():
            self.assertIs(v.get("refs_with_end_frame"), True, k)       # rà THẤP (b): khóa riêng của tuyến ref (ảnh tham chiếu cuối)
        self.assertTrue(model_router.ref_mode_takes_end_frame())
        with mock.patch.object(video_rules, "models", return_value={k: dict(v, last_frame=True, refs_with_end_frame=False)
                                                                       for k, v in fam.items()}):
            self.assertFalse(model_router.ref_mode_takes_end_frame())

    def test_unknown_capability_counts_as_not_taken(self):
        with mock.patch.object(video_rules, "models", return_value={"s": {"family": "seedance"}}):
            self.assertFalse(model_router.ref_mode_takes_end_frame())
        with mock.patch.object(video_rules, "models", return_value={}):
            self.assertFalse(model_router.ref_mode_takes_end_frame())

    def test_golden_inputs_pin_the_flag_off(self):
        path = os.path.join(os.path.dirname(__file__), "golden", "package_inputs.json")
        text = open(path, encoding="utf-8").read()
        self.assertGreaterEqual(text.count(f'"{FLAG}": false'), 2)


if __name__ == "__main__":
    unittest.main()
