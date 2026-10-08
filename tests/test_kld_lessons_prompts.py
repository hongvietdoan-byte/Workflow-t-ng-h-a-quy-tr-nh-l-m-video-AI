"""KLD-8/9/12/14/15/25 (duyệt 08/10) — bài học #22 Khủng Long Đỏ vào prompt Đạo diễn / Quay phim / Motion / QC clip qua cờ
`kld_lessons_prompts` (TẮT mặc định). Cờ tắt → bundle gửi Claude Y HỆT trước; cờ bật → thêm đoạn bổ sung, ⚙ Kiến thức liệt kê đúng file."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import claude_tasks, features, knowledge, prompts
from core.db import connect
from core.pipeline import Pipeline

ROOT = os.path.join(os.path.dirname(__file__), "..")
FLAG = "kld_lessons_prompts"
MARK = {"director": "bài học dự án #22 Khủng Long Đỏ", "dp": "Bổ sung vai Quay phim", "motion": "Bổ sung quy tắc motion — bài học #22",
        "video_qc": "Bổ sung cách viết `issues`"}


def _flags(**kw):
    return mock.patch.dict(os.environ, {f"FEATURE_{k.upper()}": v for k, v in kw.items()})


class FlagAndDocs(unittest.TestCase):
    def test_flag_off_unverified_and_declared(self):
        self.assertIn(FLAG, features.FEATURES)
        self.assertFalse(features.FEATURES[FLAG]["verified"])
        with mock.patch.dict(os.environ, {}):
            os.environ.pop("FEATURE_KLD_LESSONS_PROMPTS", None)
            self.assertFalse(features.on(FLAG))
        text = open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8").read()
        json.loads(text)
        self.assertIn(FLAG, text)
        self.assertIn("tests/test_kld_lessons_prompts.py", text)

    def test_blocks_empty_off_and_present_on(self):
        with _flags(kld_lessons_prompts="0"):
            for g in MARK:
                self.assertEqual(knowledge.kld_blocks(g), [])
        with _flags(kld_lessons_prompts="1"):
            for g, mark in MARK.items():
                out = knowledge.kld_blocks(g)
                self.assertEqual(len(out), 1, g)
                self.assertIn(mark, out[0])
                self.assertIn("1 dự án", out[0])          # độ tin ghi rõ — không khái quát từ một mẫu
            with self.assertRaises(ValueError):
                knowledge.kld_blocks("nope")

    def test_unreadable_doc_is_said_aloud(self):
        with _flags(kld_lessons_prompts="1"), mock.patch.object(knowledge, "_read", lambda p: ""):
            with self.assertRaises(FileNotFoundError):
                knowledge.kld_blocks("director")

    def test_each_kld_item_is_written(self):
        d = knowledge.kld_text("director")
        for s in ("tradeoffs", "Hô biến", "script_notes", "dialogue_take", "0,03 / 0,44"):
            self.assertIn(s, d)
        self.assertIn("đen có sừng đỏ", d)
        self.assertIn("đeo kín", d)
        self.assertIn("điểm cuối", knowledge.kld_text("dp"))
        self.assertIn("không có nghĩa mặc định", knowledge.kld_text("dp"))
        m = knowledge.kld_text("motion")
        self.assertIn("chỉ-ảnh-tham-chiếu", m)
        self.assertIn("mask worn up over nose and mouth", m)
        self.assertIn("đứng đơ", m)
        q = knowledge.kld_text("video_qc")
        self.assertIn("trạng thái đúng", q)
        self.assertIn("model property — regenerating with the same route will not fix it", q)

    def test_knowledge_page_lists_docs_only_with_flag(self):
        with _flags(kld_lessons_prompts="0", film_crew="1"):
            self.assertFalse(any("kld22" in d["file"] for g in ("director", "motion") for d in knowledge.builtin_docs(g)))
        with _flags(kld_lessons_prompts="1", film_crew="1"):
            dfiles = {d["file"] for d in knowledge.builtin_docs("director")}
            mfiles = {d["file"] for d in knowledge.builtin_docs("motion")}
        self.assertTrue({"knowledge/roles/director_kld22.md", "knowledge/roles/dp_kld22.md"} <= dfiles)
        self.assertIn("prompts/03_video_motion_kld22.md", mfiles)


class Bundles(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": self.dir})
        self.env.start()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("kld", operating_mode="human_qc")

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def _all(self):
        intent = {"characters": [], "scenes": []}
        return (prompts.build_director_bundle(self.p, self.pid), prompts.build_intent_bundle(self.p, self.pid),
                prompts.dp_common(self.p, self.pid, intent), prompts.build_motion_bundle(self.p, self.pid),
                claude_tasks.video_qc_head())

    def test_off_is_byte_identical(self):
        for crew in ("0", "1"):
            with _flags(kld_lessons_prompts="0", film_crew=crew):
                now = self._all()
                with mock.patch.object(knowledge, "kld_blocks", lambda g: []):
                    without = self._all()
            self.assertEqual(now, without)
            for t in now:
                self.assertNotIn("#22 Khủng Long Đỏ", t)
        with _flags(kld_lessons_prompts="0"):
            head = claude_tasks.video_qc_head()
        self.assertEqual(head, claude_tasks._read("prompts", "12_video_qc.md") + "\n\n---\n\n"
                         + claude_tasks._read("knowledge", "character_lock.md"))

    def test_on_carries_the_lessons(self):
        with _flags(kld_lessons_prompts="1", film_crew="1"):
            director, intent, dp, motion, qc = self._all()
        self.assertIn(MARK["director"], director)
        self.assertIn(MARK["director"], intent)
        self.assertIn(MARK["dp"], dp)
        self.assertIn(MARK["motion"], motion)
        self.assertIn(MARK["video_qc"], qc)
        self.assertLess(qc.index(MARK["video_qc"]), qc.index("---"))  # right after the QC prompt, before Character Lock


if __name__ == "__main__":
    unittest.main()
