"""Lỗi hệ thống 4 (#27 13/10, cờ ref_mark_off_face): Seedance 2.5 chép dấu '+' đỏ của ảnh tham chiếu đánh dấu (Kho chủ thể đầy → gửi
ảnh đánh dấu cũ, dấu trên mắt) lên mặt Kelly shot 8–9, 18. Cờ bật: dấu ở góc ảnh + câu cấm theo tên; bị từ chối 'người thật' →
quay lại dấu trên mắt một lần (đổi đầu vào), rồi bậc tuyến cũ. Cùng chỗ: lỗi 3 (cờ skill_object_guard) trên prompt video thật.
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

    def test_real_person_refusal_goes_back_to_the_eye_mark_once_then_the_old_ladder(self):
        from core import model_router
        from core.adapters.clipai import REAL_PERSON
        with mock.patch.dict(os.environ, ON):
            vr, leader = self._leader()
            self.p.conn.execute("UPDATE jobs SET model='seedance-2.5' WHERE id=?", (leader["id"],))
            self.assertEqual(seedance_refs.mark_style(self.p.conn, self.ids), "corner_plus")
            self.assertTrue(vr._on_refused(self.p.job(leader["id"]), REAL_PERSON, "may contain real person"))
            self.assertEqual(seedance_refs.mark_style(self.p.conn, self.ids), "eye_plus")
            from core import shots
            self.assertIsNotNone(shots.group_of(self.p.conn, self.ids[0]))     # still the group: only the mark changed
            refs = vr._submit_kwargs(self.p.job(leader["id"]))["reference_only"]
            self.assertTrue(all(p.endswith("_marked.png") for p in refs))
            self.assertIn("Never draw a plus sign", vr._submit_args(self.p.job(leader["id"]))[1])
            self.assertTrue(vr._on_refused(self.p.job(leader["id"]), REAL_PERSON, "may contain real person"))
            self.assertIsNone(shots.group_of(self.p.conn, self.ids[0]))         # then the ladder as before
            self.assertIn("seedance", model_router.scene_choice(self.p.conn, self.ids[0])["model"])

    def test_skill_object_guard_reaches_the_sent_motion(self):
        """Lỗi 3 trên đường gửi video thật: câu về tường keo bỏ 'elevator/doors' + câu cấm; shot tường mọc lên → VÀNG gợi ý ghép."""
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
