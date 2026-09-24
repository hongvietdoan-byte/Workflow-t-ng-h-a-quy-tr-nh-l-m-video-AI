import os
import shutil
import tempfile
import unittest

from core import knowledge, llm_runner
from core.db import connect
from core.pipeline import Pipeline
from core.prompts import build_director_bundle, build_motion_bundle, build_qc_bundle

GOOD = ("## Phong cách & tông chung\n- Tông lạnh [studio]\n\n## Nhân vật & đối tượng\n- Giữ dấu hiệu nhận biết\n\n"
        "## Điều cần tránh\n- Tay 6 ngón")
# every required section of every step (Q2: a playbook missing one — e.g. cut off — is refused)
GOOD += "".join(f"\n\n## {name}\n- ..." for name in dict.fromkeys(n for names in knowledge.DISTILL_SECTIONS.values() for n in names)
                if f"## {name}\n" not in GOOD)


class DistillTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.scene = self.p.create_scene(self.pid, 1, "S1")
        knowledge.add_doc("director", "studio.md", ("Tông lạnh. " * 200).encode("utf-8"), title="studio")

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_bundle_asks_for_the_fixed_sections_and_carries_every_source(self):
        text = knowledge.build_distill_bundle("director")
        for name in knowledge.DISTILL_SECTIONS["director"]:
            self.assertIn(name, text)
        self.assertIn("### Tài liệu: studio", text)
        self.assertIn("Mâu thuẫn", text)
        self.assertNotIn("Cơ bản điện ảnh", text)  # built-in files only when asked
        self.assertIn("### Tài liệu: Cơ bản điện ảnh", knowledge.build_distill_bundle("director", include_builtin=True))
        os.remove(os.path.join(self.dir, "director", "docs.json"))
        with self.assertRaises(ValueError):
            knowledge.build_distill_bundle("director")  # nothing to distil

    def test_a_stored_playbook_replaces_the_raw_upload_in_the_prompt(self):
        before = build_director_bundle(self.p, self.pid)
        self.assertIn("Tông lạnh. Tông lạnh.", before)
        knowledge.store_distilled("director", GOOD)
        after = build_director_bundle(self.p, self.pid)
        self.assertNotIn("Tông lạnh. Tông lạnh.", after)
        self.assertIn("Cẩm nang kiến thức đã chắt lọc", after)
        self.assertIn("Tay 6 ngón", after)
        self.assertTrue("Knowledge pack — Biên kịch" in after)  # built-in knowledge still there (not folded)
        self.assertLess(len(after), len(before))

    def test_including_builtin_folds_them_and_shortens_every_run(self):
        raw = build_director_bundle(self.p, self.pid)
        knowledge.store_distilled("director", GOOD, include_builtin=True)
        folded = build_director_bundle(self.p, self.pid)
        self.assertLess(len(folded), len(raw) - 5000)
        self.assertFalse("Knowledge pack — Biên kịch" in folded)  # its text is summarised, not repeated
        ov = knowledge.overview("director")
        self.assertLess(ov["chars"], ov["raw_chars"])
        replaced = {d["title"] for d in ov["docs"] if d["replaced"]}
        self.assertEqual(replaced, {"Cơ bản điện ảnh", "Hướng dẫn 7 thể loại", "Nguyên tắc từ nguồn nghiên cứu", "Phương pháp đạo diễn", "Dịch skill → hình ảnh (67 nhân vật FF)", "Character Lock", "Viết thoại", "studio"})
        # the prompt file and the few-shot examples are never folded
        self.assertFalse(next(d for d in ov["docs"] if d["title"] == "Ví dụ mẫu (few-shot)")["replaced"])
        self.assertIn("Kịch bản đã tách cảnh", folded)

    def test_changing_the_sources_makes_the_playbook_stale_and_prompts_fall_back_to_raw(self):
        knowledge.store_distilled("director", GOOD)
        self.assertTrue(knowledge.distilled_status("director")["fresh"])
        knowledge.add_doc("director", "moi.md", "Quy tắc mới: luôn có sương mù.".encode("utf-8"))
        status = knowledge.distilled_status("director")
        self.assertEqual((status["exists"], status["fresh"], status["active"]), (True, False, False))
        bundle = build_director_bundle(self.p, self.pid)
        self.assertIn("Quy tắc mới: luôn có sương mù.", bundle)  # new knowledge still reaches Claude
        self.assertNotIn("Cẩm nang kiến thức đã chắt lọc", bundle)

    def test_switch_off_edit_and_clear(self):
        knowledge.store_distilled("director", GOOD)
        knowledge.set_use_distilled("director", False)
        self.assertFalse(knowledge.distilled_status("director")["active"])
        self.assertIn("Tông lạnh. Tông lạnh.", build_director_bundle(self.p, self.pid))
        knowledge.set_use_distilled("director", True)
        knowledge.store_distilled("director", GOOD + "\n\n## Ví dụ ngắn tiêu biểu\n- thêm")  # an edit by the user
        self.assertIn("thêm", knowledge.distilled_status("director")["text"])
        knowledge.clear_distilled("director")
        self.assertFalse(knowledge.distilled_status("director")["exists"])
        with self.assertRaises(KeyError):
            knowledge.set_use_distilled("director", True)

    def test_validation(self):
        for bad in ("", "chỉ một dòng", "## A\n- x\n\n## B\n- y", "## A\n" + "x" * (knowledge.MAX_DISTILLED_CHARS + 1)):
            with self.assertRaises(ValueError):
                knowledge.store_distilled("director", bad)
        cleaned = knowledge.validate_distilled("director", "```markdown\n" + GOOD + "\n```")
        self.assertTrue(cleaned.startswith("## Phong cách"))

    def test_each_step_distils_separately(self):
        knowledge.add_doc("qc", "qc.md", "Chấm gắt tay mặt. ".encode("utf-8") * 50)
        knowledge.store_distilled("qc", GOOD)
        self.assertTrue(knowledge.distilled_status("qc")["active"])
        self.assertFalse(knowledge.distilled_status("director")["exists"])
        self.assertIn("Cẩm nang kiến thức đã chắt lọc", build_qc_bundle(self.p, self.scene))
        self.assertNotIn("Cẩm nang kiến thức đã chắt lọc", build_motion_bundle(self.p, self.pid))

    def test_motion_folding_leaves_out_the_built_in_files(self):
        knowledge.add_doc("motion", "mo.md", b"Ua chuyen dong cham")
        raw = build_motion_bundle(self.p, self.pid)
        knowledge.store_distilled("motion", GOOD, include_builtin=True)
        folded = build_motion_bundle(self.p, self.pid)
        self.assertLess(len(folded), len(raw))
        self.assertIn("Cẩm nang kiến thức đã chắt lọc", folded)


class RunDistillTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        knowledge.add_doc("director", "a.md", b"Quy tac A. " * 100)

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_mock_model_produces_every_required_section(self):
        r = llm_runner.run_distill("director", llm_runner.MockLlm())
        status = knowledge.distilled_status("director")
        self.assertTrue(status["active"])
        for name in knowledge.DISTILL_SECTIONS["director"]:
            self.assertIn(f"## {name}", status["text"])
        self.assertEqual(r["source_chars"], status["source_chars"])
        self.assertEqual(r["input_tokens"], 200)

    def test_bad_answer_is_retried_once_with_the_reason_then_reported(self):
        prompts_seen = []

        class Sloppy:
            def __init__(self, answers):
                self.answers = list(answers)

            def complete(self, prompt, images=()):
                prompts_seen.append(prompt)
                return llm_runner.LlmReply(self.answers.pop(0), 10, 5)

        llm_runner.run_distill("director", Sloppy(["quá ngắn", GOOD]))
        self.assertIn("không đạt", prompts_seen[1])
        self.assertTrue(knowledge.distilled_status("director")["exists"])
        knowledge.clear_distilled("director")
        with self.assertRaises(llm_runner.LlmError) as e:
            llm_runner.run_distill("director", Sloppy(["x", "y"]))
        self.assertEqual(e.exception.code, "bad_text")
        self.assertFalse(knowledge.distilled_status("director")["exists"])  # nothing half-stored


if __name__ == "__main__":
    unittest.main()
