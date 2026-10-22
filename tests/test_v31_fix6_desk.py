"""C-FIX6 phần A (rà kỹ C-M48-DESK-CORE, docs/RA_CLOUD_FIX6_2026-10-22.md): cổng S-C ở MỘT chỗ cho mọi đường gửi trả phí (runner
.submit_pending — nút Gen ảnh, autopilot, gen video, gửi lại), cổng chỉ chạy khi EP đã đánh dấu bắt buộc (không có → y hệt trước), kiểm-và-ghi
trong cùng khóa S, S-D chỉ shot ĐỔI máy, khóa S nhả khi lỗi / gỡ nguyên tử, user=None khi đăng nhập BẬT, N11 lấy khóa S. 0 USD: provider
giả, Blender giả (khung tests/test_stage_auto)."""
import json
import os
from unittest import mock

from core import autopilot, batch, runner as R, stage_desk as D, write_guard
from core.providers import MockImageProvider, MockVideoProvider
from tests.test_v31_m48_desk_core import EP, HUMAN, DeskBase


class _Counting(MockImageProvider):
    def __init__(self):
        super().__init__()
        self.sent = 0

    def submit(self, *a, **k):
        self.sent += 1
        return super().submit(*a, **k)


class _CountingVideo(MockVideoProvider):
    def __init__(self):
        super().__init__()
        self.sent = 0

    def submit(self, *a, **k):
        self.sent += 1
        return super().submit(*a, **k)


class FixBase(DeskBase):
    def setUp(self):
        super().setUp()
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE project_id=?", (self.pid,))
        self.p.conn.commit()
        R.WAIT_REASONS.clear()
        off = mock.patch("core.place_refs.enabled", return_value=False)    # chờ render nền 3D (_wait, có trước) không phải việc ở đây
        off.start()
        self.addCleanup(off.stop)

    def sid(self, idx):
        return self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()[0]

    def mark(self, idx=1):
        self.assertTrue(D.require_plate(self.p.conn, self.pid, self.data, self.sid(idx), True, HUMAN, EP)["ok"])

    def state(self, jid):
        return self.p.conn.execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()[0]

    def assert_held(self, jid, prov):
        self.assertEqual(self.state(jid), "queued")
        self.assertEqual(prov.sent, 0)
        self.assertIn("plate 3D bắt buộc", R.wait_reason(jid) or "")
        n = self.p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE job_id=? AND code='stage_desk_hold'", (jid,)).fetchone()[0]
        self.assertEqual(n, 1)


# ---- mục 1: một cổng cho mọi đường gửi trả phí ------------------------------------------------------------------------------
class PaidPathsTests(FixBase):
    def test_gen_image_button_path_holds_even_when_the_person_ticks_go_anyway(self):
        self.mark(1)
        out = batch.queue_images(self.p, self.pid, confirmed=True, data_dir=self.data)    # "vẫn gen" không thay ngoại lệ EP
        self.assertGreaterEqual(out["created"], 1)
        jid = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen'", (self.sid(1),)).fetchone()[0]
        prov = _Counting()
        R.ImageRunner(self.p, prov, self.data).submit_pending(self.pid, only=[jid])
        self.assert_held(jid, prov)

    def test_autopilot_image_phase_holds_and_waits_for_the_person(self):
        self.mark(1)
        self.p.conn.execute("UPDATE projects SET autopilot_state=? WHERE id=?", (autopilot.RUNNING, self.pid))
        self.p.conn.commit()
        prov = _Counting()
        ctx = autopilot.Context(self.data, R.ImageRunner(self.p, prov, self.data), R.VideoRunner(self.p, MockVideoProvider(), self.data),
                                None)
        with self.assertRaises(autopilot._Wait) as w:
            autopilot._images_phase(self.p, self.pid, ctx)
        self.assertEqual(w.exception.gate, "stage_desk")
        self.assertIn("plate 3D", str(w.exception))
        jid = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen'", (self.sid(1),)).fetchone()[0]
        self.assertEqual(self.state(jid), "queued")

    def test_paid_video_path_holds(self):
        self.mark(1)
        jid = self.p.create_job(self.sid(1), "video_gen")
        prov = _CountingVideo()
        with mock.patch.object(R.VideoRunner, "_wait", return_value=False):
            R.VideoRunner(self.p, prov, self.data).submit_pending(self.pid)
        self.assert_held(jid, prov)

    def test_resend_path_holds(self):
        first = self.p.create_job(self.sid(1), "image_gen")
        self.p.transition(first, R.JobState.RUNNING)
        self.p.fail(first, "provider error")
        self.mark(1)
        jid = self.p.resend(first, "gửi lại")
        prov = _Counting()
        R.ImageRunner(self.p, prov, self.data).submit_pending(self.pid)
        self.assert_held(jid, prov)

    def test_exception_lets_the_job_go(self):
        self.mark(1)
        D.allow_exception(self.p.conn, self.pid, self.data, self.sid(1), "gấp, chấp nhận lệch", HUMAN, EP)
        jid = self.p.create_job(self.sid(1), "image_gen")
        prov = _Counting()
        R.ImageRunner(self.p, prov, self.data).submit_pending(self.pid)
        self.assertNotEqual(self.state(jid), "queued")
        self.assertEqual(prov.sent, 1)


# ---- mục 3: không đánh dấu bắt buộc → y hệt trước ---------------------------------------------------------------------------
class NoMarkSameAsBeforeTests(FixBase):
    def test_half_done_crew_without_marks_adds_no_yellow_and_reads_nothing(self):
        self.answer(blocking_answer())                                   # crew/state.json dở
        os.makedirs(os.path.join(self.data, str(self.pid), "stage"), exist_ok=True)
        with mock.patch.object(D, "scene_status", side_effect=AssertionError("không được đọc sân khấu")):
            self.assertEqual(D.paid_gate(self.p.conn, self.pid, self.data, [self.sid(1), self.sid(2)]), [])
            self.assertIsNone(D.paid_hold(self.p.conn, self.pid, self.data, [self.sid(1)]))
            gates = batch.image_gates(self.p, self.pid, self.data, scene_ids=[self.sid(1), self.sid(2)])
        self.assertFalse([w for w in gates["warn"] if "sân khấu 3D" in w], gates)

    def test_runner_sends_exactly_like_before_without_marks(self):
        self.answer(blocking_answer())
        jobs, sent = [], []
        for gate_off in (False, True):
            jid = self.p.create_job(self.sid(1 if not gate_off else 2), "image_gen")
            prov = _Counting()
            if gate_off:                                                 # "trước": không có cổng S-C trong runner
                with mock.patch.object(D, "paid_hold", return_value=None):
                    R.ImageRunner(self.p, prov, self.data).submit_pending(self.pid, only=[jid])
            else:
                R.ImageRunner(self.p, prov, self.data).submit_pending(self.pid, only=[jid])
            jobs.append(self.state(jid))
            sent.append(prov.sent)
        self.assertEqual(jobs[0], jobs[1])
        self.assertEqual(sent, [1, 1])


def blocking_answer():
    from tests.test_stage_crew import blocking
    return blocking()


# ---- mục 4: kiểm dấu máy trong cùng khóa ghi --------------------------------------------------------------------------------
class MarksInsideLockTests(FixBase):
    def test_camera_written_while_waiting_for_the_lock_is_refused(self):
        self.to_duyet()
        marks = self.st()["marks"]
        real = D._Hold.acquire

        def racing(hold):                                                # autopilot ghi máy shot 2 ngay trước khi nhả khóa cho N6
            d = self.shot(self.pid, 2)
            d["stage_camera"] = {"auto": True, "xen_giua": 1}
            self.p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=2", (json.dumps(d), self.pid))
            self.p.conn.commit()
            return real(hold)
        with mock.patch.object(D._Hold, "acquire", racing):
            r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP, expected_marks=marks)
        self.assertFalse(r["ok"], r)
        self.assertEqual(r.get("stale"), [2])
        self.assertEqual(self.crew_state()["phase"], "duyet")


# ---- mục 5: S-D chỉ shot đổi máy + ghi lại trước khi xóa dấu ----------------------------------------------------------------
class ResetOnlyChangedTests(FixBase):
    def test_only_shots_whose_camera_changed_go_stale_and_the_list_is_kept(self):
        self.to_duyet()
        self.assertTrue(D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)["ok"])
        d = self.shot(self.pid, 2)                                       # máy shot 2 khác máy lượt mới sẽ ghi
        d["stage_camera"] = dict(d["stage_camera"], lens=99)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=2", (json.dumps(d), self.pid))
        self.p.conn.commit()
        prev = D.reset(self.p.conn, self.pid, self.data, "1", HUMAN)["preview"]
        self.assertEqual(prev["plates_stale_after"], [])                # chưa biết máy mới: không đánh dấu shot giữ nguyên máy
        self.assertEqual(prev["cams_kept"], [1, 2, 3])
        self.assertTrue(D.reset(self.p.conn, self.pid, self.data, "1", HUMAN, confirm=True)["ok"])
        self.to_duyet()
        r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["reset_stale"]["plates_stale"], [2])
        st = self.st()
        self.assertIsNone(st["reset"])                                   # dấu đã xóa …
        self.assertEqual(st["reset_stale"]["plates_stale"], [2])         # … sau khi ghi lại danh sách
        self.assertEqual(st["reset_stale"]["images_stale"], [])


# ---- mục 6 --------------------------------------------------------------------------------------------------------------------
class LockRobustnessTests(FixBase):
    def lock_path(self):
        return os.path.join(D.seg_dir(self.data, self.pid, self.seg), D.LOCK_FILE)

    def test_progress_write_error_releases_the_lock(self):
        with mock.patch.object(D, "_write", side_effect=OSError("đĩa đầy")):
            r = D.check_inputs(self.p.conn, self.pid, self.data, "1", HUMAN)
        self.assertFalse(r["ok"])
        self.assertFalse(os.path.exists(self.lock_path()))

    def test_lock_write_error_leaves_no_lock_and_releases_earlier_ones(self):
        seg2 = dict(self.seg, id=self.seg["id"] + "_b", scene="2")
        with mock.patch.object(D, "seg_dir", lambda data, pid, g: os.path.join(data, str(pid), "stage", "doan_" + str(g["scene"]))):
            first = D._Hold(self.data, self.pid, self.seg, "x", HUMAN, None)
            calls = {"n": 0}
            real = os.write

            def flaky(fd, b):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise OSError("đĩa đầy")
                return real(fd, b)
            with mock.patch.object(D.os, "write", flaky):
                with self.assertRaises(OSError):
                    with D.hold_segments(self.p.conn, self.pid, self.data, [self.seg, seg2], "autopilot", HUMAN):
                        pass
            self.assertFalse(os.path.exists(first.path))
            self.assertFalse(os.path.exists(D._lock_path(self.data, self.pid, seg2)))

    def test_stale_lock_removal_never_removes_a_fresh_lock(self):
        path = self.lock_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"pid": 2 ** 22 + 7, "token": "cu", "action": "N4", "since_ts": 1}, f)
        real = D._stale_why

        def judged_then_replaced(p, h):
            why = real(p, h)
            with open(p, "w", encoding="utf-8") as f:                     # tiến trình khác gỡ khóa cũ + giữ khóa MỚI ngay lúc đó
                json.dump({"pid": os.getppid(), "token": "moi", "action": "N3", "since_ts": __import__("time").time()}, f)
            return why
        with mock.patch.object(D, "_stale_why", judged_then_replaced):
            D.lock_holder(self.data, self.pid, "1", self.p.conn)
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["token"], "moi")

    def test_no_user_with_sign_in_on_is_not_the_executive_producer(self):
        with mock.patch.dict(os.environ, {"DASHBOARD_AUTH": "on"}):
            self.assertFalse(D.is_executive_producer(self.p.conn, self.pid, None))
            self.to_duyet()
            r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, None)
        self.assertFalse(r["ok"])
        with mock.patch.dict(os.environ, {"DASHBOARD_AUTH": "off"}):
            self.assertTrue(D.is_executive_producer(self.p.conn, self.pid, None))

    def test_render_plates_takes_the_stage_lock(self):
        with D.hold_segments(self.p.conn, self.pid, self.data, [self.seg], "autopilot", write_guard.actor("auto", "autopilot.stage")):
            with mock.patch("core.place_refs.ensure_async", return_value=True) as ens:
                r = D.render_plates(self.p.conn, self.pid, self.data, "1", HUMAN)
        self.assertFalse(r["ok"])
        self.assertIn("autopilot", r["errors"][0])
        self.assertFalse(ens.called)


# ---- rà quy ước 7 (C-FIX6): lỗi đọc, shot ngoài sân khấu, nhóm, 📥 ------------------------------------------------------------
class ReviewGateTests(FixBase):
    def test_required_shot_is_held_when_segments_cannot_be_read(self):
        self.mark(1)
        with mock.patch("core.stage_auto.segments", side_effect=OSError("hỏng")):
            g = {x["scene_id"]: x for x in D.paid_gate(self.p.conn, self.pid, self.data, [self.sid(1), self.sid(2)])}
            self.assertEqual((g[self.sid(1)]["level"], g[self.sid(2)]["level"]), ("hold", "warn"))
            self.assertTrue(D.paid_hold(self.p.conn, self.pid, self.data, [self.sid(1)]))

    def test_required_shot_outside_every_stage_is_held(self):
        other = self.p.create_scene(self.pid, 9, "s9")                                  # không có bối cảnh 3D
        self.assertTrue(D.require_plate(self.p.conn, self.pid, self.data, other, True, HUMAN, EP)["ok"])
        self.assertEqual([x["level"] for x in D.paid_gate(self.p.conn, self.pid, self.data, [other])], ["hold"])

    def test_autopilot_waits_when_the_runner_held_a_group_leader(self):
        self.mark(1)
        jid = self.p.create_job(self.sid(1), "video_gen")
        R.WAIT_REASONS[jid] = ("sân khấu 3D — shot 2: plate 3D bắt buộc chưa đạt", __import__("time").time())   # runner giữ vì shot nhóm
        with mock.patch.object(D, "paid_hold", return_value=None):                     # tính riêng shot 1 thì qua
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._desk_wait(self.p, self.pid, "video_gen", self.data)
        self.assertEqual(w.exception.gate, "stage_desk")

    def test_inbox_lists_a_clip_held_by_the_desk_gate(self):
        from core import inbox
        self.mark(1)
        jid = self.p.create_job(self.sid(1), "video_gen")
        with mock.patch.object(R.VideoRunner, "_wait", return_value=False):
            R.VideoRunner(self.p, _CountingVideo(), self.data).submit_pending(self.pid)
        self.assertEqual(self.state(jid), "queued")
        lines = inbox._video_waits(self.p.conn, self.pid, [])
        self.assertTrue(any("plate 3D bắt buộc" in x for x in lines), lines)


class OffRunnerPaidPathsTests(DeskBase):
    """Đường trả phí theo shot KHÔNG qua runner: ảnh khung cuối (end_frames._tick) và phép thử Seedance (quality_samples.send)."""

    def test_quality_sample_is_held_before_any_spend(self):
        from core import quality_samples
        from tests.test_quality_samples import Provider
        prov = Provider()
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()[0]
        with mock.patch.dict(os.environ, {"FEATURE_SEEDANCE_SAMPLE_MODE": "1"}), \
                mock.patch.object(D, "paid_hold", return_value="sân khấu 3D — shot 1: plate 3D bắt buộc chưa đạt"), \
                mock.patch.object(quality_samples, "plan", side_effect=AssertionError("không được dựng đầu vào trả phí")):
            with self.assertRaises(ValueError) as e:
                quality_samples.send(self.p, self.pid, sid, "draft", prov, self.data)
        self.assertIn("plate 3D", str(e.exception))
        self.assertEqual(prov.calls, [])


class EndFrameHoldTests(__import__("unittest").TestCase):
    def test_end_frame_is_held_before_any_spend(self):
        import tempfile
        from core import end_frames, llm_runner
        from tests._flags import pin_off
        from tests.test_end_frames import _shot_with_end_state
        from tests.test_v3 import _approve_all_images, kenta_project
        pin_off(self, "seedance_ref_groups")
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = _shot_with_end_state(p, pid)
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        self.assertIn(sid, end_frames.queue(p, pid))
        prov = MockImageProvider()
        with mock.patch.object(D, "paid_hold", side_effect=lambda c, i, d, s: "sân khấu 3D — plate 3D bắt buộc chưa đạt" if sid in s
                               else None):
            end_frames.tick(p, pid, prov, data)
        self.assertFalse([t for t, pr in prov.prompts.items() if "lies on the ground" in pr])
        row = p.conn.execute("SELECT state, note FROM end_frames WHERE scene_id=? ORDER BY id DESC", (sid,)).fetchone()
        self.assertIn("plate 3D", row["note"] or "")


# ---- vòng sửa sau rà kỹ C-FIX6 (A1–A5) --------------------------------------------------------------------------------------
class _MultiProvider:
    name = "clipai"

    def __init__(self):
        self.sent = []

    def submit(self, *a, **k):
        self.sent.append((a, k))
        return "clipai:video:1"


class DeepReviewTests(FixBase):
    def _plan(self):
        scenes = [{"id": self.sid(1), "idx": 1, "jid": 1}, {"id": self.sid(2), "idx": 2, "jid": 2}]
        return mock.patch("core.experiments._plan", return_value=(scenes, [{"prompt": "a", "duration": 5},
                                                                          {"prompt": "b", "duration": 5}], 10))

    def test_a1_kling_multishot_is_held_when_a_sent_shot_needs_an_approved_plate(self):
        from core import experiments
        self.mark(1)
        prov = _MultiProvider()
        with self._plan(), self.assertRaises(ValueError) as e:
            experiments.kling_multishot(self.p, self.pid, 1, prov, self.data)
        self.assertIn("plate 3D bắt buộc", str(e.exception))
        self.assertEqual(prov.sent, [])

    def test_a1_kling_multishot_without_marks_sends_as_before(self):
        from core import experiments
        prov = _MultiProvider()
        with self._plan():
            experiments.kling_multishot(self.p, self.pid, 1, prov, self.data)
        self.assertEqual(len(prov.sent), 1)

    def test_a2_autopilot_does_not_wait_on_a_stale_reason_after_the_ep_exception(self):
        self.mark(1)
        jid = self.p.create_job(self.sid(1), "video_gen")
        R.WAIT_REASONS[jid] = ("sân khấu 3D — shot 1: plate 3D bắt buộc chưa đạt", __import__("time").time())
        D.allow_exception(self.p.conn, self.pid, self.data, self.sid(1), "gấp", HUMAN, EP)
        run = R.VideoRunner(self.p, _CountingVideo(), self.data)        # lượt gửi break sớm (slot đầy) → lý do cũ chưa bị xóa
        autopilot._desk_wait(self.p, self.pid, "video_gen", self.data, run)        # không _Wait
        self.assertIsNone(R.wait_reason(jid))

    def test_a2_still_waits_while_the_shot_is_held(self):
        self.mark(1)
        jid = self.p.create_job(self.sid(1), "video_gen")
        R.WAIT_REASONS[jid] = ("sân khấu 3D — shot 1: plate 3D bắt buộc chưa đạt", __import__("time").time())
        with self.assertRaises(autopilot._Wait):
            autopilot._desk_wait(self.p, self.pid, "video_gen", self.data, R.VideoRunner(self.p, _CountingVideo(), self.data))

    def test_a3_shot_drawn_while_waiting_for_the_lock_needs_confirm(self):
        self.to_duyet()
        with mock.patch("core.camera_plan.drawn_shots", side_effect=[[], [1]]):
            r = D.approve(self.p.conn, self.pid, self.data, "1", HUMAN, EP)
        self.assertFalse(r["ok"], r)
        self.assertEqual(r.get("needs_confirm"), [1])
        self.assertEqual(self.crew_state()["phase"], "duyet")

    def test_a5_no_marks_reads_no_send_group(self):
        jid = self.p.create_job(self.sid(1), "video_gen")
        run = R.VideoRunner(self.p, _CountingVideo(), self.data)
        with mock.patch.object(R.VideoRunner, "_sends_group", side_effect=AssertionError("không được đọc nhóm gửi")):
            self.assertIsNone(run._desk_hold(self.p.job(jid)))


class EndFrameHoldFirstTests(__import__("unittest").TestCase):
    def test_a4_held_end_frame_builds_no_prompt(self):
        import tempfile
        from core import end_frames, llm_runner
        from tests._flags import pin_off
        from tests.test_end_frames import _shot_with_end_state
        from tests.test_v3 import _approve_all_images, kenta_project
        pin_off(self, "seedance_ref_groups")
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = _shot_with_end_state(p, pid)
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        end_frames.queue(p, pid)
        real = end_frames.prompt_for
        seen = []
        with mock.patch.object(D, "paid_hold", side_effect=lambda c, i, d, s: "sân khấu 3D — plate 3D bắt buộc chưa đạt" if sid in s
                               else None), \
                mock.patch.object(end_frames, "prompt_for", side_effect=lambda pp, i, s, fix=None: seen.append(s) or real(pp, i, s, fix)):
            end_frames.tick(p, pid, MockImageProvider(), data)
        self.assertNotIn(sid, seen)
