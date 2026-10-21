"""V11 (rà gốc video #27 13/10, cờ qc_framing_cap): QC clip phải thấy bố cục cần giữ (khung CUỐI clip cạnh ảnh khung đầu, render 3D,
khung cuối dự kiến) và trả lời câu hỏi bố cục; máy đo thấy đổi bố cục (framing_guard) → code hạ trần motion_match / artifacts.
Claude giả (không gọi API), không đọc clip thật (trích khung giả)."""
from tests._flags import pin_off
import json
import os
import tempfile
import unittest
from unittest import mock

from core import claude_tasks
from core.db import connect
from core.pipeline import Pipeline
from tests._flags import flags_off, flags_on

# job 912 (#27 shot 17): Seedance lùi máy + vẽ mặt đồng hồ, QC 1,00 — số đo framing_guard ghi trong docs/handoff/RA_GOC_VIDEO_P27
M912 = {"framing": {"measured": True, "frame0_measured": True, "flag": "framing", "kinds": ["zoom"],
                    "why": "đổi bố cục / cắt cảnh: máy lùi / thu nhỏ cảnh trong clip (nền × 0.79 ở 2.5 s so khung 0)",
                    "zoom": [[0.5, 0.97], [2.5, 0.79]]}}
HIGH = {"identity": 0.98, "physics": 0.95, "motion_match": 0.97, "artifacts": 0.96}


class FramingCap(unittest.TestCase):
    def setUp(self):
        pin_off(self, "framing_guard")                    # C-FLAGTEST8: đường cờ TẮT, không dựa mặc định
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("#27")
        self.p.conn.execute("UPDATE projects SET qc_autofix=0, qc_auto_pass_threshold=0.82, qc_reject_floor=0.3 WHERE id=?", (self.pid,))
        sid = self.p.create_scene(self.pid, 1, "S17")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": [], "action": "Kelly runs"}), sid))
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?,?, 'approved')", (sid, "Kelly runs"))
        img = self.p.create_job(sid)
        self.jid = self.p.create_job(sid, "video_gen")
        clip = os.path.join(self.tmp, "c.mp4")
        open(clip, "wb").write(b"x")
        self.p.conn.execute("UPDATE jobs SET source_job_id=?, result_path=? WHERE id=?", (img, clip, self.jid))
        first = os.path.join(self.tmp, str(self.pid), "images", f"job_{img}.png")
        os.makedirs(os.path.dirname(first))
        open(first, "wb").write(b"p")
        self.frames = []
        for n in range(6):
            f = os.path.join(self.tmp, f"f{n}.jpg")
            open(f, "wb").write(b"f")
            self.frames.append(f)
        self.p.conn.commit()
        self.p.start(self.jid)
        self.p.succeed(self.jid)

    def run_qc(self, measured):
        seen = {}

        def fake_run(p, pid, stage, prompt, validate, client, images=()):
            seen["prompt"], seen["images"] = prompt, list(images)
            return {"criteria": dict(HIGH), "issues": ""}
        with mock.patch("core.video_analysis.extract_frames", return_value=self.frames), \
                mock.patch("core.video_analysis.probe", return_value={"duration_sec": 3.0}), \
                mock.patch.object(claude_tasks, "_measure_clip", return_value=measured), \
                mock.patch.object(claude_tasks, "_run", side_effect=fake_run), \
                mock.patch("core.place_refs.shot_ref", return_value=None):
            out = claude_tasks.qc_video(self.p, self.jid, object(), self.tmp, autofix=False)
        scores = {r["criterion"]: r["score"] for r in self.p.conn.execute("SELECT criterion, score FROM qc_results WHERE job_id=?",
                                                                           (self.jid,))}
        return out, scores, seen

    def test_framing_flag_caps_score(self):
        flags_on(self, "qc_framing_cap")
        out, scores, seen = self.run_qc(M912)
        self.assertLessEqual(scores["motion_match"], claude_tasks.FRAMING_CAP)
        self.assertLessEqual(scores["artifacts"], claude_tasks.FRAMING_CAP)
        self.assertEqual(scores["identity"], 0.98)                                 # chỉ hạ hai tiêu chí bố cục
        self.assertNotEqual(out["decision"], "approved")                           # 912 không còn tự qua
        self.assertIn("Kiểm bố cục", seen["prompt"])
        self.assertIn("máy lùi", seen["prompt"])
        self.assertTrue(any("KHUNG CUỐI clip" in label for label, _ in seen["images"]))
        why = self.p.conn.execute("SELECT message FROM diag_events WHERE code='qc_framing_cap'").fetchone()
        self.assertIn("motion_match 0.97→0.50", why["message"])

    def test_no_framing_flag_keeps_scores_but_asks_layout(self):
        flags_on(self, "qc_framing_cap")
        _, scores, seen = self.run_qc({"framing": {"measured": True, "flag": None, "zoom": [[0.5, 1.0], [2.5, 1.01]]}})
        self.assertEqual(scores["motion_match"], 0.97)
        self.assertIn("chạy tại chỗ", seen["prompt"])

    def test_flag_off_prompt_and_scores_unchanged(self):
        flags_off(self, "qc_framing_cap")                                    # C1 15/10: mặc định code BẬT — ghim đường cờ TẮT
        out, scores, seen = self.run_qc(M912)
        self.assertEqual(scores["motion_match"], 0.97)
        self.assertNotIn("Kiểm bố cục", seen["prompt"])
        self.assertFalse(any("KHUNG CUỐI clip" in label for label, _ in seen["images"]))

    def test_cap_keeps_original_scores_for_trust(self):
        # R15 (rà S4): framing_guard bật (đường thật: chỉ khi đó mới có số đo bố cục) → clip bị giữ vì đổi bố cục; điểm gốc của Claude
        # giữ trong qc_results + sổ kinh nghiệm (đo QC khớp người), trần chỉ ghi diag; số đo V2 không gọi "tin được"; không gửi trùng ảnh
        flags_on(self, "qc_framing_cap", "framing_guard")
        with mock.patch("core.video_qc_context.note_case") as note:
            out, scores, seen = self.run_qc(M912)
        self.assertEqual(scores["motion_match"], 0.97)
        self.assertEqual(scores["artifacts"], 0.96)
        self.assertEqual(note.call_args[0][4]["motion_match"], 0.97)
        self.assertNotEqual(out["decision"], "approved")
        self.assertEqual(out["capped"]["motion_match"], (0.97, claude_tasks.FRAMING_CAP))
        why = self.p.conn.execute("SELECT message FROM diag_events WHERE code='qc_framing_cap'").fetchone()
        self.assertIn("motion_match 0.97→0.50", why["message"])
        self.assertNotIn("tin được", seen["prompt"])
        pics = [pic for _, pic in seen["images"]]
        self.assertEqual(pics.count(self.frames[-1]), 1)                           # khung 6/6 gửi một lần, gắn nhãn khung cuối
        self.assertTrue(any("KHUNG CUỐI clip" in label for label, _ in seen["images"]))


if __name__ == "__main__":
    unittest.main()


class EndFrameSentAndCameraMove(unittest.TestCase):
    """R12 (rà S3+S4): QC chỉ được thấy 'khung cuối DỰ KIẾN' khi clip THẬT SỰ gửi kèm khung đó (jobs.sent_package);
    _measure_clip truyền camera_move của shot vào clip_measure.measure (R5 S3)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("#27")
        self.sid = self.p.create_scene(self.pid, 1, "S17")
        self.jid = self.p.create_job(self.sid, "video_gen")
        self.end = os.path.join(self.tmp, "end.png")
        open(self.end, "wb").write(b"e")
        self.p.conn.execute("INSERT INTO end_frames (project_id, scene_id, start_job_id, state, path, created_at, updated_at)"
                            " VALUES (?,?,?, 'ready', ?, datetime('now'), datetime('now'))", (self.pid, self.sid, self.jid, self.end))
        self.p.conn.commit()

    def _layout(self, pkg):
        self.p.conn.execute("UPDATE jobs SET sent_package=? WHERE id=?", (json.dumps(pkg) if pkg is not None else None, self.jid))
        job = self.p.conn.execute("SELECT * FROM jobs WHERE id=?", (self.jid,)).fetchone()
        with mock.patch("core.place_refs.shot_ref", return_value=None):
            return [label for label, _ in claude_tasks._layout_images(self.p, job, self.tmp, [], None)]

    def test_layout_skips_end_frame_not_sent(self):
        labels = self._layout({"v": 1, "refs": [{"param": "image_path", "role": "start_frame", "path": "a.png"}], "params": {}})
        self.assertFalse(any("DỰ KIẾN" in x for x in labels))
        self.assertFalse(any("DỰ KIẾN" in x for x in self._layout(None)))       # job cũ không có gói gửi = không gửi

    def test_layout_keeps_end_frame_when_sent(self):
        labels = self._layout({"v": 1, "refs": [{"param": "last_frame", "role": "last_frame", "path": "end_m.png"}], "params": {}})
        self.assertTrue(any("DỰ KIẾN" in x for x in labels))

    def test_measure_clip_passes_camera_move(self):
        job = self.p.conn.execute("SELECT * FROM jobs WHERE id=?", (self.jid,)).fetchone()
        with mock.patch("core.clip_measure.measure", return_value={}) as m, \
                mock.patch("core.shots.approved_image_path", return_value=None):
            claude_tasks._measure_clip(self.p, job, "c.mp4", {"camera_move": "pan_left"}, None, self.tmp)
        self.assertEqual(m.call_args.kwargs.get("camera_move"), "pan_left")
