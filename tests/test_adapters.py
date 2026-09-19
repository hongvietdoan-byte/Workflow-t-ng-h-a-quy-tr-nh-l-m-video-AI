import json
import os
import re
import tempfile
import unittest
from unittest import mock

from core.adapters import factory
from core.adapters.clipai import ClipAIVideoProvider, classify_failure, resolve_model
from core.adapters.deepix import DeepixImageProvider, validate_seedream_size
from core.adapters.http import ApiClient, HttpResponse, encode_multipart, parse_envelope
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import Pipeline
from core.providers import RISK_CONTROL, ProviderError
from core.runner import VideoRunner

TOKEN = "secret-token-123"


def ok(data, **extra):
    return HttpResponse(200, json.dumps({"code": 0, "msg": "", "data": data, **extra}).encode())


class FakeTransport:
    """Routes requests by (method, path); records everything sent."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def on(self, method, path, handler):
        self.routes[(method, path)] = handler

    def __call__(self, method, url, headers, body, timeout):
        path = url.split("://", 1)[1]
        path = "/" + path.split("/", 1)[1] if "/" in path else "/"
        route = path.split("?")[0]
        self.calls.append({"method": method, "url": url, "path": route, "headers": headers, "body": body})
        handler = self.routes.get((method, route)) or self.routes.get((method, "*"))
        if handler is None:
            return HttpResponse(404, b"not found")
        result = handler(self.calls[-1]) if callable(handler) else handler
        return result


def ctx_of(call):
    text = call["body"].decode("utf-8", "replace")
    return json.loads(re.search(r'name="ctx"\r\n\r\n(.*?)\r\n--', text, re.S).group(1))


def field_of(call, name):
    text = call["body"].decode("utf-8", "replace")
    return re.search(rf'name="{name}"\r\n\r\n(.*?)\r\n--', text, re.S).group(1)


class HttpLayerTests(unittest.TestCase):
    def test_multipart_contains_fields_and_file(self):
        body, ctype = encode_multipart({"a": "1"}, [("image_files", "x.png", b"\x89PNG")])
        self.assertIn("boundary=", ctype)
        self.assertIn(b'name="a"\r\n\r\n1', body)
        self.assertIn(b'filename="x.png"', body)
        self.assertIn(b"\x89PNG", body)

    def test_envelope_rules(self):
        self.assertEqual(parse_envelope({"code": 0, "data": 5}), 5)
        self.assertEqual(parse_envelope({"status": "success", "data": 6}), 6)
        self.assertEqual(parse_envelope({"data": 7}), 7)
        for bad in ({"code": 1, "msg": "x"}, {"status": "error", "msg": "y"}, "nope"):
            with self.assertRaises(ProviderError):
                parse_envelope(bad)

    def test_bearer_header_only_on_api_calls_and_errors_hide_token(self):
        t = FakeTransport()
        t.on("GET", "/x", ok({"v": 1}))
        t.on("GET", "*", HttpResponse(200, b"file-bytes"))
        client = ApiClient("https://api.example", TOKEN, "UA", t)
        self.assertEqual(client.get("/x"), {"v": 1})
        self.assertEqual(t.calls[0]["headers"]["Authorization"], f"Bearer {TOKEN}")
        with tempfile.TemporaryDirectory() as d:
            client.download("https://cdn.example/v.mp4", os.path.join(d, "v.mp4"))
            self.assertNotIn("Authorization", t.calls[-1]["headers"])
            self.assertEqual(open(os.path.join(d, "v.mp4"), "rb").read(), b"file-bytes")
        t.on("GET", "/auth", HttpResponse(401, b"bad"))
        with self.assertRaises(ProviderError) as cm:
            client.get("/auth")
        self.assertEqual(cm.exception.code, "auth")
        self.assertNotIn(TOKEN, str(cm.exception))
        t.on("GET", "/boom", HttpResponse(503, b""))
        with self.assertRaises(ProviderError) as cm:
            client.get("/boom")
        self.assertTrue(cm.exception.transient)


class ClipAITests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.dir = tempfile.mkdtemp()
        self.image = os.path.join(self.dir, "img.png")
        with open(self.image, "wb") as f:
            f.write(b"\x89PNG-fake")
        self.p = ClipAIVideoProvider(TOKEN, "https://clipai.example", self.t)

    def test_model_resolution(self):
        self.assertEqual(resolve_model(None), ("kling-v3-omni", "omni"))
        self.assertEqual(resolve_model("seedance"), ("dreamina-seedance-2-0-260128", "seedance"))
        self.assertEqual(resolve_model("seedance-2.5")[0], "dreamina-seedance-2-5-260628")
        self.assertEqual(resolve_model("dreamina-seedance-2-0-fast-260128")[1], "seedance")
        for bad in ("minimax", "doubao-seedance-2-0", "whatever"):
            with self.assertRaises(ProviderError):
                resolve_model(bad)

    def test_kling_submit_builds_omni_request(self):
        self.t.on("POST", "/api/kling/omni-video-submit",
                  ok({"tasks": [{"task_id": "T1", "task_status": "submitted", "task_status_msg": ""}]}))
        ext = self.p.submit(self.image, "slow push-in", "extra fingers", 5)
        self.assertEqual(ext, "omni:T1")
        call = self.t.calls[0]
        ctx = ctx_of(call)
        self.assertEqual((ctx["model_name"], ctx["duration"], ctx["mode"], ctx["aspect_ratio"], ctx["multi_shot"]),
                         ("kling-v3-omni", "5", "pro", "16:9", 0))
        self.assertEqual(ctx["image_list"], [{"image_url": "", "type": "first_frame"}])
        self.assertNotIn("Avoid", ctx["prompt"])
        self.assertIn(b"\x89PNG-fake", call["body"])
        self.assertIn('name="image_files"', call["body"].decode("utf-8", "replace"))

    def test_negative_prompt_appended_only_when_enabled(self):
        self.t.on("POST", "/api/kling/omni-video-submit", ok({"tasks": [{"task_id": "T", "task_status": "submitted"}]}))
        self.p.negative = "append"
        self.p.submit(self.image, "push in", "extra fingers", 5)
        self.assertIn("Avoid: extra fingers", ctx_of(self.t.calls[0])["prompt"])

    def test_seedance_submit_and_duration_clamps(self):
        self.t.on("POST", "/api/kling/seedance-video-submit",
                  ok({"tasks": [{"task_id": "S1", "task_status": "submitted"}]}))
        self.assertEqual(self.p.submit(self.image, "orbit", None, 20, model="seedance"), "seedance:S1")
        ctx = ctx_of(self.t.calls[0])
        self.assertEqual(ctx["duration"], 15)
        self.assertEqual(ctx["model_name"], "dreamina-seedance-2-0-260128")
        self.assertEqual(ctx["content"][0], {"type": "text", "text": "orbit"})
        self.assertEqual(ctx["content"][1]["role"], "first_frame")
        self.p.submit(self.image, "orbit", None, 20, model="seedance-2.5")
        self.assertEqual(ctx_of(self.t.calls[1])["duration"], 20)

    def test_seedance_failure_hidden_inside_success_envelope(self):
        self.t.on("POST", "/api/kling/seedance-video-submit", ok({"tasks": [
            {"task_id": "S2", "task_status": "failed", "task_status_msg": "Failure to pass the risk control system"}]}))
        with self.assertRaises(ProviderError) as cm:
            self.p.submit(self.image, "wonder woman", None, 5, model="seedance")
        self.assertEqual(cm.exception.code, RISK_CONTROL)

    def test_input_validation(self):
        with self.assertRaises(ProviderError) as cm:
            self.p.submit(self.image, "x" * 2501, None, 5)
        self.assertEqual(cm.exception.code, "prompt_too_long")
        with self.assertRaises(ProviderError) as cm:
            self.p.submit(os.path.join(self.dir, "missing.png"), "ok", None, 5)
        self.assertEqual(cm.exception.code, "missing_image")
        self.assertEqual(self.t.calls, [])

    def list_response(self, rows):
        return ok({"data": rows, "count": len(rows)}, status="success")

    def test_status_scan_download_and_cancel(self):
        rows = [{"id": 11, "task_id": "T1", "task_status": 1, "video_url": ""}]
        self.t.on("GET", "/api/kling/video-list", lambda call: self.list_response(rows))
        self.assertEqual(self.p.status("omni:T1").state, "running")
        query = self.t.calls[0]["url"]
        self.assertIn("task_type=6", query)
        self.assertIn("pageSize=50", query)
        rows[0].update(task_status=2, video_url="https://cdn.example/t1.mp4")
        self.assertEqual(self.p.status("omni:T1").state, "succeeded")
        self.t.on("GET", "*", HttpResponse(200, b"MP4DATA"))
        dest = os.path.join(self.dir, "out", "01.mp4")
        self.p.download("omni:T1", dest)
        self.assertEqual(open(dest, "rb").read(), b"MP4DATA")
        self.assertNotIn("Authorization", self.t.calls[-1]["headers"])
        deleted = []
        self.t.on("POST", "/api/kling/video-delete", lambda call: (deleted.append(json.loads(call["body"])), ok({}))[1])
        self.p.cancel("omni:T1")
        self.assertEqual(deleted, [{"id": 11}])

    def test_failed_status_is_classified_and_missing_task_times_out(self):
        rows = [{"id": 1, "task_id": "T2", "task_status": 3, "task_status_msg": "Failure to pass the risk control system"}]
        self.t.on("GET", "/api/kling/video-list", lambda call: self.list_response(rows))
        st = self.p.status("seedance:T2")
        self.assertIn("task_type=8", self.t.calls[0]["url"])
        self.assertEqual((st.state, st.error_code), ("failed", RISK_CONTROL))
        rows.clear()
        states = [self.p.status("omni:GONE").state for _ in range(12)]
        self.assertEqual(states[:11], ["running"] * 11)
        self.assertEqual(states[11], "failed")

    def test_classify_failure(self):
        self.assertEqual(classify_failure("Failure to pass the risk control system"), RISK_CONTROL)
        self.assertEqual(classify_failure("upstream timeout"), "task_failed")

    def test_from_env(self):
        with mock.patch.dict(os.environ, {"CLIPAI_TOKEN": ""}):
            with self.assertRaises(ProviderError) as cm:
                ClipAIVideoProvider.from_env()
            self.assertEqual(cm.exception.code, "config")
        with mock.patch.dict(os.environ, {"CLIPAI_TOKEN": f"Bearer {TOKEN}", "CLIPAI_ASPECT_RATIO": "9:16"}):
            prov = ClipAIVideoProvider.from_env(self.t)
            self.assertEqual(prov.aspect_ratio, "9:16")
            self.assertEqual(prov.client._headers()["Authorization"], f"Bearer {TOKEN}")


class DeepixTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.p = DeepixImageProvider(TOKEN, "https://deepix.example", self.t)

    def test_submit_builds_text_to_image_request_and_uses_msg_id(self):
        self.t.on("POST", "/api/image-generator/conversation-create", ok({"id": 1, "msg_id": 6789}))
        self.assertEqual(self.p.submit("misty forest"), "6789")
        call = self.t.calls[0]
        self.assertEqual(field_of(call, "prompt_key"), "2")
        self.assertEqual(field_of(call, "message_type"), "text-to-image")
        self.assertEqual(json.loads(field_of(call, "prompts")), [{"key": "positive_prompt", "text": "misty forest"}])
        self.assertEqual(field_of(call, "model"), "dola-seedream-5-0-pro-260628")
        self.assertEqual(field_of(call, "size"), "2048x1152")

    def test_status_uses_nested_data_status(self):
        state = {"status": "generating"}
        self.t.on("GET", "/api/image-generator/message-status",
                  lambda call: ok(dict(state), status="success"))
        self.assertEqual(self.p.status("6789").state, "running")
        self.assertIn("message_id=6789", self.t.calls[0]["url"])
        state.update(status="completed", image_url="https://cdn.example/a.png")
        self.assertEqual(self.p.status("6789").state, "succeeded")
        state.update(status="failed", msg="bad prompt")
        failed = self.p.status("6789")
        self.assertEqual((failed.state, failed.error_message), ("failed", "bad prompt"))

    def test_download_and_size_validation(self):
        self.t.on("GET", "/api/image-generator/message-status",
                  ok({"status": "completed", "image_url": "https://cdn.example/a.png"}, status="success"))
        self.p.status("1")
        self.t.on("GET", "*", HttpResponse(200, b"PNGDATA"))
        with tempfile.TemporaryDirectory() as d:
            self.p.download("1", os.path.join(d, "job_1.png"))
            self.assertEqual(open(os.path.join(d, "job_1.png"), "rb").read(), b"PNGDATA")
        for bad in ("1920x1080", "abc", "16x16", "8192x8192"):
            with self.assertRaises(ProviderError):
                validate_seedream_size(bad)
        validate_seedream_size("2048x1152")


class CheckTests(unittest.TestCase):
    def test_read_only_check_reports_ok_and_failures_without_leaking_token(self):
        from core.adapters import check
        t = FakeTransport()
        t.on("GET", "/api/kling/video-list", ok({"data": [], "count": 3}, status="success"))
        t.on("GET", "/api/image-generator/message-list", HttpResponse(401, b"nope"))
        results = check.run(ClipAIVideoProvider(TOKEN, "https://clipai.example", t),
                            DeepixImageProvider(TOKEN, "https://deepix.example", t))
        self.assertEqual([(n, ok_) for n, ok_, _ in results], [("Clip AI", True), ("Deepix", False)])
        self.assertTrue(all(c["method"] == "GET" for c in t.calls))
        self.assertNotIn(TOKEN, " ".join(m for _, _, m in results))


class FactoryAndRunnerTests(unittest.TestCase):
    def test_factory(self):
        with mock.patch.dict(os.environ, {"VIDEO_PROVIDER": "", "IMAGE_PROVIDER": ""}):
            self.assertIsNone(factory.video_provider())
            self.assertIsNone(factory.image_provider())
        with mock.patch.dict(os.environ, {"VIDEO_PROVIDER": "mock", "IMAGE_PROVIDER": "mock"}):
            self.assertEqual(factory.describe(factory.video_provider()), "mock")
        with mock.patch.dict(os.environ, {"VIDEO_PROVIDER": "clipai", "CLIPAI_TOKEN": ""}):
            with self.assertRaises(ProviderError):
                factory.video_provider()

    def build(self, prompt, transport):
        p = Pipeline(connect())
        directory = tempfile.mkdtemp()
        pid = p.create_project("t", max_retry=2)
        scene = p.create_scene(pid, 1, "S1")
        img = p.create_job(scene)
        p.start(img)
        p.succeed(img)
        p.approve(img)
        images = os.path.join(directory, str(pid), "images")
        os.makedirs(images)
        with open(os.path.join(images, f"job_{img}.png"), "wb") as f:
            f.write(b"png")
        store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": prompt}]})
        approve_motion_prompt(p, scene)
        job = p.create_job(scene, "video_gen")
        provider = ClipAIVideoProvider(TOKEN, "https://clipai.example", transport)
        return p, pid, job, directory, VideoRunner(p, provider, directory)

    def test_end_to_end_success_writes_ordered_file(self):
        t = FakeTransport()
        t.on("POST", "/api/kling/omni-video-submit", ok({"tasks": [{"task_id": "T9", "task_status": "submitted"}]}))
        t.on("GET", "/api/kling/video-list", ok({"data": [{"id": 5, "task_id": "T9", "task_status": 2,
                                                          "video_url": "https://cdn.example/9.mp4"}]}, status="success"))
        t.on("GET", "*", HttpResponse(200, b"VIDEO"))
        p, pid, job, directory, runner = self.build("slow push-in", t)
        runner.run(pid, interval=0, sleep=lambda s: None)
        self.assertEqual(p.state(job).value, "succeeded")
        self.assertTrue(os.path.exists(os.path.join(directory, str(pid), "videos", "01.mp4")))

    def test_risk_control_at_create_is_logged_and_job_fails_without_retry(self):
        t = FakeTransport()
        t.on("POST", "/api/kling/omni-video-submit", ok({"tasks": [
            {"task_id": "T", "task_status": "failed", "task_status_msg": "Failure to pass the risk control system"}]}))
        p, pid, job, directory, runner = self.build("hero flies", t)
        runner.run(pid, interval=0, sleep=lambda s: None)
        self.assertEqual(p.state(job).value, "failed")
        self.assertEqual(p.conn.execute("SELECT provider FROM content_moderation_failures").fetchone()[0], "clipai")
        self.assertEqual(p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], 1)

    def test_network_errors_keep_job_queued_or_running(self):
        t = FakeTransport()
        t.on("POST", "/api/kling/omni-video-submit", HttpResponse(503, b""))
        p, pid, job, directory, runner = self.build("push in", t)
        self.assertEqual(runner.submit_pending(pid), 0)
        self.assertEqual(p.state(job).value, "queued")
        t.on("POST", "/api/kling/omni-video-submit", ok({"tasks": [{"task_id": "T3", "task_status": "submitted"}]}))
        runner.submit_pending(pid)
        self.assertEqual(p.state(job).value, "running")
        t.on("GET", "/api/kling/video-list", HttpResponse(502, b""))
        self.assertEqual(runner.poll_once(pid)["running"], 1)
        self.assertEqual(p.state(job).value, "running")


if __name__ == "__main__":
    unittest.main()
