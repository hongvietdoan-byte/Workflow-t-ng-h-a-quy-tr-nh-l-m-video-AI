"""tools/audit_run.py: read-only report of where money and errors pile up (cause of every paid submission, same-input redos)."""
import importlib.util
import json
import os
import tempfile
import unittest

from core import regen
from core.cost import record_usage
from core.db import connect
from core.pipeline import Pipeline

_spec = importlib.util.spec_from_file_location("audit_run", os.path.join(os.path.dirname(__file__), "..", "tools", "audit_run.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

GOOD = {"character": .9, "hands_face": .9, "composition": .9, "mood_lighting": .9, "consistency": .9, "scale": .9, "grounding": .9,
        "set_match": .9}
VID_BAD = {"identity": .5, "physics": .8, "motion_match": .5, "artifacts": .8}
VID_OK = {"identity": .9, "physics": .9, "motion_match": .9, "artifacts": .9}


class AuditRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "m.sqlite")
        c = connect(self.db)
        p = Pipeline(c)
        self.pid = pid = p.create_project("V2", operating_mode="auto", threshold=0.82, max_retry=2)
        s1, s2 = p.create_scene(pid, 1), p.create_scene(pid, 2)
        for s in (s1, s2):
            c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1}), s))

        def img(scene, scores):
            q = c.execute("SELECT id FROM jobs WHERE scene_id=? AND state='queued'", (scene,)).fetchone()
            jid = q["id"] if q else p.create_job(scene, "image_gen")
            record_usage(c, jid, "image", "deepix", "m", "std", 1, "image")
            p.start(jid), p.succeed(jid)
            p.apply_qc(jid, scores, issues="Kelly must have a short black bob")
            return jid

        def vid(scene, src, h):
            q = c.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' AND state='queued'", (scene,)).fetchone()
            jid = q["id"] if q else p.create_job(scene, "video_gen")
            c.execute("UPDATE jobs SET external_id='v', source_job_id=?, input_hash=? WHERE id=?", (src, h, jid))
            record_usage(c, jid, "video", "clipai", "kling-v3-omni", "std", 10, "second")
            p.start(jid), p.succeed(jid)
            return jid

        img(s1, dict(GOOD, character=.4))          # QC reject -> automatic redo whose prompt carries the note
        i1 = img(s1, GOOD)
        i2 = img(s2, GOOD)
        v = vid(s1, i1, "h")
        p.apply_qc(v, VID_BAD)                      # redo with the very same inputs
        p.apply_qc(vid(s1, i1, "h"), VID_OK)
        p.apply_qc(vid(s2, i2, "h2"), VID_OK)
        regen.regenerate_video(p, self.tmp.name, c.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' AND state='approved'",
                                                           (s2,)).fetchone()["id"], "làm lại vì ảnh đổi")
        p.apply_qc(vid(s2, i2, "h2b"), VID_OK)
        c.commit()
        c.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_is_read_only_and_finds_causes(self):
        before = os.path.getmtime(self.db)
        conn = audit.open_ro(self.db)
        with self.assertRaises(Exception):
            conn.execute("DELETE FROM jobs")
        text, usd, wasted, _ = audit.report_project(conn, self.pid, {"per_video_second": {"kling-v3-omni:std": 0.1}, "per_video_clip": {},
                                                                     "per_image": {}}, audit.load_floors())
        conn.close()
        self.assertEqual(os.path.getmtime(self.db), before)
        self.assertAlmostEqual(usd, 4.0)            # 4 clips x 10 s x $0.10
        self.assertAlmostEqual(wasted, 2.0)         # the QC-rejected clip + the clip redone because its input changed
        self.assertIn("| QC loại → tự gen lại | 1 |", text)
        self.assertIn("| Đầu vào đổi → làm lại | 1 |", text)
        self.assertIn("gửi lại **đầu vào y hệt** (cùng ảnh + cùng motion prompt): **1** (100%)", text)
        self.assertIn("câu sửa chứa điểm số hoặc tiếng Việt (đi thẳng vào prompt Deepix): 1", text)

    def test_storyboard_gate_counts_clips_made_from_visibly_wrong_pictures(self):
        c = connect(self.db)
        p = Pipeline(c)
        s3 = p.create_scene(self.pid, 3)
        img = p.create_job(s3, "image_gen")
        p.start(img), p.succeed(img)
        p.apply_qc(img, dict(GOOD, composition=.4))    # passes on average, but the framing is visibly wrong
        c.execute("UPDATE jobs SET state='approved' WHERE id=?", (img,))
        v = p.create_job(s3, "video_gen")
        c.execute("UPDATE jobs SET external_id='v', source_job_id=? WHERE id=?", (img, v))
        record_usage(c, v, "video", "clipai", "kling-v3-omni", "std", 10, "second")
        c.commit(), c.close()
        conn = audit.open_ro(self.db)
        text = audit.report_project(conn, self.pid, {"per_video_second": {"kling-v3-omni:std": 0.1}, "per_video_clip": {},
                                                     "per_image": {}}, audit.load_floors())[0]
        conn.close()
        self.assertIn("**1 lần, $1.00 (20%)**", text)
        self.assertIn("composition 0.40", text)


if __name__ == "__main__":
    unittest.main()
