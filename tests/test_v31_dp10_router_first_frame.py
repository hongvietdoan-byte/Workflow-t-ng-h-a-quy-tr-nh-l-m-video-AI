"""V3.1 M2.8 (DP10) — router theo khả năng model, cờ router_first_frame (mặc định tắt): shot CẦN khung đầu đã duyệt không gộp vào nhóm
Seedance ref-only (ref-only không giữ khung đầu — data/provider_rules.json first_frame_in_ref_mode), gửi một mình; lý do ghi vào gói gửi.
#31 G28 (khung 0 khác ảnh đầu), G37 (nhóm 28+29 mất dạng). Cờ tắt = nhóm như cũ. CSDL tạm, provider giả, không mạng."""
import json
import unittest
from unittest import mock

from core import character_forms, model_router, seedance_refs, video_rules
from tests._flags import flags_on
from tests import test_seedance_refs as _sr


class _Base(_sr.SeedanceRefTests):
    """Dùng lại dự án mock của test nhóm Seedance (một cảnh, ≥ 2 shot liền cùng nhóm)."""

    def set(self, sid, **fields):
        row = self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        d = dict(json.loads(row["data"] or "{}"), **fields)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        self.p.conn.commit()

    def group_ids(self):
        return [[r["id"] for r in g] for g in seedance_refs._groups(self.p.conn, self.pid)]


# chỉ chạy test của lớp này, không chạy lại mọi test kế thừa từ SeedanceRefTests
for _name in [n for n in dir(_sr.SeedanceRefTests) if n.startswith("test_")]:
    setattr(_Base, _name, None)


class RouterFirstFrame(_Base):
    def test_flag_off_groups_as_before_even_with_a_chained_shot(self):
        flags_on(self, "router_first_frame", value=False)
        before = self.group_ids()
        self.set(self.ids[0], start_from_prev_clip=True)
        self.assertEqual(self.group_ids(), before)                     # lỗi cũ còn nguyên khi cờ tắt (byte hành vi)
        self.assertIn(self.ids[0], before[0])
        self.assertIsNone(seedance_refs.split_reason(self.p.conn, self.ids[0]))

    def test_flag_on_sends_a_shot_that_needs_its_first_frame_alone(self):
        flags_on(self, "router_first_frame")
        self.set(self.ids[0], start_from_prev_clip=True)
        groups = self.group_ids()
        self.assertFalse(any(self.ids[0] in g for g in groups))
        if len(self.ids) >= 3:                                          # the rest still go together
            self.assertEqual(groups[0][:len(self.ids) - 1], self.ids[1:])
        self.assertIn("start_from_prev_clip", seedance_refs.split_reason(self.p.conn, self.ids[0]))
        self.assertIsNone(seedance_refs.split_reason(self.p.conn, self.ids[1]))

    def test_flag_on_nothing_needs_a_first_frame_same_groups(self):
        flags_on(self, "router_first_frame", value=False)
        off = self.group_ids()
        flags_on(self, "router_first_frame")
        self.assertEqual(self.group_ids(), off)

    def test_a_character_form_for_the_whole_shot_splits_it(self):
        """G37: ảnh dạng bóng mờ bị cắt khi nhóm hết chỗ → shot có nhân vật ở dạng đặc biệt gửi một mình."""
        flags_on(self, "router_first_frame")
        target = self.ids[-1]

        def forms(conn, pid, data, chosen=None):
            return {"KENTA": {"form": "ghost", "label": "Bóng mờ"}} if data.get("shot_no") == self.shot_no(target) else {}
        with mock.patch.object(character_forms, "for_shot", side_effect=forms):
            self.assertFalse(any(target in g for g in self.group_ids()))
            self.assertIn("Bóng mờ", seedance_refs.split_reason(self.p.conn, target))

    def shot_no(self, sid):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])["shot_no"]

    def test_a_model_family_that_keeps_the_first_frame_is_not_split(self):
        flags_on(self, "router_first_frame")
        self.set(self.ids[0], start_from_prev_clip=True)
        keep = {k: dict(v, refs_with_first_frame=True) for k, v in video_rules.models().items()}
        with mock.patch.object(video_rules, "models", return_value=keep):
            self.assertTrue(model_router.ref_mode_keeps_first_frame())
            self.assertIn(self.ids[0], self.group_ids()[0])
            self.assertIsNone(seedance_refs.split_reason(self.p.conn, self.ids[0]))

    def test_sent_package_says_why_the_shot_went_alone(self):
        """(start_from_prev_clip làm job chờ clip shot trước — ca gói dùng lý do dạng nhân vật, cùng đường router.)"""
        flags_on(self, "router_first_frame")
        vr = self._ready()
        sid = self.ids[0]
        no = self.shot_no(sid)
        real = model_router.needs_first_frame
        with mock.patch.object(model_router, "needs_first_frame",
                               side_effect=lambda c, p, d, chosen=None: "nhân vật ở dạng đặc biệt: KENTA (Bóng mờ)"
                               if d.get("shot_no") == no else real(c, p, d, chosen)):
            jid = self.p.create_job(sid, "video_gen")
            vr.submit_pending(self.pid)
        pkg = json.loads(self.p.job(jid)["sent_package"] or "{}")
        self.assertTrue(pkg, "job gửi đi phải có gói")
        self.assertTrue(pkg["router"]["gui_mot_minh"])
        self.assertIn("Bóng mờ", pkg["router"]["ly_do"])
        self.assertIn("VẪN ref-only", pkg["router"]["ly_do"])             # rà DP10 CAO: không nói như đã có khung đầu

    def test_sent_package_without_the_flag_has_no_router_key(self):
        flags_on(self, "router_first_frame", value=False)
        vr = self._ready()
        jid = self.p.create_job(self.ids[0], "video_gen")
        vr.submit_pending(self.pid)
        pkg = json.loads(self.p.job(jid)["sent_package"] or "{}")
        self.assertTrue(pkg)
        self.assertNotIn("router", pkg)


    def test_a_middle_shot_split_leaves_two_sub_groups_or_lone_shots(self):
        flags_on(self, "router_first_frame", value=False)
        before = self.group_ids()[0]
        self.assertGreaterEqual(len(before), 3, "cần nhóm ≥ 3 shot")
        mid = before[1]
        flags_on(self, "router_first_frame")
        self.set(mid, start_from_prev_clip=True)
        after = self.group_ids()
        self.assertFalse(any(mid in g for g in after))
        self.assertNotIn([before[0]], after)                             # lone remains are one-shot clips, not groups
        self.assertEqual([x for g in after for x in g if x in before], [x for x in before[2:]] if len(before) > 3 else [])

    def test_split_reason_none_when_the_old_rule_already_sent_it_alone(self):
        """Rà DP10 VỪA-4: shot đứng lẻ theo luật cũ (nhóm khác) — không ghi 'tách vì khung đầu'."""
        flags_on(self, "router_first_frame")
        lone = self.ids[0]
        self.set(lone, sequence=99, start_from_prev_clip=True)          # its own continuity group: alone under the old rule
        self.assertIsNone(seedance_refs.split_reason(self.p.conn, lone))

    def test_price_follows_the_same_groups(self):
        """Giá dùng cùng groups() (model_router.plan): shot trong clip nhóm tính 0 s; bị tách → tính tiền clip riêng (≥ 4 s Seedance)."""
        sid = self.ids[1]
        billed = lambda: next(r["billed_seconds"] for r in model_router.plan(self.p.conn, self.pid) if r["scene_id"] == sid)  # noqa: E731
        flags_on(self, "router_first_frame", value=False)
        self.set(sid, start_from_prev_clip=True)
        self.assertEqual(billed(), 0.0)                                  # cờ tắt: trong clip nhóm của shot đầu
        flags_on(self, "router_first_frame")
        self.assertGreaterEqual(billed(), seedance_refs.SEEDANCE_MIN)

    def test_video_pregen_says_the_split_shot_still_has_no_first_frame(self):
        from core import video_pregen
        flags_on(self, "router_first_frame")
        self.set(self.ids[0], start_from_prev_clip=True)
        out = []
        video_pregen._check_router_split(self.p.conn, self.ids[0], {"reference_only": ["a.png"]}, out)
        self.assertEqual([(i["ma"], i["muc"]) for i in out], [("khung_dau", "vang")])
        self.assertIn("start_from_prev_clip", out[0]["ly_do"])
        out = []
        video_pregen._check_router_split(self.p.conn, self.ids[1], {"reference_only": ["a.png"]}, out)
        self.assertEqual(out, [])
        flags_on(self, "router_first_frame", value=False)
        video_pregen._check_router_split(self.p.conn, self.ids[0], {"reference_only": ["a.png"]}, out)
        self.assertEqual(out, [])

    def test_flag_switched_on_while_a_group_clip_is_in_flight_does_not_send_the_part_twice(self):
        """Rà DP10 VỪA-3: clip nhóm [A, B, …] đã gửi từ A; bật cờ, B bị tách → B KHÔNG gửi một mình lần nữa."""
        flags_on(self, "router_first_frame", value=False)
        vr = self._ready()
        lead = self.p.create_job(self.ids[0], "video_gen")
        self.assertEqual(vr.submit_pending(self.pid), 1)
        sent = json.loads(self.p.job(lead)["sent_group"] or "[]")
        self.assertIn(self.ids[1], [int(g["id"]) for g in sent])
        flags_on(self, "router_first_frame")
        self.set(self.ids[1], start_from_prev_clip=True)
        b = self.p.create_job(self.ids[1], "video_gen")
        self.assertTrue(vr._wait(self.p.job(b)))
        self.assertEqual(self.p.job(b)["state"], "queued")


class Rules(unittest.TestCase):
    def test_every_seedance_model_declares_the_capability(self):
        fam = {k: v for k, v in video_rules.models().items() if v.get("family") == "seedance"}
        self.assertTrue(fam)
        for k, v in fam.items():
            self.assertIs(v.get("refs_with_first_frame"), False, k)
        self.assertFalse(model_router.ref_mode_keeps_first_frame())

    def test_unknown_capability_counts_as_not_kept(self):
        with mock.patch.object(video_rules, "models", return_value={"s": {"family": "seedance"}}):
            self.assertFalse(model_router.ref_mode_keeps_first_frame())
        with mock.patch.object(video_rules, "models", return_value={}):
            self.assertFalse(model_router.ref_mode_keeps_first_frame())

    def test_reasons(self):
        nf = lambda d: model_router.needs_first_frame(None, 1, d)  # noqa: E731
        with mock.patch.object(character_forms, "for_shot", return_value={}):
            self.assertIsNone(nf({"shot_no": 1}))
            self.assertIsNone(nf({"continuity_from": 3}))                 # rà DP10 VỪA-2: luật bố cục ảnh, không phải khung đầu video
            self.assertIn("start_from_prev_clip", nf({"start_from_prev_clip": True}))
            self.assertIn("trong_khung", nf({"byd": {"khung": {"moc_nen": {"y_do": "trong_khung"}}}}))
            self.assertIsNone(nf({"byd": {"khung": {"moc_nen": {"y_do": "ngoai_khung"}}}}))
            self.assertIsNone(nf({"byd": "hỏng"}))
        with mock.patch.object(character_forms, "for_shot", return_value={"KELLY": {"label": "Bóng mờ"}}):
            self.assertIn("KELLY (Bóng mờ)", nf({"characters": ["KELLY"]}))


if __name__ == "__main__":
    unittest.main()
