"""S14.10 (Gói F1): devsys đo đúng — S1 cờ theo đúng luật core.features.on(), S2 bằng chứng test::Lớp::tên kiểm bằng ast, S3 nhập điểm
đối chiếu dấu vân tay của bản xuất, S11 dòng TODO chung nhiều khu vực chia điểm, S15 trích dẫn chạy thật phải là dòng có dấu hiệu chạy thật;
Đợt 6b hiệu quả vận hành; thang v2.1."""
import json
import os
import unittest
from unittest import mock

from devsys import collect
from tests import test_devsys as base
from tests.test_devsys import _mini_repo, _write


def tearDownModule():
    base.tearDownModule()


def _clean_env():
    """No FEATURE_* / FEATURE_SETTINGS_FILE from the machine running the tests."""
    return {k: v for k, v in os.environ.items() if not k.startswith("FEATURE_")}


class FlagsStateTests(unittest.TestCase):
    """S1: devsys must say a flag is ON exactly when the Dashboard would (core.features.on): the 🧪 screen choice and preset in
    data/feature_settings.json of the measured repo, then FEATURE_<NAME> from the environment / dashboard.env."""

    def setUp(self):
        self.root = _mini_repo()
        self.cfg = collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))

    def state(self, name):
        with mock.patch.dict(os.environ, _clean_env(), clear=True):
            return {f["name"]: f for f in collect.flags_state(self.root, self.cfg)}[name]

    def test_the_screen_choice_in_feature_settings_wins(self):
        _write(self.root, "data/feature_settings.json", json.dumps({"preset": "custom", "flags": {"lip_sync": True}}))
        f = self.state("lip_sync")
        self.assertTrue(f["on"], "chọn bật trên màn 🧪 (data/feature_settings.json) → Dashboard bật")
        self.assertIn("màn", f["on_why"])

    def test_the_stable_preset_turns_an_unverified_flag_off_even_with_dashboard_env(self):
        _write(self.root, "dashboard.env", "FEATURE_LIP_SYNC=1\n")
        self.assertTrue(self.state("lip_sync")["on"])                       # custom preset: dashboard.env decides
        _write(self.root, "data/feature_settings.json", json.dumps({"preset": "stable", "flags": {}}))
        f = self.state("lip_sync")
        self.assertFalse(f["on"], "preset Ổn định: cờ chưa thử thật luôn tắt, dashboard.env không bật được")
        self.assertEqual(f["env_source"], "dashboard.env")                  # where the env value came from is still shown

    def test_module_constants_named_flag_are_found_but_not_numbers(self):
        _write(self.root, "core/hero.py", 'FLAG = "lip_sync"\nCLAUDE_FLAG = "lip_sync"\nDARK_FLAG = 0.20\n')
        sites = self.state("lip_sync")["sites"]
        self.assertIn("core/hero.py:1", sites)
        self.assertIn("core/hero.py:2", sites)
        self.assertNotIn("core/hero.py:3", sites)

    def test_a_repo_without_features_on_falls_back_to_the_ast_reading(self):
        _write(self.root, "core/features.py", 'FEATURES = {"lip_sync": {"label": "x", "verified": True, "why": ""}}\n')
        f = self.state("lip_sync")
        self.assertTrue(f["on"])                                             # verified, nothing set → on
        self.assertIn("ast", f["on_why"])


VOICE_TEST = "from core import (\n    db,\n    voice,\n)\n\n\nclass VoiceTests:\n    def test_speak(self):\n        pass\n\n\ndef test_top():\n    pass\n"


def _a21(area, **over):
    from devsys import scores
    crit = {k: {"deductions": [], "evidence_for": []} for k in scores.CRITERIA_MAX_V2}
    crit.update(over)
    return {"format": scores.FORMAT_V2, "area": area, "criteria": crit, "summary": "ổn", "can_kiem_lai": [],
            "checklist": {k: {"tra_loi": "khong", "ghi_chu": "đã đọc core/voice.py"} for k in scores.CHECKLIST_IDS}}


FIX = {"why": "ảnh hưởng", "fix": "Sửa ở core/voice.py hàm speak", "effort": "💻", "priority": 1}


class EvidenceTests(unittest.TestCase):
    """S2: a `test:` citation names a test that exists (file, class, function — read with ast); an explanation of a big swing must cite
    evidence that can be checked."""

    def setUp(self):
        self.root = _mini_repo()
        _write(self.root, "tests/test_voice.py", VOICE_TEST)

    def test_test_citations_are_checked_down_to_the_class_and_function(self):
        from devsys import scores
        ok = ("test:tests/test_voice.py", "test:tests/test_voice.py::VoiceTests::test_speak", "test:tests/test_voice.py::test_top",
              "test:tests/test_voice.py::test_speak", "test:tests/test_voice.py::VoiceTests::test_speak[a-b]")
        for e in ok:
            self.assertIsNone(scores.check_evidence(e, self.root), e)
        bad = ("test:tests/test_voice.py::VoiceTests::test_khong_co", "test:tests/test_voice.py::KhongCo::test_speak",
               "test:tests/test_voice.py::test_khong_co", "test:tests/test_khong_co.py::A::b", "test:chạy pytest thấy lỗi")
        for e in bad:
            self.assertIsNotNone(scores.check_evidence(e, self.root), e)

    def test_the_bundle_prints_failing_tests_with_their_class(self):
        from devsys import scorer, scores
        ref = scorer.test_ref("tests/test_voice.py", "tests.test_voice.VoiceTests::test_speak")
        self.assertEqual(ref, "test:tests/test_voice.py::VoiceTests::test_speak")
        self.assertIsNone(scores.check_evidence(ref, self.root))
        self.assertEqual(scorer.test_ref("tests/test_voice.py", "tests.test_voice::test_top"), "test:tests/test_voice.py::test_top")

    def test_a_blocking_deduction_citing_a_test_that_does_not_exist_is_not_blocking(self):
        from devsys import scores
        raw = _a21("voice", bang_chung={"evidence_for": ["TODO.md:3"]},
                   tin_cay={"deductions": [{"muc": "chan", "reason": "lỗi", "evidence": ["test:tests/test_voice.py::VoiceTests::test_khong_co"],
                                            "feedback": FIX}]})
        s = scores.normalize(raw, self.root, ["voice", "ui", "infra"], {"test_files": 1, "has_run": True, "failed": 0})
        self.assertEqual(s["criteria"]["tin_cay"]["deductions"][0]["muc"], "lon")

    def test_a_swing_explained_only_with_unverifiable_evidence_is_refused(self):
        from devsys import scores
        prev = {"score": 100.0, "auto_points": 0.0, "rubric_hash": scores.rubric_hash(self.root), "format": scores.FORMAT_V2}
        ded = {"muc": "lon", "reason": "lỗi", "evidence": ["core/voice.py:6"], "feedback": FIX}
        raw = _a21("voice", bang_chung={"evidence_for": ["TODO.md:3"]}, chuc_nang={"deductions": [ded, ded, ded]})
        raw["giai_thich_chenh"] = [{"criterion": "chuc_nang", "why": "lần trước bỏ sót", "evidence": ["core/khong_co.py:3"]}]
        with self.assertRaises(scores.ScoreError):
            scores.normalize(raw, self.root, ["voice", "ui", "infra"], {"test_files": 1, "has_run": True, "failed": 0}, prev=prev)
        raw["giai_thich_chenh"][0]["evidence"] = ["core/voice.py:6"]
        s = scores.normalize(raw, self.root, ["voice", "ui", "infra"], {"test_files": 1, "has_run": True, "failed": 0}, prev=prev)
        self.assertTrue(s["drift"]["explained"])


class ImportTests(unittest.TestCase):
    """S3: an external score is tied to the export it was written from (fingerprint + input_hash of the export footer); commit and date
    always come from this machine, never from the file."""

    def setUp(self):
        self.root = _mini_repo()
        self.cfg = collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))
        self.snap = collect.collect(self.root, self.cfg, db_path=os.path.join(self.root, "khong_co.sqlite"))
        self.health = collect.area_health(self.snap, self.cfg)

    def bundle(self):
        from devsys import scorer
        return scorer.build_bundle(self.root, self.cfg, collect.area_by_id(self.cfg)["voice"], self.snap, self.health["voice"], None)

    def imp(self, raw):
        from devsys import scorer
        return scorer.import_score(self.root, self.cfg, self.snap, self.health, raw, "claude-code-session")

    def test_the_export_footer_carries_both_hashes(self):
        from devsys import scorer
        b = self.bundle()
        text = open(scorer.export_bundle(self.root, b), encoding="utf-8").read()
        self.assertIn(f'"fingerprint": "{b["fingerprint"]}"', text)
        self.assertIn(f'"input_hash": "{b["input_hash"]}"', text)

    def test_a_score_without_the_export_fingerprint_is_refused(self):
        from devsys import scores
        with self.assertRaises(scores.ScoreError) as cm:
            self.imp(_a21("voice", bang_chung={"evidence_for": ["TODO.md:3"]}))
        self.assertIn("fingerprint", str(cm.exception))

    def test_a_score_of_an_older_export_is_refused(self):
        from devsys import scores
        b = self.bundle()
        raw = dict(_a21("voice", bang_chung={"evidence_for": ["TODO.md:3"]}), fingerprint=b["fingerprint"], input_hash=b["input_hash"])
        _write(self.root, "core/voice.py", "def speak(text):\n    return text.upper()\n")       # the code changed after the export
        with self.assertRaises(scores.ScoreError) as cm:
            self.imp(raw)
        self.assertIn("xuất lại", str(cm.exception))

    def test_commit_and_date_come_from_the_system(self):
        b = self.bundle()
        raw = dict(_a21("voice", bang_chung={"evidence_for": ["TODO.md:3"]}), fingerprint=b["fingerprint"], input_hash=b["input_hash"],
                   commit="deadbeef", date="2020-01-01T00:00:00+07:00")
        rec = json.load(open(self.imp(raw), encoding="utf-8"))
        self.assertEqual(rec["commit"], (collect.head(self.root) or {}).get("hash"))
        self.assertNotEqual(rec["date"], "2020-01-01T00:00:00+07:00")
        self.assertEqual(rec["claimed"], {"commit": "deadbeef", "date": "2020-01-01T00:00:00+07:00"})
        self.assertEqual((rec["fingerprint"], rec["input_hash"]), (b["fingerprint"], b["input_hash"]))


TODO_SHARED = """# TODO
## Đang làm
- [ ] Sửa `core/voice.py` và `core/db.py` cùng lúc
- [ ] Sửa riêng `core/voice.py`
- [ ] 👤 Người dùng nghe thử `core/voice.py` rồi chọn giọng
- [ ] Quy ước: mọi câu `core/voice.py` đọc phải có dấu
"""


class TodoShareTests(unittest.TestCase):
    """S11: one open TODO line tied to several areas costs the system once (its points are split between them), and only code work
    counts — a person's job (👤, người dùng nghe/chấm…) or a working convention (quy ước) is not missing code."""

    def setUp(self):
        self.root = _mini_repo()
        _write(self.root, "TODO.md", TODO_SHARED)
        self.cfg = collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))
        self.snap = collect.collect(self.root, self.cfg, db_path=os.path.join(self.root, "khong_co.sqlite"))

    def auto(self, aid):
        from devsys import metrics
        m = metrics.area_metrics(self.root, self.cfg, collect.area_by_id(self.cfg)[aid], self.snap)
        return m, {a["rule"]: a for a in metrics.auto_deductions(m)}

    def test_a_line_shared_by_two_areas_is_split_and_only_code_work_counts(self):
        m, auto = self.auto("voice")
        self.assertEqual(m["todo_open"], [3, 4])
        self.assertEqual(m["todo_people"], [5])
        self.assertEqual(m["todo_rules"], [6])
        self.assertEqual(auto["todo_mo"]["points"], round(0.3 * 1.5, 1))   # 0.3 × (½ + 1): rounded once
        m, auto = self.auto("infra")
        self.assertEqual(m["todo_open"], [3])
        self.assertEqual(auto["todo_mo"]["points"], round(0.3 * 0.5, 1))   # 0.3 × ½
        self.assertIn("chia", auto["todo_mo"]["reason"])


REPORT = """# Báo cáo chạy thử giọng

## Kết quả

Đã chạy thật 05/10 dự án #12: 14 câu, 2 câu đọc sai dấu.
Một dòng chung chung không nói gì.
"""


class RealRunEvidenceTests(unittest.TestCase):
    """S15: `bang_chung` > 0 only with a cited LINE that records a real run (a number / date / 'đã chạy') or names the area — a
    heading, a blank line or a whole file without a line number is not a record of a run."""

    def setUp(self):
        self.root = _mini_repo()
        _write(self.root, "docs/bao_cao.md", REPORT)

    def bang_chung(self, *ev):
        from devsys import scores
        s = scores.normalize(_a21("voice", bang_chung={"evidence_for": list(ev)}), self.root, ["voice", "ui", "infra"],
                             {"test_files": 1, "has_run": True, "failed": 0})
        return s["criteria"]["bang_chung"]

    def test_heading_blank_whole_file_and_vague_lines_do_not_count(self):
        for ev in ("docs/bao_cao.md:1", "docs/bao_cao.md:2", "docs/bao_cao.md:3", "docs/bao_cao.md", "docs/bao_cao.md:6", "docs/bao_cao.md:1-4"):
            c = self.bang_chung(ev)
            self.assertEqual(c["score"], 0, ev)
            self.assertTrue(any("chạy thật" in x for x in c["code_caps"]), c["code_caps"])

    def test_a_line_with_numbers_or_naming_the_area_counts(self):
        self.assertEqual(self.bang_chung("docs/bao_cao.md:5")["score"], 16)
        self.assertEqual(self.bang_chung("docs/bao_cao.md:3-5")["score"], 16)
        self.assertEqual(self.bang_chung("TODO.md:3")["score"], 16)           # "… cho giọng Việt": names the area (keyword 'giọng')
        self.assertEqual(self.bang_chung("docs/bao_cao.md:1", "docs/bao_cao.md:5")["score"], 16)


if __name__ == "__main__":
    unittest.main()
