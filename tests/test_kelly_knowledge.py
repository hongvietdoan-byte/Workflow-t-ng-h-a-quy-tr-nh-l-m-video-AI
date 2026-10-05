"""S14.34 Bước 1 — tri thức Kelly (S14.32) nạp vào Biên kịch / Đạo diễn / Quay phim / Dựng qua cờ `kelly_knowledge` (TẮT mặc định).

Luật: cờ tắt -> prompt Y HỆT trước (bản ghi S11.2 khoá theo sha256(prompt)); cờ bật -> thêm tài liệu GỢI Ý, không bắt buộc, trong trần ký tự."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import editor_review, features, idea_to_script as I, knowledge, prompts
from core.db import connect
from core.pipeline import Pipeline
from tests.test_idea_to_script import ANCHORS, IDEA, Recorder, make_kit

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCS = {"screenwriter": "kelly_bien_kich.md", "director": "kelly_dao_dien.md", "dp": "kelly_quay_phim.md", "editor": "kelly_dung.md"}


def _flags(**kw):
    return mock.patch.dict(os.environ, {f"FEATURE_{k.upper()}": v for k, v in kw.items()})


class FlagTests(unittest.TestCase):
    def test_flag_is_off_and_unverified(self):
        self.assertIn("kelly_knowledge", features.FEATURES)
        self.assertFalse(features.FEATURES["kelly_knowledge"]["verified"])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FEATURE_KELLY_KNOWLEDGE", None)
            self.assertFalse(features.on("kelly_knowledge"))

    def test_areas_json_declares_flag_and_test(self):
        import json
        text = open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8").read()
        json.loads(text)
        self.assertIn("kelly_knowledge", text)
        self.assertIn("tests/test_kelly_knowledge.py", text)


class DocsTests(unittest.TestCase):
    def test_docs_exist_and_say_suggestion_only(self):
        for name in DOCS.values():
            text = open(os.path.join(ROOT, "knowledge", "craft", name), encoding="utf-8").read()
            self.assertIn("GỢI Ý", text, name)
            self.assertLess(len(text), 6000, name)
            self.assertIn("MỞ RỘNG", text, name)              # người dùng 05/10: mở rộng phong cách, không áp đặt
            low = text.lower().replace("không bắt buộc", "")
            for hard in ("cấm", "bắt buộc", "tuyệt đối", "không được", "không viết"):
                self.assertNotIn(hard, low, f"{name}: '{hard}'")
        text = open(os.path.join(ROOT, "knowledge", "craft", DOCS["screenwriter"]), encoding="utf-8").read()
        for word in ("A.", "B.", "C.", "D.", "Kỹ thuật né", "Hook", "cú chốt"):
            self.assertIn(word, text)

    def test_kelly_blocks_empty_when_off(self):
        with _flags(kelly_knowledge="0"):
            for g in DOCS:
                self.assertEqual(knowledge.kelly_blocks(g), [])

    def test_kelly_blocks_when_on(self):
        with _flags(kelly_knowledge="1"):
            for g, name in DOCS.items():
                out = knowledge.kelly_blocks(g)
                self.assertEqual(len(out), 1, g)
                self.assertIn("GỢI Ý", out[0])
            with self.assertRaises(ValueError):
                knowledge.kelly_blocks("nope")

    def test_listed_doc_that_cannot_be_read_is_said_aloud(self):
        with _flags(kelly_knowledge="1"), mock.patch.object(knowledge, "_read", lambda p: ""):
            with self.assertRaises(FileNotFoundError):
                knowledge.kelly_blocks("director")

    def test_knowledge_page_lists_docs_only_with_flag(self):
        with _flags(kelly_knowledge="0"):
            self.assertFalse(any("kelly_" in d["file"] for d in knowledge.builtin_docs("director")))
        with _flags(kelly_knowledge="1"):
            files = {d["file"] for d in knowledge.builtin_docs("director")}
        self.assertTrue({"knowledge/craft/kelly_dao_dien.md", "knowledge/craft/kelly_quay_phim.md",
                         "knowledge/craft/kelly_dung.md"} <= files)

    def test_director_group_stays_under_the_char_limit(self):
        with _flags(kelly_knowledge="1", murch_knowledge="1", film_crew="1"):
            o = knowledge.overview("director")
            # what one run sends (raw_chars counts the crew-replaced books too and was already over before S14.34: 180 517)
            self.assertLess(o["chars"], knowledge.MAX_USER_CHARS)
            with _flags(kelly_knowledge="0"):
                before = knowledge.overview("director")["chars"]
            self.assertLess(o["chars"] - before, 6000)         # the three books together


class _Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": self.dir})
        self.env.start()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("kelly", operating_mode="human_qc")
        make_kit(self.p.conn)

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.dir, ignore_errors=True)


class ScreenwriterPromptTests(_Base):
    def _state(self):
        I.start(self.p.conn, self.pid, IDEA, anchors=ANCHORS)
        return I.get_state(self.p.conn, self.pid)

    def test_prompt_identical_when_off(self):
        st = self._state()
        with _flags(kelly_knowledge="0"):
            now = [I.build_prompt(self.p.conn, self.pid, st, t) for t in (1, 2, 3, 4)]
            with mock.patch.object(knowledge, "kelly_blocks", lambda g: []):
                without = [I.build_prompt(self.p.conn, self.pid, st, t) for t in (1, 2, 3, 4)]
        self.assertEqual(now, without)
        for text in now:
            self.assertNotIn("Bốn khuôn kịch bản", text)

    def test_prompt_has_the_formats_when_on(self):
        st = self._state()
        with _flags(kelly_knowledge="1"):
            on = I.build_prompt(self.p.conn, self.pid, st, 1)
        with _flags(kelly_knowledge="0"):
            off = I.build_prompt(self.p.conn, self.pid, st, 1)
        self.assertIn("Bốn khuôn kịch bản", on)
        self.assertGreater(len(on), len(off))
        # the buildable rules and the kit still come first, then the suggestions
        self.assertLess(on.index("Ràng buộc DỰNG ĐƯỢC"), on.index("Bốn khuôn kịch bản"))
        self.assertLess(on.index("Thứ dựng chắc được"), on.index("Bốn khuôn kịch bản"))


class CrewPromptTests(_Base):
    def test_bundles_identical_when_off_and_carry_docs_when_on(self):
        for crew in ("0", "1"):
            with _flags(kelly_knowledge="0", film_crew=crew):
                now = (prompts.build_director_bundle(self.p, self.pid), prompts.build_intent_bundle(self.p, self.pid))
                with mock.patch.object(knowledge, "kelly_blocks", lambda g: []):
                    without = (prompts.build_director_bundle(self.p, self.pid), prompts.build_intent_bundle(self.p, self.pid))
            self.assertEqual(now, without)
            self.assertFalse(any("Kelly -> Đạo diễn" in t for t in now))
        with _flags(kelly_knowledge="1", film_crew="1"):
            for t in (prompts.build_director_bundle(self.p, self.pid), prompts.build_intent_bundle(self.p, self.pid)):
                self.assertIn("Kelly -> Đạo diễn", t)

    def test_dp_common_carries_the_camera_doc_when_on(self):
        intent = {"characters": [], "scenes": []}
        with _flags(kelly_knowledge="0"):
            off = prompts.dp_common(self.p, self.pid, intent)
        with _flags(kelly_knowledge="1"):
            on = prompts.dp_common(self.p, self.pid, intent)
        self.assertNotIn("Kelly -> Quay phim", off)
        self.assertIn("Kelly -> Quay phim", on)

    def test_editor_prompt_carries_the_edit_doc_when_on(self):
        res = {"shots": [], "scenes": [], "sheets": [], "sound": {}, "coverage": {}, "flags": []}
        with _flags(kelly_knowledge="0"):
            off, _ = editor_review.editor_prompt(res)
        with _flags(kelly_knowledge="1"):
            on, _ = editor_review.editor_prompt(res)
        self.assertNotIn("Kelly -> Dựng", off)
        self.assertIn("Kelly -> Dựng", on)


if __name__ == "__main__":
    unittest.main()
