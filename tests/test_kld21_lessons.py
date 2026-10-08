"""KLD-21 / KLD-22 (người dùng duyệt 08/10): đường bài học chạy sau mỗi bản giao, bài học tổng kết dự án, tools/lessons_add.py,
và ca 'đạt' của người duyệt không ghi chú (#22: 0 success dù 9 ảnh + 9 clip đã duyệt)."""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from core import experience, lessons
from core.db import connect
from core.pipeline import Pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "TONG_HOP_3_LUOT_KHUNG_LONG_DO.md")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import lessons_add  # noqa: E402


def _decide(p, conn, kind, decision, note):
    pid = p.create_project("t")
    sid = p.create_scene(pid, 1, "s")
    j = p.create_job(sid, kind)
    conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (j,))
    (p.approve if decision == "approve" else p.reject)(j, "user", note=note, **({} if decision == "approve" else {"respawn": False}))
    return pid, j


class ReviewLogSuccessTests(unittest.TestCase):          # KLD-22
    def setUp(self):
        self.conn = connect(":memory:")
        self.p = Pipeline(self.conn)

    def test_an_approval_without_a_note_is_a_success_case(self):
        _decide(self.p, self.conn, "image_gen", "approve", None)
        _decide(self.p, self.conn, "video_gen", "approve", "  ")
        self.assertEqual(experience.import_review_log(self.conn, tempfile.mkdtemp()), 2)
        rows = [dict(r) for r in self.conn.execute("SELECT stage, outcome, note FROM experience_cases ORDER BY id")]
        self.assertEqual([(r["stage"], r["outcome"]) for r in rows], [("image", "success"), ("video", "success")])
        self.assertTrue(all(r["note"] for r in rows))                    # a readable note, not empty

    def test_a_rejection_without_a_reason_and_script_decisions_stay_out(self):
        _decide(self.p, self.conn, "image_gen", "reject", None)
        _decide(self.p, self.conn, "image_gen", "approve", experience.SCRIPT_MARK + " duyệt thử")
        self.assertEqual(experience.import_review_log(self.conn, tempfile.mkdtemp()), 0)


class ProjectReviewLessonTests(unittest.TestCase):       # KLD-21
    def setUp(self):
        self.conn = connect(":memory:")

    def test_a_one_project_lesson_is_proposed_with_its_confidence_and_kept_once(self):
        ok = lessons.add_project_review(self.conn, "qc", "L1", "Tiêu đề", "Phát hiện", project_id=22, context="Bối cảnh", origin="job 560")
        self.assertTrue(ok)
        again = lessons.add_project_review(self.conn, "qc", "L1", "Tiêu đề khác", "x", project_id=22)
        self.assertFalse(again)
        row = lessons.list_lessons(self.conn, "proposed")[0]
        self.assertEqual((row["source"], row["key"], row["state"]), ("project_review", "project_review:22:L1", "proposed"))
        self.assertIn("1 dự án", lessons.origin_text(row))
        self.assertIn("#22", lessons.origin_text(row))
        with self.assertRaises(ValueError):
            lessons.add_project_review(self.conn, "code", "L12", "t", "b", project_id=22)

    def test_after_delivery_harvests_mistakes_and_refreshes_cases(self):
        p = Pipeline(self.conn)
        _decide(p, self.conn, "image_gen", "reject", "tay thừa ngón")
        _decide(p, self.conn, "image_gen", "approve", None)
        with mock.patch("core.experience.import_qc_labels", return_value=0):
            res = lessons.after_delivery(self.conn, tempfile.mkdtemp())
        self.assertEqual(res, {"mistakes": 1, "cases": 2})

    def test_snapshot_after_delivery_runs_the_lesson_path_and_says_a_failure(self):
        from dashboard.steps import step5
        p = Pipeline(self.conn)
        pid = p.create_project("t")
        with mock.patch("core.effectiveness.snapshot"), mock.patch("core.lessons.after_delivery") as hook:
            step5.snapshot_after_delivery(p, pid)
        hook.assert_called_once()
        with mock.patch("core.effectiveness.snapshot"), \
                mock.patch("core.lessons.after_delivery", side_effect=RuntimeError("hỏng")), \
                mock.patch.object(step5.st, "warning") as warn, mock.patch.object(step5.st, "toast"):
            step5.snapshot_after_delivery(p, pid)                  # said, never raised
        warn.assert_called_once()
        self.assertIn("bài học", warn.call_args[0][0])


class LessonsAddToolTests(unittest.TestCase):           # KLD-21 tools/lessons_add.py
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "m.sqlite")
        connect(self.db).close()

    def run_tool(self, *extra):
        return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "lessons_add.py"), "--db", self.db, "--from", DOC,
                               "--section", "6", "--source", "project_review:22", *extra],
                              capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONUTF8="1"))

    def count(self):
        c = connect(self.db)
        try:
            return c.execute("SELECT count(*) FROM lessons").fetchone()[0]
        finally:
            c.close()

    def test_parse_the_table_of_section_6(self):
        rows = lessons_add.parse_section(open(DOC, encoding="utf-8").read(), "6")
        self.assertEqual([r["ref"] for r in rows], [f"L{n}" for n in range(1, 19)])
        plan = lessons_add.plan(rows)
        self.assertEqual(sorted({r["group"] for r in plan["ok"]}), ["director", "motion", "qc"])
        self.assertEqual(len(plan["ok"]), 11)
        self.assertEqual([r["ref"] for r in plan["skipped"]], [f"L{n}" for n in range(12, 19)])

    def test_dry_run_by_default_then_yes_writes_once(self):
        out = self.run_tool()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("CHẠY THỬ", out.stdout)
        self.assertEqual(self.count(), 0)
        out = self.run_tool("--yes")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.count(), 11)
        out = self.run_tool("--yes")
        self.assertEqual(self.count(), 11)                                  # same source + L# → not twice
        self.assertIn("đã có", out.stdout)

    def test_source_must_be_project_review(self):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "lessons_add.py"), "--db", self.db, "--from", DOC,
                              "--section", "6", "--source", "research"], capture_output=True, text=True, encoding="utf-8",
                             env=dict(os.environ, PYTHONUTF8="1"))
        self.assertNotEqual(out.returncode, 0)


if __name__ == "__main__":
    unittest.main()
