"""Owner-only reset of the money bars (core.money_reset): nothing in the ledger is deleted or changed."""
import os
import unittest
from unittest import mock

from core import auth, budget, money_reset, project_budget, team
from core.db import connect
from core.pipeline import Pipeline

OWNER = {"email": "boss@x", "role": "owner", "perms": []}
MEMBER = {"email": "lan@x", "role": "member", "perms": ["knowledge"]}
ON = {"FEATURE_PROJECT_BUDGET": "1"}
MODEL = "gpt-image-2.5-sunburst"


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.pid = self.p.create_project("t", created_by="lan@x")
        sid = self.p.create_scene(self.pid, 1, "s1")
        self.job = self.p.create_job(sid, "image_gen")
        self.conn.execute("UPDATE jobs SET created_by='lan@x' WHERE id=?", (self.job,))
        self.conn.commit()

    def spend(self, n, at):
        self.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                          " VALUES (?,?,?,?,?,?,?,?,?)", (self.job, self.pid, "image", "deepix", MODEL, "1152x2048", n, "image", at))
        self.conn.commit()

    def ledger(self):
        return tuple(self.conn.execute("SELECT COUNT(*), COALESCE(SUM(quantity),0), group_concat(at) FROM usage_events").fetchone())

    def test_non_owner_refused_and_nothing_changes(self):
        before = (budget.get(self.conn), self.ledger())
        for who in (MEMBER, auth.Identity("lan@x", "Lan", "member", ["knowledge"])):
            with self.assertRaises(auth.AuthError):
                money_reset.reset(self.conn, who, ["trial", "claude"], "thử")
        self.assertEqual((budget.get(self.conn), self.ledger()), before)
        self.assertIsNone(money_reset.last(self.conn, "trial"))

    def test_bad_input_refused(self):
        for reason in ("", "   ", None):
            with self.assertRaises(ValueError):
                money_reset.reset(self.conn, OWNER, ["trial"], reason)
        with self.assertRaises(ValueError):
            money_reset.reset(self.conn, OWNER, ["nope"], "x")
        with self.assertRaises(ValueError):
            money_reset.reset(self.conn, OWNER, ["user"], "x")
        with self.assertRaises(ValueError):
            money_reset.reset(self.conn, OWNER, ["project"], "x", project_id=self.pid)     # no budget yet

    def test_trial_and_claude_move_the_start_and_keep_the_caps(self):
        budget.save(self.conn, usd=42.0, llm_usd=7.0, since="2020-01-01 00:00:00", llm_since="2020-01-01 00:00:00", enabled=False)
        self.spend(2, "2020-06-01 00:00:00")
        before = self.ledger()
        money_reset.reset(self.conn, OWNER, ["trial", "claude"], "vòng mới")
        b = budget.get(self.conn)
        self.assertGreater(b["since"], "2020-01-01 00:00:00")
        self.assertGreater(b["llm_since"], "2020-01-01 00:00:00")
        self.assertEqual((b["usd"], b["llm_usd"], b["enabled"]), (42.0, 7.0, True))
        self.assertEqual(self.ledger(), before)
        self.assertEqual(money_reset.last(self.conn, "trial")["who"], "boss@x")
        self.assertEqual(money_reset.last(self.conn, "claude")["why"], "vòng mới")

    def test_user_baseline_only_changes_the_person_bar(self):
        self.spend(2, "2999-01-01 00:00:00")        # a future event counts as "after" the reset
        self.spend(3, "2000-01-01 00:00:00")        # an old one counts before it
        self.conn.execute("UPDATE jobs SET created_at='2999-01-01T00:00:00'")      # keep both inside the 30-day window
        self.conn.commit()
        total = team.spend_by_user(self.conn, None)["lan@x"]
        self.assertEqual(team.month_spend(self.conn, "lan@x"), total)
        before = self.ledger()
        money_reset.reset(self.conn, OWNER, ["user"], "tháng mới", email="Lan@X")
        self.assertEqual(self.ledger(), before)
        self.assertEqual(team.spend_by_user(self.conn, None)["lan@x"], total)          # the ledger total is unchanged
        self.assertIsNotNone(team.user_baseline(self.conn, "lan@x"))
        self.assertAlmostEqual(team.month_spend(self.conn, "lan@x"), total * 2 / 5, places=4)    # only the 2-image event is after
        self.assertEqual(money_reset.last(self.conn, "user", "lan@x")["who"], "boss@x")

    @mock.patch.dict(os.environ, ON)
    def test_project_baseline_clears_the_warning_then_warns_again(self):
        # S14.16: was "unblocks then blocks again" — the project amount warns (project_budget.warning), check never refuses
        self.spend(30, "2020-01-01 00:00:00")
        per = project_budget.spent_by_stage(self.conn, self.pid)["images"] / 30
        self.assertGreater(per, 0)
        project_budget._save(self.conn, self.pid, {"caps": {k: 1.0 for k in project_budget.STAGES}, "total": 6.0, "locked": True,
                                                   "raises": []})
        self.assertIsNotNone(project_budget.warning(self.conn, self.pid, "images", per))    # warned: already over
        self.assertIsNone(project_budget.check(self.conn, self.pid, "images", per))
        before = self.ledger()
        money_reset.reset(self.conn, OWNER, ["project"], "làm lại", project_id=self.pid)
        self.assertEqual(self.ledger(), before)
        self.assertEqual(project_budget.spent_by_stage(self.conn, self.pid)["images"], 0.0)
        self.assertIsNone(project_budget.warning(self.conn, self.pid, "images", per))
        self.assertEqual(project_budget.get(self.conn, self.pid)["resets"][0]["why"], "làm lại")
        self.spend(30, "2020-02-01 00:00:00")                                               # spending after the baseline passes the line
        self.assertIsNotNone(project_budget.warning(self.conn, self.pid, "images", per))
        self.assertEqual(money_reset.last(self.conn, "project", self.pid)["who"], "boss@x")

    def test_user_bar_reports_before_after_and_keeps_limit_a_warning(self):
        self.spend(2, "2000-01-01 00:00:00")            # the job is recent (inside 30 days); the usage row is before the reset point
        team.set_limit(self.conn, "lan@x", 1.0)
        bar = money_reset.user_bar(self.conn, " Lan@X ")
        self.assertEqual((bar["email"], bar["limit"], bar["since"]), ("lan@x", 1.0, None))
        self.assertGreater(bar["month_usd"], 0)
        done = money_reset.reset(self.conn, OWNER, ["user"], "tháng mới", email="lan@x")
        self.assertEqual(done["user"]["before_usd"], bar["month_usd"])
        self.assertEqual(done["user"]["after_usd"], 0.0)
        self.assertEqual(money_reset.user_bar(self.conn, "lan@x")["limit"], 1.0)         # the personal limit is untouched (warning only)
        with self.assertRaises(auth.AuthError):                                          # no non-Owner path to the same effect
            money_reset.reset(self.conn, MEMBER, ["user"], "x", email="lan@x")
        with self.assertRaises(ValueError):
            money_reset.reset(self.conn, OWNER, ["user"], "  ", email="lan@x")

    def test_audit_row_written(self):
        money_reset.reset(self.conn, auth.Identity("boss@x", "B", "owner", []), ["trial"], "ghi vết")
        row = self.conn.execute("SELECT email, detail FROM audit_log WHERE action='reset_money'").fetchone()
        self.assertEqual(row["email"], "boss@x")
        self.assertIn("ghi vết", row["detail"])


if __name__ == "__main__":
    unittest.main()
