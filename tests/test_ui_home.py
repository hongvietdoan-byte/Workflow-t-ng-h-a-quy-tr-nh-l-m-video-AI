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


class SlimTests(unittest.TestCase):
    """Lượt tinh gọn 01/10 (QUY_TAC §5): chi tiết vào ⓘ / expander có nhãn; ngoài chỉ P1 + một dòng tóm tắt."""
    setUp = UiHomeTests.setUp
    _md = UiHomeTests._md
    _home = UiHomeTests._home

    @staticmethod
    def _in_info(at, text: str) -> bool:
        """True when some ⓘ popover holds markdown containing `text`."""
        return any(text in m.value for p in at.get("popover") for m in p.markdown)

    def test_project_card_is_slim_and_details_are_in_its_info(self):
        at = self._home()
        md = self._md(at)
        self.assertIn("home-sum", md)                                    # the ONE summary line
        self.assertNotIn('class="home-note"', md)                                # autopilot note no longer outside
        self.assertNotIn("Bước: ", md)                                   # the step pill is folded into the summary
        self.assertTrue(self._in_info(at, "Người tạo:"))
        for label in ("Người tạo:", "Tiến độ:", "Tiền:", "Chờ bạn:"):    # full details still there, inside the ⓘ
            self.assertIn(label, md)

    def test_scope_note_moved_into_info_beside_the_filters(self):
        at = self._home()
        self.assertTrue(self._in_info(at, "“Của tôi” = dự án bạn tạo"))
        self.assertIn("“Của tôi” = dự án bạn tạo", self._md(at))
        self.assertFalse(any("“Của tôi” = dự án bạn tạo" in c.value for c in at.caption))
        self.assertFalse(any("tổng chi các dự án đang hiện" in c.value for c in at.caption))

    def test_team_main_table_has_only_the_main_columns_rest_in_labelled_expander(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["step"] = "👥 Nhóm"
        at.run()
        self.assertFalse(at.exception, at.exception)
        md = self._md(at)
        main = [m.value for m in at.markdown if "Video (xong / gửi)" in m.value][0]
        for gone in ("Giây video", "Lỗi · Gen lại", "Gần nhất"):
            self.assertNotIn(gone, main)
            self.assertIn(gone, md)                                      # …but they still exist (in the expander)
        labels = {e.label: e for e in at.expander}
        self.assertTrue(any("Chi tiết từng người" in k for k in labels))
        self.assertTrue(any("Lịch sử hoạt động" in k for k in labels))
        self.assertTrue(all(not e.proto.expanded for e in at.expander))
        self.assertTrue(self._in_info(at, "Hạn mức chỉ để cảnh báo"))
        self.assertTrue(self._in_info(at, "quyền lẻ vẫn ở"))
        self.assertTrue(any(getattr(w, "key", None) == "team_new_email" for w in at.text_input))

    def test_monitor_details_are_in_closed_expanders_and_ok_state_is_one_line(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["step"] = "📊 Theo dõi"
        at.run()
        self.assertFalse(at.exception, at.exception)
        labels = [e.label for e in at.expander]
        for want in ("Tải theo loại job", "Hiệu quả workflow", "Giám sát từng khâu", "Sự kiện lỗi/cảnh báo", "Báo cáo chẩn đoán"):
            self.assertTrue(any(want in k for k in labels), want)
        self.assertTrue(all(not e.proto.expanded for e in at.expander))
        self.assertTrue(self._in_info(at, "AUTOPILOT_MAX_PARALLEL"))
        self.assertNotIn("AUTOPILOT_MAX_PARALLEL</small>", self._md(at))  # internal codes no longer under the stats
        self.assertFalse(any("PERF_MAX_ACTIVE" in c.value for c in at.caption))


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
