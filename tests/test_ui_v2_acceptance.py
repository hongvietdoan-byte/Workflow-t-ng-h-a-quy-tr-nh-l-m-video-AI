"""S13.10: nghiệm thu giao diện v2 bằng số (tools/ui_v2_acceptance.py) chạy như test — click không nhiều hơn bản cũ, không mất khóa điều khiển.
Hiệu năng (perf) không đặt vào test vì phụ thuộc máy; chạy tay: py tools/ui_v2_acceptance.py perf."""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import ui_v2_acceptance as U  # noqa: E402

RENAMED = U.RENAMED     # S14.8 U6: bảng khóa đổi tên có chủ ý nằm ở tools/ui_v2_acceptance.py (công cụ + test + devsys dùng chung)


def _git_has(rev: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", rev], cwd=U.ROOT, capture_output=True).returncode == 0


class AcceptanceTests(unittest.TestCase):
    @unittest.skipUnless(_git_has(U.BASE_REV), "không có lịch sử git tới " + U.BASE_REV)
    def test_no_widget_key_pattern_lost_in_source(self):
        old, new = U.static_keys(U.BASE_REV), U.static_keys("HEAD")
        self.assertEqual(sorted(set(old) - set(new)), [], "khóa key= trong mã nguồn bị mất so với bản cũ")

    def test_click_count_new_project_to_first_video_not_more_than_old(self):
        # S14.14 G-a: the Kịch bản screen has no old layout any more, so a FEATURE_UI_V2=0 run is no longer "the old one" — compare with
        # the old screen's number measured just before G-a (U.OLD_CLICKS_BASELINE), and still with whatever =0 draws today
        old, new = U.child("clicks", "0"), U.child("clicks", "1")
        self.assertTrue(old["ok"], old)
        self.assertTrue(new["ok"], new)
        self.assertLessEqual(new["clicks"], U.OLD_CLICKS_BASELINE)
        self.assertLessEqual(new["clicks"], old["clicks"])

    def test_dynamic_keys_only_documented_renames_missing(self):
        old, new = U.child("keys", "0"), U.child("keys", "1")
        lost = set()
        for screen in old:
            lost |= {k for _, k in old[screen]} - {k for _, k in new.get(screen, [])}
        self.assertEqual(U.unexplained(lost), [], "khóa widget cũ biến mất ở v2 mà chưa có lý do trong RENAMED")

    def test_renamed_table_explains_only_its_own_patterns(self):
        """S14.8 U6/U8: khóa mất có lý do trong RENAMED không tính là mất; khóa khác vẫn bị báo."""
        self.assertIn("retry_{}", U.RENAMED)
        self.assertEqual(U.unexplained({"retry_5", "fold_refs_3_btn", "inbox_kind", "new_thing_2"}), ["new_thing_2"])
        self.assertEqual(U.explained({"retry_5", "x"}), ["retry_5"])


if __name__ == "__main__":
    unittest.main()
