"""F1-D (09/10/2026): prompt Đạo diễn / Quay phim / motion / viết lại có các ý bắt buộc của công thức prompt
(docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md, knowledge/formula/) — để Đạo diễn viết đúng từ đầu, không bị core/prompt_formula chặn gửi.
Kiểm theo từ khóa (ý), không kiểm nguyên câu; và giữ prompt gọn (Đạo diễn tính tiền theo token)."""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class DirectorPromptFormulaTest(unittest.TestCase):
    def test_shot_prompt_has_formula_section(self):
        t = _read("prompts/17_director_shots.md")
        self.assertIn("Công thức prompt ảnh", t)
        self.assertIn("knowledge/formula/", t)
        for k in ("GỢI", "out of focus", "everything in focus",            # luật cứng FF: chi tiết ghê chỉ gợi
                  "never touches", "pass through",                          # vật gần người: đường đi + không chạm
                  "hồ sơ Kho",                                              # trang phục một nguồn
                  "không phải người",                                       # luật người không áp cho quái
                  "khớp tư thế",                                            # cỡ cảnh ↔ tư thế
                  "trồng thêm", "~20 %",                                    # viết lại, không trồng thêm
                  "#22", "#24"):                                            # có bằng chứng, không lệnh trần
            self.assertIn(k, t, k)

    def test_intent_and_scene_prompts_point_to_formula(self):
        for rel in ("prompts/19_director_intent.md", "prompts/01_director_scene_analysis.md"):
            t = _read(rel)
            self.assertIn("knowledge/formula/", t, rel)
            self.assertIn("hồ sơ Kho", t, rel)
            self.assertIn("gợi", t, rel)
        self.assertIn("không phải người", _read("prompts/19_director_intent.md"))
        self.assertIn("never", _read("prompts/01_director_scene_analysis.md"))
        self.assertIn("Công thức prompt ảnh", _read("prompts/20_dp_scene_shots.md"))

    def test_rewrite_prompt_replaces_not_appends(self):
        t = _read("prompts/26_director_rewrite.md")
        for k in ("Viết lại, không trồng thêm", "thay hoặc bỏ", "~20 %", "chặn gửi gen", "never touches", "hồ sơ Kho", "in shadow"):
            self.assertIn(k, t, k)

    def test_motion_prompt_order_and_special_parts(self):
        t = _read("prompts/03_video_motion.md")
        for k in ("knowledge/formula/motion.md", "The clip starts exactly", "chân không trượt", "It ends with",
                  "chỉ-ảnh-tham-chiếu", "never touches", "does not pass through", "Quái/ma/thú", "chỉ gợi"):
            self.assertIn(k, t, k)

    def test_role_books_match(self):
        d = _read("knowledge/roles/director.md")
        self.assertIn("N6. Bài học theo 3 tầng", d)
        self.assertIn("không trồng thêm", d)
        p = _read("knowledge/roles/dp.md")
        self.assertIn("ảnh toàn cùng trục", p)
        self.assertIn("ngửa trời", p)
        self.assertIn("hồ sơ Kho", p)

    def test_prompts_stay_lean(self):
        # số ký tự trước F1-D (main 374e2f6) — mỗi file tăng ≤ ~16 % (Đạo diễn #24 tốn 0,47 USD; prompt dài = tiền mỗi lượt)
        before = {"prompts/17_director_shots.md": 23536, "prompts/19_director_intent.md": 14650,
                  "prompts/01_director_scene_analysis.md": 9869, "prompts/03_video_motion.md": 5018,
                  "prompts/26_director_rewrite.md": 2686, "prompts/20_dp_scene_shots.md": 5006}
        for rel, n in before.items():
            self.assertLessEqual(len(_read(rel)), n * 1.16, rel)


if __name__ == "__main__":
    unittest.main()
