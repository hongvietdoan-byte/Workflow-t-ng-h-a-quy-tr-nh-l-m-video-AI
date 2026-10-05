"""S14.23 — Bộ não prompt Đợt 4: bảng kê tài nguyên trước Director (cờ `asset_checklist`, prompts/27, khâu Claude `asset_checklist`).

Không gọi Claude thật: FakeClient trả JSON dựng sẵn."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import asset_checklist, assets, llm_runner
from core.db import connect
from core.pipeline import Pipeline

ON = {"FEATURE_ASSET_CHECKLIST": "1"}
OFF = {"FEATURE_ASSET_CHECKLIST": "0"}
SCRIPT = "Cảnh 1 - Sân thượng\nKelly cầm khẩu M1887 đứng trên sân thượng.\n\nCảnh 2 - Phố\nKelly mặc áo dài đỏ gặp Kenta."


class FakeClient:
    name = "fake"

    def __init__(self, answer=None, error=None):
        self.calls, self.tags = [], []
        self.answer, self.error = answer, error

    def complete(self, prompt, images=()):
        self.calls.append(prompt)
        self.tags.append(llm_runner.current_tag())
        if self.error is not None:
            raise self.error
        return llm_runner.LlmReply(json.dumps(self.answer, ensure_ascii=False), 100, 50)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        env = mock.patch.dict(os.environ, {"FEATURE_SETTINGS_FILE": os.path.join(self.tmp, "none.json")})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", "human_qc", 0.85, 3)
        self.p.set_script_text(self.pid, SCRIPT)
        c = self.p.conn
        self.kelly = assets.create(c, "FF", "character", "Kelly", aliases="Kelly Nhanh")
        self.roof = assets.create(c, "FF", "location", "Sân thượng Bermuda")
        self.dress = assets.create(c, "FF", "outfit", "Áo dài đỏ")
        assets.attach(c, self.pid, self.kelly)

    def answer(self, **over):
        rows = [
            {"loai": "character", "ten": "Kelly", "canh": [1, 2], "quan_trong": "chinh", "trong_kho": self.kelly, "vi_sao": "nhân vật chính"},
            {"loai": "location", "ten": "Sân thượng", "canh": [1], "quan_trong": "chinh", "trong_kho": self.roof, "vi_sao": "nơi cảnh 1"},
            {"loai": "weapon", "ten": "M1887", "canh": [1], "quan_trong": "chinh", "trong_kho": None, "vi_sao": "Kho chưa có"},
            {"loai": "outfit", "ten": "áo dài đỏ", "cho_nhan_vat": "Kelly", "canh": [2], "quan_trong": "phu", "trong_kho": None,
             "vi_sao": "không chắc"},
            {"loai": "character", "ten": "Kenta", "canh": [2], "quan_trong": "phu", "trong_kho": 9999, "vi_sao": "bịa id"},
        ]
        out = {"can": rows, "thieu": ["M1887"]}
        out.update(over)
        return out


class Flag(Base):
    def test_flag_is_new_unverified_and_off_by_default(self):
        from core import features
        self.assertIn("asset_checklist", features.FEATURES)
        self.assertFalse(features.FEATURES["asset_checklist"]["verified"])
        with mock.patch.dict(os.environ, {"FEATURE_ASSET_CHECKLIST": ""}):
            self.assertFalse(features.on("asset_checklist"))

    def test_flag_off_no_call_and_said(self):
        client = FakeClient(self.answer())
        with mock.patch.dict(os.environ, OFF):
            with self.assertRaises(asset_checklist.ChecklistError):
                asset_checklist.run(self.p, self.pid, client)
            self.assertIsNone(asset_checklist.get(self.p, self.pid))
        self.assertEqual(client.calls, [])

    def test_flag_off_director_prompt_identical(self):
        from core import prompts
        with mock.patch.dict(os.environ, OFF):
            off = prompts.build_director_bundle(self.p, self.pid)
        with mock.patch.dict(os.environ, ON):
            asset_checklist.run(self.p, self.pid, FakeClient(self.answer()))
            on = prompts.build_director_bundle(self.p, self.pid)
        self.assertEqual(off, on)

    def test_dashboard_panel_draws_nothing_when_off(self):
        from dashboard.steps import step1_checklist

        class Boom:
            def __getattr__(self, name):
                raise AssertionError(f"st.{name} gọi khi cờ tắt")
        with mock.patch.dict(os.environ, OFF), mock.patch.object(step1_checklist, "st", Boom()):
            step1_checklist.checklist_panel(self.p, self.pid)


class Stage(unittest.TestCase):
    def test_stage_has_own_small_max_tokens_and_estimate(self):
        from core import cost, project_budget
        s = llm_runner.stage_settings(asset_checklist.STAGE)
        self.assertIn(asset_checklist.STAGE, llm_runner.STAGE_SETTINGS)
        self.assertLessEqual(s["max_tokens"], 8000)
        self.assertIn(asset_checklist.STAGE, cost.LLM_STAGE_TOKENS)
        self.assertEqual(project_budget.claude_stage(asset_checklist.STAGE), "claude_director")

    def test_mock_llm_answers_a_valid_checklist(self):
        p = Pipeline(connect())
        pid = p.create_project("m", "human_qc", 0.85, 3)
        p.set_script_text(pid, SCRIPT)
        assets.create(p.conn, "FF", "character", "Kelly")
        with mock.patch.dict(os.environ, ON):
            r = asset_checklist.run(p, pid, llm_runner.MockLlm())
        self.assertTrue(any(row["name"] == "Kelly" and row["status"] != "missing" for row in r["rows"]))


class Run(Base):
    def run_on(self, answer=None):
        client = FakeClient(answer or self.answer())
        with mock.patch.dict(os.environ, ON):
            r = asset_checklist.run(self.p, self.pid, client)
        return r, client

    def test_prompt_has_script_library_with_ids_and_outfit_kind(self):
        _, client = self.run_on()
        prompt = client.calls[0]
        self.assertTrue(prompt.startswith("# Bảng kê tài nguyên"))
        self.assertIn("Kelly cầm khẩu M1887", prompt)
        self.assertIn(f'"id": {self.kelly}', prompt)
        self.assertIn(f'"id": {self.dress}', prompt)
        self.assertIn("Trang phục", prompt)
        self.assertIn("Kelly Nhanh", prompt)                     # other names reach the model

    def test_call_is_tagged_with_its_stage_and_project(self):
        _, client = self.run_on()
        self.assertEqual(client.tags, [(asset_checklist.STAGE, self.pid)])

    def test_rows_statuses_attached_library_missing(self):
        r, _ = self.run_on()
        by = {row["name"]: row for row in r["rows"]}
        self.assertEqual(by["Kelly"]["status"], "attached")
        self.assertEqual(by["Sân thượng"]["status"], "in_library")
        self.assertEqual(by["Sân thượng"]["asset_id"], self.roof)
        self.assertEqual(by["M1887"]["status"], "missing")

    def test_code_matches_outfit_by_exact_name_and_keeps_for_character(self):
        r, _ = self.run_on()
        row = {x["name"]: x for x in r["rows"]}["áo dài đỏ"]
        self.assertEqual(row["kind"], "outfit")
        self.assertEqual(row["asset_id"], self.dress)
        self.assertEqual(row["for_character"], "Kelly")
        self.assertIn("code", row["note"])

    def test_invented_or_wrong_kind_id_is_dropped_and_said(self):
        bad = self.answer()
        bad["can"][0]["trong_kho"] = self.roof               # a place given for a character
        r, _ = self.run_on(bad)
        by = {row["name"]: row for row in r["rows"]}
        self.assertEqual(by["Kenta"]["status"], "missing")
        self.assertIn("9999", by["Kenta"]["note"])
        self.assertEqual(by["Kelly"]["asset_id"], self.kelly)        # wrong kind dropped, then matched by its exact name
        self.assertIn("loại", by["Kelly"]["note"])

    def test_missing_list_recomputed_by_code(self):
        r, _ = self.run_on(self.answer(thieu=[]))
        self.assertEqual(sorted(r["missing"]), sorted(["M1887", "Kenta"]))

    def test_saved_and_stale_when_script_changes(self):
        self.run_on()
        with mock.patch.dict(os.environ, ON):
            self.assertFalse(asset_checklist.get(self.p, self.pid)["stale"])
            self.p.set_script_text(self.pid, SCRIPT + "\nThêm một dòng.")
            self.assertTrue(asset_checklist.get(self.p, self.pid)["stale"])

    def test_used_inputs_written_to_diag(self):
        self.run_on()
        row = self.p.conn.execute("SELECT stage, message FROM diag_events WHERE code='asset_checklist' ORDER BY id DESC").fetchone()
        self.assertEqual(row["stage"], "director")
        self.assertIn("thiếu", row["message"])
        self.assertIn("Kho", row["message"])

    def test_quick_attach_marks_row_attached(self):
        self.run_on()
        with mock.patch.dict(os.environ, ON):
            asset_checklist.attach(self.p, self.pid, self.roof)
            by = {row["name"]: row for row in asset_checklist.get(self.p, self.pid)["rows"]}
        self.assertEqual(by["Sân thượng"]["status"], "attached")


class MissingInputs(Base):
    def test_no_script_is_said_and_no_call(self):
        pid = self.p.create_project("empty", "human_qc", 0.85, 3)
        client = FakeClient(self.answer())
        with mock.patch.dict(os.environ, ON):
            with self.assertRaises(asset_checklist.ChecklistError) as e:
                asset_checklist.run(self.p, pid, client)
        self.assertIn("kịch bản", str(e.exception))
        self.assertEqual(client.calls, [])

    def test_empty_library_is_told_to_the_model_and_shown(self):
        p = Pipeline(connect())
        pid = p.create_project("t2", "human_qc", 0.85, 3, game="XX")
        p.set_script_text(pid, SCRIPT)
        client = FakeClient({"can": [{"loai": "character", "ten": "Kelly", "canh": [1], "quan_trong": "chinh", "trong_kho": None,
                                      "vi_sao": "Kho trống"}], "thieu": ["Kelly"]})
        with mock.patch.dict(os.environ, ON):
            r = asset_checklist.run(p, pid, client)
        self.assertIn("Kho trống", client.calls[0])
        self.assertTrue(any("Kho trống" in w for w in r["warnings"]))

    def test_bad_json_twice_raises_and_diag_warns(self):
        client = FakeClient({"khong": 1})
        with mock.patch.dict(os.environ, ON):
            with self.assertRaises(llm_runner.LlmError):
                asset_checklist.run(self.p, self.pid, client)
        self.assertEqual(len(client.calls), 2)
        row = self.p.conn.execute("SELECT severity FROM diag_events WHERE code='asset_checklist_failed'").fetchone()
        self.assertEqual(row["severity"], "warn")


if __name__ == "__main__":
    unittest.main()


class ReviewFixes(Base):
    """Rà độc lập S14.23 (05/10): quyền chi tiền / gắn, Kho đúng dự án, ước tính tính dư."""

    def stranger(self):
        self.p.user = {"email": "la@garena.vn", "role": "member"}
        self.p.actor = "la@garena.vn"

    def test_a_viewer_cannot_spend_on_a_checklist(self):
        from core import access
        self.stranger()
        client = FakeClient(self.answer())
        with mock.patch.dict(os.environ, ON), self.assertRaises(access.AccessDenied):
            asset_checklist.run(self.p, self.pid, client)
        self.assertEqual(client.calls, [])

    def test_a_viewer_cannot_attach(self):
        from core import access
        self.stranger()
        with self.assertRaises(access.AccessDenied):
            asset_checklist.attach(self.p, self.pid, self.roof)

    def test_attach_only_from_this_projects_library(self):
        other = assets.create(self.p.conn, "OTHERGAME", "character", "Người lạ")
        with self.assertRaises(asset_checklist.ChecklistError):
            asset_checklist.attach(self.p, self.pid, other)
        asset_checklist.attach(self.p, self.pid, self.roof)          # the right Kho still works

    def test_the_estimate_counts_the_retry(self):
        from core import cost
        one = cost.llm_estimate(self.p.conn, asset_checklist.STAGE, 1)
        if one:
            self.assertGreaterEqual(asset_checklist.estimate_usd(self.p.conn), 2 * one - 1e-9)
