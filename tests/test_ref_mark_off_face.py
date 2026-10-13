"""Lỗi hệ thống 4 (#27 13/10, cờ ref_mark_off_face): Seedance 2.5 chép dấu '+' đỏ của ảnh tham chiếu đánh dấu (Kho chủ thể đầy → gửi
ảnh đánh dấu cũ, dấu trên mắt) lên mặt Kelly shot 8–9, 18. Cờ bật: dấu ở góc ảnh + câu cấm theo tên; bị từ chối 'người thật' →
bậc tuyến cũ ngay (V5 13/10: không còn bước quay lại dấu trên mắt). Cùng chỗ: lỗi 3 (cờ skill_object_guard) trên prompt video thật.
Không gọi API."""
import json
import os
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from core import seedance_refs
from tests import test_seedance_refs as base   # module, not the class: pytest would run its tests twice

ON = {"FEATURE_REF_MARK_OFF_FACE": "1"}
OFF = {"FEATURE_REF_MARK_OFF_FACE": "0"}


def red_box(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    ys, xs = np.nonzero((a[..., 0] > 180) & (a[..., 1] < 60) & (a[..., 2] < 60))
    h, w = a.shape[:2]
    return (xs.min() / w, ys.min() / h) if len(xs) else None


class RefMarkOffFaceTest(unittest.TestCase):
    setUp = base.SeedanceRefTests.setUp
    _ready = base.SeedanceRefTests._ready

    def _leader(self):
        vr = self._ready()
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        return vr, leader

    def test_flag_off_eye_mark_and_old_prompt(self):
        with mock.patch.dict(os.environ, OFF):
            vr, leader = self._leader()
            refs = vr._submit_kwargs(leader)["reference_only"]
            motion = vr._submit_args(leader)[1]
        self.assertTrue(all(p.endswith("_marked.png") for p in refs))          # eye_plus file name, as before
        self.assertNotIn("Never draw a plus sign", motion)
        x, y = red_box(refs[0])
        self.assertLess(y, 0.8)                                                  # no face found: the upper middle

    def test_flag_on_corner_mark_and_ban_sentence_by_name(self):
        with mock.patch.dict(os.environ, ON):
            vr, leader = self._leader()
            refs = vr._submit_kwargs(leader)["reference_only"]
            motion = vr._submit_args(leader)[1]
        self.assertTrue(all(p.endswith("_marked_corner_plus.png") for p in refs))
        x, y = red_box(refs[0])
        self.assertGreater(x, 0.8)
        self.assertGreater(y, 0.85)                                              # bottom-right corner, off every face
        self.assertIn("Never draw a plus sign, cross, crosshair or any red mark on", motion)
        self.assertIn("on anyone's face, head, body or clothes", motion)      # the mock cast has no identity picture

    def test_ban_sentence_names_each_character_once(self):
        with mock.patch.dict(os.environ, ON):
            text = seedance_refs.prompt([("Kelly runs.", 2.0)], [("KELLY", "k.png"), ("KELLY" + seedance_refs.OUTFIT_TAG, "o.png"),
                                                                ("YÊU NỮ", "y.png")])
        self.assertIn("on KELLY, YEU NU's face", text)
        with mock.patch.dict(os.environ, OFF):
            self.assertNotIn("Never draw", seedance_refs.prompt([("Kelly runs.", 2.0)], [("KELLY", "k.png")]))

    def test_real_person_refusal_goes_down_the_ladder_never_back_to_the_eye_mark(self):
        """V5 (rà gốc 13/10, G9): the old step back to the eye mark drew the plus onto the start frame's face (852/853/896) — a
        refusal now goes straight down the route ladder; the corner mark and the ban sentence stay."""
        from core import model_router
        from core.adapters.clipai import REAL_PERSON
        with mock.patch.dict(os.environ, ON):
            vr, leader = self._leader()
            self.p.conn.execute("UPDATE jobs SET model='seedance-2.5' WHERE id=?", (leader["id"],))
            self.assertEqual(seedance_refs.mark_style(self.p.conn, self.ids), "corner_plus")
            self.assertTrue(vr._on_refused(self.p.job(leader["id"]), REAL_PERSON, "may contain real person"))
            self.assertEqual(seedance_refs.mark_style(self.p.conn, self.ids), "corner_plus")
            from core import shots
            self.assertIsNone(shots.group_of(self.p.conn, self.ids[0]))         # the ladder at once
            self.assertIn("seedance", model_router.scene_choice(self.p.conn, self.ids[0])["model"])
            refs = vr._submit_kwargs(self.p.job(leader["id"]))["reference_only"]
            self.assertTrue(refs and all(p.endswith("_marked_corner_plus.png") for p in refs))
            self.assertIn("Never draw a plus sign", vr._submit_args(self.p.job(leader["id"]))[1])

    def test_real_person_refusal_of_unmarked_subject_library_pictures_goes_down_the_ladder(self):
        """Rà gộp 13/10: ảnh đi qua Kho chủ thể (asset://, không dấu) bị từ chối 'người thật' → đổi dấu không đổi gì ở đầu vào
        (gửi lại y hệt, tốn tiền) → đi thẳng bậc tuyến cũ, không ghi ref_mark."""
        from core import shots
        from core.adapters.clipai import REAL_PERSON
        from tests.test_subjects import CountingLibrary
        with mock.patch.dict(os.environ, dict(ON, FEATURE_SEEDANCE_SUBJECTS="1")):
            vr, leader = self._leader()
            vr.provider.supports_subjects = True
            vr.subject_library = CountingLibrary()
            self.p.conn.execute("UPDATE jobs SET model='seedance-2.5' WHERE id=?", (leader["id"],))
            refs = vr._submit_kwargs(self.p.job(leader["id"]))["reference_only"]
            self.assertTrue(refs and all(isinstance(r, dict) for r in refs))
            self.assertTrue(vr._on_refused(self.p.job(leader["id"]), REAL_PERSON, "may contain real person"))
            self.assertIsNone(shots.group_of(self.p.conn, self.ids[0]))         # the ladder at once
            self.assertEqual(seedance_refs.mark_style(self.p.conn, self.ids), "corner_plus")   # no mark step written

    def _end_frame_send(self, deferred):
        """A reference-only shot with a drawn end frame, the Subject Library ON but refusing every picture (Kho đầy, lỗi 6.11)."""
        from core import shots
        from tests.test_subjects import CountingLibrary
        vr, leader = self._leader()
        vr.provider.supports_subjects = True
        vr.subject_library = CountingLibrary("failed")
        end = shots.approved_image_path(self.p.conn, self.data, self.pid, self.ids[1])     # a real picture with the cast in it
        with mock.patch.object(vr, "_sends_group", return_value=None), mock.patch.object(vr, "_end_frame", return_value=end),                 mock.patch.object(vr, "_lip_sync_audio", return_value=None):
            vr._pregen_local, vr._pregen_deferred = deferred, []
            out = vr._base_submit_kwargs(leader)
            vr._pregen_local = False
            out = vr._finish_kwargs(leader, out)
        return out

    def test_kho_full_fallback_marks_the_end_frame_like_the_other_pictures(self):
        """V5 (rà gốc 13/10, G9) — fallback in the runner: the Subject Library refused, the pictures fall back to the marked way, but
        the drawn end frame stayed the UNMARKED copy prepared for the library (refused as a real person, or sent unlike the rest).
        It gets the same mark as the others — with ref_mark_off_face the corner, never the eye."""
        for deferred in (False, True):
            with mock.patch.dict(os.environ, dict(ON, FEATURE_SEEDANCE_SUBJECTS="1")):
                out = self._end_frame_send(deferred)
            refs = out["reference_only"]
            self.assertTrue(refs and all(isinstance(r, str) and r.endswith("_marked_corner_plus.png") for r in refs), (deferred, refs))
            self.assertTrue(out["last_frame"].endswith("_marked_corner_plus.png"), (deferred, out["last_frame"]))

    def test_start_frame_never_eye_marked(self):
        """V5: with the flag on, no picture of the send — the start frames included — carries the eye mark, Kho full or not."""
        with mock.patch.dict(os.environ, dict(ON, FEATURE_SEEDANCE_SUBJECTS="1")):
            out = self._end_frame_send(False)
        self.assertFalse([r for r in out["reference_only"] + [out["last_frame"]] if str(r).endswith("_marked.png")])

    def test_skill_object_guard_reaches_the_sent_motion(self):
        """Lỗi 3 trên đường gửi video thật: câu về tường keo bỏ 'elevator/doors' + câu cấm; shot ném keo → chữ "đã đứng sẵn" + VÀNG gợi ý ghép."""
        vr, leader = self._leader()
        sid = self.ids[0]
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt=? WHERE scene_id=?",
                            ("Kelly throws; the glue wall of grey elevator doors shoots up in front of her.", sid))
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        d["action"] = "Kelly ném bom keo, tường keo mọc lên ngay"
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, {"FEATURE_SKILL_OBJECT_GUARD": "0"}):
            off = vr._submit_args(self.p.job(leader["id"]))[1]
        with mock.patch.dict(os.environ, {"FEATURE_SKILL_OBJECT_GUARD": "1"}):
            on = vr._submit_args(self.p.job(leader["id"]))[1]
        self.assertIn("elevator doors", off)
        self.assertNotIn("is a solid skill object", off)
        self.assertNotIn("elevator", on.lower())
        self.assertIn("grey flat panels", on)
        self.assertNotIn("shoots up", on)                                  # tường xuất hiện luôn (13/10 21:31)
        self.assertIn("already standing at full height", on)
        self.assertIn("is a solid skill object", on)
        codes = {r[0] for r in self.p.conn.execute("SELECT code FROM diag_events")}
        self.assertIn("skill_object_compose", codes)


    def test_skill_object_guard_reaches_the_sent_image_prompt(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        sid = self.ids[0]
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        d["image_prompt"] = "Kelly crouches behind a tall glue wall of grey metal elevator-door panels with small lights."
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        self.p.conn.commit()
        ir = ImageRunner(self.p, MockImageProvider(), self.data)
        job = self.p.job(self.p.create_job(sid, "image_gen"))
        with mock.patch.dict(os.environ, {"FEATURE_SKILL_OBJECT_GUARD": "0"}):
            off = ir._submit_args(job)[0]
        with mock.patch.dict(os.environ, {"FEATURE_SKILL_OBJECT_GUARD": "1"}):
            on = ir._submit_args(job)[0]
        self.assertIn("elevator-door panels", off)
        self.assertNotIn("skill object", off)
        self.assertNotIn("elevator", on.lower())
        self.assertIn("grey metal flat panels", on)
        self.assertIn("is a solid skill object", on)


if __name__ == "__main__":
    unittest.main()
