"""UI v2 (S13, lane G) — Video screen: clip cards, hero, kept widget keys, flag OFF = the classic card."""
import json
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import qc_scene
from core.db import connect
from core.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
V2 = {"FEATURE_UI_V2": "1"}
STEP_VIDEO, STEP_DELIVER = 3, 4


class VideoSeed(unittest.TestCase):
    """A project with one video job per state: succeeded, pending_review, failed, queued, approved."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        self.data = os.path.join(self.tmp, "projects")
        patcher = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data,
                                               "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "k")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("Demo video")
        os.makedirs(os.path.join(self.data, str(self.pid), "videos"), exist_ok=True)
        self.jobs = {}
        for idx, state in enumerate(["succeeded", "pending_review", "failed", "queued", "approved"], start=1):
            scene = self.p.create_scene(self.pid, idx, f"CẢNH {idx}")
            jid = self.p.create_job(scene, "video_gen")
            path = None
            if state in ("succeeded", "pending_review", "approved"):
                path = os.path.join(self.data, str(self.pid), "videos", f"{idx:02d}.mp4")
                with open(path, "wb") as f:
                    f.write(b"not a real video")
            self.p.conn.execute("UPDATE jobs SET state=?, result_path=?, model='kling-v3-omni' WHERE id=?", (state, path, jid))
            self.jobs[state] = jid
        # layer-0 measurement on the first frame that feeds the pending_review clip
        scene2 = self.p.conn.execute("SELECT scene_id FROM jobs WHERE id=?", (self.jobs["pending_review"],)).fetchone()["scene_id"]
        src = self.p.create_job(scene2, "image_gen")
        self.p.conn.execute("UPDATE jobs SET source_job_id=? WHERE id=?", (src, self.jobs["pending_review"]))
        self.p.conn.commit()
        qc_scene.record_flags(self.data, self.pid, src, [{"code": "shot_size", "severity": "flag", "problem": "cỡ cảnh đo được MS — shot xin CU",
                                                          "fix": "Frame as a close-up."}])
        self.p.conn.execute("INSERT INTO qc_results (job_id, criterion, score, threshold_at_time, auto_decision) VALUES (?,?,?,?,?)",
                            (self.jobs["pending_review"], "identity", 0.91, 0.85, "pass"))
        self.p.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,datetime('now'))",
                            (self.jobs["pending_review"], "ai_agent", "reject", "Tay phải hơi lệch khi xoay người"))
        self.p.conn.commit()

    def open_video(self, v2=True) -> AppTest:
        env = dict(V2) if v2 else {"FEATURE_UI_V2": "0"}
        with mock.patch.dict(os.environ, env):
            at = AppTest.from_file(APP, default_timeout=40).run()
            at.radio(key="step").set_value(at.radio(key="step").options[STEP_VIDEO]).run()
        self.assertFalse(at.exception, at.exception)
        return at


def md(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


class VideoV2Tests(VideoSeed):
    def test_every_state_has_a_card_with_the_fixed_pill_text(self):
        at = self.open_video()
        html = md(at)
        self.assertIn("v2-pill", html)
        for text in ("Lỗi", "Chờ gen", "Đã duyệt"):
            self.assertEqual(html.count(f">{text}<"), 1, text)
        self.assertEqual(html.count(">Cần duyệt<"), 2)                       # succeeded + pending_review both wait for the person

    def test_hero_shows_stats_and_progress(self):
        html = md(self.open_video())
        for label in ("Clip dùng được", "Chờ duyệt", "Lỗi / đã loại", "Tiền video đã chi"):
            self.assertIn(label, html)
        self.assertIn("v2-meter", html)

    def test_measurements_notes_and_model_line_are_chips_and_rows(self):
        html = md(self.open_video())
        self.assertIn("Đo lớp 0", html)                                  # layer-0 row
        self.assertIn("cỡ cảnh đo được MS", html)
        self.assertIn("Giữ đúng nhân vật", html)
        self.assertIn("**0.91**", html)
        self.assertIn("Ghi chú QC", html)
        self.assertIn("Tay phải hơi lệch", html)
        self.assertIn("kling-v3-omni", html)

    def test_details_sit_behind_an_info_popover(self):
        at = self.open_video()
        self.assertGreaterEqual(len(at.get("popover")), 3)             # QC criteria, layer-0 measurements and QC note sit behind ⓘ

    def test_old_widget_keys_are_kept(self):
        at = self.open_video()
        keys = {b.key for b in at.button}
        j = self.jobs
        for k in (f"va_{j['pending_review']}", f"vr_rej_{j['pending_review']}", f"vregen_{j['pending_review']}", f"vfix_{j['pending_review']}",
                  f"vr_{j['failed']}", f"vfix_{j['failed']}", f"va_{j['succeeded']}", f"vregen_{j['approved']}", "btn_bad_retry"):
            self.assertIn(k, keys, k)
        self.assertIn(f"vnote_{j['pending_review']}", {t.key for t in at.text_input})
        self.assertIn(f"vfixtxt_{j['failed']}", {t.key for t in at.text_input})
        self.assertIn(f"vaudio_{self.pid}", {c.key for c in at.checkbox})

    def test_actions_have_text_labels_and_the_regen_price(self):
        at = self.open_video()
        labels = {b.key: b.label for b in at.button}
        self.assertIn("Duyệt", labels[f"va_{self.jobs['pending_review']}"])
        self.assertIn("Gen lại", labels[f"vregen_{self.jobs['pending_review']}"])
        self.assertIn("Sửa motion prompt", labels[f"vfix_{self.jobs['pending_review']}"])
        self.assertIn("Loại", labels[f"vr_rej_{self.jobs['pending_review']}"])
        self.assertRegex(labels[f"vregen_{self.jobs['pending_review']}"], r"≈ \d|chưa có giá")

    def test_approve_button_approves_the_pending_clip(self):
        at = self.open_video()
        next(b for b in at.button if b.key == f"va_{self.jobs['pending_review']}").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(Pipeline(connect(self.db)).job(self.jobs["pending_review"])["state"], "approved")

    def test_approve_is_disabled_when_nothing_to_review(self):
        at = self.open_video()
        self.assertTrue(next(b for b in at.button if b.key == f"va_{self.jobs['approved']}").disabled)
        self.assertTrue(next(b for b in at.button if b.key == f"vr_rej_{self.jobs['approved']}").disabled)

    def test_edit_motion_prompt_opens_the_motion_tab(self):
        at = self.open_video()
        next(b for b in at.button if b.key == f"vfix_{self.jobs['pending_review']}").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(at.session_state["step"].startswith("Storyboard"))
        self.assertIn("Motion", at.session_state["sb_tab"])

    def test_clip_set_redo_button_still_exists(self):
        folder = os.path.join(self.data, str(self.pid), "qc_set")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "clips_result.json"), "w", encoding="utf-8") as f:
            json.dump({"ok": False, "summary": "lệch màu", "issues": [{"idx": 5, "problem": "màu lệch", "fix": "Match the warm grade."}]}, f)
        at = self.open_video()
        self.assertIn(f"clipqc_redo_{self.pid}_0", {b.key for b in at.button})

    def test_empty_project_shows_an_empty_state_with_one_action(self):
        other = self.p.create_project("Trống")
        with mock.patch.dict(os.environ, V2):
            at = AppTest.from_file(APP, default_timeout=40)
            at.session_state["global_pid"] = other
            at.run()
            at.radio(key="step").set_value(at.radio(key="step").options[STEP_VIDEO]).run()
        self.assertFalse(at.exception)
        self.assertIn("Chưa có clip nào", md(at))
        self.assertIn(f"vid-empty-go_{other}", {b.key for b in at.button})


class VideoClassicTests(VideoSeed):
    def test_flag_off_keeps_the_classic_card(self):
        at = self.open_video(v2=False)
        html = md(at)
        self.assertNotIn("v2-pill", html)
        keys = {b.key for b in at.button}
        j = self.jobs
        for k in (f"va_{j['pending_review']}", f"vr_rej_{j['pending_review']}", f"vr_{j['failed']}", f"vregen_{j['succeeded']}"):
            self.assertIn(k, keys, k)
        self.assertNotIn(f"vfix_{j['pending_review']}", keys)                 # the always-visible edit button is v2 only


if __name__ == "__main__":
    unittest.main()
