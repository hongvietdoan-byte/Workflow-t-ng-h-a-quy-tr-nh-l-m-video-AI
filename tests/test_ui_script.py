"""S13 lane E: the Kịch bản screen under the UI v2 flag — empty project and project with scenes + characters + locked Bible.
Every widget key of the old screen must still exist; the flag off keeps the old screen (covered by test_step1_flow / test_dashboard)."""
import os
import tempfile
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

from core import script_parser
from core.db import connect
from core.pipeline import Pipeline
from dashboard.steps import step1_v2
from tests.test_autopilot import SAMPLE

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")

OLD_KEYS = ("up_{p}", "paste_{p}", "btn_analyse_{p}", "lock_go_{p}", "ap_gate_bible_{p}", "ap_gate_pilot_{p}", "ap_gate_board_{p}", "ref_go_{p}")


def tree_keys(at):
    """Every element key in the tree (file_uploader included)."""
    out = set()

    def walk(node):
        key = getattr(node, "key", None)
        if key:
            out.add(key)
        for child in getattr(node, "children", {}).values():
            walk(child)
    walk(at.main)
    return out


def ordered_keys(at):
    """Every element key in drawing order (S14.28: which block comes first)."""
    out = []

    def walk(node):
        key = getattr(node, "key", None)
        if key and key not in out:
            out.append(key)
        for child in getattr(node, "children", {}).values():
            walk(child)
    walk(at.main)
    return out


class ScriptScreenV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
                                           "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "ku"), "FEATURE_UI_V2": "1", "LLM_PROVIDER": "mock"})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect(self.db))

    def run_app(self):
        at = AppTest.from_file(APP, default_timeout=90).run()
        self.assertFalse(at.exception, at.exception)
        return at

    def html(self, at):
        """Markdown + st.html text of the page (the injected style block excluded)."""
        parts = [m.value or "" for m in at.markdown] + [getattr(getattr(e, "proto", None), "body", "") or "" for e in at.get("html")]
        return "\n".join(x for x in parts if not x.lstrip().startswith("<style"))

    def test_new_project_shows_empty_state_hero_and_the_input_panel(self):
        pid = self.p.create_project("Dự án trống")
        at = self.run_app()
        html = self.html(at)
        self.assertIn("v2-hero-title", html)                               # hero with the project title
        self.assertIn("Dự án trống", html)
        self.assertIn("v2-empty", html)                                    # the "no script yet" state
        self.assertIn("Đầu vào", html)                                     # the 📎 input panel is the first card
        keys = tree_keys(at)
        for k in OLD_KEYS:
            if k.startswith(("lock_go", "ap_gate")):                       # need scenes / characters
                continue
            self.assertIn(k.format(p=pid), keys, k)
        self.assertNotIn(f"script-cta_{pid}", keys)                         # nothing to plan before a script exists
        self.assertEqual(step1_v2.next_kind(self.p, pid, [], [], False, False, False), "analyse")

    def project_with_bible(self, lock: bool = True):
        pid = self.p.create_project("Dự án có kịch bản")
        paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
        script_parser.import_scenes(self.p, pid, script_parser.split_scenes(paragraphs), full_text="\n".join(paragraphs))
        for name in ("LYRA", "KAEL"):
            self.p.conn.execute("INSERT INTO characters (project_id, name, description, locked, anchor_approved) VALUES (?,?,?,?,1)",
                                (pid, name, "mô tả " + name, 1 if lock else 0))
        self.p.conn.commit()
        return pid

    def test_project_with_scenes_characters_and_locked_bible_keeps_every_old_key(self):
        pid = self.project_with_bible(lock=True)
        at = self.run_app()
        html = self.html(at)
        for needle in ("Bible đã khóa", "nhân vật", "cảnh"):               # pills, not ad-hoc badges
            self.assertIn(needle, html)
        self.assertIn("v2-pill", html)
        keys = tree_keys(at)
        for k in OLD_KEYS:
            self.assertIn(k.format(p=pid), keys, k)
        self.assertIn(f"script-cta-next_{pid}", keys)                      # Bible locked → the primary action is "go to Storyboard"
        self.assertTrue(at.get("popover"), "long explanations live in ⓘ popovers")

    def test_long_caption_keeps_its_whole_text_for_the_info_popover(self):
        long = "Ưu tiên model theo slide ClipAI: cảnh quan trọng dùng model tốt nhất, cảnh thường dùng model hiệu quả. " * 2
        short = step1_v2._short(long)
        self.assertLess(len(short), len(long))
        self.assertLessEqual(len(short), 90)
        self.assertEqual(step1_v2._short("Ngắn"), "Ngắn")

    def test_primary_action_follows_the_state(self):
        pid = self.project_with_bible(lock=False)
        at = self.run_app()
        self.assertIn(f"script-cta-lock_{pid}", tree_keys(at))
        self.assertIn(f"lock_go_{pid}", tree_keys(at))                     # the old button is still there
        self.assertIn("Bible chưa khóa", self.html(at))
        pid2 = self.p.create_project("Chỉ tách cảnh")
        paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
        script_parser.import_scenes(self.p, pid2, script_parser.split_scenes(paragraphs), full_text="\n".join(paragraphs))
        scenes = self.p.conn.execute("SELECT * FROM scenes WHERE project_id=?", (pid2,)).fetchall()
        self.assertEqual(step1_v2.next_kind(self.p, pid2, scenes, [], False, False, False), "plan")
        self.assertEqual(step1_v2.next_kind(self.p, pid, scenes, [1], False, False, False), "lock")
        with mock.patch.object(step1_v2, "allowed", return_value=True):
            self.assertEqual(step1_v2.next_kind(self.p, pid, scenes, [1], False, False, True), "budget")     # budget not locked yet
            self.assertEqual(step1_v2.next_kind(self.p, pid, scenes, [1], True, True, True), "next")
        with mock.patch.object(step1_v2, "allowed", return_value=False):                                     # no autopilot right → skip it
            self.assertEqual(step1_v2.next_kind(self.p, pid, scenes, [1], False, False, True), "lock")

    # ---- slim pass (01/10): details in ⓘ, panels closed by default, only the next job open --------------------------------------------
    def test_next_panel_is_the_one_open_job(self):
        pid = self.p.create_project("Trình tự việc")
        self.assertEqual(step1_v2.next_panel(self.p, pid, [], [], False), "")                       # no script → nothing in card ② opens
        paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
        script_parser.import_scenes(self.p, pid, script_parser.split_scenes(paragraphs), full_text="\n".join(paragraphs))
        scenes = self.p.conn.execute("SELECT * FROM scenes WHERE project_id=?", (pid,)).fetchall()
        self.p.set_project_field(pid, "aspect", None)
        self.assertEqual(step1_v2.next_panel(self.p, pid, scenes, [], False), "format")             # format not chosen yet
        self.p.set_project_field(pid, "aspect", "9:16")
        self.p.set_project_field(pid, "genre", "SHORT_FORM")
        self.assertEqual(step1_v2.next_panel(self.p, pid, scenes, [], False), "director")
        fake = [{"anchor_approved": 0}]
        self.assertEqual(step1_v2.next_panel(self.p, pid, scenes, fake, False), "bible")
        self.assertEqual(step1_v2.next_panel(self.p, pid, scenes, [{"anchor_approved": 1}], True), "")

    def prepared(self, lock: bool):
        pid = self.project_with_bible(lock=lock)
        self.p.set_project_field(pid, "aspect", "9:16")
        self.p.set_project_field(pid, "genre", "SHORT_FORM")
        return pid

    def test_locked_bible_leaves_every_panel_of_card_two_closed(self):
        pid = self.prepared(lock=True)
        at = self.run_app()
        self.assertEqual(at.session_state["_script_next"], "")
        self.assertFalse(at.session_state[f"fold_director_{pid}"])
        self.assertFalse(at.session_state[f"fold_bible_{pid}"])
        opened = [e.label for e in at.expander if e.proto.expanded]
        self.assertEqual(opened, [], opened)                                # 📐 Định dạng, 🧰 Tài nguyên, 1f Rà thoại … all one line each
        labels = " ".join(e.label for e in at.expander)
        self.assertIn("Định dạng", labels)                                  # …but each still has its one-line summary

    def test_only_the_next_job_is_open(self):
        pid = self.prepared(lock=False)                                     # characters exist, Bible not locked → the Bible is the job
        at = self.run_app()
        self.assertEqual(at.session_state["_script_next"], "bible")
        self.assertTrue(at.session_state[f"fold_bible_{pid}"])
        self.assertFalse(at.session_state[f"fold_director_{pid}"])
        self.assertEqual([e.label for e in at.expander if e.proto.expanded], [])

    def test_notes_become_one_line_plus_info_and_old_boxes_when_flag_off(self):
        def app():
            import streamlit as st
            from dashboard.steps.step1_v2 import say
            say("warning", "Một cảnh báo rất dài " * 20, "t-warn", "Tóm tắt cảnh báo")
            say("success", "Đã xong việc", "t-ok")
            say("info", "Ghi chú", "t-info")
        at = AppTest.from_function(app).run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(len(at.warning), 0)                                # no st.warning box in v2
        self.assertEqual(len(at.success), 0)
        self.assertEqual(len(at.info), 0)
        body = " ".join(m.value for m in at.markdown)
        self.assertIn("Tóm tắt cảnh báo", body)                             # the one summary line …
        self.assertEqual(len(at.get("popover")), 3)                         # … and its ⓘ (the whole text lives inside)
        full = [m.value for m in at.markdown if "Một cảnh báo rất dài" in (m.value or "")]
        self.assertTrue(full, "the full message is kept inside the ⓘ")
        with mock.patch.dict(os.environ, {"FEATURE_UI_V2": "0"}):
            off = AppTest.from_function(app).run()
            self.assertFalse(off.exception, off.exception)
            self.assertEqual((len(off.warning), len(off.success), len(off.info)), (1, 1, 1))     # flag off = the old boxes
            self.assertEqual(len(off.get("popover")), 0)

    def test_cap_summary_keeps_the_figure_outside_and_the_text_inside(self):
        def app():
            from dashboard.steps.step1_v2 import cap
            cap("💵 Ước tính Director (model X): 1 lượt · ~12k token vào / ~3k ra ≈ 0,34 USD — nếu bật hai lượt: 5 lượt ≈ 0,90 USD · thô ±50%",
                summary="💵 Ước tính Director ≈ 0,34 USD")
        at = AppTest.from_function(app).run()
        self.assertFalse(at.exception, at.exception)
        body = " ".join(m.value for m in at.markdown)
        self.assertIn("≈ 0,34 USD", body)
        self.assertIn("nếu bật hai lượt", body)                             # full text inside the popover
        self.assertEqual(len(at.get("popover")), 1)

    def test_lock_row_has_no_second_primary_button(self):
        pid = self.prepared(lock=False)
        at = self.run_app()
        primaries = [b.key for b in at.button if b.proto.type == "primary"]
        self.assertIn(f"script-cta-lock_{pid}", primaries)
        self.assertNotIn(f"lock_go_{pid}", primaries)                       # the hero owns THE primary action
        self.assertIn(f"lock_go_{pid}", tree_keys(at))                      # …but the old widget key is kept

    # ---- S14.28: kịch bản lên đầu, tham chiếu sau phân tích cảnh, loại Trang phục, dòng trang phục trong danh sách nhân vật ----
    def test_s14_28_script_first_and_no_reference_form_before_analysis(self):
        pid = self.p.create_project("Chưa có kịch bản")
        at = self.run_app()
        keys = ordered_keys(at)
        for k in (f"ref_go_{pid}", f"ref_up_{pid}", f"ref_name_{pid}"):
            self.assertNotIn(k, keys)                                         # no big form before there is a script
        self.assertIn(f"up_{pid}", keys)
        self.assertLess(keys.index(f"card-script-a-{pid}"), keys.index(f"card-script-refs-{pid}"))
        self.assertIn("Gắn ảnh tham chiếu sau khi phân tích cảnh", self.html(at))
        coming = [b for b in at.button if (b.key or "").startswith("coming_")]
        self.assertEqual(len(coming), 3)
        self.assertTrue(all(b.disabled for b in coming))
        self.assertNotIn("v2-pill", "".join(getattr(getattr(e, "proto", None), "body", "") or "" for e in at.get("html")
                                             if "Sắp có" in (getattr(getattr(e, "proto", None), "body", "") or "")))  # no 3 big cards

    def test_s14_28_references_after_scene_analysis_folded_with_recognised_names(self):
        pid = self.prepared(lock=False)
        at = self.run_app()
        keys = ordered_keys(at)
        self.assertLess(keys.index(f"card-script-a-{pid}"), keys.index(f"card-script-refs-{pid}"))
        self.assertLess(keys.index(f"card-script-refs-{pid}"), keys.index(f"card-script-b-{pid}"))
        self.assertIn(f"ref_go_{pid}", keys)                                  # same widget keys, inside the fold
        refs = [e for e in at.expander if e.label.startswith("🖼 Tham chiếu")]
        self.assertEqual(len(refs), 1)
        self.assertFalse(refs[0].proto.expanded)                              # folded by default
        self.assertIn("LYRA", at.selectbox(key=f"ref_for_{pid}").options)    # attach per recognised character / place

    def test_s14_28_outfit_kind_asks_which_character(self):
        pid = self.prepared(lock=False)
        at = self.run_app()
        self.assertNotIn(f"ref_outfit_for_{pid}", tree_keys(at))
        at.selectbox(key=f"ref_kind_{pid}").set_value("outfit").run()
        self.assertFalse(at.exception, at.exception)
        opts = at.selectbox(key=f"ref_outfit_for_{pid}").options
        self.assertIn("LYRA", opts)
        self.assertIn("KAEL", opts)

    def test_s14_28_character_list_shows_outfit_line_and_kho_outfits(self):
        from core import assets
        from tests.test_new_skills import PNG
        os.environ["ASSET_DIR"] = os.path.join(self.tmp, "assets")
        self.addCleanup(lambda: os.environ.pop("ASSET_DIR", None))
        pid = self.prepared(lock=False)
        kho = assets.create(self.p.conn, "FF", "outfit", "Đồ bơi hè")                  # shared Kho outfit, NOT attached to the project
        img = assets.add_image(self.p.conn, kho, "a.png", PNG, status="approved")
        img_id = self.p.conn.execute("SELECT id FROM asset_images WHERE asset_id=?", (kho,)).fetchone()["id"]
        assets.set_outfit(self.p.conn, pid, "LYRA", [img_id])
        self.assertTrue(img)
        at = self.run_app()
        labels = [x.proto.popover.label for x in at.get("popover")]
        self.assertTrue(any(l.startswith("👗 Trang phục: Đồ bơi hè") for l in labels), labels)
        self.assertTrue(any(l.startswith("👗 Trang phục: mặc định FF") for l in labels), labels)
        self.assertIn("Trang phục", self.html(at))                                       # a column of the Character Bible table
        self.assertTrue(any("Đồ bơi hè" in o for o in at.multiselect(key=f"outfit_{pid}_KAEL").options))
        self.assertIn(f"outfit_set_{pid}_LYRA", tree_keys(at))                           # the paid 2-picture set button stays


class ScriptScreenOldUiTests(unittest.TestCase):
    """S14.28 on the old screen (flag off): the script fold first, the reference fold after it and absent before a script."""
    run_app, prepared, project_with_bible = ScriptScreenV2Tests.run_app, ScriptScreenV2Tests.prepared, ScriptScreenV2Tests.project_with_bible

    def setUp(self):
        ScriptScreenV2Tests.setUp(self)
        env = mock.patch.dict(os.environ, {"FEATURE_UI_V2": "0"})
        env.start()
        self.addCleanup(env.stop)

    def test_s14_28_old_ui_script_fold_before_references(self):
        pid = self.p.create_project("Cũ")
        at = self.run_app()
        keys = ordered_keys(at)
        self.assertNotIn(f"ref_go_{pid}", keys)
        self.assertNotIn(f"fold_refs_{pid}_btn", keys)
        pid2 = self.prepared(lock=False)
        at.session_state["global_pid"] = pid2
        at.run()
        keys = ordered_keys(at)
        self.assertLess(keys.index(f"fold_script_{pid2}_btn"), keys.index(f"fold_refs_{pid2}_btn"))




if __name__ == "__main__":
    unittest.main()
