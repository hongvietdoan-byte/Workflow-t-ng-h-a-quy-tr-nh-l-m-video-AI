"""S14.6 Gói K: đợt ngân sách có lịch sử + mức dùng theo NGÀY (core.budget_rounds). 0 USD — chỉ CSDL trong bộ nhớ."""
import unittest

from core import auth, budget, budget_rounds as R, money_reset
from core.db import connect
from core.pipeline import Pipeline

OWNER = {"email": "boss@x", "role": "owner", "perms": []}
MEMBER = {"email": "lan@x", "role": "member", "perms": ["knowledge"]}
PRICING = {"currency": "usd",
           "per_image": {"img-a": 0.05, "img-b": 0.10},
           "per_video_second": {"vid-a:720p": 0.10, "vid-a:1080p": None, "vid-b:std": 0.20},
           "per_video_clip": {},
           "per_audio": {"tts": None},
           "per_million_tokens": {"claude-x": {"input": 3.0, "output": 15.0}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.pid = self.p.create_project("Một")
        self.pid2 = self.p.create_project("Hai")
        sid = self.p.create_scene(self.pid, 1, "s1")
        self.job = self.p.create_job(sid, "image_gen")

    def ev(self, kind, model, tier, qty, at, pid=None, provider="deepix", stage=None):
        self.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at, stage)"
                          " VALUES (?,?,?,?,?,?,?,?,?,?)", (None, pid or self.pid, kind, provider, model, tier, qty, kind, at, stage))
        self.conn.commit()


class DailyTests(Base):
    def test_days_add_up_by_kind_with_counts(self):
        self.ev("image", "img-a", "1k", 2, "2026-10-03 03:00:00")                 # 0.10
        self.ev("image", "img-b", "1k", 1, "2026-10-03 04:00:00")                 # 0.10
        self.ev("video", "vid-a", "720p", 5, "2026-10-03 05:00:00")               # 0.50
        self.ev("llm", "claude-x", "input", 1_000_000, "2026-10-03 06:00:00", provider="anthropic", stage="director")   # 3.00
        self.ev("llm", "claude-x", "output", 100_000, "2026-10-03 06:00:00", provider="anthropic", stage="director")   # 1.50
        self.ev("image", "img-a", "1k", 1, "2026-10-04 03:00:00")                 # next day 0.05
        self.ev("image", "img-a", "1k", 9, "2026-10-03 03:00:00", provider="mock-images")   # simulated: never counts
        days = R.daily(self.conn, pricing=PRICING)
        self.assertEqual([d["day"] for d in days], ["2026-10-04", "2026-10-03"])            # newest first
        d = days[1]
        self.assertAlmostEqual(d["image"]["usd"], 0.20)
        self.assertEqual(d["image"]["n"], 3)
        self.assertAlmostEqual(d["video"]["usd"], 0.50)
        self.assertEqual(d["video"]["n"], 1)
        self.assertAlmostEqual(d["llm"]["usd"], 4.50)
        self.assertEqual(d["llm"]["n"], 1)                                           # one call = its input row
        self.assertAlmostEqual(d["total_usd"], 5.20)
        self.assertEqual(d["unpriced"], [])
        self.assertAlmostEqual(days[0]["total_usd"], 0.05)

    def test_day_is_vietnam_time(self):
        self.ev("image", "img-a", "1k", 1, "2026-10-03 18:00:00")                   # 01:00 on 04/10 in Việt Nam
        self.assertEqual([d["day"] for d in R.daily(self.conn, pricing=PRICING)], ["2026-10-04"])

    def test_unpriced_rows_are_estimated_high_and_named(self):
        self.ev("video", "vid-a", "1080p", 5, "2026-10-03 05:00:00")              # no price: highest of the model (0.10/s) × 1.5
        self.ev("audio", "tts", "-", 2, "2026-10-03 05:00:00")                     # no audio price at all → unpriced, no estimate
        d = R.daily(self.conn, pricing=PRICING)[0]
        self.assertAlmostEqual(d["video"]["usd"], 0.0)
        self.assertAlmostEqual(d["video"]["est_usd"], 0.75)
        self.assertIn("vid-a:1080p", d["unpriced"])
        self.assertIn("tts", d["unpriced"])
        self.assertEqual(d["audio"]["n"], 2)
        self.assertAlmostEqual(d["total_usd"], 0.75)
        self.assertAlmostEqual(d["est_usd"], 0.75)
        self.assertIn("chưa có giá", R.unpriced_note(d))
        self.assertIn("ước tính dư", R.unpriced_note(d))

    def test_filters_by_round_window_and_project(self):
        self.ev("image", "img-a", "1k", 1, "2026-10-01 03:00:00")
        self.ev("image", "img-a", "1k", 1, "2026-10-03 03:00:00")
        self.ev("image", "img-b", "1k", 1, "2026-10-03 04:00:00", pid=self.pid2)
        days = R.daily(self.conn, since="2026-10-02 00:00:00", pricing=PRICING)
        self.assertEqual([d["day"] for d in days], ["2026-10-03"])
        self.assertAlmostEqual(days[0]["total_usd"], 0.15)
        days = R.daily(self.conn, since="2026-10-02 00:00:00", project_id=self.pid2, pricing=PRICING)
        self.assertAlmostEqual(days[0]["total_usd"], 0.10)
        days = R.daily(self.conn, until="2026-10-02 00:00:00", pricing=PRICING)
        self.assertEqual([d["day"] for d in days], ["2026-10-01"])

    def test_one_day_detail_lists_every_ledger_row(self):
        self.ev("image", "img-a", "1k", 2, "2026-10-03 03:00:00", stage="storyboard")
        self.ev("video", "vid-a", "1080p", 5, "2026-10-03 05:00:00", pid=self.pid2)
        self.ev("image", "img-a", "1k", 1, "2026-10-04 03:00:00")
        rows = R.day_detail(self.conn, "2026-10-03", pricing=PRICING)
        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first["time"], "10:00:00")                                 # 03:00 UTC = 10:00 Việt Nam
        self.assertEqual(first["project"], f"#{self.pid} Một")
        self.assertEqual(first["stage"], "storyboard")
        self.assertEqual(first["provider"], "deepix")
        self.assertEqual(first["model"], "img-a")
        self.assertAlmostEqual(first["usd"], 0.10)
        self.assertFalse(first["estimated"])
        self.assertTrue(rows[1]["estimated"])
        self.assertAlmostEqual(rows[1]["usd"], 0.75)
        self.assertEqual(len(R.day_detail(self.conn, "2026-10-03", project_id=self.pid2, pricing=PRICING)), 1)

    def test_ledger_has_an_index_on_time(self):
        names = [r[1] for r in self.conn.execute("PRAGMA index_list(usage_events)")]
        self.assertIn("idx_usage_events_at", names)


class RoundTests(Base):
    def test_before_any_round_the_current_baseline_is_the_first_round(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        cur = R.current(self.conn)
        self.assertIsNone(cur["id"])
        self.assertEqual(cur["name"], R.FIRST_NAME)
        self.assertEqual(cur["started_at"], "2026-09-30 00:00:00")
        self.assertEqual(cur["planned_usd"], 20.0)
        self.assertEqual([r["name"] for r in R.history(self.conn)], [R.FIRST_NAME])

    def test_only_owner_and_reason_required_and_nothing_changes(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        before = budget.get(self.conn)
        with self.assertRaises(auth.AuthError):
            R.start_new(self.conn, MEMBER, "Đợt 2", 30, 5, "lý do")
        for why in ("", "  ", None):
            with self.assertRaises(ValueError):
                R.start_new(self.conn, OWNER, "Đợt 2", 30, 5, why)
        with self.assertRaises(ValueError):
            R.start_new(self.conn, OWNER, "  ", 30, 5, "x")
        with self.assertRaises(ValueError):
            R.start_new(self.conn, OWNER, "Đợt 2", -1, 5, "x")
        self.assertEqual(budget.get(self.conn), before)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM budget_rounds").fetchone()[0], 0)
        self.assertIsNone(money_reset.last(self.conn, "trial"))

    def test_new_round_closes_the_old_with_summary_and_moves_bars_and_plans(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00", llm_usd=5.0, llm_since="2026-09-30 00:00:00")
        self.ev("image", "img-a", "1k", 2, "2026-09-29 03:00:00")                 # before the round: not in its summary
        self.ev("image", "img-a", "1k", 2, "2026-10-01 03:00:00")                 # 0.10
        self.ev("video", "vid-a", "720p", 5, "2026-10-02 03:00:00", pid=self.pid2)   # 0.50
        self.ev("llm", "claude-x", "input", 1_000_000, "2026-10-02 04:00:00", provider="anthropic")   # 3.00
        rows = self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
        out = R.start_new(self.conn, OWNER, "Đợt 04/10", 30.0, 8.0, "chính sách tiền mới", pricing=PRICING)
        closed, opened = out["closed"], out["opened"]
        self.assertEqual(closed["name"], R.FIRST_NAME)
        self.assertEqual(closed["started_at"], "2026-09-30 00:00:00")
        self.assertEqual(closed["ended_at"], opened["started_at"])
        self.assertEqual(closed["planned_usd"], 20.0)
        s = closed["summary"]
        self.assertAlmostEqual(s["by_kind"]["image"]["usd"], 0.10)
        self.assertEqual(s["by_kind"]["image"]["n"], 2)
        self.assertAlmostEqual(s["by_kind"]["video"]["usd"], 0.50)
        self.assertAlmostEqual(s["by_kind"]["llm"]["usd"], 3.00)
        self.assertAlmostEqual(s["total_usd"], 3.60)
        self.assertAlmostEqual(s["by_project"][str(self.pid)], 0.10 + 3.00)
        self.assertAlmostEqual(s["by_project"][str(self.pid2)], 0.50)
        self.assertEqual(closed["closed_by"], "boss@x")
        # the new round + the bars through money_reset (planned amounts set, start moved to now)
        b = budget.get(self.conn)
        self.assertEqual(opened["name"], "Đợt 04/10")
        self.assertEqual(b["since"], opened["started_at"])
        self.assertGreater(b["since"], "2026-10-02 04:00:00")
        self.assertEqual((b["usd"], b["llm_usd"], b["enabled"]), (30.0, 8.0, True))
        self.assertEqual(money_reset.last(self.conn, "trial")["why"], "chính sách tiền mới")
        self.assertEqual(money_reset.last(self.conn, "claude")["why"], "chính sách tiền mới")
        self.assertEqual(R.current(self.conn)["id"], opened["id"])
        self.assertEqual([r["name"] for r in R.history(self.conn)], ["Đợt 04/10", R.FIRST_NAME])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], rows)   # ledger untouched
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='budget_round'").fetchone()[0], 1)
        # a second new round closes the first REAL round (its id), not a new "Trước 04/10"
        self.ev("image", "img-b", "1k", 1, "2099-01-01 00:00:00")
        out2 = R.start_new(self.conn, OWNER, "Đợt 3", 40.0, 8.0, "đợt tiếp", pricing=PRICING)
        self.assertEqual(out2["closed"]["id"], opened["id"])
        self.assertEqual([r["name"] for r in R.history(self.conn)], ["Đợt 3", "Đợt 04/10", R.FIRST_NAME])

    def test_window_of_a_round(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        self.assertEqual(R.window(R.current(self.conn)), ("2026-09-30 00:00:00", None))


if __name__ == "__main__":
    unittest.main()
