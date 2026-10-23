"""K1/K2 — an end frame for a shot whose end_state changes something, sent as first + last frame (feature `end_frames`)."""
from tests._flags import pin_off
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
        pin_off(self, "seedance_ref_groups")                    # C-FLAGTEST8: đường cờ TẮT, không dựa mặc định
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
        pin_off(self, "seedance_ref_groups")                    # C-FLAGTEST8: đường cờ TẮT, không dựa mặc định
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


    def test_dashboard_poll_draws_the_asked_end_frame_then_the_clip_goes(self):
        """C5 (3): the card's 🖼 Vẽ khung cuối queues (end_frames.redo); the Bước 4 poll draws it with the image provider (mock here,
        0 USD) and lets the held clip go."""
        from dashboard import end_frame_ui
        end_frames.redo(self.p, self.sid)
        img = MockImageProvider()
        with mock.patch("core.adapters.factory.image_provider", return_value=img), \
                mock.patch.object(self.vr, "submit_pending") as go:
            self.assertEqual(end_frame_ui.poll(self.p, self.pid, self.data, self.vr), 0)    # sent
            self.assertEqual(end_frame_ui.poll(self.p, self.pid, self.data, self.vr), 1)    # downloaded
        go.assert_called_once_with(self.pid, only=[self.job["id"]])     # R1 (rà S3): only the clip that waited for it
        self.assertTrue(end_frames.usable_path(self.p.conn, self.sid))
        self.assertFalse(self.vr._wait(self.job))

    # ---- vòng sửa sau rà S3 (RA_S3_S4 R1, R7, R8) ----------------------------------------------------------------------------------
    def _poll(self, img, times=2):
        from dashboard import end_frame_ui
        with mock.patch("core.adapters.factory.image_provider", return_value=img), \
                mock.patch.object(self.vr, "submit_pending") as go:
            for _ in range(times):
                end_frame_ui.poll(self.p, self.pid, self.data, self.vr)
        return go

    def test_dashboard_poll_skips_autopilot_queued_rows(self):
        """R1: the autopilot queued an end frame, then the person stopped it — opening Bước 4 must not draw it (paid, nobody clicked);
        the card says why and shows the priced button; a click draws exactly one picture."""
        from core import autopilot
        from dashboard import end_frame_ui
        self.assertIn(self.sid, end_frames.queue(self.p, self.pid))          # the autopilot's own queue
        autopilot.stop(self.p, self.pid)
        img = MockImageProvider()
        go = self._poll(img)
        self.assertEqual(img.prompts, {})
        go.assert_not_called()
        why = end_frames.missing_reason(self.p.conn, self.sid)
        self.assertIn("chạy tự động", why)
        self.assertNotEqual(why, end_frame_ui.DRAWING)
        with mock.patch.object(end_frame_ui, "st") as st:
            st.button.return_value = False
            end_frame_ui.card_block(self.p, self.pid, self.sid, lambda f: f())
        self.assertTrue(st.button.called)                                    # the way out: the priced button
        end_frames.redo(self.p, self.sid)                                    # the person clicks 🖼 Vẽ
        self._poll(img)
        self.assertEqual(len(img.prompts), 1)

    def test_dashboard_poll_draws_nothing_for_a_read_only_viewer(self):
        """R1 (b): a 'Chỉ xem' watcher opening Bước 4 never sends a paid end frame."""
        end_frames.redo(self.p, self.sid)
        img = MockImageProvider()
        with mock.patch("dashboard.common.read_only", return_value=True):
            self._poll(img)
        self.assertEqual(img.prompts, {})

    def test_budget_refused_end_frame_reason_shows_the_cap(self):
        """R7: a queued end frame the spending limit refused says the cap (not 'đang vẽ'), and does not keep the page polling."""
        rid = end_frames.redo(self.p, self.sid)
        self.p.conn.execute("UPDATE end_frames SET note=? WHERE id=?", ("chờ: vượt trần dự án 10 USD", rid))
        self.p.conn.commit()
        why = end_frames.missing_reason(self.p.conn, self.sid)
        self.assertTrue(why.startswith("chưa vẽ được khung cuối"), why)
        self.assertIn("trần", why)
        self.assertEqual(end_frames.drawing(self.p, self.pid), 0)

    def test_end_frame_hold_survives_in_held_reason(self):
        """R8: the hold for an end frame is written in diag (end_frame_wait, in HOLD_CODES) — read back after 5 minutes / elsewhere."""
        from core import runner
        end_frames.redo(self.p, self.sid)
        self.assertTrue(self.vr._wait(self.job))
        runner.WAIT_REASONS.pop(self.job["id"], None)
        self.assertIn("end_frame_wait", runner.HOLD_CODES)
        self.assertIn("khung cuối", runner.held_reason(self.p.conn, self.job["id"]) or "")

    # ---- C3 (người dùng 14/10): gửi clip KHÔNG kèm khung cuối khi chạy tự động đã dừng --------------------------------------------
    def _card_click(self, click: bool, read_only: bool = False):
        from dashboard import end_frame_ui
        with mock.patch.object(end_frame_ui, "st") as st, mock.patch("dashboard.common.read_only", return_value=read_only), \
                mock.patch.object(self.vr, "submit_pending") as go:
            st.button.side_effect = lambda label, key=None, **k: click and key == f"efoff_{self.sid}"
            end_frame_ui.card_block(self.p, self.pid, self.sid, lambda f: (f(), True)[1], self.vr)
        labels = [c.args[0] for c in st.button.call_args_list]
        return labels, go

    def test_stopped_autopilot_clip_can_be_sent_without_its_end_frame(self):
        pin_off(self, "safe_paid_buttons")                # M8.0b cờ tắt: bấm là chạy như cũ (cờ bật: test_m80b_* / test_safe_paid_buttons)
        from core import autopilot
        end_frames.queue(self.p, self.pid)                                   # the autopilot's own row
        autopilot.stop(self.p, self.pid)
        self.assertTrue(self.vr._wait(self.job))                             # held: nobody draws it now
        self.assertTrue(end_frames.held_without_autopilot(self.p.conn, self.sid))
        labels, go = self._card_click(click=False)
        btn = [x for x in labels if x.startswith("▶ Gửi clip KHÔNG kèm khung cuối")]
        self.assertEqual(len(btn), 1)
        self.assertRegex(btn[0], r"\$|USD|giá")                               # the clip's price is on the button
        go.assert_not_called()
        labels, go = self._card_click(click=True)
        go.assert_called_once_with(self.pid, only=[self.job["id"]])          # only this shot's held clip
        note = self.p.conn.execute("SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (self.job["id"],)).fetchone()[0]
        self.assertIn(end_frames.OFF_NOTE, note)
        self.assertIn("chạy tự động", note)                                  # the reason at that time
        self.assertFalse(self.vr._wait(self.job))
        self.assertEqual(end_frames.missing_reason(self.p.conn, self.sid), end_frames.OFF_NOTE)
        self.assertIsNone(self.vr._end_frame(self.job, "kling"))
        self.assertTrue(any("KHÔNG kèm khung cuối" in m for m in self._said("end_frame_off")))
        self.assertEqual(end_frames.current(self.p.conn, self.sid)["state"], "failed")   # a resumed run never pays to draw it
        self.assertEqual(end_frames.queue(self.p, self.pid), [])
        self.assertEqual(end_frames.drawing(self.p, self.pid), 0)

    def test_a_new_end_frame_request_ends_the_choice(self):
        pin_off(self, "safe_paid_buttons")                # M8.0b cờ tắt: bấm là chạy như cũ (cờ bật: test_m80b_* / test_safe_paid_buttons)
        from core import autopilot
        end_frames.queue(self.p, self.pid)
        autopilot.stop(self.p, self.pid)
        self._card_click(click=True)
        self.assertTrue(end_frames.sent_without(self.p.conn, self.sid))
        end_frames.redo(self.p, self.sid)                                    # the person asks 🖼 Vẽ khung cuối after all
        self.assertIsNone(end_frames.sent_without(self.p.conn, self.sid))
        self.assertTrue(self.vr._wait(self.job))                             # waits for the new one again
        self.assertFalse(end_frames.held_without_autopilot(self.p.conn, self.sid))   # being drawn for the person: no button

    def test_no_send_without_button_while_autopilot_runs_or_for_a_viewer(self):
        from core import autopilot
        end_frames.queue(self.p, self.pid)
        self.p.conn.execute("UPDATE projects SET autopilot_state='running' WHERE id=?", (self.pid,))
        self.p.conn.commit()
        labels, _ = self._card_click(click=False)
        self.assertFalse([x for x in labels if x.startswith("▶ Gửi clip")])
        autopilot.stop(self.p, self.pid)
        labels, go = self._card_click(click=True, read_only=True)
        self.assertFalse([x for x in labels if x.startswith("▶ Gửi clip")])
        go.assert_not_called()
        self.assertIsNone(end_frames.sent_without(self.p.conn, self.sid))


class ConcurrentPollTests(unittest.TestCase):
    """R2 (rà S3): two Bước 4 tabs (two threads, own connections) polling at once send the same end frame once."""

    def setUp(self):
        import sqlite3
        from core.db import connect
        from core.pipeline import Pipeline
        from tests._flags import flags_on
        flags_on(self, "end_frames")
        p, self.pid = kenta_project()
        llm_runner.run_director(p, self.pid, llm_runner.MockLlm())
        self.sid = _shot_with_end_state(p, self.pid)
        self.data = tempfile.mkdtemp()
        _approve_all_images(p, self.pid, self.data)
        end_frames.redo(p, self.sid)
        self.db = os.path.join(self.data, "t.db")
        out = sqlite3.connect(self.db)
        p.conn.backup(out)
        out.close()
        self.open = lambda: Pipeline(connect(self.db))

    def test_two_concurrent_polls_send_once(self):
        import threading
        import time as _t
        from dashboard import end_frame_ui
        calls = []

        class Slow(MockImageProvider):
            def submit(self, *a, **k):
                calls.append(1)
                _t.sleep(0.3)
                return super().submit(*a, **k)

        img = Slow()

        def one():
            end_frame_ui.poll(self.open(), self.pid, self.data, None)

        with mock.patch("core.adapters.factory.image_provider", return_value=img):
            ts = [threading.Thread(target=one) for _ in range(2)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        self.assertEqual(len(calls), 1)

    def test_claimed_row_is_not_sent_again_until_the_claim_is_stale(self):
        """R2: another PROCESS's claim ('đang gửi', fresh) holds the row; a claim left by a crash (old) is taken over."""
        p = self.open()
        rid = end_frames.current(p.conn, self.sid)["id"]
        p.conn.execute("UPDATE end_frames SET note='đang gửi', updated_at=datetime('now') WHERE id=?", (rid,))
        p.conn.commit()
        img = MockImageProvider()
        end_frames.tick(p, self.pid, img, self.data)
        self.assertEqual(img.prompts, {})
        p.conn.execute("UPDATE end_frames SET updated_at=datetime('now','-1 hour') WHERE id=?", (rid,))
        p.conn.commit()
        end_frames.tick(p, self.pid, img, self.data)
        self.assertEqual(len(img.prompts), 1)
        self.assertNotEqual(end_frames.current(p.conn, self.sid)["note"], "đang gửi")      # claim cleared once sent


class SkillObjectSkipTests(unittest.TestCase):
    """R3 (rà S3): a shot where the skill object appears gets no drawn end frame (the runner always drops it — the build is the code
    composite): not queued, not drawn, the card says why and shows no paid button."""
    def setUp(self):
        pin_off(self, "seedance_ref_groups")                    # C-FLAGTEST8: đường cờ TẮT, không dựa mặc định
        super().setUp()


    def test_queue_skips_skill_object_rising_shot(self):
        from core import framing_guard
        from dashboard import end_frame_ui
        from tests._flags import flags_on
        flags_on(self, "end_frames", framing_guard.FLAG, "skill_object_guard")
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = _shot_with_end_state(p, pid)
        data_dir = tempfile.mkdtemp()
        _approve_all_images(p, pid, data_dir)
        with mock.patch("core.skill_objects.rises", return_value=True):
            self.assertNotIn(sid, end_frames.queue(p, pid))
            why = end_frames.missing_reason(p.conn, sid)
            self.assertIn("vật kỹ năng", why)
            with mock.patch.object(end_frame_ui, "st") as st:
                end_frame_ui.card_block(p, pid, sid, lambda f: f())
            st.button.assert_not_called()




class SkillObjectEndFrameTests(unittest.TestCase):
    """Rà S2 'việc cho S3' (1): the end frame of a shot with the glue wall uses the SAME words as the video prompt — it stands at full
    height (skill_objects.standing_text / guard_prompt), never 'pops up' (người dùng 13/10 21:31)."""
    def setUp(self):
        pin_off(self, "seedance_ref_groups")                    # C-FLAGTEST8: đường cờ TẮT, không dựa mặc định
        super().setUp()


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
