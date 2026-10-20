# -*- coding: utf-8 -*-
"""Hộp thư sự kiện (tools/hop_thu.py): vòng đời việc, nhận trùng, điều kiện, giao lại, ke, hỏi/trả lời,
file hỏng, giờ VN, và --push qua git thật (repo tạm + remote bare)."""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import hop_thu as ht  # noqa: E402


def run(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = ht.main(["--goc", str(root), *argv])
    return code, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="hop_thu_"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def ok(self, *argv):
        code, out, err = run(self.root, *argv)
        self.assertEqual(code, 0, f"{argv}: {out}{err}")
        return out

    def fail_(self, *argv):
        code, out, err = run(self.root, *argv)
        self.assertEqual(code, 1, f"{argv} phải bị từ chối: {out}{err}")
        return err

    def state(self):
        ev, errors = ht.load_events(self.root)
        return ht.compute_state(ev), errors

    def giao(self, ma, to, **kw):
        argv = ["giao", ma, "--to", to, "--title", kw.get("title", f"việc {ma}"), "--lane", "phien-chinh"]
        if "depends" in kw:
            argv += ["--depends", kw["depends"]]
        if "priority" in kw:
            argv += ["--priority", str(kw["priority"])]
        if "spec" in kw:
            argv += ["--spec", kw["spec"]]
        return self.ok(*argv)


class LifecycleTests(Base):
    def test_giao_nhan_xong_gop(self):
        self.giao("C-M42", "cloud-C", spec="docs/CLOUD_TASKS.md#### C-M42")
        st, _ = self.state()
        self.assertEqual(st["tasks"]["C-M42"].status, ht.CHO)
        out = self.ok("nhan", "C-M42", "--lane", "cloud-C", "--khong-pull")
        self.assertIn("docs/CLOUD_TASKS.md", out)
        self.assertEqual(self.state()[0]["tasks"]["C-M42"].status, ht.DANG_LAM)
        self.ok("xong", "C-M42", "--lane", "cloud-C", "--branch", "claude/m42", "--commit", "abc123")
        t = self.state()[0]["tasks"]["C-M42"]
        self.assertEqual((t.status, t.branch, t.commit), (ht.XONG, "claude/m42", "abc123"))
        self.ok("gop", "C-M42", "--lane", "phien-chinh", "--commit", "def456")
        self.assertEqual(self.state()[0]["tasks"]["C-M42"].status, ht.GOP)
        files = list((self.root / "hop_thu" / "su_kien").glob("*.json"))
        self.assertEqual(len(files), 4)  # mỗi sự kiện một file, không sửa file cũ
        self.assertRegex(files[0].name, r"^\d{8}-\d{6}-[a-zA-Z-]+-[a-z0-9]{4}\.json$")

    def test_xong_by_someone_not_working_on_it_is_refused(self):
        self.giao("A1", "cloud-B")
        self.fail_("xong", "A1", "--lane", "cloud-B", "--branch", "b", "--commit", "c")

    def test_bo(self):
        self.giao("A1", "cloud-B")
        self.ok("bo", "A1", "--lane", "phien-chinh", "--text", "không cần nữa")
        self.assertEqual(self.state()[0]["tasks"]["A1"].status, ht.BO)
        self.fail_("nhan", "A1", "--lane", "cloud-B", "--khong-pull")

    def test_invalid_lane_is_refused(self):
        err = self.fail_("giao", "A1", "--to", "cloud-B", "--title", "x", "--lane", "ai do")
        self.assertIn("Tên làn không hợp lệ", err)
        self.giao("A2", "phien-con-abc")  # mở rộng được


class DuplicateClaimTests(Base):
    def test_cli_refuses_second_claim(self):
        self.giao("DP1", "pool")
        self.ok("nhan", "DP1", "--lane", "cloud-B", "--khong-pull")
        err = self.fail_("nhan", "DP1", "--lane", "cloud-D", "--khong-pull")
        self.assertIn("cloud-B", err)

    def test_earliest_claim_wins_when_both_written_concurrently(self):
        self.giao("DP1", "pool")
        t0 = ht.now_vn() + timedelta(minutes=1)  # sau sự kiện giao
        # cloud-D ghi file SAU về thời gian thật nhưng ts sớm hơn → cloud-D thắng
        ht.write_event(self.root, "cloud-B", "nhan", now=t0 + timedelta(seconds=5), task="DP1")
        ht.write_event(self.root, "cloud-D", "nhan", now=t0, task="DP1")
        st, _ = self.state()
        t = st["tasks"]["DP1"]
        self.assertEqual(t.claimer, "cloud-D")
        self.assertTrue(any("nhận trùng — bỏ" in n and "cloud-B" in n for n in t.notes))
        self.assertIn("nhận trùng — bỏ", ht.render_board(st, []))


class DependsTests(Base):
    def test_depends_not_merged(self):
        self.giao("C-M26", "cloud-C", depends="C-M42,G1")
        self.giao("C-M42", "cloud-B")
        st, _ = self.state()
        self.assertEqual(ht.display_status(st, st["tasks"]["C-M26"]), ht.CHO_DK)
        err = self.fail_("nhan", "C-M26", "--lane", "cloud-C", "--khong-pull")
        self.assertIn("C-M42", err)
        self.assertIn("G1: chưa giao", err)
        board = self.ok("bang")
        self.assertIn("CHỜ ĐIỀU KIỆN", board)
        self.assertIn("thiếu: C-M42: CHỜ, G1: chưa giao", board)

    def test_depends_merged_unlocks(self):
        self.giao("B", "cloud-C", depends="A")
        self.giao("A", "cloud-B")
        self.ok("nhan", "A", "--lane", "cloud-B", "--khong-pull")
        self.ok("xong", "A", "--lane", "cloud-B", "--branch", "x", "--commit", "1")
        self.fail_("nhan", "B", "--lane", "cloud-C", "--khong-pull")  # XONG chưa đủ, phải GỘP
        self.ok("gop", "A", "--lane", "phien-chinh", "--commit", "2")
        self.ok("nhan", "B", "--lane", "cloud-C", "--khong-pull")


class ReassignTests(Base):
    def test_reassign_changes_owner(self):
        self.giao("CX20-5", "cloud-B")
        self.ok("nhan", "CX20-5", "--lane", "cloud-B", "--khong-pull")
        self.giao("CX20-5", "codex")
        t = self.state()[0]["tasks"]["CX20-5"]
        self.assertEqual((t.owner, t.claimer, t.status), ("codex", None, ht.CHO))
        self.fail_("nhan", "CX20-5", "--lane", "cloud-B", "--khong-pull")
        self.ok("nhan", "CX20-5", "--lane", "codex", "--khong-pull")


class NextTests(Base):
    def test_own_first_then_pool_then_none(self):
        self.giao("P1", "pool", priority=1)
        self.giao("O2", "cloud-C", priority=5)
        self.giao("O1", "cloud-C", priority=2)
        self.giao("O0", "cloud-C", priority=0, depends="X")  # chưa đủ điều kiện
        self.assertIn("O1", self.ok("ke", "--lane", "cloud-C"))
        self.ok("ke", "--lane", "cloud-C", "--nhan", "--khong-pull")
        self.assertEqual(self.state()[0]["tasks"]["O1"].claimer, "cloud-C")
        self.ok("nhan", "O2", "--lane", "cloud-C", "--khong-pull")
        out = self.ok("ke", "--lane", "cloud-C")
        self.assertIn("P1", out)
        self.assertIn("pool", out)
        self.ok("nhan", "P1", "--lane", "cloud-C", "--khong-pull")
        self.assertIn("HẾT VIỆC", self.ok("ke", "--lane", "cloud-C"))


class QuestionTests(Base):
    def test_hoi_tra_loi(self):
        self.ok("hoi", "--lane", "cloud-B", "--to", "phien-chinh", "--text", "Dùng nhánh nào?", "--task", "A1")
        st, _ = self.state()
        q = st["questions"][0]
        self.assertIn("Dùng nhánh nào?", ht.render_board(st, []))
        self.ok("tra-loi", q["_file"], "--lane", "phien-chinh", "--text", "main")
        st, _ = self.state()
        board = ht.render_board(st, [])
        self.assertNotIn("Dùng nhánh nào?", board)
        self.fail_("tra-loi", "khong-co.json", "--lane", "phien-chinh", "--text", "x")

    def test_tin_and_het_viec(self):
        self.ok("tin", "--lane", "cloud-D", "--to", "all", "--text", "đã cập nhật pytest")
        self.ok("het-viec", "--lane", "cloud-D")
        board = self.ok("bang")
        self.assertIn("đã cập nhật pytest", board)
        self.assertIn("- cloud-D (từ", board)


class BrokenFileTests(Base):
    def test_broken_json_is_reported_and_others_still_read(self):
        self.giao("A1", "cloud-B")
        d = self.root / "hop_thu" / "su_kien"
        (d / "20261020-090000-cloud-B-zzzz.json").write_text("{không phải json", encoding="utf-8")
        (d / "20261020-090001-cloud-B-yyyy.json").write_text('{"lane": "cloud-B"}', encoding="utf-8")
        code, out, err = run(self.root, "bang")
        self.assertEqual(code, 0)
        self.assertIn("20261020-090000-cloud-B-zzzz.json", err)
        self.assertIn("20261020-090000-cloud-B-zzzz.json", out)
        self.assertIn("20261020-090001-cloud-B-yyyy.json", out)
        self.assertIn("A1", out)

    def test_bom_and_crlf_files_are_read(self):
        d = self.root / "hop_thu" / "su_kien"
        d.mkdir(parents=True)
        ev = {"ts": "2026-10-20T09:00:00+07:00", "lane": "phien-chinh", "kind": "giao", "task": "Z1",
              "to": "cloud-B", "title": "Việc có dấu"}
        (d / "20261020-090000-phien-chinh-abcd.json").write_bytes(
            b"\xef\xbb\xbf" + json.dumps(ev, ensure_ascii=False, indent=2).replace("\n", "\r\n").encode("utf-8"))
        st, errors = self.state()
        self.assertEqual(errors, [])
        self.assertEqual(st["tasks"]["Z1"].title, "Việc có dấu")


class TimeTests(Base):
    def test_vietnam_time_offset(self):
        before = datetime.now(timezone.utc)
        p = ht.write_event(self.root, "cloud-B", "tin", text="x")
        ev = json.loads(p.read_text(encoding="utf-8"))
        self.assertTrue(ev["ts"].endswith("+07:00"), ev["ts"])
        ts = datetime.fromisoformat(ev["ts"])
        self.assertLess(abs((ts - before).total_seconds()), 60)
        local = before.astimezone(timezone(timedelta(hours=7)))
        self.assertTrue(p.name.startswith(local.strftime("%Y%m%d-")), p.name)


def _git(cwd, *a):
    r = subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git {a}: {r.stderr}")
    return r.stdout.strip()


@unittest.skipUnless(shutil.which("git"), "cần git")
class PushTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hop_thu_git_"))
        self.remote = self.tmp / "remote.git"
        _git(self.tmp, "init", "--bare", "-b", "main", str(self.remote))
        seed = self.tmp / "seed"
        _git(self.tmp, "clone", "-q", str(self.remote), str(seed))
        self._cfg(seed)
        (seed / "README.md").write_text("x\n", encoding="utf-8")
        _git(seed, "add", "README.md")
        _git(seed, "commit", "-q", "-m", "init")
        _git(seed, "push", "-q", "origin", "HEAD:main")
        self.a = self._clone("a")
        self.b = self._clone("b")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cfg(self, repo):
        _git(repo, "config", "user.name", "test")
        _git(repo, "config", "user.email", "t@example.com")
        _git(repo, "config", "core.autocrlf", "false")

    def _clone(self, name):
        p = self.tmp / name
        _git(self.tmp, "clone", "-q", "-b", "main", str(self.remote), str(p))
        self._cfg(p)
        return p

    def _remote_files(self):
        out = _git(self.remote, "ls-tree", "-r", "--name-only", "main")
        return [l for l in out.splitlines() if l.startswith("hop_thu/su_kien/")]

    def test_two_lanes_writing_at_once_do_not_conflict(self):
        # cả hai clone cùng đứng ở commit cũ; b push sau phải pull --rebase rồi mới đẩy được
        code, out, err = run(self.a, "giao", "A1", "--to", "cloud-B", "--title", "a", "--lane", "phien-chinh", "--push")
        self.assertEqual(code, 0, out + err)
        code, out, err = run(self.b, "tin", "--lane", "cloud-C", "--to", "all", "--text", "chào", "--push")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(len(self._remote_files()), 2)
        msgs = _git(self.remote, "log", "main", "--format=%B")
        self.assertIn("hộp thư: giao A1 (phien-chinh)", msgs)
        self.assertIn("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", msgs)
        # b sau khi pull thấy việc A1, nhận được
        code, out, err = run(self.b, "nhan", "A1", "--lane", "cloud-B", "--push")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(len(self._remote_files()), 3)

    def test_push_from_feature_branch_sends_only_the_event_file(self):
        _git(self.a, "checkout", "-q", "-b", "nhanh-rieng")
        (self.a / "code.py").write_text("print(1)\n", encoding="utf-8")
        _git(self.a, "add", "code.py")
        _git(self.a, "commit", "-q", "-m", "code riêng")
        run(self.b, "tin", "--lane", "cloud-C", "--text", "trước", "--push")  # main đi trước
        code, out, err = run(self.a, "tin", "--lane", "cloud-B", "--text", "từ nhánh", "--push")
        self.assertEqual(code, 0, out + err)
        names = _git(self.remote, "ls-tree", "-r", "--name-only", "main").splitlines()
        self.assertNotIn("code.py", names)
        self.assertEqual(len(self._remote_files()), 2)
        self.assertEqual(_git(self.a, "rev-parse", "--abbrev-ref", "HEAD"), "nhanh-rieng")


if __name__ == "__main__":
    unittest.main()
