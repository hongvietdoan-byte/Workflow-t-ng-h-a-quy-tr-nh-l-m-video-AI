"""GĐ-E3 (docs/KE_HOACH_TONG_2026-09-24.md): F1 — the Character Bible text is checked against the library pictures before any picture is
paid for (GĐ6 R1: "Kelly đuôi ngựa" while the picture has short hair), cached per text + pictures; A15/A16/A20/F6 small fixes."""
import json
import os
import shutil
import tempfile
import unittest

from PIL import Image

from core import assets, claude_tasks, llm_runner, script_parser, shots, storyboard_gate
from core.db import connect
from core.pipeline import Pipeline


class Wrong(llm_runner.MockLlm):
    calls = 0

    def complete(self, prompt, images=()):
        if "Kiểm Character Bible" in prompt:
            Wrong.calls += 1
            out = {"characters": [{"name": "KELLY", "ok": False, "mismatches": ["mô tả 'tóc đuôi ngựa' — ảnh: tóc ngắn"],
                                   "fixed_description": "young woman with short white hair"}]}
            return llm_runner.LlmReply(json.dumps(out, ensure_ascii=False), 10, 5)
        return super().complete(prompt, images)


class BibleCheckTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.conn = connect(":memory:")
        self.p = Pipeline(self.conn)
        self.pid = self.p.create_project("P")
        a = assets.create(self.conn, "FF", "character", "KELLY")
        path = os.path.join(self.dir, "k.png")
        Image.new("RGB", (400, 900), (200, 200, 200)).save(path)
        with open(path, "rb") as f:
            assets.add_image(self.conn, a, "k.png", f.read())
        assets.attach(self.conn, self.pid, a)
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'girl with a ponytail')", (self.pid,))
        self.conn.commit()
        Wrong.calls = 0

    def test_a_mismatch_is_flagged_with_a_fix_and_the_check_is_cached(self):
        claude_tasks.bible_check(self.p, self.pid, Wrong())
        self.assertEqual(claude_tasks.bible_flags(self.p, self.pid), {"KELLY": ["mô tả 'tóc đuôi ngựa' — ảnh: tóc ngắn"]})
        claude_tasks.bible_check(self.p, self.pid, Wrong())
        self.assertEqual(Wrong.calls, 1)                                  # same text + pictures: no second paid call
        self.conn.execute("UPDATE characters SET description='young woman with short white hair' WHERE project_id=?", (self.pid,))
        self.conn.commit()
        self.assertEqual(claude_tasks.bible_flags(self.p, self.pid), {})  # the text changed: the old result no longer applies

    def test_the_run_waits_at_the_bible_when_it_contradicts_the_pictures_even_with_the_gate_off(self):
        from core import autopilot
        autopilot.set_gates(self.p, self.pid, {"bible": False})
        sid = self.p.create_scene(self.pid, 1, "x")
        self.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "Kelly runs", "characters": ["KELLY"]}), sid))
        self.conn.commit()
        ctx = autopilot.Context(data_dir=self.dir, image_runner=None, video_runner=None, llm=Wrong())
        with self.assertRaises(autopilot._Wait) as cm:
            autopilot._director_phase(self.p, self.pid, ctx)
        self.assertIn("mâu thuẫn với ảnh", str(cm.exception.args))


class SmallFixTests(unittest.TestCase):
    def test_a_content_line_is_not_a_scene_heading(self):
        scenes = script_parser.split_scenes(["CẢNH 1. BÃI BIỂN - NGÀY", "Nội dung: Kelly chạy trên cát.", "NỘI. NHÀ KELLY - ĐÊM", "Kelly ngủ."])
        self.assertEqual([s.heading for s in scenes], ["CẢNH 1. BÃI BIỂN - NGÀY", "NỘI. NHÀ KELLY - ĐÊM"])

    def test_a_shot_that_lists_nobody_stays_empty(self):
        scene = {"idx": 1, "characters": ["KELLY", "KENTA"]}
        base = {"image_prompt": "p", "size": "WS", "role": "setup", "action": "a", "duration_s": 3}
        self.assertEqual(shots.shot_data(scene, dict(base, characters=[]), 1)["characters"], [])
        self.assertEqual(shots.shot_data(scene, base, 1)["characters"], ["KELLY", "KENTA"])

    def test_a_first_word_guess_is_used_only_when_it_is_the_only_candidate(self):
        pool = [{"kind": "character", "images": [1], "name": n, "aliases": ""} for n in ("Kelly thức tỉnh", "Kelly bãi biển")]
        self.assertIsNone(assets.match_character(pool, "Kelly"))
        self.assertEqual(assets.match_character(pool[:1], "Kelly")["name"], "Kelly thức tỉnh")

    def test_a_long_single_clip_is_flagged(self):
        p = Pipeline(connect(":memory:"))
        pid = p.create_project("P")
        sid = p.create_scene(pid, 1, "x")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"duration_s": 15, "characters": []}), sid))
        p.conn.commit()
        self.assertTrue(any("nhiều nhịp" in f for f in storyboard_gate.flags(p, pid)[sid]))


if __name__ == "__main__":
    unittest.main()
