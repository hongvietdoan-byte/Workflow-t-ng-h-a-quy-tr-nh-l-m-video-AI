import os
import shutil
import tempfile
import unittest

from core import knowledge
from core.db import connect
from core.pipeline import Pipeline
from core.prompts import build_director_bundle, build_motion_bundle, build_qc_bundle
from tests.test_scene_regen import write  # noqa: F401  (shared helper)


def docx_bytes(paragraphs):
    """Smallest valid .docx with the given paragraphs."""
    import io
    import zipfile
    body = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in paragraphs)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_overview_lists_the_builtin_documents_with_sizes(self):
        ov = knowledge.overview("director")
        titles = [d["title"] for d in ov["docs"]]
        self.assertIn("Cơ bản điện ảnh", titles)
        self.assertIn("Ví dụ mẫu (few-shot)", titles)
        self.assertTrue(all(d["source"] == "builtin" and d["exists"] and d["chars"] > 0 for d in ov["docs"]))
        self.assertEqual(ov["chars"], sum(d["chars"] for d in ov["docs"]))
        self.assertEqual(ov["tokens"], knowledge.approx_tokens(ov["chars"]))
        self.assertEqual(ov["user_dir"], os.path.join(self.dir, "director"))
        self.assertEqual(knowledge.user_text("director"), "")

    def test_add_md_txt_and_docx_then_they_reach_the_prompt(self):
        knowledge.add_doc("director", "phong cach studio.md", "Luôn dùng tông màu lạnh.".encode("utf-8"), note="style")
        knowledge.add_doc("director", "loi hay gap.txt", "Tránh nhân vật đứng thẳng đơ.".encode("utf-8"))
        knowledge.add_doc("director", "mau.docx", docx_bytes(["Ví dụ tốt:", "Cảnh đêm rừng, sương mù."]))
        ov = knowledge.overview("director")
        user = [d for d in ov["docs"] if d["source"] == "user"]
        self.assertEqual(len(user), 3)
        self.assertIn("Cảnh đêm rừng, sương mù.", knowledge.read_doc("director", "user", user[2]["file"]))
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.create_scene(pid, 1, "S1")
        bundle = build_director_bundle(p, pid)
        self.assertIn("Tài liệu bổ sung do người dùng cung cấp", bundle)
        self.assertIn("Luôn dùng tông màu lạnh.", bundle)
        self.assertIn("Tránh nhân vật đứng thẳng đơ.", bundle)
        self.assertLess(bundle.index("Luôn dùng tông màu lạnh."), bundle.index("# Kịch bản đã tách cảnh"))
        self.assertNotIn("Luôn dùng tông màu lạnh.", build_qc_bundle(p, p.conn.execute("SELECT id FROM scenes").fetchone()["id"]))

    def test_each_step_has_its_own_documents(self):
        knowledge.add_doc("qc", "qc.md", "Chấm gắt hơn với bàn tay.".encode("utf-8"))
        knowledge.add_doc("motion", "mo.md", "Ưu tiên chuyển động chậm.".encode("utf-8"))
        p = Pipeline(connect())
        pid = p.create_project("t")
        scene = p.create_scene(pid, 1, "S1")
        self.assertIn("Chấm gắt hơn với bàn tay.", build_qc_bundle(p, scene))
        self.assertNotIn("Ưu tiên chuyển động chậm.", build_qc_bundle(p, scene))
        self.assertIn("Ưu tiên chuyển động chậm.", build_motion_bundle(p, pid))
        self.assertNotIn("Chấm gắt hơn với bàn tay.", build_director_bundle(p, pid))

    def test_switching_a_document_off_keeps_it_but_stops_sending_it(self):
        entry = knowledge.add_doc("director", "a.md", b"NOI DUNG A")
        before = knowledge.overview("director")["chars"]
        knowledge.set_enabled("director", entry["file"], False)
        self.assertEqual(knowledge.overview("director")["chars"], before - entry["chars"])
        self.assertEqual(knowledge.user_text("director"), "")
        self.assertTrue(any(d["file"] == entry["file"] and not d["enabled"] for d in knowledge.overview("director")["docs"]))
        knowledge.set_enabled("director", entry["file"], True)
        self.assertIn("NOI DUNG A", knowledge.user_text("director"))
        with self.assertRaises(KeyError):
            knowledge.set_enabled("director", "nope.md", True)

    def test_remove_deletes_the_file_and_the_entry(self):
        entry = knowledge.add_doc("qc", "x.md", b"abc")
        path = os.path.join(self.dir, "qc", entry["file"])
        self.assertTrue(os.path.exists(path))
        knowledge.remove_doc("qc", entry["file"])
        self.assertFalse(os.path.exists(path))
        self.assertEqual([d for d in knowledge.overview("qc")["docs"] if d["source"] == "user"], [])
        with self.assertRaises(KeyError):
            knowledge.remove_doc("qc", entry["file"])

    def test_limits_and_validation(self):
        with self.assertRaises(ValueError):
            knowledge.add_doc("director", "x.pdf", b"%PDF")
        with self.assertRaises(ValueError):
            knowledge.add_doc("director", "empty.md", b"  \n ")
        with self.assertRaises(ValueError):
            knowledge.add_doc("director", "big.md", ("x" * (knowledge.MAX_DOC_CHARS + 1)).encode())
        for i in range(3):  # 3 x 50k fits (150k); the 4th does not
            knowledge.add_doc("director", f"d{i}.md", ("y" * knowledge.MAX_DOC_CHARS).encode())
        with self.assertRaises(ValueError) as e:
            knowledge.add_doc("director", "d4.md", b"one more")
        self.assertIn("vượt", str(e.exception))
        with self.assertRaises(ValueError):
            knowledge.group_dir("unknown")

    def test_same_file_name_twice_and_unicode_names_are_kept_apart(self):
        a = knowledge.add_doc("director", "Hướng dẫn.md", b"1")
        b = knowledge.add_doc("director", "Hướng dẫn.md", b"2")
        self.assertNotEqual(a["file"], b["file"])
        self.assertEqual(knowledge.read_doc("director", "user", a["file"]), "1")
        self.assertEqual(knowledge.read_doc("director", "user", b["file"]), "2")

    def test_read_doc_cannot_escape_the_knowledge_folders(self):
        with self.assertRaises(ValueError):
            knowledge.read_doc("director", "user", "../../../etc/passwd")
        with self.assertRaises(ValueError):
            knowledge.read_doc("director", "builtin", "../core/db.py")

    def test_utf16_and_bom_text_decode(self):
        knowledge.add_doc("qc", "bom.txt", "﻿Xin chào".encode("utf-8"))
        knowledge.add_doc("qc", "u16.txt", "Tiếng Việt".encode("utf-16"))
        text = knowledge.user_text("qc")
        self.assertIn("Xin chào", text)
        self.assertIn("Tiếng Việt", text)


if __name__ == "__main__":
    unittest.main()
