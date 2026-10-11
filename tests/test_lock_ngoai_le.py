"""11/10 #24 shots 9–10: BYĐ ngoai_le "không có hiệu ứng glitch toàn thân trong ảnh (ảnh sạch)" (phạm vi [9, 10]) while the Character
Lock still sent "keep … full-body glitch/noise effect; never … losing glitch effect" — the lock beat the shot's own exception. The lock
must drop the clauses the exception overrides, only for the shots in its scope."""
import json
import unittest

from core.db import connect
from core.pipeline import Pipeline
from core.runner import lock_exceptions, lock_note

RULES = {"must_keep": "white hair with red tips, black face with round red eyes, comic-style crosshatch linework, red heels, "
                      "full-body glitch/noise effect",
         "forbidden": "removing crosshatch linework, changing hair color, losing glitch effect"}
EXC = {"doi_tuong": "YN2", "dieu_trai": "không có hiệu ứng glitch toàn thân trong ảnh/video (ảnh sạch); nhiễu sóng chỉ ghép hậu kỳ",
       "cach_hien": "anh_sach_nhieu_hau_ky", "ly_do": "phong_cach", "pham_vi": [9, 10]}


class LockHonoursNgoaiLe(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("p")
        self.p.conn.execute("INSERT INTO characters (project_id, name, description, lock_rules) VALUES (?,?,?,?)",
                            (self.pid, "YN2", "x", json.dumps(RULES)))
        self.p.conn.commit()

    def scene(self, shot, exc=(EXC,)):
        return {"characters": ["YN2"], "byd": {"shot": shot, "ngoai_le": list(exc)}}

    def test_exception_in_scope_drops_the_glitch_clauses(self):
        note = lock_note(self.p.conn, self.pid, ["YN2"], self.scene(9))
        self.assertNotIn("glitch/noise effect", note)
        self.assertNotIn("losing glitch", note)
        self.assertIn("WITHOUT any glitch", note)
        self.assertIn("crosshatch linework", note)          # the rest of the lock stays
        self.assertIn("changing hair color", note)

    def test_out_of_scope_or_no_scene_keeps_the_lock(self):
        for data in (self.scene(8), None, {"characters": ["YN2"]}):
            note = lock_note(self.p.conn, self.pid, ["YN2"], data)
            self.assertIn("full-body glitch/noise effect", note)
            self.assertIn("losing glitch effect", note)

    def test_exception_for_someone_else_or_unknown_item_changes_nothing(self):
        other = dict(EXC, doi_tuong="khung_hinh")
        vague = dict(EXC, dieu_trai="tư thế khác thường", cach_hien="dien_xuat")
        for exc in ((other,), (vague,)):
            self.assertIn("losing glitch effect", lock_note(self.p.conn, self.pid, ["YN2"], self.scene(9, exc)))

    def test_lock_exceptions_reads_items_and_negation(self):
        self.assertEqual(lock_exceptions(self.scene(10)), {"YN2": {"items": ["glitch"], "without": True}})
        self.assertEqual(lock_exceptions(self.scene(11)), {})

    def test_name_case_and_text_scope_still_match(self):
        exc = dict(EXC, doi_tuong=" yn2 ", pham_vi=["9"])
        self.assertNotIn("losing glitch", lock_note(self.p.conn, self.pid, ["YN2"], self.scene(9, (exc,))))


if __name__ == "__main__":
    unittest.main()
