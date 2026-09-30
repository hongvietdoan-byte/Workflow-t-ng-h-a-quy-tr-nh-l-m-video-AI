"""Data Pack P5 (S10.11): a service that says it is out of money stops every later paid send to it — said, not retried in a loop — until a
person reopens it."""
import unittest

from core import budget
from core.adapters.http import ApiClient, HttpResponse, out_of_credit, parse_envelope
from core.db import connect
from core.providers import ProviderError


class OutOfCreditTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def test_the_words_are_narrow(self):
        self.assertTrue(out_of_credit("Insufficient balance, please recharge"))
        self.assertTrue(out_of_credit("账户余额不足"))
        self.assertTrue(out_of_credit("Your credit balance is too low to access the Anthropic API"))
        self.assertFalse(out_of_credit("rate limit: too many requests"))
        self.assertFalse(out_of_credit("quota exceeded for requests per minute"))     # a rate quota, not money

    def test_http_402_and_an_envelope_saying_so_are_out_of_credit(self):
        client = ApiClient("https://api.example", "tok", "test", transport=lambda *a: HttpResponse(402, b'{"msg":"payment required"}'))
        with self.assertRaises(ProviderError) as cm:
            client.get("/x")
        self.assertEqual(cm.exception.code, "out_of_credit")
        self.assertFalse(cm.exception.transient)
        with self.assertRaises(ProviderError) as cm:
            parse_envelope({"code": 4001, "msg": "余额不足"})
        self.assertEqual(cm.exception.code, "out_of_credit")

    def test_a_halt_refuses_that_service_only_until_reopened(self):
        budget.halt(self.conn, "clipai", "HTTP 402")
        stop = budget.check_video(self.conn, "clipai", "kling-v3-omni", "std", 3)
        self.assertIn("HẾT TIỀN", stop)
        self.assertIn("HẾT TIỀN", budget.check_audio(self.conn, "clipai_audio"))
        self.assertIsNone(budget.halted(self.conn, "deepix"))
        self.assertIsNone(budget.check_video(self.conn, "mock", "kling-v3-omni", "std", 3))       # tests / dry runs unaffected
        budget.reopen(self.conn, "clipai")
        self.assertIsNone(budget.halted(self.conn, "clipai"))
        budget.halt(self.conn, "anthropic", "credit balance is too low")
        self.assertIn("HẾT TIỀN", budget.check_llm(self.conn, 0.01))


if __name__ == "__main__":
    unittest.main()
