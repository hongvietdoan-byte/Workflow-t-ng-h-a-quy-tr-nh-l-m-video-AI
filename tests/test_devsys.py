"""AI Development System (devsys/): bản đồ khu vực phủ mọi file code, đọc TODO.md, dòng thời gian git, file điểm + điểm do code tính,
người chấm giả lập không ghi sổ chi, người chấm Claude đi qua sổ chi (stage "devsys"), luôn có ước tính trước khi gọi, hook git."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unicodedata
import unittest
from unittest import mock

from core.adapters.http import HttpResponse
from core.db import connect
from devsys import collect, scorer, scores

ROOT = collect.ROOT


def _git(root, *args):
    subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@x", "-c", "commit.gpgsign=false", *args], cwd=root, check=True,
                   capture_output=True)


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


AREAS = {"version": 1, "scan_roots": ["core", "dashboard"], "infra_modules": ["core/db.py"], "areas": [
    {"id": "voice", "name": "Giọng", "weight": 2, "code": ["core/voice.py"], "assets": [], "docs": ["docs/voice.md"], "tests": [],
     "flags": ["lip_sync"], "diag_stages": ["motion"], "keywords": ["giọng"]},
    {"id": "ui", "name": "Giao diện", "weight": 1, "code": ["dashboard/*.py"], "assets": [], "docs": [], "tests": [], "flags": [],
     "diag_stages": [], "keywords": ["giao diện"]},
    {"id": "infra", "name": "Lõi", "weight": 1, "code": ["core/db.py"], "assets": [], "docs": [], "tests": [], "flags": [],
     "diag_stages": [], "keywords": []},
]}

TODO = """# TODO
## Đang làm
- [ ] Sửa `core/voice.py` cho giọng Việt
- [x] Xong hẳn cái này
- [x] Làm giao diện mới (chưa thử thật)
| 3 | Khớp môi | ✅ code · còn: thử thật (GĐ8) · **cần người dùng: có mở tài khoản sync.so không** |
Việc không đánh dấu gì
## 🔁 Việc phải làm lại MỖI LẦN (checklist cố định)
- [ ] Build lại PLAN.docx
## ⏸ Tạm gác
- [ ] Nghiên cứu thêm ⏳
"""


_TEMP = []


def tearDownModule():
    import stat

    def unlock(func, path, _exc):          # git marks its object files read-only on Windows
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for d in _TEMP:
        if not os.path.isdir(d):
            continue
        try:
            shutil.rmtree(d, onexc=unlock)                 # Python 3.12+
        except TypeError:
            shutil.rmtree(d, onerror=unlock)
        except OSError:
            pass


def _mini_repo():
    """A small git repo shaped like the project: two areas of code, a test, TODO.md, the real rubric."""
    root = tempfile.mkdtemp(prefix="devsys_")
    _TEMP.append(root)
    _write(root, "devsys/areas.json", json.dumps(AREAS, ensure_ascii=False))
    shutil.copy(os.path.join(ROOT, "devsys", "rubric.md"), os.path.join(root, "devsys", "rubric.md"))
    _write(root, "core/__init__.py", "")
    shutil.copy(os.path.join(ROOT, "core", "features.py"), os.path.join(root, "core", "features.py"))
    _write(root, "core/db.py", "def connect():\n    return None\n")
    _write(root, "core/voice.py", '"""Giọng."""\n\n\ndef speak(text):\n    """Đọc câu."""\n    return text  # TODO: chưa có TTS\n')
    _write(root, "dashboard/__init__.py", "")
    _write(root, "dashboard/app.py", "import streamlit as st\nst.button('Tạo giọng')\n")
    _write(root, "tests/test_voice.py", "from core import (\n    db,\n    voice,\n)\n")
    _write(root, "docs/voice.md", "# Giọng\n✅ xong phần đọc\n")
    _write(root, "TODO.md", TODO)
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "Khởi tạo: đã sửa hết mọi thứ, hoàn hảo")
    return root


class AreaMapTests(unittest.TestCase):
    def test_every_code_file_of_the_real_repo_belongs_to_an_area(self):
        cfg = collect.load_areas()
        cov = collect.coverage(cfg, collect.repo_files(ROOT))
        self.assertGreater(len(cov["files"]), 100)
        self.assertEqual(cov["unmapped"], [], "thêm các file này vào devsys/areas.json")

    def test_areas_json_names_real_files_and_flags(self):
        cfg = collect.load_areas()
        feats = collect.read_features(ROOT)
        self.assertEqual(len({a["id"] for a in cfg["areas"]}), len(cfg["areas"]))
        for a in cfg["areas"]:
            for kind in ("code", "assets", "docs", "tests"):
                for pat in a[kind]:
                    if not any(ch in pat for ch in "*?["):
                        self.assertTrue(os.path.exists(os.path.join(ROOT, pat)), f"{a['id']}.{kind}: {pat} không có")
            for f in a["flags"]:
                self.assertIn(f, feats, f"{a['id']}: cờ {f} không có trong core/features.py")
        self.assertTrue(all(n in {f for a in cfg["areas"] for f in a["flags"]} for n in feats), "mọi cờ thuộc ít nhất một khu vực")

    def test_every_test_file_of_the_real_repo_maps_to_an_area(self):
        cfg = collect.load_areas()
        tmap = collect.test_map(ROOT, cfg)
        self.assertEqual([t for t, v in tmap.items() if not v["areas"]], [])

    def test_imports_decide_the_areas_of_a_test_infrastructure_only_when_nothing_else(self):
        root = _mini_repo()
        cfg = collect.load_areas(os.path.join(root, "devsys", "areas.json"))
        tmap = collect.test_map(root, cfg)
        self.assertEqual(tmap["tests/test_voice.py"]["modules"], ["core/db.py", "core/voice.py"])   # multi-line "from core import (…)"
        self.assertEqual(tmap["tests/test_voice.py"]["areas"], ["voice"])                           # db is infrastructure
        cov = collect.coverage(cfg, collect.repo_files(root))
        self.assertEqual(cov["unmapped"], ["core/__init__.py", "core/features.py"])      # shown as a warning in the app
        self.assertEqual(collect.areas_of_path(cfg, "dashboard/app.py"), ["ui"])


class TodoTests(unittest.TestCase):
    def test_open_items_keep_line_section_markers_and_skip_done_lines(self):
        items = collect.parse_todo(TODO)
        by_line = {i["line"]: i for i in items}
        self.assertEqual(sorted(by_line), [3, 5, 6, 9, 11])
        self.assertEqual(by_line[3]["markers"], ["[ ]"])
        self.assertEqual(by_line[3]["section"], "Đang làm")
        self.assertEqual(by_line[5]["markers"], ["chưa thử thật"])           # a ticked line that was never run for real stays open
        self.assertIn("còn:", by_line[6]["markers"])
        self.assertTrue(by_line[6]["focus"].startswith("còn:thử thật (GĐ8)"))
        self.assertTrue(by_line[6]["waiting_user"])
        self.assertEqual(by_line[9]["kind"], "recurring")
        self.assertEqual(by_line[11]["kind"], "paused")
        self.assertEqual(by_line[11]["markers"], ["[ ]", "⏳"])

    def test_decomposed_vietnamese_is_read_the_same(self):
        nfd = unicodedata.normalize("NFD", "- việc này chưa làm\n- cái kia chưa thử thật\n")
        self.assertEqual([i["markers"] for i in collect.parse_todo(nfd)], [["chưa làm"], ["chưa thử thật"]])

    def test_items_go_to_the_area_named_by_file_flag_or_keyword(self):
        items = collect.parse_todo(TODO + "- [ ] bật cờ lip_sync\n- [ ] sửa giao diện nút\n- [ ] việc lạ ⏳\n")
        by = collect.todo_by_area(items, AREAS)
        self.assertEqual([i["line"] for i in by["voice"]], [3, 12])           # core/voice.py, flag lip_sync
        self.assertEqual(by["voice"][0]["matched_by"], "tên file/cờ")
        self.assertEqual([i["line"] for i in by["ui"]], [5, 13])               # keyword "giao diện"
        self.assertEqual([i["line"] for i in by["_chung"]], [6, 11, 14])
        self.assertNotIn(9, [i["line"] for v in by.values() for i in v])      # the fixed checklist is not an open item

    def test_the_real_todo_parses(self):
        with open(os.path.join(ROOT, "TODO.md"), encoding="utf-8") as f:
            items = collect.parse_todo(f.read())
        self.assertTrue(items)
        self.assertTrue(all(i["line"] > 0 and i["markers"] for i in items))


class GitTests(unittest.TestCase):
    def test_timeline_and_uncommitted_changes_on_a_temp_repo(self):
        root = _mini_repo()
        cfg = collect.load_areas(os.path.join(root, "devsys", "areas.json"))
        _write(root, "core/voice.py", "def speak(t):\n    return t.upper()\n")
        _git(root, "commit", "-q", "-am", "Giọng: viết hoa\n\nthân message không được đọc")
        _write(root, "dashboard/app.py", "import streamlit as st\n")                   # modified, not committed
        _write(root, "dashboard/new_page.py", "x = 1\ny = 2\n")                         # new file
        tl = collect.timeline(root, cfg)
        self.assertEqual([c["subject"] for c in tl], ["Giọng: viết hoa", "Khởi tạo: đã sửa hết mọi thứ, hoàn hảo"])
        self.assertEqual(tl[0]["files"], ["core/voice.py"])
        self.assertEqual(tl[0]["areas"], ["voice"])
        self.assertIn("ui", tl[1]["areas"])
        work = {w["path"]: w for w in collect.working_changes(root, cfg)}
        self.assertEqual(set(work), {"dashboard/app.py", "dashboard/new_page.py"})
        self.assertEqual(work["dashboard/app.py"]["status"], "sửa")
        self.assertEqual(work["dashboard/new_page.py"]["status"], "mới (chưa add)")
        self.assertEqual(work["dashboard/new_page.py"]["added"], 2)
        self.assertEqual(work["dashboard/app.py"]["areas"], ["ui"])
        self.assertEqual(collect.head(root)["subject"], "Giọng: viết hoa")

    def test_porcelain_renames_and_log_records(self):
        entries = collect.parse_porcelain("R  moi.py\0cu.py\0?? thư mục/tệp.md\0 M core/x.py\0")
        self.assertEqual([(e["path"], e["status"], e["orig"]) for e in entries],
                         [("moi.py", "đổi tên", "cu.py"), ("thư mục/tệp.md", "mới (chưa add)", None), ("core/x.py", "sửa", None)])
        log = "\x1eabc\x1fa\x1f2026-09-26T10:00:00+07:00\x1fAn\x1fDòng đầu\ncore/voice.py\nTODO.md\n\x1edef\x1fd\x1f2026-09-25T10:00:00+07:00\x1fBình\x1fTrống\n"
        recs = collect.parse_log(log)
        self.assertEqual(recs[0]["files"], ["core/voice.py", "TODO.md"])
        self.assertEqual(recs[1]["files"], [])

    def test_junit_results_are_counted_per_test_file_and_area(self):
        root = _mini_repo()
        cfg = collect.load_areas(os.path.join(root, "devsys", "areas.json"))
        xml = ('<testsuites><testsuite><testcase classname="tests.test_voice.VoiceTests" name="test_ok"/>'
               '<testcase classname="tests.test_voice.VoiceTests" name="test_bad"><failure message="AssertionError: 1 != 2">tb</failure></testcase>'
               '<testcase classname="tests.test_voice.VoiceTests" name="test_skip"><skipped message="x"/></testcase></testsuite></testsuites>')
        run = collect.parse_junit(xml, root)
        self.assertEqual(run["totals"], {"tests": 3, "passed": 1, "failed": 1, "errors": 0, "skipped": 1})
        by = collect.tests_by_area(run, collect.test_map(root, cfg), cfg)
        self.assertEqual((by["voice"]["passed"], by["voice"]["failed"]), (1, 1))
        self.assertEqual(by["voice"]["failed_names"][0]["message"], "AssertionError: 1 != 2")
        self.assertEqual(by["ui"]["test_files"], [])


def _answer(area, **over):
    crit = {k: {"deductions": [], "evidence_for": []} for k in scores.CRITERIA_MAX}
    crit.update(over)
    return {"area": area, "criteria": crit, "summary": "ổn", "can_kiem_lai": []}


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.root = _mini_repo()
        self.ids = ["voice", "ui", "infra"]

    def test_the_score_is_computed_by_code_from_deductions_with_evidence(self):
        raw = _answer("voice", chuc_nang={"deductions": [{"points": 5, "reason": "chưa có TTS", "evidence": ["core/voice.py:6"]}]},
                      bang_chung={"deductions": [{"points": 12, "reason": "chưa chạy thật", "evidence": ["TODO.md:5"]}],
                                  "evidence_for": ["docs/voice.md:2"]})
        raw["score"] = 100                                                   # a claimed total is ignored
        s = scores.normalize(raw, self.root, self.ids, {"test_files": 1, "has_run": True, "failed": 0})
        self.assertEqual(s["criteria"]["chuc_nang"]["score"], 25)
        self.assertEqual(s["criteria"]["bang_chung"]["score"], 8)
        self.assertEqual(s["score"], 25 + 8 + 15 + 15 + 10 + 10)
        self.assertEqual(s["unverified_evidence"], [])

    def test_a_deduction_without_evidence_is_refused(self):
        with self.assertRaises(scores.ScoreError):
            scores.normalize(_answer("voice", test={"deductions": [{"points": 3, "reason": "ít test", "evidence": []}]}), self.root, self.ids)
        with self.assertRaises(scores.ScoreError):
            scores.normalize({"area": "voice", "criteria": {}}, self.root, self.ids)
        with self.assertRaises(scores.ScoreError):
            scores.normalize(_answer("khac"), self.root, self.ids)

    def test_code_caps_real_run_evidence_and_tests(self):
        s = scores.normalize(_answer("voice"), self.root, self.ids, {"test_files": 0, "has_run": False, "failed": 0})
        self.assertEqual(s["criteria"]["bang_chung"]["score"], 0)            # no real-run citation → 0 whatever the scorer says
        self.assertEqual(s["criteria"]["test"]["score"], 3)                  # no test file at all
        s = scores.normalize(_answer("voice", bang_chung={"deductions": [], "evidence_for": ["core/voice.py:2"]}), self.root, self.ids,
                             {"test_files": 2, "has_run": True, "failed": 1})
        self.assertEqual(s["criteria"]["bang_chung"]["score"], 0)            # code is not a record of a real run
        self.assertEqual(s["criteria"]["test"]["score"], 7)
        s = scores.normalize(_answer("voice", bang_chung={"deductions": [], "evidence_for": ["TODO.md:6"]}), self.root, self.ids,
                             {"test_files": 2, "has_run": False, "failed": 0})
        self.assertEqual(s["criteria"]["bang_chung"]["score"], 20)
        self.assertEqual(s["criteria"]["test"]["score"], 8)

    def test_evidence_that_cannot_be_found_is_flagged(self):
        raw = _answer("voice", tai_lieu={"deductions": [{"points": 2, "reason": "lệch", "evidence": ["core/voice.py:999", "core/khong_co.py"]}]})
        s = scores.normalize(raw, self.root, self.ids)
        self.assertEqual(len(s["unverified_evidence"]), 2)
        self.assertEqual(s["criteria"]["tai_lieu"]["score"], 8)

    def test_files_load_aggregate_and_trend(self):
        cfg = AREAS
        base = {"format": scores.FORMAT, "rubric_hash": scores.rubric_hash(self.root)}
        for date, area, pts, who in (("2026-09-20T10:00:00+07:00", "voice", 40, "claude-api"),
                                     ("2026-09-21T10:00:00+07:00", "ui", 10, "claude-code-session"),
                                     ("2026-09-22T10:00:00+07:00", "voice", 20, "claude-api"),
                                     ("2026-09-23T10:00:00+07:00", "infra", 0, "mock")):
            raw = _answer(area, chuc_nang={"deductions": [{"points": pts, "reason": "x", "evidence": ["absent:x"]}] if pts else []})
            scores.save({**base, **raw, "scorer": who, "date": date}, self.root)
        _write(self.root, "devsys/data/scores/hong.json", "{không phải json")
        _write(self.root, "devsys/data/scores/thieu_scorer.json", json.dumps({"format": scores.FORMAT, **_answer("ui")}))
        loaded, problems = scores.load_all(self.root, self.ids)
        self.assertEqual(len(loaded), 4)
        self.assertEqual(len(problems), 2)
        latest = scores.latest_by_area(loaded)
        # every answer has no real-run citation (bang_chung 0) and no facts (no test caps): 80 - deductions
        self.assertEqual(latest["voice"]["score"], 60)
        self.assertEqual(latest["ui"]["score"], 70)
        o = scores.overall(latest, cfg)
        self.assertEqual(o["covered"], ["voice", "ui"])                      # the mock score does not count
        self.assertAlmostEqual(o["score"], (2 * 60 + 70) / 3, places=1)
        tr = scores.trend(loaded, cfg)
        # the first voice answer took 40 from a criterion worth 30: the criterion stops at 0 (score 50, not 40)
        self.assertEqual([p["overall"] for p in tr], [50, round((2 * 50 + 70) / 3, 1), round((2 * 60 + 70) / 3, 1)])


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.root = _mini_repo()
        self.cfg = collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))
        self.snap = collect.collect(self.root, self.cfg, db_path=os.path.join(self.root, "khong_co.sqlite"))
        self.health = collect.area_health(self.snap, self.cfg)
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        connect(self.db).close()

    def usage_rows(self):
        conn = connect(self.db)
        try:
            return [dict(r) for r in conn.execute("SELECT provider, model, tier, quantity, stage FROM usage_events ORDER BY id")]
        finally:
            conn.close()

    def test_bundle_holds_real_data_and_no_commit_message(self):
        p = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice"], provider="mock")
        prompt = p["todo"][0]["prompt"]
        self.assertIn("L4: def speak(text):", prompt)                         # code with real line numbers
        self.assertIn("TODO.md:3", prompt)
        self.assertIn("flag:lip_sync", prompt)
        self.assertIn("CHƯA CÓ LẦN CHẠY TEST", prompt)
        self.assertIn("Thang chấm cố định", prompt)
        self.assertNotIn("hoàn hảo", prompt)                                  # the self-praising commit message never reaches the scorer

    def test_mock_scorer_records_nothing_and_incremental_mode_skips_unchanged_areas(self):
        p = scorer.plan(self.root, self.cfg, self.snap, self.health, provider="mock")
        self.assertEqual([b["area"] for b in p["todo"]], ["voice", "ui", "infra"])
        with self.assertRaises(scorer.ScorerError):
            scorer.run(self.root, self.cfg, self.snap, p["todo"], "mock", yes=False, db_path=self.db, note=lambda m: None)
        res = scorer.run(self.root, self.cfg, self.snap, p["todo"], "mock", yes=True, db_path=self.db, note=lambda m: None)
        self.assertEqual((len(res["saved"]), res["failed"], res["usd"]), (3, [], 0.0))
        self.assertEqual(self.usage_rows(), [])                               # nothing paid, nothing in the ledger
        saved = json.load(open(res["saved"][0], encoding="utf-8"))
        self.assertEqual((saved["scorer"], saved["model"]), ("mock", "mock"))
        self.assertTrue(saved["fingerprint"] and saved["input_hash"] and saved["commit"])
        again = scorer.plan(self.root, self.cfg, self.snap, self.health, provider="mock")
        self.assertEqual(again["todo"], [])
        self.assertEqual(len(again["skipped"]), 3)
        _write(self.root, "core/voice.py", "def speak(t):\n    return t\n")  # the voice area changed → only it is scored again
        snap = collect.collect(self.root, self.cfg, db_path=os.path.join(self.root, "khong_co.sqlite"))
        again = scorer.plan(self.root, self.cfg, snap, collect.area_health(snap, self.cfg), provider="mock")
        self.assertEqual([b["area"] for b in again["todo"]], ["voice"])
        self.assertIn("Từ lần chấm trước", again["todo"][0]["prompt"])         # the diff since the last score is sent

    def test_estimate_is_priced_from_pricing_json(self):
        p = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice", "ui"])
        est = scorer.estimate(p["todo"], "claude-sonnet-5")
        self.assertTrue(est["priced"])
        self.assertGreater(est["usd_expected"], 0)
        self.assertGreater(est["usd_max"], est["usd_expected"])
        text = scorer.estimate_text(est)
        self.assertIn("$", text)
        self.assertIn("2 khu vực", text)
        self.assertFalse(scorer.estimate(p["todo"], "model-khong-gia")["priced"])

    def test_claude_scoring_goes_through_the_cost_ledger_with_stage_devsys(self):
        calls = []

        def send(method, url, headers, body, timeout):
            payload = json.loads(body)
            calls.append(payload)
            answer = _answer("voice", chuc_nang={"deductions": [{"points": 6, "reason": "chưa có TTS", "evidence": ["core/voice.py:6"]}]})
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": json.dumps(answer, ensure_ascii=False)}],
                                                 "stop_reason": "end_turn", "usage": {"input_tokens": 5000, "output_tokens": 800}}).encode())

        p = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice"])
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-devsys", "ANTHROPIC_MODEL": "claude-sonnet-5"}):
            res = scorer.run(self.root, self.cfg, self.snap, p["todo"], "anthropic", yes=True, db_path=self.db, transport=send,
                             note=lambda m: None)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["output_config"], {"effort": "low"})         # stage "devsys" settings
        self.assertEqual(calls[0]["max_tokens"], scorer.MAX_OUTPUT_TOKENS)
        self.assertNotIn("temperature", calls[0])
        rows = self.usage_rows()
        self.assertEqual({(r["provider"], r["stage"], r["tier"], r["quantity"]) for r in rows},
                         {("anthropic", "devsys", "input", 5000), ("anthropic", "devsys", "output", 800)})
        saved = json.load(open(res["saved"][0], encoding="utf-8"))
        self.assertEqual((saved["scorer"], saved["model"], saved["criteria"]["chuc_nang"]["score"]), ("claude-api", "claude-sonnet-5", 24))
        self.assertAlmostEqual(saved["usage"]["usd"], (5000 * 2 + 800 * 10) / 1e6, places=6)

    def test_claude_scoring_refuses_without_a_ledger_or_over_the_claude_cap(self):
        p = scorer.plan(self.root, self.cfg, self.snap, self.health, ["voice"])
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-devsys"}):
            with self.assertRaises(scorer.ScorerError):
                scorer.run(self.root, self.cfg, self.snap, p["todo"], "anthropic", yes=True, db_path=os.path.join(self.root, "khong.sqlite"),
                           transport=lambda *a: self.fail("không được gọi"), note=lambda m: None)
            from core import budget
            conn = connect(self.db)
            budget.save(conn, llm_usd=0.0001)
            conn.close()
            with self.assertRaises(scorer.ScorerError):
                scorer.run(self.root, self.cfg, self.snap, p["todo"], "anthropic", yes=True, db_path=self.db,
                           transport=lambda *a: self.fail("không được gọi"), note=lambda m: None)
        self.assertEqual(self.usage_rows(), [])

    def test_external_score_is_imported_and_recomputed(self):
        raw = _answer("ui", trai_nghiem={"deductions": [{"points": 4, "reason": "nút tốn tiền không ghi giá", "evidence": ["dashboard/app.py:2"]}]})
        raw["score"] = 99
        with self.assertRaises(scores.ScoreError):
            scorer.import_score(self.root, self.cfg, self.snap, self.health, dict(raw))            # no scorer name
        path = scorer.import_score(self.root, self.cfg, self.snap, self.health, raw, "claude-code-session")
        loaded, problems = scores.load_all(self.root, ["voice", "ui", "infra"])
        self.assertEqual(problems, [])
        self.assertEqual(loaded[0]["scorer"], "claude-code-session")
        self.assertEqual(loaded[0]["criteria"]["trai_nghiem"]["score"], 6)
        self.assertEqual(loaded[0]["score"], 30 + 0 + 3 + 15 + 6 + 10)       # no test file for ui → test capped at 3; no real-run → 0
        self.assertTrue(os.path.basename(path).endswith("_ui.json"))

    def test_cli_shows_the_estimate_and_calls_nothing_without_yes(self):
        from tools import devsys_score
        out = io.StringIO()
        with mock.patch.object(scorer, "make_client", side_effect=AssertionError("không được tạo client")), \
                contextlib.redirect_stdout(out):
            code = devsys_score.main(["--areas", "lipsync"])
        self.assertEqual(code, 1)
        self.assertIn("Ước tính chấm 1 khu vực", out.getvalue())
        self.assertIn("Chưa gọi gì", out.getvalue())


class HookTests(unittest.TestCase):
    def test_install_is_idempotent_keeps_the_old_hook_and_uninstalls(self):
        from tools import devsys_hook
        root = _mini_repo()
        hook = devsys_hook.hook_path(root)
        _write(root, os.path.relpath(hook, root), "#!/bin/sh\necho cu\n")
        devsys_hook.install(root, python="C:\\Python\\python.exe")
        devsys_hook.install(root, python="C:\\Python\\python.exe")
        text = open(hook, encoding="utf-8").read()
        self.assertEqual(text.count(devsys_hook.BEGIN), 1)
        self.assertIn("echo cu", text)
        self.assertIn('"C:/Python/python.exe"', text)
        self.assertIn("|| true", text)                                        # never blocks a commit
        self.assertTrue(devsys_hook.installed(root))
        self.assertTrue(devsys_hook.uninstall(root))
        self.assertEqual(open(hook, encoding="utf-8").read(), "#!/bin/sh\necho cu\n")

    def test_run_records_the_commit_and_never_fails(self):
        from tools import devsys_hook
        root = _mini_repo()
        self.assertEqual(devsys_hook.run(root), 0)
        events = collect.read_events(root)
        self.assertEqual([e["kind"] for e in events], ["commit", "snapshot"])
        self.assertEqual(events[0]["areas"], sorted(events[0]["areas"]))
        self.assertTrue(os.path.exists(os.path.join(root, "devsys", "data", "snapshot.json")))
        _write(root, "devsys/areas.json", "{hỏng")
        self.assertEqual(devsys_hook.run(root), 0)
        self.assertTrue(os.path.exists(os.path.join(root, "devsys", "data", "hook_errors.log")))


class AppTests(unittest.TestCase):
    def test_every_page_renders_without_an_exception(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:  # pragma: no cover
            self.skipTest("streamlit.testing không có")
        at = AppTest.from_file(os.path.join(ROOT, "devsys", "app.py"), default_timeout=180)
        at.run()
        self.assertEqual([e.value for e in at.exception], [])
        for page in at.sidebar.radio[0].options:
            at.sidebar.radio[0].set_value(page).run()
            self.assertEqual([e.value for e in at.exception], [], page)


if __name__ == "__main__":
    unittest.main()
