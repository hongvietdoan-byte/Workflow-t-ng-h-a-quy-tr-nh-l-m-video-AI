"""08/10 dự án #24 (cờ storyboard_api bật): 'Bật gen thử trước' chọn shot 2, 5, 8 nhưng chế độ storyboard bắt shot không phải neo chờ ảnh
neo của cảnh (shot 1, WS) — shot 1 không nằm trong gen thử → 3 job 'queued' mãi, runner chờ im lặng, UI bảo 'bấm ▶ Gen ảnh' (lỗi 11);
nút Gen ảnh ước tính 9 ảnh khi chỉ gửi 3 (lỗi 12); ghi chú render 3D từ thread khác mất vì dùng kết nối của thread chính (lỗi 13)."""
import json
import os
import sqlite3
import tempfile
import threading
import types
import unittest
from unittest import mock

from core import cost, pilot, scene_storyboard
from core.db import connect
from core.pipeline import Pipeline
from core.runner import ImageRunner

ON = {"FEATURE_STORYBOARD_API": "1"}
SIZES = ["WS", "MS", "CU", "MCU", "CU", "MS", "MCU", "CU", "MS"]


def p24(db=":memory:"):
    p = Pipeline(connect(db))
    pid = p.create_project("p24")
    ids = []
    for i, size in enumerate(SIZES, 1):
        sid = p.create_scene(pid, i, f"shot {i}")
        p.conn.execute("UPDATE scenes SET state='ready', data=? WHERE id=?", (json.dumps(
            {"story_scene": 1, "shot_no": i, "size": size, "characters": ["KELLY"] if i < 5 else ["YÊU NỮ"],
             "image_prompt": "x"}), sid))
        ids.append(sid)
    p.conn.commit()
    return p, pid, ids


class PilotAnchorTests(unittest.TestCase):
    def test_pilot_adds_the_anchor_its_shots_wait_for(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            chosen = pilot.start(p, pid)
        self.assertIn(ids[0], chosen)                                   # shot 1 (WS) = the scene's anchor

    def test_an_old_pilot_without_the_anchor_still_lets_it_through(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            pilot.save(p, pid, {"enabled": True, "scenes": [ids[1], ids[4], ids[7]], "released": False})   # #24: 258/261/264
            self.assertEqual(pilot.allowed_scenes(p, pid, ids), [ids[0], ids[1], ids[4], ids[7]])
            self.assertEqual(cost.pending_image_units(p, pid), 4)       # lỗi 12: 3 shots + their anchor, not 9

    def test_a_stuck_wait_is_said(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            p.create_job(ids[1], "image_gen")
            why = scene_storyboard.wait_reason(p.conn, tempfile.mkdtemp(), pid, ids[1])
        self.assertTrue(why["stuck"])
        self.assertIn("shot 1", why["text"])
        self.assertIsNone(scene_storyboard.wait_reason(p.conn, tempfile.mkdtemp(), pid, ids[0]))   # the anchor itself never waits


class ThreadDiagTests(unittest.TestCase):
    def test_a_note_from_another_thread_reaches_the_database(self):
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        p, pid, ids = p24(db)
        job = {"project_id": pid, "scene_id": ids[0], "id": p.create_job(ids[0], "image_gen")}
        fake = types.SimpleNamespace(p=p, job_type="image_gen", _diag=lambda *a: None)
        log = ImageRunner._thread_diag(fake, job, "place_render")
        t = threading.Thread(target=log, args=("Render 3D xong 9 plate",))
        t.start()
        t.join()
        c = sqlite3.connect(db)
        rows = c.execute("SELECT message FROM diag_events WHERE code='place_render'").fetchall() if c.execute(
            "SELECT 1 FROM sqlite_master WHERE name='diag_events'").fetchone() else []
        c.close()
        self.assertTrue(any("Render 3D xong" in r[0] for r in rows), rows)


class PilotWaitsSaidTests(unittest.TestCase):
    def test_the_grey_release_button_names_what_is_left(self):
        p, pid, ids = p24()
        pilot.save(p, pid, {"enabled": True, "scenes": [ids[0], ids[1]], "released": False})
        j = p.create_job(ids[0], "image_gen")
        p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (j,))
        p.conn.commit()
        self.assertEqual(pilot.unapproved(p, pid), ["shot 1 (chờ duyệt)", "shot 2 (chưa gen)"])
        p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (j,))
        p.conn.commit()
        self.assertEqual(pilot.unapproved(p, pid), ["shot 2 (chưa gen)"])


if __name__ == "__main__":
    unittest.main()
