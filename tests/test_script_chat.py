import unittest
from unittest.mock import patch
from core.db import connect
from core.pipeline import Pipeline
from core import script_chat, llm_runner, project_budget

class ScriptChatTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect(':memory:'))
        self.pid = self.p.create_project('chat')

    def test_history_survives_reload_and_is_isolated(self):
        script_chat.append(self.p, self.pid, 'user', 'Xin chào')
        other = self.p.create_project('khác')
        self.assertEqual(script_chat.history(self.p, self.pid)[0]['text'], 'Xin chào')
        self.assertEqual(script_chat.history(self.p, other), [])

    def test_last_thirty_and_folded_older(self):
        for i in range(35):
            script_chat.append(self.p, self.pid, 'user', str(i))
        old, recent = script_chat.window(self.p, self.pid)
        self.assertEqual(len(old), 5)
        self.assertEqual(len(recent), 30)
        self.assertEqual(recent[0]['text'], '5')

    def test_rules_do_not_call_model_or_edit_scenes(self):
        for text, intent in [('CẢNH 1 - NHÀ\nKENTA: Chào.', 'script'), ('sửa cảnh 2 cho vui hơn', 'edit'), ('ý tưởng: Kenta đi chợ', 'idea')]:
            self.assertEqual(script_chat.intent(text), intent)
        self.assertEqual(script_chat.intent('Bạn nghĩ nhịp phim này thế nào?'), 'chat')

    def test_free_chat_tags_one_call_and_does_not_mutate_script(self):
        class Client:
            def complete(inner, prompt, images=()):
                inner.tag = llm_runner.current_tag()
                return llm_runner.LlmReply('Nên nghỉ một nhịp trước cú chốt.', 10, 5)
        client = Client()
        script_chat.send(self.p, self.pid, 'Bạn nghĩ nhịp phim thế nào?', client)
        self.assertEqual(client.tag, ('script_chat', self.pid))
        self.assertEqual([m['role'] for m in script_chat.history(self.p, self.pid)], ['user', 'assistant'])
        self.assertFalse(self.p.project(self.pid)['script_text'])

    def test_failure_is_saved_without_auto_retry(self):
        class Client:
            calls = 0
            def complete(inner, *args):
                inner.calls += 1
                raise llm_runner.LlmError('mạng lỗi')
        client = Client()
        with self.assertRaises(llm_runner.LlmError):
            script_chat.send(self.p, self.pid, 'Bạn nghĩ thế nào?', client)
        self.assertEqual(client.calls, 1)
        self.assertIn('mạng lỗi', script_chat.history(self.p, self.pid)[-1]['text'])

    def test_chat_has_its_own_project_cost_source(self):
        self.assertEqual(project_budget.claude_stage('script_chat'), 'claude_chat')
        self.assertEqual(project_budget.STAGES['claude_chat'], 'chat Kịch bản')

    def test_real_client_records_chat_tokens_without_network(self):
        import tempfile
        from tests.test_llm_runner import Recorder, reply
        with tempfile.TemporaryDirectory() as tmp:
            db = tmp + '/chat.sqlite'
            p = Pipeline(connect(db))
            pid = p.create_project('ledger')
            transport = Recorder(reply('Nhịp ổn.'))
            client = llm_runner.AnthropicClient('test-key', transport=transport, ledger=db)
            script_chat.send(p, pid, 'Bạn thấy nhịp thế nào?', client)
            rows = p.conn.execute('SELECT stage,project_id FROM usage_events').fetchall()
            self.assertTrue(rows)
            self.assertTrue(all(r['stage'] == 'script_chat' and r['project_id'] == pid for r in rows))
            self.assertEqual(len(transport.calls), 1)
            self.assertEqual(transport.calls[0]['body']['max_tokens'], 1500)
            from core import budget_rounds
            day = budget_rounds.daily(p.conn, project_id=pid)[0]['day']
            self.assertEqual(budget_rounds.day_detail(p.conn, day, pid)[0]['stage'], 'chat Kịch bản')
            p.conn.close()

    def test_unrelated_user_cannot_read_or_send(self):
        from core import access
        self.p.user = {'email': 'stranger@example.com', 'role': 'member'}
        with self.assertRaises(access.AccessDenied):
            script_chat.history(self.p, self.pid)
        client = unittest.mock.Mock()
        with self.assertRaises(access.AccessDenied):
            script_chat.send(self.p, self.pid, 'Bạn nghĩ thế nào?', client)
        client.complete.assert_not_called()

    def test_transient_http_failure_is_not_retried(self):
        from tests.test_llm_runner import Recorder, error
        transport = Recorder(error(500))
        client = llm_runner.AnthropicClient('test-key', transport=transport)
        with self.assertRaises(llm_runner.LlmError):
            script_chat.send(self.p, self.pid, 'Bạn nghĩ thế nào?', client)
        self.assertEqual(len(transport.calls), 1)

    def test_daily_chat_is_a_subset_not_added_to_total_twice(self):
        from core import cost, budget_rounds
        cost.record_usage(self.p.conn, None, 'llm', 'real', 'claude-sonnet-5', 'output', 100000, 'token',
                          project_id=self.pid, stage='script_chat')
        day = budget_rounds.daily(self.p.conn, project_id=self.pid)[0]
        self.assertAlmostEqual(day['chat_usd'], 1.0)
        self.assertAlmostEqual(day['total_usd'], 1.0)

    def test_header_estimate_names_chat_source(self):
        from dashboard.design.screens.shell_parts import summary_detail_md
        summary = project_budget.cost_summary(self.p, self.pid)
        self.assertIn('chat Kịch bản', summary_detail_md(summary))

    def test_disconnected_client_keeps_the_user_message(self):
        with self.assertRaises(ValueError):
            script_chat.send(self.p, self.pid, 'Bạn nghĩ thế nào?', None)
        self.assertEqual(script_chat.history(self.p, self.pid)[0]['text'], 'Bạn nghĩ thế nào?')
