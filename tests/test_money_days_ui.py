"""S14.6 Gói K giao diện (UI v2, AppTest): thẻ 💵 → 📅 mức dùng theo ngày, chọn ngày ra từng dòng sổ chi, khối mở đợt mới chỉ Owner."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import budget, budget_rounds
from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
MODEL = "gpt-image-2.5-sunburst"


class MoneyDaysUiTests(unittest.TestCase):
    AUTH = "off"

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.db = os.path.join(tmp, "m.sqlite")
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(tmp, "projects"),
                                           "KNOWLEDGE_USER_DIR": os.path.join(tmp, "ku"), "DASHBOARD_AUTH": self.AUTH,
                                           "FEATURE_UI_V2": "1", "FEATURE_SETTINGS_FILE": os.path.join(tmp, "fs.json")})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("Dự án tiền")
        budget.save(self.p.conn, enabled=True, usd=10.0, since="2026-10-01 00:00:00")
        for at, n in (("2026-10-02 03:00:00", 2), ("2026-10-03 03:00:00", 1)):
            self.p.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at, stage)"
                                " VALUES (?,?,?,?,?,?,?,?,?,?)", (None, self.pid, "image", "deepix", MODEL, "1152x2048", n, "image", at,
                                                                  "storyboard"))
        self.p.conn.commit()

    def open_days(self):
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["global_pid"] = self.pid
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertIn("mc_days", [b.key for b in at.button])
        at.button(key="mc_days").click().run()
        self.assertFalse(at.exception, at.exception)
        return at

    @staticmethod
    def text(at):
        return " ".join(m.value for m in at.markdown)

    def test_money_card_opens_the_daily_table_and_a_day_shows_its_rows(self):
        at = self.open_days()
        self.assertIn("md_round", [s.key for s in at.selectbox])
        page = self.text(at)
        self.assertIn("2026-10-02", page)
        self.assertIn("2026-10-03", page)
        self.assertIn("$0.10 · 2 lượt", page)                       # 2 pictures × 0.052
        at.selectbox(key="md_day").set_value("2026-10-02").run()
        self.assertFalse(at.exception, at.exception)
        page = self.text(at)
        self.assertIn("10:00:00", page)                              # 03:00 UTC → 10:00 Việt Nam
        self.assertIn("storyboard", page)
        self.assertIn(f"#{self.pid} Dự án tiền", page)

    def test_owner_opens_a_new_round_with_reason_and_confirmation(self):
        at = self.open_days()
        self.assertTrue(at.button(key="md_new_go").disabled)                  # no name / reason → cannot ask
        at.text_input(key="md_new_name").set_value("Đợt 04/10")
        at.text_input(key="md_new_why").set_value("chính sách tiền mới")
        at.run()
        at.button(key="md_new_go").click().run()
        self.assertIn("md_new_go_yes", [b.key for b in at.button])
        conn = connect(self.db)
        self.assertIsNone(budget_rounds.current(conn)["id"])                  # nothing done before the yes
        at.button(key="md_new_go_yes").click().run()
        self.assertFalse(at.exception, at.exception)
        conn = connect(self.db)
        names = [r["name"] for r in budget_rounds.history(conn)]
        self.assertEqual(names, ["Đợt 04/10", "Đợt từ 01/10/2026"])
        self.assertGreater(budget.get(conn)["since"], "2026-10-03 03:00:00")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], 2)

    def test_confirmation_lists_project_and_people_bars_switched_on_by_default(self):
        from core import auth, money_reset, project_budget, team
        project_budget.set_planned(self.p.conn, self.pid, 12.0)
        auth.add_user(self.p.conn, auth.Identity("boss@x", "Boss", "owner", []), "lan@x.vn", ["knowledge"])
        at = self.open_days()
        self.assertTrue(at.checkbox(key="md_new_projects").value)
        self.assertTrue(at.checkbox(key="md_new_users").value)
        at.number_input(key=f"md_new_plan_{self.pid}").set_value(20.0)
        at.text_input(key="md_new_name").set_value("Đợt 04/10")
        at.text_input(key="md_new_why").set_value("chính sách tiền mới")
        at.run()
        at.button(key="md_new_go").click().run()
        question = " ".join(w.value for w in at.warning)
        for part in ("Đợt thử", "Claude API", f"dự án #{self.pid} ($20.00)", "lan@x.vn"):
            self.assertIn(part, question)
        at.button(key="md_new_go_yes").click().run()
        self.assertFalse(at.exception, at.exception)
        conn = connect(self.db)
        self.assertEqual(project_budget.planned(conn, self.pid), 20.0)
        self.assertIsNotNone(money_reset.last(conn, "project", self.pid))
        self.assertIsNotNone(team.user_baseline(conn, "lan@x.vn"))

    def test_open_flag_without_rights_draws_no_dialog(self):
        def page():
            import streamlit as st
            from dashboard.design.screens import money_days
            st.session_state[money_days.FLAG] = True
            money_days.dialog_if_open({"email": "lan@x.vn", "role": "member", "perms": []})
        at = AppTest.from_function(page, default_timeout=60).run()
        self.assertFalse(at.exception, at.exception)
        self.assertNotIn("md_round", [s.key for s in at.selectbox])

    def test_non_owner_sees_the_table_but_not_the_new_round_block(self):
        def page():
            import os
            from core.db import connect as c
            from dashboard.design.screens import money_days
            money_days.body(c(os.environ["PIPELINE_DB"]), {"email": "lan@x.vn", "role": "member", "perms": ["monitor"]})
        at = AppTest.from_function(page, default_timeout=60).run()
        self.assertFalse(at.exception, at.exception)
        self.assertIn("md_round", [s.key for s in at.selectbox])
        self.assertNotIn("md_new_go", [b.key for b in at.button])
        self.assertNotIn("md_new_why", [t.key for t in at.text_input])


class MemberMoneyDaysTests(unittest.TestCase):
    """Bảng ghi sổ chi MỌI dự án → chỉ người có quyền tiền (settings) / theo dõi (monitor); thành viên mới không thấy nút."""
    setUp = MoneyDaysUiTests.setUp
    AUTH = "on"

    def test_new_member_without_money_rights_has_no_daily_button(self):
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()
        at.text_input(key="login_email").set_value("lan@garena.vn")
        next(b for b in at.button if b.key == "login_btn").click().run()
        self.assertEqual(at.session_state["identity"]["role"], "member")
        at.session_state["global_pid"] = self.pid
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertNotIn("mc_days", [b.key for b in at.button])
        self.assertNotIn("md_new_go", [b.key for b in at.button])


if __name__ == "__main__":
    unittest.main()
