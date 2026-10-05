"""S14.39 — bảng 💵 gọn: câu tóm tắt không vỡ định dạng ($ lẻ bị Streamlit đọc thành công thức), MỘT nút đặt lại 2 thanh."""
import os
import re
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import auth, budget, budget_rounds, money_reset, project_budget
from core.db import connect
from core.pipeline import Pipeline
from tests.test_ui_shell import APP, ShellBase

OWNER = {"email": "o@x", "role": "owner"}
UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")


class SummaryText(unittest.TestCase):
    def summary(self):
        p = Pipeline(connect(os.path.join(tempfile.mkdtemp(), "m.sqlite")))
        pid = p.create_project("x")
        run = {"images": 1.5, "videos": 2.25, "llm": 0.3, "unknown": []}
        with mock.patch("core.cost.estimate_run", return_value=run):
            return project_budget.cost_summary(p, pid)

    def test_markdown_form_has_no_bare_dollar_and_no_backtick(self):
        s = self.summary()
        self.assertNotRegex(s["md"], UNESCAPED_DOLLAR)          # `$a ... $b` would be drawn as a formula (the 05/10 screenshot)
        self.assertNotIn("`", s["md"] + s["line"])
        self.assertIn("Đã chi", s["md"])

    def test_one_clean_line_with_the_three_numbers(self):
        s = self.summary()
        self.assertEqual(s["line"], f"Đã chi ${s['spent']:.2f} · còn lại ≈ ${s['remaining']:.2f} · tổng ≈ ${s['total']:.2f}")
        self.assertNotIn("Ảnh", s["line"])                      # the per-stage detail lives in the fold

    def test_text_is_unchanged_for_the_gates(self):
        self.assertIn("Đã chi + ước tính phần còn lại", self.summary()["text"])


class ResetTwoBars(unittest.TestCase):
    def setUp(self):
        self.conn = connect(os.path.join(tempfile.mkdtemp(), "m.sqlite"))
        budget.save(self.conn, enabled=True, usd=10.0, since="2026-09-30 00:00:00", llm_usd=5.0, llm_since="2026-09-30 00:00:00")

    def test_moves_both_marks_keeps_planned_and_writes_audit(self):
        out = budget_rounds.reset_two(self.conn, OWNER)
        b = budget.get(self.conn)
        self.assertGreater(b["since"], "2026-09-30 00:00:00")
        self.assertGreater(b["llm_since"], "2026-09-30 00:00:00")
        self.assertEqual((b["usd"], b["llm_usd"]), (10.0, 5.0))             # planned amounts are kept
        self.assertTrue(b["enabled"])
        self.assertEqual(out["opened"]["planned_usd"], 10.0)
        self.assertEqual(out["opened"]["started_at"], b["since"])           # the round starts at the bar's mark
        self.assertEqual(money_reset.last(self.conn, "trial")["why"], budget_rounds.DEFAULT_RESET_WHY)
        self.assertEqual(money_reset.last(self.conn, "claude")["why"], budget_rounds.DEFAULT_RESET_WHY)
        actions = [a["action"] for a in auth.recent_audit(self.conn)]
        self.assertIn("budget_round", actions)
        self.assertIn("reset_money", actions)

    def test_ledger_is_untouched_and_old_round_is_closed_with_summary(self):
        before = self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
        out = budget_rounds.reset_two(self.conn, OWNER, "nạp thêm tiền")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], before)
        self.assertTrue(out["closed"]["ended_at"])
        self.assertIn("total_usd", out["closed"]["summary"])
        self.assertEqual(money_reset.last(self.conn, "trial")["why"], "nạp thêm tiền")

    def test_non_owner_is_refused_and_nothing_changes(self):
        with self.assertRaises(auth.AuthError):
            budget_rounds.reset_two(self.conn, {"email": "m@x", "role": "member"})
        self.assertEqual(budget.get(self.conn)["since"], "2026-09-30 00:00:00")
        self.assertIsNone(money_reset.last(self.conn, "trial"))


class CardUi(ShellBase):
    def test_the_old_ticks_are_gone_and_one_button_resets_both_bars(self):
        budget.save(self.p.conn, enabled=True, usd=10.0, since="2026-09-30 00:00:00", llm_usd=5.0, llm_since="2026-09-30 00:00:00")
        at = self.run_app()
        self.assertFalse(at.exception, at.exception)
        keys = [c.key for c in at.checkbox]
        self.assertNotIn("shell-mr-trial", keys)       # root cause of "cannot tick": it was disabled=True (S14.6) — now removed
        self.assertFalse([c for c in at.checkbox if c.proto.disabled and (c.key or "").startswith("shell-mr")])
        self.assertIn("shell_mr_two", [b.key for b in at.button])
        at.button(key="shell_mr_two").click().run()                                     # step 1: ask
        self.assertIn("shell_mr_two_yes", [b.key for b in at.button])
        self.assertIsNone(money_reset.last(connect(self.db), "trial"))
        at.button(key="shell_mr_two_yes").click().run()                                 # step 2: confirm
        self.assertFalse(at.exception, at.exception)
        conn = connect(self.db)
        self.assertEqual(money_reset.last(conn, "trial")["why"], budget_rounds.DEFAULT_RESET_WHY)
        self.assertGreater(budget.get(conn)["llm_since"], "2026-09-30 00:00:00")

    def test_card_has_no_bare_dollar_pair_in_markdown(self):
        budget.save(self.p.conn, enabled=True, usd=10.0, since="2026-09-30 00:00:00", llm_usd=5.0, llm_since="2026-09-30 00:00:00")
        run = {"images": 1.5, "videos": 2.25, "llm": 0.3, "unknown": []}
        with mock.patch("core.cost.estimate_run", return_value=run):
            at = self.run_app()
        self.assertFalse(at.exception, at.exception)
        bad = [m.value for m in at.markdown if UNESCAPED_DOLLAR.search(m.value)]
        self.assertEqual(bad, [])

    def test_summary_is_one_line_with_details_in_a_fold(self):
        run = {"images": 1.5, "videos": 2.25, "llm": 0.3, "unknown": []}
        with mock.patch("core.cost.estimate_run", return_value=run):
            at = self.run_app()
        self.assertTrue(any("đã chi" in c.value.lower() and "tổng ≈" in c.value for c in at.caption) or
                        any("tổng ≈" in m.value for m in at.markdown))
        self.assertTrue(any(x.label == "Chi tiết" for x in at.expander), [x.label for x in at.expander])


class CardUiMember(ShellBase):
    AUTH = "on"

    def test_member_sees_no_active_reset_button(self):
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()
        at.text_input(key="login_email").set_value("lan@garena.vn")
        next(b for b in at.button if b.key == "login_btn").click().run()
        self.assertEqual(at.session_state["identity"]["role"], "member")
        two = [b for b in at.button if b.key == "shell_mr_two"]
        self.assertTrue(not two or two[0].proto.disabled)


if __name__ == "__main__":
    unittest.main()
