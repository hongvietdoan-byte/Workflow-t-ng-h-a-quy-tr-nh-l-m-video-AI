import os
import tempfile
import time
import unittest

from streamlit.testing.v1 import AppTest

from core import auth
from core.auth import AuthError, Identity
from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
OWNER = auth.OWNER_EMAIL


def fresh():
    conn = connect(os.path.join(tempfile.mkdtemp(), "m.sqlite"))
    auth.ensure_owner(conn)
    return conn


def owner():
    return Identity(OWNER, "owner", "owner", [])


class SignInTests(unittest.TestCase):
    def test_the_requested_e_mail_is_the_owner_and_signs_in_with_the_e_mail_alone(self):
        self.assertEqual(OWNER, "hongviet.doan@garena.vn")
        conn = fresh()
        who = auth.identity(conn, auth.login(conn, "  Hongviet.Doan@Garena.vn "))
        self.assertEqual((who.email, who.role), (OWNER, "owner"))
        for perm in ("workflow", "settings", "knowledge", "monitor", "lessons", "users", "shutdown"):
            self.assertTrue(auth.can(who, perm))

    def test_company_e_mail_is_added_as_a_plain_member_on_first_sign_in(self):
        conn = fresh()
        who = auth.identity(conn, auth.login(conn, "lan@garena.vn"))
        self.assertEqual((who.role, who.perms), ("member", []))
        self.assertTrue(auth.can(who, "workflow") and auth.can(who, "autopilot"))
        for perm in ("settings", "knowledge", "monitor", "lessons", "users", "shutdown"):
            self.assertFalse(auth.can(who, perm), perm)
        self.assertEqual(conn.execute("SELECT created_by FROM users WHERE email='lan@garena.vn'").fetchone()[0], "auto-domain")

    def test_other_e_mails_are_refused_until_the_owner_adds_them(self):
        conn = fresh()
        with self.assertRaises(AuthError) as ctx:
            auth.login(conn, "someone@gmail.com")
        self.assertIn("chưa được cấp quyền", str(ctx.exception))
        with self.assertRaises(AuthError):
            auth.login(conn, "not an email")
        auth.add_user(conn, owner(), "someone@gmail.com", ["monitor"])
        who = auth.identity(conn, auth.login(conn, "someone@gmail.com"))
        self.assertTrue(auth.can(who, "monitor"))

    def test_owner_can_change_or_clear_the_auto_member_domains(self):
        conn = fresh()
        auth.set_auto_domains(conn, owner(), "example.com; other.org")
        self.assertEqual(auth.auto_domains(conn), ["example.com", "other.org"])
        with self.assertRaises(AuthError):
            auth.login(conn, "lan@garena.vn")                                     # no longer an auto domain
        self.assertTrue(auth.login(conn, "x@example.com"))
        auth.set_auto_domains(conn, owner(), "")
        with self.assertRaises(AuthError):
            auth.login(conn, "y@example.com")
        with self.assertRaises(AuthError):
            auth.set_auto_domains(conn, owner(), "not a domain!")
        with self.assertRaises(AuthError):
            auth.set_auto_domains(conn, Identity("m@garena.vn", "m", "member", []), "evil.com")   # owner only

    def test_owner_local_only_switch_refuses_remote_owner_sign_in(self):
        conn = fresh()
        os.environ["DASHBOARD_OWNER_LOCAL_ONLY"] = "1"
        try:
            with self.assertRaises(AuthError):
                auth.login(conn, OWNER, "host=10.7.30.23:8501", local=False)
            self.assertTrue(auth.login(conn, OWNER, "host=localhost:8501", local=True))
            self.assertTrue(auth.login(conn, "m@garena.vn", "host=10.7.30.23:8501", local=False))   # others unaffected
        finally:
            os.environ.pop("DASHBOARD_OWNER_LOCAL_ONLY", None)

    def test_sessions_expire_sign_out_and_die_when_a_person_is_switched_off(self):
        conn = fresh()
        token = auth.login(conn, "s@garena.vn")
        self.assertIsNotNone(auth.identity(conn, token))
        self.assertIsNone(auth.identity(conn, "made-up"))
        conn.execute("UPDATE sessions SET expires_at=? WHERE email='s@garena.vn'", (time.time() - 1,))
        conn.commit()
        self.assertIsNone(auth.identity(conn, token))
        token = auth.login(conn, "s@garena.vn")
        auth.logout(conn, token)
        self.assertIsNone(auth.identity(conn, token))
        token = auth.login(conn, "s@garena.vn")
        auth.set_user(conn, owner(), "s@garena.vn", [], False)
        self.assertIsNone(auth.identity(conn, token))                               # at once
        with self.assertRaises(AuthError):
            auth.login(conn, "s@garena.vn")                                         # and an auto-domain e-mail cannot slip back in
        auth.set_user(conn, owner(), "s@garena.vn", [], True)
        self.assertTrue(auth.login(conn, "s@garena.vn"))

    def test_sign_ins_and_refusals_are_in_the_audit_log_with_their_origin(self):
        conn = fresh()
        auth.login(conn, "a@garena.vn", "host=10.7.30.23:8501 ip=10.7.30.9")
        with self.assertRaises(AuthError):
            auth.login(conn, "b@gmail.com", "host=10.7.30.23:8501 ip=10.7.30.77")
        log = {(r["email"], r["action"]): r["detail"] for r in auth.recent_audit(conn)}
        self.assertIn("ip=10.7.30.9", log[("a@garena.vn", "login")])
        self.assertIn("ip=10.7.30.77", log[("b@gmail.com", "login_refused")])


class PermissionTableTests(unittest.TestCase):
    def test_only_the_owner_edits_the_table_and_the_owner_row_is_untouchable(self):
        conn = fresh()
        member = Identity("m@garena.vn", "m", "member", ["settings", "knowledge", "monitor", "lessons"])
        for action in (lambda: auth.add_user(conn, member, "z@garena.vn"), lambda: auth.set_user(conn, member, "m@garena.vn", [], True),
                       lambda: auth.remove_user(conn, member, "m@garena.vn"),
                       lambda: auth.apply_table(conn, member, [{"email": "m@garena.vn", "active": True, "perms": []}])):
            with self.assertRaises(AuthError):
                action()
        for action in (lambda: auth.set_user(conn, owner(), OWNER, [], False), lambda: auth.remove_user(conn, owner(), OWNER)):
            with self.assertRaises(AuthError):
                action()
        self.assertEqual(conn.execute("SELECT role, active FROM users WHERE email=?", (OWNER,)).fetchone()[:], ("owner", 1))
        conn.execute("UPDATE users SET role='member' WHERE email=?", (OWNER,))       # even a tampered row is corrected
        conn.commit()
        auth.ensure_owner(conn)
        self.assertEqual(conn.execute("SELECT role FROM users WHERE email=?", (OWNER,)).fetchone()[0], "owner")

    def test_saving_the_table_grants_and_removes_permissions_and_counts_only_real_changes(self):
        conn = fresh()
        auth.add_user(conn, owner(), "a@garena.vn")
        auth.add_user(conn, owner(), "b@garena.vn", ["lessons", "bogus-permission"])
        self.assertEqual({u["email"]: u["perms"] for u in auth.list_users(conn)}["b@garena.vn"], ["lessons"])   # unknown ones dropped
        with self.assertRaises(AuthError):
            auth.add_user(conn, owner(), "a@garena.vn")                               # already there
        rows = [{"email": "a@garena.vn", "active": True, "perms": ["settings", "monitor"]},
                {"email": "b@garena.vn", "active": True, "perms": ["lessons"]},         # unchanged
                {"email": OWNER, "active": False, "perms": []}]                         # ignored
        self.assertEqual(auth.apply_table(conn, owner(), rows), 1)
        token = auth.login(conn, "a@garena.vn")
        who = auth.identity(conn, token)
        self.assertTrue(auth.can(who, "settings") and auth.can(who, "monitor"))
        self.assertFalse(auth.can(who, "knowledge") or auth.can(who, "users") or auth.can(who, "shutdown"))
        auth.apply_table(conn, owner(), [{"email": "a@garena.vn", "active": True, "perms": []}])
        self.assertFalse(auth.can(auth.identity(conn, token), "settings"))             # applies to the open session at once
        auth.remove_user(conn, owner(), "b@garena.vn")
        self.assertNotIn("b@garena.vn", [u["email"] for u in auth.list_users(conn)])

    def test_owner_only_rights_cannot_be_handed_out(self):
        conn = fresh()
        auth.add_user(conn, owner(), "c@garena.vn", ["users", "shutdown", "settings"])
        who = auth.identity(conn, auth.login(conn, "c@garena.vn"))
        self.assertEqual(who.perms, ["settings"])
        self.assertFalse(auth.can(who, "users") or auth.can(who, "shutdown"))


class DashboardGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"), "DASHBOARD_AUTH": "on"})
        self.conn = connect(self.db)
        Pipeline(self.conn).create_project("demo")

    def tearDown(self):
        os.environ["DASHBOARD_AUTH"] = "off"
        os.environ.pop("PIPELINE_DB", None)
        os.environ.pop("PIPELINE_DATA", None)

    def sign_in(self, email, params=None):
        at = AppTest.from_file(APP, default_timeout=40)
        for k, v in (params or {}).items():
            at.query_params[k] = v
        at.run()
        if email:
            at.text_input(key="login_email").set_value(email)
            next(b for b in at.button if b.key == "login_btn").click().run()
        return at

    def test_only_an_e_mail_box_is_shown_before_signing_in(self):
        at = self.sign_in(None)
        self.assertFalse(at.exception)
        self.assertEqual(len(at.radio), 0)
        self.assertEqual([t.key for t in at.text_input], ["login_email"])            # no password field at all

    def test_owner_sees_everything(self):
        at = self.sign_in(OWNER)
        self.assertFalse(at.exception)
        options = list(at.radio(key="step").options)
        self.assertEqual(len(options), 9)
        self.assertTrue(any("Phân quyền" in o for o in options))
        self.assertTrue(any("Tắt Dashboard" in e.label for e in at.expander))
        self.assertIn("login", at.query_params)                                       # remembered for reloads

    def test_company_e_mail_only_gets_the_video_steps(self):
        at = self.sign_in("new.person@garena.vn")
        self.assertFalse(at.exception)
        options = list(at.radio(key="step").options)
        self.assertEqual(len(options), 6)
        self.assertFalse(any(w in o for o in options for w in ("Theo dõi", "Bài học", "Phân quyền")))
        self.assertFalse(any("Tắt Dashboard" in e.label for e in at.expander))
        labels = [t.label for t in at.tabs]
        self.assertNotIn("Bảng giá", labels)
        self.assertFalse(any(l.startswith("Kho kiến thức") for l in labels))
        self.assertIn("Dự án mới", labels)

    def test_a_granted_permission_shows_up_for_that_person(self):
        auth.add_user(self.conn, owner(), "boss2@garena.vn", ["monitor", "settings"])
        at = self.sign_in("boss2@garena.vn")
        options = list(at.radio(key="step").options)
        self.assertEqual(len(options), 7)
        self.assertTrue(any("Theo dõi" in o for o in options))
        self.assertIn("Bảng giá", [t.label for t in at.tabs])
        self.assertFalse(any("Phân quyền" in o for o in options))

    def test_unlisted_outside_e_mail_is_refused_with_a_clear_message(self):
        at = self.sign_in("stranger@gmail.com")
        self.assertEqual(len(at.radio), 0)
        self.assertTrue(any("chưa được cấp quyền" in e.value for e in at.error))

    def test_the_e_mail_in_the_address_signs_in_again_after_a_reload(self):
        at = self.sign_in(None, {"login": "back@garena.vn"})
        self.assertFalse(at.exception)
        self.assertEqual(len(at.radio(key="step").options), 6)

    def test_owner_permission_table_page_renders(self):
        auth.add_user(self.conn, owner(), "x@garena.vn", ["lessons"])
        at = self.sign_in(OWNER, {"step": "users"})
        self.assertFalse(at.exception)
        self.assertTrue(any("Bảng phân quyền" in m.value for m in at.markdown))
        self.assertTrue(any(OWNER in m.value for m in at.markdown))


if __name__ == "__main__":
    unittest.main()
