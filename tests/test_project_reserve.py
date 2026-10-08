"""Ngân sách trích riêng từng dự án (core.project_reserve — người dùng 08/10 chọn phương án 1, TODO "VIỆC ĐỂ SAU DỰ ÁN KHỦNG LONG ĐỎ" 1a)."""
import unittest
from unittest import mock

from core import archive, budget, cost, delivered, project_reserve, spend_gate
from core.db import connect
from core.pipeline import Pipeline

CLAUDE = ("llm", "claude-sonnet-5", "output", 100000)      # 1 USD of Claude output (data/pricing.json)


def est(usd):
    return mock.patch.object(project_reserve, "estimate", return_value={"usd": float(usd), "note": ""})


class ReserveTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.c = self.p.conn
        self.a = self.p.create_project("A")
        self.b = self.p.create_project("B")
        budget.restart(self.c, usd=10.0)                        # the shared trial cap: 10 USD

    def pay(self, pid, n=1, provider="real"):
        kind, model, tier, qty = CLAUDE
        for _ in range(n):
            cost.record_usage(self.c, None, kind, provider, model, tier, qty, "token", project_id=pid, stage="director")

    def log(self, pid):
        return [r["action"] for r in project_reserve.history(self.c, pid)]

    def test_first_paid_send_reserves_the_project_estimate_from_the_shared_cap(self):
        self.assertIsNone(project_reserve.get(self.c, self.a))
        with est(4.0):
            self.pay(self.a)
        r = project_reserve.get(self.c, self.a)
        self.assertEqual((r["usd"], r["source"], r["state"]), (4.0, "auto", "active"))
        self.assertEqual(self.log(self.a), ["reserve"])
        self.assertEqual(project_reserve.history(self.c, self.a)[0]["who"], project_reserve.SYSTEM)
        # the pool: 10 − 1 spent − (4 − 1) still held for A = 6
        self.assertAlmostEqual(project_reserve.free(self.c), 6.0, places=2)

    def test_mock_sends_and_a_switched_off_trial_reserve_nothing(self):
        with est(4.0):
            self.pay(self.a, provider="mock")
        self.assertIsNone(project_reserve.get(self.c, self.a))
        budget.stop(self.c)
        with est(4.0):
            self.pay(self.a)
        self.assertIsNone(project_reserve.get(self.c, self.a))

    def test_a_second_paid_send_does_not_reserve_again(self):
        with est(4.0):
            self.pay(self.a)
        with est(9.0):                                          # same shot table → no new estimate taken
            self.pay(self.a, 2)
        self.assertEqual(project_reserve.get(self.c, self.a)["usd"], 4.0)
        self.assertEqual(self.log(self.a), ["reserve"])

    def test_an_auto_share_grows_once_when_the_shot_table_changes(self):
        with est(2.0):
            self.pay(self.a)                                    # the Director's first call: no shot yet
        self.c.execute("INSERT INTO scenes (project_id, idx, data) VALUES (?, 1, '{}')", (self.a,))
        self.c.commit()
        with est(5.0):
            self.pay(self.a)
        self.assertEqual(project_reserve.get(self.c, self.a)["usd"], 5.0)
        self.assertEqual(self.log(self.a), ["top_up", "reserve"])

    def test_not_enough_left_reserves_what_remains_and_warns(self):
        with est(8.0):
            self.pay(self.a)                                    # A: 8 of 10 (1 spent)
        with est(5.0):
            self.pay(self.b)                                    # pool: 10 − 2 spent − 7 held for A = 1 (+ B's own 1) → 2
        r = project_reserve.get(self.c, self.b)
        self.assertAlmostEqual(r["usd"], 2.0, places=2)
        self.assertIn("thiếu", r["note"])
        msg = self.c.execute("SELECT message FROM diag_events WHERE code='money_warning' AND project_id=?", (self.b,)).fetchone()
        self.assertIsNotNone(msg)
        self.assertIn("THIẾU $3.00", msg[0])

    def test_another_project_cannot_use_the_reserved_share(self):
        self.c.execute("INSERT INTO usage_events (project_id, kind, provider, model, tier, quantity, unit, at)"
                       " VALUES (?, 'llm', 'real', 'claude-sonnet-5', 'output', 100000, 'token', '2020-01-01 00:00:00')", (self.b,))
        self.c.commit()                                         # B spent before the feature: never reserved (not retroactive)
        with est(8.0):
            self.pay(self.a)
            self.pay(self.b)
        self.assertIsNone(project_reserve.get(self.c, self.b))
        self.assertIn("không trích hồi tố", project_reserve.skip_reason(self.c, self.b))
        # trial since = restart time, so the 2020 row is outside it: 10 − 2 spent − 7 held for A = 1
        self.assertAlmostEqual(project_reserve.free(self.c), 1.0, places=2)
        w = project_reserve.warning(self.c, self.b, 3.0)
        self.assertIn(f"#{self.a}", w)
        self.assertIn("VẪN GỬI", w)
        self.assertIsNone(project_reserve.warning(self.c, self.b, 0.5))       # fits in what is really free
        stop, warns, _ = spend_gate.assess(self.c, "image", "real", self.b, "gpt-image-2.5-sunburst", None, 60, "images")
        self.assertIsNone(stop)                                                # a warning, never a stop
        self.assertTrue(any("lấn vào phần của dự án khác" in x for x in warns))

    def test_a_person_edits_the_share_by_hand_and_it_is_kept(self):
        with est(4.0):
            self.pay(self.a)
        r = project_reserve.set_amount(self.c, self.a, 6.5, "owner@x", "cảnh nhảy gen lại")
        self.assertEqual((r["usd"], r["source"]), (6.5, "manual"))
        h = project_reserve.history(self.c, self.a)[0]
        self.assertEqual((h["action"], h["who"], h["usd"], h["before_usd"]), ("manual", "owner@x", 6.5, 4.0))
        self.c.execute("INSERT INTO scenes (project_id, idx, data) VALUES (?, 1, '{}')", (self.a,))
        self.c.commit()
        with est(20.0):
            self.pay(self.a)                                    # a hand-set share is not topped up
        self.assertEqual(project_reserve.get(self.c, self.a)["usd"], 6.5)
        big = project_reserve.set_amount(self.c, self.a, 50.0, "owner@x")
        self.assertIn("vượt trần chung", big["warning"])        # saved anyway, warned
        with self.assertRaises(ValueError):
            project_reserve.set_amount(self.c, self.a, -1, "owner@x")

    def test_the_unused_part_returns_on_final_delivery(self):
        with est(6.0):
            self.pay(self.a, 2)                                 # 2 spent of 6
        self.assertAlmostEqual(project_reserve.free(self.c), 4.0, places=2)    # 10 − 2 − 4 held
        delivered.mark(self.c, self.a, "/out/final.mp4", by="lead@x")
        r = project_reserve.get(self.c, self.a)
        self.assertEqual((r["state"], r["returned_usd"]), ("released", 4.0))
        h = project_reserve.history(self.c, self.a)[0]
        self.assertEqual((h["action"], h["who"], h["usd"]), ("release", "lead@x", 4.0))
        self.assertAlmostEqual(project_reserve.free(self.c), 8.0, places=2)
        self.assertIsNone(project_reserve.warning(self.c, self.a, 100.0))      # released: no share warning any more

    def test_the_unused_part_returns_when_the_project_is_archived(self):
        with est(6.0):
            self.pay(self.a)
        archive.archive(self.p, self.a)
        r = project_reserve.get(self.c, self.a)
        self.assertEqual((r["state"], r["returned_usd"]), ("released", 5.0))
        self.assertEqual(self.log(self.a)[0], "release")

    def test_going_over_the_share_warns_for_that_project_and_never_stops(self):
        with est(1.5):
            self.pay(self.a)                                    # 1 spent of 1.5
        self.assertIsNone(project_reserve.warning(self.c, self.a, 0.4))
        w = project_reserve.warning(self.c, self.a, 1.0)
        self.assertIn(f"dự án #{self.a} — phần ngân sách trích riêng", w)
        self.assertIn("mức dự tính $1.50", w)
        stop, warns, _ = spend_gate.assess(self.c, "image", "real", self.a, "gpt-image-2.5-sunburst", None, 20, "images")
        self.assertIsNone(stop)
        self.assertTrue(any("trích riêng" in x for x in warns))

    def test_finished_or_archived_projects_are_not_reserved(self):
        delivered.mark(self.c, self.a, "/out/final.mp4")
        self.c.execute("UPDATE projects SET archived=1 WHERE id=?", (self.b,))
        self.c.commit()
        with est(4.0):
            self.pay(self.a)
            self.pay(self.b)
        self.assertIsNone(project_reserve.get(self.c, self.a))
        self.assertIsNone(project_reserve.get(self.c, self.b))
        self.assertEqual(project_reserve.skip_reason(self.c, self.a), "dự án đã giao bản cuối")
        self.assertEqual(project_reserve.skip_reason(self.c, self.b), "dự án đã cất")

    def test_a_reservation_error_never_breaks_the_ledger(self):
        with mock.patch.object(project_reserve, "on_paid", side_effect=RuntimeError("hỏng")):
            self.pay(self.a)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM usage_events WHERE project_id=?", (self.a,)).fetchone()[0], 1)
        self.assertIsNotNone(self.c.execute("SELECT 1 FROM diag_events WHERE code='project_reserve'").fetchone())

    def test_the_real_estimate_is_used_by_default(self):
        from tests.test_v3 import kenta_project
        p, pid = kenta_project(shot_mode="per_shot")
        budget.restart(p.conn, usd=50.0)
        kind, model, tier, qty = CLAUDE
        cost.record_usage(p.conn, None, kind, "real", model, tier, qty, "token", project_id=pid, stage="director")
        r = project_reserve.get(p.conn, pid)
        self.assertIsNotNone(r)
        self.assertGreaterEqual(r["usd"], 1.0)                  # at least what is spent already
        self.assertEqual(r["estimate_usd"], r["usd"])


if __name__ == "__main__":
    unittest.main()
