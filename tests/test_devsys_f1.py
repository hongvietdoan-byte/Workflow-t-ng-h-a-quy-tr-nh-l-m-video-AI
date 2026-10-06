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
        _write(self.root, "tests/fixtures/run4.json", "{\n  \"x\": 1\n}\n")
        self.assertEqual(self.bang_chung("tests/fixtures/run4.json:1")["score"], 16)   # a fixture / data file is the record as a whole


def _ops_db(rows=(), feedback=()):
    """A real-schema database (core.db.connect) with system-wide effectiveness snapshots and feedback."""
    import tempfile
    from core.db import connect
    path = os.path.join(tempfile.mkdtemp(prefix="devsys_ops_"), "m.sqlite")
    conn = connect(path)
    for at, img, vid, flags, kfp in rows:
        conn.execute("INSERT INTO effectiveness_snapshots (at, project_id, trigger, image_first_pass, video_first_pass, satisfaction, feedback_n,"
                     " flags_on, knowledge_fp) VALUES (?, NULL, 'manual', ?, ?, 0.8, 3, ?, ?)", (at, img, vid, json.dumps(flags), kfp))
    for at, stage, rating, handled in feedback:
        conn.execute("INSERT INTO user_feedback (at, kind, stage, rating, text, handled) VALUES (?, 'delivery', ?, ?, 'ảnh lệch mặt nhân vật', ?)",
                     (at, stage, rating, handled))
    conn.commit()
    conn.close()
    return path


def _recent(days_ago: int) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M")


OPS_AREAS = {**base.AREAS, "areas": [dict(a, ops_stages=["image"]) if a["id"] == "voice" else a for a in base.AREAS["areas"]]}


class OpsSummaryTests(unittest.TestCase):
    """Đợt 6b: devsys reads what real runs say about the output (effectiveness snapshots + feedback), read-only, and the scorer sees it."""

    def setUp(self):
        self.root = _mini_repo()
        _write(self.root, "devsys/areas.json", json.dumps(OPS_AREAS, ensure_ascii=False))
        self.cfg = collect.load_areas(os.path.join(self.root, "devsys", "areas.json"))
        self.db = _ops_db(rows=[(_recent(9), 0.80, 0.5, ["a"], "k1"), (_recent(2), 0.60, 0.5, ["a", "b"], "k1")],
                          feedback=[(_recent(1), "image", 1, None), (_recent(3), "image", 2, None), (_recent(4), "image", 5, None),
                                    (_recent(5), "image", 1, "bỏ qua: đã sửa")])

    def test_ops_summary_reads_snapshots_feedback_and_what_changed(self):
        ops = collect.ops_summary(self.db, self.root)
        self.assertTrue(ops["available"])
        self.assertEqual([r["image_first_pass"] for r in ops["trend"]], [0.8, 0.6])
        self.assertEqual(ops["latest"]["flags_on"], ["a", "b"])
        self.assertEqual([m["text"] for m in ops["markers"]], ["+b"])
        img = ops["feedback"]["by_stage"]["image"]
        self.assertEqual((img["n"], img["low"], len(img["low_open_30d"]), img["positive"]), (4, 3, 2, 1))
        none = collect.ops_summary(os.path.join(self.root, "khong_co.sqlite"), self.root)
        self.assertFalse(none["available"])
        self.assertIn("không có CSDL", none["note"])

    def test_the_effect_page_puts_three_lines_and_the_markers_on_one_axis(self):
        ops = collect.ops_summary(self.db, self.root)
        d = collect.effect_series([{"date": _recent(3), "overall": 71.5}], ops)
        self.assertEqual({p["series"] for p in d["points"]},
                         {"Điểm devsys (có trọng số)", "Ảnh qua lần đầu (%)", "Video qua lần đầu (%)", "Góp ý hài lòng (%)"})
        self.assertEqual([m["text"] for m in d["markers"]], ["+b"])
        self.assertEqual(d["notes"], [])
        none = collect.effect_series([], collect.ops_summary(os.path.join(self.root, "x.sqlite"), self.root))
        self.assertEqual(len(none["notes"]), 2)                                 # both missing inputs are said, not silently empty

    def test_the_bundle_has_the_two_sections_and_the_fingerprint_follows_new_data(self):
        from devsys import scorer
        snap = collect.collect(self.root, self.cfg, db_path=self.db)
        health = collect.area_health(snap, self.cfg)
        area = collect.area_by_id(self.cfg)["voice"]
        b = scorer.build_bundle(self.root, self.cfg, area, snap, health["voice"])
        self.assertIn("## Hiệu quả vận hành", b["prompt"])
        self.assertIn("## Góp ý người dùng", b["prompt"])
        self.assertIn(f"db:effectiveness_snapshots:{snap['ops']['latest']['id']}", b["prompt"])
        self.assertLess(b["prompt"].index("## Hiệu quả vận hành"), b["prompt"].index("## Điểm lần trước"))
        ui = scorer.build_bundle(self.root, self.cfg, collect.area_by_id(self.cfg)["ui"], snap, health["ui"])
        self.assertIn("không gắn khâu vận hành", ui["prompt"])
        db2 = _ops_db(rows=[(_recent(9), 0.80, 0.5, ["a"], "k1"), (_recent(2), 0.60, 0.5, ["a", "b"], "k1"), (_recent(1), 0.6, 0.5, ["a"], "k1")])
        snap2 = collect.collect(self.root, self.cfg, db_path=db2)
        self.assertNotEqual(scorer.fingerprint(self.root, area, snap, health["voice"]),
                            scorer.fingerprint(self.root, area, snap2, collect.area_health(snap2, self.cfg)["voice"]))


FULL = {"test_files": 1, "has_run": True, "failed": 0}


def _a21_full(area, **over):
    from devsys import scores
    raw = _a21(area, **over)
    raw["format"] = scores.FORMAT_V21
    return raw


class RubricV21Tests(unittest.TestCase):
    """Thang v2.1 (S14.10, đổi MỘT lần): K11/K12, tiêu chí mặc định cho mỗi loại lỗi, `db:` chỉ cho khoản tự động, khu vực chỉ tài liệu
    không chấm `test`, điểm cũ bản 2 vẫn đọc được với số cũ."""

    def setUp(self):
        self.root = _mini_repo()
        self.ids = ["voice", "ui", "infra"]

    def norm(self, raw, facts=FULL, **kw):
        from devsys import scores
        return scores.normalize(raw, self.root, self.ids, facts, **kw)

    def test_the_rubric_file_is_v21_and_names_what_code_enforces(self):
        from devsys import metrics, scores
        text = open(os.path.join(collect.ROOT, "devsys", "rubric.md"), encoding="utf-8").read()
        self.assertIn("bản 2.1", text)
        self.assertIn(scores.FORMAT_V21, text)
        for k in ("K11_vong_doi_job", "K12_pha_huy_truoc_ban_moi"):
            self.assertIn(k, scores.CHECKLIST_IDS)
            self.assertIn(k, text)
        for k in scores.CHECKLIST_IDS:
            self.assertIn(scores.CHECKLIST_CRITERION[k], scores.CRITERIA_MAX_V2, k)
        for rule in ("hieu_qua_tut", "gop_y_lap"):
            self.assertIn(rule, metrics.RULES)
            self.assertIn(f"`{rule}`", text)
        self.assertIn("db:", text)
        self.assertEqual(scores.version_of({"format": scores.FORMAT_V21}), 2.1)

    def test_a_v21_answer_must_answer_k11_and_k12_but_an_old_v2_file_need_not(self):
        from devsys import scores
        old = _a21("voice", bang_chung={"evidence_for": ["TODO.md:3"]})          # format devsys-score/2
        for k in ("K11_vong_doi_job", "K12_pha_huy_truoc_ban_moi"):
            old["checklist"].pop(k, None)
        self.assertEqual(self.norm(old)["format"], scores.FORMAT_V2)            # old files keep loading
        new = dict(old, format=scores.FORMAT_V21)
        with self.assertRaises(scores.ScoreError) as cm:
            self.norm(new)
        self.assertIn("K11_vong_doi_job", str(cm.exception))
        with self.assertRaises(scores.ScoreError):
            self.norm(old, version=2.1)                                         # a NEW answer is checked by the current rubric

    def test_db_evidence_is_only_for_automatic_deductions(self):
        from devsys import scores
        self.assertIsNotNone(scores.check_evidence("db:user_feedback:3", self.root))
        raw = _a21_full("voice", bang_chung={"evidence_for": ["TODO.md:3"]},
                        tin_cay={"deductions": [{"muc": "chan", "reason": "x", "evidence": ["db:user_feedback:3"], "feedback": FIX}]})
        d = self.norm(raw)["criteria"]["tin_cay"]["deductions"][0]
        self.assertEqual(d["muc"], "lon")                                       # db: never proves a blocker
        self.assertIn("db:user_feedback:3", d["unverified"])

    def test_a_docs_only_area_has_no_test_criterion_and_is_rescaled(self):
        raw = _a21_full("voice", bang_chung={"evidence_for": ["TODO.md:3"]}, chuc_nang={"deductions": [{"muc": "lon", "reason": "x",
                                                                                                         "evidence": ["TODO.md:3"], "feedback": FIX}]})
        s = self.norm(raw, {"test_files": 0, "has_run": False, "failed": 0, "doc_only": True})
        self.assertTrue(s["criteria"]["test"]["khong_ap_dung"])
        self.assertEqual(s["criteria"]["test"]["max"], 0)
        self.assertAlmostEqual(s["score"], round((88 - 3.1) * 100 / 88, 1), places=1)    # no 2.4 / 12 cap, rescaled to 100
        code_area = self.norm(raw, {"test_files": 0, "has_run": False, "failed": 0})
        self.assertEqual(code_area["criteria"]["test"]["score"], 2.4)


class MeasureV21Tests(unittest.TestCase):
    """S10 bảo trì: mỗi file trừ một lần, trần chung; except có chú thích lý do không bị coi là nuốt lỗi. 6b: hieu_qua_tut / gop_y_lap."""

    def test_an_except_with_a_reason_comment_is_not_swallowing(self):
        import ast
        from devsys import metrics
        src = ("def a():\n    try:\n        x()\n    except Exception:  # noqa: BLE001 - chỉ là dòng trạng thái, lỗi đã hiện ở trên\n        pass\n"
               "def b():\n    try:\n        x()\n    except Exception:  # noqa: BLE001\n        pass\n"
               "def c():\n    try:\n        x()\n    except Exception:\n        # bỏ qua: tệp tạm có thể đã bị xóa\n        pass\n")
        self.assertEqual(metrics.swallowed_excepts(ast.parse(src), src), [9])

    def test_maintenance_deductions_count_each_file_once_and_share_one_cap(self):
        from devsys import metrics
        m = {"big_files": ["core/a.py:1200", "core/b.py:950"], "long_funcs": [f"core/a.py:{i} f{i} (200 dòng)" for i in range(1, 5)]
             + ["core/c.py:3 g (160 dòng)", "core/c.py:90 h (170 dòng)"], "complex_funcs": ["core/c.py:3 g (40)", "core/d.py:5 k (35)"],
             "todo_open": [], "flags_on_unverified": [], "swallowed": [], "paid_unguarded": [], "modules_untested": [], "funcs_untested_ratio": 0,
             "funcs_public": 0, "funcs_untested": 0, "untested_names": [], "controls": {}}
        auto = {a["rule"]: a for a in metrics.auto_deductions(m)}
        self.assertEqual(auto["file_dai"]["points"], 2.0)
        self.assertEqual(auto["ham_dai"]["count"], 1)                            # only core/c.py (core/a.py is already a long file)
        self.assertEqual(auto["ham_phuc_tap"]["count"], 1)                       # only core/d.py
        self.assertLessEqual(sum(a["points"] for a in auto.values() if a["criterion"] == "bao_tri"), metrics.BAO_TRI_AUTO_CAP)

    def test_effectiveness_drop_and_repeated_complaints_become_automatic_deductions(self):
        from devsys import metrics
        root = _mini_repo()
        _write(root, "devsys/areas.json", json.dumps(OPS_AREAS, ensure_ascii=False))
        cfg = collect.load_areas(os.path.join(root, "devsys", "areas.json"))
        db = _ops_db(rows=[(_recent(9), 0.80, 0.5, ["a"], "k1"), (_recent(2), 0.60, 0.5, ["a"], "k1")],
                     feedback=[(_recent(1), "image", 1, None), (_recent(3), "image", 2, None), (_recent(4), "image", 2, None)])
        snap = collect.collect(root, cfg, db_path=db)
        m = metrics.area_metrics(root, cfg, collect.area_by_id(cfg)["voice"], snap)
        auto = {a["rule"]: a for a in metrics.auto_deductions(m)}
        self.assertEqual(auto["hieu_qua_tut"]["criterion"], "bang_chung")
        self.assertTrue(all(e.startswith("db:effectiveness_snapshots:") for e in auto["hieu_qua_tut"]["evidence"]))
        self.assertEqual(auto["gop_y_lap"]["criterion"], "trai_nghiem")
        self.assertEqual(len(auto["gop_y_lap"]["evidence"]), 3)
        # the same drop while a flag was switched (or the knowledge changed) is explained by that change: no deduction
        db2 = _ops_db(rows=[(_recent(9), 0.80, 0.5, ["a"], "k1"), (_recent(2), 0.60, 0.5, ["a", "b"], "k1")])
        snap2 = collect.collect(root, cfg, db_path=db2)
        m2 = metrics.area_metrics(root, cfg, collect.area_by_id(cfg)["voice"], snap2)
        self.assertNotIn("hieu_qua_tut", {a["rule"] for a in metrics.auto_deductions(m2)})


class AggregateV21Tests(unittest.TestCase):
    """S14 tổng chỉ cộng cùng thang (cờ mixed); S17 vân tay không đổi vì số test qua; S5 ổn định chỉ so cùng người chấm."""

    def test_overall_averages_only_one_scale_and_says_when_mixed(self):
        from devsys import scores
        cfg = base.AREAS
        latest = {"voice": {"area": "voice", "score": 80.0, "rubric_hash": "moi", "scorer": "s"},
                  "ui": {"area": "ui", "score": 40.0, "rubric_hash": "cu", "scorer": "s"}}
        o = scores.overall(latest, cfg, rubric="moi")
        self.assertEqual((o["score"], o["covered"], o["mixed"], o["other_scale"]), (80.0, ["voice"], True, ["ui"]))
        self.assertFalse(scores.overall({"voice": latest["voice"]}, cfg, rubric="moi")["mixed"])

    def test_the_fingerprint_does_not_move_with_the_number_of_passing_tests(self):
        from devsys import scorer
        root = _mini_repo()
        cfg = collect.load_areas(os.path.join(root, "devsys", "areas.json"))
        snap = collect.collect(root, cfg, db_path=os.path.join(root, "x.sqlite"))
        area = collect.area_by_id(cfg)["voice"]
        t = snap["tests_by_area"]["voice"]
        fp = scorer.fingerprint(root, area, snap, {})
        t["passed"] += 7
        self.assertEqual(scorer.fingerprint(root, area, snap, {}), fp)
        t["failed"] += 1
        self.assertNotEqual(scorer.fingerprint(root, area, snap, {}), fp)

    def test_stability_noise_only_counts_the_same_scorer(self):
        from devsys import scores
        a = {"area": "voice", "score": 80.0, "rubric_hash": "h", "fingerprint": "f", "scorer": "claude-api", "date": "1"}
        b = dict(a, score=70.0, scorer="claude-code-session", date="2")
        c = dict(a, score=78.0, scorer="claude-code-session", date="3")
        st = scores.stability([a, b, c])
        self.assertEqual(st["n"], 2)
        self.assertEqual([p["delta"] for p in st["noise"]], [8.0])              # b → c: same scorer, same fingerprint
        self.assertEqual(st["cross_scorer"], 1)


class ImportPlaceTests(unittest.TestCase):
    """S4: an import from a git worktree is refused (its devsys/data and data/ are not the real ones); a missing devsys/data/runs is said
    as such, not as 'never ran the tests'."""

    def test_import_from_a_worktree_is_refused(self):
        from devsys import scorer, scores
        with mock.patch.object(scorer, "worktree_of", return_value="D:/repo"):
            with self.assertRaises(scores.ScoreError) as cm:
                scorer.check_import_place(collect.ROOT)
        self.assertIn("D:/repo", str(cm.exception))
        with mock.patch.object(scorer, "worktree_of", return_value=None):
            scorer.check_import_place(collect.ROOT)

    def test_the_test_cap_says_when_devsys_data_is_missing(self):
        from devsys import scores
        s = scores.normalize(_a21_full("voice", bang_chung={"evidence_for": ["TODO.md:3"]}), _mini_repo(), ["voice", "ui", "infra"],
                             {"test_files": 2, "has_run": False, "failed": 0, "runs_dir": False})
        self.assertTrue(any("devsys/data/runs" in c for c in s["criteria"]["test"]["code_caps"]), s["criteria"]["test"]["code_caps"])


if __name__ == "__main__":
    unittest.main()
