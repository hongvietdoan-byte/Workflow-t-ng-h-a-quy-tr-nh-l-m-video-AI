"""Lỗi hệ thống 2 (#27, 13/10): video tự đổi bố cục / cắt cảnh — cờ `framing_guard` (mặc định TẮT: không đo, không đổi gì).

Fixture thật thu nhỏ ở tests/fixtures/framing_p27/ (dự án #27):
  s17_start_job910.jpg + s17_job912_seedance_reframed.mp4 — 0,6 s đầu job 912 (Seedance 2.5): máy lùi ×0,95 + khung trượt 6 % xuống,
      tháp vẽ thêm mặt đồng hồ; người dùng loại ("lùi máy + thêm mặt đồng hồ").
  s17_start_job893.jpg + s17_job903_seedance_kept.mp4 — job 903 (Seedance 2.5) người dùng DUYỆT: trượt ~5 % (đặc tính Seedance) phải
      KHÔNG bị cờ.   s17_job915_kling_kept.mp4 — job 915 (Kling, bản đang dùng) với ảnh 910: giữ đúng khung đầu.
  s16_job907_jump.mp4 — 0,3–0,9 s job 907: Kelly "nhảy cóc ra xa" (cỡ mặt ×2,6 trong 0,08 s) vì khung cuối vẽ Kelly ở xa.
  s16_start_job836.jpg + s16_end16_far.jpg (khung cuối 16: Kelly lùi sau tường, mặt ×0,61) / s16_end21_kept.jpg (khung cuối 21 người
      dùng giữ — "cùng khoảng cách máy")."""
import json
import os
import shutil
import tempfile
import unittest

import cv2
import numpy as np

from core import clip_measure, features, framing_guard as fg, text_placement
from core.db import connect
from core.pipeline import Pipeline
from tests._flags import flags_on

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "framing_p27")
F = lambda name: os.path.join(FIX, name)  # noqa: E731
HAS_FACES = bool(text_placement.model_path())


def _zoomed(img, s):
    """img seen from further back (s < 1: everything × s about the centre, the border filled by the picture's own edge)."""
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)


def _write_clip(path, frames, fps=24):
    h, w = frames[0].shape[:2]
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        vw.write(f)
    vw.release()
    return path


class FlagTests(unittest.TestCase):
    def test_flag_declared_and_off_by_default(self):
        self.assertIn(fg.FLAG, features.FEATURES)
        self.assertFalse(features.FEATURES[fg.FLAG]["verified"])
        self.assertNotIn(fg.FLAG, features.OPT_IN_ONLY)

    def test_off_measures_nothing(self):
        flags_on(self, fg.FLAG, value=False)
        self.assertIsNone(fg.end_frame_check(F("s16_start_job836.jpg"), F("s16_end16_far.jpg")))


class EndFrameDistanceTests(unittest.TestCase):
    """(a) TRƯỚC gen: khung cuối phải cùng khoảng cách máy với ảnh đầu."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    @unittest.skipUnless(HAS_FACES, "YuNet face model not installed")
    def test_p27_end_frame_16_person_further_back_is_flagged(self):
        r = fg.end_frame_distance(F("s16_start_job836.jpg"), F("s16_end16_far.jpg"))
        self.assertIs(r["ok"], False)
        self.assertAlmostEqual(r["scale"], 1.0, delta=0.03)          # the house behind did not move: the PERSON is further back
        self.assertLess(r["face_ratio"], 1 / fg.END_FACE)
        self.assertIn("khác khoảng cách máy", r["why"])
        self.assertIn("× 0.6", r["why"])                               # the number is said

    def test_p27_end_frame_21_kept_by_the_person_passes(self):
        r = fg.end_frame_distance(F("s16_start_job836.jpg"), F("s16_end21_kept.jpg"))
        self.assertIs(r["ok"], True)
        self.assertAlmostEqual(r["scale"], 1.0, delta=0.03)

    def test_camera_pulled_back_is_flagged_by_the_background(self):
        start = cv2.imread(F("s16_end21_kept.jpg"))
        far = os.path.join(self.tmp, "far.png")
        cv2.imwrite(far, _zoomed(start, 0.75))
        r = fg.end_frame_distance(F("s16_end21_kept.jpg"), far)
        self.assertIs(r["ok"], False)
        self.assertAlmostEqual(r["scale"], 0.75, delta=0.04)
        self.assertIn("lùi xa", r["why"])

    def test_cannot_measure_is_said_not_passed(self):
        blank = os.path.join(self.tmp, "blank.png")
        cv2.imwrite(blank, np.full((640, 360, 3), 128, np.uint8))
        r = fg.end_frame_distance(blank, blank)
        self.assertIsNone(r["ok"])
        self.assertIn("không đo được", r["note"])
        self.assertIsNone(fg.end_frame_distance(F("s16_start_job836.jpg"), os.path.join(self.tmp, "none.png"))["ok"])


class ClipFramingTests(unittest.TestCase):
    """(b) SAU gen: khung 0 so ảnh đầu, zoom / lùi máy, người nhảy vọt, cắt cảnh."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_p27_job912_seedance_reframed_is_red(self):
        r = fg.clip_framing(F("s17_job912_seedance_reframed.mp4"), F("s17_start_job910.jpg"))
        self.assertEqual(r["flag"], "framing")
        self.assertIn("frame0", r["kinds"])
        self.assertGreater(r["frame0"]["corner"], fg.F0_CORNER)
        self.assertIn("khung 0 lệch ảnh đầu", r["why"])
        self.assertIn("đổi model", r["suggest"])

    def test_p27_job903_seedance_approved_by_the_person_is_not_flagged(self):
        r = fg.clip_framing(F("s17_job903_seedance_kept.mp4"), F("s17_start_job893.jpg"))
        self.assertIsNone(r["flag"])
        self.assertTrue(r["frame0_measured"])

    def test_p27_job915_kling_keeps_the_first_frame(self):
        r = fg.clip_framing(F("s17_job915_kling_kept.mp4"), F("s17_start_job910.jpg"))
        self.assertIsNone(r["flag"])
        self.assertLess(r["frame0"]["corner"], 0.02)

    @unittest.skipUnless(HAS_FACES, "YuNet face model not installed")
    def test_p27_job907_person_jumps_away_is_red(self):
        r = fg.clip_framing(F("s16_job907_jump.mp4"), None)
        self.assertEqual(r["flag"], "framing")
        self.assertIn("jump", r["kinds"])
        self.assertIn("bỏ khung cuối", r["suggest"])
        self.assertIn("không có ảnh khung đầu", r["note"])            # what was not measured is said

    def test_camera_pulling_back_inside_the_clip_is_red(self):
        start = cv2.imread(F("s17_start_job910.jpg"))
        frames = [_zoomed(start, 1 - 0.3 * i / 23) for i in range(24)]
        clip = _write_clip(os.path.join(self.tmp, "pull.mp4"), frames)
        r = fg.clip_framing(clip, F("s17_start_job910.jpg"))
        self.assertEqual(r["flag"], "framing")
        self.assertIn("zoom", r["kinds"])
        self.assertIn("máy lùi", r["why"])

    def test_a_cut_is_red(self):
        r = fg.clip_framing(F("s17_job915_kling_kept.mp4"), F("s17_start_job910.jpg"), cuts=[0.4])
        self.assertEqual(r["kinds"], ["cut"])

    def test_nothing_to_measure_is_said(self):
        flat = [np.full((854, 480, 3), 90, np.uint8) for _ in range(12)]
        clip = _write_clip(os.path.join(self.tmp, "flat.mp4"), flat)
        r = fg.clip_framing(clip, None)
        self.assertIsNone(r["flag"])
        self.assertFalse(r["frame0_measured"])
        self.assertIn("zoom", r["note"])
        self.assertIn("không có ảnh khung đầu", r["note"])
        r = fg.clip_framing(clip, F("s17_start_job910.jpg"))          # a blank clip for a real picture: the layout is gone → red
        self.assertEqual(r["kinds"], ["frame0"])
        r = fg.clip_framing(os.path.join(self.tmp, "missing.mp4"), None)
        self.assertIs(r["measured"], False)
        self.assertIn("chưa đo được", r["note"])


class MeasureWiringTests(unittest.TestCase):
    def test_flag_off_measure_has_no_framing_key(self):
        flags_on(self, fg.FLAG, value=False)
        out = clip_measure.measure(F("s17_job912_seedance_reframed.mp4"), F("s17_start_job910.jpg"))
        self.assertNotIn("framing", out)
        self.assertNotIn("framing", out["flags"])

    def test_flag_on_measure_flags_framing(self):
        flags_on(self, fg.FLAG)
        out = clip_measure.measure(F("s17_job912_seedance_reframed.mp4"), F("s17_start_job910.jpg"))
        self.assertIn("framing", out["flags"])
        self.assertIn("đổi model", out["framing"]["suggest"])


class ApplyQcTests(unittest.TestCase):
    GOOD = {"identity": .95, "physics": .95, "motion_match": .95, "artifacts": .95}
    RED = {"framing": {"flag": "framing", "kinds": ["frame0"], "why": "đổi bố cục / cắt cảnh: khung 0 lệch ảnh đầu: tỉ lệ × 0.95",
                       "suggest": "gợi ý: đổi model"}, "flags": ["framing"]}

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("framing", operating_mode="auto", threshold=0.82, max_retry=2)
        self.sid = self.p.create_scene(self.pid, 1)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY KL"]}), self.sid))
        self.p.conn.commit()

    def clip(self, tier=None):
        jid = self.p.create_job(self.sid, "video_gen")
        if tier:
            self.p.conn.execute("UPDATE jobs SET quality_tier=? WHERE id=?", (tier, jid))
            self.p.conn.commit()
        self.p.start(jid)
        self.p.succeed(jid)
        return jid

    def diag(self, code):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code=?", (code,))]

    def test_flag_off_a_red_measure_changes_nothing(self):
        flags_on(self, fg.FLAG, value=False)
        self.assertEqual(self.p.apply_qc(self.clip(), self.GOOD, measured=self.RED), "approved")
        self.assertEqual(self.diag("framing_guard"), [])

    def test_red_framing_holds_a_passing_clip_for_the_person(self):
        flags_on(self, fg.FLAG)
        jid = self.clip()
        self.assertEqual(self.p.apply_qc(jid, self.GOOD, issues="Fix x.", autofix=True, measured=self.RED), "needs_review")
        self.assertEqual(self.p.job(jid)["state"], "pending_review")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE scene_id=? AND state='queued'", (self.sid,)).fetchone()[0], 0)
        note = self.p.conn.execute("SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (jid,)).fetchone()["note"]
        self.assertIn("khung 0 lệch ảnh đầu", note)
        self.assertIn("đổi model", note)
        said = self.diag("framing_guard")
        self.assertEqual(len(said), 1)
        self.assertIn("ĐỎ", said[0])
        from core import compare                                        # the hold marker is not a QC score
        self.assertAlmostEqual(compare.metrics(self.p, self.pid, tempfile.mkdtemp())["qc_video"], 0.95)

    def test_red_framing_on_a_draft_blocks_the_autopilot(self):
        from core import autopilot, quality_tier
        flags_on(self, fg.FLAG)
        jid = self.clip("draft")
        self.p.apply_qc(jid, self.GOOD, measured=self.RED)
        self.assertEqual(self.p.job(jid)["state"], "pending_review")
        reasons = autopilot._flag_reasons(self.p, self.p.job(jid))
        self.assertTrue(any("bố cục" in r for r in reasons), reasons)
        self.assertTrue(quality_tier is not None)

    def test_not_measured_is_said_yellow_and_does_not_block(self):
        flags_on(self, fg.FLAG)
        self.assertEqual(self.p.apply_qc(self.clip(), self.GOOD, measured=None), "approved")
        said = self.diag("framing_guard")
        self.assertEqual(len(said), 1)
        self.assertIn("chưa đo được", said[0])

    def test_a_clean_measure_approves(self):
        flags_on(self, fg.FLAG)
        ok = {"framing": {"flag": None, "measured": True, "frame0_measured": True}, "flags": []}
        self.assertEqual(self.p.apply_qc(self.clip(), self.GOOD, measured=ok), "approved")
        self.assertEqual(self.diag("framing_guard"), [])


class RunnerEndFrameTests(unittest.TestCase):
    """(a) wiring: runner._end_frame does not send an end frame at another camera distance (VÀNG with the numbers)."""

    def setUp(self):
        from core import batch, end_frames, llm_runner, model_router
        from core.providers import MockImageProvider, MockVideoProvider
        from core.runner import VideoRunner
        from tests.test_end_frames import _shot_with_end_state
        from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project
        flags_on(self, "end_frames")
        self.p, self.pid = kenta_project()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        self.sid = _shot_with_end_state(self.p, self.pid)
        self.data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.data, True)
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        model_router.set_override(self.p.conn, self.sid, "kling")
        end_frames.queue(self.p, self.pid)
        img = MockImageProvider()
        end_frames.tick(self.p, self.pid, img, self.data)
        end_frames.tick(self.p, self.pid, img, self.data)
        self.drawn = end_frames.usable_path(self.p.conn, self.sid)
        self.assertTrue(self.drawn)
        from core import shots
        self.start = shots.approved_image_path(self.p.conn, self.data, self.pid, shots.image_scene(self.p.conn, self.sid))
        self.assertTrue(self.start)
        pic = cv2.imread(F("s16_end21_kept.jpg"))
        cv2.imwrite(self.start, pic)
        cv2.imwrite(self.drawn, _zoomed(pic, 0.75))                       # the end frame drawn from further back
        batch.queue_videos(self.p, self.pid, self.data)
        self.job = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid,)).fetchone()
        self.vr = VideoRunner(self.p, MockVideoProvider(), self.data)

    def _said(self):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='end_frame_distance'")]

    def test_flag_off_sends_the_drawn_end_frame_as_before(self):
        flags_on(self, fg.FLAG, value=False)
        self.assertEqual(self.vr._end_frame(self.job, "kling"), self.drawn)
        self.assertEqual(self._said(), [])

    def test_end_frame_at_another_distance_is_not_sent_and_said_once(self):
        flags_on(self, fg.FLAG)
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        said = self._said()
        self.assertEqual(len(said), 1)
        self.assertIn("KHÔNG kèm khung cuối", said[0])
        self.assertIn("× 0.7", said[0])

    def test_same_distance_end_frame_is_sent(self):
        flags_on(self, fg.FLAG)
        cv2.imwrite(self.drawn, cv2.imread(F("s16_end21_kept.jpg")))
        self.assertEqual(self.vr._end_frame(self.job, "kling"), self.drawn)

    def test_pregen_says_it_yellow(self):
        from core import video_pregen
        flags_on(self, fg.FLAG)
        plan = {"model": "kling", "duration": 4, "last_frame": self.drawn, "group_ids": [], "data_dir": self.data, "project_id": self.pid}
        data = {k: v for k, v in video_pregen._data(self.p.conn, self.sid).items() if k != "byd"}
        out = []
        video_pregen._check_end(self.p.conn, self.sid, plan, data, out)
        hits = [i for i in out if "khoảng cách máy" in i["ly_do"]]
        self.assertEqual([i["muc"] for i in hits], [video_pregen.VANG])
        self.assertIn("khác khoảng cách máy", hits[0]["ly_do"])
        flags_on(self, fg.FLAG, value=False)
        out = []
        video_pregen._check_end(self.p.conn, self.sid, plan, data, out)
        self.assertFalse([i for i in out if "khoảng cách máy" in i["ly_do"]])


if __name__ == "__main__":
    unittest.main()
