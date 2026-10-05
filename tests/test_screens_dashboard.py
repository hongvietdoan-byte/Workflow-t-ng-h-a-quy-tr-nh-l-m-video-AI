"""Đợt 3 (01/10): ⌂ Tất cả dự án, 👥 Nhóm, 📥 Việc cần bạn, 🎚 Mức tự động, 📎 Đầu vào & tham chiếu (AppTest + phần logic thuần)."""
import os
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import automation, team
from core.db import connect
from core.pipeline import Pipeline
from dashboard import home

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class HomeLogicTests(unittest.TestCase):
    def row(self, **kw):
        base = {"paused": False, "done": False, "needs_review": 0, "active": 0, "running_auto": False}
        base.update(kw)
        return base

    def test_status_order_of_importance(self):
        self.assertEqual(home.status_of(self.row(paused=True, needs_review=3), False), "pause")
        self.assertEqual(home.status_of(self.row(done=True), False), "done")
        self.assertEqual(home.status_of(self.row(needs_review=1, active=2), False), "wait")
        self.assertEqual(home.status_of(self.row(), True), "wait")
        self.assertEqual(home.status_of(self.row(active=1), False), "run")
        self.assertEqual(home.status_of(self.row(), False), "idle")

    def test_filters_and_sorts(self):
        rs = [{"id": 1, "name": "A Kenta", "creator": "viet", "mine": True, "status": "done", "screen": "deliver", "warn": False, "spent": 5.0},
              {"id": 2, "name": "B Kelly", "creator": "lan", "mine": False, "status": "wait", "screen": "video", "warn": True, "spent": 2.0},
              {"id": 3, "name": "C Maxim", "creator": "viet", "mine": True, "status": "run", "screen": "video", "warn": False, "spent": 9.0}]
        f = lambda **k: [r["id"] for r in home.apply_filters(rs, **{"scope": "team", "q": "", "status": "", "step": "", "creator": "", "warn": False, **k})]
        self.assertEqual(f(), [1, 2, 3])
        self.assertEqual(f(scope="mine"), [1, 3])
        self.assertEqual(f(q="kelly"), [2])
        self.assertEqual(f(status="run"), [3])
        self.assertEqual(f(step="video"), [2, 3])
        self.assertEqual(f(creator="lan"), [2])
        self.assertEqual(f(warn=True), [2])
        self.assertEqual([r["id"] for r in home._sort(rs, "wait")], [2, 3, 1])
        self.assertEqual([r["id"] for r in home._sort(rs, "cost")], [3, 1, 2])
        self.assertEqual([r["id"] for r in home._sort(rs, "new")], [3, 2, 1])


class ScreensTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                           "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku")})
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("PIPELINE_DB", "PIPELINE_DATA", "KNOWLEDGE_USER_DIR")])
        self.p = Pipeline(connect(self.db))
        self.a = self.p.create_project("Dự án A")
        self.b = self.p.create_project("Dự án B")
        from core import qc_policy
        qc_policy.apply(self.p, self.a, "balanced")             # what "➕ Dự án mới" does
        sid = self.p.create_scene(self.b, 1, "s")
        jid = self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (jid,))
        self.p.conn.commit()

    def test_home_lists_projects_and_opens_one_on_the_right_screen(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["step"] = "⌂ Tất cả dự án"
        at.run()
        self.assertFalse(at.exception, at.exception)
        keys = [b.key for b in at.button]
        self.assertIn(f"home_open_{self.a}", keys)
        self.assertIn(f"home_open_{self.b}", keys)
        at.button(key=f"home_open_{self.b}").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.radio(key="step").value, "Storyboard")           # project B has a scene with no picture yet → Storyboard
        self.assertEqual(at.selectbox(key="global_pid").value, self.b)

    def test_inbox_counts_what_waits_and_opens_the_project(self):
        at = AppTest.from_file(APP, default_timeout=40).run()
        self.assertFalse(at.exception, at.exception)
        labels = [x.proto.popover.label for x in at.get("popover")]
        self.assertTrue(any(l.startswith("📥 Việc cần bạn (") and "(0)" not in l for l in labels), labels)
        inb = [b for b in at.button if b.key and b.key.startswith("inb_")]
        self.assertTrue(inb)

    def test_level_bar_changes_the_three_settings_and_reads_back(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["global_pid"] = self.a
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.radio(key=f"level_{self.a}").value, "main")
        at.radio(key=f"level_{self.a}").set_value("all").run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(automation.current(Pipeline(connect(self.db)), self.a), "all")
        self.assertEqual(at.radio(key=f"level_{self.a}").value, "all")

    def test_team_screen_renders_for_the_owner(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["step"] = "👥 Nhóm"
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(any("Nhóm" in m.value for m in at.markdown))
        self.assertTrue(len(at.dataframe) >= 1)

    def test_script_screen_has_the_inputs_and_references_panel(self):
        at = AppTest.from_file(APP, default_timeout=40)
        at.session_state["global_pid"] = self.a
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(any(b.key == f"ref_go_{self.a}" for b in at.button))             # S14.28: no form before the scene analysis…
        self.assertTrue(any("Gắn ảnh tham chiếu sau khi phân tích cảnh" in (c.value or "") for c in at.caption)
                        or any("Gắn ảnh tham chiếu sau khi phân tích cảnh" in (getattr(e.proto, "body", "") or "") for e in at.get("html")))  # …one hint line
        self.assertTrue(any(b.key.startswith("coming_") and b.disabled for b in at.button))   # video-ref / dance / trend: "sắp có"


if __name__ == "__main__":
    unittest.main()


class LevelAndTabsTests(unittest.TestCase):
    """Rà soát đợt 3 (agent): the 🎚 bar must not be undone by the older controls that share its settings, and the Motion jumps must open the Motion tab."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                           "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku")})
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("PIPELINE_DB", "PIPELINE_DATA", "KNOWLEDGE_USER_DIR")])
        from core import qc_policy
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("có cảnh")
        self.p.create_scene(self.pid, 1, "cảnh 1")                 # a scene → the Step-1 gate checkboxes render too
        qc_policy.apply(self.p, self.pid, "balanced")

    def _db(self):
        return Pipeline(connect(self.db))

    def test_switching_between_human_and_auto_survives_the_older_widgets(self):
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["global_pid"] = self.pid
        at.run()
        self.assertFalse(at.exception, at.exception)
        at.radio(key=f"level_{self.pid}").set_value("auto").run()
        self.assertFalse(at.exception, at.exception)
        p = self._db()
        self.assertEqual(automation.current(p, self.pid), "auto")
        self.assertEqual(p.project(self.pid)["operating_mode"], "auto")
        at.radio(key=f"level_{self.pid}").set_value("all").run()
        self.assertFalse(at.exception, at.exception)
        p = self._db()
        self.assertEqual(automation.current(p, self.pid), "all")
        self.assertEqual(p.project(self.pid)["operating_mode"], "human_qc")
        at.radio(key=f"level_{self.pid}").set_value("main").run()
        self.assertEqual(automation.current(self._db(), self.pid), "main")

    def test_level_is_read_back_from_the_person_choice_while_the_run_holds_the_project(self):
        from core import autopilot
        automation.apply(self.p, self.pid, "all")
        autopilot.start(self.p, self.pid)                          # the run switches to automatic QC and keeps the person's mode
        self.assertEqual(self.p.project(self.pid)["operating_mode"], "auto")
        self.assertEqual(automation.current(self.p, self.pid), "all")
        with self.assertRaises(ValueError):
            automation.apply(self.p, self.pid, "auto")

    def test_motion_jump_opens_the_motion_tab(self):
        from dashboard import common as C
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["global_pid"] = self.pid
        at.session_state["step"] = "Storyboard"
        at.session_state["sb_tab"] = C.SB_TABS[1]
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["sb_tab"], C.SB_TABS[1])
        at2 = AppTest.from_file(APP, default_timeout=60)
        at2.query_params["step"] = "3"                             # old deep link to Motion & giọng
        at2.run()
        self.assertFalse(at2.exception, at2.exception)
        self.assertEqual(at2.radio(key="step").value, "Storyboard")
        self.assertEqual(at2.session_state["sb_tab"], C.SB_TABS[1])
