"""S9 E0.1 (kế hoạch sau #8, người dùng duyệt 2026-09-28): one "next thing to do" line under each step's head, read from the state."""
import json
import unittest

from core import autopilot
from core.db import connect
from core.pipeline import Pipeline
from dashboard import next_step


def project():
    p = Pipeline(connect())
    return p, p.create_project("t")


class NextStepTests(unittest.TestCase):
    def test_step1_walks_from_script_to_lock(self):
        p, pid = project()
        self.assertIn("dán kịch bản", next_step.next_action(p, pid, 1)[0])
        sid = p.create_scene(pid, 1, "CẢNH 1")
        self.assertIn("Director", next_step.next_action(p, pid, 1)[0])
        p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', 'x')", (pid,))
        p.conn.commit()
        text, level = next_step.next_action(p, pid, 1)
        self.assertEqual(level, "todo")
        self.assertTrue("ảnh mốc" in text or "ngân sách" in text)
        self.assertIsNotNone(sid)
        p.conn.execute("UPDATE characters SET locked=1 WHERE project_id=?", (pid,))
        p.conn.commit()
        with __import__("unittest.mock", fromlist=["patch"]).patch("core.project_budget.enabled", return_value=False):
            self.assertEqual(next_step.next_action(p, pid, 1), ("Bước 1 xong — sang Bước 2", "done"))   # #8: locked, no anchors

    def test_a_waiting_automatic_run_comes_first(self):
        p, pid = project()
        p.create_scene(pid, 1, "CẢNH 1")
        autopilot._set(p, pid, "waiting", "Dừng ở storyboard: duyệt 10 khung")
        text, level = next_step.next_action(p, pid, 3)
        self.assertEqual(level, "wait")
        self.assertIn("duyệt 10 khung", text)

    def test_steps_2_to_5_count_what_is_left(self):
        p, pid = project()
        sid = p.create_scene(pid, 1, "CẢNH 1")
        self.assertIn("Gen ảnh cho 1 cảnh", next_step.next_action(p, pid, 2)[0])
        job = p.create_job(sid, "image_gen")
        p.start(job)
        p.succeed(job)
        p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (job,))
        p.conn.commit()
        self.assertIn("Duyệt 1 ảnh", next_step.next_action(p, pid, 2)[0])
        self.assertIn("Dựng video cuối", next_step.next_action(p, pid, 5)[0])
        from core import delivery
        delivery.record(p, pid, "final", "x.mp4", None, {"final_qc": {"blocks": 2, "warns": 0, "issues": []}})
        self.assertIn("2 lỗi chặn", next_step.next_action(p, pid, 5)[0])

    def test_the_band_never_breaks_a_step(self):
        p, pid = project()
        html = next_step.band(p, pid, 1)
        self.assertIn("nextband", html)
        self.assertIn("Việc tiếp theo", html)
        self.assertIn("Không đọc được", next_step.band(None, pid, 1))     # a broken state says so instead of raising
        self.assertEqual(json.loads("{}"), {})


if __name__ == "__main__":
    unittest.main()
