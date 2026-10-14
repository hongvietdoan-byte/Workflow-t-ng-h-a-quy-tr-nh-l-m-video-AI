"""Tư thế BYĐ ↔ chữ kịch bản (core/script_pose, người dùng 14/10). Ca thật: thử D6 #28 shot 3 'đứng sát, núp' → BYĐ quỳ."""
import json
import os
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


SHOT3 = "Kelly núp sát bên trái tường keo thứ nhất, ló đầu ra quan sát"


class FixStandingTests(unittest.TestCase):
    def test_script_standing_byd_kneeling_is_fixed_to_standing(self):
        data = shot(SHOT3, "quy", "quy")
        data["byd"]["hanh_dong"][0]["bat_dau"]["cham_dat"] = ["dau_goi"]
        data["image_prompt"] = "Kelly crouching behind the glue wall"
        got = S.fix_standing(SCRIPT, [(3, data)])
        self.assertEqual(len(got), 1)
        self.assertIn("code đổi BYĐ thành đứng", got[0])
        self.assertIn("crouching", got[0])                      # the Director's English words are pointed at, not silently left
        self.assertEqual(S.byd_poses(data), ["dung", "dung"])
        self.assertEqual(data["byd"]["hanh_dong"][0]["bat_dau"]["cham_dat"], ["ban_chan"])
        self.assertIn("sua_tu_the", data["byd"]["hanh_dong"][0])
        self.assertEqual(S.mismatches(SCRIPT, [(3, data)]), [])

    def test_ambiguous_cases_are_left_yellow(self):
        cases = [
            ("Kelly đứng dậy, núp ở bên trái bức tường keo, ló ra ngó xem có địch không.", shot(SHOT3, "ngoi")),   # a change of pose
            (SCRIPT, shot(SHOT3, "nga_ngua")),                                                                    # a fall may be meant
            (SCRIPT, {"action": SHOT3, "byd": {"hanh_dong": [{"ai": "KELLY", "bat_dau": {"tu_the": "quy"}},
                                                             {"ai": "MAXIM", "bat_dau": {"tu_the": "quy"}}]}}),  # whose pose?
        ]
        for script, data in cases:
            with self.subTest(script=script[:30], byd=data["byd"]):
                before = json.dumps(data, sort_keys=True)
                self.assertEqual(S.fix_standing(script, [(3, data)]), [])
                self.assertEqual(json.dumps(data, sort_keys=True), before)

    def test_hand_locked_byd_is_never_changed(self):
        data = dict(shot(SHOT3, "quy"), _user_locked=["byd"])
        self.assertEqual(S.fix_standing(SCRIPT, [(3, data)]), [])
        self.assertEqual(S.byd_poses(data), ["quy"])
        self.assertEqual(len(S.mismatches(SCRIPT, [(3, data)])), 1)     # still said VÀNG

    def test_p24_fixture_shots_are_not_changed(self):
        here = os.path.join(os.path.dirname(__file__), "fixtures")
        script = open(os.path.join(here, "p24_script.txt"), encoding="utf-8").read()
        obj = json.load(open(os.path.join(here, "director_p24_shots.json"), encoding="utf-8"))
        rows = [(k, s) for sc in obj["scenes"] for k, s in enumerate(sc["shots"], 1)]
        self.assertEqual(S.fix_standing(script, rows), [])


class StoreFixTests(unittest.TestCase):
    def setUp(self):
        from core.db import connect
        from core.pipeline import Pipeline
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("thử tư thế")
        self.p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (SCRIPT, self.pid))
        self.sid = self.p.create_scene(self.pid, 1, "CẢNH 1 · shot 3")

    def _run(self, data, on=True):
        from core import llm_io
        from tests._flags import flags_on
        flags_on(self, S.FIX_FLAG, value=on)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.sid))
        llm_io._script_pose_fix(self.p.conn, self.pid)
        saved = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"])
        codes = [r[0] for r in self.p.conn.execute("SELECT code FROM diag_events WHERE project_id=?", (self.pid,))]
        return saved, codes

    def test_flag_on_saves_the_fix_and_says_it(self):
        saved, codes = self._run(shot(SHOT3, "quy", "quy"))
        self.assertEqual(S.byd_poses(saved), ["dung", "dung"])
        self.assertIn("script_pose_fix", codes)

    def test_flag_off_changes_nothing(self):
        saved, codes = self._run(shot(SHOT3, "quy", "quy"), on=False)
        self.assertEqual(S.byd_poses(saved), ["quy", "quy"])
        self.assertNotIn("script_pose_fix", codes)
