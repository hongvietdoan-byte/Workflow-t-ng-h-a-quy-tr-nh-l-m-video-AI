"""01/10 B1: every Claude stage named in the code must fit under the cap of its budget line even at its worst case. Four times a
stage without its own max_tokens (video_analysis 28/09, translate 28/09, screenwriter 01/10, then 11 more) got the 32k default, whose
worst case beat the 0.20 USD "Claude — khác" line of a locked project, so the lock refused it for ever."""
import re
import unittest
from pathlib import Path

from core import llm_runner, project_budget

ROOT = Path(__file__).resolve().parent.parent


def _stages():
    found = set()
    for d in ("core", "tools", "devsys", "dashboard"):
        for f in (ROOT / d).rglob("*.py"):
            found.update(re.findall(r'tagged\(\s*"([a-z_0-9]+)"', f.read_text(encoding="utf-8", errors="ignore")))
    return found


class StageBudgetScan(unittest.TestCase):
    def test_scan_finds_stages(self):
        self.assertGreaterEqual(len(_stages()), 15)

    def test_every_other_stage_has_a_bounded_answer(self):
        for st in sorted(_stages()):
            mt = llm_runner.stage_settings(st).get("max_tokens")
            self.assertTrue(mt, st)
            self.assertLessEqual(mt, 64000, st)

    def test_worst_case_fits_the_line_cap(self):
        model = "claude-sonnet-5-5"
        caps = {"claude_other": project_budget.OTHER_CLAUDE_USD}
        for st in sorted(_stages()):
            line = project_budget.claude_stage(st)
            if line not in caps:
                continue                              # director / qc / motion caps come from estimates, not a fixed line
            mt = llm_runner.stage_settings(st)["max_tokens"]
            worst = llm_runner._price(model, "input", 6000) * 1.25 + llm_runner._price(model, "output", mt)
            self.assertLess(worst, caps[line], f"{st}: worst ≈ {worst:.3f} ≥ {caps[line]}")


if __name__ == "__main__":
    unittest.main()
