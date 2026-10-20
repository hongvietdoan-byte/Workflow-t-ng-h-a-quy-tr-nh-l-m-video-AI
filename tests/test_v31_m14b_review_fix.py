"""C-RA-M14B (cloud-C, 20/10): rà độc lập nhánh M1.4b — mỗi lỗi một test ĐỎ trước khi sửa (docs/RA_CLOUD_M14B_REVIEW_2026-10-20.md).
Provider giả, không mạng, 0 USD."""
import os
from datetime import datetime, timedelta, timezone
from unittest import mock

from core import llm_provider, llm_runner as lr
from core.states import JobState
from tests.test_v31_m14b_provider import Base, Done

NO_TIME = '{"is_error": true, "result": "Claude AI usage limit reached|1760000000"}'


class QuotaWithoutResetTime(Base):
    """CAO-1: không đọc được giờ mở lại → dừng VĨNH VIỄN (không có nơi nào gọi quota_reopen) dù lời báo bảo 'mở lại trong ⚙'."""

    def test_it_probes_again_by_itself_after_the_probe_delay(self):
        t0 = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        llm_provider.quota_halt(self.conn, "claude_cli", "usage_limit", "limit reached", now=t0)
        code, why = llm_provider.quota_halted(self.conn, "claude_cli", now=t0 + timedelta(minutes=5))
        self.assertEqual(code, "usage_limit")
        self.assertIn("chưa đọc được giờ mở lại", why)
        self.assertIn("tự thử lại", why)
        later = t0 + timedelta(minutes=llm_provider.PROBE_MINUTES + 1)
        self.assertIsNone(llm_provider.quota_halted(self.conn, "claude_cli", now=later))

    def test_reopen_is_reachable_and_lists_the_halts(self):
        llm_provider.quota_halt(self.conn, "claude_cli", "out_of_credit", "Credit balance is too low")
        self.assertEqual(list(llm_provider.quota_all(self.conn)), ["claude_cli"])
        llm_provider.quota_reopen(self.conn, "claude_cli")
        self.assertEqual(llm_provider.quota_all(self.conn), {})

    def test_the_settings_card_offers_the_reopen_button(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "dashboard", "header.py"), encoding="utf-8").read()
        self.assertIn("llm_provider.quota_reopen", src)

    def test_a_reset_with_a_date_is_still_read(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        self.assertIsNotNone(llm_provider.reset_at("Weekly limit reached · resets Oct 21, 4am (Asia/Ho_Chi_Minh)", now))


class ChangeReviewStopsTheRound(Base):
    """VỪA-1: hết lượt giữa lượt Tổ rà soát → mọi thay đổi còn lại thành 'failed' (phải bấm thử lại từng shot), gọi tiếp từng thay đổi."""

    def _event(self, scene):
        self.conn.execute("INSERT INTO change_events(at, kind, project_id, scene_id, before, after) VALUES ('2026-10-20','scene',?,?,"
                          "'{}','{}')", (self.a, scene))

    def test_quota_stops_the_round_and_keeps_the_changes_pending(self):
        from core import change_review
        s2 = self.p.create_scene(self.a, 2, "CẢNH 2")
        self._event(self.sa)
        self._event(s2)
        self.conn.commit()
        calls = []

        def boom(*a, **k):
            calls.append(1)
            raise lr.LlmError("You've hit your session limit · resets 4:20am (Asia/Ho_Chi_Minh)", code="usage_limit")
        with mock.patch.object(change_review, "claude_review", boom), \
             mock.patch.object(change_review, "affected_scenes", lambda conn, ev: [ev["scene_id"]]), \
             mock.patch.object(change_review, "code_rules", lambda *a, **k: None), \
             mock.patch.object(change_review, "changed_keys", lambda *a, **k: ["image_prompt"]), \
             mock.patch.object(change_review, "_before_director", lambda *a, **k: False), \
             mock.patch("core.change_audit.audit_shot", lambda *a, **k: []), \
             mock.patch.object(change_review, "motion_enabled", return_value=True):
            res = change_review.process_pending(self.conn, self.dir, client="ENV")
        self.assertEqual(len(calls), 1)                                     # lượt dừng ngay, không gọi tiếp
        states = [r[0] for r in self.conn.execute("SELECT state FROM change_events ORDER BY id")]
        self.assertEqual(states, ["code_only", "pending"])                 # luật code đã chạy → chờ Claude như "không có Claude"; cái sau chưa đụng
        self.assertEqual(res["failed"], 0)
        self.assertTrue(res.get("halted"))


class VideoBatchStopsOnUsageLimit(Base):
    """VỪA-2: qc_video_batch không dừng khi hết lượt gói (chỉ auth/config/out_of_credit/ledger) → thử từng clip."""

    def test_usage_limit_breaks_the_batch(self):
        from core import claude_tasks
        tried = []

        def qc(p, jid, client, data_dir):
            tried.append(jid)
            raise lr.LlmError("limit", code="usage_limit")
        with mock.patch.object(claude_tasks, "unchecked_videos", return_value=[1, 2, 3]), \
             mock.patch.object(claude_tasks, "qc_video", qc), mock.patch("core.access.need_edit"):
            out = claude_tasks.qc_video_batch(self.p, self.a, object(), self.dir)
        self.assertEqual(tried, [1])
        self.assertEqual(len(out["failed"]), 1)


class BatchQcUsesTheJobsSnapshot(Base):
    """VỪA-3: QC hàng loạt (autoqc ảnh, autopilot) dùng client DỰ ÁN cho mọi job — job đã chụp provider khác bị chấm bằng provider khác."""

    def _image_job(self, provider):
        jid = self.p.create_job(self.sa)
        self.conn.execute("UPDATE jobs SET llm_provider=?, state='succeeded' WHERE id=?", (provider, jid))
        self.conn.commit()
        return jid

    def test_run_qc_batch_asks_each_jobs_client(self):
        j1, j2 = self._image_job("mock"), self._image_job("claude_cli")
        used = []
        with mock.patch.object(lr, "run_qc", lambda p, jid, client, d, **k: used.append((jid, type(client).__name__)) or
                               {"decision": "approve", "input_tokens": 0, "output_tokens": 0}), \
             mock.patch("core.access.need_edit"):
            lr.run_qc_batch(self.p, self.a, "PROJECT", self.dir, client_for_job=llm_provider.JobClients(self.conn).or_default("PROJECT"))
        self.assertEqual(used, [(j1, "MockLlm"), (j2, "ClaudeCliClient")])

    def test_autoqc_image_round_uses_the_snapshot(self):
        from core import autoqc
        j1 = self._image_job("mock")
        used = []

        def run_qc(p, jid, client, d, **k):
            used.append(type(client).__name__)
            p.transition(jid, JobState.PENDING_REVIEW, actor="ai_agent")
        with mock.patch.object(lr, "run_qc", run_qc), mock.patch("core.qc_scene.active", return_value=False):
            autoqc._work(self.db, self.dir, self.a, llm_provider.project_factory(self.db, self.a), per_job=True)
        self.assertEqual(used, ["MockLlm"])
        self.assertTrue(j1)


class AutopilotSaysWhenClaudeReopens(Base):
    """VỪA-4: autopilot dừng vì hết lượt nhưng ghi chú cắt 80 ký tự cuối → mất giờ mở lại; hết tiền claude_cli lại bảo 'nạp Anthropic'."""

    def test_stop_note_carries_the_reopen_time(self):
        from core import autopilot
        llm_provider.quota_halt(self.conn, "claude_cli", "usage_limit", "You've hit your session limit · resets 4:20am (Asia/Ho_Chi_Minh)")
        err = lr.LlmError("x" * 300, code="usage_limit")
        with self.assertRaises(autopilot._Stop) as stop:
            autopilot._stop_if_claude_blocked([(1, err)], self.conn)
        self.assertIn("mở lại lúc", str(stop.exception))

    def test_cli_out_of_credit_does_not_say_anthropic(self):
        from core import autopilot
        llm_provider.quota_halt(self.conn, "claude_cli", "out_of_credit", "Credit balance is too low")
        with self.assertRaises(autopilot._Stop) as stop:
            autopilot._stop_if_claude_blocked([(1, lr.LlmError("Credit balance is too low", code="out_of_credit"))], self.conn)
        self.assertNotIn("Anthropic", str(stop.exception))
