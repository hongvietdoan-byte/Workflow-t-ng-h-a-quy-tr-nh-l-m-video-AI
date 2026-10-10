"""K1a — tools/byd_fill.py: điền BYĐ cho shot đã có, không chạy lại Đạo diễn. CSDL tạm + Claude giả, KHÔNG gọi API."""
import contextlib
import io
import json
import re
import unittest
from unittest import mock

from core import director_byd, llm_runner
from tests.test_director_byd import KHO, OFF, _good, _project
from tools import byd_fill

SECTION = re.compile(r"### Cảnh (\d+) · shot (\d+)")


class FakeClaude:
    """Lượt sửa BYĐ giả: `make(canh, shot)` → BYĐ trả về cho mỗi shot có trong đề bài."""

    def __init__(self, make):
        self.make, self.prompts = make, []

    def complete(self, prompt, images=()):
        text = llm_runner.plain(prompt)
        self.prompts.append(text)
        rows = [{"canh": int(c), "shot": int(k), "byd": self.make(int(c), int(k))} for c, k in SECTION.findall(text)]
        return llm_runner.LlmReply("```json\n" + json.dumps({"byd": rows}, ensure_ascii=False) + "\n```", 50, 30)


def _shot_project():
    with mock.patch.dict("os.environ", OFF):
        p, pid = _project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())       # cờ tắt: hàng shot không có byd
    return p, pid


def _rows(p, pid):
    return {r[0]: json.loads(r[1]) for r in p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))}


def _run(argv, p, client):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), mock.patch.dict("os.environ", OFF):
        byd_fill.main(argv, conn=p.conn, client=client)
    return buf.getvalue()


def _valid(c, k):
    return _good(k, {"characters": ["KENTA"]})


class BydFillTests(unittest.TestCase):
    def test_dry_run_calls_nobody_and_prints_the_estimate(self):
        p, pid = _shot_project()
        before = _rows(p, pid)
        client = FakeClaude(_valid)
        out = _run(["--project", str(pid)], p, client)
        self.assertEqual(client.prompts, [])
        self.assertIn(f"{len(before)} shot sẽ điền BYĐ", out)
        self.assertIn("Ước tính ≈", out)
        self.assertIn("chạy khô", out)
        self.assertEqual(_rows(p, pid), before)
        est = byd_fill.estimate_usd(p.conn, len(before))
        self.assertGreaterEqual(est["usd"], est["ledger"])

    def test_yes_writes_only_byd_and_byd_kiem(self):
        p, pid = _shot_project()
        before = _rows(p, pid)
        client = FakeClaude(_valid)
        out = _run(["--project", str(pid), "--yes", "--max-usd", "5"], p, client)
        self.assertEqual(len(client.prompts), 1)
        after = _rows(p, pid)
        for rid, data in after.items():
            self.assertEqual({k: v for k, v in data.items() if k not in ("byd", "byd_kiem")}, before[rid])
            self.assertEqual(data["byd_kiem"]["muc"], "ok", data["byd_kiem"])
            self.assertEqual(data["byd"]["noi_chon"]["kho_id"], KHO)
        self.assertIn("OK", out)

    def test_bad_byd_is_retried_at_most_twice_then_yellow(self):
        p, pid = _shot_project()

        def bad(c, k):
            b = _valid(c, k)
            b["may"]["co"] = "XXL"
            return b
        client = FakeClaude(bad)
        out = _run(["--project", str(pid), "--yes", "--max-usd", "5"], p, client)
        self.assertEqual(len(client.prompts), director_byd.MAX_ROUNDS)
        for data in _rows(p, pid).values():
            self.assertEqual(data["byd_kiem"]["muc"], "vang")
            self.assertTrue(data["byd_kiem"]["ly_do"])
        self.assertIn("VANG", out)

    def test_a_shot_with_a_valid_byd_is_not_sent(self):
        p, pid = _shot_project()
        rows = _rows(p, pid)
        first = min(rows)
        rows[first]["byd"] = _valid(1, 1)
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(rows[first], ensure_ascii=False), first))
        p.conn.commit()
        client = FakeClaude(_valid)
        out = _run(["--project", str(pid), "--yes", "--max-usd", "5"], p, client)
        self.assertEqual(len(client.prompts), 1)
        self.assertEqual(len(SECTION.findall(client.prompts[0])), len(rows) - 1)
        self.assertEqual(_rows(p, pid)[first], rows[first])          # giữ nguyên, kể cả không thêm byd_kiem
        self.assertIn("1 shot đã có BYĐ hợp lệ", out)

    def test_a_row_without_shot_input_is_said_yellow(self):
        p, pid = _shot_project()
        p.conn.execute("INSERT INTO scenes (project_id, idx, title, data) VALUES (?, 999, 'x', '{\"location\": \"tháp\"}')", (pid,))
        p.conn.commit()
        out = _run(["--project", str(pid)], p, FakeClaude(_valid))
        self.assertIn("VÀNG hàng #999", out)
        self.assertIn("không dựng được đầu vào", out)

    def test_yes_needs_a_hard_cap(self):
        p, pid = _shot_project()
        with self.assertRaises(SystemExit):
            _run(["--project", str(pid), "--yes"], p, FakeClaude(_valid))


if __name__ == "__main__":
    unittest.main()
