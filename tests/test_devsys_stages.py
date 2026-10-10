"""K0a kế hoạch kiểm soát (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.9, N3, N6, N7): hợp đồng của SỔ KHÂU
devsys/stages.json + BẢNG LOẠI LỖI devsys/error_types.json + định dạng ca hồi quy tests/golden/.

Đỏ đúng chỗ thiếu thật nhưng không làm đỏ cả bộ: chỗ thiếu ĐÃ BIẾT phải ghi `dot` (đợt kế hoạch sẽ lấp). Khâu tốn tiền đang chạy mà không có
lớp kiểm trước đang chạy / học việc, hoặc lớp kiểm đọc chữ tự do để kết luận → thiếu `dot` là đỏ. Chạy `-s` để in bảng khâu thiếu kiểm."""
import os
import unittest

from devsys import decisions, stages
from tests import golden

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StagesBookTests(unittest.TestCase):
    def setUp(self):
        self.doc = stages.load_stages()
        self.deci = decisions.load()

    def test_book_has_no_problems(self):
        self.assertEqual(stages.stage_problems(self.doc, self.deci), [])

    def test_every_work_stage_l1_to_l16_is_listed(self):
        got = {stages.base_id(s["id"]) for s in self.doc["stages"]}
        self.assertEqual(got, {f"L{i}" for i in range(1, 17)})
        for sp in ("am_thanh", "phu_de", "dung"):                       # A11: âm / chữ / dựng có dòng riêng
            self.assertIn(sp, {s["san_pham"] for s in self.doc["stages"]})

    def test_code_stages_found_missing_by_the_review_are_now_in_decisions(self):
        wheres = " ".join(d["where"] for d in self.deci["items"])
        for path in ("core/prompt_formula.py", "core/stage_facts.py", "core/before_run.py", "core/stage_solver.py",
                     "tools/render_plates.py", "core/end_popup.py", "core/change_audit.py"):
            self.assertIn(path + ":", wheres)
        self.assertEqual(decisions.broken_wheres(self.deci, ROOT), [])

    def test_paid_stage_without_live_pre_check_needs_a_planned_wave(self):
        bad = {"stages": [dict(s) for s in self.doc["stages"]]}
        l9 = next(s for s in bad["stages"] if s["id"] == "L9")
        l9["dot"] = None
        got = " ".join(stages.stage_problems(bad, self.deci))
        self.assertIn("L9", got)
        self.assertIn("kiểm trước", got)

    def test_a_switched_off_pre_check_does_not_count(self):
        s = {"id": "L99", "ten": "x", "san_pham": "anh", "lam": [], "ton_tien": True, "khau_trang_thai": "chay",
             "kiem_truoc": ["d24"], "trang_thai_kiem": "tat", "kiem_sau": [], "trang_thai_sau": "khong_co", "doc_tu": "ket_qua",
             "nguoi_kiem": True, "dot": None}
        self.assertIn("L99", " ".join(stages.stage_problems({"stages": [s]}, self.deci)))
        self.assertEqual([x["id"] for x in stages.missing_pre_checks({"stages": [s]})], ["L99"])
        s2 = dict(s, khau_trang_thai="tat")                             # khâu không chạy: không đòi đợt
        self.assertEqual(stages.stage_problems({"stages": [s2]}, self.deci), [])

    def test_free_text_reading_needs_a_planned_wave(self):
        s = {"id": "L98", "ten": "x", "san_pham": "chu", "lam": [], "ton_tien": False, "khau_trang_thai": "chay",
             "kiem_truoc": ["d84"], "trang_thai_kiem": "chay", "kiem_sau": [], "trang_thai_sau": "khong_co", "doc_tu": "chu_tu_do",
             "nguoi_kiem": False, "dot": None}
        self.assertIn("chu_tu_do", " ".join(stages.stage_problems({"stages": [s]}, self.deci)))

    def test_unknown_ids_enums_and_inconsistent_states_are_reported(self):
        s = {"id": "L97", "ten": "x", "san_pham": "zz", "lam": ["d999"], "ton_tien": "yes", "khau_trang_thai": "chay",
             "kiem_truoc": [], "trang_thai_kiem": "chay", "kiem_sau": ["nope"], "trang_thai_sau": "??", "doc_tu": "mat_troi",
             "nguoi_kiem": True, "dot": "K99"}
        got = " ".join(stages.stage_problems({"stages": [s]}, self.deci))
        for word in ("d999", "nope", "zz", "ton_tien", "mat_troi", "??", "K99", "khong_co"):
            self.assertIn(word, got)

    def test_summary_table_prints(self):
        rows = stages.summary_rows(self.doc)
        self.assertEqual(len(rows), len(self.doc["stages"]))
        print("\n" + stages.summary_text(self.doc, stages.load_error_types()))


class ErrorTypeTests(unittest.TestCase):
    def setUp(self):
        self.doc = stages.load_error_types()

    def test_every_type_of_section_4_is_listed(self):
        want = {f"L{i}" for i in range(1, 16)} | {f"V{i}" for i in range(1, 5)} | {f"A{i}" for i in range(1, 5)}
        self.assertEqual({t["id"] for t in self.doc["types"]}, want)

    def test_table_has_no_problems(self):
        self.assertEqual(stages.error_type_problems(self.doc, ROOT), [])

    def test_a_product_without_any_check_is_red(self):
        bad = {"san_pham": ["anh", "video", "am_chu"],
               "types": [{"id": "L1", "ten": "x", "ap_dung": ["anh", "video"],
                          "code_do": [{"mo_ta": "m", "trang_thai": "co", "dot": None, "where": "core/qc_measure.py:faces", "san_pham": ["anh"]}],
                          "claude_khai": []}]}
        got = " ".join(stages.error_type_problems(bad, ROOT))
        self.assertIn("video", got)

    def test_building_without_wave_and_missing_where_are_red(self):
        bad = {"san_pham": ["anh"],
               "types": [{"id": "L1", "ten": "x", "ap_dung": ["anh"],
                          "code_do": [{"mo_ta": "m", "trang_thai": "xay", "dot": None, "where": None},
                                      {"mo_ta": "n", "trang_thai": "co", "dot": None, "where": "core/khong_co.py:f"},
                                      {"mo_ta": "o", "trang_thai": "co", "dot": None, "where": "core/qc_measure.py:khong_co_ham"}],
                          "claude_khai": [{"mo_ta": "k", "enum": [], "trang_thai": "gi_do", "dot": None, "where": None}]}]}
        got = " ".join(stages.error_type_problems(bad, ROOT))
        for word in ("dot", "core/khong_co.py", "khong_co_ham", "gi_do", "enum"):
            self.assertIn(word, got)

    def test_only_building_is_counted(self):
        ids = [t["id"] for t in stages.only_building(self.doc)]
        self.assertIn("L14", ids)
        self.assertNotIn("L7", ids)


class GoldenFormatTests(unittest.TestCase):
    def test_cases_follow_the_format(self):
        cases = golden.load_cases()
        self.assertGreaterEqual(len(cases), 8)                         # 8 ca stage_facts gộp từ tests/fixtures (K0a)
        types = [t["id"] for t in stages.load_error_types()["types"]]
        ids = [d["id"] for d in decisions.load()["items"]]
        self.assertEqual([p for c in cases for p in golden.problems(c, types, ids)], [])
        self.assertEqual(len({c["id"] for c in cases}), len(cases))

    def test_format_problems_are_reported(self):
        bad = {"id": "x", "_file": "y.json", "ca_vang_tay": True, "byd": None, "loai_loi": ["L99"], "lop_phai_bat": ["d999"], "ky_vong": {}}
        got = " ".join(golden.problems(bad, ["L1"], ["d85"]))
        for word in ("nguon", "y.json", "L99", "d999", "ca_vang_tay", "ky_vong"):
            self.assertIn(word, got)

    def test_stage_facts_view_keeps_the_old_shape(self):
        c = golden.stage_facts_cases()[0]
        self.assertEqual(set(c), {"name", "source", "stage_camera", "objects", "image_prompt", "expect"})


if __name__ == "__main__":
    unittest.main()
