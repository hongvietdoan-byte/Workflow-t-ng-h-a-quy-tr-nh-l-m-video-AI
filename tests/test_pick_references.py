"""GĐ-E0c (T3/T5/B1–B3/K7, docs/KE_HOACH_TONG_2026-09-24.md): the reference pictures follow the shot — a close shot gets a face, a
back-to-camera shot a back view; a place is sent as pixels only as an approved empty background from the shot's kind of camera, for a
wide shot; otherwise it goes as words with real landmark heights; every image job records what it sent."""
import json
import os
import shutil
import tempfile
import unittest

from PIL import Image

from core import assets
from core.db import connect
from core.pipeline import Pipeline


class PickTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.conn = connect(":memory:")
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("P")
        self.kelly = assets.create(self.conn, "FF", "character", "KELLY")
        for n, (w, h, role) in enumerate([(400, 1000, "full_body"), (600, 700, "half_body"), (500, 500, "close_up"),
                                          (400, 1000, "back")]):
            self.add(self.kelly, f"k{n}.png", w, h, n, role)
        self.place = assets.create(self.conn, "FF", "location", "Tháp đồng hồ", "Tháp gạch đỏ giữa quảng trường")
        self.top = self.add(self.place, "map.png", 1920, 1080, 20, "top_down")
        self.eye = self.add(self.place, "eye.png", 1920, 1080, 21, "eye_level")
        for a in (self.kelly, self.place):
            assets.attach(self.conn, self.pid, a)
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'd')", (self.pid,))
        self.conn.commit()

    def add(self, aid, name, w, h, seed, role):
        path = os.path.join(self.dir, name)
        Image.new("RGB", (w, h), (seed * 9 % 255, 80, 120)).save(path)
        with open(path, "rb") as f:
            assets.add_image(self.conn, aid, name, f.read(), role=role)
        return path

    def roles(self, scene):
        by_path = {i["path"]: i["role"] for a in (self.kelly, self.place) for i in assets.get(self.conn, a)["images"]}
        return [(r["role"], by_path.get(r["path"])) for r in assets.scene_references(self.conn, self.pid, scene)]

    def test_a_close_shot_gets_the_face_and_no_background_picture(self):
        got = self.roles({"characters": ["KELLY"], "location": "Tháp đồng hồ", "size": "CU"})
        self.assertEqual(got[0], ("character", "close_up"))
        self.assertNotIn("location", [r for r, _ in got])                    # B3: no background pixels for a close shot

    def test_a_wide_shot_gets_the_whole_figure_and_the_eye_level_background_never_the_map(self):
        got = self.roles({"characters": ["KELLY"], "location": "Tháp đồng hồ", "size": "WS", "angle": "eye"})
        self.assertEqual(got[0], ("character", "full_body"))
        self.assertEqual(got[-1], ("location", "eye_level"))
        self.assertNotIn(("location", "top_down"), got)                       # B2: a map from above is information only

    def test_a_high_wide_shot_without_a_high_background_gets_no_background(self):
        got = self.roles({"characters": ["KELLY"], "location": "Tháp đồng hồ", "size": "WS", "angle": "high"})
        self.assertNotIn("location", [r for r, _ in got])

    def test_a_back_to_camera_shot_gets_the_back_view_first(self):
        got = self.roles({"characters": ["KELLY"], "size": "MS", "blocking": "Kelly quay lưng về phía camera"})
        self.assertEqual(got[0], ("character", "back"))

    def test_the_v2_shot_words_are_read_too(self):
        self.assertEqual(assets.shot_size({"shot": "medium close-up, eye level"}), "MCU")
        self.assertEqual(assets.shot_size({"shot": "Wide establishing shot"}), "WS")
        self.assertIsNone(assets.shot_size({"shot": ""}))

    def test_the_place_goes_as_words_with_real_heights(self):
        import hashlib
        stored = assets.get(self.conn, self.place)["images"]
        for img in stored:
            with open(img["path"], "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            self.conn.execute("INSERT OR REPLACE INTO set_analyses (sha256, data, created_at) VALUES (?,?, 'x')",
                              (h, json.dumps({"camera": "eye", "landmarks": [{"name": "brick wall", "height_m": 1.2},
                                                                              {"name": "clock tower", "height_m": 32}]})))
        self.conn.commit()
        text = assets.location_text(self.conn, assets.get(self.conn, self.place))
        self.assertIn("Tháp gạch đỏ", text)
        self.assertIn("brick wall about 1.2 m tall", text)
        self.assertIn("1.7 m", text)

    def test_the_notes_say_what_each_picture_does_not_control(self):
        refs = assets.scene_references(self.conn, self.pid, {"characters": ["KELLY"], "location": "Tháp đồng hồ", "size": "WS"})
        note = assets.reference_note(refs)
        self.assertIn("does not set the people, their size or their position", note)
        self.assertIn("not the pose, the camera or how big they are", note)


class SentRefsTest(unittest.TestCase):
    def test_an_image_job_records_the_pictures_it_sent(self):
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        os.environ["ASSET_DIR"] = os.path.join(d, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        conn = connect(":memory:")
        p = Pipeline(conn)
        pid = p.create_project("P")
        kelly = assets.create(conn, "FF", "character", "KELLY")
        path = os.path.join(d, "k.png")
        Image.new("RGB", (400, 900), (1, 2, 3)).save(path)
        with open(path, "rb") as f:
            assets.add_image(conn, kelly, "k.png", f.read())
        assets.attach(conn, pid, kelly)
        sid = p.create_scene(pid, 1, "x")
        conn.execute("UPDATE scenes SET data=?, state='ready' WHERE id=?",
                     (json.dumps({"image_prompt": "Kelly runs", "characters": ["KELLY"]}), sid))
        conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'd')", (pid,))
        conn.commit()
        jid = p.create_job(sid, "image_gen")
        ImageRunner(p, MockImageProvider(), d).submit_pending(pid)
        sent = json.loads(p.job(jid)["sent_refs"])
        self.assertEqual([(s["label"], s["role"]) for s in sent], [("KELLY", "character")])


class StandardProfileTests(PickTests):
    """T1: an approved library profile is the one source for every project — it wins over a project's own (possibly copied or
    Director-written) Lock, carries the real height, and the Director is told not to rewrite it."""

    def test_the_approved_profile_wins_over_the_project_lock(self):
        from core import prompts
        from core.runner import lock_note
        self.conn.execute("UPDATE characters SET lock_rules=? WHERE project_id=? AND name='KELLY'",
                          (json.dumps({"must_keep": "ponytail", "may_change": "", "forbidden": ""}), self.pid))
        self.conn.commit()
        self.assertIn("ponytail", lock_note(self.conn, self.pid, ["KELLY"]))          # no approved profile yet: project Lock
        assets.set_profile(self.conn, self.kelly, {"identity": "young woman, short white hair", "must_keep": "short white hair",
                                                   "forbidden": "ponytail", "height_m": 1.68}, approved=True)
        note = lock_note(self.conn, self.pid, ["KELLY"])
        self.assertIn("keep short white hair", note)
        self.assertIn("never ponytail", note)
        self.assertIn("about 1.68 m tall", note)
        self.assertIn("hồ sơ chuẩn Kho", prompts.lock_text(self.conn, self.pid))
        self.assertIn("KHÔNG viết lại", prompts.standard_block(self.p, self.pid))

    def test_a_draft_profile_is_not_inherited(self):
        assets.set_profile(self.conn, self.kelly, {"must_keep": "x"}, approved=False)
        self.assertIsNone(assets.standard_for(self.conn, self.pid, "KELLY"))
        self.assertIsNone(assets.set_profile(self.conn, self.kelly, {"height_m": 99}, approved=True)["height_m"])  # not a person


if __name__ == "__main__":
    unittest.main()
