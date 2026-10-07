"""Bố cục khung hẹp (người dùng 07/10, điểm 4: 'khung xem hẹp/cao thì bố cục vỡ — chữ tí hon, cột lệch'). Chụp màn thật 640 / 900 px:
thanh trên cắt chữ ('Khủng Lon', '⚙ C…'), 3 thẻ clip chen một hàng ở 900 px. Sửa: thanh trên xuống dòng; lưới thẻ 2 thẻ/hàng dưới
1100 px; lưới Video xếp THEO HÀNG (trước theo cột: xuống dòng sẽ đảo thứ tự cảnh 1, 4, 7 / 2, 5, 8)."""
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


class NarrowTests(unittest.TestCase):
    def test_the_theme_wraps_the_top_bar_and_the_card_grids_on_narrow_screens(self):
        css = read("dashboard", "design", "theme.css")
        block = re.search(r"@media \(max-width: 1100px\) \{(.*?)\n\}", css, re.S)
        self.assertIsNotNone(block, "no narrow-screen block")
        for sel in (".st-key-shell-bar", ".st-key-vid-grid", ".st-key-sb-grid"):
            self.assertIn(sel, block.group(1))
        self.assertIn("flex-wrap: wrap", block.group(1))

    def test_the_containers_carry_the_keys(self):
        self.assertIn('st.container(key="shell-bar")', read("dashboard", "header.py"))          # the v2 top bar (already keyed)
        self.assertIn('key="vid-grid"', read("dashboard", "steps", "step4.py"))
        self.assertIn('key="sb-grid"', read("dashboard", "steps", "step2.py"))

    def test_the_video_grid_is_built_row_by_row(self):
        src = read("dashboard", "steps", "step4.py")
        self.assertNotIn("with cols[n % 3]:", src)


if __name__ == "__main__":
    unittest.main()
