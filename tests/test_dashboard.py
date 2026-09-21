import os
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class DashboardSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        os.environ["PIPELINE_DB"] = self.db
        os.environ["PIPELINE_DATA"] = os.path.join(self.tmp, "projects")
        os.environ["KNOWLEDGE_USER_DIR"] = os.path.join(self.tmp, "knowledge_user")

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        os.environ.pop("PIPELINE_DB", None)
        os.environ.pop("PIPELINE_DATA", None)

    def seed(self):
        p = Pipeline(connect(self.db))
        pid = p.create_project("Demo")
        p.create_scene(pid, 1, "CẢNH 1")
        store_scene_analysis(p, pid, ANALYSIS)
        return p, pid

    def test_empty_state_prompts_project_creation(self):
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Chưa có dự án" in i.value for i in at.info))

    def test_every_step_renders_without_error(self):
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        options = list(at.radio(key="step").options)
        self.assertEqual(len(options), 10)
        for option in options:
            at.radio(key="step").set_value(option).run()
            self.assertFalse(at.exception, option)

    def test_create_image_jobs_and_mode_switch(self):
        p, pid = self.seed()
        from core.llm_io import lock_character_bible
        lock_character_bible(p, pid)
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        next(b for b in at.button if "Tạo job gen ảnh" in b.label).click().run()
        self.assertFalse(at.exception)
        rows = Pipeline(connect(self.db)).conn.execute("SELECT type, state FROM jobs").fetchall()
        self.assertEqual([(r["type"], r["state"]) for r in rows], [("image_gen", "queued")])
        at.radio(key=f"mode_{pid}").set_value("auto").run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["operating_mode"], "auto")

    def test_pause_button_sets_flag(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        next(b for b in at.button if "Pause" in b.label).click().run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["paused"], 1)

    def test_music_step_with_mock_audio_creates_and_selects_draft(self):
        self.seed()
        os.environ["AUDIO_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
            self.assertFalse(at.exception)
            next(b for b in at.button if "bản nháp" in b.label).click().run()
            next(b for b in at.button if "Kiểm tra" in b.label).click().run()
            next(b for b in at.button if "Chọn bản này" in b.label).click().run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("AUDIO_PROVIDER", None)
        music_dir = os.path.join(self.tmp, "projects", "1", "music")
        self.assertEqual(os.listdir(music_dir), ["selected.wav"])

    def test_final_step_lists_generated_clips_and_shows_total(self):
        self.seed()
        videos = os.path.join(self.tmp, "projects", "1", "videos")
        os.makedirs(videos)
        open(os.path.join(videos, "01.mp4"), "wb").write(b"not a real video")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[5]).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("CẢNH 1" in c.label for c in at.checkbox))
        self.assertTrue(any("Tổng thời lượng dự kiến" in i.value for i in at.info))
        at.radio(key="tr_1").set_value("crossfade").run()
        self.assertTrue(any("crossfade cần ít nhất 2 clip" in w.value for w in at.warning))
        self.assertTrue(next(b for b in at.button if "Render Final" in b.label).disabled)

    def test_sfx_created_selected_and_counted_for_final_mix(self):
        self.seed()
        os.environ["AUDIO_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
            self.assertFalse(at.exception)
            at.text_input(key="sfx_p_1").set_value("door slam").run()
            next(b for b in at.button if "Tạo SFX" in b.label).click().run()
            next(b for b in at.button if "Kiểm tra" in b.label and b.key == "ax_refresh_1").click().run()
            at.checkbox(key="ax_use_1_0").set_value(True).run()
            self.assertFalse(at.exception)
            at.radio(key="step").set_value(at.radio(key="step").options[5]).run()
            self.assertTrue(any("đưa vào bản ghép: 1" in c.value for c in at.caption))
        finally:
            os.environ.pop("AUDIO_PROVIDER", None)

    def test_character_edit_and_unlock_from_dashboard(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.text_area(key=f"cd_{pid}_Lyra").set_value("Nữ, tóc đỏ").run()
        next(b for b in at.button if b.key == f"cs_{pid}_Lyra").click().run()
        self.assertFalse(at.exception)
        row = Pipeline(connect(self.db)).conn.execute("SELECT description FROM characters WHERE name='Lyra'").fetchone()
        self.assertEqual(row["description"], "Nữ, tóc đỏ")
        from core.llm_io import lock_character_bible
        lock_character_bible(Pipeline(connect(self.db)), pid)
        at = AppTest.from_file(APP, default_timeout=30).run()
        next(b for b in at.button if b.key == "btn_bad_unlock").click().run()
        self.assertEqual(Pipeline(connect(self.db)).conn.execute(
            "SELECT COUNT(*) c FROM characters WHERE locked=1").fetchone()["c"], 0)

    def test_llm_runner_buttons_with_mock_model(self):
        p = Pipeline(connect(self.db))
        pid = p.create_project("Demo")
        p.create_scene(pid, 1, "CẢNH 1")
        os.environ["LLM_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            next(b for b in at.button if b.key == f"llm_dir_{pid}").click().run()
            self.assertFalse(at.exception)
            self.assertFalse(at.error)
            row = Pipeline(connect(self.db)).conn.execute("SELECT name FROM characters").fetchone()
            self.assertEqual(row["name"], "Nhân vật chính")
            from core.llm_io import lock_character_bible
            lock_character_bible(Pipeline(connect(self.db)), pid)
            q = Pipeline(connect(self.db))
            scene = q.conn.execute("SELECT id FROM scenes").fetchone()["id"]
            job = q.create_job(scene)
            q.start(job)
            q.succeed(job)
            img = os.path.join(self.tmp, "projects", str(pid), "images")
            os.makedirs(img)
            with open(os.path.join(img, f"job_{job}.png"), "wb") as f:
                f.write(bytes([0x89]) + b"PNG" + b"0" * 20)
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
            next(b for b in at.button if b.key == f"llm_qc_all_{pid}").click().run()
            self.assertFalse(at.exception)
            state = Pipeline(connect(self.db)).conn.execute("SELECT state FROM jobs").fetchone()["state"]
            self.assertEqual(state, "pending_review")  # human_qc: mock scores wait for a person
        finally:
            os.environ.pop("LLM_PROVIDER", None)

    def test_price_editor_saves_table_to_the_pricing_file(self):
        import json
        self.seed()
        path = os.path.join(self.tmp, "pricing.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"currency": "credits", "confirm_batch_at": 10, "per_image": {"img": 3},
                       "per_video_second": {}, "per_video_clip": {}}, f)
        os.environ["PIPELINE_PRICING"] = path
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            self.assertFalse(at.exception)
            at.text_input(key="price_currency").set_value("token").run()
            next(b for b in at.button if b.key == "btn_save_prices").click().run()
            self.assertFalse(at.exception)
            self.assertFalse(at.error)
        finally:
            os.environ.pop("PIPELINE_PRICING", None)
        saved = json.load(open(path, encoding="utf-8"))
        self.assertEqual((saved["currency"], saved["per_image"]), ("token", {"img": 3.0}))
        self.assertIn("kling-v3-omni:pro:5s", saved["per_video_clip"])

    def test_scene_number_and_script_dropdown_under_image_video_and_history(self):
        import json
        from core.llm_io import approve_motion_prompt, lock_character_bible, store_motion_prompts
        p, pid = self.seed()
        lock_character_bible(p, pid)
        scene = p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        p.conn.execute("UPDATE scenes SET data=json_set(data, '$.text', ?) WHERE id=?",
                       ("CẢNH 1. ĐÊM - RỪNG ELDER" + chr(10) + "Lyra: Đi tiếp thôi.", scene))
        p.conn.commit()
        img = p.create_job(scene)
        p.start(img)
        p.succeed(img)
        p.approve(img)
        store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "push in slowly"}]})
        approve_motion_prompt(p, scene)
        vid = p.create_job(scene, "video_gen")
        p.start(vid)
        p.succeed(vid)
        videos = os.path.join(self.tmp, "projects", str(pid), "videos")
        os.makedirs(videos)
        with open(os.path.join(videos, "01.mp4"), "wb") as f:
            f.write(b"x")

        def labels(at):
            return [e.label for e in at.expander]

        at = AppTest.from_file(APP, default_timeout=30).run()
        for index in (1, 2, 3, 5, 6):
            at.radio(key="step").set_value(at.radio(key="step").options[index]).run()
            self.assertFalse(at.exception, index)
            self.assertTrue(any("Cảnh 1" in l and "nội dung kịch bản" in l for l in labels(at)), (index, labels(at)))
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        self.assertTrue(any("Cảnh 1" in m.value for m in at.markdown))
        # the detail panel shows the script text itself
        joined = " ".join(m.value for m in at.markdown)
        self.assertIn("Lyra: Đi tiếp thôi.", joined)
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        self.assertTrue(any("push in slowly" in m.value for m in at.markdown))

    def _pending_images(self, n=2):
        from core.llm_io import lock_character_bible
        p, pid = self.seed()
        lock_character_bible(p, pid)
        ids = []
        for idx in range(1, n + 1):
            if idx > 1:
                p.create_scene(pid, idx, f"CẢNH {idx}")
            scene = p.conn.execute("SELECT id FROM scenes WHERE idx=?", (idx,)).fetchone()["id"]
            job = p.create_job(scene)
            p.start(job)
            p.succeed(job)
            p.apply_qc(job, {"a": 0.9, "b": 0.9})  # human_qc: waits for a person
            ids.append(job)
        return p, pid, ids

    def test_approve_all_asks_yes_or_no_once(self):
        p, pid, ids = self._pending_images(2)

        def states():
            return [r["state"] for r in Pipeline(connect(self.db)).conn.execute("SELECT state FROM jobs ORDER BY id")]

        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        next(b for b in at.button if b.key == "approve_all").click().run()
        self.assertEqual(states(), ["pending_review", "pending_review"])  # nothing approved by the first click
        self.assertTrue(any("Duyệt tất cả 2 ảnh" in w.value for w in at.warning))
        next(b for b in at.button if b.key == "approve_all_no").click().run()
        self.assertEqual(states(), ["pending_review", "pending_review"])  # "No" changes nothing
        self.assertFalse(any("Duyệt tất cả 2 ảnh" in w.value for w in at.warning))
        next(b for b in at.button if b.key == "approve_all").click().run()
        next(b for b in at.button if b.key == "approve_all_yes").click().run()
        self.assertEqual(states(), ["approved", "approved"])

    def test_a_new_pending_image_cancels_a_question_already_asked(self):
        p, pid, ids = self._pending_images(1)
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        next(b for b in at.button if b.key == "approve_all").click().run()
        self.assertTrue(any("Duyệt tất cả 1 ảnh" in w.value for w in at.warning))
        q = Pipeline(connect(self.db))
        job = q.create_job(q.create_scene(pid, 2, "CẢNH 2"))
        q.start(job)
        q.succeed(job)
        q.apply_qc(job, {"a": 0.9, "b": 0.9})
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        self.assertFalse(any("Duyệt tất cả" in w.value for w in at.warning))  # the old question is gone
        self.assertTrue(any(b.key == "approve_all" for b in at.button))  # asks again from the button

    def test_low_score_image_lands_in_the_trash_tab_and_can_be_restored(self):
        p, pid, ids = self._pending_images(1)
        q = Pipeline(connect(self.db))
        job = ids[0]
        img_dir = os.path.join(self.tmp, "projects", str(pid), "images")
        os.makedirs(img_dir, exist_ok=True)
        with open(os.path.join(img_dir, f"job_{job}.png"), "wb") as f:
            f.write(b"x")
        q.conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (job,))
        q.conn.commit()
        self.assertEqual(q.apply_qc(job, {"a": 0.2, "b": 0.3}), "rejected")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[6]).run()
        self.assertFalse(at.exception)
        trashed = os.listdir(os.path.join(self.tmp, "projects", str(pid), "trash", "images"))
        self.assertTrue(any(name.startswith(f"job_{job}__") for name in trashed))
        self.assertFalse(os.path.exists(os.path.join(img_dir, f"job_{job}.png")))
        restore = next(b for b in at.button if (b.key or "").startswith("tr_images_"))
        restore.click().run()
        self.assertTrue(os.path.exists(os.path.join(img_dir, f"job_{job}.png")))

    def _finished_video(self):
        p, pid = self.seed()
        scene = p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        vid = p.create_job(scene, "video_gen")
        p.start(vid)
        p.succeed(vid)
        clip = os.path.join(self.tmp, "projects", str(pid), "videos", "01.mp4")
        os.makedirs(os.path.dirname(clip))
        with open(clip, "wb") as f:
            f.write(b"x")
        p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (clip, vid))
        p.conn.commit()
        return p, pid, vid, clip

    def test_regenerate_button_replaces_delete_for_a_finished_video(self):
        p, pid, vid, clip = self._finished_video()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        self.assertFalse(any((b.key or "").startswith("vdel_") for b in at.button))  # no delete button any more
        next(b for b in at.button if b.key == f"vregen_{vid}").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(os.path.exists(clip))
        self.assertEqual(len(os.listdir(os.path.join(self.tmp, "projects", str(pid), "trash", "videos"))), 2)  # file + manifest
        rows = Pipeline(connect(self.db)).conn.execute("SELECT state FROM jobs WHERE type='video_gen' ORDER BY id").fetchall()
        self.assertEqual([r["state"] for r in rows], ["rejected", "queued"])

    def test_video_plays_inline_without_a_size_switch_and_audio_option(self):
        p, pid, vid, clip = self._finished_video()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        self.assertFalse(at.exception)
        self.assertGreaterEqual(len(at.get("video")), 1)  # shown right in the list, no tick box needed
        self.assertFalse(any((r.key or "").startswith("vsize") for r in at.radio))  # no size switch any more
        at.checkbox(key=f"vaudio_{pid}").set_value(True).run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["video_audio"], 1)

    def test_every_scene_is_listed_and_editable_in_place(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertTrue(any(e.label.startswith("S01") for e in at.expander))  # the scene row itself, no picker
        self.assertFalse(any(sb.key == f"scene_pick_{pid}" for sb in at.selectbox))
        at.text_area(key=f"sd_{pid}_1_prompt").set_value("dark forest, low fog").run()
        at.text_area(key=f"sd_{pid}_1_text").set_value("CẢNH 1. Nội dung sửa").run()
        next(b for b in at.button if b.key == f"sds_{pid}_1").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        import json
        data = json.loads(Pipeline(connect(self.db)).conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual((data["image_prompt"], data["text"]), ("dark forest, low fog", "CẢNH 1. Nội dung sửa"))

    def test_subject_library_panel_defaults_to_free_fire_and_links_a_character(self):
        from core import subjects
        p, pid = self.seed()
        os.environ["SUBJECT_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            self.assertFalse(at.exception)
            self.assertEqual(at.selectbox(key=f"game_{pid}").value, "FF")
            self.assertTrue(any("Free Fire đã ký thỏa thuận" in s.value for s in at.success))
            at.selectbox(key=f"game_{pid}").set_value("AOV").run()
            self.assertEqual(Pipeline(connect(self.db)).project(pid)["game"], "AOV")
            self.assertTrue(any("chưa có thỏa thuận" in w.value for w in at.warning))
        finally:
            os.environ.pop("SUBJECT_PROVIDER", None)
        q = Pipeline(connect(self.db))
        subjects.link(q, pid, "Lyra", {"asset_id": "asset-mock-1", "asset_uri": "asset://asset-mock-1",
                                       "provider_status": "active", "name": "FF_Lyra"})
        os.environ["SUBJECT_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            self.assertTrue(any("1/2 nhân vật đã có" in e.label for e in at.expander))
        finally:
            os.environ.pop("SUBJECT_PROVIDER", None)

    def test_attach_subjects_switch_is_saved(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        at.checkbox(key=f"vsubj_{pid}").set_value(True).run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["use_subjects"], 1)

    def test_step1_shows_the_full_script_next_to_the_scene_list(self):
        p, pid = self.seed()
        p.set_script_text(pid, "TÊN KỊCH BẢN" + chr(10) + "CẢNH 1. ĐÊM" + chr(10) + "Lyra: Đi thôi.")
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        markup = " ".join(m.value for m in at.markdown)
        self.assertIn("scriptfull", markup)
        self.assertIn("TÊN KỊCH BẢN", markup)                       # whole script, including the part before scene 1
        self.assertIn("<b>CẢNH 1. ĐÊM</b>", markup)                 # scene headings stand out
        self.assertTrue(any(e.label.startswith("S01") for e in at.expander))  # ...and the scene rows sit beside it

    def test_add_and_delete_a_scene_from_the_scene_list(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        next(b for b in at.button if b.key == f"scene_add_{pid}").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(Pipeline(connect(self.db)).conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 2)
        next(b for b in at.button if b.key == f"scene_del_{pid}_2").click().run()
        self.assertEqual(Pipeline(connect(self.db)).conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 2)  # asked first
        next(b for b in at.button if b.key == f"scene_del_{pid}_2_yes").click().run()
        self.assertEqual(Pipeline(connect(self.db)).conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 1)

    def test_bible_accepts_a_non_human_entry_from_the_dashboard(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.text_input(key=f"cadd_name_{pid}").set_value("Rồng lửa").run()
        at.text_area(key=f"cadd_desc_{pid}").set_value("Rồng đỏ cao 5m").run()
        next(b for b in at.button if b.key == f"cadd_{pid}").click().run()
        self.assertFalse(at.exception)
        names = [r["name"] for r in Pipeline(connect(self.db)).conn.execute("SELECT name FROM characters")]
        self.assertIn("Rồng lửa", names)

    def test_escalated_image_offers_a_restart_and_an_approved_one_can_be_reopened(self):
        from core.llm_io import lock_character_bible
        p, pid = self.seed()
        lock_character_bible(p, pid)
        p.conn.execute("UPDATE projects SET max_retry_count=0 WHERE id=?", (pid,))
        p.conn.commit()
        scene = p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        job = p.create_job(scene)
        p.start(job)
        p.succeed(job)
        self.assertEqual(p.reject(job, "user", "sai"), "escalated")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        self.assertFalse(at.exception)
        next(b for b in at.button if b.key == f"rs_{job}").click().run()
        rows = Pipeline(connect(self.db)).conn.execute("SELECT state FROM jobs ORDER BY id").fetchall()
        self.assertEqual([r["state"] for r in rows], ["rejected", "queued"])
        # an approved image: reopen it from the detail panel
        q = Pipeline(connect(self.db))
        new = q.conn.execute("SELECT id FROM jobs WHERE state='queued'").fetchone()["id"]
        q.start(new)
        q.succeed(new)
        q.approve(new, "user")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        next(b for b in at.button if b.key == f"sel_btn_{new}").click().run()  # open its detail panel
        at.text_input(key=f"rn_{new}").set_value("đổi màu áo").run()
        next(b for b in at.button if b.key == f"reopen_{new}").click().run()
        self.assertFalse(at.exception)
        states = [r["state"] for r in Pipeline(connect(self.db)).conn.execute("SELECT state FROM jobs ORDER BY id")]
        self.assertEqual(states, ["rejected", "rejected", "queued"])

    def test_knowledge_settings_tab_shows_overview_and_manages_uploaded_documents(self):
        from core import knowledge
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertEqual([m.label for m in at.metric][:3], ["Tài liệu đang bật", "Ký tự gửi Claude mỗi lần chạy", "≈ token mỗi lần chạy"])
        labels = [e.label for e in at.expander]
        self.assertTrue(any("Cơ bản điện ảnh" in l for l in labels))          # built-in documents are listed
        self.assertEqual(at.selectbox(key="kb_group").value, "director")
        at.selectbox(key="kb_group").set_value("qc").run()
        self.assertTrue(any("Lỗi thường gặp của ảnh AI" in e.label for e in at.expander))
        entry = knowledge.add_doc("qc", "phong cach.md", "Chấm gắt hơn.".encode("utf-8"))
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.selectbox(key="kb_group").set_value("qc").run()
        self.assertTrue(any("phong cach" in e.label and "bạn thêm" in e.label for e in at.expander))
        at.checkbox(key=f"kb_en_qc_{entry['file']}").set_value(False).run()
        self.assertEqual(knowledge.user_text("qc"), "")                        # switched off in the UI
        next(b for b in at.button if b.key == f"kb_del_qc_{entry['file']}").click().run()
        next(b for b in at.button if b.key == f"kb_del_qc_{entry['file']}_yes").click().run()
        self.assertEqual([d for d in knowledge.overview("qc")["docs"] if d["source"] == "user"], [])

    def test_distilling_the_knowledge_into_a_short_playbook_from_the_settings(self):
        from core import knowledge
        self.seed()
        knowledge.add_doc("director", "studio.md", ("Tông lạnh, sương mù. " * 300).encode("utf-8"), title="studio")
        os.environ["LLM_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            self.assertFalse(at.exception)
            self.assertTrue(any("Chưa có cẩm nang" in i.value for i in at.info))
            at.checkbox(key="kb_inc_director").set_value(True).run()      # fold the built-in knowledge in too
            next(b for b in at.button if b.key == "kb_distill_director").click().run()
            self.assertFalse(at.exception)
            self.assertFalse(at.error)
            status = knowledge.distilled_status("director")
            self.assertTrue(status["active"] and status["include_builtin"])
            self.assertTrue(any("Đang dùng cẩm nang" in s.value for s in at.success))
            ov = knowledge.overview("director")
            self.assertLess(ov["chars"], ov["raw_chars"])                  # every run now sends less
            knowledge.add_doc("director", "moi.md", "Quy tắc mới.".encode("utf-8"))
            at = AppTest.from_file(APP, default_timeout=30).run()
            self.assertTrue(any("cẩm nang đã cũ" in w.value for w in at.warning))  # asks to distil again
        finally:
            os.environ.pop("LLM_PROVIDER", None)

    def test_autopilot_panel_lists_what_is_missing_before_it_can_start(self):
        self.seed()
        for k in ("IMAGE_PROVIDER", "VIDEO_PROVIDER", "LLM_PROVIDER", "ANTHROPIC_API_KEY"):
            os.environ.pop(k, None)
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("tự động hoàn toàn" in m.value for m in at.markdown))
        self.assertTrue(any("✖" in m.value for m in at.markdown))     # reasons shown, no start possible

    def test_performance_monitor_tab_shows_load_and_health(self):
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30)
        at.query_params["step"] = "monitor"
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Theo dõi hiệu suất" in m.value for m in at.markdown))
        self.assertTrue(any(m.label == "Job hôm nay" for m in at.metric))
        self.assertTrue(any("Gen video" in str(d.value) for d in at.dataframe))
        self.assertTrue(any("Giám sát từng khâu" in m.value for m in at.markdown))
        self.assertTrue(any("Báo cáo chẩn đoán" in c.value for c in at.code))     # the paste-into-chat report

    def test_lessons_tab_lists_proposals_and_approving_feeds_the_knowledge_base(self):
        import tempfile
        from core import knowledge, lessons
        os.environ["KNOWLEDGE_USER_DIR"] = tempfile.mkdtemp()
        try:
            p, pid = self.seed()
            conn = connect(self.db)
            lessons.add_research(conn, "director", "Mẹo thử nghiệm", "Luôn nêu rõ cỡ cảnh.", "https://example.com/x")
            at = AppTest.from_file(APP, default_timeout=30)
            at.query_params["step"] = "lessons"
            at.run()
            self.assertFalse(at.exception)
            self.assertTrue(any("Đề xuất chờ duyệt (1)" in m.value for m in at.markdown))
            next(b for b in at.button if b.label == "👍 Duyệt").click().run()
            self.assertFalse(at.exception)
            self.assertEqual([d["title"] for d in knowledge.user_docs("director")], [lessons.DOC_TITLE])
        finally:
            os.environ.pop("KNOWLEDGE_USER_DIR", None)

    def test_risk_corner_lists_ip_and_moderation_notes(self):
        p, pid = self.seed()
        scene = p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        job = p.create_job(scene, "video_gen")
        from core.preflight import record_failure
        record_failure(p.conn, job, "clipai", "Failure to pass the risk control system")
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get("popover")), 1)
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("Cảnh 1 bị chặn (clipai)", text)      # risk-control block, with its scene
        self.assertIn("Nữ chiến binh Amazon", text)          # IP warning from the Character Bible

    def test_music_can_be_previewed_over_the_clips(self):
        from unittest import mock
        self.seed()
        videos = os.path.join(self.tmp, "projects", "1", "videos")
        os.makedirs(videos)
        with open(os.path.join(videos, "01.mp4"), "wb") as f:
            f.write(b"x")
        os.environ["AUDIO_PROVIDER"] = "mock"
        made = []

        def fake_preview(pipeline, data_dir, pid, music_path, out_path, volume=0.6, keep_audio=False):
            with open(out_path, "wb") as f:
                f.write(b"x")
            made.append(music_path)
            return out_path

        try:
            with mock.patch("core.final_cut.preview_with_music", side_effect=fake_preview):
                at = AppTest.from_file(APP, default_timeout=30).run()
                at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
                next(b for b in at.button if "bản nháp" in b.label).click().run()
                next(b for b in at.button if "Kiểm tra" in b.label).click().run()
                next(b for b in at.button if b.key == "prevd_1_0").click().run()
                self.assertFalse(at.exception)
        finally:
            os.environ.pop("AUDIO_PROVIDER", None)
        self.assertEqual(len(made), 1)
        self.assertTrue(made[0].endswith(".wav"))

    def test_reject_floor_slider_is_saved_for_the_project(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
        at.slider(key=f"rej_v_{pid}").set_value(0.7).run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["qc_reject_floor"], 0.7)
        at.checkbox(key=f"rej_on_{pid}").set_value(False).run()
        self.assertIsNone(Pipeline(connect(self.db)).project(pid)["qc_reject_floor"])

    def test_video_step_with_mock_provider_runs_to_completion(self):
        from core.llm_io import approve_motion_prompt, lock_character_bible, store_motion_prompts
        p, pid = self.seed()
        lock_character_bible(p, pid)
        scene = p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        img = p.create_job(scene)
        p.start(img)
        p.succeed(img)
        p.approve(img)
        store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        approve_motion_prompt(p, scene)
        os.environ["VIDEO_PROVIDER"] = "mock"
        os.environ["HEARTBEAT_SEC"] = "0"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
            next(b for b in at.button if "Tạo job gen video" in b.label).click().run()
            next(b for b in at.button if "heartbeat" in b.label).click().run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("VIDEO_PROVIDER", None)
            os.environ.pop("HEARTBEAT_SEC", None)
        row = Pipeline(connect(self.db)).conn.execute(
            "SELECT state, result_path FROM jobs WHERE type='video_gen'").fetchone()
        self.assertEqual(row["state"], "succeeded")
        self.assertTrue(os.path.exists(row["result_path"]))

    def test_image_step_with_mock_provider_generates_files(self):
        from core.llm_io import lock_character_bible
        p, pid = self.seed()
        lock_character_bible(p, pid)
        os.environ["IMAGE_PROVIDER"] = "mock"
        os.environ["HEARTBEAT_SEC"] = "0"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[1]).run()
            next(b for b in at.button if "Tạo job gen ảnh" in b.label).click().run()
            next(b for b in at.button if "heartbeat" in b.label).click().run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("IMAGE_PROVIDER", None)
            os.environ.pop("HEARTBEAT_SEC", None)
        row = Pipeline(connect(self.db)).conn.execute(
            "SELECT state, result_path FROM jobs WHERE type='image_gen'").fetchone()
        self.assertEqual(row["state"], "succeeded")
        self.assertTrue(os.path.exists(row["result_path"]))


if __name__ == "__main__":
    unittest.main()
