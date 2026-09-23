import json
import unittest

from core.db import connect
from core.llm_io import store_scene_analysis, validate_qc_result
from core.pipeline import Pipeline
from core.prompts import build_director_bundle, build_motion_bundle, build_qc_bundle, qc_criteria
from tests.test_llm_io_preflight import ANALYSIS


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.sid = self.p.create_scene(self.pid, 1, "CẢNH 1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"text": "Sương mù dày đặc."}, ensure_ascii=False), self.sid))
        store_scene_analysis(self.p, self.pid, ANALYSIS)

    def test_director_bundle_contains_prompt_knowledge_and_scenes(self):
        text = build_director_bundle(self.p, self.pid)
        self.assertIn("Character Bible", text)
        self.assertIn("Slugline", text)
        self.assertIn("Sương mù dày đặc.", text)
        self.assertIn("Hướng dẫn theo thể loại", text)
        self.assertIn("Ví dụ mẫu", text)

    def test_qc_bundle_has_bible_and_spec(self):
        text = build_qc_bundle(self.p, self.sid)
        self.assertIn("Lyra", text)
        self.assertIn("misty forest", text)

    def test_qc_bundle_includes_failure_modes(self):
        self.assertIn("Lỗi thường gặp của ảnh AI", build_qc_bundle(self.p, self.sid))

    def test_motion_bundle_lists_only_scenes_with_approved_image(self):
        self.assertNotIn("misty forest", build_motion_bundle(self.p, self.pid))
        job = self.p.create_job(self.sid)
        self.p.start(job)
        self.p.succeed(job)
        self.p.approve(job)
        text = build_motion_bundle(self.p, self.pid)
        self.assertIn("misty forest", text)
        self.assertIn("Từ vựng camera", text)

    def test_motion_bundle_adds_seedance_guide_only_for_seedance(self):
        job = self.p.create_job(self.sid)
        self.p.start(job)
        self.p.succeed(job)
        self.p.approve(job)
        self.assertNotIn("Seedance — cách viết motion prompt", build_motion_bundle(self.p, self.pid))
        self.p.set_video_model(self.pid, "seedance-2.5")
        self.assertIn("Seedance — cách viết motion prompt", build_motion_bundle(self.p, self.pid))
        self.p.set_video_model(self.pid, "kling")
        self.assertNotIn("Seedance — cách viết motion prompt", build_motion_bundle(self.p, self.pid))

    def test_checklist_keys_match_qc_prompt(self):
        keys = qc_criteria()
        self.assertEqual(keys, ["character", "hands_face", "composition", "mood_lighting", "consistency", "scale", "grounding", "set_match"])
        ok = {"criteria": {k: 0.9 for k in keys}}
        self.assertEqual(validate_qc_result(ok, keys), ok)


if __name__ == "__main__":
    unittest.main()
