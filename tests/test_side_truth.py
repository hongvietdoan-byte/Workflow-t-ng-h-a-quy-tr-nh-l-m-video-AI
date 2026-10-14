"""Trái/phải của nhân vật → trái/phải khung, do code viết (core/side_truth, cờ side_truth, người dùng 14/10).
Ca thật: thử D6 #28/#29 shot 3 — kịch bản "Kelly đứng sát, núp ở bên trái bức tường keo" → Kelly núp sai bên."""
import json
import unittest

from core import side_truth as T
from core.db import connect
from core.pipeline import Pipeline
from tests._flags import flags_on
from tests.test_script_pose import SCRIPT

ACTION = "Kelly núp sát bên trái tường keo thứ nhất, ló đầu ra quan sát"


def shot(**kw):
    return {"action": ACTION, "characters": ["KELLY"], "angle": "eye", **kw}


class SideWordsTests(unittest.TestCase):
    def test_side_words_need_ben_phia_sang_qua_tay(self):
        self.assertEqual(T.mentions("Kelly núp ở bên trái bức tường"), [("bên trái", "left")])
        self.assertEqual(T.mentions("chạy về phía bên phải, rồi sang trái"), [("phía bên phải", "right"), ("sang trái", "left")])
        self.assertEqual(T.mentions("cầm súng tay phải"), [("tay phải", "right")])

    def test_phai_meaning_must_is_never_a_side(self):
        self.assertEqual(T.mentions("Kelly phải núp sau tường keo ngay"), [])
        self.assertEqual(T.mentions("cần phải nhanh, không phải lúc"), [])
        self.assertEqual(T.mentions("ben trai ben phai"), [])            # bỏ dấu: "trai" = con trai — không đoán
        got = T.for_shot("Kelly phải núp sau tường keo ngay.", shot(action="Kelly phải núp sau tường keo", angle="ots"))
        self.assertEqual((got["sentence"], got["warn"]), ("", None))


class ConvertTests(unittest.TestCase):
    def test_camera_behind_keeps_the_side(self):
        got = T.for_shot(SCRIPT, shot(angle="ots", blocking="Kelly back to camera, peeking around the glue wall"))
        self.assertEqual(got["camera"], "behind")
        self.assertIn("'bên trái' (KELLY's left) = FRAME-LEFT", got["sentence"])
        self.assertIsNone(got["warn"])

    def test_camera_in_front_flips_the_side(self):
        got = T.for_shot(SCRIPT, shot(blocking="Kelly facing the camera, pressed against the glue wall"))
        self.assertEqual(got["camera"], "front")
        self.assertIn("'bên trái' (KELLY's left) = FRAME-RIGHT", got["sentence"])

    def test_game_tps_is_behind(self):
        self.assertEqual(T.camera_relation({"size": "GAME_TPS"})[0], "behind")

    def test_unknown_camera_is_yellow_not_a_guess(self):
        got = T.for_shot(SCRIPT, shot(blocking="Kelly hides at the glue wall"))
        self.assertEqual(got["sentence"], "")
        self.assertIn("không quy đổi được", got["warn"])
        self.assertIn("sau lưng hay trước mặt", got["warn"])

    def test_negated_front_and_profile_are_not_known(self):
        self.assertIsNone(T.camera_relation({"blocking": "Kelly never facing the camera"})[0])
        rel, why = T.camera_relation({"blocking": "profile view of Kelly at the wall"})
        self.assertIsNone(rel)
        self.assertIn("ngang hông", why)

    def test_several_characters_is_yellow_unless_the_words_name_one(self):
        two = ["KELLY", "MAXIM"]
        got = T.for_shot("Hai người núp ở bên trái bức tường keo.", shot(action="Hai người núp ở bên trái bức tường keo", characters=two,
                                                                          angle="ots"))
        self.assertEqual(got["sentence"], "")
        self.assertIn("2 nhân vật", got["warn"])
        got = T.for_shot(SCRIPT, shot(characters=two, angle="ots"))     # "Kelly đứng sát, núp ở bên trái…" names Kelly only
        self.assertIn("KELLY's left", got["sentence"])
        got = T.for_shot("Maxim đứng bên trái Kelly ở bức tường.", shot(action="Maxim đứng bên trái Kelly ở bức tường", characters=two,
                                                                         angle="ots"))
        self.assertIn("2 nhân vật", got["warn"])

    def test_director_action_sides_are_not_read(self):
        """#24 shot 12: the Director's 'giếng sau lưng yêu nữ bên phải' is the viewer's right — only the script's words count."""
        got = T.for_shot("Popup quảng cáo hai hành động bật lên giữa màn hình.",
                         shot(action="Kelly đứng cạnh yêu nữ, nhìn thẳng vào máy. Giếng sau lưng yêu nữ bên phải",
                              blocking="both facing the camera"))
        self.assertEqual((got["sentence"], got["warn"], got["mentions"]), ("", None, []))

    def test_no_side_word_says_nothing(self):
        got = T.for_shot(SCRIPT, {"action": "Kelly chạy nhanh lên tới điểm B", "characters": ["KELLY"], "angle": "ots"})
        self.assertEqual((got["sentence"], got["warn"]), ("", None))


class RewriteKeepsTests(unittest.TestCase):
    def setUp(self):
        self.line = T.sentence("KELLY", "front", [("bên trái", "left")])
        self.assembled = "Kelly hides at the glue wall. " + self.line

    def test_rewrite_that_lost_the_side_gets_it_back(self):
        out = T.kept_after_rewrite(self.assembled, "Kelly hides at the left of the glue wall.")
        self.assertTrue(out.endswith(self.line))

    def test_rewrite_that_kept_frame_words_is_untouched(self):
        new = "Kelly hides on frame-right of the glue wall."
        self.assertEqual(T.kept_after_rewrite(self.assembled, new), new)

    def test_past_the_limit_falls_back_to_the_assembled_prompt(self):
        self.assertEqual(T.kept_after_rewrite(self.assembled, "x" * 90, limit=100), self.assembled)


class _Runner:
    def __init__(self, p):
        self.p, self.said = p, []

    def _diag_once(self, job, sev, code, msg):
        self.said.append((sev, code, msg))


class RunnerSentenceTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("thử trái phải")
        self.p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (SCRIPT, self.pid))
        self.sid = self.p.create_scene(self.pid, 1, "CẢNH 1 · shot 3")

    def _data(self, data):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.sid))

    def test_flag_off_adds_nothing(self):
        from core import runner
        self._data(shot(angle="ots"))
        flags_on(self, T.FLAG, value=False)
        self.assertEqual(runner._side_truth(_Runner(self.p), {"scene_id": self.sid, "project_id": self.pid}), "")

    def test_flag_on_gives_the_sentence_and_says_it(self):
        from core import runner
        self._data(shot(angle="ots"))
        flags_on(self, T.FLAG)
        r = _Runner(self.p)
        line = runner._side_truth(r, {"scene_id": self.sid, "project_id": self.pid})
        self.assertIn("FRAME-LEFT", line)
        self.assertEqual(r.said[0][:2], ("info", "side_truth"))

    def test_flag_on_unknown_camera_is_said_yellow(self):
        from core import runner
        self._data(shot(blocking="Kelly hides at the glue wall"))
        flags_on(self, T.FLAG)
        r = _Runner(self.p)
        self.assertEqual(runner._side_truth(r, {"scene_id": self.sid, "project_id": self.pid}), "")
        self.assertEqual(r.said[0][:2], ("warn", "side_truth"))
