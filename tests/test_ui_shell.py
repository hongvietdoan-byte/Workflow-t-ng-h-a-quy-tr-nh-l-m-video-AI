"""UI v2 khung ứng dụng (S13 nhánh B): thanh trên, hero dự án, thẻ 💵 với khối "Đặt lại thanh tiền" chỉ Owner (AppTest, cờ ui_v2 bật)."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import budget, money_reset
from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class ShellBase(unittest.TestCase):
    AUTH = "off"
    V2 = "1"

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.db = os.path.join(tmp, "m.sqlite")
        self.env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(tmp, "projects"),
                                                "KNOWLEDGE_USER_DIR": os.path.join(tmp, "ku"), "DASHBOARD_AUTH": self.AUTH,
                                                "FEATURE_UI_V2": self.V2, "FEATURE_SETTINGS_FILE": os.path.join(tmp, "fs.json")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("Dự án thử khung")

    def run_app(self, **state):
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["global_pid"] = self.pid
        for k, v in state.items():
            at.session_state[k] = v
        return at.run()

    @staticmethod
    def html_text(at):
        return " ".join(str(getattr(e.proto, "body", "")) for e in at.get("html")) + " ".join(m.value for m in at.markdown)


class HeroTests(ShellBase):
    def test_hero_strip_on_a_project_screen_not_on_home(self):
        at = self.run_app()
        self.assertFalse(at.exception, at.exception)
        self.assertIn("Dự án thử khung", self.html_text(at))
        self.assertTrue(any("v2-hero-title" in str(e.proto.body) for e in at.get("html")))
        self.assertIn(f"level_{self.pid}", [r.key for r in at.radio])              # 🎚 keeps its key
        at = self.run_app(step="⌂ Tất cả dự án")
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(any("v2-hero-title" in str(e.proto.body) for e in at.get("html")))
        self.assertNotIn(f"level_{self.pid}", [r.key for r in at.radio])

    def test_bar_keeps_every_old_control_reachable(self):
        at = self.run_app()
        keys = [b.key for b in at.button]
        for k in ("btn_pause", "btn_cancel", "settings_features", "mc_budget"):
            self.assertIn(k, keys)
        labels = [x.proto.popover.label for x in at.get("popover")]
        for part in ("Dự án mới", "Việc cần bạn", "Tiền", "Thêm", "Cài đặt"):
            self.assertTrue(any(part in l for l in labels), (part, labels))
        self.assertEqual(at.radio(key="step").value, "Kịch bản")

    def test_paused_project_shows_resume_in_the_bar(self):
        self.p.set_paused(self.pid, True)
        at = self.run_app()
        self.assertIn("btn_resume", [b.key for b in at.button])
        self.assertNotIn("btn_pause", [b.key for b in at.button])

    def test_flag_off_has_no_hero_and_the_old_bar(self):
        with mock.patch.dict(os.environ, {"FEATURE_UI_V2": "0"}):
            at = self.run_app()
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(any("v2-hero-title" in str(e.proto.body) for e in at.get("html")))
        labels = [x.proto.popover.label for x in at.get("popover")]
        self.assertIn("⚙", labels)
        self.assertFalse(any("Thêm" in l for l in labels))


class MoneyResetTests(ShellBase):
    def seed_spend(self):
        sid = self.p.create_scene(self.pid, 1, "s")
        job = self.p.create_job(sid, "image_gen")
        self.p.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                            " VALUES (?,?,?,?,?,?,?,?,?)", (job, self.pid, "image", "deepix", "gpt-image-2.5-sunburst", "1152x2048", 3, "image",
                                                             "2026-10-01 00:00:00"))
        self.p.conn.commit()

    def test_owner_sees_block_and_reset_moves_the_baseline_without_deleting_rows(self):
        budget.save(self.p.conn, enabled=True, usd=10.0, since="2026-09-30 00:00:00")
        self.seed_spend()
        rows = self.p.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
        self.assertEqual(budget.spent(self.p.conn, since=budget.get(self.p.conn)["since"])["images"], 3)
        at = self.run_app()
        self.assertFalse(at.exception, at.exception)
        self.assertIn("shell-mr-trial", [c.key for c in at.checkbox])
        at.checkbox(key="shell-mr-trial").set_value(True)
        at.text_input(key="shell-mr-why").set_value("bắt đầu đợt thử mới")
        at.run()
        at.button(key="shell_mr_go").click().run()                           # step 1: ask
        self.assertIn("shell_mr_go_yes", [b.key for b in at.button])
        self.assertIsNone(money_reset.last(connect(self.db), "trial"))        # nothing done before the yes
        at.button(key="shell_mr_go_yes").click().run()                       # step 2: confirm
        self.assertFalse(at.exception, at.exception)
        conn = connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0], rows)     # the ledger is untouched
        last = money_reset.last(conn, "trial")
        self.assertEqual(last["why"], "bắt đầu đợt thử mới")
        self.assertEqual(budget.spent(conn, since=budget.get(conn)["since"])["images"], 0)          # the bar counts from now

    def test_reason_is_required(self):
        at = self.run_app()
        at.checkbox(key="shell-mr-trial").set_value(True).run()
        self.assertTrue(at.button(key="shell_mr_go").disabled)


class MemberSignInTests(ShellBase):
    AUTH = "on"

    def test_signed_in_company_member_has_no_reset_block(self):
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()
        at.text_input(key="login_email").set_value("lan@garena.vn")
        next(b for b in at.button if b.key == "login_btn").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["identity"]["role"], "member")
        self.assertNotIn("shell-mr-trial", [c.key for c in at.checkbox])


if __name__ == "__main__":
    unittest.main()
