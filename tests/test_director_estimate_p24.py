"""08/10 dự án #24: nút "🤖 Chạy Director hai lượt … Claude ≈ 0.21 USD (ước tính)" nhưng thực chi 0,47 USD (usage_events stage='director':
Tầng A vào 46.254 / ra 8.195; Tầng B vào 2.758 + ghi cache 56.750 / ra 14.457, claude-sonnet-5). Luật chi phí: ước tính phải tính DƯ —
đếm token phần vào nhân hệ số đo được, phần ra không dưới mức lớn nhất đã đo ở các lượt thật."""
import os
import unittest
from unittest import mock

from core import director_two_pass as dtp
from tests.test_v3 import kenta_project

MODEL = "claude-sonnet-5"
REAL = {"input": 46254 + 2758, "cache_write": 56750, "output": 8195 + 14457}


def ledger(p, pid):
    rows = [("2026-10-08 10:38:26", "input", 46254), ("2026-10-08 10:38:26", "output", 8195),
            ("2026-10-08 10:41:06", "input", 2758), ("2026-10-08 10:41:06", "output", 14457), ("2026-10-08 10:41:06", "cache_write", 56750)]
    for at, tier, q in rows:
        p.conn.execute("INSERT INTO usage_events (project_id, kind, provider, model, tier, quantity, unit, at, stage)"
                       " VALUES (?, 'llm', 'anthropic', ?, ?, ?, 'token', ?, 'director')", (pid, MODEL, tier, q, at))
    p.conn.commit()


class DirectorEstimateTests(unittest.TestCase):
    def test_measured_reads_tier_a_and_b_from_the_ledger(self):
        p, pid = kenta_project()
        ledger(p, pid)
        m = dtp.measured(p.conn, MODEL)
        self.assertEqual((m["a_out"], m["b_out"], m["b_in"], m["b_common"], m["calls"]), (8195, 14457, 2758, 56750, 2))

    def test_two_pass_estimate_is_not_under_a_real_run(self):
        with mock.patch.dict(os.environ, {"FEATURE_DIRECTOR_TWO_PASS": "1"}):
            p, pid = kenta_project()
            ledger(p, pid)
            est = dtp.estimate(p, pid, model=MODEL)
        real = dtp._usd(MODEL, REAL)
        self.assertIsNotNone(real)
        b_call = dtp._usd(MODEL, {"input": 2758, "output": 14457})                  # one Tầng B call (the shared part cached once)
        need = dtp._usd(MODEL, {"input": 46254, "output": 8195}) + b_call * est["scenes"] + dtp._usd(MODEL, {"cache_write": 56750})
        self.assertGreaterEqual(est["two_pass"]["usd"], need * 0.95)
        self.assertGreaterEqual(est["two_pass"]["tier_a"]["output"], 8195)
        self.assertIn("lượt Director thật", dtp.estimate_text(est))


if __name__ == "__main__":
    unittest.main()
