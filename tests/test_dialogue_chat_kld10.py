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


if __name__ == "__main__":
    unittest.main()
