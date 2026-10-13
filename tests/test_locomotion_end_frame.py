"""Hộp thư 12/10 18:13 (#27 shot 3, job 782 → 783): a run / walk generated much longer than the shot gets no drawn end frame, and a run
the camera follows gets the ground sentence — flag locomotion_end_frame (off by default: the old text and the old send, byte for byte)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import end_frames, llm_runner, motion_physics, video_pregen
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import VideoRunner
from tests._flags import flags_on
from tests.test_end_frames import _shot_with_end_state
from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project

RUN_OLD = ("Each foot lands under the body with no sliding, the arms swing opposite the legs, the body leans forward, and hair and loose "
           "clothes trail behind.")


class SentenceTests(unittest.TestCase):
    def test_default_text_is_unchanged(self):
        self.assertEqual(motion_physics.sentence("Kelly sprints toward the gate"), RUN_OLD)
        self.assertEqual(motion_physics.sentence("Kelly sprints toward the gate", "follow"), RUN_OLD)       # flag off

    def test_ground_sentence_only_for_a_followed_run_or_walk(self):
        flags_on(self, "locomotion_end_frame")
        self.assertEqual(motion_physics.sentence("Kelly sprints toward the gate", "follow"),
                         RUN_OLD + " " + motion_physics.GROUND_SENTENCE)
        self.assertTrue(motion_physics.sentence("Kelly chạy về phía cổng", "push_in").endswith("never running in place."))
        self.assertTrue(motion_physics.sentence("Kelly runs and jumps over the crate", "tracking").endswith("never running in place."))
        self.assertEqual(motion_physics.sentence("Kelly sprints toward the gate"), RUN_OLD)                # no camera given: old text
        self.assertEqual(motion_physics.sentence("Kelly sprints toward the gate", "static"), RUN_OLD)
        self.assertEqual(motion_physics.sentence("Kelly picks up the rifle", "follow"),
                         motion_physics.sentence("Kelly picks up the rifle"))                             # not moving through space

    def test_in_place_risk(self):
        run = {"action": "Kelly chạy tới cổng", "motion_en": {"action": "Kelly runs to the gate"}}
        self.assertIn("chạy tại chỗ", motion_physics.in_place_risk(run, 2, 3))                          # 3 > 2 × 1.3
        self.assertIsNone(motion_physics.in_place_risk(run, 3, 3))
        self.assertIsNone(motion_physics.in_place_risk(run, 2.5, 3))                                      # 3 ≤ 3.25
        self.assertIsNone(motion_physics.in_place_risk({"action": "Kelly looks up"}, 1, 4))
        self.assertIsNotNone(motion_physics.in_place_risk({"action": "x", "motion_en": {"action": "she walks forward"}}, 1, 3))


class RunnerEndFrameTests(unittest.TestCase):
    def setUp(self):
        from core import batch, model_router
        flags_on(self, "end_frames")
        self.p, self.pid = kenta_project()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        self.sid = _shot_with_end_state(self.p, self.pid)
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"])
        data.update(action="Kenta sprints toward the gate", duration_s=2, camera_move="follow")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), self.sid))
        self.p.conn.commit()
        self.data = tempfile.mkdtemp()
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=2 WHERE scene_id=?", (self.sid,))
        self.p.conn.commit()
        model_router.set_override(self.p.conn, self.sid, "kling")
        end_frames.queue(self.p, self.pid)
        img = MockImageProvider()
        end_frames.tick(self.p, self.pid, img, self.data)
        end_frames.tick(self.p, self.pid, img, self.data)
        self.drawn = end_frames.usable_path(self.p.conn, self.sid)
        self.assertTrue(self.drawn)
        batch.queue_videos(self.p, self.pid, self.data)
        self.job = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid,)).fetchone()
        self.vr = VideoRunner(self.p, MockVideoProvider(), self.data)

    def _said(self):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='locomotion_end_frame'")]

    def test_flag_off_sends_the_drawn_end_frame_as_before(self):
        self.assertEqual(self.vr._end_frame(self.job, "kling"), self.drawn)
        self.assertEqual(self._said(), [])

    def test_a_short_run_generated_at_3_s_goes_without_the_drawn_end_frame_and_says_so(self):
        flags_on(self, "locomotion_end_frame")
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        said = self._said()
        self.assertEqual(len(said), 1)                                                   # once per job
        self.assertIn("KHÔNG kèm khung cuối", said[0])

    def test_a_run_as_long_as_its_clip_keeps_the_end_frame(self):
        flags_on(self, "locomotion_end_frame")
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=3 WHERE scene_id=?", (self.sid,))
        self.p.conn.commit()
        self.assertEqual(self.vr._end_frame(self.job, "kling"), self.drawn)

    def test_sprint_end_frame_same_scale_dropped(self):
        """V12 (rà gốc 13/10, G12): the clip is as long as the shot (no stretch), the camera follows the run, but the drawn end frame
        shows the background at the SAME size as the start picture (no ground covered) → not sent, said (needs framing_guard: the
        OpenCV measure). A end frame where the destination grew is sent."""
        import cv2
        from core import framing_guard, shots
        from tests.test_framing_guard import F, _zoomed
        flags_on(self, "locomotion_end_frame", framing_guard.FLAG)
        self.p.conn.execute("UPDATE motion_prompts SET duration_sec=3 WHERE scene_id=?", (self.sid,))
        self.p.conn.commit()
        start = shots.approved_image_path(self.p.conn, self.data, self.pid, shots.image_scene(self.p.conn, self.sid))
        pic = cv2.imread(F("s16_end21_kept.jpg"))
        cv2.imwrite(start, pic)
        cv2.imwrite(self.drawn, pic)                                                      # same place, same size: ran in place
        framing_guard._END_CACHE.clear()
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        said = self._said()
        self.assertEqual(len(said), 1)
        self.assertIn("cùng cỡ", said[0])
        self.assertIn("KHÔNG kèm khung cuối", said[0])
        cv2.imwrite(self.drawn, _zoomed(pic, 1.10))                                       # the destination grew: ground covered
        framing_guard._END_CACHE.clear()
        self.vr._said_once = set()
        with mock.patch.object(framing_guard, "face_height", return_value=0.12):
            self.assertEqual(self.vr._end_frame(self.job, "kling"), self.drawn)

    def test_same_ground_ignores_matching_person_on_new_background(self):
        """R4 (rà S3): the person fills the middle of both frames (same size, same place — the camera follows), the ground on both sides
        is another place: RANSAC used to lock on the person (× 1,00, corner 0) and drop a RIGHT end frame. The person's box is masked
        (YuNet, here patched) → no verdict. The same place with the person masked is still judged."""
        import cv2
        from core import framing_guard
        from tests.test_framing_guard import F
        tmp = tempfile.mkdtemp()
        a = cv2.imread(F("s17_start_job910.jpg"))
        h, w = a.shape[:2]
        b = cv2.resize(cv2.imread(F("s16_start_job836.jpg")), (w, h))
        person = cv2.resize(cv2.imread(F("s16_end16_far.jpg")), (w, h))
        x0, x1 = int(w * 0.3), int(w * 0.7)
        start, end = a.copy(), b.copy()
        start[:, x0:x1] = person[:, x0:x1]
        end[:, x0:x1] = person[:, x0:x1]
        sp, ep = os.path.join(tmp, "s.png"), os.path.join(tmp, "e.png")
        cv2.imwrite(sp, start)
        cv2.imwrite(ep, end)
        run = {"action": "Kenta sprints toward the gate", "camera_move": "follow"}
        box = [(0.28, 0.0, 0.72, 1.0)]
        with mock.patch.object(framing_guard, "person_boxes", return_value=box, create=True):
            self.assertIsNone(motion_physics.same_ground(run, framing_guard.end_frame_distance(sp, ep)))
            self.assertTrue(motion_physics.same_ground(run, framing_guard.end_frame_distance(sp, sp)))

    def test_same_ground_needs_a_followed_run(self):
        m = {"scale": 1.0, "corner": 0.01}
        run = {"action": "Kenta sprints toward the gate", "camera_move": "follow"}
        self.assertTrue(motion_physics.same_ground(run, m))
        self.assertIsNone(motion_physics.same_ground(dict(run, camera_move="static"), m))   # the person crosses a still frame
        self.assertIsNone(motion_physics.same_ground({"action": "Kenta waves", "camera_move": "follow"}, m))
        self.assertIsNone(motion_physics.same_ground(run, {"scale": 1.12, "corner": 0.06}))
        self.assertIsNone(motion_physics.same_ground(run, {"scale": None}))

    def test_pregen_says_it_yellow(self):
        flags_on(self, "locomotion_end_frame")
        plan = {"model": "kling", "duration": 2, "last_frame": None, "group_ids": [], "data_dir": self.data}
        data = {k: v for k, v in video_pregen._data(self.p.conn, self.sid).items() if k != "byd"}
        out = []
        video_pregen._check_end(self.p.conn, self.sid, plan, data, out)
        self.assertEqual([i["muc"] for i in out], [video_pregen.VANG])
        self.assertIn("locomotion_end_frame", out[0]["ly_do"])
        out = []
        video_pregen._check_end(self.p.conn, self.sid, dict(plan, last_frame=self.drawn), data, out)
        self.assertTrue(any("nên bỏ khung cuối vẽ" in i["ly_do"] for i in out))


if __name__ == "__main__":
    unittest.main()
