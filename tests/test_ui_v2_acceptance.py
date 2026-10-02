"""S13.10: nghiệm thu giao diện v2 bằng số (tools/ui_v2_acceptance.py) chạy như test — click không nhiều hơn bản cũ, không mất khóa điều khiển.
Hiệu năng (perf) không đặt vào test vì phụ thuộc máy; chạy tay: py tools/ui_v2_acceptance.py perf."""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import ui_v2_acceptance as U  # noqa: E402

# khóa cũ được chủ ý đổi tên / bỏ trong v2 (kèm lý do) — danh sách này chỉ được dài thêm khi có quyết định rõ
RENAMED = {
    "retry_{}": "storyboard_cards.py: nút '↻ Vẽ lại' của ảnh lỗi dùng dretry_{} (cùng p.retry) — khóa cũ chỉ còn ở giao diện cũ",
    "inbox_kind": "header.inbox_card: bộ lọc loại việc chỉ hiện khi hộp thư > 3 việc (INBOX_SHOWN)",
    "fold_refs_{}_btn": "v2 thay thẻ gập 'Tham chiếu' bằng khối luôn mở (inputs_and_refs_v2)",
    "fold_script_{}_btn": "v2 thay thẻ gập 'Kịch bản' bằng thẻ ① + expander 'Nhập / thay kịch bản'",
}


def _git_has(rev: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", rev], cwd=U.ROOT, capture_output=True).returncode == 0


class AcceptanceTests(unittest.TestCase):
    @unittest.skipUnless(_git_has(U.BASE_REV), "không có lịch sử git tới " + U.BASE_REV)
    def test_no_widget_key_pattern_lost_in_source(self):
        old, new = U.static_keys(U.BASE_REV), U.static_keys("HEAD")
        self.assertEqual(sorted(set(old) - set(new)), [], "khóa key= trong mã nguồn bị mất so với bản cũ")

    def test_click_count_new_project_to_first_video_not_more_than_old(self):
        old, new = U.child("clicks", "0"), U.child("clicks", "1")
        self.assertTrue(old["ok"], old)
        self.assertTrue(new["ok"], new)
        self.assertLessEqual(new["clicks"], old["clicks"])

    def test_dynamic_keys_only_documented_renames_missing(self):
        old, new = U.child("keys", "0"), U.child("keys", "1")
        lost = set()
        for screen in old:
            lost |= {k for _, k in old[screen]} - {k for _, k in new.get(screen, [])}
        import re
        undocumented = sorted(k for k in lost if re.sub(r"\d+", "{}", k) not in RENAMED and not re.sub(r"_\d+", "_{}", k) in RENAMED)
        self.assertEqual(undocumented, [], "khóa widget cũ biến mất ở v2 mà chưa có lý do trong RENAMED")


if __name__ == "__main__":
    unittest.main()
