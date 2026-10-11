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


class EveryLockReaderHonoursNgoaiLe(LockHonoursNgoaiLe):
    """Rà tích hợp 11/10: QC ảnh / clip / cảnh (prompts.lock_text, qc_spec.compile_frame), prompt viết motion và nhận diện hiệu ứng chủ
    ý (video_qc_context) đọc CÙNG ngoại lệ (core/lock_exceptions) — ảnh sạch theo ngoại lệ không bị chấm "mất glitch"."""

    def test_qc_lock_text_one_shot_drops_the_clauses_and_says_the_exception(self):
        from core import prompts
        txt = prompts.lock_text(self.p.conn, self.pid, ["YN2"], shots=[self.scene(9)])
        self.assertNotIn("losing glitch", txt)
        self.assertNotIn("glitch/noise effect", txt)
        self.assertIn("crosshatch", txt)
        self.assertIn("KHÔNG có glitch", txt)
        old = prompts.lock_text(self.p.conn, self.pid, ["YN2"], shots=[self.scene(8)])
        self.assertEqual(old, prompts.lock_text(self.p.conn, self.pid, ["YN2"]))      # ngoài phạm vi: y như cũ
        self.assertIn("losing glitch effect", old)

    def test_qc_lock_text_many_shots_keeps_the_lock_and_lists_each_exception(self):
        from core import prompts
        txt = prompts.lock_text(self.p.conn, self.pid, ["YN2"], shots=[self.scene(8), self.scene(9)])
        self.assertIn("losing glitch effect", txt)                       # shot 8 vẫn giữ khóa
        self.assertIn("shot 9", txt)
        self.assertIn("KHÔNG có glitch", txt)

    def test_frame_spec_does_not_ask_for_the_excepted_item(self):
        from core import qc_spec
        prof = {"YN2": dict(RULES)}
        spec = qc_spec.compile_frame(None, self.pid, 1, self.scene(9), profiles=prof)
        self.assertFalse([a for a in spec["assertions"] if "glitch" in str(a).lower()], spec["assertions"])
        self.assertTrue([a for a in spec["assertions"] if "crosshatch" in str(a).lower()])
        spec8 = qc_spec.compile_frame(None, self.pid, 1, self.scene(8), profiles=prof)
        self.assertTrue([a for a in spec8["assertions"] if "glitch" in str(a).lower()])
        self.assertEqual(prof["YN2"], RULES)                             # hồ sơ gốc không bị sửa

    def test_motion_writer_bundle_carries_the_exception(self):
        from core import prompts
        c = self.p.conn
        for shot in (8, 9):
            sid = c.execute("INSERT INTO scenes (project_id, idx, data) VALUES (?,?,?)",
                            (self.pid, shot, json.dumps(self.scene(shot)))).lastrowid
            c.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                      (self.pid, sid, "image_gen", "approved", "2026-10-11T00:00:00", "2026-10-11T00:00:00"))
        c.commit()
        bundle = prompts.build_motion_bundle(self.p, self.pid)
        self.assertIn("shot 9", bundle)
        self.assertIn("KHÔNG có glitch", bundle)

    def test_negated_or_excepted_glitch_is_not_an_intended_effect(self):
        from core import video_qc_context as vqc
        self.assertEqual(vqc.intended_effects({"action": "Màn hình nhiễu sóng, glitch như mất kết nối"})["noise"][:1], ["glitch"])
        for data, motion in (({"action": "Kelly đứng yên, không glitch"}, None),
                             ({"action": "Kelly stands still"}, "Clean frame WITHOUT any glitch or distortion."),
                             ({"action": "Kelly stands still"}, "No glitch, no flicker.")):
            self.assertEqual(vqc.intended_effects(data, motion)["noise"], [], (data, motion))
        # ngoại lệ BYĐ "ảnh sạch, nhiễu chỉ ghép hậu kỳ" của shot → clip phải sạch: `artifacts` lại chặn cứng
        data = dict(self.scene(9), action="YN2 lướt tới, màn hình nhiễu sóng")
        self.assertEqual(vqc.intended_effects(data)["noise"], [])
        self.assertEqual(vqc.soft_criteria(data), ())
        self.assertTrue(vqc.intended_effects(dict(self.scene(8), action="YN2 lướt tới, màn hình nhiễu sóng"))["noise"])


if __name__ == "__main__":
    unittest.main()
