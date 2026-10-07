import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core.db import connect
from core.llm_io import store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")


class DashboardSmokeTests(unittest.TestCase):
    def setUp(self):
        os.environ["DASHBOARD_EXPERT"] = "1"      # these tests use the advanced panels (kế hoạch V4 5.3)
        self.addCleanup(os.environ.pop, "DASHBOARD_EXPERT", None)
        # S14.14 G-a: ui_v2 is ON by default now. These smoke tests were written for the classic screens; the heavy screens (Storyboard,
        # Bản giao, header — G-b) still have them behind FEATURE_UI_V2=0, the light ones (Kịch bản, Video, Theo dõi) are v2 only and their
        # tests below open the v2 folds instead. G-b removes this line with the classic heavy screens.
        flag = mock.patch.dict(os.environ, {"FEATURE_UI_V2": "0"})
        flag.start()
        self.addCleanup(flag.stop)
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

    @staticmethod
    def open_all(at):
        """S14.14 G-a: the v2 Kịch bản screen draws only the panel of the next job open (step1_v2.next_panel) — open every closed
        ui.fold (Director, Character Bible, 🔧 Tinh chỉnh…) like a person clicking ▸ Mở, as tools/ui_v2_acceptance.py does."""
        for _ in range(12):
            closed = [b for b in at.button if (b.key or "").startswith("fold_") and (b.key or "").endswith("_btn") and b.label.startswith("▸")]
            if not closed:
                break
            closed[0].click().run()
        return at

    @staticmethod
    def notes(at) -> str:
        """Text of the page's markdown (v2 step1 notes: step1_v2.say → pill + summary line + the whole message in the ⓘ popover)."""
        return " ".join(m.value or "" for m in at.markdown)

    @staticmethod
    def with_lock(p, pid):
        """A Bible the automatic run would accept (every character has a Character Lock): since 2026-09-26 the manual Gen ảnh button
        stops at the same gates (core.batch.image_gates)."""
        p.conn.execute("UPDATE characters SET lock_rules='{\"must_keep\": \"face\"}' WHERE project_id=?", (pid,))
        p.conn.commit()

    def test_empty_state_prompts_project_creation(self):
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Chưa có dự án" in i.value for i in at.info))

    def test_new_project_button_creates_it_and_switches_the_picker_to_it(self):
        """The "+" button next to the user's name (2026-09-22 header redesign) works even with zero projects,
        and the header picker switches straight to the project it just made."""
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.text_input(key="new_name").set_value("Fresh One").run()
        next(b for b in at.button if b.key == "new_project_go").click().run()
        self.assertFalse(at.exception)
        pid = Pipeline(connect(self.db)).conn.execute("SELECT id FROM projects WHERE name='Fresh One'").fetchone()["id"]
        self.assertEqual(at.selectbox(key="global_pid").value, pid)

    def test_settings_gear_opens_one_dialog_at_a_time(self):
        """Kho tài nguyên / Bảng giá / Kho kiến thức / Lịch sử / Bài học / Phân quyền each open as their own
        st.dialog panel; opening one must close whichever was open before (st.dialog only allows one at once)."""
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.button(key="mc_pricing").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any(t.key == "price_currency" for t in at.text_input))
        at.button(key="settings_history").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(any(t.key == "price_currency" for t in at.text_input))          # Bảng giá closed
        self.assertTrue(any(s.label == "Cảnh" for s in at.selectbox))                    # Lịch sử's scene picker

    def test_expert_switch_hides_the_advanced_panels_by_default(self):
        """Kế hoạch V4 5.3: off by default, the steps show a normal run only; the ⚙ switch brings the advanced panels back."""
        os.environ.pop("DASHBOARD_EXPERT", None)
        self.seed()
        at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
        self.assertFalse(at.exception)
        labels = lambda: [e.label for e in at.expander]  # noqa: E731
        self.assertFalse(any("Nâng cao: prompt gửi Claude" in x for x in labels()))
        self.assertFalse(any("World Bible" in x for x in labels()))
        at.toggle(key="expert_mode").set_value(True).run()
        self.open_all(at)                                  # v2: World Bible sits in card ②'s "🔧 Tinh chỉnh" fold (expert only)
        self.assertFalse(at.exception)
        self.assertTrue(any("World Bible" in x for x in labels()))

    def test_the_overview_cards_are_gone_but_their_facts_stay_on_the_status_line(self):
        """01/10: the four cards duplicated the bar's progress and the ⌂ page; the queue / background facts moved to the status line."""
        _, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertFalse([b for b in at.button if (b.key or "").startswith("ov_")])
        self.assertFalse(any("Tổng quan dự án" in e.label for e in at.expander))

    def test_the_limits_dialog_opens_with_its_numbers(self):
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.button(key="settings_limits").click().run()
        self.assertFalse(at.exception)
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("Cấu hình", text)
        self.assertIn("Hàng đợi bây giờ", text)
        self.assertTrue(any("chưa đủ dữ liệu" in i.value for i in at.info))      # an empty history gives no guess

    def test_the_library_shows_the_review_box_and_the_3d_panel(self):
        from core import assets
        self.seed()
        models = os.path.join(self.tmp, "model 3D")
        os.makedirs(models)
        open(os.path.join(models, "thap.glb"), "wb").write(b"glTF")
        os.environ.update({"MODEL3D_DIR": models, "ASSET_DIR": os.path.join(self.tmp, "assets")})
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("MODEL3D_DIR", "ASSET_DIR")])
        conn = connect(self.db)
        aid = assets.create(conn, "FF", "character", "KELLY")
        from tests.test_new_skills import PNG
        assets.add_image(conn, aid, "k.png", PNG, status="pending")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.button(key="settings_assets").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Ảnh chờ duyệt" in e.label for e in at.expander))
        self.assertTrue(any("1 ảnh chờ duyệt" in c.value for c in at.caption))
        self.assertTrue(any("Bối cảnh 3D" in e.label for e in at.expander))
        at.toggle(key="p3d_open").set_value(True).run()
        self.assertTrue(any(s.key == "p3d_file" for s in at.selectbox))

    def test_review_box_bulk_remove_redraws_only_the_box(self):
        from core import assets
        from tests.test_new_skills import PNG
        self.seed()
        os.environ["ASSET_DIR"] = os.path.join(self.tmp, "assets")
        self.addCleanup(lambda: os.environ.pop("ASSET_DIR", None))
        conn = connect(self.db)
        aid = assets.create(conn, "FF", "character", "KELLY")
        for n in range(3):
            assets.add_image(conn, aid, f"k{n}.png", PNG + bytes([n]), status="pending")
        ids = [w["id"] for w in assets.pending_images(conn, "FF")]
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.button(key="settings_assets").click().run()
        for i in ids[:2]:
            at.checkbox(key=f"lib_rev_pick_{i}").check()
        at.run()
        at.button(key="lib_rev_rmpick_FF").click().run()
        at.button(key="lib_rev_rmyes_FF").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([w["id"] for w in assets.pending_images(connect(self.db), "FF")], ids[2:])

    def test_every_step_renders_without_error(self):
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        options = list(at.radio(key="step").options)
        self.assertEqual(len(options), 7)                      # ⌂ Tất cả dự án + 4 màn + 👥 Nhóm + Theo dõi hiệu suất
        for option in options:
            at.radio(key="step").set_value(option).run()
            self.assertFalse(at.exception, option)
        # Kho tài nguyên / Bảng giá / Kho kiến thức / Lịch sử / Bài học / Phân quyền: moved to the settings
        # gear, each its own dialog -- must render without error too.
        for key in ("settings_assets", "mc_pricing", "settings_knowledge", "settings_history",
                   "settings_lessons", "settings_users", "settings_limits"):
            at.button(key=key).click().run()
            self.assertFalse(at.exception, key)

    def test_create_image_jobs_and_mode_switch(self):
        p, pid = self.seed()
        from core.llm_io import lock_character_bible
        self.with_lock(p, pid)
        lock_character_bible(p, pid)
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
        next(b for b in at.button if "Gen ảnh các cảnh" in b.label).click().run()
        self.assertFalse(at.exception)
        rows = Pipeline(connect(self.db)).conn.execute("SELECT type, state FROM jobs").fetchall()
        self.assertEqual([(r["type"], r["state"]) for r in rows], [("image_gen", "queued")])
        at.radio(key=f"mode_{pid}").set_value("auto").run()
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["operating_mode"], "auto")

    def test_pause_button_sets_flag(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        next(b for b in at.button if "Tạm dừng" in b.label).click().run()
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
        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state["fold_clips_1"] = True                 # S9 E5.1 / E5.6: the clip list and the render settings fold
        at.session_state["fold_render_set_1"] = True
        at.run()
        at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("CẢNH 1" in c.label for c in at.checkbox))
        self.assertTrue(any("Tổng thời lượng dự kiến" in i.value for i in at.info))
        at.radio(key="tr_1").set_value("crossfade").run()
        self.assertTrue(any("crossfade cần ít nhất 2 clip" in w.value for w in at.warning))
        self.assertTrue(next(b for b in at.button if "Dựng video cuối" in b.label).disabled)

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
            at.checkbox(key="ax_use_1_0_0_0.0_1.0").set_value(True).run()   # key carries the stored values (see step5 mixer)
            self.assertFalse(at.exception)
            at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
            self.assertTrue(any("trong bản trộn: 1" in c.value for c in at.caption))
        finally:
            os.environ.pop("AUDIO_PROVIDER", None)

    def test_tts_overlap_warning_and_reschedule_button(self):
        """Two voice-over lines whose real audio overlaps must show a warning with a fix button; clicking it
        must not crash even when there is no clip/subtitle data yet to match cues against (PLAN.md 3.7b #5)."""
        from core import audio_lib
        from core.music import MockAudioProvider
        p, pid = self.seed()
        directory = audio_lib.assets_dir(os.path.join(self.tmp, "projects"), pid)
        provider = MockAudioProvider()
        audio_lib.submit_tts(provider, directory, "A", 1, "V")
        audio_lib.submit_tts(provider, directory, "B", 1, "V")
        audio_lib.refresh(provider, directory)
        audio_lib.set_mix(directory, 0, True, 0.0, 1.0)
        audio_lib.set_mix(directory, 1, True, 0.5, 1.0)      # mock TTS duration is 1.5s -> overlaps
        os.environ["AUDIO_PROVIDER"] = "mock"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[4]).run()
            self.assertFalse(at.exception)
            self.assertTrue(any("đè lên nhau" in w.value for w in at.warning))
            next(b for b in at.button if "Xếp lại theo thoại" in b.label).click().run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("AUDIO_PROVIDER", None)

    def test_character_edit_and_unlock_from_dashboard(self):
        p, pid = self.seed()
        at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
        at.text_area(key=f"cd_{pid}_Lyra").set_value("Nữ, tóc đỏ").run()
        next(b for b in at.button if b.key == f"cs_{pid}_Lyra").click().run()
        self.assertFalse(at.exception)
        row = Pipeline(connect(self.db)).conn.execute("SELECT description FROM characters WHERE name='Lyra'").fetchone()
        self.assertEqual(row["description"], "Nữ, tóc đỏ")
        from core.llm_io import lock_character_bible
        lock_character_bible(Pipeline(connect(self.db)), pid)
        at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
        next(b for b in at.button if b.key == "btn_bad_unlock").click().run()
        self.assertEqual(Pipeline(connect(self.db)).conn.execute(
            "SELECT COUNT(*) c FROM characters WHERE locked=1").fetchone()["c"], 0)

    def test_llm_runner_buttons_with_mock_model(self):
        p = Pipeline(connect(self.db))
        pid = p.create_project("Demo")
        p.create_scene(pid, 1, "CẢNH 1")
        os.environ["LLM_PROVIDER"] = "mock"
        try:
            at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
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
            from core import llm_runner as lr
            self.assertEqual(lr.run_qc(q, job, lr.MockLlm(), os.path.join(self.tmp, "projects"))["decision"], "pending_review")
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
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
            at.button(key="mc_pricing").click().run()
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

        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state[f"fold_motion_{pid}"] = True           # S9 E3.1 / E5.1: folded once everything there is approved
        at.session_state[f"fold_clips_{pid}"] = True
        at.run()
        for index in (2, 3, 4):                                # Storyboard (Ảnh + Motion tabs), Video, Bản giao; Lịch sử (below) is its own panel now
            at.radio(key="step").set_value(at.radio(key="step").options[index]).run()
            self.assertFalse(at.exception, index)
            self.assertTrue(any("Cảnh 1" in l and "nội dung kịch bản" in l for l in labels(at)), (index, labels(at)))
        at.button(key="settings_history").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Cảnh 1" in l and "nội dung kịch bản" in l for l in labels(at)), labels(at))
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
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
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
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
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
        next(b for b in at.button if b.key == "approve_all").click().run()
        self.assertTrue(any("Duyệt tất cả 1 ảnh" in w.value for w in at.warning))
        q = Pipeline(connect(self.db))
        job = q.create_job(q.create_scene(pid, 2, "CẢNH 2"))
        q.start(job)
        q.succeed(job)
        q.apply_qc(job, {"a": 0.9, "b": 0.9})
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
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
        self.assertEqual(q.apply_qc(job, {"a": 0.2, "b": 0.3}, issues="Fix the face."), "rejected")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.button(key="settings_history").click().run()                     # Lịch sử now opens as its own panel
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
        at = self.script_open(pid)
        self.assertTrue(any(e.label.startswith("S01") for e in at.expander))  # the scene row itself, no picker
        self.assertFalse(any(sb.key == f"scene_pick_{pid}" for sb in at.selectbox))
        at.toggle(key=f"sd_open_{pid}_1").set_value(True).run()
        at.text_area(key=f"sd_{pid}_1_prompt").set_value("dark forest, low fog").run()
        at.text_area(key=f"sd_{pid}_1_text").set_value("CẢNH 1. Nội dung sửa").run()
        next(b for b in at.button if b.key == f"sds_{pid}_1").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        import json
        data = json.loads(Pipeline(connect(self.db)).conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual((data["image_prompt"], data["text"]), ("dark forest, low fog", "CẢNH 1. Nội dung sửa"))

    def test_saving_a_shot_keeps_its_half_second_duration(self):
        import json
        p, pid = self.seed()
        row = p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()
        p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=1",
                       (json.dumps(dict(json.loads(row["data"] or "{}"), duration_s=2.5)), pid))
        p.conn.commit()
        at = self.script_open(pid)
        at.toggle(key=f"sd_open_{pid}_1").set_value(True).run()
        self.assertEqual(at.number_input(key=f"sd_{pid}_1_dur").value, 2.5)
        at.text_area(key=f"sd_{pid}_1_prompt").set_value("dark forest, low fog").run()
        next(b for b in at.button if b.key == f"sds_{pid}_1").click().run()
        self.assertFalse(at.exception)
        data = json.loads(Pipeline(connect(self.db)).conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual(data["duration_s"], 2.5)                                    # was cut to 2 by an int box
        self.assertNotIn("duration_s", data.get("_user_locked") or [])                # not changed by hand → not locked

    def test_a_shot_size_angle_and_move_are_set_by_hand(self):
        """07/10 (Khủng Long Đỏ): a "same frame as the previous shot" shot needs the previous shot's size — there was no box for it."""
        import json
        p, pid = self.seed()
        row = p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()
        p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=1",
                       (json.dumps(dict(json.loads(row["data"] or "{}"), shot_no=1, size="MS", angle="eye")), pid))
        p.conn.commit()
        at = self.script_open(pid)
        at.toggle(key=f"sd_open_{pid}_1").set_value(True).run()
        self.assertEqual(at.selectbox(key=f"sd_{pid}_1_size").value, "MS")
        at.selectbox(key=f"sd_{pid}_1_size").set_value("MCU").run()
        at.selectbox(key=f"sd_{pid}_1_move").set_value("static").run()
        at.selectbox(key=f"sd_{pid}_1_route").set_value("kling").run()
        next(b for b in at.button if b.key == f"sds_{pid}_1").click().run()
        self.assertFalse(at.exception)
        data = json.loads(Pipeline(connect(self.db)).conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual((data["size"], data["angle"], data["move"], data["video_route"]), ("MCU", "eye", "static", "kling"))
        self.assertIn("size", data["_user_locked"])                                   # kept when the Director runs again
        from core import llm_io
        with self.assertRaises(llm_io.SchemaError):
            llm_io.update_scene(Pipeline(connect(self.db)), pid, 1, {"size": "HUGE"})

    def test_a_flash_and_a_shake_into_the_shot_are_set_by_hand(self):
        """07/10 (Khủng Long Đỏ, "hô biến"): the cut into a shot (chớp trắng) and a frame shake had no box — only the Director/an impact
        sound could set them."""
        import json
        p, pid = self.seed()
        row = p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()
        p.conn.execute("UPDATE scenes SET data=? WHERE project_id=? AND idx=1",
                       (json.dumps(dict(json.loads(row["data"] or "{}"), shot_no=1)), pid))
        p.conn.commit()
        at = self.script_open(pid)
        at.toggle(key=f"sd_open_{pid}_1").set_value(True).run()
        self.assertEqual(at.selectbox(key=f"sd_{pid}_1_trans").value, "cut")
        at.selectbox(key=f"sd_{pid}_1_trans").set_value("flash").run()
        at.checkbox(key=f"sd_{pid}_1_shake").check().run()
        next(b for b in at.button if b.key == f"sds_{pid}_1").click().run()
        self.assertFalse(at.exception)
        data = json.loads(Pipeline(connect(self.db)).conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual((data["transition_in"], data["shake_in"]), ("flash", True))
        from core import llm_io
        with self.assertRaises(llm_io.SchemaError):
            llm_io.update_scene(Pipeline(connect(self.db)), pid, 1, {"transition_in": "spin"})

    def test_a_scene_background_is_chosen_from_the_project_places_and_saved_by_id(self):
        import io
        import json
        from PIL import Image
        from core import assets
        os.environ["ASSET_DIR"] = os.path.join(self.tmp, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        p, pid = self.seed()
        buf = io.BytesIO()
        Image.new("RGB", (64, 36), (10, 90, 40)).save(buf, "PNG")
        loc = assets.create(p.conn, "FF", "location", "Đảo Quân Sự", "", "", None, "x")
        assets.add_image(p.conn, loc, "wide.png", buf.getvalue())
        assets.attach(p.conn, pid, loc)
        at = self.script_open(pid)
        at.toggle(key=f"sd_open_{pid}_1").set_value(True).run()
        box = at.selectbox(key=f"sd_{pid}_1_bg")
        self.assertIsNone(box.value)                                                  # automatic by default
        box.set_value(loc).run()
        next(b for b in at.button if b.key == f"sds_{pid}_1").click().run()
        self.assertFalse(at.exception)
        data = json.loads(Pipeline(connect(self.db)).conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual(data["location_asset"], loc)

    def test_the_storyboard_is_built_from_step_1_and_shown_without_any_approval(self):
        import io
        from PIL import Image
        from core import assets, llm_io
        os.environ["ASSET_DIR"] = os.path.join(self.tmp, "assets")
        os.environ["LLM_PROVIDER"] = "mock"
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.addCleanup(os.environ.pop, "LLM_PROVIDER", None)
        p, pid = self.seed()
        buf = io.BytesIO()
        Image.new("RGB", (640, 360), (120, 150, 110)).save(buf, "PNG")
        loc = assets.create(p.conn, "FF", "location", "Đảo Quân Sự", "", "", None, "x")
        assets.add_image(p.conn, loc, "wide.png", buf.getvalue())
        assets.attach(p.conn, pid, loc)
        llm_io.update_scene(p, pid, 1, {"location_asset": loc})
        at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
        at.button(key=f"pv_plan_{pid}").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "projects", str(pid), "layouts", "storyboard.png")))
        at.button(key=f"pv_review_{pid}").click().run()
        self.assertFalse(at.exception)
        self.assertIn("không thấy lỗi", self.notes(at))                 # v2: say("success") = pill + one line + the text in ⓘ

    def test_an_outfit_is_picked_in_the_character_bible_and_a_character_set_made_from_it(self):
        import io
        from PIL import Image
        from core import assets
        os.environ["ASSET_DIR"] = os.path.join(self.tmp, "assets")
        os.environ["IMAGE_PROVIDER"] = "mock"
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        self.addCleanup(os.environ.pop, "IMAGE_PROVIDER", None)
        p, pid = self.seed()
        name = p.conn.execute("SELECT name FROM characters WHERE project_id=? ORDER BY id", (pid,)).fetchone()["name"]
        buf = io.BytesIO()
        Image.new("RGB", (60, 90), (200, 30, 30)).save(buf, "PNG")
        skin = assets.create(p.conn, "FF", "prop", "Áo giáp đỏ", "", "", None, "x")
        assets.add_image(p.conn, skin, "skin.png", buf.getvalue())
        assets.attach(p.conn, pid, skin)
        img_id = assets.get(p.conn, skin)["images"][0]["id"]
        at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
        at.multiselect(key=f"outfit_{pid}_{name}").set_value([img_id]).run()
        at.button(key=f"outfit_save_{pid}_{name}").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([i["id"] for i in assets.outfit_images(p.conn, pid, name)], [img_id])
        at.button(key=f"outfit_set_{pid}_{name}").click().run()
        self.assertFalse(at.exception)
        linked = assets.link_characters(Pipeline(connect(self.db)).conn, pid, [name])[name]
        self.assertTrue(linked["name"].endswith("· trang phục 1"))

    def test_blocking_and_sequence_are_edited_in_the_scene_and_shown_in_its_row(self):
        import json
        p, pid = self.seed()
        at = self.script_open(pid)
        at.toggle(key=f"sd_open_{pid}_1").set_value(True).run()
        at.text_input(key=f"sd_{pid}_1_blocking").set_value("Kelly frame-left facing right").run()
        at.number_input(key=f"sd_{pid}_1_seq").set_value(2).run()
        next(b for b in at.button if b.key == f"sds_{pid}_1").click().run()
        self.assertFalse(at.exception)
        data = json.loads(Pipeline(connect(self.db)).conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual((data["blocking"], data["sequence"]), ("Kelly frame-left facing right", 2))
        at = self.script_open(pid)
        self.assertTrue(any(e.label.startswith("S01 · nhóm 2") for e in at.expander))

    def test_subject_library_panel_defaults_to_free_fire_and_links_a_character(self):
        from core import subjects
        p, pid = self.seed()
        os.environ["SUBJECT_PROVIDER"] = "mock"
        os.environ["SHOW_SUBJECT_LIBRARY"] = "1"                 # hidden by default since the 2026-09-22 decision
        self.addCleanup(os.environ.pop, "SHOW_SUBJECT_LIBRARY", None)
        try:
            at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
            self.assertFalse(at.exception)
            self.assertEqual(at.selectbox(key=f"game_{pid}").value, "FF")
            self.assertIn("Free Fire đã ký thỏa thuận", self.notes(at))     # v2: say() notes, not st.success boxes
            at.selectbox(key=f"game_{pid}").set_value("AOV").run()
            self.assertEqual(Pipeline(connect(self.db)).project(pid)["game"], "AOV")
            self.assertIn("chưa có thỏa thuận", self.notes(at))
        finally:
            os.environ.pop("SUBJECT_PROVIDER", None)
        q = Pipeline(connect(self.db))
        subjects.link(q, pid, "Lyra", {"asset_id": "asset-mock-1", "asset_uri": "asset://asset-mock-1",
                                       "provider_status": "active", "name": "FF_Lyra"})
        os.environ["SUBJECT_PROVIDER"] = "mock"
        try:
            at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
            self.assertTrue(any("1/2 nhân vật đã có" in e.label for e in at.expander))
        finally:
            os.environ.pop("SUBJECT_PROVIDER", None)

    def test_the_subject_library_is_hidden_unless_a_project_already_uses_it(self):
        p, pid = self.seed()
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(any("Kho chủ thể" in e.label for e in at.expander))
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        self.assertFalse(any(c.key == f"vsubj_{pid}" for c in at.checkbox))
        p.set_use_subjects(pid, True)                                         # an older project that turned it on can still turn it off
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        self.assertTrue(any(c.key == f"vsubj_{pid}" for c in at.checkbox))

    def test_attach_subjects_switch_is_saved(self):
        p, pid = self.seed()
        os.environ["SHOW_SUBJECT_LIBRARY"] = "1"
        self.addCleanup(os.environ.pop, "SHOW_SUBJECT_LIBRARY", None)
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[3]).run()
        box = at.checkbox(key=f"vsubj_{pid}")
        # M7: Seedance drops subjects next to a first frame (every clip has one), so the switch is shown locked, not silently useless
        self.assertTrue(box.disabled)
        self.assertEqual(Pipeline(connect(self.db)).project(pid)["use_subjects"], 0)

    def script_open(self, pid):
        """Step 1 with the script card unfolded (S9.1: it folds to one line once the script is split)."""
        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state[f"fold_script_{pid}"] = True
        return at.run()

    def test_the_script_card_has_its_summary_and_the_input_folds_into_an_expander(self):
        """S9.1 (người dùng sau #8): "thêm nút thu gọn cho phần kịch bản". S14.14 G-a: the old fold (fold_script_{pid}_btn, in RENAMED of
        tools/ui_v2_acceptance.py) went with the old screen — in v2 card ① carries the one-line summary as a pill and the input box
        sits in the closed "📥 Nhập / thay kịch bản" expander once the script is split."""
        p, pid = self.seed()
        p.set_script_text(pid, "TÊN KỊCH BẢN" + chr(10) + "CẢNH 1. ĐÊM" + chr(10) + "Lyra: Đi thôi.")
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        html = " ".join(str(getattr(e.proto, "body", "")) for e in at.get("html"))
        self.assertIn("1 cảnh", html)                              # the summary pill of card ①
        self.assertNotIn(f"fold_script_{pid}_btn", [b.key for b in at.button])
        box = [e for e in at.expander if e.label.startswith("📥 Nhập / thay kịch bản")]
        self.assertEqual(len(box), 1)
        self.assertFalse(box[0].proto.expanded)

    def test_step1_shows_the_full_script_next_to_the_scene_list(self):
        p, pid = self.seed()
        p.set_script_text(pid, "TÊN KỊCH BẢN" + chr(10) + "CẢNH 1. ĐÊM" + chr(10) + "Lyra: Đi thôi.")
        at = self.script_open(pid)
        self.assertFalse(at.exception)
        markup = " ".join(m.value for m in at.markdown)
        self.assertIn("scriptfull", markup)
        self.assertIn("TÊN KỊCH BẢN", markup)                       # whole script, including the part before scene 1
        self.assertIn("<b>CẢNH 1. ĐÊM</b>", markup)                 # scene headings stand out
        self.assertTrue(any(e.label.startswith("S01") for e in at.expander))  # ...and the scene rows sit beside it

    def test_add_and_delete_a_scene_from_the_scene_list(self):
        p, pid = self.seed()
        at = self.script_open(pid)
        next(b for b in at.button if b.key == f"scene_add_{pid}").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(Pipeline(connect(self.db)).conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 2)
        at.toggle(key=f"sd_open_{pid}_2").set_value(True).run()
        next(b for b in at.button if b.key == f"scene_del_{pid}_2").click().run()
        self.assertEqual(Pipeline(connect(self.db)).conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 2)  # asked first
        next(b for b in at.button if b.key == f"scene_del_{pid}_2_yes").click().run()
        self.assertEqual(Pipeline(connect(self.db)).conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 1)

    def test_bible_accepts_a_non_human_entry_from_the_dashboard(self):
        p, pid = self.seed()
        at = self.open_all(AppTest.from_file(APP, default_timeout=30).run())
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
        self.assertEqual(p.reject(job, "ai_agent", "sai"), "escalated")    # S14.16: only an automatic reject is capped (was "user")
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
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
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
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
        at.button(key="settings_knowledge").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m.label for m in at.metric][:3], ["Tài liệu đang bật", "Ký tự gửi Claude mỗi lần chạy", "≈ token mỗi lần chạy"])
        labels = [e.label for e in at.expander]
        self.assertTrue(any("Cơ bản điện ảnh" in l for l in labels))          # built-in documents are listed
        self.assertEqual(at.selectbox(key="kb_group").value, "director")
        at.selectbox(key="kb_group").set_value("qc").run()
        self.assertTrue(any("Lỗi thường gặp của ảnh AI" in e.label for e in at.expander))
        entry = knowledge.add_doc("qc", "phong cach.md", "Chấm gắt hơn.".encode("utf-8"))
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.button(key="settings_knowledge").click().run()
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
            at.button(key="settings_knowledge").click().run()
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
            at.button(key="settings_knowledge").click().run()
            self.assertTrue(any("cẩm nang đã cũ" in w.value for w in at.warning))  # asks to distil again
        finally:
            os.environ.pop("LLM_PROVIDER", None)

    def test_autopilot_panel_lists_what_is_missing_before_it_can_start(self):
        self.seed()
        for k in ("IMAGE_PROVIDER", "VIDEO_PROVIDER", "LLM_PROVIDER", "ANTHROPIC_API_KEY"):
            os.environ.pop(k, None)
        at = AppTest.from_file(APP, default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Tự động hoàn toàn" in m.value for m in at.markdown))     # v2: card ③'s "🚀 Tự động hoàn toàn" panel
        self.assertTrue(any("✖" in m.value for m in at.markdown))     # reasons shown, no start possible

    def test_performance_monitor_tab_shows_load_and_health(self):
        self.seed()
        at = AppTest.from_file(APP, default_timeout=30)
        at.query_params["step"] = "monitor"
        at.run()
        self.assertFalse(at.exception)
        # S14.14 G-a: 📊 Theo dõi is v2 only — stats are D.stat tiles and the tables are HTML inside closed expanders
        md = " ".join(m.value for m in at.markdown)
        self.assertIn("Theo dõi hiệu suất", md)
        self.assertIn("Lượt gửi thật hôm nay", md)
        self.assertIn("Gen video", md)                                             # the per-job-kind table
        self.assertTrue(any("Giám sát từng khâu" in e.label for e in at.expander))
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
        # the per-character outfit popovers, and (S14.14 G-a: the Kịch bản screen is v2 only) its "Chi tiết" ⓘ and "⋯ Cách khác" aside
        bars = [x for x in at.get("popover") if not x.proto.popover.label.startswith("👗")
                and x.proto.popover.label not in ("Chi tiết", "⋯ Cách khác")]
        self.assertEqual(len(bars), 6)                    # risk corner + 💬 góp ý (S14.19) + "new project" + 📥 inbox + 💵 card + ⚙
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
        at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
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
            next(b for b in at.button if "Gen video" in b.label).click().run()   # queue + send; the page then polls by itself
            at.run()
            at.run()
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
        self.with_lock(p, pid)
        lock_character_bible(p, pid)
        os.environ["IMAGE_PROVIDER"] = "mock"
        os.environ["HEARTBEAT_SEC"] = "0"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            at.radio(key="step").set_value(at.radio(key="step").options[2]).run()
            next(b for b in at.button if "Gen ảnh các cảnh" in b.label).click().run()   # queue + send; the page then polls by itself
            at.run()
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
