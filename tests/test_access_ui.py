"""Đợt F (02/10): quyền theo dự án trên Dashboard thật (AppTest, đăng nhập BẬT, UI v2): ⌂ lọc theo quyền, chế độ chỉ xem khóa nút ghi, người theo dõi
"được sửa" làm được, người lạ không thấy gì, quản lý người theo dõi ở ⚙ → Dự án và 👥 Nhóm."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import access, auth
from core.db import connect
from tests.test_access import CREATOR, OWNER, STRANGER, WEDIT, WVIEW, make_world

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
# widgets that stay usable in read-only mode because they only navigate / look, or belong to the person (not the project)
FREE_KEYS = {"global_pid", "step", "logout_btn", "settings_limits", "settings_history", "dark_toggle", "expert_mode", "new_name", "new_aspect",
             "new_genre", "new_prio", "new_game", "new_project_go", "home_q", "home_sort", "home_scope", "home_status", "home_step",
             "home_creator", "home_warn", "home_reset", "inbox_scope", "inbox_kind"}
# S14.19: the remarks (💬 Góp ý màn này, "Bản này dùng được chứ?" — keys fb_*) stay open to a view-only person: they change nothing


class AccessUiBase(unittest.TestCase):
    V2 = "1"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        env = {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"), "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku"),
               "FEATURE_UI_V2": self.V2, "DASHBOARD_AUTH": "on"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.conn, self.pid, self.sid, self.jid = make_world(connect(self.db))
        from core.pipeline import Pipeline
        p = Pipeline(self.conn)
        self.other = p.create_project("dự án của người lạ", created_by=STRANGER)

    def sign_in(self, email, step=None) -> AppTest:
        at = AppTest.from_file(APP, default_timeout=60)
        if step:
            at.query_params["step"] = step
        at.run()
        at.text_input(key="login_email").set_value(email)
        next(b for b in at.button if b.key == "login_btn").click().run()
        self.assertFalse(at.exception, at.exception)
        return at

    def text(self, at) -> str:
        return "\n".join([m.value for m in at.markdown] + [w.value for w in at.warning] + [w.value for w in at.info] + [c.value for c in at.caption])


class HomeListTests(AccessUiBase):
    def keys(self, at):
        return {b.key for b in at.button if b.key and b.key.startswith("home_open_")}

    def test_home_lists_follow_the_rights(self):
        want = {OWNER: {self.pid, self.other}, CREATOR: {self.pid}, WEDIT: {self.pid}, WVIEW: {self.pid}}
        for email, ids in want.items():
            at = self.sign_in(email, "home")
            if email == OWNER:                                          # the Owner's "Của tôi" is only what they made; "Cả nhóm" is everything
                self.assertEqual(self.keys(at), set())
                at.radio(key="home_scope").set_value("Cả nhóm").run()
            else:
                self.assertEqual(len(at.radio(key="step").options), 5)  # a member has no scope switch: the list is theirs + shared
                self.assertFalse(any(getattr(r, "key", None) == "home_scope" for r in at.radio))
            self.assertEqual(self.keys(at), {f"home_open_{i}" for i in ids}, email)
        at = self.sign_in(STRANGER, "home")                              # sees only their own project, never the chủ's
        self.assertEqual(self.keys(at), {f"home_open_{self.other}"})
        self.assertNotIn("dự án của chủ", self.text(at))

    def test_a_person_with_no_project_at_all_sees_nothing_of_others(self):
        auth.add_user(self.conn, Identity_owner(), "moi@garena.vn", [])
        at = self.sign_in("moi@garena.vn", "home")
        self.assertEqual(self.keys(at), set())
        self.assertIn("Chưa có dự án", self.text(at))
        self.assertNotIn("dự án của chủ", self.text(at))

    def test_watched_cards_say_which_level(self):
        self.assertIn("theo dõi · chỉ xem", self.text(self.sign_in(WVIEW, "home")))
        self.assertIn("theo dõi · được sửa", self.text(self.sign_in(WEDIT, "home")))

    def test_a_removed_watcher_loses_the_project_at_once(self):
        access.remove_watcher(self.conn, {"email": OWNER, "role": "owner"}, self.pid, WVIEW)
        at = self.sign_in(WVIEW, "home")
        self.assertEqual(self.keys(at), set())

    def test_the_inbox_holds_only_what_the_person_can_act_on(self):
        def inbox_buttons(email):
            at = self.sign_in(email, "home")
            return len([b for b in at.button if b.key and b.key.startswith("inb_")])
        self.assertEqual(inbox_buttons(CREATOR), 1)
        self.assertEqual(inbox_buttons(WEDIT), 1)
        self.assertEqual(inbox_buttons(WVIEW), 0)


def Identity_owner():
    return auth.Identity(OWNER, "owner", "owner", [])


class ReadOnlyModeTests(AccessUiBase):
    def test_view_only_person_has_every_project_input_locked(self):
        at = self.sign_in(WVIEW, "1")
        text = self.text(at)
        self.assertIn("CHỈ XEM", text)
        self.assertIn("dự án của chu@garena.vn", text)
        unlocked = []
        for kind in ("button", "checkbox", "text_area", "text_input", "selectbox", "radio", "toggle", "number_input", "slider", "multiselect"):
            for w in getattr(at, kind):
                if getattr(w, "key", None) not in FREE_KEYS and not str(getattr(w, "key", "")).startswith(("sel_btn_", "home_open_", "inb_", "fb_")) \
                        and not w.proto.disabled:
                    unlocked.append((kind, w.key))
        self.assertEqual(unlocked, [])
        locked = [w.key for w in at.button if w.proto.disabled]
        for k in ("btn_pause", "btn_cancel", "scene_add_1", "settings_clone"):
            self.assertIn(k, locked)

    def test_the_other_project_screens_are_locked_too(self):
        for step in ("2", "4", "5"):
            at = self.sign_in(WVIEW, step)
            bad = [(k, w.key) for k in ("button", "checkbox", "text_area", "text_input", "selectbox", "radio", "toggle")
                   for w in getattr(at, k) if w.key not in FREE_KEYS and not str(w.key).startswith(("sel_btn_", "home_open_", "inb_", "fb_"))
                   and not w.proto.disabled]
            self.assertEqual(bad, [], step)

    def test_view_only_person_can_still_give_feedback_on_a_delivery(self):
        out = os.path.join(self.tmp, "projects", str(self.pid), "output")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "FINAL_VIDEO.mp4"), "wb") as f:
            f.write(b"x")
        at = self.sign_in(WVIEW, "5")
        keys = {b.key: b.proto.disabled for b in at.button}
        self.assertIn(f"fb_send_{self.pid}", keys)
        self.assertFalse(keys[f"fb_send_{self.pid}"])
        self.assertFalse(at.text_area(key=f"fb_text_{self.pid}").proto.disabled)
        self.assertFalse(keys["fb_screen_send"])
        self.assertTrue(keys[f"deliver_{self.pid}"])                       # the delivery itself stays locked
    def test_a_press_that_slips_through_is_refused_by_the_core(self):
        at = self.sign_in(WVIEW, "1")
        self.assertTrue(next(b for b in at.button if b.key == "btn_pause").proto.disabled)
        self.assertEqual(self.conn.execute("SELECT paused FROM projects WHERE id=?", (self.pid,)).fetchone()[0], 0)

    def test_edit_watcher_works_like_the_creator_but_cannot_archive_or_delete(self):
        at = self.sign_in(WEDIT, "1")
        self.assertIn("quyền SỬA", self.text(at))
        keys = {b.key: b.proto.disabled for b in at.button}
        for k in ("btn_pause", "scene_add_1", "settings_clone"):
            self.assertFalse(keys[k], k)
        self.assertNotIn(f"proj_archive_{self.pid}", keys)
        self.assertNotIn(f"proj_del_{self.pid}", keys)
        next(b for b in at.button if b.key == "btn_pause").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.conn.execute("SELECT paused FROM projects WHERE id=?", (self.pid,)).fetchone()[0], 1)

    def test_creator_and_owner_see_archive_and_delete(self):
        for email in (CREATOR, OWNER):
            keys = {b.key for b in self.sign_in(email, "1").button}
            self.assertIn(f"proj_archive_{self.pid}", keys, email)
            self.assertIn(f"proj_del_{self.pid}", keys, email)

    def test_no_banner_for_the_creator(self):
        text = self.text(self.sign_in(CREATOR, "1"))
        self.assertNotIn("CHỈ XEM", text)
        self.assertNotIn("quyền SỬA", text)

    def test_the_lock_does_not_leak_to_the_next_screen_or_person(self):
        at = self.sign_in(WVIEW, "1")
        at.query_params["step"] = "home"
        at.session_state["step"] = "⌂ Tất cả dự án"
        at.run()
        self.assertTrue(all(not b.proto.disabled for b in at.button if str(b.key).startswith("home_open_")))
        self.assertFalse(next(w for w in at.selectbox if w.key == "global_pid").proto.disabled)
        again = self.sign_in(CREATOR, "1")                             # another session: widgets are free again
        self.assertFalse(next(b for b in again.button if b.key == "btn_pause").proto.disabled)


class ManageWatchersTests(AccessUiBase):
    def test_creator_adds_and_removes_a_watcher_in_the_project_settings(self):
        auth.add_user(self.conn, Identity_owner(), "them@garena.vn", [])
        at = self.sign_in(CREATOR, "1")
        at.selectbox(key=f"set_new_{self.pid}").set_value("them@garena.vn")
        at.selectbox(key=f"set_newlvl_{self.pid}").set_value("view")
        next(b for b in at.button if b.key == f"set_add_{self.pid}").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual({w["email"]: w["level"] for w in access.list_watchers(self.conn, self.pid)}, {WVIEW: "view", WEDIT: "edit", "them@garena.vn": "view"})
        next(b for b in at.button if b.key == f"set_rm_{self.pid}_them@garena.vn").click().run()
        self.assertNotIn("them@garena.vn", {w["email"] for w in access.list_watchers(self.conn, self.pid)})

    def test_creator_changes_a_level(self):
        at = self.sign_in(CREATOR, "1")
        at.selectbox(key=f"set_lvl_{self.pid}_{WVIEW}").set_value("edit")
        at.run()
        self.assertEqual(access.level(self.conn, self.pid, {"email": WVIEW, "role": "member"}), "edit")

    def test_an_edit_watcher_sees_the_list_but_has_no_controls(self):
        at = self.sign_in(WEDIT, "1")
        keys = {getattr(w, "key", None) for kind in ("button", "selectbox") for w in getattr(at, kind)}
        self.assertFalse(any(str(k).startswith(("set_add_", "set_rm_", "set_lvl_", "set_new_")) for k in keys))
        self.assertTrue(any("Chỉ Owner hoặc chủ dự án đổi danh sách" in c.value for c in at.caption))

    def test_owner_manages_watchers_and_assigns_old_projects_in_the_team_screen(self):
        self.conn.execute("UPDATE projects SET created_by=NULL WHERE id=?", (self.other,))
        self.conn.commit()
        at = self.sign_in(OWNER, "team")
        self.assertFalse(at.exception, at.exception)
        at.selectbox(key="access_pick").set_value(self.pid)
        at.run()
        self.assertTrue(any(b.key == f"team_rm_{self.pid}_{WVIEW}" for b in at.button))
        at.selectbox(key="orphan_pick").set_value(self.other)
        at.selectbox(key="orphan_owner").set_value(CREATOR)
        next(b for b in at.button if b.key == "orphan_go").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(self.conn.execute("SELECT created_by FROM projects WHERE id=?", (self.other,)).fetchone()[0], CREATOR)

    def test_a_person_without_the_monitor_permission_has_no_team_screen(self):
        at = self.sign_in(CREATOR, "team")
        self.assertFalse(at.exception, at.exception)
        self.assertNotIn("team_rm_", " ".join(str(b.key) for b in at.button))


class LegacyLookTests(AccessUiBase):
    V2 = "0"

    def test_the_old_interface_follows_the_same_rights(self):
        at = self.sign_in(WVIEW, "1")
        self.assertIn("CHỈ XEM", self.text(at))
        self.assertTrue(next(b for b in at.button if b.key == "btn_pause").proto.disabled)
        home = self.sign_in(STRANGER, "home")
        self.assertEqual({b.key for b in home.button if str(b.key).startswith("home_open_")}, {f"home_open_{self.other}"})


if __name__ == "__main__":
    unittest.main()
