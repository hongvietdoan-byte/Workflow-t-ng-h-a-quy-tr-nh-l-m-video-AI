"""#24 (08/10): clip nhóm shot 5–7 và 8–9 bị chặn trước khi gửi (0 USD):
  - "prompt còn chữ tiếng Việt" — tên nhân vật "YÊU NỮ TÀ LINH DẠNG 1" vào nguyên văn câu "Image N is …" dù mọi trường Director đã dịch;
  - "prompt dài 4135 ký tự > 4000" — ước lượng khi gộp nhóm (2 923) bỏ sót câu PLACE render của nền 3D.
Nay: tên không dấu trong prompt (thoại giữ nguyên tiếng Việt), ước lượng tính dư câu nền."""
import unittest

from core import seedance_refs as s


class VietnameseNameTests(unittest.TestCase):
    def test_ascii_name(self):
        self.assertEqual(s.ascii_name("YÊU NỮ TÀ LINH DẠNG 1"), "YEU NU TA LINH DANG 1")
        self.assertEqual(s.ascii_name("Đạo sĩ"), "Dao si")
        self.assertEqual(s.ascii_name("KELLY"), "KELLY")

    def test_prompt_has_no_vietnamese_from_names(self):
        parts = [("KELLY sits on the ground; YÊU NỮ TÀ LINH DẠNG 1 climbs over the well rim", 3.0),
                 ("Yêu nữ tà linh dạng 1 crawls toward the camera", 3.0)]
        ids = [("KELLY", "a.png"), ("YÊU NỮ TÀ LINH DẠNG 1", "b.png"), ("YÊU NỮ TÀ LINH DẠNG 2 OUTFIT", "c.png")]
        text = s.prompt(parts, ids, places=[{"shots": [1]}])
        self.assertFalse(s.has_vietnamese(text), text)
        self.assertIn("Image 4 is YEU NU TA LINH DANG 1: identity only", text)
        self.assertIn("YEU NU TA LINH DANG 1 climbs", text)
        self.assertIn("Yeu nu ta linh dang 1 crawls", text)
        self.assertIn("the OUTFIT YEU NU TA LINH DANG 2 wears", text)
        self.assertEqual(s.lint_group(text, 2, 6, 6, [3.0, 3.0], False), [])

    def test_spoken_lines_stay_vietnamese(self):
        parts = [('LÝ speaks. Dialogue (LÝ): "Cứu tôi với"', 3.0)]
        text = s.prompt(parts, [("LÝ", "a.png")])
        self.assertIn('Dialogue (LÝ): "Cứu tôi với"', text)
        self.assertIn("Image 2 is LY: identity only", text)
        self.assertEqual(s.lint_group(text, 1, 2, 2, [3.0], False), [])


class GroupLengthTests(unittest.TestCase):
    def rows(self, n):
        motion = "medium shot, low angle, camera crane: " + "the creature climbs over the rim of the ancient stone well " * 6
        return [{"id": i, "data": {"characters": ["KELLY", "YÊU NỮ TÀ LINH DẠNG 1"], "action": motion, "duration_s": 3.0}}
                for i in range(1, n + 1)]

    def test_estimate_counts_the_place_sentences(self):
        rows = self.rows(3)
        with_places = s._estimated_len(rows)
        without = len(s.prompt([(s.shot_motion(r["data"]), 3.0) for r in rows], [("KELLY", ""), ("YÊU NỮ TÀ LINH DẠNG 1", "")]))
        self.assertGreater(with_places, without + 3 * 250)       # ~330 characters per rendered shot
