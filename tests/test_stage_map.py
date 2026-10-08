"""Đợt 3 tab kiểu chat (người dùng 07/10: chia khâu + đường dẫn rõ, dễ phân biệt, thông tin đủ không thừa; cờ chat_first):
bản đồ shot × khâu (Ảnh · Motion · Video) — mỗi ô một trạng thái, một dòng tóm tắt 'khâu đang làm'."""
import unittest

from core import stage_map as M
from core.db import connect
from core.pipeline import Pipeline

T = "2026-10-07T00:00:00Z"


class StageMapTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("x")
        self.sids = [self.p.create_scene(self.pid, i, f"CẢNH {i}") for i in (1, 2, 3)]

    def job(self, sid, kind, state):
        self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                            (self.pid, sid, kind, state, T, T))
        self.p.conn.commit()

    def test_each_cell_says_one_state(self):
        self.job(self.sids[0], "image_gen", "approved")
        self.job(self.sids[1], "image_gen", "pending_review")
        self.job(self.sids[2], "image_gen", "failed")
        self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?, 'x', 'pending')", (self.sids[0],))
        rows = M.build(self.p.conn, self.pid)
        self.assertEqual([r["idx"] for r in rows], [1, 2, 3])
        self.assertEqual([r["image"] for r in rows], ["done", "review", "failed"])
        self.assertEqual([r["motion"] for r in rows], ["review", "none", "none"])
        self.assertEqual({r["video"] for r in rows}, {"none"})

    def test_the_summary_names_the_stage_being_worked_on(self):
        self.job(self.sids[0], "image_gen", "approved")
        s = M.summary(M.build(self.p.conn, self.pid))
        self.assertEqual(s["counts"]["image"], (1, 3))
        self.assertEqual(s["current"], "image")
        for sid in self.sids[1:]:
            self.job(sid, "image_gen", "approved")
        self.assertEqual(M.summary(M.build(self.p.conn, self.pid))["current"], "motion")

    def test_running_and_empty(self):
        self.job(self.sids[0], "video_gen", "running")
        rows = M.build(self.p.conn, self.pid)
        self.assertEqual(rows[0]["video"], "running")
        self.assertEqual(M.summary([])["current"], None)


if __name__ == "__main__":
    unittest.main()


class OneClickTests(unittest.TestCase):
    def test_only_approve_everything_buttons_become_one_click_and_only_with_the_flag(self):
        import os
        from dashboard.design import components as D
        os.environ["FEATURE_CHAT_FIRST"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_CHAT_FIRST", None)
        for k in ("approve_all", "btn_ok_all", "script-cta-budget_7"):
            self.assertTrue(D.one_click(k), k)
        for k in ("del_all", "trash_empty", "approve_all_yes", "script-cta-lock_7"):
            self.assertFalse(D.one_click(k), k)
        os.environ["FEATURE_CHAT_FIRST"] = "0"
        self.assertFalse(D.one_click("approve_all"))


class VideoIdleReasonTests(unittest.TestCase):
    """Bố cục điểm 6 (người dùng 07/10): ▶ Gen video khóa với '(0 cảnh mới)' mà không nói vì sao — người mới không biết làm gì.
    Nút nói LÝ DO khi không có gì để gửi (0 USD, đọc bản đồ tiến độ)."""

    def r(self, motion, video):
        return {"idx": 1, "image": "done", "motion": motion, "video": video}

    def test_each_reason(self):
        self.assertIn("chưa duyệt motion", M.video_idle_reason([self.r("review", "none"), self.r("done", "done")]))
        self.assertIn("1 cảnh", M.video_idle_reason([self.r("review", "none"), self.r("done", "done")]))
        self.assertIn("đang gen", M.video_idle_reason([self.r("done", "running")]))
        self.assertIn("chờ duyệt", M.video_idle_reason([self.r("done", "review")]))
        self.assertIn("mọi cảnh đã có clip", M.video_idle_reason([self.r("done", "done")]))
        self.assertIn("chưa có cảnh", M.video_idle_reason([]))
