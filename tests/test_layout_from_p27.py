"""12/10 dự án #27 (shot 11–12): quay lại đúng chỗ ba đồng đội gục sau nhánh thế giới song song — shot thuộc `sequence` khác shot 1–4
nên không có ảnh neo/ảnh cảnh trước nào cho thấy hàng đồng đội; chữ "exactly as in the opening shot" không kèm ảnh → hàng người bị dồn,
nằm chồng lên nhau. Trường `continuity_from` (số shot trước) gửi ảnh shot đó làm ảnh 'giữ bố cục'."""
import json
import os
import tempfile
import types
import unittest
from unittest import mock

from core import llm_io, scene_storyboard
from core.assets import reference_note
from core.db import connect
from core.pipeline import Pipeline
from core.runner import ImageRunner, layout_frame_job, layout_reference

ON = {"FEATURE_STORYBOARD_API": "1"}


def project():
    """Shot 1 (sequence 1, the fallen teammates) · shots 2–3 (sequence 3, one story scene, back at the same spot)."""
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("p27")
    ids = []
    for i, (seq, scene, no) in enumerate([(1, 1, 1), (3, 6, 1), (3, 6, 2)], 1):
        sid = p.create_scene(pid, i, f"shot {i}")
        d = {"sequence": seq, "story_scene": scene, "shot_no": no, "size": "WS" if no == 1 else "MS", "characters": ["KELLY"],
             "image_prompt": "x"}
        p.conn.execute("UPDATE scenes SET state='ready', data=? WHERE id=?", (json.dumps(d), sid))
        ids.append(sid)
    p.conn.commit()
    return p, pid, ids


def picture(p, pid, sid, state, data_dir):
    j = p.create_job(sid, "image_gen")
    p.conn.execute("UPDATE jobs SET state=? WHERE id=?", (state, j))
    p.conn.commit()
    folder = os.path.join(data_dir, str(pid), "images")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"job_{j}.png")
    open(path, "wb").write(b"png")
    return j, path


class LayoutFromTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p, self.pid, self.ids = project()

    def test_the_approved_picture_wins_else_the_newest_waiting_one(self):
        self.assertIsNone(layout_frame_job(self.p.conn, self.pid, {}))
        self.assertIsNone(layout_frame_job(self.p.conn, self.pid, {"continuity_from": 1}))       # no picture yet
        waiting, _ = picture(self.p, self.pid, self.ids[0], "pending_review", self.data)
        self.assertEqual(layout_frame_job(self.p.conn, self.pid, {"continuity_from": 1})["id"], waiting)
        approved, _ = picture(self.p, self.pid, self.ids[0], "approved", self.data)
        picture(self.p, self.pid, self.ids[0], "pending_review", self.data)                       # a newer redraw waiting
        self.assertEqual(layout_frame_job(self.p.conn, self.pid, {"continuity_from": 1})["id"], approved)
        picture(self.p, self.pid, self.ids[0], "rejected", self.data)
        self.assertEqual(layout_frame_job(self.p.conn, self.pid, {"continuity_from": 1})["id"], approved)

    def test_an_unapproved_or_missing_picture_is_said(self):
        notes = []
        runner = types.SimpleNamespace(p=self.p, data_dir=self.data, _diag=lambda job, sev, code, msg: notes.append(code))
        job = {"id": 9, "project_id": self.pid, "scene_id": self.ids[1]}
        self.assertIsNone(layout_reference(runner, job, {"continuity_from": 1}))
        self.assertEqual(notes, ["missing_reference"])
        _, path = picture(self.p, self.pid, self.ids[0], "pending_review", self.data)
        ref = layout_reference(runner, job, {"continuity_from": 1})
        self.assertEqual((ref["path"], ref["role"]), (path, "layout_from"))
        self.assertEqual(notes[-1], "layout_from_unapproved")
        self.assertIsNone(layout_reference(runner, job, {}))

    def test_the_storyboard_anchor_shot_sends_the_earlier_shot_with_its_note(self):
        _, path = picture(self.p, self.pid, self.ids[0], "approved", self.data)
        with mock.patch.dict(os.environ, ON):
            f = scene_storyboard.job_fields(self.p.conn, self.data, self.pid, self.ids[1], [], 0, layout=path, layout_label="shot 1")
            plain = scene_storyboard.job_fields(self.p.conn, self.data, self.pid, self.ids[1], [], 0)
        self.assertEqual([r["role"] for r in f["refs"]], ["layout_from"])
        self.assertIn("Image 1 is an EARLIER shot at this same place", f["storyboard"]["image_mapping"])
        self.assertIn("Image 1 (shot 1): earlier shot at the same place", f["storyboard"]["image_mapping"])
        self.assertNotIn("continuity anchor", f["storyboard"]["image_mapping"])     # rà 12/10: not "inherit … appearance / framing"
        self.assertEqual(plain["refs"], [])                                                   # without the field: as before
        self.assertIn("EARLIER shot at this same place", reference_note(f["refs"]))

    def test_the_runner_adds_it_in_storyboard_mode(self):
        _, path = picture(self.p, self.pid, self.ids[0], "approved", self.data)
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.ids[1],)).fetchone()["data"])
        d["continuity_from"] = 1
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), self.ids[1]))
        self.p.conn.commit()
        with mock.patch.dict(os.environ, ON):
            fake = types.SimpleNamespace(p=self.p, data_dir=self.data, provider=types.SimpleNamespace(supports_storyboard=True),
                                         _diag=lambda *a: None)
            job = {"id": self.p.create_job(self.ids[1], "image_gen"), "project_id": self.pid, "scene_id": self.ids[1]}
            prompt, sent = ImageRunner._finish_args(fake, job, "shot 2", [])
        self.assertIn(path, sent)
        self.assertIn("EARLIER shot at this same place", prompt)
        self.assertIn("layout_from", json.dumps(fake._sent[job["id"]]))

    def test_a_shot_on_another_spot_gets_no_anchor_picture(self):
        """#27 cảnh 7: shot 15 (level_9_4, the gunfight) got frame 1 of shot 13 (bac_thang_giua, the pick-up) — job 771."""
        for sid, spot in ((self.ids[1], "bac_thang_giua"), (self.ids[2], "level_9_4")):
            d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
            d["plate_spot"] = spot
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        self.p.conn.commit()
        _, anchor = picture(self.p, self.pid, self.ids[1], "approved", self.data)
        with mock.patch.dict(os.environ, ON):
            g = scene_storyboard.group_of(self.p.conn, self.pid, self.ids[2])
            self.assertTrue(scene_storyboard.other_spot(g, self.ids[2]))
            self.assertFalse(scene_storyboard.uses_anchor(g, self.ids[2]))
            f = scene_storyboard.job_fields(self.p.conn, self.data, self.pid, self.ids[2], [], 0)
            self.assertNotIn(anchor, [r["path"] for r in f["refs"]])
            self.assertTrue(f["anchor_skipped"])
            notes = []
            fake = types.SimpleNamespace(p=self.p, data_dir=self.data, provider=types.SimpleNamespace(supports_storyboard=True),
                                         _diag=lambda job, sev, code, msg: notes.append((code, msg)))
            job = {"id": self.p.create_job(self.ids[2], "image_gen"), "project_id": self.pid, "scene_id": self.ids[2]}
            ImageRunner._finish_args(fake, job, "shot 3", [])
            said = [m for c, m in notes if c == "storyboard_anchor_skipped"]
            self.assertTrue(said and "chỗ khác shot neo (plate_spot level_9_4 ≠ bac_thang_giua)" in said[0], notes)
            self.assertNotIn("quay khỏi mốc", said[0])
            d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.ids[2],)).fetchone()["data"])
            d["plate_spot"] = "bac_thang_giua"                                              # same spot: frame 1 as before
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), self.ids[2]))
            self.p.conn.commit()
            f = scene_storyboard.job_fields(self.p.conn, self.data, self.pid, self.ids[2], [], 0)
        self.assertIn(anchor, [r["path"] for r in f["refs"]])

    def test_a_changed_layout_shot_makes_the_picture_outdated(self):
        from core.change_review import WATCH
        from core.lineage import image_spec_hash
        d = {"image_prompt": "x", "characters": ["KELLY"]}
        self.assertNotEqual(image_spec_hash(d, [], "9:16"), image_spec_hash(dict(d, continuity_from=3), [], "9:16"))
        self.assertIn("anh", WATCH["continuity_from"])

    def test_the_scene_edit_takes_only_an_earlier_shot(self):
        llm_io.store_scene_analysis(self.p, self.pid, {"characters": [{"name": "KELLY", "description": "d"}], "scenes": [
            {"idx": i, "location": "l", "time": "day", "characters": ["KELLY"], "mood": "m", "lighting": "l", "shot": "s",
             "image_prompt": f"shot {i}"} for i in (1, 2, 3)]})
        self.assertIn("continuity_from", llm_io.update_scene(self.p, self.pid, 2, {"continuity_from": 1}))
        for bad in (2, 3, 0, "1", True):
            with self.assertRaises(llm_io.SchemaError):
                llm_io.update_scene(self.p, self.pid, 2, {"continuity_from": bad})
        llm_io.update_scene(self.p, self.pid, 2, {"continuity_from": None})


if __name__ == "__main__":
    unittest.main()
