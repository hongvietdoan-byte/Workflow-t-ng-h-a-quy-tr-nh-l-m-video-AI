"""S11.2 bộ đo 5 ý tưởng (tools/experiments/idea_script_eval.py): chạy đủ 4 lượt, ghi / chạy lại, phiếu chấm, cổng bật cờ — 0 USD."""
import json
import os
import sys
import tempfile
import unittest

from core import assets, llm_runner
from core.db import connect
from core.pipeline import Pipeline
from tests.test_idea_to_script import ANCHORS, make_kit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "experiments"))
import idea_script_eval as E  # noqa: E402

ITEMS = [{"id": 1, "idea": "Kelly và Maxim tranh nhau một thùng thính ở Đảo Quân Sự.", "duration_s": 30, "characters": ["KELLY"], "anchors": ANCHORS},
         {"id": 2, "idea": "Maxim lật kèo ở bo cuối bằng một cú nhảy liều lĩnh.", "duration_s": 30, "cta": "Tải Free Fire ngay", "anchors": ANCHORS}]


class EvalTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("nghiệm thu", operating_mode="human_qc")
        make_kit(self.p.conn)                                                             # S14.31: the Biên kịch only reads what can be built
        self.tmp = tempfile.mkdtemp()

    def test_record_then_replay_gives_the_same_scripts_and_a_sheet(self):
        calls = os.path.join(self.tmp, "calls.jsonl")
        out = E.run_all(self.p, self.pid, ITEMS, E.RecordingClient(llm_runner.MockLlm(), calls), 1.0, log=lambda *a, **k: None)
        self.assertEqual(len(open(calls, encoding="utf-8").readlines()), 8)            # 2 ideas × 4 turns
        st = out["results"]["1"]
        self.assertTrue(all(a["defaulted"] for a in st["answers"]))                       # the eval answers nothing: defaults, written down
        self.assertEqual(st["chosen"], 0)
        self.assertEqual(st["script_checks"]["scenes"], 2)
        again = E.run_all(self.p, self.pid, ITEMS, E.ReplayClient(calls), 1.0, log=lambda *a, **k: None)
        self.assertEqual(again["results"]["2"]["script"], out["results"]["2"]["script"])
        self.assertEqual(again["errors"], [])
        md = E.sheet(ITEMS, out, self.tmp)
        self.assertIn("## Ý tưởng 2", md)
        self.assertIn("★", md)
        self.assertIn('⛔ CTA "Tải Free Fire ngay" chưa có ở cảnh cuối', md)              # the mock script has no CTA
        self.assertIn("| 2 |  |  |  |  |  |  |", md)

    def test_a_prompt_not_in_the_record_is_an_error_not_a_silent_answer(self):
        open(os.path.join(self.tmp, "empty.jsonl"), "w").close()
        out = E.run_all(self.p, self.pid, ITEMS[:1], E.ReplayClient(os.path.join(self.tmp, "empty.jsonl")), 1.0, log=lambda *a, **k: None)
        self.assertEqual(out["errors"][0]["code"], "replay_miss")
        self.assertTrue(E.blocking(out["results"]["1"]))

    def test_scores_and_gate(self):
        results = {"1": {"script": "x", "script_checks": {"problems": []}, "outline_checks": []},
                   "2": {"script": "x", "script_checks": {"problems": []}, "outline_checks": [{"level": "warn", "text": "w"}]}}
        path = os.path.join(self.tmp, "sheet.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# x\n## Bảng điểm (điền 1–5)\n| Ý tưởng | a | b | c | d | e | Ghi chú |\n|---|---|---|---|---|---|---|\n"
                     "| 1 | 5 | 4 | 4 | 5 | 4 | tốt |\n| 2 | 4 | 4 | 3 | 4 | 5 |  |\n")
        g = E.gate(E.read_scores(path), results)
        self.assertEqual(g["mean"], 4.2)
        self.assertTrue(g["pass"])
        results["2"]["script_checks"]["problems"] = ["thiếu CTA"]
        self.assertFalse(E.gate(E.read_scores(path), results)["pass"])                   # a code block fails the gate whatever the score
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("| 3 | 5 |  | 4 | 4 | 4 |  |\n")
        with self.assertRaises(SystemExit):
            E.read_scores(path)                                                           # an empty cell is refused, not counted as 0


if __name__ == "__main__":
    unittest.main()
