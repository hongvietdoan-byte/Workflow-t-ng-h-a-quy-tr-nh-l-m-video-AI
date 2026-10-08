"""08/10 dự án #24 (lỗi D): chế độ storyboard cả cảnh gửi ảnh neo (khung 1 = shot 1 WS nhìn về Tháp Đồng Hồ) cho MỌI shot, kể cả shot có
plate_view away/left/right — job 576 (shot 4, góc ngược nhìn về nhà mái đỏ) gửi job_573.png và vẽ tháp sau lưng Kelly.
Dữ liệu dạng #24: scenes 257–265, cỡ shot + plate_view đúng như manifest (đọc 08/10)."""
import json
import os
import tempfile
import types
import unittest
from unittest import mock

from core import pilot, scene_storyboard
from core.db import connect
from core.pipeline import Pipeline
from core.runner import ImageRunner

ON = {"FEATURE_STORYBOARD_API": "1"}
# (size, plate_view background, characters) of #24 shots 1..9
SHOTS = [("WS", None, ["KELLY"]), ("MS", "left", ["KELLY"]), ("MS", "landmark", ["KELLY"]), ("MCU", "away", ["KELLY"]),
         ("WS", "left", ["KELLY", "YÊU NỮ"]), ("MS", "landmark", ["YÊU NỮ"]), ("MS", "left", ["YÊU NỮ"]),
         ("CU", None, ["YÊU NỮ"]), ("WS", "left", ["KELLY", "YÊU NỮ"])]


def p24():
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("p24")
    ids = []
    for i, (size, view, cast) in enumerate(SHOTS, 1):
        sid = p.create_scene(pid, i, f"shot {i}")
        d = {"story_scene": 1, "shot_no": i, "size": size, "characters": cast, "image_prompt": "x", "action": f"beat {i}"}
        if view:
            d["plate_view"] = {"background": view, "why": "#24"}
        p.conn.execute("UPDATE scenes SET state='ready', data=? WHERE id=?", (json.dumps(d), sid))
        ids.append(sid)
    p.conn.commit()
    return p, pid, ids


def with_anchor_picture(p, pid, ids):
    data = tempfile.mkdtemp()
    j = p.create_job(ids[0], "image_gen")
    p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (j,))
    p.conn.commit()
    os.makedirs(os.path.join(data, str(pid), "images"))
    path = os.path.join(data, str(pid), "images", f"job_{j}.png")
    open(path, "wb").write(b"png")
    return data, path


class AwayShotAnchorTests(unittest.TestCase):
    def test_an_away_shot_gets_no_anchor_picture(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            data, anchor = with_anchor_picture(p, pid, ids)
            away = scene_storyboard.job_fields(p.conn, data, pid, ids[3], [], 0, landmark="the clock tower")
            toward = scene_storyboard.job_fields(p.conn, data, pid, ids[2], [], 0)
        self.assertNotIn(anchor, [r["path"] for r in away["refs"]])           # shot 4 (away): no frame 1
        self.assertTrue(away["anchor_skipped"])
        self.assertIn("the clock tower is NOT in this frame", away["cast_note"])
        self.assertNotIn("frame 1 (scene anchor)", away["storyboard"]["image_mapping"])
        self.assertIn(anchor, [r["path"] for r in toward["refs"]])            # shot 3 (landmark): frame 1 as before
        self.assertFalse(toward["anchor_skipped"])
        self.assertNotIn("NOT in this frame, not even far", toward["cast_note"])
        self.assertNotEqual(away["storyboard"]["storyboard_id"], toward["storyboard"]["storyboard_id"])   # own session

    def test_left_and_right_shots_count_as_turned_away(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            g = scene_storyboard.group_of(p.conn, pid, ids[1])
        self.assertEqual(g["anchor"]["id"], ids[0])
        self.assertEqual([scene_storyboard.turned_away(g, s) for s in ids],
                         [False, True, False, True, True, False, True, False, True])

    def test_an_away_shot_does_not_wait_for_the_anchor(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            data = tempfile.mkdtemp()
            self.assertFalse(scene_storyboard.waits(p.conn, data, pid, ids[3]))
            self.assertTrue(scene_storyboard.waits(p.conn, data, pid, ids[2]))
            self.assertEqual(pilot.anchors_needed(p, pid, [ids[3], ids[1]]), [])        # nobody of these needs shot 1
            self.assertEqual(pilot.anchors_needed(p, pid, [ids[3], ids[2]]), [ids[0]])

    def test_an_anchor_turned_away_too_is_still_sent(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            d = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (ids[0],)).fetchone()["data"])
            d["plate_view"] = {"background": "away"}
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), ids[0]))
            p.conn.commit()
            data, anchor = with_anchor_picture(p, pid, ids)
            f = scene_storyboard.job_fields(p.conn, data, pid, ids[3], [], 0)
        self.assertIn(anchor, [r["path"] for r in f["refs"]])                 # frame 1 shows no landmark either


class RunnerAwayTests(unittest.TestCase):
    def test_the_runner_drops_frame_1_and_says_so(self):
        with mock.patch.dict(os.environ, ON):
            p, pid, ids = p24()
            data, anchor = with_anchor_picture(p, pid, ids)
            notes = []
            fake = types.SimpleNamespace(p=p, data_dir=data, provider=types.SimpleNamespace(supports_storyboard=True),
                                         _diag=lambda job, sev, code, msg: notes.append((code, msg)))
            job = {"id": p.create_job(ids[3], "image_gen"), "project_id": pid, "scene_id": ids[3]}
            out = ImageRunner._finish_args(fake, job, "shot 4", [])
        sent = out[1] if len(out) > 1 else []
        self.assertNotIn(anchor, sent)
        self.assertIn("NOT in this frame", out[0])
        self.assertTrue(any(c == "storyboard_anchor_skipped" for c, _ in notes), notes)
        self.assertNotIn("frame 1", json.dumps(fake._sent[job["id"]]))


if __name__ == "__main__":
    unittest.main()
