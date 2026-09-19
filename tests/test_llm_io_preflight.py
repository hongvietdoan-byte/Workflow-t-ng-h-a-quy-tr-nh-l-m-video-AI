import copy
import json
import unittest

from core.db import connect
from core.llm_io import (SchemaError, approve_motion_prompt, lock_character_bible, ready_for_video,
                         store_motion_prompts, store_scene_analysis,
                         validate_motion_prompts, validate_qc_result, validate_scene_analysis)
from core.pipeline import Pipeline
from core.preflight import check_characters, check_text, load_blocklist, record_failure

ANALYSIS = {
    "characters": [
        {"name": "Lyra", "description": "Nữ, tóc bạc, giáp cobalt"},
        {"name": "Nữ chiến binh Amazon", "description": "giáp vàng, khiên tròn", "wardrobe": "vòng tay bạc"},
    ],
    "scenes": [{"idx": 1, "location": "Rừng Elder", "time": "Đêm", "characters": ["Lyra"],
                "mood": "u ám", "lighting": "ánh trăng", "shot": "wide", "image_prompt": "misty forest"}],
}


class LlmIoTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.create_scene(self.pid, 1, "CẢNH 1")

    def test_valid_analysis_is_stored_and_locked(self):
        store_scene_analysis(self.p, self.pid, json.dumps(ANALYSIS, ensure_ascii=False))
        n = self.p.conn.execute("SELECT COUNT(*) c FROM characters").fetchone()["c"]
        self.assertEqual(n, 2)
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual(data["image_prompt"], "misty forest")
        self.assertEqual(lock_character_bible(self.p, self.pid), 1)

    def test_locked_character_not_overwritten(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        lock_character_bible(self.p, self.pid)
        changed = copy.deepcopy(ANALYSIS)
        changed["characters"][0]["description"] = "khác hoàn toàn"
        store_scene_analysis(self.p, self.pid, changed)
        desc = self.p.conn.execute("SELECT description FROM characters WHERE name='Lyra'").fetchone()[0]
        self.assertEqual(desc, "Nữ, tóc bạc, giáp cobalt")

    def test_unknown_character_in_scene_rejected(self):
        bad = copy.deepcopy(ANALYSIS)
        bad["scenes"][0]["characters"] = ["Ai đó"]
        with self.assertRaises(SchemaError):
            validate_scene_analysis(bad)

    def test_missing_field_rejected(self):
        bad = copy.deepcopy(ANALYSIS)
        del bad["scenes"][0]["lighting"]
        with self.assertRaises(SchemaError):
            validate_scene_analysis(bad)

    def test_unknown_scene_idx_rejected(self):
        bad = copy.deepcopy(ANALYSIS)
        bad["scenes"][0]["idx"] = 9
        with self.assertRaises(SchemaError):
            store_scene_analysis(self.p, self.pid, bad)

    def test_qc_result_validation(self):
        ok = {"criteria": {"character": 0.9, "mood": 1}}
        self.assertEqual(validate_qc_result(ok, ["character", "mood"]), ok)
        for bad in ({"criteria": {"character": 0.9}}, {"criteria": {"character": 1.5, "mood": 0.5}},
                    {"criteria": {"character": True, "mood": 0.5}}):
            with self.assertRaises(SchemaError):
                validate_qc_result(bad, ["character", "mood"])

    def test_motion_prompts_validation(self):
        validate_motion_prompts({"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        with self.assertRaises(SchemaError):
            validate_motion_prompts({"scenes": [{"idx": 1, "motion_prompt": "x", "duration_sec": 99}]})


class MotionPromptTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.scene = self.p.create_scene(self.pid, 1, "S1")

    def approved_image(self):
        job = self.p.create_job(self.scene)
        self.p.start(job)
        self.p.succeed(job)
        self.p.approve(job)

    def test_requires_approved_image(self):
        with self.assertRaises(SchemaError):
            store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})

    def test_store_approve_and_list_ready(self):
        self.approved_image()
        data = {"scenes": [{"idx": 1, "motion_prompt": "slow push-in", "duration_sec": 5}]}
        self.assertEqual(store_motion_prompts(self.p, self.pid, data), 1)
        self.assertEqual(ready_for_video(self.p, self.pid), [])
        approve_motion_prompt(self.p, self.scene)
        ready = ready_for_video(self.p, self.pid)
        self.assertEqual([r["motion_prompt"] for r in ready], ["slow push-in"])

    def test_editing_prompt_resets_approval(self):
        self.approved_image()
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "a"}]})
        approve_motion_prompt(self.p, self.scene)
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "b"}]})
        self.assertEqual(ready_for_video(self.p, self.pid), [])


class PreflightTests(unittest.TestCase):
    def test_blocklist_hits_wonder_woman_case_insensitive(self):
        entries = load_blocklist()
        self.assertTrue(check_text("a heroine like WONDER   woman", entries))
        self.assertEqual(check_text("Wonderful womanhood", entries), [])

    def test_character_check_flags_amazon_warrior(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.create_scene(pid, 1)
        store_scene_analysis(p, pid, ANALYSIS)
        warnings = check_characters(p.conn, pid, load_blocklist())
        self.assertEqual([w["character"] for w in warnings], ["Nữ chiến binh Amazon"])

    def test_record_failure(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        job = p.create_job(p.create_scene(pid, 1), "video_gen")
        record_failure(p.conn, job, "kling", "Failure to pass the risk control system")
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM content_moderation_failures").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
