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
        self.assertIn("Kling 3.0 Omni", html)                              # KLD-23: the real model name, not the alias

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


class QueuedClipsAreSentTests(VideoSeed):
    """07/10 Khủng Long Đỏ: "↻ Gửi lại clip lỗi" / "✖ Loại & gen lại" only QUEUED the clips and "▶ Gen video" stayed disabled with
    "0 cảnh sẵn sàng" — 7 paid-for clips waited with no button to send them."""

    def test_gen_video_is_enabled_and_sends_the_queued_clips(self):
        with mock.patch.dict(os.environ, {"VIDEO_PROVIDER": "mock"}):
            at = self.open_video()
            btn = next(b for b in at.button if b.key == f"gen_vid_{self.pid}")
            self.assertFalse(btn.disabled)
            self.assertIn("đang chờ gửi", btn.label)
            sent = []
            with mock.patch("core.runner.VideoRunner.submit_pending", lambda self_, pid: sent.append(pid) or 1):
                btn.click().run()
        self.assertEqual(sent, [self.pid])


class KldVideoScreenTests(VideoSeed):
    """KLD-1 / KLD-2 (08/10): the resend button holds only provider failures; an outdated-input failure has its own line; an older take
    with its own file can be chosen for the shot."""

    def seed_stale_failure(self):
        scene = self.p.create_scene(self.pid, 6, "CẢNH 6")
        jid = self.p.create_job(scene, "video_gen")
        self.p.start(jid)
        self.p.fail(jid, "stale_input: ảnh đã duyệt đã đổi")
        return jid

    def test_resend_button_skips_the_outdated_input_failure_and_offers_a_requeue(self):
        stale = self.seed_stale_failure()
        at = self.open_video()
        labels = {b.key: b.label for b in at.button}
        self.assertIn("(1)", labels["btn_bad_retry"])                     # only the seeded provider failure, not the stale one
        self.assertIn(f"stale_requeue_{self.pid}", labels)
        self.assertIn("đầu vào đã cũ", "\n".join(w.value for w in at.warning))
        self.assertNotIn(f"vr_{stale}", labels)                           # the card offers no plain resend either

    def test_an_older_take_with_its_own_file_can_be_chosen(self):
        from core import takes
        scene = self.p.conn.execute("SELECT scene_id FROM jobs WHERE id=?", (self.jobs["approved"],)).fetchone()["scene_id"]
        old = self.jobs["approved"]
        new = self.p.create_job(scene, "video_gen")
        self.p.start(new)
        dest = os.path.join(self.data, str(self.pid), "videos", "05.mp4")
        takes.make_room(self.p.conn, self.data, self.p.job(new), dest)    # the old take's file goes to the trash, still linked to it
        with open(dest, "wb") as f:
            f.write(b"new take")
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, new))
        self.p.conn.commit()
        self.p.succeed(new)
        at = self.open_video()
        btn = next(b for b in at.button if b.key == f"vuse_{old}")
        btn.click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(takes.chosen(Pipeline(connect(self.db)).conn, scene)["id"], old)


class VideoFlagOffTests(VideoSeed):
    def test_flag_off_still_draws_the_v2_cards(self):
        """S14.14 G-a (người dùng duyệt 05/10): the classic clip card (step4.video_card) was removed — the Video screen is v2 only,
        FEATURE_UI_V2=0 included; every key of the classic card lives on in video_card_v2."""
        at = self.open_video(v2=False)
        html = md(at)
        self.assertIn("v2-pill", html)
        keys = {b.key for b in at.button}
        j = self.jobs
        for k in (f"va_{j['pending_review']}", f"vr_rej_{j['pending_review']}", f"vr_{j['failed']}", f"vregen_{j['succeeded']}",
                  f"vfix_{j['pending_review']}"):
            self.assertIn(k, keys, k)


if __name__ == "__main__":
    unittest.main()
