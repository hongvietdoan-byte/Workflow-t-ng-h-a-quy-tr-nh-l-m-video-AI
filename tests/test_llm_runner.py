import base64
import json
import os
import tempfile
import unittest
from unittest import mock

from core import assets, llm_io, llm_runner as lr
from core.adapters.http import HttpResponse
from core.db import connect
from core.llm_io import lock_character_bible, store_scene_analysis
from core.pipeline import Pipeline
from tests.test_llm_io_preflight import ANALYSIS
from tests.test_references import png

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

    def test_director_sees_reference_pictures_of_attached_characters(self):
        """The Director must write the Character Bible from the resource's real picture, not invent an appearance
        that QC then has to unlearn one retry at a time (found by comparing a real project's rejected-job history
        against its character resources: the invented text matched neither the picture nor the final approved
        image consistently across scenes)."""
        with mock.patch.dict(os.environ, {"ASSET_DIR": tempfile.mkdtemp()}):
            aid = assets.create(self.p.conn, "FF", "character", "KELLY", "", "", None, "x")
            assets.add_image(self.p.conn, aid, "kelly.png", png(1))
            assets.attach(self.p.conn, self.pid, aid)
            seen = []

            class Spy:
                def __init__(self, inner):
                    self.inner = inner

                def complete(self, prompt, images=()):
                    seen.append(list(images))
                    return self.inner.complete(prompt, images)

            lr.run_director(self.p, self.pid, Spy(self.client))
        self.assertEqual(len(seen[0]), 1)
        self.assertIn("KELLY", seen[0][0][0])
        self.assertTrue(os.path.exists(seen[0][0][1]))

    def test_director_gets_no_pictures_when_no_character_resource_is_attached(self):
        seen = []

        class Spy:
            def __init__(self, inner):
                self.inner = inner

            def complete(self, prompt, images=()):
                seen.append(list(images))
                return self.inner.complete(prompt, images)

        lr.run_director(self.p, self.pid, Spy(self.client))
        self.assertEqual(seen[0], [])

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


class ClaudeCliTests(unittest.TestCase):
    """The no-API-key route: Claude Code on this PC (`claude -p`). The process is faked here; the real login was not exercised."""

    class Done:
        def __init__(self, out, code=0, err=""):
            self.stdout, self.returncode, self.stderr = out, code, err

    def client(self, done, calls):
        def run(args, **kw):
            calls.append((args, kw))
            return done
        return lr.ClaudeCliClient(run=run)

    def test_a_reply_is_read_from_the_json_output_and_the_prompt_goes_through_stdin(self):
        calls = []
        done = self.Done('{"result": "{\\"ok\\": true}", "is_error": false, "usage": {"input_tokens": 7, "output_tokens": 3}}')
        reply = self.client(done, calls).complete("xin chào")
        self.assertEqual((reply.text, reply.input_tokens, reply.output_tokens), ('{"ok": true}', 7, 3))
        args, kw = calls[0]
        self.assertEqual(kw["input"], "xin chào")
        self.assertNotIn("xin chào", args)

    def test_images_are_passed_as_readable_file_paths(self):
        import tempfile
        calls = []
        path = os.path.join(tempfile.mkdtemp(), "a.png")
        with open(path, "wb") as f:
            f.write(b"x")
        self.client(self.Done('{"result": "ok"}'), calls).complete("chấm ảnh", [("Ảnh 1", path)])
        args, kw = calls[0]
        self.assertIn("Read", args)
        self.assertIn(os.path.dirname(path), args)
        self.assertIn(path, kw["input"])

    def test_not_logged_in_is_reported_with_what_to_do(self):
        done = self.Done('{"is_error": true, "result": "Failed to authenticate: OAuth session expired"}', 1)
        with self.assertRaises(lr.LlmError) as ctx:
            self.client(done, []).complete("x")
        self.assertEqual(ctx.exception.code, "auth")
        self.assertIn("đăng nhập", str(ctx.exception))

    def test_the_connection_check_reports_a_working_and_a_broken_claude(self):
        from core.adapters import check
        class Works:
            name = "fake"
            def complete(self, prompt, images=()):
                return lr.LlmReply("OK")
        class Broken:
            def complete(self, prompt, images=()):
                raise lr.LlmError("Claude Code chưa đăng nhập", code="auth")
        self.assertEqual(check.check_llm(Works())[1], True)
        ok, message = check.check_llm(Broken())[1:]
        self.assertFalse(ok)
        self.assertIn("chưa đăng nhập", message)

    def test_the_claude_process_gets_no_markers_of_a_parent_session(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_ENTRYPOINT": "claude-desktop", "CLAUDECODE": "1", "CLAUDE_CODE_OAUTH_SCOPES": "x", "KEEP_ME": "1"}):
            env = lr.ClaudeCliClient.clean_env()
        self.assertNotIn("CLAUDE_CODE_ENTRYPOINT", env)
        self.assertNotIn("CLAUDECODE", env)
        self.assertNotIn("CLAUDE_CODE_OAUTH_SCOPES", env)
        self.assertEqual(env.get("KEEP_ME"), "1")

    def test_it_is_chosen_by_the_environment_setting(self):
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "claude_cli"}), mock.patch("shutil.which", return_value="claude"):
            self.assertEqual(lr.client_from_env().name, "claude-cli")


if __name__ == "__main__":
    unittest.main()
