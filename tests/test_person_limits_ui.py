"""S14.18 trên Dashboard thật (AppTest, đăng nhập BẬT; giao diện v2 và giao diện cũ): ➕ Dự án mới bị chặn có số liệu → GIỮ / BỎ; dự án thứ 3
trong ngày → gửi yêu cầu → Owner duyệt ở 👥 Nhóm → tạo được; ⚙ 📦 cất dự án dở thứ 2 → lựa chọn; Kho dự án đã xong tách riêng."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import archive, person_limits as PL
from core.db import connect
from core.pipeline import Pipeline
from tests.test_access import CREATOR, OWNER, make_world

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class Base(unittest.TestCase):
    V2 = "1"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        env = {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"), "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku"),
               "FEATURE_UI_V2": self.V2, "DASHBOARD_AUTH": "on"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.conn, self.pid, _, _ = make_world(connect(self.db))    # CREATOR has 1 unfinished project (made by the system: not counted today)

    def sign_in(self, email, step=None) -> AppTest:
        at = AppTest.from_file(APP, default_timeout=60)
        if step:
            at.query_params["step"] = step
        at.run()
        at.text_input(key="login_email").set_value(email)
        next(b for b in at.button if b.key == "login_btn").click().run()
        self.assertFalse(at.exception, at.exception)
        return at

    def create(self, at, name):
        at.text_input(key="new_name").set_value(name).run()
        at.button(key="new_project_go").click().run()
        self.assertFalse(at.exception, at.exception)
        return at

    def projects(self):
        return [r["name"] for r in self.conn.execute("SELECT name FROM projects WHERE created_by=? ORDER BY id", (CREATOR,))]

    def warnings(self, at) -> str:
        return "\n".join(w.value for w in at.warning)


class CreateFlow(Base):
    def test_open_limit_then_daily_request_then_owner_approves(self):
        at = self.sign_in(CREATOR, "1")
        self.create(at, "Thứ hai")
        self.assertEqual(self.projects(), ["dự án của chủ", "Thứ hai"])
        self.create(at, "Thứ ba")                                    # (a) 2 unfinished already
        self.assertEqual(len(self.projects()), 2)
        self.assertIn("2/2 dự án dở", self.warnings(at))
        keys = {b.key for b in at.button}
        self.assertIn(f"lim_keep_{self.pid}", keys)
        self.assertIn(f"lim_drop_{self.pid}", keys)
        at.button(key=f"lim_drop_{self.pid}").click().run()          # BỎ: put the first one away
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(archive.is_archived(Pipeline(connect(self.db)).project(self.pid)))
        self.create(at, "Thứ ba")                                    # made: 2nd of the day
        self.assertIn("Thứ ba", self.projects())
        second = self.conn.execute("SELECT id FROM projects WHERE name='Thứ hai'").fetchone()[0]
        third = self.conn.execute("SELECT id FROM projects WHERE name='Thứ ba'").fetchone()[0]
        for pid in (second, third):
            self.conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?, 'final', 'x', '{}', 'now')", (pid,))
        self.conn.commit()
        self.create(at, "Thứ tư")                                    # (b) 3rd of the day
        self.assertIn(f"Hôm nay bạn đã tạo 2/2 dự án: #{second}, #{third}", self.warnings(at))
        self.assertNotIn("Thứ tư", self.projects())
        at.text_input(key="lim_reason_daily").set_value("bản gấp cho sự kiện").run()
        at.button(key="lim_req_daily").click().run()
        self.assertFalse(at.exception, at.exception)
        rid = self.conn.execute("SELECT id FROM limit_requests WHERE status='pending'").fetchone()[0]

        boss = self.sign_in(OWNER, "team")
        self.assertIn(f"lim_ok_{rid}", {b.key for b in boss.button})
        boss.button(key=f"lim_ok_{rid}").click().run()
        self.assertFalse(boss.exception, boss.exception)
        self.assertEqual(self.conn.execute("SELECT status FROM limit_requests WHERE id=?", (rid,)).fetchone()[0], "approved")

        self.create(at, "Thứ tư")
        self.assertIn("Thứ tư", self.projects())

    def test_owner_rejects_and_nothing_is_made(self):
        p = Pipeline(self.conn)
        p.user = {"email": CREATOR, "role": "member"}
        for name in ("a", "b"):
            pid = p.create_project(name, created_by=CREATOR)
            archive.archive(Pipeline(self.conn), pid)                # the system puts them away: no 📦 limit, only "today" counts
        rid = PL.request(self.conn, p.user, "daily", "thử")
        boss = self.sign_in(OWNER, "team")
        boss.button(key=f"lim_no_{rid}").click().run()
        self.assertFalse(boss.exception, boss.exception)
        at = self.sign_in(CREATOR, "1")
        self.create(at, "c")
        self.assertNotIn("c", self.projects())
        self.assertIn("2/2", self.warnings(at))

    def test_owner_sets_a_person_limit_from_the_team_screen(self):
        boss = self.sign_in(OWNER, "team")
        boss.number_input(key=f"plim_open_{CREATOR}").set_value(4).run()
        boss.button(key=f"plim_save_{CREATOR}").click().run()
        self.assertFalse(boss.exception, boss.exception)
        self.assertEqual(PL.limits(self.conn, CREATOR)["open"], 4)


class ArchiveFlow(Base):
    def test_second_unfinished_put_away_is_refused_with_choices_and_finished_store_is_apart(self):
        p = Pipeline(self.conn)
        p.user = {"email": CREATOR, "role": "member"}
        parked = p.create_project("đã cất", created_by=CREATOR)
        archive.archive(p, parked)
        at = self.sign_in(CREATOR, "1")
        at.button(key=f"proj_archive_{self.pid}").click().run()
        at.button(key=f"proj_archive_{self.pid}_yes").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertFalse(archive.is_archived(Pipeline(connect(self.db)).project(self.pid)))
        self.assertIn("1/1 dự án dở", self.warnings(at))
        keys = {b.key for b in at.button}
        for k in (f"lim_swap_{parked}", f"lim_del_{parked}", "lim_req_parked"):
            self.assertIn(k, keys)
        at.button(key=f"lim_swap_{parked}").click().run()            # khôi phục dự án đang cất ↔ cất dự án này
        self.assertFalse(at.exception, at.exception)
        q = Pipeline(connect(self.db))
        self.assertTrue(archive.is_archived(q.project(self.pid)))
        self.assertFalse(archive.is_archived(q.project(parked)))
        # a finished project is put away without limit and listed in the "Kho dự án đã xong"
        self.conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?, 'final', 'x', '{}', 'now')", (parked,))
        self.conn.commit()
        archive.archive(p, parked)
        at.run()
        self.assertTrue(any("Kho dự án đã xong (1)" in e.label for e in at.expander))


class CreateFlowOldUi(CreateFlow):
    V2 = "0"


if __name__ == "__main__":
    unittest.main()
