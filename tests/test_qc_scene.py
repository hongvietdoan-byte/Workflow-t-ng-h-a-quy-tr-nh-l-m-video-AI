"""QC per script scene (flag scene_qc, 2026-09-27): layer 0 code checks with thresholds measured on real frames; layer 1 one strict Claude
call per scene — every check needs visible evidence, a failed check can never pass, the root cause picks what happens next."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_runner, qc_scene, shots
from tests.test_v3 import _approve_all_images, kenta_project
from tests._flags import flags_clear, flags_on, flags_on_ctx, flags_on_deco  # noqa: F401


def picture(path, light=0.6):
    """A picture of the given mean light with some content (a flat one is caught as blank); light 0 = black."""
    from PIL import Image, ImageDraw
    v = int(255 * light)
    im = Image.new("RGB", (180, 320), (v, v, v))
    if light > 0:
        d = ImageDraw.Draw(im)
        for y in range(0, 320, 8):
            d.line([(0, y), (180, y)], fill=(min(v + 40, 255),) * 3 if (y // 8) % 2 else (max(v - 40, 0),) * 3, width=4)
    im.save(path)
    return path


class LayerZeroTests(unittest.TestCase):
    def setUp(self):
        self.path = picture(os.path.join(tempfile.mkdtemp(), "f.png"))

    def test_sizes_measured_on_real_frames(self):
        self.assertEqual(qc_scene.measured_size(0.665), "ECU")      # #7 frame 3
        self.assertEqual(qc_scene.measured_size(0.259), "CU")
        self.assertEqual(qc_scene.measured_size(0.226), "MCU")      # #8 S1·1 asked CU, looked MCU
        self.assertEqual(qc_scene.measured_size(0.15), "MS")
        self.assertEqual(qc_scene.measured_size(0.05), "WS")

    def test_a_close_up_drawn_wider_is_redrawn_with_a_framing_fix(self):
        with mock.patch("core.text_placement.face_boxes", return_value=[(0.3, 0.2, 0.6, 0.426)]):
            flags = qc_scene.check_frame(self.path, {"size": "CU", "characters": ["KELLY"]})
        size = next(f for f in flags if f["code"] == "shot_size")
        self.assertEqual(size["severity"], "redraw")
        self.assertIn("close-up", size["fix"])

    def test_a_medium_shot_of_the_right_size_passes(self):
        with mock.patch("core.text_placement.face_boxes", return_value=[(0.4, 0.25, 0.55, 0.40)]):
            self.assertEqual(qc_scene.check_frame(self.path, {"size": "MS", "characters": ["KELLY"]}), [])

    def test_a_dark_night_face_and_eyes_under_the_top_bar(self):
        dark = picture(os.path.join(tempfile.mkdtemp(), "d.png"), light=0.08)
        with mock.patch("core.text_placement.face_boxes", return_value=[(0.3, 0.02, 0.6, 0.24)]):
            flags = {f["code"]: f for f in qc_scene.check_frame(dark, {"size": "MCU", "time": "night", "characters": ["KELLY"]})}
        self.assertEqual(flags["dark_face"]["severity"], "redraw")
        self.assertEqual(flags["top_bar"]["severity"], "redraw")

    def test_a_black_or_flat_picture_is_redrawn_without_asking_claude(self):
        black = picture(os.path.join(tempfile.mkdtemp(), "b.png"), light=0.0)
        flags = qc_scene.check_frame(black, {"size": "MS"})
        self.assertEqual([(f["code"], f["severity"]) for f in flags], [("blank", "redraw")])
        missing = qc_scene.check_frame(os.path.join(tempfile.mkdtemp(), "none.png"), {"size": "MS"})
        self.assertEqual(missing[0]["code"], "blank")

    def test_no_detector_no_guess(self):
        with mock.patch("core.text_placement.face_boxes", return_value=None):
            self.assertEqual(qc_scene.check_frame(self.path, {"size": "CU"}), [])


def frame(k, verdict="pass", cause="none", failed=(), fix=""):
    checks = {c: {"ok": c not in failed, "evidence": f"thấy rõ chi tiết {c} ở khung {k}"} for c in qc_scene.CHECKS}
    return {"k": k, "shot": f"S1·{k}", "seen": "Kelly đứng trước tháp", "checks": checks, "verdict": verdict, "root_cause": cause,
            "problem": "lỗi cụ thể" if verdict != "pass" else "", "fix": fix}


class ValidateTests(unittest.TestCase):
    labels = [(1, "K1"), (2, "K2")]

    def ok(self, frames):
        return qc_scene.validate({"frames": frames, "scene": {"ok": True, "notes": ""}}, self.labels)

    def test_a_failed_check_can_never_pass(self):
        from core.llm_io import SchemaError
        with self.assertRaises(SchemaError):
            self.ok([frame(1, failed=("identity",)), frame(2)])

    def test_evidence_must_be_something_seen(self):
        from core.llm_io import SchemaError
        f = frame(1)
        f["checks"]["place"]["evidence"] = "ổn"
        with self.assertRaises(SchemaError):
            self.ok([f, frame(2)])

    def test_every_frame_once_and_an_english_fix(self):
        from core.llm_io import SchemaError
        with self.assertRaises(SchemaError):
            self.ok([frame(1)])                                               # K2 missing
        with self.assertRaises(SchemaError):
            self.ok([frame(1), frame(2, "fix", "prompt", ("framing",), "Khung cận hơn")])
        self.ok([frame(1), frame(2, "fix", "prompt", ("framing",), "Frame as a close-up of Kelly's face.")])


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        _approve_all_images(self.p, self.pid, self.data)   # the mock pictures are flat: made before layer 0 is on
        flags_on(self, "scene_qc")
        rows = shots.shots_of(self.p, self.pid)
        self.scene = rows[0]["data"]["story_scene"]
        self.rows = [r for r in rows if r["data"]["story_scene"] == self.scene]
        self.assertGreaterEqual(len(self.rows), 3)
        for r in self.rows:                                                   # the pictures wait for a decision again
            j = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'", (r["id"],)).fetchone()
            self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (j["id"],))
            picture(os.path.join(self.data, str(self.pid), "images", f"job_{j['id']}.png"))
        self.p.conn.commit()

    def client(self, frames):
        class C:
            name = "fake"
            asked = []

            def complete(inner, prompt, images=()):
                inner.asked.append((prompt, [lab for lab, _ in images]))
                return llm_runner.LlmReply(json.dumps({"frames": frames, "scene": {"ok": False, "notes": ""}}), 100, 50)
        return C()

    def test_until_it_passes_its_acceptance_every_frame_waits_for_a_person(self):
        os.environ.pop("FEATURE_SCENE_QC_TRUSTED", None)
        frames = [frame(1)] + [frame(k, "fix", "model", ("artifacts",), "Kelly's left hand has exactly five fingers.")
                               for k in range(2, len(self.rows) + 1)]
        res = qc_scene.review_scene(self.p, self.pid, self.scene, self.client(frames), self.data)
        self.assertTrue(all(v.startswith("giữ cho người") for v in res["applied"].values()))
        states = {self.p.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='image_gen' ORDER BY id DESC LIMIT 1",
                                      (r["id"],)).fetchone()["state"] for r in self.rows}
        self.assertEqual(states, {"pending_review"})                          # nothing approved, nothing redrawn by an untrusted QC

    def test_one_call_per_scene_and_each_verdict_does_the_right_thing(self):
        os.environ["FEATURE_SCENE_QC_TRUSTED"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_SCENE_QC_TRUSTED", None)
        n = len(self.rows)
        frames = [frame(1), frame(2, "fix", "model", ("artifacts",), "Kelly's left hand has exactly five fingers."),
                  frame(3, "fix", "plan", ("action",))] + [frame(k, "doubt", "none", ("identity",)) for k in range(4, n + 1)]
        c = self.client(frames)
        res = qc_scene.review_scene(self.p, self.pid, self.scene, c, self.data)
        self.assertEqual(len(c.asked), 1)                                     # the whole scene in one call
        prompt, labels = c.asked[0]
        self.assertIn("Bảng shot của cảnh", prompt)
        self.assertTrue(any("Tấm ghép" in lab for lab in labels))
        states = [self.p.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='image_gen' ORDER BY id DESC LIMIT 1",
                                      (r["id"],)).fetchone()["state"] for r in self.rows]
        self.assertEqual(res["applied"]["K1"], "duyệt")
        self.assertEqual(states[0], "approved")
        self.assertEqual(states[1], "queued")                                 # drawn again…
        new = self.p.conn.execute("SELECT retry_reason FROM jobs WHERE scene_id=? AND type='image_gen' ORDER BY id DESC LIMIT 1",
                                  (self.rows[1]["id"],)).fetchone()
        self.assertIn("five fingers", new["retry_reason"])                   # …with the fix, not the same input
        self.assertEqual(states[2], "pending_review")                         # the shot table is wrong: a person decides
        from core import autopilot
        held = autopilot._flag_reasons(self.p, self.p.job(self.p.conn.execute(
            "SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' ORDER BY id DESC LIMIT 1", (self.rows[2]["id"],)).fetchone()["id"]))
        self.assertIn("QC cảnh giữ cho người xem", held)

    def layer_one_on(self):
        os.environ["FEATURE_SCENE_QC_CLAUDE"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_SCENE_QC_CLAUDE", None)

    def test_the_same_pictures_are_judged_once(self):
        self.layer_one_on()
        frames = [frame(k) for k in range(1, len(self.rows) + 1)]
        c = self.client(frames)
        qc_scene.run_ready_scenes(self.p, self.pid, c, self.data)
        before = len(c.asked)
        self.assertGreaterEqual(before, 1)
        qc_scene.run_ready_scenes(self.p, self.pid, c, self.data)
        self.assertEqual(len(c.asked), before)

    def test_layer_one_off_no_claude_call_and_the_frames_wait_for_a_person(self):
        """#8 2026-09-27: layer 1 failed its acceptance and re-judging whole scenes cost ~0.5 USD for notes — off by default."""
        c = self.client([frame(k) for k in range(1, len(self.rows) + 1)])
        r = qc_scene.run_ready_scenes(self.p, self.pid, c, self.data)
        self.assertEqual(c.asked, [])
        self.assertIn(self.scene, r["waiting"])
        states = {self.p.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='image_gen' ORDER BY id DESC LIMIT 1",
                                      (x["id"],)).fetchone()["state"] for x in self.rows}
        self.assertEqual(states, {"pending_review"})

    def test_after_a_redraw_only_the_changed_frame_and_its_neighbours_are_looked_at(self):
        self.layer_one_on()
        n = len(self.rows)
        qc_scene.run_ready_scenes(self.p, self.pid, self.client([frame(k) for k in range(1, n + 1)]), self.data)
        last = self.rows[-1]                                                   # a new picture for the scene's last shot
        new = self.p.create_job(last["id"], "image_gen")
        self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (new,))
        self.p.conn.commit()
        picture(os.path.join(self.data, str(self.pid), "images", f"job_{new}.png"))
        c = self.client([frame(1), frame(2)])
        qc_scene.run_ready_scenes(self.p, self.pid, c, self.data)
        self.assertEqual(len(c.asked), 1)
        self.assertIn(f"S{self.scene}·{last['data']['shot_no']}", c.asked[0][0])
        self.assertLess(c.asked[0][0].count(f"S{self.scene}·"), n)           # not the whole scene again
        again = len(c.asked)
        qc_scene.run_ready_scenes(self.p, self.pid, c, self.data)
        self.assertEqual(len(c.asked), again)                                  # the scene's new set counts as judged

    def test_to_review_keeps_the_changed_frames_and_their_neighbours(self):
        frames = [{"job_id": j} for j in (1, 2, 3, 4, 5)]
        self.assertEqual([f["job_id"] for f in qc_scene.to_review(frames, [1, 2, 3, 4, 5, 9])], [1, 2, 3, 4, 5])
        self.assertEqual([f["job_id"] for f in qc_scene.to_review(frames, [])], [1, 2, 3, 4, 5])
        frames[2] = {"job_id": 7}
        self.assertEqual([f["job_id"] for f in qc_scene.to_review(frames, [1, 2, 3, 4, 5])], [2, 7, 4])


class RunnerLayerZeroTests(unittest.TestCase):
    def test_a_sure_layer_zero_fault_is_drawn_again_with_its_fix(self):
        flags_on(self, "scene_qc")
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        p, pid = kenta_project(shot_mode="per_shot")
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        row = shots.shots_of(p, pid)[0]
        jid = p.create_job(row["id"], "image_gen")
        r = ImageRunner(p, MockImageProvider(polls_to_finish=1), data)
        sure = [{"code": "shot_size", "severity": "redraw", "problem": "cỡ cảnh MCU — xin CU", "fix": "Frame as a close-up."}]
        with mock.patch("core.qc_scene.check_frame", return_value=sure):
            for _ in range(4):
                r.submit_pending(pid)
                r.poll_once(pid)
                if p.job(jid)["state"] != "running" and p.job(jid)["state"] != "queued":
                    break
        self.assertEqual(p.job(jid)["state"], "cancelled")                   # failed → retried (the old one closed)
        new = p.conn.execute("SELECT id, retry_reason FROM jobs WHERE parent_job_id=?", (jid,)).fetchone()
        self.assertIn("close-up", new["retry_reason"])
        with mock.patch("core.qc_scene.check_frame", return_value=[dict(sure[0])]):   # the same fault after its fix: no 2nd redraw
            for _ in range(4):
                r.submit_pending(pid)
                r.poll_once(pid)
                if p.job(new["id"])["state"] not in ("running", "queued"):
                    break
        self.assertEqual(p.job(new["id"])["state"], "succeeded")
        self.assertIsNone(p.conn.execute("SELECT 1 FROM jobs WHERE parent_job_id=?", (new["id"],)).fetchone())


class TraineeLayerZeroTests(unittest.TestCase):
    """B3 học việc 08/10: scene_qc 🎓 — layer 0 checks and records what it WOULD do; no redraw, no layer0.json, old QC stays off."""

    def setUp(self):
        from tests._flags import flags_trainee
        flags_trainee(self, "scene_qc")
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())

    def test_a_sure_fault_is_only_recorded(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        row = shots.shots_of(self.p, self.pid)[0]
        jid = self.p.create_job(row["id"], "image_gen")
        r = ImageRunner(self.p, MockImageProvider(polls_to_finish=1), self.data)
        sure = [{"code": "shot_size", "severity": "redraw", "problem": "cỡ cảnh MCU — xin CU", "fix": "Frame as a close-up."}]
        with mock.patch("core.qc_scene.check_frame", return_value=sure):
            for _ in range(4):
                r.submit_pending(self.pid)
                r.poll_once(self.pid)
                if self.p.job(jid)["state"] not in ("running", "queued"):
                    break
        self.assertEqual(self.p.job(jid)["state"], "succeeded")             # no RedrawWithFix
        self.assertIsNone(self.p.conn.execute("SELECT 1 FROM jobs WHERE parent_job_id=?", (jid,)).fetchone())
        self.assertEqual(qc_scene.flags_of(self.data, self.pid, jid), [])  # nothing in layer0.json (the person must not see it)
        log = self.p.conn.execute("SELECT feature, decision, subject, would_do FROM trainee_log").fetchall()
        self.assertEqual([(x["feature"], x["decision"], x["subject"]) for x in log], [("scene_qc", "redraw", f"job:{jid}")])
        self.assertIn("close-up", json.loads(log[0]["would_do"])["fix"])

    def test_the_old_claude_qc_does_not_come_back(self):
        from core import autopilot, cost, known_issues
        self.assertFalse(qc_scene.enabled())
        self.assertTrue(qc_scene.active())
        self.assertFalse(known_issues._per_image_qc(self.p.conn, self.pid))
        self.assertNotEqual(cost._picture_qc_calls(self.p.conn, self.pid, 4), 4)
        self.assertIsNone(autopilot._setcheck_phase(self.p, self.pid, None))   # the old whole-set look stays off


if __name__ == "__main__":
    unittest.main()
