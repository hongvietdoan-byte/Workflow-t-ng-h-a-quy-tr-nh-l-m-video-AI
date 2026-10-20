"""V3.1 M0.8: sơ đồ tiến độ vẽ từ file kế hoạch + sổ khâu + bảng việc↔khâu — màu đi theo trạng thái việc, việc chưa gắn khâu bị báo."""
import json
import os
import tempfile
import unittest

from devsys import plan_map, plan_progress

PLAN = """### M0 — Nền
- [x] M0.1 · Audit · nặng:1 · ✅ · abc1234 · biên bản
- [ ] M0.2 · Sổ lỗi · nặng:2 · 🔄
### M1 — Tiền
- [ ] M1.1 · Parser · nặng:1 · ⏸
- [ ] M1.2 · Chưa gắn · nặng:1 · ⬜
"""
ROWS = [{"id": "L8", "ten": "Gói ảnh", "thieu": True, "tu_do": False}, {"id": "L9", "ten": "Gen ảnh", "thieu": False, "tu_do": True}]


class PlanMapTests(unittest.TestCase):
    def setUp(self):
        self.plan = plan_progress.parse(PLAN)
        self.m = plan_map.model(self.plan, ROWS, {"M0.1": ["NEN"], "M0.2": ["NEN", "L8"], "M1.1": ["L9"], "X9.9": ["L9"]}, {"L8": 2})

    def test_unmapped_and_stale_tasks_are_reported(self):
        self.assertEqual(self.m["unmapped"], ["M1.2"])
        self.assertEqual(self.m["stale"], ["X9.9"])

    def test_stage_rows_follow_task_status_and_check_state(self):
        rows = {r["id"]: r for r in self.m["rows"]}
        self.assertEqual(rows["L8"]["kind"], "thieu")
        self.assertEqual(rows["L9"]["kind"], "tu_do")
        self.assertEqual([t["id"] for t in rows["NEN"]["tasks"]], ["M0.1", "M0.2"])
        self.assertEqual(rows["NEN"]["done"], 1)
        self.assertEqual(rows["L8"]["open_errors"], 2)
        self.assertEqual(rows["L9"]["open_errors"], 0)

    def test_svg_colours_each_task_by_status(self):
        svg = plan_map.roadmap_svg(self.m, "t")
        self.assertIn(plan_map.STATUS_COLOR["✅"], svg)
        self.assertIn(plan_map.STATUS_COLOR["🔄"], svg)
        self.assertIn(plan_map.STATUS_COLOR["⏸"], svg)
        self.assertIn("abc1234", svg)
        self.assertTrue(plan_map.stages_svg(self.m, "t").startswith("<svg"))

    def test_open_errors_skip_verified_and_wont_fix(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "errors.json")
            with open(path, "w", encoding="utf-8") as f:
                from devsys.errors import FIELDS
                def row(i, stage, status):
                    it = dict.fromkeys(FIELDS)
                    it.update(id=f'P31-G{i}', alias=[], source_document='fixture', stage=stage,
                              status=status, severity='cao', plan_workstream='WS1',
                              fix_commit='abc', tests=['t'], real_run_evidence=['run'], status_reason='lý do')
                    return it
                json.dump({'schema_version': 1, 'items': [row(1, 'L8', 'OPEN'), row(2, 'L8', 'VERIFIED'),
                                                         row(3, 'L9', 'WONT_FIX'), row(4, None, 'OPEN')]}, f)
            self.assertEqual(plan_map.open_errors_by_stage(path), {"L8": 1, "NEN": 1})
        self.assertIsNone(plan_map.open_errors_by_stage(os.path.join(tempfile.gettempdir(), "khong_co_errors.json")))

    def test_real_plan_and_map_agree(self):
        m, a, b = plan_map.build()
        self.assertEqual(m["unmapped"], [], "việc trong kế hoạch chính chưa gắn khâu ở devsys/plan_map.json")
        self.assertEqual(m["stale"], [])
        self.assertEqual(m["unknown_stage"], [])
        self.assertTrue(a.startswith("<svg") and b.startswith("<svg"))

    def test_unknown_stage_code_is_reported(self):
        m = plan_map.model(self.plan, ROWS, {"M0.1": ["L99"], "M0.2": ["L8"], "M1.1": ["L9"], "M1.2": ["L9"]})
        self.assertEqual(m["unknown_stage"], ["M0.1→L99"])

    def test_title_with_markup_is_escaped(self):
        plan = plan_progress.parse("### M0 — x\n- [ ] M0.1 · <script>&a · nặng:1 · ⬜\n")
        svg = plan_map.roadmap_svg(plan_map.model(plan, ROWS, {"M0.1": ["L8"]}), "<t>")
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;&amp;a", svg)

    def test_empty_plan_and_bad_errors_file(self):
        empty = plan_map.model({"waves": [], "bad": [], "cap": None, "focus": None}, ROWS, {})
        self.assertTrue(plan_map.roadmap_svg(empty, "t").startswith("<svg"))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "errors.json")
            for bad in ({"errors": ["x"]}, {"errors": [{"id": "a", "stage": [["L8"]], "status": "OPEN"}]}, ["x"]):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(bad, f)
                with self.assertRaises(ValueError):
                    plan_map.open_errors_by_stage(path)


if __name__ == "__main__":
    unittest.main()
