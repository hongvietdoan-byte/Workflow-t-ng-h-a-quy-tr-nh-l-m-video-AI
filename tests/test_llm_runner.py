import base64
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_io, llm_runner as lr
from core.adapters.http import HttpResponse
from core.db import connect
from core.llm_io import lock_character_bible, store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS

KEY = "sk-ant-secret-123"
PNG = bytes([0x89]) + b"PNG" + b"0" * 20


def reply(text, tin=10, tout=5):
    body = {"content": [{"type": "text", "text": text}], "usage": {"input_tokens": tin, "output_tokens": tout}}
    return HttpResponse(200, json.dumps(body).encode())


def error(status, message="x"):
    return HttpResponse(status, json.dumps({"error": {"message": message}}).encode())


class Recorder:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append({"method": method, "url": url, "headers": headers, "body": json.loads(body)})
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


class ClientTests(unittest.TestCase):
    def client(self, *responses, **kw):
        t = Recorder(*responses)
        return lr.AnthropicClient(KEY, transport=t, sleep=lambda s: None, **kw), t

    def test_request_shape_and_image_encoding(self):
        c, t = self.client(reply("hi"))
        img = os.path.join(tempfile.mkdtemp(), "a.png")
        open(img, "wb").write(PNG)
        out = c.complete("chấm ảnh", [("Ảnh:", img)])
        self.assertEqual((out.text, out.input_tokens, out.output_tokens), ("hi", 10, 5))
        call = t.calls[0]
        self.assertEqual(call["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(call["headers"]["x-api-key"], KEY)
        self.assertEqual(call["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(call["body"]["model"], lr.DEFAULT_MODEL)
        blocks = call["body"]["messages"][0]["content"]
        self.assertEqual([b["type"] for b in blocks], ["text", "image", "text"])
        self.assertEqual(blocks[1]["source"]["media_type"], "image/png")
        self.assertEqual(base64.b64decode(blocks[1]["source"]["data"]), PNG)

    def test_transient_errors_are_retried_then_succeed(self):
        c, t = self.client(error(429, "slow down"), error(529), reply("ok"))
        self.assertEqual(c.complete("x").text, "ok")
        self.assertEqual(len(t.calls), 3)

    def test_gives_up_after_retries_and_key_never_leaks(self):
        c, t = self.client(error(500))
        with self.assertRaises(lr.LlmError) as e:
            c.complete("x")
        self.assertTrue(e.exception.transient)
        self.assertNotIn(KEY, str(e.exception))
        self.assertEqual(len(t.calls), 3)

    def test_auth_and_bad_request_are_not_retried(self):
        c, t = self.client(error(401, "bad key"))
        with self.assertRaises(lr.LlmError) as e:
            c.complete("x")
        self.assertEqual((e.exception.code, len(t.calls)), ("auth", 1))
        self.assertNotIn(KEY, str(e.exception))
        c, _ = self.client(error(400, "prompt too long"))
        with self.assertRaises(lr.LlmError) as e:
            c.complete("x")
        self.assertIn("prompt too long", str(e.exception))

    def test_bad_image_inputs(self):
        c, _ = self.client(reply("x"))
        with self.assertRaises(lr.LlmError):
            c.complete("x", [("a", os.path.join(tempfile.mkdtemp(), "missing.png"))])
        txt = os.path.join(tempfile.mkdtemp(), "t.png")
        open(txt, "wb").write(b"not an image")
        with self.assertRaises(lr.LlmError):
            c.complete("x", [("a", txt)])

    def test_from_env_and_selection(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "LLM_PROVIDER": ""}):
            self.assertIsNone(lr.client_from_env())
            with self.assertRaises(lr.LlmError):
                lr.AnthropicClient.from_env()
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": KEY, "LLM_PROVIDER": "", "ANTHROPIC_MODEL": "claude-opus-5"}):
            c = lr.client_from_env()
            self.assertEqual((c.name, c.model), ("anthropic", "claude-opus-5"))
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "mock"}):
            self.assertEqual(lr.client_from_env().name, "mock-llm")


class JsonTests(unittest.TestCase):
    def test_extract_json_variants(self):
        self.assertEqual(lr.extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(lr.extract_json('Đây là kết quả:\n{"a": {"b": 2}}\nHết.'), {"a": {"b": 2}})
        with self.assertRaises(ValueError):
            lr.extract_json("không có json")

    def test_ask_json_retries_once_with_the_error_then_succeeds(self):
        prompts_seen = []

        class Fake:
            def __init__(self):
                self.answers = ["không phải json", '{"ok": true}']

            def complete(self, prompt, images=()):
                prompts_seen.append(prompt)
                return lr.LlmReply(self.answers.pop(0), 3, 2)

        obj, tin, tout = lr.ask_json(Fake(), "P", lambda o: None)
        self.assertEqual((obj, tin, tout), ({"ok": True}, 6, 4))
        self.assertIn("không hợp lệ", prompts_seen[1])

    def test_ask_json_fails_after_two_bad_answers(self):
        class Bad:
            def complete(self, prompt, images=()):
                return lr.LlmReply('{"x": 1}')

        def must_have_a(o):
            if "a" not in o:
                raise llm_io.SchemaError("missing 'a'")

        with self.assertRaises(lr.LlmError) as e:
            lr.ask_json(Bad(), "P", must_have_a)
        self.assertEqual(e.exception.code, "bad_json")


class StepTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", "auto")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        self.client = lr.MockLlm()

    def make_image(self, approved=False):
        scene = self.p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        job = self.p.create_job(scene)
        self.p.start(job)
        self.p.succeed(job)
        path = lr.image_path(self.data, self.pid, job)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(PNG)
        if approved:
            self.p.approve(job)
        return job

    def test_director_stores_characters_and_scenes(self):
        r = lr.run_director(self.p, self.pid, self.client)
        self.assertEqual((r["characters"], r["scenes"]), (1, 1))
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM characters").fetchone()["c"], 1)

    def test_qc_applies_decision_and_reports_tokens(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        job = self.make_image()
        r = lr.run_qc(self.p, job, self.client, self.data)
        self.assertEqual(r["decision"], "approved")  # mock scores 0.9 >= 0.85 in auto mode
        self.assertEqual(r["input_tokens"], 100)

    def test_qc_issues_flow_into_the_retry_reason(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        job = self.make_image()

        class Harsh:
            def complete(self, prompt, images=()):
                return lr.LlmReply(json.dumps({"criteria": {k: 0.3 for k in lr.prompts.qc_criteria()},
                                               "issues": ["tay trái 6 ngón", "sai màu áo"]}))

        self.assertEqual(lr.run_qc(self.p, job, Harsh(), self.data)["decision"], "rejected")
        retry = self.p.conn.execute("SELECT retry_reason FROM jobs WHERE parent_job_id=?", (job,)).fetchone()
        self.assertIn("tay trái 6 ngón", retry["retry_reason"])

    def test_qc_batch_and_missing_image(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        job = self.make_image()
        os.remove(lr.image_path(self.data, self.pid, job))
        with self.assertRaises(lr.LlmError):
            lr.run_qc(self.p, job, self.client, self.data)
        summary = lr.run_qc_batch(self.p, self.pid, self.client, self.data)
        self.assertEqual((summary["checked"], len(summary["failed"])), (0, 1))
        open(lr.image_path(self.data, self.pid, job), "wb").write(PNG)
        summary = lr.run_qc_batch(self.p, self.pid, self.client, self.data)
        self.assertEqual((summary["checked"], summary["decisions"]), (1, {"approved": 1}))

    def test_motion_only_for_scenes_without_a_prompt(self):
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        lock_character_bible(self.p, self.pid)
        self.make_image(approved=True)
        self.assertEqual(lr.run_motion(self.p, self.pid, self.client, self.data)["scenes"], 1)
        row = self.p.conn.execute("SELECT state FROM motion_prompts").fetchone()
        self.assertEqual(row["state"], "pending")
        llm_io.approve_motion_prompt(self.p, self.p.conn.execute("SELECT id FROM scenes").fetchone()["id"])
        self.assertEqual(lr.run_motion(self.p, self.pid, self.client, self.data)["scenes"], 0)  # kept, not overwritten
        self.assertEqual(self.p.conn.execute("SELECT state FROM motion_prompts").fetchone()["state"], "approved")


if __name__ == "__main__":
    unittest.main()
