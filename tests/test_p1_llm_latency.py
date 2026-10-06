"""TODO Tồn đọng P1 (Data Pack 29/09): mỗi lời gọi Claude ghi thời gian chờ (latency_ms) + request-id của Anthropic vào llm_calls; Giám
sát hiện thời gian trung bình / chậm nhất theo khâu thay câu "Chưa đo thời gian gọi Claude". Lỗi HTTP kèm request-id để hỏi Anthropic."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_runner, perf
from core.adapters.http import HttpResponse
from core.db import connect


def _transport(status=200, rid="req_011ABC"):
    def send(method, url, headers, body, timeout):
        payload = ({"content": [{"type": "text", "text": "OK"}], "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 5}}
                   if status == 200 else {"error": {"message": "boom"}})
        return HttpResponse(status, json.dumps(payload).encode(), {"request-id": rid} if rid else {})
    return send


class LatencyTests(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        self.conn = connect(self.db)

    def client(self, **kw):
        return llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=_transport(**kw), sleep=lambda s: None, ledger=self.db)

    def test_reply_and_ledger_carry_latency_and_request_id(self):
        with mock.patch.object(llm_runner.time, "monotonic", side_effect=[100.0, 101.234]), llm_runner.tagged("qc", None):
            reply = self.client().complete("x")
        self.assertEqual((reply.request_id, reply.latency_ms), ("req_011ABC", 1234))
        row = self.conn.execute("SELECT stage, latency_ms, request_id FROM llm_calls").fetchone()
        self.assertEqual(tuple(row), ("qc", 1234, "req_011ABC"))

    def test_missing_header_is_empty_not_an_error(self):
        reply = self.client(rid=None).complete("x")
        self.assertEqual(reply.request_id, "")
        self.assertGreaterEqual(reply.latency_ms, 0)

    def test_http_error_names_the_request_id(self):
        with self.assertRaises(llm_runner.LlmError) as e:
            self.client(status=400, rid="req_bad").complete("x")
        self.assertIn("req_bad", str(e.exception))

    def test_old_response_without_headers_still_works(self):
        self.assertEqual(HttpResponse(200, b"{}").headers, {})

    def test_latency_table_by_stage(self):
        for stage, ms in (("qc", 1000), ("qc", 3000), ("motion", 8000), ("qc", None)):
            self.conn.execute("INSERT INTO llm_calls (at, stage, model, latency_ms) VALUES (datetime('now'), ?, 'm', ?)", (stage, ms))
        self.conn.commit()
        rows = {r["stage"]: r for r in perf.llm_latency(self.conn, days=7)}
        self.assertEqual((rows["qc"]["calls"], rows["qc"]["avg_s"], rows["qc"]["max_s"]), (2, 2.0, 3.0))
        self.assertEqual(rows["motion"]["max_s"], 8.0)
        self.assertEqual(perf.llm_latency(connect(), days=7), [])

    def test_monitor_no_longer_says_not_measured(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "dashboard", "admin.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("Chưa đo thời gian gọi Claude", src)
        self.assertIn("perf.llm_latency(", src)


if __name__ == "__main__":
    unittest.main()
