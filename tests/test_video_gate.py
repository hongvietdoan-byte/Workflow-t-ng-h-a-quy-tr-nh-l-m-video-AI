"""V7 (rà gốc video #27 13/10, cờ video_gate — core/video_gate.py): clip chỉ GỬI khi ảnh khung đầu đã qua kiểm nền 3D (hoặc người bỏ
qua có lý do) và cả nhóm shot liền mạch đã duyệt ảnh; giữ = job vẫn chờ có lý do (không hỏng, không tốn tiền). Cờ tắt y cũ.
+ C9 (rà chuỗi 13/10): bản cao nâng từ nháp NGƯỜI đã duyệt không bị Tổ rà soát giữ vì mục đỏ khâu ảnh cũ.
CSDL tạm, provider giả, không gọi API, không đụng data/."""
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from core import access, change_review as CR, llm_io, qc_overrides, runner, video_gate
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests._flags import flags_off, flags_on

RENDER = {"path": "render.png", "_rec": {}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(os.path.join(self.tmp, "t.db")))
        self.dir = os.path.join(self.tmp, "projects")
        os.makedirs(self.dir)
        self.pid = self.p.create_project("v7", max_retry=2)
        self.idx = 0
        for held in (runner.PREGEN_HELD, runner._PREGEN_SAID, runner.WAIT_REASONS):
            held.clear()
            self.addCleanup(held.clear)

    def tearDown(self):
        self.p.conn.close()

    def shot(self, data=None, image=True):
        self.idx += 1
        scene = self.p.create_scene(self.pid, self.idx, f"S{self.idx}")
        if data is not None:
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), scene))
            self.p.conn.commit()
        if not image:
            return scene, None
        img = self.p.create_job(scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        path = os.path.join(self.dir, str(self.pid), "images", f"job_{img}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        from PIL import Image
        Image.new("RGB", (32, 32), (img % 255, 40, 90)).save(path)
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (path, img))
        self.p.conn.commit()
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": self.idx, "motion_prompt": "she walks", "duration_sec": 5}]})
        llm_io.approve_motion_prompt(self.p, scene)
        return scene, img

    def plate(self, img, severity, msg="ĐỎ: nền ảnh lệch render 3D: đường trời lệch 18%"):
        from core import diag
        diag.record(self.p.conn, "image", severity, msg, "plate_layout", self.pid, job_id=img)

    def send(self, job):
        prov = MockVideoProvider()
        calls = []
        orig = prov.submit
        prov.submit = lambda *a, **k: calls.append(a) or orig(*a, **k)
        with mock.patch("core.video_pregen.enabled", return_value=False):
            VideoRunner(self.p, prov, self.dir).submit_pending(self.pid, only=[job])
        return calls


class VideoGate(Base):
    def test_queue_video_blocked_until_plate_check_passed(self):
        flags_on(self, "video_gate")
        scene, img = self.shot()
        self.plate(img, "error")
        job = self.p.create_job(scene, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=RENDER):
            self.assertEqual(self.send(job), [])                                   # giữ, không gửi (0 USD)
            self.assertEqual(self.p.job(job)["state"], "queued")                   # không hỏng job: tự gửi khi cổng mở
            self.assertIn("lệch nền 3D", runner.held_reason(self.p.conn, job))
            with self.assertRaises(ValueError):
                video_gate.skip(self.p.conn, img, "  ")                            # bỏ qua phải có lý do
            self.assertEqual([r["idx"] for r in video_gate.red_images(self.p.conn, self.dir, self.pid)], [1])
            video_gate.skip(self.p.conn, img, "nền lệch nhẹ, không thấy trong clip", "a@b")
            self.assertEqual(video_gate.red_images(self.p.conn, self.dir, self.pid), [])
            runner.WAIT_REASONS.clear()
            self.assertEqual(len(self.send(job)), 1)                               # bỏ qua có lý do → gửi


class M47GateHardening(Base):
    def test_m47_flag_requires_a_verified_revision_before_legacy_gate_skip(self):
        flags_on(self, "video_gate")
        scene, img = self.shot()
        qc_overrides.migrate_up(self.p.conn)
        self.p.conn.commit()
        with mock.patch.object(qc_overrides, "enabled", return_value=True):
            with self.assertRaises(access.AccessDenied):
                video_gate.skip(self.p.conn, img, "Đã rà lại nền và chấp nhận ngoại lệ.", session_token=None)
            self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM video_gate_skips").fetchone()[0], 0)

            def record_effect(conn, *, effect, **_kwargs):
                saved = {"actor_email": "editor@example.test"}
                effect(conn, saved)
                conn.commit()
                return saved

            with mock.patch.object(qc_overrides, "record_with_effect", side_effect=record_effect) as record:
                video_gate.skip(self.p.conn, img, "Đã rà lại nền và chấp nhận ngoại lệ.", who="caller-spoof",
                                session_token="session-fixture-editor")
            kwargs = record.call_args.kwargs
            self.assertEqual(kwargs["session_token"], "session-fixture-editor")
            self.assertEqual(kwargs["project_id"], self.pid)
            self.assertEqual(kwargs["target_kind"], "gate")
            saved = self.p.conn.execute("SELECT who, reason FROM video_gate_skips WHERE image_job_id=?", (img,)).fetchone()
            self.assertEqual(saved["who"], "editor@example.test")
            self.assertTrue(saved["reason"].startswith("Đã rà lại"))

    def test_m47_gate_audit_and_legacy_skip_rollback_together(self):
        flags_on(self, "video_gate")
        scene, img = self.shot()
        qc_overrides.migrate_up(self.p.conn)
        self.p.conn.commit()
        with mock.patch.object(qc_overrides, "enabled", return_value=True), \
                mock.patch.object(qc_overrides, "_human_editor", return_value="editor@example.test"):
            self.p.conn.execute(
                "CREATE TRIGGER reject_legacy_gate_skip BEFORE INSERT ON video_gate_skips "
                "BEGIN SELECT RAISE(ABORT, 'fixture write failure'); END"
            )
            self.p.conn.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                video_gate.skip(
                    self.p.conn, img, "Đã rà lại nền và chấp nhận ngoại lệ.",
                    session_token="session-fixture-editor",
                )
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0], 0)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM video_gate_skips").fetchone()[0], 0)
        self.assertFalse(self.p.conn.in_transaction)

    def test_skip_reason_minimum_is_flagged_only(self):
        with mock.patch.object(qc_overrides, "enabled", return_value=False):
            self.assertEqual(video_gate.minimum_skip_reason_length(), 3)
        with mock.patch.object(qc_overrides, "enabled", return_value=True):
            self.assertEqual(video_gate.minimum_skip_reason_length(), 15)

    def test_missing_plate_result_is_measured_once_then_read(self):
        flags_on(self, "video_gate")
        scene, img = self.shot()
        job = self.p.create_job(scene, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=RENDER), \
                mock.patch("core.plate_layout_qc.check_strict", return_value=("error", "ĐỎ: nền lệch")) as chk:
            self.assertIn("lệch nền 3D", video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
            self.assertIn("lệch nền 3D", video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
        self.assertEqual(chk.call_count, 1)                                        # kết quả ghi diag plate_layout, lần sau đọc lại

    def test_passed_plate_or_no_render_sends(self):
        flags_on(self, "video_gate")
        scene, img = self.shot()
        self.plate(img, "info", "bố cục nền khớp render 3D")
        job = self.p.create_job(scene, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=RENDER):
            self.assertIsNone(video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
        scene2, img2 = self.shot()
        job2 = self.p.create_job(scene2, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=None):           # không có render: không có gì để so
            self.assertIsNone(video_gate.hold(self.p.conn, self.dir, self.p.job(job2)))

    def test_measuring_error_never_holds_but_is_said(self):
        flags_on(self, "video_gate")
        scene, img = self.shot()
        job = self.p.create_job(scene, "video_gen")
        with mock.patch("core.place_refs.shot_ref", side_effect=OSError("render hỏng")):
            self.assertIsNone(video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
        row = self.p.conn.execute("SELECT severity, message FROM diag_events WHERE code='video_gate'").fetchone()
        self.assertEqual(row["severity"], "warn")
        self.assertIn("không kiểm được nền", row["message"])

    def test_group_queued_only_when_all_images_approved(self):
        flags_on(self, "video_gate")
        g = {"shot_no": 1, "story_scene": 3, "sequence": 2}
        s1, _ = self.shot(dict(g))
        s2, _ = self.shot(dict(g, shot_no=2), image=False)                         # shot kề chưa duyệt ảnh
        job = self.p.create_job(s1, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=None):
            why = video_gate.hold(self.p.conn, self.dir, self.p.job(job))
            self.assertIn("S02 chưa duyệt ảnh", why)
            img2 = self.p.create_job(s2)
            self.p.start(img2)
            self.p.succeed(img2)
            self.p.approve(img2)
            self.assertIsNone(video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
            redo = self.p.create_job(s2)                                           # shot kề đang vẽ lại ảnh (đổi nền) → chờ
            self.assertIn("S02 đang vẽ lại ảnh", video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
            self.p.conn.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (redo,))
            # sequence 0 = không nhóm (Bước 1)
            s3, _ = self.shot({"shot_no": 1, "story_scene": 4, "sequence": 0})
            self.shot({"shot_no": 2, "story_scene": 4, "sequence": 0}, image=False)
            j3 = self.p.create_job(s3, "video_gen")
            self.assertIsNone(video_gate.hold(self.p.conn, self.dir, self.p.job(j3)))

    def test_autopilot_waits_with_gate_reason(self):
        # R11 (rà S4): cổng giữ mọi clip đang chờ → autopilot CHỜ người có lý do (không quay "Gen video…" mãi); bỏ qua có lý do → chạy
        from core import autopilot
        flags_on(self, "video_gate")
        scene, img = self.shot()
        self.plate(img, "error")
        job = self.p.create_job(scene, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=RENDER):
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._gate_wait(self.p, self.pid, self.dir)
            self.assertEqual(w.exception.gate, "video_gate")
            self.assertIn("S01", str(w.exception))
            self.assertIn("lệch nền 3D", str(w.exception))
            self.assertIn("Bước 4", str(w.exception))                              # chỉ đường thoát
            other = self.p.create_job(self.shot()[0], "video_gen")                 # một clip khác gửi được → không dừng cả lượt
            with mock.patch("core.place_refs.shot_ref", side_effect=lambda d, p_, s: RENDER if s == scene else None):
                autopilot._gate_wait(self.p, self.pid, self.dir)
            self.p.conn.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (other,))
            video_gate.skip(self.p.conn, img, "nền lệch nhẹ, chấp nhận", "a@b")
            autopilot._gate_wait(self.p, self.pid, self.dir)                       # bỏ qua có lý do → không chờ
        self.assertEqual(self.p.job(job)["state"], "queued")

    def test_unreviewed_newer_take_is_not_called_redrawing(self):
        # R11: take ảnh mới đã về mà người chưa duyệt ≠ "đang vẽ lại ảnh"; nhóm liền mạch có nút Bỏ qua chờ nhóm (bắt buộc lý do)
        flags_on(self, "video_gate")
        g = {"shot_no": 1, "story_scene": 3, "sequence": 2}
        s1, img1 = self.shot(dict(g))
        s2, _ = self.shot(dict(g, shot_no=2))
        newer = self.p.create_job(s2)
        self.p.start(newer)
        self.p.succeed(newer)                                                      # về rồi, chờ người duyệt
        job = self.p.create_job(s1, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=None):
            why = video_gate.hold(self.p.conn, self.dir, self.p.job(job))
            self.assertIn("S02 có ảnh mới chờ duyệt", why)
            self.assertNotIn("đang vẽ lại", why)
            self.assertIn("Bỏ qua chờ nhóm", why)
            waits = video_gate.group_waits(self.p.conn, self.pid)
            self.assertEqual([(r["idx"], r["image_job_id"]) for r in waits], [(1, img1)])
            with self.assertRaises(ValueError):
                video_gate.skip(self.p.conn, img1, " ", group=True)
            video_gate.skip(self.p.conn, img1, "shot kề không đổi nền", "a@b", group=True)
            self.assertIsNone(video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
            self.assertEqual(video_gate.group_waits(self.p.conn, self.pid), [])
            self.assertIsNone(video_gate.skipped(self.p.conn, img1))               # bỏ qua chờ nhóm ≠ bỏ qua kiểm nền

    def test_shot_without_approved_image_is_not_promised_a_skip_button(self):
        # rà C1 15/10: shot chưa có ảnh khung đầu duyệt → group_waits không có nút Bỏ qua → lý do giữ chỉ nói lối ra thật
        flags_on(self, "video_gate")
        g = {"shot_no": 1, "story_scene": 3, "sequence": 2}
        s1, _ = self.shot(dict(g), image=False)
        self.shot(dict(g, shot_no=2), image=False)
        job = self.p.create_job(s1, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=None):
            why = video_gate.hold(self.p.conn, self.dir, self.p.job(job))
            self.assertIn("S02 chưa duyệt ảnh", why)
            self.assertNotIn("Bỏ qua chờ nhóm", why)
            self.assertIn("Bước 2", why)
            self.assertEqual(video_gate.group_waits(self.p.conn, self.pid), [])

    def test_flag_off_never_holds(self):
        flags_off(self, "video_gate")                                        # C1 15/10: mặc định code BẬT — ghim đường cờ TẮT
        scene, img = self.shot()
        self.plate(img, "error")
        job = self.p.create_job(scene, "video_gen")
        with mock.patch("core.place_refs.shot_ref", return_value=RENDER):
            self.assertIsNone(video_gate.hold(self.p.conn, self.dir, self.p.job(job)))
            self.assertEqual(len(self.send(job)), 1)


class UpgradeHold(Base):
    """C9: Tổ rà soát và lệnh NÂNG từ nháp đã duyệt."""

    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {"FEATURE_CHANGE_REVIEW": "1"})
        env.start()
        self.addCleanup(env.stop)

    def red(self, sid, khau, at):
        self.p.conn.execute("INSERT INTO change_findings(project_id, scene_id, source, level, khau, msg, at) VALUES (?,?,?,?,?,?,?)",
                            (self.pid, sid, "claude", "do", khau, f"lệch {khau}", at))
        self.p.conn.commit()

    def test_old_red_image_finding_does_not_hold_upgrade_from_approved_draft(self):
        scene, _ = self.shot()
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        self.red(scene, "anh", "2026-10-13T08:00:00Z")                             # mục đỏ khâu ảnh (cũ)
        self.red(scene, "motion", "2026-10-13T08:30:00Z")                          # khâu motion nhưng CŨ hơn lúc duyệt nháp
        since = "2026-10-13T09:00:00+00:00"                                        # người duyệt nháp lúc 09:00
        notes = []
        self.assertIsNone(CR.blocking(self.p.conn, scene, since=since, notes=notes))
        self.assertEqual(len(notes), 2)                                            # không giữ nhưng nói ra (VÀNG ở runner)
        self.assertIn("lệch", CR.blocking(self.p.conn, scene))                     # gen thường (không nâng) vẫn bị giữ như cũ
        self.red(scene, "video", "2026-10-13T09:10:00Z")                           # mục đỏ MỚI khâu video → giữ cả lệnh nâng
        self.assertIn("video", CR.blocking(self.p.conn, scene, since=since))

    def test_runner_uses_draft_approval_time_for_final(self):
        scene, _ = self.shot()
        draft = self.p.create_job(scene, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='draft', state='approved' WHERE id=?", (draft,))
        self.p.conn.execute("INSERT INTO review_log(job_id, reviewer_type, decision, decided_at) VALUES (?,?,?,?)",
                            (draft, "user", "approve", "2026-10-13T09:00:00+00:00"))
        final = self.p.create_job(scene, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='final', draft_job_id=? WHERE id=?", (draft, final))
        self.p.conn.commit()
        vr = VideoRunner(self.p, MockVideoProvider(), self.dir)
        self.assertEqual(vr._draft_approved_at(self.p.job(final)), "2026-10-13T09:00:00+00:00")
        self.assertIsNone(vr._draft_approved_at(self.p.job(draft)))
        self.p.conn.execute("INSERT INTO review_log(job_id, reviewer_type, decision, decided_at) VALUES (?,?,?,?)",
                            (draft, "ai_agent", "approve", "2026-10-13T10:00:00+00:00"))
        self.assertIsNone(vr._draft_approved_at(self.p.job(final)))               # máy duyệt sau cùng ≠ người duyệt

    def test_autopilot_review_wait_lets_upgrade_from_approved_draft(self):
        # R10 (rà S4): autopilot dùng cùng `since` như runner (C9) — mục đỏ khâu ảnh cũ không dừng bản cao nâng từ nháp người duyệt
        from core import autopilot
        scene, _ = self.shot()
        self.p.conn.execute("UPDATE change_events SET state='skipped'")
        draft = self.p.create_job(scene, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='draft', state='approved' WHERE id=?", (draft,))
        self.p.conn.execute("INSERT INTO review_log(job_id, reviewer_type, decision, decided_at) VALUES (?,?,?,?)",
                            (draft, "user", "approve", "2026-10-13T09:00:00+00:00"))
        final = self.p.create_job(scene, "video_gen")
        self.p.conn.execute("UPDATE jobs SET quality_tier='final', draft_job_id=? WHERE id=?", (draft, final))
        self.p.conn.commit()
        self.red(scene, "anh", "2026-10-13T08:00:00Z")
        autopilot._review_wait(self.p, self.pid, "video_gen", self.dir)            # không ném _Wait
        self.p.conn.execute("UPDATE jobs SET draft_job_id=NULL WHERE id=?", (final,))
        with self.assertRaises(autopilot._Wait):                                   # gen thường vẫn chờ người như cũ
            autopilot._review_wait(self.p, self.pid, "video_gen", self.dir)


class Migration(unittest.TestCase):
    def test_old_database_gets_table_and_trigger_and_reruns_safely(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "old.db")
        c = connect(path)
        c.execute("DROP TRIGGER trg_change_motion")
        c.execute("DROP TABLE video_gate_skips")
        c.execute("PRAGMA user_version=0")
        c.commit()
        c.close()
        from core import db
        db._MIGRATED.clear()
        for _ in range(2):                                                         # chạy lại nhiều lần không lỗi
            c = connect(path)
            names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE name IN ('trg_change_motion','video_gate_skips')")}
            self.assertEqual(names, {"trg_change_motion", "video_gate_skips"})
            c.close()
            db._MIGRATED.clear()


if __name__ == "__main__":
    unittest.main()
