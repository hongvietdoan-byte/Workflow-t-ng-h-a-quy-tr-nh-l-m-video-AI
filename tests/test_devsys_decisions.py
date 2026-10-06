"""S14.50 (ý 1 từ tài liệu 'Prompt Spider' 06/10): bản đồ AI QUYẾT — devsys/decisions.json + devsys/decisions.py + trang 'Ai quyết'.
Bản đồ phải khớp code: mọi khâu Claude có trong code (tagged("…"), _run(…, "…"), STAGE = "…", STAGE_SETTINGS) có ít nhất một điểm
'claude'; mọi 'where' (file:hàm) tồn tại — đổi tên hàm mà quên bản đồ thì test đỏ."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from devsys import decisions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MapTests(unittest.TestCase):
    def setUp(self):
        self.doc = decisions.load()

    def test_every_claude_stage_in_code_is_mapped(self):
        found = decisions.claude_stages_in_code(ROOT)
        self.assertGreaterEqual(len(found), 20)
        self.assertEqual(decisions.unmapped_stages(self.doc, ROOT), [])

    def test_every_where_exists(self):
        self.assertEqual(decisions.broken_wheres(self.doc, ROOT), [])

    def test_fields_are_valid(self):
        self.assertEqual(decisions.problems(self.doc), [])
        ids = [d["id"] for d in self.doc["items"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_problems_are_reported_not_dropped(self):
        bad = {"steps": {"a": "A"}, "items": [{"id": "x", "step": "zz", "who": "robot", "what": "", "where": "nowhere"},
                                              {"id": "y", "step": "a", "who": "claude", "what": "w", "where": "core/db.py:connect"}]}
        got = " ".join(decisions.problems(bad))
        for word in ("zz", "robot", "what", "where", "stage"):
            self.assertIn(word, got)
        self.assertIn("core/zzz.py:f", " ".join(decisions.broken_wheres({"items": [{"id": "q", "where": "core/zzz.py:f"}]}, ROOT)))
        self.assertIn("core/db.py:khong_co", " ".join(decisions.broken_wheres({"items": [{"id": "q", "where": "core/db.py:khong_co"}]}, ROOT)))

    def test_unmapped_stage_is_listed(self):
        doc = {"items": [d for d in self.doc["items"] if d.get("stage") != "sfx"]}
        self.assertIn("sfx", decisions.unmapped_stages(doc, ROOT))

    def test_summary_shares(self):
        items = [{"step": "s", "who": "code"}] * 3 + [{"step": "s", "who": "claude"}] + [{"step": "t", "who": "human"}]
        s = decisions.summary({"steps": {"s": "S", "t": "T"}, "items": items})
        self.assertEqual(s["all"]["n"], 5)
        self.assertEqual(s["all"]["code"], 3)
        self.assertAlmostEqual(s["all"]["pct"]["code"], 60.0)
        self.assertEqual(s["by_step"]["t"]["human"], 1)


class PageTests(unittest.TestCase):
    def test_page_renders_shares_and_suggestions(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:  # pragma: no cover
            self.skipTest("streamlit.testing không có")
        at = AppTest.from_file(os.path.join(ROOT, "devsys", "app.py"), default_timeout=180)
        at.run()
        at.sidebar.radio[0].set_value("Ai quyết").run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertTrue(at.title[0].value.startswith("Ai quyết"))
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("Code", text)
        frames = " ".join(f.value.to_string() for f in at.dataframe)
        self.assertIn("voice_casting", frames)                                         # một gợi ý chuyển sang code


if __name__ == "__main__":
    unittest.main()
