"""S14.4 C1b / J1 (04/10): errors a person reads are Vietnamese and say what to do — not English, not a class name."""
import ast
import os
import re
import unittest

from core import llm_io, llm_runner
from core.adapters import deepix
from core.db import connect
from core.pipeline import Pipeline
from core.providers import ProviderError

ROOT = os.path.join(os.path.dirname(__file__), "..")
ENGLISH = re.compile(r"\b(expected|must|missing|not in|already exists|does not exist|is locked|is not set|did not return)\b")
CHECKED = ("core/llm_io.py", "core/director_two_pass.py", "core/editor_review.py", "core/story_check.py")


def _raised_texts(path):
    """Constant text parts of every `raise SchemaError/ValueError/KeyError(...)` of a file."""
    tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    for n in ast.walk(tree):
        if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
            name = getattr(n.exc.func, "id", getattr(n.exc.func, "attr", ""))
            if name in ("SchemaError", "ValueError", "KeyError") and n.exc.args:
                for c in ast.walk(n.exc.args[0]):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str):
                        yield n.lineno, c.value


class ScanTests(unittest.TestCase):
    def test_no_english_validation_messages(self):
        bad = [f"{path}:{line} {text!r}" for path in CHECKED for line, text in _raised_texts(path) if ENGLISH.search(text)]
        self.assertEqual(bad, [])

    def test_the_money_card_does_not_show_only_a_class_name(self):
        src = open(os.path.join(ROOT, "dashboard", "header.py"), encoding="utf-8").read()
        self.assertNotIn("({type(e).__name__})", src)


class MessageTests(unittest.TestCase):
    def test_deepix_without_a_token_says_how_to_fix_it(self):
        old = os.environ.pop("DEEPIX_TOKEN", None)
        try:
            with self.assertRaises(ProviderError) as cm:
                deepix.DeepixImageProvider.from_env()
        finally:
            if old is not None:
                os.environ["DEEPIX_TOKEN"] = old
        self.assertIn("Chưa đặt DEEPIX_TOKEN", str(cm.exception))
        self.assertIn("Cách xử lý", str(cm.exception))

    def test_two_bad_answers_are_explained_in_vietnamese(self):
        class Bad:
            def complete(self, prompt, images=None):
                return llm_runner.LlmReply("not json", 1, 1)

        with self.assertRaises(llm_runner.LlmError) as cm:
            llm_runner.ask_json(Bad(), "p", lambda o: o)
        self.assertNotIn("did not return", str(cm.exception))
        self.assertIn("Cách xử lý", str(cm.exception))

    def test_a_bad_playbook_twice_is_explained_in_vietnamese(self):
        class Bad:
            def complete(self, prompt, images=None):
                return llm_runner.LlmReply("x", 1, 1)

        def refuse(text):
            raise ValueError("ngắn quá")
        with self.assertRaises(llm_runner.LlmError) as cm:
            llm_runner.ask_text(Bad(), "p", refuse)
        self.assertNotIn("did not return", str(cm.exception))
        self.assertIn("Cách xử lý", str(cm.exception))

    def test_an_unknown_knowledge_document_is_explained_in_vietnamese(self):
        import tempfile
        from unittest import mock
        from core import knowledge
        with mock.patch.dict(os.environ, {"KNOWLEDGE_USER_DIR": tempfile.mkdtemp()}):
            for fn in (lambda: knowledge.set_enabled("qc", "khong_co.md", True), lambda: knowledge.remove_doc("qc", "khong_co.md")):
                with self.assertRaises(KeyError) as cm:
                    fn()
                self.assertNotIn("is not an uploaded document", str(cm.exception))
                self.assertIn("tải lại trang", str(cm.exception))

    def test_editing_a_locked_character_is_explained_in_vietnamese(self):
        p = Pipeline(connect())
        pid = p.create_project("j1")
        llm_io.add_character(p, pid, "KELLY", "tóc ngắn")
        with self.assertRaises(ValueError) as cm:
            llm_io.add_character(p, pid, "KELLY", "tóc dài")
        self.assertIn("đã có", str(cm.exception))
        p.conn.execute("UPDATE characters SET locked=1 WHERE project_id=?", (pid,))
        p.conn.commit()
        with self.assertRaises(ValueError) as cm:
            llm_io.update_character(p, pid, "KELLY", "tóc dài")
        self.assertIn("Mở khóa", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
