"""V3.1 M4.7 phần XEM (C-M47A, cờ send_preview_panel TẮT): thẻ clip Bước 4 — khung gập "Gói sẽ gửi" dựng bằng ĐÚNG đường của nút Gen
(VideoRunner._submit_args / _submit_kwargs / _build_package), KHÔNG gọi nhà cung cấp, không ghi CSDL / diag; khung "QC shadow" đọc
M4.2 (video_qc.jsonl), M4.3 (continuity_shadow.json), M4.1 (qc_evidence). Không có nút sửa / override. Provider giả, CSDL tạm."""
import functools
import inspect
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_io, send_preview as SP
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockVideoProvider
from core.runner import VideoRunner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _spy(provider, name):
    orig = getattr(provider, name)
    calls = []

    @functools.wraps(orig)
    def wrapper(*a, **k):
        calls.append((a, k))
        return orig(*a, **k)
    setattr(provider, name, wrapper)
    return calls


class FlagTests(unittest.TestCase):
    def test_flag_registered_and_off(self):
        from core import features
        self.assertIn(SP.FLAG, features.FEATURES)
        with mock.patch.dict(os.environ, {"FEATURE_SEND_PREVIEW_PANEL": ""}):
            self.assertFalse(SP.enabled())

    def test_registered_in_areas(self):
        areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))
        step4 = next(a for a in areas["areas"] if a["id"] == "step4")
        for f in ("core/send_preview.py", "dashboard/send_preview_ui.py"):
            self.assertIn(f, step4["code"])
        self.assertIn("tests/test_v31_m47a_send_preview.py", step4["tests"])
        self.assertIn(SP.FLAG, step4["flags"])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(os.path.join(self.tmp, "t.db")))
        self.dir = os.path.join(self.tmp, "projects")
        os.makedirs(self.dir)
        self.pid = self.p.create_project("m47a", max_retry=2)

    def tearDown(self):
        self.p.conn.close()

    def video_job(self, prompt="slow push-in — Kenta “bước tới”"):
        scene = self.p.create_scene(self.pid, 1, "S1")
        img = self.p.create_job(scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": prompt}]})
        llm_io.approve_motion_prompt(self.p, scene)
        self.scene = scene
        return self.p.create_job(scene, "video_gen")


class PackagePreviewTests(Base):
    def test_preview_is_the_package_the_gen_button_sends(self):
        job = self.video_job()
        prov = MockVideoProvider()
        calls = _spy(prov, "submit")
        runner = VideoRunner(self.p, prov, self.dir)
        got = SP.video_package(self.p, runner, self.p.job(job))
        self.assertEqual(calls, [])                                         # xem trước: không gửi
        self.assertTrue(got["ok"], got)
        VideoRunner(self.p, prov, self.dir).submit_pending(self.pid)        # gửi thật (provider giả) → gói thật trên job
        real = json.loads(self.p.conn.execute("SELECT sent_package FROM jobs WHERE id=?", (job,)).fetchone()[0])
        pkg = got["package"]
        for k in ("prompt", "negative", "model", "params", "provider"):
            self.assertEqual(pkg[k], real[k], k)
        self.assertEqual([(r["param"], r["role"], r["file"]) for r in pkg["refs"]],
                         [(r["param"], r["role"], r["file"]) for r in real["refs"]])
        self.assertIsNone(pkg["external_id"])
        self.assertEqual([r["n"] for r in got["refs"]], list(range(1, len(pkg["refs"]) + 1)))   # thứ tự ref đánh số 1..n

    def test_preview_never_calls_the_provider_nor_writes(self):
        job = self.video_job()

        class Loud(MockVideoProvider):
            def submit(self, *a, **k):
                raise AssertionError("submit trong xem trước")

            def task_usage(self, *a, **k):
                raise AssertionError("hỏi nhà cung cấp trong xem trước")

        before = self.p.conn.total_changes
        diag_rows = self.p.conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0]
        got = SP.video_package(self.p, VideoRunner(self.p, Loud(), self.dir), self.p.job(job))
        self.assertTrue(got["ok"], got)
        self.assertEqual(self.p.conn.total_changes, before)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0], diag_rows)

    def test_runner_notes_are_shown_not_written(self):
        job = self.video_job()
        runner = VideoRunner(self.p, MockVideoProvider(), self.dir)
        orig = VideoRunner._submit_args

        def noisy(self_, j):
            self_._diag(j, "warn", "x_code", "ghi chú khi dựng")
            return orig(self_, j)
        with mock.patch.object(VideoRunner, "_submit_args", noisy):
            got = SP.video_package(self.p, runner, self.p.job(job))
        self.assertIn("ghi chú khi dựng", " ".join(n["text"] for n in got["notes"]))
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='x_code'").fetchone()[0], 0)

    def test_missing_input_is_said(self):
        scene = self.p.create_scene(self.pid, 1, "S1")
        job = self.p.create_job(scene, "video_gen")
        got = SP.video_package(self.p, VideoRunner(self.p, MockVideoProvider(), self.dir), self.p.job(job))
        self.assertFalse(got["ok"])
        self.assertIn("thiếu đầu vào", got["why"])

    def test_d6_is_not_called_and_said(self):
        job = self.video_job()
        with mock.patch("core.chat_prompt.enabled", return_value=True), \
             mock.patch("core.chat_prompt.rewrite", side_effect=AssertionError("Claude trong xem trước")):
            got = SP.video_package(self.p, VideoRunner(self.p, MockVideoProvider(), self.dir), self.p.job(job))
        self.assertTrue(got["ok"], got)
        self.assertTrue(any("D6" in n["text"] for n in got["notes"]))

    def test_build_error_is_said_not_raised(self):
        job = self.video_job()
        with mock.patch.object(VideoRunner, "_submit_args", side_effect=OSError("tệp mất")):
            got = SP.video_package(self.p, VideoRunner(self.p, MockVideoProvider(), self.dir), self.p.job(job))
        self.assertFalse(got["ok"])
        self.assertIn("tệp mất", got["why"])

    def test_runner_side_effects_are_guarded_in_preview(self):
        """Ghi khi DỰNG yêu cầu (lipsync 'generate_sent', ghi kiểu đánh dấu ảnh, đổi bậc direct→draft) không chạy khi xem trước."""
        from core import runner as R
        src = inspect.getsource(R.VideoRunner)
        self.assertGreaterEqual(src.count('if not self.__dict__.get("_preview")'), 4)
        self.assertIn('getattr(runner, "_preview", False)', inspect.getsource(R.chat_rewrite))

    def test_price_only_with_send_estimate(self):
        job = self.video_job()
        runner = VideoRunner(self.p, MockVideoProvider(), self.dir)
        with mock.patch("core.cost.send_estimate_on", return_value=False):
            self.assertIsNone(SP.video_package(self.p, runner, self.p.job(job))["price"])
        with mock.patch("core.cost.send_estimate_on", return_value=True), \
             mock.patch("core.cost.clip_estimate", return_value=1.25) as est:
            self.assertEqual(SP.video_package(self.p, runner, self.p.job(job))["price"], 1.25)
        self.assertEqual(est.call_args.kwargs.get("parent_job_id"), job)


class ShadowTests(Base):
    def _write(self, rel, text):
        path = os.path.join(self.dir, str(self.pid), *rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_reads_the_three_shadows_of_this_shot_only(self):
        job = self.video_job()
        mine = {"qc_run_id": "a", "job_ids": [job], "findings": [{"qc_code": "QC-V2-STILL_OVER_1_5S", "severity": "REVIEW",
                                                                   "why": "đứng yên 2 s"}], "notes": [], "chua_kiem": []}
        other = dict(mine, qc_run_id="b", job_ids=[job + 99])
        self._write(("qc_shadow", "video_qc.jsonl"), json.dumps(mine) + "\n" + json.dumps(other) + "\n")
        cont = {"expected": [{"qc_code": "QC-L13-CONTINUITY", "why": "súng mất", "evidence": {"shots": [1, 2]}},
                             {"qc_code": "QC-L13-CONTINUITY", "why": "khác", "evidence": {"shots": [5, 6]}}],
                "observed": [], "can_xem": {"1": [0], "7": [6]}}
        self._write(("qc_set", "sequence", "continuity_shadow.json"), json.dumps(cont))
        ev = {"qc_run_id": "c", "job_ids": [job], "findings": [{"qc_code": "QC-F1-BLACK", "severity": "REVIEW"}]}
        self._write(("qc_shadow", "qc_evidence.jsonl"), json.dumps(ev) + "\n" + json.dumps(dict(ev, job_ids=[0])) + "\n")
        got = SP.shadow_of(self.p.conn, self.dir, self.pid, self.p.job(job), idx=1)
        self.assertEqual([r["qc_run_id"] for r in got["video"]], ["a"])
        self.assertEqual([f["why"] for f in got["continuity"]], ["súng mất"])
        self.assertEqual(got["can_xem"], [0])
        self.assertEqual([r["qc_run_id"] for r in got["evidence"]], ["c"])

    def test_nothing_written_is_said_not_passed(self):
        job = self.video_job()
        got = SP.shadow_of(self.p.conn, self.dir, self.pid, self.p.job(job), idx=1)
        self.assertEqual((got["video"], got["continuity"], got["evidence"]), ([], [], []))
        self.assertTrue(got["notes"])                                     # nói "chưa có bản ghi", không im lặng = đạt


class UiTests(Base):
    def test_flag_off_draws_nothing(self):
        from dashboard import send_preview_ui as U
        job = self.video_job()
        with mock.patch.dict(os.environ, {"FEATURE_SEND_PREVIEW_PANEL": ""}), mock.patch.object(U, "st") as st:
            U.card_block(self.p, self.pid, self.p.job(job), None, idx=1)
        self.assertEqual(st.mock_calls, [])

    def test_flag_on_has_no_override_button(self):
        from dashboard import send_preview_ui as U
        src = inspect.getsource(U)
        self.assertIn("Gói sẽ gửi", src)
        self.assertIn("QC shadow", src)
        for word in ("override", "Bỏ qua", "Sửa", "Duyệt"):
            self.assertNotIn(f'button("{word}', src)

    def test_card_calls_the_block(self):
        src = open(os.path.join(ROOT, "dashboard", "steps", "step4.py"), encoding="utf-8").read()
        self.assertIn("send_preview_ui.card_block(p, pid, j, runner", src)


if __name__ == "__main__":
    unittest.main()
