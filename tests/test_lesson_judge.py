"""S14.24 (Bộ não prompt Đợt 5): agent chấm bài học — CHẾ ĐỘ BÓNG. Chấm + ghi lesson_reviews (reviewer_type ai_agent), KHÔNG đổi
bài học / knowledge; cờ `lesson_judge` TẮT mặc định; rubric 6 tiêu chí (AI ghi khoản trừ + bằng chứng, CODE tính điểm); 8 van về người."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import cost, features, lesson_judge as lj, llm_runner
from core.db import connect


def _ai(**over):
    """A valid AI answer: no deduction anywhere unless overridden."""
    crit = {k: {"deductions": []} for k in lj.AI_CRITERIA}
    crit.update(over)
    return {"criteria": crit, "summary": "ổn"}


def _ded(muc, reason="x", evidence=("trích",), sua="sửa thế này"):
    d = {"muc": muc, "reason": reason, "evidence": list(evidence)}
    if sua is not None:
        d["sua"] = sua
    return d


GOOD_FACTS = {"lesson_id": 1, "source": "mistakes", "group": "director", "key": "mistake:hands", "state": "proposed",
              "events": 4, "projects": 2, "examples_found": 2, "examples": 2, "key_known": True, "duplicates": [],
              "retired": [], "approved_in_group": 1, "doc_chars": 900, "docs_text": "Luôn ghi rõ số ngón tay."}


class NormalizeTests(unittest.TestCase):
    def test_clean_answer_scores_full_marks(self):
        r = lj.normalize(json.dumps(_ai()), GOOD_FACTS)
        self.assertEqual(r["total"], 100)
        self.assertEqual(r["score"], 1.0)
        self.assertEqual(r["floors_failed"], [])

    def test_code_takes_points_by_severity_never_the_model(self):
        r = lj.normalize(_ai(cu_the={"deductions": [_ded("lon"), _ded("nho", sua=None)]}, do_rong={"deductions": [_ded("nho", sua=None)]}),
                         GOOD_FACTS)
        self.assertAlmostEqual(r["criteria"]["cu_the"]["points"], 25 - 25 * 0.12 - 25 * 0.04)
        self.assertAlmostEqual(r["criteria"]["do_rong"]["points"], 10 - 0.4)
        self.assertEqual(lj.SEVERITY_FRACTION, {"chan": 0.35, "lon": 0.12, "nho": 0.04})   # cùng bảng với devsys/scores.py

    def test_scale_is_0_to_1(self):
        r = lj.normalize(_ai(cu_the={"deductions": [_ded("lon")]}), GOOD_FACTS)
        self.assertTrue(0 <= r["score"] <= 1)
        self.assertAlmostEqual(r["score"], r["total"] / 100)

    def test_bad_enum_missing_fields_and_unknown_criterion_are_reported(self):
        with self.assertRaises(lj.JudgeError) as e:
            lj.normalize(_ai(cu_the={"deductions": [_ded("rat_nang")]}), GOOD_FACTS)
        self.assertIn("rat_nang", str(e.exception))
        with self.assertRaises(lj.JudgeError) as e:
            lj.normalize(_ai(cu_the={"deductions": [_ded("lon", sua=None)]}), GOOD_FACTS)        # lon/chan bắt buộc có cách sửa
        self.assertIn("sua", str(e.exception))
        with self.assertRaises(lj.JudgeError) as e:
            lj.normalize(_ai(cu_the={"deductions": [_ded("lon", evidence=())]}), GOOD_FACTS)
        self.assertIn("evidence", str(e.exception))
        bad = _ai()
        del bad["criteria"]["do_rong"]
        with self.assertRaises(lj.JudgeError) as e:
            lj.normalize(bad, GOOD_FACTS)
        self.assertIn("do_rong", str(e.exception))
        with self.assertRaises(lj.JudgeError):
            lj.normalize(_ai(bang_chung={"deductions": []}), GOOD_FACTS)                      # tiêu chí CODE chấm: AI không được ghi
        with self.assertRaises(lj.JudgeError):
            lj.normalize("không phải JSON", GOOD_FACTS)

    def test_contradiction_quote_must_be_verbatim_else_downgraded(self):
        ok = lj.normalize(_ai(khong_mau_thuan={"deductions": [_ded("chan", evidence=["Luôn ghi rõ số ngón tay."])]}), GOOD_FACTS)
        self.assertEqual(ok["criteria"]["khong_mau_thuan"]["deductions"][0]["muc"], "chan")
        made_up = lj.normalize(_ai(khong_mau_thuan={"deductions": [_ded("chan", evidence=["câu không có trong tài liệu"])]}), GOOD_FACTS)
        d = made_up["criteria"]["khong_mau_thuan"]["deductions"][0]
        self.assertEqual(d["muc"], "lon")
        self.assertIn("không tìm thấy", d["note"])

    def test_chan_caps_total_at_60(self):
        r = lj.normalize(_ai(do_rong={"deductions": [_ded("chan")]}), GOOD_FACTS)
        self.assertLessEqual(r["total"], 60)

    def test_code_criteria_from_facts(self):
        weak = dict(GOOD_FACTS, events=2, projects=1, examples_found=0)
        r = lj.normalize(_ai(), weak)
        self.assertLess(r["criteria"]["bang_chung"]["points"], 25)
        self.assertIn("bang_chung", r["floors_failed"])
        dup = dict(GOOD_FACTS, duplicates=[7])
        self.assertLess(lj.normalize(_ai(), dup)["criteria"]["khong_trung"]["points"], 15)


class ValveTests(unittest.TestCase):
    """8 van BẮT BUỘC về tay người (+ van 'chủ đề đã bỏ' S14.46: coi là không dùng)."""

    def _v(self, facts=None, result=None, **ctx):
        facts = facts or GOOD_FACTS
        result = result or lj.normalize(_ai(), facts)
        return lj.verdict(result, facts, **ctx)

    def test_clean_lesson_passes(self):
        v = self._v()
        self.assertEqual((v["decision"], v["valves"]), ("approve", []))

    def test_1_research_never_judged_by_agent(self):
        v = self._v(facts=dict(GOOD_FACTS, source="research"))
        self.assertEqual(v["decision"], "needs_human")
        self.assertIn("research", v["valves"])

    def test_2_floor_or_chan(self):
        v = self._v(facts=dict(GOOD_FACTS, events=1))
        self.assertIn("san_cung", v["valves"])
        v = self._v(result=lj.normalize(_ai(do_rong={"deductions": [_ded("chan")]}), GOOD_FACTS))
        self.assertIn("san_cung", v["valves"])
        self.assertEqual(v["decision"], "needs_human")

    def test_3_grey_zone(self):
        r = lj.normalize(_ai(), GOOD_FACTS)
        r = dict(r, score=0.87, total=87)
        v = lj.verdict(r, GOOD_FACTS, threshold=0.85)
        self.assertEqual(v["decision"], "needs_human")
        self.assertIn("vung_xam", v["valves"])
        low = lj.verdict(dict(r, score=0.5, total=50), GOOD_FACTS, threshold=0.85)
        self.assertEqual(low["decision"], "reject")

    def test_4_no_claude(self):
        v = lj.verdict(None, GOOD_FACTS, no_claude="thiếu khóa")
        self.assertEqual(v["decision"], "needs_human")
        self.assertIn("khong_goi_duoc_claude", v["valves"])

    def test_5_contradiction(self):
        r = lj.normalize(_ai(khong_mau_thuan={"deductions": [_ded("lon", evidence=["Luôn ghi rõ số ngón tay."])]}), GOOD_FACTS)
        v = lj.verdict(r, GOOD_FACTS, threshold=0.5)
        self.assertIn("mau_thuan", v["valves"])

    def test_6_document_cap(self):
        self.assertIn("tran_tai_lieu", self._v(facts=dict(GOOD_FACTS, doc_chars=lj.SOFT_DOC_CHARS + 1))["valves"])
        self.assertIn("tran_tai_lieu", self._v(facts=dict(GOOD_FACTS, approved_in_group=lj.MAX_AUTO_LESSONS))["valves"])

    def test_7_sync_error(self):
        self.assertIn("loi_dong_bo", self._v(sync_error="LessonError: quá dài")["valves"])

    def test_8_quota_only_for_proposed(self):
        self.assertIn("quota", self._v(approved_this_week=3, quota_week=3)["valves"])
        old = dict(GOOD_FACTS, state="approved")                                             # chấm lại bài cũ (bộ vàng): không tính quota
        self.assertNotIn("quota", self._v(facts=old, approved_this_week=3, quota_week=3)["valves"])

    def test_key_outside_tags(self):
        self.assertIn("key_la", self._v(facts=dict(GOOD_FACTS, key_known=False))["valves"])

    def test_retired_topic_is_not_used(self):
        v = self._v(facts=dict(GOOD_FACTS, retired=["location_plates"]))
        self.assertEqual(v["decision"], "reject")
        self.assertIn("chu_de_da_bo", v["valves"])

    def test_retired_topics_come_from_core_retired_topics(self):
        self.assertEqual(lj.retired_topics("Dùng phông xanh để ghép nền"), ["location_plates"])      # S14.46: một nguồn chủ đề đã bỏ
        self.assertIn("layout_to_model", lj.retired_topics("bật layout_to_model"))
        self.assertEqual(lj.retired_topics("phong cách xanh lá, ánh sáng dịu"), [])          # không bỏ dấu → không khớp nhầm
        self.assertEqual(lj.retired_topics("QC bắt ghép lộ viền phông xanh"), [])            # 'keep': lỗi vẫn còn xảy ra


class EstimateTests(unittest.TestCase):
    def test_stage_has_its_own_limits(self):
        self.assertIn(lj.STAGE, llm_runner.STAGE_SETTINGS)
        self.assertLessEqual(llm_runner.stage_settings(lj.STAGE)["max_tokens"], 4000)
        self.assertIn(lj.STAGE, cost.LLM_STAGE_TOKENS)

    def test_estimate_before_calling(self):
        conn = connect()
        e = lj.estimate(conn, 3)
        self.assertEqual(e["calls"], 3)
        self.assertIn("Claude", e["tag"])
        one = lj.estimate(conn, 1)
        if one["usd"] is not None:
            self.assertAlmostEqual(e["usd"], 3 * one["usd"])
        self.assertEqual(lj.estimate(conn, 0)["tag"], "")


class ShadowRunTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["KNOWLEDGE_USER_DIR"] = self.dir
        self.conn = connect()
        for i, (pid, text) in enumerate([(1, "tay thừa ngón"), (2, "ngón tay méo"), (1, "bàn tay sai"), (2, "thừa ngón tay")]):
            self.conn.execute("INSERT INTO mistakes (source, ref_id, at, project_id, stage, group_name, text) VALUES ('review',?,?,?,?,?,?)",
                              (i + 1, "2026-10-01T00:00:00+00:00", pid, "image", "director", text))
        ev = json.dumps({"events": 4, "projects": 2, "examples": ["tay thừa ngón", "ngón tay méo"]}, ensure_ascii=False)
        rows = [("mistake:hands", "Tránh lỗi lặp: Bàn tay", "Mỗi nhân vật trong khung: ghi rõ 'năm ngón mỗi bàn tay', tránh cận cảnh bàn tay đang cầm vật nhỏ.",
                 "mistakes", "proposed"),
                ("research:x", "Mẹo web", "Dùng prompt X.", "research", "proposed"),
                ("mistake:lighting", "Tránh lỗi lặp: Ánh sáng", "Ghép phông xanh rồi chỉnh sáng bằng tay cho khớp nền.", "mistakes", "approved"),
                ("mistake:face", "Tránh lỗi lặp: Khuôn mặt", "Chú ý mặt.", "mistakes", "rejected")]
        for key, title, body, src, state in rows:
            self.conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, evidence, state) VALUES (?,?,?,?,?,?,?,?)",
                              ("2026-10-02T00:00:00+00:00", "director", key, title, body, src, ev, state))
        self.conn.commit()

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_USER_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _files(self):
        return sorted(os.path.join(d, f) for d, _, fs in os.walk(self.dir) for f in fs)

    def _lessons(self):
        return [tuple(r) for r in self.conn.execute("SELECT id, key, title, body, state, decided_at FROM lessons ORDER BY id")]

    def test_flag_off_by_default_and_nothing_runs(self):
        self.assertIn("lesson_judge", features.FEATURES)
        self.assertFalse(features.FEATURES["lesson_judge"]["verified"])
        client = mock.Mock()
        with mock.patch.object(features, "on", return_value=False):
            with self.assertRaises(lj.JudgeOff):
                lj.judge_all(self.conn, client)
        client.complete.assert_not_called()
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM lesson_reviews").fetchone()[0], 0)

    def test_mock_end_to_end_records_and_changes_nothing(self):
        before = self._lessons()
        docs_before = self._files()
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"):
            out = lj.judge_all(self.conn, lj.MockJudge())
        self.assertEqual(self._lessons(), before)                                            # bóng: không đổi bài học nào
        self.assertEqual(self._files(), docs_before)                          # … không ghi knowledge
        rows = {r["lesson_id"]: dict(r) for r in self.conn.execute("SELECT * FROM lesson_reviews")}
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["reviewer_type"] == "ai_agent" for r in rows.values()))
        by_key = {r[1]: r[0] for r in before}
        hands = rows[by_key["mistake:hands"]]
        self.assertEqual(hands["decision"], "approve")
        self.assertAlmostEqual(hands["threshold_at_time"], lj.AUTO_PASS_DEFAULT)
        detail = json.loads(hands["detail"])
        self.assertEqual(set(detail["criteria"]), set(lj.CRITERIA))
        self.assertTrue(detail["shadow"])
        self.assertEqual(rows[by_key["research:x"]]["decision"], "needs_human")              # van 1: không gọi Claude cho research
        lighting = rows[by_key["mistake:lighting"]]
        self.assertEqual(lighting["decision"], "reject")                                     # chủ đề đã bỏ (phông xanh)
        self.assertIn("chu_de_da_bo", json.loads(lighting["detail"])["valves"])
        self.assertEqual(out["judged"], 4)
        self.assertEqual(out["calls"], 2)                                                    # research + chủ đề đã bỏ: không tốn lời gọi

    def test_rerun_skips_unchanged_lessons(self):
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"):
            lj.judge_all(self.conn, lj.MockJudge())
            out = lj.judge_all(self.conn, lj.MockJudge())
        self.assertEqual(out["judged"], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM lesson_reviews").fetchone()[0], 4)

    def test_budget_halt_records_valve_and_diag_without_calling(self):
        client = mock.Mock()
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"), \
                mock.patch("core.budget.check_llm", return_value="Anthropic báo hết credit"):
            lj.judge_all(self.conn, client)
        client.complete.assert_not_called()
        decisions = {r["decision"] for r in self.conn.execute("SELECT decision FROM lesson_reviews")}
        self.assertEqual(decisions - {"reject"}, {"needs_human"})
        self.assertTrue(self.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='lesson_judge_no_claude'").fetchone()[0])

    def test_invalid_model_answer_goes_to_person_and_is_logged(self):
        bad = mock.Mock()
        bad.complete.return_value = llm_runner.LlmReply(text="xin lỗi, không chấm được")
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"):
            lj.judge_all(self.conn, bad)
        self.assertGreaterEqual(bad.complete.call_count, 1)
        row = self.conn.execute("SELECT decision, detail FROM lesson_reviews WHERE lesson_id=1").fetchone()
        self.assertEqual(row["decision"], "needs_human")
        self.assertIn("tra_loi_hong", json.loads(row["detail"])["valves"])

    def test_agreement_with_people(self):
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"):
            lj.judge_all(self.conn, lj.MockJudge())
        a = lj.agreement(self.conn)
        self.assertEqual(a["pairs"], 2)                                                     # chỉ bài người đã duyệt/bỏ, agent không 'cần người'
        self.assertFalse(a["ready"])                                                         # < 10 cặp

    def test_transport_failure_records_the_no_claude_valve(self):
        client = mock.Mock()
        client.complete.side_effect = llm_runner.LlmError("mất kết nối", code="network", transient=True)
        before = self._lessons()
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"):
            out = lj.judge_all(self.conn, client)
        self.assertEqual(self._lessons(), before)
        self.assertEqual(out["judged"], 4)
        row = self.conn.execute("SELECT decision, detail FROM lesson_reviews WHERE lesson_id=1").fetchone()
        self.assertEqual(row["decision"], "needs_human")
        self.assertIn("khong_goi_duoc_claude", json.loads(row["detail"])["valves"])

    def test_agreement_ignores_a_review_of_the_previous_body(self):
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"):
            lj.judge_all(self.conn, lj.MockJudge())
        self.conn.execute("UPDATE lessons SET body='Nội dung mới, chưa được agent chấm.' WHERE key='mistake:face'")
        self.conn.commit()
        self.assertEqual(lj.agreement(self.conn)["pairs"], 1)

    def test_a_network_failure_can_be_judged_again_after_recovery(self):
        client = mock.Mock()
        client.complete.side_effect = llm_runner.LlmError("mất kết nối", code="network", transient=True)
        with mock.patch.object(features, "on", side_effect=lambda n: n == "lesson_judge"):
            lj.judge_all(self.conn, client)
            self.assertEqual(lj.pending_count(self.conn), 2)
            out = lj.judge_all(self.conn, lj.MockJudge())
        self.assertEqual(out["calls"], 2)
        self.assertEqual(lj.pending_count(self.conn), 0)


if __name__ == "__main__":
    unittest.main()


class LessonsTabUiTests(unittest.TestCase):
    """Tab Bài học: cờ tắt → không có gì mới; cờ bật → nút chấm có giá trên nhãn, bấm thì ghi kết quả bóng, bài học không đổi."""
    APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")

    def setUp(self):
        try:
            from streamlit.testing.v1 import AppTest  # noqa: F401
        except ImportError:  # pragma: no cover
            self.skipTest("streamlit.testing không có")
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "m.sqlite")
        env = {"DASHBOARD_EXPERT": "1", "PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(self.tmp, "projects"),
               "KNOWLEDGE_USER_DIR": os.path.join(self.tmp, "knowledge_user"), "LLM_PROVIDER": "mock"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        from core.pipeline import Pipeline
        p = Pipeline(connect(self.db))
        p.create_project("Demo")
        ev = json.dumps({"events": 4, "projects": 2, "examples": []}, ensure_ascii=False)
        p.conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, evidence, state) VALUES (?,?,?,?,?,?,?,?)",
                       ("2026-10-02T00:00:00+00:00", "director", "mistake:hands", "Tránh lỗi lặp: Bàn tay",
                        "Ghi rõ năm ngón mỗi bàn tay, tránh cận cảnh bàn tay cầm vật nhỏ.", "mistakes", ev, "proposed"))
        p.conn.commit()

    def _run(self, flag: str):
        from streamlit.testing.v1 import AppTest
        with mock.patch.dict(os.environ, {"FEATURE_LESSON_JUDGE": flag}):
            at = AppTest.from_file(self.APP, default_timeout=60)
            at.query_params["step"] = "lessons"
            at.run()
        return at

    def test_flag_off_shows_nothing_new(self):
        at = self._run("0")
        self.assertFalse(at.exception)
        self.assertFalse([b for b in at.button if b.key == "ls_judge"])

    def test_flag_on_button_has_price_and_click_records_shadow_review(self):
        at = self._run("1")
        self.assertFalse(at.exception)
        btn = next(b for b in at.button if b.key == "ls_judge")
        self.assertRegex(btn.label, r"≈\s*[\d.,]+|chưa có giá")
        with mock.patch.dict(os.environ, {"FEATURE_LESSON_JUDGE": "1"}):
            btn.click().run()
        self.assertFalse(at.exception)
        conn = connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM lesson_reviews WHERE reviewer_type='ai_agent'").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT state FROM lessons").fetchone()[0], "proposed")          # bóng: bài học không đổi
        text = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
        self.assertIn("chế độ bóng", text)
