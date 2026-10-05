"""S14.27: câu trả lời của người dùng cho việc ⏸ trong kế hoạch — lưu ở devsys/data/user_answers.json (không vào git),
ghi nguyên tử, file hỏng báo rõ (không ghi đè im lặng), CLI `py -m devsys.answers`, trang 📋 có ô trả lời cho mỗi việc ⏸."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from devsys import answers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AnswersCoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "sub", "user_answers.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_missing_file_is_empty(self):
        self.assertEqual(answers.load(self.path), {})
        self.assertEqual(answers.pending(self.path), [])

    def test_answer_is_saved_with_source_person_time_and_status(self):
        rec = answers.answer("S14.12", "Duyệt trần 10 USD", source="devsys", who="viet", choice="Duyệt", path=self.path)
        self.assertEqual(rec["status"], "answered")
        data = answers.load(self.path)
        got = data["S14.12"]
        self.assertEqual((got["task_id"], got["text"], got["choice"], got["source"], got["who"]),
                         ("S14.12", "Duyệt trần 10 USD", "Duyệt", "devsys", "viet"))
        self.assertTrue(got["at"])
        with open(self.path, encoding="utf-8") as f:
            raw = json.load(f)
        self.assertEqual(raw["format"], answers.FORMAT)
        self.assertEqual([r["task_id"] for r in answers.pending(self.path)], ["S14.12"])

    def test_editing_keeps_the_old_answer_in_history_and_reopens_an_applied_one(self):
        answers.answer("S14.12", "Để sau", path=self.path)
        answers.mark_applied("S14.12", "đã ghi kế hoạch · abc1234", path=self.path)
        self.assertEqual(answers.pending(self.path), [])
        answers.answer("S14.12", "Duyệt luôn", source="chat", path=self.path)
        got = answers.load(self.path)["S14.12"]
        self.assertEqual((got["text"], got["source"], got["status"]), ("Duyệt luôn", "chat", "answered"))
        self.assertEqual([h["text"] for h in got["history"]], ["Để sau"])
        self.assertEqual(got["history"][0]["status"], "applied")

    def test_mark_applied_records_note_and_time(self):
        answers.answer("S11.14", "Không", path=self.path)
        rec = answers.mark_applied("S11.14", "bỏ việc · 1a2b3c4", path=self.path)
        self.assertEqual((rec["status"], rec["applied_note"]), ("applied", "bỏ việc · 1a2b3c4"))
        self.assertTrue(rec["applied_at"])

    def test_mark_applied_without_an_answer_fails_loudly(self):
        with self.assertRaises(answers.AnswersError):
            answers.mark_applied("S14.99", "x", path=self.path)

    def test_bad_input_is_rejected(self):
        with self.assertRaises(answers.AnswersError):
            answers.answer("S14.12", "  ", path=self.path)                      # no text, no choice
        with self.assertRaises(answers.AnswersError):
            answers.answer("không phải mã", "x", path=self.path)
        with self.assertRaises(answers.AnswersError):
            answers.answer("S14.12", "x", source="email", path=self.path)
        self.assertFalse(os.path.exists(self.path))

    def test_choice_alone_is_an_answer(self):
        rec = answers.answer("S14.13", "", choice="Để sau", path=self.path)
        self.assertEqual((rec["choice"], rec["text"]), ("Để sau", ""))

    def test_corrupt_file_is_reported_and_never_overwritten(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{hỏng")
        with self.assertRaises(answers.AnswersError) as cm:
            answers.load(self.path)
        self.assertIn("user_answers.json", str(cm.exception))
        with self.assertRaises(answers.AnswersError):
            answers.answer("S14.12", "Duyệt", path=self.path)
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{hỏng")

    def test_wrong_format_is_reported(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"format": "khac/9", "answers": {}}, f)
        with self.assertRaises(answers.AnswersError):
            answers.load(self.path)

    def test_write_is_atomic_temp_file_then_replace(self):
        answers.answer("S14.12", "Duyệt", path=self.path)
        before = open(self.path, encoding="utf-8").read()
        with mock.patch.object(answers.os, "replace", side_effect=OSError("đĩa đầy")):
            with self.assertRaises(OSError):
                answers.answer("S14.13", "Không", path=self.path)
        self.assertEqual(open(self.path, encoding="utf-8").read(), before)           # the old file is untouched
        self.assertEqual([n for n in os.listdir(os.path.dirname(self.path)) if n != "user_answers.json"], [])  # no temp left

    def test_default_path_is_the_main_checkout_data_dir_or_the_env_override(self):
        with mock.patch.dict(os.environ, {"DEVSYS_ANSWERS_FILE": self.path}):
            self.assertEqual(answers.default_path(), self.path)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEVSYS_ANSWERS_FILE", None)
            p = answers.default_path()
        self.assertTrue(p.replace("\\", "/").endswith("devsys/data/user_answers.json"))
        self.assertNotIn(os.sep + "worktrees" + os.sep, p)             # a worktree session writes where the web (main checkout) reads


class AnswersCliTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "user_answers.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _cli(self, *args):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"DEVSYS_ANSWERS_FILE": self.path}), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(out):
            code = answers.main(list(args))
        return code, out.getvalue()

    def test_add_list_applied_round_trip(self):
        code, out = self._cli("add", "S14.12", "Duyệt trần 10 USD", "--source", "chat", "--who", "viet")
        self.assertEqual(code, 0, out)
        code, out = self._cli("list", "--pending")
        self.assertEqual(code, 0)
        self.assertIn("S14.12", out)
        self.assertIn("Duyệt trần 10 USD", out)
        code, out = self._cli("applied", "S14.12", "đã ghi kế hoạch · abc1234")
        self.assertEqual(code, 0, out)
        code, out = self._cli("list", "--pending")
        self.assertNotIn("S14.12", out)
        code, out = self._cli("list", "--json")
        self.assertEqual(json.loads(out)["S14.12"]["status"], "applied")

    def test_cli_errors_have_a_nonzero_exit_and_a_message(self):
        code, out = self._cli("applied", "S14.99", "x")
        self.assertNotEqual(code, 0)
        self.assertIn("S14.99", out)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{hỏng")
        code, out = self._cli("list")
        self.assertNotEqual(code, 0)
        self.assertIn("user_answers.json", out)

    def test_module_runs_as_python_m(self):
        env = dict(os.environ, DEVSYS_ANSWERS_FILE=self.path, PYTHONUTF8="1")
        r = subprocess.run([sys.executable, "-m", "devsys.answers", "list", "--pending"], cwd=ROOT, env=env, capture_output=True,
                           text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)


PLAN = ("### S14 — Thử\n- [ ] S14.12 · Dự án thử 30 s · nặng:3 · ⏸ · chờ duyệt trần\n- [ ] S14.13 · Dọn cờ · nặng:1 · ⏸ · sau S14.12\n"
        "- [ ] S14.27 · Ô trả lời · nặng:2 · ⬜\n")


class PlanPageAnswerBoxTests(unittest.TestCase):
    def setUp(self):
        try:
            from streamlit.testing.v1 import AppTest  # noqa: F401
        except ImportError:  # pragma: no cover
            self.skipTest("streamlit.testing không có")
        self.dir = tempfile.mkdtemp()
        self.plan = os.path.join(self.dir, "plan.md")
        with open(self.plan, "w", encoding="utf-8") as f:
            f.write(PLAN)
        self.path = os.path.join(self.dir, "user_answers.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _run(self):
        from streamlit.testing.v1 import AppTest
        from devsys import plan_progress
        at = AppTest.from_file(os.path.join(ROOT, "devsys", "app.py"), default_timeout=180)
        with mock.patch.object(plan_progress, "PLAN_FILE", self.plan), mock.patch.dict(os.environ, {"DEVSYS_ANSWERS_FILE": self.path}):
            at.run()
        return at

    def test_every_waiting_task_has_an_answer_box_and_saving_writes_the_file(self):
        from devsys import plan_progress
        at = self._run()
        self.assertEqual([e.value for e in at.exception], [])
        keys = [t.key for t in at.text_area]
        self.assertIn("ans-text-w-S14.12", keys)
        self.assertIn("ans-text-w-S14.13", keys)
        self.assertFalse(any("S14.27" in k for k in keys))                       # only ⏸ tasks get a box
        at.radio(key="ans-choice-w-S14.12").set_value("Duyệt")
        at.text_area(key="ans-text-w-S14.12").input("ok trần 10 USD")
        with mock.patch.object(plan_progress, "PLAN_FILE", self.plan), mock.patch.dict(os.environ, {"DEVSYS_ANSWERS_FILE": self.path}):
            at.button(key="ans-save-w-S14.12").click().run()
        self.assertEqual([e.value for e in at.exception], [])
        got = answers.load(self.path)["S14.12"]
        self.assertEqual((got["choice"], got["text"], got["source"], got["status"]), ("Duyệt", "ok trần 10 USD", "devsys", "answered"))
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("đã trả lời — chờ Claude áp dụng", text)

    def test_answered_and_applied_states_are_shown(self):
        answers.answer("S14.12", "Duyệt", path=self.path)
        answers.answer("S14.13", "Không", path=self.path)
        answers.mark_applied("S14.13", "bỏ việc · abc1234", path=self.path)
        at = self._run()
        self.assertEqual([e.value for e in at.exception], [])
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("đã trả lời — chờ Claude áp dụng", text)
        self.assertIn("đã áp dụng", text)
        self.assertIn("bỏ việc · abc1234", text)

    def test_a_corrupt_answers_file_is_shown_not_overwritten(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{hỏng")
        at = self._run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertTrue(any("user_answers.json" in e.value for e in at.error))
        self.assertEqual([t.key for t in at.text_area if t.key and t.key.startswith("ans-")], [])
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{hỏng")


if __name__ == "__main__":
    unittest.main()
