"""H3 + H7 (kế hoạch 2026-09-25): each role's principles are a way of thinking, not a list of orders — the structure is checked, not the
length (the person asked for no hard cap on the number of rules)."""
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..", "knowledge")
ROLES = {"director": os.path.join(ROOT, "roles", "director.md"), "dp": os.path.join(ROOT, "roles", "dp.md"),
         "editor": os.path.join(ROOT, "editor", "editing.md")}


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class RoleKnowledgeTests(unittest.TestCase):
    def test_every_role_has_the_five_layers(self):
        for role, path in ROLES.items():
            text = _read(path)
            for n in range(1, 6):
                self.assertRegex(text, rf"## Tầng {n} —", f"{role}: thiếu tầng {n}")

    def test_the_director_carries_the_agreed_priority_order_and_tradeoffs(self):
        whole = _read(ROLES["director"])
        text = whole[whole.index("## Tầng 4"):whole.index("## Tầng 5")]
        order = ["Mạch truyện & cảm xúc", "Thoại nguyên văn + cặp đối đáp", "Góc máy kịch bản ghi", "Thời lượng kịch bản",
                 "Tiết kiệm tiền video", "Phong cách dựng"]
        pos = [text.find(x) for x in order]
        self.assertTrue(all(p >= 0 for p in pos), pos)
        self.assertEqual(pos, sorted(pos))                    # người dùng chốt thứ tự này 2026-09-25
        self.assertIn("tradeoffs", text)

    def test_director_rules_give_a_reason_and_evidence(self):
        text = _read(ROLES["director"])
        for block in re.findall(r"### N\d\..*?(?=\n### |\n## )", text, re.S):
            self.assertTrue("Vì sao" in block or "Căn cứ" in block, block[:60])

    def test_safe_zone_numbers_name_their_source(self):
        text = _read(os.path.join(ROOT, "editor", "safe_zones.md"))
        self.assertIn("Meta Ads Guide", text)
        self.assertIn("tin cậy", text)


if __name__ == "__main__":
    unittest.main()
