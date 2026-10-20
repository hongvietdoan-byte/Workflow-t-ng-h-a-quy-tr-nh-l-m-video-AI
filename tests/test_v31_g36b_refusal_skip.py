"""C-G36B (G36 phần 2, #31 1057→1065→1071): Seedance từ chối gói nhóm vì MỘT ảnh (`content[N]`, PrivacyInformation) — bước "Seedance
từng shot" (thứ tự người dùng chốt 2026-09-27) gửi lại đúng ảnh đó trong gói từng shot nên chắc chắn bị từ chối lần nữa: phí một lượt
thử. Cờ refusal_skip_same_picture: shot nào có ảnh bị từ chối trong gói từng shot → sang Kling ngay; shot khác vẫn đi từng shot. Cờ
TẮT = như cũ (nhóm → từng shot → Kling)."""
import json
import os
import unittest
from unittest import mock

from core import model_router, seedance_refs
from tests import test_seedance_refs as group_tests          # module, not the class: pytest would collect its tests here again
from tests.test_seedance_refs import real_png

REFUSED = "[InputImageSensitiveContentDetected.PrivacyInformation] The request failed because the input image 'content[{}]' may " \
          "contain real person."


class RefusalSkipSamePicture(unittest.TestCase):
    _ready = group_tests.SeedanceRefTests._ready             # same fixture as the group tests, without running them again here

    def setUp(self):
        group_tests.SeedanceRefTests.setUp(self)
        self.form = os.path.join(self.data, "kenta_form.png")       # a FORM picture every shot of the group carries (#31 G27/G32)
        real_png(self.form)
        patch = mock.patch("core.seedance_refs.identity_pictures", return_value=[("KENTA FORM", self.form)])
        patch.start()
        self.addCleanup(patch.stop)

    def _flag(self, value):
        os.environ["FEATURE_REFUSAL_SKIP_SAME_PICTURE"] = value
        self.addCleanup(os.environ.pop, "FEATURE_REFUSAL_SKIP_SAME_PICTURE", None)

    def _refuse(self, vr, n):
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        self.p.conn.execute("UPDATE jobs SET model='seedance' WHERE id=?", (leader["id"],))
        self.p.conn.commit()
        sent = vr._reference_sources(leader, vr._sends_group(leader))
        self.assertEqual(sent[len(self.ids)]["path"], self.form)          # Image N+1 (after the N storyboard frames) = the form
        return self.assertTrue(vr._on_refused(self.p.job(leader["id"]), "bad_request", REFUSED.format(n)))

    def _routes(self):
        rows = {r["id"]: json.loads(r["data"] or "{}") for r in self.p.conn.execute("SELECT id, data FROM scenes")}
        return {sid: seedance_refs.route(rows[sid]) for sid in self.ids}

    def test_a_shared_picture_refused_skips_the_per_shot_step(self):
        self._flag("1")
        vr = self._ready()
        self._refuse(vr, len(self.ids) + 1)                                   # content[0] is the text: content[N+1] = the form
        self.assertEqual(set(self._routes().values()), {"kling"})
        self.assertEqual({model_router.scene_choice(self.p.conn, sid)["model"] for sid in self.ids}, {"kling"})
        said = [r[0] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='real_person'")]
        self.assertTrue(any("Image" in m and "Kling" in m and "từng shot" in m for m in said), said)

    def test_one_shots_own_frame_refused_moves_only_that_shot(self):
        self._flag("1")
        vr = self._ready()
        self._refuse(vr, 2)                                                   # content[2] = storyboard frame of the group's Shot 2
        routes = self._routes()
        self.assertEqual(routes[self.ids[1]], "kling")
        self.assertEqual({routes[sid] for sid in self.ids if sid != self.ids[1]}, {"single"})

    def test_no_picture_named_keeps_the_chosen_order(self):
        self._flag("1")
        vr = self._ready()
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        self.assertTrue(vr._on_refused(leader, "real_person", "may contain real person"))
        self.assertEqual(set(self._routes().values()), {"single"})

    def test_flag_off_keeps_group_then_single(self):
        self._flag("0")
        vr = self._ready()
        self._refuse(vr, len(self.ids) + 1)
        self.assertEqual(set(self._routes().values()), {"single"})
        self.assertIn("seedance", model_router.scene_choice(self.p.conn, self.ids[0])["model"])


if __name__ == "__main__":
    unittest.main()
