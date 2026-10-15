"""#31 (15/10) — hai việc mở sau Đạo diễn hai lượt, kiểm bằng câu THẬT của #31 (0 USD, không gọi model).

1. prompt_formula ĐỎ 5 shot vì chữ ghê không có câu gợi: (a) 'blood stains' chép từ hồ sơ trang phục (cảnh 4·1, 8·2), (b) vật kịch bản
   bắt buộc 'corpse' (6·1, 6·2), (c) 'glow … bleeds in' là ánh sáng loang, KHÔNG phải máu (5·2 — bộ từ ghê đọc nhầm).
   Sửa công thức: khuôn Quay phim nói rõ ba ca + câu gợi mẫu; thông báo đỏ chỉ cách sửa cụ thể; 'bleed' của ánh sáng không là ghê.
   Ngưỡng không đổi: 'blood stains' / 'corpse' không câu gợi vẫn ĐỎ.
2. BYĐ cảnh 8 shot 1–4 'shot: thiếu trường bắt buộc' sau 2 vòng sửa: khuôn trả lời của lượt sửa đặt số shot NGOÀI khối byd
   ({"canh", "shot", "byd": {…}}) nên Đạo diễn bỏ `shot` trong byd — code không lấy số đó vào → hai vòng trả tiền không lấp được.
"""
import json
import os
import unittest
from unittest import mock

from core import director_byd, llm_runner, looks, prompt_formula as pf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# câu thật #31 (data/manifest.sqlite, scenes 325 / 327 / 334 — rút gọn phần không liên quan)
P31_5_2 = ("Medium-long shot (knees-up), eye-level, camera tracking backward just ahead of Kelly as she walks toward door 2. "
           "Purple-red glow from door 1 bleeds in at the frame-left edge behind her. Determined expression, eyes fixed ahead. "
           "Free Fire in-game 3D render, stylized proportions, moderate texture detail, clear gameplay lighting, everything in focus.")
P31_6_1 = ("Free Fire in-game 3D render, everything in focus. Wide shot, low angle looking slightly upward. Kelly in her ghost form "
           "standing on misty ground frame-left looking up. A gaunt black humanoid corpse floats motionless in mid-air frame-right, "
           "entirely black silhouette, a faint dim red light column glowing softly behind it.")
P31_8_2 = ("Free Fire in-game 3D render, medium shot, over-the-shoulder angle behind Kelly; Sứ giả bóng đêm frame-center (cracked "
           "gray mask with red eyes, black felt hat, white-gray dirty long coat with blood stains, metal claws, laughing); everything "
           "in focus")


def _red_ff(text):
    return [i for i in pf._common(text, {}, None, "ảnh", ff=True) if i["part"] == "luat_ff" and i["level"] == "red"]


class GoreWordsTest(unittest.TestCase):
    def test_light_bleed_is_not_gore(self):
        self.assertEqual(looks.gore_words(P31_5_2), [])
        self.assertEqual(looks.gore_words("red light bleeding through the cracks of the door"), [])
        self.assertEqual(_red_ff(P31_5_2), [])

    def test_body_bleed_and_real_gore_still_red(self):
        self.assertEqual(looks.gore_words("the wound bleeds under the red glow"), ["wound", "bleeds"])
        self.assertEqual(looks.gore_words("his arm bleeds"), ["bleeds"])
        # rà 15/10: chỉ bỏ qua khi từ ánh sáng là chủ ngữ sát trước VÀ ngay sau là in/into/through/…
        self.assertEqual(looks.gore_words("The neon-lit soldier bleeds from his arm"), ["bleeds"])
        self.assertEqual(looks.gore_words("Kelly stands in the moonlight and her arm bleeds"), ["bleeds"])
        self.assertEqual(looks.gore_words("In the glow of the fire the man bleeds heavily"), ["bleeds"])
        hits = [m.start() for m in looks._gore_iter("glow bleeding into the bleeding man")]
        self.assertEqual(hits, ["glow bleeding into the bleeding man".rindex("bleeding")])   # chữ thứ 2
        self.assertEqual(looks.gore_words("glow from door 1 bleeds in"), [])
        self.assertTrue(_red_ff(P31_6_1))              # ngưỡng không đổi: xác không câu gợi vẫn ĐỎ
        self.assertTrue(_red_ff(P31_8_2))              # vết máu trên áo hồ sơ cũng ĐỎ

    def test_red_message_says_how_to_fix(self):
        msg = _red_ff(P31_8_2)[0]["msg"]
        self.assertIn("only hinted", msg)
        self.assertIn("except", msg)                   # 'everything in focus' → '… except the hinted …'
        self.assertIn("hồ sơ trang phục", msg)
        self.assertIn("spills", msg)

    def test_suggested_sentence_clears_the_red(self):
        fixed = P31_6_1.replace("everything in focus", "everything in focus except the hinted corpse") + \
            " The corpse is only hinted — a featureless dark silhouette, partly hidden in fog, out of focus."
        self.assertEqual(_red_ff(fixed), [])


class DpFormulaTextTest(unittest.TestCase):
    def _read(self, rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()

    def test_shot_rules_cover_costume_story_object_and_light(self):
        t = self._read("prompts/17_director_shots.md")
        for k in ("hồ sơ trang phục", "#31", "only hinted", "except the hinted", "spills"):
            self.assertIn(k, t, k)

    def test_dp_head_prompt_points_to_the_rule(self):
        t = self._read("prompts/20_dp_scene_shots.md")
        for k in ("câu gợi", "#31", "spills"):
            self.assertIn(k, t, k)


class _Fake:
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def complete(self, prompt, images=()):
        self.calls += 1
        return llm_runner.LlmReply(json.dumps(self.answer(prompt), ensure_ascii=False), 10, 10)


def _byd(shot=None, co="MS"):
    b = {"thanh_phan": [{"vat": "KELLY", "vai": "chinh"}], "may": {"co": co, "do_cao": "ngang", "goc": "ngang",
                                                                    "chuyen_dong": "dung_yen"},
         "noi_chon": {"kho_id": None, "thoi_gian": "day", "thoi_tiet": "clear"}}
    if shot is not None:
        b["shot"] = shot
    return b


class BydShotNumberTest(unittest.TestCase):
    def setUp(self):
        from tests.test_director_byd import _project, KHO
        self.p, self.pid = _project()
        self.kho = KHO
        self.env = mock.patch.dict(os.environ, {"FEATURE_SHOT_INTENT": "1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.p.conn.close()

    def _obj(self, bydlist):
        for b in bydlist:
            b["noi_chon"]["kho_id"] = self.kho
        return {"scenes": [{"idx": 8, "shots": [{"characters": ["KELLY"], "byd": b} for b in bydlist]}]}

    def test_missing_number_is_taken_from_position_no_paid_round(self):
        obj = self._obj([_byd(), _byd()])
        client = _Fake(lambda p: {"byd": []})
        summary = director_byd.settle(self.p.conn, self.pid, obj, client)
        self.assertEqual(client.calls, 0)
        self.assertEqual([s["byd"]["shot"] for s in obj["scenes"][0]["shots"]], [1, 2])
        self.assertEqual(summary["vang_do"], 0)
        self.assertEqual(summary["so_shot_theo_vi_tri"], 2)

    def test_saved_shot_no_wins_over_position(self):
        # tools/byd_fill gửi một phần shot của cảnh: vị trí trong danh sách gửi không phải số shot — hàng đã lưu có shot_no
        obj = self._obj([_byd()])
        obj["scenes"][0]["shots"][0]["shot_no"] = 3
        director_byd.settle(self.p.conn, self.pid, obj, _Fake(lambda p: {"byd": []}))
        self.assertEqual(obj["scenes"][0]["shots"][0]["byd"]["shot"], 3)

    def test_repair_answer_without_inner_number_is_settled(self):
        # #31 cảnh 8: byd hỏng (enum sai) → lượt sửa trả {"canh", "shot", "byd": {…}} không có `shot` trong byd
        obj = self._obj([_byd(shot=1, co="NOPE")])

        def answer(prompt):
            good = _byd()
            good["noi_chon"]["kho_id"] = self.kho
            return {"byd": [{"canh": 8, "shot": 1, "byd": good}]}
        client = _Fake(answer)
        summary = director_byd.settle(self.p.conn, self.pid, obj, client)
        self.assertEqual(client.calls, 1)
        self.assertEqual(summary["vang_do"], 0)
        self.assertEqual(obj["scenes"][0]["shots"][0]["byd"]["shot"], 1)

    def test_repair_prompt_shows_number_inside_byd(self):
        text = director_byd.build_repair_prompt([(8, 1, {"byd": _byd()}, [{"truong": "may.co", "loi": "x"}])], 1)
        self.assertIn('"byd": {"shot": <số shot>', text)

    def test_repair_prompt_uses_saved_shot_no(self):
        # rà 15/10: byd_fill gửi một phần cảnh — tiêu đề + trường "shot" phải là shot_no thật, không phải vị trí k
        text = director_byd.build_repair_prompt([(8, 1, {"shot_no": 3, "byd": _byd()}, [{"truong": "may.co", "loi": "x"}])], 1)
        self.assertIn("### Cảnh 8 · shot 3", text)
        self.assertIn('"shot": 3', text)
        self.assertNotIn("### Cảnh 8 · shot 1", text)

    def test_repair_answer_keyed_by_shot_no(self):
        obj = self._obj([_byd(shot=3, co="NOPE")])
        obj["scenes"][0]["shots"][0]["shot_no"] = 3

        def answer(prompt):
            good = _byd()
            good["noi_chon"]["kho_id"] = self.kho
            return {"byd": [{"canh": 8, "shot": 3, "byd": good}]}
        summary = director_byd.settle(self.p.conn, self.pid, obj, _Fake(answer))
        self.assertEqual(summary["vang_do"], 0)
        self.assertEqual(obj["scenes"][0]["shots"][0]["byd"]["shot"], 3)

    def test_warn_diag_names_auto_numbered(self):
        obj = self._obj([_byd(), _byd(co="NOPE")])
        with mock.patch.object(director_byd.diag, "record") as rec:
            director_byd.settle(self.p.conn, self.pid, obj, _Fake(lambda p: {"byd": []}))
        msg = rec.call_args[0][3]
        self.assertEqual(rec.call_args[0][2], "warn")
        self.assertIn("2 BYĐ thiếu `shot` — lấy số theo vị trí", msg)


if __name__ == "__main__":
    unittest.main()
