"""C1 (người dùng duyệt 15/10, docs/handoff/RA_QUYET_DINH_LOI_LAP_2026-10-15.md mục C1): cờ sửa lỗi gốc của dự án trước (khai
`fixes_projects` trong core/features.py) mà còn TẮT ở dự án mới hơn → mục ĐỎ ở 🧭 Trước khi chạy (lối thoát: bật cờ / bỏ qua có lý do);
`features.report()` xuất bảng trạng thái cờ thật (bật/tắt + nguồn) để báo cáo kết thúc dự án không viết tay."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from core import before_run as BR
from core import features
from core.db import connect
from core.pipeline import Pipeline
from tests._flags import flags_off, flags_on

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P27_FLAGS = ("video_gate", "qc_framing_cap", "plate_view_sentence", "character_state_lock", "ref_rule_early",
             "motion_consistency_lint", "group_keep_approved")


def _clean_env():
    return mock.patch.dict(os.environ, {"FEATURE_" + k.upper(): "" for k in features.FEATURES})


class FixesProjectsDeclared(unittest.TestCase):
    def test_p27_flags_declare_project_27(self):
        for name in P27_FLAGS:
            self.assertIn(27, features.FEATURES[name].get("fixes_projects") or [], name)

    def test_fixes_projects_are_lists_of_project_ids(self):
        for name, meta in features.FEATURES.items():
            if "fixes_projects" in meta:
                fp = meta["fixes_projects"]
                self.assertIsInstance(fp, list, name)
                self.assertTrue(fp and all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in fp), name)

    def test_p27_flags_default_on_by_user_decision(self):
        """Người dùng quyết bật (13/10, nhắc lại 15/10) → mặc định CODE bật, không chỉ nhờ tệp cài đặt máy chính."""
        with _clean_env():
            for name in P27_FLAGS:
                self.assertEqual(features.state(name), "on", name)
                self.assertIn("mặc định", features.why_state(name))
                self.assertFalse(features.FEATURES[name]["verified"], name)   # bật theo quyết định, KHÔNG phải đã thử thật

    def test_env_zero_still_switches_a_default_on_flag_off(self):
        with _clean_env(), mock.patch.dict(os.environ, {"FEATURE_VIDEO_GATE": "0"}):
            self.assertEqual(features.state("video_gate"), "off")


class FixFlagsOff(unittest.TestCase):
    def test_off_flag_listed_for_newer_project_only(self):
        flags_off(self, "video_gate")
        names = {r["name"]: r for r in features.fix_flags_off(31)}
        self.assertIn("video_gate", names)
        self.assertEqual(names["video_gate"]["projects"], [27])
        self.assertTrue(names["video_gate"]["why"])
        self.assertNotIn("video_gate", {r["name"] for r in features.fix_flags_off(27)})   # dự án nó sửa: không báo oan
        self.assertNotIn("video_gate", {r["name"] for r in features.fix_flags_off(12)})   # dự án cũ hơn: không báo oan

    def test_on_flag_not_listed(self):
        flags_on(self, "video_gate")
        self.assertNotIn("video_gate", {r["name"] for r in features.fix_flags_off(31)})

    def test_opt_in_only_flag_never_listed(self):
        tagged = [k for k in features.OPT_IN_ONLY if features.FEATURES.get(k, {}).get("fixes_projects")]
        self.assertTrue(tagged, "cần ít nhất một cờ OPT_IN_ONLY có fixes_projects để kiểm loại trừ")
        flags_off(self, *tagged)
        self.assertFalse({r["name"] for r in features.fix_flags_off(10_000)} & set(tagged))

    def test_no_project_id_lists_nothing(self):
        self.assertEqual(features.fix_flags_off(None), [])


class Report(unittest.TestCase):
    def test_report_rows_have_state_source_verified(self):
        flags_on(self, "video_gate")
        flags_off(self, "qc_framing_cap")
        with _clean_env(), mock.patch.dict(os.environ, {"FEATURE_REF_RULE_EARLY": "0"}):
            rows = {r["name"]: r for r in features.report()}
            self.assertEqual(set(rows), set(features.FEATURES))
            self.assertEqual((rows["video_gate"]["state"], rows["video_gate"]["source"]), ("on", "settings"))
            self.assertEqual((rows["qc_framing_cap"]["state"], rows["qc_framing_cap"]["source"]), ("off", "settings"))
            self.assertEqual((rows["ref_rule_early"]["state"], rows["ref_rule_early"]["source"]), ("off", "env"))
            self.assertEqual((rows["group_keep_approved"]["state"], rows["group_keep_approved"]["source"]), ("on", "default"))
            self.assertEqual(rows["group_keep_approved"]["fixes_projects"], [27])
            self.assertIs(rows["group_keep_approved"]["verified"], False)
            md = features.report_md()
            self.assertIn("video_gate", md)
            self.assertIn("| cờ |", md)

    def test_cli_report_runs_from_any_cwd(self):
        env = dict(os.environ, PYTHONUTF8="1")
        out = subprocess.run([sys.executable, "-m", "core.features", "--report", "--json"], cwd=tempfile.mkdtemp(),
                             env=dict(env, PYTHONPATH=ROOT), capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr[-800:])
        rows = json.loads(out.stdout)
        self.assertIn("video_gate", {r["name"] for r in rows})


class BeforeRunFixFlags(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.c = self.p.conn
        now = "2026-10-15T00:00:00Z"
        for pid in (12, 31):
            self.c.execute("INSERT INTO projects(id, name, created_at) VALUES (?, ?, ?)", (pid, f"p{pid}", now))
        self.c.commit()

    def _red(self, pid):
        res = BR.collect(self.c, self.tmp, pid)
        return [it for g in res["groups"] if g["key"] == "fixes" for it in g["items"] if it["level"] == "do"], res

    def test_red_item_for_newer_project(self):
        flags_off(self, "video_gate")
        red, res = self._red(31)
        hit = [it for it in red if it.get("flag") == "video_gate"]
        self.assertEqual(len(hit), 1)
        self.assertIn("#27", hit[0]["text"])
        self.assertIn("Bật các cờ sửa lỗi", hit[0]["fix"])
        self.assertGreaterEqual(res["counts"]["do"], 1)
        self.assertIn("video_gate", BR.fix_flags_pending(self.c, 31))

    def test_old_project_not_flagged(self):
        flags_off(self, *P27_FLAGS)
        red, _ = self._red(12)
        self.assertFalse([it for it in red if it.get("flag") in P27_FLAGS])

    def test_skip_needs_reason_and_turns_item_to_info(self):
        flags_off(self, "video_gate")
        with self.assertRaises(ValueError):
            BR.skip_fix_flag(self.c, 31, "video_gate", "  ")
        BR.skip_fix_flag(self.c, 31, "video_gate", "đo riêng ở dự án này", who="claude")
        red, res = self._red(31)
        self.assertFalse([it for it in red if it.get("flag") == "video_gate"])
        infos = [it for g in res["groups"] if g["key"] == "fixes" for it in g["items"] if it.get("flag") == "video_gate"]
        self.assertEqual(infos[0]["level"], "info")
        self.assertIn("đo riêng ở dự án này", infos[0]["text"])
        self.assertNotIn("video_gate", BR.fix_flags_pending(self.c, 31))

    def test_enable_turns_on_through_settings(self):
        flags_off(self, "video_gate", "qc_framing_cap")
        names = BR.fix_flags_pending(self.c, 31)
        self.addCleanup(features.save_settings, flags={n: features.settings()["flags"].get(n) for n in names})
        left = BR.enable_fix_flags(names)
        self.assertTrue(features.on("video_gate") and features.on("qc_framing_cap"))
        red, _ = self._red(31)
        self.assertFalse([it for it in red if it.get("flag") in ("video_gate", "qc_framing_cap")])
        self.assertTrue(all(BR.costly_fix_flag(n) for n in left))

    def test_costly_flag_never_bulk_enabled(self):
        """CLAUDE.md quy ước 6: cờ thêm lời gọi tốn tiền (change_review, sửa lỗi #24) không bật hàng loạt."""
        flags_off(self, "change_review")
        self.assertTrue(BR.costly_fix_flag("change_review"))
        self.assertIn("change_review", BR.fix_flags_pending(self.c, 31))
        self.assertEqual(BR.enable_fix_flags(["change_review"]), ["change_review"])
        self.assertFalse(features.on("change_review"))
        red, _ = self._red(31)
        hit = [it for it in red if it.get("flag") == "change_review"]
        self.assertIn("TỐN TIỀN", hit[0]["text"])


if __name__ == "__main__":
    unittest.main()
