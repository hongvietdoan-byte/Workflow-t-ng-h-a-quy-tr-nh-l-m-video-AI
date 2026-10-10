"""K1a — Đạo diễn điền BYĐ (cờ `shot_intent`, core/director_byd.py). Chỉ Claude giả (core.llm_runner.MockLlm + Recorder) — không lời
gọi tốn tiền. Ca: (1) cờ tắt → prompt + kết quả y cũ; (2) BYĐ hợp lệ → lưu scenes.data.byd, identity_declare / chạy khô đọc được;
(3) BYĐ sai enum → vòng sửa gửi lỗi, tối đa 2, rồi VÀNG có lý do; (4) không trả BYĐ → VÀNG; (5) lượt sửa qua sổ chi + ước tính."""
import copy
import json
import os
import unittest
from unittest import mock

from core import cost, diag, director_byd, director_two_pass as dtp, identity_declare, llm_runner, prompts, shot_intent, shots
from tests.test_director_two_pass import Recorder
from tests.test_v3 import kenta_project

OFF = {"FEATURE_SHOT_INTENT": "0", "FEATURE_DIRECTOR_TWO_PASS": "0"}
ON = {"FEATURE_SHOT_INTENT": "1", "FEATURE_DIRECTOR_TWO_PASS": "0"}
ON_TWO = {"FEATURE_SHOT_INTENT": "1", "FEATURE_DIRECTOR_TWO_PASS": "1"}
KHO = 263


def _project():
    p, pid = kenta_project()
    p.conn.execute("INSERT INTO assets (id, game, kind, name) VALUES (?, 'FF', 'location', 'Tháp Đồng Hồ')", (KHO,))
    p.conn.commit()
    return p, pid


def _good(k, shot):
    who = [c for c in shot.get("characters") or [] if isinstance(c, str)] or ["KENTA"]
    return {"shot": k, "thanh_phan": [{"vat": w, "vai": "chinh" if i == 0 else "phu", "thay": "mat"} for i, w in enumerate(who)],
            "hanh_dong": [{"ai": who[0], "bat_dau": {"tu_the": "dung"}}],
            "may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
            "noi_chon": {"kho_id": KHO, "thoi_gian": "night", "thoi_tiet": "fog"}}


def _walk_shots(obj):
    """Mọi danh sách `shots` trong câu trả lời (một lượt: scenes[*].shots; Tầng B: dạng của cảnh)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "shots" and isinstance(v, list):
                yield v
            else:
                yield from _walk_shots(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_shots(v)


def _with_byd(make):
    def edit(kind, scene, attempt, obj):
        for lst in _walk_shots(obj):
            for k, s in enumerate(lst, 1):
                if isinstance(s, dict):
                    b = make(k, s)
                    if b is not None:
                        s["byd"] = b
        return obj
    return edit


def _is_repair(prompt):
    return llm_runner.plain(prompt).startswith(director_byd.HEADER)


class RepairRecorder(Recorder):
    """Recorder + lượt sửa BYĐ: `fix(round, prompt)` → câu trả lời JSON; ghi thẻ sổ chi lúc gọi."""

    def __init__(self, edit=None, fix=None):
        super().__init__(edit)
        self.fix, self.tags, self.repairs = fix, [], []

    def complete(self, prompt, images=()):
        if _is_repair(prompt):
            self.repairs.append(llm_runner.plain(prompt))
            self.tags.append(llm_runner.current_tag())
            if self.fix is not None:
                return llm_runner.LlmReply("```json\n" + json.dumps(self.fix(len(self.repairs), llm_runner.plain(prompt)),
                                                                     ensure_ascii=False) + "\n```", 50, 30)
            return llm_runner.MockLlm.complete(self, prompt, images)
        return super().complete(prompt, images)


def _rows(p, pid):
    return [r["data"] for r in shots.shots_of(p, pid)]


class FlagOffTests(unittest.TestCase):
    def test_flag_is_registered_off_by_default(self):
        from core import features
        self.assertIn("shot_intent", features.FEATURES)
        self.assertFalse(features.FEATURES["shot_intent"]["verified"])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FEATURE_SHOT_INTENT", None)
            self.assertFalse(director_byd.enabled())

    def test_off_prompt_is_the_on_prompt_without_the_block_byte_for_byte(self):
        block = open(os.path.join(director_byd._ROOT, "prompts", director_byd.PROMPT_FILE), encoding="utf-8").read()
        p, pid = _project()
        with mock.patch.dict(os.environ, OFF):
            off = prompts.build_director_bundle(p, pid)
            self.assertEqual(director_byd.prompt_block(), "")
        with mock.patch.dict(os.environ, ON):
            on = prompts.build_director_bundle(p, pid)
        self.assertNotIn("Bảng ý đồ shot (BYĐ)", off)
        self.assertIn(block, on)
        self.assertEqual(on.replace(prompts._SEP + block, "", 1), off)

    def test_off_run_makes_no_extra_call_and_stores_nothing_new_even_if_the_director_writes_byd(self):
        with mock.patch.dict(os.environ, OFF):
            p0, pid0 = _project()
            plain_rec = RepairRecorder()
            llm_runner.run_director(p0, pid0, plain_rec)
            p1, pid1 = _project()
            chatty = RepairRecorder(edit=_with_byd(_good))      # Đạo diễn tự viết byd khi cờ tắt → không lưu, không kiểm
            llm_runner.run_director(p1, pid1, chatty)
        self.assertEqual(chatty.repairs, [])
        self.assertEqual(plain_rec.prompts, chatty.prompts)
        self.assertEqual(_rows(p0, pid0), _rows(p1, pid1))
        for d in _rows(p1, pid1):
            self.assertNotIn("byd", d)
            self.assertNotIn("byd_kiem", d)
        self.assertNotIn("byd_kiem", json.loads(p1.project(pid1)["director_raw"]))

    def test_off_estimate_text_is_unchanged(self):
        p, pid = _project()
        with mock.patch.dict(os.environ, OFF):
            est = dtp.estimate(p, pid)
        self.assertNotIn("byd", est)
        self.assertNotIn("BYĐ", dtp.estimate_text(est))


class FlagOnTests(unittest.TestCase):
    def test_valid_byd_is_stored_on_each_row_and_readers_use_it(self):
        with mock.patch.dict(os.environ, ON):
            p, pid = _project()
            rec = RepairRecorder(edit=_with_byd(_good))
            llm_runner.run_director(p, pid, rec)
            rows = _rows(p, pid)
        self.assertEqual(rec.repairs, [])
        self.assertTrue(rows)
        for d in rows:
            self.assertEqual(d["byd_kiem"]["muc"], "ok", d.get("byd_kiem"))
            self.assertEqual(shot_intent.validate(d["byd"], p.conn), [])
            who = d["byd"]["thanh_phan"][0]["vat"]
            self.assertTrue(identity_declare.byd_view(d["byd"], who)["trong_khung"])
        self.assertEqual(json.loads(p.project(pid)["director_raw"])["byd_kiem"]["vang_do"], 0)
        from tools import dryrun_k0b_p24 as dry
        byd, issues, suy, _note, spec = dry.byd_of_row({"shot": 1, "thanh_phan": [{"vat": "X", "vai": "chinh"}]}, [], rows[0], p.conn)
        self.assertIs(byd, rows[0]["byd"])
        self.assertEqual(issues, [])
        self.assertIn("Đạo diễn điền", suy[0])
        self.assertEqual([c["vat"] for c in spec["thanh_phan"]], [c["vat"] for c in rows[0]["byd"]["thanh_phan"]])

    def test_the_block_goes_to_the_dp_not_to_tier_a(self):
        with mock.patch.dict(os.environ, ON_TWO):
            p, pid = _project()
            rec = RepairRecorder(edit=_with_byd(_good))
            llm_runner.run_director(p, pid, rec)
            rows = _rows(p, pid)
        kinds = rec.kinds()
        self.assertEqual(kinds[0], "A")
        self.assertNotIn("Bảng ý đồ shot (BYĐ)", llm_runner.plain(rec.prompts[0]))
        self.assertTrue(all("Bảng ý đồ shot (BYĐ)" in llm_runner.plain(pr) for pr, k in zip(rec.prompts, kinds) if k.startswith("B")))
        self.assertTrue(rows and all(d["byd_kiem"]["muc"] == "ok" for d in rows))

    def test_bad_enum_is_sent_back_with_the_error_at_most_twice_then_yellow(self):
        def bad(k, s):
            b = _good(k, s)
            b["hanh_dong"][0]["bat_dau"]["tu_the"] = "lying"
            return b
        with mock.patch.dict(os.environ, ON):
            p, pid = _project()
            rec = RepairRecorder(edit=_with_byd(bad))           # lượt sửa giả trả lại nguyên BYĐ cũ (MockLlm) → vẫn sai
            llm_runner.run_director(p, pid, rec)
            rows = _rows(p, pid)
        self.assertEqual(len(rec.repairs), director_byd.MAX_ROUNDS)
        for text in rec.repairs:
            self.assertIn("hanh_dong[0].bat_dau.tu_the", text)
            self.assertIn("'lying' không hợp lệ", text)
        for d in rows:
            self.assertEqual(d["byd_kiem"]["muc"], "vang")
            self.assertIn("sau 2 vòng sửa", d["byd_kiem"]["ly_do"])
            self.assertEqual(d["byd_kiem"]["vong"], 2)
        warn = p.conn.execute("SELECT severity, message FROM diag_events WHERE code='director_byd' AND project_id=?", (pid,)).fetchall()
        self.assertEqual([r["severity"] for r in warn], ["warn"])
        self.assertIn("sau 2 vòng sửa", warn[0]["message"])

    def test_a_fixed_answer_in_round_one_stops_the_loop(self):
        def bad(k, s):
            b = _good(k, s)
            b["may"]["co"] = "close"
            return b

        def fix(n, prompt):
            ans = director_byd.mock_answer(prompt)
            for r in ans["byd"]:
                r["byd"]["may"]["co"] = "MS"
            return ans
        with mock.patch.dict(os.environ, ON):
            p, pid = _project()
            rec = RepairRecorder(edit=_with_byd(bad), fix=fix)
            llm_runner.run_director(p, pid, rec)
            rows = _rows(p, pid)
        self.assertEqual(len(rec.repairs), 1)
        self.assertIn("may.co", rec.repairs[0])
        self.assertTrue(all(d["byd_kiem"] == {"muc": "ok", "ly_do": "", "loi": [], "vong": 1} for d in rows))

    def test_no_byd_is_yellow_never_silent(self):
        with mock.patch.dict(os.environ, ON):
            p, pid = _project()
            rec = RepairRecorder()                              # Đạo diễn giả không viết byd
            llm_runner.run_director(p, pid, rec)
            rows = _rows(p, pid)
        self.assertEqual(len(rec.repairs), director_byd.MAX_ROUNDS)
        self.assertIn("BYĐ trước: (không có)", rec.repairs[0])
        for d in rows:
            self.assertNotIn("byd", d)
            self.assertEqual(d["byd_kiem"]["muc"], "vang")
            self.assertTrue(d["byd_kiem"]["ly_do"].startswith("Đạo diễn không trả BYĐ"))

    def test_unreadable_repair_answer_counts_as_a_round_and_is_said(self):
        with mock.patch.dict(os.environ, ON):
            p, pid = _project()
            rec = RepairRecorder(fix=lambda n, pr: {"khong": "dung"})
            llm_runner.run_director(p, pid, rec)
        self.assertEqual(len(rec.repairs), 2)
        raw = json.loads(p.project(pid)["director_raw"])
        self.assertEqual(len(raw["byd_kiem"]["loi_goi"]), 2)


class CostTests(unittest.TestCase):
    def test_repair_calls_are_tagged_for_the_ledger(self):
        with mock.patch.dict(os.environ, ON):
            p, pid = _project()
            rec = RepairRecorder()
            llm_runner.run_director(p, pid, rec)
        self.assertEqual(rec.tags, [(director_byd.STAGE, pid)] * 2)

    def test_stage_has_its_own_max_tokens_and_a_priced_estimate(self):
        self.assertIn(director_byd.STAGE, llm_runner.STAGE_SETTINGS)
        self.assertGreaterEqual(llm_runner.STAGE_SETTINGS[director_byd.STAGE]["max_tokens"], 8000)
        self.assertIn(director_byd.STAGE, cost.LLM_STAGE_TOKENS)
        p, _ = _project()
        self.assertIsNotNone(cost.llm_estimate(p.conn, director_byd.STAGE, director_byd.MAX_ROUNDS))

    def test_on_estimate_adds_the_byd_output_and_the_repair_rounds(self):
        p, pid = _project()
        with mock.patch.dict(os.environ, OFF):
            off = dtp.estimate(p, pid)
        with mock.patch.dict(os.environ, ON):
            on = dtp.estimate(p, pid)
        extra = on["byd"]
        self.assertGreater(extra["extra_output"], 0)
        self.assertEqual(on["single"]["output"], off["single"]["output"] + extra["extra_output"])
        self.assertEqual(extra["repair_calls_max"], 2)
        self.assertIn("sửa BYĐ tối đa 2 lượt", dtp.estimate_text(on))


class PromptSyncTests(unittest.TestCase):
    def test_prompt_31_names_every_enum_value_of_the_schema(self):
        text = open(os.path.join(director_byd._ROOT, "prompts", director_byd.PROMPT_FILE), encoding="utf-8").read()
        for name in ("TU_THE", "CHE", "VAI", "THAY", "CO", "DO_CAO", "GOC", "CHUYEN_DONG", "THOI_GIAN", "THOI_TIET", "CHAM_DAT",
                     "NGOAI_LE_LY_DO", "GROUPS"):
            for v in getattr(shot_intent, name):
                self.assertIn(f"`{v}`", text, f"{name}: thiếu `{v}` trong prompt 31")

    def test_the_example_in_prompt_31_is_valid(self):
        text = open(os.path.join(director_byd._ROOT, "prompts", director_byd.PROMPT_FILE), encoding="utf-8").read()
        example = json.loads(text.split("```json", 1)[1].split("```", 1)[0])
        self.assertEqual([i for i in shot_intent.validate(example) if i["muc"] == "do"], [])

    def test_mock_answer_round_trips_the_previous_byd(self):
        b = _good(2, {"characters": ["KENTA"]})
        prompt = director_byd.build_repair_prompt([(3, 2, {"byd": b}, [{"truong": "x", "loi": "y"}]),
                                                   (3, 4, {}, [{"truong": "byd", "loi": "thiếu"}])], 1)
        self.assertEqual(director_byd.mock_answer(prompt), {"byd": [{"canh": 3, "shot": 2, "byd": b},
                                                                    {"canh": 3, "shot": 4, "byd": None}]})


if __name__ == "__main__":
    unittest.main()
