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
    tmp = tempfile.mkdtemp()
    conn = connect(os.path.join(tmp, "m.sqlite"))
    return tmp, conn


def owner_ident(conn):
    return Identity(OWNER, "owner", "owner")


class OwnerTests(unittest.TestCase):
    def test_the_default_owner_is_the_requested_e_mail_and_starts_without_a_password(self):
        self.assertEqual(OWNER, "hongviet.doan@garena.vn")
        tmp, conn = fresh()
        code = auth.ensure_owner(conn, tmp)
        row = conn.execute("SELECT * FROM users WHERE email=?", (OWNER,)).fetchone()
        self.assertEqual((row["role"], row["pw_hash"]), ("owner", None))          # nobody can walk in with just the e-mail
        with self.assertRaises(AuthError):
            auth.login(conn, OWNER, "")
        self.assertEqual(open(os.path.join(tmp, "owner_setup_code.txt"), encoding="utf-8").read().split()[-1], code)
        self.assertEqual(auth.ensure_owner(conn, tmp), code)                       # the same code until it is used

    def test_setup_code_sets_the_owner_password_once_and_then_disappears(self):
        tmp, conn = fresh()
        code = auth.ensure_owner(conn, tmp)
        with self.assertRaises(AuthError):
            auth.accept_invite(conn, OWNER, "WRONG-CODE1", "long-enough-pw", tmp)
        auth.accept_invite(conn, OWNER.upper(), code.lower(), "long-enough-pw", tmp)     # case-insensitive
        self.assertFalse(os.path.exists(os.path.join(tmp, "owner_setup_code.txt")))
        self.assertIsNotNone(auth.identity(conn, auth.login(conn, OWNER, "long-enough-pw")))
        with self.assertRaises(AuthError):                                          # the code cannot be reused
            auth.accept_invite(conn, OWNER, code, "another-password", tmp)

    def test_the_owner_cannot_be_invited_demoted_or_deactivated_by_anyone(self):
        tmp, conn = fresh()
        auth.ensure_owner(conn, tmp)
        admin = Identity("a@garena.vn", "a", "admin")
        auth.invite(conn, owner_ident(conn), "a@garena.vn", "admin")
        for actor in (admin, owner_ident(conn)):
            with self.assertRaises(AuthError):
                auth.invite(conn, actor, OWNER, "member")
            with self.assertRaises(AuthError):
                auth.set_active(conn, actor, OWNER, False)
        with self.assertRaises(AuthError):
            auth.set_role(conn, owner_ident(conn), OWNER, "member")
        conn.execute("UPDATE users SET role='member' WHERE email=?", (OWNER,))       # even a tampered row is corrected
        conn.commit()
        auth.ensure_owner(conn, tmp)
        self.assertEqual(conn.execute("SELECT role FROM users WHERE email=?", (OWNER,)).fetchone()[0], "owner")


class InviteAndLoginTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.conn = fresh()
        code = auth.ensure_owner(self.conn, self.tmp)
        auth.accept_invite(self.conn, OWNER, code, "owner-password", self.tmp)
        self.owner = owner_ident(self.conn)

    def join(self, email, role="member", pw="member-password"):
        code = auth.invite(self.conn, self.owner, email, role)
        auth.accept_invite(self.conn, email, code, pw, self.tmp)
        return auth.login(self.conn, email, pw)

    def test_invited_person_signs_in_with_the_code_and_their_own_password(self):
        token = self.join("Lan@Garena.vn")
        who = auth.identity(self.conn, token)
        self.assertEqual((who.email, who.role), ("lan@garena.vn", "member"))
        self.assertIsNone(auth.identity(self.conn, "not-a-token"))
        with self.assertRaises(AuthError):
            auth.login(self.conn, "lan@garena.vn", "wrong-password")
        with self.assertRaises(AuthError) as ctx:
            auth.login(self.conn, "nobody@garena.vn", "whatever123")
        self.assertEqual(str(ctx.exception), "Email hoặc mật khẩu không đúng")       # same message: no e-mail guessing

    def test_expired_and_weak_inputs_are_refused(self):
        code = auth.invite(self.conn, self.owner, "x@garena.vn", "member")
        with self.assertRaises(AuthError):
            auth.accept_invite(self.conn, "x@garena.vn", code, "short")
        self.conn.execute("UPDATE users SET invite_expires=? WHERE email='x@garena.vn'", (time.time() - 1,))
        self.conn.commit()
        with self.assertRaises(AuthError):
            auth.accept_invite(self.conn, "x@garena.vn", code, "long-enough-pw")
        with self.assertRaises(AuthError):
            auth.invite(self.conn, self.owner, "not-an-email", "member")

    def test_five_wrong_passwords_lock_the_account_for_a_while(self):
        self.join("lock@garena.vn")
        for _ in range(auth.LOCK_AFTER):
            with self.assertRaises(AuthError):
                auth.login(self.conn, "lock@garena.vn", "nope-nope-nope")
        with self.assertRaises(AuthError) as ctx:
            auth.login(self.conn, "lock@garena.vn", "member-password")               # even the right one, while locked
        self.assertIn("tạm khóa", str(ctx.exception))
        self.conn.execute("UPDATE users SET locked_until=? WHERE email='lock@garena.vn'", (time.time() - 1,))
        self.conn.commit()
        self.assertTrue(auth.login(self.conn, "lock@garena.vn", "member-password"))

    def test_sessions_expire_can_be_signed_out_and_die_when_the_account_is_deactivated(self):
        token = self.join("s@garena.vn")
        self.assertIsNotNone(auth.identity(self.conn, token))
        self.conn.execute("UPDATE sessions SET expires_at=? WHERE email='s@garena.vn'", (time.time() - 1,))
        self.conn.commit()
        self.assertIsNone(auth.identity(self.conn, token))
        token = auth.login(self.conn, "s@garena.vn", "member-password")
        auth.logout(self.conn, token)
        self.assertIsNone(auth.identity(self.conn, token))
        token = auth.login(self.conn, "s@garena.vn", "member-password")
        auth.set_active(self.conn, self.owner, "s@garena.vn", False)
        self.assertIsNone(auth.identity(self.conn, token))                              # effective at once
        with self.assertRaises(AuthError):
            auth.login(self.conn, "s@garena.vn", "member-password")
        auth.set_active(self.conn, self.owner, "s@garena.vn", True)
        self.assertTrue(auth.login(self.conn, "s@garena.vn", "member-password"))

    def test_passwords_are_stored_hashed_and_can_be_changed(self):
        self.join("h@garena.vn")
        stored = self.conn.execute("SELECT pw_hash FROM users WHERE email='h@garena.vn'").fetchone()[0]
        self.assertTrue(stored.startswith("scrypt$"))
        self.assertNotIn("member-password", stored)
        with self.assertRaises(AuthError):
            auth.change_password(self.conn, "h@garena.vn", "wrong", "brand-new-password")
        auth.change_password(self.conn, "h@garena.vn", "member-password", "brand-new-password")
        self.assertTrue(auth.login(self.conn, "h@garena.vn", "brand-new-password"))
        with self.assertRaises(AuthError):
            auth.login(self.conn, "h@garena.vn", "member-password")

    def test_reinviting_resets_a_forgotten_password_and_signs_the_person_out(self):
        token = self.join("f@garena.vn")
        code = auth.invite(self.conn, self.owner, "f@garena.vn", "member")
        self.assertIsNone(auth.identity(self.conn, token))
        with self.assertRaises(AuthError):
            auth.login(self.conn, "f@garena.vn", "member-password")
        auth.accept_invite(self.conn, "f@garena.vn", code, "second-password")
        self.assertTrue(auth.login(self.conn, "f@garena.vn", "second-password"))


class PermissionTests(unittest.TestCase):
    def test_matrix(self):
        for perm in ("workflow", "autopilot"):
            self.assertTrue(all(auth.can(r, perm) for r in ("owner", "admin", "member")))
        for perm in ("settings", "pricing", "knowledge", "monitor", "lessons", "invite_members"):
            self.assertEqual([auth.can(r, perm) for r in ("owner", "admin", "member")], [True, True, False], perm)
        for perm in ("users", "roles", "shutdown"):
            self.assertEqual([auth.can(r, perm) for r in ("owner", "admin", "member")], [True, False, False], perm)
        self.assertFalse(auth.can(None, "workflow"))
        self.assertFalse(auth.can("stranger", "workflow"))

    def test_who_may_invite_and_change_whom(self):
        tmp, conn = fresh()
        code = auth.ensure_owner(conn, tmp)
        auth.accept_invite(conn, OWNER, code, "owner-password", tmp)
        owner = owner_ident(conn)
        auth.invite(conn, owner, "admin@garena.vn", "admin")
        admin = Identity("admin@garena.vn", "admin", "admin")
        member = Identity("m@garena.vn", "m", "member")
        auth.invite(conn, admin, "m@garena.vn", "member")                              # admin invites a member: ok
        with self.assertRaises(AuthError):
            auth.invite(conn, admin, "second-admin@garena.vn", "admin")                # only the owner makes admins
        with self.assertRaises(AuthError):
            auth.invite(conn, member, "z@garena.vn", "member")                         # members invite nobody
        with self.assertRaises(AuthError):
            auth.set_role(conn, admin, "m@garena.vn", "admin")                         # only the owner changes roles
        with self.assertRaises(AuthError):
            auth.set_active(conn, admin, "admin@garena.vn", False)                     # an admin cannot touch an admin
        auth.set_role(conn, owner, "m@garena.vn", "admin")
        self.assertEqual(conn.execute("SELECT role FROM users WHERE email='m@garena.vn'").fetchone()[0], "admin")
        self.assertTrue(auth.recent_audit(conn))


class DashboardGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"), "DASHBOARD_AUTH": "on"})
        conn = connect(self.db)
        Pipeline(conn).create_project("demo")
        self.conn = conn
        self.code = auth.ensure_owner(conn, self.tmp)

    def tearDown(self):
        os.environ["DASHBOARD_AUTH"] = "off"
        os.environ.pop("PIPELINE_DB", None)
        os.environ.pop("PIPELINE_DATA", None)

    def app(self):
        return AppTest.from_file(APP, default_timeout=40).run()

    def test_nothing_of_the_workflow_is_shown_before_sign_in(self):
        at = self.app()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.radio), 0)                                             # no step tabs, no project bar
        self.assertTrue(any("Đăng nhập" in b.label for b in at.button))
        self.assertTrue(any(auth.OWNER_EMAIL in i.value for i in at.info))            # tells where the setup code is, not the code
        self.assertFalse(any(self.code in i.value for i in at.info))

    def test_owner_claims_the_account_and_sees_everything(self):
        at = self.app()
        at.text_input(key="setup_email").set_value(OWNER)
        at.text_input(key="setup_code").set_value(self.code)
        at.text_input(key="setup_pw").set_value("owner-password")
        at.text_input(key="setup_pw2").set_value("owner-password")
        next(b for b in at.button if b.key == "setup_btn").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.radio(key="step").options), 10)
        self.assertTrue(any("Owner" in m.value for m in at.markdown))
        self.assertTrue(any("Tắt Dashboard" in e.label for e in at.expander))

    def test_member_only_gets_the_video_workflow(self):
        owner = Identity(OWNER, "owner", "owner")
        code = auth.invite(self.conn, owner, "mem@garena.vn", "member")
        at = self.app()
        at.text_input(key="setup_email").set_value("mem@garena.vn")
        at.text_input(key="setup_code").set_value(code)
        at.text_input(key="setup_pw").set_value("member-password")
        at.text_input(key="setup_pw2").set_value("member-password")
        next(b for b in at.button if b.key == "setup_btn").click().run()
        self.assertFalse(at.exception)
        options = list(at.radio(key="step").options)
        self.assertEqual(len(options), 7)
        self.assertFalse(any("Theo dõi" in o or "Bài học" in o or "Người dùng" in o for o in options))
        self.assertFalse(any("Tắt Dashboard" in e.label for e in at.expander))         # no shutdown
        labels = [t.label for t in at.tabs]
        self.assertNotIn("Bảng giá", labels)
        self.assertFalse(any(l.startswith("Kho kiến thức") for l in labels))
        self.assertIn("Dự án mới", labels)                                              # can still create projects

    def test_wrong_password_is_refused_with_a_neutral_message(self):
        at = self.app()
        at.text_input(key="login_email").set_value(OWNER)
        at.text_input(key="login_pw").set_value("guess-guess")
        next(b for b in at.button if b.key == "login_btn").click().run()
        self.assertEqual(len(at.radio), 0)
        self.assertTrue(any("không đúng" in e.value for e in at.error))


OWNER = auth.OWNER_EMAIL

if __name__ == "__main__":
    unittest.main()
