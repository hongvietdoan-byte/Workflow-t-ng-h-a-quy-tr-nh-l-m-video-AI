import tempfile
import unittest
from pathlib import Path

from devsys import plan_progress


PLAN = """# Kế hoạch giả

### M4 — Dashboard
- [ ] M4.1 · Dashboard có cảnh báo · nặng:2 · 🔄 · ghi chú cũ

### M9 — Giám sát
- [ ] M9.0 · Quy tắc giám sát · nặng:1 · ✅ · đã thống nhất
- [ ] M9.2 · Đo KPI · nặng:2 · ⬜

## 6. Nhật ký
- 2026-10-23: dòng cũ
"""


def finding(severity="LỚN", run_no=3, **extra):
    return {
        "axis": "errors",
        "severity": severity,
        "type": "test-regression",
        "evidence": "tests/test_gate.py:27",
        "task_id": "M4.1",
        "reason": "Bài kiểm tra hồi quy đang thất bại.",
        "source": "CX24-GIAM-SAT",
        "observed_on": "2026-10-24",
        "run_no": run_no,
        **extra,
    }


class PlanWriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plan = Path(self.tmp.name) / "plan.md"
        self.plan.write_text(PLAN, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_major_finding_once_and_keeps_plan_parser_compatible(self):
        from devsys import plan_writer

        result = plan_writer.apply_findings(str(self.plan), [finding()])
        text = self.plan.read_text(encoding="utf-8")
        parsed = plan_progress.parse(text)

        self.assertEqual(result["written"], 1)
        self.assertEqual(result["report_only"], [])
        self.assertEqual(parsed["bad"], [])
        m9 = next(w for w in parsed["waves"] if w["id"] == "M9")
        self.assertEqual([t["id"] for t in m9["tasks"]], ["M9.0", "M9.2", "M9.3"])
        self.assertIn("GIÁM SÁT 2026-10-24 (#3)", text)
        self.assertIn("[GS-", text)
        self.assertIn("ghi chú cũ", text)
        backups = list(Path(self.tmp.name).glob("plan.md.giam-sat.*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), PLAN)

    def test_same_observation_is_idempotent_and_new_run_updates_existing_m9_item(self):
        from devsys import plan_writer

        first = plan_writer.apply_findings(str(self.plan), [finding()])
        after_first = self.plan.read_text(encoding="utf-8")
        second = plan_writer.apply_findings(str(self.plan), [finding()])
        self.assertEqual(self.plan.read_text(encoding="utf-8"), after_first)
        self.assertFalse(second["changed"])
        self.assertEqual(self.plan.read_text(encoding="utf-8"), after_first)
        self.assertEqual(len(list(Path(self.tmp.name).glob("plan.md.giam-sat.*.bak"))), 1)

        later = plan_writer.apply_findings(str(self.plan), [finding(run_no=4, observed_on="2026-10-25")])
        text = self.plan.read_text(encoding="utf-8")
        parsed = plan_progress.parse(text)
        m9 = next(w for w in parsed["waves"] if w["id"] == "M9")
        self.assertEqual(sum(t["id"].startswith("M9.") for t in m9["tasks"]), 3)
        self.assertTrue(later["changed"])
        self.assertIn("GIÁM SÁT 2026-10-25 (#4)", text)

    def test_small_findings_are_report_only(self):
        from devsys import plan_writer

        result = plan_writer.apply_findings(str(self.plan), [finding(severity="NHỎ")])
        self.assertEqual(result["written"], 0)
        self.assertEqual(len(result["report_only"]), 1)
        self.assertFalse(result["changed"])
        self.assertEqual(self.plan.read_text(encoding="utf-8"), PLAN)
        self.assertEqual(list(Path(self.tmp.name).glob("*.bak")), [])

    def test_missing_affected_task_fails_without_mutating_plan(self):
        from devsys import plan_writer

        with self.assertRaises(plan_writer.PlanWriterError):
            plan_writer.apply_findings(str(self.plan), [finding(task_id="M99.1")])
        self.assertEqual(self.plan.read_text(encoding="utf-8"), PLAN)

    def test_missing_m9_or_journal_section_fails_closed(self):
        from devsys import plan_writer

        self.plan.write_text("### M4 — Dashboard\n- [ ] M4.1 · X · nặng:1 · ⬜\n", encoding="utf-8")
        with self.assertRaises(plan_writer.PlanWriterError):
            plan_writer.apply_findings(str(self.plan), [finding()])
        self.assertEqual(self.plan.read_text(encoding="utf-8"), "### M4 — Dashboard\n- [ ] M4.1 · X · nặng:1 · ⬜\n")


if __name__ == "__main__":
    unittest.main()
