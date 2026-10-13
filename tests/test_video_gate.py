"""V7 (rà gốc video #27 13/10, cờ video_gate — core/video_gate.py): clip chỉ GỬI khi ảnh khung đầu đã qua kiểm nền 3D (hoặc người bỏ
qua có lý do) và cả nhóm shot liền mạch đã duyệt ảnh; giữ = job vẫn chờ có lý do (không hỏng, không tốn tiền). Cờ tắt y cũ.
+ C9 (rà chuỗi 13/10): bản cao nâng từ nháp NGƯỜI đã duyệt không bị Tổ rà soát giữ vì mục đỏ khâu ảnh cũ.
CSDL tạm, provider giả, không gọi API, không đụng data/."""
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from core import change_review as CR, llm_io, runner, video_gate
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests._flags import flags_on

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

    def test_flag_off_never_holds(self):
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
