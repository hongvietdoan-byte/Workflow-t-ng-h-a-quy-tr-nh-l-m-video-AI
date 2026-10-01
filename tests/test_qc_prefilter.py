"""Lọc trước bộ độc lập (tools/experiments/qc_prefilter.py): nguồn ghi chú, loại lỗi theo ghi chú, nhãn gợi ý — 0 USD."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "experiments"))
import qc_prefilter as q  # noqa: E402


def hist(*reviews):
    return {"reviews": [{"by": by, "decision": d, "source": q.source_of(n) if by == "user" else "agent", "note": n}
                        for by, d, n in reviews], "qc_low": [], "moderation": 0}


class SourceAndCategory(unittest.TestCase):
    def test_source(self):
        self.assertEqual(q.source_of("[thử tự động] Draw the place"), "thử tự động")
        self.assertEqual(q.source_of("duyệt bởi phiên vận hành chạy thử 2A"), "phiên vận hành")
        self.assertEqual(q.source_of("Đồng bộ cả bộ: Kelly must wear"), "người bấm theo QC đồng bộ")
        self.assertEqual(q.source_of("tháp chưa giống Free Fire"), "người")

    def test_category_earliest_words_win(self):
        self.assertEqual(q.category_of_note("Kelly and Maxim gaze up and to the right instead of at the crate; hair ok"),
                         "Hướng nhìn / diễn xuất")
        self.assertEqual(q.category_of_note("tháp chưa giống Free Fire — gen lại với ảnh mốc"), "Bối cảnh / kiến trúc")
        self.assertEqual(q.category_of_note("Show the real night background, never a plain black void."), "Liền mạch / ánh sáng")
        self.assertEqual(q.category_of_note("Đồng bộ cả bộ: Re-render in the same semi-realistic cinematic style, Kenta has a topknot"),
                         "Kỹ thuật")

    def test_keep_clause_is_not_the_fault(self):
        self.assertEqual(q.category_of_note("Đồng bộ cả bộ: Keep the exact composition, lighting and wall. Redraw Kelly with a bob."),
                         "Nhân vật")

    def test_set_note_without_a_named_fault(self):
        self.assertEqual(q.category_of_note("Đồng bộ cả bộ: Eye-level medium shot of Kenta behind the wall in bright daylight."), "Khác")


class Suggest(unittest.TestCase):
    f = {"state": "rejected"}

    def test_person_reject_is_block_high(self):
        label, cat, _, conf = q.suggest(self.f, [], hist(("user", "reject", "tháp chưa giống Free Fire")))
        self.assertEqual((label, cat, conf), ("Chặn", "Bối cảnh / kiến trúc", "cao"))

    def test_planned_retake_is_not_a_defect(self):
        label, _, _, _ = q.suggest(self.f, [], hist(("user", "reject", "gen lại có chủ đích (phiên vận hành)")))
        self.assertEqual(label, "")

    def test_reject_then_approve_follows_the_last_decision(self):
        label, _, _, conf = q.suggest({"state": "approved"}, [], hist(("user", "reject", "Show the real night background"),
                                                                      ("user", "approve", "ok")))
        self.assertEqual((label, conf), ("Đạt", "vừa"))

    def test_sure_code_finding_wins(self):
        flag = {"kind": "blank", "sure": True, "category": "Kỹ thuật", "text": "khung gần như một màu"}
        label, cat, _, conf = q.suggest({"state": "approved"}, [flag], hist(("user", "approve", "ok")))
        self.assertEqual((label, cat, conf), ("Chặn", "Kỹ thuật", "cao"))

    def test_approved_with_a_doubt_flag_stays_open(self):
        flag = {"kind": "extra_faces", "sure": False, "category": "Nhân vật", "text": "3 mặt, bảng shot 1 người"}
        label, cat, _, _ = q.suggest({"state": "approved"}, [flag], hist(("user", "approve", "ok")))
        self.assertEqual((label, cat), ("", "Nhân vật"))

    def test_old_automatic_qc_is_the_weakest_hint(self):
        label, cat, _, conf = q.suggest(self.f, [], hist(("ai_agent", "reject", "QC 0.53 < 0.85 — Kelly is completely missing")))
        self.assertEqual((label, cat, conf), ("Chặn", "Nhân vật", "thấp"))
        label, _, _, conf = q.suggest({"state": "approved"}, [], hist(("ai_agent", "approve", "autopilot")))
        self.assertEqual((label, conf), ("Đạt", "thấp"))


if __name__ == "__main__":
    unittest.main()
