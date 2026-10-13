"""K1/K2 — an end frame for a shot whose end_state changes something, sent as first + last frame (feature `end_frames`)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import end_frames, llm_runner
from core.adapters.clipai import ClipAIVideoProvider
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import VideoRunner
from tests.test_adapters import TOKEN, FakeTransport, ctx_of, ok
from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project

from tests._flags import flags_on_deco  # noqa: E402


def _shot_with_end_state(p, pid):
    """The first shot that does not continue into the next one, given a clear end state."""
    for s in p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        data = json.loads(s["data"] or "{}")
        if data.get("shot_no") and not data.get("continuous_with_next"):
            data["end_state"] = "Kenta lies on the ground, sword out of reach"
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), s["id"]))
            p.conn.commit()
            return s["id"]
    raise AssertionError("no standalone shot in the sample")


class NeededTests(unittest.TestCase):
    def test_only_standalone_shots_that_change_state(self):
        self.assertTrue(end_frames.needed({"end_state": "he falls"}, "per_shot"))
        self.assertFalse(end_frames.needed({"end_state": ""}, "per_shot"))
        self.assertFalse(end_frames.needed({"end_state": "he falls", "continuous_with_next": True}, "per_shot"))   # ends on next shot
        self.assertFalse(end_frames.needed({"end_state": "he falls"}, "multishot"))      # a Kling multi-shot request takes none
        self.assertFalse(end_frames.needed({"end_state": "he falls"}, None))


class EndFrameFlowTests(unittest.TestCase):
    def setUp(self):
        self.p, self.pid = kenta_project()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        self.sid = _shot_with_end_state(self.p, self.pid)
        self.data = tempfile.mkdtemp()
        _approve_all_images(self.p, self.pid, self.data)

    def test_drawn_from_the_start_picture_and_outdated_by_a_new_one(self):
        queued = end_frames.queue(self.p, self.pid)
        self.assertIn(self.sid, queued)
        self.assertEqual(end_frames.queue(self.p, self.pid), [])                          # not queued twice
        provider = MockImageProvider()
        end_frames.tick(self.p, self.pid, provider, self.data)                            # sent
        sent = [t for t, pr in provider.prompts.items() if "lies on the ground" in pr]
        self.assertEqual(len(sent), 1)
        self.assertTrue(any(os.path.basename(r).startswith("job_") for r in provider.references[sent[0]]))   # start picture goes along
        end_frames.tick(self.p, self.pid, provider, self.data)                            # downloaded
        path = end_frames.usable_path(self.p.conn, self.sid)
        self.assertTrue(path and os.path.exists(path))
        spent = self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE stage='end_frame'").fetchone()[0]
        self.assertGreaterEqual(spent, 1)                                                 # counted like every picture
        start = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                                    (self.sid,)).fetchone()["id"]
        self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at)"
                            " SELECT project_id, scene_id, type, 'approved', created_at, updated_at FROM jobs WHERE id=?", (start,))
        self.p.conn.commit()
        self.assertIsNone(end_frames.usable_path(self.p.conn, self.sid))                  # a new start picture: redraw
        self.assertIn(self.sid, end_frames.queue(self.p, self.pid))

    @flags_on_deco("end_frames")                   # B1 học việc 08/10: FEATURE_END_FRAMES=1 = học việc; really ON only from 🧪
    def test_the_clip_waits_for_its_end_frame_then_goes_out_first_plus_last(self):
        from core import batch, model_router
        _approve_all_motion(self.p, self.pid, self.data)
        model_router.set_override(self.p.conn, self.sid, "kling")
        end_frames.queue(self.p, self.pid)
        video = MockVideoProvider()
        vr = VideoRunner(self.p, video, self.data)
        vr.max_concurrent = 99
        batch.queue_videos(self.p, self.pid, self.data)
        vr.submit_pending(self.pid)
        mine = self.p.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid,)).fetchone()
        self.assertEqual(mine["state"], "queued")                                          # waiting for its end frame
        img = MockImageProvider()
        end_frames.tick(self.p, self.pid, img, self.data)
        end_frames.tick(self.p, self.pid, img, self.data)
        for _ in range(20):                                                                # free throttle slots, then it goes
            vr.poll_once(self.pid)
            vr.submit_pending(self.pid)
            if self.p.conn.execute("SELECT external_id FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid,)).fetchone()[0]:
                break
        job =self.p.conn.execute("SELECT external_id FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid,)).fetchone()
        self.assertEqual(video._tasks[job["external_id"]]["last_frame"], end_frames.usable_path(self.p.conn, self.sid))

    def test_off_by_default_nothing_waits(self):
        from core import batch
        _approve_all_motion(self.p, self.pid, self.data)
        end_frames.queue(self.p, self.pid)
        vr = VideoRunner(self.p, MockVideoProvider(), self.data)
        vr.max_concurrent = 99
        batch.queue_videos(self.p, self.pid, self.data)
        vr.submit_pending(self.pid)
        mine = self.p.conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid,)).fetchone()
        self.assertEqual(mine["state"], "running")


class ManualSendTests(unittest.TestCase):
    """C5 (rà chuỗi 13/10): the Dashboard way (▶ Gen video, no autopilot) never drew the end frame and the clip went without it, said
    nowhere; a clip waiting for its end frame waited without a reason."""

    def setUp(self):
        from core import batch, model_router
        from tests._flags import flags_on
        flags_on(self, "end_frames")
        self.p, self.pid = kenta_project()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        self.sid = _shot_with_end_state(self.p, self.pid)
        self.data = tempfile.mkdtemp()
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        model_router.set_override(self.p.conn, self.sid, "kling")
        batch.queue_videos(self.p, self.pid, self.data)
        self.job = self.p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen'", (self.sid,)).fetchone()
        self.vr = VideoRunner(self.p, MockVideoProvider(), self.data)

    def _said(self, code):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code=?", (code,))]

    def test_manual_video_send_without_end_frame_is_said(self):
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        said = self._said("end_frame_missing")
        self.assertEqual(len(said), 1)                                  # once per job
        self.assertIn("KHÔNG kèm khung cuối", said[0])
        self.assertIn("chưa vẽ", said[0])
        self.assertEqual(end_frames.missing_reason(self.p.conn, self.sid), "chưa vẽ khung cuối")

    def test_manual_video_send_waits_for_needed_end_frame(self):
        """A queued end frame (🔁 vẽ khung cuối on the card) holds the clip WITH a reason the card / inbox show."""
        from core import runner
        end_frames.redo(self.p, self.sid)
        self.assertTrue(self.vr._wait(self.job))
        self.assertIn("khung cuối", runner.wait_reason(self.job["id"]) or "")
        self.assertEqual(end_frames.missing_reason(self.p.conn, self.sid), "đang vẽ khung cuối")

    def test_rejected_end_frame_is_said_not_silent(self):
        img = MockImageProvider()
        end_frames.queue(self.p, self.pid)
        end_frames.tick(self.p, self.pid, img, self.data)
        end_frames.tick(self.p, self.pid, img, self.data)
        end_frames.reject(self.p, end_frames.current(self.p.conn, self.sid)["id"])
        self.assertIn("loại", end_frames.missing_reason(self.p.conn, self.sid))
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        self.assertTrue(any("loại" in m for m in self._said("end_frame_missing")))

    def test_ready_end_frame_says_nothing(self):
        img = MockImageProvider()
        end_frames.queue(self.p, self.pid)
        end_frames.tick(self.p, self.pid, img, self.data)
        end_frames.tick(self.p, self.pid, img, self.data)
        self.assertIsNone(end_frames.missing_reason(self.p.conn, self.sid))
        self.assertTrue(self.vr._end_frame(self.job, "kling"))
        self.assertEqual(self._said("end_frame_missing"), [])


class SkillObjectEndFrameTests(unittest.TestCase):
    """Rà S2 'việc cho S3' (1): the end frame of a shot with the glue wall uses the SAME words as the video prompt — it stands at full
    height (skill_objects.standing_text / guard_prompt), never 'pops up' (người dùng 13/10 21:31)."""

    def test_end_frame_prompt_says_the_wall_is_standing(self):
        from core import skill_objects
        from tests.test_skill_objects import GLUE_DESC
        from tests._flags import flags_on
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = _shot_with_end_state(p, pid)
        c = p.conn
        aid = c.execute("INSERT INTO assets (game, kind, name, aliases, description) VALUES ('FF','weapon','Bom keo','Gloowall',?)",
                        (GLUE_DESC,)).lastrowid
        c.execute("INSERT INTO project_assets (project_id, asset_id) VALUES (?,?)", (pid, aid))
        data = json.loads(c.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        data["end_state"] = "the Gloowall glue wall pops up in front of Kenta, who crouches behind it"
        c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
        c.commit()
        data_dir = tempfile.mkdtemp()
        _approve_all_images(p, pid, data_dir)
        with mock.patch.dict(os.environ, {"FEATURE_SKILL_OBJECT_GUARD": "1"}):
            self.assertTrue(skill_objects.enabled())
            end_frames.queue(p, pid)
            img = MockImageProvider()
            end_frames.tick(p, pid, img, data_dir)
        sent = [pr for pr in img.prompts.values() if "Kenta, who crouches" in pr]
        self.assertEqual(len(sent), 1)
        self.assertIn(skill_objects.STANDING, sent[0])
        self.assertNotIn("pops up", sent[0])
        end_frames.tick(p, pid, img, data_dir)
        self.assertTrue(end_frames.usable_path(c, sid))                 # the guarded words never make it look outdated (C6)


class KlingEndFrameTests(unittest.TestCase):
    def test_kling_omni_gets_first_and_end_frame(self):
        t = FakeTransport()
        t.on("POST", "/api/kling/omni-video-submit", ok({"tasks": [{"task_id": "T", "task_status": "submitted"}]}))
        d = tempfile.mkdtemp()
        first, last = os.path.join(d, "a.png"), os.path.join(d, "b.png")
        for path in (first, last):
            with open(path, "wb") as f:
                f.write(b"\x89PNG-" + path.encode())
        ClipAIVideoProvider(TOKEN, "https://clipai.example", t).submit(first, "he falls", None, 5, last_frame=last)
        ctx = ctx_of(t.calls[0])
        self.assertEqual([i["type"] for i in ctx["image_list"]], ["first_frame", "end_frame"])
        self.assertEqual(t.calls[0]["body"].count(b'name="image_files"'), 2)
        self.assertIn("end exactly on the last image", ctx["prompt"])


if __name__ == "__main__":
    unittest.main()
