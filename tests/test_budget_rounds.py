"""S14.6 Gói K: đợt ngân sách có lịch sử + mức dùng theo NGÀY (core.budget_rounds). 0 USD — chỉ CSDL trong bộ nhớ."""
import sqlite3
import unittest
from unittest import mock

from core import auth, budget, budget_rounds as R, money_reset
from core.db import connect
from core.pipeline import Pipeline

OWNER = {"email": "boss@x", "role": "owner", "perms": []}
MEMBER = {"email": "lan@x", "role": "member", "perms": ["knowledge"]}
FIRST = "Đợt từ 30/09/2026"          # tên đợt đầu tính từ mốc thật 2026-09-30 00:00 UTC (= 07:00 giờ VN)
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
        self.assertNotIn("tts", d["unpriced"])                                    # no estimate possible → its own group
        self.assertEqual(d["no_estimate"], ["tts"])
        self.assertEqual(d["no_estimate_n"], 2)
        self.assertEqual(d["audio"]["n"], 2)
        self.assertEqual(d["audio"]["none_n"], 2)
        self.assertAlmostEqual(d["total_usd"], 0.75)
        self.assertAlmostEqual(d["est_usd"], 0.75)
        note = R.unpriced_note(d)
        self.assertIn("vid-a:1080p", note)
        self.assertIn("ước tính dư ≈ $0.75", note)
        self.assertIn("chưa có giá — không ước tính được: tts (2 lượt)", note)

    def test_only_unestimable_rows_never_say_zero_dollars(self):
        self.ev("audio", "tts", "-", 3, "2026-10-03 05:00:00")
        d = R.daily(self.conn, pricing=PRICING)[0]
        self.assertEqual(d["unpriced"], [])
        note = R.unpriced_note(d)
        self.assertNotIn("$0.00", note)
        self.assertNotIn("đã cộng vào tổng", note)
        self.assertIn("không ước tính được: tts (3 lượt)", note)
        from dashboard.design.screens import money_days
        cell = money_days._money(d["audio"])
        self.assertNotIn("$0.00", cell)
        self.assertIn("chưa có giá", cell)
        self.assertIn("3 lượt", cell)

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
        self.assertEqual(cur["name"], FIRST)
        self.assertEqual(cur["started_at"], "2026-09-30 00:00:00")
        self.assertEqual(cur["planned_usd"], 20.0)
        self.assertEqual([r["name"] for r in R.history(self.conn)], [FIRST])

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
        self.assertEqual(closed["name"], FIRST)
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
        self.assertEqual([r["name"] for r in R.history(self.conn)], ["Đợt 04/10", FIRST])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], rows)   # ledger untouched
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='budget_round'").fetchone()[0], 1)
        # a second new round closes the first REAL round (its id), not a new "Trước 04/10"
        self.ev("image", "img-b", "1k", 1, "2099-01-01 00:00:00")
        out2 = R.start_new(self.conn, OWNER, "Đợt 3", 40.0, 8.0, "đợt tiếp", pricing=PRICING)
        self.assertEqual(out2["closed"]["id"], opened["id"])
        self.assertEqual([r["name"] for r in R.history(self.conn)], ["Đợt 3", "Đợt 04/10", FIRST])

    def test_first_round_name_comes_from_the_real_baseline(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 20:00:00")       # 03:00 01/10 giờ VN
        self.assertEqual(R.current(self.conn)["name"], "Đợt từ 01/10/2026")
        budget.save(self.conn, since=None)
        self.assertEqual(R.current(self.conn)["name"], "Từ đầu sổ chi")

    def snapshot(self):
        return (budget.get(self.conn), self.conn.execute("SELECT COUNT(*) FROM budget_rounds").fetchone()[0],
                money_reset.last(self.conn, "trial"), money_reset.last(self.conn, "claude"))

    def test_summary_failure_writes_nothing(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        before = self.snapshot()
        with mock.patch.object(R, "summarize", side_effect=RuntimeError("hỏng")):
            with self.assertRaises(RuntimeError):
                R.start_new(self.conn, OWNER, "Đợt 2", 30, 5, "lý do", pricing=PRICING)
        self.assertEqual(self.snapshot(), before)

    def test_insert_failure_rolls_back_and_leaves_the_bars(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        before = self.snapshot()

        class Boom:
            def __init__(self, c):
                self._c = c

            def execute(self, sql, *a):
                if sql.startswith("INSERT INTO budget_rounds (name, started_at, planned_usd"):
                    raise sqlite3.OperationalError("đĩa đầy")
                return self._c.execute(sql, *a)

            def __getattr__(self, k):
                return getattr(self._c, k)
        with self.assertRaises(sqlite3.OperationalError):
            R.start_new(Boom(self.conn), OWNER, "Đợt 2", 30, 5, "lý do", pricing=PRICING)
        self.assertEqual(self.snapshot(), before)

    def test_bar_failure_after_the_round_is_said_with_a_fix(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        with mock.patch.object(money_reset, "set_planned", side_effect=RuntimeError("khóa CSDL")):
            with self.assertRaises(R.BarsNotReset) as cm:
                R.start_new(self.conn, OWNER, "Đợt 2", 30, 5, "lý do", pricing=PRICING)
        msg = str(cm.exception)
        self.assertIn("Đợt 2", msg)
        self.assertIn("khóa CSDL", msg)
        self.assertIn("Cách sửa", msg)
        self.assertEqual(R.current(self.conn)["name"], "Đợt 2")             # the round itself was written whole

    def test_project_and_people_bars_are_reset_with_the_round(self):
        from core import project_budget, team
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        project_budget.set_planned(self.conn, self.pid, 12.0)
        auth.add_user(self.conn, auth.Identity("boss@x", "Boss", "owner", []), "lan@x.vn", ["knowledge"])
        targets = R.reset_targets(self.conn)
        self.assertEqual(targets["projects"], {self.pid: 12.0})
        self.assertIn("lan@x.vn", targets["users"])
        out = R.start_new(self.conn, OWNER, "Đợt 2", 30, 5, "lý do", pricing=PRICING,
                          projects={self.pid: 15.0}, users=["lan@x.vn"])
        self.assertEqual(project_budget.planned(self.conn, self.pid), 15.0)
        self.assertEqual(money_reset.last(self.conn, "project", self.pid)["why"], "lý do")
        self.assertIsNotNone(team.user_baseline(self.conn, "lan@x.vn"))
        self.assertEqual(money_reset.last(self.conn, "user", "lan@x.vn")["why"], "lý do")
        self.assertEqual(sorted(out["bars"]), ["claude", f"project:{self.pid}", "trial", "user:lan@x.vn"])
        lines = R.bars_text(30, 5, {self.pid: 15.0}, ["lan@x.vn"])
        for part in ("Đợt thử", "Claude", f"dự án #{self.pid}", "lan@x.vn"):
            self.assertIn(part, lines)

    def test_unknown_project_refused_before_writing(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            R.start_new(self.conn, OWNER, "Đợt 2", 30, 5, "lý do", pricing=PRICING, projects={self.pid: 10.0})   # no budget yet
        self.assertEqual(self.snapshot(), before)

    def test_schema_stamp_covers_the_rounds_table(self):
        from core import db
        with mock.patch.object(R, "TABLE", R.TABLE.replace("close_reason TEXT", "close_reason TEXT, x TEXT")):
            db._STAMP.clear()
            changed = db.schema_stamp()
        db._STAMP.clear()
        self.assertNotEqual(changed, db.schema_stamp())

    def test_window_of_a_round(self):
        budget.save(self.conn, enabled=True, usd=20.0, since="2026-09-30 00:00:00")
        self.assertEqual(R.window(R.current(self.conn)), ("2026-09-30 00:00:00", None))


if __name__ == "__main__":
    unittest.main()
