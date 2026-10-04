"""S14.17 UI (cờ ui_v2): thẻ ảnh Storyboard và thẻ clip Video hiện mục gập "✏ Prompt đã sửa (vN)" khi Đạo diễn đã viết lại prompt shot —
so sánh cũ/mới + danh sách thay đổi + nút "↩ Dùng lại prompt cũ" (không tốn tiền, không tạo job). 0 USD (Claude giả)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import llm_runner, prompt_rewrite
from core.db import connect
from core.llm_io import lock_character_bible, store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class Fake:
    def __init__(self, new):
        self.new = new

    def complete(self, prompt, images=()):
        return llm_runner.LlmReply(json.dumps({"new_prompt": self.new, "changed": ["Đổi màu áo (thử)"], "why": "thử"}), 10, 10)


class PromptVersionsUi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                                           "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku"), "FEATURE_UI_V2": "1",
                                           "DASHBOARD_EXPERT": "1", "FEATURE_DIRECTOR_REWRITE": "1",
                                           "FEATURE_SETTINGS_FILE": os.path.join(self.tmp, "none.json")})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("Demo")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        lock_character_bible(self.p, self.pid)
        self.sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchone()["id"]

    def rewrite(self, job, new):
        with mock.patch.object(prompt_rewrite, "client_for", lambda p: Fake(new)):
            self.p.reject(job, "user", "đổi màu áo")

    def open(self, step):
        at = AppTest.from_file(APP, default_timeout=60).run()
        at.radio(key="step").set_value(at.radio(key="step").options[step]).run()
        self.assertFalse(at.exception, at.exception)
        return at

    def test_storyboard_card_shows_old_new_and_reverts_for_free(self):
        old = prompt_rewrite.current_prompt(self.p.conn, self.sid, "image")
        job = self.p.create_job(self.sid)
        self.p.start(job)
        self.p.succeed(job)
        self.p.apply_qc(job, {"a": 0.9, "b": 0.9})
        self.rewrite(job, "a brand new prompt for the shot")
        at = self.open(2)
        labels = [e.label for e in at.expander]
        self.assertTrue(any(lbl.startswith("✏ Prompt đã sửa (v2)") for lbl in labels), labels)
        html = " ".join(m.value for m in at.markdown)
        self.assertIn("line-through", html)
        self.assertIn("Đổi màu áo (thử)", html)
        jobs_before = self.p.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        at.button(key=f"pvrevert_image_{self.sid}").click().run()
        self.assertFalse(at.exception, at.exception)
        conn = connect(self.db)
        self.assertEqual(prompt_rewrite.current_prompt(conn, self.sid, "image"), old)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], jobs_before)

    def test_video_card_shows_the_motion_prompt_rewrite(self):
        self.p.conn.execute("INSERT OR REPLACE INTO motion_prompts (scene_id, motion_prompt, state) VALUES (?,?, 'approved')",
                            (self.sid, "Fast whip pan"))
        self.p.conn.commit()
        job = self.p.create_job(self.sid, "video_gen")
        self.p.start(job)
        self.p.succeed(job)
        self.rewrite(job, "Slow steady pan")
        new = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["id"]
        self.p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (new,))
        self.p.conn.commit()
        at = self.open(3)
        self.assertTrue(any(e.label.startswith("✏ Prompt đã sửa (v2)") for e in at.expander))
        self.assertIn(f"pvrevert_video_{self.sid}", {b.key for b in at.button})


class SpinnerScan(unittest.TestCase):
    """Rà S14.17 #3: mọi nút có thể gọi Đạo diễn (Loại & gen lại kèm ghi chú, bỏ duyệt kèm ghi chú, gen lại clip kèm câu sửa) chạy dưới
    spinner — người dùng thấy đang chờ Claude thay vì trang đứng im."""

    def test_every_rewrite_button_runs_under_the_spinner(self):
        import re
        root = os.path.join(os.path.dirname(__file__), "..", "dashboard")
        files = [os.path.join(root, "steps", "step2.py"), os.path.join(root, "steps", "step4.py"),
                 os.path.join(root, "design", "screens", "storyboard_cards.py")]
        bad = []
        for path in files:
            for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
                calls = re.search(r"act\((.*)", line)
                if not calls:
                    continue
                body = calls.group(1)
                paid = ((re.search(r"p\.reject\([^)]*\"user\"", body) and "respawn=False" not in body)
                        or re.search(r"reopen_approved\(jid, r_note", body) or re.search(r"regenerate_video\(.*fix=", body))
                if paid and not body.startswith("_spin("):
                    bad.append(f"{os.path.basename(path)}:{n}")
        self.assertEqual(bad, [])

    def test_spinner_only_when_the_flag_is_on(self):
        import contextlib
        from dashboard.design.screens import prompt_versions_ui as PV
        with mock.patch.dict(os.environ, {"FEATURE_DIRECTOR_REWRITE": "0", "FEATURE_SETTINGS_FILE": os.path.join(tempfile.mkdtemp(), "n.json")}):
            self.assertIsInstance(PV.busy(), contextlib.nullcontext)
            self.assertEqual(PV.spin(lambda: 7)(), 7)


if __name__ == "__main__":
    unittest.main()
