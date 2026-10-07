"""Người dùng 07/10: hiệu ứng nút sáng bật sẵn ở mọi tài khoản; ai muốn tắt thì tắt — và lần sau vào vẫn tắt (lưu theo người)."""
import unittest

from core import user_prefs as U
from core.db import connect


class PrefsTests(unittest.TestCase):
    def test_on_by_default_off_per_person_and_kept(self):
        conn = connect()
        self.assertTrue(U.get(conn, "a@garena.vn", "next_glow"))
        U.set(conn, "A@garena.vn", "next_glow", False)                          # same person, any case
        self.assertFalse(U.get(conn, "a@garena.vn", "next_glow"))
        self.assertTrue(U.get(conn, "b@garena.vn", "next_glow"))                # others keep it on
        U.set(conn, "a@garena.vn", "next_glow", True)
        self.assertTrue(U.get(conn, "a@garena.vn", "next_glow"))

    def test_unknown_names_are_refused(self):
        with self.assertRaises(ValueError):
            U.get(connect(), "a@x", "nope")


if __name__ == "__main__":
    unittest.main()
