"""AI Development System — thang chấm bản 2 (2026-10-03): mức nghiêm trọng do code gán điểm, khoản trừ tự động do code đo (ast), checklist lỗi đã
gặp, độ ổn định giữa các lần chấm, số đo giao diện thật, so thang cũ ↔ mới, báo cáo hành động. Điểm bản 1 vẫn đọc được."""
import contextlib
import io
import json
import os
import tempfile
import textwrap
import unittest
from unittest import mock

from core.adapters.http import HttpResponse
from core.db import connect
from devsys import collect, metrics, scorer, scores
from tests import test_devsys as base
from tests.test_devsys import AREAS, _mini_repo, _write

ROOT = collect.ROOT
FIX = {"why": "ảnh hưởng tới người dùng", "fix": "Sửa ở core/voice.py hàm speak", "files": ["core/voice.py"], "verify": "test mới", "effort": "💻",
       "priority": 1}


def tearDownModule():
    base.tearDownModule()


def _a2(area, **over):
    crit = {k: {"deductions": [], "evidence_for": []} for k in scores.CRITERIA_MAX_V2}
    crit.update(over)
    return {"format": scores.FORMAT_V2, "area": area, "criteria": crit, "summary": "ổn", "can_kiem_lai": [],
            "checklist": {k: {"tra_loi": "khong", "ghi_chu": "đã đọc core/voice.py"} for k in scores.CHECKLIST_IDS}}


def _ded(muc, reason="lỗi", evidence=("core/voice.py:6",), feedback=FIX, **kw):
    d = {"muc": muc, "reason": reason, "evidence": list(evidence), **kw}
    if feedback is not None:
        d["feedback"] = feedback
    return d


FULL = {"test_files": 1, "has_run": True, "failed": 0}
REAL_RUN = {"evidence_for": ["TODO.md:3"]}


class RubricV2Tests(unittest.TestCase):
    def test_criteria_sum_to_100_and_the_rubric_names_everything_code_enforces(self):
        self.assertEqual(sum(scores.CRITERIA_MAX_V2.values()), 100)
        self.assertEqual(sum(scores.CRITERIA_MAX.values()), 100)                  # bản 1 untouched
        text = open(os.path.join(ROOT, "devsys", "rubric.md"), encoding="utf-8").read()
        self.assertIn("Thang chấm cố định", text)
        for k in scores.CRITERIA_MAX_V2:
            self.assertIn(f"`{k}`", text)
        for k in scores.CHECKLIST_IDS:
            self.assertIn(k, text)
        for rule in metrics.RULES:
            self.assertIn(f"`{rule}`", text, f"luật tự động {rule} phải được liệt kê trong thang")
        self.assertIn("devsys-score/2", text)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "devsys", "rubric_v1.md")))
        self.assertNotEqual(scores.rubric_hash(ROOT), "khong-co-rubric")

    def test_version_is_read_from_format_then_hint_then_shape(self):
        self.assertEqual(scores.version_of({"format": scores.FORMAT_V2}), 2)
        self.assertEqual(scores.version_of({"criteria": {"tin_cay": {}}}), 2)
        self.assertEqual(scores.version_of({"criteria": {"chuc_nang": {}}}), 1)
        self.assertEqual(scores.version_of({}, hint=scores.FORMAT_V2), 2)
        self.assertEqual(scores.version_of({"format": scores.FORMAT}, hint=scores.FORMAT_V2), 1)


class ScoreV2Tests(unittest.TestCase):
    def setUp(self):
        self.root = _mini_repo()
        self.ids = ["voice", "ui", "infra"]

    def norm(self, raw, facts=FULL, prev=None):
        return scores.normalize(raw, self.root, self.ids, facts, prev=prev)

    def test_points_come_from_the_severity_not_from_the_scorer(self):
        raw = _a2("voice", chuc_nang={"deductions": [_ded("lon", points=20)]}, bang_chung=REAL_RUN, test={"deductions": [_ded("nho", feedback=None)]})
        s = self.norm(raw)
        d = s["criteria"]["chuc_nang"]["deductions"][0]
        self.assertEqual((d["points"], d["muc"], d["claimed_points"]), (3.1, "lon", 20.0))     # 12 % of 26
        self.assertEqual(s["criteria"]["test"]["deductions"][0]["points"], 0.5)                # 4 % of 12
        self.assertEqual(s["format"], scores.FORMAT_V2)
        self.assertAlmostEqual(s["score"], 100 - 3.1 - 0.5, places=1)
        raw["score"] = 100
        self.assertAlmostEqual(self.norm(raw)["score"], 96.4, places=1)                        # a claimed total is still ignored
        for bad in ("nang", None, ""):
            with self.assertRaises(scores.ScoreError):
                self.norm(_a2("voice", chuc_nang={"deductions": [{"muc": bad, "reason": "x", "evidence": ["TODO.md:3"]}]}))

    def test_a_blocking_deduction_needs_provable_evidence_and_caps_the_area(self):
        soft = self.norm(_a2("voice", chuc_nang={"deductions": [_ded("chan", evidence=["absent:không thấy", "flag:lip_sync"])]}, bang_chung=REAL_RUN))
        d = soft["criteria"]["chuc_nang"]["deductions"][0]
        self.assertEqual((d["muc"], d["points"]), ("lon", 3.1))                                # nothing to open → treated as 'lớn'
        self.assertIn("hạ từ 'chặn'", d["note"])
        hard = self.norm(_a2("voice", chuc_nang={"deductions": [_ded("chan")]}, bang_chung=REAL_RUN))
        self.assertEqual(hard["criteria"]["chuc_nang"]["deductions"][0]["points"], 9.1)        # 35 % of 26
        self.assertEqual(hard["score"], 89.0)                                                  # 90.9 → capped at 89
        self.assertTrue(any("tối đa" in c or "giới hạn 89" in c for c in hard["code_caps"]))
        two = self.norm(_a2("voice", chuc_nang={"deductions": [_ded("chan")]}, tin_cay={"deductions": [_ded("chan", evidence=["test:tests/test_voice.py::T::t"])]},
                           bang_chung=REAL_RUN))
        self.assertEqual(two["severity"]["chan"], 2)
        self.assertEqual(two["score"], 79.0)                                                   # 100 - 9.1 - 4.2 = 86.7 → capped at 79

    def test_a_big_deduction_must_become_a_fix(self):
        with self.assertRaises(scores.ScoreError) as cm:
            self.norm(_a2("voice", chuc_nang={"deductions": [_ded("lon", feedback=None)]}))
        self.assertIn("feedback.fix", str(cm.exception))
        with self.assertRaises(scores.ScoreError):
            self.norm(_a2("voice", chuc_nang={"deductions": [_ded("chan", feedback={"fix": "ngắn", "effort": "💻"})]}))
        self.norm(_a2("voice", chuc_nang={"deductions": [_ded("nho", feedback=None)]}))        # small ones may go without

    def test_the_checklist_must_answer_every_known_bug_class(self):
        raw = _a2("voice")
        del raw["checklist"]["K3_rang_buoc_ben_ngoai"]
        with self.assertRaises(scores.ScoreError) as cm:
            self.norm(raw)
        self.assertIn("K3_rang_buoc_ben_ngoai", str(cm.exception))
        raw = _a2("voice")
        raw["checklist"]["K2_cong_do_sai"] = {"tra_loi": "co", "ghi_chu": "mẫu số sai ở core/effectiveness.py"}
        with self.assertRaises(scores.ScoreError) as cm:                                      # 'yes' without a deduction = a bug that is not a fix
            self.norm(raw)
        self.assertIn("K2_cong_do_sai", str(cm.exception))
        raw["criteria"]["tin_cay"]["deductions"].append(_ded("lon", loai="K2_cong_do_sai"))
        ok = self.norm(raw)
        self.assertEqual([c["khoan_tru"] for c in ok["checklist"] if c["id"] == "K2_cong_do_sai"], [1])
        raw["checklist"]["K1_khai_bao_chung"] = {"tra_loi": "chắc là không", "ghi_chu": "đã tìm kỹ rồi"}
        with self.assertRaises(scores.ScoreError):
            self.norm(raw)
        raw["checklist"]["K1_khai_bao_chung"] = {"tra_loi": "khong", "ghi_chu": "ừ"}
        with self.assertRaises(scores.ScoreError):                                            # 'no' must say where it looked
            self.norm(raw)
        bad = _a2("voice", chuc_nang={"deductions": [_ded("nho", loai="K99_khong_co", feedback=None)]})
        with self.assertRaises(scores.ScoreError):
            self.norm(bad)

    def test_automatic_deductions_are_applied_by_code_and_the_scorer_cannot_remove_them(self):
        auto = [{"criterion": "bao_tri", "points": 3.0, "rule": "file_dai", "reason": "3 file dài", "evidence": ["core/voice.py:1"], "count": 3},
                {"criterion": "tin_cay", "points": 4.0, "rule": "nuot_loi", "reason": "10 except nuốt lỗi", "evidence": ["core/voice.py:6"], "heuristic": False}]
        s = self.norm(_a2("voice", bang_chung=REAL_RUN), {**FULL, "auto": auto})
        self.assertEqual(s["criteria"]["bao_tri"]["score"], 5.0)
        self.assertEqual(s["criteria"]["tin_cay"]["score"], 8.0)
        ds = s["criteria"]["bao_tri"]["deductions"]
        self.assertTrue(ds[0]["auto"] and ds[0]["muc"] == "tu_dong" and ds[0]["loai"] == "file_dai")
        self.assertEqual(s["auto_points"], 7.0)
        self.assertEqual(s["score"], 93.0)

    def test_code_caps_for_tests_and_for_a_ui_area_without_a_real_measurement(self):
        s = self.norm(_a2("voice", bang_chung=REAL_RUN), {"test_files": 0, "has_run": False, "failed": 0})
        self.assertEqual(s["criteria"]["test"]["score"], 2.4)                                  # 3 of 15, scaled to a 12-point criterion
        s = self.norm(_a2("voice", bang_chung=REAL_RUN), {"test_files": 2, "has_run": False, "failed": 0})
        self.assertEqual(s["criteria"]["test"]["score"], 6.4)
        s = self.norm(_a2("voice", bang_chung=REAL_RUN), {"test_files": 2, "has_run": True, "failed": 1})
        self.assertEqual(s["criteria"]["test"]["score"], 5.6)
        s = self.norm(_a2("ui", bang_chung={"evidence_for": ["core/voice.py:2"]}), {**FULL, "ui_measured": True, "ui_present": False})
        self.assertEqual(s["criteria"]["bang_chung"]["score"], 0)                              # code is not a record of a real run
        self.assertEqual(s["criteria"]["trai_nghiem"]["score"], 6.0)
        s = self.norm(_a2("ui", bang_chung=REAL_RUN), {**FULL, "ui_measured": True, "ui_present": True})
        self.assertEqual(s["criteria"]["trai_nghiem"]["score"], 10)

    def test_a_score_far_from_the_previous_one_needs_an_explanation(self):
        prev = {"score": 100.0, "auto_points": 0.0, "rubric_hash": scores.rubric_hash(self.root), "format": scores.FORMAT_V2, "date": "2026-10-01"}
        big = _a2("voice", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon"), _ded("lon"), _ded("lon")]})         # −9.3
        with self.assertRaises(scores.ScoreError) as cm:
            self.norm(big, prev=prev)
        self.assertIn("giai_thich_chenh", str(cm.exception))
        big["giai_thich_chenh"] = [{"criterion": "chuc_nang", "why": "lần trước bỏ sót 3 hàm trống", "evidence": ["core/voice.py:6"]}]
        s = self.norm(big, prev=prev)
        self.assertTrue(s["drift"]["explained"])
        self.assertEqual((s["drift"]["prev_score"], s["drift"]["delta"]), (100.0, -9.3))
        small = self.norm(_a2("voice", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon")]}), prev=prev)             # −3.1: within the limit
        self.assertFalse(small["drift"]["explained"])
        other = dict(prev, rubric_hash="thang-khac")
        self.assertNotIn("drift", self.norm(big, prev=other))                                  # a different rubric is not comparable
        # automatic deductions do not count as the scorer drifting
        auto = [{"criterion": "bao_tri", "points": 3.0, "rule": "file_dai", "reason": "x", "evidence": ["core/voice.py:1"]}]
        self.norm(_a2("voice", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon")]}), {**FULL, "auto": auto},
                  prev=dict(prev, score=100.0))

    def test_old_and_new_files_load_together_and_old_scores_keep_their_numbers(self):
        old = {"format": scores.FORMAT, "rubric_hash": "thang-cu", "scorer": "claude-code-session", "date": "2026-10-01T10:00:00+07:00",
               "facts": FULL, **base._answer("voice", chuc_nang={"deductions": [{"points": 5, "reason": "x", "evidence": ["TODO.md:3"]}]},
                                               bang_chung={"deductions": [], "evidence_for": ["TODO.md:3"]})}
        scores.save(old, self.root)
        new = {"rubric_hash": scores.rubric_hash(self.root), "scorer": "claude-code-session", "date": "2026-10-03T10:00:00+07:00", "facts": FULL,
               "raw": _a2("voice", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon")]}),
               **self.norm(_a2("voice", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon")]}))}
        scores.save(new, self.root)
        loaded, problems = scores.load_all(self.root, self.ids)
        self.assertEqual(problems, [])
        self.assertEqual([s["format"] for s in loaded], [scores.FORMAT, scores.FORMAT_V2])
        self.assertEqual(loaded[0]["score"], 95.0)                                            # 100 − 5, exactly as bản 1 computed it
        self.assertAlmostEqual(loaded[1]["score"], 96.9, places=1)
        self.assertEqual(scores.criteria_of(loaded[0]), scores.CRITERIA)
        self.assertEqual(scores.criteria_of(loaded[1]), scores.CRITERIA_V2)
        self.assertNotEqual(loaded[0]["rubric_hash"], scores.rubric_hash(self.root))           # the old score shows as 'khác thang'
        rows = scores.compare_rounds(scores.latest_by_area(loaded[:1]), scores.latest_by_area(loaded[1:]), AREAS)
        voice = [r for r in rows if r["area"] == "voice"][0]
        self.assertEqual((voice["old"], voice["delta"]), (95.0, 1.9))
        self.assertEqual(voice["criteria"]["chuc_nang"], {"old_pct": 83, "new_pct": 88})
        self.assertIn("tin_cay", voice["only_new"])


class MetricsTests(unittest.TestCase):
    def test_swallowed_excepts_only_flags_broad_handlers_that_do_nothing(self):
        import ast
        src = textwrap.dedent('''
            def f():
                try:
                    a()
                except Exception:
                    pass
                try:
                    a()
                except:
                    return None
                try:
                    a()
                except Exception as e:
                    log(e)
                try:
                    a()
                except Exception:
                    raise
                try:
                    a()
                except (OSError, ValueError):
                    pass
                for x in y:
                    try:
                        a()
                    except Exception:
                        continue
            ''')
        self.assertEqual(metrics.swallowed_excepts(ast.parse(src)), [5, 9, 26])

    def test_long_complex_paid_and_controls_are_measured_by_ast(self):
        import ast
        body = "\n".join("    x = 1" for _ in range(metrics.LONG_FUNC_LINES + 5))
        branches = "\n".join(f"    if a == {i}:\n        b = {i}" for i in range(metrics.COMPLEX_FUNC + 2))
        src = f"def long_one():\n{body}\n\ndef many():\n{branches}\n"
        long_, cx = metrics.long_and_complex(ast.parse(src))
        self.assertEqual([n for _, n, _ in long_], ["long_one"])
        self.assertEqual([n for _, n, _ in cx], ["many"])
        paid = textwrap.dedent('''
            def guarded(p, conn):
                budget.check_video(conn)
                return p.submit(1)
            def naked(p):
                return p.submit(1)
            def pool_ok(pool):
                return pool.submit(fetch, 1)
            def music(p):
                return p.generate_music("x")
            ''')
        found = metrics.paid_call_sites(ast.parse(paid), paid)
        self.assertEqual([(f["function"], f["call"]) for f in found], [("naked", "submit"), ("music", "generate_music")])
        ui = ast.parse("st.button('a')\nc.selectbox('b', [])\nst.write('x')\nwith st.expander('e'):\n    st.checkbox('c')\n")
        self.assertEqual(metrics.controls_in(ui), 4)
        self.assertEqual(metrics.public_functions(ast.parse("def a(): pass\ndef _b(): pass\nclass C:\n    def m(self): pass\n    def __init__(self): pass\n")), ["a", "m"])

    def _repo_with(self, voice_src, ui_area=False):
        root = _mini_repo()
        _write(root, "core/voice.py", voice_src)
        cfg = collect.load_areas(os.path.join(root, "devsys", "areas.json"))
        if ui_area:
            cfg["areas"][1]["ui_metrics"] = True
        snap = collect.collect(root, cfg, db_path=os.path.join(root, "khong_co.sqlite"))
        return root, cfg, snap

    def test_area_metrics_and_automatic_deductions_have_verifiable_evidence_and_caps(self):
        swallow = "\n".join("    try:\n        a()\n    except Exception:\n        pass" for _ in range(12))
        src = f'"""Giọng."""\n\n\ndef speak(text):\n{swallow}\n    return text\n'
        root, cfg, snap = self._repo_with(src)
        area = collect.area_by_id(cfg)["voice"]
        m = metrics.area_metrics(root, cfg, area, snap)
        self.assertEqual(len(m["swallowed"]), 12)
        self.assertEqual(m["modules_untested"], [])                                            # tests/test_voice.py imports core/voice.py
        self.assertEqual(m["code_files"], 1)
        auto = metrics.auto_deductions(m)
        sw = [a for a in auto if a["rule"] == "nuot_loi"][0]
        self.assertEqual((sw["criterion"], sw["points"]), ("tin_cay", 4.0))                    # 12 × 0.4 = 4.8 → capped at 4
        self.assertEqual(sw["count"], 12)
        for a in auto:
            for ev in a["evidence"]:
                self.assertIsNone(scores.check_evidence(ev, root, None), f"{a['rule']}: {ev}")
        self.assertTrue(all(0 < a["points"] <= metrics.RULES[a["rule"]][2] for a in auto))
        f = metrics.facts_extra(root, cfg, area, snap)
        self.assertEqual(set(f), {"metrics", "auto", "ui_measured", "ui_present", "ui"})
        json.dumps(f)                                                                          # stored in the score file

    def test_a_module_no_test_imports_costs_points(self):
        root, cfg, snap = self._repo_with('def speak(t):\n    return t\n')
        os.remove(os.path.join(root, "tests", "test_voice.py"))
        snap = collect.collect(root, cfg, db_path=os.path.join(root, "khong_co.sqlite"))
        m = metrics.area_metrics(root, cfg, collect.area_by_id(cfg)["voice"], snap)
        self.assertEqual(m["modules_untested"], ["core/voice.py"])
        rules = {a["rule"]: a for a in metrics.auto_deductions(m)}
        self.assertEqual(rules["module_khong_test"]["points"], 0.6)
        self.assertEqual(rules["module_khong_test"]["criterion"], "test")

    def test_ui_numbers_are_read_from_the_acceptance_and_contrast_output(self):
        acc = ("CLICK Dự án mới → video đầu: cũ 9 · v2 7 (nhập liệu 3 / 3) · video job cũ 1 v2 1\n"
               "KHÓA TĨNH (mã nguồn, mẫu key=): cũ 10 · mới 12 · mất ['a_key']\n"
               "   màn Storyboard              cũ   30 · v2   31 · mất trong v2 []\n"
               "PERF home_50       wall-min cũ 0.100s · v2 0.112s · +12.0 % | cpu-min cũ 0.1s · v2 0.1s · +5.0 % | SQL cũ 4 câu/1.0 ms · v2 5 câu/1.1 ms  ĐẠT\n"
               "PERF storyboard_30 wall-min cũ 0.500s · v2 0.650s · +30.0 % | cpu-min cũ 0.5s · v2 0.6s · +20.0 % | SQL cũ 4 câu/1.0 ms · v2 5 câu/1.1 ms  VƯỢT\n")
        con = "Màn Storyboard | chữ<4.5: 2 | chữ<12.5px: 1\nHộp ⚙ | chữ<4.5: 0 | chữ<12.5px: 3\n"
        ui = metrics.ui_from_text(acc, con, "thử")
        self.assertEqual((ui["clicks_old"], ui["clicks_v2"], ui["perf_worst_pct"], ui["keys_lost"]), (9, 7, 30.0, 1))
        self.assertEqual((ui["contrast_fail"], ui["small_text"], ui["zones"]), (2, 4, 2))
        only_acc = metrics.ui_from_text(acc)
        self.assertIsNone(only_acc["contrast_fail"])

    def test_keys_renamed_on_purpose_are_not_counted_as_lost(self):
        """S14.8 U8: keys_lost chỉ đếm khóa mất KHÔNG có lý do trong RENAMED (tools/ui_v2_acceptance.py) — cả bản in cũ lẫn mới."""
        old_print = "   màn Storyboard   cũ   30 · v2   31 · mất trong v2 ['retry_5', 'fold_refs_3_btn', 'lạ_1']\n"
        self.assertEqual(metrics.ui_from_text(old_print)["keys_lost"], 1)
        new_print = "   màn Storyboard   cũ   30 · v2   31 · mất trong v2 [] · đổi có chủ ý ['retry_5']\n"
        self.assertEqual(metrics.ui_from_text(new_print)["keys_lost"], 0)

    def test_real_ui_measurement_replaces_the_cap_and_adds_deductions(self):
        from tools import devsys_ui_metrics
        root, cfg, snap = self._repo_with('def speak(t):\n    return t\n', ui_area=True)
        ui_area = collect.area_by_id(cfg)["ui"]
        f = metrics.facts_extra(root, cfg, ui_area, snap)
        self.assertEqual((f["ui_measured"], f["ui_present"]), (True, False))
        self.assertFalse([a for a in f["auto"] if a["rule"] in ("tuong_phan", "chu_nho")])
        # only the second measurement (contrast) arrives later: the first (clicks) is kept
        devsys_ui_metrics.save(root, "CLICK x: cũ 5 · v2 6 (nhập liệu 1 / 1)\nPERF a wall-min cũ 1s · v2 2s · +100.0 % | x", "", "acceptance")
        devsys_ui_metrics.save(root, "", "Màn A | chữ<4.5: 6 | chữ<12.5px: 2\n", "contrast")
        f = metrics.facts_extra(root, cfg, ui_area, snap)
        self.assertTrue(f["ui_present"])
        rules = {a["rule"]: a for a in f["auto"]}
        self.assertEqual(rules["tuong_phan"]["points"], 0.6)
        self.assertEqual(rules["chu_nho"]["points"], 0.1)
        self.assertEqual(rules["ui_nhieu_click"]["points"], 1.0)                               # 6 clicks in v2 against 5
        self.assertEqual(rules["ui_cham"]["points"], 1.0)
        for a in f["auto"]:
            for ev in a["evidence"]:
                self.assertIsNone(scores.check_evidence(ev, root, None))
        s = scores.normalize(_a2("ui", bang_chung=REAL_RUN), root, ["voice", "ui", "infra"], {**FULL, **f})
        self.assertAlmostEqual(s["criteria"]["trai_nghiem"]["score"], 7.3, places=1)


class ScorerV2Tests(unittest.TestCase):
    def setUp(self):
        self.root = _mini_repo()
        self.cfg = collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))
        self.snap = collect.collect(self.root, self.cfg, db_path=os.path.join(self.root, "khong_co.sqlite"))
        self.health = collect.area_health(self.snap, self.cfg)
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        connect(self.db).close()

    def _transport(self, answers, calls):
        def send(method, url, headers, body, timeout):
            payload = json.loads(body)
            calls.append(payload)
            a = answers[min(len(calls) - 1, len(answers) - 1)]
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": json.dumps(a, ensure_ascii=False)}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": 6000, "output_tokens": 1500}}).encode())
        return send

    def test_the_bundle_carries_the_measures_the_checklist_and_the_v2_instructions(self):
        p = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice"], provider="mock")
        b = p["todo"][0]
        self.assertIn("Số đo do code tính", b["prompt"])
        self.assertIn("K2_cong_do_sai", b["prompt"])
        self.assertIn("không ghi số điểm", b["prompt"].lower().replace("**", ""))
        self.assertIn("devsys-score/2", b["prompt"])
        self.assertEqual(set(b["facts"]) >= {"test_files", "has_run", "failed", "metrics", "auto"}, True)
        self.assertIsNone(b["prev"])
        self.assertNotIn("hoàn hảo", b["prompt"])                                              # the commit message still never reaches the scorer

    def test_mock_run_saves_a_valid_bản_2_score(self):
        p = scorer.plan(self.root, self.cfg, self.snap, self.health, provider="mock")
        res = scorer.run(self.root, self.cfg, self.snap, p["todo"], "mock", yes=True, db_path=self.db, note=lambda m: None)
        self.assertEqual((len(res["saved"]), res["failed"]), (3, []))
        saved = json.load(open(res["saved"][0], encoding="utf-8"))
        self.assertEqual(saved["format"], scores.FORMAT_V2)
        self.assertIn("auto", saved["facts"])
        self.assertEqual(len(saved["checklist"]), 10)
        loaded, problems = scores.load_all(self.root, ["voice", "ui", "infra"])
        self.assertEqual(problems, [])
        self.assertTrue(all(0 < s["score"] <= 100 for s in loaded))

    def test_claude_answers_in_bản_2_are_scored_and_a_big_swing_is_asked_again_with_the_reason(self):
        first = _a2("voice", bang_chung=REAL_RUN)
        swing = _a2("voice", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon"), _ded("lon"), _ded("lon")]})
        explained = dict(swing, giai_thich_chenh=[{"criterion": "chuc_nang", "why": "lần trước bỏ sót 3 hàm trống", "evidence": ["core/voice.py:6"]}])
        env = {"ANTHROPIC_API_KEY": "sk-test-devsys", "ANTHROPIC_MODEL": "claude-sonnet-5"}
        calls = []
        p = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice"])
        with mock.patch.dict(os.environ, env):
            r1 = scorer.run(self.root, self.cfg, self.snap, p["todo"], "anthropic", yes=True, db_path=self.db, transport=self._transport([first], calls),
                            note=lambda m: None)
        self.assertEqual((len(calls), r1["failed"]), (1, []))
        s1 = json.load(open(r1["saved"][0], encoding="utf-8"))
        self.assertEqual((s1["format"], s1["scorer"]), (scores.FORMAT_V2, "claude-api"))
        self.assertNotIn("drift", s1)
        # the second scoring of the same area knows the first one and its deductions
        p2 = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice"])
        b = p2["todo"][0]
        self.assertEqual(b["prev"]["score"], s1["score"])
        self.assertIn("Lần trước:", b["prompt"])
        calls2 = []
        with mock.patch.dict(os.environ, env):
            r2 = scorer.run(self.root, self.cfg, self.snap, p2["todo"], "anthropic", yes=True, db_path=self.db,
                            transport=self._transport([swing, explained], calls2), note=lambda m: None)
        self.assertEqual((len(calls2), r2["failed"]), (2, []))                                 # refused once, then explained
        self.assertIn("Câu trả lời trước không hợp lệ", json.dumps(calls2[1], ensure_ascii=False))   # the retry tells the scorer what was wrong
        s2 = json.load(open(r2["saved"][0], encoding="utf-8"))
        self.assertTrue(s2["drift"]["explained"])
        loaded, _ = scores.load_all(self.root, ["voice", "ui", "infra"])
        self.assertEqual(len(loaded), 2)
        self.assertTrue([r for r in loaded if r.get("drift")][0]["drift"]["explained"])        # the drift survives a reload
        st = scores.stability(loaded)
        self.assertEqual(st["n"], 1)
        self.assertGreater(st["max_abs"], scores.DRIFT_LIMIT)

    def test_external_bản_2_score_is_imported_recomputed_and_exports_are_written(self):
        b = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice"], provider="mock")["todo"][0]
        path = scorer.export_bundle(self.root, b)
        text = open(path, encoding="utf-8").read()
        self.assertIn("checklist", text)
        raw = _a2("voice", chuc_nang={"deductions": [_ded("lon")]}, bang_chung=REAL_RUN)
        raw["score"] = 99
        out = scorer.import_score(self.root, self.cfg, self.snap, self.health, raw, "claude-code-session")
        rec = json.load(open(out, encoding="utf-8"))
        self.assertEqual(rec["format"], scores.FORMAT_V2)
        self.assertLess(rec["score"], 99)
        self.assertEqual(rec["rubric_hash"], scores.rubric_hash(self.root))
        with self.assertRaises(scores.ScoreError):                                             # a missing checklist is refused at import too
            bad = _a2("voice")
            del bad["checklist"]
            scorer.import_score(self.root, self.cfg, self.snap, self.health, bad, "claude-code-session")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.root = _mini_repo()
        self.ids = ["voice", "ui", "infra"]

    def rec(self, area, raw, scorer_name="s", date="2026-10-03T10:00:00+07:00", fp="f1", facts=FULL):
        n = scores.normalize(raw, self.root, self.ids, facts)
        return {**n, "scorer": scorer_name, "date": date, "fingerprint": fp, "rubric_hash": scores.rubric_hash(self.root), "commit": "abc"}

    def test_stability_counts_pairs_and_flags_noise_on_unchanged_code(self):
        a = self.rec("voice", _a2("voice", bang_chung=REAL_RUN), date="2026-10-01T10:00:00+07:00", fp="same")
        b = self.rec("voice", _a2("voice", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("nho", feedback=None)]}), date="2026-10-02T10:00:00+07:00", fp="same")
        c = self.rec("ui", _a2("ui", bang_chung=REAL_RUN), date="2026-10-02T11:00:00+07:00")
        mock_rec = dict(self.rec("voice", _a2("voice", bang_chung=REAL_RUN), date="2026-10-02T12:00:00+07:00"), scorer="mock")
        st = scores.stability([a, b, c, mock_rec])
        self.assertEqual((st["n"], st["over_limit"]), (1, 0))
        self.assertEqual(len(st["noise"]), 1)                                                  # moved −1 with the same fingerprint
        self.assertEqual(st["pairs"][0]["delta"], -1.0)
        self.assertEqual(scores.stability([])["n"], 0)

    def test_the_action_report_lists_why_what_who_and_in_which_order(self):
        raw = _a2("voice", bang_chung=REAL_RUN,
                  chuc_nang={"deductions": [_ded("nho", "chữ nhỏ", feedback=None), _ded("chan", "cổng sai", feedback=dict(FIX, priority=1))]},
                  tin_cay={"deductions": [_ded("lon", "nuốt lỗi", feedback={"fix": "Ghi diag trong core/voice.py", "effort": "💵", "priority": 2})]})
        raw["checklist"]["K8_im_lang"] = {"tra_loi": "co", "ghi_chu": "nuốt lỗi ở core/voice.py"}
        raw["criteria"]["tin_cay"]["deductions"][0]["loai"] = "K8_im_lang"
        facts = {**FULL, "auto": [{"criterion": "bao_tri", "points": 1.0, "rule": "file_dai", "reason": "1 file dài", "evidence": ["core/voice.py:1"]}]}
        voice = self.rec("voice", raw, facts=facts)
        ui = self.rec("ui", _a2("ui", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon", "cờ chưa thử", evidence=("flag:lip_sync",))]}))
        infra = self.rec("infra", _a2("infra", bang_chung=REAL_RUN, chuc_nang={"deductions": [_ded("lon", "cờ chưa thử", evidence=("flag:lip_sync",))]}))
        latest = {"voice": voice, "ui": ui, "infra": infra}
        text = scores.action_report(latest, AREAS)
        self.assertLess(text.index("cổng sai"), text.index("nuốt lỗi"))                         # blocker first
        self.assertLess(text.index("nuốt lỗi"), text.index("chữ nhỏ"))
        self.assertIn("Ai: cần chi tiền", text)
        self.assertIn("Claude Code (code miễn phí)", text)
        self.assertIn("K8_im_lang", text)
        self.assertIn("Khoản trừ tự động", text)
        self.assertIn("Một việc — nhiều khu vực", text)                                         # flag:lip_sync cited by ui and infra
        rec = scores.recurring(latest)
        self.assertEqual(rec[0]["evidence"], "flag:lip_sync")
        self.assertEqual(rec[0]["areas"], ["infra", "ui"])

    def test_cli_report_compare_and_stability_read_only_and_write_a_file(self):
        from tools import devsys_score
        out = io.StringIO()
        target = os.path.join(tempfile.mkdtemp(), "bao_cao.md")
        with contextlib.redirect_stdout(out):
            code = devsys_score.main(["--report", target, "--compare", "--stability"])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile(target))
        self.assertIn("Báo cáo hành động", open(target, encoding="utf-8").read())
        self.assertIn("Đã ghi báo cáo hành động", out.getvalue())

    def test_cli_exports_every_area_with_all(self):
        from tools import devsys_score
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(devsys_score, "ROOT", self.root), \
                mock.patch.object(devsys_score.collect, "load_areas", return_value=collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))):
            code = devsys_score.main(["--export", "all"])
        self.assertEqual(code, 0)
        for aid in self.ids:
            self.assertTrue(os.path.isfile(os.path.join(self.root, "devsys", "data", "exports", f"{aid}.md")))


class RealRepoMeasureTests(unittest.TestCase):
    def test_every_area_of_the_real_repo_can_be_measured_and_its_evidence_exists(self):
        cfg = collect.load_areas()
        snap = collect.collect(ROOT, cfg)
        seen = 0
        for a in cfg["areas"]:
            f = metrics.facts_extra(ROOT, cfg, a, snap)
            for d in f["auto"]:
                self.assertLessEqual(d["points"], metrics.RULES[d["rule"]][2] + 1e-9, f"{a['id']}.{d['rule']}")
                for ev in d["evidence"]:
                    self.assertIsNone(scores.check_evidence(ev, ROOT, None), f"{a['id']}.{d['rule']}: {ev}")
                    seen += 1
            json.dumps(f)
        self.assertGreater(seen, 20)
        self.assertTrue(collect.area_by_id(cfg)["dashboard_ui"].get("ui_metrics"))


if __name__ == "__main__":
    unittest.main()


class AppNameShadowTests(unittest.TestCase):
    def test_no_module_level_name_shadows_a_helper_function(self):
        """03/10: `stale = snap.get("tests_stale")` in the sidebar replaced the helper `stale(aid)` with None whenever the tests were fresh,
        so the 'Chấm điểm AI' page crashed with "'NoneType' object is not callable"."""
        import ast
        path = os.path.join(os.path.dirname(__file__), "..", "devsys", "app.py")
        tree = ast.parse(open(path, encoding="utf-8").read())
        funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        bound = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    bound |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)}
        # only assignments outside any function body count as module scope
        in_func = {id(x) for n in tree.body if isinstance(n, ast.FunctionDef) for x in ast.walk(n)}
        mod_bound = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and id(node) not in in_func:
                for t in node.targets:
                    mod_bound |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)}
        self.assertEqual(sorted(funcs & mod_bound), [])


class TodoLogLinesTests(unittest.TestCase):
    def test_done_log_entries_are_general_items_not_area_items(self):
        """03/10: "- **Đã chạy …**" / "- **Chấm lại …**" notes name files and flags and say "chưa …": tying them to the areas they mention flipped
        those areas' fingerprint (a false 'đã đổi, nên chấm lại'). They stay visible as general items (`_chung`) - a leftover written in
        them ("Còn: …") is not lost - but never belong to one area."""
        text = "\n".join(["# TODO",
                          "- **Đã chạy 03/10 (dọn):** sửa `core/costume.py`; chưa làm B7. Còn: gán lại dự án",
                          "- **Chấm lại toàn bộ 03/10:** chưa thử thật costume",
                          "- [ ] việc thật còn mở, chưa làm `core/costume.py`", ""])
        items = collect.parse_todo(text)
        self.assertEqual([i["log"] for i in items], [True, True, False])
        cfg = {"areas": [{"id": "assets", "name": "Kho", "code": ["core/costume.py"], "keywords": []}]}
        by = collect.todo_by_area(items, cfg)
        self.assertEqual([i["text"] for i in by["assets"]], ["- [ ] việc thật còn mở, chưa làm `core/costume.py`"])
        self.assertEqual(len(by["_chung"]), 2)
