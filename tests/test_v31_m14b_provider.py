"""V3.1 M1.4b (D02): nhà cung cấp Claude theo dự án + chụp theo job + dừng khi hết lượt có giờ mở. Provider giả, không mạng, 0 USD."""
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

from core import llm_provider, llm_runner as lr
from core.db import connect, migrate_llm_provider_down, migrate_llm_provider_up
from core.pipeline import Pipeline

LIMIT = "You've hit your session limit · resets 4:20am (Asia/Ho_Chi_Minh)"


class Done:
    def __init__(self, out, code=0, err=""):
        self.stdout, self.returncode, self.stderr = out, code, err


def no_network(*a, **k):
    raise AssertionError("không được gọi Claude API trả phí")


class Base(unittest.TestCase):
    migrate = True

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "m.sqlite")
        self.conn = connect(self.db)
        if self.migrate:
            migrate_llm_provider_up(self.conn)
        llm_provider._COLS.clear()
        self.p = Pipeline(self.conn)
        self.a = self.p.create_project("A", "auto")
        self.b = self.p.create_project("B", "auto")
        self.sa = self.p.create_scene(self.a, 1, "CẢNH 1")
        self.sb = self.p.create_scene(self.b, 1, "CẢNH 1")
        self.env = mock.patch.dict(os.environ, {"LLM_PROVIDER": "claude_cli", "ANTHROPIC_API_KEY": "sk-ant-fake-key"})
        self.env.start()
        self.which = mock.patch("shutil.which", return_value="claude")
        self.which.start()

    def tearDown(self):
        self.which.stop()
        self.env.stop()
        self.conn.close()
        llm_provider._COLS.clear()


class ProjectProvider(Base):
    def test_two_projects_two_providers_in_one_process(self):
        llm_provider.set_project_provider(self.conn, self.a, "anthropic")
        ca = llm_provider.client_for_project(self.conn, self.a, transport=no_network)
        cb = llm_provider.client_for_project(self.conn, self.b, transport=no_network)
        self.assertIsInstance(ca, lr.AnthropicClient)
        self.assertIsInstance(cb, lr.ClaudeCliClient)          # B không khai → theo LLM_PROVIDER
        self.assertEqual(ca.ledger, self.db)
        self.assertEqual(cb.ledger, self.db)

    def test_project_value_is_checked(self):
        with self.assertRaises(ValueError):
            llm_provider.set_project_provider(self.conn, self.a, "openai")
        self.conn.execute("UPDATE projects SET llm_provider='la' WHERE id=?", (self.a,))
        kind, why = llm_provider.resolve(self.conn, self.a)
        self.assertIsNone(kind)
        self.assertIn("không hợp lệ", why)

    def test_job_keeps_the_provider_it_was_created_with(self):
        old = self.p.create_job(self.sa)
        row = self.p.job(old)
        self.assertEqual(row["llm_provider"], "claude_cli")
        self.assertTrue(row["llm_config_ver"])
        llm_provider.set_project_provider(self.conn, self.a, "anthropic")      # Dashboard đổi cấu hình dự án sau khi job đã tạo
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}):      # và đổi cả môi trường
            self.assertIsInstance(llm_provider.client_for_job(self.conn, old, transport=no_network), lr.ClaudeCliClient)
            new = self.p.create_job(self.sa)
            self.assertIsInstance(llm_provider.client_for_job(self.conn, new, transport=no_network), lr.AnthropicClient)

    def test_a_retry_keeps_its_parents_provider(self):
        first = self.p.create_job(self.sa)
        llm_provider.set_project_provider(self.conn, self.a, "anthropic")
        retry = self.p._insert_job(self.a, self.sa, "image_gen", parent_job_id=first, retry_count=1)
        self.assertEqual(self.p.job(retry)["llm_provider"], "claude_cli")

    def test_empty_provider_and_a_key_never_becomes_the_paid_api(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": ""}):
            self.assertIsNone(llm_provider.client_for_project(self.conn, self.b, transport=no_network))
            self.assertIn("KHÔNG tự dùng API trả phí", llm_provider.missing_hint_for(self.conn, self.b))
            job = self.p.create_job(self.sb)
            self.assertIsNone(self.p.job(job)["llm_provider"])               # không có provider → không bịa ảnh chụp
            self.assertIsNone(llm_provider.client_for_job(self.conn, job, transport=no_network))

    def test_cli_subprocess_never_gets_the_api_key(self):
        seen = []

        def run(args, **kw):
            seen.append(kw["env"])
            return Done('{"result": "ok", "usage": {"input_tokens": 5, "output_tokens": 2}}')
        cli = llm_provider.client_for_project(self.conn, self.b)
        cli._run = run
        cli.complete("x")
        self.assertNotIn("ANTHROPIC_API_KEY", seen[0])

    def test_cli_call_is_written_with_its_provider_and_costs_nothing(self):
        cli = llm_provider.client_for_project(self.conn, self.b)
        cli._run = lambda args, **kw: Done('{"result": "ok", "usage": {"input_tokens": 50, "output_tokens": 7}}')
        with lr.tagged("qc", self.b):
            cli.complete("x")
        row = self.conn.execute("SELECT provider, input_tokens, output_tokens, project_id FROM llm_calls").fetchone()
        self.assertEqual(tuple(row), ("claude_cli", 50, 7, self.b))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], 0)   # 0 USD: không vào sổ tiền


class Callers(Base):
    def test_autopilot_uses_the_projects_claude(self):
        from core import autopilot
        llm_provider.set_project_provider(self.conn, self.a, "mock")
        with mock.patch.dict(os.environ, {"IMAGE_PROVIDER": "mock", "VIDEO_PROVIDER": "mock"}):
            self.assertIsInstance(autopilot.default_context(self.p, self.dir, self.a).llm, lr.MockLlm)
            self.assertIsInstance(autopilot.default_context(self.p, self.dir, self.b).llm, lr.ClaudeCliClient)

    def test_change_review_gives_each_change_its_projects_client(self):
        from core import change_review
        got = []
        self.conn.execute("INSERT INTO change_events(at, kind, project_id, scene_id, before, after) VALUES ('2026-10-20','scene',?,?,'{}','{}')",
                          (self.a, self.sa))
        self.conn.commit()
        with mock.patch.object(change_review, "_review_group", lambda conn, d, ev, ids, client, res: got.append((ev["project_id"], client))), \
             mock.patch.object(change_review, "motion_enabled", return_value=True):
            change_review.process_pending(self.conn, self.dir, client="ENV", client_for=lambda pid: f"P{pid}")
        self.assertEqual(got, [(self.a, f"P{self.a}")])


class Quota(Base):
    def test_usage_limit_stops_with_reopen_time_and_never_calls_the_api(self):
        calls = []

        def run(args, **kw):
            calls.append(args)
            return Done('{"is_error": true, "result": "' + LIMIT + '"}', 1)
        cli = llm_provider.client_for_project(self.conn, self.b)
        cli._run = run
        with self.assertRaises(lr.LlmError) as first:
            cli.complete("x")
        self.assertEqual(first.exception.code, "usage_limit")
        with self.assertRaises(lr.LlmError) as again:                      # lần sau: từ chối TRƯỚC khi chạy claude
            cli.complete("y")
        self.assertEqual(len(calls), 1)
        self.assertEqual(again.exception.code, "usage_limit")
        self.assertIn("mở lại lúc", str(again.exception))
        self.assertIn("KHÔNG tự chuyển", str(again.exception))
        self.assertIsInstance(llm_provider.client_for_project(self.conn, self.b, transport=no_network), lr.ClaudeCliClient)

    def test_reopens_by_itself_after_the_reset_time(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        rec = llm_provider.quota_halt(self.conn, "claude_cli", "usage_limit", LIMIT, now=now)
        self.assertEqual(rec["reset_at"], "2026-10-20T21:20:00+00:00")       # 4:20 sáng giờ VN hôm sau = 21:20 UTC
        self.assertIsNotNone(llm_provider.quota_halted(self.conn, "claude_cli", now=now))
        later = datetime(2026, 10, 20, 21, 21, tzinfo=timezone.utc)
        self.assertIsNone(llm_provider.quota_halted(self.conn, "claude_cli", now=later))

    def test_no_reset_time_is_not_guessed(self):
        rec = llm_provider.quota_halt(self.conn, "claude_cli", "out_of_credit", "Credit balance is too low")
        self.assertIsNone(rec["reset_at"])
        code, why = llm_provider.quota_halted(self.conn, "claude_cli")
        self.assertEqual(code, "out_of_credit")
        self.assertIn("chưa đọc được giờ mở lại", why)


class OldDatabase(Base):
    migrate = False

    def test_columns_absent_means_the_old_environment_behaviour(self):
        job = self.p.create_job(self.sa)                                    # không lỗi, không ghi cột chưa có
        self.assertNotIn("llm_provider", self.p.job(job).keys())
        self.assertIsInstance(llm_provider.client_for_project(self.conn, self.a), lr.ClaudeCliClient)
        self.assertIsInstance(llm_provider.client_for_job(self.conn, job), lr.ClaudeCliClient)
        with self.assertRaises(ValueError):
            llm_provider.set_project_provider(self.conn, self.a, "anthropic")
        cli = llm_provider.client_for_project(self.conn, self.a)
        cli._run = lambda args, **kw: Done('{"result": "ok", "usage": {"input_tokens": 1, "output_tokens": 1}}')
        cli.complete("x")                                                    # sổ cũ chưa có cột provider: vẫn ghi lượt gọi
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0], 1)

    def test_opening_the_database_does_not_add_the_columns(self):
        connect(self.db).close()
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(jobs)")}
        self.assertNotIn("llm_provider", cols)

    def test_migration_up_then_down(self):
        self.assertEqual(sorted(migrate_llm_provider_up(self.conn)),
                         ["jobs.llm_config_ver", "jobs.llm_provider", "llm_calls.provider", "projects.llm_provider"])
        self.assertEqual(migrate_llm_provider_up(self.conn), [])          # chạy lại không đổi gì
        llm_provider._COLS.clear()
        job = self.p.create_job(self.sa)
        self.assertEqual(self.p.job(job)["llm_provider"], "claude_cli")
        with self.assertRaises(ValueError):                                 # còn dữ liệu → từ chối gỡ
            migrate_llm_provider_down(self.conn)
        self.assertEqual(len(migrate_llm_provider_down(self.conn, force=True)), 4)
        self.assertNotIn("llm_provider", {r[1] for r in self.conn.execute("PRAGMA table_info(jobs)")})
        self.p.create_job(self.sa)                                          # code mới chạy tiếp trên CSDL đã gỡ cột


class DevsysScorer(unittest.TestCase):
    def test_claude_cli_is_the_default_and_needs_no_money_cap(self):
        from devsys import scorer
        import tools.devsys_score as ds
        with mock.patch("shutil.which", return_value="claude"):
            self.assertIsInstance(scorer.make_client("claude_cli", None), lr.ClaudeCliClient)
        self.assertNotIn("--max-usd", scorer.score_command(["step1"], "claude_cli", {}))
        self.assertIn("--max-usd", scorer.score_command(["step1"], "anthropic", {"usd_max": 0.2}))
        import argparse
        seen = {}
        orig = argparse.ArgumentParser.add_argument

        def spy(self, *a, **k):
            if "--provider" in a:
                seen.update(k)
            return orig(self, *a, **k)
        with mock.patch.object(argparse.ArgumentParser, "add_argument", spy), mock.patch.object(ds, "ROOT", tempfile.mkdtemp()):
            try:
                ds.main(["--export", "khong_co"])
            except (SystemExit, Exception):  # noqa: BLE001 - only the parser setup is looked at
                pass
        self.assertEqual(seen.get("default"), "claude_cli")


if __name__ == "__main__":
    unittest.main()
