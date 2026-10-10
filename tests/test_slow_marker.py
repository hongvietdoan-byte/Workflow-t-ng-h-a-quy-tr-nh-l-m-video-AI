"""Nhãn `slow` (conftest.py, người dùng 10/10): danh sách không được cũ, và related_areas báo đúng khi phải chạy nhóm slow."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import glob  # noqa: E402
import re  # noqa: E402

import conftest  # noqa: E402
import related_areas  # noqa: E402

EVERYWHERE = "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(ROOT, "tests", "*.py")))


class SlowListTests(unittest.TestCase):
    def test_every_slow_id_still_exists(self):
        self.assertTrue(conftest.SLOW_TESTS)
        for nid in conftest.SLOW_TESTS:
            parts = nid.split("::")
            path = os.path.join(ROOT, parts[0])
            self.assertTrue(os.path.isfile(path), nid)
            src = open(path, encoding="utf-8").read()
            for name in parts[1:]:
                pat = re.compile(rf"(def|class) {name}\b|import \w+ as {name}\b")     # lớp có thể là tên gán lại khi import
                # tên lớp phải ở chính file; tên hàm có thể kế thừa từ lớp ở file khác (vd editor_review.RunTests ← rough_cut)
                self.assertTrue(pat.search(src) or (name.startswith("test_") and pat.search(EVERYWHERE)), nid)

    def test_ids_are_unique(self):
        self.assertEqual(len(conftest.SLOW_TESTS), len(set(conftest.SLOW_TESTS)))


class RelatedAreasSlowTests(unittest.TestCase):
    A = [{"id": "dung", "code": ["core/editor_*.py"], "tests": ["tests/test_editor_apply.py"]},
         {"id": "kho", "code": ["core/assets.py"], "tests": ["tests/test_assets.py"]}]
    SLOW = ("tests/test_editor_apply.py::ApplyTests::test_x",)

    def test_area_with_slow_test_requires_slow_run(self):
        need = related_areas.slow_needed(["core/editor_apply.py"], {"dung"}, self.A, self.SLOW)
        self.assertEqual(need, ["tests/test_editor_apply.py"])

    def test_area_without_slow_test_does_not(self):
        self.assertEqual(related_areas.slow_needed(["core/assets.py"], {"kho"}, self.A, self.SLOW), [])

    def test_changing_a_slow_test_file_itself_requires_it(self):
        self.assertEqual(related_areas.slow_needed(["tests/test_editor_apply.py"], set(), self.A, self.SLOW),
                         ["tests/test_editor_apply.py"])

    def test_conftest_change_requires_all_slow(self):
        need = related_areas.slow_needed(["conftest.py"], set(), self.A, self.SLOW)
        self.assertEqual(need, ["tests/test_editor_apply.py"])


if __name__ == "__main__":
    unittest.main()
