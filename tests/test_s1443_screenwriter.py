"""S14.43 nhánh A (chấm phiếu 05d, người dùng 06/10, TB 4,20): Biên kịch dùng tên thật FF, thoại vui GenZ + khớp hành động, màn hình
điện thoại nhìn từ xa không chặn / lộ màn hình = cần tài nguyên màn hình mô phỏng, `idea_to_script` bật mặc định + hỏi khi kịch bản sơ sài,
kho khuôn hài. 0 USD (MockLlm / hàm thuần, không gọi API thật)."""
import json
import os
import unittest
from unittest import mock

from core import assets, idea_buildable as B, idea_to_script as I
from core.db import connect
from core.pipeline import Pipeline
from tests.test_idea_to_script import ANCHORS, IDEA, Recorder, make_kit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\n"
INP = {"duration_s": 15, "anchors": dict(ANCHORS, characters=["KELLY", "MAXIM"], plot="", ending="")}


class PhoneScreenS1443(unittest.TestCase):
    """Mục 4: nhìn TỪ XA (không đọc được) → không chặn; LỘ góc nhìn màn hình → không chặn, 'cần tài nguyên màn hình mô phỏng' (bảng kê +
    ước tính); nhắc màn hình mà không rõ xa/cận → nói ra (coi là từ xa), không im lặng."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("màn hình", operating_mode="human_qc")
        make_kit(self.p.conn)

    def check(self, body):
        return I.check_script(self.p.conn, self.pid, HEAD + body, INP)

    def test_view_rules_far_close_content_unclear(self):
        cases = {
            "Toàn cảnh: Kelly và Maxim cúi nhìn điện thoại, màn hình nhìn từ xa không đọc được.": "far",
            "Máy đặt từ xa, Kelly chỉ vào màn hình điện thoại của Maxim.": "far",
            "Ánh sáng màn hình hắt lên mặt Kelly.": "far",
            "Cận màn hình điện thoại: huy hiệu hạng Huyền Thoại xoay.": "exposed",
            "Cận cảnh điện thoại trên tay Kelly.": "exposed",
            "Kelly giơ điện thoại về phía máy quay khoe rank.": "exposed",
            "Màn hình hiện dòng chữ 'Up next in 3'.": "exposed",
            "Quay màn hình: bảng xếp hạng bạn bè.": "exposed",
            "Trung cảnh, Kelly chỉ tay vào màn hình điện thoại của Maxim.": "unclear",
            "Maxim cau mày nhìn xuống màn hình mình.": "unclear",
            "Kelly đứng ở bãi cỏ, thanh máu hiện trên đầu.": "",
            "CHỮ TRÊN MÀN HÌNH: Tải Free Fire ngay": "",
        }
        for line, want in cases.items():
            with self.subTest(line=line):
                self.assertEqual(B.screen_view(line), want)

    def test_far_or_unclear_screen_is_not_blocked_and_unclear_is_said(self):
        far = self.check("Toàn cảnh từ xa: Kelly và Maxim cúi nhìn điện thoại.\nKELLY: Rớt rồi kìa!")
        self.assertEqual(far["blocked_scenes"], [])
        self.assertFalse(any("màn hình" in f for f in far["flags"]))
        unclear = self.check("Trung cảnh, Kelly chỉ tay vào màn hình điện thoại của Maxim.\nMAXIM: Xui thật đó mà.")
        self.assertEqual(unclear["blocked_scenes"], [])                    # phiếu 05d ý 2: không chặn nữa
        self.assertTrue(any("từ xa" in f.lower() for f in unclear["flags"]), unclear["flags"])   # nói ra, không im lặng

    def test_exposed_screen_is_a_resource_not_a_block(self):
        c = self.check("Cận màn hình điện thoại: huy hiệu hạng Huyền Thoại xoay, lớp 'Up next in 3' bật lên.\nKELLY: Ơ…")
        self.assertEqual(c["blocked_scenes"], [])
        self.assertTrue(any("cần tài nguyên màn hình mô phỏng" in f for f in c["flags"]), c["flags"])
        # game interface on the exposed phone screen = what the simulated screen shows (not a set to build)
        c2 = self.check("Cận màn hình điện thoại hiện bảng xếp hạng Free Fire.\nKELLY: Hạng nhất!")
        self.assertEqual(c2["blocked_scenes"], [])

    def test_game_interface_without_a_phone_is_still_blocked(self):
        c = self.check("Cận giao diện game Free Fire, minimap và bảng xếp hạng.\nMAXIM: Hạng nhất!")
        self.assertEqual(c["blocked_scenes"][0]["scene"], 1)
        c2 = self.check("Kelly nhảy dù xuống, vòng bo thu hẹp.\nKELLY: Đi!")
        self.assertEqual(c2["blocked_scenes"][0]["scene"], 1)                # combat gameplay off the phone: still blocked

    def test_screen_needs_go_into_the_asset_checklist_with_an_estimate(self):
        script = (HEAD + "Cận màn hình điện thoại: huy hiệu hạng Huyền Thoại.\nKELLY: Đỉnh chưa?\n\n"
                  "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nToàn cảnh từ xa, Kelly cúi nhìn điện thoại.\nKELLY: Ơ…")
        self.p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (script, self.pid))
        self.p.conn.commit()
        need = B.screen_needs(self.p.conn, self.pid)
        self.assertEqual([n["scene"] for n in need], [1])
        self.assertGreater(need[0]["est_usd"], 0)
        from core import asset_checklist
        with mock.patch.dict(os.environ, {"FEATURE_ASSET_CHECKLIST": "1"}):
            res = asset_checklist.get(self.p, self.pid)
        row = next(r for r in res["rows"] if r["status"] == "to_create")
        self.assertIn("màn hình", row["status_label"])
        self.assertIn("USD", row["status_label"])
        self.assertEqual(row["scenes"], [1])

    def test_writer_is_told_the_new_screen_rule(self):
        self.assertIn("TỪ XA", B.RULES)
        self.assertIn("màn hình mô phỏng", B.RULES)


if __name__ == "__main__":
    unittest.main()
