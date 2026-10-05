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
    @staticmethod
    def crafted(at, values):
        """What a crafted browser message would send: the current widget states + `values` ({widget id: (field, value)}).
        AppTest refuses to set a disabled widget, so the message is built by hand like a modified client would."""
        ws = at._tree.get_widget_states()
        for wid, (field, value) in values.items():
            w = next((x for x in ws.widgets if x.id == wid), None) or ws.widgets.add()
            w.id = wid
            setattr(w, field, value)
        return at._run(ws)

    def test_streamlit_drops_values_sent_for_a_disabled_widget(self):
        """S14.7 (D1, kế hoạch 3.5 ý 4): khóa "chỉ xem" có hiệu lực ở SERVER vì Streamlit bỏ giá trị gửi lên của widget `disabled`
        (đã kiểm trên 1.64.0). Ghim bản tối thiểu trong requirements.txt để một lần hạ cấp không mở lại lỗ này."""
        script = ("import streamlit as st\n"
                  "v = st.text_input('x', key='t', disabled={d})\n"
                  "c = st.button('b', key='b', disabled={d})\n"
                  "st.markdown(f'v={{v!r}} c={{c}}')\n")
        for disabled, want in ((False, "v='hack' c=True"), (True, "v='' c=False")):     # control first: the crafted message works
            at = AppTest.from_string(script.format(d=disabled))
            at.run()
            self.crafted(at, {at.text_input(key="t").id: ("string_value", "hack"), at.button(key="b").id: ("trigger_value", True)})
            self.assertFalse(at.exception, at.exception)
            self.assertEqual(at.markdown[-1].value, want, f"disabled={disabled}")
        # the real screen: a click sent for the disabled ⏸ never reaches the core (no refusal message, nothing written)
        real = self.sign_in(WVIEW, "1")
        pause = next(b for b in real.button if b.key == "btn_pause")
        self.assertTrue(pause.proto.disabled)
        before = [e.value for e in real.error]     # (a viewer already sees one refusal: the format panel auto-fills an empty aspect)
        self.crafted(real, {pause.id: ("trigger_value", True)})
        self.assertFalse(real.exception, real.exception)
        self.assertEqual([e.value for e in real.error], before)          # no new refusal: the core was never even asked
        self.assertEqual(self.conn.execute("SELECT paused FROM projects WHERE id=?", (self.pid,)).fetchone()[0], 0)

    def test_requirements_pin_the_streamlit_that_drops_disabled_values(self):
        import re
        import streamlit
        req = open(os.path.join(os.path.dirname(__file__), "..", "requirements.txt"), encoding="utf-8").read()
        m = re.search(r"^streamlit\s*>=\s*([\d.]+)", req, re.M)
        self.assertIsNotNone(m, "requirements.txt không ghim streamlit")
        pin = tuple(int(x) for x in m.group(1).split("."))
        self.assertGreaterEqual(pin, (1, 64), "ghim streamlit thấp hơn bản đã kiểm (1.64)")
        self.assertGreaterEqual(tuple(int(x) for x in streamlit.__version__.split(".")[:2]), pin[:2])

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


class UiHoleTests(AccessUiBase):
    """S14.7 (D1, kế hoạch 3.5 ý 1): hai nút ghi đi ngoài kiểm quyền — mở lại dịch vụ hết tiền và khôi phục thùng rác."""

    def halt(self):
        from core import budget
        budget.halt(self.conn, "clipai", "hết tiền (thử)")

    def test_a_member_without_money_rights_gets_no_reopen_button(self):
        self.halt()
        at = self.sign_in(CREATOR, "1")
        keys = {b.key: b.proto.disabled for b in at.button}
        self.assertFalse(keys.get("mc_reopen_clipai") is False, "người không có quyền 'Cài đặt & bảng giá' bấm được mở lại dịch vụ")
        from core import budget
        self.assertTrue(budget.halted(self.conn, "clipai"))

    def test_the_budget_dialog_checks_the_right_again_when_drawn(self):
        self.halt()
        at = self.sign_in(CREATOR, "1")
        at.session_state["dlg_budget"] = True                          # a stale flag (or a crafted rerun) opens the dialog
        at.run()
        self.assertFalse(at.exception, at.exception)
        keys = {b.key for b in at.button}
        self.assertNotIn("reopen_clipai", keys)
        self.assertNotIn("budget_usd", {w.key for w in at.number_input})
        self.assertTrue(any("Cài đặt & bảng giá" in e.value for e in at.error), [e.value for e in at.error])

    def test_the_owner_still_reopens(self):
        self.halt()
        at = self.sign_in(OWNER, "1")
        b = next(b for b in at.button if b.key == "mc_reopen_clipai")
        self.assertFalse(b.proto.disabled)
        b.click().run()
        from core import budget
        self.assertFalse(budget.halted(self.conn, "clipai"))

    def trashed(self):
        from core import trash
        data = os.path.join(self.tmp, "projects")
        img = os.path.join(data, str(self.pid), "images", "job_99.png")
        os.makedirs(os.path.dirname(img), exist_ok=True)
        with open(img, "wb") as f:
            f.write(b"x")
        trash.move_to_trash(img, data, self.pid, "images", "bị loại", 99, 1)
        return img

    def test_a_view_only_watcher_cannot_restore_from_the_trash(self):
        img = self.trashed()
        at = self.sign_in(WVIEW, "1")
        at.session_state["dlg_history"] = True
        at.run()
        self.assertFalse(at.exception, at.exception)
        btns = [b for b in at.button if str(b.key).startswith("tr_images_")]
        self.assertTrue(btns, "không thấy nút khôi phục")
        self.assertTrue(all(b.proto.disabled for b in btns), "người chỉ xem bấm được ↩ Khôi phục")
        self.assertFalse(os.path.exists(img))

    def test_an_edit_watcher_restores(self):
        img = self.trashed()
        at = self.sign_in(WEDIT, "1")
        at.session_state["dlg_history"] = True
        at.run()
        b = next(b for b in at.button if str(b.key).startswith("tr_images_"))
        self.assertFalse(b.proto.disabled)
        b.click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(os.path.exists(img))


class MachineLoginUiTests(AccessUiBase):
    """S14.7 (D1, 6b ý 2): DASHBOARD_LAN=1 → thành viên chỉ vào từ máy Owner đã duyệt; cả lối ?login= cũng qua kiểm máy.
    AppTest không có IP → trình duyệt coi như trên chính máy chủ (tên máy = socket.gethostname, ở đây thay bằng tên giả)."""

    def setUp(self):
        super().setUp()
        from core import machine_auth
        machine_auth.clear_cache()
        self.addCleanup(machine_auth.clear_cache)
        for patcher in (mock.patch.dict(os.environ, {"DASHBOARD_LAN": "1", "DASHBOARD_OWNER_PASSCODE": "ma"}),
                        mock.patch("core.machine_auth.socket.gethostname", return_value="may-chu.vn.corp")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def try_in(self, email, link=False) -> AppTest:
        at = AppTest.from_file(APP, default_timeout=60)
        at.query_params["step"] = "1"
        if link:
            at.query_params["login"] = email
        at.run()
        if not link:
            at.text_input(key="login_email").set_value(email)
            next(b for b in at.button if b.key == "login_btn").click().run()
        self.assertFalse(at.exception, at.exception)
        return at

    def signed_in(self, at) -> bool:
        return not any(b.key == "login_btn" for b in at.button)

    def status(self):
        r = self.conn.execute("SELECT status FROM machine_approvals WHERE email=? AND machine='MAY-CHU'", (CREATOR,)).fetchone()
        return r[0] if r else None

    def test_a_member_waits_until_the_owner_approves_the_machine(self):
        at = self.try_in(CREATOR)
        self.assertFalse(self.signed_in(at))
        self.assertTrue(any("chờ Owner duyệt máy MAY-CHU" in i.value for i in at.info), [i.value for i in at.info])
        self.assertEqual(self.status(), "pending")
        owner = self.sign_in(OWNER, "team")                                    # the Owner on the server machine: as before
        self.assertTrue(self.signed_in(owner))
        btn = next(b for b in owner.button if b.key == f"mach_ok_{CREATOR}_MAY-CHU")
        btn.click().run()
        self.assertFalse(owner.exception, owner.exception)
        self.assertEqual(self.status(), "approved")
        self.assertTrue(self.signed_in(self.try_in(CREATOR)))

    def test_an_old_login_link_goes_through_the_machine_check(self):
        at = self.try_in(CREATOR, link=True)
        self.assertFalse(self.signed_in(at))
        self.assertEqual(self.status(), "pending")

    def test_a_revoked_machine_ends_the_open_session(self):
        from core import machine_auth
        machine_auth.approve(self.conn, OWNER, CREATOR, "MAY-CHU")
        at = self.try_in(CREATOR)
        self.assertTrue(self.signed_in(at))
        machine_auth.revoke(self.conn, OWNER, CREATOR, "MAY-CHU")
        at.run()
        self.assertFalse(self.signed_in(at))


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
