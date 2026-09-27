"""GĐ-C1 (docs/KE_HOACH_TONG_2026-09-24.md): every Claude API call goes through the cost ledger with its stage and project, and the
Claude cap refuses when the spend cannot be known (unpriced model, unreadable or unwritable ledger); a cut answer is reported."""
import glob
import json
import os
import re
import tempfile
import unittest
from unittest import mock

from core import budget, llm_runner
from core.adapters.http import HttpResponse
from core.db import connect

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _transport(calls, stop="end_turn"):
    def send(method, url, headers, body, timeout):
        calls.append(json.loads(body))
        return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "OK"}], "stop_reason": stop,
                                             "usage": {"input_tokens": 1000, "output_tokens": 200}}).encode())
    return send


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        self.conn = connect(self.db)
        self.calls = []

    def client(self, model="claude-sonnet-5", stop="end_turn", ledger=True):
        return llm_runner.AnthropicClient("sk-test", model, transport=_transport(self.calls, stop), sleep=lambda s: None,
                                          ledger=self.db if ledger else None)

    def rows(self):
        return self.conn.execute("SELECT stage, project_id, tier FROM usage_events WHERE kind='llm' ORDER BY id").fetchall()

    def test_calls_carry_their_stage_and_project(self):
        pid = self.conn.execute("INSERT INTO projects (name, created_at) VALUES ('P', 'x')").lastrowid
        self.conn.commit()
        c = self.client()
        with llm_runner.tagged("qc", pid):
            with llm_runner.tagged("asset_vision"):               # nested: keeps the outer project
                c.complete("a")
        c.complete("b")                                           # untagged: still in the ledger, as 'other'
        got = [(r["stage"], r["project_id"]) for r in self.rows()]
        self.assertEqual(got, [("asset_vision", pid)] * 2 + [("other", None)] * 2)

    def test_an_unpriced_model_is_refused_before_paying(self):
        with self.assertRaises(llm_runner.LlmError) as err:
            self.client("claude-unknown-9").complete("x")
        self.assertEqual(err.exception.code, "budget")
        self.assertEqual(self.calls, [])

    def test_a_dated_model_id_takes_the_price_of_its_family(self):
        self.client("claude-sonnet-5-20260901").complete("x")
        self.assertAlmostEqual(budget.llm_spent(self.conn), 1000 * 2.0 / 1e6 + 200 * 10.0 / 1e6)
        self.assertAlmostEqual(budget.token_price({"per_million_tokens": {"claude-opus-5": {"input": 5}, "claude-opus-5-5":
                                                                         {"input": 4}}}, "claude-opus-5-5-x", "input", 1e6), 4)

    def test_an_unreadable_ledger_refuses_instead_of_letting_the_call_through(self):
        c = self.client()
        with mock.patch.object(budget, "check_llm", side_effect=RuntimeError("locked")):
            with self.assertRaises(llm_runner.LlmError) as err:
                c.complete("x")
        self.assertEqual(err.exception.code, "budget")
        self.assertEqual(self.calls, [])

    def test_a_ledger_that_cannot_be_written_keeps_the_answer_then_refuses_the_next_call(self):
        c = self.client()
        with mock.patch("core.cost.record_usage", side_effect=RuntimeError("disk full")):
            self.assertEqual(c.complete("x").text, "OK")          # the paid answer is not lost
        with self.assertRaises(llm_runner.LlmError) as err:
            c.complete("y")
        self.assertEqual(err.exception.code, "budget")
        self.assertEqual(len(self.calls), 1)

    def test_a_cut_answer_is_recorded_and_reported_not_asked_again(self):
        c = self.client(stop="max_tokens")
        with self.assertRaises(llm_runner.LlmError) as err:
            llm_runner.ask_json(c, "json please", lambda o: o)
        self.assertEqual(err.exception.code, "truncated")
        self.assertEqual(len(self.calls), 1)                      # no second paid call for the same cut
        self.assertEqual(len(self.rows()), 2)                     # but the tokens are in the ledger

    def test_background_workers_get_a_ledger_bound_client(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-test"}):
            self.assertEqual(llm_runner.ledger_factory(self.db)().ledger, self.db)

    def test_no_code_path_builds_a_claude_client_without_the_ledger(self):
        bare = []
        for d in ("core", "dashboard", "tools"):
            for f in glob.glob(os.path.join(ROOT, d, "**", "*.py"), recursive=True):
                with open(f, encoding="utf-8") as fh:
                    # a call without the ledger, or the bare function used as a default factory
                    if re.search(r"client_from_env\(\s*\)|llm_runner\.client_from_env\b(?!\()", fh.read()):
                        bare.append(f)
        self.assertEqual(bare, [])


class CacheAndImageTests(unittest.TestCase):
    """GĐ-C2/C3: repeating prompt parts are cached (priced x1.25 once, then x0.1) and pictures are sent at a capped size."""

    def test_the_cached_parts_go_first_then_pictures_then_the_changing_part(self):
        from PIL import Image
        big = os.path.join(tempfile.mkdtemp(), "big.png")
        Image.new("RGB", (3000, 1500), (200, 10, 10)).save(big)
        calls = []
        c = llm_runner.AnthropicClient("sk-test", transport=_transport(calls), sleep=lambda s: None)
        c.complete("RULES" + llm_runner.CACHE_BREAK + "BIBLE" + llm_runner.CACHE_BREAK + "SHOT", [("Ảnh:", big)])
        blocks = calls[0]["messages"][0]["content"]
        self.assertEqual([b.get("text") for b in blocks[:2]], ["RULES", "BIBLE"])
        self.assertTrue(all(b["cache_control"] == {"type": "ephemeral"} for b in blocks[:2]))
        self.assertEqual(blocks[-1], {"type": "text", "text": "SHOT"})
        img = next(b for b in blocks if b["type"] == "image")
        import base64
        import io
        size = Image.open(io.BytesIO(base64.b64decode(img["source"]["data"]))).size
        self.assertEqual(max(size), llm_runner.IMAGE_EDGE)

    def test_cache_tokens_are_priced_from_the_input_price(self):
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)

        def send(method, url, headers, body, timeout):
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "OK"}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": 0, "output_tokens": 0,
                                                           "cache_creation_input_tokens": 1_000_000,
                                                           "cache_read_input_tokens": 1_000_000}}).encode())
        llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, ledger=db).complete("x")
        self.assertAlmostEqual(budget.llm_spent(conn), 2.0 * 1.25 + 2.0 * 0.1)

    def test_other_clients_and_people_never_see_the_cache_mark(self):
        text = "A" + llm_runner.CACHE_BREAK + "B"
        self.assertNotIn("<<<cache>>>", llm_runner.plain(text))
        seen = []
        cli = llm_runner.ClaudeCliClient(run=lambda args, **k: seen.append(k["input"]) or mock.Mock(
            returncode=0, stdout=json.dumps({"result": "OK", "usage": {}}), stderr=""))
        cli.complete(text)
        self.assertNotIn("<<<cache>>>", seen[0])

    def test_the_image_qc_prompt_marks_rules_and_project_parts_for_caching(self):
        from core import prompts
        from tests.test_v3 import kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (pid,)).fetchone()[0]
        parts = prompts.build_qc_bundle(p, sid).split(prompts.CACHE_BREAK)
        self.assertEqual(len(parts), 3)
        self.assertIn("Character Bible", parts[1])
        self.assertIn("Thông số cảnh", parts[2])


class MotionBatchTests(unittest.TestCase):
    """GĐ-C3 (C6/M20/Q1): motion sends each picture once and never more than MAX_IMAGES per call — no silent cut."""

    def test_a_long_project_is_split_into_calls_of_at_most_twelve_pictures(self):
        from tests.test_v3 import _approve_all_images, kenta_project
        p, pid = kenta_project()
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        _approve_all_images(p, pid, data)
        seen = []
        mock_llm = llm_runner.MockLlm()

        class Spy:
            name = "spy"

            def complete(self, prompt, images=()):
                seen.append([label for label, _ in images])
                return mock_llm.complete(prompt, images)

        n = p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]
        out = llm_runner.run_motion(p, pid, Spy(), data)
        self.assertEqual(out["scenes"], n)
        self.assertTrue(all(len(x) <= llm_runner.MAX_IMAGES for x in seen))
        self.assertEqual(out["calls"], len(seen))
        labels = [label for x in seen for label in x]
        self.assertEqual(len(labels), len(set(labels)))                  # a shared group picture is sent once

    def test_batches_cut_on_distinct_pictures(self):
        todo = [{"idx": i, "jid": i // 2} for i in range(30)]           # pairs share a picture: 15 pictures
        batches = llm_runner._motion_batches(todo)
        self.assertEqual([len({r["jid"] for r in b}) for b in batches], [12, 3])

    def test_too_many_pictures_are_refused_before_paying(self):
        calls = []
        c = llm_runner.AnthropicClient("sk-test", transport=_transport(calls), sleep=lambda s: None)
        with self.assertRaises(llm_runner.LlmError) as err:
            c.complete("x", [("a", "/nope")] * (llm_runner.MAX_IMAGES + 1))
        self.assertEqual(err.exception.code, "too_many_images")
        self.assertEqual(calls, [])


class AudioCapAndClipPriceTests(unittest.TestCase):
    """GĐ-C4: audio (no price yet) is capped by count; a paid button knows its clip's price (M8)."""

    def test_audio_stops_at_the_test_round_count(self):
        from core import audio_lib

        class Tts:
            name = "clipai-audio"
            sent = 0

            def generate_tts(self, *a, **k):
                Tts.sent += 1
                return f"a{Tts.sent}"

        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)
        budget.restart(conn, 50)
        budget.save(conn, audio_cap=2)
        d = tempfile.mkdtemp()
        results = [audio_lib.submit_tts(Tts(), d, f"câu {i}", 1, ledger=(conn, None)) for i in range(3)]
        self.assertEqual(Tts.sent, 2)
        self.assertEqual(results[2]["state"], "failed")
        self.assertIn("trần 2 lượt", results[2]["message"])
        self.assertEqual(budget.status(conn)["audios"], 2)

    def test_a_clip_is_priced_with_its_model_and_length(self):
        from core import cost
        from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project
        p, pid = kenta_project()
        data = tempfile.mkdtemp()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        _approve_all_images(p, pid, data)
        _approve_all_motion(p, pid, data)
        sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (pid,)).fetchone()[0]
        usd = cost.clip_estimate(p.conn, sid)
        self.assertIsNotNone(usd)
        self.assertGreater(usd, 0)
        self.assertEqual(cost.price_tag(usd), f" · ≈ {usd:.2f} USD")
        self.assertEqual(cost.price_tag(None), " · chưa có giá")


class ConverseTests(unittest.TestCase):
    """The QC agent's multi-turn tool use goes through the same budget check and ledger as every other Claude call."""

    def test_tools_and_system_are_sent_and_the_blocks_come_back(self):
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)
        sent = []

        def send(method, url, headers, body, timeout):
            sent.append(json.loads(body))
            return HttpResponse(200, json.dumps({"content": [{"type": "tool_use", "id": "a", "name": "view_frame", "input": {"k": 1}}],
                                                 "stop_reason": "tool_use", "usage": {"input_tokens": 500, "output_tokens": 40}}).encode())
        c = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, sleep=lambda s: None, ledger=db)
        with llm_runner.tagged("qc_agent", None):
            reply = c.converse([{"role": "user", "content": [{"type": "text", "text": "soi"}]}], [{"name": "view_frame", "input_schema": {}}],
                               "hệ thống")
        self.assertEqual(reply.blocks[0]["name"], "view_frame")
        self.assertEqual(sent[0]["tools"][0]["name"], "view_frame")
        self.assertEqual(sent[0]["system"][0]["text"], "hệ thống")
        self.assertEqual(conn.execute("SELECT stage FROM usage_events WHERE kind='llm' LIMIT 1").fetchone()[0], "qc_agent")


class SpendLockTests(unittest.TestCase):
    """28/09: the QC agent spent ~2 USD on 1.5 scenes with nothing capping one task, and crossed the Claude cap (5.54 / 5.50)."""

    def client(self, calls, usage=(20000, 2000), db=None):
        def send(method, url, headers, body, timeout):
            calls.append(1)
            return HttpResponse(200, json.dumps({"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
                                                 "usage": {"input_tokens": usage[0], "output_tokens": usage[1]}}).encode())
        return llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=send, sleep=lambda s: None, ledger=db)

    def test_a_task_lock_stops_the_next_call_before_it_is_paid(self):
        calls = []
        c = self.client(calls)                       # each call: 20k in × $2/M + 2k out × $10/M = 0.06
        msgs = [{"role": "user", "content": [{"type": "text", "text": "x"}]}]
        with llm_runner.spend_cap(0.15, "thử") as cap:
            c.converse(msgs, [], max_tokens=4000)
            c.converse(msgs, [], max_tokens=4000)
            with self.assertRaises(llm_runner.LlmError) as e:     # 0.12 spent + the next ≈ 0.06 > 0.15 → refused, not sent
                c.converse(msgs, [], max_tokens=4000)
        self.assertEqual(len(calls), 2)
        self.assertEqual(e.exception.code, "budget")
        self.assertIn("chạm trần 'thử'", str(e.exception))
        self.assertAlmostEqual(cap["spent"], 0.12, places=3)
        c.converse(msgs, [], max_tokens=4000)        # outside the block the task lock is gone
        self.assertEqual(len(calls), 3)

    def test_nested_locks_all_count_and_the_tightest_one_stops(self):
        calls = []
        c = self.client(calls)
        msgs = [{"role": "user", "content": [{"type": "text", "text": "x"}]}]
        with llm_runner.spend_cap(1.0, "cả lần chạy") as total:
            with llm_runner.spend_cap(0.07, "một cảnh"):
                c.converse(msgs, [], max_tokens=4000)
                with self.assertRaises(llm_runner.LlmError):
                    c.converse(msgs, [], max_tokens=4000)
        self.assertAlmostEqual(total["spent"], 0.06, places=3)

    def test_one_call_whose_worst_case_is_over_the_per_call_lock_is_refused(self):
        calls = []
        c = self.client(calls)
        with self.assertRaises(llm_runner.LlmError):
            c.converse([{"role": "user", "content": [{"type": "text", "text": "x"}]}], [], max_tokens=200000)   # 200k × $10/M = 2 USD
        self.assertEqual(calls, [])

    def test_the_project_cap_is_never_crossed_by_the_next_call(self):
        from core import budget
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)
        budget.save(conn, enabled=True, llm_usd=0.05)
        calls = []
        c = self.client(calls, db=db)
        with self.assertRaises(llm_runner.LlmError) as e:      # worst case of this call (4000 out = 0.04 + input) with 0 spent: ok?
            c.converse([{"role": "user", "content": [{"type": "text", "text": "x" * 40000}]}], [], max_tokens=4000)
        self.assertIn("có thể tốn tới", str(e.exception))      # 16k in ($0.032) + 4k out ($0.04) = 0.072 > 0.05 → refused
        self.assertEqual(calls, [])
        self.assertIsNone(budget.check_llm(conn, 0.01))


class SourcesTests(unittest.TestCase):
    """Rà soát 2026-09-27: which skill files a Claude call really carried is written with its tokens (llm_calls.sources)."""

    def test_the_files_read_to_build_a_request_go_with_its_tokens(self):
        from core import prompts
        db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        conn = connect(db)
        calls = []
        c = llm_runner.AnthropicClient("sk-test", "claude-sonnet-5", transport=_transport(calls), sleep=lambda s: None, ledger=db)
        text = prompts._read("prompts", "21_scene_qc.md") + prompts._read("knowledge", "ai_image_failure_modes.md")
        with llm_runner.tagged("qc"):
            c.complete(text)
        c.complete("không đọc tệp nào")
        rows = conn.execute("SELECT stage, sources, input_tokens FROM llm_calls ORDER BY id").fetchall()
        self.assertEqual(set(json.loads(rows[0]["sources"])), {"prompts/21_scene_qc.md", "knowledge/ai_image_failure_modes.md"})
        self.assertEqual(rows[0]["stage"], "qc")
        self.assertEqual(json.loads(rows[1]["sources"]), [])              # forgotten after each call


if __name__ == "__main__":
    unittest.main()
