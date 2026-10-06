"""S14.3 B1a (docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 3.2, T2 / T3 / T9): job lifecycle in the runner.

T2: a job that already has its provider task (paid) is moved to RUNNING in the same transaction as its external_id — the project
being paused (Pipeline.start → PipelinePaused) or the job cancelled while `submit` was in flight must never leave a paid job queued
(it would be sent and paid again). T3: runner.cancel_all — rights first, cancel at the provider, then cancel_all_active.
T9: core.composite.composite_video checks the ffmpeg writer / reader and the output file.

Fake providers, an in-memory database, 0 USD — no real API is called."""
import os
import tempfile
import unittest
from unittest import mock

from core import access
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import Pipeline, PipelinePaused
from core.providers import MockImageProvider, MockVideoProvider, ProviderError
from core.runner import ImageRunner, VideoRunner


def _diag_codes(p, project_id):
    return [r["code"] for r in p.conn.execute("SELECT code FROM diag_events WHERE project_id=?", (project_id,))]


class _Base(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.dir = tempfile.mkdtemp()
        self.pid = self.p.create_project("b1a", max_retry=2)

    def scene_ready_for_video(self, idx, prompt="slow push-in"):
        scene = self.p.create_scene(self.pid, idx, f"S{idx}")
        img = self.p.create_job(scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": idx, "motion_prompt": prompt}]})
        approve_motion_prompt(self.p, scene)
        return scene

    def usage_rows(self, job_id):
        return self.p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE job_id=?", (job_id,)).fetchone()[0]


class PausedOrCancelledWhileSubmitting(_Base):
    def test_project_paused_while_submit_is_in_flight_is_not_paid_twice(self):
        """Before: external_id committed, then p.start() raised PipelinePaused → the job stayed queued with its paid task; after
        resuming, the next pass sent it again (paid twice)."""
        test = self

        class PausesDuringSubmit(MockVideoProvider):
            def submit(self, *a, **kw):
                tid = super().submit(*a, **kw)
                test.p.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (test.pid,))   # the person pressed pause meanwhile
                test.p.conn.commit()
                return tid

        job = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        provider = PausesDuringSubmit(polls_to_finish=9)
        r = VideoRunner(self.p, provider, self.dir, max_concurrent=2)
        try:
            r.submit_pending(self.pid)
        except PipelinePaused:
            pass
        self.p.set_paused(self.pid, False)
        r.submit_pending(self.pid)
        self.assertEqual(len(provider._tasks), 1)                       # sent (and paid) once
        row = self.p.job(job)
        self.assertEqual((row["state"], row["external_id"]), ("running", "mock-1"))
        self.assertEqual(self.usage_rows(job), 1)

    def test_paused_while_submitting_an_image_is_not_paid_twice(self):
        test = self
        scene = self.p.create_scene(self.pid, 1, "S1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", ('{"image_prompt": "misty forest"}', scene))
        self.p.conn.commit()
        job = self.p.create_job(scene)

        class PausesDuringSubmit(MockImageProvider):
            def submit(self, *a, **kw):
                tid = super().submit(*a, **kw)
                test.p.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (test.pid,))
                test.p.conn.commit()
                return tid

        provider = PausesDuringSubmit(polls_to_finish=9)
        r = ImageRunner(self.p, provider, self.dir)
        try:
            r.submit_pending(self.pid)
        except PipelinePaused:
            pass
        self.p.set_paused(self.pid, False)
        r.submit_pending(self.pid)
        self.assertEqual(len(provider.prompts), 1)
        self.assertEqual(self.p.job(job)["state"], "running")

    def test_job_cancelled_while_submit_is_in_flight_keeps_the_paid_task_on_record(self):
        """cancel_all_active ran while the provider call was in flight: the task exists and may be billed → its id and the ledger
        row are kept, the task is cancelled at the provider and the diagnostics say so (no exception out of the loop, nothing hidden)."""
        test = self

        class CancelledDuringSubmit(MockVideoProvider):
            def submit(self, *a, **kw):
                tid = super().submit(*a, **kw)
                test.p.cancel_all_active(test.pid)
                return tid

        job = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        provider = CancelledDuringSubmit(polls_to_finish=9)
        r = VideoRunner(self.p, provider, self.dir, max_concurrent=2)
        self.assertEqual(r.submit_pending(self.pid), 0)
        row = self.p.job(job)
        self.assertEqual((row["state"], row["external_id"]), ("cancelled", "mock-1"))
        self.assertEqual(provider.cancelled, ["mock-1"])
        self.assertEqual(self.usage_rows(job), 1)
        self.assertIn("cancelled_in_flight", _diag_codes(self.p, self.pid))
        r.submit_pending(self.pid)
        self.assertEqual(len(provider._tasks), 1)

    def test_a_failed_send_still_ends_failed_without_queued_to_failed(self):
        class Refuses(MockVideoProvider):
            def submit(self, *a, **kw):
                raise ProviderError("bad input", code="bad_request")

        job = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        VideoRunner(self.p, Refuses(), self.dir).submit_pending(self.pid)
        self.assertEqual(self.p.job(job)["state"], "failed")
        states = [r["to_state"] for r in self.p.conn.execute("SELECT to_state FROM job_events WHERE job_id=? ORDER BY id", (job,))]
        self.assertEqual(states, ["queued", "running", "failed"])


class AlreadySentJobs(_Base):
    def test_a_queued_job_with_a_task_is_moved_to_running_not_sent_again(self):
        job = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='paid-7' WHERE id=?", (job,))
        self.p.conn.commit()
        provider = MockVideoProvider(polls_to_finish=9)
        VideoRunner(self.p, provider, self.dir).submit_pending(self.pid)
        self.assertEqual(provider._tasks, {})
        row = self.p.job(job)
        self.assertEqual((row["state"], row["external_id"]), ("running", "paid-7"))

    def test_relink_failed_on_a_paused_project_reopens_the_job_without_a_new_send(self):
        class Relinks(VideoRunner):
            def _find_real(self, job):
                return "real-9"

        job = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='queue-1' WHERE id=?", (job,))
        self.p.start(job)
        self.p.fail(job, "not_found: x")
        self.p.set_paused(self.pid, True)
        provider = MockVideoProvider(polls_to_finish=9)
        r = Relinks(self.p, provider, self.dir)
        new_id = r.relink_failed(job)
        self.assertIsNotNone(new_id)
        row = self.p.job(new_id)
        self.assertEqual((row["state"], row["external_id"]), ("running", "real-9"))
        self.p.set_paused(self.pid, False)
        r.submit_pending(self.pid)
        self.assertEqual(provider._tasks, {})

    def test_group_follower_on_a_paused_project_gets_the_leaders_clip(self):
        """Kling multi-shot: the leader's clip is paid; its followers take their part (core.runner._finish_group). Before: the
        follower got the leader's external_id, then p.start() raised PipelinePaused → it stayed queued with a task id."""
        s1, s2 = self.scene_ready_for_video(1), self.scene_ready_for_video(2)
        leader = self.p.create_job(s1, "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='mock-1', model='kling' WHERE id=?", (leader,))
        self.p.start(leader)
        follower = self.p.create_job(s2, "video_gen")
        self.p.set_paused(self.pid, True)
        r = VideoRunner(self.p, MockVideoProvider(), self.dir)
        group = [{"id": s1, "idx": 1, "data": {}}, {"id": s2, "idx": 2, "data": {}}]
        path = os.path.join(self.dir, "01.mp4")
        with mock.patch("core.shots.split_group_clip"), mock.patch("core.shots.trim_clip"), mock.patch.object(r, "_clean_edges"):
            r._finish_group(self.p.job(leader), path, group)
        row = self.p.job(follower)
        self.assertEqual((row["state"], row["external_id"], row["group_leader"]), ("succeeded", "mock-1", leader))


class _Deepixish(MockImageProvider):
    name = "deepix"                                          # Deepix has no cancel endpoint (core/adapters/deepix.py)

    def cancel(self, task_id):
        raise AssertionError("Deepix has nothing to call")


class _Flaky(MockVideoProvider):
    def cancel(self, task_id):
        if task_id == "bad-1":
            raise ProviderError("network down", code="network", transient=True)
        super().cancel(task_id)


class CancelAll(_Base):
    def running_video(self, idx, ext, scene=None):
        jid = self.p.create_job(scene or self.scene_ready_for_video(idx), "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (ext, jid))
        self.p.start(jid)
        return jid

    def running_image(self, ext):
        scene = self.p.create_scene(self.pid, 50, "img")
        jid = self.p.create_job(scene)
        self.p.conn.execute("UPDATE jobs SET external_id=? WHERE id=?", (ext, jid))
        self.p.start(jid)
        return jid

    def test_cancels_at_the_provider_once_per_task_then_locally(self):
        from core import runner
        a = self.running_video(1, "grp-1")
        b = self.running_video(2, "grp-1")                    # a multi-shot follower shares the leader's task
        c = self.running_video(3, "solo-2")
        queued = self.p.create_job(self.scene_ready_for_video(4), "video_gen")
        img = self.running_image("img-1")
        video = VideoRunner(self.p, MockVideoProvider(), self.dir)
        image = ImageRunner(self.p, _Deepixish(), self.dir)
        rep = runner.cancel_all(self.p, self.pid, video=video, image=image)
        self.assertEqual(sorted(video.provider.cancelled), ["grp-1", "solo-2"])
        self.assertEqual({self.p.job(j)["state"] for j in (a, b, c, queued, img)}, {"cancelled"})
        self.assertEqual(rep["cancelled"], 5)
        note = runner.cancel_note(rep)
        self.assertIn("ảnh đã gửi vẫn tính tiền", note)
        self.assertNotIn("hoàn", note)                       # ClipAI's refund policy is not verified: promise nothing

    def test_one_provider_error_does_not_stop_the_others_and_is_said(self):
        from core import runner
        self.running_video(1, "bad-1")
        ok = self.running_video(2, "good-2")
        video = VideoRunner(self.p, _Flaky(), self.dir)
        rep = runner.cancel_all(self.p, self.pid, video=video, image=None)
        self.assertEqual(video.provider.cancelled, ["good-2"])
        self.assertEqual(self.p.job(ok)["state"], "cancelled")
        self.assertEqual([f[0] for f in rep["failed"]], ["bad-1"])
        self.assertIn("bad-1", runner.cancel_note(rep))

    def test_without_a_configured_service_the_jobs_are_still_cancelled_and_the_note_says_so(self):
        from core import runner
        j = self.running_video(1, "v-1")
        rep = runner.cancel_all(self.p, self.pid, video=None, image=None)
        self.assertEqual(self.p.job(j)["state"], "cancelled")
        self.assertEqual(rep["no_provider"], 1)
        self.assertIn("chưa hủy", runner.cancel_note(rep))

    def test_a_viewer_is_refused_before_anything_is_cancelled_at_the_provider(self):
        from core import auth, runner
        from tests.test_access import WHO, as_user, make_world
        conn, pid, sid, jid = make_world()
        system = Pipeline(conn)
        v = system.create_job(sid, "video_gen")
        conn.execute("UPDATE jobs SET external_id='paid-1' WHERE id=?", (v,))
        system.start(v)
        viewer = as_user(conn, "watch_view")
        provider = MockVideoProvider()
        with self.assertRaises(access.AccessDenied):
            runner.cancel_all(viewer, pid, video=VideoRunner(viewer, provider, self.dir), image=None)
        self.assertEqual(provider.cancelled, [])
        self.assertEqual(system.job(v)["state"], "running")

    def test_holds_the_project_turn_so_no_send_runs_meanwhile(self):
        from core import runner
        held = []
        real = runner._turn

        def spy(project_id, job_type):
            lock = real(project_id, job_type)
            held.append(job_type)
            return lock

        self.running_video(1, "v-1")
        with mock.patch.object(runner, "_turn", side_effect=spy):
            runner.cancel_all(self.p, self.pid, video=VideoRunner(self.p, MockVideoProvider(), self.dir), image=None)
        self.assertEqual(sorted(held), ["image_gen", "video_gen"])


class CancelButtons(unittest.TestCase):
    """header.py ■ Hủy (btn_cancel) and 🗑 Xóa dự án (proj_del_<pid>) go through runner.cancel_all: the running task is cancelled at
    the provider (the service is the one the dashboard builds — core.adapters.factory, patched with a recording fake)."""

    def setUp(self):
        from tests.test_step1_flow import split_only
        self.tmp, self.db, self.data, self.p, self.pid = split_only()
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (self.pid,)).fetchone()["id"]
        self.job = self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='live-1' WHERE id=?", (self.job,))
        self.p.start(self.job)
        self.provider = MockVideoProvider()
        self.env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data})
        self.env.start()
        self.addCleanup(self.env.stop)

    def app(self):
        from streamlit.testing.v1 import AppTest
        from tests.test_step1_flow import APP
        return AppTest.from_file(APP, default_timeout=60).run()

    def test_the_cancel_button_cancels_the_running_task_at_the_provider(self):
        with mock.patch("core.adapters.factory.video_provider", return_value=self.provider):
            at = self.app()
            next(b for b in at.button if b.key == "btn_cancel").click().run()
            next(b for b in at.button if b.key == "btn_cancel_yes").click().run()
            self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.provider.cancelled, ["live-1"])
        self.assertEqual(self.p.job(self.job)["state"], "cancelled")

    def test_deleting_the_project_cancels_the_running_task_at_the_provider(self):
        with mock.patch("core.adapters.factory.video_provider", return_value=self.provider):
            at = self.app()
            next(b for b in at.button if b.key == f"proj_del_{self.pid}").click().run()
            next(b for b in at.button if b.key == f"proj_del_{self.pid}_yes").click().run()
            self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.provider.cancelled, ["live-1"])
        self.assertIsNone(self.p.project(self.pid))


class _FakeProc:
    """A Popen stand-in: `out` = bytes on stdout (the reader), `code` = exit code, `writes` = a file the writer leaves behind."""

    def __init__(self, out=b"", code=0, writes=None):
        import io
        self.stdout = io.BytesIO(out)
        self.stdin = io.BytesIO()
        self.code, self.writes, self.returncode = code, writes, None

    def wait(self, timeout=None):
        if self.writes:
            with open(self.writes, "wb") as f:
                f.write(b"half a clip")
        self.returncode = self.code
        return self.code


class CompositeVideoChecks(unittest.TestCase):
    """T9: composite_video ignored the ffmpeg writer's exit code — a writer that died left a half-written file that the runner put in
    place of the clip."""

    def setUp(self):
        from PIL import Image
        self.dir = tempfile.mkdtemp()
        self.plate = os.path.join(self.dir, "plate.png")
        Image.new("RGB", (40, 20), (10, 20, 30)).save(self.plate)
        self.green = os.path.join(self.dir, "green.mp4")
        with open(self.green, "wb") as f:
            f.write(b"ORIGINAL")
        self.out = os.path.join(self.dir, "out.mp4")

    def run_with(self, writer_code, reader_code=0, writes=True, frames=1):
        from core import composite
        procs = [_FakeProc(out=b"\x00" * (40 * 20 * 3) * frames, code=reader_code),
                 _FakeProc(code=writer_code, writes=self.out if writes else None)]

        def fake_composite(frame, plate, out_path, env=None, place=None, seed=1, **kw):
            from PIL import Image
            Image.new("RGB", (40, 20)).save(out_path)
            return {"path": out_path, "placement": {"x": 0}}

        probe = mock.Mock(stderr="Stream #0:0: Video: h264, yuv420p, 40x20, 24 fps")
        with mock.patch.object(composite.subprocess, "run", return_value=probe), \
                mock.patch.object(composite.subprocess, "Popen", side_effect=procs), \
                mock.patch.object(composite, "composite", side_effect=fake_composite), \
                mock.patch.object(composite.ffmpeg_studio, "probe_duration", return_value=frames / 24):
            return composite.composite_video(self.green, {"plate": self.plate}, self.out, "ffmpeg")

    def test_a_writer_that_exits_with_an_error_raises(self):
        from core.composite import CompositeError
        with self.assertRaises(CompositeError) as ctx:
            self.run_with(writer_code=1)
        self.assertIn("1", str(ctx.exception))

    def test_a_reader_that_exits_with_an_error_raises(self):
        from core.composite import CompositeError
        with self.assertRaises(CompositeError):
            self.run_with(writer_code=0, reader_code=1)

    def test_a_missing_output_file_raises(self):
        from core.composite import CompositeError
        with self.assertRaises(CompositeError):
            self.run_with(writer_code=0, writes=False)

    def test_a_good_run_still_returns_the_clip(self):
        self.assertEqual(self.run_with(writer_code=0)["frames"], 1)


class ReviewFixes(_Base):
    """Rà soát độc lập nhánh B1a (04/10): 2 lỗi phải sửa + 3 điểm nhỏ."""

    def test_a_paid_job_with_stale_inputs_is_fetched_not_failed(self):
        job = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='paid-3' WHERE id=?", (job,))
        self.p.conn.commit()
        provider = MockVideoProvider(polls_to_finish=9)
        r = VideoRunner(self.p, provider, self.dir)
        with mock.patch.object(r, "_blocked", return_value="motion prompt đã đổi"):
            r.submit_pending(self.pid)
        row = self.p.job(job)
        self.assertEqual((row["state"], row["external_id"]), ("running", "paid-3"))
        self.assertEqual(provider._tasks, {})
        self.assertIn("stale_paid", _diag_codes(self.p, self.pid))

    def test_cancelled_in_flight_at_deepix_does_not_claim_a_cancel(self):
        test = self
        scene = self.p.create_scene(self.pid, 1, "S1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", ('{"image_prompt": "misty forest"}', scene))
        self.p.conn.commit()
        self.p.create_job(scene)

        class DeepixCancelledDuringSubmit(_Deepixish):
            def submit(self, *a, **kw):
                tid = super().submit(*a, **kw)
                test.p.cancel_all_active(test.pid)
                return tid

        ImageRunner(self.p, DeepixCancelledDuringSubmit(), self.dir).submit_pending(self.pid)
        msg = self.p.conn.execute("SELECT message FROM diag_events WHERE code='cancelled_in_flight'").fetchone()["message"]
        self.assertIn("ảnh đã gửi vẫn tính tiền", msg)
        self.assertNotIn("đã yêu cầu hủy", msg)

    def test_cancel_all_gives_up_when_the_turn_stays_busy_and_cancels_nothing(self):
        import threading
        from core import runner
        jid = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='v-1' WHERE id=?", (jid,))
        self.p.start(jid)
        taken, release = threading.Event(), threading.Event()

        def hold():
            with runner._turn(self.pid, "video_gen"):
                taken.set()
                release.wait(10)

        t = threading.Thread(target=hold, daemon=True)
        t.start()
        taken.wait(5)
        provider = MockVideoProvider()
        try:
            rep = runner.cancel_all(self.p, self.pid, video=VideoRunner(self.p, provider, self.dir), image=None, wait=0.2)
        finally:
            release.set()
            t.join(5)
        self.assertTrue(rep["busy"])
        self.assertIn("đang bận", runner.cancel_note(rep))
        self.assertEqual(provider.cancelled, [])
        self.assertEqual(self.p.job(jid)["state"], "running")
        self.assertTrue(runner._turn(self.pid, "image_gen").acquire(blocking=False))     # nothing left held
        runner._turn(self.pid, "image_gen").release()

    def test_cancel_all_also_cancels_queued_jobs_that_already_have_a_task(self):
        from core import runner
        q = self.p.create_job(self.scene_ready_for_video(1), "video_gen")
        self.p.conn.execute("UPDATE jobs SET external_id='old-5' WHERE id=?", (q,))
        self.p.conn.commit()
        provider = MockVideoProvider()
        runner.cancel_all(self.p, self.pid, video=VideoRunner(self.p, provider, self.dir), image=None)
        self.assertEqual(provider.cancelled, ["old-5"])
        self.assertEqual(self.p.job(q)["state"], "cancelled")


class DeleteWhileBusy(CancelButtons):
    """Rà soát B1a điểm 4: the turn stays busy → nothing is cancelled, so the project must NOT be deleted (its tasks would bill on)."""
    test_the_cancel_button_cancels_the_running_task_at_the_provider = None
    test_deleting_the_project_cancels_the_running_task_at_the_provider = None

    def test_a_busy_project_is_not_deleted(self):
        import threading
        from core import runner
        taken, release = threading.Event(), threading.Event()

        def hold():
            with runner._turn(self.pid, "video_gen"):
                taken.set()
                release.wait(60)

        t = threading.Thread(target=hold, daemon=True)
        t.start()
        taken.wait(5)
        try:
            with mock.patch("core.adapters.factory.video_provider", return_value=self.provider), \
                    mock.patch.object(runner, "CANCEL_WAIT_S", 0.2):
                at = self.app()
                next(b for b in at.button if b.key == f"proj_del_{self.pid}").click().run()
                next(b for b in at.button if b.key == f"proj_del_{self.pid}_yes").click().run()
                self.assertFalse(at.exception, at.exception)
        finally:
            release.set()
            t.join(5)
        self.assertIsNotNone(self.p.project(self.pid))
        self.assertEqual(self.provider.cancelled, [])
        self.assertEqual(self.p.job(self.job)["state"], "running")


class CompositeRealFfmpeg(unittest.TestCase):
    """Rà soát B1a lỗi 1: when the loop stopped early (the writer died → BrokenPipe), the finally block waited on the ffmpeg reader
    whose stdout pipe was full and unread → hung for ever (the poll thread kept the project's _turn lock, ■ Hủy hung behind it)."""

    def test_a_dead_writer_raises_fast_with_real_ffmpeg_and_the_clip_is_kept(self):
        import subprocess
        import threading
        import time
        from PIL import Image
        from core import composite, ffmpeg_studio
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except Exception as e:  # noqa: BLE001
            self.skipTest(f"không có ffmpeg trên máy này ({e}) — ca treo thật chỉ kiểm được khi có ffmpeg")
        d = tempfile.mkdtemp()
        green = os.path.join(d, "g.mp4")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x00ff00:s=320x240:d=5:r=24",
                        "-pix_fmt", "yuv420p", green], check=True, timeout=60)
        before = os.path.getsize(green)
        plate = os.path.join(d, "p.png")
        Image.new("RGB", (320, 240), (90, 90, 120)).save(plate)
        out = os.path.join(d, "no_such_dir", "o.mp4")                     # the writer cannot open its output → dies

        def cheap(frame, plate_, out_path, env=None, place=None, seed=1, **kw):     # the per-frame grade is not what is tested
            Image.new("RGB", (320, 240)).save(out_path)
            return {"path": out_path, "placement": {"x": 0}}

        result = {}

        def go():
            try:
                composite.composite_video(green, {"plate": plate}, out, ff)
                result["ok"] = True
            except Exception as e:  # noqa: BLE001
                result["error"] = e

        start = time.time()
        with mock.patch.object(composite, "composite", side_effect=cheap):
            t = threading.Thread(target=go, daemon=True)
            t.start()
            t.join(60)
        self.assertFalse(t.is_alive(), "composite_video treo quá 60 s khi writer chết")
        self.assertIsInstance(result.get("error"), composite.CompositeError, result)
        self.assertEqual(os.path.getsize(green), before)
        print(f"\n[ffmpeg thật] writer chết → CompositeError sau {time.time() - start:.1f} s")


if __name__ == "__main__":
    unittest.main()
