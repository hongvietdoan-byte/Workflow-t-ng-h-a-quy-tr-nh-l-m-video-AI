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


if __name__ == "__main__":
    unittest.main()
