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
# Cờ sửa lỗi có chữ "Claude" / "lượt" trong nhãn / lý do nhưng KHÔNG thêm lời gọi tốn tiền (rà 15/10) — mỗi cờ một lý do.
PAID_COST_EXEMPT = {
    "motion_prose": "prompt video viết bằng CODE khi Claude không viết; 'Claude' chỉ ở lý do (so #28 code vs #29 Claude), 0 USD",
    "script_pose_fix": "code sửa BYĐ sau 'lượt Đạo diễn' sẵn có, không thêm lời gọi (0 USD)",
    "send_claim": "khóa 'lượt' gửi job trong CSDL — BỚT gửi trùng, không thêm lời gọi (0 USD)",
}


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

    def test_paid_fix_flags_declare_costs(self):
        """Rà 15/10: cờ sửa lỗi mà nhãn / lý do nói tới Claude / sổ chi / lượt gọi phải khai `costs: True` (costly_fix_flag đọc trường
        này, không dò chữ) — hoặc nằm trong PAID_COST_EXEMPT kèm lý do vì sao 0 USD."""
        hits = []
        for name, meta in features.FEATURES.items():
            if not meta.get("fixes_projects"):
                continue
            text = (meta.get("label", "") + " " + meta.get("why", "")).casefold()
            if any(w in text for w in ("claude", "sổ chi", "lượt")) and meta.get("costs") is not True:
                if not (PAID_COST_EXEMPT.get(name) or "").strip():
                    hits.append(name)
        self.assertEqual(hits, [], "cờ nói tới Claude/sổ chi/lượt nhưng thiếu costs: True (hoặc lý do miễn trừ)")
        for name in PAID_COST_EXEMPT:                  # miễn trừ không được che cờ đã khai tốn tiền / cờ không còn
            self.assertIn(name, features.FEATURES)
            self.assertIsNot(features.FEATURES[name].get("costs"), True, name)

    def test_costs_field_drives_costly_fix_flag(self):
        for name, meta in features.FEATURES.items():
            if meta.get("costs") is True:
                self.assertTrue(BR.costly_fix_flag(name), name)
        for name in ("end_state_fresh", "p24_lessons", "kld_lessons_prompts", "change_review_frames", "qc_framing_cap"):
            self.assertIs(features.FEATURES[name].get("costs"), True, name)
            self.assertTrue(BR.costly_fix_flag(name), name)
        self.assertFalse(BR.costly_fix_flag("video_gate"))

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
        # rà 15/10: qc_framing_cap thêm ảnh vào mỗi lượt QC clip → tốn tiền, không còn bật hàng loạt (xem test_paid_*)
        flags_off(self, "video_gate", "ref_rule_early", "qc_framing_cap")
        names = BR.fix_flags_pending(self.c, 31)
        self.addCleanup(features.save_settings, flags={n: features.settings()["flags"].get(n) for n in names})
        left = BR.enable_fix_flags(names)
        self.assertTrue(features.on("video_gate") and features.on("ref_rule_early"))
        self.assertFalse(features.on("qc_framing_cap"))
        self.assertIn("qc_framing_cap", left)
        red, _ = self._red(31)
        self.assertFalse([it for it in red if it.get("flag") in ("video_gate", "ref_rule_early")])
        self.assertTrue(all(BR.costly_fix_flag(n) for n in left))

    def test_end_state_fresh_not_bulk_enabled(self):
        """Rà 15/10: end_state_fresh dịch lại qua sổ chi (lời gọi Claude) — nút '(0 USD)' không được bật nó."""
        flags_off(self, "end_state_fresh")
        self.addCleanup(features.save_settings, flags={"end_state_fresh": features.settings()["flags"].get("end_state_fresh")})
        self.assertEqual(BR.enable_fix_flags(["end_state_fresh"]), ["end_state_fresh"])
        self.assertFalse(features.on("end_state_fresh"))

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


M71_PAID = ("hero_takes", "end_frames", "scene_qc_claude", "voice_check_redo", "audio_first", "story_check")


class M71PaidFlagsDeclared(unittest.TestCase):
    """C-M71 A2 (+ B5 docs/BANG_CHUNG_CHOT_CO_2026-10-21.md 2.4.3): cờ có đường gọi trả phí (clip ⭐ thứ hai, ảnh khung cuối, Claude mỗi
    cảnh / người xem lần đầu / chọn giọng, TTS gửi lại) phải khai `costs: True` + dòng PAID_FLAGS → costly_fix_flag True (nút bật hàng
    loạt '0 USD' không bật nhầm; 🧭 Trước khi chạy nói giá). Trước C-M71: cả 6 = 0 USD."""

    def test_flags_declare_costs_and_are_costly(self):
        for name in M71_PAID:
            self.assertIs(features.FEATURES[name].get("costs"), True, name)
            self.assertIn(name, BR.PAID_FLAGS, name)
            self.assertTrue(BR.costly_fix_flag(name), name)

    def test_paid_call_sites_are_behind_these_flags(self):
        """Bằng chứng đường gọi trả phí đọc đúng cờ (grep code — nếu đổi tên cờ ở chỗ gọi, test đỏ để khai lại)."""
        sites = {"hero_takes": ("core/hero_takes.py", "FLAG = \"hero_takes\""),
                 "voice_check_redo": ("core/autopilot.py", "features.on(\"voice_check_redo\")"),
                 "story_check": ("core/autopilot.py", "features.on(\"story_check\")"),
                 "audio_first": ("core/autopilot.py", "features.on(\"audio_first\")"),
                 "scene_qc_claude": ("core/qc_scene.py", "scene_qc_claude"),
                 "end_frames": ("core/end_frames.py", "end_frames")}
        for name, (path, needle) in sites.items():
            with open(os.path.join(ROOT, path), encoding="utf-8") as f:
                self.assertIn(needle, f.read(), name)
