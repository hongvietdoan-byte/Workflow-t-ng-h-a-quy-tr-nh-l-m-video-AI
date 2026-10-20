"""V3.1 M1.7 — vận hành (0 USD): G55 Dashboard / vòng nền chạy code cũ (cờ stale_code_alarm), G56 gộp diag lặp theo (mã, shot)
(cờ diag_merge), G39 regen kiểm data_dir, A14 câu báo ngân sách theo D01 khi mức dự tính = 0 (cờ budget_notice_d01).
Cờ tắt = như cũ (test so). Không gọi dịch vụ tốn tiền, không đọc data/ thật."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import code_version, diag, money_policy, regen
from core.db import connect
from core.pipeline import Pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def flag(name, on=True):
    return mock.patch.dict(os.environ, {f"FEATURE_{name.upper()}": "1" if on else "0"})


class FakeRepo:
    def __init__(self, base, sha="a" * 40, packed=False):
        git = os.path.join(base, ".git")
        os.makedirs(os.path.join(git, "refs", "heads"))
        with open(os.path.join(git, "HEAD"), "w") as f:
            f.write("ref: refs/heads/main\n")
        self.git, self.base = git, base
        self.set(sha, packed)

    def set(self, sha, packed=False):
        ref = os.path.join(self.git, "refs", "heads", "main")
        if packed:
            if os.path.exists(ref):
                os.remove(ref)
            with open(os.path.join(self.git, "packed-refs"), "w") as f:
                f.write(f"# pack-refs\n{sha} refs/heads/main\n")
        else:
            with open(ref, "w") as f:
                f.write(sha + "\n")


class G55StaleCode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = os.path.join(self.tmp, "data", "manifest.sqlite")
        os.makedirs(os.path.dirname(self.db))

    def test_head_sha_reads_loose_and_packed_refs(self):
        repo = FakeRepo(self.tmp)
        self.assertEqual(code_version.head_sha(self.tmp), "a" * 40)
        repo.set("b" * 40, packed=True)
        self.assertEqual(code_version.head_sha(self.tmp), "b" * 40)
        self.assertIsNone(code_version.head_sha(os.path.join(self.tmp, "nope")))

    def test_this_repo_head_is_read(self):
        sha = code_version.head_sha(ROOT)
        self.assertTrue(sha is None or len(sha) == 40)

    def test_registry_finds_an_OTHER_port_running_old_code(self):
        # C-FIX-M16-17: "code cũ" = các .py của core/ + dashboard/ đã đổi từ lúc tiến trình nạp (dấu vân tay), không phải sha HEAD
        new, old = mock.patch.object(code_version, "code_fingerprint", return_value="newcode"), \
            mock.patch.object(code_version, "code_fingerprint", return_value="oldcode")
        with flag("stale_code_alarm"), mock.patch.dict(code_version.BOOT, {"sha": "o" * 40, "pid": 4242, "code": "oldcode"}), \
                mock.patch.object(code_version, "_started_at", return_value=None):
            path = code_version.register("8503", self.db)
            self.assertTrue(path.endswith("dashboard_8503.json"))
            with new:
                rows = code_version.stale_instances(self.db, head="n" * 40, alive=lambda pid: True)
            self.assertEqual([(r["port"], r["pid"]) for r in rows], [("8503", 4242)])
            with old:
                self.assertEqual(code_version.stale_instances(self.db, head="n" * 40, alive=lambda pid: True), [])   # chỉ commit đổi
            with new, mock.patch.object(code_version, "head_sha", return_value="n" * 40), \
                    mock.patch.object(code_version, "_alive", return_value=True):
                text = code_version.banner(self.db)
            with new:
                self.assertEqual(code_version.stale_instances(self.db, head="n" * 40, alive=lambda pid: False), [])  # tiến trình đã tắt
        self.assertIn("8503", text)
        self.assertIn("stop_dashboard.ps1 -All", text)

    def test_flag_off_writes_nothing_and_says_nothing(self):
        with flag("stale_code_alarm", False):
            self.assertIsNone(code_version.register("8501", self.db))
            self.assertFalse(os.path.exists(code_version.run_dir(self.db)))
            self.assertEqual(code_version.banner(self.db), "")
            conn = connect(":memory:")
            with mock.patch.dict(code_version.BOOT, {"sha": "o" * 40}), \
                    mock.patch.object(code_version, "head_sha", return_value="n" * 40):
                self.assertIsNone(code_version.check_round(conn))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0], 0)

    def test_background_round_on_old_code_writes_a_diag(self):
        conn = connect(":memory:")
        with flag("stale_code_alarm"), mock.patch.dict(code_version.BOOT, {"sha": "o" * 40, "port": "8503", "code": "oldcode"}), \
                mock.patch.object(code_version, "head_sha", return_value="n" * 40), \
                mock.patch.object(code_version, "code_fingerprint", return_value="newcode"):
            for _ in range(3):
                msg = code_version.check_round(conn)
        self.assertIn("cổng 8503 chạy code cũ — tệp .py của core/ / dashboard/ đã đổi", msg)   # C-FIX-THAP-1: theo dấu vân tay code
        rows = conn.execute("SELECT code, count FROM diag_events").fetchall()
        self.assertEqual([(r["code"], r["count"]) for r in rows], [(code_version.CODE, 3)])

    def test_round_once_calls_the_check(self):
        import inspect
        from core import bg_poll
        self.assertIn("code_version.check_round(conn)", inspect.getsource(bg_poll.round_once))

    def test_serve_registers_its_port(self):
        from dashboard import serve
        self.assertEqual(serve._port(["--server.port", "8504", "--x"]), "8504")
        self.assertEqual(serve._port(["--server.port=8503"]), "8503")
        with mock.patch("core.code_version.register") as reg:
            serve._register(["--server.port", "8503"])
        reg.assert_called_once_with("8503")

    def test_stop_script_can_stop_every_dashboard_port(self):
        with open(os.path.join(ROOT, "tools", "stop_dashboard.ps1"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("[switch]$All", src)
        self.assertIn("dashboard\\.serve", src)
        self.assertIn("DASHBOARD_PORT", src)                       # không có -All: như cũ


class G56DiagMerge(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def burst(self):
        for i in range(5):
            diag.record(self.conn, "video", "warn", f"chưa gửi: lý do {i}", "change_review_hold", project_id=31, scene_id=7, job_id=70)
        diag.record(self.conn, "video", "warn", "chưa gửi: lý do x", "change_review_hold", project_id=31, scene_id=8, job_id=80)

    def test_flag_off_keeps_one_row_per_wording(self):
        with flag("diag_merge", False):
            self.burst()
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0], 6)

    def test_same_code_same_shot_is_one_row_with_a_count_and_the_newest_wording(self):
        with flag("diag_merge"):
            self.burst()
        rows = self.conn.execute("SELECT scene_id, count, message FROM diag_events ORDER BY scene_id").fetchall()
        self.assertEqual([(r["scene_id"], r["count"]) for r in rows], [(7, 5), (8, 1)])
        self.assertEqual(rows[0]["message"], "chưa gửi: lý do 4")

    def test_rows_read_by_job_or_wording_are_never_merged(self):
        # rà quy ước 7 (CAO): video_gate đọc plate_layout theo job_id — 2 ảnh cùng shot phải còn 2 dòng; khác job cũng không gộp
        with flag("diag_merge"):
            diag.record(self.conn, "image", "warn", "lệch bố cục A", "plate_layout", project_id=31, scene_id=7, job_id=1)
            diag.record(self.conn, "image", "warn", "lệch bố cục B", "plate_layout", project_id=31, scene_id=7, job_id=2)
            diag.record(self.conn, "video", "warn", "giữ 1", "change_review_hold", project_id=31, scene_id=7, job_id=1)
            diag.record(self.conn, "video", "warn", "giữ 2", "change_review_hold", project_id=31, scene_id=7, job_id=2)
        rows = self.conn.execute("SELECT code, job_id FROM diag_events ORDER BY id").fetchall()
        self.assertEqual([(r["code"], r["job_id"]) for r in rows],
                         [("plate_layout", 1), ("plate_layout", 2), ("change_review_hold", 1), ("change_review_hold", 2)])

    def test_every_hold_code_of_the_runner_is_merged(self):
        from core import runner
        self.assertTrue(set(runner.HOLD_CODES) <= set(diag.MERGE_CODES))

    def test_without_a_shot_the_old_key_stays(self):
        with flag("diag_merge"):
            diag.record(self.conn, "system", "warn", "a", "x", project_id=1)
            diag.record(self.conn, "system", "warn", "b", "x", project_id=1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0], 2)


class G39RegenDataDir(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.p = Pipeline(connect(":memory:"))
        self.pid = self.p.create_project("G39")
        sid = self.p.create_scene(self.pid, 1, "S1")
        self.job = self.p.create_job(sid, "video_gen")
        self.p.start(self.job)
        self.p.succeed(self.job)
        os.makedirs(os.path.join(self.root, "projects", str(self.pid), "videos"))

    def test_the_data_root_is_refused_before_anything_changes(self):
        with self.assertRaises(ValueError) as e:
            regen.regenerate_video(self.p, self.root, self.job)
        self.assertIn("data_dir sai", str(e.exception))
        self.assertEqual(self.p.job(self.job)["state"], "succeeded")
        self.assertFalse(os.path.exists(os.path.join(self.root, str(self.pid))))       # không tạo data/<id>/trash

    def test_the_projects_folder_works(self):
        new = regen.regenerate_video(self.p, os.path.join(self.root, "projects"), self.job)
        self.assertIsNotNone(new)

    def test_a_folder_without_the_project_yet_still_works(self):
        self.assertIsNone(regen.wrong_data_dir(tempfile.gettempdir() + "/m17-none", self.pid))


class A14BudgetNotice(unittest.TestCase):
    def test_flag_off_keeps_the_old_sentence(self):
        with flag("budget_notice_d01", False):
            text = money_policy.warning_text("dự án #33 — phần ngân sách trích riêng", 3.0, 0.0, 1.2)
        self.assertIn("mức dự tính $0.00", text)

    def test_zero_amount_is_said_as_not_set_with_numbers_and_still_sends(self):
        with flag("budget_notice_d01"):
            text = money_policy.warning_text("dự án #33 — phần ngân sách trích riêng", 3.0, 0.0, 1.2)
            normal = money_policy.warning_text("dự án #33", 3.0, 10.0, 1.2)
        self.assertNotIn("$0.00", text)
        self.assertIn("chưa có mức dự tính (0 USD)", text)
        self.assertIn("đã chi ≈ $3.00", text)
        self.assertIn("lượt này ≈ $1.20", text)
        self.assertIn("VẪN GỬI (D01", text)
        self.assertIn("mức dự tính $10.00", normal)              # mức > 0: câu cũ


if __name__ == "__main__":
    unittest.main()
