"""C-FIX-M16-17 (cloud-C 20/10): lỗi rà kỹ của phiên chính trên M1.6 (cờ send_estimate) + M1.7 (cờ stale_code_alarm, diag_merge).
Mỗi lỗi một test ĐỎ trước khi sửa. Không gọi dịch vụ tốn tiền, không đọc data/ thật."""
import inspect
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

from core import code_version, cost, diag, quality_tier as qt
from core.db import connect
from tests.test_cost_route_e1 import ON, Base
from tests.test_v31_m16_send_estimate import FLAG_ON, REF_S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


class RetryOfAFinalIsPricedAsTheUpgrade(Base):
    """CAO: send_clip_usd tính bậc qua batch._draft_tier (không có job cha) → gen lại / thử lại một bản cao kế thừa bậc 'final' của cha
    (quality_tier.tier_for_new_job) mà nút báo giá nháp 480p (~1,15 USD) thay vì bước nâng 1080p (~6,36 USD)."""
    REF = {"seconds": REF_S, "warnings": []}

    def _failed_final(self):
        draft = self.approved_draft()
        jid = self.p._insert_job(self.pid, self.s1, "video_gen", quality_tier="final", draft_job_id=draft)   # như quality_tier:686
        self.p.start(jid)
        self.p.fail(jid, "server_error: thử")
        return draft, jid

    def test_retry_of_a_final_costs_at_least_the_upgrade(self):
        with ON, FLAG_ON, mock.patch.object(cost, "video_reference_seconds", return_value=self.REF):
            draft, final = self._failed_final()
            self.assertEqual(qt.tier_for_new_job(self.p.conn, self.s1, final)["quality_tier"], "final")
            got = cost.clip_estimate(self.p.conn, self.s1, parent_job_id=final)
            want = qt.upgrade_price("9:16", 4.0, REF_S)
            new_job = cost.clip_estimate(self.p.conn, self.s1)                       # job mới (không cha): vẫn giá nháp như M1.6
        self.assertGreaterEqual(got, want)
        self.assertLess(new_job, want)

    def test_the_step4_buttons_pass_the_job(self):
        src = open(os.path.join(ROOT, "dashboard", "steps", "step4.py"), encoding="utf-8").read()
        self.assertIn('cost.clip_estimate(p.conn, p.job(job["id"])["scene_id"], parent_job_id=job["id"])', src)   # ↻ Gen lại clip này
        self.assertIn("cost.clip_estimate(p.conn, p.job(j)[\"scene_id\"], parent_job_id=j)", src)               # thử lại clip lỗi


class PregenCheckSaysWhichClaude(unittest.TestCase):
    """VỪA: pregen_check chạy ngoài Dashboard không có LLM_PROVIDER → claude_free() sai → cộng Claude giá API (hoặc ngược lại)."""

    def test_reads_llm_provider_from_dashboard_env_only(self):
        import pregen_check
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "dashboard.env"), "w", encoding="utf-8") as f:
            f.write("ANTHROPIC_API_KEY=sk-ant-SECRET\nLLM_PROVIDER=claude_cli\nFEATURE_X=1\n")
        self.assertEqual(pregen_check.llm_provider_of(os.path.join(d, "dashboard.env")), "claude_cli")
        self.assertIsNone(pregen_check.llm_provider_of(os.path.join(d, "none.env")))

    def test_flag_overrides_and_the_line_is_printed(self):
        import pregen_check
        src = inspect.getsource(pregen_check.main)
        self.assertIn("--llm-provider", src)
        self.assertIn("Claude tính theo LLM_PROVIDER=", src)


class MemoKeysFollowClaudeFree(unittest.TestCase):
    """THẤP: khóa _memo của giá nút không có claude_free() → đổi LLM_PROVIDER giữa lượt vẫn lấy giá cũ."""

    def test_rewrite_and_video_batch_keys_carry_claude_free(self):
        src = inspect.getsource(cost.image_button_tag) + inspect.getsource(cost.video_batch_tag)
        self.assertEqual(src.count("claude_free()"), 2)


class ModelLineSharesTheSendPrice(unittest.TestCase):
    """THẤP: dashboard/model_line tự tính lại giá nháp → khác send_clip_usd (thiếu sàn bảng giá)."""

    def test_model_line_uses_send_clip_usd_with_the_flag(self):
        src = open(os.path.join(ROOT, "dashboard", "model_line.py"), encoding="utf-8").read()
        self.assertIn("cost.send_clip_usd(", src)


class StaleCodeIsAboutCodeNotCommits(unittest.TestCase):
    """VỪA: so sha HEAD → mọi commit (kể cả chỉ TODO.md / hộp thư) báo 'code cũ' giả. Nay so dấu vân tay các .py của core/ + dashboard/."""

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base, True)
        for sub in ("core", "dashboard"):
            os.makedirs(os.path.join(self.base, sub))
            with open(os.path.join(self.base, sub, "a.py"), "w") as f:
                f.write("x = 1\n")
        self.db = os.path.join(self.base, "data", "m.sqlite")
        os.makedirs(os.path.dirname(self.db))
        self.flag = mock.patch.dict(os.environ, {"FEATURE_STALE_CODE_ALARM": "1"})
        self.flag.start()
        self.addCleanup(self.flag.stop)

    def _boot(self):
        fp = code_version.code_fingerprint(self.base)
        return mock.patch.dict(code_version.BOOT, {"code": fp, "sha": "a" * 40, "pid": os.getpid(), "at": time.time(), "port": "8501"})

    def test_a_commit_of_todo_only_is_not_stale(self):
        with self._boot():
            code_version.register(8501, self.db, root=self.base)
            with open(os.path.join(self.base, "TODO.md"), "w") as f:
                f.write("hộp thư")
            self.assertEqual(code_version.stale_instances(self.db, head="b" * 40, root=self.base), [])
            self.assertIsNone(code_version.self_stale(head="b" * 40, root=self.base))

    def test_a_changed_python_file_is_stale(self):
        with self._boot():
            code_version.register(8501, self.db, root=self.base)
            time.sleep(0.01)
            with open(os.path.join(self.base, "core", "a.py"), "w") as f:
                f.write("x = 2  # đổi\n")
            self.assertEqual(len(code_version.stale_instances(self.db, head="b" * 40, root=self.base)), 1)
            self.assertIsNotNone(code_version.self_stale(head="b" * 40, root=self.base))

    def test_a_dead_process_record_is_removed(self):
        """THẤP: bản ghi pid chết nằm mãi trong run/ (pid dùng lại → báo nhầm)."""
        with self._boot():
            path = code_version.register(8503, self.db, root=self.base)
            with open(os.path.join(self.base, "core", "a.py"), "w") as f:
                f.write("x = 3\n")
            self.assertEqual(code_version.stale_instances(self.db, head="b" * 40, root=self.base, alive=lambda pid: False), [])
        self.assertFalse(os.path.exists(path))

    def test_a_reused_pid_is_not_the_old_dashboard(self):
        with self._boot():
            path = code_version.register(8504, self.db, root=self.base)
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
            rec["at"] = time.time() - 3600
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rec, f)
            with open(os.path.join(self.base, "core", "a.py"), "w") as f:
                f.write("x = 4\n")
            with mock.patch.object(code_version, "_started_at", return_value=time.time()):   # tiến trình mang pid này mới chạy
                self.assertEqual(code_version.stale_instances(self.db, head="b" * 40, root=self.base), [])


class StopDashboardNeverPrintsTheCommandLine(unittest.TestCase):
    """THẤP: -All in CommandLine (có thể mang token) và tắt dashboard.serve của repo KHÁC trên máy."""

    def test_script(self):
        src = open(os.path.join(ROOT, "tools", "stop_dashboard.ps1"), encoding="utf-8").read()
        self.assertNotIn("$($p.CommandLine)", src)
        self.assertIn("$PSScriptRoot", src)                 # lọc theo thư mục repo của chính script


class PlateStaleMergeKeepsFirstSeen(unittest.TestCase):
    """THẤP: gộp plate_stale theo (mã, shot, job) — giữ `at` lần đầu + `last_at` lần cuối + đếm (không mất mốc bắt đầu)."""

    def test_first_at_is_kept(self):
        conn = connect(":memory:")
        with mock.patch.dict(os.environ, {"FEATURE_DIAG_MERGE": "1"}):
            diag.record(conn, "image", "warn", "nền 3D cũ: plate A", "plate_stale", 1, scene_id=5)
            first = conn.execute("SELECT at FROM diag_events").fetchone()[0]
            time.sleep(1.1)
            diag.record(conn, "image", "warn", "nền 3D cũ: plate B", "plate_stale", 1, scene_id=5)
        rows = conn.execute("SELECT at, last_at, count, message FROM diag_events").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["at"], first)
        self.assertGreater(rows[0]["last_at"], first)
        self.assertEqual(rows[0]["count"], 2)
        self.assertIn("plate A", rows[0]["message"])          # lần gộp nói cả nền trước (không mất 'item' cũ)
        self.assertIn("plate B", rows[0]["message"])
