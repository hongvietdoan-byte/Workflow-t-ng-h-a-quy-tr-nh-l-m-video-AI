"""Màn 👥 Nhóm: nút "↺ Đặt lại" thanh tiền theo người (chỉ Owner, lý do bắt buộc, xác nhận, số trước → sau). AppTest, cả giao diện cũ và v2."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import auth, money_reset, team
from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
BOSS = auth.Identity("boss@x", "Boss", "owner", [])
MODEL = "gpt-image-2.5-sunburst"


class TeamMoneyResetTests(unittest.TestCase):
    V2 = "0"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                                           "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku"), "FEATURE_UI_V2": self.V2})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect(self.db))
        self.conn = self.p.conn
        pid = self.p.create_project("t", created_by="lan@x.vn")
        sid = self.p.create_scene(pid, 1, "s1")
        job = self.p.create_job(sid, "image_gen")
        self.conn.execute("UPDATE jobs SET created_by='lan@x.vn' WHERE id=?", (job,))
        self.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                          " VALUES (?,?,?,?,?,?,?,?,?)", (job, pid, "image", "deepix", MODEL, "1152x2048", 5, "image", "2000-01-01 00:00:00"))
        self.conn.commit()
        auth.add_user(self.conn, BOSS, "lan@x.vn", ["knowledge"])
        team.set_limit(self.conn, "lan@x.vn", 1.0)
        self.before = money_reset.user_bar(self.conn, "lan@x.vn")["month_usd"]
        self.assertGreater(self.before, 0)

    def run_team(self, identity=None):
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["step"] = "👥 Nhóm"
        if identity:
            at.session_state["identity"] = identity
        at.run()
        self.assertFalse(at.exception, at.exception)
        return at

    def test_owner_resets_one_person_with_reason_and_confirmation(self):
        at = self.run_team()
        self.assertIn("team_mr_lan@x.vn", [b.key for b in at.button])
        at.button(key="team_mr_lan@x.vn").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.text_input(key="team_mr_why_lan@x.vn").value, "")
        self.assertTrue(at.button(key="team_mr_go_lan@x.vn").disabled)                      # no reason -> cannot even ask
        at.text_input(key="team_mr_why_lan@x.vn").set_value("sang tháng mới").run()
        at.button(key="team_mr_go_lan@x.vn").click().run()
        self.assertIn("team_mr_go_lan@x.vn_yes", [b.key for b in at.button])                 # the yes/no question; nothing reset yet
        self.assertIsNone(team.user_baseline(self.conn, "lan@x.vn"))
        self.assertTrue(any(f"{self.before:.2f} USD → 0.00 USD" in w.value for w in at.warning))
        at.button(key="team_mr_go_lan@x.vn_yes").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertIsNotNone(team.user_baseline(self.conn, "lan@x.vn"))
        self.assertEqual(money_reset.last(self.conn, "user", "lan@x.vn")["why"], "sang tháng mới")
        self.assertTrue(any(f"{self.before:.2f} USD → 0.00 USD" in s.value for s in at.success))         # before -> after shown
        self.assertEqual(money_reset.user_bar(self.conn, "lan@x.vn")["limit"], 1.0)                      # limit untouched
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], 1)     # ledger untouched
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='reset_money'").fetchone()[0], 1)

    def test_answering_no_changes_nothing(self):
        at = self.run_team()
        at.button(key="team_mr_lan@x.vn").click().run()
        at.text_input(key="team_mr_why_lan@x.vn").set_value("thử").run()
        at.button(key="team_mr_go_lan@x.vn").click().run()
        at.button(key="team_mr_go_lan@x.vn_no").click().run()
        self.assertIsNone(team.user_baseline(self.conn, "lan@x.vn"))
        self.assertIsNone(money_reset.last(self.conn, "user", "lan@x.vn"))

    def test_monitor_only_person_sees_no_reset_button(self):
        def page():                                      # the block as a non-Owner with the "monitor" permission would reach it
            from core.db import connect as c
            from core.pipeline import Pipeline as P
            from dashboard import team_screen
            pipe = P(c())
            team_screen.user_reset_block(pipe, {"email": "mon@x.vn", "role": "member", "perms": ["monitor"]},
                                         team_screen.people_rows(pipe, None), False)
        at = AppTest.from_function(page, default_timeout=60).run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(len(at.button), 0)
        self.assertEqual(len(at.expander), 0)
        with self.assertRaises(auth.AuthError):          # and the core refuses it anyway
            money_reset.reset(self.conn, {"email": "mon@x.vn", "role": "member", "perms": ["monitor"]}, ["user"], "x", email="lan@x.vn")
        self.assertIsNone(team.user_baseline(self.conn, "lan@x.vn"))


class TeamMoneyResetV2Tests(TeamMoneyResetTests):
    V2 = "1"


if __name__ == "__main__":
    unittest.main()
