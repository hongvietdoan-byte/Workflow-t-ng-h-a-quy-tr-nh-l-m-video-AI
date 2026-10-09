"""KLD-10 (09/10) phần lõi — trao đổi thoại với Biên kịch trong chat; "ok áp dụng" là sửa (chưa nối vào khung chat). Không gọi dịch vụ."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import dialogue_chat as DC
from core.db import connect
from core.pipeline import Pipeline


class DialogueChatCore(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": os.path.join(tmp, "m.sqlite"), "PIPELINE_DATA": os.path.join(tmp, "p"),
                                               "KNOWLEDGE_USER_DIR": os.path.join(tmp, "k")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        self.pid = self.p.create_project("KLD10")
        self.p.set_script_text(self.pid, "CẢNH 1\nMaxim ướm áo.\nMAXIM: Hô biến! Đồ mới nè!\nKELLY: Đi thôi.")
        sid = self.p.create_scene(self.pid, 1, "C1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({
            "action": "Maxim ướm áo hoodie đỏ", "text": "Maxim ướm áo.\nMAXIM: Hô biến! Đồ mới nè!",
            "dialogue": [{"speaker": "MAXIM", "text": "Hô biến! Đồ mới nè!", "delivery": "hào hứng"},
                         {"speaker": "KELLY", "text": "Đi thôi."}]}, ensure_ascii=False), sid))
        self.p.conn.commit()

    def test_lines_rules_and_parse(self):
        ls = DC.lines(self.p, self.pid)
        self.assertEqual([(x["id"], x["speaker"], x["text"]) for x in ls], [("L1", "MAXIM", "Hô biến! Đồ mới nè!"), ("L2", "KELLY", "Đi thôi.")])
        self.assertIn("B12", DC.rules())
        self.assertIn("B13", DC.rules())
        got = DC.parse('Đây nè:\n{"reply": "Câu 1 cứng.", "proposals": [{"line": "L1", "new": "Ủa, đồ này ở đâu ra vậy?", "why": "B12"}], '
                       '"apply": []}')
        self.assertEqual((got["reply"], got["proposals"][0]["line"], got["apply"]), ("Câu 1 cứng.", "L1", []))
        self.assertEqual(DC.parse("không phải json")["proposals"], [])
        self.assertTrue(DC.approved("ok áp dụng câu 1 và 3"))
        self.assertTrue(DC.approved("chốt hết"))
        self.assertFalse(DC.approved("câu 2 nghe cứng quá, sửa lại giúp"))

    def test_apply_then_undo(self):
        pr = {"id": "P1", "line": "L1", "old": "Hô biến! Đồ mới nè!", "new": "Ủa, đồ này ở đâu ra mà nhìn hay zậy?"}
        res = DC.apply(self.p, self.pid, [pr])
        self.assertEqual(res["applied"], ["P1"])
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()[0])
        self.assertEqual((data["dialogue"][0]["speaker"], data["dialogue"][0]["text"]), ("MAXIM", pr["new"]))
        self.assertIn("MAXIM: " + pr["new"], self.p.project(self.pid)["script_text"])
        again = DC.apply(self.p, self.pid, [pr])                                 # old line gone → never applied twice
        self.assertIn("P1", again["skipped"])
        DC.undo(self.p, self.pid, res["undo"])
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()[0])
        self.assertEqual(data["dialogue"][0]["text"], "Hô biến! Đồ mới nè!")
        self.assertIn("MAXIM: Hô biến! Đồ mới nè!", self.p.project(self.pid)["script_text"])


class DialogueChatFixes(DialogueChatCore):
    """Rà độc lập 09/10: cổng đồng ý, hoàn tác nguyên trạng, thay theo thứ tự, tiêu đề không phải thoại."""

    def scene_data(self, idx=1):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (self.pid, idx)).fetchone()[0])

    def test_1_approval_gate_rejects_negation_question_and_changes(self):
        for text in ("không ok", "ok?", "ok nhưng bỏ chữ trời", "không đồng ý", "chưa áp dụng nhé", "đừng áp dụng câu 1",
                     "ok không?", "ok áp dụng hết trừ câu 2", "ok mà đổi thành 'đi nào'"):
            self.assertFalse(DC.approved(text), text)
        for text in ("ok áp dụng câu 1 và 3", "chốt hết", "đồng ý P2", "ok, thay luôn", "Ok áp dụng hết nhé"):
            self.assertTrue(DC.approved(text), text)

    def test_3_undo_restores_scene_data_exactly(self):
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (self.pid,)).fetchone()[0]
        original = {"action": "Maxim ướm áo", "text": "Maxim ướm áo.\nMAXIM: Hô biến! Đồ mới nè!",
                    "dialogue": [{"speaker": "MAXIM", "text": "", "beat": 0},
                                 {"speaker": "MAXIM", "text": "Hô biến! Đồ mới nè!", "delivery": "hào hứng", "t_start": 1.5},
                                 {"speaker": "KELLY", "text": "Đi thôi.", "lang": "vi"}]}
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(original, ensure_ascii=False), sid))
        self.p.conn.commit()
        pr = {"id": "P1", "line": "L1", "old": "Hô biến! Đồ mới nè!", "new": "Ủa, đồ mới hả?"}
        res = DC.apply(self.p, self.pid, [pr])
        self.assertEqual(res["applied"], ["P1"])
        DC.undo(self.p, self.pid, res["undo"])
        self.assertEqual(self.scene_data(), original)                    # cả dòng rỗng, trường lạ, không còn _user_locked

    def test_4_script_text_replaced_by_order_and_not_blindly(self):
        self.p.set_script_text(self.pid, "CẢNH 1\nKELLY: Đi thôi.\nCẢNH 2\nKELLY: Đi thôi.")
        sid = self.p.create_scene(self.pid, 2, "C2")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"text": "KELLY: Đi thôi.",
                            "dialogue": [{"speaker": "KELLY", "text": "Đi thôi."}]}, ensure_ascii=False), sid))
        self.p.conn.commit()
        ids = {(x["idx"], x["text"]): x["id"] for x in DC.lines(self.p, self.pid)}
        res = DC.apply(self.p, self.pid, [{"id": "P1", "line": ids[(2, "Đi thôi.")], "old": "Đi thôi.", "new": "Lẹ lên!"}])
        self.assertEqual(res["applied"], ["P1"])
        self.assertEqual(self.p.project(self.pid)["script_text"], "CẢNH 1\nKELLY: Đi thôi.\nCẢNH 2\nKELLY: Lẹ lên!")
        # câu không còn trong kịch bản dự án → không thay mù chữ khác, có ghi chú
        self.p.set_script_text(self.pid, "CẢNH 1\nMaxim nói Hô biến! Đồ mới nè! rồi cười.")
        res = DC.apply(self.p, self.pid, [{"id": "P2", "line": "L1", "old": "Hô biến! Đồ mới nè!", "new": "Ủa?"}])
        self.assertEqual(self.p.project(self.pid)["script_text"], "CẢNH 1\nMaxim nói Hô biến! Đồ mới nè! rồi cười.")
        self.assertTrue(res["notes"])

    def test_5_headings_are_not_dialogue(self):
        self.p.conn.execute("DELETE FROM scenes WHERE project_id=?", (self.pid,))
        self.p.conn.commit()
        self.p.set_script_text(self.pid, "CẢNH 1: NHÀ KELLY - ĐÊM\nINT: PHÒNG NGỦ\nLƯU Ý: quay dọc\nGHI CHÚ: nhạc nhỏ\nKELLY: Chào.")
        self.assertEqual([(x["speaker"], x["text"]) for x in DC.lines(self.p, self.pid)], [("KELLY", "Chào.")])


if __name__ == "__main__":
    unittest.main()
