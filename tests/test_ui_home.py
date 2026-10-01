"""UI v2 lane D (S13): ⌂ Tất cả dự án card grid, 👥 Nhóm HTML table, 📊 Theo dõi cards — with the flag ui_v2 ON (FEATURE_UI_V2=1)."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class UiHomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        env = {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"), "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku"),
               "FEATURE_UI_V2": "1"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Pipeline(connect(self.db))
        self.a = self.p.create_project("Dự án A")
        self.b = self.p.create_project("Dự án B có tên rất dài để thử cắt chữ trong thẻ dự án của lưới ba cột")
        from core import qc_policy
        qc_policy.apply(self.p, self.a, "balanced")
        sid = self.p.create_scene(self.b, 1, "s")
        jid = self.p.create_job(sid, "video_gen")
        self.p.actor = "Viet"
        self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (jid,))
        self.p.conn.commit()

    def _md(self, at) -> str:
        return "\n".join(m.value for m in at.markdown)

    def _home(self) -> AppTest:
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["step"] = "⌂ Tất cả dự án"
        at.run()
        self.assertFalse(at.exception, at.exception)
        return at

    def test_flag_is_on(self):
        from dashboard import ui
        self.assertTrue(ui.v2_on())

    def test_home_grid_has_cards_hero_and_old_keys(self):
        at = self._home()
        md = self._md(at)
        for k in (f"home_open_{self.a}", f"home_open_{self.b}"):
            self.assertIn(k, [b.key for b in at.button])
        for k in ("home_q", "home_sort"):
            self.assertTrue(any(getattr(w, "key", None) == k for w in list(at.text_input) + list(at.selectbox) + list(at.radio)), k)
        self.assertIn("v2-hero-title", md)
        self.assertIn("Số dự án", md)
        self.assertIn("Chờ bạn", md)
        self.assertIn("v2-meter", md)
        self.assertIn("home-name", md)
        self.assertIn("Dự án B có tên rất dài", md)

    def test_the_waiting_project_gets_the_primary_button_the_other_secondary(self):
        at = self._home()
        self.assertEqual(at.button(key=f"home_open_{self.b}").proto.type, "primary")
        self.assertEqual(at.button(key=f"home_open_{self.a}").proto.type, "secondary")

    def test_card_open_button_navigates_to_the_right_screen(self):
        at = self._home()
        at.button(key=f"home_open_{self.b}").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.radio(key="step").value, "Storyboard")
        self.assertEqual(at.selectbox(key="global_pid").value, self.b)

    def test_search_filter_still_works(self):
        at = self._home()
        at.text_input(key="home_q").set_value("rất dài").run()
        self.assertFalse(at.exception, at.exception)
        keys = [b.key for b in at.button]
        self.assertIn(f"home_open_{self.b}", keys)
        self.assertNotIn(f"home_open_{self.a}", keys)
        self.assertTrue(any("Hiện **1** / 2" in c.value for c in at.caption))

    def test_status_filter_in_popover(self):
        at = self._home()
        at.radio(key="home_status").set_value("wait").run()
        self.assertFalse(at.exception, at.exception)
        keys = [b.key for b in at.button]
        self.assertIn(f"home_open_{self.b}", keys)
        self.assertNotIn(f"home_open_{self.a}", keys)

    def test_team_table_renders_for_the_owner_with_editor_keys(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["step"] = "👥 Nhóm"
        at.run()
        self.assertFalse(at.exception, at.exception)
        md = self._md(at)
        self.assertIn("v2-table", md)
        self.assertIn("team-table", md)
        self.assertIn("Viet", md)
        self.assertIn("Số người", md)
        self.assertEqual(len(at.dataframe), 0)                          # no st.dataframe on this screen any more
        self.assertTrue(any(getattr(w, "key", None) == "team_new_email" for w in at.text_input))
        self.assertTrue(any(b.key == "team_new_go" for b in at.button))

    def test_monitor_renders_cards_and_keeps_controls(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["step"] = "📊 Theo dõi"
        at.run()
        self.assertFalse(at.exception, at.exception)
        keys = [b.key for b in at.button] + [getattr(d, "key", None) for d in at.get("download_button")]
        self.assertIn("perf_refresh", keys)
        self.assertIn("diag_dl", keys)
        md = self._md(at)
        self.assertIn("mon-table", md)
        self.assertIn("v2-pill", md)


class FlagOffTests(unittest.TestCase):
    def test_flag_off_keeps_the_old_rows(self):
        tmp = tempfile.mkdtemp()
        env = {"PIPELINE_DB": os.path.join(tmp, "m.sqlite"), "PIPELINE_DATA": os.path.join(tmp, "projects"), "FEATURE_UI_V2": "0"}
        with mock.patch.dict(os.environ, env):
            p = Pipeline(connect(env["PIPELINE_DB"]))
            pid = p.create_project("Cũ")
            at = AppTest.from_file(APP, default_timeout=40)
            at.session_state["step"] = "⌂ Tất cả dự án"
            at.run()
            self.assertFalse(at.exception, at.exception)
            self.assertIn(f"home_open_{pid}", [b.key for b in at.button])
            self.assertNotIn("home-name", "\n".join(m.value for m in at.markdown))


if __name__ == "__main__":
    unittest.main()
