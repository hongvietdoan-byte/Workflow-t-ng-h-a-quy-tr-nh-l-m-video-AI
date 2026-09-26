"""Regressions for the 6 problems the first AI Development System graders found (docs/DANH_GIA_DEVSYS_2026-09-26.md) — one class per
problem; each test fails on the code before the fix. No real provider is called."""
import json
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from core import budget, cost, diag, experiments, features, lessons, llm_runner, location_pack, research
from core.db import connect
from core.pipeline import Pipeline
from devsys import collect
from tests.test_location_pack import PackTests


# ---- 1: the Kling multi-shot experiment sent a paid clip outside the money cap --------------------------------------------------
class ExperimentCapTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("exp", aspect="9:16")
        self.dir = tempfile.mkdtemp()
        self.sent = []
        sent = self.sent

        class Provider:
            name = "clipai"

            def submit(self, *a, **k):
                sent.append((a, k))
                return "clipai:video:1"
        self.provider = Provider()
        plan = ([{"idx": 1, "jid": 1}, {"idx": 2, "jid": 2}], [{"prompt": "a", "duration": 10}, {"prompt": "b", "duration": 5}], 15)
        self.plan = mock.patch.object(experiments, "_plan", return_value=plan)
        self.plan.start()

    def tearDown(self):
        self.plan.stop()

    @mock.patch.dict(os.environ, {"CLIPAI_KLING_MODE": "std"})
    def test_over_the_cap_nothing_is_sent_or_recorded(self):
        budget.restart(self.p.conn, usd=1.0)                                     # 15 s x 0.08 = 1.20 > 1.00
        with self.assertRaises(ValueError) as e:
            experiments.kling_multishot(self.p, self.pid, 1, self.provider, self.dir)
        self.assertIn("vượt trần", str(e.exception))
        self.assertEqual(self.sent, [])
        self.assertEqual(budget.spent(self.p.conn)["usd"], 0)

    @mock.patch.dict(os.environ, {"CLIPAI_KLING_MODE": "std"})
    def test_inside_the_cap_it_is_sent_counted_and_priced_before_the_click(self):
        budget.restart(self.p.conn, usd=10.0)
        self.assertAlmostEqual(experiments.estimate(self.p, self.pid, 1)["usd"], 1.2)
        experiments.kling_multishot(self.p, self.pid, 1, self.provider, self.dir)
        self.assertEqual(len(self.sent), 1)
        self.assertAlmostEqual(budget.spent(self.p.conn)["usd"], 1.2)


# ---- 2: Claude buttons without a price; web search fees outside the ledger -----------------------------------------------------
class PriceBeforeClickTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect()

    def test_a_web_search_is_recorded_and_priced(self):
        reply = llm_runner.LlmReply("{}", 1000, 100, "end_turn", web_searches=3)
        client = llm_runner.AnthropicClient.__new__(llm_runner.AnthropicClient)
        client.ledger, client.name, client.model = True, "anthropic", "claude-sonnet-5"
        path = os.path.join(tempfile.mkdtemp(), "ledger.sqlite")
        client._ledger_conn = lambda: connect(path)
        client._record(reply)
        self.conn = connect(path)
        row = self.conn.execute("SELECT quantity, unit FROM usage_events WHERE tier='web_search'").fetchone()
        self.assertEqual((row["quantity"], row["unit"]), (3, "search"))
        tokens = budget.token_price(cost.load_pricing(), "claude-sonnet-5", "input", 1000) + \
            budget.token_price(cost.load_pricing(), "claude-sonnet-5", "output", 100)
        self.assertAlmostEqual(budget.spent(self.conn)["llm_usd"], round(tokens + 0.03, 4), places=4)

    def test_the_parser_reads_the_search_count(self):
        client = llm_runner.AnthropicClient.__new__(llm_runner.AnthropicClient)
        body = json.dumps({"content": [{"type": "text", "text": "x"}], "stop_reason": "end_turn",
                           "usage": {"input_tokens": 5, "output_tokens": 2, "server_tool_use": {"web_search_requests": 2}}})
        resp = mock.Mock(status=200, body=body.encode("utf-8"))
        self.assertEqual(client._parse(resp).web_searches, 2)

    def test_research_and_lesson_buttons_have_an_estimate(self):
        usd = research.estimate(self.conn)
        n = sum(len(v) for v in research.DEFAULT_TOPICS.values())
        self.assertGreaterEqual(usd, n * research.MAX_SEARCHES * 0.01)         # the searches alone
        self.assertEqual(lessons.ready_count(self.conn), 0)

    def test_audio_buttons_say_the_count_and_the_trial_cap(self):
        self.assertIn("chưa có giá USD", budget.audio_tag(self.conn, 3))
        budget.restart(self.conn, usd=10.0)
        self.assertIn("0/", budget.audio_tag(self.conn))
        self.assertEqual(budget.audio_tag(self.conn, 0), "")


# ---- 3: a camera Blender did not return was skipped silently and rendered again every autopilot tick -----------------------------
class PlateFailureTests(unittest.TestCase):
    setUp, tearDown, project = PackTests.setUp, PackTests.tearDown, PackTests.project

    def half_render(self, cfg, blender=None, timeout=0):
        """Blender returns nothing (a crash in the camera loop, a bad model)."""
        self.calls.append(cfg)
        return {"plates": [], "out_dir": cfg["out_dir"], "error": "camera loop crashed"}

    def test_a_missing_camera_is_said_marked_and_not_rendered_again(self):
        pid = self.project("f")
        data = os.path.join(self.tmp, "projects")
        idx = location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (90, 160), blender="x", render=self.half_render)
        runs = len(self.calls)
        self.assertTrue(idx and all(v.get("failed") for v in idx.values()))
        sid = int(next(iter(idx)))
        self.assertIn("Blender không trả về", location_pack.plate_failed(data, pid, sid))
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='plate_missing'").fetchone())
        location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (90, 160), blender="x", render=self.half_render)
        self.assertEqual(len(self.calls), runs)                                  # not rendered again at the next tick
        self.assertGreater(location_pack.forget_failures(self.tmp), 0)
        location_pack.ensure_plates(self.p.conn, pid, data, self.tmp, (90, 160), blender="x", render=self.half_render)
        self.assertGreater(len(self.calls), runs)                                # retried after the person fixed it


# ---- 4: diag.record swallowed SQLite errors ------------------------------------------------------------------------------------
class DiagLostTests(unittest.TestCase):
    def test_a_refused_write_is_kept_counted_and_never_raises(self):
        path = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = sqlite3.connect(path)                                           # no diag_events table: every write fails
        before = diag.lost()
        diag.record(conn, "system", "warn", "không ghi được", "x")
        self.assertEqual(diag.lost(), before + 1)
        with open(path + ".diag_lost.log", encoding="utf-8") as f:
            self.assertIn("không ghi được", f.read())


# ---- 5: the devsys measures fed the graders wrong facts ------------------------------------------------------------------------
class DevsysMeasureTests(unittest.TestCase):
    def test_flags_switched_on_in_dashboard_env_count_as_on(self):
        root = tempfile.mkdtemp()
        with open(os.path.join(root, "dashboard.env"), "w", encoding="utf-8") as f:
            f.write("CLIPAI_TOKEN=secret\nFEATURE_FILM_CREW=1\nFEATURE_LIP_SYNC = 0\n")
        self.assertEqual(collect.env_file_flags(root), {"film_crew": "1", "lip_sync": "0"})   # keys are never read

    def test_a_wrapped_entry_is_read_whole_and_sub_items_of_a_replaced_parent_are_closed(self):
        text = ("## Đang làm\n"
                "- [ ] sửa giao diện nút ở\n"
                "  `core/voice.py` còn: nghe thử\n"
                "- [x] *(đã thay)* kế hoạch cũ\n"
                "  - [ ] ô con cũ\n"
                "- [ ] việc mới\n")
        items = collect.parse_todo(text)
        self.assertEqual([i["line"] for i in items], [2, 6])
        self.assertIn("core/voice.py", items[0]["text"])
        self.assertIn("còn:", items[0]["markers"])

    def test_devsys_tools_and_dashboard_screens_have_their_tests(self):
        cfg = collect.load_areas(os.path.join(collect.ROOT, "devsys", "areas.json"))
        mods = {m for v in collect.test_map(collect.ROOT, cfg).values() for m in v["modules"]}
        for f in ("devsys/collect.py", "devsys/scorer.py", "dashboard/steps/step1.py", "dashboard/admin.py"):
            self.assertIn(f, mods)

    def test_a_test_run_older_than_the_code_is_said(self):
        with mock.patch.object(collect, "git", side_effect=lambda root, *a, **k: "core/x.py\ndocs/a.md\n" if a[0] == "diff" else "2\n"):
            stale = collect.tests_stale(collect.ROOT, {"commit": "abc"}, [{"path": "tools/y.py"}])
        self.assertEqual(stale, {"files": ["core/x.py", "tools/y.py"], "commits": 2})
        self.assertIsNone(collect.tests_stale(collect.ROOT, None, []))


# ---- 6: documents that described old flows -------------------------------------------------------------------------------------
class DocTests(unittest.TestCase):
    def test_the_lip_sync_label_says_sync_so_is_not_used(self):
        self.assertIn("không dùng sync.so", features.FEATURES["lip_sync"]["label"])


if __name__ == "__main__":
    unittest.main()
