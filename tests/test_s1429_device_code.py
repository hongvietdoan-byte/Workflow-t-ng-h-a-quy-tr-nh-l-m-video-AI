"""S14.29: đăng nhập LAN — nhận máy dự phòng bằng MÃ THIẾT BỊ khi IP không có tên DNS ngược (người dùng duyệt thiết kế 05/10).

Trình duyệt giữ một mã ngẫu nhiên (cookie dài hạn); 'máy' = DEV-<6 ký tự băm>; CSDL chỉ lưu băm, không lưu mã thô; mã không vào nhật ký.
Cùng luật như máy có tên DNS: máy đầu tự duyệt (khi AUTO_FIRST_MACHINE), máy sau chờ Owner, Owner thu hồi được; có tên DNS thì vẫn
dùng tên DNS. Không gọi DNS thật."""
import os
import unittest
from unittest import mock

from core import auth, machine_auth
from core.db import connect

MEMBER = "ban@garena.vn"
NO_PTR = "10.7.168.20"           # dải 10.7.168.x: không có PTR (thử thật 05/10)
WITH_PTR = "10.7.30.31"
CODE = machine_auth.new_device_code()
OTHER = machine_auth.new_device_code()


class DeviceCodeTests(unittest.TestCase):
    def setUp(self):
        machine_auth.clear_cache()
        self.conn = connect()
        auth.ensure_owner(self.conn)
        for p in (mock.patch.dict(os.environ, {"DASHBOARD_LAN": "1", "DASHBOARD_OWNER_PASSCODE": "ma-owner"}),
                  mock.patch.object(machine_auth, "_dns_name", lambda ip: {WITH_PTR: "GKP8Q03"}.get(ip))):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(machine_auth.clear_cache)

    def sign_in(self, device=None, ip=NO_PTR, email=MEMBER):
        return machine_auth.sign_in(self.conn, email, ip, False, f"ip={ip}", device=device)

    def everything_stored(self) -> str:
        out = []
        for (table,) in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            out += [repr(tuple(r)) for r in self.conn.execute(f"SELECT * FROM {table}")]
        return "\n".join(out)

    def test_code_format_and_name(self):
        self.assertTrue(machine_auth.valid_device_code(CODE))
        self.assertNotEqual(CODE, OTHER)
        for bad in (None, "", "ngắn", "x" * 200, "abc def" * 8, "a/b" * 20):
            self.assertFalse(machine_auth.valid_device_code(bad), bad)
        name = machine_auth.device_name(machine_auth.device_hash(CODE))
        self.assertRegex(name, r"^DEV-[0-9A-F]{6}$")

    def test_no_dns_name_and_no_code_is_refused_and_says_why(self):
        with self.assertRaises(auth.AuthError) as e:
            self.sign_in(device=None)
        self.assertIn("mã thiết bị", str(e.exception))

    def test_first_device_is_auto_approved_then_the_same_code_signs_in(self):
        with mock.patch.object(machine_auth, "AUTO_FIRST_MACHINE", True):
            self.assertTrue(self.sign_in(device=CODE))
            self.assertTrue(self.sign_in(device=CODE))
        row = self.conn.execute("SELECT * FROM machine_approvals").fetchone()
        self.assertEqual((row["status"], row["kind"]), ("approved", "device"))
        self.assertEqual(row["machine"], machine_auth.device_name(machine_auth.device_hash(CODE)))
        self.assertEqual(row["device_hash"], machine_auth.device_hash(CODE))
        self.assertNotIn(CODE, self.everything_stored())                                # mã thô không nằm ở đâu trong CSDL
        self.assertIsNone(machine_auth.session_refusal(self.conn, MEMBER, "member", NO_PTR, False, device=CODE))

    def test_unknown_or_forged_code_waits_for_the_owner(self):
        with mock.patch.object(machine_auth, "AUTO_FIRST_MACHINE", True):
            self.sign_in(device=CODE)
            with self.assertRaises(machine_auth.MachinePending) as e:
                self.sign_in(device=OTHER)                                            # máy thứ hai của cùng người → chờ
        self.assertIn("DEV-", str(e.exception))
        self.assertNotIn(OTHER, str(e.exception))
        other = machine_auth.device_name(machine_auth.device_hash(OTHER))
        self.assertEqual(machine_auth.status(self.conn, MEMBER, other), "pending")
        machine_auth.approve(self.conn, auth.OWNER_EMAIL, MEMBER, other)
        self.assertTrue(self.sign_in(device=OTHER))

    def test_same_name_with_a_different_code_is_refused(self):
        with mock.patch.object(machine_auth, "AUTO_FIRST_MACHINE", True):
            self.sign_in(device=CODE)
        name = machine_auth.device_name(machine_auth.device_hash(CODE))
        with mock.patch.object(machine_auth, "device_name", return_value=name):             # trùng 6 ký tự đầu băm (giả lập)
            with self.assertRaises(auth.AuthError) as e:
                self.sign_in(device=OTHER)
        self.assertNotIsInstance(e.exception, machine_auth.MachinePending)
        self.assertIn("không khớp", str(e.exception))

    def test_revoked_code_is_refused_and_the_open_session_ends(self):
        with mock.patch.object(machine_auth, "AUTO_FIRST_MACHINE", True):
            self.sign_in(device=CODE)
        name = machine_auth.device_name(machine_auth.device_hash(CODE))
        machine_auth.revoke(self.conn, auth.OWNER_EMAIL, MEMBER, name)
        with self.assertRaises(auth.AuthError):
            self.sign_in(device=CODE)
        self.assertIsNotNone(machine_auth.session_refusal(self.conn, MEMBER, "member", NO_PTR, False, device=CODE))

    def test_dns_name_wins_over_the_code(self):
        with mock.patch.object(machine_auth, "AUTO_FIRST_MACHINE", True):
            self.sign_in(device=CODE, ip=WITH_PTR)
        row = self.conn.execute("SELECT machine, kind, device_hash FROM machine_approvals").fetchone()
        self.assertEqual((row["machine"], row["kind"], row["device_hash"]), ("GKP8Q03", "dns", None))

    def test_code_never_reaches_the_audit_log(self):
        with mock.patch.object(machine_auth, "AUTO_FIRST_MACHINE", True):
            self.sign_in(device=CODE)
            with self.assertRaises(machine_auth.MachinePending):
                self.sign_in(device=OTHER)
        text = " ".join(f"{r['action']} {r['detail']}" for r in auth.recent_audit(self.conn, 50))
        self.assertIn("DEV-", text)
        self.assertNotIn(CODE, text)
        self.assertNotIn(OTHER, text)

    def test_lan_off_ignores_the_code(self):
        with mock.patch.dict(os.environ, {"DASHBOARD_LAN": "0"}):
            self.assertTrue(self.sign_in(device=CODE))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM machine_approvals").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
