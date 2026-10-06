"""S14.46 (người dùng 06/10): lessons / mistakes / experience cases about removed features (phông xanh, sync.so, the 5 flags of S14.9…)
never reach a prompt; ordinary lessons still do; retiring is reversible and backed up; an old database migrates; the dry run changes
nothing."""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from core import diag, experience, features, knowledge, lessons, retired_topics
from core.db import connect
from core.pipeline import Pipeline
from core.prompts import build_director_bundle, build_motion_bundle, build_qc_bundle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GREEN = "Model vẽ cả cảnh thay vì phông xanh → bị dán thành khung chữ nhật lên nền 3D"
GREEN_OLD = "Ảnh ghép phông xanh (quy trình cũ) — chuyển sang ảnh toàn cảnh + storyboard tự vẽ cảnh"
PLAIN = "Tay Kenta thừa một ngón, mặt méo khi quay đầu"
BOOTS = "Kenta wears black sneakers instead of his dark blue-purple plated boots with buckle straps"


def diag_rows(conn, code):
    return conn.execute("SELECT * FROM diag_events WHERE code=?", (code,)).fetchall()


class TopicTests(unittest.TestCase):
    def test_removed_flags_and_other_removed_features_are_topics(self):
        names = set(retired_topics.topics())
        self.assertTrue(set(features.REMOVED) <= names)
        self.assertTrue({"sync_so", "ff_site_vm", "autopilot_daily_jobs"} <= names)

    def test_matches_whole_topic_words_not_short_lookalikes(self):
        self.assertEqual(retired_topics.matches(GREEN), ["location_plates"])
        self.assertEqual(retired_topics.matches("dùng plate_mode cũ"), ["location_plates"])
        self.assertEqual(retired_topics.matches("Khớp môi bằng sync.so"), ["sync_so"])
        self.assertEqual(retired_topics.matches(BOOTS), [])                       # "plated" is not a plate
        self.assertEqual(retired_topics.matches("Giảm chroma của da, ánh sáng ấm"), [])   # colour-grading word
        self.assertEqual(retired_topics.matches("Ánh sáng quá tối, phông nền đen"), [])
        self.assertEqual(retired_topics.matches("Đồng bộ âm thanh (sync) lệch 2 khung"), [])
        self.assertEqual(retired_topics.matches("máy VM chạy chậm"), [])
        self.assertEqual(retired_topics.matches(""), [])

    def test_a_fault_that_can_still_happen_is_kept(self):
        self.assertEqual(retired_topics.matches("Ghép lộ: mảng chữ nhật dán, đường nối thẳng (#8 ghép phông xanh)"), [])

    def test_decomposed_unicode_still_matches(self):
        import unicodedata
        self.assertEqual(retired_topics.matches(unicodedata.normalize("NFD", GREEN)), ["location_plates"])

    def test_hand_edited_file_adds_and_switches_off_topics(self):
        d = tempfile.mkdtemp()
        try:
            path = os.path.join(d, "retired_topics.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"old_tool": {"why": "bỏ", "patterns": [r"\bfoo_tool\b"]}, "sync_so": None}, f)
            os.environ["RETIRED_TOPICS_FILE"] = path
            self.assertEqual(retired_topics.matches("dùng foo_tool"), ["old_tool"])
            self.assertEqual(retired_topics.matches("sync.so"), [])
            with open(path, "w", encoding="utf-8") as f:
                f.write("{broken")
            os.utime(path, ns=(1, 1))
            self.assertEqual(retired_topics.matches("sync.so"), ["sync_so"])      # broken file → the built-in list, said
            self.assertTrue(retired_topics.file_error())
        finally:
            os.environ.pop("RETIRED_TOPICS_FILE", None)
            shutil.rmtree(d, ignore_errors=True)


class ExperienceFilterTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def add(self, key, note, **kw):
        return experience.record(self.conn, key=key, stage="qc_image", outcome="failure", note=note, source="t",
                                 subjects=["KENTA"], view="behind", confirmed_by="người", **kw)

    def test_case_about_a_removed_feature_is_not_shown_and_it_is_said_once(self):
        self.add("green", GREEN)
        self.add("green2", GREEN_OLD)
        self.add("plain", PLAIN)
        keys = [c["key"] for c in experience.relevant(self.conn, ["qc_image"], ["KENTA"], ["behind"], limit=4)]
        self.assertEqual(keys, ["plain"])
        rows = diag_rows(self.conn, "lesson_retired_topic")
        self.assertEqual(len(rows), 1)
        self.assertIn("2", rows[0]["message"])

    def test_retired_case_stays_retired_when_its_source_is_read_again(self):
        self.add("plain", PLAIN)
        self.add("x", "nhãn cũ")
        self.conn.execute("UPDATE experience_cases SET retired_at='2026-10-06', retired_why='t' WHERE key='x'")
        self.add("x", "nhãn mới", replace=True)                     # import_qc_labels re-reads with replace=True
        row = self.conn.execute("SELECT * FROM experience_cases WHERE key='x'").fetchone()
        self.assertEqual(row["retired_at"], "2026-10-06")
        self.assertEqual(row["note"], "nhãn mới")
        keys = [c["key"] for c in experience.relevant(self.conn, ["qc_image"], ["KENTA"], ["behind"])]
        self.assertEqual(keys, ["plain"])


class LessonFilterTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        self.p = Pipeline(connect())
        self.conn = self.p.conn

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def mistake(self, ref, project, text):
        self.conn.execute("INSERT INTO mistakes (source, ref_id, at, project_id, stage, group_name, text) VALUES ('t',?,?,?,?,?,?)",
                          (ref, "2026-10-06", project, "image", "director", text))

    def test_mistakes_about_a_removed_feature_never_become_a_lesson(self):
        for n in range(6):
            self.mistake(n, n % 3, GREEN + " — sai khung, cảnh lệch bố cục")      # would be 'composition' x6 in 3 projects
        for n in range(6, 10):
            self.mistake(n, n % 2, "Bàn tay thừa ngón")
        tags = {(c["group"], c["tag"]) for c in lessons.clusters(self.conn)}
        self.assertIn(("director", "hands"), tags)
        self.assertNotIn(("director", "composition"), tags)
        self.assertEqual(len(diag_rows(self.conn, "lesson_retired_topic")), 1)

    def test_retired_mistake_is_left_out_of_clusters(self):
        for n in range(4):
            self.mistake(n, n % 2, "Bàn tay thừa ngón")
        self.conn.execute("UPDATE mistakes SET retired_at='x' WHERE ref_id IN (0,1)")
        hands = [c for c in lessons.clusters(self.conn) if c["tag"] == "hands"][0]
        self.assertEqual(hands["events"], 2)

    def add_lesson(self, title, body, state="approved"):
        self.conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, state) VALUES (?,?,?,?,?,?,?)",
                          ("2026-10-06", "director", "k:" + title, title, body, "mistakes", state))
        self.conn.commit()

    def test_approved_lesson_on_a_removed_topic_is_not_written_into_the_step_document(self):
        self.add_lesson("Tránh lỗi tay", "Đếm ngón tay trước khi duyệt.")
        self.add_lesson("Phông xanh", "Luôn vẽ phông xanh trơn để ghép nền 3D.")
        lessons.sync_knowledge(self.conn, "director")
        text = knowledge.user_text("director")
        self.assertIn("Đếm ngón tay", text)
        self.assertNotIn("phông xanh", text.lower())
        self.assertEqual(len(diag_rows(self.conn, "lesson_retired_topic")), 1)
        self.assertEqual([r["title"] for r in lessons.list_lessons(self.conn, "approved")], ["Phông xanh", "Tránh lỗi tay"])

    def test_retired_lesson_is_hidden_from_lists_and_documents(self):
        self.add_lesson("Tránh lỗi tay", "Đếm ngón tay trước khi duyệt.")
        self.add_lesson("Cũ", "Bài học đã cất.")
        self.conn.execute("UPDATE lessons SET retired_at='x' WHERE title='Cũ'")
        lessons.sync_knowledge(self.conn, "director")
        self.assertNotIn("Bài học đã cất", knowledge.user_text("director"))
        self.assertEqual([r["title"] for r in lessons.list_lessons(self.conn, "approved")], ["Tránh lỗi tay"])

    def old_lessons_doc(self, group):
        """A lessons document written BEFORE S14.46 (still has the green-screen line)."""
        body = (f"# Bài học\n\n- **Tránh lỗi tay**: Đếm ngón tay.\n- **Phông xanh**: Vẽ phông xanh trơn.\n"
                "- **Khớp môi**: dùng sync.so cho đoạn thoại dài.\n")
        knowledge.add_doc(group, "bai_hoc.md", body.encode("utf-8"), title=lessons.DOC_TITLE)

    def test_prompts_of_every_step_leave_out_old_lesson_lines(self):
        for g in ("director", "qc", "motion"):
            self.old_lessons_doc(g)
        pid = self.p.create_project("t")
        sid = self.p.create_scene(pid, 1, "S1")
        bundles = {"director": build_director_bundle(self.p, pid), "qc": build_qc_bundle(self.p, sid)}
        for name, bundle in bundles.items():
            self.assertIn("Đếm ngón tay", bundle, name)
            self.assertNotIn("Vẽ phông xanh trơn", bundle, name)
            self.assertNotIn("sync.so cho đoạn thoại", bundle, name)
        motion = knowledge.user_text("motion", conn=self.conn)
        self.assertIn("Đếm ngón tay", motion)
        self.assertNotIn("phông xanh", motion.lower())
        self.assertTrue(diag_rows(self.conn, "lesson_retired_topic"))

    def test_motion_bundle_leaves_out_old_lesson_lines(self):
        self.old_lessons_doc("motion")
        pid = self.p.create_project("t")
        self.p.create_scene(pid, 1, "S1")
        try:
            bundle = build_motion_bundle(self.p, pid)
        except (ValueError, KeyError):
            self.skipTest("motion bundle needs approved pictures")
        self.assertNotIn("Vẽ phông xanh trơn", bundle)

    def test_uploaded_document_and_playbook_are_flagged_not_rewritten(self):
        knowledge.add_doc("director", "notes.md", "Ghi chú: thử phông xanh cho cảnh tháp.".encode("utf-8"))
        text = knowledge.user_text("director", conn=self.conn)
        self.assertIn("thử phông xanh", text)                     # the person's own document is not cut
        self.assertTrue(diag_rows(self.conn, "knowledge_retired_topic"))
        flagged = knowledge.retired_in_docs("director")
        self.assertEqual(flagged[0]["topics"], ["location_plates"])


class StorageTests(unittest.TestCase):
    def test_old_database_gets_the_columns_and_keeps_its_rows(self):
        d = tempfile.mkdtemp()
        try:
            path = os.path.join(d, "old.sqlite")
            c = sqlite3.connect(path)
            c.executescript("""
                CREATE TABLE mistakes (id INTEGER PRIMARY KEY, source TEXT NOT NULL, ref_id INTEGER NOT NULL, at TEXT NOT NULL,
                    project_id INTEGER, stage TEXT NOT NULL, group_name TEXT NOT NULL, text TEXT NOT NULL, UNIQUE (source, ref_id));
                CREATE TABLE lessons (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, group_name TEXT NOT NULL, key TEXT NOT NULL,
                    title TEXT NOT NULL, body TEXT NOT NULL, source TEXT NOT NULL, evidence TEXT, state TEXT NOT NULL DEFAULT 'proposed',
                    decided_at TEXT);
                CREATE TABLE experience_cases (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, at TEXT, stage TEXT, outcome TEXT,
                    project_id INTEGER, job_id INTEGER, shot TEXT, subjects TEXT, view TEXT, kind TEXT, note TEXT, evidence TEXT,
                    source TEXT, confirmed_by TEXT);
                INSERT INTO mistakes (source, ref_id, at, stage, group_name, text) VALUES ('review', 1, 'x', 'image', 'director', 'a');
                INSERT INTO experience_cases (key, note) VALUES ('review:1', 'b');
            """)
            c.commit()
            c.close()
            conn = connect(path)
            for t in ("mistakes", "lessons", "experience_cases"):
                self.assertTrue(retired_topics.has_columns(conn, t), t)
            self.assertEqual(conn.execute("SELECT text FROM mistakes").fetchone()[0], "a")
            self.assertIsNone(conn.execute("SELECT retired_at FROM experience_cases").fetchone()[0])
            conn.close()
        finally:
            shutil.rmtree(d, ignore_errors=True)


def _hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "data", "manifest.sqlite")
        os.makedirs(os.path.dirname(self.db))
        conn = connect(self.db)
        conn.execute("PRAGMA journal_mode = DELETE")
        for n, text in enumerate([GREEN, PLAIN, BOOTS, "Khớp môi sync.so lệch"]):
            conn.execute("INSERT INTO mistakes (source, ref_id, at, project_id, stage, group_name, text) VALUES ('review',?,?,?,?,?,?)",
                         (n, "x", 8, "image", "director", text))
        experience.record(conn, key="review:1", stage="image", outcome="failure", note=GREEN_OLD, source="review_log", confirmed_by="u")
        experience.record(conn, key="review:2", stage="image", outcome="failure", note=PLAIN, source="review_log", confirmed_by="u")
        conn.commit()
        conn.close()
        self.docs = os.path.join(self.dir, "docs")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_tool(self, *args):
        env = dict(os.environ, PYTHONUTF8="1", KNOWLEDGE_USER_DIR=os.path.join(self.dir, "ku"))
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "lessons_retire.py"), "--db", self.db, "--docs-dir", self.docs,
                            *args], capture_output=True, text=True, encoding="utf-8", env=env, cwd=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def retired(self):
        c = sqlite3.connect(self.db)
        out = sorted(c.execute("SELECT 'mistakes', ref_id FROM mistakes WHERE retired_at IS NOT NULL UNION ALL "
                               "SELECT 'experience_cases', key FROM experience_cases WHERE retired_at IS NOT NULL").fetchall())
        c.close()
        return out

    def test_dry_run_lists_candidates_and_changes_nothing(self):
        before = _hash(self.db)
        out = self.run_tool()
        self.assertEqual(_hash(self.db), before)
        self.assertIn("CHẠY THỬ", out)
        self.assertIn("location_plates", out)
        self.assertIn("sync_so", out)
        self.assertNotIn("plated boots", out)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "data", "backup")))
        self.assertFalse(os.path.exists(self.docs))

    def test_yes_backs_up_retires_writes_the_list_and_restore_gives_back(self):
        self.run_tool("--yes", "--keep", "mistakes:4")
        backups = os.listdir(os.path.join(self.dir, "data", "backup"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].startswith("manifest.before_lessons_retire_"))
        b = sqlite3.connect(os.path.join(self.dir, "data", "backup", backups[0]))
        self.assertEqual(b.execute("SELECT count(*) FROM mistakes").fetchone()[0], 4)
        b.close()
        self.assertEqual(self.retired(), [("experience_cases", "review:1"), ("mistakes", 0)])   # mistakes:4 = the sync.so one, kept
        c = sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT count(*) FROM mistakes").fetchone()[0], 4)             # nothing deleted
        why = c.execute("SELECT retired_why FROM mistakes WHERE ref_id=0").fetchone()[0]
        mid = c.execute("SELECT id FROM mistakes WHERE ref_id=0").fetchone()[0]
        c.close()
        self.assertIn("location_plates", why)
        listing = os.listdir(self.docs)
        self.assertEqual(len(listing), 1)
        self.assertTrue(listing[0].startswith("BAI_HOC_DA_CAT_"))
        with open(os.path.join(self.docs, listing[0]), encoding="utf-8") as f:
            md = f.read()
        self.assertIn("phông xanh", md)
        self.assertIn("--restore", md)
        out = self.run_tool("--restore", f"mistakes:{mid}")
        self.assertIn("khôi phục 1", out)
        self.assertEqual(self.retired(), [("experience_cases", "review:1")])
        self.run_tool("--restore", "all")
        self.assertEqual(self.retired(), [])

    def test_unknown_keep_id_is_refused(self):
        env = dict(os.environ, PYTHONUTF8="1")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "lessons_retire.py"), "--db", self.db, "--docs-dir", self.docs,
                            "--keep", "nope"], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
