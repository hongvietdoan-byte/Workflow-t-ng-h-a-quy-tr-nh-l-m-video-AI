"""S14.45: bảng chấm hiệu quả quy trình nhiều phiên — devsys/workflow_runs.jsonl (trong git), parser dòng "Số đo:" của kế hoạch
(dòng không đọc được → liệt kê, không im lặng bỏ), CLI `python -m devsys.workflow add|list|import-plan`, trang devsys "Hiệu quả quy trình"."""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from devsys import workflow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chép nguyên văn các dòng việc thật trong docs/KE_HOACH_SUA_SAU_DU_AN_8.md (06/10), cắt bớt phần giữa không liên quan.
REAL = {
    "S14.5": "- [x] S14.5 · C2 — `ff_site` an toàn · nặng:2 · ✅ · 86d14d2 · 06/10: trang chỉ `https://ff.garena.com:443`. "
             "Số đo: làm ≈ 158k + sửa ≈ 235k, rà ≈ 115k",
    "S14.7": "- [x] S14.7 · D1 — quyền · nặng:2 · ✅ · fc0e96f · 05/10: thử thật mạng công ty. Số đo: làm ≈ 252 nghìn token, "
             "rà ≈ 123 nghìn (≈ 33 %), rà bắt 3 lỗi. Mở: chưa thử thật DASHBOARD_LAN=1 từ máy đồng nghiệp",
    "S14.9": "- [x] S14.9 · L — dọn cờ đợt 1 · nặng:1 · ✅ · 580c47e · 06/10: bỏ hẳn 5 cờ. "
             "Số đo: làm ≈ 300k + thêm ≈ 361k (đánh thức lại — context lớn)",
    "S14.18": "- [x] S14.18 · Giới hạn theo người · nặng:2 · ✅ · efc4b1b · 05/10: xong. "
              "Số đo: làm ≈ 233k + sửa ≈ 257k token, rà ≈ 138k (≈ 28 %), rà bắt 5 lỗi",
    "S14.20": "- [x] S14.20 · Bộ não prompt — Đợt 2 · nặng:2 · ✅ · a16c7c6 · 05/10: xong. Số đo: làm ≈ 200 nghìn token, rà 0 phiên riêng, "
              "lỗi bắt được 1 (cả bộ test). Mở: nghiệm thu cần Claude thật",
    "S14.27": "- [x] S14.27 · AI Dev System: ô trả lời · nặng:2 · ✅ · 1b3fe7f · 05/10: xong. Số đo: làm ≈ 125k token, rà 0.",
    "S14.32": "- [x] S14.32 · Phân tích kênh TikTok · nặng:2 · ✅ · 05/10 · Đợt 1 xong. Số đo: ≈ 343k token (1 phiên làm, rà nhẹ). Đợt 2 chỉ khi cần",
    "S14.43": "- [x] S14.43 · Biên kịch theo chấm phiếu 05d · nặng:3 · ✅ · 357434f + 599606b · 06/10 · xong. "
              "Số đo: A làm ≈ 276k + sửa ≈ 620k, rà ≈ 130k; B làm ≈ 171k + sửa ≈ 233k, rà ≈ 149k",
    "S14.44": "- [x] S14.44 · Dữ liệu cũ `plate_mode` · nặng:1 · ✅ · df8fdfa · 06/10: giữ đọc. Số đo: làm ≈ 101k (việc nhỏ, rà nhẹ)",
}


class ParseMeasureTests(unittest.TestCase):
    def _one(self, tid):
        got = workflow.parse_plan(REAL[tid])
        self.assertEqual(got["bad"], [], got["bad"])
        return got["runs"]

    def test_work_fix_review_with_k(self):
        (r,) = self._one("S14.5")
        self.assertEqual((r["task"], r["work_k"], r["fix_k"], r["review_k"], r["fix_rounds"], r["review"]), ("S14.5", 158, 235, 115, 1, "ky"))
        self.assertEqual((r["date"][5:], r["commit"]), ("10-06", "86d14d2"))

    def test_nghin_unit_and_bugs_and_note_cut(self):
        (r,) = self._one("S14.7")
        self.assertEqual((r["work_k"], r["review_k"], r["fix_k"], r["bugs"], r["fix_rounds"]), (252, 123, 0, 3, 0))
        self.assertNotIn("DASHBOARD_LAN", r["note"])                                  # phần "Mở: …" sau số đo không lẫn vào

    def test_them_wakeup_counts_as_fix_round(self):
        (r,) = self._one("S14.9")
        self.assertEqual((r["work_k"], r["fix_k"], r["fix_rounds"]), (300, 361, 1))
        self.assertIn("thêm", r["note"])
        self.assertIsNone(r["review_k"])                                               # không ghi rà = không biết, không đoán 0
        self.assertIsNone(r["review"])

    def test_sua_with_token_word(self):
        (r,) = self._one("S14.18")
        self.assertEqual((r["work_k"], r["fix_k"], r["review_k"], r["bugs"]), (233, 257, 138, 5))

    def test_ra_zero_is_light_review_and_bugs_other_wording(self):
        (r,) = self._one("S14.20")
        self.assertEqual((r["work_k"], r["review_k"], r["review"], r["bugs"]), (200, 0, "nhe", 1))
        (r,) = self._one("S14.27")
        self.assertEqual((r["work_k"], r["review_k"], r["review"], r["bugs"]), (125, 0, "nhe", None))

    def test_bare_total_and_ra_nhe_text(self):
        (r,) = self._one("S14.32")
        self.assertEqual((r["work_k"], r["review"], r["date"][5:]), (343, "nhe", "10-05"))
        (r,) = self._one("S14.44")
        self.assertEqual((r["work_k"], r["review"]), (101, "nhe"))

    def test_two_labelled_branches_on_one_line(self):
        a, b = self._one("S14.43")
        self.assertEqual((a["task"], a["part"], a["work_k"], a["fix_k"], a["review_k"]), ("S14.43", "A", 276, 620, 130))
        self.assertEqual((b["part"], b["work_k"], b["fix_k"], b["review_k"]), ("B", 171, 233, 149))
        self.assertEqual(a["commit"], "357434f")

    def test_unreadable_measure_is_listed_not_dropped(self):
        got = workflow.parse_plan("- [x] S9.1 · thử · nặng:1 · ✅ · abc1234 · 05/10: x. Số đo: chưa ghi kịp\n"
                                  "- [x] S9.2 · thử · nặng:1 · ✅ · abc1235 · 05/10: x. Số đo: làm ≈ 300 token\n")
        self.assertEqual(got["runs"], [])
        self.assertEqual(len(got["bad"]), 2)
        self.assertIn("S9.1", got["bad"][0])
        self.assertIn("S9.2", got["bad"][1])                                          # số token không có đơn vị k/nghìn → không đoán

    def test_unfinished_task_and_prose_are_reported_as_skipped(self):
        got = workflow.parse_plan("- [ ] S14.45 · nhập lại từ các dòng 'Số đo:' trong kế hoạch · nặng:2 · ⬜\n"
                                  "| S0.7 | Số đo thành **chỉ số mục tiêu** |\n")
        self.assertEqual((got["runs"], got["bad"]), ([], []))
        self.assertEqual(len(got["skipped"]), 1)
        self.assertIn("S14.45", got["skipped"][0])

    def test_real_plan_file_has_no_unreadable_measure(self):
        path = os.path.join(ROOT, "docs", "KE_HOACH_SUA_SAU_DU_AN_8.md")
        if not os.path.exists(path):
            self.skipTest("chưa có file kế hoạch")
        with open(path, encoding="utf-8") as f:
            got = workflow.parse_plan(f.read())
        self.assertEqual(got["bad"], [])
        self.assertGreaterEqual(len(got["runs"]), 18)


class StoreAndCliTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "sub", "workflow_runs.jsonl")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = workflow.main(list(args) + ["--file", self.path])
        return code, out.getvalue(), err.getvalue()

    def test_missing_file_is_empty(self):
        self.assertEqual(workflow.load(self.path), [])

    def test_add_validates_and_list_shows(self):
        code, out, _ = self._cli("add", "S14.45", "--date", "2026-10-06", "--mode", "cloud", "--review", "nhe", "--work", "150",
                                 "--review-k", "0", "--fix", "20", "--rounds", "1", "--bugs", "2", "--major", "1", "--note", "thử")
        self.assertEqual(code, 0, out)
        rows = workflow.load(self.path)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["task"], r["mode"], r["review"], r["work_k"], r["fix_k"], r["fix_rounds"], r["bugs"], r["bugs_major"], r["source"]),
                         ("S14.45", "cloud", "nhe", 150, 20, 1, 2, 1, "cli"))
        code, out, _ = self._cli("list")
        self.assertEqual(code, 0)
        self.assertIn("S14.45", out)
        self.assertIn("170", out)                                                     # tổng = làm + rà + sửa

    def test_add_rejects_bad_enum_negative_and_duplicate(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self._cli("add", "S14.45", "--mode", "free", "--review", "nhe", "--work", "1")
        code, _, err = self._cli("add", "S14.45", "--mode", "goi", "--review", "nhe", "--work", "-5")
        self.assertNotEqual(code, 0)
        self.assertIn("âm", err)
        self.assertEqual(self._cli("add", "S14.45", "--mode", "goi", "--review", "nhe", "--work", "5")[0], 0)
        code, _, err = self._cli("add", "S14.45", "--mode", "goi", "--review", "nhe", "--work", "6")
        self.assertNotEqual(code, 0)
        self.assertIn("đã có", err)
        self.assertEqual(len(workflow.load(self.path)), 1)

    def test_broken_file_is_reported_not_overwritten(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('{"task": "S1.1", "work_k": 1}\nkhông phải json\n')
        with self.assertRaises(workflow.WorkflowError):
            workflow.load(self.path)
        code, _, err = self._cli("add", "S14.45", "--mode", "goi", "--review", "nhe", "--work", "5")
        self.assertNotEqual(code, 0)
        self.assertIn("dòng 2", err)
        with open(self.path, encoding="utf-8") as f:
            self.assertIn("không phải json", f.read())

    def test_import_plan_writes_once_and_lists_bad_lines(self):
        plan = os.path.join(self.dir, "plan.md")
        with open(plan, "w", encoding="utf-8") as f:
            f.write("\n".join([REAL["S14.5"], REAL["S14.43"], "- [x] S9.1 · thử · nặng:1 · ✅ · abc1234 · 05/10: x. Số đo: chưa ghi"]) + "\n")
        code, out, _ = self._cli("import-plan", "--plan", plan)                           # mặc định chỉ xem, không ghi
        self.assertEqual(code, 0)
        self.assertIn("S9.1", out)
        self.assertEqual(workflow.load(self.path), [])
        self.assertEqual(self._cli("import-plan", "--plan", plan, "--write")[0], 0)
        self.assertEqual(len(workflow.load(self.path)), 3)
        self.assertEqual(self._cli("import-plan", "--plan", plan, "--write")[0], 0)       # chạy lại không nhân đôi
        rows = workflow.load(self.path)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["source"].startswith("plan:") and r["mode"] == "goi" for r in rows))
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(len([json.loads(x) for x in f if x.strip()]), 3)


class SummaryTests(unittest.TestCase):
    RUNS = [
        {"task": "S1", "date": "2026-10-05", "mode": "goi", "review": "ky", "work_k": 200, "review_k": 100, "fix_k": 100, "fix_rounds": 1, "bugs": 4},
        {"task": "S2", "date": "2026-10-05", "mode": "goi", "review": "ky", "work_k": 300, "review_k": 100, "fix_k": 0, "fix_rounds": 0, "bugs": 1},
        {"task": "S3", "date": "2026-10-06", "mode": "cloud", "review": "nhe", "work_k": 120, "review_k": 0, "fix_k": 0, "fix_rounds": 0, "bugs": None},
        {"task": "S4", "date": "2026-10-06", "mode": "goi", "review": None, "work_k": 182, "review_k": None, "fix_k": 0, "fix_rounds": 0, "bugs": None},
    ]

    def test_metrics_by_review_level_date_and_mode(self):
        s = workflow.summarize(self.RUNS)
        ky = s["by_review"]["ky"]
        self.assertEqual((ky["n"], ky["total_k"], ky["per_branch_k"]), (2, 800, 400))
        self.assertAlmostEqual(ky["pct_review"], 25.0)
        self.assertAlmostEqual(ky["pct_fix"], 12.5)
        self.assertAlmostEqual(ky["review_per_bug_k"], 40.0)
        self.assertAlmostEqual(ky["bugs_per_branch"], 2.5)
        self.assertAlmostEqual(ky["fix_rounds_per_branch"], 0.5)
        self.assertEqual(s["by_review"]["nhe"]["per_branch_k"], 120)
        self.assertEqual(s["by_review"]["?"]["n"], 1)                                # mức rà không rõ → nhóm riêng, không gộp nhầm
        self.assertEqual(s["by_date"]["2026-10-06"]["n"], 2)
        self.assertEqual(s["by_mode"]["cloud"]["total_k"], 120)
        self.assertEqual(s["all"]["n"], 4)

    def test_compare_has_both_baselines(self):
        rows = workflow.compare(workflow.summarize(self.RUNS))
        names = [r["Chỉ số"] for r in rows]
        self.assertIn("Token/nhánh rà kỹ (nghìn)", names)
        self.assertIn("% rà (rà kỹ)", names)
        row = next(r for r in rows if r["Chỉ số"] == "Token/nhánh rà kỹ (nghìn)")
        self.assertEqual((row["Hiện tại"], row["Mốc B 05–06/10"]), (400, 653))
        self.assertEqual(workflow.BASELINES["A"]["per_branch_k"], 443)

    def test_repo_file_loads_and_matches_plan_import(self):
        if not os.path.exists(workflow.RUNS_FILE):
            self.skipTest("chưa có devsys/workflow_runs.jsonl")
        rows = workflow.load(workflow.RUNS_FILE)
        self.assertGreaterEqual(len(rows), 18)
        self.assertTrue(all(r["mode"] in workflow.MODES for r in rows))


class PageTests(unittest.TestCase):
    def test_page_renders_table_baselines_and_bad_lines(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:  # pragma: no cover
            self.skipTest("streamlit.testing không có")
        d = tempfile.mkdtemp()
        try:
            runs = os.path.join(d, "runs.jsonl")
            with open(runs, "w", encoding="utf-8") as f:
                for r in SummaryTests.RUNS:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            plan = os.path.join(d, "plan.md")
            with open(plan, "w", encoding="utf-8") as f:
                f.write("### S9 — Thử\n- [x] S9.1 · thử · nặng:1 · ✅ · abc1234 · 05/10: x. Số đo: chưa ghi\n")
            from devsys import plan_progress
            at = AppTest.from_file(os.path.join(ROOT, "devsys", "app.py"), default_timeout=180)
            with mock.patch.dict(os.environ, {"DEVSYS_WORKFLOW_FILE": runs}), mock.patch.object(plan_progress, "PLAN_FILE", plan):
                at.run()
                at.sidebar.radio[0].set_value("Hiệu quả quy trình").run()
            self.assertEqual([e.value for e in at.exception], [])
            self.assertEqual(at.title[0].value[:18], "Hiệu quả quy trình")
            text = " ".join(m.value for m in at.markdown) + " ".join(str(w.value) for w in at.warning)
            self.assertIn("S9.1", text)                                               # dòng không đọc được hiện ra
            frames = [df.value for df in at.dataframe]
            joined = " ".join(" ".join(map(str, f.columns)) + " " + f.to_string() for f in frames)
            self.assertIn("Mốc A 04–05/10", joined)
            self.assertIn("Mốc B 05–06/10", joined)
            self.assertIn("S3", joined)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
