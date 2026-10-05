"""S14.7 (Gói D1, kế hoạch 6b ý 2): đăng nhập LAN theo "máy được duyệt" (core/machine_auth.py).

Không gọi DNS thật: tra tên máy được thay bằng hàm giả (`machine_auth._dns_name`) hoặc socket giả."""
import os
import socket
import time
import unittest
from unittest import mock

from core import auth, machine_auth
from core.db import connect

OWNER = auth.OWNER_EMAIL
MEMBER = "ban@garena.vn"
IP = "10.20.0.31"


def fake_dns(table):
    """{ip: name or None} → a stand-in for the reverse+forward lookup."""
    return lambda ip: table.get(ip)


class Base(unittest.TestCase):
    def setUp(self):
        machine_auth.clear_cache()
        self.conn = connect()
        auth.ensure_owner(self.conn)
        env = mock.patch.dict(os.environ, {"DASHBOARD_LAN": "1", "DASHBOARD_OWNER_PASSCODE": "ma-owner"})
        env.start()
        self.addCleanup(env.stop)
        dns = mock.patch.object(machine_auth, "_dns_name", fake_dns({IP: "GKP8Q03", "10.20.0.36": "GKP8Q04"}))
        dns.start()
        self.addCleanup(dns.stop)
        self.addCleanup(machine_auth.clear_cache)

    def sign_in(self, email=MEMBER, ip=IP, local=False, passcode=None):
        return machine_auth.sign_in(self.conn, email, ip, local, f"ip={ip}", passcode)

    def actions(self):
        return [r["action"] for r in auth.recent_audit(self.conn, 50)]


class NameLookupTests(unittest.TestCase):
    def setUp(self):
        machine_auth.clear_cache()
        self.addCleanup(machine_auth.clear_cache)

    def test_reverse_name_must_resolve_back_to_the_same_ip(self):
        rev = mock.patch("core.machine_auth.socket.gethostbyaddr", return_value=("gkp8q03.vn.corp.seagroup.com", [], [IP]))
        fwd = mock.patch("core.machine_auth.socket.getaddrinfo", return_value=[(2, 1, 6, "", (IP, 0))])
        with rev, fwd:
            self.assertEqual(machine_auth.machine_of(IP, False), ("GKP8Q03", ""))

    def test_a_stale_dns_record_is_not_trusted(self):
        """Đã gặp thật 05/10: hai IP (.31, .36) cùng trả một tên → bản ghi cũ. Chiều thuận không chứa IP → không xác định được máy."""
        rev = mock.patch("core.machine_auth.socket.gethostbyaddr", return_value=("gkp8q03.vn.corp.seagroup.com", [], ["10.20.0.36"]))
        fwd = mock.patch("core.machine_auth.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("10.20.0.31", 0))])
        with rev, fwd:
            name, why = machine_auth.machine_of("10.20.0.36", False)
        self.assertIsNone(name)
        self.assertIn("không khớp", why)

    def test_no_reverse_record(self):
        with mock.patch("core.machine_auth.socket.gethostbyaddr", side_effect=socket.herror(1, "not found")):
            name, why = machine_auth.machine_of(IP, False)
        self.assertIsNone(name)
        self.assertTrue(why)

    def test_a_slow_lookup_gives_up_quickly(self):
        def slow(ip):
            time.sleep(3)
            return "LATE"
        with mock.patch.object(machine_auth, "_dns_name", slow), mock.patch.object(machine_auth, "TIMEOUT", 0.2):
            t = time.time()
            name, why = machine_auth.machine_of("10.9.9.9", False)
        self.assertLess(time.time() - t, 1.5)
        self.assertIsNone(name)
        self.assertIn("quá", why)

    def test_results_are_cached_per_ip(self):
        calls = []
        def dns(ip):
            calls.append(ip)
            return "PC1"
        with mock.patch.object(machine_auth, "_dns_name", dns):
            machine_auth.machine_of(IP, False)
            machine_auth.machine_of(IP, False)
        self.assertEqual(calls, [IP])

    def test_localhost_is_the_server_itself(self):
        with mock.patch("core.machine_auth.socket.gethostname", return_value="may-chu.vn.corp"):
            self.assertEqual(machine_auth.machine_of("127.0.0.1", True)[0], "MAY-CHU")
            self.assertEqual(machine_auth.machine_of("::1", None)[0], "MAY-CHU")
            self.assertEqual(machine_auth.machine_of("", True)[0], "MAY-CHU")

    def test_ipv4_mapped_address(self):
        self.assertEqual(machine_auth.normalize_ip("::ffff:10.20.0.31"), IP)
        self.assertTrue(machine_auth.is_local_ip("::ffff:127.0.0.1"))


class SignInTests(Base):
    def test_first_sign_in_from_a_new_machine_waits_for_the_owner(self):
        with self.assertRaises(machine_auth.MachinePending) as e:
            self.sign_in()
        self.assertIn("GKP8Q03", str(e.exception))
        self.assertIn("chờ Owner duyệt", str(e.exception))
        row = self.conn.execute("SELECT * FROM machine_approvals").fetchone()
        self.assertEqual((row["email"], row["machine"], row["status"], row["last_ip"]), (MEMBER, "GKP8Q03", "pending", IP))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)       # not signed in
        self.assertIn("machine_request", self.actions())
        with self.assertRaises(machine_auth.MachinePending):                                       # asked again: still waiting, one row
            self.sign_in()
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM machine_approvals").fetchone()[0], 1)

    def test_after_approval_only_that_machine_works(self):
        with self.assertRaises(machine_auth.MachinePending):
            self.sign_in()
        machine_auth.approve(self.conn, OWNER, MEMBER, "GKP8Q03")
        token = self.sign_in()
        self.assertEqual(auth.identity(self.conn, token).email, MEMBER)
        login = auth.recent_audit(self.conn, 1)[0]
        self.assertEqual(login["action"], "login")
        self.assertIn("GKP8Q03", login["detail"])                                               # audit names the machine
        with self.assertRaises(machine_auth.MachinePending):                                       # another PC → a new request
            self.sign_in(ip="10.20.0.36")
        machine_auth.approve(self.conn, OWNER, MEMBER, "GKP8Q04")                                   # one e-mail, several machines
        self.assertTrue(self.sign_in(ip="10.20.0.36"))

    def test_rejected_and_revoked_machines_are_refused(self):
        with self.assertRaises(machine_auth.MachinePending):
            self.sign_in()
        machine_auth.reject(self.conn, OWNER, MEMBER, "GKP8Q03")
        with self.assertRaises(auth.AuthError) as e:
            self.sign_in()
        self.assertNotIsInstance(e.exception, machine_auth.MachinePending)
        self.assertIn("GKP8Q03", str(e.exception))
        machine_auth.approve(self.conn, OWNER, MEMBER, "GKP8Q03")
        token = self.sign_in()
        machine_auth.revoke(self.conn, OWNER, MEMBER, "GKP8Q03")
        self.assertIsNone(auth.identity(self.conn, token))                                      # the open session ends at once
        with self.assertRaises(auth.AuthError):
            self.sign_in()
        self.assertIn("machine_revoke", self.actions())

    def test_unknown_machine_is_refused_with_reason_and_guidance(self):
        with self.assertRaises(auth.AuthError) as e:
            self.sign_in(ip="10.99.0.1")
        msg = str(e.exception)
        self.assertNotIsInstance(e.exception, machine_auth.MachinePending)
        self.assertIn("Không xác định được tên máy", msg)
        self.assertIn("10.99.0.1", msg)
        self.assertIn("Cách xử lý", msg)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM machine_approvals").fetchone()[0], 0)
        self.assertIn("login_refused_machine", self.actions())

    def test_owner_from_another_machine_needs_the_passcode_not_an_approval(self):
        with self.assertRaises(auth.AuthError):
            self.sign_in(OWNER, ip="10.99.0.1")                          # unknown machine, no code
        self.assertTrue(self.sign_in(OWNER, ip="10.99.0.1", passcode="ma-owner"))     # unknown machine but the code: in
        self.assertTrue(self.sign_in(OWNER, ip="127.0.0.1", local=True))              # the server itself: as before

    def test_only_listed_people_can_ask(self):
        with self.assertRaises(auth.AuthError) as e:
            self.sign_in("la@gmail.com")
        self.assertNotIsInstance(e.exception, machine_auth.MachinePending)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM machine_approvals").fetchone()[0], 0)

    def test_too_many_failed_tries_are_blocked_and_logged(self):
        for _ in range(machine_auth.MAX_FAILS):
            with self.assertRaises(auth.AuthError):
                self.sign_in("la@gmail.com")
        with self.assertRaises(auth.AuthError) as e:
            self.sign_in(OWNER, ip=IP, passcode="ma-owner")               # even a right attempt waits now
        self.assertIn("quá nhiều", str(e.exception))
        self.assertIn("login_rate_limited", self.actions())
        later = time.time() + machine_auth.FAIL_WINDOW + 1
        self.assertIsNone(machine_auth.blocked(self.conn, IP, now=later))

    def test_session_check_follows_the_machine(self):
        with self.assertRaises(machine_auth.MachinePending):
            self.sign_in()
        machine_auth.approve(self.conn, OWNER, MEMBER, "GKP8Q03")
        self.assertIsNone(machine_auth.session_refusal(self.conn, MEMBER, "member", IP, False))
        why = machine_auth.session_refusal(self.conn, MEMBER, "member", "10.20.0.36", False)     # the token carried to another PC
        self.assertIn("GKP8Q04", why)
        self.assertIsNone(machine_auth.session_refusal(self.conn, OWNER, "owner", "10.99.0.1", False))
        with mock.patch.dict(os.environ, {"DASHBOARD_LAN": ""}):
            self.assertIsNone(machine_auth.session_refusal(self.conn, MEMBER, "member", "10.20.0.36", False))

    def test_only_the_owner_decides(self):
        with self.assertRaises(machine_auth.MachinePending):
            self.sign_in()
        with self.assertRaises(auth.AuthError):
            machine_auth.approve(self.conn, MEMBER, MEMBER, "GKP8Q03")
        self.assertEqual(machine_auth.status(self.conn, MEMBER, "GKP8Q03"), "pending")
        self.assertEqual([r["machine"] for r in machine_auth.requests(self.conn)], ["GKP8Q03"])


class ReviewFixTests(Base):
    """Rà độc lập D1 (05/10): 3 lỗi nên sửa."""
    def test_rejecting_a_pending_request_does_not_sign_the_person_out(self):
        with self.assertRaises(machine_auth.MachinePending):
            self.sign_in(ip="10.20.0.36")
        machine_auth.approve(self.conn, OWNER, MEMBER, "GKP8Q04")
        token = self.sign_in(ip="10.20.0.36")                        # signed in on the approved PC
        with self.assertRaises(machine_auth.MachinePending):          # someone types this e-mail on another PC
            self.sign_in()
        machine_auth.reject(self.conn, OWNER, MEMBER, "GKP8Q03")
        self.assertIsNotNone(auth.identity(self.conn, token))         # the real person is not thrown out
        machine_auth.revoke(self.conn, OWNER, MEMBER, "GKP8Q04")      # revoking an APPROVED machine still ends sessions
        self.assertIsNone(auth.identity(self.conn, token))

    def test_too_many_lookups_in_flight_answer_at_once(self):
        called = []
        with mock.patch.object(machine_auth, "_dns_name", lambda ip: called.append(ip) or "X"),                 mock.patch.object(machine_auth, "_inflight", machine_auth.MAX_INFLIGHT):
            name, why = machine_auth.machine_of("10.20.0.77", False)
        self.assertIsNone(name)
        self.assertIn("bận", why)
        self.assertEqual(called, [])
        self.assertNotIn("10.20.0.77", machine_auth._cache)             # not remembered: the next try looks up again

    def test_only_the_configured_owner_email_skips_the_machine_check(self):
        old_owner = "cu@garena.vn"                                     # a stale users row with role owner
        gate = machine_auth._gate(self.conn, "10.99.0.1", False)
        with self.assertRaises(auth.AuthError):
            gate(old_owner, "owner")
        self.assertIsNotNone(machine_auth.session_refusal(self.conn, old_owner, "owner", "10.99.0.1", False))
        self.assertIsNone(machine_auth.session_refusal(self.conn, OWNER, "owner", "10.99.0.1", False))


class LanOffTests(unittest.TestCase):
    def test_without_lan_the_old_sign_in_is_kept(self):
        conn = connect()
        with mock.patch.dict(os.environ, {"DASHBOARD_LAN": ""}), mock.patch.object(machine_auth, "_dns_name", lambda ip: None):
            self.assertFalse(machine_auth.lan_on())
            self.assertTrue(machine_auth.sign_in(conn, MEMBER, "", True, "local", None))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM machine_approvals").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
