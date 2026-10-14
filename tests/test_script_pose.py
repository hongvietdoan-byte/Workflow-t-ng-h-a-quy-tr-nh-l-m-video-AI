"""Tư thế BYĐ ↔ chữ kịch bản (core/script_pose, người dùng 14/10). Ca thật: thử D6 #28 shot 3 'đứng sát, núp' → BYĐ quỳ."""
import unittest

from core import script_pose as S

SCRIPT = ("Kelly đứng ở điểm A — chân cầu thang của Tháp Đồng Hồ. Kelly chạy nhanh lên tới điểm B — bậc cao nhất của cầu thang. "
          "Kelly đứng sát, núp ở bên trái bức tường keo, ló ra ngó xem có địch không. Rồi Kelly chạy tiếp 5 bước về bên trái, đặt bom "
          "keo thứ hai, ngồi xuống sau tường, cầm SKORP bằng hai tay, thở ra.")


def shot(action, *poses):
    beats = dict(zip(("bat_dau", "ket_thuc"), ({"tu_the": p} for p in poses)))
    return {"action": action, "byd": {"hanh_dong": [{"ai": "KELLY", **beats}]}}


class ScriptPoseTests(unittest.TestCase):
    def test_hiding_while_standing_written_as_kneel_is_flagged(self):
        got = S.mismatches(SCRIPT, [(3, shot("Kelly núp sát bên trái tường keo thứ nhất, ló đầu ra quan sát", "quy", "quy"))])
        self.assertEqual(len(got), 1)
        self.assertIn("đứng", got[0])
        self.assertIn("quỳ", got[0])

    def test_matching_poses_and_unrelated_shots_pass(self):
        rows = [(3, shot("Kelly núp sát bên trái tường keo thứ nhất, ló đầu ra quan sát", "dung")),
                (4, shot("Kelly chạy nhanh 5 bước sang trái, ném bom keo thứ hai", "dung", "dung")),
                (5, shot("Kelly ngồi thấp xuống sau tường keo thứ hai, hai tay cầm SKORP", "dung", "ngoi")),
                (6, {"action": "Kelly đứng sát tường", "byd": {}})]
        self.assertEqual(S.mismatches(SCRIPT, rows), [])

    def test_unaccented_words_do_not_count(self):
        self.assertEqual(S.script_poses("Kelly dùng bom keo đúng lúc, núp sau tường keo", "Kelly dùng bom keo núp sau tường")[0], [])

    def test_decomposed_accents_still_match(self):
        import unicodedata
        nfd = unicodedata.normalize("NFD", SCRIPT)
        got = S.mismatches(nfd, [(3, shot("Kelly núp sát bên trái tường keo thứ nhất, ló đầu ra quan sát", "quy"))])
        self.assertEqual(len(got), 1)
